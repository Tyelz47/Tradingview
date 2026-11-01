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
               "liqRightIn", "liqReactIn", "liqMemory", "eqTolTk", "eqMinTch", "lrlOn", "cisdOn"}
# Display policy accessors: they read fvgMitRule but are called only from L6/L7 (S-01 since v0.3.2).
VIEW_READ_ALLOWED = {"policyBar", "policyTime"}
CALC_SECTIONS = ("L1 · MARKET DATA", "L2 · DETECTION", "L5 · EVENT BUS", "L3 · STATE MANAGEMENT", "ENGINE RUN")
RENDER_SECTIONS = ("L6 · RENDERER (functions", "L6 · RENDERER (run)")
DRAWING_TYPES = {"line", "box", "label", "linefill", "table", "polyline"}
STATE_CALLS = re.compile(r"\.(step|register|take|takeEq|cluster|trigger|advance|dropCluster|pushExtreme|markFinal|supersede|"
                         r"advanceLrl|judge|grow|promote|seed|finish|trim|feedHtf|stepHtf|seedHtf|trimHtf|milestonesHtf|"
                         r"pruneCisd|feedCisd|factsCisd|confirmCisd)\(|"
                         r"\b(f_emit|f_emitHtf|f_roll|f_sesNew|f_sesStep|f_sesExtend|f_sesFinalize|f_sesSupersede|f_fvgStep)\(")


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


def _body(name: str, src=None) -> list[str]:
    """The code lines of a top-level function's body."""
    lines = src if src is not None else source()
    i = next(k for k, ln in enumerate(lines) if re.match(rf"^{name}\(", ln))
    out = []
    for ln in lines[i + 1:]:
        if ln and not ln[0].isspace():
            break
        out.append(code(ln))
    return out


