# IST · CONTEXT-01 · Directional context research

**Status: RESEARCH (2026-11-03). Nothing in this document is a rule, and nothing is frozen.**
* The frozen modules (CISD-R, DISPLACEMENT-R, IFVG-R, Phase 1 / 2) are read as facts and never reopened.
* The numbers come from `validation/studies/context.py`, on 83 h of NQ / MNQ 1m.
* Hundreds of events reduce to **1–12 distinct outcomes** per fact type, because overlapping events share the same next external target. So every number below is descriptive, not evidence for a rule.

## 1 · States (initial vocabulary, not frozen)

| state | meaning (proposal) |
|---|---|
| UP / DOWN | the governing timeframe's delivery state agrees with the leg timeframe's, or the disagreement is a recognised retracement (§3) whose regime is UP / DOWN |
| MIXED | an explicit conflict rule fires (DOL_RESEARCH §8) |
| UNKNOWN | the inputs are missing: warm-up, the loaded-history boundary, no HTF data, nothing eligible |

The output carries its basis: per-timeframe states, phase, supporting facts, contradictions. A bare label is not enough. A user reading "DOWN" must see *why*.

## 2 · Evidence inventory

| fact | frozen definition | timescale on 1m (measured) | what it can say | what it cannot say |
|---|---|---|---|---|
| CISD state | DEF-CISD4: UNKNOWN → UP / DOWN, strictly alternating | 317 CISDs on bars ≥ 200; a median **8–11 bars** apart (§4) | the current *delivery leg* on its timeframe | the day's or the regime's direction |
| displacement | DEF-DISP1…6, one candle | 110 events | that a candle repriced strongly: energy | that the move continues |
| IFVG | DEF-IFVG, the parent's DEF-A5 close through | 622 inversions | that a zone flipped: a path element | a bias |
| LRL terminal | DEF-LRL5: DRIFT / SWEEP / BREAK / EXPIRED (**experimental**) | 26 sweeps, 26 breaks, 14 drifts | a diagonal pool was run (or the line decayed into price) | a target |
| Phase 2 sweep / break | DEF-L4 on 1m swings | 128 sweeps, 104 breaks | an internal pool was taken | a turn (§8) |
| external sweep / break | DEF-L4 applied to period / session extremes (context layer, read-only) | **5 sweeps, 11 breaks in 83 h** | the narrative anchor: external liquidity taken | — (too rare here to say anything) |
| HTF FVG | DEF-B0…B6 (**experimental**) | not measured in CONTEXT-01 | HTF delivery zones or obstacles | a target |
| location | position in R_D / R_W (TARGET_UNIVERSE §4) | outside R_D at 6 of 11 decision points | premium / discount *when inside* | anything when outside |

**Facts → the first external target reached** (descriptive). At each event bar e:
* take the nearest AVAILABLE external target above and below at e;
* see which one is reached first by the end of the trading day;
* compare with the driftless reference d(other) / (d(up) + d(down)).

| fact | resolved | first external reached on the event's side | driftless reference | distinct outcomes |
|---|---|---|---|---|
| CISD (1m) | 171 | 88 (51%) | 52% | 12 |
| IFVG inversion | 326 | 168 (52%) | 56% | 12 |
| displacement | 59 | 31 (53%) | 57% | 11 |
| Phase 2 sweep | 66 | 54 (82%) | 64% | 10 |
| Phase 2 break | 47 | 30 (64%) | 65% | 9 |
| LRL break · sweep · drift | 15 · 6 · 7 | 53% · 33% · 29% | 49% · 59% · 48% | 6 · 5 · 5 |
| external sweep · break | 3 · 2 | 100% · 100% | 54% · 65% | 3 · 1 |

**Reading.**
* No single fact points at the next external target better than its distance does.
  * CISD, IFVG and displacement each sit at or below their reference.
  * This matches what STUDY_CISD found for CISD alone.
* **The one visible difference** is Phase 2 *sweeps*: 82% against a 64% reference. After a 1m swing is swept, price went on to the external target **on the swept side**. These internal sweeps behaved as en-route liquidity, not turns.
  * Only 10 distinct outcomes stand behind that figure, so it is a hypothesis (H-CX4), not a finding.

