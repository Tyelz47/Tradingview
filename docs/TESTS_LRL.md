# IST · LRL tests — v0.5.3-dev (EXPERIMENTAL)

**Status.** Automated validation: PASS, FULL (totals in `CHANGELOG.md`). TradingView: **LRL-L00 PASS** (v0.5.1-dev, user, 2026-10-29); every other LRL-L test PENDING. They are recorded only from the user's results, never assumed. LRL is frozen only after **LRL-L11** (real Pine ↔ oracle parity) gives **0 DIFFERENCE**.

**Build:** `src/IST.pine` v0.5.3-dev (branch `lrl/pine`). v0.5.3-dev draws one straight line per LRL (user, 2026-10-29); no polyline.

**v0.7.1-dev:** IST v0.5.0-dev … v0.7.0-dev read the TR average inside `seed` / `fits` (`lrlTra[bar_index - xa]`). Inside a function that does not run on every bar, Pine returns the value of an earlier CALL, not the earlier bar, so τ and the separation check used wrong TR averages (the first divergence: the LRL LOW anchored 2026-10-29 23:33, τ 5.88 instead of 7.22; with Pine's logged τ injected the oracle loses 260 of the 330 differences). v0.7.1-dev records the TR average of every closed bar at global scope (`lrlTraBuf`) and reads the anchor's value from it (`f_lrlTraAt`); ST-21 forbids the construct. The definition is unchanged. **LRL-L11 needs a new capture with v0.7.1-dev.**

**History:** v0.5.0-dev LRL-L00 **FAIL** (user, 2026-10-28): CE10182, an overloaded `advance` (FVG + LRL). Fixed in v0.5.1-dev (LRL method renamed `advanceLrl`; ST-18).
* v0.5.1-dev: LRL-L00 compile **PASS** (user, 2026-10-29).
* v0.5.1-dev runtime with **Show historical LRL ON: FAIL** (user): "Error on bar 11241: The requested historical offset (1231) is beyond the historical buffer's limit (1230)" in `f_lrlDraw` (bar_index polyline). The `time` series' history was too short for historical bar_index drawings.
* Fixed in v0.5.2-dev: `max_bars_back(time, 5000)`, pinned by ST-17. Retest pending: Show LRL ON + Show historical LRL ON, NQ1! 1m, a long history. The definition is in `docs/LRL.md`.

## Automated (before TradingView)

| id | what | where | result |
|---|---|---|---|
| S-LRL-1 | the 9 frozen constants equal the oracle; 30 formulas line by line; ADVANCE before JUDGE; extend → confirm → seed | ST-17 | PASS |
| S-LRL-2 | 22 definition mutations each caught (5/3, τ, G, separation, non-horizontal, previous boundary, DRIFT inequality, order, spent reuse, …) | `tests/test_lrl_pine.py` | PASS |
| S-LRL-3 | Pine event names = oracle event names, whole family, no exception | ST-14 | PASS |
| S-LRL-4 | the LRL engine names no Phase 1 / 2 state and reads no [view] input | `tests/test_lrl_pine.py`, ST-01, ST-06 | PASS |
| S-LRL-5 | the Parity capture writes every LRL key the parser reads; warm-up = 76 from the dependencies | `tests/test_parity_lrl.py` | PASS |
| S-LRL-7 | no user function / method name declared twice (Pine CE10182) | ST-18 | PASS |
| S-LRL-6 | bounded LRL parity: 0 DIFFERENCE on faithful synthetic captures; 8 kinds of error detected | `tests/test_parity_lrl.py` | PASS |

## TradingView procedure (NQ1! 1m unless stated; Confirmed only ON)

Before you start: in the Pine Editor, replace the code with `src/IST.pine` v0.5.3-dev, save it, and add it to an NQ1! 1m chart.

| id | test | how | expected |
|---|---|---|---|
| LRL-L00 | compile and runtime | add the indicator; open the Pine Logs and the status line | no compile error, no runtime error ("max_bars_back", loop, memory), chart loads |
| LRL-L01 | inputs | Settings → group **LRL · DIAGONAL LIQUIDITY** | exactly: Enable LRL engine ✓, Show LRL ✓, Show historical LRL ☐, Show lifecycle markers ☐. In DEVELOPER: Inspect LRL = 0, Draw LRL candidates ☐. No pivot / τ / gap / separation inputs anywhere |
| LRL-L02 | visual | look at the chart | at most one active LRL per side: ONE thin straight diagonal from the first to the latest failure swing (magenta on highs, cyan on lows), no bend at intermediate swings, continuing as a fainter dashed line on the same slope, with no kink, while active; a small "LRL" label. No horizontal LRL. No 2-point lines |
| LRL-L03 | debug state | Debug mode ON; rows 35–41 (bottom right) | row 35 `ON · pivots left 3 · right 2 (no significance test) · τ = max(EQ 4 ticks, 0.5 × TR(14) …) · gap ≤ 30 · pullback ≥ 1 × TR · drop > 2τ · candidates 25 · memory 50/side`. Rows 36–37: counts per side. Rows 38–40: the newest LRL (status, points, τ, anchor → latest, boundary now · previous). Row 41: drawn counts |
| LRL-L04 | confirmation bar, no early drawing | Bar Replay: step bar by bar up to an LRL's 3rd pivot | nothing appears before the close of the 3rd pivot's bar + 2. Row 39's "confirmed" = that bar. When a later swing extends it, the straight line is redrawn first → new latest from that bar on |
| LRL-L05 | extension / ending | Bar Replay through an LRL's life, Show historical + markers ON | a 4th compatible pivot extends it (row 38 points +1; row 40's boundaries move from the next bar). It ends once: D, S, B or E, never relabelled. For a D: the tooltip shows high > boundary but ≤ previous bar's boundary |
| LRL-L06 | visibility never changes calculation | note rows 36–37; toggle Show LRL, Show historical, markers, candidates | rows 36–37 identical in every combination |
| LRL-L07 | Phase 1 / Phase 2 unchanged | note rows 2–4 and 22–27; set Enable LRL engine OFF | rows 2–4 and 22–27 identical with LRL ON and OFF; with OFF, row 35 says OFF and no LRL is drawn |
| LRL-L08 | objects and time | Show historical ON, Draw LRL candidates ON (Debug ON); max bars; also 3m and 5m | no object-limit warning (row 13, row 41 LRL lines ≤ ~44); no timeout. Note the Pine Profiler time if available |
| LRL-L09 | timeframes | NQ1! 3m and 5m | runs; fewer LRLs; same behaviour |
| LRL-L10 | Live mode | Confirmed only OFF, on a live session | LRL changes only at bar close (rows 36–37 and drawings do not change intrabar, except the projection following the current bar) |
| LRL-L11 | **Pine ↔ oracle parity (freeze criterion)** | Confirmed only ON, Balanced, Debug can stay OFF. DEVELOPER → Parity capture ON, N = **1000**. Wait for `END\|bars=1076` in Pine Logs, save the logs (CSV) into `validation/parity/`, run `python -m validation.parity --capture validation/parity/<file>.csv`. Then capture OFF | the CAPTURE line has `lrl=1 … warmup=76`; **1,076 BAR lines** (1,000 + 76 warm-up). The report has an `LRL` section. **0 DIFFERENCE** over LRL events (type, side, id, bar, price, τ, points, boundaries) and per-bar boundaries / candidate counts, and the Phase 1 / 2 sections still 0 DIFFERENCE. NOT OBSERVABLE (expected, see below) |
| LRL-L12 | alerts | an existing "Any alert() function call" alert | delivers exactly what it did in v0.4.4-dev: there are no LRL alerts in v0.5.x |

**NOT OBSERVABLE in LRL-L11** (bounded window; the oracle starts empty at the first captured bar):
* LRLs whose first point is in the first 14 captured bars (their τ needs the TR average there) or before the capture;
* any LRL sharing a pivot with such an LRL, in either stream, transitively;
* LRL memory drops;
* candidate counts before bar 76, while such an LRL is active, and for 2 × 30 + 2 bars after one of its points.

**Not covered by any parity:** rendering, Live mode, alerts, object and time budgets, reload behaviour. These are LRL-L02 … L10 and L12, checked by eye.
