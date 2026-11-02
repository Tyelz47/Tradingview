"""Property tests · IFVG (docs/IFVG.md DEF-IFVG): every invariant on generated candles (Phase 1
FVG included), mirror and translation symmetry, no lookahead, the IFVG never changes another
module, and long random walks. Generated candles with gaps and fast legs make many FVGs that are
closed through (counter "ifvg.inverted")."""
import pytest
from hypothesis import given
from hypothesis import strategies as st

from validation import stats
from validation.candles import from_ticks, mirror, random_walk, shift
from validation.conftest import BUDGET, MODE
from validation.fuzz.helpers import checked, run
from validation.fuzz.strategies import SPEC, candle_lists, full_settings
from validation.models.types import MODULES, FvgSettings, IfvgSettings, Settings

pytestmark = [pytest.mark.ifvg, pytest.mark.section("property")]


@st.composite
def swings(draw):
    """Fast legs of 2–6 bars drifting ±6…20 ticks a bar, alternating, then random candles."""
    specs, d = [], draw(st.sampled_from([-1, 1]))
    for _ in range(draw(st.integers(2, 8))):
        step = d * draw(st.integers(6, 20))
        specs += draw(st.lists(st.tuples(st.sampled_from([0, 0, 0, -4, 4]), st.integers(step - 3, step + 3),
                                         st.integers(0, 3), st.integers(0, 3)), min_size=2, max_size=6))
        d = -d
    return from_ticks(specs + draw(st.lists(SPEC, max_size=30)))


candles = st.one_of(candle_lists(), swings())
ifvg_settings = st.builds(IfvgSettings, memory=st.sampled_from([1, 2, 50]))
fvg_settings = st.builds(FvgSettings, min_ticks=st.sampled_from([1, 2, 4]), k_tra=st.sampled_from([0.0, 0.1]),
                         memory=st.sampled_from([1, 3, 50]))


def _s(fs, ifs):
    return Settings(modules=("fvg", "ifvg"), fvg=fs, ifvg=ifs)


def _ifvg(m, price=lambda p: p, flip=1):
    """Canonical (sorted) IFVG events: on one bar the two sides' events come in list order, which a
    mirror swaps."""
    return sorted((e.bar, e.type, flip * e.dir, e.sid, e.origin_bar, round(price(e.price), 6)) for e in m.events
                  if e.type.startswith("IFVG_"))


@given(candles, fvg_settings, ifvg_settings)
def test_ifvg_invariants_hold(candles, fs, ifs):
    m = checked("test_ifvg_invariants_hold", candles, _s(fs, ifs), "property.examples")
    stats.bump("ifvg.inverted", m.ifvg.inverted)


@given(candles, fvg_settings, ifvg_settings)
def test_ifvg_pine_formulation_equals_oracle(candles, fs, ifs):
    """IST.pine's formulation (IfvgPine: advanceIfvg, then observeIfvg over the shadows) = the approved
    IfvgEngine: every record field, every event, the shadows = the oracle's registry."""
    from validation.models.events import EventLog
    from validation.models.fvg import FvgEngine
    from validation.models.ifvg import PRE, IfvgEngine, IfvgPine
    out = []
    for cls in (IfvgEngine, IfvgPine):
        log = EventLog()
        f = FvgEngine(fs, 0.25, log)
        e = cls(ifs, 0.25, log, f)
        for t, c in enumerate(candles):
            log.at(t, c.time)
            f.step(t, c)
            e.step(t, c)
        pine = cls is IfvgPine
        out.append(([(r.id, r.side, r.top, r.bottom, r.mid, r.bar, r.close, PRE[r.pre] if pine else r.pre,
                      *((r.touch_bar, r.ce_bar, r.full_bar, r.end_bar) if pine else (r.retest, r.ce, r.full, r.end)))
                     for r in e.records()],
                    [(x.bar, x.type, x.dir, x.sid, x.origin_bar, x.price) for x in log.events],
                    [z.id for z in e.shadows] if pine else list(e.parents)))
    assert out[0] == out[1]
    stats.bump("property.examples")


@given(candles, fvg_settings, ifvg_settings)
def test_ifvg_memory_never_changes_a_lifecycle(candles, fs, ifs):
    """DEF-IFVG8 (revised): memory drops INVALIDATED records only, so with any memory the ACTIVE IFVGs
    and every IFVG event but the drops equal those of an unlimited memory."""
    small, big = run(candles, _s(fs, ifs)), run(candles, _s(fs, IfvgSettings(memory=10 ** 6)))
    life = lambda m: [x for x in _ifvg(m) if x[1] != "IFVG_DROPPED_MEMORY"]
    active = lambda m: {(r.side, r.id) for r in m.ifvg.records() if r.end is None}
    assert life(small) == life(big) and active(small) == active(big)
    assert all(e.meta == "invalidated record" for e in small.events if e.type == "IFVG_DROPPED_MEMORY")
    stats.bump("property.examples")


@given(candles, fvg_settings, ifvg_settings)
def test_ifvg_mirror_symmetry(candles, fs, ifs):
    """Reflecting prices (p → −p) swaps bullish and bearish IFVGs, prices negated."""
    assert _ifvg(run(mirror(candles, 0.0), _s(fs, ifs))) == _ifvg(run(candles, _s(fs, ifs)), lambda p: -p, -1)
    stats.bump("property.examples")


@given(candles, fvg_settings, ifvg_settings, st.integers(-400, 400))
def test_ifvg_translation_invariance(candles, fs, ifs, ticks):
    pts = ticks * 0.25
    assert _ifvg(run(shift(candles, pts), _s(fs, ifs))) == _ifvg(run(candles, _s(fs, ifs)), lambda p: p + pts)
    stats.bump("property.examples")


@given(candles, fvg_settings, ifvg_settings, st.data())
def test_ifvg_no_lookahead(candles, fs, ifs, data):
    n = data.draw(st.integers(2, len(candles)))
    assert [e for e in run(candles, _s(fs, ifs)).events if e.bar < n] == run(candles[:n], _s(fs, ifs)).events
    stats.bump("property.examples")


@given(candles, full_settings(), ifvg_settings)
def test_ifvg_never_changes_other_modules(candles, s, ifs):
    """Phase 1 (FVG included), Phase 2, LRL, HTF FVG, CISD and displacement events are identical with
    the IFVG on and off, and the Phase 1 FVG records too."""
    base = MODULES + ("lrl", "htf", "cisd", "disp")
    off = run(candles, Settings(fvg=s.fvg, liq=s.liq, modules=base))
    on = run(candles, Settings(fvg=s.fvg, liq=s.liq, ifvg=ifs, modules=base + ("ifvg",)))
    assert [e for e in on.events if not e.type.startswith("IFVG_")] == off.events
    assert on.fvg.state() == off.fvg.state()
    stats.bump("property.examples")


_WALKS = {"quick": [5], "full": [5, 13, 29], "deep": [5, 13, 29, 41, 77, 101]}[MODE]


@pytest.mark.section("longwalk")
@pytest.mark.parametrize("seed", _WALKS)
def test_ifvg_long_walk(seed):
    """IFVG with the default Phase 1 inputs, every invariant (ended records swept every 25 bars)."""
    n = BUDGET["walk_bars"]
    m = checked(f"test_ifvg_long_walk[s{seed}]", random_walk(n, seed, gap_prob=0.01), Settings(modules=MODULES + ("ifvg",)),
                "longwalk.runs", seed=seed, sweep_every=25)
    stats.bump("longwalk.bars", n)
    stats.bump("ifvg.inverted", m.ifvg.inverted)
    assert m.ifvg.inverted > n / 50
