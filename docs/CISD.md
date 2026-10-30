# IST · CISD, change in state of delivery (DEF-CISD1 … CISD9)

**Status:**
* **The definition was APPROVED by the user on 2026-10-30.** It is the recommendation CISD-R of `docs/STUDY_CISD.md` §H. The decisions D-C1…D-C12 were approved, with these clarifications:
  * an explicit UNKNOWN initial state (DEF-CISD4);
  * the 200-bar guard is a display / alert guard only, not part of the definition (DEF-CISD9).
* **Oracle only (validation 1.12.0).** `validation/models/cisd.py` is the opt-in module `cisd`.
  * **No Pine yet.** The Pine implementation starts only after the user approves these oracle results.
  * Default runs, the regression baseline and parity do not include it.
* Real golden cases come later. Once the Pine implementation runs in TradingView, the user marks real CISDs on the chart, and those become the first human-labelled golden cases. The oracle is validated without them: synthetic cases, real NQ statistical replay, random walks.
* The frozen baselines `PHASE1_BASELINE_v0.3.2` and `PHASE2_BASELINE_v0.4.4-dev` are untouched. Phase 1, Phase 2, LRL and HTF FVG are untouched.

**CISD detection ≠ CISD quality.**
* This document defines detection only: the structure, from bars alone.
* The study found no edge in CISD alone: on NQ, frequency, retest and follow-through are ≈ a random walk.
* Context lives in later, separate layers: liquidity taken, HTF FVG, session, displacement.

**Notation:**
* Everything is written for the **bullish CISD** (event `dir` **+1**).
* The **bearish CISD** (`dir` −1) is the same rule on the mirrored candle: open, close negated; high ↔ −low.
* ε = 0.01 tick: the project's float margin (Phase 1 / 2, `Settings.eps`).
  * Prices are on the tick grid, so "equal" means within ε and "strictly beyond" means by more than ε.
  * No decision uses raw floating-point equality.
* Bars are counted in bar index. Every decision is taken at a bar's close, from bars ≤ t only (Confirmed mode).

## 1 · Definitions

| id | rule (bullish; bearish = mirrored) |
|---|---|
| **DEF-CISD1** delivery candle, series | A **delivery candle** has close < open − ε (down-close). A **doji** (\|close − open\| ≤ ε) is not one. A **delivery series** is a maximal run of consecutive delivery candles: an up-close candle **or a doji ends it**. |
| **DEF-CISD2** leg window | The bars searched for the bullish side's delivery extreme. While the state is UNKNOWN: from bar 0 (the first loaded bar). Otherwise from the delivery extreme of the leg before it: the bar of the bearish CISD's extreme, its highest delivery high. |
| **DEF-CISD3** level L | The **lowest delivery low** in the leg window, counting delivery candles only (a non-delivery wick never selects). On an **equal low, the later delivery candle wins**. **L = the open of the first candle of the series holding that low** (the origin). L is known at the close of the bar that made that low. |
| **DEF-CISD4** state of delivery | One value: **UNKNOWN**, **BULL** or **BEAR**. The engine starts UNKNOWN; the first loaded bar establishes nothing. While UNKNOWN, both sides are armed; the first confirmed CISD (either side) establishes the state. Afterwards only the side against the state is armed, so CISDs **strictly alternate**. Proof that two CISDs never confirm on one bar is below. |
| **DEF-CISD5** confirmation | The first bar t > origin (and after the previous CISD) whose **close > L + ε**. The confirming candle may be **any colour** (up, down or doji). A wick through L does not confirm, nor does a close exactly at L; one tick beyond does. |
| **DEF-CISD6** record | Fields: `id` (origin candle time), `side`, delivery state `before` / `after`, `level` L, `origin`, `ext_bar`, `ext` (the delivery extreme), `leg_ext`, `known`, `bar`, `time`, `close`, `body_k`, `end` (status ACTIVE → ENDED), and the facts `retest`, `reclaim`, `broken`. Definitions of the less obvious fields:<br>• `leg_ext`: the lowest wick from the origin to the confirmation. It is the extreme the CISD protects.<br>• `body_k`: side × (close − open) / TR average of the 14 bars before the confirmation. It is metadata for a future displacement module; no decision reads it.<br>• facts (immutable, from the bar after the confirmation, while ACTIVE): `retest` = the first wick back to L; `reclaim` = the first close back at or through L; `broken` = the first close beyond `leg_ext`. Always retest ≤ reclaim ≤ broken. |
| **DEF-CISD7** lifecycle, memory | A confirmed CISD is **ACTIVE** until the opposite CISD, which **ENDS** it on its own bar. There are no further states and no RETEST / INVALIDATED events. At most one record is ACTIVE (the newest). Records kept: `memory` = 50. When full, the oldest (always ENDED) record goes, with `CISD_DROPPED_MEMORY`. |
| **DEF-CISD8** isolation | Detection reads bars only: no Phase 1 / 2 state, sessions, levels, LRL, HTF FVG, liquidity or context. With CISD on, every other module's events and state are byte-identical. |
| **DEF-CISD9** display / alert guard (**not part of the definition**) | The renderer and alerts ignore a CISD confirmed before bar index 200. It is a conservative chart-start / reload stabilisation guard and may be revised after real TradingView reload tests. During the first 200 bars the CISD calculation, records, events and state run normally; parity and debug can observe them. |

