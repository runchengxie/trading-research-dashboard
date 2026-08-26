from pathlib import Path

WORKFLOW = Path(".github/workflows/deploy-dashboard.yml").read_text(encoding="utf-8")


def test_deploy_workflow_declares_rbreaker_inputs_and_backtest_install() -> None:
    assert "research_run_id:" in WORKFLOW
    assert "enable_rbreaker:" in WORKFLOW
    assert "RESEARCH_ARTIFACT_TOKEN" in WORKFLOW
    assert "--extra backtest" in WORKFLOW


def test_deploy_workflow_validates_and_generates_before_frontend_build() -> None:
    validation = WORKFLOW.index("load_artifact")
    generation = WORKFLOW.index("rbreaker-snapshot")
    static_validation = WORKFLOW.index("Validate Dashboard data snapshots")
    build = WORKFLOW.index("Build Dashboard")
    deploy = WORKFLOW.index("Deploy to Cloudflare")
    assert validation < generation < static_validation < build < deploy


def test_deploy_workflow_uses_temporary_artifact_and_read_only_secret() -> None:
    assert "${{ runner.temp }}/rbreaker-input" in WORKFLOW
    assert "actions/download-artifact@v4" in WORKFLOW
    assert "DASHBOARD_REPOSITORY_TOKEN" not in WORKFLOW


def test_deploy_workflow_has_explicit_skip_path() -> None:
    assert "enable_rbreaker == false" in WORKFLOW
    assert "skipped" in WORKFLOW
