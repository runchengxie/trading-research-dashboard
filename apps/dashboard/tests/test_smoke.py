def test_imports():
    import importlib
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path('.').resolve()))
    importlib.import_module('astock_tech')
