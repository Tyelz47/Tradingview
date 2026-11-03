# IST · IFVG freeze report — v0.9.1-dev

**Status: FREEZE PREPARED on 2026-11-03. NOT FROZEN YET.**
* IFVG-L00, IFVG-L10 and IFVG-L11 pass, all recorded from the user's results.
* IFVG-L12: the automated part passes. The manual TradingView reload check is the user's (`docs/TESTS_IFVG.md`, "IFVG-L12 manual").
* The baseline tag **`IFVG_BASELINE_v0.9.1-dev` is not created.** It follows the user's manual IFVG-L12 PASS and go.
* This prepares the freeze of the **IFVG module** (IFVG-R) only:
  * LRL and HTF FVG in the same file stay EXPERIMENTAL;
  * CISD stays frozen under `CISD_BASELINE_v0.7.1-dev`, displacement under `DISPLACEMENT_BASELINE_v0.8.0-dev`;
  * the Phase 1 and Phase 2 baselines are untouched.

## 1 · Identity

| Item | Value |
|---|---|
| Build | IST **v0.9.1-dev**. The label is kept: the frozen bytes are the bytes captured in TradingView |
| Source | `src/IST.pine`, SHA-256 `553248e78d36fb22665768e4f2e85be610f62a869886b363d05d18c851ea9b91`, unchanged since commit `0d49bc3` (the build in the real capture, `build=v0.9.1-dev`) |
| Oracle | `validation/models/ifvg.py`: `IfvgEngine` is the definition; `IfvgPine` is Pine's formulation, transliterated and proven equal. SHA-256 `1b980c3cf12bd29b35733283be74f158df23b505cab15831323d2f735e08c118` |
| Proposed git tag | **`IFVG_BASELINE_v0.9.1-dev`** (annotated, the convention of the earlier baselines), on branch `ifvg/pine`. Not merged into `main` |
| Read-only copy | `releases/v0.9.1-dev/` (see the next table) |
| Baselines | `PHASE1_BASELINE_v0.3.2`, `PHASE2_BASELINE_v0.4.4-dev`, `CISD_BASELINE_v0.7.1-dev` and `DISPLACEMENT_BASELINE_v0.8.0-dev` unchanged. The Phase 1 diff guard (ST-15) passes. Against `DISPLACEMENT_BASELINE_v0.8.0-dev` the Pine diff only adds lines, except the four build lines |
| Validation tooling | 1.23.0 |

**What `releases/v0.9.1-dev/` holds.**
* the source, the four IFVG documents (`IFVG.md`, `STUDY_IFVG.md`, `TESTS_IFVG.md`, this report) and the requirements note;
* the oracle (`oracle/ifvg.py`);
* the human / deterministic golden dataset and its README (`golden/ifvg/`);
* the real v0.9.1-dev Pine Logs evidence, byte for byte (`evidence/`);
* `SHA256SUMS.txt` (inside the folder: `sha256sum -c SHA256SUMS.txt`);
* `MANIFEST.txt` (the tests, static checks, invariants and tooling, from the repository root).

**Rollback:** once tagged, `git checkout IFVG_BASELINE_v0.9.1-dev`, or paste `releases/v0.9.1-dev/src/IST.pine` into the Pine Editor.

## 2 · Evidence

### 2.1 IFVG-L10: real TradingView parity (v0.9.1-dev) — PASS

The capture is `validation/parity/evidence/ist-v0.9.1-dev_mnq1-1m_capture-1000_2026-11-02.csv`:
* the user's `pine-logs-IST_faf9f.csv`, copied byte for byte;
* SHA-256 `48ae8db3ba0954fe3c10135075135d236d5002b8d6efeac13fc61a5ca456ce63`;
* MNQ1! (CME_MINI:MNQ1!, back-adjusted continuous, settlement as close) 1m, live chart, 2026-11-02 04:16 → 23:11 New York, 1,000 bars + 76 warm-up.

**BOUNDED PINE-LOG BAR-BY-BAR PARITY: PASS. 82 MATCH · 0 DIFFERENCE · 16 NOT OBSERVABLE.**

