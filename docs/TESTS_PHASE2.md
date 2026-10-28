# IST — Phase 2 acceptance tests (liquidity engine, v0.4.3-dev)

Definitions: docs/LIQUIDITY.md (DEF-L1…L7). Phase 1 tests: docs/TESTS.md (unchanged).

**Status rules.**
* Only results you run in TradingView become PASS/FAIL.
* Anything that needs TradingView stays **PENDING MANUAL VALIDATION** until then. Pending never counts as passed.
* "NOT TESTABLE HERE" marks checks that cannot be run in this environment.

## Score

| Kind | Total | PASS | FAIL | Pending |
|---|---|---|---|---|
| S · static / model (run here on v0.4.1-dev) | 13 | 13 | 0 | 0 |
| L · TradingView runtime | 45 (L00–L44) | 0 | 0 | 45 |

**Phase 2 is not complete.** L00 passed on v0.4.1-dev (user, 2026-10-27). v0.4.2-dev and v0.4.3-dev change debug output only: Pine Logs event lines, row 34 "Loaded history", and the Parity capture (default OFF). It is still new source, so L00 must be re-run on v0.4.3-dev.

**Runtime observation (user, 2026-10-27, NQ1! 1m, Balanced: left 5 · right 3 · k 1.0 · EQ tolerance 4 ticks · minimum touches 2).** This is an observation, not a test result. Debug rows 22–23 showed:
* Swing highs: 1182 pivots → 1129 PASS · 52 REJECT (~4.4%) · 1 warm-up → 1129 BSL created.
* Swing lows: 1215 pivots → 1169 PASS · 46 REJECT (~3.8%) → 1169 SSL created.

No DIFFERS indication appeared, and the renderer showed a limited number of levels. On real NQ data, as on noise, the Balanced reaction floor passes ~95–96% of confirmed pivots. The filter stays unchanged until Pine ↔ Python parity is verified on real data: full bar-by-bar parity from a Data Window export (paid plan), or manual event parity from the debug table and Pine Logs (free plan; weaker): `python -m validation.parity`, validation/README.md.

**Bounded Pine-Log parity (user capture, 2026-10-27, NQ1! 1m, Balanced, IST v0.4.3-dev).** This is a parity observation, not an L-test result.
* The input was TradingView's saved Pine Logs CSV: 317 bars, 10:49–16:05 New York, warm-up 17.
* Result: **PASS**. 300 bars × 7 series, and 340 events of structures born inside the window, with 0 differences.
* That window held **0 REJECT pivots**, so the REJECT branch of the reaction filter is not yet exercised. A 1,000-bar capture is next.

**Bounded Pine-Log parity, 1,000-bar capture (user, 2026-10-27 03:38 → 21:34 New York, NQ1! 1m, Balanced, IST v0.4.3-dev).** This is a parity observation, not an L-test result.
* Result: **PASS**. 1,000 bars + 17 warm-up × 7 series, and 1,258 events, with 0 differences.
* After the warm-up, Pine and the oracle agree exactly on the swings: highs 71 PASS / 7 REJECT, lows 68 PASS / 1 REJECT. This includes the REJECT branch.
* The capture is committed (`validation/studies/data/`) and preserved by `test_real_nq_capture_parity_is_preserved`.
* Conclusion: the permissiveness of Balanced comes from its definition, not from the Pine implementation. See `docs/STUDY_LIQUIDITY_SIGNIFICANCE.md`, a study awaiting review; no definition is changed.

---

## S · Static and model checks (executed here)

