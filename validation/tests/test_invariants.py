"""Negative tests: every invariant detector must fire on a deliberately corrupted state.

An invariant that never fails proves nothing unless its detector is shown to work.
Each case builds a valid model, corrupts one thing, and expects InvariantViolation
with exactly that invariant id. Detectors proven here are listed in the report.
"""
from dataclasses import replace

import pytest

from validation import stats
from validation.candles import WARM, from_rows
from validation.invariants import REGISTRY, InvariantViolation, Monitor
from validation.models.eq import BREAK
from validation.models.events import Event, parse_local
from validation.models.ist import IstModel
from validation.models.types import Candle, LevelSettings, SessionSettings, Settings
from validation.scenarios import EQ_AB, QUIET_HI, SWING_HI, fvg_settings, liq_settings

pytestmark = [pytest.mark.common, pytest.mark.section("invariants")]

BULL = [(100, 101, 99, 100.5), (100.5, 104, 100.5, 103.5), (103.5, 105, 102, 104.5)]
STEPS = [(104.5, 105, 101.75, 102.5), (102.5, 103, 101.5, 102), (102, 102.5, 101, 101.25),
         (101.25, 101.5, 100.5, 101), (101, 101.25, 100, 100.25)]
TAKE = (99.5, 102.25, 99, 101.5)                               # takes BSL 102 by one tick, closes back (sweep)


def staircase(n):
    return [(100 + 2 * i, 101 + 2 * i, 99 + 2 * i, 100.5 + 2 * i) for i in range(n)]


def build(rows, settings, checked=None, **kw):
    """Model + monitor; the first `checked` bars (default: all) are stepped AND checked."""
    cs = from_rows(rows)
    m = IstModel(settings, **kw)
    mon = Monitor(m)
    n = len(cs) if checked is None else checked
    for c in cs[:n]:
        m.step(c)
        mon.check()
    for c in cs[n:]:
        m.step(c)
    return m, mon


def ev_now(m, type_, d, sid, price=None):
    return Event(m.bar, m.candles[-1].time, type_, d, sid, price, m.bar)


def fvg_case():
    return build(BULL + STEPS, fvg_settings())


def liq_case(extra=(), checked=None):
    rows = WARM + SWING_HI + list(extra)
    return build(rows, liq_settings(), checked=None if checked is None else 20 + checked)


def eq_case(extra=(), checked=None, **kw):
    rows = WARM + EQ_AB + QUIET_HI + list(extra)
    return build(rows, liq_settings(**kw), checked=None if checked is None else 20 + checked)


def lvl(m, bar):
    return next(x for x in m.liq.bsl.hist + m.liq.bsl.live if x.origin_bar == bar)


# ── corruptions, one per invariant ──
def ev01():
    m, mon = fvg_case()
    m.log.events.append(Event(m.bar - 3, m.candles[-1].time, "FVG_CE_TOUCH", 1, 1, 1.0, 0))
    mon.check()


def ev02():
    m, mon = fvg_case()
    m.log.events[0] = replace(m.log.events[0], price=0.0)
    m.step(Candle(m.candles[-1].time + 60_000, 100, 101, 99, 100))
    mon.check()


def ev03():
    m, mon = fvg_case()
    m.log.events.append(replace(m.log.events[0], bar=m.bar, time=m.candles[-1].time))
    mon.check()


def ev04():
    m, mon = build(staircase(13), fvg_settings(memory=10))
    dropped = next(e for e in m.events if e.type == "FVG_DROPPED_MEMORY")
    m.log.events.append(ev_now(m, "FVG_FIRST_TOUCH", 1, dropped.sid, 0.0))
    mon.check()


def ev05():
    m, mon = fvg_case()
    m.log.events.append(ev_now(m, "BSL_TAKEN", 1, 123, 1.0))
    mon.check()


def fvg01():
    m, mon = fvg_case()
    z = m.fvg.bull[0]
    z.top = z.bottom - 1
    mon.check(full=True)


def fvg02():
    m, mon = fvg_case()
    m.fvg.bull[0].mid += 0.25
    mon.check(full=True)


def fvg03():
    m, mon = build(BULL + STEPS[:2], fvg_settings())
    m.fvg.bull[0].touch_bar = 4
    mon.check(full=True)


def fvg04():
    m, mon = build(BULL + [(104.5, 105, 103, 104)], fvg_settings())
    m.fvg.bull[0].ce_bar = 3
    mon.check(full=True)


def fvg05():
    m, mon = build(BULL + STEPS[:1], fvg_settings(), checked=3)
    m.fvg.bull[0].touch_bar = None
    mon.check()


def fvg06():
    m, mon = build(BULL + STEPS, fvg_settings(), checked=7)
    z = m.fvg.bull[0]
    z.inv_bar = z.inv_time = None
    assert m.log.events.pop().type == "FVG_INVALIDATED"
    mon.check()


