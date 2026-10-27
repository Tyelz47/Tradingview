"""Bounded Pine-Log parity: parser and comparison self-tests, then the real capture if present.

A synthetic 'Pine capture' is written from the oracle's run over the WHOLE history (what
Pine knows when it logs), cut to the last N + warm-up bars. The bounded oracle then sees
only those bars, as with a real capture, so these tests exercise the warm-up and the
exclusion of everything born before the window."""
import re
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

import pytest

from validation import PINE_SOURCE, stats
from validation.candles import random_walk
from validation.models.ist import IstModel
from validation.models.types import Settings
from validation.parity import capture, manual, oracle_series
from validation.parity.__main__ import main

pytestmark = [pytest.mark.common, pytest.mark.section("parity")]
TZ = "America/New_York"
HEAD = ("CAPTURE|sym=CME_MINI:NQ1!|tf=1|tick=0.25|tz=America/New_York|confirmed=1|liq=1|preset={preset}|left={l}|right={r}"
        "|k={k}|eqtol=4|eqmin=2|liqmem=100|fvgticks=2|fvgtra=0.1|fvgrng=0|fvglen=14|fvgmem=50"
        "|ses=Asia@2000-0000,London@0200-0500,NY AM@0930-1200,NY PM@1330-1600|bars={n}|warmup={w}")


def _n(x):
    return "na" if x is None else (f"{x:.8f}".rstrip("0").rstrip(".") or "0")


@lru_cache(maxsize=None)
def _history(seed=7, bars=1500, preset="balanced"):
    cs = random_walk(bars, seed, gap_prob=0.02)
    s = Settings.from_dict({"liq": {"preset": preset}})
    m = IstModel(s)
    return cs, s, oracle_series(cs, s, m), m.events


def _capture(seed=7, bars=1500, n=300, preset="balanced", end=True):
    """The Pine Logs lines IST writes for the last n closed bars (+ warm-up), oldest first."""
    cs, s, series, events = _history(seed, bars, preset)
    w = max(s.fvg.length + 2, max(s.liq.tra_len, s.liq.left) + s.liq.right)
    a = len(cs) - (n + w)
    by_bar = {}
    for e in events:
        by_bar.setdefault(e.bar, []).append(e)
    lines = [HEAD.format(preset=preset.title(), l=s.liq.left, r=s.liq.right, k=_n(s.liq.k), n=n, w=w)]
    for t in range(a, len(cs)):
        c = cs[t]
        ts = datetime.fromtimestamp(c.time / 1000, ZoneInfo(TZ)).strftime("%Y-%m-%dT%H:%M:%S%z")
        v = {k: _n(series[f][t]) for k, f in capture.FIELDS.items()}
        lines.append(f"BAR|{ts}|i={t}|O={_n(c.open)}|H={_n(c.high)}|L={_n(c.low)}|C={_n(c.close)}|"
                     + "|".join(f"{k}={x}" for k, x in v.items()))
        lines += [manual.pine_text(e, TZ) for e in by_bar.get(t, [])]
    if end:
        lines.append(f"END|bars={n + w}")
    return lines


def _run(lines, preset=None):
    return capture.compare(capture.parse("\n".join(lines)), preset)


def _diffs(r):
    return [c["text"] for c in r["checks"] if c["status"] == manual.DIFF]


def _bar_index(lines, i):
    return next(k for k, ln in enumerate(lines) if f"|i={i}|" in ln)


def test_valid_bar_lines_parse():
    lines = _capture()
    cap = capture.parse("\n".join(lines))
    cs, s, series, _ = _history()
    assert len(cap["bars"]) == 300 + 17 and cap["end"] == 317 and cap["head"]["preset"] == "Balanced"
    first = cap["bars"][0]
    assert first["candle"] == cs[len(cs) - 317] and first["i"] == len(cs) - 317
    assert first["vals"]["liq_required"] == pytest.approx(series["liq_required"][first["i"]], abs=1e-8)
    # as copied from the Pine Logs pane: its own timestamp in front, CRLF, UI text around
    pane = ["Pine Logs", ""] + [f"[2026-10-26T18:59:00.000-04:00]: {ln}" for ln in lines] + ["Load more"]
    again = capture.parse("\r\n".join(pane))
    assert [b["candle"] for b in again["bars"]] == [b["candle"] for b in cap["bars"]] and again["ignored"] == 2
    assert len(again["events"]) == len(cap["events"]) > 0


