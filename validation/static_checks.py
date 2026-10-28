"""Static checks on the production Pine source (src/IST.pine).

These read the Pine text; they do not compile or run it. Compilation stays
MANUAL / TRADINGVIEW (test L00). Each check returns (passed, detail).
"""
from __future__ import annotations

import re
import subprocess
from functools import lru_cache

from validation import PINE_SOURCE, ROOT, VALIDATION_DIR

# [calc] inputs: everything else declared with input.* is [view] or [alert] (ARCHITECTURE §2.2).
CALC_INPUTS = {"confirmedOnly", "fvgMinTicks", "fvgMinTra", "fvgMinRng", "fvgLen", "fvgMemory", "sesTz",
               "s1Nm", "s2Nm", "s3Nm", "s4Nm", "s1Ss", "s2Ss", "s3Ss", "s4Ss", "liqOn", "liqPreset", "liqLeftIn",
               "liqRightIn", "liqReactIn", "liqMemory", "eqTolTk", "eqMinTch", "lrlOn"}
# Display policy accessors: they read fvgMitRule but are called only from L6/L7 (S-01 since v0.3.2).
VIEW_READ_ALLOWED = {"policyBar", "policyTime"}
CALC_SECTIONS = ("L1 · MARKET DATA", "L2 · DETECTION", "L5 · EVENT BUS", "L3 · STATE MANAGEMENT", "ENGINE RUN")
RENDER_SECTIONS = ("L6 · RENDERER (functions", "L6 · RENDERER (run)")
DRAWING_TYPES = {"line", "box", "label", "linefill", "table", "polyline"}
STATE_CALLS = re.compile(r"\.(step|register|take|takeEq|cluster|trigger|advance|dropCluster|pushExtreme|markFinal|supersede|"
                         r"judge|grow|promote|seed|finish|trim)\(|"
                         r"\b(f_emit|f_roll|f_sesNew|f_sesStep|f_sesExtend|f_sesFinalize|f_sesSupersede|f_fvgStep)\(")


@lru_cache(maxsize=1)
def source() -> tuple[str, ...]:
    return tuple(PINE_SOURCE.read_text(encoding="utf-8").splitlines())


def code(line: str) -> str:
    """The line without its // comment and with string literals emptied."""
    out, quote, i = [], None, 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == quote:
                quote = None
                out.append(ch)
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif line.startswith("//", i):
            break
        else:
            out.append(ch)
        i += 1
    return "".join(out)


@lru_cache(maxsize=1)
def sections() -> dict[str, tuple[int, int]]:
    """Section title → (first line index, end index) from the '// ════ title' markers."""
    marks = [(i, ln.split("════", 1)[1].strip(" ═")) for i, ln in enumerate(source())
             if ln.startswith("// ════ ")]
    out = {}
    for k, (i, title) in enumerate(marks):
        out[title] = (i, marks[k + 1][0] if k + 1 < len(marks) else len(source()))
    return out


def lines_of(prefixes) -> list[tuple[int, str]]:
    out = []
    for title, (a, b) in sections().items():
        if title.startswith(prefixes):
            out += [(i, code(source()[i])) for i in range(a, b)]
    return out


def inputs() -> dict[str, str]:
    """name → declaration line, for every input.*(…) declaration."""
    pat = re.compile(r"^(\w+)\s*=\s*input\.\w+\(")
    return {m.group(1): ln for ln in source() if (m := pat.match(ln))}


def view_identifiers() -> set[str]:
    """[view]/[alert] inputs plus every top-level value derived from them (transitively)."""
    view = set(inputs()) - CALC_INPUTS
    a, b = sections()["CONSTANTS"]
    assigns = []
    for ln in source()[a:b]:
        m = re.match(r"^(?:\w+\s+)?(\w+)\s*=\s*(.+)$", code(ln))
        if m:
            assigns.append((m.group(1), set(re.findall(r"\b\w+\b", m.group(2)))))
    changed = True
    while changed:
        changed = False
        for name, used in assigns:
            if name not in view and used & view:
                view.add(name)
                changed = True
    return view


def _enclosing_def(i: int) -> str | None:
    for j in range(i, -1, -1):
        m = re.match(r"^(?:method\s+)?(\w+)\(.*\)\s*=>", source()[j])
        if m:
            return m.group(1)
        if source()[j] and not source()[j][0].isspace() and not source()[j].startswith("//") and j != i:
            return None
    return None


