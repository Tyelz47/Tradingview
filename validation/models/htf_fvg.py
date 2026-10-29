"""HTF fair value gaps — reference model of docs/HTF_FVG.md DEF-B0…B6 (approved 2026-10-29).

Six timeframes (15m, 30m, 1H, 4H, 1D, 1W), each active only above the chart timeframe and
each an independent registry: records of different timeframes are never merged (identity
= timeframe + direction + HTF candle-3 open time). The FVG definition and its thresholds
are the frozen Phase 1 ones (DEF-A1, DEF-A2; validation/models/fvg.py).

Per chart bar t (decided at the bar's close), per timeframe, in this order:
  0. SEED on the first chart bar at which a completed HTF bar exists: the K newest zones
     per direction that the HTF-side engine holds open as of the last completed HTF bar
     (DEF-B2). Nothing else completes on that bar.
  1. When an HTF bar has just completed (the first chart bar of the next HTF period; Pine:
     request.security with [1] and lookahead_on): INVALIDATE the open records whose zone
     that bar CLOSED beyond (own-timeframe close, DEF-B4), then CREATE the zone whose
     candle 3 is that bar (DEF-B1).
  2. MILESTONES on this chart bar's wicks for every record not invalidated, including one
     created or seeded on this bar (DEF-B3: the lifecycle starts on the bar it is known).
The unfinished HTF bar is never read.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from validation.models.events import EventLog
from validation.models.fvg import qualifies, raw_gap, required, sma, true_range
from validation.models.lrl import fx
from validation.models.types import Candle, FvgSettings, HtfSettings

NAMES = {"15": "15m", "30": "30m", "60": "1H", "240": "4H", "D": "1D", "W": "1W"}
SECONDS = {"15": 900, "30": 1800, "60": 3600, "240": 14400, "D": 86400, "W": 604800}
CODES = {v: k for k, v in NAMES.items()}


def bucket(ms: int, tf: str, tz: str = "America/New_York", hour: int = 18) -> int:
    """Open time (ms) of the `tf` bar containing ms. 15m / 30m / 1H: clock-aligned in tz.
    4H / 1D / 1W: from the session start at `hour` (CME 18:00 New York), the week from
    Sunday's session. TradingView's own HTF candles are the truth; the parity capture checks
    this alignment against them."""
    dt = datetime.fromtimestamp(ms / 1000, ZoneInfo(tz))
    if tf in ("15", "30", "60"):
        m = (dt.hour * 60 + dt.minute) // int(tf) * int(tf)
        start = dt.replace(hour=m // 60, minute=m % 60, second=0, microsecond=0)
    else:
        start = dt.replace(hour=hour, minute=0, second=0, microsecond=0)
        if dt.hour < hour:
            start -= timedelta(days=1)
        if tf == "240":
            start += timedelta(hours=4 * int((dt - start).total_seconds() // 14400))
        elif tf == "W":
            while start.weekday() != 6:
                start -= timedelta(days=1)
    return int(start.timestamp() * 1000)


@dataclass
class HtfBar:
    """One completed HTF bar, with the DEF-A2 references at it (TR average, average range)."""
    time: int
    open: float
    high: float
    low: float
    close: float
    tra: float | None = None
    rng: float | None = None

    @property
    def candle(self) -> Candle:
        return Candle(self.time, self.open, self.high, self.low, self.close)


@dataclass
class HtfFvg:
    tf: str
    dir: int
    id: int                     # HTF candle-3 open time
    c1_time: int                # HTF candle-1 open time: the box's visual origin (D8)
    top: float
    bottom: float
    known_bar: int              # the chart bar where it became known (lifecycle starts here)
    known_time: int
    seeded: bool = False
    pre_touch: bool = False     # seeded: touched / CE before the chart history (no event)
    pre_ce: bool = False
    touch_bar: int | None = None
    ce_bar: int | None = None
    full_bar: int | None = None
    inv_bar: int | None = None
    inv_close: float | None = None

    @property
    def mid(self) -> float:
        return (self.top + self.bottom) / 2

    @property
    def open(self) -> bool:
        return self.inv_bar is None

    @property
    def shown(self) -> bool:
        """DEF-B5 display policy (full fill): untouched or partially filled, not invalidated."""
        return self.inv_bar is None and self.full_bar is None

    def state(self) -> dict:
        return {"tf": self.tf, "dir": self.dir, "id": self.id, "c1": self.c1_time, "top": self.top,
                "bottom": self.bottom, "known_bar": self.known_bar, "seeded": self.seeded,
                "pre_touch": self.pre_touch, "pre_ce": self.pre_ce, "touch_bar": self.touch_bar,
                "ce_bar": self.ce_bar, "full_bar": self.full_bar, "inv_bar": self.inv_bar}


@dataclass
class Side:
    tf: str
    bars: list = field(default_factory=list)       # completed HTF bars (also before the chart, via `pre`)
    cur: list | None = None                         # the HTF bar in progress: [open time, o, h, l, c]
    tr: list = field(default_factory=list)
    rngs: list = field(default_factory=list)
    recs: list = field(default_factory=list)        # the registry, in registration order
    seeds: list = field(default_factory=list)       # HTF-side engine: open zones [dir, top, bottom, c1, c3, ext]
    started: bool = False                           # the seed point has passed
    last_c3: int | None = None
    created: int = 0
    seeded: int = 0
    dropped: int = 0
    last_drop: dict | None = None

    @property
    def name(self) -> str:
        return NAMES[self.tf]


class HtfEngine:
    def __init__(self, s: HtfSettings, fvg: FvgSettings, tick: float, log: EventLog, pre=None, external=None):
        """`pre`: chart candles before the chart history (what the HTF context saw before the
        first loaded bar). `external`: {chart bar index: {tf: HtfBar}} to feed completed HTF
        bars from a Pine capture instead of aggregating the chart bars (parity replay)."""
        self.s, self.fvg, self.tick, self.eps, self.log = s, fvg, tick, tick * 0.01, log
        self.external = external
        self.sides = [Side(tf) for tf in s.tfs if SECONDS[tf] > s.chart_sec]
        for c in pre or ():
            for side in self.sides:
                done = self._aggregate(side, c)
                if done is not None:
                    self._seed_engine(side, done)

    # ── HTF bars ──
    def _aggregate(self, side: Side, c: Candle) -> HtfBar | None:
        """Adds a chart bar; returns the HTF bar that completed when this bar opened a new one."""
        k = bucket(c.time, side.tf, self.s.timezone, self.s.session_hour)
        done = None
        if side.cur is not None and side.cur[0] != k:
            done = self._close(side, side.cur)
            side.cur = None
        if side.cur is None:
            side.cur = [k, c.open, c.high, c.low, c.close]
        else:
            side.cur[2], side.cur[3], side.cur[4] = max(side.cur[2], c.high), min(side.cur[3], c.low), c.close
        return done

    def _close(self, side: Side, cur: list) -> HtfBar:
        b = HtfBar(*cur)
        prev = side.bars[-1].candle if side.bars else None
        side.tr.append(true_range(b.candle, prev))
        side.rngs.append(b.high - b.low)
        b.tra = sma(side.tr, len(side.tr) - 1, self.fvg.length)
        b.rng = sma(side.rngs, len(side.rngs) - 1, self.fvg.length)
        side.bars.append(b)
        return b

    def _zone(self, side: Side) -> tuple | None:
        """DEF-B1 = DEF-A1 / DEF-A2 on the last three completed HTF bars: (dir, top, bottom, c1, c3)."""
        if len(side.bars) < 3:
            return None
        c1, c3 = side.bars[-3], side.bars[-1]
        geo = raw_gap(c1.candle, c3.candle)
        if geo is None:
            return None
        d, top, bottom = geo
        if not qualifies(top - bottom, *required(self.fvg, self.tick, c1.tra, c1.rng), self.eps):
            return None
        return d, top, bottom, c1.time, c3.time

    def _seed_engine(self, side: Side, b: HtfBar) -> None:
        """The HTF-side engine (inside Pine's request.security): open zones at HTF resolution."""
        keep = []
        for z in side.seeds:
            d, top, bottom, c1, c3, ext = z
            if c3 < b.time:
                if d > 0:
                    ext = b.low if ext is None else min(ext, b.low)
                else:
                    ext = b.high if ext is None else max(ext, b.high)
                z[5] = ext
                if (d > 0 and (b.low <= bottom or b.close < bottom)) or (d < 0 and (b.high >= top or b.close > top)):
                    continue
            keep.append(z)
        side.seeds = keep
        zone = self._zone(side)
        if zone is not None:
            side.seeds.append([*zone, None])
        for d in (1, -1):
            mine = [z for z in side.seeds if z[0] == d]
            for z in mine[:max(0, len(mine) - self.s.seed_memory)]:
                side.seeds.remove(z)

    # ── per chart bar ──
    def step(self, bar: int, c: Candle) -> None:
        for side in self.sides:
            if self.external is None:
                done = self._aggregate(side, c)
            else:
                done = self.external.get(bar, {}).get(side.tf)
                if done is not None:
                    side.bars.append(done)
            if done is not None:
                self._seed_engine(side, done)
            if not side.started:
                if side.bars:                               # 0. the seed point
                    side.started = True
                    side.last_c3 = side.bars[-1].time
                    self._seed(side, bar, c)
            elif done is not None:                          # 1. a newly completed HTF bar
                self._complete(side, bar, c, done)
            self._milestones(side, bar, c)                  # 2.

    def _seed(self, side: Side, bar: int, c: Candle) -> None:
        for d in (1, -1):
            for dd, top, bottom, c1, c3, ext in [z for z in side.seeds if z[0] == d][-self.s.seeds:]:
                if any(r.dir == d and r.id == c3 for r in side.recs):
                    continue
                r = HtfFvg(side.tf, d, c3, c1, top, bottom, bar, c.time, seeded=True)
                if ext is not None:
                    r.pre_touch = ext <= top if d > 0 else ext >= bottom
                    r.pre_ce = ext <= r.mid if d > 0 else ext >= r.mid
                side.recs.append(r)
                side.seeded += 1
                self.log.emit("HTF_FVG_SEEDED", d, c3, bar, r.mid, f"tf={side.name} · bottom={fx(bottom)} · top={fx(top)} · "
                              f"c1={c1} · ext={'na' if ext is None else fx(ext)}", side.tf)
                self._trim(side)

    def _complete(self, side: Side, bar: int, c: Candle, done: HtfBar) -> None:
        for r in side.recs:
            if r.inv_bar is None and done.time > r.id and (
                    (r.dir > 0 and done.close < r.bottom) or (r.dir < 0 and done.close > r.top)):
                r.inv_bar, r.inv_close = bar, done.close
                self.log.emit("HTF_FVG_INVALIDATED", r.dir, r.id, r.known_bar, done.close,
                              f"tf={side.name} · close={fx(done.close)}", side.tf)
        side.last_c3 = done.time
        zone = self._zone(side)
        if zone is not None:
            d, top, bottom, c1, c3 = zone
            if not any(r.dir == d and r.id == c3 for r in side.recs):
                r = HtfFvg(side.tf, d, c3, c1, top, bottom, bar, c.time)
                side.recs.append(r)
                side.created += 1
                self.log.emit("HTF_FVG_CREATED", d, c3, bar, r.mid,
                              f"tf={side.name} · bottom={fx(bottom)} · top={fx(top)} · c1={c1}", side.tf)
                self._trim(side)

    def _milestones(self, side: Side, bar: int, c: Candle) -> None:
        for r in side.recs:
            if r.inv_bar is not None:
                continue
            reach = c.low if r.dir > 0 else c.high
            beyond = (lambda p: reach <= p) if r.dir > 0 else (lambda p: reach >= p)
            near, far = (r.top, r.bottom) if r.dir > 0 else (r.bottom, r.top)
            for attr, price, pre, typ in (("touch_bar", near, r.pre_touch, "HTF_FVG_FIRST_TOUCH"),
                                          ("ce_bar", r.mid, r.pre_ce, "HTF_FVG_CE_TOUCH"),
                                          ("full_bar", far, False, "HTF_FVG_FULL_FILL")):
                if getattr(r, attr) is None and not pre and beyond(price):
                    setattr(r, attr, bar)
                    self.log.emit(typ, r.dir, r.id, r.known_bar, price, f"tf={side.name}", side.tf)

    def _trim(self, side: Side) -> None:
        """DEF-B6: at most `memory` records per timeframe; the oldest fully filled or invalidated
        record goes first, else the oldest one."""
        if len(side.recs) <= self.s.memory:
            return
        done = next((r for r in side.recs if r.inv_bar is not None or r.full_bar is not None), None)
        side.last_drop = {"open": done is None, "done_available": done is not None}
        old = done or side.recs[0]
        side.recs.remove(old)
        side.dropped += 1
        self.log.emit("HTF_FVG_DROPPED_MEMORY", old.dir, old.id, old.known_bar, old.mid,
                      f"tf={side.name} · {'closed record' if done else 'open record · tracking stopped'}", side.tf)

    # ── parity replay ──
    def restore(self, side_tf: str, last_c3: int, bars: list, recs: list) -> None:
        """Start a timeframe from a Pine snapshot (Parity capture): its last completed HTF bars,
        the last candle-3 time and its registry. The seed point is then over."""
        side = next(x for x in self.sides if x.tf == side_tf)
        side.bars, side.recs, side.last_c3, side.started = list(bars), list(recs), last_c3, True

    def state(self) -> dict:
        return {"records": [r.state() for side in self.sides for r in side.recs],
                "counters": {side.name: {"created": side.created, "seeded": side.seeded, "dropped": side.dropped,
                                         "records": len(side.recs), "shown": sum(r.shown for r in side.recs)}
                             for side in self.sides}}
