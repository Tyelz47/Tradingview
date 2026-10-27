"""Phase 1 · FVG detection and qualification (DEF-A1, DEF-A2, DEF-A3, ARCHITECTURE §6)."""
import pytest

from validation.candles import from_rows
from validation.invariants import run_checked
from validation.scenarios import ev, fvg_run, fvg_settings

pytestmark = [pytest.mark.phase1, pytest.mark.section("phase1.fvg")]

# candle 1 high 101 < candle 3 low 102 → bull zone [101, 102]; candle 1 low 103 > candle 3 high 102 → bear [102, 103]
BULL = [(100, 101, 99, 100.5), (100.5, 104, 100.5, 103.5), (103.5, 105, 102, 104.5)]
BEAR = [(104, 105, 103, 103.5), (103.5, 103.5, 100, 100.5), (100.5, 102, 99, 99.5)]
FLAT = [(100, 101, 99, 100)]


def created(m):
    return [(b, s, p) for b, t, s, p in ev(m, "FVG_CREATED")]


@pytest.mark.spec("T01", "DEF-A1", "DEF-A3")
def test_bullish_detection():
    m = fvg_run(BULL)
    assert created(m) == [(2, 2, 101.5)]
    z = m.fvg.bull[0]
    assert (z.top, z.bottom, z.mid, z.origin_bar, z.confirm_bar) == (102, 101, 101.5, 0, 2)
    assert z.id == z.confirm_time == m.candles[2].time and z.origin_time == m.candles[0].time


@pytest.mark.spec("T02", "DEF-A1")
def test_bearish_detection():
    m = fvg_run(BEAR)
    assert created(m) == [(2, 2, 102.5)]
    z = m.fvg.bear[0]
    assert (z.top, z.bottom, z.dir) == (103, 102, -1) and not m.fvg.bull


@pytest.mark.spec("DEF-A1")
def test_comparison_is_strict():
    touching = BULL[:2] + [(103.5, 105, 101, 104.5)]          # candle 3 low == candle 1 high
    assert not created(fvg_run(touching, min_ticks=1))
    overlap = BULL[:2] + [(103.5, 105, 100.75, 104.5)]
    assert not created(fvg_run(overlap, min_ticks=1))


@pytest.mark.spec("DEF-A1")
def test_no_candidate_before_candle_3():
    assert not created(fvg_run(BULL[:2]))


@pytest.mark.spec("DEF-A2", "§6")
@pytest.mark.parametrize("min_ticks, passes", [(1, True), (4, True), (5, False)])
def test_tick_minimum(min_ticks, passes):
    """Gap = 1.00 point = 4 ticks: passes for n ≤ 4, fails for n = 5 (the tolerance is 0.01 tick only)."""
    assert bool(created(fvg_run(BULL, min_ticks=min_ticks))) is passes


@pytest.mark.spec("DEF-A2", "§6")
@pytest.mark.parametrize("c3_low, passes", [(103.0, True), (102.75, False)])
def test_tr_average_threshold(c3_low, passes):
    """length 2: TR(bar1) = TR(bar2) = 2 → TR average at t−2 = 2; k = 1 → required gap 2.0 (gap = c3 low − 101)."""
    rows = FLAT * 3 + [(100, 103, 100, 103), (103, 104, c3_low, 103.5)]
    m = fvg_run(rows, min_ticks=1, k_tra=1.0, length=2)
    assert bool(created(m)) is passes
    if passes:
        assert m.fvg.bull[0].thr_tra == 2.0


TR_VS_RANGE = [(100, 101, 99, 100), (104, 105, 103, 104), (104, 105, 103, 104), (104, 108, 104, 107.5)]
# TR: bar1 = 5 (|105 − 100|), bar2 = 2 → TR average at bar 2 (length 2) = 3.5; ranges are all 2 → avg range 2.


@pytest.mark.spec("DEF-A2", "§6")
@pytest.mark.parametrize("c3_low, passes", [(107.0, True), (106.75, False)])
def test_average_range_threshold(c3_low, passes):
    m = fvg_run(TR_VS_RANGE + [(107.5, 109, c3_low, 108)], min_ticks=1, k_rng=1.0, length=2)
    assert bool(created(m)) is passes


@pytest.mark.spec("DEF-A2", "§6")
@pytest.mark.parametrize("c3_low, passes", [(108.5, True), (108.25, False), (107.0, False)])
def test_all_filters_combined_use_the_max(c3_low, passes):
    """Required = max(tick 0.25, TR 3.5, range 2.0) = 3.5: the range threshold alone would pass 107."""
    m = fvg_run(TR_VS_RANGE + [(107.5, 110, c3_low, 109)], min_ticks=1, k_tra=1.0, k_rng=1.0, length=2)
    assert bool(created(m)) is passes
    if passes:
        z = m.fvg.bull[0]
        assert (z.thr_tick, z.thr_tra, z.thr_rng) == (0.25, 3.5, 2.0)


@pytest.mark.spec("§6")
def test_reference_window_ends_at_candle_1():
    """Candle 2 (the impulse) never enters the reference: a huge candle 2 leaves the requirement unchanged."""
    calm = FLAT * 3 + [(100, 103, 100, 103), (103, 104, 103, 103.5)]
    wild = FLAT * 3 + [(100, 140, 60, 103), (103, 104, 103, 103.5)]
    a, b = fvg_run(calm, min_ticks=1, k_tra=1.0, length=2), fvg_run(wild, min_ticks=1, k_tra=1.0, length=2)
    assert created(a) and created(b) and a.fvg.bull[0].thr_tra == b.fvg.bull[0].thr_tra == 2.0


@pytest.mark.spec("§6")
def test_warmup_rejects_until_the_reference_exists():
    """k_TR > 0 and length 14: the first possible FVG is at t = len + 1 = 15."""
    gap = [(100, 103, 100, 103), (103, 106, 103.5, 105)]       # candle 2 + candle 3 (low 103.5 > 101)
    at15 = fvg_run(FLAT * 14 + gap, min_ticks=1, k_tra=0.1, length=14)
    at14 = fvg_run(FLAT * 13 + gap, min_ticks=1, k_tra=0.1, length=14)
    assert created(at15) == [(15, 15, 102.25)] and not created(at14)
    assert created(fvg_run(FLAT * 13 + gap, min_ticks=1, k_tra=0.0)), "with k_TR = 0 there is no warm-up"


@pytest.mark.spec("DEF-A2")
def test_thresholds_and_size_stored_at_birth():
    m = run_checked(from_rows(FLAT * 14 + [(100, 103, 100, 103), (103, 106, 103.5, 105)]),
                    fvg_settings(min_ticks=2, k_tra=0.1, k_rng=0.25, length=14))
    z = m.fvg.bull[0]
    assert z.thr_tick == 0.5 and abs(z.thr_tra - 0.2) < 1e-12 and abs(z.thr_rng - 0.5) < 1e-12
    assert abs(z.size_tra - (103.5 - 101) / 2.0) < 1e-12
