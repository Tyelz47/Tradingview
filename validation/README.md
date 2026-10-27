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
| **Pine ↔ Python parity** | only with observations you copy from TradingView into `parity/pine_observed.json` |

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
  parity/               pine_observed.example.json (template) → your pine_observed.json
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
* The map from each TradingView **L-test** to the automated tests that cover its logic. Its TradingView column always stays PENDING.
* The MANUAL list.
* Failures, each with the invariant id and a reproducible case.

## Add a scenario

Add a `test_…` function to the matching file in `tests/`. Mark it with the ids it covers, for example `@pytest.mark.spec("L09", "DEF-L4")`, and it shows up in the L-test coverage table. Build the candles with `scenarios.py` (`liq_run`, `fvg_run`) or `candles.py`. Every helper runs with all invariants checked.

## Add an invariant

1. In `invariants.py`, register it with `_inv("INV-XXX-NN", family, text)` and check it in the matching `Monitor._…` method. Call `self._fail(ID, details)` on a violation and count the evaluation.
2. Add its **negative test** to `tests/test_invariants.py` (`CASES`): corrupt one thing and expect exactly that id. The suite fails if an invariant has no negative test.

## Add a golden case

See `golden/README.md`. Real NQ cases go to `golden/nq/` with `"source": "tradingview"`. Label them from the chart and the IST debug rows, never from the Python output.

## Pine parity (manual data)

1. Copy `parity/pine_observed.example.json` to `parity/pine_observed.json`.
2. Fill it in:
   * build and settings exactly as used on the chart
   * the candles: a TradingView *Export chart data* CSV next to the file, or inline
   * a time window
   * events copied from the IST debug row "Last events" or from alert messages, pasted verbatim into `observed_event_lines`
   * optional field values from the inspectors
3. The agent then compares Pine with the oracle and fails on any difference.

Two cautions:
* Warm-up and memory differ when the export starts later than the chart history. Choose a window well after the first exported bar.
* Nothing scrapes TradingView.

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
