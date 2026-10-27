"""Manual event parity (free plan): parser and comparison self-tests, then the real file if present.
The 'Pine observations' here are written from the oracle's own run, so they must match;
each injected fault must then be found."""
from dataclasses import replace
from functools import lru_cache

import pytest

from validation import stats
from validation.candles import random_walk
from validation.models.ist import run_model
from validation.models.types import Settings
from validation.parity import manual
from validation.parity.__main__ import main

pytestmark = [pytest.mark.common, pytest.mark.section("parity")]
TZ = "America/New_York"


@lru_cache(maxsize=None)
def _run():
    cs = random_walk(1500, 7, gap_prob=0.02)
    return cs, run_model(cs, Settings.from_dict({"liq": {"preset": "balanced"}}))


def _block(m, n=60):
    """The last n log entries, newest first, as 'Last events' shows them (all types)."""
    return list(reversed(m.events[-n:]))


def _text(events=None, short=False, **over):
    """A manual file as the user fills it: debug rows 21–26 and 34, then one EVENTS block."""
    cs, m = _run()
    vals = {"SYMBOL": "NQ1!", "TIMEFRAME": "1m", "PRESET": "balanced", "LEFT": 5, "RIGHT": 3, "REACTION": "1.0",
            "EQ_TOLERANCE_TICKS": 4, "EQ_MIN_TOUCHES": 2, "CONFIRMED_ONLY": "yes",
            "HISTORY_START": manual._fmt(cs[0].time, TZ), "HISTORY_END": manual._fmt(cs[-1].time, TZ),
            "HISTORY_BARS": len(cs), "CANDLES": "nq.csv", **manual.oracle_counts(m), **over}
    lines = [manual.pine_text(e, TZ)[5 if short else 0:] for e in (events if events is not None else _block(m))]
    return "\n".join([*(f"{k}={v}" for k, v in vals.items()), "EVENTS", *lines, "END_EVENTS", ""])


def _check(tmp_path, text, preset=None):
    cs, _ = _run()
    (tmp_path / "nq.csv").write_text("time,open,high,low,close\n" + "".join(
        f"{c.time // 1000},{c.open},{c.high},{c.low},{c.close}\n" for c in cs))
    (tmp_path / "manual_observed.txt").write_text(text, encoding="utf-8")
    return manual.run(tmp_path / "manual_observed.txt", preset)


def _diffs(r):
    return [c["text"] for c in r["checks"] if c["status"] == manual.DIFF]


def _middle(pred=lambda e: True):
    """An event strictly inside the block (not on its oldest or newest bar) that has an id."""
    _, m = _run()
    b = _block(m)
    return next(e for e in b[5:-5] if e.type != "LEVEL_SET" and e.time not in (b[0].time, b[-1].time) and pred(e))


def test_valid_manual_input_parses_and_matches(tmp_path):
    cs, m = _run()
    man = manual.parse(_text())
    assert man["values"]["SWING_HIGH_PIVOTS"] == m.liq.bsl.pivots and man["values"]["CONFIRMED_ONLY"] is True
    assert len(man["blocks"]) == 1 and len(man["blocks"][0]) == 60
    r = _check(tmp_path, _text())
    assert r["differences"] == 0, _diffs(r)
    by = {s: [c for c in r["checks"] if c["section"] == s and c["status"] == manual.MATCH] for s in manual.SECTIONS}
    assert len(by["settings"]) == 4 and len(by["candles"]) == 4
    assert len(by["summary"]) == 4 + len(manual.COUNTS)              # 4 internal + every count vs the oracle
    assert len(by["events"]) == sum(e.type != "LEVEL_SET" for e in _block(m))
    assert manual.verdict(r).startswith("MANUAL EVENT PARITY: PASS")


def test_spacing_and_copy_variants_parse(tmp_path):
    """TradingView copy/paste and hand typing: case, spaces, tabs, ':' for '=', CRLF, BOM,
    thousands separators, decimal comma, comments, 'Last events' times without the year,
    a Pine Logs timestamp or the row label in front of a line."""
    cs, m = _run()
    clean = manual.parse(_text())

    def mangle(line):
        if line in ("EVENTS", "END_EVENTS", ""):
            return {"EVENTS": "  Events:  ", "END_EVENTS": "end events"}.get(line, "   ")
        if line[0].isdigit():
            return "\t" + line.replace("  ", "     ").replace(" id=", "  ID = ").replace(" px=", " px= ") + "   "
        k, v = line.split("=", 1)
        return f"   {k.lower()} :  {v}\t"

    messy = "﻿# copied by hand\r\n" + "\r\n".join(map(mangle, _text(short=True).splitlines()))
    messy = messy.replace(f"history_bars :  {len(cs)}", f"HISTORY BARS = {len(cs):,} bars")
    messy = messy.replace("swing_high_warmup :", "Swing-High Warm-up =")
    messy = messy.replace("reaction :  1.0", "REACTION = 1,0")
    assert "1,500 bars" in messy and "1,0" in messy
    got = manual.parse(messy)
    assert got["values"] == clean["values"]
    assert [{k: e[k] for k in ("time", "type", "dir", "sid", "price")} for e in got["blocks"][0]] == \
           [{k: e[k] for k in ("time", "type", "dir", "sid", "price")} for e in clean["blocks"][0]]
    e = _middle()
    for prefix in (f"[{manual._fmt(e.time, TZ).replace(' ', 'T')}:00.000-04:00]: ", "Last events  "):
        one = manual.parse(f"EVENTS\n{prefix}{manual.pine_text(e, TZ)}\nEND_EVENTS")["blocks"][0][0]
        assert (one["time"], one["type"], one["sid"]) == (e.time, e.type, e.sid)
        assert one["price"] == float(manual.pine_px(e.price, 0.25))


