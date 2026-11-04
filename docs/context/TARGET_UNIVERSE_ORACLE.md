# IST · CONTEXT-02 · Target universe oracle (DEF-TU1 … TU10)

**Status: APPROVED as the deterministic TARGET UNIVERSE milestone (user, 2026-11-03; commit `e1ee951`). A research / oracle milestone, not a frozen semantic baseline.**
* The approval covers no Primary DOL, no target hierarchy, no directional context, no HTF Model B and no predictive edge.
* **The user's decisions D-TU1…D-TU9 (§7) are applied in CONTEXT-03:**
  * identity by the SOURCE period;
  * sessions pending T19–T22;
  * temporal availability (OPEN / CLOSE);
  * EQ exactly as Phase 2;
  * the HTF restoration conditions;
  * EXACT_TOUCH naming.
* The CONTEXT-01 milestone is commit `6576bae`, a research record, not a frozen baseline.
* No Pine: `src/IST.pine` is byte-identical to `IFVG_BASELINE_v0.9.1-dev`. No frozen module, no LRL and no HTF FVG changed.
* Model: `validation/models/targets.py`. It is an observer, attached beside the oracle; `validation/models/ist.py` and `types.py` are unchanged.
* Tests: `validation/tests/test_targets.py` (synthetic) and `test_targets_real.py` (the real evidence); report section `targets`, phase `--phase targets`.

**What it answers.** At bar t: which known liquidity targets objectively exist, their identity, where they are, and their factual lifecycle state.

**What it never answers.** Which target price will go to. The model has no Primary DOL, no directional context, no HTF regime, no narrative, no probability, no score, no priority, no renderer and no alerts.

A PASS of CONTEXT-02 means only one thing: the objective targets that exist at t can be described correctly.

---

## 1 · Definitions

**DEF-TU1 · Scope and isolation.**
* After every bar, the universe reads three frozen oracle engines:
  * Module G (`levels`: PDH / PDL / PWH / PWL);
  * Module F (`sessions`: completed session extremes);
  * Phase 2 (`liq`: BSL / SSL / EQH / EQL).
* It never writes them. Every frozen module's events and state are byte-identical with the universe on and off (tested on random walks and on the real data).
* PD arrays (FVG, IFVG, HTF FVG) and LRL are not targets. They belong to a later `PathContext`.

**DEF-TU2 · Identity.** The identity is `TYPE : source key : price in ticks`. It is unique (asserted at registration) and contains no bar index, so it survives a replay or reload of the same observable history.

| type | source key (the frozen module's own identity) | example |
|---|---|---|
| PDH / PDL | the **source trading day** that printed the extreme (D-TU2), in Module G's own `day_key`. The publication day is metadata (`published_in`) | `PDL:D2026-10-30:112929` (Friday's low, published Monday 11-02) |
| PWH / PWL | the **source ISO week**, in Module G's `week_key`; `published_in` is the week it is published in | `PWL:W2026-44:112929` (published in week 45) |
| SESSION_HIGH / SESSION_LOW | `name@window : session id` (the session's start time) | `SESSION_LOW:NY AM@0930-1200:1793629800000:114538` |
| BSL / SSL | Phase 2's Level id (the swing bar time) | `SSL:1793652060000:112405` |
| EQH / EQL | Phase 2's cluster id (the time its second member confirmed). Its `bound` cannot move (DEF-L5.4, asserted) | `EQL:1793653260000:112405` |

`source_id` repeats the frozen identity (`G:PDL:D2026-11-02`, `F:London@0200-0500:<id>`, `L:SSL:<id>`, `L5:EQL:<id>`). The same Phase 2 identity always gives the same target (tested on every real bar).

**Source period (D-TU2), in this order:**
1. The source bar the value provider names: the TradingView D / W bar handed to Module G. Its open time is converted to Module G's trading-day or ISO-week key.
2. Otherwise, the period observed just before an observed roll.
3. Otherwise there is no identity: the value is **BLOCKED** (`SOURCE_PERIOD_UNKNOWN`) and not represented. This is the case for a value seeded on the first loaded bar by a provider that cannot name its source.

The same source period published again is the same target (`republished_in`), so the identity never depends on when the next session happened to expose the level.

**DEF-TU3 · Times (temporal availability, D-TU4).** All times are ms bar times, never bar indices.
* `known_at` says when, inside the confirming bar, the target became objectively known:
  * **OPEN**: the value is final before that bar trades, so that bar may interact with it;
  * **CLOSE**: it is known only at that bar's close, so only later bars may interact.
* Nothing finer is ever inferred.

| field | period level | session extreme | BSL / SSL / EQH / EQL |
|---|---|---|---|
| `confirmed_at` | the bar where Module G set the value (LEVEL_SET; the first loaded bar if it was seeded) | the `SESSION_END` bar (the first bar outside the window) | the confirmation bar / the EQ qualification bar |
| `known_at` | **OPEN**: request.security's previous-period value is final before the period's first bar trades | **OPEN**: the window has ended when the first bar outside it opens | **CLOSE**: a swing / pool is known at its confirmation close |
| `first_observable_at` | that same bar | that same bar | the bar **after** (DEF-L4: k > confirmation) |
| `since` (from here every trade must be seen) | the serving period's nominal start (Module G's boundary: 18:00 ET day, Sunday 18:00 week) | `confirmed_at` | `confirmed_at` |
| `origin_time` | DEF-G3 anchor (or none) | the bar that printed the extreme | the swing bar / the first member's swing |

