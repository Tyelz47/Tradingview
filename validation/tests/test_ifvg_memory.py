"""IFVG memory (docs/IFVG.md DEF-IFVG8, revised and approved 2026-11-02, IST v0.9.1-dev).

IFVG_MEM = 50 is the retention target per IFVG side, not a licence to drop logical state:
* an ACTIVE IFVG is never dropped (no IFVG_DROPPED_MEMORY for it);
* while a side holds more than 50 records, its oldest INVALIDATED record leaves (inversion order);
* a side whose records are all ACTIVE keeps them all (temporary overflow);
* one routine compacts after the bar's ends (bullish side, then bearish) and after each inversion.

Every scenario runs under the invariant monitor (INV-IFVG-07 cap / order, INV-IFVG-09 ACTIVE kept) and
with Pine's formulation (IfvgPine = the oracle, record for record and event for event), on both sides.

stair(n) makes n bullish Phase 1 FVGs [q + 1, q + 3] (q = 20000 − 20k), each inverted by the next
candle's drop: n bearish IFVGs that stay ACTIVE, since price only falls. `ends` appends, after motif k,
a candle that closes one point above that IFVG's top (its retest, CE, full and end on one bar)."""
import pytest

from validation.candles import from_rows, mirror, random_walk
from validation.invariants import run_checked
from validation.models.events import EventLog
from validation.models.fvg import FvgEngine
from validation.models.ifvg import Ifvg, IfvgEngine, IfvgPine, PineIfvg
from validation.models.types import NQ_TICK, FvgSettings, IfvgSettings, Settings
from validation.tests.test_ifvg_pine import BIG, run, same

pytestmark = [pytest.mark.ifvg, pytest.mark.section("ifvg")]
DROP, INV, TOUCH, END = "IFVG_DROPPED_MEMORY", "IFVG_INVERTED", "IFVG_FIRST_TOUCH", "IFVG_INVALIDATED"


def stair(n, ends=(), p=20000.0):
    rows = [(p, p + 1, p - 1, p)] * 16
    for k in range(n):
        q = p - 20 * k
        rows += [(q, q + 1, q - 1, q), (q, q + 4, q, q + 4), (q + 4, q + 6, q + 3, q + 5), (q + 5, q + 5, q - 15, q - 14)]
        if k in ends:
            rows.append((q - 14, q + 4, q - 14, q + 4))
    return rows


def recovery(n, rows, step=9):
    """n candles rising `step` points each from the last close: they end the newest IFVGs one by one."""
    c, out = rows[-1][3], list(rows)
    for _ in range(n):
        out.append((c, c + step + 1, c - 1, c + step))
        c += step
    return out


def model(rows, flip, memory=50):
    """The checked oracle and the IFVG side under test (bearish, or bullish on the mirrored candles)."""
    cs = from_rows(rows)
    cs = mirror(cs, 0.0) if flip else cs
    same(cs, FvgSettings(), IfvgSettings(memory=memory))
    m = run_checked(cs, Settings(modules=("fvg", "ifvg"), ifvg=IfvgSettings(memory=memory)))
    return m, (m.ifvg.bull if flip else m.ifvg.bear)


def drops(m):
    return [e for e in m.events if e.type == DROP]


def inverted(m, k):
    """The id of the k-th IFVG (inversion order)."""
    return [e.sid for e in m.events if e.type == INV][k]


SIDES = pytest.mark.parametrize("flip", [False, True], ids=["bearish", "bullish (mirror)"])


@SIDES
def test_01_fifty_active_plus_a_new_active_keeps_51(flip):
    m, side = model(stair(51), flip)
    assert len(side) == 51 and all(r.end is None for r in side) and not drops(m)


@SIDES
def test_02_fifty_five_active_are_all_kept(flip):
    m, side = model(stair(55), flip)
    assert len(side) == 55 and all(r.end is None for r in side) and not drops(m)
    assert [r.id for r in side] == [inverted(m, k) for k in range(55)]               # inversion order


def test_03_the_routine_drops_the_old_invalidated_record_and_keeps_51_active():
    """51 ACTIVE + 1 older INVALIDATED (53 > 50 is never left like this by a bar; the routine itself):
    exactly the INVALIDATED one leaves, all 51 ACTIVE stay. The oracle and Pine's compactIfvg."""
    for cls, mk in ((IfvgEngine, lambda i, end: Ifvg(i, -1, i, i, 2.0, 1.0, 1.5, i, i, 1.0, "UNTOUCHED", end=end)),
                    (IfvgPine, lambda i, end: PineIfvg(i, -1, i, i, i, i, 2.0, 1.0, 1.5, i, i, 1.0, 0, end_bar=end))):
        log = EventLog()
        e = cls(IfvgSettings(), NQ_TICK, log, FvgEngine(FvgSettings(), NQ_TICK, log))
        recs = [mk(0, 5)] + [mk(i, None) for i in range(1, 52)]
        e._compact(recs)
        assert [r.id for r in recs] == list(range(1, 52)) and e.dropped == 1
        assert [(x.type, x.sid, x.meta) for x in log.events] == [(DROP, 0, "invalidated record")]


@SIDES
def test_03_an_old_invalidated_record_leaves_and_51_active_remain(flip):
    """The first IFVG ends at once; at the 51st inversion the side holds 51 (it + 50 ACTIVE): it leaves.
    The 52nd inversion leaves 51 ACTIVE, all kept."""
    m, side = model(stair(52, ends={0}), flip)
    (d,) = drops(m)
    assert (d.sid, d.meta, d.bar) == (inverted(m, 0), "invalidated record", [e.bar for e in m.events if e.type == INV][50])
    assert len(side) == 51 and all(r.end is None for r in side)


