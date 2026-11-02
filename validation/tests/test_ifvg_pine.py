"""IFVG in src/IST.pine (v0.9.0-dev; memory revised in v0.9.1-dev, tests/test_ifvg_memory.py). Pine runs IFVG-R as transliterated in validation/models/ifvg.py
IfvgPine (written from the Pine code: advanceIfvg on the active records, then observeIfvg over the
shadows of the Phase 1 FVG engine, invertIfvg). Proven here: it equals the approved oracle (IfvgEngine)
on every case of the approval list (1–35) and on the real data, record for record and event for event;
the Pine diff against the frozen displacement baseline only adds lines; ST-23 pins every IFVG-R line
and each listed mutation is caught. Nothing here runs Pine: compilation and runtime stay MANUAL /
TRADINGVIEW (docs/TESTS_IFVG.md, IFVG-L00…)."""
import re
import statistics
import subprocess

import pytest

from validation import PINE_SOURCE, ROOT
from validation.candles import from_rows, mirror, random_walk, shift
from validation.models.events import EventLog
from validation.models.fvg import FvgEngine
from validation.models.ifvg import PRE, IfvgEngine, IfvgPine
from validation.models.ist import IstModel
from validation.models.types import KNOWN_MODULES, NQ_TICK, FvgSettings, IfvgSettings, Settings
from validation.static_checks import (CALC_INPUTS, CALC_SECTIONS, _ifvg_blocks, code, lines_of, source,
                                      st01_calc_independent_of_view, st04_plots_data_window_only)
from validation.static_checks import st21_no_history_in_functions as st21
from validation.static_checks import st23_ifvg_rules as st23
from validation.studies import ifvg as study

pytestmark = [pytest.mark.ifvg, pytest.mark.section("ifvg")]
SRC = PINE_SOURCE.read_text(encoding="utf-8")
BIG = 10 ** 6

# (100, 101, 99, 100) × 16, then a Phase 1 bullish FVG confirmed on bar 17: bottom 101, top 103, CE 102.
FLAT = (100, 101, 99, 100)
BASE = [FLAT] * 16 + [(100, 104, 100, 104), (104, 106, 103, 105)]
INV = (102, 102.5, 100, 100.75)                       # bar 18: close one tick below the bottom
LIFE = BASE + [INV,
               (100.75, 101, 100, 100.5),             # 19 retest: high reaches the near edge 101
               (100.5, 102, 100.5, 101.5),            # 20 CE (high 102)
               (101.5, 103, 101.5, 102.5),            # 21 far edge reached, close inside
               (102.5, 103.25, 102.5, 103),           # 22 wick through the far edge, close exactly on it: active
               (103, 103.5, 103, 103.25)]             # 23 close one tick beyond the far edge: INVALIDATED


def run(cls, cs, fs=FvgSettings(memory=BIG), isx=IfvgSettings(memory=BIG)):
    log = EventLog()
    f = FvgEngine(fs, NQ_TICK, log)
    e = cls(isx, NQ_TICK, log, f)
    for t, c in enumerate(cs):
        log.at(t, c.time)
        f.step(t, c)
        e.step(t, c)
    return e, log.events


def same(cs, fs=FvgSettings(memory=BIG), isx=IfvgSettings(memory=BIG)):
    """Pine's formulation = the oracle: every record field, every event (in emission order), the
    counters and the shadows = the oracle's registry. Returns per IFVG (parent bar, side, bar, pre,
    touch, CE, full, end)."""
    o, oe = run(IfvgEngine, cs, fs, isx)
    p, pe = run(IfvgPine, cs, fs, isx)
    assert [(r.id, r.side, r.origin_bar, r.parent_bar, r.top, r.bottom, r.mid, r.bar, r.time, r.close, r.pre, r.retest,
             r.ce, r.full, r.end) for r in o.records()] == \
           [(r.id, r.side, r.origin_bar, r.parent_bar, r.top, r.bottom, r.mid, r.bar, r.time, r.close, PRE[r.pre],
             r.touch_bar, r.ce_bar, r.full_bar, r.end_bar) for r in p.records()]
    assert all(r.end_close == cs[r.end_bar].close for r in p.records() if r.end_bar is not None)
    assert [(e.bar, e.type, e.dir, e.sid, e.origin_bar, e.price) for e in oe] == \
           [(e.bar, e.type, e.dir, e.sid, e.origin_bar, e.price) for e in pe]
    assert (o.inverted, o.dropped) == (p.inverted, p.dropped) and list(o.parents) == [z.id for z in p.shadows]
    return [(r.parent_bar, r.side, r.bar, r.pre, r.touch_bar, r.ce_bar, r.full_bar, r.end_bar) for r in p.records()]


