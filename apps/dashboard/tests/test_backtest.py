import subprocess
import sys
import pathlib


def test_rbreaker_imports():
    import importlib

    sys.path.insert(0, str(pathlib.Path('backtest').resolve()))
    mod = importlib.import_module('rbreaker')
    assert hasattr(mod, 'RBreakerStrategy')
    assert hasattr(mod, 'main')


def test_rbreaker_help():
    script = str(pathlib.Path('backtest/rbreaker.py').resolve())
    result = subprocess.run(
        [sys.executable, script, '--help'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    assert result.returncode == 0
    assert 'R-Breaker' in result.stdout
    assert '--data-source' in result.stdout
    assert '--symbol' in result.stdout
