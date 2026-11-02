"""IFVG — reference model of docs/IFVG.md DEF-IFVG1…IFVG9 (IFVG-R, recommended by
docs/STUDY_IFVG.md on 2026-11-02, awaiting the user's approval).

An inversion fair value gap is a frozen Phase 1 FVG whose far edge was closed through: the same
zone, now acting from the opposite side. The module OBSERVES the Phase 1 FVG engine and never
writes to it: the parent stays historically INVALIDATED in Phase 1 (DEF-A5), and the IFVG is a
separate record that copies the parent's identity and geometry.

  eligible parent   a Phase 1 FVG (DEF-A1 / A2, the frozen detector and its inputs) that the FVG
                    engine still tracks (open) when it is invalidated (DEF-IFVG1)
  inversion         the parent's DEF-A5 invalidation, unchanged: bullish parent close < bottom,
                    bearish parent close > top, strict, from its confirmation + 1, at the bar's
                    close (DEF-IFVG2). A wick, or a close exactly at the edge, never inverts
  side              the opposite of the parent's (DEF-IFVG3)
  geometry          the parent's top, bottom and CE, exactly (DEF-IFVG4)
  identity          the parent's id (candle-3 time) and the IFVG side (DEF-IFVG5)
  facts             from the bar after the inversion, each stamped once (wick reach, as DEF-A4):
                    retest = the near edge (the inversion boundary), CE, full = the far edge
                    (bearish IFVG: high ≥ bottom / mid / top; bullish mirrored) (DEF-IFVG6)
  terminal          the first close strictly beyond the far edge (bearish IFVG: close > top), the
                    mirror of DEF-A5: ACTIVE → INVALIDATED; no second inversion (DEF-IFVG7)
  memory            per side; the oldest ended record first, else the oldest active (DEF-IFVG8)

Per bar t: 1. active IFVGs advance (touch → CE → full → invalidation, DEF-A7 order); 2. the Phase 1
FVGs created on t join the registry, and those the FVG engine invalidated on t become IFVGs;
3. memory. Detection reads bars and the Phase 1 FVG records only (DEF-IFVG9): no CISD,
displacement, liquidity, LRL or HTF state; no display input.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from validation.models.events import EventLog
from validation.models.fvg import Fvg, FvgEngine
from validation.models.types import Candle, IfvgSettings

SIDE = {1: "BULL", -1: "BEAR"}


@dataclass
class Ifvg:
    """One inversion FVG. Prices are real prices; bars are chart bar indices."""
    id: int                     # the parent FVG's id (its candle-3 open time)
    side: int                   # +1 bullish IFVG (from a bearish FVG) · −1 bearish IFVG (from a bullish FVG)
    origin_bar: int             # the parent's candle 1
    parent_bar: int             # the parent's confirmation (candle 3)
    top: float                  # the parent's geometry, unchanged
    bottom: float
    mid: float
    bar: int                    # the inversion bar = the parent's DEF-A5 invalidation bar
    time: int
    close: float                # the inverting close
    pre: str                    # the parent before the inversion bar: UNTOUCHED · TOUCHED · CE · FULL (metadata)
    retest: int | None = None   # facts, from the bar after the inversion, each stamped once
    ce: int | None = None
    full: int | None = None
    end: int | None = None      # INVALIDATED: the first close strictly beyond the far edge

    @property
    def near(self) -> float:    # the inversion boundary (the parent's far edge)
        return self.bottom if self.side < 0 else self.top

    @property
    def far(self) -> float:
        return self.top if self.side < 0 else self.bottom

    @property
    def status(self) -> str:
        return "ACTIVE" if self.end is None else "INVALIDATED"


def pre_state(z: Fvg, bar: int) -> str:
    """The parent's milestones before the inversion bar (strictly earlier bars)."""
    done = lambda b: b is not None and b < bar
    return "FULL" if done(z.full_bar) else "CE" if done(z.ce_bar) else "TOUCHED" if done(z.touch_bar) else "UNTOUCHED"


class IfvgEngine:
    def __init__(self, s: IfvgSettings, tick: float, log: EventLog, fvg: FvgEngine):
        self.s, self.log, self.fvg = s, log, fvg
        self.parents: dict[int, Fvg] = {}             # the Phase 1 FVGs that may still invert (read only)
        self.bull: list[Ifvg] = []                    # oldest first
        self.bear: list[Ifvg] = []
        self.inverted = self.dropped = 0

    def records(self) -> list[Ifvg]:
        return self.bull + self.bear

    def step(self, t: int, c: Candle) -> None:
        for r in self.records():                      # 1. advance, from the bar after the inversion
            if r.end is None and t > r.bar:
                self._advance(r, t, c)
        for z in self.fvg.records():                  # 2. the FVGs created on this bar join the registry
            if z.confirm_bar == t:
                self.parents[z.id] = z
        tracked = {z.id for z in self.fvg.records() if z.is_open}
        for k, z in list(self.parents.items()):
            if z.inv_bar == t:                        # invalidated on this bar (DEF-A5): it inverts
                del self.parents[k]
                self._invert(z, t, c)
            elif z.inv_bar is not None or k not in tracked:
                del self.parents[k]                   # dropped by the FVG memory while open: never inverts

    def _invert(self, z: Fvg, t: int, c: Candle) -> None:
        r = Ifvg(z.id, -z.dir, z.origin_bar, z.confirm_bar, z.top, z.bottom, z.mid, t, c.time, c.close, pre_state(z, t))
        recs = self.bull if r.side > 0 else self.bear
        recs.append(r)
        self.inverted += 1
        self.log.emit("IFVG_INVERTED", r.side, r.id, r.origin_bar, r.close, f"{r.bottom}-{r.top} · from {r.pre}")
        if len(recs) > self.s.memory:                 # 3. the oldest ended record first, else the oldest active
            i = next((i for i, x in enumerate(recs[:-1]) if x.end is not None), 0)
            old = recs.pop(i)
            self.dropped += 1
            self.log.emit("IFVG_DROPPED_MEMORY", old.side, old.id, old.origin_bar, old.mid,
                          "active record" if old.end is None else "invalidated record")

    def _advance(self, r: Ifvg, t: int, c: Candle) -> None:
        """DEF-IFVG6 / IFVG7, the DEF-A4 / A7 mirror: touch → CE → full → invalidation on one bar."""
        reach = (lambda lv: c.high >= lv) if r.side < 0 else (lambda lv: c.low <= lv)
        if r.retest is None and reach(r.near):
            r.retest = t
            self.log.emit("IFVG_FIRST_TOUCH", r.side, r.id, r.origin_bar, r.near, "retest of the inversion edge")
        if r.ce is None and reach(r.mid):
            r.ce = t
        if r.full is None and reach(r.far):
            r.full = t
        if (c.close > r.far) if r.side < 0 else (c.close < r.far):
            r.end = t
            self.log.emit("IFVG_INVALIDATED", r.side, r.id, r.origin_bar, c.close,
                          "close>top" if r.side < 0 else "close<bottom")

    def state(self) -> list[dict]:
        return [{**asdict(r), "side": SIDE[r.side], "status": r.status} for r in sorted(self.records(), key=lambda r: (r.side, r.id))]
