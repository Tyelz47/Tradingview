"""LRL — reference model of docs/LRL.md DEF-LRL1…LRL8 (approved 2026-10-28).

A diagonal liquidity line through three or more successive failure swings. Written once
for the HIGH side (bearish LRL: descending swing highs, buy stops above; event dir +1).
The LOW side (bullish LRL: ascending swing lows; dir −1) runs the same code on the
mirrored series (high ↔ −low, close ↔ −close): "side coordinates" below.

Per bar t (Confirmed mode: every bar is closed), per side:
  1. advance, with the geometry in effect BEFORE t, every LRL confirmed before t: a high
     strictly beyond line + τ takes it (SWEEP / BREAK at this close), else it expires once
     no further point can arrive, else a high within τ of the line is a touch; 2-point
     candidates that are crossed, expired or hold a spent pivot are dropped silently;
  2. judge the swing bar X = t − right (DEF-LRL1). A new pivot extends one LRL, else
     confirms one candidate (its 3rd point), else seeds new candidates.
So an LRL is never taken by the bar that confirmed it, and a new geometry applies from the
next bar on. Detection reads bars only: no Phase 1 / 2 state (DEF-LRL8), no context
(DEF-LRL9).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from validation.models.events import EventLog
from validation.models.fvg import sma, true_range
from validation.models.types import Candle, LrlSettings

SWEEP, BREAK, EXPIRED = "SWEEP", "BREAK", "EXPIRED"


@dataclass
class Lrl:
    """One LRL record, or a 2-point candidate (born = −1). Prices in side coordinates."""
    id: int                     # time of the first point's swing bar X₁ (unique per side)
    xs: list                    # swing bars of the points (append-only)
    ps: list                    # their prices
    tau: float                  # DEF-LRL2, frozen when the candidate formed
    born: int = -1              # confirmation bar (3rd point known)
    ext: list = field(default_factory=list)   # bars where the 4th, 5th, … point joined
    touches: int = 0
    end: str | None = None      # SWEEP · BREAK · EXPIRED
    end_bar: int | None = None
    end_level: float | None = None    # line + τ on the end bar
    end_close: float | None = None

    @property
    def slope(self) -> float:   # DEF-LRL4: chord through the first and the latest point
        return (self.ps[-1] - self.ps[0]) / (self.xs[-1] - self.xs[0])

    def y(self, x: float) -> float:
        return self.ps[0] + self.slope * (x - self.xs[0])

    @property
    def last_decision(self) -> int:
        return self.ext[-1] if self.ext else self.born


class Side:
    def __init__(self, sign: int):
        self.sign = sign                    # +1 high side (bearish LRL) · −1 low side (bullish LRL)
        self.hi: list[float] = []           # side coordinates
        self.lo: list[float] = []
        self.cl: list[float] = []
        self.live: list[Lrl] = []           # confirmed, active
        self.hist: list[Lrl] = []           # confirmed, ended (in end order)
        self.cands: list[Lrl] = []
        self.piv: list[tuple] = []          # recent pivots (X, P), X within `gap` of the newest
        self.members: set = set()           # points of active LRLs
        self.spent: set = set()             # points of taken LRLs: never used again
        self.pivots = self.seeded = self.confirmed = self.extended = 0
        self.taken = self.expired = self.dropped = 0
        self.last_drop: dict | None = None  # {"active": bool, "ended_available": bool}

    @property
    def name(self) -> str:
        return "HIGH" if self.sign > 0 else "LOW"

    def records(self) -> list[Lrl]:
        return self.hist + self.live


class LrlEngine:
    def __init__(self, s: LrlSettings, eq_tol_ticks: int, tick: float, log: EventLog):
        self.s, self.log, self.eps = s, log, tick * 0.01
        self.tol = eq_tol_ticks * tick                    # DEF-L5 EQ tolerance (shared input)
        self.candles: list[Candle] = []
        self.tr: list[float] = []
        self.high, self.low = Side(1), Side(-1)

    def sides(self):
        return (self.high, self.low)

    def tra(self, x: int) -> float | None:
        return sma(self.tr, x, self.s.tra_len)

    def tau(self, x: int) -> float | None:
        """DEF-LRL2 at anchor bar x; None while the TR average warms up (no candidate)."""
        tra = self.tra(x)
        return None if tra is None else max(self.tol, self.s.tol_k * tra)

    # ── per bar ──
    def step(self, bar: int, c: Candle) -> None:
        self.tr.append(true_range(c, self.candles[-1] if self.candles else None))
        self.candles.append(c)
        for side in self.sides():
            g = side.sign
            side.hi.append(c.high if g > 0 else -c.low)
            side.lo.append(c.low if g > 0 else -c.high)
            side.cl.append(g * c.close)
        for side in self.sides():
            self._advance(side, bar)
        for side in self.sides():
            self._judge(side, bar)

    def _advance(self, side: Side, t: int) -> None:
        s, eps, hi = self.s, self.eps, side.hi
        for r in list(side.live):
            if r.born >= t:
                continue
            lv = r.y(t) + r.tau
            if hi[t] > lv + eps:
                self._end(side, r, t, BREAK if side.cl[t] > lv + eps else SWEEP, lv)
            elif t > r.xs[-1] + s.gap + s.right:
                self._end(side, r, t, EXPIRED, lv)
            elif hi[t] >= r.y(t) - r.tau - eps:
                r.touches += 1
        side.cands = [k for k in side.cands if not (side.spent & set(k.xs) or hi[t] > k.y(t) + k.tau + eps
                                                    or t > k.xs[-1] + s.gap + s.right)]

    def _end(self, side: Side, r: Lrl, t: int, kind: str, level: float) -> None:
        r.end, r.end_bar, r.end_level, r.end_close = kind, t, level, side.cl[t]
        side.live.remove(r)
        side.hist.append(r)
        side.members.difference_update(r.xs)
        if kind == EXPIRED:
            side.expired += 1
        else:
            side.taken += 1
            side.spent.update(r.xs)
        self.log.emit(f"LRL_{kind}", side.sign, r.id, r.xs[0], side.sign * level,
                      f"{len(r.xs)} points · close {self.candles[t].close}")

    def fits(self, side: Side, xs: list, ps: list, tau: float, t: int) -> bool:
        """DEF-LRL3 (last pair) and DEF-LRL4 (whole list) at bar t."""
        s, eps = self.s, self.eps
        xa, pa, xb, pb = xs[-2], ps[-2], xs[-1], ps[-1]
        if xb - xa > s.gap or not pb < pa - self.tol - eps:
            return False
        if s.sep_k:
            tra = self.tra(xa)
            if tra is None or pb - min(side.lo[xa + 1:xb]) < s.sep_k * tra - eps:
                return False
        if len(xs) > 2 and not ps[0] - ps[-1] > s.drop_k * tau + eps:
            return False
        line = Lrl(0, xs, ps, tau)
        if any(abs(p - line.y(x)) > tau + eps for x, p in zip(xs, ps)):
            return False
        return all(side.hi[j] <= line.y(j) + tau + eps for j in range(xs[0] + 1, t + 1))

    def _judge(self, side: Side, t: int) -> None:
        s, hi = self.s, side.hi
        X = t - s.right
        if X - s.left < 0 or not (hi[X] > max(hi[X - s.left:X]) and hi[X] >= max(hi[X + 1:t + 1])):
            return
        side.pivots += 1
        P = hi[X]
        if not self._extend(side, X, P, t) and not self._confirm(side, X, P, t):
            self._seed(side, X, P, t)
        side.piv = [p for p in side.piv if X - p[0] <= s.gap] + [(X, P)]

    def _extend(self, side: Side, X: int, P: float, t: int) -> bool:
        for r in sorted(side.live, key=lambda r: r.xs[0]):
            if self.fits(side, r.xs + [X], r.ps + [P], r.tau, t):
                r.xs.append(X)
                r.ps.append(P)
                r.ext.append(t)
                side.members.add(X)
                side.extended += 1
                self.log.emit("LRL_EXTENDED", side.sign, r.id, r.xs[0], side.sign * P,
                              f"{len(r.xs)} points · tau {r.tau:.4f} · slope {side.sign * r.slope:.4f}/bar")
                return True
        return False

    def _confirm(self, side: Side, X: int, P: float, t: int) -> bool:
        for k in sorted(side.cands, key=lambda k: (k.xs[0], k.xs[1])):
            if self.fits(side, k.xs + [X], k.ps + [P], k.tau, t):
                r = Lrl(k.id, k.xs + [X], k.ps + [P], k.tau, born=t)
                side.live.append(r)
                side.members.update(r.xs)
                side.cands = [d for d in side.cands if not set(d.xs) & set(r.xs)]
                side.confirmed += 1
                self.log.emit("LRL_CONFIRMED", side.sign, r.id, r.xs[0], side.sign * P,
                              f"3 points · tau {r.tau:.4f} · slope {side.sign * r.slope:.4f}/bar")
                self._memory(side)
                return True
        return False

    def _seed(self, side: Side, X: int, P: float, t: int) -> None:
        for xa, pa in side.piv:
            if xa in side.members or xa in side.spent or X - xa > self.s.gap:
                continue
            tau = self.tau(xa)
            if tau is not None and self.fits(side, [xa, X], [pa, P], tau, t):
                side.cands.append(Lrl(self.candles[xa].time, [xa, X], [pa, P], tau))
                side.seeded += 1
        side.cands = side.cands[-self.s.cand_memory:]

    def _memory(self, side: Side) -> None:
        """DEF-LRL6: records per side ≤ memory; the record that ended first goes first,
        else the oldest active one, whose points become spent (so its id never returns)."""
        if len(side.live) + len(side.hist) <= self.s.memory:
            return
        side.last_drop = {"active": not side.hist, "ended_available": bool(side.hist)}
        old = side.hist.pop(0) if side.hist else side.live.pop(0)
        if old.end is None:
            side.members.difference_update(old.xs)
            side.spent.update(old.xs)
        side.dropped += 1
        self.log.emit("LRL_DROPPED_MEMORY", side.sign, old.id, old.xs[0], side.sign * old.ps[-1],
                      "active record · tracking stopped" if old.end is None else "ended record")

    def state(self) -> dict:
        def rec(side, r):
            g = side.sign
            return {"id": r.id, "side": side.name, "points": [[x, g * p] for x, p in zip(r.xs, r.ps)],
                    "tau": r.tau, "born": r.born, "ext": list(r.ext), "touches": r.touches,
                    "status": r.end or "ACTIVE", "end_bar": r.end_bar,
                    "end_level": None if r.end_level is None else g * r.end_level}
        return {"records": [rec(side, r) for side in self.sides() for r in sorted(side.records(), key=lambda r: r.id)],
                "counters": {side.name: {"pivots": side.pivots, "candidates": side.seeded, "confirmed": side.confirmed,
                                         "extended": side.extended, "taken": side.taken, "expired": side.expired,
                                         "dropped": side.dropped} for side in self.sides()}}
