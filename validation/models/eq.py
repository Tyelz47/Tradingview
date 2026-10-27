"""EQH / EQL clusters — reference model of LIQUIDITY.md DEF-L5.1…L5.6.

Described for EQH; EQL mirrors it (`sign` = +1 for EQH, −1 for EQL, so
"beyond" is sign·(x − p) > 0).
"""
from __future__ import annotations

from dataclasses import dataclass, field

SWEEP, BREAK = 1, 2
CLS_NAME = {0: None, SWEEP: "SWEEP", BREAK: "BREAK"}


@dataclass
class EqCluster:
    # identity: never changes (DEF-L5.1)
    id: int                 # time of the bar where the 2nd member confirmed
    bar: int                # that bar
    is_high: bool
    ref: float              # creation reference = extreme of the first two members
    origin_bar: int         # earliest member's swing bar
    origin_time: int
    first_confirm_bar: int  # first member's confirmation (pool intact from here)
    # state
    bound: float            # current outer boundary; moves outward only
    members: list[int] = field(default_factory=list)   # member level ids, append-only
    last_bar: int | None = None
    last_time: int | None = None
    qual_bar: int | None = None
    qual_time: int | None = None
    taken_bar: int | None = None
    taken_time: int | None = None
    cls: int = 0

    @property
    def sign(self) -> int:
        return 1 if self.is_high else -1

    @property
    def active(self) -> bool:
        return self.taken_bar is None

    def outer(self, a: float, b: float) -> float:
        return max(a, b) if self.is_high else min(a, b)

    def state(self) -> dict:
        return {"id": self.id, "side": "EQH" if self.is_high else "EQL", "bar": self.bar, "ref": self.ref,
                "bound": self.bound, "members": list(self.members), "qual_bar": self.qual_bar,
                "taken_bar": self.taken_bar, "cls": CLS_NAME[self.cls]}


def nearest_active(clusters: list[EqCluster], price: float, tol: float, eps: float) -> EqCluster | None:
    """DEF-L5.2 join: nearest active cluster with |price − bound| ≤ tol; ties → newest."""
    hit, best = None, None
    for c in clusters:                      # oldest first, so `<=` lets the newest win ties
        d = abs(price - c.bound)
        if c.active and d <= tol + eps and (best is None or d <= best):
            hit, best = c, d
    return hit


def nearest_seed(live: list, new, tol: float, eps: float, is_high: bool):
    """DEF-L5.2 form: nearest earlier level in no cluster, within tolerance, with an intact pool.

    Intact = untaken, or taken but nothing has traded beyond the NEW level since
    (`far` is the furthest excursion beyond the old level).
    """
    seed, best = None, None
    for m in live:
        d = abs(new.price - m.price)
        intact = m.taken_bar is None or (new.price >= m.far if is_high else new.price <= m.far)
        if m.eq is None and intact and d <= tol + eps and (best is None or d <= best):
            seed, best = m, d
    return seed


def form(seed, new, bar: int, time: int, is_high: bool) -> EqCluster:
    edge = max(seed.price, new.price) if is_high else min(seed.price, new.price)
    return EqCluster(id=time, bar=bar, is_high=is_high, ref=edge, bound=edge, members=[seed.id],
                     origin_bar=seed.origin_bar, origin_time=seed.origin_time,
                     first_confirm_bar=seed.confirm_bar)


def join(c: EqCluster, level, bar: int, time: int, min_touch: int) -> bool:
    """Append a member; the boundary can only move outward. True if the cluster qualified now."""
    c.members.append(level.id)
    c.bound = c.outer(c.bound, level.price)
    c.last_bar, c.last_time = bar, time
    if c.qual_bar is None and len(c.members) >= min_touch:
        c.qual_bar, c.qual_time = bar, time
        return True
    return False


def drop_victim(clusters: list[EqCluster]) -> int:
    """Memory policy: the oldest taken cluster (never the newest), else the oldest one."""
    return next((i for i, c in enumerate(clusters[:-1]) if not c.active), 0)
