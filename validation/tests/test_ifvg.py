"""IFVG oracle (validation/models/ifvg.py, docs/IFVG.md DEF-IFVG1…IFVG9, IFVG-R recommended
2026-11-02, awaiting approval). Every run here is invariant-checked, Phase 1 FVG included.

The warm-up candle (100, 101, 99, 100) and then (100, 104, 100, 104), (104, 106, 103, 105) make
one Phase 1 bullish FVG on bar 17: bottom 101 (candle 1 high), top 103 (candle 3 low), CE 102."""
from dataclasses import replace

import pytest

from validation.candles import from_rows, mirror, shift
from validation.invariants import run_checked
from validation.models.ist import IstModel
from validation.models.types import KNOWN_MODULES, MODULES, FvgSettings, IfvgSettings, Settings, ViewSettings
from validation.studies import displacement as dsp
from validation.studies import ifvg as study

pytestmark = [pytest.mark.ifvg, pytest.mark.section("ifvg")]

FLAT = (100, 101, 99, 100)
BASE = [FLAT] * 16 + [(100, 104, 100, 104), (104, 106, 103, 105)]
C3 = 17                                     # the parent's confirmation bar
INV, TOUCH, INVAL = "IFVG_INVERTED", "IFVG_FIRST_TOUCH", "IFVG_INVALIDATED"


def model(rows, **kw):
    return run_checked(from_rows(rows), Settings(modules=("fvg", "ifvg"), **kw))


def parent_ifvg(m):
    """The IFVG of the bar-17 parent, or None."""
    return next((r for r in m.ifvg.records() if r.parent_bar == C3), None)


# ── the trigger: the frozen Phase 1 invalidation (DEF-A5) ──

def test_bullish_fvg_becomes_a_bearish_ifvg_on_a_close_one_tick_below_the_bottom():
    m = model(BASE + [(102, 102.5, 100, 100.75)])
    r = parent_ifvg(m)
    assert (r.side, r.bar, r.close, r.pre) == (-1, C3 + 1, 100.75, "UNTOUCHED")
    z = next(z for z in m.fvg.records() if z.confirm_bar == C3)
    assert z.inv_bar == r.bar and (r.id, r.top, r.bottom, r.mid, r.origin_bar) == (z.id, z.top, z.bottom, z.mid, z.origin_bar)


def test_bearish_fvg_becomes_a_bullish_ifvg():
    m = run_checked(mirror(from_rows(BASE + [(102, 102.5, 100, 100.75)]), 0.0), Settings(modules=("fvg", "ifvg")))
    r = parent_ifvg(m)
    assert (r.side, r.bar, r.top, r.bottom, r.close) == (1, C3 + 1, -101.0, -103.0, -100.75)


def test_close_exactly_at_the_edge_does_not_invert():
    assert parent_ifvg(model(BASE + [(102, 102.5, 100, 101)])) is None


def test_wick_beyond_with_a_close_inside_does_not_invert():
    assert parent_ifvg(model(BASE + [(102, 102.5, 100, 101.5)])) is None


def test_immediate_inversion_on_the_first_bar_after_confirmation():
    assert parent_ifvg(model(BASE + [(102, 102.5, 100, 100.75)])).bar == C3 + 1


@pytest.mark.parametrize("first, pre", [((104, 104, 102.5, 103.5), "TOUCHED"), ((104, 104, 102, 102.5), "CE"),
                                        ((104, 104, 101, 102), "FULL")])
def test_inversion_after_touch_ce_or_full_fill(first, pre):
    r = parent_ifvg(model(BASE + [first, (102, 102, 100, 100.75)]))
    assert (r.bar, r.pre) == (C3 + 2, pre)


def test_gap_through_the_edge_inverts_with_every_parent_milestone_on_that_bar():
    m = model(BASE + [(99, 99.5, 98.5, 99)])
    r = parent_ifvg(m)
    assert (r.bar, r.pre, r.close) == (C3 + 1, "UNTOUCHED", 99.0)
    order = [e.type for e in m.events if e.bar == C3 + 1 and e.sid == r.id]
    assert order == ["FVG_FIRST_TOUCH", "FVG_CE_TOUCH", "FVG_FULL_FILL", "FVG_INVALIDATED", INV]   # DEF-A7, then the IFVG


def test_the_inversion_bar_stamps_no_ifvg_fact():
    r = parent_ifvg(model(BASE + [(102, 102.5, 100, 100.75)]))
    assert (r.retest, r.ce, r.full, r.end) == (None, None, None, None)


