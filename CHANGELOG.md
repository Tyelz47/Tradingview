# Changelog

## CONTEXT-01 — DOL / directional context research · IST v0.9.1-dev unchanged · validation 1.24.0 (2026-11-03, branch `context/research`) — no indicator change

**User (2026-11-03):** research and specification only, for a future DOL / DIRECTIONAL CONTEXT layer above the detection modules.
* Up to PRIMARY DOL; no Pine, renderer, styling, alerts, score, entry model, SMT, OB / breaker / OTE.
* No frozen module changes. Facts are not bias. No arbitrary score or voting.
* FEATURES_AT_T apart from OUTCOME_AFTER_T.

**CHANGES**
* `docs/context/` (new, proposal):
  * `DOL_RESEARCH.md`: DEF-DOL1…DOL8, liquidity target versus PD array, states, PRIMARY / NEXT / ALTERNATE / path, an eligibility matrix and the DOL-P1 candidate (precedence, no score), MIXED / UNKNOWN, baselines B0…B4, outcome labels, the conceptual schema, the 12 answers, decisions D-CX1…D-CX12;
  * `TARGET_UNIVERSE.md`, `DIRECTIONAL_CONTEXT_RESEARCH.md`, `RESEARCH_CASES.md`, `CONTEXT_ROADMAP.md` (the exact CONTEXT-02 proposal).
* `validation/studies/context.py` (new, analysis only):
  * four real 1m segments from the evidence;
  * PDH … PWL from Pine's own HTF snapshot / HTFBAR / LEVEL_SET;
  * target status with the observation-coverage rule;
  * 13 pre-registered decision points, with features from the cut segment;
  * the baselines, the fact → first-external-target tables and the case categories.
* `validation/tests/test_context_study.py` (new, report section `research.context`): no lookahead (the future is replaced), the DEF-L4 status rule and UNVERIFIED, the outcome labels, the quoted numbers.
* `validation/validation_agent.py` (one report section), `validation/conftest.py` (one marker), `validation/__init__.py` (1.24.0).

**RESULT (descriptive; nothing tuned, no predictive claim)**
* 4,979 bars ≈ 83 h, NQ family only; 13 decision points.
* B1 (the nearest target of any class) was reached first 9 / 12 times against a driftless reference of 10.0. Proximity adds nothing beyond itself.
* CISD, IFVG and displacement each sit at or below their reference for the next external target; 1–12 distinct outcomes per fact.
* The 1m and 15m CISD states agree on 49–63% of bars.
* External takes are rare: 5 sweeps and 11 breaks in 83 h.
* Prerequisites flagged: G-V1…G-V5 (the level source) pending; a dataset (NQ and ES, ≥ 60 complete days each).

**RISKS:** none for the indicator: `src/IST.pine` and every frozen file are unchanged. The study is descriptive on a small sample. Its numbers must not be read as evidence for a rule.

**TEST:**
* FULL (mode full, before the README / CHANGELOG entries): **PASS**, exit 0, 1169.2 s, **1461 passed, 1 skipped** (the absent manual `pine_observed.json`, not a functional failure): static 23/23; golden 290/290; parity 167/168; invariant detectors 85/85; property 44/44; IFVG 172, CISD 167, displacement 106, LRL 85, HTF 46; research studies LRL 34, CISD 29, displacement 24, IFVG 8, **context 4/4 (new)**; Phase 1 / 2 unchanged.
* `src/IST.pine` SHA-256 `553248e7…9b91` (= `IFVG_BASELINE_v0.9.1-dev`).
* The release SHA256SUMS: v0.3.2 5/5, v0.4.4-dev 9/9, v0.7.1-dev 10/10, v0.8.0-dev 30/30, v0.9.1-dev 36/36.
* The v0.9.1-dev MANIFEST: 51/51.
* `git diff IFVG_BASELINE_v0.9.1-dev` is empty for `src/`, `releases/`, `validation/models/`, `validation/parity/`, `validation/golden/`.

## IFVG FROZEN — IFVG_BASELINE_v0.9.1-dev · IST v0.9.1-dev unchanged · validation 1.23.0 (2026-11-03, branch `ifvg/pine`) — no indicator change

**User (2026-11-03):** IFVG-L12 manual validation PASS.
* The four MNQ1! 1m cases of 2026-11-02 (A3 bearish, B2 bullish, B4 lifecycle, C2 wick-only rejection), Debug ON, kept their IFVG / FVG Pine Logs identities, inversions and lifecycles on the normal chart, after a page refresh, and after removing and re-adding the indicator.
* The documented exceptions are accepted, not failures: IFVG_DROPPED_MEMORY timing, "inversions so far", CE / full as facts, the first ~16 loaded bars.
* IFVG-L00, L10, L11, L12 PASS; IFVG-R approved for freeze. Freeze the implementation exactly as validated, with a documentation-only commit and the annotated tag on it.

**RESULT**
* Final statuses: **IFVG-L00 PASS · IFVG-L10 PASS · IFVG-L11 PASS · IFVG-L12 PASS** (automated and manual; `docs/TESTS_IFVG.md`).
* **Frozen: IFVG-R exactly as approved** (`docs/IFVG_FREEZE_REPORT.md` §3):
  * Phase-1-qualified FVGs only;
  * the strict DEF-A5 close beyond the far edge, opposite side; a wick or a close at the boundary is no inversion;
  * inherited geometry;
  * confirmed at the inversion close, lifecycle from the next bar;
  * wick facts FIRST_TOUCH / CE / FULL_TRAVERSAL, INVALIDATED only on a strict close beyond the far edge;
  * an observer of Phase 1, one IFVG per original FVG;
  * memory 50 per side as a retention target, ACTIVE never evicted;
  * no context requirement.
* **Accepted limitations, frozen** (§6):
  * the loaded-history boundary (about 16 bars observed, not a rule);
  * the Phase 1 DEF-A6 dependency;
  * IFVG_DROPPED_MEMORY timing;
  * no hard memory bound (to monitor);
  * CE / full as facts, no renderer / alerts;
  * chart timeframe only, no predictive claim.
* **Freeze commit (documentation and release metadata only):**
  * `docs/IFVG_FREEZE_REPORT.md`, `docs/IFVG.md`, `docs/TESTS_IFVG.md` and `docs/STUDY_IFVG.md` marked FROZEN; README; this entry;
  * `releases/v0.9.1-dev/`: the same documents, `CHANGELOG.md`, `README.md` and `README.txt` refreshed, `SHA256SUMS.txt` regenerated, read-only again; `MANIFEST.txt` unchanged (no file in it changed).
* Annotated tag `IFVG_BASELINE_v0.9.1-dev` on this commit, so the tagged tree records the manual IFVG-L12 PASS.

**TEST:**
* FULL on the freeze tree: **PASS**, exit 0, 683.0 s, **1457 passed, 1 skipped** (the absent manual `pine_observed.json`, not a functional failure): static 23/23; IFVG 172/172; golden 290/290; parity 167/168 (the real v0.9.1-dev evidence 0 DIFFERENCE); invariant detectors 85/85; property 44/44; CISD 167, displacement 106, LRL 85, HTF 46; Phase 1 / 2 unchanged.
* `src/IST.pine` unchanged since `0d49bc3` (SHA-256 `553248e7…9b91`). The oracle, the golden dataset and the evidence are unchanged since `db607ae`. Untouched: `PHASE1_BASELINE_v0.3.2`, `PHASE2_BASELINE_v0.4.4-dev`, `CISD_BASELINE_v0.7.1-dev`, `DISPLACEMENT_BASELINE_v0.8.0-dev` and the earlier releases.

## IFVG-L11 PASS · IFVG-L12 automated determinism / reload PASS · IFVG freeze prepared — IST v0.9.1-dev unchanged · validation 1.23.0 (2026-11-03, branch `ifvg/pine`) — no indicator change

**User (2026-11-03):** the manual IFVG-L11 sanity review passed: mark IFVG-L11 = PASS (IFVG-L00 and IFVG-L10 PASS, IFVG-L12 pending).
* Run the final IFVG-L12 determinism / reload validation and prepare the freeze package.
* Do not create the baseline tag before the user's manual IFVG-L12 PASS.
* Do not change IFVG-R or any frozen module; no HTF IFVG, DOL / context engine, quality scoring, renderer / styling or alerts.

**RESULT**
* **IFVG-L11 PASS** recorded (`docs/TESTS_IFVG.md`).
* **IFVG-L12 automated: PASS.** `tests/test_ifvg_freeze.py`, 46 tests, each requirement by name (the table is in its docstring). The data: the real v0.9.1-dev candles, the three research segments, a 5,000-bar walk with a side over 50 ACTIVE, and the six real captures.
  1. **Determinism.** Two fresh runs are identical on every bar: shadows, every record field, memory, the bar's events. The Pine-Log text of the IFVG event stream matches byte for byte, and the oracle matches per bar.
  2. **No repaint.** A bar only adds its inversions, stamps facts / ends of ACTIVE IFVGs, or drops INVALIDATED records. A prefix equals the full run's past, and no IFVG of the prefix changes.
  3. **A later first loaded bar** (shifts 1, 17, 100, 400 on six real captures) keeps every IFVG of an FVG confirmed ≥ 16 bars after it: every field, its events, the ACTIVE set. Only the timing of IFVG_DROPPED_MEMORY follows the older records held.
  4. **Independence.** Every module and display setting on / off gives the same IFVGs. The Pine engine reads only `ifvgOn`, `IFVG_MEM`, its event codes, its book and the Phase 1 FVG lists, inside `if engineTick`.
  5. **Memory.** Two reloads from the real Pine state (51–66 ACTIVE bearish IFVGs for 655 bars) give the same ACTIVE set on every bar, equal to Pine's counts and to Pine's own final set; no drop of an ACTIVE record.
  6. **Same-bar order.** In the real Pine log, every bar follows Phase 1 → facts / ends → memory → inversion → memory, and its IFVG lines are the oracle's, in order (654 events, 332 bars). A real example is pinned (05:57). Memory 1 / 2 / 50 gives the same order.
  7. **Phase 1** is identical with the IFVG on and off, on every bar.
* **Real capture regression:** the v0.9.1-dev evidence still gives 0 DIFFERENCE, with every count pinned; the CSV is unchanged.
* **Tooling.** `parity/capture.py`: `restore_ifvg` was extracted from `_compare_ifvg` (the same comparison) so the L12 memory test can restore the real snapshot.
* **Freeze package** (tag `IFVG_BASELINE_v0.9.1-dev` **not created**):
  * `docs/IFVG_FREEZE_REPORT.md`;
  * `docs/TESTS_IFVG.md` with the manual IFVG-L12 procedure (A3 bearish, B2 bullish, B4 lifecycle, C2 wick-only rejection; refresh, remove / re-add);
  * the status of `docs/IFVG.md` and `docs/STUDY_IFVG.md`;
  * `releases/v0.9.1-dev/`, read-only: source, IFVG docs, oracle, golden dataset, real evidence byte for byte, SHA256SUMS, MANIFEST, README.txt.
* **Known limitation documented.** Phase 1's frozen DEF-A6 release of an OPEN FVG follows the history start. Four such releases are in the real v0.9.1-dev log, all of FVGs 4–5 days old and about 1,500 points away, and none on the six replayed captures.

**PHASE 1 / 2, LRL, HTF FVG, CISD, DISPLACEMENT, IFVG IMPACT:** none. `src/IST.pine` is unchanged (v0.9.1-dev, SHA-256 `553248e7…`), and so is the oracle.

**TEST:**
* FULL: PASS, exit 0, 739.1 s, **1457 passed, 1 skipped**: static 23/23; IFVG 172/172 (+46 L12); golden 290/290; parity 167/168; invariant detectors 85/85; property 44/44; CISD 167, displacement 106, LRL 85 and HTF 46, all unchanged.
* TradingView: IFVG-L00, L10 and L11 PASS (user). IFVG-L12: automated part PASS; the manual reload check is the user's.

## IFVG-L10 PASS · IFVG-L11 human / golden validation — IST v0.9.1-dev unchanged · validation 1.22.0 (2026-11-03, branch `ifvg/pine`) — no indicator change

**User (2026-11-03):** IFVG-L10 real Pine ↔ oracle parity PASSED on IST v0.9.1-dev:
* 82 MATCH · 0 DIFFERENCE · 16 NOT OBSERVABLE;
* IFVG 1,059 bars, 654 events, 100 snapshot records;
* every earlier module still at 0 real differences.

Mark IFVG-L10 = PASS and run IFVG-L11: human / golden validation of the fixed IFVG-R, with no rule tuning. Do not change IFVG-R or any frozen module; no HTF IFVG, scoring or styling; do not freeze yet.