@SIDES
def test_04_an_over_full_active_side_compacts_when_one_ends(flip):
    """52 ACTIVE are kept; then the newest ends: on that bar its retest, its end, then memory drops it."""
    m, side = model(stair(52, ends={51}), flip)
    last = inverted(m, 51)
    bar = max(e.bar for e in m.events)
    assert [(e.type, e.sid) for e in m.events if e.bar == bar and e.type.startswith("IFVG_")] == \
           [(TOUCH, last), (END, last), (DROP, last)]
    assert len(side) == 51 and all(r.end is None for r in side)


@SIDES
def test_04_within_memory_an_ended_record_stays(flip):
    m, side = model(stair(10, ends={9}), flip)
    assert len(side) == 10 and side[-1].end is not None and not drops(m)


@SIDES
def test_05_an_older_invalidated_record_goes_before_a_newly_invalidated_one(flip):
    """50 records: IFVG 0 (ended long ago), IFVG 49 (just ended), 48 ACTIVE. The 51st inversion drops
    IFVG 0; IFVG 49 stays, INVALIDATED."""
    m, side = model(stair(51, ends={0, 49}), flip)
    assert [d.sid for d in drops(m)] == [inverted(m, 0)]
    kept = next(r for r in side if r.id == inverted(m, 49))
    assert len(side) == 50 and kept.end is not None and sum(r.end is None for r in side) == 49


@SIDES
def test_05_of_two_ended_on_one_bar_the_older_goes_first(flip):
    """51 ACTIVE; one candle ends IFVG 49 and IFVG 50: the side holds 51, so IFVG 49 (older) leaves and
    IFVG 50 stays INVALIDATED."""
    rows = stair(51)
    q = 20000.0 - 20 * 50
    m, side = model(rows + [(q - 14, q + 24, q - 14, q + 24)], flip)
    assert [d.sid for d in drops(m)] == [inverted(m, 49)]
    assert len(side) == 50 and [r.end is not None for r in side].count(True) == 1 and side[-1].id == inverted(m, 50)


def _lifecycle(m):
    return [(e.bar, e.type, e.dir, e.sid, e.price) for e in m.events if e.type.startswith("IFVG_") and e.type != DROP]


@SIDES
def test_06_07_overflow_never_changes_a_lifecycle(flip):
    """55 ACTIVE, then 12 rising candles end the newest ones one by one: with memory 50 every ended
    one is dropped right after its end, never an ACTIVE one; every IFVG's retest / CE / full / end is
    the same as with unlimited memory."""
    rows = recovery(12, stair(55))
    m, side = model(rows, flip)
    big, _ = model(rows, flip, BIG)
    assert _lifecycle(m) == _lifecycle(big) and len(_lifecycle(m)) > 55
    assert drops(m) and all(d.meta == "invalidated record" for d in drops(m))
    ended = {e.sid for e in m.events if e.type == END}
    assert {d.sid for d in drops(m)} <= ended
    facts = lambda s: {r.id: (r.retest, r.ce, r.full, r.end) for r in s}
    big_side = big.ifvg.bull if flip else big.ifvg.bear
    assert {i: f for i, f in facts(big_side).items() if f[3] is None} == {i: f for i, f in facts(side).items() if f[3] is None}
    assert len(side) >= 50 and all(r.end is None for r in side)


def test_09_deterministic_replay_with_overflow():
    cs = from_rows(recovery(3, stair(55)))            # ends one: 54 ACTIVE remain, over 50
    a, ae = run(IfvgPine, cs, FvgSettings(), IfvgSettings())
    b, be = run(IfvgPine, list(cs), FvgSettings(), IfvgSettings())
    assert a.records() == b.records() and ae == be and len(a.bear) == 54 and all(r.end_bar is None for r in a.bear)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_10_random_walks_never_lose_an_active_ifvg(seed):
    """5,000 bars with gaps (trending walks: a side holds up to 72–95 ACTIVE IFVGs): no ACTIVE IFVG is
    dropped, the sides overflow 50, and the ACTIVE IFVGs and every lifecycle event equal those of an
    unlimited memory. (The v0.9.0-dev fallback dropped 95–215 ACTIVE IFVGs on 20,000-bar walks.)"""
    cs = random_walk(5000, seed, gap_prob=0.02)
    same(cs, FvgSettings(), IfvgSettings())
    log = EventLog()
    f = FvgEngine(FvgSettings(), NQ_TICK, log)
    p = IfvgPine(IfvgSettings(), NQ_TICK, log, f)
    peak = 0
    for t, c in enumerate(cs):
        log.at(t, c.time)
        f.step(t, c)
        p.step(t, c)
        peak = max(peak, len(p.bull), len(p.bear))
    big, bev = run(IfvgPine, cs, FvgSettings(), IfvgSettings(memory=BIG))
    life = lambda ev: [(e.bar, e.type, e.dir, e.sid, e.price) for e in ev if e.type.startswith("IFVG_") and e.type != DROP]
    act = lambda e: {(r.side, r.id) for r in e.records() if r.end_bar is None}
    assert peak > 50 and act(p) == act(big) and life(log.events) == life(bev)
    assert all(e.meta == "invalidated record" for e in log.events if e.type == DROP)
