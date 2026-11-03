"""CONTEXT-01 research study: draw on liquidity (DOL) and directional context. Analysis only: no
indicator, oracle or frozen-module change (Phase 1, Phase 2, CISD, displacement, IFVG, LRL and HTF FVG
untouched). Specification: docs/context/ (awaiting the user's approval).

    python -m validation.studies.context

Two kinds of number are kept apart, as in every IST study:

* FEATURES_AT_T use bars <= t and Pine values known by the close of t only. `features` runs the
  oracle on the cut segment (candles[:t + 1], HTF bars known by t), so no later bar can reach a
  feature (tested by replacing the future).
* OUTCOME_AFTER_T use the bars after t. They label a hypothesis afterwards and never enter one.

The data is the real 1m evidence in the repository: four segments. Captures that share bars are
merged only where every shared bar is identical. PDH / PDL / PWH / PWL are TradingView's own values
as Pine received them: the completed D / W bars of the captures' HTF snapshot (HTFSTATE) and HTFBAR
lines, or LEVEL_SET for the NQ1! captures that predate the HTF module.

Everything is descriptive. Nothing here is a DOL rule, a weight or a score; the baselines B0…B4
(docs/context/DOL_RESEARCH.md §9) are defined, not tuned.
"""
from __future__ import annotations

import argparse
import statistics as st
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from validation.models.ist import IstModel
from validation.models.sessions import in_window, local
from validation.models.types import MODULES, NQ_TICK, Candle, SessionSettings, Settings
from validation.parity import CAPTURE_V043, CAPTURE_V044, CAPTURE_V070, CAPTURE_V071, CAPTURE_V080, CAPTURE_V091, capture
from validation.studies.cisd import NY
from validation.studies.lrl import resample

EPS = NQ_TICK * 0.01
TZ = "America/New_York"
H = 3_600_000
DUR = {"240": 4 * H, "D": 24 * H, "W": 168 * H}   # nominal, to the next bar's open (a break is inside it)
WARMUP = 200          # bars before a decision or an event: the DEF-CISD9 guard (the oracle has no Pine history)
ALL = MODULES + ("lrl", "cisd", "disp", "ifvg")
WINDOWS = SessionSettings().windows
EXTERNAL = ("W", "D", "S")                           # period extremes: external to their own period (§4)
RANK = {"W": 0, "D": 1, "S": 2, "EQ": 3, "SW": 4}   # B3: the higher timeframe first
TRA_LEN = 14


@dataclass
class Segment:
    name: str
    cs: list[Candle]
    htf: list[tuple[str, int, float, float, int]]    # completed TradingView bars: (tf, open, high, low, known ms)
    pdx: list[tuple[int, float, float]]              # LEVEL_SET PDH / PDL: (known ms, high, low)

    def cut(self, t: int) -> "Segment":
        """The segment as it was at the close of bar t."""
        k = self.cs[t].time
        return Segment(self.name, self.cs[:t + 1], [h for h in self.htf if h[4] <= k], [p for p in self.pdx if p[0] <= k])


@dataclass(frozen=True)
class Target:
    kind: str       # PDH, D-2 L, PWH, London H, BSL, EQL, …
    cls: str        # W · D · S (period extremes) · EQ · SW (chart-timeframe Phase 2 structure)
    side: int       # +1 above: reached when high > price · −1 below: reached when low < price (DEF-L4)
    price: float
    since: int      # ms: every trade from here on must be seen for the target to be AVAILABLE
    known: int      # ms: when it became known


def beyond(c: Candle, x: Target) -> bool:
    return c.high > x.price + EPS if x.side > 0 else c.low < x.price - EPS


# ── data ───────────────────────────────────────────────────────────────────────────────────────

