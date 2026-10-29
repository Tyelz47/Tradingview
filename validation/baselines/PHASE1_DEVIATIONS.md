# Reviewed deviations from `PHASE1_BASELINE_v0.3.2`

ST-15 checks every Phase 1 line that has since been removed or changed against `phase1_removed_lines.txt`. This file records **why**.

| # | since | line (as in the baseline) | change | reviewed by | effect |
|---|---|---|---|---|---|
| 1–11 | v0.4.0-dev … v0.4.4-dev | header, TT_MIN, the Debug-mode tooltip, `f_evName` / `f_evText` lines, the alert key, the debug table size and rows | text needed by the Phase 2 additions (liquidity names, debug rows, side in the event text, `dir` in the alert key) | user, with each Phase 2 release | none on Phase 1 calculation, events or alerts (Phase 1 regression and the Phase 1 sections of the validation unchanged) |
| 12 | **v0.6.0-dev** (2026-10-29) | `fvgShow = input.bool(true, "Show FVGs", …)` | **default ON → OFF**, and a tooltip | **user decision D9** (HTF FVG design approval, 2026-10-29) | **display only**. The chart-timeframe FVG engine still computes every record, milestone and event, and its alerts are unchanged (still ON by default). The user-facing FVGs are now the HTF FVGs (`docs/HTF_FVG.md`). Switching Show FVGs back ON restores the v0.3.2 chart exactly |
