"""Phase 2 liquidity — reference model of LIQUIDITY.md DEF-L1…L6.

Per bar (Confirmed mode, every bar is closed):
  1. both sides advance: level takes, exact touches, closing, then cluster takes;
  2. the swing bar X = t − right is judged (DEF-L1) and, if significant (DEF-L2),
     becomes a level, is clustered (DEF-L5) and the memory policy runs (DEF-L6).
So a level or cluster is never taken by the bar that created it.

`incremental=True` adds Pine's trigger-price gate (an optimisation that skips the
scan on quiet bars). The oracle default is the plain full scan; tests prove both
give identical results.
"""
from __future__ import annotations

from dataclasses import dataclass

from validation.models import eq as eqm
from validation.models.eq import BREAK, SWEEP, EqCluster
from validation.models.events import EventLog
from validation.models.fvg import sma, true_range
from validation.models.types import Candle, LiqSettings


@dataclass
class Level:
    id: int                 # swing bar time
    is_bsl: bool
    price: float
    origin_bar: int         # swing bar X
    origin_time: int
    confirm_bar: int        # X + right
    confirm_time: int
    piv_l: int
    piv_r: int
    react: float
    react_req: float
    tra: float
    touches: int = 0
    taken_bar: int | None = None
    taken_time: int | None = None
    take_ext: float | None = None
    take_close: float | None = None
    take_gap: bool = False
    cls: int = 0
    far: float | None = None
    eq_open: bool = True
    eq: EqCluster | None = None

    @property
    def sign(self) -> int:
        return 1 if self.is_bsl else -1

    def state(self) -> dict:
        return {"id": self.id, "side": "BSL" if self.is_bsl else "SSL", "price": self.price,
                "origin_bar": self.origin_bar, "confirm_bar": self.confirm_bar, "touches": self.touches,
                "taken_bar": self.taken_bar, "take_ext": self.take_ext, "cls": eqm.CLS_NAME[self.cls],
                "gap": self.take_gap, "eq": None if self.eq is None else self.eq.id,
                "status": "ACTIVE" if self.taken_bar is None else "TAKEN"}


class Side:
    def __init__(self, is_bsl: bool):
        self.is_bsl = is_bsl
        self.sign = 1 if is_bsl else -1
        self.live: list[Level] = []       # can still change (active, or taken but EQ-eligible)
        self.hist: list[Level] = []       # closed
        self.eqs: list[EqCluster] = []
        self.trig: float | None = None
        self.pivots = self.rejects = self.levels = 0
        # REJECT by reason, disjoint (C1): reaction only · dominance only · both. rejects = their sum.
        self.rej_react = self.rej_dom = self.rej_both = 0
        self.drop_live = self.drop_hist = self.drop_eq = 0

    @property
    def name(self) -> str:
        return "BSL" if self.is_bsl else "SSL"

    @property
    def eq_name(self) -> str:
        return "EQH" if self.is_bsl else "EQL"

    def all_levels(self) -> list[Level]:
        return self.hist + self.live


