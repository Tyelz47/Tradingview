# IST · Inversion fair value gap (DEF-IFVG1 … IFVG9)

**Status: APPROVED (2026-11-02), with two clarifications and the revised memory rule (§6). In Pine since v0.9.0-dev; the current build is v0.9.1-dev (EXPERIMENTAL, not frozen; TradingView tests IFVG-L00… pending, `docs/TESTS_IFVG.md`).**
* This is the recommendation IFVG-R of `docs/STUDY_IFVG.md` §I.
* Reference model: `validation/models/ifvg.py`, the opt-in module `ifvg` of the oracle. It needs the Phase 1 module `fvg`. Default runs and the regression baseline do not include it.
* Pine: `src/IST.pine` v0.9.1-dev (§7), transliterated in `validation/models/ifvg.py` `IfvgPine` and proven equal to the oracle.
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
| DEF-IFVG8 memory | `IFVG_MEM = 50` is the **retention target** per IFVG side, not a cap on logical state (revised and approved 2026-11-02, §6). An ACTIVE IFVG is never dropped. While a side holds more than 50 records, its oldest INVALIDATED record leaves (inversion order), one at a time, each with `IFVG_DROPPED_MEMORY`. When every record of the side is ACTIVE, nothing leaves: the side may hold more than 50 (temporary overflow) until ends let it compact. One routine runs after the bar's ends (bullish side, then bearish) and after each inversion. Several inversions on one bar are recorded in parent creation order |
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

## 4 · Validation (validation 1.20.0)

* `tests/test_ifvg.py` (oracle, deterministic).
* `tests/test_ifvg_pine.py` (Pine's formulation = the oracle on the approval's cases 1–35 and the real data; ST-23 and its mutations; the Pine diff against the frozen baseline only adds lines).
* `tests/test_ifvg_memory.py` (DEF-IFVG8: temporary overflow, compaction, lifecycles unchanged, walks).
* `tests/test_parity_ifvg.py` (bounded parity on synthetic captures, corruption kinds).
* `fuzz/test_ifvg_properties.py` (invariants, Pine = oracle, mirror, translation, no lookahead, other modules unchanged, long walks).
* `tests/test_ifvg_study.py` (the research harness).
* Invariants INV-IFVG-01…09, each with a negative test.
* The full list: `docs/TESTS_IFVG.md`.

## 5 · Not started (by instruction)

* HTF IFVG (N8).
* Final styling: drawing and alerts.
* Context / quality scoring / confluence.

## 6 · Approval clarifications (2026-11-02)

**Eligibility.** An original FVG is IFVG-eligible if it is in the Phase 1 logical FVG universe immediately before its DEF-A5 invalidation.
* It is invalidated and released by the Phase 1 memory on the same bar: it inverts.
* It was released earlier without an inversion: it never inverts.
* Visibility (Show FVGs, the display policy, caps) is irrelevant.

The registry of FVGs that may still invert has no retention of its own. After every bar it equals the open Phase 1 FVGs in memory (INV-IFVG-08).

**One close rule.** The inversion is Phase 1's DEF-A5 bar itself, read from the Phase 1 record (`invBar`). The IFVG module never evaluates a second close-through rule.
* DEF-A5 compares strictly, without EPS (`close < bottom`).
* On the tick grid this equals `close < bottom − EPS`: prices are multiples of the tick and EPS is 0.01 tick.
* The IFVG end is the mirror, `close > top` (bearish IFVG), with the same equivalence.

**Memory (review of v0.9.0-dev, 2026-11-02).** The v0.9.0-dev fallback (when all 50 records of a side are ACTIVE, the oldest ACTIVE one goes) is **not approved**: an ACTIVE IFVG is logical market state and never disappears to enforce a storage cap. DEF-IFVG8 above is the approved rule (v0.9.1-dev).
* Only an INVALIDATED record is ever dropped, and `IFVG_DROPPED_MEMORY` is emitted only for one.
* Example: 52 ACTIVE → all 52 kept. One becomes INVALIDATED → `IFVG_INVALIDATED`, then the memory routine: the side holds 52 > 50 and a terminal record exists, so the oldest INVALIDATED record leaves (`IFVG_DROPPED_MEMORY`). An older INVALIDATED record, if one exists, leaves first.
* So the future facts and end of every ACTIVE IFVG are always observed: every IFVG event but the drops is the same as with an unlimited memory (INV-IFVG-09, `tests/test_ifvg_memory.py`).

## 7 · Pine (v0.9.1-dev)

One input: `ifvgOn` ("Enable IFVG engine", [calc], ON). One constant: `IFVG_MEM = 50`.

**Architecture.** An observer placed in ENGINE RUN after the frozen Phase 1 FVG block (milestones, creation, release) and before displacement.

The state is `IfvgBook`:
* `shadows`: references to the Phase 1 `Fvg` records that may still invert;
* `bull` and `bear`: the IFVG records;
* the counters.

Per confirmed bar, when ON:
1. **advanceIfvg** runs on every active IFVG, from the bar after its inversion, bullish IFVGs then bearish. First the wick facts, each stamped once: retest, CE, full. Then the close: strictly beyond the far edge means INVALIDATED.
2. **compactIfvg** (memory) runs on the bullish side, then on the bearish side: an end on this bar may let an over-full side compact.
3. **observeIfvg** runs next:
   * The Phase 1 FVG created on this bar joins `shadows` (`bullFvgs.last()` / `bearFvgs.last()` when its `confirmBar` is this bar).
   * Then, in shadow (creation) order:
     * a shadow whose `invBar` is this bar inverts (**invertIfvg**: record, `IFVG_INVERTED`, then **compactIfvg** of its side) and leaves;
     * a shadow that Phase 1 released while open (its own `fvgDropNow` list) leaves.

The shadow reference survives Phase 1's same-bar release, so clarification 1 holds. The observer reads Phase 1 records and lists and never writes them (ST-23).

**Memory (DEF-IFVG8, `compactIfvg`).** One routine: while the side holds more than `IFVG_MEM` records, scan from the oldest; skip an ACTIVE record, remove an INVALIDATED one (`IFVG_DROPPED_MEMORY`); stop at the cap or at the end of the side.
* On the real data the sides never exceed 50, and the drops are the same as in v0.9.0-dev.
* On trending random walks a side holds many ACTIVE IFVGs at times: on 20,000-bar walks up to 93, 248 and 180 (seeds 1–3), all kept. Their ACTIVE IFVGs and every lifecycle event equal those of an unlimited memory.
* There is no hard bound: the number of ACTIVE IFVGs is what the market leaves open. A Pine array holds up to 100,000 elements.

**Diagnostics** (read only):
* Data Window, Debug mode: shadows, active bullish IFVGs, active bearish IFVGs, inversions so far.
* Events in Pine Logs. No drawing, no alert.

**Parity capture.**
* CAPTURE carries `ifvg=1|ifvgmem=50`.
* After captured bar `fvglen + 2`: one `IFVGSTATE` line (`at`, the counters, the shadows as `id:dir`), the whole Phase 1 memory as `FVGREC` lines, and the IFVG records as `IFVGREC` lines.
* Every BAR line carries:
  * `IS` = shadows count : Σ id/1000;
  * `IA` = active bullish : bearish;
  * `IX` = the CE / full facts stamped on the bar.
* The parity tool restores the snapshot into the oracles and replays the rest (`validation/parity/capture.py` `_compare_ifvg`).
