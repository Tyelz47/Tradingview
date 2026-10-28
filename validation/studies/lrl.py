"""LRL research study: diagonal failure-swing liquidity. Analysis only: no indicator,
oracle or Phase 2 change. Specification: docs/STUDY_LRL.md (awaiting the user's review).

    python -m validation.studies.lrl [--svg DIR]

Everything is written once, for the BEARISH LRL: descending swing highs, buy stops above
the line. The BULLISH LRL (ascending swing lows) is the same algorithm on the mirrored
series (high ↔ −low, close ↔ −close), so mirror symmetry holds by construction.

Per bar t (Confirmed mode: every decision at a bar's close, from bars ≤ t only):
  1. advance every confirmed LRL and every 2-point candidate with the geometry in effect
     BEFORE this bar: a high strictly beyond line + τ takes it (candidates die silently),
     else it expires once no further point can arrive, else a high within τ is a touch;
  2. judge the DEF-L1 swing bar X = t − right; a new pivot, in this order, extends one
     confirmed LRL, else confirms one candidate (3rd point), else seeds new candidates.
So a record is never taken by the bar that confirmed or extended it, and a geometry
change applies from the bar after the change only.
"""
from __future__ import annotations

import argparse
import statistics as st
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

from validation.candles import random_walk
from validation.models.fvg import sma, true_range
from validation.models.ist import IstModel
from validation.models.types import NQ_TICK, Candle, Settings
from validation.parity import CAPTURE_V043, CAPTURE_V044, capture

EQ_TOL = 4 * NQ_TICK        # DEF-L5 tolerance (frozen Phase 2 default)
EPS = NQ_TICK * 0.01        # the float margin of Phase 2
TRA_LEN = 14                # TR average length of DEF-L2
CAND_MEMORY = 25            # 2-point candidates kept per side (oldest dropped)


@dataclass(frozen=True)
class Spec:
    """One candidate LRL definition. Every field changes calculation."""
    name: str
    geometry: str = "chord"   # fixed (first two points) · chord (first → latest) · fit (least squares) · local (last segment)
    tol: tuple = ("tr", 0.5)  # τ: ("ticks", n) · ("tr", c) = max(EQ tol, c × TR avg at the anchor) · ("range", c)
    gmax: int = 30            # max bars between consecutive points; a record lives until X_last + gmax + right
    left: int = 5             # pivot engine (DEF-L1 rule): Balanced 5 / 3 by default
    right: int = 3
    anchor: str = "any"       # first point: any pivot · "c1" = a frozen Phase 2 BSL / SSL
    points: str = "any"       # later points: any pivot · "c1"
    chain: bool = False       # control: consecutive lower pivots only, no line and no clean test
    ratio: float = 2.0        # local geometry: consecutive segment slopes within this factor
    drop: float = 2.0         # first − latest point > drop × τ: no horizontal line fits within τ (0 = off)
    reuse: bool = False       # True: pivots of a taken LRL may seed a new one (False: they are spent)
    sep: float = 0.0          # pullback between consecutive points ≥ sep × TR avg (separate swings; 0 = off)


@dataclass
class Lrl:
    side: str                 # "bear" (descending highs) · "bull" (ascending lows)
    pts: list                 # member pivots [(X, P)], P in side coordinates (lows negated)
    tau: float
    line: tuple               # (x, y, slope) of the geometry in effect
    born: int                 # confirmation bar (3rd point confirmed); -1 for a candidate
    geometry: str = "chord"
    ext: list = field(default_factory=list)   # bars where a 4th, 5th, … point joined
    touches: int = 0
    end: str | None = None    # SWEEP · BREAK · EXPIRED (None: active at the data end)
    end_bar: int | None = None

    def y(self, x: float) -> float:
        """Line level at bar x: the member polyline for local geometry inside the span,
        the geometry line everywhere else."""
        if self.geometry == "local" and x <= self.pts[-1][0]:
            for (xa, ya), (xb, yb) in zip(self.pts, self.pts[1:]):
                if x <= xb:
                    return ya + (yb - ya) * (x - xa) / (xb - xa)
        x0, y0, s = self.line
        return y0 + s * (x - x0)

    @property
    def anchor(self) -> tuple:
        return self.pts[0]

    def price(self, p: float) -> float:
        return p if self.side == "bear" else -p


