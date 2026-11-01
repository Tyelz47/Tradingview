"""Displacement research study (validation/studies/displacement.py, docs/STUDY_DISPLACEMENT.md): the
harness is trustworthy. Bullish = mirrored bearish, prices can be shifted, no decision uses a
later bar, the multi-bar and FVG candidates fire where the study says, the thresholds are the
Tukey fences of the real data, and the numbers quoted in the study reproduce. No indicator,
oracle or frozen-engine change is tested here."""
import pytest

from validation.candles import from_rows, mirror, random_walk, shift
from validation.studies import displacement as dsp

pytestmark = [pytest.mark.disp, pytest.mark.section("research.disp")]
FLAT = (100, 101, 99, 100)


def ev(cs, spec):
    return [(d.bar, d.side, d.origin, round(d.body_k, 9), d.fvg) for d in dsp.run(cs, spec)]


@pytest.fixture(scope="module")
def segs():
    return dsp.segments()


@pytest.mark.parametrize("spec", dsp.CANDIDATES, ids=lambda s: s.name.split()[0])
def test_candidates_are_mirror_and_translation_symmetric(spec):
    cs = random_walk(1500, 3, gap_prob=0.02)
    base = ev(cs, spec)
    assert [(b, -s, o, k, f) for b, s, o, k, f in ev(mirror(cs, 0.0), spec)] == base
    assert ev(shift(cs, 125.0), spec) == base


@pytest.mark.parametrize("spec", dsp.CANDIDATES, ids=lambda s: s.name.split()[0])
def test_candidates_never_look_ahead(spec):
    cs = random_walk(800, 11, gap_prob=0.02)
    full = dsp.run(cs, spec)
    for n in (100, 333, 640):
        part = [(d.bar, d.side, d.origin) for d in dsp.run(cs[:n], spec)]
        assert part == [(d.bar, d.side, d.origin) for d in full if d.bar < n]


def test_fvg_candidate_decides_on_candle_three():
    cs = from_rows([FLAT] * 15 + [(100, 103, 100, 103), (103, 104, 101.25, 104)])
    assert ev(cs, dsp.D5) == [(16, 1, 15, 1.5, True)]
    assert ev(cs, dsp.D1) == [(15, 1, 15, 1.5, True)]


def test_run_candidate_fires_once_per_run_from_its_first_candle():
    rows = [FLAT] * 15 + [(100, 102, 100, 102), (102, 104, 102, 104), (104, 106, 104, 106), (106, 108, 106, 108)]
    got = dsp.run(from_rows(rows), dsp.Spec("run", k=2.7, run=True))
    assert [(d.bar, d.origin) for d in got] == [(17, 15)]    # 6 points ≥ 2.7 × 2 on the third candle, once
    assert dsp.run(from_rows(rows), dsp.RECOMMENDED) == []   # no single candle qualifies


def test_thresholds_are_the_tukey_fences_of_the_real_data(segs):
    p = dsp.populations(segs)
    assert {k: round(dsp.fence(p[k]), 1) for k in dsp.FENCE_OF} == dsp.FENCE_OF


def test_recommended_numbers_quoted_by_the_study(segs):
    m = dsp.measure(segs, dsp.RECOMMENDED)
    assert (m["n"], m["bull"], m["cisd_n"]) == (110, 49, 300)
    assert (round(m["per_hour"], 2), round(m["fvg"], 2), round(m["on_cisd"], 2), round(m["cisd_with"], 2)) == \
        (1.74, 0.85, 0.31, 0.11)


def test_absolute_size_detector_concentrates_in_ny_am_and_the_relative_one_does_not(segs):
    rel = dsp.measure(segs, dsp.RECOMMENDED)["sessions"]
    big = dsp.measure(segs, dsp.Spec("abs", absolute=20))["sessions"]
    assert rel["NY AM"][1] / rel["Asia"][1] < 1.5 < 10 < big["NY AM"][1] / big["Asia"][1]


def test_shuffle_keeps_the_candle_shapes(segs):
    cs = segs[1][1]
    sh = dsp.shuffled(cs, 1)
    shape = lambda c: (round(c.high - c.open, 6), round(c.low - c.open, 6), round(c.close - c.open, 6))
    assert sorted(map(shape, sh)) == sorted(map(shape, cs)) and len(sh) == len(cs)
