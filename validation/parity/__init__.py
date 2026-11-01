"""Pine / Python parity: compare what TradingView showed with what the oracle expects.

Nothing here talks to TradingView. You export the chart by hand (Export chart data,
IST Debug mode ON) and either run `python -m validation.parity EXPORT.csv`, which
writes validation/parity/pine_observed.json, or fill that file yourself (format:
pine_observed.example.json). Two kinds of observation are compared:

* Data Window, bar by bar: the IST debug plots in the export (FVG verdict and
  required gap, swing verdicts, reactions, required reaction, take codes).
* Events and states copied from the IST debug table or alerts (optional).
"""
from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from validation import VALIDATION_DIR
from validation.candles import load_tradingview_export
from validation.models.events import ONCE, parse_local, parse_pine_line
from validation.models.fvg import raw_gap, required, sma
from validation.models.ist import IstModel
from validation.models.types import Candle, Settings

PARITY_DIR = VALIDATION_DIR / "parity"
OBSERVED = PARITY_DIR / "pine_observed.json"
# Real TradingView Parity captures kept as validation evidence: never rewritten, hashed in
# evidence/SHA256SUMS.txt, described in evidence/README.md.
EVIDENCE = PARITY_DIR / "evidence"
CAPTURE_V043 = EVIDENCE / "ist-v0.4.3-dev_nq1-1m_capture-1000_2026-10-27.csv"  # historical: DEF-L2 before C1
CAPTURE_V044 = EVIDENCE / "ist-v0.4.4-dev_nq1-1m_capture-1000_2026-10-28.csv"  # C1: Phase 2 frozen baseline
CAPTURE_V070 = EVIDENCE / "ist-v0.7.0-dev_mnq-1m_capture-1000_2026-10-30.csv"  # the call-history defect (fixed in v0.7.1-dev)
CAPTURE_V071 = EVIDENCE / "ist-v0.7.1-dev_mnq-1m-replay_capture-1000_2026-10-14.csv"  # CISD freeze evidence: 0 DIFFERENCE
CAPTURE_V080 = EVIDENCE / "ist-v0.8.0-dev_mnq-1m-replay_capture-1000_2026-10-30.csv"  # DISP-L10: 0 DIFFERENCE

# src/IST.pine Data Window plots (Debug mode ON), found by a fragment of the plot title
# (the export's column header). tests/test_parity.py checks each matches exactly one title.
SERIES = {
    "fvg_verdict": "candle 3 verdict",                  # ±2 created · ±1 raw gap rejected · 0 no gap
    "fvg_required": "required gap = max",               # points; na while a reference warms up
    "bsl_pivot": "liq swing high judged here",          # 2 → BSL · 1 rejected (or warm-up) · 0 none
    "ssl_pivot": "liq swing low judged here",
    "liq_required": "liq required reaction",            # k × TR average at the swing bar
    "bsl_reaction": "liq reaction of that swing high",  # compared where the oracle created the level
    "ssl_reaction": "liq reaction of that swing low",
    "bsl_take": "liq bsl take on this bar",             # 0 · 1 sweep · 2 break · 3 taken, bar open
    "ssl_take": "liq ssl take on this bar",
    "bsl_dominance": "liq dominance: highest high",     # C1: extreme of the W bars before the swing bar
    "ssl_dominance": "liq dominance: lowest low",       # (na: dominance off, or fewer than W earlier bars)
}
MINTICK = "syminfo.mintick"
NUM_TOL = 1e-4          # points: the export may round floats


def load(path: Path = OBSERVED) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def export_of(obs: dict, base: Path) -> tuple[list[Candle], list[dict]]:
    tz = obs.get("timezone", "America/New_York")
    if obs.get("candles_csv"):
        return load_tradingview_export(base / obs["candles_csv"], tz)
    return [Candle(parse_local(r[0], tz) if isinstance(r[0], str) else int(r[0]), *map(float, r[1:5]))
            for r in obs["candles"]], []


def candles_of(obs: dict, base: Path) -> list[Candle]:
    return export_of(obs, base)[0]