def fvg07():
    m, mon = fvg_case()
    m.fvg.bull[0].extreme += 5
    mon.check(full=True)


def fvg08():
    m, mon = build(BULL, fvg_settings(), checked=2)
    z = m.fvg.bull[0]
    z.top += 0.5
    z.mid = (z.top + z.bottom) / 2
    mon.check()


def fvg09():
    m, mon = build(staircase(12), fvg_settings(memory=10))
    m.fvg.bull.append(replace(m.fvg.bull[-1]))
    mon.check()


def fvg10():
    m, mon = build(BULL + [(104.5, 105, 103, 104)], fvg_settings())
    m.log.events.append(ev_now(m, "FVG_CE_TOUCH", 1, m.fvg.bull[0].id, m.fvg.bull[0].mid))
    mon.check()


def liq01():
    m, mon = liq_case()
    m.liq.bsl.live[0].confirm_bar += 1
    mon.check(full=True)


def liq02():
    m, mon = liq_case([TAKE], checked=2)
    x = lvl(m, 20)
    x.taken_bar = x.confirm_bar
    mon.check()


def liq03():
    m, mon = liq_case([TAKE], checked=2)
    lvl(m, 20).cls = BREAK
    mon.check()


def liq04():
    m, mon = liq_case([TAKE])
    lvl(m, 20).take_ext += 0.25
    mon.check(full=True)


def liq05():
    m, mon = liq_case([TAKE], checked=2)
    x = lvl(m, 20)
    x.take_ext = x.price
    mon.check()


def liq06():
    m, mon = liq_case([TAKE], checked=2)
    x = lvl(m, 20)
    x.taken_bar = x.taken_time = x.take_ext = x.take_close = x.far = None
    x.cls, x.take_gap = 0, False
    del m.log.events[-2:]                                       # BSL_TAKEN + BSL_SWEEP
    mon.check()


def liq07():
    m, mon = liq_case()
    x = m.liq.bsl.live[0]
    x.react = x.react_req - 1
    mon.check(full=True)


def liq08():
    m, mon = liq_case(checked=1)
    m.liq.bsl.live[0].price += 0.25
    mon.check()


def liq11():
    m, mon = build(WARM + SWING_HI, liq_settings(dom=10))
    x = m.liq.bsl.live[0]
    m.liq.H[x.origin_bar - 1] = x.price + 1.25         # an earlier high 5 ticks above: not dominant
    mon.check(full=True)


def liq12():
    m, mon = liq_case()
    m.liq.bsl.rej_react += 1                             # REJECT by reason no longer adds up
    mon.check()


def liq09():
    m, mon = liq_case()
    side = m.liq.bsl
    side.live += [replace(side.live[0]) for _ in range(m.settings.liq.memory)]
    mon.check()


def liq10():
    m, mon = liq_case([TAKE], checked=2)
    assert m.log.events.pop().type == "BSL_SWEEP"
    mon.check()


def eq01():
    m, mon = eq_case()
    c = m.liq.bsl.eqs[0]
    m.liq.bsl.eqs.append(replace(c, id=c.id + 1, members=[c.members[0]]))
    mon.check(full=True)


def eq02():
    m, mon = eq_case()
    m.liq.bsl.eqs[0].ref += 1
    mon.check(full=True)


def eq03():
    m, mon = eq_case()
    m.liq.bsl.eqs[0].bound -= 0.25
    mon.check(full=True)


def eq04():
    m, mon = eq_case()
    m.liq.bsl.eqs[0].members.pop()
    mon.check(full=True)


def eq05():
    m, mon = eq_case()
    c = m.liq.bsl.eqs[0]
    c.taken_bar, c.cls = c.bar, BREAK
    mon.check(full=True)


def eq06():
    m, mon = eq_case([(99, 102.5, 98.7, 101), (101, 101.25, 99, 99.5)])
    m.liq.bsl.eqs[0].taken_bar += 1
    mon.check(full=True)


def eq07():
    m, mon = eq_case()
    c = m.liq.bsl.eqs[0]
    a = lvl(m, 20)                                              # taken member (by B), snapshotted
    a.take_close += 0.25
    c.members.append(999)                                       # a join on this bar
    mon._eq(m.bar, m.candles[-1], [ev_now(m, "BSL_CREATED", 1, 999)], False)


def eq08():
    m, mon = eq_case()
    lvl(m, 24).price = 100.0
    mon.check(full=True)


def eq09():
    m, mon = eq_case()
    m.liq.bsl.eqs[0].bound += 0.25
    mon.check(full=True)


def eq10():
    m, mon = eq_case([(99, 102.5, 98.7, 101)], checked=8)
    c = m.liq.bsl.eqs[0]
    c.taken_bar = c.taken_time = None
    c.cls = 0
    assert m.log.events.pop().type == "EQH_TAKEN"
    mon.check()


