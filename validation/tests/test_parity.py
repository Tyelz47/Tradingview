"""Pine/Python parity layer. Self-test with synthetic 'observations', then the real file if present."""
import pytest

from validation import stats
from validation import parity
from validation.golden import candles_of, load_cases

pytestmark = [pytest.mark.common, pytest.mark.section("parity")]


def _observed_from_oracle(case_id):
    """A fake 'Pine observation' built from the oracle's own run of a golden case."""
    case = next(c for _, c in load_cases() if c["id"] == case_id)
    cs = candles_of(case)
    from validation.golden import settings_of
    from validation.models.ist import run_model
    m = run_model(cs, settings_of(case))
    return {"timezone": case["timezone"], "tick_size": case["tick_size"], "settings": case["settings"],
            "candles": [[c.time, c.open, c.high, c.low, c.close] for c in cs], "complete": True,
            "observed_events": [{"time": e.time, "type": e.type, "dir": e.dir, "sid": e.sid, "price": e.price}
                                for e in m.events]}


def test_parity_layer_self_check():
    obs = _observed_from_oracle("GOLD_EQ_001")
    assert parity.compare(obs)["differences"] == 0
    obs["observed_events"][-1]["price"] += 0.25                       # Pine 'saw' another price
    del obs["observed_events"][0]                                     # and missed one event
    r = parity.compare(obs)
    assert len(r["mismatched"]) == 1 and len(r["not_observed_in_pine"]) == 1, r


def test_observed_tradingview_data():
    result = parity.run()
    stats.RESULTS["parity"] = result
    if result["status"] == "NO OBSERVED DATA":
        pytest.skip("validation/parity/pine_observed.json not present: parity is PENDING (manual TradingView data)")
    assert result["differences"] == 0, result
