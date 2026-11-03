"""IFVG-L11 · human / golden validation of IFVG-R (validation/golden/human/ifvg/, README there). Real MNQ
1m candles copied exactly from the evidence captures (IST v0.9.1-dev and v0.8.0-dev, kept byte for
byte); each case was chosen and classified from its candles; the expected verdict is IFVG-R written out
by hand below (`by_hand`: the Phase 1 FVG, its DEF-A5 close beyond the far edge, the IFVG's facts and
end). Nothing here reads a rule from the cases.

Checked per case: the candles are the evidence bars; the recorded numbers follow from them; the oracle
(every invariant checked) and Pine's formulation give the recorded verdict on the case window and on
the whole capture; the real Pine log agrees (v0.9.1-dev: FVG_INVALIDATED and IFVG_INVERTED of the same
FVG id on the same bar, the audit geometry, every later IFVG event and CE / full fact; v0.8.0-dev: the
DEF-A5 FVG_INVALIDATED); the context recorded is the Pine log's and never changes the verdict; the
mirror. Then the coverage the task asks for, the mechanical case R, the memory golden (real log) and
the H1 reference (supporting only)."""
import json
from functools import lru_cache

import pytest

from validation.candles import mirror
from validation.golden import GOLDEN_DIR, candles_of
from validation.invariants import run_checked
from validation.models.ifvg import PRE, IfvgPine
from validation.models.ist import IstModel
from validation.models.types import MODULES, NQ_TICK, FvgSettings, IfvgSettings, Settings
from validation.parity import EVIDENCE, capture
from validation.tests.test_ifvg_pine import same
from validation.tests.test_parity_v091_evidence import drop_kinds

pytestmark = [pytest.mark.ifvg, pytest.mark.section("golden")]
DIR = GOLDEN_DIR / "human" / "ifvg"
ALL = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(DIR.glob("GOLD_IFVG_*.json"))}
CASES = {k: v for k, v in ALL.items() if v.get("kind", "case") == "case"}
SIDE = {1: "BULL", -1: "BEAR"}
TOL = 1e-9


def by_hand(w, k3, tick=NQ_TICK, length=14, k_tra=0.1, min_ticks=2):
    """IFVG-R on the candles `w` for the three-candle gap confirmed at index k3, written out:
    DEF-A1 / A2 (the Phase 1 FVG and its qualification at candle 1), DEF-A4 milestones, DEF-A5 (the
    first close strictly beyond the far edge), then the IFVG (opposite side, same geometry): retest
    (near edge = the inversion boundary), CE, full traversal (far edge) by wick from the next bar,
    and its end on the first close strictly beyond its far edge. Indices into `w`."""
    c1, c3 = w[k3 - 2], w[k3]
    d = 1 if c3.low > c1.high else -1 if c3.high < c1.low else 0
    top, bottom = (c3.low, c1.high) if d > 0 else (c1.low, c3.high)
    tr = lambda j: max(w[j].high - w[j].low, abs(w[j].high - w[j - 1].close), abs(w[j].low - w[j - 1].close))
    tra = sum(tr(j) for j in range(k3 - 1 - length, k3 - 1)) / length
    gap, ce = top - bottom, (top + bottom) / 2
    out = {"dir": d, "top": top, "bottom": bottom, "ce": ce, "gap": gap, "tr_avg": tra,
           "qualified": d != 0 and gap >= min_ticks * tick - tick * 0.01 and gap >= k_tra * tra}
    near, far = (top, bottom) if d > 0 else (bottom, top)
    reach = (lambda c, lv: c.low <= lv) if d > 0 else (lambda c, lv: c.high >= lv)
    beyond = (lambda c: c.close < bottom) if d > 0 else (lambda c: c.close > top)
    inv = next((j for j in range(k3 + 1, len(w)) if beyond(w[j])), None)
    stop = len(w) if inv is None else inv + 1
    first = lambda r, lv, a, b: next((j for j in range(a, b) if r(w[j], lv)), None)
    out["touch"], out["ce_touch"], out["full"] = (first(reach, lv, k3 + 1, stop) for lv in (near, ce, far))
    wick = (lambda c: c.low < far) if d > 0 else (lambda c: c.high > far)
    out["rejections"] = [(j, "edge" if w[j].close == far else "wick") for j in range(k3 + 1, stop if inv is None else inv)
                         if w[j].close == far or wick(w[j])]
    out["inversion"] = inv
    if inv is not None:
        done = lambda b: b is not None and b < inv
        out["pre"] = "FULL" if done(out["full"]) else "CE" if done(out["ce_touch"]) else \
            "TOUCHED" if done(out["touch"]) else "UNTOUCHED"
        s, inear, ifar = -d, far, near
        ireach = (lambda c, lv: c.high >= lv) if s < 0 else (lambda c, lv: c.low <= lv)
        end = next((j for j in range(inv + 1, len(w)) if ((w[j].close > ifar) if s < 0 else (w[j].close < ifar))), None)
        stop2 = len(w) if end is None else end + 1
        out.update(side=s, margin_ticks=round(abs(w[inv].close - inear) / tick), end=end,
                   retest=first(ireach, inear, inv + 1, stop2), ifvg_ce=first(ireach, ce, inv + 1, stop2),
                   traversal=first(ireach, ifar, inv + 1, stop2))
    return out


