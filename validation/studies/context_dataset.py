"""CONTEXT-03 dataset contract (docs/context/DATASET_CONTRACT.md): the metadata every research dataset carries, its
integrity checks, the trading-day structure, contract roll boundaries, and the time-ordered DEVELOPMENT / OOS split
with policy locks. Research tooling only: it reads candles and never changes an oracle module.

The trading day is the CME equity-futures day in America/New_York: 18:00 → 17:00, the daily halt 17:00–18:00
Monday–Thursday, the weekend Friday 17:00 → Sunday 18:00 (the Module G / HTF boundary assumption; TradingView's own
D bars in the evidence open at 18:00 ET, also after the 2026-11-01 DST change). Exchange holidays are not modelled:
a dataset declares them, otherwise a missing day is an unscheduled gap.
"""
from __future__ import annotations

import hashlib
import inspect
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from validation.models.types import Candle

TZ = "America/New_York"
MIN = 60_000


@dataclass(frozen=True)
class ContractSpan:
    symbol: str                 # the actual contract or continuous symbol, e.g. MNQZ2026, NQ1!
    start: int                  # ms, inclusive
    end: int | None             # ms, exclusive (None: open)
    continuous: bool            # a continuous symbol (its rolls are inside the feed)
    back_adjustment: str | None = None


@dataclass(frozen=True)
class DatasetMeta:
    id: str
    underlying: str             # NQ · ES: never pooled by default
    contracts: tuple            # ContractSpan, contiguous, in order; a new span = a roll boundary
    timezone: str
    tick: float
    timeframe_sec: int
    source: str                 # e.g. "TradingView Pine-Log capture (IST v0.9.1-dev)"
    files: tuple                # ((path, sha256), …): provenance
    holidays: tuple = ()        # declared closed trading dates (date objects)
    rolls: tuple = ()           # declared roll times inside continuous spans (ms)


@dataclass(frozen=True)
class Issue:
    time: int
    kind: str                   # DUPLICATE_TIMESTAMP · NON_MONOTONIC · OFF_TICK · OHLC_INCONSISTENT · UNSCHEDULED_GAP · NO_CONTRACT
    detail: str = ""


@dataclass
class Day:
    date: date
    first: int
    last: int
    bars: int
    complete: bool
    truncated_start: bool
    truncated_end: bool
    issues: list = field(default_factory=list)


def _local(t: int, tz: str = TZ) -> datetime:
    return datetime.fromtimestamp(t / 1000, ZoneInfo(tz))


def closed(t: int, tz: str = TZ, holidays=()) -> bool:
    """The CME schedule is closed during this minute: the daily halt, the weekend, or a declared holiday."""
    d = _local(t, tz)
    if trading_date(t, tz) in holidays:
        return True
    wd, hm = d.weekday(), d.hour * 60 + d.minute
    if wd == 5 or (wd == 4 and hm >= 17 * 60) or (wd == 6 and hm < 18 * 60):
        return True
    return wd in (0, 1, 2, 3) and 17 * 60 <= hm < 18 * 60


def trading_date(t: int, tz: str = TZ) -> date:
    return (_local(t, tz) + timedelta(hours=6)).date()      # 18:00 → the next calendar date


def day_bounds(day: date, tz: str = TZ) -> tuple[int, int]:
    """(first scheduled minute, last scheduled minute) of a trading day: 18:00 the evening before (Sunday 18:00 for
    a Monday) → 16:59, both in local time, so DST never moves them."""
    z = ZoneInfo(tz)
    start = datetime(day.year, day.month, day.day, tzinfo=z) - timedelta(hours=6)    # a Monday: Sunday 18:00
    end = datetime(day.year, day.month, day.day, 16, 59, tzinfo=z)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def contract_at(meta: DatasetMeta, t: int) -> ContractSpan | None:
    return next((s for s in meta.contracts if s.start <= t and (s.end is None or t < s.end)), None)


def boundaries(meta: DatasetMeta) -> list[int]:
    """Every contract roll: the start of every span after the first, and the declared rolls inside continuous spans."""
    return sorted([s.start for s in meta.contracts[1:]] + list(meta.rolls))


def boundary_after(meta: DatasetMeta, t: int) -> int | None:
    return next((b for b in boundaries(meta) if b > t), None)


