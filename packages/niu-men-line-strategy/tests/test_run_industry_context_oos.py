import importlib.util
from pathlib import Path


def _load_runner():
    path = Path(__file__).resolve().parents[1] / "scripts" / "run_industry_context_oos.py"
    spec = importlib.util.spec_from_file_location("run_industry_context_oos", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_industry_context_oos = _load_runner()


def test_resolve_research_commit_prefers_explicit_value() -> None:
    commit = "a" * 40

    assert run_industry_context_oos._resolve_research_commit(commit) == commit


def test_resolve_research_commit_rejects_empty_explicit_value() -> None:
    assert run_industry_context_oos._resolve_research_commit("   ") is None
