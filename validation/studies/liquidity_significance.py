"""Phase 2 liquidity significance study. Analysis only: no indicator or oracle change.

    python -m validation.studies.liquidity_significance [--noise]

Reads the exact NQ1! 1m candles of the committed TradingView capture (IST v0.4.3-dev,
bounded Pine-Log parity PASS), finds every confirmed pivot with the current DEF-L1 rule,
and measures candidate significance features. Two kinds of number are kept apart:

* FEATURES use only bars up to the confirmation bar t = X + right (no lookahead). Only
  these may enter a definition.
* OUTCOMES use later bars (when the level is taken, how far price moved away first).
  They only evaluate candidates and never enter a definition.

Swing lows are measured as swing highs of the mirrored series (high ↔ −low), so every
formula below is written once, for highs.
"""
from __future__ import annotations

import argparse
import statistics as st
import sys
from dataclasses import dataclass
from pathlib import Path

from validation.candles import random_walk
from validation.models.fvg import sma, true_range
from validation.models.ist import IstModel
from validation.models.liquidity import LiquidityEngine
from validation.models.types import PRESETS, Settings
from validation.parity import capture

DATA = Path(__file__).parent / "data" / "nq1_1m_capture_2026-10-27.csv"
TICK, TOL_TICKS, TRA_LEN = 0.25, 4, 14
LOOKBACK = 60          # features need up to 60 earlier bars: pivots before that are not studied
MAJOR = 3.0            # outcome: price moved ≥ 3 × TR average away before revisiting the level


@dataclass
class Pivot:
    side: str           # "high" / "low"
    X: int              # swing bar
    t: int              # confirmation bar (X + right)
    price: float        # the swing price (mirrored for lows)
    tra: float          # TR average (14) at X: the normaliser of every feature
    react: float        # DEF-L2 reaction: high − lowest low of the right bars
    excess: float       # height above the highest neighbour inside the pivot window
    dom: int            # bars since a high above high + EQ tolerance (left dominance)
    dom_censored: bool  # no such bar inside the data: dom is a lower bound
    rise: float         # high − lowest low since that bar (left prominence)
    rise_w: dict        # high − lowest low of the last W bars, W in (10, 20, 30, 60)
    beyond: float       # how far the right bars went beyond the swing bar's own low
    sep: float | None   # distance to the previous same-side level accepted by the current rule
    take: int | None    # OUTCOME: bars from confirmation to the first trade strictly beyond
    amp: float          # OUTCOME: furthest move away before that take (or the data end)


def _sides(cs):
    yield "high", [c.high for c in cs], [c.low for c in cs]
    yield "low", [-c.low for c in cs], [-c.high for c in cs]


def pivots(cs, left: int, right: int, k: float) -> list[Pivot]:
    """Every DEF-L1 pivot with X ≥ LOOKBACK, its features and outcomes."""
    tr = [true_range(c, cs[i - 1] if i else None) for i, c in enumerate(cs)]
    tol, eps = TOL_TICKS * TICK, TICK * 0.01
    out = []
    for side, hi, lo in _sides(cs):
        last_ok = None
        for t in range(len(cs)):
            X = t - right
            if X - left < 0:
                continue
            if not (hi[X] > max(hi[X - left:X]) and hi[X] >= max(hi[X + 1:t + 1])):
                continue
            tra = sma(tr, X, TRA_LEN)
            react = hi[X] - min(lo[X + 1:t + 1])
            accepted_now = tra is not None and react >= k * tra
            if X < LOOKBACK or tra is None:
                last_ok = hi[X] if accepted_now else last_ok
                continue
            j = X - 1
            while j >= 0 and hi[j] <= hi[X] + tol:
                j -= 1
            take = next((s - t for s in range(t + 1, len(cs)) if hi[s] > hi[X] + eps), None)
            end = t + take if take is not None else len(cs)
            out.append(Pivot(
                side, X, t, hi[X], tra, react / tra,
                (hi[X] - max(hi[X - left:X] + hi[X + 1:t + 1])) / tra,
                X - j - 1, j < 0, (hi[X] - min(lo[j + 1:X + 1])) / tra,
                {w: (hi[X] - min(lo[X - w:X + 1])) / tra for w in (10, 20, 30, 60)},
                (lo[X] - min(lo[X + 1:t + 1])) / tra,
                None if last_ok is None else abs(hi[X] - last_ok) / tra,
                take, (hi[X] - min(lo[X + 1:end])) / tra))
            if accepted_now:
                last_ok = hi[X]
    return out


# ── candidate definitions (feature-only predicates) ────────────────────────────

