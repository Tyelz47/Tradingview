#!/usr/bin/env python3
"""Reference model of the IST liquidity engine (DEF-L1…L6), v0.4.0-dev.

Mirrors src/IST.pine bar by bar in Confirmed mode (every bar is a closed bar).
It checks the ALGORITHM, not Pine: compilation and runtime stay TradingView's job.
Run:  python tests/liq_model.py      (exit code 0 = all checks passed)
"""
import random

TICK = 0.25
EPS = TICK * 0.01
SWEEP, BREAK = 1, 2


class Rec:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class Side:
    def __init__(self, bsl):
        self.bsl, self.live, self.hist, self.eqs, self.trig = bsl, [], [], [], None
        self.pivots = self.levels = 0


class Engine:
    def __init__(self, L, R, K, tol_ticks=4, min_touch=2, memory=100, eq_mem=25, tra_len=14, gate=True):
        self.L, self.R, self.K, self.tol = L, R, K, tol_ticks * TICK
        self.min_touch, self.memory, self.eq_mem, self.tra_len, self.gate = min_touch, memory, eq_mem, tra_len, gate
        self.H, self.Lo, self.C, self.TR, self.events = [], [], [], [], []
        self.bsl, self.ssl = Side(True), Side(False)

    # ── helpers mirroring the Pine methods ──
    def emit(self, kind, side, id_, price):
        self.events.append((self.t, kind, "B" if side.bsl else "S", id_, price))

    def pen(self, side, p):
        return self.h - p if side.bsl else p - self.l

    def trigger(self, side):
        v = [x.price if x.taken is None else x.far for x in side.live]
        v += [c.price for c in side.eqs if c.taken is None]
        return None if not v else (min(v) if side.bsl else max(v))

    def take(self, side, x):
        x.taken, x.ext = self.t, (self.h if side.bsl else self.l)
        x.far, x.gap = x.ext, (self.o > x.price if side.bsl else self.o < x.price)
        self.emit("TAKEN", side, x.id, x.price)
        x.close = self.c
        x.cls = BREAK if (self.c > x.price if side.bsl else self.c < x.price) else SWEEP
        self.emit("BREAK" if x.cls == BREAK else "SWEEP", side, x.id, x.price)

    def step(self, side):
        if side.trig is None or (self.gate and self.pen(side, side.trig) < 0):
            return
        for i in range(len(side.live) - 1, -1, -1):
            x = side.live[i]
            if self.t > x.confirm:
                p = self.pen(side, x.price)
                if x.taken is None:
                    if p > 0:
                        self.take(side, x)
                    elif p == 0:
                        x.touches += 1
                elif self.pen(side, x.far) > 0:
                    x.far = self.h if side.bsl else self.l
                if x.taken is not None and p > self.tol + EPS:
                    x.eq_open = False
                    side.hist.append(side.live.pop(i))
        for c in side.eqs:
            if c.taken is None and self.pen(side, c.price) > 0:
                c.taken = self.t
                c.cls = BREAK if (self.c > c.price if side.bsl else self.c < c.price) else SWEEP
                if c.qual is not None:
                    self.emit("EQ_TAKEN", side, c.id, c.price)
        side.trig = self.trigger(side)

    def drop_cluster(self, side):
        victim = next((i for i, c in enumerate(side.eqs[:-1]) if c.taken is not None), 0)
        old = side.eqs.pop(victim)
        if old.taken is None:
            for m in side.live:
                if m.eq is old:
                    m.eq = None
        self.emit("EQ_DROPPED", side, old.id, old.price)

    def cluster(self, side, x):
        hit, best = None, None
        for c in side.eqs:
            d = abs(x.price - c.price)
            if c.taken is None and d <= self.tol + EPS and (best is None or d <= best):
                best, hit = d, c
        if hit is None:
            seed = None
            for m in side.live:
                d = abs(x.price - m.price)
                intact = m.taken is None or (x.price >= m.far if side.bsl else x.price <= m.far)
                if m.eq is None and intact and d <= self.tol + EPS and (best is None or d <= best):
                    best, seed = d, m
            if seed is not None:
                px = max(seed.price, x.price) if side.bsl else min(seed.price, x.price)
                hit = Rec(id=self.t, price=px, members=[seed.id], origin=seed.origin, first_confirm=seed.confirm,
                          created=self.t, qual=None, taken=None, cls=0)
                seed.eq = hit
                side.eqs.append(hit)
                if len(side.eqs) > self.eq_mem:
                    self.drop_cluster(side)
        if hit is not None:
            hit.members.append(x.id)
            x.eq = hit
            if hit.qual is None and len(hit.members) >= self.min_touch:
                hit.qual = self.t
                self.emit("EQ_CREATED", side, hit.id, hit.price)

    def register(self, side, px, X, react, req, tra):
        x = Rec(id=X, price=px, origin=X, confirm=self.t, react=react, req=req, tra=tra, touches=0, taken=None,
                ext=None, close=None, gap=False, cls=0, far=None, eq_open=True, eq=None)
        self.emit("CREATED", side, x.id, px)
        self.cluster(side, x)
        side.live.append(x)
        side.levels += 1
        side.trig = px if side.trig is None else (min(side.trig, px) if side.bsl else max(side.trig, px))
        if len(side.live) + len(side.hist) > self.memory:
            if side.hist:
                old = side.hist.pop(0)
            else:
                old = side.live.pop(0)
                side.trig = self.trigger(side)
            self.emit("DROPPED", side, old.id, old.price)

    # ── one closed bar: L1 → L2/L4 → L3 (step, then register), as in the Pine engine run ──
    def bar(self, o, h, l, c):
        self.t = t = len(self.H)
        self.o, self.h, self.l, self.c = o, h, l, c
        tr = h - l if not self.C else max(h - l, abs(h - self.C[-1]), abs(l - self.C[-1]))
        self.H.append(h); self.Lo.append(l); self.C.append(c); self.TR.append(tr)
        self.step(self.bsl)
        self.step(self.ssl)
        X = t - self.R
        if X - self.L < 0:
            return
        tra = sum(self.TR[X - self.tra_len + 1:X + 1]) / self.tra_len if X >= self.tra_len - 1 else None
        req = None if tra is None else self.K * tra
        hiR, loR = max(self.H[X + 1:t + 1]), min(self.Lo[X + 1:t + 1])
        if self.H[X] > max(self.H[X - self.L:X]) and self.H[X] >= hiR:
            self.bsl.pivots += 1
            if req is not None and self.H[X] - loR >= req:
                self.register(self.bsl, self.H[X], X, self.H[X] - loR, req, tra)
        if self.Lo[X] < min(self.Lo[X - self.L:X]) and self.Lo[X] <= loR:
            self.ssl.pivots += 1
            if req is not None and hiR - self.Lo[X] >= req:
                self.register(self.ssl, self.Lo[X], X, hiR - self.Lo[X], req, tra)


