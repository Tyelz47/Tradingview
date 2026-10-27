"""Pine/Python parity layer. Self-tests with synthetic 'observations', then the real file if present."""
import csv
import re

import pytest

from validation import PINE_SOURCE, parity, stats
from validation.candles import random_walk
from validation.golden import candles_of, load_cases
from validation.models.types import Settings

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


def _titles():
    return re.findall(r'^plot\(.*?, "(dbg · [^"]+)"', PINE_SOURCE.read_text(encoding="utf-8"), re.M)


def test_data_window_columns_match_pine_plot_titles():
    """Each column fragment finds exactly one IST plot title, so a renamed plot fails here."""
    titles = [t.lower() for t in _titles()]
    for key, frag in {**parity.SERIES, "mintick": parity.MINTICK}.items():
        assert sum(frag in t for t in titles) == 1, (key, frag)


def _export(path, candles, series, titles, blank=False):
    """A file shaped like TradingView's Export chart data, with the IST plot titles as headers."""
    cols = {k: next(t for t in titles if frag in t.lower()) for k, frag in parity.SERIES.items()}
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close", *cols.values(), next(t for t in titles if parity.MINTICK in t)])
        for i, c in enumerate(candles):
            vals = ["NaN" if blank or series[k][i] is None else series[k][i] for k in cols]
            w.writerow([c.time // 1000, c.open, c.high, c.low, c.close, *vals, "NaN" if blank else 0.25])


def test_data_window_parity_self_check(tmp_path):
    cs = random_walk(1500, 7, gap_prob=0.02)
    obs = {"candles_csv": "x.csv", "tick_size": 0.25, "settings": {"liq": {"preset": "balanced"}}}
    series = parity.oracle_series(cs, Settings.from_dict({**obs["settings"], "tick": 0.25}))
    titles = _titles()
    _export(tmp_path / "x.csv", cs, series, titles)
    r = parity.compare(obs, tmp_path)
    dw = r["data_window"]
    assert r["differences"] == 0 and dw["bars"] == len(cs) - 1, r
    t = dw["totals"]["oracle"]
    assert t == dw["totals"]["pine"]
    assert all((t[s]["pass"], t[s]["reject_or_warmup"], t[s]["sweep"], t[s]["break"]) for s in ("bsl", "ssl"))
    assert t["fvg"]["bull"] and t["fvg"]["bear"] and t["fvg"]["rejected"], t
    from validation.models.ist import run_model                       # the codes agree with the oracle's counters
    m = run_model(cs, Settings.from_dict({**obs["settings"], "tick": 0.25}))
    for side in m.liq.sides():
        k = side.name.lower()
        assert (t[k]["pivots"], t[k]["pass"]) == (side.pivots, side.levels)
        assert t[k]["sweep"] + t[k]["break"] == len({e.bar for e in m.events if e.type == f"{side.name}_TAKEN"})
    assert t["fvg"]["bull"] + t["fvg"]["bear"] == sum(e.type == "FVG_CREATED" for e in m.events)

    series["bsl_pivot"][series["bsl_pivot"].index(2)] = 1             # Pine 'rejected' a swing the oracle kept
    series["liq_required"][100] += 0.01                               # and saw another TR average
    _export(tmp_path / "x.csv", cs, series, titles)
    r = parity.compare(obs, tmp_path)
    assert r["differences"] == 2 and r["data_window"]["by_series"] == {"bsl_pivot": 1, "liq_required": 1}, r

    _export(tmp_path / "x.csv", cs, series, titles, blank=True)       # exported with Debug mode OFF
    with pytest.raises(ValueError, match="Debug mode"):
        parity.compare(obs, tmp_path)


def test_observed_tradingview_data():
    result = parity.run()
    stats.RESULTS["parity"] = result
    if result["status"] == "NO OBSERVED DATA":
        pytest.skip(f"parity is PENDING (manual TradingView data): "
                    f"{result.get('reason', 'validation/parity/pine_observed.json not present')}")
    assert result["differences"] == 0, result
