"""LRL research study (validation/studies/lrl.py, docs/STUDY_LRL.md): the harness is
trustworthy. Synthetic scenarios give the specified events, every guard rule is
load-bearing, bullish = mirrored bearish, no decision uses a later bar, and the frozen
Phase 2 engine is only read. No indicator or oracle change is tested here."""
from dataclasses import replace

import pytest

from validation.candles import mirror, random_walk
from validation.studies import lrl

pytestmark = [pytest.mark.section("research.lrl")]
R = lrl.RECOMMENDED
C, X, S, B, E = "LRL_CONFIRMED", "LRL_EXTENDED", "LRL_SWEEP", "LRL_BREAK", "LRL_EXPIRED"

# LRL-R: (bar, event, side, anchor bar, points). Pivots 3/2: a point at X is known at X + 2;
# a record expires on the first bar after X_last + gmax (30) + right (2).
EXPECTED = {
    "clean bearish LRL": [(84, C, "bear", 50, 3), (115, E, "bear", 50, 3)],
    "two failure swings only (internal candidate)": [],
    "4th and 5th point extension": [(84, C, "bear", 50, 3), (100, X, "bear", 50, 4), (116, X, "bear", 50, 5),
                                    (147, E, "bear", 50, 5)],
    "line touch → extension": [(84, C, "bear", 50, 3), (100, X, "bear", 50, 4), (131, E, "bear", 50, 4)],
    "sweep (wick through, close back)": [(84, C, "bear", 50, 3), (93, S, "bear", 50, 3)],
    "break (close beyond)": [(84, C, "bear", 50, 3), (93, B, "bear", 50, 3)],
    "pivot beyond the line": [(84, C, "bear", 50, 3), (96, S, "bear", 50, 3)],
    "false candidate: 3rd high below the line": [],
    "false candidate: 3rd high above the line": [],
    "equal highs, then a staircase": [(100, C, "bear", 66, 3), (131, E, "bear", 66, 3)],
    "range: equal-ish highs (steps ≤ EQ tolerance)": [],
    "strong trend, collinear highs": [(76, C, "bear", 50, 3), (107, S, "bear", 50, 3)],
    "strong trend, accelerating highs": [],
    "micro-pivots (collinear, 0.75-point pullbacks)": [],
    "shallow staircase (drop ≤ 2τ)": [],
    "points too far apart": [],
    "triangle: bearish and bullish together": [(84, C, "bear", 50, 3), (92, C, "bull", 58, 3), (98, X, "bear", 50, 4),
                                               (101, S, "bear", 50, 4), (114, S, "bull", 58, 3)],
}


def _ev(cs, spec=R):
    return lrl.events(lrl.both(cs, spec, lrl.c1_origins(cs)))


def test_every_scenario_has_an_expectation():
    assert set(EXPECTED) == set(lrl.SCENARIOS)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_scenario(name):
    assert _ev(lrl.SCENARIOS[name]) == EXPECTED[name]


@pytest.mark.parametrize("name, mutated", [
    ("micro-pivots (collinear, 0.75-point pullbacks)", replace(R, sep=0)),      # separate-swings rule
    ("shallow staircase (drop ≤ 2τ)", replace(R, drop=0)),                      # non-horizontal rule
    ("false candidate: 3rd high below the line", replace(R, chain=True)),       # line test (control)
    ("strong trend, accelerating highs", replace(R, geometry="local")),         # chord collinearity
])
def test_each_guard_is_load_bearing(name, mutated):
    """Removing one rule makes a rejected scenario produce an LRL."""
    cs = lrl.SCENARIOS[name]
    assert not _ev(cs) and any(k == C for _, k, *_ in _ev(cs, mutated))


def test_two_points_stay_an_internal_candidate():
    """A singular swing is not an LRL and two compatible failure swings are only a candidate:
    no event, no record. The third point confirms (user requirement, STUDY_LRL §A)."""
    recs, n = lrl.run(lrl.SCENARIOS["two failure swings only (internal candidate)"], R, "bear")
    assert recs == [] and n["candidates"] >= 1 and n["confirmed"] == 0


