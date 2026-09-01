from __future__ import annotations

from pathlib import Path

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "agent-paper-portfolio.yml"


def test_agent_workflow_is_manual_and_weekday_scheduled() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert 'cron: "30 22 * * 1-5"' in text


def test_agent_workflow_uses_secret_and_read_only_permissions() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "ZHIPU_API_KEY" in text
    assert "OPENROUTER_API_KEY" in text
    assert "OPENROUTER_MODEL" in text
    assert "OPENROUTER_BASE_URL" in text
    assert "TUSHARE_TOKEN_2" in text
    assert "TUSHARE_API_URL_2" in text
    assert "contents: read" in text
    assert "agent-portfolio" in text


def test_agent_workflow_handles_dispatch_input_without_shell_interpolation() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "AS_OF_OVERRIDE: ${{ inputs.as_of }}" in text
    assert 'if [ -n "${{ inputs.as_of }}" ]' not in text
    assert "--max-time 20" in text


def test_agent_workflow_does_not_reset_state_after_configured_fetch_failure() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'if [ -n "$CLOUDFLARE_PUBLIC_URL" ]; then' in text
    assert "Unable to load the previous deployed Agent portfolio state" in text


def test_agent_workflow_does_not_contain_broker_credentials_or_order_calls() -> None:
    text = WORKFLOW.read_text(encoding="utf-8").lower()
    assert "broker_api_key" not in text
    assert "submit_order" not in text
