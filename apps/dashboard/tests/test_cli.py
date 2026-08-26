import subprocess
import sys


def test_main_executes_help():
    result = subprocess.run(
        [sys.executable, '-m', 'trading_research.dashboard.astock_tech', '--help'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    assert result.returncode == 0
    assert 'usage' in result.stdout
    assert '--codes' in result.stdout
    assert '--output-root' in result.stdout
