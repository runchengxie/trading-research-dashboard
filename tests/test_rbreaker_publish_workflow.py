from pathlib import Path


def _workflow_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "publish-rbreaker-snapshot.yml"
    )


def test_rbreaker_publication_workflow_is_manual_only() -> None:
    text = _workflow_path().read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "push:" not in text
    assert "pull_request:" not in text
    assert "artifact_repository:" in text
    assert "artifact_run_id:" in text
    assert "artifact_name:" in text


def test_rbreaker_publication_workflow_has_cross_repo_auth_gate() -> None:
    text = _workflow_path().read_text(encoding="utf-8")

    assert "RESEARCH_ARTIFACT_TOKEN" in text
    assert "inputs.artifact_repository != github.repository" in text
    assert "Cross-repository artifact access requires RESEARCH_ARTIFACT_TOKEN" in text
    assert (
        "inputs.artifact_repository == github.repository && github.token || "
        "secrets.RESEARCH_ARTIFACT_TOKEN"
    ) in text


def test_rbreaker_publication_workflow_generates_then_publishes_snapshot() -> None:
    text = _workflow_path().read_text(encoding="utf-8")

    assert "trading_research.scripts.generate_rbreaker_snapshot" in text
    assert "--artifact-root incoming-rbreaker" in text
    assert "--producer-run-id \"${{ inputs.artifact_run_id }}\"" in text
    assert "scripts/publish_research_snapshot.py" in text
    assert "--strategy-id r-breaker" in text
    assert "--open-pr" in text

    assert "git add incoming-rbreaker" not in text
    assert "git add generated-snapshot" not in text
    assert "data/raw" not in text
