"""Pure result metrics used by the R-Breaker backtest."""

from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np


def annualized_sharpe_from_returns(values: Iterable[float]) -> float:
    """Return a finite annualized daily Sharpe value for a return series."""
    returns = np.asarray(list(values), dtype=float)
    returns = returns[np.isfinite(returns)]
    if len(returns) < 2:
        return 0.0
    volatility = float(returns.std(ddof=1))
    if volatility == 0.0:
        return 0.0
    return float(returns.mean() / volatility * math.sqrt(252))
