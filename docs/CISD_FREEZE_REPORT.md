# IST · CISD freeze report — v0.7.1-dev

**Status: FROZEN on 2026-10-31. Annotated tag `CISD_BASELINE_v0.7.1-dev` on commit `cb2ee9700068f1e7697fe80bcc1f5fe80eb99538`.**
* CISD-L00, CISD-L10, CISD-L11 and CISD-L12 (automated and the user's manual TradingView reload check) pass.
* The tag was created after the user's reload check passed and the user's go. The tagged commit's own documents still read "freeze prepared / manual pending"; this status was recorded in a later documentation-only commit, and the tag message records the manual result.
* This freezes the **CISD module** only:
  * LRL and HTF FVG in the same file stay EXPERIMENTAL;
  * the Phase 1 and Phase 2 baselines are untouched.

## 1 · Identity

| Item | Value |
|---|---|
| Build | IST **v0.7.1-dev** (label kept: the frozen bytes are the bytes captured in TradingView) |
| Source | `src/IST.pine`, SHA-256 `29dd2bfd243f549d1e68db3daf941b343e4f3e3f3ffb25ebf2678008db4afbbf`, unchanged since commit `b34a194` (the build in the real capture, `build=v0.7.1-dev`) |
| Oracle | `validation/models/cisd.py` (`CisdEngine` = the definition; `CisdStack` = Pine's formulation, proven equal), SHA-256 `73cb78793c449f3e07e85408af558895bd5155d80c4c297d2604d34643f4364e` |
| Git tag | **`CISD_BASELINE_v0.7.1-dev`** (annotated, the convention of `PHASE1_BASELINE_v0.3.2` / `PHASE2_BASELINE_v0.4.4-dev`) on the freeze commit `cb2ee97` of branch `cisd/pine`. Not merged into `main` |
| Read-only copy | `releases/v0.7.1-dev/` with `SHA256SUMS.txt` (inside the folder: `sha256sum -c SHA256SUMS.txt`) and `MANIFEST.txt` (tests, goldens, evidence, from the repository root) |
| Baselines | `PHASE1_BASELINE_v0.3.2` and `PHASE2_BASELINE_v0.4.4-dev` unchanged; the Phase 1 diff guard (ST-15) passes |
| Validation tooling | 1.15.0 |

**Rollback:** `git checkout CISD_BASELINE_v0.7.1-dev`, or paste `releases/v0.7.1-dev/src/IST.pine` into the Pine Editor.

## 2 · Evidence

### 2.1 CISD-L10: real TradingView parity (v0.7.1-dev)

The capture is `validation/parity/evidence/ist-v0.7.1-dev_mnq-1m-replay_capture-1000_2026-10-14.csv`:
* the user's `pine-logs-IST_5040e.csv`, copied byte for byte;
* SHA-256 `5789a0cc18106d0adc999f8ea705c7d3eb0fe3b8596e56bc6b32eb8b60714bb6`;
* MNQ (CME_MINI:MNQZ2026) 1m in Bar Replay, 2026-10-13 19:57 → 2026-10-14 13:52 New York, 1,000 bars + 76 warm-up.

**BOUNDED PINE-LOG BAR-BY-BAR PARITY: PASS. 67 MATCH · 0 DIFFERENCE · 9 NOT OBSERVABLE.**

| module | compared |
|---|---|
| Phase 1 / 2 | 1,043 bars × 9 series, 1,027 events |
| LRL | 49 events, 322 boundaries, 2,000 candidate counts |
| HTF FVG | 126 candles, 139 events, 1,075 bar registries |
| **CISD** | 1,075 bar states (delivery state, both candidates, active CISD); 94 CISD_CONFIRMED + 94 CISD_DROPPED_MEMORY, all fields; the definition oracle started UNKNOWN, synchronised on the first CISD (20:01), then 94 CISDs identical |

The only CISD NOT OBSERVABLE item is 3 body / TR values in the first captured bars, while the replay's TR average warms up.

Pinned by `tests/test_parity_v071_evidence.py`. The v0.7.0-dev capture and its fixed defect are in `tests/test_parity_v070_evidence.py`.

### 2.2 CISD-L11: human / golden validation — PASS

| example | source | result |
|---|---|---|
| H1 | the reference product's bullish CISD | **EXACT MATCH**: golden `GOLD_CISD_H1` (origin, L 0 px, confirming bar 0 bars) |
| H2 | a trader's bearish CISD in a 4H FVG | **EXACT MATCH**: golden `GOLD_CISD_H2` |
| H3 | LRL + bullish CISD | supporting reference; OHLC not recoverable (candles ≈ 1 px); nothing fabricated |
| H4 | bullish CISD + 15m FVG, later failed | supporting reference; consistent where readable (the low is out of frame) |
| video 0:21, 1:13–1:21 | reference product | consistent; marked by the confirming bar's close, not intrabar |

* 2 deterministic goldens pass, 0 human mismatch, 0 systematic conflict (`docs/AUDIT_CISD_HUMAN.md`).
* The human lines reject the two alternatives the study had ruled out: the last-candle anchor and the any-candle extreme.
* The approved rules are each pinned by a named test (`tests/test_cisd_freeze.py`, list in its docstring):
  * the first candle of the delivery series gives L, and the last candle never replaces it;
  * only delivery candles set the extreme;
  * a wick through L, or a close exactly at L, does not confirm; a close strictly through L does;
  * exact mirror;
  * UNKNOWN start, then strict UP / DOWN alternation;
  * a failed CISD stays a CISD;
  * no FVG / IFVG / LRL / sweep / displacement requirement.

### 2.3 CISD-L12: reload / determinism — PASS (automated and manual)

**Automated:**
* the same OHLC and settings in two fresh engines and a full replay give the same per-bar state, both candidates, the active CISD, and every record and lifecycle; the Pine formulation equals the oracle (`test_l12_identical_history_gives_identical_results`);
* a prefix equals the full run's past (T12, property);
* Show CISD, Show previous CISD, CISD alerts, Debug, Inspect CISD and the capture are never read by a calculation section or the CISD engine (`test_l12_view_inputs_never_reach_the_engine`, ST-01, ST-20);
* the guard changes no logic (T18, property) and never draws a CISD confirmed before bar 200, even later as the previous one (`test_l12_guard_never_draws_retroactively`);
* real parity: Pine's state equals the oracle's on every captured bar.

**Manual: PASS (user, 2026-10-31)**, the TradingView reload check in `docs/TESTS_CISD.md`:
* the same 3 historical CISDs were checked;
* a page refresh kept their side, origin / id, L, confirmation bar and delivery state;
* removing and re-adding the indicator kept the same values;
* no historical CISD changed.

### 2.4 Automated validation (FULL, final run before the freeze)

**FULL: PASS**, exit 0, 473.8 s, **780 passed, 1 skipped** (the parity section's long-standing skip):
* static 21/21 (ST-20 CISD-R lines, ST-21 history scope);
* CISD 167/167 (oracle, Pine formulation, mutations, freeze tests);
* parity 119/120, including both real-capture evidence tests and the observed-capture test on the v0.7.1-dev capture;
* golden 8/8 (H1, H2);
* invariant detectors 70/70;
* LRL 85/85, HTF 46/46;
* Phase 1 / 2 sections unchanged.

## 3 · Frozen definition (exact text: `docs/CISD.md`, DEF-CISD1 … CISD9)

Bullish CISD; the bearish one is the exact mirror. ε = 0.01 tick.
* **Delivery candle:** close < open − ε. A doji is not one and ends a series. A delivery series is a maximal run of consecutive delivery candles.
* **Leg window:** from bar 0 while the state is UNKNOWN; otherwise from the delivery extreme of the previous (opposite) CISD.
* **L:** the open of the first candle of the series holding the lowest delivery low of the window. Only delivery candles count, and on an equal low the later candle wins.
* **Confirmation:** the first close > L + ε, any colour, after the origin and after the last CISD. A wick through L is not a confirmation, nor is a close at L.
* **State of delivery:** UNKNOWN until the first CISD, then UP / DOWN. CISDs strictly alternate, and never two on one bar (proof in `docs/CISD.md` §1).
* **Record:** identity side + origin time; fields L, origin, the delivery extreme and its time, the leg extreme, confirmation bar / time / close, and body / TR (metadata). Retest, close back and leg break are immutable facts. ACTIVE → ENDED at the opposite CISD. Memory 50, the oldest ENDED record goes first.
* **Events:** `CISD_CONFIRMED`, `CISD_DROPPED_MEMORY`.
* **Pine:** incremental, with no leg-length limit (no bar re-read, no history buffer). No history read of a user series inside a function (ST-21).
* **View:** the current CISD as one 1 px line at L from the origin to the confirmation, plus a tiny label; the previous one optional. Alerts default OFF. No drawing or alert for a CISD confirmed in the first 200 loaded bars.

## 4 · What the freeze guarantees

* CISD detection, state, records and events are fixed to the text above and the oracle. Any change is a new, approved version with new evidence.
* ST-20 pins every CISD-R line of the Pine source, and ST-21 guards the construct behind the v0.7.0-dev defect. The 29 CISD mutations and the human goldens run in every validation.

## 5 · Open items (not blocking the freeze unless the user decides otherwise)

* CISD-L01 … L09 were not recorded one by one; L10 covers their logic on real data.
* The renderer differences from the references (line length past the confirmation, label position) are a separate styling decision; they do not touch detection (`docs/AUDIT_CISD_HUMAN.md` §D).

## 6 · Known limitations

* Chart timeframe only (no multi-timeframe CISD).
* No predictive claim. The study found CISD alone ≈ a random walk on NQ (`docs/STUDY_CISD.md`); CISD describes a change in delivery state.
* Body / TR is informational metadata only: no decision reads it. In a capture's first bars it can be NOT OBSERVABLE while the replay's TR average warms up.
* The renderer and alerts are guarded for the first 200 loaded bars. This is a UX / reload guard, not DEF-CISD.
* The history start matters: the state starts UNKNOWN, and CISDs within the first ~100 bars can differ when the loaded history changes (`docs/CISD.md` §3).
* No CISD quality, context or confluence score yet. Displacement and IFVG are separate future modules.