# ── checks ──
def st01_calc_independent_of_view():
    view = view_identifiers()
    hits = []
    for i, ln in lines_of(CALC_SECTIONS):
        for ident in set(re.findall(r"\b\w+\b", ln)) & view:
            if _enclosing_def(i) not in VIEW_READ_ALLOWED:
                hits.append(f"line {i + 1}: {ident}")
    return not hits, f"{len(view)} view/alert identifiers; hits outside the allowed display accessors: {hits or 'none'}"


def st02_no_leftovers():
    bad = [f"line {i + 1}: {w}" for i, ln in enumerate(source())
           for w in ("fvgOn", "bullOpen", "f_qualifies") if re.search(rf"\b{w}\b", code(ln))]
    return not bad, f"removed identifiers still in code: {bad or 'none'}"


def st03_request_security_no_leak():
    calls = [code(ln) for ln in source() if "request.security(" in code(ln)]
    ok = len(calls) == 2 and all("[high[1], low[1]]" in c and "lookahead = barmerge.lookahead_on" in c for c in calls)
    return ok, f"{len(calls)} request.security calls, all `expr[1]` + lookahead_on: {ok}"


def st04_plots_data_window_only():
    plots = [code(ln) for ln in source() if re.match(r"^plot\(", code(ln))]
    bad = [p[:60] for p in plots if "display.data_window" not in p]
    return not bad and plots, f"{len(plots)} plots, not Data-Window-only: {bad or 'none'}"


def st05_fvg_rule_single_path():
    src = [code(ln) for ln in source()]
    n_new = sum("Fvg.new(" in ln for ln in src)
    bull = any(re.search(r"bullCand\s*=\s*rawBull and gapPass\s*$", ln) for ln in src)
    bear = any(re.search(r"bearCand\s*=\s*rawBear and gapPass\s*$", ln) for ln in src)
    gated = any("if barstate.isconfirmed and (bullCand or bearCand)" in ln for ln in src)
    return n_new == 1 and bull and bear and gated, f"Fvg.new ×{n_new}; bull/bear from gapPass: {bull}/{bear}; creation on confirmed bars: {gated}"


def udt_fields() -> dict[str, set[str]]:
    """field name -> declared types, from the `type` blocks."""
    out: dict[str, set[str]] = {}
    in_type = False
    for ln in source():
        if ln.startswith("type "):
            in_type = True
            continue
        if in_type:
            m = re.match(r"^\s+([\w<>.]+)\s+(\w+)", code(ln))
            if m:
                out.setdefault(m.group(2), set()).add(m.group(1))
            elif ln.strip() and not ln.startswith((" ", "\t")):
                in_type = False
    return out


def st06_renderer_never_writes_state():
    """L6 may write drawing handles (line/box/label fields) only, and call no state method."""
    fields = udt_fields()
    hits = []
    for i, ln in lines_of(RENDER_SECTIONS):
        if STATE_CALLS.search(ln):
            hits.append(f"line {i + 1}: call {STATE_CALLS.search(ln).group(0)}")
        for f, rhs in re.findall(r"\.(\w+)\s*:=\s*(.*)", ln):
            kinds = fields.get(f, set())
            logical = kinds - DRAWING_TYPES
            if not logical:
                continue                                    # a drawing handle (or not a record field)
            if kinds & DRAWING_TYPES and re.match(r"(line|box|label|linefill)\.new\b|na\b", rhs.strip()):
                continue                                    # same name is also a handle; the value is a drawing
            hits.append(f"line {i + 1}: writes .{f} ({'/'.join(sorted(kinds))})")
    return not hits, f"state writes or state calls in L6: {hits or 'none'}"


def st07_single_creation_paths():
    src = [code(ln) for ln in source()]
    liq = [i for i, ln in enumerate(src) if "Liq.new(" in ln]
    eq = [i for i, ln in enumerate(src) if "EqCluster.new(" in ln]
    reg = [i for i, ln in enumerate(src) if re.search(r"\w+\.register\(", ln)]
    ok = (len(liq) == 1 and _enclosing_def(liq[0]) == "register" and len(eq) == 1 and _enclosing_def(eq[0]) == "cluster"
          and len(reg) == 2)
    return ok, f"Liq.new ×{len(liq)} (in register), EqCluster.new ×{len(eq)} (in cluster), register calls ×{len(reg)}"