def window(case):
    return candles_of(case)


def at(case, key):
    """Index in the case window of a recorded time (None stays None)."""
    from validation.models.events import parse_local
    if key is None:
        return None
    t = parse_local(key, case["timezone"])
    return next(i for i, c in enumerate(window(case)) if c.time == t)


def k3_of(case):
    return at(case, case["fvg"]["confirmation"])


@lru_cache(maxsize=None)
def evidence(name: str) -> dict:
    return capture.parse((EVIDENCE / name).read_text(encoding="utf-8"))


def history(case):
    return [b["candle"] for b in evidence(case["source"]["evidence"][0])["bars"]]


def offset(case) -> int:
    t0 = window(case)[0].time
    return next(i for i, c in enumerate(history(case)) if c.time == t0)


def recorded(case):
    """The recorded expectation as window indices, in by_hand's terms."""
    f, e, lc = case["fvg"], case["expected"], case["expected"]["lifecycle"]
    inv = e["inversion"]
    out = {"dir": 1 if f["side"] == "BULL" else -1, "top": f["top"], "bottom": f["bottom"], "ce": f["ce"],
           "touch": at(case, f["touch"]), "ce_touch": at(case, f["ce_touch"]), "full": at(case, f["full"]),
           "rejections": [(at(case, r["time"]), r["kind"]) for r in case["rejections"]],
           "inversion": at(case, inv["time"]) if inv else None}
    if inv:
        out.update(side=1 if inv["ifvg_side"] == "BULL" else -1, margin_ticks=inv["margin_ticks"],
                   pre=f["state_before_inversion"], retest=at(case, lc["first_touch"]), ifvg_ce=at(case, lc["ce"]),
                   traversal=at(case, lc["full_traversal"]),
                   end=at(case, lc["invalidated"]["time"]) if lc["invalidated"] else None)
    return out


# ── per case ──
@pytest.mark.parametrize("cid", sorted(CASES))
def test_candles_are_exact_evidence_bars(cid):
    case = CASES[cid]
    hist, w, i = history(case), window(case), offset(case)
    assert hist[i:i + len(w)] == w                            # time and OHLC, bar for bar: nothing fabricated


@pytest.mark.parametrize("cid", sorted(CASES))
def test_recorded_numbers_follow_from_the_candles(cid):
    """IFVG-R by hand on the window gives every recorded number and time."""
    case, w = CASES[cid], window(CASES[cid])
    h, f = by_hand(w, k3_of(case)), case["fvg"]
    assert h["qualified"] and abs(h["tr_avg"] - f["tr_avg"]) <= TOL and abs(h["gap"] - f["gap"]) <= TOL
    rec = recorded(case)
    assert {k: h.get(k) for k in rec} == rec
    assert f["origin"] == case["candles"][k3_of(case) - 2][0] and f["id"] == f["confirmation"]
    e = case["expected"]
    assert e["verdict"] == ("NO INVERSION" if h["inversion"] is None else f"{SIDE[h['side']]}ISH IFVG")
    if h["inversion"] is not None:
        c = w[h["inversion"]]
        assert e["inversion"]["ohlc"] == [c.open, c.high, c.low, c.close] and e["inversion"]["close"] == c.close
        lc = e["lifecycle"]
        assert lc["state_at_window_end"] == ("ACTIVE" if h["end"] is None else "INVALIDATED")
        assert lc["invalidated"] is None or lc["invalidated"]["close"] == w[h["end"]].close


