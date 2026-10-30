# CISD human / reference audit (2026-10-30) — no definition change, no Pine change

**Question.** Do the human and reference CISD examples the user supplied agree with CISD-R (`docs/CISD.md`, IST v0.7.0-dev), or do they show a systematic mismatch?

**Material.** The user's 4 screenshots, kept in `validation/golden/human/img/`:
* H1, the product image "Live IFVG & CISD detection";
* H2, a trader's bearish CISD inside a 4H FVG;
* H3, an "LRLR" + CISD long;
* H4, a "Bullish CISD" with a 15m FVG.

Also the YouTube video *ICT PRO+ Indicator preview video* (Timmy, unlisted, 2:25): https://www.youtube.com/watch?v=EIbRq4xECnI. Its transcript was read, and 1080p frames were inspected at 0:21, 1:16, 1:18.5, 1:19.4, 1:20 and 1:21.5.

**Method.**
* No screenshot has a readable price or time axis. Levels are therefore measured in **pixels**; ticks cannot be derived.
* Where the candles are readable (H1, H2), they were digitised from the pixels:
  * bodies by colour, wicks by the grey wick line;
  * a few pixels corrected by eye where a drawn line or box hides a wick;
  * price = 1000 − pixel row, 1 unit = 1 px.
* The approved oracle (`CisdEngine`) was then run on those candles, and its CISD compared with the drawn one.
* Both are now golden cases that run in every validation: `validation/golden/human/GOLD_CISD_H1.json` and `GOLD_CISD_H2.json`.
* The oracle starts UNKNOWN on the first visible candle. It may print other CISDs before the drawn one; only the drawn one is labelled (`events_match: subset`).

## A · Human CISD golden comparison

**H1 · product image (white chart).** Classification: **EXACT MATCH**.

| item | human / reference | CISD-R |
|---|---|---|
| side | bullish | bullish |
| delivery sequence | 2 up-close, then 4 consecutive down-close candles (bars 18–21) into the low; bar 22 (up-close) has a lower wick below them | — |
| origin (open used) | bar 18 (the line starts at its body, x 869) | bar 18 |
| L | row 179–180 (line drawn 2 px); open of bar 18 = row 180 | row 180 |
| delivery extreme | bar 21 low (row 351); bar 22's wick (row 367) is not a delivery candle | bar 21 (row 351) |
| confirmation | close of bar 26 above the line; bar 24's wick through the line does not count | bar 26, by close |
| difference | 0 px, 0 bars | |

**H2 · trader, bearish, inside a 4H FVG, short.** Classification: **EXACT MATCH**.

| item | human / reference | CISD-R |
|---|---|---|
| side | bearish | bearish |
| delivery sequence | up-close bars 10–11 into the highest up-close high (bar 11); the highest high overall is bar 8's wick, a down-close candle | — |
| origin (open used) | bar 10 (line from x 92) | bar 10 |
| L | row 183–185 (line); open of bar 10 = row 183 | row 183 |
| delivery extreme | bar 11 high (row 20); bar 8's higher wick is ignored | bar 11 (row 20) |
| confirmation | close of bar 12 below the line (the entry is bar 13's open, so the trader took it as confirmed at bar 12's close) | bar 12, by close |
| difference | 0 px, 0 bars | |

**H3 · "LRLR" + CISD, long.** Classification: **NOT ENOUGH INFORMATION**.
* What is readable: a bullish CISD after a sweep below the range lows, under a descending "LRLR" line. The CISD line and the "CISD" label are at the right end.
* Not readable: the image is 188 × 157 px and candles are about 1 px wide, so the delivery sequence, the origin candle, its open and the confirmation candle cannot be identified.
* CISD-R comparison: not run.

**H4 · "Bullish CISD", 15m FVG, long.** Classification: **NOT ENOUGH INFORMATION**. The level is consistent with CISD-R.
* Readable:
  * the line starts at the open of the big down-close candle that starts the drop (row 58), and the preceding candle is up-close;
  * a green candle closes above the line (row 47);
  * the long is entered on the next bar.
* Not readable:
  * the image is 194 × 186 px;
  * the delivery low and 2–3 candles between the origin and the confirmation are below the frame (only wick stubs are visible).
* CISD-R comparison:
  * CISD-R would choose the same origin if the hidden candles continue the down series;
  * if the hidden candles start a later series, it would choose that series (a lower L) instead;
  * the confirmation timing cannot be verified.

**V1 · video, 1:13–1:21 (30-second chart).** Classification: **NOT ENOUGH INFORMATION**. The level and timing are consistent with CISD-R.
* Readable:
  * "Bullish CISD" starts at the open of the first down-close candle of the drop;
  * a green candle closes far above it;
  * the IFVG flips on the same bar.
* Not readable: the drop's low is below the visible crop.
* CISD-R comparison: same origin if the drop is one down-close series; the confirming candle is the same bar.

**V2 · video, 0:21 (live scenario).** Classification: **NOT ENOUGH INFORMATION**. The level is consistent with CISD-R.
* Readable: "Bullish CISD" inside a "4H Fair Value Gap", starting at the open of the big down-close candle that starts the drop; a green candle closes just above it.
* Not readable: the low is out of the frame.
* CISD-R comparison: as for V1.

