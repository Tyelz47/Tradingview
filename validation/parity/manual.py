"""Manual event parity (free TradingView plan): the settings, counts and events you copy
or type from the IST debug table and Pine Logs, compared with the oracle.

This is weaker than FULL CSV BAR-BY-BAR PARITY (`python -m validation.parity EXPORT.csv`),
which compares every bar of a Data Window export. Here only what you supply is checked,
and only on the bars of the candle file you supply (CANDLES=, any OHLC source). Every
check is MATCH, DIFFERENCE or NOT OBSERVABLE. Format: manual_observed_template.txt.
"""
from __future__ import annotations

import difflib
import math
import re
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from validation import VALIDATION_DIR
from validation.candles import load_tradingview_export
from validation.models.eq import BREAK, SWEEP
from validation.models.events import ONCE, TYPES, parse_local
from validation.models.ist import IstModel
from validation.models.types import PRESETS, Settings, validate_candles

MANUAL = VALIDATION_DIR / "parity" / "manual_observed.txt"
MATCH, DIFF, NOBS = "MATCH", "DIFFERENCE", "NOT OBSERVABLE"
SECTIONS = ("settings", "candles", "summary", "events")

FIELDS = ("PIVOTS", "PASS", "REJECT", "WARMUP", "CREATED", "REJECT_REACTION", "REJECT_DOMINANCE", "REJECT_BOTH")
COUNTS = ([f"SWING_{s}_{f}" for s in ("HIGH", "LOW") for f in FIELDS]                    # debug rows 22–23
          + [f"{s}_{f}" for s in ("BSL", "SSL") for f in ("ACTIVE", "TAKEN", "SWEEP", "BREAK")]  # rows 24–25
          + [f"{s}_{f}" for s in ("EQH", "EQL") for f in ("ACTIVE", "TAKEN", "BELOW_MIN")])     # row 26
KEYS = {"SYMBOL": "text", "TIMEFRAME": "text", "TIMEZONE": "text", "TICK_SIZE": "num", "CANDLES": "text",
        "PRESET": "text", "LEFT": "int", "RIGHT": "int", "REACTION": "num", "EQ_TOLERANCE_TICKS": "int",
        "EQ_MIN_TOUCHES": "int", "CONFIRMED_ONLY": "bool",
        "HISTORY_START": "text", "HISTORY_END": "text", "HISTORY_BARS": "int", "EVENT_FILTER": "text",
        **{k: "int" for k in COUNTS}}
FAMILIES = ("FVG", "SESSION", "LEVEL", "BSL", "SSL", "EQH", "EQL")

_NAME = r"(?:FVG|SESSION|LEVEL|BSL|SSL|EQH|EQL)_[A-Z_]*[A-Z]"
_ANY_NAME = re.compile(rf"(?<![A-Z_]){_NAME}(?![A-Z_])", re.I)
# One "Last events" / Pine Logs line (src/IST.pine f_evText). Searched, not anchored: a
# Pine Logs timestamp or a row label in front of it is ignored.
_EV = re.compile(
    r"(?:(?P<date>(?:\d{4}[-/])?\d{1,2}[-/]\d{1,2})[ T]+(?P<hm>\d{1,2}:\d\d)(?::\d\d)?\s+)?"
    rf"(?P<name>{_NAME})(?![A-Z_])"
    r"(?:\s+(?P<side>BULL|BEAR|HIGH|LOW)\b)?"
    r"(?:\s*[·•|,;]?\s*ID\s*[=:]\s*(?P<id>\d{4}-\d{1,2}-\d{1,2}[ T]+\d{1,2}:\d\d))?"
    r"(?:\s*[·•|,;]?\s*PX\s*[=:]\s*(?P<px>-?\d[\d,]*(?:\.\d+)?|[—–-]|NA|N/A)(?![\d.]))?",
    re.I)


# ── parsing ────────────────────────────────────────────────────────────────────

