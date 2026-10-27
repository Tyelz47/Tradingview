"""Phase 2 · taken, sweep, break (DEF-L4) — the fact and its single-bar classification.

Migrated from tests/liq_model.py: s_exact_touch_is_not_taken, s_wick_through_close_back_is_sweep,
s_close_exactly_at_level_is_sweep, s_close_beyond_is_break, s_break_then_reclaim_stays_break,
s_gap_through, s_one_tick_penetration, s_repeated_attacks_fire_once, s_ssl_mirror.
"""
import pytest

from validation.models.eq import BREAK, SWEEP
from validation.scenarios import SWING_HI, ev, kinds, level, liq_run

pytestmark = [pytest.mark.phase2, pytest.mark.section("phase2.sweeps")]

LO = [(100, 100.5, 98, 99), (99, 101, 98.5, 100.5)]                    # SSL 98: swing bar 20, known at 21


@pytest.mark.spec("L28", "L16", "DEF-L4")
def test_exact_touch_is_not_taken():
    m = liq_run(SWING_HI + [(99.5, 101, 99, 100), (100, 102, 99.2, 100)])
    assert not ev(m, "BSL_TAKEN") and level(m, 20).touches == 1


@pytest.mark.spec("L09", "DEF-L4")
def test_wick_through_close_back_is_sweep():
    m = liq_run(SWING_HI + [(99.5, 102.25, 99, 101.5)])
    assert kinds(m, 20) == ["CREATED", "TAKEN", "SWEEP"]
    assert ev(m, "BSL_TAKEN")[0][0] == ev(m, "BSL_SWEEP")[0][0] == 22


@pytest.mark.spec("L29", "DEF-L4")
def test_close_exactly_at_level_is_sweep():
    m = liq_run(SWING_HI + [(99.5, 102.25, 99, 102)])
    assert kinds(m, 20) == ["CREATED", "TAKEN", "SWEEP"]


@pytest.mark.spec("L11", "DEF-L4")
def test_close_beyond_is_break():
    m = liq_run(SWING_HI + [(99.5, 103, 99, 102.25)])
    assert kinds(m, 20) == ["CREATED", "TAKEN", "BREAK"]


@pytest.mark.spec("L13", "DEF-L4")
def test_break_then_reclaim_stays_break():
    m = liq_run(SWING_HI + [(99.5, 102.5, 99, 102.25), (102.25, 102.75, 100, 100.5), (100.5, 103.5, 100, 103)])
    assert kinds(m, 20) == ["CREATED", "TAKEN", "BREAK"]


@pytest.mark.spec("L30", "DEF-L4")
def test_gap_through():
    m = liq_run(SWING_HI + [(102.5, 103, 102.25, 102.75)])
    x = level(m, 20)
    assert x.take_gap and x.cls == BREAK and "opened beyond" in [e for e in m.events if e.type == "BSL_TAKEN"][0].meta


@pytest.mark.spec("DEF-L4")
def test_gap_through_and_close_back_is_sweep():
    m = liq_run(SWING_HI + [(102.5, 102.75, 101, 101.5)])
    x = level(m, 20)
    assert x.take_gap and x.cls == SWEEP


@pytest.mark.spec("DEF-L4")
def test_one_tick_penetration():
    m = liq_run(SWING_HI + [(99.5, 102.25, 99, 101)])
    assert ev(m, "BSL_TAKEN")[0][2] == 20 and level(m, 20).take_ext == 102.25
    assert ev(m, "BSL_TAKEN") and [e.meta for e in m.events if e.type == "BSL_TAKEN"] == ["+1 ticks"]


@pytest.mark.spec("L07", "L16", "DEF-L4")
def test_repeated_attacks_fire_once():
    m = liq_run(SWING_HI + [(99.5, 102.25, 99, 101), (101, 102.5, 100, 101), (101, 102.25, 100, 101.5), (101, 104, 100, 103.5)])
    for k in ("BSL_TAKEN", "BSL_SWEEP", "BSL_BREAK"):
        assert len(ev(m, k, 20)) <= 1
    assert len(ev(m, "BSL_TAKEN", 20)) == 1


@pytest.mark.spec("L08", "L10", "L12", "DEF-L4")
def test_ssl_mirror():
    m = liq_run(LO + [(100.5, 101, 97.75, 98.5)])
    assert kinds(m, 20, "SSL") == ["CREATED", "TAKEN", "SWEEP"]
    m = liq_run(LO + [(100.5, 101, 97, 97.5)])
    assert kinds(m, 20, "SSL") == ["CREATED", "TAKEN", "BREAK"]


@pytest.mark.spec("DEF-L4")
def test_several_candles_hovering_at_the_level():
    m = liq_run(SWING_HI + [(101, 102, 100, 101), (101, 102, 100.5, 101.5), (101.5, 102, 101, 101.75)])
    assert not ev(m, "BSL_TAKEN") and level(m, 20).touches == 3


@pytest.mark.spec("DEF-L4")
def test_outside_bar_takes_both_sides():
    """One bar beyond a BSL and an SSL: each level gets its own TAKEN + class."""
    rows = [(100, 102, 99.5, 101), (101, 101.5, 98, 98.5), (98.5, 100, 97, 99.5), (99.5, 100.5, 98.5, 100),
            (100, 103, 96, 99)]
    m = liq_run(rows)
    taken = {(t, s) for _, t, s, _ in ev(m) if t.endswith("_TAKEN")}
    assert {"BSL_TAKEN", "SSL_TAKEN"} <= {t for t, _ in taken}, ev(m)


@pytest.mark.spec("DEF-L4")
def test_level_cannot_be_taken_on_its_confirmation_bar():
    """DEF-L1 makes the confirmation bar ≤ the level; the take test also starts at confirm + 1."""
    m = liq_run(SWING_HI + [(99.5, 102.25, 99, 101)])
    x = level(m, 20)
    assert x.taken_bar > x.confirm_bar
