# Human / golden IFVG cases (IFVG-L11)

**What this is.** 22 cases of real MNQ 1m data, plus one mechanical case (R1) and one memory golden on the real log (MEM1), to test the **approved** IFVG-R (`docs/IFVG.md`) against human-style examples. This is not a rule search. Everything below is fixed and nothing in these files is read as a rule:
* a Phase-1-qualified FVG only;
* inversion = the frozen DEF-A5 close strictly beyond the far edge; a wick, or a close exactly on the edge, never inverts;
* the original geometry, the opposite side;
* the lifecycle from the bar after the inversion;
* the end on a close strictly beyond the IFVG's far edge; no second inversion;
* CISD, displacement, liquidity and LRL are context only.

**Provenance.**
* Every candle is copied exactly from an evidence capture in `validation/parity/evidence/`, kept byte for byte with SHA-256:
  * 20 cases from the real **IST v0.9.1-dev** capture (MNQ1!, live chart, 2026-11-02 04:16 → 23:11 New York), the IFVG-L10 evidence. Its Pine log holds IST's own FVG and IFVG events for these cases;
  * 2 cases (A7, B7) from the **v0.8.0-dev** capture (MNQZ2026, Bar Replay, 2026-10-29 / 30): another day and contract. That build has no IFVG, but its log holds the DEF-A5 `FVG_INVALIDATED`.
* No OHLC comes from a screenshot.
* A case file starts 16 bars before candle 1, so the Phase 1 TR average at candle 1 is exact. It ends one bar after the IFVG's end, or a few bars after the last fact or rejection.
* `tests/test_ifvg_golden.py` proves the candles are the evidence bars, bar for bar.

**Classification.**
* The cases were chosen from the evidence by the reviewer (Claude), and each `judgement` says why. The `special` letters are derived from the candles and the Pine log, and the test re-derives them.
* **These are not yet the user's own labels.** Every case has an exact time, so the user can look at it on TradingView. A case the user judges differently is reported as a conflict, not absorbed into the rule.

