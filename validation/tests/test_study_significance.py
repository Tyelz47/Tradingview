"""Phase 2 liquidity significance study (validation/studies): the harness is trustworthy,
the dominance feature is exact at its boundaries, and the recommended candidate keeps
the properties the study claims. No indicator or oracle change is tested here."""
import pytest

from validation.candles import random_walk
from validation.models.ist import IstModel
from validation.models.types import PRESETS, Candle, Settings
from validation.parity import capture
from validation.studies import liquidity_significance as study

pytestmark = [pytest.mark.phase2, pytest.mark.section("phase2.swing")]


def _nq():
    return [b["candle"] for b in capture.parse(study.DATA.read_text(encoding="utf-8"))["bars"]]


@pytest.mark.parametrize("preset", sorted(PRESETS))
def test_study_engine_reproduces_the_oracle(preset):
    """With the current DEF-L2 as its test, the study engine emits exactly the oracle's events."""
    cs, k = _nq(), PRESETS[preset][2]
    s = Settings.from_dict({"liq": {"preset": preset}, "modules": ["liq"]})
    want = [e.compact() for e in IstModel(s).run(cs).events]
    assert [e.compact() for e in study._run(cs, preset, lambda c: c.react >= k)] == want and want


def _bars(highs, mirror=False):
    """One-minute bars with these highs (range 1 point); mirror=True turns them into lows."""
    out = []
    for i, h in enumerate(highs):
        c = Candle(i * 60_000, h - 0.5, h, h - 1, h - 0.5)
        out.append(Candle(c.time, -c.open, -c.low, -c.high, -c.close) if mirror else c)
    return out


@pytest.mark.parametrize("mirror", [False, True])
def test_dominance_boundaries(mirror):
    """X = 30 is a Balanced pivot. An earlier high exactly at + tolerance (4 ticks = 1 point)
    keeps dominance; one tick more breaks it; outside the window it does not count."""
    seen = {}

    def record(c):
        seen[c.X] = (c.dominates(25), c.dominates(15))
        return False

    for prior, want in ((110.0, (True, True)), (110.25, (False, True))):
        highs = [100 + (i % 2) * 0.25 for i in range(40)]
        highs[10], highs[30] = prior, 109.0
        seen.clear()
        study._run(_bars(highs, mirror), "balanced", record)
        assert seen[30] == want, (prior, seen)


@pytest.mark.parametrize("seed", [1, 2])
@pytest.mark.parametrize("preset, w", [("aggressive", 10), ("balanced", 30), ("strict", 60)])
def test_dominance_candidate_is_a_subset_with_identical_takes(preset, w, seed):
    """Adding dominance only removes levels; every kept level is taken, swept or broken
    exactly as today (on the NQ capture and on random walks)."""
    k = PRESETS[preset][2]
    for cs in (_nq(), random_walk(4000, seed, gap_prob=0.02)):
        cur = study._run(cs, preset, lambda c: c.react >= k)
        new = study._run(cs, preset, lambda c: c.react >= k and c.dominates(w))
        made = lambda ev: {(e.dir, e.sid) for e in ev if e.type in ("BSL_CREATED", "SSL_CREATED")}
        keep = made(new)
        takes = lambda ev: sorted((e.type, e.dir, e.sid, e.bar) for e in ev
                                  if e.type.split("_", 1)[1] in ("TAKEN", "SWEEP", "BREAK")
                                  and e.type[:3] in ("BSL", "SSL") and (e.dir, e.sid) in keep)
        assert keep <= made(cur) and takes(new) == takes(cur)
        assert len(keep) < len(made(cur))