| module | compared |
|---|---|
| **IFVG** | **1,059 bar states** (shadows, ACTIVE IFVGs per side, CE / full facts); **654 events**: 167 IFVG_INVERTED, 168 IFVG_FIRST_TOUCH, 168 IFVG_INVALIDATED, 151 IFVG_DROPPED_MEMORY, all fields; **100 snapshot records** consistent; the shadows equal the open Phase 1 FVGs |
| Phase 1 / 2 | 1,043 bars × 9 series, 940 events |
| LRL | 41 events, 302 boundaries, 2,000 candidate counts |
| HTF FVG | 126 candles, 92 events, 1,075 bar registries |
| CISD | 1,075 bar states, 174 events; the definition oracle gives 87 CISDs identical to Pine's |
| displacement | 1,060 bar verdicts, 46 events |

**Memory in real Pine.**
* The bearish side held 51–66 ACTIVE IFVGs for 655 bars (from 05:06, peak 66 at 23:04), and every one was kept.
* Every one of the 153 IFVG_DROPPED_MEMORY lines was of an INVALIDATED record: 121 ended earlier in the log, 31 in the snapshot, and 1 before the snapshot (NOT OBSERVABLE).

Pinned by `tests/test_parity_v091_evidence.py`.

### 2.2 IFVG-L11: human / golden validation — PASS

**User, 2026-11-03:** the manual sanity review of the six cases passed.

The dataset is `validation/golden/human/ifvg/` (README there): **22 real MNQ cases**, 20 inside the v0.9.1-dev capture and 2 from v0.8.0-dev (another day and contract).
* 7 clear bearish IFVGs and 7 clear bullish.
* 3 wick-only rejections and 3 closes exactly on the edge.
* 2 one-tick borderline inversions.
* The special cases A–Q are each derived from real candles. Case R1 is mechanical: no real instance exists in the five captures, for any Phase 1 memory from 1 to 15.
* MEM1 is the memory golden on the real log.
* References: H1 and V1 SUPPORTING, V2 INCONCLUSIVE, no conflict.

**0 mismatch.** IFVG-R by hand, the oracle and `IfvgPine` give every recorded number, on the window and on the whole capture.
* The real Pine log agrees: FVG_INVALIDATED and IFVG_INVERTED of the same FVG id on the same bar, the audit geometry, and every later event and fact.

Pinned by `tests/test_ifvg_golden.py`.

### 2.3 IFVG-L12: reload / determinism — automated PASS · manual PENDING

**Automated** (`tests/test_ifvg_freeze.py`, 46 tests; the requirement table is in its docstring). The data:
* the real v0.9.1-dev candles (1,076 bars);
* the three research segments (1,639, 1,076 and 1,076 bars);
* a 5,000-bar walk on which a side holds more than 50 ACTIVE IFVGs;
* the six real captures, for the history-start test.

