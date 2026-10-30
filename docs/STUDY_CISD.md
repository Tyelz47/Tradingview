# CISD research study · change in state of delivery

**Status: APPROVED by the user on 2026-10-30 (CISD-R, D-C1…D-C12, with clarifications).** The specification is now `docs/CISD.md`, and the oracle is `validation/models/cisd.py` (validation 1.12.0, no Pine yet). This study is kept as the research record.
* **Correction (validation 1.12.0):** the reload figure "≤ 4 CISDs, ≤ 62 bars" below covered starts in the first 600 bars only. Over the whole capture it is ≤ 8 CISDs and ≤ 87 bars (`docs/CISD.md` §3).
* At the time of the study: no change to `src/IST.pine`, the oracle, Phase 1, Phase 2, LRL or HTF FVG; no reference model and no Pine code before approval (§N).
* Harness: `validation/studies/cisd.py` (`python -m validation.studies.cisd --svg docs/study_cisd`).
* Tests: `validation/tests/test_cisd_study.py`, report section `research.cisd`.
* Charts: `docs/study_cisd/cisd-R.svg` (recommended) and `cisd-2.svg` (a stateless candidate, for the clutter comparison).

**Data and honesty notes**
* Real data: the two evidence captures merged, NQ1! 1m, 2026-10-27 03:38 → 10-28 07:56 New York: **1,639 bars ≈ 27.3 h**.
  * 3m / 5m / 15m are the same bars resampled (547 / 329 / 110 bars). The 15m sample is too small to conclude anything.
* Noise control: random walks (`validation/candles.random_walk`: 6,000 bars, seed 1; more seeds in the tests).
* No statistic here shows a predictive edge, and none is claimed. Every follow-through rate's 95 % interval contains 50 %, on NQ as on the random walk.

---

## A · Formal semantics

All rules are written for the **bullish** CISD. The bearish CISD is the identical rule on the mirrored candle (open and close negated, high ↔ −low): §D.

| term | exact rule (EPS = 0.01 tick, as everywhere in IST) |
|---|---|
| opposing candle | a down-close candle: `close < open − EPS` |
| doji | `abs(close − open) ≤ EPS`; it is not opposing and it **ends** a run (D-C2) |
| opposing run (delivery series) | a maximal sequence of consecutive opposing candles |
| state of delivery | one value: unknown (start), bullish, or bearish. A bullish CISD can only occur while the state is not bullish; it sets the state to bullish |
| leg window | the bars from the bearish leg's start to now. The bearish leg starts at the **delivery extreme of the bullish leg before it** (its highest high among up-close candles). At the start of the data, it is bar 0 |
| delivery extreme | the lowest low **of an opposing candle** in the leg window (D-C4). An equal low moves it to the later candle (D-C3) |
| reference run | the opposing run that contains the delivery extreme. It may have started before the leg window: the series from the top |
| CISD level L | the **open of the reference run's first candle**: the opening price of the down-close series that delivered price into the low |
| confirmation | the first bar t after the run's first candle, and after the bar that set the bearish state, whose **close > L + EPS** (any candle colour, D-C5) |
| decision bar | t. Nothing about this CISD is known or drawn before bar t closes |

In one sentence: *a bullish CISD is the first close above the opening price of the down-close series that delivered price into the lowest low of the current bearish leg.*

## B · Candidate definitions

Five definitions were compared, all with the same exact candle vocabulary.

| | anchor (level) | context (which series counts) |
|---|---|---|
| **CISD-1** | open of the **last** opposing candle | none: the newest one, any time |
| **CISD-2** | open of the **first** candle of the newest opposing series | none |
| **CISD-3** | open of the first candle of the series into the leg's delivery extreme | **state of delivery** (alternating) |
| **CISD-4** | open of the last opposing candle of that series | state of delivery |
| **CISD-5** | CISD-3 | state of delivery, and the confirming candle's body ≥ 1 × TR average (displacement) |

Further variants, all on CISD-3:
* confirmation: A wick, B close (CISD-3 itself), C body (open and close beyond), D close + displacement (= CISD-5);
* doji skipped instead of ending a run;
* an equal extreme keeps the first candle;
* the leg extreme set by any candle (wicks of non-delivery candles included);
* a confirming candle that must close in the new direction.

