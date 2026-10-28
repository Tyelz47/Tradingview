# LRL · research and specification study (diagonal failure-swing liquidity)

**Status: RESEARCH ONLY, awaiting the user's review. Nothing here is approved.**
* No change to `src/IST.pine`, the oracle, Phase 1 or Phase 2. The frozen baseline `PHASE2_BASELINE_v0.4.4-dev` (0487ec4) is untouched; this work is on branch `research/lrl`.
* LRL is not implemented in Pine. The static check ST-08 still forbids LRL identifiers in `src/IST.pine`.
* The request that started this study (2026-10-28) arrived truncated inside deliverable F, after "line break; pivot". This study covers items 1–15 and deliverables A–F as received. It adds G–K (answers, recommendation, validation plan, Pine notes, open questions) as the natural rest of a specification.

**Data.**
* Real data: the two evidence captures (`validation/parity/evidence/`), merged by bar time. That gives 1,639 NQ1! 1m bars, 2026-10-27 03:38 → 2026-10-28 07:56 New York (≈ 27 h, one maintenance gap). The 411 shared bars are identical.
* The sample is small. Every number below is indicative.
* A random walk (6,000 bars, the null: no structure at all) runs alongside, to separate structure from geometry.
* No labelled LRL examples exist yet. The user's reference screenshots were not available in this session, so the visual judgement is the user's (charts in `docs/study_lrl/`).

**Reproduce:** the commands are below.
* `python -m validation.studies.lrl --svg docs/study_lrl` prints every table of §E/§F and writes the charts.
* `pytest validation/tests/test_lrl_study.py` runs 31 tests (report section *LRL research study*).

**Two kinds of number, kept apart (as in the significance study):**
* **definition inputs** use only bars up to the decision bar;
* **outcomes** (time to take, whether price ran to the anchor) use later bars. They describe candidates and never enter a definition.

**Notation.** Everything is written for the **bearish LRL**: descending swing highs, buy stops above the line. The **bullish LRL** (ascending swing lows) is the same algorithm on the mirrored series (high ↔ −low, close ↔ −close). Mirror symmetry is therefore exact, and it is tested.

A pivot is (X, P): swing bar and price. τ is the line tolerance. EQ tol is the frozen DEF-L5 tolerance (4 ticks = 1.0 NQ point). TRA is the TR average, SMA(true range, 14).

---

## A · What an LRL is (formal semantics)

**Failure swing.** A swing high that rallies and fails to reach the previous relevant high. Relative to the previous point of a chain (X₋, P₋), a new confirmed pivot (X, P) is a failure swing iff:
1. **P < P₋ − EQ tol.** It is strictly lower by more than the EQ tolerance. A high within EQ tolerance is an *equal* high: it belongs to EQH, not to a diagonal.
2. **Price never traded above the chain's line + τ between them.** The previous high's diagonal held. Had it not, the "failure" did not happen.

**LRL.** A chain of **at least three** failure swings that form one coherent diagonal. Coherent means all of the following:
* **Close in time:** consecutive points are at most G bars apart.
* **Separate swings:** a real pullback lies between consecutive points.
* **On one line:** every point is within τ of the line.
* **Clean:** no bar's high exceeds the line + τ from the first point to the decision bar.
* **Genuinely diagonal:** the total drop exceeds 2τ, so no horizontal line fits the points within τ.

**Liquidity meaning.** Buy stops rest above each failure swing and along the line, where trendline traders place them. The line is a **diagonal liquidity object**, distinct from horizontal BSL/SSL. Its take is the first trade beyond the projected line + τ. A take can lead to a "run" through the failure swings towards the first point (the anchor).

**Not every sequence of lower highs is an LRL (item 3).** Three consecutive lower highs (control LRL-0) appear about as often on a random walk as on NQ (0.48/h vs 0.51/h). The collinearity, clean, spacing, separation and non-horizontal tests turn "lower highs" into "a line that held three times". Scenario evidence is in §F ("false candidate", "accelerating", "micro-pivots", "shallow staircase").

**The key structural finding: LRL and C1 are complementary, not nested.**
* C1 dominance (DEF-L2b) rejects a swing whenever a higher high lies in the W bars before it. A failure swing is, by definition, a lower high shortly after a higher one.
* On the NQ data, **0 of 56** points 2…n of the recommended LRLs are C1 levels. A C1-only source finds **0 LRLs**.
* BSL/SSL are the *dominant* swings; LRLs are chains of the *non-dominant* swings that C1 filters out. This is what the user anticipated ("smaller failure swings that are intentionally filtered out of BSL/SSL").
* The first point is often a BSL anyway: 17 of 27 anchors are C1 levels.

---

## B · Candidate definitions

