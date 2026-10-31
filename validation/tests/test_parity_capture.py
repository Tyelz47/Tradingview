"""Bounded Pine-Log parity: parser and comparison self-tests, then the real capture if present.

A synthetic 'Pine capture' is written from the oracle's run over the WHOLE history (what
Pine knows when it logs), cut to the last N + warm-up bars. The bounded oracle then sees
only those bars, as with a real capture, so these tests exercise the warm-up and the
exclusion of everything born before the window."""
import hashlib
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from validation import PINE_SOURCE, stats
from validation.candles import random_walk
from validation.models.ist import IstModel
from validation.models.types import PRESETS, Settings
from validation.parity import CAPTURE_V043, CAPTURE_V044, CAPTURE_V070, CAPTURE_V071, EVIDENCE, capture, manual, oracle_series
from validation.parity.__main__ import main

pytestmark = [pytest.mark.common, pytest.mark.section("parity")]
TZ = "America/New_York"
# As IST writes it on a chart with back-adjustment settings: syminfo.tickerid is a JSON
# object (quotes and commas inside the message), as in the user's TradingView file.
SYM = '={"backadjustment":"default","settlement-as-close":true,"symbol":"CME_MINI:NQ1!"}'
HEAD = ("CAPTURE|sym=" + SYM.replace("{", "{{").replace("}", "}}")
        + "|tf=1|tick=0.25|tz=America/New_York|confirmed=1|liq=1|preset={preset}|left={l}|right={r}"
        "|k={k}|w={dw}|eqtol=4|eqmin=2|liqmem=100|fvgticks=2|fvgtra=0.1|fvgrng=0|fvglen=14|fvgmem=50"
        "|ses=Asia@2000-0000,London@0200-0500,NY AM@0930-1200,NY PM@1330-1600|bars={n}|warmup={w}")
FIXTURE = Path(__file__).parent / "fixtures" / "pine_logs_capture_synthetic.csv"
MINUTE = 60_000


def _n(x):
    return "na" if x is None else (f"{x:.8f}".rstrip("0").rstrip(".") or "0")


def _warm(preset="balanced") -> int:
    """Capture warm-up from the dependency graph (Pine capWarm): Balanced 33 since C1."""
    s = Settings.from_dict({"liq": {"preset": preset}})
    return max(s.fvg.lookback, s.liq.lookback + s.liq.right)


@lru_cache(maxsize=None)
def _history(seed=7, bars=1500, preset="balanced", price=20000.0, start=None):
    cs = random_walk(bars, seed, gap_prob=0.02, start_price=price, **({"start": start} if start else {}))
    s = Settings.from_dict({"liq": {"preset": preset}})
    m = IstModel(s)
    return cs, s, oracle_series(cs, s, m), m.events


def _capture(seed=7, bars=1500, n=300, preset="balanced", end=True, first_i=None, price=20000.0, at=None):
    """The Pine Logs messages IST writes for the last n closed bars (+ warm-up), oldest
    first, as (bar open time, message). `first_i` / `at` relabel the window's first bar
    index and move its open time, as on a real chart."""
    w = _warm(preset)
    a = bars - (n + w)
    cs, s, series, events = _history(seed, bars, preset, price, at - a * MINUTE if at else None)
    off = (first_i - a) if first_i is not None else 0
    by_bar = {}
    for e in events:
        by_bar.setdefault(e.bar, []).append(e)
    out = [(cs[a].time, HEAD.format(preset=preset.title(), l=s.liq.left, r=s.liq.right, k=_n(s.liq.k), dw=s.liq.dom,
                                    n=n, w=w))]
    for t in range(a, len(cs)):
        c = cs[t]
        ts = datetime.fromtimestamp(c.time / 1000, ZoneInfo(TZ)).strftime("%Y-%m-%dT%H:%M:%S%z")
        v = {k: _n(series[f][t]) for k, f in capture.FIELDS.items()}
        out.append((c.time, f"BAR|{ts}|i={t + off}|O={_n(c.open)}|H={_n(c.high)}|L={_n(c.low)}|C={_n(c.close)}|"
                    + "|".join(f"{k}={x}" for k, x in v.items())))
        out += [(c.time, manual.pine_text(e, TZ)) for e in by_bar.get(t, [])]
    if end:
        out.append((cs[-1].time, f"END|bars={n + w}"))
    return out if at or first_i is not None else [m for _, m in out]


