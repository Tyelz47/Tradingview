# Displacement research study

**Status: APPROVED by the user on 2026-11-01 (DISPLACEMENT-R, decisions M1…M11 as recommended in §M).** The specification is `docs/DISPLACEMENT.md`, the reference model `validation/models/displacement.py` (validation 1.16.0), and the Pine implementation IST v0.8.0-dev (validation 1.17.0). This study is kept as the research record.
* **Wording correction (2026-11-01, no rule change).** §A item 4, §H and M3 first described "close beyond the previous candle" as the necessary condition for leaving an FVG. That was wrong. A standard bullish FVG is a three-candle condition: the low of candle 3 above the high of candle 1. The rule stays in DISPLACEMENT-R as a **displacement** criterion: it separates directional repricing from a large candle still contained within the previous candle. It is not the FVG definition.
* At the time of the study: no change to `src/IST.pine`, to CISD-R (frozen, `CISD_BASELINE_v0.7.1-dev`), to LRL, HTF FVG, Phase 1 or Phase 2.
* Harness: `validation/studies/displacement.py` (`python -m validation.studies.displacement` prints every table below).
* Tests: `validation/tests/test_displacement_study.py` (report section `research.disp`); the oracle's tests are listed in §K.

**Data and honesty notes**
* Real data: every 1m capture in the repository, as **three separate segments**, never joined, so no TR average crosses from one segment into another. In total **3,791 bars ≈ 63.2 h**:
  * NQ1! 2026-10-27 03:38 → 10-28 07:56 New York, 1,639 bars, including the CME 17:00–18:00 break;
  * MNQ 2026-10-29 21:48 → 10-30 15:43, 1,076 bars;
  * MNQ 2026-10-13 19:57 → 10-14 13:52, 1,076 bars (Bar Replay).
* 3m / 5m / 15m are the same bars resampled. The 15m sample (210 bars) is too small to conclude anything.
* Noise controls: the same candles in a random order (5 shuffles), and random walks (`validation/candles.random_walk`, 5 seeds).
* **Everything below is descriptive.** No threshold was chosen from what price did afterwards, no statistic shows a predictive edge, and none is claimed.
* No human-labelled displacement example exists yet. The human CISD goldens (H1, H2) carry no displacement label, so they cannot validate this module (§M, M10).

---

## A · Conceptual findings

**What the methodology means by displacement.** The ICT material reachable here is secondary: educational sites and indicator authors, not the original lessons. On the core idea they agree:
* Displacement is a fast, one-sided, energetic repricing: large bodies, small wicks, moving decisively in one direction.
* It often leaves a fair value gap behind. In this reading the FVG is the residue of the move, and the move itself is the displacement.
* It is what gives a market structure shift its weight. A slow drift through a level is not displacement.
* Sources differ on the details: one large candle, or 3–5 strong closes in a row. The thresholds are not standardised (examples: body ≥ 60 % of the range; body ≥ ATR(14) × 2). None of them is ICT's own number.