def _num(v) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def _fmt(ms: int, tz: str) -> str:
    return datetime.fromtimestamp(ms / 1000, ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M")


def mintick(rows: list[dict]) -> float | None:
    col = next((h for h in (rows[0] if rows else {}) if MINTICK in h), None)
    return next((x for x in (_num(r[col]) for r in rows) if x is not None), None) if col else None


def oracle_series(candles: list[Candle], settings: Settings, m: IstModel | None = None) -> dict[str, list]:
    """What each Data Window plot must show on every bar, read from the oracle's own run
    (its events, pivot counters and TR series; `m`, if given, is a fresh model to run).
    Nothing here re-decides the logic."""
    s = settings
    m = m or IstModel(s)
    out = {k: [] for k in SERIES}
    for t, c in enumerate(candles):
        was = [side.pivots for side in m.liq.sides()]
        new = m.step(c)
        types = {e.type for e in new}
        made = [e.dir for e in new if e.type == "FVG_CREATED"]
        geo = raw_gap(candles[t - 2], c) if t >= 2 else None
        out["fvg_verdict"].append(2 * made[0] if made else geo[0] if geo else 0)
        tick_req, tra_req, rng_req = required(s.fvg, s.tick, *m.fvg.references(t))
        out["fvg_required"].append(None if tra_req is None or rng_req is None else max(tick_req, tra_req, rng_req))
        tra = sma(m.liq.tr, t - s.liq.right, s.liq.tra_len)
        out["liq_required"].append(None if tra is None else s.liq.k * tra)
        for side, before in zip(m.liq.sides(), was):
            k, n = side.name.lower(), side.name
            created = f"{n}_CREATED" in types
            out[f"{k}_pivot"].append(2 if created else 1 if side.pivots > before else 0)
            out[f"{k}_reaction"].append(side.live[-1].react if created else None)
            out[f"{k}_take"].append(2 if f"{n}_BREAK" in types else 1 if f"{n}_SWEEP" in types
                                    else 3 if f"{n}_TAKEN" in types else 0)
            out[f"{k}_dominance"].append(m.liq.dominance_ref(side, t - s.liq.right))
        if m.lrl is not None:                       # what the capture's LH / LL / KH / KL must show
            for side in m.lrl.sides():
                g, k = side.sign, side.name.lower()
                out.setdefault(f"lrl_{k}", []).append(
                    {r.id: (g * (r.y(t) + r.tau), g * (r.y(t - 1) + r.tau)) for r in side.live})
                out.setdefault(f"lrl_cand_{k}", []).append(len(side.cands))
    return out


def totals(series: dict[str, list]) -> dict:
    """Counts comparable with the IST debug rows 22–23 (swings). Takes count bars (one code
    per bar and side, break over sweep), not levels."""
    out = {}
    for side in ("bsl", "ssl"):
        p, k = series.get(f"{side}_pivot", []), series.get(f"{side}_take", [])
        out[side] = {"pivots": sum(1 for v in p if v), "pass": p.count(2), "reject_or_warmup": p.count(1),
                     "sweep": k.count(1), "break": k.count(2)}
    v = series.get("fvg_verdict", [])
    out["fvg"] = {"bull": v.count(2), "bear": v.count(-2), "rejected": v.count(1) + v.count(-1)}
    return out


def data_window(candles: list[Candle], rows: list[dict], settings: Settings, tz: str,
                lo: int | None = None, hi: int | None = None, m: IstModel | None = None) -> dict | None:
    """Bar-by-bar comparison of the IST Data Window columns with the oracle. None when the
    export has no IST debug column at all."""
    header = list(rows[0]) if rows else []
    cols = {k: next((h for h in header if frag in h), None) for k, frag in SERIES.items()}
    if not any(cols.values()):
        return None
    missing = [SERIES[k] for k, h in cols.items() if h is None]
    if missing:
        raise ValueError(f"export lacks IST Data Window columns {missing}: is it the same IST build?")
    pine = {k: [_num(r[h]) for r in rows] for k, h in cols.items()}
    if all(v is None for vs in pine.values() for v in vs):
        raise ValueError("every IST debug column is empty: turn ON 'Debug mode' in the IST settings and export again")
    want = oracle_series(candles, settings, m)
    diffs, bars = [], 0
    tick = mintick(rows)
    if tick is not None and abs(tick - settings.tick) > 1e-12:
        diffs.append({"time": "-", "bar": None, "series": "tick_size", "pine": tick, "oracle": settings.tick})
    for t in range(len(candles) - 1):                  # the last exported bar may still be open
        ms = candles[t].time
        if (lo is not None and ms < lo) or (hi is not None and ms > hi):
            continue
        bars += 1
        for k in SERIES:
            p, o = pine[k][t], want[k][t]
            if k.endswith("_reaction") and o is None:
                continue
            if (p is None) != (o is None) or (p is not None and abs(p - o) > NUM_TOL):
                diffs.append({"time": _fmt(ms, tz), "bar": t, "series": k, "pine": p, "oracle": o})
    return {"bars": bars, "first_bar": _fmt(candles[0].time, tz), "last_bar": _fmt(candles[-1].time, tz),
            "differences": len(diffs), "by_series": dict(Counter(d["series"] for d in diffs)), "first": diffs[:25],
            "totals": {"pine": totals(pine), "oracle": totals(want)}}


def observed_events(obs: dict) -> list[dict]:
    tz, year = obs.get("timezone", "America/New_York"), int(obs.get("year", 2026))
    out = []
    for d in obs.get("observed_events", []):
        e = dict(d)
        for k in ("time", "sid"):
            if isinstance(e.get(k), str):
                e[k] = parse_local(e[k], tz)
        out.append(e)
    out += [parse_pine_line(line, tz, year) for line in obs.get("observed_event_lines", [])]
    return out


def _key(e: dict) -> tuple:
    return (e["type"], e.get("dir", 0), e.get("sid")) if e["type"] in ONCE else (e["type"], e.get("sid"), e.get("time"))


def compare(obs: dict, base: Path = PARITY_DIR) -> dict:
    """Data Window columns bar by bar (when the export has them), then every observed event
    must match an oracle event (type, direction, id; then time and price). With
    "complete": true, every oracle event of the observed types inside the window must
    also have been observed."""
    tz = obs.get("timezone", "America/New_York")
    settings = Settings.from_dict({**obs.get("settings", {}), "tick": obs.get("tick_size", 0.25)})
    candles, rows = export_of(obs, base)
    lo = parse_local(obs["window"]["from"], tz) if obs.get("window") else None
    hi = parse_local(obs["window"]["to"], tz) if obs.get("window") else None
    m = IstModel(settings)
    dw = data_window(candles, rows, settings, tz, lo, hi, m) if rows else None
    if not m.candles:
        m.run(candles)
    oracle = [{"time": e.time, "type": e.type, "dir": e.dir, "sid": e.sid, "price": e.price} for e in m.events
              if (lo is None or e.time >= lo) and (hi is None or e.time <= hi)]
    want = {_key(e): e for e in oracle}
    seen = observed_events(obs)
    missing, mismatched, matched = [], [], 0
    for o in seen:
        e = want.get(_key(o))
        if e is None:
            missing.append({"observed_in_pine": o, "oracle": "no such event"})
            continue
        bad = {k: (o[k], e[k]) for k in ("time", "price") if o.get(k) is not None and o[k] != e[k]}
        if bad:
            mismatched.append({"event": o["type"], "sid": o.get("sid"), "pine_vs_oracle": bad})
        else:
            matched += 1
    extra = []
    if obs.get("complete"):
        types = {o["type"] for o in seen}
        keys = {_key(o) for o in seen}
        extra = [e for e in oracle if e["type"] in types and _key(e) not in keys]
    states = []
    for st in obs.get("observed_states", []):
        recs = m.state().get(st["group"], [])
        sid = parse_local(st["id"], tz) if isinstance(st.get("id"), str) else st.get("id")
        rec = next((r for r in recs if r.get("id") == sid), None)
        if rec is None or rec.get(st["field"]) != st["value"]:
            states.append({"group": st["group"], "id": st.get("id"), "field": st["field"], "pine": st["value"],
                           "oracle": None if rec is None else rec.get(st["field"])})
    return {"status": "COMPARED", "build": obs.get("build"), "bars": len(candles), "observed": len(seen),
            "matched": matched, "not_in_oracle": missing, "mismatched": mismatched, "not_observed_in_pine": extra,
            "state_differences": states, "data_window": dw,
            "differences": len(missing) + len(mismatched) + len(extra) + len(states) + (dw["differences"] if dw else 0)}


def run() -> dict:
    obs = load()
    if obs is None:
        return {"status": "NO OBSERVED DATA", "differences": 0}
    if obs.get("candles_csv") and not (PARITY_DIR / obs["candles_csv"]).exists():
        return {"status": "NO OBSERVED DATA", "differences": 0,
                "reason": f"{obs['candles_csv']} not found (TradingView exports are not committed)"}
    return compare(obs)
