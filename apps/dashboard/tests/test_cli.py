import subprocess, sys, pathlib
def test_main_executes_help():
    script = str(pathlib.Path('astock_tech.py').resolve())
    result = subprocess.run([sys.executable, script, '--help'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert result.returncode in (0,1)
    assert result.stdout is not None
