"""Explicit, named invariants checked after every bar.

`Monitor(model).check()` runs after each `model.step(candle)`. A violation raises
InvariantViolation naming the invariant id, its text, the bar and the details.
Every invariant also has a negative test (tests/test_invariants.py) that corrupts
state on purpose and proves the detector fires.

Sweeps: with `sweep_every=1` (property tests) every record is checked on every
bar. With N > 1 (long walks) records that can change (open FVGs, live levels,
active clusters, anything touched by this bar's events) are checked every bar —
so "never missed" stays exact to the bar — and every record, frozen ones included,
every N bars and once more at the end of the run.
"""
from __future__ import annotations

import operator
from dataclasses import dataclass

from validation import stats
from validation.models.eq import BREAK, SWEEP
from validation.models.events import LRL_TERMINAL, ONCE, RANK
from validation.models.sessions import in_window


@dataclass(frozen=True)
class Invariant:
    id: str
    family: str
    text: str


REGISTRY: dict[str, Invariant] = {}


def _inv(id_: str, family: str, text: str) -> str:
    REGISTRY[id_] = Invariant(id_, family, text)
    return id_


# ── events ──
EV_BAR = _inv("INV-EV-01", "EVENTS", "an event is stamped with the bar that emitted it; stream time never moves backward")
EV_APPEND = _inv("INV-EV-02", "EVENTS", "the event log is append-only: no past event is rewritten or removed")
EV_ONCE = _inv("INV-EV-03", "EVENTS", "a transition event fires at most once per (type, direction, structure id)")
EV_AFTER_DROP = _inv("INV-EV-04", "EVENTS", "no event for a structure after it was dropped from memory")
EV_KNOWN = _inv("INV-EV-05", "EVENTS", "event type and direction are valid; every event refers to a structure that exists")
# ── FVG (DEF-A1…A7, §3.3, §6) ──
FVG_GEOM = _inv("INV-FVG-01", "FVG", "top > bottom (gap ≥ min ticks > 0)")
FVG_CE = _inv("INV-FVG-02", "FVG", "CE = (top + bottom) / 2, strictly inside the zone")
FVG_ONCE = _inv("INV-FVG-03", "FVG", "each milestone (touch, CE, full, invalidation) is stamped once and never changes")
FVG_ORDER = _inv("INV-FVG-04", "FVG", "milestones start after confirmation and respect touch ≤ CE ≤ full ≤ invalidation")
FVG_FIRST = _inv("INV-FVG-05", "FVG", "a milestone is stamped on the FIRST bar that reaches it, never missed")
FVG_INVAL = _inv("INV-FVG-06", "FVG", "invalidation = first confirmed close beyond the far edge, never missed")
FVG_EXT = _inv("INV-FVG-07", "FVG", "the deepest-penetration extreme only moves deeper")
FVG_BIRTH = _inv("INV-FVG-08", "FVG", "a record is born on candle 3 with DEF-A1 geometry and gap ≥ all §6 thresholds")
FVG_MEM = _inv("INV-FVG-09", "FVG", "records per direction ≤ memory; an open record is released only when no closed one exists")
FVG_EVSTATE = _inv("INV-FVG-10", "FVG", "milestone events and record fields agree (same bar, same structure)")
# ── liquidity (DEF-L1…L4, L6) ──
LIQ_CONF = _inv("INV-LIQ-01", "LIQUIDITY", "confirmation = origin + right ≥ origin")
LIQ_AFTER = _inv("INV-LIQ-02", "LIQUIDITY", "a level cannot be taken on or before its confirmation bar")
LIQ_CLASS = _inv("INV-LIQ-03", "LIQUIDITY", "a taken level has exactly one class; BREAK iff the taking close is strictly beyond")
LIQ_FROZEN = _inv("INV-LIQ-04", "LIQUIDITY", "take facts (bar, extreme, close, gap, class) never change once set")
LIQ_BEYOND = _inv("INV-LIQ-05", "LIQUIDITY", "taken means strictly beyond: the taking bar's extreme is beyond the price")
LIQ_FIRST = _inv("INV-LIQ-06", "LIQUIDITY", "the take is on the FIRST bar strictly beyond, never missed")
LIQ_SIG = _inv("INV-LIQ-07", "LIQUIDITY", "a level passed the significance filter at birth: reaction ≥ k × TR average")
LIQ_PIVOT = _inv("INV-LIQ-08", "LIQUIDITY", "a level is a DEF-L1 pivot (strict left, ≥ right) judged exactly at X + right")
LIQ_MEM = _inv("INV-LIQ-09", "LIQUIDITY", "live + closed records per side ≤ memory")
LIQ_EVSTATE = _inv("INV-LIQ-10", "LIQUIDITY", "TAKEN and exactly one of SWEEP/BREAK fire together on the taking bar")
LIQ_DOM = _inv("INV-LIQ-11", "LIQUIDITY", "a level was dominant at birth: no extreme strictly beyond its price + EQ "
                                          "tolerance in the W bars before its swing bar (C1)")
LIQ_COUNT = _inv("INV-LIQ-12", "LIQUIDITY", "selectivity counters partition: REJECT = reaction + dominance + both, "
                                            "PASS = levels created, pivots ≥ PASS + REJECT")
