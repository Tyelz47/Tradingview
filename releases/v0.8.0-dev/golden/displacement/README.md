# Human / golden displacement cases (DISP-L11)

**What this is.** 19 cases, 22 candles, of real NQ / MNQ 1m data, to test the **approved** DISPLACEMENT-R (`docs/DISPLACEMENT.md`) against human-style examples. This is not a threshold search: k = 1.5, close position 0.75, A = TR average of the 14 bars before, and the close beyond the previous candle are fixed. Nothing in these files is read as a threshold.

**Provenance.**
* Every candle is copied exactly from an evidence capture in `validation/parity/evidence/`, which is kept byte for byte with SHA-256: NQ1! from the two v0.4.x captures merged, MNQ from the v0.7.0-dev and v0.7.1-dev captures. No OHLC comes from a screenshot.
* A case file holds 15 bars before its first case bar, so its A uses only exact true ranges, and 1 bar after, for the FVG metadata.
* `tests/test_displacement_golden.py` proves the candles are the evidence bars, bar for bar.

**Classification (before the detector).**
* Each case's category and `judgement` were written by the reviewer (Claude) from the candle's shape. The criteria are those of the research: aggressive one-sided repricing, a large body against the neighbouring candles, a strong close, limited rejection, the close beyond the previous candle.
* The detector was run on the case files afterwards.
* **These are not yet the user's own labels.** Every case has an exact time, so the user can look at it on TradingView. A case the user judges differently is reported as a conflict, not absorbed into the rule.

**Approved verdict.** The arithmetic of DEF-DISP1…5 on the recorded numbers, written out in the test.

**What the test checks.**
* The oracle and Pine's formulation (`DispPine`) give that verdict, on the case window and on the case's full evidence history.
* For the 4 cases inside the real IST v0.8.0-dev capture (A3, A6, B5, C1), the verdict, A, body / A, close position and the next bar's FVG metadata that **Pine itself logged** are the same.
* The bearish mirror of every case gives the mirrored verdict.
* The CISD relation is recomputed with the frozen CISD-R oracle on the full history.

## Cases

The FVG column is the DEF-A1 geometry on the next candle. It is the record's metadata only for a displacement; for the others it is information.

| case | cat. | candle (New York) | dir | body / A | range / A | close pos. | beyond prev. | DISPLACEMENT-R | failing condition(s) | FVG next | same-side CISD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | A | MNQ 2026-10-14 03:02 | ▲ | 3.245 | 3.40 | 0.953 | yes | **BULL** | — | YES | on the bar |
| A2 | A | NQ1! 2026-10-28 05:15 | ▲ | 2.382 | 2.49 | 0.956 | yes | **BULL** | — | YES | none ±10 |
| A3 | A | MNQ 2026-10-30 10:38 | ▲ | 2.459 | 2.58 | 0.978 | yes | **BULL** | — | YES | −7, +10 |
| A4 | A | NQ1! 2026-10-27 18:02 | ▼ | 3.500 | 3.76 | 0.931 | yes | **BEAR** | — | YES | on the bar |
| A5 | A | MNQ 2026-10-14 09:31 | ▼ | 2.606 | 3.89 | 0.981 | yes | **BEAR** | — | NO | +6 |
| A6 | A | MNQ 2026-10-30 02:00 | ▼ | 2.217 | 2.63 | 0.912 | yes | **BEAR** | — | YES | none ±10 |
| B1 | B | NQ1! 2026-10-27 08:25 | ▲ | 0.282 | 2.09 | 0.144 | no | none | body; close position; not beyond | NO | none ±10 |
| B2 | B | MNQ 2026-10-14 01:00 | ▼ | 0.381 | 2.40 | 0.227 | yes | none | body; close position | NO | −8, +1, +7 |
| B3 | B | NQ1! 2026-10-27 14:00 | ▼ | 2.266 | 4.53 | 0.537 | yes | none | close position only | NO | −8 |
| B4 | B | MNQ 2026-10-14 06:46 | ▼ | 1.546 | 1.66 | 0.930 | no | none | not beyond the previous low only | NO | none ±10 |
| B5 | B | MNQ 2026-10-30 01:20 | ▼ | 0.604 | 0.89 | 1.000 | yes | none | body only | NO | on the bar |
| C1 | C | MNQ 2026-10-30 12:39 | ▲ | 1.507 | 1.66 | 0.929 | yes | **BULL** | — | YES | none ±10 |
| C2 | C | NQ1! 2026-10-28 07:27 | ▲ | 1.483 | 1.48 | 1.000 | yes | none | body only (just below 1.5) | NO | none ±10 |
| C3 | C | NQ1! 2026-10-27 22:30 | ▲ | 1.860 | 2.59 | 0.756 | yes | **BULL** | — | YES | on the bar |
| C4 | C | NQ1! 2026-10-27 23:50 | ▲ | 2.163 | 2.92 | 0.740 | yes | none | close position only (just below 0.75) | YES | −5 |
| C5 | C | NQ1! 2026-10-27 22:52 | ▼ | 1.509 | 1.64 | 0.941 | yes | **BEAR** | — | YES | +5 |
| C6 | C | MNQ 2026-10-30 14:12 | ▼ | 1.482 | 1.84 | 0.917 | yes | none | body only (just below 1.5) | YES | none ±10 |
| I1 | S/I | NQ1! 2026-10-28 03:56 | ▲ | 2.610 | 4.97 | 0.652 | yes | none | close position | YES | +1 |
| I1 | S/I | NQ1! 2026-10-28 03:57 | ▲ | 1.613 | 2.68 | 0.602 | no | none | close position; not beyond | NO | on the bar |
| I2 | S/I | MNQ 2026-10-14 02:02 | ▼ | 0.833 | 1.43 | 0.783 | no | none | body; not beyond | NO | +1 |
| I2 | S/I | MNQ 2026-10-14 02:03 | ▼ | 0.955 | 1.07 | 0.894 | yes | none | body | YES | on the bar |
| I2 | S/I | MNQ 2026-10-14 02:04 | ▼ | 1.424 | 1.71 | 0.935 | yes | none | body | YES | −1 |

