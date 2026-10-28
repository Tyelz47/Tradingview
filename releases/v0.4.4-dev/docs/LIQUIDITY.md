# IST — Phase 2 · Liquidity engine (v0.4.1-dev)

> **Status:** development build on branch `phase2/liquidity` (v0.4.1-dev = v0.4.0-dev + the EQ boundary hardening review, DEF-L5.1–L5.6, and selectivity diagnostics; liquidity outputs unchanged). **Not compiled or validated in TradingView yet. Phase 2 is not complete until manual validation (docs/TESTS_PHASE2.md) is done.**
>
> **Baseline:** Phase 1 = v0.3.2, frozen. Git tag `PHASE1_BASELINE_v0.3.2`; read-only copy with SHA-256 sums in `releases/v0.3.2/`.
>
> **In scope:** swing highs/lows, BSL/SSL, liquidity taken, sweep vs break/run, EQH/EQL, Phase 2 events, alerts, debug.
>
> **Out of scope** (not implemented, not prepared beyond the extension points in §12): CISD, displacement, IFVG, HTF FVG, SMT, quality scoring, confluence dashboard, buy/sell signals, LRL.

---

## 1 · The four questions

| Question | Answered by | Where |
|---|---|---|
| **Where** is meaningful liquidity? | Confirmed swing (DEF-L1) that passed the rejection filter (DEF-L2) and has not been traded through: an *active* BSL/SSL level, or an active EQH/EQL pool (DEF-L5) | `price` of active `Liq` / `EqCluster` records |
| **When** did it become known? | The close of the confirmation bar, swing bar + right (DEF-L1). Never earlier, whatever the drawing anchor | `confirmBar/confirmTime`; EQ: `qualBar/qualTime` |
| **Has** price actually taken it? | First bar whose high (BSL) or low (SSL) is strictly beyond the price, after confirmation (DEF-L4) | `takenBar/takenTime`, event `BSL/SSL_TAKEN` |
| **Was** it a sweep/reclaim or a break/run? | The close of the taking bar: strictly beyond = BREAK, otherwise SWEEP (DEF-L4) | `cls`, event `BSL/SSL_SWEEP` or `_BREAK` |

---

## 2 · What makes a swing meaningful enough to become liquidity?

Not "being a pivot". A swing becomes a liquidity level only when all of these hold:

1. **It dominates its neighbourhood (structure).** Its high is strictly above every high of the `left` bars before it, and at or above every high of the `right` bars after it. Lows mirror this. The left side costs no latency, so the presets lean on `left`: a Balanced 1m swing high is the highest point of the previous 5 minutes and held for 3.
2. **Price was rejected from it (significance, part a).** Within the `right` confirmation bars, price moved away from the swing by at least **k × TR average** (the TR average is measured at the swing bar). A rejection means orders were left resting beyond the extreme: stops above a high that price walked away from. A pivot where price only stalled sideways (inside bars, a drift) is a pause, not a level.
2b. **It is the extreme of its recent past (significance, part b: dominance; C1, v0.4.4-dev, FROZEN Phase 2 definition).** No high in the **W bars before the swing bar** is above the swing high + EQ tolerance (lows mirrored). It is the "external" liquidity of that window, not an inner pivot. This was added because, on real NQ 1m data, part (a) alone passed ~95 % of pivots. That reaction is large by construction; see `docs/STUDY_LIQUIDITY_SIGNIFICANCE.md`, approved 2026-10-28.
3. **It is still untraded.** The moment price trades through it, it stops being *active* liquidity (it is *taken*). Only active levels compete for display.
4. **It is not a duplicate.** Swings within tolerance merge into one EQ pool instead of two lines (DEF-L5). A level sitting exactly on a visible PDH/PDL/PWH/PWL or session high/low line is not drawn a second time (rendering only, DEF-L7).

**Deliberately not used in Phase 2:** age (the engine-memory policy handles it logically, the nearest-first display handles it visually), distance to price (a display concern, not a logical one), volume (no reliable data in Pine for this), HTF swings (Phase 4), and any scoring (Phase 5).

**What keeps an NQ 1m chart readable** is the combination: the pivot window (1), the rejection floor (2), taken levels leaving the active set at once (3), merging (4), and the display budget (5 nearest active levels per side, DEF-L7). Logical state is never pruned for display reasons.

### 2.1 Presets: explicit numbers, no hidden logic

| Preset | left | right (= confirmation delay) | k (reaction ≥ k × TR average) | W (dominance window, bars) | Character |
|---|---|---|---|---|---|
| Aggressive | 3 | 2 | 0.5 | 10 | more levels, earlier, more noise |
| **Balanced** (default) | **5** | **3** | **1.0** | **30** | NQ default |
| Strict | 10 | 5 | 2.0 | 60 | fewer, more significant, later |
| Custom | input | input | input | none (0: dominance off) | the three inputs, shown in the debug table |

W is part of the preset, not an input. Custom has no W input yet, so it keeps the definition from before C1. On 1m, W = 10 / 30 / 60 bars is 10 minutes, half an hour and an hour; on 5m it is 50 / 150 / 300 minutes.

