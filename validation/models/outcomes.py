"""CONTEXT-03 outcome oracle: evaluation only. It labels a frozen DOL hypothesis issued at t from the bars after
t, and never feeds anything back into a hypothesis, a policy or the target universe.
Spec: docs/context/EVALUATION.md (pre-registered).

Three different facts about one target and one bar, never merged:

    concept          upper target (▲)      lower target (▼)
    EXACT_TOUCH      high == price         low == price            diagnostic
    TARGET_REACHED   high >= price         low <= price            the DOL question: did price get there?
    TARGET_TAKEN     high >  price         low <  price            DEF-L4 consumption; SWEEP / BREAK by that close

A crossing is REACHED and TAKEN without being an EXACT_TOUCH. An exact touch is REACHED, not TAKEN. Phase 2's
own semantics are not changed: this layer only reads prices.
"""
from __future__ import annotations

from dataclasses import dataclass

OUTCOMES = ("PRIMARY_REACHED", "OPPOSITE_REACHED_FIRST", "BOTH_SAME_BAR_UNRESOLVED", "UNRESOLVED", "CENSORED",
            "DATA_INVALID", "NO_HYPOTHESIS")
NOT_APPLICABLE = ("CONTEXT_INVALIDATED",)   # reserved for CONTEXT-04 (directional context); never emitted


@dataclass(frozen=True)
class DOLHypothesis:
    """Everything is fixed at t, from information available at t (DEF-EV1). Frozen: nothing can change it later."""
    policy_id: str
    t: int                      # ms: the decision bar (its close)
    target_id: str
    target_side: int            # +1 above · −1 below
    target_price: float
    opposite_id: str            # the pre-registered opposite comparator (DEF-EV3)
    opposite_side: int
    opposite_price: float
    close: float                # the decision bar's close (for the geometric reference)
    horizon_end: int            # ms: bars with time < horizon_end are evaluated (DEF-EV4)
    horizon_rule: str
    info: tuple = ()            # (key, value) pairs known at t, for the record only


@dataclass(frozen=True)
class NoHypothesis:
    policy_id: str
    t: int
    reason: str                 # ABSTAIN · NO_CANDIDATE · NO_COMPARATOR


@dataclass(frozen=True)
class Interaction:
    exact_touch_at: int | None  # first bar exactly at the price
    reached_at: int | None      # first bar at or beyond the price
    reached_by: str | None      # EXACT_TOUCH (that bar was exactly at it) · CROSSED (beyond it)
    taken_at: int | None        # first bar strictly beyond (DEF-L4)
    taken_kind: str | None      # SWEEP · BREAK, by that bar's close
    touched_not_taken: bool     # TOUCHED_NOT_TAKEN: reached, and the reaching bar did not go beyond


@dataclass(frozen=True)
class Outcome:
    label: str
    primary: Interaction
    opposite: Interaction
    decided_at: int | None      # the bar that decided the label, if any
    reason: str = ""


def reached(side: int, price: float, c) -> bool:
    return c.high >= price if side > 0 else c.low <= price


def exact(side: int, price: float, c) -> bool:
    return (c.high if side > 0 else c.low) == price


def taken(side: int, price: float, c) -> bool:
    return c.high > price if side > 0 else c.low < price


def interaction(side: int, price: float, bars) -> Interaction:
    """The first exact touch, the first reach and the first take of one level over `bars`."""
    touch = reach = take = None
    by = kind = None
    for c in bars:
        if touch is None and exact(side, price, c):
            touch = c.time
        if reach is None and reached(side, price, c):
            reach, by = c.time, "CROSSED" if taken(side, price, c) else "EXACT_TOUCH"
        if take is None and taken(side, price, c):
            take = c.time
            kind = "BREAK" if (c.close > price if side > 0 else c.close < price) else "SWEEP"
            break
    return Interaction(touch, reach, by, take, kind, by == "EXACT_TOUCH")


class OutcomeEvaluator:
    """Labels one hypothesis (DEF-EV2). It sees only the hypothesis and the bars after it; it refuses a bar at or
    before t, so a policy's information and the outcome can never be mixed."""

    def evaluate(self, h: DOLHypothesis, future_bars, data_end: int | None = None, invalid_at: int | None = None,
                 boundary_at: int | None = None, bar_ms: int = 60_000) -> Outcome:
        """`future_bars`: every available bar after t, in order. `data_end`: the end of the available data (ms; the
        last bar's close). `invalid_at`: the first integrity issue after t. `boundary_at`: a contract roll or another
        data boundary after t. Bars at or after `invalid_at` / `boundary_at` are never read."""
        if any(c.time <= h.t for c in future_bars):
            raise ValueError("the outcome evaluator only reads bars after the hypothesis time")
        stop = min(x for x in (h.horizon_end, invalid_at, boundary_at) if x is not None)
        bars = [c for c in future_bars if c.time < stop]
        p = interaction(h.target_side, h.target_price, bars)
        o = interaction(h.opposite_side, h.opposite_price, bars)
        a, b = p.reached_at, o.reached_at
        if a is not None or b is not None:
            if b is None or (a is not None and a < b):
                return Outcome("PRIMARY_REACHED", p, o, a)
            if a is None or b < a:
                return Outcome("OPPOSITE_REACHED_FIRST", p, o, b)
            return Outcome("BOTH_SAME_BAR_UNRESOLVED", p, o, a, "both reached inside one bar; the order is unknown")
        if invalid_at is not None and invalid_at < h.horizon_end:
            return Outcome("DATA_INVALID", p, o, None, "an integrity issue before any decisive bar")
        if boundary_at is not None and boundary_at < h.horizon_end:
            return Outcome("CENSORED", p, o, None, "a data boundary (roll) before the horizon")
        end = data_end if data_end is not None else (future_bars[-1].time + bar_ms if future_bars else h.t + bar_ms)
        if end < h.horizon_end:
            return Outcome("CENSORED", p, o, None, "the data ends before the horizon")
        return Outcome("UNRESOLVED", p, o, None)


def distance_reference(h: DOLHypothesis) -> float | None:
    """REF-A (DEF-EV6): d(opposite) / (d(primary) + d(opposite)), the probability that a continuous, symmetric,
    driftless path started at the decision close reaches the primary first (gambler's ruin). It ignores the horizon,
    the volatility, gaps and the fact that reaching uses wicks. A yardstick for resolved outcomes, not a model."""
    dp, do = abs(h.target_price - h.close), abs(h.opposite_price - h.close)
    return do / (dp + do) if dp + do > 0 else None