M1 = FvgSettings(memory=1)
CASES = {   # the approval's list: (rows, Phase 1 settings, [(parent bar, side, bar, pre, touch, CE, full, end)])
    "1 bullish FVG → bearish IFVG": (BASE + [INV], None, [(17, -1, 18, 0, None, None, None, None)]),
    "3 wick beyond, close inside": (BASE + [(102, 102.5, 100, 101.5)], None, []),
    "4 close exactly at the edge": (BASE + [(102, 102.5, 100, 101)], None, []),
    "5 close one tick beyond": (BASE + [(102, 102.5, 100.75, 100.75)], None, [(17, -1, 18, 0, None, None, None, None)]),
    "6 gap through the edge, immediate": (BASE + [(99, 99.5, 98.5, 99)], None, [(17, -1, 18, 0, None, None, None, None)]),
    "7 after FIRST_TOUCH": (BASE + [(104, 104, 102.5, 103.5), (102, 102, 100, 100.75)], None,
                            [(17, -1, 19, 1, None, None, None, None)]),
    "8 after CE": (BASE + [(104, 104, 102, 102.5), (102, 102, 100, 100.75)], None, [(17, -1, 19, 2, None, None, None, None)]),
    "9 after FULL_FILL": (BASE + [(104, 104, 101, 102), (102, 102, 100, 100.75)], None,
                          [(17, -1, 19, 3, None, None, None, None)]),
    "10 invalidated and released by Phase 1 on the same bar": (
        [FLAT] * 16 + [(100, 100, 98, 98.5), (103, 104, 103, 103.5), (102, 102, 100.5, 100.75)], M1,
        [(17, -1, 18, 0, None, None, None, None)]),
    "11 released by Phase 1 earlier, never inverts": (
        BASE + [(105, 108, 105, 108), (108, 110, 107.5, 109), (109, 109, 99, 99.5)], M1,
        [(19, -1, 20, 0, None, None, None, None)]),
    # bar 19 is also a bearish FVG [101, 103] (fully filled on 21) that bar 23 inverts: a bullish IFVG
    "15–17, 19, 20 lifecycle (retest, CE, full; close on the edge; end)": (
        LIFE, None, [(19, 1, 23, 3, None, None, None, None), (17, -1, 18, 0, 19, 20, 21, 23)]),
    "18 wick through the far edge, close inside": (LIFE[:22] + [(102.5, 103.5, 102, 102.5)], None,
                                                   [(17, -1, 18, 0, 19, 20, 21, None)]),
    "21 every fact and the end on one bar": (BASE + [INV, (100.75, 104, 100.5, 103.5)], None,
                                             [(17, -1, 18, 0, 19, 19, 19, 19)]),
    # bar 24 closes below 101 again: the ended bar-17 IFVG stays as it was (the bullish FVGs of bars 21
    # and 22 invert there, and the bar-23 bullish IFVG ends on that close)
    "22 no second inversion": (LIFE + [(103.25, 104, 99, 99.5), (99.5, 104, 99, 100)], None,
                               [(19, 1, 23, 3, 24, 24, 24, 24), (17, -1, 18, 0, 19, 20, 21, 23),
                                (21, -1, 24, 0, 25, 25, 25, None), (22, -1, 24, 0, 25, 25, 25, None)]),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_case_pine_equals_oracle(name):
    rows, fs, want = CASES[name]
    assert same(from_rows(rows), fs or FvgSettings(memory=BIG)) == want


@pytest.mark.parametrize("name", sorted(CASES))
def test_case_mirror(name):                                       # 2, 23
    rows, fs, want = CASES[name]
    got = same(mirror(from_rows(rows), 0.0), fs or FvgSettings(memory=BIG))
    assert sorted(got) == sorted((b, -s, *x) for b, s, *x in want)


def test_12_13_geometry_and_identity_copied_exactly():
    cs = from_rows(LIFE)
    p, _ = run(IfvgPine, cs)
    f = FvgEngine(FvgSettings(memory=BIG), NQ_TICK, EventLog())
    for t, c in enumerate(cs):
        f.step(t, c)
    r, z = p.bear[0], f.bull[0]
    assert (r.id, r.top, r.bottom, r.mid, r.origin_bar, r.origin_time, r.parent_bar, r.parent_time) == \
           (z.id, z.top, z.bottom, z.mid, z.origin_bar, z.origin_time, z.confirm_bar, z.confirm_time) == \
           (z.id, 103.0, 101.0, 102.0, 15, cs[15].time, 17, cs[17].time)
    moved, _ = run(IfvgPine, shift(cs, 250.0))
    assert [(x.id, x.side, x.bar, x.top - 250.0, x.bottom - 250.0) for x in moved.records()] == \
           [(x.id, x.side, x.bar, x.top, x.bottom) for x in p.records()]


def test_14_the_inversion_bar_is_not_a_retest_and_21_facts_come_before_the_end():
    _, ev = run(IfvgPine, from_rows(BASE + [INV, (100.75, 104, 100.5, 103.5)]))
    assert [(e.bar, e.type) for e in ev if e.type.startswith("IFVG_")] == \
           [(18, "IFVG_INVERTED"), (19, "IFVG_FIRST_TOUCH"), (19, "IFVG_INVALIDATED")]


# ── real data, memory, determinism, independence ──
@pytest.fixture(scope="module")
def segs():
    return study.segments()


def test_real_data_pine_equals_oracle_exactly(segs):
    """The research dataset: 652 Phase 1 FVGs, 566 inversions (272 from bullish FVGs, 294 from
    bearish), median 9 bars from confirmation to inversion — Pine's formulation gives the oracle's
    records exactly."""
    flat = [r for _, cs in segs for r in same(cs)]
    fvgs = sum(len(study.parents(cs, i)) for i, (_, cs) in enumerate(segs))
    assert (fvgs, len(flat), sum(r[1] < 0 for r in flat), sum(r[1] > 0 for r in flat)) == (652, 566, 272, 294)
    assert statistics.median(r[2] - r[0] for r in flat) == 9


def test_24_memory_50_per_side_on_real_data(segs):
    """The approved settings (Phase 1 memory 50, IFVG memory 50 per side) on the real data, both
    models; no active IFVG is ever dropped there."""
    for (_, cs), want in zip(segs, [(266, 166), (140, 40), (160, 60)]):
        same(cs, FvgSettings(), IfvgSettings())
        p, ev = run(IfvgPine, cs, FvgSettings(), IfvgSettings())
        assert (p.inverted, p.dropped) == want and max(len(p.bull), len(p.bear)) == 50
        assert not [e for e in ev if e.type == "IFVG_DROPPED_MEMORY" and e.meta == "active record"]


def test_25_deterministic_full_replay(segs):
    cs = segs[2][1]
    a, ae = run(IfvgPine, cs)
    b, be = run(IfvgPine, list(cs))
    assert a.records() == b.records() and ae == be


@pytest.mark.parametrize("mods", [("fvg", "ifvg"), ("fvg", "liq", "ifvg"), ("fvg", "liq", "lrl", "ifvg"),
                                  ("fvg", "cisd", "ifvg"), ("fvg", "disp", "ifvg"), KNOWN_MODULES])
def test_30_31_32_the_same_ifvgs_with_any_other_module(segs, mods):
    cs = segs[0][1]
    assert IstModel(Settings(modules=mods)).run(cs).ifvg.state() == \
           IstModel(Settings(modules=("fvg", "ifvg"))).run(cs).ifvg.state()


# ── the Pine source ──
def test_pine_source_passes_st23_and_st21():                     # 34
    for check in (st23, st21):
        ok, detail = check()
        assert ok, detail


def test_26_to_32_the_engine_reads_no_view_input_and_no_other_module():
    """Visibility, the FVG Show toggle, debug, the capture and alerts are [view] inputs: no calculation
    section reads them; the IFVG engine reads no CISD, displacement, liquidity, LRL or HTF FVG state."""
    view = ("fvgShow", "fvgShowCE", "dbgOn", "capOn", "capN", "dbgIfvg")
    calc = "\n".join(code(ln) for _, ln in lines_of(CALC_SECTIONS))
    engine = "\n".join(_ifvg_blocks(list(source())))
    assert not set(view) & CALC_INPUTS and "ifvgOn" in CALC_INPUTS and st01_calc_independent_of_view()[0]
    assert not [n for n in view if re.search(rf"\b{n}\b", calc)]
    assert not re.search(r"\b(cisd\w*|Cisd\w*|disp\w*|Disp\w*|liq\w*|Liq\w*|lrl\w*|Lrl\w*|htf\w*|Htf\w*|sig\w*|piv\w*)\b",
                         engine)


def test_33_phase_1_and_every_frozen_line_unchanged():
    """Against the frozen DISPLACEMENT_BASELINE_v0.8.0-dev source the v0.9.0-dev diff only ADDS lines,
    except the four that carry the build: the header, IST_BUILD, the CAPTURE line and the BAR line."""
    try:
        diff = subprocess.run(["git", "diff", "--no-color", "-U0", "DISPLACEMENT_BASELINE_v0.8.0-dev", "--",
                               "src/IST.pine"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git or the baseline tag not available")
    gone = [ln[1:] for ln in diff.splitlines() if ln.startswith("-") and not ln.startswith("---")]
    assert len(gone) == 4 and [re.match(p, g) is not None for p, g in zip(
        (r"//  ICT STRUCTURE TOOLKIT \(IST\) · v0\.8\.0-dev", r'IST_BUILD\s+= "v0\.8\.0-dev"',
         r'\s+log\.info\("CAPTURE\|build=', r'\s+log\.info\("BAR\|'), gone)] == [True] * 4, gone


def test_no_renderer_no_alert_data_window_only():
    l6 = "\n".join(code(ln) for _, ln in lines_of(("L6 · RENDERER (functions", "L6 · RENDERER (run)")))
    assert l6 and not re.search(r"\b(ifvg\w*|Ifvg\w*)\b", l6)
    plots = [ln for ln in SRC.splitlines() if ln.startswith("plot(") and "IFVG" in ln]
    assert len(plots) == 4 and all(ln.startswith("plot(dbgIfvg ? ") for ln in plots) and st04_plots_data_window_only()[0]
    assert "EV_IFVG_INVERTED  => false" in SRC and "table.new(position.bottom_right, 2, 52," in SRC


def test_capture_lines():
    for key in ('"|ifvg="', '"|ifvgmem="', '"|IS="', '"|IA="', '"|IX="', '"IFVGSTATE|at="', '"FVGREC|dir=1|id="',
                '"FVGREC|dir=-1|id="', '"IFVGREC|side="', "if ifvgOn and capDone == fvgLen + 2"):
        assert key in SRC, key


def _block(start, end):
    i = SRC.index(start)
    return SRC[i:SRC.index(end, i)]


BEAR_FACTS = _block("        if na(r.touchBar) and high >= r.bottom\n", "        if close > r.top\n")
BEAR_END = _block("        if close > r.top\n", "    else\n")
MUTATIONS = {
    "a second close rule (no EPS)": ("if not na(z.invBar) and z.invBar == bar_index",
                                     "if (z.isBull ? close < z.bottom : close > z.top)"),
    "a wick inverts": ("if not na(z.invBar) and z.invBar == bar_index",
                       "if (z.isBull ? low < z.bottom : high > z.top)"),
    "inversion one bar late": ("z.invBar == bar_index\n", "z.invBar == bar_index - 1\n"),
    "the same side as the FVG": ("int  s = z.isBull ? -1 : 1", "int  s = z.isBull ? 1 : -1"),
    "geometry from the FVG's extreme": ("z.top, z.bottom, z.mid, bar_index", "z.extreme, z.bottom, z.mid, bar_index"),
    "CE recomputed": ("z.top, z.bottom, z.mid, bar_index", "z.top, z.bottom, (z.top + z.bottom) / 2, bar_index"),
    "the inversion bar is a retest": ("for r in ifvgBook.bull\n            if na(r.endBar) and bar_index > r.invBar",
                                      "for r in ifvgBook.bull\n            if na(r.endBar) and bar_index >= r.invBar"),
    "retest at the CE": ("if na(r.touchBar) and high >= r.bottom", "if na(r.touchBar) and high >= r.mid"),
    "full at the near edge": ("if na(r.fullBar) and low <= r.bottom", "if na(r.fullBar) and low <= r.top"),
    "end on a close at the far edge": ("        if close > r.top\n", "        if close >= r.top\n"),
    "end on a wick": ("        if close < r.bottom\n", "        if low < r.bottom\n"),
    "a close back inside ends": ("        if close > r.top\n", "        if close > r.top or close < r.bottom\n"),
    "the close before the facts": (BEAR_FACTS + BEAR_END, BEAR_END + BEAR_FACTS),
    "the observer before the advance": ("        for r in ifvgBook.bull\n            if na(r.endBar)",
                                        "        ifvgBook.observeIfvg()\n        for r in ifvgBook.bull\n            if na(r.endBar)"),
    "a shadow released while open stays": ("        else if f_ifvgDroppedOpen(z)\n            b.shadows.remove(i)\n", ""),
    "a released closed FVG leaves too": ("and old.isBull == z.isBull and na(old.invBar)", "and old.isBull == z.isBull"),
    "only shown FVGs join": ("        if nb.confirmBar == bar_index\n", "        if nb.confirmBar == bar_index and fvgShow\n"),
    "the observer writes Phase 1": ("            b.invertIfvg(z)\n", "            b.invertIfvg(z)\n            z.invBar := na\n"),
    "the observer removes a Phase 1 record": ("            b.shadows.remove(i)\n        else if",
                                              "            bullFvgs.remove(0)\n            b.shadows.remove(i)\n        else if"),
    "memory 60": ("IFVG_MEM     = 50 ", "IFVG_MEM     = 60 "),
    "the newest record dropped": ("            recs.remove(i)\n", "            recs.pop()\n"),
    "an ACTIVE record evicted (the v0.9.0-dev fallback)": ("        if na(x.endBar)\n            i += 1\n",
                                                           "        if na(x.endBar) and recs.size() <= IFVG_MEM\n            i += 1\n"),
    "compaction stops at the first ACTIVE record": ("        if na(x.endBar)\n            i += 1\n",
                                                    "        if na(x.endBar)\n            break\n"),
    "no memory after the bar's ends": ("        ifvgBook.compactIfvg(ifvgBook.bull)\n        ifvgBook.compactIfvg(ifvgBook.bear)\n", ""),
    "memory before the advance": ("        ifvgBook.compactIfvg(ifvgBook.bull)\n        ifvgBook.compactIfvg(ifvgBook.bear)\n"
                                  "        ifvgBook.observeIfvg()\n", "        ifvgBook.observeIfvg()\n"
                                  "        ifvgBook.compactIfvg(ifvgBook.bull)\n        ifvgBook.compactIfvg(ifvgBook.bear)\n"),
    "no memory after an inversion": ("    b.compactIfvg(recs)\n", ""),
    "a cap of active records": ("    while recs.size() > IFVG_MEM and i < recs.size()\n",
                                "    while recs.size() > IFVG_MEM and i < recs.size() - 1\n"),
    "a debug toggle gates detection": ("    if ifvgOn and barstate.isconfirmed\n", "    if ifvgOn and dbgOn and barstate.isconfirmed\n"),
    "the capture gates detection": ("    if ifvgOn and barstate.isconfirmed\n", "    if ifvgOn and capOn and barstate.isconfirmed\n"),
    "CISD gates detection": ("    if ifvgOn and barstate.isconfirmed\n", "    if ifvgOn and cisdOn and barstate.isconfirmed\n"),
    "a Data Window value read by detection": ("    if ifvgOn and barstate.isconfirmed\n",
                                               "    if ifvgOn and barstate.isconfirmed and f_ifvgActive(ifvgBook.bull) >= 0\n"),
    "a history read in the engine": ("if na(r.touchBar) and high >= r.bottom", "if na(r.touchBar) and high[1] >= r.bottom"),
    "event without its side": ("f_emit(EV_IFVG_INVERTED, s,", "f_emit(EV_IFVG_INVERTED, 0,"),
    "IFVG alerts on": ("EV_IFVG_INVERTED  => false", "EV_IFVG_INVERTED  => true"),
}


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_mutation_is_caught(name):
    old, new = MUTATIONS[name]
    assert SRC.count(old) == 1, f"mutation anchor not found once: {old!r}"
    ok, detail = st23(SRC.replace(old, new))
    assert not ok, f"{name}: ST-23 still passes ({detail})"


def test_st21_catches_a_history_read_inside_the_engine():
    """The v0.7.0-dev defect class: a user-series history read inside a method that does not run on
    every bar reads an earlier CALL. ST-21 and ST-23 both catch it."""
    old, new = "if na(r.touchBar) and high >= r.bottom", "if na(r.touchBar) and high >= r.bottom and not rawBull[1]"
    ok, detail = st21(SRC.replace(old, new))
    assert not ok and "advanceIfvg: rawBull[1]" in detail and not st23(SRC.replace(old, new))[0]