| ID | Check | Method | Status |
|---|---|---|---|
| S-01 | No [view]/[alert] input or view-derived value in L1–L5 or the engine run | Scripted scan over the L1→L3 sections and the engine run, with all [view]/[alert] identifiers (Phase 1 + 14 new). The only 2 hits are the Phase 1 `policyBar`/`policyTime` accessors (`switch fvgMitRule`), identical to v0.3.2 and called only from L6/L7 | **PASS** |
| S-02 | No leftover identifiers from removed features | grep (`fvgOn`, `bullOpen`, `f_qualifies`, sequential ids). `ta.atr` appears only in a comment | **PASS** |
| S-03 | Exactly 2 `request.security` calls | grep = 2 | **PASS** |
| S-04 | Debug adds no drawing objects: 18/18 plots are `display.data_window`; no `line/box/label.new` exists because of `dbgOn` | grep | **PASS** |
| S-05 | FVG rule unchanged: one `Fvg.new`; `bullCand = rawBull and gapPass`, `bearCand = rawBear and gapPass` | grep | **PASS** |
| S-06 | Phase 1 diff is display/text only | `git diff PHASE1_BASELINE_v0.3.2`: the only removed lines are the header, 2 tooltips, `f_evName` signature, the `f_evText` suffix line, the alert key, the table size and the "Last events" row index (LIQUIDITY.md §7; v0.4.1-dev: 34 rows, row 33). No Phase 1 logic line was changed | **PASS** |
| S-07 | The algorithm satisfies DEF-L1…L6 | `python tests/liq_model.py` up to v0.4.1-dev; since then the validation agent (`python -m validation`, validation/README.md), which migrated every scenario and fuzz configuration. The reference model mirrors the Pine engine bar by bar. Results (v0.4.1-dev): **26 scenario checks PASS** (18 from v0.4.0-dev, earlier reported as "19 checks" = 18 scenarios + the fuzz; plus L35–L42), see the "Model" column below. Fuzz on 20,000-bar random walks, **7 runs over 4 configurations** (Balanced defaults × 4 seeds; Aggressive with 8-tick tolerance; Strict with 3 touches; Balanced with 8 ticks, 3 touches and a 3-cluster memory for the drop path): every event fires at most once per (kind, side, id); CREATED exactly at swing + right; TAKEN strictly after confirmation; exactly one of SWEEP/BREAK, on the taking bar; EQ_TAKEN after EQ_CREATED; EQ members within tolerance and inside the boundary; the pool is untraded from the first member's confirmation until its take; **trigger gate ON = full scan** (identical event lists) in every run. *This checks the algorithm, not Pine* | **PASS** |
| S-08 | The renderer never writes liquidity state | Scan of the L6 liquidity functions and run block: no `:=` on record fields, no `step/register/take/cluster/trigger`, no `f_emit` | **PASS** |
| S-09 | One creation path | 1 `Liq.new` (in `register`), 1 `EqCluster.new` (in `cluster`), `register` called only from the engine run (BSL + SSL) | **PASS** |
| S-10 | Scope | No CISD, displacement, IFVG, HTF FVG, SMT, score, confluence or LRL identifiers in code | **PASS** |
| S-11 | EQ identity versus boundary (DEF-L5.1–L5.5) | Model scenarios L35–L42 (below) plus **per-bar invariants** in all 7 fuzz runs (140,000 bars, 3,847 clusters): a level is in at most one cluster; cluster `id` and `ref` never change; EQH boundary never decreases, EQL never increases; members only appended; a cluster is never taken on or before the bar it (or its latest member) became known; a cluster take is never rewritten; an individual level's take fields (bar, extreme, class, close) never change once set; **`bound == ref` on every bar** (DEF-L5.4: expansion unreachable through prices). Also measured: 0 clusters born within tolerance of another active cluster. Violated invariants: **none** | **PASS** |
| S-12 | v0.4.1-dev changes no liquidity output | The v0.4.0-dev model (`git show 96f7846:tests/liq_model.py`) and the v0.4.1-dev model on the same 12 walks (4 configurations × 3 seeds): **identical event logs, 149,751 events** | **PASS** |
| S-13 | The boundary is the only state-facing cluster price | grep: every cluster price read in L3/L5/L6 (join distance, take test, classification, trigger, EQ_CREATED/TAKEN/DROPPED prices, line and label) uses `bound`; `ref` is written once (creation) and read only by the debug text `f_eqTxt`. Selectivity counters: `rejects` is incremented only for judged pivots (`not na(reactReq)`), so pivots = PASS + REJECT + warm-up, and PASS = levels created | **PASS** |

---

## L · Runtime acceptance (TradingView)

Setup for all tests unless stated otherwise:
* NQ1! 1m, standard candles.
* Default settings, **Debug mode ON**.
* Data Window open.
* The liquidity inspector is set by "Inspect liquidity level (0 = newest)".

Model column: `s_<name>` is the reference-model scenario, now `test_<name>` in `validation/tests/` (the validation agent report maps every L-test to its automated logic tests).

