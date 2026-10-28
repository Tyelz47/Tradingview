"""Bounded Pine-Log parity. IST's "Parity capture" writes the last N closed bars to
Pine Logs: a CAPTURE line (settings), then per bar one BAR line (OHLC and the per-bar
debug values) followed by that bar's events, then END. Pasted into a file, the BAR lines
rebuild the exact candles of that window; the oracle runs on them alone and every bar
after the warm-up is compared with what Pine logged.

BOUNDED PINE-LOG BAR-BY-BAR PARITY covers only the captured window. It is not FULL CSV
BAR-BY-BAR PARITY: whatever was born before the window (older levels and FVGs, EQ
clusters, engine memory, sessions already running) is invisible to the oracle, so it is
reported NOT OBSERVABLE and never compared.
"""
from __future__ import annotations

import csv
import io
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from validation import VALIDATION_DIR
from validation.models.ist import IstModel
from validation.models.events import LRL_TERMINAL
from validation.models.types import MODULES, PRESETS, Candle, LrlSettings, Settings
from validation.parity import oracle_series
from validation.parity.manual import DIFF, MATCH, NOBS, _ANY_NAME, _event, _fmt, _same_px, _tf_seconds, pine_text

PARITY_DIR = VALIDATION_DIR / "parity"
TOL = 1e-6                     # Pine prints these values with 8 decimals
SECTIONS = ("settings", "bars", "events", "lrl")
# CAPTURE key → (LrlSettings field, type): the frozen LRL constants Pine ran with (v0.5.0-dev+).
LRL_HEAD = {"lrlleft": ("left", int), "lrlright": ("right", int), "lrltol": ("tol_k", float), "lrlgap": ("gap", int),
            "lrlsep": ("sep_k", float), "lrldrop": ("drop_k", float), "lrltra": ("tra_len", int),
            "lrlcand": ("cand_memory", int), "lrlmem": ("memory", int)}
# BAR key → oracle series (parity.SERIES). The take codes are left out on purpose: on one
# bar a level born before the window can be taken too, and the oracle cannot know it.
FIELDS = {"FV": "fvg_verdict", "FR": "fvg_required", "SH": "bsl_pivot", "SL": "ssl_pivot",
          "RH": "bsl_reaction", "RL": "ssl_reaction", "RQ": "liq_required",
          "DH": "bsl_dominance", "DL": "ssl_dominance"}
NEW_IN_044 = {"DH", "DL"}      # absent from captures of IST builds before v0.4.4-dev (C1)
LABELS = {"fvg_verdict": "FVG verdict", "fvg_required": "FVG required gap", "bsl_pivot": "swing high verdict",
          "ssl_pivot": "swing low verdict", "bsl_reaction": "swing high reaction",
          "ssl_reaction": "swing low reaction", "liq_required": "required reaction",
          "bsl_dominance": "dominance reference high", "ssl_dominance": "dominance reference low"}
HEAD = ("tick", "tz", "confirmed", "liq", "preset", "left", "right", "k", "eqtol", "eqmin", "liqmem",
        "fvgticks", "fvgtra", "fvgrng", "fvglen", "fvgmem", "ses", "bars", "warmup")
_TOKEN = re.compile(r"\b(CAPTURE|BAR|END)\|(.*)$")
_CSV_ROW = re.compile(r'^\s*\d{4}-\d\d-\d\d[^,"|]*,"')   # a `date,"message"` row without its header


# ── parsing ────────────────────────────────────────────────────────────────────

def _pairs(parts: list[str]) -> dict:
    out = {}
    for p in parts:
        k, eq, v = p.partition("=")
        if not eq:
            raise ValueError(f"expected key=value, got {p!r}")
        out[k.strip()] = v.strip()
    return out


def _num(k: str, v: str) -> float | None:
    if v.lower() == "na":
        return None
    try:
        return float(v)
    except ValueError:
        raise ValueError(f"{k}={v}: not a number") from None


