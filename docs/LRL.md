# IST · LRL detection (DEF-LRL1 … LRL9)

**Status:**
* **The definition was APPROVED by the user on 2026-10-28.** It is the recommendation LRL-R of `docs/STUDY_LRL.md` §H, with the recommended answers of §K:
  * pivots 3/2;
  * τ = 0.5 × TR average;
  * G = 30 bars;
  * a crossing of the projected boundary ends the LRL. **Correction (user, 2026-10-28, before any Pine):** when the boundary moved into price, the end is a separate terminal class, `LRL_DRIFT`, not SWEEP / BREAK (DEF-LRL5);
  * the pivots of a taken LRL are spent;
  * display (later) shows the nearest active LRL per side, and 2-point candidates only in debug.
* **Reference model and validation only. NOT in Pine.** `src/IST.pine` is unchanged, and the static check ST-08 still forbids LRL identifiers in it.
* The frozen baselines `PHASE1_BASELINE_v0.3.2` and `PHASE2_BASELINE_v0.4.4-dev` are untouched.
* In the oracle, LRL is the **opt-in module `lrl`**. Default runs, the regression baseline and Pine parity do not include it.

**LRL detection ≠ LRL target quality.** This document defines detection only: the diagonal failure-swing structure, from bars alone. Whether an LRL is a good target (low or high resistance) is a separate, future context layer (DEF-LRL9).

**Notation:**
* Everything is written for the **high side**: the **bearish LRL**, descending swing highs with buy stops above, event `dir` **+1**.
* The **low side** (the **bullish LRL**, ascending swing lows, `dir` −1) is the same rule on the mirrored series (high ↔ −low, close ↔ −close).
* (X, P) is a swing bar and its price. TRA(x) = SMA(true range, 14) at bar x. EQ tol = the DEF-L5 EQ tolerance input (4 ticks by default), shared with Phase 2.
* ε = 0.01 tick, the Phase 2 float margin.
* Bars are counted in bar index: the chart's own geometry.

## 1 · Definitions

* **DEF-LRL1 · Pivots.** A dedicated intermediate engine, independent of the liquidity preset. At the close of bar t, X = t − 2 is an LRL swing high iff `high[X] > max(high[X−3 … X−1])` and `high[X] ≥ max(high[X+1 … t])`. This is the DEF-L1 rule with left 3, right 2, and **no** reaction or dominance test: failure swings are, by definition, non-dominant (STUDY_LRL §A).
* **DEF-LRL2 · Tolerance.** τ = max(EQ tol, 0.5 × TRA(X₁)), where X₁ is the first point's swing bar. It is frozen when the 2-point candidate forms. While TRA(X₁) is undefined (warm-up), no candidate forms.
* **DEF-LRL3 · Consecutive points** (Xₐ, Pₐ) → (X_b, P_b). All three must hold:
  * **failure step:** P_b < Pₐ − EQ tol − ε;
  * **spacing:** X_b − Xₐ ≤ 30;
  * **separate swings:** P_b − min(low[Xₐ+1 … X_b−1]) ≥ 1.0 × TRA(Xₐ) − ε.
* **DEF-LRL4 · Line**, the chord through the first and the latest point: s = (Pₙ − P₁)/(Xₙ − X₁), y(x) = P₁ + s · (x − X₁). For a list of points to be valid at bar t:
  * every point lies within τ: |Pᵢ − y(Xᵢ)| ≤ τ + ε;
  * it is diagonal (from 3 points on): P₁ − Pₙ > 2τ + ε;
  * it is clean: high[j] ≤ y(j) + τ + ε for every X₁ < j ≤ t.
