# IST — ICT Structure Toolkit (TradingView, Pine Script v6)

A non-repainting ICT market-structure toolkit, tuned for NQ futures on 1m, 3m and 5m charts. It is built in stages. Each phase is validated and frozen before the next one starts.

| File | Purpose |
|---|---|
| `src/IST.pine` | The indicator. Paste it into the TradingView Pine Editor. |
| `docs/ARCHITECTURE.md` | Architecture, Pine limitations, anti-repaint strategy, budgets, and exact definitions (Appendix A). |
| `docs/TESTS.md` | Acceptance checklist for every module, plus the non-repaint protocol. |
| `docs/LIQUIDITY.md` | Phase 2 liquidity engine: exact definitions (DEF-L), timing, budgets, limitations. |
| `docs/LRL.md` | LRL detection (diagonal failure-swing liquidity), DEF-LRL1…9 (approved) and its Pine implementation (§6). The research behind it is in `docs/STUDY_LRL.md`. |
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
| LRL | Diagonal failure-swing liquidity (detection only; target-quality context later) | **v0.5.1-dev EXPERIMENTAL (not frozen; v0.5.0-dev failed to compile: CE10182, fixed) · in Pine, oracle + validation 1.9.1 · terminal classes DRIFT / SWEEP / BREAK / EXPIRED · TradingView LRL-L00…L12 pending (`docs/TESTS_LRL.md`) · `docs/LRL.md`** |
| 3 | Displacement, CISD | design in Appendix A |
| 4 | IFVG, HTF FVG | design in Appendix A |
| 5 | Quality score, confluence dashboard, UX | later |
