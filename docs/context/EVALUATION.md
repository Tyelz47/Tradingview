# IST · CONTEXT-03 · DOL evaluation harness (pre-registration)

**Status: RESEARCH (2026-11-03, branch `context/research`), awaiting the user's review.**
* No Primary-DOL policy exists or is approved. Directional context is not implemented.
* Nothing here is optimised, and every result on the repository's sample is **descriptive only**.
* Code:
  * `validation/models/outcomes.py`: the outcome oracle;
  * `validation/models/dol_policy.py`: the policy interface and the baselines;
  * `validation/studies/context_eval.py`: the harness;
  * `validation/studies/context_dataset.py`: the dataset contract, DATASET_CONTRACT.md.
* Tests: `test_outcomes.py`, `test_dol_baselines.py`, `test_context_dataset.py`; report section `evaluation`.

```
TARGET UNIVERSE (CONTEXT-02) ─▶ HYPOTHESIS AT t ─▶ FUTURE OUTCOME LABEL ─▶ METRICS
        FEATURES_AT_T                (frozen)          OUTCOME_AFTER_T
```

* The two passes never mix.
* During the target-universe pass, at each decision bar, a policy receives one frozen `Snapshot` and returns a frozen hypothesis or none.
* After the pass, the evaluator receives the frozen hypothesis and **only** the bars after t; it refuses any other bar.
* A test replaces every later bar and checks that no hypothesis changes.

## 1 · Three facts per level and bar: never merged

| concept | upper target (▲) | lower target (▼) | used for |
|---|---|---|---|
| **EXACT_TOUCH** | `high == price` | `low == price` | diagnostic |
| **TARGET_REACHED** | `high >= price` | `low <= price` | **the DOL question: did price get there?** |
| **TARGET_TAKEN** | `high > price` | `low < price` | DEF-L4 consumption, then SWEEP / BREAK by that bar's close |

* A crossing (target 20000, high 20005) is REACHED and TAKEN, without an EXACT_TOUCH.
* An exact touch is REACHED, not TAKEN: the diagnostic `TOUCHED_NOT_TAKEN`.
* Phase 2's semantics are not changed; this layer only reads prices.

## 2 · Definitions (DEF-EV1 … EV10)

**DEF-EV1 · Hypothesis.** A frozen record, fixed at t from information available at t, with no future field:
* `policy_id`, `t`;
* the target id / side / price;
* the opposite comparator id / side / price;
* the decision close;
* the horizon end and its rule;
* `info` (key / value pairs known at t).

**DEF-EV2 · Outcome contract v1.** One label per hypothesis:

| label | when |
|---|---|
| `PRIMARY_REACHED` | the primary is REACHED before the opposite comparator |
| `OPPOSITE_REACHED_FIRST` | the comparator is REACHED first |
| `BOTH_SAME_BAR_UNRESOLVED` | both are REACHED in the same lowest-resolution bar. The order is never inferred from the candle's direction or shape |
| `UNRESOLVED` | neither by the horizon, which was fully observed |
| `CENSORED` | the data ends, or a contract roll or other data boundary comes, before the horizon with nothing decided |
| `DATA_INVALID` | an integrity issue (DATASET_CONTRACT §3) before anything was decided; or at t itself (then no hypothesis is issued) |
| `NO_HYPOTHESIS` | the policy abstained or could not form a hypothesis (reasons `ABSTAIN` · `NO_CANDIDATE` · `NO_COMPARATOR`). **It is never a failed prediction** |

* `CONTEXT_INVALIDATED` is reserved (`outcomes.NOT_APPLICABLE`) and **never emitted**. It needs a directional context and its invalidation semantics (CONTEXT-04).
* A decisive bar before an integrity issue keeps its label. Bars at or after an issue, a roll or the horizon are never read.

**DEF-EV3 · The opposite comparator is pre-registered.**
* Each policy names the primary, the comparator and the horizon at t, by a rule fixed before any outcome.
* A policy that cannot name its comparator emits `NO_HYPOTHESIS (NO_COMPARATOR)`. The comparator is never chosen after the future is seen.

**DEF-EV4 · The horizon is pre-registered.**
* **H0 = 17:00 ET, the CME close of the trading day that contains the minute after t.** It is computed from the clock alone. It is the primary evaluation horizon, fixed now, before any policy comparison.
* Sensitivity horizons (the end of the current session window, or fixed spans of 1 h / 2 h / 4 h) may be reported later as a separate, labelled run. They are **never** used to pick or tune anything.

**DEF-EV5 · Decision points.**
* The close of the bar before every session window opens (Asia 20:00, London 02:00, NY AM 09:30, NY PM 13:30 ET), read from the clock.
* There must be ≥ 200 bars of history before it (the DEF-CISD9 guard; the oracle has no Pine history before a dataset starts).
* There must be no integrity issue between the start of the data and t.
* The rule is fixed, so no case is chosen.

