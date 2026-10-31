# IST · CISD, change in state of delivery (DEF-CISD1 … CISD9)

**Status:**
* **The definition was APPROVED by the user on 2026-10-30.** It is the recommendation CISD-R of `docs/STUDY_CISD.md` §H. The decisions D-C1…D-C12 were approved, with these clarifications:
  * an explicit UNKNOWN initial state (DEF-CISD4);
  * the 200-bar guard is a display / alert guard only, not part of the definition (DEF-CISD9).
* **Oracle approved by the user on 2026-10-30** (validation 1.12.0): `validation/models/cisd.py` is the opt-in module `cisd` of the oracle; default runs and the regression baseline do not include it.
* **Implemented in Pine: IST v0.7.1-dev. FREEZE PREPARED (2026-10-31): `docs/CISD_FREEZE_REPORT.md`.** §5 describes the implementation.
  * The definition was not changed for Pine.
  * The identity of a CISD is **side + origin time** (user, 2026-10-30).
  * CISD-L10 real parity: **0 DIFFERENCE** (v0.7.1-dev capture).
  * CISD-L11 human / golden validation: **PASS**.
  * CISD-L12: automated part **PASS**; the TradingView reload check is the user's (`docs/TESTS_CISD.md`).
  * Tag `CISD_BASELINE_v0.7.1-dev` follows that check.
* Human / reference goldens: `validation/golden/human/` (H1, H2 exact; H3, H4 supporting) and `docs/AUDIT_CISD_HUMAN.md`.
* The frozen baselines `PHASE1_BASELINE_v0.3.2` and `PHASE2_BASELINE_v0.4.4-dev` are untouched. Phase 1, Phase 2, LRL and HTF FVG are untouched.

**CISD detection ≠ CISD quality.**
* This document defines detection only: the structure, from bars alone.
* The study found no edge in CISD alone: on NQ, frequency, retest and follow-through are ≈ a random walk.
* Context lives in later, separate layers: liquidity taken, HTF FVG, session, displacement.

**Notation:**
* Everything is written for the **bullish CISD** (event `dir` **+1**).
* The **bearish CISD** (`dir` −1) is the same rule on the mirrored candle: open, close negated; high ↔ −low.
* ε = 0.01 tick: the project's float margin (Phase 1 / 2, `Settings.eps`).
  * Prices are on the tick grid, so "equal" means within ε and "strictly beyond" means by more than ε.
  * No decision uses raw floating-point equality.
* Bars are counted in bar index. Every decision is taken at a bar's close, from bars ≤ t only (Confirmed mode).

## 1 · Definitions

