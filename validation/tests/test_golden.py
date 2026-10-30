"""Golden dataset: every case in golden/synthetic, golden/nq and golden/human must reproduce exactly."""
import pytest

from validation import stats
from validation.golden import load_cases, run_case

pytestmark = [pytest.mark.common, pytest.mark.section("golden")]
CASES = load_cases()


def test_golden_runner_detects_mismatches():
    """Corrupt each expectation kind of every case: the runner must report it."""
    import copy
    for _, case in CASES:
        bad = copy.deepcopy(case)
        exp = bad["expected"]
        exp["events"][0]["bar"] = exp["events"][0].get("bar", 0) + 1000
        for group in ("structures", "final_states"):
            for it in exp.get(group, []):
                k = next(iter(it["expect"]))
                it["expect"][k] = "corrupted"
        _, fails = run_case(bad)
        assert any(f.startswith("missing event") for f in fails), case["id"]
        for group in ("structures", "final_states"):
            if exp.get(group):
                assert any("corrupted" in f for f in fails), (case["id"], group)


@pytest.mark.parametrize("path, case", CASES, ids=[c["id"] for _, c in CASES])
def test_golden_case(path, case):
    _, fails = run_case(case)
    stats.RESULTS.setdefault("golden", {})[case["id"]] = {"source": case.get("source", "?"), "ok": not fails,
                                                          "failures": fails[:10]}
    assert not fails, f"{case['id']} ({path.name}):\n  " + "\n  ".join(fails)
