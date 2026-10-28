# Phase 2 · Liquidity significance study

**Status: study for review. No definition is approved. `src/IST.pine`, the oracle and `PHASE1_BASELINE_v0.3.2` are unchanged.**

**Data.**
* Exact NQ1! 1m candles from the IST v0.4.3-dev Parity capture: 1,017 bars, 2026-10-27 03:38 → 21:34 New York.
* The file is committed as `validation/studies/data/nq1_1m_capture_2026-10-27.csv`.
* Its bounded Pine-Log parity is PASS: 1,000 bars × 7 series, 1,258 events, 0 differences. That result is now a regression test.
* An earlier 317-bar capture lies inside this window and has identical OHLC on all 317 shared bars.

**Reproduce:**

```bash
python -m validation.studies.liquidity_significance --grid --noise
```

**Two kinds of number, kept apart.**
* **Features** use only bars up to the confirmation bar t = X + right. Only features may enter a definition.
* **Outcomes** use later bars. Two are used:
  * *time until taken*: bars from confirmation to the first trade strictly beyond the level;
  * *amplitude*: how far price moved away from the level before it was taken.

  Outcomes evaluate candidates only. They are partly mechanical: amplitude includes the reaction window, so any reaction-based filter "improves" it by construction. They are not ground truth.

**Sample size.**
* One trading day: Balanced has 140 pivots with 60 bars of history behind them.
* Every percentage below is indicative. A random walk (the null: no structure at all) is run alongside to separate structure from geometry.

---

## A · Why the current filter accepts so many pivots

Current Balanced: pivot with strict left 5 and ≥ right 3. Significance means reaction = high − lowest low of the 3 right bars ≥ 1.0 × TR average(14) at the swing bar.

* **The reaction is large by construction.** The right bars' highs are at or below the swing high, which is how the pivot is defined. Their lows sit about one bar range below their highs. So the lowest low of 3 right bars is almost always about one TR or more under the swing high, whatever the market does. On this sample the reaction's 10th percentile is 1.10 TR. A floor of 1.0 TR removes only stalls, where the next bars hug the high.
* **It is the same on noise.** On a random walk the Balanced reaction median is 2.21 TR and its 10th percentile 1.34 TR. NQ is lower: median 1.87, p10 1.10. NQ 1m pivots are statistically indistinguishable from random-walk pivots on every feature measured (table B). k = 1 is therefore not a significance test. It rejects about 6% on NQ and about 2% on noise.
* **Selection is left to the window.** Strict-left 5 / right-3 pivots occur about 8 times an hour on 1m (both sides together), and 94% of them become levels.

**Consequence for the design.** No feature known at confirmation separated NQ structure from noise structure in this sample. The choice of definition is therefore a *definitional* choice: what a liquidity level *is*. It must be justified by meaning, robustness and behaviour, not by a predictive claim this data cannot support.

## B · Feature distributions (Balanced pivots, × TR average unless stated)

Percentiles p10 · p25 · median · p75 · p90, NQ capture (140 pivots) vs random walk (seed 1, 18,000 bars, 2,584 pivots):

| Feature (known at confirmation) | NQ | Random walk |
|---|---|---|
| Reaction, DEF-L2 (high − lowest low of the right bars) | 1.10 · 1.40 · 1.87 · 2.46 · 3.25 | 1.34 · 1.71 · 2.21 · 2.89 · 3.58 |
| Local prominence: height above the highest neighbour in the pivot window | 0.02 · 0.07 · 0.15 · 0.30 · 0.63 | 0.00 · 0.00 · 0.13 · 0.32 · 0.52 |
| Left dominance: bars since a high above this high + EQ tolerance | 6 · 9 · 21 · 85 · 245 | 7 · 10 · 27 · 104 · 449 |
| Left rise since that higher high (left prominence) | 1.91 · 2.57 · 4.17 · 7.92 · 15.5 | 2.41 · 3.14 · 5.06 · 10.9 · 24.1 |
| Rise over the last 30 bars (range position numerator) | 2.34 · 3.20 · 4.49 · 6.39 · 7.84 | 2.77 · 3.67 · 5.30 · 7.61 · 9.79 |
| Rejection beyond the swing bar's own low | −0.30 · 0.30 · 0.70 · 1.25 · 1.71 | 0.16 · 0.62 · 1.19 · 1.88 · 2.56 |
| Same-side separation from the previous accepted level | 0.15 · 0.40 · 1.32 · 2.75 · 4.72 | 0.28 · 0.69 · 1.62 · 3.30 · 5.47 |
| *Outcome:* bars from confirmation to the take (taken levels) | 1 · 3 · 10 · 36 · 73 | 1 · 3 · 10 · 44 · 208 |
| *Outcome:* amplitude before the take | 1.39 · 1.81 · 3.07 · 7.20 · 12.3 | 1.61 · 2.17 · 3.64 · 7.72 · 17.7 |

