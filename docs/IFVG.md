# IST · Inversion fair value gap (DEF-IFVG1 … IFVG9)

**Status: PROPOSED (2026-11-02), awaiting the user's approval.**
* This is the recommendation IFVG-R of `docs/STUDY_IFVG.md` §I. The open decisions are N1…N11 of the study.
* Reference model: `validation/models/ifvg.py`, the opt-in module `ifvg` of the oracle (validation 1.19.0). It needs the Phase 1 module `fvg`. Default runs, the regression baseline and parity do not include it.
* **Not implemented in Pine.** `src/IST.pine` is unchanged (v0.8.0-dev).
* An independent observer: the frozen Phase 1 FVG (DEF-A1…A7), Phase 2, LRL, HTF FVG, CISD-R and DISPLACEMENT-R are untouched.

## 1 · Definitions

Written for a **bearish IFVG from a bullish Phase 1 FVG** (`bottom` = candle 1 high, `top` = candle 3 low, `mid` = CE). The bullish IFVG from a bearish FVG is the exact mirror: `top` ↔ `bottom`, `<` ↔ `>`, `high` ↔ `low`.

| id | rule |
|---|---|
| DEF-IFVG1 eligible parent | a Phase 1 FVG, as the frozen DEF-A1 / A2 detector creates it with the current [calc] FVG inputs, still tracked (open) by the FVG engine when it is invalidated. A raw gap that DEF-A2 rejects is never a parent; a parent the FVG memory drops while open (DEF-A6) can never invert |
| DEF-IFVG2 inversion | the parent's DEF-A5 invalidation, unchanged: the first bar after its confirmation with `close < bottom` (strict; on the tick grid, one tick or more below, ≡ `close < bottom − EPS`). A wick below with a close at or above `bottom` is not an inversion. A gap that opens and closes below is one. The same bar may first stamp the parent's touch, CE and full fill (DEF-A7 order), then invert. Decided at that bar's close, never intrabar; never on candle 3 itself |
| DEF-IFVG3 side | the opposite of the parent's: bearish |
| DEF-IFVG4 geometry | the parent's `top`, `bottom`, `mid`, exactly. No clipping, no new boundary |
| DEF-IFVG5 identity | the parent's id (its candle-3 time) and the IFVG side. A parent inverts at most once, so the key is unique; the inversion bar, time and close are stored |
| DEF-IFVG6 facts | from the bar after the inversion, each stamped once, by wick reach as DEF-A4: **retest** = `high ≥ bottom` (the near edge, the inversion boundary), **CE** = `high ≥ mid`, **full** = `high ≥ top` (the zone traversed). `pre` = the parent's state before the inversion bar (UNTOUCHED / TOUCHED / CE / FULL), metadata |
| DEF-IFVG7 end | **INVALIDATED** on the first later close strictly beyond the far edge: `close > top` (the DEF-A5 mirror). A close back inside the zone is mitigation, not an end. There is no second inversion. Same-bar order: retest → CE → full → invalidation |
| DEF-IFVG8 memory | 50 records per side; on overflow the oldest INVALIDATED record of that side goes, else the oldest ACTIVE one (the DEF-A6 mirror). Several inversions on one bar are recorded in parent creation order |
| DEF-IFVG9 independence | reads the bars and the Phase 1 FVG records only, and never writes them: the parent stays historically INVALIDATED in Phase 1. No CISD, displacement, liquidity, LRL, HTF FVG, session or display input. Context is a later layer |

## 2 · Events

| event | when | dir · id · price · origin |
|---|---|---|
| `IFVG_INVERTED` | the inversion bar's close | IFVG side · parent id · the inverting close · the parent's candle 1 |
| `IFVG_FIRST_TOUCH` | the retest bar | side · id · the near edge · candle 1 |
| `IFVG_INVALIDATED` | the end bar | side · id · the close · candle 1 |
| `IFVG_DROPPED_MEMORY` | a record leaves memory | side · id · CE · candle 1 |

CE and full traversal are record facts, not events (decision N3).

## 3 · Non-repaint guarantees

* Every decision is made at a bar's close from that bar and earlier ones; the parent is frozen Phase 1 state.
* The inversion bar is the parent's DEF-A5 bar, which Phase 1 already logs and parity already verifies.
* Prefix invariance and reload: an IFVG depends on its parent's existence, which is a Phase 1 property (reload behaviour as Phase 1), and on later bars only.

## 4 · Validation (oracle, validation 1.19.0)

* `tests/test_ifvg.py` (deterministic).
* `fuzz/test_ifvg_properties.py` (invariants, mirror, translation, no lookahead, other modules unchanged, long walks).
* `tests/test_ifvg_study.py` (the research harness).
* Invariants INV-IFVG-01…07, each with a negative test.

## 5 · Not started (by instruction)

* Pine.
* HTF IFVG (N8).
* Renderer and alerts.
* Context / quality / confluence.