**DEF-EV6 · Geometric reference REF-A.**
* `P = d(opposite) / (d(primary) + d(opposite))`, the distances from the decision close.
* It is the probability that a **continuous, symmetric, driftless** path reaches the primary first (gambler's ruin).
* Assumptions, stated in full:
  * no drift;
  * no horizon (eventual hitting);
  * a constant volatility that cancels out;
  * no gaps;
  * the path starts at the close;
  * reaching by the path, while the bars report wicks.
* It is computed from t-only quantities before any outcome. It is compared with the **resolved** outcomes only: the summed REF-A against the PRIMARY_REACHED count.
* It is a yardstick against which a policy that only exploits geometry is not celebrated. It is not a model of NQ, and is not called a random-walk expectation beyond these assumptions.
* A horizon-aware reference (REF-B: simulated driftless paths with t-known volatility over the bars left to H0) is defined as future work, not implemented.

**DEF-EV7 · Same-bar ordering.**
* On 1m, two targets reached inside one bar stay `BOTH_SAME_BAR_UNRESOLVED`.
* Only a genuinely lower-resolution dataset of the same interval may resolve them, in a separate run.

**DEF-EV8 · Metrics.** These are reported per policy and per underlying (NQ and ES **never pooled**):
* the eligible decision points;
* the hypotheses emitted;
* NO_HYPOTHESIS by reason;
* coverage;
* every label count;
* `DATA_INVALID` at t;
* for the primary:
  * exact touches;
  * reached but never taken;
  * taken;
  * SWEEP;
  * BREAK.

The rates are:
* **resolved-only** = PRIMARY / (PRIMARY + OPPOSITE), beside the summed REF-A;
* **all-evaluable** = PRIMARY / (PRIMARY + OPPOSITE + SAME_BAR + UNRESOLVED). CENSORED and DATA_INVALID are not judgments, but they stay in the table.

There is no P&L, no Sharpe and no trade win rate.

**DEF-EV9 · DEVELOPMENT / OOS.**
* Trading days are split by date: up to a pre-registered `dev_until` is DEVELOPMENT, later is OOS. The split is never shuffled.
* Candidate policies are designed on DEVELOPMENT only.
* Before any OOS run, they are **locked**: `PolicyLock` stores each policy's fingerprint (its class source plus its parameters).
* An OOS evaluation refuses an unlocked policy, or one changed after its lock (tested).
* If OOS is weak, it is reported weak. Nothing is tuned on OOS and then called OOS again.

**DEF-EV10 · Eligibility profiles.**
* **STRICT:** only targets the universe calls AVAILABLE. Today that means Phase 2 targets only, because every G-V and T19–T22 gate is pending.
* **PROVISIONAL:** also the targets that are UNVERIFIED **only** because their source gate is pending, with their history observed and never consumed.
* PROVISIONAL results are conditional on those gates and are labelled so.

## 3 · Baselines (definitions, not candidates; DOL_RESEARCH §9 on the target universe)

| id | primary | pre-registered comparator | no hypothesis when |
|---|---|---|---|
| B0 | the nearest eligible external target (DAILY / WEEKLY / SESSION) | the nearest eligible external target on the other side | none, or none opposite |
| B1 | the nearest eligible target of any class | the nearest eligible target of any class opposite | as B0 |
| B2 | the nearer of the CURRENT PDH / PDL | the other one | either is not eligible |
| B3 | the nearest in the highest class present, by **B3's own order** WEEKLY > DAILY > SESSION > STRUCTURAL. That order is a baseline experiment, not semantics, and no hierarchy is approved | the nearest of that class opposite | no comparator in that class |
| B4 | `ABSTAIN` when eligible external targets exist on both sides; otherwise the nearest external target | the nearest eligible target of any class opposite | none |

Ties go to the target above; the rule was fixed before any outcome.

## 4 · Results on the repository sample (DESCRIPTIVE ONLY)

The sample:
* 4 segments, 83 h, NQ family (NQ1!, MNQZ2026, MNQ1!), no ES;
* **no complete trading day** (DATASET_CONTRACT §6);
* 13 decision points, all DEVELOPMENT; no OOS exists.

| policy | eligible | emitted | NO_HYP | PRIMARY | OPPOSITE | SAME_BAR | UNRES. | CENSORED | DATA_INV. | exact touch | reached, not taken | taken | SWEEP | BREAK | resolved-only · REF-A | all-evaluable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0@STRICT | 13 | 0 | 13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — |
| B1@STRICT | 13 | 11 | 2 | 7 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 11 | 7 | 4 | 7/11 · 7.8 | 7/11 |
| B2@STRICT | 13 | 0 | 13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — |
| B3@STRICT | 13 | 11 | 2 | 7 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 11 | 7 | 4 | 7/11 · 7.8 | 7/11 |
| B4@STRICT | 13 | 0 | 13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — |
| B0@PROVISIONAL | 13 | 7 | 6 | 4 | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 4 | 1 | 3 | 4/6 · 4.0 | 4/6 |
| B1@PROVISIONAL | 13 | 12 | 1 | 8 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 12 | 7 | 5 | 8/12 · 8.7 | 8/12 |
| B2@PROVISIONAL | 13 | 5 | 8 | 2 | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 2 | 0 | 2 | 2/4 · 2.7 | 2/4 |
| B3@PROVISIONAL | 13 | 4 | 9 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 1 | 3 | 3/4 · 3.2 | 3/4 |
| B4@PROVISIONAL | 13 | 4 | 9 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/4 · 0.5 | 0/4 |

NO_HYPOTHESIS reasons:
* B0@STRICT, B2@STRICT, B4@STRICT: NO_CANDIDATE 13. No external target is AVAILABLE while the gates are pending.
* B0@PROVISIONAL: NO_COMPARATOR 5, NO_CANDIDATE 1.
* B2@PROVISIONAL: NO_COMPARATOR 6, NO_CANDIDATE 2.
* B3@PROVISIONAL: NO_COMPARATOR 9.
* B4@PROVISIONAL: ABSTAIN 7, NO_CANDIDATE 1, NO_COMPARATOR 1.

**Reading.**
* Every resolved count sits on its REF-A reference within what 4–12 decisions can resolve.
* B1 (the nearest of any class) is reached first 8 / 12 times, where geometry alone expects 8.7. Proximity again explains itself.
* On 1m, no primary was reached by an exact touch: every reach was a crossing.
* No result here supports any policy, hierarchy or edge.

## 5 · What CONTEXT-03 does not mean

It does not mean that any baseline has an edge, that a Primary DOL policy exists, or that HTF directional context exists.