# ── EQH / EQL (DEF-L5) ──
EQ_UNIQUE = _inv("INV-EQ-01", "EQ", "an individual level belongs to at most one cluster")
EQ_ID = _inv("INV-EQ-02", "EQ", "cluster identity (id, ref, origin, creation bar) never changes")
EQ_BOUND = _inv("INV-EQ-03", "EQ", "EQH boundary never decreases; EQL boundary never increases")
EQ_MEMBERS = _inv("INV-EQ-04", "EQ", "members are only appended: count never decreases, order never changes")
EQ_AFTER = _inv("INV-EQ-05", "EQ", "a cluster is never taken on or before the bar it (or its latest member) became known")
EQ_FROZEN = _inv("INV-EQ-06", "EQ", "a cluster take (bar, class) never changes once set")
EQ_NO_REWRITE = _inv("INV-EQ-07", "EQ", "adding a member never rewrites the member levels' individual take facts")
EQ_TOL = _inv("INV-EQ-08", "EQ", "members lie within [boundary − tolerance, boundary]")
EQ_THEOREM = _inv("INV-EQ-09", "EQ", "boundary == creation reference in every reachable state (DEF-L5.4)")
EQ_INTACT = _inv("INV-EQ-10", "EQ", "the pool is untraded beyond its boundary from the first member's confirmation until its take")
EQ_QUAL = _inv("INV-EQ-11", "EQ", "qualified iff members ≥ minimum; EQ_CREATED only for qualified clusters")
EQ_EVENT = _inv("INV-EQ-12", "EQ", "EQ_TAKEN only for a qualified cluster, at its boundary, on its taking bar")
# ── sessions / levels (DEF-F, DEF-G) ──
SES_RANGE = _inv("INV-SES-01", "SESSIONS", "final session high/low = max/min of the bars inside; end = last bar inside")
SES_START = _inv("INV-SES-02", "SESSIONS", "a session starts on its first bar inside the window, never on the first loaded bar")
LVL_SET = _inv("INV-LVL-01", "LEVELS", "LEVEL_SET carries a price and matches the live level known on that bar")
# ── LRL (docs/LRL.md DEF-LRL1…LRL6; checked only when the opt-in module runs) ──
LRL_UNIQUE = _inv("INV-LRL-01", "LRL", "a pivot belongs to at most one LRL")
LRL_POINTS = _inv("INV-LRL-02", "LRL", "points are DEF-LRL1 pivots; consecutive points fail strictly (step > EQ "
                                       "tolerance), are ≤ gap bars apart and separated by a pullback ≥ sep_k × TR average")
LRL_LINE = _inv("INV-LRL-03", "LRL", "≥ 3 points; τ = max(EQ tolerance, tol_k × TR average at the first point); every "
                                     "point within τ of the chord; first − latest > drop_k × τ")
LRL_CLEAN = _inv("INV-LRL-04", "LRL", "no high beyond line + τ from the first point to the current bar (active), the "
                                      "bar before the take (taken) or the expiry bar (expired)")
LRL_TAKE = _inv("INV-LRL-05", "LRL", "a crossed LRL: the ending high is strictly beyond the boundary y + τ; DRIFT "
                                     "iff it is not beyond the previous bar's boundary; otherwise BREAK iff the close "
                                     "is beyond y + τ, else SWEEP; the recorded level is y + τ")
LRL_TIMING = _inv("INV-LRL-06", "LRL", "confirmed at X3 + right, extended at Xn + right; it ends after its last "
                                       "decision bar and expires on the first bar after Xn + gap + right")
LRL_FROZEN = _inv("INV-LRL-07", "LRL", "id, τ and confirmation bar never change; points and extensions are "
                                       "append-only; end facts never change")
LRL_EVENTS = _inv("INV-LRL-08", "LRL", "events and records agree: CONFIRMED on the confirmation bar, one EXTENDED "
                                       "per extension, one terminal event on the end bar, prices as specified")
LRL_MEM = _inv("INV-LRL-09", "LRL", "records per side ≤ memory, candidates ≤ candidate memory; an active record "
                                    "is dropped only when no ended one exists")
LRL_TERM = _inv("INV-LRL-10", "LRL", "an LRL ends at most once, with exactly one of LRL_DRIFT / LRL_SWEEP / LRL_BREAK / "
                                     "LRL_EXPIRED, never relabelled; an active LRL has no terminal facts")

LIQ_FACTS = ("taken_bar", "take_ext", "take_close", "take_gap", "cls")


def _facts(x) -> tuple:
    return (x.taken_bar, x.take_ext, x.take_close, x.take_gap, x.cls)


class InvariantViolation(AssertionError):
    def __init__(self, inv_id: str, message: str, bar: int):
        self.inv_id, self.message, self.bar = inv_id, message, bar
        text = REGISTRY[inv_id].text if inv_id in REGISTRY else inv_id
        super().__init__(f"[{inv_id}] {text} — bar {bar}: {message}")


