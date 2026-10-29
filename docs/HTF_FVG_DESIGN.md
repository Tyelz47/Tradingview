# HTF Fair Value Gaps · technical design (for approval)

**Status: DESIGN ONLY, nothing implemented.**
* No change to `src/IST.pine`, the oracle, Phase 1, Phase 2 or LRL.
* It develops ARCHITECTURE Appendix A, **DEF-B** ("DEF-A evaluated inside the HTF request with offset [1]; de-duplicated by HTF c3 time; lifecycle on chart bars").
* The user's reference screenshots (2026-10-29) are the visual target: a clean rectangular zone, its timeframe written small at the bottom right, only important HTF zones, minimal clutter.
* Decisions the user must make are marked **D1 … D10** and collected in §13.

---

## 1 · Architecture

A new, separate module, **Module B · HTF FVG**, beside the frozen Phase 1 FVG engine (Module A). It does not replace Module A.

| layer | HTF FVG |
|---|---|
| L1 market data | 6 `request.security` calls, one per timeframe (15m, 30m, 1H, 4H, 1D, 1W). Each returns only values of **completed** HTF bars (§2) |
| L2 detection | DEF-A1 geometry and DEF-A2 qualification, evaluated **inside** each request on that timeframe's own candles and TR average |
| L3 state | `HtfFvg` records, one registry per timeframe, keyed (timeframe, direction, candle-3 open time). Lifecycle on **chart bars** (§4) |
| L5 events | the `HTF_FVG_*` family; the timeframe is part of the identity and of the event text |
| L6 renderer | per-timeframe caps, timeframe hierarchy, the timeframe label as box text (§6, §9) |
| L7 | debug rows; Parity capture extension (§10) |

**Rules, as everywhere in IST:**
* Calculation never depends on visibility. The timeframe switches (15m … 1W ON / OFF) are **[view]**: every timeframe above the chart timeframe is always computed.
* Records of different timeframes are **never merged**: overlap is a rendering question only (§7).
* Timeframes at or below the chart timeframe are inactive. On 1m all six run; on a 15m chart, 30m … 1W run.

## 2 · HTF data acquisition

One call per timeframe (`"15"`, `"30"`, `"60"`, `"240"`, `"D"`, `"W"`):

```
[c3T, c3Close, c1T, hi3, lo3, hi1, lo1, cl3, tra1, seeds…] =
    request.security(syminfo.tickerid, TF, f_htfPack(), lookahead = barmerge.lookahead_on)
```

**`f_htfPack()` reads only bars [1] and older.** In the HTF context, candle 3 = `[1]` (the last completed HTF bar) and candle 1 = `[3]`. Its fields:

| field | expression |
|---|---|
| `c3T` | `time[1]` (the id) |
| `c3Close` | `time_close[1]` |
| `c1T` | `time[3]` |
| `hi3`, `lo3` | `high[1]`, `low[1]` |
| `hi1`, `lo1` | `high[3]`, `low[3]` |
| `cl3` | `close[1]`: the own-timeframe close, for DEF-B4 |
| `tra1` | `ta.sma(ta.tr(true), 14)[3]`: the TR average at candle 1, as in DEF-A2 |

This is the same non-repainting pattern as PDH / PDL (DEF-G2): lookahead_on only aligns an already-closed value to the start of the next HTF bar. A static check (an extended ST-03) will require that every HTF request uses `lookahead_on` and reads nothing newer than `[1]`.

**Seeds (D3).** A chart-side engine only sees HTF FVGs whose candle 3 closes inside the loaded chart history. On a 1m chart (≈ 3.5 days on the free plan) that misses the older, still-open 1D / 1W zones, which are the important ones. So `f_htfPack()` also returns the **K most recent zones still open as of the last completed HTF bar**: K = 3 per direction, as fixed tuple slots (top, bottom, c1 time, c3 time, deepest penetration).
* They come from a small engine inside the HTF context.
* It uses only [1]-shifted inputs, at HTF resolution.
* The chart registers them when they first appear (§4 DEF-B2).

## 3 · Exact non-repainting timing

