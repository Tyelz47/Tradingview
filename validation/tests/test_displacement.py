"""Displacement oracle (validation/models/displacement.py, docs/DISPLACEMENT.md DEF-DISP1…DISP9,
DISPLACEMENT-R recommended 2026-11-01, awaiting approval). Every run here is invariant-checked.

The warm-up candle (100, 101, 99, 100) has a true range of 2, so after it the TR average A is 2
and the body threshold 1.5 × A = 3 points: thresholds below are exact on the 0.25 tick grid."""
from dataclasses import replace

import pytest

from validation.candles import MINUTE, from_rows, mirror, shift
from validation.invariants import run_checked
from validation.models.ist import IstModel
from validation.models.types import KNOWN_MODULES, MODULES, DispSettings, Settings
from validation.studies import displacement as study

pytestmark = [pytest.mark.disp, pytest.mark.section("disp")]

FLAT = (100, 101, 99, 100)
W = 15                                    # warm-up candles: the tested candle is bar 15
C, D = "DISPLACEMENT_CONFIRMED", "DISPLACEMENT_DROPPED_MEMORY"


def model(cs, ds=DispSettings(), modules=("disp",)):
    return run_checked(cs, Settings(modules=modules, disp=ds))


def recs(rows, ds=DispSettings()):
    return [(r.bar, r.side) for r in model(from_rows(rows), ds).disp.recs]


def one(*candles):
    return [FLAT] * W + list(candles)


# ── thresholds: body, close location, beyond the previous candle ──

def test_exact_body_threshold_is_a_displacement():
    m = model(from_rows(one((100, 103, 100, 103))))
    r, = m.disp.recs
    assert (r.bar, r.side, r.tra, r.body_k, r.range_k, r.clv, r.prev_ext) == (W, 1, 2.0, 1.5, 1.5, 1.0, 101)


def test_one_tick_below_and_above_the_body_threshold():
    assert recs(one((100, 102.75, 100, 102.75))) == []
    assert recs(one((100, 103.25, 100, 103.25))) == [(W, 1)]


def test_bearish_is_the_exact_mirror():
    assert recs(one((100, 100, 97, 97))) == [(W, -1)]
    assert recs(one((100, 100, 97.25, 97.25))) == []
    for row in ((100, 103, 100, 103), (100, 104, 100, 103), (100, 104.25, 100, 103), (100, 106, 100, 103.5)):
        cs = from_rows(one(row, (103, 104, 101.25, 104)))
        up = [(r.bar, r.side, r.body_k, r.clv, r.fvg) for r in model(cs).disp.recs]
        down = [(r.bar, -r.side, r.body_k, r.clv, r.fvg) for r in model(mirror(cs, 0.0)).disp.recs]
        assert up == down


def test_doji_and_equal_open_close_are_never_displacement():
    assert recs(one((100, 105, 95, 100))) == []
    assert recs(one((100, 100, 100, 100))) == []


def test_weak_close_is_rejected_and_the_strong_close_threshold_is_exact():
    assert recs(one((100, 106, 100, 103.5))) == []          # body 3.5 ≥ 3, close at 58 % of the range
    assert recs(one((100, 104, 100, 103))) == [(W, 1)]       # close at exactly 75 %
    assert recs(one((100, 104.25, 100, 103))) == []          # one tick more upper wick: 70.6 %


def test_large_wick_small_body_is_not_displacement():
    assert recs(one((100, 110, 95, 101))) == []


def test_large_body_with_a_modest_range_is_displacement():
    r, = model(from_rows(one((100, 103.5, 100, 103.5)))).disp.recs
    assert (r.body_k, r.range_k) == (1.75, 1.75)             # the range is not a requirement


def test_close_must_be_strictly_beyond_the_previous_candle():
    prev = (100, 108, 99, 100)                               # TR 9: A = (13 × 2 + 9) / 14 = 2.5, threshold 3.75
    assert recs(one(prev, (104, 108, 104, 108))) == []       # body 4, close AT the previous high
    m = model(from_rows(one(prev, (104, 108.25, 104, 108.25))))
    r, = m.disp.recs
    assert (r.bar, r.tra, r.prev_ext) == (W + 1, 2.5, 108)


# ── edge cases: consecutive, multi-bar, gaps, session boundary, warm-up, zero scale ──

def test_consecutive_displacement_candles_are_separate_records():
    m = model(from_rows(one((100, 103, 100, 103), (103, 106.5, 103, 106.5))))
    assert [(r.bar, r.side, r.fvg) for r in m.disp.recs] == [(W, 1, True), (W + 1, 1, None)]
    assert [e.type for e in m.events] == [C, C]


def test_a_staircase_of_medium_candles_is_not_a_displacement():
    """Known false negative of the one-candle rule (study §J): 3 × 2 points = 3 × A, no candle ≥ 1.5 × A."""
    assert recs(one((100, 102, 100, 102), (102, 104, 102, 104), (104, 106, 104, 106))) == []


def test_gap_open_counts_only_the_candle_body_and_inflates_the_next_yardstick():
    cs = from_rows(one((110, 113, 110, 113), (113, 116, 113, 116), (116, 116.75, 115.75, 116.5)))
    cs[W:] = [replace(c, time=c.time + 60 * MINUTE) for c in cs[W:]]        # CME break: 61 minutes without bars
    m = model(cs)
    r, = m.disp.recs
    assert (r.bar, r.tra, r.body_k) == (W, 2.0, 1.5)        # 10-point gap not counted; no session reset
    assert m.disp.tr[W] == 13                                # the gap enters the true range, so the next candle's
    assert sum(m.disp.tr[W - 13:W + 1]) / 14 > 2.75           # 3-point body is below 1.5 × A


