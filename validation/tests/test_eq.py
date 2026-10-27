"""Phase 2 · EQH / EQL clusters (DEF-L5.1…L5.6): L17–L21 and L35–L42.

Migrated from tests/liq_model.py: s_eqh_second_lower_within_tol, s_eqh_second_higher_within_tol,
s_outside_tolerance_no_cluster, s_cluster_does_not_duplicate_and_taken_once,
s_pool_not_intact_no_cluster and s_L35 … s_L42.
"""
import pytest

from validation.models.eq import SWEEP
from validation.scenarios import (EQ_AB, EQ_BASE, EQL_AB, QUIET_HI, QUIET_LO, ev, expand, feed, level, liq_run,
                                  members, sid_bar)

pytestmark = [pytest.mark.phase2, pytest.mark.section("phase2.eq")]


@pytest.mark.spec("L17", "DEF-L5.2")
def test_eqh_second_lower_within_tol():
    m = liq_run(EQ_BASE + [(98, 101.5, 97.8, 101), (101, 101, 99, 99.5)])
    c = m.liq.bsl.eqs[0]
    assert ev(m, "EQH_CREATED") and c.ref == c.bound == 102 and members(m, c) == [20, 24]


@pytest.mark.spec("L17", "L37", "DEF-L5.2")
def test_eqh_second_higher_within_tol():
    m = liq_run(EQ_AB)
    assert [t for _, t, s, _ in ev(m) if s == 20 and t.startswith("BSL")] == ["BSL_CREATED", "BSL_TAKEN", "BSL_SWEEP"]
    c = m.liq.bsl.eqs[0]
    assert c.ref == c.bound == 102.25 and members(m, c) == [20, 24]


@pytest.mark.spec("L18", "DEF-L5.2")
def test_eql_within_tol_line_at_lower_price():
    m = liq_run(EQL_AB)
    c = m.liq.ssl.eqs[0]
    assert ev(m, "EQL_CREATED") and c.bound == 97.75 and members(m, c) == [20, 24]


@pytest.mark.spec("L19", "DEF-L5.2")
def test_outside_tolerance_no_cluster():
    m = liq_run(EQ_BASE + [(98, 100.75, 97.8, 100.5), (100.5, 100.5, 99, 99.5)])   # 5 ticks below
    assert ev(m, "BSL_CREATED", 24) and not m.liq.bsl.eqs


@pytest.mark.spec("DEF-L5.2")
def test_tolerance_boundary_exactly_n_ticks_joins():
    m = liq_run(EQ_BASE + [(98, 101, 97.8, 100.5), (100.5, 100.5, 99, 99.5)])       # exactly 4 ticks below
    assert m.liq.bsl.eqs and members(m, m.liq.bsl.eqs[0]) == [20, 24]


@pytest.mark.spec("L20", "L21", "DEF-L5.2")
def test_cluster_does_not_duplicate_and_taken_once():
    rows = EQ_BASE + [(98, 101.5, 97.8, 101), (101, 101, 99, 99.5),
                      (99.5, 100, 98.5, 99), (99, 99.25, 98.6, 99), (99, 101.75, 98.7, 101), (101, 101.25, 100, 100.5),
                      (100.5, 102.25, 100.2, 101.75), (101.75, 103, 101, 102.5)]
    m = liq_run(rows)
    assert len(m.liq.bsl.eqs) == 1 and members(m, m.liq.bsl.eqs[0]) == [20, 24, 28]
    assert len(ev(m, "EQH_CREATED")) == 1 and len(ev(m, "EQH_TAKEN")) == 1
    assert ev(m, "EQH_TAKEN")[0][0] == 30 and m.liq.bsl.eqs[0].cls == SWEEP


@pytest.mark.spec("DEF-L5.2")
def test_pool_not_intact_no_cluster():
    # 102 taken at bar 24 (furthest 102.5, rejected pivot: reaction too small); new swing 102.25 < 102.5
    rows = EQ_BASE + [(98, 102.5, 97.8, 102.3), (102.25, 102.25, 102, 102), (102, 102, 101, 101.25),
                      (101.25, 101.5, 100.5, 101), (101, 101.5, 100.5, 101), (101, 102.25, 100.75, 102),
                      (102, 102, 99.5, 100)]
    m = liq_run(rows, K=1.0)
    assert ev(m, "BSL_CREATED", 20) and not ev(m, "BSL_CREATED", 24), "102.5 must be rejected (small reaction)"
    assert ev(m, "BSL_CREATED", 29), "102.25 must become a level"
    assert not m.liq.bsl.eqs, "102 was traded beyond 102.25: no intact pool"