def _series(cs, side):
    if side == "bear":
        return [c.high for c in cs], [c.low for c in cs], [c.close for c in cs]
    return [-c.low for c in cs], [-c.high for c in cs], [-c.close for c in cs]


def c1_origins(cs) -> dict:
    """Swing bars X that the FROZEN Phase 2 oracle (Balanced, C1) made BSL / SSL."""
    m = IstModel(Settings.from_dict({"liq": {"preset": "balanced"}, "modules": ["liq"]})).run(cs)
    return {"bear": {e.origin_bar for e in m.events if e.type == "BSL_CREATED"},
            "bull": {e.origin_bar for e in m.events if e.type == "SSL_CREATED"}}


def geometry(kind: str, pts) -> tuple:
    (xa, ya), (xb, yb) = pts[0], pts[1] if kind == "fixed" else pts[-1]
    if kind == "local":
        (xa, ya), (xb, yb) = pts[-2], pts[-1]
    if kind == "fit" and len(pts) > 2:
        n = len(pts)
        mx, my = sum(x for x, _ in pts) / n, sum(p for _, p in pts) / n
        s = sum((x - mx) * (p - my) for x, p in pts) / sum((x - mx) ** 2 for x, _ in pts)
        return mx, my, s
    return xa, ya, (yb - ya) / (xb - xa)


def run(cs, spec: Spec, side: str, c1: dict | None = None) -> tuple[list[Lrl], dict]:
    """All confirmed LRLs of one side, and the candidate counters."""
    hi, lo, cl = _series(cs, side)
    c1 = (c1 or {}).get(side, set())
    tr = [true_range(c, cs[i - 1] if i else None) for i, c in enumerate(cs)]
    piv, cands, out, members, spent = [], [], [], set(), set()
    n = {"candidates": 0, "crossed": 0, "expired": 0, "confirmed": 0}

    def tau_of(a, b):
        kind, c = spec.tol
        if kind == "ticks":
            return c * NQ_TICK
        if kind == "range":
            return max(EQ_TOL, c * (a[1] - min(lo[a[0]:b[0] + 1])))
        tra = sma(tr, a[0], TRA_LEN)
        return None if tra is None else max(EQ_TOL, c * tra)

    def fit(pts, tau, t):
        """Geometry of these points if they form a valid LRL at bar t, else None."""
        (xa, pa), (xb, pb) = pts[-2], pts[-1]
        if xb - xa > spec.gmax or not pb < pa - EQ_TOL - EPS:      # spacing; failure step beyond EQ
            return None
        if spec.chain:
            return geometry("chord", pts) if piv and pts[-2] == piv[-1] else None
        tra = sma(tr, xa, TRA_LEN)
        if spec.sep and (tra is None or pb - min(lo[xa + 1:xb]) < spec.sep * tra - EPS):   # separate swings
            return None
        if len(pts) > 2 and not pts[0][1] - pts[-1][1] > spec.drop * tau + EPS:   # diagonal, not EQ-flat
            return None
        g = geometry(spec.geometry, pts)
        probe = Lrl(side, pts, tau, g, -1, spec.geometry)
        if spec.geometry == "local":
            s = [(b[1] - a[1]) / (b[0] - a[0]) for a, b in zip(pts, pts[1:])]
            if any(not (1 / spec.ratio <= s2 / s1 <= spec.ratio) for s1, s2 in zip(s, s[1:])):
                return None
        elif any(abs(p - probe.y(x)) > tau + EPS for x, p in pts):
            return None
        if any(hi[j] > probe.y(j) + tau + EPS for j in range(pts[0][0] + 1, t + 1)):   # clean
            return None
        return g

    for t in range(len(cs)):
        for r in out:                                             # 1. advance confirmed records
            if r.end is not None or r.born >= t:
                continue
            lv = r.y(t)
            if hi[t] > lv + r.tau + EPS:
                r.end, r.end_bar = ("BREAK" if cl[t] > lv + r.tau + EPS else "SWEEP"), t
            elif t > r.pts[-1][0] + spec.gmax + spec.right:
                r.end, r.end_bar = "EXPIRED", t
            elif hi[t] >= lv - r.tau - EPS:
                r.touches += 1
            if r.end is not None:
                members.difference_update(x for x, _ in r.pts)
                if r.end != "EXPIRED" and not spec.reuse:
                    spent.update(x for x, _ in r.pts)
        keep = []
        for c in cands:                                           # 1. advance candidates
            if spent & {c.pts[0][0], c.pts[1][0]}:
                continue
            if hi[t] > c.y(t) + c.tau + EPS:
                n["crossed"] += 1
            elif t > c.pts[-1][0] + spec.gmax + spec.right:
                n["expired"] += 1
            else:
                keep.append(c)
        cands = keep
        X = t - spec.right                                        # 2. the swing bar
        if X - spec.left < 0 or not (hi[X] > max(hi[X - spec.left:X]) and hi[X] >= max(hi[X + 1:t + 1])):
            continue
        new, used = (X, hi[X]), False
        follower = spec.points != "c1" or X in c1
        if follower:
            for r in sorted((r for r in out if r.end is None), key=lambda r: r.anchor[0]):
                g = fit(r.pts + [new], r.tau, t)
                if g:
                    r.pts, r.line, used = r.pts + [new], g, True
                    r.ext.append(t)
                    members.add(X)
                    break
        if follower and not used:
            for c in sorted(cands, key=lambda c: (c.pts[0][0], c.pts[1][0])):
                g = fit(c.pts + [new], c.tau, t)
                if g:
                    r = Lrl(side, c.pts + [new], c.tau, g, t, spec.geometry)
                    out.append(r)
                    n["confirmed"] += 1
                    xs = {x for x, _ in r.pts}
                    members |= xs
                    cands = [d for d in cands if not xs & {d.pts[0][0], d.pts[1][0]}]
                    used = True
                    break
        if follower and not used:
            for a in (piv[-1:] if spec.chain else piv):
                if a[0] in members or a[0] in spent or X - a[0] > spec.gmax:
                    continue
                if spec.anchor == "c1" and not (a[0] in c1 and a[0] + 3 <= t):
                    continue
                tau = tau_of(a, new)
                g = None if tau is None else fit([a, new], tau, t)
                if g:
                    cands.append(Lrl(side, [a, new], tau, g, -1, spec.geometry))
                    n["candidates"] += 1
            cands = cands[-CAND_MEMORY:]
        piv = [p for p in piv if X - p[0] <= spec.gmax] + [new]
    return out, n


