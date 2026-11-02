"""IFVG research study: when does an existing Phase 1 FVG become an inversion FVG? Analysis only:
no indicator, FVG, CISD, displacement, LRL, HTF FVG or Phase 2 change. Specification:
docs/STUDY_IFVG.md (awaiting the user's approval).

    python -m validation.studies.ifvg

The universe is the frozen Phase 1 FVGs (DEF-A1 / A2, default inputs), followed for their whole
life (memory unbounded here, so no lifecycle is cut). For a parent FVG of side d the IFVG side is
s = −d and the edge to close through is the parent's far edge (bullish parent: its bottom; bearish:
its top). Every trigger is looked for from the bar after the parent's confirmation (DEF-A3).

  IF1  wick through the far edge (bullish parent: low < bottom)
  IF2  close strictly through the far edge (close < bottom) = the frozen Phase 1 invalidation (DEF-A5)
  IF3  IF2 on a candle that is a DISPLACEMENT-R candle of side s (a later close-through counts)
  IF4  IF2 on a bar after the one that first fully filled the zone (low ≤ bottom on an earlier bar)
  IF5  IF2 with a side-s CISD confirmed in the 10 bars up to it (structure context)
Lifecycle statistics after IF2 (descriptive only): the IFVG's near edge is the parent's far edge
(the inversion boundary), its far edge the parent's near edge.
"""
from __future__ import annotations

import argparse
import math
import statistics as st
import sys
from dataclasses import dataclass, replace

from validation.models.fvg import FvgEngine, raw_gap
from validation.models.events import EventLog
from validation.models.ist import IstModel
from validation.models.types import MODULES, NQ_TICK, FvgSettings, Settings
from validation.studies.cisd import _hours, session
from validation.studies import displacement as dsp

CONTEXT = 10                     # bars before (and including) the inversion that count as "near" for context
NEAR = 5                         # ± bars for CISD proximity
SESSIONS = ("Asia", "London", "NY AM", "NY PM", "other")


@dataclass
class Parent:
    """One Phase 1 FVG with its frozen milestones (bars, None = never)."""
    seg: int
    d: int
    id: int
    confirm: int
    top: float
    bottom: float
    mid: float
    touch: int | None
    ce: int | None
    full: int | None
    inv: int | None


def parents(cs, seg: int, memory: int = 10 ** 6) -> list[Parent]:
    e = FvgEngine(replace(FvgSettings(), memory=memory), NQ_TICK, EventLog())
    for t, c in enumerate(cs):
        e.log.at(t, c.time)
        e.step(t, c)
    return [Parent(seg, z.dir, z.id, z.confirm_bar, z.top, z.bottom, z.mid, z.touch_bar, z.ce_bar, z.full_bar, z.inv_bar)
            for z in sorted(e.records(), key=lambda z: z.confirm_bar)]


def context(cs) -> dict:
    """Per segment: displacement sides, CISD sides, sweeps / breaks and LRL terminal events per bar."""
    m = IstModel(Settings(modules=MODULES + ("lrl", "cisd", "disp"))).run(cs)
    ev = {}
    for e in m.events:
        ev.setdefault(e.type, {}).setdefault(e.bar, set()).add(e.dir)
    return {"disp": {d.bar: d.side for d in dsp.run(cs, dsp.RECOMMENDED)},
            "cisd": {b: next(iter(v)) for b, v in ev.get("CISD_CONFIRMED", {}).items()}, "ev": ev}


def through(p: Parent, c) -> bool:
    return c.close < p.bottom if p.d > 0 else c.close > p.top


def wick(p: Parent, c) -> bool:
    return c.low < p.bottom if p.d > 0 else c.high > p.top


def trigger(p: Parent, cs, ctx, kind: str) -> int | None:
    s = -p.d
    for t in range(p.confirm + 1, len(cs)):
        c = cs[t]
        if kind == "IF1" and wick(p, c):
            return t
        if kind != "IF1" and through(p, c):
            if kind == "IF2" or (kind == "IF3" and ctx["disp"].get(t) == s) or \
                    (kind == "IF4" and p.full is not None and p.full < t) or \
                    (kind == "IF5" and any(ctx["cisd"].get(j) == s for j in range(t - CONTEXT, t + 1))):
                return t
    return None


@dataclass
class Life:
    """What price did after an IF2 inversion (bars after the inversion bar; None = not by the data's end)."""
    retest: int | None           # the IFVG's near edge reached (bearish IFVG: high ≥ the parent's bottom)
    ce: int | None
    full: int | None             # the far edge reached: the zone traversed
    reclaim: int | None          # T1: a close back beyond the near edge (inside the zone or beyond)
    broken: int | None           # T2: a close strictly beyond the far edge (the IFVG mirror of DEF-A5)
    left: int                    # bars observed after the inversion


