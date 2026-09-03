import pytest

from research_core.experiments import (
    AGENT_RUN_VERSION,
    EVAL_RESULT_VERSION,
    RESEARCH_EVIDENCE_VERSION,
    RESEARCH_EXPERIMENT_VERSION,
    validate_agent_run,
    validate_eval_result,
    validate_research_evidence,
    validate_research_experiment,
)


def research_experiment():
    return {
        "schemaVersion": RESEARCH_EXPERIMENT_VERSION,
        "experimentId": "cn-stock-rerank-2026-09",
        "objective": "Compare a numeric ranking baseline with an LLM reranker.",
        "taskType": "stock_selection",
        "market": "CN",
        "createdAt": "2026-09-03T08:00:00Z",
        "caseSet": {"id": "cn-daily-selection", "version": "2026-09-03"},
        "baselineVariantId": "numeric",
        "variants": [
            {
                "variantId": "numeric",
                "label": "Numeric baseline",
                "kind": "numeric_baseline",
            },
            {
                "variantId": "llm",
                "label": "LLM reranker",
                "kind": "model",
                "model": "deepseek-v4-flash",
                "promptVersion": "2026-07-29.1",
            },
        ],
        "scorecard": [
            {
                "metricId": "top1_return",
                "label": "Top-1 return",
                "direction": "maximize",
                "unit": "pct",
                "required": True,
            }
        ],
        "constraints": ["no_future_data"],
        "provenance": {"source": "research-core-test"},
    }


def test_research_experiment_version_is_stable():
    assert RESEARCH_EXPERIMENT_VERSION == "trading_research.research_experiment.v1"


def test_valid_research_experiment_is_accepted():
    validate_research_experiment(research_experiment())


def test_research_contract_rejects_non_object_root():
    with pytest.raises(TypeError, match="root must be an object"):
        validate_research_experiment([])


def test_research_contract_rejects_provenance_without_source():
    payload = research_experiment()
    payload["provenance"] = {"adapterVersion": "v1"}
    with pytest.raises(ValueError, match="source"):
        validate_research_experiment(payload)


def test_research_experiment_rejects_missing_baseline_variant():
    payload = research_experiment()
    payload["baselineVariantId"] = "missing"
    with pytest.raises(ValueError, match="baselineVariantId"):
        validate_research_experiment(payload)


def test_research_experiment_rejects_duplicate_variant_ids():
    payload = research_experiment()
    payload["variants"].append(dict(payload["variants"][0]))
    with pytest.raises(ValueError, match="duplicate variantId"):
        validate_research_experiment(payload)


def test_research_experiment_rejects_duplicate_metric_ids():
    payload = research_experiment()
    payload["scorecard"].append(dict(payload["scorecard"][0]))
    with pytest.raises(ValueError, match="duplicate metricId"):
        validate_research_experiment(payload)


def agent_run():
    return {
        "schemaVersion": AGENT_RUN_VERSION,
        "runId": "run-001",
        "experimentId": "cn-stock-rerank-2026-09",
        "caseId": "2026-09-03",
        "variantId": "llm",
        "status": "completed",
        "startedAt": "2026-09-03T08:00:00Z",
        "completedAt": "2026-09-03T08:00:12Z",
        "model": {"provider": "deepseek", "name": "deepseek-v4-flash"},
        "harness": {"name": "ai-stock-picker", "version": "0.8"},
        "budget": {"tokenLimit": 8192, "timeLimitMs": 60000},
        "usage": {"inputTokens": 1200, "outputTokens": 300, "wallTimeMs": 12000},
        "tasks": [
            {
                "taskId": "rerank",
                "agentId": "selector",
                "role": "candidate_reranker",
                "status": "completed",
                "dependsOn": [],
                "startedAt": "2026-09-03T08:00:00Z",
                "completedAt": "2026-09-03T08:00:12Z",
                "iterations": 1,
                "summary": "Reranked the frozen candidate set.",
                "artifactRefs": ["artifact://selection.json"],
                "evidenceRefs": ["evidence-001"],
            }
        ],
        "artifactRefs": ["artifact://selection.json"],
        "evidenceRefs": ["evidence-001"],
        "limitations": ["strict_point_in_time_not_established"],
        "provenance": {"source": "research-core-test"},
    }


def research_evidence():
    return {
        "schemaVersion": RESEARCH_EVIDENCE_VERSION,
        "evidenceId": "evidence-001",
        "runId": "run-001",
        "evidenceType": "candidate_snapshot",
        "source": {
            "provider": "internal",
            "sourceType": "artifact",
            "sourceUri": "artifact://candidates.json",
            "symbolUniverse": ["000001.SZ", "600000.SH"],
            "benchmark": [],
            "timeframe": "daily",
            "method": "frozen_candidate_pool",
        },
        "retrievedAt": "2026-09-03T07:59:00Z",
        "dataAsOf": "2026-09-02",
        "freshnessStatus": "fresh",
        "verificationStatus": "verified",
        "artifactRef": "artifact://candidates.json",
        "contentSha256": "a" * 64,
        "pointInTime": {
            "assurance": "signal_date_only",
            "strict": False,
            "eligibleAsOosEvidence": False,
        },
        "limitations": ["external_timestamp_unavailable"],
        "provenance": {"source": "research-core-test"},
    }


