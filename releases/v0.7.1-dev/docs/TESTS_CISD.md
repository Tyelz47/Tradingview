# IST · CISD tests — v0.7.1-dev (freeze prepared)

**Status (2026-10-31).**
* CISD-L00, CISD-L10 and CISD-L11 **PASS**.
* CISD-L12: the automated part **PASS**; the TradingView reload check (manual) is **PENDING** (procedure below).
* CISD-L01 … L09 were not recorded one by one.
* TradingView results are recorded only from the user's results, never assumed.
* The freeze (`docs/CISD_FREEZE_REPORT.md`) is prepared. Tag `CISD_BASELINE_v0.7.1-dev` is created after the manual CISD-L12 check.

**Build:** `src/IST.pine` v0.7.1-dev (branch `cisd/pine`). Definition: `docs/CISD.md` (CISD-R, approved 2026-10-30).

**History.**
* **v0.7.0-dev, first real capture** (2026-10-30, `validation/parity/evidence/ist-v0.7.0-dev_mnq-1m_capture-1000_2026-10-30.csv`):
  * every CISD agreed with the oracle;
  * only the metadata bk differed. `cisdTra[1]`, read inside `confirmCisd`, returned the previous same-side confirmation's TR average (Pine keeps a history per call of a function; 80 of 80 reproduced);
  * fixed in v0.7.1-dev (`cisdTraPrv` at global scope); ST-21.
