"""LRL in src/IST.pine (v0.5.0-dev): the static check ST-17 pins the approved constants and
every oracle formula, line by line, and each mutation that would change the definition is
caught. Nothing here runs Pine: compilation and runtime stay MANUAL / TRADINGVIEW."""
import pytest

from validation import PINE_SOURCE
from validation.static_checks import st17_lrl_rules

pytestmark = [pytest.mark.lrl, pytest.mark.section("lrl")]
SRC = PINE_SOURCE.read_text(encoding="utf-8")

# name → (exact text in IST.pine, replacement): each one changes the approved definition.
MUTATIONS = {
    "pivots 5/3 instead of 3/2": ("LRL_L        = 3 ", "LRL_L        = 5 ", "LRL_R        = 2 ", "LRL_R        = 3 "),
    "τ coefficient 0.25": ("LRL_TOL_K    = 0.5 ", "LRL_TOL_K    = 0.25 "),
    "τ from the TR average only": ("float tau = math.max(EQ_TOL, LRL_TOL_K * tra)", "float tau = LRL_TOL_K * tra"),
    "gap 60": ("LRL_GAP      = 30 ", "LRL_GAP      = 60 "),
    "separation missing": ("ok := not na(tra) and pb - pull >= LRL_SEP_K * tra - EPS", "ok := not na(tra)"),
    "non-horizontal rule missing": ("ok := p0 - pb > LRL_DROP_K * tau + EPS", "ok := true"),
    "failure step within the EQ tolerance": ("pb < pa - EQ_TOL - EPS", "pb < pa - EPS"),
    "previous boundary = current boundary": ("float bPrev = r.yAt(t - 1) + r.tau", "float bPrev = r.yAt(t) + r.tau"),
    "DRIFT inequality strict": ("hi <= bPrev + EPS ? LRL_DRIFT", "hi < bPrev + EPS ? LRL_DRIFT"),
    "DRIFT against the current boundary": ("hi <= bPrev + EPS ? LRL_DRIFT", "hi <= bNow + EPS ? LRL_DRIFT"),
    "BREAK on the previous boundary": ("cl > bNow + EPS ? LRL_BREAK", "cl > bPrev + EPS ? LRL_BREAK"),
    "cross without tolerance": ("float bNow  = r.yAt(t) + r.tau", "float bNow  = r.yAt(t)"),
    "ADVANCE after JUDGE": ("        lrlHi.advanceLrl()\n        lrlLo.advanceLrl()\n        lrlHi.judge(lrlPivH, lrlX, lrlXT, lrlPxH)\n"
                            "        lrlLo.judge(lrlPivL, lrlX, lrlXT, -lrlPxL)",
                            "        lrlHi.judge(lrlPivH, lrlX, lrlXT, lrlPxH)\n        lrlLo.judge(lrlPivL, lrlX, lrlXT, -lrlPxL)\n"
                            "        lrlHi.advanceLrl()\n        lrlLo.advanceLrl()"),
    "confirm before extend": ("        bool used = s.grow(X, XT, P)\n        if not used\n            used := s.promote(X, XT, P)",
                              "        bool used = s.promote(X, XT, P)\n        if not used\n            used := s.grow(X, XT, P)"),
    "spent pivots reused (seeding)": ("if not s.members.includes(xa) and not s.spent.includes(xa) and X - xa <= LRL_GAP",
                                      "if not s.members.includes(xa) and X - xa <= LRL_GAP"),
    "spent pivots kept in candidates": ("bool dead = s.spent.includes(c.xs.get(0)) or s.spent.includes(c.xs.get(1)) or ",
                                        "bool dead = "),
    "a crossed LRL does not spend its points": ("        if kind != LRL_EXPIRED\n            s.spent.push(x)",
                                                "        if kind == LRL_EXPIRED\n            s.spent.push(x)"),
    "judged on its confirmation bar": ("        if r.born < t\n", "        if r.born <= t\n"),
    "no clean-line check": ("if s.hiS(j) > p0 + sl * (j - x0) + tau + EPS", "if false"),
    "chord from the first two points": ("float sl = (pb - p0) / (xb - x0)", "float sl = (ps.get(1) - p0) / (xs.get(1) - x0)"),
    "expiry one bar later": ("else if t > r.xs.last() + LRL_GAP + LRL_R", "else if t > r.xs.last() + LRL_GAP + LRL_R + 1"),
    "time history buffer removed": ("max_bars_back(time, 5000)\n", ""),
    "time history buffer too short": ("max_bars_back(time, 5000)", "max_bars_back(time, 1000)"),
    "high history buffer removed": ("max_bars_back(high, 5000)\n", ""),
    "a significance test on LRL pivots": ("bool  lrlPivH = lrlPxH > lrlHiL[LRL_R + 1] and lrlPxH >= lrlHiR",
                                          "bool  lrlPivH = lrlPxH > lrlHiL[LRL_R + 1] and lrlPxH >= lrlHiR and sigHi"),
}