def test_agent_run_and_evidence_versions_are_stable():
    assert AGENT_RUN_VERSION == "trading_research.agent_run.v1"
    assert RESEARCH_EVIDENCE_VERSION == "trading_research.research_evidence.v1"


def test_valid_agent_run_and_evidence_are_accepted():
    validate_agent_run(agent_run())
    validate_research_evidence(research_evidence())


def test_completed_agent_run_requires_completed_at():
    payload = agent_run()
    del payload["completedAt"]
    with pytest.raises(ValueError, match="completedAt"):
        validate_agent_run(payload)


def test_incomplete_agent_run_is_a_valid_terminal_state():
    payload = agent_run()
    payload["status"] = "incomplete"
    validate_agent_run(payload)


def test_agent_run_rejects_duplicate_task_ids():
    payload = agent_run()
    payload["tasks"].append(dict(payload["tasks"][0]))
    with pytest.raises(ValueError, match="duplicate taskId"):
        validate_agent_run(payload)


def test_agent_run_rejects_unexpected_task_fields():
    payload = agent_run()
    payload["tasks"][0]["rawChainOfThought"] = "should never be canonical"
    with pytest.raises(ValueError, match="rawChainOfThought"):
        validate_agent_run(payload)


def test_agent_run_accepts_undeclared_budget_and_usage():
    payload = agent_run()
    payload["budget"] = {}
    payload["usage"] = {}
    validate_agent_run(payload)


def test_agent_run_rejects_unknown_task_dependency():
    payload = agent_run()
    payload["tasks"][0]["dependsOn"] = ["missing-task"]
    with pytest.raises(ValueError, match="unknown dependency"):
        validate_agent_run(payload)


def test_agent_run_rejects_task_dependency_cycle():
    payload = agent_run()
    second = dict(payload["tasks"][0])
    second["taskId"] = "risk-review"
    second["dependsOn"] = ["rerank"]
    payload["tasks"][0]["dependsOn"] = ["risk-review"]
    payload["tasks"].append(second)
    with pytest.raises(ValueError, match="dependency cycle"):
        validate_agent_run(payload)


def test_completed_agent_run_rejects_noncompleted_task():
    payload = agent_run()
    payload["tasks"][0]["status"] = "incomplete"
    with pytest.raises(ValueError, match="completed run"):
        validate_agent_run(payload)


def test_strict_pit_can_remain_ineligible_as_oos_evidence():
    payload = research_evidence()
    payload["pointInTime"] = {
        "assurance": "strict_replay",
        "strict": True,
        "eligibleAsOosEvidence": False,
    }
    validate_research_evidence(payload)


def test_evidence_rejects_strict_pit_without_strict_replay_assurance():
    payload = research_evidence()
    payload["pointInTime"] = {
        "assurance": "externally_timestamped",
        "strict": True,
        "eligibleAsOosEvidence": False,
    }
    with pytest.raises(ValueError, match="strict point-in-time"):
        validate_research_evidence(payload)


def test_evidence_rejects_oos_eligibility_for_signal_date_only():
    payload = research_evidence()
    payload["pointInTime"]["eligibleAsOosEvidence"] = True
    with pytest.raises(ValueError, match="OOS evidence"):
        validate_research_evidence(payload)


def test_evidence_rejects_unexpected_fields():
    payload = research_evidence()
    payload["futurePrice"] = 123.45
    with pytest.raises(ValueError, match="futurePrice"):
        validate_research_evidence(payload)


def eval_result():
    return {
        "schemaVersion": EVAL_RESULT_VERSION,
        "evalId": "eval-001",
        "experimentId": "cn-stock-rerank-2026-09",
        "caseId": "2026-09-03",
        "runId": "run-001",
        "variantId": "llm",
        "evaluatedAt": "2026-09-10T08:00:00Z",
        "status": "completed",
        "metrics": [
            {
                "metricId": "top1_return",
                "value": 0.012,
                "unit": "pct",
                "status": "pass",
                "threshold": 0.0,
                "notes": "Forward return after the declared evaluation window.",
            }
        ],
        "scorecardStatus": "partial",
        "limitations": ["strict_point_in_time_not_established"],
        "provenance": {"source": "research-core-test"},
    }


def test_eval_result_version_is_stable():
    assert EVAL_RESULT_VERSION == "trading_research.eval_result.v1"


def test_valid_eval_result_is_accepted():
    validate_eval_result(eval_result())


def test_eval_result_rejects_duplicate_metric_ids():
    payload = eval_result()
    payload["metrics"].append(dict(payload["metrics"][0]))
    with pytest.raises(ValueError, match="duplicate metricId"):
        validate_eval_result(payload)


def test_public_package_exports_new_contracts():
    import research_core

    assert research_core.RESEARCH_EXPERIMENT_VERSION == RESEARCH_EXPERIMENT_VERSION
    assert research_core.AGENT_RUN_VERSION == AGENT_RUN_VERSION
    assert research_core.RESEARCH_EVIDENCE_VERSION == RESEARCH_EVIDENCE_VERSION
    assert research_core.EVAL_RESULT_VERSION == EVAL_RESULT_VERSION
    assert research_core.validate_research_experiment is validate_research_experiment
    assert research_core.validate_agent_run is validate_agent_run
    assert research_core.validate_research_evidence is validate_research_evidence
    assert research_core.validate_eval_result is validate_eval_result
