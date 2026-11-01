"""DISP-L11 · human / golden validation of DISPLACEMENT-R (validation/golden/human/displacement/,
README there). Real NQ / MNQ 1m candles copied exactly from the evidence captures; each case was
classified from its candle shape before the detector ran; the approved verdict is the arithmetic of
DEF-DISP1…5 on the recorded numbers (k 1.5, close position 0.75, A over 14 bars, close beyond the
previous candle: nothing here reads a threshold from the cases).

Checked: the candles are the evidence bars; the recorded numbers follow from them; the oracle and
Pine's formulation give the approved verdict on the case window and on the full history; the real
IST v0.8.0-dev Pine Logs agree where a case lies in that capture; the bearish mirror; the CISD
relation (frozen CISD-R oracle); the coverage the task asks for."""
import json
from functools import lru_cache

import pytest

from validation.candles import mirror
from validation.golden import GOLDEN_DIR, candles_of
from validation.invariants import run_checked
from validation.models.displacement import DispPine
from validation.models.events import EventLog
from validation.models.ist import IstModel
from validation.models.types import NQ_TICK, DispSettings, Settings
from validation.parity import CAPTURE_V043, CAPTURE_V080, EVIDENCE, capture
from validation.studies.lrl import nq_candles

pytestmark = [pytest.mark.disp, pytest.mark.section("golden")]
DIR = GOLDEN_DIR / "human" / "displacement"
CASES = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(DIR.glob("GOLD_DISP_*.json"))}
TOL = 1e-9
EPS = NQ_TICK * 0.01
FVG = {True: "YES", False: "NO", None: None}


@lru_cache(maxsize=None)
def history(files: tuple) -> tuple:
    """The full evidence history a case was cut from (NQ1!: both v0.4.x captures merged)."""
    if CAPTURE_V043.name in files:
        return tuple(nq_candles())
    return tuple(b["candle"] for b in capture.parse((EVIDENCE / files[0]).read_text(encoding="utf-8"))["bars"])


@lru_cache(maxsize=None)
def pine_bars() -> dict:
    """time → the per-bar values IST v0.8.0-dev logged in the real capture (DISP-L10)."""
    return {b["time"]: b for b in capture.parse(CAPTURE_V080.read_text(encoding="utf-8"))["bars"]}


def window(case):
    return candles_of(case)


def offset(case) -> int:
    hist = history(tuple(case["source"]["evidence"]))
    return next(i for i, c in enumerate(hist) if c.time == window(case)[0].time)


def near(a, b):
    return (a is None) == (b is None) and (a is None or abs(a - b) <= TOL * max(1.0, abs(b)))


@pytest.mark.parametrize("cid", sorted(CASES))
def test_candles_are_exact_evidence_bars(cid):
    case = CASES[cid]
    hist, w = history(tuple(case["source"]["evidence"])), window(case)
    i = offset(case)
    assert list(hist[i:i + len(w)]) == w                     # time and OHLC, bar for bar: nothing fabricated


@pytest.mark.parametrize("cid", sorted(CASES))
def test_recorded_numbers_follow_from_the_candles(cid):
    """The approved verdict is DEF-DISP1…5 on these numbers, written out by hand."""
    case, w = CASES[cid], window(CASES[cid])
    for k, e in zip(case["case_bars"], case["expected"]):
        c, p, n = w[k], w[k - 1], w[k + 1]
        tr = lambda j: max(w[j].high - w[j].low, abs(w[j].high - w[j - 1].close), abs(w[j].low - w[j - 1].close))
        a = sum(tr(j) for j in range(k - 14, k)) / 14
        d = 1 if c.close > c.open + EPS else -1 if c.close < c.open - EPS else 0
        rng = c.high - c.low
        cp = ((c.close - c.low) if d > 0 else (c.high - c.close)) / rng if d else None
        beyond = (c.close > p.high + EPS) if d > 0 else (c.close < p.low - EPS) if d < 0 else False
        ok = d != 0 and d * (c.close - c.open) >= 1.5 * a and rng > 0 and cp is not None and \
            (c.close - c.low if d > 0 else c.high - c.close) >= 0.75 * rng and beyond
        assert (e["side"], e["prev_high"], e["prev_low"], e["beyond_prev"]) == (d, p.high, p.low, beyond)
        assert all(near(e[x], y) for x, y in (("A", a), ("body", d * (c.close - c.open)), ("range", rng),
                                              ("body_k", d * (c.close - c.open) / a), ("range_k", rng / a),
                                              ("close_position", cp)))
        assert e["verdict"] == (d if ok else 0) and (e["verdict"] == 0) == bool(e["fails"])
        gap = (n.low > p.high) if d > 0 else (n.high < p.low) if d < 0 else None
        assert e["fvg_next"] == (FVG[gap] if d else None)


def _models(cs):
    oracle = run_checked(cs, Settings(modules=("disp",), disp=DispSettings(memory=10 ** 6))).disp
    pine = DispPine(DispSettings(memory=10 ** 6), NQ_TICK, EventLog())
    for t, c in enumerate(cs):
        pine.log.at(t, c.time)
        pine.step(t, c)
    return oracle, pine