class Monitor:
    """Checks every registered invariant after each bar. Snapshots hold a reference to
    their record, so Python object ids stay unique for the whole run."""

    def __init__(self, model, sweep_every: int = 1):
        self.m = model
        self.sweep_every = max(1, sweep_every)
        self.n_events = 0
        self.last_event = None
        self.shadow: list = []                  # our own copy of the log, for INV-EV-02
        self.seen: set = set()
        self.dropped: set = set()
        self.known: set = set()                 # (family, dir, sid) that exist
        self.fvg_snap: dict = {}
        self.liq_snap: dict = {}
        lq = getattr(model, "liq", None)        # CREATED events per side so far, for INV-LIQ-12
        self.liq_made = {1: lq.bsl.levels, -1: lq.ssl.levels} if lq is not None else {1: 0, -1: 0}
        self.eq_snap: dict = {}
        self.lrl_snap: dict = {}
        self.lrl_ended: set = set()             # (dir, id) with a terminal event, for INV-LRL-10
        self.tol = model.settings.liq.tol_ticks * model.settings.tick
        self.eps = model.settings.eps

    def _fail(self, inv_id: str, msg: str):
        raise InvariantViolation(inv_id, msg, self.m.bar)

    def check(self, full: bool | None = None) -> None:
        m = self.m
        bar, c = m.bar, m.candles[-1]
        if full is None:
            full = bar % self.sweep_every == 0
        new = m.events[self.n_events:]
        self._events(bar, c, new, full)
        if m.fvg is not None:
            self._fvg(bar, c, new, full)
        if m.liq is not None:
            self._liq(bar, c, new, full)
            self._eq(bar, c, new, full)
        if m.sessions is not None:
            self._sessions(bar, c, new)
        if m.levels is not None:
            self._levels(bar, new)
        if getattr(m, "lrl", None) is not None:
            self._lrl(bar, new, full)
        self.n_events = len(m.events)
        self.last_event = m.events[-1] if m.events else None

    def final(self) -> None:
        """One full sweep of every record on the last bar (frozen facts included)."""
        m = self.m
        if not m.candles:
            return
        bar, c = m.bar, m.candles[-1]
        self._events(bar, c, [], True)
        if m.fvg is not None:
            self._fvg(bar, c, [], True, final=True)
        if m.liq is not None:
            self._liq(bar, c, [], True, final=True)
            self._eq(bar, c, [], True, final=True)
        if getattr(m, "lrl", None) is not None:
            self._lrl(bar, [], True, final=True)

    # ── events ──
    def _events(self, bar, c, new, full=True):
        ev = self.m.events
        if self.n_events and (len(ev) < self.n_events or ev[self.n_events - 1] is not self.last_event):
            self._fail(EV_APPEND, "an earlier event was replaced or removed")
        if full and not all(map(operator.is_, ev, self.shadow)):
            i = next(i for i, (a, b) in enumerate(zip(ev, self.shadow)) if a is not b)
            self._fail(EV_APPEND, f"event #{i} was rewritten: {self.shadow[i]} -> {ev[i]}")
        self.shadow.extend(new)
        for e in new:
            if e.bar != bar or e.time != c.time:
                self._fail(EV_BAR, f"{e.type} stamped bar {e.bar}/{e.time}, emitted on bar {bar}/{c.time}")
            if e.type not in RANK or e.dir not in (-1, 0, 1):
                self._fail(EV_KNOWN, f"unknown event {e.type} dir {e.dir}")
            fam = (e.type.split("_")[0], e.dir, e.sid)
            if e.type in ONCE:
                if e.ident() in self.seen:
                    self._fail(EV_ONCE, f"{e.type} dir {e.dir} id {e.sid} fired twice")
                self.seen.add(e.ident())
            if fam in self.dropped:
                self._fail(EV_AFTER_DROP, f"{e.type} id {e.sid} after its DROPPED_MEMORY")
            if e.type.endswith("_CREATED") or e.type in ("SESSION_START", "LRL_CONFIRMED"):
                self.known.add(fam)
            elif e.type != "LEVEL_SET" and fam not in self.known:
                self._fail(EV_KNOWN, f"{e.type} id {e.sid} refers to no known structure")
            if e.type.endswith("_DROPPED_MEMORY"):
                self.dropped.add(fam)
        for k in (EV_BAR, EV_APPEND, EV_ONCE, EV_AFTER_DROP, EV_KNOWN):
            stats.INV_CHECKS[k] += 1

    # ── FVG ──
    def _fvg(self, bar, c, new, full, final=False):
        f = self.m.fvg
        s = self.m.settings
        if len(f.bull) > s.fvg.memory or len(f.bear) > s.fvg.memory:
            self._fail(FVG_MEM, f"{len(f.bull)} bull / {len(f.bear)} bear records > memory {s.fvg.memory}")
        stats.peak("fvg.records_per_direction", max(len(f.bull), len(f.bear)))
        if f.last_drop and f.last_drop["was_open"] and f.last_drop["closed_available"]:
            self._fail(FVG_MEM, f"open record {f.last_drop['id']} released while a closed one existed")
        stamped_now = {(e.type, e.sid) for e in new
                       if e.type.startswith("FVG_") and e.type not in ("FVG_CREATED", "FVG_DROPPED_MEMORY")}
        for z in f.bull + f.bear:
            changeable = z.inv_bar is None or z.inv_bar == bar
            if not (full or changeable):
                continue                                   # closed: frozen, re-checked on sweeps
            if full or z.confirm_bar == bar:
                if not z.top > z.bottom:
                    self._fail(FVG_GEOM, f"FVG {z.id}: top {z.top} ≤ bottom {z.bottom}")
                if z.mid != (z.top + z.bottom) / 2 or not z.bottom < z.mid < z.top:
                    self._fail(FVG_CE, f"FVG {z.id}: CE {z.mid} for [{z.bottom}, {z.top}]")
            marks = (z.touch_bar, z.ce_bar, z.full_bar, z.inv_bar)
            old = self.fvg_snap.get(id(z))
            if old is not None:
                if old[0] != marks and any(a is not None and a != b for a, b in zip(old[0], marks)):
                    self._fail(FVG_ONCE, f"FVG {z.id}: milestones {old[0]} → {marks}")
                if (z.extreme > old[1]) if z.is_bull else (z.extreme < old[1]):
                    self._fail(FVG_EXT, f"FVG {z.id}: extreme {old[1]} → {z.extreme}")
            if old is None or old[0] != marks or old[1] != z.extreme:
                self.fvg_snap[id(z)] = (marks, z.extreme, z)
            if marks != (None, None, None, None):
                for i, mb in enumerate(marks):
                    if mb is None:
                        continue
                    if mb <= z.confirm_bar:
                        self._fail(FVG_ORDER, f"FVG {z.id}: milestone at {mb}, not after confirmation {z.confirm_bar}")
                    if i and (marks[i - 1] is None or marks[i - 1] > mb):
                        self._fail(FVG_ORDER, f"FVG {z.id}: milestones (touch, CE, full, inval) = {marks}")
            if changeable and bar > z.confirm_bar and not final:
                self._first_reach(z, bar, c, stamped_now)
        for e in new:
            if e.type == "FVG_CREATED":
                self._fvg_birth(e, bar, f)
        for k in (FVG_GEOM, FVG_CE, FVG_ONCE, FVG_ORDER, FVG_FIRST, FVG_INVAL, FVG_EXT, FVG_BIRTH, FVG_MEM, FVG_EVSTATE):
            stats.INV_CHECKS[k] += 1

    def _first_reach(self, z, bar, c, stamped_now):
        """Checked every bar, so 'never missed' + 'stamped bar reaches it' = first reach."""
        bull = z.is_bull
        near, far = (z.top, z.bottom) if bull else (z.bottom, z.top)
        reach = c.low if bull else c.high
        for name, lv, mb, et in (("touch", near, z.touch_bar, "FVG_FIRST_TOUCH"), ("CE", z.mid, z.ce_bar, "FVG_CE_TOUCH"),
                                 ("full", far, z.full_bar, "FVG_FULL_FILL"), ("invalidation", None, z.inv_bar, "FVG_INVALIDATED")):
            if lv is not None:
                hit = reach <= lv if bull else reach >= lv
                if hit and mb is None:
                    self._fail(FVG_FIRST, f"FVG {z.id}: bar reaches {name} {lv} but nothing was stamped")
                if mb == bar and not hit:
                    self._fail(FVG_FIRST, f"FVG {z.id}: {name} stamped on a bar that does not reach {lv}")
            if (mb == bar) != ((et, z.id) in stamped_now):
                self._fail(FVG_EVSTATE, f"FVG {z.id}: {name} field = bar {mb}, event this bar: {(et, z.id) in stamped_now}")
        beyond = c.close < z.bottom if bull else c.close > z.top
        if beyond and z.inv_bar is None:
            self._fail(FVG_INVAL, f"FVG {z.id}: close {c.close} beyond the far edge but not invalidated")
        if z.inv_bar == bar and not beyond:
            self._fail(FVG_INVAL, f"FVG {z.id}: invalidated on a close {c.close} that is not beyond")

    def _fvg_birth(self, e, bar, f):
        cs = self.m.candles
        z = next((r for r in reversed(f.bull + f.bear) if r.id == e.sid and r.dir == e.dir), None)
        if z is None:
            self._fail(FVG_BIRTH, f"FVG_CREATED {e.sid} has no record")
        c1, c3 = cs[bar - 2], cs[bar]
        geo = (c3.low, c1.high) if z.is_bull else (c1.low, c3.high)
        if z.confirm_bar != bar or z.origin_bar != bar - 2 or (z.top, z.bottom) != geo:
            self._fail(FVG_BIRTH, f"FVG {z.id}: born {z.origin_bar}->{z.confirm_bar} [{z.bottom},{z.top}], expected geometry {geo}")
        gap = z.top - z.bottom
        if not (gap >= z.thr_tick - self.eps and z.thr_tra is not None and z.thr_rng is not None
                and gap >= z.thr_tra and gap >= z.thr_rng):
            self._fail(FVG_BIRTH, f"FVG {z.id}: gap {gap} below its thresholds {z.thr_tick}/{z.thr_tra}/{z.thr_rng}")
        if e.price != z.mid:
            self._fail(FVG_EVSTATE, f"FVG_CREATED price {e.price} != CE {z.mid}")

    # ── liquidity ──
    def _liq(self, bar, c, new, full, final=False):
        lq = self.m.liq
        s = lq.s
        taken_now = {(e.dir, e.sid) for e in new if e.type in ("BSL_TAKEN", "SSL_TAKEN")}
        classes = [(e.dir, e.sid) for e in new if e.type in ("BSL_SWEEP", "SSL_SWEEP", "BSL_BREAK", "SSL_BREAK")]
        if sorted(taken_now) != sorted(classes) or len(set(classes)) != len(classes):
            self._fail(LIQ_EVSTATE, f"TAKEN {sorted(taken_now)} vs class events {sorted(classes)}")
        created_now = [(e.dir, e.sid) for e in new if e.type in ("BSL_CREATED", "SSL_CREATED")]
        for side in lq.sides():
            n = len(side.live) + len(side.hist)
            if n > s.memory:
                self._fail(LIQ_MEM, f"{side.name}: {n} records > memory {s.memory}")
            stats.peak("liq.records_per_side", n)
            sg = side.sign
            if full:
                recs = side.hist + side.live
            elif any(d == sg for d, _ in taken_now):     # a level taken now may already sit in hist
                recs = [x for x in side.hist if (sg, x.id) in taken_now] + side.live
            else:
                recs = side.live
            beyond_px = c.high if sg > 0 else c.low
            for x in recs:
                if full or x.confirm_bar == bar:
                    if x.confirm_bar != x.origin_bar + x.piv_r or x.confirm_bar < x.origin_bar:
                        self._fail(LIQ_CONF, f"{side.name} {x.id}: origin {x.origin_bar}, confirm {x.confirm_bar}, right {x.piv_r}")
                    if x.react < x.react_req or abs(x.react_req - s.k * x.tra) > 1e-9:
                        self._fail(LIQ_SIG, f"{side.name} {x.id}: reaction {x.react} < required {x.react_req}")
                    if s.dom:                        # recomputed here, independently of the engine
                        X, w = x.origin_bar, s.dom
                        ref = None if X < w else max(lq.H[X - w:X]) if sg > 0 else min(lq.Lo[X - w:X])
                        if ref is None or sg * (ref - x.price) > self.tol + self.eps:
                            self._fail(LIQ_DOM, f"{side.name} {x.id}: earlier extreme {ref} in the {w} bars "
                                                f"before bar {X} vs price {x.price} ± {self.tol}")
                if x.taken_bar is None:
                    if x.cls != 0:
                        self._fail(LIQ_CLASS, f"{side.name} {x.id}: classified {x.cls} without a take")
                    if not final and bar > x.confirm_bar and sg * (beyond_px - x.price) > 0:
                        self._fail(LIQ_FIRST, f"{side.name} {x.id}: bar trades beyond {x.price} but the level is not taken")
                    continue
                facts = _facts(x)
                old = self.liq_snap.get(id(x))
                if old is not None and old[0] != facts:
                    self._fail(LIQ_FROZEN, f"{side.name} {x.id}: take facts {old[0]} → {facts}")
                if old is None:
                    self.liq_snap[id(x)] = (facts, x)
                if full or x.taken_bar == bar:
                    if x.taken_bar <= x.confirm_bar:
                        self._fail(LIQ_AFTER, f"{side.name} {x.id}: taken at {x.taken_bar}, confirmed at {x.confirm_bar}")
                    if x.cls not in (SWEEP, BREAK) or (x.cls == BREAK) != (sg * (x.take_close - x.price) > 0):
                        self._fail(LIQ_CLASS, f"{side.name} {x.id}: class {x.cls} with close {x.take_close} vs {x.price}")
                    k = self.m.candles[x.taken_bar]
                    if not sg * (x.take_ext - x.price) > 0 or x.take_ext != (k.high if sg > 0 else k.low):
                        self._fail(LIQ_BEYOND, f"{side.name} {x.id}: take extreme {x.take_ext} vs price {x.price}")
                    if not final and x.taken_bar == bar and (sg, x.id) not in taken_now:
                        self._fail(LIQ_EVSTATE, f"{side.name} {x.id}: taken this bar without a TAKEN event")
            for d, sid in created_now:
                if d == sg:
                    self._pivot(side, sid, bar, lq)
            self.liq_made[sg] += sum(d == sg for d, _ in created_now)
            if side.rejects != side.rej_react + side.rej_dom + side.rej_both or side.levels != self.liq_made[sg] \
                    or side.pivots < side.levels + side.rejects:
                self._fail(LIQ_COUNT, f"{side.name}: pivots {side.pivots}, PASS {side.levels} (created "
                                      f"{self.liq_made[sg]}), REJECT {side.rejects} = {side.rej_react} + "
                                      f"{side.rej_dom} + {side.rej_both}?")
        for k in (LIQ_CONF, LIQ_AFTER, LIQ_CLASS, LIQ_FROZEN, LIQ_BEYOND, LIQ_FIRST, LIQ_SIG, LIQ_PIVOT, LIQ_MEM,
                  LIQ_EVSTATE, LIQ_DOM, LIQ_COUNT):
            stats.INV_CHECKS[k] += 1

    def _pivot(self, side, sid, t, lq):
        x = next((y for y in reversed(side.live) if y.id == sid), None)
        if x is None:
            return                                   # released by memory on the same bar
        H, Lo, L, R = lq.H, lq.Lo, x.piv_l, x.piv_r
        X = x.origin_bar
        if x.confirm_bar != t or X != t - R:
            self._fail(LIQ_PIVOT, f"{side.name} {x.id}: judged at {x.confirm_bar}, expected {X} + {R}")
        if side.is_bsl:
            ok = H[X] == x.price and H[X] > max(H[X - L:X]) and H[X] >= max(H[X + 1:t + 1])
            react = H[X] - min(Lo[X + 1:t + 1])
        else:
            ok = Lo[X] == x.price and Lo[X] < min(Lo[X - L:X]) and Lo[X] <= min(Lo[X + 1:t + 1])
            react = max(H[X + 1:t + 1]) - Lo[X]
        if not ok or react != x.react:
            self._fail(LIQ_PIVOT, f"{side.name} {x.id}: not a DEF-L1 pivot at {X} (or reaction {x.react} != {react})")

    # ── EQ ──
    def _eq(self, bar, c, new, full, final=False):
        lq = self.m.liq
        cs = self.m.candles
        membership_changed = any(e.type in ("BSL_CREATED", "SSL_CREATED") for e in new)
        for side in lq.sides():
            sg = side.sign
            stats.peak("eq.clusters_per_side", len(side.eqs))
            deep = full or membership_changed
            levels = {x.id: x for x in side.live + side.hist} if deep else None
            owner = {}
            beyond_px = c.high if sg > 0 else c.low
            for cl in side.eqs:
                if not (deep or cl.active or cl.taken_bar == bar):
                    continue                                    # taken: frozen, re-checked on sweeps
                if deep:
                    for mid in cl.members:
                        if mid in owner:
                            self._fail(EQ_UNIQUE, f"{side.name} level {mid} in clusters {owner[mid]} and {cl.id}")
                        owner[mid] = cl.id
                ident = (cl.id, cl.ref, cl.origin_bar, cl.bar)
                old = self.eq_snap.get(id(cl))
                if old is None:
                    self.known.add((side.eq_name, sg, cl.id))
                    seg = range(cl.first_confirm_bar + 1, bar + 1)
                    if any(sg * ((cs[j].high if sg > 0 else cs[j].low) - cl.bound) > 0 for j in seg):
                        self._fail(EQ_INTACT, f"{side.eq_name} {cl.id}: price traded beyond {cl.bound} before it formed")
                else:
                    if old[0] != ident:
                        self._fail(EQ_ID, f"{side.eq_name}: identity {old[0]} → {ident}")
                    if sg * (cl.bound - old[1]) < 0:
                        self._fail(EQ_BOUND, f"{side.eq_name} {cl.id}: boundary {old[1]} → {cl.bound}")
                    if tuple(cl.members[:len(old[2])]) != old[2]:
                        self._fail(EQ_MEMBERS, f"{side.eq_name} {cl.id}: members {old[2]} → {cl.members}")
                    if old[3][0] is not None and old[3] != (cl.taken_bar, cl.cls):
                        self._fail(EQ_FROZEN, f"{side.eq_name} {cl.id}: take {old[3]} → {(cl.taken_bar, cl.cls)}")
                    if len(cl.members) > len(old[2]) and levels is not None:
                        for mid in cl.members:
                            x = levels.get(mid)
                            snap = None if x is None else self.liq_snap.get(id(x))
                            if snap is not None and snap[0] != _facts(x):
                                self._fail(EQ_NO_REWRITE, f"{side.eq_name} {cl.id}: member {mid} facts changed on join")
                snap = (ident, cl.bound, tuple(cl.members), (cl.taken_bar, cl.cls), cl)
                if old is None or old[1:4] != snap[1:4]:
                    self.eq_snap[id(cl)] = snap
                if cl.taken_bar is not None and cl.taken_bar <= max(cl.bar, cl.last_bar or cl.bar):
                    self._fail(EQ_AFTER, f"{side.eq_name} {cl.id}: taken at {cl.taken_bar}, known at {cl.bar}/{cl.last_bar}")
                if levels is not None:
                    for mid in cl.members:
                        x = levels.get(mid)
                        if x is not None and not (0 <= sg * (cl.bound - x.price) <= self.tol + self.eps):
                            self._fail(EQ_TOL, f"{side.eq_name} {cl.id}: member {x.price} outside [{cl.bound} − tol, {cl.bound}]")
                if cl.bound != cl.ref:
                    self._fail(EQ_THEOREM, f"{side.eq_name} {cl.id}: boundary {cl.bound} != reference {cl.ref}")
                if not final and cl.active and bar > cl.bar and sg * (beyond_px - cl.bound) > 0:
                    self._fail(EQ_INTACT, f"{side.eq_name} {cl.id}: bar trades beyond {cl.bound} but the cluster is active")
                if (cl.qual_bar is not None) != (len(cl.members) >= lq.s.min_touch):
                    self._fail(EQ_QUAL, f"{side.eq_name} {cl.id}: {len(cl.members)} members, qualified at {cl.qual_bar}")
            if deep:
                for x in side.live:                       # a level points to the cluster that lists it
                    if x.eq is not None and x.id not in x.eq.members and any(x.eq is k for k in side.eqs):
                        self._fail(EQ_UNIQUE, f"{side.name} {x.id} points to {side.eq_name} {x.eq.id}, which does not list it")
        for e in new:
            if e.type in ("EQH_CREATED", "EQL_CREATED", "EQH_TAKEN", "EQL_TAKEN"):
                side = lq.bsl if e.dir > 0 else lq.ssl
                cl = next((k for k in side.eqs if k.id == e.sid), None)
                if cl is None:
                    continue                          # released on the same bar
                if cl.qual_bar is None:
                    self._fail(EQ_QUAL if e.type.endswith("CREATED") else EQ_EVENT, f"{e.type} for an unqualified cluster {cl.id}")
                if e.type.endswith("TAKEN") and (cl.taken_bar != bar or e.price != cl.bound):
                    self._fail(EQ_EVENT, f"{e.type} {cl.id} at {e.price} on bar {bar}; cluster says {cl.taken_bar} / {cl.bound}")
        for k in (EQ_UNIQUE, EQ_ID, EQ_BOUND, EQ_MEMBERS, EQ_AFTER, EQ_FROZEN, EQ_NO_REWRITE, EQ_TOL, EQ_THEOREM,
                  EQ_INTACT, EQ_QUAL, EQ_EVENT):
            stats.INV_CHECKS[k] += 1

    # ── sessions / levels ──
    def _sessions(self, bar, c, new):
        se = self.m.sessions
        cs = self.m.candles
        for s in [x for x in se.live if x is not None] + se.done[-len(se.live):]:
            if s.complete and s.known_time == c.time:
                rng = cs[s.start_bar:s.end_bar + 1]
                if s.end_bar != bar - 1 or s.hi != max(k.high for k in rng) or s.lo != min(k.low for k in rng):
                    self._fail(SES_RANGE, f"{s.name} {s.id}: H {s.hi} L {s.lo} end {s.end_bar} vs the bars inside")
        for e in new:
            if e.type == "SESSION_START":
                s = next(x for x in se.live if x is not None and x.id == e.sid)
                spec = dict(se.s.windows)[s.name]
                if bar == 0 or not in_window(c.time, spec, se.s.timezone) or in_window(cs[bar - 1].time, spec, se.s.timezone):
                    self._fail(SES_START, f"{s.name} started on bar {bar}, which is not the first bar inside")
        stats.INV_CHECKS[SES_RANGE] += 1
        stats.INV_CHECKS[SES_START] += 1

    def _levels(self, bar, new):
        lv = self.m.levels
        for e in new:
            if e.type == "LEVEL_SET":
                live = lv.live.get(e.sid)
                if e.price is None or live is None or live.price != e.price or live.known_time != self.m.candles[bar].time:
                    self._fail(LVL_SET, f"LEVEL_SET {e.meta} {e.price} does not match the live level")
        stats.INV_CHECKS[LVL_SET] += 1

    # ── LRL (docs/LRL.md) ──
    def _lrl(self, bar, new, full, final=False):
        e = self.m.lrl
        s = e.s
        evs = [x for x in new if x.type.startswith("LRL_")]
        for side in e.sides():
            recs = side.records()
            if len(recs) > s.memory or len(side.cands) > s.cand_memory:
                self._fail(LRL_MEM, f"{side.name}: {len(recs)} records / {len(side.cands)} candidates")
            if side.last_drop and side.last_drop["active"] and side.last_drop["ended_available"]:
                self._fail(LRL_MEM, f"{side.name}: an active record was dropped while an ended one existed")
            pts = [x for r in recs for x in r.xs]
            if len(pts) != len(set(pts)):
                self._fail(LRL_UNIQUE, f"{side.name}: a pivot is a point of two LRLs")
            mine = [x for x in evs if x.dir == side.sign]
            for x in mine:
                if x.type in LRL_TERMINAL:
                    if (side.sign, x.sid) in self.lrl_ended:
                        self._fail(LRL_TERM, f"{side.name} LRL {x.sid}: {x.type} after it had already ended")
                    self.lrl_ended.add((side.sign, x.sid))
            touched = {x.sid for x in mine}
            for r in (recs if full else [r for r in recs if r.end is None or r.id in touched]):
                self._lrl_record(e, side, r, bar)
            if not final:                         # this bar's events were compared by check()
                self._lrl_events(side, mine, recs, bar)
        stats.peak("lrl.records_per_side", max(len(side.records()) for side in e.sides()))
        for k in (LRL_UNIQUE, LRL_POINTS, LRL_LINE, LRL_CLEAN, LRL_TAKE, LRL_TIMING, LRL_FROZEN, LRL_EVENTS, LRL_MEM,
                  LRL_TERM):
            stats.INV_CHECKS[k] += 1

    def _lrl_record(self, e, side, r, bar):
        s, eps, hi = e.s, e.eps, side.hi
        tag = f"{side.name} LRL {r.id}"
        for i, x in enumerate(r.xs):
            if not (x >= s.left and hi[x] > max(hi[x - s.left:x]) and hi[x] >= max(hi[x + 1:x + s.right + 1])
                    and r.ps[i] == hi[x]):
                self._fail(LRL_POINTS, f"{tag}: point at bar {x} is not a DEF-LRL1 pivot at its price")
        for (xa, pa), (xb, pb) in zip(zip(r.xs, r.ps), zip(r.xs[1:], r.ps[1:])):
            tra = e.tra(xa)
            if not (0 < xb - xa <= s.gap and pb < pa - e.tol - eps) or (
                    s.sep_k and (tra is None or pb - min(side.lo[xa + 1:xb]) < s.sep_k * tra - eps)):
                self._fail(LRL_POINTS, f"{tag}: points {xa} → {xb} ({pa} → {pb}) are not a failure step")
        if len(r.xs) < 3 or r.tau != e.tau(r.xs[0]) or not r.ps[0] - r.ps[-1] > s.drop_k * r.tau + eps \
                or any(abs(p - r.y(x)) > r.tau + eps for x, p in zip(r.xs, r.ps)):
            self._fail(LRL_LINE, f"{tag}: {len(r.xs)} points, τ {r.tau} vs {e.tau(r.xs[0])}, off the chord or too flat")
        ended, active = r.end is not None, any(x is r for x in side.live)
        if (ended and f"LRL_{r.end}" not in LRL_TERMINAL) or {ended, r.end_bar is not None, r.end_level is not None,
                                                               not active} != {ended}:
            self._fail(LRL_TERM, f"{tag}: end {r.end!r} bar {r.end_bar} level {r.end_level}, active {active}")
        limit = r.xs[-1] + s.gap + s.right
        if r.born != r.xs[2] + s.right or r.ext != [x + s.right for x in r.xs[3:]] or (
                r.end is None and bar > limit) or (r.end == "EXPIRED" and r.end_bar != limit + 1) or (
                r.end is not None and r.end_bar <= r.last_decision):
            self._fail(LRL_TIMING, f"{tag}: born {r.born} ext {r.ext} end {r.end} at {r.end_bar}, points {r.xs}")
        last = bar if r.end is None else r.end_bar - (r.end != "EXPIRED")
        bad = next((j for j in range(r.xs[0] + 1, last + 1) if hi[j] > r.y(j) + r.tau + eps), None)
        if bad is not None:
            self._fail(LRL_CLEAN, f"{tag}: bar {bad} traded beyond line + τ ({hi[bad]} > {r.y(bad) + r.tau})")
        if r.end in ("DRIFT", "SWEEP", "BREAK"):
            k = r.end_bar
            lv, prev = r.y(k) + r.tau, r.y(k - 1) + r.tau
            kind = "DRIFT" if hi[k] <= prev + eps else "BREAK" if side.cl[k] > lv + eps else "SWEEP"
            if not hi[k] > lv + eps or r.end != kind or r.end_level != lv:
                self._fail(LRL_TAKE, f"{tag}: {r.end} on bar {k} (should be {kind}): high {hi[k]}, close {side.cl[k]}, "
                                     f"level {r.end_level} vs y + τ {lv}, previous boundary {prev}")
        now = (r.tau, r.born, tuple(r.xs), tuple(r.ps), tuple(r.ext), r.end, r.end_bar, r.end_level)
        old = self.lrl_snap.get((side.sign, r.id))
        if old is not None:
            n, k = len(old[2]), len(old[4])
            if old[:2] != now[:2] or now[2][:n] != old[2] or now[3][:n] != old[3] or now[4][:k] != old[4] or (
                    old[5] is not None and old[5:] != now[5:]):
                self._fail(LRL_FROZEN, f"{tag}: {old} → {now}")
        self.lrl_snap[(side.sign, r.id)] = now

    def _lrl_events(self, side, mine, recs, bar):
        g = side.sign
        gone = {x.sid for x in mine if x.type == "LRL_DROPPED_MEMORY"}
        got = sorted((x.type, x.sid, x.price, x.origin_bar) for x in mine if x.sid not in gone)
        want = []
        for r in recs:
            if r.born == bar:
                want.append(("LRL_CONFIRMED", r.id, g * r.ps[2], r.xs[0]))
            if bar in r.ext:
                want.append(("LRL_EXTENDED", r.id, g * r.ps[3 + r.ext.index(bar)], r.xs[0]))
            if r.end_bar == bar:
                want.append((f"LRL_{r.end}", r.id, g * r.end_level, r.xs[0]))
        if got != sorted(want) or gone & {r.id for r in recs}:
            self._fail(LRL_EVENTS, f"{side.name}: events {got} vs records {sorted(want)}, dropped {sorted(gone)}")


def run_checked(candles, settings=None, model=None, sweep_every: int = 1, **kw):
    """Run the reference model bar by bar with every invariant checked. Returns the model."""
    from validation.models.ist import IstModel
    m = model or IstModel(settings, **kw)
    mon = Monitor(m, sweep_every)
    for c in candles:
        m.step(c)
        mon.check()
    mon.final()
    stats.bump("bars.checked", len(candles))
    return m