| id | rule (bullish; bearish = mirrored) |
|---|---|
| **DEF-CISD1** delivery candle, series | A **delivery candle** has close < open − ε (down-close). A **doji** (\|close − open\| ≤ ε) is not one. A **delivery series** is a maximal run of consecutive delivery candles: an up-close candle **or a doji ends it**. |
| **DEF-CISD2** leg window | The bars searched for the bullish side's delivery extreme. While the state is UNKNOWN: from bar 0 (the first loaded bar). Otherwise from the delivery extreme of the leg before it: the bar of the bearish CISD's extreme, its highest delivery high. |
| **DEF-CISD3** level L | The **lowest delivery low** in the leg window, counting delivery candles only (a non-delivery wick never selects). On an **equal low, the later delivery candle wins**. **L = the open of the first candle of the series holding that low** (the origin). L is known at the close of the bar that made that low. |
| **DEF-CISD4** state of delivery | One value: **UNKNOWN**, **UP** (after a bullish CISD) or **DOWN** (after a bearish CISD). The engine starts UNKNOWN; the first loaded bar establishes nothing. While UNKNOWN, both sides are armed; the first confirmed CISD (either side) establishes the state. Afterwards only the side against the state is armed, so CISDs **strictly alternate**. Proof that two CISDs never confirm on one bar is below. |
| **DEF-CISD5** confirmation | The first bar t > origin (and after the previous CISD) whose **close > L + ε**. The confirming candle may be **any colour** (up, down or doji). A wick through L does not confirm, nor does a close exactly at L; one tick beyond does. |
| **DEF-CISD6** record | Identity: **side + origin time** (`id` alone is not the identity). Fields: `id` (origin candle time), `side`, delivery state `before` / `after`, `level` L, `origin`, `ext_bar`, `ext` (the delivery extreme), `leg_ext`, `known`, `bar`, `time`, `close`, `body_k`, `end` (status ACTIVE → ENDED), and the facts `retest`, `reclaim`, `broken`. Definitions of the less obvious fields:<br>• `leg_ext`: the lowest wick from the origin to the confirmation. It is the extreme the CISD protects.<br>• `body_k`: side × (close − open) / TR average of the 14 bars before the confirmation. It is metadata for a future displacement module; no decision reads it.<br>• facts (immutable, from the bar after the confirmation, while ACTIVE): `retest` = the first wick back to L; `reclaim` = the first close back at or through L; `broken` = the first close beyond `leg_ext`. Always retest ≤ reclaim ≤ broken. |
| **DEF-CISD7** lifecycle, memory | A confirmed CISD is **ACTIVE** until the opposite CISD, which **ENDS** it on its own bar. There are no further states and no RETEST / INVALIDATED events. At most one record is ACTIVE (the newest). Records kept: `memory` = 50. When full, the oldest (always ENDED) record goes, with `CISD_DROPPED_MEMORY`. |
| **DEF-CISD8** isolation | Detection reads bars only: no Phase 1 / 2 state, sessions, levels, LRL, HTF FVG, liquidity or context. With CISD on, every other module's events and state are byte-identical. |
| **DEF-CISD9** display / alert guard (**not part of the definition**) | The renderer and alerts ignore a CISD confirmed before bar index 200. It is a conservative chart-start / reload stabilisation guard and may be revised after real TradingView reload tests. During the first 200 bars the CISD calculation, records, events and state run normally; parity and debug can observe them. |

**After a CISD (the flip).** Say a bullish CISD confirms on bar t:
* the state becomes UP;
* the previous (bearish) CISD ends on bar t;
* the bearish side is armed. Its leg window restarts at this CISD's delivery extreme (`ext_bar`) and is scanned up to t;
* the bullish side is disarmed. Its window restarts at the bearish side's new extreme, and then again at every new bearish-side extreme, so its next leg is always measured from the turn.

**Two CISDs never confirm on one bar (DEF-CISD4).**
* After the first CISD only one side is armed, so the claim concerns the UNKNOWN state only.
* While UNKNOWN, let the bullish extreme be on bar e_b and the bearish extreme on bar e_a. They differ, because the candle colours differ; say e_b > e_a.
* The bullish series cannot contain the up-close bar e_a, so its origin is after e_a. On that origin bar the bearish reference was already final.
* The bearish side did not confirm there, so close[origin] ≥ L_bear − ε.
* The origin is a down-close candle, so L_bull = open[origin] > close[origin] + ε ≥ L_bear.
* A bar confirming both would need L_bull + ε < close < L_bear − ε, which is impossible. The case e_a > e_b is the mirror.
* The engine asserts this on every bar, and no generated or real sequence has failed it.

## 2 · Events

| event | dir | id | price | origin | when |
|---|---|---|---|---|---|
| `CISD_CONFIRMED` | +1 / −1 | origin candle time | L | origin bar | the confirmation bar |
| `CISD_DROPPED_MEMORY` | +1 / −1 | the record's id | L | origin bar | the bar a new CISD pushes the oldest record out |

* The events carry the side (`dir`, printed BULL / BEAR) and the origin time (`id`): together, the identity.
* The audit text of `CISD_CONFIRMED` is `prev=UNKNOWN|UP|DOWN · close=… · ext=… · et=<the extreme's bar time, ms> · bk=<body / TR, or na>` (oracle `audit()` = Pine `f_cisdTxt`).
* Retest, close back through L and leg break are **record facts, not events**. They become events only if a later study proves they deserve it.
* Pine has both names since v0.7.0-dev: static check ST-14 is exact again (the temporary oracle-only exception is removed).

## 3 · Non-repaint guarantees