@pytest.mark.parametrize("cid", sorted(CASES))
def test_oracle_and_pine_give_the_approved_verdict(cid):
    case = CASES[cid]
    oracle, pine = _models(window(case))
    for k, e in zip(case["case_bars"], case["expected"]):
        o = next((r for r in oracle.recs if r.bar == k), None)
        p = next((r for r in pine.recs if r.bar == k), None)
        assert (o.side if o else 0) == (p.side if p else 0) == e["verdict"], e["time"]
        if o:
            assert all(near(x, e[y]) for x, y in ((o.tra, "A"), (o.body_k, "body_k"), (o.range_k, "range_k"),
                                                  (o.clv, "close_position")))
            assert (o.prev_ext, FVG[o.fvg], {1: "YES", -1: "NO"}[p.fvg]) == \
                   (e["prev_high"] if o.side > 0 else e["prev_low"], e["fvg_next"], e["fvg_next"])


@pytest.mark.parametrize("cid", sorted(CASES))
def test_full_history_agrees_and_the_cisd_relation_holds(cid):
    """Cut from its whole history, nothing changes: same verdict and FVG metadata; the frozen CISD-R
    oracle on that history gives the recorded CISD relation."""
    case = CASES[cid]
    hist, i = history(tuple(case["source"]["evidence"])), offset(case)
    m = IstModel(Settings(modules=("disp", "cisd"), disp=DispSettings(memory=10 ** 6))).run(list(hist))
    cisd = {e.bar: e.dir for e in m.events if e.type == "CISD_CONFIRMED"}
    for k, e in zip(case["case_bars"], case["expected"]):
        t = i + k
        r = next((r for r in m.disp.recs if r.bar == t), None)
        assert (r.side if r else 0) == e["verdict"] and (FVG[r.fvg] if r else e["fvg_next"]) == e["fvg_next"]
        assert cisd.get(t, 0) == e["cisd_on_bar"]
        assert sorted(b - t for b, s in cisd.items() if abs(b - t) <= 10 and s == e["side"]) == \
               (e["same_side_cisd_within_10"] if e["side"] else [])


IN_V080 = sorted(cid for cid, c in CASES.items() if any(
    candles_of(c)[k].time in pine_bars() and candles_of(c)[k + 1].time in pine_bars() for k in c["case_bars"]))


@pytest.mark.parametrize("cid", IN_V080)
def test_real_pine_capture_agrees(cid):
    """The cases inside the real v0.8.0-dev capture: the candle Pine saw is the case candle, and Pine's
    logged verdict, A, body / A, close position and the next bar's FVG metadata are the approved ones."""
    case, w, bars = CASES[cid], window(CASES[cid]), pine_bars()
    for k, e in zip(case["case_bars"], case["expected"]):
        b, nb = bars[w[k].time], bars[w[k + 1].time]
        assert b["candle"] == w[k] and nb["candle"] == w[k + 1]
        got = b["disp"]
        assert got["side"] == e["verdict"]
        assert abs(got["a"] - e["A"]) <= 1e-6 and abs(got["bk"] - e["body_k"]) <= 1e-6
        assert abs(got["cp"] - e["close_position"]) <= 1e-6
        assert nb["disp"]["fvg"] == ({"YES": 1, "NO": -1}[e["fvg_next"]] if e["verdict"] else None)


@pytest.mark.parametrize("cid", sorted(CASES))
def test_bearish_mirror(cid):
    case = CASES[cid]
    oracle, _ = _models(mirror(window(case), 0.0))
    for k, e in zip(case["case_bars"], case["expected"]):
        o = next((r for r in oracle.recs if r.bar == k), None)
        assert (o.side if o else 0) == -e["verdict"]
        if o:
            assert near(o.body_k, e["body_k"]) and near(o.clv, e["close_position"])


def test_coverage_the_task_asks_for():
    cat = lambda c: c["category"][0]
    clear = [(c["expected"][0]["verdict"]) for c in CASES.values() if cat(c) == "A"]
    assert clear.count(1) >= 3 and clear.count(-1) >= 3
    assert sum(cat(c) == "B" and "large range / weak body rejected" in c["special"] for c in CASES.values()) >= 2
    assert sum(cat(c) == "C" for c in CASES.values()) >= 2
    tags = " | ".join(t for c in CASES.values() for t in c["special"])
    for need in ("displacement + CISD", "displacement without CISD", "CISD without displacement", "FVG = YES",
                 "FVG = NO", "large range / weak body rejected", "body / A ≥ 1.5 but close position < 0.75 rejected",
                 "strong body + strong close, previous candle extreme not exceeded"):
        assert need in tags, need
    assert all(c["category"][0] in "ABCS" for c in CASES.values())


def test_every_clear_case_matches_its_category():
    """A → displacement, B → none: the reviewer's classification and DISPLACEMENT-R agree."""
    for cid, c in CASES.items():
        v = [e["verdict"] for e in c["expected"]]
        if c["category"].startswith("A"):
            assert v == [c["expected"][0]["side"]], cid
        elif c["category"].startswith("B"):
            assert v == [0], cid


def test_thresholds_are_the_approved_ones():
    s = DispSettings()
    assert (s.k, s.clv, s.tra_len, s.memory) == (1.5, 0.75, 14, 50)
