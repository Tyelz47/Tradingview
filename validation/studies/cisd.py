"""CISD research study: change in state of delivery. Analysis only: no indicator, oracle,
Phase 1 / Phase 2 / LRL / HTF FVG change. Specification: docs/STUDY_CISD.md (awaiting the
user's approval).

    python -m validation.studies.cisd [--svg DIR]

Everything is written once, for the BULLISH CISD, on side coordinates. The BEARISH CISD is the
same rule on the mirrored candle (open, close negated; high ↔ −low), so mirror symmetry holds
by construction. Every decision is taken at a bar's close, from bars ≤ t only.

Bullish CISD vocabulary (side coordinates; bearish = mirrored):
  opposing candle   close < open − EPS (a down-close candle); a doji is |close − open| ≤ EPS
  opposing run      a maximal sequence of consecutive opposing candles (a doji ends it, or is
                    skipped: Spec.doji)
  level L           the OPEN of the run's first candle (anchor "series") or of the last opposing
                    candle (anchor "last")
  confirmation      the first later bar whose close (Spec.confirm) is strictly beyond L
Context "none": the candidate is simply the newest opposing run (or candle).
Context "state" (state of delivery): one bit of state, bullish or bearish. A bullish CISD can
only occur while the state is not bullish; its candidate is the run that delivered price into
the LOWEST LOW of the current bearish leg. The bearish leg starts at the extreme of the bullish
leg before it (its highest high): while the state is bullish, the bullish side's window is
restarted at every new high, so the opposing delivery is always measured from the turn. A CISD
flips the state, so bullish and bearish CISDs alternate.
"""
from __future__ import annotations

import argparse
import math
import statistics as st
import sys
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from validation.candles import from_rows, random_walk
from validation.models.fvg import sma, true_range
from validation.models.types import NQ_TICK, Candle
from validation.studies.lrl import nq_candles, resample

EPS = NQ_TICK * 0.01         # the float margin of IST (Phase 1 / 2): prices on the tick grid
TRA_LEN = 14                 # TR average length (DEF-A2); used only by the displacement variant and the statistics
NY = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class Spec:
    name: str
    anchor: str = "series"   # series: open of the run's first candle · last: open of the last opposing candle
    context: str = "state"   # state: state of delivery (alternating) · none: the newest run, no state
    confirm: str = "close"   # wick · close · body (open and close beyond) · disp (close + body ≥ k × TR average)
    doji: str = "break"      # break: a doji ends a run · skip: a doji neither joins nor ends it
    ties: str = "latest"     # latest: an equal extreme moves the reference (≤) · first: only a new extreme (<)
    extreme: str = "delivery"  # delivery: only opposing candles set the leg extreme · any: every candle does
    newdir: bool = False     # True: the confirming candle must close in the new direction (up-close for a bullish CISD)
    disp_k: float = 1.0


@dataclass
class Cisd:
    side: int                # +1 bullish · −1 bearish
    level: float             # real price
    origin: int              # first candle of the opposing run: where the line starts
    anchor: int              # the candle whose open is the level
    ext_bar: int             # the delivery extreme that selected the reference (state context; = anchor otherwise)
    ext: float               # the leg extreme protected by the CISD: lowest low (bull) from the series start to the confirmation
    known: int               # bar at whose close this reference became the candidate
    bar: int                 # confirmation = decision bar
    body_k: float | None     # confirming candle body / TR average (information for a displacement layer)
    end: int | None = None   # opposite CISD (state) / next same-side CISD (none): the record ends there
    retest: int | None = None    # first later bar whose wick reaches the level
    reclaim: int | None = None   # first later bar that CLOSES back at or through the level
    broken: int | None = None    # first later bar that closes beyond the leg extreme


def view(c: Candle, s: int) -> tuple:
    """Side coordinates (o, h, l, c): +1 as is, −1 mirrored (open, close negated, high ↔ −low)."""
    return (c.open, c.high, c.low, c.close) if s > 0 else (-c.open, -c.low, -c.high, -c.close)


