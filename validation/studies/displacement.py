"""Displacement research study. Analysis only: no indicator, CISD, LRL, HTF FVG, Phase 1 or
Phase 2 change. Specification: docs/STUDY_DISPLACEMENT.md (awaiting the user's approval).

    python -m validation.studies.displacement

Everything is written once, for the BULLISH displacement, on side coordinates. The BEARISH one
is the same rule on the mirrored candle (open, close negated; high ↔ −low), so mirror symmetry
holds by construction. Every decision is taken at a bar's close, from bars ≤ t only; the TR
average is the one BEFORE the displacement's first candle, so a candle never inflates its own
yardstick.

Bullish vocabulary (bearish = mirrored), one candidate = one `Spec`:
  travel     close of the decision bar − open of the displacement's first candle (one candle:
             its body). It must be > EPS: a doji or a down-close candle is never bullish
  body       travel ≥ k × TR average (Spec.k)
  range      high − low of the displacement ≥ rk × TR average (Spec.rk)
  close      close − low ≥ clv × (high − low): the close in the upper part (Spec.clv)
  relative   travel ≥ rel × median body of the `look` candles before it (Spec.rel)
  beyond     close > the highest high of the `beyond` candles before it (Spec.beyond; 1 = the
             previous candle: the close is outside its range)
  multi-bar  n > 1: the last n candles (one event per window); run: the current run of
             up-close candles (a doji or a down-close candle ends it), one event per run
  fvg        the candle must be candle 2 of a bullish FVG (low of the next candle > high of the
             previous one): known one bar LATER, so the event is on candle 3
Thresholds are not tuned on outcomes: each candidate's is the Tukey upper fence (Q3 + 1.5 × IQR)
of its own statistic on the real data (`fences()`), i.e. "an outlier against its own population".
"""
from __future__ import annotations

import argparse
import math
import random
import statistics as st
import sys
from dataclasses import dataclass, replace
from datetime import datetime

from validation.candles import random_walk
from validation.models.fvg import raw_gap, sma, true_range
from validation.models.ist import IstModel
from validation.models.types import NQ_TICK, Candle, Settings
from validation.parity import CAPTURE_V070, CAPTURE_V071, capture
from validation.studies.cisd import NY, _hours, session
from validation.studies.lrl import nq_candles, resample

EPS = NQ_TICK * 0.01         # the float margin of IST: prices on the tick grid
TRA_LEN = 14                 # TR average length of Phase 1 (DEF-A2) and of the CISD body / TR metadata
SESSIONS = ("Asia", "London", "NY AM", "NY PM", "other")


@dataclass(frozen=True)
class Spec:
    name: str
    k: float = 0.0           # travel ≥ k × TR average · 0 = off
    rk: float = 0.0          # range ≥ rk × TR average · 0 = off
    clv: float = 0.0         # close − low ≥ clv × range · 0 = off
    rel: float = 0.0         # travel ≥ rel × median body of the `look` candles before · 0 = off
    look: int = 20
    beyond: int = 0          # close beyond the extreme of the `beyond` candles before · 0 = off
    n: int = 1               # candles in a fixed multi-bar window
    run: bool = False        # multi-bar: the current directional run, one event per run
    fvg: bool = False        # the (one-candle) displacement must be candle 2 of an FVG; event on candle 3
    tra_len: int = TRA_LEN
    absolute: float = 0.0    # control, NOT a displacement rule: travel ≥ this many points (a large-candle detector)


@dataclass
class Disp:
    side: int                # +1 bullish · −1 bearish
    bar: int                 # decision bar (the close that confirms it)
    origin: int              # first candle of the displacement (= bar for one candle; bar − 1 with fvg)
    body_k: float            # travel / TR average
    range_k: float           # (highest high − lowest low of the displacement) / TR average
    clv: float               # (close − low) / (high − low), side coordinates
    fvg: bool | None = None  # candle 2 of an FVG in its direction lies in [origin, bar]; None: not known yet