def candidates(k: float) -> dict:
    """name → predicate on a Pivot. The current rule first; every other one keeps the
    pivot window and the confirmation bar unchanged."""
    tol_tr = lambda p: TOL_TICKS * TICK / p.tra
    c = {f"C0 current (reaction ≥ {k:g})": lambda p: p.react >= k}
    for kk in (1.5, 2, 3):
        c[f"C0 reaction ≥ {kk:g} (k raised)"] = lambda p, kk=kk: p.react >= kk
    for w in (10, 20, 30, 60):
        c[f"C1 current + dominance ≥ {w}"] = lambda p, w=w: p.react >= k and p.dom >= w
    for m in (1, 1.5, 2, 3):
        c[f"C2 prominence min(rise, reaction) ≥ {m:g}"] = lambda p, m=m: min(p.rise, p.react) >= m
    for w, m in ((10, 1), (20, 1.5), (30, 1.5), (30, 2), (60, 2)):
        c[f"C3 dominance ≥ {w} and min(rise_{w}, reaction) ≥ {m:g}"] = \
            lambda p, w=w, m=m: p.dom >= w and min(p.rise_w[w], p.react) >= m
    for b in (0, 0.5, 1):
        c[f"C4 beyond swing bar ≥ {b:g}"] = lambda p, b=b: p.beyond >= b
    for s in (1, 2):
        c[f"C5 current + separation ≥ {s} (EQ band kept)"] = \
            lambda p, s=s: p.react >= k and (p.sep is None or p.sep >= s or p.sep <= tol_tr(p))
    return c


def _q(xs, qs=(0.1, 0.25, 0.5, 0.75, 0.9)):
    xs = sorted(xs)
    return [xs[min(len(xs) - 1, int(q * len(xs)))] for q in qs] if xs else []


def describe(ps: list[Pivot]) -> list[str]:
    rows = ["| feature (× TR average) | p10 | p25 | median | p75 | p90 |", "|---|---|---|---|---|---|"]
    feats = {"reaction (DEF-L2)": [p.react for p in ps], "excess over window neighbours": [p.excess for p in ps],
             "left dominance (bars)": [p.dom for p in ps], "rise since last higher high": [p.rise for p in ps],
             **{f"rise over last {w} bars": [p.rise_w[w] for p in ps] for w in (10, 20, 30, 60)},
             "beyond swing bar": [p.beyond for p in ps],
             "separation to previous accepted": [p.sep for p in ps if p.sep is not None],
             "OUTCOME bars to take (taken only)": [p.take for p in ps if p.take is not None],
             "OUTCOME amplitude before take": [p.amp for p in ps]}
    for name, xs in feats.items():
        rows.append(f"| {name} | " + " | ".join(f"{x:.2f}" if isinstance(x, float) else str(x) for x in _q(xs)) + " |")
    return rows


def evaluate(ps: list[Pivot], k: float, hours: float) -> list[str]:
    major = [p for p in ps if p.amp >= MAJOR]
    rows = ["| candidate | kept (H · L) | kept % | per hour | taken ≤ 5 bars | median amplitude | "
            f"major kept (recall) | kept that were major (precision) | median same-side spacing |",
            "|---|---|---|---|---|---|---|---|---|"]
    for name, ok in candidates(k).items():
        kept = [p for p in ps if ok(p)]
        if not kept:
            rows.append(f"| {name} | 0 | 0% | — | — | — | — | — | — |")
            continue
        hl = f"{sum(p.side == 'high' for p in kept)} · {sum(p.side == 'low' for p in kept)}"
        quick = sum(p.take is not None and p.take <= 5 for p in kept) / len(kept)
        rec = sum(p in kept for p in major) / len(major) if major else float("nan")
        prec = sum(p.amp >= MAJOR for p in kept) / len(kept)
        gaps = []
        for side in ("high", "low"):
            px = [p for p in sorted(kept, key=lambda p: p.t) if p.side == side]
            gaps += [abs(b.price - a.price) / b.tra for a, b in zip(px, px[1:])]
        rows.append(f"| {name} | {hl} | {100 * len(kept) / len(ps):.0f}% | {len(kept) / hours:.1f} | "
                    f"{100 * quick:.0f}% | {st.median(p.amp for p in kept):.1f} | {100 * rec:.0f}% | "
                    f"{100 * prec:.0f}% | {st.median(gaps) if gaps else float('nan'):.1f} |")
    return rows


def study(cs, label: str) -> list[str]:
    hours = len(cs) / 60
    out = [f"## {label}: {len(cs)} bars"]
    for preset, (left, right, k) in PRESETS.items():
        ps = pivots(cs, left, right, k)
        out += ["", f"### {preset} (left {left} · right {right} · k {k:g}): {len(ps)} pivots with X ≥ {LOOKBACK} "
                f"({sum(p.side == 'high' for p in ps)} highs · {sum(p.side == 'low' for p in ps)} lows); "
                f"major swings (amplitude ≥ {MAJOR:g} TR before revisit): {sum(p.amp >= MAJOR for p in ps)}", ""]
        out += describe(ps) + [""] + evaluate(ps, k, hours)
    return out