@pytest.mark.parametrize("seed, bars, n, preset", [(7, 1500, 300, "balanced"), (11, 2500, 1000, "balanced"),
                                                   (3, 1200, 300, "strict"), (5, 1500, 600, "aggressive")])
def test_successful_bounded_parity(seed, bars, n, preset):
    r = _run(_capture(seed, bars, n, preset))
    assert r["differences"] == 0, _diffs(r)[:10]
    assert r["compared_bars"] == n and r["matched_events"] > 0
    got = {c["text"].split(":")[0] for c in r["checks"] if c["section"] == "events" and c["status"] == manual.MATCH}
    assert {"BSL_CREATED", "SSL_CREATED", "FVG_CREATED"} <= got and got & {"BSL_SWEEP", "BSL_BREAK", "SSL_SWEEP", "SSL_BREAK"}
    nobs = " ".join(c["text"] for c in r["checks"] if c["status"] == manual.NOBS)
    assert "before the capture" in nobs                               # Pine knew older structures; never compared
    assert r["totals"]["pine"] == r["totals"]["oracle"]


def test_warm_up_is_needed_and_excluded():
    """Inside the warm-up the bounded oracle really differs from Pine (it lacks the earlier
    bars), so comparing there would report false differences; a fault after it is found."""
    lines = _capture()
    cap = capture.parse("\n".join(lines))
    cs, s, _, _ = _history()
    want = oracle_series([b["candle"] for b in cap["bars"]], s)
    assert any(b["vals"]["fvg_required"] != want["fvg_required"][t] for t, b in enumerate(cap["bars"][:16]))
    i0 = cap["bars"][0]["i"]
    k = _bar_index(lines, i0 + 3)
    lines[k] = re.sub(r"\|FR=[^|]+", "|FR=99", lines[k])               # inside the warm-up: not compared
    assert _diffs(_run(lines)) == []
    t = next(t for t, b in enumerate(cap["bars"]) if t > 40 and b["vals"]["bsl_pivot"] == 2)
    k = _bar_index(lines, i0 + t)
    lines[k] = lines[k].replace("|SH=2|", "|SH=1|")                    # Pine 'rejected' a swing the oracle kept
    d = _diffs(_run(lines))
    assert len(d) == 1 and "swing high verdict: Pine 1.0 · oracle 2" in d[0], d


def test_missing_bar_is_rejected():
    lines = _capture()
    i0 = int(re.search(r"\|i=(\d+)\|", lines[1])[1])
    del lines[_bar_index(lines, i0 + 50)]
    with pytest.raises(ValueError, match=rf"bar i={i0 + 50} missing \(between lines \d+ and \d+\)"):
        capture.parse("\n".join(lines))


def test_duplicate_bar_is_rejected():
    lines = _capture()
    k = _bar_index(lines, int(re.search(r"\|i=(\d+)\|", lines[1])[1]) + 50)
    lines.insert(k, lines[k])
    with pytest.raises(ValueError, match=r"bar i=\d+ appears 2 times \(lines \d+, \d+\): paste the capture once"):
        capture.parse("\n".join(lines))


@pytest.mark.parametrize("old, new, msg", [
    (r"\|H=[^|]+", "|H=1", r"wrong OHLC: high < max\(open, close\)"),
    (r"\|O=[^|]+", "|O=20000.1", r"wrong OHLC: .*off the 0.25 tick grid"),
    (r"\|C=[^|]+", "|C=abc", r"C=abc: not a number"),
    (r"\|L=[^|]+", "|L=na", r"wrong OHLC: na"),
    (r"\|RQ=[^|]+", "", r"BAR: missing RQ"),
])
def test_wrong_ohlc_is_rejected(old, new, msg):
    lines = _capture()
    k = _bar_index(lines, int(re.search(r"\|i=(\d+)\|", lines[1])[1]) + 30)
    lines[k] = re.sub(old, new, lines[k])
    with pytest.raises(ValueError, match=msg):
        capture.parse("\n".join(lines))


@pytest.mark.parametrize("bad", ["2026-10-26 12:00", "2026-10-26T12:00:00", "2026-13-26T12:00:00-0400", "yesterday"])
def test_malformed_timestamp_is_rejected(bad):
    lines = _capture()
    k = _bar_index(lines, int(re.search(r"\|i=(\d+)\|", lines[1])[1]) + 30)
    lines[k] = re.sub(r"^BAR\|[^|]+", f"BAR|{bad}", lines[k])
    with pytest.raises(ValueError, match=rf"line {k + 1}: BAR: malformed timestamp"):
        capture.parse("\n".join(lines))


