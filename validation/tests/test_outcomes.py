"""CONTEXT-03 outcome oracle (validation/models/outcomes.py, docs/context/EVALUATION.md): EXACT_TOUCH ≠ TARGET_REACHED ≠
TARGET_TAKEN; every label of the outcome contract; the evaluator reads only bars after t and never changes a
hypothesis; CONTEXT_INVALIDATED is never emitted; the distance reference."""
import dataclasses
import random

import pytest

from validation.models import outcomes as O
from validation.models.types import Candle

pytestmark = [pytest.mark.evaluation, pytest.mark.section("evaluation")]
T0 = 1_793_000_000_000
EV = O.OutcomeEvaluator()


def bar(i, h, l, c=None, o=None):
    mid = (h + l) / 2
    return Candle(T0 + 60_000 * i, mid if o is None else o, h, l, mid if c is None else c)


def hyp(up=20000.0, dn=19900.0, horizon=60, close=19950.0, side=1):
    return O.DOLHypothesis("TEST", T0, "P", side, up if side > 0 else dn, "O", -side, dn if side > 0 else up, close,
                           T0 + 60_000 * horizon, "H-test")


# ── EXACT_TOUCH ≠ TARGET_REACHED ≠ TARGET_TAKEN ──

def test_an_exact_touch_is_reached_but_not_taken():
    p = O.interaction(1, 20000.0, [bar(1, 19990, 19980), bar(2, 20000, 19990, 19995)])
    assert (p.exact_touch_at, p.reached_at, p.reached_by, p.taken_at, p.touched_not_taken) == \
        (T0 + 120_000, T0 + 120_000, "EXACT_TOUCH", None, True)


def test_a_crossing_is_reached_and_taken_without_an_exact_touch():
    p = O.interaction(1, 20000.0, [bar(1, 20005, 19995, 19998)])           # the user's example: target 20000, high 20005
    assert (p.exact_touch_at, p.reached_at, p.reached_by, p.taken_at, p.taken_kind, p.touched_not_taken) == \
        (None, T0 + 60_000, "CROSSED", T0 + 60_000, "SWEEP", False)
    assert O.interaction(1, 20000.0, [bar(1, 20005, 19995, 20001)]).taken_kind == "BREAK"
    lo = O.interaction(-1, 19900.0, [bar(1, 19910, 19899, 19899.5)])
    assert (lo.reached_by, lo.taken_kind) == ("CROSSED", "BREAK")


def test_reached_needs_no_exact_equality_and_is_the_label_criterion():
    h = hyp()
    out = EV.evaluate(h, [bar(1, 19960, 19940), bar(2, 20003.25, 19950)])
    assert (out.label, out.decided_at, out.primary.exact_touch_at) == ("PRIMARY_REACHED", T0 + 120_000, None)


# ── the outcome contract ──

def test_primary_first_opposite_first_and_both_in_one_bar():
    h = hyp()
    assert EV.evaluate(h, [bar(1, 20000, 19950)]).label == "PRIMARY_REACHED"
    assert EV.evaluate(h, [bar(1, 19960, 19900)]).label == "OPPOSITE_REACHED_FIRST"
    both = EV.evaluate(h, [bar(1, 20001, 19899, o=19950, c=20000)])         # a bullish candle: still no order guessed
    assert (both.label, both.decided_at) == ("BOTH_SAME_BAR_UNRESOLVED", T0 + 60_000)
    assert EV.evaluate(h, [bar(1, 19960, 19940), bar(2, 19970, 19899), bar(3, 20010, 19960)]).label == "OPPOSITE_REACHED_FIRST"


