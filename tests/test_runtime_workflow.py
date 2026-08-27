from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_publish_snapshot_requires_dedicated_cross_repo_artifact_token() -> None:
    text = (_root() / ".github/workflows/publish-research-snapshot.yml").read_text(encoding="utf-8")

    assert "RESEARCH_ARTIFACT_TOKEN" in text
    assert "inputs.artifact_repository != github.repository" in text
    assert "Cross-repository artifact access requires RESEARCH_ARTIFACT_TOKEN" in text
    assert "inputs.artifact_repository == github.repository && github.token || secrets.RESEARCH_ARTIFACT_TOKEN" in text


def test_dashboard_report_schedule_is_shadow_only_until_cutover() -> None:
    text = (_root() / ".github/workflows/dashboard-report.yml").read_text(encoding="utf-8")

    assert 'cron: "10 1 * * 1-5"' in text
    assert "SCHEDULE_MODE: shadow" in text
    assert "options:" in text
    assert "- shadow" in text
    assert "- authoritative" in text
    assert "check_runtime_candidate.py" in text
    assert "dashboard-runtime-candidate-${{ github.run_id }}" in text
    assert "if: ${{ steps.mode.outputs.mode == 'authoritative' }}" in text
    assert "npx --yes wrangler@4 deploy --config apps/dashboard/wrangler.jsonc" in text


def test_shadow_path_has_no_repository_write_permission() -> None:
    text = (_root() / ".github/workflows/dashboard-report.yml").read_text(encoding="utf-8")

    assert "permissions:\n  contents: read" in text
    assert "git push" not in text
    assert "git add data/raw" not in text