**Trade-off.**
* `right` is pure latency: a level is unknown for `right` bars after its extreme printed. On 1m that is 2 / 3 / 5 minutes; on 5m it is 10 / 15 / 25.
* `left` is structural relevance at no latency cost: a larger value means the extreme must dominate more history.
* `k` is the rejection floor: a larger value rejects swings that price only drifted away from.
* All three move monotonically from Aggressive to Strict. The values were chosen for that monotonic ladder and for latency on 1m–5m. **They were not fitted to any chart or screenshot.**

**What the reaction floor does, measured honestly.** On a synthetic random walk (the reference model, now `validation/models/`, 20,000 bars), these are the share of pivots that pass the reaction rule:

| Window | Pivots per 1,000 bars (one side) | k 0.5 | k 1.0 | k 1.5 | k 2.0 | k 2.5 |
|---|---|---|---|---|---|---|
| left 3, right 2 | 106 | 100 % | 94 % | 68 % | 39 % | 19 % |
| left 5, right 3 | 72 | 100 % | 98 % | 86 % | 61 % | 38 % |
| left 10, right 5 | 40 | 100 % | 100 % | 97 % | 86 % | 69 % |

On noise, the window does almost all of the selection and the default floors remove only stalls (≈2 % for Balanced, ≈14–18 % for Strict depending on the walk; v0.4.1-dev fuzz, seed 7: Balanced 2.4 % highs / 1.7 % lows, Strict 17.6 % / 16.0 %). This is a property of the noise model, not of NQ. **The presets are not changed on this evidence.** On real charts debug rows 22–23 (`Swing highs / lows (loaded history)`) show pivots, significance PASS, REJECT (with %), warm-up and levels created, per side. If Balanced proves too busy, the transparent levers are `left` (no latency) or the Strict preset. The k values are not quietly retuned. Real NQ data (1,000-bar capture, parity PASS) confirmed this on 2026-10-27. The study `docs/STUDY_LIQUIDITY_SIGNIFICANCE.md` led to C1 (dominance, part b above), approved on 2026-10-28, implemented in v0.4.4-dev and **frozen** with Phase 2 on 2026-10-28 (`docs/PHASE2_FREEZE_REPORT.md`). **k was not changed.**

---

## 3 · Exact definitions (DEF-L)

All prices are chart prices. t = the bar being evaluated (its close in Confirmed mode). `EPS` = 0.01 tick.

**DEF-L1 · Swing and confirmation.** At the close of bar t, the candidate swing bar is X = t − right.
* **Swing high:** `high[X] > max(high[X−left … X−1])` **and** `high[X] ≥ max(high[X+1 … t])`.
* **Swing low:** `low[X] < min(low[X−left … X−1])` **and** `low[X] ≤ min(low[X+1 … t])`.
* **Ties (plateau rule).** Strict on the left, non-strict on the right. For a flat top of adjacent equal highs at bars X, X+1, …, X+j:
  * **Bar X qualifies.** Its right-side test is `≥`, so the equal bars pass it.
  * **Every later plateau bar fails.** Its left window contains an equal high, and the left test is strict.
  * **So the plateau gives exactly one swing**, at its first bar, confirmed at X + right (like any swing). Adjacent equal bars never create duplicate individual swings.
  * **Why the first bar:** it is when the extreme was first printed, where the orders beyond it start to rest. It is also the earliest deterministic choice: it confirms first and never moves.
  * **Equal highs further apart than `left` bars**, with lower bars between, are separate swings. That is what EQH is built from.
  * Flat bottoms mirror this.
* **Origin** = X. **Confirmation** = t = X + right. The swing does not exist for the engine before t closes. Pivots are evaluated on confirmed bars only, in both engine modes.
* During warm-up (the first left + right bars) there are no pivots.

**DEF-L2 · Significance = rejection AND dominance** (dominance: C1, v0.4.4-dev; **frozen** with Phase 2 on 2026-10-28, tag `PHASE2_BASELINE_v0.4.4-dev`, after a 1,000-bar real-NQ capture gave Pine ↔ Python parity with 0 differences).
* (a) Rejection:
  * `reaction(high) = high[X] − min(low[X+1 … t])`
  * `reaction(low) = max(high[X+1 … t]) − low[X]`
  * `required = k × TRavg[X]`, where `TRavg = SMA(true range, 14)` is the same deterministic, non-Wilder definition as DEF-A2. It has its own fixed length, so FVG inputs never affect liquidity.
  * passes iff `reaction ≥ required`.
* (b) Dominance, with `tol = EQ tolerance ticks × mintick`, the same tolerance and float margin `EPS` as DEF-L5:
  * `domRef(high) = max(high[X−W … X−1])`: the W bars **before the swing bar**. The window is anchored to the origin X, not to the confirmation bar, and the right bars are not part of it.
  * passes iff `domRef(high) ≤ high[X] + tol`. Only an earlier high **strictly** above the swing + tolerance rejects; one exactly at + tolerance does not. Lows mirror it: `domRef(low) = min(low[X−W … X−1])`, passes iff `domRef(low) ≥ low[X] − tol`.
  * W = 0 (Custom) means dominance is off.
  * The EQ tolerance is used so that a second top up to the tolerance below an earlier top inside W can still be a level and form an EQH. Changing "EQ tolerance" therefore also changes dominance.
