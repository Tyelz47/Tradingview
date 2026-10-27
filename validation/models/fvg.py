"""Phase 1 fair value gaps — reference model of ARCHITECTURE.md DEF-A1…A7, §3.3, §6.

Bar t = candle 3. On its close:
  1. existing open records advance (milestones start at confirmation + 1, DEF-A3),
  2. a qualifying gap creates a record (DEF-A1, DEF-A2),
  3. the engine-memory policy may release one record of that direction (DEF-A6).
"""
from __future__ import annotations

from dataclasses import dataclass

from validation.models.events import EventLog
from validation.models.types import Candle, FvgSettings


@dataclass
class Fvg:
    id: int                 # confirmation time (candle 3 open time)
    is_bull: bool
    origin_bar: int         # candle 1
    origin_time: int
    confirm_bar: int        # candle 3
    confirm_time: int
    top: float
    bottom: float
    mid: float              # CE
    size_tra: float | None  # gap / TR average at birth
    thr_tick: float
    thr_tra: float | None
    thr_rng: float | None
    extreme: float          # deepest penetration so far
    touch_bar: int | None = None
    touch_time: int | None = None
    ce_bar: int | None = None
    ce_time: int | None = None
    full_bar: int | None = None
    full_time: int | None = None
    inv_bar: int | None = None
    inv_time: int | None = None

    @property
    def dir(self) -> int:
        return 1 if self.is_bull else -1

    @property
    def is_open(self) -> bool:
        return self.inv_bar is None

    def policy_bar(self, rule: str) -> int | None:
        """DEF-A5: the milestone the display policy treats as 'mitigated'. Pure read."""
        return {"firstTouch": self.touch_bar, "midpoint": self.ce_bar,
                "fullFill": self.full_bar}.get(rule, self.inv_bar)

    def active_at(self, b: int, rule: str) -> bool:
        pb = self.policy_bar(rule)
        return self.confirm_bar <= b and (pb is None or pb > b)

    def state(self) -> dict:
        return {"id": self.id, "dir": self.dir, "confirm_bar": self.confirm_bar, "top": self.top,
                "bottom": self.bottom, "mid": self.mid, "touch_bar": self.touch_bar, "ce_bar": self.ce_bar,
                "full_bar": self.full_bar, "inv_bar": self.inv_bar, "extreme": self.extreme,
                "status": "OPEN" if self.is_open else "CLOSED"}


def true_range(c: Candle, prev: Candle | None) -> float:
    """ta.tr(true): high − low on the first bar, else the classic true range."""
    if prev is None:
        return c.high - c.low
    return max(c.high - c.low, abs(c.high - prev.close), abs(c.low - prev.close))


def sma(values: list[float], end: int, n: int) -> float | None:
    """Mean of values[end−n+1 … end]; None while fewer than n values exist (warm-up)."""
    if end < n - 1:
        return None
    return sum(values[end - n + 1:end + 1]) / n


def raw_gap(c1: Candle, c3: Candle) -> tuple[int, float, float] | None:
    """DEF-A1 geometry on candle 3: (dir, top, bottom), strict comparisons."""
    if c3.low > c1.high:
        return 1, c3.low, c1.high
    if c3.high < c1.low:
        return -1, c1.low, c3.high
    return None


def required(s: FvgSettings, tick: float, tra: float | None, rng: float | None) -> tuple[float, float | None, float | None]:
    """§6 thresholds at t−2: (tickReq, traReq, rngReq). A disabled term is 0; a warming one None."""
    tra_req = 0.0 if s.k_tra <= 0 else (None if tra is None else s.k_tra * tra)
    rng_req = 0.0 if s.k_rng <= 0 else (None if rng is None else s.k_rng * rng)
    return s.min_ticks * tick, tra_req, rng_req


def qualifies(gap: float, tick_req: float, tra_req, rng_req, eps: float) -> bool:
    """gap ≥ max(...); only the tick term carries the 0.01-tick float tolerance; None rejects."""
    return (tra_req is not None and rng_req is not None and gap >= tick_req - eps
            and gap >= tra_req and gap >= rng_req)


