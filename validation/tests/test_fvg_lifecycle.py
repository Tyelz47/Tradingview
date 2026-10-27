"""Phase 1 · FVG lifecycle (DEF-A3…A7, §3.3): milestones, invalidation, policy, memory."""
import pytest

from validation.candles import from_rows
from validation.invariants import run_checked
from validation.models.types import MIT_RULES, Settings, ViewSettings
from validation.scenarios import ev, fvg_run, fvg_settings

pytestmark = [pytest.mark.phase1, pytest.mark.section("phase1.lifecycle")]

BULL = [(100, 101, 99, 100.5), (100.5, 104, 100.5, 103.5), (103.5, 105, 102, 104.5)]   # zone [101, 102], CE 101.5
BEAR = [(104, 105, 103, 103.5), (103.5, 103.5, 100, 100.5), (100.5, 102, 99, 99.5)]    # zone [102, 103], CE 102.5
STEPS = [(104.5, 105, 101.75, 102.5),    # 3: low 101.75 ≤ top → first touch
         (102.5, 103, 101.5, 102),       # 4: low 101.5 ≤ CE → CE touch
         (102, 102.5, 101, 101.25),      # 5: low 101 ≤ bottom → full fill (close 101.25 stays inside)
         (101.25, 101.5, 100.5, 101),    # 6: close == bottom → NOT invalidated (strictly beyond needed)
         (101, 101.25, 100, 100.25),     # 7: close < bottom → invalidated
         (100.25, 102, 99, 101.5)]       # 8: after invalidation nothing more


def milestones(m):
    return [(b, t) for b, t, s, p in ev(m) if t != "FVG_CREATED"]


@pytest.mark.spec("T03", "DEF-A4")
def test_milestones_in_sequence():
    m = fvg_run(BULL + STEPS)
    assert milestones(m) == [(3, "FVG_FIRST_TOUCH"), (4, "FVG_CE_TOUCH"), (5, "FVG_FULL_FILL"), (7, "FVG_INVALIDATED")]
    z = m.fvg.bull[0]
    assert (z.touch_bar, z.ce_bar, z.full_bar, z.inv_bar) == (3, 4, 5, 7) and not z.is_open
    prices = {t: p for _, t, _, p in ev(m)}
    assert prices["FVG_FIRST_TOUCH"] == 102 and prices["FVG_CE_TOUCH"] == 101.5 and prices["FVG_FULL_FILL"] == 101
    assert prices["FVG_INVALIDATED"] == 100.25


@pytest.mark.spec("DEF-A3")
def test_creating_candle_never_touches():
    """Candle 3's low IS the top; milestones start at confirmation + 1."""
    m = fvg_run(BULL)
    assert m.fvg.bull[0].touch_bar is None and not milestones(m)


@pytest.mark.spec("DEF-A7")
def test_same_bar_milestones_in_rule_order():
    m = fvg_run(BULL + [(104.5, 104.5, 100, 100.5)])
    assert milestones(m) == [(3, "FVG_FIRST_TOUCH"), (3, "FVG_CE_TOUCH"), (3, "FVG_FULL_FILL"), (3, "FVG_INVALIDATED")]
    assert [e.type for e in m.events if e.bar == 3] == ["FVG_FIRST_TOUCH", "FVG_CE_TOUCH", "FVG_FULL_FILL", "FVG_INVALIDATED"]


@pytest.mark.spec("DEF-A4")
def test_each_milestone_once_under_repeated_attacks():
    rows = BULL + [(104.5, 105, 101.75, 102.5)] * 3 + [(102.5, 103, 101.5, 102)] * 3
    m = fvg_run(rows)
    assert milestones(m) == [(3, "FVG_FIRST_TOUCH"), (6, "FVG_CE_TOUCH")]


@pytest.mark.spec("DEF-A4")
def test_bear_mirror():
    rows = BEAR + [(99.5, 102, 99, 101), (101, 102.5, 100.5, 102), (102, 103, 101.5, 102.5), (102.5, 103.5, 102, 103.25)]
    m = fvg_run(rows)
    assert milestones(m) == [(3, "FVG_FIRST_TOUCH"), (4, "FVG_CE_TOUCH"), (5, "FVG_FULL_FILL"), (6, "FVG_INVALIDATED")]


@pytest.mark.spec("DEF-A5")
def test_mitigation_policy_reads_milestones_only():
    m = fvg_run(BULL + STEPS)
    z = m.fvg.bull[0]
    assert [z.policy_bar(r) for r in MIT_RULES] == [3, 4, 5, 7]
    assert z.active_at(2, "fullFill") and z.active_at(4, "fullFill") and not z.active_at(5, "fullFill")
    assert not z.active_at(1, "firstTouch"), "not active before confirmation"


@pytest.mark.spec("DEF-A5", "ARCH §2")
@pytest.mark.parametrize("view", [ViewSettings(mit_rule=r) for r in MIT_RULES] +
                         [ViewSettings(fvg_show=False, minimal=True, fvg_max_visible=1)])
def test_view_settings_never_change_logical_state(view):
    rows = BULL + STEPS + BEAR
    base = run_checked(from_rows(rows), fvg_settings())
    other = run_checked(from_rows(rows), fvg_settings().with_(view=view))
    assert base.canonical_events() == other.canonical_events() and base.state() == other.state()


def staircase(n, start=0):
    """Bar i: (100+2i, 101+2i, 99+2i, 100.5+2i). Every bar from 2 on creates a bull FVG of 2 points."""
    return [(100 + 2 * i, 101 + 2 * i, 99 + 2 * i, 100.5 + 2 * i) for i in range(start, start + n)]


@pytest.mark.spec("DEF-A6", "§3.3")
def test_memory_releases_oldest_open_when_nothing_is_closed():
    m = fvg_run(staircase(13), memory=10)
    drops = ev(m, "FVG_DROPPED_MEMORY")
    assert [(b, s) for b, _, s, _ in drops] == [(12, 2)] and m.fvg.drop_open == 1 and len(m.fvg.bull) == 10
    assert [e.meta for e in m.events if e.type == "FVG_DROPPED_MEMORY"] == ["open record · lifecycle tracking stopped"]


@pytest.mark.spec("DEF-A6", "§3.3")
def test_memory_releases_oldest_closed_first():
    dip = [(114.5, 114.5, 109.5, 110)]                         # bar 8 invalidates only the FVG of bar 7
    rows = staircase(8) + dip + staircase(5, start=9)
    m = fvg_run(rows, memory=10)
    assert [(b, t) for b, t, s, _ in ev(m) if s == 7 and t == "FVG_INVALIDATED"] == [(8, "FVG_INVALIDATED")]
    drops = ev(m, "FVG_DROPPED_MEMORY")
    assert [(b, s) for b, _, s, _ in drops] == [(13, 7)] and m.fvg.drop_closed == 1 and m.fvg.drop_open == 0


@pytest.mark.spec("DEF-A6")
def test_closed_record_stays_in_memory_and_is_not_advanced():
    m = fvg_run(BULL + STEPS + [(101.5, 103, 98, 99)])
    z = m.fvg.bull[0]
    assert not z.is_open and z in m.fvg.bull and z.extreme == 100  # extreme frozen at the invalidation bar


def test_fill_extreme_tracks_deepest_penetration():
    m = fvg_run(BULL + STEPS[:3])
    assert m.fvg.bull[0].extreme == 101