def test_unresolved_censored_and_data_invalid():
    h = hyp(horizon=3)
    quiet = [bar(i, 19960, 19940) for i in range(1, 6)]
    assert EV.evaluate(h, quiet).label == "UNRESOLVED"
    assert EV.evaluate(h, quiet + [bar(6, 20010, 19950)]).label == "UNRESOLVED"     # beyond the horizon: never read
    assert EV.evaluate(hyp(horizon=30), quiet).label == "CENSORED"                  # the data ends before the horizon
    assert EV.evaluate(hyp(horizon=30), quiet, data_end=T0 + 60_000 * 40).label == "UNRESOLVED"
    assert EV.evaluate(hyp(horizon=30), quiet, boundary_at=T0 + 60_000 * 10, data_end=T0 + 60_000 * 40).label == "CENSORED"
    assert EV.evaluate(hyp(horizon=30), quiet + [bar(12, 20010, 19950)], boundary_at=T0 + 60_000 * 10,
                       data_end=T0 + 60_000 * 40).label == "CENSORED"               # bars after a roll are never read
    bad = EV.evaluate(hyp(horizon=30), quiet + [bar(8, 20010, 19950)], invalid_at=T0 + 60_000 * 7, data_end=T0 + 60_000 * 40)
    assert bad.label == "DATA_INVALID"
    early = EV.evaluate(hyp(horizon=30), [bar(1, 20010, 19950)], invalid_at=T0 + 60_000 * 7, data_end=T0 + 60_000 * 40)
    assert early.label == "PRIMARY_REACHED"                                          # decided before the integrity issue


def test_the_evaluator_reads_only_the_future_and_never_changes_the_hypothesis():
    h = hyp()
    with pytest.raises(ValueError):
        EV.evaluate(h, [bar(0, 20010, 19950)])                                       # the bar at t is not the future
    with pytest.raises(dataclasses.FrozenInstanceError):
        h.target_price = 1.0
    before = dataclasses.asdict(h)
    EV.evaluate(h, [bar(1, 20010, 19950)])
    assert dataclasses.asdict(h) == before


def test_context_invalidated_is_never_emitted_and_labels_are_deterministic():
    rnd = random.Random(7)
    seen = set()
    for _ in range(400):
        bars, p = [], 19950.0
        for i in range(1, rnd.randint(2, 80)):
            o = p
            p += rnd.choice([-1, 1]) * rnd.randint(0, 40) * 0.25
            bars.append(Candle(T0 + 60_000 * i, o, max(o, p) + rnd.randint(0, 8) * 0.25, min(o, p) - rnd.randint(0, 8) * 0.25, p))
        h = hyp(up=19950 + rnd.randint(1, 60) * 0.25 * 4, dn=19950 - rnd.randint(1, 60) * 0.25 * 4, horizon=rnd.randint(5, 90),
                side=rnd.choice([1, -1]))
        a, b = EV.evaluate(h, bars), EV.evaluate(h, bars)
        assert a == b and a.label in O.OUTCOMES and a.label != "NO_HYPOTHESIS"
        seen.add(a.label)
    assert "CONTEXT_INVALIDATED" not in seen and "CONTEXT_INVALIDATED" not in O.OUTCOMES
    assert {"PRIMARY_REACHED", "OPPOSITE_REACHED_FIRST", "UNRESOLVED", "CENSORED"} <= seen


def test_mirror_symmetry():
    bars = [bar(1, 19960, 19940), bar(2, 20000, 19950), bar(3, 19990, 19899)]
    flip = [Candle(c.time, 40000 - c.open, 40000 - c.low, 40000 - c.high, 40000 - c.close) for c in bars]
    a = EV.evaluate(hyp(), bars)
    b = EV.evaluate(O.DOLHypothesis("TEST", T0, "P", -1, 20000.0, "O", 1, 20100.0, 20050.0, T0 + 3_600_000, "H"), flip)
    assert (a.label, a.decided_at, a.primary.reached_by) == (b.label, b.decided_at, b.primary.reached_by)


def test_the_distance_reference():
    assert O.distance_reference(hyp(up=20000.0, dn=19900.0, close=19950.0)) == 0.5
    assert O.distance_reference(hyp(up=20000.0, dn=19800.0, close=19950.0)) == 0.75
