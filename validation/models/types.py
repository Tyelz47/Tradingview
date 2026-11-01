"""Candles and settings shared by every reference model.

Settings mirror the Pine inputs that change calculation ([calc]). View inputs are
collected in ViewSettings, which the logic never reads (ARCHITECTURE §2): tests
use it to prove that visibility cannot change logical state.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, replace

NQ_TICK = 0.25

# Pine `LiqPreset` → (left, right, k, W), LIQUIDITY.md DEF-L3. W = dominance window (C1,
# v0.4.4-dev). The Custom preset has no W input: its dominance is off (W = 0).
PRESETS = {
    "aggressive": (3, 2, 0.5, 10),
    "balanced": (5, 3, 1.0, 30),
    "strict": (10, 5, 2.0, 60),
}

# Pine `MitRule` values (DEF-A5): which milestone counts as "mitigated" for display.
MIT_RULES = ("firstTouch", "midpoint", "fullFill", "closeThrough")


@dataclass(frozen=True)
class Candle:
    """One closed bar. `time` is the bar's open time in ms since the epoch (Pine `time`)."""
    time: int
    open: float
    high: float
    low: float
    close: float

    def problems(self) -> list[str]:
        out = []
        if self.high < max(self.open, self.close):
            out.append("high < max(open, close)")
        if self.low > min(self.open, self.close):
            out.append("low > min(open, close)")
        if self.high < self.low:
            out.append("high < low")
        return out


def validate_candles(candles: list[Candle], tick: float | None = None) -> None:
    """Raise ValueError naming the first malformed candle (OHLC rules, time order, tick grid)."""
    prev_t = None
    for i, c in enumerate(candles):
        bad = c.problems()
        if prev_t is not None and c.time <= prev_t:
            bad.append("time does not increase")
        if tick:
            for name in ("open", "high", "low", "close"):
                v = getattr(c, name) / tick
                if abs(v - round(v)) > 1e-6:
                    bad.append(f"{name} {getattr(c, name)} is off the {tick} tick grid")
        if bad:
            raise ValueError(f"candle {i} {c}: " + "; ".join(bad))
        prev_t = c.time


@dataclass(frozen=True)
class FvgSettings:
    """DEF-A2 / ARCHITECTURE §6 qualification and §3.3 memory ([calc])."""
    min_ticks: int = 2          # fvgMinTicks
    k_tra: float = 0.10         # fvgMinTra  (× TR average; 0 = off)
    k_rng: float = 0.0          # fvgMinRng  (× average range; 0 = off)
    length: int = 14            # fvgLen
    memory: int = 50            # fvgMemory, records per direction

    @property
    def lookback(self) -> int:
        """Bars before candle 3 its decision depends on: the t−2 references average
        `length` true ranges, and the first of them needs the close before it."""
        return self.length + 2


@dataclass(frozen=True)
class LiqSettings:
    """LIQUIDITY.md DEF-L1…L6 ([calc]). Defaults = Balanced preset."""
    left: int = 5
    right: int = 3
    k: float = 1.0
    dom: int = 30               # DEF-L2 dominance window W (bars before the swing bar); 0 = off (Custom)
    tol_ticks: int = 4          # eqTolTk
    min_touch: int = 2          # eqMinTch
    memory: int = 100           # liqMemory, records per side
    eq_memory: int = 25         # Pine constant EQ_MEM; variable here only to exercise the drop path
    tra_len: int = 14           # Pine constant LIQ_TRA_LEN

    @classmethod
    def preset(cls, name: str, **kw) -> "LiqSettings":
        left, right, k, w = PRESETS[name]
        return cls(left=left, right=right, k=k, dom=w, **kw)

    @property
    def lookback(self) -> int:
        """Bars before the swing bar X its decision depends on (the dependency graph of
        DEF-L1/L2): the TR average at X averages `tra_len` true ranges, the first needing
        the close before it; the pivot reads `left` bars; dominance reads `dom` bars."""
        return max(self.tra_len, self.left, self.dom)


