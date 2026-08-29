import subprocess
import sys

import numpy as np

from trading_research.strategies.rbreaker import annualized_sharpe_from_returns


def test_rbreaker_imports():
    import importlib

    mod = importlib.import_module('trading_research.strategies.rbreaker')
    assert hasattr(mod, 'RBreakerStrategy')
    assert hasattr(mod, 'main')


def test_rbreaker_help():
    result = subprocess.run(
        [sys.executable, '-m', 'trading_research.strategies.rbreaker', '--help'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    assert result.returncode == 0
    assert 'R-Breaker' in result.stdout
    assert '--data-source' in result.stdout
    assert '--symbol' in result.stdout


def test_rbreaker_sharpe_fallback_is_finite_for_time_returns():
    result = annualized_sharpe_from_returns(np.array([0.01, -0.005, 0.02]))
    assert np.isfinite(result)
    assert result > 0