All share the common machinery of §C (per-bar order, failure step, spacing G = 30, τ = max(EQ tol, 0.5 × TRA at the anchor), clean test, take / expiry, spent pivots, one LRL per pivot). They differ in pivot source and geometry:

| id | pivot source | geometry (line and projection) | extra test |
|---|---|---|---|
| **LRL-0 control** | DEF-L1 pivots 5/3 | chord, but **no** line, clean or non-horizontal test | the three pivots must be consecutive pivots of that side |
| **LRL-1 fixed** | DEF-L1 5/3 | line through the **first two** points, never moves; later points must lie on its extrapolation | — |
| **LRL-2 chord** | DEF-L1 5/3 | line through the **first and latest** point; earlier points within τ (interpolation) | — |
| **LRL-3 fit** | DEF-L1 5/3 | **least-squares** line through all points; every residual ≤ τ | — |
| **LRL-4 local** | DEF-L1 5/3 | projection = **last segment**; consecutive segment slopes within a factor 2 (curved staircase allowed) | no global collinearity |
| **LRL-5 structural** | anchor = a frozen **C1 BSL/SSL**; later points any DEF-L1 5/3 pivot | chord | — |
| **LRL-R recommended** | dedicated **intermediate pivot engine 3/2** (DEF-L1 rule, no significance test) | chord | consecutive points separated by a pullback ≥ k × TRA (k = 1.0, the Balanced k) |

Swing-source variants were measured separately (§E2): 5/3, C1 only, 3/2, 2/2, and the hybrid C1 anchor + 5/3 followers.

---

## C · Exact formulas and pseudocode

