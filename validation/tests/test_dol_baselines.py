"""CONTEXT-03 policy interface and baselines (validation/models/dol_policy.py, validation/studies/context_eval.py): the
B0…B4 rules and their pre-registered comparators, STRICT versus PROVISIONAL eligibility, the policy / outcome
separation (a changed future never changes a hypothesis), the metrics (abstentions and NO_HYPOTHESIS counted,
NQ / ES never pooled) and determinism. Publishes the evaluation diagnostics of the report."""
import dataclasses

import pytest

from validation import stats
from validation.models.dol_policy import BASELINES, Baseline, Snapshot, TargetView, eligible
from validation.models.outcomes import DOLHypothesis, NoHypothesis
from validation.models.types import Candle
from validation.studies import context_eval as E

pytestmark = [pytest.mark.evaluation, pytest.mark.section("evaluation")]


def tv(id, cls, side, price, state="AVAILABLE", typ=None, role=None, verification=(), history="OBSERVED", consumed=False):
    return TargetView(id, typ or ("BSL" if side > 0 else "SSL"), cls, side, price, state, history, verification, consumed, role)


def snap(*targets, close=100.0):
    return Snapshot(1, close, 2, "H", tuple(sorted(targets, key=lambda x: x.id)))


S = [tv("pdh", "DAILY", 1, 110, typ="PDH", role="CURRENT"), tv("pdl", "DAILY", -1, 94, typ="PDL", role="CURRENT"),
     tv("lon_h", "SESSION", 1, 104), tv("bsl", "STRUCTURAL", 1, 101), tv("ssl", "STRUCTURAL", -1, 98.5),
     tv("pwl", "WEEKLY", -1, 80, typ="PWL", role="CURRENT")]


def pick(name, targets, profile="STRICT", close=100.0):
    h = Baseline(name, profile).evaluate(snap(*targets, close=close))
    return (h.target_id, h.opposite_id) if isinstance(h, DOLHypothesis) else h.reason


def test_the_baseline_rules_and_their_pre_registered_comparators():
    assert pick("B0", S) == ("lon_h", "pdl")                    # nearest external · nearest external on the other side
    assert pick("B1", S) == ("bsl", "ssl")                      # nearest of any class · nearest of any class opposite
    assert pick("B2", S) == ("pdl", "pdh")                      # the nearer of the current PDH / PDL · the other one
    assert pick("B3", S) == "NO_COMPARATOR"                      # WEEKLY is present, but only below
    assert pick("B4", S) == "ABSTAIN"                            # external targets on both sides
    one_side = [x for x in S if x.side > 0 or x.source_class == "STRUCTURAL"]
    assert pick("B4", one_side) == ("lon_h", "ssl")             # one side only: comparator = nearest of any class opposite
    assert pick("B0", one_side) == "NO_COMPARATOR"              # no external opposite: no evaluable hypothesis
    assert pick("B2", [S[0]]) == "NO_COMPARATOR" and pick("B2", []) == "NO_CANDIDATE"


def test_b3_s_class_order_is_its_own_rule_only():
    both_weeks = S + [tv("pwh", "WEEKLY", 1, 130, typ="PWH", role="CURRENT")]
    assert pick("B3", both_weeks) == ("pwl", "pwh")             # WEEKLY on both sides: the nearer weekly, the other weekly
    assert pick("B3", [x for x in S if x.source_class == "STRUCTURAL"]) == ("bsl", "ssl")


def test_strict_and_provisional_eligibility():
    pend = tv("x", "DAILY", 1, 1, state="UNVERIFIED", verification=("SOURCE_PENDING_GV",))
    assert not eligible(pend, "STRICT") and eligible(pend, "PROVISIONAL")
    assert not eligible(dataclasses.replace(pend, history="INCOMPLETE", verification=("SOURCE_PENDING_GV", "HISTORY_INCOMPLETE")),
                        "PROVISIONAL")
    assert not eligible(dataclasses.replace(pend, consumed=True), "PROVISIONAL")
    assert not eligible(tv("y", "STRUCTURAL", 1, 1, state="TAKEN"), "PROVISIONAL")


def test_a_policy_sees_one_frozen_snapshot_and_nothing_else():
    assert [f.name for f in dataclasses.fields(Snapshot)] == ["t", "close", "horizon_end", "horizon_rule", "targets"]
    s = snap(*S)
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.close = 1.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.targets[0].price = 1.0


@pytest.fixture(scope="module")
def evaluated():
    data, recs = E.run_all()
    return data, recs


def test_a_changed_future_never_changes_a_hypothesis(evaluated):
    data, recs = evaluated
    for meta, seg in data:
        k = len(seg.cs) // 2
        fut = seg.cs[:k] + [Candle(c.time, c.open + 500, c.high + 500, c.low + 500, c.close + 500) for c in seg.cs[k:]]
        a = [r.hypothesis for r in E.run_dataset(meta, seg, BASELINES) if r.t < seg.cs[k].time]
        b = [r.hypothesis for r in E.run_dataset(meta, seg, BASELINES, future=fut) if r.t < seg.cs[k].time]
        assert a == b                                            # the hypotheses at t; only their outcomes may differ


def test_metrics_count_everything_and_never_pool_underlyings(evaluated):
    _, recs = evaluated
    ms = E.metrics(recs)
    for m in ms.values():
        labels = sum(m[x] for x in ("PRIMARY_REACHED", "OPPOSITE_REACHED_FIRST", "BOTH_SAME_BAR_UNRESOLVED", "UNRESOLVED",
                                     "CENSORED", "DATA_INVALID"))
        assert m["decision points"] == m["eligible"] + m["DATA_INVALID at t"]
        assert m["eligible"] == m["emitted"] + m["NO_HYPOTHESIS"] and m["emitted"] == labels
        assert m["NO_HYPOTHESIS"] == sum(m[f"no hypothesis: {k}"] for k in ("ABSTAIN", "NO_CANDIDATE", "NO_COMPARATOR"))
    es = [dataclasses.replace(r, underlying="ES") for r in recs[:5]]
    assert {u for u, _ in E.metrics(recs[:5] + es)} == {"NQ", "ES"}
    assert {u for u, _ in ms} == {"NQ"} and len({(u, p) for u, p in ms}) == len(BASELINES)


def test_the_harness_is_deterministic_and_the_quoted_numbers_reproduce(evaluated):
    data, recs = evaluated
    assert E.run_all()[1] == recs
    rows = E.metric_rows(E.metrics(recs))
    assert len({r.t for r in recs}) == 13
    assert "| NQ | B1@PROVISIONAL | 13 | 12 | 1 | 8 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 12 | 7 | 5 | 12/13 | 8/12 · 8.7 | 8/12 |" in rows
    assert "| NQ | B0@STRICT | 13 | 0 | 13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/13 | — | — |" in rows
    stats.RESULTS["evaluation"] = {"rows": rows, "datasets": E.dataset_rows(data), "reasons": E.reason_rows(E.metrics(recs))}