**What the test checks, per case.**
* **IFVG-R by hand** (`by_hand`: DEF-A1 / A2, DEF-A4, DEF-A5, then the IFVG's retest, CE, full traversal and end) gives every recorded number and time.
* **The oracle** (every invariant checked) **and Pine's formulation** (`IfvgPine`) give the recorded verdict, on the case window and on the whole capture (`after_window`).
* **The real Pine log agrees:**
  * v0.9.1-dev: `FVG_INVALIDATED` and `IFVG_INVERTED` of the **same FVG id on the same bar**; the audit bottom / top / ce / pre; `IFVG_FIRST_TOUCH` and `IFVG_INVALIDATED` on their bars; the CE / full facts in the BAR lines; nothing on a rejection bar;
  * v0.8.0-dev: the same DEF-A5 `FVG_INVALIDATED`.
* **Context** (`context`) is the Pine log's (CISD within ±5 bars, DISPLACEMENT-R and liquidity events on the anchor bar, LRL within ±5), and the verdict is the same with every other module on or off.
* **The bearish ↔ bullish mirror** gives the mirrored verdict.

## Cases

Times are New York. IFVG: ▼ bearish (from a bullish FVG), ▲ bullish (from a bearish FVG). "after" = later in the same capture.

| case | FVG (candle 3) | zone | before | inversion (close, ticks beyond) | IFVG | retest · CE · full | end (close) | context on / near the inversion |
|---|---|---|---|---|---|---|---|---|
| A1 | ▲ 11-02 10:28 | 28862.50–28879.25 | TOUCHED | 10:30 (28850.00, 50) | ▼ | none | ACTIVE to the capture's end | DISPLACEMENT-R ▼ and a bearish CISD on the candle |
| A2 | ▲ 11-02 07:43 | 28700.00–28702.00 | UNTOUCHED | 08:00 (28697.25, 11) | ▼ | 08:01 · 08:01 · 08:01 | 08:04 (28709.75) | SSL taken + sweep on the candle; bearish CISD +2 |
| A3 | ▲ 11-02 08:14 | 28713.75–28717.00 | CE | 08:17 (28709.50, 17) | ▼ | 08:18 · 08:18 · 08:18 | 08:36 (28754.25) | bearish CISD +2 |
| A4 | ▲ 11-02 10:13 | 28743.50–28746.75 | UNTOUCHED | 10:56 (28741.00, 10) | ▼ | 11:03 · 11:04 · 11:04 | ACTIVE to the capture's end | bullish CISD +5 only |
| A5 | ▲ 11-02 11:32 | 28674.25–28677.50 | FULL | 11:37 (28664.50, 39) | ▼ | 11:45 · 11:53 · 12:00 | ACTIVE to the capture's end | bearish CISD −1; a wick at 11:36 |
| A6 | ▲ 11-02 09:07 | 28764.75–28766.50 | UNTOUCHED | 09:08 (28763.50, 5), first eligible bar | ▼ | 09:09 · 09:09 · 09:09 | 09:09 (28770.00) | an opposite (bullish) CISD −3 only |
| A7 | ▲ 10-30 09:37 (MNQZ2026) | 28699.50–28708.25 | FULL | 10:14 (28679.50, 80) | ▼ | 10:15 · 10:18 · 10:18 | 10:37 (28725.50) | bearish CISD −5, LRL break −5 |
| B1 | ▼ 11-02 14:22 | 28333.00–28341.00 | TOUCHED | 14:27 (28349.75, 35) | ▲ | 14:28 · 14:28 · 14:28 | 14:31 (28313.00) | DISPLACEMENT-R ▲ and a bullish CISD on the candle |
| B2 | ▼ 11-02 14:26 | 28301.50–28321.00 | UNTOUCHED | 14:27 (28349.75, 115), first eligible bar | ▲ | 14:31 · 14:31 · 14:32 | 14:36 (28282.25) | the B1 candle |
| B3 | ▼ 11-02 14:48 | 28237.25–28250.75 | CE | 14:52 (28262.75, 48) | ▲ | 14:54 · 14:55 · 15:30 | 15:30 (28218.75) | bullish CISD +5 |
| B4 | ▼ 11-02 15:41 | 28128.50–28133.25 | FULL | 15:43 (28143.50, 41) | ▲ | 15:50 · 15:51 · 15:51 | 15:57 (28105.75) | bullish CISD +3; a wick at 15:42 |
| B5 | ▼ 11-02 20:42 | 28233.00–28237.50 | UNTOUCHED | 20:44 (28243.50, 24) | ▲ | 20:45 · 20:45 · 20:45 | 21:54 (28229.50) | DISPLACEMENT-R ▲; bullish CISD +1 |
| B6 | ▼ 11-02 10:53 | 28762.25–28764.50 | UNTOUCHED | 10:55 (28767.00, 10) | ▲ | 10:56 · 10:56 · 10:56 | 10:56 (28741.00) | none ±5 |
| B7 | ▼ 10-30 01:39 (MNQZ2026) | 29010.75–29013.75 | FULL | 02:28 (29016.75, 12) | ▲ | 02:29 · 02:29 · 02:29 | 02:45 (29008.75) | DISPLACEMENT-R ▲, bullish CISD and BSL taken + break on the candle |
| C1 | ▲ 11-02 07:45 | 28720.00–28727.00 | FULL | **07:47, 07:48, 07:49: wick below 28720, close above: none**; 07:50 (28715.25, 19) | ▼ | 08:13 · 08:14 · 08:36 | 08:36 (28754.25) | none ±5 |
| C2 | ▼ 11-02 10:49 | 28787.75–28791.75 | — | **10:51: high 28792.50 above the top, close 28765.00: none**; never inverted in the capture | — | — | — | none ±5 |
| C3 | ▼ 11-02 10:57 | 28742.50–28752.75 | — | **11:04 and 11:08: wick above the top, close below: none**; never inverted in the capture | — | — | — | CISDs of both sides near |
| D1 | ▲ 11-02 20:45 | 28225.75–28231.50 | FULL | wicks 21:54, 21:55, 21:57; **21:58 closes exactly on the bottom (28225.75): none**; 21:59 (28214.75, 44) | ▼ | 22:03 · 22:06 · 22:06 | 22:09 (28233.00) | SSL taken + break on the candle |
| D2 | ▼ 11-02 22:00 | 28221.00–28224.25 | FULL | wicks 22:02, 22:03; **22:05 closes exactly on the top (28224.25): none**; 22:06 (28229.75, 22) | ▲ | 22:07 · 22:07 · 22:11 | 22:11 (28220.75) | bullish CISD +3 |
| D3 | ▲ 11-02 22:46 | 28182.00–28187.00 | FULL | wicks 22:50–22:52, 22:57; **22:56 closes exactly on the bottom (28182.00): none**; 22:58 (28177.25, 19) | ▼ | 22:59 · — · — | ACTIVE to the capture's end | bearish CISD +2; LRL −2 |
| S1 | ▼ 11-02 21:53 | 28244.25–28245.25 (1 pt) | FULL | wick 22:22; **22:24 closes exactly on the top: none; 22:25 closes ONE tick above (28245.50): inversion** | ▲ | 22:26 · 22:26 · 22:26 | 22:26 (28240.00) | an opposite (bearish) CISD +2 only |
| S2 | ▼ 11-02 15:32 | 28198.50–28215.50 | FULL | wicks 16:05, 16:06; 16:07 closes **one tick** above the top (28215.75) | ▲ | 16:08 · 16:08 · 16:30 | 16:30 (28190.25) | bullish CISD −5 |

Categories:
* **A**: clear bearish IFVG.
* **B**: clear bullish IFVG.
* **C**: wick beyond the far edge, close not beyond it: no inversion.
* **D**: close exactly on the far edge: no inversion.
* **S**: borderline / supporting. These are regression cases at the one-tick boundary, never used to move it.

**Special cases the task requires (each derived from the case, re-derived by the test).**

| # | required case | where |
|---|---|---|
| A | bullish FVG → bearish IFVG | A1–A7, C1, D1, D3 |
| B | bearish FVG → bullish IFVG | B1–B7, D2, S1, S2 |
| C | wick beyond the far edge, close not beyond it → no inversion | C1, C2, C3 (also A5, A7, B4, B7, D1–D3, S1, S2) |
| D | close exactly on the boundary → no inversion | D1, D2, D3, S1 |
| E | strict close beyond → inversion | every inverted case; one tick: S1, S2 |
| F | immediate inversion, first eligible bar | A6, B2 |
| G | inversion after FIRST_TOUCH | A1, B1 |
| H | inversion after CE | A3, B3 |
| I | inversion after a full fill | A5, A7, B4, B7, C1, D1–D3, S1, S2 |
| J | inversion candle is DISPLACEMENT-R | A1, B1, B2, B5, B7 |
| K | inversion candle is not DISPLACEMENT-R | A2–A7, B3, B4, B6, C1, D1–D3, S1, S2 |
| L | same-side CISD within 5 bars | A1, A2, A3, A5, A7, B1–B5, B7, D2, D3, S2 |
| M | no CISD within 5 bars | B6, C1, D1 |
| N | retest, still ACTIVE | A2–A5, A7, B1–B5, B7, C1, D1–D3, S2 |
| O | full traversal with the close inside → still ACTIVE | A2–A5, A7, B1, B2, B4, B5, B7, D1 |
| P | strict close beyond the far edge → INVALIDATED | A2, A3, A6, A7, B1–B7, C1, D1, D2, S1, S2 |
| Q | facts, then the end, on one bar | A6, B3, B6, C1, D2, S1, S2 |
| R | invalidated and released by Phase 1 memory on one bar → the IFVG is still created | R1 (mechanical, below) |

## R1 · mechanical (synthetic candles)

No real candle shows case R. The five evidence captures were searched with every Phase 1 memory from 1 to 15 (Pine's `fvgMemory` minimum is 10), and none has it.
* **Why.** It needs a same-direction FVG created on the very bar of the inversion, with the memory full.
* Because the closes must stay above the parent's bottom until then, this happens only when the inversion comes one bar after confirmation and the new FVG's candle 1 is below the parent.
* R1 is therefore the synthetic case of `tests/test_ifvg.py`:
  * Phase 1 memory 1;
  * the FVG of bar 17 [101, 103] is invalidated on bar 18, where a new bullish FVG makes Phase 1 release it;
  * the IFVG is still created, with its geometry, and the parent is gone from Phase 1.

## MEM1 · DEF-IFVG8 on the real log

The real v0.9.1-dev run exercised the revised memory heavily.
* **Overflow kept.** The bearish side passes 50 ACTIVE IFVGs at 05:06 (20 : 50 → 19 : 51) and stays above for 655 bars, up to 66 at 23:04. All are kept.
* **Ending while over 50.** A bearish IFVG that ends while the side is over 50 is dropped on that very bar, after its `IFVG_INVALIDATED`: 05:58 at 06:39, 05:48 at 07:08.
* **Every drop was terminal.** All 153 `IFVG_DROPPED_MEMORY` in the log were INVALIDATED first:
  * 121 earlier in the log;
  * 31 in the snapshot;
  * 1 before the snapshot (its end lies before the window, NOT OBSERVABLE).
* **Mechanics.** On the same real candles with memory 2 (model only), under the invariant monitor, only INVALIDATED records leave, the oldest first, and the ACTIVE IFVGs are those of an unlimited memory.

## Reference audit (screenshots and video: no price axis)

| ref | what it shows | class | why |
|---|---|---|---|
| H1 (`../img/H1_product_ifvg_cisd.png`, "Live IFVG & CISD detection") | a bearish FVG in a drop; a bullish candle closes above its top; the box is kept, recoloured; the CISD 4 bars later | **SUPPORTING** | on the pixel-digitised candles (`../GOLD_CISD_H1.json`, price = 1000 − row), IFVG-R inverts the FVG of bar 21 [708, 733] by bar 22's close (736), 4 bars before the CISD of bar 26, with the box unchanged (`test_h1_reference_supporting_only`). Pixel prices are not market data, so it is not deterministic. IFVG-R also inverts two earlier FVGs (bars 19, 20) on bar 23 that the image does not draw: the product's display filter, unknown, not a definition conflict |
| V1 (video, 1:16–1:21.5) | an orange FVG box turns into a cyan IFVG by the close of a strong bullish candle, on the same bar as a bullish CISD | **SUPPORTING** | close-of-bar, parent box kept, by a close beyond the far edge: as IFVG-R. No axis, so not deterministic |
| V2 (video, 0:05–0:30) | narration: "inversion FVGs", HTF gaps "when they get inversed" | **INCONCLUSIVE** | no IFVG candle readable; HTF IFVG is out of scope |
| H2, H3, H4 | CISD references (an FVG as context, no inversion drawn) | not IFVG references | — |

**Conflicts with IFVG-R.** None.
* Every readable reference shows the parent box, kept, and an inversion by the candle's close beyond the far edge.
* No reference shows a wick inversion, a new geometry, or an IFVG drawn intrabar.
