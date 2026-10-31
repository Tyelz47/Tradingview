"""CISD freeze (IST v0.7.1-dev): the CISD-L11 rule list and the automated CISD-L12 (reload /
determinism) requirements, each pinned by name. Where an earlier test already proves a rule, the
list below names it instead of repeating it; the tests here add the angles not yet explicit.

CISD-L11 rule                                        proven by
first candle of the delivery series gives L          test_l11_first_candle_gives_l (+ T4, T5, human H1 / H2)
the run's last candle never replaces the first       test_l11_last_candle_never_replaces_the_first
non-delivery candles never set the extreme           T6 (tests/test_cisd.py), human H2, test_l11_human_goldens
wick through L is no CISD · close at L is no CISD    T8, T9
close strictly through L is a CISD                   T10
bullish = exact mirror of bearish                    T11, fuzz/test_cisd_properties.py
initial state UNKNOWN                                T1
strict UP / DOWN alternation after the first CISD    T3
a CISD stays valid when price later fails            test_l11_a_failed_cisd_stays_a_cisd
FVG, IFVG, LRL, sweeps, displacement not required    T15, T16, test_l11_detection_needs_no_other_module

CISD-L12 (reload / determinism), automated part      proven by
same OHLC + settings → same per-bar state, both      test_l12_identical_history_gives_identical_results
candidates, active CISD, records and lifecycle
the Pine formulation (CisdStack) = the oracle         tests/test_cisd_pine.py, fuzz (property)
no lookahead: a prefix = the full run's past          T12, fuzz
display / alert / debug / capture inputs never        test_l12_view_inputs_never_reach_the_engine (+ ST-01, ST-20)
reach CISD state
guard changes no logic                               T18, fuzz
guard never draws a CISD retroactively               test_l12_guard_never_draws_retroactively
real TradingView: Pine = oracle bar by bar           tests/test_parity_v071_evidence.py (v0.7.1-dev capture)
"""
from dataclasses import replace

import pytest

from validation import PINE_SOURCE
from validation.golden import candles_of, load_cases, run_case
from validation.models.cisd import CisdEngine, CisdStack
from validation.models.events import EventLog
from validation.models.ist import IstModel
from validation.models.types import MODULES, NQ_TICK, CisdSettings, Settings
from validation.static_checks import CALC_INPUTS, CALC_SECTIONS, _cisd_blocks, lines_of, source
from validation.studies import cisd as study
from validation.studies.lrl import nq_candles

pytestmark = [pytest.mark.cisd, pytest.mark.section("cisd")]
S = Settings(modules=("cisd",))
BIG = CisdSettings(memory=10 ** 6)
HUMAN = {c["id"]: c for _, c in load_cases() if c["id"].startswith("GOLD_CISD_H")}


def _run(cls, cs, s=BIG):
    log = EventLog()
    e = cls(s, NQ_TICK, log)
    trace = []
    for t, c in enumerate(cs):
        log.at(t, c.time)
        e.step(t, c)
        if isinstance(e, CisdStack):
            act = e.active
            trace.append((e.delivery, e.candidate(1), e.candidate(-1), None if act is None else (act.side, act.id)))
        else:
            trace.append(e.delivery)
    return e, log.events, trace


# ── CISD-L11 ──
def test_l11_human_goldens():
    """The deterministic human goldens (H1 reference product, H2 trader) reproduce exactly; H3 / H4
    stay supporting references (their OHLC cannot be recovered: validation/golden/human/README.md)."""
    assert set(HUMAN) == {"GOLD_CISD_H1", "GOLD_CISD_H2"}
    for case in HUMAN.values():
        assert run_case(case)[1] == [], case["id"]


def test_l11_first_candle_gives_l():
    """Every CISD's L is the open of the FIRST candle of its delivery series: the candle before
    the origin is not a delivery candle (NQ, both sides, every record)."""
    cs = nq_candles()
    e, _, _ = _run(CisdEngine, cs)
    for r in e.recs:
        o = cs[r.origin]
        assert r.level == o.open
        if r.origin > 0:
            p = cs[r.origin - 1]
            assert not (r.side * (p.close - p.open) < -0.0025), r          # not a delivery candle of that side


def test_l11_last_candle_never_replaces_the_first():
    """Scenario 1: down series 1…3; L = 100 (bar 1's open), never 96.5 / 98.5 (later candles' opens).
    Human H1: the last-candle anchor (study CISD-4) would give row 297 on bar 22; the oracle and the
    trader's line give row 180 on bar 26."""
    r, = _run(CisdEngine, study.SCENARIOS["1 clean bullish CISD"])[0].recs
    assert (r.level, r.origin) == (100, 1)
    cs = candles_of(HUMAN["GOLD_CISD_H1"])
    first = [(x.bar, x.level) for x in study.run(cs, study.RECOMMENDED)[0] if x.side > 0][-1]
    last = [(x.bar, x.level) for x in study.run(cs, study.SPECS[3])[0] if x.side > 0][-1]
    assert first == (26, 820) and last == (22, 703)