For timeframe P, the three candles are HTF bars k−2, k−1 and k (candle 3 = k, opening at o_k and closing at c_k).

| moment | value |
|---|---|
| HTF candle origin | candle 1 open time (k−2): the zone's **origin** |
| HTF confirmation | c_k, candle 3's close (`time_close`) |
| chart bar where it becomes known | the **first chart bar whose open time ≥ c_k**, i.e. the first chart bar of HTF period k+1. lookahead_on + [1] switches exactly there |
| state change (Confirmed mode) | at that chart bar (§4 D2). In Live mode, at its first tick |
| unfinished HTF candle | never read. No provisional HTF zone (an optional preview could come later: never stored, logged or alerted, like DEF-A8) |
| request.security | `lookahead_on` with every series `[1]`-shifted. `lookahead_off` with `[0]` is **not** used: it repaints in realtime |

**Examples on NQ1! 1m (New York):**
* **15m:** candles 09:30 / 09:45 / 10:00. Confirmed at 10:15; known on the 10:15 chart bar. Id = (15m, dir, 10:00).
* **1H:** candles 08:00 / 09:00 / 10:00. Known on the 11:00 chart bar.

**Session boundaries are TradingView's own:**
* The 4H, 1D and 1W candles are the ones `request.security` returns: for CME, sessions starting 18:00 ET, 4H at 18 / 22 / 02 / 06 / 10 / 14, the week starting Sunday 18:00. **Verify on TradingView**; see §10 check (a).
* No chart-side aggregation is needed, so the open previous-day questions (G-V1…G-V5) do not affect detection. They do affect how the oracle aggregates for checking.

## 4 · Lifecycle (proposed DEF-B)

Rules are written for bullish zones; bearish ones mirror them.

* **DEF-B1 Creation.** At the known bar, if DEF-A1 holds (`lo3 > hi1`, zone `[hi1, lo3]`) and DEF-A2 holds: gap ≥ max(2 ticks, 0.10 × `tra1`).
  * **D4:** use the Phase 1 default numbers as fixed HTF constants (recommended: no new inputs), or read the Phase 1 inputs.
  * Event: `HTF_FVG_CREATED`.
* **DEF-B2 Seeding.** A zone from the seed slots that the registry does not know yet is registered on the chart bar where it first appears (normally the first loaded bar).
  * It carries its HTF-side state: touched or CE already, deepest penetration.
  * It is flagged *seeded*: its earlier milestones are known at HTF resolution only.
  * Event: `HTF_FVG_SEEDED`. A seed equal to an existing id is ignored, so there are never duplicates.
