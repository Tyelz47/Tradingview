# IST · Displacement freeze report — v0.8.0-dev

**Status: FROZEN on 2026-11-02.**
* Annotated tag `DISPLACEMENT_BASELINE_v0.8.0-dev` on the freeze commit of branch `displacement/pine`. Not merged into `main`.
* DISP-L00, DISP-L10, DISP-L11 and DISP-L12 pass, all recorded from the user's results.
* This freezes the **displacement module** (DISPLACEMENT-R, single candle) only:
  * LRL and HTF FVG in the same file stay EXPERIMENTAL;
  * CISD stays frozen under `CISD_BASELINE_v0.7.1-dev`;
  * the Phase 1 and Phase 2 baselines are untouched.

## 1 · Identity

| Item | Value |
|---|---|
| Build | IST **v0.8.0-dev**. The label is kept: the frozen bytes are the bytes captured in TradingView |
| Source | `src/IST.pine`, SHA-256 `740ebcf68f5330ade022ec8a3336e2f6a308dce936d40e6fe913332e7c6c5862`, unchanged since commit `1b54759` (the build in the real capture, `build=v0.8.0-dev`) |
| Oracle | `validation/models/displacement.py`: `DisplacementEngine` is the definition; `DispPine` is Pine's formulation, transliterated and proven equal. SHA-256 `9be5f082c19b289b1df328fcd246482914aeeccb04a4df8fc1cd5b267ad03885` |
| Git tag | **`DISPLACEMENT_BASELINE_v0.8.0-dev`** (annotated; the convention of `PHASE1_BASELINE_v0.3.2`, `PHASE2_BASELINE_v0.4.4-dev`, `CISD_BASELINE_v0.7.1-dev`) |
| Read-only copy | `releases/v0.8.0-dev/` (see the next table) |
| Baselines | `PHASE1_BASELINE_v0.3.2`, `PHASE2_BASELINE_v0.4.4-dev` and `CISD_BASELINE_v0.7.1-dev` unchanged; the Phase 1 diff guard (ST-15) passes |
| Validation tooling | 1.18.0 |

**What `releases/v0.8.0-dev/` holds.**
* the source, the four displacement documents, the oracle;
* the golden dataset and its README;
* the real parity evidence, byte for byte;
* `SHA256SUMS.txt` (inside the folder: `sha256sum -c SHA256SUMS.txt`);
* `MANIFEST.txt` (tests, static checks and tooling, from the repository root).

**Rollback:** `git checkout DISPLACEMENT_BASELINE_v0.8.0-dev`, or paste `releases/v0.8.0-dev/src/IST.pine` into the Pine Editor.

## 2 · Evidence

### 2.1 DISP-L10: real TradingView parity (v0.8.0-dev)

The capture is `validation/parity/evidence/ist-v0.8.0-dev_mnq-1m-replay_capture-1000_2026-10-30.csv`:
* the user's `pine-logs-IST_43f18.csv`, copied byte for byte;
* SHA-256 `8b64c99a666354378e6670d06cad36e34ea44a7113b1d3b51d317ac20873a9b6`;
* MNQ (CME_MINI:MNQZ2026) 1m in Bar Replay, 2026-10-29 19:56 → 2026-10-30 13:51 New York, 1,000 bars + 76 warm-up.

**BOUNDED PINE-LOG BAR-BY-BAR PARITY: PASS. 75 MATCH · 0 DIFFERENCE · 12 NOT OBSERVABLE.**

| module | compared |
|---|---|
| **displacement** | **1,060 bar verdicts** (verdict, A, body / A, close position, FVG metadata), **22 DISPLACEMENT_CONFIRMED + 22 DISPLACEMENT_DROPPED_MEMORY** (all fields), **50 snapshot records** consistent; the 4 settings constants equal the approved ones |
| Phase 1 / 2 | 1,043 bars × 9 series, 947 events |
| LRL | 38 events, 144 boundaries, 1,980 candidate counts |
| HTF FVG | 126 candles, 118 events, 1,075 bar registries |
| CISD | 1,075 bar states, 170 events; the definition oracle gives 85 CISDs identical to Pine's |

The displacement NOT OBSERVABLE items are expected:
* the bars up to the snapshot (A needs the 14 true ranges before them);
* the candles of snapshot records older than the window; their own numbers and the rule are still checked.

Pinned by `tests/test_parity_v080_evidence.py`.

### 2.2 DISP-L11: human / golden validation — PASS

The dataset is `validation/golden/human/displacement/` (README there): **19 cases, 22 candles**.
* Every candle is copied exactly from the evidence captures, and a test proves it.
* The categories were written from the candle shape before the detector ran. The user confirmed DISP-L11.

| category | cases | DISPLACEMENT-R |
|---|---|---|
| A · clear displacement | **6** (A1–A3 ▲, A4–A6 ▼) | all 6 confirmed |
| B · clear non-displacement | **5** (B1, B2 large range / weak body; B3 close position 0.54; B4 not beyond the previous low; B5 a CISD without displacement) | none |
| C · borderline | **6** (body / A 1.483 / 1.507 / 1.509 / 1.482; close position 0.740 / 0.756) | as the approved thresholds say |
| SUPPORTING / INCONCLUSIVE | **2** (I1, I2) | none (approved exclusions) |

