# Changelog

## Tooling · validation agent 1.3.1 (2026-10-27, branch `tooling/validation-agent`) — capture importer reads TradingView's Pine Logs CSV — no indicator change

**ROOT CAUSE.** TradingView saves Pine Logs as a real CSV (`Date,Message`) with every message quoted and inner quotes doubled. The capture importer read physical lines, so the closing quote stayed in the last value (`warmup=17"`, `int()` failed). The doubled quotes of the JSON tickerid in `sym=` were not undone either.

**FIX** (`validation/parity/capture.py`):
* Input detection: a `Date,Message` header means the file is read with the `csv` module (strict). The Message column is found case-insensitively, and only that field is parsed. The Date column is kept for diagnostics.
* Plain pasted text still works. A `date,"message"` row pasted without its header is decoded too. CRLF and a UTF-8 BOM are handled.
* Capture runs: the log is split into CAPTURE … END runs that are never merged. A file saved newest first is turned around. The latest complete and valid run is used, and every run is listed.
* Stricter: END is required, and the BAR count must equal END and `bars + warmup`.
* `python -m validation` picks the most recently saved `parity/pine_capture*.csv` / `.txt`.
* `src/IST.pine` and the capture format are unchanged.

**TESTS.**
* 12 new tests: TradingView CSV, quoted JSON in CAPTURE, `warmup=17` read as 17, CRLF, BOM, commas, doubled quotes, header-less rows, capture runs never merged, a file saved newest first, a missing Message column, malformed CSV.
* A committed regression fixture with the real file shape: `tests/fixtures/pine_logs_capture_synthetic.csv`.

**RESULT ON THE USER'S FILE** (`pine_capture.txt.csv`, as saved, 317 bars): BOUNDED PINE-LOG BAR-BY-BAR PARITY **PASS**. 300 bars × 7 series and 340 events compared, 0 differences.

## Tooling · validation agent 1.3.0 (2026-10-27, branch `tooling/validation-agent`) — bounded Pine-Log parity

* `python -m validation.parity --capture validation/parity/pine_capture.txt` rebuilds the exact candles of an IST *Parity capture* pasted from Pine Logs, replays them with the oracle, and compares two things after the warm-up:
  * on every bar: FVG verdict and required gap, swing verdicts, reactions on PASS bars, required reaction;
  * the events of structures born inside the window: type, direction, id, time, price, duplicates, extra and missing.
* Everything that depends on history before the window is NOT OBSERVABLE: older levels and FVGs (and their takes), EQ clusters, memory drops, running sessions, LEVEL_SET.
* The parser rejects inexact input with line numbers: a missing bar, a duplicate bar, wrong OHLC, a malformed timestamp, a count that disagrees with END, no CAPTURE line.
* Three parity levels, labelled apart in the CLI and the report: FULL CSV BAR-BY-BAR PARITY, BOUNDED PINE-LOG BAR-BY-BAR PARITY, MANUAL EVENT PARITY. CSV parity and manual parity are unchanged.
* 21 new tests (`tests/test_parity_capture.py`), including successful parity on 4 configurations. A one-off sweep of 138 runs (3 presets × 20 seeds, windows of 300–2,000 bars) gave 0 false differences.

## v0.4.3-dev — Parity capture to Pine Logs (2026-10-27, branch `tooling/validation-agent`)

**CHANGE.** Diagnostics only (L7). Two new [view] inputs in DEVELOPER: "Parity capture → Pine Logs" (**default OFF**) and "Capture last N closed bars" (300, 50–2,000). When the capture is ON:
* One CAPTURE line with the calculation settings.
* For each of the last N closed bars, plus the warm-up the comparison needs (max(FVG length + 2, max(14, left) + right); Balanced 17), one BAR line followed by that bar's events. The BAR line holds:
  * time with UTC offset and bar index;
  * OHLC with 8 decimals;
  * FVG verdict and required gap;
  * swing verdicts;
  * reactions on pivot bars;
  * required reaction.
* Then END.
* Bounded by a counter: at most N + warm-up bars, nothing afterwards, also in realtime.
* While the capture is ON, the Debug-mode event logging is limited to the captured bars.

**WHY.** On a free plan there is no candle export. The capture gives the exact OHLC of a window, so the oracle can replay Pine's own bars.

**PHASE 1 IMPACT.** None. No detection, state, event, alert or drawing line changed. The BAR line prints values that the Data Window plots already compute.

**REPAINT IMPACT.** None. Only `barstate.isconfirmed` bars are logged. `last_bar_index` only selects which closed bars are written.

**REGRESSION TESTS.**
* The static checks and the full validation agent pass. The oracle and the regression baseline are unchanged.
* TradingView: L00 must be re-run on v0.4.3-dev. New L44 (capture) is PENDING.

