# IFVG · research requirements (input for a future study; nothing is implemented)

**Status.**
* **Audited on 2026-11-02 by `docs/STUDY_IFVG.md` §A**: every observation holds. The rule is now proposed in `docs/IFVG.md` (IFVG-R: the inversion is the frozen DEF-A5 close beyond the far edge, with the parent's exact geometry).
* One correction: the IFVG observer copies the parent on its confirmation bar, not at its invalidation. The FVG engine can release a just-invalidated record on that same bar.
* This is a requirements note only, written from the user's references.
* No IFVG rule is decided here, and none may be taken from a marketing image alone.
* A future IFVG study must derive a deterministic, non-repainting definition first, as was done for LRL and CISD.

## 1 · Principles that already hold

* **CISD ≠ IFVG.**
  * CISD is a horizontal level: has the delivery state changed? (`docs/CISD.md`)
  * An IFVG is a zone: has an existing FVG undergone a valid inversion?
  * Neither one's base detection may require the other.
  * Confluence (liquidity event → CISD → displacement → FVG / IFVG → HTF context → LRL / DOL quality) is a later, separate layer.
* **Confirmed bar, non-repainting** is the default. "Live" or "the instant they form" in product wording is not a rule. Intrabar marking would need its own decision.
* **An outcome never changes detection.** A failed IFVG or CISD stays what it was; the outcome is metadata.

## 2 · What the references show (observations, not rules)

From `validation/golden/human/img/H1_product_ifvg_cisd.png` and the video (https://www.youtube.com/watch?v=EIbRq4xECnI, 1:16–1:21.5):

| observation | H1 (product image) | video 1:16–1:21.5 |
|---|---|---|
| parent | a bearish 3-candle FVG during the drop: candle 1 low = box top, candle 3 high = box bottom | a bearish FVG during the drop, drawn as an orange "FVG" box |
| inversion candle | a bullish candle **closes above the bearish FVG's top**, the far edge (the same event as our FVG invalidation, DEF-A5) | a bullish candle closes far above the box; the box turns cyan ("IFVG") by the close (it was still orange while that bar was forming above it) |
| IFVG geometry | exactly the parent box (top, bottom), from the parent's candle 1, extended about 9 bars right | the parent box, recoloured |
| after inversion | a later wick tests the IFVG's top edge (now support) and holds | not observed |
| relation to CISD | the IFVG precedes the CISD by 4 bars, below the CISD level | the IFVG and the CISD are confirmed by the same candle |
| HTF | no | "4-hour and high time frame relevant gaps" are said to be marked when inverted (0:14–0:22); not shown in detail |

Not observable in the references:
* a wick-only pass through an FVG;
* partial fills;
* CE behaviour;
* an IFVG's own invalidation;
* bearish inversions;
* how long an IFVG stays active.

## 3 · Questions the IFVG study must answer

1. **Inversion event.**
   * A close beyond the far edge (as in H1 and the video), or a wick?
   * A close beyond the CE?
   * Must the whole gap be traded through first, or a full fill?
2. **Equality and ε.** Is a close exactly at the edge an inversion?
3. **Relevant boundary after inversion.** Which edge acts as support or resistance: near, far or CE? How is a "hold" or a "failure" measured?
4. **CE** after inversion.
5. **Direction.** A bullish FVG inverts into bearish support / resistance, and vice versa: exact mirror rules.
6. **Timing.** Known at the close of the inverting bar (as observed). Is there any lag?
7. **Mitigation and invalidation of the IFVG itself**, and its full lifecycle (states, terminal classes, memory).
8. **Record model.** Does the FVG record transform in place, or is a new IFVG record created that is linked to its parent? (Preferred to evaluate: linked; the parent stays immutable.)
9. **Timeframes.** Chart-timeframe IFVG from Phase 1 FVGs, HTF IFVG from HTF FVG zones (own-timeframe close, as DEF-B4), or both?
10. **Renderer.** A box with the parent geometry, its extension, labels, caps, colour within the `#C2BAAE` palette, and its interaction with HTF boxes.
11. **Overlap with CISD.** The same-bar co-occurrence (video) is metadata for confluence, never a requirement.
12. **Non-repainting.** Prefix invariance, reload behaviour of parents that formed before the chart history, and parity capture.

## 4 · Audit: what the FVG architecture already stores for linking (no change made)

A future IFVG needs: parent id, original side, original timeframe, original top / bottom / CE, inversion bar, resulting side, lifecycle status.

| needed | Phase 1 chart-TF FVG (`Fvg` in Pine; `validation/models/fvg.py`) | HTF FVG (`HtfZone`; `validation/models/htf_fvg.py`) |
|---|---|---|
| parent identity | `id` = candle-3 time, `isBull`, `tf` (chart): key (tf, side, id) | `id` = HTF candle-3 time, `dir`, and the timeframe of its `HtfTf`: key (tf, dir, id); `Event.tf` already carries the timeframe |
| original side | `isBull` | `dir` |
| original geometry | `top`, `bottom`, `mid` (CE) | `top`, `bottom`, `mid` |
| inversion candidate bar | `invBar`, `invTime`: the first close beyond the far edge (DEF-A5) | `invBar` and `invClose`: the first own-timeframe close beyond (DEF-B4) |
| inverting close | not stored in the record; carried as the price of the `FVG_INVALIDATED` event | `invClose`; also the `HTF_FVG_INVALIDATED` price |
| resulting side | derivable (−side) | derivable (−dir) |
| lifecycle after inversion | none: the parent's lifecycle ends at invalidation | none |

**Constraint.** Memory releases closed (invalidated) records first:
* Phase 1: `fvgMemory` per direction;
* HTF: 20 per timeframe.

A linked IFVG must therefore copy the parent's identity and geometry when it is created, not hold a reference.

**Conclusion.** The identity and geometry needed for "inversion tracking" already exist in both FVG engines. The candidate inversion bar exists too, if the study confirms that inversion = close beyond the far edge. No frozen Phase 1 or HTF state needs to change unless the study finds a missing field. The only small gap (the chart-TF invalidating close) is already in the event stream.
