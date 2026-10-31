"""The CISD freeze evidence: the real TradingView capture of IST v0.7.1-dev (MNQ 1m in Bar Replay,
1,000 bars + 76 warm-up, 2026-10-13 19:57 → 2026-10-14 13:52 New York; validation/parity/evidence,
kept byte for byte). Every module compared, 0 DIFFERENCE: Phase 1 / Phase 2 series and events, LRL
(after the v0.7.1-dev fix), HTF FVG and CISD (restored state, per bar and per event, and the
definition oracle started UNKNOWN, synchronised, then identical)."""
import pytest

from validation.parity import CAPTURE_V071, capture, manual

pytestmark = [pytest.mark.cisd, pytest.mark.section("parity")]


@pytest.fixture(scope="module")
def r():
    return capture.compare(capture.parse(CAPTURE_V071.read_text(encoding="utf-8")))


def test_v071_capture_is_exact_everywhere(r):
    assert r["differences"] == 0, [c["text"] for c in r["checks"] if c["status"] == manual.DIFF][:5]
    assert r["capture_build"] == "v0.7.1-dev"
    assert (r["compared_bars"], r["series"], r["matched_events"]) == (1043, 9, 1027)
    assert (r["counts"][manual.MATCH], r["counts"][manual.NOBS]) == (67, 9)
    assert (r["lrl"]["events"], r["lrl"]["boundaries"], r["lrl"]["cand_bars"]) == (49, 322, 2000)
    assert (r["htf"]["candles"], r["htf"]["events"], r["htf"]["open_bars"]) == (126, 139, 1075)


def test_v071_cisd_is_exact_from_a_restored_state_and_from_unknown(r):
    c = r["cisd"]
    assert (c["bars"], c["events"], c["cold"]) == (1075, 188, 94)
    text = [x["text"] for x in r["checks"] if x["section"] == "cisd"]
    assert any("CISD_CONFIRMED: 94" in t for t in text) and any("CISD_DROPPED_MEMORY: 94" in t for t in text)
    assert any("synchronised on" in t and "then 94 CISDs identical" in t for t in text)
    nobs = [x["text"] for x in r["checks"] if x["section"] == "cisd" and x["status"] == manual.NOBS]
    assert nobs == ["3 not compared: body / TR of a CISD in the first bars (the replay's TR average is still warming up)"]
