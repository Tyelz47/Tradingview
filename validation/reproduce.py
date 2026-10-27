"""Re-run a saved failure: python -m validation.reproduce validation/reports/failures/<case>/failure.json"""
import json
import sys

from validation.invariants import InvariantViolation, run_checked
from validation.models.types import Candle, Settings


def main(path: str) -> int:
    data = json.loads(open(path, encoding="utf-8").read())
    candles = [Candle(*r) for r in data["candles"]]
    settings = Settings.from_dict(data["settings"])
    print(f"{data['test']}: {len(candles)} candles, recorded failure: {data['message']}")
    try:
        m = run_checked(candles, settings)
    except InvariantViolation as v:
        print(f"REPRODUCED {v}")
        return 1
    print(f"not reproduced by the invariant monitor ({len(m.events)} events). If the failure was a metamorphic "
          f"property, compare `expected`/`actual` in the file.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
