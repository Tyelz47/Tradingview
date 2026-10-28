"""Phase 2 · DEF-L2 dominance (C1, v0.4.4-dev).

A swing is significant when BOTH hold: reaction ≥ k × TR average (unchanged) and
dominance: no extreme strictly beyond its price + EQ tolerance in the W bars BEFORE the
swing bar (X−W … X−1; anchored to the origin, the right bars are not part of it).
Presets (left, right, k, W): Aggressive 3/2/0.5/10 · Balanced 5/3/1.0/30 · Strict
10/5/2.0/60 · Custom: no W input, dominance off.
"""
import random

import pytest

from validation import static_checks as stc
from validation.candles import from_rows, random_walk
from validation.invariants import InvariantViolation, Monitor
from validation.models.ist import IstModel
from validation.models.liquidity import LiquidityEngine
from validation.models.types import PRESETS, LiqSettings, Settings
from validation.parity import capture

pytestmark = [pytest.mark.phase2, pytest.mark.section("phase2.swing")]
TOL = 1.0                       # EQ tolerance 4 ticks × 0.25
OUTCOME = {(1, 0, 0, 0): "PASS", (0, 1, 0, 0): "REACTION", (0, 0, 1, 0): "DOMINANCE", (0, 0, 0, 1): "BOTH",
           (0, 0, 0, 0): "WARM-UP"}


