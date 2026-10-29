"""HTF FVG reference model (validation/models/htf_fvg.py, docs/HTF_FVG.md DEF-B, approved
2026-10-29): timing (no zone before its candle-3 HTF bar closed), the Phase 1 definition on
HTF candles, the lifecycle from the known bar (D2), own-timeframe invalidation (D5), the
box origin vs confirmation (D8), seeds (D3), memory, identity, session alignment, and the
other modules untouched."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from validation.candles import BASE_TIME, mirror, random_walk
from validation.invariants import run_checked
from validation.models.events import Event
from validation.models.htf_fvg import NAMES, bucket
from validation.models.ist import IstModel
from validation.models.types import MODULES, Candle, FvgSettings, HtfSettings, Settings
from validation.studies.lrl import nq_candles

pytestmark = [pytest.mark.htf, pytest.mark.section("htf")]
MIN = 60_000
S15 = Settings(modules=("htf",), fvg=FvgSettings(k_tra=0), htf=HtfSettings(tfs=("15",)))
A = (100, 102, 99, 101)            # candle 1: high 102
B = (101, 110, 101, 109)           # candle 2
C = (109, 112, 104, 111)           # candle 3: low 104 > 102 → bullish zone [102, 104], CE 103
QUIET = (111, 113, 108, 112)       # does not reach the zone


def m1(specs, minutes=15, start=BASE_TIME):
    """1m candles whose `minutes` aggregation is exactly `specs`. An (o, h, l, c) spec puts the
    whole range in the HTF bar's first minute, then flat minutes at its close; a list spec is
    the bar's 1m candles themselves (padded flat to `minutes`)."""
    out, t = [], start
    for spec in specs:
        rows = list(spec) if isinstance(spec, list) else [spec]
        rows += [(rows[-1][3],) * 4] * (minutes - len(rows))
        for o, h, l, c in rows:
            out.append(Candle(t, float(o), float(h), float(l), float(c)))
            t += MIN
    return out


def ev(cs, s=S15, **kw):
    m = IstModel(s, **kw).run(cs)
    return [(e.bar, e.type[8:], e.dir, e.sid, e.price, e.tf) for e in m.events], m


T_A, T_C = BASE_TIME, BASE_TIME + 30 * MIN


def test_known_on_the_first_chart_bar_after_candle_3_closes():
    """Candle 3 (C) is the 15m bar 30…44; it closes when bar 45 opens: the zone is known on
    bar 45, never during C. id = C's open time; the box origin is candle 1's open (D8)."""
    got, m = ev(m1([A, B, C, QUIET, QUIET]))
    assert got == [(45, "CREATED", 1, T_C, 103.0, "15")]
    r = m.hfvg.sides[0].recs[0]
    assert (r.c1_time, r.id, r.top, r.bottom, r.known_bar, r.known_time) == (T_A, T_C, 104.0, 102.0, 45, T_C + 15 * MIN)


def test_lifecycle_starts_on_the_known_bar():
    """D2: the bar where the zone becomes known can already touch it (it was confirmed before
    that bar opened); nothing is ever stamped before it."""
    got, _ = ev(m1([A, B, C, (111, 112, 103.5, 111), QUIET]))
    assert got == [(45, "CREATED", 1, T_C, 103.0, "15"), (45, "FIRST_TOUCH", 1, T_C, 104.0, "15")]


def test_invalidation_needs_an_own_timeframe_close():
    """D5: a 1m close below the bottom inside a 15m bar that closes back above does not
    invalidate; the next 15m bar closing below does, on the first chart bar after it."""
    d = [(111, 111, 101, 101.5), (101.5, 105, 101.5, 104.5)]          # 1m close 101.5 < 102, 15m close 104.5
    e = (104.5, 105, 100, 101)                                           # 15m close 101 < 102
    got, _ = ev(m1([A, B, C, d, e, QUIET]))
    assert got == [(45, "CREATED", 1, T_C, 103.0, "15"), (45, "FIRST_TOUCH", 1, T_C, 104.0, "15"),
                   (45, "CE_TOUCH", 1, T_C, 103.0, "15"), (45, "FULL_FILL", 1, T_C, 102.0, "15"),
                   (75, "INVALIDATED", 1, T_C, 101.0, "15")]


def test_bearish_is_the_mirror():
    got, _ = ev(mirror(m1([A, B, C, (111, 112, 103.5, 111), QUIET]), 0.0))
    assert got == [(45, "CREATED", -1, T_C, -103.0, "15"), (45, "FIRST_TOUCH", -1, T_C, -104.0, "15")]


def test_the_unfinished_htf_bar_is_never_used():
    """Cut the data inside candle 3: no zone, whatever the partial bar shows."""
    for n in range(31, 45):
        assert ev(m1([A, B, C])[:n])[0] == []


