"""Target universe (CONTEXT-02, DEF-TU1…TU10, with the user's decisions D-TU1…D-TU9 of 2026-11-03): which
liquidity targets objectively exist at bar t, their identity, where they are and their factual lifecycle.
Spec: docs/context/TARGET_UNIVERSE_ORACLE.md. Python oracle only: no Pine, no drawing, no alert.

An OBSERVER of the frozen oracle engines. After each bar it reads Module G (`levels`: PDH / PDL / PWH /
PWL), Module F (`sessions`: completed session extremes) and Phase 2 (`liq`: BSL / SSL / EQH / EQL) and
never writes them: their events and state are byte-identical with it on and off (tested).

It answers "which targets exist, where, since when, in which state". It never answers "which one will
price go to": no preference, priority, rank, score, directional context or path. `source_class` is
provenance (metadata), not priority. PD arrays (FVG, IFVG, HTF FVG) and LRL are not targets.

Two kinds of target, never mixed:
* ADAPTED (BSL / SSL / EQH / EQL): identity, exact touches, take and class are Phase 2's own record
  fields (DEF-L4 / DEF-L5); nothing is recomputed or added (D-TU8: Phase 2 counts no EQ touches, so
  neither does this layer). Phase 2 says taken → the target is taken.
* OBSERVED (period and session extremes): Module F / G only *set* these values. TARGET_TAKEN is the
  DEF-L4 rule applied unchanged (high > price strictly; class by the taking bar's close: BREAK if
  beyond, else SWEEP), D-TU7; UNKNOWN when missing history prevents the classification.

EXACT_TOUCH (the bar's high / low is exactly the price) ≠ TARGET_TAKEN (strictly beyond). TARGET_REACHED
(high ≥ price / low ≤ price) is an evaluation concept: validation/models/outcomes.py.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from validation.models.eq import CLS_NAME
from validation.models.events import LEVEL_KINDS
from validation.models.ist import IstModel
from validation.models.types import Settings

H = 3_600_000
DUR = {"15": H // 4, "30": H // 2, "60": H, "240": 4 * H, "D": 24 * H, "W": 168 * H}   # nominal, break included
PERIOD = {"PDH": ("DAILY", 1, "D"), "PDL": ("DAILY", -1, "D"), "PWH": ("WEEKLY", 1, "W"), "PWL": ("WEEKLY", -1, "W")}
MIRROR = {"PDH": "PDL", "PDL": "PDH", "PWH": "PWL", "PWL": "PWH", "SESSION_HIGH": "SESSION_LOW",
          "SESSION_LOW": "SESSION_HIGH", "BSL": "SSL", "SSL": "BSL", "EQH": "EQL", "EQL": "EQH"}
PENDING = {"DAILY": "SOURCE_PENDING_GV", "WEEKLY": "SOURCE_PENDING_GV", "SESSION": "SOURCE_PENDING_T19_T22"}
AVAILABLE, TAKEN, UNVERIFIED, INVALID = "AVAILABLE", "TAKEN", "UNVERIFIED", "INVALID"
EVENTS = ("TARGET_CREATED", "TARGET_HISTORICAL", "TARGET_EXACT_TOUCH", "TARGET_TAKEN", "TARGET_STATE")   # in-bar order


@dataclass(frozen=True)
class TargetSettings:
    """`validated`: the source classes whose origin is validated (D-TU1, D-TU3). DAILY / WEEKLY wait for
    G-V1…G-V5 and SESSION for T19–T22 (docs/context/MANUAL_GATES.md): their targets are never AVAILABLE or
    TAKEN, only UNVERIFIED with every fact recorded (DEF-TU5)."""
    validated: frozenset = frozenset({"STRUCTURAL"})


@dataclass
class Target:
    id: str                         # DEF-TU2: type : source key : price in ticks
    type: str                       # PDH PDL PWH PWL SESSION_HIGH SESSION_LOW BSL SSL EQH EQL
    source_class: str               # DAILY · WEEKLY · SESSION · STRUCTURAL (provenance, not priority)
    side: int                       # +1 above · −1 below
    price: float
    price_ticks: int
    source_id: str                  # the frozen module's own identity
    origin_time: int | None         # the bar that printed the extreme, when the source knows it
    confirmed_at: int               # the bar on which the source makes it known
    known_at: str                   # OPEN: known from that bar's open (it may interact) · CLOSE: from its close (it may not)
    since: int                      # every trade from here on must be seen before it can be AVAILABLE
    adapted: bool                   # exact touches and take read from Phase 2, never recomputed
    first_observable_at: int | None = None
    period_role: str | None = None  # CURRENT | HISTORICAL_PERIOD_LEVEL (period levels only)
    age_periods: int = 0
    exact_touches: int | None = 0   # None: the source does not track exact touches (EQ, D-TU8)
    exact_touch_at: int | None = None
    taken_at: int | None = None
    taken_kind: str | None = None   # SWEEP · BREAK · UNKNOWN (the first take was not observed)
    taken_gap: bool = False
    taken_before: int | None = None  # beyond inside an evidence bar opening here; no observed take
    invalid_at: int | None = None
    invalid_reason: str | None = None
    history: str = "INCOMPLETE"     # OBSERVED: every trade since `since` was seen
    verification: tuple = ()        # SOURCE_PENDING_GV · SOURCE_PENDING_T19_T22 · HISTORY_INCOMPLETE
    state: str | None = None        # AVAILABLE · TAKEN · UNVERIFIED · INVALID (set at the first settle)
    meta: dict = field(default_factory=dict)

    @property
    def consumed(self) -> bool:
        return self.taken_at is not None or self.taken_before is not None

    def record(self) -> dict:
        return asdict(self)


def _ticks(p: float, tick: float) -> int:
    return round(p / tick)


def _beyond(side: int, high: float, low: float, p: float) -> bool:
    return high > p if side > 0 else low < p                  # DEF-L4: strictly beyond, no tolerance


class TargetUniverse:
    def __init__(self, model: IstModel, settings: TargetSettings | None = None, evidence=(),
                 order=("periods", "sessions", "structure")):
        """`evidence` (D-TU9): completed bars of the same feed (tf, open ms, high, low, known ms), the only way
        to prove what happened before the first loaded bar (DEF-TU6). Each must be closed when known.
        `order`: the adapters' registration order; registration is sorted by id, so it is irrelevant (tested)."""
        self.m, self.s, self.order = model, settings or TargetSettings(), order
        self.evidence = sorted(e for e in evidence if e[0] in DUR)
        bad = [e for e in self.evidence if e[4] < e[1] + DUR[e[0]]]
        if bad:
            raise ValueError(f"evidence bar known before its period closed: {bad[0]}")
        self.tick = model.settings.tick
        self.bar_ms = model.settings.levels.timeframe_sec * 1000
        self.targets: dict[str, Target] = {}
        self.events: list[tuple] = []          # (time, type, target id, detail), append-only
        self.blocked: list[tuple] = []         # (time, tag, reason): a value no identity can be given to
        self._cur: dict[str, object] = {}      # Module G tag → the RefLevel last seen
        self._key: dict[str, tuple] = {}       # "D" / "W" → Module G's period key at the previous bar
        self._ses: set = set()
        self._p2: dict[tuple, Target] = {}
        self._covered: dict[str, bool] = {}

    # ── per bar: call after model.step(c) ──
    def step(self) -> None:
        c, k = self.m.candles[-1], self.m.candles[-1].time
        n0 = len(self.events)
        new = [x for name in self.order for x in getattr(self, "_" + name)(k)]
        for x in sorted(new, key=lambda x: x.id):
            if x.id in self.targets:
                raise AssertionError(f"duplicate target identity {x.id}")
            self.targets[x.id] = x
        for x in self.targets.values():
            self._evidence(x, k)
            self._observe(x, c)
        for x in sorted(self.targets.values(), key=lambda x: x.id):
            self._settle(x, k)
        g = self.m.levels
        self._key = {"D": g.day and g.day.key, "W": g.week and g.week.key}
        self.events[n0:] = sorted(self.events[n0:], key=lambda e: (e[2], EVENTS.index(e[1])))   # canonical per bar

    def _emit(self, k, typ, x, detail="") -> None:
        self.events.append((k, typ, x.id, detail))

    # ── adapters (read only) ──
    def _periods(self, k) -> list[Target]:
        g, out = self.m.levels, []
        for tag, (cls, side, kind) in PERIOD.items():
            r = g.live.get(LEVEL_KINDS[tag])
            if r is None or r is self._cur.get(tag):
                continue
            self._cur[tag] = r
            src = self._source(kind)
            if src is None:
                self.blocked.append((k, tag, "SOURCE_PERIOD_UNKNOWN"))
                continue
            ticks = _ticks(r.price, self.tick)
            tid = f"{tag}:{src}:{ticks}"
            published, start = self._period(kind, r.known_time)
            if tid in self.targets:                          # the same source period published again: same target
                self.targets[tid].meta.setdefault("republished_in", []).append(published)
                continue
            for x in self.targets.values():                # a new source period: every earlier one of this tag ages
                if x.type == tag:
                    x.age_periods += 1
                    if x.period_role == "CURRENT":
                        x.period_role = "HISTORICAL_PERIOD_LEVEL"
                        self._emit(k, "TARGET_HISTORICAL", x)
            out.append(Target(tid, tag, cls, side, r.price, ticks, f"G:{tag}:{src}", r.anchor_time, r.known_time, "OPEN",
                              start, adapted=False, period_role="CURRENT",
                              meta={"source_period": src, "published_in": published}))
        return out

    def _source(self, kind) -> str | None:
        """D-TU2: the SOURCE period that produced the value: the feed bar the provider handed Module G (its
        trading date / ISO week, in Module G's own keys), else the period observed just before an observed
        roll. Neither → None: no identity can be given."""
        g, src = self.m.levels, getattr(self.m.levels.htf, "source", None)
        op = src(kind) if src is not None else None
        if op is not None:
            key = (g.day_key if kind == "D" else g.week_key)(op)
        else:
            now = g.day if kind == "D" else g.week
            key = self._key.get(kind)
            if key is None or now is None or key == now.key:
                return None
        return f"D{key[0]:04d}-{key[1]:02d}-{key[2]:02d}" if kind == "D" else f"W{key[0]:04d}-{key[1]:02d}"

    def _period(self, kind, t) -> tuple[str, int]:
        """The period in which Module G publishes the value (metadata) and its nominal start (`since`), both from
        Module G's own boundary assumption (LevelSettings: 18:00 ET day, Sunday 18:00 week)."""
        s = self.m.levels.s
        back = timedelta(hours=24 - s.day_start_hour)
        if kind == "D":
            y, mo, d = self.m.levels.day_key(t)
            key, first = f"D{y:04d}-{mo:02d}-{d:02d}", date(y, mo, d)
        else:
            y, w = self.m.levels.week_key(t)
            key, first = f"W{y:04d}-{w:02d}", date.fromisocalendar(y, w, 1)
        start = datetime(first.year, first.month, first.day, tzinfo=ZoneInfo(s.timezone)) - back
        return key, int(start.timestamp() * 1000)

    def _sessions(self, k) -> list[Target]:
        ses, out = self.m.sessions, []
        for s in ses.done + [x for x in ses.live if x is not None]:
            if not s.complete or (s.slot, s.id) in self._ses:
                continue
            self._ses.add((s.slot, s.id))
            name, spec = ses.s.windows[s.slot]
            src = f"F:{name}@{spec}:{s.id}"
            for typ, side, p, ot in (("SESSION_HIGH", 1, s.hi, s.hi_time), ("SESSION_LOW", -1, s.lo, s.lo_time)):
                ticks = _ticks(p, self.tick)
                out.append(Target(f"{typ}:{name}@{spec}:{s.id}:{ticks}", typ, "SESSION", side, p, ticks, src, ot,
                                  s.known_time, "OPEN", s.known_time, adapted=False,
                                  meta={"session": name, "window": spec, "start_time": s.start_time, "end_time": s.end_time}))
        return out

    def _structure(self, k) -> list[Target]:
        """Phase 2 → targets: identity, price, exact touches, take and class are the frozen record's own."""
        out, seen = [], set()
        for side in self.m.liq.sides():
            for x in side.all_levels():
                key = (side.name, x.id)
                seen.add(key)
                t = self._p2.get(key)
                if t is None:
                    ticks = _ticks(x.price, self.tick)
                    t = Target(f"{side.name}:{x.id}:{ticks}", side.name, "STRUCTURAL", side.sign, x.price, ticks,
                               f"L:{side.name}:{x.id}", x.origin_time, x.confirm_time, "CLOSE", x.confirm_time, adapted=True,
                               meta={"pivot": [x.piv_l, x.piv_r], "react": x.react, "tra": x.tra})
                    self._p2[key] = t
                    out.append(t)
                if x.touches and t.exact_touch_at is None:
                    t.exact_touch_at = k
                    self._emit(k, "TARGET_EXACT_TOUCH", t)
                t.exact_touches = x.touches
                if x.taken_bar is not None and t.taken_at is None:
                    t.taken_at, t.taken_kind, t.taken_gap = x.taken_time, CLS_NAME[x.cls], x.take_gap
                    self._emit(k, "TARGET_TAKEN", t, t.taken_kind)
            for cl in side.eqs:
                if cl.qual_bar is None:
                    continue                                    # never an EQH / EQL (DEF-L5.6)
                key = (side.eq_name, cl.id)
                seen.add(key)
                t = self._p2.get(key)
                if t is None:
                    ticks = _ticks(cl.bound, self.tick)
                    t = Target(f"{side.eq_name}:{cl.id}:{ticks}", side.eq_name, "STRUCTURAL", side.sign, cl.bound, ticks,
                               f"L5:{side.eq_name}:{cl.id}", cl.origin_time, cl.qual_time, "CLOSE", cl.qual_time, adapted=True,
                               exact_touches=None, meta={"members": list(cl.members), "ref": cl.ref})
                    self._p2[key] = t
                    out.append(t)
                if cl.bound != t.price:
                    raise AssertionError(f"{t.id}: the EQ boundary moved (DEF-L5.4 says it cannot)")
                t.meta["members"] = list(cl.members)
                if cl.taken_bar is not None and t.taken_at is None:
                    t.taken_at, t.taken_kind = cl.taken_time, CLS_NAME[cl.cls]
                    self._emit(k, "TARGET_TAKEN", t, t.taken_kind)
        for key, t in self._p2.items():
            if key not in seen and t.invalid_at is None:        # released by Phase 2's memory: no longer tracked
                t.invalid_at, t.invalid_reason = k, "SOURCE_MEMORY_RELEASED"
        return out

    # ── observation (observed targets only) ──
    def _observe(self, x: Target, c) -> None:
        """D-TU4: a bar may interact only if the target was known before its price movement could happen: known at
        a bar's OPEN → that bar counts; known at its CLOSE → only the bars after it."""
        if x.invalid_at is not None or x.consumed:
            return
        if c.time < x.confirmed_at or (x.known_at == "CLOSE" and c.time == x.confirmed_at):
            return
        if x.first_observable_at is None:
            x.first_observable_at = c.time
        if x.adapted:
            return                                              # Phase 2's own counters (D-TU8)
        if _beyond(x.side, c.high, c.low, x.price):
            out = c.close > x.price if x.side > 0 else c.close < x.price
            first = self._is_covered(x, c.time - self.bar_ms, before=c.time)
            x.taken_at, x.taken_gap = c.time, (c.open > x.price if x.side > 0 else c.open < x.price)
            x.taken_kind = ("BREAK" if out else "SWEEP") if first else "UNKNOWN"
            self._emit(c.time, "TARGET_TAKEN", x, x.taken_kind)
        elif (c.high if x.side > 0 else c.low) == x.price:
            x.exact_touches += 1
            if x.exact_touch_at is None:
                x.exact_touch_at = c.time
                self._emit(c.time, "TARGET_EXACT_TOUCH", x)

    # ── state (DEF-TU5) ──
    def _evidence(self, x: Target, k) -> None:
        """A completed evidence bar after `since`, known by now, went beyond while no observed bar did: the take
        lies where nothing was seen (before the loaded history). Consumed, class unknown."""
        if x.invalid_at is None and not x.consumed and not x.adapted and x.since < self.m.candles[0].time:
            hit = [op for tf, op, hi, lo, kn in self.evidence if kn <= k and op >= x.since and _beyond(x.side, hi, lo, x.price)]
            if hit:
                x.taken_before, x.taken_kind = min(hit), "UNKNOWN"
                self._emit(k, "TARGET_TAKEN", x, "UNKNOWN (inside an evidence bar, not observed)")

    def _settle(self, x: Target, k) -> None:
        x.history = "OBSERVED" if self._is_covered(x, k) else "INCOMPLETE"
        pend = () if x.source_class in self.s.validated else (PENDING[x.source_class],)
        x.verification = pend + (("HISTORY_INCOMPLETE",) if x.history != "OBSERVED" and not x.consumed else ())
        new = INVALID if x.invalid_at is not None else UNVERIFIED if pend else \
            TAKEN if x.consumed else UNVERIFIED if x.verification else AVAILABLE
        if x.state is None:
            self._emit(k, "TARGET_CREATED", x, f"{x.source_id} · {new}")
        elif new != x.state:
            self._emit(k, "TARGET_STATE", x, f"{x.state} → {new}")
        x.state = new

    def _is_covered(self, x: Target, k, before=None) -> bool:
        """Every trade from x.since to the close of the bar at k was seen and stayed on the near side of x.
        Consecutive bars of one timeframe leave nothing out between them (a weekend or the daily break is no
        gap), so a run of evidence bars that never went beyond x proves its whole span; a bar that went
        beyond proves nothing after `since`. The chart bars cover the loaded history. Monotone: once
        covered, always covered (cached)."""
        if before is None and self._covered.get(x.id):
            return True
        first = self.m.candles[0].time
        if x.since >= first:
            ok = True
        else:
            end = (before if before is not None else k + self.bar_ms)
            spans = [(first, end)]
            for tf in DUR:
                run = None
                for f, op, hi, lo, kn in self.evidence:
                    if f != tf or kn > k:
                        continue
                    if _beyond(x.side, hi, lo, x.price):
                        run = None
                    elif run is None:
                        run = [op, op + DUR[tf]]
                        spans.append(run)
                    else:
                        run[1] = op + DUR[tf]
            reach = x.since
            for a, b in sorted(map(tuple, spans)):
                if a <= reach:
                    reach = max(reach, b)
            ok = reach >= end
        if before is None and ok:
            self._covered[x.id] = True
        return ok

    # ── views at the current bar (derived, nothing stored) ──
    def pools(self) -> list[dict]:
        """DEF-TU8 (D-TU6): ≥ 2 unconsumed targets on one side at exactly the same tick. Members keep their
        identities; no tolerance, no cross-source radius."""
        groups = {}
        for x in self.targets.values():
            if x.invalid_at is None and not x.consumed:
                groups.setdefault((x.side, x.price_ticks), []).append(x)
        return [{"id": f"POOL:{'+' if side > 0 else '-'}:{ticks}@{min(x.confirmed_at for x in xs)}", "side": side,
                 "price_ticks": ticks, "members": sorted(x.id for x in xs)}
                for (side, ticks), xs in sorted(groups.items()) if len(xs) > 1]

    def ranges(self) -> dict:
        """DEF-TU9: the deterministic closed ranges valid now: the previous day and week (Module G's current
        values) and the latest completed instance of each session window."""
        out = {}
        cur = {x.type: x for x in self.targets.values() if x.period_role == "CURRENT"}
        for name, hi, lo in (("PREVIOUS_DAY", "PDH", "PDL"), ("PREVIOUS_WEEK", "PWH", "PWL")):
            if hi in cur and lo in cur:
                out[name] = (cur[lo].price_ticks, cur[hi].price_ticks)
        last = {}
        for x in self.targets.values():
            if x.source_class == "SESSION" and (x.meta["session"] not in last or x.confirmed_at > last[x.meta["session"]][0]):
                last[x.meta["session"]] = (x.confirmed_at, x.source_id)
        for name, (_, src) in last.items():
            xs = {x.type: x for x in self.targets.values() if x.source_id == src}
            out[f"SESSION:{name}"] = (xs["SESSION_LOW"].price_ticks, xs["SESSION_HIGH"].price_ticks)
        return out

    def externality(self, x: Target, ranges: dict | None = None) -> dict:
        """Categorical position of x against every range: ABOVE · AT_HIGH · INSIDE · AT_LOW · BELOW. No rank."""
        rel = {}
        for name, (lo, hi) in (ranges if ranges is not None else self.ranges()).items():
            p = x.price_ticks
            rel[name] = "ABOVE" if p > hi else "AT_HIGH" if p == hi else "BELOW" if p < lo else "AT_LOW" if p == lo else "INSIDE"
        return rel

    def snapshot(self) -> dict:
        rg = self.ranges()
        pool = {m: p["id"] for p in self.pools() for m in p["members"]}
        return {"targets": [{**x.record(), "composite": pool.get(x.id), "externality": self.externality(x, rg)}
                            for x in sorted(self.targets.values(), key=lambda x: x.id)],
                "pools": self.pools(), "ranges": rg}