def _mutate(old_new: tuple) -> str:
    src = SRC
    for old, new in zip(old_new[::2], old_new[1::2]):
        assert src.count(old) == 1, f"mutation anchor not unique or missing: {old!r}"
        src = src.replace(old, new)
    return src


def test_st17_passes_on_the_source():
    ok, detail = st17_lrl_rules()
    assert ok, detail


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_mutation_is_caught(name):
    ok, detail = st17_lrl_rules(_mutate(MUTATIONS[name]))
    assert not ok, f"{name} was not caught: {detail}"


def test_no_overloaded_names_ce10182():
    """LRL-L00 failed on v0.5.0-dev with CE10182: LRL's `advance(LrlSide)` overloaded the frozen
    FVG `advance(Fvg)`, and Pine forbids global variables inside overloaded user functions.
    ST-18 passes now; putting the old name back (or any second declaration) is caught."""
    from validation.static_checks import st18_no_overloaded_functions as st18
    assert st18()[0], st18()[1]
    back = SRC.replace("method advanceLrl(LrlSide s) =>", "method advance(LrlSide s) =>")
    ok, detail = st18(back)
    assert not ok and "['advance']" in detail
    assert "method advance(Fvg z) =>" in SRC                       # the frozen FVG method is untouched


def test_renderer_draws_one_straight_line():
    """DEF-LRL7 (user, 2026-10-29): ONE straight solid line first → latest point (the chord in
    state) and the projection on the same function y, dashed: no polyline through the
    intermediate pivots, so no visible kink anywhere."""
    import re
    draw = SRC[SRC.index("f_lrlDraw(LrlSide s, Lrl r) =>"):SRC.index("f_lrlRender(LrlSide s, int slot) =>")]
    assert "polyline" not in SRC and "chart.point" not in SRC
    chord = re.findall(r"line\.new\(x0, s\.sign \* r\.yAt\(x0\), x1, s\.sign \* r\.yAt\(x1\), .*style = line\.style_solid", draw)
    proj = re.findall(r"line\.new\(x1, s\.sign \* r\.yAt\(x1\), x2, s\.sign \* r\.yAt\(x2\), .*style = line\.style_dashed", draw)
    assert len(chord) == 1 and len(proj) == 1
    assert "int   x0     = r.xs.first()" in draw and "int   x1     = r.xs.last()" in draw


def test_lrl_style_solid_stronger_than_projection():
    """v0.6.1-dev readability pass (user, 2026-10-30): neutral grey from the chart's text colour
    (no magenta / cyan), the solid confirmed line stronger than the dashed projection, width 1,
    a small LRL label."""
    import re
    solid = {int(t) for t in re.findall(r"^LRL_(?:BEAR|BULL)_COL = color\.new\(chart\.fg_color, (\d+)\)", SRC, re.M)}
    proj = re.search(r"^LRL_PROJ_T\s+=\s+(\d+)", SRC, re.M)
    assert len(solid) == 1 and proj and int(proj[1]) > solid.pop()
    draw = SRC[SRC.index("f_lrlDraw(LrlSide s, Lrl r) =>"):SRC.index("f_lrlRender(LrlSide s, int slot) =>")]
    assert "color.new(base, active ? LRL_PROJ_T : 75), style = line.style_dashed, width = 1" in draw
    assert '"LRL", xloc = xloc.bar_index' in draw and "size = size.tiny" in draw


def test_lrl_never_reads_phase1_or_phase2_state():
    """DEF-LRL8 in Pine: the LRL engine methods and its engine-run block mention no FVG,
    session, reference-level, BSL/SSL or EQ state (only bars, its own TR average, EQ_TOL
    and EPS)."""
    lines = SRC.splitlines()
    a = next(i for i, ln in enumerate(lines) if ln.startswith("// ── LRL (DEF-LRL1…LRL6"))
    b = next(i for i, ln in enumerate(lines) if ln.startswith("// ════ L6 · RENDERER (functions"))
    run = next(i for i, ln in enumerate(lines) if "// ── LRL (DEF-LRL1…LRL8)" in ln)
    body = "\n".join(lines[a:b] + lines[run:run + 9])
    for name in ("bslS", "sslS", "bullFvgs", "bearFvgs", "liveLvl", "liveSes", "histLvl", "histSes", "Liq ",
                 "EqCluster", "liqTra", "sigHi", "sigLo", "pivHi", "pivLo", "liqOn", "lrlShow", "lrlHist", "lrlMarks"):
        assert name not in body, name