@pytest.mark.spec("DEF-L5.2")
def test_join_nearest_active_cluster():
    """Two active clusters within tolerance of a new swing: it joins the nearer one."""
    rows = EQ_BASE + [(98, 101.5, 97.8, 101), (101, 101, 99, 99.5)]           # EQH 102 {20, 24}
    m = liq_run(rows + [(99.5, 100, 98.5, 99), (99, 99.25, 98.6, 99), (99, 101.75, 98.7, 101), (101, 101.25, 100, 100.5)])
    assert members(m, m.liq.bsl.eqs[0]) == [20, 24, 28] and len(m.liq.bsl.eqs) == 1


@pytest.mark.spec("DEF-L5.6")
def test_group_below_minimum_ends_silently():
    """minimum 3: a 2-member group traded through emits nothing (it never was an EQH)."""
    m = liq_run(EQ_AB + QUIET_HI + [(99, 102.5, 98.7, 101), (101, 101.25, 99, 99.5)], min_touch=3)
    c = m.liq.bsl.eqs[0]
    assert c.qual_bar is None and c.taken_bar == 28 and not ev(m, ("EQH_CREATED", "EQH_TAKEN"))


# ── L35-L42: identity vs boundary, individual vs cluster liquidity ──
@pytest.mark.spec("L35", "DEF-L5.4")
def test_L35_eqh_boundary_expands_upward():
    # Real prices: a third, slightly higher swing C = 102.5 (1 tick beyond, inside tolerance)
    # has to trade through the known boundary first → EQH taken once at C's bar, at the
    # boundary it had then; C becomes a separate BSL. The boundary never moved.
    C = QUIET_HI + [(99, 102.5, 98.7, 101), (101, 101.25, 99, 99.5)]       # C prints at 28, confirms at 29
    for mt in (2, 3):
        m = liq_run(EQ_AB + C, min_touch=mt)
        c = m.liq.bsl.eqs[0]
        assert len(m.liq.bsl.eqs) == 1 and sid_bar(m, c.id) == 25 and c.ref == c.bound == 102.25
        assert members(m, c) == [20, 24] and c.taken_bar == 28 and level(m, 28).eq is None
        assert [(b, p) for b, _, _, p in ev(m, "EQH_TAKEN")] == ([(28, 102.25)] if mt == 2 else [])
    # Join path (test hook): a member beyond the boundary → same id and ref, count + 1, new boundary.
    m = liq_run(EQ_AB + QUIET_HI)
    c = m.liq.bsl.eqs[0]
    x = expand(m, True, 102.5)
    assert x.eq is c and sid_bar(m, c.id) == 25 and c.ref == 102.25 and c.bound == 102.5
    assert members(m, c) == [20, 24, 27] and c.last_bar == 27 and c.active


@pytest.mark.spec("L36", "DEF-L5.4")
def test_L36_eql_boundary_expands_downward():
    C = QUIET_LO + [(101, 101.3, 97.5, 99), (99, 100.5, 98, 100)]         # C = 97.5 prints at 28, confirms at 29
    m = liq_run(EQL_AB + C)
    c = m.liq.ssl.eqs[0]
    assert sid_bar(m, c.id) == 25 and c.ref == c.bound == 97.75 and members(m, c) == [20, 24] and c.taken_bar == 28
    assert [(b, p) for b, _, _, p in ev(m, "EQL_TAKEN")] == [(28, 97.75)]
    m = liq_run(EQL_AB + QUIET_LO)
    c = m.liq.ssl.eqs[0]
    expand(m, False, 97.5)
    assert sid_bar(m, c.id) == 25 and c.ref == 97.75 and c.bound == 97.5 and members(m, c) == [20, 24, 27]


@pytest.mark.spec("L37", "DEF-L5.3")
def test_L37_individual_take_does_not_clear_cluster():
    m = liq_run(EQ_AB + QUIET_HI)
    a = level(m, 20)
    c = m.liq.bsl.eqs[0]
    assert a.taken_bar == 24 and a.cls == SWEEP, "individual swing A: TAKEN (by B's bar)"
    assert c.active and c.bound == 102.25 and not ev(m, "EQH_TAKEN"), "EQH: ACTIVE at max(A, B)"