**RESULT**
* **IFVG-L10 recorded.** The user's capture (`pine-logs-IST_faf9f.csv`, MNQ1! live, 2026-11-02 04:16 → 23:11) is kept byte for byte as `parity/evidence/ist-v0.9.1-dev_mnq1-1m_capture-1000_2026-11-02.csv`, with its SHA-256 and `CAPTURE_V091`.
  * `tests/test_parity_v091_evidence.py` pins its counts.
  * It checks every one of the 153 IFVG drops in the log: 121 INVALIDATED earlier in the log, 31 in the snapshot, 1 before the snapshot (NOT OBSERVABLE), 0 ACTIVE.
  * The bearish side held 51–66 ACTIVE IFVGs for 655 bars, all kept: the revised DEF-IFVG8 at work in real Pine.
  * The observed-capture test now runs on it (0 DIFFERENCE) instead of skipping.
* **IFVG-L11 golden package** (`validation/golden/human/ifvg/`, README there).
  * **22 real MNQ cases:** 20 inside the v0.9.1-dev capture, 2 from v0.8.0-dev (another day and contract).
    * 7 clear bearish IFVGs, 7 clear bullish;
    * 3 wick-only rejections;
    * 3 closes exactly on the edge;
    * 2 one-tick borderline inversions.
    * The special cases A–Q are each covered by real candles and derived, not labelled.
  * **R1:** case R is mechanical (synthetic). The five captures hold no real instance with any Phase 1 memory 1–15, and the README explains why.
  * **MEM1:** the memory golden on the real log.
  * **H1:** re-audited as SUPPORTING, from its pixel-digitised candles; V1 SUPPORTING; V2 INCONCLUSIVE. No conflict.
* `tests/test_ifvg_golden.py`, per case:
  * the candles are the evidence bars;
  * IFVG-R by hand gives every recorded number;
  * the oracle (invariants on) and `IfvgPine` give the verdict on the window and the whole capture;
  * the real Pine log agrees: FVG_INVALIDATED and IFVG_INVERTED of the same FVG id on the same bar, the audit geometry, every later IFVG event and CE / full fact;
  * the context is the Pine log's and never changes the verdict;
  * the mirror;
  * then the coverage, R1, MEM1 and H1.
* **Finding (diagnostics only, no bug).** An IFVG that ends while its side is over 50 is dropped on that bar, so the BAR line's IX no longer lists its last-bar fact. The parity oracle does the same (0 DIFFERENCE). The golden test checks such a fact through the drop, which comes only on or after the end.

**PHASE 1 / 2, LRL, HTF FVG, CISD, DISPLACEMENT, IFVG IMPACT:** none. `src/IST.pine` is unchanged (v0.9.1-dev), and so is the oracle.

**TEST:**
* FULL: **PASS**, exit 0, 582.0 s, **1411 passed, 1 skipped** (the manual-parity JSON, not present; the observed-capture test now runs on the v0.9.1-dev capture: 0 DIFFERENCE):
  * static 23/23 (ST-21, ST-23);
  * golden 290/290 (+180 IFVG-L11), IFVG 126/126, IFVG study 8/8;
  * parity 167/168, property 44/44, long walks 22/22, invariant detectors 85/85;
  * CISD 167/167, displacement 106/106, LRL 85/85, HTF 46/46, regression 5/5;
  * Phase 1 / 2 unchanged.
* TradingView: IFVG-L10 PASS (user). IFVG-L11: automated part PASS; the manual sanity cases are the user's. IFVG-L12 (reload) pending.

## v0.9.1-dev — IFVG memory never drops an ACTIVE IFVG (DEF-IFVG8 revised) · validation 1.21.0 (2026-11-02, branch `ifvg/pine`) — EXPERIMENTAL, not frozen

**User (2026-11-02):** the v0.9.0-dev implementation report is approved except its memory fallback (all 50 records of a side ACTIVE → the oldest ACTIVE one dropped), which is NOT approved: an ACTIVE IFVG is logical market state and must never disappear to enforce a storage cap. `IFVG_MEM = 50` stays as the retention target per side. Correct it before IFVG-L00; v0.9.0-dev (never compiled) is not the build to test.

**CHANGE (src/IST.pine, IFVG memory only)**
* **`compactIfvg`, the one memory routine:**
  * while the side holds more than `IFVG_MEM` records, scan from the oldest (inversion order);
  * skip an ACTIVE record; remove an INVALIDATED one, with `IFVG_DROPPED_MEMORY`;
  * stop at the cap, or at the end of the side.
* **When it runs:**
  * in ENGINE RUN, after the active IFVGs advanced (bullish side, then bearish), so an end can let an over-full side compact;
  * in `invertIfvg`, after each inversion's record and event.
* The v0.9.0-dev victim scan (else the oldest ACTIVE one) is removed. `IFVG_DROPPED_MEMORY` now exists only for INVALIDATED records.
* **Per-bar order:** Phase 1 FVG block → IFVG facts and ends (bullish IFVGs, then bearish) → memory (bullish side, then bearish) → observer (new shadows; each inversion: record → `IFVG_INVERTED` → memory of its side).
* Build v0.9.1-dev. No other line changes: the inversion trigger, eligibility, shadows, geometry, thresholds, same-bar order and identity are unchanged. Phase 1, CISD, displacement, LRL and HTF are unchanged.

**WHY.** The 50 is a retention target, not permission to destroy active logical state.
* 52 ACTIVE → all 52 kept (temporary overflow).
* One ends → `IFVG_INVALIDATED`, then memory drops the oldest INVALIDATED record.
* Every ACTIVE IFVG's future retest, CE, full and end stay observable.

**PHASE 1 / 2, LRL, HTF FVG, CISD, DISPLACEMENT IMPACT:** none. Against `DISPLACEMENT_BASELINE_v0.8.0-dev` the diff still only adds lines, except the four build lines.

**REPAINT IMPACT:** none. Memory changes only which INVALIDATED records are kept.

**Validation 1.21.0**
* **Oracle and `IfvgPine`:** `_compact`, the same routine at the same points; Pine = oracle, record for record and event for event.
* **INV-IFVG-07** (revised): ≤ memory per side unless every record of the side is ACTIVE; inversion order; the oldest INVALIDATED records leave first, and only while the side holds more than memory.
* **INV-IFVG-09** (new): every dropped record was INVALIDATED just before the drop, and the ACTIVE identities after a bar = those before − the bar's ends + the bar's inversions. 83 invariants.
* **ST-23:** 21 rules (the memory routine and its three call sites pinned); 34 mutations, among them the v0.9.0-dev fallback.
* **`tests/test_ifvg_memory.py`** (the requested cases 1–10, both sides, under the invariant monitor, Pine = oracle):
  * 50 + 1 ACTIVE → 51 kept;
  * 55 ACTIVE kept;
  * the routine on 51 ACTIVE + 1 old INVALIDATED;
  * an old INVALIDATED record leaves, 51 ACTIVE remain;
  * an over-full ACTIVE side compacts when one ends;
  * the older INVALIDATED record goes first (also for two ended on one bar);
  * lifecycles identical with or without overflow;
  * replay;
  * 5,000-bar walks lose no ACTIVE IFVG.
* **Property:** with any memory, the ACTIVE IFVGs and every IFVG event but the drops equal those of an unlimited memory.
* **Random walks (20,000 bars, seeds 1–3, memory 50):**
  * 0 ACTIVE drops, where v0.9.0-dev had 95–215;
  * peak side 93 / 248 / 180;
  * ACTIVE IFVGs and lifecycles = an unlimited memory.
* **Real data unchanged:** 566 inversions; (inverted, dropped) per segment (266, 166), (140, 40), (160, 60).
* **Docs:** `docs/IFVG.md` DEF-IFVG8 and §6 / §7; `docs/TESTS_IFVG.md` (S-IFVG-12, v0.9.1-dev procedure).

**TEST:**
* FULL: **PASS**, exit 0, 722.4 s, **1227 passed, 2 skipped** (the long-standing parity skip, and the observed-capture test: the latest real capture was written by v0.8.0-dev):
  * static 23/23 (ST-21, ST-23);
  * IFVG 126/126 (oracle 26, Pine 79, memory 21), IFVG study 8/8;
  * parity 163/165, property 44/44, long walks 22/22, invariant detectors 85/85;
  * CISD 167/167, displacement 106/106, LRL 85/85, HTF 46/46, golden 110/110, regression 5/5;
  * Phase 1 / 2 unchanged.
* TradingView: IFVG-L00 PENDING, on v0.9.1-dev. IFVG-L10 needs a new real capture with v0.9.1-dev.

## v0.9.0-dev — IFVG in Pine (IFVG-R) · validation 1.20.0 (2026-11-02, branch `ifvg/pine`) — EXPERIMENTAL, not frozen

**User (2026-11-02):** the IFVG research / oracle phase is approved, with two clarifications.
* **Eligibility:** an FVG is IFVG-eligible if it is in the Phase 1 logical FVG universe immediately before its DEF-A5 invalidation. Invalidated and released on the same bar: eligible. Released earlier without an inversion: never. Visibility is irrelevant.
* **One close rule:** the exact Phase 1 DEF-A5 semantics, no second close-through rule.

Implement IFVG-R in Pine as an observer after the frozen Phase 1 FVG block. No frozen baseline, LRL or HTF semantics change; no HTF IFVG, final styling, alerts or quality scoring.

**CHANGE (src/IST.pine)**
* **Constants:** `IFVG_MEM 50`; events 36…39 = `IFVG_INVERTED` / `IFVG_FIRST_TOUCH` / `IFVG_INVALIDATED` / `IFVG_DROPPED_MEMORY`. One [calc] input: `ifvgOn` (group IFVG, ON).
* **Types:**
  * `Ifvg`: identity and geometry copied from the original FVG; inversion bar / time / close; `pre`; fact bars and times; end bar / time / close.
  * `IfvgBook`: `shadows` (references to Phase 1 `Fvg` records), `bull`, `bear`, counters.
* **L3:**
  * `advanceIfvg`: wick facts (retest at the near edge, CE, full at the far edge), then a strict close beyond the far edge = INVALIDATED;
  * `invertIfvg`: the record, `IFVG_INVERTED`, then memory (the oldest INVALIDATED of the side first, else the oldest active);
  * `observeIfvg`: the Phase 1 FVG created on this bar joins the shadows. In creation order, a shadow whose Phase 1 `invBar` is this bar inverts; one that Phase 1 released while open (its own `fvgDropNow`) leaves.
* **ENGINE RUN:** at bar close, after the Phase 1 FVG block (milestones, creation, release) and before displacement: advance, then observe. The Phase 1 block is not modified: against `DISPLACEMENT_BASELINE_v0.8.0-dev` the diff only adds lines, except the four build lines (header, `IST_BUILD`, CAPTURE, BAR).
* **No renderer and no alert:** `EV_IFVG_INVERTED => false`. Debug: four Data-Window-only values (`dbg · IFVG …`). The 52-row debug table is unchanged.
* **Parity capture:**
  * CAPTURE `ifvg / ifvgmem`;
  * after captured bar `fvglen + 2`: `IFVGSTATE` (counters, shadows), the Phase 1 memory as `FVGREC`, the IFVGs as `IFVGREC`;
  * per bar `IS` (shadows count : Σ id) / `IA` (active ▲ : ▼) / `IX` (CE / full facts).
  * Existing capture output is unchanged.

**WHY.** The approved IFVG-R in IST, as an observer: the inversion is Phase 1's own DEF-A5 bar, so there is exactly one close-through rule, and the parent stays INVALIDATED in Phase 1.

**PHASE 1 / 2, LRL, HTF FVG, CISD, DISPLACEMENT IMPACT:** none. ST-15…ST-22 pass unchanged, and every frozen CISD and displacement test passes unchanged.

**REPAINT IMPACT:** none. Decided at the bar close from that bar and the frozen Phase 1 state. Reload behaviour is Phase 1's (an IFVG exists iff its parent exists).

