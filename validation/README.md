# IST validation agent

One command that checks as much of IST as can be checked outside TradingView. It
answers one question: **AUTOMATED LOGIC VALIDATION: PASS / FAIL**. TradingView is then
only the final layer, for what cannot be checked here.

```bash
python -m validation                  # = python validation/validation_agent.py --mode full
```

## What it validates, and what it never claims

| Validated here | How |
|---|---|
| The specification, as a Python **reference model** (oracle): FVG detection, thresholds and lifecycle, sessions, the chart-side level logic, swings, BSL/SSL, taken / sweep / break, EQH/EQL clusters | deterministic scenarios, 40 named invariants, property, stateful and long-walk fuzzing, golden cases |
| The **Pine source text** | 15 static checks: calc/view separation, single creation paths, the renderer never writes state, no-leak `request.security`, defaults/presets/constants/event names equal to the oracle, Phase 1 baseline diff guard |
| **Regressions** | canonical event stream + final state vs a committed baseline; old reference models read from git tags |
| **Pine ↔ Python parity** | only with data you take from TradingView by hand. **Full bar-by-bar** (paid plan): `python -m validation.parity EXPORT.csv` compares the IST Data Window on every bar. **Manual event parity** (free plan, weaker): `python -m validation.parity --manual FILE` compares the settings, counts and events you copy |

**Never claimed** (the report marks these MANUAL / TRADINGVIEW REQUIRED, unless observed data is supplied):
* Pine compilation
* actual Pine runtime behaviour
* `request.security` values and the Daily-bar definition
* Pine `time()` sessions
* graphical rendering
* object limits and execution time
* live / realtime rollback
* alert delivery

## Architecture

```
validation/
  validation_agent.py   CLI: runs pytest in-process, collects results, writes the report, sets the exit code
  __main__.py           python -m validation
  conftest.py           modes (Hypothesis profiles, walk sizes), markers
  models/               THE ORACLE: plain, deterministic Python of the specification
    types.py            Candle, settings (calc) and ViewSettings (view; never read by logic)
    events.py           canonical Event, deterministic order, Pine event-line parser
    fvg.py              DEF-A1…A7, §3.3, §6
    liquidity.py        DEF-L1…L4, L6 (Pine's trigger gate is an optional switch)
    eq.py               DEF-L5.1…L5.6
    sessions.py         DEF-F1…F6
    levels.py           DEF-G2…G6 chart-side logic (day boundary = labelled ASSUMPTION)
    ist.py              all modules in the Pine engine order → events + state
  invariants.py         40 named invariants + the per-bar Monitor
  static_checks.py      text checks of src/IST.pine
  regression.py         corpus, baseline snapshot, diff/classify, legacy models from git
  candles.py            builders, random walks, TradingView CSV loader, mirror/shift
  scenarios.py          helpers shared by the scenario tests
  artifacts.py          failure.json + failure.md per failure; reproduce.py re-runs one
  tests/                deterministic tests (one file per area) + negative invariant tests
  fuzz/                 Hypothesis strategies, property tests, stateful machine, long walks
  golden/               golden dataset (synthetic/ now, nq/ for real labelled cases) + README
  parity/               full parity (python -m validation.parity EXPORT.csv → pine_observed.json) and manual
                        parity (manual.py, --manual manual_observed.txt; manual_observed_template.txt)
  baselines/            baseline.json, expected_changes.json, phase1_removed_lines.txt
  reports/              VALIDATION_REPORT.md and failures/ (generated, not committed)
```

**The oracle principle.** `models/` states the definitions, not the Pine code line by line. It is written for clarity and determinism. Pine-only optimisations are not part of the oracle; they are tested for equivalence against it. The trigger gate, for example, is tested as "gate ON = full scan".

**Order of trust:**
1. When the oracle and a golden case disagree, check the chart first.
2. When the oracle and Pine disagree (parity), one of the two is wrong. Read the specification to decide which.
3. Never edit the trading logic to make a test pass.

## Install

Python 3.10+ and two small dev dependencies (plus `tzdata` on Windows, for the New York timezone):

```bash
python -m pip install -r requirements-dev.txt
```

## Run

| Mode | Use | Hypothesis examples / test | Stateful | Long walks | Time here |
|---|---|---|---|---|---|
| `--mode quick` | every code change | 40 | 15 × 40 steps | 1 × 3,000 bars | ~10 s |
| `--mode full` (default) | before TradingView validation | 250 | 60 × 60 steps | 7 × 20,000 bars | ~1.6 min |
| `--mode deep` | before a version freeze | 2,500 | 400 × 100 steps | 14 × 50,000 bars | ~10 min |