def _ifvg(m, k3):
    return next((r for r in m.ifvg.records() if r.parent_bar == k3), None)


@pytest.mark.parametrize("cid", sorted(CASES))
def test_oracle_and_pine_give_the_recorded_verdict(cid):
    """The oracle (every invariant checked) and Pine's formulation, on the case window."""
    case, w, k3 = CASES[cid], window(CASES[cid]), k3_of(CASES[cid])
    rec = recorded(case)
    m = run_checked(w, Settings(modules=("fvg", "ifvg")))
    same(w, FvgSettings(), IfvgSettings())                    # IfvgPine = the oracle, record and event
    z = next(z for z in m.fvg.records() if z.confirm_bar == k3)
    assert (z.dir, z.top, z.bottom, z.mid, z.touch_bar, z.ce_bar, z.full_bar, z.inv_bar) == \
           (rec["dir"], rec["top"], rec["bottom"], rec["ce"], rec["touch"], rec["ce_touch"], rec["full"], rec["inversion"])
    r = _ifvg(m, k3)
    if rec["inversion"] is None:
        assert r is None
        return
    assert (r.side, r.bar, r.top, r.bottom, r.mid, r.pre, r.retest, r.ce, r.full, r.end, r.id) == \
           (rec["side"], rec["inversion"], rec["top"], rec["bottom"], rec["ce"], rec["pre"], rec["retest"], rec["ifvg_ce"],
            rec["traversal"], rec["end"], z.id)


@pytest.mark.parametrize("cid", sorted(CASES))
def test_whole_capture_agrees(cid):
    """Run on the whole evidence capture (approved settings), the case's FVG and IFVG are the same, and
    the recorded state after the window (`after_window`) holds."""
    case, k3 = CASES[cid], k3_of(CASES[cid])
    i, rec = offset(case), recorded(case)
    m = IstModel(Settings(modules=("fvg", "ifvg"))).run(history(case))
    r = _ifvg(m, i + k3)
    sh = lambda b: None if b is None else b - i
    if rec["inversion"] is None:
        assert r is None or r.bar - i >= len(window(case))
    else:
        n = len(window(case))
        inside = lambda b: None if b is None or b - i >= n else b - i
        assert (r.side, sh(r.bar), inside(r.retest), inside(r.ce), inside(r.full), inside(r.end)) == \
               (rec["side"], rec["inversion"], rec["retest"], rec["ifvg_ce"], rec["traversal"], rec["end"])
    after = case["after_window"]
    tz = case["timezone"]
    from validation.parity.manual import _fmt
    t = lambda b: None if b is None else _fmt(history(case)[b].time, tz).replace(" ", "T")
    assert after == {"inversion": t(r.bar) if r else None, "invalidated": t(r.end) if r else None,
                     "first_touch": t(r.retest) if r else None}


def _pine(case):
    return evidence(case["source"]["evidence"][0])