def _tv_csv(rows, crlf=False, bom=False):
    """A TradingView 'Pine Logs' file: Date (the bar time in UTC), then the quoted Message,
    its quotes doubled."""
    nl = "\r\n" if crlf else "\n"
    body = nl.join(f'{datetime.fromtimestamp(t / 1000, ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.000-00:00")},'
                   f'"{m.replace(chr(34), chr(34) * 2)}"' for t, m in rows)
    return ("﻿" if bom else "") + "Date,Message" + nl + body + nl


def write_fixture():
    """Regenerate tests/fixtures/pine_logs_capture_synthetic.csv (synthetic candles, real
    TradingView file shape: first bar i=16190 at 2026-10-27 10:50 New York). The committed
    file has the v0.4.3-dev shape (no w=, no DH/DL); regenerating now writes the v0.4.4-dev
    shape, so the fixture test's numbers would change with it."""
    at = int(datetime(2026, 10, 27, 10, 50, tzinfo=ZoneInfo(TZ)).timestamp() * 1000)
    FIXTURE.parent.mkdir(exist_ok=True)
    FIXTURE.write_bytes(_tv_csv(_capture(seed=21, first_i=16190, price=29664.5, at=at)).encode("utf-8"))


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
    W = _warm()
    assert W == 33 and len(cap["bars"]) == 300 + W and cap["end"] == 300 + W and cap["head"]["preset"] == "Balanced"
    assert cap["head"]["w"] == "30" and set(cap["bars"][0]["vals"]) == set(capture.FIELDS.values())
    first = cap["bars"][0]
    assert first["candle"] == cs[len(cs) - 300 - W] and first["i"] == len(cs) - 300 - W
    assert first["vals"]["liq_required"] == pytest.approx(series["liq_required"][first["i"]], abs=1e-8)
    # as copied from the Pine Logs pane: its own timestamp in front, CRLF, UI text around
    pane = ["Pine Logs", ""] + [f"[2026-10-26T18:59:00.000-04:00]: {ln}" for ln in lines] + ["Load more"]
    again = capture.parse("\r\n".join(pane))
    assert [b["candle"] for b in again["bars"]] == [b["candle"] for b in cap["bars"]]
    assert again["notes"] == ["2 log lines outside any capture run were ignored"]
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
    with pytest.raises(ValueError, match="END says 333 bars but 332"):
        capture.parse("\n".join(lines[:1] + lines[2:]))
    with pytest.raises(ValueError, match="no END line: the last bar was still open"):
        capture.parse("\n".join(_capture(end=False)))                 # last bar still open, or the copy is cut
    short = [re.sub(r"bars=300", "bars=299", lines[0])] + lines[1:]
    with pytest.raises(ValueError, match=r"333 BAR lines, but the CAPTURE line expects 332 \(bars 299 \+ warm-up 33\)"):
        capture.parse("\n".join(short))
    with pytest.raises(ValueError, match="preset Balanced but --preset strict"):
        _run(lines, preset="strict")


# ── TradingView's saved Pine Logs file (Date,Message CSV) ──

def _same(a, b):
    """Two parsed captures hold the same header, candles, per-bar values and events."""
    key = lambda c: (c["head"], [(x["i"], x["candle"], x["vals"]) for x in c["bars"]],
                     [{k: e[k] for k in ("time", "type", "dir", "sid", "price")} for e in c["events"]])
    return key(a) == key(b)


def test_tradingview_csv_capture_works():
    rows = _capture(first_i=16190, at=int(datetime(2026, 10, 27, 10, 50, tzinfo=ZoneInfo(TZ)).timestamp() * 1000))
    plain = capture.parse("\n".join(m for _, m in rows))
    cap = capture.parse(_tv_csv(rows))
    assert _same(cap, plain) and cap["source"].startswith("TradingView Pine Logs CSV") and plain["source"] == "pasted text"
    assert cap["head"]["sym"] == SYM                                  # doubled quotes undone, commas kept
    assert cap["head"]["warmup"] == "33" and cap["head"]["bars"] == "300" and cap["end"] == 333
    assert cap["head"]["ses"] == "Asia@2000-0000,London@0200-0500,NY AM@0930-1200,NY PM@1330-1600"
    assert cap["bars"][0]["i"] == 16190 and cap["bars"][-1]["i"] == 16190 + 332
    r = capture.compare(cap)
    assert r["differences"] == 0 and r["warmup"] == 33 and r["symbol"] == "CME_MINI:NQ1!", _diffs(r)


