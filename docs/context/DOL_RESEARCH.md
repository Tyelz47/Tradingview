# IST · CONTEXT-01 · Draw on liquidity (DOL): research and specification proposal

**Status: RESEARCH + SPECIFICATION PROPOSAL (CONTEXT-01, 2026-11-03), awaiting the user's review. Nothing here is approved, implemented in Pine or frozen.**
* No indicator change: `src/IST.pine` is byte-identical to `IFVG_BASELINE_v0.9.1-dev` (SHA-256 `553248e7…9b91`).
* No frozen module changes: `PHASE1_BASELINE_v0.3.2`, `PHASE2_BASELINE_v0.4.4-dev`, `CISD_BASELINE_v0.7.1-dev`, `DISPLACEMENT_BASELINE_v0.8.0-dev` and `IFVG_BASELINE_v0.9.1-dev`, with their release folders, are untouched. LRL and HTF FVG (experimental) are untouched too.
* Harness: `validation/studies/context.py`. `python -m validation.studies.context` prints every measured table quoted in `docs/context/`.
* Tests: `validation/tests/test_context_study.py`, report section `research.context`. They cover no lookahead, the status rule, the outcome labels and the quoted numbers.
* Companion documents:
  * `TARGET_UNIVERSE.md`: the candidates, their states, internal vs external;
  * `DIRECTIONAL_CONTEXT_RESEARCH.md`: context, the HTF hierarchy, the role of each fact, location;
  * `RESEARCH_CASES.md`: the real cases and the dataset proposal;
  * `CONTEXT_ROADMAP.md`: the phases and the exact CONTEXT-02 proposal.

**Honesty notes.**
* The real data in the repository is 4,979 1m bars, about 83 h, in four segments of NQ1! / MNQ. There is no ES data.
* That gives 13 pre-registered decision points.
* Events cluster heavily: hundreds of events collapse into 1–12 distinct outcomes per fact type.
* So every number here is descriptive. **No DOL rule, threshold or preference was chosen from what price did afterwards**, and no predictive claim is made.

---

## 0 · Where this layer sits

```
DETECTION FACTS        frozen / experimental modules: FVG, sessions, levels, BSL/SSL, EQH/EQL, LRL, HTF FVG, CISD, displacement, IFVG
      ↓  read-only
LIQUIDITY / TARGET UNIVERSE   which liquidity exists, where, since when, in which state          (CONTEXT-01 §2–5, TARGET_UNIVERSE.md)
      ↓
DIRECTIONAL CONTEXT    UP / DOWN / MIXED / UNKNOWN, with its basis                               (DIRECTIONAL_CONTEXT_RESEARCH.md)
      ↓
PRIMARY DOL            PRIMARY_DOL · NEXT_TARGET · ALTERNATE_DOL · path                          (§6–8)
      ↓  — not in this phase —
NARRATIVE → QUALITY / CONFLUENCE → RENDERER
```

Rules for every layer above the detection facts:

* **Read-only.** A context layer never writes a detection record or changes an event. The frozen modules' events and state must be byte-identical with the layer on and off. This is the same isolation rule as DEF-CISD8, DEF-DISP9, DEF-LRL8 and DEF-LRL9.
* **FEATURES_AT_T versus OUTCOME_AFTER_T.**
  * A hypothesis at bar t is built from bars ≤ t and from values known by t's close.
  * Later bars only evaluate it (§10).
  * The harness enforces this by running the oracle on the cut segment. A test replaces every later bar and checks that nothing changes.
* **No score, no voting.** No weights such as "sweep +2, CISD +2", no majority of signals, no fitted thresholds. What is used instead:
  * hard eligibility filters;
  * precedence orders declared before any data is seen;
  * explicit conflict rules that return MIXED or UNKNOWN instead of a forced answer.
* **Reuse the frozen semantics.**
  * "Reached" is DEF-L4's take.
  * SWEEP and BREAK are DEF-L4's classes.
  * TESTED is Phase 2's `touches`.
  * The delivery state is DEF-CISD4.
  * No new name is invented for something a frozen module already defines.

## 1 · Facts are not bias

