"""IFVG freeze (IST v0.9.1-dev): the automated IFVG-L12 requirements (determinism, reload, prefix,
independence, memory, same-bar order), each pinned by name. A TradingView reload recomputes the script
from its first loaded bar. The strongest automated equivalent is a replay of the same OHLC with the same
settings from a fresh state, compared bar by bar. To that come a prefix extended by future bars, a later
history start, the toggles, a reload from the real Pine state while more than 50 ACTIVE IFVGs are held,
and the real Pine log's own order. Where an earlier test already proves a requirement, it is named too.

IFVG-L12 requirement                                    proven by
1  same OHLC + settings, two fresh runs: identical on     test_l12_1_two_fresh_runs_identical_on_every_bar
   every bar (shadows: id, side, geometry, eligibility;   (+ test_ifvg.py, test_ifvg_pine.py test_25,
   every IFVG field; memory; the bar's events), the        test_ifvg_memory.py test_09)
   Pine-log text byte for byte; the oracle bar by bar
2  no repaint: a bar only adds its inversions, stamps     test_l12_2_a_bar_only_advances_active_ifvgs
   facts / ends of ACTIVE IFVGs, drops INVALIDATED ones
   a prefix = the full run's past; every IFVG of the      test_l12_2_prefix_then_future_bars_rewrite_nothing
   prefix keeps identity, geometry, inversion, facts      (+ fuzz/test_ifvg_properties.py no lookahead)
   a later history start (a reload on a live chart)       test_l12_2_a_later_history_start_keeps_every_ifvg
3  Debug, capture, renderer, alerts, CISD, displacement,  test_l12_3_modules_and_view_settings_never_change_the_ifvg
   liquidity / LRL on or off: the same IFVGs              test_l12_3_the_engine_reads_only_ifvgOn_and_phase_1
                                                          (+ test_ifvg_pine.py test_26_to_32, test_30_31_32; ST-01, ST-06, ST-23)
4  memory: a reload while a side holds > 50 ACTIVE        test_l12_4_reload_above_50_active_keeps_the_active_set
                                                          (+ test_l12_1 on the walk; test_ifvg_memory.py; INV-IFVG-07 / 09)
5  same-bar order (facts → end → memory, then each        test_l12_5_same_bar_order_in_the_real_pine_log
   inversion → IFVG_INVERTED → memory; no fact on the     test_l12_5_same_bar_order_pinned_real_example
   inversion bar)                                         test_l12_5_same_bar_order_on_every_bar (+ ST-23's 4 orders)
6  Phase 1 identical with the IFVG on and off             test_l12_6_phase_1_identical_with_ifvg_on_and_off
                                                          (+ fuzz test_ifvg_never_changes_other_modules; test_ifvg_pine.py test_33)
7  real capture: 0 DIFFERENCE, counts pinned              tests/test_parity_v091_evidence.py, tests/test_parity_capture.py
"""
import re
from collections import Counter, defaultdict
from dataclasses import astuple
from functools import lru_cache

import pytest

from validation.candles import random_walk
from validation.models.events import EventLog
from validation.models.fvg import FvgEngine
from validation.models.ifvg import PRE, IfvgEngine, IfvgPine
from validation.models.ist import IstModel
from validation.models.types import KNOWN_MODULES, NQ_TICK, FvgSettings, IfvgSettings, Settings, ViewSettings
from validation.parity import CAPTURE_V091, EVIDENCE, capture
from validation.parity.manual import _fmt, pine_text
from validation.static_checks import _ifvg_blocks, code, inputs, source, st06_renderer_never_writes_state, view_identifiers
from validation.studies import displacement as dsp
from validation.tests.test_ifvg_pine import run

