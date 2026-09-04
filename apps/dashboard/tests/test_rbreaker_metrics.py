import numpy as np
import pytest

from trading_research.strategies.rbreaker_metrics import annualized_sharpe_from_returns


def test_annualized_sharpe_ignores_non_finite_returns() -> None:
    result = annualized_sharpe_from_returns(np.array([0.01, np.nan, -0.005, 0.02]))

    expected = np.mean([0.01, -0.005, 0.02]) / np.std([0.01, -0.005, 0.02], ddof=1)
    assert result == pytest.approx(expected * np.sqrt(252))
