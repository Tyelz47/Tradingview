# IFVG research study · inversion fair value gap

**Status: RESEARCH + ORACLE, awaiting the user's approval (2026-11-02).** The recommendation is **IFVG-R** (§I). Its specification is `docs/IFVG.md` and its reference model is `validation/models/ifvg.py` (validation 1.19.0). **There is no Pine code.**
* Nothing frozen changes:
  * `PHASE1_BASELINE_v0.3.2`, `PHASE2_BASELINE_v0.4.4-dev`, `CISD_BASELINE_v0.7.1-dev` and `DISPLACEMENT_BASELINE_v0.8.0-dev` are untouched;
  * `src/IST.pine` is unchanged;
  * LRL and HTF FVG semantics are unchanged.
* Harness: `validation/studies/ifvg.py` (`python -m validation.studies.ifvg` prints every table below).
* Tests: `validation/tests/test_ifvg_study.py` (report section `research.ifvg`); the oracle's tests are listed in §M.

**Data and honesty notes**
* The same three real 1m segments as the displacement study: 3,791 bars ≈ 63.2 h of NQ1! (2026-10-27 / 28) and MNQ (2026-10-29 / 30 and 2026-10-13 / 14). Never joined.
* The universe is the **frozen Phase 1 FVGs** with default inputs, 652 of them. Each is followed for its whole life (memory unbounded in the study, so no lifecycle is cut).
* **Everything is descriptive.** No trigger was chosen from what price did afterwards, and no predictive claim is made.
* The references (H1, the video) have no price axis. They support the trigger; they are not deterministic goldens (§B).

---

## A · Audit of `docs/IFVG_REQUIREMENTS.md`

| item in the note | verdict |
|---|---|
| CISD ≠ IFVG; neither requires the other; confluence is a later layer | **confirmed** by the data (§F) |
| confirmed bar, non-repainting; an outcome never changes detection | **kept** |
| H1 / video: a close beyond the far edge; the box keeps the parent geometry, recoloured; known by the close | **confirmed**. Re-checked on H1's digitised candles (§B). "Far edge" in the note = "opposite boundary" in the task |
| "the same event as our FVG invalidation, DEF-A5" | **confirmed and decisive**. Phase 1's DEF-A5 is exactly a strict close beyond the far edge, from confirmation + 1, at the bar close (oracle `models/fvg.py`, Pine `advance(Fvg)`): IF2 = the frozen invalidation, bar for bar (tested) |
| record model: linked, parent immutable | **adopted**, with one correction. The note says "copy at creation". The oracle copies the parent on its **confirmation** bar, because the FVG engine can release a just-invalidated record on the bar it is invalidated (tested, §L) |
| the Phase 1 chart-TF record lacks the invalidating close (only in the event) | **true, harmless**. The IFVG record stores it; Phase 1 is not changed |
| "the HTF FVG stores `invClose`" | true; relevant only for a future HTF IFVG (§N) |
| memory releases closed records first, so an IFVG must copy rather than reference | **confirmed**. On real data, 0 open Phase 1 FVGs were dropped before inverting with the default memory |
| open questions 1–12 | answered in §C–§O, except the renderer (later) |

Nothing in the note was wrong. Its one imprecision was where to copy the parent; the correction is above.

## B · Conceptual and reference findings

* **The hypothesis holds on every observable point.**
  * An IFVG starts from an existing FVG and keeps its box.
  * It is created when a candle closes beyond the far edge (the opposite boundary), known at that close.
  * The box then acts from the other side; the product recolours it rather than drawing new geometry.
  * IFVG and CISD co-occur (same bar in the video, 4 bars apart in H1), but neither needs the other.
* **H1, checked on its digitised candles** (`golden/human/GOLD_CISD_H1.json`, pixel units, supporting only):
  * Phase 1 FVG + IF2 finds the bearish FVG of the drop's bar 21 [708, 733], inverted by the close of bar 22 (736 > 733).
  * That is 4 bars before the CISD of bar 26, as in the image.
  * Two earlier bearish FVGs (bars 19, 20) invert on bar 23. The product shows one box; its display filter is unknown.
* **Not observable in the references:** the IFVG's own failure, CE behaviour, and bearish examples.
* No ICT text defines a numeric rule. As with displacement, the frozen IST geometry is the anchor.

## C · Candidate definitions IF1 … IF5

