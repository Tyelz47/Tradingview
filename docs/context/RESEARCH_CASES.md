# IST · CONTEXT-01 · Research cases (real data) and dataset proposal

**Status: RESEARCH (2026-11-03).**
* Every table is printed by `python -m validation.studies.context`. `validation/tests/test_context_study.py` pins the key numbers.
* No case was chosen by hand and no result was invented. Where a requested category does not occur in the data, it is reported as **NOT FOUND**.

## 1 · Data inventory

| segment | bars | hours | completed D · W bars from Pine | PDH / PDL source |
|---|---|---|---|---|
| NQ1! 2026-10-27 03:38 → 10-28 07:56 | 1639 | 27.3 | 0 · 0 | LEVEL_SET at the 10-27 18:00 roll only |
| MNQZ2026 2026-10-29 19:56 → 10-30 15:43 | 1188 | 19.8 | 3 · 3 | HTF snapshot (HTFSTATE / HTFBAR) |
| MNQZ2026 2026-10-13 19:57 → 10-14 13:52 (Bar Replay) | 1076 | 17.9 | 3 · 3 | HTF snapshot (HTFSTATE / HTFBAR) |
| MNQ1! 2026-11-02 04:16 → 23:11 | 1076 | 17.9 | 4 · 3 | HTF snapshot (HTFSTATE / HTFBAR) |

**How the segments were built.**
* Captures that share bars are merged only where every shared bar is identical:
  * v0.4.3 + v0.4.4 share 411 bars;
  * the v0.8.0 replay + the v0.7.0 live capture share 964 bars, with 0 differences.
* Segments are never joined to each other.

**Honesty notes.**
* **83 h in total. NQ family only; no ES.**
* About one trading day per segment, so only **13 decision points**.
* For NQ1! 10-27 there is **no PDH / PDL**: that capture predates the HTF snapshot, and the previous day lies outside it.
* London on 10-27 and 11-02 was already in progress at load, so it is never tracked (DEF-F2).
* The oracle has no Pine history before a segment. Decisions and events need ≥ 200 bars before them (the DEF-CISD9 guard).
* The facts are the frozen oracle's. These captures gave Pine ↔ oracle parity with 0 DIFFERENCE for:
  * Phase 2: v0.4.4;
  * CISD: v0.7.1;
  * displacement: v0.8.0;
  * IFVG: v0.9.1.
* The PDH / PDL / PWH / PWL values are TradingView's own, as Pine logged them.

## 2 · Selection rule (fixed before looking)

* **Decision points:** the close of the bar before every session window opens (Asia 20:00, London 02:00, NY AM 09:30, NY PM 13:30 ET), with ≥ 200 bars of history.
* **Event points:** every frozen fact on bars ≥ 200 (CISD, displacement, IFVG inversion, Phase 2 sweep / break, LRL terminal), plus every first take of an AVAILABLE external target.
* **Horizon:** 17:00 ET, the end of the trading day. CENSORED if the data ends first.
* **FEATURES_AT_T come from the segment cut at t.** A test shifts every later bar by 1,000 points and drops every later HTF bar; every feature is unchanged.

## 3 · Decision points (FEATURES_AT_T · the first OUTCOME)

* "nearest" = the nearest AVAILABLE target of that class group, in TR averages (TRA14 at t).
* "first external reached" is OUTCOME_AFTER_T.