def view(c: Candle, s: int) -> tuple:
    """Side coordinates (o, h, l, c): +1 as is, −1 mirrored (open, close negated, high ↔ −low)."""
    return (c.open, c.high, c.low, c.close) if s > 0 else (-c.open, -c.low, -c.high, -c.close)


def run(cs, spec: Spec) -> list[Disp]:
    tr = [true_range(c, cs[i - 1] if i else None) for i, c in enumerate(cs)]
    body = [abs(c.close - c.open) for c in cs]
    out, last = [], {1: -10 ** 9, -1: -10 ** 9}
    start = {1: None, -1: None}                   # current directional run per side
    used = {1: None, -1: None}                    # the run that already fired
    for t in range(len(cs)):
        for s in (1, -1):
            o, _, _, cl = view(cs[t], s)
            start[s] = (start[s] if start[s] is not None else t) if cl > o + EPS else None
        if spec.fvg:
            m = t - 1                             # candle 2, judged on candle 3's close
            g = raw_gap(cs[m - 1], cs[t]) if m >= 1 else None
            for s in (1, -1):
                if g and g[0] == s and _ok(cs, tr, body, spec, s, m, m):
                    out.append(_rec(cs, tr, spec, s, m, m, t, fvg=True))
            continue
        for s in (1, -1):
            if spec.run:
                a = start[s]
                if a is None or used[s] == a:
                    continue
            else:
                a = t - spec.n + 1
                if a < 0 or (spec.n > 1 and last[s] > t - spec.n):
                    continue
            if _ok(cs, tr, body, spec, s, a, t):
                out.append(_rec(cs, tr, spec, s, a, t, t))
                last[s], used[s] = t, a
    for d in out:                                 # FVG fact, from the bar after the decision
        if d.fvg is None:
            d.fvg = fvg_inside(cs, d.side, d.origin, d.bar)
    return out


def _ok(cs, tr, body, spec, s, a, t) -> bool:
    tra = sma(tr, a - 1, spec.tra_len) if a >= 1 else None
    if not tra:
        return False                              # TR average warming up (or 0: no scale): no decision
    o, cl = view(cs[a], s)[0], view(cs[t], s)[3]
    hi = max(view(cs[j], s)[1] for j in range(a, t + 1))
    lo = min(view(cs[j], s)[2] for j in range(a, t + 1))
    travel = cl - o
    if not travel > EPS or (spec.n == 1 and not spec.run and not cl > view(cs[t], s)[0] + EPS):
        return False
    if spec.k and not travel >= spec.k * tra:
        return False
    if spec.rk and not hi - lo >= spec.rk * tra:
        return False
    if spec.clv and not cl - lo >= spec.clv * (hi - lo):
        return False
    if spec.rel:
        med = st.median(body[a - spec.look:a]) if a >= spec.look else 0
        if med <= 0 or not travel >= spec.rel * med:
            return False
    if spec.beyond and (a < spec.beyond or not cl > max(view(cs[j], s)[1] for j in range(a - spec.beyond, a)) + EPS):
        return False
    return not spec.absolute or travel >= spec.absolute


def _rec(cs, tr, spec, s, a, t, bar, fvg=None) -> Disp:
    tra = sma(tr, a - 1, spec.tra_len)
    hi = max(view(cs[j], s)[1] for j in range(a, t + 1))
    lo = min(view(cs[j], s)[2] for j in range(a, t + 1))
    cl = view(cs[t], s)[3]
    return Disp(s, bar, a, (cl - view(cs[a], s)[0]) / tra, (hi - lo) / tra, (cl - lo) / (hi - lo), fvg)


def fvg_inside(cs, s, a, t) -> bool | None:
    """Is candle 2 of an FVG in direction s inside [a, t]? None while candle 3 of t is missing."""
    if t + 1 >= len(cs):
        return None
    return any(j >= 1 and (g := raw_gap(cs[j - 1], cs[j + 1])) is not None and g[0] == s for j in range(a, t + 1))