@pytest.mark.parametrize("crlf, bom", [(True, False), (False, True), (True, True)])
def test_tradingview_csv_crlf_and_bom(crlf, bom):
    rows = _capture(first_i=16190, at=1793112600000)
    assert _same(capture.parse(_tv_csv(rows, crlf=crlf, bom=bom)), capture.parse(_tv_csv(rows)))


def test_csv_rows_pasted_without_their_header():
    rows = _capture(first_i=16190, at=1793112600000)
    body = _tv_csv(rows).split("\n", 1)[1]
    assert _same(capture.parse(body), capture.parse(_tv_csv(rows)))


def test_regression_fixture_real_tradingview_shape():
    """The committed fixture has the shape of the file TradingView saves (synthetic
    candles, v0.4.3-dev lines: no w=, no DH/DL, so it replays without dominance)."""
    raw = FIXTURE.read_text(encoding="utf-8")
    assert raw.startswith("Date,Message\n2026-10-27T14:50:00.000-00:00,\"CAPTURE|sym==" + '{""backadjustment"":""default""')
    assert '\n2026-10-27T14:50:00.000-00:00,"BAR|2026-10-27T10:50:00-0400|i=16190|O=' in raw
    cap = capture.parse(raw)
    assert cap["head"]["warmup"] == "17" and len(cap["bars"]) == 317 and cap["end"] == 317
    r = capture.compare(cap)
    assert r["differences"] == 0 and r["matched_events"] > 0 and r["compared_bars"] == 300, _diffs(r)


def test_capture_runs_are_never_merged():
    one = _capture()
    r = _run(one + one)                                               # the same run twice: one is used, both listed
    assert r["differences"] == 0 and r["notes"][0].startswith("2 capture runs in the file (never merged); used run 2")
    cap = capture.parse("\n".join(one + _capture(end=False)))         # a later run never finished
    assert "USED run 1" in " ".join(cap["notes"]) and "skipped run 2" in " ".join(cap["notes"])
    assert "no END line" in " ".join(cap["notes"])
    cap = capture.parse("\n".join(_capture(end=False) + one))         # an earlier run cut by the next CAPTURE
    assert "USED run 2" in " ".join(cap["notes"])
    other = _capture(seed=8)                                          # two runs' lines in one CAPTURE … END
    with pytest.raises(ValueError, match="appears 2 times|END says"):
        capture.parse("\n".join(one[:200] + other[1:]))
    with pytest.raises(ValueError, match="none of the 2 capture runs in the file is complete and valid"):
        capture.parse("\n".join(_capture(end=False) + one[:200] + other[1:]))
    newest_first = _capture(first_i=16190, at=1793112600000)[::-1]    # a file saved newest first
    assert _same(capture.parse(_tv_csv(newest_first)), capture.parse(_tv_csv(newest_first[::-1])))


def test_csv_without_message_column_is_rejected():
    with pytest.raises(ValueError, match=r"the CSV has no Message column \(header: Date,Text\)"):
        capture.parse('Date,Text\n2026-10-27T14:50:00.000-00:00,"BAR|x"\n')


@pytest.mark.parametrize("body, msg", [
    ('2026-10-27T14:50:00.000-00:00,"CAPTURE|sym=x|bars=300\n', r"malformed CSV at line \d+"),
    ('2026-10-27T14:50:00.000-00:00,"CAPTURE|x"garbage\n', r"malformed CSV at line 2"),
    ('2026-10-27T14:50:00.000-00:00\n', r"line 2: 1 column\(s\), no Message field"),
])
def test_malformed_csv_is_rejected_clearly(body, msg):
    with pytest.raises(ValueError, match=msg):
        capture.parse("Date,Message\n" + body)


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
    g = tmp_path / "pine_capture.csv"                                 # the file TradingView saves, as it is
    g.write_bytes(FIXTURE.read_bytes())
    assert main(["--capture", str(g)]) == 0
    assert "TradingView Pine Logs CSV (Date,Message)" in capsys.readouterr().out