| ID | Test | Procedure → expected | Model | Status |
|---|---|---|---|---|
| L00 | Compiles | Save → Add to chart → **0 errors, 0 warnings**. Report every message verbatim | — | PENDING MANUAL VALIDATION on v0.4.3-dev (v0.4.1-dev: **PASS**, user, 2026-10-27: compiles and runs on NQ1! 1m) |
| L01 | Swing high known only after the right bars | Pick a swing high X. On bars X … X+2 the Data Window "LIQ swing high judged here" is 0. On **X+3** (Balanced: right = 3) it is 2 (or 1 if rejected). The inspector shows `swing → known` = X → X+3. `BSL_CREATED` time = X+3 | s_confirmation_timing | PENDING MANUAL VALIDATION |
| L02 | Swing low: same behaviour | Mirror of L01 with "LIQ swing low judged here" and `SSL_CREATED` | s_ssl_mirror | PENDING MANUAL VALIDATION |
| L03 | BSL at the correct price | Inspector price = the high of bar X exactly (hover the candle) | s_confirmation_timing | PENDING MANUAL VALIDATION |
| L04 | SSL at the correct price | = the low of bar X exactly | s_ssl_mirror | PENDING MANUAL VALIDATION |
| L05 | Hidden BSL/SSL stay logically active | BSL and SSL display OFF → debug rows 24/25 (counts, memory) unchanged; the inspector still shows the levels; events still logged | — | PENDING MANUAL VALIDATION |
| L06 | The visual limit doesn't change state | Note rows 22–26 and Last events. Max active visible 5 → 1, EQ max 3 → 0, taken max 2 → 0 → the same numbers and events; only row 27 changes | — | PENDING MANUAL VALIDATION |
| L07 | BSL taken once | A BSL traded through on several bars → exactly one `BSL_TAKEN` for that id, on the first bar with high > level | s_repeated_attacks_fire_once | PENDING MANUAL VALIDATION |
| L08 | SSL taken once | Mirror | s_ssl_mirror | PENDING MANUAL VALIDATION |
| L09 | BSL wick-through + close below = SWEEP | The taking bar closes below the level → `BSL_TAKEN` + `BSL_SWEEP` on that bar; Data Window BSL take = 1 | s_wick_through_close_back_is_sweep | PENDING MANUAL VALIDATION |
| L10 | SSL wick-through + close above = SWEEP | Mirror; SSL take = 1 | s_ssl_mirror | PENDING MANUAL VALIDATION |
| L11 | BSL close above = BREAK | `BSL_TAKEN` + `BSL_BREAK`; take = 2 | s_close_beyond_is_break | PENDING MANUAL VALIDATION |
| L12 | SSL close below = BREAK | Mirror | s_ssl_mirror | PENDING MANUAL VALIDATION |
| L13 | Never both SWEEP and BREAK for one take | For 10 taken levels (inspector #0…#9 or the event log): exactly one class each, on the taking bar; a later reclaim doesn't relabel | s_break_then_reclaim_stays_break | PENDING MANUAL VALIDATION |
| L14 | No event before confirmation | For 5 levels: no event with that id before X + right | fuzz invariant | PENDING MANUAL VALIDATION |
| L15 | Realtime confirmed state matches reload | Watch ≥ 30 live bars with ≥ 2 liquidity events; note the event times, classes and rows 22–26 → reload → identical | — | PENDING MANUAL VALIDATION |
| L16 | Repeated touches don't duplicate | A level hit by exact touches on several bars → `touches` grows, no event; after the take, more attacks → no event | s_exact_touch_is_not_taken, s_repeated_attacks_fire_once | PENDING MANUAL VALIDATION |
| L17 | EQH within tolerance | Two significant highs ≤ 4 ticks apart, with no trade above the higher one in between → `EQH_CREATED`, `EQH ×2` line at the **higher** price. Check both cases: second lower, and second higher (the first then shows TAKEN+SWEEP by 1–4 ticks, correctly) | s_eqh_second_lower…, s_eqh_second_higher… | PENDING MANUAL VALIDATION |
| L18 | EQL within tolerance | Mirror (line at the **lower** price) | (mirror logic) | PENDING MANUAL VALIDATION |
| L19 | Outside tolerance → no cluster | Two highs 5+ ticks apart → two BSL, no EQH | s_outside_tolerance_no_cluster | PENDING MANUAL VALIDATION |
| L20 | No duplicate clusters | A third equal high → `EQH ×3` on the same line; still one `EQH_CREATED` | s_cluster_does_not_duplicate… | PENDING MANUAL VALIDATION |
| L21 | Taken EQH/EQL state | Price trades above the EQH line → one `EQH_TAKEN` on that bar (with the member BSL takes); the line disappears; on a member, inspector row 32 "EQ cluster (pool)" shows TAKEN | s_cluster_does_not_duplicate… | PENDING MANUAL VALIDATION |
| L22 | NQ 1m performance | Max bars loaded; Pine Profiler → total time well under the limit; no "script takes too long" error. Note the time; also note rows 22–23 (pivots · PASS · REJECT % · warm-up → levels created, per side) for the Balanced-default review | — | PENDING MANUAL VALIDATION |
| L23 | NQ 3m works | L01, L09, L11, L17 spot checks | — | PENDING MANUAL VALIDATION |
| L24 | NQ 5m works | Same as L23 | — | PENDING MANUAL VALIDATION |
| L25 | Object limits safe | All display caps at their maximum (Phase 1 + liquidity) → no orange object warning, or the warning appears before any loss; row 13 counts < 500 | — | PENDING MANUAL VALIDATION |
| L26 | Debug state correct | For 3 inspected levels (one active, one swept, one broken), verify every inspector field by hand on the chart | — | PENDING MANUAL VALIDATION |
| L27 | Phase 1 regression | Re-run Phase 1 T00, T01, T02, T09–T13 (previously PASS) and T03/T03a on v0.4.1-dev → same results as v0.3.2. Also run **L31** | — | PENDING MANUAL VALIDATION |
| L28 | Exact tick touch is not a take | A bar whose high equals a BSL exactly → no event; the inspector's touches +1 | s_exact_touch_is_not_taken | PENDING MANUAL VALIDATION |
| L29 | Close exactly at the level = SWEEP | Wick through, close == level → SWEEP | s_close_exactly_at_level_is_sweep | PENDING MANUAL VALIDATION |
| L30 | Gap through | E.g. the 18:00 ET reopen beyond a level → TAKEN "opened beyond", class by close | s_gap_through | PENDING MANUAL VALIDATION |
| L31 | Liquidity OFF = Phase 1 only | Enable liquidity engine OFF → no liquidity lines, labels, events or alerts; FVG/levels/sessions identical to v0.3.2 on the same chart (compare against the baseline script added as a second indicator) | — | PENDING MANUAL VALIDATION |
| L32 | Presets are the documented numbers | Switch Aggressive / Balanced / Strict / Custom → row 21 shows 3/2/0.5, 5/3/1.0, 10/5/2.0, the custom values | — | PENDING MANUAL VALIDATION |
| L33 | Rejected swing is not liquidity | A pivot with Data Window verdict 1 → no event, no line; its reaction < required in the Data Window | s_significance_filter | PENDING MANUAL VALIDATION |
| L34 | No duplicate line on reference levels | A swing high equal to a visible PDH or session high → only the reference line is drawn; row 27 "on a reference line" ≥ 1; the inspector still shows the BSL | — | PENDING MANUAL VALIDATION |
| L35 | EQH: a slightly higher swing within tolerance | Find an EQH, then a later swing high 1–4 ticks above its boundary. **Expected (DEF-L5.4):** the bar that first trades above the boundary emits one `EQH_TAKEN` at the old boundary (sweep/break by its close). The new swing confirms right bars later as its own BSL; the inspector on it shows row 32 = `none`. The old cluster's row 32 keeps the same id, `= reference`, ×2. *The outcome first requested (same id, count + 1, new boundary) cannot occur through prices; the model verifies it on the join path only.* | s_L35_eqh_boundary_expands_upward | PENDING MANUAL VALIDATION |
| L36 | EQL: a slightly lower swing within tolerance | Mirror of L35 (`EQL_TAKEN` at the old lower boundary; the new swing is its own SSL) | s_L36_eql_boundary_expands_downward | PENDING MANUAL VALIDATION |
| L37 | An individual take doesn't clear the pool | Find an EQH whose 2nd high is 1–4 ticks **above** the 1st. Inspector on the 1st member: row 31 = TAKEN (+1–4 ticks) → SWEEP/BREAK, at the 2nd high's bar; row 32 = EQH **ACTIVE**, boundary = the 2nd high `(= reference)`. The EQH line is at the 2nd high | s_L37_individual_take_does_not_clear_cluster | PENDING MANUAL VALIDATION |
| L38 | No retroactive cluster take | For that EQH: no `EQH_TAKEN` with its id at or before its "known" time (row 32). If it was taken, the take time is later than "known" and "last member" | s_L38_no_retroactive_cluster_take | PENDING MANUAL VALIDATION |
| L39 | EQH taken exactly once beyond the boundary | Price later trades above the EQH line on several bars → exactly one `EQH_TAKEN` for that id, on the first bar with high > boundary; event price = the boundary; class by that bar's close | s_L39_eqh_taken_once_beyond_boundary | PENDING MANUAL VALIDATION |
| L40 | EQL taken exactly once beyond the boundary | Mirror of L39 | s_L40_eql_taken_once_beyond_boundary | PENDING MANUAL VALIDATION |
| L41 | Cluster id stable | Inspector on each member of one cluster (and before/after a 3rd member joins, if one does) → the same cluster id and reference; row 32 never shows `DIFFERS` | s_L41_cluster_id_stable | PENDING MANUAL VALIDATION |
| L42 | No duplicate cluster | A 3rd equal high → still one line (`EQH ×3`) and one `EQH_CREATED` (as L20). After an L35 sweep, a pool formed by later swings has a **different** id | s_L42_boundary_change_no_duplicate | PENDING MANUAL VALIDATION |
| L43 | Debug output for manual parity | Debug mode ON. (a) Row 34 "Loaded history (closed bars)" shows the first loaded bar → the last closed bar · N bars · tz; scroll to the chart's first bar to confirm the start. (b) Pine Logs (Pine Editor or IST status line → More → Pine Logs) show one line per event, `yyyy-MM-dd HH:mm  NAME … id=… px=…`, the same text as "Last events"; with Debug mode OFF there are none. (c) Report whether the log text can be selected and copied | — | PENDING MANUAL VALIDATION |
| L44 | Parity capture (bounded) | "Parity capture → Pine Logs" ON, N = 300. Pine Logs show one CAPTURE line, then N + warm-up (Balanced: 317) BAR lines with consecutive `i=`, each followed by that bar's events, then an END line with `bars=317`. Nothing more is logged afterwards (wait 2–3 realtime bars). The capture OFF → no BAR line. Save the Pine Logs into `validation/parity/` as they are (TradingView's `Date,Message` CSV) and run `python -m validation.parity --capture validation/parity/<file>.csv`: report the printed result verbatim | test_parity_capture (parser, warm-up, events) | PENDING MANUAL VALIDATION |

