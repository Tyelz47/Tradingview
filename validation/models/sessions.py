"""Sessions — reference model of ARCHITECTURE.md DEF-F1…F6.

Membership is decided from the bar's open time in the session timezone (DST is
handled by the IANA database). Pine computes the same thing with
time(timeframe.period, "HHMM-HHMM:1234567", tz); that call itself is not tested
here (MANUAL / TRADINGVIEW).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from validation.models.events import EventLog
from validation.models.types import Candle, SessionSettings


def parse_window(spec: str) -> tuple[int, int]:
    a, b = spec.split("-")
    return int(a[:2]) * 60 + int(a[2:]), int(b[:2]) * 60 + int(b[2:])


@lru_cache(maxsize=None)
def _zone(tz: str) -> ZoneInfo:
    return ZoneInfo(tz)


def local(t_ms: int, tz: str) -> datetime:
    return datetime.fromtimestamp(t_ms / 1000, _zone(tz))


def in_window(t_ms: int, spec: str, tz: str) -> bool:
    """DEF-F1: [start, end) in local minutes; end ≤ start means the window crosses midnight."""
    start, end = parse_window(spec)
    d = local(t_ms, tz)
    m = d.hour * 60 + d.minute
    return start <= m < end if start < end else (m >= start or m < end)


@dataclass
class SessionRange:
    id: int                 # start time
    slot: int
    name: str
    start_bar: int
    start_time: int
    hi: float
    lo: float
    hi_time: int
    lo_time: int
    end_bar: int | None = None      # last bar inside the window
    end_time: int | None = None
    known_time: int | None = None   # when the final values became known (first bar outside)
    complete: bool = False

    def state(self) -> dict:
        return {"id": self.id, "slot": self.slot, "name": self.name, "start_bar": self.start_bar,
                "end_bar": self.end_bar, "hi": self.hi, "lo": self.lo, "hi_time": self.hi_time,
                "lo_time": self.lo_time, "complete": self.complete}


class SessionEngine:
    def __init__(self, s: SessionSettings, log: EventLog):
        self.s, self.log = s, log
        self.tf_ok = s.timeframe_sec <= 3600          # Pine sesTfOk (intraday ≤ 1H)
        self.live: list[SessionRange | None] = [None] * len(s.windows)
        self.done: list[SessionRange] = []            # superseded instances (logical history)
        self.prev: Candle | None = None

    def step(self, bar: int, c: Candle) -> None:
        prev, self.prev = self.prev, c
        if not self.tf_ok:
            return
        for slot, (name, spec) in enumerate(self.s.windows):
            in_now = in_window(c.time, spec, self.s.timezone)
            in_prev = prev is not None and in_window(prev.time, spec, self.s.timezone)
            cur = self.live[slot]
            if in_now and not in_prev and bar > 0:            # DEF-F2: never the first loaded bar
                if cur is not None:                             # DEF-F6: supersession
                    if not cur.complete:
                        self._finalize(cur, bar, prev, c)
                    self.done.append(cur)
                new = SessionRange(id=c.time, slot=slot, name=name, start_bar=bar, start_time=c.time,
                                   hi=c.high, lo=c.low, hi_time=c.time, lo_time=c.time)
                self.live[slot] = new
                self.log.emit("SESSION_START", 0, new.id, bar, None, name)
            elif cur is not None and not cur.complete:
                if in_now:                                      # DEF-F3
                    if c.high > cur.hi:
                        cur.hi, cur.hi_time = c.high, c.time
                    if c.low < cur.lo:
                        cur.lo, cur.lo_time = c.low, c.time
                else:                                           # DEF-F4
                    self._finalize(cur, bar, prev, c)

    def _finalize(self, s: SessionRange, bar: int, prev: Candle, c: Candle) -> None:
        s.complete = True
        s.end_bar, s.end_time, s.known_time = bar - 1, prev.time, c.time
        self.log.emit("SESSION_END", 0, s.id, s.start_bar, None, f"{s.name} H {s.hi} L {s.lo}")

    def state(self) -> list[dict]:
        return [s.state() for s in self.done + [x for x in self.live if x is not None]]