class LiquidityEngine:
    def __init__(self, s: LiqSettings, tick: float, log: EventLog, incremental: bool = False):
        self.s, self.tick, self.eps, self.log = s, tick, tick * 0.01, log
        self.tol = s.tol_ticks * tick
        self.incremental = incremental
        self.candles: list[Candle] = []
        self.tr: list[float] = []
        self.H: list[float] = []
        self.Lo: list[float] = []
        self.bsl, self.ssl = Side(True), Side(False)

    def sides(self):
        return (self.bsl, self.ssl)

    def pen(self, side: Side, p: float, c: Candle) -> float:
        """How far the bar traded beyond p on the side's side (> 0 beyond, 0 exactly at)."""
        return c.high - p if side.is_bsl else p - c.low

    # ── per bar ──
    def step(self, bar: int, c: Candle) -> None:
        prev = self.candles[-1] if self.candles else None
        self.candles.append(c)
        self.tr.append(true_range(c, prev))
        self.H.append(c.high)
        self.Lo.append(c.low)
        for side in self.sides():
            self._advance(side, bar, c)
        self._judge(bar)

    def _advance(self, side: Side, bar: int, c: Candle) -> None:
        if self.incremental and (side.trig is None or self.pen(side, side.trig, c) < 0):
            return
        for i in range(len(side.live) - 1, -1, -1):
            x = side.live[i]
            if bar <= x.confirm_bar:
                continue
            p = self.pen(side, x.price, c)
            if x.taken_bar is None:
                if p > 0:
                    self._take(side, x, bar, c)
                elif p == 0:
                    x.touches += 1                     # exact touch: not a take, no event
            elif self.pen(side, x.far, c) > 0:
                x.far = c.high if side.is_bsl else c.low
            if x.taken_bar is not None and p > self.tol + self.eps:
                x.eq_open = False                      # beyond price ± tol: never EQ-eligible again
                side.hist.append(side.live.pop(i))
        for cl in side.eqs:
            if cl.active and self.pen(side, cl.bound, c) > 0:
                self._take_cluster(side, cl, bar, c)
        side.trig = self._trigger(side)

    def _take(self, side: Side, x: Level, bar: int, c: Candle) -> None:
        """DEF-L4: the fact (strictly beyond), then the class at this bar's close."""
        x.taken_bar, x.taken_time = bar, c.time
        x.take_ext = c.high if side.is_bsl else c.low
        x.far = x.take_ext
        x.take_gap = c.open > x.price if side.is_bsl else c.open < x.price
        ticks = round(self.pen(side, x.price, c) / self.tick)
        self.log.emit(f"{side.name}_TAKEN", side.sign, x.id, x.origin_bar, x.price,
                      f"+{ticks} ticks" + (" · opened beyond" if x.take_gap else ""))
        x.take_close = c.close
        x.cls = BREAK if (c.close > x.price if side.is_bsl else c.close < x.price) else SWEEP
        self.log.emit(f"{side.name}_{'BREAK' if x.cls == BREAK else 'SWEEP'}", side.sign, x.id, x.origin_bar,
                      x.price, f"close {c.close}")

    def _take_cluster(self, side: Side, cl: EqCluster, bar: int, c: Candle) -> None:
        cl.taken_bar, cl.taken_time = bar, c.time
        cl.cls = BREAK if (c.close > cl.bound if side.is_bsl else c.close < cl.bound) else SWEEP
        if cl.qual_bar is not None:                    # a group below the minimum ends silently
            self.log.emit(f"{side.eq_name}_TAKEN", side.sign, cl.id, cl.origin_bar, cl.bound,
                          f"{len(cl.members)} swings · {'break' if cl.cls == BREAK else 'sweep'}")

    def _trigger(self, side: Side) -> float | None:
        v = [x.price if x.taken_bar is None else x.far for x in side.live]
        v += [cl.bound for cl in side.eqs if cl.active]
        if not v:
            return None
        return min(v) if side.is_bsl else max(v)

    # ── DEF-L1 / DEF-L2: judge the swing bar X = t − right ──
    def _judge(self, t: int) -> None:
        L, R = self.s.left, self.s.right
        X = t - R
        if X - L < 0:
            return
        H, Lo = self.H, self.Lo
        tra = sma(self.tr, X, self.s.tra_len)
        req = None if tra is None else self.s.k * tra
        hi_r, lo_r = max(H[X + 1:t + 1]), min(Lo[X + 1:t + 1])
        x_time = self.candles[X].time
        if H[X] > max(H[X - L:X]) and H[X] >= hi_r:          # strict left, ≥ right
            self._judged(self.bsl, H[X], X, x_time, H[X] - lo_r, req, tra, t)
        if Lo[X] < min(Lo[X - L:X]) and Lo[X] <= lo_r:
            self._judged(self.ssl, Lo[X], X, x_time, hi_r - Lo[X], req, tra, t)

    def dominance_ref(self, side: Side, X: int) -> float | None:
        """DEF-L2 (C1): the extreme of the W bars BEFORE the swing bar X (X−W … X−1; the
        right bars are not part of it). None when dominance is off (W = 0) or fewer
        than W earlier bars exist (warm-up)."""
        w = self.s.dom
        if not w or X < w:
            return None
        return max(self.H[X - w:X]) if side.is_bsl else min(self.Lo[X - w:X])

    def dominant(self, side: Side, px: float, ref: float) -> bool:
        """Only an earlier extreme STRICTLY beyond the swing price + EQ tolerance rejects
        (the same tolerance and float margin as EQ clustering)."""
        return ref <= px + self.tol + self.eps if side.is_bsl else ref >= px - self.tol - self.eps

    def _judged(self, side: Side, px, X, x_time, react, req, tra, t) -> None:
        side.pivots += 1
        ref = self.dominance_ref(side, X)
        if req is None or (self.s.dom and ref is None):
            return                                         # warm-up: neither PASS nor REJECT
        react_ok = react >= req
        dom_ok = not self.s.dom or self.dominant(side, px, ref)
        if react_ok and dom_ok:
            self._register(side, px, X, x_time, react, req, tra, t)
            return
        side.rejects += 1
        if not react_ok and not dom_ok:
            side.rej_both += 1
        elif not react_ok:
            side.rej_react += 1
        else:
            side.rej_dom += 1

    def _register(self, side: Side, px, X, x_time, react, req, tra, t) -> None:
        now = self.candles[t]
        x = Level(id=x_time, is_bsl=side.is_bsl, price=px, origin_bar=X, origin_time=x_time, confirm_bar=t,
                  confirm_time=now.time, piv_l=self.s.left, piv_r=self.s.right, react=react, react_req=req, tra=tra)
        self.log.emit(f"{side.name}_CREATED", side.sign, x.id, X, px,
                      f"reaction {react / tra:.2f}xTR >= {self.s.k}" if tra else "")
        self._cluster(side, x, t, now.time)
        side.live.append(x)
        side.levels += 1
        side.trig = px if side.trig is None else (min(side.trig, px) if side.is_bsl else max(side.trig, px))
        if len(side.live) + len(side.hist) > self.s.memory:
            if side.hist:
                old = side.hist.pop(0)
                side.drop_hist += 1
                why = "closed record"
            else:
                old = side.live.pop(0)
                side.drop_live += 1
                side.trig = self._trigger(side)
                why = "live record · tracking stopped"
            self.log.emit(f"{side.name}_DROPPED_MEMORY", side.sign, old.id, old.origin_bar, old.price, why)

    def _cluster(self, side: Side, x: Level, t: int, time: int) -> None:
        hit = eqm.nearest_active(side.eqs, x.price, self.tol, self.eps)
        if hit is None:
            seed = eqm.nearest_seed(side.live, x, self.tol, self.eps, side.is_bsl)
            if seed is not None:
                hit = eqm.form(seed, x, t, time, side.is_bsl)
                seed.eq = hit
                side.eqs.append(hit)
                if len(side.eqs) > self.s.eq_memory:
                    self._drop_cluster(side)
        if hit is not None:
            x.eq = hit
            if eqm.join(hit, x, t, time, self.s.min_touch):
                self.log.emit(f"{side.eq_name}_CREATED", side.sign, hit.id, hit.origin_bar, hit.bound,
                              f"{len(hit.members)} swings within {self.s.tol_ticks} ticks")

    def _drop_cluster(self, side: Side) -> None:
        old = side.eqs.pop(eqm.drop_victim(side.eqs))
        if old.active:                                   # release members of an active cluster
            for m in side.live:
                if m.eq is old:
                    m.eq = None
        side.drop_eq += 1
        self.log.emit(f"{side.eq_name}_DROPPED_MEMORY", side.sign, old.id, old.origin_bar, old.bound,
                      "active cluster · tracking stopped" if old.active else "taken cluster")

    def state(self) -> dict:
        levels = [x.state() for side in self.sides() for x in sorted(side.all_levels(), key=lambda x: x.id)]
        clusters = [c.state() for side in self.sides() for c in side.eqs]
        counters = {side.name: {"pivots": side.pivots, "pass": side.levels, "reject": side.rejects,
                                "reject_reaction": side.rej_react, "reject_dominance": side.rej_dom,
                                "reject_both": side.rej_both,
                                "drop_live": side.drop_live, "drop_hist": side.drop_hist, "drop_eq": side.drop_eq}
                    for side in self.sides()}
        return {"levels": levels, "clusters": clusters, "counters": counters}
