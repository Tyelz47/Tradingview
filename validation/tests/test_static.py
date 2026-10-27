"""Static checks on src/IST.pine (text only: nothing here compiles or runs Pine)."""
import pytest

from validation import stats
from validation.static_checks import CHECKS

pytestmark = [pytest.mark.common, pytest.mark.section("static")]


SPEC = {"ST-01": ("L05", "L06", "S-01"), "ST-06": ("L05", "L06", "S-08"), "ST-13": ("L32",), "ST-15": ("L27", "S-06")}


@pytest.mark.parametrize("cid, name, fn", [pytest.param(*c, marks=pytest.mark.spec(*SPEC.get(c[0], ()))) for c in CHECKS],
                         ids=[c[0] for c in CHECKS])
def test_static(cid, name, fn):
    ok, detail = fn()
    stats.RESULTS.setdefault("static", {})[cid] = {"name": name, "ok": ok, "detail": detail}
    if ok is None:
        pytest.skip(detail)
    assert ok, f"{cid} {name}: {detail}"
