# IST — ICT Structure Toolkit · Architecture and Phase 1 specification

> **Status:** Phase 1 = **v0.3.2, frozen safety baseline** (git tag `PHASE1_BASELINE_v0.3.2`, copy in `releases/v0.3.2/`). Phase 2 (liquidity) is in development as **v0.4.1-dev** on branch `phase2/liquidity` (v0.4.0-dev tagged); its specification is **docs/LIQUIDITY.md** and its tests are **docs/TESTS_PHASE2.md**. This document remains the Phase 1 specification and the architecture both phases follow. **Not production-ready.**
>
> **Roles:**
> * Claude Code — primary implementation engineer
> * ChatGPT — architecture review and QA
> * Astra — occasional independent code audit
> * **TradingView — final authority on compilation and runtime**
>
> **Scope:** CME NQ futures. Execution on 1m, 3m and 5m; context from 15m to W. Pine Script v6. SMT is permanently excluded.

## Contents

0. Ground rules
1. Official architecture: 7 layers
2. Calculation versus visibility: rule, audit, input classification
3. State: records, logical history, visual history, budgets, replay-readiness
4. Event model
5. Timing and repaint contract (the six questions, per feature)
6. FVG thresholds: exact specification
7. Daily and weekly levels: source, claims, validation
8. Pine Script v6 limitations
9. Performance and object budget
10. Known limitations and open problems
11. Code organisation
12. Phase 1 plan and validation gate

Appendix A: Definitions

---

## 0 · Ground rules

1. **Bar close defines what is true.** By default, state changes once per bar, at the close. Intrabar updates exist only for monotonic facts.
2. **Origin and confirmation are different concepts.** `origin` is where a structure sits on the chart. `confirmation` is the first bar on which it could be known. State, events and alerts use only the confirmation. Drawings may start at the origin, but they never imply earlier knowledge (§5).
3. **Calculation never depends on visibility** (§2).
4. **Logical deletion is deliberate.** Only an explicit logical retention policy removes a structure, and it logs the removal (§3).
5. **Every concept has a numbered definition** (Appendix A), and the code cites it.
6. **No silent changes.** Every revision ships with CHANGES / WHY / REPAINT IMPACT / PERFORMANCE IMPACT / TESTS / KNOWN LIMITATIONS.
7. **Scope freeze.** No later-phase logic before the Phase 1 gate (§12).

---

## 1 · Official architecture: 7 layers

```
L1  MARKET DATA / TIME ENGINE   reference series, candle refs, period flags, HTF requests, session membership.
                                Runs every bar, unconditionally.
L2  DETECTION ENGINES           raw 3-candle FVG geometry, session boundary transitions, period rolls. Pure.
L4  CONTEXT / FILTERING         qualification of raw candidates (FVG size thresholds). Pure.
L3  STATE MANAGEMENT            records and lifecycles (FVG, sessions, levels). Gated by engineTick.
                                Reads no display input.
L5  EVENT BUS                   every transition becomes an Event, logged on history too.
L6  RENDERER                    reads state and writes only the drawing handles stored on records.
L7  ALERTS / DIAGNOSTICS        event → alert filter; debug table and inspector; Data Window; object warnings.
```

**Execution order per bar:** L1 → L2 → L4 → L3 (emitting into L5) → L6 → L7.

**How state reaches the renderer.** L3 never draws. On each bar it fills hand-off lists that L6 consumes:

* `lvlNewNow` and `lvlEndNow`: levels set or superseded on this bar
* `sesDirtyNow` and `sesEndNow`: sessions started, extended, finished or superseded on this bar
* `fvgDropNow`: FVG records released by engine memory

The FVG policy transitions of the bar are found by L6 itself (`metNow()`). Colours, styles, visibility, anchors, labels, fade versus remove, and every history cap are decided in L6.

**Static verification (v0.3.0).** A scripted scan of the source confirms that no [view] input, and no value derived from one, is referenced in L1–L5 or in the engine run (TESTS S-01).

---

## 2 · Calculation versus visibility

**Rule.** Engines compute and maintain state whether or not anything is shown. A visual toggle never disables detection or destroys state. Only explicitly named [calc] inputs change calculation.

### 2.1 Audit history