@pytest.mark.spec("L38", "DEF-L5.5")
def test_L38_no_retroactive_cluster_take():
    m = liq_run(EQ_AB + QUIET_HI)
    assert not ev(m, "EQH_TAKEN"), "B's own bar (102.25 > A) never takes the cluster it later forms"
    c = m.liq.bsl.eqs[0]
    expand(m, True, 102.5)                             # boundary 102.25 → 102.5, known from bar 27's close
    feed(m, [(99, 102.4, 98.7, 101), (101, 102.5, 100, 101)])   # beyond the old boundary, not the new one
    assert c.active and not ev(m, "EQH_TAKEN"), "only price beyond the CURRENT boundary takes"


@pytest.mark.spec("L39", "DEF-L5.5")
def test_L39_eqh_taken_once_beyond_boundary():
    m = liq_run(EQ_AB + QUIET_HI + [(99, 102.5, 98.7, 101), (101, 103, 100.5, 102.75), (102.75, 104, 102, 103.5)])
    assert [(b, s, p) for b, _, s, p in ev(m, "EQH_TAKEN")] == [(28, 25, 102.25)]
    assert m.liq.bsl.eqs[0].cls == SWEEP
    m = liq_run(EQ_AB + QUIET_HI)                      # same with an expanded boundary
    expand(m, True, 102.5)
    feed(m, [(99, 102.5, 98.7, 101), (101, 102.75, 100, 101), (101, 103, 100, 102.9)])
    assert [(b, p) for b, _, _, p in ev(m, "EQH_TAKEN")] == [(29, 102.5)]


@pytest.mark.spec("L40", "DEF-L5.5")
def test_L40_eql_taken_once_beyond_boundary():
    m = liq_run(EQL_AB + QUIET_LO + [(101, 101.3, 97.5, 99), (99, 99.5, 97, 97.25), (97.25, 98, 96, 96.5)])
    assert [(b, s, p) for b, _, s, p in ev(m, "EQL_TAKEN")] == [(28, 25, 97.75)]
    m = liq_run(EQL_AB + QUIET_LO)
    expand(m, False, 97.5)
    feed(m, [(101, 101.3, 97.5, 99), (99, 99.5, 97.25, 99), (99, 99.5, 97, 97.1)])
    assert [(b, p) for b, _, _, p in ev(m, "EQL_TAKEN")] == [(29, 97.5)]


@pytest.mark.spec("L41", "DEF-L5.1")
def test_L41_cluster_id_stable():
    m = liq_run(EQ_AB + QUIET_HI)
    c = m.liq.bsl.eqs[0]
    before = (c.id, c.ref, c.origin_bar, c.first_confirm_bar, c.members[:2], c.qual_bar)
    expand(m, True, 102.5)
    assert (c.id, c.ref, c.origin_bar, c.first_confirm_bar, c.members[:2], c.qual_bar) == before
    assert [s for _, _, s, _ in ev(m, "EQH_CREATED")] == [25]


@pytest.mark.spec("L42", "DEF-L5.2")
def test_L42_boundary_change_no_duplicate():
    m = liq_run(EQ_AB + QUIET_HI)
    n = len(m.events)
    expand(m, True, 102.5)
    assert len(m.liq.bsl.eqs) == 1 and [e.type for e in m.events[n:]] == ["BSL_CREATED"], "no new cluster, no EQ event"
    m = liq_run(EQ_AB + QUIET_HI + [(99, 102.5, 98.7, 101), (101, 101.25, 99, 99.5)] + QUIET_HI
                + [(99, 102.4, 98.7, 101), (101, 101, 99, 99.5)])          # D = 102.4 (bar 32) next to C = 102.5
    assert [(sid_bar(m, c.id), members(m, c)) for c in m.liq.bsl.eqs] == [(25, [20, 24]), (33, [28, 32])], "new pool = new id"


@pytest.mark.spec("DEF-L5.6")
def test_cluster_memory_drop_releases_active_members():
    """Cluster memory 1: forming a 2nd pool releases the 1st (logged) and frees its members."""
    second = [(99, 100.5, 98.7, 100), (100, 100.25, 99, 99.5)]          # swing 100.5 (7 ticks below EQH 102.25)
    m = liq_run(EQ_AB + QUIET_HI + second + QUIET_HI + second, eq_memory=1)
    assert ev(m, "EQH_DROPPED_MEMORY") == [(33, "EQH_DROPPED_MEMORY", 25, 102.25)]
    assert [(sid_bar(m, c.id), members(m, c)) for c in m.liq.bsl.eqs] == [(33, [28, 32])]
    assert level(m, 20).eq is None and level(m, 24).eq is None
