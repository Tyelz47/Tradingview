"""Static checks on src/IST.pine (text only: nothing here compiles or runs Pine)."""
import pytest

from validation import stats
from validation.static_checks import CHECKS

pytestmark = [pytest.mark.common, pytest.mark.section("static")]


@pytest.mark.parametrize("cid, name, fn", CHECKS, ids=[c[0] for c in CHECKS])
def test_static(cid, name, fn):
    ok, detail = fn()
    stats.RESULTS.setdefault("static", {})[cid] = {"name": name, "ok": ok, "detail": detail}
    if ok is None:
        pytest.skip(detail)
    assert ok, f"{cid} {name}: {detail}"