@dataclass(frozen=True)
class LrlSettings:
    """docs/LRL.md DEF-LRL1…LRL6 ([calc]), approved 2026-10-28. Constants of the definition,
    not user inputs; variable here only so tests can exercise every rule. The EQ tolerance
    is the shared liquidity input (LiqSettings.tol_ticks)."""
    left: int = 3               # DEF-LRL1 intermediate pivot engine (DEF-L1 rule, no significance test)
    right: int = 2
    tol_k: float = 0.5          # DEF-LRL2 τ = max(EQ tolerance, tol_k × TR average at the anchor)
    gap: int = 30               # DEF-LRL3 max bars between consecutive points
    sep_k: float = 1.0          # DEF-LRL3 pullback between consecutive points ≥ sep_k × TR average (0 = off)
    drop_k: float = 2.0         # DEF-LRL4 first − latest point > drop_k × τ
    tra_len: int = 14
    cand_memory: int = 25       # DEF-LRL6 2-point candidates per side
    memory: int = 50            # DEF-LRL6 LRL records per side

    @property
    def lookback(self) -> int:
        """Bars a 3-point LRL confirmed at t depends on (its dependency graph): its first point
        is at most 2 × gap bars before the third (X3 = t − right), and τ needs the TR average
        there (tra_len true ranges, the first needing the close before it). Pine's Parity
        capture warm-up uses the same formula."""
        return self.right + 2 * self.gap + self.tra_len


@dataclass(frozen=True)
class HtfSettings:
    """docs/HTF_FVG.md DEF-B (approved 2026-10-29). The FVG definition and thresholds are the
    Phase 1 ones (FvgSettings, D4); these are the module's own constants."""
    tfs: tuple = ("15", "30", "60", "240", "D", "W")
    memory: int = 20            # DEF-B6 records per timeframe
    seeds: int = 3              # DEF-B2 open zones per direction recovered from before the chart history
    seed_memory: int = 20       # open zones per direction the HTF-side seed engine keeps
    timezone: str = "America/New_York"
    session_hour: int = 18      # CME session start: 4H / 1D / 1W buckets (to verify against TradingView)
    chart_sec: int = 60         # chart timeframe: only timeframes above it are active


@dataclass(frozen=True)
class CisdSettings:
    """docs/CISD.md DEF-CISD (CISD-R, approved 2026-10-30). The definition has no parameter:
    these are bookkeeping constants, variable here only so tests can exercise every rule."""
    memory: int = 50            # DEF-CISD7 records kept (≥ 1); only the newest is ACTIVE
    tra_len: int = 14           # TR average of the body / TR metadata (future displacement module); no decision reads it
    guard: int = 200            # [view] DEF-CISD9: no display or alert for a CISD confirmed before this bar index;
                                # chart-start / reload guard, not part of the definition; no decision reads it


@dataclass(frozen=True)
class DispSettings:
    """docs/DISPLACEMENT.md DISPLACEMENT-R (recommended 2026-11-01, awaiting the user's approval).
    k and clv are the definition's constants, variable here only so tests can exercise every rule."""
    k: float = 1.5              # DEF-DISP3 body ≥ k × TR average (the Tukey fence of body / TR on NQ, §E of the study)
    clv: float = 0.75           # DEF-DISP4 close in the outer quarter of the candle's range
    tra_len: int = 14           # DEF-DISP2 TR average of the bars before the candle (Phase 1 DEF-A2 length)
    memory: int = 50            # DEF-DISP8 records kept (≥ 1); the oldest goes first


@dataclass(frozen=True)
class SessionSettings:
    """DEF-F1…F6. Windows are `HHMM-HHMM` in `timezone`, every weekday."""
    timezone: str = "America/New_York"
    windows: tuple = (("Asia", "2000-0000"), ("London", "0200-0500"),
                      ("NY AM", "0930-1200"), ("NY PM", "1330-1600"))
    timeframe_sec: int = 60     # sessions run only on intraday charts up to 1H


