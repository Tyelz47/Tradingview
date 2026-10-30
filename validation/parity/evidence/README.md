# Parity evidence: real TradingView captures

These are the exact files TradingView saved from the Pine Logs pane (IST Parity capture). They are kept **byte for byte**: never edit, re-save or reformat them. `SHA256SUMS.txt` holds their hashes, and `tests/test_parity_capture.py::test_evidence_captures_are_unchanged` checks them on every run. The tests and the tooling find them through `validation.parity.CAPTURE_V043` / `CAPTURE_V044`.

| File | IST build | Liquidity definition | Window (New York) | Result | Role |
|---|---|---|---|---|---|
| `ist-v0.4.3-dev_nq1-1m_capture-1000_2026-10-27.csv` | v0.4.3-dev | DEF-L2 before C1: reaction only. No `w=` in its CAPTURE line | 2026-10-27 03:38 → 21:34 (1,017 bars, warm-up 17) | PASS: 1,000 bars × 7 series, 1,258 events, 0 DIFFERENCE. Swings 71/7 · 68/1 | **Historical evidence** of the previous definition. Replayed with that definition (`test_v043_capture_parity_is_preserved_under_its_own_definition`); forced to C1 it shows only the intended change (`test_v043_capture_under_c1_differs_only_by_the_expected_definition_change`). Source of `docs/STUDY_LIQUIDITY_SIGNIFICANCE.md` |
| `ist-v0.4.4-dev_nq1-1m_capture-1000_2026-10-28.csv` | v0.4.4-dev | **C1** (reaction AND dominance), Balanced: left 5 · right 3 · k 1 · W 30 · EQ 4 ticks · min 2 | 2026-10-27 13:44 → 2026-10-28 07:56 (1,033 bars, warm-up 33) | PASS: 1,000 bars × 9 series (dominance references included), 1,049 events, 29 MATCH · 0 DIFFERENCE · 6 NOT OBSERVABLE. Swings 38/39 · 28/45, FVG 90/90/43 | **Phase 2 freeze evidence** (TESTS_PHASE2 L48) and the regression asset of the frozen C1 definition (`test_v044_capture_parity_c1_frozen_baseline`) |

| `ist-v0.7.0-dev_mnq-1m_capture-1000_2026-10-30.csv` | v0.7.0-dev (the user's UTF-8 save of `pine-logs-IST_9c917.csv`) | C1 Balanced; LRL, HTF FVG, CISD on; MNQ (CME_MINI:MNQZ2026, settlement as close) | 2026-10-29 21:48 → 2026-10-30 15:43 (1,076 bars, warm-up 76) | FAIL by design of the old build: Phase 1 / 2 and HTF 0 DIFFERENCE; CISD 81 DIFFERENCE, all on bk; LRL 330 DIFFERENCE | **Defect evidence**: Pine reads a user series' history inside a function per CALL, not per bar (`cisdTra[1]` in `confirmCisd`, `lrlTra[bar_index - xa]` in `seed` / `fits`). Fixed in v0.7.1-dev (ST-21); the diagnosis is pinned by `tests/test_parity_v070_evidence.py`. It cannot validate v0.7.1-dev: a new capture is needed |

**Cross-load check.** The two captures come from two separate TradingView loads. They share 411 bars (2026-10-27 13:44 → 21:34), and the OHLC of all 411 is identical.

**Replay a file:**

```bash
python -m validation.parity --capture "validation/parity/evidence/ist-v0.4.4-dev_nq1-1m_capture-1000_2026-10-28.csv"
```
