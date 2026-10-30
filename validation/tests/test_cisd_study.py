"""CISD research study (validation/studies/cisd.py, docs/STUDY_CISD.md): the harness is
trustworthy. Synthetic scenarios give the specified events, the candidates differ where the
study says they do, bullish = mirrored bearish, prices can be shifted, no decision uses a later
bar, and CISD-R's state model alternates with one candidate at a time. No indicator, oracle or
frozen-engine change is tested here (there is none)."""
from dataclasses import replace

import pytest

from validation.candles import mirror, random_walk, shift
from validation.studies import cisd
from validation.studies.lrl import nq_candles

pytestmark = [pytest.mark.cisd, pytest.mark.section("research.cisd")]
R, S = cisd.RECOMMENDED, cisd.SCENARIOS
C, T = "CISD_CONFIRMED", "CISD_RETEST"

# CISD-R: (bar, event, side, level). Bar 0 is the first scenario bar.
EXPECTED = {
    "1 clean bullish CISD": [(5, C, 1, 100)],
    "3 wick through only": [],
    "4 close exactly at the level": [],
    "5 close one tick beyond": [(5, C, 1, 100), (6, T, 1, 100)],
    # 6 and 10 start with a bearish CISD (bar 3, level 98) so the state is established; 7 with scenario 1
    "6 false change (bounce below the level, then lower)": [(3, C, -1, 98), (4, T, -1, 98)],
    "7 strong trend continuation (shallow pullbacks)": [(5, C, 1, 100)],
    "8 range / chop": [],
    "9 immediate reversal (the extreme bar confirms)": [(3, C, 1, 100)],
    "10 multiple candidates (the reference moves to the run into the new low)": [(3, C, -1, 98), (4, T, -1, 98),
                                                                                 (12, C, 1, 98.5)],
    "11 confirmed CISD, then a retest": [(5, C, 1, 100), (6, T, 1, 100)],
    "12 confirmed CISD, then invalidation": [(5, C, 1, 100), (6, T, 1, 100), (7, C, -1, 95.5)],
    "14 displacement present": [(20, C, 1, 100)],
    "15 same structure without displacement": [(35, C, 1, 100)],
    "16 doji inside the series": [(5, C, 1, 98.25), (6, T, 1, 98.25)],
}


def ev(cs, spec=R):
    return [(b, e, s, lv) for b, e, s, lv, _ in cisd.events(cisd.run(cs, spec)[0])]


def test_every_scenario_is_specified():
    assert set(EXPECTED) == set(S)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_recommended_definition_on_scenarios(name):
    assert ev(S[name]) == EXPECTED[name]


def test_the_candidates_differ_where_the_study_says():
    """Wick vs close (3, 4), stateless repeats in a trend (7), the last-candle anchor's false
    change (6), displacement (14 vs 15), body confirmation one bar later (1), doji (16)."""
    wick = replace(R, confirm="wick")
    assert ev(S["3 wick through only"], wick)[0] == (5, C, 1, 100)
    assert ev(S["4 close exactly at the level"], wick)[0] == (5, C, 1, 100)
    assert len(ev(S["8 range / chop"], wick)) > 20                       # the wick rule flips every bar in chop
    assert [e[0] for e in ev(S["7 strong trend continuation (shallow pullbacks)"], cisd.SPECS[1]) if e[1] == C] == [5, 9, 12, 15]
    assert (7, C, 1, 96.5) in ev(S["6 false change (bounce below the level, then lower)"], cisd.SPECS[0])
    disp = cisd.SPECS[4]
    assert ev(S["14 displacement present"], disp) == [(20, C, 1, 100)]
    assert ev(S["15 same structure without displacement"], disp) == []
    assert ev(S["1 clean bullish CISD"], replace(R, confirm="body")) == [(6, C, 1, 100)]
    assert ev(S["16 doji inside the series"], replace(R, doji="skip")) == [(6, C, 1, 100)]