@pytest.mark.parametrize("cid", sorted(CASES))
def test_real_pine_log_agrees(cid):
    """The events IST logged on TradingView for this FVG. v0.9.1-dev: FVG_INVALIDATED and IFVG_INVERTED
    of the same FVG id on the inversion bar (the audit geometry and prior state included), IFVG_FIRST_TOUCH
    and IFVG_INVALIDATED on their bars, the CE / full facts in the BAR lines; nothing on a rejection
    bar. v0.8.0-dev (before IFVG): the same FVG_INVALIDATED (DEF-A5)."""
    case, w = CASES[cid], window(CASES[cid])
    cap, rec = _pine(case), recorded(case)
    fid, fdir = w[k3_of(case)].time, rec["dir"]
    ev = [e for e in cap["events"] if e["sid"] == fid]
    pick = lambda typ, d: sorted(e["time"] for e in ev if e["type"] == typ and e["dir"] == d)
    tm = lambda k: None if k is None else w[k].time
    assert pick("FVG_CREATED", fdir) == [fid]
    assert pick("FVG_INVALIDATED", fdir) == ([tm(rec["inversion"])] if rec["inversion"] is not None else
                                             [t for t in pick("FVG_INVALIDATED", fdir) if t > w[-1].time])
    if case["source"]["pine_ifvg"] is False:
        assert not [e for e in cap["events"] if e["type"].startswith("IFVG_")]
        return
    s = -fdir
    if rec["inversion"] is None:
        assert [t for t in pick("IFVG_INVERTED", s) if t <= w[-1].time] == []
        return
    (inv,) = [e for e in ev if e["type"] == "IFVG_INVERTED" and e["dir"] == s]
    got = capture._kv(inv["text"])
    assert inv["time"] == tm(rec["inversion"]) and abs(inv["price"] - w[rec["inversion"]].close) < 1e-9
    assert [float(got[k]) for k in ("bottom", "top", "ce")] == [rec["bottom"], rec["top"], rec["ce"]] and got["pre"] == rec["pre"]
    upto = lambda typ: [t for t in pick(typ, s) if t <= w[-1].time]
    assert upto("IFVG_FIRST_TOUCH") == ([tm(rec["retest"])] if rec["retest"] is not None else [])
    assert upto("IFVG_INVALIDATED") == ([tm(rec["end"])] if rec["end"] is not None else [])
    # memory may drop the record on its end bar (its side over 50): never earlier. The BAR line lists the
    # facts of the records kept at the bar's close, so a fact on that very bar is the drop's, not IX's.
    dropped = upto("IFVG_DROPPED_MEMORY")
    assert dropped in ([], [tm(rec["end"])]) and (not dropped or rec["end"] is not None)
    bars = {b["time"]: b for b in cap["bars"]}
    for k, tag in ((rec["ifvg_ce"], "C"), (rec["traversal"], "F")):
        if k is not None and w[k].time not in dropped:
            assert f"{tag}{fid}," in bars[w[k].time]["ifvg"]["ix"]


def pine_context(case):
    """The context around the anchor bar (the inversion, else the first rejection) as IST logged it."""
    cap, w = _pine(case), window(case)
    rec = recorded(case)
    k = rec["inversion"] if rec["inversion"] is not None else rec["rejections"][0][0]
    times = [c.time for c in w]
    off = lambda t: times.index(t) - k if t in times else None
    near = lambda e, n: off(e["time"]) is not None and abs(off(e["time"])) <= n
    side = rec.get("side", -rec["dir"])
    return {"anchor": case["candles"][k][0],
            "cisd_within_5": sorted([off(e["time"]), SIDE[e["dir"]]] for e in cap["events"]
                                    if e["type"] == "CISD_CONFIRMED" and near(e, 5)),
            "same_side_cisd_within_5": any(e["type"] == "CISD_CONFIRMED" and e["dir"] == side and near(e, 5)
                                           for e in cap["events"]),
            "displacement_on_anchor": next((SIDE[e["dir"]] for e in cap["events"]
                                            if e["type"] == "DISPLACEMENT_CONFIRMED" and near(e, 0)), None),
            "liquidity_on_anchor": sorted(e["type"] for e in cap["events"] if near(e, 0) and
                                          e["type"].startswith(("BSL_", "SSL_", "EQH_", "EQL_")) and
                                          not e["type"].endswith(("_CREATED", "_DROPPED_MEMORY"))),
            "lrl_within_5": sorted([off(e["time"]), e["type"]] for e in cap["events"]
                                   if e["type"].startswith("LRL_") and near(e, 5)),
            "source": "the Pine log of the evidence capture"}


@pytest.mark.parametrize("cid", sorted(CASES))
def test_context_is_the_pine_log_and_never_changes_the_verdict(cid):
    case, w, k3 = CASES[cid], window(CASES[cid]), k3_of(CASES[cid])
    assert case["context"] == pine_context(case)
    alone = IstModel(Settings(modules=("fvg", "ifvg"))).run(w)
    every = IstModel(Settings.from_dict({"liq": {"preset": "balanced"},
                                         "modules": list(MODULES) + ["lrl", "cisd", "disp", "ifvg"]})).run(w)
    key = lambda m: [(r.side, r.bar, r.retest, r.ce, r.full, r.end) for r in m.ifvg.records() if r.parent_bar == k3]
    assert key(alone) == key(every)


