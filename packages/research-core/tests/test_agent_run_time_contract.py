from research_core.experiments import AGENT_RUN_VERSION, validate_agent_run


def test_completed_agent_run_allows_unknown_started_at():
    payload = {
        "schemaVersion": AGENT_RUN_VERSION,
        "runId": "ai-stock-picker-2026-09-03",
        "status": "completed",
        "completedAt": "2026-09-03T08:00:12Z",
        "model": {"provider": "deepseek", "name": "deepseek-v4-flash"},
        "harness": {"name": "ai-stock-picker", "version": "1.0.0"},
        "budget": {},
        "usage": {},
        "tasks": [],
        "artifactRefs": ["artifact://selection.json"],
        "evidenceRefs": [],
        "limitations": ["started_at_not_recorded_by_owner"],
        "provenance": {"source": "ai-stock-picker"},
    }

    validate_agent_run(payload)