## 3 · HTF hierarchy: three candidate models

The CISD-R definition applied to a higher timeframe's candles gives a delivery state per timeframe. This is research only.
* IST has no such engine: the frozen CISD runs on the chart timeframe.
* The study builds 15m candles from the 1m bars to illustrate it.

| model | rule | strength | failure mode |
|---|---|---|---|
| **A · regime dominates** | the context is the highest timeframe's state; the lower timeframes are ignored | simple, stable | late at HTF turns. It also points at the regime's DOL *during* a counter-leg, often for hours: in a 4H-DOWN regime with a 1H-UP retracement, Model A says "DOL below" while price delivers up to premium / BSL first |
| **B · regime + leg** | the higher timeframe gives the regime, the lower one gives the current delivery leg. Output: both states, plus a phase: ALIGNED (they agree) or RETRACEMENT (the leg is against the regime) | explicit; no weights; every conflict becomes a named phase instead of a number | needs a rule for when a retracement becomes a reversal; that is Model C |
| **C · state machine** | phases ALIGNED → RETRACEMENT → CONTINUATION (the leg turns back with the regime, typically after taking leg-side liquidity) or TRANSITION (the retracement closes beyond the regime's protected extreme, the regime CISD's `leg_ext`) → REVERSAL (the regime CISD flips) | captures the classic sequence (sweep → CISD → delivery) as transitions | needs per-timeframe CISD state, protected extremes and the target universe at once: the most data-hungry |