Reading:
* **Local prominence** is tiny (median 0.15 TR, about 1–2 ticks). A low value also marks flat and equal tops, which are prime liquidity (EQH). A floor on it would remove exactly the levels ICT cares about.
* **Left rise** is almost always larger than the reaction. min(left rise, reaction) therefore behaves like the reaction alone (table E: C2 ≈ C0), so the left side adds nothing.
* **Dominance** is spread over two orders of magnitude, so it separates "inner" pivots from W-bar extremes cleanly. It is the only feature that describes *structure* rather than the size of a move.
* **Separation** depends on which levels were accepted before, so it is path-dependent (see D).
* **Deferred excursion** means qualifying when price later moves m × TR away. The qualifying pivots do so at confirmation (median delay 0 bars), and 18–41 levels are taken first. It adds variable timing and state for almost no change.

## C · Candidate definitions

All candidates keep these unchanged:
* the DEF-L1 pivot (strict left L, ≥ right R) and its confirmation bar t = X + R;
* TR average (14) at X as the normaliser;
* taken / sweep / break;
* the EQ rules.

Only DEF-L2 changes. Formulas are written for swing highs; swing lows are mirrored.

| Id | Definition (accept when …) | Parameters per preset (Aggressive · Balanced · Strict) |
|---|---|---|
| C0 | reaction ≥ k (current) | k = 0.5 · 1.0 · 2.0 |
| C0+ | reaction ≥ k′ ("k raised") | k′ = 2k |
| **C1** | **reaction ≥ k and dominance: X ≥ W and max(high[X−W … X−1]) ≤ high[X] + EQ tolerance** | **W = 10 · 30 · 60 bars, k unchanged** |
| C2 | min(left rise since the last higher high, reaction) ≥ m | m = 1.0 · 1.5 · 2.0 |
| C3 | dominance W and reaction ≥ m | W as C1, m = 1.0 · 1.5 · 2.0 |
| C4 | rejection beyond the swing bar: low[X] − lowest low of the right bars ≥ b | b = 0 · 0.5 · 1.0 |
| C5 | C0 and separation from the previous accepted same-side level ≥ s (levels within EQ tolerance kept) | s = 1 or 2 |
| C6 | deferred: qualifies at the first bar s ≤ X + R + M where high − lowest low (X+1 … s) ≥ m, if not taken before | m = 1.5–2, M = 10–30 |

W is in bars of the chart. On 1m, 10 / 30 / 60 bars are 10 minutes, half an hour and an hour; they are round time scales, not fitted values.

## D · Pros, cons and failure modes

| Id | Pros | Cons and failure modes |
|---|---|---|
| C0 | Simple, already verified (parity PASS on 1,000 real bars) | Not selective (A). About 8 levels an hour on Balanced, up to 21 active per side |
| C0+ | One number | **Destroys EQH/EQL.** Balanced k = 2: clusters fall from 18 to 3, because the second top of a double top rarely has a large 3-bar reaction. Also tuned to magnitude only: NQ and noise react identically. This is "blindly raising k" |
| **C1** | **Structural meaning: the swing is the extreme of the last W bars ("external" liquidity of that window), not an inner pivot.** **Monotone:** every level is a current level, with *identical* take / sweep / break events (verified). **No lookahead**, and timing unchanged. **Reload-stable:** it depends on W + R bars only. Keeps EQH/EQL far better than C0+, because of the EQ tolerance inside dominance. Cheap in Pine: one `ta.highest(high, W)[R + 1]` | Does not reduce the share of levels taken within 5 bars of creation (≈ 33%), because in a trend each new high is dominant and is run quickly. On noise it thins exactly as on NQ (it defines structure; it does not discover it). Couples to the EQ tolerance input. Warm-up grows to max(14, W) + R bars |
| C2 | Symmetric "prominence" idea | The left side is almost never binding, so it equals C0+ with the same EQ loss |
| C3 | Fewest quick takes at moderate density | Two changed parameters. The raised reaction part brings C0+'s EQ loss (Balanced EQ 18 → 6). Weaker evidence base |
| C4 | "Price traded through the swing candle": an intuitive rejection | Magnitude-based like C0+, with similar EQ loss. Sensitive to large swing bars (a big pivot candle needs a bigger move to qualify) |
| C5 | Fewer near-duplicate levels | **Path-dependent:** it depends on which earlier levels were accepted, so it depends on where the loaded history starts. A reload can then change the levels, against IST's id-stability rule. Conflicts with EQ unless the EQ band is exempted. No outcome improvement (it only thins) |
| C6 | "Let the market prove the level" | Variable creation time. A level taken before it qualifies never exists, so a quick stop run of a fresh high disappears. Needs a pending-candidate state in Pine. Median delay 0: it changes almost nothing |

