# IST — ICT Structure Toolkit (TradingView, Pine Script v6)

A non-repainting ICT market-structure toolkit, tuned for NQ futures on 1m, 3m and 5m charts. It is built in stages. Each phase is validated and frozen before the next one starts.

| File | Purpose |
|---|---|
| `src/IST.pine` | The indicator. Paste it into the TradingView Pine Editor. |
| `docs/ARCHITECTURE.md` | Architecture, Pine limitations, anti-repaint strategy, budgets, and exact definitions (Appendix A). |
| `docs/TESTS.md` | Acceptance checklist for every module, plus the non-repaint protocol. |
| `docs/LIQUIDITY.md` | Phase 2 liquidity engine: exact definitions (DEF-L), timing, budgets, limitations. |
| `docs/LRL.md` | LRL detection (diagonal failure-swing liquidity), DEF-LRL1…9 (approved) and its Pine implementation (§6). The research behind it is in `docs/STUDY_LRL.md`. |
| `docs/HTF_FVG.md` | HTF Fair Value Gaps (15m · 30m · 1H · 4H · 1D · 1W), DEF-B0…B6 (approved 2026-10-29, decisions D1–D10), timing, seeds, reload consistency, parity capture. Design history: `docs/HTF_FVG_DESIGN.md`. |
| `docs/CISD.md` | CISD (change in state of delivery), DEF-CISD1…9: CISD-R approved 2026-10-30, explicit UNKNOWN start, identity side + origin time, events, record facts, 200-bar display guard (not part of the definition), validation T1–T18, and the Pine implementation (§5: incremental, no leg-length limit, capture). |
| `docs/CISD_FREEZE_REPORT.md` | CISD freeze (v0.7.1-dev): identity and hashes, evidence (real parity, human goldens, reload / determinism), the frozen definition, guarantees, open items, known limitations. |
| `docs/AUDIT_CISD_HUMAN.md` | CISD human / reference audit (2026-10-30): the user's screenshots and the reference video against CISD-R. 2 exact matches, 0 mismatches, keep CISD-R; visual differences only. |
| `docs/IFVG_REQUIREMENTS.md` | IFVG research requirements (no rule decided): observations from the references, the questions for a future study, and an audit of the FVG identity already stored for inversion tracking. |
| `docs/TESTS_CISD.md` | CISD tests: automated S-CISD, TradingView CISD-L00…L12 (L10 = Pine ↔ oracle parity, L11 = the user's golden cases: the freeze criteria). |
| `docs/STUDY_CISD.md` | CISD research (A–N): five candidate definitions, real NQ vs random walk, the recommendation CISD-R (approved), decisions D-C1…D-C12. |
| `docs/DISPLACEMENT.md` | Displacement, DEF-DISP1…9: DISPLACEMENT-R **proposed** 2026-11-01 (awaiting approval): one closed candle, body ≥ 1.5 × TR average, close in the outer quarter, close beyond the previous candle; FVG fact as metadata; oracle only, no Pine. |
| `docs/STUDY_DISPLACEMENT.md` | Displacement research (A–M): nine candidate definitions on 63 h of real NQ / MNQ 1m, thresholds = Tukey fences (not tuned on outcomes), noise controls, CISD and FVG relationships, the recommendation DISPLACEMENT-R and open decisions M1…M11. |
| `docs/TESTS_HTF.md` | HTF FVG tests: automated S-HTF, TradingView HTF-L00…L14 (L12 = Pine ↔ oracle parity, the freeze criterion). |
| `docs/TESTS_LRL.md` | LRL tests: automated S-LRL, TradingView LRL-L00…L12 (L11 = Pine ↔ oracle parity, the freeze criterion). |
| `docs/TESTS_PHASE2.md` | Phase 2 tests (S-01…S-13, L00–L48) and the manual validation procedure. |
| `validation/` | Validation agent: Python reference model (oracle), scenarios, invariants, property/stateful fuzzing, regression, golden dataset, Pine parity. Run `python -m validation`; see `validation/README.md`. |
| `requirements-dev.txt` | Development-only dependencies of the validation agent (pytest, Hypothesis). |
| `releases/v0.3.2/` | Frozen Phase 1 baseline (read-only, SHA-256). Git tag `PHASE1_BASELINE_v0.3.2`. |
| `releases/v0.4.4-dev/` | Frozen Phase 2 baseline (read-only, SHA-256). Git tag `PHASE2_BASELINE_v0.4.4-dev`. Report: `docs/PHASE2_FREEZE_REPORT.md`. |
| `CHANGELOG.md` | CHANGES / REASON / RISKS / TEST for every revision. |

## Install

1. In TradingView, open **Pine Editor**, choose **Open → New blank indicator**, and replace its contents with `src/IST.pine`.
2. Click **Save**, then **Add to chart**. Use NQ1! or the front-month contract with standard candles.
3. For alerts, create an alert with the condition **IST → Any alert() function call**.

## Status

| Phase | Content | State |
|---|---|---|
| 0 | Architecture (7 layers, calculation independent of visibility) | adopted |
| 1 | FVG engine, PDH/PDL, PWH/PWL, sessions, FVG alerts, diagnostics | **v0.3.2 frozen safety baseline · runtime 8/50 PASS, 1 FAIL (T03, re-test), 41 pending** |
| 2 | Swing liquidity, BSL/SSL, taken, sweep vs break, EQH/EQL | **v0.4.4-dev FROZEN Phase 2 baseline (2026-10-28) · tag `PHASE2_BASELINE_v0.4.4-dev` · copy in `releases/v0.4.4-dev/` · significance C1 = reaction AND dominance (W 10/30/60) · TradingView L00, L45–L48 PASS (L48: 1,000-bar real-NQ parity, 0 DIFFERENCE); L01–L44 not recorded one by one · `docs/PHASE2_FREEZE_REPORT.md`** |
| LRL | Diagonal failure-swing liquidity (detection only; target-quality context later) | **v0.5.3-dev EXPERIMENTAL (not frozen) · one straight line per LRL · LRL-L00 compile PASS (v0.5.1-dev); historical-drawing retest pending · in Pine, oracle + validation 1.9.3 (LRL unchanged in v0.6.0-dev; neutral grey) · terminal classes DRIFT / SWEEP / BREAK / EXPIRED · TradingView LRL-L00…L12 pending (`docs/TESTS_LRL.md`) · `docs/LRL.md`** |
| HTF FVG | Fair value gaps of the 15m / 30m / 1H / 4H / 1D / 1W candles (Module B, beside the frozen Phase 1 engine) | **v0.6.2-dev EXPERIMENTAL (not frozen) · v0.6.0-dev compiles and runs (user, 2026-10-30); v0.6.1-dev / v0.6.2-dev = readability passes (labels, LRL line, grey-brown HTF palette for a `#C2BAAE` background) · in Pine, oracle + validation 1.10.1 · non-repainting ([1] + lookahead_on) · own-timeframe invalidation · seeds · ≤ 12 neutral grey boxes, timeframe label bottom-right · Phase 1 `Show FVGs` default OFF (reviewed deviation) · TradingView HTF-L00…L14 pending (`docs/TESTS_HTF.md`) · `docs/HTF_FVG.md`** |
| CISD | Change in state of delivery (detection only; context later) | **v0.7.1-dev FROZEN CISD baseline (2026-10-31) · tag `CISD_BASELINE_v0.7.1-dev` · copy in `releases/v0.7.1-dev/` · real capture 0 DIFFERENCE (CISD-L10) · human goldens PASS (CISD-L11) · reload / determinism PASS (CISD-L12, automated + manual) · CISD-R approved (2026-10-30) · in Pine (incremental, no leg-length limit), oracle + validation 1.15.0 · events CISD_CONFIRMED / CISD_DROPPED_MEMORY · current CISD only, 200-bar display guard · TradingView CISD-L00, L10–L12 PASS; L01–L09 not recorded one by one (`docs/TESTS_CISD.md`) · `docs/CISD_FREEZE_REPORT.md` · `docs/CISD.md`** |
| 3 | Displacement | **research + oracle (2026-11-01, validation 1.16.0): DISPLACEMENT-R proposed, awaiting approval · no Pine · independent of CISD (frozen) · `docs/STUDY_DISPLACEMENT.md`, `docs/DISPLACEMENT.md`** |
| 4 | IFVG | design in Appendix A |
| 5 | Quality score, confluence dashboard, UX | later |