pytestmark = [pytest.mark.ifvg, pytest.mark.section("ifvg")]
BIG = 10 ** 6
TZ = "America/New_York"
DATA = ("v091", "seg0", "seg1", "seg2", "walk")
# PineIfvg as a tuple: identity … pre, then (bar, time) of the touch, CE and full facts, then the end (bar, time, close)
FIXED, FACTS, END = slice(0, 13), ((13, 15), (15, 17), (17, 19)), slice(19, 22)
LETTER = {"IFVG_FIRST_TOUCH": "T", "IFVG_INVALIDATED": "I", "IFVG_DROPPED_MEMORY": "D", "IFVG_INVERTED": "V"}
ORDER = re.compile(r"f*[TI]*D*(VD*)*")      # Phase 1, facts / ends, memory, then each inversion and its memory


@lru_cache(maxsize=None)
def candles(name):
    """v091: the real v0.9.1-dev capture's bars (MNQ1! 2026-11-02); seg0…2: the research data (NQ 10-27/28,
    MNQ 10-29/30, MNQ 10-13/14); walk: 5,000 bars on which a side holds more than 50 ACTIVE IFVGs."""
    if name == "v091":
        return tuple(b["candle"] for b in v091_cap()["bars"])
    if name == "walk":
        return tuple(random_walk(5000, 1, gap_prob=0.02))
    return tuple(dsp.segments()[int(name[-1])][1])


@lru_cache(maxsize=None)
def v091_cap():
    return capture.parse(CAPTURE_V091.read_text(encoding="utf-8"))


def trace(cs, ifs=IfvgSettings(), cls=IfvgPine):
    """A fresh Phase 1 FVG engine and IFVG engine stepped on cs. Per bar: the shadows (id, side, top, bottom,
    CE, confirmation bar, open in Phase 1), each side's IFVG records in memory order (every field), the
    counters (inverted, dropped) and the bar's events in emission order (Phase 1 and IFVG)."""
    log = EventLog()
    f = FvgEngine(FvgSettings(), NQ_TICK, log)
    e = cls(ifs, NQ_TICK, log, f)
    out = []
    for t, c in enumerate(cs):
        log.at(t, c.time)
        n = len(log.events)
        f.step(t, c)
        e.step(t, c)
        reg = e.shadows if cls is IfvgPine else list(e.parents.values())
        out.append((tuple((z.id, z.dir, z.top, z.bottom, z.mid, z.confirm_bar, z.is_open) for z in reg),
                    tuple(map(astuple, e.bull)), tuple(map(astuple, e.bear)), (e.inverted, e.dropped),
                    tuple((x.type, x.dir, x.sid, x.origin_bar, x.price, x.meta) for x in log.events[n:])))
    return out, log.events


@lru_cache(maxsize=None)
def pine(name, memory=50):
    return trace(candles(name), IfvgSettings(memory=memory))


def common(snap, is_pine):
    """A per-bar snapshot in the terms Pine and the oracle share (the oracle keeps no times; Pine codes pre)."""
    sh, bull, bear, counts, ev = snap
    rec = (lambda r: (r[0], r[1], r[2], r[4], *r[6:12], PRE[r[12]], r[13], r[15], r[17], r[19])) if is_pine else (lambda r: r)
    return [z[0] for z in sh], [rec(r) for r in bull], [rec(r) for r in bear], counts, [x[:5] for x in ev]


def letters(ev):
    return "".join(LETTER.get(x[0], "f") for x in ev if x[0].startswith(("FVG_", "IFVG_")))


def check_order(ev) -> bool:
    """One bar's events ((type, side, id, …), emission order) in the frozen order:
    1. Phase 1 (FVG_*);
    2. the ACTIVE IFVGs' FIRST_TOUCH / INVALIDATED (a record's touch before its end);
    3. the memory drops after the ends (bullish side, then bearish);
    4. each new inversion, IFVG_INVERTED, followed by its own side's drops.
    True when the bar shows all of it: an end, a drop, an inversion and its drop."""
    tag = letters(ev)
    assert ORDER.fullmatch(tag), tag
    body, ifvg = tag.lstrip("f"), [x[:3] for x in ev if x[0].startswith("IFVG_")]
    k = len(re.match(r"[TI]*", body).group(0))
    d = k + len(re.match(r"D*", body[k:]).group(0))
    assert [x[1] for x in ifvg[k:d]] == sorted((x[1] for x in ifvg[k:d]), reverse=True)
    side = None
    for x in ifvg[d:]:
        side = x[1] if x[0] == "IFVG_INVERTED" else side
        assert x[1] == side
    for i, x in enumerate(ifvg[:k]):
        assert x[0] != "IFVG_INVALIDATED" or ("IFVG_FIRST_TOUCH", *x[1:]) not in ifvg[i + 1:k]
    return bool(re.fullmatch(r"[TI]*I[TI]*D+V+D+", body))