**DEF-TU4 · EXACT_TOUCH ≠ TARGET_TAKEN.** TARGET_REACHED (`high ≥ price` / `low ≤ price`) is an evaluation concept, in `docs/context/EVALUATION.md` §1.
* **EXACT_TOUCH** (`TARGET_EXACT_TOUCH`, `exact_touches`, `exact_touch_at`). From `first_observable_at`, before any take, a bar whose high (▲) or low (▼) is **exactly** the price. There is no tolerance.
  * BSL / SSL: Phase 2's own `touches` counter, adapted.
  * EQH / EQL: **not tracked** (`exact_touches = None`). Phase 2 counts no cluster touches, and the adapter adds no interpretation of its own (D-TU8).
* **TARGET_TAKEN**, once and terminal:
  * **Adapted (BSL / SSL / EQH / EQL):** Phase 2's own `taken_bar` and SWEEP / BREAK. Nothing is recomputed.
  * **Observed (period and session extremes):** the DEF-L4 rule applied unchanged.
    * The first bar from `first_observable_at` with `high > price` (▲) or `low < price` (▼): strictly beyond, one tick is enough.
    * Its class is set at that bar's close: **BREAK** if the close is strictly beyond the level, else **SWEEP**. A gap through is flagged.
    * A test applies this rule by hand to every Phase 2 level of a walk and gets Phase 2's own take bar, class and touches. It is the same rule.
  * **Class `UNKNOWN`:** the target was beyond, but its *first* take may lie where nothing was observed. This happens in two cases:
    * the history before the take was incomplete;
    * a completed evidence bar shows the price beyond before the loaded history (`taken_before`).

**DEF-TU5 · State (exactly one).**

| state | when |
|---|---|
| `INVALID` | the source no longer tracks it (Phase 2 memory release: `SOURCE_MEMORY_RELEASED`) |
| `UNVERIFIED` | its source class is not validated (`SOURCE_PENDING_GV`, §3: facts are still recorded), or it is not consumed and part of `[since, t]` was not seen (`HISTORY_INCOMPLETE`) |
| `TAKEN` | consumed: an observed take, or `taken_before` |
| `AVAILABLE` | validated origin, confirmed, `first_observable_at` known, every trade since `since` observed, never consumed |

* A level born before the first loaded bar is **never AVAILABLE by assumption**. `history` (OBSERVED / INCOMPLETE) and `verification` (the reasons) are reported beside the state.

**DEF-TU6 · The loaded-history boundary (observation).**
* `history` is OBSERVED when every trade in `[since, t]` was seen. Two kinds of observation count:
  * the chart bars, which cover `[first loaded bar, t]`;
  * completed **evidence bars** of the same feed (the TradingView 15m … 1W bars Pine logged), each known by t.
* Consecutive bars of one timeframe leave nothing out, so weekends and the daily break are no gap. A run of them that never went beyond the price proves its span.
* A bar that went beyond proves nothing after `since`. If no observed bar went beyond, it marks the target consumed with an `UNKNOWN` class.
* The rule is monotone: once observed, always observed.

Minimum evidence needed to restore AVAILABLE, per source:

