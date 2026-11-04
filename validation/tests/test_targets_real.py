"""Target universe on the real evidence (the four 1m segments of validation/studies/context.py): the Phase 2
adapter on every bar, the loaded-history boundary at several history starts, what the captures prove for
G-V1…G-V5, and the real golden cases, each labelled DETERMINISTIC (every input proven) or SUPPORTING (the facts
are exact, but one input waits for a gate). Publishes the TARGET UNIVERSE diagnostics of the report."""
import re
from collections import Counter
from datetime import datetime

import pytest

from validation import stats
from validation.models import targets as T
from validation.models.ist import IstModel
from validation.models.sessions import local
from validation.parity import CAPTURE_V043, CAPTURE_V044, CAPTURE_V070, CAPTURE_V071, CAPTURE_V080, CAPTURE_V091, capture
from validation.studies.context import segments
from validation.tests.test_targets import ALL, NY, p2_conflicts

pytestmark = [pytest.mark.targets, pytest.mark.section("targets")]
OFFSETS = (0, 97, 311, 640)


@pytest.fixture(scope="module")
def segs():
    return segments()


def run(seg, k=0, targets=None, snapshots=()):
    """The universe with the history starting at bar k of the segment, Module G fed TradingView's own D / W bars."""
    return T.run(seg.cs[k:], targets=targets, provider=T.tradingview_periods(seg.htf, seg.pdx), evidence=seg.htf,
                 snapshots=snapshots)


def bar_at(seg, when: str) -> int:
    return next(i for i, c in enumerate(seg.cs) if local(c.time, "America/New_York").strftime("%m-%d %H:%M") == when)


def ms(when: str, year=2026) -> int:
    return int(datetime.strptime(f"{year}-{when}", "%Y-%m-%d %H:%M").replace(tzinfo=NY).timestamp() * 1000)


def target(tu, prefix: str):
    xs = [x for x in tu.targets.values() if x.id.startswith(prefix)]
    assert len(xs) == 1, (prefix, [x.id for x in xs])
    return xs[0]


@pytest.fixture(scope="module")
def full(segs):
    return [run(s) for s in segs]


# ── Phase 2 adapter, determinism, isolation on the real data ──

def test_phase_2_adapter_has_zero_conflict_on_every_real_bar(segs):
    checks = 0
    for seg in segs:
        m = IstModel()
        tu = T.TargetUniverse(m)
        for c in seg.cs:
            m.step(c)
            tu.step()
            assert not p2_conflicts(m, tu)
            checks += sum(len(s.all_levels()) + sum(q.qual_bar is not None for q in s.eqs) for s in m.liq.sides())
    stats.RESULTS.setdefault("targets", {})["p2"] = {"bars": sum(len(s.cs) for s in segs), "checks": checks, "conflicts": 0}


def test_real_replay_is_deterministic_and_isolated(segs, full):
    seg = segs[3]
    m, tu, _ = full[3]
    _, again, _ = run(seg)
    assert again.snapshot() == tu.snapshot() and again.events == tu.events
    alone = IstModel()
    alone.levels.htf = T.tradingview_periods(seg.htf, seg.pdx)(alone.levels)      # the same Module G values, no universe
    alone.run(seg.cs)
    assert alone.canonical_events() == m.canonical_events() and alone.state() == m.state()


def test_session_extremes_equal_the_values_pine_logged(segs, full):
    """Bounded parity compares SESSION membership (start / end bars); the H / L travel only in the event text.
    Every session the universe holds equals Pine's own SESSION_END H / L."""
    caps = [(CAPTURE_V043, CAPTURE_V044), (CAPTURE_V080, CAPTURE_V070), (CAPTURE_V071,), (CAPTURE_V091,)]
    compared = 0
    for paths, (_, tu, _) in zip(caps, full):
        pine = {}
        for p in paths:
            for e in capture.parse(p.read_text(encoding="utf-8"))["events"]:
                if e["type"] == "SESSION_END":
                    name, hi, lo = re.search(r"· (.+) H ([\d.]+) L ([\d.]+)$", e["text"]).groups()
                    pine[(name, e["sid"])] = (float(hi), float(lo))
        for x in tu.targets.values():
            if x.type == "SESSION_HIGH":
                lo = next(y for y in tu.targets.values() if y.type == "SESSION_LOW" and y.source_id == x.source_id)
                assert pine[(x.meta["session"], x.meta["start_time"])] == (x.price, lo.price), x.id
                compared += 1
    assert compared >= 12
    stats.RESULTS.setdefault("targets", {})["sessions"] = compared