For a parent FVG of side d (bullish d = +1), the IFVG side is s = −d.
* The **far edge** is the boundary to close through: a bullish parent's bottom (candle 1 high), a bearish parent's top (candle 1 low).
* Every trigger is checked from the bar after the parent's confirmation (DEF-A3), at the bar close.

| id | exact trigger (bullish parent; bearish = mirror) | confirmation | repaint | false positives | false negatives | Phase 1 compatibility |
|---|---|---|---|---|---|---|
| IF1 wick-through | first `low < bottom` | that bar's close | none | **a wick that is rejected** (the close stays inside) inverts; contradicts the references (by the close) | — | a second event, not in Phase 1 |
| **IF2 close-through** | first `close < bottom` (strict) | that bar's close | none | an exhausted spike that closes just beyond, then reverses (the IFVG then ends quickly, §D) | — | **identical to DEF-A5**: the same bar as `FVG_INVALIDATED`, always |
| IF3 + displacement | the first close-through on a bar that is a side-s DISPLACEMENT-R candle; a later close-through counts | that bar's close | none | — | **82 % of IF2 inversions**; and 76 % of IF3 triggers come after the Phase 1 invalidation, often tens of bars later, on an unrelated candle | breaks the one-event link to DEF-A5 |
| IF4 after a full fill | the first close-through on a bar after the bar that first fully filled the zone | that bar's close | none | — | every one-candle inversion (22 %), which then waits for a second, later close-through (46 % come after the Phase 1 invalidation) | breaks the link |
| IF5 + context | the first close-through with a side-s CISD in the 10 bars up to it | that bar's close | none | — | 45 % of real inversions lack the context; couples IFVG to CISD (forbidden as a base rule) | breaks the link |

## D · Real NQ / MNQ statistics

**Universe.** 788 raw three-candle gaps (DEF-A1 geometry); **652 Phase 1 FVGs** (DEF-A2 qualified, 83 %). With the default memory (50 per direction), no open FVG was dropped before it could invert.

| candidate | inverted (rate) | from ▲ · ▼ parents | bars to inversion (median) | same bar as first touch · after first touch · after CE · after a full fill | after the Phase 1 invalidation | candle is DISPLACEMENT-R | same-side CISD ±5 | Asia · London · NY AM · NY PM · other |
|---|---|---|---|---|---|---|---|---|
| IF1 | 596 (91 %) | 284 · 312 | 5 | 46 % · 16 % · 33 % · 5 % | 0 % | 13 % | 51 % | 72 · 103 · 60 · 47 · 314 |
| **IF2** | **566 (87 %)** | 272 · 294 | **9** | **22 % · 9 % · 16 % · 54 %** | 0 % (identical) | **18 %** | **56 %** | 70 · 100 · 56 · 45 · 295 |
| IF3 | 437 (67 %) | 239 · 198 | 45 | 9 % · 4 % · 3 % · 84 % | 76 % | 100 % | 61 % | 43 · 79 · 52 · 26 · 237 |
| IF4 | 558 (86 %) | 267 · 291 | 11 | 0 · 0 · 0 · 100 % | 46 % | 9 % | 58 % | 68 · 99 · 57 · 41 · 293 |
| IF5 | 545 (84 %) | 270 · 275 | 16 | 11 % · 6 % · 9 % · 74 % | 43 % | 25 % | 84 % | 62 · 87 · 59 · 45 · 292 |

* Session counts are inversion bars. "other" is the hours outside the four session windows.
* On 1m, most FVGs are eventually closed through: **87 %**, about 9 per hour. Most are closed through after a full fill on an earlier bar (54 %); 22 % are closed through by the very candle that first touches them (one candle or a gap).

**After an IF2 inversion (descriptive, 566).** The IFVG's near edge is the inversion boundary (the parent's far edge); its far edge is the parent's near edge. Median 625 bars observed after each inversion.

| fact | within 10 bars | within 30 | within 60 | by the data's end | median bars |
|---|---|---|---|---|---|
| retest: the near edge reached | 82 % | 88 % | 92 % | 95 % | 1 |
| CE reached | 73 % | 84 % | 89 % | 93 % | 2 |
| zone traversed: the far edge reached | 66 % | 78 % | 85 % | 91 % | 3 |
| T1: a close back beyond the near edge | 66 % | 80 % | 86 % | 91 % | 4 |
| **T2: a close strictly beyond the far edge** | 52 % | 70 % | 79 % | 86 % | 7 |

