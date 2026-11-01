# IST · Displacement tests — v0.8.0-dev (EXPERIMENTAL)

**Status (2026-11-01).**
* **DISP-L10 PASS** (user, real IST v0.8.0-dev capture, 0 DIFFERENCE).
* **DISP-L11 PASS** (human / golden validation: 19 cases, 22 candles, 0 mismatch, no systematic conflict). The reviewer's classifications await the user's look on the chart (procedure below).
* DISP-L12 (reload, freeze gate) and DISP-L01 … L05 are **PENDING**. TradingView results are recorded only from the user's results, never assumed.
* Freeze gates: DISP-L10 PASS · DISP-L11 PASS · DISP-L12 pending.

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
| S-DISP-11 | DISP-L11 human goldens (19 cases, 22 candles). Checked: candles = evidence bars; the recorded numbers follow from them; the oracle and `DispPine` give the approved verdict on the window and on the full history; the real Pine log agrees where a case lies in the v0.8.0-dev capture (A3, A6, B5, C1); the bearish mirror; the CISD relation; required coverage | `golden/human/displacement/`, `tests/test_displacement_golden.py` |
| S-DISP-12 | the real v0.8.0-dev capture (DISP-L10): 0 DIFFERENCE, with its counts pinned (displacement 1,060 bar verdicts, 22 + 22 events, 50 snapshot records) | `parity/evidence/`, `tests/test_parity_v080_evidence.py` |

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
| DISP-L11 | **human golden cases (freeze gate, M10)** | the golden cases of `validation/golden/human/displacement/` (real candles), then the user's visual check (below) | every deterministic golden reproduced, or each difference explained |
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

### DISP-L11 visual check of the golden cases (recommended, what you do)

`validation/golden/human/displacement/README.md` lists 19 cases with exact times:
* NQ1! 2026-10-27 / 28;
* MNQ (CME_MINI:MNQZ2026) 2026-10-13 / 14 and 10-29 / 30. Use Bar Replay if the history is no longer loaded.

For each case, look at the candle and say whether you agree with its category: A clear displacement · B clear non-displacement · C borderline · S/I inconclusive. A disagreement is recorded as a conflict with DISPLACEMENT-R; the rule is not changed to absorb it.

### DISP-L12 manual: TradingView reload (what you do)

1. **Chart.** Use a 1m NQ1! or MNQ1! chart with IST v0.8.0-dev, default settings, Confirmed only ON. Turn **Debug mode** on (Developer).
2. **Choose an area.** Pick a historical area at least 50 bars after the chart's first loaded bar (Debug row 34 shows the first loaded bar). A displacement only needs the 14 bars before it.
3. **Note at least 3 displacements**, one of each side if you can.
   * In the Data Window (cursor on the candle), a candle with `dbg · DISP verdict` = 1 or −1. Write down:
     * its time (the id);
     * the side;
     * A;
     * body / A;
     * close position.
   * On the next candle, write down `dbg · DISP FVG metadata` (1 or −1).
   * The Pine Logs line `DISPLACEMENT_CONFIRMED … px=…` gives the close.
   * Note one near-miss candle too (verdict 0).
4. **Reload, two ways.** (a) Refresh the browser page. (b) Remove IST from the chart and add it again.
5. **Compare** the same candles, by time.
   * **Expected:** the same side, A, body / A, close position, close and FVG metadata; the near-miss stays 0.

## Results (user)

| id | result | date | notes |
|---|---|---|---|
| DISP-L00 | not recorded separately | 2026-11-01 | the DISP-L10 capture was written by v0.8.0-dev in TradingView, so it compiled and ran |
| DISP-L01 … L05 | PENDING | | |
| DISP-L10 | **PASS** | 2026-11-01 | real capture of IST v0.8.0-dev (MNQ 1m Bar Replay, 2026-10-29 19:56 → 10-30 13:51; `pine-logs-IST_43f18.csv`, kept as `parity/evidence/ist-v0.8.0-dev_mnq-1m-replay_capture-1000_2026-10-30.csv`): 0 DIFFERENCE in every module. Displacement: 1,060 bar verdicts, 50 snapshot records consistent, 22 + 22 events |
| DISP-L11 | **PASS** | 2026-11-01 | 19 cases / 22 candles from the evidence captures: 6 clear displacements (3 ▲, 3 ▼), 5 clear non-displacements, 6 borderline, 2 supporting / inconclusive (I1, I2: approved exclusions M2 / M5). 0 mismatch; the mirror holds; 4 cases agree with the real Pine log. Visual confirmation by the user recommended (above) |
| DISP-L12 | PENDING | | the reload procedure above (freeze gate) |