| source | minimum evidence |
|---|---|
| Phase 2 BSL / SSL / EQH / EQL | none. The engine only holds levels confirmed inside the loaded history; older ones are absent, not UNVERIFIED |
| session extremes | none. A window already in progress at load is never tracked (DEF-F2) |
| period level seeded on the first loaded bar | chart history from the serving period's start, or completed evidence bars covering `[period start, first loaded bar)` without going beyond |
| historical period level (D-2, D-3 … from before the history) | not a Module G source in v1 → **not represented** |

**DEF-TU7 · Source gate.**
* `TargetSettings.validated` defaults to **{STRUCTURAL}**: Phase 2 is frozen, with real Pine parity 0 DIFFERENCE.
* **SESSION waits for T19–T22** (`SOURCE_PENDING_T19_T22`, D-TU3). The real evidence (SESSION parity, and the 12 H / L equal Pine's logs) is SUPPORTING, not proof.
* **DAILY / WEEKLY wait for G-V1…G-V5** (`SOURCE_PENDING_GV`, D-TU1).
* Until the user records those gates, the affected targets are UNVERIFIED and their facts are recorded.
* The procedure is in `docs/context/MANUAL_GATES.md`.

**DEF-TU8 · Composite pools.**
* A pool is two or more unconsumed, non-INVALID targets on one side at **exactly the same tick**.
* Members keep their identities, and the pool has no state of its own.
* `id = POOL:<side>:<ticks>@<earliest confirmed_at>`.
* There is **no tolerance and no cross-source radius**: a PDH one tick from a BSL is two targets. Phase 2's EQ pools keep their own frozen tolerance inside Phase 2.

**DEF-TU9 · Ranges and externality (categorical, no rank).**
* The closed, deterministic ranges valid at t are:
  * PREVIOUS_DAY: the current PDH / PDL;
  * PREVIOUS_WEEK: the current PWH / PWL;
  * `SESSION:<name>`: the latest completed instance of each window.
* Each target gets a relation per range, in ticks: ABOVE · AT_HIGH · INSIDE · AT_LOW · BELOW.
* The model has no W > D > S rank, and no policy reads the relation. `source_class` (DAILY · WEEKLY · SESSION · STRUCTURAL) is provenance, not priority.

**DEF-TU10 · Period roles.**
* When Module G sets a new value for a tag, the previous CURRENT target of that tag becomes `HISTORICAL_PERIOD_LEVEL`. `age_periods` counts the later values, the identity is unchanged, the lifecycle continues, and there is no priority.
* Older D / W extremes from before the loaded history (D-2, D-3, W-2, W-3 at load) are not a Module G source: **BLOCKED for v1**.

**Events** go to the universe's own log; the frozen event bus is untouched. They are `TARGET_CREATED`, `TARGET_HISTORICAL`, `TARGET_TOUCH`, `TARGET_TAKEN` and `TARGET_STATE`. Each fires once per transition, in a canonical order inside each bar.

## 2 · TargetRecord

```
id                  str     TYPE:source key:price_ticks (DEF-TU2)
type                str     PDH PDL PWH PWL SESSION_HIGH SESSION_LOW BSL SSL EQH EQL
source_class        str     DAILY WEEKLY SESSION STRUCTURAL (provenance, not priority)
side                int     +1 above · −1 below
price, price_ticks
source_id           str     the frozen module's identity
origin_time         ms|None the bar that printed the extreme (when the source knows it)
confirmed_at        ms      known at this bar's close (DEF-TU3)
first_observable_at ms|None first bar whose range counts
since               ms      every trade from here must be seen for AVAILABLE
adapted             bool    exact touches and take read from Phase 2
known_at            OPEN | CLOSE   (DEF-TU3, D-TU4)
period_role         CURRENT | HISTORICAL_PERIOD_LEVEL | None;  age_periods int
exact_touches (None: not tracked), exact_touch_at  (TARGET_EXACT_TOUCH)
taken_at, taken_kind (SWEEP|BREAK|UNKNOWN), taken_gap, taken_before   (TARGET_TAKEN)
invalid_at, invalid_reason
history             OBSERVED | INCOMPLETE
verification        () | SOURCE_PENDING_GV | SOURCE_PENDING_T19_T22 | HISTORY_INCOMPLETE
state               AVAILABLE | TAKEN | UNVERIFIED | INVALID
meta                source_period · published_in · republished_in · session / window / start / end · pivot / react / tra · members / ref
snapshot only:      composite (pool id) · externality {range: relation}
```

* Every field is built from bars ≤ t and values known by t. A test appends the future and checks that every earlier snapshot and event is unchanged.

## 3 · G-V1 … G-V5

* These are manual TradingView checks (`docs/TESTS.md` §G-V). They **stay PENDING**: no TradingView test is declared passed without the user's result.
* The table records what each gate proves, and what the captures already show (`test_g_v_evidence_in_the_captures`).

| gate | what it proves | evidence in the repository | missing |
|---|---|---|---|
| **G-V1** NQ1!: the script's PDH / PDL equal the previous 1D candle; D / W source check 100%; day / week start | **origin definition** and **exact price** of the period source on the continuous contract | MNQ1! 11-02 18:00: Module G's own LEVEL_SET (PDH 28891.5, PDL 28101.25) = the D bar that the HTF request received. That D bar = the aggregate of its six 4H bars. All 8 logged D bars open at 18:00 ET and all 6 W bars on Sunday 18:00 ET | NQ1! itself (its only roll in the evidence predates the HTF snapshot); the 1D chart's Data Window; the debug source-check rows |
| **G-V2** the same on a dated contract | origin and price on a dated contract | MNQZ2026 D / W bars also open at 18:00 / Sunday 18:00, and their 10-27…10-29 bars equal MNQ1!'s | no Module G LEVEL_SET on a dated contract (no roll inside those windows) |
| **G-V3** Monday = Friday's candle; LEVEL_SET on Sunday's 18:00 bar; the first Asia on Sunday 20:00 | **period identity** across the weekend | on Monday 11-02 the latest completed D bar is Friday's (opened Thu 18:00) | Sunday's bars are in no capture |
| **G-V4** DST (2026-11-01) | the boundary stays 18:00 ET across DST | the D bar after the change opens Sun 11-01 18:00 EST; Module G's 11-02 18:00 value equals it | the source-check row around the change |
| **G-V5** the chart session setting versus the Daily source | the definition holds under the user's chart settings | none (every capture uses the same setting) | everything |

**Shown by the oracle and the tests** (not by TradingView):
* the first observable time: LEVEL_SET lands on the first bar of the new day (18:00 ET) in every capture;
* no future leakage: the provider hands Module G only bars already known, and ST-03 pins `[1]` + `lookahead_on` in Pine;
* the lifecycle from the first observable time (DEF-TU3 / TU4);
* reload determinism of identity and state (§6).

**Consequence:** DAILY / WEEKLY targets stay UNVERIFIED (D-TU1).

## 4 · The Phase 2 adapter

* 192,772 record states were compared on the 4,979 real bars, plus every bar of three 4,000-bar random walks. There were **0 conflicts**:
  * same identity;
  * AVAILABLE ⇔ ACTIVE;
  * TAKEN ⇔ TAKEN, with the same taken time and class;
  * the same touch count;
  * a release from memory becomes INVALID.
* The universe never recomputes a swing, a significance test or a cluster.

## 5 · Real golden cases

| id | label | case |
|---|---|---|
| TU-G1 | SUPPORTING | PDH = NY PM H = BSL, one exact-tick pool (NQ1! 10-27 19:59). PDH waits for G-V |
| TU-G2 | SUPPORTING | PDL = PWL, one exact-tick pool (MNQ1! 11-02 09:29). Both wait for G-V |
| TU-G3 | DETERMINISTIC | PWL of the week of 10-26 is never proven, because Monday 10-26 is in no capture (HISTORY_INCOMPLETE). Taken later, class UNKNOWN |
| TU-G4 | SUPPORTING | PDL 30591.25 SWEEP at 10-14 08:35; the first take was observed. PDL waits for G-V |
| TU-G5 | SUPPORTING | PDH 29881.25 BREAK at 10-27 21:41 (in Asia), on the same bar as NY PM H. PDH waits for G-V |
| TU-G6 | SUPPORTING | London L 28882 SWEEP at 10-30 05:47. The session source waits for T19–T22 |
| TU-G7 | SUPPORTING | NY AM L 28634.5 SWEEP at 11-02 12:10. The session source waits for T19–T22 |
| TU-G8 | SUPPORTING | PWH 30114 of the week of 10-26, consumed before the history: the logged D bar of 10-27 went above it (`taken_before`) |
| TU-G9 | DETERMINISTIC | an exact touch is never a take on real bars: every touched target is taken later or never, at a bar exactly at the price |
| TU-G10 | DETERMINISTIC | identity = the source period: on MNQ1! 11-02, PDL is `PDL:D2026-10-30` (Friday's low, published in D2026-11-02) and PWL is `PWL:W2026-44` (published in W2026-45); Monday's own low becomes `PDL:D2026-11-02` at the 18:00 roll |

* SUPPORTING = the facts are exact, but an input (the Module G source, or the session source) waits for G-V or T19–T22.
* Totals: 3 DETERMINISTIC (G3, G9, G10) and 7 SUPPORTING (G1, G2, G4–G8). INCONCLUSIVE: none.

## 6 · Measured behaviour (diagnostics, no accuracy)

The report's TARGET UNIVERSE section shows, per real segment:
* targets by source and state;
* TOUCH / SWEEP / BREAK / UNKNOWN counts;
* pools;
* SOURCE_PENDING_GV and history-incomplete counts.

On the loaded-history boundary, the real segments were restarted at bars 97, 311 and 640, with every source validated so that the logic is exercised:
* **36** targets were born before the loaded history;
* **21** were restored by evidence bars;
* **15** were consumed with an unknown class;
* **0** were left AVAILABLE by assumption.

A shorter history never claims more than the full one:
* AVAILABLE ⇒ AVAILABLE;
* a known class ⇒ the same take;
* a target born inside it ⇒ the same facts.

## 7 · The user's decisions (2026-11-03), applied

| id | decision | in the oracle |
|---|---|---|
| D-TU1 | G-V1…G-V5 are **not** waived. The capture evidence is supporting, not proof | DAILY / WEEKLY stay `SOURCE_PENDING_GV`; the procedure is MANUAL_GATES.md |
| D-TU2 | Identity by the **source period**, not the publication period | `PDH:D<source trading day>:<ticks>`, `PWH:W<source ISO week>:<ticks>`; `published_in` is metadata; an unknown source → BLOCKED |
| D-TU3 | Sessions stay implemented; VERIFIED waits for T19–T22 | SESSION is no longer in `validated`: `SOURCE_PENDING_T19_T22` |
| D-TU4 | No blanket "first bar counts": temporal availability | `known_at` OPEN / CLOSE; OPEN only for values final before the bar trades |
| D-TU5 | Pre-history targets: UNVERIFIED / BLOCKED, never AVAILABLE by assumption | approved, unchanged |
| D-TU6 | Composite pools: exact same tick only, no cross-source tolerance | approved, unchanged |
| D-TU7 | SWEEP / BREAK outside Phase 2 only as the DEF-L4 analogue for factual high / low targets; UNKNOWN when history is missing; never redefines Phase 2 | approved, unchanged |
| D-TU8 | EQ exactly as Phase 2; no independent interpretation | EQ exact touches are no longer counted (`None`) |
| D-TU9 | HTF restoration in the oracle only, with the same feed, a fully closed period, a known availability, coverage of the missing interval, and OHLC enough to prove crossed or not | the evidence-bar rule; an evidence bar known before its period closed is rejected (`ValueError`); not in Pine |

The questions as first asked, kept for the record:

| id | question | the provisional choice then |
|---|---|---|
| D-TU1 | PDH / PDL / PWH / PWL source: run G-V1…G-V5, or accept the capture evidence of §3 for some gates? | UNVERIFIED until the gates are recorded |
| D-TU2 | The serving period as the identity of a period level (the day it is published) versus the source D / W bar's open time | serving period (Module G knows it; the source bar time comes from request.security) |
| D-TU3 | Session sources: accept the frozen DEF-F + real parity + the 12 matched H / L, with T19–T22 (manual) still pending? | validated |
| D-TU4 | The first observable bar of a period / session value counts for its lifecycle, because the value is final at its open. Phase 2 starts one bar later | yes |
| D-TU5 | Historical period levels: only Module G values seen superseded inside the history; older D / W extremes BLOCKED | yes |
| D-TU6 | Composite pool: exact tick only, membership by facts (unconsumed), no pool-level state | yes |
| D-TU7 | Non-Phase-2 SWEEP / BREAK: DEF-L4 unchanged; UNKNOWN when the first take is unseen | yes |
| D-TU8 | Touches on EQH / EQL: an observation on `bound` (Phase 2 does not count them) | yes |
| D-TU9 | Restoring the history with completed HTF evidence bars (Pine would need such a source in a later phase) | yes, oracle only |
