"""The displacement evidence (DISP-L10): the real TradingView capture of IST v0.8.0-dev (MNQ 1m in
Bar Replay, 1,000 bars + 76 warm-up, 2026-10-29 19:56 → 2026-10-30 13:51 New York;
validation/parity/evidence, kept byte for byte). Every module compared, 0 DIFFERENCE; displacement
per bar (verdict, A, body / A, close position, FVG metadata), per event, and every snapshot record."""
import pytest

from validation.parity import CAPTURE_V080, capture, manual

pytestmark = [pytest.mark.disp, pytest.mark.section("parity")]


@pytest.fixture(scope="module")
def r():
    return capture.compare(capture.parse(CAPTURE_V080.read_text(encoding="utf-8")))


def test_v080_capture_is_exact_everywhere(r):
    assert r["differences"] == 0, [c["text"] for c in r["checks"] if c["status"] == manual.DIFF][:5]
    assert r["capture_build"] == "v0.8.0-dev"
    assert (r["compared_bars"], r["series"], r["matched_events"]) == (1043, 9, 947)
    assert (r["counts"][manual.MATCH], r["counts"][manual.NOBS]) == (75, 12)
    assert (r["lrl"]["events"], r["lrl"]["boundaries"], r["lrl"]["cand_bars"]) == (38, 144, 1980)
    assert (r["htf"]["candles"], r["htf"]["events"], r["htf"]["open_bars"]) == (126, 118, 1075)
    assert (r["cisd"]["bars"], r["cisd"]["events"], r["cisd"]["cold"]) == (1075, 170, 85)


def test_v080_displacement_is_exact(r):
    d = r["disp"]
    assert (d["bars"], d["events"], d["records"]) == (1060, 44, 50)
    text = [x["text"] for x in r["checks"] if x["section"] == "disp"]
    assert any("DISPLACEMENT_CONFIRMED: 22" in t for t in text) and any("DISPLACEMENT_DROPPED_MEMORY: 22" in t for t in text)
    assert any("per bar: verdict, A, body / A, close position, FVG metadata: 1060 bars" in t for t in text)
    settings = [x for x in r["checks"] if x["section"] == "settings" and x["text"].startswith("displacement ")]
    assert len(settings) == 4 and all(x["status"] == manual.MATCH for x in settings)