def test_v043_capture_parity_is_preserved_under_its_own_definition():
    """Historical evidence, versioned: the 1,000-bar TradingView capture of IST v0.4.3-dev
    (NQ1! 1m, Balanced, 2026-10-27; validation/parity/evidence, never rewritten) has no w=
    in its CAPTURE line, so it is replayed with the definition that build used (reaction
    only, no dominance) and must still match Pine exactly."""
    r = capture.compare(capture.parse(CAPTURE_V043.read_text(encoding="utf-8")))
    assert r["differences"] == 0, _diffs(r)
    assert (r["compared_bars"], r["matched_events"], r["warmup"], r["series"]) == (1000, 1258, 17, 7)
    assert r["totals"]["pine"]["swing highs"] == "71 PASS · 7 REJECT" == r["totals"]["oracle"]["swing highs"]
    assert r["totals"]["pine"]["swing lows"] == "68 PASS · 1 REJECT" == r["totals"]["oracle"]["swing lows"]
    assert any("W: not in this capture" in c["text"] and c["status"] == manual.NOBS for c in r["checks"])


def test_v043_capture_under_c1_differs_only_by_the_expected_definition_change():
    """The same capture forced to C1 (W = 30): every difference is one C1 intends. Pine
    v0.4.3 kept a swing (verdict 2) that C1 rejects (1), and the Pine events of those
    levels (CREATED / TAKEN / SWEEP / BREAK) have no oracle counterpart. Nothing else
    differs: no swing appears that Pine rejected, no event is missing in Pine, no FVG,
    reaction or required-reaction value changes."""
    cap = capture.parse(CAPTURE_V043.read_text(encoding="utf-8"))
    cap["head"]["w"] = "30"
    r = capture.compare(cap)
    d = _diffs(r)
    bars = [x for x in d if "verdict" in x]
    events = [x for x in d if "not in the oracle" in x]
    assert d and len(bars) + len(events) == len(d) - sum("W:" in x for x in d), d[:5]
    assert all(re.search(r"swing (high|low) verdict: Pine 2\.0 · oracle 1$", x) for x in bars), bars[:5]
    assert all(re.search(r" (BSL|SSL)_(CREATED|TAKEN|SWEEP|BREAK) ", x) for x in events), events[:5]
    created = [x for x in events if "_CREATED" in x]
    assert len(created) == len(bars), (len(created), len(bars))       # one removed level per changed verdict
    assert not any("missing in Pine" in x for x in d)


def test_v044_capture_parity_c1_frozen_baseline():
    """The Phase 2 freeze evidence: the 1,000-bar TradingView capture of IST v0.4.4-dev
    (C1, NQ1! 1m, Balanced, W 30, 2026-10-27 13:44 → 2026-10-28 07:56 New York) matches the
    oracle on every compared bar of all 9 series, dominance references included, and on
    every event of a structure born in the window."""
    r = capture.compare(capture.parse(CAPTURE_V044.read_text(encoding="utf-8")))
    assert r["differences"] == 0, _diffs(r)
    assert (r["compared_bars"], r["series"], r["matched_events"], r["warmup"]) == (1000, 9, 1049, 33)
    assert r["totals"]["pine"] == r["totals"]["oracle"] == {
        "swing highs": "38 PASS · 39 REJECT", "swing lows": "28 PASS · 45 REJECT",
        "FVG": "90 bull · 90 bear · 43 rejected"}
    ok = {c["text"].split(":")[0] for c in r["checks"] if c["status"] == manual.MATCH}
    assert {"balanced W", "dominance reference high", "dominance reference low"} <= ok, ok
    assert (r["counts"][manual.MATCH], r["counts"][manual.NOBS]) == (29, 6)


def test_evidence_captures_are_unchanged():
    """The evidence files are byte-identical to the hashes recorded at the freeze."""
    sums = dict(reversed(ln.split(" *", 1)) for ln in (EVIDENCE / "SHA256SUMS.txt").read_text().splitlines() if ln)
    assert set(sums) == {CAPTURE_V043.name, CAPTURE_V044.name, CAPTURE_V070.name, CAPTURE_V071.name}
    for name, digest in sums.items():
        assert hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest() == digest, name


def test_capture_observed_tradingview_data():
    result = capture.run()
    stats.RESULTS["capture_parity"] = result
    if result["status"] == "NO OBSERVED DATA":
        pytest.skip(f"bounded Pine-Log parity is PENDING: {result['reason']}")
    if result["capture_build"] != result["current_build"]:
        pytest.skip(f"the latest capture ({result['file']}) was written by IST {result['capture_build'] or 'v0.7.0-dev or earlier'}, "
                    f"src/IST.pine is {result['current_build']}: a NEW TradingView capture is required "
                    f"({result['differences']} differences against the older Pine output)")
    assert result["differences"] == 0, _diffs(result)