* The swing becomes a level iff (a) and (b) both pass.
* **Warm-up:** while `TRavg[X]` is `na` (the first 14 bars) or fewer than W bars exist before X, the pivot is **warm-up**: counted as a pivot, neither PASS nor REJECT.
* **REJECT reasons are recorded disjointly:** reaction only · dominance only · both. The REJECT total is their sum, and a pivot that fails both is counted once, under "both".
* Only data up to t is used. A decision depends only on the bars X − max(14, left, W) … t, so it does not change when the loaded history starts earlier (reload invariance).

**DEF-L3 · Presets.** These are exactly the numbers in §2.1: (left, right, k, W). Custom uses `Swing left bars`, `Swing right bars` and `Min reaction × TR average`, with no dominance. The values in force at birth are stored on each level (`pivL`, `pivR`, `reactReq`, `tra`).

**DEF-L4 · Taken, sweep, break.** A BSL is described here; an SSL mirrors it, with `low` and "below".
* **Taken** (the fact): on the first bar k > confirmation with `high > price`. A single tick and a wick are both enough. This emits `BSL_TAKEN` once, with the penetration in ticks.
* **Classification** (the interpretation): made at the **close of the taking bar k**.
  * **BREAK:** `close > price` (accepted beyond).
  * **SWEEP:** `close ≤ price` (no acceptance beyond: back inside, or exactly at the level).
  * It emits `BSL_BREAK` or `BSL_SWEEP` once. The class is never relabelled.
* **Exact touch:** `high == price` is **not** a take. It increments `touches` (pre-take interactions) and emits no event.
* **Gap through:** the taking bar opened beyond the level. It is classified by the same rule and flagged `takeGap` ("opened beyond" in the event).
* After the take the level is inactive: it gets no further events and leaves the active display set.
* **Live mode** (Confirmed only OFF): TAKEN is logged at the tick it happens. A take cannot un-happen within a bar, so it is intrabar-stable. SWEEP/BREAK still wait for the close.

| Edge case | Result |
|---|---|
| Exact tick touch (`high == level`) | not taken; `touches + 1`; no event |
| Wick through, close back below | TAKEN + SWEEP on that bar |
| Wick through, close **exactly at** the level | TAKEN + SWEEP (a break needs acceptance = a close strictly beyond) |
| Close beyond | TAKEN + BREAK |
| One-tick penetration | TAKEN (it is a fact); class by close; penetration in the event and the inspector. Grading penetration is Phase 3+ |
| Gap through the level | TAKEN ("opened beyond") + class by close |
| First candle closes beyond, second closes back | BREAK at the first candle. **Not** relabelled (see §12: confirmation window) |
| Several candles hovering at the level without exceeding it | `touches` counted; no event |
| Repeated attacks after the take | no events (the level is inactive) |
| One bar takes several levels / both sides (outside bar) | every level gets its own TAKEN + class |
| A level on its own confirmation bar | cannot be taken there (DEF-L1 guarantees `high[t] ≤ level`); the engine also checks `bar_index > confirmBar` |

**"Structural sweep" versus a future "high-quality sweep".** Phase 2's SWEEP is purely structural: taken plus no close beyond. A Phase 3 strict sweep (taken + reclaim within a window + displacement) would be a separate classification layered on the same stored facts (`takenBar`, `takeExt`, `takeClose`). It would not redefine this one.

**DEF-L5 · EQH / EQL.** EQH is described here; EQL mirrors it (`min` for `max`, "below" for "above"). Members are levels (significant swings) of one side.

**DEF-L5.1 · Identity versus boundary (v0.4.1-dev).** The cluster record keeps two separate concepts:

| Concept | Fields | Changes? |
|---|---|---|
| **Identity / creation reference** | `id` = time of the bar where the cluster formed (its 2nd member confirmed) · `ref` = extreme of the first two members · `originBar/Time` = earliest member's swing · first members = `members[0..1]` | **never** |
| **Current state** | `bound` = **current outer boundary** = highest accepted member (EQH) / lowest (EQL) · `members` (append-only; count = size) · `lastBar/Time` = latest member's confirmation · `qualBar/Time` · `takenBar/Time`, `cls` | `bound` only outward: `bound := max(bound, member)` |

Everything that acts on the pool uses **`bound`**: join distance, the take test, the classification, the trigger gate, event prices and the drawn line. `id` and `ref` are identity and debug metadata. A boundary change keeps `id`, `ref` and the existing members, emits no event and creates no cluster.

**DEF-L5.2 · Join and form.**
* **Join:** a new level joins the nearest **active** cluster with `|new − bound| ≤ tolerance`. Ties go to the newest.
* **Form:** otherwise it forms a cluster with the nearest earlier level that:
  * is in no cluster,
  * is within tolerance,
  * has an **intact pool**: either untaken (then the new level is at or below it), or taken but with nothing traded above the *new* level since (then the new level is the edge).
