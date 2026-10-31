"""CISD — reference model of docs/CISD.md DEF-CISD1…CISD9 (CISD-R, approved 2026-10-30).

Change in state of delivery. Written once for the BULLISH CISD, on side coordinates; the
BEARISH CISD runs the same code on the mirrored candle (open, close negated; high ↔ −low), so
mirror symmetry holds by construction. Bullish vocabulary (bearish = mirrored):

  delivery candle   close < open − EPS (down-close). A doji (|close − open| ≤ EPS) is not one
                    and ends a series (DEF-CISD1)
  delivery series   a maximal run of consecutive delivery candles
  delivery state    UNKNOWN until the first CISD, then UP (after a bullish CISD) or DOWN; CISDs
                    alternate (DEF-CISD4)
  leg window        the bars searched for the side's delivery extreme: from bar 0 while the
                    state is UNKNOWN, else from the extreme of the leg before it (DEF-CISD2)
  level L           the OPEN of the first candle of the series holding the leg's lowest delivery
                    low; an equal low moves it to the later candle (DEF-CISD3)
  confirmation      the first later close strictly beyond L: close > L + EPS, any colour (DEF-CISD5)

Per bar t (Confirmed mode: every bar is closed):
  1. record facts of the active CISD: retest, close back through L, close beyond its leg extreme;
  2. per side: series bookkeeping; a delivery candle at or beyond the side's extreme moves the
     extreme and the reference L;
  3. the armed side's new extreme restarts the state side's window there (the turn moved);
  4. confirmation of an armed side (both are armed while UNKNOWN; never both on one bar, DEF-CISD4);
  5. a CISD flips the state: the opposite side's window restarts at this leg's extreme, this
     side's at the opposite extreme; the previous CISD ends; memory (DEF-CISD7).
Detection reads bars only: no Phase 1 / 2, LRL or HTF FVG state, no context (DEF-CISD8). The
body / TR average of the confirming candle is metadata for a future displacement module: no
decision reads it. The display / alert guard (DEF-CISD9) is a view setting: no decision reads it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from validation.models.events import EventLog
from validation.models.fvg import sma, true_range
from validation.models.lrl import fx
from validation.models.types import Candle, CisdSettings

UNKNOWN = 0
STATE = {0: "UNKNOWN", 1: "UP", -1: "DOWN"}     # delivery state: UP after a bullish CISD, DOWN after a bearish one
SIDE = {1: "BULL", -1: "BEAR"}


@dataclass
class Cisd:
    """One confirmed CISD. Prices are real prices."""
    id: int                     # open time of the origin candle (unique per side)
    side: int                   # +1 bullish · −1 bearish
    before: int                 # delivery state before it: UNKNOWN (first CISD) or −side; after it: side
    level: float                # L: the open of the origin candle
    origin: int                 # first candle of the delivery series (the anchor; the line starts here)
    ext_bar: int                # the delivery extreme that selected the series
    ext: float                  # its low (bullish) / high (bearish)
    leg_ext: float              # lowest low (bullish) from the origin to the confirmation, any candle
    known: int                  # bar at whose close this reference was (re)selected
    bar: int                    # confirmation bar
    time: int
    close: float                # confirmation close
    body_k: float | None        # side × (close − open) / TR average before the bar: metadata only
    end: int | None = None      # the opposite CISD's bar: ACTIVE → ENDED
    retest: int | None = None   # first later bar whose wick reaches L
    reclaim: int | None = None  # first later bar that closes back at or through L
    broken: int | None = None   # first later bar that closes beyond the leg extreme

    @property
    def status(self) -> str:
        return "ACTIVE" if self.end is None else "ENDED"


def audit(r: Cisd, ext_time: int) -> str:
    """The CISD_CONFIRMED audit text, as src/IST.pine f_cisdTxt writes it (parsed by the parity tool)."""
    return (f"prev={STATE[r.before]} · close={fx(r.close)} · ext={fx(r.ext)} · et={ext_time} · "
            f"bk={'na' if r.body_k is None else fx(r.body_k)}")


class _Side:
    def __init__(self, s: int):
        self.s = s
        self.o: list[float] = []            # side coordinates
        self.lo: list[float] = []
        self.cl: list[float] = []
        self.run_of: list = []              # per bar: first bar of its delivery series (None: not a delivery candle)
        self.in_run = False
        self.run_start = 0
        self.armed = True                   # may confirm (both while UNKNOWN, then only the side against the state)
        self.arm = 0                        # first bar of the leg window
        self.since = -1                     # confirmation only after this bar (the last flip)
        self.ext: float | None = None
        self.ext_bar: int | None = None
        self.ref: tuple | None = None       # (origin, L, known), side coordinates


class CisdEngine:
    def __init__(self, s: CisdSettings, tick: float, log: EventLog):
        self.s, self.log, self.eps = s, log, tick * 0.01
        self.candles: list[Candle] = []
        self.tr: list[float] = []
        self.sides = {1: _Side(1), -1: _Side(-1)}
        self.delivery = UNKNOWN
        self.recs: list[Cisd] = []
        self.confirmed = self.dropped = self.max_scan = 0

    @property
    def active(self) -> Cisd | None:
        return self.recs[-1] if self.recs and self.recs[-1].end is None else None

    def step(self, t: int, c: Candle) -> None:
        eps = self.eps
        self.tr.append(true_range(c, self.candles[-1] if self.candles else None))
        self.candles.append(c)
        for sd in self.sides.values():
            o, lo, cl = (c.open, c.low, c.close) if sd.s > 0 else (-c.open, -c.high, -c.close)
            sd.o.append(o)
            sd.lo.append(lo)
            sd.cl.append(cl)
        r = self.active                                   # 1. facts, from the bar after the confirmation
        if r is not None:
            sd, lv = self.sides[r.side], r.side * r.level
            if r.retest is None and sd.lo[t] <= lv + eps:
                r.retest = t
            if r.reclaim is None and sd.cl[t] <= lv + eps:
                r.reclaim = t
            if r.broken is None and sd.cl[t] < r.side * r.leg_ext - eps:
                r.broken = t
        for sd in self.sides.values():                    # 2. series, extreme, reference
            if sd.cl[t] < sd.o[t] - eps:
                if not sd.in_run:
                    sd.in_run, sd.run_start = True, t
                sd.run_of.append(sd.run_start)
                if sd.ext is None or sd.lo[t] <= sd.ext + eps:
                    sd.ext, sd.ext_bar = sd.lo[t], t
                    sd.ref = (sd.run_start, sd.o[sd.run_start], t)
            else:
                sd.in_run = False                         # an opposite candle or a doji ends the series
                sd.run_of.append(None)
        if self.delivery != UNKNOWN and self.sides[-self.delivery].ext_bar == t:
            self._restart(self.sides[self.delivery], t, t)   # 3. the turn moved here
        hits = [sd for sd in self.sides.values() if sd.armed and sd.ref is not None and t > sd.ref[0]
                and t > sd.since and sd.cl[t] > sd.ref[1] + eps]
        assert len(hits) <= 1, "two CISDs on one bar: impossible by DEF-CISD4 (docs/CISD.md)"
        if hits:                                          # 4.
            self._confirm(hits[0], t)

    def _restart(self, sd: _Side, a: int, t: int) -> None:
        """The leg window of `sd` becomes [a, t]: its extreme and reference are recomputed."""
        sd.arm, sd.ext, sd.ext_bar = a, None, None
        for j in range(a, t + 1):
            if sd.cl[j] < sd.o[j] - self.eps and (sd.ext is None or sd.lo[j] <= sd.ext + self.eps):
                sd.ext, sd.ext_bar = sd.lo[j], j
        sd.ref = None if sd.ext_bar is None else (sd.run_of[sd.ext_bar], sd.o[sd.run_of[sd.ext_bar]], t)
        self.max_scan = max(self.max_scan, t - a + 1)

    def _confirm(self, sd: _Side, t: int) -> None:
        s, (origin, lv, known), c = sd.s, sd.ref, self.candles[t]
        tra = sma(self.tr, t - 1, self.s.tra_len)
        r = Cisd(self.candles[origin].time, s, self.delivery, s * lv, origin, sd.ext_bar, s * sd.lo[sd.ext_bar],
                 s * min(sd.lo[origin:t + 1]), known, t, c.time, c.close, s * (c.close - c.open) / tra if tra else None)
        if self.active is not None:
            self.active.end = t
        self.recs.append(r)
        self.confirmed += 1
        self.delivery = s                                 # 5. flip
        op = self.sides[-s]
        self._restart(op, r.ext_bar, t)
        self._restart(sd, op.ext_bar if op.ext_bar is not None else t, t)
        sd.armed = False
        op.armed, op.since = True, t
        self.log.emit("CISD_CONFIRMED", s, r.id, origin, r.level, audit(r, self.candles[r.ext_bar].time))
        if len(self.recs) > self.s.memory:               # the oldest goes; it is never the active one
            old = self.recs.pop(0)
            self.dropped += 1
            self.log.emit("CISD_DROPPED_MEMORY", old.side, old.id, old.origin, old.level, "ended record")

    # ── view (DEF-CISD9): reads records only; the engine never calls these ──
    def visible(self, previous: bool = False) -> list[Cisd]:
        """What the renderer draws: the active CISD (and the one before it, faded, if `previous`),
        never one confirmed on a bar before the guard."""
        return [r for r in self.recs[-2 if previous else -1:] if r.bar >= self.s.guard]

    def alertable(self, events) -> list:
        return [e for e in events if e.type == "CISD_CONFIRMED" and e.bar >= self.s.guard]

    def state(self) -> dict:
        def rec(r):
            return {**asdict(r), "side": SIDE[r.side], "before": STATE[r.before], "after": STATE[r.side],
                    "status": r.status}
        return {"state": STATE[self.delivery], "records": [rec(r) for r in self.recs],
                "counters": {"confirmed": self.confirmed, "dropped": self.dropped, "max_scan": self.max_scan}}


# ── Pine's formulation (src/IST.pine, v0.7.0-dev): the same definition, no backward scan ──

class _Stack:
    """One side of the incremental engine, side coordinates. `d` = the suffix minima of the
    delivery lows in the leg window (bar ≥ a): (bar, time, low, origin bar, origin time, L).
    Its bottom is the window's delivery extreme (the latest on a tie) and its series. `w` =
    the suffix minima of every low (bar, low): the leg extreme from any origin ≥ a. Entries
    below the window start are dropped; nothing is ever read from older bars."""
    def __init__(self, s: int):
        self.s = s
        self.armed, self.a, self.since, self.known = True, 0, -1, None
        self.in_run, self.run = False, None                # run = (bar, time, L) of the current series
        self.d: list[tuple] = []
        self.w: list[tuple] = []

    def prune(self, a: int) -> None:
        self.a = a
        while self.d and self.d[0][0] < a:
            self.d.pop(0)
        while self.w and self.w[0][0] < a:
            self.w.pop(0)


class CisdStack:
    """DEF-CISD exactly as CisdEngine, but incremental, as Pine runs it: per bar O(1) amortised
    stack updates, and at a flip only stack prunes (no scan of the leg window, whatever its
    length). Equivalence with CisdEngine: tests/test_cisd_pine.py. `restore` loads the state
    Pine logs at the start of a parity capture (CISDSIDE / CISDREC)."""

    def __init__(self, s: CisdSettings, tick: float, log: EventLog):
        self.s, self.log, self.eps = s, log, tick * 0.01
        self.prev: Candle | None = None
        self.tr: dict[int, float] = {}
        self.sides = {1: _Stack(1), -1: _Stack(-1)}
        self.delivery = UNKNOWN
        self.recs: list[Cisd] = []
        self.confirmed = self.dropped = self.peak = 0

    @property
    def active(self) -> Cisd | None:
        return self.recs[-1] if self.recs and self.recs[-1].end is None else None

    def step(self, t: int, c: Candle) -> None:
        eps = self.eps
        self.tr[t] = true_range(c, self.prev)
        self.prev = c
        view = {s: (c.open, c.low, c.close) if s > 0 else (-c.open, -c.high, -c.close) for s in (1, -1)}
        r = self.active                                   # 1. facts
        if r is not None:
            o, lo, cl = view[r.side]
            lv = r.side * r.level
            if r.retest is None and lo <= lv + eps:
                r.retest = t
            if r.reclaim is None and cl <= lv + eps:
                r.reclaim = t
            if r.broken is None and cl < r.side * r.leg_ext - eps:
                r.broken = t
        for s, sd in self.sides.items():                  # 2. stacks
            o, lo, cl = view[s]
            while sd.w and lo <= sd.w[-1][1] + eps:
                sd.w.pop()
            sd.w.append((t, lo))
            if cl < o - eps:
                if not sd.in_run:
                    sd.in_run, sd.run = True, (t, c.time, o)
                while sd.d and lo <= sd.d[-1][2] + eps:
                    sd.d.pop()
                sd.d.append((t, c.time, lo, *sd.run))
                if len(sd.d) == 1:
                    sd.known = t                          # a new delivery extreme: the reference moved
            else:
                sd.in_run = False
            self.peak = max(self.peak, len(sd.d), len(sd.w))
        if self.delivery != UNKNOWN:                      # 3. the armed side's new extreme: the state side restarts
            arm = self.sides[-self.delivery]
            if arm.d and arm.d[0][0] == t:
                self.sides[self.delivery].prune(t)
        hits = [sd for s, sd in self.sides.items() if sd.armed and sd.d and t > sd.d[0][3] and t > sd.since
                and view[s][2] > sd.d[0][5] + eps]
        assert len(hits) <= 1, "two CISDs on one bar: impossible by DEF-CISD4 (docs/CISD.md)"
        if hits:
            self._confirm(hits[0], t, c)

    def _confirm(self, sd: _Stack, t: int, c: Candle) -> None:
        s = sd.s
        ext_bar, ext_t, ext, origin, origin_t, lv = sd.d[0]
        leg = next(lo for j, lo in sd.w if j >= origin)
        vals = [self.tr.get(j) for j in range(t - self.s.tra_len, t)]     # TR average before the bar = sma(t − 1)
        tra = None if None in vals else sum(vals) / self.s.tra_len
        r = Cisd(origin_t, s, self.delivery, s * lv, origin, ext_bar, s * ext, s * leg, sd.known, t, c.time, c.close,
                 s * (c.close - c.open) / tra if tra else None)
        if self.active is not None:
            self.active.end = t
        self.recs.append(r)
        self.confirmed += 1
        self.delivery = s                                 # 5. flip: prunes only
        op = self.sides[-s]
        op.prune(ext_bar)
        sd.prune(op.d[0][0] if op.d else t)
        op.known = sd.known = t
        sd.armed = False
        op.armed, op.since = True, t
        self.log.emit("CISD_CONFIRMED", s, r.id, origin, r.level, audit(r, ext_t))
        if len(self.recs) > self.s.memory:
            old = self.recs.pop(0)
            self.dropped += 1
            self.log.emit("CISD_DROPPED_MEMORY", old.side, old.id, old.origin, old.level, "ended record")

    def candidate(self, s: int):
        """Per bar, as the capture logs it: 'off' (not armed), None (armed, no reference) or L."""
        sd = self.sides[s]
        return "off" if not sd.armed else s * sd.d[0][5] if sd.d else None

    def snapshot(self) -> dict:
        return {"delivery": self.delivery, "confirmed": self.confirmed, "dropped": self.dropped,
                "sides": {s: {"armed": sd.armed, "a": sd.a, "since": sd.since, "known": sd.known, "in_run": sd.in_run,
                              "run": sd.run, "d": list(sd.d), "w": list(sd.w)} for s, sd in self.sides.items()},
                "recs": [replace(r) for r in self.recs]}

    def restore(self, snap: dict, prev: Candle | None = None) -> None:
        """The state after a bar, with bars renumbered by the caller; `prev` = that bar's candle."""
        self.delivery, self.confirmed, self.dropped = snap["delivery"], snap["confirmed"], snap["dropped"]
        for s, x in snap["sides"].items():
            sd = self.sides[s]
            sd.armed, sd.a, sd.since, sd.known, sd.in_run, sd.run = (x["armed"], x["a"], x["since"], x["known"],
                                                                     x["in_run"], x["run"])
            sd.d, sd.w = list(x["d"]), list(x["w"])
        self.recs = [replace(r) for r in snap["recs"]]
        self.prev = prev