def st08_scope_no_later_phases():
    pat = re.compile(r"\b(cisd|ifvg|smt|displacement|confluence|qualityscore)\b", re.I)
    bad = [f"line {i + 1}: {m.group(0)}" for i, ln in enumerate(source()) if (m := pat.search(code(ln)))]
    return not bad, f"later-phase identifiers in code: {bad or 'none'}"


def st09_cluster_reference_is_metadata():
    reads = [i for i, ln in enumerate(source()) if re.search(r"\.ref\b", code(ln))]
    where = {_enclosing_def(i) for i in reads}
    return where <= {"f_eqTxt"}, f"EqCluster.ref read in: {sorted(w or '?' for w in where) or 'nowhere'} (allowed: f_eqTxt)"


def st10_tr_average_not_wilder():
    bad = [f"line {i + 1}" for i, ln in enumerate(source()) if re.search(r"ta\.(atr|rma)\(", code(ln))]
    return not bad, f"ta.atr / ta.rma in code: {bad or 'none'}"


def st11_liquidity_alerts_default_off():
    ins = inputs()
    names = ("alLiqTkn", "alLiqSwp", "alLiqBrk", "alEqTkn")
    ok = all(n in ins and "input.bool(false" in ins[n] for n in names)
    return ok, f"{', '.join(names)} default false: {ok}"


def st12_version_consistent():
    head = re.search(r"\(IST\) · (v[\w.\-]+)", "\n".join(source()[:5]))
    log = re.search(r"^## (v[\w.\-]+)", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), re.M)
    ok = bool(head and log and head.group(1) == log.group(1))
    return ok, f"IST.pine header {head and head.group(1)} vs CHANGELOG top {log and log.group(1)}"


def st13_oracle_defaults_match_pine():
    """The oracle's defaults, presets and constants equal the Pine inputs/constants."""
    from validation.models.types import PRESETS, FvgSettings, LiqSettings, SessionSettings
    ins, src = inputs(), "\n".join(source())

    def default(name):
        m = re.search(r"input\.\w+\(([^,]+),", ins[name])
        return m.group(1).strip().strip('"')

    f, l, s = FvgSettings(), LiqSettings(), SessionSettings()
    pairs = {
        "fvgMinTicks": (int(default("fvgMinTicks")), f.min_ticks), "fvgMinTra": (float(default("fvgMinTra")), f.k_tra),
        "fvgMinRng": (float(default("fvgMinRng")), f.k_rng), "fvgLen": (int(default("fvgLen")), f.length),
        "fvgMemory": (int(default("fvgMemory")), f.memory), "liqMemory": (int(default("liqMemory")), l.memory),
        "eqTolTk": (int(default("eqTolTk")), l.tol_ticks), "eqMinTch": (int(default("eqMinTch")), l.min_touch),
        "sesTz": (default("sesTz"), s.timezone),
        "sessions": (tuple(default(f"s{i}Ss") for i in range(1, 5)), tuple(w[1] for w in s.windows)),
        "LIQ_TRA_LEN": (int(re.search(r"LIQ_TRA_LEN\s*=\s*(\d+)", src).group(1)), l.tra_len),
        "EQ_MEM": (int(re.search(r"EQ_MEM\s*=\s*(\d+)", src).group(1)), l.eq_memory),
    }
    for name, (left, right, k, w) in PRESETS.items():
        got = tuple(float(re.search(rf"(?:int|float) {v} = switch liqPreset(?:.|\n)*?LiqPreset\.{name}\s*=>\s*([\d.]+)",
                                    src).group(1)) for v in ("LIQ_L", "LIQ_R", "LIQ_K", "LIQ_W"))
        pairs[f"preset {name}"] = (got, (float(left), float(right), float(k), float(w)))
    custom_w = re.search(r"int LIQ_W = switch liqPreset(?:.|\n)*?\n\s*=>\s*(\d+)", src)
    pairs["preset custom W"] = (int(custom_w.group(1)) if custom_w else None, 0)
    bad = {k: v for k, v in pairs.items() if v[0] != v[1]}
    return not bad, f"{len(pairs)} defaults/constants compared; mismatches (Pine, oracle): {bad or 'none'}"