---

## Manual validation procedure

1. **Keep the baseline next to the build.** Add `releases/v0.3.2/src/IST.pine` as a second indicator named "IST v0.3.2", which is needed for L27/L31. Paste `src/IST.pine` (v0.4.3-dev) as a new indicator.
2. **L00:** Save. Report every compiler message verbatim. If there are errors, stop: they come back here before anything else.
3. **Chart:** NQ1! 1m, standard candles, maximum history. Turn Debug ON (DEVELOPER) and open the Data Window.
4. **Swings (L01–L04, L33):** pick a clear swing high and walk the cursor from the swing bar forward: the verdict appears only on swing + 3. Read the inspector (set "Inspect liquidity level" until it shows that swing). Repeat for a low and for a rejected pivot (verdict 1).
5. **Takes (L07–L13, L16, L28–L30):** use the event log (debug row 33) and the inspector on taken levels. For each class, hover the taking bar and compare its high/low/close with the level.
6. **EQ (L17–L21, L35–L42):** find an `EQH ×2` line. Inspector row 32 on both members shows the same cluster id, boundary and reference. Check the tolerance in ticks with the price difference. Look for one EQH whose 2nd high is above the 1st (L37/L38) and, if possible, one that was run by 1–4 ticks into a new swing (L35/L36). Wait for, or find, a take (L39/L40).
7. **State versus display (L05, L06, L31):** toggle displays and caps; rows 22–26 and the events must not change.
8. **Realtime (L15):** in a liquid session, leave the chart open for ≥ 30 bars; write down the events; reload; compare.
9. **Timeframes and resources (L22–L25):** Pine Profiler on 1m; spot checks on 3m/5m; object test with every cap at its maximum.
10. **Phase 1 regression (L27):** re-run the Phase 1 tests that passed, plus T03/T03a, on v0.4.1-dev, and compare with "IST v0.3.2" on the same chart.
11. **Report** each test as PASS/FAIL with a screenshot of the Data Window or inspector for each FAIL. Report the rows 22–23 numbers from L22 (pivots, PASS, REJECT %, levels created, per side, for the loaded history): they are the input for any decision about the Balanced defaults.

**Rollback** at any time:

```bash
git checkout PHASE1_BASELINE_v0.3.2 -- src/IST.pine
```

Alternatively, paste `releases/v0.3.2/src/IST.pine`. To verify the copy, run `sha256sum -c SHA256SUMS.txt` inside `releases/v0.3.2/`.