@dataclass
class _Side:
    s: int
    in_run: bool = False
    run_start: int | None = None
    run_of: list = field(default_factory=list)     # per bar: start of its opposing run (None: not opposing)
    last_opp: list = field(default_factory=list)   # per bar: newest opposing candle at or before it
    armed: bool = True
    arm: int = 0                     # first bar of the leg window (state context)
    since: int = 0                   # confirmation only on later bars (the flip bar)
    ext: float | None = None
    ext_bar: int | None = None
    ref: tuple | None = None         # (origin, anchor, level, known)
    used: int | None = None          # context none: anchor already confirmed
    cands: int = 0


def _tra(cs):
    tr = [true_range(c, cs[i - 1] if i else None) for i, c in enumerate(cs)]
    return lambda x: sma(tr, x, TRA_LEN) if x >= 0 else None


def run(cs, spec: Spec) -> tuple[list[Cisd], dict]:
    """Both sides, bar by bar. Returns the confirmed CISDs and counters."""
    tra = _tra(cs)
    v = {s: [view(c, s) for c in cs] for s in (1, -1)}
    sides = {s: _Side(s) for s in (1, -1)}
    recs, active, conc = [], [], []
    state = 0
    better = (lambda l, ext: ext is None or l <= ext + EPS) if spec.ties == "latest" else         (lambda l, ext: ext is None or l < ext - EPS)

    def ref_at(sd, e, t):
        """The opposing run that delivered price into bar e: the run of the newest opposing
        candle at or before e (inside the leg window). Known at the close of bar t."""
        j = sd.last_opp[e]
        if j is None or (spec.context == "state" and j < sd.arm):
            return None
        origin = sd.run_of[j]
        anchor = origin if spec.anchor == "series" else j
        return (origin, anchor, v[sd.s][anchor][0], t)

    def restart(sd, a, t):
        """The leg window of `sd` is [a, t]: its extreme and candidate are recomputed."""
        sd.arm, sd.ext, sd.ext_bar = a, None, None
        for j in range(a, t + 1):
            o, h, l, c = v[sd.s][j]
            if (c < o - EPS or spec.extreme == "any") and better(l, sd.ext):
                sd.ext, sd.ext_bar = v[sd.s][j][2], j
        sd.ref = ref_at(sd, sd.ext_bar, t) if sd.ext_bar is not None else None

    for t in range(len(cs)):
        # 1. lifecycle facts of the confirmed records (from the bar after their confirmation)
        for r in active:
            o, h, l, c = v[r.side][t]
            lv, ex = r.side * r.level, r.side * r.ext
            if r.retest is None and l <= lv + EPS:
                r.retest = t
            if r.reclaim is None and c <= lv + EPS:
                r.reclaim = t
            if r.broken is None and c < ex - EPS:
                r.broken = t
        # 2. runs, extremes, candidates
        for s, sd in sides.items():
            o, h, l, c = v[s][t]
            if c < o - EPS:
                if not sd.in_run:
                    sd.in_run, sd.run_start = True, t
                sd.run_of.append(sd.run_start)
                sd.last_opp.append(t)
            else:
                if not (abs(c - o) <= EPS and spec.doji == "skip"):
                    sd.in_run = False
                sd.run_of.append(None)
                sd.last_opp.append(sd.last_opp[-1] if t else None)
            if spec.context == "state":
                if (c < o - EPS or spec.extreme == "any") and better(l, sd.ext):
                    sd.ext, sd.ext_bar = l, t
                    new = ref_at(sd, t, t)
                    if sd.armed and new is not None and (sd.ref is None or new[1] != sd.ref[1]):
                        sd.cands += 1
                    sd.ref = new
            else:
                new = ref_at(sd, t, t)
                if new is not None and (sd.ref is None or new[1] != sd.ref[1]) and new[1] != sd.used:
                    sd.cands += 1
                sd.ref = None if new is None or new[1] == sd.used else new
        if spec.context == "state" and state != 0 and sides[-state].ext_bar == t:
            restart(sides[state], t, t)                       # the armed side's new extreme: the turn moved here
        conc.append(sum(sd.armed and sd.ref is not None for sd in sides.values()))
        # 3. confirmations
        hits = []
        for s, sd in sides.items():
            if not sd.armed or sd.ref is None or t <= sd.ref[1] or (spec.context == "state" and t <= sd.since):
                continue
            o, h, l, c = v[s][t]
            lv = sd.ref[2]
            ref_tra = tra(t - 1)
            ok = {"wick": h > lv + EPS, "close": c > lv + EPS, "body": min(o, c) > lv + EPS,
                  "disp": c > lv + EPS and ref_tra is not None and c - o >= spec.disp_k * ref_tra - EPS}[spec.confirm]
            if ok and (not spec.newdir or c > o + EPS):
                hits.append(s)
        if spec.context == "state" and len(hits) == 2:
            hits = []                                         # only before the first CISD: symmetric, no event
        for s in hits:
            sd = sides[s]
            o, h, l, c = v[s][t]
            ref_tra = tra(t - 1)
            ext_bar = sd.ext_bar if spec.context == "state" else sd.ref[1]
            ext = min(v[s][j][2] for j in range(sd.ref[0], t + 1))       # the leg extreme: series start → confirmation, wicks
            r = Cisd(s, s * sd.ref[2], sd.ref[0], sd.ref[1], ext_bar, s * ext, sd.ref[3], t,
                     (c - o) / ref_tra if ref_tra else None)
            for old in active:
                if (spec.context == "state" and old.side == -s) or (spec.context == "none" and old.side == s):
                    old.end = t
            active = [x for x in active if x.end is None]
            recs.append(r)
            active.append(r)
            if spec.context == "state":
                state = s
                op = sides[-s]
                restart(op, ext_bar, t)                       # the opposite leg runs from this leg's extreme
                restart(sd, op.ext_bar if op.ext_bar is not None else t, t)   # this side's next leg: from the opposite extreme
                sd.armed = False
                op.armed, op.since = True, t
                op.cands += op.ref is not None
            else:
                sd.used, sd.ref = sd.ref[1], None
    return recs, {"candidates": sum(sd.cands for sd in sides.values()), "confirmed": len(recs), "conc": conc}


