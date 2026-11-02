# IST · IFVG tests — v0.9.1-dev (EXPERIMENTAL)

**Status (2026-11-02).**
* The automated part passes (validation 1.20.0).
* **IFVG-L00 … L12: NOT RUN.** v0.9.0-dev was never compiled; it is superseded by v0.9.1-dev (revised memory). TradingView results are recorded only from the user's results, never assumed.
* Not frozen.

**Build:** `src/IST.pine` v0.9.1-dev (branch `ifvg/pine`). Definition: `docs/IFVG.md` (IFVG-R, approved 2026-11-02 with two clarifications and the revised memory rule DEF-IFVG8).

## Automated (before TradingView)

| id | what | where |
|---|---|---|
| S-IFVG-1 | Pine's formulation (`IfvgPine`, transliterated from IST.pine) = the approved oracle (`IfvgEngine`): every record field, every event, the counters, and the shadows = the oracle's registry. Covered: the approval's cases 1–22 on both sides (wick / close at / close beyond the edge, immediate, after touch / CE / full, gap through, invalidated and released on the same bar, released earlier, the lifecycle, the far edge, every fact and the end on one bar, no second inversion); the real data (652 FVGs, 566 inversions: 272 from bullish, 294 from bearish, median 9 bars to inversion); memory 50 per side on real data; generated candles | `tests/test_ifvg_pine.py`, `fuzz/test_ifvg_properties.py` |
| S-IFVG-2 | 21 rule lines, the constant (= `IfvgSettings`), and 4 orders: Phase 1 → advance → memory → observe; facts → close, both sides; event → memory. The inversion is Phase 1's `invBar` (no second close rule). The observer never writes a Phase 1 record or list. No history read and no number but 0 … 3 in the engine. One call site per engine method (three for the memory routine). No Data Window or capture value read by detection | ST-23 |
| S-IFVG-3 | 34 mutations caught, among them: a second close rule; a wick inverts; one bar late; the same side; geometry from the extreme; the inversion bar as a retest; end on a close at the edge or on a wick; the close before the facts; only shown FVGs join; the observer writing or removing Phase 1 records; the newest dropped; an ACTIVE record evicted (the v0.9.0-dev fallback); no memory after the ends or after an inversion; memory before the advance; a debug, capture or CISD toggle gating detection; a history read; alerts on | `tests/test_ifvg_pine.py` |
| S-IFVG-4 | no history read of a user series inside a function or method (regression of the v0.7.0-dev defect) | ST-21 |
| S-IFVG-5 | Pine event names = oracle names (`ORACLE_ONLY` now empty) | ST-14 |
| S-IFVG-6 | one input (`ifvgOn`, [calc], ON); no renderer; no alert; 4 Data-Window-only debug plots; the 52-row debug table unchanged; the capture keys; the engine reads no view input and no CISD, displacement, liquidity, LRL or HTF FVG state | `tests/test_ifvg_pine.py`, ST-01, ST-04 |
| S-IFVG-7 | Phase 1 and every frozen line unchanged: against `DISPLACEMENT_BASELINE_v0.8.0-dev` the diff only adds lines, except the four build lines (header, `IST_BUILD`, CAPTURE, BAR) | `tests/test_ifvg_pine.py` |
| S-IFVG-8 | bounded parity on faithful synthetic captures (NQ, walks, memory 2): 0 DIFFERENCE; 17 corruption kinds detected; a build without IFVG is not compared | `tests/test_parity_ifvg.py` |
| S-IFVG-9 | oracle: trigger, eligibility, lifecycle, memory, real data, identity, visibility and module independence, determinism | `tests/test_ifvg.py` |
| S-IFVG-10 | invariants INV-IFVG-01 … 09, each with a negative test (07: ≤ 50 per side unless all ACTIVE, oldest INVALIDATED first; 08: the registry = the open Phase 1 FVGs; 09: memory never removes an ACTIVE IFVG) | `invariants.py`, `tests/test_invariants.py` |
| S-IFVG-11 | the research harness | `tests/test_ifvg_study.py` |
| S-IFVG-12 | DEF-IFVG8 (revised): 50 ACTIVE + 1 → 51 kept; 55 ACTIVE kept; an old INVALIDATED record leaves, 51 ACTIVE remain; an over-full ACTIVE side compacts when one ends (retest → end → drop on that bar); an older INVALIDATED record goes before a newly invalidated one; never a drop of an ACTIVE record; lifecycles identical with or without overflow; both sides; replay; random walks lose no ACTIVE IFVG (equal to an unlimited memory); generated candles | `tests/test_ifvg_memory.py`, `fuzz/test_ifvg_properties.py` |