def test_no_decision_while_the_tr_average_warms_up():
    assert recs([FLAT] * 13 + [(100, 103, 100, 103)]) == []  # bar 13: only 13 true ranges before it
    assert recs([FLAT] * 14 + [(100, 103, 100, 103)]) == [(14, 1)]


def test_zero_tr_average_has_no_scale():
    assert recs([(100, 100, 100, 100)] * W + [(100, 100.25, 100, 100.25)]) == []


def test_tr_average_length_is_the_setting():
    assert recs([FLAT] * 3 + [(100, 103, 100, 103)], DispSettings(tra_len=2)) == [(3, 1)]


# ── record facts, memory, events ──

def test_fvg_fact_is_stamped_on_the_next_bar_only():
    yes = model(from_rows(one((100, 103, 100, 103), (103, 104, 101.25, 104)))).disp.recs[0]
    no = model(from_rows(one((100, 103, 100, 103), (103, 104, 100.75, 103.5)))).disp.recs[0]
    last = model(from_rows(one((100, 103, 100, 103)))).disp.recs[0]
    assert (yes.fvg, no.fvg, last.fvg) == (True, False, None)


def test_events_carry_side_id_close_and_bar():
    m = model(from_rows(one((100, 103, 100, 103))))
    e, = m.events
    assert (e.type, e.dir, e.sid, e.price, e.origin_bar, e.bar) == (C, 1, m.candles[W].time, 103.0, W, W)
    assert e.meta.startswith("body 1.50×TR")


def test_memory_drops_the_oldest_record_with_an_event():
    rows = one((100, 103, 100, 103), FLAT, (100, 103.5, 100, 103.5), FLAT, (100, 104, 100, 104))
    m = model(from_rows(rows), DispSettings(memory=2))
    assert [r.bar for r in m.disp.recs] == [W + 2, W + 4]
    assert [(e.type, e.sid) for e in m.events if e.type == D] == [(D, m.candles[W].time)]
    assert (m.disp.confirmed, m.disp.dropped) == (3, 1)


# ── the real data, independence, determinism ──

@pytest.fixture(scope="module")
def segs():
    return study.segments()


def test_oracle_equals_the_study_definition_on_real_data(segs):
    n = 0
    for _, cs in segs:
        mine = [(r.bar, r.side, round(r.body_k, 9), round(r.clv, 9), r.fvg)
                for r in IstModel(Settings(modules=("disp",), disp=DispSettings(memory=10 ** 6))).run(cs).disp.recs]
        assert mine == [(d.bar, d.side, round(d.body_k, 9), round(d.clv, 9), d.fvg) for d in study.run(cs, study.RECOMMENDED)]
        n += len(mine)
    assert n == 110


def test_real_data_counts(segs):
    got = [model(cs).disp for _, cs in segs]
    assert [e.confirmed for e in got] == [57, 23, 30]
    assert sum(r.side > 0 for _, cs in segs for r in IstModel(Settings(modules=("disp",), disp=DispSettings(memory=999)))
               .run(cs).disp.recs) == 49


def test_detection_ignores_every_other_module(segs):
    """Module toggles: the records are the same alone or with every other module on."""
    for _, cs in segs:
        alone = model(cs).disp.state()
        assert IstModel(Settings(modules=KNOWN_MODULES)).run(cs).disp.state() == alone


def test_other_modules_are_unchanged_by_displacement(segs):
    cs = segs[0][1]
    base = MODULES + ("lrl", "cisd")
    on = IstModel(Settings(modules=base + ("disp",))).run(cs)
    off = IstModel(Settings(modules=base)).run(cs)
    assert [e for e in on.events if not e.type.startswith("DISPLACEMENT_")] == off.events
    assert on.cisd.state() == off.cisd.state()


def test_default_run_has_no_displacement(segs):
    m = IstModel().run(segs[1][1])
    assert m.disp is None and not any(e.type.startswith("DISPLACEMENT_") for e in m.events)


def test_identical_history_gives_identical_results(segs):
    cs = segs[2][1]
    a, b = IstModel(Settings(modules=("disp",))).run(cs), IstModel(Settings(modules=("disp",))).run(list(cs))
    assert a.disp.state() == b.disp.state() and a.events == b.events


def test_prefix_equals_the_past_of_the_full_run(segs):
    cs = segs[1][1]
    full = IstModel(Settings(modules=("disp",))).run(cs)
    for n in (200, 517, 900):
        part = IstModel(Settings(modules=("disp",))).run(cs[:n])
        assert part.events == [e for e in full.events if e.bar < n]
        old = [(r.id, r.fvg if r.bar < n - 1 else None) for r in full.disp.recs if r.bar < n]
        assert [(r.id, r.fvg) for r in part.disp.recs] == old[-50:]


def test_translation_does_not_change_records(segs):
    cs = segs[2][1]
    a = [(r.bar, r.side, round(r.body_k, 9), r.fvg) for r in model(cs).disp.recs]
    assert [(r.bar, r.side, round(r.body_k, 9), r.fvg) for r in model(shift(cs, 250.0)).disp.recs] == a


def test_settings_round_trip():
    s = Settings(modules=("disp",), disp=DispSettings(k=2.0, clv=0.5, tra_len=10, memory=7))
    assert Settings.from_dict(s.to_dict()) == s
    assert "disp" not in Settings().to_dict()
