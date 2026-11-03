# IST · Context roadmap (CONTEXT-01 → …)

**Status: PROPOSAL (2026-11-03).** Only CONTEXT-01 (this research) is done. Nothing after it has started, and CONTEXT-02 is not implemented.

## 1 · Layers and where each one stands

| layer | status | phase |
|---|---|---|
| detection facts | Phase 1, Phase 2, CISD, displacement and IFVG **frozen**; LRL and HTF FVG **experimental** | — |
| liquidity / target universe | specified as a proposal (TARGET_UNIVERSE.md); measured by the study harness | **CONTEXT-02** (oracle) |
| directional context | candidate models A / B / C (DIRECTIONAL_CONTEXT_RESEARCH.md); no HTF data | CONTEXT-03 (research + oracle) |
| PRIMARY DOL | the DOL-P1 candidate (DOL_RESEARCH §7); baselines B0…B4 defined | CONTEXT-04 (evaluation + oracle) |
| Pine for the approved layers | — | CONTEXT-05 (Pine + parity + freeze) |
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

## 3 · CONTEXT-02, the exact proposal (not started)

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

## 4 · After CONTEXT-02 (sketch, to be re-proposed when its time comes)

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
