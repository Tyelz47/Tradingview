# IST · Manual verification package: G-V1 … G-V5 and T19 … T22

**Status: every gate PENDING.** These are TradingView checks for the user. Nothing here is marked PASS until the user reports the result (D-TU1, D-TU3).
* Why they matter: until they pass, the target universe keeps PDH / PDL / PWH / PWL (G-V) and the session extremes (T19–T22) **UNVERIFIED**. Their facts are recorded; their state is never AVAILABLE or TAKEN (docs/context/TARGET_UNIVERSE_ORACLE.md DEF-TU5 / TU7).
* The "expected" values come from IST's own Pine Logs and HTF snapshot in `validation/parity/evidence/`. The check is whether TradingView's chart agrees with them.
* Chart setup for every check:
  * timezone **America/New_York (UTC−4 / −5)**;
  * IST v0.9.1-dev, Debug ON;
  * "Confirmed only" ON;
  * the symbol's default session (extended / electronic) unless the gate says otherwise.
* How to read a 1D / 1W candle: open the 1D (1W) chart of the same symbol and read the Data Window on that candle. TradingView labels a CME daily candle by its session date: the candle that opens Mon 18:00 ET is "Tue".

## G-V1 … G-V5 (the PDH / PDL / PWH / PWL source)

| gate | question validated | symbol · date · timeframe | what to inspect | expected | PASS condition |
|---|---|---|---|---|---|
| **G-V1** | On the continuous contract, are IST's PDH / PDL / PWH / PWL exactly the previous 1D / 1W candle? Does the day start at 18:00 ET and the week on Sunday 18:00 ET? | **NQ1!** · trading day **Wed 2026-10-28** · 1m and 1D | (a) the 1D candle **Tue 2026-10-27**: H / L in the Data Window. (b) On 1m, any bar of Wed 10-28 (for example 09:00 ET): IST's PDH / PDL (inspector or lines). (c) The debug rows `D source check`, `W source check`, `Day · week start (ET)` | (a) and (b): **PDH 29881.25 · PDL 29288.00** (IST's LEVEL_SET logged on the 10-27 18:00 bar). (c) 100% · 100% · `… 18:00` / `Sun … 18:00` | (a) = (b) = expected, to the tick; source checks 100%; starts at 18:00 / Sunday 18:00 |
| **G-V2** | The same on a **dated** contract | **MNQZ2026** · trading day **Fri 2026-10-30** · 1m and 1D / 1W | (a) the 1D candle Thu 2026-10-29 and the 1W candle of the week of Oct 19. (b) On 1m, any bar of Fri 10-30: IST's PDH / PDL / PWH / PWL. (c) The source-check rows | PDH **29794.25** · PDL **29111.00** · PWH **30114.00** · PWL **28986.25** (the HTF snapshot Pine logged on this contract) | (a) = (b) = expected; source checks 100% |
| **G-V3** | Over the weekend: is Monday's PDH / PDL Friday's candle, set on Sunday's 18:00 bar, with the first Asia on Sunday 20:00? | **MNQ1!** · **Mon 2026-11-02** · 1m | (a) PDH / PDL on any Monday bar. (b) The `LEVEL_SET` line in Pine Logs (or `Last events`): its bar. (c) The first `SESSION_START … Asia` of the week | (a) **PDH 29180.75 · PDL 28232.25** (= the 1D candle Fri 2026-10-30). (b) the **Sun 2026-11-01 18:00** bar. (c) **Sun 2026-11-01 20:00** | all three as expected |
| **G-V4** | Does the day still start at 18:00 ET across the DST change (Sun 2026-11-01)? | **MNQ1!** · **Fri 2026-10-30** (EDT) and **Tue 2026-11-03** (EST) · 1m | (a) PDH / PDL on Fri 10-30 and the LEVEL_SET bar. (b) PDH / PDL on Tue 11-03 and the LEVEL_SET bar. (c) The `D source check` row has no ✗ around 11-01 | (a) **29794.25 / 29111.00**, LEVEL_SET Thu 10-29 18:00. (b) **28891.50 / 28101.25**, LEVEL_SET Mon 11-02 18:00 (already in the 11-02 capture). (c) no ✗ | as expected on both sides of the change |
| **G-V5** | Does the chart's session setting change the Daily source? | **MNQ1!** · **Mon 2026-11-02** · 1m and 1D | Chart settings → Symbol → Session: note the default. Switch to the other setting offered (for example Regular / RTH) and back. Each time, read the 1D candle Mon 11-02, IST's PDH / PDL on Tue 11-03, and the source-check rows | default setting: **28891.50 / 28101.25**. Other setting: to be recorded | Under the default setting the values equal the 1D candle and the source checks are 100%. Under the other setting, the observed behaviour is **documented**. This gate is a record, not a value check |

**The minimum set** is G-V1 (a)(b)(c), G-V2 (a)(b), G-V3 (a)(b), G-V4 (a)(b) and G-V5: about 12 readings. G-V1 also needs one PWH / PWL reading on NQ1!; the value to expect is the 1W candle's own.

## T19 … T22 (session extremes)

* For each window, IST must log `SESSION_START` on the window's first bar and `SESSION_END` on the first bar **outside** it.
* The final H / L must equal the highest high and the lowest low of the bars inside the window. Check it with the Data Window, or a horizontal-line check over the window.

| test | symbol · date | window (ET) | expected `SESSION_END` | expected H · L (IST's logged values) |
|---|---|---|---|---|
| **T19** Asia | **MNQZ2026** · Thu 2026-10-29 | 20:00–00:00 | on the Fri **00:00** bar | **29131.75 · 28820.25** |
| **T20** London | **MNQ1!** · Mon 2026-11-02 | 02:00–05:00 | on the **05:00** bar | **28803.25 · 28712.75** |
| **T21** NY AM | **MNQ1!** · Mon 2026-11-02 | 09:30–12:00 | on the **12:00** bar | **28891.50 · 28634.50** |
| **T22** NY PM | **MNQ1!** · Mon 2026-11-02 | 13:30–16:00 | on the **16:00** bar | **28547.00 · 28101.25** |

**PASS** for each: the START / END bars as stated, and the chart's own highest high / lowest low over the window equal to the expected pair.

T23 (a hidden session is still calculated) and T24 (DST behaviour of the windows) are not needed for the target universe's source gate.

## Recording

* Report every reading as `gate · PASS / FAIL · the values you saw`. The tables in `docs/TESTS.md` (§G-V, T19–T22) are filled from your report only.
* When every G-V gate passes, DAILY / WEEKLY join `TargetSettings.validated`; when T19–T22 pass, SESSION does. Each is a one-line change with a test.
