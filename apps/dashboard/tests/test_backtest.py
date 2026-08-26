import subprocess
import sys


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