* **v0.7.1-dev, real capture** (`validation/parity/evidence/ist-v0.7.1-dev_mnq-1m-replay_capture-1000_2026-10-14.csv`, the user's `pine-logs-IST_5040e.csv`): **0 DIFFERENCE** in every module.

## Automated (before TradingView)

| id | what | where |
|---|---|---|
| S-CISD-1 | Pine's incremental formulation (`CisdStack`) = the approved oracle (`CisdEngine`), record for record and event for event: NQ 1m / 3m / 5m / 15m, four 20,000-bar walks, a mirrored walk, every scenario, memory 50 and 2, generated candles | `tests/test_cisd_pine.py`, `fuzz/test_cisd_properties.py` |
| S-CISD-2 | a leg longer than 500 bars is exact (origin 657, extreme 648, leg extreme 560 bars back; flip window 649 bars); 500 bars only would give another L | `tests/test_cisd_pine.py` |
| S-CISD-3 | 34 rule lines, 3 constants, the per-bar order; **no history read and no number in the engine** (no leg-length limit); guard and display inputs outside detection | ST-20 |
| S-CISD-4 | the 15 mutations the user listed and 14 more are caught, among them the v0.7.0-dev call-history read and the TR average of the confirming bar itself | `tests/test_cisd_pine.py` |
| S-CISD-5 | Pine event names = oracle names | ST-14 |
| S-CISD-6 | settings (4 normal inputs ON / ON / OFF / OFF, no mathematical input, Developer Inspect CISD); renderer (one 1 px line at L from origin to confirmation, a tiny CISD label, previous only with the toggle, no box, bar-time coordinates); debug rows 45–51; capture keys | `tests/test_cisd_pine.py` |
| S-CISD-7 | oracle: the user's T1–T18 and the record fields | `tests/test_cisd.py` |
| S-CISD-8 | invariants INV-CISD-01 … 08, each with a negative test | `invariants.py`, `tests/test_invariants.py` |
| S-CISD-9 | bounded CISD parity on faithful synthetic captures from an established state: 0 DIFFERENCE; 10 error kinds and the v0.7.0-dev bk defect detected; replay with Pine's constants | `tests/test_parity_cisd.py` |
| S-CISD-10 | no history read of a user series inside a function or method (allowed: `f_htfPack`, which runs on every bar) | ST-21 |
| S-CISD-11 | the CISD-L11 rule list and the automated CISD-L12 requirements, each pinned by name | `tests/test_cisd_freeze.py` |
| S-CISD-12 | human goldens H1 (reference product) and H2 (trader) reproduced exactly | `golden/human/`, `tests/test_golden.py` |
| S-CISD-13 | the real v0.7.1-dev capture: 0 DIFFERENCE, with its counts pinned | `tests/test_parity_v071_evidence.py` |

## TradingView procedure (NQ1! or MNQ 1m unless stated; Confirmed only ON)

Before you start: in the Pine Editor, replace the code with `src/IST.pine` v0.7.1-dev, save it, and add it to a 1m chart. Debug mode rows 45–51 show the CISD engine, its state, both sides, an inspector and what is drawn.

| id | test | how | expected |
|---|---|---|---|
| CISD-L00 | compile and runtime | add the indicator; open the Pine Logs and the status line | no compile error, no runtime error (in particular no "CISD: two confirmations on one bar"), the chart loads |
| CISD-L01 | settings | open the settings | group CISD · CHANGE IN STATE OF DELIVERY: Enable CISD engine ON, Show CISD ON, Show previous CISD OFF, CISD alerts OFF; no other CISD input. Developer: Inspect CISD |
| CISD-L02 | the drawing | look at the current CISD | one short thin line at L from the first candle of the delivery series to the confirming candle, a small "CISD" label at its end, neutral grey-brown; nothing else (no box, no older lines) |
| CISD-L03 | the definition on the chart | Bar Replay through a bullish CISD; Debug row 47 | L = the open of the first down-close candle of the series into the lowest down-close low; no CISD on a wick through L or a close exactly at L; the CISD on the first close one tick above |
| CISD-L04 | alternation | scroll through several CISDs (Inspect CISD 0, 1, 2, …) | bullish and bearish CISDs alternate; row 49 shows UP → DOWN → UP …; the first loaded CISD has UNKNOWN before it |
| CISD-L05 | toggles are view-only | switch Show CISD OFF, then Show previous CISD ON | the drawing disappears (then the previous CISD appears faded); Debug rows 46–50 do not change |
| CISD-L06 | 200-bar guard | a chart whose history is short, or Bar Replay from the chart start | no CISD drawn while bar index < 200 (row 46 says so); a CISD confirmed before bar 200 is never drawn later; CISD events still appear in Pine Logs (Debug ON) |
| CISD-L07 | alert | CISD alerts ON; create an alert "Any alert() function call" | one message per CISD_CONFIRMED at the bar close; none with CISD alerts OFF |
| CISD-L08 | other modules unchanged | Enable CISD engine OFF, then ON | FVG / sessions / levels / BSL / SSL / EQ / LRL / HTF drawings and Debug rows 0–44 identical |
| CISD-L09 | other chart timeframes | 3m, 5m, 15m charts | no error; CISDs alternate; fewer per hour on higher timeframes |
| CISD-L10 | **real parity (freeze gate)** | Developer → Parity capture ON; save the Pine Logs into `validation/parity/`; run `python -m validation.parity --capture <file>` | **0 DIFFERENCE**, the CISD section included (per-bar state and candidates, events, the definition oracle after synchronisation) |
| CISD-L11 | **human / golden validation (freeze gate)** | the human and reference CISD examples (`validation/golden/human/`, `docs/AUDIT_CISD_HUMAN.md`) against CISD-R | every deterministic golden reproduced; no systematic conflict with the human method; no approved-rule regression |
| CISD-L12 | **reload / determinism (freeze gate)** | automated: `tests/test_cisd_freeze.py`, T12, T18, parity; manual: the procedure below | historical CISDs do not change after a recalculation or a reload |

### CISD-L12 manual: TradingView reload (what you do)

1. **Chart.** Use the 1m chart, IST v0.7.1-dev, default settings, Confirmed only ON. Turn on **Debug mode** (Developer).
2. **Choose an area.** Pick a historical area with at least 3 CISDs, at least 200 bars after the chart's first loaded bar (Debug row 34 shows the first loaded bar).
3. **Note at least 3 CISDs.** For each, read Debug row 49 with Developer → Inspect CISD = 0, 1, 2, …, and write down:
   * the id (`side:origin time`);
   * L;
   * the confirmation time and close;
   * the state change (for example `DOWN → UP`).

   The same lines are in Pine Logs as `CISD_CONFIRMED … id=… px=…`.
4. **Reload, two ways.** (a) Refresh the browser page. (b) Remove IST from the chart and add it again.
5. **Compare** the same CISDs, found by their id. If new bars have closed, the Inspect index shifts, so use the id.
   * **Expected:** the same side, id (origin time), L, confirmation time and close, and the same state change.
   * The style does not need to match pixel for pixel.
6. **Record the result** below. If anything differs, save the Pine Logs of both loads.

Not part of this check: CISDs within the first ~100 bars after the first loaded bar. If the history window itself changes (more or less history), those may differ, because the state starts UNKNOWN (`docs/CISD.md` §3). That is why step 2 asks for an area at least 200 bars in.

Results (user):

| id | result | date | notes |
|---|---|---|---|
| CISD-L00 | **PASS** | 2026-10-30 / 31 | v0.7.0-dev and v0.7.1-dev compiled and ran (their real captures) |
| CISD-L01 … L09 | not recorded one by one | | |
| CISD-L10 | **PASS** | 2026-10-31 | v0.7.1-dev real capture: 0 DIFFERENCE; CISD 1,075 bar states, 94 + 94 events, the definition oracle synchronised from UNKNOWN then 94 identical; 3 body / TR values NOT OBSERVABLE (TR warm-up) |
| CISD-L11 | **PASS** | 2026-10-31 | H1 and H2 golden exact; H3 / H4 supporting (OHLC not recoverable), consistent; 0 human mismatch; no rule regression (`docs/CISD_FREEZE_REPORT.md` §2) |
| CISD-L12 | automated **PASS** · manual **PENDING** | 2026-10-31 | `tests/test_cisd_freeze.py`; manual procedure above |
