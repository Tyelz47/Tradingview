"""CISD in src/IST.pine (v0.7.0-dev). Pine runs CISD-R incrementally (validation/models/cisd.py
CisdStack: per-side suffix-minimum stacks, a window restart only drops entries), never re-reading
a bar. Proven here: that formulation equals the approved oracle (CisdEngine) everywhere, legs
longer than 500 bars included; its parity snapshot restores exactly; ST-20 pins every CISD-R line
of the Pine source; each listed mutation is caught. Nothing here runs Pine: compilation and
runtime stay MANUAL / TRADINGVIEW (docs/TESTS_CISD.md)."""
import re

import pytest

from validation import PINE_SOURCE
from validation.candles import from_rows, mirror, random_walk
from validation.models.cisd import CisdEngine, CisdStack
from validation.models.events import EventLog
from validation.models.types import NQ_TICK, CisdSettings
from validation.static_checks import code, st01_calc_independent_of_view, st18_no_overloaded_functions as st18
from validation.static_checks import st20_cisd_rules as st20
from validation.studies import cisd as study
from validation.studies.lrl import nq_candles, resample

pytestmark = [pytest.mark.cisd, pytest.mark.section("cisd")]
SRC = PINE_SOURCE.read_text(encoding="utf-8")
BIG = CisdSettings(memory=10 ** 6)


def run(cls, cs, s=BIG, start=0):
    log = EventLog()
    e = cls(s, NQ_TICK, log)
    for t, c in enumerate(cs[start:], start):
        log.at(t, c.time)
        e.step(t, c)
    return e, log.events


def long_legs():
    """A bearish state (bar 3), a 10-bar down series from bar 3 (L 100) into the delivery low
    90 on bar 12, then 647 bars of range below L: an up-close spike to 89 on bar 100 (not a
    delivery candle: it never selects), the range's highest up-close high 99.5 on bar 60 (its up
    series starts on bar 59). Bar 660
    confirms the bullish CISD by a down-close gap candle (origin 657 bars back, extreme 648, leg
    extreme 560); the flip re-reads 649 bars in the oracle. Bars 661–662 confirm the bearish CISD
    from the series at bar 59 (603 bars back)."""
    rows = list(study._BEAR_STATE)
    p = 97.75
    for _ in range(9):
        rows.append((p, p + 0.25, p - 1.0, p - 0.75))
        p -= 0.75
    rows[-1] = (rows[-1][0], rows[-1][1], 90.0, rows[-1][3])          # the delivery extreme: bar 12, low 90
    i = len(rows)
    while i < 660:
        if i == 60:
            rows.append((p, 99.5, min(p, 91.75), 99.0))               # the range's highest up-close high
        elif i == 100:
            rows.append((p, 96.0, 89.0, p + 0.25))                    # up-close wick spike below the delivery low
        elif i % 2:
            rows.append((p, max(p, 96.0), min(p, 91.75), 95.5))
        else:
            rows.append((p, max(p, 96.0), 92.0, 92.25))
        p = rows[-1][3]
        i += 1
    rows += [(101.0, 101.25, 100.25, 100.5), (100.5, 100.5, 98.5, 98.75), (98.75, 98.75, 90.5, 91.0)]
    return from_rows([tuple(float(x) for x in r) for r in rows])


# ── the incremental formulation is the approved definition ──
@pytest.mark.parametrize("data", ["nq", "nq3", "nq5", "nq15", "walk1", "walk2", "walk3", "mirror", "long"] + sorted(study.SCENARIOS))
@pytest.mark.parametrize("memory", [10 ** 6, 2])
def test_incremental_equals_oracle(data, memory):
    cs = {"nq": nq_candles, "walk1": lambda: random_walk(20_000, 1, gap_prob=0.02),
          "walk2": lambda: random_walk(20_000, 2, gap_prob=0.02), "walk3": lambda: random_walk(20_000, 3, gap_prob=0.1),
          "mirror": lambda: mirror(random_walk(5000, 9, gap_prob=0.05), 20000.0), "long": long_legs}.get(
        data, lambda: resample(nq_candles(), int(data[2:])) if data.startswith("nq") else study.SCENARIOS[data])()
    s = CisdSettings(memory=memory)
    (a, ea), (b, eb) = run(CisdEngine, cs, s), run(CisdStack, cs, s)
    assert b.recs == a.recs and eb == ea and b.delivery == a.delivery and b.confirmed == a.confirmed