* No lookahead. The level is known at the close of the extreme's bar; the confirmation is a closed bar's close; facts are stamped from the bar after.
  * A run on the first n bars emits exactly the full run's events before n (prefix property, NQ, walks, generated cases).
* Nothing is relabelled. A record's identity, level, extreme and confirmation never change; facts and the end are stamped once (INV-CISD-06).
* Mirror and translation: exact (NQ, walks, scenarios, generated cases).
* History start (reload). The state depends on history but forgets it quickly. Started at any later bar, the truncated run's CISDs equal the full history's from some CISD on. Measured, as the bars until the last differing CISD:

  | data | starts | differing CISDs (max · median) | bars (max · median) |
  |---|---|---|---|
  | NQ 1m | 206, every 7 bars | 8 · 1 | 87 · 5 |
  | NQ 3m | 162 | 4 · 1 | 17 · 4 |
  | NQ 5m | 90 | 10 · 1.5 | 105 · 6 |
  | three walks | 109 each | ≤ 9 | ≤ 60 |

  * **Correction to the study:** its "≤ 4 CISDs, ≤ 62 bars" covered starts in the first 600 bars only (86 starts).
  * All of these fall inside the 200-bar display guard (DEF-CISD9), but the guard is not a guarantee: convergence is a measured property of this data.

## 4 · Validation (oracle `validation/models/cisd.py`, validation 1.12.0)

**Identical to the approved study engine.** Record by record, on:
* NQ 1m, 3m, 5m and 15m: 121 · 55 · 23 · 14 CISDs;
* two walks;
* all 14 study scenarios.

Every study number therefore holds for the oracle.

| user test | where | what |
|---|---|---|
| T1 UNKNOWN initial state | `tests/test_cisd.py::test_t01…` | state UNKNOWN at start, after a huge first bar, and through wick-only, close-at-L and chop scenarios |
| T2 establishing the state | `test_t02…` | the first CISD (bull, its mirror, a bearish one) has prior state UNKNOWN; the state becomes its side |
| T3 strict alternation | `test_t03…` | NQ 1m / 5m and walks: sides alternate, `before` = previous side, each record ends on the next one's bar; trend scenario: one CISD |
| T4 doji ends a series | `test_t04…` | scenario 16: L = 98.25 (after the doji), not 100 ("doji skipped" variant) |
| T5 equal extreme → latest | `test_t05…` | equal lows 96 in two series: L = 97.25 (the later); "first" variant: no CISD |
| T6 non-delivery wick ignored | `test_t06…` | an up-close spike to 95.5 does not select: L = 100, delivery extreme 96, `leg_ext` 95.5; "any candle" variant: a different CISD |
| T7 any colour confirms | `test_t07…` | up-close, down-close (gap) and doji candles confirm on the same bar at the same L; "new direction" variant rejects two of them |
| T8 wick only → none | `test_t08…` | scenario 3 |
| T9 close at L → none | `test_t09…` | scenario 4 |
| T10 one tick → CISD | `test_t10…` | scenario 5 (close 100.25) |
| T11 mirror | `test_t11…`, `fuzz/test_cisd_properties.py` | NQ, walk, every scenario, generated cases |
| T12 prefix / no lookahead | `test_t12…`, property | events and records of every prefix |
| T13 reload convergence | `test_t13…` | NQ 1m / 3m / 5m and walks: converges, the last differing CISD inside the first 200 bars |
| T14 translation | `test_t14…`, property | NQ, walk, scenarios: ±1 tick to 30,000 points |
| T15 valid without displacement | `test_t15…` | scenario 15: CISD with body 0.33 × TR average |
| T16 displacement → same event | `test_t16…` | the same structure with a 4.3× or a 0.2× body: identical event; `body_k` differs; the TR length changes no event |
| T17 other modules byte-identical | `test_t17…`, property | Phase 1, sessions, levels, Phase 2, LRL, HTF FVG: events and state, NQ and walk |
| T18 guard changes no logic | `test_t18…`, property | guard 0 / 200 / 10⁶: identical events and state; renderer and alerts suppress CISDs before bar 200 |

**Invariants** (`validation/invariants.py`): INV-CISD-01…08, each with a negative test (`tests/test_invariants.py`):
* state;
* level and window;
* confirmation;
* timing;
* facts;
* frozen;
* events;
* memory / lifecycle.