WARM = [(100, 101, 99, 100)] * 20      # flat highs/lows: no pivots, TR average = 2


def run(bars, L=2, R=1, K=0.0, **kw):
    e = Engine(L, R, K, **kw)
    for b in WARM + bars:
        e.bar(*b)
    return e


def ev(e, kind=None, side=None, id_=None):
    return [x for x in e.events if (kind is None or x[1] == kind) and (side is None or x[2] == side)
            and (id_ is None or x[3] == id_)]


SWING_HI = [(100, 102, 99.5, 101), (101, 101.5, 99, 99.5)]           # BSL 102: swing bar 20, known at 21


# ── scenario checks (numbers = TESTS_PHASE2 ids they support) ──
def s_confirmation_timing():                                          # L01, L03, L14
    e = run(SWING_HI)
    assert [x[:4] for x in e.events] == [(21, "CREATED", "B", 20)], e.events
    x = e.bsl.live[0]
    assert (x.origin, x.confirm, x.price) == (20, 21, 102)


def s_flat_top_one_swing():                                           # DEF-L1 tie rule
    e = run([(100, 102, 99.5, 101), (101, 102, 99.5, 101), (101, 101, 99.2, 100), (100, 100.5, 99.3, 100)])
    assert [(x[3], x[4]) for x in ev(e, "CREATED", "B")] == [(20, 102)]


def s_exact_touch_is_not_taken():                                     # edge: exact tick
    e = run(SWING_HI + [(99.5, 101, 99, 100), (100, 102, 99.2, 100)])
    assert not ev(e, "TAKEN") and e.bsl.live[0].touches == 1


def s_wick_through_close_back_is_sweep():                             # L09
    e = run(SWING_HI + [(99.5, 102.25, 99, 101.5)])
    assert [x[1] for x in ev(e, side="B")] == ["CREATED", "TAKEN", "SWEEP"]
    assert ev(e, "TAKEN")[0][0] == ev(e, "SWEEP")[0][0] == 22


def s_close_exactly_at_level_is_sweep():                              # edge: close == level
    e = run(SWING_HI + [(99.5, 102.25, 99, 102)])
    assert [x[1] for x in ev(e, side="B")] == ["CREATED", "TAKEN", "SWEEP"]


def s_close_beyond_is_break():                                        # L11
    e = run(SWING_HI + [(99.5, 103, 99, 102.25)])
    assert [x[1] for x in ev(e, side="B")] == ["CREATED", "TAKEN", "BREAK"]


