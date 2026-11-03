"""The IFVG evidence (IFVG-L10): the real TradingView capture of IST v0.9.1-dev (MNQ1! 1m, live chart,
1,000 bars + 76 warm-up, 2026-11-02 04:16 → 23:11 New York; validation/parity/evidence, kept byte for
byte). Every module compared, 0 DIFFERENCE; IFVG per bar (shadows, active per side, CE / full facts),
per event, every snapshot record, the shadows = the open Phase 1 FVGs. Its bearish side holds more than
50 ACTIVE IFVGs for 655 bars (peak 66): DEF-IFVG8's temporary overflow, in real Pine."""
import pytest

from validation.parity import CAPTURE_V091, capture, manual

pytestmark = [pytest.mark.ifvg, pytest.mark.section("parity")]


@pytest.fixture(scope="module")
def cap():
    return capture.parse(CAPTURE_V091.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def r(cap):
    return capture.compare(cap)


def test_v091_capture_is_exact_everywhere(r):
    assert r["differences"] == 0, [c["text"] for c in r["checks"] if c["status"] == manual.DIFF][:5]
    assert r["capture_build"] == "v0.9.1-dev"
    assert (r["compared_bars"], r["series"], r["matched_events"]) == (1043, 9, 940)
    assert (r["counts"][manual.MATCH], r["counts"][manual.NOBS]) == (82, 16)
    assert (r["lrl"]["events"], r["lrl"]["boundaries"], r["lrl"]["cand_bars"]) == (41, 302, 2000)
    assert (r["htf"]["candles"], r["htf"]["events"], r["htf"]["open_bars"]) == (126, 92, 1075)
    assert (r["cisd"]["bars"], r["cisd"]["events"], r["cisd"]["cold"]) == (1075, 174, 87)
    assert (r["disp"]["bars"], r["disp"]["events"]) == (1060, 46)


def test_v091_ifvg_is_exact(r):
    d = r["ifvg"]
    assert (d["bars"], d["events"], d["records"]) == (1059, 654, 100)
    text = [x["text"] for x in r["checks"] if x["section"] == "ifvg"]
    for typ, n in (("IFVG_INVERTED", 167), ("IFVG_FIRST_TOUCH", 168), ("IFVG_INVALIDATED", 168), ("IFVG_DROPPED_MEMORY", 151)):
        assert any(t.startswith(f"{typ}: {n} ") for t in text), typ
    assert any("shadows = the open Phase 1 FVGs" in t for t in text)
    assert any("per bar: shadows, active IFVGs per side, CE / full facts: 1059 bars" in t for t in text)


def drop_kinds(cap) -> list[str]:
    """Why each IFVG_DROPPED_MEMORY of a capture is allowed: its record was INVALIDATED earlier in the
    log ("log") or in the snapshot ("snapshot"); a drop up to the snapshot of a record not in it ended
    before the window ("before the snapshot", NOT OBSERVABLE); anything else is "ACTIVE"."""
    ended, logged = {}, []
    for e in cap["events"]:
        if e["type"] == "IFVG_INVALIDATED":
            ended.setdefault((e["dir"], e["sid"]), e["time"])
        elif e["type"] == "IFVG_DROPPED_MEMORY":
            logged.append(e)
    snap = {(x["side"], x["id"]): x for x in cap["ifvg"]["IFVGREC"]}
    t_snap = next(b["time"] for b in cap["bars"] if b["i"] == cap["ifvg"]["IFVGSTATE"][0]["at"])
    return [("log" if ended.get((e["dir"], e["sid"]), e["time"] + 1) <= e["time"] else
             "snapshot" if snap.get((e["dir"], e["sid"]), {}).get("end") is not None else
             "before the snapshot" if e["time"] <= t_snap else "ACTIVE") for e in logged]


def test_v091_memory_never_dropped_an_active_ifvg(cap):
    """Every IFVG_DROPPED_MEMORY in the real log was INVALIDATED before its drop: earlier in the log
    (121) or already in the snapshot (31); one drop happened before the snapshot, its record's end is
    before the window (NOT OBSERVABLE). The bearish side holds 51…66 ACTIVE IFVGs from 05:06 on, all kept."""
    kinds = drop_kinds(cap)
    assert [kinds.count(k) for k in ("log", "snapshot", "before the snapshot", "ACTIVE")] == [121, 31, 1, 0]
    over = [(b["time"], b["ifvg"]["ia"]) for b in cap["bars"] if b["ifvg"] and b["ifvg"]["ia"][1] > 50]
    assert len(over) == 655 and max(a[1] for _, a in over) == 66