They are checked on every bar of every checked run:
* NQ with the whole model (1m / 3m / 5m / 15m);
* memory 1 / 2 / 7;
* generated cases;
* long walks: 20,000 bars × 3 seeds in FULL.

## 5 · Pine implementation (IST v0.7.0-dev, validation 1.13.0)

**No leg-length limit, no backward scan.**
* The oracle re-reads the leg window at a flip. Pine does not: it runs the same definition incrementally.
* This incremental form is `validation/models/cisd.py` `CisdStack`. It is proven record-for-record and event-for-event equal to `CisdEngine` on:
  * NQ 1m / 3m / 5m / 15m;
  * four 20,000-bar walks and a mirrored walk;
  * every scenario, with memory 50 and 2;
  * generated candles (Hypothesis).
* Each side (side coordinates) keeps two stacks:
  * `d`: the suffix minima of the delivery lows in its leg window, each entry carrying its series' origin and L. The first entry is the window's delivery extreme (an equal low pops the older entry: the later candle wins) and its reference.
  * `w`: the suffix minima of every low, for the leg extreme.
* A window restart (the flip, or the state side's restart at the armed side's new extreme) only drops the entries before the new start. No bar is ever re-read, and no history buffer is involved:
  * the engine reads no series beyond `cisdTra[1]`, the body / TR metadata;
  * drawings use bar times.
* **Proof on a leg longer than 500 bars** (`tests/test_cisd_pine.py::test_a_leg_longer_than_500_bars_is_exact`):
  * the bullish CISD's origin is 657 bars back, its delivery extreme 648 and its leg extreme 560;
  * the oracle's flip re-reads 649 bars;
  * the next bearish CISD's origin is 603 bars back;
  * Pine's formulation gives the exact records, with stacks of at most 4 entries;
  * on the last 500 bars only, the same bar would have another level (95.5 instead of 100).
* **Resources.**
  * Per bar and side: amortised O(1) pushes and pops.
  * At a flip: array shifts of the dropped entries.
  * Stack sizes are bounded by the distinct price levels inside a leg, not by its length. Measured peak: 25 entries on NQ 1m, 17 on 20,000-bar walks, 4 on the 657-bar leg.
  * Records: 50 `Cisd` objects.
  * Drawings: at most 2 lines and 2 labels.

**Pine objects.**
* `Cisd`: the record. Identity side + origin time (`f_cisdKey`).
* `CisdSide` ×2 (`cisdUp`, `cisdDn`): armed flag, window start, last flip, the current series, both stacks.
* `CisdBook`: the delivery state (0 UNKNOWN · +1 UP · −1 DOWN), the records and the counters. A Pine function cannot assign a global, so they live in an object.
* Methods `feedCisd`, `pruneCisd`, `readyCisd`, `factsCisd`, `confirmCisd`.
* Per closed bar, after the HTF engine:
  1. the facts of the active CISD;
  2. both sides' stacks;
  3. the state side's restart at the armed side's new extreme;
  4. the confirmation of the armed side (both while UNKNOWN). Two sides at once is impossible (proof §1); Pine stops with `runtime.error` if it ever happens.
* Static check ST-20 pins every rule line, the constants, the per-bar order, the absence of any history read or number in the engine (no truncation), and the guard and display inputs outside detection.
  * Its mutation tests catch the user's 15 listed mutations and more.

**Settings** (group "CISD · CHANGE IN STATE OF DELIVERY"; no mathematical input, CISD-R has none):
* Enable CISD engine **ON** [calc];
* Show CISD **ON** [view];
* Show previous CISD (faded) **OFF** [view];
* CISD alerts **OFF** [alert].

Developer: Inspect CISD (0 = current).

**Renderer** (D-C8):
* the current CISD (the newest record, always the ACTIVE one): one 1 px solid line at L from the origin candle to the confirming candle, plus a tiny `CISD` label at its end;
* colour `#4F473F`, the HTF label tone for the `#C2BAAE` background;
* the previous CISD faded (transparency 60) only with Show previous CISD;
* no boxes, no history;
* rebuilt on the last bar from state; visibility never reaches L3.