def s_break_then_reclaim_stays_break():                               # edge: 2nd candle closes back; L13
    e = run(SWING_HI + [(99.5, 102.5, 99, 102.25), (102.25, 102.75, 100, 100.5), (100.5, 103.5, 100, 103)])
    kinds = [x[1] for x in ev(e, side="B", id_=20)]
    assert kinds == ["CREATED", "TAKEN", "BREAK"], kinds


def s_gap_through():                                                  # edge: gap
    e = run(SWING_HI + [(102.5, 103, 102.25, 102.75)])
    x = (e.bsl.live + e.bsl.hist)[0]
    assert x.gap and x.cls == BREAK


def s_one_tick_penetration():                                         # edge: very small penetration
    e = run(SWING_HI + [(99.5, 102.25, 99, 101)])
    assert ev(e, "TAKEN")[0][3] == 20 and (e.bsl.live + e.bsl.hist)[0].ext == 102.25


def s_repeated_attacks_fire_once():                                   # L07, L16
    e = run(SWING_HI + [(99.5, 102.25, 99, 101), (101, 102.5, 100, 101), (101, 102.25, 100, 101.5), (101, 104, 100, 103.5)])
    for k in ("TAKEN", "SWEEP", "BREAK"):
        assert len(ev(e, k, "B", 20)) <= 1
    assert len(ev(e, "TAKEN", "B", 20)) == 1


def s_ssl_mirror():                                                   # L02, L04, L10, L12, L08
    lo = [(100, 100.5, 98, 99), (99, 101, 98.5, 100.5)]             # SSL 98: swing bar 20, known at 21
    e = run(lo + [(100.5, 101, 97.75, 98.5)])
    assert [x[1] for x in ev(e, side="S")] == ["CREATED", "TAKEN", "SWEEP"]
    e = run(lo + [(100.5, 101, 97, 97.5)])
    assert [x[1] for x in ev(e, side="S")] == ["CREATED", "TAKEN", "BREAK"]


EQ_BASE = SWING_HI + [(99.5, 100, 98, 98.5), (98.5, 99, 97.5, 98)]  # BSL 102 (id 20) active; bars 22-23 lower


def s_eqh_second_lower_within_tol():                                  # L17
    e = run(EQ_BASE + [(98, 101.5, 97.8, 101), (101, 101, 99, 99.5)])
    c = e.bsl.eqs[0]
    assert ev(e, "EQ_CREATED", "B") and c.price == 102 and c.members == [20, 24]


def s_eqh_second_higher_within_tol():                                 # L17 (1st level swept by 1 tick, pool intact)
    e = run(EQ_BASE + [(98, 102.25, 97.8, 101.5), (101.5, 101.75, 99, 99.5)])
    assert [x[1] for x in ev(e, side="B", id_=20)] == ["CREATED", "TAKEN", "SWEEP"]
    c = e.bsl.eqs[0]
    assert c.price == 102.25 and c.members == [20, 24]


def s_outside_tolerance_no_cluster():                                 # L19
    e = run(EQ_BASE + [(98, 100.75, 97.8, 100.5), (100.5, 100.5, 99, 99.5)])   # 5 ticks below
    assert ev(e, "CREATED", "B", 24) and not e.bsl.eqs


def s_cluster_does_not_duplicate_and_taken_once():                    # L20, L21
    bars = EQ_BASE + [(98, 101.5, 97.8, 101), (101, 101, 99, 99.5),
                      (99.5, 100, 98.5, 99), (99, 99.25, 98.6, 99), (99, 101.75, 98.7, 101), (101, 101.25, 100, 100.5),
                      (100.5, 102.25, 100.2, 101.75), (101.75, 103, 101, 102.5)]
    e = run(bars)
    assert len(e.bsl.eqs) == 1 and e.bsl.eqs[0].members == [20, 24, 28], [c.members for c in e.bsl.eqs]
    assert len(ev(e, "EQ_CREATED", "B")) == 1 and len(ev(e, "EQ_TAKEN", "B")) == 1
    assert ev(e, "EQ_TAKEN", "B")[0][0] == 30 and e.bsl.eqs[0].cls == SWEEP


def s_pool_not_intact_no_cluster():                                   # DEF-L5 intact rule
    # 102 taken at bar 24 (furthest 102.5, rejected pivot: reaction too small); new swing 102.25 < 102.5
    bars = EQ_BASE + [(98, 102.5, 97.8, 102.3), (102.25, 102.25, 102, 102), (102, 102, 101, 101.25),
                      (101.25, 101.5, 100.5, 101), (101, 101.5, 100.5, 101), (101, 102.25, 100.75, 102),
                      (102, 102, 99.5, 100)]
    e = run(bars, K=1.0)
    assert ev(e, "CREATED", "B", 20) and not ev(e, "CREATED", "B", 24), "102.5 must be rejected (small reaction)"
    assert ev(e, "CREATED", "B", 29), "102.25 must become a level"
    assert not e.bsl.eqs, "102 was traded beyond 102.25: no intact pool"


