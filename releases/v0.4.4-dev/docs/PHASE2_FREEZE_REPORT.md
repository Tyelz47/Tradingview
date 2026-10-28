# IST · Phase 2 freeze report — v0.4.4-dev

**Status: FROZEN on 2026-10-28, by decision of the user.** Phase 2 (swing liquidity, BSL/SSL, taken / sweep / break, EQH/EQL) is the second safety baseline, after `PHASE1_BASELINE_v0.3.2`. Phase 3 is not started.

## 1 · Identity

| Item | Value |
|---|---|
| Build | IST **v0.4.4-dev** (version label kept: the frozen bytes are exactly the bytes validated in TradingView) |
| Source | `src/IST.pine`, SHA-256 `b97f4a11a888d7dc3b6e2b24e2a0fc7ebd0aa899f819733dfecfa7dd5664871c`, unchanged since commit 5ec9a33 (the build tested in TradingView) |
| Git tag | **`PHASE2_BASELINE_v0.4.4-dev`** (annotated) on the freeze commit of branch `tooling/validation-agent`. Not merged into `main` |
| Read-only copy | `releases/v0.4.4-dev/` with `SHA256SUMS.txt` (verify: `sha256sum -c SHA256SUMS.txt` inside the folder) |
| Phase 1 baseline | `PHASE1_BASELINE_v0.3.2` (commit 1247abc), unchanged; the Phase 1 diff guard (ST-15) passes |
| Validation tooling | 1.5.1 (`python -m validation --mode full`) |
| Approved liquidity significance | **C1** (DEF-L2 = reaction AND dominance), from `docs/STUDY_LIQUIDITY_SIGNIFICANCE.md` |

**Rollback:** `git checkout PHASE2_BASELINE_v0.4.4-dev`, or paste `releases/v0.4.4-dev/src/IST.pine` into the Pine Editor.

## 2 · Evidence

### 2.1 TradingView (recorded by the user, v0.4.4-dev, 2026-10-28)

| Test | Result |
|---|---|
| L00 compile / runtime | **PASS** |
| L45 dominance preset / debug verification | **PASS**: the debug panel shows Balanced dominance = 30 bars |
| L46 rejection diagnostics | **PASS**: REJECT counters split by reason; dominance actively rejects candidates |
| L47 visual / runtime liquidity sanity check | **PASS**: the EQH/EQL engine remains operational |
| L48 1,000-bar real NQ1! 1m Pine-Log parity | **PASS** (below) |

### 2.2 L48: bounded Pine-Log bar-by-bar parity (real NQ1! 1m)

Settings: Balanced · left 5 · right 3 · k 1 · W 30 · EQ tolerance 4 ticks · minimum touches 2 · Confirmed only.

| Item | Result |
|---|---|
| Window | 2026-10-27 13:44 → 2026-10-28 07:56 New York · 1,033 bars, the first 33 = warm-up (never compared) |
| Bars × series | **1,000 × 9**: FVG verdict, FVG required gap, swing high/low verdict, reactions (PASS bars), required reaction, **dominance reference high/low** |
| Events of structures born in the window | **1,049** compared |
| Checks | **29 MATCH · 0 DIFFERENCE · 6 NOT OBSERVABLE** (all bounded-window limits, §6) |
| Swings after the warm-up (Pine = oracle) | highs **38 PASS / 39 REJECT** · lows **28 PASS / 45 REJECT** |
| FVG after the warm-up (Pine = oracle) | **90 bull · 90 bear · 43 rejected** |

The capture is kept byte for byte as `validation/parity/evidence/ist-v0.4.4-dev_nq1-1m_capture-1000_2026-10-28.csv` (SHA-256 `81726518…eed320c8`). It is replayed on every run by `test_v044_capture_parity_c1_frozen_baseline`.

### 2.3 Historical evidence (definition before C1)