def events(recs) -> list[tuple]:
    """(bar, event, side, level, origin) in bar order: the study's event stream."""
    out = []
    for r in recs:
        out.append((r.bar, "CISD_CONFIRMED", r.side, r.level, r.origin))
        if r.retest is not None and (r.end is None or r.retest <= r.end):
            out.append((r.retest, "CISD_RETEST", r.side, r.level, r.origin))
    return sorted(out, key=lambda e: (e[0], e[1], -e[2]))


# ── statistics (outcomes are measured, never part of a definition) ────────────────

def _hours(cs) -> float:
    return len(cs) * (cs[1].time - cs[0].time) / 3_600_000


def session(ms: int) -> str:
    ny = datetime.fromtimestamp(ms / 1000, NY)
    m = ny.hour * 60 + ny.minute
    for name, a, b in (("Asia", 20 * 60, 24 * 60), ("London", 2 * 60, 5 * 60), ("NY AM", 9 * 60 + 30, 12 * 60),
                       ("NY PM", 13 * 60 + 30, 16 * 60)):
        if a <= m < b:
            return name
    return "other"


def _wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p, z = k / n, 1.96
    d = 1 + z * z / n
    mid, half = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (mid - half, mid + half)


def follow_through(cs, recs, horizon=60) -> tuple[int, int]:
    """+1 TR average in the CISD's direction before −1 against, within `horizon` bars (a bar
    reaching both counts against). An outcome check only: (wins, decided)."""
    tra = _tra(cs)
    win = dec = 0
    for r in recs:
        R = tra(r.bar - 1)
        if not R:
            continue
        c0 = view(cs[r.bar], r.side)[3]
        for j in range(r.bar + 1, min(len(cs), r.bar + 1 + horizon)):
            o, h, l, c = view(cs[j], r.side)
            if l <= c0 - R:
                dec += 1
                break
            if h >= c0 + R:
                win += 1
                dec += 1
                break
    return win, dec