On 1m, an IFVG is usually retested immediately, and about half end (T2) within 10 bars. No statistic here was used to choose a rule.

## E · Relationship with the original FVG lifecycle

* **Inversion = the parent's DEF-A5 invalidation.** Before it, the parent may be UNTOUCHED (the same candle touches and inverts, 22 %), TOUCHED (9 %), CE (16 %) or FULL (54 %). The IFVG records this as metadata (`pre`).
* **An INVALIDATED parent is exactly what becomes an IFVG.**
  * Phase 1 stays as frozen: the parent is historically INVALIDATED (closed), its milestones and events unchanged, and it is released from memory by DEF-A6 like any closed record.
  * The IFVG engine observes that invalidation and creates its own record from the same frozen geometry. Proven: the Phase 1 events and state are identical with the IFVG on or off.
* **Same bar.** DEF-A7 orders a bar's parent milestones touch → CE → full → invalidation, and the IFVG is created after them. A gap through the edge stamps all four and inverts on one bar. Inversion is possible on the first bar after the parent's confirmation, never on candle 3 itself.
* **Size filter (option A).** Only Phase 1-qualified FVGs. Raw gaps rejected by DEF-A2 (136 of 788 here) never become IFVGs, so there is no second universe of FVGs. The IFVG therefore follows the user's [calc] FVG inputs.
* **Geometry.**
  * The parent's top, bottom and CE, exactly (option A). Clipping to the unfilled part (B) is degenerate: a close beyond the far edge means the whole zone was traded through on or before that bar, so nothing is unfilled.
  * New geometry from the inversion candle (C) has no evidence; the references keep the parent's box. CE alone (D) is a level, not a zone.

## F · Relationship with CISD (frozen CISD-R)

* Of 490 inversions counted per side and bar, 263 have a same-side CISD within ±5 bars and 227 do not.
* **41 % of CISDs** (123 of 300) have no same-side inversion within ±5 bars.
* **Two distinct modules**, often co-located; CISD is not required. Real examples (New York):
  * **IFVG + CISD:** NQ1! 2026-10-27 04:02 bullish IFVG [29326.25, 29327.00]; 04:41 bearish [29355.50, 29366.75].
  * **IFVG without CISD:** 04:57 bullish [29393.25, 29408.75]; 06:14 bearish [29400.25, 29410.75].
  * **CISD without IFVG:** 05:49, 06:28 and 07:42 bearish CISDs.

## G · Relationship with DISPLACEMENT-R (frozen)

* **18 % of IF2 inversion candles are DISPLACEMENT-R** candles of the IFVG's side. Examples:
  * with displacement: NQ1! 2026-10-27 04:27 bearish IFVGs [29371.75, 29380.00] and [29382.25, 29388.75]; 06:14 bearish [29400.25, 29410.75];
  * without: 04:00, 04:02, 04:41.
* Requiring it (IF3) misses 82 % and moves the event away from the inversion the references show.
* **Displacement is context / quality metadata for a later layer, not a requirement.** DISPLACEMENT-R is unchanged.

## H · Relationship with liquidity and LRL (frozen Phase 2, LRL unchanged)

Events in the 10 bars up to an IF2 inversion:
* the opposite liquidity swept (bearish IFVG: BSL_SWEEP): 11 %;
* a swing broken in the inversion's direction: 13 %;
* an LRL terminal event: 21 %;
* a same-side CISD: 55 %.

None is close to a defining condition. All are context for a later confluence layer.

## I · Recommended IFVG-R

Exact definitions: `docs/IFVG.md` DEF-IFVG1…IFVG9. Bearish IFVG from a bullish FVG; the bullish IFVG is the exact mirror.