def test_a_leg_longer_than_500_bars_is_exact():
    """No 500-bar (or any) truncation: origin, delivery extreme, leg extreme and the flip's window
    all lie more than 500 bars back, and the incremental engine gives the oracle's exact records.
    A 500-bar history gives the same bar another level, 95.5 (the last check)."""
    cs = long_legs()
    (o, eo), (p, ep) = run(CisdEngine, cs), run(CisdStack, cs)
    assert p.recs == o.recs and ep == eo
    first, bull, bear = o.recs
    assert first.side == -1 and (bull.side, bull.bar, bull.level, bull.origin, bull.ext_bar, bull.ext, bull.leg_ext) == \
           (1, 660, 100, 3, 12, 90, 89)
    assert bull.bar - bull.origin > 500 and bull.bar - bull.ext_bar > 500 and o.max_scan > 500
    assert (bear.side, bear.bar, bear.origin, bear.ext_bar) == (-1, 662, 59, 60) and bear.bar - bear.origin > 500
    assert p.peak < 20                                       # the stacks stay small: price levels, not bars
    cut, _ = run(CisdEngine, cs[660 - 500:])                 # only the last 500 bars: another level
    assert (cut.recs[0].side, cut.recs[0].bar + 160, cut.recs[0].level) == (1, 660, 95.5)


def test_snapshot_restore_replays_exactly():
    """The parity capture's snapshot path: the state after bar k, restored into a new engine with
    bars renumbered from k, replays the rest exactly (records, events, per-bar candidates)."""
    cs = nq_candles()
    full, events = run(CisdStack, cs)
    for k in range(5, len(cs) - 50, 113):
        part, _ = run(CisdStack, cs[:k + 1])
        snap = part.snapshot()
        log = EventLog()
        e = CisdStack(BIG, NQ_TICK, log)
        e.restore(snap, cs[k])
        e.tr = {j: v for j, v in part.tr.items() if j > k - BIG.tra_len}
        for t in range(k + 1, len(cs)):
            log.at(t, cs[t].time)
            e.step(t, cs[t])
        assert e.recs[-len(full.recs[-5:]):] == full.recs[-5:] and log.events == [x for x in events if x.bar > k], k


# ── ST-20 and the mutations it must catch ──
def test_pine_source_passes_st20_and_has_no_overloads():
    ok, detail = st20()
    assert ok, detail
    assert st18()[0]


MUTATIONS = {
    "1 wick confirmation instead of close": (
        "s.sign * close > s.dL.first() + EPS", "(s.sign > 0 ? high : -low) > s.dL.first() + EPS"),
    "2 >= instead of strict >": ("s.sign * close > s.dL.first() + EPS", "s.sign * close >= s.dL.first()"),
    "3 <= instead of strict < (a bearish close at L confirms)": (
        "s.sign * close > s.dL.first() + EPS", "(s.sign > 0 ? close > s.dL.first() + EPS : close <= -s.dL.first())"),
    "4 first equal extreme instead of latest": (
        "while s.dBar.size() > 0 and lo <= s.dLow.last() + EPS", "while s.dBar.size() > 0 and lo < s.dLow.last() - EPS"),
    "5 every candle's low selects the leg extreme": (
        "    if cl < o - EPS\n        if not s.inRun\n", "    if true\n        if not s.inRun\n"),
    "6 a doji continues the delivery series": (
        "    else\n        s.inRun := false\n", "    else if math.abs(cl - o) > EPS\n        s.inRun := false\n"),
    "7 confirmation candle colour required": (
        "s.sign * close > s.dL.first() + EPS\n", "s.sign * close > s.dL.first() + EPS and s.sign * close > s.sign * open\n"),
    "8 no alternation (both sides stay armed)": ("    s.armed  := false\n", "    s.armed  := true\n"),
    "8b no restart of the state side": ("                sts.pruneCisd(bar_index)\n", "                sts.peak := sts.peak\n"),
    "9 initial state UP instead of UNKNOWN": ("    int         state = 0 ", "    int         state = 1 "),
    "10 opposite leg from the confirmation bar": ("    op.pruneCisd(eb)\n", "    op.pruneCisd(bar_index)\n"),
    "11 displacement required": (
        "s.sign * close > s.dL.first() + EPS\n", "s.sign * close > s.dL.first() + EPS and s.sign * (close - open) >= cisdTra[1]\n"),
    "12 the 200-bar guard gates detection": (
        "    if cisdOn and barstate.isconfirmed\n", "    if cisdOn and barstate.isconfirmed and bar_index >= CISD_GUARD\n"),
    "13 a display toggle gates detection": (
        "    if cisdOn and barstate.isconfirmed\n", "    if cisdOn and cisdShow and barstate.isconfirmed\n"),
    "14 side omitted from the identity": (
        '    str.tostring(r.side) + ":" + str.tostring(r.id)\n', "    str.tostring(r.id)\n"),
    "14b event without its side": (
        "f_emit(EV_CISD_CONFIRMED, r.side, r.id,", "f_emit(EV_CISD_CONFIRMED, 0, r.id,"),
    "15 a 500-bar truncation of the leg": (
        "    while s.dBar.size() > 0 and s.dBar.first() < a\n",
        "    while s.dBar.size() > 0 and (s.dBar.first() < a or bar_index - s.dBar.first() > 500)\n"),
    "15b a history buffer on the engine": (
        "float cisdTra = ta.sma(ta.tr(true), CISD_TRA_LEN)\n", "float cisdTra = ta.sma(ta.tr(true), CISD_TRA_LEN)\nmax_bars_back(cisdTra, 500)\n"),
    "15c re-reading old bars": ("    float lo = s.sign > 0 ? low : -high\n", "    float lo = s.sign > 0 ? low[1] : -high\n"),
    "the active CISD dropped by memory": ("        Cisd old = b.recs.shift()\n", "        Cisd old = b.recs.pop()\n"),
    "memory 60": ("CISD_MEM     = 50 ", "CISD_MEM     = 60 "),
    "the previous CISD never ends": ("            prv.endBar := bar_index\n", "            prv.known := bar_index\n"),
    "confirmation on the origin bar": ("ok := bar_index > s.dOrg.first() and", "ok := bar_index >= s.dOrg.first() and"),
    "L = the last delivery candle's open": ("            s.runL    := o\n", "            s.runL    := s.runL\n"),
    "facts after the end": ("        if na(r.endBar)\n            float lv", "        if true\n            float lv"),
    "drawing before the guard": ("        if cur.cBar >= CISD_GUARD\n", "        if true\n"),
    "alert ON regardless of the guard": (
        "EV_CISD_CONFIRMED => cisdAlert and e.eventBar >= CISD_GUARD", "EV_CISD_CONFIRMED => cisdAlert"),
}


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_mutation_is_caught(name):
    old, new = MUTATIONS[name]
    assert SRC.count(old) == 1, f"mutation anchor not found once: {old!r}"
    ok, detail = st20(SRC.replace(old, new))
    assert not ok, f"{name}: ST-20 still passes ({detail})"


