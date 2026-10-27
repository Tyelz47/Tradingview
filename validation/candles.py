"""Candle builders: scenario rows, deterministic random walks, TradingView CSV
exports, and the metamorphic transforms (mirror, shift) used by property tests."""
from __future__ import annotations

import csv
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from validation.models.types import NQ_TICK, Candle

MINUTE = 60_000
# Sunday 2026-10-25 18:00 America/New_York: the start of a futures week (under the
# §7.2 assumption), so walks cross real session windows and day/week boundaries.
BASE_TIME = int(datetime(2026, 10, 25, 18, 0, tzinfo=ZoneInfo("America/New_York")).timestamp() * 1000)

# 20 flat bars (no pivots, TR average 2.0) used before liquidity scenarios, as in the
# original tests/liq_model.py.
WARM = [(100, 101, 99, 100)] * 20


def from_rows(rows, start: int = BASE_TIME, step: int = MINUTE) -> list[Candle]:
    """[(o, h, l, c), …] → candles one `step` apart."""
    return [Candle(start + i * step, float(o), float(h), float(l), float(c)) for i, (o, h, l, c) in enumerate(rows)]


def random_walk(n: int, seed: int, tick: float = NQ_TICK, start_price: float = 20000.0, max_step: int = 12,
                gap_prob: float = 0.0, start: int = BASE_TIME, step: int = MINUTE) -> list[Candle]:
    """Each bar walks 4 moves of ±0…max_step ticks from the previous close (the
    original fuzz walk). `gap_prob` opens some bars away from the previous close."""
    rnd = random.Random(seed)
    out, c = [], start_price
    for i in range(n):
        o = c
        if gap_prob and rnd.random() < gap_prob:
            o = c + rnd.choice([-1, 1]) * rnd.randint(1, 3 * max_step) * tick
        path = [o]
        for _ in range(4):
            path.append(path[-1] + rnd.choice([-1, 1]) * rnd.randint(0, max_step) * tick)
        c = path[-1]
        out.append(Candle(start + i * step, o, max(path), min(path), c))
    return out


def from_ticks(specs, tick: float = NQ_TICK, start_price: float = 20000.0, start: int = BASE_TIME,
               step: int = MINUTE) -> list[Candle]:
    """[(gap, body, upper_wick, lower_wick), …] in ticks → valid candles (property tests).
    open = previous close + gap · close = open + body · high/low add the wicks."""
    out, c = [], round(start_price / tick)
    for i, (gap, body, up, down) in enumerate(specs):
        o = c + gap
        c = o + body
        h, l = max(o, c) + up, min(o, c) - down
        out.append(Candle(start + i * step, o * tick, h * tick, l * tick, c * tick))
    return out


def mirror(candles: list[Candle], pivot: float) -> list[Candle]:
    """Price reflection p → 2·pivot − p: highs become lows, bull becomes bear."""
    return [Candle(k.time, 2 * pivot - k.open, 2 * pivot - k.low, 2 * pivot - k.high, 2 * pivot - k.close)
            for k in candles]


def shift(candles: list[Candle], points: float) -> list[Candle]:
    return [Candle(k.time, k.open + points, k.high + points, k.low + points, k.close + points) for k in candles]


def load_tradingview_export(path, tz: str = "America/New_York") -> tuple[list[Candle], list[dict]]:
    """A TradingView 'Export chart data' CSV: columns time, open, high, low, close, then one
    column per indicator plot (title = header). Returns the candles and every row as
    {lower-cased header: raw text}. `time` may be unix seconds or an ISO date-time (naive
    values are read in `tz`)."""
    candles, rows = [], []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
            t = row["time"]
            if t.replace(".", "", 1).isdigit():
                ms = int(float(t) * 1000)
            else:
                dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=ZoneInfo(tz))
                ms = int(dt.timestamp() * 1000)
            candles.append(Candle(ms, float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"])))
            rows.append(row)
    return candles, rows


def load_tradingview_csv(path, tz: str = "America/New_York") -> list[Candle]:
    return load_tradingview_export(path, tz)[0]