| # | Found in | Violation | Fix (version) |
|---|---|---|---|
| V1 | v0.1.0 | `bullFvg = fvgOn and …` | detection free of visibility (0.2.0) |
| V2 | v0.1.0 | session membership used the show toggle | hidden sessions tracked (0.2.0) |
| V3 | v0.1.0 | level toggles gated calculation | levels always computed (0.2.0) |
| V4 | v0.1.0 | events gated by alert toggles and realtime | all transitions logged (0.2.0) |
| V5 | v0.1.0 | mitigation removed records | milestones independent (0.2.0) |
| V6 | v0.1.0 | the visible cap evicted records | separate [view] and [calc] caps (0.2.0) |
| V7 | v0.1.0 | max age deleted records | [view] "hide older than" (0.2.0) |
| C1 | v0.2.0 | **invalidation deleted the record** | records are kept **closed** in memory (0.3.0) |
| C2 | v0.2.0 | **L3 functions took colour/style/visibility parameters and created lines** | L3 is draw-free; L6 decides everything visual (0.3.0) |
| C3 | v0.2.0 | **the "Start line at extreme" [view] option changed the state field `anchorTime`** | state stores the verified anchor or `na`; L6 applies the preference (0.3.0) |
| C4 | v0.2.0 | **ATR used `ta.atr` (RMA)**, whose value at a fixed bar depends on the first loaded bar | deterministic TR average, an SMA of the true range (0.3.0; renamed from "ATR" in 0.3.1, §6) |
| C5 | v0.2.0 | **sequential ids** changed whenever the loaded history moved (i.e. every reload as time passes) | ids are times (0.3.0) |
| C6 | v0.2.0 | renderer queries "active now" only | `activeAt(z, b)` takes a bar parameter, so replay stays possible (0.3.0) |

### 2.2 Input classification

| Tag | Inputs |
|---|---|
| **[calc]** | Confirmed only · FVG min ticks · × TR average · × avg range · TR-average/range length · Engine memory · Session timezone · Session windows |
| **[view]** | Minimal mode · label size · right extension · Show FVGs · colours · Mitigation policy (display) · Mitigated zones · Draw zones from · Max visible · Max faded · Hide older than · Extend · CE line · Shrink · Labels · Preview · all LEVELS inputs · session show toggles, names, colours, lines, developing, midpoint, box, labels, history · Debug mode · Inspect FVG |
| **[alert]** | Alert timing · per-event alert toggles |

* **Mitigation policy** is display/event policy. It decides when a zone stops being drawn as active. It never changes which milestones are recorded.
* **Validity guards (not visibility):**
  * daily levels need an intraday chart
  * weekly levels need an intraday or daily chart
  * sessions and the midnight open need a chart timeframe ≤ 1H

---

## 3 · State: records, logical history, visual history, budgets

### 3.1 Records

**FVG (`Fvg`)**

