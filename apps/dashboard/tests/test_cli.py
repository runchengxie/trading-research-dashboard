import subprocess
import sys
import pathlib


def test_main_executes_help():
    script = str(pathlib.Path('astock_tech.py').resolve())
    result = subprocess.run(
        [sys.executable, script, '--help'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    assert result.returncode == 0
    assert 'usage' in result.stdout
    assert '--codes' in result.stdout
    assert '--output-root' in result.stdout