def _segment(name: str, *paths) -> Segment:
    bars, htf, pdx = {}, {}, {}
    for p in paths:                                   # the earliest capture first
        cap = capture.parse(p.read_text(encoding="utf-8"))
        for b in cap["bars"]:
            if bars.setdefault(b["time"], b["candle"]) != b["candle"]:
                raise ValueError(f"{name}: the captures disagree at {b['time']}")
        at, first = {b["i"]: b["time"] for b in cap["bars"]}, cap["bars"][0]["time"]
        h = cap.get("htf") or {}
        rows = [(s["tf"], x, first) for s in h.get("HTFSTATE", []) for x in s["bars"]]
        rows += [(r["tf"], r["bar"], at[r["i"]]) for r in h.get("HTFBAR", []) if r["i"] in at]
        for tf, x, kn in rows:
            if tf in DUR:
                old = htf.setdefault((tf, x.time), (x.high, x.low, kn))
                if old[:2] != (x.high, x.low):
                    raise ValueError(f"{name}: the captures disagree on the {tf} bar {x.time}")
                htf[(tf, x.time)] = (x.high, x.low, min(old[2], kn))
        for e in cap["events"]:
            if e["type"] == "LEVEL_SET" and e["text"].endswith(("PDH", "PDL")):
                pdx.setdefault(e["time"], {})[e["text"][-3:]] = e["price"]
    cs = [bars[k] for k in sorted(bars)]
    return Segment(name, cs, sorted((tf, op, hi, lo, kn) for (tf, op), (hi, lo, kn) in htf.items()),
                   [(k, v["PDH"], v["PDL"]) for k, v in sorted(pdx.items())])


def segments() -> list[Segment]:
    """The real 1m evidence: four segments, never joined (no TR average crosses from one to another)."""
    return [_segment("NQ1! 2026-10-27 03:38 → 10-28 07:56", CAPTURE_V043, CAPTURE_V044),
            _segment("MNQZ2026 2026-10-29 19:56 → 10-30 15:43", CAPTURE_V080, CAPTURE_V070),
            _segment("MNQZ2026 2026-10-13 19:57 → 10-14 13:52 (Bar Replay)", CAPTURE_V071),
            _segment("MNQ1! 2026-11-02 04:16 → 23:11", CAPTURE_V091)]


# ── the target universe at the close of bar t (FEATURES) ─────────────────────────────────────

def covered(seg: Segment, x: "Target", t: int) -> bool:
    """Every trade from x.since to the close of bar t was seen, and stayed on the near side of x.
    Consecutive TradingView bars of one timeframe leave nothing out between them (a weekend or the
    daily break is no gap), so a run of them that never went beyond x proves its whole span; a bar that
    went beyond proves nothing about its part after `since`. The 1m bars cover the segment."""
    k, spans = seg.cs[t].time, [(seg.cs[0].time, seg.cs[t].time + 60_000)]
    for tf in DUR:
        run = None
        for _, op, hi, lo, _ in sorted(h for h in seg.htf if h[0] == tf and h[4] <= k):
            if hi > x.price + EPS if x.side > 0 else lo < x.price - EPS:
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
    return reach >= k + 60_000


def take(seg: Segment, x: Target) -> tuple[int, str] | None:
    """The first 1m bar at or after `since` that trades beyond x, and its DEF-L4 class at that close."""
    for j, c in enumerate(seg.cs):
        if c.time >= x.since and beyond(c, x):
            out = c.close > x.price + EPS if x.side > 0 else c.close < x.price - EPS
            return j, "BREAK" if out else "SWEEP"
    return None


def period_targets(seg: Segment, t: int) -> list[Target]:
    """PDH / PDL … from the completed D and W bars Pine knew at the close of t: the last three of each."""
    k, out = seg.cs[t].time, []
    for tf, cls, names in (("D", "D", ("PDH", "PDL", "D-2 H", "D-2 L", "D-3 H", "D-3 L")),
                           ("W", "W", ("PWH", "PWL", "W-2 H", "W-2 L", "W-3 H", "W-3 L"))):
        bars = sorted((h for h in seg.htf if h[0] == tf and h[4] <= k), key=lambda h: -h[1])[:3]
        for r, (_, op, hi, lo, kn) in enumerate(bars):
            out += [Target(names[2 * r], cls, 1, hi, op + DUR[tf], kn), Target(names[2 * r + 1], cls, -1, lo, op + DUR[tf], kn)]
    if not any(x.cls == "D" for x in out) and seg.pdx:     # the pre-HTF captures: LEVEL_SET only
        kn, hi, lo = [p for p in seg.pdx if p[0] <= k][-1] if any(p[0] <= k for p in seg.pdx) else (None, 0, 0)
        if kn is not None:
            out += [Target("PDH", "D", 1, hi, kn, kn), Target("PDL", "D", -1, lo, kn, kn)]
    return out


