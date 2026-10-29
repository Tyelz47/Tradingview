# HTF Fair Value Gaps · Module B (DEF-B0 … B6)

**Status: APPROVED definition (user, 2026-10-29), implemented in `src/IST.pine` v0.6.0-dev. EXPERIMENTAL, not frozen.**
* Reference model: `validation/models/htf_fvg.py`. Design history and alternatives: `docs/HTF_FVG_DESIGN.md`.
* Frozen only after real TradingView Pine ↔ Oracle parity (HTF-L12, `docs/TESTS_HTF.md`) gives **0 DIFFERENCE**.
* Module B sits beside the frozen Phase 1 FVG engine (Module A). It changes nothing in Module A's calculation, events or alerts.

## Decisions (user, 2026-10-29)

| | decision |
|---|---|
| D1 | No hiding of contained lower-timeframe zones. Records stay independent; overlap is a rendering question only |
| D2 | The lifecycle starts on the chart bar where the zone becomes KNOWN. Touch / CE / full fill count from that bar; nothing is stamped retroactively |
| D3 | Seeds: the 3 newest still-open zones per direction per timeframe, from the HTF context |
| D4 | The frozen Phase 1 FVG definition and thresholds (DEF-A1, DEF-A2), on each timeframe's own candles and TR average |
| D5 | Invalidation only by a close of the zone's OWN timeframe. A 1m close never invalidates a 4H / 1D / 1W zone |
| D6 | Per timeframe, the nearest open zone above and the nearest open zone below price: at most 12 boxes. Logical memory is independent |
| D7 | Neutral grey. The hierarchy is fill and border opacity only: 15m / 30m light, 1H / 4H medium, 1D / 1W strongest |
| D8 | The box's visual origin is HTF candle 1, but the zone is neither visible nor logically active before candle 3 closes |
| D9 | Phase 1 `Show FVGs` default OFF (display only), recorded in `validation/baselines/PHASE1_DEVIATIONS.md` |
| D10 | Label `15m Fair Value Gap` … `1W Fair Value Gap`; `15m FVG` only as a Developer option |

## DEF-B0 · Data (non-repainting)

* Six timeframes: `15`, `30`, `60`, `240`, `D`, `W`. A timeframe at or below the chart timeframe is **inactive** (its request reads the chart timeframe and is ignored). On 1m all six run; on 15m, 30m … 1W.
* One `request.security(syminfo.tickerid, TF, f_htfPack(), lookahead = barmerge.lookahead_on)` per timeframe.
* `f_htfPack()` runs inside the HTF context and reads **every price and time series at `[1]` or older**: candle 3 = `[1]` (the last completed HTF bar), candle 1 = `[3]`. Its result is final for the whole next HTF bar. `lookahead_on` only aligns it to that bar's start, exactly like PDH / PDL (DEF-G2). **The unfinished HTF candle is never read.** ST-03 enforces it (no bare series, no `[0]`, `ta.tr` only shifted).
* It returns the last completed HTF bar (open time, O, H, L, C, TR average, average range), the DEF-B1 zone whose candle 3 that bar is, the seeds (DEF-B2) and, for the parity snapshot, the last three completed HTF bars.

## DEF-B1 · Creation

On the three last completed HTF bars (candles 1, 2, 3):
* bullish if `low(c3) > high(c1)`: zone `[high(c1), low(c3)]`; bearish if `high(c3) < low(c1)`: zone `[high(c3), low(c1)]`;
* qualified by DEF-A2 with the Phase 1 inputs: gap ≥ max(min ticks × mintick, k_TR × TR average, k_range × average range), the references taken **at candle 1** on that timeframe (TR average = SMA of the true range, never Wilder ATR).
* Identity = **timeframe + direction + candle-3 open time**. Records of different timeframes are never merged.
* Event `HTF_FVG_CREATED` on the chart bar where it becomes known.

## Timing

For timeframe P, candles k−2, k−1, k (candle 3 = k, open o_k, close c_k):

| moment | value |
|---|---|
| box origin (D8) | candle 1's open time (k−2) |
| HTF confirmation | c_k, candle 3's close |
| chart bar where it becomes **known** | the first chart bar whose open time ≥ c_k (the first chart bar of HTF period k+1) |
| state change, Confirmed mode | at that bar's close (the bar's own wick already counts, D2) |
| before c_k | nothing: no record, no event, no drawing |

Examples, NQ1! 1m, New York:
* 15m candles 09:30 / 09:45 / 10:00: known on the 10:15 chart bar; the box starts at 09:30. Id = (15m, dir, 10:00).
* 1H candles 08:00 / 09:00 / 10:00: known on the 11:00 chart bar; the box starts at 08:00.

**D8 note.** The box is drawn back to candle 1 only once the zone is known. On a chart replayed bar by bar, the zone (and its box) does not exist on any bar before the known bar. Drawing from candle 1 is a visual convention, not a claim that the zone existed there.