**Line.** For a record with points (X₁, P₁) … (Xₙ, Pₙ), the line in effect is y(x) = y₀ + s · (x − x₀), in bar-index units (the chart's own geometry):

| geometry | (x₀, y₀, s) |
|---|---|
| fixed | (X₁, P₁, (P₂ − P₁)/(X₂ − X₁)) |
| chord | (X₁, P₁, (Pₙ − P₁)/(Xₙ − X₁)) |
| fit | (x̄, P̄, Σ(X−x̄)(P−P̄) / Σ(X−x̄)²) |
| local | (Xₙ₋₁, Pₙ₋₁, (Pₙ − Pₙ₋₁)/(Xₙ − Xₙ₋₁)); inside the span y follows the polyline through the points |

**Tolerance**, frozen when the candidate is formed: τ = max(EQ tol, c × TRA[X₁]), with c = 0.5. The study also measures τ = n ticks, and τ = max(EQ tol, c × (P₁ − lowest low between the first two points)) (range-based).

**Validity of a point list at bar t**, `fit(points, τ, t)`. With (Xₐ, Pₐ), (X_b, P_b) the last two points:
1. **spacing:** X_b − Xₐ ≤ G;
2. **failure step:** P_b < Pₐ − EQ tol − ε;
3. **separate swings** (LRL-R): P_b − min(low[Xₐ+1 … X_b−1]) ≥ k × TRA[Xₐ] − ε;
4. **diagonal** (from 3 points): P₁ − Pₙ > 2τ + ε;
5. **on the line:** |Pᵢ − y(Xᵢ)| ≤ τ + ε for every point. Local geometry replaces this with: every ratio of consecutive segment slopes is in [½, 2];
6. **clean:** high[j] ≤ y(j) + τ + ε for every bar X₁ < j ≤ t.

ε is the Phase 2 float margin (0.01 tick). The control LRL-0 keeps only 1, 2 and "consecutive pivots".

**Per bar t, Confirmed mode** (decisions at the close; same order as the Phase 2 engine):

```
1. ADVANCE   (geometry in effect BEFORE bar t; a record is never judged on its own decision bar)
   for each active LRL with last decision bar < t:
       v = y(t)
       if high[t] > v + τ + ε:   end = BREAK if close[t] > v + τ + ε else SWEEP   (once, never relabelled)
                                 its points become SPENT (never reused)
       elif t > Xₙ + G + right:  end = EXPIRED   (no further point can arrive)
       elif high[t] ≥ v − τ − ε: touches += 1    (diagnostic, no event)
   for each 2-point candidate: drop it silently if crossed (same test), expired, or it holds a spent pivot
2. JUDGE the swing bar X = t − right (DEF-L1 rule of the source engine). If (X, P = high[X]) is a pivot:
   a. EXTEND: active LRLs, oldest anchor first: the first whose points + (X, P) pass fit(…, t)
              takes the pivot → LRL_EXTENDED (n points); the new geometry applies from bar t + 1
   b. CONFIRM (pivot unused): candidates, oldest anchor then oldest 2nd point: the first whose
              points + (X, P) pass fit → LRL_CONFIRMED (3 points). Candidates sharing a point with it are dropped
   c. SEED   (pivot unused): for every earlier pivot A with X − X_A ≤ G that is not a member of an
              active LRL and not spent (and, for LRL-5, is a C1 level): if fit([A, (X, P)], τ_A, t) holds,
              add candidate (A, (X, P)). Keep the newest 25 per side
```

**Consequences, by construction:**
* a pivot belongs to at most one LRL;
* the confirmation bar is X₃ + right, and each extension bar is Xₙ + right;
* a geometry change never applies to a bar before it was decided;
* expiry and take use only bars ≤ t.

---

## D · Pros, cons and failure modes

| id | pros | cons / failure modes |
|---|---|---|
| LRL-0 control | trivial; extends naturally | **accepts any three lower highs**, including non-collinear ones (scenario "3rd high below the line"); same rate on random walk; no line semantics. Rejected |
| LRL-1 fixed | the projection never moves (simplest non-repaint story) | the slope comes from the two *earliest* points. Extrapolation amplifies their noise, so later failure swings miss the line (strictest: 0.22/h). Its line does not pass through the latest point, so it looks detached |
| LRL-2 chord | passes through the first and latest pivots (the visual requirement); interpolation tests the middle points (robust); projection starts at the latest pivot | the projection changes on each extension (forward only; see §G 9). On 5/3 pivots it is rare (0.29/h) and never reached 4 points on NQ |
| LRL-3 fit | tolerant to one off-line point | the line passes through **no** pivot: it does not "connect" them. It needs all points stored, and the slope and intercept move on each extension |
| LRL-4 local | follows curved / accelerating staircases | **accepts non-collinear points** (scenarios "3rd high below", "accelerating"): it is a staircase detector, not a line. The projection follows only the last segment and is unstable |
| LRL-5 structural | ties every LRL to a Phase 2 BSL/SSL | half the LRLs on 5/3 (0.26/h). Misses staircases whose top is not dominant (10 of 27 LRL-R anchors are not C1 levels) |
| **LRL-R** | sees the visible failure-swing staircases (charts); 3–5 points; ~1/h on NQ 1m, at most 1 concurrent per side; separation rule removes micro-pivot chains | a second pivot engine (3/2) beside the Phase 2 one (5/3); about half of the takes come from the line descending into price (below) |

**Failure modes common to all diagonal definitions:**
* **Drift takes.** A descending projection eventually meets a sideways market. On NQ, 43% to 83% of the takes (28% to 56% on the random walk) happened with the taking bar's high below the last failure swing. By trendline semantics this is still a take: the line was crossed. It is not a rally through the highs. The expiry rule (G bars) limits it.
* **Fast takes.** The median is 3–5 bars from confirmation to take. The third touch is often where the staircase ends.
* **No edge.** Rate, take timing and "ran to the anchor" are similar on the random walk. Like C1, an LRL is a *definition* of a structure, not a prediction.

---

## E · Real NQ data (and the random-walk null)

### E1 · Candidate definitions (LRL-0…5 on 5/3 pivots; all: τ = 0.5 TR average, G = 30)

**NQ1! 1m, 1,639 bars ≈ 27.3 h**

| definition | LRLs (bear · bull) | per hour | points 3 · 4 · 5+ | sweep · break · expired · open | bars to take (median) | takes below the last point | ran to anchor ≤ 60 bars after take | concurrent per side (mean · max) | span bars (median) | slope TR/bar (median) |
|---|---|---|---|---|---|---|---|---|---|---|
| LRL-0 control | 14 (7 · 7) | 0.51 | 13 · 1 · 0 | 6 · 8 · 0 · 0 | 3 | 43% | 50% | 0.03 · 1 | 25 | 0.11 |
| LRL-1 fixed | 6 (4 · 2) | 0.22 | 5 · 1 · 0 | 3 · 2 · 1 · 0 | 3 | 60% | 60% | 0.02 · 1 | 32 | 0.12 |
| LRL-2 chord | 8 (5 · 3) | 0.29 | 8 · 0 · 0 | 4 · 3 · 1 · 0 | 3 | 71% | 43% | 0.02 · 1 | 29 | 0.12 |
| LRL-3 fit | 9 (5 · 4) | 0.33 | 9 · 0 · 0 | 4 · 4 · 1 · 0 | 5 | 50% | 50% | 0.03 · 1 | 32 | 0.11 |
| LRL-4 local | 7 (4 · 3) | 0.26 | 7 · 0 · 0 | 4 · 2 · 1 · 0 | 3 | 83% | 33% | 0.02 · 1 | 28 | 0.13 |
| LRL-5 structural | 7 (5 · 2) | 0.26 | 7 · 0 · 0 | 4 · 2 · 1 · 0 | 3 | 67% | 50% | 0.02 · 1 | 28 | 0.12 |
| **LRL-R** | **27 (15 · 12)** | **0.99** | 25 · 2 · 0 | 17 · 10 · 0 · 0 | 4 | 44% | 52% | 0.05 · 1 | 24 | 0.12 |

**Random walk, seed 1, 6,000 bars ≈ 100 h**

| definition | LRLs (bear · bull) | per hour | points 3 · 4 · 5+ | sweep · break · expired · open | bars to take (median) | takes below the last point | ran to anchor | concurrent (mean · max) |
|---|---|---|---|---|---|---|---|---|
| LRL-0 control | 48 (20 · 28) | 0.48 | 40 · 3 · 5 | 14 · 33 · 1 · 0 | 6 | 55% | 34% | 0.05 · 1 |
| LRL-1 fixed | 27 (15 · 12) | 0.27 | 25 · 2 · 0 | 6 · 12 · 9 · 0 | 3 | 28% | 72% | 0.03 · 1 |
| LRL-2 chord | 30 (16 · 14) | 0.30 | 28 · 1 · 1 | 6 · 16 · 8 · 0 | 3 | 41% | 73% | 0.04 · 1 |
| LRL-3 fit | 36 (19 · 17) | 0.36 | 32 · 2 · 2 | 8 · 22 · 6 · 0 | 4 | 37% | 57% | 0.04 · 1 |
| LRL-4 local | 35 (17 · 18) | 0.35 | 31 · 3 · 1 | 12 · 20 · 3 · 0 | 5 | 56% | 53% | 0.04 · 1 |
| LRL-5 structural | 20 (12 · 8) | 0.20 | 20 · 0 · 0 | 5 · 11 · 4 · 0 | 4 | 50% | 75% | 0.02 · 1 |
| LRL-R | 81 (41 · 40) | 0.81 | 69 · 9 · 3 | 25 · 45 · 10 · 1 | 4 | 51% | 56% | 0.07 · 1 |

### E2 · Swing source (chord geometry)

| source | LRLs (bear · bull) | per hour | points 3 · 4 · 5+ | sweep · break · expired | bars to take |
|---|---|---|---|---|---|
| all DEF-L1 pivots 5/3 (any significance) | 8 (5 · 3) | 0.29 | 8 · 0 · 0 | 4 · 3 · 1 | 3 |
| **C1 significant only (BSL/SSL)** | **0** | 0.00 | — | — | — |
| intermediate engine 3/2 | 29 (15 · 14) | 1.06 | 28 · 1 · 0 | 19 · 10 · 0 | 4 |
| intermediate engine 2/2 | 36 (19 · 17) | 1.32 | 31 · 3 · 2 | 25 · 11 · 0 | 4 |
| hybrid: C1 anchor + any 5/3 pivots | 7 (5 · 2) | 0.26 | 7 · 0 · 0 | 4 · 2 · 1 | 3 |

C1 membership:
* LRL-2: 7/8 anchors are C1 levels, and 0/16 of points 2…n.
* LRL-R: 17/27 anchors are C1 levels, and **0/56** of points 2…n.

### E3 · Ablations of the two guard rules (LRL-2, 5/3 pivots)

| variant | LRLs | per hour | bars to take | takes below the last point |
|---|---|---|---|---|
| as specified (drop > 2τ, taken pivots spent) | 8 | 0.29 | 3 | 71% |
| without the non-horizontal rule | 9 | 0.33 | 3 | 62% |
| pivots reused after a take | 11 | 0.40 | 5 | 60% |
| without both | 12 | 0.44 | 3 | 55% |

For LRL-R on NQ, each rule removes a few lines: 27 as specified; 28 without the non-horizontal rule; 29 without the separation rule; 30 with pivots reused after a take.

Before these two rules the 5/3 chart showed two defects. A cluster of almost flat lines formed in the 13:00–14:30 range: highs a few points apart, which is EQ territory. The same staircase was also re-drawn from the same top right after its sweep (00:45–01:05).

### E4 · Tolerance × spacing (LRLs per hour, bear + bull)

| LRL-R, NQ: G \ τ | 4 ticks | 0.25 TRA | **0.5 TRA** | 1.0 TRA | 10% of the first pullback |
|---|---|---|---|---|---|
| 15 | 0.33 | 0.48 | 0.59 | 0.51 | 0.48 |
| **30** | 0.40 | 0.62 | **0.99** | 1.17 | 0.73 |
| 60 | 0.66 | 1.06 | 1.46 | 1.43 | 1.24 |

| LRL-R, random walk: G \ τ | 4 ticks | 0.25 TRA | 0.5 TRA | 1.0 TRA | 10% |
|---|---|---|---|---|---|
| 15 | 0.32 | 0.34 | 0.49 | 0.41 | 0.43 |
| 30 | 0.56 | 0.60 | 0.81 | 0.87 | 0.82 |
| 60 | 0.85 | 0.88 | 1.10 | 1.19 | 1.24 |

LRL-2 (5/3) and LRL-1 (5/3) follow the same shape, at about a third of these rates.

### E5 · Timeframes (NQ data resampled; bars, TR average and τ are those of the timeframe)

| LRL-R | bars | LRLs (bear · bull) | per hour | points 3 · 4 | sweep · break · expired · open | concurrent max per side |
|---|---|---|---|---|---|---|
| 1m | 1,639 | 27 (15 · 12) | 0.99 | 25 · 2 | 17 · 10 · 0 · 0 | 1 |
| 3m | 547 | 12 (3 · 9) | 0.44 | 11 · 1 | 4 · 5 · 2 · 1 | 2 |
| 5m | 329 | 5 (1 · 4) | 0.18 | 4 · 1 | 1 · 2 · 2 · 0 | 1 |

**Candidate funnel (NQ, LRL-R):**
* bearish: 90 candidates → 63 crossed before a third point, 1 expired, 15 confirmed;
* bullish: 105 → 77 crossed, 8 expired, 12 confirmed.

### E6 · Observations

1. **Clutter is not a calculation problem.** LRL-R has at most **one** active LRL per side at any bar on NQ 1m (two on 3m), about one new LRL per hour. Display selection (item 11) is a renderer choice, not a necessity of the logic.
2. **Source decides the result more than geometry does.**
   * C1 gives nothing.
   * 5/3 pivots are too coarse: 0.29/h, no 4th point in 27 h. The staircases visible on the chart are missed (compare `lrl-2.svg` and `lrl-R.svg`).
   * The 3/2 engine sees them.
   * 2/2 adds more lines and more micro-structure for little visual gain.
3. **Geometry.**
   * On the same pivots, fixed (A–B) is the strictest, chord and fit are similar, and local is the loosest.
   * Only chord passes through the first and the latest pivot, so the drawn line connects the pivots.
4. **Tolerance.**
   * 4 ticks is very tight on NQ 1m: τ ≈ 0.11 TRA, giving 0.40/h against 0.99/h.
   * 0.5 TRA (≈ 4.5 NQ points at the median TRA of 9.0) is where the count levels off. 1.0 TRA admits points a full TR average off the line.
   * The range-based τ depends on one pullback, so it is less stable.
   * A TR-normalised τ scales automatically to 3m/5m and to volatility.
5. **Spacing.** G = 30 (the Balanced W) keeps lines within about half an hour per step. G = 60 lets far-apart pivots connect (1.46/h).
6. **Takes.**
   * The median take comes 4 bars after confirmation.
   * 44% of the LRL-R takes happen while the taking bar is still below the last failure swing: the line descended into price.
   * About half the takes reach the anchor (the top of the staircase) within 60 bars, on NQ *and* on the random walk.
   * **No predictive claim is made.**
7. **Sweep vs break mix differs from the walk** (NQ LRL-R 63% sweeps, walk 36%). This is probably the walk's candle construction (its close is the end of its path), not structure. It is not used anywhere.

---

## F · Synthetic scenarios

Built by `zigzag()`: 40 flat bars at 100 (no pivots, TR warm-up), then straight moves through the listed vertices, then flat bars. The ±0.5 path bars make every vertex a strict pivot. Results: ▼ bearish / ▲ bullish · C confirmed · Xn n-th point · S sweep · B break · E expired · @ bar. The LRL-R column is asserted exactly by `test_lrl_study.py`. The other columns are printed by the study.

| scenario | LRL-0 | LRL-1 | LRL-2 | LRL-3 | LRL-4 | LRL-5 | LRL-R |
|---|---|---|---|---|---|---|---|
| clean bearish LRL (highs 120.5 · 116.5 · 112.5, 16 bars apart) | ▼C@85 ▼E@116 | ▼C@85 ▼E@116 | ▼C@85 ▼E@116 | ▼C@85 ▼E@116 | ▼C@85 ▼E@116 | ▼C@85 ▼E@116 | ▼C@84 ▼E@115 |
| clean bullish LRL (mirror of the above) | mirrored: ▲ at the same bars (tested on every scenario, on NQ and on a random walk) | | | | | | |
| 4th and 5th point extension | ▼C@85 ▼X4@101 ▼X5@117 ▼E@148 | same | same | same | same | same | ▼C@84 ▼X4@100 ▼X5@116 ▼E@147 |
| line touch → extension (4th high 0.5 below the line) | ▼C@85 ▼X4@101 ▼E@132 | same | same | same | same | same | ▼C@84 ▼X4@100 ▼E@131 (2 touches) |
| sweep (wick through, close back) | ▼C@85 ▼S@93 | same | same | same | same | same | ▼C@84 ▼S@93 |
| break (close beyond) | ▼C@85 ▼B@93 | same | same | same | same | same | ▼C@84 ▼B@93 |
| pivot beyond the line | ▼C@85 ▼S@96 | same | same | same | same | same | ▼C@84 ▼S@96 (taken by the bar that crossed, before that pivot is confirmed) |
| false candidate: 3rd high 3 points below the line | **▼C@85 ▼E@116** | — | — | — | **▼C@85 ▼S@111** | — | — |
| false candidate: 3rd high above the line | — | — | — | — | — | — | — |
| equal highs (EQH), then a staircase | ▼C@101 ▼E@132 | same | same | same | same | same | ▼C@100 ▼E@131, anchored on the **later** equal high; the frozen oracle still creates the EQH |
| range: equal-ish highs (steps ≤ EQ tolerance) | — | — | — | — | — | — | — |
| strong trend, collinear highs (slope −1 point/bar) | ▼C@77 ▼S@107 | same | same | same | same | same | ▼C@76 ▼S@107 (a drift take) |
| strong trend, accelerating highs | **▼C@77 ▼S@107** | — | — | — | **▼C@77 ▼B@99** | — | — |
| micro-pivots (collinear, 0.75-point pullbacks) | — (5/3 cannot see them) | — | — | — | — | — | — (an LRL without the separation rule) |
| shallow staircase (drop ≤ 2τ) | **▼C@85 ▼E@116** | — | — | — | — | — | — (an LRL without the non-horizontal rule) |
| points too far apart (gaps 36 > 30) | — | — | — | — | — | — | — |
| triangle: bearish and bullish together | ▼C@85 ▲C@93 ▼S@99 ▲S@114 | same | same | same | same | same | ▼C@84 ▲C@92 ▼X4@98 ▼S@101 ▲S@114 |

**What the tests prove** (`validation/tests/test_lrl_study.py`, 31 tests):
* every scenario gives exactly the LRL-R events above;
* **each guard is load-bearing**: removing the separation, non-horizontal, line or chord-collinearity rule turns a rejected scenario into an LRL;
* bullish = mirrored bearish (NQ, random walk);
* **no lookahead**: on NQ and a random walk, every event before bar n is identical with or without the bars ≥ n;
* record invariants: points fail strictly, are ≤ G apart, lie on the line within τ, drop more than 2τ, and belong to one LRL only; events sit on the points' confirmation bars;
* failure swings are never C1 levels on NQ, and the C1-only source is empty;
* the definition runs on 3m and 5m;
* the frozen oracle's EQH is unaffected.

---

## G · Answers to the study questions

1. **Swing source.** Not C1: it is structurally incompatible (§A, 0/56). Use a **dedicated intermediate pivot engine**: the DEF-L1 rule with left 3 / right 2 and no significance test, plus a separation rule (k × TRA pullback) against micro-pivots. All DEF-L1 5/3 pivots are too coarse on 1m. The hybrid (C1 anchor) halves the count and misses non-dominant tops. Whether the anchor is a BSL/SSL should be **metadata** (label), not a filter.
2. **Minimum points.**
   * A 2-point **candidate** is internal state only: no event, not drawn (any two pivots define a line).
   * The LRL is **confirmed by the 3rd point**, at that point's confirmation bar.
   * It **extends** to a 4th, 5th, … compatible point.
   * "3 points from inception" (search all triples when a pivot confirms) gives identical results here, because candidates are kept for G bars. The incremental form is cheaper in Pine.
   * Lifecycle: candidate → confirmed → extended → swept / broken / expired.
3. **Failure semantics.** P < P₋ − EQ tol, with the line clean between them (§A). Lower highs alone are not enough. Collinearity, cleanliness, spacing, separation and the non-horizontal rule are all required (§F).
4. **Geometry.** **Chord, first → latest point.** It is the only one that connects the pivots and tests the middle points by interpolation. Fixed A–B is too brittle (extrapolation), least squares connects no pivot, and the last-segment slope accepts curves.
5. **Slope consistency.** Every point within τ = max(EQ tol, 0.5 × TRA at the anchor), frozen per record. Ticks are too tight on 1m and do not scale. The range-based τ is unstable. A time-widening τ was not adopted: it makes the take level drift with distance and is harder to verify.
6. **Time spacing.**
   * **Minimum:** for descending highs the DEF-L1 strict-left rule already forces more than `left` bars between points, because a lower high cannot be a pivot within `left` bars of a higher one. Real separation comes from the pullback rule.
   * **Maximum:** G = 30 bars between consecutive points.
7. **EQ interaction.**
   * An EQ-equal high (within EQ tol) is never an LRL step. EQ and LRL steps are disjoint by construction, using the same frozen tolerance.
   * An LRL can start at the later member of an EQH (the most recent failure).
   * The LRL engine only reads bars. EQH/EQL logic cannot be affected, and the frozen oracle still creates the EQH in that scenario.
8. **Invalidation.**
   * **TAKEN** = first bar with high > line + τ (wick), at its close: **BREAK** if the close is beyond line + τ, else **SWEEP**. This applies at any time, including a swing pivot beyond the line, which takes the LRL on the bar that crosses, before that pivot is even confirmed.
   * **EXPIRED** = no new point possible (X_last + G + right) and not taken.
   * **TOUCH** = a high within ±τ of the line: counted, no event.
   * A candidate that is crossed simply dies.
   * The ended line stays in history (renderer option).
   * Breaking the originating high cannot happen before the line is taken, so it adds no state. It is a Phase 2 BSL take when the anchor is a BSL.
9. **Extension.**
   * Points are append-only.
   * The chord moves to (first, new latest) only from the extension bar on. Earlier take decisions used the earlier chord and are never re-evaluated.
   * The extension test re-checks cleanliness of all past bars against the new chord, using past data only.
   * The **drawn** pivot-to-pivot polyline never moves: its segments join fixed pivots.
10. **Projection.** Yes, as a separate concept:
    * the **historical polyline** (immutable) and the **active projection** (dashed) from the latest point along the chord;
    * the projection is drawn only while active, until the take or expiry bar, and is never extended past expiry.
11. **Multiple candidates.**
    * The logical state keeps every candidate (≤ 25 per side) and every active LRL.
    * A pivot joins at most one LRL. Candidates sharing a point with a confirmed LRL are dropped, and the pivots of a taken LRL are spent.
    * NQ 1m never had more than one active LRL per side. Display default: the active LRL nearest to price per side, with history optional.
12. **Relation to BSL/SSL.**
    * Separate structure and separate event family (`LRL_CONFIRMED / _EXTENDED / _SWEEP / _BREAK / _EXPIRED`).
    * It reads bars only. It writes nothing to BSL/SSL/EQ.
    * The first point *may* be a BSL/SSL (17/27 on NQ). The later points are, by the C1 definition, not.
13. **Repainting.**
    * Every decision is made at a bar's close from bars ≤ t.
    * Confirmation time = third point's confirmation bar, never earlier.
    * Events are immutable and the points append-only.
    * Proven by prefix invariance on NQ and a random walk.
    * The polyline drawn back to past pivots is a drawing of confirmed facts, like a BSL line drawn from its swing bar (logical history ≠ visual history, ARCHITECTURE §2).
14. **Timeframes.**
    * All parameters are in bars and TR multiples. Only the EQ floor is in ticks.
    * On 3m / 5m the definition runs unchanged (12 and 5 LRLs in the same 27 h).
    * Bars per point stay the same, so lines span more time.
15. **Visual target.** `docs/study_lrl/lrl-R.svg` is the proposal:
    * a thin polyline through the failure-swing pivots, plus a dashed projection while active;
    * a small "LRL" label at the latest point, and an S / B mark where it was taken;
    * bearish and bullish mirrored, and no horizontal lines.
    * The open circle marks the confirmation bar (a debug idea, optional).

---

## H · Recommendation (for approval): DEF-LRL1 … LRL8

Proposed as the next specification, **not implemented**. Constants are those of LRL-R and were not tuned to a target count.

* **DEF-LRL1 · Pivots.** A dedicated intermediate engine, independent of the liquidity preset. At the close of bar t, X = t − 2 is an LRL swing high iff `high[X] > max(high[X−3 … X−1])` and `high[X] ≥ max(high[X+1 … t])`. Lows are mirrored. No reaction or dominance test.
* **DEF-LRL2 · Tolerance.** τ = max(EQ tolerance, 0.5 × SMA(TR,14)[X₁]), frozen when the candidate forms. No TR average yet means no candidate.
* **DEF-LRL3 · Consecutive points** (X₋, P₋) → (X, P), all three required:
  * P < P₋ − EQ tolerance;
  * X − X₋ ≤ 30;
  * P − min(low[X₋+1 … X−1]) ≥ 1.0 × SMA(TR,14)[X₋].
* **DEF-LRL4 · Line.**
  * Chord through the first and latest points: y(x) = P₁ + (Pₙ − P₁)(x − X₁)/(Xₙ − X₁).
  * Every point within τ of it, and P₁ − Pₙ > 2τ.
  * Clean: `high[j] ≤ y(j) + τ` for X₁ < j ≤ t.
* **DEF-LRL5 · Lifecycle.**
  * Candidate (internal), confirmed (3rd point, `LRL_CONFIRMED` at X₃ + 2), extended (`LRL_EXTENDED` at Xₙ + 2), as in §C.
  * Taken: the first bar k after the last decision bar with `high[k] > y(k) + τ`. At its close, `LRL_BREAK` iff `close[k] > y(k) + τ`, else `LRL_SWEEP`. Once, never relabelled. Its pivots are spent.
  * Expired: the first bar after Xₙ + 32 with no take (`LRL_EXPIRED`).
  * Touch: a diagnostic counter.
  * Per-bar order: advance, then judge.
* **DEF-LRL6 · Identity and memory.**
  * id = side + time of X₁ + confirmation time.
  * 25 candidates and a bounded number of LRL records per side (oldest ended first), each drop logged as in DEF-L6.
  * One LRL per pivot.
* **DEF-LRL7 · Display (L6 only).**
  * Polyline through the member pivots; a dashed projection from the latest point to the current bar while active, ending at the take / expiry bar; label "LRL".
  * Default: the nearest active LRL per side; ended LRLs behind a history toggle.
  * Visibility never changes state.
* **DEF-LRL8 · Coexistence.**
  * Reads bars (and, for a label only, whether X₁ is a BSL/SSL); never writes Phase 1 or Phase 2 state.
  * The Phase 1 and Phase 2 event streams must be byte-identical with LRL on and off.
  * Alerts are a separate later decision, default OFF.

**LRL presets.** Measured, **not recommended yet.** Tying the LRL to the liquidity presets (Aggressive 2/2 · G 10, Strict 5/3 · G 60) gave Aggressive *fewer* lines than Balanced on NQ 1m (0.70/h vs 0.99/h, because G = W = 10 is tight). The proposal is one fixed LRL definition first, and presets only after it is validated on TradingView.

---

## I · Validation plan before any Pine code (after approval)

1. **Oracle.** `validation/models/lrl.py`, a clean reference model of DEF-LRL1…8 (the study engine is the prototype). It plugs into `IstModel` as a fifth engine after liquidity, reading bars only.
2. **Invariants with negative tests:**
   * INV-LRL-1: one LRL per pivot.
   * INV-LRL-2: strict failure step.
   * INV-LRL-3: on-line ≤ τ.
   * INV-LRL-4: drop > 2τ.
   * INV-LRL-5: clean at every decision.
   * INV-LRL-6: events on X + right bars only.
   * INV-LRL-7: one terminal event.
   * INV-LRL-8: Phase 1/2 streams identical with LRL on/off.
   * INV-LRL-9: mirror symmetry.
   * INV-LRL-10: prefix invariance.
3. **Scenarios.** The 16 of §F become oracle tests; the user's labelled real examples become golden cases.
4. **Parity.** Extend the debug Parity capture with the five `LRL_*` event lines (points, τ) and a per-bar value: the level y + τ of the nearest active LRL per side. Bounded Pine-Log bar-by-bar parity of that series and of the events is then possible on the free plan, as for L48.
5. **TradingView tests** (draft L-LRL list):
   * compile / runtime;
   * the confirmation bar and no early drawing;
   * reload invariance on historical bars;
   * extension, sweep / break / expiry on chart;
   * object budget with Phase 1 + 2 rendering on;
   * 1m / 3m / 5m.

## J · Pine feasibility notes

* **State.** UDT `Lrl` with arrays of point bars and prices, plus τ, slope and status. Candidates use the same UDT. That means ≤ 25 candidates and a handful of LRLs per side.
* **Cost.**
  * Advancing is O(active + candidates) per bar.
  * Only on a pivot bar, extension / confirmation / seeding run the clean test over ≤ ~3 G bars of `high[]` history, about ≤ 25 × 90 checks.
  * It needs `max_bars_back` ≥ ~100 on `high` / `low`.
* **Drawing.** One polyline per displayed LRL, re-created only when a point joins (the same fixed points, so nothing moves), plus one projection line updated while active. Display is capped, so objects stay within the Phase 2 budget. This is to be measured in TradingView (L-LRL object test), not assumed.

## K · Open questions for the user

1. **Pivot engine 3/2** (recommended), or keep the Phase 2 5/3 pivots? On 5/3, 0.29/h and no extensions.
2. **τ = 0.5 × TR average and G = 30 bars:** confirm.
3. **Take semantics:** crossing the projected line + τ counts, including when the line descends into price (44% of takes). Or do you want a separate label for those?
4. **After a take, the pivots are spent** (recommended). The alternative re-draws the line from the same top after a sweep: on NQ, LRL-R goes from 27 to 30 lines, and LRL-2 from 8 to 11.
5. **Display default:** the nearest active LRL per side, history optional, 2-point candidates only in debug?
6. **Visual check:** please compare `docs/study_lrl/lrl-R.svg` with your reference screenshots and list lines that are missing or should not be there. Those examples become the first golden LRL cases.
