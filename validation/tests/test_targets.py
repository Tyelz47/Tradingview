"""Target universe oracle (validation/models/targets.py, docs/context/TARGET_UNIVERSE_ORACLE.md) on synthetic
data: identity, no future leakage, TOUCH ≠ TAKEN, SWEEP / BREAK mirror, the Phase 2 adapter, the loaded-history
boundary, exact-tick composite pools, determinism and isolation. The real evidence is test_targets_real.py."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from validation.candles import mirror, random_walk
from validation.models import targets as T
from validation.models.eq import CLS_NAME
from validation.models.ist import IstModel
from validation.models.types import Candle, Settings

pytestmark = [pytest.mark.targets, pytest.mark.section("targets")]
NY = ZoneInfo("America/New_York")
ALL = T.TargetSettings(validated=frozenset({"DAILY", "WEEKLY", "SESSION", "STRUCTURAL"}))
TU_MODULES = Settings(modules=("levels", "sessions", "liq"))


def ms(y, mo, d, h, mi):
    return int(datetime(y, mo, d, h, mi, tzinfo=NY).timestamp() * 1000)


def bars(start, specials, n, base=100.0):
    """n flat 1m bars from `start` (o = c = base, h = base + 0.5, l = base − 0.5), except {minute offset: (o, h, l, c)}."""
    return [Candle(start + 60_000 * i, *(specials.get(i) or (base, base + 0.5, base - 0.5, base))) for i in range(n)]


def by_type(tu, typ):
    return [x for x in tu.targets.values() if x.type == typ]


def london(extra=None):
    """London 02:00–05:00 with H 105 at 03:00 and L 95 at 04:00, then: 05:05 exact touch of 105, 05:10 one tick
    beyond with the close back (SWEEP), 05:15 exact touch of 95, 05:20 beyond with the close beyond (BREAK)."""
    t0 = ms(2026, 10, 27, 1, 55)
    sp = {65: (100, 105, 99.5, 100), 125: (100, 100.5, 95, 100),
          190: (100, 105, 99.5, 100), 195: (104, 105.25, 103.5, 104), 200: (100, 100.5, 95, 99), 205: (95, 95.5, 94.75, 94.5)}
    sp.update(extra or {})
    return bars(t0, sp, 230)


@pytest.fixture(scope="module")
def walks():
    return [random_walk(4000, seed) for seed in (1, 2, 3)]


# ── lifecycle: TOUCH ≠ TAKEN, SWEEP / BREAK, mirror, no future leakage ──

def test_touch_is_not_a_take_and_the_class_is_by_the_taking_close():
    cs = london()
    m, tu, snaps = T.run(cs, TU_MODULES, snapshots={184, 185, 194, 195})
    hi, lo = by_type(tu, "SESSION_HIGH")[0], by_type(tu, "SESSION_LOW")[0]
    t = lambda i: cs[i].time
    assert (hi.price, hi.confirmed_at, hi.first_observable_at) == (105, t(185), t(185))
    assert (hi.touch_at, hi.touches, hi.taken_at, hi.taken_kind, hi.state) == (t(190), 1, t(195), "SWEEP", "TAKEN")
    assert (lo.touch_at, lo.touches, lo.taken_at, lo.taken_kind, lo.state) == (t(200), 1, t(205), "BREAK", "TAKEN")
    assert hi.id == f"SESSION_HIGH:London@0200-0500:{t(5)}:420" and hi.source_id == f"F:London@0200-0500:{t(5)}"
    assert not any(x["source_class"] == "SESSION" for x in snaps[184]["targets"])        # absent before the session ends
    state = lambda i: next(x["state"] for x in snaps[i]["targets"] if x["id"] == hi.id)
    assert (state(185), state(194), state(195)) == ("AVAILABLE", "AVAILABLE", "TAKEN")  # the touch leaves it AVAILABLE
    kinds = [(e[1], e[3]) for e in tu.events if e[2] == hi.id]
    assert kinds == [("TARGET_CREATED", f"F:London@0200-0500:{t(5)} · AVAILABLE"), ("TARGET_TOUCH", ""),
                     ("TARGET_TAKEN", "SWEEP"), ("TARGET_STATE", "AVAILABLE → TAKEN")]


def test_mirror_swaps_high_and_low_and_keeps_every_fact():
    cs = london()
    _, a, _ = T.run(cs, TU_MODULES)
    _, b, _ = T.run(mirror(cs, 100.0), TU_MODULES)
    fact = lambda x: (x.source_id.split(":")[0], x.confirmed_at, x.touch_at, x.taken_at, x.taken_kind, x.state, x.touches)
    for x in a.targets.values():
        twin = [y for y in b.targets.values() if y.type == T.MIRROR[x.type] and y.price == 200 - x.price
                and y.confirmed_at == x.confirmed_at]
        assert len(twin) == 1 and fact(twin[0]) == fact(x), x.id


def test_a_target_is_taken_once_and_taken_is_terminal():
    cs = london({215: (100, 106, 99, 100)})                     # trades through 105 again after the take
    _, tu, _ = T.run(cs, TU_MODULES)
    hi = by_type(tu, "SESSION_HIGH")[0]
    assert hi.taken_at == cs[195].time and hi.state == "TAKEN"
    assert sum(e[1] == "TARGET_TAKEN" and e[2] == hi.id for e in tu.events) == 1


# ── period levels: the source gate and the loaded-history boundary ──

def fixed(pdh, pdl, pwh=130.0, pwl=70.0):
    return lambda engine: (lambda kind, key, old: (pdh, pdl) if kind == "D" else (pwh, pwl))


def test_period_level_is_unverified_while_its_source_waits_for_g_v():
    cs = bars(ms(2026, 10, 27, 8, 0), {}, 40)
    _, tu, _ = T.run(cs, TU_MODULES, provider=fixed(110.0, 90.0))
    pdh = by_type(tu, "PDH")[0]
    assert pdh.id == "PDH:D2026-10-27:440" and pdh.source_id == "G:PDH:D2026-10-27"
    assert pdh.since == ms(2026, 10, 26, 18, 0) and pdh.period_role == "CURRENT"
    assert pdh.state == "UNVERIFIED" and pdh.verification == ("SOURCE_PENDING_GV", "HISTORY_INCOMPLETE")


def test_a_level_born_before_the_loaded_history_is_never_available_by_assumption():
    cs = bars(ms(2026, 10, 27, 8, 0), {}, 150)
    _, tu, _ = T.run(cs, TU_MODULES, targets=ALL, provider=fixed(110.0, 90.0))
    assert {x.type: (x.state, x.history) for x in tu.targets.values() if x.source_class != "SESSION"} == \
        {t: ("UNVERIFIED", "INCOMPLETE") for t in ("PDH", "PDL", "PWH", "PWL")}


def test_completed_evidence_bars_restore_the_unseen_history_from_the_bar_they_are_known():
    t0 = ms(2026, 10, 27, 8, 0)
    four = lambda h, hi, lo, known: ("240", ms(2026, 10, 26 if h >= 18 else 27, h, 0), hi, lo, known)
    ev = [four(18, 101, 99, t0), four(22, 101, 99, t0), four(2, 101, 99, t0), four(6, 101, 99, ms(2026, 10, 27, 10, 0))]
    cs = bars(t0, {}, 150)
    _, tu, snaps = T.run(cs, TU_MODULES, targets=ALL, provider=fixed(110.0, 90.0), evidence=ev, snapshots={119, 120})
    st = lambda i: next(x["state"] for x in snaps[i]["targets"] if x["type"] == "PDH")
    assert (st(119), st(120)) == ("UNVERIFIED", "AVAILABLE")      # 06:00–10:00 is proven only when that bar completes
    pwh = by_type(tu, "PWH")[0]
    assert pwh.state == "UNVERIFIED" and pwh.history == "INCOMPLETE"   # the week started Sunday 18:00: still unseen
    beyond = [four(18, 101, 99, t0), four(22, 111, 99, t0)]           # 22:00 went above 110 before anything was seen
    _, tu2, _ = T.run(cs, TU_MODULES, targets=ALL, provider=fixed(110.0, 90.0), evidence=beyond)
    pdh = by_type(tu2, "PDH")[0]
    assert (pdh.state, pdh.taken_kind, pdh.taken_before, pdh.taken_at) == ("TAKEN", "UNKNOWN", ms(2026, 10, 26, 22, 0), None)


def test_an_observed_roll_is_fully_observed_and_the_old_value_becomes_historical():
    cs = bars(ms(2026, 10, 27, 17, 30), {45: (100, 110, 99.5, 109.5)}, 60)   # 18:15: through 108 and 109, close above 109
    vals = iter([(108.0, 92.0), (109.0, 91.0)])
    seq = {}
    prov = lambda engine: (lambda kind, key, old: seq.setdefault((kind, key), next(vals)) if kind == "D" else (130.0, 70.0))
    _, tu, _ = T.run(cs, TU_MODULES, targets=ALL, provider=prov)
    old, new = sorted(by_type(tu, "PDH"), key=lambda x: x.confirmed_at)
    assert (old.period_role, old.age_periods, new.period_role, new.age_periods) == ("HISTORICAL_PERIOD_LEVEL", 1, "CURRENT", 0)
    assert new.id == "PDH:D2026-10-28:436" and new.since == new.confirmed_at == ms(2026, 10, 27, 18, 0)
    assert (new.history, new.touch_at, new.taken_at, new.taken_kind) == ("OBSERVED", None, cs[45].time, "BREAK")
    assert old.taken_at == cs[45].time and old.taken_kind == "UNKNOWN"   # born before the history: first take unseen
    _, gated, _ = T.run(cs, TU_MODULES, provider=lambda e: (lambda kind, key, old: (109.0, 91.0) if kind == "D" else (130.0, 70.0)))
    g = [x for x in by_type(gated, "PDH") if x.period_role == "CURRENT"][0]
    assert (g.state, g.taken_kind) == ("UNVERIFIED", "BREAK")          # facts kept; never TAKEN / AVAILABLE before G-V


# ── exact-tick composite pools: no tolerance ──

def test_exact_tick_pool_keeps_its_members_and_one_tick_apart_is_no_pool():
    cs = london()[:189]
    _, same, _ = T.run(cs, TU_MODULES, provider=fixed(105.0, 95.0))
    pool = [p for p in same.pools() if p["price_ticks"] == 380][0]
    ssl = [x.id for x in by_type(same, "SSL") if x.price_ticks == 380]       # the 04:00 low is also a Phase 2 swing
    assert pool["side"] == -1 and len(ssl) == 1
    assert pool["members"] == sorted(["PDL:D2026-10-27:380", by_type(same, "SESSION_LOW")[0].id, *ssl])
    _, apart, _ = T.run(cs, TU_MODULES, provider=fixed(105.0, 95.25))
    assert [p["members"] for p in apart.pools() if p["price_ticks"] == 380] == [sorted([by_type(apart, "SESSION_LOW")[0].id, *ssl])]
    assert not any("PDL:D2026-10-27:381" in p["members"] for p in apart.pools())   # one tick apart: no pool, no radius


# ── the Phase 2 adapter: zero semantic conflict ──

def p2_conflicts(m, tu) -> list[str]:
    bad, ids = [], set()
    for side in m.liq.sides():
        for x in side.all_levels():
            t = tu.targets.get(f"{side.name}:{x.id}:{round(x.price / 0.25)}")
            ids.add(t and t.id)
            want = ("AVAILABLE" if x.taken_bar is None else "TAKEN", x.taken_time, CLS_NAME[x.cls], x.touches)
            if t is None or (t.state, t.taken_at, t.taken_kind, t.touches) != want:
                bad.append(f"{side.name} {x.id}: {t and (t.state, t.taken_at, t.taken_kind, t.touches)} vs {want}")
        for cl in side.eqs:
            if cl.qual_bar is None:
                continue
            t = tu.targets.get(f"{side.eq_name}:{cl.id}:{round(cl.bound / 0.25)}")
            ids.add(t and t.id)
            want = ("AVAILABLE" if cl.taken_bar is None else "TAKEN", cl.taken_time, CLS_NAME[cl.cls])
            if t is None or (t.state, t.taken_at, t.taken_kind) != want:
                bad.append(f"{side.eq_name} {cl.id}: {t and (t.state, t.taken_at, t.taken_kind)} vs {want}")
    for t in tu.targets.values():
        if t.source_class == "STRUCTURAL" and t.id not in ids and t.state != "INVALID":
            bad.append(f"{t.id}: Phase 2 released it, the target is {t.state}")
    return bad


def test_phase_2_targets_mirror_the_frozen_records_on_every_bar(walks):
    for cs in walks:
        m = IstModel(TU_MODULES)
        tu = T.TargetUniverse(m)
        for c in cs:
            m.step(c)
            tu.step()
            assert not p2_conflicts(m, tu)
        assert any(t.state == "INVALID" for t in tu.targets.values())    # memory releases happened and were mirrored


def test_the_strict_beyond_rule_of_observed_targets_is_phase_2_s_own_rule(walks):
    """Applied by hand to every Phase 2 level, the observed-target rule gives Phase 2's own take bar, class and touches."""
    m = IstModel(TU_MODULES).run(walks[0])
    cs = m.candles
    for side in m.liq.sides():
        for x in side.all_levels():
            p, take, touches = x.price, None, 0
            for j in range(x.confirm_bar + 1, len(cs)):
                if T._beyond(side.sign, cs[j].high, cs[j].low, p):
                    take = j
                    break
                touches += (cs[j].high if side.sign > 0 else cs[j].low) == p
            assert (take, touches) == (x.taken_bar, x.touches)
            if take is not None:
                out = cs[take].close > p if side.sign > 0 else cs[take].close < p
                assert CLS_NAME[x.cls] == ("BREAK" if out else "SWEEP")