def test_the_parent_stays_invalidated_in_phase_1_unchanged():
    rows = BASE + [(102, 102.5, 100, 100.75), (100.75, 101.5, 100.5, 101)]
    on = IstModel(Settings(modules=("fvg", "ifvg"))).run(from_rows(rows))
    off = IstModel(Settings(modules=("fvg",))).run(from_rows(rows))
    assert on.fvg.state() == off.fvg.state()
    assert [e for e in on.events if not e.type.startswith("IFVG_")] == off.events


# ── lifecycle: retest, CE, full traversal, the end ──

LIFE = BASE + [(102, 102.5, 100, 100.75),            # 18 inversion: bearish IFVG [101, 103]
               (100.75, 101, 100, 100.5),            # 19 retest: high reaches the near edge 101
               (100.5, 102, 100.5, 101.5),           # 20 CE reached (high 102)
               (101.5, 103, 101.5, 102.5),           # 21 far edge reached (high 103), close inside
               (102.5, 103.25, 102.5, 103),          # 22 close exactly at the far edge: not the end
               (103, 103.5, 103, 103.25)]            # 23 close one tick above the far edge: INVALIDATED


def test_lifecycle_facts_and_the_end():
    m = model(LIFE)
    r = parent_ifvg(m)
    assert (r.retest, r.ce, r.full, r.end, r.status) == (19, 20, 21, 23, "INVALIDATED")
    ev = [(e.bar, e.type, e.price) for e in m.events if e.type.startswith("IFVG_") and e.sid == r.id]
    assert ev == [(18, INV, 100.75), (19, TOUCH, 101.0), (23, INVAL, 103.25)]


def test_an_ended_ifvg_never_inverts_again_and_never_changes():
    m = model(LIFE + [(103.25, 104, 99, 99.5), (99.5, 104, 99, 100)])
    r = parent_ifvg(m)
    assert (r.end, r.side) == (23, -1) and sum(e.sid == r.id and e.type == INV for e in m.events) == 1


def test_mirrored_lifecycle():
    m = run_checked(mirror(from_rows(LIFE), 0.0), Settings(modules=("fvg", "ifvg")))
    r = parent_ifvg(m)
    assert (r.side, r.retest, r.ce, r.full, r.end) == (1, 19, 20, 21, 23)


# ── eligibility: the frozen Phase 1 universe only ──

def test_a_gap_below_the_phase_1_size_never_becomes_an_ifvg():
    rows = [FLAT] * 16 + [(100, 104, 100, 101.25), (101.25, 102, 101.25, 101.5), (101.5, 101.5, 100, 100.5)]
    m = model(rows)                                  # raw gap 101 → 101.25 = 1 tick < the 2-tick minimum
    assert not m.fvg.records() and not m.ifvg.records()


def test_a_parent_the_fvg_memory_dropped_while_open_never_inverts():
    rows = BASE + [(105, 108, 105, 108), (108, 110, 107.5, 109)] + [(109, 109, 99, 99.5)]
    m = model(rows, fvg=FvgSettings(memory=1))       # bar 19 creates a second bullish FVG: the first (open) is dropped
    assert any(e.type == "FVG_DROPPED_MEMORY" and e.bar == 19 for e in m.events)
    assert parent_ifvg(m) is None and [r.parent_bar for r in m.ifvg.records()] == [19]


def test_a_parent_released_by_the_fvg_memory_on_its_inversion_bar_still_inverts():
    """The observer copies each parent on its confirmation bar, so a parent the FVG engine releases on
    the bar it is invalidated (memory 1: a new bullish FVG on that bar, the oldest closed one goes)
    still inverts, with its geometry."""
    rows = [FLAT] * 16 + [(100, 100, 98, 98.5), (103, 104, 103, 103.5), (102, 102, 100.5, 100.75)]
    m = model(rows, fvg=FvgSettings(memory=1))
    assert any(e.type == "FVG_DROPPED_MEMORY" and e.bar == 18 and e.dir == 1 for e in m.events)
    r = parent_ifvg(m)
    assert (r.side, r.bar, r.bottom, r.top) == (-1, 18, 101.0, 103.0)
    assert all(z.confirm_bar != C3 for z in m.fvg.records())          # gone from Phase 1 memory, kept here


def test_needs_the_phase_1_fvg_engine():
    with pytest.raises(ValueError):
        IstModel(Settings(modules=("ifvg",)))


# ── memory, identity, determinism, independence ──