def test_record_facts_after_invalidation():
    """Scenario 12: the bullish CISD (leg low 95) is retested and closed back through on bar 6;
    the bearish CISD on bar 7 ends it, on the same bar as the close below the leg low."""
    bull, bear = cisd.run(S["12 confirmed CISD, then invalidation"], R)[0]
    assert (bull.bar, bull.level, bull.ext, bull.origin, bull.retest, bull.reclaim, bull.broken, bull.end) == \
           (5, 100, 95, 1, 6, 6, 7, 7)
    assert (bear.side, bear.level, bear.origin, bear.end) == (-1, 95.5, 4, None)


def _flip(evs, pivot=0.0):
    return [(b, e, -s, 2 * pivot - lv) for b, e, s, lv in evs]


@pytest.mark.parametrize("spec", [R, cisd.SPECS[1], cisd.SPECS[3], replace(R, confirm="body")], ids=lambda s: s.name[:7])
def test_mirror_symmetry(spec):
    for name in ("1 clean bullish CISD", "12 confirmed CISD, then invalidation", "10 multiple candidates "
                 "(the reference moves to the run into the new low)"):
        assert ev(mirror(S[name], 100.0), spec) == _flip(ev(S[name], spec), 100.0)
    cs = random_walk(3000, 5, gap_prob=0.02)
    assert sorted(ev(mirror(cs, 0.0), spec)) == sorted(_flip(ev(cs, spec)))


def test_translation_invariance():
    cs = random_walk(3000, 6, gap_prob=0.02)
    assert ev(shift(cs, 37.25)) == [(b, e, s, lv + 37.25) for b, e, s, lv in ev(cs)]


@pytest.mark.parametrize("spec", [R, cisd.SPECS[1], cisd.SPECS[4]], ids=lambda s: s.name[:7])
def test_no_lookahead_prefix_invariance(spec):
    cs = random_walk(2500, 8, gap_prob=0.02)
    full = ev(cs, spec)
    for n in range(50, len(cs), 233):
        assert ev(cs[:n], spec) == [e for e in full if e[0] < n], n


@pytest.mark.parametrize("data", ["nq", "walk"])
def test_state_model_alternates_with_one_candidate(data):
    """CISD-R: directions alternate, never two candidates once the state is set, and a close
    beyond the protected leg extreme never comes before the opposite CISD (that is what makes a
    separate INVALIDATED event unnecessary; gap-only exceptions are counted in the study)."""
    cs = nq_candles() if data == "nq" else random_walk(6000, 1, gap_prob=0.02)
    recs, info = cisd.run(cs, R)
    assert all(a.side == -b.side for a, b in zip(recs, recs[1:]))
    assert all(a.end == b.bar for a, b in zip(recs, recs[1:]))
    assert max(info["conc"][recs[0].bar + 1:]) <= 1
    assert not [r for r in recs if r.broken is not None and (r.end is None or r.broken < r.end)]


def test_level_is_known_before_confirmation():
    """The level is an open that printed before the decision bar; the record's facts come after it."""
    recs, _ = cisd.run(nq_candles(), R)
    for r in recs:
        assert r.origin <= r.anchor < r.bar and r.known <= r.bar
        assert all(x is None or x > r.bar for x in (r.retest, r.reclaim, r.broken))


def test_reload_convergence():
    """The state model depends on history, but forgets it fast: started at any of 86 later bars,
    the truncated run's CISDs equal the full history's after at most 4 CISDs (NQ; 62 bars at
    most). This is the warm-up a Pine chart's first loaded bar implies (docs/STUDY_CISD.md §M)."""
    cs = nq_candles()
    full = [(r.bar, r.side, r.level, r.origin) for r in cisd.run(cs, R)[0]]
    worst = 0
    for k in range(1, 600, 7):
        part = [(r.bar + k, r.side, r.level, r.origin + k) for r in cisd.run(cs[k:], R)[0]]
        i = next(i for i in range(len(part)) if part[i:] == full[len(full) - len(part) + i:])
        worst = max(worst, i)
    assert worst <= 4