## E · Behaviour on the captured NQ sample (oracle liquidity engine, EQ/takes unchanged)

The current definition, replayed through the study engine, reproduces the oracle's events exactly (tested for all presets).

| Balanced (L5 R3) | levels (BSL · SSL) | per hour | EQH · EQL | sweeps · breaks | taken ≤ 5 bars after creation | active per side (median · max) |
|---|---|---|---|---|---|---|
| C0 current, k 1 | 71 · 68 | 8.2 | 10 · 8 | 58 · 58 | 31% | 4 · 21 |
| C0+ k 2 | 28 · 32 | 3.5 | 1 · 2 | 25 · 22 | 10% | 3 · 13 |
| **C1 dominance 30, k 1** | **34 · 27** | **3.6** | **4 · 4** | **26 · 24** | **33%** | **2 · 9** |
| C3 dominance 30, reaction ≥ 1.5 | 24 · 20 | 2.6 | 4 · 2 | 20 · 15 | 25% | 2 · 8 |
| reaction ≥ 1.5 alone | 48 · 56 | 6.1 | 7 · 5 | 45 · 38 | 24% | 4 · 20 |
| C4 beyond swing bar ≥ 0.5 | 41 · 50 | 5.4 | 4 · 4 | 38 · 35 | 24% | 3 · 17 |

| C1 per preset | levels: current → C1 | per hour | EQ clusters: current → C1 |
|---|---|---|---|
| Aggressive (L3 R2 k0.5, W 10) | 222 → 133 (60%) | 13.1 → 7.8 | 25 → 17 |
| Balanced (L5 R3 k1.0, W 30) | 139 → 61 (44%) | 8.2 → 3.6 | 18 → 8 |
| Strict (L10 R5 k2.0, W 60) | 58 → 24 (41%) | 3.4 → 1.4 | 4 → 2 |

**Sensitivity** (Balanced pivots, dominance W × reaction m; levels/hour · EQ clusters · taken ≤ 5 bars):

| W \ m | 1.0 | 1.25 | 1.5 | 2.0 |
|---|---|---|---|---|
| none | 8.2 · 18 · 31% | 7.0 · 14 · 29% | 6.1 · 12 · 24% | 3.5 · 3 · 10% |
| 15 | 5.4 · 12 · 33% | 4.5 · 10 · 31% | 4.1 · 10 · 26% | 2.4 · 3 · 10% |
| 20 | 4.5 · 9 · 32% | 3.8 · 7 · 31% | 3.4 · 7 · 25% | 2.1 · 3 · 11% |
| 30 | 3.6 · 8 · 33% | 3.1 · 6 · 33% | 2.6 · 6 · 25% | 1.5 · 3 · 8% |
| 45 | 2.9 · 7 · 28% | 2.6 · 6 · 27% | 2.2 · 6 · 21% | 1.4 · 3 · 8% |
| 60 | 2.4 · 5 · 24% | 2.1 · 5 · 22% | 1.8 · 5 · 13% | 1.1 · 3 · 5% |

* Behaviour changes smoothly in both parameters. No value sits on a cliff, so W = 30 is not a fitted optimum.
* The two halves of the day (03:38–12:06 and 12:06–21:34) give the same picture: C1 Balanced at 3.2 and 4.0 levels/hour.
* m = 2 removes almost every EQ cluster at any W.
* On the random walk, C1 Balanced gives 4.0 levels/hour: dominance thins noise and NQ alike.

## F · Edge cases

1. **Double and equal tops.**
   * A second top up to EQ tolerance *below* an earlier top is still dominant, so EQH can form. Without the tolerance (tested): Balanced EQ 8 → 6, Aggressive 17 → 11.
   * A second top more than the tolerance below an earlier top inside W is not dominant. It is then an inner high, and not an equal one either.
