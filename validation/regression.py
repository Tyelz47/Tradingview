"""Regression engine: compare the current reference model with a committed baseline.

A baseline is the canonical event stream + final structural state of a fixed,
deterministic corpus. `diff()` classifies differences as ADDED / REMOVED events,
TIMING / PRICE changes of the same event, CHANGED cases and STATE changes;
`classify()` marks the ones listed in the expected-changes manifest as EXPECTED.
Anything else is UNEXPECTED and fails the run.
"""
from __future__ import annotations

import fnmatch
import json
import subprocess
import types
from datetime import date

from validation import ROOT, VALIDATION_DIR
from validation.candles import random_walk
from validation.models.events import ONCE, canonical
from validation.models.ist import run_model
from validation.models.types import FvgSettings, LiqSettings, Settings

FORMAT = "ist-regression/1"
BASELINE = VALIDATION_DIR / "baselines" / "baseline.json"
MANIFEST = VALIDATION_DIR / "baselines" / "expected_changes.json"
CATEGORIES = ("ADDED", "REMOVED", "TIMING", "PRICE", "STATE", "CHANGED")


def corpus() -> list[tuple[str, Settings, list]]:
    """Fixed cases, independent of --seed and --mode, so baselines stay comparable."""
    return [
        ("walk-balanced-s11", Settings(), random_walk(1000, 11)),
        ("walk-aggressive-gaps-s12",
         Settings(liq=LiqSettings.preset("aggressive", tol_ticks=8), fvg=FvgSettings(k_tra=0.25)),
         random_walk(1000, 12, gap_prob=0.03)),
        ("walk-strict-min3-s13",
         Settings(liq=LiqSettings.preset("strict", min_touch=3, eq_memory=3), fvg=FvgSettings(k_rng=0.25, memory=10)),
         random_walk(1000, 13, max_step=8)),
    ]


def pine_version() -> str:
    import re
    head = (ROOT / "src" / "IST.pine").read_text(encoding="utf-8").splitlines()[2]
    m = re.search(r"(v[\w.\-]+)", head)
    return m.group(1) if m else "unknown"


def snapshot(label: str | None = None) -> dict:
    cases = {}
    for name, settings, candles in corpus():
        m = run_model(candles, settings)
        cases[name] = {"settings": settings.to_dict(), "bars": len(candles),
                       "events": [e.compact() for e in canonical(m.events)], "state": m.state()}
    return {"format": FORMAT, "label": label or f"oracle @ {pine_version()}", "created": date.today().isoformat(),
            "cases": cases}


def write_baseline(label: str | None = None) -> dict:
    snap = snapshot(label)
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    with open(BASELINE, "w", encoding="utf-8") as f:     # one event per line keeps git diffs readable
        f.write('{"format": %s, "label": %s, "created": %s, "cases": {\n' % (
            json.dumps(snap["format"]), json.dumps(snap["label"]), json.dumps(snap["created"])))
        for k, (name, case) in enumerate(snap["cases"].items()):
            f.write(f' {json.dumps(name)}: {{"settings": {json.dumps(case["settings"])}, "bars": {case["bars"]},\n')
            f.write('  "events": [\n' + ",\n".join("   " + json.dumps(e, separators=(",", ":")) for e in case["events"]) + "],\n")
            f.write(f'  "state": {json.dumps(case["state"], separators=(",", ":"))}}}' + (",\n" if k < len(snap["cases"]) - 1 else "\n"))
        f.write("}}\n")
    return snap


def load_baseline() -> dict | None:
    return json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else None


def _ident(e: list) -> tuple:
    bar, type_, d, sid, _ = e
    return (type_, d, sid) if type_ in ONCE else (type_, d, sid, bar)


def _flatten(state: dict) -> dict:
    out = {}
    for group, recs in state.items():
        if isinstance(recs, list):
            for r in recs:
                key = r.get("tag") or f"{r.get('side', r.get('dir', r.get('slot', '')))}:{r.get('id')}"
                for f, v in r.items():
                    out[f"{group}[{key}].{f}"] = v
        elif isinstance(recs, dict):
            for k, v in recs.items():
                for f, x in (v.items() if isinstance(v, dict) else [("", v)]):
                    out[f"{group}.{k}.{f}".rstrip(".")] = x
    return out


