# IST · Context roadmap (CONTEXT-01 → …)

**Status (2026-11-04).**
* CONTEXT-01 is approved as a research milestone (`6576bae`).
* CONTEXT-02 is approved as the deterministic TARGET UNIVERSE milestone (`e1ee951`); D-TU1…D-TU9 are applied.
* CONTEXT-03 is done as research: `EVALUATION.md`, `DATASET_CONTRACT.md`, `MANUAL_GATES.md`; awaiting review.
* CONTEXT-04 is proposed in §6, not started.
* Nothing here freezes a policy, hierarchy, model or claim.

## 1 · Layers and where each one stands

| layer | status | phase |
|---|---|---|
| detection facts | Phase 1, Phase 2, CISD, displacement and IFVG **frozen**; LRL and HTF FVG **experimental** | — |
| liquidity / target universe | **oracle implemented** (TARGET_UNIVERSE_ORACLE.md, DEF-TU1…TU10); research, not frozen | CONTEXT-02 ✓ |
| evaluation harness and dataset | **implemented**: outcome oracle (EXACT_TOUCH ≠ REACHED ≠ TAKEN), policy interface, baselines B0…B4, metrics, REF-A, dataset contract, DEV / OOS locks (EVALUATION.md) | CONTEXT-03 ✓ |
| directional context | candidate models A / B / C (DIRECTIONAL_CONTEXT_RESEARCH.md); no HTF data | **CONTEXT-04** (proposed, §6) |
| PRIMARY DOL | the DOL-P1 candidate (DOL_RESEARCH §7), a hypothesis only | CONTEXT-05 (evaluation + oracle) |
| Pine for the approved layers | — | after the oracle layers (Pine + parity + freeze) |
| narrative, quality / confluence, renderer, alerts | not started (by instruction) | later |

Every phase follows the project's discipline:
* study → the user's approval → oracle → tests → (Pine → real parity with 0 DIFFERENCE → human goldens → reload) → freeze;
* frozen baselines never change;
* definitions are never tuned to pass a test.

## 2 · Prerequisites and dependencies

