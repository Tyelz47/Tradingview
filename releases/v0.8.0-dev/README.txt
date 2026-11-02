DISPLACEMENT BASELINE — IST v0.8.0-dev (frozen 2026-11-02)

Exact byte copy of the IST build whose displacement module (DISPLACEMENT-R, single candle, DEF-DISP1…DISP9)
passed real TradingView Pine-Log parity with 0 DIFFERENCE (DISP-L10), the human / golden validation (DISP-L11)
and the reload check (DISP-L12), with its definition, research study, tests document, freeze report and oracle
(oracle/displacement.py = validation/models/displacement.py), the human golden dataset (golden/displacement/ =
validation/golden/human/displacement/) and the real parity evidence, byte for byte
(evidence/ist-v0.8.0-dev_mnq-1m-replay_capture-1000_2026-10-30.csv = the user's pine-logs-IST_43f18.csv). Report: docs/DISPLACEMENT_FREEZE_REPORT.md.
Only the displacement module is frozen by this baseline; LRL and HTF FVG in the same file stay experimental,
CISD stays frozen under CISD_BASELINE_v0.7.1-dev. No multi-bar displacement in this baseline.
Do not edit these files. Verify integrity with:  sha256sum -c SHA256SUMS.txt
Tests, static checks and tooling stay in the repository; their hashes: MANIFEST.txt (from the repo root:
  sha256sum -c releases/v0.8.0-dev/MANIFEST.txt).
Git: tag DISPLACEMENT_BASELINE_v0.8.0-dev (branch displacement/pine).
Rollback: copy releases/v0.8.0-dev/src/IST.pine into the Pine Editor, or git checkout DISPLACEMENT_BASELINE_v0.8.0-dev
Earlier baselines: releases/v0.3.2/ (PHASE1_BASELINE_v0.3.2), releases/v0.4.4-dev/ (PHASE2_BASELINE_v0.4.4-dev),
releases/v0.7.1-dev/ (CISD_BASELINE_v0.7.1-dev), unchanged.
