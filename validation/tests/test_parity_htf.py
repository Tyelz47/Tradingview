"""Bounded Pine-Log parity for HTF FVG (IST v0.6.0-dev): the capture lines IST.pine writes
(HTFSTATE / HTFREC snapshot, HTFBAR per completed HTF candle, HO per bar, HTF_FVG_* events
with tf=) and the comparison, on synthetic captures written from the oracle's run over the
WHOLE history (what Pine knows when it logs), cut to the last N + warm-up bars."""
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from validation import PINE_SOURCE
from validation.candles import random_walk
from validation.models.ist import IstModel
from validation.models.types import Settings
from validation.parity import capture, manual
from validation.studies.lrl import nq_candles

pytestmark = [pytest.mark.htf, pytest.mark.section("parity")]
TZ = "America/New_York"
S = Settings.from_dict({"liq": {"preset": "balanced"}})
SH = Settings(modules=("htf",), fvg=S.fvg, tick=S.tick)
W = max(S.fvg.lookback, S.liq.lookback + S.liq.right)
HEAD = ("CAPTURE|sym=CME_MINI:NQ1!|tf=1|tick=0.25|tz=America/New_York|confirmed=1|liq=1|preset=Balanced|left=5|right=3"
        "|k=1|w=30|eqtol=4|eqmin=2|liqmem=100|fvgticks=2|fvgtra=0.1|fvgrng=0|fvglen=14|fvgmem=50"
        "|ses=Asia@2000-0000,London@0200-0500,NY AM@0930-1200,NY PM@1330-1600"
        "|lrl=0|htf=1|htftfs=15,30,60,240,D,W|htfmem=20|htfseeds=3|htfseedmem=20|bars={n}|warmup={w}")


def _n(x):
    return "na" if x is None else (f"{x:.8f}".rstrip("0").rstrip(".") or "0")


def _i(x, off):
    return "na" if x is None else str(x + off)


def pine_capture(cs, n, off=10_000) -> list[str]:
    """The Pine Logs messages for the last n + warm-up bars, from runs over every candle (Pine's
    full history). Bar indices are shifted by `off`, as on a real chart."""
    from validation.parity import oracle_series
    a = len(cs) - (n + W)
    series = oracle_series(cs, S, IstModel(S))
    main = {}
    for e in IstModel(S).run(cs).events:
        main.setdefault(e.bar, []).append(e)
    h = IstModel(SH)
    out = [HEAD.format(n=n, w=W)]
    for t, c in enumerate(cs):
        sizes = [len(side.bars) for side in h.hfvg.sides]
        new = h.step(c)
        if t < a:
            continue
        if t == a:
            for side in h.hfvg.sides:
                b3 = ";".join(f"{b.time}:{_n(b.open)}:{_n(b.high)}:{_n(b.low)}:{_n(b.close)}:{_n(b.tra)}:{_n(b.rng)}"
                              for b in side.bars[-3:])
                out.append(f"HTFSTATE|tf={side.tf}|last={_i(side.last_c3, 0)}|bars={b3}")
                for r in side.recs:
                    out.append(f"HTFREC|tf={side.tf}|dir={r.dir}|id={r.id}|c1={r.c1_time}|top={_n(r.top)}|bottom={_n(r.bottom)}"
                               f"|known={r.known_bar + off}|kt={r.known_time}|seeded={int(r.seeded)}|pt={int(r.pre_touch)}"
                               f"|pc={int(r.pre_ce)}|touch={_i(r.touch_bar, off)}|ce={_i(r.ce_bar, off)}"
                               f"|full={_i(r.full_bar, off)}|inv={_i(r.inv_bar, off)}|invc={_n(r.inv_close)}")
        for side, k in zip(h.hfvg.sides, sizes):
            if len(side.bars) > k:
                b = side.bars[-1]
                out.append(f"HTFBAR|tf={side.tf}|i={t + off}|t={b.time}|O={_n(b.open)}|H={_n(b.high)}|L={_n(b.low)}"
                           f"|C={_n(b.close)}|tra={_n(b.tra)}|rng={_n(b.rng)}")
        ts = datetime.fromtimestamp(c.time / 1000, ZoneInfo(TZ)).strftime("%Y-%m-%dT%H:%M:%S%z")
        v = "|".join(f"{k}={_n(series[f][t])}" for k, f in capture.FIELDS.items())
        ho = ",".join(f"{side.tf}:{sum(r.inv_bar is None for r in side.recs)}" for side in h.hfvg.sides)
        out.append(f"BAR|{ts}|i={t + off}|O={_n(c.open)}|H={_n(c.high)}|L={_n(c.low)}|C={_n(c.close)}|{v}|HO={ho}")
        out += [manual.pine_text(e, TZ) for e in main.get(t, []) + new]
    out.append(f"END|bars={len(cs) - a}")
    return out


def _cmp(lines):
    return capture.compare(capture.parse("\n".join(lines)))


