from scripts import run_industry_context_oos


def test_resolve_research_commit_prefers_explicit_value() -> None:
    commit = "a" * 40

    assert run_industry_context_oos._resolve_research_commit(commit) == commit


def test_resolve_research_commit_rejects_empty_explicit_value() -> None:
    assert run_industry_context_oos._resolve_research_commit("   ") is None
