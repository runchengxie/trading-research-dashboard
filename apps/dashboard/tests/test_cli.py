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


def test_import_has_no_stdout_or_socket_timeout_side_effect() -> None:
    script = """
import socket
socket.setdefaulttimeout(7.5)
before = socket.getdefaulttimeout()
import trading_research.dashboard.astock_tech
after = socket.getdefaulttimeout()
print(f"{before}|{after}")
"""
    result = subprocess.run(
        [sys.executable, '-c', script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == '7.5|7.5'
