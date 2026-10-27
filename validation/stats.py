"""Run-wide counters shared by the tests and the agent (same process).

Tests publish numbers here (generated examples, sequences, invariant checks, peak
record counts, structured regression/golden/parity results); the agent reads them
to write the report.
"""
from collections import Counter, defaultdict

COUNTS: Counter = Counter()          # e.g. "property.examples", "stateful.sequences", "bars"
INV_CHECKS: Counter = Counter()      # invariant id -> number of evaluations
PEAKS: dict = defaultdict(int)       # e.g. "fvg.records.dir" -> max seen
RESULTS: dict = {}                   # "regression", "legacy", "golden", "parity", "selectivity", …


def bump(key: str, n: int = 1) -> None:
    COUNTS[key] += n


def peak(key: str, value: int) -> None:
    if value > PEAKS[key]:
        PEAKS[key] = value


def reset() -> None:
    COUNTS.clear()
    INV_CHECKS.clear()
    PEAKS.clear()
    RESULTS.clear()
