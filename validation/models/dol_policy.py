"""CONTEXT-03 research-only DOL policy interface, and the CONTEXT-01 baselines B0…B4 on the target universe.

These are BASELINES, not candidate policies. No Primary-DOL policy is approved. B3's class order exists only
inside B3: no target hierarchy is approved (CONTEXT-02, D-TU decisions). Spec: docs/context/EVALUATION.md.

    DOLPolicy.evaluate(snapshot_at_t) → DOLHypothesis | NoHypothesis

A policy receives one frozen Snapshot (the target universe at the decision bar, the close, the pre-registered
horizon) and nothing else: no bar list, no model, no future. It must name its opposite comparator at t
(DEF-EV3); a policy that cannot, emits no hypothesis.
"""
from __future__ import annotations

from dataclasses import dataclass

from validation.models.outcomes import DOLHypothesis, NoHypothesis

EXTERNAL = ("DAILY", "WEEKLY", "SESSION")                        # period and session extremes (CONTEXT-01 §4)
B3_ORDER = ("WEEKLY", "DAILY", "SESSION", "STRUCTURAL")          # B3's own rule, nothing else reads it


@dataclass(frozen=True)
class TargetView:
    id: str
    type: str
    source_class: str
    side: int
    price: float
    state: str
    history: str
    verification: tuple
    consumed: bool
    period_role: str | None


@dataclass(frozen=True)
class Snapshot:
    """FEATURES_AT_T: immutable. Built from the target universe at the decision bar only."""
    t: int
    close: float
    horizon_end: int
    horizon_rule: str
    targets: tuple              # TargetView, sorted by id

    @staticmethod
    def of(tu, close: float, horizon_end: int, horizon_rule: str) -> "Snapshot":
        rows = tuple(TargetView(x.id, x.type, x.source_class, x.side, x.price, x.state, x.history, tuple(x.verification),
                                x.consumed, x.period_role) for x in sorted(tu.targets.values(), key=lambda x: x.id))
        return Snapshot(tu.m.candles[-1].time, close, horizon_end, horizon_rule, rows)


def eligible(x: TargetView, profile: str) -> bool:
    """STRICT: the universe says AVAILABLE. PROVISIONAL: also a target that is UNVERIFIED only because its source
    gate is pending (G-V, T19–T22), with its history observed and never consumed. PROVISIONAL results are
    conditional on those gates and are labelled so."""
    if x.state == "AVAILABLE":
        return True
    return profile == "PROVISIONAL" and x.state == "UNVERIFIED" and not x.consumed and x.history == "OBSERVED" \
        and all(v.startswith("SOURCE_PENDING") for v in x.verification)


def nearest(xs, side: int, p: float) -> TargetView | None:
    return min((x for x in xs if x.side == side), key=lambda x: (abs(x.price - p), x.id), default=None)


@dataclass(frozen=True)
class Baseline:
    """One of B0…B4 (DOL_RESEARCH §9, recomputed on the target universe). `profile`: STRICT or PROVISIONAL."""
    name: str
    profile: str = "STRICT"

    @property
    def policy_id(self) -> str:
        return f"{self.name}@{self.profile}"

    def evaluate(self, s: Snapshot) -> DOLHypothesis | NoHypothesis:
        p = s.close
        av = [x for x in s.targets if eligible(x, self.profile)]
        ext = [x for x in av if x.source_class in EXTERNAL]
        if self.name == "B0":                       # nearest external; comparator: nearest external on the other side
            pick, pool = self._nearest_either(ext, p), ext
        elif self.name == "B1":                     # nearest of any class; comparator: nearest of any class opposite
            pick, pool = self._nearest_either(av, p), av
        elif self.name == "B2":                     # the nearer of the current PDH / PDL; comparator: the other one
            pair = {x.type: x for x in av if x.type in ("PDH", "PDL") and x.period_role == "CURRENT"}
            if len(pair) < 2:
                return NoHypothesis(self.policy_id, s.t, "NO_CANDIDATE" if not pair else "NO_COMPARATOR")
            u, d = pair["PDH"], pair["PDL"]
            x, o = (u, d) if u.price - p <= p - d.price else (d, u)
            return self._h(s, x, o)
        elif self.name == "B3":                     # the highest class present by B3_ORDER; comparator in that class
            top = next((c for c in B3_ORDER if any(x.source_class == c for x in av)), None)
            pool = [x for x in av if x.source_class == top]
            pick = self._nearest_either(pool, p)
        elif self.name == "B4":                     # abstain when external targets exist on both sides
            if nearest(ext, 1, p) and nearest(ext, -1, p):
                return NoHypothesis(self.policy_id, s.t, "ABSTAIN")
            pick, pool = self._nearest_either(ext, p), av
        else:
            raise ValueError(self.name)
        if pick is None:
            return NoHypothesis(self.policy_id, s.t, "NO_CANDIDATE")
        o = nearest(pool, -pick.side, p)
        return NoHypothesis(self.policy_id, s.t, "NO_COMPARATOR") if o is None else self._h(s, pick, o)

    @staticmethod
    def _nearest_either(xs, p) -> TargetView | None:
        u, d = nearest(xs, 1, p), nearest(xs, -1, p)
        if u is None or d is None:
            return u or d
        return u if u.price - p <= p - d.price else d          # a tie goes above (fixed before any outcome)

    def _h(self, s: Snapshot, x: TargetView, o: TargetView) -> DOLHypothesis:
        return DOLHypothesis(self.policy_id, s.t, x.id, x.side, x.price, o.id, o.side, o.price, s.close, s.horizon_end,
                             s.horizon_rule, (("source_class", x.source_class), ("opposite_class", o.source_class)))


BASELINES = tuple(Baseline(n, pr) for pr in ("STRICT", "PROVISIONAL") for n in ("B0", "B1", "B2", "B3", "B4"))
