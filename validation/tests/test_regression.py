"""Regression: the diff engine itself, the committed baseline, and the legacy models in git."""
import copy
import os

import pytest

from validation import regression as rg
from validation import stats
from validation.candles import random_walk
from validation.models.ist import run_model
from validation.models.types import LiqSettings, Settings

pytestmark = [pytest.mark.common, pytest.mark.section("regression")]
# Balanced defaults · Aggressive, 8-tick tolerance · Strict, 3 touches · Balanced, 8 ticks, 3 touches, 3-cluster memory
LEGACY_CONFIGS = [(5, 3, 1.0, 4, 2, 25), (3, 2, 0.5, 8, 2, 25), (10, 5, 2.0, 4, 3, 25), (5, 3, 1.0, 8, 3, 3)]


def _tiny():
    return {"label": "t", "cases": {"c": {"settings": {}, "bars": 3,
                                          "events": [[1, "BSL_CREATED", 1, 10, 100.0], [2, "BSL_TAKEN", 1, 10, 100.0],
                                                     [2, "BSL_SWEEP", 1, 10, 100.0], [0, "LEVEL_SET", 1, 0, 99.0]],
                                          "state": {"levels": [{"id": 10, "side": "BSL", "price": 100.0, "cls": "SWEEP"}]}}}}


def test_diff_engine_detects_every_category():
    base, cur = _tiny(), _tiny()
    ev = cur["cases"]["c"]["events"]
    ev[1] = [3, "BSL_TAKEN", 1, 10, 100.0]                       # TIMING
    ev[2] = [2, "BSL_SWEEP", 1, 10, 100.25]                      # PRICE
    ev.append([2, "EQH_CREATED", 1, 20, 100.0])                  # ADDED
    del ev[0]                                                    # REMOVED
    cur["cases"]["c"]["state"]["levels"][0]["cls"] = "BREAK"     # STATE
    cur["cases"]["new"] = copy.deepcopy(base["cases"]["c"])      # CHANGED (case added)
    cats = sorted(d["category"] for d in rg.diff(base, cur))
    assert cats == ["ADDED", "CHANGED", "PRICE", "REMOVED", "STATE", "TIMING"], cats


def test_manifest_marks_expected_changes():
    base, cur = _tiny(), _tiny()
    cur["cases"]["c"]["events"][2] = [2, "BSL_SWEEP", 1, 10, 100.25]
    d = rg.classify(rg.diff(base, cur), [{"id": "X-1", "category": "PRICE", "type": "BSL_*"}])
    assert [x["expected"] for x in d] == ["X-1"]
    d = rg.classify(rg.diff(base, cur), [{"id": "X-2", "category": "TIMING"}])
    assert [x["expected"] for x in d] == [None]


def test_against_committed_baseline():
    base = rg.load_baseline()
    assert base is not None, "no baseline: run `python -m validation --update-baseline` once and commit it"
    cur = rg.snapshot()
    diffs = rg.classify(rg.diff(base, cur), rg.load_manifest())
    summary = rg.summarize(base, cur, diffs)
    stats.RESULTS["regression"] = summary
    assert summary["unexpected"] == 0, f"{summary['unexpected']} unexpected differences: {summary['unexpected_sample'][:5]}"


@pytest.mark.parametrize("ref", ["v0.4.0-dev", "v0.4.1-dev"])
def test_legacy_models_match_the_oracle(ref, budget):
    """The liquidity oracle reproduces the reference models that validated v0.4.0-dev / v0.4.1-dev."""
    mod = rg.load_legacy(ref)
    if mod is None:
        stats.RESULTS.setdefault("legacy", {})[ref] = "SKIPPED (git or tag not available)"
        pytest.skip(f"{ref}: git or tag not available")
    n_bars = min(budget["walk_bars"], 20_000)
    total = 0
    for cfg in LEGACY_CONFIGS:
        L, R, K, tol, mt, mem = cfg
        # The legacy models are the definition before C1 (v0.4.4-dev): no dominance.
        liq = LiqSettings(left=L, right=R, k=K, dom=0, tol_ticks=tol, min_touch=mt, eq_memory=mem)
        candles = random_walk(n_bars, 7)
        want = rg.legacy_events(mod, candles, liq)
        got = [(e.bar, e.type, e.sid, e.price) for e in run_model(candles, Settings(modules=("liq",), liq=liq)).events]
        assert got == want, f"{ref} {cfg}: first difference at {next(i for i, (a, b) in enumerate(zip(got, want)) if a != b)}"
        total += len(want)
    stats.RESULTS.setdefault("legacy", {})[ref] = f"identical: {len(LEGACY_CONFIGS)} configurations × {n_bars} bars, {total} events"