# ── data ──

def segments() -> list[tuple[str, list[Candle]]]:
    """The real data in the repository: three separate 1m segments (never joined, so no TR
    average crosses from one to another)."""
    load = lambda p: [b["candle"] for b in capture.parse(p.read_text(encoding="utf-8"))["bars"]]
    return [("NQ1! 2026-10-27 03:38 → 10-28 07:56", nq_candles()),
            ("MNQ 2026-10-29 21:48 → 10-30 15:43", load(CAPTURE_V070)),
            ("MNQ 2026-10-13 19:57 → 10-14 13:52 (Bar Replay)", load(CAPTURE_V071))]


def shuffled(cs, seed: int) -> list[Candle]:
    """The same candle shapes (gap from the previous close; high, low, close from the open) in a
    random order: the marginal distribution kept, volatility clustering and sequence destroyed."""
    shapes = [(c.open - (cs[i - 1].close if i else c.open), c.high - c.open, c.low - c.open, c.close - c.open)
              for i, c in enumerate(cs)]
    random.Random(seed).shuffle(shapes)
    out, prev = [], cs[0].open
    for i, (g, h, lo, cl) in enumerate(shapes):
        o = prev + g
        out.append(Candle(cs[0].time + i * 60_000, o, o + h, o + lo, o + cl))
        prev = o + cl
    return out


def cisd_bars(cs) -> dict[int, int]:
    """Confirmation bar → side of every CISD of the frozen oracle (CISD-R) on these candles."""
    return {e.bar: e.dir for e in IstModel(Settings(modules=("cisd",))).run(cs).events if e.type == "CISD_CONFIRMED"}


def ist_fvg_middles(cs) -> dict[int, int]:
    """Candle 2 → direction of every Phase 1 FVG (frozen defaults: ≥ 2 ticks and ≥ 0.10 × TR average)."""
    return {e.bar - 1: e.dir for e in IstModel(Settings(modules=("fvg",))).run(cs).events if e.type == "FVG_CREATED"}


# ── statistics ──

def fence(xs) -> float:
    """Tukey's upper fence Q3 + 1.5 × IQR: the outlier boundary of a population."""
    q = st.quantiles(xs, n=4)
    return q[2] + 1.5 * (q[2] - q[0])


def populations(segs) -> dict[str, list[float]]:
    """Every decidable bar: |body| / TR, range / TR, |close − open| / median body of 20, the
    |travel| / TR of the last 2 and 3 candles, of the current directional run, and the close
    location of every non-doji candle."""
    p = {k: [] for k in ("body", "range", "rel", "n2", "n3", "run", "clv")}
    for _, cs in segs:
        tr = [true_range(c, cs[i - 1] if i else None) for i, c in enumerate(cs)]
        body = [abs(c.close - c.open) for c in cs]
        rs = None
        for t, c in enumerate(cs):
            s = 1 if c.close > c.open + EPS else -1 if c.close < c.open - EPS else 0
            rs = (rs if rs and rs[1] == s else (t, s)) if s else None
            if s:
                o, h, lo, cl = view(c, s)
                p["clv"].append((cl - lo) / (h - lo))
            if t > TRA_LEN:
                a = sma(tr, t - 1, TRA_LEN)
                p["body"].append(body[t] / a)
                p["range"].append((c.high - c.low) / a)
            if t > 20 and (med := st.median(body[t - 20:t])) > 0:
                p["rel"].append(body[t] / med)
            for n in (2, 3):
                if t - n + 1 > TRA_LEN:
                    p[f"n{n}"].append(abs(c.close - cs[t - n + 1].open) / sma(tr, t - n, TRA_LEN))
            if rs and rs[0] > TRA_LEN:
                p["run"].append(abs(c.close - cs[rs[0]].open) / sma(tr, rs[0] - 1, TRA_LEN))
    return p