Sources (secondary): [LuxAlgo, Displacement](https://www.luxalgo.com/library/concept/displacement/) · [Backtrex, ICT displacement candle](https://backtrex.com/en/blog/ict-displacement-candle-market-concept) · [TradingView, ICT PD Arrays / FVG / Displacement script](https://www.tradingview.com/script/U5qHodUJ-ICT-PD-Arrays-LunqFX-FVG-Displacement-Smart-Money-Zones/) · [Tradervue, The ICT trading strategy](https://www.tradervue.com/blog/the-ict-trading-strategy) · [TrendSpider, ICT basics](https://trendspider.com/blog/ict-basics-a-beginners-guide/).

**What separates displacement from ordinary volatility (measured here, §C, §D).**
1. **Relative, not absolute, size.** A large-candle detector in points is a session clock: on these data it fires 11–69 × more often per hour in the NY AM session than in Asia. Measured against the local TR average, displacement fires at the same rate in every session (1.5–1.9 per hour; NY AM ÷ Asia = 1.2). Ordinary volatility is high TR everywhere; displacement is a candle that stands out **from its own neighbourhood**.
2. **Body, not range.** Range-based candidates select wide two-sided candles. Their p10 travel is 0.81 × TR and their close location goes down to 0.60, so they leave fewer FVGs (68 % vs 85 %). Body-based ones select net one-way delivery.
3. **Acceptance at the extreme.** Among bodies ≥ 1.5 × TR the median close location is 0.90, but 13 % have a closing-side wick above 25 % of the range: a push that was partly rejected inside the bar.
4. **Repricing beyond the prior candle.** A close outside the previous candle's range separates directional repricing from a large candle still contained within the previous candle (for example, a strong retrace inside a bigger news candle). It is a displacement criterion, not the FVG definition: a standard bullish FVG is a three-candle condition (the low of candle 3 above the high of candle 1).

**Detection vs. contextual quality (the separation this study keeps).**
* **Detection (this module).** One closed candle reprices aggressively against its own neighbourhood. It reads candles only.
* **Context and quality (later modules, never base requirements).** After a liquidity sweep, with or as a CISD, leaving an FVG, toward a DOL, breaking a swing or a recent range, the session, multi-candle legs.
  * The evidence keeps them out of the base definition. FVG creation is a frequent **consequence** (85 %), but 86 % of FVGs come without a displacement candle (§G). CISD overlaps only partly (§F). A recent-range break removes events with no structural reason (D7).

## B · Candidate definitions

Common rules for every candidate:
* **Mirror symmetry.** Written for the bullish side; the bearish side is the mirrored candle (§H, DEF-DISP1).
* **EPS.** 0.01 tick, the float margin used everywhere in IST.
* **Yardstick A.** `ta.sma(ta.tr(true), 14)` of the bars **before** the displacement's first candle, so a candle never inflates its own yardstick.
* **Warm-up.** No decision until A exists. **A = 0** (no price change in 14 bars) has no scale, so no decision either.
* **Thresholds are not tuned on outcomes.** Each one is the **Tukey upper fence** (Q3 + 1.5 × IQR) of that candidate's own statistic on the real data, rounded to 0.1: "an outlier against its own population" (§E). The fences (1m, all three segments):
  * body / TR 1.47;
  * range / TR 1.94;
  * body / median body 3.87;
  * 2-candle travel 2.10;
  * 3-candle travel 2.53;
  * directional-run travel 2.74.

| id | exact rule (bullish) | parameters | confirmed | repaint | Pine | expected false positives | expected false negatives |
|---|---|---|---|---|---|---|---|
| D1 body expansion | `close − open ≥ 1.5 × A`, `close > open + EPS` | k | candle close | none | trivial | big bodies with a large closing-side wick (rejected pushes); big bodies inside a bigger previous candle | fast moves made of several medium candles |
| D1r range expansion | `high − low ≥ 1.9 × A`, any non-doji candle | rk | candle close | none | trivial | **two-sided volatility**: p10 travel 0.81 × A, close location down to 0.60 | strong bodies with a modest range |
| D2 body + strong close | D1 and `close − low ≥ 0.75 × (high − low)` | k, clv | candle close | none | trivial | big bodies inside the previous candle's range | multi-candle moves |
| D3 relative body | `close − open ≥ 3.9 × median(|body|, 20 before)` | rel, look | candle close | none | `ta.median` at global scope | **quiet periods**: the median body collapses (p10 travel 1.01 × A); fires 2.9/h | after a run of large bodies the median rises |
| D4 multi-bar window | `close[t] − open[t−n+1] ≥ k × A(before t−n+1)`, one event per window (n = 2: k 2.1; n = 3: k 2.5) | n, k | close of the last candle | none (window fixed) | trivial | slow two-sided drifts inside the window | single candles that already qualify are delayed or absorbed |
| D4r directional run | the current run of up-close candles (a doji or a down-close candle ends it): `close − open of the run's first candle ≥ 2.7 × A(before the run)`, once per run | k | the close that crosses | none | `var` run start | **slow staircases** (velocity unbounded) | runs broken by one doji |
| D5 expansion + FVG | D1 and candle 2 of a bullish FVG: `low[t+1] > high[t−1]` | k | **candle 3** (one bar late) | none | trivial | ordinary candles whose next bar gaps | displacement whose next bar dips back into the previous candle; the event is always one bar late (it is a CISD's confirming candle only 2 % of the time, vs 31 %) |
| **D6 hybrid** | D2 and `close > high[t−1] + EPS` | k, clv | candle close | none | trivial | strong candles in a news sequence that inflates A only afterwards | multi-candle moves (§F, §J); a strong reversal candle closing inside a bigger previous candle |
| D7 hybrid + recent-range break | D2 and `close > highest high of the 10 candles before + EPS` | k, clv, 10 | candle close | none | `ta.highest` at global scope | — | displacement inside a range (e.g. the first leg out of a consolidation that is not yet the 10-bar high): a structural / context condition, not displacement |

## C · Real NQ statistics (1m, three segments, 63.2 h)

Population (every bar with A): body / TR p50 0.39 · p90 1.04 · p95 1.34 · p99 2.24 · max 12.99. TR average on NQ 1m: min 4.2 points, p1 4.7 (a zero or tiny A never occurs on real data).

| definition | events (bull · bear) | per hour | per hour: Asia · London · NY AM · NY PM · other | travel / A (p10 · median · p90 · max) | range / A (median) | close location (p10 · median) | raw FVG left | Phase 1 FVG left | is a CISD's confirming candle | same-side CISD ±5 bars | CISDs confirmed by one |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D1 body ≥ 1.5 × A | 129 (59 · 70) | 2.04 | 1.8 · 1.8 · 2.1 · 2.3 · 2.1 | 1.53 · 1.94 · 2.79 · 12.99 | 2.36 | 0.73 · 0.90 | 81 % | 80 % | 32 % | 64 % | 14 % |
| D1r range ≥ 1.9 × A | 165 (80 · 85) | 2.61 | 2.0 · 2.8 · 2.8 · 2.1 · 2.8 | 0.81 · 1.72 · 2.70 · 12.99 | 2.26 | 0.60 · 0.86 | 68 % | 67 % | 32 % | 64 % | 17 % |
| D2 = D1 + close outer 25 % | 112 (49 · 63) | 1.77 | 1.5 · 1.6 · 1.9 · 1.8 · 1.9 | 1.54 · 1.91 · 2.86 · 12.99 | 2.26 | 0.82 · 0.92 | 84 % | 82 % | 30 % | 60 % | 11 % |
| D3 body ≥ 3.9 × median body | 186 (86 · 100) | 2.94 | 2.5 · 3.6 · 3.3 · 3.1 · 2.7 | 1.01 · 1.56 · 2.62 · 12.99 | 2.02 | 0.72 · 0.90 | 77 % | 73 % | 29 % | 60 % | 18 % |
| D4 3-candle travel ≥ 2.5 × A | 102 (51 · 51) | 1.61 | 1.2 · 2.0 · 1.5 · 1.4 · 1.7 | 2.57 · 2.91 · 3.83 · 15.03 | 3.77 | 0.78 · 0.93 | 97 % | 97 % | 17 % | 64 % | 6 % |
| D4r run travel ≥ 2.7 × A | 115 (55 · 60) | 1.82 | 1.4 · 1.8 · 1.5 · 2.9 · 1.9 | 2.74 · 3.05 · 3.94 · 12.99 | 3.57 | 0.82 · 0.93 | 97 % | 97 % | 19 % | 62 % | 7 % |
| D5 = D1 + FVG (on candle 3) | 104 (47 · 57) | 1.65 | 1.6 · 1.5 · 1.2 · 1.8 · 1.8 | 1.53 · 2.03 · 2.99 · 12.99 | 2.38 | 0.74 · 0.90 | 100 % | 99 % | 2 % | 65 % | 1 % |
| **D6 = DISPLACEMENT-R** | **110 (49 · 61)** | **1.74** | **1.5 · 1.6 · 1.7 · 1.8 · 1.9** | 1.54 · 1.93 · 2.88 · 12.99 | 2.27 | 0.82 · 0.91 | **85 %** | 84 % | 31 % | 60 % | 11 % |
| D7 = D2 + beyond 10 candles | 85 (36 · 49) | 1.35 | 0.9 · 1.4 · 1.2 · 1.4 · 1.5 | 1.54 · 2.04 · 3.07 · 12.99 | 2.32 | 0.81 · 0.91 | 89 % | 88 % | 29 % | 61 % | 8 % |

**Large-candle control** (the "generic large candle detector" the user does not want):

| detector | events | per hour: Asia · London · NY AM · NY PM · other | NY AM ÷ Asia |
|---|---|---|---|
| DISPLACEMENT-R | 110 | 1.5 · 1.6 · 1.7 · 1.8 · 1.9 | 1.2 |
| body ≥ 15 points | 322 | 1.6 · 3.5 · 18.1 · 7.8 · 3.1 | 11.6 |
| body ≥ 20 points | 162 | 0.4 · 1.0 · 11.1 · 4.3 · 1.4 | 28.2 |
| body ≥ 25 points | 81 | 0.1 · 0.5 · 6.8 · 1.4 · 0.6 | 69.4 |

**Timeframes** (DISPLACEMENT-R; the selectivity is a share of bars, so it carries across timeframes):

| timeframe | per hour | share of bars |
|---|---|---|
| 1m | 1.74 | 2.9 % |
| 3m | 0.66 | 3.3 % |
| 5m | 0.38 | 3.2 % |
| 15m (small sample) | 0.09 | 2.4 % |

**Selectivity.**
* **Not too frequent.** About one displacement every 35 bars on any timeframe, so not a trend-candle marker. At k = 1.0 the rate is 5.35/h, one every 11 bars.
* **Not too rare.** Only 2 of the 110 have a body ≥ 4 × A, so the rule is not a news-candle detector.

## D · Synthetic comparison (events per hour)

| definition | real NQ / MNQ | the same candles shuffled (5 orders) | random walk (5 seeds) |
|---|---|---|---|
| DISPLACEMENT-R with k 1.0 | 5.35 | 5.71 | 13.80 |
| **DISPLACEMENT-R (k 1.5)** | **1.74** | 2.44 | 5.16 |
| DISPLACEMENT-R with k 2.0 | 0.79 | 1.18 | 1.22 |
| D1 | 2.04 | 2.92 | 5.31 |
| D4r | 1.82 | 2.13 | 3.82 |

Body / TR fence: real 1.47 · shuffled 1.39 · random walk 2.11.

* **Noise produces "displacement" candles too.** Shuffled real candles produce 40 % more than the real order: in real data, large candles cluster in volatile stretches, which raise A. A random walk with uniform steps produces many more.
* **What follows.** DISPLACEMENT-R is a **description** of the delivery of one candle relative to its neighbourhood. It is not evidence of informed order flow, and a displacement does not predict anything by itself. This is the same honest conclusion as the CISD study.

## E · Parameter sensitivity

| parameter (others as DISPLACEMENT-R) | value | per hour | events in common with DISPLACEMENT-R (Jaccard) | events ≥ 4 × A |
|---|---|---|---|---|
| k | 1.0 · 1.25 · **1.5** · 1.75 · 2.0 · 2.5 | 5.35 · 3.20 · **1.74** · 1.08 · 0.79 · 0.33 | 0.33 · 0.54 · 1 · 0.62 · 0.45 · 0.19 | 2 at every k |
| clv | 0 · 0.5 · 0.67 · **0.75** · 0.8 · 0.9 | 1.98 · 1.98 · 1.88 · **1.74** · 1.66 · 1.00 | 0.88 · 0.88 · 0.92 · 1 · 0.95 · 0.57 | 2 |
| beyond (candles) | 0 · **1** · 2 · 5 · 10 · 20 | 1.77 · **1.74** · 1.63 · 1.49 · 1.35 · 1.03 | 0.98 · 1 · 0.94 · 0.85 · 0.77 · 0.59 | 2 |
| TR average length | 7 · 10 · **14** · 20 · 30 · 50 | 1.88 · 1.80 · **1.74** · 1.73 · 1.79 · 1.69 | 0.62 · 0.78 · 1 · 0.82 · 0.70 · 0.63 | 3 · 3 · 2 · 2 · 4 · 5 |

**Tukey fence of body / TR**, the source of k:

| data | 1m | 3m | 5m | 15m (n ≈ 60–95) |
|---|---|---|---|---|
| NQ1! | 1.49 | 1.52 | 1.45 | 1.40 |
| MNQ 10-29/30 | 1.42 | 1.50 | 1.52 | 1.72 |
| MNQ 10-13/14 | 1.48 | 1.40 | 1.42 | 1.75 |
| all three | **1.47** | 1.48 | 1.47 | 1.58 |

Reading:
* **k.** The body / TR distribution has no natural break; k only sets the selectivity, and the event sets nest. The Tukey fence is the one outcome-free anchor, and it is **stable across segments and timeframes (1.40–1.52 from 1m to 5m)**. So k = 1.5 is "an outlier body against the local delivery", not a tuned number.
* **clv.** 0.5 never binds at k = 1.5, so a body ≥ 1.5 × A always closes in its upper half. Between 0.67 and 0.8 the event set barely moves (Jaccard 0.92–0.95). 0.75 ("the outer quarter") removes the 12 % with a large closing-side wick.
* **beyond.** One candle removes 2 % (the rule is nearly implied by the other two), while a 10- or 20-candle range break removes 23–41 %. That condition is structural (context), not displacement.
* **TR length.** 10–20 agree at 0.78–0.86. 14 is the length already used by Phase 1 (DEF-A2) and by the CISD body / TR metadata.

## F · CISD relationship (the frozen CISD-R oracle, not modified)

On the same data, 290 CISDs fall where a displacement is decidable (bar ≥ 19).

| relation | count | share |
|---|---|---|
| CISD whose confirming candle **is** a displacement | 34 of 290 | 12 % |
| CISD with **no** same-side displacement within ±5 bars | 231 of 290 | 80 % |
| displacement that **is** a CISD's confirming candle | 34 of 110 | 31 % |
| displacement with **no** same-side CISD within ±10 bars | 27 of 110 | 25 % |

Real examples to look at in TradingView (New York time):
* **CISD + displacement.** NQ1! 2026-10-27 10:22 bullish (body 1.73 × A) · 18:02 bearish (3.50 × A, right after the CME reopen) · 19:58 bearish (1.56 × A) · 21:00 bearish (2.74 × A).
* **CISD without displacement.** NQ1! 2026-10-27 04:38 bullish · 04:41 bearish · 04:49 bullish · 05:14 bearish.
* **Displacement without CISD.** NQ1! 2026-10-27 05:08 bullish (1.55 × A) · 06:14 bearish (2.13 × A) · 06:47 bearish (1.73 × A) · 07:14 bearish (1.52 × A).

**Conclusion: two distinct modules.**
* Most CISDs (80 %) occur without displacement near them, and a quarter of displacements occur with no CISD.
* "CISD with displacement" is a combination for a later context / quality layer. It is not part of either definition.
* CISD-R is unchanged.
* The CISD record's body / TR metadata is the **same number** as DISPLACEMENT-R's body_k for that candle (same A, the bar before). The displacement module still computes its own and never reads a CISD record (§H, DEF-DISP9).

## G · FVG relationship

| relation | value |
|---|---|
| DISPLACEMENT-R candles that leave a raw FVG (as candle 2, known one bar later) | 85 % |
| … that leave a Phase 1 FVG (≥ 2 ticks and ≥ 0.10 × TR average) | 84 % |
| Phase 1 FVGs whose candle 2 is a DISPLACEMENT-R candle | 92 of 652 (**14 %**) |
| Candle 2 of the Phase 1 FVGs, body / A in the FVG's direction | Q1 0.64 · median 0.92 · Q3 1.30; 56 % below 1 × A, 84 % below 1.5 × A |

**Decision: FVG creation is OPTIONAL METADATA** (the record's `fvg` fact, stamped on the next bar), not a requirement:
* Most FVGs are created **without** meaningful displacement, so an FVG cannot define displacement.
* Requiring it (D5) delays every event by one bar and moves it off the CISD candle (31 % → 2 %), while adding little (85 % already leave one).
* "Displacement that left an FVG" is a natural higher-quality class for a later context module, as is the later IFVG work. IFVG is not started.

## H · DISPLACEMENT-R: exact specification (recommended)

Constants:
* EPS = 0.01 × tick;
* k = 1.5 (the Tukey fence, §E);
* clv = 0.75;
* N = 14.

Per candle t, at its close:

| rule | bullish | bearish (exact mirror) |
|---|---|---|
| DEF-DISP1 direction | `close > open + EPS` | `close < open − EPS` |
| DEF-DISP2 yardstick | `A = SMA(TR, N)` of bars t−N … t−1, TR = `ta.tr(true)` (bar 0: high − low). No decision while A is undefined (t < N) or A = 0 | same |
| DEF-DISP3 body | `close − open ≥ k × A` | `open − close ≥ k × A` |
| DEF-DISP4 strong close | `close − low ≥ clv × (high − low)` | `high − close ≥ clv × (high − low)` |
| DEF-DISP5 beyond the previous candle | `close > high[t−1] + EPS` | `close < low[t−1] − EPS` |

**Confirmation timing.** A displacement exists iff all five hold. It is confirmed **at the candle's close**: the earliest deterministic closed-bar decision. It is never intrabar, and never needs a later bar.

**Edge cases.**
* **Doji, equal open / close, zero-range candle.** Never a displacement: DEF-DISP1 fails.
* **Gap open.** The body counts only open → close, so the gap is not displacement. The gap enters the true range of its bar, so it raises A for the next 14 bars.
* **Session boundary (CME 17:00–18:00, weekends).** No reset and no session logic. The previous candle is the previous chart bar, even across the break. The gap at the reopen enters TR as above. Example: NQ1! 2026-10-27 18:02 is a displacement 2 bars after the reopen.
* **Tiny A.** No absolute floor, so the rule stays instrument-agnostic. A = 0 means no decision. On NQ 1m, A never fell below 4.2 points.
* **Large news candles.** They qualify (no cap). They raise A for 14 bars, so the candles right after them need more. Only 2 of 110 events had a body ≥ 4 × A.
* **Overlapping and consecutive candles.** Each qualifying candle is its own displacement. A candle has one direction, so there is at most one record per bar. A candle closing inside a bigger previous candle is not a displacement (DEF-DISP5).

**What it detects.** One closed candle that reprices aggressively against its own neighbourhood: a net body that is an outlier against the local true range, accepted at the extreme, and closed beyond the previous candle.

**What it intentionally does NOT detect.**
* Absolute size, volatility regimes or sessions.
* Two-sided wide candles, or pushes rejected inside the bar.
* Multi-candle legs without a qualifying candle (§J, M5).
* Context: sweep, CISD, FVG, DOL, structure, session.
* Any prediction.

**What later context / quality modules may add** (metadata or classes, never retroactively):
* a CISD on the same candle or nearby;
* a liquidity sweep before it (Phase 2 events);
* the FVG left (the record's `fvg` fact; the Phase 1 FVG id is `FVG_CREATED` at bar t+1 with origin t−1);
* a structural break (Phase 2 BSL / SSL break on the bar);
* the DOL direction, the HTF FVG position, the session;
* a multi-candle "displacement leg".

**Why it is preferred over the other candidates.**
* **Body-based (D1 / D2 / D6) over range (D1r).** It separates delivery from two-sided volatility: higher FVG rate, stronger closes.
* **Over relative-median (D3).** No unstable yardstick in quiet periods.
* **Over the multi-bar candidates (D4 / D4r).** No windowing or run-ending choices, earliest confirmation, an unambiguous candle. The multi-bar candidates remain a different object (§J).
* **Over FVG-required (D5).** Not one bar late, not tied to the next candle.
* **Over the recent-range break (D7).** That is context.
* **Over D2.** D6 adds the parameter-free "beyond the previous candle": the close leaves the previous candle's range, so a large candle still contained within it is not displacement.

## I · Event and record schema

**Events.**
* `DISPLACEMENT_CONFIRMED`: on the candle's bar. dir = side, id (sid) = the candle's open time, price = close, origin = the bar itself.
* `DISPLACEMENT_DROPPED_MEMORY`: when the oldest record leaves memory (memory 50). Displacement has **no lifecycle**: no ACTIVE / ENDED, no invalidation. The drop event is storage bookkeeping, kept like every IST module with bounded memory (M6).

| record field | meaning |
|---|---|
| id, side, bar, time | identity: the candle's open time and direction |
| open, high, low, close | the candle |
| tra | A, the TR average of the 14 bars before |
| body_k, range_k | side × (close − open) / A, (high − low) / A |
| clv | the close location in side coordinates |
| prev_ext | the previous candle's high (bullish) / low (bearish) that the close cleared |
| fvg | `None` until the next bar closes, then whether the candle is candle 2 of a raw FVG in its direction (`low[t+1] > high[t−1]`, strict); never changes afterwards |

**Not stored (derivable or context).**
* body and range: from OHLC.
* CISD proximity, sweep, structural break, DOL, session: context modules, later.

## J · Oracle implementation summary

The oracle is `validation/models/displacement.py`, opt-in module `"disp"`. It is not in the default run, the regression baseline or parity.

**`DisplacementEngine`.** Per bar:
1. stamp the FVG fact of the record on bar t−1;
2. decide candle t (side coordinates, one code path for both sides);
3. memory.

**Wiring.**
* Settings: `DispSettings(k=1.5, clv=0.75, tra_len=14, memory=50)`. These are the definition's constants; they vary only in tests.
* Events: `ORACLE_ONLY`, so ST-14 excludes them until Pine has them.

**Results.**
* **Equals the study.** The oracle is record-for-record identical to the study's D6 on the three segments: 110 records, 57 / 23 / 30.
* **Stateless.** It needs the last 15 candles only, so a reload or a different history start cannot change any displacement after bar 14. This is the main difference from CISD, which has a delivery state.
* **Known false negative of the one-candle rule.** Fast multi-candle moves without a qualifying candle:

| multi-bar candidate (Tukey fence) | per hour | events | containing a DISPLACEMENT-R candle | raw FVG left |
|---|---|---|---|---|
| 2-candle travel ≥ 2.1 × A | 1.74 | 110 | 66 % | 95 % |
| 3-candle travel ≥ 2.5 × A | 1.61 | 102 | 58 % | 96 % |
| directional run ≥ 2.7 × A | 1.82 | 115 | 42 % | 97 % |

## K · Validation (test totals)

* `validation/tests/test_displacement.py`: 26 deterministic tests, every run invariant-checked.
  * Thresholds: the exact body threshold; one tick below and above; the bearish mirror (incl. FVG facts); doji / equal open-close.
  * Close shape: weak close; the exact strong-close threshold and one tick below; large wick + small body; large body + modest range; close at vs one tick beyond the previous high.
  * Edge cases: consecutive displacements; the staircase false negative; gap open + session break (61 min); TR warm-up (bar 13 vs 14); A = 0; the TR length setting.
  * Records and events: FVG fact on the next bar only; event fields; memory + drop event.
  * Real data and determinism: oracle = study (110); real counts; module toggles (alone = with every module); other modules unchanged; the default run has none; identical history → identical results; prefix = the past of the full run; translation; settings round trip.
* `validation/fuzz/test_displacement_properties.py`: invariants; mirror; translation; no lookahead; other modules unchanged; no other module read; long walks (3 in full mode).
* `validation/tests/test_displacement_study.py`: 24 harness tests (symmetry and no lookahead for all 9 candidates, D5 / D4r timing, fences = constants, quoted numbers, the session control, the shuffle).
* **Invariants INV-DISP-01…06**, each with a negative corruption test:

| id | checks |
|---|---|
| INV-DISP-01 | the rule, recomputed from candles: a record iff a displacement |
| INV-DISP-02 | the fields |
| INV-DISP-03 | the FVG fact: next bar, never missed |
| INV-DISP-04 | frozen records |
| INV-DISP-05 | events = records |
| INV-DISP-06 | memory and order |

* **FULL validation (validation 1.16.0): PASS**, exit 0, 620.8 s, **845 passed, 1 skipped** (the long-standing parity skip). Displacement-specific: 26 oracle + 24 study + 6 property + 3 long walks + 6 negative = 65 tests. Every other section is unchanged (static 21/21, CISD 167/167, LRL 85/85, HTF 46/46, parity 119/120, golden 8/8).

## L · Pine feasibility and risks (no Pine yet)

**Feasible, O(1) per bar, ST-21-safe.** Every history read stays at global scope:
* `float dispTra = ta.sma(ta.tr(true), 14)` and `float dispTraPrv = dispTra[1]`;
* `high[1]` / `low[1]`;
* for the FVG fact: `low > high[2]` / `high < low[2]`.

These are passed as arguments to the record methods, with no loops, no `request.security`, and no history buffer beyond 2 bars plus the SMA. It uses its own TR series rather than reading the frozen CISD's `cisdTraPrv`: the numbers are identical, but the modules stay independent (M9).

**Risks.**
1. **Exact ties.** A is a float average. Pine's `ta.sma` and Python's sum may differ by 1 ulp, so a body exactly at 1.5 × A could flip. This does not happen on real tick-grid data except in constructed cases; parity would show it as a DIFFERENCE with the numbers.
2. **Display clutter.** 1.7/h on 1m. The renderer is not designed: styling is frozen, and the decision is the user's.
3. **Warm-up.** The first 14 bars of a chart cannot have displacement. This is not a reload risk (stateless).
4. **Alert volume.** Alerts default OFF (proposal).

## M · Unresolved questions for the user

| # | decision | recommendation |
|---|---|---|
| M1 | k (body / A) | **1.5** (the Tukey fence, stable 1.40–1.52 on 1m–5m). Alternatives: 1.25 (3.2/h) or 2.0 (0.8/h) |
| M2 | strong close | **0.75** (outer quarter; removes 12 %). Alternatives: 2/3 (+6 %), or none |
| M3 | close beyond the previous candle | **keep** (parameter-free; separates directional repricing from a large candle contained within the previous one; removes 2 %) |
| M4 | constants or [calc] inputs | **constants**, like CISD-R (one definition, one parity) |
| M5 | multi-candle "displacement leg" | **not in DISPLACEMENT-R**; a separate, later object or context class if wanted (34–58 % of fast multi-bar moves have no qualifying candle) |
| M6 | events | **CONFIRMED + DROPPED_MEMORY**, memory 50; no lifecycle |
| M7 | FVG fact | **raw geometry** (strict DEF-A1), metadata only; the Phase 1 qualified FVG stays the FVG module's |
| M8 | absolute floor on A | **none**; A = 0 → no decision |
| M9 | TR series in Pine | **own** `ta.sma(ta.tr(true), 14)[1]`, not the CISD's variable |
| M10 | human goldens | none exist for displacement. The user may label real examples (§F lists candidates to check) |
| M11 | renderer and alerts | not designed (styling frozen); later |
