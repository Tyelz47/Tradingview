"""IST validation agent — one command, one honest answer.

    python validation/validation_agent.py [--mode quick|full|deep] [--phase 1|2|lrl|htf|cisd|disp|ifvg|all]
                                          [--seed N] [--report PATH] [--verbose] [--update-baseline]
    python -m validation  (same options)

Runs the whole suite (static Pine checks, deterministic scenarios, invariants and
their negative tests, Hypothesis properties, the stateful machine, long random
walks, regression, golden, parity), writes validation/reports/VALIDATION_REPORT.md
and exits 0 only if every automated check passed. It validates the REFERENCE MODEL
and static properties of the Pine source; it never claims anything about TradingView.
"""
from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

if __package__ in (None, ""):                         # run as a script: make `validation` importable
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from validation import ROOT, VALIDATION_DIR, __version__  # noqa: E402

REPORT = VALIDATION_DIR / "reports" / "VALIDATION_REPORT.md"
EXIT_PASS, EXIT_FAIL, EXIT_ERROR = 0, 1, 2

SECTIONS = [  # key, report title, group
    ("static", "Static checks on src/IST.pine", "STATIC"),
    ("phase1.fvg", "FVG detection & thresholds", "PHASE 1"),
    ("phase1.lifecycle", "FVG lifecycle & memory", "PHASE 1"),
    ("phase1.sessions", "Sessions", "PHASE 1"),
    ("phase1.levels", "Reference levels (chart-side logic)", "PHASE 1"),
    ("phase2.swing", "Swings & significance", "PHASE 2"),
    ("phase2.sweeps", "Taken / sweep / break", "PHASE 2"),
    ("phase2.eq", "EQH / EQL clusters", "PHASE 2"),
    ("events", "Event stream", "COMMON"),
    ("invariants", "Invariant detectors (negative tests)", "COMMON"),
    ("property", "Property tests (Hypothesis)", "FUZZ"),
    ("stateful", "Stateful machine", "FUZZ"),
    ("longwalk", "Long random walks", "FUZZ"),
    ("regression", "Regression", "COMMON"),
    ("golden", "Golden dataset", "COMMON"),
    ("parity", "Pine / Python parity", "COMMON"),
    ("lrl", "LRL detection (oracle + Pine v0.7.1-dev)", "LRL"),
    ("htf", "HTF FVG (oracle + Pine v0.6.2-dev)", "HTF"),
    ("cisd", "CISD (oracle + Pine v0.7.1-dev)", "CISD"),
    ("disp", "Displacement (oracle + Pine v0.8.0-dev)", "DISP"),
    ("ifvg", "IFVG (oracle + Pine v0.9.0-dev)", "IFVG"),
    ("research.lrl", "LRL research study (no indicator change)", "RESEARCH"),
    ("research.cisd", "CISD research study (no indicator change)", "RESEARCH"),
    ("research.disp", "Displacement study (no indicator change)", "RESEARCH"),
    ("research.ifvg", "IFVG study (no indicator change)", "RESEARCH"),
]
SCENARIO_SECTIONS = {"phase1.fvg", "phase1.lifecycle", "phase1.sessions", "phase1.levels", "phase2.swing",
                     "phase2.sweeps", "phase2.eq", "events"}
MANUAL = [
    ("Pine compilation in TradingView (L00)", "PENDING — MANUAL / TRADINGVIEW REQUIRED"),
    ("Pine runtime behaviour on real NQ data", "PENDING — MANUAL / TRADINGVIEW REQUIRED"),
    ("Pine ↔ Python runtime parity", None),
    ("request.security values (PDH/PDL/PWH/PWL) and the Daily-bar definition (G-V1…G-V5)",
     "PENDING — MANUAL / TRADINGVIEW REQUIRED"),
    ("Pine time() session membership", "PENDING — MANUAL / TRADINGVIEW REQUIRED"),
    ("Graphical rendering (lines, boxes, labels, caps, anchors)", "PENDING — MANUAL / TRADINGVIEW REQUIRED"),
    ("Pine object limits and execution time under real runtime (L22–L25)", "PENDING — MANUAL / TRADINGVIEW REQUIRED"),
    ("Live mode / realtime rollback (L15)", "PENDING — MANUAL / TRADINGVIEW REQUIRED"),
    ("Alert delivery infrastructure", "PENDING — MANUAL / TRADINGVIEW REQUIRED"),
]