def life(p: Parent, cs, t: int) -> Life:
    s = -p.d
    near, far = (p.bottom, p.top) if s < 0 else (p.top, p.bottom)
    out = dict(retest=None, ce=None, full=None, reclaim=None, broken=None)
    reach = lambda c, lv: c.high >= lv if s < 0 else c.low <= lv
    for j in range(t + 1, len(cs)):
        c = cs[j]
        for k, ok in (("retest", reach(c, near)), ("ce", reach(c, p.mid)), ("full", reach(c, far)),
                      ("reclaim", c.close > near if s < 0 else c.close < near),
                      ("broken", c.close > far if s < 0 else c.close < far)):
            if out[k] is None and ok:
                out[k] = j - t
        if out["broken"] is not None:
            break
    return Life(**out, left=len(cs) - 1 - t)


def segments():
    return dsp.segments()


def universe(segs):
    """(segment candles, context, parents) per segment."""
    return [(cs, context(cs), parents(cs, i)) for i, (_, cs) in enumerate(segs)]


def _pct(a, b):
    return f"{a / b:.0%}" if b else "—"


def candidate_rows(uni) -> list[str]:
    rows = ["| candidate | FVGs | inverted (rate) | from ▲ · ▼ parents | bars to inversion (median) | same bar as the first touch · "
            "after the first touch · after the CE · after a full fill | after the Phase 1 invalidation | candle is DISPLACEMENT-R "
            "| same-side CISD ±5 | Asia · London · NY AM · NY PM · other |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for kind in ("IF1", "IF2", "IF3", "IF4", "IF5"):
        n = inv = bull = 0
        lag, buckets, after_inv, disp, cisd, sess = [], [0, 0, 0, 0], 0, 0, 0, {k: 0 for k in SESSIONS}
        for cs, ctx, ps in uni:
            for p in ps:
                n += 1
                t = trigger(p, cs, ctx, kind)
                if t is None:
                    continue
                inv += 1
                bull += p.d > 0
                lag.append(t - p.confirm)
                pre = [x for x in (p.touch, p.ce, p.full) if x is not None and x < t]
                buckets[len(pre)] += 1
                after_inv += p.inv is not None and t > p.inv
                disp += ctx["disp"].get(t) == -p.d
                cisd += any(ctx["cisd"].get(j) == -p.d for j in range(t - NEAR, t + NEAR + 1))
                sess[session(cs[t].time)] += 1
        rows.append(f"| {kind} | {n} | {inv} ({_pct(inv, n)}) | {bull} · {inv - bull} | {st.median(lag) if lag else '—'} | "
                    + " · ".join(_pct(x, inv) for x in buckets) + f" | {_pct(after_inv, inv)} | {_pct(disp, inv)} | "
                    f"{_pct(cisd, inv)} | " + " · ".join(str(sess[k]) for k in SESSIONS) + " |")
    return rows


def lifecycle_rows(uni) -> list[str]:
    lives = [life(p, cs, p.inv) for cs, _, ps in uni for p in ps if p.inv is not None]
    n = len(lives)
    by = lambda k, h=None: sum(getattr(x, k) is not None and (h is None or getattr(x, k) <= h) for x in lives)
    med = lambda k: st.median([getattr(x, k) for x in lives if getattr(x, k) is not None]) if by(k) else "—"
    return [f"IF2 inversions: {n} (bars observed after the inversion: median {st.median([x.left for x in lives])})", "",
            "| fact (bars after the inversion bar) | within 10 | within 30 | within 60 | by the data's end | median bars |",
            "|---|---|---|---|---|---|"] + [
        f"| {label} | {_pct(by(k, 10), n)} | {_pct(by(k, 30), n)} | {_pct(by(k, 60), n)} | {_pct(by(k), n)} | {med(k)} |"
        for k, label in (("retest", "retest: the near edge reached"), ("ce", "CE reached"), ("full", "zone traversed (far edge reached)"),
                         ("reclaim", "T1: close back beyond the near edge"), ("broken", "T2: close strictly beyond the far edge"))]


def context_rows(uni) -> list[str]:
    """For each IF2 inversion of side s, events in the CONTEXT bars up to it: the opposite side's
    liquidity swept (s < 0: BSL_SWEEP), a swing break in the inversion's direction (s < 0: SSL_BREAK),
    any LRL terminal event, a side-s CISD, and the inversion candle being DISPLACEMENT-R."""
    n = sweep = brk = lrl = cisd = disp = 0
    for cs, ctx, ps in uni:
        ev = ctx["ev"]
        for p in ps:
            if p.inv is None:
                continue
            t, s = p.inv, -p.d
            w = range(t - CONTEXT, t + 1)
            has = lambda typ, d=None: any(b in ev.get(typ, {}) and (d is None or d in ev[typ][b]) for b in w)
            n += 1
            sweep += has("BSL_SWEEP" if s < 0 else "SSL_SWEEP")
            brk += has("SSL_BREAK" if s < 0 else "BSL_BREAK")
            lrl += any(has(k) for k in ("LRL_SWEEP", "LRL_BREAK", "LRL_DRIFT"))
            cisd += any(ctx["cisd"].get(j) == s for j in w)
            disp += ctx["disp"].get(t) == s
    return [f"| context in the {CONTEXT} bars up to the IF2 inversion | share of {n} |", "|---|---|",
            f"| the opposite liquidity swept (bearish IFVG: BSL_SWEEP; bullish: SSL_SWEEP) | {_pct(sweep, n)} |",
            f"| a swing broken in the inversion's direction (SSL_BREAK / BSL_BREAK) | {_pct(brk, n)} |",
            f"| an LRL terminal event (sweep / break / drift) | {_pct(lrl, n)} |",
            f"| a same-side CISD | {_pct(cisd, n)} |",
            f"| the inversion candle is DISPLACEMENT-R (same side) | {_pct(disp, n)} |"]


def cisd_rows(uni) -> list[str]:
    """IFVG + CISD near the inversion, IFVG without CISD, CISD without an IFVG near it (±NEAR, same side)."""
    with_c = without = c_total = c_alone = 0
    for cs, ctx, ps in uni:
        inv = {}
        for p in ps:
            if p.inv is not None:
                inv.setdefault(p.inv, set()).add(-p.d)
        for t, sides in inv.items():
            for s in sides:
                if any(ctx["cisd"].get(j) == s for j in range(t - NEAR, t + NEAR + 1)):
                    with_c += 1
                else:
                    without += 1
        for b, s in ctx["cisd"].items():
            c_total += 1
            c_alone += not any(s in inv.get(j, ()) for j in range(b - NEAR, b + NEAR + 1))
    return [f"* inversions (IF2, counted per side and bar) with a same-side CISD within ±{NEAR} bars: {with_c} · without: {without}",
            f"* CISDs with no same-side IF2 inversion within ±{NEAR} bars: {c_alone} of {c_total} ({_pct(c_alone, c_total)})"]


def example_rows(uni, segs, show: int = 3) -> list[str]:
    """Real IF2 inversions to look at (New York time): with / without a same-side CISD within ±NEAR,
    with / without a DISPLACEMENT-R inversion candle, and CISDs with no inversion near them."""
    from datetime import datetime
    from validation.studies.cisd import NY
    cat = {k: [] for k in ("IFVG + CISD", "IFVG without CISD", "CISD without IFVG", "inversion candle is DISPLACEMENT-R",
                           "inversion candle is not DISPLACEMENT-R")}
    for (label, _), (cs, ctx, ps) in zip(segs, uni):
        tm = lambda b: f"{label.split()[0]} {datetime.fromtimestamp(cs[b].time / 1000, NY):%Y-%m-%d %H:%M}"
        inv = {}
        for p in ps:
            if p.inv is None:
                continue
            s, t = -p.d, p.inv
            inv.setdefault(t, set()).add(s)
            what = f"{tm(t)} {'bull' if s > 0 else 'bear'} IFVG [{p.bottom:.2f}, {p.top:.2f}]"
            near = any(ctx["cisd"].get(j) == s for j in range(t - NEAR, t + NEAR + 1))
            cat["IFVG + CISD" if near else "IFVG without CISD"].append(what)
            cat["inversion candle is DISPLACEMENT-R" if ctx["disp"].get(t) == s else
                "inversion candle is not DISPLACEMENT-R"].append(what)
        for b, s in ctx["cisd"].items():
            if b > 20 and not any(s in inv.get(j, ()) for j in range(b - NEAR, b + NEAR + 1)):
                cat["CISD without IFVG"].append(f"{tm(b)} {'bull' if s > 0 else 'bear'} CISD")
    return [f"* {k}: {'; '.join(v[:show])}" for k, v in cat.items()]


def universe_rows(segs) -> list[str]:
    """Option B (any raw 3-candle gap) against option A (the frozen Phase 1 FVGs)."""
    raw = qual = dropped_open = 0
    for i, (_, cs) in enumerate(segs):
        raw += sum(1 for t in range(2, len(cs)) if raw_gap(cs[t - 2], cs[t]) is not None)
        qual += len(parents(cs, i))
        e = FvgEngine(FvgSettings(), NQ_TICK, EventLog())
        for t, c in enumerate(cs):
            e.log.at(t, c.time)
            e.step(t, c)
        dropped_open += e.drop_open
    return [f"* raw 3-candle gaps (DEF-A1 geometry): {raw} · Phase 1 FVGs (DEF-A2 qualified, default inputs): {qual} "
            f"({_pct(qual, raw)}); open FVGs dropped by the default memory (50 per direction) before any inversion: {dropped_open}"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m validation.studies.ifvg")
    ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    segs = segments()
    uni = universe(segs)
    say = lambda *rows: print("\n".join(rows) + "\n")
    say("## Universe\n", *universe_rows(segs), f"* data: {sum(len(cs) for _, cs in segs)} bars ≈ "
        f"{sum(_hours(cs) for _, cs in segs):.1f} h, three segments")
    say("## Candidate triggers\n", *candidate_rows(uni))
    say("## After an IF2 inversion (descriptive)\n", *lifecycle_rows(uni))
    say("## Context up to the IF2 inversion\n", *context_rows(uni))
    say("## CISD relationship\n", *cisd_rows(uni))
    say("## Real examples\n", *example_rows(uni, segs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