# ── downstream: the oracle's own liquidity engine with another significance test ──

class _Engine(LiquidityEngine):
    """Study only: DEF-L2 replaced by `accept`; pivots, takes, classes and EQ unchanged."""

    def __init__(self, *a, accept=None, **kw):
        super().__init__(*a, **kw)
        self.accept = accept

    def _judged(self, side, px, X, x_time, react, req, tra, t) -> None:
        side.pivots += 1
        if req is None:
            return
        if self.accept(_Ctx(self, side, X, t, tra)):
            self._register(side, px, X, x_time, react, req, tra, t)
        else:
            side.rejects += 1


class _Ctx:
    """Features of one judged pivot, in TR averages, from bars up to t only."""

    def __init__(self, eng, side, X, t, tra):
        s = 1 if side.is_bsl else -1
        self.hi = (lambda j: eng.H[j]) if s > 0 else (lambda j: -eng.Lo[j])
        self.lo = (lambda j: eng.Lo[j]) if s > 0 else (lambda j: -eng.H[j])
        self.X, self.t, self.tra, self.tol = X, t, tra, eng.tol

    @property
    def react(self):
        return (self.hi(self.X) - min(self.lo(j) for j in range(self.X + 1, self.t + 1))) / self.tra

    def dominates(self, w):
        """No high above this one + EQ tolerance in the w bars before it (and w bars exist)."""
        return self.X >= w and all(self.hi(j) <= self.hi(self.X) + self.tol for j in range(self.X - w, self.X))

    @property
    def beyond(self):
        return (self.lo(self.X) - min(self.lo(j) for j in range(self.X + 1, self.t + 1))) / self.tra


def definitions(preset: str) -> dict:
    """Candidate DEF-L2 replacements for one preset (study grid, not a proposal list)."""
    k = PRESETS[preset][2]
    w = {"aggressive": 10, "balanced": 30, "strict": 60}[preset]
    m = {"aggressive": 1.0, "balanced": 1.5, "strict": 2.0}[preset]
    b = {"aggressive": 0.0, "balanced": 0.5, "strict": 1.0}[preset]
    return {f"current: reaction ≥ {k:g}": lambda c: c.react >= k,
            f"k doubled: reaction ≥ {2 * k:g}": lambda c: c.react >= 2 * k,
            f"current + dominance {w}": lambda c: c.react >= k and c.dominates(w),
            f"dominance {w} + reaction ≥ {m:g}": lambda c: c.dominates(w) and c.react >= m,
            f"reaction ≥ {m:g} (no dominance)": lambda c: c.react >= m,
            f"beyond swing bar ≥ {b:g}": lambda c: c.beyond >= b}


def simulate(cs, preset: str) -> list[str]:
    left, right, _ = PRESETS[preset]
    rows = [f"| {preset} definition | BSL · SSL created | per hour | EQH · EQL created | sweeps · breaks | "
            "taken ≤ 5 bars after creation | active levels per side (median · max) |", "|---|---|---|---|---|---|---|"]
    hours = len(cs) / 60
    for name, accept in definitions(preset).items():
        s = Settings.from_dict({"liq": {"preset": preset}, "modules": ["liq"]})
        m = IstModel(s)
        m.liq = _Engine(s.liq, s.tick, m.log, accept=accept)
        m.run(cs)
        ev = m.events
        n = lambda typ: sum(e.type == typ for e in ev)
        born = {(e.dir, e.sid): e.bar for e in ev if e.type in ("BSL_CREATED", "SSL_CREATED")}
        taken = {(e.dir, e.sid): e.bar for e in ev if e.type in ("BSL_TAKEN", "SSL_TAKEN")}
        quick = sum(1 for key, b in born.items() if key in taken and taken[key] - b <= 5)
        active = []
        for d in (1, -1):
            spans = [(b, taken.get(key, len(cs))) for key, b in born.items() if key[0] == d]
            active += [sum(a <= t < z for a, z in spans) for t in range(LOOKBACK, len(cs), 5)]
        rows.append(f"| {name} | {n('BSL_CREATED')} · {n('SSL_CREATED')} | {len(born) / hours:.1f} | "
                    f"{n('EQH_CREATED')} · {n('EQL_CREATED')} | {n('BSL_SWEEP') + n('SSL_SWEEP')} · "
                    f"{n('BSL_BREAK') + n('SSL_BREAK')} | {100 * quick / max(1, len(born)):.0f}% | "
                    f"{st.median(active):.0f} · {max(active)} |")
    return rows