**CISD-R (recommended) = CISD-3** with: close confirmation, doji ends a run, latest equal extreme, delivery extremes only, any candle colour.

## C · Formulas and pseudocode

Per bar t, both sides, in side coordinates (bearish side: the mirrored candle). Decided at the bar's close.

```
1  facts of the active record (bars after its confirmation):
     retest  = first bar with low ≤ L + EPS            (wick back to the level)
     reclaim = first bar with close ≤ L + EPS          (closed back at / through it)
     broken  = first bar with close < legLow − EPS     (closed beyond the protected leg extreme)
2  runs:  opposing(t) := close < open − EPS
          runStart(t) := t if opposing and not opposing(t−1) (a doji ends a run), else runStart(t−1) while opposing
3  delivery extreme (state context): if opposing(t) and low ≤ ext + EPS → ext := low, extBar := t,
          candidate := run containing t (its first candle's open = L), provided that run has a candle ≥ legStart
   the other side's leg window restarts at t whenever this side (the armed one) sets a new extreme
4  confirmation: armed side, candidate exists, t > run start, t > the bar the state flipped:
          CISD-R: close > L + EPS      A: high > L + EPS      C: min(open, close) > L + EPS
          D (CISD-5): close > L + EPS and close − open ≥ 1 × TRavg14(t−1)
5  on confirmation: emit CISD_CONFIRMED; state := this side;
          the other side's leg window := [this leg's extBar, t] (its extreme and candidate recomputed);
          this side's next window := [the other side's extBar, t]
   Before the first CISD both sides are armed; if both confirm on the same bar, neither is emitted (symmetry).
```

**Context "none" (CISD-1 / 2):**
* the candidate is the newest opposing series (or candle);
* it is consumed by its confirmation;
* a newer series replaces it;
* no state, so the same direction can repeat.

**Timing:**
* The level is an open that printed before the decision bar, at the run's first candle.
* It becomes the candidate at the close of the bar that set the delivery extreme (`known`).
* Confirmation is decided at a bar close.
* No value is ever revised.

## D · Direction (mirror)

**Bearish CISD:**
* opposing candle = up-close (`close > open + EPS`);
* delivery extreme = the highest high of an up-close candle in the bullish leg;
* L = the open of the up-close series into that high;
* confirmation = `close < L − EPS`;
* it sets the state to bearish.

Mirror symmetry is exact by construction, tested on scenarios and random walks for four candidates (`test_mirror_symmetry`).

## E · Real NQ results (NQ1! 1m, 27.3 h)

Retest, close back and leg extreme broken are measured before the record ends. "Within 3 bars" = ended by the next CISD within 3 bars (a flip-flop). Follow-through = +1 TR average in the CISD's direction before −1 TR average against, within 60 bars.

| definition | CISDs (bull · bear) | per hour | candidates → confirmed | lifetime median (bars) | retest · close back · leg broken | L − extreme (× TR) | ended ≤ 3 bars | follow-through (95 % CI) |
|---|---|---|---|---|---|---|---|---|
| CISD-1 last candle · no state | 514 (267 · 247) | **18.8** | 1601 → 514 | 6 | 76 % · 58 % · 34 % | 0.70 | 24 % | 50 % (46–55) |
| CISD-2 series · no state | 389 (209 · 180) | **14.2** | 797 → 389 | 6 | 77 % · 59 % · 34 % | 0.81 | 21 % | 53 % (48–58) |
| **CISD-3 / R series · state** | 121 (60 · 61) | **4.4** | 287 → 121 | 9 | 80 % · 65 % · **15 %** | **1.46** | 17 % | 51 % (42–60) |
| CISD-4 last candle · state | 327 (163 · 164) | 12.0 | 924 → 327 | 4 | 74 % · 56 % · 12 % | 0.88 | 44 % | 47 % (42–52) |
| CISD-5 = 3 + displacement | 51 (25 · 26) | 1.9 | 180 → 51 | 25.5 | 59 % · 45 % · 18 % | 2.13 | 6 % | 55 % (41–68) |