* **DEF-B3 First touch / CE / full fill.** The DEF-A4 rules on **chart-bar** wicks, each stamped once, in the DEF-A7 same-bar order.
  * **D2:** counted **from the known bar itself** (recommended: the zone was confirmed before that bar opened), or from the bar after (Phase 1's DEF-A3 symmetry).
* **DEF-B4 Invalidation.** **D5**, two options:
  * **(a) recommended:** a confirmed close **of the zone's own timeframe** beyond the far edge (`cl3`). A 1m close below a 4H zone is not a 4H invalidation. It is known on the first chart bar of the next HTF period.
  * **(b):** a chart-bar close, as in Phase 1.
* **DEF-B5 Mitigation (display).** As Phase 1, default **full fill**:
  * untouched and **partially filled zones stay visible**;
  * a zone is no longer drawn after full fill or invalidation (optionally faded, Developer).
* **DEF-B6 Memory.** 20 records per timeframe (both directions). When full, the oldest *closed* (fully filled or invalidated) record goes first, else the oldest open one. Each drop logs `HTF_FVG_DROPPED_MEMORY`. That is ≤ 120 records.
* **Events:** `HTF_FVG_CREATED · SEEDED · FIRST_TOUCH · CE_TOUCH · FULL_FILL · INVALIDATED · DROPPED_MEMORY`. dir ±1, sid = candle-3 open time, and the timeframe in the text (`tf=15`) and in every key.

## 5 · Record identity

* **Identity = symbol + timeframe + direction + candle-3 open time.** This is the ARCHITECTURE §7.2 point 10 requirement.
* A 15m and a 1H zone can share a candle-3 open time (10:00): the timeframe separates them.
* Kept on each record: origin = candle-1 open time, confirmation = candle-3 close, known = the chart bar time.
* Alert de-duplication keys include the timeframe.
* Phase 1 records keep their own identity (chart timeframe).

## 6 · Renderer hierarchy

* **Which zones (D6):** per timeframe, the **nearest open zone above and below price**, so at most 2 per timeframe and **≤ 12 boxes** in total. The alternative is 2 per side (≤ 24).
* **Z-order:** drawn from the highest to the lowest timeframe (1W first, 15m last), so a nested lower-timeframe zone stays visible over its parent. Pine draws later objects on top.
* **Box extent:**
  * left at the HTF candle-1 open time, the origin, as in the references (**D8**; alternatives: candle 3, or the known bar);
  * right at the current bar + right offset while open;
  * `xloc.bar_time`.
* **Prominence by opacity and border only (D7):** colour as Phase 1 (bull green / bear red) or neutral gray as in the references. The proposal:

| timeframe | fill transparency | border |
|---|---|---|
| 15m | 94 | none |
| 30m | 93 | none |
| 1H | 91 | 1 px, faint |
| 4H | 89 | 1 px |
| 1D | 87 | 1 px, solid |
| 1W | 85 | 2 px |

## 7 · Overlap strategy (to approve before any merging)

| | rule | pros | cons |
|---|---|---|---|
| **A** | draw every zone within the per-timeframe caps | simple, faithful, deterministic | nested zones stack |
| **B** | where zones overlap, only the highest timeframe | very clean | hides valid lower-timeframe information |
| **C** | merge overlapping boxes visually (records stay separate) | cleanest look | a merged box has no single timeframe or label; hard to explain; **not recommended now** |
| **D** | hide a lower-timeframe zone fully contained in a **visible** higher-timeframe zone of the same direction | removes the most redundant clutter | the visible set depends on the higher timeframe's visibility |
| **E** | nearest relevant zones per timeframe (§6) | bounded clutter | far zones are not shown |

**Recommendation:** **A within the E caps** as the default, with **D as an option, default OFF until approved** (D1). B and C are not proposed now.
* Containment for D: same direction, `Z.top ≤ H.top` and `Z.bottom ≥ H.bottom`, and H is drawn on this bar.
* Logical records are never merged by any option.

## 8 · Objects and resources

* **`request.security`:** +6, so 8 in total (limit 40). Each returns ≈ 40 values with K = 3 seeds per direction.
* **Boxes:** ≤ 12 by default (+ ≤ 12 faded if that Developer option is on). They are shared with Phase 1 boxes (limit 500).
* **Labels:** 0, because the label is the box's own text. **Lines:** 0; an optional CE line would add ≤ 12.
* **Memory:** ≤ 120 records. Per closed chart bar, an O(open records) milestone scan (≤ 120).
* **HTF contexts:** 6 small seed engines inside the HTF contexts. Their execution time is to measure (HTF-L test).

## 9 · Labels and exact placement

* The **box text** is the label: `text_halign = text.align_right`, `text_valign = text.align_bottom`, `text_size = size.tiny`, gray `#787B86` at ~30 % transparency, no wrapping.
* So it always sits in the **bottom-right corner inside the zone**, aligned the same way for every FVG, like the references.
* **Text:** `15m Fair Value Gap`, `30m Fair Value Gap`, `1H Fair Value Gap`, `4H Fair Value Gap`, `1D Fair Value Gap`, `1W Fair Value Gap`. A compact form `15m FVG` is a Developer option (**D10**). The timeframe is always written.
* Switch: "Show timeframe labels" (ON).
* Pine cannot know a box's height in pixels. In a very thin zone, the tiny text may be clipped: to check on TradingView.

## 10 · Parity and testing

1. **Oracle:** `validation/models/htf_fvg.py`.
   * A timeframe aggregator, used for synthetic tests and for checking only.
   * The DEF-B1 detector on HTF candles.
   * The seed engine.
   * The chart-bar lifecycle.
2. **Parity capture additions:**
   * the CAPTURE line says `htf=1` and lists the timeframes;
   * one line per completed HTF bar: `HTF|tf|open|close|O|H|L|C`, from the request;
   * at the capture start, a snapshot of the open HTF records: `HTFSEED|tf|dir|id|top|bottom|state`;
   * the `HTF_FVG_*` events, with their timeframe;
   * per BAR line, the count of open records per timeframe.
3. **Checks:**
   * **(a) HTF candles** against the oracle's aggregation of the captured 1m bars. This settles the session alignment. HTF bars not fully inside the window are NOT OBSERVABLE.
   * **(b) Detection** recomputed from Pine's own HTF candles (exact source).
   * **(c) Lifecycle** replayed from the snapshot on the captured 1m bars.
4. **Invariants:**
   * never known before c_k;
   * known on the first chart bar ≥ c_k;
   * milestones on or after the known bar;
   * one record per (timeframe, direction, c3);
   * no merge across timeframes;
   * prefix invariance (no lookahead).
   * Phase 1 / Phase 2 / LRL streams identical with HTF on and off.
5. **Static:** ST-03 extended (8 requests, every one `lookahead_on` and `[1]`); ST-14 names; a new rule for the HTF timing lines; ST-18 (no shared names).
6. **TradingView:** HTF-L00 … (compile; timing in Bar Replay: no zone before its HTF close; labels; caps; objects; 1m / 3m / 5m; the parity capture).

## 11 · Effect on the frozen Phase 1 engine

* **Unchanged:** Module A's calculation, events, alerts and regression. HTF is additive.
* **De-cluttering (D9):**
  * the chart-timeframe FVG display default would become OFF: one Phase 1 *view* line, `fvgShow` true → false, recorded in the reviewed Phase 1 manifest (ST-15);
  * no logic or event changes.
* **Alerts (D9b):** the Phase 1 FVG alerts (bull / bear created, ON by default) would keep delivering chart-timeframe FVGs to an existing alert. Recommendation: leave them unchanged until you decide.

## 12 · Expected Pine limitations

* **History depth.** HTF zones whose candle 3 closed before the loaded chart history are known only through the K seeds per direction. How far back an HTF context reaches on a 1m chart (free plan) must be measured.
* **Timeframes.** Only timeframes above the chart timeframe. Non-standard candles (Heikin Ashi, …) give synthetic HTF values (the existing warning applies).
* **Session alignment.** 4H / 1D / 1W are CME session candles (TradingView). Back-adjusted continuous contracts shift historical prices, as in Phase 1.
* **Seed resolution.** Seeded zones' earlier milestones are known at HTF resolution only. From the known bar on, everything is at chart resolution.
* **Drawing.** Box text cannot be measured in pixels. `bar_time` boxes starting before the first loaded bar are clipped by TradingView.
* **Confirmed mode.** A zone appears at the close of the first chart bar of the next HTF period: one chart bar after the HTF close at most.

## 13 · Decisions requested

| | question | recommendation |
|---|---|---|
| D1 | overlap option D (hide contained lower-timeframe zones) | implement as an option, OFF |
| D2 | milestones counted from the known bar or the bar after | the known bar |
| D3 | seeds (K open zones per direction from the HTF context) | yes, K = 3 |
| D4 | qualification numbers | fixed = the Phase 1 defaults (2 ticks, 0.10 × TR(14) of that timeframe) |
| D5 | invalidation | the zone's own-timeframe close |
| D6 | zones drawn per timeframe | nearest 1 above + 1 below price |
| D7 | colours | direction colours, low opacity; or neutral gray as in the references |
| D8 | box left edge | HTF candle-1 open (origin) |
| D9 / D9b | chart-timeframe FVG display default OFF / Phase 1 FVG alerts | OFF (one reviewed view line) / unchanged |
| D10 | compact label `15m FVG` | Developer option; default full text |
