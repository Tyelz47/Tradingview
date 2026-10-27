"""Phase 1 · sessions (DEF-F1…F6), reproduced from bar times in America/New_York.

What stays MANUAL / TRADINGVIEW: Pine's time(timeframe, session, tz) itself.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from validation.invariants import run_checked
from validation.models.events import parse_local
from validation.models.sessions import in_window
from validation.models.types import Candle, SessionSettings, Settings

pytestmark = [pytest.mark.phase1, pytest.mark.section("phase1.sessions")]
NY = "America/New_York"


def utc(text):
    return int(datetime.fromisoformat(text).replace(tzinfo=ZoneInfo("UTC")).timestamp() * 1000)


def minutes(start, n, step=60_000, base=100.0):
    t0 = parse_local(start, NY)
    out = []
    for i in range(n):
        p = base + (i * 7 % 11) * 0.25
        out.append(Candle(t0 + i * step, p, p + 1 + (i % 3) * 0.25, p - 1 - (i % 5) * 0.25, p + 0.25))
    return out


def run(candles, tf=60):
    return run_checked(candles, Settings(modules=("sessions",), sessions=SessionSettings(timeframe_sec=tf)))


@pytest.mark.spec("DEF-F1")
@pytest.mark.parametrize("local, spec, inside", [
    ("2026-10-27T09:29", "0930-1200", False), ("2026-10-27T09:30", "0930-1200", True),
    ("2026-10-27T11:59", "0930-1200", True), ("2026-10-27T12:00", "0930-1200", False),
    ("2026-10-27T19:59", "2000-0000", False), ("2026-10-27T20:00", "2000-0000", True),
    ("2026-10-27T23:59", "2000-0000", True), ("2026-10-28T00:00", "2000-0000", False),
    ("2026-10-28T02:00", "0200-0500", True), ("2026-10-28T05:00", "0200-0500", False),
    ("2026-10-27T22:00", "2200-0300", True), ("2026-10-28T02:59", "2200-0300", True),
    ("2026-10-28T03:00", "2200-0300", False)])
def test_window_membership(local, spec, inside):
    assert in_window(parse_local(local, NY), spec, NY) is inside


@pytest.mark.spec("DEF-F1")
def test_dst_keeps_local_session_time():
    """US DST ends 2026-11-01: 09:30 ET is 13:30 UTC before and 14:30 UTC after."""
    assert in_window(utc("2026-10-30T13:30"), "0930-1200", NY)
    assert in_window(utc("2026-11-02T14:30"), "0930-1200", NY)
    assert not in_window(utc("2026-11-02T13:30"), "0930-1200", NY)


@pytest.mark.spec("DEF-F2", "DEF-F3", "DEF-F4")
def test_ny_am_lifecycle():
    cs = minutes("2026-10-27T09:25", 161)                     # 09:25 … 12:05
    m = run(cs)
    types = [(e.bar, e.type) for e in m.events]
    assert types == [(5, "SESSION_START"), (155, "SESSION_END")]
    s = m.sessions.live[2]
    inside = cs[5:155]
    assert (s.start_bar, s.end_bar, s.complete) == (5, 154, True)
    assert s.hi == max(k.high for k in inside) and s.lo == min(k.low for k in inside)
    assert s.id == cs[5].time and s.known_time == cs[155].time


@pytest.mark.spec("DEF-F2")
def test_never_starts_on_the_first_loaded_bar():
    m = run(minutes("2026-10-27T09:30", 30))
    assert not m.events and m.sessions.live[2] is None


@pytest.mark.spec("DEF-F1", "DEF-F4")
def test_window_crossing_midnight():
    cs = minutes("2026-10-27T19:58", 245)                     # 19:58 … 00:02
    m = run(cs)
    asia = [(e.bar, e.type) for e in m.events if "Asia" in e.meta or e.sid == cs[2].time]
    assert asia == [(2, "SESSION_START"), (242, "SESSION_END")]


@pytest.mark.spec("DEF-F6")
def test_supersession_next_day():
    day1 = minutes("2026-10-27T09:29", 152)                   # 09:29 … 12:00
    day2 = minutes("2026-10-28T09:29", 3)
    m = run(day1 + day2)
    assert [e.type for e in m.events] == ["SESSION_START", "SESSION_END", "SESSION_START"]
    assert m.sessions.done[0].id == day1[1].time and m.sessions.live[2].id == day2[1].time


@pytest.mark.spec("DEF-F1")
def test_no_sessions_above_one_hour():
    cs = minutes("2026-10-27T08:00", 10, step=7_200_000)
    assert not run(cs, tf=7200).events