def _bar(parts: list[str], tick: float | None) -> dict:
    ts, kv = parts[0], _pairs(parts[1:])
    try:
        t = int(datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z").timestamp() * 1000)
    except ValueError:
        raise ValueError(f"malformed timestamp {ts!r} (expected yyyy-MM-ddTHH:mm:ss±hhmm)") from None
    miss = [k for k in ("i", "O", "H", "L", "C", *FIELDS) if k not in kv and k not in NEW_IN_044]
    if miss:
        raise ValueError(f"missing {', '.join(miss)}")
    ohlc = [_num(k, kv[k]) for k in "OHLC"]
    if None in ohlc:
        raise ValueError("wrong OHLC: na")
    c = Candle(t, *ohlc)
    bad = c.problems() + [f"{k} {v} is off the {tick} tick grid" for k, v in zip("OHLC", ohlc)
                          if tick and abs(v / tick - round(v / tick)) > 1e-6]
    if bad:
        raise ValueError(f"wrong OHLC: {'; '.join(bad)}")
    return {"i": int(kv["i"]), "time": t, "candle": c,
            "vals": {s: _num(k, kv[k]) for k, s in FIELDS.items() if k in kv}, "lrl": _lrl_fields(kv)}


def _lrl_fields(kv: dict) -> dict | None:
    """LH / LL: every active LRL as id:boundary now:previous boundary (';'-separated);
    KH / KL: candidates per side. None for a build without LRL (before v0.5.0-dev)."""
    if not {"LH", "LL", "KH", "KL"} <= set(kv):
        return None
    out = {}
    for key, name in (("LH", "high"), ("LL", "low")):
        recs = {}
        for item in filter(None, kv[key].split(";")):
            parts = item.split(":")
            if len(parts) != 3:
                raise ValueError(f"{key}: expected id:boundary:previous, got {item!r}")
            recs[int(parts[0])] = (_num(key, parts[1]), _num(key, parts[2]))
        out[name] = recs
    out["cand_high"], out["cand_low"] = int(kv["KH"]), int(kv["KL"])
    return out


def _messages(text: str) -> tuple[list[tuple[int, str, str | None]], str]:
    """Every log message as (line, message, date), and the input kind.

    A TradingView Pine Logs file (`Date,Message`, recognised by its header) is read with
    the csv module, which undoes the quoting and the doubled quotes; only the Message field
    is parsed, the Date column is kept for diagnostics. Any other text is read line by line
    (the pane's own timestamp in front of a message is ignored); a `date,"message"` row
    pasted without its header is decoded the same way."""
    text = text.lstrip(chr(0xFEFF))
    first = next((ln for ln in text.splitlines() if ln.strip()), "")
    try:
        cols = [c.strip().lower() for c in next(csv.reader([first]), [])]
    except csv.Error:
        cols = []
    if len(cols) >= 2 and {"date", "message"} & set(cols):
        if "message" not in cols:
            raise ValueError(f"capture rejected: the CSV has no Message column (header: {first.strip()})")
        mi, di = cols.index("message"), cols.index("date") if "date" in cols else None
        rows = csv.reader(io.StringIO(text, newline=""), strict=True)
        out, header = [], True
        try:
            for row in rows:
                if not any(c.strip() for c in row):
                    continue
                if header:
                    header = False
                    continue
                if len(row) <= mi:
                    raise ValueError(f"capture rejected: line {rows.line_num}: {len(row)} column(s), no Message field")
                out.append((rows.line_num, row[mi], row[di] if di is not None and di < len(row) else None))
        except csv.Error as e:
            raise ValueError(f"capture rejected: malformed CSV at line {rows.line_num}: {e}") from None
        return out, "TradingView Pine Logs CSV (Date,Message)"
    out = []
    for n, ln in enumerate(text.splitlines(), 1):
        if _CSV_ROW.match(ln):
            try:
                row = next(csv.reader([ln], strict=True))
            except csv.Error as e:
                raise ValueError(f"capture rejected: line {n}: malformed CSV row: {e}") from None
            out.append((n, row[-1], row[0]))
        else:
            out.append((n, ln, None))
    return out, "pasted text"


def _runs(msgs: list) -> tuple[list[dict], int]:
    """The capture runs in log order, each CAPTURE … END, never merged with another. A file
    saved newest first (BAR times mostly decreasing) is turned around first."""
    ts = []
    for _, msg, _ in msgs:
        m = re.search(r"\bBAR\|([^|]+)\|", msg)
        if m:
            try:
                ts.append(datetime.strptime(m[1].strip(), "%Y-%m-%dT%H:%M:%S%z"))
            except ValueError:
                pass
    if 2 * sum(b < a for a, b in zip(ts, ts[1:])) > len(ts):
        msgs = msgs[::-1]
    runs, cur, outside = [], None, 0
    for n, msg, _ in msgs:
        m = _TOKEN.search(msg)
        if m and m[1] == "CAPTURE":
            if cur is not None:
                runs.append(cur)                              # no END before the next CAPTURE
            cur = {"lines": [], "end": False}
        if cur is None:
            outside += bool(msg.strip())
            continue
        cur["lines"].append((n, msg))
        if m and m[1] == "END":
            cur["end"] = True
            runs.append(cur)
            cur = None
    if cur is not None:
        runs.append(cur)
    return runs, outside


def _parse_run(lines: list[tuple[int, str]]) -> tuple[dict | None, list[str]]:
    """One CAPTURE … END run → (capture, []) or (None, every problem numbered by line)."""
    n0, first = lines[0]
    try:
        head = _pairs([p for p in _TOKEN.search(first)[2].split("|") if p.strip()])
        miss = [k for k in HEAD if k not in head]
        if miss:
            raise ValueError(f"missing {', '.join(miss)} (is it the same IST build?)")
        tick, expected = float(head["tick"]), int(head["bars"]) + int(head["warmup"])
    except ValueError as e:
        return None, [f"line {n0}: CAPTURE: {e}"]
    bars, raw_events, end, ignored, errors = [], [], None, 0, []
    for n, line in lines[1:]:
        m = _TOKEN.search(line)
        try:
            if m and m[1] == "BAR":
                bars.append({**_bar([p.strip() for p in m[2].split("|")], tick), "line": n})
            elif m and m[1] == "END":
                end = int(_pairs([m[2]])["bars"])
            elif not m and _ANY_NAME.search(line):
                raw_events.append((n, line))
            elif not m and line.strip():
                ignored += 1
        except (ValueError, KeyError) as e:
            errors.append(f"line {n}: {m[1] if m else 'event'}: {e}")
    events = []
    for n, line in raw_events:
        try:
            events.append({**_event(line, head["tz"], None), "line": n})
        except ValueError as e:
            errors.append(f"line {n}: {e}")
    bars.sort(key=lambda b: b["i"])
    count = Counter(b["i"] for b in bars)
    for i, k in sorted(count.items()):
        if k > 1:
            errors.append(f"bar i={i} appears {k} times (lines {', '.join(str(b['line']) for b in bars if b['i'] == i)}): "
                          f"paste the capture once")
    for a, b in zip(bars, bars[1:]):
        if b["i"] > a["i"] + 1:
            errors.append(f"bar i={a['i'] + 1}" + (f"…{b['i'] - 1}" if b["i"] > a["i"] + 2 else "")
                          + f" missing (between lines {a['line']} and {b['line']}): copy the whole capture")
        elif b["i"] == a["i"] + 1 and b["time"] <= a["time"]:
            errors.append(f"line {b['line']}: bar i={b['i']} is not later than bar i={a['i']}")
    if end is None:
        errors.append("no END line: the last bar was still open when the logs were copied or saved, or the "
                      "file is cut; take them again once END has appeared")
    elif end != len(count):
        errors.append(f"END says {end} bars but {len(count)} BAR lines were pasted")
    if len(count) != expected:
        errors.append(f"{len(count)} BAR lines, but the CAPTURE line expects {expected} "
                      f"(bars {head['bars']} + warm-up {head['warmup']})")
    if errors:
        return None, errors
    return {"head": head, "bars": bars, "events": events, "end": end, "ignored": ignored}, []


def parse(text: str) -> dict:
    """Pine Logs → one capture: {"head", "bars", "events", "end", "ignored", "notes",
    "source"}. Plain pasted text and TradingView's saved `Date,Message` CSV are both read
    (detected from the header). Messages are found by their token (CAPTURE|, BAR|, END|,
    an event name). Several capture runs are never merged: the latest complete and valid
    run is used and every run is listed in the notes. Anything that would make the
    candles inexact rejects the run (ValueError, every problem numbered by line)."""
    msgs, source = _messages(text)
    runs, outside = _runs(msgs)
    if not runs:
        raise ValueError("capture rejected:\n  no CAPTURE line: take the capture from its first line (CAPTURE|…)")
    for k, r in enumerate(runs, 1):
        r.update(k=k, first=r["lines"][0][0], last=r["lines"][-1][0])
        r["cap"], r["errs"] = _parse_run(r["lines"])
    good = [r for r in runs if r["cap"]]
    if not good:
        errs = runs[0]["errs"] if len(runs) == 1 else \
            [f"run {r['k']} (lines {r['first']}–{r['last']}): {e}" for r in runs for e in r["errs"][:5]]
        lead = "capture rejected:" if len(runs) == 1 else \
            f"capture rejected: none of the {len(runs)} capture runs in the file is complete and valid:"
        raise ValueError(lead + "\n  " + "\n  ".join(errs[:30])
                         + (f"\n  … {len(errs) - 30} more" if len(errs) > 30 else ""))
    use, notes = good[-1], []
    if len(runs) > 1:
        notes.append(f"{len(runs)} capture runs in the file (never merged); used run {use['k']}, the latest complete one:")
        for r in runs:
            c = r["cap"]
            what = (f"{_fmt(c['bars'][0]['time'], c['head']['tz'])} → {_fmt(c['bars'][-1]['time'], c['head']['tz'])}, "
                    f"{len(c['bars'])} bars, preset {c['head']['preset']}") if c else f"not usable: {r['errs'][0]}"
            notes.append(f"  {'USED' if r is use else 'skipped'} run {r['k']} (lines {r['first']}–{r['last']}): {what}")
    if outside:
        notes.append(f"{outside} log lines outside any capture run were ignored")
    return {**use["cap"], "notes": notes, "source": source}


# ── comparison ─────────────────────────────────────────────────────────────────

def settings_of(h: dict) -> tuple[Settings, bool]:
    """The oracle's settings from the CAPTURE line, and whether the session windows are
    plain HHMM-HHMM (anything else is not modelled)."""
    wins = [tuple(w.rsplit("@", 1)) for w in h["ses"].split(",")]
    ses_ok = all(len(w) == 2 and re.fullmatch(r"\d{4}-\d{4}", w[1]) for w in wins)
    tf = _tf_seconds(h.get("tf", "1"))
    s = {"tick": float(h["tick"]),
         "fvg": {"min_ticks": int(h["fvgticks"]), "k_tra": float(h["fvgtra"]), "k_rng": float(h["fvgrng"]),
                 "length": int(h["fvglen"]), "memory": int(h["fvgmem"])},
         # no w: a build before C1 (v0.4.4-dev), replayed with the definition it used (no dominance)
         "liq": {"left": int(h["left"]), "right": int(h["right"]), "k": float(h["k"]), "dom": int(h.get("w", "0")),
                 "tol_ticks": int(h["eqtol"]), "min_touch": int(h["eqmin"]), "memory": int(h["liqmem"])},
         "sessions": {"timezone": h["tz"], "timeframe_sec": tf, **({"windows": wins} if ses_ok else {})},
         "levels": {"timeframe_sec": tf}}
    if h.get("lrl") == "1":                   # v0.5.0-dev+: the LRL engine ran in Pine
        s["modules"] = [*MODULES, "lrl"]
        s["lrl"] = {f: typ(h[k]) for k, (f, typ) in LRL_HEAD.items() if k in h}
    return Settings.from_dict(s), ses_ok


def compare(cap: dict, preset: str | None = None) -> dict:
    h, bars, checks, notes = cap["head"], cap["bars"], [], list(cap.get("notes", []))
    add = lambda sec, st, txt: checks.append({"section": sec, "status": st, "text": txt})
    tz = h["tz"]
    fmt = lambda ms: _fmt(ms, tz)
    name = h["preset"].lower()
    if preset and preset != name:
        raise ValueError(f"the capture was made with preset {h['preset']} but --preset {preset} was given")
    if h["liq"] != "1":
        raise ValueError("the capture was made with the liquidity engine OFF: turn it on and capture again")
    s, ses_ok = settings_of(h)
    if name in PRESETS:
        for key, got, want in zip(("left", "right", "k", "W"), (s.liq.left, s.liq.right, s.liq.k, s.liq.dom),
                                  PRESETS[name]):
            if key == "W" and "w" not in h:
                add("settings", NOBS, f"{name} W: not in this capture (IST before v0.4.4-dev); replayed without "
                                      f"dominance, the definition that build used")
                continue
            add("settings", MATCH if abs(got - want) < 1e-9 else DIFF, f"{name} {key}: Pine {got:g} · oracle preset {want:g}")
    add("settings", MATCH if h["confirmed"] == "1" else DIFF,
        "confirmed only: ON" if h["confirmed"] == "1" else "confirmed only: OFF · the oracle models ON only")
    lrl_on = "lrl" in s.modules
    if lrl_on:                                                # the frozen LRL constants (docs/LRL.md)
        approved = LrlSettings()
        for k, (f, _) in LRL_HEAD.items():
            got, ok = getattr(s.lrl, f), getattr(approved, f)
            add("settings", MATCH if k in h and got == ok else DIFF,
                f"LRL {f}: Pine {h.get(k, 'missing')} · approved {ok:g}")

    # bars: the oracle replays exactly the captured candles; the warm-up is never compared
    candles = [b["candle"] for b in bars]
    m = IstModel(s)
    want = oracle_series(candles, s, m)
    w_fvg = s.fvg.lookback                                    # warm-up from the dependency graph (models.types)
    w_swing = s.liq.lookback                                  # bars a swing bar X needs before it
    w_liq = w_swing + s.liq.right
    w_need = max(w_fvg, w_liq, s.lrl.lookback if lrl_on else 0)
    if int(h["warmup"]) < w_need:
        notes.append(f"Pine captured {h['warmup']} warm-up bars; {w_need} are needed, so fewer bars are compared")
    start = {k: w_fvg if k.startswith("fvg") else w_liq for k in FIELDS.values()}
    compared, bar_diffs = Counter(), []
    for t, b in enumerate(bars):
        for k, st in start.items():
            if t < st or k not in b["vals"]:
                continue
            p, o = b["vals"][k], want[k][t]
            if k.endswith("_reaction") and o is None:         # the oracle keeps the reaction of created levels
                continue
            compared[k] += 1
            if (p is None) != (o is None) or (p is not None and abs(p - o) > TOL):
                bar_diffs.append(k)
                add("bars", DIFF, f"{fmt(b['time'])} (i={b['i']}) {LABELS[k]}: Pine {p} · oracle {o}")
    for k in FIELDS.values():
        if compared[k] and k not in bar_diffs:
            add("bars", MATCH, f"{LABELS[k]}: {compared[k]} bars from {fmt(bars[start[k]]['time'])}")
        elif not compared[k]:
            add("bars", NOBS, f"{LABELS[k]}: " + ("no bar after the warm-up" if any(k in b["vals"] for b in bars)
                                                    else "not in this capture (IST before v0.4.4-dev)"))

    def totals(get) -> dict:
        sh, sl, fv = get("bsl_pivot"), get("ssl_pivot"), get("fvg_verdict")
        return {"swing highs": f"{sh.count(2)} PASS · {sh.count(1)} REJECT",
                "swing lows": f"{sl.count(2)} PASS · {sl.count(1)} REJECT",
                "FVG": f"{fv.count(2)} bull · {fv.count(-2)} bear · {fv.count(1) + fv.count(-1)} rejected"}
    tot = {"pine": totals(lambda k: [b["vals"][k] for b in bars[start[k]:]]),
           "oracle": totals(lambda k: want[k][start[k]:])}

    # events: only structures born after the warm-up and never dropped from memory
    t0, t_end = bars[0]["time"], bars[-1]["time"]
    t_fvg = bars[w_fvg]["time"] if len(bars) > w_fvg else None
    t_swing = bars[w_swing]["time"] if len(bars) > w_swing else None
    is_lrl = lambda e: e["type"].startswith("LRL_")           # compared in their own section (_compare_lrl)
    oracle = [{"time": e.time, "type": e.type, "dir": e.dir, "sid": e.sid, "price": e.price, "e": e} for e in m.events
              if not e.type.startswith("LRL_")]
    pine_events = [e for e in cap["events"] if not is_lrl(e)]
    fam = lambda e: e["type"].split("_")[0]
    drops = {}
    for e in oracle + pine_events:
        if e["type"].endswith("DROPPED_MEMORY"):
            key = (fam(e), e["dir"], e["sid"])
            drops[key] = min(drops.get(key, e["time"]), e["time"])

    def outside(e) -> str | None:
        f = fam(e)
        if e["type"] == "LEVEL_SET":
            return "LEVEL_SET: request.security values and the previous-day definition are not modelled"
        if e["type"].endswith("DROPPED_MEMORY"):
            return "memory drops: Pine's memory also holds records from before the capture"
        if f in ("EQH", "EQL"):
            return "EQ clusters: a cluster can include levels from before the capture"
        if e["time"] is None or not t0 <= e["time"] <= t_end:
            return "outside the captured bars"
        if f == "SESSION" and (not ses_ok or e["sid"] is None or e["sid"] <= t0):
            return "sessions that started before the capture (or non-standard session strings)"
        if f == "FVG" and (t_fvg is None or e["sid"] is None or e["sid"] < t_fvg):
            return "FVGs born in the warm-up or before the capture"
        if f in ("BSL", "SSL") and (t_swing is None or e["sid"] is None or e["sid"] < t_swing):
            return "levels whose swing is in the warm-up or before the capture"
        if (f, e["dir"], e["sid"]) in drops and e["time"] >= drops[(f, e["dir"], e["sid"])]:
            return "structures already dropped from memory on one side"
        return None

    ident = lambda e: (e["type"], e["dir"], e["sid"])
    by_id = {ident(e): e for e in oracle if outside(e) is None}
    seen, matched, nobs = set(), Counter(), Counter()
    for o in pine_events:
        why = outside(o)
        if why:
            nobs[why] += 1
            continue
        if (ident(o), o["time"]) in seen:
            add("events", DIFF, f"line {o['line']}: {o['text']}: logged twice")
            continue
        seen.add((ident(o), o["time"]))
        e = by_id.pop(ident(o), None)
        if e is None:
            add("events", DIFF, f"line {o['line']}: {o['text']}: not in the oracle (an extra Pine event)")
            continue
        bad = ([f"time Pine {fmt(o['time'])} · oracle {fmt(e['time'])}"] if o["time"] != e["time"] else []) + \
              ([f"price Pine {o['price']} · oracle {e['price']}"] if o["has_price"] and
               not _same_px(o["price"], e["price"], s.tick) else [])
        if bad:
            add("events", DIFF, f"line {o['line']}: {o['text']}: {'; '.join(bad)}")
        else:
            matched[o["type"]] += 1
    for e in sorted(by_id.values(), key=lambda e: e["time"]):
        add("events", DIFF, f"missing in Pine: {pine_text(e['e'], tz, s.tick)} (oracle)")
    for typ, n in sorted(matched.items()):
        add("events", MATCH, f"{typ}: {n}")
    for why, n in nobs.most_common():
        add("events", NOBS, f"{n} Pine events not compared: {why}")
    lrl = _compare_lrl(cap, m, want, s, add, fmt) if lrl_on else None
    sym = re.search(r'"symbol"\s*:\s*"([^"]+)"', h.get("sym", ""))       # extended tickerid: a JSON object
    cnt = Counter(c["status"] for c in checks)
    return {"status": "COMPARED", "mode": "BOUNDED PINE-LOG BAR-BY-BAR PARITY", "checks": checks, "counts": cnt,
            "differences": cnt[DIFF], "notes": notes, "totals": tot, "bars": len(bars), "lrl": lrl,
            "compared_bars": max(0, len(bars) - max(w_fvg, w_liq)), "warmup": max(w_fvg, w_liq),
            "series": sum(1 for k in FIELDS.values() if compared[k]),
            "matched_events": sum(matched.values()), "window": f"{fmt(t0)} → {fmt(t_end)}",
            "symbol": sym[1] if sym else h.get("sym", "—"), "source": cap.get("source", "—"),
            "about": (f"preset {name} → left {s.liq.left} · right {s.liq.right} · k {s.liq.k:g} · EQ {s.liq.tol_ticks} "
                      f"ticks · min {s.liq.min_touch} · tick {s.tick:g} · {tz}")}


def _kv(text: str) -> dict:
    """The key=value parts of an event's audit text (after 'px=… · ')."""
    m = re.search(r"\bpx=\S+ · (.*)$", text)
    return {k.strip(): v.strip() for k, eq, v in (p.partition("=") for p in (m[1] if m else "").split(" · ")) if eq}


def _compare_lrl(cap: dict, m: IstModel, want: dict, s: Settings, add, fmt) -> dict:
    """LRL in the captured window: every LRL event (type, side, id, bar, price, τ, points,
    boundaries) and, per bar and side, every active LRL's boundary now and on the previous
    bar, then the candidate counts.

    NOT OBSERVABLE (never compared), because the oracle starts empty at the first captured bar:
    * an LRL whose first point lies in the first `tra_len` bars (its τ needs the TR average
      there) or before the capture;
    * any LRL sharing a point (same side) with such an LRL, in either stream, transitively:
      that point was a member, or spent, in one stream and free in the other;
    * memory drops (Pine's memory also holds records from before the capture);
    * candidate counts before bar `lookback` (= right + 2 × gap + TR length), while such an LRL
      is active, and for 2 × gap + right bars after one of its points."""
    ls, bars, tz = s.lrl, cap["bars"], cap["head"]["tz"]
    times = [b["time"] for b in bars]
    index = {t: i for i, t in enumerate(times)}
    t_anchor = times[ls.tra_len] if len(times) > ls.tra_len else float("inf")
    names = {1: "high", -1: "low"}
    pine = [e for e in cap["events"] if e["type"].startswith("LRL_")]
    for e in pine:
        e["kv"] = _kv(e["text"])
    oracle = [{"time": e.time, "type": e.type, "dir": e.dir, "sid": e.sid, "price": e.price, "kv": _kv(f"px=0 · {e.meta}"),
               "e": e} for e in m.events if e.type.startswith("LRL_")]
    # points (side, bar time) of every LRL known in each stream
    pts = {"pine": {}, "oracle": {}}
    for src, evs in (("pine", pine), ("oracle", oracle)):
        for e in evs:
            if "pts" in e["kv"]:
                pts[src].setdefault((e["dir"], e["sid"]), set()).update((e["dir"], int(t)) for t in e["kv"]["pts"].split(","))
    keys = {(e["dir"], e["sid"]) for e in pine + oracle}
    for b in bars:
        for g in (1, -1):
            keys |= {(g, i) for i in b["lrl"][names[g]]}
    for want_side, g in (("lrl_high", 1), ("lrl_low", -1)):
        for d in want.get(want_side, []):
            keys |= {(g, i) for i in d}
    nobs = {k for k in keys if k[1] < t_anchor}
    nobs |= {(e["dir"], e["sid"]) for e in pine + oracle if e["type"] == "LRL_DROPPED_MEMORY"}
    grow = True
    while grow:                                               # contamination by shared points, to closure
        bad = set().union(*(pts[src].get(k, set()) for src in pts for k in nobs))
        more = {k for k in keys - nobs if (pts["pine"].get(k, set()) | pts["oracle"].get(k, set())) & bad}
        nobs |= more
        grow = bool(more)

    # events
    ev_key = lambda e: (e["type"], e["dir"], e["sid"], e["time"])
    left = {ev_key(e): e for e in oracle if (e["dir"], e["sid"]) not in nobs and e["type"] != "LRL_DROPPED_MEMORY"}
    matched, nobs_ev, diffs = Counter(), Counter(), 0
    num = lambda kv, k: float(kv[k]) if k in kv and kv[k] != "na" else None
    for o in pine:
        if o["type"] == "LRL_DROPPED_MEMORY":
            nobs_ev["memory drops: Pine's memory also holds LRLs from before the capture"] += 1
            continue
        if (o["dir"], o["sid"]) in nobs:
            nobs_ev["LRLs anchored in the TR warm-up or before the capture, or sharing a point with one"] += 1
            continue
        e = left.pop(ev_key(o), None)
        if e is None:
            add("lrl", DIFF, f"line {o['line']}: {o['text']}: not in the oracle (an extra Pine event)")
            diffs += 1
            continue
        bad = [] if _same_px(o["price"], e["price"], s.tick) else [f"price Pine {o['price']} · oracle {e['price']}"]
        for k in ("tau", "bnow", "bprev"):
            a, b = num(o["kv"], k), num(e["kv"], k)
            if (a is None) != (b is None) or (a is not None and abs(a - b) > TOL):
                bad.append(f"{k} Pine {o['kv'].get(k)} · oracle {e['kv'].get(k)}")
        if o["kv"].get("pts") != e["kv"].get("pts") or o["kv"].get("n") != e["kv"].get("n"):
            bad.append(f"points Pine {o['kv'].get('pts')} · oracle {e['kv'].get('pts')}")
        if bad:
            add("lrl", DIFF, f"line {o['line']}: {o['text']}: {'; '.join(bad)}")
            diffs += 1
        else:
            matched[o["type"]] += 1
    for e in sorted(left.values(), key=lambda e: e["time"]):
        add("lrl", DIFF, f"missing in Pine: {pine_text(e['e'], tz, s.tick)} (oracle)")
        diffs += 1

    # per bar: the boundaries of every observable active LRL, then the candidate counts
    spans = []
    for g in (1, -1):
        for k, src in ((names[g], "pine"), (f"lrl_{names[g]}", "oracle")):
            for t in range(len(bars)):
                cur = bars[t]["lrl"][k] if src == "pine" else want[k][t]
                spans += [(g, t) for i in cur if (g, i) in nobs]
    busy = set(spans)
    for (g, _), ps in ((k, v) for src in pts for k, v in pts[src].items() if k in nobs):
        for _, t in ps:
            if t in index:
                busy |= {(g, j) for j in range(index[t], index[t] + 2 * ls.gap + ls.right + 2)}
    bound_bars, bound_vals, cand_bars = 0, 0, 0
    for t, b in enumerate(bars):
        for g in (1, -1):
            n = names[g]
            p = {i: v for i, v in b["lrl"][n].items() if (g, i) not in nobs}
            o = {i: v for i, v in want[f"lrl_{n}"][t].items() if (g, i) not in nobs}
            bound_bars += 1
            if p.keys() != o.keys():
                add("lrl", DIFF, f"{fmt(b['time'])} (i={b['i']}) active {n}-side LRLs: Pine {sorted(p)} · oracle {sorted(o)}")
                diffs += 1
                continue
            for i in p:
                bound_vals += 1
                if any(x is None or abs(x - y) > TOL for x, y in zip(p[i], o[i])):
                    add("lrl", DIFF, f"{fmt(b['time'])} (i={b['i']}) LRL {fmt(i)} {n} boundary now · previous: "
                                     f"Pine {p[i]} · oracle {o[i]}")
                    diffs += 1
            if t >= ls.lookback and (g, t) not in busy:
                cand_bars += 1
                if b["lrl"][f"cand_{n}"] != want[f"lrl_cand_{n}"][t]:
                    add("lrl", DIFF, f"{fmt(b['time'])} (i={b['i']}) {n}-side candidates: Pine {b['lrl'][f'cand_{n}']} · "
                                     f"oracle {want[f'lrl_cand_{n}'][t]}")
                    diffs += 1
    if not diffs:
        add("lrl", MATCH, f"active LRL boundaries (now · previous bar): {bound_bars} bar-sides, {bound_vals} values")
        add("lrl", MATCH, f"candidate counts: {cand_bars} bar-sides from bar {ls.lookback}")
    for typ, n in sorted(matched.items()):
        add("lrl", MATCH, f"{typ}: {n}")
    for why, n in nobs_ev.most_common():
        add("lrl", NOBS, f"{n} Pine LRL events not compared: {why}")
    if nobs:
        add("lrl", NOBS, f"{len(nobs)} LRLs not compared (anchored in the TR warm-up or before the capture, "
                         f"a shared point, or dropped from memory)")
    ends = lambda evs: Counter(e["type"][4:] for e in evs if e["type"] in LRL_TERMINAL and (e["dir"], e["sid"]) not in nobs)
    return {"events": sum(matched.values()), "bar_sides": bound_bars, "boundaries": bound_vals, "cand_bars": cand_bars,
            "lookback": ls.lookback, "not_observable": len(nobs), "ends": {"pine": ends(pine), "oracle": ends(oracle)}}


def latest_capture() -> Path | None:
    """The most recently saved validation/parity/pine_capture*.csv / .txt, or pine-logs-*.csv
    (the name TradingView gives the file it saves; it may also append .csv to yours)."""
    files = [p for pat in ("pine_capture*", "pine-logs*") for p in PARITY_DIR.glob(pat)
             if p.suffix.lower() in (".csv", ".txt")]
    return max(files, key=lambda p: (p.stat().st_mtime, p.name)) if files else None


def run(path=None, preset: str | None = None) -> dict:
    path = Path(path) if path else latest_capture()
    if path is None or not path.exists():
        return {"status": "NO OBSERVED DATA", "differences": 0,
                "reason": f"{path.name if path else 'no validation/parity/pine_capture*.csv or .txt'} not present"}
    r = compare(parse(path.read_text(encoding="utf-8")), preset)
    r["file"] = path.name
    return r


def verdict(r: dict) -> str:
    c = r["counts"]
    lrl = r.get("lrl")
    tally = (f"{r['compared_bars']} bars × {r['series']} series and {r['matched_events']} events compared"
             + (f" + LRL: {lrl['events']} events, {lrl['boundaries']} boundaries, {lrl['cand_bars']} candidate counts"
                if lrl else "")
             + f"; {c[MATCH]} MATCH · {c[DIFF]} DIFFERENCE · {c[NOBS]} NOT OBSERVABLE")
    return f"BOUNDED PINE-LOG BAR-BY-BAR PARITY: {'FAIL' if r['differences'] else 'PASS'} — {tally}"


def show(r: dict, build: str) -> None:
    print("BOUNDED PINE-LOG BAR-BY-BAR PARITY — the bars and events IST logged, replayed by the oracle.")
    print("Only the captured window is covered; this is NOT full CSV bar-by-bar parity.\n")
    print(f"  {r['symbol']} · IST {build} · {r['about']}")
    print(f"  input: {r.get('file', '—')} · {r['source']}")
    print(f"  window {r['window']} · {r['bars']} bars · first {r['warmup']} = warm-up (never compared)")
    for n in r["notes"]:
        print(f"  NOTE: {n}")
    for sec in SECTIONS:
        rows = [c for c in r["checks"] if c["section"] == sec]
        if rows:
            print(f"\n  {sec.upper()}")
            for c in rows[:60]:
                print(f"    {c['status']:<15}{c['text']}")
            if len(rows) > 60:
                print(f"    … {len(rows) - 60} more")
    print(f"\n  {'after the warm-up':<20}{'Pine (log)':<42}oracle")
    for k in r["totals"]["pine"]:
        print(f"  {k:<20}{r['totals']['pine'][k]:<42}{r['totals']['oracle'][k]}")
    if r.get("lrl"):
        e = r["lrl"]["ends"]
        f = lambda c: " · ".join(f"{k} {c.get(k, 0)}" for k in ("DRIFT", "SWEEP", "BREAK", "EXPIRED"))
        print(f"  {'LRL ends (observable)':<20}{f(e['pine']):<42}{f(e['oracle'])}")
    print(f"\n  {verdict(r)}")
    print("  FULL CSV BAR-BY-BAR PARITY: not run here (it needs the Data Window export).")