class Collector:
    """pytest plugin: per-test section, spec ids, outcome, duration and message."""

    def __init__(self):
        self.meta: dict = {}
        self.res: dict = {}
        self.collect_errors: list = []

    def pytest_collection_modifyitems(self, session, config, items):
        for it in items:
            sec = it.get_closest_marker("section")
            specs = sorted({a for mk in it.iter_markers("spec") for a in mk.args})
            self.meta[it.nodeid] = {"section": sec.args[0] if sec else "other", "specs": specs, "name": it.name}

    def pytest_collectreport(self, report):
        if report.failed:
            self.collect_errors.append((report.nodeid, str(report.longrepr)[-1500:]))

    def pytest_runtest_logreport(self, report):
        r = self.res.setdefault(report.nodeid, {"outcome": "passed", "duration": 0.0, "message": ""})
        r["duration"] += report.duration
        if report.failed:
            r["outcome"] = "failed" if report.when == "call" else "error"
            r["message"] = (report.longreprtext or "")[-2500:]
        elif report.skipped and r["outcome"] == "passed":
            r["outcome"] = "skipped"
            lr = report.longrepr
            r["message"] = lr[2] if isinstance(lr, tuple) else str(lr)


def git(*args) -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "n/a"


def pine_build() -> str:
    m = re.search(r"\(IST\) · (v[\w.\-]+)", (ROOT / "src" / "IST.pine").read_text(encoding="utf-8")[:600])
    return m.group(1) if m else "unknown"


def l_tests() -> list[tuple[str, str, str]]:
    """(id, name, status) of each TradingView L-test; the status is what the user recorded."""
    p = ROOT / "docs" / "TESTS_PHASE2.md"
    if not p.exists():
        return []
    rows = re.findall(r"^\| (L\d\d) \| ([^|]+) \|.*\| ([^|]+?) \|\s*$", p.read_text(encoding="utf-8"), re.M)
    return [(lid, name.strip(), st.strip()) for lid, name, st in rows]


def recorded(status: str) -> str:
    """PASS / FAIL as recorded by the user, else PENDING. Never set by this agent."""
    return next((k for k in ("PASS", "FAIL") if status.lstrip("* ").startswith(k)), "PENDING")