@pytest.mark.parametrize("cid", sorted(CASES))
def test_bearish_bullish_mirror(cid):
    case, w, k3 = CASES[cid], window(CASES[cid]), k3_of(CASES[cid])
    h, mw = by_hand(w, k3), mirror(w, 0.0)
    hm = by_hand(mw, k3)
    assert (hm["dir"], hm["inversion"], hm.get("side"), hm.get("retest"), hm.get("end"), hm["rejections"]) == \
           (-h["dir"], h["inversion"], -h["side"] if "side" in h else None, h.get("retest"), h.get("end"), h["rejections"])
    m = IstModel(Settings(modules=("fvg", "ifvg"))).run(mw)
    r = _ifvg(m, k3)
    assert (r.side, r.bar, r.end) == (hm["side"], hm["inversion"], hm["end"]) if hm["inversion"] is not None else r is None


# ── the coverage the task asks for ──
SPECIAL = {"A": "bullish FVG → bearish IFVG", "B": "bearish FVG → bullish IFVG", "C": "wick beyond the far edge, close not beyond it: no inversion",
           "D": "close exactly on the boundary: no inversion", "E": "strict close beyond: inversion",
           "F": "immediate inversion (first eligible bar)", "G": "inversion after FIRST_TOUCH", "H": "inversion after CE",
           "I": "inversion after a full fill", "J": "inversion candle is DISPLACEMENT-R",
           "K": "inversion candle is not DISPLACEMENT-R", "L": "same-side CISD within 5 bars", "M": "no CISD within 5 bars",
           "N": "retest, still ACTIVE", "O": "full traversal with the close inside: still ACTIVE",
           "P": "strict close beyond the far edge: INVALIDATED", "Q": "facts before the end on one bar",
           "R": "invalidated and released by Phase 1 memory on one bar: the IFVG is still created"}


def _specials(case):
    """Each special letter, derived from the case (not from its labels)."""
    rec, ctx = recorded(case), case["context"]
    if case["kind"] != "case":
        return set()
    out = set()
    if rec["rejections"]:
        out |= {"C" if k == "wick" else "D" for _, k in rec["rejections"]}
    if rec["inversion"] is None:
        return out
    out |= {"A" if rec["side"] < 0 else "B", "E"}
    out.add("F" if rec["inversion"] == k3_of(case) + 1 else {"TOUCHED": "G", "CE": "H", "FULL": "I"}.get(rec["pre"], ""))
    out.add("J" if ctx["displacement_on_anchor"] == SIDE[rec["side"]] else "K")
    out.add("L" if ctx["same_side_cisd_within_5"] else "M" if not ctx["cisd_within_5"] else "")
    end = rec["end"]
    if rec["retest"] is not None and (end is None or rec["retest"] < end):
        out.add("N")
    if rec["traversal"] is not None and (end is None or rec["traversal"] < end):
        out.add("O")
    if end is not None:
        out.add("P")
        if end in (rec["retest"], rec["ifvg_ce"], rec["traversal"]):
            out.add("Q")
    return out - {""}


@pytest.mark.parametrize("cid", sorted(CASES))
def test_recorded_special_letters_are_the_derived_ones(cid):
    case = CASES[cid]
    assert set(case["special"]) == _specials(case)


def test_coverage_the_task_asks_for():
    got = {k: [cid for cid, c in CASES.items() if k in c["special"]] for k in SPECIAL}
    got["R"] = [cid for cid, c in ALL.items() if "R" in c.get("special", [])]
    assert all(got[k] for k in SPECIAL), [k for k in SPECIAL if not got[k]]
    clear = lambda s: [cid for cid, c in CASES.items() if c["category"].startswith(s)]
    assert len(clear("A ·")) >= 3 and len(clear("B ·")) >= 3 and len(clear("C ·")) >= 2 and len(clear("D ·")) >= 2
    assert len(got["P"]) >= 2 and len(set(got["N"]) | set(got["O"])) >= 2 and len(clear("S ·")) >= 2


# ── the mechanical case R, the memory golden, the H1 reference ──
def test_r_invalidated_and_released_on_one_bar_still_inverts():
    """Mechanical (synthetic candles: no real candle shows it, README): with Phase 1 memory 1 the FVG
    confirmed on bar 17 is invalidated on bar 18, where a new bullish FVG makes Phase 1 release it."""
    case = ALL["GOLD_IFVG_R1"]
    w = candles_of(case)
    s = Settings(modules=("fvg", "ifvg"), fvg=FvgSettings(memory=case["settings"]["fvg_memory"]))
    m = run_checked(w, s)
    e = case["expected"]
    assert any(x.type == "FVG_DROPPED_MEMORY" and x.bar == e["inversion_bar"] and x.dir == 1 for x in m.events)
    r = next(r for r in m.ifvg.records() if r.parent_bar == e["parent_bar"])
    assert (r.side, r.bar, r.bottom, r.top) == (-1, e["inversion_bar"], e["bottom"], e["top"])
    assert all(z.confirm_bar != e["parent_bar"] for z in m.fvg.records())       # gone from Phase 1, kept here
    same(w, FvgSettings(memory=case["settings"]["fvg_memory"]), IfvgSettings())


