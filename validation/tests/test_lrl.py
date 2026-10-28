"""LRL detection oracle (validation/models/lrl.py, docs/LRL.md DEF-LRL1…LRL8): the approved
definition, its events, its coexistence with Phase 1 / Phase 2, and its agreement with
the independent study engine (validation/studies/lrl.py) that the user approved."""
import pytest

from validation.candles import mirror, random_walk
from validation.invariants import run_checked
from validation.models.ist import IstModel
from validation.models.types import MODULES, Candle, LrlSettings, Settings
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
    """DEF-LRL1…6 as approved on 2026-10-28, with the LRL_DRIFT class (user correction, same
    day); changing one is a definition change."""
    assert LrlSettings() == LrlSettings(left=3, right=2, tol_k=0.5, gap=30, sep_k=1.0, drop_k=2.0, tra_len=14,
                                        cand_memory=25, memory=50)
    r = study.APPROVED
    assert (r.left, r.right, r.tol, r.gmax, r.sep, r.drop, r.geometry, r.drift) == (
        3, 2, ("tr", 0.5), 30, 1.0, 2.0, "chord", True)


def test_event_names_prepared_for_pine():
    """The exact LRL event names the future Pine f_evName must emit. Until then they are
    oracle-only, and ST-14 (Pine names = oracle names) excludes exactly them."""
    from validation.models.events import LRL_TERMINAL, ORACLE_ONLY, TYPES
    names = {"LRL_CONFIRMED", "LRL_EXTENDED", "LRL_SWEEP", "LRL_BREAK", "LRL_DRIFT", "LRL_EXPIRED", "LRL_DROPPED_MEMORY"}
    assert {t for t in TYPES if t.startswith("LRL_")} == ORACLE_ONLY == names
    assert set(LRL_TERMINAL) == {"LRL_DRIFT", "LRL_SWEEP", "LRL_BREAK", "LRL_EXPIRED"}


@pytest.mark.parametrize("name", sorted(study.SCENARIOS))
def test_oracle_equals_the_approved_study_engine_on_scenarios(name):
    cs = study.SCENARIOS[name]
    want = sorted((b, k, s, a) for b, k, s, a, _ in study.events(study.both(cs, study.APPROVED, {})))
    assert _short(_run(cs, Settings(modules=("lrl",)))) == want


@pytest.mark.parametrize("which", range(4), ids=["nq", "walk1", "walk2", "walk3"])
def test_oracle_equals_the_approved_study_engine_on_data(which):
    name, cs = _data()[which]
    want = sorted((b, k, s, a) for b, k, s, a, _ in study.events(study.both(cs, study.APPROVED, {})))
    assert _short(_run(cs)) == want and want


@pytest.mark.parametrize("which", range(4), ids=["nq", "walk1", "walk2", "walk3"])
def test_drift_only_relabels_crossings(which):
    """LRL_DRIFT changes no detection: same bars, sides and anchors as the reviewed study
    (where every crossing was SWEEP / BREAK); each DRIFT was a SWEEP or BREAK there."""
    _, cs = _data()[which]
    old = sorted((b, k, s, a) for b, k, s, a, _ in study.events(study.both(cs, study.RECOMMENDED, {})))
    new = _short(_run(cs, Settings(modules=("lrl",))))
    assert [(b, s, a) for b, _, s, a in old] == [(b, s, a) for b, _, s, a in new]
    assert all(k == n or (n == "LRL_DRIFT" and k in ("LRL_SWEEP", "LRL_BREAK")) for (_, k, _, _), (_, n, _, _) in zip(old, new))


