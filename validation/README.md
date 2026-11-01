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
| **Pine ↔ Python parity** | only with data you take from TradingView by hand. **Full CSV bar-by-bar** (paid plan): `python -m validation.parity EXPORT.csv` compares the IST Data Window on every bar. **Bounded Pine-Log bar-by-bar** (free plan): `python -m validation.parity --capture FILE` replays a window captured to Pine Logs. **Manual event parity** (free plan, weakest): `python -m validation.parity --manual FILE` compares the settings, counts and events you copy |

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
    lrl.py              docs/LRL.md DEF-LRL1…LRL8: opt-in module "lrl" (not in default runs; the Parity
                        capture turns it on when the CAPTURE line says lrl=1). Pine: v0.5.0-dev, ST-17
    htf_fvg.py          docs/HTF_FVG.md DEF-B0…B6: opt-in module "htf" (6 timeframes, seeds, own-timeframe
                        invalidation; restore() + an external HTF feed for the Parity capture). Pine: v0.6.0-dev, ST-03, ST-19
    cisd.py             docs/CISD.md DEF-CISD1…CISD9: opt-in module "cisd" (UNKNOWN start, alternating
                        state, record facts); CisdStack = Pine's incremental formulation (no scan),
                        proven equal, restorable from the parity snapshot. Pine: v0.7.0-dev, ST-20
    displacement.py     docs/DISPLACEMENT.md DEF-DISP1…DISP9 (DISPLACEMENT-R, proposed): opt-in module "disp"
                        (one closed candle; FVG fact on the next bar). No Pine yet: its events are ORACLE_ONLY (ST-14)
    ist.py              all modules in the Pine engine order → events + state
  invariants.py         74 named invariants (10 LRL, 8 HTF, 8 CISD, 6 displacement, checked only when the module runs) + the per-bar Monitor
  static_checks.py      text checks of src/IST.pine
  regression.py         corpus, baseline snapshot, diff/classify, legacy models from git
  candles.py            builders, random walks, TradingView CSV loader, mirror/shift
  scenarios.py          helpers shared by the scenario tests
  artifacts.py          failure.json + failure.md per failure; reproduce.py re-runs one
  tests/                deterministic tests (one file per area) + negative invariant tests
  fuzz/                 Hypothesis strategies, property tests, stateful machine, long walks
  golden/               golden dataset (synthetic/ now, nq/ for real labelled cases) + README
  parity/evidence/      real TradingView captures kept byte for byte (SHA256SUMS.txt): v0.4.3-dev, v0.4.4-dev (C1)
  parity/               full parity (python -m validation.parity EXPORT.csv → pine_observed.json) and manual
                        parity (manual.py, --manual manual_observed.txt; manual_observed_template.txt) and
                        bounded Pine-Log parity (capture.py, --capture pine_capture.csv or .txt)
  studies/              analyses before a definition is specified (never change the oracle):
                        liquidity_significance.py (reads the v0.4.3-dev evidence capture);
                        lrl.py (LRL research, docs/STUDY_LRL.md; both captures merged, charts → docs/study_lrl);
                        cisd.py (CISD research, docs/STUDY_CISD.md; the oracle equals its CISD-R engine);
                        displacement.py (displacement research, docs/STUDY_DISPLACEMENT.md; the oracle equals D6)
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
* `--phase 1|2|lrl|htf|cisd|disp|all` runs one phase (or LRL detection, HTF FVG, CISD, displacement) plus the shared checks.
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

There are three levels, and the report never mixes them:

