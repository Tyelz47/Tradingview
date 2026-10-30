"""CISD oracle (validation/models/cisd.py, docs/CISD.md DEF-CISD1…CISD9, approved 2026-10-30).

The numbered tests are the user's approval list (T1…T18). The oracle is also proven identical to
the approved study engine (validation/studies/cisd.py, CISD-R), so every study number holds for it."""
from dataclasses import replace

import pytest

from validation.candles import mirror, random_walk, shift
from validation.invariants import run_checked
from validation.models.cisd import UNKNOWN
from validation.models.events import ORACLE_ONLY, TYPES
from validation.models.ist import IstModel
from validation.models.types import MODULES, CisdSettings, Settings
from validation.studies import cisd as study
from validation.studies.lrl import nq_candles, resample

pytestmark = [pytest.mark.cisd, pytest.mark.section("cisd")]
S = Settings(modules=("cisd",))
ALL = Settings(modules=MODULES + ("lrl", "htf", "cisd"))
R, SC, rows = study.RECOMMENDED, study.SCENARIOS, study._rows
BASE = study._DOWN + [(95.5, 98, 95.25, 97.5)]          # bullish delivery 1…3 (L 100, low 95), bounce: bar 5 decides
# Equal delivery lows (96, bars 4 and 6) in two series; the BEARISH state first (bar 3), so the window holds both.
TIES = study._BEAR_STATE + [(97.75, 98, 96, 96.5), (96.5, 97.5, 96.25, 97.25), (97.25, 97.5, 96, 96.25),
                            (96.25, 98, 96.25, 97.75)]
# Bar 7 is an UP-close candle whose wick (95.5) undercuts the delivery low (96, bar 4).
SPIKE = study._BEAR_STATE + [(97.75, 98, 96, 96.25), (96.25, 97.5, 96.25, 97.25), (97.25, 97.5, 96.75, 97),
                             (97, 97.25, 95.5, 97.25), (97.25, 98, 97, 97.75), (97.75, 100.75, 97.5, 100.5)]


def model(cs, s=S):
    return run_checked(cs, s)


def recs(cs, s=S):
    return model(cs, s).cisd.recs


def fast(cs, s=None):
    """Unchecked run, unbounded memory: the symmetry tests compare whole streams (the invariants
    are checked by the other tests and the properties)."""
    return IstModel(s or UNBOUNDED).run(cs).cisd.recs


def ident(r, k=0, sign=1, price=lambda p: p):
    return (r.bar + k, sign * r.side, price(r.level), r.origin + k, r.ext_bar + k, price(r.ext), price(r.leg_ext),
            sign * r.before, r.retest and r.retest + k, r.reclaim and r.reclaim + k, r.broken and r.broken + k,
            r.end and r.end + k)


def evs(m):
    return [(e.bar, e.type, e.dir, e.price, e.origin_bar) for e in m.events if e.type.startswith("CISD_")]


def _walks():
    return [random_walk(4000, seed, gap_prob=0.02) for seed in (1, 2)]


# ── the oracle is the approved definition ──
UNBOUNDED = Settings(modules=("cisd",), cisd=CisdSettings(memory=10 ** 6))


@pytest.mark.parametrize("data", ["nq", "nq3", "nq5", "nq15", "walk1", "walk2"] + sorted(SC))
def test_oracle_equals_the_approved_study_engine(data):
    cs = {"nq": nq_candles, "walk1": lambda: _walks()[0], "walk2": lambda: _walks()[1]}.get(
        data, lambda: resample(nq_candles(), int(data[2:])) if data.startswith("nq") else SC[data])()
    want = [(r.bar, r.side, r.level, r.origin, r.ext_bar, r.ext, r.known, r.retest, r.reclaim, r.broken, r.end,
             r.body_k) for r in study.run(cs, R)[0]]
    got = [(r.bar, r.side, r.level, r.origin, r.ext_bar, r.leg_ext, r.known, r.retest, r.reclaim, r.broken, r.end,
            r.body_k) for r in recs(cs, UNBOUNDED)]
    assert got == want
    if data == "nq":
        assert len(got) == 121


# ── T1–T3 state of delivery ──
def test_t01_unknown_initial_state():
    """The engine starts UNKNOWN and stays UNKNOWN until a CISD: the first loaded bar, however
    large, establishes nothing; a range with no confirmed CISD keeps it UNKNOWN."""
    m = IstModel(S)
    assert m.cisd.delivery == UNKNOWN and m.state()["cisd"]["state"] == "UNKNOWN"
    m.step(rows([(100, 120, 100, 120)])[0])
    assert m.cisd.delivery == UNKNOWN and not m.events
    for name in ("3 wick through only", "4 close exactly at the level", "8 range / chop"):
        m = model(SC[name])
        assert m.cisd.delivery == UNKNOWN and m.cisd.recs == [] and m.state()["cisd"]["state"] == "UNKNOWN", name
    assert all(fast(cs)[0].before == UNKNOWN and fast(cs)[0].bar > 0 for cs in [nq_candles()] + _walks())


