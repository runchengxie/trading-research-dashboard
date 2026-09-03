# Research Run Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add vendor-neutral experiment, agent-run, research-evidence, and evaluation-result contracts to `research-core` so external research producers can publish auditable records without coupling the Dashboard to producer-specific schemas.

**Architecture:** Add four Draft 2020-12 JSON Schemas under `research_core.schemas` and one focused `research_core.experiments` module that loads them, exposes stable version constants, performs schema validation, and enforces the few cross-field invariants JSON Schema cannot express cleanly. Keep producer adapters, UI, network calls, raw traces, and strict PIT promotion out of this PR.

**Tech Stack:** Python 3.11+, `jsonschema` Draft 2020-12, `pytest`, `ruff`, `uv` workspace.

**Spec:** `docs/superpowers/specs/2026-09-03-research-run-contracts-design.md`

## Review corrections

Implementation review refined three details before v1 was exposed to external consumers:

- strict Point-in-time correctness and OOS eligibility are independent axes. `strict=true` requires `strict_replay`, but strict replay may remain `eligibleAsOosEvidence=false` when the case is still in model-training or research-development scope;
- `agent_run.budget` and `agent_run.usage` remain required envelopes but may be empty when the producer did not declare or observe those values. Adapters must not invent token, cost, or latency values merely to satisfy the contract;
- task dependencies form a real DAG: dependencies must reference tasks in the same run, cycles are rejected, and a `completed` run cannot contain non-completed tasks. All four canonical records also require a non-empty `provenance.source`.

These corrections supersede the earlier draft invariant that coupled strict PIT to OOS eligibility.

## Global Constraints

- New contracts are additive and must not modify existing snapshot wire formats.
- Do not add network calls, React changes, market-data changes, broker connections, or external-repository source copies.
- Do not persist hidden chain-of-thought in canonical contracts.
- SHA-256 or producer-reported timestamps must never upgrade evidence to strict point-in-time or OOS status.
- `ai-stock-picker` records with `strict_point_in_time=false` and `eligible_as_oos_evidence=false` must remain conservatively representable.
- `incomplete` is a valid terminal run/task status distinct from `completed` and `failed`.
- JSON objects use `additionalProperties: false` unless a deliberately open metadata/value object is required.
- Cross-object references such as eval metric IDs against a separately loaded experiment remain outside v1 file-level validation.

---

### Task 1: Research experiment contract

**Files:**
- Create: `packages/research-core/tests/test_experiments.py`
- Create: `packages/research-core/src/research_core/schemas/research-experiment.v1.schema.json`
- Create: `packages/research-core/src/research_core/experiments.py`

**Interfaces:**
- Produces: `RESEARCH_EXPERIMENT_VERSION: str`
- Produces: `validate_research_experiment(payload: Mapping[str, Any]) -> None`
- Later tasks extend the same module with the other three validators.

- [x] **Step 1: Write failing tests for the experiment contract**

Add helpers that build a minimal valid experiment and tests that assert:

```python
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
```

The fixture includes two variants (`numeric` baseline and `llm`) and one scorecard metric.

- [x] **Step 2: Verify RED**

Focused test collection failed before `research_core.experiments` existed.

- [x] **Step 3: Add the experiment schema and minimal validator**

The schema requires:

```text
schemaVersion, experimentId, objective, taskType, market, createdAt,
caseSet, baselineVariantId, variants, scorecard, constraints, provenance
```

Variant `kind` enum:

```text
numeric_baseline, single_agent, multi_agent, model, harness, custom
```

Scorecard direction enum:

```text
maximize, minimize, target
```

`experiments.py` loads the schema with `importlib.resources.files`, uses `Draft202012Validator`, reports the first sorted schema error, then checks duplicate `variantId`, duplicate `metricId`, and membership of `baselineVariantId` in `variants`.

- [x] **Step 4: Verify GREEN**

The focused experiment tests passed after the minimal implementation.

- [x] **Step 5: Commit**

Implemented on `feat/research-run-contracts`.

---

### Task 2: Agent run and research evidence contracts

**Files:**
- Modify: `packages/research-core/tests/test_experiments.py`
- Create: `packages/research-core/src/research_core/schemas/agent-run.v1.schema.json`
- Create: `packages/research-core/src/research_core/schemas/research-evidence.v1.schema.json`
- Modify: `packages/research-core/src/research_core/experiments.py`

**Interfaces:**
- Produces: `AGENT_RUN_VERSION: str`
- Produces: `RESEARCH_EVIDENCE_VERSION: str`
- Produces: `validate_agent_run(payload: Mapping[str, Any]) -> None`
- Produces: `validate_research_evidence(payload: Mapping[str, Any]) -> None`