```bash
python validation/validation_agent.py --mode quick
python validation/validation_agent.py --mode full
python validation/validation_agent.py --mode deep
```

**Options:**
* `--phase 1|2|all` runs one phase plus the shared checks.
* `--seed N` sets the Hypothesis seed. Walks and the regression corpus are fixed.
* `--report PATH` writes the report elsewhere.
* `--verbose` prints every test.
* `--update-baseline` rewrites the regression baseline.

**Exit codes:**
* `0`: every automated check passed.
* `1`: at least one automated failure.
* `2`: usage, dependency or internal error.

The FINAL STATUS says READY FOR TRADINGVIEW VALIDATION only after a **full or deep** run of **all phases** with no failures. A passing quick run says PASS, but NOT READY.

## Reading the report

`reports/VALIDATION_REPORT.md` contains:

* Build: Pine version, commit, uncommitted changes, tool versions.
* Summary per section.
* The static checks with details.
* Scenario counts.
* Property, stateful and walk statistics, including reaction-floor selectivity on synthetic noise.
* Invariants: evaluations, and whether each detector is proven by a negative test.
* Regression, by category, expected or unexpected, plus the legacy models.
* The golden dataset.
* Parity.
* Performance, with peak record counts.
* The map from each TradingView **L-test** to the automated tests that cover its logic. Its TradingView column shows only what the user recorded in `docs/TESTS_PHASE2.md`.
* The MANUAL list.
* Failures, each with the invariant id and a reproducible case.

## Add a scenario

Add a `test_…` function to the matching file in `tests/`. Mark it with the ids it covers, for example `@pytest.mark.spec("L09", "DEF-L4")`, and it shows up in the L-test coverage table. Build the candles with `scenarios.py` (`liq_run`, `fvg_run`) or `candles.py`. Every helper runs with all invariants checked.

## Add an invariant

1. In `invariants.py`, register it with `_inv("INV-XXX-NN", family, text)` and check it in the matching `Monitor._…` method. Call `self._fail(ID, details)` on a violation and count the evaluation.
2. Add its **negative test** to `tests/test_invariants.py` (`CASES`): corrupt one thing and expect exactly that id. The suite fails if an invariant has no negative test.

## Add a golden case

See `golden/README.md`. Real NQ cases go to `golden/nq/` with `"source": "tradingview"`. Label them from the chart and the IST debug rows, never from the Python output.

## Pine parity (observed TradingView data)

There are two levels, and the report never mixes them:

| | FULL BAR-BY-BAR PARITY | MANUAL EVENT PARITY |
|---|---|---|
| TradingView plan | paid (*Export chart data*) | free |
| Input | one CSV export | `manual_observed.txt`: values and event lines copied from the debug table and Pine Logs |
| Compared | 9 Data Window series on every bar | only what you copy: settings, debug-row counts, the listed events |
| Candles for the oracle | in the export | a separate OHLC file you supply (`CANDLES=`) |
| A PASS means | Pine and the oracle agree on every exported bar | no difference in what you copied; says nothing about the rest |

### Full bar-by-bar parity (Data Window export)

With Debug mode ON, IST writes its per-bar decisions to the Data Window. TradingView's *Export chart data* includes every Data Window plot as a column, with the plot title as the header. One export therefore holds both the candles and what Pine decided on each bar. Nothing scrapes TradingView: you export by hand.

1. In TradingView:
   * open NQ1! 1m with **one** IST instance;
   * use the settings you want to check, with *Confirmed only* ON and **Debug mode ON**;
   * note debug rows 22–23 (the swing counts).
2. Layout menu (top right) → *Export chart data…*:
   * choose the chart with IST;
   * set time format **UNIX timestamp**;
   * save the CSV in `validation/parity/` (CSV files there are not committed).
3. Run:
   ```bash
   python -m validation.parity validation/parity/<file>.csv --preset balanced
   ```
   * Add `--from 2026-10-27T09:30 --to 2026-10-27T16:00` (New York time) to compare a window.
   * It writes `parity/pine_observed.json` and prints the Pine and oracle counts, then every difference with its New York time.
   * Exit codes: 0 = no difference, 1 = differences, 2 = unusable export (for example, Debug mode was off).