# ── candidate definitions ──────────────────────────────────────────────────────

SPECS = [
    Spec("LRL-0 control: 3 consecutive lower pivots", chain=True),
    Spec("LRL-1 fixed line (first two points)", geometry="fixed"),
    Spec("LRL-2 chord (first → latest point)", geometry="chord"),
    Spec("LRL-3 least-squares fit", geometry="fit"),
    Spec("LRL-4 local slope (curved staircase)", geometry="local"),
    Spec("LRL-5 structural: chord, anchor = C1 BSL/SSL", geometry="chord", anchor="c1"),
]
# The study's recommendation (docs/STUDY_LRL.md §G): LRL-2 geometry on an intermediate
# 3 / 2 pivot engine, consecutive points separated by a k × TR pullback (Balanced k = 1).
RECOMMENDED = Spec("LRL-R recommended: chord · pivots 3/2 · separate swings", left=3, right=2, sep=1.0)
SPECS.append(RECOMMENDED)
SOURCES = [
    Spec("all DEF-L1 pivots 5/3 (any significance)"),
    Spec("C1 significant only (BSL/SSL)", anchor="c1", points="c1"),
    Spec("small engine 3/2", left=3, right=2),
    Spec("small engine 2/2", left=2, right=2),
    Spec("hybrid: C1 anchor + any 5/3 pivots", anchor="c1"),
]
ABLATIONS = [
    Spec("LRL-2 as specified (drop > 2τ, taken pivots spent)"),
    Spec("LRL-2 without the non-horizontal rule (drop 0)", drop=0),
    Spec("LRL-2 with pivots reused after a take", reuse=True),
    Spec("LRL-2 without both", drop=0, reuse=True),
]


def nq_candles() -> list:
    """Both evidence captures merged by bar time (their 411 shared bars are identical)."""
    bars = {}
    for path in (CAPTURE_V043, CAPTURE_V044):
        for b in capture.parse(path.read_text(encoding="utf-8"))["bars"]:
            c = b["candle"]
            if bars.setdefault(c.time, c) != c:
                raise ValueError(f"the captures disagree at {c.time}")
    return [bars[k] for k in sorted(bars)]