**200-bar guard** (DEF-CISD9, a UX / reload guard, **not DEF-CISD**):
* a CISD confirmed before bar index 200 is never drawn and never alerted, also later, so nothing appears suddenly on bar 200;
* it remains in the logical state, the events, the debug table and the capture.

**Alert** (D-C12):
* "CISD alerts", OFF by default;
* one message per `CISD_CONFIRMED`, at the close of the confirming bar, never in the first 200 bars;
* CISD is decided only on closed bars, so there is no intrabar CISD.

**Debug table rows 45–51:**
* engine;
* state (UNKNOWN / UP / DOWN), records / memory, confirmed, dropped, the active CISD, the guard state;
* per side: armed, candidate L with its series, the delivery extreme and its time, window start, stack sizes (and peak);
* inspect: id = side:origin time, before → after, L, extreme, confirmation, close, status;
* the facts, the leg extreme and body / TR;
* what is drawn.

**Parity capture (Pine Logs).**
* `CAPTURE|…|cisd=1|cisdmem=50|cisdtra=14|cisdguard=200|…`.
* After the first captured bar, the whole engine state:
  * `CISDSTATE|state=|confirmed=|dropped=`;
  * `CISDSIDE|side=±1|armed=|a=|since=|known=|run=|rb=|rt=|rl=|d=bar:time:low:origin:origin time:L;…|w=bar:low;…` (side coordinates, bottom first);
  * one `CISDREC|side=|id=|before=|level=|origin=|eb=|et=|ext=|leg=|known=|bar=|time=|close=|bk=|end=|rt=|rc=|br=` per record.
* Per `BAR`: `CS=` state, `CU=` / `CN=` the bullish / bearish candidate L (`off` = not armed, `na` = armed without a reference), `CA=` the active CISD's side:origin time (or `na`).
* Events: `CISD_CONFIRMED BULL|BEAR id=<origin> px=<L> · prev=… · close=… · ext=… · et=… · bk=…` and `CISD_DROPPED_MEMORY … · ended record`.

`python -m validation.parity --capture` compares (`validation/parity/capture.py` `_compare_cisd`):
* **(b) exactly from an established state.** The snapshot is restored into `CisdStack` and replayed on the captured bars. Compared:
  * per bar: state, both candidates, the active CISD;
  * every event: side, id, time, L, previous state, close, extreme, its time, body / TR.
* **(c) against the definition oracle itself.** `CisdEngine` is started UNKNOWN on the first captured bar. After its first CISD that equals one of Pine's (same bar, side, origin, L, extreme), every later CISD must be identical: both engines are then in the same state.
* NOT OBSERVABLE:
  * the first captured bar's events (they are in the snapshot);
  * body / TR of a CISD confirmed in the first 15 captured bars (the replay's TR average warms up);
  * in (c), Pine's CISDs before the definition oracle synchronises (a state started UNKNOWN cannot know Pine's).

**Warm-up and stabilisation.** CISD needs no capture warm-up (the snapshot carries its state). On a chart, detection runs from the first loaded bar (UNKNOWN). The 200-bar guard only hides drawings and alerts; the reload measurements are in §3.

**v0.7.1-dev fix.** The body / TR metadata reads the previous bar's TR average at global scope (`cisdTraPrv = cisdTra[1]`, every bar). In v0.7.0-dev, `cisdTra[1]` inside `confirmCisd` gave the previous same-side confirmation's value (Pine keeps a history per call of a function); only `bk` was affected, never a CISD (real capture 2026-10-30; ST-21).

**Pine-specific compromises.**
* State in objects (a Pine function cannot assign a global).
* A `runtime.error` for the impossible double confirmation.
* Pine's `ta.sma` and Python's sum can differ in the last float digit, so body / TR is compared within 1e-6.
* Nothing in the definition was approximated, bounded or re-anchored.

**Freeze gate:** a real TradingView Pine ↔ oracle capture parity with 0 DIFFERENCE (CISD-L10), then the user's labelled golden cases (CISD-L11).

## 6 · Not started (by instruction)

* Displacement module.
* IFVG.
* DEF-LRL9 context.
* Scoring / confluence.
