# IST · Displacement tests — v0.8.0-dev (EXPERIMENTAL)

**Status (2026-11-01).**
* Automated: see the table below and the CHANGELOG entry of v0.8.0-dev.
* TradingView DISP-L00 … L12: **PENDING**. They are recorded only from the user's results, never assumed.
* Freeze gates (not before): DISP-L10 real capture parity 0 DIFFERENCE, DISP-L11 human golden cases (M10), DISP-L12 reload.

**Build:** `src/IST.pine` v0.8.0-dev (branch `displacement/pine`). Definition: `docs/DISPLACEMENT.md` (DISPLACEMENT-R, approved 2026-11-01).

## Automated (before TradingView)

| id | what | where |
|---|---|---|
| S-DISP-1 | Pine's formulation (`DispPine`, transliterated from IST.pine) = the approved oracle (`DisplacementEngine`), every record field and event. Covered: the approval's case list on both sides (thresholds, close position, the previous extreme, doji, zero range, warm-up, A = 0, session transition, gap, FVG YES / NO); the research dataset (110 records); three walks (memory 50); generated candles | `tests/test_displacement_pine.py`, `fuzz/test_displacement_properties.py` |
| S-DISP-2 | the rule and order lines, 4 constants (= `DispSettings`), and the per-bar order (FVG metadata → detection → record; event → memory). Every history read at global scope, no number but 0 / 1 in the engine, one call site per engine method; Data Window / capture values never read by detection | ST-22 |
| S-DISP-3 | 25 mutations caught, among them: the v0.7.0-dev call-history read; A including the candle; the CISD TR series; FVG required; a debug / capture toggle gating detection; the capture writing state; alerts on | `tests/test_displacement_pine.py` |
| S-DISP-4 | no history read of a user series inside a function or method | ST-21 |
| S-DISP-5 | Pine event names = oracle names (`ORACLE_ONLY` now empty) | ST-14 |
| S-DISP-6 | one input (`dispOn`, [calc], ON); no renderer; no alert; 5 Data-Window-only debug plots; the 52-row debug table unchanged; capture keys | `tests/test_displacement_pine.py`, ST-01, ST-04 |
| S-DISP-7 | bounded parity on faithful synthetic captures (NQ, walks with memory drops, other constants): 0 DIFFERENCE; 15 corruption kinds detected | `tests/test_parity_disp.py` |
| S-DISP-8 | oracle: thresholds, edge cases, facts, memory, real data, independence, determinism | `tests/test_displacement.py` |
| S-DISP-9 | invariants INV-DISP-01 … 06, each with a negative test | `invariants.py`, `tests/test_invariants.py` |
| S-DISP-10 | the research harness (symmetry, no lookahead, fences, quoted numbers) | `tests/test_displacement_study.py` |

## TradingView procedure (NQ1! or MNQ1! 1m; Confirmed only ON)

Before you start:
1. In the Pine Editor, replace the code with `src/IST.pine` v0.8.0-dev.
2. Save it, and add it to a 1m chart, or update the chart's copy.

There is **no displacement drawing** in this build (M11). Developer → **Debug mode** ON adds five Data Window values, `dbg · DISP …`, and the events in Pine Logs.

| id | test | how | expected |
|---|---|---|---|
| DISP-L00 | compile and runtime | the procedure below | no compile error, no runtime error, the chart loads, everything else as in v0.7.1-dev |
| DISP-L01 | settings | open the settings | a group DISPLACEMENT with one checkbox, "Enable displacement engine", ON. No other displacement input |
| DISP-L02 | the definition on a candle | Debug ON; put the cursor on a candle whose `dbg · DISP verdict` is 1, then on one with −1 | body / A ≥ 1.5, close position ≥ 0.75, and the close above the previous candle's high (below the previous low for −1). A near-miss candle shows 0 |
| DISP-L03 | FVG metadata | the candle right after a displacement | `dbg · DISP FVG metadata …` = 1 when that candle's low is above the high of the candle before the displacement (bearish: its high below that candle's low), else −1 |
| DISP-L04 | engine OFF / other modules | Enable displacement engine OFF, then ON | no DISPLACEMENT events and DISP values na while OFF; every drawing, Debug row and alert of the other modules identical either way |
| DISP-L05 | no drawing, no alert | look at the chart; an "Any alert() function call" alert | nothing displacement-related drawn; no displacement alert message |
| DISP-L10 | **real parity (freeze gate)** | Developer → Parity capture ON (N = 1000); save the Pine Logs into `validation/parity/`; run `python -m validation.parity --capture <file>` | **0 DIFFERENCE**, the displacement section included (per-bar verdict, A, body / A, close position, FVG metadata; events; snapshot records) |
| DISP-L11 | **human golden cases (freeze gate, M10)** | the user's labelled displacement examples against DISPLACEMENT-R | every deterministic golden reproduced, or each difference explained |
| DISP-L12 | **reload (freeze gate)** | note 3 displacements (id = time, side, close, body / A); refresh the page; remove and re-add the indicator | the same displacements, unchanged (any bar ≥ 14 from the history start) |

### DISP-L00 manual: compile + runtime (what you do)

1. **Code.** Pine Editor → open IST → select all → paste `src/IST.pine` (v0.8.0-dev; line 3 of the header says `v0.8.0-dev`) → **Save**.
2. **Compile.** The editor console shows no error, and the indicator is added (or updated) on a **1m NQ1! or MNQ1!** chart.
3. **Runtime.** On the chart, the IST status line has no red error mark. Open **Pine Logs**: there is no runtime error. The chart looks as with v0.7.1-dev (FVG, levels, liquidity, LRL, HTF FVG, CISD), with nothing new drawn.
4. **Settings.** There is a new group **DISPLACEMENT** with **Enable displacement engine = ON**, and nothing else in it.
5. **Debug.** Developer → **Debug mode ON**.
   * The table still ends with the CISD rows (45–51).
   * Open the **Data Window**, move the cursor over candles, and find five rows `dbg · DISP …`: verdict, A, body / A, close position, FVG metadata.
   * Find one candle with verdict **1** and one with **−1** (large candles that close near their extreme and beyond the previous candle).
6. **Events.** In Pine Logs (Debug ON), lines `DISPLACEMENT_CONFIRMED BULL id=… px=… · close=… · bk=… · rk=… · cp=… · prev=…` appear, for the same candles.
7. **OFF / ON.** Enable displacement engine **OFF**: the DISP values show na and no DISPLACEMENT lines appear. Turn it back **ON**.
8. **Record.** PASS, or FAIL with the error text or a screenshot.

After DISP-L00, the next step is DISP-L10, the real Pine Logs capture with Parity capture ON. The capture tool already reads the displacement lines.

## Results (user)

| id | result | date | notes |
|---|---|---|---|
| DISP-L00 … L12 | PENDING | | |