* `ref = bound = max(seed, new)` at formation.
* A level belongs to at most one cluster, so one pool gives **one** cluster, never overlapping duplicates. A taken cluster keeps its members, so they cannot seed another pool: a later pool needs new swings and gets a new `id`.
* Members always lie in `[bound − tolerance, bound]`. A taken level whose furthest excursion exceeds `price + tolerance` can never be part of an intact pool, so it closes.
* **EQH_CREATED:** when the member count first reaches `Minimum touches`. Its timing is the confirmation of that member.
* **EQH_TAKEN:** the first bar after the cluster is known with `high > bound`, i.e. all members' stops. It has the same SWEEP/BREAK rule, stored on the cluster, and fires once. A cluster that never reached the minimum and is traded through ends silently: it never was an EQH.
* **Tolerance:** ticks only (`Tolerance (ticks)`, default 4 = 1.0 NQ point). A TR-relative mode is a documented extension.

**DEF-L5.3 · Individual liquidity versus cluster liquidity.** These are two separate facts, stored on separate records.
* **Individual** (each member's own `Liq`): taken when price trades beyond **its own** price (DEF-L4).
* **Cluster** (the `EqCluster`): taken when price trades beyond the **cluster's current boundary**, after the cluster is known.
* An individual member being TAKEN does **not** clear the cluster.

Example (tolerance 4 ticks): A = 100.00 confirmed. B prints 100.25, which takes A by one tick. B confirms, and nothing has traded above 100.25 since, so B forms an EQH with A. The resulting state is deterministic:

| Record | State |
|---|---|
| swing A (BSL 100.00) | **TAKEN** at B's bar, SWEEP or BREAK by that close. A true fact; never rewritten |
| swing B (BSL 100.25) | ACTIVE |
| EQH {A, B} | **ACTIVE**, `ref = bound = 100.25 = max(A, B)` |

Only a later trade above 100.25 takes the EQH. A member's individual events are never rewritten when it joins a cluster or when the cluster changes.

**DEF-L5.4 · Can the boundary move after creation? No, not through prices.** This follows from the DEF-L1 pivot with a fixed window. Proof (EQH):

Let M be the cluster's latest member (swing bar X_M, confirmed at X_M + R). Let C be a later swing high with C > `bound` ≥ M.
1. C confirms after M, so X_C > X_M (every pivot uses the same R).
2. If X_C ≤ X_M + R, bar X_C lies in M's right window, and DEF-L1 requires `high[X_M] ≥ high[X_C]`. That gives C ≤ M ≤ `bound`, a contradiction. So X_C > X_M + R: C's high prints **after** the cluster containing M was known.
3. On bar X_C the engine's take test runs: `high[X_C] = C > bound`. So the cluster is **taken on C's own bar**, at the boundary known then: EQH_TAKEN, classified at that bar's close.
4. When C confirms, at X_C + R, the cluster is already taken, and only active clusters accept members. C becomes its own BSL, in no cluster.

So in every reachable state `bound == ref`, and the outward update in DEF-L5.1 is a no-op today. It is kept so that the state model is explicit and stays correct if a later phase changes when a cluster counts as taken (for example a confirmation window). The model asserts `bound == ref` on every bar of every fuzz run (S-11).

**Worked example (the review case).** Tolerance 4 ticks.
1. A = 100.00. B = 100.50 trades through A, so A is TAKEN. B confirms, giving EQH {A, B} with `ref = bound = 100.50`.
2. C = 100.75 prints after B was confirmed. **EQH TAKEN on C's bar** (+1 tick; SWEEP or BREAK by that close).
3. C confirms R bars later as a new BSL at 100.75, in no cluster.
4. A later D within 4 ticks of C, with the pool intact, forms a **new** cluster {C, D} with a new id.

Why not "expand the cluster" instead? The only way to know that C is a member is to wait R bars after the trade through 100.50. Expanding would need one of two things, and both break the contract:
* not counting a within-tolerance excursion as a take. That changes the agreed TAKEN definition and delays the sweep event by R bars (or repaints it);
* rewriting an EQH_TAKEN that already fired. That breaks the once-only and no-rewrite rules.

The trade through 100.50 is the classic one-tick sweep of equal highs, which is exactly what the tool must report. With `Minimum touches` ≥ 3, the same trade ends the 2-member group silently, so C cannot make it a 3-touch EQH.

**DEF-L5.5 · Timing (no self-trigger, no retroactive take).**

| Step | Bar | Effect |
|---|---|---|
| 1 · the member's price prints | X | nothing for the cluster: the swing does not exist yet. That price may take *other* levels individually (L5.3) |
| 2 · the member confirms | X + R, close | `BSL_CREATED` |
| 3 · it joins, or forms a cluster | same close, **after** that bar's take tests | `members`, `lastBar`; `EQH_CREATED` if the minimum is reached now |
| 4 · the boundary updates (theoretical, L5.4) | same close | no event, same `id` |
| 5 · first bar that can take that boundary | X + R + 1 | `EQH_TAKEN` if `high > bound` |

Order within each bar: level takes → cluster takes → new pivots register and cluster. So a bar never takes a cluster it creates or updates. Past bars are never re-evaluated, so no EQH_TAKEN can come from price that printed before the cluster or its boundary was known. The member's own swing bar cannot take its boundary anyway: it is equal to it, and a take needs *strictly* beyond.

**DEF-L5.6 · Cluster lifecycle.**

```
formed (2 members, id + ref fixed) ──members ≥ min──▶ EQH ACTIVE (EQH_CREATED)
   │   join: members + 1, lastBar, bound = max(bound, member); id / ref / earlier members unchanged
   ├── high > bound before the minimum ──▶ ended silently (never an EQH)
   └── EQH ACTIVE ── high > bound (bar after it is known) ──▶ TAKEN: EQH_TAKEN once, SWEEP | BREAK at that close
memory: 25 clusters per side → oldest taken first, then oldest active (its members released) → EQH_DROPPED_MEMORY
```

**Why the extreme member as reference.** The candidates were the first swing, the average, the highest/lowest, or a tick-normalised centre.
* **Average and centre** move every time a member joins, so the line drifts and the "taken" price changes after the fact.
* **The first swing** is stable, but for an EQH whose second high is higher, it sits *inside* the pool: "taken" would fire before the pool's stops are run.
* **The extreme** is the price that must be exceeded to clear every member. By DEF-L5.4 it is also provably fixed. So it is both the most stable choice and the most truthful one.

**DEF-L6 · Lifecycle and memory.**

```
pivot (judged at X+R) ──rejected──▶ counted only (Data Window verdict 1)
        │ significant
        ▼
ACTIVE level ── high > price ──▶ TAKEN ──close──▶ SWEEP | BREAK   (decided once, same bar)
        │                          │
        │                          ├─ furthest excursion ≤ price + tol → still EQ-eligible (live)
        │                          └─ beyond price + tol → CLOSED (hist)
        ▼
memory policy: per side, live + closed ≤ Engine memory (default 100):
   the oldest CLOSED record goes first, then the oldest live one → BSL/SSL_DROPPED_MEMORY
```

* `live` holds the records that can still change; `hist` holds the closed ones. Hiding, display caps and toggles never move or delete a record.
* EQ clusters: at most 25 per side (a constant). The oldest taken cluster is dropped first, then the oldest active one (its members are released). Every drop is logged: `EQH/EQL_DROPPED_MEMORY`.
* **Incremental processing:** each side keeps a trigger price, the nearest price at which anything on that side can change. A bar that doesn't reach it costs one comparison. Equivalence with a full scan is checked by the model (§ S-07).

**DEF-L7 · Rendering and visual priority.**
* The liquidity view is **rebuilt from state on the last bar**: all of its lines and labels are deleted and redrawn. Nothing is drawn on history and records hold no drawing handles. So drawings cannot diverge from state, and visibility cannot touch state.
* **Active levels:** the `Max active visible per side` levels **nearest to the close** (default 5). Every active BSL is above price and every active SSL below, so "nearest" means the next liquidity in each direction. Ties go to the newest. The style is a thin solid line plus a tiny right-edge label `BSL`/`SSL`, with a tooltip giving the swing time, the known time, the reaction and the touches.
* **EQ pools:** the `Max visible per side` nearest active, qualified clusters (default 3), drawn as a solid line of width 2 labelled `EQH ×n`/`EQL ×n`. Their member levels are not drawn separately.
* **Taken levels:** the `Max taken visible per side` most recently taken (default 2). They are drawn as a faded dotted line ending at the taking bar, with a tiny tag `sweep`/`break`. Defaults: sweeps ON, breaks OFF. They are hidden in Minimal mode.
* **Line start:** `Draw lines from` = Confirmation bar (default; nothing drawn before it was known) or Swing bar (optional backward anchor). EQ lines start at EQ confirmation, or at the first member's swing bar when anchored to the origin.
* **No duplicate lines:** a level or pool at exactly the price of a visible PDH/PDL/PWH/PWL or live session high/low line is not drawn; that line already marks it. The record, its events and its alerts are unaffected. This is counted in the debug row "on a reference line".
* **Logically separate:** PDH/PDL/PWH/PWL and session highs/lows are **not** converted into swing liquidity. They stay in their own engines (a common liquidity-context layer is later work).
* The priority is a single function (`f_drawActive`); replacing "nearest" with a relevance order later is a local change.

---

## 4 · Records

**`Liq`** (one level):

| Field | Meaning |
|---|---|
| `id` | the swing bar's time (stable across reloads; with `isBsl` it is unique) |
| `isBsl` | swing high → BSL; swing low → SSL |
| `price` | the swing extreme |
| `originBar/Time` | swing bar X |
| `confirmBar/Time` | X + right = creation |
| `pivL`, `pivR` | the window in force at birth (swing strength) |
| `react`, `reactReq`, `tra` | reaction (pts), required (pts), TR average at X. Strength in TR = `react / tra` |
| `touches` | exact-price touches before the take |
| `takenBar/Time` | the first bar trading beyond; `na` = active |
| `takeExt` | that bar's high (BSL) / low (SSL): **taken price** reached |
| `takeClose` | that bar's close |
| `takeGap` | the bar opened beyond the level |
| `cls` | `0` until classified, `1` = SWEEP (taken by wick, no close beyond), `2` = BREAK (close beyond) |
| `far` | the furthest price beyond the level since the take (EQ intactness) |
| `eqOpen` | still EQ-eligible |
| `eq` | the cluster it belongs to, or `na` |

"Taken by wick?" corresponds to `cls == SWEEP`; "close beyond?" to `cls == BREAK`. Visual reference: none in the record; the renderer owns its pool (DEF-L7).

**`EqCluster`:** identity: `id` (creation time), `isHigh`, `ref` (creation reference), `originBar/Time` (the first member's swing). State: `bound` (current outer boundary), `members` (participating level ids, append-only, in join order: the first two are the founding members), `lastBar/Time` (latest member's confirmation), `qualBar/Time` (EQ confirmation), `takenBar/Time`, `cls`. The touch count is `members.size()`. See DEF-L5.1.

---

## 5 · Events (once per state transition)

| Event | When | `sid` | price | reason |
|---|---|---|---|---|
| `BSL_CREATED` / `SSL_CREATED` | the confirmation bar of a significant swing | swing time | level | `reaction x×TR ≥ k` |
| `BSL_TAKEN` / `SSL_TAKEN` | the first bar beyond | swing time | level | `+n ticks [· opened beyond]` |
| `BSL_SWEEP` / `SSL_SWEEP` | the taking bar's close, not beyond | swing time | level | `close …` |
| `BSL_BREAK` / `SSL_BREAK` | the taking bar's close, strictly beyond | swing time | level | `close …` |
| `EQH_CREATED` / `EQL_CREATED` | members reach the minimum | cluster id | boundary | `n swings within t ticks` |
| `EQH_TAKEN` / `EQL_TAKEN` | the first bar beyond the current boundary, after the cluster is known | cluster id | boundary | `n swings · sweep/break` |
| `BSL/SSL_DROPPED_MEMORY`, `EQH/EQL_DROPPED_MEMORY` | the memory policy | id | price | `closed record` / `live record · tracking stopped` |

* **Exactly once.** Each event is tied to a field changing from `na` (or 0) to a value, which cannot happen twice. The model checks this on 20,000+ bars (S-07).
* **No event for a cluster join or boundary change.** Membership and boundary are state, visible in the inspector; the cluster's `id` is unchanged.
* **No `SWING_*_CONFIRMED` event.** A significant swing's confirmation *is* `BSL/SSL_CREATED`. Rejected pivots are counted in the debug table and shown in the Data Window, but not logged, because they are not liquidity and would flood the log.
* **Alerts:** liquidity taken, sweep, break, EQH/EQL taken, each covering both sides. **All default OFF**, so an existing "Any alert() function call" alert delivers exactly what it delivered in v0.3.2. Bar-close timing is the default. In Intrabar (experimental) mode, TAKEN may fire at the tick, while SWEEP/BREAK/EQ class still fire at the close.

---

## 6 · Timing and repaint (Confirmed mode, the default)

| Structure | A · Origin bar | B · Confirmation bar | C · First moment knowable | D · First displayed | E · First alert | F · Visual anchor goes back to origin? |
|---|---|---|---|---|---|---|
| BSL/SSL level (significant swing) | swing bar X | X + right | close of X + right | close of X + right, if among the nearest N | none: creation is not alertable | **No by default** (line starts at X + right). Optional "Swing bar" draws from X, *right* bars earlier; events/alerts still carry X + right |
| Rejected pivot | X | X + right | close of X + right (Data Window: 1) | never drawn | never | — |
| Taken | X | the taking bar k > X + right | close of k (Live mode: the tick) | close of k: the line stops at k | close of k (intrabar mode: the tick, experimental) | No |
| Sweep / Break | X | close of k | close of k (both modes) | close of k (tag `sweep`/`break`) | close of k | No |
| EQH/EQL | the first member's swing bar | the confirmation of the member reaching the minimum (q) | close of q | close of q, if among the nearest N | none: creation is not alertable | **No by default** (from q). Origin anchor: from the first member's swing bar |
| EQ join / boundary update | the member's swing bar | its confirmation | close of that bar | the line moves to the new boundary (theoretical, DEF-L5.4) | none | — |
| EQH/EQL taken | — | bar k beyond the current boundary, k > the bar it became known | close of k (Live: the tick) | the EQ line disappears at k | close of k | No |
| Dropped by memory | — | the creation bar of a newer level | that bar | its view disappears | never | — |

**Repaint contract.** With identical data and inputs, a confirmed liquidity event never appears earlier, never disappears, and never changes its bar after reload. Everything is computed from closed bars with fixed windows. The declared exceptions:

1. Warm-up: the first `left + right` bars (no pivots) and the first 14 bars of TR average (rejected).
2. Records outside engine memory (DEF-L6). Near the start of loaded history, the retained set can depend on the first loaded bar.
3. Drawings are rebuilt on the last bar, so scrolling back shows today's active levels, not those active at the scrolled-to time. **The drawings are a view of the present; the records hold history** (as Phase 1 §10.7).

There is **no developing-swing preview** in this build. If one is added, it will be OFF by default, visually distinct, outside confirmed state, and never alerted.

---

## 7 · Phase 1 isolation

The liquidity module reads OHLC/time only. It reads no Phase 1 state. The single exception is the renderer's duplicate-line check, which reads Phase 1 *display* state. With `Enable liquidity engine` OFF, nothing runs and nothing is drawn.

Shared code that changed (each documented in CHANGELOG v0.4.0-dev with WHY / PHASE 1 IMPACT / REPAINT IMPACT / REGRESSION TESTS):

| Change | Phase 1 impact |
|---|---|
| `f_evName(k)` → `f_evName(k, dir)`; `f_evText` skips the BULL/HIGH suffix for liquidity kinds | none: kinds 1–9 return byte-identical text |
| Intrabar alert de-dup key `kind:sid` → `kind:dir:sid` | none: FVG keys were already unique; liquidity needs it (a BSL and an SSL can share a swing time) |
| `f_alertOn` gains 4 cases | none: the new toggles default OFF |
| Debug table 22 → 34 rows; "Last events" moves from row 21 to row 33 (v0.4.0-dev: 32 rows, row 31) | display only; rows 0–20 unchanged |
| v0.4.2-dev: 35 rows, row 34 "Loaded history (closed bars)"; with Debug mode ON, one Pine Logs line per event of a closed bar (the "Last events" text with the full date) | diagnostics only: reads the bar's event list, writes nothing |
| v0.4.3-dev: "Parity capture → Pine Logs" (default OFF): the last N closed bars plus warm-up as machine-readable lines (settings, OHLC, per-bar debug values, events), bounded to N + warm-up bars | diagnostics only: reads values already computed for the Data Window, writes nothing |
| 7 Data Window plots appended after the 11 Phase 1 plots | display only; Phase 1 plot order unchanged |
| Tooltips (`Minimal mode`, `Debug mode`) mention liquidity | text only |
| Event log (cap 40) is shared | debug display only: "Last events" spans less time when liquidity is busy |
| Engine run: the liquidity block runs **after** the Phase 1 block, inside the same `engineTick` gate | none: Phase 1 order and state untouched |

---

## 8 · Performance and resources

* **Per bar:**
  * L1: one SMA of TR plus 4 window extremes (`ta.highest`/`ta.lowest`).
  * L3: per side, one comparison against the trigger price. Only when reached: one pass over that side's live records (≤ memory) and active clusters (≤ 25), plus a trigger recompute.
  * At a confirmation: one pass over clusters plus live records (EQ matching).
* **Last bar only:** rendering selection: (visible slots) × (live records) comparisons per side, at most 20 × 250.
* **Memory:** at most 2 × 100 level records (default; 250 max) and 2 × 25 clusters.
* **Drawings** (lines/labels):
  * default ≤ 20 lines + 20 labels (active 5+5, EQ 3+3, taken 2+2)
  * maximum 80 + 80
  * Phase 1's maximum is about 300 lines, so the worst case is about 380, under the 450 warning and the 500 limit. The existing warning covers it.
* **Requests:** none added (still 2). **Plots:** 18 (limit 64), all Data Window only.
* **Execution time:** not measurable here. It is test L22 (Pine Profiler).

---

## 9 · New settings

| Group | Setting | Default | Tag |
|---|---|---|---|
| LIQUIDITY · CALCULATION | Enable liquidity engine | ON | calc |
| | Sensitivity | Balanced | calc |
| | Swing left bars / right bars / Min reaction × TR average (Custom only) | 5 / 3 / 1.0 | calc |
| | Engine memory · records per side | 100 (20–250) | calc |
| LIQUIDITY · DISPLAY | BSL ■ / SSL ■ | ON / ON | view |
| | Max active visible per side (nearest first) | 5 | view |
| | Draw lines from | Confirmation bar | view |
| | Labels | ON | view |
| | Show sweeps / Show breaks | ON / OFF | view |
| | Max taken visible per side | 2 | view |
| EQH / EQL | Show EQH / EQL | ON | view |
| | Tolerance (ticks) | 4 | calc |
| | Minimum touches | 2 | calc |
| | Max visible per side | 3 | view |
| ALERTS | Liquidity taken · Sweep · Break · EQH/EQL taken | all OFF | alert |
| DEVELOPER | Inspect liquidity level (0 = newest) | 0 | view |

* The general **Right extension** setting is reused for line ends.
* **No "sweep classification mode" input** is exposed: v1 has exactly one rule. The confirmation window (§12) will add the input when it exists.

---

## 10 · Debug additions (Debug mode ON)

**Table rows 21–32:**

| Row | Shows |
|---|---|
| 21 · Liquidity engine | ON/OFF, the preset with its resolved numbers (incl. dominance W bars, or off), EQ tolerance and minimum |
| 22 · Swing highs (loaded history) | pivot candidates · significance PASS · REJECT (share of judged pivots) = reaction + dominance + both (disjoint reasons, v0.4.4-dev) · warm-up (not judgeable: TR average still `na`, or fewer than W bars before the swing) → BSL levels created (= PASS: every PASS creates a level). Counted from the first loaded bar |
| 23 · Swing lows (loaded history) | same for swing lows → SSL |
| 24 · BSL | active, taken (sweep/break), memory use, drops |
| 25 · SSL | same as BSL |
| 26 · EQH · EQL | active, taken, below the minimum, dropped |
| 27 · Liquidity drawn | per kind, plus how many were merged into reference lines |
| 28–31 · Liquidity inspector (n-th newest by confirmation) | type, id, price; swing → known (bars, times, window); significance at birth (reaction pts, × TR, TR, required, PASS/INCONSISTENT); status **of this swing** (ACTIVE + touches, or TAKEN time, reached price + ticks, gap, close, SWEEP/BREAK, touches before) |
| 32 · EQ cluster (pool) | the inspected swing's cluster, separately from the swing: id, **boundary** and **reference** (`= reference`, or both prices plus `DIFFERS`), member count, latest member confirmation, known time or `below min`, ACTIVE or TAKEN time → SWEEP/BREAK |

Row 33 · Last events includes liquidity events. Rows 31 and 32 together make DEF-L5.3 visible: a swing can read TAKEN while its pool reads ACTIVE.

**Data Window plots** (cursor on the confirmation bar):
* swing-high verdict (2 → BSL · 1 rejected · 0) and swing-low verdict
* reaction high and reaction low (pts)
* required reaction (pts)
* BSL and SSL take on this bar (1 sweep · 2 break · 3 taken, bar open)
* dominance reference high and low (v0.4.4-dev): the highest high / lowest low of the W bars before the swing judged on this bar (`na` while warming up, or when dominance is off)

No chart labels are added for debug.

---

## 11 · Known limitations

1. **Classification window = one bar.** "Close beyond, then close back on the next bar" stays BREAK. This is intentional for v1 (§12).
2. **EQ tolerance is in ticks**, so it is not timeframe-adaptive: 4 ticks is tight on 5m.
3. **The reaction floor is weak on noise-like movement** (§2.1); the selection comes mostly from `left`/`right`.
4. **Drawings show the present** (last-bar rebuild): no historical "what was active then" view. Records support it later (bars and times stored).
5. **The duplicate-line check uses the exact price.** A level one tick from PDH is drawn next to the PDH line.
6. **Memory window:** in a long one-directional trend, the oldest *active* levels on the far side (furthest from price) can be dropped. This is logged, and their tracking stops.
7. **Non-extreme cluster members** can be taken while the pool stays active (DEF-L5.3): their stops ran, but the pool's boundary did not. The cluster reports only its boundary; the members' own records keep their takes.
8. **Live mode:** intrabar TAKEN relies on TradingView's rollback of object fields (the same dependency as Phase 1 NR-04). Confirmed mode is immune.
9. **Labels** at the right edge can overlap Phase 1 labels at nearby prices.
10. **Phase 1 reference levels are not unified** with swing liquidity (by design, until a later context layer).
11. **Not compiled here.** TradingView is the authority; T00-style compilation is test L00.
12. **A one-tick run through an EQH ends it** (DEF-L5.4), even when the run forms a new swing within tolerance. The new swing starts a new pool (new id); it does not extend the swept one. With `Minimum touches` ≥ 3, a 2-member group traded through ends silently.

---

## 12 · Extension points (documented, not implemented)

* **Sweep confirmation window W.** Classification would run while `bar_index − takenBar < W` on confirmed bars, from the stored facts. W = 1 is today's rule. This is an additive input with no state-model change.
* **Strict / high-quality sweep (Phase 3).** A separate class from the same facts, plus a reclaim window plus displacement. The structural SWEEP stays as it is.
* **Relevance-ordered display.** Replace the key in `f_drawActive`.
* **TR-relative EQ tolerance.** A second tolerance term, OFF by default.
* **Developing-swing preview:** with the constraints in §6.
* **Liquidity-context layer:** PDH/PDL/PWH/PWL/sessions plus swings in one ranked view (later phase).

---

## 13 · Phase 2 plan (internal order) and status

| Step | Content | State |
|---|---|---|
| P2.1 | Swing detection + confirmation (DEF-L1/L2/L3) | implemented · model-checked · TradingView pending |
| P2.2 | BSL/SSL state engine (DEF-L6) | implemented · model-checked · pending |
| P2.3 | Taken / sweep / break (DEF-L4) | implemented · model-checked · pending |
| P2.4 | Renderer (DEF-L7) | implemented · static-checked · pending |
| P2.5 | EQH/EQL (DEF-L5) | implemented · boundary review done (v0.4.1-dev, DEF-L5.1–L5.6, L35–L42) · model-checked · pending |
| P2.6 | Alerts | implemented (default OFF) · pending |
| P2.7 | Debug + documentation | implemented · pending |
| P2.8 | Phase 1 regression review | static review done (§7); runtime L27 pending |
| **Gate** | All L-tests PASS or FAIL with a fix; Phase 1 regression PASS; your approval | **open** |