**Confirmation rules on CISD-3 (NQ):**

| rule | per hour | lifetime | retest · close back | close beyond L (× TR) | ended ≤ 3 bars |
|---|---|---|---|---|---|
| A wick | 8.3 | 4 | 89 % · 74 % | 0.00 | 44 % |
| **B close** | **4.4** | 9 | 80 % · 65 % | 0.35 | 17 % |
| C body (open and close beyond) | 3.3 | 12.5 | 74 % · 62 % | 0.60 | 8 % |
| D close + displacement | 1.9 | 25.5 | 59 % · 45 % | 1.30 | 6 % |

**Variants of CISD-3 (NQ):**
* leg extreme set by any candle: 4.0 / h;
* new-direction confirming candle: 4.4 / h (identical on this data);
* doji skipped: 4.3 / h;
* equal extreme keeps the first: 4.4 / h.

Exact set differences against CISD-R:

| variant | CISD-R events that change |
|---|---|
| doji skipped | 8 of 121 (7 %) |
| equal extreme keeps the first | 5 (4 %) |
| new-direction candle | 0 |
| leg extreme set by any candle | **22 (18 %)** |

D-C2, D-C3 and D-C5 are therefore minor, and they are settled by structure (§H), not by counts. D-C4 matters (§N).

**Timeframes (CISD-R, NQ resampled):**

| | 1m | 3m | 5m | 15m |
|---|---|---|---|---|
| CISDs per hour | 4.4 | 2.0 | 0.8 | 0.5 |
| CISDs per bar | 7.4 % | 10.1 % | 7.0 % | 12.7 % |

* The definition has no bar-count or point parameter, so it means the same on every timeframe.
* The rate per bar is stable. The 15m sample (14 CISDs) is too small.

**Sessions (CISD-R, 1m):** Asia 4.5 / h · London 3.7 / h · NY AM 4.0 / h · NY PM 4.0 / h · other 4.8 / h. There is no session effect in this sample.

**Charts** (background `#C2BAAE`, the recommended renderer): `docs/study_cisd/cisd-R.svg`, against `cisd-2.svg` (stateless) for the clutter. The recommended CISDs sit:
* at the open of the up-close series into a top, or of the down-close series into a bottom;
* with a short line to the confirmation candle.

Choppy tops and bottoms produce clusters of 2–3 alternating CISDs (17 % end within 3 bars). That is a quality question (§F, §N), not a detection error.

## F · Synthetic scenarios

Each scenario has exact expected events for CISD-R (`test_recommended_definition_on_scenarios`), and the contrasts below are asserted (`test_the_candidates_differ_where_the_study_says`).

| # | scenario | CISD-R | what the others do |
|---|---|---|---|
| 1 | clean bullish | ▲ @5, L 100 (open of the down series) | CISD-1 / 4: @4 at 96.5 (last candle); body: @6 |
| 2 | clean bearish (mirror of 1) | ▼ @5, L 100 | mirrored everywhere |
| 3 | wick through only | — | wick rule: ▲ @5 |
| 4 | close exactly at L | — (strict) | wick rule: ▲ @5 |
| 5 | close one tick beyond | ▲ @5, retest @6 | — |
| 6 | false change: bounce below L, then lower (inside a bearish state) | nothing after the initial bearish CISD | CISD-1 / 4: false ▲ @7; CISD-2: a continuation ▼ @10 |
| 7 | strong trend, shallow pullbacks | ▲ @5 only | CISD-1 / 2: a new ▲ on every pullback (@9, @12, @15) |
| 8 | range / chop (closes exactly at the opens) | — | wick rule: a CISD on every bar (45) |
| 9 | immediate reversal (engulfing candle makes the low) | ▲ @3, on the extreme candle | body: @4 |
| 10 | multiple candidates | ▲ @12 at 98.5: the series into the **new** low, not the older 100 | CISD-1 / 2 fire on the intermediate swings |
| 11 | CISD, then a retest | ▲ @5, retest @6 | |
| 12 | CISD, then invalidation | ▲ @5, retest and close back @6, ▼ @7 at 95.5: the leg low breaks on the same bar | |
| 13 | mirror pair (11 mirrored) | ▼ @5, retest @6 | |
| 14 | displacement present | ▲ @20 | CISD-5: ▲ @20 |
| 15 | same structure, no displacement (creeping) | ▲ @35 | CISD-5: none |
| 16 | doji inside the series | ▲ @5 at 98.25 (the doji ends the series) | doji skipped: ▲ @6 at 100 |

