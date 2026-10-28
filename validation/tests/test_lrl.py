"""LRL detection oracle (validation/models/lrl.py, docs/LRL.md DEF-LRL1…LRL8): the approved
definition, its events, its coexistence with Phase 1 / Phase 2, and its agreement with
the independent study engine (validation/studies/lrl.py) that the user approved."""
import pytest

from validation.candles import random_walk
from validation.invariants import run_checked
from validation.models.ist import IstModel
from validation.models.types import MODULES, LrlSettings, Settings
from validation.studies import lrl as study

pytestmark = [pytest.mark.lrl, pytest.mark.section("lrl")]
ON = Settings(modules=MODULES + ("lrl",))
SIDE = {1: "bear", -1: "bull"}                  # event dir +1 = the high side = the bearish LRL


def _run(cs, s=ON):
    return IstModel(s).run(cs)


def _short(m):
    return sorted((e.bar, e.type, SIDE[e.dir], e.origin_bar) for e in m.events if e.type.startswith("LRL_"))


def _data():
    return [("nq", study.nq_candles())] + [(f"walk{s}", random_walk(4000, s, gap_prob=0.02)) for s in (1, 2, 3)]


def test_approved_constants():
    """DEF-LRL1…6 as approved on 2026-10-28; changing one is a definition change."""
    assert LrlSettings() == LrlSettings(left=3, right=2, tol_k=0.5, gap=30, sep_k=1.0, drop_k=2.0, tra_len=14,
                                        cand_memory=25, memory=50)
    r = study.RECOMMENDED
    assert (r.left, r.right, r.tol, r.gmax, r.sep, r.drop, r.geometry) == (3, 2, ("tr", 0.5), 30, 1.0, 2.0, "chord")


@pytest.mark.parametrize("name", sorted(study.SCENARIOS))
def test_oracle_equals_the_approved_study_engine_on_scenarios(name):
    cs = study.SCENARIOS[name]
    want = sorted((b, k, s, a) for b, k, s, a, _ in study.events(study.both(cs, study.RECOMMENDED, {})))
    assert _short(_run(cs, Settings(modules=("lrl",)))) == want


@pytest.mark.parametrize("which", range(4), ids=["nq", "walk1", "walk2", "walk3"])
def test_oracle_equals_the_approved_study_engine_on_data(which):
    name, cs = _data()[which]
    want = sorted((b, k, s, a) for b, k, s, a, _ in study.events(study.both(cs, study.RECOMMENDED, {})))
    assert _short(_run(cs)) == want and want


def test_nq_numbers_of_the_approved_study():
    """27 LRLs (15 on highs, 12 on lows) on the merged NQ captures, as approved."""
    m = _run(study.nq_candles())
    c = m.lrl.state()["counters"]
    assert (c["HIGH"]["confirmed"], c["LOW"]["confirmed"]) == (15, 12)


def test_event_fields():
    """sid = time of the first point's swing bar, origin = that bar; CONFIRMED / EXTENDED carry
    the new point's price, SWEEP / BREAK / EXPIRED the level line + τ on that bar."""
    cs = study.SCENARIOS["4th and 5th point extension"]
    m = _run(cs, Settings(modules=("lrl",)))
    r = m.lrl.high.hist[0]
    ev = [(e.bar, e.type, e.dir, e.sid, e.origin_bar, e.price) for e in m.events]
    assert ev == [(84, "LRL_CONFIRMED", 1, cs[50].time, 50, 112.5), (100, "LRL_EXTENDED", 1, cs[50].time, 50, 108.5),
                  (116, "LRL_EXTENDED", 1, cs[50].time, 50, 104.5),
                  (147, "LRL_EXPIRED", 1, cs[50].time, 50, r.y(147) + r.tau)]
    m = _run(study.SCENARIOS["sweep (wick through, close back)"], Settings(modules=("lrl",)))
    r = m.lrl.high.hist[0]
    assert m.events[-1].type == "LRL_SWEEP" and m.events[-1].price == r.y(93) + r.tau < 112


def test_bullish_events_carry_low_side_prices():
    from validation.candles import mirror
    cs = mirror(study.SCENARIOS["clean bearish LRL"], 0.0)
    e = _run(cs, Settings(modules=("lrl",))).events[0]
    assert (e.type, e.dir, e.price) == ("LRL_CONFIRMED", -1, -112.5)


@pytest.mark.parametrize("which", range(4), ids=["nq", "walk1", "walk2", "walk3"])
def test_phase1_and_phase2_are_identical_with_lrl_on(which):
    """DEF-LRL8: LRL reads bars only. Every Phase 1 / 2 event and all their state are
    byte-identical with the module on and off."""
    _, cs = _data()[which]
    off, on = _run(cs, Settings()), _run(cs)
    assert [e for e in on.events if not e.type.startswith("LRL_")] == off.events
    state = on.state()
    assert state.pop("lrl")["records"] and state == off.state()


def test_module_is_opt_in_and_does_not_change_case_definitions():
    """Default runs (baselines, parity) have no LRL; their serialised settings are unchanged."""
    assert "lrl" not in Settings().modules and "lrl" not in Settings().to_dict()
    assert IstModel(Settings()).lrl is None
    s = Settings.from_dict({"modules": ["liq", "lrl"], "lrl": {"gap": 20}})
    assert s.modules == ("liq", "lrl") and s.lrl.gap == 20 and s.to_dict()["lrl"]["gap"] == 20


def test_invariants_hold_on_nq_with_the_whole_model():
    run_checked(study.nq_candles(), ON)


def test_memory_drop_path():
    """DEF-LRL6 with tiny memories: ended records go first, every drop is logged once, all
    invariants hold (INV-LRL-09) and dropped ids never come back."""
    cs = random_walk(3000, 3, gap_prob=0.02)
    m = run_checked(cs, Settings(modules=("lrl",), lrl=LrlSettings(memory=2, cand_memory=2)), sweep_every=10)
    drops = [e for e in m.events if e.type == "LRL_DROPPED_MEMORY"]
    assert drops and len({(e.dir, e.sid) for e in drops}) == len(drops)
    for side in m.lrl.sides():
        assert len(side.records()) <= 2 and side.dropped == sum(e.dir == side.sign for e in drops)