| requirement | result |
|---|---|
| **1 determinism** | Two runs from a fresh state are identical **on every bar** on all five data sets. Compared: the shadows (identity, original side, geometry, eligibility), every IFVG record field (id = original FVG id, side, top, bottom, CE, inversion bar / time / close, pre, touch / CE / full bar and time, end bar / time / close), the memory (records per side, counters) and the bar's events in order. The IFVG event stream as Pine-Log text is **identical byte for byte**. The oracle gives the same per-bar state, and so does the whole model with every module (run twice) |
| **2 no repaint** | Bar by bar, a new bar only adds the IFVGs it inverts (with no fact yet), stamps an unset fact or the end of an ACTIVE IFVG on that bar, or drops an INVALIDATED record. Identity, side, geometry, inversion bar / time / close and prior state never change, and an INVALIDATED record never changes. A prefix run (7 cuts per data set) equals the full run's past on every bar. Every IFVG of the prefix keeps its fields in the extended run; a fact it lacked comes at the cut or later |
| **2 later history start** | On all six real captures, with shifts of 1, 17, 100 and 400 bars: every IFVG whose parent is confirmed ≥ 16 bars after the first loaded bar is identical, with every field, its events and the ACTIVE set. Only IFVG_DROPPED_MEMORY follows the number of older records held (§6) |
| **3 independence** | The IFVG records and events are the same with Phase 1 alone, with every module, with each of levels, sessions, liquidity, LRL, HTF FVG, CISD and displacement off, and with the FVG display rules changed. In IST.pine the engine reads one input (`ifvgOn`) and, of the global names, only `IFVG_MEM`, its four event codes, its own book and the Phase 1 lists (`bullFvgs`, `bearFvgs`, `fvgDropNow`). Debug, the capture, displays and alerts are out of its reach. Its call sits inside `if engineTick` only. L6 / L7 write no state (ST-06), so a future IFVG renderer cannot change it |
| **4 memory** | Two reloads from Pine's own state (the real snapshot restored) are identical on every bar, and match Pine's active count per side on every captured bar: **655 bars over 50, peak 66**. The ACTIVE set moves only by ends and inversions; compaction never touches it; every drop is of an INVALIDATED record. The final ACTIVE set equals Pine's own (its snapshot's ACTIVE records and logged inversions, minus its logged ends). The walk shows the same from scratch |
| **5 same-bar order** | **Real Pine:** on every bar of the log, Phase 1 → FIRST_TOUCH / INVALIDATED of ACTIVE IFVGs (a touch before its end) → memory (bullish, then bearish) → each inversion with its own side's memory. After the snapshot, the IFVG lines of every bar are the oracle's, one by one and in order: 654 events on 332 bars. Pinned example: 2026-11-02 05:57 (touch, end, drop of the bearish IFVG 05:50; then the 05:52 inversion and the bullish drop; no fact on the new IFVG although its zone was reached). The same order holds on every bar with memory 1, 2 and 50, and an end always comes with all its facts (touch ≤ CE ≤ full ≤ end) |
| **6 Phase 1** | Phase 1 alone and Phase 1 with the IFVG: the same Phase 1 events and FVG records (ids, geometry, lifecycle, memory order) on every bar, and the same memory releases |
| **7 real capture** | The v0.9.1-dev evidence re-run: 0 DIFFERENCE, every count of §2.1 (`tests/test_parity_v091_evidence.py`); its SHA-256 checked (`tests/test_parity_capture.py`) |

**Manual: PENDING.** The user's TradingView reload check (`docs/TESTS_IFVG.md`, "IFVG-L12 manual"):
* three IFVGs (A3 bearish, B2 bullish, B4 lifecycle) and one rejection (C2, wick only);
* each checked on the normal chart, after a page refresh, and after removing and re-adding the indicator.

### 2.4 IFVG-L00 — PASS

v0.9.1-dev compiled and ran in TradingView (user).

### 2.5 Automated validation (FULL, final run before the freeze)

**FULL: PASS**, exit 0, 739.1 s, **1457 passed, 1 skipped**. The only skip is the parity section's manual `pine_observed.json`, which does not exist.
* static 23/23 (ST-21 history scope, ST-23 IFVG-R lines);
* IFVG 172/172 (oracle, Pine formulation, mutations, memory, the 46 L12 tests), IFVG study 8/8;
* golden 290/290 (180 IFVG human golden tests);
* parity 167/168, including the real v0.9.1-dev evidence (0 DIFFERENCE) and the observed-capture test on it;
* invariant detectors 85/85, property 44/44, long walks 22/22;
* CISD 167/167 and displacement 106/106 (frozen suites unchanged), LRL 85/85, HTF 46/46;
* Phase 1 / 2 sections and regression (5/5) unchanged.

## 3 · Frozen definition (IFVG-R; exact text: `docs/IFVG.md`, DEF-IFVG1 … IFVG9)

The bearish IFVG from a bullish Phase 1 FVG is described here; the bullish IFVG from a bearish FVG is the exact mirror.