def _number(v: str) -> float:
    s = re.sub(r"(?<=\d) (?=\d{3}\b)", "", v)                   # 1 182
    m = re.search(r"[+-]?\d+(?:[.,]\d+)*", s)
    if not m:
        raise ValueError("expected a number")
    # a comma before exactly three digits groups thousands (1,182); otherwise it is a decimal comma (1,0)
    return float(re.sub(r",(?=\d{3}(?!\d))", "", m.group()).replace(",", "."))


def _value(kind: str, v: str):
    if kind == "text":
        return v
    if kind == "bool":
        b = {"yes": True, "y": True, "true": True, "on": True, "1": True, "sim": True,
             "no": False, "n": False, "false": False, "off": False, "0": False, "não": False, "nao": False}.get(v.lower())
        if b is None:
            raise ValueError("expected yes or no")
        return b
    x = _number(v)
    if kind == "int":
        if x != int(x):
            raise ValueError("expected a whole number")
        return int(x)
    return x


def _key(k: str) -> str:
    return re.sub(r"[\s\-]+", "_", k.strip().upper()).replace("WARM_UP", "WARMUP")


def _ms(y: int, mo: int, d: int, hh: int, mm: int, tz: str) -> int:
    return int(datetime(y, mo, d, hh, mm, tzinfo=ZoneInfo(tz)).timestamp() * 1000)


def _local(text: str | None, tz: str) -> int | None:
    return None if not text else parse_local(re.sub(r"[ T]+", "T", text.strip())[:16], tz)


