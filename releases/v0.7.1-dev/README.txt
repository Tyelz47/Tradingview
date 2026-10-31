CISD BASELINE — IST v0.7.1-dev (freeze prepared 2026-10-31)

Exact byte copy of the IST build whose CISD module (CISD-R, DEF-CISD1…CISD9) passed real TradingView
Pine-Log parity with 0 DIFFERENCE (CISD-L10) and the human / golden validation (CISD-L11), with its
definition, tests document, freeze report, research study, human audit and oracle (oracle/cisd.py =
validation/models/cisd.py). Report: docs/CISD_FREEZE_REPORT.md.
Only the CISD module is frozen by this baseline; LRL and HTF FVG in the same file stay experimental.
Do not edit these files. Verify integrity with:  sha256sum -c SHA256SUMS.txt
Tests, goldens and parity evidence stay in the repository; their hashes: MANIFEST.txt (from the repo root:
  sha256sum -c releases/v0.7.1-dev/MANIFEST.txt).
Git: tag CISD_BASELINE_v0.7.1-dev (branch cisd/pine), created after the manual CISD-L12 reload check.
Rollback: copy releases/v0.7.1-dev/src/IST.pine into the Pine Editor, or git checkout CISD_BASELINE_v0.7.1-dev
Earlier baselines: releases/v0.3.2/ (PHASE1_BASELINE_v0.3.2), releases/v0.4.4-dev/ (PHASE2_BASELINE_v0.4.4-dev), unchanged.