Scenarios 6, 7 and 10 begin with a CISD that establishes the state, because they study behaviour inside a state. At the start of the data, the state is unknown, so the first CISD may be a continuation (the warm-up, §M).

## G · Noise / random-walk comparison (6,000 bars, 100 h)

| definition | NQ per hour | random walk per hour | NQ L − extreme (× TR) | walk L − extreme (× TR) |
|---|---|---|---|---|
| CISD-1 | 18.8 | 19.6 | 0.70 | 0.80 |
| CISD-2 | 14.2 | 14.5 | 0.81 | 0.96 |
| **CISD-R** | **4.4** | **5.2** | **1.46** | **1.74** |
| CISD-4 | 12.0 | 12.9 | 0.88 | 0.98 |
| CISD-5 | 1.9 | 3.5 | 2.13 | 1.87 |

**What this shows:**
* Every definition fires on structureless noise at about the NQ rate.
* Retest (78–80 %), close back (65–70 %) and follow-through (≈ 50 %) are the same on NQ and noise.
* **A CISD is a structural description of price, not a signal.** Its value comes from context (liquidity taken, displacement, HTF FVG, DOL), which is exactly why the context layer must stay separate.
* The stateless definitions are 3–4× more frequent than CISD-R on both data sets. Most of their events are pullback continuations (scenario 7).

## H · Recommended definition: CISD-R

**CISD-R** = series open · state of delivery · close strictly beyond · delivery extremes · doji ends a series · equal extreme → the later candle · any confirming candle.

**Why:**
1. **It is the concept, made exact.** The level is the opening price of the opposing delivery series into the extreme. The "change in state" is literal: one bit of state that a CISD flips. Same-direction repeats (continuations) are impossible by construction (scenario 7), and a bounce that does not close beyond the series open is nothing (scenario 6).
2. **No parameters.** There is no bar count, point threshold or TR multiple. It means the same on 1m, 3m, 5m and 15m, and there is nothing to tune.
3. **Least clutter.** At most one candidate exists at any time (tested), there is one active CISD, and 4.4 / h on NQ 1m. The stateless definitions run 14–19 / h with two live candidates.
4. **Clean lifecycle.**
   * A close beyond the protected leg extreme never precedes the opposite CISD: 0 cases on NQ and on the 100 h walk.
   * Rare gap-only exceptions exist on very long or gappy walks: 1 per 20,000 bars.
   * So "invalidation" needs no separate rule (§I).
5. **Non-repainting and prefix-invariant.** Every input is a printed open, a closed bar's close, or a closed bar's low.
6. **Displacement stays out** (§6 of the request). CISD-5 removes 58 % of the CISDs on NQ, so displacement is clearly a *different* property: a quality of the confirming leg. It also does not separate NQ from noise (1.9 vs 3.5 / h; follow-through intervals overlap 50 %). Displacement therefore belongs to its own engine. Each CISD record carries `body / TR average` of its confirming candle, for that engine.

**Why not the others:**
* **CISD-1 / CISD-4 (last-candle anchor):** the level is the nearest candle's open. That fires on minor bounces (scenario 6), half of them flip within 3 bars (CISD-4: 44 %), and the legs are under 1 TR.
* **CISD-2 (stateless series):** it repeats on every trend pullback.
* **Wick (A):** confirms without any close beyond (median close beyond L = 0.00 TR) and flips in chop on every bar (scenario 8).
* **Body (C):** confirms one bar later by design (scenario 1). It is a legitimate *stricter confirmation* option for a later quality layer, not the base event.

## I · Lifecycle / state model