def measure(cs, recs, info) -> dict:
    hours, n = _hours(cs), len(recs)
    ended = [r for r in recs if r.end is not None]
    frac = lambda f: sum(f(r) for r in recs) / n if n else math.nan
    within = lambda b, r: b is not None and (r.end is None or b <= r.end)
    tra = _tra(cs)
    win, dec = follow_through(cs, recs)
    sess = {}
    for r in recs:
        sess[session(cs[r.bar].time)] = sess.get(session(cs[r.bar].time), 0) + 1
    return {
        "n": n, "bull": sum(r.side > 0 for r in recs), "per_hour": n / hours,
        "conv": n / info["candidates"] if info["candidates"] else math.nan,
        "conc_max": max(info["conc"]) if info["conc"] else 0, "conc_mean": st.mean(info["conc"]) if info["conc"] else 0,
        "life_med": st.median(r.end - r.bar for r in ended) if ended else None,
        "retest": frac(lambda r: within(r.retest, r)), "reclaim": frac(lambda r: within(r.reclaim, r)),
        "broken": frac(lambda r: within(r.broken, r)),
        "t_retest": st.median(r.retest - r.bar for r in recs if within(r.retest, r)) if any(within(r.retest, r) for r in recs) else None,
        "beyond_med": st.median(r.side * (cs[r.bar].close - r.level) / tra(r.bar - 1) for r in recs if tra(r.bar - 1))
        if any(tra(r.bar - 1) for r in recs) else None,
        "leg_med": st.median(r.bar - r.origin for r in recs) if recs else None,
        "leg_k": st.median(r.side * (r.level - r.ext) / tra(r.bar - 1) for r in recs if tra(r.bar - 1))
        if any(tra(r.bar - 1) for r in recs) else None,
        "quick": frac(lambda r: r.end is not None and r.end - r.bar <= 3),
        "follow": (win, dec), "sessions": sess,
    }