4. `python -m validation` then includes the comparison in the report.

Compared on every bar except the last exported bar, which may still be open:

| Series | IST Data Window plot | Oracle |
|---|---|---|
| `fvg_verdict` | candle 3 verdict (±2 PASS · ±1 REJECT · 0) | FVG_CREATED on the bar, else the raw gap |
| `fvg_required` | required gap = max (points) | §6 thresholds at t−2 |
| `bsl_pivot` / `ssl_pivot` | LIQ swing high/low judged here (2 · 1 · 0) | BSL/SSL_CREATED on the bar, else a judged pivot |
| `liq_required` | LIQ required reaction (points) | k × TR average at the swing bar |
| `bsl_reaction` / `ssl_reaction` | LIQ reaction of that swing | the created level's reaction (on PASS bars) |
| `bsl_take` / `ssl_take` | LIQ BSL/SSL take on this bar (0 · 1 sweep · 2 break) | SWEEP/BREAK events on the bar (break wins) |

Integer codes must be equal. Prices may differ by up to 1e-4 points, because the export may round. The export's `syminfo.mintick` column must equal the tick size.

**Check the swing counts first.** The Pine counts printed for the export must equal debug rows 22–23. If they do, the export starts at the indicator's first bar and every bar can be compared. If they do not, take codes can differ near the start, because memory and history before the export are missing. In that case, compare a later window with `--from`.

**What the Data Window does not cover:** EQH/EQL clusters, FVG milestones, sessions and previous levels. For those, paste lines from the debug row "Last events" (or alert messages) verbatim into `observed_event_lines`. Optional field values from the inspectors go into `observed_states` (format: `parity/pine_observed.example.json`). The importer keeps both when it rewrites the file.

### Manual event parity (free plan)

No export is needed. You copy (or type) what IST shows and run one command:

```bash
python -m validation.parity --manual validation/parity/manual_observed.txt --preset balanced
```

1. **IST settings:** Debug mode ON, Confirmed only ON, other inputs at their defaults except the ones in the file.
2. **Copy `parity/manual_observed_template.txt` to `parity/manual_observed.txt`** and fill what you observe. Empty values are skipped. The template quotes each debug-table row:

   | Key(s) | From |
   |---|---|
   | `SYMBOL`, `TIMEFRAME`, `TIMEZONE`, `TICK_SIZE` | the chart; Sessions → Timezone |
   | `PRESET`, `LEFT`, `RIGHT`, `REACTION`, `EQ_TOLERANCE_TICKS`, `EQ_MIN_TOUCHES` | row 21 "Liquidity engine" |
   | `CONFIRMED_ONLY` | General → Confirmed only |
   | `HISTORY_START`, `HISTORY_END`, `HISTORY_BARS` | row 34 "Loaded history (closed bars)" (v0.4.2-dev) |
   | `SWING_HIGH_*`, `SWING_LOW_*` (pivots, PASS, REJECT, warm-up, created) | rows 22–23 |
   | `BSL_*`, `SSL_*` (active, taken, sweep, break) | rows 24–25 |
   | `EQH_*`, `EQL_*` (active, taken, below min) | row 26 |
   | `CANDLES` | an OHLC CSV of the same chart (see below) |
   | lines between `EVENTS` and `END_EVENTS` | row 33 "Last events" (6 lines) or the Pine Logs pane (one line per event) |