def parse_args(argv):
    ap = argparse.ArgumentParser(prog="validation_agent", description=__doc__.split("\n\n")[0])
    ap.add_argument("--mode", choices=("quick", "full", "deep"), default="full",
                    help="quick: every change · full (default): before TradingView · deep: before a version freeze")
    ap.add_argument("--phase", choices=("1", "2", "lrl", "htf", "cisd", "disp", "ifvg", "all"), default="all")
    ap.add_argument("--all", action="store_const", const="all", dest="phase", help="same as --phase all")
    ap.add_argument("--seed", type=int, default=20261027, help="Hypothesis seed (walks and corpus are fixed)")
    ap.add_argument("--report", type=Path, default=REPORT)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--update-baseline", action="store_true",
                    help="rewrite validation/baselines/baseline.json from the current model, then exit")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    os.environ["IST_VAL_MODE"] = args.mode
    os.environ["IST_VAL_SEED"] = str(args.seed)
    if args.update_baseline:
        from validation import regression
        snap = regression.write_baseline()
        print(f"baseline written: {regression.BASELINE} ({snap['label']}, {len(snap['cases'])} cases, "
              f"{sum(len(c['events']) for c in snap['cases'].values())} events). Review `git diff` before committing.")
        return EXIT_PASS
    from importlib.metadata import PackageNotFoundError, version
    try:
        versions = (version("pytest"), version("hypothesis"))
    except PackageNotFoundError as e:
        print(f"missing dependency: {e}. Install with: python -m pip install -r requirements-dev.txt")
        return EXIT_ERROR
    import pytest                                      # hypothesis is NOT imported here: pytest must load it first

    from validation import artifacts, stats
    stats.reset()
    shutil.rmtree(artifacts.FAIL_DIR, ignore_errors=True)
    marker = {"1": "phase1 or common", "2": "phase2 or common", "lrl": "lrl or common", "htf": "htf or common",
              "cisd": "cisd or common", "disp": "disp or common", "ifvg": "ifvg or common"}.get(args.phase)
    pargs = [str(VALIDATION_DIR / "tests"), str(VALIDATION_DIR / "fuzz"), "-p", "no:cacheprovider",
             "--rootdir", str(ROOT), "-o", "addopts=", f"--hypothesis-seed={args.seed}",
             "-v" if args.verbose else "-q", "--tb=short" if args.verbose else "--tb=line", "-W", "ignore::DeprecationWarning"]
    if marker:
        pargs += ["-m", marker]
    col = Collector()
    t0 = time.time()
    print(f"IST validation agent · mode {args.mode} · phase {args.phase} · seed {args.seed}")
    code = pytest.main(pargs, plugins=[col])
    elapsed = time.time() - t0
    if code not in (0, 1, 5):
        print(f"pytest stopped with code {code} (usage or internal error)")
        return EXIT_ERROR

    report, passed = build_report(args, col, elapsed, *versions)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print_summary(col, passed, args, elapsed)
    return EXIT_PASS if passed else EXIT_FAIL


# ── report ──
def _by_section(col):
    out = {}
    for nid, meta in col.meta.items():
        r = col.res.get(nid, {"outcome": "not run", "duration": 0.0, "message": ""})
        out.setdefault(meta["section"], []).append((nid, meta, r))
    return out


def _count(rows):
    c = {"passed": 0, "failed": 0, "error": 0, "skipped": 0, "not run": 0}
    for _, _, r in rows:
        c[r["outcome"]] = c.get(r["outcome"], 0) + 1
    return c


def _verdict(c):
    if c["failed"] or c["error"]:
        return "**FAIL**"
    if c["passed"] == 0 and c["skipped"]:
        return "SKIPPED"
    return "PASS" if c["passed"] else "—"