| fact (frozen event) | what it is | what it is **not** |
|---|---|---|
| `CISD_CONFIRMED` DOWN | The delivery state on the chart timeframe changed to DOWN (DEF-CISD4/5). | Not "DOL below". On 1m a CISD confirms every ~8–11 bars (median), and the 1m state matches the 15m state only 49–63% of the time (RESEARCH_CASES §7). |
| bearish IFVG (`IFVG_INVERTED` −1) | A bullish Phase 1 FVG was closed through and now acts bearish (DEF-IFVG). | Not "bearish". It is a zone: a delivery zone or an obstacle relative to a target. |
| `BSL_SWEEP` | A significant chart-timeframe swing high was traded through by a wick, and the bar closed back (DEF-L4). | Not "short". After a Phase 2 sweep, the next external target reached was on the swept side 82% of the time (driftless reference 64%, 10 distinct outcomes). Internal sweeps were en-route liquidity, not turns, in this data. |
| `DISPLACEMENT_CONFIRMED` | One candle repriced strongly in its direction (DEF-DISP1…6). | Not continuation. 53% toward its side versus a 57% reference. |

The context layer interprets **relations** between facts: their order in time, where they sit relative to the targets, and the timeframe. It never re-reads a single fact as a bias.

## 2 · Formal definition (proposal: DEF-DOL1 … DOL8)

**DEF-DOL1 · Liquidity target.** A liquidity target `x` has:
* a **price level** `x.price`;
* a **side**: ABOVE (+1) or BELOW (−1);
* a source in a frozen or approved IST module;
* a class: W · D · S · EQ · SW (TARGET_UNIVERSE §1);
* a `known` time: when the value became known, never earlier;
* a `since` time: every trade from then on must be observed for the target to be AVAILABLE.

Resting orders are presumed to sit beyond `x.price`: buy stops above a high, sell stops below a low. A target is a **line**, never a zone.

**DEF-DOL2 · Reached = DEF-L4 taken.**
* ABOVE: the first bar after `since` with `high > price` (strictly, a single tick is enough).
* BELOW: the first bar with `low < price`.
* An exact touch is not a take.
* The class is decided at that bar's close: **BREAK** if the close is strictly beyond the level, else **SWEEP**. It is never relabelled.
* The context layer applies exactly this rule to the targets Phase 2 does not track (PDH/PDL/PWH/PWL, session extremes). That is a reuse, not a new semantic.

**DEF-DOL3 · Target status at t** (mapping in §5):
* **AVAILABLE**: known, everything from `since` to t seen, never reached.
* **CONSUMED**: reached. It is SWEPT or BROKEN when the first take was observed, and of unknown class when it happened where nothing was observed.
* **UNVERIFIED**: never reached in what was seen, but part of `[since, t]` was not seen (the loaded-history boundary). UNVERIFIED is **never eligible**.

**DEF-DOL4 · The DOL hypothesis at t.** `H(t)` holds:
* `directional_context`;
* `PRIMARY_DOL`, `NEXT_TARGET`, `ALTERNATE_DOL`, `path`;
* `supporting_facts`, `contradictions`;
* `state` ∈ {CLEAR, MIXED, UNKNOWN, NONE}.

It is computed from FEATURES_AT_T only. **`H(t)` is a structured statement ("the structure confirmed so far points at x"), not a probability and not a trade.** It is judged afterwards by the labels of §10.

**DEF-DOL5 · PD arrays are path, never targets.** FVG, IFVG, HTF FVG and a future HTF IFVG never become PRIMARY_DOL, NEXT_TARGET or ALTERNATE_DOL. Inside `H(t)` a zone is one of three things:
* a **DELIVERY_ZONE**: on the context side and between price and the PRIMARY_DOL;
* an **OBSTACLE**: opposing, between price and the PRIMARY_DOL;
* **CONTEXT**: anything else.

§3 explains why.

**DEF-DOL6 · Never targets:**
* the day open and the midnight open (location references);
* developing extremes of an unfinished session, day or week (they move);
* ATH / ATL (TARGET_UNIVERSE §6);
* any value whose source is undefined (`na`), or that was released by engine memory.

**DEF-DOL7 · Composite pools.**
* Targets on one side within the EQ tolerance (DEF-L5, 4 ticks) form **one pool** that keeps every label, for example `PDH = NY PM H`.
* The pool is a single target, so it is never counted twice.
* Coincidence is mostly *structural*: the day's high is by construction the high of the session that printed it. In the data, PDH 29881.25 = NY PM H 29881.25 (NQ1! 10-27), and PDH 28891.5 = NY AM H 28891.5 (MNQ1! 11-02).
* Treating coincident labels as independent confluence would double-count one pool.