def eq11():
    m, mon = eq_case()
    m.liq.bsl.eqs[0].qual_bar = None
    mon.check(full=True)


def eq12():
    m, mon = eq_case([(99, 102.5, 98.7, 101)], checked=8)
    assert m.log.events[-1].type == "EQH_TAKEN"
    m.log.events[-1] = replace(m.log.events[-1], price=m.log.events[-1].price + 0.25)
    mon.check()


def _session_model(n, checked):
    t0 = parse_local("2026-10-27T09:28", "America/New_York")
    cs = [Candle(t0 + i * 60_000, 100, 101 + (i % 3), 99, 100) for i in range(n)]
    m = IstModel(Settings(modules=("sessions",), sessions=SessionSettings()))
    mon = Monitor(m)
    for i, c in enumerate(cs):
        m.step(c)
        if i < checked:
            mon.check()
    return m, mon


def ses01():
    m, mon = _session_model(155, 153)                           # 12:00 is bar 152 → END emitted there
    m, mon = _session_model(153, 152)
    m.sessions.live[2].hi += 1
    mon.check()


def ses02():
    m, mon = _session_model(10, 10)
    s = m.sessions.live[2]
    s.id = m.candles[-1].time
    m.log.events.append(ev_now(m, "SESSION_START", 0, s.id))
    mon.check()


def lvl01():
    t0 = parse_local("2026-10-27T16:00", "America/New_York")
    cs = [Candle(t0 + i * 3_600_000, 100, 101, 99, 100) for i in range(4)]
    m = IstModel(Settings(modules=("levels",), levels=LevelSettings(timeframe_sec=3600)))
    mon = Monitor(m)
    for c in cs:
        m.step(c)
        mon.check()
    m.log.events.append(ev_now(m, "LEVEL_SET", 0, 4, 1.0))
    mon.check()


# ── LRL (opt-in module, docs/LRL.md) ──
def lrl_case(name="4th and 5th point extension", upto=None):
    """Scenario bars stepped and checked: by bar 120 the high-side LRL has 5 points and is active."""
    from validation.studies.lrl import SCENARIOS
    m = IstModel(Settings(modules=("lrl",)))
    mon = Monitor(m)
    for c in SCENARIOS[name][:upto]:
        m.step(c)
        mon.check()
    return m, mon


def lrl01():
    m, mon = lrl_case(upto=120)
    r = m.lrl.high.live[0]
    m.lrl.high.hist.append(replace(r, id=r.id + 1, xs=list(r.xs), ps=list(r.ps), ext=list(r.ext)))
    mon.check()


def lrl02():
    m, mon = lrl_case(upto=120)
    m.lrl.high.live[0].ps[1] -= 0.25
    mon.check()


def lrl03():
    m, mon = lrl_case(upto=120)
    m.lrl.high.live[0].tau += 0.25
    mon.check()


def lrl04():
    m, mon = lrl_case(upto=120)
    m.lrl.high.hi[90] += 50                                      # bar 90 lies in no point's pivot window
    mon.check()


def lrl05():
    m, mon = lrl_case("sweep (wick through, close back)")
    m.lrl.high.hist[0].end = "BREAK"
    mon.check()


def lrl06():
    m, mon = lrl_case(upto=120)
    m.lrl.high.live[0].born += 1
    mon.check()


def lrl07():
    m, mon = lrl_case("clean bearish LRL")
    m.lrl.high.hist[0].end_level += 1                            # an expired record's end fact
    mon.check()


def lrl08():
    m, mon = lrl_case(upto=120)
    m.log.events.append(ev_now(m, "LRL_EXTENDED", 1, m.lrl.high.live[0].id, 1.0))
    mon.check()


def lrl09():
    m, mon = lrl_case(upto=120)
    m.lrl.s = replace(m.lrl.s, memory=0)
    mon.check()


def lrl10():
    m, mon = lrl_case("strong trend, collinear highs")                # ends with LRL_DRIFT on bar 107
    r = m.lrl.high.hist[0]
    assert r.end == "DRIFT"
    m.log.events.append(ev_now(m, "LRL_SWEEP", 1, r.id, 1.0))      # relabelled later as a SWEEP
    mon.check()


# ── HTF FVG (opt-in module, docs/HTF_FVG.md) ──
def htf_case():
    """The merged NQ captures with the HTF module, stepped and checked (15m and 30m zones form,
    are touched, filled and invalidated)."""
    from validation.studies.lrl import nq_candles
    m = IstModel(Settings(modules=("htf",)))
    mon = Monitor(m)
    for c in nq_candles():
        m.step(c)
        mon.check()
    return m, mon, m.hfvg.sides[0]                    # the 15m side


