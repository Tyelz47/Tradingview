"""The first real TradingView capture of IST v0.7.0-dev (MNQ 1m, 1,000 bars + 76 warm-up,
2026-10-29 21:48 → 2026-10-30 15:43 New York; validation/parity/evidence, kept byte for byte) and
the defect it revealed, fixed in v0.7.1-dev (ST-21).

Pine keeps a separate history PER CALL of a function. A history read of a user series inside
a function or method that does not run on every bar returns the value of an earlier CALL, not
of the earlier BAR:
* CISD (confirmCisd, 2 call sites, one per side): `cisdTra[1]` = the TR average at the previous
  confirmation of the SAME SIDE. Only the body / TR metadata `bk` was wrong, never a CISD.
* LRL (seed, fits): `lrlTra[bar_index - xa]` = a TR average from an earlier call: τ and the
  separation check used wrong TR averages, so LRLs, their boundaries and their ends diverged.
Phase 1, Phase 2 and HTF FVG read no user series inside a conditionally run function: 0
differences. This file pins that diagnosis on the evidence; the corrected Pine needs a NEW capture."""
import pytest

from validation.models import lrl as L
from validation.models.fvg import true_range
from validation.parity import CAPTURE_V070, capture, manual
from validation.parity.capture import _kv

pytestmark = [pytest.mark.cisd, pytest.mark.lrl, pytest.mark.section("parity")]


@pytest.fixture(scope="module")
def cap():
    return capture.parse(CAPTURE_V070.read_text(encoding="utf-8"))


def _diffs(r, sec):
    return [c["text"] for c in r["checks"] if c["section"] == sec and c["status"] == manual.DIFF]


def test_other_modules_are_exact_and_the_build_is_flagged(cap):
    r = capture.compare(cap)
    for sec in ("settings", "bars", "events", "htf"):
        assert not _diffs(r, sec), sec
    assert r["capture_build"] is None and r["current_build"] != "v0.7.0-dev"
    assert any("Take a new capture" in n for n in r["notes"])


def test_cisd_differences_are_only_body_tr_and_are_the_call_history_value(cap):
    """Every CISD agrees on side, id, time, L, previous state, close, extreme and its time; only bk
    differs. Pine's bk = body / the TR average AT THE PREVIOUS SAME-SIDE CONFIRMATION BAR (the
    previous call of that call site), for every case where that bar is in the window."""
    r = capture.compare(cap)
    d = _diffs(r, "cisd")
    assert d and all(x.rsplit(": ", 1)[1].startswith("bk Pine") and x.count("Pine") == 1 for x in d)
    bars = cap["bars"]
    cs = [b["candle"] for b in bars]
    tr = [true_range(c, cs[i - 1] if i else None) for i, c in enumerate(cs)]
    sma = lambda end: sum(tr[end - 13:end + 1]) / 14
    at = {b["time"]: i for i, b in enumerate(bars)}
    prev, emulated, intended = {}, [], 0
    for e in (e for e in cap["events"] if e["type"] == "CISD_CONFIRMED"):
        t, g, bk = at[e["time"]], e["dir"], float(_kv(e["text"])["bk"])
        body = g * (cs[t].close - cs[t].open)
        if prev.get(g, 0) >= 14:
            emulated.append(abs(body / sma(prev[g]) - bk) < 1e-6)
        intended += t > 14 and abs(body / sma(t - 1) - bk) < 1e-6
        prev[g] = t
    assert len(emulated) == 80 and all(emulated) and intended <= 1


def test_lrl_tau_is_not_the_anchor_tr_average_and_explains_most_differences(cap):
    """Pine's τ of every confirmed LRL (bar 14 onward) is not 0.5 × the TR average at its anchor;
    with Pine's logged τ injected into the oracle, the LRL differences fall from 330 to 70, and the
    rest sit where the same wrong read decided the separation check (an extension, a candidate)."""
    r = capture.compare(cap)
    assert len(_diffs(r, "lrl")) == 330
    first = min(_diffs(r, "lrl"), key=lambda x: x.split(": ", 1)[1][:16] if x.startswith("line") else x[:16])
    assert "LRL_CONFIRMED LOW id=2026-10-29 23:33" in first and "tau Pine 5.88392857 · oracle 7.22321429" in first
    bars = cap["bars"]
    at = {b["time"]: i for i, b in enumerate(bars)}
    cs = [b["candle"] for b in bars]
    tr = [true_range(c, cs[i - 1] if i else None) for i, c in enumerate(cs)]
    pine_tau, off = {}, 0
    for e in cap["events"]:
        if e["type"] in ("LRL_CONFIRMED", "LRL_EXTENDED"):
            kv = _kv(e["text"])
            x = int(kv["pts"].split(",")[0])
            pine_tau[x] = float(kv["tau"])
    for x, tau in pine_tau.items():
        if x in at and at[x] >= 14:
            off += abs(tau - max(1.0, 0.5 * sum(tr[at[x] - 13:at[x] + 1]) / 14)) > 1e-6
    assert off >= 14
    orig = L.LrlEngine.tau
    try:
        L.LrlEngine.tau = lambda self, x: pine_tau.get(self.candles[x].time, orig(self, x))
        assert len(_diffs(capture.compare(cap), "lrl")) == 70
    finally:
        L.LrlEngine.tau = orig