class _Rec(LiquidityEngine):
    """The oracle engine, recording each judged pivot's outcome by (side, swing time)."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.dec = {}

    def _judged(self, side, px, X, x_time, react, req, tra, t):
        before = (side.levels, side.rej_react, side.rej_dom, side.rej_both)
        super()._judged(side, px, X, x_time, react, req, tra, t)
        delta = tuple(a - b for a, b in zip((side.levels, side.rej_react, side.rej_dom, side.rej_both), before))
        self.dec[(side.name, x_time)] = OUTCOME[delta]


def _run(cs, settings, checked=True):
    """Every bar stepped and (by default) checked by the invariant monitor."""
    m = IstModel(settings)
    m.liq = _Rec(settings.liq, settings.tick, m.log)
    mon = Monitor(m) if checked else None
    for c in cs:
        m.step(c)
        if mon:
            mon.check()
    return m


def _liq(w=10, left=2, right=2, k=0.0, **kw):
    return Settings(modules=("liq",), liq=LiqSettings(left=left, right=right, k=k, dom=w, **kw))


def _swing(prior=None, w=10, right=2, k=0.0, swing=102.0, n=40, mirror=False, left=2):
    """Flat bars (high 100.5) then a swing high `swing` at bar X = n, `right` lower bars
    (reaction 3 points ≈ 3 × TR) and a tail. `prior` = (d, high) puts that high on bar
    X − d. mirror=True reflects every price (200 − p): the same case for a swing low."""
    rows = [(100, 100.5, 99.5, 100)] * n
    if prior:
        d, hi = prior
        rows[n - d] = (100, hi, 99.5, 100)
    rows += [(100, swing, 99.5, 100)] + [(99.5, 100, 99, 99.5)] * (right + 4)
    if mirror:
        rows = [(200 - o, 200 - l, 200 - h, 200 - c) for o, h, l, c in rows]
    cs = from_rows(rows)
    m = _run(cs, _liq(w, left, right, k))
    return m, m.liq.dec.get(("SSL" if mirror else "BSL", cs[n].time)), cs


# ── 3 · 5 · 6 · 7 · boundaries and window ──────────────────────────────────────

@pytest.mark.spec("DEF-L2")
@pytest.mark.parametrize("mirror", [False, True])
def test_exact_dominance_boundary(mirror):
    """A prior extreme exactly at P ± tolerance does NOT reject; one tick beyond does."""
    assert _swing(prior=(5, 102.0 + TOL), mirror=mirror)[1] == "PASS"
    assert _swing(prior=(5, 102.0 + TOL + 0.25), mirror=mirror)[1] == "DOMINANCE"


@pytest.mark.spec("DEF-L2")
@pytest.mark.parametrize("mirror", [False, True])
def test_dominance_rejection_inside_the_window(mirror):
    for d in (1 + 2, 6, 10):                                  # anywhere in X−W … X−1 (outside the left window)
        m, out, _ = _swing(prior=(d, 105.0), mirror=mirror)
        assert out == "DOMINANCE", d
        side = m.liq.ssl if mirror else m.liq.bsl
        assert not any(x.price == (98.0 if mirror else 102.0) for x in side.all_levels())


@pytest.mark.spec("DEF-L2")
@pytest.mark.parametrize("mirror", [False, True])
def test_outside_the_window_does_not_reject(mirror):
    """The same extreme W + 1 bars before the swing is outside X−W … X−1."""
    assert _swing(prior=(10, 105.0), w=10, mirror=mirror)[1] == "DOMINANCE"
    assert _swing(prior=(11, 105.0), w=10, mirror=mirror)[1] == "PASS"


@pytest.mark.spec("DEF-L2")
def test_window_is_anchored_to_the_origin_not_the_confirmation():
    """With right = 3, a higher high at X − W is inside the origin window but outside the
    window a confirmation-relative rule (t−W … t−1) would read: the correct rule rejects."""
    w, right, n = 10, 3, 40
    m, out, cs = _swing(prior=(w, 105.0), w=w, right=right, n=n)
    X, t = n, n + right
    H = [c.high for c in cs]
    assert max(H[t - w:t]) <= H[X] + TOL                     # confirmation-relative would have accepted
    assert max(H[X - w:X]) > H[X] + TOL and out == "DOMINANCE"
    assert m.liq.dominance_ref(m.liq.bsl, X) == 105.0


# ── 8 · 9 · 10 · reasons and diagnostics ───────────────────────────────────────

@pytest.mark.spec("DEF-L2")
def test_reaction_only_rejection():
    m, out, _ = _swing(k=10.0)
    s = m.liq.bsl
    assert out == "REACTION" and (s.rej_react, s.rej_dom, s.rej_both, s.levels) == (1, 0, 0, 0)


@pytest.mark.spec("DEF-L2")
def test_dominance_only_rejection():
    m, out, _ = _swing(prior=(3, 105.0))
    s = m.liq.bsl
    assert out == "DOMINANCE" and (s.rej_dom, s.rej_both) == (1, 0) and s.rej_react == 0


@pytest.mark.spec("DEF-L2")
def test_both_fail_is_counted_once_as_both():
    """The prior high (itself a pivot, dominant, weak) fails on reaction only; the swing fails
    on both and is counted once, under 'both': the reasons stay disjoint and add up."""
    m, out, cs = _swing(prior=(3, 105.0), k=10.0)
    s = m.liq.bsl
    assert out == "BOTH" and m.liq.dec[("BSL", cs[37].time)] == "REACTION"
    assert (s.pivots, s.levels, s.rejects, s.rej_react, s.rej_dom, s.rej_both) == (2, 0, 2, 1, 0, 1)
    assert s.rejects == s.rej_react + s.rej_dom + s.rej_both
    c = m.state()["counters"]["BSL"]
    assert (c["reject"], c["reject_reaction"], c["reject_dominance"], c["reject_both"]) == (2, 1, 0, 1)


@pytest.mark.spec("DEF-L2")
def test_fewer_than_w_bars_before_the_swing_is_warm_up_not_reject():
    m, out, _ = _swing(w=50, n=40)
    s = m.liq.bsl
    assert out == "WARM-UP" and (s.pivots, s.levels, s.rejects) == (1, 0, 0)


# ── 4 · double tops ────────────────────────────────────────────────────────────

@pytest.mark.spec("DEF-L2", "DEF-L5", "L17")
@pytest.mark.parametrize("mirror", [False, True])
def test_double_top_within_tolerance_still_forms_eq(mirror):
    """A (102, bar 40) then B (101.25, bar 50) with W = 20: A is inside B's window but only
    0.75 above it (≤ tolerance), so B is dominant, qualifies and forms EQH with A. B at
    100.75 (A 1.25 above) is not dominant: no second level, no EQH."""
    def run(b_high):
        rows = [(100, 100.5, 99.5, 100)] * 40 + [(100, 102, 99.5, 100)] + [(99.5, 100, 99, 99.5)] * 3 \
            + [(100, 100.5, 99.5, 100)] * 6 + [(100, b_high, 99.5, 100)] + [(99.5, 100, 99, 99.5)] * 6
        if mirror:
            rows = [(200 - o, 200 - l, 200 - h, 200 - c) for o, h, l, c in rows]
        cs = from_rows(rows)
        return _run(cs, _liq(w=20, right=2)), cs
    m, cs = run(101.25)
    side, eq = ("SSL", "EQL_CREATED") if mirror else ("BSL", "EQH_CREATED")
    assert m.liq.dec[(side, cs[40].time)] == m.liq.dec[(side, cs[50].time)] == "PASS"
    assert [e.type for e in m.events if e.type == eq] == [eq]
    m, cs = run(100.75)
    assert m.liq.dec[(side, cs[50].time)] == "DOMINANCE" and not any(e.type == eq for e in m.events)


# ── 1 · 2 · no lookahead, history start ───────────────────────────────────────

def _decisions(cs, preset):
    return _run(cs, Settings.from_dict({"liq": {"preset": preset}, "modules": ["liq"]}), checked=False).liq.dec


@pytest.mark.parametrize("preset", sorted(PRESETS))
def test_no_lookahead_truncation(preset):
    """Every decision is identical when all bars after its confirmation are removed."""
    cs = random_walk(1500, 31, gap_prob=0.02)
    full = _decisions(cs, preset)
    right = PRESETS[preset][1]
    t2i = {c.time: i for i, c in enumerate(cs)}
    picks = random.Random(5).sample(sorted(full), 25)
    for side, x_time in picks:
        t = t2i[x_time] + right
        cut = _decisions(cs[:t + 1], preset)
        assert cut[(side, x_time)] == full[(side, x_time)], (side, x_time)
        assert {k: v for k, v in cut.items() if t2i[k[1]] + right <= t} == \
               {k: v for k, v in full.items() if t2i[k[1]] + right <= t}


@pytest.mark.parametrize("preset", sorted(PRESETS))
def test_history_start_invariance(preset):
    """Starting the replay later changes no decision of a swing with enough history before
    it (lookback = max(TR length, left, W) bars)."""
    cs = random_walk(1500, 32, gap_prob=0.02)
    full = _decisions(cs, preset)
    look = Settings.from_dict({"liq": {"preset": preset}}).liq.lookback
    for s in (37, 211, 480):
        late = _decisions(cs[s:], preset)
        ok_from = cs[s + look].time
        keys = {k for k in full if k[1] >= ok_from}
        assert keys and {k: late[k] for k in keys} == {k: full[k] for k in keys}, s


# ── 11 · presets and Pine constants ────────────────────────────────────────────

def test_approved_presets_and_pine_constants():
    assert PRESETS == {"aggressive": (3, 2, 0.5, 10), "balanced": (5, 3, 1.0, 30), "strict": (10, 5, 2.0, 60)}
    assert LiqSettings() == LiqSettings.preset("balanced") and LiqSettings().dom == 30
    assert Settings.from_dict({"liq": {"left": 4, "right": 2, "k": 0.7}}).liq.dom == 0          # Custom: off
    for check in (stc.st13_oracle_defaults_match_pine, stc.st16_dominance_rule):
        ok, detail = check()
        assert ok, detail


# ── 12 · 13 · 14 · what C1 must not change ─────────────────────────────────────

def _streams(cs, settings):
    ev = IstModel(settings).run(cs).events
    fam = lambda *f: [(e.bar, e.type, e.dir, e.sid, e.price) for e in ev if e.type.split("_")[0] in f]
    return ev, fam


@pytest.mark.parametrize("preset", sorted(PRESETS))
def test_c1_keeps_a_subset_with_identical_takes_and_phase1_untouched(preset):
    """Against the same preset without dominance: C1 only removes levels; every kept level
    is taken, swept or broken identically; FVG, session and level events are identical."""
    data = [random_walk(3000, seed, gap_prob=0.02) for seed in (41, 42)]
    from validation.studies.liquidity_significance import DATA
    data.append([b["candle"] for b in capture.parse(DATA.read_text(encoding="utf-8"))["bars"]])
    for cs in data:
        old_ev, old = _streams(cs, Settings.from_dict({"liq": {"preset": preset, "dom": 0}}))
        new_ev, new = _streams(cs, Settings.from_dict({"liq": {"preset": preset}}))
        made = lambda ev: {(e.dir, e.sid) for e in ev if e.type in ("BSL_CREATED", "SSL_CREATED")}
        keep = made(new_ev)
        takes = lambda ev: [(e.bar, e.type, e.dir, e.sid, e.price) for e in ev if e.type[:3] in ("BSL", "SSL")
                            and e.type.split("_", 1)[1] in ("TAKEN", "SWEEP", "BREAK") and (e.dir, e.sid) in keep]
        assert keep < made(old_ev) and takes(new_ev) == takes(old_ev)
        assert new("FVG") == old("FVG") and new("SESSION") == old("SESSION") and new("LEVEL") == old("LEVEL")


# ── 15 · mutations must be caught ──────────────────────────────────────────────

def test_mutation_inclusive_boundary_is_caught(monkeypatch):
    """'≥' instead of '>' at the boundary (reject a prior extreme exactly at P + tolerance)
    makes the exact-boundary case fail."""
    assert _swing(prior=(5, 103.0))[1] == "PASS"
    monkeypatch.setattr(LiquidityEngine, "dominant",
                        lambda self, side, px, ref: ref < px + self.tol if side.is_bsl else ref > px - self.tol)
    assert _swing(prior=(5, 103.0))[1] != "PASS"


def test_mutation_dominance_ignored_is_caught_by_the_invariant(monkeypatch):
    """An engine that accepts a non-dominant swing violates INV-LIQ-11."""
    monkeypatch.setattr(LiquidityEngine, "dominant", lambda self, side, px, ref: True)
    with pytest.raises(InvariantViolation, match="INV-LIQ-11"):
        _swing(prior=(5, 105.0))


@pytest.mark.parametrize("old, new", [
    ("domHiRef <= swHiPx + EQ_TOL + EPS", "domHiRef < swHiPx + EQ_TOL + EPS"),   # inclusive boundary lost
    ("domLoRef >= swLoPx - EQ_TOL - EPS", "domLoRef > swLoPx - EQ_TOL - EPS"),
    ("domHiAll[LIQ_R + 1]", "domHiAll[LIQ_R]"),                                    # window shifted onto the swing
    ("swHiPx + EQ_TOL + EPS", "swHiPx + EPS"),                                     # tolerance dropped
    ("not liqWarm and reactHiOk and domHiOk", "not liqWarm and reactHiOk"),         # dominance not applied
])
def test_mutation_of_the_pine_rule_is_caught(old, new):
    src = stc.PINE_SOURCE.read_text(encoding="utf-8") if hasattr(stc, "PINE_SOURCE") else "\n".join(stc.source())
    assert stc.st16_dominance_rule(src)[0]
    assert src.count(old) == 1 and not stc.st16_dominance_rule(src.replace(old, new))[0]
