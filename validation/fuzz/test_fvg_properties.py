"""Property tests · Phase 1 FVG (Hypothesis). Every example runs with all invariants checked."""
import pytest
from hypothesis import given
from hypothesis import strategies as st

from validation.candles import mirror, shift
from validation.fuzz.helpers import checked, compare, event_set, mirrored, run, shifted
from validation.fuzz.strategies import candle_lists, fvg_settings, view_settings
from validation.models.types import Settings

pytestmark = [pytest.mark.phase1, pytest.mark.section("property")]
FVG_ONLY = ("fvg",)


@given(candle_lists(), fvg_settings)
def test_fvg_invariants_hold(candles, fs):
    checked("test_fvg_invariants_hold", candles, Settings(modules=FVG_ONLY, fvg=fs), "property.examples")


@given(candle_lists(), fvg_settings)
def test_fvg_mirror_symmetry(candles, fs):
    """Reflecting prices turns every bull FVG into a bear FVG with reflected prices, and vice versa."""
    s = Settings(modules=FVG_ONLY, fvg=fs)
    pivot = 20000.0
    a, b = run(candles, s), run(mirror(candles, pivot), s)
    compare("test_fvg_mirror_symmetry", candles, s, mirrored(event_set(a), pivot), event_set(b), "mirror symmetry")
    from validation import stats
    stats.bump("property.examples")


@given(candle_lists(), fvg_settings, st.integers(-400, 400))
def test_fvg_translation_invariance(candles, fs, ticks):
    s = Settings(modules=FVG_ONLY, fvg=fs)
    pts = ticks * 0.25
    a, b = run(candles, s), run(shift(candles, pts), s)
    compare("test_fvg_translation_invariance", candles, s, shifted(event_set(a), pts), event_set(b), "translation invariance")
    from validation import stats
    stats.bump("property.examples")


@given(candle_lists(), fvg_settings, view_settings)
def test_fvg_view_settings_do_not_change_logic(candles, fs, view):
    a = run(candles, Settings(modules=FVG_ONLY, fvg=fs))
    b = run(candles, Settings(modules=FVG_ONLY, fvg=fs, view=view))
    assert a.canonical_events() == b.canonical_events() and a.state() == b.state()
    from validation import stats
    stats.bump("property.examples")


@given(candle_lists(min_size=12), fvg_settings, st.data())
def test_fvg_no_lookahead(candles, fs, data):
    """Causality: the events up to bar n do not depend on bars after n (nothing repaints)."""
    n = data.draw(st.integers(3, len(candles)))
    s = Settings(modules=FVG_ONLY, fvg=fs)
    full, prefix = run(candles, s), run(candles[:n], s)
    assert [e for e in full.events if e.bar < n] == prefix.events
    from validation import stats
    stats.bump("property.examples")
