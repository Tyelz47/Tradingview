"""HTF FVG in src/IST.pine (v0.6.0-dev): ST-03 pins the six [1]-only requests, ST-19 the approved
constants and every timing / definition line of the oracle, and each mutation that would
repaint or change the definition is caught. The view rules the user approved (D1, D6–D10) are
read from the source. Nothing here runs Pine: compilation and runtime stay MANUAL / TRADINGVIEW."""
import re

import pytest

from validation import PINE_SOURCE
from validation.static_checks import code
from validation.static_checks import st03_request_security_no_leak as st03
from validation.static_checks import st18_no_overloaded_functions as st18
from validation.static_checks import st19_htf_rules as st19

pytestmark = [pytest.mark.htf, pytest.mark.section("htf")]
SRC = PINE_SOURCE.read_text(encoding="utf-8")

# name → (exact text in IST.pine, replacement, …): each one repaints or changes the approved definition.
MUTATIONS = {
    "lookahead_off": ('f_htfReq("60"), f_htfPack(), lookahead = barmerge.lookahead_on)',
                      'f_htfReq("60"), f_htfPack(), lookahead = barmerge.lookahead_off)'),
    "candle 3 = the unfinished HTF bar": ("bool  up   = low[1] > high[3]", "bool  up   = low > high[2]"),
    "a [0] read": ("float rng  = ta.sma(high[1] - low[1], fvgLen)", "float rng  = ta.sma(high[0] - low[0], fvgLen)"),
    "TR average including the unfinished bar": ("ta.sma(ta.tr(true)[1], fvgLen)", "ta.sma(ta.tr(true), fvgLen)"),
    "a timeframe request removed": ('[xWt, xWo, xWh, xWl, xWc, xWtra, xWrng, xWd, xWtop, xWbot, xWc1, xWsd, xWb3] = '
                                    'request.security(syminfo.tickerid, f_htfReq("W"), f_htfPack(), lookahead = barmerge.lookahead_on)\n', ""),
    "thresholds at candle 3": ("fvgMinTra * tra[2] : 0.0", "fvgMinTra * tra : 0.0"),
    "no TR-average threshold": ("and gap >= traQ and gap >= rngQ", "and gap >= rngQ"),
    "invalidation by the chart close (D5)": ("(r.dir > 0 ? s.bC < r.bottom : s.bC > r.top)", "(r.dir > 0 ? close < r.bottom : close > r.top)"),
    "a zone invalidated by its own candle 3": ("if na(r.invBar) and s.bT > r.id and", "if na(r.invBar) and s.bT >= r.id and"),
    "box origin at candle 3 (D8)": ("HtfZone.new(s.zDir, s.bT, s.zC1,", "HtfZone.new(s.zDir, s.bT, s.bT,"),
    "retroactive touches on seeds": ("if na(r.touchBar) and not r.preTouch and", "if na(r.touchBar) and"),
    "milestones on the close": ("float reach = r.dir > 0 ? low : high", "float reach = close"),
    "seed engine keeps fully filled zones": ("(low[1] <= zs.get(i, 2) or close[1] < zs.get(i, 2))", "(close[1] < zs.get(i, 2))"),
    "memory 30": ("HTF_MEM      = 20 ", "HTF_MEM      = 30 "),
    "5 seeds": ("HTF_SEEDS    = 3 ", "HTF_SEEDS    = 5 "),
    "memory drops open records first": ("            if not na(r.invBar) or not na(r.fullBar)\n", "            if true\n"),
    "create before invalidate": (
        "            for r in s.recs\n                if na(r.invBar) and s.bT > r.id and (r.dir > 0 ? s.bC < r.bottom : s.bC > r.top)\n"
        "                    r.invBar   := bar_index\n                    r.invClose := s.bC\n"
        "                    f_emitHtf(EV_HTF_INVAL, s, r, s.bC, \"close=\" + f_x(s.bC))\n",
        "",
        "                s.trimHtf()\n        s.milestonesHtf()",
        "                s.trimHtf()\n            for r in s.recs\n"
        "                if na(r.invBar) and s.bT > r.id and (r.dir > 0 ? s.bC < r.bottom : s.bC > r.top)\n"
        "                    r.invBar   := bar_index\n                    r.invClose := s.bC\n"
        "                    f_emitHtf(EV_HTF_INVAL, s, r, s.bC, \"close=\" + f_x(s.bC))\n        s.milestonesHtf()"),
    "a lower timeframe requested": ("timeframe.in_seconds(tf) > timeframe.in_seconds() ? tf : timeframe.period", "tf"),
}


def _mutate(old_new: tuple) -> str:
    src = SRC
    for old, new in zip(old_new[::2], old_new[1::2]):
        assert src.count(old) == 1, f"mutation anchor not unique or missing: {old!r}"
        src = src.replace(old, new)
    return src


def test_st03_st19_pass_on_the_source():
    for check in (st03, st19, st18):
        ok, detail = check()
        assert ok, detail


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_mutation_is_caught(name):
    src = _mutate(MUTATIONS[name])
    assert not (st03(src)[0] and st19(src)[0]), f"{name} was not caught"