`validation/parity/evidence/ist-v0.4.3-dev_nq1-1m_capture-1000_2026-10-27.csv` (SHA-256 `14640c71…cab8609c`) is the IST v0.4.3-dev capture.
* It gave 1,000 bars × 7 series and 1,258 events, 0 DIFFERENCE, with swings 71/7 and 68/1. It is the data of the significance study.
* It is replayed with its own definition, with no dominance, on every run (`test_v043_capture_parity_is_preserved_under_its_own_definition`).
* Forced to C1, it shows only the intended definition change (`test_v043_capture_under_c1_differs_only_by_the_expected_definition_change`).

**Cross-load data check.** The two captures come from two separate TradingView loads. They share 411 bars, and their OHLC is identical on all 411.

### 2.4 Automated validation (FULL, final run before the freeze)

`python -m validation --mode full` (2026-10-28, validation 1.5.1): **AUTOMATED LOGIC VALIDATION: PASS**, exit 0, 121.7 s. **307 passed, 1 skipped.** The skipped test is the FULL CSV real-data parity: there is no paid export.

| Section | Result |
|---|---|
| Static checks on `src/IST.pine` (incl. ST-15 Phase 1 guard, ST-16 dominance rule) | 16/16 |
| Phase 1 · FVG detection & thresholds · lifecycle & memory · sessions · reference levels | 17/17 · 16/16 · 19/19 · 4/4 |
| Phase 2 · swings & significance · taken / sweep / break · EQH / EQL | 52/52 · 13/13 · 18/18 |
| Event stream · invariant negative tests (43 invariants) | 10/10 · 43/43 |
| Fuzz · properties · stateful · long walks (7 × 20,000 bars) | 12/12 · 1/1 · 7/7 |
| Regression (baseline at v0.4.4-dev; legacy models v0.4.0/v0.4.1 identical with dominance off: 50,110 events) | 5/5 |
| Golden dataset | 6/6 |
| Pine / Python parity (incl. both evidence captures and their SHA-256) | 68/69 (1 skipped: no CSV export) |

TradingView L-tests recorded by the user: 5 PASS, 0 FAIL, 44 PENDING.

## 3 · Frozen definitions (exact text: `docs/LIQUIDITY.md`, DEF-L1 … DEF-L7)

All of these are written for highs / BSL; lows / SSL mirror them. Confirmed mode is the default. Every decision is made at a bar's close and uses only data up to that bar.

| Concept | Frozen definition |
|---|---|
| **Swing (DEF-L1)** | At the close of bar t, swing bar X = t − right. **Swing high:** `high[X] > max(high[X−left … X−1])` and `high[X] ≥ max(high[X+1 … t])`. Ties (plateau): one swing, at the first bar. Origin = X; known at t = X + right |
| **Significance (DEF-L2, C1)** | (a) **Rejection:** `high[X] − min(low[X+1 … t]) ≥ k × SMA(true range, 14)[X]`. (b) **Dominance:** `max(high[X−W … X−1]) ≤ high[X] + EQ tolerance`, a window **anchored to the origin** with the right bars excluded; only a strictly greater earlier high rejects. **Both** must hold. **Warm-up** (TR average `na`, or fewer than W bars before X): neither PASS nor REJECT. REJECT reasons are recorded disjointly (reaction · dominance · both) |
| **Presets (DEF-L3)** | (left, right, k, W): **Aggressive 3 / 2 / 0.5 / 10 · Balanced 5 / 3 / 1.0 / 30 (default) · Strict 10 / 5 / 2.0 / 60 · Custom** = the left / right / k inputs, no dominance (W = 0). W is part of the preset, not an input |
| **BSL / SSL** | A significant swing high becomes a BSL at t, with id = time of X and price = `high[X]`. Events `BSL_CREATED` / `SSL_CREATED` |
| **Taken (DEF-L4)** | The first bar k > t with `high[k] > price` (strictly beyond; a tick or a wick is enough). `BSL_TAKEN` once. An exact touch (`high == price`) is not a take: `touches + 1`, no event. After the take the level is inactive |
| **Sweep / Break (DEF-L4)** | Classified at the **close of the taking bar k**: **BREAK** iff `close[k] > price`, else **SWEEP** (a close exactly at the level is a SWEEP). Fires once and is never relabelled. A gap through is flagged "opened beyond" |
| **EQH / EQL (DEF-L5)** | Members are levels (significant swings) of one side. A new level **joins** the nearest active cluster with `|new − bound| ≤ tolerance` (ties to the newest); otherwise it **forms** a cluster with the nearest earlier unclustered level within tolerance whose pool is intact. `id` and `ref` are fixed at formation; `bound` = the outer member, moving outward only (`bound == ref` in every reachable state, DEF-L5.4). `EQH_CREATED` fires when the members reach `Minimum touches` (default 2). `EQH_TAKEN` fires on the first bar after the cluster is known with `high > bound`, with the same SWEEP / BREAK rule. Tolerance: 4 ticks (1.0 NQ point) by default. A member's individual take is a separate fact |
| **Memory (DEF-L6)** | 100 records per side (input 20–250). When full, the oldest closed record is dropped first, else the oldest live one; each drop is logged (`*_DROPPED_MEMORY`). EQ memory: 25 clusters per side |
| **Display (DEF-L7)** | Renderer only: it never writes state; levels on a visible reference line are not drawn twice. Calculation never depends on visibility |

