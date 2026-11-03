"""CONTEXT-01 research study (validation/studies/context.py, docs/context/): the harness is trustworthy.
FEATURES_AT_T never see a later bar; a target's status follows the frozen DEF-L4 take rule and is
UNVERIFIED where nothing was seen; the outcome labels and the driftless reference are exact; the numbers
the documents quote reproduce."""
from datetime import datetime

import pytest

from validation.models.types import Candle
from validation.studies import context as study

pytestmark = [pytest.mark.context, pytest.mark.section("research.context")]
T0 = int(datetime(2026, 10, 27, 10, 0, tzinfo=study.NY).timestamp() * 1000)


@pytest.fixture(scope="module")
def segs():
    return study.segments()


@pytest.fixture(scope="module")
def dec(segs):
    return study.decisions(segs)


def test_features_never_see_a_later_bar(segs, dec):
    """Every decision point: shift every later bar by 1,000 points and drop every later HTF bar and
    LEVEL_SET. Nothing in FEATURES_AT_T changes."""
    for i, f in dec:
        seg, t = segs[i], f["t"]
        k = seg.cs[t].time
        alt = study.Segment(seg.name, seg.cs[:t + 1] + [Candle(c.time, c.open + 1000, c.high + 1000, c.low + 1000, c.close + 1000)
                                                        for c in seg.cs[t + 1:]],
                            [h for h in seg.htf if h[4] <= k], [p for p in seg.pdx if p[0] <= k])
        assert study.features(alt, t) == f


def bars(*hlc):
    return study.Segment("synthetic", [Candle(T0 + 60_000 * j, c, h, l, c) for j, (h, l, c) in enumerate(hlc)], [], [])


def test_status_is_the_frozen_take_rule_and_unverified_where_unseen():
    seg = bars((99, 98, 98.5), (100, 99, 99.5), (100.25, 99, 99.75), (101, 99, 100.5))
    x = study.Target("PDH", "D", 1, 100.0, T0, T0)
    assert study.status(seg, x, 1) == ("AVAILABLE", "")                  # an exact touch is no take
    assert study.status(seg, x, 2) == ("TAKEN", "SWEEP")                 # one tick beyond, close back inside
    assert study.status(seg, study.Target("PDH", "D", 1, 99.5, T0, T0), 3)[1] == "SWEEP"
    assert study.status(seg, study.Target("X", "D", 1, 100.0, T0 + 180_000, T0), 3) == ("TAKEN", "BREAK")
    early = study.Target("PWH", "W", 1, 105.0, T0 - 3 * study.H, T0)     # born before anything was seen
    assert study.status(seg, early, 3) == ("UNVERIFIED", "")
    seen = study.Segment("s", seg.cs, [("240", T0 - 4 * study.H, 104.0, 97.0, T0)], [])
    assert study.status(seen, early, 3) == ("AVAILABLE", "")             # a completed 4H bar covers the gap
    over = study.Segment("s", seg.cs, [("240", T0 - 4 * study.H, 106.0, 97.0, T0)], [])
    assert study.status(over, early, 3) == ("UNVERIFIED", "")            # beyond in a bar across `since`: unknowable
    older = study.Target("PWH", "W", 1, 105.0, T0 - 8 * study.H, T0)
    assert study.status(over, older, 0) == ("TAKEN", "?")                # taken before the segment: no class


def test_outcome_labels_and_the_driftless_reference():
    seg = bars((100, 99, 99.5), (100.5, 99, 100), (101, 99.5, 100.5), (100.5, 97, 98), (102, 96, 99))
    up = study.Target("A", "S", 1, 100.75, T0, T0)
    dn = study.Target("B", "S", -1, 98.5, T0, T0)
    assert study.label(seg, 0, up, dn) == ("PRIMARY_REACHED", 2)
    assert study.label(seg, 0, dn, up) == ("OPPOSITE_REACHED_FIRST", None)
    assert study.label(seg, 2, study.Target("C", "S", 1, 101.5, T0, T0), study.Target("D", "S", -1, 96.5, T0, T0)) == \
        ("BOTH_SAME_BAR_UNRESOLVED", 2)
    assert study.label(seg, 0, study.Target("E", "S", 1, 110, T0, T0), None) == ("CENSORED", None)
    assert study.null_p(100.0, study.Target("A", "S", 1, 101.0, 0, 0), study.Target("B", "S", -1, 97.0, 0, 0)) == 0.75


def test_numbers_quoted_by_the_study(segs, dec):
    assert [len(s.cs) for s in segs] == [1639, 1188, 1076, 1076] and len(dec) == 13
    rows = study.baseline_rows(segs, dec)
    assert "| B1 nearest, any class | 13 | 0 | 9 | 3 | 0 | 0 | 1 | 9/12 · 10.0 | 3 |" in rows
    assert "| B0 nearest external | 13 | 1 | 5 | 5 | 0 | 0 | 2 | 5/10 · 5.0 | 78 |" in rows
    facts = study.fact_rows(study.fact_events(segs))
    assert "| CISD (1m) | 317 | 222 | 171 | 88 (51%) | 52% | 12 |" in facts
    assert "| external sweep | 5 | 3 | 3 | 3 (100%) | 54% | 3 |" in facts
