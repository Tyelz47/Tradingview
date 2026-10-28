"""Property tests · LRL detection (docs/LRL.md): every invariant on generated candles, mirror
and translation symmetry, no lookahead, Phase 1 / 2 untouched, and long random walks.

Generated sequences are short (≤ 160 bars), so the strategy also varies the definition's
constants (smaller pivots, gaps and TR windows): LRLs then form often enough that the
invariants are exercised, not vacuous (counter "lrl.confirmed" in the report)."""
import pytest
from hypothesis import given
from hypothesis import strategies as st

from validation import stats
from validation.candles import from_ticks, mirror, random_walk, shift
from validation.conftest import BUDGET, MODE
from validation.fuzz.helpers import checked, run
from validation.fuzz.strategies import SPEC, candle_lists, full_settings
from validation.models.types import MODULES, LiqSettings, LrlSettings, Settings

pytestmark = [pytest.mark.lrl, pytest.mark.section("property")]


@st.composite
def staircases(draw):
    """Zigzags whose legs rise less than they fall (lower highs, irregular spacing and
    pullbacks, small wicks), then random candles; mirrored half the time. LRLs form,
    extend, fail and are taken often, so every LRL path is exercised."""
    def leg(total, bars):
        base, rem = divmod(total, bars)
        wicks = draw(st.lists(st.tuples(st.integers(0, 3), st.integers(0, 3)), min_size=bars, max_size=bars))
        return [(0, base + (i < rem), u, d) for i, (u, d) in enumerate(wicks)]

    specs = [(0, 0, 1, 1)] * draw(st.integers(2, 16))
    for _ in range(draw(st.integers(3, 7))):
        rise = draw(st.integers(10, 80))
        specs += leg(rise, draw(st.integers(2, 12))) + leg(-(rise + draw(st.integers(-6, 30))), draw(st.integers(2, 12)))
    if draw(st.booleans()):                                      # falling away: the LRL can expire untouched
        specs += leg(-draw(st.integers(40, 400)), draw(st.integers(5, 40)))
    cs = from_ticks(specs + draw(st.lists(SPEC, max_size=40)))
    return mirror(cs, 0.0) if draw(st.booleans()) else cs


candles = st.one_of(candle_lists(), staircases())

lrl_settings = st.builds(LrlSettings, left=st.integers(1, 3), right=st.integers(1, 2),
                         tol_k=st.sampled_from([0.25, 0.5, 1.0]), gap=st.sampled_from([6, 15, 30]),
                         sep_k=st.sampled_from([0.0, 0.5, 1.0]), drop_k=st.sampled_from([0.0, 2.0]),
                         tra_len=st.sampled_from([2, 5, 14]), cand_memory=st.sampled_from([2, 25]),
                         memory=st.sampled_from([2, 50]))
tolerances = st.sampled_from([0, 2, 4, 8])


def _s(ls, tol):
    return Settings(modules=("lrl",), lrl=ls, liq=LiqSettings(tol_ticks=tol))


def _lrl(m, price=lambda p: p, flip=1):
    return sorted((e.bar, e.type, flip * e.dir, e.sid, e.origin_bar, None if e.price is None else round(price(e.price), 6))
                  for e in m.events if e.type.startswith("LRL_"))


@given(candles, lrl_settings, tolerances)
def test_lrl_invariants_hold(candles, ls, tol):
    m = checked("test_lrl_invariants_hold", candles, _s(ls, tol), "property.examples")
    stats.bump("lrl.confirmed", sum(side.confirmed for side in m.lrl.sides()))


@given(candles, lrl_settings, tolerances)
def test_lrl_mirror_symmetry(candles, ls, tol):
    """Reflecting prices (p → −p) swaps the bearish and bullish LRL, prices negated."""
    s = _s(ls, tol)
    assert _lrl(run(mirror(candles, 0.0), s)) == _lrl(run(candles, s), lambda p: -p, -1)
    stats.bump("property.examples")


@given(candles, lrl_settings, tolerances, st.integers(-400, 400))
def test_lrl_translation_invariance(candles, ls, tol, ticks):
    s, pts = _s(ls, tol), ticks * 0.25
    assert _lrl(run(shift(candles, pts), s)) == _lrl(run(candles, s), lambda p: p + pts)
    stats.bump("property.examples")


@given(candles, lrl_settings, tolerances, st.data())
def test_lrl_no_lookahead(candles, ls, tol, data):
    n = data.draw(st.integers(3, len(candles)))
    s = _s(ls, tol)
    assert [e for e in run(candles, s).events if e.bar < n] == run(candles[:n], s).events
    stats.bump("property.examples")


@given(candles, full_settings(), lrl_settings)
def test_lrl_never_changes_phase1_or_phase2(candles, s, ls):
    on = Settings(fvg=s.fvg, liq=s.liq, lrl=ls, modules=MODULES + ("lrl",))
    a, b = run(candles, s), run(candles, on)
    assert [e for e in b.events if not e.type.startswith("LRL_")] == a.events
    stats.bump("property.examples")


_WALKS = {"quick": [7], "full": [7, 11, 23], "deep": [7, 11, 23, 42, 99, 123]}[MODE]


@pytest.mark.section("longwalk")
@pytest.mark.parametrize("seed", _WALKS)
def test_lrl_long_walk(seed):
    """LRL with the approved constants, every invariant (records swept every 25 bars). Coexistence
    with Phase 1 / 2 is proven separately (test_lrl_never_changes_phase1_or_phase2, tests/test_lrl.py)."""
    n = BUDGET["walk_bars"]
    m = checked(f"test_lrl_long_walk[s{seed}]", random_walk(n, seed, gap_prob=0.01), Settings(modules=("lrl",)),
                "longwalk.runs", seed=seed, sweep_every=25)
    stats.bump("longwalk.bars", n)
    stats.bump("lrl.confirmed", sum(side.confirmed for side in m.lrl.sides()))
    assert sum(side.confirmed for side in m.lrl.sides()) > 0