def st14_event_names_match_oracle():
    from validation.models.events import TYPES
    src = "\n".join(source())
    fixed = set(re.findall(r'EV_\w+\s*=>\s*"([A-Z_]+)"', src))
    sided = re.findall(r"EV_\w+\s*=>\s*([sq]) \+ \"([A-Z_]+)\"", src)
    names = fixed | {f"{p}{n}" for k, n in sided for p in (("BSL_", "SSL_") if k == "s" else ("EQH_", "EQL_"))}
    ok = names == set(TYPES)
    return ok, f"Pine names {len(names)}, oracle names {len(TYPES)}; only in Pine: {sorted(names - set(TYPES)) or 'none'}; only in oracle: {sorted(set(TYPES) - names) or 'none'}"


def st15_phase1_baseline_guard():
    """Lines removed from Phase 1 since PHASE1_BASELINE_v0.3.2 must all be in the reviewed manifest."""
    manifest = VALIDATION_DIR / "baselines" / "phase1_removed_lines.txt"
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "diff", "PHASE1_BASELINE_v0.3.2", "--", "src/IST.pine"],
                             capture_output=True, text=True, encoding="utf-8", check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        return None, f"SKIPPED: git or the baseline tag is not available ({e.__class__.__name__})"
    removed = [ln[1:] for ln in out.splitlines() if ln.startswith("-") and not ln.startswith("---")]
    allowed = manifest.read_text(encoding="utf-8").splitlines()
    new = [r for r in removed if r not in allowed]
    return not new, f"{len(removed)} Phase 1 lines removed since the baseline; not in the reviewed manifest: {new or 'none'}"


# DEF-L2 dominance (C1) as it must read in Pine: the window is the W bars before the swing
# bar (history offset right + 1), only a strictly greater extreme rejects (≤ / ≥ with the
# EQ tolerance and EPS), and the significance uses both conditions plus the warm-up.
DOMINANCE_RULES = {
    "window high": r"^float\s+domHiAll\s*=\s*ta\.highest\(high,\s*math\.max\(LIQ_W,\s*1\)\)",
    "window low": r"^float\s+domLoAll\s*=\s*ta\.lowest\(low,\s*math\.max\(LIQ_W,\s*1\)\)",
    "ready": r"^bool\s+domReady\s*=\s*LIQ_W\s*>\s*0\s+and\s+swBar\s*>=\s*LIQ_W\s*$",
    "anchor high": r"^float\s+domHiRef\s*=\s*domReady\s*\?\s*domHiAll\[LIQ_R \+ 1\]\s*:\s*na\b",
    "anchor low": r"^float\s+domLoRef\s*=\s*domReady\s*\?\s*domLoAll\[LIQ_R \+ 1\]\s*:\s*na\b",
    "boundary high": r"^bool\s+domHiOk\s*=\s*LIQ_W == 0 or domHiRef <= swHiPx \+ EQ_TOL \+ EPS\s*$",
    "boundary low": r"^bool\s+domLoOk\s*=\s*LIQ_W == 0 or domLoRef >= swLoPx - EQ_TOL - EPS\s*$",
    "warm-up": r"^bool\s+liqWarm\s*=\s*na\(reactReq\) or \(LIQ_W > 0 and not domReady\)\s*$",
    "significance high": r"^bool\s+sigHi\s*=\s*pivHi and not liqWarm and reactHiOk and domHiOk\s*$",
    "significance low": r"^bool\s+sigLo\s*=\s*pivLo and not liqWarm and reactLoOk and domLoOk\s*$",
}


def st16_dominance_rule(src: str | None = None):
    """The C1 dominance lines in IST.pine, exactly: anchored before the swing bar, inclusive
    of + tolerance, joined with the reaction floor and the warm-up."""
    text = "\n".join(code(ln) for ln in (src.splitlines() if src is not None else source()))
    bad = [name for name, rx in DOMINANCE_RULES.items() if len(re.findall(rx, text, re.M)) != 1]
    return not bad, f"{len(DOMINANCE_RULES)} dominance rules; missing or changed: {bad or 'none'}"