| | FULL CSV BAR-BY-BAR PARITY | BOUNDED PINE-LOG BAR-BY-BAR PARITY | MANUAL EVENT PARITY |
|---|---|---|---|
| TradingView plan | paid (*Export chart data*) | free | free |
| Input | one CSV export | `pine_capture.csv` (the Pine Logs file TradingView saves) or `.txt` (pasted): an IST *Parity capture* | `manual_observed.txt`: values and event lines copied by hand |
| Candles for the oracle | in the export | in the capture (exact, rebuilt from the BAR lines) | a separate OHLC file you supply (`CANDLES=`) |
| Compared | 11 Data Window series on every bar | 9 per-bar series (7 before v0.4.4-dev) on every bar after the warm-up, and the events of structures born inside the window | only what you copy: settings, debug-row counts, the listed events |
| A PASS means | Pine and the oracle agree on every exported bar | they agree on that window; nothing about earlier history | no difference in what you copied |

### Full CSV bar-by-bar parity (Data Window export)

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
| `bsl_dominance` / `ssl_dominance` | LIQ dominance: highest high / lowest low of the W bars before the swing (v0.4.4-dev) | `dominance_ref()` of the swing judged on the bar |

Integer codes must be equal. Prices may differ by up to 1e-4 points, because the export may round. The export's `syminfo.mintick` column must equal the tick size.

**Check the swing counts first.** The Pine counts printed for the export must equal debug rows 22–23. If they do, the export starts at the indicator's first bar and every bar can be compared. If they do not, take codes can differ near the start, because memory and history before the export are missing. In that case, compare a later window with `--from`.

**What the Data Window does not cover:** EQH/EQL clusters, FVG milestones, sessions and previous levels. For those, paste lines from the debug row "Last events" (or alert messages) verbatim into `observed_event_lines`. Optional field values from the inspectors go into `observed_states` (format: `parity/pine_observed.example.json`). The importer keeps both when it rewrites the file.

### Bounded Pine-Log bar-by-bar parity (free plan)

IST (since v0.4.3-dev) has a debug-only input, **Parity capture → Pine Logs** (default OFF), with **Capture last N closed bars** (default 300, 50–2,000). When it is ON, IST writes to Pine Logs:

```text
CAPTURE|sym=CME_MINI:NQ1!|tf=1|tick=0.25|tz=America/New_York|confirmed=1|liq=1|preset=Balanced|left=5|right=3|k=1|w=30|…|bars=300|warmup=33
BAR|2026-10-27T10:31:00-0400|i=10234|O=21345.25|H=21347|L=21344.5|C=21346.75|FV=0|FR=1.0357|SH=0|SL=2|RH=na|RL=6.25|RQ=4.0179|DH=21351.5|DL=21302.25
2026-10-27 10:31  SSL_CREATED id=2026-10-27 10:28 px=21340.50 · reaction 1.56×TR ≥ 1
…
END|bars=333
```

* **CAPTURE** holds every calculation setting the oracle needs: the liquidity and EQ inputs, the FVG thresholds and memories, the session windows and the timezone. Nothing has to be typed.
* **BAR**, one per closed bar, holds:
  * the bar's open time with its UTC offset and its bar index;
  * the exact OHLC (8 decimals);
  * FVG verdict `FV` (±2 created, ±1 rejected, 0) and required gap `FR`;
  * swing verdicts `SH`/`SL` (2 PASS, 1 REJECT, 0 none);
  * reactions `RH`/`RL` on pivot bars;
  * dominance references `DH`/`DL` (v0.4.4-dev): the highest high / lowest low of the W bars before the swing judged on this bar;
  * required reaction `RQ` (k × TR average).
* After each BAR line come that bar's **events**, in the Pine Logs event format.
* **Only closed bars** are logged. Logging is **bounded**: N + warm-up bars, then END, then nothing more, even in realtime. With the capture ON, events are logged for the captured bars only.

Save the Pine Logs as a file in `validation/parity/` (TradingView saves a `Date,Message` CSV; keep it as it is), or paste the text into a `.txt` file there, then run:

```bash
python -m validation.parity --capture validation/parity/pine_capture.csv
```

