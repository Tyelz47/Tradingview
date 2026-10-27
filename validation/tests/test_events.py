"""Canonical event stream: ordering, identity, serialisation, Pine text parsing."""
import json
import random

import pytest

from validation.candles import random_walk
from validation.models.events import Event, canonical, parse_local, parse_pine_line
from validation.models.ist import run_model
from validation.models.types import Settings

pytestmark = [pytest.mark.common, pytest.mark.section("events")]
NY = "America/New_York"


def test_canonical_order_is_deterministic():
    m = run_model(random_walk(1500, 5), Settings())
    evs = list(m.events)
    shuffled = evs[:]
    random.Random(1).shuffle(shuffled)
    assert canonical(shuffled) == canonical(evs)
    keys = [e.key() for e in canonical(evs)]
    assert keys == sorted(keys) and len(set(keys)) == len(keys), "canonical keys are unique"


def test_json_round_trip():
    m = run_model(random_walk(500, 2), Settings())
    data = json.loads(json.dumps([e.to_dict() for e in m.events]))
    assert [Event.from_dict(d) for d in data] == m.events


def test_transition_identity_unique():
    m = run_model(random_walk(3000, 9), Settings())
    once = [e.ident() for e in m.events if e.type != "LEVEL_SET"]
    assert len(once) == len(set(once))


def test_events_never_move_backward_in_time():
    m = run_model(random_walk(2000, 4), Settings())
    times = [e.time for e in m.events]
    assert times == sorted(times)


@pytest.mark.spec("parity")
@pytest.mark.parametrize("line, expect", [
    ("10-27 09:41  FVG_CREATED BULL id=2026-10-27 09:41 px=21001.50 · 21000.25–21002.75",
     {"type": "FVG_CREATED", "dir": 1, "price": 21001.5, "time": "2026-10-27 09:41", "sid": "2026-10-27 09:41"}),
    ("10-27 10:02  BSL_SWEEP id=2026-10-27 09:55 px=21010.00 · close 21008.25",
     {"type": "BSL_SWEEP", "dir": 1, "price": 21010.0, "time": "2026-10-27 10:02", "sid": "2026-10-27 09:55"}),
    ("10-27 10:05  EQL_TAKEN id=2026-10-27 09:58 px=20990.75 · 2 swings · sweep",
     {"type": "EQL_TAKEN", "dir": -1, "price": 20990.75, "time": "2026-10-27 10:05", "sid": "2026-10-27 09:58"}),
    ("10-26 18:00  LEVEL_SET HIGH px=21100.00 · PDH", {"type": "LEVEL_SET", "dir": 1, "price": 21100.0, "sid": 0}),
    ("10-27 09:30  SESSION_START id=2026-10-27 09:30 px=— · NY AM", {"type": "SESSION_START", "dir": 0, "price": None}),
    ("NQ1! 1 · FVG_INVALIDATED BEAR id=2026-10-27 09:41 px=21005.25 · close>top", {"type": "FVG_INVALIDATED", "dir": -1, "time": None}),
])
def test_parse_pine_event_lines(line, expect):
    got = parse_pine_line(line, NY, 2026)
    for k, v in expect.items():
        if k in ("time", "sid") and isinstance(v, str):
            v = parse_local(v, NY)
        assert got[k] == v, (k, got)