def session_targets(seg: Segment, m: IstModel, t: int) -> list[Target]:
    """The H / L of every session completed by the close of t (DEF-F4: final on the first bar outside)."""
    out = []
    for s in m.sessions.done + [x for x in m.sessions.live if x is not None]:
        if s.complete and s.end_bar + 1 <= t:
            kn = seg.cs[s.end_bar + 1].time
            out += [Target(f"{s.name} H", "S", 1, s.hi, kn, kn), Target(f"{s.name} L", "S", -1, s.lo, kn, kn)]
    return out


def status(seg: Segment, x: Target, t: int, took=False) -> tuple[str, str]:
    """(AVAILABLE | TAKEN | UNVERIFIED, SWEEP | BREAK | '?' | '') at the close of t.
    * TAKEN with a class: the first 1m bar beyond (DEF-L4, classed by its close), when everything from
      `since` up to that bar was seen and stayed inside;
    * TAKEN '?': beyond, but the first take may lie where nothing was seen (a completed TradingView bar
      after `since` went beyond before or across the segment start);
    * UNVERIFIED: not taken in what was seen, but part of [since, t] was not seen (before the loaded history).
    `took`: the precomputed take(seg, x), when the caller has it."""
    tk = take(seg, x) if took is False else took
    k, start = seg.cs[t].time, seg.cs[0].time
    seen = [(op, f) for f, op, hi, lo, kn in seg.htf
            if kn <= k and op >= x.since and (hi > x.price + EPS if x.side > 0 else lo < x.price - EPS)]
    if any(op + DUR[f] <= start for op, f in seen):
        return "TAKEN", "?"
    if tk and tk[0] <= t:
        sure = (x.since >= start or (tk[0] > 0 and covered(seg, x, tk[0] - 1))) and not any(op < start for op, _ in seen)
        return "TAKEN", tk[1] if sure else "?"
    if seen:
        return "TAKEN", "?"
    return ("AVAILABLE" if covered(seg, x, t) else "UNVERIFIED"), ""


def structure_targets(m: IstModel) -> list[Target]:
    """Active Phase 2 levels and qualified, untaken EQ pools (frozen DEF-L1…L5, read only)."""
    st_ = m.liq.state()
    out = [Target(r["side"], "SW", 1 if r["side"] == "BSL" else -1, r["price"], 0, 0)
           for r in st_["levels"] if r["status"] == "ACTIVE"]
    out += [Target(q["side"], "EQ", 1 if q["side"] == "EQH" else -1, q["bound"], 0, 0)
            for q in st_["clusters"] if q["qual_bar"] is not None and q["taken_bar"] is None]
    return out


def tra(cs: list[Candle], t: int) -> float:
    trs = [max(c.high - c.low, abs(c.high - p.close), abs(c.low - p.close)) for p, c in zip(cs[t - TRA_LEN:t], cs[t - TRA_LEN + 1:t + 1])]
    return sum(trs) / len(trs)