**Session alignment.** The HTF candles are TradingView's own (CME: 4H at 18 / 22 / 02 / 06 / 10 / 14 ET, the day from 18:00 ET, the week from Sunday 18:00 ET). The oracle's aggregator uses the same rule; parity check (a) verifies it against the candles Pine received.

## DEF-B2 · Seeds (D3)

* Inside `f_htfPack()`, a small engine holds the zones still open at HTF resolution (at most 20 per direction): a zone leaves it when a later HTF bar fully fills it (wick to the far edge) or closes beyond it.
* On the **seed point** (the first chart bar where a completed HTF bar exists, normally the first loaded bar), the 3 newest of them per direction are registered: event `HTF_FVG_SEEDED`, flagged *seeded*. Nothing else completes on that bar.
* A seed already touched or already through its CE before the chart history keeps that as state (`preTouch`, `preCe`). **No retroactive FIRST_TOUCH / CE_TOUCH is emitted.**

## DEF-B3 · First touch · CE · full fill

On every chart bar from the known bar on, for every zone not invalidated, on the chart bar's wick (bullish: low; bearish: high, mirrored):
* first touch: the wick reaches the near edge; CE: it reaches the midpoint; full fill: it reaches the far edge;
* each stamped once, in that order on one bar; events `HTF_FVG_FIRST_TOUCH`, `HTF_FVG_CE_TOUCH`, `HTF_FVG_FULL_FILL`.

## DEF-B4 · Invalidation (D5)

* Only when an HTF bar of the zone's own timeframe **completes after candle 3 and closed beyond the far edge** (bullish: close < bottom). Known on the first chart bar of the next HTF period: event `HTF_FVG_INVALIDATED`, price = that close.
* A chart-bar close never invalidates an HTF zone.
* Per completed HTF bar, invalidation runs before the new zone is created, then the milestones of the chart bar.

## DEF-B5 · Display (D1, D6–D10)

* Shown: zones not fully filled and not invalidated (untouched or partially filled).
* Per timeframe, the nearest shown zone **above** and **below** the last close (above / below by the zone's midpoint; distance from the close to its near edge, 0 inside; ties → the newest). At most 2 per timeframe, ≤ 12 boxes.
* Drawn 1W first and 15m last, so a nested lower-timeframe zone stays visible over its parent. Nothing is merged or hidden.
* Box: from candle 1's open to the current bar + right offset (`xloc.bar_time`); fill and border grey `#9598A1`, fill transparency 94 / 91 / 88 and border transparency 85 / 70 / 55 for 15m–30m / 1H–4H / 1D–1W.
* Label: the box text, bottom-right inside the zone, tiny, grey `#787B86` at 30 % transparency: `15m Fair Value Gap` … `1W Fair Value Gap` (Developer: `15m FVG`).
* Rebuilt from state on the last bar only. The per-timeframe switches and "Show HTF FVGs" are **[view]**: every active timeframe is always computed.

## DEF-B6 · Memory

* 20 records per timeframe (both directions). Over the limit, the oldest fully filled or invalidated record goes first, else the oldest one. Each removal logs `HTF_FVG_DROPPED_MEMORY`.

## Reload consistency

* Every input to a decision is a completed HTF bar or a closed chart bar, and ids are times. Reloading the chart or moving its first bar changes nothing for a zone known inside both histories.
* A zone known before the new first bar comes back as a seed with the same id, geometry and touch / CE state (at HTF resolution).
* Tested: `validation/fuzz/test_htf_properties.py::test_htf_reload_consistency` (a chart loaded from bar k, with the earlier bars as HTF context, agrees with the full history on every zone it tracks); prefix invariance (no lookahead).

## Events

`HTF_FVG_CREATED · SEEDED · FIRST_TOUCH · CE_TOUCH · FULL_FILL · INVALIDATED · DROPPED_MEMORY`. dir +1 bull / −1 bear, sid = candle-3 open time. The timeframe is in `Event.tf` (identity) and first in the audit text (`tf=15m · bottom=… · top=… · c1=…`). No HTF alerts yet.

## Resources

* `request.security`: 8 in total (2 period levels + 6 HTF).
* Boxes: ≤ 12. Lines / labels: 0.
* Memory: ≤ 120 records.
* Per closed chart bar: O(records) milestone scan.

## Parity capture (bounded Pine-Log)

* The `CAPTURE` line adds `htf=1`, the active timeframes and the three constants.
* After the first captured bar: per timeframe `HTFSTATE` (the last completed HTF bar and the last three HTF candles) and one `HTFREC` per record, the whole registry.
* `HTFBAR` on every chart bar where an HTF candle completed.
* `HO=` (open records per timeframe) on every `BAR` line.
* Checks:
  * (a) HTF candles against the oracle's own aggregation of the captured bars (time, OHLC, completion bar);
  * (b)+(c) the registry restored and replayed on the captured bars with Pine's own HTF candles: every `HTF_FVG_*` event and every bar's open counts.