def test_memory_drops_the_oldest_record_of_its_side_with_an_event():
    """A second bearish IFVG (bar 26, from a bullish FVG of bar 25) with memory 1: the first (ended)
    bearish IFVG goes; the bullish one (bar 23) is untouched."""
    rows = LIFE + [(103.25, 106, 103.25, 106), (106, 108, 105.5, 107.5), (107, 107, 102, 102.5)]
    m = model(rows, ifvg=IfvgSettings(memory=1))
    first = next(e.sid for e in m.events if e.type == INV)
    assert [(e.bar, e.dir, e.sid) for e in m.events if e.type == "IFVG_DROPPED_MEMORY"] == [(26, -1, first)]
    assert [(r.side, r.bar) for r in m.ifvg.records()] == [(1, 23), (-1, 26)]


@pytest.fixture(scope="module")
def segs():
    return dsp.segments()


def test_oracle_equals_the_study_on_real_data(segs):
    total = 0
    for i, (_, cs) in enumerate(segs):
        m = IstModel(Settings(modules=("fvg", "ifvg"), fvg=FvgSettings(memory=10 ** 6),
                              ifvg=IfvgSettings(memory=10 ** 6))).run(cs)
        ps = [p for p in study.parents(cs, i) if p.inv is not None]
        assert sorted((r.id, r.side, r.bar) for r in m.ifvg.records()) == sorted((p.id, -p.d, p.inv) for p in ps)
        lives = {p.id: study.life(p, cs, p.inv) for p in ps}
        rel = lambda b, r: None if b is None else b - r.bar
        assert all((rel(r.retest, r), rel(r.ce, r), rel(r.full, r), rel(r.end, r)) ==
                   (lives[r.id].retest, lives[r.id].ce, lives[r.id].full, lives[r.id].broken) for r in m.ifvg.records())
        total += len(ps)
    assert total == 566


def test_real_data_counts_with_the_default_memory(segs):
    got = [IstModel(Settings(modules=MODULES + ("ifvg",))).run(cs).ifvg for _, cs in segs]
    assert [(e.inverted, e.dropped) for e in got] == [(266, 166), (140, 40), (160, 60)]


def test_identity_survives_prefix_shift_and_every_other_module(segs):
    cs = segs[1][1]
    full = IstModel(Settings(modules=("fvg", "ifvg"))).run(cs)
    key = lambda m, f=lambda x: x: [(r.side, r.id, f(r.top), f(r.bottom), r.bar, r.end) for r in m.ifvg.records()]
    allm = IstModel(Settings(modules=KNOWN_MODULES)).run(cs)
    assert key(allm) == key(full)
    moved = IstModel(Settings(modules=("fvg", "ifvg"))).run(shift(cs, 250.0))
    assert key(moved, lambda p: round(p - 250.0, 6)) == key(full, lambda p: round(p, 6))
    for n in (300, 700):
        part = IstModel(Settings(modules=("fvg", "ifvg"))).run(cs[:n])
        assert part.events == [e for e in full.events if e.bar < n]


def test_identical_history_gives_identical_results(segs):
    cs = segs[2][1]
    a, b = (IstModel(Settings(modules=("fvg", "ifvg"))).run(list(cs)) for _ in range(2))
    assert a.ifvg.state() == b.ifvg.state() and a.events == b.events


def test_view_settings_never_change_the_ifvg(segs):
    """Visibility independence: the FVG display rule, caps and toggles are [view]."""
    cs = segs[0][1]
    base = IstModel(Settings(modules=("fvg", "ifvg"))).run(cs).ifvg.state()
    for v in (ViewSettings(fvg_show=False), ViewSettings(mit_rule="firstTouch", fvg_max_visible=1, minimal=True)):
        assert IstModel(Settings(modules=("fvg", "ifvg"), view=v)).run(cs).ifvg.state() == base


def test_other_modules_are_unchanged_by_the_ifvg(segs):
    cs = segs[0][1]
    base = MODULES + ("lrl", "cisd", "disp")
    on = IstModel(Settings(modules=base + ("ifvg",))).run(cs)
    off = IstModel(Settings(modules=base)).run(cs)
    assert [e for e in on.events if not e.type.startswith("IFVG_")] == off.events


def test_settings_round_trip():
    s = Settings(modules=("fvg", "ifvg"), ifvg=IfvgSettings(memory=7))
    assert Settings.from_dict(s.to_dict()) == s and "ifvg" not in Settings().to_dict()
