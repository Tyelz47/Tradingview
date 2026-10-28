"""python -m validation.parity EXPORT.csv [--preset balanced] [--from T] [--to T]
python -m validation.parity --manual validation/parity/manual_observed.txt [--preset balanced]
python -m validation.parity --capture validation/parity/pine_capture.csv

Full CSV bar-by-bar parity: builds validation/parity/pine_observed.json from a TradingView
'Export chart data' CSV (IST Debug mode ON) and prints the Pine ↔ oracle comparison.
Event lines and states already in pine_observed.json are kept.
Manual event parity (free plan): compares the settings, counts and events copied from
the IST debug table and Pine Logs (format: parity/manual_observed_template.txt).
Bounded Pine-Log parity (free plan): rebuilds the candles of an IST "Parity capture"
pasted from Pine Logs and compares every bar after the warm-up, and its events.
Exit 0 = no difference, 1 = differences, 2 = unusable input.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from validation import parity
from validation.parity import capture, manual
from validation.candles import load_tradingview_export
from validation.models.types import PRESETS
from validation.validation_agent import pine_build


def build(csv_path: Path, preset: str, lo: str | None, hi: str | None) -> dict:
    obs = parity.load() or {"format": "ist-parity/1"}
    obs.pop("about", None)
    csv_path = csv_path.resolve()
    try:
        ref = csv_path.relative_to(parity.PARITY_DIR.resolve()).as_posix()
    except ValueError:
        ref = str(csv_path)
    tz = obs.setdefault("timezone", "America/New_York")
    _, rows = load_tradingview_export(csv_path, tz)
    settings = obs.get("settings", {})
    settings["liq"] = {**settings.get("liq", {}), "preset": preset}
    obs.update({"build": pine_build(), "candles_csv": ref, "tick_size": parity.mintick(rows) or obs.get("tick_size", 0.25),
                "settings": settings})
    if lo or hi:
        obs["window"] = {"from": lo, "to": hi}
    else:
        obs.pop("window", None)
    return obs


def show(r: dict, preset: str) -> None:
    dw = r["data_window"]
    if dw is None:
        print("  no IST Data Window columns in this export (was IST on the chart?): events only")
    else:
        left, right, k, w = PRESETS[preset]
        print(f"  export {dw['first_bar']} → {dw['last_bar']} · {r['bars']} bars · {dw['bars']} compared "
              f"(the last bar is never compared: it may still be open)")
        print(f"  liquidity preset {preset} (left {left} · right {right} · k {k} · dominance {w}) · other settings from pine_observed.json\n")
        print(f"  {'':<14}{'Pine (export)':<48}oracle")
        p, o = dw["totals"]["pine"], dw["totals"]["oracle"]
        for side in ("bsl", "ssl"):
            f = lambda d: f"{d['pivots']} pivots · {d['pass']} PASS · {d['reject_or_warmup']} reject/warm-up"
            g = lambda d: f"{d['sweep']} sweep · {d['break']} break"
            print(f"  {side.upper() + ' swings':<14}{f(p[side]):<48}{f(o[side])}")
            print(f"  {side.upper() + ' take bars':<14}{g(p[side]):<48}{g(o[side])}")
        f = lambda d: f"{d['bull']} bull · {d['bear']} bear · {d['rejected']} rejected"
        print(f"  {'FVG':<14}{f(p['fvg']):<48}{f(o['fvg'])}")
        print("\n  The Pine swing counts must equal IST debug rows 22–23 (PASS, REJECT + warm-up); if they do not,"
              "\n  the export does not start at the indicator's first bar and early differences are expected.")
        for d in dw["first"]:
            print(f"    {d['time']}  {d['series']:<14} Pine {d['pine']}  oracle {d['oracle']}")
        if dw["differences"] > len(dw["first"]):
            print(f"    … {dw['differences'] - len(dw['first'])} more; per series: {dw['by_series']}")
    if r["observed"]:
        print(f"  events: {r['matched']} / {r['observed']} match")
    for k in ("not_in_oracle", "mismatched", "not_observed_in_pine", "state_differences"):
        for d in r[k][:10]:
            print(f"    {k}: {d}")
    kind = "FULL CSV BAR-BY-BAR PARITY" if dw else "EVENT PARITY (no Data Window columns)"
    print(f"\n  {kind}: {'PASS' if r['differences'] == 0 else 'FAIL'} — {r['differences']} differences "
          f"(observed TradingView data, build {r['build']})")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m validation.parity", description=__doc__.split("\n\n")[1])
    ap.add_argument("csv", type=Path, nargs="?", help="TradingView 'Export chart data' CSV (IST Debug mode ON)")
    ap.add_argument("--manual", type=Path, help="manual observation file (free plan), e.g. validation/parity/manual_observed.txt")
    ap.add_argument("--capture", type=Path, help="IST Parity capture: the Pine Logs file TradingView saves (Date,Message CSV) or pasted text")
    ap.add_argument("--preset", choices=[*sorted(PRESETS), "custom"], help="liquidity preset used on the chart (default balanced)")
    ap.add_argument("--from", dest="lo", help="compare from this New York time, e.g. 2026-10-27T09:30")
    ap.add_argument("--to", dest="hi", help="compare up to this New York time")
    a = ap.parse_args(argv)
    if sum(x is not None for x in (a.csv, a.manual, a.capture)) != 1:
        ap.error("give one of: an export CSV, --manual FILE, --capture FILE")
    if (a.manual or a.capture) and (a.lo or a.hi):
        ap.error("--from / --to apply to the CSV export only")
    if a.csv and a.preset == "custom":
        ap.error("--preset custom is for --manual and --capture")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")      # Windows consoles default to cp1252
    if a.capture:
        try:
            if not a.capture.exists():
                raise OSError(f"{a.capture} not found (paste the Pine Logs of an IST Parity capture into it)")
            r = capture.run(a.capture, a.preset)
        except (OSError, ValueError) as e:
            print(f"unusable capture: {e}", file=sys.stderr)
            return 2
        capture.show(r, pine_build())
        return 0 if r["differences"] == 0 else 1
    if a.manual:
        try:
            if not a.manual.exists():
                raise OSError(f"{a.manual} not found (copy validation/parity/manual_observed_template.txt)")
            r = manual.run(a.manual, a.preset)
        except (OSError, ValueError) as e:
            print(f"unusable manual input: {e}", file=sys.stderr)
            return 2
        manual.show(r, pine_build())
        return 0 if r["differences"] == 0 else 1
    a.preset = a.preset or "balanced"
    try:
        obs = build(a.csv, a.preset, a.lo, a.hi)
        r = parity.compare(obs)
    except (OSError, KeyError, ValueError) as e:
        print(f"unusable export: {e}", file=sys.stderr)
        return 2
    parity.OBSERVED.write_text(json.dumps(obs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {parity.OBSERVED.relative_to(parity.PARITY_DIR.parent.parent).as_posix()}")
    show(r, a.preset)
    return 0 if r["differences"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