def test_t02_the_first_resolved_structure_establishes_the_state():
    """Both sides are armed while UNKNOWN; whichever confirms first sets the state (its record's
    prior state is UNKNOWN). Never both on one bar (engine assertion; DEF-CISD4 proof)."""
    for cs, side in ((SC["1 clean bullish CISD"], 1), (mirror(SC["1 clean bullish CISD"], 100.0), -1),
                     (rows(study._BEAR_STATE), -1)):
        m = model(cs)
        first = m.cisd.recs[0]
        assert (first.side, first.before, m.cisd.delivery) == (side, UNKNOWN, side)
        assert m.state()["cisd"]["records"][0]["before"] == "UNKNOWN"
        assert m.state()["cisd"]["records"][0]["after"] == ("BULL" if side > 0 else "BEAR")


def test_t03_strict_alternation_after_the_state_is_established():
    for cs in [nq_candles(), resample(nq_candles(), 5)] + _walks():
        rs = fast(cs)
        assert len(rs) > 10
        assert rs[0].before == UNKNOWN and all(b.side == -a.side and b.before == a.side for a, b in zip(rs, rs[1:]))
        assert all(a.end == b.bar for a, b in zip(rs, rs[1:])) and rs[-1].end is None
    trend = recs(SC["7 strong trend continuation (shallow pullbacks)"])
    assert [(r.bar, r.side) for r in trend] == [(5, 1)]                  # pullbacks in a bullish state: no second bullish
    assert [(r.bar, r.side) for r in recs(SC["12 confirmed CISD, then invalidation"])] == [(5, 1), (7, -1)]


# ── T4–T10 definition details ──
def test_t04_doji_terminates_the_delivery_series():
    """Scenario 16: down, DOJI, down (the new low). The series into the low starts after the doji:
    L = 98.25, not the 100 of a series running through it (the 'doji skipped' variant)."""
    r, = recs(SC["16 doji inside the series"])
    assert (r.bar, r.level, r.origin, r.ext_bar) == (5, 98.25, 3, 3)
    assert [(x.bar, x.level) for x in study.run(SC["16 doji inside the series"], replace(R, doji="skip"))[0]] == [(6, 100)]


def test_t05_equal_extreme_latest_delivery_candle_wins():
    bear, bull = recs(rows(TIES))
    assert (bull.bar, bull.level, bull.origin, bull.ext_bar, bull.ext) == (7, 97.25, 6, 6, 96)
    assert [(x.bar, x.side) for x in study.run(rows(TIES), replace(R, ties="first"))[0]] == [(3, -1)]   # L stays 100


def test_t06_non_delivery_wick_extreme_is_ignored():
    """The up-close spike (bar 7, low 95.5) does not select a series: L stays the open of the
    series into the delivery low (100, low 96 on bar 4). The leg extreme protected by the CISD
    (leg-break fact) is the true wick low, 95.5."""
    bear, bull = recs(rows(SPIKE))
    assert (bull.bar, bull.level, bull.origin, bull.ext_bar, bull.ext, bull.leg_ext) == (9, 100, 3, 4, 96, 95.5)
    assert [(x.bar, x.level) for x in study.run(rows(SPIKE), replace(R, extreme="any"))[0]][1:] == [(8, 97.25)]


@pytest.mark.parametrize("bar,colour", [((97.5, 100.75, 97.25, 100.5), "up-close"),
                                        ((101.5, 101.75, 100.25, 100.5), "down-close"),
                                        ((100.5, 100.75, 100.25, 100.5), "doji")])
def test_t07_confirmation_candle_of_any_colour(bar, colour):
    r, = recs(rows(BASE + [bar]))
    assert (r.bar, r.side, r.level, r.close) == (5, 1, 100, 100.5), colour
    newdir = [x.bar for x in study.run(rows(BASE + [bar]), replace(R, newdir=True))[0]]
    assert newdir == ([5] if colour == "up-close" else [])                # the rejected 'new direction' variant


def test_t08_wick_through_only_is_no_cisd():
    m = model(SC["3 wick through only"])
    assert evs(m) == [] and max(c.high for c in SC["3 wick through only"][4:]) > 100


def test_t09_close_exactly_at_the_level_is_no_cisd():
    m = model(SC["4 close exactly at the level"])
    assert evs(m) == [] and SC["4 close exactly at the level"][5].close == 100


def test_t10_one_tick_beyond_the_level_is_a_cisd():
    m = model(SC["5 close one tick beyond"])
    assert evs(m) == [(5, "CISD_CONFIRMED", 1, 100, 1)] and m.cisd.recs[0].close == 100.25