# ── determinism, prefix invariance, order independence, isolation ──

def test_fresh_replay_prefix_and_order_are_deterministic(walks):
    cs = walks[1]
    pts = {700, 1777, 3999}
    m1, a, sa = T.run(cs, TU_MODULES, snapshots=pts)
    _, b, sb = T.run(cs, TU_MODULES, snapshots=pts, order=("structure", "sessions", "periods"))
    assert sa == sb and a.events == b.events                     # twice, and in another registration order
    for n in pts:
        _, p, sp = T.run(cs[:n + 1], TU_MODULES, snapshots={n})
        assert sp[n] == sa[n]                                       # appending the future changes nothing up to n
        assert p.events == [e for e in a.events if e[0] <= cs[n].time]


def test_identities_are_unique_and_stable(walks):
    for cs in walks:
        _, tu, _ = T.run(cs, TU_MODULES)
        sources = [(x.type, x.source_id) for x in tu.targets.values()]
        assert len(sources) == len(set(sources)) == len(tu.targets)
        assert all(x.id.split(":")[-1] == str(x.price_ticks) and x.price_ticks * 0.25 == x.price for x in tu.targets.values())


def test_the_universe_never_changes_a_frozen_module(walks):
    cs = walks[2]
    alone = IstModel(TU_MODULES).run(cs)
    with_tu, _, _ = T.run(cs, TU_MODULES)
    assert with_tu.canonical_events() == alone.canonical_events() and with_tu.state() == alone.state()


def test_externality_is_categorical_and_relative_to_closed_ranges_only():
    cs = london()[:189]
    _, tu, _ = T.run(cs, TU_MODULES, provider=fixed(105.0, 95.0))
    rg = tu.ranges()
    assert rg == {"PREVIOUS_DAY": (380, 420), "PREVIOUS_WEEK": (280, 520), "SESSION:London": (380, 420)}
    hi = by_type(tu, "SESSION_HIGH")[0]
    assert tu.externality(hi) == {"PREVIOUS_DAY": "AT_HIGH", "PREVIOUS_WEEK": "INSIDE", "SESSION:London": "AT_HIGH"}
    assert set(v for x in tu.targets.values() for v in tu.externality(x).values()) <= {"ABOVE", "AT_HIGH", "INSIDE", "AT_LOW", "BELOW"}
