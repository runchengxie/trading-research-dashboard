from pathlib import Path

WORKFLOW_ROOT = Path(__file__).parents[3] / ".github" / "workflows"


def _read(name: str) -> str:
    return (WORKFLOW_ROOT / name).read_text(encoding="utf-8")


def test_dashboard_workflows_enrich_before_validation_without_automatic_deploy_triggers() -> None:
    report = _read("dashboard-report.yml")
    deploy = _read("deploy-dashboard.yml")

    for workflow in (report, deploy):
        assert "enrich_contextual_research" in workflow
        assert "validate_static_assets.py" in workflow
        assert workflow.index("enrich_contextual_research") < workflow.index(
            "validate_static_assets.py"
        )
        assert "\npush:" not in workflow
        assert "\npull_request:" not in workflow


def test_authoritative_workflow_has_strict_contextual_validation() -> None:
    report = _read("dashboard-report.yml")
    assert "--require-contextual" in report