# ── the loaded-history boundary ──

def test_a_later_history_start_never_claims_more_than_the_full_history(segs):
    pre = Counter()
    for seg in segs:
        _, ref, _ = run(seg, targets=ALL)
        for k in OFFSETS[1:]:
            m, tu, _ = run(seg, k, targets=ALL)
            start = seg.cs[k].time
            assert not p2_conflicts(m, tu)
            for x in tu.targets.values():
                assert x.state != "AVAILABLE" or x.history == "OBSERVED", x.id
                if x.since < start:                                    # born before this loaded history
                    pre["born before the history"] += 1
                    pre["consumed, class unknown" if x.consumed and x.taken_kind == "UNKNOWN" else
                        "restored by evidence bars" if x.history == "OBSERVED" else "still UNVERIFIED"] += 1
                y = ref.targets.get(x.id)
                if y is None:
                    continue
                if x.state == "AVAILABLE":
                    assert y.state == "AVAILABLE", (k, x.id)
                if x.state == "TAKEN" and x.taken_kind in ("SWEEP", "BREAK"):
                    assert (y.taken_at, y.taken_kind) == (x.taken_at, x.taken_kind), (k, x.id)
                if x.source_class != "STRUCTURAL" and x.since >= start:     # born inside the shorter history
                    fact = lambda t: (t.exact_touch_at, t.exact_touches, t.taken_at, t.taken_kind, t.state, t.history)
                    assert fact(x) == fact(y), (k, x.id)
    stats.RESULTS.setdefault("targets", {})["excluded"] = dict(pre)


def test_period_levels_seeded_mid_period_wait_for_evidence(segs):
    """MNQ1! 11-02: the history starts 04:16, the day and the week began Sunday 18:00. The 4H bars Pine logged
    cover Fri 14:00 → Mon 02:00 at once; 02:00–04:16 is proven only when the 02:00 bar completes (06:00)."""
    seg = segs[3]
    i5, i6 = bar_at(seg, "11-02 05:59"), bar_at(seg, "11-02 06:00")
    _, tu, sn = run(seg, targets=ALL, snapshots={i5, i6})
    hist = lambda i: {x["id"]: x["history"] for x in sn[i]["targets"] if x["source_class"] in ("DAILY", "WEEKLY")}
    assert set(hist(i5).values()) == {"INCOMPLETE"} and set(hist(i6).values()) == {"OBSERVED"}
    _, bare, _ = T.run(seg.cs, targets=ALL, provider=T.tradingview_periods(seg.htf, seg.pdx))     # no evidence
    assert {x.history for x in bare.targets.values() if x.source_class in ("DAILY", "WEEKLY") and x.period_role == "HISTORICAL_PERIOD_LEVEL"} == {"INCOMPLETE"}


# ── what the captures prove for G-V1…G-V5 (the gates themselves stay PENDING: manual TradingView checks) ──

