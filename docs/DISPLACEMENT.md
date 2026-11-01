# IST · Displacement (DEF-DISP1 … DISP9)

**Status: PROPOSED (2026-11-01), awaiting the user's approval.**
* This is the recommendation DISPLACEMENT-R of `docs/STUDY_DISPLACEMENT.md` §H. The open decisions are M1…M11 of the study.
* Reference model: `validation/models/displacement.py`, the opt-in module `disp` of the oracle (validation 1.16.0). Default runs, the regression baseline and parity do not include it.
* **Not implemented in Pine.** `src/IST.pine` is unchanged.
* An independent module: CISD-R (frozen, `CISD_BASELINE_v0.7.1-dev`), LRL, HTF FVG, Phase 1 and Phase 2 are untouched.

## 1 · Definitions

Written for the **bullish** displacement. The bearish one is the exact mirror: open and close negated, high ↔ −low. EPS = 0.01 × tick, the float margin of IST.

| id | rule |
|---|---|
| DEF-DISP1 direction | bullish: `close > open + EPS`; bearish: `close < open − EPS`. A doji (`|close − open| ≤ EPS`) is neither |
| DEF-DISP2 yardstick | `A = SMA(TR, 14)` over the bars t−14 … t−1 (Pine: `ta.sma(ta.tr(true), 14)[1]`; the first bar's TR is high − low). No decision while A is undefined (t < 14) or A = 0 |
| DEF-DISP3 body | `close − open ≥ 1.5 × A` (bearish: `open − close ≥ 1.5 × A`); no EPS on this term |
| DEF-DISP4 strong close | `close − low ≥ 0.75 × (high − low)` (bearish: `high − close ≥ 0.75 × (high − low)`) |
| DEF-DISP5 beyond the previous candle | `close > high[t−1] + EPS` (bearish: `close < low[t−1] − EPS`) |
| DEF-DISP6 confirmation | A displacement is a candle where DEF-DISP1…5 all hold. It is decided **at the candle's close**, from bars ≤ t, and never changes. A candle has at most one record. Consecutive candles are separate displacements |
| DEF-DISP7 record | id = the candle's open time; side, bar, OHLC, A, body / A, range / A, close location, the previous extreme. FVG fact: on bar t+1, whether the candle is candle 2 of a raw FVG in its direction (bullish `low[t+1] > high[t−1]`, strict). It is `None` until then and never changes afterwards. Metadata only: no decision reads it |
| DEF-DISP8 memory | 50 records; the oldest leaves first |
| DEF-DISP9 independence | reads candles only: no CISD, FVG, liquidity, LRL, HTF FVG or session state, and no context. No session reset: a gap enters TR and raises A, but the body excludes it |

## 2 · Events

| event | when | dir · id · price · origin |
|---|---|---|
| `DISPLACEMENT_CONFIRMED` | the candle's close | side · candle open time · close · the bar |
| `DISPLACEMENT_DROPPED_MEMORY` | the oldest record leaves memory | side · id · close · its bar |

Displacement has no lifecycle (no ACTIVE / ENDED, no invalidation).

## 3 · Non-repaint guarantees

* Decided at the bar close (Confirmed mode) from that bar and the 14 before it. No later bar can change it.
* The FVG fact is stamped once, one bar later, and is metadata only.
* **Stateless.** A displacement depends only on its own candle, the previous candle and A. Any chart history that contains those 15 bars gives the same result, so a reload cannot change a displacement after the first 14 loaded bars.

## 4 · Validation (oracle, validation 1.16.0)

* `tests/test_displacement.py` (deterministic: thresholds, mirror, edge cases, facts, memory, real data, independence, determinism).
* `fuzz/test_displacement_properties.py` (invariants, mirror, translation, no lookahead, other modules unchanged both ways, long walks).
* `tests/test_displacement_study.py` (the research harness).

**Invariants**, each with a negative test (`tests/test_invariants.py`):

| id | checks |
|---|---|
| INV-DISP-01 | the rule, recomputed from candles |
| INV-DISP-02 | the record fields |
| INV-DISP-03 | the FVG fact: next bar, never missed |
| INV-DISP-04 | frozen records |
| INV-DISP-05 | events = records |
| INV-DISP-06 | memory and order |

## 5 · Not started (by instruction)

* Pine implementation, renderer and alerts.
* Context / quality classes: CISD, sweep, FVG, DOL, structure, multi-candle legs.
* IFVG.
