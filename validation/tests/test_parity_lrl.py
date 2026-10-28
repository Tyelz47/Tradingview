"""Bounded Pine-Log parity for LRL (IST v0.5.0-dev): the capture format IST.pine writes,
and the comparison, on synthetic captures written from the oracle's run over the WHOLE
history (what Pine knows when it logs), cut to the last N + warm-up bars, so LRLs that
started before the window, and everything they touch, really are invisible to the bounded
oracle."""
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from validation import PINE_SOURCE
from validation.candles import random_walk
from validation.models.ist import IstModel
from validation.models.types import MODULES, LrlSettings, Settings
from validation.parity import capture, manual, oracle_series
from validation.studies import lrl as study

pytestmark = [pytest.mark.lrl, pytest.mark.section("parity")]
TZ = "America/New_York"
S = Settings.from_dict({"liq": {"preset": "balanced"}, "modules": [*MODULES, "lrl"]})
HEAD = ("CAPTURE|sym=CME_MINI:NQ1!|tf=1|tick=0.25|tz=America/New_York|confirmed=1|liq=1|preset=Balanced|left=5|right=3"
        "|k=1|w=30|eqtol=4|eqmin=2|liqmem=100|fvgticks=2|fvgtra=0.1|fvgrng=0|fvglen=14|fvgmem=50"
        "|ses=Asia@2000-0000,London@0200-0500,NY AM@0930-1200,NY PM@1330-1600"
        "|lrl=1|lrlleft=3|lrlright=2|lrltol=0.5|lrlgap=30|lrlsep=1|lrldrop=2|lrltra=14|lrlcand=25|lrlmem=50"
        "|bars={n}|warmup={w}")


def _n(x):
    return "na" if x is None else (f"{x:.8f}".rstrip("0").rstrip(".") or "0")


def warm() -> int:
    """Pine capWarm with LRL ON: max(FVG, swing, LRL) dependency graphs = 76 for Balanced."""
    return max(S.fvg.lookback, S.liq.lookback + S.liq.right, S.lrl.lookback)


def pine_capture(cs, n, a=None) -> list[str]:
    """The Pine Logs messages for bars a … end (default: the last n + warm-up), from a run over
    every candle (Pine's full history)."""
    w = warm()
    a = len(cs) - (n + w) if a is None else a
    n = len(cs) - a - w
    m = IstModel(S)
    series = oracle_series(cs, S, m)
    by_bar = {}
    for e in m.events:
        by_bar.setdefault(e.bar, []).append(e)
    lrl = lambda d: ";".join(f"{i}:{_n(v[0])}:{_n(v[1])}" for i, v in d.items())
    out = [HEAD.format(n=n, w=w)]
    for t in range(a, len(cs)):
        c = cs[t]
        ts = datetime.fromtimestamp(c.time / 1000, ZoneInfo(TZ)).strftime("%Y-%m-%dT%H:%M:%S%z")
        v = "|".join(f"{k}={_n(series[f][t])}" for k, f in capture.FIELDS.items())
        out.append(f"BAR|{ts}|i={t}|O={_n(c.open)}|H={_n(c.high)}|L={_n(c.low)}|C={_n(c.close)}|{v}"
                   f"|LH={lrl(series['lrl_high'][t])}|LL={lrl(series['lrl_low'][t])}"
                   f"|KH={series['lrl_cand_high'][t]}|KL={series['lrl_cand_low'][t]}")
        out += [manual.pine_text(e, TZ) for e in by_bar.get(t, [])]
    out.append(f"END|bars={len(cs) - a}")
    return out


def _cmp(lines):
    return capture.compare(capture.parse("\n".join(lines)))


def _diffs(r):
    return [c["text"] for c in r["checks"] if c["status"] == manual.DIFF]


def test_warm_up_comes_from_the_lrl_dependencies():
    """right + 2 × gap + TR length = 2 + 60 + 14 = 76, in the oracle and in IST.pine capWarm."""
    assert LrlSettings().lookback == 76 and warm() == 76
    src = PINE_SOURCE.read_text(encoding="utf-8")
    assert re.search(r"^int\s+capWarm\s+=\s+math\.max\(fvgLen \+ 2, math\.max\(LIQ_TRA_LEN, LIQ_L, LIQ_W\) \+ LIQ_R, "
                     r"lrlOn \? LRL_R \+ 2 \* LRL_GAP \+ LRL_TRA_LEN : 0\)", src, re.M)


def test_pine_capture_lines_carry_lrl():
    """IST.pine writes every LRL key this parser reads: the frozen constants on the CAPTURE
    line, and LH / LL / KH / KL on every BAR line (LRL ON)."""
    src = PINE_SOURCE.read_text(encoding="utf-8")
    head = next(ln for ln in src.splitlines() if 'log.info("CAPTURE|' in ln)
    assert all(f'"|{k}=" ' in head for k in ("lrl", *capture.LRL_HEAD)), head
    bar = next(ln for ln in src.splitlines() if 'log.info("BAR|"' in ln)
    assert all(f'"|{k}=" ' in bar for k in ("LH", "LL", "KH", "KL")), bar