def _between(a: str, b: str) -> str:
    return SRC[SRC.index(a):SRC.index(b)]


def test_htf_never_reads_other_modules_state():
    """Module B reads its own requests, the Phase 1 [calc] FVG inputs (D4) and this bar's
    wicks: no FVG, session, level, liquidity or LRL state, and no display input in L3."""
    body = (_between("f_htfPack() =>", "f_htfReq(string tf) =>")
            + _between("// ── HTF fair value gaps (DEF-B0…B6", "// ════ L6 · RENDERER (functions"))
    for name in ("bslS", "sslS", "bullFvgs", "bearFvgs", "liveLvl", "liveSes", "lrlHi", "lrlLo", "rawGap", "refTra",
                 "gapPass", "htfShow", "htfOn15", "htfLabels", "htfCompact", "fvgShow"):
        assert name not in body, name


def test_renderer_rules():
    """D6: per timeframe the nearest open zone above and below (≤ 12 boxes). D1: drawn 1W first,
    15m last, no hiding or merging. D7: neutral grey, opacity tiers only. D8: the box starts at
    HTF candle 1. D10 + labels: the full text at the bottom right, the compact form a Developer
    option."""
    render = _between("f_htfRender(HtfTf s) =>", "// ════ ENGINE RUN")
    assert render.count("f_htfBox(s, up)") == 1 and render.count("f_htfBox(s, dn)") == 1
    box = _between("f_htfBox(HtfTf s, HtfZone r) =>", "f_htfRender(HtfTf s) =>")
    assert box.count("box.new(") == 1 and "box.new(r.c1, r.top, rightT, r.bottom, xloc = xloc.bar_time" in box
    assert "text_halign = text.align_right, text_valign = text.align_bottom" in box and "text_size = HTF_TXT_SIZE" in box
    # readability (user, 2026-10-30): one step larger (v0.6.1-dev), dark grey-brown, opaque (v0.6.2-dev)
    assert re.search(r"^HTF_TXT_SIZE = size\.small\b", SRC, re.M)
    assert re.search(r"^HTF_TXT_COL  = color\.new\(#4F473F, 0\)", SRC, re.M)
    assert "border_width = 1" in box
    assert 's.name + (htfCompact ? " FVG" : " Fair Value Gap")' in box
    # user palette 2026-10-30 (chart background #C2BAAE): per-tier fill and border, stronger for higher timeframes
    assert "bgcolor = tier == 0 ? HTF_FILL_1 : tier == 1 ? HTF_FILL_2 : HTF_FILL_3" in box
    assert "border_color = tier == 0 ? HTF_BORDER_1 : tier == 1 ? HTF_BORDER_2 : HTF_BORDER_3" in box
    fill = [int(t) for t in re.findall(r"^HTF_FILL_[123]\s+= color\.new\(#[0-9A-F]{6}, (\d+)\)", SRC, re.M)]
    edge = [int(t) for t in re.findall(r"^HTF_BORDER_[123] = color\.new\(#[0-9A-F]{6}, (\d+)\)", SRC, re.M)]
    assert fill == [88, 84, 80] and edge == [35, 20, 10]          # each tier less transparent than the one below
    run = _between("// HTF FVG (DEF-B5): rebuilt from state", "// ════ L7 · ALERTS")
    assert "for i = htfTfs.size() - 1 to 0" in run
    assert "var array<HtfTf> htfTfs = array.from(h15, h30, h60, h240, hD, hW)" in SRC
    assert not re.search(r"contain|merge|hide", "\n".join(code(ln) for ln in (render + run).splitlines()), re.I)


def test_settings_target():
    """HTF FAIR VALUE GAPS: Show HTF FVGs ON, 15m … 1W ON, Show timeframe labels ON; compact
    labels OFF (Developer); Phase 1 'Show FVGs' OFF (D9, a reviewed deviation)."""
    for name in ("htfShow", "htfOn15", "htfOn30", "htfOn60", "htfOn240", "htfOnD", "htfOnW", "htfLabels"):
        assert re.search(rf"^{name}\s*= input\.bool\(true, .*group = G_HTF", SRC, re.M), name
    assert re.search(r'^htfCompact = input\.bool\(false, .*group = G_DBG', SRC, re.M)
    assert re.search(r'^fvgShow\s*= input\.bool\(false, "Show FVGs"', SRC, re.M)
    dev = (PINE_SOURCE.parents[1] / "validation" / "baselines" / "PHASE1_DEVIATIONS.md").read_text(encoding="utf-8")
    assert "fvgShow" in dev and "D9" in dev


def test_events_carry_the_timeframe():
    """Identity = timeframe + direction + candle-3 time: Event.tf is set on every HTF event and
    the timeframe opens its audit text (the parity parser reads it there)."""
    emit = _between("f_emitHtf(int kind", "method trimHtf")
    assert "e.tf := s.tf" in emit and '"tf=" + s.name' in emit
    calls = re.findall(r"f_emit\(EV_HTF_", SRC)
    assert not calls, "HTF events must go through f_emitHtf"
