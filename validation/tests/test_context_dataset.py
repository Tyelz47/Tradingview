"""CONTEXT-03 dataset contract (validation/studies/context_dataset.py, docs/context/DATASET_CONTRACT.md): contract
continuity and roll boundaries, duplicate / non-monotonic timestamps, wrong tick, OHLC consistency, scheduled versus
unscheduled gaps, session truncation, the trading day across DST, the time-ordered DEV / OOS split and policy locks,
and the repository's evidence under the contract."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from validation.models.dol_policy import Baseline
from validation.models.types import Candle
from validation.studies import context_dataset as D

pytestmark = [pytest.mark.evaluation, pytest.mark.section("evaluation")]
NY = ZoneInfo("America/New_York")


def ms(y, mo, d, h, mi=0):
    return int(datetime(y, mo, d, h, mi, tzinfo=NY).timestamp() * 1000)


def meta(start, end=None, rolls=(), holidays=(), spans=None):
    spans = spans or (D.ContractSpan("NQZ2026", start, end, False),)
    return D.DatasetMeta("t", "NQ", spans, D.TZ, 0.25, 60, "synthetic", (), holidays, rolls)


def run(t0, n, skip=(), price=100.0):
    return [Candle(t0 + 60_000 * i, price, price + 0.5, price - 0.5, price) for i in range(n) if i not in skip]


def kinds(cs, m):
    return [x.kind for x in D.integrity(cs, m)]


def test_integrity_issues():
    t0 = ms(2026, 10, 27, 9, 30)
    good = run(t0, 10)
    assert kinds(good, meta(t0)) == []
    dup = good[:5] + [good[4]] + good[5:]
    assert "DUPLICATE_TIMESTAMP" in kinds(dup, meta(t0))
    back = good[:5] + [good[2]] + good[5:]
    assert "NON_MONOTONIC" in kinds(back, meta(t0))
    off = good[:3] + [Candle(good[3].time, 100.1, 100.5, 99.5, 100)] + good[4:]
    assert "OFF_TICK" in kinds(off, meta(t0))
    ohlc = good[:3] + [Candle(good[3].time, 100, 99.75, 99.5, 100)] + good[4:]
    assert "OHLC_INCONSISTENT" in kinds(ohlc, meta(t0))
    assert kinds(run(t0, 10, skip={4, 5}), meta(t0)) == ["UNSCHEDULED_GAP"]       # two open minutes missing


def test_contract_continuity_and_roll_boundaries():
    t0 = ms(2026, 12, 10, 9, 30)
    roll = t0 + 5 * 60_000
    spans = (D.ContractSpan("NQZ2026", t0, roll, False), D.ContractSpan("NQH2027", roll, None, False))
    m = meta(t0, spans=spans)
    assert D.boundaries(m) == [roll] and D.boundary_after(m, t0) == roll and D.boundary_after(m, roll) is None
    assert D.contract_at(m, roll - 60_000).symbol == "NQZ2026" and D.contract_at(m, roll).symbol == "NQH2027"
    assert kinds(run(t0 - 60_000, 3), m) == ["NO_CONTRACT"]                          # a bar no contract span covers
    cont = meta(t0, spans=(D.ContractSpan("NQ1!", t0, None, True, "default"),), rolls=(roll,))
    assert D.boundaries(cont) == [roll]                                               # a declared roll inside a continuous symbol


def test_the_cme_schedule_closures_are_not_gaps():
    friday = run(ms(2026, 10, 30, 16, 55), 5)                                         # 16:55 … 16:59
    sunday = run(ms(2026, 11, 1, 18, 0), 5)                                           # the weekend, across the DST change
    assert kinds(friday + sunday, meta(friday[0].time)) == []
    halt = run(ms(2026, 10, 27, 16, 55), 5) + run(ms(2026, 10, 27, 18, 0), 5)         # the daily 17:00–18:00 halt
    assert kinds(halt, meta(halt[0].time)) == []
    holiday = run(ms(2026, 11, 25, 16, 55), 5) + run(ms(2026, 11, 26, 18, 0), 5)      # a missing day: a gap unless declared
    assert kinds(holiday, meta(holiday[0].time)) == ["UNSCHEDULED_GAP"]
    assert kinds(holiday, meta(holiday[0].time, holidays=(date(2026, 11, 26),))) == []


def test_trading_days_and_truncation_across_dst():
    assert D.day_bounds(date(2026, 11, 2)) == (ms(2026, 11, 1, 18, 0), ms(2026, 11, 2, 16, 59))   # Monday, after DST
    assert D.day_bounds(date(2026, 10, 30)) == (ms(2026, 10, 29, 18, 0), ms(2026, 10, 30, 16, 59))
    assert D.day_bounds(date(2026, 3, 9)) == (ms(2026, 3, 8, 18, 0), ms(2026, 3, 9, 16, 59))     # the spring change
    assert D.trading_date(ms(2026, 11, 1, 18, 0)) == date(2026, 11, 2) and D.trading_date(ms(2026, 11, 2, 16, 59)) == date(2026, 11, 2)
    full = [c for c in run(ms(2026, 10, 26, 18, 0), 23 * 60) if not D.closed(c.time)]
    days = D.trading_days(full, meta(full[0].time))
    assert [(d.date, d.complete, d.truncated_start, d.truncated_end) for d in days] == [(date(2026, 10, 27), True, False, False)]
    part = D.trading_days(full[30:-10], meta(full[30].time))
    assert [(d.complete, d.truncated_start, d.truncated_end) for d in part] == [(False, True, True)]


def test_dev_oos_split_is_time_ordered_and_oos_needs_a_lock():
    days = [date(2026, 10, d) for d in (13, 14, 27, 28, 30)]
    assert D.split(days, date(2026, 10, 27)) == {date(2026, 10, 13): "DEV", date(2026, 10, 14): "DEV",
                                                 date(2026, 10, 27): "DEV", date(2026, 10, 28): "OOS", date(2026, 10, 30): "OOS"}
    lock = D.PolicyLock.of([Baseline("B0", "STRICT")])
    lock.check(Baseline("B0", "STRICT"))
    with pytest.raises(PermissionError):
        lock.check(Baseline("B1", "STRICT"))                                          # never locked
    with pytest.raises(PermissionError):
        D.PolicyLock((("B0@STRICT", "0" * 64),)).check(Baseline("B0", "STRICT"))      # changed after its lock
    assert D.fingerprint(Baseline("B0", "STRICT")) != D.fingerprint(Baseline("B0", "PROVISIONAL"))


def test_the_evidence_under_the_contract():
    data = D.evidence_datasets()
    assert [(m.underlying, m.timezone, m.tick) for m, _ in data] == [("NQ", "America/New_York", 0.25)] * 4
    for m, seg in data:
        assert D.integrity(seg.cs, m) == []                                           # its only gaps are scheduled closures
        assert not any(d.complete for d in D.trading_days(seg.cs, m))                 # no complete trading day anywhere
        assert all(len(h) == 64 for _, h in m.files)                                  # provenance: the evidence SHA-256