def test_seeds_recover_zones_open_before_the_chart_history():
    """D3: the HTF context saw A…D before the first loaded bar. The zone, still open, is SEEDED
    on the first chart bar (no CREATED); a zone partly touched before keeps that as state
    (pre_touch) and gets no retroactive FIRST_TOUCH."""
    pre = m1([A, B, C, QUIET])
    chart = m1([QUIET, (111, 112, 102.5, 111)], start=BASE_TIME + 60 * MIN)
    got, m = ev(chart, htf_pre=pre)
    assert got == [(0, "SEEDED", 1, T_C, 103.0, "15"), (15, "FIRST_TOUCH", 1, T_C, 104.0, "15"),
                   (15, "CE_TOUCH", 1, T_C, 103.0, "15")]
    pre = m1([A, B, C, (111, 112, 103.5, 111)])
    got, m = ev(chart, htf_pre=pre)
    r = m.hfvg.sides[0].recs[0]
    assert r.seeded and r.pre_touch and not r.pre_ce
    assert got == [(0, "SEEDED", 1, T_C, 103.0, "15"), (15, "CE_TOUCH", 1, T_C, 103.0, "15")]


def test_seeds_are_read_once_and_never_duplicate():
    pre = m1([A, B, C, QUIET])
    got, _ = ev(m1([QUIET] * 6, start=BASE_TIME + 60 * MIN), htf_pre=pre)
    assert [g[1] for g in got] == ["SEEDED"]


def test_memory_drops_closed_records_first():
    s = Settings(modules=("htf",), fvg=FvgSettings(k_tra=0), htf=HtfSettings(tfs=("15",), memory=2))
    m = run_checked(random_walk(6000, 5, gap_prob=0.02), s)
    side = m.hfvg.sides[0]
    assert side.dropped > 0 and len(side.recs) <= 2


def test_only_timeframes_above_the_chart_are_active():
    s = Settings(modules=("htf",), htf=HtfSettings(chart_sec=900))
    assert [x.tf for x in IstModel(s).hfvg.sides] == ["30", "60", "240", "D", "W"]
    assert [x.tf for x in IstModel(Settings(modules=("htf",))).hfvg.sides] == ["15", "30", "60", "240", "D", "W"]


def test_identity_includes_the_timeframe():
    a = Event(1, 0, "HTF_FVG_CREATED", 1, T_C, 1.0, 1, "", "15")
    b = Event(1, 0, "HTF_FVG_CREATED", 1, T_C, 1.0, 1, "", "60")
    assert a.ident() != b.ident() and a.key() != b.key()
    assert NAMES == {"15": "15m", "30": "30m", "60": "1H", "240": "4H", "D": "1D", "W": "1W"}


def _ny(y, mo, d, h, mi=0):
    return int(datetime(y, mo, d, h, mi, tzinfo=ZoneInfo("America/New_York")).timestamp() * 1000)


@pytest.mark.parametrize("t, tf, want", [
    (_ny(2026, 10, 27, 11, 58), "15", _ny(2026, 10, 27, 11, 45)),
    (_ny(2026, 10, 27, 11, 58), "60", _ny(2026, 10, 27, 11)),
    (_ny(2026, 10, 27, 11, 58), "240", _ny(2026, 10, 27, 10)),
    (_ny(2026, 10, 27, 1, 30), "240", _ny(2026, 10, 26, 22)),
    (_ny(2026, 10, 27, 16, 59), "240", _ny(2026, 10, 27, 14)),
    (_ny(2026, 10, 27, 11, 58), "D", _ny(2026, 10, 26, 18)),
    (_ny(2026, 10, 30, 16, 59), "W", _ny(2026, 10, 25, 18)),
    (_ny(2026, 11, 1, 19, 0), "W", _ny(2026, 11, 1, 18)),           # the week after the DST change
    (_ny(2026, 3, 9, 3, 0), "240", _ny(2026, 3, 9, 2)),             # Monday after the DST change
])
def test_session_alignment(t, tf, want):
    """4H / 1D / 1W from the CME session start (18:00 New York), the week from Sunday's session,
    DST included. To confirm against TradingView's own HTF candles (parity check (a))."""
    assert bucket(t, tf) == want


def test_nq_with_every_module_and_all_invariants():
    m = run_checked(nq_candles(), Settings(modules=MODULES + ("lrl", "htf")))
    c = m.hfvg.state()["counters"]
    assert c["15m"]["created"] == 14 and c["30m"]["created"] == 4


@pytest.mark.parametrize("data", ["nq", "walk"])
def test_other_modules_identical_with_htf_on(data):
    cs = nq_candles() if data == "nq" else random_walk(4000, 2, gap_prob=0.02)
    off = IstModel(Settings(modules=MODULES + ("lrl",))).run(cs)
    on = IstModel(Settings(modules=MODULES + ("lrl", "htf"))).run(cs)
    assert [e for e in on.events if not e.type.startswith("HTF_")] == off.events
    st = on.state()
    assert "htf" in st and {k: v for k, v in st.items() if k != "htf"} == off.state()


def test_no_lookahead_prefix_invariance():
    cs = random_walk(3000, 9, gap_prob=0.02)
    s = Settings(modules=("htf",), fvg=FvgSettings(k_tra=0))
    full = IstModel(s).run(cs).events
    for n in range(300, len(cs), 371):
        assert IstModel(s).run(cs[:n]).events == [e for e in full if e.bar < n], n
