# IST — Phase 2 acceptance tests (liquidity engine, v0.4.0-dev)

Definitions: docs/LIQUIDITY.md (DEF-L1…L7). Phase 1 tests: docs/TESTS.md (unchanged).

**Status rules.**
* Only results you run in TradingView become PASS/FAIL.
* Anything that needs TradingView stays **PENDING MANUAL VALIDATION** until then. Pending never counts as passed.
* "NOT TESTABLE HERE" marks checks that cannot be run in this environment.

## Score

| Kind | Total | PASS | FAIL | Pending |
|---|---|---|---|---|
| S · static / model (run here on v0.4.0-dev) | 10 | 10 | 0 | 0 |
| L · TradingView runtime | 35 (L00–L34) | 0 | 0 | 35 |

**Phase 2 is not complete:** no runtime test has been run.

---

## S · Static and model checks (executed here)

| ID | Check | Method | Status |
|---|---|---|---|
| S-01 | No [view]/[alert] input or view-derived value in L1–L5 or the engine run | Scripted scan over the L1→L3 sections and the engine run, with all [view]/[alert] identifiers (Phase 1 + 14 new). The only 2 hits are the Phase 1 `policyBar`/`policyTime` accessors (`switch fvgMitRule`), identical to v0.3.2 and called only from L6/L7 | **PASS** |
| S-02 | No leftover identifiers from removed features | grep (`fvgOn`, `bullOpen`, `f_qualifies`, sequential ids). `ta.atr` appears only in a comment | **PASS** |
| S-03 | Exactly 2 `request.security` calls | grep = 2 | **PASS** |
| S-04 | Debug adds no drawing objects: 18/18 plots are `display.data_window`; no `line/box/label.new` exists because of `dbgOn` | grep | **PASS** |
| S-05 | FVG rule unchanged: one `Fvg.new`; `bullCand = rawBull and gapPass`, `bearCand = rawBear and gapPass` | grep | **PASS** |
| S-06 | Phase 1 diff is display/text only | `git diff PHASE1_BASELINE_v0.3.2`: the only removed lines are the header, 2 tooltips, `f_evName` signature, the `f_evText` suffix line, the alert key, the table size and the "Last events" row index (LIQUIDITY.md §7). No Phase 1 logic line was changed | **PASS** |
| S-07 | The algorithm satisfies DEF-L1…L6 | `python tests/liq_model.py`. The reference model mirrors the Pine engine bar by bar. Results: 19 scenario checks PASS (see the "Model" column below). Fuzz on 20,000-bar random walks, 4 seeds, Balanced: every event fires at most once per (kind, side, id); CREATED exactly at swing + right; TAKEN strictly after confirmation; exactly one of SWEEP/BREAK, on the taking bar; EQ members within tolerance and inside the reference; the pool is untraded from the first member's confirmation until its take; **trigger gate ON = full scan** (identical event lists). *This checks the algorithm, not Pine* | **PASS** |
| S-08 | The renderer never writes liquidity state | Scan of the L6 liquidity functions and run block: no `:=` on record fields, no `step/register/take/cluster/trigger`, no `f_emit` | **PASS** |
| S-09 | One creation path | 1 `Liq.new` (in `register`), 1 `EqCluster.new` (in `cluster`), `register` called only from the engine run (BSL + SSL) | **PASS** |
| S-10 | Scope | No CISD, displacement, IFVG, HTF FVG, SMT, score, confluence or LRL identifiers in code | **PASS** |

---

## L · Runtime acceptance (TradingView)

Setup for all tests unless stated otherwise:
* NQ1! 1m, standard candles.
* Default settings, **Debug mode ON**.
* Data Window open.
* The liquidity inspector is set by "Inspect liquidity level (0 = newest)".

