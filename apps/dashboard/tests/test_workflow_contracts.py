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


def test_deploy_workflow_can_publish_optional_contextual_history() -> None:
    deploy = _read("deploy-dashboard.yml")

    assert "contextual_history:" in deploy
    assert "strategy_outcomes:" in deploy
    assert "args+=(--history" in deploy
    assert "args+=(--strategy-outcomes" in deploy


def test_rbreaker_artifact_workflow_produces_validated_alpaca_artifact() -> None:
    workflow = _read("rbreaker-artifact-and-deploy.yml")

    assert "workflow_dispatch" in workflow
    assert "symbol:" in workflow
    assert "session_date:" in workflow
    assert "feed:" in workflow
    assert "default: sip" in workflow
    assert "APCA_API_KEY_ID" in workflow
    assert "APCA_API_SECRET_KEY" in workflow
    assert "trading_research.scripts.build_rbreaker_alpaca_artifact" in workflow
    assert "generate_ict_liquidity_reclaim_snapshot" in workflow
    assert "ict-liquidity-reclaim-research.json" in workflow
    assert "rbreaker-input-v1" in workflow
    assert "enrich_contextual_research" in workflow
    assert "validate_static_assets.py --require-contextual" in workflow
    assert "wrangler@4 deploy" in workflow
    assert workflow.index("enrich_contextual_research") < workflow.index(
        "validate_static_assets.py --require-contextual"
    )
    assert 'echo "$APCA_API_KEY_ID"' not in workflow
    assert 'echo "$APCA_API_SECRET_KEY"' not in workflow