def resample(cs, minutes: int) -> list[Candle]:
    """1m candles → `minutes` candles (buckets of the bar time, like a chart timeframe)."""
    out = []
    for c in cs:
        k = c.time - c.time % (minutes * 60_000)
        if out and out[-1].time == k:
            p = out[-1]
            out[-1] = Candle(k, p.open, max(p.high, c.high), min(p.low, c.low), c.close)
        else:
            out.append(Candle(k, c.open, c.high, c.low, c.close))
    return out


def both(cs, spec, c1=None) -> list[Lrl]:
    c1 = c1 if c1 is not None else (c1_origins(cs) if "c1" in (spec.anchor, spec.points) else {})
    return [r for side in ("bear", "bull") for r in run(cs, spec, side, c1)[0]]


def events(recs) -> list[tuple]:
    """(bar, event, side, anchor bar, points) of every record, in bar order (the study's
    event stream: LRL_CONFIRMED, LRL_EXTENDED, LRL_SWEEP / LRL_BREAK / LRL_EXPIRED)."""
    out = []
    for r in recs:
        out.append((r.born, "LRL_CONFIRMED", r.side, r.anchor[0], 3))
        out += [(b, "LRL_EXTENDED", r.side, r.anchor[0], 4 + i) for i, b in enumerate(r.ext)]
        if r.end:
            out.append((r.end_bar, f"LRL_{r.end}", r.side, r.anchor[0], len(r.pts)))
    return sorted(out)


def _tra(cs):
    tr = [true_range(c, cs[i - 1] if i else None) for i, c in enumerate(cs)]
    return lambda x: sma(tr, x, TRA_LEN)


def _hours(cs) -> float:
    return len(cs) * (cs[1].time - cs[0].time) / 3_600_000


def measure(cs, recs) -> dict:
    """Clutter and OUTCOMES of confirmed LRLs (outcomes never enter a definition)."""
    hours, tra = _hours(cs), _tra(cs)
    act = {s: [0] * len(cs) for s in ("bear", "bull")}
    take, run_ok, drift = [], 0, 0
    for r in recs:
        stop = r.end_bar if r.end_bar is not None else len(cs)
        for t in range(r.born, stop):
            act[r.side][t] += 1
        if r.end in ("SWEEP", "BREAK"):
            take.append(r.end_bar - r.born)
            hi = _series(cs, r.side)[0]
            run_ok += any(hi[j] > r.anchor[1] for j in range(r.end_bar, min(len(cs), r.end_bar + 60)))
            drift += hi[r.end_bar] <= r.pts[-1][1]          # the line fell into price below the last point
    conc = [v for s in act.values() for v in s]
    npts = [len(r.pts) for r in recs]
    return {
        "n": len(recs), "bear": sum(r.side == "bear" for r in recs), "per_hour": len(recs) / hours,
        "pts": (npts.count(3), npts.count(4), sum(k >= 5 for k in npts)),
        "end": tuple(sum(r.end == e for r in recs) for e in ("SWEEP", "BREAK", "EXPIRED", None)),
        "take_med": st.median(take) if take else None, "run": run_ok / len(take) if take else None,
        "drift": drift / len(take) if take else None,
        "conc_max": max(conc) if conc else 0, "conc_mean": st.mean(conc) if conc else 0,
        "span_med": st.median(r.pts[-1][0] - r.anchor[0] for r in recs) if recs else None,
        "slope_med": st.median(abs(r.line[2]) / tra(r.anchor[0]) for r in recs if tra(r.anchor[0])) if recs else None,
    }


def table(cs, specs, label, c1=None) -> list[str]:
    rows = [f"**{label}** ({len(cs)} bars ≈ {_hours(cs):.1f} h)", "",
            "| definition | LRLs (bear · bull) | per hour | points 3 · 4 · 5+ | sweep · break · expired · open | "
            "bars to take (median) | takes below the last point | ran to anchor ≤ 60 bars after take | "
            "concurrent per side (mean · max) | span bars (median) | slope TR/bar (median) |", "|---" * 11 + "|"]
    f = lambda v, fmt="{:.0f}": "—" if v is None else fmt.format(v)
    for spec in specs:
        m = measure(cs, both(cs, spec, c1))
        rows.append(f"| {spec.name} | {m['n']} ({m['bear']} · {m['n'] - m['bear']}) | {m['per_hour']:.2f} | "
                    f"{' · '.join(map(str, m['pts']))} | {' · '.join(map(str, m['end']))} | {f(m['take_med'])} | "
                    f"{f(m['drift'], '{:.0%}')} | {f(m['run'], '{:.0%}')} | {m['conc_mean']:.2f} · {m['conc_max']} | "
                    f"{f(m['span_med'])} | {f(m['slope_med'], '{:.2f}')} |")
    return rows


