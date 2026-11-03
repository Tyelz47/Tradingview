# IST · CONTEXT-01 · Target universe

**Status: RESEARCH + SPECIFICATION PROPOSAL (2026-11-03), awaiting the user's review.**
* No frozen module changes. Every source below is read as it is.
* The parent document is `DOL_RESEARCH.md` (DEF-DOL1…DOL8). The measured numbers come from `validation/studies/context.py`.

## 1 · Catalogue

| candidate | side | class | source (status) | known from | `since` (observation must start) | in v1? | notes |
|---|---|---|---|---|---|---|---|
| PDH / PDL | ▲ / ▼ | D | Module G, DEF-G2 (**Phase 1 frozen**; TradingView source **G-V1…G-V5 pending**) | the first chart bar of the new day | the start of the day after the source bar | **yes** | values from `request.security("1D", high[1] / low[1])`: TradingView's own Daily bar |
| PWH / PWL | ▲ / ▼ | W | Module G (same) | the first bar of the new week | the start of the week after | **yes** | often UNVERIFIED: the week start must lie in the loaded history (§3) |
| older D extremes (D-2, D-3) | ▲ / ▼ | D | not in IST: the context layer would need `high[2]`, `high[3]` on 1D | as PDH, one / two days earlier | the start of the day after each bar | **yes (proposal)** | "old highs / lows". On 10-30 both lows were already consumed; the completed D bars show it |
| older W extremes (W-2, W-3) | ▲ / ▼ | W | not in IST (as above, on 1W) | — | — | **yes (proposal)** | on 11-02 every one was already consumed |
| Asia / London / NY AM / NY PM H / L | ▲ / ▼ | S | Module F, DEF-F1…F4 (**Phase 1 frozen**) | `SESSION_END`: the first bar outside the window | the same bar | **yes, completed sessions only** | a window in progress at load is never tracked (DEF-F2). A session can be taken on the very bar that ends it |
| developing session / day / week H / L | — | — | Module F `live` | — | — | **no (DEF-DOL6)** | it moves; location only |
| BSL / SSL | ▲ / ▼ | SW | Phase 2 DEF-L1 / L2 / L4 (**frozen**) | the confirmation bar (X + right) | the confirmation bar | **yes, internal by default** | 1m Balanced: W = 30 bars, so "dominant" means 30 minutes |
| EQH / EQL | ▲ / ▼ | EQ | Phase 2 DEF-L5 (**frozen**) | `EQH_CREATED` (qualified) | the qualification bar | **yes** | the price is the pool's `bound` |
| LRL | ▲ / ▼ | (diagonal) | DEF-LRL1…LRL9 (**experimental**) | `LRL_CONFIRMED` | — | **path, not a target** | its price moves each bar. A context that depends on it cannot freeze before LRL does |
| major 1H / 4H / Daily swings | ▲ / ▼ | — | **not in IST** (Phase 2 runs on the chart timeframe only) | — | — | **no: RESEARCH REQUIRED** | §6 |
| ATH / ATL | ▲ / ▼ | — | not in IST; continuous-contract back-adjustment makes it ill-defined | — | — | **no** | §6 |
| day open, midnight open | — | — | Module G DEF-G4 | — | — | **no (location)** | — |
| FVG / IFVG / HTF FVG | — | zone | Phase 1 / IFVG-R (frozen) / HTF FVG (experimental) | — | — | **path (DEF-DOL5)** | delivery zone, obstacle, context |

**One reach rule for every level.** A level is reached by DEF-L4: strictly beyond by a wick, classified at that close.
* Phase 2 tracks it for BSL / SSL / EQH / EQL (frozen state).
* For the period and session extremes, the context layer applies the same rule read-only. Module F / G only *set* values; they track no take.

## 2 · States per source

| source | AVAILABLE | CONSUMED (SWEPT / BROKEN / ?) | UNVERIFIED |
|---|---|---|---|
| BSL / SSL / EQH / EQL | Phase 2 `ACTIVE` / qualified and untaken | Phase 2 `TAKEN`, `cls` SWEEP / BREAK (frozen) | a level born before the loaded history is unknown to the engine (LIQUIDITY.md §11). It is simply absent, never UNVERIFIED |
| PDH … W-3 | every trade since `since` seen, none beyond | the first observed bar beyond: DEF-L4 class; beyond inside a completed HTF bar only: class `?` | some of `[since, t]` unseen |
| session H / L | the same; always fully observed, since the session ended on the chart | DEF-L4 class | — |

## 3 · AVAILABLE needs observation (the loaded-history rule)