* **DEF-LRL5 · Lifecycle**, decided at each bar's close in this order:
  1. **Advance**, with the geometry in effect before bar t, every LRL confirmed before t:
     * **crossed** if `high[t] > boundary_now + ε`, with `boundary_now = y(t) + τ` and `boundary_prev = y(t − 1) + τ`, both on the geometry known before bar t. Then:
       * **`LRL_DRIFT`** if `high[t] ≤ boundary_prev + ε`: the projection moved into price. Equality with the previous boundary is DRIFT;
       * otherwise price moved through it: **`LRL_BREAK`** if `close[t] > boundary_now + ε`, else **`LRL_SWEEP`**.
       * The class is terminal: once, never relabelled. Its points become **spent**, for all three classes.
       * Low side (bullish LRL), in real prices: boundary_now = y(t) − τ and boundary_prev = y(t − 1) − τ. It is crossed if `low[t] < boundary_now − ε`; DRIFT if `low[t] ≥ boundary_prev − ε`; else BREAK if `close[t] < boundary_now − ε`, else SWEEP.
     * else **expired** if t > Xₙ + 30 + 2 (`LRL_EXPIRED`).
     * else a **touch** if `high[t] ≥ y(t) − τ − ε` (a counter, no event).
     * 2-point candidates are dropped silently when crossed (same test), expired (same bound) or holding a spent pivot.
  2. **Judge** X = t − 2. If it is a pivot (X, P):
     * **extend:** the first active LRL, oldest X₁ first, whose points + (X, P) are valid (DEF-LRL3 on the new pair, DEF-LRL4 on the whole list) takes it → `LRL_EXTENDED`. Its chord moves from the next bar on.
     * else **confirm:** the first candidate, ordered by (X₁, X₂), whose points + (X, P) are valid becomes an LRL → `LRL_CONFIRMED`. Candidates sharing a point with it are dropped.
     * else **seed:** every earlier pivot (Xₐ, Pₐ) with X − Xₐ ≤ 30 that is not a point of an active LRL and not spent, with τ defined and [(Xₐ, Pₐ), (X, P)] valid, forms a candidate. The newest 25 per side are kept.
  * A single swing is never an LRL. Two points are only an internal candidate: no event, not drawn. **Three** compatible failure swings confirm.
* **DEF-LRL6 · Identity and memory.**
  * id = the time of X₁. It is unique per side: a point belongs to at most one LRL, and spent pivots never return.
  * 25 candidates per side, and **50 LRL records** per side. Beyond 50, the record that ended first is dropped; if none ended, the oldest active one is dropped and its points become spent. Each drop emits `LRL_DROPPED_MEMORY`.
* **DEF-LRL7 · Display** (renderer, L6; later, with Pine):
  * a polyline through the member pivots (fixed points: segments never move) and a dashed projection from the latest point along y while active, ending at the take or expiry bar;
  * label "LRL";
  * by default the nearest active LRL per side, with ended LRLs behind a history toggle.
  * Visibility never changes state.
* **DEF-LRL8 · Coexistence.** Detection reads bars only. It never reads or writes Phase 1 / Phase 2 state, and every Phase 1 / 2 event and state is identical with LRL on and off. The LRL take is its own event family, separate from BSL/SSL.
* **DEF-LRL9 · Target quality: FUTURE requirement, not implemented.**
  * A separate context layer (L4) may classify an existing LRL as LOW RESISTANCE, NEUTRAL or HIGH RESISTANCE from DOL, FVG support or opposition, displacement / delivery and surrounding liquidity.
  * It is read-only on LRL records, and LRL events must be identical with it on and off.
  * It needs its own study after LRL detection is validated in TradingView.

## 2 · Events

| event | bar | `price` | `meta` |
|---|---|---|---|
| `LRL_CONFIRMED` | X₃ + 2 | P₃ (the 3rd point) | points, τ, slope per bar |
| `LRL_EXTENDED` (repeats) | Xₙ + 2 | Pₙ (the new point) | points, τ, slope per bar |
| `LRL_DRIFT` / `LRL_SWEEP` / `LRL_BREAK` | the crossing bar | boundary_now = y + τ on that bar | points, close, previous boundary |
| `LRL_EXPIRED` | Xₙ + 33 | y + τ on that bar | points, close |
| `LRL_DROPPED_MEMORY` | the confirmation that overflowed memory | Pₙ | ended or active record |

* `dir`: **+1** = the high side (bearish LRL), **−1** = the low side (bullish LRL), as for BSL / SSL.
* `sid`: the time of X₁. `origin_bar`: X₁. Prices are real prices (the low side converted back from the mirrored series).
* All are once per LRL, except `LRL_EXTENDED`. **Exactly one terminal event per LRL:** `LRL_DRIFT`, `LRL_SWEEP`, `LRL_BREAK` or `LRL_EXPIRED` (`events.LRL_TERMINAL`).
* In-bar canonical order: SWEEP, BREAK, DRIFT, EXPIRED, EXTENDED, CONFIRMED, DROPPED, after every Phase 1 / 2 type, whose ranks are unchanged.
* **Names for the future Pine `f_evName`:** exactly these seven: `LRL_CONFIRMED`, `LRL_EXTENDED`, `LRL_SWEEP`, `LRL_BREAK`, `LRL_DRIFT`, `LRL_EXPIRED`, `LRL_DROPPED_MEMORY`. Until Pine emits them they are `events.ORACLE_ONLY`, which ST-14 excludes. Empty that set in the same change that adds them to Pine.

