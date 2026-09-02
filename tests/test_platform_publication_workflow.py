from __future__ import annotations

from pathlib import Path


WORKFLOW = Path(".github/workflows/publish-platform-publication.yml")


def test_platform_publication_workflow_is_scoped_and_durable() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "actions/download-artifact@v4" in text
    assert "RESEARCH_ARTIFACT_TOKEN" in text
    assert "trading_research.platform_publication" in text
    assert "apps/dashboard/web/public/platform-publication.json" in text
    assert "apps/dashboard/web/public/platform" in text
    assert "gh pr create" in text
    assert "pull-requests: write" in text
    assert "contents: write" in text
    assert "dashboard-publish" not in text
