"""Failure artifacts: a reproducible case per failure, in validation/reports/failures/.

Hypothesis replays the minimal (shrunk) example last, and each save overwrites the
previous one for the same test, so the files left behind hold the minimized case.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from validation import VALIDATION_DIR

FAIL_DIR = VALIDATION_DIR / "reports" / "failures"


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_")[:90] or "failure"


def save_failure(test: str, *, invariant: str | None, message: str, candles=(), settings=None,
                 expected=None, actual=None, seed=None, extra: dict | None = None) -> Path:
    out = FAIL_DIR / _slug(test)
    out.mkdir(parents=True, exist_ok=True)
    rows = [[k.time, k.open, k.high, k.low, k.close] for k in candles]
    data = {"format": "ist-failure/1", "test": test, "invariant": invariant, "message": message, "seed": seed,
            "settings": settings.to_dict() if hasattr(settings, "to_dict") else settings,
            "candles": rows, "expected": expected, "actual": actual, "extra": extra or {}}
    (out / "failure.json").write_text(json.dumps(data, indent=1, default=str), encoding="utf-8")
    lines = [f"# Failure: {test}", "",
             f"* **Invariant / check:** `{invariant or '—'}`",
             f"* **Message:** {message}",
             f"* **Seed:** {seed if seed is not None else '—'}",
             f"* **Candles:** {len(rows)} (time ms, open, high, low, close in failure.json)", "",
             "Reproduce:", "", "```bash", f"python -m validation.reproduce {out.relative_to(VALIDATION_DIR.parent).as_posix()}/failure.json", "```", ""]
    if expected is not None or actual is not None:
        lines += ["## Expected", "", "```", json.dumps(expected, indent=1, default=str), "```", "",
                  "## Actual", "", "```", json.dumps(actual, indent=1, default=str), "```", ""]
    if rows and len(rows) <= 80:
        lines += ["## Candles", "", "| # | time | open | high | low | close |", "|---|---|---|---|---|---|"]
        lines += [f"| {i} | {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |" for i, r in enumerate(rows)]
    (out / "failure.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def list_failures() -> list[Path]:
    return sorted(p for p in FAIL_DIR.glob("*/failure.json")) if FAIL_DIR.exists() else []