def run(candles, settings: Settings | None = None, targets: TargetSettings | None = None, provider=None,
        evidence=(), order=("periods", "sessions", "structure"), snapshots=(), on_bar=None) -> tuple[IstModel, TargetUniverse, dict]:
    """Run the oracle with the target universe attached. `provider(levels_engine)` builds Module G's
    documented value provider (IstModel(htf=…)). Returns (model, universe, {bar: snapshot} for `snapshots`).
    `on_bar(i, model, universe)` is called after every bar (the evaluation harness issues hypotheses there)."""
    m = IstModel(settings)
    if provider is not None:
        m.levels.htf = provider(m.levels)
    tu = TargetUniverse(m, targets, evidence, order)
    snaps = {}
    for i, c in enumerate(candles):
        m.step(c)
        tu.step()
        if i in snapshots:
            snaps[i] = tu.snapshot()
        if on_bar is not None:
            on_bar(i, m, tu)
    return m, tu, snaps


class _Provider:
    """Module G's value provider (IstModel(htf=…)) that also tells which source bar it handed over (D-TU2)."""

    def __init__(self, engine, bars, level_sets):
        self.engine, self.bars, self.level_sets, self.last = engine, bars, level_sets, {}

    def __call__(self, kind, key, old):
        now = self.engine.prev.time
        xs = [b for b in self.bars if b[0] == kind and b[4] <= now]
        if xs:
            b = max(xs, key=lambda b: b[1])
            self.last[kind] = b[1]
            return b[2], b[3]
        self.last[kind] = None
        ls = [p for p in self.level_sets if p[0] <= now] if kind == "D" else []
        return (ls[-1][1], ls[-1][2]) if ls else None

    def source(self, kind) -> int | None:
        return self.last.get(kind)


def tradingview_periods(bars, level_sets=()):
    """Module G's provider from the values TradingView gave Pine: the latest completed D / W bar known at
    the current bar (`bars`: (tf, open, high, low, known ms)), else the latest LEVEL_SET (known ms, PDH, PDL),
    whose source bar is unknown (the observed roll then names the source period)."""
    return lambda engine: _Provider(engine, bars, level_sets)