## Tooling · validation agent 1.2.0 (2026-10-27, branch `tooling/validation-agent`) — manual event parity for the free plan

* `python -m validation.parity --manual validation/parity/manual_observed.txt --preset balanced` compares what you copy from the IST debug table and Pine Logs with the oracle. No TradingView export is needed.
  * Input: `KEY=VALUE` lines and `EVENTS … END_EVENTS` blocks (`parity/manual_observed_template.txt`). The parser tolerates copy/paste spacing, case, `KEY: value`, thousands separators and a decimal comma. It rejects a malformed file with every bad line numbered.
  * Checks: preset table and Confirmed only; candle alignment with the loaded history; internal row consistency; rows 22–26 against the oracle; each event's type, time, direction, id and price; duplicates; extra events; missing events inside each block. Every check prints MATCH, DIFFERENCE or NOT OBSERVABLE.
  * The candles come from any OHLC CSV (`CANDLES=`). The CSV loader also accepts a `datetime` / `date` / `timestamp` column.
* The CLI and the report label the two levels separately: FULL BAR-BY-BAR PARITY (Data Window export) and MANUAL EVENT PARITY (weaker; never reported as full parity).
* `parity/manual_observed.txt` holds the user's 2026-10-27 runtime numbers (settings, rows 22–23). Its events, loaded history and candles are still to be added.
* 26 new tests (`tests/test_parity_manual.py`): a valid file matches; copy variants parse; 14 malformed inputs are rejected; a missing, extra, duplicate, wrong-time, wrong-price event and a wrong swing count are each detected.

## v0.4.2-dev — debug output for manual parity (2026-10-27, branch `tooling/validation-agent`)

**CHANGE.** Diagnostics only (L7), with Debug mode ON:
* Every event of a closed bar is written to **Pine Logs**: one line, the "Last events" text with the full date (`yyyy-MM-dd HH:mm  NAME … id=… px=… · reason`). The pane keeps up to 10,000 historical lines and can be searched.
* **Debug row 34 "Loaded history (closed bars)"** shows the first loaded bar, the last closed bar, the number of bars and the timezone. The table grows from 34 to 35 rows.
* The Debug-mode tooltip mentions the logs.

**WHY.** On a free plan there is no *Export chart data*, and the debug table is drawn on the chart. Pine Logs give the event history as text. Row 34 tells a replay where Pine's history starts and ends, so the oracle can run on the same bars.

**PHASE 1 IMPACT.** None. No detection, state, event, alert or drawing line changed. The logs read the bar's event list. `dbgFirstT` is a display-only `var`.

**REPAINT IMPACT.** None. The logs are gated by `barstate.isconfirmed`, so an open bar is never logged.

**REGRESSION TESTS.**
* The static checks and the full validation agent pass. The oracle is unchanged, so the regression baseline is unchanged.
* TradingView: L00 must be re-run on v0.4.2-dev (it passed on v0.4.1-dev). New L43 covers the row and the logs (PENDING).

## Tooling · validation agent 1.1.0 (2026-10-27, branch `tooling/validation-agent`) — no indicator change

* Pine ↔ Python parity from one TradingView *Export chart data* CSV (IST Debug mode ON). The new command is `python -m validation.parity EXPORT.csv --preset balanced`.
  * It writes `validation/parity/pine_observed.json`.
  * It compares the 9 IST Data Window series bar by bar with the oracle: FVG verdict and required gap, swing verdicts, reactions, required reaction, and BSL/SSL take codes.
  * It prints the swing counts to check against debug rows 22–23, and every difference with its New York time.
  * The validation report shows the comparison.
* The report's TradingView column and MANUAL list now show the results the user recorded in `docs/TESTS_PHASE2.md` (L00 = PASS, 2026-10-27). The agent never sets them itself.
* `src/IST.pine`, the detection logic and `PHASE1_BASELINE_v0.3.2` are unchanged.

## Tooling · validation agent 1.0.0 (2026-10-27, branch `tooling/validation-agent`) — no indicator change

* `validation/`: one command (`python -m validation --mode quick|full|deep`) runs static checks of `src/IST.pine`, the Python reference model (oracle) of Phase 1 and Phase 2, deterministic scenarios, 40 named invariants with negative tests, Hypothesis property and stateful tests, long random walks, regression against a committed baseline and the legacy models in git, a golden dataset and a Pine-parity layer, and writes `validation/reports/VALIDATION_REPORT.md`. Exit code 0 only when every automated check passes.
* `tests/liq_model.py` is replaced by `validation/models/` (liquidity results identical; the old versions stay readable at tags `v0.4.0-dev` and `v0.4.1-dev` and are cross-checked on every run).
* Tag `v0.4.1-dev` added on commit 96ed891. `src/IST.pine` and `PHASE1_BASELINE_v0.3.2` are unchanged.
* Nothing here tests TradingView: compilation, runtime, rendering, limits, request.security and alerts stay MANUAL.