| ID | Test | Procedure → expected | Model | Status |
|---|---|---|---|---|
| L00 | Compiles | Save → Add to chart → **0 errors, 0 warnings**. Report every message verbatim | — | PENDING MANUAL VALIDATION |
| L01 | Swing high known only after the right bars | Pick a swing high X. On bars X … X+2 the Data Window "LIQ swing high judged here" is 0. On **X+3** (Balanced: right = 3) it is 2 (or 1 if rejected). The inspector shows `swing → known` = X → X+3. `BSL_CREATED` time = X+3 | s_confirmation_timing | PENDING MANUAL VALIDATION |
| L02 | Swing low: same behaviour | Mirror of L01 with "LIQ swing low judged here" and `SSL_CREATED` | s_ssl_mirror | PENDING MANUAL VALIDATION |
| L03 | BSL at the correct price | Inspector price = the high of bar X exactly (hover the candle) | s_confirmation_timing | PENDING MANUAL VALIDATION |
| L04 | SSL at the correct price | = the low of bar X exactly | s_ssl_mirror | PENDING MANUAL VALIDATION |
| L05 | Hidden BSL/SSL stay logically active | BSL and SSL display OFF → debug rows 23/24 (counts, memory) unchanged; the inspector still shows the levels; events still logged | — | PENDING MANUAL VALIDATION |
| L06 | The visual limit doesn't change state | Note rows 22–25 and Last events. Max active visible 5 → 1, EQ max 3 → 0, taken max 2 → 0 → the same numbers and events; only row 26 changes | — | PENDING MANUAL VALIDATION |
| L07 | BSL taken once | A BSL traded through on several bars → exactly one `BSL_TAKEN` for that id, on the first bar with high > level | s_repeated_attacks_fire_once | PENDING MANUAL VALIDATION |
| L08 | SSL taken once | Mirror | s_ssl_mirror | PENDING MANUAL VALIDATION |
| L09 | BSL wick-through + close below = SWEEP | The taking bar closes below the level → `BSL_TAKEN` + `BSL_SWEEP` on that bar; Data Window BSL take = 1 | s_wick_through_close_back_is_sweep | PENDING MANUAL VALIDATION |
| L10 | SSL wick-through + close above = SWEEP | Mirror; SSL take = 1 | s_ssl_mirror | PENDING MANUAL VALIDATION |
| L11 | BSL close above = BREAK | `BSL_TAKEN` + `BSL_BREAK`; take = 2 | s_close_beyond_is_break | PENDING MANUAL VALIDATION |
| L12 | SSL close below = BREAK | Mirror | s_ssl_mirror | PENDING MANUAL VALIDATION |
| L13 | Never both SWEEP and BREAK for one take | For 10 taken levels (inspector #0…#9 or the event log): exactly one class each, on the taking bar; a later reclaim doesn't relabel | s_break_then_reclaim_stays_break | PENDING MANUAL VALIDATION |
| L14 | No event before confirmation | For 5 levels: no event with that id before X + right | fuzz invariant | PENDING MANUAL VALIDATION |
| L15 | Realtime confirmed state matches reload | Watch ≥ 30 live bars with ≥ 2 liquidity events; note the event times, classes and rows 22–25 → reload → identical | — | PENDING MANUAL VALIDATION |
| L16 | Repeated touches don't duplicate | A level hit by exact touches on several bars → `touches` grows, no event; after the take, more attacks → no event | s_exact_touch_is_not_taken, s_repeated_attacks_fire_once | PENDING MANUAL VALIDATION |
| L17 | EQH within tolerance | Two significant highs ≤ 4 ticks apart, with no trade above the higher one in between → `EQH_CREATED`, `EQH ×2` line at the **higher** price. Check both cases: second lower, and second higher (the first then shows TAKEN+SWEEP by 1–4 ticks, correctly) | s_eqh_second_lower…, s_eqh_second_higher… | PENDING MANUAL VALIDATION |
| L18 | EQL within tolerance | Mirror (line at the **lower** price) | (mirror logic) | PENDING MANUAL VALIDATION |
| L19 | Outside tolerance → no cluster | Two highs 5+ ticks apart → two BSL, no EQH | s_outside_tolerance_no_cluster | PENDING MANUAL VALIDATION |
| L20 | No duplicate clusters | A third equal high → `EQH ×3` on the same line; still one `EQH_CREATED` | s_cluster_does_not_duplicate… | PENDING MANUAL VALIDATION |
| L21 | Taken EQH/EQL state | Price trades above the EQH line → one `EQH_TAKEN` on that bar (with the member BSL takes); the line disappears; the inspector on a member shows "EQ: … · taken" | s_cluster_does_not_duplicate… | PENDING MANUAL VALIDATION |
| L22 | NQ 1m performance | Max bars loaded; Pine Profiler → total time well under the limit; no "script takes too long" error. Note the time; also note the levels per side per session (row 22) for the Balanced-default review | — | PENDING MANUAL VALIDATION |
| L23 | NQ 3m works | L01, L09, L11, L17 spot checks | — | PENDING MANUAL VALIDATION |
| L24 | NQ 5m works | Same as L23 | — | PENDING MANUAL VALIDATION |
| L25 | Object limits safe | All display caps at their maximum (Phase 1 + liquidity) → no orange object warning, or the warning appears before any loss; row 13 counts < 500 | — | PENDING MANUAL VALIDATION |
| L26 | Debug state correct | For 3 inspected levels (one active, one swept, one broken), verify every inspector field by hand on the chart | — | PENDING MANUAL VALIDATION |
| L27 | Phase 1 regression | Re-run Phase 1 T00, T01, T02, T09–T13 (previously PASS) and T03/T03a on v0.4.0-dev → same results as v0.3.2. Also run **L31** | — | PENDING MANUAL VALIDATION |
| L28 | Exact tick touch is not a take | A bar whose high equals a BSL exactly → no event; the inspector's touches +1 | s_exact_touch_is_not_taken | PENDING MANUAL VALIDATION |
| L29 | Close exactly at the level = SWEEP | Wick through, close == level → SWEEP | s_close_exactly_at_level_is_sweep | PENDING MANUAL VALIDATION |
| L30 | Gap through | E.g. the 18:00 ET reopen beyond a level → TAKEN "opened beyond", class by close | s_gap_through | PENDING MANUAL VALIDATION |
| L31 | Liquidity OFF = Phase 1 only | Enable liquidity engine OFF → no liquidity lines, labels, events or alerts; FVG/levels/sessions identical to v0.3.2 on the same chart (compare against the baseline script added as a second indicator) | — | PENDING MANUAL VALIDATION |
| L32 | Presets are the documented numbers | Switch Aggressive / Balanced / Strict / Custom → row 21 shows 3/2/0.5, 5/3/1.0, 10/5/2.0, the custom values | — | PENDING MANUAL VALIDATION |
| L33 | Rejected swing is not liquidity | A pivot with Data Window verdict 1 → no event, no line; its reaction < required in the Data Window | s_significance_filter | PENDING MANUAL VALIDATION |
| L34 | No duplicate line on reference levels | A swing high equal to a visible PDH or session high → only the reference line is drawn; row 26 "on a reference line" ≥ 1; the inspector still shows the BSL | — | PENDING MANUAL VALIDATION |

---

## Manual validation procedure

1. **Keep the baseline next to the build.** Add `releases/v0.3.2/src/IST.pine` as a second indicator named "IST v0.3.2", which is needed for L27/L31. Paste `src/IST.pine` (v0.4.0-dev) as a new indicator.
2. **L00:** Save. Report every compiler message verbatim. If there are errors, stop: they come back here before anything else.
3. **Chart:** NQ1! 1m, standard candles, maximum history. Turn Debug ON (DEVELOPER) and open the Data Window.
4. **Swings (L01–L04, L33):** pick a clear swing high and walk the cursor from the swing bar forward: the verdict appears only on swing + 3. Read the inspector (set "Inspect liquidity level" until it shows that swing). Repeat for a low and for a rejected pivot (verdict 1).
5. **Takes (L07–L13, L16, L28–L30):** use the event log (debug row 31) and the inspector on taken levels. For each class, hover the taking bar and compare its high/low/close with the level.
6. **EQ (L17–L21):** find an `EQH ×2` line. The inspector on both members shows the same EQ. Check the tolerance in ticks with the price difference. Wait for, or find, a take.
7. **State versus display (L05, L06, L31):** toggle displays and caps; rows 22–25 and the events must not change.
8. **Realtime (L15):** in a liquid session, leave the chart open for ≥ 30 bars; write down the events; reload; compare.
9. **Timeframes and resources (L22–L25):** Pine Profiler on 1m; spot checks on 3m/5m; object test with every cap at its maximum.
10. **Phase 1 regression (L27):** re-run the Phase 1 tests that passed, plus T03/T03a, on v0.4.0-dev, and compare with "IST v0.3.2" on the same chart.
11. **Report** each test as PASS/FAIL with a screenshot of the Data Window or inspector for each FAIL. Report the row-22 numbers from L22 (pivots → levels per side over a session): they are the input for any decision about the Balanced defaults.

**Rollback** at any time:

```bash
git checkout PHASE1_BASELINE_v0.3.2 -- src/IST.pine
```

Alternatively, paste `releases/v0.3.2/src/IST.pine`. To verify the copy, run `sha256sum -c SHA256SUMS.txt` inside `releases/v0.3.2/`.