def build_report(args, col, elapsed, pytest_v, hyp_v):
    from validation import stats
    from validation.artifacts import list_failures
    from validation.invariants import REGISTRY

    secs = _by_section(col)
    all_rows = [x for rows in secs.values() for x in rows]
    tot = _count(all_rows)
    failed = tot["failed"] + tot["error"] + len(col.collect_errors)
    passed = failed == 0 and tot["passed"] > 0
    ready = passed and args.mode in ("full", "deep") and args.phase == "all"
    status = ("READY FOR TRADINGVIEW VALIDATION" if ready else
              "NOT READY — quick mode or a partial phase only; run `--mode full` before TradingView" if passed else
              "NOT READY — automated failures below")
    dirty = git("status", "--porcelain")
    L = []
    w = L.append
    w("# IST · Validation report\n")
    w(f"**AUTOMATED LOGIC VALIDATION: {'PASS' if passed else 'FAIL'}**  ")
    w(f"**FINAL STATUS: {status}**\n")
    w("> This report covers the Python reference model (oracle) of the specification and static checks of the "
      "Pine source text. **It does not compile or run Pine and it does not test TradingView.** The TradingView "
      "items show only results the user recorded in docs/TESTS_PHASE2.md or observed data supplied in "
      "validation/parity/; everything else stays PENDING.\n")
    w("## Build\n")
    w("| | |\n|---|---|")
    w(f"| Pine build | {pine_build()} (src/IST.pine header) |")
    w(f"| Commit | {git('rev-parse', '--short', 'HEAD')} on `{git('rev-parse', '--abbrev-ref', 'HEAD')}`"
      f"{' · **uncommitted changes present**' if dirty and dirty != 'n/a' else ''} |")
    w(f"| Date | {datetime.now().strftime('%Y-%m-%d %H:%M')} |")
    w(f"| Validator | validation {__version__} · Python {platform.python_version()} · pytest {pytest_v} · hypothesis {hyp_v} |")
    w(f"| Mode · phase · seed | {args.mode} · {args.phase} · {args.seed} |")
    w(f"| Runtime | {elapsed:.1f} s |\n")

    w("## Summary\n")
    w("| Group | Section | Result | Passed | Failed | Skipped | Time |\n|---|---|---|---|---|---|---|")
    known = {k for k, _, _ in SECTIONS}
    for key, title, group in SECTIONS + [(k, k, "OTHER") for k in sorted(set(secs) - known)]:
        rows = secs.get(key, [])
        if not rows:
            continue
        c = _count(rows)
        t = sum(r["duration"] for _, _, r in rows)
        w(f"| {group} | {title} | {_verdict(c)} | {c['passed']} | {c['failed'] + c['error']} | {c['skipped']} | {t:.1f} s |")
    w(f"| | **All** | {'**PASS**' if passed else '**FAIL**'} | {tot['passed']} | {tot['failed'] + tot['error']} | {tot['skipped']} | {elapsed:.1f} s |\n")

    st = stats.RESULTS.get("static", {})
    if st:
        ok = sum(1 for v in st.values() if v["ok"])
        w(f"## Static checks on src/IST.pine — {ok} / {len(st)} PASS\n")
        w("Text-level checks of the production source; they do not compile it.\n")
        w("| ID | Check | Result | Detail |\n|---|---|---|---|")
        for cid in sorted(st):
            v = st[cid]
            res = "PASS" if v["ok"] else ("SKIPPED" if v["ok"] is None else "**FAIL**")
            w(f"| {cid} | {v['name']} | {res} | {v['detail'][:220].replace('|', '/')} |")
        w("")

    sc = [x for k in SCENARIO_SECTIONS for x in secs.get(k, [])]
    c = _count(sc)
    w(f"## Deterministic scenarios — {c['passed']} / {len(sc)} PASS\n")
    for key, title, group in SECTIONS:
        if key in SCENARIO_SECTIONS and secs.get(key):
            cc = _count(secs[key])
            w(f"* {group} · {title}: {cc['passed']} / {len(secs[key])}")
    w("")

    w("## Property, stateful and long-walk testing\n")
    w(f"* Property tests: {stats.COUNTS['property.examples']} generated examples (valid, tick-aligned OHLC) — "
      f"{_verdict(_count(secs.get('property', [])))}")
    w(f"* Stateful machine: {stats.COUNTS['stateful.sequences']} sequences, {stats.COUNTS['stateful.steps']} steps, "
      f"{stats.COUNTS['stateful.bars']} bars — {_verdict(_count(secs.get('stateful', [])))}")
    w(f"* Long random walks: {stats.COUNTS['longwalk.runs']} runs, {stats.COUNTS['longwalk.bars']} bars, every module, "
      f"invariants every bar (full sweep every 25) — {_verdict(_count(secs.get('longwalk', [])))}")
    w(f"* Bars checked by the invariant monitor in total: {stats.COUNTS['bars.checked']}")
    w(f"* Coverage: {stats.COUNTS['lrl.confirmed']} LRLs confirmed, {stats.COUNTS['htf.created']} HTF FVGs created, "
      f"{stats.COUNTS['htf.seeded']} seeded (reload property), {stats.COUNTS['cisd.confirmed']} CISDs confirmed, "
      f"{stats.COUNTS['disp.confirmed']} displacements, {stats.COUNTS['ifvg.inverted']} IFVGs\n")
    sel = stats.RESULTS.get("selectivity")
    if sel:
        w("Reaction-floor selectivity on the walks (synthetic noise, NOT NQ; presets unchanged):\n")
        w("| Run | Side | Pivots | PASS | REJECT | Reject % |\n|---|---|---|---|---|---|")
        for s in sel:
            w(f"| {s['run']} ({s['bars']} bars) | {s['side']} | {s['pivots']} | {s['pass']} | {s['reject']} | {s['reject_pct']} |")
        w("")

    det = stats.RESULTS.get("detectors", set())
    exercised = sum(1 for k in REGISTRY if stats.INV_CHECKS[k] > 0)
    inv_fail = {nid for nid, m, r in all_rows if r["outcome"] in ("failed", "error") and "[INV-" in r["message"]}
    w(f"## Invariants — {exercised} / {len(REGISTRY)} exercised and never violated · {len(det)} / {len(REGISTRY)} detectors proven\n")
    if inv_fail:
        w(f"**Violations reported by {len(inv_fail)} test(s): see Failures.**\n")
    w("| ID | Invariant | Evaluations | Detector proven |\n|---|---|---|---|")
    for k, v in REGISTRY.items():
        w(f"| {k} | {v.text} | {stats.INV_CHECKS[k]} | {'yes' if k in det else '**no**'} |")
    w("")

    rg = stats.RESULTS.get("regression")
    w("## Regression\n")
    if rg:
        w(f"* Baseline: **{rg['baseline']}** (created {rg['baseline_created']}) — {rg['cases']} cases, {rg['events']} events")
        w(f"* Differences by category: " + ", ".join(f"{k} {v}" for k, v in rg["by_category"].items()))
        w(f"* Expected (manifest): {rg['expected']} · **Unexpected: {rg['unexpected']}**")
        for d in rg["unexpected_sample"][:10]:
            w(f"  * {d}")
    else:
        w("* Baseline comparison did not run (see the regression section in the summary).")
    for ref, msg in sorted(stats.RESULTS.get("legacy", {}).items()):
        w(f"* Legacy model `{ref}:tests/liq_model.py` vs oracle: {msg}")
    w("")

    gd = stats.RESULTS.get("golden", {})
    ok = sum(1 for v in gd.values() if v["ok"])
    real = sum(1 for v in gd.values() if v["source"] != "synthetic")
    w(f"## Golden dataset — {ok} / {len(gd)} PASS ({len(gd) - real} synthetic, {real} real NQ)\n")
    for cid, v in sorted(gd.items()):
        w(f"* {cid} ({v['source']}): {'PASS' if v['ok'] else '**FAIL** ' + '; '.join(v['failures'][:3])}")
    w("")

    from validation.parity import SERIES, capture as cap_parity, manual as man_parity
    par = stats.RESULTS.get("parity", {"status": "NOT RUN"})
    dw = par.get("data_window")
    if par["status"] in ("NO OBSERVED DATA", "NOT RUN"):
        parity_txt = ("PENDING — no observed TradingView data (validation/parity/pine_observed.json)"
                      + (f": {par['reason']}" if par.get("reason") else ""))
    else:
        parts = ([f"Data Window {dw['bars']} bars × {len(SERIES)} series"] if dw else []) + \
                ([f"{par['matched']} / {par['observed']} observed events match"] if par["observed"] else [])
        parity_txt = (f"{'PASS' if par['differences'] == 0 else '**FAIL**'} — {', '.join(parts)}; "
                      f"{par['differences']} differences (observed TradingView data, build {par['build']})")
    mp = stats.RESULTS.get("manual_parity", {"status": "NOT RUN"})
    if mp["status"] in ("NO OBSERVED DATA", "NOT RUN"):
        manual_txt = "PENDING — no validation/parity/manual_observed.txt" + (f" ({mp['reason']})" if mp.get("reason") else "")
    else:
        manual_txt = man_parity.verdict(mp).split(": ", 1)[1].replace("FAIL", "**FAIL**", 1)
    cp = stats.RESULTS.get("capture_parity", {"status": "NOT RUN"})
    if cp["status"] in ("NO OBSERVED DATA", "NOT RUN"):
        capture_txt = "PENDING — no validation/parity/pine_capture*.csv or .txt"
    else:
        capture_txt = (cap_parity.verdict(cp).split(": ", 1)[1].replace("FAIL", "**FAIL**", 1)
                       + f"; {cp['file']} ({cp['source']}), window {cp['window']} New York, first {cp['warmup']} "
                         f"bars = warm-up" + "".join(f"; {n.strip()}" for n in cp["notes"]))
    w("## Pine / Python parity\n\nThree levels, never mixed:\n"
      "* FULL CSV BAR-BY-BAR PARITY compares every bar of a Data Window export (paid plan).\n"
      "* BOUNDED PINE-LOG BAR-BY-BAR PARITY compares every bar of one captured window after its warm-up, and the "
      "events of structures born inside it; nothing before the window.\n"
      "* MANUAL EVENT PARITY compares only the settings, counts and events copied by hand.\n\n"
      "A bounded or manual PASS is not full-history parity.\n")
    w(f"* **FULL CSV BAR-BY-BAR PARITY** (Data Window export): {parity_txt}")
    w(f"* **BOUNDED PINE-LOG BAR-BY-BAR PARITY** (Parity capture): {capture_txt}")
    w(f"* **MANUAL EVENT PARITY** (copied by hand): {manual_txt}")
    for res, mod in ((cp, cap_parity), (mp, man_parity)):
        if res["status"] == "COMPARED":
            for c in [c for c in res["checks"] if c["status"] == mod.DIFF][:25]:
                w(f"  * DIFFERENCE ({res['mode'].lower()}) {c['text']}")
    if dw:
        w(f"* export {dw['first_bar']} → {dw['last_bar']} (New York); the last exported bar is never compared\n")
        w("| Counts over the whole export | Pine (export) | oracle |\n|---|---|---|")
        tp, to = dw["totals"]["pine"], dw["totals"]["oracle"]
        swings = lambda d: f"{d['pivots']} pivots · {d['pass']} PASS · {d['reject_or_warmup']} reject/warm-up"
        takes = lambda d: f"{d['sweep']} sweep · {d['break']} break"
        fvgs = lambda d: f"{d['bull']} bull · {d['bear']} bear · {d['rejected']} rejected"
        for side in ("bsl", "ssl"):
            w(f"| {side.upper()} swings | {swings(tp[side])} | {swings(to[side])} |")
            w(f"| {side.upper()} take bars | {takes(tp[side])} | {takes(to[side])} |")
        w(f"| FVG | {fvgs(tp['fvg'])} | {fvgs(to['fvg'])} |\n")
        for d in dw["first"]:
            w(f"* {d['time']} `{d['series']}`: Pine {d['pine']} · oracle {d['oracle']}")
    w("")

    w("## Performance\n")
    w("| Section | Time |\n|---|---|")
    for key, title, _ in SECTIONS:
        if secs.get(key):
            w(f"| {title} | {sum(r['duration'] for _, _, r in secs[key]):.2f} s |")
    w(f"| **Total wall time** | {elapsed:.1f} s |\n")
    w("Peak logical records seen (the budgets are the Pine defaults; small test memories are also exercised):\n")
    for k, v in sorted(stats.PEAKS.items()):
        w(f"* {k}: {v}")
    w("* Budgets: FVG 50 per direction (10–200) · liquidity 100 per side (20–250) · clusters 25 per side\n")

    lt = l_tests()
    if lt:
        cover = {}
        for nid, meta, r in all_rows:
            for sp in meta["specs"]:
                cover.setdefault(sp, []).append(r["outcome"])
        w("## TradingView L-tests — model coverage of the logic\n")
        w("Model coverage means the *rule* behind the test is checked here. The TradingView column is what the "
          "user recorded in docs/TESTS_PHASE2.md; this agent never sets it.\n")
        w("| L-test | Name | Automated tests (logic) | Model result | TradingView (user) |\n|---|---|---|---|---|")
        for lid, name, st_ in lt:
            o = cover.get(lid, [])
            res = "—" if not o else ("**FAIL**" if any(x in ("failed", "error") for x in o) else "PASS")
            w(f"| {lid} | {name} | {len(o) or '—'} | {res} | {recorded(st_)} |")
        w("")

    w("## TradingView — MANUAL / TRADINGVIEW REQUIRED\n")
    w("| Item | Status |\n|---|---|")
    user = {lid: st_ for lid, _, st_ in lt}
    for item, st_ in MANUAL:
        lid = re.search(r"\((L\d\d)\)", item)
        if lid and recorded(user.get(lid.group(1), "")) != "PENDING":
            st_ = f"{user[lid.group(1)]} (recorded by the user in docs/TESTS_PHASE2.md)"
        w(f"| {item} | {st_ or f'full CSV: {parity_txt} · bounded Pine-Log: {capture_txt} · manual event: {manual_txt}'} |")
    w("")

    fails = [(nid, m, r) for nid, m, r in all_rows if r["outcome"] in ("failed", "error")]
    if fails or col.collect_errors:
        w(f"## Failures ({len(fails) + len(col.collect_errors)})\n")
        for nid, m, r in fails:
            inv = re.search(r"\[(INV-[A-Z]+-\d+)\]", r["message"])
            w(f"### {nid}\n")
            if inv:
                w(f"* **Invariant violated:** `{inv.group(1)}` — {REGISTRY[inv.group(1)].text}")
            w("```\n" + r["message"].strip()[-1800:] + "\n```\n")
        for nid, msg in col.collect_errors:
            w(f"### collection error: {nid}\n```\n{msg}\n```\n")
        arts = list_failures()
        if arts:
            w("Reproducible cases saved:\n")
            for p in arts:
                w(f"* `{p.relative_to(ROOT).as_posix()}` — reproduce: `python -m validation.reproduce {p.relative_to(ROOT).as_posix()}`")
            w("")
    skipped = [(nid, r) for nid, m, r in all_rows if r["outcome"] == "skipped"]
    if skipped:
        w("## Skipped\n")
        for nid, r in skipped:
            w(f"* {nid}: {r['message']}")
        w("")
    w(f"---\nGenerated by `python validation/validation_agent.py --mode {args.mode}`.")
    return "\n".join(L) + "\n", passed


def print_summary(col, passed, args, elapsed):
    secs = _by_section(col)
    print("\n" + "=" * 72)
    for key, title, group in SECTIONS:
        if secs.get(key):
            c = _count(secs[key])
            print(f"  {group:<8} {title:<40} {_verdict(c).strip('*'):<8} {c['passed']}/{len(secs[key])}")
    print("=" * 72)
    print(f"  AUTOMATED LOGIC VALIDATION: {'PASS' if passed else 'FAIL'}   ({elapsed:.1f} s, mode {args.mode})")
    rec = Counter(recorded(st) for _, _, st in l_tests())
    print(f"  TradingView L-tests recorded by the user: {rec['PASS']} PASS, {rec['FAIL']} FAIL, "
          f"{rec['PENDING']} PENDING (docs/TESTS_PHASE2.md)")
    print(f"  Report: {args.report}")


if __name__ == "__main__":
    sys.exit(main())