**Outcome and context, recorded as metadata only** (`validation/golden/human/README.md`):
* H3 reached its target.
* H4 is the structurally valid CISD that **failed**: price fell into the stop after the long.
* Outcomes never change detection. A CISD describes a change in delivery state; the next move is metadata (DEF-CISD7 has no outcome state).

## B · Exact matches vs mismatches

| classification | cases |
|---|---|
| EXACT MATCH | **H1, H2** (independent sources: a product image and a trader's own chart) |
| LEVEL MATCH / TIMING DIFFERENCE | none |
| TIMING MATCH / LEVEL DIFFERENCE | none |
| DEFINITION MISMATCH | **none** |
| NOT ENOUGH INFORMATION | H3, H4, V1, V2 (no contradiction; H4, V1 and V2 are consistent where readable) |

## C · Systematic mismatch

**None.** Where the candles can be read, the human and reference examples agree with CISD-R on the three rules the study had to choose between:
The variants were run on the same digitised candles (`validation/studies/cisd.py`).
* **Anchor = the first candle of the delivery series, not the last.** The last-candle anchor (study candidate CISD-4) disagrees with both humans:
  * H1: L at bar 21's open (row 297, 117 px below the drawn line), confirmed on bar 22, 4 bars early;
  * H2: L at bar 11's open (row 84, 99 px from the line).

  H4, V1 and V2 also draw from the first candle of the move.
* **Only delivery candles set the leg extreme.**
  * H2: with the "any candle" variant, the highest wick (bar 8, a down-close candle) would move the reference to bar 7's series: L at row 244 (61 px off), confirmed on bar 13 (1 bar late). The trader's line follows the delivery-only rule.
  * H1 does not discriminate: its spike candle sits in the same series either way.
* **Confirmation by close, not wick.** In H1, bar 24's wick crosses the line without a CISD; the CISD is the close of bar 26. In H2 the entry follows the confirming close.

## D · Pine visual differences (not mathematical)

| | references (H1–H4, video) | Pine v0.7.0-dev |
|---|---|---|
| level | one horizontal 1 px line at L | same |
| start | at the origin candle | at the origin candle (its bar time) |
| end | **past the confirming candle**: about 7 bars (H1, video 0:21), 4 (H2), about 8 (video 1:20) | at the confirming candle |
| text | "CISD" (H1–H3) or "Bullish CISD" (H4, video), small, **at the right end, above the line** (H1–H3) or inline to its right (H4, video) | "CISD", tiny, at the confirming candle, **below** the line for a bullish CISD and above for a bearish one |
| colour | blue (H1, H2) or dark grey / black (H3, H4, video) | `#4F473F` dark grey-brown (the user's palette) |
| count | one CISD at a time | current only (previous optional) |
| boxes / markers | none | none |

Possible renderer tweak, for a separate styling decision (not done):
* extend the line a fixed few bars past the confirmation (the references suggest 4–8);
* put the label above the line at its right end, for both sides.

Neither touches detection.

## E · Video findings

| time | concept claimed (transcript) | what the frames show | CISD-R |
|---|---|---|---|
| 0:05–0:30 | marks session lows, inversion FVGs, CISDs, relevant FVGs "being held"; "when they get inversed, we get those 4-hour and high time frame relevant gaps"; SMT; "low resistance liquidity" | 0:21: "Bullish CISD" line from the open of the first down-close candle of a drop, inside a "4H Fair Value Gap", confirmed by a close just above | consistent; the low is out of frame (ambiguous for an exact check) |
| 1:13–1:26 | "major displacement … we form this fair value gap … we inverse that and we form this bullish change in state of delivery. All of this is marked out in live time" | 1:16: an orange "FVG" box. 1:18.5–1:19.4: the confirming green bar is forming, already above L, with **no CISD and no IFVG drawn**. By 1:20 the "Bullish CISD" line (from the open of the drop's first down-close candle) and the cyan IFVG (the same box) appear; at 1:21.5 the next bar is printed | supports close-of-bar confirmation; the level is consistent; nothing was observed intrabar |
| 1:26–1:41 | "we marked out that IFG [IFVG] … that bullish change in state of delivery … swept that London low … the indicator marked out the IFG plus CISD and we got that confirmation" | the trade: London-low sweep, then IFVG + CISD, then a long | context only (liquidity → CISD + IFVG); it does not define CISD |
| whole video | "live", "in live time" | the replay shows marking at or after the confirming bar's close | marketing wording; no intrabar evidence |

No part of the video states a CISD or IFVG rule in words.

## F · IFVG

See `docs/IFVG_REQUIREMENTS.md`: research requirements, observations, and an audit of the FVG identity already stored.

## G · Recommendation: **KEEP CISD-R**

Evidence:
* 2 EXACT MATCHES out of 2 verifiable human / reference examples, from independent sources.
* 0 definition, level or timing mismatches.
* The 4 unverifiable cases are consistent wherever readable.
* The human lines confirm the three rules the study chose (series anchor, delivery-only extreme, close confirmation), each against its rejected alternative.
* The reference product appears to mark at the bar close, which matches our confirmed-bar, non-repainting engine.
* The only differences are visual: line length and label position.
* Reopen only if real labelled NQ cases (CISD-L11) show a repeated mismatch.
