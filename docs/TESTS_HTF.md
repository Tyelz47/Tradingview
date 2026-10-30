# IST · HTF FVG tests — v0.6.2-dev (EXPERIMENTAL)

**Status.** Automated validation: see `CHANGELOG.md`. TradingView: every HTF-L test **PENDING**. They are recorded only from the user's results, never assumed. HTF FVG is frozen only after **HTF-L12** (real Pine ↔ oracle parity) gives **0 DIFFERENCE**.

**Build:** `src/IST.pine` v0.6.2-dev (branch `lrl/pine`). Definition: `docs/HTF_FVG.md`. v0.6.0-dev compiles and runs on TradingView (user, 2026-10-30; HTF-L00 for v0.6.0-dev); v0.6.1-dev and v0.6.2-dev change styling only (label size and colour, LRL line colour; v0.6.2-dev: the grey-brown HTF palette).

## Automated (before TradingView)

| id | what | where |
|---|---|---|
| S-HTF-1 | 8 `request.security` calls: 2 period levels + one per timeframe 15m … 1W, all `lookahead_on`; `f_htfPack()` reads nothing newer than `[1]` | ST-03 |
| S-HTF-2 | the 3 constants equal the oracle; 19 timing / definition lines; per-bar order (LRL → HTF; invalidate → create → milestones) | ST-19 |
| S-HTF-3 | 18 mutations caught (lookahead_off, candle 3 = unfinished bar, `[0]`, unshifted TR, thresholds at candle 3, chart-close invalidation, origin at candle 3, retroactive touches, …) | `tests/test_htf_pine.py` |
| S-HTF-4 | Pine event names = oracle names; HTF events go through `f_emitHtf` (timeframe in `Event.tf` and the text) | ST-14, `tests/test_htf_pine.py` |
| S-HTF-5 | Module B names no Phase 1 / 2 / LRL state and reads no [view] input in L3; renderer rules D1, D6–D10; settings target | ST-01, ST-06, `tests/test_htf_pine.py` |
| S-HTF-6 | oracle: timing, D2, D5, D8, seeds, memory, identity, session alignment (DST), other modules identical, prefix invariance | `tests/test_htf_fvg.py` |
| S-HTF-7 | invariants INV-HTF-01 … 08, each with a negative test | `invariants.py`, `tests/test_invariants.py` |
| S-HTF-8 | properties: invariants, mirror, translation, no lookahead, reload consistency, other modules untouched, long walks | `fuzz/test_htf_properties.py` |
| S-HTF-9 | bounded HTF parity: 0 DIFFERENCE on faithful synthetic captures; 8 kinds of error detected | `tests/test_parity_htf.py` |

## TradingView procedure (NQ1! 1m unless stated; Confirmed only ON)

Before you start: in the Pine Editor, replace the code with `src/IST.pine` v0.6.2-dev, save it, and add it to an NQ1! 1m chart. Debug mode rows 42–44 show the HTF engine, its registries and the drawn boxes.

| id | test | how | expected |
|---|---|---|---|
| HTF-L00 | compile and runtime | add the indicator; open the Pine Logs and the status line | no compile error, no runtime error, the chart loads |
| HTF-L01 | settings target | open the settings | group HTF FAIR VALUE GAPS: Show HTF FVGs ON; 15m 30m 1H / 4H 1D 1W ON; Show timeframe labels ON. FVG · DISPLAY: Show FVGs **OFF** (no 1m FVG boxes) |
| HTF-L02 | timing (no repaint) | Bar Replay on 1m; find a 15m gap (candles 09:30 / 09:45 / 10:00); step bar by bar from 10:00 | no box (and no `HTF_FVG_CREATED` in Pine Logs, Debug ON) on any bar before 10:15; the box appears on the 10:15 bar |
| HTF-L03 | origin (D8) | the same zone | the box's left edge is at 09:30 (candle 1), its edges at high(09:30) / low(10:00) (bull) |
| HTF-L04 | labels | look at several zones | `15m Fair Value Gap` … `1W Fair Value Gap`, bottom-right inside the box, small neutral grey, immediately readable but not dominant (v0.6.1-dev), the same placement for all; Developer "Compact HTF labels" → `15m FVG`. Note if a very thin zone clips its text |
| HTF-L05 | caps (D6) | Debug row 44 | at most one zone above and one below price per shown timeframe, ≤ 12 boxes |
| HTF-L06 | toggles are view-only | switch 15m OFF, then Show HTF FVGs OFF | the 15m boxes (then all) disappear; Debug row 43 (registries) does not change |
| HTF-L07 | own-timeframe invalidation (D5) | Bar Replay through a 1m close beyond a 1H / 4H zone that closes back inside on its own timeframe | the zone stays; it is invalidated (`HTF_FVG_INVALIDATED … tf=4H`) only on the first bar after a 4H candle closed beyond it |
| HTF-L08 | full fill | Bar Replay until a wick reaches a zone's far edge | the box is no longer drawn from that bar; `HTF_FVG_FULL_FILL` once |
| HTF-L09 | overlaps (D1) | a 15m zone inside a 1H / 4H zone | both drawn, the 15m one on top; nothing merged |
| HTF-L10 | session alignment | Debug row 43 "last HTF bar"; compare with the 4H / 1D / 1W charts | 4H at 18 / 22 / 02 / 06 / 10 / 14 ET, 1D at 18:00 ET, 1W Sunday 18:00 ET |
| HTF-L11 | reload consistency | note several zones (ids in Pine Logs); reload the chart, then scroll back / change the history window | the same zones with the same ids, edges and states; older ones may come back as `HTF_FVG_SEEDED` |
| HTF-L12 | **real parity (freeze gate)** | Developer → Parity capture ON (300 bars); save the Pine Logs as `validation/parity/pine_capture_htf.csv`; run `python -m validation.parity --capture validation/parity/pine_capture_htf.csv` | **0 DIFFERENCE**, the HTF section included (candles, events, open records) |
| HTF-L13 | other chart timeframes | 3m, 5m, 15m, 1H charts | no error; on 15m the 15m timeframe is inactive (Debug row 43), on 1H 15m / 30m / 1H are |
| HTF-L14 | objects and time | Debug row 13; Pine profiler if available | no object warning; load time noted |

Record results here (date, build, PASS / FAIL, the exact message or screenshot for a FAIL):

| id | date | build | result | notes |
|---|---|---|---|---|