def grid(cs, label, base: Spec, c1=None) -> list[str]:
    """LRLs per hour for τ × spacing, one definition."""
    tols = (("ticks", 4), ("tr", 0.25), ("tr", 0.5), ("tr", 1.0), ("range", 0.1))
    rows = [f"{label}: {base.name}, LRLs per hour (bear + bull)", "",
            "| gmax \\ τ | " + " | ".join(f"{k} {c:g}" for k, c in tols) + " |", "|---" * (len(tols) + 1) + "|"]
    for g in (15, 30, 60):
        cells = [f"{len(both(cs, replace(base, tol=tol, gmax=g), c1)) / _hours(cs):.2f}" for tol in tols]
        rows.append(f"| {g} | " + " | ".join(cells) + " |")
    return rows


def follower_significance(cs, spec, c1) -> str:
    """How many points 2…n of LRLs are frozen C1 levels (the dominance test rejects lower highs)."""
    recs = both(cs, spec, c1)
    later = [(r.side, x) for r in recs for x, _ in r.pts[1:]]
    first = [(r.side, r.anchor[0]) for r in recs]
    return (f"anchors that are C1 levels: {sum(x in c1[s] for s, x in first)} / {len(first)} · "
            f"points 2…n that are C1 levels: {sum(x in c1[s] for s, x in later)} / {len(later)}")


# ── synthetic scenarios ────────────────────────────────────────────────────────

def zigzag(vertices, base=100.0, warm=40, tail=40, extra=()) -> list[Candle]:
    """`warm` flat bars at `base` (no pivots, TR warm-up), then straight moves through the
    (bar, price) vertices, then `extra` explicit (o, h, l, c) rows, then `tail` flat bars.
    Path bars: open = close = path, high / low = path ± 0.5."""
    mids = [base] * warm
    for (xa, ya), (xb, yb) in zip([(warm - 1, base)] + list(vertices), vertices):
        mids += [ya + (yb - ya) * (x - xa) / (xb - xa) for x in range(xa + 1, xb + 1)]
    rows = [(m, m + 0.5, m - 0.5, m) for m in mids] + list(extra)
    rows += [(rows[-1][3], rows[-1][3] + 0.5, rows[-1][3] - 0.5, rows[-1][3])] * tail
    return [Candle(i * 60_000, *map(float, r)) for i, r in enumerate(rows)]


_BEAR = [(50, 120), (58, 108), (66, 116), (74, 104), (82, 112)]       # highs 120.5 · 116.5 · 112.5 on one line
SCENARIOS = {
    "clean bearish LRL": zigzag(_BEAR + [(100, 95)]),
    "two failure swings only (internal candidate)": zigzag(_BEAR[:4] + [(100, 95)]),
    "4th and 5th point extension": zigzag(_BEAR + [(90, 100), (98, 108), (106, 96), (114, 104), (130, 90)]),
    "line touch → extension": zigzag(_BEAR + [(90, 100), (98, 107.5), (120, 92)]),
    "sweep (wick through, close back)": zigzag(_BEAR + [(92, 100)], extra=[(100, 112, 99.5, 101.5)]),
    "break (close beyond)": zigzag(_BEAR + [(92, 100)], extra=[(100, 112, 99.5, 111.5)]),
    "pivot beyond the line": zigzag(_BEAR + [(90, 100), (98, 113), (120, 92)]),
    "false candidate: 3rd high below the line": zigzag(_BEAR[:4] + [(82, 108), (100, 95)]),
    "false candidate: 3rd high above the line": zigzag(_BEAR[:4] + [(82, 115.5), (100, 95)]),
    "equal highs, then a staircase": zigzag([(50, 120), (58, 108), (66, 120), (74, 104), (82, 116), (90, 100),
                                             (98, 112), (116, 95)]),
    "range: equal-ish highs (steps ≤ EQ tolerance)": zigzag([(50, 110), (56, 104), (62, 109.5), (68, 104), (74, 110.25), (80, 103.5),
                                             (86, 109), (92, 104), (98, 108.75), (110, 100)]),
    "strong trend, collinear highs": zigzag([(50, 140), (56, 122), (62, 128), (68, 110), (74, 116), (90, 85)]),
    "strong trend, accelerating highs": zigzag([(50, 140), (56, 126), (62, 132), (68, 108), (74, 116), (90, 85)]),
    "micro-pivots (collinear, 0.75-point pullbacks)": zigzag([(50, 120), (52, 117.75), (55, 118.5), (57, 116.25),
                                                              (60, 117), (62, 114.75), (65, 115.5), (80, 100)]),
    "shallow staircase (drop ≤ 2τ)": zigzag([(50, 140), (58, 125), (66, 138.75), (74, 125), (82, 137.5), (100, 120)]),
    "points too far apart": zigzag([(50, 120), (70, 104), (86, 116), (110, 100), (122, 112), (140, 95)]),
    "triangle: bearish and bullish together": zigzag([(50, 120), (58, 100), (66, 116), (74, 103), (82, 112),
                                                      (90, 106), (96, 109)]),
}


