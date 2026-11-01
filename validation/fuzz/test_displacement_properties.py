"""Property tests · displacement (docs/DISPLACEMENT.md DEF-DISP): every invariant on generated
candles, mirror and translation symmetry, no lookahead, the other modules untouched (both ways),
and long random walks.

Random candles hold many dojis, gaps and equal highs (small tick integers); the trending legs
make large bodies after quiet bars, so displacements occur (counter "disp.confirmed")."""
import pytest
from hypothesis import given
from hypothesis import strategies as st

from validation import stats
from validation.candles import from_ticks, mirror, random_walk, shift
from validation.conftest import BUDGET, MODE
from validation.fuzz.helpers import checked, run
from validation.fuzz.strategies import SPEC, candle_lists, full_settings
from validation.models.types import KNOWN_MODULES, MODULES, DispSettings, Settings

pytestmark = [pytest.mark.disp, pytest.mark.section("property")]


@st.composite
def legs(draw):
    """Quiet stretches of 2–10 bars, then bursts of 1–3 bars drifting ±4…20 ticks, then random candles."""
    specs = []
    for _ in range(draw(st.integers(2, 10))):
        specs += draw(st.lists(st.tuples(st.just(0), st.integers(-2, 2), st.integers(0, 2), st.integers(0, 2)),
                               min_size=2, max_size=10))
        d = draw(st.sampled_from([-1, 1])) * draw(st.integers(4, 20))
        specs += draw(st.lists(st.tuples(st.sampled_from([0, 0, 0, -3, 3]), st.integers(d - 2, d + 2),
                                         st.integers(0, 3), st.integers(0, 3)), min_size=1, max_size=3))
    return from_ticks(specs + draw(st.lists(SPEC, max_size=30)))


candles = st.one_of(candle_lists(), legs())
disp_settings = st.builds(DispSettings, k=st.sampled_from([0.5, 1.5]), clv=st.sampled_from([0.0, 0.75]),
                          tra_len=st.sampled_from([2, 14]), memory=st.sampled_from([1, 2, 50]))


def _s(ds):
    return Settings(modules=("disp",), disp=ds)


def _disp(m, price=lambda p: p, flip=1):
    return [(e.bar, e.type, flip * e.dir, e.sid, e.origin_bar, round(price(e.price), 6)) for e in m.events]


@given(candles, disp_settings)
def test_disp_invariants_hold(candles, ds):
    m = checked("test_disp_invariants_hold", candles, _s(ds), "property.examples")
    stats.bump("disp.confirmed", m.disp.confirmed)


@given(candles, disp_settings)
def test_disp_pine_formulation_equals_oracle(candles, ds):
    """IST.pine's formulation (DispPine: global-scope A and previous extremes, factsDisp →
    f_dispHit → confirmDisp) = the approved DisplacementEngine: every record field, every event."""
    from validation.models.displacement import DispPine, DisplacementEngine
    from validation.models.events import EventLog
    out = []
    for cls in (DisplacementEngine, DispPine):
        log = EventLog()
        e = cls(ds, 0.25, log)
        for t, c in enumerate(candles):
            log.at(t, c.time)
            e.step(t, c)
        out.append(([(r.bar, r.side, r.id, r.tra, r.body_k, r.range_k, r.clv, r.prev_ext,
                      r.fvg if cls is DispPine else {None: 0, True: 1, False: -1}[r.fvg]) for r in e.recs],
                    [(x.bar, x.type, x.dir, x.sid, x.origin_bar, x.price) for x in log.events]))
    assert out[0] == out[1]
    stats.bump("property.examples")


@given(candles, disp_settings)
def test_disp_mirror_symmetry(candles, ds):
    """Reflecting prices (p → −p) swaps bullish and bearish displacements, prices negated."""
    assert _disp(run(mirror(candles, 0.0), _s(ds))) == _disp(run(candles, _s(ds)), lambda p: -p, -1)
    stats.bump("property.examples")


@given(candles, disp_settings, st.integers(-400, 400))
def test_disp_translation_invariance(candles, ds, ticks):
    pts = ticks * 0.25
    assert _disp(run(shift(candles, pts), _s(ds))) == _disp(run(candles, _s(ds)), lambda p: p + pts)
    stats.bump("property.examples")


@given(candles, disp_settings, st.data())
def test_disp_no_lookahead(candles, ds, data):
    n = data.draw(st.integers(2, len(candles)))
    assert [e for e in run(candles, _s(ds)).events if e.bar < n] == run(candles[:n], _s(ds)).events
    stats.bump("property.examples")


@given(candles, full_settings(), disp_settings)
def test_disp_never_changes_other_modules(candles, s, ds):
    """Phase 1, Phase 2, LRL, HTF FVG and CISD events are identical with displacement on and off."""
    base = MODULES + ("lrl", "htf", "cisd")
    off = Settings(fvg=s.fvg, liq=s.liq, modules=base)
    on = Settings(fvg=s.fvg, liq=s.liq, disp=ds, modules=base + ("disp",))
    assert [e for e in run(candles, on).events if not e.type.startswith("DISPLACEMENT_")] == run(candles, off).events
    stats.bump("property.examples")


@given(candles, full_settings(), disp_settings)
def test_disp_reads_no_other_module(candles, s, ds):
    """Displacement records are identical alone and with every other module on, whatever their settings."""
    alone = run(candles, _s(ds)).disp.state()
    assert run(candles, Settings(fvg=s.fvg, liq=s.liq, disp=ds, modules=KNOWN_MODULES)).disp.state() == alone
    stats.bump("property.examples")


_WALKS = {"quick": [5], "full": [5, 13, 29], "deep": [5, 13, 29, 41, 77, 101]}[MODE]


@pytest.mark.section("longwalk")
@pytest.mark.parametrize("seed", _WALKS)
def test_disp_long_walk(seed):
    """Displacement with the recommended constants, every invariant (old records swept every 25 bars)."""
    n = BUDGET["walk_bars"]
    m = checked(f"test_disp_long_walk[s{seed}]", random_walk(n, seed, gap_prob=0.01), Settings(modules=("disp",)),
                "longwalk.runs", seed=seed, sweep_every=25)
    stats.bump("longwalk.bars", n)
    stats.bump("disp.confirmed", m.disp.confirmed)
    assert m.disp.confirmed > n / 100
