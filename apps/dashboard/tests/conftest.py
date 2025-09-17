import os
import random
import pytest
@pytest.fixture(autouse=True)
def _fixed_env(monkeypatch):
    monkeypatch.setenv('TZ', 'UTC')
@pytest.fixture(autouse=True)
def _fixed_seed():
    random.seed(1337)