def scenario_rows(specs) -> list[str]:
    rows = ["| scenario | " + " | ".join(s.name.split(" ")[0] for s in specs) + " |", "|---" * (len(specs) + 1) + "|"]
    short = {"LRL_CONFIRMED": "C", "LRL_EXTENDED": "X", "LRL_SWEEP": "S", "LRL_BREAK": "B", "LRL_EXPIRED": "E"}
    for name, cs in SCENARIOS.items():
        c1 = c1_origins(cs)
        cells = []
        for spec in specs:
            ev = events(both(cs, spec, c1))
            cells.append(" ".join(f"{'▼' if s == 'bear' else '▲'}{short[k]}{n if k == 'LRL_EXTENDED' else ''}@{b}"
                                  for b, k, s, _, n in ev) or "—")
        rows.append(f"| {name} | " + " | ".join(cells) + " |")
    return rows


# ── SVG chart (study renderer: also the visual proposal of DEF-LRL-R) ──────────

def svg(cs, recs, title, per_row=330) -> str:
    W, H, pad, top = 1500, 300, 50, 26
    rows = (len(cs) + per_row - 1) // per_row
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{rows * H + 30}" font-family="sans-serif" '
           f'font-size="11"><rect width="100%" height="100%" fill="#fff"/><text x="{pad}" y="18" font-size="14" '
           f'font-weight="bold">{title}</text>']
    from datetime import datetime
    from zoneinfo import ZoneInfo
    for k in range(rows):
        a, b = k * per_row, min(len(cs), (k + 1) * per_row)
        y0 = 30 + k * H
        lo, hi = min(c.low for c in cs[a:b]), max(c.high for c in cs[a:b])
        sx = lambda i: pad + (i - a + 0.5) * (W - 2 * pad) / per_row
        sy = lambda p: y0 + top + (hi - p) / (hi - lo) * (H - top - 20)
        out.append(f'<clipPath id="c{k}"><rect x="{pad}" y="{y0 + top - 4}" width="{W - 2 * pad}" '
                   f'height="{H - top - 12}"/></clipPath><rect x="{pad}" y="{y0 + top - 4}" width="{W - 2 * pad}" '
                   f'height="{H - top - 12}" fill="none" stroke="#ddd"/>')
        for i in range(a, b):
            ny = datetime.fromtimestamp(cs[i].time / 1000, ZoneInfo("America/New_York"))
            if ny.minute == 0 or i == a:
                out.append(f'<text x="{sx(i):.1f}" y="{y0 + H - 6}" fill="#888">{ny:%d %H:%M}</text>')
            c = cs[i]
            col = "#9aa5b1" if c.close >= c.open else "#55606e"
            out.append(f'<line x1="{sx(i):.1f}" x2="{sx(i):.1f}" y1="{sy(c.high):.1f}" y2="{sy(c.low):.1f}" stroke="{col}"/>')
        out.append(f'<text x="{W - pad + 4}" y="{y0 + top + 6}" fill="#888">{hi:.2f}</text>'
                   f'<text x="{W - pad + 4}" y="{y0 + H - 22}" fill="#888">{lo:.2f}</text><g clip-path="url(#c{k})">')
        for r in recs:
            stop = r.end_bar if r.end_bar is not None else len(cs) - 1
            if r.pts[0][0] >= b or stop < a:
                continue
            col = "#d6336c" if r.side == "bear" else "#1c7ed6"
            pl = " ".join(f"{sx(x):.1f},{sy(r.price(p)):.1f}" for x, p in r.pts)
            xl = r.pts[-1][0]
            out.append(f'<polyline points="{pl}" fill="none" stroke="{col}" stroke-width="1.6"/>'
                       f'<line x1="{sx(xl):.1f}" y1="{sy(r.price(r.y(xl))):.1f}" x2="{sx(stop):.1f}" '
                       f'y2="{sy(r.price(r.y(stop))):.1f}" stroke="{col}" stroke-width="1.2" stroke-dasharray="4 3"/>')
            out += [f'<circle cx="{sx(x):.1f}" cy="{sy(r.price(p)):.1f}" r="2.2" fill="{col}"/>' for x, p in r.pts]
            out.append(f'<circle cx="{sx(r.born):.1f}" cy="{sy(r.price(r.y(r.born))):.1f}" r="3" fill="#fff" stroke="{col}"/>')
            dy = -6 if r.side == "bear" else 14
            out.append(f'<text x="{sx(xl) + 3:.1f}" y="{sy(r.price(r.pts[-1][1])) + dy:.1f}" fill="{col}" '
                       f'font-size="10">LRL</text>')
            if r.end in ("SWEEP", "BREAK"):
                out.append(f'<text x="{sx(stop) - 3:.1f}" y="{sy(r.price(r.y(stop))) + (dy - 2 if r.side == "bear" else dy):.1f}" '
                           f'fill="{col}" font-size="10" font-weight="bold">{r.end[0]}</text>')
        out.append("</g>")
    return "\n".join(out + ["</svg>"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m validation.studies.lrl")
    ap.add_argument("--svg", type=Path, help="write one chart per candidate definition into this folder")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cs = nq_candles()
    c1 = c1_origins(cs)
    walk = random_walk(6000, 1, gap_prob=0.02)
    say = lambda *rows: print("\n".join(rows) + "\n")
    say("## Candidate definitions (LRL-0…5: pivots 5/3; all: τ = max(EQ tol, 0.5 × TR average), gmax 30)\n",
        *table(cs, SPECS, "NQ1! 1m, evidence captures merged, 2026-10-27 03:38 → 10-28 07:56 New York", c1), "",
        *table(walk, SPECS, "Random walk (no structure), seed 1"))
    say("## Swing source (geometry: chord)\n", *table(cs, SOURCES, "NQ capture", c1), "",
        "LRL-2: " + follower_significance(cs, SPECS[2], c1),
        "LRL-R: " + follower_significance(cs, RECOMMENDED, c1))
    say("## Ablations (5/3 pivots)\n", *table(cs, ABLATIONS, "NQ capture", c1))
    say("## Tolerance × spacing\n", *grid(cs, "NQ capture", RECOMMENDED, c1), "", *grid(cs, "NQ capture", SPECS[2], c1),
        "", *grid(cs, "NQ capture", SPECS[1], c1), "", *grid(walk, "Random walk", RECOMMENDED))
    say("## Timeframes (NQ capture resampled; bars, TR and τ are those of the timeframe)\n",
        *[row for m in (1, 3, 5) for row in table(resample(cs, m), [RECOMMENDED], f"NQ {m}m") + [""]])
    say("Candidate funnel (NQ, LRL-R): " + ", ".join(
        f"{side} {run(cs, RECOMMENDED, side, c1)[1]}" for side in ("bear", "bull")))
    say("## Synthetic scenarios (▼ bearish · ▲ bullish; C confirmed · Xn n-th point · S sweep · B break · "
        "E expired; @ bar)\n", *scenario_rows(SPECS))
    if a.svg:
        a.svg.mkdir(parents=True, exist_ok=True)
        for i, spec in [(0, SPECS[0]), (2, SPECS[2]), ("R", RECOMMENDED)]:
            (a.svg / f"lrl-{i}.svg").write_bytes(svg(cs, both(cs, spec, c1), f"{spec.name} · NQ1! 1m").encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