def test_nq_numbers_of_the_approved_study():
    """27 LRLs (15 on highs, 12 on lows) on the merged NQ captures; their terminations with
    LRL_DRIFT: 8 DRIFT · 9 SWEEP · 10 BREAK · 0 EXPIRED (high 5 · 3 · 7 · 0, low 3 · 6 · 3 · 0)."""
    m = _run(study.nq_candles())
    c = m.lrl.state()["counters"]
    assert (c["HIGH"]["confirmed"], c["LOW"]["confirmed"]) == (15, 12)
    assert [(c[k]["drift"], c[k]["sweep"], c[k]["break"], c[k]["expired"]) for k in ("HIGH", "LOW")] == [
        (5, 3, 7, 0), (3, 6, 3, 0)]


# ── terminal classification: DRIFT · SWEEP · BREAK (docs/LRL.md DEF-LRL5) ──
LRL_ONLY = Settings(modules=("lrl",))
BEAR = [(50, 120), (58, 108), (66, 116), (74, 104), (82, 112)]   # highs 120.5 · 116.5 · 112.5, line −0.25/bar, τ ≈ 1.018
EXACT = [(50, 112), (58, 104), (66, 108), (74, 100), (82, 104)]  # highs 112.5 · 108.5 · 104.5, τ = EQ tol = 1.0 exactly
STEEP = [(50, 140), (56, 122), (62, 128), (68, 110), (74, 116)]  # highs 140.5 · 128.5 · 116.5, line −1/bar, τ ≈ 1.732


def _ends(cs):
    """(bar, event, dir) of every LRL event, and the model."""
    m = _run(cs, LRL_ONLY)
    return [(e.bar, e.type, e.dir) for e in m.events], m


def _cases():
    drift = study.zigzag(BEAR + [(92, 100), (96, 106.5)])          # price parks at 107 (high); the line descends into it
    return {
        "drift": (drift, [(84, "LRL_CONFIRMED"), (109, "LRL_DRIFT")]),
        "sweep": (study.SCENARIOS["sweep (wick through, close back)"], [(84, "LRL_CONFIRMED"), (93, "LRL_SWEEP")]),
        "break": (study.SCENARIOS["break (close beyond)"], [(84, "LRL_CONFIRMED"), (93, "LRL_BREAK")]),
    }


@pytest.mark.parametrize("bullish", [False, True], ids=["bearish", "bullish"])
@pytest.mark.parametrize("kind", ["drift", "sweep", "break"])
def test_terminal_classification(kind, bullish):
    """1–6: bearish and bullish DRIFT, genuine SWEEP and genuine BREAK. The bullish case is the
    mirror (p → −p): boundary y − τ, previous boundary y(t−1) − τ, low / close comparisons."""
    cs, want = _cases()[kind]
    g = -1 if bullish else 1
    ev, m = _ends(mirror(cs, 0.0) if bullish else cs)
    assert ev == [(b, k, g) for b, k in want]
    side = m.lrl.low if bullish else m.lrl.high
    r, (bar, _) = side.hist[0], want[-1]
    now, prev = r.y(bar) + r.tau, r.y(bar - 1) + r.tau              # side coordinates (lows negated)
    assert m.events[-1].price == g * now
    if bullish:                                                       # real prices: line y − τ, lows and closes
        low, close = m.candles[bar].low, m.candles[bar].close
        assert low < -now - m.lrl.eps and (kind == "drift") == (low >= -prev - m.lrl.eps)
        assert kind == "drift" or (kind == "break") == (close < -now - m.lrl.eps)


@pytest.mark.parametrize("high, want", [(103.5, "LRL_DRIFT"), (103.75, "LRL_SWEEP"), (103.25, None)],
                         ids=["at-previous-boundary", "one-tick-beyond-it", "at-the-boundary"])
