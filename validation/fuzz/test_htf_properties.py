"""Property tests · HTF FVG (docs/HTF_FVG.md DEF-B): every invariant on generated 1m candles,
mirror and translation symmetry, no lookahead, reload consistency (seeds = what a full
history holds open), Phase 1 / 2 / LRL untouched, and long random walks.

1m sequences drift in segments, so 15m / 30m / 1H candles gap, retrace, fill and close
through often (counter "htf.created" in the report)."""
import pytest
from hypothesis import given
from hypothesis import strategies as st

from validation import stats
from validation.candles import from_ticks, mirror, random_walk, shift
from validation.conftest import BUDGET, MODE
from validation.fuzz.helpers import checked, run
from validation.fuzz.strategies import fvg_settings, full_settings
from validation.models.types import MODULES, HtfSettings, Settings

pytestmark = [pytest.mark.htf, pytest.mark.section("property")]


@st.composite
def trends(draw, segments=(2, 10)):
    """1m candles from BASE_TIME (a 15m boundary) in 2–10 segments of 5–60 bars, each with a
    drift of −12…12 ticks a bar."""
    specs = []
    for _ in range(draw(st.integers(*segments))):
        d, n = draw(st.integers(-12, 12)), draw(st.integers(5, 60))
        specs += draw(st.lists(st.tuples(st.just(0), st.integers(d - 4, d + 4), st.integers(0, 6), st.integers(0, 6)),
                               min_size=n, max_size=n))
    return from_ticks(specs)


htf_settings = st.builds(HtfSettings, tfs=st.sampled_from([("15",), ("15", "30", "60"), HtfSettings().tfs]),
                         memory=st.sampled_from([2, 20]), seeds=st.sampled_from([1, 3]))


def _s(fs, hs):
    return Settings(modules=("htf",), fvg=fs, htf=hs)


def _htf(m, price=lambda p: p, flip=1):
    return sorted((e.bar, e.type, flip * e.dir, e.sid, e.tf, round(price(e.price), 6)) for e in m.events)


@given(trends(), fvg_settings, htf_settings)
def test_htf_invariants_hold(candles, fs, hs):
    m = checked("test_htf_invariants_hold", candles, _s(fs, hs), "property.examples")
    stats.bump("htf.created", sum(side.created for side in m.hfvg.sides))


@given(trends(), fvg_settings, htf_settings)
def test_htf_mirror_symmetry(candles, fs, hs):
    """Reflecting prices (p → −p) swaps bullish and bearish zones, prices negated."""
    s = _s(fs, hs)
    assert _htf(run(mirror(candles, 0.0), s)) == _htf(run(candles, s), lambda p: -p, -1)
    stats.bump("property.examples")


@given(trends(), fvg_settings, htf_settings, st.integers(-400, 400))
def test_htf_translation_invariance(candles, fs, hs, ticks):
    s, pts = _s(fs, hs), ticks * 0.25
    assert _htf(run(shift(candles, pts), s)) == _htf(run(candles, s), lambda p: p + pts)
    stats.bump("property.examples")


@given(trends(), fvg_settings, htf_settings, st.data())
def test_htf_no_lookahead(candles, fs, hs, data):
    n = data.draw(st.integers(3, len(candles)))
    s = _s(fs, hs)
    assert [e for e in run(candles, s).events if e.bar < n] == run(candles[:n], s).events
    stats.bump("property.examples")


@given(trends(segments=(8, 16)), fvg_settings, st.data())
def test_htf_reload_consistency(candles, fs, data):
    """Load the chart from bar k (a 15m boundary) with the bars before it as HTF context:
    the seeds are the `seeds` newest zones per direction that the full history holds open and
    unfilled at k, with the same touch / CE state, and from k on both runs agree on every
    zone the reloaded chart tracks (D2, D3, D8: the chart history never changes a zone)."""
    n = len(candles) // 15
    k = 15 * data.draw(st.integers(max(1, n // 2), max(1, n - 1)))
    s = Settings(modules=("htf",), fvg=fs, htf=HtfSettings(tfs=("15",), memory=200))
    full, part = run(candles, s), run(candles[k:], s, htf_pre=candles[:k])
    recs = run(candles[:k + 1], s).hfvg.sides[0].recs
    for d in (1, -1):
        want = [r for r in recs if r.dir == d and r.inv_bar is None and (r.full_bar is None or r.full_bar == k)][-3:]
        got = [r for r in part.hfvg.sides[0].recs if r.dir == d and r.seeded]
        assert [(r.id, r.c1_time, r.top, r.bottom, r.touch_bar is not None and r.touch_bar < k,
                 r.ce_bar is not None and r.ce_bar < k) for r in want] == \
               [(r.id, r.c1_time, r.top, r.bottom, r.pre_touch, r.pre_ce) for r in got]
    ids = {(r.dir, r.id) for r in part.hfvg.sides[0].recs}
    start = {"HTF_FVG_CREATED", "HTF_FVG_SEEDED"}
    a = sorted((e.bar, e.type, e.dir, e.sid, e.price) for e in full.events
               if e.bar >= k and (e.dir, e.sid) in ids and not (e.bar == k and e.type in start))
    b = sorted((e.bar + k, e.type, e.dir, e.sid, e.price) for e in part.events if e.type != "HTF_FVG_SEEDED")
    assert a == b
    stats.bump("property.examples")
    stats.bump("htf.seeded", part.hfvg.sides[0].seeded)


@given(trends(), full_settings(), htf_settings)
def test_htf_never_changes_other_modules(candles, s, hs):
    off = Settings(fvg=s.fvg, liq=s.liq, modules=MODULES + ("lrl",))
    on = Settings(fvg=s.fvg, liq=s.liq, htf=hs, modules=MODULES + ("lrl", "htf"))
    a, b = run(candles, off), run(candles, on)
    assert [e for e in b.events if not e.type.startswith("HTF_")] == a.events
    stats.bump("property.examples")


_WALKS = {"quick": [5], "full": [5, 13, 31], "deep": [5, 13, 31, 47, 77, 101]}[MODE]


@pytest.mark.section("longwalk")
@pytest.mark.parametrize("seed", _WALKS)
def test_htf_long_walk(seed):
    """Every timeframe with the approved settings and every invariant."""
    n = BUDGET["walk_bars"]
    m = checked(f"test_htf_long_walk[s{seed}]", random_walk(n, seed, gap_prob=0.01), Settings(modules=("htf",)),
                "longwalk.runs", seed=seed, sweep_every=25)
    stats.bump("longwalk.bars", n)
    stats.bump("htf.created", sum(side.created for side in m.hfvg.sides))
    assert sum(side.created for side in m.hfvg.sides) > 0
