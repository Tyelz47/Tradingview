# IST — Phase 1 acceptance tests (v0.3.2, frozen candidate)

**Status values**

* **PASS** / **FAIL** — the test was executed.
* **PENDING MANUAL VALIDATION** — it requires TradingView, and only you can run it.
* **NOT TESTABLE HERE** — no means to run it in this environment.

Nothing that requires TradingView is marked PASS until you have run it.

**Default setup:**

* NQ1! (CME), standard candles, chart timezone America/New_York.
* **Debug mode ON.** It gives you the state table, the FVG inspector, the event log and the Data Window values.
* "Bar time" means the bar's open time in New York.
* For every FAIL, record a screenshot, the bar date and time, and the expected versus actual result.

**How to read the debug output**

* **`Last events`** lists the latest 6 events, newest first. Each line is `time  TYPE DIR id=… px=… · reason`.
* **Inspect FVG** = *n*. 0 is the newest record, 1 the one before, and so on. The inspector shows:
  * origin → confirm, as bar number and time
  * **zone prices**, labelled: `top … · CE … · bottom …`. Before v0.3.2 these were three unlabelled numbers, and the middle one is the CE, not the bottom
  * **size check @ birth:** gap in points and ticks, mintick, the three thresholds in force when the record was created, the required gap, and the verdict. A record must always show PASS. **INCONSISTENT would prove an engine bug**
  * the milestone times, `—` if not reached
  * the policy status
  * OPEN or CLOSED, and whether the zone is drawn
* **Data Window (debug).** Put the cursor **on candle 3** of the gap being audited:
  * candle-3 verdict: ±2 PASS, ±1 REJECT, 0 no gap
  * raw gap in points and in ticks
  * `syminfo.mintick`
  * the required gap from each of ticks, TR average and avg range
  * `required gap = max`
  * TR average and avg range at candle 1
  * logical record count

---

## Score

| Group | Total | PASS | FAIL | PENDING MANUAL | NOT TESTABLE HERE |
|---|---|---|---|---|---|
| S · static and formula checks (executed here) | 6 | 6 | 0 | 0 | 0 |
| T · runtime acceptance (TradingView) | 50 | 8 | 1 | 41 | 0 |

**Phase 1 runtime acceptance: 8 / 50 passed, 1 failed, 41 pending manual validation.**

* **PASS:** T00, T01, T02, T09–T13. These were run on v0.3.1. v0.3.2 does not change detection, state or rendering, so they stay provisionally passed.
* **FAIL:** T03, on v0.3.1. It needs a re-test on v0.3.2, together with the new regression test T03a.
* The static and formula checks validate the source text and a model of the formula, not the runtime, so they are not counted toward acceptance.

---

## S · Static and formula checks (re-executed here on v0.3.2)

| ID | Check | Method | Status |
|---|---|---|---|
| S-01 | No [view] input or view-derived value is referenced in L1–L5 or the engine run | Scripted scan of `src/IST.pine`: every [view] identifier was located, and none appears outside the input, constant and L6/L7 sections | **PASS** |
| S-02 | No identifiers left over from removed features (`fvgOn`, taken logic, sequential ids, RMA ATR, `bullOpen`, `f_qualifies`) | grep | **PASS** |
| S-03 | Exactly 2 `request.security` calls | grep count = 2 | **PASS** |
| S-04 | Debug adds no drawing objects: 11/11 plots are `display.data_window`, and `dbgOn` creates no line, box or label | grep | **PASS** |
| S-05 | One size rule for both directions: `bullCand = rawBull and gapPass`, `bearCand = rawBear and gapPass`. Exactly one `Fvg.new` site, and nothing else assigns the candidates | grep | **PASS** |
| S-06 | The v0.3.2 L4 expression equals the v0.3.1 expression, and the T03 inputs reject 6.00 points | A Python model of both expressions, with Pine's `na` comparisons evaluating false: 500,000 random cases (mintick 0.25/0.01/0.1/1, `na` references included) gave identical results. With mintick 0.25, minTicks 40, TR k 0.1: 6.00 pts (24 ticks) → REJECT, 9.75 (39) → REJECT, 10.00 (40) → PASS. *This is a model of the formula, not the Pine runtime* | **PASS** |

---

## T · Runtime acceptance

