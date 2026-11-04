# IST · CONTEXT-03 · Research dataset contract

**Status: RESEARCH (2026-11-03).** This contract is the design of the dataset, written before any policy is chosen.
* Code: `validation/studies/context_dataset.py`.
* Tests: `validation/tests/test_context_dataset.py`.
* Every dataset used for DOL evaluation must satisfy it. Data that fails it yields `DATA_INVALID` / `CENSORED`; it is never silently repaired.

## 1 · Metadata (`DatasetMeta`)

| field | content |
|---|---|
| `id` | a stable dataset id |
| `underlying` | **NQ** or **ES**. Never pooled by default; MNQ / MES count as their underlying (a decision, §8) |
| `contracts` | `ContractSpan(symbol, start, end, continuous, back_adjustment)`: the **actual** contract (for example NQZ2026) or the continuous symbol (NQ1!) per span, contiguous. A new span is a roll boundary |
| `rolls` | declared roll times inside a continuous span (TradingView's NQ1! rolls inside the feed) |
| `timezone` | America/New_York (every session rule is local; timestamps are UTC ms) |
| `tick`, `timeframe_sec` | 0.25 · 60 for NQ 1m |
| `source` | for example "TradingView Pine-Log capture (IST v0.9.1-dev)", or a licensed vendor export the user names |
| `files` | `(path, SHA-256)` per source file: provenance |
| `holidays` | declared closed trading dates (exchange holidays are not modelled: an undeclared missing day is a gap) |

## 2 · The trading day and the schedule

* The trading day is **18:00 → 17:00 ET**: the CME equity-futures day, and the Module G / HTF boundary assumption. The TradingView D bars in the evidence all open at 18:00 ET, also after the 2026-11-01 DST change. G-V1…G-V5 must still confirm it (MANUAL_GATES.md).
* Closures:
  * the daily halt 17:00–18:00, Monday–Thursday;
  * the weekend, Friday 17:00 → Sunday 18:00;
  * declared holidays.
* A missing bar inside a closure is **never a gap**.
* The rules are applied in local time, so DST never moves a boundary. This is tested on 2026-11-01 and 2026-03-08.
* A day is **complete** when its first bar is at its scheduled start (Sunday 18:00 for a Monday), its last at 16:59, and it has no integrity issue. Otherwise it is truncated at the start and / or the end.

## 3 · Integrity checks (`integrity`)

| issue | meaning | effect |
|---|---|---|
| `DUPLICATE_TIMESTAMP` | two bars with one time | DATA_INVALID from there |
| `NON_MONOTONIC` | time goes back | DATA_INVALID from there |
| `OFF_TICK` | a price off the tick grid | DATA_INVALID from there |
| `OHLC_INCONSISTENT` | high < max(open, close), low > min(open, close) or high < low | DATA_INVALID from there |
| `UNSCHEDULED_GAP` | open minutes missing outside every closure | DATA_INVALID from there |
| `NO_CONTRACT` | no contract span covers the bar | DATA_INVALID from there |

* A decision needs no issue between the start of the data and t (DEF-EV5).
* An outcome decided before the first later issue keeps its label (DEF-EV2).

## 4 · Contract continuity and rolls

* Each bar belongs to exactly one span.
* A roll (a new span, or a declared roll inside a continuous symbol) is a **data boundary**. An evaluation window that reaches it without a decision is `CENSORED`; bars after it are never read.
* Back-adjusted continuous data is allowed only with its adjustment recorded. A level price from before a roll is not compared with prices after it.

## 5 · Granularity

* The data must show, per bar:
  * whether a level exists and when it is first observable (DEF-TU3 / D-TU4);
  * TARGET_REACHED, TARGET_TAKEN and the close class.
* On 1m, a same-bar reach of both targets stays `BOTH_SAME_BAR_UNRESOLVED`. Tick-level order is never invented.
* HTF bars (15m … 1W) from the same feed may restore the history before the first loaded bar (D-TU9). Each must be fully closed when used, with a known availability time, and must cover the missing interval.

## 6 · The repository's evidence under the contract

| dataset | underlying · contract | bars | trading days complete · partial | integrity issues |
|---|---|---|---|---|
| evidence-0 | NQ · NQ1! (continuous, back-adjustment default) | 1639 | **0** · 2 | none |
| evidence-1 | NQ · MNQZ2026 | 1188 | **0** · 1 | none |
| evidence-2 | NQ · MNQZ2026 (Bar Replay) | 1076 | **0** · 1 | none |
| evidence-3 | NQ · MNQ1! (continuous, back-adjustment default) | 1076 | **0** · 2 | none |

* Their only gaps are scheduled closures.
* **No complete trading day exists in the repository.** The CONTEXT-01 / 03 numbers rest on partial days and are descriptive only.
* No roll lies inside these windows: Z2026 was the front contract.
* The SHA-256 of every file is the one in `validation/parity/evidence/SHA256SUMS.txt`.

## 7 · Size and sampling (planning guidance, not a statistical guarantee)

| stage | per underlying | purpose |
|---|---|---|
| exploratory | **≥ 60 complete trading days** | inspect behaviour, design candidates (DEVELOPMENT) |
| before an empirical result justifies a semantic or policy decision | **≥ 250 complete trading days**, preferably more | DEVELOPMENT plus a locked OOS block |

* Sampling uses **contiguous** sessions, never hand-picked "good ICT days".
* Effective sample counts are reported after:
  * invalid data;
  * abstention;
  * same-bar outcomes;
  * censoring.
* Strata are labels computed after the fact and fixed before use (CONTEXT-01 RESEARCH_CASES §9). They are never features.

## 8 · Decisions for the user

| id | question |
|---|---|
| D-DS1 | Source of the dataset: Pine-Log captures (TradingView's own data; ~1.4 1m captures per day) or a licensed export, checked against an overlapping capture |
| D-DS2 | NQ versus MNQ (ES versus MES): count micro contracts as their underlying, or keep them apart |
| D-DS3 | The `dev_until` date of the first DEVELOPMENT / OOS split, fixed before collecting the OOS block |
| D-DS4 | Holidays: the list of closed dates to declare for the chosen period |