**Input.** Two kinds of input are read, and the kind is detected from the file itself:
* **TradingView's saved file** (header `Date,Message`, detected from its header). It is read with Python's `csv` module, which undoes the quoting and the doubled quotes. Only the Message field is parsed; the Date column is kept for diagnostics. CRLF, a UTF-8 BOM, and commas or quotes inside a message are handled. On a chart with back-adjustment, `sym=` holds a JSON object; that is expected.
* **Pasted text.** The pane's own timestamps in front of each line, blank lines and pane text are ignored. `Date,"Message"` rows pasted without their header are decoded the same way as the CSV.

**Capture runs.** A log can hold several runs, for example after a reload. A run is one CAPTURE … END. Runs are **never merged**: the latest complete and valid run is used, and every run is listed in the output with its lines, window and status.

**Rejected, with line numbers (exit 2)**, because the candles would not be exact:
* no CAPTURE line;
* no END line: the last bar was still open when the logs were saved, or the file is cut;
* a BAR count that differs from END, or from `bars + warmup` on the CAPTURE line;
* a missing bar (index gap) or a bar listed twice;
* wrong OHLC (high below open/close, off the tick grid, `na`, not a number);
* a malformed timestamp;
* a CSV without a Message column, or malformed CSV.

**Warm-up.** The oracle sees only the captured bars, so its first bars lack history: its TR on the first bar has no previous close, and the first pivots lack their left window. IST therefore captures the warm-up automatically. It is derived from the dependency graph (`FvgSettings.lookback`, `LiqSettings.lookback`): `warmup` = max(FVG length + 2, max(14, left, W) + right). On v0.4.4-dev that is 33 for Balanced, 65 for Strict and 16 for Aggressive; before C1 it was 17 / 19 / 16. None of it is compared:

| Compared from capture bar | Series |
|---|---|
| FVG length + 2 | FVG verdict, required gap |
| max(14, left, W) + right | swing verdicts, reactions (on PASS bars), required reaction, dominance references |

A capture without `w=` (IST before v0.4.4-dev) is replayed with the definition its build used, reaction only, and its dominance series are NOT OBSERVABLE. The committed v0.4.3-dev capture is preserved this way.

**Evidence (`parity/evidence/`).** The real TradingView captures are kept byte for byte, with `SHA256SUMS.txt` and `README.md`.
* **v0.4.3-dev** (before C1): historical evidence.
* **v0.4.4-dev** (C1): **the Phase 2 freeze evidence and the regression asset of the frozen definition**. It gives 1,000 bars × 9 series and 1,049 events, 0 DIFFERENCE.

Tests replay both on every run and check their hashes. C1 (DEF-L2 dominance) is the frozen Phase 2 liquidity definition: tag `PHASE2_BASELINE_v0.4.4-dev`, `docs/PHASE2_FREEZE_REPORT.md`.

**Events.** Only structures born inside the comparable region are compared. These are FVGs whose candle 3 is after the FVG warm-up, levels whose swing bar is after the liquidity warm-up, and sessions that start inside the window. For each, the check covers type, direction, id, time and price, an event logged twice, an extra event and a missing event. Everything the oracle cannot know is **NOT OBSERVABLE** and never compared:
* levels and FVGs born before the window, or in its warm-up, including their takes, sweeps and breaks inside the window;
* EQH/EQL clusters, which can include older levels;
* `*_DROPPED_MEMORY` (Pine's memory also holds older records), and any event of a structure after one side dropped it;
* sessions already running at the start;
* `LEVEL_SET`.

The per-bar take codes are not in the BAR line for the same reason: one bar can also take an older level.

**Self-test.** Synthetic captures are written from an oracle run over the whole history, which is what Pine knows, and cut to the last N + warm-up bars. Over 138 runs (3 presets, 20 seeds, windows of 300 to 2,000 bars) this gives 0 false differences and 228,008 matched events. Injected faults are each found.

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

Exit codes: 0 = no difference, 1 = differences, 2 = the file is malformed (every bad line is listed with its number). `python -m validation` runs the most recently saved `parity/pine_capture*.csv` / `.txt` and `parity/manual_observed.txt` when they exist and shows each result on its own line, next to the full CSV parity.

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