def _run(cs, preset, accept):
    s = Settings.from_dict({"liq": {"preset": preset}, "modules": ["liq"]})
    m = IstModel(s)
    m.liq = _Engine(s.liq, s.tick, m.log, accept=accept)
    return m.run(cs).events


def grid(cs, label: str, preset="balanced", ws=(15, 20, 30, 45, 60), ms=(1.0, 1.25, 1.5, 2.0)) -> list[str]:
    """Sensitivity of 'dominance W + reaction ≥ m': levels per hour · EQH+EQL · % taken ≤ 5 bars."""
    hours = len(cs) / 60
    rows = [f"{label} ({len(cs)} bars), {preset} pivots: levels/hour · EQ clusters · taken ≤ 5 bars", "",
            "| W \\ m | " + " | ".join(f"{m:g}" for m in ms) + " |", "|---" * (len(ms) + 1) + "|"]
    for w in (0, *ws):
        cells = []
        for m in ms:
            ev = _run(cs, preset, lambda c, w=w, m=m: c.react >= m and (w == 0 or c.dominates(w)))
            born = {(e.dir, e.sid): e.bar for e in ev if e.type.endswith("_CREATED") and e.type[:3] in ("BSL", "SSL")}
            taken = {(e.dir, e.sid): e.bar for e in ev if e.type in ("BSL_TAKEN", "SSL_TAKEN")}
            quick = sum(1 for k, b in born.items() if k in taken and taken[k] - b <= 5)
            eq = sum(e.type in ("EQH_CREATED", "EQL_CREATED") for e in ev)
            cells.append(f"{len(born) / hours:.1f} · {eq} · {100 * quick / max(1, len(born)):.0f}%")
        rows.append(f"| {'none' if w == 0 else w} | " + " | ".join(cells) + " |")
    return rows


def deferred(cs, preset="balanced", ms=(1.5, 2.0), horizons=(10, 30)) -> list[str]:
    """Alternative: a pivot qualifies on the first bar s ≥ X + right at which price has moved
    m × TR away from it (bars X+1…s), if that happens within M bars and before the level is
    taken. Decided once, at s (no repaint), but the creation time varies."""
    left, right, _ = PRESETS[preset]
    rows = ["| m · M | qualified / pivots | median delay after X + right | taken before qualifying |", "|---|---|---|---|"]
    ps = pivots(cs, left, right, 0)
    for m in ms:
        for M in horizons:
            ok, delays, lost = 0, [], 0
            for side, hi, lo in _sides(cs):
                for p in (p for p in ps if p.side == side):
                    s_end = p.t + p.take if p.take is not None else len(cs)
                    s = next((s for s in range(p.t, min(s_end, p.X + right + M + 1))
                              if hi[p.X] - min(lo[p.X + 1:s + 1]) >= m * p.tra), None)
                    if s is not None:
                        ok, delays = ok + 1, delays + [s - p.t]
                    elif p.take is not None and p.t + p.take <= p.X + right + M:
                        lost += 1
            rows.append(f"| {m:g} · {M} | {ok} / {len(ps)} ({100 * ok / len(ps):.0f}%) | "
                        f"{st.median(delays) if delays else '—'} bars | {lost} |")
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m validation.studies.liquidity_significance")
    ap.add_argument("--noise", action="store_true", help="also run the same study on random walks (the null)")
    ap.add_argument("--grid", action="store_true", help="sensitivity grid, halves of the sample, deferred qualification")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cs = [b["candle"] for b in capture.parse(DATA.read_text(encoding="utf-8"))["bars"]]
    print("\n".join(study(cs, "NQ1! 1m, TradingView capture 2026-10-27 03:38 → 21:34 New York")))
    print("\n## Downstream (oracle liquidity engine, NQ capture; EQ, takes and classes unchanged)\n")
    for preset in PRESETS:
        print("\n".join(simulate(cs, preset)) + "\n")
    if a.grid:
        half = len(cs) // 2
        for part, label in ((cs, "NQ capture"), (cs[:half], "NQ first half"), (cs[half:], "NQ second half")):
            print("\n".join(grid(part, label)) + "\n")
        print("Deferred qualification (balanced pivots, NQ capture)\n\n" + "\n".join(deferred(cs)) + "\n")
        if a.noise:
            print("\n".join(grid(random_walk(18000, 1, gap_prob=0.02), "Random walk seed 1")) + "\n")
    if a.noise:
        walk = random_walk(18000, 1, gap_prob=0.02)
        print("\n" + "\n".join(study(walk, "Random walk (no structure), seed 1, 18000 bars")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
