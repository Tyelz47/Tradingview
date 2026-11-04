"""CONTEXT-03 evaluation harness (research): TARGET UNIVERSE → HYPOTHESIS AT t → FUTURE OUTCOME LABEL → METRICS.
Pre-registered in docs/context/EVALUATION.md; data under docs/context/DATASET_CONTRACT.md.

    python -m validation.studies.context_eval

Two passes, never mixed:
* during the target-universe pass, at every pre-registered decision bar, each policy receives one frozen Snapshot
  (FEATURES_AT_T) and returns a frozen hypothesis or no hypothesis;
* after the pass, the OutcomeEvaluator receives each frozen hypothesis and only the bars after its t
  (OUTCOME_AFTER_T).

No policy is optimised here. The baselines are baselines. On the repository's sample (83 h, NQ family only, no
complete trading day) every number is descriptive.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from validation.models import targets as T
from validation.models.dol_policy import BASELINES, Snapshot
from validation.models.outcomes import NoHypothesis, OutcomeEvaluator, distance_reference
from validation.models.sessions import in_window
from validation.models.types import SessionSettings
from validation.studies.context_dataset import TZ, boundary_after, evidence_datasets, integrity, invalid_after, \
    trading_date, valid_at
from zoneinfo import ZoneInfo

WARMUP = 200                                   # the DEF-CISD9 guard: the oracle has no Pine history before a segment
H0 = "H0: 17:00 ET, the CME close of the trading day that contains the next bar"
WINDOWS = SessionSettings().windows


def horizon_h0(t: int, bar_ms: int = 60_000) -> int:
    """DEF-EV4 · H0, from the clock alone: 17:00 ET of the trading day of the minute after t."""
    d = trading_date(t + bar_ms, TZ)
    return int(datetime(d.year, d.month, d.day, 17, tzinfo=ZoneInfo(TZ)).timestamp() * 1000)


def decision_bars(cs) -> list[int]:
    """DEF-EV5: the close of the bar before every session window opens (Asia, London, NY AM, NY PM), with ≥ WARMUP
    bars before it. The opening is read from the clock (the next minute), not from a future bar."""
    out = []
    for i in range(WARMUP, len(cs)):
        a, b = cs[i].time, cs[i].time + 60_000
        if any(in_window(b, w, TZ) and not in_window(a, w, TZ) for _, w in WINDOWS):
            out.append(i)
    return out


@dataclass(frozen=True)
class Record:
    dataset: str
    underlying: str
    contract: str
    split: str
    t: int
    policy_id: str
    hypothesis: object          # DOLHypothesis | NoHypothesis | None (data invalid at t)
    outcome: object             # Outcome | None
    reference: float | None


def run_dataset(meta, seg, policies, targets=None, split_of=lambda day: "DEV", future=None) -> list[Record]:
    """One target-universe pass with hypotheses issued at the decision bars, then the outcomes. `future`, when
    given, replaces the bars the evaluator reads (tests: the future must not change a hypothesis)."""
    cs = seg.cs
    issues = integrity(cs, meta)
    want = set(decision_bars(cs))
    issued = []

    def on_bar(i, m, tu):
        if i not in want:
            return
        t = cs[i].time
        if not valid_at(issues, t, cs[0].time):
            issued.extend((i, p.policy_id, None) for p in policies)
            return
        snap = Snapshot.of(tu, cs[i].close, horizon_h0(t), H0)
        issued.extend((i, p.policy_id, p.evaluate(snap)) for p in policies)

    T.run(cs, targets=targets, provider=T.tradingview_periods(seg.htf, seg.pdx), evidence=seg.htf, on_bar=on_bar)
    bars = future if future is not None else cs
    ev, out = OutcomeEvaluator(), []
    for i, pid, h in issued:
        t = cs[i].time
        o = ref = None
        if h is not None and not isinstance(h, NoHypothesis):
            after = [c for c in bars if c.time > t]
            o = ev.evaluate(h, after, data_end=bars[-1].time + 60_000, invalid_at=invalid_after(issues, t),
                            boundary_at=boundary_after(meta, t))
            ref = distance_reference(h)
        out.append(Record(meta.id, meta.underlying, meta.contracts[0].symbol, split_of(trading_date(t)), t, pid, h, o, ref))
    return out


def metrics(records) -> dict:
    """Per (underlying, policy): every count of EVALUATION.md §6. NQ and ES are never pooled."""
    out = {}
    for r in records:
        m = out.setdefault((r.underlying, r.policy_id), Counter())
        m["decision points"] += 1
        if r.hypothesis is None:
            m["DATA_INVALID at t"] += 1
            continue
        m["eligible"] += 1
        if isinstance(r.hypothesis, NoHypothesis):
            m["NO_HYPOTHESIS"] += 1
            m[f"no hypothesis: {r.hypothesis.reason}"] += 1
            continue
        m["emitted"] += 1
        m[r.outcome.label] += 1
        p = r.outcome.primary
        m["exact touch"] += p.exact_touch_at is not None
        m["reached, not taken"] += p.reached_at is not None and p.taken_at is None
        m["taken"] += p.taken_at is not None
        m["SWEEP"] += p.taken_kind == "SWEEP"
        m["BREAK"] += p.taken_kind == "BREAK"
        if r.outcome.label in ("PRIMARY_REACHED", "OPPOSITE_REACHED_FIRST") and r.reference is not None:
            m["reference (resolved, x1000)"] += round(1000 * r.reference)
    return out


COLUMNS = ("eligible", "emitted", "NO_HYPOTHESIS", "PRIMARY_REACHED", "OPPOSITE_REACHED_FIRST", "BOTH_SAME_BAR_UNRESOLVED",
           "UNRESOLVED", "CENSORED", "DATA_INVALID", "exact touch", "reached, not taken", "taken", "SWEEP", "BREAK")


def metric_rows(ms: dict) -> list[str]:
    rows = ["| underlying | policy | " + " | ".join(COLUMNS) + " | coverage | resolved-only rate · REF-A | all-evaluable rate |",
            "|---|---|" + "---|" * (len(COLUMNS) + 3)]
    for (u, pid), m in sorted(ms.items()):
        res = m["PRIMARY_REACHED"] + m["OPPOSITE_REACHED_FIRST"]
        ev = res + m["BOTH_SAME_BAR_UNRESOLVED"] + m["UNRESOLVED"]
        cov = f"{m['emitted']}/{m['eligible']}"
        rr = f"{m['PRIMARY_REACHED']}/{res} · {m['reference (resolved, x1000)'] / 1000:.1f}" if res else "—"
        ar = f"{m['PRIMARY_REACHED']}/{ev}" if ev else "—"
        rows.append(f"| {u} | {pid} | " + " | ".join(str(m[c]) for c in COLUMNS) + f" | {cov} | {rr} | {ar} |")
    return rows


def reason_rows(ms: dict) -> list[str]:
    rows = ["| policy | ABSTAIN | NO_CANDIDATE | NO_COMPARATOR |", "|---|---|---|---|"]
    for (u, pid), m in sorted(ms.items()):
        rows.append(f"| {pid} ({u}) | " + " | ".join(str(m[f'no hypothesis: {k}']) for k in ("ABSTAIN", "NO_CANDIDATE", "NO_COMPARATOR")) + " |")
    return rows


def dataset_rows(data) -> list[str]:
    from validation.studies.context_dataset import trading_days
    rows = ["| dataset | underlying · contract | bars | trading days (complete · partial) | integrity issues | source files (SHA-256) |",
            "|---|---|---|---|---|---|"]
    for meta, seg in data:
        days = trading_days(seg.cs, meta)
        iss = Counter(x.kind for x in integrity(seg.cs, meta))
        rows.append(f"| {meta.id} | {meta.underlying} · {meta.contracts[0].symbol} | {len(seg.cs)} | "
                    f"{sum(d.complete for d in days)} · {sum(not d.complete for d in days)} | {dict(iss) or 'none'} | "
                    + "; ".join(f"{p.rsplit('/', 1)[1]} ({h[:8]}…)" for p, h in meta.files) + " |")
    return rows


def run_all(policies=BASELINES) -> tuple[list, list[Record]]:
    data = evidence_datasets()
    recs = [r for meta, seg in data for r in run_dataset(meta, seg, policies)]
    return data, recs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m validation.studies.context_eval")
    ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    data, recs = run_all()
    ms = metrics(recs)
    say = lambda *rows: print("\n".join(rows) + "\n")
    say("## Datasets under the contract\n", *dataset_rows(data))
    say("## Baselines B0…B4 (descriptive only: 83 h, NQ family, every decision point DEVELOPMENT)\n", *metric_rows(ms))
    say("## No-hypothesis reasons\n", *reason_rows(ms))
    return 0


if __name__ == "__main__":
    sys.exit(main())