| rule | frozen text |
|---|---|
| **origin** | Only Phase-1-qualified FVGs: DEF-A1 / A2, the frozen detector with the current [calc] FVG inputs. The FVG must be in the Phase 1 logical FVG universe immediately before its DEF-A5 invalidation. Invalidated and released on the same bar: it inverts. Released earlier: it never inverts. Visibility is irrelevant |
| **inversion** | Original bullish FVG: the strict DEF-A5 close below its bottom → **bearish IFVG**. Original bearish FVG: the strict DEF-A5 close above its top → **bullish IFVG**. A wick alone: **no**. A close exactly at the boundary: **no**. Decided at the bar's close, from the bar after the FVG's confirmation. It is Phase 1's own DEF-A5 bar (`invBar`), read and never recomputed: there is one close rule |
| **geometry** | Exactly inherited: top, bottom, CE. No clipping, no new boundary |
| **lifecycle** | From the bar **after** the inversion. FIRST_TOUCH (the near edge), CE and FULL_TRAVERSAL (the far edge) are wick facts, each stamped once. Terminal INVALIDATED on the first strict close beyond the far edge. A close back inside the zone is not an end |
| **same-bar order** | ACTIVE IFVGs (bullish, then bearish): FIRST_TOUCH → CE → FULL_TRAVERSAL → INVALIDATED. Then memory (bullish side, then bearish). Then the new Phase 1 inversions in creation order: record → IFVG_INVERTED → memory of its side. A new IFVG is not evaluated on its inversion bar |
| **memory** | Target 50 per side, a retention target. An ACTIVE IFVG is never memory-evicted. Temporary overflow is allowed. While a side holds more than 50 records, its oldest INVALIDATED record leaves, with IFVG_DROPPED_MEMORY (terminal records only) |
| **identity** | The original FVG's stable id (its candle-3 time) and the IFVG side. No second inversion |
| **context** | Not required: CISD, displacement, liquidity, LRL, HTF FVG, session, display. Context is a later layer |
| **events** | `IFVG_INVERTED`, `IFVG_FIRST_TOUCH`, `IFVG_INVALIDATED`, `IFVG_DROPPED_MEMORY`. CE and full traversal are record facts, not events |
| **Pine** | An observer after the frozen Phase 1 FVG block that never writes a Phase 1 record or list (ST-23). One input, `ifvgOn` ([calc], ON); one constant, `IFVG_MEM = 50`. No history read in the engine (ST-21). No renderer and no alert; Debug shows four Data Window values and the Pine Logs events |

## 4 · What the freeze guarantees

* IFVG detection, records, lifecycle, memory and events are fixed to the text above and the oracle. Any change is a new, approved version with new evidence.
* ST-23 pins every IFVG-R line, the constant and the four orders of the Pine source. ST-21 guards against history reads inside functions.
* The 34 Pine mutations, the 17 parity corruption kinds, the 22 real golden cases, R1, MEM1 and the L12 tests run in every validation.

## 5 · Open items (not blocking the freeze)

* IFVG-L01 … L05 were not recorded one by one; L00, L10 and L11 cover their logic.
* Not started, by instruction: HTF IFVG, the DOL / context engine, quality scoring, the renderer / styling, alerts.
* The BAR line's IX does not list the last-bar fact of an IFVG that is dropped on its end bar. This is diagnostics only, and the oracle does the same (`docs/TESTS_IFVG.md`, L11).

## 6 · Known limitations

* **Chart timeframe only.**
* **History start (reload on a live chart).** TradingView recomputes from the first loaded bar, which moves as new bars arrive.
  * The IFVGs of FVGs confirmed in the first 16 loaded bars can differ, because Phase 1 qualification needs the TR average.
  * An IFVG of an FVG inverted before the first loaded bar does not exist.
  * Phase 1's frozen DEF-A6 releases an OPEN FVG when all 50 of a direction are open. Which one it releases follows the history start, and a released FVG never inverts. The real v0.9.1-dev log has four such releases, all of FVGs 4–5 days old and about 1,500 points from price; none of the six real captures shows one when replayed. This is Phase 1's reload behaviour, inherited.
  * The timing of IFVG_DROPPED_MEMORY follows the number of older records held. It is bookkeeping and never touches an ACTIVE IFVG or a lifecycle event.
* **Memory has no hard bound** by design. The number of ACTIVE IFVGs is what the market leaves open: real peak 66, up to 248 on 20,000-bar trending walks. A Pine array holds up to 100,000 elements.
* **CE and full traversal are facts, not events.** On the chart they are visible only through the parity capture (BAR IX).
* **No drawing or alert yet.** IFVGs are visible only with Debug mode (Data Window, Pine Logs).
* **No predictive claim** (`docs/STUDY_IFVG.md`). IFVG-R describes a frozen FVG closed through.
* Pine prints prices rounded to the tick. On an exact half-tick CE, parity accepts both neighbouring ticks.
