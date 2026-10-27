"""Daily / weekly reference levels — the chart-side logic of ARCHITECTURE.md DEF-G2…G6.

What is reproducible here, and what is not:
  * The VALUES of PDH/PDL/PWH/PWL come from request.security on TradingView's Daily
    and Weekly bars. They are NOT reproducible from chart candles alone. The model
    takes them from an `htf` provider; by default it uses the chart aggregate of the
    previous period when that period was fully observed, else no value.
  * The period boundary is an ASSUMPTION (LevelSettings): 18:00 ET day, Sunday 18:00
    ET week (§7.2, unverified until G-V1…G-V5). It is not labelled "CME ETH".
  * Reproduced exactly: roll timing, LEVEL_SET events, seeding on the first bar,
    the DEF-G3 anchor, the DEF-G6 source check, the day open and the midnight open.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from validation.models.events import LEVEL_KINDS, EventLog
from validation.models.sessions import local
from validation.models.types import Candle, LevelSettings


@dataclass
class RefLevel:
    kind: int
    tag: str
    price: float
    anchor_time: int | None
    known_time: int
    end_time: int | None = None

    def state(self) -> dict:
        return {"tag": self.tag, "price": self.price, "anchor_time": self.anchor_time, "known_time": self.known_time}


@dataclass
class Period:
    key: tuple
    full: bool              # its start was observed on the chart
    hi: float
    hi_time: int
    lo: float
    lo_time: int


class LevelEngine:
    def __init__(self, s: LevelSettings, tick: float, log: EventLog, htf=None):
        """htf(kind, previous_period_key, previous_period) -> (high, low) | None, kind 'D' or 'W'."""
        self.s, self.log, self.half = s, log, tick * 0.5
        self.htf = htf or self.chart_aggregate
        self.intraday = s.timeframe_sec < 86400
        self.ses_ok = s.timeframe_sec <= 3600
        self.live: dict[int, RefLevel] = {}
        self.history: list[RefLevel] = []
        self.day: Period | None = None
        self.week: Period | None = None
        self.checks = {"D": [0, 0], "W": [0, 0]}      # DEF-G6: [complete periods compared, mismatches]
        self.prev: Candle | None = None

    # ── period keys (the ASSUMPTION lives here) ──
    def day_key(self, t: int) -> tuple:
        d = local(t, self.s.timezone) + timedelta(hours=24 - self.s.day_start_hour)
        return (d.year, d.month, d.day)

    def week_key(self, t: int) -> tuple:
        d = local(t, self.s.timezone) + timedelta(hours=24 - self.s.day_start_hour)
        iso = d.isocalendar()
        return (iso[0], iso[1])

    @staticmethod
    def chart_aggregate(kind: str, key, period: Period | None):
        """Default provider: the chart-aggregated previous period, if it was complete."""
        return (period.hi, period.lo) if period is not None and period.full else None

    def step(self, bar: int, c: Candle) -> None:
        prev, self.prev = self.prev, c
        if not self.intraday:
            return
        first = prev is None
        new_day = not first and self.day_key(c.time) != self.day_key(prev.time)
        new_week = not first and self.week_key(c.time) != self.week_key(prev.time)
        if first or new_day:
            self.day = self._roll("D", self.day, c, new_day, first, ("PDH", "PDL"))
            if new_day:
                self._set("DO", 0, c.open, c.time, c)
        else:
            self._extend(self.day, c)
        if first or new_week:
            self.week = self._roll("W", self.week, c, new_week, first, ("PWH", "PWL"))
        else:
            self._extend(self.week, c)
        if self.ses_ok and not first:                  # DEF-G4 midnight open
            d, pd = local(c.time, self.s.timezone), local(prev.time, self.s.timezone)
            if d.hour == 0 and d.day != pd.day:
                self._set("MO", 0, c.open, c.time, c)

    def _roll(self, kind: str, old: Period | None, c: Candle, is_new: bool, first: bool, tags) -> Period:
        key = (self.day_key if kind == "D" else self.week_key)(c.time)
        prev_key = None if old is None else old.key
        val = self.htf(kind, prev_key, old)
        if val is not None and old is not None and old.full and is_new:   # DEF-G6, complete periods only
            self.checks[kind][0] += 1
            if abs(old.hi - val[0]) >= self.half or abs(old.lo - val[1]) >= self.half:
                self.checks[kind][1] += 1
        if val is not None:
            hi, lo = val
            self._set(tags[0], 1, hi, self._anchor(old, True, hi), c)
            self._set(tags[1], -1, lo, self._anchor(old, False, lo), c)
        return Period(key=key, full=not first, hi=c.high, hi_time=c.time, lo=c.low, lo_time=c.time)

    def _anchor(self, p: Period | None, high: bool, htf_px: float) -> int | None:
        """DEF-G3: the chart bar that printed the extreme, only if the chart extreme equals the HTF value."""
        if p is None:
            return None
        px, t = (p.hi, p.hi_time) if high else (p.lo, p.lo_time)
        return t if abs(px - htf_px) < self.half else None

    @staticmethod
    def _extend(p: Period, c: Candle) -> None:
        if c.high > p.hi:
            p.hi, p.hi_time = c.high, c.time
        if c.low < p.lo:
            p.lo, p.lo_time = c.low, c.time

    def _set(self, tag: str, d: int, price: float, anchor: int | None, c: Candle) -> None:
        kind = LEVEL_KINDS[tag]
        old = self.live.get(kind)
        if old is not None:
            old.end_time = c.time
            self.history.append(old)
        self.live[kind] = RefLevel(kind=kind, tag=tag, price=price, anchor_time=anchor, known_time=c.time)
        self.log.emit("LEVEL_SET", d, kind, self.log.bar, price, tag)

    def state(self) -> list[dict]:
        return [self.live[k].state() for k in sorted(self.live)]