* **0 mismatch.** The same verdict from the oracle and `DispPine`, on the case window and on the full history.
* The real Pine log agrees on the 4 cases inside the v0.8.0-dev capture (A3, A6, B5, C1). The bearish mirror holds.
* Every special case is covered (CISD with / without displacement, FVG YES / NO, each failing condition alone), and each approved condition decides at least one case on its own.
* **I1 and I2: evidence for a possible future multi-bar module.**
  * I1 (NQ1! 2026-10-28 03:56–03:57): a two-candle push of about 4 × A, each candle with a large upper wick.
  * I2 (MNQ 2026-10-14 02:02–02:04): a three-candle staircase of about 3.3 × A.
  * Neither changes the frozen single-candle DISPLACEMENT-R.

Pinned by `tests/test_displacement_golden.py`.

### 2.3 DISP-L12: reload / determinism — PASS

**Manual (user, 2026-11-02).**
* Historical displacements were checked before and after (a) a page refresh and (b) removing and re-adding the indicator.
* The same timestamps kept side / verdict, A, body / A, close position, confirmation close and FVG metadata. A borderline non-displacement stayed verdict 0.

**Automated.**
* Identical history gives identical records and events; a prefix equals the full run's past (no lookahead), so the module is stateless and reload-proof after bar 14.
* Detection reads no display, debug, capture or alert value (ST-01, ST-22, mutations).

### 2.4 DISP-L00 — PASS

v0.8.0-dev compiled and ran in TradingView (user).

### 2.5 Automated validation (FULL, final run before the freeze)

**FULL: PASS**, exit 0, 684.9 s, **1052 passed, 1 skipped** (the parity section's long-standing skip):
* static 22/22 (ST-21 history scope, ST-22 DISPLACEMENT-R lines);
* displacement 106/106 (oracle, Pine formulation, mutations), displacement study 24/24;
* golden 110/110 (102 displacement human golden tests);
* parity 142/143, including the real v0.8.0-dev evidence (0 DIFFERENCE) and the observed-capture test on it;
* invariant detectors 76/76, property 37/37, long walks 19/19;
* CISD 167/167 (frozen tests unchanged), LRL 85/85, HTF 46/46;
* Phase 1 / 2 sections unchanged.

## 3 · Frozen definition (exact text: `docs/DISPLACEMENT.md`, DEF-DISP1 … DISP9)

The bullish displacement is defined below; the bearish one is the exact mirror. EPS = 0.01 tick. One closed candle t:

| rule | bullish | bearish |
|---|---|---|
| direction | `close > open + EPS` (a doji never) | `close < open − EPS` |
| A | the TR average (`ta.tr(true)`, SMA) of the **14 completed bars before** the candle; none while warming up or when A ≤ 0 | same |
| body | `close − open ≥ 1.5 × A` | `open − close ≥ 1.5 × A` |
| close position | `(close − low) / range ≥ 0.75`, range > 0 | `(high − close) / range ≥ 0.75` |
| beyond the previous candle | `close > previous high + EPS` | `close < previous low − EPS` |

* **Confirmed at the close of the same candle.** No later confirmation, no state machine, no lifecycle.
* **FVG is metadata only.** UNKNOWN at confirmation, then YES / NO once on the next candle: the candle is candle 2 of a Phase 1 DEF-A1 gap.
* **Not base requirements:** CISD, liquidity sweep, structure (BOS / MSS), LRL, FVG, IFVG, DOL, session.
* **Memory:** 50 records; the oldest goes first.
* **Events:** `DISPLACEMENT_CONFIRMED`, `DISPLACEMENT_DROPPED_MEMORY`.
* **Pine.**
  * Its own TR series and every history read at global scope (ST-21, ST-22).
  * One input (`dispOn`); constants k 1.5, close position 0.75, 14 bars, memory 50.
  * No renderer and no alert. Debug shows values in the Data Window only.
* **No multi-bar displacement in this baseline.**

## 4 · What the freeze guarantees

* Displacement detection, records, the FVG metadata and the events are fixed to the text above and the oracle. Any change is a new, approved version with new evidence.
* ST-22 pins every DISPLACEMENT-R line of the Pine source, and ST-21 guards against history reads inside functions.
* The 25 Pine mutations, the 15 parity corruption kinds and the 19 human golden cases run in every validation.

## 5 · Open items (not blocking the freeze)

* DISP-L01 … L05 were not recorded one by one; L00, L10 and L12 cover their logic.
* The renderer, the alerts and the final visual design are deferred (M11).
* Multi-bar displacement (M5): a possible future, separate module, with I1 / I2 as its first evidence.
* Context / quality classes (CISD, sweep, FVG, DOL, structure) and IFVG are future modules.

## 6 · Known limitations

* Chart timeframe only.
* No predictive claim: shuffled candles and random walks produce such candles too (`docs/STUDY_DISPLACEMENT.md` §D). DISPLACEMENT-R describes one candle's delivery against its neighbourhood.
* The first 14 loaded bars cannot have a displacement (A warm-up).
* Single candle only: a fast multi-candle leg without one qualifying candle is not detected (I1, I2; 34–58 % of fast multi-bar moves in the study).
* An exact tie at a threshold could differ by one float ulp between Pine's `ta.sma` and Python. None was seen in real data; parity would show it as a DIFFERENCE.
* No drawing or alert yet, so on the chart it is visible only with Debug mode (Data Window, Pine Logs).
* The golden classifications were written by the reviewer from the candle shape and confirmed by the user. They are not an independent labelled corpus.