| # | segment · decision (ET) | opens | close | PDH · PDL (status) | pos in PD range | CISD 1m (age) · 15m | nearest external ▲ · ▼ (× TR avg) | nearest Phase 2 ▲ · ▼ (× TR avg) | external taken earlier today | first external reached after t |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | NQ1! 10-27 09:29 | NY AM | 29560.2 | — | — | UP (1) · UP | — · — | BSL 5.8 · SSL 3.5 | — | none |
| 2 | NQ1! 10-27 13:29 | NY PM | 29788.5 | — | — | DOWN (11) · DOWN | — · NY AM L 30.9 | BSL 9.2 · SSL 1.1 | NY AM H BREAK | none |
| 3 | NQ1! 10-27 19:59 | Asia | 29853 | PDH 29881.2 AVAILABLE; PDL 29288 AVAILABLE | 0.95 | DOWN (1) · UP | NY PM H 4.2 · NY PM L 14.3 | BSL 1.7 · SSL 6.9 | — | NY PM H (▲, +102 bars) |
| 4 | NQ1! 10-28 01:59 | London | 29912.8 | PDH 29881.2 TAKEN·BREAK; PDL 29288 AVAILABLE | 1.05 | UP (5) · UP | Asia H 7.9 · Asia L 17.2 | BSL 3.0 · SSL 1.8 | PDH BREAK, NY PM H BREAK | Asia H (▲, +42 bars) |
| 5 | MNQZ2026 10-30 01:59 | London | 28980 | PDH 29794.2 AVAILABLE; PDL 29111 TAKEN·? | -0.19 | DOWN (19) · DOWN | Asia H 15.7 · Asia L 16.5 | BSL 6.4 · SSL 11.3 | — | Asia L (▼, +305 bars) |
| 6 | MNQZ2026 10-30 09:29 | NY AM | 28798.8 | PDH 29794.2 AVAILABLE; PDL 29111 TAKEN·? | -0.46 | UP (11) · UP | London H 20.5 · — | BSL 3.4 · SSL 3.5 | Asia L SWEEP, London L SWEEP | none (censored) |
| 7 | MNQZ2026 10-30 13:29 | NY PM | 28487.5 | PDH 29794.2 AVAILABLE; PDL 29111 TAKEN·? | -0.91 | DOWN (3) · DOWN | NY AM H 23.0 · — | BSL 9.3 · SSL 2.1 | Asia L SWEEP, London L SWEEP, NY AM L BREAK | none (censored) |
| 8 | MNQZ2026 10-14 01:59 | London | 30752.8 | PDH 30905.5 AVAILABLE; PDL 30591.2 AVAILABLE | 0.51 | DOWN (52) · DOWN | Asia H 14.9 · Asia L 0.9 | BSL 14.9 · — | — | Asia L (▼, +1 bars) |
| 9 | MNQZ2026 10-14 09:29 | NY AM | 30551.8 | PDH 30905.5 AVAILABLE; PDL 30591.2 TAKEN·SWEEP | -0.13 | DOWN (12) · DOWN | London H 21.6 · W-2 L 13.6 | BSL 21.5 · SSL 1.0 | PDL SWEEP, Asia L BREAK, London L BREAK | W-2 L (▼, +128 bars) |
| 10 | MNQZ2026 10-14 13:29 | NY PM | 30178 | PDH 30905.5 AVAILABLE; PDL 30591.2 TAKEN·SWEEP | -1.32 | DOWN (3) · DOWN | NY AM H 31.6 · W-3 L 18.0 | BSL 8.6 · — | PDL SWEEP, W-2 L BREAK, Asia L BREAK, London L BREAK, NY AM L BREAK | none (censored) |
| 11 | MNQ1! 11-02 09:29 | NY AM | 28721.5 | PDH 29180.8 AVAILABLE; PDL 28232.2 AVAILABLE | 0.52 | DOWN (2) · UP | PDH 35.8 · PDL 38.2 | BSL 9.5 · SSL 3.0 | — | PDL (▼, +318 bars) |
| 12 | MNQ1! 11-02 13:29 | NY PM | 28540 | PDH 29180.8 AVAILABLE; PDL 28232.2 AVAILABLE | 0.32 | DOWN (2) · DOWN | NY AM H 21.8 · PDL 19.1 | BSL 4.2 · SSL 3.4 | NY AM L SWEEP | PDL (▼, +78 bars) |
| 13 | MNQ1! 11-02 19:59 | Asia | 28193 | PDH 28891.5 AVAILABLE; PDL 28101.2 AVAILABLE | 0.12 | DOWN (26) · DOWN | NY PM H 24.8 · NY PM L 6.4 | BSL 3.5 · SSL 2.1 | — | none (censored) |

Prices print with one decimal (`:g`): 29881.2 = 29881.25. "TAKEN·?" = beyond, but the first take happened where nothing was observed (TARGET_UNIVERSE §2).

## 4 · The requested case categories

The rules are explicit. They are applied to the decision points and to the event points of §2. A label is applied *after the fact*; it is OUTCOME, never FEATURE.

