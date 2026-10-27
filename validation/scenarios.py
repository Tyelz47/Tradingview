"""Builders shared by the deterministic scenario tests (migrated from tests/liq_model.py).

Prices are around 100 with a 0.25 tick, after WARM (20 flat bars), so bar 20 is the
first scenario bar, as in the original tests. Structure ids are times; `evb()`
reports them as bar numbers so assertions read like the specification.
"""
from __future__ import annotations

from validation.candles import WARM, from_rows
from validation.invariants import run_checked
from validation.models.ist import IstModel
from validation.models.types import FvgSettings, LiqSettings, Settings

SWING_HI = [(100, 102, 99.5, 101), (101, 101.5, 99, 99.5)]               # BSL 102: swing bar 20, known at 21
EQ_BASE = SWING_HI + [(99.5, 100, 98, 98.5), (98.5, 99, 97.5, 98)]       # BSL 102 (id 20) active; bars 22-23 lower
# EQ_AB: A = 102 (bar 20) confirmed at 21; B = 102.25 prints at 24, takes A by one tick
# (A: TAKEN + SWEEP at 24), confirms at 25 and forms EQH (id = bar 25) with A, boundary 102.25.
EQ_AB = EQ_BASE + [(98, 102.25, 97.8, 101.5), (101.5, 101.75, 99, 99.5)]
QUIET_HI = [(99.5, 100, 98.5, 99), (99, 99.25, 98.6, 99)]                # bars 26-27, far below
# EQL mirror: A = 98 (bar 20) at 21; B = 97.75 prints at 24, takes A by one tick, confirms at 25.
EQL_AB = [(100, 100.5, 98, 99), (99, 101, 98.5, 100.5), (100.5, 102, 100, 101.5), (101.5, 102.5, 101, 102),
          (102, 102.2, 97.75, 98.5), (98.5, 100.25, 98.25, 100)]
QUIET_LO = [(100, 101.5, 99.5, 101), (101, 101.25, 100.75, 101)]          # bars 26-27, far above


def liq_settings(L=2, R=1, K=0.0, **kw) -> Settings:
    return Settings(modules=("liq",), liq=LiqSettings(left=L, right=R, k=K, **kw))


def liq_run(rows, L=2, R=1, K=0.0, warm=True, **kw) -> IstModel:
    """The original `run()`: WARM + rows, liquidity only, every invariant checked."""
    return run_checked(from_rows((WARM if warm else []) + list(rows)), liq_settings(L, R, K, **kw))


def fvg_settings(min_ticks=2, k_tra=0.0, k_rng=0.0, length=14, memory=50) -> Settings:
    return Settings(modules=("fvg",), fvg=FvgSettings(min_ticks=min_ticks, k_tra=k_tra, k_rng=k_rng,
                                                      length=length, memory=memory))


def fvg_run(rows, **kw) -> IstModel:
    return run_checked(from_rows(rows), fvg_settings(**kw))


def sid_bar(m: IstModel, sid: int) -> int:
    return next(i for i, c in enumerate(m.candles) if c.time == sid)


def ev(m: IstModel, type_=None, sid_bar_=None):
    """Events as (bar, type, structure bar, price), optionally filtered."""
    t2b = {c.time: i for i, c in enumerate(m.candles)}
    out = []
    for e in m.events:
        b = t2b.get(e.sid, e.sid)
        if (type_ is None or e.type == type_ or (isinstance(type_, tuple) and e.type in type_)) and \
                (sid_bar_ is None or b == sid_bar_):
            out.append((e.bar, e.type, b, e.price))
    return out


def kinds(m: IstModel, sid_bar_: int, prefix: str = "BSL") -> list[str]:
    return [t.split("_", 1)[1] for _, t, b, _ in ev(m) if b == sid_bar_ and t.startswith(prefix)]


def level(m: IstModel, bar: int, bsl: bool = True):
    side = m.liq.bsl if bsl else m.liq.ssl
    return next(x for x in side.all_levels() if x.origin_bar == bar)


def feed(m: IstModel, rows) -> IstModel:
    """Continue a model with more rows, one minute apart, WITHOUT the invariant monitor
    (used after `expand`, whose injected member is deliberately not a real pivot)."""
    from validation.models.types import Candle
    for o, h, l, c in rows:
        m.step(Candle(m.candles[-1].time + 60_000, float(o), float(h), float(l), float(c)))
    return m


def members(m: IstModel, cl) -> list[int]:
    return [sid_bar(m, x) for x in cl.members]


def expand(m: IstModel, bsl: bool, px: float):
    """TEST HOOK: confirm a member beyond the boundary WITHOUT its price path. Through
    real prices this cannot happen (DEF-L5.4: the cluster is taken first); this
    exercises the join path only."""
    side = m.liq.bsl if bsl else m.liq.ssl
    t = m.bar
    m.liq._register(side, px, t, m.candles[t].time, 1.0, 0.0, 1.0, t)
    return next(x for x in side.live if x.origin_bar == t)