# ── 1 · determinism ──
@pytest.mark.parametrize("name", DATA)
def test_l12_1_two_fresh_runs_identical_on_every_bar(name):
    """Two runs from a fresh state on the same OHLC with the same settings are identical on every bar:
    the Phase 1 shadows (identity, original side, geometry, eligibility), every IFVG record field (id =
    the original FVG id, side, top, bottom, CE, inversion bar / time / close, pre, the touch / CE / full
    bar and time, the end bar / time / close), the memory (records held per side, counters) and the
    bar's events in order. The Pine-log text of the IFVG event stream is the same byte for byte, and the
    approved oracle gives the same per-bar state."""
    cs = candles(name)
    a, ea = pine(name)
    b, eb = trace(list(cs))
    assert a == b and len(a) == len(cs)
    text = lambda ev: "\n".join(pine_text(x, TZ, NQ_TICK) for x in ev if x.type.startswith("IFVG_")).encode("utf-8")
    assert text(ea) == text(eb) and text(ea).count(b"IFVG_INVERTED") > 100
    o, _ = trace(cs, cls=IfvgEngine)
    assert [common(x, True) for x in a] == [common(x, False) for x in o]
    peak = max(max(len(s[1]), len(s[2])) for s in a)
    assert (peak > 50) == (name == "walk")                   # the walk overflows: a replay with > 50 ACTIVE
    if name == "v091":
        m1, m2 = (IstModel(Settings(modules=KNOWN_MODULES)).run(cs) for _ in range(2))
        assert m1.ifvg.state() == m2.ifvg.state() and m1.events == m2.events


# ── 2 · prefix / history stability ──
@pytest.mark.parametrize("name", DATA)
def test_l12_2_a_bar_only_advances_active_ifvgs(name):
    """Non-repaint, bar by bar. A new bar may only:
    (a) add the IFVGs it inverts: inversion bar = this bar, no fact yet, IFVG_INVERTED;
    (b) stamp an unset fact, or the end, of an ACTIVE IFVG on this bar;
    (c) drop an INVALIDATED record (IFVG_DROPPED_MEMORY), including one that ended on this bar.
    Identity, side, geometry, inversion bar / time / close and prior state never change, a stamped fact
    never changes, and an INVALIDATED record never changes."""
    cs, (snaps, _) = candles(name), pine(name)
    seen = Counter()
    for t in range(1, len(snaps)):
        key = lambda s: {(r[1], r[0]): r for r in s[1] + s[2]}
        prev, cur, ev = key(snaps[t - 1]), key(snaps[t]), {x[:3] for x in snaps[t][4]}
        stamp = (t, cs[t].time)
        for k in cur.keys() - prev.keys():
            r = cur[k]
            assert r[9:11] == stamp and r[11] == cs[t].close and r[13:] == (None,) * 9 and ("IFVG_INVERTED", *k) in ev
            seen["inverted"] += 1
        for k in prev.keys() - cur.keys():
            assert ("IFVG_DROPPED_MEMORY", *k) in ev and (prev[k][19] is not None or ("IFVG_INVALIDATED", *k) in ev)
            seen["dropped"] += 1
        for k in prev.keys() & cur.keys():
            p, r = prev[k], cur[k]
            assert r[FIXED] == p[FIXED]
            if p[19] is not None:
                assert r == p
                seen["invalidated, unchanged"] += 1
                continue
            for i, j in FACTS:
                assert r[i:j] == p[i:j] or (p[i] is None and r[i:j] == stamp)
            assert r[END] == p[END] or (r[19:21] == stamp and r[21] == cs[t].close and ("IFVG_INVALIDATED", *k) in ev)
            seen["advanced"] += r != p
    assert all(seen[k] > 0 for k in ("inverted", "dropped", "invalidated, unchanged", "advanced")), seen


