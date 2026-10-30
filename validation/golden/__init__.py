"""Golden dataset: hand-labelled cases with expected events, structures and final states.

Cases are JSON files in golden/synthetic/ (built by hand to pin a rule) and
golden/nq/ (real NQ examples, labelled manually from TradingView). Format: README.md.
"""
from __future__ import annotations

import json
from pathlib import Path

from validation import VALIDATION_DIR
from validation.models.events import parse_local
from validation.models.types import Candle, Settings

GOLDEN_DIR = VALIDATION_DIR / "golden"
FIELDS_EVENT = ("bar", "type", "dir", "price", "sid_bar")


def load_cases() -> list[tuple[Path, dict]]:
    out = []
    for sub in ("synthetic", "nq", "human"):
        for p in sorted((GOLDEN_DIR / sub).glob("*.json")):
            out.append((p, json.loads(p.read_text(encoding="utf-8"))))
    return out


def candles_of(case: dict) -> list[Candle]:
    tz = case.get("timezone", "America/New_York")
    step = int(case.get("timeframe_sec", 60)) * 1000
    t = parse_local(case["start"], tz)
    rows = []
    warm = case.get("warmup")
    if warm:
        rows += [list(warm["ohlc"])] * int(warm["bars"])
    rows += case["candles"]
    out = []
    for r in rows:
        if isinstance(r[0], str):                       # ["2026-10-27T09:41", o, h, l, c]
            t = parse_local(r[0], tz)
            r = r[1:]
        out.append(Candle(t, *map(float, r)))
        t += step
    return out


def settings_of(case: dict) -> Settings:
    d = dict(case.get("settings", {}))
    d.setdefault("tick", case.get("tick_size", 0.25))
    return Settings.from_dict(d)


def _records(m, kind: str) -> list[dict]:
    """State records of one kind, with bar-based helper fields for matching."""
    t2b = {c.time: i for i, c in enumerate(m.candles)}
    st = m.state()
    recs = {"fvg": st.get("fvg", []), "liq": st.get("levels", []), "eq": st.get("clusters", []),
            "session": st.get("sessions", []), "level": st.get("ref_levels", [])}[kind]
    out = []
    for r in recs:
        r = dict(r)
        if "id" in r:
            r["id_bar"] = t2b.get(r["id"])
        if "members" in r:
            r["members_bars"] = [t2b.get(x) for x in r["members"]]
        out.append(r)
    return out


def _check_records(m, items: list[dict], label: str) -> list[str]:
    fails = []
    for it in items:
        recs = [r for r in _records(m, it["kind"]) if all(r.get(k) == v for k, v in it.get("match", {}).items())]
        if len(recs) != 1:
            fails.append(f"{label} {it['kind']} {it.get('match')}: {len(recs)} matching records")
            continue
        for k, v in it.get("expect", {}).items():
            if recs[0].get(k) != v:
                fails.append(f"{label} {it['kind']} {it.get('match')}: {k} = {recs[0].get(k)!r}, expected {v!r}")
    return fails


def run_case(case: dict):
    """Run one case through the oracle (all invariants checked). Returns (model, failures)."""
    from validation.invariants import run_checked
    m = run_checked(candles_of(case), settings_of(case))
    exp = case.get("expected", {})
    fails = []
    t2b = {c.time: i for i, c in enumerate(m.candles)}
    actual = [{"bar": e.bar, "type": e.type, "dir": e.dir, "price": e.price, "sid_bar": t2b.get(e.sid, e.sid)}
              for e in m.canonical_events()]
    want = exp.get("events", [])
    used = set()
    for w in want:
        hit = next((i for i, a in enumerate(actual) if i not in used and all(a[k] == w[k] for k in w if k in FIELDS_EVENT)), None)
        if hit is None:
            fails.append(f"missing event {w}")
        else:
            used.add(hit)
    if exp.get("events_match", "exact") == "exact":
        types = set(exp.get("event_types") or {w["type"] for w in want})
        extra = [a for i, a in enumerate(actual) if i not in used and a["type"] in types]
        fails += [f"unexpected event {a}" for a in extra]
    fails += _check_records(m, exp.get("structures", []), "structure")
    fails += _check_records(m, exp.get("final_states", []), "final state")
    return m, fails