**After a CISD (the flip).** Say a bullish CISD confirms on bar t:
* the state becomes BULL;
* the previous (bearish) CISD ends on bar t;
* the bearish side is armed. Its leg window restarts at this CISD's delivery extreme (`ext_bar`) and is scanned up to t;
* the bullish side is disarmed. Its window restarts at the bearish side's new extreme, and then again at every new bearish-side extreme, so its next leg is always measured from the turn.

**Two CISDs never confirm on one bar (DEF-CISD4).**
* After the first CISD only one side is armed, so the claim concerns the UNKNOWN state only.
* While UNKNOWN, let the bullish extreme be on bar e_b and the bearish extreme on bar e_a. They differ, because the candle colours differ; say e_b > e_a.
* The bullish series cannot contain the up-close bar e_a, so its origin is after e_a. On that origin bar the bearish reference was already final.
* The bearish side did not confirm there, so close[origin] ≥ L_bear − ε.
* The origin is a down-close candle, so L_bull = open[origin] > close[origin] + ε ≥ L_bear.
* A bar confirming both would need L_bull + ε < close < L_bear − ε, which is impossible. The case e_a > e_b is the mirror.
* The engine asserts this on every bar, and no generated or real sequence has failed it.

## 2 · Events

| event | dir | id | price | origin | when |
|---|---|---|---|---|---|
| `CISD_CONFIRMED` | +1 / −1 | origin candle time | L | origin bar | the confirmation bar |
| `CISD_DROPPED_MEMORY` | +1 / −1 | the record's id | L | origin bar | the bar a new CISD pushes the oldest record out |

* The audit text is `prev=UNKNOWN|BULL|BEAR · close=… · ext=…`.
* Retest, close back through L and leg break are **record facts, not events**. They become events only if a later study proves they deserve it.
* Both types are `ORACLE_ONLY`: static check ST-14 excludes them until Pine gains the module. ST-14 stays exact for every other name.

## 3 · Non-repaint guarantees

* No lookahead. The level is known at the close of the extreme's bar; the confirmation is a closed bar's close; facts are stamped from the bar after.
  * A run on the first n bars emits exactly the full run's events before n (prefix property, NQ, walks, generated cases).
* Nothing is relabelled. A record's identity, level, extreme and confirmation never change; facts and the end are stamped once (INV-CISD-06).
* Mirror and translation: exact (NQ, walks, scenarios, generated cases).
* History start (reload). The state depends on history but forgets it quickly. Started at any later bar, the truncated run's CISDs equal the full history's from some CISD on. Measured, as the bars until the last differing CISD:

  | data | starts | differing CISDs (max · median) | bars (max · median) |
  |---|---|---|---|
  | NQ 1m | 206, every 7 bars | 8 · 1 | 87 · 5 |
  | NQ 3m | 162 | 4 · 1 | 17 · 4 |
  | NQ 5m | 90 | 10 · 1.5 | 105 · 6 |
  | three walks | 109 each | ≤ 9 | ≤ 60 |

  * **Correction to the study:** its "≤ 4 CISDs, ≤ 62 bars" covered starts in the first 600 bars only (86 starts).
  * All of these fall inside the 200-bar display guard (DEF-CISD9), but the guard is not a guarantee: convergence is a measured property of this data.

## 4 · Validation (oracle `validation/models/cisd.py`, validation 1.12.0)