def _first_seen(mon, side, r):
    """Timing and geometry are checked when a record first appears (INV-HTF-08 freezes them
    afterwards): forget the monitor's snapshot of r so the corruption is a new record's."""
    mon.htf_snap.pop((side.tf, r.dir, r.id))
    return r


def htf01():
    m, mon, side = htf_case()
    _first_seen(mon, side, next(r for r in side.recs if not r.seeded)).known_bar -= 1
    mon.check()


def htf02():
    m, mon, side = htf_case()
    _first_seen(mon, side, side.recs[0]).top += 0.25
    mon.check()


def htf08_geometry_change():
    """The same corruption on a record the monitor already knows: INV-HTF-08 (frozen facts)."""
    m, mon, side = htf_case()
    side.recs[0].top += 0.25
    mon.check()


def htf03():
    m, mon, side = htf_case()
    r = next(r for r in side.recs if r.ce_bar is not None)
    r.ce_bar = r.known_bar - 1
    mon.check()


def htf04():
    m, mon, side = htf_case()
    r = next(r for r in side.recs if r.inv_bar is not None)
    r.inv_close = r.top + 10 if r.dir > 0 else r.bottom - 10
    mon.check()


def htf05():
    m, mon, side = htf_case()
    side.recs.append(replace(side.recs[0]))
    mon.check()


def htf06():
    m, mon, side = htf_case()
    m.hfvg.s = replace(m.hfvg.s, memory=0)
    mon.check()


def htf07():
    m, mon, side = htf_case()
    r = next(r for r in side.recs if r.touch_bar is None and r.inv_bar is None)
    m.log.events.append(replace(ev_now(m, "HTF_FVG_FIRST_TOUCH", r.dir, r.id, r.top), tf=side.tf))
    mon.check()


def htf08():
    m, mon, side = htf_case()
    next(r for r in side.recs if not r.seeded).pre_touch = True
    mon.check()


CASES = {
    "INV-EV-01": ev01, "INV-EV-02": ev02, "INV-EV-03": ev03, "INV-EV-04": ev04, "INV-EV-05": ev05,
    "INV-FVG-01": fvg01, "INV-FVG-02": fvg02, "INV-FVG-03": fvg03, "INV-FVG-04": fvg04, "INV-FVG-05": fvg05,
    "INV-FVG-06": fvg06, "INV-FVG-07": fvg07, "INV-FVG-08": fvg08, "INV-FVG-09": fvg09, "INV-FVG-10": fvg10,
    "INV-LIQ-01": liq01, "INV-LIQ-02": liq02, "INV-LIQ-03": liq03, "INV-LIQ-04": liq04, "INV-LIQ-05": liq05,
    "INV-LIQ-06": liq06, "INV-LIQ-07": liq07, "INV-LIQ-08": liq08, "INV-LIQ-09": liq09, "INV-LIQ-10": liq10,
    "INV-LIQ-11": liq11, "INV-LIQ-12": liq12,
    "INV-EQ-01": eq01, "INV-EQ-02": eq02, "INV-EQ-03": eq03, "INV-EQ-04": eq04, "INV-EQ-05": eq05,
    "INV-EQ-06": eq06, "INV-EQ-07": eq07, "INV-EQ-08": eq08, "INV-EQ-09": eq09, "INV-EQ-10": eq10,
    "INV-EQ-11": eq11, "INV-EQ-12": eq12,
    "INV-SES-01": ses01, "INV-SES-02": ses02, "INV-LVL-01": lvl01,
    "INV-LRL-01": lrl01, "INV-LRL-02": lrl02, "INV-LRL-03": lrl03, "INV-LRL-04": lrl04, "INV-LRL-05": lrl05,
    "INV-LRL-06": lrl06, "INV-LRL-07": lrl07, "INV-LRL-08": lrl08, "INV-LRL-09": lrl09, "INV-LRL-10": lrl10,
    "INV-HTF-01": htf01, "INV-HTF-02": htf02, "INV-HTF-03": htf03, "INV-HTF-04": htf04, "INV-HTF-05": htf05,
    "INV-HTF-06": htf06, "INV-HTF-07": htf07, "INV-HTF-08": htf08,
}


def test_every_invariant_has_a_negative_test():
    assert set(CASES) == set(REGISTRY), set(REGISTRY) ^ set(CASES)


def test_htf_geometry_change_on_a_known_record_is_frozen_violation():
    with pytest.raises(InvariantViolation) as err:
        htf08_geometry_change()
    assert err.value.inv_id == "INV-HTF-08", str(err.value)


@pytest.mark.parametrize("inv_id", sorted(CASES))
def test_detector_fires(inv_id):
    with pytest.raises(InvariantViolation) as err:
        CASES[inv_id]()
    assert err.value.inv_id == inv_id, f"expected {inv_id}, got: {err.value}"
    stats.RESULTS.setdefault("detectors", set()).add(inv_id)
