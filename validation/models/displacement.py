"""Displacement — reference model of docs/DISPLACEMENT.md DEF-DISP1…DISP9 (DISPLACEMENT-R,
recommended by docs/STUDY_DISPLACEMENT.md on 2026-11-01, awaiting the user's approval).

One closed candle that reprices aggressively. Written once for the BULLISH displacement, on side
coordinates; the BEARISH one runs the same code on the mirrored candle (open, close negated;
high ↔ −low), so mirror symmetry holds by construction. Bullish vocabulary (bearish = mirrored):

  bullish candle   close > open + EPS. A doji (|close − open| ≤ EPS) is neither side (DEF-DISP1)
  yardstick A      the TR average of the `tra_len` bars BEFORE the candle, ta.sma(ta.tr(true), 14)[1]:
                   none while warming up, and A = 0 has no scale: no decision (DEF-DISP2)
  body             close − open ≥ k × A                        (DEF-DISP3, k = 1.5)
  strong close     close − low ≥ clv × (high − low)            (DEF-DISP4, clv = 0.75)
  beyond           close > high of the previous candle + EPS   (DEF-DISP5)

Per bar t (Confirmed mode: every bar is closed):
  1. the FVG fact of a displacement on t − 1: is it candle 2 of a raw FVG in its direction
     (low of t > high of t − 2, strict, DEF-A1 geometry)? Stamped once, never changed (DEF-DISP7);
  2. detection on t, at its close (DEF-DISP6); a candle has one direction, so at most one record;
  3. memory: the oldest record goes first (DEF-DISP8).
Detection reads bars only: no CISD, FVG, liquidity, LRL, HTF FVG or session state, no context
(DEF-DISP9). The FVG fact is metadata: no decision reads it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from validation.models.events import EventLog
from validation.models.fvg import raw_gap, sma, true_range
from validation.models.lrl import fx
from validation.models.types import Candle, DispSettings

SIDE = {1: "BULL", -1: "BEAR"}


@dataclass
class Disp:
    """One displacement candle. Prices are real prices."""
    id: int                     # open time of the candle (unique: one record per candle)
    side: int                   # +1 bullish · −1 bearish
    bar: int                    # the candle = its confirmation bar
    time: int
    open: float
    high: float
    low: float
    close: float
    tra: float                  # A: TR average of the bars before the candle
    body_k: float               # side × (close − open) / A
    range_k: float              # (high − low) / A
    clv: float                  # close location, side coordinates: (close − low) / (high − low)
    prev_ext: float             # the previous candle's high (bullish) / low (bearish): the close is beyond it
    fvg: bool | None = None     # candle 2 of a raw FVG in its direction; None until the next bar closes


def audit(r: Disp) -> str:
    """Pine-style reason text (informative, not compared by default)."""
    return (f"body {r.body_k:.2f}×TR · range {r.range_k:.2f}×TR · close {r.clv:.2f} · "
            f"beyond {'H' if r.side > 0 else 'L'}[1] {r.prev_ext:g}")


class DisplacementEngine:
    def __init__(self, s: DispSettings, tick: float, log: EventLog):
        self.s, self.eps, self.log = s, tick * 0.01, log
        self.candles: list[Candle] = []
        self.tr: list[float] = []
        self.recs: list[Disp] = []
        self.confirmed = self.dropped = 0

    def step(self, t: int, c: Candle) -> None:
        eps, cs = self.eps, self.candles
        self.tr.append(true_range(c, cs[-1] if cs else None))
        cs.append(c)
        r = self.recs[-1] if self.recs else None          # 1. FVG fact of yesterday's displacement
        if r is not None and r.bar == t - 1:
            g = raw_gap(cs[t - 2], c)
            r.fvg = g is not None and g[0] == r.side
        tra = sma(self.tr, t - 1, self.s.tra_len)
        if not tra:                                       # warming up, or no scale
            return
        p = cs[t - 1]
        for s in (1, -1):                                 # 2. side coordinates
            o, h, lo, cl = (c.open, c.high, c.low, c.close) if s > 0 else (-c.open, -c.low, -c.high, -c.close)
            pe = p.high if s > 0 else -p.low
            if cl > o + eps and cl - o >= self.s.k * tra and cl - lo >= self.s.clv * (h - lo) and cl > pe + eps:
                self._confirm(s, t, c, tra, (cl - lo) / (h - lo), s * pe)

    def _confirm(self, s: int, t: int, c: Candle, tra: float, clv: float, prev_ext: float) -> None:
        r = Disp(c.time, s, t, c.time, c.open, c.high, c.low, c.close, tra, s * (c.close - c.open) / tra,
                 (c.high - c.low) / tra, clv, prev_ext)
        self.recs.append(r)
        self.confirmed += 1
        self.log.emit("DISPLACEMENT_CONFIRMED", s, r.id, t, r.close, audit(r))
        if len(self.recs) > self.s.memory:               # 3. the oldest goes
            old = self.recs.pop(0)
            self.dropped += 1
            self.log.emit("DISPLACEMENT_DROPPED_MEMORY", old.side, old.id, old.bar, old.close, "oldest record")

    def state(self) -> dict:
        return {"records": [{**asdict(r), "side": SIDE[r.side]} for r in self.recs],
                "counters": {"confirmed": self.confirmed, "dropped": self.dropped}}


# ── Pine's formulation (src/IST.pine, v0.8.0-dev), transliterated: written from the Pine code, not
#    from the engine above, so the tests can prove the two equal ──

@dataclass
class PineDisp:
    """A Pine `Disp` record. fvg: 0 UNKNOWN · 1 YES · −1 NO."""
    side: int
    id: int
    bar: int
    o: float
    h: float
    l: float
    c: float
    tra: float
    body: float
    rng: float
    body_k: float
    range_k: float
    clv: float
    prev_ext: float
    fvg: int = 0


def pine_txt(r: PineDisp) -> str:
    """f_dispTxt: the audit text of DISPLACEMENT_CONFIRMED in Pine Logs."""
    return f"close={fx(r.c)} · bk={fx(r.body_k)} · rk={fx(r.range_k)} · cp={fx(r.clv)} · prev={fx(r.prev_ext)}"


class DispPine:
    """Per bar, as IST.pine runs it: the L1 / L2 values every bar takes (dispTra = ta.sma(ta.tr(true),
    14), A = dispTra[1], high[1], low[1], Phase 1's rawBull / rawBear), then at the close factsDisp,
    f_dispHit (bullish first) and confirmDisp. `side` = dispSide of the last bar; `bar_values(t)` =
    the capture's DA / DK / DP / DF of bar t."""

    def __init__(self, s: DispSettings, tick: float, log: EventLog):
        self.s, self.eps, self.log = s, tick * 0.01, log
        self.candles: list[Candle] = []
        self.tr: list[float] = []
        self.tra: list[float | None] = []                 # dispTra per bar
        self.recs: list[PineDisp] = []
        self.confirmed = self.dropped = 0
        self.side = 0

    def a(self, t: int) -> float | None:                   # dispTraPrv on bar t
        return self.tra[t - 1] if t >= 1 else None

    def step(self, t: int, c: Candle) -> None:
        cs = self.candles
        self.tr.append(true_range(c, cs[-1] if cs else None))
        cs.append(c)
        self.tra.append(sma(self.tr, t, self.s.tra_len))
        a = self.a(t)
        raw_bull = t >= 2 and c.low > cs[t - 2].high       # Phase 1 L2 (DEF-A1): low > c1High
        raw_bear = t >= 2 and c.high < cs[t - 2].low
        if self.recs:                                      # factsDisp
            r = self.recs[-1]
            if r.fvg == 0 and r.bar == t - 1:
                r.fvg = 1 if (raw_bull if r.side > 0 else raw_bear) else -1
        self.side = 0
        if a is not None and a > 0:
            p = cs[t - 1]
            self.side = 1 if self._hit(1, c, a, p.high) else -1 if self._hit(-1, c, a, -p.low) else 0
            if self.side:
                self._confirm(self.side, t, c, a, p.high if self.side > 0 else p.low)

    def _hit(self, s: int, c: Candle, a: float, pe: float) -> bool:      # f_dispHit
        o, cl = s * c.open, s * c.close
        h, lo = (c.high, c.low) if s > 0 else (-c.low, -c.high)
        rg = h - lo
        return cl > o + self.eps and cl - o >= self.s.k * a and rg > 0 and cl - lo >= self.s.clv * rg and cl > pe + self.eps

    def _confirm(self, s: int, t: int, c: Candle, a: float, pe: float) -> None:     # confirmDisp
        rg = c.high - c.low
        bd = s * (c.close - c.open)
        cp = (c.close - c.low if s > 0 else c.high - c.close) / rg
        r = PineDisp(s, c.time, t, c.open, c.high, c.low, c.close, a, bd, rg, bd / a, rg / a, cp, pe)
        self.recs.append(r)
        self.confirmed += 1
        self.log.emit("DISPLACEMENT_CONFIRMED", s, r.id, t, r.c, pine_txt(r))
        if len(self.recs) > self.s.memory:
            old = self.recs.pop(0)
            self.dropped += 1
            self.log.emit("DISPLACEMENT_DROPPED_MEMORY", old.side, old.id, old.bar, old.c, "oldest record")

    def bar_values(self, t: int) -> tuple:
        """The capture's per-bar values of bar t (the last stepped bar): A, body / A and close position in
        the candle's own direction, the FVG metadata resolved on t (1 · −1 · None)."""
        c, a, e = self.candles[t], self.a(t), self.eps
        d = 1 if c.close > c.open + e else -1 if c.close < c.open - e else 0
        bk = d * (c.close - c.open) / a if d and a else None
        cp = ((c.close - c.low) if d > 0 else (c.high - c.close)) / (c.high - c.low) if d else None
        prev = next((r.fvg for r in self.recs[-2:] if r.bar == t - 1), None)
        return a, bk, cp, prev