def test_g_v_evidence_in_the_captures(segs):
    seg = segs[3]
    d_bars = [h for s in segs for h in s.htf if h[0] == "D"]
    w_bars = [h for s in segs for h in s.htf if h[0] == "W"]
    f_bars = [h for s in segs for h in s.htf if h[0] == "240"]
    hhmm = lambda t: local(t, "America/New_York").strftime("%a %H:%M")
    # period identity: every D bar opens 18:00 ET (also after the 11-01 DST change), every W bar Sunday 18:00 ET
    assert {hhmm(h[1])[4:] for h in d_bars} == {"18:00"} and {hhmm(h[1]) for h in w_bars} == {"Sun 18:00"}
    assert {local(h[1], "America/New_York").hour for h in f_bars} <= {18, 22, 2, 6, 10, 14}
    assert any(hhmm(h[1]) == "Sun 18:00" and h[1] > ms("11-01 02:00") for h in d_bars)
    # exact price: Module G's own LEVEL_SET equals the D bar the HTF request received (MNQ1!, 11-02 18:00)
    cap = capture.parse(CAPTURE_V091.read_text(encoding="utf-8"))
    ls = {(e["time"], e["text"][-3:]): e["price"] for e in cap["events"] if e["type"] == "LEVEL_SET"}
    d = [h for h in seg.htf if h[0] == "D" and h[4] == ms("11-02 18:00")]
    assert len(d) == 1 and (ls[(ms("11-02 18:00"), "PDH")], ls[(ms("11-02 18:00"), "PDL")]) == (d[0][2], d[0][3])
    # first observable time: LEVEL_SET lands on the first bar of the new day (18:00 ET)
    nq = [capture.parse(p.read_text(encoding="utf-8")) for p in (CAPTURE_V043, CAPTURE_V044)]
    assert {hhmm(e["time"])[4:] for c in [cap] + nq for e in c["events"]
            if e["type"] == "LEVEL_SET" and e["text"][-3:] in T.PERIOD} == {"18:00"}
    # the D bar = its six 4H bars (Monday 11-02's session, every 4H bar logged by Pine)
    six = [h for h in seg.htf if h[0] == "240" and d[0][1] <= h[1] < d[0][1] + 24 * T.H]
    assert len(six) == 6 and (max(h[2] for h in six), min(h[3] for h in six)) == (d[0][2], d[0][3])
    # the W bar of the week of 10-26 equals the extremes of its D bars that were logged (Monday 10-26 is in no capture)
    week = [h for h in d_bars if ms("10-25 18:00") <= h[1] < ms("11-01 17:00")]
    w = [h for h in w_bars if h[1] == ms("10-25 18:00")][0]
    assert (max(h[2] for h in week), min(h[3] for h in week)) == (w[2], w[3]) and len({h[1] for h in week}) == 4
    # no future leakage: the provider only ever hands Module G a bar already known
    seen = []

    def spy(bars, sets):
        inner = T.tradingview_periods(bars, sets)

        def make(engine):
            f = inner(engine)

            def provide(kind, key, old):
                now = engine.prev.time
                seen.append(all(b[4] <= now for b in bars if b[0] == kind and (b[2], b[3]) == (f(kind, key, old) or (None, None))))
                return f(kind, key, old)
            return provide
        return make
    T.run(seg.cs, provider=spy(seg.htf, seg.pdx), evidence=seg.htf)
    assert seen and all(seen)
    stats.RESULTS.setdefault("targets", {})["gv"] = {
        "level_set_vs_d_bar": "1 roll, PDH and PDL equal (MNQ1! 11-02 18:00)",
        "d_open": f"{len({h[1] for h in d_bars})} D bars, all 18:00 ET (one after DST)",
        "w_open": f"{len({h[1] for h in w_bars})} W bars, all Sunday 18:00 ET",
        "four_hour_day": "Monday 11-02: 6 × 4H = the D bar",
        "week": "W of 10-26 = its 4 logged D bars (Monday unseen)"}


# ── real golden cases ──

GOLDEN = [
    ("TU-G1", "SUPPORTING", "PDH = NY PM H = BSL, one exact-tick pool (NQ1! 10-27 19:59); PDH waits for G-V"),
    ("TU-G2", "SUPPORTING", "PDL = PWL, one exact-tick pool (MNQ1! 11-02 09:29); both wait for G-V"),
    ("TU-G3", "DETERMINISTIC", "PWL of the week of 10-26 is never proven: Monday 10-26 is in no capture (HISTORY_INCOMPLETE)"),
    ("TU-G4", "SUPPORTING", "PDL 30591.25 SWEEP at 10-14 08:35, the first take observed; PDL waits for G-V"),
    ("TU-G5", "SUPPORTING", "PDH 29881.25 BREAK at 10-27 21:41 (in Asia), together with NY PM H; PDH waits for G-V"),
    ("TU-G6", "SUPPORTING", "London L 28882 SWEEP at 10-30 05:47; the session source waits for T19–T22"),
    ("TU-G7", "SUPPORTING", "NY AM L 28634.5 SWEEP at 11-02 12:10; the session source waits for T19–T22"),
    ("TU-G8", "SUPPORTING", "PWH 30114 of the week of 10-26 consumed before the history: the logged D bar of 10-27 went above it"),
    ("TU-G9", "DETERMINISTIC", "exact touch ≠ take on real bars: a target touched exactly and taken later (or never)"),
    ("TU-G10", "DETERMINISTIC", "identity = the source period: Monday 11-02's PDL is Friday 10-30's low, PWL the week-44 low"),
]