def test_l11_a_failed_cisd_stays_a_cisd():
    """A CISD is never withdrawn or relabelled when price later fails (closes back through L,
    breaks the leg extreme): the event stays, the record keeps every identity field; only the
    immutable facts and the end are added. Scenario 12, then every failed CISD on NQ."""
    cs = study.SCENARIOS["12 confirmed CISD, then invalidation"]
    at5, _, _ = _run(CisdEngine, cs[:6])
    full, events, _ = _run(CisdEngine, cs)
    bull = full.recs[0]
    assert (bull.reclaim, bull.broken, bull.end) == (6, 7, 7) and \
           replace(bull, retest=None, reclaim=None, broken=None, end=None) == at5.recs[0]
    assert [e.type for e in events].count("CISD_CONFIRMED") == 2 and {e.type for e in events} == {"CISD_CONFIRMED"}
    nq = nq_candles()
    e, ev, _ = _run(CisdEngine, nq)
    failed = [r for r in e.recs if r.broken is not None]
    assert len(failed) >= 10
    for r in failed:
        cut, _, _ = _run(CisdEngine, nq[:r.bar + 1])
        assert replace(r, retest=None, reclaim=None, broken=None, end=None) == cut.recs[-1]
        assert any(x.type == "CISD_CONFIRMED" and x.bar == r.bar and x.sid == r.id for x in ev)


@pytest.mark.parametrize("data", ["nq", "walk"])
def test_l11_detection_needs_no_other_module(data):
    """CISD events and state are the same with CISD alone and with every other module (FVG,
    liquidity / sweeps, EQ, LRL, HTF FVG) running; no other module's state is named in the CISD
    engine's Pine code. IFVG and displacement do not exist; T15 / T16 show displacement is neither
    required nor used."""
    from validation.candles import random_walk
    cs = nq_candles() if data == "nq" else random_walk(4000, 7, gap_prob=0.02)
    alone = IstModel(S).run(cs)
    full = IstModel(Settings(modules=MODULES + ("lrl", "htf", "cisd"))).run(cs)
    pick = lambda m: [e for e in m.events if e.type.startswith("CISD_")]
    assert pick(alone) == pick(full) and alone.cisd.state() == full.cisd.state()
    engine = "\n".join(_cisd_blocks(list(source())))
    other = ("bullFvgs", "bearFvgs", "bslS", "sslS", "lrlHi", "lrlLo", "htfTfs", "liveLvl", "liveSes", "lrlTra",
             "liqTra", "traNow", "pivHi", "pivLo", "sigHi", "sigLo")
    assert not [n for n in other if n in engine]


# ── CISD-L12 (automated) ──
@pytest.mark.parametrize("data", ["nq", "long"])
def test_l12_identical_history_gives_identical_results(data):
    """Identical OHLC and settings, two fresh engines, full replays: identical per-bar delivery
    state, both sides' candidate L, active CISD, every record (side, origin time / id, L,
    confirmation bar and time, previous state, delivery extreme and its bar, leg extreme, body / TR)
    and its lifecycle (end, facts). The Pine formulation and the oracle agree on all of it."""
    from validation.tests.test_cisd_pine import long_legs
    cs = nq_candles() if data == "nq" else long_legs()
    a, ea, ta = _run(CisdStack, cs)
    b, eb, tb = _run(CisdStack, cs)
    o, eo, to = _run(CisdEngine, cs)
    assert ta == tb and a.recs == b.recs and ea == eb
    assert [x[0] for x in ta] == to and a.recs == o.recs and ea == eo
    s50 = Settings(modules=("cisd",))
    assert IstModel(s50).run(cs).state() == IstModel(s50).run(cs).state()


def test_l12_view_inputs_never_reach_the_engine():
    """Show CISD, Show previous CISD, CISD alerts, Debug, Inspect CISD and the parity capture are
    [view] / [alert] inputs: none is read by any calculation section (L1, L2, L3, L5, ENGINE RUN)
    nor by the CISD engine; the guard constant neither."""
    names = ("cisdShow", "cisdPrev", "cisdAlert", "dbgOn", "dbgCisdIns", "capOn", "capN", "CISD_GUARD")
    assert not set(names) & CALC_INPUTS
    calc = "\n".join(ln for _, ln in lines_of(CALC_SECTIONS))
    engine = "\n".join(_cisd_blocks(list(source())))
    import re
    assert not [n for n in names if re.search(rf"\b{n}\b", calc) or re.search(rf"\b{n}\b", engine)]
    assert "cisdOn" in CALC_INPUTS and PINE_SOURCE.exists()


def test_l12_guard_never_draws_retroactively():
    """A CISD confirmed before bar 200 is never drawn: not while the guard runs, not on bar 200,
    not later as the previous CISD. The first CISD confirmed after the guard is drawn."""
    cs = nq_candles()
    m = IstModel(S)
    seen_inside = seen_first_after = False
    for t, c in enumerate(cs):
        m.step(c)
        recs = m.cisd.recs
        shown = m.cisd.visible(previous=True)
        assert all(r.bar >= 200 for r in shown), t
        if t >= 200 and recs and recs[-1].bar < 200:
            assert m.cisd.visible() == [] and m.cisd.visible(previous=True) == []
            seen_inside = True
        if recs and recs[-1].bar >= 200 and len(recs) > 1 and recs[-2].bar < 200:
            assert m.cisd.visible(previous=True) == [recs[-1]]
            seen_first_after = True
    assert seen_inside and seen_first_after