**Identical to the approved study engine.** Record by record, on:
* NQ 1m, 3m, 5m and 15m: 121 · 55 · 23 · 14 CISDs;
* two walks;
* all 14 study scenarios.

Every study number therefore holds for the oracle.

| user test | where | what |
|---|---|---|
| T1 UNKNOWN initial state | `tests/test_cisd.py::test_t01…` | state UNKNOWN at start, after a huge first bar, and through wick-only, close-at-L and chop scenarios |
| T2 establishing the state | `test_t02…` | the first CISD (bull, its mirror, a bearish one) has prior state UNKNOWN; the state becomes its side |
| T3 strict alternation | `test_t03…` | NQ 1m / 5m and walks: sides alternate, `before` = previous side, each record ends on the next one's bar; trend scenario: one CISD |
| T4 doji ends a series | `test_t04…` | scenario 16: L = 98.25 (after the doji), not 100 ("doji skipped" variant) |
| T5 equal extreme → latest | `test_t05…` | equal lows 96 in two series: L = 97.25 (the later); "first" variant: no CISD |
| T6 non-delivery wick ignored | `test_t06…` | an up-close spike to 95.5 does not select: L = 100, delivery extreme 96, `leg_ext` 95.5; "any candle" variant: a different CISD |
| T7 any colour confirms | `test_t07…` | up-close, down-close (gap) and doji candles confirm on the same bar at the same L; "new direction" variant rejects two of them |
| T8 wick only → none | `test_t08…` | scenario 3 |
| T9 close at L → none | `test_t09…` | scenario 4 |
| T10 one tick → CISD | `test_t10…` | scenario 5 (close 100.25) |
| T11 mirror | `test_t11…`, `fuzz/test_cisd_properties.py` | NQ, walk, every scenario, generated cases |
| T12 prefix / no lookahead | `test_t12…`, property | events and records of every prefix |
| T13 reload convergence | `test_t13…` | NQ 1m / 3m / 5m and walks: converges, the last differing CISD inside the first 200 bars |
| T14 translation | `test_t14…`, property | NQ, walk, scenarios: ±1 tick to 30,000 points |
| T15 valid without displacement | `test_t15…` | scenario 15: CISD with body 0.33 × TR average |
| T16 displacement → same event | `test_t16…` | the same structure with a 4.3× or a 0.2× body: identical event; `body_k` differs; the TR length changes no event |
| T17 other modules byte-identical | `test_t17…`, property | Phase 1, sessions, levels, Phase 2, LRL, HTF FVG: events and state, NQ and walk |
| T18 guard changes no logic | `test_t18…`, property | guard 0 / 200 / 10⁶: identical events and state; renderer and alerts suppress CISDs before bar 200 |

**Invariants** (`validation/invariants.py`): INV-CISD-01…08, each with a negative test (`tests/test_invariants.py`):
* state;
* level and window;
* confirmation;
* timing;
* facts;
* frozen;
* events;
* memory / lifecycle.

They are checked on every bar of every checked run:
* NQ with the whole model (1m / 3m / 5m / 15m);
* memory 1 / 2 / 7;
* generated cases;
* long walks: 20,000 bars × 3 seeds in FULL.

## 5 · Pine notes (for the next phase; nothing is implemented)

* Per bar the cost is O(1); a flip adds one bounded scan of the leg window.
  * The longest scan measured is 85 bars on NQ 1m (`max_scan` counter) and ≤ 67 on walks.
  * Pine's `max_bars_back` must cover it: 500 is the proposal.
  * A longer window is possible in principle (a very long leg). The Pine phase must decide what happens beyond the buffer and test it.
* Event names `CISD_CONFIRMED` / `CISD_DROPPED_MEMORY` and the audit text above.
* Renderer (D-C8):
  * the ACTIVE CISD only by default: a short horizontal 1 px line from the origin to the confirmation, with a small `CISD` label;
  * the previous CISD optionally faded;
  * no boxes, no history clutter;
  * the guard as in DEF-CISD9.
* Alert: exists, **OFF** by default (D-C12).
* Chart timeframe only; no MTF CISD (D-C11).
* Freeze gate: a real TradingView Pine ↔ oracle parity with 0 DIFFERENCE, then the user's labelled golden cases.

## 6 · Not started (by instruction)

* Pine CISD.
* Displacement module.
* IFVG.
* DEF-LRL9 context.
* Scoring / confluence.
