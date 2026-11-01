"""Displacement in src/IST.pine (v0.8.0-dev). Pine runs DISPLACEMENT-R as transliterated in
validation/models/displacement.py DispPine (written from the Pine code: global-scope A and previous
extremes, factsDisp → f_dispHit → confirmDisp). Proven here: it equals the approved oracle
(DisplacementEngine) on every case of the approval list and on the real data, record for record and
event for event; ST-22 pins every DISPLACEMENT-R line of the Pine source; each listed mutation is
caught, the v0.7.0-dev call-history defect (ST-21) among them. Nothing here runs Pine: compilation
and runtime stay MANUAL / TRADINGVIEW (docs/TESTS_DISPLACEMENT.md, DISP-L00…)."""
import re
from dataclasses import replace

import pytest

from validation import PINE_SOURCE
from validation.candles import MINUTE, from_rows, mirror, random_walk
from validation.models.displacement import DispPine, DisplacementEngine
from validation.models.events import EventLog
from validation.models.types import NQ_TICK, DispSettings
from validation.static_checks import (CALC_INPUTS, RENDER_SECTIONS, code, lines_of, st01_calc_independent_of_view,
                                      st04_plots_data_window_only)
from validation.static_checks import st21_no_history_in_functions as st21
from validation.static_checks import st22_disp_rules as st22
from validation.studies import displacement as study

pytestmark = [pytest.mark.disp, pytest.mark.section("disp")]
SRC = PINE_SOURCE.read_text(encoding="utf-8")
FLAT = (100, 101, 99, 100)                 # true range 2: after 14 of them A = 2, the body threshold 3 points
W = 15
FVG = {None: 0, True: 1, False: -1}


def run(cls, cs, s=DispSettings(memory=10 ** 6)):
    log = EventLog()
    e = cls(s, NQ_TICK, log)
    for t, c in enumerate(cs):
        log.at(t, c.time)
        e.step(t, c)
    return e, log.events


def same(cs, s=DispSettings(memory=10 ** 6)):
    """Pine's formulation = the oracle: every record field and every event. Returns (bar, side, fvg) per record."""
    o, oe = run(DisplacementEngine, cs, s)
    p, pe = run(DispPine, cs, s)
    assert [(r.bar, r.side, r.id, r.open, r.high, r.low, r.close, r.tra, r.body_k, r.range_k, r.clv, r.prev_ext,
             FVG[r.fvg]) for r in o.recs] == \
           [(r.bar, r.side, r.id, r.o, r.h, r.l, r.c, r.tra, r.body_k, r.range_k, r.clv, r.prev_ext, r.fvg) for r in p.recs]
    assert [(e.bar, e.type, e.dir, e.sid, e.origin_bar, e.price) for e in oe] == \
           [(e.bar, e.type, e.dir, e.sid, e.origin_bar, e.price) for e in pe]
    assert (o.confirmed, o.dropped) == (p.confirmed, p.dropped)
    return [(r.bar, r.side, r.fvg) for r in p.recs]


def one(*candles):
    return from_rows([FLAT] * W + list(candles))


def session_break():
    """A 61-minute break (CME 17:00–18:00) before bar W, which gaps up 10 points: A at bar W is still
    the 14 bars before the break, the body counts only the candle's own 3 points."""
    cs = one((110, 113, 110, 113), (113, 116, 113, 116), (116, 116.75, 115.75, 116.5))
    return cs[:W] + [replace(c, time=c.time + 60 * MINUTE) for c in cs[W:]]