# DEF-LRL1…LRL6 as they must read in Pine: the approved oracle (validation/models/lrl.py)
# line by line. Each rule must match exactly one code line (comments and strings ignored).
LRL_RULES = {
    "TR average": r"^float\s+lrlTra\s+=\s+ta\.sma\(ta\.tr\(true\), LRL_TRA_LEN\)\s*$",
    "left window high": r"^float\s+lrlHiL\s+=\s+ta\.highest\(high, LRL_L\)\s*$",
    "left window low": r"^float\s+lrlLoL\s+=\s+ta\.lowest\(low, LRL_L\)\s*$",
    "right window high": r"^float\s+lrlHiR\s+=\s+ta\.highest\(high, LRL_R\)\s*$",
    "right window low": r"^float\s+lrlLoR\s+=\s+ta\.lowest\(low, LRL_R\)\s*$",
    "pivot high (strict left, ≥ right)": r"^bool\s+lrlPivH\s+=\s+lrlPxH > lrlHiL\[LRL_R \+ 1\] and lrlPxH >= lrlHiR\s*$",
    "pivot low (mirror)": r"^bool\s+lrlPivL\s+=\s+lrlPxL < lrlLoL\[LRL_R \+ 1\] and lrlPxL <= lrlLoR\s*$",
    "side coordinates (high)": r"^\s+s\.sign > 0 \? high\[bar_index - j\] : -low\[bar_index - j\]\s*$",
    "side coordinates (low)": r"^\s+s\.sign > 0 \? low\[bar_index - j\] : -high\[bar_index - j\]\s*$",
    "chord slope": r"^\s+\(r\.ps\.last\(\) - r\.ps\.first\(\)\) / \(r\.xs\.last\(\) - r\.xs\.first\(\)\)\s*$",
    "chord value": r"^\s+r\.ps\.first\(\) \+ r\.slope\(\) \* \(x - r\.xs\.first\(\)\)\s*$",
    "spacing · failure step": r"^\s+bool\s+ok\s+=\s+xb - xa <= LRL_GAP and pb < pa - EQ_TOL - EPS and bar_index - x0 <= LRL_SPAN\s*$",
    "separation (pullback ≥ k × TR)": r"^\s+ok := not na\(tra\) and pb - pull >= LRL_SEP_K \* tra - EPS\s*$",
    "non-horizontal (drop > 2τ)": r"^\s+ok := p0 - pb > LRL_DROP_K \* tau \+ EPS\s*$",
    "candidate chord": r"^\s+float\s+sl\s+=\s+\(pb - p0\) / \(xb - x0\)\s*$",
    "points on the chord": r"^\s+if math\.abs\(ps\.get\(i\) - \(p0 \+ sl \* \(xs\.get\(i\) - x0\)\)\) > tau \+ EPS\s*$",
    "clean line": r"^\s+if s\.hiS\(j\) > p0 \+ sl \* \(j - x0\) \+ tau \+ EPS\s*$",
    "tau at the first point": r"^\s+float\s+tau\s+=\s+math\.max\(EQ_TOL, LRL_TOL_K \* tra\)\s*$",
    "never judged on its confirmation bar": r"^\s+if r\.born < t\s*$",
    "boundary now": r"^\s+float\s+bNow\s+=\s+r\.yAt\(t\) \+ r\.tau\s*$",
    "boundary of the previous bar": r"^\s+float\s+bPrev\s+=\s+r\.yAt\(t - 1\) \+ r\.tau\s*$",
    "cross": r"^\s+if hi > bNow \+ EPS\s*$",
    "classification DRIFT · BREAK · SWEEP":
        r"^\s+s\.finish\(r, hi <= bPrev \+ EPS \? LRL_DRIFT : cl > bNow \+ EPS \? LRL_BREAK : LRL_SWEEP, bNow, bPrev\)\s*$",
    "expiry": r"^\s+else if t > r\.xs\.last\(\) \+ LRL_GAP \+ LRL_R\s*$",
    "touch": r"^\s+else if hi >= r\.yAt\(t\) - r\.tau - EPS\s*$",
    "candidates die": r"^\s+bool\s+dead\s+=\s+s\.spent\.includes\(c\.xs\.get\(0\)\) or s\.spent\.includes\(c\.xs\.get\(1\)\) "
                      r"or hi > c\.yAt\(t\) \+ c\.tau \+ EPS or t > c\.xs\.last\(\) \+ LRL_GAP \+ LRL_R\s*$",
    "seed only free pivots": r"^\s+if not s\.members\.includes\(xa\) and not s\.spent\.includes\(xa\) and X - xa <= LRL_GAP\s*$",
    "a crossed LRL spends its points": r"^\s+if kind != LRL_EXPIRED\s*\n\s+s\.spent\.push\(x\)\s*$",
    "candidate memory": r"^\s+while s\.cands\.size\(\) > LRL_CANDS\s*$",
    "record memory": r"^\s+if s\.live\.size\(\) \+ s\.hist\.size\(\) > LRL_MEM\s*$",
}
# Code lines that must appear in this order: ADVANCE both sides, then JUDGE both sides;
# inside JUDGE, extend, then confirm, then seed.
LRL_ORDER = (("lrlHi.advance()", "lrlLo.advance()", "lrlHi.judge(", "lrlLo.judge("),
             ("bool used = s.grow(", "used := s.promote(", "s.seed(X, XT, P)"))
