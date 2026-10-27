"""Pine / Python parity: compare what TradingView showed with what the oracle expects.

Nothing here talks to TradingView. You copy observations by hand into
validation/parity/pine_observed.json (format: pine_observed.example.json): the
chart's candles (inline or a TradingView 'Export chart data' CSV), the settings
used, and the events / states read from the IST debug table or alerts.
"""
from __future__ import annotations

import json
from pathlib import Path

from validation import VALIDATION_DIR
from validation.candles import load_tradingview_csv
from validation.models.events import ONCE, parse_local, parse_pine_line
from validation.models.ist import run_model
from validation.models.types import Candle, Settings

PARITY_DIR = VALIDATION_DIR / "parity"
OBSERVED = PARITY_DIR / "pine_observed.json"


def load(path: Path = OBSERVED) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def candles_of(obs: dict, base: Path) -> list[Candle]:
    tz = obs.get("timezone", "America/New_York")
    if obs.get("candles_csv"):
        return load_tradingview_csv(base / obs["candles_csv"], tz)
    return [Candle(parse_local(r[0], tz) if isinstance(r[0], str) else int(r[0]), *map(float, r[1:5]))
            for r in obs["candles"]]


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
    """Every observed event must match an oracle event (type, direction, id; then time and price).
    With "complete": true, every oracle event of the observed types inside the window must
    also have been observed."""
    tz = obs.get("timezone", "America/New_York")
    settings = Settings.from_dict({**obs.get("settings", {}), "tick": obs.get("tick_size", 0.25)})
    candles = candles_of(obs, base)
    m = run_model(candles, settings)
    lo = parse_local(obs["window"]["from"], tz) if obs.get("window") else None
    hi = parse_local(obs["window"]["to"], tz) if obs.get("window") else None
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
            "state_differences": states,
            "differences": len(missing) + len(mismatched) + len(extra) + len(states)}


def run() -> dict:
    obs = load()
    if obs is None:
        return {"status": "NO OBSERVED DATA", "differences": 0}
    return compare(obs)