| ID | Test | Procedure → expected | Status |
|---|---|---|---|
| T00 | Script compiles | Pine Editor → Save → Add to chart (NQ1! 1m) → **0 errors, 0 warnings**. Report messages verbatim | **PASS** (v0.3.1). Re-check that v0.3.2 compiles |
| **FVG engine** | | | |
| T01 | Bullish FVG correctly detected | Find 3 candles where candle 3's low is above candle 1's high → zone `[high c1, low c3]`; the box starts at candle 3 (default anchor); `FVG_CREATED BULL` at candle 3's close; the inspector's origin is candle 1, confirm is candle 3; Data Window = +2 | **PASS** (v0.3.1) |
| T02 | Bearish FVG correctly detected | The mirror of T01 → zone `[high c3, low c1]`, `FVG_CREATED BEAR`, Data Window = −2 | **PASS** (v0.3.1) |
| T03 | Small FVG rejected by filters | Min ticks = 4 → a 2-tick gap shows Data Window = ±1 and no event. Set × TR average so that `gap < k·TR average` → ±1. Set the thresholds to permissive values → ±2 and created. Also check that a gap whose edges are exactly equal is rejected (Data Window 0) | **FAIL** (v0.3.1). Re-test on v0.3.2 |
| T03a | **Regression:** a 6-point NQ FVG is rejected when Min ticks = 40 | NQ1! 1m, Confirmed only ON, Min ticks **40**, × TR average 0.1, × avg range 0, memory 50, Debug ON. (a) Put the cursor on candle 3 of the 22:25 bullish gap from the T03 report. The Data Window must show raw gap **6.00 pts / 24 ticks**, mintick **0.25**, required · ticks **10.00**, required gap **≥ 10.00**, verdict **+1 (REJECT)**, and there must be **no** `FVG_CREATED` at that time. (b) For every record, the inspector (n = 0, 1, 2, …) must show `size check @ birth … → PASS` with gap ≥ 40 ticks. (c) If (a) shows +2, or (b) shows INCONSISTENT or a gap under 40 ticks, it is a confirmed engine bug: send screenshots of the Data Window and inspector | PENDING MANUAL VALIDATION |
| T04 | First touch recorded once | A zone revisited on several bars → exactly one `FVG_FIRST_TOUCH` for that id, on the first bar whose wick reaches the near edge; the inspector shows the same time | PENDING MANUAL VALIDATION |
| T05 | CE touch recorded once | One `FVG_CE_TOUCH`, on the first bar reaching CE | PENDING MANUAL VALIDATION |
| T06 | Full fill recorded once | One `FVG_FULL_FILL`, on the first bar reaching the far edge | PENDING MANUAL VALIDATION |
| T07 | Invalidation recorded independently | A wick through the far edge with a close back inside → FULL_FILL but **no** INVALIDATED. A later confirmed close beyond → one `FVG_INVALIDATED`; the inspector shows CLOSED | PENDING MANUAL VALIDATION |
| T08 | Mitigation and invalidation not confused | Policy = Full fill: the zone fades at full fill, the inspector still shows OPEN, and INVALIDATED comes later or never. Policy = Close through: the zone fades only at invalidation | PENDING MANUAL VALIDATION |
| T09 | Hidden FVGs still exist logically | Show FVGs OFF → `FVG records` unchanged; the inspector still shows records and milestones; events keep being logged | **PASS** (v0.3.1) |
| T10 | Show FVGs off/on does not change calculation history | Note the `Last events` list, the record counts and the inspector for n = 0…3 → toggle OFF and then ON → all identical | **PASS** (v0.3.1) |
| T11 | The visual-history limit doesn't affect logical state | Change Max faded 10 → 0, Max visible 8 → 1 and Hide older than → 20 → record counts, events and inspector unchanged; only the drawn and faded counts change | **PASS** (v0.3.1) |
| T12 | The engine-memory limit behaves intentionally | Memory = 10 on 1m, so it fills quickly → `FVG_DROPPED_MEMORY` appears; closed records are dropped before open ones (the reason text says which); the debug "Dropped by memory (open · closed)" counter rises; the dropped id is no longer inspectable and logs nothing more; no MITIGATED or other event is logged for the drop | **PASS** (v0.3.1) |
| T13 | Old visual zones are cleaned correctly | Max faded = 2 → only the 2 newest faded zones remain. Max visible = 2 → when a drawn zone is mitigated, the next older active zone appears (exact reconciliation). The object count in debug stays consistent | **PASS** (v0.3.1) |
| **Levels** | | | |
| T14 | PDH correct | Equals the high of the previous **1D** candle (Data Window on a 1D chart of the same symbol) | PENDING MANUAL VALIDATION |
| T15 | PDL correct | Equals the low of the previous 1D candle | PENDING MANUAL VALIDATION |
| T16 | PWH correct | Equals the high of the previous **1W** candle | PENDING MANUAL VALIDATION |
| T17 | PWL correct | Equals the low of the previous 1W candle | PENDING MANUAL VALIDATION |
| T18 | Previous-period levels stable after reload | Note the PDH/PDL/PWH/PWL values and the `LEVEL_SET` times → reload → identical. Only the line *start* may move to the period start, if the previous period is no longer fully loaded (visual, DEF-G3) | PENDING MANUAL VALIDATION |
| **Sessions** | | | |
| T19 | Asia session correct | `SESSION_START` on the 20:00 ET bar; developing lines dotted; `SESSION_END` on the 00:00 bar with the final H/L equal to the highest high and lowest low of the 20:00–23:59 bars | PENDING MANUAL VALIDATION |
| T20 | London session correct | Same check for 02:00–05:00 ET (END on the 05:00 bar) | PENDING MANUAL VALIDATION |
| T21 | NY AM session correct | Same check for 09:30–12:00 ET | PENDING MANUAL VALIDATION |
| T22 | NY PM session correct | Same check for 13:30–16:00 ET | PENDING MANUAL VALIDATION |
| T23 | Session state remains calculated when hidden | Untick Asia → its debug row still shows LIVE/DONE with H/L, and SESSION events are still logged | PENDING MANUAL VALIDATION |
| T24 | DST transition behaviour checked | Around **2026-11-01**, with the chart in ET, every window starts at the same ET time on both sides. With the chart in UTC, the starts shift by 1h | PENDING MANUAL VALIDATION |
| **Repaint, alerts** | | | |
| T25 | No future HTF leakage | On 1m, during the current day, PDH/PDL must equal **yesterday's** 1D candle, never today's developing high/low. In Bar Replay, step through a day: PDH never changes intraday and never shows a value that hasn't happened yet | PENDING MANUAL VALIDATION |
| T26 | Realtime confirmed events match post-reload history | 30 min live on 1m, Confirmed only ON. Copy the `Last events` list as it appears → reload → the same events with the same ids and times. Also run Bar Replay over 60 bars and compare with normal history | PENDING MANUAL VALIDATION |
| T27 | Alerts fire once per intended transition | Alert = "Any alert() function call". A zone touched on 5 bars → one first-touch alert. A bar with several events → one aggregated message at the close. A reload → no alerts | PENDING MANUAL VALIDATION |
| **Timeframes** | | | |
| T28 | NQ 1m works | No errors; FVGs, sessions and levels all present | PENDING MANUAL VALIDATION |
| T29 | NQ 3m works | Same as T28; session starts align to the 3m grid | PENDING MANUAL VALIDATION |
| T30 | NQ 5m works | Same as T28 | PENDING MANUAL VALIDATION |
| **Previous-period source** | | | |
| T31 | NQ1! previous-period source checked (**G-V1**) | See §G-V | PENDING MANUAL VALIDATION |
| T32 | Dated NQ contract source checked (**G-V2**) | See §G-V | PENDING MANUAL VALIDATION |
| **Limits** | | | |
| T33 | No object-limit errors | All display caps at their maximum, scroll the whole history → no orange object warning at the default caps, every type ≤ 500 at the maximum caps, no active zone vanishing unexplained | PENDING MANUAL VALIDATION |
| T34 | No request-limit errors | No "too many security calls" error (2 calls) | PENDING MANUAL VALIDATION |
| T35 | No runtime errors | No red error icon on 1m/3m/5m, on NQ1! and the dated contract, in Confirmed and Live mode | PENDING MANUAL VALIDATION |
| **Additional** | | | |
| T36 | Sunday/Monday transition (**G-V3**) | See §G-V | PENDING MANUAL VALIDATION |
| T37 | US DST transition (**G-V4**) | See §G-V | PENDING MANUAL VALIDATION |
| T38 | Chart session setting vs the Daily source (**G-V5**) | See §G-V | PENDING MANUAL VALIDATION |
| T39 | TR-average filter timing exact | Add the built-in *Average True Range* with **Smoothing = SMA** (this reproduces the TR average; IST does not use Wilder ATR), Length = 14 → its value **on candle 1** equals Data Window `TR average at candle 1 (t-2)` read on candle 3 | PENDING MANUAL VALIDATION |
| T40 | Ids stable when the history window moves | Note 5 FVG ids and 2 session ids → reload the next day, when the first loaded bar has moved → the same ids for the same zones | PENDING MANUAL VALIDATION |
| T41 | Origin versus confirmation never conflated | The inspector shows origin (candle 1) ≠ confirm (candle 3); `FVG_CREATED` time = candle 3. **By default the box starts at candle 3** (confirmation); "Draw zones from: Candle 1" starts it at candle 1 with no other change (same ids, events and inspector) | PENDING MANUAL VALIDATION |
| T42 | Preview is provisional only | Confirmed only OFF + Preview ON: the dashed "forming · provisional" box appears and vanishes intrabar, is never in `Last events`, never alerts, and the real zone appears only at the close | PENDING MANUAL VALIDATION |
| T43 | US/EU DST mismatch week | **2026-10-26 → 10-30:** London stays 02:00–05:00 ET by design. Timezone Europe/London with the window 0800-1100 follows UK time instead | PENDING MANUAL VALIDATION |
| T44 | Session end is not a sweep | Price trading through a completed session high produces no event and no visual change (Phase 2 scope) | PENDING MANUAL VALIDATION |
| T45 | Debug hidden when off | No table, no FVG text, no Data Window values; the object count is the same as with debug ON | PENDING MANUAL VALIDATION |
| T46 | Debug inspector correct | For an inspected FVG, verify every field by hand on the chart: bars, times, prices, milestones and policy status | PENDING MANUAL VALIDATION |
| T47 | Object warning not silent | Set the caps to push lines above 450 (sessions 10 + midpoint + levels 40 + CE) → the orange warning appears; at defaults it's absent | PENDING MANUAL VALIDATION |
| T48 | Minimal mode | No CE lines, labels, faded zones, session boxes or midpoints; logical counts unchanged | PENDING MANUAL VALIDATION |