def diff(base: dict, cur: dict) -> list[dict]:
    out = []
    for name in sorted(set(base["cases"]) | set(cur["cases"])):
        if name not in base["cases"] or name not in cur["cases"]:
            out.append({"case": name, "category": "CHANGED", "what": "case added" if name in cur["cases"] else "case removed"})
            continue
        b, c = base["cases"][name], cur["cases"][name]
        if b["settings"] != c["settings"] or b["bars"] != c["bars"]:
            out.append({"case": name, "category": "CHANGED", "what": "case definition (settings/bars) changed"})
        be = {_ident(e): e for e in b["events"]}
        ce = {_ident(e): e for e in c["events"]}
        for k in be.keys() - ce.keys():
            out.append({"case": name, "category": "REMOVED", "type": be[k][1], "what": be[k], "before": be[k]})
        for k in ce.keys() - be.keys():
            out.append({"case": name, "category": "ADDED", "type": ce[k][1], "what": ce[k], "after": ce[k]})
        for k in be.keys() & ce.keys():
            x, y = be[k], ce[k]
            if x[0] != y[0]:
                out.append({"case": name, "category": "TIMING", "type": x[1], "what": k, "before": x[0], "after": y[0]})
            elif x[4] != y[4]:
                out.append({"case": name, "category": "PRICE", "type": x[1], "what": k, "before": x[4], "after": y[4]})
        bs, cs = _flatten(b["state"]), _flatten(c["state"])
        for k in sorted(bs.keys() | cs.keys()):
            if bs.get(k, "<absent>") != cs.get(k, "<absent>"):
                out.append({"case": name, "category": "STATE", "what": k, "before": bs.get(k, "<absent>"),
                            "after": cs.get(k, "<absent>")})
    return out


def load_manifest() -> list[dict]:
    if not MANIFEST.exists():
        return []
    return json.loads(MANIFEST.read_text(encoding="utf-8")).get("expected", [])


def classify(diffs: list[dict], manifest: list[dict]) -> list[dict]:
    """Mark each diff EXPECTED if a manifest entry matches (case/category/type/what are globs)."""
    for d in diffs:
        d["expected"] = None
        for entry in manifest:
            if all(fnmatch.fnmatch(str(d.get(f, "")), str(entry[f])) for f in ("case", "category", "type", "what") if f in entry):
                d["expected"] = entry.get("id", "manifest")
                break
    return diffs


def summarize(base: dict, cur: dict, diffs: list[dict]) -> dict:
    by_cat = {c: sum(d["category"] == c for d in diffs) for c in CATEGORIES}
    unexpected = [d for d in diffs if not d.get("expected")]
    return {"baseline": base.get("label"), "baseline_created": base.get("created"), "current": cur.get("label"),
            "cases": len(cur["cases"]), "events": sum(len(c["events"]) for c in cur["cases"].values()),
            "by_category": by_cat, "expected": len(diffs) - len(unexpected), "unexpected": len(unexpected),
            "unexpected_sample": unexpected[:15]}


# ── legacy models kept in git (tests/liq_model.py at a tag) ──
LEGACY_NAMES = {"CREATED": "{s}_CREATED", "TAKEN": "{s}_TAKEN", "SWEEP": "{s}_SWEEP", "BREAK": "{s}_BREAK",
                "DROPPED": "{s}_DROPPED_MEMORY", "EQ_CREATED": "{q}_CREATED", "EQ_TAKEN": "{q}_TAKEN",
                "EQ_DROPPED": "{q}_DROPPED_MEMORY"}


def load_legacy(ref: str) -> types.ModuleType | None:
    try:
        src = subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:tests/liq_model.py"], capture_output=True,
                             text=True, encoding="utf-8", check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    mod = types.ModuleType(f"legacy_{ref}")
    exec(compile(src, f"{ref}:tests/liq_model.py", "exec"), mod.__dict__)
    return mod


def legacy_events(mod, candles, liq: LiqSettings) -> list[tuple]:
    """Run a legacy liquidity model and express its events as (bar, type, sid time, price)."""
    e = mod.Engine(liq.left, liq.right, liq.k, tol_ticks=liq.tol_ticks, min_touch=liq.min_touch, memory=liq.memory,
                   eq_mem=liq.eq_memory)
    for k in candles:
        e.bar(k.open, k.high, k.low, k.close)
    out = []
    for t, kind, side, i, p in e.events:
        name = LEGACY_NAMES[kind].format(s="BSL" if side == "B" else "SSL", q="EQH" if side == "B" else "EQL")
        out.append((t, name, candles[i].time, p))
    return out
