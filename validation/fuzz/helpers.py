"""Shared helpers for property tests: checked runs that leave a failure artifact,
and the event transforms used by the metamorphic properties."""
from __future__ import annotations

from validation import stats
from validation.artifacts import save_failure
from validation.invariants import InvariantViolation, run_checked
from validation.models.ist import run_model

MIRROR_TYPE = {}
for a, b in (("BSL", "SSL"), ("EQH", "EQL")):
    for suffix in ("CREATED", "TAKEN", "SWEEP", "BREAK", "DROPPED_MEMORY"):
        MIRROR_TYPE[f"{a}_{suffix}"] = f"{b}_{suffix}"
        MIRROR_TYPE[f"{b}_{suffix}"] = f"{a}_{suffix}"


def checked(test: str, candles, settings, counter: str, seed=None, **kw):
    """run_checked; on a violation save the case, then re-raise. The model is causal, so
    the candles up to the violating bar reproduce it; Hypothesis cases are also shrunk."""
    stats.bump(counter)
    try:
        return run_checked(candles, settings, **kw)
    except InvariantViolation as v:
        save_failure(test, invariant=v.inv_id, message=str(v), candles=candles[:v.bar + 1], settings=settings,
                     seed=seed, extra={"bar": v.bar, "original_length": len(candles)})
        raise


def compare(test: str, candles, settings, expected, actual, what: str):
    if expected != actual:
        save_failure(test, invariant=None, message=f"metamorphic property failed: {what}", candles=candles,
                     settings=settings, expected=sorted(expected - actual, key=str)[:20],
                     actual=sorted(actual - expected, key=str)[:20])
        raise AssertionError(f"{what}: {len(expected - actual)} expected events missing, {len(actual - expected)} unexpected")


def event_set(m, families=None) -> set:
    return {(e.bar, e.type, e.dir, e.sid, e.price) for e in m.events
            if families is None or e.type.split("_")[0] in families}


def mirrored(events: set, pivot: float) -> set:
    out = set()
    for bar, t, d, sid, p in events:
        out.add((bar, MIRROR_TYPE.get(t, t), -d, sid, None if p is None else 2 * pivot - p))
    return out


def shifted(events: set, points: float) -> set:
    return {(bar, t, d, sid, None if p is None else p + points) for bar, t, d, sid, p in events}


def run(candles, settings, **kw):
    return run_model(candles, settings, **kw)