| state | meaning | entered | left |
|---|---|---|---|
| (internal) candidate | the open of the series into the current leg's delivery extreme; at most one per chart; **no event, not drawn** (Debug only) | a new delivery extreme with a series in the leg | a further extreme (replaced), or confirmation |
| **ACTIVE** | the confirmed CISD that defines the current state of delivery | CISD_CONFIRMED (decision bar = the confirmation close) | the opposite CISD's confirmation bar |
| **ENDED** | history | the opposite CISD_CONFIRMED (same bar) | dropped by memory |

**Facts stamped once on the ACTIVE record:** these are record facts, not states, and none has an event in the proposal.

| fact | stamped on | NQ (before the record ends) |
|---|---|---|
| `retest` | the first later bar whose wick reaches L | 80 % of CISDs, median **1 bar** after the confirmation; noise: 78 % |
| `reclaim` | the first later bar that closes at or back through L | 65 %; noise: 70 % |
| `broken` | the first later bar that closes beyond the protected leg extreme | always on or after the opposite CISD's bar (§H 4) |

**Not kept:**
* **expired:** an active CISD stays the state until the opposite CISD, so expiry has no structural meaning;
* **superseded:** there is no same-direction supersession in a state model;
* **invalidated:** subsumed by the opposite CISD, so it would duplicate an event.

## J · Event model

| event | when | price | identity |
|---|---|---|---|
| `CISD_CONFIRMED` | the confirmation bar (decision bar) | L | dir ±1, sid = the series' first candle open time (the origin) |
| `CISD_DROPPED_MEMORY` (proposed; D-C7) | memory policy removes an ENDED record | L | same |

**Not proposed as events:** RETEST (it happens on the next bar 80 % of the time, on NQ and noise alike), INVALIDATED (subsumed by the opposite CISD), and ENDED (it is the opposite CISD_CONFIRMED on the same bar).

* Timestamps are immutable: one record per (dir, origin time).
* Alerts: CISD_CONFIRMED, default OFF, like every non-Phase-1 alert.

## K · Renderer proposal (matches the reference charts; no new styling work now)