def test_equality_at_the_previous_boundary(high, want):
    """7: τ = 1.0 and the line on the tick grid, so boundaries are exact: bar 91 has boundary
    103.25 and previous boundary 103.5. A high exactly AT the previous boundary is DRIFT
    (≤ previous + ε); one tick beyond it is price-driven; exactly at the boundary is no cross
    (that bar is a touch on the line, so it becomes the 4th point when confirmed on bar 93)."""
    ev, m = _ends(study.zigzag(EXACT + [(90, 96)], extra=[(96, high, 95.5, 96)]))
    r = m.lrl.high.hist[0]
    assert ev[0] == (84, "LRL_CONFIRMED", 1)
    if want:
        assert r.tau == 1.0 and (r.y(91) + r.tau, r.y(90) + r.tau) == (103.25, 103.5) and len(r.xs) == 3
        assert ev[1:] == [(91, want, 1)]
    else:
        assert ev[1] == (93, "LRL_EXTENDED", 1) and r.xs[3] == 91 and r.touches >= 1


@pytest.mark.parametrize("high, close, want", [(112.0, 100.5, "LRL_DRIFT"), (112.5, 100.5, "LRL_SWEEP"),
                                               (113.0, 112.0, "LRL_BREAK")])
def test_steep_one_bar_projection(high, close, want):
    """8: a steep line (−1 point per bar) moves its boundary 1 point in one bar: on bar 81 it is
    ≈ 111.23, the previous ≈ 112.23. A high inside that band is DRIFT; beyond it, price-driven."""
    ev, m = _ends(study.zigzag(STEEP + [(80, 100)], extra=[(100, high, 99.5, close)]))
    r = m.lrl.high.hist[0]
    assert r.y(80) - r.y(81) == 1.0 and r.y(81) + r.tau < high
    assert ev == [(76, "LRL_CONFIRMED", 1), (81, want, 1)]


def test_extension_immediately_before_a_potential_drift():
    """9: a 4th point (108.25, 0.75 below the line) joins on bar 98 and steepens the chord.
    The drift is judged with the NEW geometry from bar 99 on: DRIFT on bar 100 (the old
    chord would have reached the parked price only on bar 104). Bar 98 itself was advanced
    with the old geometry, before the extension."""
    cs = study.zigzag(BEAR + [(92, 100), (96, 107.75)])
    ev, m = _ends(cs)
    assert ev == [(84, "LRL_CONFIRMED", 1), (98, "LRL_EXTENDED", 1), (100, "LRL_DRIFT", 1)]
    r = m.lrl.high.hist[0]
    old = lambda x: 120.5 - 0.25 * (x - 50) + r.tau
    assert len(r.xs) == 4 and r.slope < -0.25
    assert old(100) > cs[100].high and old(103) > cs[103].high > old(104)      # the old chord: no cross before 104


def test_drift_consumes_pivots():
    """10: like SWEEP / BREAK, a DRIFT spends its pivots (never reused); EXPIRED does not."""
    _, m = _ends(_cases()["drift"][0])
    side, r = m.lrl.high, m.lrl.high.hist[0]
    assert r.end == "DRIFT" and set(r.xs) <= side.spent and not side.members
    assert all(not set(k.xs) & set(r.xs) for k in side.cands)
    _, m = _ends(study.SCENARIOS["clean bearish LRL"])
    r = m.lrl.high.hist[0]
    assert r.end == "EXPIRED" and not set(r.xs) & m.lrl.high.spent


def test_terminal_event_is_never_relabelled():
    """11: after the DRIFT, bars trade far through the line and close beyond it (a BREAK if
    the LRL were still active): nothing more is emitted, the record stays DRIFT. The
    detector INV-LRL-10 (tests/test_invariants.py) fires if a second terminal event appears."""
    late = study.zigzag(BEAR + [(92, 100), (96, 106.5)], tail=20)                 # bars 0…116, DRIFT on 109
    late += [Candle(late[-1].time + 60_000 * (i + 1), 107, 130, 106.5, 129) for i in range(5)]
    ev, m = _ends(late)
    assert ev == [(84, "LRL_CONFIRMED", 1), (109, "LRL_DRIFT", 1)] and len(late) == 122
    assert m.lrl.high.hist[0].end == "DRIFT" and m.lrl.high.hist[0].end_bar == 109
    run_checked(late, LRL_ONLY)


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
