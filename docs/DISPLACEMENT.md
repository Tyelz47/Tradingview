# IST · Displacement (DEF-DISP1 … DISP9)

**Status: APPROVED by the user on 2026-11-01 (DISPLACEMENT-R, M1…M11). Implemented in Pine: IST v0.8.0-dev (EXPERIMENTAL, not frozen).**
* The research behind it is `docs/STUDY_DISPLACEMENT.md`.
* Reference model: `validation/models/displacement.py`, the opt-in module `disp` of the oracle (validation 1.16.0, unchanged by the Pine phase).
* Pine: §5. Parity capture: §6. TradingView tests: `docs/TESTS_DISPLACEMENT.md`.
* **DISP-L10 PASS:** the real v0.8.0-dev capture, 0 DIFFERENCE.
* **DISP-L11 PASS:** human golden cases, `validation/golden/human/displacement/`.
* DISP-L12 (reload) is the remaining freeze gate.
* **Approved decisions.**
  * M1: k = 1.5.
  * M2: close position 0.75.
  * M3: keep the close beyond the previous candle.
  * M4: constants, not inputs.
  * M5: no multi-bar displacement.
  * M6: events `DISPLACEMENT_CONFIRMED` and `DISPLACEMENT_DROPPED_MEMORY`.
  * M7: FVG as metadata only.
  * M8: no absolute floor.
  * M9: its own TR series.
  * M10: human golden cases are required before a freeze, not before the first Pine.
  * M11: renderer and alerts deferred.
* **An independent module.** Untouched: CISD-R (frozen, `CISD_BASELINE_v0.7.1-dev`), LRL, HTF FVG, Phase 1 and Phase 2.

## 1 · Definitions

Written for the **bullish** displacement. The bearish one is the exact mirror: open and close negated, high ↔ −low. EPS = 0.01 × tick, the float margin of IST.