def test_memory_golden_real_log_and_mechanics():
    """The real v0.9.1-dev log keeps every ACTIVE IFVG over the 50 target and drops only INVALIDATED
    ones (tests/test_parity_v091_evidence.py checks every drop); here the recorded moments, and the
    mechanics on the same real candles with memory 2 under the invariant monitor (INV-IFVG-07: the oldest
    INVALIDATED first; INV-IFVG-09: never an ACTIVE one)."""
    case = ALL["GOLD_IFVG_MEM1"]
    cap = evidence(case["source"]["evidence"][0])
    from validation.parity.manual import _fmt
    ia = {_fmt(b["time"], case["timezone"]).replace(" ", "T"): b["ifvg"]["ia"] for b in cap["bars"] if b["ifvg"]}
    e = case["expected"]
    assert [ia[t] for t in e["first_over_50"]["around"]] == [tuple(x) for x in e["first_over_50"]["ia"]]
    assert ia[e["peak"]["time"]] == tuple(e["peak"]["ia"]) and max(v[1] for v in ia.values()) == e["peak"]["ia"][1]
    for d in e["ended_then_dropped_on_one_bar"]:
        evs = [x for x in cap["events"] if _fmt(x["sid"], case["timezone"]).replace(" ", "T") == d["id"] and x["dir"] == -1]
        when = lambda typ: [_fmt(x["time"], case["timezone"]).replace(" ", "T") for x in evs if x["type"] == typ]
        assert when("IFVG_INVALIDATED") == when("IFVG_DROPPED_MEMORY") == [d["time"]] and ia[d["time"]][1] > 50
    kinds = drop_kinds(cap)
    assert [kinds.count(k) for k in ("log", "snapshot", "before the snapshot", "ACTIVE")] == \
           [e["drops"][k] for k in ("invalidated_earlier_in_the_log", "invalidated_in_the_snapshot",
                                    "before_the_snapshot_not_observable", "active")]
    cs, mem = [b["candle"] for b in cap["bars"]], case["settings"]["mechanical_memory"]
    m = run_checked(cs, Settings(modules=("fvg", "ifvg"), ifvg=IfvgSettings(memory=mem)))
    big = IstModel(Settings(modules=("fvg", "ifvg"), ifvg=IfvgSettings(memory=10 ** 6))).run(cs)
    active = lambda x: {(r.side, r.id) for r in x.ifvg.records() if r.end is None}
    assert all(x.meta == "invalidated record" for x in m.events if x.type == "IFVG_DROPPED_MEMORY")
    assert active(m) == active(big) and len(m.ifvg.bear) > mem and all(r.end is None for r in m.ifvg.bear)


def test_h1_reference_supporting_only():
    """H1 (product image, pixel-digitised, no price axis): IFVG-R finds the bearish FVG of the drop's bar 21
    [708, 733] inverted by bar 22's close (736) into a bullish IFVG, 4 bars before the CISD of bar 26, the
    box unchanged, as the image shows. SUPPORTING: the digitised prices are not market data."""
    h1 = json.loads((GOLDEN_DIR / "human" / "GOLD_CISD_H1.json").read_text(encoding="utf-8"))
    w = candles_of(h1)
    m = IstModel(Settings.from_dict({"tick": 1.0, "modules": ["fvg", "ifvg", "cisd"]})).run(w)
    r = next(r for r in m.ifvg.records() if r.parent_bar == 21)
    assert (r.side, r.bar, r.bottom, r.top, w[22].close) == (1, 22, 708.0, 733.0, 736.0)
    # the drawn CISD (GOLD_CISD_H1 matches it as a subset: bar 5's is the window's first, not drawn)
    assert 26 in [x.bar for x in m.events if x.type == "CISD_CONFIRMED" and x.dir == 1]
    assert sorted(r.parent_bar for r in m.ifvg.records() if r.bar == 23) == [19, 20]