| item | IFVG-R |
|---|---|
| eligible parent | a Phase 1 FVG (DEF-A1 / A2, the frozen detector and its inputs) still tracked (open) by the FVG engine when it is invalidated |
| trigger | the parent's DEF-A5 invalidation, unchanged: `close < bottom`, strict, from confirmation + 1. Prices are on the tick grid, so this is "at least one tick below" (≡ `close < bottom − EPS`) |
| not a trigger | a wick beyond with a close inside (or at) the zone; a close exactly at the bottom |
| gap through | yes: it is a close beyond (all parent milestones and the inversion on one bar) |
| confirmation | the close of that bar (Confirmed mode; never intrabar) |
| side | bearish (the opposite of the parent) |
| geometry | the parent's top, bottom and CE, exactly |
| identity | the parent's id (candle-3 time) + the IFVG side. A parent inverts at most once, so the key is unique and survives reload, prefix, visibility, memory order and replay |
| facts (from the next bar, stamped once, wick reach as DEF-A4) | retest = high ≥ bottom (the near edge); CE = high ≥ mid; full = high ≥ top (traversed) |
| terminal | INVALIDATED on the first `close > top` (strict), the DEF-A5 mirror; no second inversion |
| memory | 50 per side; the oldest invalidated record first, else the oldest active (the DEF-A6 mirror) |
| events | `IFVG_INVERTED`, `IFVG_FIRST_TOUCH`, `IFVG_INVALIDATED`, `IFVG_DROPPED_MEMORY` (CE and full are record facts) |
| relationship to the parent | observer: Phase 1 is never written; the parent stays INVALIDATED in Phase 1 |
| relationship to CISD / displacement / liquidity / LRL | none in detection; context for a later confluence layer |
| relationship to fill / invalidation | the inversion is the invalidation; the parent's prior state is metadata (`pre`) |

**Why IF2.**
* It is the frozen geometry's own close-through, identical to DEF-A5, so the inversion is the event IST already logs and parity already verifies.
* It agrees with every reference observation (by the close, with the parent box).
* It adds no parameter, and it is the earliest deterministic closed-bar decision.
* IF1 marks rejected wicks; IF3, IF4 and IF5 delay or drop the event and couple modules.

## J · State machine

```
                  parent's DEF-A5 close beyond its far edge
Phase 1 FVG (open) ─────────────────────────────────────────▶ IFVG ACTIVE ──── close strictly beyond the IFVG's far edge ──▶ INVALIDATED
                                                                  │  facts, once each: retest (near edge) → CE → full (far edge)
                                                                  └── memory ──▶ (dropped: IFVG_DROPPED_MEMORY)
```

* Two states: ACTIVE and INVALIDATED.
* There is no RECLAIMED state: a close back inside the zone (T1) is mitigation, not an end, as for a Phase 1 FVG.
* BROKEN is the INVALIDATED end itself.
* There is no age limit.
* The same-bar order is retest → CE → full → invalidation (the DEF-A7 mirror).

## K · Event and record schema

**Events** (dir = IFVG side; sid = the parent's id; origin = the parent's candle 1):

| event | price |
|---|---|
| `IFVG_INVERTED` | the inverting close |
| `IFVG_FIRST_TOUCH` | the near edge |
| `IFVG_INVALIDATED` | the close |
| `IFVG_DROPPED_MEMORY` | CE |

**Record:**
* identity: id, side;
* the parent: origin bar, parent bar (candle 3);
* geometry: top, bottom, mid;
* the inversion: bar, time, close;
* `pre`, the parent's state before the inversion bar: UNTOUCHED, TOUCHED, CE or FULL;
* facts: retest, ce, full;
* end;
* status.

Context (CISD, displacement, sweeps, LRL, session) is not stored; a later layer joins it by bar and time.

## L · Oracle implementation

`validation/models/ifvg.py` is the opt-in module `"ifvg"`. It needs `"fvg"` and reads the Phase 1 engine's records without writing them.
* **Settings:** `IfvgSettings(memory=50)`. The definition has no parameter.
* **Events:** `ORACLE_ONLY`, so ST-14 excludes them until Pine has them.
* **Per bar:**
  1. active IFVGs advance;
  2. the FVGs created this bar join the observer's registry, and the invalidated ones become IFVGs, in parent creation order;
  3. memory.
* **The registry** copies each parent on its confirmation bar. A parent the FVG engine releases on its own invalidation bar still inverts (tested; plain scanning of the FVG memory would miss it).
* **Equals the study.** On the real data the oracle is IF2 exactly: 566 inversions, every lifecycle fact equal to the study's.
* **Default memory:** 266 / 140 / 160 inversions per segment.

## M · Test totals

