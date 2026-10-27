"""Hypothesis strategies: valid, tick-aligned NQ candle sequences and settings.

Every generated candle satisfies high ≥ max(open, close), low ≤ min(open, close),
high ≥ low, on the 0.25 tick grid (built in integer ticks, see candles.from_ticks).
Small integers (which Hypothesis favours and shrinks towards) produce flat bars,
equal highs, exact touches and plateaus: the edge cases that matter here.
"""
from hypothesis import strategies as st

from validation.candles import from_ticks
from validation.models.types import FvgSettings, LiqSettings, Settings, ViewSettings

GAP = st.one_of(st.just(0), st.just(0), st.just(0), st.integers(-12, 12))       # mostly continuous opens
SPEC = st.tuples(GAP, st.integers(-16, 16), st.integers(0, 10), st.integers(0, 10))


def candle_lists(min_size: int = 8, max_size: int = 160):
    return st.lists(SPEC, min_size=min_size, max_size=max_size).map(from_ticks)


fvg_settings = st.builds(FvgSettings, min_ticks=st.sampled_from([1, 2, 4]), k_tra=st.sampled_from([0.0, 0.1, 0.5]),
                         k_rng=st.sampled_from([0.0, 0.25]), length=st.sampled_from([2, 5, 14]),
                         memory=st.sampled_from([10, 50]))

liq_settings = st.builds(LiqSettings, left=st.integers(1, 6), right=st.integers(1, 4),
                         k=st.sampled_from([0.0, 0.5, 1.0, 2.0]), tol_ticks=st.sampled_from([0, 2, 4, 8]),
                         min_touch=st.sampled_from([2, 3]), memory=st.sampled_from([20, 100]),
                         eq_memory=st.sampled_from([2, 25]))

view_settings = st.builds(ViewSettings, fvg_show=st.booleans(),
                          mit_rule=st.sampled_from(["firstTouch", "midpoint", "fullFill", "closeThrough"]),
                          fvg_max_visible=st.integers(1, 30), minimal=st.booleans(), liq_max_visible=st.integers(0, 20),
                          eq_max_visible=st.integers(0, 10), liq_max_taken=st.integers(0, 10),
                          show_sweeps=st.booleans(), show_breaks=st.booleans())


@st.composite
def full_settings(draw):
    return Settings(fvg=draw(fvg_settings), liq=draw(liq_settings))
