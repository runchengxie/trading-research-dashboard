"""Compatibility entry point for the packaged R-Breaker strategy."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_research.strategies import rbreaker as _implementation  # noqa: E402, I001


if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