* **One short horizontal line per drawn CISD:**
  * at L, from the origin candle (the series' first candle) to the confirmation candle;
  * 1 px, colour `#4F473F` (the HTF FVG text colour), opaque.
* **Small text `CISD`** at the right end of the line: tiny; below the line for bullish, above it for bearish. No box, no fill, no marker on other candles.
* **Visibility (D-C8):**
  * default: the **ACTIVE CISD only** (one line);
  * option: also the previous one (the one it replaced), faded.
* All records stay logical, whatever is drawn.
* Candidates: never drawn, except a dotted Debug option.
* Objects: ≤ 2 lines + 2 labels.
* The line is *not* extended to the right: the reference charts show a short level, and the active state is implied by it being the latest.

## L · Oracle / validation plan (after approval)

* **Oracle:**
  * `validation/models/cisd.py`, an opt-in module `"cisd"` (not in default runs or the regression baseline, like `lrl` / `htf`);
  * written from §A–§C, not from this study's harness. The study harness becomes its cross-check: equal events on all scenarios, NQ and walks.
* **Invariants** (`INV-CISD-01…`), each with a negative test:
  1. level = the open of the reference series' first candle;
  2. that series is opposing, contains the delivery extreme, and lies in the leg window;
  3. the confirmation bar is the FIRST bar after the state flip whose close is strictly beyond L, and no earlier bar qualified;
  4. directions alternate; one ACTIVE record; at most one candidate;
  5. an ACTIVE record ends exactly on the opposite CISD's bar;
  6. facts (retest / reclaim / broken) are each the first qualifying bar after the confirmation, never revised;
  7. identity and level are frozen;
  8. events ↔ records;
  9. memory ≤ N, ended records dropped first.
* **Scenario tests:** the 16 scenarios, plus boundary cases at ±1 tick and EPS. Golden real cases: 5–10 CISDs on the NQ evidence capture, labelled by the user (needed: I cannot label "true" CISDs myself).
* **Properties (Hypothesis):** mirror, translation, prefix (no lookahead), and reload convergence (synchronisation within a bounded number of CISDs). Phase 1 / 2 / LRL / HTF event streams must be identical with CISD on.
* **Pine static checks (ST-20):**
  * the exact formula lines: opposing candle, doji, run start, extreme update with ties, close > L + EPS, flip and window restart;
  * unique method names (ST-18);
  * event names (ST-14);
  * calc vs view (ST-01, ST-06).
  * Mutation tests: wick instead of close, ≥ instead of >, last-candle anchor, no state, extremes from any candle, doji skip, no window restart.
* **Parity capture:**
  * `cisd=1`;
  * a state snapshot after the first captured bar (state, each side's leg window start, extreme, extreme bar, candidate origin and level, current run start), so the replay starts from Pine's exact state;
  * per BAR: the candidate level per side (`CL` / `CS`) and the state (`ST`);
  * events with dir, origin, L.

## M · Pine feasibility / resources

* **State:**
  * per side: run start, last opposing bar, leg window start, extreme, extreme bar, candidate (origin, level), plus the state bit;
  * per-bar series `runStart` and `lastOpp` for history references;
  * records: a small array (memory 50).
* **Work per bar:** O(1).
  * At a flip, the new window's extreme is recomputed by a loop from the opposite extreme bar to now. On NQ that window is median 3 bars (max 84), and a whole leg from series start to confirmation is median 4 bars (max 90). It still needs a bound and `max_bars_back` on low / high / the run series. Proposal: 500 bars.
* **Objects:** ≤ 2 lines + 2 labels.
* **Requests:** none. Chart timeframe only; an HTF CISD is a separate later question.
* **Non-repainting:**
  * decisions at bar close (Confirmed mode);
  * Live mode would still confirm only at the close, like DEF-A creation.
* **Warm-up / reload:**
  * The state depends on history, but forgets it quickly. From 86 different first bars, the truncated runs matched the full history after **≤ 4 CISDs (median 1)** and **≤ 62 bars (median 15)** on NQ (`test_reload_convergence`).
  * So CISDs in a chart's first bars can differ between reloads that move the first loaded bar. Proposal (D-C9): mark the first 200 bars after the first loaded bar as warm-up (computed, not drawn or alerted).
  * The parity snapshot removes the issue for validation.
* **Calculation inputs:** none (no thresholds). Display inputs: Show CISD, Show previous CISD; Developer: candidates.

## N · Open decisions for the user

| | decision | recommendation |
|---|---|---|
| D-C1 | definition | **CISD-R** (series open · state of delivery · close strictly beyond) |
| D-C2 | doji inside a series | ends the series (8 of 121 CISDs differ on NQ) |
| D-C3 | equal extreme | the later candle moves the reference (5 of 121 differ) |
| D-C4 | what sets the leg extreme | only delivery (opposing) candles (22 of 121 CISDs differ). With any candle, a wick spike from a non-delivery candle can leave no candidate while price breaks the leg (an NQ case: bar 863's upper wick, leg broken at bar 881 with no CISD) |
| D-C5 | confirming candle colour | any candle's close (the canonical "close above"; the new-direction variant has more gap exceptions on walks, and is identical on NQ) |
| D-C6 | events | `CISD_CONFIRMED` only. Retest / close-back / leg-broken as record facts for the context layer, no events |
| D-C7 | memory | 50 records, oldest ENDED first, with `CISD_DROPPED_MEMORY` (IST convention) |
| D-C8 | display | the ACTIVE CISD only; option: the previous one faded |
| D-C9 | warm-up | 200 bars after the first loaded bar are not drawn or alerted (reload stability) |
| D-C10 | displacement | not in CISD. The confirming candle's body / TR average is stored for the displacement engine |
| D-C11 | timeframe | chart timeframe only for now |
| D-C12 | alerts | `CISD_CONFIRMED` alert available, default OFF |

**What a future IFVG / context engine can read from a CISD record:**
* side;
* origin (series start bar and time);
* level L;
* the delivery extreme (bar, price) and the protected leg extreme;
* the confirmation bar;
* `body / TR average` of the confirming candle;
* facts: retest, reclaim, broken;
* end bar (the opposite CISD);
* the delivery leg = origin → extreme → confirmation.
