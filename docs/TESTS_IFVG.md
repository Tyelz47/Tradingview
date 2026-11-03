# IST · IFVG tests — v0.9.1-dev (FROZEN)

**Status (2026-11-03).**
* **IFVG-L00: PASS** (user).
* **IFVG-L10: PASS** (the user's real capture, 2026-11-02, recorded from the user's result): 82 MATCH · 0 DIFFERENCE · 16 NOT OBSERVABLE; IFVG 1,059 bar states, 167 + 168 + 168 + 151 events, 100 snapshot records, the shadows = the open Phase 1 FVGs. Kept as evidence (`validation/parity/evidence/ist-v0.9.1-dev_mnq1-1m_capture-1000_2026-11-02.csv`, `tests/test_parity_v091_evidence.py`).
* **IFVG-L11: PASS**: 22 real golden cases, the mechanical case R1 and the memory golden MEM1 (`validation/golden/human/ifvg/`, `tests/test_ifvg_golden.py`), and the user's manual sanity review (2026-11-03).
* **IFVG-L12: PASS.** The automated part (validation 1.23.0, `tests/test_ifvg_freeze.py`), and **IFVG-L12 MANUAL = PASS** (user, 2026-11-03: the procedure below, four cases in three states).
* IFVG-L01 … L05: not recorded one by one; L00, L10, L11 and L12 cover their logic. TradingView results are recorded only from the user's results, never assumed.
* **IFVG FROZEN:** tag `IFVG_BASELINE_v0.9.1-dev` (`docs/IFVG_FREEZE_REPORT.md`, copy in `releases/v0.9.1-dev/`). v0.9.0-dev was never compiled; v0.9.1-dev (revised memory) superseded it.

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
| S-IFVG-13 | IFVG-L11 human / golden: 22 real MNQ cases (20 inside the real v0.9.1-dev capture, 2 from v0.8.0-dev): the candles are the evidence bars; IFVG-R by hand gives every recorded number; the oracle and `IfvgPine` give the verdict on the window and on the whole capture; the real Pine log agrees (FVG_INVALIDATED and IFVG_INVERTED of the same FVG id on the same bar, the audit geometry, every later IFVG event and CE / full fact); the context is the Pine log's and never changes the verdict; the mirror; the coverage A–R; R1 mechanical; MEM1 on the real log; H1 supporting | `validation/golden/human/ifvg/`, `tests/test_ifvg_golden.py` |
| S-IFVG-14 | the real v0.9.1-dev capture (IFVG-L10): 0 DIFFERENCE, its counts pinned; every IFVG_DROPPED_MEMORY was INVALIDATED before it (121 in the log, 31 in the snapshot, 1 before the snapshot); the bearish side over 50 ACTIVE for 655 bars (peak 66), all kept | `parity/evidence/`, `tests/test_parity_v091_evidence.py` |
| S-IFVG-15 | IFVG-L12 automated, each requirement by name (table in the file's docstring). (1) Two fresh runs are identical on every bar: shadows, every record field, memory, the bar's events; the Pine-Log text of the event stream byte for byte; the oracle per bar. (2) A bar only adds its inversions, stamps facts / ends of ACTIVE IFVGs, drops INVALIDATED records; a prefix = the full run's past; a later history start keeps every IFVG of an FVG confirmed ≥ 16 bars after it. (3) Every module and display setting on / off; the engine reads only `ifvgOn` and Phase 1. (4) Two reloads from the real Pine state with 51–66 ACTIVE bearish IFVGs keep the same ACTIVE set. (5) The same-bar order in the real Pine log, a pinned example (05:57), memory 1 / 2 / 50. (6) Phase 1 unchanged on every bar | `tests/test_ifvg_freeze.py` |

## TradingView procedure (NQ1! or MNQ1! 1m; Confirmed only ON)

Before you start:
1. In the Pine Editor, replace the code with `src/IST.pine` v0.9.1-dev.
2. Save it, and add it to a 1m chart, or update the chart's copy.

There is **no IFVG drawing** in this build. Developer → **Debug mode** ON adds four Data Window values, `dbg · IFVG …`, and the events in Pine Logs.

| id | test | how | expected |
|---|---|---|---|
| IFVG-L00 | compile and runtime · **PASS** (user) | the procedure below | no compile error, no runtime error, the chart loads, everything else as in v0.8.0-dev |
| IFVG-L01 | settings | open the settings | a group IFVG with one checkbox, "Enable IFVG engine", ON. No other IFVG input |
| IFVG-L02 | the inversion on a candle | Debug ON, Show FVGs ON; find an FVG that a candle closes beyond (bullish FVG: close below its bottom) | on that candle: `FVG_INVALIDATED` then `IFVG_INVERTED BEAR` with the same id and `bottom / top / ce` of the FVG. A candle whose wick goes beyond and closes inside or exactly at the edge gives neither |
| IFVG-L03 | lifecycle | follow that IFVG on the next candles | `IFVG_FIRST_TOUCH` when a high reaches its bottom (never on the inversion candle); `IFVG_INVALIDATED` on the first close above its top (a close exactly at the top, or a wick above it, is not an end) |
| IFVG-L04 | engine OFF / other modules / visibility | Enable IFVG engine OFF, then ON; then Show FVGs OFF | while OFF: no IFVG events, IFVG values na. Every drawing, Debug row and alert of the other modules identical either way. Show FVGs OFF changes no IFVG value |
| IFVG-L05 | no drawing, no alert | look at the chart; an "Any alert() function call" alert | nothing IFVG-related drawn; no IFVG alert message |
| IFVG-L10 | **real parity (freeze gate)** · **PASS (2026-11-02)** | Developer → Parity capture ON (N = 1000); save the Pine Logs into `validation/parity/`; run `python -m validation.parity --capture <file>` | **0 DIFFERENCE**, the IFVG section included (shadows, active per side, facts per bar; events; snapshot records) |
| IFVG-L11 | **human golden cases (freeze gate)** · **PASS** (2026-11-03: automated, and the user's sanity review) | the cases of `validation/golden/human/ifvg/` (real candles), then the user's visual check of the sanity cases (README there) | every deterministic golden reproduced, or each difference explained |
| IFVG-L12 | **reload (freeze gate)** · **PASS** (2026-11-03: automated, and the user's manual reload) | automated: `tests/test_ifvg_freeze.py`; manual: the procedure below (3 IFVGs + 1 rejection; refresh the page; remove and re-add the indicator) | the same IFVGs, unchanged: id, side, geometry, inversion, lifecycle lines (any FVG confirmed ≥ 16 bars after the first loaded bar); the rejection stays NO IFVG |

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

### IFVG-L12 manual: TradingView reload (what you do)

**Set-up.**
* **MNQ1!** 1m (CME_MINI:MNQ1!, back-adjustment default, settlement as close, as in the capture), IST **v0.9.1-dev**, default settings, Confirmed only ON.
* Developer → **Debug mode ON**. Times are New York.
* The chart must still load 2026-11-02; a 1m chart loads a few days of history.

There is no IFVG drawing, so you compare the **Pine Logs** lines.
* For each case, search Pine Logs for its id (for example `id=2026-11-02 08:14`) and note its IFVG lines (time, side, id, px, bottom / top / ce, pre).
* Do it three times:
  * **A.** on the chart as it is;
  * **B.** after a browser page refresh (F5), once the chart has loaded;
  * **C.** after removing IST from the chart and adding it again, with Debug mode ON again.
* **PASS:** A, B and C give the same lines for every case.

Not part of the comparison:
* **CE and full traversal** are record facts, not Pine Logs lines. The automated tests and the real parity cover them.
* **`IFVG_DROPPED_MEMORY`** (and Phase 1's `FVG_DROPPED_MEMORY`) is bookkeeping. Its time follows how many older records the loaded history holds. If it moves, or disappears, after B or C because the first loaded bar moved, that is not a failure: note it.
* **"inversions so far (loaded history)"** in the Data Window counts from the first loaded bar, so it may change after a refresh.

| # | case | original FVG (id = candle 3) | IFVG | expected Pine Logs lines | final state |
|---|---|---|---|---|---|
| 1 | **bearish** (golden A3) | bullish FVG, candle 1 08:12, candle 3 **08:14** → `id=2026-11-02 08:14`; bottom 28713.75, top 28717.00, CE 28715.375; its CE was touched before | **BEAR**, the same bottom / top / CE; inversion **08:17**, close 28709.50, pre CE | `08:17 FVG_INVALIDATED BULL id=2026-11-02 08:14 px=28709.50 · close<bottom` · `08:17 IFVG_INVERTED BEAR id=2026-11-02 08:14 px=28709.50 · bottom=28713.75 · top=28717 · ce=28715.375 · pre=CE` · `08:18 IFVG_FIRST_TOUCH BEAR id=2026-11-02 08:14 px=28713.75 · high>=bottom` (CE and full traversal also at 08:18) · `08:36 IFVG_INVALIDATED BEAR id=2026-11-02 08:14 px=28754.25 · close>top` · bookkeeping: `08:36 IFVG_DROPPED_MEMORY BEAR id=2026-11-02 08:14` | **INVALIDATED** 08:36 |
| 2 | **bullish** (golden B2) | bearish FVG, candle 1 14:24, candle 3 **14:26** → `id=2026-11-02 14:26`; bottom 28301.50, top 28321.00, CE 28311.25; untouched before | **BULL**; inversion **14:27** (the large candle, the first eligible bar), close 28349.75, pre UNTOUCHED | `14:27 FVG_INVALIDATED BEAR id=2026-11-02 14:26 px=28349.75 · close>top` · `14:27 IFVG_INVERTED BULL id=2026-11-02 14:26 px=28349.75 · bottom=28301.5 · top=28321 · ce=28311.25 · pre=UNTOUCHED` · `14:31 IFVG_FIRST_TOUCH BULL id=2026-11-02 14:26 px=28321.00 · low<=top` (CE 14:31, full traversal 14:32) · `14:36 IFVG_INVALIDATED BULL id=2026-11-02 14:26 px=28282.25 · close<bottom` | **INVALIDATED** 14:36 |
| 3 | **lifecycle** (golden B4) | bearish FVG, candle 1 15:39, candle 3 **15:41** → `id=2026-11-02 15:41`; bottom 28128.50, top 28133.25, CE 28130.875; fully filled before | **BULL**; 15:42 is a wick above the top (high 28138.50, close 28125.75): **no line**; inversion **15:43**, close 28143.50, pre FULL | `15:43 FVG_INVALIDATED BEAR id=2026-11-02 15:41 px=28143.50 · close>top` · `15:43 IFVG_INVERTED BULL id=2026-11-02 15:41 px=28143.50 · bottom=28128.5 · top=28133.25 · ce=28130.875 · pre=FULL` · `15:50 IFVG_FIRST_TOUCH BULL id=2026-11-02 15:41 px=28133.25 · low<=top` (CE and full traversal 15:51) · bookkeeping: `15:56 FVG_DROPPED_MEMORY BEAR id=2026-11-02 15:41 · closed record` (Phase 1 releases the parent; the IFVG lives on) · `15:57 IFVG_INVALIDATED BULL id=2026-11-02 15:41 px=28105.75 · close<bottom` | **INVALIDATED** 15:57 |
| 4 | **rejected: wick only** (golden C2) | bearish FVG, candle 1 10:47, candle 3 **10:49** → `id=2026-11-02 10:49`; bottom 28787.75, top 28791.75, CE 28789.75 | **NO IFVG**: at 10:51 (O 28787.25 · H 28792.50 · L 28764.50 · C 28765.00) the wick goes above the top, the close stays below it | only Phase 1 lines: `10:49 FVG_CREATED`, `10:50 FVG_FIRST_TOUCH`, `10:50 FVG_CE_TOUCH`, `10:51 FVG_FULL_FILL`. **No `FVG_INVALIDATED` and no `IFVG_` line with this id**, at 10:51 or later (up to at least 23:11) | no IFVG |

**Record:** PASS, or FAIL with the case, the step (A, B or C) and the line that changed.

**Result (user, 2026-11-03): PASS.** All four cases, Debug ON, in A, B and C: the IFVG / FVG Pine Logs identities, the inversions and the lifecycles stayed the same.
* The documented exceptions were accepted and are not failures: the timing of IFVG_DROPPED_MEMORY, "inversions so far", CE / full as facts, and the IFVGs of FVGs confirmed inside the first ~16 loaded bars (`docs/IFVG_FREEZE_REPORT.md` §6).