def measure(segs, spec: Spec, near: int = 5) -> dict:
    n = bull = fvg = fvg_known = on_cisd = cisd_near = ist = cisd_n = cisd_disp = 0
    sess, sess_h, bk, rk, clv = {}, {}, [], [], []
    for _, cs in segs:
        recs = run(cs, spec)
        cb, im = cisd_bars(cs), ist_fvg_middles(cs)
        step_h = (cs[1].time - cs[0].time) / 3_600_000
        for c in cs:
            sess_h[session(c.time)] = sess_h.get(session(c.time), 0) + step_h
        mine = {(d.bar, d.side) for d in recs}
        for d in recs:
            n += 1
            bull += d.side > 0
            sess[session(cs[d.bar].time)] = sess.get(session(cs[d.bar].time), 0) + 1
            bk.append(d.body_k)
            rk.append(d.range_k)
            clv.append(d.clv)
            if d.fvg is not None:
                fvg_known += 1
                fvg += d.fvg
            ist += any(im.get(j) == d.side for j in range(d.origin, d.bar + 1))
            on_cisd += cb.get(d.bar) == d.side
            cisd_near += any(cb.get(j) == d.side for j in range(d.bar - near, d.bar + near + 1))
        cisd_n += len(cb)
        cisd_disp += sum((b, s) in mine for b, s in cb.items())
    q = lambda xs, p: st.quantiles(xs, n=100)[p - 1] if len(xs) > 1 else math.nan
    pct = lambda a, b: a / b if b else math.nan
    return {"n": n, "bull": bull, "per_hour": n / sum(_hours(cs) for _, cs in segs),
            "sessions": {k: (sess.get(k, 0), sess.get(k, 0) / sess_h[k]) for k in SESSIONS if sess_h.get(k)},
            "bk": (q(bk, 10), st.median(bk) if bk else math.nan, q(bk, 90), max(bk, default=math.nan)),
            "rk": st.median(rk) if rk else math.nan, "clv": (q(clv, 10), st.median(clv) if clv else math.nan),
            "fvg": pct(fvg, fvg_known), "ist_fvg": pct(ist, n), "on_cisd": pct(on_cisd, n),
            "cisd_near": pct(cisd_near, n), "cisd_with": pct(cisd_disp, cisd_n), "cisd_n": cisd_n}


def rate(segs, spec) -> float:
    return sum(len(run(cs, spec)) for _, cs in segs) / sum(_hours(cs) for _, cs in segs)


def jaccard(segs, a: Spec, b: Spec) -> float:
    ea = {(i, d.bar, d.side) for i, (_, cs) in enumerate(segs) for d in run(cs, a)}
    eb = {(i, d.bar, d.side) for i, (_, cs) in enumerate(segs) for d in run(cs, b)}
    return len(ea & eb) / len(ea | eb) if ea | eb else 1.0


def _f(x, p="{:.2f}") -> str:
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else p.format(x)


# ── candidates (thresholds: the Tukey fence of each statistic on the real data, §E) ──

D1 = Spec("D1 body ≥ 1.5 × TR avg", k=1.5)
D1R = Spec("D1r range ≥ 1.9 × TR avg (any up / down close)", rk=1.9)
D2 = Spec("D2 = D1 + close in the outer 25 % of the range", k=1.5, clv=0.75)
D3 = Spec("D3 body ≥ 3.9 × median body of the 20 candles before", rel=3.9, look=20)
D4_2 = Spec("D4 2-candle travel ≥ 2.1 × TR avg", k=2.1, n=2)
D4 = Spec("D4 3-candle travel ≥ 2.5 × TR avg", k=2.5, n=3)
D4R = Spec("D4r directional run travel ≥ 2.7 × TR avg (once per run)", k=2.7, run=True)
D5 = Spec("D5 = D1 + candle 2 of an FVG (event on candle 3)", k=1.5, fvg=True)
D6 = Spec("D6 = D2 + close beyond the previous candle", k=1.5, clv=0.75, beyond=1)
D7 = Spec("D7 = D2 + close beyond the previous 10 candles", k=1.5, clv=0.75, beyond=10)
CANDIDATES = [D1, D1R, D2, D3, D4, D4R, D5, D6, D7]
RECOMMENDED = replace(D6, name="DISPLACEMENT-R (= D6)")
FENCE_OF = {"body": D1.k, "range": D1R.rk, "rel": D3.rel, "n2": D4_2.k, "n3": D4.k, "run": D4R.k}   # rounded, pinned by a test