def test_header_and_end_are_checked():
    lines = _capture()
    with pytest.raises(ValueError, match="no CAPTURE line"):
        capture.parse("\n".join(lines[1:]))
    with pytest.raises(ValueError, match="END says 317 bars but 316"):
        capture.parse("\n".join(lines[:1] + lines[2:]))
    r = _run(_capture(end=False))                                     # last bar still open, or copy cut: a note
    assert r["differences"] == 0 and any("no END line" in n for n in r["notes"])
    with pytest.raises(ValueError, match="preset Balanced but --preset strict"):
        _run(lines, preset="strict")


def _event_lines(lines, kinds=r"(BSL|SSL|FVG)_CREATED", start=60):
    """Indices of event lines well after the warm-up, of structures born there (so compared)."""
    i0 = int(re.search(r"\|i=(\d+)\|", lines[1])[1])
    k0 = _bar_index(lines, i0 + start)
    return [k for k in range(k0, len(lines) - 30) if re.search(rf"  {kinds}\b", lines[k])]


def test_event_mismatch_is_detected():
    lines = _capture()
    k = _event_lines(lines)[3]
    wrong = lines.copy()
    wrong[k] = re.sub(r"px=([\d.]+)", lambda m: f"px={float(m[1]) + 0.25:.2f}", wrong[k])
    d = _diffs(_run(wrong))
    assert len(d) == 1 and "price Pine" in d[0], d
    gone = lines[:k] + lines[k + 1:]
    d = _diffs(_run(gone))
    assert len(d) == 1 and d[0].startswith("missing in Pine:") and lines[k].split("  ")[1].split()[0] in d[0], d
    dup = lines[:k] + [lines[k], lines[k]] + lines[k + 1:]
    d = _diffs(_run(dup))
    assert len(d) == 1 and "logged twice" in d[0], d
    k = _event_lines(lines, r"(BSL|SSL)_CREATED")[0]                    # the same swing on the other side
    flip = lines[k].replace("BSL_", "#").replace("SSL_", "BSL_").replace("#", "SSL_")
    d = _diffs(_run(lines[:k] + [flip] + lines[k:]))
    assert len(d) == 1 and "not in the oracle (an extra Pine event)" in d[0], d


def test_pine_capture_lines_match_the_parser():
    """IST.pine writes what this parser reads: input OFF by default, every BAR key, every
    CAPTURE key, and an END line."""
    src = PINE_SOURCE.read_text(encoding="utf-8")
    assert re.search(r'^capOn\s*=\s*input\.bool\(false, "Parity capture', src, re.M)
    assert re.search(r'^capN\s*=\s*input\.int\(300, .*maxval = 2000', src, re.M)
    bar = next(ln for ln in src.splitlines() if 'log.info("BAR|"' in ln)
    assert all(f'"|{k}=" ' in bar for k in ("i", "O", "H", "L", "C", *capture.FIELDS)), bar
    assert "yyyy-MM-dd'T'HH:mm:ssZ" in bar
    head = next(ln for ln in src.splitlines() if 'log.info("CAPTURE|' in ln)
    assert all(re.search(rf'[|"]{k}=', head) for k in capture.HEAD), [k for k in capture.HEAD if f"{k}=" not in head]
    assert 'log.info("END|bars="' in src and "capDone < capTotal" in src


def test_command_line_exit_codes(tmp_path, capsys):
    f = tmp_path / "pine_capture.txt"
    f.write_text("\n".join(_capture()), encoding="utf-8")
    assert main(["--capture", str(f)]) == 0
    out = capsys.readouterr().out
    assert "BOUNDED PINE-LOG BAR-BY-BAR PARITY: PASS" in out and "NOT full CSV bar-by-bar parity" in out
    lines = _capture()
    k = _event_lines(lines)[1]
    f.write_text("\n".join(lines[:k] + lines[k + 1:]), encoding="utf-8")
    assert main(["--capture", str(f)]) == 1
    f.write_text("BAR|nonsense", encoding="utf-8")
    assert main(["--capture", str(f)]) == 2 and "no CAPTURE line" in capsys.readouterr().err


def test_capture_observed_tradingview_data():
    result = capture.run()
    stats.RESULTS["capture_parity"] = result
    if result["status"] == "NO OBSERVED DATA":
        pytest.skip(f"bounded Pine-Log parity is PENDING: {result['reason']}")
    assert result["differences"] == 0, _diffs(result)
