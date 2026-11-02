"""IFVG research study (validation/studies/ifvg.py, docs/STUDY_IFVG.md): the harness is trustworthy.
IF2 is exactly the frozen Phase 1 invalidation; a wick comes no later than a close; IF4 waits for an
earlier full fill; the candidates are mirror-symmetric and never look ahead; the numbers the study
quotes reproduce."""
import pytest

from validation.candles import mirror, random_walk
from validation.studies import displacement as dsp
from validation.studies import ifvg as study

pytestmark = [pytest.mark.ifvg, pytest.mark.section("research.ifvg")]
KINDS = ("IF1", "IF2", "IF3", "IF4", "IF5")


@pytest.fixture(scope="module")
def uni():
    return study.universe(dsp.segments())


def test_if2_is_the_frozen_phase_1_invalidation(uni):
    for cs, ctx, ps in uni:
        assert all(study.trigger(p, cs, ctx, "IF2") == p.inv for p in ps)


def test_wick_first_and_full_fill_before_if4(uni):
    for cs, ctx, ps in uni:
        for p in ps:
            t1, t2, t4 = (study.trigger(p, cs, ctx, k) for k in ("IF1", "IF2", "IF4"))
            assert t2 is None or (t1 is not None and t1 <= t2)
            assert t4 is None or (p.full is not None and p.full < t4 and t4 >= t2)


@pytest.fixture(scope="module")
def walk():
    cs = random_walk(800, 7, gap_prob=0.03)
    mm, part = mirror(cs, 0.0), cs[:500]
    return {k: (c, study.context(c), study.parents(c, 0)) for k, c in (("cs", cs), ("mirror", mm), ("part", part))}


@pytest.mark.parametrize("kind", KINDS)
def test_candidates_are_mirror_symmetric_and_never_look_ahead(walk, kind):
    trig = lambda key: {(p.confirm, -p.d if key != "mirror" else p.d, study.trigger(p, walk[key][0], walk[key][1], kind))
                        for p in walk[key][2]}
    assert trig("cs") == trig("mirror")
    early = {x for x in trig("part") if x[2] is not None}
    assert early == {x for x in trig("cs") if x[2] is not None and x[2] < 500}


def test_numbers_quoted_by_the_study(uni):
    rows = study.candidate_rows(uni)
    if2 = next(r for r in rows if r.startswith("| IF2 "))
    assert "| 652 | 566 (87%) | 272 · 294 | 9.0 |" in if2
    life = "\n".join(study.lifecycle_rows(uni))
    assert "IF2 inversions: 566" in life and "| retest: the near edge reached | 82% |" in life