## 4 · What the freeze guarantees

* Frozen source = validated source (same SHA-256), recoverable from the tag and from `releases/v0.4.4-dev/`.
* Phase 1 output (FVG, sessions, levels) is unchanged: Phase 1 baseline guard and the C1 tests show identical FVG / session / level events with and without C1.
* C1 levels are a strict subset of the pre-C1 levels; every kept level is taken, swept and broken exactly as before.
* No lookahead and reload invariance of every swing decision (tested); the confirmation bar is unchanged.

## 5 · Open TradingView tests

TESTS_PHASE2 has 49 runtime tests: **L00 and L45–L48 PASS** (recorded by the user). **L01–L44 were not recorded one by one and remain PENDING.** Their logic is covered by the automated suite (the L-test map in the validation report), and on real NQ by the bounded parity above. Their TradingView-specific parts are listed in §6.

## 6 · Known limitations and NOT OBSERVABLE areas (need TradingView-specific testing in later phases)

1. **Rendering** (lines, labels, caps, anchors, nearest-first display, the duplicate-line rule on reference lines, faded and historical levels): never compared by parity (L05/L06/L19/L20/L26–L31 area).
2. **Object limits and execution time** under real loads (L22–L25), on 1m / 3m / 5m.
3. **Live mode / realtime rollback** (Confirmed only OFF, L15). Only Confirmed mode is modelled and parity-tested.
4. **Alert delivery** (liquidity alerts default OFF; Phase 1 FVG alerts) and the intrabar alert mode.
5. **`request.security` values (PDH/PDL/PWH/PWL) and the previous-day / week definition** (G-V1…G-V5 unresolved): `LEVEL_SET` is NOT OBSERVABLE in every parity mode.
6. **Pine `time()` session membership:** compared only for sessions that start inside a capture window.
7. **Bounded-window limits of the parity** (the 6 NOT OBSERVABLE groups of L48):
   * engine-memory drops (Pine's memory also holds earlier records);
   * FVGs and levels born in the warm-up or before the window, including their takes;
   * EQ clusters that may contain earlier levels;
   * sessions already running;
   * `LEVEL_SET`.

   Per-bar take codes are not in the capture.
8. **Coverage of the real-data parity.**
   * Only **NQ1! 1m, Balanced**, about 2 days of bars (two captures).
   * Aggressive, Strict, Custom, 3m / 5m and other symbols are verified only by the automated suite (random walks, scenarios), not on TradingView data.
   * FULL CSV bar-by-bar parity (paid export) was never run.
9. **Significance is definitional, not predictive.** The study found NQ 1m pivots statistically indistinguishable from random-walk pivots on every feature measured. C1 defines a meaningful swing (the extreme of its W-bar past, rejected by k × TR); it does not claim to predict reversals. A raised reaction floor (C3) was deferred until more daily captures exist.
10. **Coupling:** the EQ tolerance input also changes dominance (by design, so that equal tops can qualify).
11. **Phase 1 open items stay open:** TESTS.md runtime 8/50 PASS, T03 FAIL (re-test pending), 41 pending. The Phase 1 baseline itself is unchanged.