| Field | Meaning |
|---|---|
| `id` | the confirmation time (candle 3 open time). Unique per direction (one bar can't create both). **Stable across reloads**, even when the first loaded bar moves. In Phase 1 that is enough because every record shares the chart's symbol and timeframe. **Future requirement (§10.10):** the full identity is *symbol + timeframe + direction + confirmation time* |
| `isBull`, `tf` | direction and chart timeframe |
| `originBar`, `originTime` | candle 1 (t-2): where the imbalance sits |
| `confirmBar`, `confirmTime` | candle 3 (t): the record is created at its **close**. `confirmTime` is the open time of that bar |
| `top`, `bottom`, `mid` | zone and CE |
| `touchBar/Time`, `ceBar/Time`, `fullBar/Time`, `invBar/Time` | independent milestones, `na` until reached, each stamped once |
| `extreme` | deepest penetration so far (current value only) |
| `sizeTra` | gap / TR average at creation |
| `thrTick`, `thrTra`, `thrRng` | the three size thresholds in force at creation (audit; the inspector re-checks the record against them) |
| `zone`, `ce` | L6 drawing handles; `na` when not drawn |

The following are **derived, never stored**, so they cannot drift:

* `age()`
* `fillPct()`
* `policyBar()` and `policyTime()`: the milestone selected by the display policy
* `activeAt(b)`: confirmed by bar b and not yet past its policy milestone at b

**Session (`SessionRange`)**

* `id`: the start time, stable across reloads
* `slot`, `name`, `complete`
* `startBar/Time`
* `endBar/Time`: the last bar inside the window
* `hi`/`lo`: `RefLevel`s. They are `developing` until the end; `anchorTime` is the bar that printed the extreme, and `knownTime` is when the value became final
* drawing handles

**Level (`RefLevel`)**

* `kind`, `tag`, `isHigh`, `price`
* `anchorTime`: the verified extreme bar, or `na`
* `knownTime`, `endTime`
* drawing handles

### 3.2 Logical versus visual history

| Container | Kind | Removed only by |
|---|---|---|
| `bullFvgs`, `bearFvgs` | **logical**: open and closed records, oldest first | **engine memory** (§3.3), logged as `FVG_DROPPED_MEMORY` |
| `liveSes[4]`, `liveLvl[6]` | **logical**: the current instance per window or kind | supersession by the next instance (lifecycle end, not display) |
| `evLog` | **logical** (audit): last 40 events | ring buffer |
| `fadedFvg` | visual | the "Max faded zones" cap: erases drawings only |
| `histSes`, `histLvl` | visual | per-slot and total history caps: erase drawings only |
| active FVG drawings | visual | last-bar reconciliation: Show FVGs, max visible, hide older than |

Visibility can never remove a record. A record with no drawing is still advanced, logged and inspectable (debug inspector).

### 3.3 Logical retention policy (FVG engine memory, [calc])

* **Budget:** `Engine memory` = **50 records per direction** by default (range 10–200), counting open and closed records together.
* **When a new record exceeds the budget**, exactly one record of that direction is released:
  1. the **oldest closed** (invalidated) record, which loses only history, otherwise
  2. the **oldest open** record, which loses lifecycle tracking
* Each release logs `FVG_DROPPED_MEMORY` with the reason ("closed record" or "open record · lifecycle tracking stopped"). The debug table counts releases separately for open and closed records.
* **A drop is neither mitigation nor expiry.** Phase 1 has no logical expiry; "Hide zones older than" is visual only.
* **Limitation:** lifecycle analysis is complete only **inside the memory window**. Nothing older than the window is available, and a dropped open record never logs later milestones. Which records are in memory near the start of loaded history can differ between loads with different first bars (§10).

### 3.4 Replay / historical-inspection readiness (not implemented)

A future mode that shows "what was active at bar b" needs nothing beyond what is now stored:

* **Activity at bar b:** `activeAt(z, b)` = `confirmBar ≤ b` and the policy milestone is not reached by b.
* **Drawing at bar b:** the milestone **times** are stored, so a past state can be drawn without looking up `time[n]` thousands of bars back.
* **Renderer:** `f_renderActive(records, b)` already takes the reference bar. Phase 1 calls it with `bar_index` on the last bar only.

Not reconstructible today:

* fill % at a past bar (only the current `extreme` is kept)
* records outside the memory window
* past sessions and levels, which leave logical state when superseded; they would need a small logical archive

All three are additive changes, not redesigns.

### 3.5 Visual budget

| | Default | Maximum | Notes |
|---|---|---|---|
| Active FVG boxes | 8 + 8 | 30 + 30 | newest unmitigated per side |
| Faded FVG boxes | 10 | 60 | |
| **FVG boxes total** | **26** (+1 preview) | 121 | **within the requested 25–35** |
| FVG CE lines | 26 | 120 | off in Minimal mode |
| Level lines | 6 live + 4 history | 6 + 40 | |
| Session lines | 4 live × 2 + 4 × 3 past × 2 = 32 | 4 × 11 × 3 = 132 | with midpoint |

**Why 26 by default.**

* 8 active zones per side covers the zones near price on 1m to 5m without clutter.
* 10 faded zones give recent context.
* Raising the active count adds boxes far from price, which hurts readability more than it helps.

**At maximum settings:** 121 boxes and about 300 lines. That stays under 500, with room left for later phases. If any object type exceeds **450**, a normal-mode warning appears, so the limit is never hit silently.

---

## 4 · Event model

```pine
type Event
    int kind; int dir; int sid; int originBar; int eventBar; int eventTime; float price; string reason
```

| Event | When | `sid` | price | reason |
|---|---|---|---|---|
| `FVG_CREATED` BULL/BEAR | candle 3 closes and qualifies | FVG id | CE | `bottom–top` |
| `FVG_FIRST_TOUCH` | first bar with low ≤ top (bull) / high ≥ bottom (bear) | FVG id | near edge | rule |
| `FVG_CE_TOUCH` | first bar reaching CE | FVG id | CE | rule |
| `FVG_FULL_FILL` | first bar reaching the far edge | FVG id | far edge | rule |
| `FVG_INVALIDATED` | first **confirmed** close beyond the far edge | FVG id | close | rule |
| `FVG_DROPPED_MEMORY` | released by engine memory | FVG id | CE | open or closed record |
| `SESSION_START` | first bar of a window | session id | — | name |
| `SESSION_END` | first bar outside the window | session id | — | name + final H/L |
| `LEVEL_SET` | PDH/PDL/PWH/PWL/DO/MO take a new value | kind | value | tag |

* **Exactly once.** Each event is tied to one field changing from `na` to a value, which can't happen twice.
* **Logged on every bar,** history included.
* **Alerts:** FVG created (bull, bear), first touch, CE touch, full fill and invalidated. Each is toggled separately; the toggles never affect logging.
* **Format:** `NQ1! 1 · FVG_CREATED BULL id=2026-10-27 09:41 px=21001.50 · 21000.25–21002.75`

---

## 5 · Timing and repaint contract

### 5.1 Acceptance target

Assume identical chart data and identical inputs. Then **confirmed events must not:**

* appear earlier after reload
* disappear after reload
* change their confirmation timestamp after reload
* change state without new market data

The **declared exceptions,** each one testable:

1. The first `len + 1` bars of loaded history (filter warm-up, §6).
2. Records outside the engine-memory window (§3.3).
3. The anchor start of a period line, which is visual only (DEF-G3).

### 5.2 The six questions, per feature (Confirmed mode, the default)

| Feature | 1 · Physically occurs | 2 · First knowable | 3 · Displayed | 4 · Alert may fire | 5 · Visual origin earlier? | 6 · Can change after reload? |
|---|---|---|---|---|---|---|
| FVG created | gap geometry fixed when candle 3 closes | **close of t** (candle 3) | from close of t | close of t | **No, by default:** the box starts at candle 3, the confirmation (v0.3.1 default). Optional "Draw zones from: Candle 1" starts it 2 bars earlier, at the origin | No (exceptions 1 and 2) |
| First touch / CE / full fill | intrabar on bar k > t | close of k (Live mode: the tick it happens) | close of k (tint, debug flags) | close of k (intrabar mode: at the tick, experimental) | No | No |
| Invalidation | close of bar k | close of k | close of k | close of k | No | No |
| "Mitigated" (display policy) | = the chosen milestone | same as that milestone | the zone fades or disappears at that bar | via that milestone's alert | the faded box spans origin → policy bar | No |
| Dropped by memory | engine decision at a creation bar | close of that bar | an active view disappears | never | — | Near the start of history, depends on the first loaded bar |
| Forming preview | developing candle 3 | **not knowable**: provisional | intrabar, Live mode only, dashed, "provisional" | never | as configured | **Yes: it is designed to change and vanish** |
| Session start | first bar in the window | that bar | from that bar (developing: dotted) | none in Phase 1 | No | No |
| Session developing H/L | each new extreme bar | close of that bar | updated as they move | none | line anchored at the extreme bar | the final values don't change; developing values change by design |
| Session end (final H/L) | last bar inside the window closes | **open of the first bar outside** | lines turn solid from that bar | none | yes, the lines start at their extreme bars inside the window | No |
| PDH/PDL, PWH/PWL | during the previous TradingView day or week | first chart bar of the new period | from that bar | none in Phase 1 | **Yes, by default:** the line starts at the bar that printed the extreme (previous period), when verifiable | value: No. Anchor: may fall back to the period start if the previous period is no longer fully loaded |
| Day open / Midnight open | first bar of the day / of 00:00 | that bar's open | from that bar | none | No | No |
| D/W source check | — | at each complete period roll | debug only | none | — | the counts depend on how many complete periods are loaded |

**Live mode (Confirmed only OFF).** Only column 2 and column 3 for wick milestones move earlier, to the tick. Creation and invalidation still need the close.

**Never implying earlier knowledge.** Events and alerts carry the confirmation bar, and the debug inspector shows `origin → confirm` explicitly. Wherever a drawing starts before confirmation, the table above says so, and there is a setting to switch it off where it matters (FVG boxes, period lines).

---

## 6 · FVG thresholds: exact specification

**Notation:**

* t = candle 3 (the confirmation bar), t−1 = candle 2, t−2 = candle 1.
* `len` = "TR-average / avg-range length" (default 14).
* `TRᵢ = max(highᵢ − lowᵢ, |highᵢ − closeᵢ₋₁|, |lowᵢ − closeᵢ₋₁|)`. On the first loaded bar, TR = high − low (`ta.tr(true)`).

| Threshold | Formula | Pine | Source bars | Value known at | Can change later? |
|---|---|---|---|---|---|
| Gap (bull) | `low_t − high_{t−2}` | `low - high[2]` | t−2, t | close of t | No |
| Gap (bear) | `low_{t−2} − high_t` | `low[2] - high` | t−2, t | close of t | No |
| Min ticks | `gap ≥ n·mintick − 0.01·mintick` | `fvgMinTicks * syminfo.mintick - EPS` | none | constant | No. The 0.01-tick tolerance only absorbs float rounding; prices are on the tick grid |
| × TR average | `gap ≥ k_TR · TRA_{t−2}`, where `TRA_{t−2} = (1/len)·Σ_{i=t−1−len}^{t−2} TRᵢ` | `ta.sma(ta.tr(true), len)[2]` | bars t−1−len … t−2, plus `close_{t−2−len}` via the first TR | **close of t−2** | **No.** It is a finite window of closed bars, identical after any reload once bar t−2−len exists (warm-up below) |
| × avg range | `gap ≥ k_R · AR_{t−2}`, where `AR_{t−2} = (1/len)·Σ_{i=t−1−len}^{t−2}(highᵢ − lowᵢ)` | `ta.sma(high - low, len)[2]` | bars t−1−len … t−2 | **close of t−2** | No |

* **One required size, shared by both directions (v0.3.2 makes this explicit):** `requiredGap = max(tickReq, traReq, rngReq)`, and a candidate qualifies iff `rawGap ≥ requiredGap`.
  * `tickReq = minTicks · mintick`.
  * `traReq = k_TR · TRA_{t−2}`, or 0 when k_TR = 0.
  * `rngReq = k_R · AR_{t−2}`, or 0 when k_R = 0.
  * A reference that is still warming up (`na`) rejects.
  * The code tests the three terms with AND, which is identical to the max form. Only the tick term carries the 0.01-tick float tolerance.
  * `rawGap`, `tickReq`, `traReq`, `rngReq`, `reqGap` and `gapPass` are named series in L4. Both `bullCand` and `bearCand` derive from the same `gapPass`.
  * Every record stores the three thresholds at birth. Debug shows all of them (Data Window per bar; the inspector per record).
* **Why the window ends at t−2.** Candle 2 is normally the impulsive candle that creates the gap. A reference that included it (a TR average at t−1 or t) would rise with the very move being measured, so the most decisive imbalances would face the highest bar. That is self-referencing. With the window ending at t−2, the gap is compared with volatility before the imbalance began. The reference is final two bars before confirmation, so it cannot change during the confirmation bar.
* **Accepted bias.** At a regime change (e.g. 09:30), the first gaps are compared with quieter pre-open volatility, so they pass more easily.
* **Deterministic TR average — deliberately *not* Wilder ATR (approved, v0.3.1).** Wilder ATR (`ta.atr`) is an RMA, and an RMA depends on every bar since the first loaded bar. On a 1m chart the first loaded bar moves forward with every reload as time passes, so RMA values at a fixed historical bar drift slightly. A gap near the threshold could then qualify on one load and not on the next. The finite window removes that.
  * Because the implementation is not Wilder ATR, it is called **"TR average"** in the UI, the code and these docs, never "ATR".
  * Default length 14. No Wilder option is offered.
  * To read the same value in TradingView, add the built-in *Average True Range* indicator with **Smoothing = SMA** and **Length = len**, and read it on candle 1.
* **Warm-up and history independence.**
  * `TRA` is defined from bar index `len−1` (0-based), so with k_TR > 0 the first possible FVG is at t = len+1.
  * Windows that include the first loaded bar use its approximate TR, so values are history-independent only from t ≥ len+2. This is exception 1 in §5.1.
* **Future optional filters.** A middle-candle direction filter, or others, would enter at the single L4 extension point (the `gapPass` expression) as a separate [calc] **filter**, OFF by default, never part of DEF-A1. Nothing like that exists now.

---

## 7 · Daily and weekly levels

### 7.1 Implementation and why it doesn't leak

```pine
[pdH, pdL] = request.security(syminfo.tickerid, "1D", [high[1], low[1]], lookahead = barmerge.lookahead_on)
[pwH, pwL] = request.security(syminfo.tickerid, "1W", [high[1], low[1]], lookahead = barmerge.lookahead_on)
```

* `high[1]` is evaluated inside the daily context: the high of the **previous**, already closed daily bar.
* `lookahead_on` only aligns that final value onto chart bars from the first chart bar of the new daily bar. Historical and realtime bars both receive yesterday's completed values. Neither ever receives today's developing values.
* Without `[1]`, the same call would leak today's final high into today's early bars. That form is never used.
* Levels roll on `timeframe.change("1D")`/`("1W")`. The first loaded bar seeds them, so a 1m chart without the start of the week still shows PWH/PWL.

### 7.2 What we claim

* **The level is the high/low of the previous TradingView Daily (Weekly) bar for the chart's symbol and session settings.** That is all we claim.
* **We expect**, but have **not verified**, that for NQ the TradingView day runs 17:00–16:00 CT = **18:00–17:00 ET**, stable across DST (Chicago and New York shift together), with the week starting Sunday 18:00 ET.
* **Until G-V1…G-V5 pass, nothing in this project is labelled "CME ETH PDH/PDL".** The labels say PDH/PDL.
* Unknowns that the tests target:
  * continuous (NQ1!) versus dated contracts
  * back-adjustment
  * holidays and early closes
  * whether chart session settings change the Daily source
  * how the feed builds daily bars
  * "settlement as close", which affects the close only; IST reads high and low only

### 7.3 Built-in check (DEF-G6)

For every **complete** period, meaning one whose start was observed on the chart, the engine compares the chart-aggregated high and low between consecutive `timeframe.change` boundaries with the `request.security` values. A difference of half a tick or more counts as a mismatch.

Debug shows:

* `D source check` / `W source check`: matches out of the total, plus the date of the last mismatch
* `Day · week start (ET)`: the weekday and time of the latest boundaries

### 7.4 Manual tests

See `TESTS.md` §G-V. The tests are:

* G-V1: NQ1! against the previous Daily candle
* G-V2: a dated contract
* G-V3: the Sunday/Monday transition
* G-V4: a US DST transition
* G-V5: the chart session setting

Results go into the results table there.

### 7.5 If the Daily bar is not the definition we want

**We will not patch it with assumptions.** The finding is flagged, and an explicit session-based calculation is proposed instead:

* a [calc] "Day definition": TradingView Daily (current), CME ETH 18:00–17:00 ET computed from chart bars over an explicit window, or RTH 09:30–16:00
* `request.security` stays as the fallback when the window isn't fully loaded

The chart-side aggregation already exists (it is the validation tracker). Levels already flow through `f_roll`, whatever the source.

---

## 8 · Pine Script v6 limitations

| Limitation | Consequence |
|---|---|
| 500 lines / boxes / labels; past that, the **oldest are deleted silently** | Hard budgets (§3.5) and a warning above 450 |
| `request.*` calls (40 per script) | 2 used |
| Loaded history is plan-dependent | D/W values come from requests; memory-window and warm-up exceptions apply |
| Per-bar loop and total execution time | Loops only over bounded record arrays |
| No intrabar sequence on history | Fixed same-bar order (DEF-A7) |
| Realtime rollback of `var` state (`varip` exempt) | Bar-close default; `varip` only in experimental alert de-duplication |
| `lookahead_on` leaks without `[1]` | Only `expr[1]` + `lookahead_on` |
| `xloc.bar_index` can't go more than 500 bars into the future | `xloc.bar_time` |
| A function can't assign globals | Counters are incremented at global scope; ids come from time |
| No unit-test framework | Static source checks here; runtime tests in TradingView (`TESTS.md`) |

---

## 9 · Performance

* **Requests:** 2.
* **Per bar:**
  * one pass over at most 2 × memory records (100 by default) to advance open zones, plus `na` checks on closed ones
  * one pass in L6 to find policy transitions
  * 4 session steps and up to 6 level checks
* **Drawings:**
  * FVG active views: created or updated on the last bar only
  * faded views: created at their policy bar
  * levels and sessions: created or updated only on bars where their state changed
* **Strings:** short reason codes are built on history. Messages are built only in realtime (alerts) or on the last bar (debug).
* **Profiling** with the Pine Profiler is part of step 1.7 (§12).

---

## 10 · Known limitations and open problems

1. **Memory window.** See §3.3: history is complete only inside it, and near the start of loaded history the set of retained records can depend on the first loaded bar.
2. **Warm-up.** The first `len + 1` bars of history have no TR-average-filtered FVGs, and their reference values can differ between loads.
3. **Same-bar ambiguity.** Fixed order only. For example, touch and invalidation on one bar.
4. **The D/W source is unverified** (§7).
5. **Live mode** depends on TradingView's rollback of object fields (NR-04). Confirmed mode is immune.
6. **Ids are minute-resolution times in display.** Numeric ids are exact. On sub-minute charts the displayed id can repeat. Sub-minute charts are out of scope.
7. **Visual history while scrolling.** You see faded (mitigated) zones and the latest active ones, not zones that were active at the scrolled-to moment. Replay mode is designed for but not built (§3.4).
8. **Session conventions and US/EU DST-mismatch weeks** are surprising but by design.
9. **Back-adjusted continuous contracts** shift historical prices.
10. **FVG identity: a future requirement, not changed in Phase 1.** Today, identity = direction (array) + `id` (confirmation time). That is unique only because every Phase 1 record comes from the chart's symbol and timeframe.
    * Once HTF FVGs (Phase 4) coexist with chart-timeframe FVGs, a 15m and a 1m zone can share a confirmation time.
    * The identity must then be **symbol + timeframe + direction + confirmation time**, carried in events (`sid` plus `tf`/symbol) and alert de-duplication keys.
    * The record already stores `tf`. Adding the symbol and composite keys is an additive change at Phase 4.

---

## 11 · Code organisation

`src/IST.pine` is one script with fixed sections:

ENUMS → INPUTS (tagged) → CONSTANTS → TYPES → STATE → **L1** → **L2+L4** → **L5** → **L3** → **L6 functions** → ENGINE RUN → **L6 run** → **L7 alerts** → **L7 diagnostics**.

**Conventions**

* Functions use `f_`. Methods are verbs.
* Constants are `UPPER_CASE`.
* Comments state *why* and cite `DEF-xx`.

---

## 12 · Phase 1 plan and validation gate

| Step | Work | Done when |
|---|---|---|
| 1.0 | Compile v0.3.1 | 0 errors, 0 warnings; messages reported verbatim |
| 1.1 | Static source checks | S-01…S-04 PASS (done here) |
| 1.2 | Runtime tests T01–T48 (`TESTS.md`) | every test PASS, or FAIL with a fix |
| 1.3 | D/W source validation G-V1…G-V5 | results recorded; the definition decided (§7.5) |
| 1.4 | QA review by ChatGPT; optional audit by Astra; Pine Profiler run; golden charts | findings resolved |
| **Gate** | **Freeze v1.0.0. Only then Phase 2** | your explicit approval |

**Decisions (v0.3.1):**

* **TR average (SMA of the true range): approved.** It is named "TR average", never "ATR". Default length 14. No Wilder option.
* **"Draw zones from" default: Candle 3 (confirmation)**, which sets the default for new instances of the indicator. Candle 1 (origin) stays optional.
* **Previous-day definition: UNRESOLVED.** Phase 1 validation uses the TradingView D/W confirmed source. G-V1…G-V5 then decide between keeping it and building an explicit CME ETH trading-day engine (§7.5). It must not be labelled "CME ETH" before then.

---

## Appendix A · Definitions

### Phase 1, implemented exactly

**Module A — Fair value gaps**

* **DEF-A1 Raw geometry** on candle 3 (bar t):
  * **Bullish** if `low[t] > high[t-2]`, giving the zone `[high[t-2], low[t]]`.
  * **Bearish** if `high[t] < low[t-2]`, giving the zone `[high[t], low[t-2]]`.
  * The comparison is strict. No candle-direction or displacement condition is part of the definition.
* **DEF-A2 Qualification** ([calc]). All of the §6 thresholds must pass.
* **DEF-A3 Confirmation.** The record is created at the close of t, with `id = confirmTime` and origin = candle 1. Milestone tracking starts at t+1.
* **DEF-A4 Milestones.** Independent; each is stamped once, with bar and time. Shown for bullish; bearish is mirrored.
  * **first touch:** `low ≤ top`
  * **CE touch:** `low ≤ (top+bottom)/2`
  * **full fill:** `low ≤ bottom`
  * **invalidation:** `close < bottom`, on a confirmed bar
* **DEF-A5 Mitigation policy** ([view/alert]). First touch, CE, full fill (default) or close through (= invalidation). It decides only the display. Recording continues.
* **DEF-A6 Retention.** A record is open until invalidated, then closed. Both stay in memory. Only the engine-memory policy (§3.3) removes records, oldest closed first, and each removal logs `FVG_DROPPED_MEMORY`.
* **DEF-A7 Same bar.** Several milestones on one bar are all stamped on that bar and emitted in rule order: touch → CE → full → invalidation.
* **DEF-A8 Preview.** Provisional, Live mode only, never stored, logged, alerted or promoted.

**Module F — Sessions**

* **DEF-F1 Membership.** The bar's open time falls in `HHMM-HHMM` in the IANA timezone, on every weekday. Windows may cross midnight.
* **DEF-F2 Start.** The first bar in the window whose previous bar is outside it. Never the first loaded bar. `id` = start time. Logs `SESSION_START`.
* **DEF-F3 Developing.** The running max and min, anchored at the bars that printed them.
* **DEF-F4 End.** On the first bar outside the window, the values become final and `SESSION_END` is logged with the final high and low. `endBar` is the last bar inside the window.
* **DEF-F5 Hidden.** A hidden session is tracked identically.
* **DEF-F6 Supersession.** When the same window starts again, the instance leaves logical state, and its drawings move to the capped visual history.

**Module G — Levels**

* **DEF-G1 Period** = TradingView's Daily or Weekly bar for the symbol (§7.2).
* **DEF-G2 Value.** The previous **completed** bar's high and low, `expr[1]` with `lookahead_on`, known from the first chart bar of the new period.
* **DEF-G3 Anchor.** State stores the bar that printed the extreme when the chart's tracked extreme equals the HTF value (within half a tick); otherwise `na`. L6 starts the line there when "Start line at the extreme's bar" is ON, otherwise at `knownTime`.
* **DEF-G4 Opens.**
  * **Day open** is the open of the first chart bar of the TradingView day.
  * **Midnight open** is the open of the first bar at hour 00 on a new date in the session timezone.
* **DEF-G5 Seeding.** The first loaded bar seeds PDH/PDL and PWH/PWL; the day open is not seeded.
* **DEF-G6 Source check.** As in §7.3.

### Later phases (proposals; unchanged; not implemented)

* **DEF-D Liquidity (Phase 2).** *Superseded by DEF-L1…L7 in docs/LIQUIDITY.md (v0.4.0-dev).* Differences from this proposal: W = 1 (classification on the taking bar's close), no buffer; the window is a documented extension point.
* **DEF-E EQH/EQL (Phase 2).** *Superseded by DEF-L5 in docs/LIQUIDITY.md.* Differences from this proposal: tick tolerance only; no distance limit; the intact-pool rule; confirmed at the member that reaches the minimum touches.
* **DEF-H Displacement (Phase 3).** body/TR average, body/range, close location, range/average range. STRICT, BALANCED and AGGRESSIVE presets.
* **DEF-I CISD (Phase 3).** The delivery-origin definition: a close beyond the open of the first candle of the opposing run. Fires only against the delivery state; once per leg.
* **DEF-C IFVG (Phase 4).** Wick, close or body invalidation of a retained record. Phase 1's `invBar` is the CLOSE mode, and closed records are kept for this.
* **DEF-B HTF FVG (Phase 4).** DEF-A evaluated inside the HTF request with offset [1]; de-duplicated by HTF c3 time; lifecycle on chart bars.
* **DEF-J P/D, DEF-Q Quality (Phases 4–5).** Q is a checklist score frozen at birth, shown as "Q x/100", never as a probability.
