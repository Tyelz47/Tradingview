# Golden dataset

Hand-labelled cases that the reference model must reproduce exactly. One JSON file
per case:
* `synthetic/` holds small cases built by hand to pin one rule.
* `nq/` holds real NQ examples labelled from TradingView. It is empty for now.
* `human/` holds human / reference CISD candidates digitised from the user's screenshots (pixel units). The provenance, the audit and the context / outcome metadata are in `human/README.md`.

Every case also runs with all invariants checked.

## Format

```json
{
  "id": "GOLD_FVG_001",
  "description": "what the case shows, and which rule (DEF-xx, Lxx)",
  "source": "synthetic | tradingview",
  "symbol": "NQ1!",
  "timeframe_sec": 60,
  "timezone": "America/New_York",
  "tick_size": 0.25,
  "start": "2026-10-27T09:41",
  "warmup": {"bars": 20, "ohlc": [o, h, l, c]},
  "settings": {"modules": ["fvg"], "fvg": {"min_ticks": 2, "k_tra": 0.0}},
  "candles": [[o, h, l, c], ["2026-10-27T09:45", o, h, l, c]],
  "expected": {
    "events": [{"bar": 2, "type": "FVG_CREATED", "dir": 1, "price": 21001.5, "sid_bar": 2}],
    "events_match": "exact",
    "event_types": ["FVG_CREATED", "FVG_FIRST_TOUCH"],
    "structures": [{"kind": "fvg", "match": {"dir": 1, "confirm_bar": 2}, "expect": {"top": 21002.0}}],
    "final_states": [{"kind": "fvg", "match": {"dir": 1, "confirm_bar": 2}, "expect": {"status": "OPEN"}}]
  }
}
```

Field notes:

* **`start`** is local time in `timezone`. Candles are `timeframe_sec` apart. A row that starts with an ISO time resets the clock, so session breaks are possible.
* **`warmup`** is optional. It adds N identical bars first, and they count in the bar numbers. Liquidity cases use it so that bar 20 is the first real bar.
* **`settings`** use the oracle names (`validation/models/types.py`). For liquidity, `"liq": {"preset": "balanced"}` also works.
* **`events`**: each listed event must be present. You give only the fields you care about: `bar`, `type`, `dir`, `price`, and `sid_bar`, which is the bar of the structure id.
* **`events_match: "exact"`**: no other events of the listed `event_types` may occur. If `event_types` is missing, it defaults to the types listed in `events`. Use `"subset"` to allow other events.
* **`structures`** and **`final_states`** select exactly one record by `match` and compare the fields in `expect` against the final state.
* **`kind`** is one of:
  * `fvg`: fields `dir`, `confirm_bar`, `top`, `bottom`, `mid`, `touch_bar`, `ce_bar`, `full_bar`, `inv_bar`, `status`
  * `liq`: fields `side`, `origin_bar`, `confirm_bar`, `price`, `taken_bar`, `take_ext`, `cls`, `gap`, `eq`, `status`
  * `eq`: fields `side`, `id_bar`, `ref`, `bound`, `members_bars`, `qual_bar`, `taken_bar`, `cls`
  * `session`
  * `level`

## Adding a real NQ case (manual labelling)

1. In TradingView, pick a short window, 30–200 bars. Export the chart data (*Export chart data…*), or copy the OHLC.
2. Write the candles into `nq/GOLD_<AREA>_<NNN>.json` with `"source": "tradingview"`, the exact settings used on the chart, and the window start.
3. Label the expected events from the chart and from the IST debug rows (Last events, inspectors). Do not label from the Python output.
4. Run `python -m validation --mode quick`.
   * A failure means the Pine behaviour, the label and the oracle disagree. Look at all three before changing any of them.
   * Never edit an expectation to make a case pass without checking the chart.

Warm-up matters. The liquidity reaction floor needs 14 bars of TR average before the swing, and FVG thresholds need `length` bars. Include enough bars before the labelled structure, or set the thresholds to 0 in the case settings.
