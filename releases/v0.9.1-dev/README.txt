IFVG BASELINE — IST v0.9.1-dev (frozen 2026-11-03)

Exact byte copy of the IST build whose IFVG module (IFVG-R, DEF-IFVG1…IFVG9) passed real TradingView Pine-Log parity
with 0 DIFFERENCE (IFVG-L10), the human / golden validation (IFVG-L11) and the reload / determinism validation
(IFVG-L12: automated, and the user's manual TradingView reload check), with its definition, research study, tests
document, freeze report, requirements note and oracle (oracle/ifvg.py = validation/models/ifvg.py), the human golden
dataset (golden/ifvg/ = validation/golden/human/ifvg/) and the real parity evidence, byte for byte
(evidence/ist-v0.9.1-dev_mnq1-1m_capture-1000_2026-11-02.csv = the user's pine-logs-IST_faf9f.csv).
Report: docs/IFVG_FREEZE_REPORT.md (frozen definition §3, accepted limitations §6).
Only the IFVG module is frozen by this baseline; LRL and HTF FVG in the same file stay experimental, CISD stays frozen
under CISD_BASELINE_v0.7.1-dev and displacement under DISPLACEMENT_BASELINE_v0.8.0-dev. No HTF IFVG, renderer, alert,
context or scoring in this baseline.
Do not edit these files. Verify integrity with:  sha256sum -c SHA256SUMS.txt
Tests, static checks, invariants and tooling stay in the repository; their hashes: MANIFEST.txt (from the repo root:
  sha256sum -c releases/v0.9.1-dev/MANIFEST.txt).
Git: tag IFVG_BASELINE_v0.9.1-dev (branch ifvg/pine).
Rollback: copy releases/v0.9.1-dev/src/IST.pine into the Pine Editor, or git checkout IFVG_BASELINE_v0.9.1-dev
Earlier baselines: releases/v0.3.2/ (PHASE1_BASELINE_v0.3.2), releases/v0.4.4-dev/ (PHASE2_BASELINE_v0.4.4-dev),
releases/v0.7.1-dev/ (CISD_BASELINE_v0.7.1-dev), releases/v0.8.0-dev/ (DISPLACEMENT_BASELINE_v0.8.0-dev), unchanged.