def integrity(cs: list[Candle], meta: DatasetMeta) -> list[Issue]:
    """Every integrity issue, in time order. A scheduled closure is never a gap."""
    out, step = [], meta.timeframe_sec * 1000
    for i, c in enumerate(cs):
        if contract_at(meta, c.time) is None:
            out.append(Issue(c.time, "NO_CONTRACT", "no contract span covers this bar"))
        bad = [n for n in ("open", "high", "low", "close") if abs(getattr(c, n) / meta.tick - round(getattr(c, n) / meta.tick)) > 1e-6]
        if bad:
            out.append(Issue(c.time, "OFF_TICK", ", ".join(bad)))
        if c.high < max(c.open, c.close) or c.low > min(c.open, c.close) or c.high < c.low:
            out.append(Issue(c.time, "OHLC_INCONSISTENT"))
        if i:
            p = cs[i - 1]
            if c.time == p.time:
                out.append(Issue(c.time, "DUPLICATE_TIMESTAMP"))
            elif c.time < p.time:
                out.append(Issue(c.time, "NON_MONOTONIC"))
            elif c.time - p.time > step:
                miss = [m for m in range(p.time + step, c.time, step) if not closed(m, meta.timezone, meta.holidays)]
                if miss:
                    out.append(Issue(miss[0], "UNSCHEDULED_GAP", f"{len(miss)} open bar(s) missing"))
    return sorted(out, key=lambda x: x.time)


def invalid_after(issues: list[Issue], t: int) -> int | None:
    return next((x.time for x in issues if x.time > t), None)


def valid_at(issues: list[Issue], t: int, history_from: int) -> bool:
    """No integrity issue between the start of the history the decision uses and t."""
    return not any(history_from <= x.time <= t for x in issues)


def trading_days(cs: list[Candle], meta: DatasetMeta) -> list[Day]:
    issues = integrity(cs, meta)
    by = {}
    for c in cs:
        by.setdefault(trading_date(c.time, meta.timezone), []).append(c)
    out = []
    for d, xs in sorted(by.items()):
        a, b = day_bounds(d, meta.timezone)
        own = [x for x in issues if a <= x.time <= b + MIN]
        start_ok, end_ok = xs[0].time <= a, xs[-1].time >= b
        out.append(Day(d, xs[0].time, xs[-1].time, len(xs), start_ok and end_ok and not own, not start_ok, not end_ok, own))
    return out


# ── DEVELOPMENT / OOS ──

def split(days, dev_until: date) -> dict:
    """Time-ordered: every trading day up to `dev_until` is DEVELOPMENT, every later one OOS. Never shuffled."""
    return {d: ("DEV" if d <= dev_until else "OOS") for d in days}


def fingerprint(policy) -> str:
    """The policy's semantics: its class source and its parameters. Any change gives a new fingerprint."""
    src = inspect.getsource(type(policy))
    params = repr(sorted(asdict(policy).items())) if hasattr(policy, "__dataclass_fields__") else repr(vars(policy))
    return hashlib.sha256((src + params).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PolicyLock:
    """Policies frozen before any OOS evaluation: policy_id → fingerprint. OOS refuses anything else."""
    locked: tuple               # ((policy_id, fingerprint), …)

    @staticmethod
    def of(policies) -> "PolicyLock":
        return PolicyLock(tuple(sorted((p.policy_id, fingerprint(p)) for p in policies)))

    def check(self, policy) -> None:
        want = dict(self.locked).get(policy.policy_id)
        if want is None:
            raise PermissionError(f"{policy.policy_id} is not locked: no OOS evaluation")
        if want != fingerprint(policy):
            raise PermissionError(f"{policy.policy_id} changed after its lock: no OOS evaluation")


# ── the repository's evidence under the contract ──

def evidence_datasets():
    """The four 1m segments of validation/studies/context.py under the contract: (meta, segment). No roll lies
    inside these windows (Z2026 was the front contract through the capture dates)."""
    from validation.parity import EVIDENCE
    from validation.studies.context import segments
    sums = {ln.split(" *", 1)[1].strip(): ln.split(" *", 1)[0] for ln in (EVIDENCE / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines() if " *" in ln}
    files = {0: ("ist-v0.4.3-dev_nq1-1m_capture-1000_2026-10-27.csv", "ist-v0.4.4-dev_nq1-1m_capture-1000_2026-10-28.csv"),
             1: ("ist-v0.8.0-dev_mnq-1m-replay_capture-1000_2026-10-30.csv", "ist-v0.7.0-dev_mnq-1m_capture-1000_2026-10-30.csv"),
             2: ("ist-v0.7.1-dev_mnq-1m-replay_capture-1000_2026-10-14.csv",),
             3: ("ist-v0.9.1-dev_mnq1-1m_capture-1000_2026-11-02.csv",)}
    contract = {0: ("NQ1!", True, "default"), 1: ("MNQZ2026", False, None), 2: ("MNQZ2026", False, None), 3: ("MNQ1!", True, "default")}
    out = []
    for i, seg in enumerate(segments()):
        sym, cont, adj = contract[i]
        meta = DatasetMeta(f"evidence-{i}", "NQ", (ContractSpan(sym, seg.cs[0].time, None, cont, adj),), TZ, 0.25, 60,
                           "TradingView Pine-Log capture (validation/parity/evidence)",
                           tuple((f"validation/parity/evidence/{f}", sums.get(f, "")) for f in files[i]))
        out.append((meta, seg))
    return out
