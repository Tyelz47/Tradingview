"""Property tests · CISD (docs/CISD.md DEF-CISD): every invariant on generated candles, mirror
and translation symmetry, no lookahead, the guard and the body / TR metadata never change a
decision, the other modules untouched, and long random walks. The engine asserts on every bar
that two CISDs never confirm on one bar (DEF-CISD4).

Random candles hold many dojis and equal lows (small tick integers); the zigzags make the
delivery state flip often (counter "cisd.confirmed" in the report)."""
import pytest
from hypothesis import given
from hypothesis import strategies as st

from validation import stats
from validation.candles import from_ticks, mirror, random_walk, shift
from validation.conftest import BUDGET, MODE
from validation.fuzz.helpers import checked, run
from validation.fuzz.strategies import SPEC, candle_lists, full_settings
from validation.models.types import MODULES, CisdSettings, Settings

pytestmark = [pytest.mark.cisd, pytest.mark.section("property")]


@st.composite
def zigzags(draw):
    """Legs of 2–12 bars drifting −10…10 ticks a bar (dojis and gaps included), then random candles."""
    specs = []
    for _ in range(draw(st.integers(2, 12))):
        d, n = draw(st.integers(-10, 10)), draw(st.integers(2, 12))
        specs += draw(st.lists(st.tuples(st.sampled_from([0, 0, 0, -3, 3]), st.integers(d - 3, d + 3),
                                         st.integers(0, 4), st.integers(0, 4)), min_size=n, max_size=n))
    return from_ticks(specs + draw(st.lists(SPEC, max_size=30)))


candles = st.one_of(candle_lists(), zigzags())
cisd_settings = st.builds(CisdSettings, memory=st.sampled_from([1, 2, 50]), tra_len=st.sampled_from([2, 14]),
                          guard=st.sampled_from([0, 200]))


def _s(cs):
    return Settings(modules=("cisd",), cisd=cs)


def _cisd(m, price=lambda p: p, flip=1):
    return [(e.bar, e.type, flip * e.dir, e.sid, e.origin_bar, round(price(e.price), 6)) for e in m.events]


@given(candles, cisd_settings)
def test_cisd_invariants_hold(candles, cs):
    m = checked("test_cisd_invariants_hold", candles, _s(cs), "property.examples")
    stats.bump("cisd.confirmed", m.cisd.confirmed)


@given(candles, cisd_settings)
def test_cisd_pine_formulation_equals_oracle(candles, cs):
    """Pine's incremental engine (CisdStack: stacks, prunes, no scan) = the approved CisdEngine."""
    from validation.models.cisd import CisdEngine, CisdStack
    from validation.models.events import EventLog
    out = []
    for cls in (CisdEngine, CisdStack):
        log = EventLog()
        e = cls(cs, 0.25, log)
        for t, c in enumerate(candles):
            log.at(t, c.time)
            e.step(t, c)
        out.append((e.recs, log.events, e.delivery))
    assert out[0] == out[1]
    stats.bump("property.examples")


@given(candles, cisd_settings)
def test_cisd_mirror_symmetry(candles, cs):
    """Reflecting prices (p → −p) swaps bullish and bearish CISDs, prices negated."""
    assert _cisd(run(mirror(candles, 0.0), _s(cs))) == _cisd(run(candles, _s(cs)), lambda p: -p, -1)
    stats.bump("property.examples")


@given(candles, cisd_settings, st.integers(-400, 400))
def test_cisd_translation_invariance(candles, cs, ticks):
    pts = ticks * 0.25
    assert _cisd(run(shift(candles, pts), _s(cs))) == _cisd(run(candles, _s(cs)), lambda p: p + pts)
    stats.bump("property.examples")


@given(candles, cisd_settings, st.data())
def test_cisd_no_lookahead(candles, cs, data):
    n = data.draw(st.integers(2, len(candles)))
    assert [e for e in run(candles, _s(cs)).events if e.bar < n] == run(candles[:n], _s(cs)).events
    stats.bump("property.examples")


@given(candles, cisd_settings, cisd_settings)
def test_cisd_guard_and_metadata_change_no_decision(candles, a, b):
    """The display guard and the body / TR length (metadata) never change events or records."""
    one, two = run(candles, _s(a)), run(candles, _s(CisdSettings(memory=a.memory, tra_len=b.tra_len, guard=b.guard)))
    strip = lambda m: [(r.bar, r.side, r.level, r.origin, r.ext_bar, r.retest, r.reclaim, r.broken, r.end)
                       for r in m.cisd.recs]
    ev = lambda m: [(e.bar, e.type, e.dir, e.sid, e.price, e.origin_bar) for e in m.events]   # audit text holds bk
    assert ev(one) == ev(two) and strip(one) == strip(two)
    stats.bump("property.examples")


@given(candles, full_settings(), cisd_settings)
def test_cisd_never_changes_other_modules(candles, s, cs):
    """Phase 1, Phase 2, LRL and HTF FVG events are identical with CISD on and off."""
    base = MODULES + ("lrl", "htf")
    off = Settings(fvg=s.fvg, liq=s.liq, modules=base)
    on = Settings(fvg=s.fvg, liq=s.liq, cisd=cs, modules=base + ("cisd",))
    assert [e for e in run(candles, on).events if not e.type.startswith("CISD_")] == run(candles, off).events
    stats.bump("property.examples")


_WALKS = {"quick": [5], "full": [5, 13, 29], "deep": [5, 13, 29, 41, 77, 101]}[MODE]


@pytest.mark.section("longwalk")
@pytest.mark.parametrize("seed", _WALKS)
def test_cisd_long_walk(seed):
    """CISD with the approved constants, every invariant (ended records swept every 25 bars)."""
    n = BUDGET["walk_bars"]
    m = checked(f"test_cisd_long_walk[s{seed}]", random_walk(n, seed, gap_prob=0.01), Settings(modules=("cisd",)),
                "longwalk.runs", seed=seed, sweep_every=25)
    stats.bump("longwalk.bars", n)
    stats.bump("cisd.confirmed", m.cisd.confirmed)
    assert m.cisd.confirmed > n / 50