def st03_request_security_no_leak(src: str | None = None):
    """PDH/PDL and PWH/PWL: `[high[1], low[1]]` (DEF-G2). HTF FVG (DEF-B0): one request per
    timeframe 15m … 1W, the expression f_htfPack(), which reads every price / time series at
    [1] or older (no bare series, no [0], ta.tr only shifted). All lookahead_on."""
    lines = src.splitlines() if src is not None else source()
    calls = [code(ln) for ln in lines if "request.security(" in code(ln)]
    period = [c for c in calls if "[high[1], low[1]]" in c]
    htf = [c for c in calls if ", f_htfPack()," in c]
    tfs = sorted(m[1] for ln in lines if ", f_htfPack()," in code(ln) and (m := re.search(r'f_htfReq\("(\w+)"\)', ln)))
    body = "\n".join(_body("f_htfPack", lines))
    leaks = (re.findall(r"\b(?:open|high|low|close|time|time_close|volume|hl2|hlc3|ohlc4)\b(?!\[)", body)
             + re.findall(r"\[\s*0\s*\]", body) + re.findall(r"ta\.tr\([^)]*\)(?!\[)", body))
    ok = (len(calls) == 8 and len(period) == 2 and len(htf) == 6 and tfs == sorted(("15", "30", "60", "240", "D", "W"))
          and all("lookahead = barmerge.lookahead_on" in c for c in calls) and not leaks)
    return ok, (f"{len(calls)} request.security calls: {len(period)} period levels `[high[1], low[1]]`, {len(htf)} HTF "
                f"f_htfPack() ({', '.join(tfs) or 'none'}), all lookahead_on: "
                f"{all('lookahead = barmerge.lookahead_on' in c for c in calls)}; reads newer than [1] in f_htfPack: {leaks or 'none'}")


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
    pat = re.compile(r"\b(ifvg|smt|displacement|confluence|qualityscore)\b", re.I)   # CISD: in scope since v0.7.0-dev
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
    build = re.search(r'^IST_BUILD\s*=\s*"(v[\w.\-]+)"', "\n".join(source()), re.M)
    ok = bool(head and log and build and head.group(1) == log.group(1) == build.group(1))
    return ok, (f"IST.pine header {head and head.group(1)} vs CHANGELOG top {log and log.group(1)} vs capture build "
                f"IST_BUILD {build and build.group(1)}")


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
    from validation.models.events import ORACLE_ONLY, TYPES
    src = "\n".join(source())
    fixed = set(re.findall(r'EV_\w+\s*=>\s*"([A-Z_]+)"', src))
    sided = re.findall(r"EV_\w+\s*=>\s*([sq]) \+ \"([A-Z_]+)\"", src)
    names = fixed | {f"{p}{n}" for k, n in sided for p in (("BSL_", "SSL_") if k == "s" else ("EQH_", "EQL_"))}
    want = set(TYPES) - ORACLE_ONLY
    ok = names == want
    return ok, (f"Pine names {len(names)}, oracle names {len(want)} (+{len(ORACLE_ONLY)} oracle-only, not in Pine yet); "
                f"only in Pine: {sorted(names - want) or 'none'}; only in oracle: {sorted(want - names) or 'none'}")


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
    # v0.7.1-dev: the TR average of every closed bar is recorded at global scope; fits / seed read
    # the anchor's value from it (a history read inside a method reads the call history: ST-21)
    "TR average recorded every closed bar": r"^if barstate\.isconfirmed\n    lrlTraBuf\.push\(lrlTra\)\s*$",
    "TR average at bar x": r"^\s+v := lrlTraBuf\.get\(lrlTraBuf\.size\(\) - 1 - k\)\s*$",
    "separation: TR average at the earlier point": r"^\s+float\s+tra\s+=\s+f_lrlTraAt\(xa\)\n\s+float\s+pull\s+=",
    "tau: TR average at the anchor": r"^\s+float\s+tra\s+=\s+f_lrlTraAt\(xa\)\n\s+if not na\(tra\)\n\s+float\s+tau\s+=",
    # history buffers: the clean-line scan reads high / low over an LRL's span (LRL_SPAN), and
    # bar_index drawings (historical LRL polylines) are converted through `time` (v0.5.1-dev
    # runtime error: "historical offset (1231) is beyond the historical buffer's limit (1230)")
    "high history 5000": r"^max_bars_back\(high, 5000\)\s*$",
    "low history 5000": r"^max_bars_back\(low, 5000\)\s*$",
    "time history 5000 (bar_index drawings)": r"^max_bars_back\(time, 5000\)\s*$",
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
LRL_ORDER = (("lrlHi.advanceLrl()", "lrlLo.advanceLrl()", "lrlHi.judge(", "lrlLo.judge("),
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


# DEF-B0…B6 as they must read in Pine (validation/models/htf_fvg.py). Each rule must match
# exactly one code line (comments and strings ignored).
HTF_RULES = {
    "TR average at [1], own timeframe": r"^\s+float\s+tra\s+=\s+ta\.sma\(ta\.tr\(true\)\[1\], fvgLen\)\s*$",
    "avg range at [1], own timeframe": r"^\s+float\s+rng\s+=\s+ta\.sma\(high\[1\] - low\[1\], fvgLen\)\s*$",
    "bull: candle 3 low above candle 1 high": r"^\s+bool\s+up\s+=\s+low\[1\] > high\[3\]\s*$",
    "bear: candle 3 high below candle 1 low": r"^\s+bool\s+dn\s+=\s+high\[1\] < low\[3\]\s*$",
    "TR threshold at candle 1": r"^\s+float\s+traQ\s+=\s+fvgMinTra > 0 \? fvgMinTra \* tra\[2\] : 0\.0\s*$",
    "range threshold at candle 1": r"^\s+float\s+rngQ\s+=\s+fvgMinRng > 0 \? fvgMinRng \* rng\[2\] : 0\.0\s*$",
    "Phase 1 qualification (D4)": r"^\s+bool\s+ok\s+=\s+not na\(gap\) and gap >= fvgMinTicks \* syminfo\.mintick - EPS "
                                  r"and gap >= traQ and gap >= rngQ\s*$",
    "seed engine: bars after candle 3": r"^\s+if zs\.get\(i, 4\) < time\[1\]\s*$",
    "seed engine: fully filled or closed beyond": r"^\s+if bull \? \(low\[1\] <= zs\.get\(i, 2\) or close\[1\] < zs\.get\(i, 2\)\) "
                                                  r": \(high\[1\] >= zs\.get\(i, 1\) or close\[1\] > zs\.get\(i, 1\)\)\s*$",
    "never a lower timeframe": r"^\s+timeframe\.in_seconds\(tf\) > timeframe\.in_seconds\(\) \? tf : timeframe\.period\s*$",
    "completion: a new completed HTF bar": r"^\s+else if s\.bT != s\.lastT\s*$",
    "invalidation: own-timeframe close after candle 3 (D5)":
        r"^\s+if na\(r\.invBar\) and s\.bT > r\.id and \(r\.dir > 0 \? s\.bC < r\.bottom : s\.bC > r\.top\)\s*$",
    "known on this chart bar, box origin candle 1 (D8)":
        r"^\s+HtfZone z = HtfZone\.new\(s\.zDir, s\.bT, s\.zC1, s\.zTop, s\.zBot, \(s\.zTop \+ s\.zBot\) / 2, bar_index, time\)\s*$",
    "milestones on the chart bar's wick": r"^\s+float\s+reach\s+=\s+r\.dir > 0 \? low : high\s*$",
    "no retroactive touch (seeds)": r"^\s+if na\(r\.touchBar\) and not r\.preTouch and \(r\.dir > 0 \? reach <= near : reach >= near\)\s*$",
    "no retroactive CE (seeds)": r"^\s+if na\(r\.ceBar\) and not r\.preCe and \(r\.dir > 0 \? reach <= r\.mid : reach >= r\.mid\)\s*$",
    "full fill": r"^\s+if na\(r\.fullBar\) and \(r\.dir > 0 \? reach <= far : reach >= far\)\s*$",
    "memory: closed records first": r"^\s+if not na\(r\.invBar\) or not na\(r\.fullBar\)\s*$",
    "renderer: only open, unfilled zones": r"^\s+if na\(r\.invBar\) and na\(r\.fullBar\)\s*$",
}
# Code lines that must appear in this order: the LRL engine, then every HTF timeframe; per
# completed HTF bar: invalidate, then create, then milestones (also on the seed bar).
HTF_ORDER = (("lrlLo.judge(", "s.stepHtf()"),
             ("s.seedHtf()", "f_emitHtf(EV_HTF_INVAL", "f_emitHtf(EV_HTF_CREATED", "s.milestonesHtf()"))
HTF_CONSTANTS = {"HTF_MEM": "memory", "HTF_SEEDS": "seeds", "HTF_SEED_MEM": "seed_memory"}


def st19_htf_rules(src: str | None = None):
    """DEF-B0…B6 in IST.pine: the approved constants (= HtfSettings), every timing and
    definition line of the oracle, and the per-bar order."""
    from validation.models.types import HtfSettings
    lines = [code(ln) for ln in (src.splitlines() if src is not None else source())]
    text = "\n".join(lines)
    bad = [name for name, rx in HTF_RULES.items() if len(re.findall(rx, text, re.M)) != 1]
    want = HtfSettings()
    for name, field in HTF_CONSTANTS.items():
        m = re.findall(rf"^{name}\s*=\s*([\d.]+)\s*$", text, re.M)
        if len(m) != 1 or float(m[0]) != float(getattr(want, field)):
            bad.append(f"{name} = {m or 'missing'} (oracle {getattr(want, field)})")
    for seq in HTF_ORDER:
        at = [next((i for i, ln in enumerate(lines) if s in ln), None) for s in seq]
        if None in at or at != sorted(at) or len(set(at)) != len(at):
            bad.append("order " + " → ".join(seq))
    return not bad, f"{len(HTF_RULES)} rules, {len(HTF_CONSTANTS)} constants, {len(HTF_ORDER)} orders; wrong or missing: {bad or 'none'}"


# DEF-CISD1…CISD9 (CISD-R) as they must read in Pine: the oracle's rules in Pine's incremental
# formulation (validation/models/cisd.py CisdStack, proven equal to CisdEngine). Each rule must
# match exactly one code line (comments and strings emptied; multi-line rules where structure matters).
CISD_RULES = {
    "TR average (body / TR metadata only)": r"^float\s+cisdTra\s+=\s+ta\.sma\(ta\.tr\(true\), CISD_TRA_LEN\)\s*$",
    "starts UNKNOWN": r"^\s+int\s+state = 0\s*$",
    "both sides armed while UNKNOWN": r"^\s+bool\s+armed = true\s*$",
    "side coordinates (bearish: open and close negated, high ↔ −low)":
        r"^\s+float\s+o\s+=\s+s\.sign \* open\n\s+float\s+lo\s+=\s+s\.sign > 0 \? low : -high\n\s+float\s+cl\s+=\s+s\.sign \* close\s*$",
    "every low enters the leg-extreme stack": r"^\s+while s\.wBar\.size\(\) > 0 and lo <= s\.wLow\.last\(\) \+ EPS\s*$",
    # a delivery candle (doji excluded) starts or continues a series and enters the delivery stack;
    # anything else, a doji included, ends the series
    "delivery candle → series → delivery stack": r"^    if cl < o - EPS\n        if not s\.inRun\n(?:            .*\n){4}"
                                                r"        while s\.dBar\.size\(\) > 0 and lo <= s\.dLow\.last\(\) \+ EPS$",
    "anything else ends the series (doji included)": r"^    else\n        s\.inRun := false$",
    "L = the open of the series' first candle": r"^\s+s\.runL\s+:= o\s*$",
    "equal extreme → the later candle (≤ pops)": r"^\s+while s\.dBar\.size\(\) > 0 and lo <= s\.dLow\.last\(\) \+ EPS\s*$",
    "a new bottom = the reference moved": r"^\s+if s\.dBar\.size\(\) == 1\s*$",
    "window restart drops older entries only": r"^\s+while s\.dBar\.size\(\) > 0 and s\.dBar\.first\(\) < a\s*$",
    "armed sides with a reference": r"^\s+if s\.armed and s\.dBar\.size\(\) > 0\s*$",
    "confirmation: first close strictly beyond L, any colour, after the origin and the flip":
        r"^\s+ok := bar_index > s\.dOrg\.first\(\) and bar_index > s\.since and s\.sign \* close > s\.dL\.first\(\) \+ EPS\s*$",
    "decided at bar close, independent of display": r"^\s+if cisdOn and barstate\.isconfirmed\s*$",
    "the armed side is against the state": r"^\s+CisdSide arm = cisdBook\.state > 0 \? cisdDn : cisdUp\s*$",
    "the state side restarts at the armed side's new extreme":
        r"^\s+if arm\.dBar\.size\(\) > 0 and arm\.dBar\.first\(\) == bar_index\n\s+sts\.pruneCisd\(bar_index\)\s*$",
    "never two CISDs on one bar": r"^\s+if upHit and dnHit\s*$",
    "the record (L, extreme, leg extreme, metadata)":
        r"^\s+Cisd r = Cisd\.new\(s\.sign, s\.dOrgT\.first\(\), b\.state, s\.sign \* s\.dL\.first\(\), origin, eb, "
        r"s\.dTime\.first\(\), s\.sign \* s\.dLow\.first\(\), s\.sign \* leg, s\.known, bar_index, time, close, bk\)\s*$",
    "leg extreme: every low from the origin": r"^\s+if j >= origin\s*$",
    "body / TR before the bar (read every bar, at global scope)":
        r"^float\s+cisdTraPrv\s+=\s+cisdTra\[1\]\s*$(?:.|\n)*^\s+float\s+tr1\s+=\s+cisdTraPrv\s*$",
    "the previous CISD ends": r"^\s+prv\.endBar := bar_index\s*$",
    "flip: the state becomes the CISD's side": r"^\s+b\.state\s+:= s\.sign\s*$",
    "flip: the opposite leg starts at this leg's delivery extreme": r"^\s+op\.pruneCisd\(eb\)\s*$",
    "flip: this side's next leg starts at the opposite extreme": r"^\s+na0 := op\.dBar\.first\(\)\n\s+s\.pruneCisd\(na0\)\s*$",
    "flip: alternation": r"^\s+s\.armed\s+:= false\n\s+op\.armed := true\n\s+op\.since := bar_index\s*$",
    "identity = side + origin time": r"^\s+str\.tostring\(r\.side\) \+ \"\" \+ str\.tostring\(r\.id\)\s*$",
    "event: side, id, origin, L": r"^\s+f_emit\(EV_CISD_CONFIRMED, r\.side, r\.id, r\.origin, r\.level, f_cisdTxt\(r\)\)\s*$",
    "fact: retest (wick back to L)": r"^\s+if na\(r\.retest\) and lo <= lv \+ EPS\s*$",
    "fact: close back at or through L": r"^\s+if na\(r\.reclaim\) and cl <= lv \+ EPS\s*$",
    "fact: close beyond the leg extreme": r"^\s+if na\(r\.broken\) and cl < r\.side \* r\.legExt - EPS\s*$",
    "facts only while ACTIVE": r"^\s+if na\(r\.endBar\)\n\s+float\s+lv\s+=\s+r\.side \* r\.level\s*$",
    "memory: the oldest record goes": r"^\s+if b\.recs\.size\(\) > CISD_MEM\n\s+Cisd old = b\.recs\.shift\(\)\s*$",
    "renderer: no CISD before the guard": r"^\s+if cur\.cBar >= CISD_GUARD\s*$",
    "alert: OFF by default input, never before the guard":
        r"^\s+EV_CISD_CONFIRMED => cisdAlert and e\.eventBar >= CISD_GUARD\s*$",
}
# FACTS → stacks → state-side restart → confirmation, after the HTF engine; inside the flip the
# opposite side restarts first (this side's next leg starts at its new extreme).
CISD_ORDER = (("s.stepHtf()", "cisdBook.factsCisd()", "cisdUp.feedCisd()", "cisdDn.feedCisd()", "sts.pruneCisd(bar_index)",
               "bool upHit = cisdUp.readyCisd()", "cisdBook.confirmCisd(cisdUp, cisdDn)"),
              ("op.pruneCisd(eb)", "s.pruneCisd(na0)", "f_emit(EV_CISD_CONFIRMED"))
CISD_CONSTANTS = {"CISD_MEM": "memory", "CISD_TRA_LEN": "tra_len", "CISD_GUARD": "guard"}


def _cisd_blocks(lines: list[str]) -> list[str]:
    """The CISD engine's code: its L3 block and its ENGINE RUN block."""
    out, on = [], False
    for ln in lines:
        if ln.startswith("// ── CISD (DEF-CISD1") or ln.startswith("    // ── CISD (DEF-CISD1"):
            on = True
        elif on and (ln.startswith("// ════") or ln.startswith("// ── ")):
            on = False
        if on:
            out.append(code(ln))
    return out


def st20_cisd_rules(src: str | None = None):
    """DEF-CISD1…CISD9 in IST.pine: the approved constants (= CisdSettings), every rule line,
    the per-bar order, no history read and no number but 0 / 1 in the engine (no leg-length
    limit, no truncation; the metadata's previous-bar TR average is read at global scope), the
    200-bar guard and the display inputs outside detection, side in the identity."""
    from validation.models.types import CisdSettings
    raw = src.splitlines() if src is not None else list(source())
    lines = [code(ln) for ln in raw]
    text = "\n".join(lines)
    bad = [name for name, rx in CISD_RULES.items() if len(re.findall(rx, text, re.M)) != 1]
    want = CisdSettings()
    for name, field in CISD_CONSTANTS.items():
        m = re.findall(rf"^{name}\s*=\s*([\d.]+)\s*$", text, re.M)
        if len(m) != 1 or float(m[0]) != float(getattr(want, field)):
            bad.append(f"{name} = {m or 'missing'} (oracle {getattr(want, field)})")
    for seq in CISD_ORDER:
        at = [next((i for i, ln in enumerate(lines) if s in ln), None) for s in seq]
        if None in at or at != sorted(at) or len(set(at)) != len(at):
            bad.append("order " + " → ".join(seq))
    engine = "\n".join(_cisd_blocks(raw))
    hist = re.findall(r"\w+\[[^\]]*\]", engine)
    nums = sorted({n for n in re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", engine) if float(n) not in (0, 1)})
    if not engine or hist or nums or "max_bars_back" in engine:
        bad.append(f"engine reads history {hist or ''} / numbers {nums or ''}: a leg-length limit or truncation")
    if any(re.search(r"max_bars_back\(\s*cisd", ln) for ln in lines):
        bad.append("max_bars_back on a CISD series")
    calc = {i for i, _ in lines_of(CALC_SECTIONS)}
    leaks = [i + 1 for i, ln in enumerate(lines) if i in calc and re.search(r"\b(CISD_GUARD|cisdShow|cisdPrev|cisdAlert)\b", ln)]
    if leaks:
        bad.append(f"guard / display / alert input read by detection: lines {leaks}")
    return not bad, (f"{len(CISD_RULES)} rules, {len(CISD_CONSTANTS)} constants, {len(CISD_ORDER)} orders, no history / "
                     f"limit, guard and display outside detection; wrong or missing: {bad or 'none'}")


# Functions that run on every bar of their context, so a history read inside them is a bar
# history: f_htfPack is the expression of each HTF request.security (DEF-B0).
EVERY_BAR_FUNCTIONS = {"f_htfPack"}
SERIES_BUILTINS = {"open", "high", "low", "close", "time", "time_close", "volume", "hl2", "hlc3", "ohlc4", "bar_index"}


def st21_no_history_in_functions(src: str | None = None):
    """No history read of a user-defined series inside a user function or method (v0.7.1-dev,
    real capture 2026-10-30). Pine keeps a separate history per call of a function: a function
    that does not run on every bar (the CISD confirmation, the LRL seed / fit checks) gets the
    value of an earlier CALL, not of the earlier BAR. Read the value at global scope (every bar)
    or keep it in a per-bar array. Built-in series (high, low, …) are exempt: their reads inside
    methods match the oracle on real captures (LRL points, liquidity)."""
    lines = src.splitlines() if src is not None else list(source())
    hits, fn = [], None
    for i, ln in enumerate(lines):
        m = re.match(r"^(?:method\s+)?(\w+)\(.*\)\s*=>", ln)
        if m:
            fn = m.group(1)
        elif ln and not ln[0].isspace() and not ln.startswith("//"):
            fn = None
        if fn is None or fn in EVERY_BAR_FUNCTIONS or not ln[:1].isspace():
            continue
        for name, idx in re.findall(r"\b(\w+)\[([^\]]+)\]", code(ln)):
            if name not in SERIES_BUILTINS and not re.match(r"^\s*(?:var\s+)?array", code(ln)):
                hits.append(f"line {i + 1}: {fn}: {name}[{idx}]")
    return not hits, f"history reads of user series inside functions / methods: {hits or 'none'}"


def st18_no_overloaded_functions(src: str | None = None):
    """Pine forbids global variables inside an overloaded user function or method (CE10182:
    'Cannot use global variable … in the local scope of overloaded function'). Every
    user-defined function and method name is therefore declared exactly once."""
    lines = src.splitlines() if src is not None else source()
    names = [m.group(1) for ln in lines if (m := re.match(r"^(?:method\s+)?(\w+)\([^)]*\)\s*=>", ln))]
    dup = sorted({n for n in names if names.count(n) > 1})
    return not dup, f"{len(names)} user-defined functions and methods; names declared more than once: {dup or 'none'}"


CHECKS = [
    ("ST-01", "Calculation never reads [view]/[alert] inputs (S-01)", st01_calc_independent_of_view),
    ("ST-02", "No identifiers of removed features (S-02)", st02_no_leftovers),
    ("ST-03", "request.security: 2 period levels + 6 HTF, all [1]-only + lookahead_on (S-03, DEF-G2, DEF-B0)",
     st03_request_security_no_leak),
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
    ("ST-18", "No overloaded user function or method names (Pine CE10182)", st18_no_overloaded_functions),
    ("ST-19", "DEF-B0…B6 HTF FVG: approved constants, timing and definition lines, per-bar order", st19_htf_rules),
    ("ST-20", "DEF-CISD1…CISD9 CISD-R: approved rules and constants, per-bar order, no leg-length limit, "
              "guard and display outside detection", st20_cisd_rules),
    ("ST-21", "No history read of a user series inside a function or method (Pine call history ≠ bar history)",
     st21_no_history_in_functions),
]