2. **Trend stair-steps.** Every new high is dominant and is accepted, then taken by the next step. The share taken within 5 bars stays about 33%. This is correct liquidity behaviour (each step's stops get run), but it is chart traffic in strong trends.
3. **Ranges.** Inner pivots are rejected and the range extremes kept: the intended effect.
4. **Warm-up.** Dominance needs W bars before X. With the TR average, the first judged swing is at X ≥ max(14, W), confirmed at + R. Pivots before that count as warm-up, not as REJECT. The capture warm-up must grow to max(FVG length + 2, max(14, L, W) + R): 65 bars for Strict.
5. **Halt and session reopen.** A reopen gap inflates the TR average for 14 bars, so reactions must be larger. W counts bars across the 17:00–18:00 halt.
6. **Timeframe.** W is in bars: 30 bars is 30 minutes on 1m and 150 minutes on 5m. That is intentional and explicit, like `left` / `right`.
7. **Ties.** A high exactly at + tolerance keeps dominance; one tick more breaks it (tested). The pivot's own strict-left rule over L bars is unchanged.
8. **History start / reloads.** A level depends only on bars X − W … X + R, so a reload that moves the first loaded bar does not change any level with X ≥ start + W.
9. **Memory.** Fewer levels means memory drops later. Takes of kept levels are identical (tested), and drops change only when memory is full.
10. **EQ tolerance coupling.** Changing "EQ tolerance" also changes dominance. That is explicit in the definition, but must be documented in the input tooltip.

## G · Recommendation

**Adopt C1, dominance, as the new DEF-L2 part (b), and keep the reaction floor (a) unchanged:**

> A confirmed swing high X (DEF-L1, unchanged, known at t = X + R) becomes BSL when both hold:
> (a) **rejection**, unchanged: high[X] − min(low[X+1 … t]) ≥ k × TR average(14) at X;
> (b) **dominance**, new: X has W earlier bars and max(high[X−W … X−1]) ≤ high[X] + EQ tolerance.
> Mirrored for SSL.
>
> | Preset | left | right | k | **W** |
> |---|---|---|---|---|
> | Aggressive | 3 | 2 | 0.5 | **10** |
> | Balanced | 5 | 3 | 1.0 | **30** |
> | Strict | 10 | 5 | 2.0 | **60** |
>
> Custom gains a W input with W ≥ left.

**Why this one:**
* It gives significance a *structural* meaning (the extreme of its last W bars) instead of a magnitude this data cannot validate.
* It is the only candidate that is **monotone**: a strict subset of today's levels, with today's take / sweep / break events unchanged. Implementation and parity can be checked exactly against the current, verified engine.
* It keeps EQH/EQL far better than raising k.
* It is reload-stable and cheap in Pine.
* On the sample it cuts Balanced from 8.2 to 3.6 levels an hour and the maximum active levels per side from 21 to 9.

**Not recommended now:**
* Raising k (C0+): it breaks EQ.
* C3: two parameters changed on one day of data.
* Separation (C5): path-dependent.
* Local prominence: it removes equal tops.
* Deferred qualification (C6): no effect, more state.

C3, a dominance plus a modest reaction raise, should be reconsidered **after** five or more daily captures (2,000 bars each), if quick takes remain a problem.

**Before approval, the user should label** a few levels on the captured window that are clearly structural (the session high/low, an obvious double top, a range extreme). Checking that C1 keeps them is a qualitative recall check, not fitting.

## H · Tests and invariants required before implementation

1. **Subset:** for the same (L, R, k), every C1 level is a C0 level. This is property-tested on the NQ capture and random walks (`tests/test_study_significance.py`). It must become a named invariant with a negative test.
2. **Take identity:** for every kept level, TAKEN, SWEEP and BREAK events are identical to C0, with the same bar and class (tested in the study).
3. **No lookahead:** decisions at t are unchanged when the bars after t are cut or altered (prefix fuzz).
4. **Reload invariance:** run from several history starts; every level with X ≥ start + W is identical.
5. **Boundaries:** dominance holds at exactly + tolerance and fails one tick above; a window edge outside W does not count; lows mirrored (tested in the study). Also: X < W is warm-up, not REJECT.
6. **Counters:** debug rows 22–23 split REJECT into "reaction" and "dominance". pivots = PASS + REJECT(reaction) + REJECT(dominance) + warm-up. PASS = levels created.
7. **Monotone in W:** a larger W gives a subset.
8. **EQ scenario:** a double top whose second top is ≤ tolerance lower forms an EQH under C1; one tick more does not.
9. **Static checks:**
   * dominance uses `ta.highest(high, W)[LIQ_R + 1]` (or an equivalent loop over X−W … X−1) and nothing from after t;
   * W is a [calc] input;
   * the preset table in Pine equals the oracle (ST-13).
10. **Parity:**
    * the capture warm-up formula includes W;
    * the BAR line's swing verdict distinguishes the reject reason, which needs a new code;
    * after implementation, take a new 1,000-bar capture: the preserved v0.4.3-dev capture (`test_real_nq_capture_parity_is_preserved`) will then fail by design and is replaced by the new one.
11. **Regression:** an expected-change manifest entry ("C1 removes non-dominant levels"), then a baseline refresh after review.
12. **Phase 1:** FVG output identical with liquidity ON and OFF (L31 analogue). Phase 1 baseline guard unchanged.