| id | rule |
|---|---|
| DEF-DISP1 direction | bullish: `close > open + EPS`; bearish: `close < open − EPS`. A doji (`|close − open| ≤ EPS`) is neither |
| DEF-DISP2 reference A | `A = SMA(TR, 14)` over the 14 **completed** bars immediately before the candle (Pine: `ta.sma(ta.tr(true), 14)[1]`; the first bar's TR is high − low). No decision while A is undefined (t < 14) or A ≤ 0 |
| DEF-DISP3 body | `body = close − open` (bearish: `open − close`); `body ≥ 1.5 × A`; no EPS on this term |
| DEF-DISP4 strong close | `range = high − low > 0`; close position `(close − low) / range ≥ 0.75` (bearish: `(high − close) / range ≥ 0.75`). Evaluated as `close − low ≥ 0.75 × range`, the same inequality for range > 0, with no division |
| DEF-DISP5 beyond the previous candle | `close > high[1] + EPS` (bearish: `close < low[1] − EPS`). A **displacement criterion**: it separates directional repricing from a large candle still contained within the previous candle. It is not the FVG definition (an FVG is a three-candle condition, DEF-A1) |
| DEF-DISP6 confirmation | A displacement is a candle where DEF-DISP1…5 all hold. It is confirmed **at the candle's close**, from bars ≤ t, and never changes. There is no later confirmation candle and no state machine. A candle has at most one record; consecutive candles are separate displacements |
| DEF-DISP7 record | id = the candle's open time; side, bar, OHLC, A, body, range, body / A, range / A, close position, the previous extreme. FVG metadata: UNKNOWN at confirmation. On the next closed candle it is set once, permanently, to YES or NO: is the displacement candle **candle 2** of a Phase 1 DEF-A1 FVG in its direction? (bullish: `low[t+1] > high[t−1]`, strict; the frozen Phase 1 geometry, not its size qualification). Metadata only: no decision reads it, and it never changes whether the displacement exists |
| DEF-DISP8 memory | 50 records (both sides); the oldest leaves first |
| DEF-DISP9 independence | reads candles only. No CISD record, FVG engine state, liquidity, sweep, LRL, MSS / BOS, DOL, HTF FVG or session state, and no context. No session reset: a gap enters TR and raises A, but the body excludes it. Detection never reads a display, debug, capture or alert input |

## 2 · Events

| event | when | dir · id · price · origin | audit text |
|---|---|---|---|
| `DISPLACEMENT_CONFIRMED` | the candle's close | side · candle open time · close · the bar | `close=… · bk=… · rk=… · cp=… · prev=…` (body / A, range / A, close position, previous extreme) |
| `DISPLACEMENT_DROPPED_MEMORY` | the oldest record leaves memory | side · id · close · its bar | `oldest record` |

Displacement has no lifecycle: no SWEEP / BREAK / INVALIDATED, no ACTIVE / ENDED. Once confirmed, a displacement is a historical fact.

## 3 · Non-repaint guarantees

* Decided at the bar close (Confirmed mode; both modes run the engine on closed bars only) from that bar and the 14 before it. No later bar can change it.
* The FVG metadata is set once, one bar later, and is metadata only.
* **Stateless.** A displacement depends only on its own candle, the previous candle and A. Any chart history that contains those 15 bars gives the same result, so a reload cannot change a displacement after the first 14 loaded bars.

## 4 · Validation (oracle, validation 1.16.0; Pine, validation 1.17.0)

* `tests/test_displacement.py`: deterministic tests of the oracle.
* `fuzz/test_displacement_properties.py`: invariants, mirror, translation, no lookahead, other modules unchanged both ways, Pine formulation = oracle, long walks.
* `tests/test_displacement_study.py`: the research harness.
* `tests/test_displacement_pine.py`:
  * Pine's formulation `DispPine` = the oracle on the approval's case list (both sides) and on the real data (110 records, field for field);
  * ST-22 pins every Pine line, and each of 25 mutations is caught;
  * ST-21 catches a history read inside the engine.
* `tests/test_parity_disp.py`: the capture format and the comparison, and each of 15 corruption kinds is detected.
* Invariants INV-DISP-01…06, each with a negative test (`tests/test_invariants.py`).

## 5 · Pine implementation (IST v0.8.0-dev)

**Constants (M4).**
* `DISP_K = 1.5`, `DISP_CLOSE = 0.75`, `DISP_TRA_LEN = 14`, `DISP_MEM = 50`.
* Events `EV_DISP_CONFIRMED = 34`, `EV_DISP_DROPPED = 35`.
* One input: `dispOn` ([calc] "Enable displacement engine", default ON, group DISPLACEMENT). There are no other displacement inputs.

**L1, every bar, global scope (ST-21).**
* `dispTra = ta.sma(ta.tr(true), DISP_TRA_LEN)` is its own series (M9; it never reads `cisdTraPrv`).
* `dispTraPrv = dispTra[1]` (A), `dispPrvHi = high[1]`, `dispPrvLo = low[1]`.
* The FVG metadata reads Phase 1's L2 `rawBull` / `rawBear` (DEF-A1, `low > high[2]` / `high < low[2]`). These are global and computed every bar whatever the FVG inputs are. On the bar after a displacement, candle 1 of that geometry is the bar before the displacement and candle 3 is this bar.
* The engine receives these as plain values. No history is read inside any displacement function or method.

**L3 (`// ── Displacement`).**
* `f_dispHit(s, a, pe)`: DEF-DISP1…5 in side coordinates.
* `factsDisp(gapUp, gapDn)`: DEF-DISP7, for the previous bar's record only, once.
* `confirmDisp(s, a, pe)`: the record, the event, memory.
* `DispBook` holds the records and counters.

**ENGINE RUN.** `if dispOn and barstate.isconfirmed`, after HTF FVG and before CISD:
1. `factsDisp(rawBull, rawBear)` first;
2. then, if A > 0: `dispSide := f_dispHit(+1) ? 1 : f_dispHit(−1) ? −1 : 0`;
3. `confirmDisp` when a side is confirmed.

**Renderer and alerts (M11).**
* No drawing: no line, label or box. Option A of the approval.
* `f_alertOn`: `EV_DISP_CONFIRMED => false`.

**Debug (developer only).**
* Data Window values with Debug mode ON (`dbg · DISP …`):
  * the verdict on the candle;
  * A;
  * body / A and close position in the candle's direction;
  * the FVG metadata resolved on that bar.
* Events appear in the "Last events" row and in Pine Logs, with the audit text.
* The 52-row debug table is unchanged.

## 6 · Parity capture (Pine Logs)

**`CAPTURE` line.** It also carries `disp=1|dispk=1.5|dispclose=0.75|disptr=14|dispmem=50`.

**Snapshot.** After captured bar `DISP_TRA_LEN + 1` (not the first), Pine logs:
* `DISPSTATE|at=<bar_index>|confirmed=…|dropped=…`;
* one `DISPREC|side|id|bar|O|H|L|C|tra|body|rng|bk|rk|cp|prev|fvg` per record (fvg 0 UNKNOWN · 1 YES · −1 NO).

From that bar on, the oracle's A, rebuilt from the captured bars alone (a bar's TR needs the close before it), equals Pine's.

**`BAR` lines.** Each also carries:
* `DS`: the verdict, 1 / −1 / 0;
* `DA`: A;
* `DK` and `DP`: body / A and the close position, in the candle's own direction (na for a doji);
* `DF`: the FVG metadata resolved on that bar (1 / −1 / na).

Existing capture fields and their meaning are unchanged.

**The comparison** is `validation/parity/capture.py _compare_disp`:
* Each snapshot record is checked: its own numbers, the rule, and its candle where it was captured.
* The approved oracle runs on the captured bars, takes the snapshot records, and replays the rest.
* Per bar: the verdict and the FVG metadata exactly; A, body / A and close position within 1e-6 (Pine prints 8 decimals).
* Every event: side, id, time and close, plus body / A, range / A, close position and previous extreme.
* NOT OBSERVABLE: the bars up to the snapshot and their events.

## 7 · Not started (by instruction)

* The renderer and alerts (M11), and the final visual design.
* Multi-bar displacement (M5).
* Context / quality classes: CISD, sweep, FVG, DOL, structure.
* IFVG.
* A freeze: DISP-L10 and DISP-L11 pass; it still needs the DISP-L12 reload check and the user's go.