@pytest.mark.parametrize("case", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_real_golden_case(case, segs, full):
    cid = case[0]
    if cid == "TU-G1":
        i = bar_at(segs[0], "10-27 19:59")
        _, _, sn = run(segs[0], snapshots={i})
        pool = [p for p in sn[i]["pools"] if p["price_ticks"] == 119525][0]
        assert [m.split(":")[0] for m in pool["members"]] == ["BSL", "PDH", "SESSION_HIGH"] and pool["side"] == 1
        assert next(x for x in sn[i]["targets"] if x["id"].startswith("PDH:"))["verification"] == ("SOURCE_PENDING_GV",)
    elif cid == "TU-G2":
        i = bar_at(segs[3], "11-02 09:29")
        _, _, sn = run(segs[3], snapshots={i})
        assert [p["members"] for p in sn[i]["pools"] if p["price_ticks"] == 112929] == [["PDL:D2026-10-30:112929", "PWL:W2026-44:112929"]]
    elif cid == "TU-G3":
        _, tu, _ = run(segs[1], targets=ALL)
        x = target(tu, "PWL:W2026-43:")
        assert x.price == 28986.25 and x.since == ms("10-25 18:00") and x.history == "INCOMPLETE"
        assert (x.state, x.taken_kind) == ("TAKEN", "UNKNOWN")        # taken later; its first take may lie unseen
        assert target(full[1][1], "PWL:W2026-43:").state == "UNVERIFIED"
    elif cid == "TU-G4":
        x = target(full[2][1], "PDL:D2026-10-13:")
        assert (x.price, x.taken_at, x.taken_kind, x.history, x.state) == (30591.25, ms("10-14 08:35"), "SWEEP", "OBSERVED", "UNVERIFIED")
    elif cid == "TU-G5":
        tu = full[0][1]
        x, s = target(tu, "PDH:D2026-10-27:"), target(tu, "SESSION_HIGH:NY PM@1330-1600:")
        assert (x.taken_at, x.taken_kind, s.taken_at, s.taken_kind) == (ms("10-27 21:41"), "BREAK", ms("10-27 21:41"), "BREAK")
        assert (x.state, s.state) == ("UNVERIFIED", "UNVERIFIED")
    elif cid == "TU-G6":
        x = target(full[1][1], "SESSION_LOW:London@0200-0500:")
        assert (x.price, x.taken_at, x.taken_kind, x.state, x.verification) == \
            (28882.0, ms("10-30 05:47"), "SWEEP", "UNVERIFIED", ("SOURCE_PENDING_T19_T22",))
    elif cid == "TU-G7":
        x = target(full[3][1], "SESSION_LOW:NY AM@0930-1200:")
        assert (x.price, x.taken_at, x.taken_kind, x.state) == (28634.5, ms("11-02 12:10"), "SWEEP", "UNVERIFIED")
    elif cid == "TU-G10":
        tu = full[3][1]
        pdl, pwl = target(tu, "PDL:D2026-10-30:"), target(tu, "PWL:W2026-44:")
        assert (pdl.meta, pwl.meta) == ({"source_period": "D2026-10-30", "published_in": "D2026-11-02"},
                                        {"source_period": "W2026-44", "published_in": "W2026-45"})
        assert target(tu, "PDL:D2026-11-02:").meta["published_in"] == "D2026-11-03"   # Monday's own low, from the 18:00 roll
    elif cid == "TU-G8":
        x = target(full[1][1], "PWH:W2026-43:")
        assert (x.price, x.taken_before, x.taken_at, x.taken_kind) == (30114.0, ms("10-27 18:00"), None, "UNKNOWN")
    elif cid == "TU-G9":
        touched = [(seg, x) for seg, (_, tu, _) in zip(segs, full) for x in tu.targets.values() if x.exact_touch_at is not None]
        assert touched and all(x.taken_at is None or x.taken_at > x.exact_touch_at for _, x in touched)
        for seg, x in touched:                                   # the touching bar is exactly at the price, never beyond
            c = next(c for c in seg.cs if c.time == x.exact_touch_at)
            assert (c.high if x.side > 0 else c.low) == x.price
    stats.RESULTS.setdefault("targets", {}).setdefault("golden", {})[cid] = case[1:]


def test_report_diagnostics(segs, full):
    rows = []
    for seg, (_, tu, _) in zip(segs, full):
        by = Counter((x.source_class, x.state) for x in tu.targets.values())
        ev = Counter(e[1] for e in tu.events)
        kinds = Counter(x.taken_kind for x in tu.targets.values() if x.consumed)
        pools = {p["id"] for p in tu.pools()}
        rows.append({"segment": seg.name, "targets": len(tu.targets), "by": dict(sorted(by.items())),
                     "touch": ev["TARGET_EXACT_TOUCH"], "sweep": kinds["SWEEP"], "break": kinds["BREAK"], "unknown": kinds["UNKNOWN"],
                     "pools_end": len(pools), "pending": sum(any(v.startswith("SOURCE_PENDING") for v in x.verification) for x in tu.targets.values()),
                     "incomplete": sum(x.history == "INCOMPLETE" for x in tu.targets.values())})
    assert sum(r["targets"] for r in rows) > 0
    stats.RESULTS.setdefault("targets", {})["segments"] = rows