def _fmt(ms: int | None, tz: str) -> str:
    return "—" if ms is None else datetime.fromtimestamp(ms / 1000, ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M")


def _event(line: str, tz: str, year: int | None) -> dict:
    names = _ANY_NAME.findall(line)
    if len(names) != 1:
        raise ValueError("no event name (e.g. BSL_CREATED)" if not names else "more than one event on one line")
    m = _EV.search(line)
    name = m["name"].upper()
    if name not in TYPES:
        close = difflib.get_close_matches(name, TYPES, 1)
        raise ValueError(f"unknown event {name}" + (f" (did you mean {close[0]}?)" if close else ""))
    sid = _local(m["id"], tz) if m["id"] else None
    t = None
    if m["date"]:
        parts = [int(p) for p in re.split(r"[-/]", m["date"])]
        if len(parts) == 3:
            y, mo, d = parts
        else:
            (mo, d), y = parts, year
            if sid is not None:                                     # 'Last events' has no year: take the id's
                ref = datetime.fromtimestamp(sid / 1000, ZoneInfo(tz))
                y = ref.year + ((mo, d) < (ref.month, ref.day))
            if y is None:
                raise ValueError("no year: write yyyy-MM-dd HH:mm or set HISTORY_END")
        hh, mm = map(int, m["hm"].split(":"))
        t = _ms(y, mo, d, hh, mm, tz)
    if t is None and sid is None:
        raise ValueError("needs the event time (MM-dd HH:mm) or its id=")
    if name.startswith(("BSL_", "EQH_")):
        dir_ = 1
    elif name.startswith(("SSL_", "EQL_")):
        dir_ = -1
    else:
        dir_ = {"BULL": 1, "HIGH": 1, "BEAR": -1, "LOW": -1}.get((m["side"] or "").upper(), 0)
    px = m["px"]
    price = None if px is None or not px[-1].isdigit() else float(px.replace(",", ""))
    return {"time": t, "type": name, "dir": dir_, "sid": sid, "price": price, "has_price": px is not None,
            "text": re.sub(r"\s+", " ", line.strip())}


def parse(text: str) -> dict:
    """KEY=VALUE lines and EVENTS … END_EVENTS blocks → {"values", "blocks"}. Every
    malformed line is reported at once, with its line number (ValueError)."""
    values, raw_events, blocks, errors = {}, [], [], []
    block = start = None
    for n, line in enumerate(text.lstrip("﻿").splitlines(), 1):
        s = re.sub(r"(^|\s)#.*$", "", line).strip()
        if not s:
            continue
        word = _key(s.rstrip(":"))
        if word in ("EVENTS", "BEGIN_EVENTS"):
            if block is not None:
                errors.append(f"line {n}: EVENTS inside the block opened on line {start} (close it with END_EVENTS)")
            block, start = [], n
            blocks.append(block)
            continue
        if word in ("END_EVENTS", "ENDEVENTS"):
            if block is None:
                errors.append(f"line {n}: END_EVENTS without EVENTS")
            block = None
            continue
        if block is not None:
            block.append(n)
            raw_events.append((n, s, len(blocks) - 1))
            continue
        m = re.match(r"([A-Za-z][\w \-]*?)\s*[=:]\s*(.*)$", s)
        if not m:
            errors.append(f"line {n}: expected KEY=VALUE, or event lines between EVENTS and END_EVENTS: {s!r}")
            continue
        key, val = _key(m[1]), m[2].strip()
        if key not in KEYS:
            close = difflib.get_close_matches(key, KEYS, 1)
            errors.append(f"line {n}: unknown key {key}" + (f" (did you mean {close[0]}?)" if close else ""))
        elif key in values:
            errors.append(f"line {n}: {key} is given twice")
        elif val:                                                   # an empty value = not observed
            try:
                values[key] = _value(KEYS[key], val)
            except ValueError as e:
                errors.append(f"line {n}: {key}={val}: {e}")
    if block is not None:
        errors.append(f"line {start}: EVENTS has no END_EVENTS")
    tz = values.get("TIMEZONE", "America/New_York")
    try:
        ZoneInfo(tz)
    except (KeyError, ValueError):
        errors.append(f"TIMEZONE={tz}: unknown time zone (e.g. America/New_York)")
        tz = "America/New_York"
    year = next((int(values[k][:4]) for k in ("HISTORY_END", "HISTORY_START")
                 if re.match(r"\d{4}-", values.get(k, ""))), None) or \
        next((int(y) for _, s, _ in raw_events for y in re.findall(r"\b(\d{4})-\d{1,2}-\d{1,2}", s)), None)
    for k in ("HISTORY_START", "HISTORY_END"):
        try:
            _local(values.get(k), tz)
        except ValueError:
            errors.append(f"{k}={values[k]}: expected yyyy-MM-dd HH:mm")
    out = [[] for _ in blocks]
    for n, s, b in raw_events:
        try:
            out[b].append({**_event(s, tz, year), "line": n})
        except ValueError as e:
            errors.append(f"line {n}: {e}: {s!r}")
    if errors:
        raise ValueError("manual input rejected:\n  " + "\n  ".join(errors[:30])
                         + (f"\n  … {len(errors) - 30} more" if len(errors) > 30 else ""))
    return {"values": values, "blocks": out}


# ── comparison ─────────────────────────────────────────────────────────────────

def pine_px(p: float, tick: float) -> str:
    """str.tostring(p, format.mintick): rounded to the nearest tick (a CE can sit on a half tick)."""
    return f"{math.floor(p / tick + 0.5) * tick:.{len(f'{tick:g}'.partition('.')[2])}f}"


def _same_px(seen: float | None, want: float | None, tick: float) -> bool:
    """Pine prints prices rounded to the tick. Pine's rule for an exact half-tick tie is not
    documented, so both neighbouring ticks are accepted there; anything further is a difference."""
    if seen is None or want is None:
        return seen is want
    return abs(seen - want) <= tick / 2 + tick * 0.01


def pine_text(e, tz: str, tick: float = 0.25) -> str:
    """An oracle event as IST prints it in Pine Logs (f_evText with the full date)."""
    fam = e.type.split("_")[0]
    side = "" if fam in ("BSL", "SSL", "EQH", "EQL") or not e.dir else \
        (" BULL" if e.dir > 0 else " BEAR") if fam == "FVG" else (" HIGH" if e.dir > 0 else " LOW")
    ident = "" if e.type == "LEVEL_SET" else f" id={_fmt(e.sid, tz)}"
    px = "—" if e.price is None else pine_px(e.price, tick)
    return f"{_fmt(e.time, tz)}  {e.type}{side}{ident} px={px}" + (f" · {e.meta}" if e.meta else "")


def oracle_counts(m: IstModel) -> dict:
    """The debug-row counts (rows 22–26) from the oracle's final state."""
    out = {}
    for side in m.liq.sides():
        s, lv, q = ("HIGH" if side.is_bsl else "LOW"), side.all_levels(), side.eqs
        act = sum(x.taken_bar is None for x in lv)
        out.update({f"SWING_{s}_PIVOTS": side.pivots, f"SWING_{s}_PASS": side.levels, f"SWING_{s}_REJECT": side.rejects,
                    f"SWING_{s}_WARMUP": side.pivots - side.levels - side.rejects, f"SWING_{s}_CREATED": side.levels,
                    f"SWING_{s}_REJECT_REACTION": side.rej_react, f"SWING_{s}_REJECT_DOMINANCE": side.rej_dom,
                    f"SWING_{s}_REJECT_BOTH": side.rej_both,
                    f"{side.name}_ACTIVE": act, f"{side.name}_TAKEN": len(lv) - act,
                    f"{side.name}_SWEEP": sum(x.taken_bar is not None and x.cls == SWEEP for x in lv),
                    f"{side.name}_BREAK": sum(x.taken_bar is not None and x.cls == BREAK for x in lv),
                    f"{side.eq_name}_ACTIVE": sum(c.qual_bar is not None and c.taken_bar is None for c in q),
                    f"{side.eq_name}_TAKEN": sum(c.qual_bar is not None and c.taken_bar is not None for c in q),
                    f"{side.eq_name}_BELOW_MIN": sum(c.qual_bar is None for c in q)})
    return out


def _label(key: str) -> str:
    if key.startswith("SWING_"):
        s, f = key[6:].split("_", 1)
        f = {"PIVOTS": "pivots", "WARMUP": "warm-up", "CREATED": "created", "REJECT_REACTION": "REJECT reaction",
             "REJECT_DOMINANCE": "REJECT dominance", "REJECT_BOTH": "REJECT both"}.get(f, f)   # as the row prints them
        return f"swing {s.lower()}s {f} (row {22 if s == 'HIGH' else 23})"
    s, f = key.split("_", 1)
    return f"{s} {f.lower().replace('_', ' ')} (row {24 if s == 'BSL' else 25 if s == 'SSL' else 26})"


def _tf_seconds(text: str) -> int:
    m = re.fullmatch(r"\s*(\d+)\s*(s|sec|m|min|h|hr|d)?\s*", text.lower())
    if not m:
        raise ValueError(f"TIMEFRAME={text}: expected e.g. 1m, 3m, 5m")
    return int(m[1]) * {"s": 1, "sec": 1, None: 60, "m": 60, "min": 60, "h": 3600, "hr": 3600, "d": 86400}[m[2]]


def compare(man: dict, preset: str | None = None, base: Path = Path(".")) -> dict:
    v, checks, notes = man["values"], [], []
    add = lambda sec, st, txt: checks.append({"section": sec, "status": st, "text": txt})
    tz, tick = v.get("TIMEZONE", "America/New_York"), v.get("TICK_SIZE", 0.25)
    fmt = lambda ms: _fmt(ms, tz)

    # settings: the preset table and the modes the oracle models
    p_file = v["PRESET"].strip().lower() if "PRESET" in v else None
    if preset and p_file and preset != p_file:
        raise ValueError(f"PRESET={p_file} in the file but --preset {preset} on the command line")
    name = p_file or preset
    if name not in (*PRESETS, "custom"):
        raise ValueError(f"PRESET={name}: expected {', '.join(PRESETS)} or custom" if name else
                         "PRESET is missing (balanced, aggressive, strict or custom)")
    if name == "custom":
        miss = [k for k in ("LEFT", "RIGHT", "REACTION") if k not in v]
        if miss:
            raise ValueError(f"PRESET=custom needs {', '.join(miss)}")
        left, right, k, w = v["LEFT"], v["RIGHT"], v["REACTION"], 0      # Custom: no dominance window
    else:
        left, right, k, w = PRESETS[name]
        for key, want in zip(("LEFT", "RIGHT", "REACTION"), (left, right, k)):
            if key in v:
                add("settings", MATCH if abs(v[key] - want) < 1e-9 else DIFF,
                    f"{name} {key.lower()}: Pine {v[key]:g} · oracle preset {want:g}")
    if "CONFIRMED_ONLY" in v:
        add("settings", MATCH if v["CONFIRMED_ONLY"] else DIFF,
            "confirmed only: ON" if v["CONFIRMED_ONLY"] else "confirmed only: OFF · the oracle models ON only")
    tol, touch = v.get("EQ_TOLERANCE_TICKS", 4), v.get("EQ_MIN_TOUCHES", 2)
    if not (0 <= tol <= 200 and 2 <= touch <= 5):
        raise ValueError("EQ_TOLERANCE_TICKS must be 0–200 and EQ_MIN_TOUCHES 2–5 (the IST input ranges)")
    tf = _tf_seconds(v["TIMEFRAME"]) if "TIMEFRAME" in v else 60
    settings = Settings.from_dict({"tick": tick, "liq": {"left": left, "right": right, "k": k, "dom": w,
                                                         "tol_ticks": tol, "min_touch": touch},
                                   "sessions": {"timezone": tz, "timeframe_sec": tf}, "levels": {"timeframe_sec": tf}})
    about = (f"preset {name} → left {left} · right {right} · k {k:g} · dominance {w or 'off'} · EQ tolerance {tol} "
             f"ticks · minimum touches "
             f"{touch} · tick {tick:g} · {tz}; other IST inputs at their defaults")

    # summary: the debug rows must agree with themselves
    for s, lv in (("HIGH", "BSL"), ("LOW", "SSL")):
        g = {f: v.get(f"SWING_{s}_{f}") for f in FIELDS}
        if None not in (g["PIVOTS"], g["PASS"], g["REJECT"], g["WARMUP"]):
            add("summary", MATCH if g["PIVOTS"] == g["PASS"] + g["REJECT"] + g["WARMUP"] else DIFF,
                f"swing {s.lower()}s: pivots {g['PIVOTS']} = PASS {g['PASS']} + REJECT {g['REJECT']} + warm-up "
                f"{g['WARMUP']} (internal)")
        if None not in (g["PASS"], g["CREATED"]):
            add("summary", MATCH if g["PASS"] == g["CREATED"] else DIFF,
                f"swing {s.lower()}s: {lv} created {g['CREATED']} = PASS {g['PASS']} (internal)")
        why = (g["REJECT_REACTION"], g["REJECT_DOMINANCE"], g["REJECT_BOTH"])
        if g["REJECT"] is not None and None not in why:
            add("summary", MATCH if g["REJECT"] == sum(why) else DIFF,
                f"swing {s.lower()}s: REJECT {g['REJECT']} = reaction {why[0]} + dominance {why[1]} + both {why[2]} "
                f"(internal)")

    # candles: the oracle needs the chart's bars; they must be Pine's loaded history
    hs, he = _local(v.get("HISTORY_START"), tz), _local(v.get("HISTORY_END"), tz)
    m, cs, why, covers = None, [], None, False
    src = v.get("CANDLES")
    path = None if not src else Path(src) if Path(src).is_absolute() else base / src
    if not src:
        why = "no CANDLES file, so the oracle has no bars to run on"
    elif not path.exists():
        why = f"CANDLES file {src} not found"
    else:
        cs = [c for c in load_tradingview_export(path, tz)[0]
              if (hs is None or c.time >= hs) and (he is None or c.time <= he)]
        if not cs:
            raise ValueError(f"{src}: no candle between HISTORY_START and HISTORY_END")
        validate_candles(cs, tick)
        if len(cs) > 1 and "TIMEFRAME" in v:
            step = statistics.median(b.time - a.time for a, b in zip(cs, cs[1:]))
            add("candles", MATCH if step == tf * 1000 else DIFF,
                f"bar spacing {step / 60000:g} min · TIMEFRAME {v['TIMEFRAME']}")
        for key, want, got in (("HISTORY_START", hs, cs[0].time), ("HISTORY_END", he, cs[-1].time)):
            add("candles", NOBS if want is None else MATCH if got == want else DIFF,
                f"{key} {fmt(want)} · candles {'start' if key == 'HISTORY_START' else 'end'} {fmt(got)}")
        if "HISTORY_BARS" in v:
            add("candles", MATCH if v["HISTORY_BARS"] == len(cs) else DIFF,
                f"bars in Pine's loaded history {v['HISTORY_BARS']} · candles {len(cs)}")
        covers = cs[0].time == hs and cs[-1].time == he and v.get("HISTORY_BARS", len(cs)) == len(cs)
        m = IstModel(settings).run(cs)
        if not covers:
            notes.append("the candles are not exactly Pine's loaded history (debug row 34: start, end, bars): counts are "
                         "NOT OBSERVABLE and event differences may come from the data, not the logic")

    # counts vs the oracle: only when the oracle replayed exactly Pine's history
    want = oracle_counts(m) if m and covers else {}
    for key in COUNTS:
        if key in v:
            add("summary", NOBS if not want else MATCH if v[key] == want[key] else DIFF,
                f"{_label(key)}: Pine {v[key]} · oracle " + (str(want[key]) if want else "not run" if m is None
                                                              else "not comparable (candles ≠ loaded history)"))

    # events: identity (type, id), direction, time, price; duplicates; missing inside each block
    keep = set(re.findall(r"[A-Z]+(?:_[A-Z]+)*", v.get("EVENT_FILTER", "").upper()))   # a filtered Pine Logs copy
    if keep - set(FAMILIES) - set(TYPES):
        raise ValueError(f"EVENT_FILTER: unknown {sorted(keep - set(FAMILIES) - set(TYPES))} (families: {', '.join(FAMILIES)})")
    shown = lambda t: not keep or t in keep or t.split("_")[0] in keep
    by_sid, by_time = {}, {}
    for e in (m.events if m else []):
        by_sid.setdefault((e.type, e.sid), []).append(e)
        by_time.setdefault((e.type, e.time), []).append(e)
    lo, hi = (cs[0].time, cs[-1].time) if cs else (None, None)
    for b, block in enumerate(man["blocks"], 1):
        seen, once, matched = set(), {}, set()
        for o in block:
            txt = f"block {b} line {o['line']}: {o['text']}"
            k1 = (o["type"], o["dir"], o["sid"], o["time"])
            if k1 in seen:
                add("events", DIFF, f"{txt}: listed twice in one block (Pine logged it twice, or it was pasted twice)")
                continue
            seen.add(k1)
            k2 = (o["type"], o["dir"], o["sid"])
            if o["type"] in ONCE and o["sid"] is not None:
                if k2 in once:
                    add("events", DIFF, f"{txt}: a one-time event also logged at {fmt(once[k2])}")
                once[k2] = o["time"]
            if o["type"] == "LEVEL_SET":
                add("events", NOBS, f"{txt}: request.security values and the previous-day definition are not modelled")
                continue
            if m is None:
                continue
            t = o["time"] if o["time"] is not None else o["sid"]
            if not lo <= t <= hi:
                add("events", NOBS, f"{txt}: outside the candles ({fmt(lo)} → {fmt(hi)})")
                continue
            cands = by_sid.get((o["type"], o["sid"]), []) if o["sid"] is not None else by_time.get((o["type"], o["time"]), [])
            if not cands:
                add("events", DIFF, f"{txt}: not in the oracle (an extra Pine event)")
                continue
            same = [e for e in cands if e.dir == o["dir"]]
            if not same:
                matched.add(id(cands[0]))
                add("events", DIFF, f"{txt}: direction Pine {o['dir']:+d} · oracle {cands[0].dir:+d}")
                continue
            e = next((e for e in same if _same_px(o["price"], e.price, tick)), same[0])
            matched.add(id(e))
            bad = []
            if o["time"] is not None and o["time"] != e.time:
                bad.append(f"time Pine {fmt(o['time'])} · oracle {fmt(e.time)}")
            if o["has_price"] and not _same_px(o["price"], e.price, tick):
                bad.append(f"price Pine {o['price']} · oracle {e.price}"
                           + (f" (prints as {pine_px(e.price, tick)})" if e.price is not None else ""))
            blind = [n for n, x in (("time", o["time"]), ("id", o["sid"]), ("price", o["has_price"] or None)) if x is None]
            add("events", DIFF if bad else MATCH, txt + (": " + "; ".join(bad) if bad else "")
                + (f" ({', '.join(blind)} not observed)" if blind else ""))
        if m is None:
            if block:
                add("events", NOBS, f"block {b}: {len(block)} events not compared with the oracle: {why}")
            continue
        times = [o["time"] for o in block if o["time"] is not None]
        if len(set(times)) < 2:
            add("events", NOBS, f"block {b}: missing events not observable (needs events on two bars or more)")
            continue
        t0, t1 = min(times), max(times)          # the oldest bar may be cut: its earlier events are not shown
        for e in m.events:
            if t0 < e.time <= t1 and e.type != "LEVEL_SET" and shown(e.type) and id(e) not in matched:
                add("events", DIFF, f"block {b}: missing in Pine: {pine_text(e, tz, tick)} (oracle; the block covers "
                                    f"{fmt(t0)} → {fmt(t1)}" + (f", {' '.join(sorted(keep))} only)" if keep else ")"))
    cnt = Counter(c["status"] for c in checks)
    return {"status": "COMPARED", "mode": "MANUAL EVENT PARITY", "checks": checks, "counts": cnt,
            "differences": cnt[DIFF], "oracle": m is not None, "why": why, "notes": notes, "about": about,
            "symbol": v.get("SYMBOL", "—"), "timeframe": v.get("TIMEFRAME", "—"),
            "candles": f"{src} · {len(cs)} bars {fmt(cs[0].time)} → {fmt(cs[-1].time)}" if cs else why,
            "events": sum(map(len, man["blocks"])), "blocks": len(man["blocks"])}


def run(path: Path = MANUAL, preset: str | None = None) -> dict:
    path = Path(path)
    if not path.exists():
        return {"status": "NO OBSERVED DATA", "differences": 0, "reason": f"{path.name} not present"}
    return compare(parse(path.read_text(encoding="utf-8")), preset, path.parent)


def verdict(r: dict) -> str:
    c = r["counts"]
    tally = f"{c[MATCH]} MATCH · {c[DIFF]} DIFFERENCE · {c[NOBS]} NOT OBSERVABLE"
    if r["differences"]:
        return f"MANUAL EVENT PARITY: FAIL — {tally}"
    if not r["oracle"]:
        return f"MANUAL EVENT PARITY: INCOMPLETE — {tally}; nothing was compared with the oracle ({r['why']})"
    return f"MANUAL EVENT PARITY: PASS — {tally}"


def show(r: dict, build: str) -> None:
    print("MANUAL EVENT PARITY — the settings, counts and events you copied, compared with the oracle.")
    print("This is NOT full bar-by-bar parity: only what you supplied is checked.\n")
    print(f"  {r['symbol']} · {r['timeframe']} · IST {build} · {r['about']}")
    print(f"  candles: {r['candles']}")
    print(f"  events: {r['events']} lines in {r['blocks']} block(s)")
    for n in r["notes"]:
        print(f"  NOTE: {n}")
    for sec in SECTIONS:
        rows = [c for c in r["checks"] if c["section"] == sec]
        if rows:
            print(f"\n  {sec.upper()}")
            for c in rows:
                print(f"    {c['status']:<15}{c['text']}")
    print(f"\n  {verdict(r)}")
    print("  FULL CSV BAR-BY-BAR PARITY: not run here (it needs the Data Window export).")
