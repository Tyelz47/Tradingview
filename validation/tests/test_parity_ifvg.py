"""Bounded Pine-Log parity for IFVG (IST v0.9.1-dev): the capture lines IST.pine writes (ifvg=1 and
ifvgmem in CAPTURE; IFVGSTATE / FVGREC / IFVGREC after captured bar fvglen + 2; IS / IA / IX per bar;
IFVG_* events with their audit text) and the comparison, on synthetic captures written from Pine's
formulation (IfvgPine over the Phase 1 FVG engine) run over the WHOLE history (what Pine knows when it
logs), cut to the last N + warm-up bars."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from validation.candles import random_walk
from validation.models.events import EventLog
from validation.models.fvg import FvgEngine
from validation.models.ifvg import IfvgPine
from validation.models.ist import IstModel
from validation.models.types import IfvgSettings, Settings
from validation.parity import capture, manual, oracle_series
from validation.studies.lrl import nq_candles

pytestmark = [pytest.mark.ifvg, pytest.mark.section("parity")]
TZ = "America/New_York"
S = Settings.from_dict({"liq": {"preset": "balanced"}})
W = max(S.fvg.lookback, S.liq.lookback + S.liq.right)
HEAD = ("CAPTURE|build=v0.9.1-dev|sym=CME_MINI:NQ1!|tf=1|tick=0.25|tz=America/New_York|confirmed=1|liq=1|preset=Balanced"
        "|left=5|right=3|k=1|w=30|eqtol=4|eqmin=2|liqmem=100|fvgticks=2|fvgtra=0.1|fvgrng=0|fvglen=14|fvgmem=50"
        "|ses=Asia@2000-0000,London@0200-0500,NY AM@0930-1200,NY PM@1330-1600"
        "|lrl=0|htf=0|cisd=0|disp=0{ifvg}|bars={n}|warmup={w}")


def _n(x):
    return "na" if x is None else (f"{x:.8f}".rstrip("0").rstrip(".") or "0")


def _i(x, off):
    return "na" if x is None else str(x + off)


def pine_capture(cs, n, off=10_000, memory=50, ifvg=True) -> list[str]:
    """The Pine Logs messages for the last n + warm-up bars. Bar indices are shifted by `off`."""
    a = len(cs) - (n + W)
    series = oracle_series(cs, S, IstModel(S))
    main = {}
    for e in IstModel(S).run(cs).events:
        main.setdefault(e.bar, []).append(e)
    log = EventLog()
    f = FvgEngine(S.fvg, S.tick, log)
    m = IfvgPine(IfvgSettings(memory=memory), S.tick, log, f)
    out = [HEAD.format(ifvg=f"|ifvg=1|ifvgmem={memory}" if ifvg else "", n=n, w=W)]
    for t, c in enumerate(cs):
        k = len(log.events)
        log.at(t, c.time)
        f.step(t, c)
        m.step(t, c)
        new = [e for e in log.events[k:] if e.type.startswith("IFVG_")]
        if t < a:
            continue
        if ifvg and t == a + S.fvg.length + 2:          # IST.pine: capDone == fvgLen + 2
            sh = ";".join(f"{z.id}:{z.dir}" for z in m.shadows)
            out.append(f"IFVGSTATE|at={t + off}|inverted={m.inverted}|dropped={m.dropped}|sh={sh}")
            out += [f"FVGREC|dir={z.dir}|id={z.id}|ob={z.origin_bar + off}|ot={z.origin_time}|cb={z.confirm_bar + off}"
                    f"|top={_n(z.top)}|bottom={_n(z.bottom)}|mid={_n(z.mid)}|ext={_n(z.extreme)}|touch={_i(z.touch_bar, off)}"
                    f"|ce={_i(z.ce_bar, off)}|full={_i(z.full_bar, off)}|inv={_i(z.inv_bar, off)}" for z in f.bull + f.bear]
            out += [f"IFVGREC|side={r.side}|id={r.id}|ob={r.origin_bar + off}|ot={r.origin_time}|pb={r.parent_bar + off}"
                    f"|top={_n(r.top)}|bottom={_n(r.bottom)}|mid={_n(r.mid)}|bar={r.bar + off}|time={r.time}"
                    f"|close={_n(r.close)}|pre={r.pre}|touch={_i(r.touch_bar, off)}|ce={_i(r.ce_bar, off)}"
                    f"|full={_i(r.full_bar, off)}|end={_i(r.end_bar, off)}|endc={_n(r.end_close)}" for r in m.records()]
        ts = datetime.fromtimestamp(c.time / 1000, ZoneInfo(TZ)).strftime("%Y-%m-%dT%H:%M:%S%z")
        v = "|".join(f"{key}={_n(series[fl][t])}" for key, fl in capture.FIELDS.items())
        b = m.bar_values(t)
        ib = f"|IS={b['is'][0]}:{b['is'][1]}|IA={b['ia'][0]}:{b['ia'][1]}|IX={b['ix']}" if ifvg else ""
        out.append(f"BAR|{ts}|i={t + off}|O={_n(c.open)}|H={_n(c.high)}|L={_n(c.low)}|C={_n(c.close)}|{v}{ib}")
        out += [manual.pine_text(e, TZ) for e in main.get(t, []) + (new if ifvg else [])]
    out.append(f"END|bars={len(cs) - a}")
    return out


def _cmp(lines):
    return capture.compare(capture.parse("\n".join(lines)))


def _diffs(r, sec="ifvg"):
    return [c["text"] for c in r["checks"] if c["section"] == sec and c["status"] == manual.DIFF]


@pytest.fixture(scope="module")
def nq_lines():
    return pine_capture(nq_candles(), 600)


def test_faithful_capture_is_exact(nq_lines):
    r = _cmp(nq_lines)
    assert r["differences"] == 0, [c["text"] for c in r["checks"] if c["status"] == manual.DIFF][:5]
    d = r["ifvg"]
    assert d["bars"] == len([x for x in nq_lines if x.startswith("BAR|")]) - (S.fvg.length + 3) and d["events"] >= 100
    assert d["records"] == len([x for x in nq_lines if x.startswith("IFVGREC|")]) >= 50
    assert "IFVG:" in capture.verdict(r) and "PASS" in capture.verdict(r)
    ok = {c["text"].split(":")[0] for c in r["checks"] if c["section"] == "ifvg" and c["status"] == manual.MATCH}
    assert {"IFVG_INVERTED", "IFVG_FIRST_TOUCH", "IFVG_INVALIDATED", "IFVG_DROPPED_MEMORY"} <= ok


@pytest.mark.parametrize("seed", [3, 5])
def test_faithful_walk_captures(seed):
    r = _cmp(pine_capture(random_walk(4000, seed, gap_prob=0.02), 1500))
    assert r["differences"] == 0, _diffs(r)[:5]


def test_replayed_with_pine_memory_and_flagged():
    """A capture made with memory 2 replays exactly with it; only the settings differ."""
    r = _cmp(pine_capture(random_walk(2500, 5, gap_prob=0.02), 600, memory=2))
    assert not _diffs(r) and [d for d in _diffs(r, "settings") if "IFVG memory" in d]


def _edit(lines, pred, fn, nth=0):
    hits = [i for i, x in enumerate(lines) if pred(x)]
    out = list(lines)
    out[hits[nth]] = fn(out[hits[nth]])
    return out


def _after(x, lines):
    return lines.index(x) > next(i for i, y in enumerate(lines) if y.startswith("IFVGSTATE|"))


def _field(x, key, fn):
    head, rest = x.split(f"|{key}=", 1)
    val, tail = (rest.split("|", 1) + [""])[:2]
    return f"{head}|{key}={fn(val)}" + (f"|{tail}" if tail else "")


def _meta(x, key, fn):
    head, rest = x.split(f" · {key}=", 1)
    val, tail = (rest.split(" · ", 1) + [""])[:2]
    return f"{head} · {key}={fn(val)}" + (f" · {tail}" if tail else "")


BAR = lambda ls: (lambda x: x.startswith("BAR|") and _after(x, ls))
EV = lambda ls, typ: (lambda x: f"{typ} " in x and _after(x, ls))
ERRORS = {
    "a shadow missing": lambda ls: _edit(ls, BAR(ls), lambda x: _field(x, "IS", lambda v: f"{int(v.split(':')[0]) - 1}:{v.split(':')[1]}"), 40),
    "a wrong shadow": lambda ls: _edit(ls, BAR(ls), lambda x: _field(x, "IS", lambda v: f"{v.split(':')[0]}:{int(v.split(':')[1]) + 60}"), 41),
    "wrong active count": lambda ls: _edit(ls, BAR(ls), lambda x: _field(x, "IA", lambda v: f"{int(v.split(':')[0]) + 1}:{v.split(':')[1]}"), 42),
    "a CE / full fact missing": lambda ls: _edit(ls, lambda x: x.startswith("BAR|") and "|IX=C" in x and _after(x, ls),
                                                 lambda x: _field(x, "IX", lambda v: "-"), 2),
    "a fact on the wrong bar": lambda ls: _edit(ls, lambda x: x.startswith("BAR|") and "|IX=-" in x and _after(x, ls),
                                                lambda x: _field(x, "IX", lambda v: "C1,"), 5),
    "missing inversion": lambda ls: (lambda i: ls[:i] + ls[i + 1:])([k for k, y in enumerate(ls) if EV(ls, "IFVG_INVERTED")(y)][3]),
    "inversion logged twice": lambda ls: (lambda i: ls[:i + 1] + [ls[i]] + ls[i + 1:])(
        [k for k, y in enumerate(ls) if EV(ls, "IFVG_INVERTED")(y)][3]),
    "missing invalidation": lambda ls: (lambda i: ls[:i] + ls[i + 1:])([k for k, y in enumerate(ls) if EV(ls, "IFVG_INVALIDATED")(y)][2]),
    "wrong retest price": lambda ls: _edit(ls, EV(ls, "IFVG_FIRST_TOUCH"), lambda x: x.replace(" px=", " px=1"), 2),
    "wrong side": lambda ls: _edit(ls, EV(ls, "IFVG_INVERTED"), lambda x: x.replace(" BEAR ", " BULL ") if " BEAR " in x
                                   else x.replace(" BULL ", " BEAR "), 4),
    "wrong geometry in the event": lambda ls: _edit(ls, EV(ls, "IFVG_INVERTED"), lambda x: _meta(x, "top", lambda v: _n(float(v) + 0.25)), 2),
    "wrong prior state in the event": lambda ls: _edit(ls, EV(ls, "IFVG_INVERTED"),
                                                       lambda x: _meta(x, "pre", lambda v: "CE" if v != "CE" else "FULL"), 3),
    "corrupt snapshot record": lambda ls: _edit(ls, lambda x: x.startswith("IFVGREC|"),
                                                lambda x: _field(x, "mid", lambda v: _n(float(v) + 0.25)), -1),
    "shadows not the open FVGs": lambda ls: _edit(ls, lambda x: x.startswith("IFVGSTATE|"),
                                                  lambda x: _field(x, "sh", lambda v: v.split(";", 1)[1])),
    "a Phase 1 geometry changed in the snapshot": lambda ls: _edit(ls, lambda x: x.startswith("FVGREC|") and "|inv=na" in x,
                                                                   lambda x: _field(x, "top", lambda v: _n(float(v) + 5))),
    "an invalidated Phase 1 FVG logged open": lambda ls: _edit(ls, lambda x: x.startswith("FVGREC|") and "|inv=na" not in x,
                                                               lambda x: _field(x, "inv", lambda v: "na"), -1),
    "no snapshot": lambda ls: [x for x in ls if not x.startswith("IFVGSTATE|")],
}


@pytest.mark.parametrize("kind", sorted(ERRORS))
def test_each_error_kind_is_detected(nq_lines, kind):
    r = _cmp(ERRORS[kind](nq_lines))
    assert _diffs(r), kind


def test_a_build_without_ifvg_is_not_compared():
    r = _cmp(pine_capture(nq_candles(), 300, ifvg=False))
    assert r["ifvg"] is None and r["differences"] == 0 and not [c for c in r["checks"] if c["section"] == "ifvg"]