**Record state** (`IstModel.state()["lrl"]`):
* the id, side, points and τ;
* the confirmation bar and the extension bars;
* touches;
* the status: ACTIVE, DRIFT, SWEEP, BREAK or EXPIRED;
* the end bar and end level;
* counters per side: pivots, candidates seeded, confirmed, extended, drift, sweep, break, expired, dropped.

## 3 · Non-repaint guarantees

* Every decision uses bars ≤ t.
* The confirmation bar is the third point's confirmation bar, never earlier.
* Events are append-only and points are append-only.
* A new chord applies from the bar after the extension. Past take decisions are never re-evaluated.
* The drawn polyline joins fixed, confirmed pivots. Like a BSL line drawn from its swing bar, it shows confirmed facts, not a claim that the line existed earlier.
* All of this is tested (§4).

## 4 · Validation (oracle `validation/models/lrl.py`, validation 1.8.0)

| what | where | proves |
|---|---|---|
| INV-LRL-01 … 10, checked after every bar, each with a negative test | `validation/invariants.py`, `tests/test_invariants.py` | the items below |
| | | 01 one LRL per pivot |
| | | 02 points are DEF-LRL1 pivots with valid failure steps |
| | | 03 τ, chord, diagonal |
| | | 04 clean until now / the take / the expiry |
| | | 05 the crossing level and class (DRIFT / SWEEP / BREAK) |
| | | 06 confirmation, extension and expiry bars |
| | | 07 frozen facts |
| | | 08 events ↔ records |
| | | 09 memory |
| | | 10 exactly one terminal class, never relabelled |
| the approved study engine reproduced exactly | `tests/test_lrl.py` | identical events (study spec `APPROVED` = LRL-R + DRIFT) on 17 scenarios, the NQ captures (27 LRLs: 15 high, 12 low) and three random walks. DRIFT only relabels crossings: bars, sides and anchors are identical to the reviewed study |
| terminal classification | `tests/test_lrl.py` | 1–6 bearish / bullish DRIFT, SWEEP, BREAK · 7 equality at the previous boundary (DRIFT), one tick beyond (SWEEP), at the boundary (a touch, then an extension) · 8 steep one-bar projection · 9 extension just before a drift (new geometry from the next bar) · 10 drift spends pivots, expiry does not · 11 never relabelled |
| NQ terminations | `tests/test_lrl.py` | 27 LRLs: **8 DRIFT · 9 SWEEP · 10 BREAK · 0 EXPIRED** (high 5 · 3 · 7 · 0, low 3 · 6 · 3 · 0) |
| event fields | `tests/test_lrl.py` | id, origin, dir, prices of every event type |
| DEF-LRL8 | `tests/test_lrl.py`, `fuzz/test_lrl_properties.py` | Phase 1 / 2 events and state identical with LRL on (NQ, walks, generated cases) |
| opt-in | `tests/test_lrl.py` | default runs and serialised settings unchanged |
| memory path | `tests/test_lrl.py` | drops logged once, ended first, ids never return |
| properties (Hypothesis) | `fuzz/test_lrl_properties.py` | invariants, mirror symmetry, translation invariance, no lookahead. Cases mix random candles with generated staircases, so LRLs form, extend, expire and are taken |
| long walks | `fuzz/test_lrl_properties.py` | LRL module with the approved constants, every invariant: 3,000 bars (quick) · 3 × 20,000 (full) · 6 × 50,000 (deep); memory drops occur from full on |
| study harness | `tests/test_lrl_study.py` | scenario expectations, guard rules, no-context detection |

`python -m validation --phase lrl` runs only the LRL and common tests.

## 5 · Not done yet (in order)

1. **Golden cases:** the user's labelled real examples (STUDY_LRL §K 6).
2. **Pine implementation, after the user approves the next step:**
   * the engine, the renderer (DEF-LRL7) and the debug rows;
   * alerts, default OFF;
   * ST-08 adjusted to allow LRL identifiers.
3. **Parity capture extension:** `LRL_*` event lines plus a per-bar value (y + τ of the nearest active LRL per side), so that bounded Pine-Log parity covers LRL as L48 does for Phase 2.
4. **TradingView L-tests:**
   * compile and runtime;
   * the confirmation bar and no early drawing;
   * reload invariance;
   * extension / sweep / break / expiry on the chart;
   * the object budget with Phase 1 + 2 on;
   * 1m / 3m / 5m.
5. **DEF-LRL9 context layer:** a separate study.