def test_renderer_toggle_is_a_view_input_and_never_reaches_the_engine():
    """ST-01 (calculation never reads [view]/[alert]) also catches mutation 13 on its own."""
    assert st01_calc_independent_of_view()[0]
    import validation.static_checks as sc
    assert "cisdShow" not in sc.CALC_INPUTS and "cisdOn" in sc.CALC_INPUTS


# ── settings, renderer, diagnostics, capture: the approved view (D-C8, D-C9, D-C12) ──
def _input(name):
    return next(ln for ln in SRC.splitlines() if re.match(rf"^{name}\s*=\s*input\.", ln))


def test_settings_minimal_group_and_defaults():
    assert "input.bool(true" in _input("cisdOn") and "input.bool(true" in _input("cisdShow")
    assert "input.bool(false" in _input("cisdPrev") and "input.bool(false" in _input("cisdAlert")
    assert "group = G_DBG" in _input("dbgCisdIns")
    cisd_inputs = [ln for ln in SRC.splitlines() if re.match(r"^\w+\s*=\s*input\.", ln) and "group = G_CISD" in ln]
    assert len(cisd_inputs) == 4                                  # no mathematical CISD parameter (CISD-R has none)


def test_renderer_rules():
    body = "\n".join(code(ln) for ln in SRC.split("f_cisdDraw(Cisd r, bool faded) =>")[1].split("f_cisdRender() =>")[0].splitlines())
    assert body.count("line.new(") == 1 and body.count("label.new(") == 1 and "box.new(" not in body
    assert "xloc = xloc.bar_time" in body and "width = 1" in body and "line.style_solid" in body
    assert 'label.new(r.cTime, r.level, "",' in body and "size = size.tiny" in body       # a small CISD text
    assert "line.new(r.id, r.level, r.cTime, r.level" in body                             # at L, origin → confirmation
    render = SRC.split("f_cisdRender() =>")[1].split("// ════")[0]
    assert "cisdBook.recs.last()" in render and "if cisdPrev and n > 1" in render and render.count("f_cisdDraw(") == 2
    assert "CISD_COL     = color.new(#4F473F, 0)" in SRC


def test_diagnostics_and_capture_lines():
    for row in range(45, 52):
        assert f"f_dbgRow({row}, " in SRC
    assert "table.new(position.bottom_right, 2, 52," in SRC
    for key in ("|cisd=", "|cisdmem=", "|cisdtra=", "|cisdguard=", '"|CS="', '"|CU="', '"|CN="', '"|CA="',
                '"CISDSTATE|state="', '"CISDSIDE|side="', '"CISDREC|side="'):
        assert key in SRC, key