class FvgEngine:
    def __init__(self, s: FvgSettings, tick: float, log: EventLog):
        self.s, self.tick, self.eps, self.log = s, tick, tick * 0.01, log
        self.candles: list[Candle] = []
        self.tr: list[float] = []
        self.rng: list[float] = []
        self.bull: list[Fvg] = []          # open + closed, oldest first
        self.bear: list[Fvg] = []
        self.drop_open = 0
        self.drop_closed = 0
        self.last_drop: dict | None = None  # audit of the latest release (for the invariant monitor)

    def records(self) -> list[Fvg]:
        return self.bull + self.bear

    # ── per bar ──
    def step(self, bar: int, c: Candle) -> None:
        prev = self.candles[-1] if self.candles else None
        self.candles.append(c)
        self.tr.append(true_range(c, prev))
        self.rng.append(c.high - c.low)
        self.last_drop = None
        for z in self.bull + self.bear:
            if z.is_open and bar > z.confirm_bar:
                self._advance(z, bar, c)
        if bar >= 2:
            self._detect(bar, c)

    def references(self, bar: int) -> tuple[float | None, float | None]:
        """TR average and average range at the close of t−2 (candle 1)."""
        return sma(self.tr, bar - 2, self.s.length), sma(self.rng, bar - 2, self.s.length)

    def _detect(self, bar: int, c3: Candle) -> None:
        c1 = self.candles[bar - 2]
        geo = raw_gap(c1, c3)
        if geo is None:
            return
        d, top, bottom = geo
        tra, rng = self.references(bar)
        tick_req, tra_req, rng_req = required(self.s, self.tick, tra, rng)
        if not qualifies(top - bottom, tick_req, tra_req, rng_req, self.eps):
            return
        z = Fvg(id=c3.time, is_bull=d > 0, origin_bar=bar - 2, origin_time=c1.time, confirm_bar=bar,
                confirm_time=c3.time, top=top, bottom=bottom, mid=(top + bottom) / 2,
                size_tra=None if not tra else (top - bottom) / tra, thr_tick=tick_req, thr_tra=tra_req,
                thr_rng=rng_req, extreme=top if d > 0 else bottom)
        recs = self.bull if d > 0 else self.bear
        recs.append(z)
        self.log.emit("FVG_CREATED", d, z.id, z.origin_bar, z.mid, f"{bottom}-{top}")
        if len(recs) > self.s.memory:
            self._release(recs, d)

    def _release(self, recs: list[Fvg], d: int) -> None:
        """DEF-A6 / §3.3: the oldest closed record, else the oldest open one. Logged."""
        older = recs[:-1]
        victim = next((i for i, z in enumerate(older) if not z.is_open), 0)
        old = recs.pop(victim)
        closed_available = any(not z.is_open for z in older)
        if old.is_open:
            self.drop_open += 1
        else:
            self.drop_closed += 1
        self.last_drop = {"id": old.id, "was_open": old.is_open, "closed_available": closed_available}
        self.log.emit("FVG_DROPPED_MEMORY", d, old.id, old.origin_bar, old.mid,
                      "open record · lifecycle tracking stopped" if old.is_open else "closed record")

    def _advance(self, z: Fvg, bar: int, c: Candle) -> None:
        """DEF-A4 milestones, each stamped once; DEF-A7 same-bar order touch → CE → full → invalidation."""
        d = z.dir
        near, far = (z.top, z.bottom) if z.is_bull else (z.bottom, z.top)
        reach = c.low if z.is_bull else c.high

        def reached(level):          # bull: low ≤ level · bear: high ≥ level
            return reach <= level if z.is_bull else reach >= level

        if z.touch_bar is None and reached(near):
            z.touch_bar, z.touch_time = bar, c.time
            self.log.emit("FVG_FIRST_TOUCH", d, z.id, z.origin_bar, near, "low<=top" if z.is_bull else "high>=bottom")
        if z.ce_bar is None and reached(z.mid):
            z.ce_bar, z.ce_time = bar, c.time
            self.log.emit("FVG_CE_TOUCH", d, z.id, z.origin_bar, z.mid, "low<=CE" if z.is_bull else "high>=CE")
        if z.full_bar is None and reached(far):
            z.full_bar, z.full_time = bar, c.time
            self.log.emit("FVG_FULL_FILL", d, z.id, z.origin_bar, far, "low<=bottom" if z.is_bull else "high>=top")
        z.extreme = min(z.extreme, c.low) if z.is_bull else max(z.extreme, c.high)
        if (c.close < z.bottom) if z.is_bull else (c.close > z.top):
            z.inv_bar, z.inv_time = bar, c.time
            self.log.emit("FVG_INVALIDATED", d, z.id, z.origin_bar, c.close, "close<bottom" if z.is_bull else "close>top")

    def state(self) -> list[dict]:
        return [z.state() for z in sorted(self.records(), key=lambda z: (z.dir, z.id))]
