"""Phase 1 · daily / weekly reference levels — chart-side logic only (DEF-G2…G6).

The PDH/PDL/PWH/PWL VALUES come from request.security in Pine: MANUAL / TRADINGVIEW.
The 18:00 ET day boundary is the §7.2 ASSUMPTION (unverified until G-V1…G-V5).
"""
import pytest

from validation.invariants import run_checked
from validation.models.events import parse_local
from validation.models.types import Candle, LevelSettings, Settings

pytestmark = [pytest.mark.phase1, pytest.mark.section("phase1.levels")]
NY = "America/New_York"
HOUR = 3_600_000


def hours(start, n):
    t0 = parse_local(start, NY)
    out = []
    for i in range(n):
        p = 100 + (i * 5 % 13)
        out.append(Candle(t0 + i * HOUR, p, p + 1 + (i % 4), p - 1 - (i % 3), p + 0.5))
    return out


def run(cs, htf=None):
    return run_checked(cs, Settings(modules=("levels",), levels=LevelSettings(timeframe_sec=3600)), htf=htf)


def sets(m, tag):
    return [(e.bar, e.price) for e in m.events if e.type == "LEVEL_SET" and e.meta == tag]


@pytest.mark.spec("DEF-G2", "DEF-G5")
def test_pdh_pdl_roll_on_assumed_day_boundary():
    cs = hours("2026-10-27T16:00", 50)                        # Tue 16:00 … Thu 17:00
    m = run(cs)
    # 18:00 Tue (bar 2): the previous day started at the first loaded bar → incomplete → no value
    # 18:00 Wed (bar 26): previous day = bars 2…25, complete
    day = cs[2:26]
    assert sets(m, "PDH") == [(26, max(k.high for k in day))] and sets(m, "PDL") == [(26, min(k.low for k in day))]
    hi_bar = max(range(2, 26), key=lambda i: (cs[i].high, -i))
    assert m.levels.live[0].anchor_time == cs[hi_bar].time
    assert [b for b, _ in sets(m, "DO")] == [2, 26]


@pytest.mark.spec("DEF-G4")
def test_midnight_open():
    cs = hours("2026-10-27T22:00", 4)                         # 22, 23, 00, 01
    m = run(cs)
    assert sets(m, "MO") == [(2, cs[2].open)]


@pytest.mark.spec("DEF-G3", "DEF-G5", "DEF-G6")
def test_htf_provider_seeding_anchor_and_source_check():
    cs = hours("2026-10-27T16:00", 50)
    day = cs[2:26]
    true_hi, true_lo = max(k.high for k in day), min(k.low for k in day)

    def htf(kind, key, period):
        if kind == "W":
            return None
        return (true_hi + 0.25, true_lo) if period is not None and period.full else (500.0, 50.0)

    m = run(cs, htf)
    assert sets(m, "PDH")[0] == (0, 500.0), "first loaded bar seeds from the HTF value"
    assert sets(m, "PDH")[-1] == (26, true_hi + 0.25)
    assert m.levels.live[0].anchor_time is None, "chart extreme ≠ HTF value → no anchor"
    assert m.levels.checks["D"] == [1, 1], "one complete day compared, one mismatch (≥ half a tick)"


@pytest.mark.spec("DEF-G1")
def test_week_boundary_sunday_18_et():
    from validation.models.levels import LevelEngine
    eng = LevelEngine(LevelSettings(), 0.25, None)
    sun17, sun18 = parse_local("2026-11-01T17:00", NY), parse_local("2026-11-01T18:00", NY)
    fri16 = parse_local("2026-10-30T16:00", NY)
    assert eng.week_key(fri16) == eng.week_key(sun17) != eng.week_key(sun18)
    assert eng.day_key(parse_local("2026-10-27T17:59", NY)) != eng.day_key(parse_local("2026-10-27T18:00", NY))