## v0.4.1-dev — Phase 2 hardening review: EQ boundary and selectivity diagnostics (2026-10-27, branch `phase2/liquidity`)

**BASELINE.** v0.4.0-dev stays reachable as git tag `v0.4.0-dev` (commit 96f7846). `PHASE1_BASELINE_v0.3.2` is untouched.

**AUDIT RESULT.** The question was whether a fixed EQH reference ("extreme member, fixed at creation") can stop being the pool's outer boundary when a later member joins.
* **v0.4.0-dev had no behavioural defect.** A member beyond the boundary can never join an active cluster (proof: LIQUIDITY.md DEF-L5.4). With the DEF-L1 pivot, such a swing must print after the cluster's latest member was confirmed, so its own bar takes the cluster first.
* **The defect was in the specification and the record.** Identity and boundary shared one field. The proof was one sentence. The review case (a one-tick run through an EQH that forms a new swing) and the silent end of an unqualified group were not described.

**CHANGES**
* **`EqCluster`** now separates its concepts:
  * identity: `id`, `ref` (creation reference), origin and the founding members (`members[0..1]`)
  * current state: `bound` (current outer boundary, moves outward only), `lastBar/Time` (latest member's confirmation)
  * Joins, takes, classification, the trigger gate, event prices and drawings all use `bound`. A join keeps `id` and `ref`, emits no event and creates no cluster.
* **DEF-L5 rewritten** as DEF-L5.1–L5.6:
  * identity versus boundary
  * join and form
  * individual versus cluster liquidity
  * the no-expansion theorem with the worked example
  * exact timing (no self-trigger, no retroactive take)
  * the cluster lifecycle
* **DEF-L1:** the plateau rule is documented in full: why the first bar, when it confirms, and no duplicate swings. The rule itself is unchanged.
* **Debug:**
  * rows 22–23 give, per side over the loaded history: pivot candidates · significance PASS · REJECT (%) · warm-up → levels created (new counter `rejects`)
  * new row 32 "EQ cluster (pool)": cluster id, boundary and reference (`DIFFERS` if they ever differ), member count, latest member, known/taken
  * row 31 now shows only the inspected swing's own status
  * table 32 → 34 rows; "Last events" row 31 → 33
* **Tests:**
  * model scenarios L35–L42
  * per-bar invariant fuzz over 4 configurations (7 runs, 140,000 bars)
  * an equivalence run against the v0.4.0-dev model: identical event logs, 149,751 events
  * TESTS_PHASE2.md gains S-11–S-13 and L35–L42.
* **Not changed:**
  * presets (3/2/0.5 · 5/3/1.0 · 10/5/2.0)
  * TAKEN / SWEEP / BREAK definitions (single-bar classification)
  * the plateau rule, alerts, rendering budgets, Phase 1

**SHARED INFRASTRUCTURE CHANGES**

| CHANGE | WHY | PHASE 1 IMPACT | REPAINT IMPACT | REGRESSION TESTS REQUIRED |
|---|---|---|---|---|
| Debug table 32 → 34 rows; "Last events" row 31 → 33 | Selectivity per side and the EQ cluster row | Display only; rows 0–20 unchanged | None | T46 (Phase 1 inspector) under L27 |

**WHY:** the review asked for an exact, testable cluster state model before the first TradingView compile.

**LIQUIDITY BEHAVIOUR:** unchanged in every reachable state. The model shows identical events to v0.4.0-dev, and `bound == ref` held on every fuzz bar.

**PHASE 1 BEHAVIOUR:** unchanged. The diff against `PHASE1_BASELINE_v0.3.2` removes the same lines as v0.4.0-dev (S-06).

**REPAINT:** none added. A boundary change, if it ever happens, takes effect from the next bar and never re-evaluates past bars.

**TESTS:**
* static/model 13/13 PASS (here)
* runtime L00–L42: 43 tests, all PENDING MANUAL VALIDATION
* Phase 2 is not complete.

## v0.4.0-dev — Phase 2: liquidity engine (2026-10-27, branch `phase2/liquidity`)

**BASELINE**

* v0.3.2 is preserved as the Phase 1 safety baseline:
  * git commit tagged `PHASE1_BASELINE_v0.3.2` on `main`, verified byte-exact; `core.autocrlf` is off for this repository
  * a read-only copy in `releases/v0.3.2/` with `SHA256SUMS.txt`
* Phase 2 work happens on `phase2/liquidity`.

**CHANGES (new module; specification in docs/LIQUIDITY.md)**

* **Swings (DEF-L1):**
  * The pivot is strict on the left and non-strict on the right.
  * Origin = X; confirmation = X + right. Judged on confirmed bars only.
* **Significance (DEF-L2):** reaction inside the confirmation window ≥ k × TR average at X. The TR average is SMA(TR, 14) with its own fixed length.
* **Presets (DEF-L3):** Aggressive 3/2/0.5, Balanced 5/3/1.0 (default), Strict 10/5/2.0, and Custom.
* **BSL/SSL records, taken, sweep, break (DEF-L4):**
  * take = strictly beyond, with no event on an exact touch
  * classification = the close of the taking bar: strictly beyond = BREAK, otherwise SWEEP
  * decided once, never relabelled
* **EQH/EQL clustering (DEF-L5):**
  * the reference is the extreme member, fixed at creation
  * the intact-pool rule; one cluster per pool
* **Lifecycle and memory (DEF-L6):**
  * live/closed sets, 100 records per side, 25 clusters per side
  * every drop is logged
  * a trigger-price gate keeps the work incremental
* **Renderer (DEF-L7):**
  * last-bar rebuild, nearest-first, budgets 5/3/2 per side
  * EQ members are merged into their cluster line
  * no duplicate line on visible PDH/PDL/PWH/PWL or session high/low lines
* **Events:** `BSL/SSL_CREATED`, `_TAKEN`, `_SWEEP`, `_BREAK`, `_DROPPED_MEMORY`; `EQH/EQL_CREATED`, `_TAKEN`, `_DROPPED_MEMORY`.
* **Alerts:** taken, sweep, break and EQH/EQL taken, all **default OFF**.
* **Debug:**
  * table rows 21–30 (engine, swings, BSL, SSL, EQ, drawn, inspector)
  * 7 Data Window plots
* **`tests/liq_model.py`:** a reference model with 18 scenarios and a fuzz of invariants (first reported as "19": that count included the fuzz).

**SHARED INFRASTRUCTURE CHANGES**

| CHANGE | WHY | PHASE 1 IMPACT | REPAINT IMPACT | REGRESSION TESTS REQUIRED |
|---|---|---|---|---|
| `f_evName(k)` → `f_evName(k, dir)`; `f_evText` adds no BULL/HIGH suffix to liquidity kinds | Liquidity event names carry their side (BSL_/SSL_, EQH_/EQL_) | None: kinds 1–9 produce identical text | None | L27 (event text in the T01/T02 logs) |
| Intrabar alert de-dup key `kind:sid` → `kind:dir:sid` | A BSL and an SSL from one outside bar share a swing-time id | None: FVG keys were already unique (one FVG per bar) | None (alert delivery only) | L27; Phase 1 intrabar-alert tests when run |
| `f_alertOn` gains liquidity cases | Liquidity alerts | None: the new toggles default OFF, so an existing alert delivers the same messages | None | L27, L31 |
| Debug table 22 → 32 rows; "Last events" row 21 → 31 | Liquidity rows | Display only; rows 0–20 unchanged | None | T46 (Phase 1 inspector) under L27 |
| 7 plots appended after the 11 Phase 1 plots | Liquidity Data Window audit | Display only; Phase 1 plot order unchanged | None | T03a reading under L27 |
| Tooltips for Minimal mode and Debug mode | They mention liquidity | Text only | None | — |
| The liquidity block runs after Phase 1 inside the same `engineTick` gate | Same confirmed/live contract | None: no Phase 1 state is read or written | None | L27, L31 |

**WHY**

* Phase 2 scope, as instructed.
* The order was P2.1 → P2.8, in one auditable branch.

**PHASE 1 BEHAVIOUR**

* Unchanged.
* The diff against the tag (S-06) shows display and text changes only.
* With liquidity OFF the chart is the Phase 1 chart (L31).

**REPAINT IMPACT**

* None for Phase 1.
* Liquidity follows the same contract. Declared exceptions: warm-up, the memory window, and drawings that show the present (LIQUIDITY.md §6).

**PERFORMANCE IMPACT**

* 1 SMA and 4 window extremes per bar.
* Gated per-side loops.
* Rendering on the last bar only.
* ≤ 20 lines and 20 labels by default (80 + 80 at maximum).
* 0 new requests; 18 plots.
* Execution time is unmeasured (L22).

**TESTS**

* S-01…S-10 PASS (static/model, here).
* L00–L34 PENDING MANUAL VALIDATION (docs/TESTS_PHASE2.md).
* Phase 1: unchanged statuses (8 PASS on v0.3.1/v0.3.2, T03 FAIL pending re-test).

**KNOWN LIMITATIONS:** LIQUIDITY.md §11. The main ones:

* a one-bar classification window
* EQ tolerance in ticks only
* a weak reaction floor on noise-like data
* drawings show the present
* not compiled here

## v0.3.2 — T03 investigation: explicit, auditable size threshold (2026-10-27)

**ROOT CAUSE**

* **Not confirmed. No defect was found in the v0.3.1 code path.**
* The v0.3.1 filter (L4, line 352) was:
  `gap >= fvgMinTicks * syminfo.mintick - EPS and (fvgMinTra <= 0 or gap >= fvgMinTra * refTra) and (fvgMinRng <= 0 or gap >= fvgMinRng * refRng)`
  * With minTicks = 40 and `syminfo.mintick` = 0.25, it requires gap ≥ 9.9975.
  * A 6.00-point gap evaluates false, so no record can be created.
* There was only one creation site (`Fvg.new`), reached only through `bullCand`/`bearCand`, and both used the same function.
* Any input change makes TradingView recalculate the script from bar 0 with fresh `var` state. The engine has no `varip` or cross-run state, so stale values from the earlier setting can't survive.
* **Hypotheses that explain the observation, in order of likelihood:**
  1. **The v0.3.1 inspector printed `top · CE · bottom` as three unlabelled numbers.** If 29477.75 was the middle value (the CE), the record's bottom is 29471.75: gap = 12.00 pts = 48 ticks, which **correctly passes** 40 ticks. The `FVG_CREATED` reason text (`bottom–top`) in the event log would show this. This is a real debug-UX defect; it is fixed in v0.3.2.
  2. **`syminfo.mintick` ≠ 0.25 on that chart.** A 6-point gap passes only if mintick ≤ 0.15. It is now visible in the Data Window and the inspector.
  3. **The Data Window "gap size" was read with the cursor on a bar other than that gap's candle 3.**
  4. **A runtime behaviour different from the source semantics.** The new `size check @ birth` row prints INCONSISTENT for any record that fails its own birth thresholds, so this can now be proven or ruled out.

**CHANGES**

* **L4 rewritten into named series, with identical semantics:**
  * `rawGap` (points, same for both sides), `tickReq = fvgMinTicks * syminfo.mintick`
  * `traReq = fvgMinTra > 0 ? fvgMinTra * refTra : 0.0`, `rngReq = fvgMinRng > 0 ? fvgMinRng * refRng : 0.0`
  * `reqGap = math.max(tickReq, traReq, rngReq)`
  * `gapPass = not na(rawGap) and rawGap >= tickReq - EPS and rawGap >= traReq and rawGap >= rngReq`
  * `bullCand = rawBull and gapPass`, `bearCand = rawBear and gapPass`
  * `f_qualifies` was removed.
* **`Fvg` gains the fields `thrTick`, `thrTra` and `thrRng`:** the thresholds in force at birth.
* **Inspector:**
  * row "zone prices" is now labelled (`top … · CE … · bottom …`)
  * new row "size check @ birth": gap in points and ticks, mintick, the three thresholds, the required max, and PASS/INCONSISTENT
  * the table grows to 22 rows
* **Data Window (debug):**
  * candle-3 verdict (±2 PASS, ±1 REJECT, 0 no gap)
  * raw gap in points and in ticks, `syminfo.mintick`
  * the required gap from ticks, from TR average and from avg range, and the required max
  * the existing TR average, avg range and record count
  * 11 plots, all Data Window only
* Version v0.3.2.

**WHY**

* T03 reported a 24-tick FVG passing a 40-tick filter. The code path is correct on inspection and in an executed model (S-06), so this release makes every number in the decision visible, per bar and per record, so the next test proves or refutes a bug directly.

**REPAINT IMPACT**

* **None. Historical FVG detection is unchanged.** The new expression equals the old one on 500,000 random cases, including `na` references (S-06).
* Ids, events, state and rendering are unchanged. Only the debug output differs.

**PERFORMANCE IMPACT**

* Negligible: a few float series, 3 fields per record, and 6 more Data Window plots, visible only with debug on.

**TESTS**

* Static and formula checks S-01…S-06, executed here: **PASS 6/6**.
* New regression test **T03a**: a 6.00-pt (24-tick) NQ gap is rejected at Min ticks = 40. **PENDING MANUAL VALIDATION.**
* **Manual results recorded:** T00, T01, T02, T09–T13 **PASS** (v0.3.1), still valid because v0.3.2 changes no behaviour. **T03 FAIL** (v0.3.1), to re-test on v0.3.2.
* **Runtime score:** 8 / 50 PASS, 1 FAIL, 41 PENDING.

**KNOWN LIMITATIONS**

* Unchanged from v0.3.1.
* If T03a confirms that a sub-threshold record exists (verdict +2 or INCONSISTENT), the cause lies in runtime behaviour that the source doesn't show, and it will need the exact screenshots to diagnose.

## v0.3.1 — Phase 1 frozen candidate (2026-10-27)

**CHANGES**

* **Renamed "ATR" to "TR average"** wherever the implementation is not Wilder ATR:
  * input labels: "Min size · × TR average" and "TR-average / avg-range length"
  * tooltips
  * Data Window: "dbg · TR average at candle 1 (t-2)"
  * the inspector's "× TR avg"
  * code identifiers: `fvgMinTra`, `traNow`, `refTra`, `sizeTra`, `TT_TRA`
  * ARCHITECTURE and TESTS
  * Formula unchanged: `ta.sma(ta.tr(true), 14)[2]`. No Wilder option.
* **"Draw zones from" default changed to Candle 3 (confirmation).** Candle 1 (origin) is still selectable. Tooltip updated.
* **Docs:**
  * the decisions are recorded (ARCHITECTURE §12)
  * **future requirement:** FVG identity = symbol + timeframe + direction + confirmation time, for when HTF and LTF structures coexist (ARCHITECTURE §3.1, §10.10). The ID system is not changed in Phase 1.
* **Previous-day definition stays UNRESOLVED.** The TradingView D/W confirmed source is kept for validation. It is not labelled "CME ETH".

**WHY**

* The approved decisions. A non-Wilder average must not be called ATR. The default view must not imply knowledge before confirmation.

**REPAINT IMPACT**

* None in calculation. The TR-average values, detection, events and ids are identical to v0.3.0.
* Display: by default, FVG boxes now start at candle 3 instead of candle 1.
* Input defaults changed, so a chart that already has the indicator keeps its saved settings. Re-add it, or reset settings, to get the new defaults.

**PERFORMANCE IMPACT**

* None.

**TESTS**

* Static checks S-01…S-04 re-executed on v0.3.1: **PASS 4/4**.
* Runtime tests: 0/49 passed. All 49 are **PENDING MANUAL VALIDATION**. T01, T03, T39 and T41 were updated for the renaming and the new default.

**KNOWN LIMITATIONS**

* Unchanged from v0.3.0.

**FREEZE**

* v0.3.x is frozen. No further architectural work unless compilation or the manual tests reveal a problem. Next step: TradingView compilation, then the Phase 1 manual tests.

## v0.3.0 — Phase 1: deliberate retention, draw-free state, reload-stable ids (2026-10-27)

**CHANGES**

* **FVG retention (C1).**
  * Invalidated records are no longer removed. They stay in memory as **closed** records.
  * `Engine memory` (default 50 per direction, [calc]) now counts open and closed records together.
  * When over budget, the oldest closed record is released first, then the oldest open one. The event is renamed to **`FVG_DROPPED_MEMORY`**, with the reason "closed record" or "open record · lifecycle tracking stopped". Debug counts drops by type.
* **State is draw-free (C2).**
  * `f_roll`, `f_sesNew` and the other L3 functions no longer receive colour, style or visibility and no longer create lines.
  * L3 hands off `lvlNewNow`, `lvlEndNow`, `sesDirtyNow`, `sesEndNow` and `fvgDropNow`. L6 decides visibility, colour, style, labels and history.
  * `RefLevel` lost its `col`/`style`/`tip` fields and gained `kind`.
  * Session history is now capped **per slot** (it was 4 × N total).
  * `rightT` moved into L6.
* **Anchor (C3).** State stores the verified extreme bar, or `na`. The [view] "Start line at the extreme's bar" is applied in L6 only.
* **ATR (C4).** `ta.atr(len)` (RMA) became `ta.sma(ta.tr(true), len)`, a finite window, still sampled at t-2. **This is a definition refinement and needs your approval.**
* **Ids (C5).** FVG `id` = confirmation time; session `id` = start time. The sequential counters were removed. Ids display as `yyyy-MM-dd HH:mm` (ET).
* **Replay readiness (C6).**
  * Milestone **times** were added next to the bars.
  * New methods `activeAt(z, b)`, `policyTime()` and `metNow()`.
  * The renderer reconciliation takes the reference bar.
* **New [view] input "Draw zones from":** Candle 1 (origin, default) or Candle 3 (confirmation).
* **Debug:**
  * an FVG inspector (`Inspect FVG` n-th newest) showing direction, id, tf, origin → confirm (bar and time), top/CE/bottom, size in ATR, milestone times, policy status, OPEN/CLOSED, fill, age, and whether it is drawn
  * open+closed record counts per direction
  * a 21-row table
* **Normal-mode warning** when any drawing-object type exceeds 450, so the 500 limit is never hit silently.
* **Policy transitions** are detected in L6 (`metNow`), not returned by `advance()`.

**WHY**

* Logical deletion must be deliberate and logged. Invalidated zones are needed later (IFVG, diagnostics, replay).
* The renderer must be strictly downstream. State must not depend on any display input, even indirectly.
* Reproducibility after reload. On a 1m chart the first loaded bar moves forward every time you reload later in the day. Two things depended on it:
  * the RMA ATR values, so a gap could qualify on one load and not the next
  * the sequential ids
* A future historical-inspection mode must stay possible without redesign.

**REPAINT IMPACT** (historical output changes compared with v0.2.0)

* **FVG qualification.** The values change slightly where the filter is on, because SMA ATR differs from RMA ATR. Gaps close to the × ATR threshold can flip in either direction. Result: identical detection after any reload, beyond the first `len+1` bars.
* **Ids** are different (time-based) and now stable across reloads.
* **Display.** Invalidated zones no longer vanish from logic. Their drawings are the same (faded or removed, per policy). Active display is unchanged.
* **Session history** is now N per window; before, it was 4N shared.
* **Confirmed-event timing is unchanged** for every event type.

**PERFORMANCE IMPACT**

* The per-bar FVG pass now iterates closed records too (one `na` check each; ≤ 100 records by default). L6 adds one more pass to find policy transitions.
* Level and session drawings are touched only on bars where their state changed (as before).
* Net: a small constant-factor increase, still O(records). It will be measured with the Pine Profiler in step 1.4.

**TESTS**

* `docs/TESTS.md` was rebuilt. It has 4 static checks, executed here: **PASS 4/4**. It has 49 runtime tests (T00–T48), all **PENDING MANUAL VALIDATION**, including G-V1…G-V5.

**KNOWN LIMITATIONS**

* Lifecycle history is complete only inside the memory window. Near the start of loaded history, which records survive can depend on the first loaded bar.
* There are warm-up bars (first `len+1`) with no ATR-filtered FVGs.
* The D/W source is not yet verified as the CME ETH day; the labels say PDH/PDL only.
* Fill % at a past bar can't be reconstructed (only the current extreme is kept).
* Superseded sessions and levels are not archived logically.
* Live mode depends on TradingView's rollback of object fields.
* Not compiled. Constructs to watch:
  * `int(na)` in a ternary
  * methods called on nested UDT fields
  * `str.format_time` with `EEE`
  * `for … in` over arrays of UDTs, with field writes

**DECISIONS REQUESTED**

1. Approve the SMA-ATR refinement (C4), or keep RMA and accept that results can change when the history window moves.
2. Default for "Draw zones from": Candle 1 (ICT convention) or Candle 3 (no visual before confirmation).
3. After G-V: keep the TradingView Daily bar, or move to an explicit session-based day (ARCHITECTURE §7.5).

## v0.2.0 — Phase 1: 7-layer architecture, calculation independent of visibility (2026-10-27)

**CHANGES**

* Code reorganised into the official layers: L1 market data/time → L2 detection → L4 filtering → L3 state → L5 event bus → L6 renderer → L7 alerts/diagnostics.
* Fixed the audit findings V1–V7 (ARCHITECTURE §2.1):
  * **FVG.** Detection no longer depends on `Show FVGs`.
  * **Sessions.** Membership no longer depends on the per-session show toggle.
  * **Levels.** PDH/PDL, PWH/PWL, DO and MO are always computed; the toggles only draw.
  * **Events.** Events are logged on every bar, history included; alert toggles filter delivery only.
* **FVG lifecycle.** First touch, CE touch, full fill and invalidation are independent milestones, each stamped once. A zone stays logically open until **invalidated** (or released by engine memory). The mitigation policy (default: full fill) is display/event only.
* **Logical versus visual history are now separate:**
  * new **[calc]** input "Engine memory · open FVGs per side" (default 50). Releasing a zone logs `FVG_DROPPED`.
  * "Max active per side" became **[view]** "Max visible per side", with exact last-bar reconciliation: the newest N unmitigated zones are drawn.
  * "Max age" became **[view]** "Hide zones older than".
* **Event model** (`Event` type): kind, dir, structure id, origin bar, event bar, time, price and a reason code.
  * Types: FVG_CREATED, FVG_FIRST_TOUCH, FVG_CE_TOUCH, FVG_FULL_FILL, FVG_INVALIDATED, FVG_DROPPED, SESSION_START, SESSION_END, LEVEL_SET.
  * The audit log keeps the last 40, and debug shows the last 6.
* The FVG record now carries `tf`, `originBar`, `confirmBar` and `confirmTime`. Age and mitigation state are derived, not stored.
* Sessions have sequential ids, `startBar`/`endBar` and a `complete` flag.
* **D/W source validation (DEF-G6).** The chart-aggregated high and low of every complete day and week are compared with the `request.security` values. The debug table shows `D/W source check` and the ET time of the latest boundaries.
* **Alerts.** Now per FVG event (created bull/bear, first touch, CE, full fill, invalidated). Intrabar timing is labelled experimental. Messages are machine-readable (`TYPE DIR id= px= · reason`).
* Inputs are tagged [calc], [view] or [alert]. The FVG settings are split into "FVG · CALCULATION" and "FVG · DISPLAY".
* Data Window additions: a candle-3 verdict (±2 accepted, ±1 filtered, 0 none), gap size, ATR and average range at candle 1, and the count of open FVGs.

**REMOVED (scope freeze, deliberate)**

* "Require displacement (basic)". Displacement belongs to Phase 3.
* "Middle candle closes in gap direction". It is not part of the standard 3-candle definition. **This was ON by default in v0.1.0.**
* Level and session "taken" state, the "When taken" display modes, and the "level/session taken" alerts. Taking a level is the primitive of the Phase 2 sweep/run logic, so it will be defined once, there.

**REASON**

* Adopt the official architecture and its core rule: calculation and market state must be independent of visibility.
* Preserve every FVG milestone for the later IFVG, CISD and quality modules.
* Freeze scope to Phase 1.
* Make the D/W source auditable instead of assumed.

**RISKS**

* **Not compiled yet.** The new constructs to watch are:
  * the `Event` UDT with positional `.new`
  * the ternary on array references (`up ? bullOpen : bearOpen`)
  * `str.format_time` with the `EEE` pattern
  * `switch` on `int` constants
* **Cost.** The engine now tracks zones until invalidation, at most 2 × memory = 100 by default, instead of until mitigation. Each bar does a little more work, still O(pool).
* **Drawing timing.** Active FVG drawings are created on the last bar only. When you scroll back through history, you see faded (mitigated) zones, not zones that were active at that past moment. This is the same as v0.1.0 for mitigated zones.

**HISTORICAL BEHAVIOUR (changed)**

* **More FVGs** with default settings, because the middle-candle filter is gone.
* **Zones disappear only when display caps say so.** A zone is no longer deleted when another zone pushes it out of "max active", or when it reaches "max age". It is merely undrawn, and it reappears if it qualifies again for display.
* **Level and session lines no longer change on a take.** They extend until they are superseded.

**TEST**

* Run `docs/TESTS.md` for v0.2.0: NR-01 to NR-06, V-01 to V-04, A-01 to A-22, G-01 to G-09, G-V1 to G-V5, F-01 to F-14, K-01 to K-05, and D-01 to D-03.

## v0.1.0 — Phase 1 foundation (2026-10-26)

**CHANGES**

* New script `src/IST.pine` (Pine Script v6). It contains:
  * **Module A, FVG core.** Detection with size filters (ticks, × ATR, × average range), an optional middle-candle direction filter and an optional basic displacement filter. Milestones (touch, CE, full fill, close-through), fill %, and a configurable mitigation rule. Mitigated zones fade or are removed. Per-side caps, a faded-history cap, optional max age, optional shrink, and an optional live "forming" preview.
  * **Module F, Sessions.** Four configurable windows (Asia, London, NY AM, NY PM by default) in an IANA timezone. The developing range becomes final on the first bar after the window. Taken detection, retirement, capped history, and an optional box and midpoint.
  * **Module G, Levels.** PDH/PDL and PWH/PWL via the non-repainting `[1]` + `lookahead_on` idiom. Lines are anchored at the extreme bar only when this is verifiable. Optional Day open and Midnight open. Taken views (fade, stop, hide) and capped history.
  * **Module K (Phase 1 events).** An event bus with bar-close aggregated alerts and an intrabar mode de-duplicated with `varip`.
  * **Developer overlay.** Zone ids, state, fill and age; a state table; object counts; Data Window values.
* New docs: `docs/ARCHITECTURE.md` and `docs/TESTS.md`.

**REASON**

* Phase 1 of the staged plan. These modules are the foundation that Phases 2–5 consume (liquidity, CISD, IFVG, HTF).

**RISKS**

* **Not compiled yet.** The code was written against the v6 reference but could not be run here. The points most likely to need a small fix are:
  * enum inputs with an empty inline title
  * method calls on nested UDT fields (`s.hi.markFinal()`)
  * `time()` with a session string ending in `0000`
  * the `display = display.none` argument on every input type
* **Live mode (Confirmed only OFF)** depends on TradingView rolling back UDT field writes on realtime ticks. Confirmed mode, the default, does not depend on this. See NR-04.
* **Session defaults are opinionated.** Asia 20:00–00:00 and NY AM 09:30–12:00 ET; adjust them to your workflow.

**HISTORICAL BEHAVIOUR**

* This is the first version, so there is nothing to compare against.

**TEST**

* Run `docs/TESTS.md`: NR-01 to NR-06, A-01 to A-23, G-01 to G-13, F-01 to F-16, K-01 to K-04, and D-01 and D-02.