**DEF-DOL8 · No lookahead, no relabelling.**
* Every part of `H(t)` depends on bars ≤ t and values known by t.
* A hypothesis issued at t is never rewritten. A later bar issues a new `H(t′)`.
* Outcomes are attached to `H(t)` and never feed back into it.

## 3 · Liquidity target versus delivery / PD array

| object | geometry | "reached" means | what rests there | role in `H(t)` |
|---|---|---|---|---|
| PDH / PDL, PWH / PWL, older D / W extremes | a level | traded beyond (DEF-L4) | stops beyond a period extreme | **target** (classes D, W) |
| session H / L (completed) | a level | traded beyond | stops beyond the session's extreme | **target** (class S) |
| BSL / SSL (Phase 2) | a level | DEF-L4 (frozen) | stops beyond a significant swing | **target** (class SW, internal by default) |
| EQH / EQL (Phase 2) | a level (the pool's `bound`) | DEF-L5 (frozen) | stops beyond equal highs / lows | **target** (class EQ) |
| LRL (experimental) | a moving diagonal line | DEF-LRL5 terminal classes | stops above descending highs | **path** (low-resistance route), not a target in v1 |
| FVG / IFVG / HTF FVG | a **zone** | touch / CE / full fill / invalidation | nothing is defined to rest *beyond* a zone | **path**: delivery zone, obstacle or context |

Why a zone is not a DOL:
* A zone has no "beyond" where orders are defined to rest, and its lifecycle measures **rebalancing**, not a liquidity take.
* Making zones targets would turn every open FVG into a DOL. There are 100 Phase 1 records and 100 IFVG records in memory on a single 1m capture. That would erase the distinction the user asked for.
* In ICT terms, imbalances are *internal range liquidity* and highs / lows are *external range liquidity*. This proposal keeps that distinction as **target versus path**.
* An explicit "imbalance draw" (price drawn to rebalance one specific HTF FVG) is a possible later type. It is **RESEARCH REQUIRED** and not in v1.

## 4 · Internal versus external (summary; the full treatment is TARGET_UNIVERSE §4)

* Externality is **relative to a reference range**, never a property of a pivot. The C1 "external" of DEF-L2b means only "the extreme of its own 30-bar window" on 1m. That is micro-structure, not range externality.
* v1 ranges are the deterministic, time-based ones:
  * R_W = [PWL, PWH];
  * R_D = [PDL, PDH];
  * each completed session's [L, H] of the current trading day.
* Every target carries an **externality vector** over these ranges: boundary, beyond, or inside. There is no single forced range.
* Its **externality rank** is the largest range it bounds or lies beyond: W > D > S.
* Chart-timeframe Phase 2 levels are **internal** unless they lie beyond R_D.
* A swing-defined dealing range (HTF swings, nested legs) has no deterministic definition in IST yet: **RESEARCH REQUIRED**.

## 5 · Target states, mapped to frozen semantics

| requested state | definition here | frozen source | eligible as a DOL? |
|---|---|---|---|
| AVAILABLE | known, fully observed since `since`, never reached | Phase 2 `ACTIVE`; Module F / G values + DEF-L4 | yes |
| TESTED | AVAILABLE with `touches ≥ 1` (exact-price touches) | Phase 2 `touches` (DEF-L4 "exact touch") | yes. TESTED is an attribute, not a state. Whether a test weakens or strengthens a target is **RESEARCH REQUIRED** |
| SWEPT | reached, close not beyond | DEF-L4 SWEEP | no (consumed) |
| BROKEN | reached, close strictly beyond | DEF-L4 BREAK | no (consumed) |
| CONSUMED | SWEPT ∪ BROKEN ∪ reached-with-unknown-class | Phase 2 `TAKEN` | no |
| INVALID | UNVERIFIED (not fully observed), undefined, or dropped by memory | — | no |

* No new state machine: a target only moves AVAILABLE → CONSUMED, once.
* SWEPT versus BROKEN never changes eligibility. It is evidence for the context (DIRECTIONAL_CONTEXT_RESEARCH §8).

## 6 · PRIMARY_DOL, NEXT_TARGET, ALTERNATE_DOL and path

| field | definition (proposal) | example (bearish context at NY AM) |
|---|---|---|
| `PRIMARY_DOL` | the eligible target on the context side at the **governing class G** (§7), chosen by the precedence of §7 | PDL |
| `path` | ordered list of what lies between price and PRIMARY_DOL: lower-class AVAILABLE targets (en-route / internal liquidity), DELIVERY_ZONEs, OBSTACLEs | London L (S), SSL 1m (SW), bearish IFVG above price (delivery zone), bullish HTF FVG below (obstacle) |
| `NEXT_TARGET` | the next eligible target **beyond** PRIMARY_DOL on the same side: the continuation objective once PRIMARY is consumed | D-2 L, or PWL if nearer |
| `ALTERNATE_DOL` | the target at class G on the **other** side, with the explicit **invalidation** that would make it the draw (for example, a close beyond the protected extreme of the context) | PDH, if the close goes back above the bearish leg's protected high |

* `NEXT_TARGET` is "after PRIMARY", not "en route". The en-route liquidity is the `path`.
* The user's own example follows this reading: primary PDL; next, the external SSL below it; alternate, PDH. If "next" was meant as "the next liquidity hit on the way", that is a decision for the user (D-CX7).

**Why not "nearest = Primary" (measured, RESEARCH_CASES §5).**
* Baseline B1, the nearest AVAILABLE target of any class, picked a target a median of **3 bars** away.
* It was reached first in 9 of 12 resolved decisions. A driftless walk predicts **10.0** of 12 from the distances alone.
* So proximity "works" exactly as much as proximity predicts, and adds nothing.
* Its side also flips with every new 1m swing: 75 AVAILABLE SW levels across 13 decisions, a median 3.0–6.4 TR average away.
* "Reached first" must always be read against the distance-implied reference, or the nearest level wins by construction.

## 7 · Eligibility model (qualitative matrix, no score)

Each criterion gets one role:
* **filter**: hard, applied first;
* **precedence**: an order declared in advance, not a weight;
* **support** or **contradiction**: listed in `H(t)`, never summed;
* **evaluation-only**;
* **research**: not used until studied.

| criterion | defined in IST now? | role | note |
|---|---|---|---|
| status AVAILABLE | yes (DEF-DOL3 = DEF-L4) | filter | UNVERIFIED and CONSUMED are out |
| known by t | yes | filter | no lookahead |
| source validated in TradingView | PDH/PDL/PWH/PWL: **G-V1…G-V5 PENDING** | filter (flag) | the level targets rest on an unvalidated Daily / Weekly source (TARGET_UNIVERSE §8) |
| side = directional context | depends on the context layer | filter for PRIMARY / NEXT; −side for ALTERNATE | context UNKNOWN or MIXED → no PRIMARY (§8) |
| externality class (W > D > S > EQ > SW) | yes (TARGET_UNIVERSE §4) | precedence | the governing class G is a user decision (D-CX7) |
| timeframe / origin | yes: class encodes it | precedence (= class) | — |
| composite pool | yes (DEF-DOL7) | identity (merge), not a bonus | prevents double counting |
| proximity | yes | precedence **within one class only** (the last tie-break) | never across classes |
| age | derivable (`known`) | research | no age rule without evidence |
| tested / untouched | yes (`touches`) | research | ambiguous in ICT practice |
| relation to delivery (aligned zones on the path) | derivable | support | listed, not counted |
| obstacles between price and target | derivable | contradiction | listed, not counted |
| opposing liquidity (AVAILABLE external on the other side) | yes | ALTERNATE / MIXED input (§8) | — |
| location in the range (premium / discount) | partly (R_D, R_W only) | research | price was outside R_D at 6 of 11 decision points with R_D known (DIRECTIONAL_CONTEXT_RESEARCH §10) |

**Candidate selection procedure DOL-P1.** A proposal to evaluate in CONTEXT-04, not a rule.
1. If `directional_context` ∉ {UP, DOWN}, then PRIMARY = NONE. The state is MIXED or UNKNOWN (§8), and both sides' candidates are still listed.
2. Side s = the context direction.
3. Candidates = AVAILABLE targets on side s, pooled by DEF-DOL7.
4. PRIMARY = the nearest candidate of class **G**, the governing class: D for an intraday narrative (D-CX7).
5. If side s has no candidate of class G, take the nearest candidate of the next higher class. If there is none, PRIMARY = NONE with reason "no external liquidity on the context side", which covers price discovery.
6. NEXT_TARGET = the nearest candidate beyond PRIMARY with class ≤ G (G or higher).
7. ALTERNATE = the nearest AVAILABLE target of class G on −s, together with the context's invalidation condition.
8. path = everything AVAILABLE strictly between price and PRIMARY, plus the zones classified by DEF-DOL5.

Each step is a filter or a declared order. Nothing is weighted, and nothing was fitted to data.

## 8 · When the answer is MIXED, UNKNOWN or NONE

| state | condition (proposal) |
|---|---|
| **UNKNOWN** | the context layer has no state on its governing timeframe: warm-up, the loaded-history boundary, or no HTF data. Also: no external target is AVAILABLE on either side (all CONSUMED or UNVERIFIED), or the level source is unvalidated and the user has opted to block on it |
| **MIXED** | the context layer returns conflicting states under an explicit conflict rule: regime and leg disagree outside a recognised retracement phase (DIRECTIONAL_CONTEXT_RESEARCH §3), or external liquidity on **both** sides was consumed in the current leg (an outside move). Also B4's case: external targets AVAILABLE on both sides with no directional state |
| **NONE** | the context is clear but side s has no eligible target (price discovery) |
| **CLEAR** | a context direction, a PRIMARY_DOL, and no contradiction of the rules of §7 |

MIXED and UNKNOWN are answers, not failures. Their outcomes are still recorded (§10, NO_HYPOTHESIS), so abstention can be judged too.

## 9 · Baselines (defined, not tuned)

Every baseline uses the same AVAILABLE universe at t.

Each baseline also uses the same **falsifier** for its evaluation:
1. the nearest AVAILABLE *external* target (W / D / S) on the other side;
2. if there is none, the nearest AVAILABLE target of any class there.

| id | rule |
|---|---|
| B0 | the nearest AVAILABLE external target (W / D / S), either side |
| B1 | the nearest AVAILABLE target of any class (including the 1m Phase 2 levels) |
| B2 | the nearer of PDH / PDL (only those that are AVAILABLE; none → abstain) |
| B3 | the highest available class (W > D > S > EQ > SW), nearest within it |
| B4 | abstain when external targets are AVAILABLE on both sides; otherwise B0 |
| reference | driftless: P(x before o) = d(o) / (d(x) + d(o)). It is the yardstick every hit count is read against, not a policy |

Measured on the 13 decision points (RESEARCH_CASES §5):

| baseline | resolved: reached first · driftless reference |
|---|---|
| B0 | 5 / 10 · 5.0 |
| B1 | 9 / 12 · 10.0 |
| B2 | 2 / 9 · 2.5 |
| B3 | 5 / 11 · 3.8 |
| B4 | abstained 10 / 13; 0 / 3 · 0.5 |

**None differs from its reference beyond what 9–12 decisions can resolve, and no conclusion is drawn.** A future policy is compared with these on the same decisions, paired, on a much larger dataset (RESEARCH_CASES §9).

## 10 · Outcome labels (evaluation only, never features)

Notation: for `H(t)` with PRIMARY x and falsifier o (the ALTERNATE_DOL when defined; for baselines see §9), bars run from t+1 to the **horizon**.

| label | definition |
|---|---|
| `PRIMARY_REACHED` | x is reached (DEF-L4) on bar a ≤ horizon, before o and before the invalidation |
| `OPPOSITE_REACHED_FIRST` | o is reached on bar b < a, or a never happens |
| `BOTH_SAME_BAR_UNRESOLVED` | a = b. The order inside a bar is unknown, and no lower timeframe is consulted |
| `CONTEXT_INVALIDATED` | the context's invalidation condition (a close) happens on bar v, before a and b |
| `UNRESOLVED` | none of these by the horizon, which was fully observed |
| `CENSORED` | the data ends before the horizon with none of these |
| `NO_HYPOTHESIS` | `H(t)` was MIXED, UNKNOWN or NONE. What happened on both sides is recorded anyway |

* **Same-bar precedence.** A wick take happens no later than that bar's close. So on one bar, `PRIMARY_REACHED` beats a close-based `CONTEXT_INVALIDATED`, and two wick takes make `BOTH_SAME_BAR_UNRESOLVED`.
* **Horizon.** The study uses the end of the trading day: 17:00 ET, with the day starting at 18:00 ET (the DEF-G assumption). The session end or N bars are alternatives. The horizon is fixed **before** an evaluation (D-CX8).
* **Metrics** (reported, never optimised):
  * reached first on resolved decisions, against the summed driftless reference;
  * abstention rate, censored share, bars to target;
  * **distinct outcomes**, because overlapping hypotheses share one outcome.
  * This is historical evaluation, not trade P&L.

## 11 · Conceptual schema of the context output (not implemented)

```json
{
  "t": "2026-11-02T09:29-05:00", "symbol": "MNQ1!", "chart_tf": "1", "close": 28721.50,
  "directional_context": {
    "state": "DOWN",
    "regime": {"tf": "<D-CX11>", "state": "DOWN", "basis": "CISD-R on regime-TF candles", "invalidation": "<protected extreme>"},
    "leg":    {"tf": "<D-CX11>", "state": "DOWN", "basis": "CISD-R on leg-TF candles"},
    "phase": "ALIGNED"
  },
  "primary_dol":   {"labels": ["PDL", "PWL"], "cls": "D", "side": -1, "price": 28232.25, "status": "AVAILABLE",
                    "source": [{"module": "G", "bar": "D 2026-10-29 18:00"}, {"module": "G", "bar": "W 2026-10-25 18:00"}]},
  "next_target":   null,
  "next_reason":   "nothing eligible beyond the PRIMARY on the context side (price discovery below)",
  "alternate_dol": {"labels": ["PDH"], "cls": "D", "side": 1, "price": 29180.75, "trigger": "<the context's invalidation>"},
  "path": [
    {"labels": ["SSL"], "cls": "SW", "side": -1, "price": "<nearest AVAILABLE Phase 2 SSL>", "role": "EN_ROUTE"},
    {"kind": "IFVG", "id": "<parent id>:BEAR", "zone": "<bottom, top>", "role": "DELIVERY_ZONE"},
    {"kind": "HTF_FVG", "tf": "60", "id": "<tf:dir:c3 time>", "zone": "<bottom, top>", "role": "OBSTACLE"}
  ],
  "supporting_facts": [{"type": "CISD_CONFIRMED", "dir": -1, "id": "<origin time>", "tf": "1"}],
  "contradictions": [{"type": "LEG_VS_CHART", "detail": "15m CISD state UP at t (decision #11)"}],
  "state": "CLEAR",
  "data_quality": {"unverified_targets": 0, "unvalidated_sources": ["PDH/PDL/PWH/PWL: G-V1…G-V5 pending"],
                   "experimental_inputs": ["HTF FVG"]}
}
```

* Decision point #11 (RESEARCH_CASES §3) supplies the real values: the close, PDH 29180.75, and PDL 28232.25. PDL equals PWL there, because Friday's low was the week's low, so the two form one composite pool. With price 28721.50, no older D / W low is below it.
* Everything in `<…>`, and the directional context itself, is a placeholder: no context engine exists.
* Every reference is a frozen module's own identity: Module G's period bar, FVG id, CISD side + origin time, IFVG id + side. That keeps each fact traceable, and no fact's semantics is copied.

## 12 · The twelve questions (CONTEXT-01 answers)

1. **What counts as a DOL candidate?** An AVAILABLE liquidity *level* from a frozen source:
   * PDH/PDL, PWH/PWL and the 2–3 older D / W extremes;
   * completed session H/L;
   * Phase 2 BSL/SSL and EQH/EQL.

   Coincident ones are pooled (DEF-DOL1, DEF-DOL7; TARGET_UNIVERSE §1).
2. **What does not?** These are path or location, not targets (DEF-DOL5, DEF-DOL6):
   * FVG / IFVG / HTF FVG zones;
   * LRL (path in v1);
   * the day and midnight opens;
   * developing extremes;
   * ATH / ATL;
   * UNVERIFIED or CONSUMED levels.
3. **Internal versus external?** Relative to deterministic time-based ranges (W, D, sessions), as an externality vector with a rank. Swing-range externality is RESEARCH REQUIRED (§4).
4. **Liquidity above and below at once?** It is the normal case: external targets were AVAILABLE on both sides at 10 of 13 decision points (B4's abstentions). Both are kept:
   * the context side gives PRIMARY;
   * the other side gives ALTERNATE, with an explicit invalidation;
   * without a context the answer is MIXED / UNKNOWN, never "the nearer one".
5. **Primary without a score?** Hard filters, then declared precedence (side → governing class → pool → proximity within that class only). Supports and contradictions are listed, never summed (§7).
6. **When MIXED / UNKNOWN?** §8: no state on the governing timeframe, nothing eligible, a regime / leg conflict outside a recognised phase, or external liquidity consumed on both sides of the current leg.
7. **How is HTF delivery represented?** As a per-timeframe vector of frozen CISD-R states (regime TF, leg TF), plus a phase (ALIGNED / RETRACEMENT / TRANSITION). It is not one merged number (DIRECTIONAL_CONTEXT_RESEARCH §3).
8. **1H / 4H / Daily conflicts?** Not by points. Model B separates the regime (the higher timeframe) from the current delivery leg (the lower one): "4H DOWN, 1H UP" is a RETRACEMENT, not MIXED. Model C would make the transitions a state machine. Which timeframe is the regime is a user decision (D-CX11), and it is not chosen from the data.
9. **Role of CISD, displacement, IFVG and LRL?**
   * CISD is the per-timeframe delivery state.
   * Displacement is metadata of the leg or CISD it belongs to.
   * IFVG is a path zone (delivery zone or obstacle).
   * LRL is path quality (a low-resistance route).
   * None of them is a DOL or a bias on its own (DIRECTIONAL_CONTEXT_RESEARCH §4–7).
10. **Which dealing range for location?** v1 = R_D and R_W positions, reported as facts (values outside [0, 1] allowed), plus the completed Asia range. A swing / leg dealing range is RESEARCH REQUIRED. Price was outside R_D at 6 of 11 decision points, so R_D alone cannot define premium / discount.
11. **What is still undefined?**
    * swing dealing ranges and nesting;
    * HTF delivery state, which needs an HTF engine, not built;
    * the regime / leg timeframes;
    * the governing class G;
    * the meaning of TESTED;
    * the age relevance;
    * the imbalance draw;
    * the Pine source of the AVAILABLE status for levels born before the loaded history;
    * the G-V1…G-V5 validation of the level source (CONTEXT_ROADMAP §2).
12. **What data is needed?** Contiguous, complete trading days for NQ and ES separately, in 1m (or 5m), plus HTF bars:
    * ≥ 60 days per instrument for a first descriptive evaluation;
    * ≥ 250 before anything supports a definition decision;
    * stratified after the fact by explicit regime labels (RESEARCH_CASES §9).

## 13 · Decisions for the user (none taken)

| id | decision | proposal |
|---|---|---|
| D-CX1 | Targets are liquidity levels only; PD arrays are path (delivery zone / obstacle / context), never PRIMARY / NEXT / ALTERNATE | yes |
| D-CX2 | Reached = DEF-L4 take; SWEEP / BREAK by DEF-L4 | yes |
| D-CX3 | v1 universe (TARGET_UNIVERSE §1): PDH/PDL, PWH/PWL, D-2/D-3 and W-2/W-3 extremes, completed session H/L, Phase 2 BSL/SSL/EQH/EQL. LRL as path; HTF swings and ATH/ATL out | yes |
| D-CX4 | Externality relative to W / D / session ranges only; swing-range externality RESEARCH REQUIRED | yes |
| D-CX5 | UNVERIFIED (not fully observed) is never eligible | yes |
| D-CX6 | Coincident targets within the EQ tolerance merge into one pool, keeping every label | yes |
| D-CX7 | Governing class G for PRIMARY (D for intraday NQ?), and the reading of NEXT_TARGET (after PRIMARY versus en route) | user |
| D-CX8 | Evaluation horizon (end of the trading day?) | user |
| D-CX9 | Research dataset: source, instruments, size (RESEARCH_CASES §9) | user |
| D-CX10 | DirectionalContext represented as regime + leg + phase (Model B); state machine C evaluated later | yes |
| D-CX11 | Regime / leg timeframes (D or 4H / 1H or 15m?) | user |
| D-CX12 | Whether unvalidated level sources (G-V pending) block a hypothesis or only flag it | user |