| item | why it matters | status |
|---|---|---|
| **G-V1…G-V5** (the PDH/PDL/PWH/PWL source, `docs/TESTS.md` §G-V) | the most important targets come from it | **PENDING (manual, the user's).** The HTF snapshots in the evidence are consistent with 18:00 ET days and Sunday 18:00 weeks. That is not a pass |
| a research dataset (RESEARCH_CASES §9) | 83 h give 13 decision points and ≤ 12 distinct outcomes per fact | the user's decision D-CX9 |
| LRL and HTF FVG frozen | a context that *depends* on an experimental module cannot be frozen | proposal: context v1 reads them only as path / support, flagged experimental, never as filters |
| a multi-timeframe delivery state | Models B / C need CISD-R states on HTF candles | not in IST; CONTEXT-03 |
| the user's decisions D-CX1…D-CX12 | DOL_RESEARCH §13 | open |

## 3 · CONTEXT-02, the proposal as written in CONTEXT-01

Now implemented as `TARGET_UNIVERSE_ORACLE.md`. It differs from this text in five places:
* TARGET_TAKEN carries the class; there are no separate TARGET_SWEEP / TARGET_BREAK events.
* The universe's own event log covers every target; the frozen event bus is untouched.
* TOUCH is separate from TAKEN.
* Pools are exact-tick.
* D-2 / D-3 come only from superseded Module G values.

**Title.** CONTEXT-02 · Target universe: an oracle-only, read-only specification and model. It makes **no DOL choice and no directional context**.

**Goal.** Turn TARGET_UNIVERSE.md into an approved definition, **TU-R**. Then implement it as an opt-in oracle module, so every later phase reads one tested universe instead of re-deriving it.

**Inputs to approve first (the user):**
* D-CX1…D-CX6 and D-CX12 (DOL_RESEARCH §13);
* the event names below;
* the G-V results.

**Definitions (DEF-TU1…TU8, to be written from TARGET_UNIVERSE.md):**
1. TU1, targets: classes W / D / S / EQ / SW, kinds, side, price, `known`, `since`, source identity.
2. TU2, sources: Module G values (PDH … PWL), and their 2–3 older D / W extremes, from a provider. That provider is Pine's request.security in a later phase, and the captures' HTF bars in the oracle. Module F completed sessions; Phase 2 levels and EQ pools, read-only.
3. TU3, reach: exactly DEF-L4, applied to the period and session extremes.
4. TU4, status: AVAILABLE / CONSUMED (SWEEP · BREAK · unknown) / UNVERIFIED, with the observation-coverage rule.
5. TU5, composite pools: same side, within the EQ tolerance, every label kept.
6. TU6, externality: a vector over R_W, R_D, R_S; rank W > D > S; Phase 2 classes internal by default.
7. TU7, events (proposal, names to approve): `TARGET_TAKEN` and `TARGET_SWEEP` / `TARGET_BREAK` for the non-Phase-2 targets, once each. **Phase 2 events stay exactly as they are; nothing is duplicated.**
8. TU8, isolation: every frozen module's events and state are byte-identical with the module on and off.

**Deliverables:**

| file | content |
|---|---|
| `docs/context/TARGET_UNIVERSE.md` | updated to the approved TU-R text |
| `validation/models/targets.py` | the opt-in oracle module `tu`, reading `levels`, `sessions`, `liq` and an HTF-bar provider |
| `validation/tests/test_targets.py` | the tests below |
| `validation/golden/human/targets/` | real golden cases taken from the evidence (§3 examples below) |
| `validation/studies/context.py` | switched to read the module instead of its own helpers (numbers unchanged, or every difference explained) |

**Tests (the minimum):**
* no lookahead: the prefix run equals the full run up to t; changing future bars changes nothing;
* isolation (TU8);
* mirror symmetry;
* reload: a later start never turns UNVERIFIED into AVAILABLE by assumption, and the status converges once `since` is observed;
* SW / EQ equal Phase 2's own state at every bar;
* every reach is the DEF-L4 rule (exact touch ≠ take; class by close);
* composite pools are one record.

**Real golden cases to pin (from the evidence):**
* PDH = NY PM H (NQ1! 10-27);
* PDL = PWL (MNQ1! 11-02);
* PWL UNVERIFIED on MNQZ2026 10-29 / 30, because the Monday session is unseen;
* PDL 30591.25 SWEEP on MNQZ2026 10-14 08:35;
* PDH 29881.25 BREAK during the 10-27 → 10-28 Asia session.

**Gates to close CONTEXT-02:**
* the user's approval of TU-R;
* G-V1…G-V5 recorded, or an explicit decision under D-CX12;
* the new tests PASS and FULL PASS;
* hash checks show no frozen file changed: `src/IST.pine`, every release folder's SHA256SUMS, the v0.9.1-dev MANIFEST.

**Out of scope:**
* DirectionalContext and PRIMARY / NEXT / ALTERNATE selection;
* any Pine, renderer, alert, styling, score or entry model;
* a multi-timeframe engine; SMT; OB / breaker / OTE; any frozen-module change.

## 4 · CONTEXT-03, the exact proposal (not started)

**Title.** CONTEXT-03 · Evaluation harness and research dataset. It contains **no DOL policy, no directional context and no Pine**.

**Why this comes before directional context.** Every later question needs three things that do not exist yet:
* fixed outcome labels computed from TOUCH / TAKEN facts;
* the baselines expressed on the target universe;
* enough data.

Today there are 83 h, 13 decision points and ≤ 12 distinct outcomes per fact. Models A / B / C need HTF history that no capture holds.

**Prerequisites (the user):**
* G-V1…G-V5 recorded, or decision D-TU1;
* the dataset source and size (D-CX9);
* the evaluation horizon (D-CX8);
* the reading of NEXT_TARGET (D-CX7, wording only).

**Deliverables:**

| file | content |
|---|---|
| `validation/models/outcomes.py` | an evaluation-only labeller. Given a hypothesis (target id, falsifier id, horizon) issued at t, it reads the target universe's TOUCH / TAKEN facts after t and returns PRIMARY_REACHED · OPPOSITE_REACHED_FIRST · BOTH_SAME_BAR_UNRESOLVED · UNRESOLVED · CENSORED, plus TOUCHED_NOT_TAKEN as a separate fact. It never feeds back into the target universe |
| `validation/studies/context.py` | the CONTEXT-01 baselines B0…B4 recomputed on the target universe, as definitions, not tuned. B3's ordering lives only inside B3, never in the universe. CONTEXT-01's numbers are kept as the record |
| `validation/data/…` (or `validation/parity/evidence/…`) | the research dataset: complete NQ and ES trading days, plus the HTF bars, each file checked against an overlapping TradingView capture (0 differences) |
| `docs/context/EVALUATION.md` | the pre-registration: decision points, horizon, labels and metrics (reached first against the driftless reference, abstention, censoring, distinct outcomes) |

**Tests (the minimum):**
* labels on hand-made paths, including a touch that is not a take and a same-bar take on both sides;
* no lookahead: a label at t is unchanged when bars before t change, and only bars after t matter;
* mirror symmetry;
* the baselines read only the AVAILABLE universe at t.

**Gates:**
* the user approves the pre-registration;
* FULL PASS;
* frozen hashes intact;
* `src/IST.pine` byte-identical.

**Out of scope:** Primary DOL, directional context (Models A / B / C), narrative, scores, renderer, alerts, Pine, any frozen-module change.

**What follows.** Directional-context research (Models A / B / C on the HTF data) becomes CONTEXT-04, and the Primary DOL policy CONTEXT-05. Both are re-proposed when their time comes.

## 5 · After CONTEXT-02 (CONTEXT-01's sketch; superseded by §4)

* **CONTEXT-03 · Directional context.**
  * Collect HTF data (15m … 1D) per D-CX9.
  * Run CISD-R on HTF candles inside the oracle only; that is a study, not a new engine in Pine.
  * Evaluate Models A / B / C on the pre-registered decision points, with the labels of DOL_RESEARCH §10.
  * Fix D-CX10 / D-CX11.
* **CONTEXT-04 · PRIMARY DOL.**
  * Evaluate DOL-P1 against B0…B4, paired, on the same decisions.
  * Report the results against the driftless reference, with distinct-outcome counts.
* **CONTEXT-05 · Pine.** Implement only the approved, oracle-validated layers, with the capture fields needed for real parity (0 DIFFERENCE), human goldens and a reload check, then freeze.
* **Later:** narrative (DIRECTIONAL_CONTEXT_RESEARCH §11), quality (§12), renderer priorities.

## 6 · CONTEXT-04, the exact proposal (not started)

**Title.** CONTEXT-04 · HTF delivery state and directional-context research (oracle only).
* There is **no Primary-DOL policy, no Pine and no renderer**.
* Models A / B / C stay research candidates. None is approved by this phase.

**Prerequisites (the user):**
* G-V1…G-V5 and T19–T22 recorded (MANUAL_GATES.md), or knowingly run PROVISIONAL;
* D-DS1…D-DS4: the dataset source, NQ / MNQ pooling, `dev_until`, holidays;
* D-CX11: the regime and leg timeframes, fixed before any run.

**Data.**
* HTF bars captured on their own TradingView charts (15m, 1H, 4H, 1D) for the chosen period, with the existing CAPTURE mechanism. HTF data is cheap: 1,000 4H bars ≈ 33 weeks.
* 1m days under DATASET_CONTRACT.md.

**Deliverables:**

| file | content |
|---|---|
| `validation/models/htf_state.py` | per timeframe, the delivery state from **the frozen CISD-R definition run on completed HTF candles**: UNKNOWN / UP / DOWN, the last CISD (side + origin time), the protected extreme (`leg_ext`). A read-only oracle with no new CISD semantics; each HTF candle is used only once closed and known (the D-TU9 conditions) |
| `docs/context/DIRECTIONAL_CONTEXT.md` | DEF-DC: the state vector, Models A / B / C written as deterministic rules, and **the invalidation semantics** that make `CONTEXT_INVALIDATED` (DEF-EV2) operational for a hypothesis carrying a context |
| `validation/studies/context_eval.py` | hypotheses may carry `invalidation` (a level + a close rule, fixed at t); the evaluator gains `CONTEXT_INVALIDATED` (a close beyond the invalidation before the primary is reached; a same-bar wick reach beats a close-based invalidation) |
| tests | HTF state = CISD-R on the HTF candles (the frozen oracle as reference); no lookahead (an HTF candle is used only after its close is known); mirror; Models A / B / C deterministic; CONTEXT_INVALIDATED semantics; DEV / OOS lock enforced |

**Evaluation (pre-registered, DEVELOPMENT only).**
* Models A / B / C each give a side (or MIXED / UNKNOWN = abstain) per decision point.
* They are paired with the B0 target rule on the context side, and compared with B0…B4 and REF-A by the CONTEXT-03 metrics, NQ and ES apart.
* No OOS run happens before the user locks a candidate.

**Gates:**
* the user approves DEF-DC and the pre-registration;
* FULL PASS;
* frozen hashes intact;
* `src/IST.pine` byte-identical.

**Out of scope:** a Primary-DOL policy, a narrative engine, scores, renderer, alerts, Pine, any frozen-module change.