Categories:
* **A**: clear displacement.
* **B**: clear non-displacement.
* **C**: borderline. These are regression cases at one approved boundary, never used to move it.
* **S/I**: SUPPORTING / INCONCLUSIVE.

**Special cases the task requires.**

| # | required case | where |
|---|---|---|
| 1 | displacement + CISD | A1, A4, C3 |
| 2 | displacement without CISD | A2, A6 |
| 3 | CISD without displacement | B5 (also I1 03:57, I2 02:03) |
| 4 | FVG = YES | A1, A2, A3, A4, A6 |
| 5 | FVG = NO | A5 |
| 6 | large range, weak body | B1, B2 |
| 7 | body / A ≥ 1.5, close position < 0.75 | B3 (also C4, I1) |
| 8 | strong body and close, previous extreme not exceeded | B4 |

* Every approved condition decides at least one case on its own: the body (B5, C2, C6), the close position (B3, C4), and the close beyond the previous candle (B4).
* The real data hold no candle that passes the body and close-position conditions and misses the close-through by less than 1 point. The tick-exact boundary of that condition is pinned by the synthetic tests in `tests/test_displacement.py` and `tests/test_displacement_pine.py`.

## Audit against the conceptual description

**Clear cases.**
* All 6 clear displacements (3 ▲, 3 ▼) are what the research describes: aggressive one-way repricing, a body 2.2–3.5 × the local true range, a close in the outer 10 % or less (0.91–0.98), and a close 12–59 points beyond the previous candle.
* The rule needs no CISD, sweep, FVG, IFVG, BOS / MSS or DOL:
  * A2 and A6 have no CISD within 10 bars;
  * A5 leaves no FVG.
* All 5 clear non-displacements are rejected for the reason a trader would give:
  * a wide two-sided or rejected candle (B1, B2);
  * a big body whose push was rejected inside the bar (B3);
  * a strong candle still inside the previous candle (B4);
  * a small candle that is only a CISD (B5).

**SUPPORTING / INCONCLUSIVE (the honest edge of the definition).**
* **I1 (NQ1! 2026-10-28 03:56–03:57).** A fast two-candle advance of about 4 × A that leaves an FVG. Each candle has a large upper wick (close positions 0.65 and 0.60), and DISPLACEMENT-R flags neither.
  * A trader might call the leg displacement; the candles show rejection.
  * This is the approved strong-close criterion (M2) and multi-bar exclusion (M5) working as designed. It is not a contradiction of the definition, but it is the type of case the user should look at.
* **I2 (MNQ 2026-10-14 02:02–02:04).** A three-candle bearish staircase of about 3.3 × A, with no single large candle. Displacement as a leg, not as a candle: a separate future object (M5).

**Conflicts with DISPLACEMENT-R.** None found among the clear cases. I1 and I2 are documented, approved exclusions, not systematic conflicts.