def test_detection_reads_no_context():
    """Detection ≠ target quality: an LRL is created from bars alone. Here the anchor is not a
    C1 level and no other module runs, yet the LRL is confirmed (STUDY_LRL §H, DEF-LRL9)."""
    cs = lrl.SCENARIOS["clean bearish LRL"]
    assert lrl.events(lrl.both(cs, R, {"bear": set(), "bull": set()})) == EXPECTED["clean bearish LRL"]


def test_equal_highs_keep_the_frozen_eqh_and_anchor_the_lrl_on_the_later_member():
    """EQ interplay: the frozen Phase 2 oracle still makes the EQH (LRL reads, never writes);
    the EQ-equal pair is not an LRL step, and the LRL starts at the most recent failure."""
    from validation.models.ist import IstModel
    from validation.models.types import Settings
    cs = lrl.SCENARIOS["equal highs, then a staircase"]
    m = IstModel(Settings.from_dict({"liq": {"preset": "balanced"}, "modules": ["liq"]})).run(cs)
    assert [e.origin_bar for e in m.events if e.type == "EQH_CREATED"] == [50]
    assert lrl.both(cs, R)[0].anchor[0] == 66


def _data():
    return {"nq": lrl.nq_candles(), "walk": random_walk(3000, 7, gap_prob=0.02)}


@pytest.mark.parametrize("which", ["nq", "walk"])
def test_bullish_is_mirrored_bearish(which):
    cs = _data()[which]
    flip = {"bear": "bull", "bull": "bear"}
    mirrored = [(b, k, flip[s], a, n) for b, k, s, a, n in lrl.events(lrl.both(mirror(cs, 0.0), R))]
    assert sorted(mirrored) == lrl.events(lrl.both(cs, R)) and mirrored


@pytest.mark.parametrize("which", ["nq", "walk"])
def test_no_lookahead_prefix_invariance(which):
    """Every event at bar < n is the same whether bars ≥ n exist or not."""
    cs = _data()[which]
    full = lrl.events(lrl.both(cs, R))
    for n in range(200, len(cs), 137):
        assert lrl.events(lrl.both(cs[:n], R)) == [e for e in full if e[0] < n], n


@pytest.mark.parametrize("which", ["nq", "walk"])
def test_record_invariants(which):
    """Points strictly fail (step > EQ tolerance), are ≤ gmax apart, on the line within τ,
    at most one LRL per pivot; events sit on the confirmation bars of their points."""
    cs = _data()[which]
    recs = lrl.both(cs, R)
    assert recs
    for side in ("bear", "bull"):
        seen = [x for r in recs if r.side == side for x, _ in r.pts]
        assert len(seen) == len(set(seen))
    for r in recs:
        for (xa, pa), (xb, pb) in zip(r.pts, r.pts[1:]):
            assert pb < pa - lrl.EQ_TOL and 0 < xb - xa <= R.gmax
        assert all(abs(p - r.y(x)) <= r.tau + lrl.EPS for x, p in r.pts)
        assert r.anchor[1] - r.pts[-1][1] > R.drop * r.tau
        assert r.born == r.pts[2][0] + R.right and r.ext == [x + R.right for x, _ in r.pts[3:]]
        assert r.end_bar is None or r.end_bar > max([r.born, *r.ext])


def test_failure_swings_are_never_c1_levels():
    """The study's source finding: C1 dominance rejects every lower high it sees, so points
    2…n of an LRL are never BSL / SSL, and a C1-only source finds no LRL on the NQ data."""
    cs = lrl.nq_candles()
    c1 = lrl.c1_origins(cs)
    recs = lrl.both(cs, R, c1)
    assert recs and not [x for r in recs for x, _ in r.pts[1:] if x in c1[r.side]]
    assert lrl.both(cs, replace(lrl.SOURCES[1], name="c1"), c1) == []


@pytest.mark.parametrize("minutes", [3, 5])
def test_definition_runs_on_higher_timeframes(minutes):
    cs = lrl.resample(lrl.nq_candles(), minutes)
    assert cs[1].time - cs[0].time == minutes * 60_000 and lrl.both(cs, R)
