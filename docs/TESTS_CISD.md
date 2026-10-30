# IST · CISD tests — v0.7.0-dev (EXPERIMENTAL)

**Status.**
* Automated validation: see `CHANGELOG.md`.
* TradingView: every CISD-L test is **PENDING**. They are recorded only from the user's results, never assumed.
* CISD is frozen only after **CISD-L10** (real Pine ↔ oracle capture parity) gives **0 DIFFERENCE** and the user's labelled golden cases (**CISD-L11**) agree.

**Build:** `src/IST.pine` v0.7.1-dev (branch `cisd/pine`). Definition: `docs/CISD.md` (CISD-R, approved 2026-10-30).

**First real capture (v0.7.0-dev, 2026-10-30, `validation/parity/evidence/ist-v0.7.0-dev_mnq-1m_capture-1000_2026-10-30.csv`):** v0.7.0-dev compiled and ran. Every CISD agreed with the oracle (side, id, time, L, previous state, close, extreme, its time). Only the metadata bk differed: `cisdTra[1]`, read inside `confirmCisd`, returned the TR average of the previous same-side confirmation (the previous call of that call site), not of the bar before the confirming bar (80 of 80 reproduced). v0.7.1-dev reads it at global scope (`cisdTraPrv`); ST-21. **CISD-L10 needs a new capture with v0.7.1-dev.**

## Automated (before TradingView)

| id | what | where |
|---|---|---|
| S-CISD-1 | Pine's incremental formulation (`CisdStack`) = the approved oracle (`CisdEngine`), record and event for record and event: NQ 1m / 3m / 5m / 15m, four 20,000-bar walks, a mirrored walk, every scenario, memory 50 and 2, generated candles | `tests/test_cisd_pine.py`, `fuzz/test_cisd_properties.py` |
| S-CISD-2 | a leg longer than 500 bars is exact: origin 657, extreme 648, leg extreme 560 bars back; flip window 649 bars; no truncation (500 bars only would give another L) | `tests/test_cisd_pine.py` |
| S-CISD-3 | 34 rule lines, 3 constants, the per-bar order, no history read beyond the metadata's `[1]` and no number in the engine (no leg-length limit), guard and display inputs outside detection | ST-20 |
| S-CISD-4 | the 15 mutations the user listed (wick confirmation, `>=`, `<=`, first equal extreme, all wicks, doji continuing, colour required, no alternation, initial UP, opposite leg from the confirmation bar, displacement required, guard gating detection, display toggle gating detection, side not in the identity, 500-bar truncation) and 12 more are caught | `tests/test_cisd_pine.py` |
| S-CISD-5 | Pine event names = oracle names (the oracle-only exception removed) | ST-14 |
| S-CISD-6 | settings: 4 normal inputs (ON / ON / OFF / OFF), no mathematical input, Developer Inspect CISD; renderer: one 1 px line at L from origin to confirmation, a tiny CISD label, previous only with the toggle, no box, bar-time coordinates; debug rows 45–51; capture keys | `tests/test_cisd_pine.py` |
| S-CISD-7 | oracle: the user's T1–T18 and the record fields | `tests/test_cisd.py` |
| S-CISD-8 | invariants INV-CISD-01 … 08, each with a negative test | `invariants.py`, `tests/test_invariants.py` |
| S-CISD-9 | bounded CISD parity: 0 DIFFERENCE on faithful captures that start from an established state (NQ, walks with memory drops); 10 kinds of error detected; replay with Pine's constants | `tests/test_parity_cisd.py` |

## TradingView procedure (NQ1! 1m unless stated; Confirmed only ON)

Before you start: in the Pine Editor, replace the code with `src/IST.pine` v0.7.0-dev, save it, and add it to an NQ1! 1m chart. Debug mode rows 45–51 show the CISD engine, its state, both sides, an inspector and what is drawn.

| id | test | how | expected |
|---|---|---|---|
| CISD-L00 | compile and runtime | add the indicator; open the Pine Logs and the status line | no compile error, no runtime error (in particular no "CISD: two confirmations on one bar"), the chart loads |
| CISD-L01 | settings | open the settings | group CISD · CHANGE IN STATE OF DELIVERY: Enable CISD engine ON, Show CISD ON, Show previous CISD OFF, CISD alerts OFF; no other CISD input. Developer: Inspect CISD |
| CISD-L02 | the drawing | look at the current CISD | one short thin line at L from the first candle of the delivery series to the confirming candle, a small "CISD" label at its end, neutral grey-brown; nothing else (no box, no older lines) |
| CISD-L03 | the definition on the chart | Bar Replay through a bullish CISD; Debug row 47 | L = the open of the first down-close candle of the series into the lowest down-close low; no CISD on a wick through L or a close exactly at L; the CISD on the first close one tick above |
| CISD-L04 | alternation | scroll through several CISDs (Inspect CISD 0, 1, 2, …) | bullish and bearish CISDs alternate; row 49 shows UP → DOWN → UP …; the first loaded CISD has UNKNOWN before it |
| CISD-L05 | toggles are view-only | switch Show CISD OFF, then Show previous CISD ON | the drawing disappears (then the previous CISD appears faded); Debug rows 46–50 do not change |
| CISD-L06 | 200-bar guard | a chart whose history is short, or Bar Replay from the chart start | no CISD drawn while bar index < 200 (row 46 says so); a CISD confirmed before bar 200 is never drawn later; CISD events still appear in Pine Logs (Debug ON) |
| CISD-L07 | alert | CISD alerts ON; create an alert "Any alert() function call" | one message per CISD_CONFIRMED at the bar close; none with CISD alerts OFF |
| CISD-L08 | other modules unchanged | Enable CISD engine OFF, then ON | FVG / sessions / levels / BSL / SSL / EQ / LRL / HTF drawings and Debug rows 0–44 identical |
| CISD-L09 | other chart timeframes | 3m, 5m, 15m charts | no error; CISDs alternate; fewer per hour on higher timeframes |
| CISD-L10 | **real parity (freeze gate)** | Developer → Parity capture ON (300 bars; Enable CISD engine ON); save the Pine Logs as `validation/parity/pine_capture_cisd.csv`; run `python -m validation.parity --capture validation/parity/pine_capture_cisd.csv` | **0 DIFFERENCE**, the CISD section included (per-bar state and candidates, events, the definition oracle after synchronisation) |
| CISD-L11 | **golden cases (freeze gate)** | the user marks real CISDs on the chart (time, side, L) | they become the first human-labelled CISD golden cases; each is reproduced by the oracle |
| CISD-L12 | reload | note several CISDs (time, side, L); reload the chart, change the history window | the same CISDs, with the same ids, after the first few CISDs of the new history (the state starts UNKNOWN; `docs/CISD.md` §3) |

Results (user):

| id | result | date | notes |
|---|---|---|---|
| CISD-L00 … L12 | PENDING | | |