def s_significance_filter():                                          # DEF-L2
    weak = run([(100, 102, 99.5, 101), (101, 101.75, 100.5, 101)], K=1.0)    # reaction 1.5 < ~2.04
    strong = run([(100, 102, 99.5, 101), (101, 101.75, 99, 99.5)], K=1.0)    # reaction 3.0
    assert weak.bsl.pivots == 1 and not weak.bsl.live
    assert strong.bsl.live and abs(strong.bsl.live[0].req - 2.0357142857) < 1e-6


def s_memory_policy():                                                # deliberate, logged drops
    e = Engine(2, 1, 0.0, memory=3, tol_ticks=0)
    for b in WARM:
        e.bar(*b)
    p = 102.0
    for k in range(6):                       # 6 lower highs (swing bars 20, 23, …, 35), never taken
        p -= 0.5
        e.bar(p - 1, p, p - 2, p - 1.5)
        e.bar(p - 1.5, p - 2, p - 4, p - 3.5)
        e.bar(p - 3.5, p - 2.5, p - 5, p - 4)
    drops = ev(e, "DROPPED", "B")
    assert len(drops) == 3 and len(e.bsl.live) == 3 and not e.bsl.hist, (drops, len(e.bsl.live))
    assert [d[3] for d in drops] == [20, 23, 26], drops   # oldest live first when nothing is closed
    # with closed records present, the oldest CLOSED one goes first
    e2 = run(SWING_HI + [(99.5, 104, 99, 103.5)] + [(103.5, 106, 103, 105.5), (105.5, 105, 102, 102.5)], memory=1)
    assert [d[3] for d in ev(e2, "DROPPED", "B")] == [20], e2.events


def fuzz(n_bars=20000, seed=7):
    """Invariants on a random walk, Balanced preset, and gate-on == gate-off."""
    rnd = random.Random(seed)
    bars, c = [], 20000.0
    for _ in range(n_bars):
        o = c
        moves = [rnd.choice([-1, 1]) * rnd.randint(0, 12) * TICK for _ in range(4)]
        path = [o]
        for m in moves:
            path.append(path[-1] + m)
        c = path[-1]
        bars.append((o, max(path), min(path), c))
    a = Engine(5, 3, 1.0, tol_ticks=4, gate=True)
    b = Engine(5, 3, 1.0, tol_ticks=4, gate=False)
    for x in bars:
        a.bar(*x)
        b.bar(*x)
    assert a.events == b.events, "trigger gate changed the result"
    seen = {}
    for t, k, s, i, _ in a.events:
        if k in ("CREATED", "TAKEN", "SWEEP", "BREAK", "EQ_CREATED", "EQ_TAKEN"):
            assert (k, s, i) not in seen, ("twice", k, s, i)
            seen[(k, s, i)] = t
    for (k, s, i), t in seen.items():
        if k == "CREATED":
            assert t == i + 3, "known exactly at swing bar + right"
        if k == "TAKEN":
            assert t > seen[("CREATED", s, i)], "taken after confirmation"
            assert (("SWEEP", s, i) in seen) != (("BREAK", s, i) in seen), "exactly one class"
            assert seen.get(("SWEEP", s, i), seen.get(("BREAK", s, i))) == t, "classified on the taking bar"
    H, Lo = a.H, a.Lo
    n_eq = 0
    for side, sgn in ((a.bsl, 1), (a.ssl, -1)):
        for c in side.eqs:
            n_eq += 1
            prices = [x.price for x in side.live + side.hist if x.id in c.members]
            assert all(0 <= sgn * (c.price - p) <= a.tol + EPS for p in prices), "members within tolerance, inside the edge"
            end = c.taken if c.taken is not None else len(H)
            seg = range(c.first_confirm + 1, end)
            beyond = [H[j] > c.price for j in seg] if side.bsl else [Lo[j] < c.price for j in seg]
            assert not any(beyond), "pool intact from first member's confirmation until taken"
            if c.taken is not None:
                assert (H[c.taken] > c.price) if side.bsl else (Lo[c.taken] < c.price)
    return a, n_eq


if __name__ == "__main__":
    checks = [v for k, v in sorted(globals().items()) if k.startswith("s_")]
    for f in checks:
        f()
        print("PASS", f.__name__)
    a, n_eq = fuzz()
    print("PASS fuzz: %d bars, BSL %d/%d levels/pivots, SSL %d/%d, %d events, %d EQ clusters, gate on == gate off"
          % (len(a.H), a.bsl.levels, a.bsl.pivots, a.ssl.levels, a.ssl.pivots, len(a.events), n_eq))
