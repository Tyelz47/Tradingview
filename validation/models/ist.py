"""The whole reference model: one bar at a time, modules in the Pine engine order
(levels → sessions → FVG → liquidity, src/IST.pine "ENGINE RUN"), then the opt-in LRL
and HTF FVG engines (docs/LRL.md, docs/HTF_FVG.md). Confirmed mode: every candle is a closed bar."""
from __future__ import annotations

from validation.models.events import Event, EventLog, canonical
from validation.models.fvg import FvgEngine
from validation.models.htf_fvg import HtfEngine
from validation.models.levels import LevelEngine
from validation.models.liquidity import LiquidityEngine
from validation.models.lrl import LrlEngine
from validation.models.sessions import SessionEngine
from validation.models.types import Candle, Settings


class IstModel:
    def __init__(self, settings: Settings | None = None, htf=None, incremental_liq: bool = False, htf_pre=None,
                 htf_external=None):
        self.settings = s = settings or Settings()
        self.log = EventLog()
        self.candles: list[Candle] = []
        self.levels = LevelEngine(s.levels, s.tick, self.log, htf) if "levels" in s.modules else None
        self.sessions = SessionEngine(s.sessions, self.log) if "sessions" in s.modules else None
        self.fvg = FvgEngine(s.fvg, s.tick, self.log) if "fvg" in s.modules else None
        self.liq = LiquidityEngine(s.liq, s.tick, self.log, incremental=incremental_liq) if "liq" in s.modules else None
        self.lrl = LrlEngine(s.lrl, s.liq.tol_ticks, s.tick, self.log) if "lrl" in s.modules else None
        self.hfvg = HtfEngine(s.htf, s.fvg, s.tick, self.log, htf_pre, htf_external) if "htf" in s.modules else None

    @property
    def bar(self) -> int:
        return len(self.candles) - 1

    @property
    def events(self) -> list[Event]:
        return self.log.events

    def step(self, c: Candle) -> list[Event]:
        bar = len(self.candles)
        self.candles.append(c)
        self.log.at(bar, c.time)
        n = len(self.log.events)
        for engine in (self.levels, self.sessions, self.fvg, self.liq, self.lrl, self.hfvg):
            if engine is not None:
                engine.step(bar, c)
        return self.log.events[n:]

    def run(self, candles) -> "IstModel":
        for c in candles:
            self.step(c)
        return self

    def canonical_events(self) -> list[Event]:
        return canonical(self.log.events)

    def state(self) -> dict:
        """Final structural state, canonical and JSON-ready (used by golden and regression)."""
        out = {}
        if self.fvg is not None:
            out["fvg"] = self.fvg.state()
        if self.liq is not None:
            out.update(self.liq.state())
        if self.sessions is not None:
            out["sessions"] = self.sessions.state()
        if self.levels is not None:
            out["ref_levels"] = self.levels.state()
        if self.lrl is not None:
            out["lrl"] = self.lrl.state()
        if self.hfvg is not None:
            out["htf"] = self.hfvg.state()
        return out


def run_model(candles, settings: Settings | None = None, **kw) -> IstModel:
    return IstModel(settings, **kw).run(candles)