@dataclass(frozen=True)
class LevelSettings:
    """DEF-G1…G6 chart-side logic.

    ASSUMPTION (ARCHITECTURE §7.2, unverified until G-V1…G-V5): the TradingView
    Daily bar for NQ starts at `day_start_hour` in `timezone` (18:00 ET) and the week
    on Sunday at that hour. The real PDH/PDL come from request.security, which this
    model cannot reproduce: see IstModel(htf=...).
    """
    timezone: str = "America/New_York"
    day_start_hour: int = 18
    timeframe_sec: int = 60


@dataclass(frozen=True)
class ViewSettings:
    """[view] inputs. The logic never reads these; tests vary them to prove it."""
    fvg_show: bool = True
    mit_rule: str = "fullFill"
    fvg_max_visible: int = 8
    minimal: bool = False
    liq_max_visible: int = 5
    eq_max_visible: int = 3
    liq_max_taken: int = 2
    show_sweeps: bool = True
    show_breaks: bool = False


MODULES = ("levels", "sessions", "fvg", "liq")
# Opt-in modules: not in the default run (src/IST.pine has no displacement yet; baselines and
# parity compare the default modules only).
KNOWN_MODULES = MODULES + ("lrl", "htf", "cisd", "disp")


@dataclass(frozen=True)
class Settings:
    tick: float = NQ_TICK
    fvg: FvgSettings = field(default_factory=FvgSettings)
    liq: LiqSettings = field(default_factory=LiqSettings)
    sessions: SessionSettings = field(default_factory=SessionSettings)
    levels: LevelSettings = field(default_factory=LevelSettings)
    view: ViewSettings = field(default_factory=ViewSettings)
    lrl: LrlSettings = field(default_factory=LrlSettings)
    htf: HtfSettings = field(default_factory=HtfSettings)
    cisd: CisdSettings = field(default_factory=CisdSettings)
    disp: DispSettings = field(default_factory=DispSettings)
    modules: tuple = MODULES

    @property
    def eps(self) -> float:          # Pine EPS: float tolerance for tick comparisons
        return self.tick * 0.01

    @property
    def half_tick(self) -> float:    # Pine HALF_TICK
        return self.tick * 0.5

    def with_(self, **kw) -> "Settings":
        return replace(self, **kw)

    def to_dict(self) -> dict:
        d = asdict(self)
        for opt in ("lrl", "htf", "cisd", "disp"):
            if opt not in self.modules:
                del d[opt]               # opt-in module: absent cases keep their earlier definition (regression)
        if "htf" in d:
            d["htf"]["tfs"] = list(self.htf.tfs)
        d["modules"] = list(self.modules)
        d["sessions"]["windows"] = [list(w) for w in self.sessions.windows]
        return d

    @classmethod
    def from_dict(cls, d: dict | None) -> "Settings":
        d = dict(d or {})
        sub = {"fvg": FvgSettings, "liq": LiqSettings, "sessions": SessionSettings,
               "levels": LevelSettings, "view": ViewSettings, "lrl": LrlSettings, "htf": HtfSettings,
               "cisd": CisdSettings, "disp": DispSettings}
        kw = {}
        for name, typ in sub.items():
            if name in d:
                part = dict(d[name])
                if name == "liq" and "preset" in part:
                    left, right, k, w = PRESETS[part.pop("preset")]
                    part = {"left": left, "right": right, "k": k, "dom": w, **part}
                elif name == "liq" and {"left", "right", "k"} & set(part):
                    part = {"dom": 0, **part}            # explicit numbers = the Custom preset: no dominance
                if name == "htf" and "tfs" in part:
                    part["tfs"] = tuple(part["tfs"])
                if name == "sessions" and "windows" in part:
                    part["windows"] = tuple(tuple(w) for w in part["windows"])
                known = {f.name for f in fields(typ)}
                unknown = set(part) - known
                if unknown:
                    raise ValueError(f"unknown {name} settings: {sorted(unknown)}")
                kw[name] = typ(**part)
        if "tick" in d:
            kw["tick"] = float(d["tick"])
        if "modules" in d:
            bad = set(d["modules"]) - set(KNOWN_MODULES)
            if bad:
                raise ValueError(f"unknown modules: {sorted(bad)}")
            kw["modules"] = tuple(m for m in KNOWN_MODULES if m in d["modules"])
        return cls(**kw)
