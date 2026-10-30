"""Bounded Pine-Log parity for CISD (IST v0.7.0-dev): the capture lines IST.pine writes
(CISDSTATE / CISDSIDE / CISDREC snapshot after the first captured bar, CS / CU / CN / CA per bar,
CISD_* events with their audit text) and the comparison, on synthetic captures written from a
run over the WHOLE history (what Pine knows when it logs), cut to the last N + warm-up bars: the
window starts with an established delivery state."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from validation.candles import random_walk
from validation.models.cisd import CisdStack
from validation.models.events import EventLog
from validation.models.ist import IstModel
from validation.models.types import CisdSettings, Settings
from validation.parity import capture, manual
from validation.studies.lrl import nq_candles

pytestmark = [pytest.mark.cisd, pytest.mark.section("parity")]
TZ = "America/New_York"
S = Settings.from_dict({"liq": {"preset": "balanced"}})
W = max(S.fvg.lookback, S.liq.lookback + S.liq.right)
HEAD = ("CAPTURE|sym=CME_MINI:NQ1!|tf=1|tick=0.25|tz=America/New_York|confirmed=1|liq=1|preset=Balanced|left=5|right=3"
        "|k=1|w=30|eqtol=4|eqmin=2|liqmem=100|fvgticks=2|fvgtra=0.1|fvgrng=0|fvglen=14|fvgmem=50"
        "|ses=Asia@2000-0000,London@0200-0500,NY AM@0930-1200,NY PM@1330-1600"
        "|lrl=0|htf=0{cisd}|bars={n}|warmup={w}")
CISD_HEAD = "|cisd=1|cisdmem=50|cisdtra=14|cisdguard=200"


def _n(x):
    return "na" if x is None else (f"{x:.8f}".rstrip("0").rstrip(".") or "0")


def _i(x, off):
    return "na" if x is None else str(x + off)


def pine_capture(cs, n, off=10_000, memory=50, cisd=True) -> list[str]:
    """The Pine Logs messages for the last n + warm-up bars. Bar indices are shifted by `off`."""
    from validation.parity import oracle_series
    a = len(cs) - (n + W)
    series = oracle_series(cs, S, IstModel(S))
    main = {}
    for e in IstModel(S).run(cs).events:
        main.setdefault(e.bar, []).append(e)
    log = EventLog()
    m = CisdStack(CisdSettings(memory=memory), S.tick, log)
    out = [HEAD.format(cisd=CISD_HEAD if cisd else "", n=n, w=W)]
    for t, c in enumerate(cs):
        k = len(log.events)
        log.at(t, c.time)
        m.step(t, c)
        new = log.events[k:]
        if t < a:
            continue
        if t == a and cisd:
            out.append(f"CISDSTATE|state={m.delivery}|confirmed={m.confirmed}|dropped={m.dropped}")
            for g in (1, -1):
                sd = m.sides[g]
                rb, rt, rl = sd.run if sd.run else (None, None, None)
                d = ";".join(f"{b + off}:{tt}:{_n(lo)}:{o + off}:{ot}:{_n(lv)}" for b, tt, lo, o, ot, lv in sd.d)
                w = ";".join(f"{b + off}:{_n(lo)}" for b, lo in sd.w)
                out.append(f"CISDSIDE|side={g}|armed={int(sd.armed)}|a={sd.a + off}|since={sd.since + off}"
                           f"|known={_i(sd.known, off)}|run={int(sd.in_run)}|rb={_i(rb, off)}|rt={'na' if rt is None else rt}"
                           f"|rl={_n(rl)}|d={d}|w={w}")
            for r in m.recs:
                out.append(f"CISDREC|side={r.side}|id={r.id}|before={r.before}|level={_n(r.level)}|origin={r.origin + off}"
                           f"|eb={r.ext_bar + off}|et={cs[r.ext_bar].time}|ext={_n(r.ext)}|leg={_n(r.leg_ext)}"
                           f"|known={_i(r.known, off)}|bar={r.bar + off}|time={r.time}|close={_n(r.close)}|bk={_n(r.body_k)}"
                           f"|end={_i(r.end, off)}|rt={_i(r.retest, off)}|rc={_i(r.reclaim, off)}|br={_i(r.broken, off)}")
        ts = datetime.fromtimestamp(c.time / 1000, ZoneInfo(TZ)).strftime("%Y-%m-%dT%H:%M:%S%z")
        v = "|".join(f"{key}={_n(series[f][t])}" for key, f in capture.FIELDS.items())
        cand = lambda g: (lambda x: x if x == "off" else _n(x))(m.candidate(g))
        act = m.active
        cb = (f"|CS={m.delivery}|CU={cand(1)}|CN={cand(-1)}|CA={'na' if act is None else f'{act.side}:{act.id}'}"
              if cisd else "")
        out.append(f"BAR|{ts}|i={t + off}|O={_n(c.open)}|H={_n(c.high)}|L={_n(c.low)}|C={_n(c.close)}|{v}{cb}")
        out += [manual.pine_text(e, TZ) for e in main.get(t, []) + (new if cisd else [])]
    out.append(f"END|bars={len(cs) - a}")
    return out


def _cmp(lines):
    return capture.compare(capture.parse("\n".join(lines)))


def _diffs(r, sec="cisd"):
    return [c["text"] for c in r["checks"] if c["section"] == sec and c["status"] == manual.DIFF]


@pytest.fixture(scope="module")
def nq_lines():
    return pine_capture(nq_candles(), 300)


def test_faithful_capture_is_exact_from_an_established_state(nq_lines):
    state = next(x for x in nq_lines if x.startswith("CISDSTATE|"))
    assert "state=0" not in state                                   # the window starts mid-state
    r = _cmp(nq_lines)
    assert r["differences"] == 0, [c["text"] for c in r["checks"] if c["status"] == manual.DIFF][:5]
    c = r["cisd"]
    assert c["bars"] == len([x for x in nq_lines if x.startswith("BAR|")]) - 1 and c["events"] >= 15 and c["cold"] >= 10
    assert "CISD:" in capture.verdict(r) and "PASS" in capture.verdict(r)


@pytest.mark.parametrize("seed", [3, 5])
def test_faithful_walk_captures_with_memory_drops(seed):
    """≈ 225 CISDs on 2,500 bars: memory 50 drops records inside the window too."""
    r = _cmp(pine_capture(random_walk(2500, seed, gap_prob=0.02), 600))
    assert r["differences"] == 0, _diffs(r)[:5]
    assert any("CISD_DROPPED_MEMORY" in c["text"] for c in r["checks"] if c["status"] == manual.MATCH)


def test_replayed_with_pine_constants_and_flagged():
    """A capture made with other constants (memory 2) replays exactly with them; only the settings differ."""
    lines = pine_capture(random_walk(2500, 5, gap_prob=0.02), 600, memory=2)
    r = _cmp([lines[0].replace("|cisdmem=50", "|cisdmem=2")] + lines[1:])
    assert not _diffs(r) and [d for d in _diffs(r, "settings") if "CISD memory" in d]


def _edit(lines, pred, fn, nth=0):
    hits = [i for i, x in enumerate(lines) if pred(x)]
    out = list(lines)
    out[hits[nth]] = fn(out[hits[nth]])
    return out


def _shift_px(x):
    head, rest = x.split(" px=")
    px, tail = rest.split(" ", 1)
    return f"{head} px={float(px.replace(',', '')) + 0.25} {tail}"


def _after_snapshot(x, lines):
    return lines.index(x) > next(i for i, y in enumerate(lines) if y.startswith("BAR|")) + 1


ERRORS = {
    "wrong L": lambda ls: _edit(ls, lambda x: "CISD_CONFIRMED" in x and _after_snapshot(x, ls), _shift_px, 1),
    "wrong delivery state on a bar": lambda ls: _edit(ls, lambda x: x.startswith("BAR|") and "|CS=1|" in x,
                                                      lambda x: x.replace("|CS=1|", "|CS=-1|"), 5),
    "wrong candidate L": lambda ls: _edit(ls, lambda x: x.startswith("BAR|") and "|CU=" in x and "|CU=off" not in x
                                          and "|CU=na" not in x, lambda x: x.replace("|CU=", "|CU=1"), 3),
    "missing event": lambda ls: [x for i, x in enumerate(ls) if not (
        "CISD_CONFIRMED" in x and i == [k for k, y in enumerate(ls) if "CISD_CONFIRMED" in y and _after_snapshot(y, ls)][2])],
    "event logged twice": lambda ls: (lambda i: ls[:i + 1] + [ls[i]] + ls[i + 1:])(
        [k for k, y in enumerate(ls) if "CISD_CONFIRMED" in y and _after_snapshot(y, ls)][2]),
    "wrong extreme time": lambda ls: _edit(ls, lambda x: "CISD_CONFIRMED" in x and _after_snapshot(x, ls),
                                           lambda x: x.replace(" · et=", " · et=9"), 2),
    "wrong body / TR": lambda ls: _edit(ls, lambda x: "CISD_CONFIRMED" in x and _after_snapshot(x, ls) and "bk=na" not in x,
                                        lambda x: x.replace(" · bk=", " · bk=7"), 4),
    "corrupt snapshot (armed sides swapped)": lambda ls: [
        x.replace("|armed=1|", "|armed=X|").replace("|armed=0|", "|armed=1|").replace("|armed=X|", "|armed=0|")
        if x.startswith("CISDSIDE|") else x for x in ls],
    "corrupt snapshot (delivery state)": lambda ls: _edit(ls, lambda x: x.startswith("CISDSTATE|"),
                                                          lambda x: x.replace("state=-1", "state=1")),
    "wrong previous state": lambda ls: _edit(ls, lambda x: "CISD_CONFIRMED" in x and _after_snapshot(x, ls),
                                             lambda x: x.replace("prev=UP", "prev=UNKNOWN").replace("prev=DOWN", "prev=UNKNOWN"), 1),
}


@pytest.mark.parametrize("kind", sorted(ERRORS))
def test_each_error_kind_is_detected(nq_lines, kind):
    r = _cmp(ERRORS[kind](nq_lines))
    assert _diffs(r), kind


def test_settings_differ_when_pine_ran_other_constants(nq_lines):
    r = _cmp([nq_lines[0].replace("|cisdmem=50", "|cisdmem=60")] + nq_lines[1:])
    assert any("CISD memory" in d for d in _diffs(r, "settings"))


def test_a_build_without_cisd_is_not_compared():
    r = _cmp(pine_capture(nq_candles(), 300, cisd=False))
    assert r["cisd"] is None and r["differences"] == 0 and not [c for c in r["checks"] if c["section"] == "cisd"]