* **`tests/test_ifvg.py`: 26 deterministic tests.**
  * Both directions; a wick beyond with a close inside; a close exactly at the edge; one tick beyond; immediate inversion.
  * After touch, CE and full fill; gap through and the same-bar order; no IFVG fact on the inversion bar.
  * The parent stays INVALIDATED and Phase 1 is unchanged.
  * The lifecycle (retest, CE, full, close at the far edge vs one tick beyond); no second inversion; the mirrored lifecycle.
  * The size filter; a parent dropped while open; a parent released on its inversion bar; the FVG module required.
  * Memory; oracle = study (566); real counts; identity under prefix / shift / every module; determinism; view settings; other modules unchanged; settings round trip.
* **`fuzz/test_ifvg_properties.py`:** invariants, mirror, translation, no lookahead, other modules (Phase 1 FVG state included) unchanged, long walks.
* **`tests/test_ifvg_study.py`:** 8 harness tests (IF2 = DEF-A5, wick first, IF4 after the full fill, symmetry and no lookahead for IF1–IF5, quoted numbers).
* **Invariants INV-IFVG-01…07**, each with a negative corruption test:

| id | checks |
|---|---|
| INV-IFVG-01 | the trigger, iff the Phase 1 invalidation |
| INV-IFVG-02 | the inherited geometry and identity |
| INV-IFVG-03 | facts never missed or early |
| INV-IFVG-04 | the end |
| INV-IFVG-05 | frozen fields |
| INV-IFVG-06 | events = records |
| INV-IFVG-07 | memory and its release order |

* **FULL validation (validation 1.19.0): PASS**, exit 0, 601.6 s, **1101 passed, 1 skipped** (the long-standing parity skip). IFVG-specific: 26 oracle + 8 study + 5 property + 3 long walks + 7 negative = 49 tests. Every other section is unchanged.

## N · Open questions for the user

| # | decision | recommendation |
|---|---|---|
| N1 | trigger | **IF2 = the frozen DEF-A5 invalidation** (strict close beyond the far edge) |
| N2 | the IFVG's end | **close strictly beyond its far edge (T2)**. Alternatives: T1 (a close back beyond the near edge), or no end (memory only) |
| N3 | events | **INVERTED, FIRST_TOUCH, INVALIDATED, DROPPED_MEMORY**; CE and full as record facts only. Alternative: CE / FULL events like Phase 1 |
| N4 | second inversion of an invalidated IFVG | **none** (one generation) |
| N5 | memory | **50 per side**, invalidated first |
| N6 | eligible parents | **Phase 1 qualified FVGs only** (option A); raw gaps excluded |
| N7 | dependence on the [calc] FVG inputs | **accept**: the IFVG follows the Phase 1 universe the user configured |
| N8 | HTF IFVG | later and separate: the same rules on `HtfZone` with the own-timeframe close (DEF-B4), its own registry and events with `tf` |
| N9 | volume of IFVGs (87 % of FVGs, about 9 / h on 1m) | keep base detection complete; relevance (displacement, CISD, sweep, recency, HTF) belongs to a later quality / confluence layer and the renderer |
| N10 | human goldens | none exact yet (H1 is supporting); real labelled cases needed before a freeze |
| N11 | renderer and alerts | later (styling frozen) |

## O · Pine feasibility and risks (no Pine yet)

**Feasible as an observer after the frozen Phase 1 FVG block, without touching Phase 1 lines** (ST-15 stays green):
* Each bar, add the records with `confirmBar == bar_index` from `bullFvgs` / `bearFvgs` to an IFVG registry. UDT objects are references, so a parent the FVG engine releases on its inversion bar stays reachable.
* Turn the registry entries with `invBar == bar_index` into IFVG records, in creation order.
* Advance the active IFVGs with the current bar's high, low and close only. There is no history read anywhere (ST-21).

**Costs.** Per bar, one pass over the registry (open FVGs, at most about 2 × memory) and over the active IFVGs (at most 2 × 50).

**Risks.**
1. **Order of several inversions on one bar.** It must match the oracle (parent creation order); it matters only when memory is smaller than the number of same-side inversions on that bar.
2. **Phase 1 timing.** Phase 1 invalidates only on confirmed bars, in both modes; the IFVG must follow the same gate.
3. **Volume.** 87 % of FVGs invert on 1m, so the renderer needs caps and nearest-first selection (N9, N11).
4. **Parity.** It needs an IFVG snapshot (the registry and records) and per-bar fields, as for CISD and displacement.
5. **Inputs.** The IFVG depends on the FVG [calc] inputs. A parity capture must carry them; it already does.
