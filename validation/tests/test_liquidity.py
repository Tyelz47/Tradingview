"""Phase 2 · swings, significance, BSL/SSL creation, memory (DEF-L1, L2, L3, L6).

Migrated from tests/liq_model.py (s_confirmation_timing, s_flat_top_one_swing,
s_significance_filter, s_memory_policy) plus new swing/significance cases.
"""
import pytest

from validation.candles import WARM, from_rows
from validation.invariants import run_checked
from validation.models.types import PRESETS, LiqSettings, Settings
from validation.scenarios import SWING_HI, ev, liq_run, liq_settings

pytestmark = [pytest.mark.phase2, pytest.mark.section("phase2.swing")]


@pytest.mark.spec("L01", "L03", "L14", "DEF-L1")
def test_confirmation_timing():
    """Swing bar 20 (origin) is known only at the close of 20 + right = 21 (confirmation)."""
    m = liq_run(SWING_HI)
    assert [(b, t, s, p) for b, t, s, p in ev(m)] == [(21, "BSL_CREATED", 20, 102)]
    x = m.liq.bsl.live[0]
    assert (x.origin_bar, x.confirm_bar, x.price) == (20, 21, 102)
    assert x.id == m.candles[20].time and x.confirm_time == m.candles[21].time


@pytest.mark.spec("L01", "DEF-L1")
def test_origin_vs_confirmation_latency_equals_right():
    rows = [(100, 102, 99.5, 101), (101, 101.5, 99, 99.5), (99.5, 100, 98.5, 99), (99, 99.5, 98, 98.5)]
    for R in (1, 2, 3):
        m = liq_run(rows, L=2, R=R)
        created = ev(m, "BSL_CREATED")
        assert created == [(20 + R, "BSL_CREATED", 20, 102)], (R, created)


@pytest.mark.spec("DEF-L1")
def test_flat_top_one_swing():
    """Plateau rule: adjacent equal highs give one swing, at the first bar."""
    m = liq_run([(100, 102, 99.5, 101), (101, 102, 99.5, 101), (101, 101, 99.2, 100), (100, 100.5, 99.3, 100)])
    assert [(s, p) for _, _, s, p in ev(m, "BSL_CREATED")] == [(20, 102)]


@pytest.mark.spec("DEF-L1")
def test_left_strict_right_non_strict():
    # equal high inside the LEFT window (bar 19 = 101 in WARM is below; build our own) → no swing
    rows = [(100, 102, 99.5, 101), (101, 101, 99, 99.5), (99.5, 102, 99, 100), (100, 100.5, 98.5, 99)]
    m = liq_run(rows, L=2, R=1)
    # bar 22 = 102 equals bar 20 inside its left window (strict) → only bar 20 is a swing
    assert [s for _, _, s, _ in ev(m, "BSL_CREATED")] == [20]
    # a higher bar in the RIGHT window kills the swing; an equal one does not
    hi_right = liq_run([(100, 102, 99.5, 101), (101, 102.25, 99, 99.5), (99.5, 100, 98, 98.5)], L=2, R=1)
    assert 20 not in [s for _, _, s, _ in ev(hi_right, "BSL_CREATED")]


@pytest.mark.spec("L02", "L04", "DEF-L1")
def test_ssl_created_at_low():
    lo = [(100, 100.5, 98, 99), (99, 101, 98.5, 100.5)]
    m = liq_run(lo)
    assert ev(m, "SSL_CREATED") == [(21, "SSL_CREATED", 20, 98)]


@pytest.mark.spec("L33", "DEF-L2")
def test_significance_filter():
    weak = liq_run([(100, 102, 99.5, 101), (101, 101.75, 100.5, 101)], K=1.0)    # reaction 1.5 < ~2.04
    strong = liq_run([(100, 102, 99.5, 101), (101, 101.75, 99, 99.5)], K=1.0)    # reaction 3.0
    assert weak.liq.bsl.pivots == 1 and weak.liq.bsl.rejects == 1 and not weak.liq.bsl.live
    assert strong.liq.bsl.live and abs(strong.liq.bsl.live[0].react_req - 2.0357142857) < 1e-6


@pytest.mark.spec("DEF-L2")
def test_warmup_pivots_are_neither_pass_nor_reject():
    """While the TR average is warming up (first 14 bars) a pivot is counted but not judged."""
    rows = [(100, 101, 99, 100), (100, 103, 99.5, 101), (101, 101.5, 98, 98.5), (98.5, 99, 97, 97.5)]
    m = run_checked(from_rows(rows), liq_settings(L=1, R=1, K=0.0))
    s = m.liq.bsl
    assert s.pivots == 1 and s.levels == 0 and s.rejects == 0, (s.pivots, s.levels, s.rejects)


@pytest.mark.spec("L32", "DEF-L3")
def test_presets_are_the_documented_numbers():
    assert PRESETS == {"aggressive": (3, 2, 0.5), "balanced": (5, 3, 1.0), "strict": (10, 5, 2.0)}
    b = LiqSettings.preset("balanced")
    assert (b.left, b.right, b.k) == (5, 3, 1.0) and LiqSettings() == b


@pytest.mark.spec("DEF-L2")
def test_selectivity_counters_add_up():
    from validation.candles import random_walk
    m = run_checked(random_walk(3000, 3), Settings(modules=("liq",)), sweep_every=25)
    for s in m.liq.sides():
        warm = s.pivots - s.levels - s.rejects
        assert 0 <= warm <= 3 and s.levels == len([e for e in m.events if e.type == f"{s.name}_CREATED"])


@pytest.mark.spec("DEF-L6")
def test_memory_policy():
    """Deliberate, logged drops: the oldest live record when nothing is closed, else the oldest closed."""
    rows, p = [], 102.0
    for _ in range(6):                       # 6 lower highs (swing bars 20, 23, …, 35), never taken
        p -= 0.5
        rows += [(p - 1, p, p - 2, p - 1.5), (p - 1.5, p - 2, p - 4, p - 3.5), (p - 3.5, p - 2.5, p - 5, p - 4)]
    m = liq_run(rows, memory=3, tol_ticks=0)
    drops = ev(m, "BSL_DROPPED_MEMORY")
    assert len(drops) == 3 and len(m.liq.bsl.live) == 3 and not m.liq.bsl.hist, drops
    assert [s for _, _, s, _ in drops] == [20, 23, 26]
    m2 = liq_run(SWING_HI + [(99.5, 104, 99, 103.5), (103.5, 106, 103, 105.5), (105.5, 105, 102, 102.5)], memory=1)
    assert [s for _, _, s, _ in ev(m2, "BSL_DROPPED_MEMORY")] == [20]


@pytest.mark.spec("DEF-L1")
def test_no_pivots_during_window_warmup():
    m = run_checked(from_rows(WARM[:3] + [(100, 105, 99, 100)]), liq_settings(L=5, R=1))
    assert m.liq.bsl.pivots == 0