LRL_CONSTANTS = {"LRL_L": "left", "LRL_R": "right", "LRL_TOL_K": "tol_k", "LRL_GAP": "gap", "LRL_SEP_K": "sep_k",
                 "LRL_DROP_K": "drop_k", "LRL_TRA_LEN": "tra_len", "LRL_CANDS": "cand_memory", "LRL_MEM": "memory"}


def st17_lrl_rules(src: str | None = None):
    """DEF-LRL1…LRL6 in IST.pine: the approved constants (= LrlSettings), every formula of the
    oracle line by line, ADVANCE before JUDGE and extend → confirm → seed."""
    from validation.models.types import LrlSettings
    lines = [code(ln) for ln in (src.splitlines() if src is not None else source())]
    text = "\n".join(lines)
    bad = [name for name, rx in LRL_RULES.items() if len(re.findall(rx, text, re.M)) != 1]
    want = LrlSettings()
    for name, field in LRL_CONSTANTS.items():
        m = re.findall(rf"^{name}\s*=\s*([\d.]+)\s*$", text, re.M)
        if len(m) != 1 or float(m[0]) != float(getattr(want, field)):
            bad.append(f"{name} = {m or 'missing'} (oracle {getattr(want, field)})")
    for seq in LRL_ORDER:
        at = [next((i for i, ln in enumerate(lines) if s in ln), None) for s in seq]
        if None in at or at != sorted(at) or len(set(at)) != len(at):
            bad.append("order " + " → ".join(seq))
    return not bad, f"{len(LRL_RULES)} formulas, {len(LRL_CONSTANTS)} constants, {len(LRL_ORDER)} orders; wrong or missing: {bad or 'none'}"


CHECKS = [
    ("ST-01", "Calculation never reads [view]/[alert] inputs (S-01)", st01_calc_independent_of_view),
    ("ST-02", "No identifiers of removed features (S-02)", st02_no_leftovers),
    ("ST-03", "request.security: exactly 2, both expr[1] + lookahead_on (S-03, DEF-G2)", st03_request_security_no_leak),
    ("ST-04", "Debug plots are Data-Window-only (S-04)", st04_plots_data_window_only),
    ("ST-05", "One FVG creation path, shared gapPass, confirmed bars (S-05)", st05_fvg_rule_single_path),
    ("ST-06", "Renderer never writes logical state (S-08)", st06_renderer_never_writes_state),
    ("ST-07", "Single creation paths for levels and clusters (S-09)", st07_single_creation_paths),
    ("ST-08", "No Phase 3+ identifiers in code (S-10)", st08_scope_no_later_phases),
    ("ST-09", "Cluster reference is metadata; state uses the boundary (S-13)", st09_cluster_reference_is_metadata),
    ("ST-10", "TR average is an SMA, never Wilder ATR/RMA", st10_tr_average_not_wilder),
    ("ST-11", "Liquidity alerts default OFF", st11_liquidity_alerts_default_off),
    ("ST-12", "Version header matches the CHANGELOG", st12_version_consistent),
    ("ST-13", "Oracle defaults/presets/constants equal the Pine ones", st13_oracle_defaults_match_pine),
    ("ST-14", "Event names: Pine f_evName == oracle", st14_event_names_match_oracle),
    ("ST-15", "Phase 1 baseline guard (git diff vs PHASE1_BASELINE_v0.3.2) (S-06)", st15_phase1_baseline_guard),
    ("ST-16", "DEF-L2 dominance (C1): window before the swing bar, strict-beyond boundary", st16_dominance_rule),
    ("ST-17", "DEF-LRL1…LRL6: approved constants, oracle formulas, ADVANCE before JUDGE", st17_lrl_rules),
]
