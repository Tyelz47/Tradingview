# Human / reference CISD golden candidates

**Provenance.**
* Screenshots supplied by the user on 2026-10-30, kept in `img/`.
* Each one was audited against CISD-R in `docs/AUDIT_CISD_HUMAN.md`.
* None has a price or time axis, so the verifiable ones are digitised in pixels: price = 1000 − pixel row, tick 1.

**What runs.** Only cases whose candles are fully readable become `GOLD_CISD_*.json`, which the golden runner reproduces with every invariant checked. They are candidates; the real labelled NQ cases come with CISD-L11.

**Rule.** Context and outcome below are **metadata only**. They never enter CISD detection. A valid CISD that later fails is still a valid CISD.

| id | image | side | CISD-R audit | context (metadata) | outcome (metadata) |
|---|---|---|---|---|---|
| H1 | `img/H1_product_ifvg_cisd.png` (product: "Live IFVG & CISD detection") | bullish | **EXACT MATCH**: `GOLD_CISD_H1.json` (origin bar 18, L row 180, confirmed bar 26 by close; a wick through on bar 24 is no CISD; a non-delivery spike below is ignored) | an IFVG (an inverted bearish FVG) 4 bars before the CISD, below its level | no position shown |
| H2 | `img/H2_bearish_cisd_4h_fvg.png` (trader) | bearish | **EXACT MATCH**: `GOLD_CISD_H2.json` (origin bar 10, L row 183, confirmed bar 12 by close; the highest wick, bar 8, is a down-close candle and is ignored) | inside a 4H FVG; short entered at bar 13's open | in progress at the screenshot |
| H3 | `img/H3_lrlr_cisd_long.png` (trader) | bullish | NOT ENOUGH INFORMATION (candles ≈ 1 px) | under a descending "LRLR" line; sweep below the range lows; long | **success**: price ran through the LRL into the target |
| H4 | `img/H4_bullish_cisd_15m_fvg_failed.png` (trader) | bullish | NOT ENOUGH INFORMATION (the low and the candles between origin and confirmation are below the frame); the line is at the open of the drop's first down-close candle, as CISD-R would draw it | 15m FVG above; long after the confirming close | **failed**: price fell into the stop after the entry |
| V1 | video 1:13–1:21.5 | bullish | NOT ENOUGH INFORMATION (low below the crop); origin and confirming bar consistent; drawn by the bar close, not intrabar | London-low sweep, hourly gap above, an IFVG on the same bar (SMT is mentioned by the author; excluded from IST) | target reached (per the video) |
| V2 | video 0:21 | bullish | NOT ENOUGH INFORMATION (low out of frame); origin consistent | inside a "4H Fair Value Gap" | — |