def _diffs(r):
    return [c["text"] for c in r["checks"] if c["status"] == manual.DIFF]


def test_pine_capture_lines_carry_htf():
    """IST.pine writes every HTF key this parser reads."""
    src = PINE_SOURCE.read_text(encoding="utf-8")
    line = lambda tok: next(ln for ln in src.splitlines() if f'log.info("{tok}|' in ln)
    assert all(k in line("CAPTURE") for k in ("|htf=1|htftfs=", "|htfmem=", "|htfseeds=", "|htfseedmem="))
    assert all(f'|{k}=" ' in line("HTFSTATE") for k in ("tf", "last", "bars"))
    assert all(f'|{k}=" ' in line("HTFREC") for k in ("tf", "dir", "id", "c1", "top", "bottom", "known", "kt", "seeded",
                                                       "pt", "pc", "touch", "ce", "full", "inv", "invc"))
    assert all(f'|{k}=" ' in line("HTFBAR") for k in ("tf", "i", "t", "O", "H", "L", "C", "tra", "rng"))
    assert '"|HO=" + f_htfOpen()' in line("BAR")


@pytest.mark.parametrize("which, n", [("nq", 1000), ("walk", 1500), ("walk", 400)])
def test_htf_parity_passes_on_a_faithful_capture(which, n):
    cs = nq_candles() if which == "nq" else random_walk(4000, 3, gap_prob=0.02)
    r = _cmp(pine_capture(cs, n))
    assert not _diffs(r), _diffs(r)[:5]
    htf = r["htf"]
    assert htf["candles"] > n // 15 and htf["events"] > 5 and htf["open_bars"] == n + W - 1
    assert htf["not_observable"] > 0                     # HTF candles that started before the window


def _edit(lines, pick, new):
    i = next(k for k, ln in enumerate(lines) if pick(ln))
    return lines[:i] + [new(lines[i])] + lines[i + 1:]


@pytest.mark.parametrize("what", ["candle high", "candle time", "missing candle", "missing event", "timeframe",
                                  "open count", "snapshot record", "zone geometry"])
def test_htf_differences_are_detected(what):
    lines = pine_capture(random_walk(4000, 3, gap_prob=0.02), 1500)
    later = lambda ln: ln.startswith("HTFBAR|tf=15|") and lines.index(ln) > 200
    if what == "candle high":
        bad = _edit(lines, later, lambda ln: re.sub(r"\|H=([\d.]+)", lambda m: f"|H={_n(float(m[1]) + 0.25)}", ln))
    elif what == "candle time":
        bad = _edit(lines, later, lambda ln: re.sub(r"\|t=(\d+)", lambda m: f"|t={int(m[1]) + 60_000}", ln))
    elif what == "missing candle":
        bad = [ln for ln in lines if ln is not next(x for x in lines if later(x))]
    elif what == "missing event":
        i = [k for k, ln in enumerate(lines) if " HTF_FVG_FIRST_TOUCH " in ln][-1]
        bad = lines[:i] + lines[i + 1:]
    elif what == "timeframe":
        bad = _edit(lines, lambda ln: " HTF_FVG_CREATED " in ln and "tf=15m" in ln and lines.index(ln) > 200,
                    lambda ln: ln.replace("tf=15m", "tf=30m"))
    elif what == "open count":
        bad = _edit(lines, lambda ln: ln.startswith("BAR|") and lines.index(ln) > 300,
                    lambda ln: re.sub(r"\|HO=15:(\d+)", lambda m: f"|HO=15:{int(m[1]) + 1}", ln))
    elif what == "snapshot record":
        bad = _edit(lines, lambda ln: ln.startswith("HTFREC|tf=15|") and "|inv=na|" in ln and "|full=na|" in ln,
                    lambda ln: ln.replace("|inv=na|", "|inv=9000|"))
    else:
        bad = _edit(lines, lambda ln: " HTF_FVG_CREATED " in ln and lines.index(ln) > 200,
                    lambda ln: re.sub(r"top=([\d.]+)", lambda m: f"top={_n(float(m[1]) + 0.25)}", ln))
    assert bad != lines
    assert _diffs(_cmp(bad)), what


def test_parser_reads_the_snapshot():
    cap = capture.parse("\n".join(pine_capture(random_walk(4000, 3, gap_prob=0.02), 400)))
    st = {x["tf"]: x for x in cap["htf"]["HTFSTATE"]}
    assert set(st) == {"15", "30", "60", "240", "D", "W"} and len(st["15"]["bars"]) == 3 and st["15"]["last"] > 0
    assert cap["htf"]["HTFREC"] and cap["htf"]["HTFBAR"]
    ev = [e for e in cap["events"] if e["type"].startswith("HTF_")]
    assert ev and all(e["tf"] in ("15", "30", "60", "240", "D", "W") and e["dir"] in (1, -1) for e in ev)