@pytest.mark.parametrize("text, msg", [
    ("SWING_HIGH_PIVOT=1182", r"line 1: unknown key SWING_HIGH_PIVOT \(did you mean SWING_HIGH_PIVOTS\?\)"),
    ("LEFT=five", r"line 1: LEFT=five: expected a number"),
    ("LEFT=5\nLEFT=6", r"line 2: LEFT is given twice"),
    ("SWING_HIGH_PASS=1129.5", r"expected a whole number"),
    ("CONFIRMED_ONLY=maybe", r"expected yes or no"),
    ("10-27 12:06 BSL_CREATED id=2026-10-27 12:03 px=1", r"line 1: expected KEY=VALUE, or event lines between EVENTS"),
    ("EVENTS\n10-27 12:06 BSL_CREATED id=2026-10-27 12:03 px=1", r"line 1: EVENTS has no END_EVENTS"),
    ("END_EVENTS", r"END_EVENTS without EVENTS"),
    ("EVENTS\n10-27 12:06 BSL_CREATE id=2026-10-27 12:03 px=1\nEND_EVENTS", r"unknown event BSL_CREATE \(did you mean BSL_CREATED\?\)"),
    ("EVENTS\nBSL_SWEEP px=21000\nEND_EVENTS", r"line 2: needs the event time"),
    ("EVENTS\n10-27 12:06 swept the high\nEND_EVENTS", r"line 2: no event name"),
    ("EVENTS\n10-27 12:06 BSL_SWEEP id=2026-10-27 12:03 px=1 | SSL_SWEEP id=2026-10-27 12:01 px=1\nEND_EVENTS",
     r"more than one event"),
    ("EVENTS\n13-45 12:06 BSL_SWEEP id=2026-10-27 12:03 px=1\nEND_EVENTS", r"line 2: month must be"),
    ("TIMEZONE=Lisbon", r"unknown time zone"),
])
def test_malformed_input_is_rejected_clearly(text, msg):
    with pytest.raises(ValueError, match=msg):
        manual.parse(text)


def test_settings_are_checked(tmp_path):
    r = _check(tmp_path, _text(LEFT=4, CONFIRMED_ONLY="no"))
    assert sorted(_diffs(r)) == ["balanced left: Pine 4 · oracle preset 5",
                                 "confirmed only: OFF · the oracle models ON only"]
    with pytest.raises(ValueError, match="--preset strict"):
        _check(tmp_path, _text(), preset="strict")
    with pytest.raises(ValueError, match="PRESET=custom needs LEFT"):
        manual.compare(manual.parse("PRESET=custom\nRIGHT=3\nREACTION=1"))