**Conflict examples, resolved without points (Model B):**
* "4H DOWN, 1H UP" = regime DOWN, leg UP, phase RETRACEMENT. Leg DOL = the leg-side internal target (BSL / premium inside the regime's range). Regime DOL = unchanged, below. Not MIXED.
* "Daily UP, 4H DOWN, 1H DOWN": the result depends on which timeframe is the regime.
  * With D as the regime: regime UP, leg DOWN (4H and 1H agree) → a deep RETRACEMENT.
  * With 4H as the regime: DOWN, ALIGNED with 1H.
* So **the regime / leg timeframes are a user decision (D-CX11)**, fixed before any evaluation, never chosen from results.

**What the data shows (illustration only).**
* 1m and 15m CISD states agree only **49–63%** of the bars where both are known (§4). They are different processes, and treating them as one bias would be noise.
* **1m CISDs against the 15m state** reached their own side's next external target first in **19 of 85** resolved cases, against a driftless reference of 38.7. Behind those 85 cases are **10 distinct outcomes**.
* That points in Model A / B's direction: a lower timeframe against the higher one fails more often. It is a hypothesis (H-CX2), not support.
* Each segment holds ≤ 20 completed 1H bars and ≤ 8 completed 4H bars (counting the 3-bar snapshot). **No regime-timeframe study is possible on the data in the repository.**

**Representation of HTF delivery (answer to Q7).** A per-timeframe vector `{tf: CISD-R state, last CISD (side, origin time), protected extreme (leg_ext)}` plus the phase.
* It is never one merged value.
* Each entry is traceable to a CISD record identity (side + origin time).

## 4 · CISD (frozen, used as context only)

| question | proposal |
|---|---|
| Does the latest confirmed CISD matter? | Yes: it *is* the delivery state of its timeframe (DEF-CISD4). On the chart timeframe it is the **leg**, not the bias |
| On which timeframe? | Regime and leg timeframes (D-CX11). On 1m it confirms every ~10 bars (segment medians 8.0 / 9.5 / 10.0 / 11 bars), so it is execution-scale |
| For how long? | Until the opposite CISD, by definition (DEF-CISD7). **No time decay is added**: that would be an invented parameter. Its relevance attaches to the leg it opens (from `ext_bar` to the next CISD) |
| When stale? | When the opposite CISD confirms. Its `broken` fact (a close beyond `leg_ext`) marks the protected extreme as lost: a candidate **invalidation** for the context built on it |
| Does an opposite CISD replace the state? | Yes, by definition: CISDs strictly alternate |
| HTF versus LTF CISD | An HTF CISD (the same definition on HTF candles) is regime / leg. The chart-timeframe CISD after an external sweep is the candidate *turn* evidence, H-CX1 in the narrative (§11). It needs a multi-timeframe engine; not now |

| segment | 1m CISDs (bars ≥ 200) | median bars between | 15m CISDs | bars where the 1m state = the 15m state |
|---|---|---|---|---|
| NQ1! 10-27 → 10-28 | 103 | 10.0 | 14 | 53% |
| MNQZ2026 10-29 → 10-30 | 71 | 9.5 | 9 | 63% |
| MNQZ2026 10-13 → 10-14 (replay) | 77 | 8.0 | 6 | 49% |
| MNQ1! 11-02 | 66 | 11 | 3 | 50% |

## 5 · Displacement (frozen, used as context only)

* Displacement is a single-candle fact with no lifecycle. Its relevance should be **relational, not timed**: it is attached to the delivery leg or CISD it belongs to. A "displaced CISD" = a displacement in the CISD's direction between its origin and its confirmation, read from the frozen records.
* Its FVG metadata (DEF-DISP7, `fvg = YES`) already links displacement and FVG creation: the "displacement FVG" candidate for quality (§12).
* Does it matter more after a sweep? This is **RESEARCH REQUIRED**: there were 5 external sweeps in the data, too few.
* On its own: the next external target was reached on its side in 53% of cases, against a 57% reference. In the data, **28 displacements** were followed first by the *other* side's external target (9 distinct outcomes; RESEARCH_CASES §4).

## 6 · IFVG (frozen, used as context only)

| relation | role |
|---|---|
| IFVG on the context side, between price and PRIMARY | DELIVERY_ZONE: where a retracement may reprice before delivery resumes |
| IFVG against the context, between price and PRIMARY | OBSTACLE: a contradiction, listed |
| IFVG after an external sweep | turn-evidence candidate (narrative, §11); RESEARCH REQUIRED |
| IFVG + CISD / + displacement | joint evidence by time order (the same leg), not by addition |
| HTF versus chart TF | there is no HTF IFVG (not started, by instruction). The chart-TF IFVG is a path element only |

* In the data, **93** inversions went against the 1m CISD state at that bar (11 distinct outcomes). The IFVG's own side was reached first in 61 of them, against a 47.5 reference.
* This is one more reason why a single 1m state is not a context. It is not evidence for the IFVG.

## 7 · LRL (experimental; it cannot be a frozen dependency)

* A high-side LRL is descending highs with buy stops above them. An **ACTIVE** one between price and an ▲ target = a low-resistance path toward that target: support, listed.
* An opposing LRL may be **inducement**: liquidity for a later run. That is RESEARCH REQUIRED.
* Terminal classes:
  * **BREAK**: the run was accepted;
  * **SWEEP**: the run failed: a failure-swing candidate for the narrative;
  * **DRIFT**: the projection decayed into price. It carries no information by construction, so it is never evidence.
* **LRL never decides a DOL** (DEF-LRL9). Its counts here (6 / 5 / 5 distinct outcomes) say nothing.

## 8 · Liquidity takes: internal versus external

* External takes (period / session extremes) are the narrative anchors, and they are **rare**: 16 in 83 h. Every resolved one continued on the taken side:
  * 3 sweeps of a level below → the next external below reached first;
  * 2 breaks → continuation.
* **No "external sweep → reversal" case exists in this data.** This is not a result; it is a sample of 5.
* Internal (Phase 2) sweeps behaved as **en-route liquidity** (§2). The working hypothesis is the ICT reading: internal liquidity is taken on the way to external liquidity (H-CX4).

## 9 · HTF FVG (experimental)

* An HTF zone is the same kind of object as a chart-TF zone: a path element (delivery zone or obstacle), weighted by nothing, labelled with its timeframe.
* It is **experimental**: any context that reads it inherits that status until HTF FVG is frozen (HTF-L12).

## 10 · Location and the dealing range

| candidate range | deterministic? | known at t? | problem |
|---|---|---|---|
| R_D = [PDL, PDH] | yes | yes | price was **outside** it at 6 of 11 decision points with R_D known (positions −1.32 … 1.05), so premium / discount is undefined half the time |
| R_W = [PWL, PWH] | yes | yes | wide; often UNVERIFIED mid-week (TARGET_UNIVERSE §3) |
| completed Asia range | yes | after 00:00 ET | small; useful for London / NY only |
| CISD leg (from the regime CISD's extreme to the running extreme) | yes, on one timeframe | yes | its other edge moves until the leg ends |
| external swing range / last liquidity-to-liquidity leg | **no** | — | which swings, which leg, when it dies, nesting: RESEARCH REQUIRED |

**Proposal.**
* v1 reports *positions* as facts: in R_D, in R_W, and in the Asia range, with values outside [0, 1] allowed.
* PREMIUM / DISCOUNT / EQUILIBRIUM labels are used only inside a range.
* Location is not used in any selection until a study defines a dealing range that is deterministic, reload-stable and known at t.

## 11 · Narrative: what it would need (not implemented)

An example narrative:

```
EXTERNAL BSL swept → LRL failure (high-side LRL_SWEEP) → CISD DOWN → bearish displacement → bearish FVG / IFVG → delivery to SSL / PDL
```

| step | fact (identity) | temporal relation to the previous step |
|---|---|---|
| external sweep | the first DEF-L4 take of an AVAILABLE ▲ external target, class SWEEP (target id) | — |
| LRL failure | `LRL_SWEEP` on the high side (LRL id), optional | after the sweep, in the same leg |
| CISD DOWN | `CISD_CONFIRMED` −1 (side + origin time), whose `ext_bar` is at or after the sweep bar | after the sweep. Its delivery extreme is the sweep's high |
| displacement | `DISPLACEMENT_CONFIRMED` −1 between the CISD's origin and the next CISD | inside the CISD's leg |
| FVG / IFVG | a bearish FVG (or an IFVG with side −1) created inside the leg | inside the leg; it becomes a DELIVERY_ZONE |
| delivery | PRIMARY_DOL = the nearest ▼ external target at class G | outcome only |

The relations needed are all **order and containment** ("after", "inside the leg"). None are time windows. Two things are still undefined:
* the end of a leg, which is the next CISD, by definition;
* whether a sweep must be the *leg's* extreme (`ext_bar` = the sweep bar) or only precede it: RESEARCH REQUIRED.

## 12 · Quality later: factors to study, not a score

The goal: **detect everything logically, but draw only what matters.**

| object | candidate factors |
|---|---|
| relevant FVG | on the PRIMARY path; aligned with the context; untouched; created by a displacement (DEF-DISP7 `fvg = YES`); inside the active leg |
| relevant IFVG | the same, plus "inverted after an external sweep" |
| high-context CISD | after an external take, with its `ext_bar` at the take; displaced (§5); on the leg timeframe and aligned with the regime |
| low-context signal | mid-range or outside every range; no external take in the leg; against the regime; 1m only |
| renderer priority | PRIMARY_DOL → ALTERNATE → path zones → NEXT → everything else in debug |

## 13 · Hypotheses for later phases (to test on a larger dataset)

| id | hypothesis | why it is only a hypothesis |
|---|---|---|
| H-CX1 | chart-TF CISD after an external take (with `ext_bar` at the take) precedes delivery to the opposite external target more often than the driftless reference | 0 such cases resolved in the data |
| H-CX2 | a lower-TF CISD against the higher-TF state reaches its side's external target less often than the reference | 19 / 85 against 38.7, but 10 distinct outcomes |
| H-CX3 | Model B (regime + leg) labels fewer decisions OPPOSITE_REACHED_FIRST than Model A, at equal abstention | needs HTF data (none) |
| H-CX4 | internal (Phase 2) sweeps are en-route liquidity: continuation to the same side's external target | 82% against 64%, but 10 distinct outcomes |
| H-CX5 | PRIMARY at class D beats B2 (the nearer of PDH / PDL) once context filters the side | needs a context engine and the dataset |