| category (request) | rule | found |
|---|---|---|
| **clear bearish delivery** | an AVAILABLE external ▲ target swept, then the nearest external ▼ target reached first | **NOT FOUND** (0 events) |
| **clear bullish delivery** | the mirror | **NOT FOUND** (0) |
| **mixed** | both sides' nearest external targets reached by the horizon | **NOT FOUND** at the decision points (0 / 13). External targets were AVAILABLE on *both* sides at 10 / 13 points (B4 abstained 10 times) |
| **wrong obvious heuristic** | B1 (the nearest of any class) picked side X; the first external target reached was on the other side | **2 / 13**: #4 NQ1! 10-28 01:59, B1 → SSL 29901.5, Asia H (▲) reached first. #5 MNQZ2026 10-30 01:59, B1 → BSL 29041.75, Asia L (▼) reached first |
| **CISD conflict** | a 1m CISD against the 15m CISD state | **85 events** (10 distinct outcomes). The CISD's own side was first in 19 of them; driftless reference 38.7. At the decision level, #3 (1m DOWN / 15m UP → ▲ first) and #11 (1m DOWN / 15m UP → ▼ first): one each way |
| **IFVG conflict** | an inversion against the 1m CISD state at that bar | **93 events** (11 distinct outcomes). The IFVG's side was first in 61; reference 47.5 |
| **displacement without continuation** | the next external target reached is on the displacement's *other* side | **28 events** (9 distinct outcomes). For example, NQ1! 10-27 18:02, a bearish displacement at close 29785.5; next: NY PM H 29881.25 (▲) before NY PM L 29755.75 (▼) |
| **external sweep without reversal** | an external target swept, then the same side's next external target reached first | **3 events** (3 distinct), all on the ▼ side. MNQZ2026 10-30 05:47 London L 28882 swept → Asia L 28820.25 first. MNQZ2026 10-14 08:35 PDL 30591.25 swept → W-2 L 30356.5 first. MNQ1! 11-02 12:10 NY AM L 28634.5 swept → PDL 28232.25 first |
| (also) external break, continuation | an external target broken, then the same side first | **2 events** (1 distinct): MNQZ2026 10-14 02:00 Asia L broken, 08:30 London L broken → PDL first |