def cisd_timeline(cs: list[Candle], minutes: int) -> list[tuple[int, int]]:
    """(1m bar index at whose close it is known, side) of every CISD on `minutes` candles built from cs.
    A bucket is known at the close of its last minute, else at the first bar of the next bucket."""
    if minutes == 1:
        m = IstModel(Settings(modules=("cisd",))).run(cs)
        return [(e.bar, e.dir) for e in m.events if e.type == "CISD_CONFIRMED"]
    step = minutes * 60_000
    bucket = lambda c: c.time - c.time % step
    first_ = -(-cs[0].time // step) * step                     # a partial first bucket is left out
    at = {}
    for j in range(1, len(cs)):
        b = bucket(cs[j - 1])
        if bucket(cs[j]) != b:                                  # bar j starts a new bucket: b is complete
            at[b] = j - 1 if cs[j - 1].time == b + step - 60_000 else j
    if cs[-1].time == bucket(cs[-1]) + step - 60_000:
        at[bucket(cs[-1])] = len(cs) - 1
    hs = [h for h in resample([c for c in cs if c.time >= first_], minutes) if h.time in at]
    m = IstModel(Settings(modules=("cisd",))).run(hs)
    return [(at[hs[e.bar].time], e.dir) for e in m.events if e.type == "CISD_CONFIRMED"]


def state_at(tl: list[tuple[int, int]], t: int) -> int:
    s = 0
    for j, d in tl:
        if j > t:
            break
        s = d
    return s


def opens_at(seg: Segment, t: int) -> str | None:
    """The session window that opens on bar t + 1 (a decision point is the close before it)."""
    if t + 1 >= len(seg.cs):
        return None
    a, b = seg.cs[t].time, seg.cs[t + 1].time
    return next((n for n, w in WINDOWS if in_window(b, w, TZ) and not in_window(a, w, TZ)), None)


def features(seg: Segment, t: int) -> dict:
    """FEATURES_AT_T: everything here comes from the cut segment."""
    s = seg.cut(t)
    m = IstModel(Settings(modules=ALL)).run(s.cs)
    c = s.cs[t]
    ext = period_targets(s, t) + session_targets(s, m, t)
    rows = [(x, *status(s, x, t)) for x in ext] + [(x, "AVAILABLE", "") for x in structure_targets(m)]
    day = _day(c.time)
    pd = {x.kind: x.price for x in ext if x.kind in ("PDH", "PDL")}
    cis = m.state()["cisd"]["records"]
    dsp = m.state()["disp"]["records"]
    ifv = [r for r in m.state()["ifvg"] if r["status"] == "ACTIVE"]
    return {"t": t, "time": c.time, "open": opens_at(seg, t), "close": c.close, "tra": tra(s.cs, t), "rows": rows,
            "cisd": m.state()["cisd"]["state"], "cisd_age": t - max((r["bar"] for r in cis), default=-10**9),
            "cisd15": {1: "UP", -1: "DOWN", 0: "UNKNOWN"}[state_at(cisd_timeline(s.cs, 15), t)],
            "disp": (dsp[-1]["side"], t - dsp[-1]["bar"]) if dsp else None,
            "ifvg": (sum(r["side"] == "BULL" for r in ifv), sum(r["side"] == "BEAR" for r in ifv)),
            "pos": (c.close - pd["PDL"]) / (pd["PDH"] - pd["PDL"]) if len(pd) == 2 and pd["PDH"] > pd["PDL"] else None,
            "swept": [(x.kind, cl) for x, stt, cl in rows if stt == "TAKEN" and x.cls in EXTERNAL and cl != "?"
                      and _day(s.cs[take(s, x)[0]].time) == day]}


def _day(ms: int):
    d = local(ms, TZ) + timedelta(hours=6)          # the trading day starts 18:00 ET (DEF-G assumption)
    return d.date()


# ── outcomes (after t only) ────────────────────────────────────────────────────────────────────

def horizon(seg: Segment, t: int) -> int:
    """17:00 ET, the end of bar t + 1's trading day."""
    d = _day(seg.cs[t + 1].time)
    return int(datetime(d.year, d.month, d.day, 17, tzinfo=NY).timestamp() * 1000)


def first(seg: Segment, t: int, x: Target | None, end: int) -> int | None:
    if x is None:
        return None
    for j in range(t + 1, len(seg.cs)):
        if seg.cs[j].time >= end:
            return None
        if beyond(seg.cs[j], x):
            return j
    return None


def label(seg: Segment, t: int, x: Target, o: Target | None) -> tuple[str, int | None]:
    """The DOL_RESEARCH §10 label of 'x before o', and the bars until x was reached."""
    end = horizon(seg, t)
    a, b = first(seg, t, x, end), first(seg, t, o, end)
    if a is not None and (b is None or a < b):
        return "PRIMARY_REACHED", a - t
    if b is not None and (a is None or b < a):
        return "OPPOSITE_REACHED_FIRST", None
    if a is not None:
        return "BOTH_SAME_BAR_UNRESOLVED", a - t
    return ("CENSORED" if seg.cs[-1].time + 60_000 < end else "UNRESOLVED"), None


def null_p(price: float, x: Target, o: Target | None) -> float | None:
    """Driftless reference: P(x before o) = distance to o / (distance to x + distance to o)."""
    if o is None:
        return None
    a, b = abs(x.price - price), abs(o.price - price)
    return b / (a + b) if a + b else None


# ── baselines B0…B4 (defined, not tuned) ───────────────────────────────────────────────────────

def nearest(xs, side: int, p: float) -> Target | None:
    return min((x for x in xs if x.side == side), key=lambda x: (abs(x.price - p), x.kind), default=None)


def baselines(f: dict) -> dict[str, tuple[Target | None, Target | None]]:
    """name → (target, the falsifier: the nearest AVAILABLE external target on the other side, else the
    nearest AVAILABLE target of any class there). Ties go above."""
    p = f["close"]
    av = [x for x, s, _ in f["rows"] if s == "AVAILABLE"]
    ext = [x for x in av if x.cls in EXTERNAL]

    def opp(x):
        return None if x is None else nearest(ext, -x.side, p) or nearest(av, -x.side, p)

    def pick(xs):
        u, d = nearest(xs, 1, p), nearest(xs, -1, p)
        x = u if d is None or (u is not None and u.price - p <= p - d.price) else d
        return x, opp(x)

    top = min((RANK[x.cls] for x in av), default=None)
    both = nearest(ext, 1, p) is not None and nearest(ext, -1, p) is not None
    return {"B0 nearest external": pick(ext),
            "B1 nearest, any class": pick(av),
            "B2 nearer of PDH / PDL": pick([x for x in av if x.kind in ("PDH", "PDL")]),
            "B3 highest timeframe": pick([x for x in av if RANK[x.cls] == top]),
            "B4 abstain if external both sides": (None, None) if both else pick(ext)}


# ── tables ─────────────────────────────────────────────────────────────────────────────────────

def _t(ms: int) -> str:
    return local(ms, TZ).strftime("%m-%d %H:%M")


def _h(cs) -> float:
    return len(cs) / 60


def decisions(segs) -> list[tuple[int, dict]]:
    """Every session open with WARMUP bars of history before it: a fixed rule, not a choice of cases."""
    return [(i, features(seg, t)) for i, seg in enumerate(segs) for t in range(WARMUP, len(seg.cs) - 1)
            if opens_at(seg, t)]


def data_rows(segs) -> list[str]:
    rows = ["| segment | bars | hours | completed D · W bars from Pine | PDH / PDL source |", "|---|---|---|---|---|"]
    for s in segs:
        d = sum(h[0] == "D" for h in s.htf)
        w = sum(h[0] == "W" for h in s.htf)
        rows.append(f"| {s.name} | {len(s.cs)} | {_h(s.cs):.1f} | {d} · {w} | "
                    f"{'HTF snapshot (HTFSTATE / HTFBAR)' if d else 'LEVEL_SET at the ' + _t(s.pdx[0][0]) + ' roll only' if s.pdx else 'none'} |")
    return rows


def decision_rows(segs, dec) -> list[str]:
    rows = ["| # | segment · decision (ET) | opens | close | PDH · PDL (status) | pos in PD range | CISD 1m (age) · 15m | "
            "nearest external ▲ · ▼ (× TR avg) | nearest Phase 2 ▲ · ▼ (× TR avg) | external taken earlier today | "
            "first external reached after t |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for n, (i, f) in enumerate(dec, 1):
        seg, p, a = segs[i], f["close"], f["tra"]
        av = [x for x, s, _ in f["rows"] if s == "AVAILABLE"]
        ext = [x for x in av if x.cls in EXTERNAL]
        sw = [x for x in av if x.cls not in EXTERNAL]
        pd = "; ".join(f"{x.kind} {x.price:g} {s}{'·' + c if c else ''}" for x, s, c in f["rows"] if x.kind in ("PDH", "PDL")) or "—"
        fmt = lambda x: "—" if x is None else f"{x.kind} {abs(x.price - p) / a:.1f}"
        u, d = nearest(ext, 1, p), nearest(ext, -1, p)
        end = horizon(seg, f["t"])
        hits = sorted(((first(seg, f["t"], x, end), x) for x in (u, d) if x is not None), key=lambda h: h[0] or 10**9)
        hits = [(j, x) for j, x in hits if j is not None]
        reach = "none (censored)" if not hits and seg.cs[-1].time + 60_000 < end else "none" if not hits else \
            f"{hits[0][1].kind} ({'▲' if hits[0][1].side > 0 else '▼'}, +{hits[0][0] - f['t']} bars)" + \
            (" · then the other side too" if len(hits) == 2 else "")
        pos = "—" if f["pos"] is None else f"{f['pos']:.2f}"
        rows.append(f"| {n} | {seg.name.split(' ')[0]} {_t(f['time'])} | {f['open']} | {p:g} | {pd} | {pos} | "
                    f"{f['cisd']} ({f['cisd_age']}) · {f['cisd15']} | {fmt(u)} · {fmt(d)} | "
                    f"{fmt(nearest(sw, 1, p))} · {fmt(nearest(sw, -1, p))} | "
                    f"{', '.join(f'{k} {c}' for k, c in f['swept']) or '—'} | {reach} |")
    return rows


def census_rows(dec) -> list[str]:
    rows = ["| class | targets seen at the decision points | AVAILABLE | TAKEN | UNVERIFIED | nearest AVAILABLE, median × TR avg ▲ · ▼ |",
            "|---|---|---|---|---|---|"]
    for cl in ("W", "D", "S", "EQ", "SW"):
        xs = [(x, s, f) for _, f in dec for x, s, _ in f["rows"] if x.cls == cl]
        dist = {1: [], -1: []}
        for _, f in dec:
            av = [y for y, s, _ in f["rows"] if s == "AVAILABLE" and y.cls == cl]
            for side in dist:
                x = nearest(av, side, f["close"])
                if x:
                    dist[side].append(abs(x.price - f["close"]) / f["tra"])
        med = " · ".join(f"{st.median(v):.1f} (n={len(v)})" if v else "—" for v in dist.values())
        rows.append(f"| {cl} | {len(xs)} | {sum(s == 'AVAILABLE' for _, s, _ in xs)} | {sum(s == 'TAKEN' for _, s, _ in xs)} | "
                    f"{sum(s == 'UNVERIFIED' for _, s, _ in xs)} | {med} |")
    return rows


def baseline_rows(segs, dec) -> list[str]:
    labels = ("PRIMARY_REACHED", "OPPOSITE_REACHED_FIRST", "BOTH_SAME_BAR_UNRESOLVED", "UNRESOLVED", "CENSORED")
    rows = ["| baseline | decisions | abstain | " + " | ".join(labels) + " | resolved: reached first · driftless reference | "
            "bars to the target (median) |", "|---|" + "---|" * (len(labels) + 4)]
    for name in baselines(dec[0][1]):
        cnt, ref, bars, hit, res, ab = {k: 0 for k in labels}, 0.0, [], 0, 0, 0
        for i, f in dec:
            x, o = baselines(f)[name]
            if x is None:
                ab += 1
                continue
            lab, b = label(segs[i], f["t"], x, o)
            cnt[lab] += 1
            if b is not None:
                bars.append(b)
            q = null_p(f["close"], x, o)
            if lab in labels[:2] and q is not None:
                res, hit, ref = res + 1, hit + (lab == labels[0]), ref + q
        rows.append(f"| {name} | {len(dec)} | {ab} | " + " | ".join(str(cnt[k]) for k in labels) +
                    f" | {hit}/{res} · {ref:.1f} | {st.median(bars) if bars else '—'} |")
    return rows


FACTS = {"CISD_CONFIRMED": "CISD (1m)", "DISPLACEMENT_CONFIRMED": "displacement", "IFVG_INVERTED": "IFVG inversion",
         "BSL_SWEEP": "Phase 2 sweep", "SSL_SWEEP": "Phase 2 sweep", "BSL_BREAK": "Phase 2 break", "SSL_BREAK": "Phase 2 break",
         "LRL_SWEEP": "LRL sweep", "LRL_BREAK": "LRL break", "LRL_DRIFT": "LRL drift"}


def fact_events(segs) -> list[dict]:
    """Every fact at bar e >= WARMUP, with the nearest AVAILABLE external targets at e and which was
    reached first after e. External takes (the first 1m bar beyond a period extreme) are facts too."""
    out = []
    for i, seg in enumerate(segs):
        m = IstModel(Settings(modules=ALL)).run(seg.cs)
        c15 = cisd_timeline(seg.cs, 15)
        c1 = cisd_timeline(seg.cs, 1)
        items = {}
        for t in range(WARMUP, len(seg.cs) - 1):                          # every external target ever known
            for x in period_targets(seg, t) + session_targets(seg, m, t):
                items.setdefault(replace(x, kind=x.kind if x.cls == "S" else x.cls + str(x.since)), (x, take(seg, x)))
        evs = [(e.bar, FACTS[e.type], e.dir, "") for e in m.events if e.type in FACTS and e.bar >= WARMUP]
        evs += [(tk[0], f"external {tk[1].lower()}", x.side, f"{x.kind} {x.price:g}") for x, tk in items.values()
                if tk and tk[0] >= WARMUP and status(seg, x, tk[0] - 1, tk)[0] == "AVAILABLE"]
        for e, fact, d, what in sorted(evs, key=lambda v: (v[0], v[1], v[3])):
            if e + 1 >= len(seg.cs):
                continue
            av = [x for x in period_targets(seg, e) + session_targets(seg, m, e)
                  if status(seg, x, e, items.get(replace(x, kind=x.kind if x.cls == "S" else x.cls + str(x.since)), (None, None))[1])[0] == "AVAILABLE"]
            p = seg.cs[e].close
            u, dn = nearest(av, 1, p), nearest(av, -1, p)
            row = {"seg": i, "bar": e, "fact": fact, "side": d, "what": what, "close": p, "u": u, "d": dn,
                   "cisd1": state_at(c1, e), "cisd15": state_at(c15, e), "res": None}
            if u is not None and dn is not None:
                end = horizon(seg, e)
                a, b = first(seg, e, u, end), first(seg, e, dn, end)
                row["res"] = ("up" if a is not None and (b is None or a < b) else "down" if b is not None and (a is None or b < a)
                              else "same" if a is not None else "censored" if seg.cs[-1].time + 60_000 < end else "none")
                row["reach"] = a if row["res"] == "up" else b if row["res"] == "down" else None
                row["p_up"] = (p - dn.price) / (u.price - dn.price)
            out.append(row)
    return out


def split(rs) -> tuple[int, int, float, int]:
    """(resolved, first external reached on the event's side, driftless reference for it, distinct outcomes)."""
    res = [r for r in rs if r["res"] in ("up", "down")]
    hit = sum((r["res"] == "up") == (r["side"] > 0) for r in res)
    ref = sum(r["p_up"] if r["side"] > 0 else 1 - r["p_up"] for r in res)
    return len(res), hit, ref, len({(r["seg"], r["reach"], r["res"]) for r in res})


def fact_rows(evs) -> list[str]:
    rows = ["| fact (frozen event) | events | external targets both sides | resolved | first external reached on the event's "
            "side | driftless reference | distinct outcomes |", "|---|---|---|---|---|---|---|"]
    for fact in dict.fromkeys(r["fact"] for r in sorted(evs, key=lambda r: r["fact"])):
        rs = [r for r in evs if r["fact"] == fact]
        n, hit, ref, distinct = split(rs)
        rows.append(f"| {fact} | {len(rs)} | {sum(r['res'] is not None for r in rs)} | {n} | "
                    + (f"{hit} ({hit / n:.0%}) | {ref / n:.0%} | {distinct} |" if n else "— | — | — |"))
    return rows


def cisd_rows(segs) -> list[str]:
    rows = ["| segment | CISDs 1m (bars ≥ 200) | median bars between 1m CISDs | CISDs 15m | bars with 1m state = 15m state "
            "(both known) |", "|---|---|---|---|---|"]
    for seg in segs:
        c1 = [x for x in cisd_timeline(seg.cs, 1) if x[0] >= WARMUP]
        c15 = cisd_timeline(seg.cs, 15)
        gaps = [b[0] - a[0] for a, b in zip(c1, c1[1:])]
        tl1 = cisd_timeline(seg.cs, 1)
        both = [(state_at(tl1, t), state_at(c15, t)) for t in range(WARMUP, len(seg.cs))]
        both = [(a, b) for a, b in both if a and b]
        same = sum(a == b for a, b in both)
        rows.append(f"| {seg.name} | {len(c1)} | {st.median(gaps) if gaps else '—'} | {len(c15)} | "
                    f"{same}/{len(both)} ({same / len(both):.0%}) |" if both else
                    f"| {seg.name} | {len(c1)} | {st.median(gaps) if gaps else '—'} | {len(c15)} | — |")
    return rows


def category_rows(segs, dec, evs) -> list[str]:
    """The case categories of RESEARCH_CASES.md, by explicit rules on the rows above (labels after the fact)."""
    ex = lambda r: (f"{segs[r['seg']].name.split(' ')[0]} {_t(segs[r['seg']].cs[r['bar']].time)}"
                    f"{' ' + r['what'] if r['what'] else ''} ({'▲' if r['side'] > 0 else '▼'}) close {r['close']:g}: "
                    f"next ▲ {r['u'].kind} {r['u'].price:g} · ▼ {r['d'].kind} {r['d'].price:g} → {r['res']} first")
    sw = [r for r in evs if r["fact"] == "external sweep" and r["res"] in ("up", "down")]
    br = [r for r in evs if r["fact"] == "external break" and r["res"] in ("up", "down")]
    rev = lambda r: (r["res"] == "down") == (r["side"] > 0)
    cats = [("clear bearish delivery: an external target above swept, the nearest external below reached first",
             [r for r in sw if r["side"] > 0 and rev(r)]),
            ("clear bullish delivery: an external target below swept, the nearest external above reached first",
             [r for r in sw if r["side"] < 0 and rev(r)]),
            ("external sweep without reversal: the same side's next external target reached first", [r for r in sw if not rev(r)]),
            ("external break, continuation: the same side reached first", [r for r in br if not rev(r)]),
            ("external break, reversal: the other side reached first", [r for r in br if rev(r)]),
            ("displacement without continuation: the other side's external target reached first",
             [r for r in evs if r["fact"] == "displacement" and r["res"] in ("up", "down") and (r["res"] == "up") != (r["side"] > 0)]),
            ("IFVG conflict: the inversion's side is against the 1m CISD state at that bar",
             [r for r in evs if r["fact"] == "IFVG inversion" and r["cisd1"] and r["cisd1"] != r["side"] and r["res"] in ("up", "down")]),
            ("CISD conflict: a 1m CISD against the 15m CISD state", [r for r in evs if r["fact"] == "CISD (1m)" and r["cisd15"]
                                                                     and r["cisd15"] != r["side"] and r["res"] in ("up", "down")])]
    rows = []
    for k, (name, rs) in enumerate(cats):
        n, hit, ref, distinct = split(rs)
        tail = f"; resolved {n}: event side first {hit}, driftless reference {ref:.1f}" if k >= 6 and n else ""
        rows.append(f"* **{name}:** {len(rs)} event(s), {distinct} distinct outcome(s){tail}")
        rows += [f"  * {ex(r)}" for r in rs[:3]]
    mixed = [(i, f) for i, f in dec if _both_reached(segs[i], f)]
    rows.append(f"* **mixed (both sides' nearest external target reached in the horizon):** {len(mixed)} of {len(dec)} decision points")
    wrong = [(i, f) for i, f in dec if _b1_wrong(segs[i], f)]
    rows.append(f"* **wrong obvious heuristic (B1's side ≠ the side of the first external target reached):** {len(wrong)} of {len(dec)} decision points")
    rows += [f"  * {segs[i].name.split(' ')[0]} {_t(f['time'])}: B1 → {baselines(f)['B1 nearest, any class'][0].kind} "
             f"{baselines(f)['B1 nearest, any class'][0].price:g}" for i, f in wrong[:3]]
    return rows


def _ext_hits(seg, f):
    av = [x for x, s, _ in f["rows"] if s == "AVAILABLE" and x.cls in EXTERNAL]
    u, d = nearest(av, 1, f["close"]), nearest(av, -1, f["close"])
    end = horizon(seg, f["t"])
    return first(seg, f["t"], u, end), first(seg, f["t"], d, end)


def _both_reached(seg, f) -> bool:
    a, b = _ext_hits(seg, f)
    return a is not None and b is not None


def _b1_wrong(seg, f) -> bool:
    x = baselines(f)["B1 nearest, any class"][0]
    a, b = _ext_hits(seg, f)
    if x is None or (a is None and b is None) or a == b:
        return False
    up_first = b is None or (a is not None and a < b)
    return up_first != (x.side > 0)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m validation.studies.context")
    ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    segs = segments()
    dec = decisions(segs)
    evs = fact_events(segs)
    say = lambda *rows: print("\n".join(rows) + "\n")
    say("## Data\n", *data_rows(segs), f"* {sum(len(s.cs) for s in segs)} bars ≈ {sum(_h(s.cs) for s in segs):.1f} h; "
        f"{len(dec)} decision points (every session open with ≥ {WARMUP} bars before it)")
    say("## Target universe at the decision points\n", *census_rows(dec))
    say("## Decision points (FEATURES_AT_T · first OUTCOME)\n", *decision_rows(segs, dec))
    say("## Baselines B0…B4\n", *baseline_rows(segs, dec))
    say("## Facts → first external target reached (descriptive)\n", *fact_rows(evs))
    say("## CISD timescale\n", *cisd_rows(segs))
    say("## Case categories\n", *category_rows(segs, dec, evs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