@pytest.mark.parametrize("which, n", [("nq", 1000), ("nq", 400), ("walk", 1500), ("walk", 600)])
def test_lrl_parity_passes_on_a_faithful_capture(which, n):
    cs = study.nq_candles() if which == "nq" else random_walk(3000, 11, gap_prob=0.02)
    r = _cmp(pine_capture(cs, n))
    assert not _diffs(r), _diffs(r)[:5]
    lrl = r["lrl"]
    assert lrl["events"] > 5 and lrl["boundaries"] > 5 and lrl["cand_bars"] > n
    assert lrl["ends"]["pine"] == lrl["ends"]["oracle"] and sum(lrl["ends"]["pine"].values()) > 2


def test_window_starting_inside_an_active_lrl_is_not_observable():
    """Start the capture while an LRL is active (its first points before the window): that
    LRL and every LRL sharing one of its points are NOT OBSERVABLE; nothing else differs."""
    cs = study.nq_candles()
    m = IstModel(S).run(cs)
    r0 = next(r for r in sorted(m.lrl.high.records() + m.lrl.low.records(), key=lambda r: r.born)
              if r.born > 300 and len(r.xs) >= 3)
    a = r0.xs[1] + 1                                         # the window opens between its 2nd and 3rd point
    r = _cmp(pine_capture(cs, 0, a=a))
    assert not _diffs(r), _diffs(r)[:5]
    assert r["lrl"]["not_observable"] >= 1 and r["lrl"]["events"] > 5


def _edit(lines, pick, new):
    i = next(k for k, ln in enumerate(lines) if pick(ln))
    return lines[:i] + [new(lines[i])] + lines[i + 1:]


def _faithful():
    return pine_capture(study.nq_candles(), 1000)


@pytest.mark.parametrize("what", ["boundary", "previous boundary", "class", "tau", "points", "missing event",
                                  "candidates", "extra event"])
def test_lrl_differences_are_detected(what):
    lines = _faithful()
    is_bar = lambda ln: ln.startswith("BAR|") and re.search(r"\|LH=\d", ln)
    if what in ("boundary", "previous boundary"):
        k = 1 if what == "boundary" else 2
        bad = _edit(lines, is_bar, lambda ln: re.sub(r"(\|LH=\d+:[^:]+:[^|;]+)",
                    lambda m: ":".join(p if j != k else _n(float(p) + 0.5) for j, p in enumerate(m[1].split(":"))), ln, 1))
    elif what == "class":
        bad = _edit(lines, lambda ln: " LRL_SWEEP " in ln, lambda ln: ln.replace(" LRL_SWEEP ", " LRL_DRIFT "))
    elif what == "tau":
        bad = _edit(lines, lambda ln: " LRL_CONFIRMED " in ln, lambda ln: re.sub(r"tau=([\d.]+)",
                    lambda m: f"tau={_n(float(m[1]) + 0.25)}", ln))
    elif what == "points":
        bad = _edit(lines, lambda ln: " LRL_CONFIRMED " in ln, lambda ln: re.sub(r"pts=(\d+)",
                    lambda m: f"pts={int(m[1]) + 60_000}", ln))
    elif what == "missing event":
        i = [k for k, ln in enumerate(lines) if " LRL_BREAK " in ln][-1]
        bad = lines[:i] + lines[i + 1:]
    elif what == "candidates":
        late = [k for k, ln in enumerate(lines) if ln.startswith("BAR|")][-10]
        bad = lines[:late] + [re.sub(r"\|KH=(\d+)", lambda m: f"|KH={int(m[1]) + 1}", lines[late])] + lines[late + 1:]
    else:
        src = next(ln for ln in lines if " LRL_EXTENDED " in ln or " LRL_BREAK " in ln)
        bad = lines + []
        bad.insert(lines.index(src) + 1, src.replace(" LRL_", " LRL_", 1).replace("LRL_BREAK", "LRL_EXPIRED")
                   .replace("LRL_EXTENDED", "LRL_CONFIRMED"))
    assert not _diffs(_cmp(lines))
    assert any("LRL" in d or "LRLs" in d or "candidates" in d for d in _diffs(_cmp(bad))), what


def test_capture_without_lrl_is_unchanged():
    """A v0.4.x capture has no LRL keys: no LRL section, the same totals as before."""
    from validation.parity import CAPTURE_V044
    r = capture.compare(capture.parse(CAPTURE_V044.read_text(encoding="utf-8")))
    assert r["lrl"] is None and not [c for c in r["checks"] if c["section"] == "lrl"]
    assert (r["counts"][manual.MATCH], r["counts"][manual.NOBS], r["differences"]) == (29, 6, 0)