CASES = {   # the approval's list: (candles, [(bar, side, Pine fvg)])
    "exact 1.5 threshold": (one((100, 103, 100, 103)), [(W, 1, 0)]),
    "just below 1.5": (one((100, 102.75, 100, 102.75)), []),
    "just above 1.5": (one((100, 103.25, 100, 103.25)), [(W, 1, 0)]),
    "bearish mirror": (one((100, 100, 97, 97)), [(W, -1, 0)]),
    "exact 0.75 close position": (one((100, 104, 100, 103)), [(W, 1, 0)]),
    "just below 0.75": (one((100, 104.25, 100, 103)), []),
    "large range, small body": (one((100, 110, 95, 101)), []),
    "large body, weak close": (one((100, 106, 100, 103.5)), []),
    "previous high not broken": (one((100, 108, 99, 100), (104, 108, 104, 108)), []),
    "previous high broken by one tick": (one((100, 108, 99, 100), (104, 108.25, 104, 108.25)), [(W + 1, 1, 0)]),
    "previous low not broken": (one((100, 101, 92, 100), (96, 96, 92, 92)), []),
    "doji": (one((100, 105, 95, 100)), []),
    "zero range": (one((100, 100, 100, 100)), []),
    "TR warm-up (bar 13)": (from_rows([FLAT] * 13 + [(100, 103, 100, 103)]), []),
    "first decidable bar (14)": (from_rows([FLAT] * 14 + [(100, 103, 100, 103)]), [(14, 1, 0)]),
    "A = 0": (from_rows([(100, 100, 100, 100)] * W + [(100, 100.25, 100, 100.25)]), []),
    "session transition (gap up, A from before the break)": (session_break(), [(W, 1, 1)]),
    "gap open, small body": (one((110, 110.75, 109.75, 110.5)), []),
    "FVG metadata YES": (one((100, 103, 100, 103), (103, 104, 101.25, 104)), [(W, 1, 1)]),
    "FVG metadata NO": (one((100, 103, 100, 103), (103, 104, 100.75, 103.5)), [(W, 1, -1)]),
    "FVG metadata YES, bearish": (one((100, 100, 97, 97), (97, 98.75, 96, 96.5)), [(W, -1, 1)]),
    "two in a row (the first one's FVG resolved before the second is recorded)":
        (one((100, 103, 100, 103), (103, 106.5, 103, 106.5)), [(W, 1, 1), (W + 1, 1, 0)]),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_case_pine_equals_oracle(name):
    cs, want = CASES[name]
    assert same(cs) == want


@pytest.mark.parametrize("name", sorted(CASES))
def test_case_mirror(name):
    cs, want = CASES[name]
    assert same(mirror(cs, 0.0)) == [(b, -s, f) for b, s, f in want]


def test_memory_50_on_real_data():
    cs = study.segments()[0][1]                          # 57 displacements: 7 drops
    o, oe = run(DisplacementEngine, cs, DispSettings())
    assert len(same(cs, DispSettings())) == 50 and o.dropped == 7
    assert sum(e.type == "DISPLACEMENT_DROPPED_MEMORY" for e in oe) == 7


def test_real_data_pine_equals_oracle_exactly():
    """On the research dataset Pine's formulation gives the oracle's 110 records, field for field."""
    assert [len(same(cs)) for _, cs in study.segments()] == [57, 23, 30]


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_walks_pine_equals_oracle(seed):
    assert len(same(random_walk(4000, seed, gap_prob=0.02), DispSettings())) == 50


def test_deterministic_full_replay():
    cs = study.segments()[2][1]
    a, ae = run(DispPine, cs)
    b, be = run(DispPine, list(cs))
    assert a.recs == b.recs and ae == be


# ── the Pine source ──
def test_pine_source_passes_st22_and_st21():
    for check in (st22, st21):
        ok, detail = check()
        assert ok, detail


ENGINE = ("        dispBook.factsDisp(rawBull, rawBear)\n"
          "        if not na(dispTraPrv) and dispTraPrv > 0\n"
          "            dispSide := f_dispHit(1, dispTraPrv, dispPrvHi) ? 1 : f_dispHit(-1, dispTraPrv, -dispPrvLo) ? -1 : 0\n"
          "            if dispSide != 0\n"
          "                dispBook.confirmDisp(dispSide, dispTraPrv, dispSide > 0 ? dispPrvHi : dispPrvLo)\n")
MUTATIONS = {
    "direction by the wick": ("cl > o + EPS and cl - o >= DISP_K * a", "h > o + EPS and cl - o >= DISP_K * a"),
    "a doji passes (no EPS)": ("cl > o + EPS and cl - o", "cl >= o and cl - o"),
    "close at the previous extreme passes": ("cl > pe + EPS\n", "cl >= pe\n"),
    "body threshold 1.0": ("DISP_K       = 1.5 ", "DISP_K       = 1.0 "),
    "strong close 0.5": ("DISP_CLOSE   = 0.75 ", "DISP_CLOSE   = 0.5 "),
    "TR length 20": ("DISP_TRA_LEN = 14 ", "DISP_TRA_LEN = 20 "),
    "memory 60": ("DISP_MEM     = 50 ", "DISP_MEM     = 60 "),
    "no range check": ("rg > 0 and cl - lo", "cl - lo"),
    "A includes the candle itself": ("float dispTraPrv = dispTra[1]\n", "float dispTraPrv = dispTra\n"),
    "A read inside the engine (call history, v0.7.0-dev)": ("cl - o >= DISP_K * a", "cl - o >= DISP_K * dispTra[1]"),
    "the CISD TR series (M9)": ("float dispTra    = ta.sma(ta.tr(true), DISP_TRA_LEN)\n", "float dispTra    = cisdTraPrv\n"),
    "the previous extreme from two bars back": ("float dispPrvHi  = high[1]\n", "float dispPrvHi  = high[2]\n"),
    "bearish against the previous high": ("f_dispHit(-1, dispTraPrv, -dispPrvLo)", "f_dispHit(-1, dispTraPrv, -dispPrvHi)"),
    "an absolute floor on A (M8)": ("if not na(dispTraPrv) and dispTraPrv > 0\n", "if not na(dispTraPrv) and dispTraPrv > 4\n"),
    "FVG required (M7)": ("            if dispSide != 0\n", "            if dispSide != 0 and (dispSide > 0 ? rawBull : rawBear)\n"),
    "FVG metadata from the qualified Phase 1 FVG": ("dispBook.factsDisp(rawBull, rawBear)", "dispBook.factsDisp(bullCand, bearCand)"),
    "FVG metadata overwritten later": ("if r.fvg == 0 and r.bar == bar_index - 1", "if r.bar == bar_index - 1 or r.fvg == 0"),
    "detection before the FVG metadata": (ENGINE, ENGINE.split("\n", 1)[1] + ENGINE.split("\n", 1)[0] + "\n"),
    "a debug toggle gates detection": ("    if dispOn and barstate.isconfirmed\n", "    if dispOn and dbgOn and barstate.isconfirmed\n"),
    "the capture gates detection": ("    if dispOn and barstate.isconfirmed\n", "    if dispOn and capOn and barstate.isconfirmed\n"),
    "a Data Window value read by detection": ("        if not na(dispTraPrv) and dispTraPrv > 0\n",
                                               "        if not na(dispTraPrv) and dispTraPrv > 0 and dispCpNow > 0\n"),
    "the capture writes state": ("    capDone += 1\n", "    capDone += 1\n    dispBook.confirmDisp(1, dispTraPrv, high)\n"),
    "the newest record dropped by memory": ("        Disp old = b.recs.shift()\n", "        Disp old = b.recs.pop()\n"),
    "event without its side": ("f_emit(EV_DISP_CONFIRMED, r.side,", "f_emit(EV_DISP_CONFIRMED, 0,"),
    "displacement alerts on": ("EV_DISP_CONFIRMED => false", "EV_DISP_CONFIRMED => true"),
}


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_mutation_is_caught(name):
    old, new = MUTATIONS[name]
    assert SRC.count(old) == 1, f"mutation anchor not found once: {old!r}"
    ok, detail = st22(SRC.replace(old, new))
    assert not ok, f"{name}: ST-22 still passes ({detail})"


def test_st21_catches_a_history_read_inside_the_engine():
    """The v0.7.0-dev defect class (real capture 2026-10-30): a user-series history read inside a
    function that does not run on every bar reads an earlier CALL, not the earlier bar."""
    old, new = MUTATIONS["A read inside the engine (call history, v0.7.0-dev)"]
    ok, detail = st21(SRC.replace(old, new))
    assert not ok and "f_dispHit: dispTra[1]" in detail


# ── inputs, toggles, capture, no renderer (M4, M11) ──
def _inputs():
    return [ln for ln in SRC.splitlines() if re.match(r"^\w+\s*=\s*input\.", ln)]


def test_one_engine_toggle_no_parameter_no_view_input():
    disp = [ln for ln in _inputs() if "group = G_DISP" in ln]
    assert len(disp) == 1 and disp[0].startswith("dispOn ") and "input.bool(true" in disp[0]
    assert "dispOn" in CALC_INPUTS and st01_calc_independent_of_view()[0]


def test_no_renderer_and_no_alert():
    l6 = "\n".join(code(ln) for _, ln in lines_of(RENDER_SECTIONS))
    assert l6 and not re.search(r"\b(disp(?!lay)\w*|Disp\w*)\b", l6)
    plots = [ln for ln in SRC.splitlines() if ln.startswith("plot(") and "DISP" in ln]
    assert len(plots) == 5 and all(ln.startswith("plot(dbgDisp ? ") for ln in plots) and st04_plots_data_window_only()[0]


def test_capture_lines_and_frozen_debug_table():
    for key in ('"|disp="', '"|dispk="', '"|dispclose="', '"|disptr="', '"|dispmem="', '"|DS="', '"|DA="', '"|DK="',
                '"|DP="', '"|DF="', '"DISPSTATE|at="', '"DISPREC|side="', "if dispOn and capDone == DISP_TRA_LEN + 1"):
        assert key in SRC, key
    assert "table.new(position.bottom_right, 2, 52," in SRC      # the CISD debug rows are untouched