---

## §G-V · Previous-period source validation

**Goal:** establish what TradingView's Daily and Weekly bars represent for NQ before calling anything "CME ETH". If they don't match the definition we want, **do not patch it**. Record the finding; the explicit session-based option in ARCHITECTURE §7.5 follows.

| ID | Procedure | Expected (to confirm or refute) |
|---|---|---|
| **G-V1** | NQ1!, 1m, Debug ON, maximum history. (a) For 3 recent days, compare the script's PDH/PDL with the high and low of the previous candle on a **1D** chart (Data Window). (b) Read `D source check` and `W source check`. (c) Read `Day · week start (ET)` | (a) equal. (b) 100% match. (c) day start `… 18:00`, week start `Sun … 18:00` |
| **G-V2** | Repeat G-V1 on the dated front contract (e.g. **NQZ2026**) | Same as G-V1 |
| **G-V3** | A Monday: PDH/PDL must equal **Friday's** 1D candle. The first Asia window of the week starts Sunday 20:00 ET. `LEVEL_SET` happens on Sunday's 18:00 ET bar | Confirm, or describe the actual boundary |
| **G-V4** | Dates on both sides of **2026-11-01** (and 2026-03-08 if loaded): the day start stays 18:00 ET; the D source check has no ✗ around the change | Confirm |
| **G-V5** | If the symbol offers alternative session settings (chart settings → Symbol → Session, e.g. regular versus extended / ETH versus RTH), switch them and repeat G-V1(a) and (b). Note whether the 1D candle and the script's values change, and whether the source check still matches | Document what changes |

**Results** (fill in after testing)

| Test | Symbol | Date tested | D check | W check | Day/week start | Result | Notes |
|---|---|---|---|---|---|---|---|
| G-V1 | NQ1! | | | | | PENDING | |
| G-V2 | NQZ2026 | | | | | PENDING | |
| G-V3 | NQ1! | | | | | PENDING | |
| G-V4 | NQ1! | | | | | PENDING | |
| G-V5 | NQ1! | | | | | PENDING | |

---

## Golden charts (captured at the Phase 1 freeze)

NQ1! on 1m and 5m, Debug ON, default settings, captured on these dates:

* 2026-03-06 → 03-10
* 2026-10-23 → 11-03
* one FOMC day
* one CPI day
* 2026-11-27

Store them in `docs/golden/` as `YYYY-MM-DD_tf_vX.Y.png`. Recapture after every change and compare.