3. **Events.** The debug table is drawn on the chart, so its text may not be selectable; type the lines if needed. With Debug mode ON, v0.4.2-dev also writes every event to **Pine Logs** (Pine Editor → More → Pine Logs, or IST's status line → More → Pine Logs). The pane keeps up to 10,000 historical lines and has Search and Start-date filters. Whether its text can be copied is test L43 (not verified here).
   * A block is read as an **unbroken piece of the event log**. Do not skip lines inside a block. Put another stretch in a new block.
   * The oldest bar of a block may be cut, so missing events are looked for after it, up to the newest bar.
   * If you used the pane's Search to keep some families only (e.g. regex `BSL_|SSL_`), set `EVENT_FILTER=BSL SSL`.
4. **Candles (optional).** The oracle needs the chart's bars. The free plan cannot export them, so `CANDLES=` takes any OHLC CSV (columns `time` or `datetime`, `open`, `high`, `low`, `close`; unix seconds or ISO times). Any other feed can differ from TradingView's (missing bars, the contract roll). The file checks this for you: `HISTORY_START`, `HISTORY_END` and `HISTORY_BARS` must match, and each event price is a check of the data. Without candles, only the internal and settings checks run.

**What it checks.** Each check prints MATCH, DIFFERENCE or NOT OBSERVABLE:

| Section | Checks |
|---|---|
| settings | `LEFT`/`RIGHT`/`REACTION` equal the oracle's preset table; Confirmed only is ON (the oracle models nothing else) |
| candles | bar spacing = `TIMEFRAME`; the candles start at `HISTORY_START`, end at `HISTORY_END` and hold `HISTORY_BARS` bars |
| summary | internal: pivots = PASS + REJECT + warm-up, created = PASS. Against the oracle: every count of rows 22–26, only when the candles are exactly the loaded history |
| events | event type, time, direction, structure id, price; a line listed twice in a block; a one-time event logged twice; an event the oracle does not have (extra); an oracle event inside a block's span that the block lacks (missing) |

Event matching: by type and `id=` (the structure id), otherwise by type and time. Prices are compared as Pine prints them. `format.mintick` rounds to the tick, so a CE on a half tick prints as a neighbouring tick; both neighbours are accepted, because Pine's tie rule is not documented. `LEVEL_SET` is NOT OBSERVABLE: `request.security` values and the previous-day definition are not modelled.

**What it cannot check:** every bar that is not in your copy. That includes FVG and swing decisions on bars without a listed event, Data Window values, the required gap and reaction thresholds, sessions not listed, and everything before the oldest line of a block. It also cannot check what Pine draws, or any setting not in the file (the oracle uses the IST defaults). A manual PASS is never full parity.

Exit codes: 0 = no difference, 1 = differences, 2 = the file is malformed (every bad line is listed with its number). `python -m validation` runs `parity/manual_observed.txt` when it exists and shows the result next to the full parity.

## Regression baseline

`baselines/baseline.json` holds the canonical events and final state of a fixed corpus of three cases (1,000-bar walks).

* Any difference is classified as ADDED, REMOVED, TIMING, PRICE, STATE or CHANGED.
* It counts as **EXPECTED** only if an entry in `baselines/expected_changes.json` matches it. Otherwise it is **UNEXPECTED** and fails the run.

Workflow for an intended model change:
1. Add a manifest entry with the reason.
2. Run the agent and review the classified differences.
3. Once approved, run `python -m validation --update-baseline`, review `git diff`, commit, and remove the entry.

The old reference models (`tests/liq_model.py` at tags `v0.4.0-dev` and `v0.4.1-dev`) are also re-run from git and must match the oracle exactly.

## Reproduce a failure

Each failure writes `reports/failures/<test>/failure.json` and `failure.md`. They contain:
* the seed
* the candles: the Hypothesis-shrunk case, or the prefix up to the violating bar
* the settings
* the invariant id
* expected and actual

```bash
python -m validation.reproduce validation/reports/failures/<test>/failure.json
```

Hypothesis also prints a `@reproduce_failure` blob in the pytest output.

## Future modules (Phase 3+)

For a new module:
1. Add a model in `models/` and wire it into `ist.py` in the Pine engine order.
2. Add its event names to `events.TYPES`. ST-14 compares them with Pine.
3. Add invariants with negative tests, scenario tests under a new `section` marker, and a strategy and properties in `fuzz/`.

The report picks up new sections automatically. Then refresh the baseline.

## CI

The command is CI-ready: no network, deterministic seeds, and the exit code carries the result. A minimal GitHub Actions job runs `pip install -r requirements-dev.txt` followed by `python -m validation --mode full`. The job needs the git tags (`fetch-depth: 0`) for the legacy and Phase 1 baseline checks. Without them, those checks report SKIPPED.

## Limitations

* **Confirmed mode only.** Every candle is a closed bar. Live-mode intrabar behaviour is not modelled.
* **The day boundary for PDH/PDL/PWH/PWL is an assumption** (18:00 ET, ARCHITECTURE §7.2), and the values from `request.security` are not reproducible here. The model checks the chart-side logic only.
* **Floating point.** Pine's `ta.sma` may sum in a different order. A threshold within ~1e-9 of the boundary could differ in Pine (parity would show it).
* **Fuzz data is synthetic** (random walks, generated sequences). It finds logic errors; it says nothing about how NQ behaves. The selectivity numbers are noise statistics, not a tuning signal.
* **Static checks read text.** A passing static check does not mean that the script compiles.
