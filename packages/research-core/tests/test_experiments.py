import pytest

from research_core.experiments import (
    RESEARCH_EXPERIMENT_VERSION,
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