## TradingView procedure (NQ1! or MNQ1! 1m; Confirmed only ON)

Before you start:
1. In the Pine Editor, replace the code with `src/IST.pine` v0.9.1-dev.
2. Save it, and add it to a 1m chart, or update the chart's copy.

There is **no IFVG drawing** in this build. Developer → **Debug mode** ON adds four Data Window values, `dbg · IFVG …`, and the events in Pine Logs.

| id | test | how | expected |
|---|---|---|---|
| IFVG-L00 | compile and runtime | the procedure below | no compile error, no runtime error, the chart loads, everything else as in v0.8.0-dev |
| IFVG-L01 | settings | open the settings | a group IFVG with one checkbox, "Enable IFVG engine", ON. No other IFVG input |
| IFVG-L02 | the inversion on a candle | Debug ON, Show FVGs ON; find an FVG that a candle closes beyond (bullish FVG: close below its bottom) | on that candle: `FVG_INVALIDATED` then `IFVG_INVERTED BEAR` with the same id and `bottom / top / ce` of the FVG. A candle whose wick goes beyond and closes inside or exactly at the edge gives neither |
| IFVG-L03 | lifecycle | follow that IFVG on the next candles | `IFVG_FIRST_TOUCH` when a high reaches its bottom (never on the inversion candle); `IFVG_INVALIDATED` on the first close above its top (a close exactly at the top, or a wick above it, is not an end) |
| IFVG-L04 | engine OFF / other modules / visibility | Enable IFVG engine OFF, then ON; then Show FVGs OFF | while OFF: no IFVG events, IFVG values na. Every drawing, Debug row and alert of the other modules identical either way. Show FVGs OFF changes no IFVG value |
| IFVG-L05 | no drawing, no alert | look at the chart; an "Any alert() function call" alert | nothing IFVG-related drawn; no IFVG alert message |
| IFVG-L10 | **real parity (freeze gate)** | Developer → Parity capture ON (N = 1000); save the Pine Logs into `validation/parity/`; run `python -m validation.parity --capture <file>` | **0 DIFFERENCE**, the IFVG section included (shadows, active per side, facts per bar; events; snapshot records) |
| IFVG-L11 | **human golden cases (freeze gate)** | to be defined after L10 (real candles, as DISP-L11) | every deterministic golden reproduced, or each difference explained |
| IFVG-L12 | **reload (freeze gate)** | note 3 IFVGs (id, side, inversion time, close); refresh the page; remove and re-add the indicator | the same IFVGs, unchanged (any FVG whose confirmation is ≥ 16 bars after the history start) |

### IFVG-L00 manual: compile + runtime (what you do)

1. **Code.** Pine Editor → open IST → select all → paste `src/IST.pine` (v0.9.1-dev: line 3 of the header says `v0.9.1-dev`) → **Save**.
2. **Compile.** The editor console shows no error, and the indicator is added (or updated) on a **1m NQ1! or MNQ1!** chart.
3. **Runtime.** On the chart, the IST status line has no red error mark. Open **Pine Logs**: there is no runtime error. The chart looks as with v0.8.0-dev (FVG, levels, liquidity, LRL, HTF FVG, CISD), with nothing new drawn.
4. **Settings.** There is a new group **IFVG · INVERSION FAIR VALUE GAPS** with **Enable IFVG engine = ON**, and nothing else in it.
5. **Debug.** Developer → **Debug mode ON**.
   * The table still ends with the CISD rows (45–51).
   * Open the **Data Window**, move the cursor over candles, and find four rows: `dbg · IFVG eligible Phase 1 FVGs (shadows)`, `dbg · IFVG active bullish`, `dbg · IFVG active bearish`, `dbg · IFVG inversions so far (loaded history)`.
   * "inversions so far" grows from left to right.
   * The other three are small whole numbers.
6. **Events.** In Pine Logs (Debug ON), find a line `IFVG_INVERTED BEAR id=… px=… · bottom=… · top=… · ce=… · pre=…` (or BULL).
   * The same candle also has a line `FVG_INVALIDATED BULL` (or BEAR) with the same id.
   * Later lines `IFVG_FIRST_TOUCH` and `IFVG_INVALIDATED` with that id appear.
7. **OFF / ON.** Enable IFVG engine **OFF**: the IFVG values show na, no IFVG lines appear, and nothing else changes. Turn it back **ON**.
8. **Record.** PASS, or FAIL with the error text or a screenshot.
