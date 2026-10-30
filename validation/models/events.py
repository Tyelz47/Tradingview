"""Canonical event stream (ARCHITECTURE §4, LIQUIDITY.md §5).

Every model emits `Event`s with the Pine event names. `canonical()` sorts them
with a fixed key, so two versions can be compared without depending on the order
in which a model happens to emit events inside one bar.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

# Pine kind numbers (src/IST.pine EV_*), used as `sid` for LEVEL_SET (K_*).
LEVEL_KINDS = {"PDH": 0, "PDL": 1, "PWH": 2, "PWL": 3, "DO": 4, "MO": 5}

# Canonical in-bar order: roughly Pine's engine order (levels, sessions, FVG, liquidity, LRL).
# LRL, then HTF FVG, then CISD types come last so the ranks of every earlier type are unchanged.
TYPES = (
    "LEVEL_SET",
    "SESSION_END", "SESSION_START",
    "FVG_FIRST_TOUCH", "FVG_CE_TOUCH", "FVG_FULL_FILL", "FVG_INVALIDATED", "FVG_CREATED", "FVG_DROPPED_MEMORY",
    "BSL_TAKEN", "SSL_TAKEN", "BSL_SWEEP", "SSL_SWEEP", "BSL_BREAK", "SSL_BREAK",
    "EQH_TAKEN", "EQL_TAKEN",
    "BSL_CREATED", "SSL_CREATED", "EQH_CREATED", "EQL_CREATED",
    "EQH_DROPPED_MEMORY", "EQL_DROPPED_MEMORY", "BSL_DROPPED_MEMORY", "SSL_DROPPED_MEMORY",
    "LRL_SWEEP", "LRL_BREAK", "LRL_DRIFT", "LRL_EXPIRED", "LRL_EXTENDED", "LRL_CONFIRMED", "LRL_DROPPED_MEMORY",
    "HTF_FVG_INVALIDATED", "HTF_FVG_SEEDED", "HTF_FVG_CREATED", "HTF_FVG_DROPPED_MEMORY",
    "HTF_FVG_FIRST_TOUCH", "HTF_FVG_CE_TOUCH", "HTF_FVG_FULL_FILL",
    "CISD_CONFIRMED", "CISD_DROPPED_MEMORY",
)
# The terminal LRL classes (docs/LRL.md DEF-LRL5): exactly one per LRL, never relabelled.
LRL_TERMINAL = ("LRL_DRIFT", "LRL_SWEEP", "LRL_BREAK", "LRL_EXPIRED")
RANK = {t: i for i, t in enumerate(TYPES)}
# Types of opt-in oracle modules that src/IST.pine does not implement yet (ST-14 excludes
# them; empty this set when Pine gains the module).
ORACLE_ONLY = frozenset(t for t in TYPES if t.startswith("CISD_"))

# Events that mark a one-time transition of one structure: at most once per (type, dir, sid).
# LRL_EXTENDED repeats (4th, 5th, … point) and is keyed by its bar, like LEVEL_SET.
ONCE = frozenset(t for t in TYPES if t not in ("LEVEL_SET", "LRL_EXTENDED"))


@dataclass(frozen=True)
class Event:
    bar: int            # bar index of the bar that emitted it
    time: int           # that bar's open time (ms)
    type: str           # Pine name, e.g. FVG_CREATED, BSL_SWEEP, EQH_TAKEN
    dir: int            # +1 bull/high/BSL/EQH · −1 bear/low/SSL/EQL · 0 n/a
    sid: int            # structure id (a time in ms) or K_* for LEVEL_SET
    price: float | None
    origin_bar: int
    meta: str = ""      # Pine `reason` text (informative, not compared by default)
    tf: str = ""        # HTF FVG only: the zone's timeframe ("15", "60", "D", …), part of its identity

    def key(self) -> tuple:
        return (self.bar, RANK[self.type], self.dir, self.sid, self.tf)

    def ident(self) -> tuple:
        """Identity used to match an event across versions."""
        tf = (self.tf,) if self.tf else ()
        return (self.type, self.dir, self.sid, *tf) if self.type in ONCE else (self.type, self.dir, self.sid, self.bar, *tf)

    @property
    def family(self) -> str:
        return self.type.split("_", 1)[0]

    def to_dict(self) -> dict:
        return asdict(self)

    def compact(self) -> list:
        return [self.bar, self.type, self.dir, self.sid, self.price]

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        return cls(**{k: d[k] for k in ("bar", "time", "type", "dir", "sid", "price", "origin_bar")},
                   meta=d.get("meta", ""), tf=d.get("tf", ""))


def canonical(events) -> list[Event]:
    return sorted(events, key=Event.key)


class EventLog:
    """Append-only log. `emit` stamps the current bar; nothing can rewrite an entry."""

    def __init__(self):
        self.events: list[Event] = []
        self.bar = -1
        self.time = 0

    def at(self, bar: int, time: int) -> None:
        self.bar, self.time = bar, time

    def emit(self, type_: str, dir_: int, sid: int, origin_bar: int, price, meta: str = "", tf: str = "") -> Event:
        e = Event(self.bar, self.time, type_, dir_, sid, None if price is None else float(price), origin_bar, meta, tf)
        self.events.append(e)
        return e


# ── Pine debug text (row "Last events", alerts) → Event fields, for the parity layer ──
_LINE = re.compile(
    r"^\s*(?:(?P<mt>\d\d-\d\d \d\d:\d\d)\s+)?(?:\S+ \S+ · )?(?P<name>[A-Z_]+)"
    r"(?: (?P<side>BULL|BEAR|HIGH|LOW))?(?: id=(?P<id>\d{4}-\d\d-\d\d \d\d:\d\d))?"
    r" px=(?P<px>[-\d.,]+|—)(?: · (?P<reason>.*))?$")


def parse_local(text: str, tz: str) -> int:
    """'2026-10-27 09:41' or '2026-10-27T09:41' in `tz` → ms since epoch."""
    dt = datetime.fromisoformat(text.replace(" ", "T")).replace(tzinfo=ZoneInfo(tz))
    return int(dt.timestamp() * 1000)


def parse_pine_line(line: str, tz: str, year: int) -> dict:
    """Parse one line copied from the Pine debug 'Last events' row or an alert message.

    Format (src/IST.pine f_lastEvents / f_evText):
      'MM-dd HH:mm  NAME[ BULL|BEAR|HIGH|LOW][ id=yyyy-MM-dd HH:mm] px=P[ · reason]'
    Returns {time, type, dir, sid, price, meta}; `time` is None when the line has no
    leading time (alert text).
    """
    m = _LINE.match(line.strip())
    if not m:
        raise ValueError(f"not a Pine event line: {line!r}")
    name, side = m["name"], m["side"]
    if name.startswith(("BSL_", "EQH_")):
        d = 1
    elif name.startswith(("SSL_", "EQL_")):
        d = -1
    else:
        d = {"BULL": 1, "HIGH": 1, "BEAR": -1, "LOW": -1}.get(side, 0)
    reason = m["reason"] or ""
    if name == "LEVEL_SET":
        sid = LEVEL_KINDS.get(reason.strip(), -1)
    else:
        sid = parse_local(m["id"], tz) if m["id"] else None
    t = parse_local(f"{year}-{m['mt']}", tz) if m["mt"] else None
    px = None if m["px"] == "—" else float(m["px"].replace(",", ""))
    return {"time": t, "type": name, "dir": d, "sid": sid, "price": px, "meta": reason}