# ── T11–T14 symmetry, causality ──
@pytest.mark.parametrize("data", ["nq", "walk"] + sorted(SC))
def test_t11_exact_mirror_symmetry(data):
    cs = nq_candles() if data == "nq" else _walks()[0] if data == "walk" else SC[data]
    p = 20000.0 if data != "nq" else 30000.0
    assert [ident(r) for r in fast(mirror(cs, p))] == [ident(r, sign=-1, price=lambda x: 2 * p - x) for r in fast(cs)]


@pytest.mark.parametrize("data", ["nq", "walk"])
def test_t12_prefix_no_lookahead(data):
    """A run on the first n bars emits exactly the full run's events before n, and its records
    are the full run's, facts stamped later than n − 1 not yet known."""
    cs = nq_candles() if data == "nq" else _walks()[1]
    full = IstModel(UNBOUNDED).run(cs)
    for n in range(40, len(cs), 97):
        part = IstModel(UNBOUNDED).run(cs[:n])
        assert part.events == [e for e in full.events if e.bar < n], n
        cut = lambda b: b if b is not None and b < n else None
        want = [replace(r, end=cut(r.end), retest=cut(r.retest), reclaim=cut(r.reclaim), broken=cut(r.broken))
                for r in full.cisd.recs if r.bar < n]
        assert part.cisd.recs == want, n


@pytest.mark.parametrize("data,step", [("nq", 11), ("nq3", 3), ("nq5", 3), ("walk1", 23), ("walk2", 23)])
def test_t13_reload_history_start_convergence(data, step, limit=200):
    """The state depends on history but forgets it: started at any later bar, the truncated
    run's CISDs equal the full history's from some CISD on, and the last differing one is
    confirmed within the first `limit` loaded bars. Measured (docs/CISD.md §7, starts every 7 /
    3 / 23 bars): NQ 1m ≤ 87 bars, 3m ≤ 17, 5m ≤ 105, walks ≤ 60 — inside the 200-bar display
    guard (DEF-CISD9), which is a chart-start safeguard, not a property of the definition."""
    cs = {"nq": nq_candles, "walk1": lambda: random_walk(1500, 1, gap_prob=0.02),
          "walk2": lambda: random_walk(1500, 2, gap_prob=0.02)}.get(data, lambda: resample(nq_candles(), int(data[2:])))()
    key = lambda r, k=0: (r.bar + k, r.side, r.level, r.origin + k, r.ext_bar + k)
    full = [key(r) for r in IstModel(UNBOUNDED).run(cs).cisd.recs]
    worst = 0
    for k in range(1, len(cs) - 60, step):
        part = [key(r, k) for r in IstModel(UNBOUNDED).run(cs[k:]).cisd.recs]
        i = next(i for i in range(len(part) + 1) if part[i:] == full[len(full) - len(part) + i:])
        assert i < len(part), f"start {k}: never converged"
        worst = max(worst, part[i - 1][0] - k + 1 if i else 0)
    assert worst < limit


@pytest.mark.parametrize("ticks", [-4000, -1, 1, 37, 120_000])
def test_t14_translation_invariance(ticks):
    pts = ticks * 0.25
    for cs in [nq_candles(), _walks()[0]] + list(SC.values()):
        assert [ident(r) for r in fast(shift(cs, pts))] == [ident(r, price=lambda x: x + pts) for r in fast(cs)]


# ── T15–T16 displacement is not part of the definition ──
def test_t15_cisd_without_displacement_remains_valid():
    r, = recs(SC["15 same structure without displacement"])
    assert (r.bar, r.level) == (35, 100) and 0 < r.body_k < 1


def test_t16_same_structure_with_displacement_gives_the_same_cisd_event():
    """Only the confirming candle differs: a large body (≈ 4 × TR average) or a small one (0.2 ×).
    The CISD event is identical; the body / TR metadata records the difference. The metadata's
    TR length changes no event either."""
    big = study._warm(study._DOWN[1:] + [(95.5, 96.5, 95.25, 96.25), (96.25, 101.5, 96, 101.25)])
    small = study._warm(study._DOWN[1:] + [(95.5, 96.5, 95.25, 96.25), (100, 100.5, 99.75, 100.25)])
    a, b = model(big), model(small)
    key = lambda m: [(e.bar, e.type, e.dir, e.sid, e.price, e.origin_bar) for e in m.events]
    assert key(a) == key(b) == [(20, "CISD_CONFIRMED", 1, big[16].time, 100, 16)]
    assert a.cisd.recs[0].body_k > 4 and b.cisd.recs[0].body_k < 0.25
    for cs in (nq_candles(), big):
        assert key(model(cs, replace(S, cisd=CisdSettings(tra_len=3)))) == key(model(cs))


