"""pytest configuration for the validation suite.

The agent sets IST_VAL_MODE (quick | full | deep) and IST_VAL_SEED; running
`pytest validation` directly uses quick with the default seed.
"""
import os

import pytest
from hypothesis import HealthCheck, settings

MODE = os.environ.get("IST_VAL_MODE", "quick")
SEED = int(os.environ.get("IST_VAL_SEED", "20261027"))

# Hypothesis examples per property test, stateful runs and steps, long-walk scale.
BUDGET = {
    "quick": {"examples": 40, "machines": 15, "steps": 40, "walk_bars": 3_000, "walk_runs": 1},
    "full": {"examples": 250, "machines": 60, "steps": 60, "walk_bars": 20_000, "walk_runs": 7},
    "deep": {"examples": 2_500, "machines": 400, "steps": 100, "walk_bars": 50_000, "walk_runs": 14},
}[MODE]

for name, n in (("quick", 40), ("full", 250), ("deep", 2_500)):
    settings.register_profile(
        name, max_examples=n, deadline=None, database=None, print_blob=True, derandomize=False,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large, HealthCheck.filter_too_much])
settings.load_profile(MODE)


def pytest_configure(config):
    for line in ("section(name): report section", "spec(*ids): TESTS_PHASE2 / ARCHITECTURE ids this test covers",
                 "phase1: Phase 1 logic", "phase2: Phase 2 logic", "lrl: LRL detection (docs/LRL.md)", "htf: HTF FVG (docs/HTF_FVG.md)", "cisd: CISD oracle and research (docs/CISD.md, docs/STUDY_CISD.md)",
                 "disp: displacement oracle and research (docs/DISPLACEMENT.md, docs/STUDY_DISPLACEMENT.md)",
                 "common: shared infrastructure"):
        config.addinivalue_line("markers", line)


@pytest.fixture
def budget():
    return BUDGET
