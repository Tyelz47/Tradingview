"""Property tests · Phase 2 liquidity and EQ, plus the whole model and the long random walks."""
import pytest
from hypothesis import given
from hypothesis import strategies as st

from validation import stats
from validation.candles import mirror, random_walk, shift
from validation.conftest import BUDGET
from validation.fuzz.helpers import checked, compare, event_set, mirrored, run, shifted
from validation.fuzz.strategies import candle_lists, full_settings, liq_settings, view_settings
from validation.models.types import FvgSettings, LiqSettings, Settings

pytestmark = [pytest.mark.phase2, pytest.mark.section("property")]
LIQ_ONLY = ("liq",)


@given(candle_lists(), liq_settings)
def test_liquidity_invariants_hold(candles, ls):
    checked("test_liquidity_invariants_hold", candles, Settings(modules=LIQ_ONLY, liq=ls), "property.examples")


@given(candle_lists(), full_settings())
def test_whole_model_invariants_hold(candles, s):
    checked("test_whole_model_invariants_hold", candles, s, "property.examples")


@given(candle_lists(), liq_settings)
def test_liquidity_mirror_symmetry(candles, ls):
    """Reflecting prices swaps BSL↔SSL and EQH↔EQL with reflected prices; nothing else changes."""
    s = Settings(modules=LIQ_ONLY, liq=ls)
    pivot = 20000.0
    a, b = run(candles, s), run(mirror(candles, pivot), s)
    compare("test_liquidity_mirror_symmetry", candles, s, mirrored(event_set(a), pivot), event_set(b), "mirror symmetry")
    stats.bump("property.examples")


@given(candle_lists(), liq_settings, st.integers(-400, 400))
def test_liquidity_translation_invariance(candles, ls, ticks):
    s = Settings(modules=LIQ_ONLY, liq=ls)
    pts = ticks * 0.25
    a, b = run(candles, s), run(shift(candles, pts), s)
    compare("test_liquidity_translation_invariance", candles, s, shifted(event_set(a), pts), event_set(b),
            "translation invariance")
    stats.bump("property.examples")


@given(candle_lists(), liq_settings)
def test_pine_trigger_gate_equals_full_scan(candles, ls):
    """Pine skips the scan on quiet bars (trigger price). That optimisation must change nothing."""
    s = Settings(modules=LIQ_ONLY, liq=ls)
    assert run(candles, s).events == run(candles, s, incremental_liq=True).events
    stats.bump("property.examples")


@given(candle_lists(min_size=12), liq_settings, st.data())
def test_liquidity_no_lookahead(candles, ls, data):
    n = data.draw(st.integers(3, len(candles)))
    s = Settings(modules=LIQ_ONLY, liq=ls)
    full, prefix = run(candles, s), run(candles[:n], s)
    assert [e for e in full.events if e.bar < n] == prefix.events
    stats.bump("property.examples")


@given(candle_lists(), liq_settings, view_settings)
def test_liquidity_view_settings_do_not_change_logic(candles, ls, view):
    a = run(candles, Settings(modules=LIQ_ONLY, liq=ls))
    b = run(candles, Settings(modules=LIQ_ONLY, liq=ls, view=view))
    assert a.canonical_events() == b.canonical_events() and a.state() == b.state()
    stats.bump("property.examples")


# ── long random walks (migrated tests/liq_model.py fuzz), scaled by --mode ──
CONFIGS = [  # name, liquidity settings, FVG settings
    ("balanced", LiqSettings(), FvgSettings()),
    ("aggressive-tol8", LiqSettings.preset("aggressive", tol_ticks=8), FvgSettings(k_tra=0.25)),
    ("strict-min3", LiqSettings.preset("strict", min_touch=3), FvgSettings(k_rng=0.25)),
    ("balanced-tol8-min3-eqmem3", LiqSettings(tol_ticks=8, min_touch=3, eq_memory=3), FvgSettings(memory=10)),
]
_RUNS = {"quick": [(0, 7)],
         "full": [(0, 7), (0, 11), (0, 23), (0, 42), (1, 7), (2, 7), (3, 7)],
         "deep": [(c, s) for c in range(4) for s in (7, 11, 23)] + [(0, 42), (0, 99)]}[
    __import__("validation.conftest", fromlist=["MODE"]).MODE]


@pytest.mark.section("longwalk")
@pytest.mark.parametrize("cfg, seed", _RUNS, ids=[f"{CONFIGS[c][0]}-s{s}" for c, s in _RUNS])
def test_long_walk(cfg, seed):
    name, liq, fvg = CONFIGS[cfg]
    n = BUDGET["walk_bars"]
    candles = random_walk(n, seed, gap_prob=0.01)
    s = Settings(liq=liq, fvg=fvg)
    m = checked(f"test_long_walk[{name}-s{seed}]", candles, s, "longwalk.runs", seed=seed, sweep_every=25)
    stats.bump("longwalk.bars", n)
    a = run(candles, Settings(modules=LIQ_ONLY, liq=liq))
    b = run(candles, Settings(modules=LIQ_ONLY, liq=liq), incremental_liq=True)
    assert a.events == b.events, "Pine trigger gate changed the result"
    sel = stats.RESULTS.setdefault("selectivity", [])
    for side in m.liq.sides():
        judged = side.levels + side.rejects
        sel.append({"run": f"{name} s{seed}", "bars": n, "side": side.name, "pivots": side.pivots, "pass": side.levels,
                    "reject": side.rejects, "reject_pct": round(100 * side.rejects / judged, 1) if judged else 0.0})
