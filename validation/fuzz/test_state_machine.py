"""Stateful testing: Hypothesis drives the model through purposeful transitions in random
orders (create / touch / mitigate / invalidate FVGs, create and confirm swings, take
liquidity, build, expand and take EQ clusters) and checks every invariant after each bar.

Rules only choose CANDLES; the model alone decides what happens. "expand cluster"
deliberately prints a swing beyond an active boundary: by DEF-L5.4 that must take the
cluster first, and INV-EQ-09 would fail otherwise.
"""
import pytest
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, precondition, rule

from validation import stats
from validation.artifacts import save_failure
from validation.candles import BASE_TIME, MINUTE
from validation.conftest import BUDGET
from validation.invariants import InvariantViolation, Monitor
from validation.models.ist import IstModel
from validation.models.types import Candle, FvgSettings, LiqSettings, Settings

pytestmark = [pytest.mark.phase2, pytest.mark.phase1, pytest.mark.section("stateful")]
TICK = 0.25
SETTINGS = Settings(fvg=FvgSettings(min_ticks=1, k_tra=0.0, memory=10),
                    liq=LiqSettings(left=2, right=1, k=0.0, tol_ticks=4, min_touch=2, memory=20, eq_memory=4))


class IstMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.m = IstModel(SETTINGS)
        self.mon = Monitor(self.m)
        self.t = BASE_TIME
        self.close = 80_000                          # price in ticks (20000.00)
        stats.bump("stateful.sequences")

    # ── plumbing ──
    def bar(self, o, h, l, c):
        """Feed one candle given in ticks (repaired to a valid OHLC), then check every invariant."""
        h, l = max(h, o, c), min(l, o, c)
        k = Candle(self.t, o * TICK, h * TICK, l * TICK, c * TICK)
        self.t += MINUTE
        self.close = c
        self.m.step(k)
        stats.bump("stateful.bars")
        try:
            self.mon.check()
        except InvariantViolation as v:
            save_failure("stateful_machine", invariant=v.inv_id, message=str(v), candles=self.m.candles,
                         settings=SETTINGS, extra={"bar": v.bar})
            raise

    def px(self, p):
        return round(p / TICK)

    def open_fvgs(self):
        return [z for z in self.m.fvg.bull + self.m.fvg.bear if z.is_open and z.confirm_bar < self.m.bar]

    def active_levels(self):
        return [x for s in self.m.liq.sides() for x in s.live if x.taken_bar is None and x.confirm_bar < self.m.bar]

    def active_clusters(self):
        return [c for s in self.m.liq.sides() for c in s.eqs if c.active and c.bar < self.m.bar]

    def swing(self, side: int, peak: int):
        """3 bars: approach, the swing bar at `peak` ticks, confirmation away from it (left 2, right 1)."""
        c = self.close
        if side > 0:
            self.bar(c, min(c + 2, peak - 2), c - 4, min(c + 1, peak - 3))
            self.bar(self.close, peak, self.close - 2, peak - 3)
            self.bar(peak - 3, peak - 2, peak - 12, peak - 10)
        else:
            self.bar(c, c + 4, max(c - 2, peak + 2), max(c - 1, peak + 3))
            self.bar(self.close, self.close + 2, peak, peak + 3)
            self.bar(peak + 3, peak + 12, peak + 2, peak + 10)

    @initialize()
    def warm(self):
        for _ in range(20):
            self.bar(self.close, self.close + 4, self.close - 4, self.close)

    # ── rules ──
    @rule(gap=st.integers(-8, 8), body=st.integers(-12, 12), up=st.integers(0, 8), down=st.integers(0, 8))
    def create_candle(self, gap, body, up, down):
        stats.bump("stateful.steps")
        o = self.close + gap
        self.bar(o, max(o, o + body) + up, min(o, o + body) - down, o + body)

    @rule(bull=st.booleans(), size=st.integers(1, 12))
    def create_fvg(self, bull, size):
        stats.bump("stateful.steps")
        c = self.close
        if bull:
            self.bar(c, c + 2, c - 2, c + 1)                     # candle 1: high c + 2
            self.bar(c + 1, c + size + 10, c, c + size + 8)      # candle 2: impulse
            lo = c + 2 + size
            self.bar(lo + 2, lo + 6, lo, lo + 4)                 # candle 3: low above candle 1 high
        else:
            self.bar(c, c + 2, c - 2, c - 1)
            self.bar(c - 1, c, c - size - 10, c - size - 8)
            hi = c - 2 - size
            self.bar(hi - 2, hi, hi - 6, hi - 4)

    @precondition(lambda self: self.open_fvgs())
    @rule(data=st.data(), depth=st.sampled_from(["touch", "ce", "full", "invalidate", "near_miss"]))
    def attack_fvg(self, data, depth):
        """touch / mitigate (CE, full) / invalidate an open FVG, or stop one tick short."""
        stats.bump("stateful.steps")
        z = data.draw(st.sampled_from(self.open_fvgs()))
        near, far = (z.top, z.bottom) if z.is_bull else (z.bottom, z.top)
        target = {"touch": near, "ce": z.mid, "full": far, "invalidate": far,
                  "near_miss": near + (TICK if z.is_bull else -TICK)}[depth]
        t = self.px(target)
        if z.is_bull:
            close = t - 2 if depth == "invalidate" else t + 2
            self.bar(max(self.close, t + 4), max(self.close, t + 4) + 1, t, close)
        else:
            close = t + 2 if depth == "invalidate" else t - 2
            self.bar(min(self.close, t - 4), t, min(self.close, t - 4) - 1, close)

    @rule(side=st.sampled_from([1, -1]), prominence=st.integers(4, 40))
    def create_and_confirm_swing(self, side, prominence):
        stats.bump("stateful.steps")
        self.swing(side, self.close + side * prominence)

    @precondition(lambda self: self.active_levels())
    @rule(data=st.data(), ticks=st.integers(0, 3), close_beyond=st.booleans(), gap=st.booleans())
    def take_liquidity(self, data, ticks, close_beyond, gap):
        """0 ticks = exact touch (no take); else take, closing beyond (break) or back (sweep)."""
        stats.bump("stateful.steps")
        x = data.draw(st.sampled_from(self.active_levels()))
        p, sg = self.px(x.price), x.sign
        ext = p + sg * ticks
        close = p + sg * (1 if close_beyond and ticks else -2)
        o = p + sg * 1 if gap and ticks else p - sg * 3
        if sg > 0:
            self.bar(o, ext, min(o, close) - 3, close)
        else:
            self.bar(o, max(o, close) + 3, ext, close)

    @precondition(lambda self: self.active_levels())
    @rule(data=st.data(), offset=st.integers(-5, 2))
    def create_eq_cluster(self, data, offset):
        """A new swing near an active level (inside or just outside the 4-tick tolerance)."""
        stats.bump("stateful.steps")
        x = data.draw(st.sampled_from(self.active_levels()))
        self.close = self.px(x.price) - x.sign * 10
        self.swing(x.sign, self.px(x.price) + x.sign * offset)

    @precondition(lambda self: self.active_clusters())
    @rule(data=st.data(), offset=st.integers(1, 4))
    def expand_cluster(self, data, offset):
        """A swing 1–4 ticks beyond an active cluster's boundary (DEF-L5.4: it takes the cluster)."""
        stats.bump("stateful.steps")
        c = data.draw(st.sampled_from(self.active_clusters()))
        self.close = self.px(c.bound) - c.sign * 10
        self.swing(c.sign, self.px(c.bound) + c.sign * offset)
        assert not c.active, "a swing beyond the boundary must take the cluster first (DEF-L5.4)"

    @precondition(lambda self: self.active_clusters())
    @rule(data=st.data(), ticks=st.integers(1, 3), close_beyond=st.booleans())
    def take_cluster(self, data, ticks, close_beyond):
        stats.bump("stateful.steps")
        c = data.draw(st.sampled_from(self.active_clusters()))
        b, sg = self.px(c.bound), c.sign
        close = b + sg * (1 if close_beyond else -2)
        if sg > 0:
            self.bar(b - 3, b + ticks, b - 6, close)
        else:
            self.bar(b + 3, b + 6, b - ticks, close)
        assert not c.active

    def teardown(self):
        if self.m.candles:
            self.mon.final()


TestIstMachine = IstMachine.TestCase
TestIstMachine.settings = settings(max_examples=BUDGET["machines"], stateful_step_count=BUDGET["steps"], deadline=None)