@pytest.mark.parametrize("name", DATA)
def test_l12_2_prefix_then_future_bars_rewrite_nothing(name):
    """History up to bar N, then the same history extended with future bars: the prefix run equals the
    full run's past on every bar (state and events). With nothing leaving memory, every IFVG of the prefix
    is in the full run with the same identity, side, geometry, inversion bar / time / close and prior
    state; a fact or end it already had is unchanged, one it lacked comes at bar N or later."""
    cs, (full, events) = candles(name), pine(name)
    cuts = range(60, len(cs), len(cs) // 7)
    for n in cuts:
        part, pev = trace(cs[:n])
        assert part == full[:n] and pev == [x for x in events if x.bar < n]
    final = {(r.side, r.id): astuple(r) for r in run(IfvgPine, cs, FvgSettings(), IfvgSettings(memory=BIG))[0].records()}
    later = 0
    for n in cuts:
        for r in map(astuple, run(IfvgPine, cs[:n], FvgSettings(), IfvgSettings(memory=BIG))[0].records()):
            f = final[(r[1], r[0])]
            assert f[FIXED] == r[FIXED]
            for i, j in FACTS + ((19, 22),):
                assert f[i:j] == r[i:j] if r[i] is not None else (f[i] is None or f[i] >= n)
                later += r[i] is None and f[i] is not None
    assert later > 0


@pytest.mark.parametrize("path", sorted(EVIDENCE.glob("*.csv")), ids=lambda p: p.name[:16])
def test_l12_2_a_later_history_start_keeps_every_ifvg(path):
    """A reload on a live chart may load history from a later first bar. Every IFVG whose parent FVG is
    confirmed at least 16 bars (the Phase 1 lookback, fvgLen + 2) after that first bar is the same:
    * with nothing leaving memory, every field;
    * with the default memory, its events and the ACTIVE set.
    Only IFVG_DROPPED_MEMORY follows the number of older records held. This holds while Phase 1 releases
    no OPEN FVG (DEF-A6, frozen), as on all six real captures; on a long real chart it does (rarely,
    four times in the v0.9.1-dev log, all FVGs 4–5 days old and about 1,500 points away), so there an
    FVG's existence, and with it its IFVG, follows the history start as Phase 1 does."""
    cs = [b["candle"] for b in capture.parse(path.read_text(encoding="utf-8"))["bars"]]
    idx, lb = {c.time: i for i, c in enumerate(cs)}, FvgSettings().lookback
    norm = lambda r, k: tuple(x + k if i in (2, 4, 9, 13, 15, 17, 19) and x is not None else x for i, x in enumerate(astuple(r)))
    life = lambda ev, keep: [(x.type, x.dir, x.sid, x.time, x.price) for x in ev
                             if x.type.startswith("IFVG_") and x.type != "IFVG_DROPPED_MEMORY" and keep(x.sid)]
    for mem in (IfvgSettings(memory=BIG), IfvgSettings()):
        base, bev = run(IfvgPine, cs, FvgSettings(), mem)
        for k in (1, 17, 100, 400):
            e, ev = run(IfvgPine, cs[k:], FvgSettings(), mem)
            keep = lambda sid: idx[sid] >= k + lb
            assert base.fvg.drop_open == e.fvg.drop_open == 0
            assert life(ev, keep) == life(bev, keep)
            assert {(r.side, r.id) for r in e.records() if r.end_bar is None and keep(r.id)} == \
                   {(r.side, r.id) for r in base.records() if r.end_bar is None and keep(r.id)}
            if mem.memory == BIG:
                assert {norm(r, k) for r in e.records() if keep(r.id)} == {norm(r, 0) for r in base.records() if keep(r.id)}


# ── 3 · visibility / feature independence ──
def test_l12_3_modules_and_view_settings_never_change_the_ifvg():
    """On the real v0.9.1-dev candles, the IFVG records and events are the same with Phase 1 alone
    and with every module, with each of levels, sessions, liquidity, LRL, HTF FVG, CISD and displacement
    off, and with the FVG display rules changed. The other modules' events are the same with the IFVG on
    and off."""
    cs = candles("v091")
    key = lambda m: (m.ifvg.state(), [x for x in m.events if x.type.startswith("IFVG_")])
    want = key(IstModel(Settings(modules=("fvg", "ifvg"))).run(cs))
    allm = IstModel(Settings(modules=KNOWN_MODULES)).run(cs)
    assert key(allm) == want and want[1]
    for off in ("levels", "sessions", "liq", "lrl", "htf", "cisd", "disp"):
        assert key(IstModel(Settings(modules=tuple(x for x in KNOWN_MODULES if x != off))).run(cs)) == want, off
    for v in (ViewSettings(fvg_show=False), ViewSettings(mit_rule="firstTouch", fvg_max_visible=1, minimal=True)):
        assert key(IstModel(Settings(modules=("fvg", "ifvg"), view=v)).run(cs)) == want
    no_ifvg = IstModel(Settings(modules=tuple(x for x in KNOWN_MODULES if x != "ifvg"))).run(cs)
    assert [x for x in allm.events if not x.type.startswith("IFVG_")] == no_ifvg.events


def test_l12_3_the_engine_reads_only_ifvgOn_and_phase_1():
    """In IST.pine the IFVG engine names one input, ifvgOn. Of the script's global names it reads only the
    approved constant, its four event codes, its own book and the Phase 1 FVG lists (bullFvgs, bearFvgs,
    fvgDropNow), so Debug, the capture, every display and alert input, and the CISD, displacement,
    liquidity and LRL inputs and state are out of its reach. Its call is gated by ifvgOn and the bar's
    confirmation inside `if engineTick` (Confirmed only), in no other module's block. The renderer (L6) and
    alerts (L7) run after it and write no state (ST-06), so a future IFVG renderer cannot change it."""
    lines = list(source())
    names = set(re.findall(r"\b\w+\b", "\n".join(_ifvg_blocks(lines))))
    glob = {m.group(1) for ln in lines if (m := re.match(r"^(?:var\s+)?(?:[\w.<>]+\s+)?(\w+)\s*:?=(?![=>])", code(ln)))}
    assert names & set(inputs()) == {"ifvgOn"} and not names & view_identifiers()
    assert names & glob == {"ifvgOn", "IFVG_MEM", "EV_IFVG_INVERTED", "EV_IFVG_TOUCH", "EV_IFVG_INVAL", "EV_IFVG_DROPPED",
                            "ifvgBook", "bullFvgs", "bearFvgs", "fvgDropNow"}
    i = next(i for i, ln in enumerate(lines) if code(ln).strip() == "if ifvgOn and barstate.isconfirmed")
    chain, ind = [], len(lines[i]) - len(lines[i].lstrip())
    for ln in map(code, reversed(lines[:i])):
        if ln.strip() and len(ln) - len(ln.lstrip()) < ind:
            chain.append(ln.strip())
            ind = len(ln) - len(ln.lstrip())
    assert chain[0] == "if engineTick" and len(chain) == 1 and st06_renderer_never_writes_state()[0]


# ── 4 · memory determinism ──
def replay(cap):
    """A reload from the real Pine state: the v0.9.1-dev capture's IFVG snapshot restored into fresh oracles
    (validation/parity/capture.py restore_ifvg), then every later captured bar. Per bar: each side's records
    (every field) and the bar's IFVG events in order."""
    s, _ = capture.settings_of(cap["head"])
    cs, log, fvg, e, _ = capture.restore_ifvg(cap, s)
    out = {}
    for t in range(cap["ifvg"]["IFVGSTATE"][0]["at"] - cap["bars"][0]["i"] + 1, len(cs)):
        log.at(t, cs[t].time)
        n = len(log.events)
        fvg.step(t, cs[t])
        e.step(t, cs[t])
        out[t] = (tuple(map(astuple, e.bull)), tuple(map(astuple, e.bear)),
                  tuple((x.type, x.dir, x.sid) for x in log.events[n:] if x.type.startswith("IFVG_")))
    return out


def test_l12_4_reload_above_50_active_keeps_the_active_set():
    """The real capture holds up to 66 ACTIVE bearish IFVGs (51–66 for 655 bars). Two reloads from Pine's
    own state are identical on every bar, and match Pine's active count per side on every captured bar.
    The ACTIVE set moves only by ends and inversions (= before − IFVG_INVALIDATED + IFVG_INVERTED): memory
    compaction never touches it, and every drop is an INVALIDATED record. The final ACTIVE set is Pine's
    own: its snapshot's ACTIVE records and its logged inversions, minus its logged ends."""
    cap = v091_cap()
    a, b = replay(cap), replay(cap)
    assert a == b
    active = lambda snap: {(r[1], r[0]) for r in snap[0] + snap[1] if r[14] is None}
    was = {(x["side"], x["id"]) for x in cap["ifvg"]["IFVGREC"] if x["end"] is None}
    over = 0
    for t, snap in a.items():
        now, ev = active(snap), snap[2]
        assert now == was - {x[1:] for x in ev if x[0] == "IFVG_INVALIDATED"} | {x[1:] for x in ev if x[0] == "IFVG_INVERTED"}
        assert not {x[1:] for x in ev if x[0] == "IFVG_DROPPED_MEMORY"} & now
        got = cap["bars"][t]["ifvg"]
        assert got is None or got["ia"] == (sum(k[0] > 0 for k in now), sum(k[0] < 0 for k in now))
        over += sum(k[0] < 0 for k in now) > 50
        was = now
    assert over == 655 and max(sum(k[0] < 0 for k in active(s)) for s in a.values()) == 66
    t_snap = cap["bars"][min(a) - 1]["time"]
    logged = lambda typ: {(x["dir"], x["sid"]) for x in cap["events"] if x["type"] == typ and x["time"] > t_snap}
    snap0 = {(x["side"], x["id"]) for x in cap["ifvg"]["IFVGREC"] if x["end"] is None}
    assert active(a[max(a)]) == (snap0 | logged("IFVG_INVERTED")) - logged("IFVG_INVALIDATED")


# ── 5 · same-bar order ──
def test_l12_5_same_bar_order_in_the_real_pine_log():
    """Real Pine (the v0.9.1-dev log): on every bar the FVG and IFVG lines come in the frozen order:
    Phase 1 (FVG_*); the ACTIVE IFVGs' FIRST_TOUCH / INVALIDATED (a record's touch before its end); the
    memory drops (bullish side, then bearish); each new inversion followed by its own side's drops. After the
    snapshot, the IFVG lines of every bar are, one by one and in order, the restored oracle's."""
    cap = v091_cap()
    by = defaultdict(list)
    for x in cap["events"]:
        if x["time"] is not None and x["type"].startswith(("FVG_", "IFVG_")):
            by[x["time"]].append((x["type"], x["dir"], x["sid"]))
    assert sum(map(check_order, by.values())) >= 10
    a = replay(cap)
    t_snap = cap["bars"][min(a) - 1]["time"]
    mine = {cap["bars"][t]["time"]: list(ev) for t, (_, _, ev) in a.items() if ev}
    logged = {t: [x for x in ev if x[0].startswith("IFVG_")] for t, ev in by.items() if t > t_snap}
    assert mine == {t: ev for t, ev in logged.items() if ev} and sum(map(len, mine.values())) == 654


def test_l12_5_same_bar_order_pinned_real_example():
    """2026-11-02 05:57, real Pine and the oracle:
    1. Phase 1 invalidates the bearish FVG 05:52.
    2. The ACTIVE bearish IFVG 05:50 is retested and invalidated on that bar (high 28770.25 ≥ its top, so
       its CE and full facts too).
    3. The over-full bearish side drops it at once.
    4. The 05:52 FVG inverts into a bullish IFVG, and the bullish side drops its oldest INVALIDATED record.
    The new IFVG's zone was reached on that bar (low ≤ its top), but it gets no fact there."""
    cap = v091_cap()
    t = next(i for i, b in enumerate(cap["bars"]) if _fmt(b["time"], TZ) == "2026-11-02 05:57")
    when = cap["bars"][t]["time"]
    lines = [x for x in cap["events"] if x["time"] == when and x["type"].startswith(("FVG_", "IFVG_"))]
    ifvg = [(x["type"], x["dir"], _fmt(x["sid"], TZ)) for x in lines if x["type"].startswith("IFVG_")]
    assert ifvg == [("IFVG_FIRST_TOUCH", -1, "2026-11-02 05:50"), ("IFVG_INVALIDATED", -1, "2026-11-02 05:50"),
                    ("IFVG_DROPPED_MEMORY", -1, "2026-11-02 05:50"), ("IFVG_INVERTED", 1, "2026-11-02 05:52"),
                    ("IFVG_DROPPED_MEMORY", 1, "2026-11-01 23:43")]
    assert ("FVG_INVALIDATED", -1, "2026-11-02 05:52") in [(x["type"], x["dir"], _fmt(x["sid"], TZ)) for x in lines]
    assert letters([(x["type"],) for x in lines]) == "ffffTIDVD"
    a = replay(cap)
    assert [(typ, d, _fmt(sid, TZ)) for typ, d, sid in a[t][2]] == ifvg
    c, old = cap["bars"][t]["candle"], next(r for r in a[t - 1][1] if _fmt(r[0], TZ) == "2026-11-02 05:50")
    new = next(r for r in a[t][0] if _fmt(r[0], TZ) == "2026-11-02 05:52")
    assert c.high >= old[4] < c.close and new[7] == t and new[11:] == (None,) * 4 and c.low <= new[4]


@pytest.mark.parametrize("memory", [1, 2, 50])
@pytest.mark.parametrize("name", DATA)
def test_l12_5_same_bar_order_on_every_bar(name, memory):
    """Pine's formulation on every bar, with memory 1, 2 and 50: the same order as the real log. The
    compaction after the ends drops bullish records before bearish ones, and the drops after an inversion
    are of its own side. A new IFVG has no fact on its inversion bar, although that bar reached its near
    edge for nearly every one. Every end comes with all its facts stamped (touch ≤ CE ≤ full ≤ end)."""
    snaps, _ = pine(name, memory)
    full, reached = sum(check_order(s[4]) for s in snaps), 0
    cs = candles(name)
    for r in (r for s in (snaps[-1][1], snaps[-1][2]) for r in s):
        assert all(b is None or b > r[9] for b in (r[13], r[15], r[17], r[19]))
        reached += (cs[r[9]].high >= r[7]) if r[1] < 0 else (cs[r[9]].low <= r[6])
        if r[19] is not None:
            assert None not in (r[13], r[15], r[17]) and r[13] <= r[15] <= r[17] <= r[19]
    assert reached > 0 and (full > 0 or memory == 50)


# ── 6 · Phase 1 independence ──
@pytest.mark.parametrize("name", DATA)
def test_l12_6_phase_1_identical_with_ifvg_on_and_off(name):
    """Phase 1 alone and Phase 1 with the IFVG, the same history: on every bar the same Phase 1 events
    and the same FVG records (ids, geometry, lifecycle bars, memory order), and the same memory releases."""
    on, off = IstModel(Settings(modules=("fvg", "ifvg"))), IstModel(Settings(modules=("fvg",)))
    for c in candles(name):
        assert [x for x in on.step(c) if not x.type.startswith("IFVG_")] == off.step(c)
        assert list(map(astuple, on.fvg.records())) == list(map(astuple, off.fvg.records()))
    assert (on.fvg.drop_open, on.fvg.drop_closed) == (off.fvg.drop_open, off.fvg.drop_closed) and on.ifvg.inverted