**Closest real examples of the two "clear" categories**, described with no rule claimed:
* **Bearish, MNQ1! 11-02.**
  * At NY AM (#11), price sat mid-range: pos 0.52, PDH 35.8 and PDL 38.2 TR averages away.
  * The 1m state was DOWN and the 15m state UP.
  * PDL 28232.25 (= PWL, one pool) was reached 318 bars later. From NY PM (#12) it was reached 78 bars later, after an NY AM L sweep at 12:10.
  * There was **no prior external ▲ sweep**: a bearish delivery day without the textbook first step.
* **Bullish, NQ1! 10-27 evening → 10-28.**
  * At 19:59 (#3) the 1m state was DOWN and the 15m state UP.
  * NY PM H = PDH (one pool) was reached ▲ after 102 bars, as a BREAK.
  * At London (#4), Asia H was reached ▲ after 42 bars.
  * That is continuation through *breaks*, not a sweep and reversal.

## 5 · Baselines B0…B4 (definitions: DOL_RESEARCH §9)

| baseline | decisions | abstain | PRIMARY_REACHED | OPPOSITE_REACHED_FIRST | BOTH_SAME_BAR_UNRESOLVED | UNRESOLVED | CENSORED | resolved: reached first · driftless reference | bars to the target (median) |
|---|---|---|---|---|---|---|---|---|---|
| B0 nearest external | 13 | 1 | 5 | 5 | 0 | 0 | 2 | 5/10 · 5.0 | 78 |
| B1 nearest, any class | 13 | 0 | 9 | 3 | 0 | 0 | 1 | 9/12 · 10.0 | 3 |
| B2 nearer of PDH / PDL | 13 | 2 | 2 | 7 | 0 | 0 | 2 | 2/9 · 2.5 | 90.0 |
| B3 highest timeframe | 13 | 0 | 5 | 6 | 0 | 0 | 2 | 5/11 · 3.8 | 128 |
| B4 abstain if external both sides | 13 | 10 | 0 | 3 | 0 | 0 | 0 | 0/3 · 0.5 | — |

**Reading.**
* Every baseline lands on its distance-implied reference, within what 9–12 decisions can resolve.
* B1's high hit count is its proximity: the median target was 3 bars away.
* Nothing here ranks the baselines. It shows **why "reached first" must be read against the reference.**

## 6 · Facts → the first external target reached

| fact (frozen event) | events | external targets both sides | resolved | first external reached on the event's side | driftless reference | distinct outcomes |
|---|---|---|---|---|---|---|
| CISD (1m) | 317 | 222 | 171 | 88 (51%) | 52% | 12 |
| IFVG inversion | 622 | 429 | 326 | 168 (52%) | 56% | 12 |
| LRL break | 26 | 16 | 15 | 8 (53%) | 49% | 6 |
| LRL drift | 14 | 8 | 7 | 2 (29%) | 48% | 5 |
| LRL sweep | 26 | 14 | 6 | 2 (33%) | 59% | 5 |
| Phase 2 break | 104 | 64 | 47 | 30 (64%) | 65% | 9 |
| Phase 2 sweep | 128 | 85 | 66 | 54 (82%) | 64% | 10 |
| displacement | 110 | 71 | 59 | 31 (53%) | 57% | 11 |
| external break | 11 | 5 | 2 | 2 (100%) | 65% | 1 |
| external sweep | 5 | 3 | 3 | 3 (100%) | 54% | 3 |

"Distinct outcomes" counts the different (segment, reaching bar, side) results. **317 CISDs carry 12 independent answers.**

## 7 · CISD timescale

| segment | CISDs 1m (bars ≥ 200) | median bars between 1m CISDs | CISDs 15m | bars with 1m state = 15m state (both known) |
|---|---|---|---|---|
| NQ1! 2026-10-27 03:38 → 10-28 07:56 | 103 | 10.0 | 14 | 768/1439 (53%) |
| MNQZ2026 2026-10-29 19:56 → 10-30 15:43 | 71 | 9.5 | 9 | 530/840 (63%) |
| MNQZ2026 2026-10-13 19:57 → 10-14 13:52 (Bar Replay) | 77 | 8.0 | 6 | 433/876 (49%) |
| MNQ1! 2026-11-02 04:16 → 23:11 | 66 | 11 | 3 | 442/876 (50%) |

## 8 · What this data cannot answer

* Any regime question: there are ≤ 8 completed 4H bars and no multi-day D structure per segment.
* ES; any regime stratum (trend / range / volatility / macro); session-driven day types.
* Any rate with a usable error: there are 1–12 distinct outcomes per row.
* The value of a sweep → reversal narrative: there are 0 resolved cases.

## 9 · Proposed research dataset

| item | proposal |
|---|---|
| instruments | NQ1! (MNQ1! as the same underlying) and ES1!, **separately**, never pooled. Back-adjustment and the dated contract at rolls are recorded |
| unit | the trading day 18:00 → 17:00 ET. **Only complete days**, so every target is VERIFIED from its `since`, plus the prior week for PWH / PWL (or the HTF bars that cover it) |
| chart timeframe | 1m for the frozen engines (or 5m for the context layer alone: 1,000 bars ≈ 3.6 days per capture, at the cost of more same-bar outcomes; decision D-CX9) |
| HTF bars | 15m, 30m, 1H, 4H, 1D, captured on their own charts. 1,000 bars ≈ 11 days of 15m, ≈ 43 days of 1H, ≈ 33 weeks of 4H, ≈ 4 years of 1D. HTF data is cheap; 1m is the bottleneck |
| size | **≥ 60 complete days per instrument** for a first descriptive evaluation (≈ 180 session-open decisions; a 50% rate's standard error ≈ 3.7 points). **≥ 250 days** before any definition decision rests on it (≈ 1.8 points). Effective n is nearer the distinct outcomes (≈ 1–3 per day) than the decision count |
| selection | contiguous calendar blocks, never hand-picked days. Holidays, early closes and DST transitions are kept and flagged |
| strata (labels after the fact, never features; parameters fixed once, not tuned) | **TREND** day: \|close − open\| ≥ 0.6 × the day's range, else **RANGE** · **HIGH / LOW volatility**: the day's range ≥ 1.5× / ≤ 0.67× the median of the previous 20 days · **macro** day: from a calendar the user supplies (CPI, FOMC, NFP, …), never scraped · **Asia- / London-driven**: the day's high or low printed in that window · **NY reversal / continuation**: NY AM takes one London extreme first; the day closes on the opposite / same side of the NY open |
| sources (user decision; TradingView is never automated or scraped) | (a) more Pine-Log captures with the existing CAPTURE mechanism: exactly TradingView's data. Bar Replay reaches past dates (as 10-14 and 10-30 did). About 1.4 1m captures per day, so ~85 captures for 60 days; laborious. (b) A user-supplied OHLC export from a source the user is licensed for, checked against an overlapping TradingView capture (0 differences) before use. (c) Option (a) on 5m |
| record per case | FEATURES_AT_T (the universe with status and identities, ranges and positions, per-timeframe CISD states, facts with identities) and OUTCOME_AFTER_T (labels per hypothesis and baseline, reach bars, censoring), stored **separately** |