- [x] **Step 1: Write failing run/evidence tests**

Coverage includes valid run/evidence records, terminal timestamps, `incomplete`, duplicate tasks, unexpected trace fields, DAG integrity, undeclared budget/usage, PIT/OOS semantics, provenance, and unexpected evidence fields.

- [x] **Step 2: Verify RED**

The focused suite first failed on missing run/evidence interfaces. Later review tests also failed against the over-strict budget rule, missing DAG validation, coupled PIT/OOS rule, and weak provenance object before each corresponding implementation fix.

- [x] **Step 3: Implement schemas and invariants**

`agent-run.v1` status enum:

```text
pending, running, completed, incomplete, failed, timeout, budget_limited, cancelled
```

Terminal statuses require `completedAt`; task IDs are unique; dependencies must reference the same run and form an acyclic graph; a completed run contains only completed tasks. Empty `budget` or `usage` means the producer did not declare or observe values.

`research-evidence.v1` assurance enum:

```text
unverified, signal_date_only, externally_timestamped, strict_replay
```

Final conservative invariants:

```text
strict=true requires assurance=strict_replay
eligibleAsOosEvidence=true requires assurance in {externally_timestamped, strict_replay}
strict PIT does not imply OOS eligibility
```

The validator does not infer or upgrade assurance from hashes or timestamps.

- [x] **Step 4: Verify GREEN**

Focused tests passed after the run/evidence implementation and review corrections.

- [x] **Step 5: Commit**

Implemented on `feat/research-run-contracts`.

---

### Task 3: Evaluation result contract and public exports

**Files:**
- Modify: `packages/research-core/tests/test_experiments.py`
- Create: `packages/research-core/src/research_core/schemas/eval-result.v1.schema.json`
- Modify: `packages/research-core/src/research_core/experiments.py`
- Modify: `packages/research-core/src/research_core/__init__.py`

**Interfaces:**
- Produces: `EVAL_RESULT_VERSION: str`
- Produces: `validate_eval_result(payload: Mapping[str, Any]) -> None`
- Re-exports all four new version constants and validators from `research_core`.

- [x] **Step 1: Write failing eval/export tests**

Tests cover the stable version, valid eval, duplicate metrics, and package exports.

- [x] **Step 2: Verify RED**

The focused suite failed before the eval interface and public exports existed.

- [x] **Step 3: Implement eval schema, duplicate check, and exports**

`eval-result.v1` requires:

```text
schemaVersion, evalId, experimentId, caseId, runId, variantId,
evaluatedAt, status, metrics, scorecardStatus, limitations, provenance
```

Metric status enum:

```text
pass, fail, informational, unavailable
```

Scorecard status enum:

```text
pass, fail, partial, insufficient_evidence
```

Unique `metricId` values are enforced in Python. Cross-file experiment metric-reference checks remain outside this file-level validator.

- [x] **Step 4: Verify GREEN**

The focused module and full `research-core` suite pass in PR CI.

- [x] **Step 5: Commit**

Implemented on `feat/research-run-contracts`.

---

### Task 4: Documentation and complete verification

**Files:**
- Modify: `packages/research-core/README.md`
- Modify: `.github/workflows/pr-ci.yml`
- Update PR description after verification.

**Interfaces:**
- Documents the four new canonical contracts, validators, ownership boundaries, DAG/PIT/OOS semantics, and vendor-neutral unknown budget/usage behavior.
- Adds `research-core` pytest and ruff to the PR quality gate.

- [x] **Step 1: Update README**

README documents all four contracts, producer ownership, hidden-reasoning boundary, task DAG consistency, PIT/OOS independence, and provenance source.

- [x] **Step 2: Run focused tests**

RED/GREEN cycles were executed in an isolated local test package while GitHub changes were being assembled.

- [x] **Step 3: Run full research-core test suite**

GitHub PR CI runs `uv run --locked pytest -q` from `packages/research-core` and passes on the final head.

- [x] **Step 4: Run lint**

GitHub PR CI runs `uv run --locked ruff check src tests`; final output is `All checks passed!`.

- [x] **Step 5: Inspect PR diff and secret/data boundaries**

The PR changes only the design/plan, `research-core` schemas/module/tests/exports/README, and the PR quality workflow. No `.env`, credentials, raw market data, provider responses, large research artifacts, or local absolute data paths are added.

- [x] **Step 6: Update PR description and mark ready for review**

Performed after final-head verification.

- [x] **Step 7: Final documentation cleanup**

README and this plan record the final reviewed semantics.
