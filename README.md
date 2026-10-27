# IST — ICT Structure Toolkit (TradingView, Pine Script v6)

A non-repainting ICT market-structure toolkit, tuned for NQ futures on 1m, 3m and 5m charts. It is built in stages. Each phase is validated and frozen before the next one starts.

| File | Purpose |
|---|---|
| `src/IST.pine` | The indicator. Paste it into the TradingView Pine Editor. |
| `docs/ARCHITECTURE.md` | Architecture, Pine limitations, anti-repaint strategy, budgets, and exact definitions (Appendix A). |
| `docs/TESTS.md` | Acceptance checklist for every module, plus the non-repaint protocol. |
| `CHANGELOG.md` | CHANGES / REASON / RISKS / TEST for every revision. |

## Install

1. In TradingView, open **Pine Editor**, choose **Open → New blank indicator**, and replace its contents with `src/IST.pine`.
2. Click **Save**, then **Add to chart**. Use NQ1! or the front-month contract with standard candles.
3. For alerts, create an alert with the condition **IST → Any alert() function call**.

## Status

| Phase | Content | State |
|---|---|---|
| 0 | Architecture (7 layers, calculation independent of visibility) | adopted |
| 1 | FVG engine, PDH/PDL, PWH/PWL, sessions, FVG alerts, diagnostics | **v0.3.2 frozen candidate · runtime 8/50 PASS, 1 FAIL (T03, re-test), 41 pending · scope frozen** |
| 2 | Swing liquidity, BSL/SSL, sweeps vs runs, EQH/EQL | design in Appendix A |
| 3 | Displacement, CISD | design in Appendix A |
| 4 | IFVG, HTF FVG | design in Appendix A |
| 5 | Quality score, confluence dashboard, UX | later |