* A level can only be AVAILABLE if **every trade since `since` was observed** and none went beyond.
* The harness accepts three kinds of evidence:
  * the 1m bars of the segment;
  * **runs of consecutive completed TradingView bars** (4H, D, W, from Pine's HTF snapshot and HTFBAR lines) that stayed on the near side;
  * consecutive bars of one timeframe leave nothing out between them, so a weekend or the daily break is never a gap.
* A completed bar that went beyond proves nothing about its part after `since`.
* Not taken in what was seen, but with part unseen → **UNVERIFIED**, never eligible.
* Measured over the 13 decision points: 6 of 54 weekly targets were UNVERIFIED. An example is PWL on MNQZ2026 10-29 / 30: the Monday 10-26 session is in no capture.
* **The Pine implementation question is open (CONTEXT-03+).** A level born before the loaded history needs either a period start inside the history or an HTF source of the running extreme since `since`. Today's frozen Module G supplies neither, and nothing about it is assumed here.

## 4 · Internal versus external

**Definitions (proposal).**
* A **reference range** R = [lo, hi] has an identity, a known time and a validity.
* For a target x:
  * **BOUNDARY** of R: `x.price` = R.hi (▲) or R.lo (▼), within the EQ tolerance;
  * **BEYOND** R: above R.hi (▲) or below R.lo (▼);
  * **INSIDE** R: strictly between.
* External to R = boundary or beyond. Internal to R = inside.

**Ranges in v1: deterministic, from frozen sources, known when they become final.**

| range | from | known | valid until |
|---|---|---|---|
| R_W = [PWL, PWH] | Module G | the first bar of the week | the next week's roll |
| R_D = [PDL, PDH] | Module G | the first bar of the day | the next day's roll |
| R_S = [L, H] of each completed session of the current trading day | Module F | `SESSION_END` | the trading day's end |

* **Externality vector.** For every target, its relation to every range valid at t. **Externality rank** = the largest range it bounds or lies beyond (W > D > S). Nothing forces one range.
* **Transitions (deterministic).**
  * When a boundary is CONSUMED, the range is *exceeded* on that side, and the external liquidity of that side becomes the next AVAILABLE target beyond: PDH taken → PWH, D-2 H, or an older untaken high.
  * At a roll, ranges are replaced. Yesterday's PDH becomes D-2 H, and is external to the new R_D only if it lies beyond it. Each time t is recomputed from scratch, so no state can drift.
* **Nested ranges.** R_S ⊂ R_D ⊂ R_W while price stays inside. A session extreme is external to its session and normally internal to R_D. The rank keeps that explicit without choosing one.
* **Phase 2 levels (SW / EQ) are internal by default.**
  * Their C1 dominance (DEF-L2b) is the extreme of 30 1m bars: window-local, not range-level.
  * A Phase 2 level beyond R_D can exist only as an older untaken swing still in memory, or after R_D broke.
  * Even then it stays class SW / EQ: eligible as path or NEXT, not PRIMARY (DOL_RESEARCH §7).
* **Swing-defined dealing ranges: RESEARCH REQUIRED.** "The last swing high and low" is ambiguous on several counts:
  * which swings (1m pivots are minutes apart);
  * which pair brackets price when legs nest;
  * when the range dies;
  * how an HTF swing is confirmed without an HTF swing engine.

  No definition is proposed until a study shows a deterministic, reload-stable rule.

## 5 · Composite pools (DEF-DOL7)

Targets on one side within the EQ tolerance merge into one pool that keeps every label. In the data:
* NQ1! 10-27 19:59: PDH 29881.25 = NY PM H 29881.25.
* MNQ1! 11-02 09:29: PDL 28232.25 = PWL 28232.25. Friday's low was the week's low.
* MNQ1! 11-02 19:59: PDH 28891.5 = NY AM H 28891.5, and PDL 28101.25 = NY PM L 28101.25.

So coincidence is **structural**: the day's extreme *is* the extreme of the session that printed it. A pool is one target, never "two confirmations".

## 6 · Longer-range liquidity (assessment, nothing implemented)

| candidate | assessment | proposal |
|---|---|---|
| older D / W extremes | Cheap. They are the classic "old highs / lows", and the HTF snapshot proves the values exist in Pine (`HTFSTATE` D / W bars) | v1 (D-2, D-3, W-2, W-3) |
| 1H / 4H / Daily swing pivots | Need an HTF pivot engine: a new multi-timeframe engine, excluded in this phase. Each also needs its own significance rule (DEF-L2 on HTF bars?) | RESEARCH REQUIRED; reconsider after CONTEXT-03 |
| ATH / ATL | Back-adjusted continuous contracts move the historical extreme, and intraday NQ rarely trades there | excluded. The useful fact, "no external liquidity on this side", is already the PRIMARY = NONE case |

## 7 · Measured census (13 decision points, `python -m validation.studies.context`)

| class | targets seen | AVAILABLE | TAKEN | UNVERIFIED | nearest AVAILABLE, median × TR average ▲ · ▼ |
|---|---|---|---|---|---|
| W | 54 | 16 | 32 | 6 | 97.9 (n=6) · 19.1 (n=5) |
| D | 58 | 28 | 30 | 0 | 43.7 (n=10) · 28.6 (n=6) |
| S | 42 | 26 | 16 | 0 | 21.0 (n=10) · 15.4 (n=6) |
| EQ | 5 | 5 | 0 | 0 | 1.8 (n=1) · 10.7 (n=3) |
| SW | 75 | 75 | 0 | 0 | 6.4 (n=13) · 3.0 (n=11) |

What the census shows:
* External targets sit tens of TR averages away; the nearest SW levels sit 3–6. The two are different scales of liquidity.
* About half of all period targets were already consumed at a session open.
* EQ pools are rare in this data.
* Across 83 h there were only **16 first takes of an AVAILABLE external target**: 5 sweeps and 11 breaks. Phase 2 had 232 sweeps and breaks over the same bars. External liquidity events are rare, which is why the dataset must be large (RESEARCH_CASES §9).

## 8 · Prerequisite: the level source

* PDH / PDL / PWH / PWL are the most important targets. Their TradingView source tests **G-V1…G-V5 are PENDING** (`docs/TESTS.md` §G-V).
* The HTF snapshots in the evidence are *consistent* with ARCHITECTURE §7.2, which expects 18:00 ET D bars and Sunday 18:00 ET weeks:
  * every completed D bar opens at 18:00 ET, Monday's on Sunday 18:00;
  * the W bars open on Sunday 18:00;
  * the 4H bars open at 18 / 22 / 02 / 06 / 10 / 14;
  * the 11-01 DST change leaves the D open at 18:00.
* **This is not a G-V pass.** The user's TradingView check is required before any context layer is frozen (CONTEXT_ROADMAP §2).