def table(cs, specs, label) -> list[str]:
    rows = [f"**{label}** ({len(cs)} bars ≈ {_hours(cs):.1f} h)", "",
            "| definition | CISDs (bull · bear) | per hour | candidates → confirmed | candidates alive (max · mean) | "
            "lifetime median (bars) | retest · close back · leg extreme broken | bars to retest (median) | "
            "close beyond L (median, × TR) | leg: L − extreme (median, × TR) | ended within 3 bars | "
            "follow-through ±1 TR (95 % CI) |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for spec in specs:
        recs, info = run(cs, spec)
        m = measure(cs, recs, info)
        w, d = m["follow"]
        lo, hi = _wilson(w, d)
        f = lambda x, p="{:.0%}": "—" if x is None or (isinstance(x, float) and math.isnan(x)) else p.format(x)
        rows.append(f"| {spec.name} | {m['n']} ({m['bull']} · {m['n'] - m['bull']}) | {m['per_hour']:.1f} | "
                    f"{info['candidates']} → {m['n']} ({f(m['conv'])}) | {m['conc_max']} · {m['conc_mean']:.2f} | "
                    f"{f(m['life_med'], '{:g}')} | {f(m['retest'])} · {f(m['reclaim'])} · {f(m['broken'])} | "
                    f"{f(m['t_retest'], '{:g}')} | {f(m['beyond_med'], '{:.2f}')} | {f(m['leg_k'], '{:.2f}')} | "
                    f"{f(m['quick'])} | "
                    f"{f(w / d if d else None)} of {d} ({f(lo)}–{f(hi)}) |")
    return rows


def sessions_row(cs, spec) -> str:
    recs, info = run(cs, spec)
    m = measure(cs, recs, info)
    hours = {}
    for c in cs:
        hours[session(c.time)] = hours.get(session(c.time), 0) + 1 / 60
    return " · ".join(f"{k} {m['sessions'].get(k, 0)} ({m['sessions'].get(k, 0) / hours[k]:.1f}/h)"
                      for k in ("Asia", "London", "NY AM", "NY PM", "other") if hours.get(k))


SPECS = [
    Spec("CISD-1 last opposing candle · no state", anchor="last", context="none"),
    Spec("CISD-2 series open · no state", anchor="series", context="none"),
    Spec("CISD-3 series open · state of delivery", anchor="series", context="state"),
    Spec("CISD-4 last opposing candle · state of delivery", anchor="last", context="state"),
    Spec("CISD-5 = CISD-3 + displacement (body ≥ 1 × TR avg)", confirm="disp"),
]
RECOMMENDED = replace(SPECS[2], name="CISD-R recommended: series open · state of delivery · close")
CONFIRMS = [replace(RECOMMENDED, name=f"CISD-3 · confirmation {n}", confirm=k)
            for n, k in (("A wick", "wick"), ("B close", "close"), ("C body", "body"), ("D close + displacement", "disp"))]
VARIANTS = [RECOMMENDED, replace(RECOMMENDED, name="CISD-3 · leg extreme set by any candle", extreme="any"),
            replace(RECOMMENDED, name="CISD-3 · confirming candle must close in the new direction", newdir=True),
            replace(RECOMMENDED, name="CISD-3 · doji skipped", doji="skip"),
            replace(RECOMMENDED, name="CISD-3 · equal extreme keeps the first", ties="first")]


# ── synthetic scenarios (bars as (open, high, low, close); expected results in tests) ──────────

_DOWN = [(100, 100, 100, 100), (100, 100.5, 98, 98.5), (98.5, 99, 96, 96.5), (96.5, 97, 95, 95.5)]   # run 1…3, L 100, low 95
# A bearish CISD first (bar 3, level 98): the scenarios that study behaviour INSIDE a bearish state start with it.
_BEAR_STATE = [(98, 98, 98, 98), (98, 99.25, 97.75, 99), (99, 100.25, 98.75, 100), (100, 100.25, 97.5, 97.75)]


def _rows(rows):
    return from_rows([tuple(float(x) for x in r) for r in rows])


def _warm(rows, n=16):
    """n quiet bars (TR 0.75) before the scenario: the TR average exists (displacement scenarios)."""
    base = rows[0][0]
    quiet = [(base, base + 0.5, base - 0.25, base) if i % 2 else (base, base + 0.25, base - 0.5, base) for i in range(n)]
    return _rows(quiet + rows)


SCENARIOS = {
    "1 clean bullish CISD": _rows(_DOWN + [(95.5, 98, 95.25, 97.5), (97.5, 100.75, 97.25, 100.5), (100.5, 102, 100.25, 101.75)]),
    "3 wick through only": _rows(_DOWN + [(95.5, 98, 95.25, 97.5), (97.5, 100.5, 97.25, 99.75), (99.75, 100, 99, 99.5)]),
    "4 close exactly at the level": _rows(_DOWN + [(95.5, 98, 95.25, 97.5), (97.5, 100.5, 97.25, 100), (100, 100, 99, 99.5)]),
    "5 close one tick beyond": _rows(_DOWN + [(95.5, 98, 95.25, 97.5), (97.5, 100.5, 97.25, 100.25), (100.25, 100.5, 99.75, 100)]),
    "6 false change (bounce below the level, then lower)": _rows(_BEAR_STATE + _DOWN[1:] + [
        (95.5, 97.25, 95.25, 97), (97, 98.75, 96.75, 98.5), (98.5, 98.75, 96, 96.25), (96.25, 96.5, 93.5, 94),
        (94, 94.25, 92.5, 92.75)]),
    "7 strong trend continuation (shallow pullbacks)": _rows(_DOWN + [
        (95.5, 98, 95.25, 97.5), (97.5, 100.75, 97.25, 100.5), (100.5, 101.25, 100.25, 101), (101, 102.25, 100.75, 102),
        (102, 102.25, 101.25, 101.5), (101.5, 103.25, 101.25, 103), (103, 104.25, 102.75, 104), (104, 104.25, 103.25, 103.5),
        (103.5, 105.25, 103.25, 105), (105, 106.25, 104.75, 106), (106, 106.25, 105.25, 105.5), (105.5, 107.25, 105.25, 107)]),
    "8 range / chop": _rows([(100, 100, 100, 100)] + [
        (100, 101, 99.5, 100.75) if i % 2 == 0 else (100.75, 101.25, 99.75, 100) for i in range(24)]),
    "9 immediate reversal (the extreme bar confirms)": _rows([
        (100, 100, 100, 100), (100, 100.25, 98, 98.25), (98.25, 98.5, 96, 96.25), (96.25, 100.75, 95, 100.5),
        (100.5, 101.5, 100.25, 101.25)]),
    "10 multiple candidates (the reference moves to the run into the new low)": _rows(_BEAR_STATE + _DOWN[1:] + [
        (95.5, 97.25, 95.25, 97), (97, 98.75, 96.75, 98.5), (98.5, 98.75, 96, 96.25), (96.25, 96.5, 94, 94.25),
        (94.25, 97, 94, 96.75), (96.75, 99.25, 96.5, 99), (99, 101, 98.75, 100.75)]),
    "11 confirmed CISD, then a retest": _rows(_DOWN + [
        (95.5, 98, 95.25, 97.5), (97.5, 100.75, 97.25, 100.5), (100.5, 101, 99.75, 100.75), (100.75, 102.25, 100.5, 102)]),
    "12 confirmed CISD, then invalidation": _rows(_DOWN + [
        (95.5, 98, 95.25, 97.5), (97.5, 100.75, 97.25, 100.5), (100.5, 100.75, 96.75, 97), (97, 97.25, 93.75, 94)]),
    "14 displacement present": _warm(_DOWN[1:] + [(95.5, 96.5, 95.25, 96.25), (96.25, 101.5, 96, 101.25),
                                                  (101.25, 102, 101, 101.75)]),
    "15 same structure without displacement": _warm(_DOWN[1:] + [(95.5, 96.5, 95.25, 96.25)] + [
        (96.25 + 0.25 * i, 96.75 + 0.25 * i, 96 + 0.25 * i, 96.5 + 0.25 * i) for i in range(16)]),
    "16 doji inside the series": _rows([(100, 100, 100, 100), (100, 100.25, 98, 98.25), (98.25, 98.75, 97.75, 98.25),
                                        (98.25, 98.5, 95, 95.25), (95.25, 97, 95, 96.75), (96.75, 98.75, 96.5, 98.5),
                                        (98.5, 100.5, 98.25, 100.25)]),
}


def scenario_rows(specs) -> list[str]:
    from validation.candles import mirror
    rows = ["| scenario | " + " | ".join(s.name.split(" ", 1)[0] + (" " + s.confirm if s.confirm != "close" else "")
                                       for s in specs) + " |", "|---|" + "---|" * len(specs)]
    cases = dict(SCENARIOS)
    cases["2 clean bearish CISD (mirror of 1)"] = mirror(SCENARIOS["1 clean bullish CISD"], 100.0)
    cases["13 mirror pair: 11 mirrored"] = mirror(SCENARIOS["11 confirmed CISD, then a retest"], 100.0)
    for name in sorted(cases, key=lambda k: int(k.split(" ")[0])):
        cells = []
        for spec in specs:
            evs = events(run(cases[name], spec)[0])
            cells.append(" ".join(f"{'▲' if s > 0 else '▼'}{'C' if e == 'CISD_CONFIRMED' else 'R'}@{b} {lv:g}"
                                  for b, e, s, lv, _ in evs) or "—")
        rows.append(f"| {name} | " + " | ".join(cells) + " |")
    return rows


# ── SVG chart (study renderer: also the visual proposal) ─────────────────────────

def svg(cs, recs, title, per_row=330) -> str:
    W, H, pad, top = 1500, 300, 50, 26
    rows = (len(cs) + per_row - 1) // per_row
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{rows * H + 30}" font-family="sans-serif" '
           f'font-size="11"><rect width="100%" height="100%" fill="#C2BAAE"/><text x="{pad}" y="18" font-size="14" '
           f'font-weight="bold" fill="#3a332c">{title}</text>']
    for k in range(rows):
        a, b = k * per_row, min(len(cs), (k + 1) * per_row)
        y0 = 30 + k * H
        lo, hi = min(c.low for c in cs[a:b]), max(c.high for c in cs[a:b])
        sx = lambda i: pad + (i - a + 0.5) * (W - 2 * pad) / per_row
        sy = lambda p: y0 + top + (hi - p) / (hi - lo) * (H - top - 20)
        out.append(f'<rect x="{pad}" y="{y0 + top - 4}" width="{W - 2 * pad}" height="{H - top - 12}" fill="none" '
                   f'stroke="#a89f92"/>')
        for i in range(a, b):
            ny = datetime.fromtimestamp(cs[i].time / 1000, NY)
            if ny.minute == 0 or i == a:
                out.append(f'<text x="{sx(i):.1f}" y="{y0 + H - 6}" fill="#5e564d">{ny:%d %H:%M}</text>')
            c = cs[i]
            col = "#f4f1ec" if c.close >= c.open else "#3a332c"
            out.append(f'<line x1="{sx(i):.1f}" x2="{sx(i):.1f}" y1="{sy(c.high):.1f}" y2="{sy(c.low):.1f}" stroke="{col}"/>')
        out.append(f'<text x="{W - pad + 4}" y="{y0 + top + 6}" fill="#5e564d">{hi:.2f}</text>'
                   f'<text x="{W - pad + 4}" y="{y0 + H - 22}" fill="#5e564d">{lo:.2f}</text>')
        for r in recs:
            if r.bar < a or r.bar >= b:
                continue
            x0 = max(a, r.origin)
            dy = 12 if r.side > 0 else -4
            out.append(f'<line x1="{sx(x0):.1f}" x2="{sx(r.bar):.1f}" y1="{sy(r.level):.1f}" y2="{sy(r.level):.1f}" '
                       f'stroke="#4F473F" stroke-width="1"/><text x="{sx(r.bar) + 2:.1f}" y="{sy(r.level) + dy:.1f}" '
                       f'fill="#4F473F" font-size="9">CISD</text>')
    return "\n".join(out + ["</svg>"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m validation.studies.cisd")
    ap.add_argument("--svg", type=Path, help="write the study charts into this folder")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cs = nq_candles()
    walk = random_walk(6000, 1, gap_prob=0.02)
    say = lambda *rows: print("\n".join(rows) + "\n")
    label = "NQ1! 1m, evidence captures merged, 2026-10-27 03:38 → 10-28 07:56 New York"
    say("## Candidate definitions (confirmation: close strictly beyond L)\n", *table(cs, SPECS, label), "",
        *table(walk, SPECS, "Random walk (no structure), seed 1"))
    say("## Confirmation rules on CISD-3\n", *table(cs, CONFIRMS, "NQ capture"), "", *table(walk, CONFIRMS, "Random walk"))
    say("## Doji and equal-extreme variants\n", *table(cs, VARIANTS, "NQ capture"))
    say("## Timeframes (NQ capture resampled)\n",
        *[row for m in (1, 3, 5, 15) for row in table(resample(cs, m), [RECOMMENDED], f"NQ {m}m") + [""]])
    say("## Sessions (CISD-R, NQ 1m)\n", sessions_row(cs, RECOMMENDED))
    say("## Synthetic scenarios (▲ bullish · ▼ bearish; C confirmed · R first retest; @ bar, then the level)\n",
        *scenario_rows(SPECS + CONFIRMS[0:1] + CONFIRMS[2:3]))
    if a.svg:
        a.svg.mkdir(parents=True, exist_ok=True)
        for tag, spec in (("R", RECOMMENDED), ("2", SPECS[1])):
            (a.svg / f"cisd-{tag}.svg").write_bytes(svg(cs, run(cs, spec)[0], f"{spec.name} · NQ1! 1m").encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