# ── T17–T18 isolation ──
@pytest.mark.parametrize("data", ["nq", "walk"])
def test_t17_existing_modules_identical_with_cisd_off_and_on(data):
    """Phase 1, sessions, levels, Phase 2 (BSL/SSL, EQH/EQL), LRL and HTF FVG: every event and
    all state byte-identical with the CISD module on and off."""
    cs = nq_candles() if data == "nq" else random_walk(4000, 2, gap_prob=0.02)
    off = IstModel(Settings(modules=MODULES + ("lrl", "htf"))).run(cs)
    on = IstModel(ALL).run(cs)
    assert [e for e in on.events if not e.type.startswith("CISD_")] == off.events
    st = on.state()
    assert st.pop("cisd")["records"] and st == off.state()


def test_t18_the_200_bar_guard_changes_no_cisd_logic():
    """DEF-CISD9: the guard hides CISDs confirmed before bar 200 from the renderer and alerts.
    Detection, state, records and events are identical for any guard."""
    cs = nq_candles()
    runs = {g: model(cs, replace(S, cisd=CisdSettings(guard=g))) for g in (0, 200, 10 ** 6)}
    assert len({repr(m.events) for m in runs.values()}) == 1 and len({repr(m.state()) for m in runs.values()}) == 1
    early = [e for e in runs[200].events if e.type == "CISD_CONFIRMED" and e.bar < 200]
    assert early                                                    # CISDs are detected inside the guard window
    assert runs[200].cisd.alertable(runs[200].events) == [e for e in runs[200].events
                                                         if e.type == "CISD_CONFIRMED" and e.bar >= 200]
    assert runs[0].cisd.alertable(early) == early and runs[200].cisd.alertable(early) == []
    assert runs[10 ** 6].cisd.visible(previous=True) == [] and runs[0].cisd.visible() == [runs[0].cisd.recs[-1]]
    short = model(cs[:150], replace(S, cisd=CisdSettings(guard=200)))
    assert short.cisd.recs and short.cisd.visible(previous=True) == []      # before bar 200: computed, not drawn


# ── record, events, memory, settings ──
def test_record_carries_every_approved_field():
    rec = model(SC["12 confirmed CISD, then invalidation"]).state()["cisd"]["records"][0]
    assert {"id", "side", "before", "after", "level", "origin", "ext_bar", "ext", "leg_ext", "known", "bar", "time",
            "close", "body_k", "retest", "reclaim", "broken", "status", "end"} <= set(rec)
    assert (rec["side"], rec["before"], rec["after"], rec["level"], rec["origin"], rec["ext"], rec["leg_ext"],
            rec["bar"], rec["retest"], rec["reclaim"], rec["broken"], rec["status"], rec["end"]) == \
           ("BULL", "UNKNOWN", "BULL", 100, 1, 95, 95, 5, 6, 6, 7, "ENDED", 7)


def test_lifecycle_facts_are_immutable_records_not_events():
    """Retest, close back through L and leg break are record facts: no event type exists for them."""
    assert {t for t in TYPES if t.startswith("CISD_")} == {"CISD_CONFIRMED", "CISD_DROPPED_MEMORY"} == ORACLE_ONLY
    m = model(SC["11 confirmed CISD, then a retest"])
    assert m.cisd.recs[0].retest == 6 and evs(m) == [(5, "CISD_CONFIRMED", 1, 100, 1)]


@pytest.mark.parametrize("memory", [1, 2, 7])
def test_memory_drop_path(memory):
    """DEF-CISD7: the oldest (always ENDED) record goes first, each drop logged once; the active
    CISD is never dropped. Every invariant holds (INV-CISD-08)."""
    m = model(nq_candles(), replace(S, cisd=CisdSettings(memory=memory)))
    drops = [e for e in m.events if e.type == "CISD_DROPPED_MEMORY"]
    assert len(m.cisd.recs) == memory and len(drops) == 121 - memory == m.cisd.dropped
    assert m.cisd.recs[-1].status == "ACTIVE" and all(r.status == "ENDED" for r in m.cisd.recs[:-1])


@pytest.mark.parametrize("data", ["nq", "nq3", "nq5", "nq15"])
def test_every_invariant_holds_on_nq_with_the_whole_model(data):
    cs = nq_candles() if data == "nq" else resample(nq_candles(), int(data[2:]))
    assert model(cs, ALL).cisd.confirmed > 5


def test_module_is_opt_in_and_does_not_change_case_definitions():
    assert "cisd" not in Settings().modules and "cisd" not in Settings().to_dict()
    assert IstModel(Settings()).cisd is None
    s = Settings.from_dict({"modules": ["cisd"], "cisd": {"memory": 5}})
    assert s.modules == ("cisd",) and s.cisd.memory == 5 and s.to_dict()["cisd"]["guard"] == 200