def table(segs, specs, label) -> list[str]:
    hours = sum(_hours(cs) for _, cs in segs)
    rows = [f"**{label}** ({sum(len(cs) for _, cs in segs)} bars ≈ {hours:.1f} h)", "",
            "| definition | events (bull · bear) | per hour | per hour: Asia · London · NY AM · NY PM · other | "
            "travel / TR (p10 · median · p90 · max) | range / TR (median) | close location (p10 · median) | "
            "raw FVG left | Phase 1 FVG left | is a CISD's confirming candle | same-side CISD ±5 bars | "
            "CISDs confirmed by one |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for spec in specs:
        m = measure(segs, spec)
        b = m["bk"]
        rows.append(f"| {spec.name} | {m['n']} ({m['bull']} · {m['n'] - m['bull']}) | {m['per_hour']:.2f} | "
                    + " · ".join(f"{v[1]:.1f}" for v in m["sessions"].values()) + " | "
                    f"{_f(b[0])} · {_f(b[1])} · {_f(b[2])} · {_f(b[3])} | {_f(m['rk'])} | "
                    f"{_f(m['clv'][0])} · {_f(m['clv'][1])} | {_f(m['fvg'], '{:.0%}')} | {_f(m['ist_fvg'], '{:.0%}')} | "
                    f"{_f(m['on_cisd'], '{:.0%}')} | {_f(m['cisd_near'], '{:.0%}')} | {_f(m['cisd_with'], '{:.0%}')} |")
    return rows


def fence_rows(segs) -> list[str]:
    rows = ["| data | bars | body / TR: Q1 · Q3 · **fence** | range / TR: Q1 · Q3 · **fence** | "
            "share of bars with body ≥ 1.5 × TR |", "|---|---|---|---|---|"]
    for m in (1, 3, 5, 15):
        for lab, cs in segs + [("all three", None)]:
            ss = [(x, resample(c, m)) for x, c in segs] if cs is None else [(lab, resample(cs, m))]
            p = populations(ss)
            qb, qr = st.quantiles(p["body"], n=4), st.quantiles(p["range"], n=4)
            rows.append(f"| {m}m · {lab} | {len(p['body'])} | {qb[0]:.2f} · {qb[2]:.2f} · **{fence(p['body']):.2f}** | "
                        f"{qr[0]:.2f} · {qr[2]:.2f} · **{fence(p['range']):.2f}** | "
                        f"{sum(x >= 1.5 for x in p['body']) / len(p['body']):.1%} |")
    return rows


def sensitivity(segs) -> list[str]:
    rows = ["| parameter (others as DISPLACEMENT-R) | value | per hour | events in common with DISPLACEMENT-R (Jaccard) | "
            "events with travel ≥ 4 × TR |", "|---|---|---|---|---|"]
    R = RECOMMENDED
    grid = [("k", (1.0, 1.25, 1.5, 1.75, 2.0, 2.5)), ("clv", (0.0, 0.5, 2 / 3, 0.75, 0.8, 0.9)),
            ("beyond", (0, 1, 2, 5, 10, 20)), ("tra_len", (7, 10, 14, 20, 30, 50))]
    for name, values in grid:
        for v in values:
            s = replace(R, **{name: v})
            ev = [d for _, cs in segs for d in run(cs, s)]
            rows.append(f"| {name} | {round(v, 2):g} | {rate(segs, s):.2f} | {jaccard(segs, R, s):.2f} | "
                        f"{sum(d.body_k >= 4 for d in ev)} |")
    return rows


def timeframe_rows(segs) -> list[str]:
    rows = ["| timeframe | DISPLACEMENT-R per hour | share of bars | D1 per hour |", "|---|---|---|---|"]
    for m in (1, 3, 5, 15):
        ss = [(x, resample(cs, m)) for x, cs in segs]
        bars = sum(len(cs) for _, cs in ss)
        n = sum(len(run(cs, RECOMMENDED)) for _, cs in ss)
        rows.append(f"| {m}m | {rate(ss, RECOMMENDED):.2f} | {n / bars:.1%} | {rate(ss, D1):.2f} |")
    return rows


def baseline_rows(segs) -> list[str]:
    walk = [("walk", random_walk(4000, s, gap_prob=0.02)) for s in range(1, 6)]
    shuf = [(x, shuffled(cs, seed)) for seed in range(1, 6) for x, cs in segs]
    rows = ["| definition | real NQ / MNQ | the same candles shuffled (5 orders) | random walk (5 seeds) | "
            "body / TR fence: real · shuffled · walk |", "|---|---|---|---|---|"]
    fs = tuple(f"{fence(populations(x)['body']):.2f}" for x in (segs, shuf, walk))
    for s in (replace(RECOMMENDED, k=1.0), RECOMMENDED, replace(RECOMMENDED, k=2.0), D1, D4R):
        k = f"{s.name} (k {s.k})" if s.k else s.name
        rows.append(f"| {k} | {rate(segs, s):.2f} | {rate(shuf, s):.2f} | {rate(walk, s):.2f} | {' · '.join(fs)} |")
    return rows


def control_rows(segs) -> list[str]:
    rows = ["| detector | events | per hour: Asia · London · NY AM · NY PM · other | NY AM ÷ Asia |", "|---|---|---|---|"]
    for s in [RECOMMENDED] + [Spec(f"large candle: body ≥ {p} points (no TR)", absolute=p) for p in (15, 20, 25)]:
        m = measure(segs, s)
        v = [x[1] for x in m["sessions"].values()]
        rows.append(f"| {s.name} | {m['n']} | {' · '.join(f'{x:.1f}' for x in v)} | "
                    f"{_f(m['sessions']['NY AM'][1] / m['sessions']['Asia'][1] if m['sessions']['Asia'][1] else math.nan, '{:.1f}')} |")
    return rows


def multibar_rows(segs) -> list[str]:
    rows = ["| multi-bar candidate (Tukey fence) | per hour | events | containing a DISPLACEMENT-R candle | raw FVG left |",
            "|---|---|---|---|---|"]
    for s in (D4_2, D4, D4R):
        tot = has = fv = 0
        for _, cs in segs:
            single = {(d.bar, d.side) for d in run(cs, RECOMMENDED)}
            for d in run(cs, s):
                tot += 1
                has += any((j, d.side) in single for j in range(d.origin, d.bar + 1))
                fv += bool(d.fvg)
        rows.append(f"| {s.name} | {rate(segs, s):.2f} | {tot} | {has / tot:.0%} | {fv / tot:.0%} |")
    return rows


def cisd_rows(segs, near: int = 5, show: int = 3) -> list[str]:
    """Only CISDs from bar TRA_LEN + near on count: before that no displacement is decidable."""
    both, cisd_only, disp_only = [], [], []
    total = 0
    for x, cs in segs:
        cb = {b: s for b, s in cisd_bars(cs).items() if b >= TRA_LEN + near}
        total += len(cb)
        ds = run(cs, RECOMMENDED)
        dset = {(d.bar, d.side): d for d in ds}
        tm = lambda b: datetime.fromtimestamp(cs[b].time / 1000, NY).strftime("%Y-%m-%d %H:%M")
        for b, s in cb.items():
            if (b, s) in dset:
                both.append(f"{tm(b)} {'bull' if s > 0 else 'bear'} (body {dset[(b, s)].body_k:.2f} × TR)")
            elif not any((j, s) in dset for j in range(b - near, b + near + 1)):
                cisd_only.append(f"{tm(b)} {'bull' if s > 0 else 'bear'}")
        for d in ds:
            if not any(cb.get(j) == d.side for j in range(d.bar - 2 * near, d.bar + 2 * near + 1)):
                disp_only.append(f"{tm(d.bar)} {'bull' if d.side > 0 else 'bear'} (body {d.body_k:.2f} × TR)")
    nd = sum(len(run(cs, RECOMMENDED)) for _, cs in segs)
    return [f"* CISD whose confirming candle IS a displacement: {len(both)} of {total} CISDs; e.g. {'; '.join(both[:show])}",
            f"* CISD with no same-side displacement within ±{near} bars: {len(cisd_only)} of {total}; e.g. {'; '.join(cisd_only[:show])}",
            f"* displacement with no same-side CISD within ±{2 * near} bars: {len(disp_only)} of {nd}; e.g. {'; '.join(disp_only[:show])}"]


def fvg_rows(segs) -> list[str]:
    allf = withd = 0
    c2 = []
    for _, cs in segs:
        tr = [true_range(c, cs[i - 1] if i else None) for i, c in enumerate(cs)]
        rr = {(d.bar, d.side) for d in run(cs, RECOMMENDED)}
        for j, s in ist_fvg_middles(cs).items():
            a = sma(tr, j - 1, TRA_LEN)
            if a:
                allf += 1
                withd += (j, s) in rr
                c2.append(s * (cs[j].close - cs[j].open) / a)
    q = st.quantiles(c2, n=4)
    m = measure(segs, RECOMMENDED)
    return [f"* DISPLACEMENT-R candles that leave a raw FVG (candle 2, known one bar later): {m['fvg']:.0%}; "
            f"a Phase 1 FVG (≥ 2 ticks and ≥ 0.10 × TR avg): {m['ist_fvg']:.0%}.",
            f"* Phase 1 FVGs whose candle 2 is a DISPLACEMENT-R candle: {withd} of {allf} ({withd / allf:.0%}).",
            f"* Candle 2 of the Phase 1 FVGs, body / TR in the FVG's direction: Q1 {q[0]:.2f} · median {q[1]:.2f} · "
            f"Q3 {q[2]:.2f}; {sum(x < 1 for x in c2) / len(c2):.0%} below 1 × TR, "
            f"{sum(x < 1.5 for x in c2) / len(c2):.0%} below 1.5 × TR."]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m validation.studies.displacement")
    ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    segs = segments()
    say = lambda *rows: print("\n".join(rows) + "\n")
    p = populations(segs)
    say("## Populations: Tukey fences (thresholds)\n",
        " · ".join(f"{k} {fence(p[k]):.2f}" for k in ("body", "range", "rel", "n2", "n3", "run")), "", *fence_rows(segs))
    say("## Candidates on the real data\n", *table(segs, CANDIDATES, "NQ / MNQ 1m, three segments"))
    say("## Large-candle control (absolute size) vs DISPLACEMENT-R\n", *control_rows(segs))
    say("## Synthetic baselines (events per hour)\n", *baseline_rows(segs))
    say("## Sensitivity\n", *sensitivity(segs))
    say("## Timeframes (the segments resampled)\n", *timeframe_rows(segs))
    say("## Multi-bar candidates vs DISPLACEMENT-R\n", *multibar_rows(segs))
    say("## CISD relationship (frozen CISD-R oracle)\n", *cisd_rows(segs))
    say("## FVG relationship\n", *fvg_rows(segs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
