"""IST validation agent.

Reference models (the oracle) of the IST specification, plus the deterministic,
property-based, stateful, regression, golden and parity checks that run against
them. The Pine script stays the production implementation; nothing here runs
Pine or TradingView.
"""
from pathlib import Path

__version__ = "1.9.3"

VALIDATION_DIR = Path(__file__).resolve().parent
ROOT = VALIDATION_DIR.parent
PINE_SOURCE = ROOT / "src" / "IST.pine"