def test_injected_missing_event_is_detected(tmp_path):
    _, m = _run()
    gone = _middle()
    r = _check(tmp_path, _text(events=[e for e in _block(m) if e is not gone]))
    assert len(_diffs(r)) == 1 and "missing in Pine" in _diffs(r)[0] and gone.type in _diffs(r)[0], _diffs(r)
    liq = [e for e in reversed(m.events[-400:]) if e.type.startswith(("BSL", "SSL"))]   # a Pine Logs search 'BSL_|SSL_'
    assert _diffs(_check(tmp_path, _text(events=liq, EVENT_FILTER="BSL SSL"))) == []
    d = _diffs(_check(tmp_path, _text(events=liq)))                     # without the filter the FVG events are missing
    assert d and all("missing in Pine" in x for x in d), d
    gone = liq[len(liq) // 2]
    d = _diffs(_check(tmp_path, _text(events=[e for e in liq if e is not gone], EVENT_FILTER="BSL, SSL")))
    assert len(d) == 1 and gone.type in d[0] and "BSL SSL only" in d[0], d


def test_injected_extra_event_is_detected(tmp_path):
    cs, m = _run()
    b = _block(m)
    ids = {e.sid for e in m.events if e.type == "BSL_CREATED"}
    fake = next(replace(b[10], type="BSL_CREATED", dir=1, sid=c.time, price=c.high, meta="")
                for c in cs[-200:] if c.time not in ids)
    r = _check(tmp_path, _text(events=[*b[:10], fake, *b[10:]]))
    assert len(_diffs(r)) == 1 and "not in the oracle" in _diffs(r)[0], _diffs(r)


def test_wrong_event_time_is_detected(tmp_path):
    _, m = _run()
    e = _middle(lambda e: e.sid is not None and e.sid != e.time)
    r = _check(tmp_path, _text(events=[replace(x, time=x.time + 60_000) if x is e else x for x in _block(m)]))
    assert len(_diffs(r)) == 1 and "time Pine" in _diffs(r)[0], _diffs(r)


def test_wrong_event_price_is_detected(tmp_path):
    _, m = _run()
    e = _middle(lambda e: e.price is not None)
    r = _check(tmp_path, _text(events=[replace(x, price=x.price + 0.25) if x is e else x for x in _block(m)]))
    assert len(_diffs(r)) == 1 and "price Pine" in _diffs(r)[0], _diffs(r)


def test_prices_compare_as_pine_prints_them():
    """format.mintick rounds to the tick: a half-tick CE prints as a neighbouring tick."""
    assert manual.pine_px(19908.125, 0.25) == "19908.25" and manual.pine_px(19908.0, 0.25) == "19908.00"
    assert manual._same_px(19908.25, 19908.125, 0.25) and manual._same_px(19908.0, 19908.125, 0.25)
    assert not manual._same_px(19908.5, 19908.125, 0.25) and not manual._same_px(19908.25, 19908.0, 0.25)


def test_duplicate_event_is_detected(tmp_path):
    _, m = _run()
    b = _block(m)
    r = _check(tmp_path, _text(events=[*b[:20], b[19], *b[20:]]))
    assert len(_diffs(r)) == 1 and "listed twice" in _diffs(r)[0], _diffs(r)


def test_wrong_swing_summary_count_is_detected(tmp_path):
    _, m = _run()
    r = _check(tmp_path, _text(SWING_HIGH_PASS=m.liq.bsl.levels + 1))
    d = _diffs(r)
    assert f"swing highs PASS (row 22): Pine {m.liq.bsl.levels + 1} · oracle {m.liq.bsl.levels}" in d, d
    assert len(d) == 3 and all("internal" in x for x in d if "row 22" not in x), d   # the row no longer adds up


def test_without_candles_nothing_is_claimed(tmp_path):
    r = _check(tmp_path, _text(CANDLES=""))
    assert r["differences"] == 0 and not r["oracle"]
    assert {c["section"] for c in r["checks"] if c["status"] == manual.MATCH} == {"settings", "summary"}
    assert manual.verdict(r).startswith("MANUAL EVENT PARITY: INCOMPLETE")
    r = _check(tmp_path, _text(HISTORY_BARS=1499))                       # the candles are not Pine's history
    assert _diffs(r) == ["bars in Pine's loaded history 1499 · candles 1500"]
    assert all(c["status"] == manual.NOBS for c in r["checks"] if "(row " in c["text"])


def test_command_line_exit_codes(tmp_path, capsys):
    _check(tmp_path, _text())
    f = str(tmp_path / "manual_observed.txt")
    assert main(["--manual", f, "--preset", "balanced"]) == 0
    out = capsys.readouterr().out
    assert "MANUAL EVENT PARITY: PASS" in out and "NOT full bar-by-bar parity" in out
    (tmp_path / "manual_observed.txt").write_text(_text(SWING_LOW_REJECT=0), encoding="utf-8")
    assert main(["--manual", f]) == 1
    (tmp_path / "manual_observed.txt").write_text("LEFT=five", encoding="utf-8")
    assert main(["--manual", f]) == 2
    assert "line 1: LEFT=five: expected a number" in capsys.readouterr().err


def test_template_parses_empty():
    man = manual.parse((manual.MANUAL.parent / "manual_observed_template.txt").read_text(encoding="utf-8"))
    assert set(man["values"]) == {"SYMBOL", "TIMEFRAME", "TIMEZONE", "TICK_SIZE", "PRESET"} and man["blocks"] == [[]]
    r = manual.compare(man)
    assert r["checks"] == [] and not r["oracle"]


def test_manual_observed_tradingview_data():
    result = manual.run()
    stats.RESULTS["manual_parity"] = result
    if result["status"] == "NO OBSERVED DATA":
        pytest.skip(f"manual parity is PENDING: {result['reason']}")
    assert result["differences"] == 0, _diffs(result)