**Validation 1.20.0**
* `IfvgPine` (`validation/models/ifvg.py`, Pine's formulation, transliterated) = the oracle. The oracle's logic is unchanged; the two clarifications were already its behaviour (documentation only).
* ST-23 (22 rules, 1 constant, 4 orders; the observer never writes Phase 1; no history in the engine). ST-08 now allows IFVG; `ifvgOn` is a [calc] input; `ORACLE_ONLY` is empty (ST-14 exact).
* INV-IFVG-08: the registry of FVGs that may still invert = the open Phase 1 FVGs after every bar (no longer retention, none missing), with a negative test.
* `tests/test_ifvg_pine.py`: the approval's cases 1–35 (14 cases × 2 sides, geometry and identity, ordering, real data 652 / 566 / 272 / 294 / median 9, memory 50 per side and the fallback on walks, determinism, module and view independence, the additive diff, ST-21 / ST-23, 29 mutations).
* `tests/test_parity_ifvg.py`: faithful captures exact; 17 corruption kinds detected.
* `fuzz`: Pine formulation = oracle.
* `parity/capture.py _compare_ifvg`; `manual.py` reads `IFVG_*` lines.
* **Docs:**
  * `docs/IFVG.md`: APPROVED, §6 the clarifications, §7 Pine and capture;
  * `docs/TESTS_IFVG.md`: S-IFVG, IFVG-L00…L12.

**OPEN FOR REVIEW (resolved in v0.9.1-dev: not approved, replaced).** DEF-IFVG8's fallback: when all 50 IFVGs of a side are active, the oldest ACTIVE one is dropped (the approved text, the DEF-A6 mirror). It never happens on the real data. It happens on 20,000-bar random walks with gaps (about 95 to 215 drops per walk).

**TEST:**
* FULL: **PASS**, exit 0, 627.3 s, **1201 passed, 2 skipped** (the long-standing parity skip, and the observed-capture test: the latest real capture was written by v0.8.0-dev):
  * static 23/23 (ST-21, ST-23);
  * IFVG 102/102 (oracle 26 + Pine 76), IFVG study 8/8;
  * parity 163/165 (+22 IFVG parity), property 43/43, long walks 22/22, invariant detectors 84/84;
  * CISD 167/167, displacement 106/106, LRL 85/85, HTF 46/46, golden 110/110, regression 5/5;
  * Phase 1 / 2 unchanged.
* TradingView: IFVG-L00 PENDING. A new real Pine Logs capture with v0.9.0-dev is needed for IFVG-L10 (the existing captures were written by v0.8.0-dev and earlier and carry no IFVG lines).

## IFVG research + oracle — IFVG-R proposed · validation 1.19.0 (2026-11-02, branch `research/ifvg`) — no indicator change

**User (2026-11-02):** start the research / specification of IFVG (inversion fair value gap) as an independent module. Audit `docs/IFVG_REQUIREMENTS.md`, compare inversion triggers on real NQ, recommend one definition, and implement it in the Python oracle. No Pine; nothing frozen changes.

**RESULT**
* **Audit (`docs/STUDY_IFVG.md` §A).** The requirements note holds. Its key observation is decisive: Phase 1's DEF-A5 invalidation is exactly a strict close beyond the far edge. One correction: the observer copies the parent on its confirmation bar, because the FVG engine can release a just-invalidated record on that bar.
* **Five triggers on the 652 real Phase 1 FVGs** (3,791 1m bars):

| trigger | inverted | after the Phase 1 invalidation |
|---|---|---|
| IF1 wick-through | 91 % | 0 % |
| **IF2 close-through** | **87 %** | **identical to DEF-A5** |
| IF3 + displacement | 67 % | 76 % |
| IF4 after a full fill | 86 % | 46 % |
| IF5 + CISD context | 84 % | 43 % |

* **Facts.** Inversion candles are DISPLACEMENT-R 18 % of the time; a same-side CISD is within ±5 bars in 56 %; 41 % of CISDs have no inversion near them. After inversion: retest within 10 bars 82 %, and a close beyond the far edge within 10 bars 52 %. Descriptive only.
* **H1 (supporting).** On its digitised candles, IF2 inverts the drop's bearish FVG 4 bars before the CISD, as in the image.
* **IFVG-R** (`docs/IFVG.md`, DEF-IFVG1…9, PROPOSED):
  * the parent's frozen DEF-A5 invalidation, at the bar close;
  * the opposite side, the parent's exact geometry, identity = the parent's id + side;
  * facts retest / CE / full, from the next bar;
  * INVALIDATED on a strict close beyond the far edge; no second inversion;
  * memory 50 per side;
  * events INVERTED / FIRST_TOUCH / INVALIDATED / DROPPED_MEMORY.
  * An observer: Phase 1 is never written, and the parent stays INVALIDATED there. CISD, displacement and liquidity are context, not requirements.

**Validation 1.19.0**
* `validation/studies/ifvg.py` + `tests/test_ifvg_study.py`.
* The oracle `validation/models/ifvg.py`: opt-in module `ifvg` (needs `fvg`), `IfvgSettings(memory=50)`. Its events are ORACLE_ONLY (ST-14 excludes them until Pine). It equals the study's IF2 exactly (566 inversions, every lifecycle fact).
* `tests/test_ifvg.py` (26), `fuzz/test_ifvg_properties.py`, INV-IFVG-01…07 with negative tests (81 invariants).
* Report sections `ifvg` and `research.ifvg`; `--phase ifvg`.

**TEST:**
* FULL: **PASS**, exit 0, 601.6 s, **1101 passed, 1 skipped** (the long-standing parity skip):
  * static 22/22;
  * IFVG 26/26, IFVG study 8/8, property 42/42 (+5), long walks 22/22 (+3), invariant detectors 83/83 (+7);
  * displacement 106/106, CISD 167/167, LRL 85/85, HTF 46/46, golden 110/110, parity 142/143;
  * Phase 1 / 2 unchanged.
* `src/IST.pine` unchanged (v0.8.0-dev, SHA-256 740ebcf6…5862). Unchanged: every frozen baseline and release, LRL, HTF FVG and the regression baseline.

## Displacement FROZEN — DISPLACEMENT_BASELINE_v0.8.0-dev · IST v0.8.0-dev unchanged · validation 1.18.0 (2026-11-02, branch `displacement/pine`) — no indicator change

**User (2026-11-02):** DISP-L12 reload PASS: the same timestamps kept side / verdict, A, body / A, close position, confirmation close and FVG metadata after a page refresh and after removing and re-adding the indicator, and a borderline non-displacement stayed 0. DISP-L00, L10, L11, L12 PASS. Freeze the approved single-candle DISPLACEMENT-R; nothing else changes.

**RESULT**
* Final statuses: **DISP-L00 PASS · DISP-L10 PASS · DISP-L11 PASS · DISP-L12 PASS** (`docs/TESTS_DISPLACEMENT.md`).
* Real parity (DISP-L10): 1,060 displacement bar comparisons, 22 DISPLACEMENT_CONFIRMED, 22 DISPLACEMENT_DROPPED_MEMORY, 50 snapshot records, 0 DIFFERENCE.
* Golden (DISP-L11): 19 cases, 22 candles. 6 clear, 5 rejected, 6 borderline, 2 inconclusive.
  * I1 / I2 are documented as evidence for a possible future multi-bar module.
  * They do not change the frozen single-candle DISPLACEMENT-R.
* **Freeze package:**
  * `docs/DISPLACEMENT_FREEZE_REPORT.md`;
  * `docs/DISPLACEMENT.md`, `docs/TESTS_DISPLACEMENT.md` and `docs/STUDY_DISPLACEMENT.md`, now marked FROZEN;
  * `releases/v0.8.0-dev/`, read-only: source, docs, oracle, golden dataset + README, the real parity evidence byte for byte, `SHA256SUMS.txt`, `MANIFEST.txt`, `README.txt`.
* Annotated tag `DISPLACEMENT_BASELINE_v0.8.0-dev` on the freeze commit.

**TEST:**
* FULL: **PASS**, exit 0, 684.9 s, **1052 passed, 1 skipped** (the long-standing parity skip):
  * static 22/22 (ST-21, ST-22);
  * displacement 106/106, displacement study 24/24, golden 110/110;
  * parity 142/143 (the real v0.8.0-dev evidence 0 DIFFERENCE);
  * CISD 167/167, LRL 85/85, HTF 46/46;
  * Phase 1 / 2 unchanged.
* `src/IST.pine` unchanged since `1b54759` (SHA-256 740ebcf6…5862). Untouched: CISD-R and `CISD_BASELINE_v0.7.1-dev`, LRL, HTF FVG, Phase 1 / 2 and the earlier releases.

## DISP-L10 PASS · DISP-L11 human goldens PASS — IST v0.8.0-dev unchanged · validation 1.18.0 (2026-11-01, branch `displacement/pine`) — no indicator change

**User (2026-11-01):** the real IST v0.8.0-dev capture passes with 0 DIFFERENCE (DISP-L10), the displacement section included (1,060 bar verdicts, 50 snapshot records, 22 + 22 events). Next: DISP-L11, human / golden validation of the approved DISPLACEMENT-R, with no threshold change and no tuning.

**RESULT**
* **DISP-L10 PASS.** The user's `pine-logs-IST_43f18.csv` is kept byte for byte as `parity/evidence/ist-v0.8.0-dev_mnq-1m-replay_capture-1000_2026-10-30.csv` (SHA-256 `8b64c99a…a9b6`). Its counts are pinned in `tests/test_parity_v080_evidence.py`, and the observed-capture test runs on it again and passes.
* **DISP-L11 PASS.** `validation/golden/human/displacement/` holds 19 cases (22 candles) of real NQ1! / MNQ 1m candles copied exactly from the evidence captures:
  * 6 clear displacements (3 bullish, 3 bearish);
  * 5 clear non-displacements;
  * 6 borderline cases (body / A 1.48–1.51, close position 0.74–0.76; both sides);
  * 2 supporting / inconclusive cases.
  * Every special case the task lists is covered, and each approved condition decides at least one case on its own.
  * The verdicts: 0 mismatch with the oracle, Pine's formulation, the full history, and the real Pine log (4 cases inside the v0.8.0-dev capture). The bearish mirror holds.
  * No systematic conflict. I1 (a two-candle push with large upper wicks) and I2 (a three-candle staircase) are approved exclusions (M2, M5), reported as inconclusive.
* The classifications are the reviewer's, from the candle shape. The user's visual check is recommended (`docs/TESTS_DISPLACEMENT.md`).

**Validation 1.18.0**
* `tests/test_displacement_golden.py`: candles = evidence bars; the recorded numbers follow from them; oracle and `DispPine` verdicts on the window and on the full history; the real Pine log agrees; the mirror; the CISD relation (frozen CISD-R oracle); coverage; the thresholds are the approved ones.
* `tests/test_parity_v080_evidence.py`; the evidence set now has 5 files (`test_evidence_captures_are_unchanged`).
* Docs: `docs/TESTS_DISPLACEMENT.md` (L10 / L11 PASS, S-DISP-11 / 12, the DISP-L11 visual check and the DISP-L12 reload procedure), `docs/DISPLACEMENT.md` status, the golden README, the evidence README.

**TEST:**
* FULL: **PASS**, exit 0, 478.0 s, **1052 passed, 1 skipped** (the long-standing parity skip only; the observed-capture test runs again on the real v0.8.0-dev capture and passes):
  * static 22/22 (ST-21, ST-22);
  * golden 110/110 (8 earlier + 102 displacement);
  * parity 142/143 (v0.8.0-dev evidence 2 + observed capture);
  * displacement 106/106, displacement study 24/24;
  * CISD 167/167, LRL 85/85, HTF 46/46, invariant detectors 76/76, regression 5/5;
  * Phase 1 / 2 unchanged.
* `src/IST.pine` unchanged since `1b54759` (SHA-256 740ebcf6…5862). DISPLACEMENT-R, CISD-R and its tag, LRL, HTF FVG and Phase 1 / 2 unchanged.

## v0.8.0-dev — Displacement in Pine (DISPLACEMENT-R) · validation 1.17.0 (2026-11-01, branch `displacement/pine`) — EXPERIMENTAL, not frozen

**User (2026-11-01):** the displacement research is approved (M1…M11). Implement DISPLACEMENT-R in Pine as an independent engine. Do not touch CISD-R or its baseline tag, Phase 1 / 2, LRL or HTF FVG; no IFVG, no multi-bar displacement, no final styling, no alerts.

**CHANGE (src/IST.pine)**
* **Constants (M4):** `DISP_K 1.5`, `DISP_CLOSE 0.75`, `DISP_TRA_LEN 14`, `DISP_MEM 50`; events 34 / 35 = `DISPLACEMENT_CONFIRMED` / `DISPLACEMENT_DROPPED_MEMORY`. One [calc] input: `dispOn` (group DISPLACEMENT, ON).
* **L1, every bar, global scope:**
  * its own `dispTra = ta.sma(ta.tr(true), 14)` (M9);
  * `dispTraPrv = dispTra[1]` (A);
  * `dispPrvHi / dispPrvLo = high[1] / low[1]`.
  * The engine receives plain values; no history read inside a function (ST-21).
* **L3:**
  * `f_dispHit`: DEF-DISP1…5 in side coordinates;
  * `factsDisp`: the FVG metadata of the previous bar's record, once. It uses Phase 1's DEF-A1 `rawBull` / `rawBear`, the frozen geometry, not a second FVG definition;
  * `confirmDisp`: the record (candle, A, body, range, body / A, range / A, close position, previous extreme, FVG metadata UNKNOWN), the event, memory 50.
* **ENGINE RUN:** at bar close, after HTF FVG and before CISD: FVG metadata first, then the candle (bullish, else bearish), no decision while A is warming up or 0.
* **No renderer and no alert (M11):** `EV_DISP_CONFIRMED => false`. Debug: five Data-Window-only values (`dbg · DISP …`). The 52-row debug table is unchanged.
* **Parity capture:**
  * CAPTURE `disp / dispk / dispclose / disptr / dispmem`;
  * `DISPSTATE` / `DISPREC` after captured bar 15;
  * per-bar `DS / DA / DK / DP / DF`.
  * Existing capture output is unchanged.

**WHY.** The approved DISPLACEMENT-R in IST. The v0.7.0-dev call-history defect class is designed out: every history read is at global scope.

**PHASE 1 / 2, LRL, HTF FVG, CISD IMPACT:** none. ST-15, ST-16, ST-17, ST-19 and ST-20 pass unchanged, and every frozen CISD test passes unchanged.

**REPAINT IMPACT:** none. Decided at the candle's close. The FVG metadata is set once, one bar later, and is metadata only. Stateless, so reload-proof after bar 14.

**Validation 1.17.0**
* `DispPine` (`validation/models/displacement.py`, Pine's formulation, transliterated) = the oracle. The oracle itself is unchanged.
* ST-22 (19 rules, 4 constants, 2 orders); ST-08 now allows displacement; `dispOn` is a [calc] input; `ORACLE_ONLY` is empty (ST-14 exact).
* `tests/test_displacement_pine.py`: the approval's case list × 2 sides, real data, walks, 25 mutations, ST-21 regression, inputs / no renderer / capture.
* `tests/test_parity_disp.py`: faithful captures exact; 15 corruption kinds detected.
* `fuzz`: Pine formulation = oracle.
* `parity/capture.py _compare_disp`; `manual.py` reads `DISPLACEMENT_*` lines.
* **Docs:**
  * `docs/DISPLACEMENT.md`: APPROVED, §5 Pine, §6 capture;
  * `docs/TESTS_DISPLACEMENT.md`: DISP-L00…L12;
  * `docs/STUDY_DISPLACEMENT.md`: approved; a wording correction ("close beyond the previous candle" is a displacement criterion, not the FVG definition; no rule change).

**TEST:**
* FULL: **PASS**, exit 0, 494.0 s, **947 passed, 2 skipped** (the long-standing parity skip, and the observed-capture test: the latest real capture was written by v0.7.1-dev):
  * static 22/22 (ST-21, ST-22);
  * displacement 106/106 (oracle 26 + Pine 80), displacement study 24/24;
  * parity 139/141 (+21 displacement parity), property 37/37, long walks 19/19, invariant detectors 76/76;
  * CISD 167/167, LRL 85/85, HTF 46/46, golden 8/8, regression 5/5;
  * Phase 1 / 2 unchanged.
* TradingView: DISP-L00 PENDING. A new real Pine Logs capture with v0.8.0-dev is needed for DISP-L10 (the existing captures were written by v0.7.1-dev and earlier).

## Displacement research + oracle — DISPLACEMENT-R proposed · validation 1.16.0 (2026-11-01, branch `research/displacement`) — no indicator change

**User (2026-11-01):** start the research / specification phase of displacement as an independent module; compare candidate definitions on real NQ without tuning on outcomes; recommend one; implement it in the Python oracle with tests and invariants; no Pine; CISD-R, LRL and HTF untouched.

**RESULT**
* `docs/STUDY_DISPLACEMENT.md` (A–M): nine candidates (body, range, strong close, relative median, 2- / 3-candle windows, directional run, FVG-required, hybrid, recent-range break) on 3,791 real 1m bars (≈ 63.2 h, three segments).
  * Each threshold = the Tukey upper fence of its own statistic. Body / TR fence 1.47, stable 1.40–1.52 across segments and 1m–5m.
* **DISPLACEMENT-R** (= D6):
  * one closed candle with `body ≥ 1.5 × TR average (14 bars before)`;
  * the close in the outer quarter of its range;
  * the close beyond the previous candle's extreme.
* **Numbers:**
  * 110 events, 1.74/h (2.9 % of bars on every timeframe), the same rate in every session.
  * A large-candle detector in points is 11–69 × denser in NY AM than in Asia.
  * 85 % leave an FVG, but only 14 % of FVGs come from a displacement candle, so the FVG is metadata, not a requirement.
  * 12 % of CISDs are confirmed by a displacement, and 25 % of displacements have no CISD within ±10 bars: distinct modules.
  * Shuffled candles and random walks produce such candles too: descriptive only, no predictive claim.
* **Known false negative:** fast multi-candle moves without a qualifying candle (34–58 %). This is open decision M5.

**Validation 1.16.0**
* `validation/studies/displacement.py` + `tests/test_displacement_study.py` (24).
* Oracle `validation/models/displacement.py`: opt-in module `disp`, `DispSettings(k 1.5, clv 0.75, tra_len 14, memory 50)`.
  * Events `DISPLACEMENT_CONFIRMED` / `DISPLACEMENT_DROPPED_MEMORY`, as `ORACLE_ONLY` (ST-14 excludes them until Pine).
  * The record's FVG fact is stamped on the next bar. The oracle equals the study's D6 record-for-record (110).
* `tests/test_displacement.py` (26), `fuzz/test_displacement_properties.py`, INV-DISP-01…06 with negative tests (74 invariants).
* Report sections `disp` and `research.disp`; `--phase disp`.

**TEST:**
* FULL: **PASS**, exit 0, 620.8 s, **845 passed, 1 skipped** (the parity section's long-standing skip):
  * static 21/21;
  * displacement 26/26, displacement study 24/24;
  * property 36/36, long walks 19/19, invariant detectors 76/76;
  * CISD 167/167, LRL 85/85, HTF 46/46, parity 119/120, golden 8/8;
  * Phase 1 / 2 unchanged.
* `src/IST.pine` unchanged (SHA-256 29dd2bfd…afbbf); CISD frozen tag and release untouched; default modules and the regression baseline unchanged.

## CISD FROZEN — CISD-L12 manual PASS recorded (2026-10-31, branch `cisd/pine`) — documentation only

**User (2026-10-31):** the CISD-L12 TradingView reload check passes. The same 3 historical CISDs kept their side, origin / id, L, confirmation bar and delivery state after a page refresh and after removing and re-adding the indicator; no historical CISD changed.

* Annotated tag `CISD_BASELINE_v0.7.1-dev` on the freeze commit `cb2ee97` (created before this commit; not moved).
* `docs/TESTS_CISD.md`, `docs/CISD_FREEZE_REPORT.md`, `docs/CISD.md`, `README.md`: CISD-L12 **PASS** (automated and manual), status FROZEN.
* No change to `src/IST.pine`, the oracle, the tests, `releases/v0.7.1-dev/` or its hashes / manifest (the release keeps the freeze commit's documents).

## CISD freeze prepared — v0.7.1-dev unchanged · validation 1.15.0 (2026-10-31, branch `cisd/pine`) — no indicator change

**User (2026-10-31):** the real v0.7.1-dev capture passes with 0 DIFFERENCE. Complete CISD-L11 and CISD-L12, then prepare the CISD freeze, without changing CISD-R, LRL or styling.

**RESULT**
* **CISD-L10 PASS:** the real capture `pine-logs-IST_5040e.csv` (kept byte for byte as `parity/evidence/ist-v0.7.1-dev_mnq-1m-replay_capture-1000_2026-10-14.csv`) gives 67 MATCH · 0 DIFFERENCE · 9 NOT OBSERVABLE, in every module.
* **CISD-L11 PASS:** human goldens H1 and H2 exact; H3 and H4 supporting; 0 mismatch; the approved rules pinned by name.
* **CISD-L12:** automated **PASS** (determinism, view-independence, guard never retroactive); TradingView reload check pending (user).

**Validation 1.15.0**
* `tests/test_cisd_freeze.py`: the L11 rule list and the L12 automated requirements; existing proofs named in its docstring.
* `tests/test_parity_v071_evidence.py`: the real capture's counts pinned.
* The evidence SHA256SUMS now has 4 files.
* The observed-capture test runs again (latest capture = current build) and passes.

**Freeze package:**
* `docs/CISD_FREEZE_REPORT.md`;
* `docs/TESTS_CISD.md` with the final statuses and the manual reload procedure;
* `releases/v0.7.1-dev/` (read-only copy, SHA256SUMS, MANIFEST).

The tag `CISD_BASELINE_v0.7.1-dev` is not created yet; it waits for the manual CISD-L12 check and the user's go.

**TEST:**
* FULL: **PASS**, exit 0, 473.8 s, **780 passed, 1 skipped**:
  * static 21/21;
  * CISD 167/167;
  * parity 119/120;
  * golden 8/8;
  * LRL 85/85, HTF 46/46;
  * Phase 1 / 2 unchanged.
* `src/IST.pine` unchanged since `b34a194` (SHA-256 29dd2bfd…afbbf).

## v0.7.1-dev — history reads moved out of functions: CISD bk and LRL τ / separation (2026-10-30, branch `cisd/pine`) — EXPERIMENTAL, not frozen · validation 1.14.0

**User (2026-10-30):** the first valid real capture of v0.7.0-dev showed CISD differences on `bk` only and real LRL divergence (τ, boundaries, events, ends, candidate counts).
* Find the root cause first.
* Do not change CISD-R or the LRL definition.
* Fix only the wrong side, add a regression test, run FULL and re-run the capture.

**ROOT CAUSE** (one Pine construct, three lines). Pine keeps a separate history **per call** of a user function or method. A history read of a user series inside a function that does not run on every bar returns the value of an earlier CALL, not of the earlier BAR.
* **CISD**, `float tr1 = cisdTra[1]` in `confirmCisd`:
  * there are two call sites, one per side, so `[1]` = the TR average at the previous same-side confirmation;
  * the first reproducible divergence is 2026-10-29 22:16 BEAR, where Pine used 14.607143 (22:05's value) and the oracle 14.75 (22:15, the bar before);
  * emulating that reproduces **80 of 80** of Pine's bk values; the intended value matches 1 of 83.
* **LRL**, `lrlTra[bar_index - xa]` in `seed` (τ) and `fits` (separation):
  * the first divergence is the LRL LOW anchored 2026-10-29 23:33, confirmed at 23:59: Pine τ 5.88392857 = 0.5 × 11.767857, a TR average from an earlier bar (23:20), where the oracle has 0.5 × 14.446429, the TR average at the anchor;
  * none of Pine's τ is the anchor's;
  * with Pine's logged τ injected, the oracle's LRL differences fall **330 → 70**. The rest sit where the same wrong read decided the separation check (an extension at 03:31, a candidate at 12:21).
* Phase 1, Phase 2 and HTF FVG have no such read (`f_htfPack` runs on every bar of its request): 0 differences in the capture.
* The oracle was right in both cases; the definitions are unchanged.

**CHANGE (`src/IST.pine`)**
* `float cisdTraPrv = cisdTra[1]` at global scope; `confirmCisd` uses it.
* The LRL TR average of every closed bar is recorded at global scope (`lrlTraBuf`, 100 bars; `LRL_TRA_BUF`). `fits` / `seed` read the anchor's value with `f_lrlTraAt(xa)`. `max_bars_back(lrlTra, 100)` is removed (unused).
* `IST_BUILD = "v0.7.1-dev"`, written into the CAPTURE line (`build=`).
* No other line is changed.

**WHY:** to make Pine compute what the approved definitions say. The CISD metadata is the TR average of the 14 bars before the confirmation (DEF-CISD6); τ = max(EQ tolerance, 0.5 × TR average at the anchor) (DEF-LRL2).

**PHASE 1 IMPACT:** none (ST-15). **REPAINT IMPACT:** none.

**Validation 1.14.0**
* **ST-21:** no history read of a user series inside a function or method (allowed: `f_htfPack`). It catches both defects.
* **ST-12:** also checks `IST_BUILD`.
* **ST-17 / ST-20:** the new lines are pinned; the CISD engine now reads no history at all.
* **Mutations:** the call-history read (CISD and LRL), the TR average of the confirming bar itself, and recording only on pivots are all caught.
* **`tests/test_parity_cisd.py`:** a capture with v0.7.0-dev's bk is flagged on bk alone.
* **The real capture is kept as evidence** (`parity/evidence/ist-v0.7.0-dev_mnq-1m_capture-1000_2026-10-30.csv`, SHA256). `tests/test_parity_v070_evidence.py` pins the diagnosis: other modules exact, CISD differences bk-only and 80/80 reproduced, LRL 330 → 70.
* **The parity report names the capture's build.** A capture from another build is reported as unable to show the current Pine. The observed-capture test is skipped, never passed, with the reason "a NEW TradingView capture is required".

**TEST:**
* FULL: **PASS**, exit 0, 505.5 s, **767 passed, 2 skipped**:
  * static 21/21 (ST-21 new);
  * LRL 85/85;
  * CISD 157/157;
  * parity 116/118;
  * the 2 skips are the previous one and the observed-capture test, which skips on a v0.7.0-dev capture with the reason given;
  * Phase 1 / 2 and HTF sections unchanged.
* The saved v0.7.0-dev capture still differs, as it must: it is v0.7.0-dev's output.
* **A NEW TradingView Pine Logs capture with v0.7.1-dev is required** (CISD-L10, LRL-L11).

## CISD human / reference audit — validation 1.13.1 (2026-10-30, branch `cisd/pine`) — no indicator change, no definition change

**User (2026-10-30):** audit the supplied CISD screenshots, the product reference and the video against CISD-R, without changing it.
* Classify each example.
* Report the visual differences separately.
* Treat outcomes as metadata.
* Write an IFVG requirements note (research only).
* Audit FVG identity for inversion tracking.
* Do not change Pine.

**DELIVERABLE**
* `docs/AUDIT_CISD_HUMAN.md` (A–G).
* `docs/IFVG_REQUIREMENTS.md`.
* `validation/golden/human/`: the 4 screenshots, a README with the classification and the context / outcome metadata, and two golden cases digitised from the screenshots (pixel units).

**RESULT**
* **H1 (product) and H2 (trader): EXACT MATCH.** Origin candle, L (0 px) and confirming bar (0 bars).
* **H3, H4 and the two video examples: NOT ENOUGH INFORMATION.** The resolution is too low or the low is out of the frame; they are consistent where readable.
* **No mismatch.** The human lines reject the last-candle anchor (H1: 117 px and 4 bars off; H2: 99 px off) and, in H2, the any-candle extreme (61 px and 1 bar off).
* **Video:** the CISD and the IFVG appear by the close of the confirming bar, not while it forms.
* **Visual differences only:**
  * the references extend the line 4–8 bars past the confirmation;
  * they put the label above the line at its right end.
* **Recommendation: KEEP CISD-R.**

**Validation 1.13.1:** the golden runner also loads `golden/human/` (GOLD_CISD_H1, GOLD_CISD_H2: CISD-R reproduces both, every invariant checked).

**TEST:**
* QUICK: **PASS**, exit 0, 262.1 s, **746 passed, 1 skipped**; golden 8/8 (2 new); static 20/20; every other section unchanged.
* `src/IST.pine` unchanged.

## v0.7.0-dev — CISD in Pine (2026-10-30, branch `cisd/pine`) — EXPERIMENTAL, not frozen · validation 1.13.0

**User (2026-10-30):** the CISD-R oracle is approved; implement CISD in Pine without changing the definition.
* Identity = side + origin time.
* Explicit UNKNOWN start, strict alternation.
* No 500-bar (or any) leg-length limit.
* Events `CISD_CONFIRMED` / `CISD_DROPPED_MEMORY` (remove the ST-14 oracle-only exception).
* Memory 50, oldest ENDED record first.
* 200-bar display / alert guard (not DEF-CISD).
* Current CISD only, previous optional.
* Minimal settings, alert OFF.
* Debug, parity capture, static and mutation tests.
* No displacement, IFVG, DEF-LRL9 or scoring.

**CHANGE (`src/IST.pine`)**
* **CISD engine (L3)**, after the HTF engine, on closed bars, reading bars only:
  * types `Cisd` (record), `CisdSide` (per side) and `CisdBook` (state, records, counters);
  * methods `feedCisd`, `pruneCisd`, `readyCisd`, `factsCisd`, `confirmCisd`;
  * its own TR average `cisdTra`, for the body / TR metadata only.
* **Incremental, no scan.** Each side keeps the suffix minima of its delivery lows (with each one's series origin and L) and of every low, in its leg window. A window restart only drops entries. No series is read beyond `cisdTra[1]`, so a leg of any length is handled exactly and no history buffer is involved.
* **Events** `CISD_CONFIRMED` (`dir` = side, `id` = origin time, `px` = L, audit `prev · close · ext · et · bk`) and `CISD_DROPPED_MEMORY`.
* **Renderer:** the current CISD as one 1 px line at L from the origin candle to the confirming candle, plus a tiny "CISD" label, colour `#4F473F`. The previous one is drawn faded with its toggle. Bar-time coordinates. Never a CISD confirmed before bar 200.
* **Settings** (group "CISD · CHANGE IN STATE OF DELIVERY"): Enable ON [calc], Show ON, Show previous OFF, CISD alerts OFF. Developer: Inspect CISD.
* **Alert:** one per `CISD_CONFIRMED` at the bar close, never before bar 200.
* **Debug rows 45–51** (table 52 rows).
* **Capture:** header `cisd / cisdmem / cisdtra / cisdguard`; the snapshot `CISDSTATE` / `CISDSIDE` / `CISDREC` after the first captured bar; per bar `CS / CU / CN / CA`.
* Phase 1 / 2, LRL and HTF FVG code is unchanged. The only shared lines touched are additions:
  * the header;
  * one `f_evName` case pair;
  * one `f_alertOn` case;
  * the `isFvg` comment;
  * the debug table size;
  * the capture header and BAR line.

**WHY:** the approved CISD-R definition, as the oracle runs it, without the 500-bar re-scan limit that a direct port of the oracle's restart scan would need.

**PHASE 1 IMPACT:** none. ST-15 shows no Phase 1 line removed beyond the reviewed manifest.

**REPAINT IMPACT:** none.
* Decided at bar close.
* L is known at the close of the extreme's bar.
* Facts are stamped from the bar after.
* The guard and the display inputs are never read by detection (ST-01, ST-20).

**Validation 1.13.0**
* **Oracle:**
  * `validation/models/cisd.py` `CisdStack`: Pine's incremental formulation, with `snapshot` / `restore`;
  * delivery state names UNKNOWN / UP / DOWN (sides BULL / BEAR);
  * the audit text gains `et` and `bk`.
* **ST-20** (34 rule lines, constants, per-bar order, no history / numbers in the engine, guard and display outside detection).
* **ST-14:** exact again (`ORACLE_ONLY` removed).
* **ST-08:** CISD in scope; IFVG, SMT, displacement, confluence and quality score still forbidden.
* **`tests/test_cisd_pine.py`:**
  * incremental = oracle on NQ 1m / 3m / 5m / 15m, four 20,000-bar walks, a mirrored walk and all scenarios, with memory 50 and 2;
  * a leg longer than 500 bars exact (origin 657 bars back; flip window 649 bars);
  * snapshot / restore;
  * 27 mutations caught (the user's 15 and 12 more);
  * settings, renderer, debug and capture.
* **Property:** incremental = oracle on generated candles.
* **`tests/test_parity_cisd.py`:**
  * faithful captures starting from an established state give 0 DIFFERENCE (NQ; walks with memory drops);
  * 10 error kinds detected;
  * replay with Pine's constants.
* **`parity/capture.py` `_compare_cisd`:**
  * (b) the restored snapshot replayed exactly;
  * (c) the definition oracle started UNKNOWN, compared after synchronising.
* **`docs/CISD.md` §5** (Pine) and **`docs/TESTS_CISD.md`** (CISD-L00…L12).

**TEST:**
* FULL: **PASS**, exit 0, 665.1 s, **756 passed, 1 skipped** (the same skip as before):
  * static 20/20 (ST-20 new);
  * cisd 155/155 (oracle 75 + Pine 80);
  * parity 113/114 (16 CISD);
  * properties 30/30;
  * long walks 16/16;
  * detectors 70/70;
  * every other section unchanged.
* TradingView: CISD-L00…L12 PENDING (not compiled yet).

## CISD oracle — validation 1.12.0 (2026-10-30, branch `research/cisd`) — no indicator change, for approval before Pine

**User (2026-10-30):** CISD-R is approved for the reference-model / oracle phase; **no Pine yet**.
* D-C1…D-C12 approved.
* Clarifications:
  * an explicit **UNKNOWN** initial state;
  * the 200 bars are a **display / alert guard only**, not part of the definition and not a requirement for a CISD;
  * the confirmation body / TR average is **metadata only**;
  * real golden cases come from the user once Pine runs in TradingView.

**DELIVERABLE** `docs/CISD.md` (DEF-CISD1…9):
* delivery candle / series: a doji ends a series;
* the leg window;
* the level L: delivery extremes only, an equal extreme goes to the later candle;
* the state of delivery: UNKNOWN → established → strict alternation, with the proof that two CISDs never confirm on one bar;
* confirmation: first close > L + ε, any colour;
* the record;
* lifecycle ACTIVE → ENDED and memory;
* isolation;
* the display guard.

**Oracle** `validation/models/cisd.py`, the opt-in module `cisd`:
* not in default runs, baselines or parity;
* `CisdSettings`: memory 50, TR length 14 (metadata), guard 200 (view);
* events `CISD_CONFIRMED` and `CISD_DROPPED_MEMORY` (`events.ORACLE_ONLY`: ST-14 excludes them until Pine gains the module, and stays exact for every other name);
* retest, close back through L and leg break are immutable record facts, not events;
* record by record identical to the approved study engine: NQ 1m / 3m / 5m / 15m = 121 / 55 / 23 / 14 CISDs, walks, all 14 scenarios.

**Validation 1.12.0:**
* invariants INV-CISD-01…08 with negative tests: state, level and window, confirmation, timing, facts, frozen, events, memory / lifecycle;
* `tests/test_cisd.py`: the user's T1…T18, plus oracle = study, record fields, memory drop path, invariants on NQ with every module, opt-in settings;
* `fuzz/test_cisd_properties.py`: invariants, mirror, translation, no lookahead, guard and metadata change no decision, other modules unchanged, long walks;
* report section `cisd`, `--phase cisd`.

**Correction:** the study's reload figure (≤ 4 CISDs, ≤ 62 bars) covered starts in the first 600 bars only. Over the whole capture it is ≤ 8 CISDs and ≤ 87 bars (1m), ≤ 105 bars (5m), ≤ 60 on walks. All are inside the 200-bar display guard, which remains a safeguard, not a guarantee.

**TEST:**
* FULL: **PASS**, exit 0, 537.0 s, **658 passed, 1 skipped** (the same skip as before):
  * cisd 75/75; detectors 70/70 (+8); properties 29/29; long walks 16/16;
  * static 19/19; every other section unchanged;
  * FULL takes about 4 minutes longer than in 1.11.0, mostly the CISD properties and long walks.
* `src/IST.pine`, Phase 1, Phase 2, LRL, HTF FVG, the frozen tags and the regression baseline are unchanged.

## CISD research study — validation 1.11.0 (2026-10-30, branch `research/cisd`) — no indicator change, for approval

**User (2026-10-30):** the next functional module is CISD. Define it exactly, deterministically and without repainting **before** any reference model or Pine. This is a research / specification phase only.

**DELIVERABLE** `docs/STUDY_CISD.md` (A–N):
* formal semantics;
* five candidate definitions with exact pseudocode;
* comparison on real NQ 1m (1,639 bars, 27.3 h), resampled 3m / 5m / 15m, and a random walk;
* 16 synthetic scenarios;
* the recommendation, lifecycle, events, renderer, oracle / validation plan, Pine feasibility;
* open decisions D-C1…D-C12.

**Recommendation CISD-R:**
* the level is the open of the down-close series (bullish CISD) that delivered price into the lowest low of the current bearish leg;
* confirmed by the first close strictly beyond it;
* a one-bit state of delivery makes bullish and bearish CISDs alternate;
* no parameters, mirror-exact, prefix-invariant.

**Measured:**
* frequency: NQ 4.4 / h vs 14–19 / h for stateless definitions;
* at most one candidate at any time;
* no edge demonstrated: CISD frequency, retest and follow-through on NQ ≈ the random walk;
* displacement removes 58 % of CISDs and stays a separate engine;
* reload convergence: from 86 different first bars, identical to the full history after ≤ 4 CISDs (≤ 62 bars).

**Findings that shaped the definition** (all in the study):
* the leg extreme must be set by delivery candles only: a non-delivery wick spike left no candidate in one NQ case;
* the opposite side's leg window starts at the previous leg's extreme, not at the confirmation bar;
* "invalidation" is subsumed by the opposite CISD: 0 cases on NQ, rare gap-only exceptions on walks.

**Validation 1.11.0** (study only):
* `validation/studies/cisd.py`;
* `validation/tests/test_cisd_study.py`, 29 tests: scenarios, candidate contrasts, mirror, translation, prefix, alternation, reload convergence;
* report section `research.cisd`, marker `cisd`;
* charts `docs/study_cisd/`.

**TEST:**
* FULL: **PASS**, exit 0, 298.2 s, **566 passed, 1 skipped**: research.cisd 29/29 · static 19/19 · every other section unchanged.
* `src/IST.pine` is not modified.

## v0.6.2-dev — HTF FVG palette for a `#C2BAAE` chart background (2026-10-30, branch `lrl/pine`) — EXPERIMENTAL, not frozen · validation 1.10.1

**User (2026-10-30):** the chart background is `#C2BAAE` and the HTF FVGs were still too hidden. The fix is a darker, neutral grey-brown palette, with no green / red. The hierarchy is kept: 15m / 30m lightest, 1H / 4H medium, 1D / 1W most visible.

**CHANGE** (`src/IST.pine`, styling only: [view] constants and one renderer call, `f_htfBox`):

| constant | v0.6.1-dev | v0.6.2-dev |
|---|---|---|
| `HTF_TXT_COL` | `color.new(chart.fg_color, 35)` | `color.new(#4F473F, 0)` |
| `HTF_FILL_1` (new, 15m / 30m) | `color.new(HTF_COL, 94)` | `color.new(#6F665B, 88)` |
| `HTF_FILL_2` (new, 1H / 4H) | `color.new(HTF_COL, 91)` | `color.new(#655D54, 84)` |
| `HTF_FILL_3` (new, 1D / 1W) | `color.new(HTF_COL, 88)` | `color.new(#5A534B, 80)` |
| `HTF_BORDER_1` (new, 15m / 30m) | `color.new(HTF_COL, 85)` | `color.new(#6A6157, 35)` |
| `HTF_BORDER_2` (new, 1H / 4H) | `color.new(HTF_COL, 70)` | `color.new(#5E564D, 20)` |
| `HTF_BORDER_3` (new, 1D / 1W) | `color.new(HTF_COL, 55)` | `color.new(#4F473F, 10)` |
| `HTF_COL` | `#9598A1` | removed (no longer used) |

* `f_htfBox` picks the fill and border by tier, where it computed them from `HTF_COL` before.

**Unchanged:**
* the 1 px border;
* the label bottom-right, `HTF_TXT_SIZE` = `size.small`, the full text `15m Fair Value Gap` …;
* no object added;
* the LRL style (v0.6.1-dev);
* no detection, state, event, oracle or lifecycle change.

**Validation:** no logic test changed. `tests/test_htf_pine.py::test_renderer_rules` pinned the old style (`HTF_COL`); it now pins the new constants:
* fill transparency 88 / 84 / 80;
* border transparency 35 / 20 / 10;
* the text `#4F473F` opaque.

**TEST:**
* QUICK: **PASS**, exit 0, **527 passed, 1 skipped**; static 19/19.
* TradingView: the visual check on the `#C2BAAE` chart (HTF-L04) is pending.

## v0.6.1-dev — visual readability pass: HTF FVG labels, LRL line (2026-10-30, branch `lrl/pine`) — EXPERIMENTAL, not frozen · validation 1.10.1

**TradingView (user, 2026-10-30):** v0.6.0-dev compiles and runs. The visual direction is confirmed:
* straight LRL;
* HTF FVGs only, local 1m FVGs hidden;
* timeframe labels present.

The HTF labels were too low-contrast and the LRL slightly too faint.

**CHANGE** (`src/IST.pine`, styling only: [view] constants and three renderer calls):

| constant | v0.6.0-dev | v0.6.1-dev |
|---|---|---|
| `HTF_TXT_COL` (HTF label colour) | `color.new(#787B86, 30)` | `color.new(chart.fg_color, 35)` |
| `HTF_TXT_SIZE` (new; HTF label size) | `size.tiny` (inline) | `size.small` |
| `LRL_BEAR_COL` / `LRL_BULL_COL` (solid confirmed LRL and its label) | `#9598A1` | `color.new(chart.fg_color, 30)` |
| `LRL_PROJ_T` (new; dashed projection while active) | 40 (inline) | 60 |

* `chart.fg_color` is the chart's own text colour, so both stay neutral grey and adapt to the theme: darker on a light chart, lighter on a dark one.
* Approximate contrast against the chart background, light / dark:

  | | v0.6.0-dev | v0.6.1-dev |
  |---|---|---|
  | HTF label | 2.6 : 1 / 2.7 : 1 | 5.8 : 1 / 5.7 : 1 |
  | solid LRL | 3.0 : 1 / 6.2 : 1 | 7 : 1 / 6.4 : 1 |
  | dashed projection | 1.7 : 1 / 3.0 : 1 | 2.6 : 1 / 2.9 : 1 |

  So the projection stays clearly subtler than the solid segment.

**Unchanged:**
* HTF boxes: `HTF_COL #9598A1`; fill transparency 94 / 91 / 88 and border transparency 85 / 70 / 55 (15m–30m / 1H–4H / 1D–1W); border 1 px; label bottom-right with the full text.
* LRL: width 1; the `LRL` label at `size.tiny`; ended LRLs (`T_HIST` 45, projection 75); no magenta / cyan.
* No object added.
* Session / PDH / PDL / PWH / PWL labels are Phase 1 and are not changed. They are already placed right of the last bar (`label.style_label_left` at the right offset); GENERAL → Label size → Tiny makes them lighter if they compete.
* No detection, state, oracle, event, lifecycle or Phase 1 / 2 change.

**Validation 1.10.1:**
* `tests/test_htf_pine.py` pins the label size and colour and the 1 px border.
* New `tests/test_lrl_pine.py::test_lrl_style_solid_stronger_than_projection`: grey from the chart's text colour, the projection's transparency above the solid line's, width 1, the label tiny.

**TEST:**
* QUICK: **PASS**.
* FULL: **PASS**, exit 0, 686.5 s on a busier machine (v0.6.0-dev: 292.7 s; one test added, no logic change), **537 passed, 1 skipped**: static 19/19 (ST-15: the same 12 reviewed Phase 1 lines) · regression 5/5 · LRL · HTF unchanged.
* TradingView: the visual check of v0.6.1-dev (HTF-L04 labels, LRL-L02 line) pending.

## v0.6.0-dev — HTF Fair Value Gaps (Module B) · neutral grey LRL · Phase 1 FVG display OFF (2026-10-29, branch `lrl/pine`) — EXPERIMENTAL, not frozen · validation 1.10.0

**Decisions (user, 2026-10-29):** the straight LRL renderer and the HTF FVG design are approved, with final decisions D1–D10 (`docs/HTF_FVG.md`):
* the LRL is drawn thin and neutral grey (no strong magenta / cyan);
* the user-facing FVGs are the HTF ones: 15m, 30m, 1H, 4H, 1D and 1W;
* Phase 1 `Show FVGs` defaults to OFF (D9, display only).

**CHANGE** (`src/IST.pine`):
* **LRL** (L6 only): `LRL_BEAR_COL` / `LRL_BULL_COL` = `#9598A1`. DEF-LRL1…6, state and events unchanged.
* **Phase 1 view default (D9):**
  * `fvgShow` true → false: one Phase 1 *view* line.
  * It is recorded as a reviewed deviation in `validation/baselines/PHASE1_DEVIATIONS.md` and in the ST-15 manifest.
  * Module A's calculation, lifecycle, events and alerts are unchanged.
* **HTF FVG, Module B (DEF-B0…B6), additive:**
  * **L1:** six `request.security(…, f_htfPack(), lookahead_on)` calls, one per timeframe. `f_htfPack()` reads every series at `[1]` or older:
    * the DEF-A1 / A2 zone on candles [3] · [2] · [1] with the Phase 1 inputs and that timeframe's own TR average (D4);
    * the HTF-side seed engine (DEF-B2);
    * the last completed HTF bar.
  * A timeframe at or below the chart's is inactive and never requests a lower timeframe.
  * **L3:** `HtfTf` / `HtfZone`, unique method names (`feedHtf`, `stepHtf`, `seedHtf`, `milestonesHtf`, `trimHtf`). On each chart bar and timeframe:
    * seed point;
    * on a new completed HTF bar: invalidate by the own-timeframe close (D5), then create;
    * milestones from the known bar (D2, no retroactive touches for seeds).
  * Memory: 20 records per timeframe (closed first).
  * **L5:** `HTF_FVG_CREATED · SEEDED · FIRST_TOUCH · CE_TOUCH · FULL_FILL · INVALIDATED · DROPPED_MEMORY` (kinds 25–31). `Event.tf` (a new field, default "") carries the timeframe, and the audit text starts with `tf=15m`. BULL / BEAR in the text. No HTF alerts.
  * **L6:**
    * per timeframe, the nearest open zone above and below price (D6, ≤ 12 boxes);
    * drawn 1W first, 15m last; no merging or hiding (D1);
    * neutral grey with opacity tiers (D7);
    * the box from HTF candle 1 (D8);
    * the text `15m Fair Value Gap` … `1W Fair Value Gap` bottom-right, tiny grey; `15m FVG` is a Developer option (D10).
  * **Inputs:**
    * group HTF FAIR VALUE GAPS: Show HTF FVGs ON, 15m / 30m / 1H / 4H / 1D / 1W ON, Show timeframe labels ON, all [view];
    * Developer: Compact HTF labels.
  * **L7:**
    * debug rows 42–44 (engine, registries, drawn);
    * Parity capture: `htf=1|htftfs|htfmem|htfseeds|htfseedmem` on CAPTURE;
    * `HTFSTATE` / `HTFREC` snapshot after the first captured bar;
    * `HTFBAR` per completed HTF candle;
    * `HO=` per BAR.

**Validation 1.10.0:**
* oracle `models/htf_fvg.py` (opt-in module "htf"; `restore()` and an external HTF feed for parity);
* `Event.tf` in the event identity;
* INV-HTF-01…08 with negative tests;
* `tests/test_htf_fvg.py` (timing, D2, D5, D8, seeds, memory, identity, session alignment incl. DST, other modules identical, prefix invariance);
* `fuzz/test_htf_properties.py` (invariants, mirror, translation, no lookahead, **reload consistency**, other modules untouched, long walks);
* ST-03 extended (8 requests, `f_htfPack` reads nothing newer than [1]);
* new ST-19 (constants, 19 timing / definition lines, order);
* `tests/test_htf_pine.py` (18 mutations caught, renderer rules, settings target);
* bounded parity `_compare_htf`, covering:
  * (a) HTF candles vs the oracle's aggregation;
  * (b)+(c) the registry restored and replayed;
* `tests/test_parity_htf.py`;
* report section HTF and `--phase htf`.

**RISKS (TradingView only, not verifiable here):**
* a `var matrix` and string building inside `request.security`, and the tuple of 13 values;
* `str.tonumber` parsing of the seeds;
* boxes whose `bar_time` origin precedes the first loaded bar (seeded 1D / 1W zones);
* thin zones may clip their text;
* load time with six HTF contexts;
* the 4H / 1D / 1W alignment (checked by parity (a)).

**Fixed during development (validation only):**
* INV-EV-05 now keys structures by (family, dir, id, timeframe). The EQ-cluster registration still added 3-element keys, so two `min3` liquidity long walks failed: `EQ*_DROPPED_MEMORY … refers to no known structure`. The key is aligned; no model change.
* The HTF monitor checks timing and geometry once per record, when it first appears; INV-HTF-08 freezes those facts afterwards. Before, it recomputed them for every record on every bar, quadratic in a walk: FULL took 905 s.
* Negative tests INV-HTF-01 / 02 corrupt a newly seen record. The same corruption on a known record is caught by INV-HTF-08 (its own test).

**TEST:**
* QUICK: run during development.
* FULL: **PASS**, exit 0, 292.7 s, **536 passed, 1 skipped**:
  * static 19/19 (ST-03: 8 requests, nothing newer than [1]; ST-19: 19 rules · 3 constants · 2 orders; ST-15: 12 reviewed Phase 1 lines, the 12th = `fvgShow`);
  * every Phase 1 / Phase 2 section unchanged; regression 5/5;
  * LRL 81/81; HTF 46/46; invariant detectors 62/62; long walks 13/13.
* TradingView: HTF-L00…L14 pending (`docs/TESTS_HTF.md`). Also pending: LRL-L02 (one straight line) and the historical-drawing retest.

## v0.5.3-dev — LRL drawn as ONE straight line (2026-10-29, branch `lrl/pine`) — EXPERIMENTAL, not frozen · validation 1.9.3

**Decision (user, 2026-10-29, from the reference screenshots):** an LRL is drawn as ONE clean straight diagonal, not a polyline that bends at every failure swing. This is a renderer change: DEF-LRL1…6, the oracle, state, events and ids are unchanged.

**CHANGE** (`src/IST.pine`, L6 only):
* `f_lrlDraw` draws the chord in state as one solid line, from the first to the latest point (`line.new` on `r.yAt` at both ends).
* The projection is the same function y, dashed and fainter (transparency 40; 75 once ended), so there is no kink.
* The polyline, its pool and its deletes are removed. Debug row 41 shows LRL lines and labels instead of polylines.
* After an extension, the line is drawn first → new latest from that bar on.
* The Show LRL tooltip is updated. `max_bars_back(time, 5000)` stays: bar-index lines to far-left anchors still need it.

**Docs:**
* `docs/LRL.md`: DEF-LRL7 rewritten (user decision), §3 non-repaint wording for a chord redrawn on extension, §6 renderer and resources (no polylines; ≤ 4 lines + 2 labels active).
* `docs/TESTS_LRL.md`: LRL-L02 / L04 / L08 expectations.

**Validation 1.9.3:** `tests/test_lrl_pine.py::test_renderer_draws_one_straight_line` requires exactly one chord line, one projection on the same function, and no polyline or `chart.point` anywhere.

**Also (design only, nothing implemented):** `docs/HTF_FVG_DESIGN.md`, the HTF Fair Value Gap module (15m · 30m · 1H · 4H · 1D · 1W) for the user's approval. It covers:
* the architecture beside the frozen Phase 1 engine;
* data acquisition and non-repainting timing;
* the lifecycle (DEF-B1…B6), record identity and renderer hierarchy;
* overlap alternatives A–E, resources, label placement, parity and testing;
* the effect on Phase 1, Pine limitations, and decisions D1–D10.

**TEST:**
* QUICK: **PASS**.
* FULL: **PASS**, exit 0, 270.1 s, **458 passed, 1 skipped**: static 18/18 · LRL 81/81 · every Phase 1 / Phase 2 section unchanged · regression 5/5 · ST-15 the same 11 reviewed Phase 1 lines.
* TradingView: LRL-L02 (one straight line) and the historical-drawing retest pending.

## v0.5.2-dev — LRL historical drawings: explicit `time` history buffer (2026-10-29, branch `lrl/pine`) — EXPERIMENTAL, not frozen · validation 1.9.2

**TradingView on v0.5.1-dev (user):**
* LRL-L00 compile: **PASS**.
* Runtime with **Show historical LRL ON: FAIL**: "Error on bar 11241: The requested historical offset (1231) is beyond the historical buffer's limit (1230)". The stack is `f_lrlDraw()` (the historical polyline: `chart.point.from_index` / `polyline.new(…, xloc = xloc.bar_index)`) ← `f_lrlRender()` ← `#main()`.

**ROOT CAUSE** (renderer only, not LRL detection or state):
* Drawings at `bar_index` coordinates are converted internally through the `time` series.
* A historical LRL's pivots can be far behind the last bar, and Pine had sized `time`'s history buffer for the offsets it saw (1230 bars).

**CHANGE** (`src/IST.pine`): `max_bars_back(time, 5000)`, a series-specific buffer next to the existing high / low 5000 (the LRL design envelope `LRL_SPAN` = 4,900). The indicator-wide `max_bars_back` is not changed.

**Not changed:** the LRL definition, the oracle, LRL ids / state / lifecycle, chord geometry, bar_index coordinates (no switch to bar_time), the historical drawings (none truncated), Phase 1 / Phase 2.

**Validation 1.9.2:** ST-17 also pins the three LRL history buffers, `max_bars_back(high | low | time, 5000)`. New mutations, each caught: the `time` buffer removed, the `time` buffer shortened to 1000, the high buffer removed.

**TEST:**
* QUICK: **PASS**.
* FULL: **PASS**, exit 0, 452.0 s, **457 passed, 1 skipped**:
  * static 18/18 (ST-17: 33 formulas · 9 constants · 2 orders) · LRL 80/80;
  * every Phase 1 / Phase 2 section unchanged;
  * regression 5/5 against the frozen baseline;
  * ST-15: the same 11 reviewed Phase 1 lines.
* TradingView retest pending: Show LRL ON + Show historical LRL ON, NQ1! 1m, a long history.

## v0.5.1-dev — LRL compile fix: no overloaded `advance` (2026-10-28, branch `lrl/pine`) — EXPERIMENTAL, not frozen · validation 1.9.1

**TradingView LRL-L00 on v0.5.0-dev: FAIL** (user). The compiler reported CE10182, "Cannot use global variable "barEv" in the local scope of overloaded function "advance()"", on the FVG `method advance(Fvg z)`; 9 problems in total.

**ROOT CAUSE:**
* v0.5.0-dev declared `method advance(LrlSide s)` next to the frozen Phase 1 `method advance(Fvg z)`. Both were then one overloaded `advance` family.
* Pine forbids global variables, such as `barEv` reached through `f_emit`, inside overloaded user functions.
* `advance` was the only name declared twice. The Phase 1 and Phase 2 baselines declare every function / method name once.

**CHANGE** (`src/IST.pine`, LRL lines only):
* The LRL method is renamed `advanceLrl`, with its two call sites in the engine run. A comment explains the name.
* The frozen FVG `advance(Fvg z)` and its call site are untouched, so no Phase 1 line changes (ST-15 unchanged).
* No compatibility wrapper is left, and the event bus and `barEv` / `f_emit` are not touched.
* No other LRL method or function name collides: every name is declared once.

**Validation 1.9.1:**
* **New ST-18:** every user-defined function and method name is declared exactly once (the CE10182 guard). It fails on v0.5.0-dev with `['advance']` and passes on the current source and on both frozen baselines.
* **ST-17** order rule and `STATE_CALLS` follow the new name.
* **`tests/test_lrl_pine.py`:** a test that re-introducing the overload is caught.

No test was weakened. The LRL definition and FVG / Phase 1 / Phase 2 behaviour are unchanged.

**TEST:**
* QUICK: **PASS**.
* FULL: **PASS**, exit 0, 213.6 s, **454 passed, 1 skipped**: static 18/18, LRL 77/77, every other section unchanged, regression 5/5 against the frozen baseline. ST-15 still lists the same 11 reviewed Phase 1 lines.
* TradingView LRL-L00 must be re-run on v0.5.1-dev: it is the only proof that every compiler problem is gone.

## v0.5.0-dev — LRL detection in Pine (2026-10-28, branch `lrl/pine`) — EXPERIMENTAL, not frozen · validation 1.9.0

**Decision (user, 2026-10-28):** "The approved LRL oracle and DRIFT correction are accepted. You may now implement LRL in Pine." The goal is DEF-LRL1…8 exactly as the oracle has them, with no tuning. DEF-LRL9 (context classification), CISD, displacement and HTF FVG are not started.

**CHANGE** (`src/IST.pine`, additive):
* **L1:** an own TR average and the 3 / 2 pivot windows; `max_bars_back` 5000 on high / low.
* **L2:** LRL pivots, with no significance test.
* **L3:** UDTs `Lrl` / `LrlSide` and the methods `fits` · `finish` · `advance` · `trim` · `grow` · `promote` · `seed` · `judge`, in side coordinates like the oracle.
* **Engine run:** last, at bar close: ADVANCE both sides, then JUDGE both sides.
* **L5:** the seven event names; LRL event text carries HIGH / LOW and its audit values.
* **L6:** the nearest active LRL per side (polyline through the confirmed pivots, a dashed projection, "LRL"), optional history (10 per side) and D / S / B / E markers, and debug candidates. Everything is rebuilt on the last bar.
* **L7:** debug rows 35–41.
* **Parity capture:** LRL constants on the CAPTURE line; `LH` / `LL` / `KH` / `KL` on every BAR line; warm-up from the LRL dependencies (= 76).
* **Inputs:** Enable LRL engine `[calc]` ON · Show LRL ON · Show historical LRL OFF · Show lifecycle markers OFF · (Developer) Inspect LRL, Draw LRL candidates OFF. The definition constants are not inputs.

**Validation 1.9.0:**
* **ST-08** no longer forbids LRL.
* **ST-14:** the temporary LRL exception is removed (`events.ORACLE_ONLY` is gone).
* **New ST-17:** the constants, 30 formulas and two orders.
* **`tests/test_lrl_pine.py`:** 22 Pine mutations are each caught, and the engine names no Phase 1 / 2 state.
* **Bounded LRL parity** in `parity/capture.py`: events, per-bar boundaries now / previous, candidate counts, with an explicit NOT OBSERVABLE rule.
* **`tests/test_parity_lrl.py`:** 0 DIFFERENCE on faithful synthetic captures, including a window opening inside an active LRL; 8 kinds of injected error are detected.
* **Oracle:** LRL event text identical to Pine's (`n`, `tau`, `pts` / `bnow`, `bprev`, `close`). `LrlSettings.lookback`.
* **Docs:** `docs/LRL.md` §6, and the new `docs/TESTS_LRL.md` (TradingView procedure).

**PHASE 1 / PHASE 2 IMPACT:** none in logic.
* LRL never reads or writes FVG, session, level, BSL / SSL or EQ state (ST-17, S-LRL-4).
* The oracle shows identical Phase 1 / 2 events and state with LRL on and off.
* Regression is unchanged. ST-15 lists the same 11 reviewed Phase 1 lines.
* Shared outputs: "Last events" and the debug Pine Logs now also list LRL events.

**REPAINT IMPACT:** none. Every LRL decision is made at bar close from bars ≤ t. Drawn segments join confirmed pivots, and only the active projection follows the current bar.

**RISKS:** Pine compile and runtime are not verified (LRL-L00 pending). The Pine-only bound `LRL_SPAN` = 4,900 bars per LRL is unreachable on real data.

**TEST:** QUICK during development.
* **FULL: PASS**, exit 0, 199.7 s, **452 passed, 1 skipped** (the paid CSV export). By section:
  * static 17/17 (ST-17 new);
  * Phase 1 and Phase 2 sections unchanged;
  * invariants 53/53 · properties 17/17 · long walks 10/10;
  * regression 5/5 (frozen baseline) · golden 6/6;
  * parity 84/85 (incl. 16 LRL parity tests);
  * LRL 76/76 · LRL study 34/34.
* TradingView LRL-L00 … L12: PENDING (`docs/TESTS_LRL.md`).

## LRL correction — terminal class `LRL_DRIFT` · validation 1.8.0 (2026-10-28, branch `lrl/oracle`) — no indicator change

**Decision (user, 2026-10-28, before any Pine):** a crossing caused by the projected boundary moving into otherwise stationary price is not a SWEEP / BREAK. It is the separate terminal event `LRL_DRIFT`.

**CHANGE** (DEF-LRL5, `docs/LRL.md`):
* With boundary_now = y(t) + τ and boundary_prev = y(t − 1) + τ, both on the geometry known before bar t, an LRL is crossed when `high[t] > boundary_now + ε`. Then:
  * **DRIFT** if `high[t] ≤ boundary_prev + ε`;
  * else **BREAK** if `close[t] > boundary_now + ε`;
  * else **SWEEP**.
* The bullish side mirrors this with y − τ and low / close.
* DRIFT is terminal, never relabelled, and spends its pivots like SWEEP / BREAK. EXPIRED, DROPPED_MEMORY, the spent pivots of a memory-dropped active LRL, and ADVANCE-before-JUDGE are unchanged.
* **Oracle:** `LRL_DRIFT` event and record status; per-side counters drift · sweep · break · expired (replacing "taken").
* **Events:** `events.LRL_TERMINAL`. The seven LRL names for the future Pine `f_evName` are listed in `docs/LRL.md`. They are `ORACLE_ONLY`, so ST-14 excludes them until Pine has them.
* **Invariants:**
  * INV-LRL-05 now classifies DRIFT / SWEEP / BREAK.
  * New **INV-LRL-10**: exactly one terminal class out of DRIFT / SWEEP / BREAK / EXPIRED, never relabelled, and no terminal facts on an active LRL. It has a negative test (a SWEEP appended after a DRIFT).
* **Study:** `Spec.drift` and the spec `APPROVED` (LRL-R + DRIFT), which the oracle now matches. The reviewed study numbers (`RECOMMENDED`) are unchanged.

**Effect:** it relabels crossings only. Confirmations, extensions, spent pivots and every bar are identical (tested on NQ and three walks).
* NQ captures, 27 LRLs: **8 DRIFT · 9 SWEEP · 10 BREAK · 0 EXPIRED**. Before, it was 17 sweeps · 10 breaks.

**TEST:** 11 explicit synthetic cases in `tests/test_lrl.py`:
1. bearish drift;
2. bearish sweep;
3. bearish break;
4. bullish drift;
5. bullish sweep;
6. bullish break;
7. equality at the previous boundary (exact boundaries with τ = 1.0), plus one tick beyond, plus exactly at the boundary;
8. steep one-bar projection (DRIFT / SWEEP / BREAK);
9. extension immediately before a drift: the new geometry is used from the next bar, and the drift bar differs from the old geometry's;
10. drift consumes pivots, expiry does not;
11. a terminal event is never relabelled.

Also: drift only relabels (NQ, walks); NQ termination counts; the event names prepared for Pine.

**Results:**
* `python -m validation --phase lrl` (quick): **PASS**.
* FULL: **PASS**, exit 0, 200.6 s, **411 passed, 1 skipped**: LRL detection 52/52, invariant detectors 53/53, every other section unchanged. Regression 5/5 against the frozen baseline.

**Unchanged:** `src/IST.pine`, Phase 1, Phase 2 (byte-identical with LRL on), the frozen tags, the regression baseline and parity.

## LRL detection — reference model + validation 1.7.0 (2026-10-28, branch `lrl/oracle`) — no indicator change

**Decision (user, 2026-10-28):** "Definition approved. Proceed with the reference model/oracle + validation, but not Pine yet." The approved definition is LRL-R (`docs/STUDY_LRL.md` §H) with the recommended answers of §K.

**CHANGE:**
* `docs/LRL.md` is the approved specification: DEF-LRL1…8 (detection), DEF-LRL9 (target-quality context, a future requirement), events, non-repaint guarantees and the validation map.
* `validation/models/lrl.py` is the oracle. It is the opt-in module `lrl` (`Settings(modules=…+("lrl",))`), constants in `LrlSettings`. Its events are `LRL_CONFIRMED`, `LRL_EXTENDED` (repeats, so it is outside ONCE), `LRL_SWEEP`, `LRL_BREAK`, `LRL_EXPIRED` and `LRL_DROPPED_MEMORY`. They are appended after every existing type, so existing ranks are unchanged.
* One definition detail is settled here: when memory forces out an *active* LRL, its points become spent, so its id can never return.
* Invariants INV-LRL-01…09, each with a negative test.
* `tests/test_lrl.py` (32 tests):
  * the approved study engine is reproduced exactly (17 scenarios, the NQ captures with 27 LRLs, three walks);
  * event fields;
  * Phase 1/2 are identical with LRL on;
  * the module is opt-in;
  * the memory path.
* `fuzz/test_lrl_properties.py`:
  * invariants, mirror symmetry, translation invariance, no lookahead and Phase 1/2 identity, on random candles and generated staircases;
  * LRL long walks.
* Report section "LRL detection", and `--phase lrl` (LRL, the LRL study and the common checks).
* ST-14 (Pine event names = oracle event names) now excludes `events.ORACLE_ONLY`, the LRL types Pine does not have yet. Empty that set when Pine gains LRL.

**REASON:** validate the approved definition before any Pine code, as for Phase 2.

**RISKS:** none for the indicator.
* `src/IST.pine` is unchanged (ST-08 still forbids LRL identifiers), and so are Phase 1 and Phase 2, the frozen tags, the regression baseline (the module is off by default, and the serialised settings of default cases are unchanged) and Pine parity.
* `Settings` gained an `lrl` field. `to_dict()` includes it only when the module runs.

**TEST:** FULL **PASS**, exit 0, 195.8 s: **390 passed, 1 skipped** (the paid CSV export).
* Unchanged: static 16/16, Phase 1 and Phase 2 sections, regression 5/5, golden 6/6, parity 68/69.
* Invariant detectors 52/52, properties 17/17, long walks 10/10.
* LRL detection 32/32, LRL study 34/34.
* The 9 LRL detectors fire on corrupted states.

## LRL study — user clarification: detection ≠ target quality (2026-10-28, branch `research/lrl`) — no indicator change

**CHANGE.** `docs/STUDY_LRL.md` records the user's clarification. LRL **detection** (the diagonal failure-swing structure, from bars alone) and LRL **target quality** stay separate.
* No HTF FVG, DOL, displacement, delivery or other context is needed to create an LRL.
* A singular swing is not an LRL; two points remain an internal candidate; three compatible failure swings are the minimum.
* A future context layer (L4) may classify an existing LRL as LOW RESISTANCE / NEUTRAL / HIGH RESISTANCE. It is kept as a requirement (DEF-LRL9, read-only, future INV-LRL-11) and **not implemented**.

**TEST.** A new scenario, "two failure swings only (internal candidate)", plus `test_two_points_stay_an_internal_candidate` and `test_detection_reads_no_context`. That makes 34 tests. The detection definition is unchanged; every existing number is identical.

## LRL research study — validation 1.6.0 (2026-10-28, branch `research/lrl`) — no indicator change, for review

**CHANGE.** Research and specification only, at the user's request ("Do NOT implement LRL in IST.pine yet"): `docs/STUDY_LRL.md`. It covers the formal semantics of a diagonal failure-swing LRL, seven candidate definitions with formulas and pseudocode, pros, cons and failure modes, the measurements on real NQ (both evidence captures merged, 1,639 bars) and on a random-walk null, 16 synthetic scenarios, answers to the 15 study questions, a proposed DEF-LRL1…8, a validation plan and open questions.
* `validation/studies/lrl.py`: the study engine, tables and charts (`docs/study_lrl/lrl-0.svg`, `lrl-2.svg`, `lrl-R.svg`).
* `validation/tests/test_lrl_study.py`: 31 tests in the new report section "LRL research study". They cover the scenarios, each guard rule (mutation), mirror symmetry, prefix invariance (no lookahead), record invariants, failure swings ≠ C1, 3m/5m, and the frozen EQH untouched.

**Key finding:** C1 dominance rejects every failure swing. 0 of 56 LRL points 2…n are BSL/SSL, and a C1-only source finds no LRL. LRL therefore needs its own (intermediate) pivot source.

**Unchanged:** `src/IST.pine` (ST-08 still forbids LRL identifiers), the oracle, Phase 1, Phase 2 and the tag `PHASE2_BASELINE_v0.4.4-dev`. Nothing is approved, and nothing is merged.

## Phase 2 FREEZE — IST v0.4.4-dev = `PHASE2_BASELINE_v0.4.4-dev` (2026-10-28) — no indicator change

**Decision (user, 2026-10-28):** freeze Phase 2 with **C1** (DEF-L2 = reaction AND dominance) as the approved liquidity significance definition. Full record: `docs/PHASE2_FREEZE_REPORT.md`.

**Evidence:**
* TradingView on v0.4.4-dev (user): L00, L45, L46, L47 and L48 **PASS**.
* L48 is a bounded Pine-Log parity on a real 1,000-bar NQ1! 1m capture (Balanced, W 30): 1,000 bars × 9 series (dominance references included) and 1,049 events. Result: 29 MATCH, **0 DIFFERENCE**, 6 NOT OBSERVABLE (bounded-window limits). Swings 38/39 · 28/45 and FVG 90/90/43, identical in Pine and the oracle.
* The FULL validation passes (totals in the report).

**What this commit freezes or adds:**
* `src/IST.pine` is **byte-identical** to the validated v0.4.4-dev (commit 5ec9a33), SHA-256 `b97f4a11…5664871c`. The version label stays `v0.4.4-dev`, so the frozen bytes are exactly the tested bytes.
* `releases/v0.4.4-dev/`: a read-only exact copy (source, docs, report) with `SHA256SUMS.txt`, as for Phase 1. Annotated tag `PHASE2_BASELINE_v0.4.4-dev`.
* `validation/parity/evidence/` (validation 1.5.1):
  * the new v0.4.4-dev capture, the regression asset of C1 (`test_v044_capture_parity_c1_frozen_baseline`);
  * the v0.4.3-dev capture, moved here with its version in the name (byte-identical: same SHA-256), as historical evidence of the definition before C1;
  * `SHA256SUMS.txt` (checked by `test_evidence_captures_are_unchanged`) and `README.md`.
* `python -m validation` also picks up `pine-logs-*.csv`, the name TradingView gives the file it saves.

**Unchanged:** Phase 1 behaviour and `PHASE1_BASELINE_v0.3.2` (1247abc); W, k, EQ tolerance and pivot parameters. Phase 3 is not started, and nothing is merged into `main`.

## v0.4.4-dev — C1: liquidity significance = rejection AND dominance (2026-10-28, branch `tooling/validation-agent`) — EXPERIMENTAL

**CHANGE** (DEF-L2, approved by the user 2026-10-28 from `docs/STUDY_LIQUIDITY_SIGNIFICANCE.md`). A confirmed swing becomes BSL/SSL only when both conditions hold:
* (a) the existing reaction ≥ k × TR average (unchanged);
* (b) **dominance:** no high in the W bars *before the swing bar* (X−W … X−1; anchored to the origin, the right bars excluded) above the swing high + EQ tolerance. Lows are mirrored. Only a strictly greater extreme rejects.

Presets are now (left, right, k, **W**): Aggressive 3/2/0.5/**10**, Balanced 5/3/1.0/**30**, Strict 10/5/2.0/**60**. Custom has no W input, so it has no dominance. W is not a user input. k and W were not tuned.

**Implementation:**
* **Rule:** `domHiRef = ta.highest(high, W)[LIQ_R + 1]`, read only when X ≥ W. A level is dominant iff `domHiRef <= swHiPx + EQ_TOL + EPS`, with the EQ tolerance and float margin. Lows are mirrored.
* **Warm-up:** fewer than W bars before X means warm-up (neither PASS nor REJECT), like the TR average.
* **Rejection diagnostics:** disjoint counters for reaction only, dominance only and both. Debug rows 22–23 read `REJECT n (x%) = reaction a + dominance b + both c`.
* **Debug and Data Window output:**
  * row 21 shows the dominance window;
  * 2 Data Window plots show the dominance reference high and low (20 plots in all);
  * the Parity capture writes `w=` on the CAPTURE line and `DH=` / `DL=` on each BAR line.
* **Capture warm-up:** taken from the dependency graph, max(fvgLen + 2, max(14, L, W) + R). That is Balanced 33, Strict 65, Aggressive 16.

**WHY.** On real NQ 1m (1,017 exact bars, Pine ↔ Python parity PASS), the reaction floor passed ~95 % of pivots. That reaction is large by construction, so the floor is not a significance test.

**PHASE 1 IMPACT.** None. FVG, session and level events are identical with C1 on or off (tested on random walks and the NQ capture). The Phase 1 baseline guard is unchanged.

**REPAINT IMPACT.** None:
* only bars X − W … t are read;
* the confirmation bar is unchanged;
* a decision is identical when later bars are cut (tested) and when the history starts earlier (tested).

**SEMANTICS KEPT.**
* C1 levels are a strict subset of the v0.4.3 levels, and every kept level is taken, swept or broken identically (tested).
* The EQ rules are unchanged. Clusters re-form among the remaining levels. The EQ tolerance inside dominance lets an equal second top still qualify (tested).

**REGRESSION TESTS.**
* 30 new tests (`validation/tests/test_liquidity_dominance.py`) and 2 new invariants with negative tests:
  * INV-LIQ-11: dominant at birth;
  * INV-LIQ-12: counter partition.
* A new static check, ST-16, covers the exact dominance lines in Pine.
* Mutation tests: ≥ at the boundary, the window anchored to confirmation, the tolerance dropped, dominance not applied. Each one is caught.
* Regression baseline refreshed after review. Every diff was in the liquidity / EQ families, plus the new `dom` setting: 433 BSL/SSL events removed, EQ clusters re-formed, state counters. There were no FVG, session or level diffs, no added level and no timing change.

**TradingView:** L00 must be re-run, then L45–L48. C1 is not frozen before L48: a new 1,000-bar capture with parity at 0 DIFFERENCE. The v0.4.3-dev capture stays committed as historical evidence (`test_v043_capture_parity_is_preserved_under_its_own_definition`).

## Tooling · validation agent 1.5.0 (2026-10-28, branch `tooling/validation-agent`) — C1 in the oracle and the parity tools

* **Oracle:**
  * `LiqSettings.dom` (W) and presets of 4 numbers;
  * `dominance_ref()` / `dominant()`;
  * REJECT counters by reason;
  * `lookback` properties, which derive the capture warm-up from the dependency graph.
* **Explicit left/right/k without a preset is Custom: no dominance.** So scenario and golden cases keep their definition, and the legacy models (v0.4.0/v0.4.1) are compared with dominance off.
* **Parity:**
  * the capture reads `w=` and `DH=` / `DL=`. A capture without `w=` (IST before v0.4.4-dev) is replayed with the definition its build used, and its dominance series is NOT OBSERVABLE;
  * the CSV parity has 2 more Data Window series;
  * manual parity checks REJECT = reaction + dominance + both.
* **The stored v0.4.3-dev capture still passes under its own definition.** A second test forces C1 on it and shows that every difference is the intended one: a swing Pine kept and C1 rejects, plus that level's own events. No swing appears, and no event is missing.

## Tooling · validation agent 1.4.0 (2026-10-28, branch `tooling/validation-agent`) — liquidity significance study — no indicator change

* `docs/STUDY_LIQUIDITY_SIGNIFICANCE.md`: Phase 2 significance study (A–H), **for review; nothing approved or implemented**.
  * Finding: on real NQ 1m (1,017 exact bars), the DEF-L2 reaction floor k = 1 sits at the 10th percentile of a reaction that is large by construction. NQ pivots are statistically indistinguishable from random-walk pivots.
  * Recommendation: add a dominance condition (W = 10 / 30 / 60 bars, EQ tolerance included) and keep k. It is a strict subset of today's levels with identical take / sweep / break.
* `python -m validation.studies.liquidity_significance [--grid] [--noise]` runs:
  * feature distributions and outcome diagnostics;
  * candidate definitions replayed through the oracle's own liquidity engine via a study subclass (the oracle is unchanged);
  * a sensitivity grid, halves of the day, and a random-walk null.
* The real 1,000-bar TradingView capture (IST v0.4.3-dev, bounded Pine-Log parity PASS) is committed in `validation/studies/data/`. `test_real_nq_capture_parity_is_preserved` keeps that parity as a regression.
* 11 new tests (`tests/test_study_significance.py` and the preserved-parity test):
  * the study engine reproduces the oracle;
  * dominance boundaries;
  * subset and identical takes on NQ and random walks.
* `src/IST.pine`, the oracle, the presets and `PHASE1_BASELINE_v0.3.2` are unchanged.

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
