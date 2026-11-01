"""Bounded Pine-Log parity for displacement (IST v0.8.0-dev): the capture lines IST.pine writes
(disp=1 and the four constants in CAPTURE; DISPSTATE / DISPREC after captured bar tra_len + 1;
DS / DA / DK / DP / DF per bar; DISPLACEMENT_* events with their audit text) and the comparison,
on synthetic captures written from Pine's formulation (DispPine) run over the WHOLE history (what
Pine knows when it logs), cut to the last N + warm-up bars."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from validation.candles import random_walk
from validation.models.displacement import DispPine
from validation.models.events import EventLog
from validation.models.ist import IstModel
from validation.models.types import DispSettings, Settings
from validation.parity import capture, manual, oracle_series
from validation.studies.lrl import nq_candles

pytestmark = [pytest.mark.disp, pytest.mark.section("parity")]
TZ = "America/New_York"
S = Settings.from_dict({"liq": {"preset": "balanced"}})
W = max(S.fvg.lookback, S.liq.lookback + S.liq.right)
HEAD = ("CAPTURE|build=v0.8.0-dev|sym=CME_MINI:NQ1!|tf=1|tick=0.25|tz=America/New_York|confirmed=1|liq=1|preset=Balanced"
        "|left=5|right=3|k=1|w=30|eqtol=4|eqmin=2|liqmem=100|fvgticks=2|fvgtra=0.1|fvgrng=0|fvglen=14|fvgmem=50"
        "|ses=Asia@2000-0000,London@0200-0500,NY AM@0930-1200,NY PM@1330-1600"
        "|lrl=0|htf=0|cisd=0{disp}|bars={n}|warmup={w}")
DISP_HEAD = "|disp=1|dispk=1.5|dispclose=0.75|disptr=14|dispmem={mem}"


def _n(x):
    return "na" if x is None else (f"{x:.8f}".rstrip("0").rstrip(".") or "0")


def pine_capture(cs, n, off=10_000, memory=50, disp=True) -> list[str]:
    """The Pine Logs messages for the last n + warm-up bars. Bar indices are shifted by `off`."""
    a = len(cs) - (n + W)
    series = oracle_series(cs, S, IstModel(S))
    main = {}
    for e in IstModel(S).run(cs).events:
        main.setdefault(e.bar, []).append(e)
    log = EventLog()
    m = DispPine(DispSettings(memory=memory), S.tick, log)
    out = [HEAD.format(disp=DISP_HEAD.format(mem=memory) if disp else "", n=n, w=W)]
    for t, c in enumerate(cs):
        k = len(log.events)
        log.at(t, c.time)
        m.step(t, c)
        new = log.events[k:]
        if t < a:
            continue
        if disp and t == a + 15:                        # IST.pine: capDone == DISP_TRA_LEN + 1
            out.append(f"DISPSTATE|at={t + off}|confirmed={m.confirmed}|dropped={m.dropped}")
            out += [f"DISPREC|side={r.side}|id={r.id}|bar={r.bar + off}|O={_n(r.o)}|H={_n(r.h)}|L={_n(r.l)}|C={_n(r.c)}"
                    f"|tra={_n(r.tra)}|body={_n(r.body)}|rng={_n(r.rng)}|bk={_n(r.body_k)}|rk={_n(r.range_k)}"
                    f"|cp={_n(r.clv)}|prev={_n(r.prev_ext)}|fvg={r.fvg}" for r in m.recs]
        ts = datetime.fromtimestamp(c.time / 1000, ZoneInfo(TZ)).strftime("%Y-%m-%dT%H:%M:%S%z")
        v = "|".join(f"{key}={_n(series[f][t])}" for key, f in capture.FIELDS.items())
        da, dk, dp, df = m.bar_values(t)
        db = f"|DS={m.side}|DA={_n(da)}|DK={_n(dk)}|DP={_n(dp)}|DF={'na' if df is None else df}" if disp else ""
        out.append(f"BAR|{ts}|i={t + off}|O={_n(c.open)}|H={_n(c.high)}|L={_n(c.low)}|C={_n(c.close)}|{v}{db}")
        out += [manual.pine_text(e, TZ) for e in main.get(t, []) + (new if disp else [])]
    out.append(f"END|bars={len(cs) - a}")
    return out


def _cmp(lines):
    return capture.compare(capture.parse("\n".join(lines)))


def _diffs(r, sec="disp"):
    return [c["text"] for c in r["checks"] if c["section"] == sec and c["status"] == manual.DIFF]


@pytest.fixture(scope="module")
def nq_lines():
    return pine_capture(nq_candles(), 600)


def test_faithful_capture_is_exact(nq_lines):
    r = _cmp(nq_lines)
    assert r["differences"] == 0, [c["text"] for c in r["checks"] if c["status"] == manual.DIFF][:5]
    d = r["disp"]
    assert d["bars"] == len([x for x in nq_lines if x.startswith("BAR|")]) - 16 and d["events"] >= 15
    assert d["records"] == len([x for x in nq_lines if x.startswith("DISPREC|")]) >= 30
    assert "DISP:" in capture.verdict(r) and "PASS" in capture.verdict(r)
    assert any("DISPLACEMENT_CONFIRMED" in c["text"] for c in r["checks"] if c["status"] == manual.MATCH)


@pytest.mark.parametrize("seed", [3, 5])
def test_faithful_walk_captures_with_memory_drops(seed):
    """≈ 400 displacements on 4,000 walk bars: memory 50 drops records inside the window too."""
    r = _cmp(pine_capture(random_walk(4000, seed, gap_prob=0.02), 1500))
    assert r["differences"] == 0, _diffs(r)[:5]
    assert any("DISPLACEMENT_DROPPED_MEMORY" in c["text"] for c in r["checks"] if c["status"] == manual.MATCH)


def test_replayed_with_pine_constants_and_flagged():
    """A capture made with memory 2 replays exactly with it; only the settings differ."""
    lines = pine_capture(random_walk(2500, 5, gap_prob=0.02), 600, memory=2)
    r = _cmp(lines)
    assert not _diffs(r) and [d for d in _diffs(r, "settings") if "displacement memory" in d]


def _edit(lines, pred, fn, nth=0):
    hits = [i for i, x in enumerate(lines) if pred(x)]
    out = list(lines)
    out[hits[nth]] = fn(out[hits[nth]])
    return out


def _after(x, lines):
    return lines.index(x) > next(i for i, y in enumerate(lines) if y.startswith("DISPSTATE|"))


def _field(x, key, fn):
    head, rest = x.split(f"|{key}=", 1)
    val, tail = (rest.split("|", 1) + [""])[:2]
    return f"{head}|{key}={fn(val)}" + (f"|{tail}" if tail else "")


def _meta(x, key, fn):
    head, rest = x.split(f" · {key}=", 1)
    val, tail = (rest.split(" · ", 1) + [""])[:2]
    return f"{head} · {key}={fn(val)}" + (f" · {tail}" if tail else "")


CONF = lambda ls: (lambda x: "DISPLACEMENT_CONFIRMED" in x and _after(x, ls))
ERRORS = {
    "a displacement bar logged as none": lambda ls: _edit(ls, lambda x: x.startswith("BAR|") and "|DS=1|" in x and _after(x, ls),
                                                          lambda x: x.replace("|DS=1|", "|DS=0|"), 2),
    "a plain bar logged as a displacement": lambda ls: _edit(ls, lambda x: x.startswith("BAR|") and "|DS=0|" in x and _after(x, ls),
                                                             lambda x: x.replace("|DS=0|", "|DS=-1|"), 7),
    "wrong A": lambda ls: _edit(ls, lambda x: x.startswith("BAR|") and "|DA=" in x and _after(x, ls),
                                lambda x: _field(x, "DA", lambda v: _n(float(v) + 0.01)), 30),
    "wrong body / A": lambda ls: _edit(ls, lambda x: x.startswith("BAR|") and "|DK=" in x and "|DK=na" not in x and _after(x, ls),
                                       lambda x: _field(x, "DK", lambda v: _n(float(v) + 0.5)), 9),
    "wrong close position": lambda ls: _edit(ls, lambda x: x.startswith("BAR|") and "|DP=na" not in x and _after(x, ls),
                                             lambda x: _field(x, "DP", lambda v: _n(1 - float(v) / 2)), 11),
    "wrong FVG metadata": lambda ls: _edit(ls, lambda x: x.startswith("BAR|") and ("|DF=1" in x or "|DF=-1" in x) and _after(x, ls),
                                           lambda x: x.replace("|DF=1", "|DF=X").replace("|DF=-1", "|DF=1").replace("|DF=X", "|DF=-1"), 1),
    "missing event": lambda ls: (lambda i: ls[:i] + ls[i + 1:])([k for k, y in enumerate(ls) if CONF(ls)(y)][3]),
    "event logged twice": lambda ls: (lambda i: ls[:i + 1] + [ls[i]] + ls[i + 1:])([k for k, y in enumerate(ls) if CONF(ls)(y)][3]),
    "wrong close (px)": lambda ls: _edit(ls, CONF(ls), lambda x: x.replace(" px=", " px=1"), 2),
    "wrong body / A in the event": lambda ls: _edit(ls, CONF(ls), lambda x: _meta(x, "bk", lambda v: _n(float(v) + 1)), 2),
    "wrong range / A in the event": lambda ls: _edit(ls, CONF(ls), lambda x: _meta(x, "rk", lambda v: _n(float(v) + 1)), 4),
    "wrong close position in the event": lambda ls: _edit(ls, CONF(ls), lambda x: _meta(x, "cp", lambda v: "0.5"), 5),
    "wrong previous extreme in the event": lambda ls: _edit(ls, CONF(ls), lambda x: _meta(x, "prev", lambda v: _n(float(v) + 0.25)), 6),
    "corrupt snapshot record candle": lambda ls: _edit(ls, lambda x: x.startswith("DISPREC|"),
                                                       lambda x: _field(x, "C", lambda v: _n(float(v) + 0.25)), -1),
    "no snapshot": lambda ls: [x for x in ls if not x.startswith("DISPSTATE|")],
}


@pytest.mark.parametrize("kind", sorted(ERRORS))
def test_each_error_kind_is_detected(nq_lines, kind):
    r = _cmp(ERRORS[kind](nq_lines))
    assert _diffs(r), kind


def test_settings_differ_when_pine_ran_other_constants(nq_lines):
    for key, bad in (("dispk=1.5", "dispk=1.25"), ("dispclose=0.75", "dispclose=0.7"), ("disptr=14", "disptr=20")):
        r = _cmp([nq_lines[0].replace(key, bad)] + nq_lines[1:])
        assert _diffs(r, "settings"), key


def test_a_build_without_displacement_is_not_compared():
    r = _cmp(pine_capture(nq_candles(), 300, disp=False))
    assert r["disp"] is None and r["differences"] == 0 and not [c for c in r["checks"] if c["section"] == "disp"]
