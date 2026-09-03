# Research Run Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add vendor-neutral experiment, agent-run, research-evidence, and evaluation-result contracts to `research-core` so external research producers can publish auditable records without coupling the Dashboard to producer-specific schemas.

**Architecture:** Add four Draft 2020-12 JSON Schemas under `research_core.schemas` and one focused `research_core.experiments` module that loads them, exposes stable version constants, performs schema validation, and enforces the few cross-field invariants JSON Schema cannot express cleanly. Keep producer adapters, UI, network calls, raw traces, and strict PIT promotion out of this PR.

**Tech Stack:** Python 3.11+, `jsonschema` Draft 2020-12, `pytest`, `ruff`, `uv` workspace.

**Spec:** `docs/superpowers/specs/2026-09-03-research-run-contracts-design.md`

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

- [ ] **Step 1: Write failing tests for the experiment contract**

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

- [ ] **Step 2: Verify RED**

Run:

```bash
uv run --locked --package research-core pytest packages/research-core/tests/test_experiments.py -q
```

Expected: collection/import failure because `research_core.experiments` does not exist yet.

- [ ] **Step 3: Add the experiment schema and minimal validator**

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

- [ ] **Step 4: Verify GREEN**

Run the Task 1 tests and confirm all experiment tests pass.

- [ ] **Step 5: Commit**

Commit message:

```text
feat: add research experiment contract
```

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

- [ ] **Step 1: Write failing run/evidence tests**

Add a minimal completed run and evidence helper, then assert:

```python
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


def test_evidence_rejects_strict_pit_without_oos_eligibility():
    payload = research_evidence()
    payload["pointInTime"] = {
        "assurance": "strict_replay",
        "strict": True,
        "eligibleAsOosEvidence": False,
    }
    with pytest.raises(ValueError, match="strict point-in-time"):
        validate_research_evidence(payload)
```

Also test `additionalProperties` rejection on a task/evidence object.

- [ ] **Step 2: Verify RED**

Run the focused test module. Expected failures mention missing version constants/validators.

- [ ] **Step 3: Implement schemas and invariants**

`agent-run.v1` requires run identity/status/timestamps/model-harness envelope/budget/usage/tasks/artifact/evidence refs/limitations/provenance. Run and task status enum:

```text
pending, running, completed, incomplete, failed, timeout, budget_limited, cancelled
```

Terminal statuses require `completedAt`; `running`/`pending` do not. Enforce unique task IDs in Python.

`research-evidence.v1` requires evidence identity/type/source/timestamps/freshness/verification/artifact/hash/PIT/limitations/provenance. PIT assurance enum:

```text
unverified, signal_date_only, externally_timestamped, strict_replay
```

Enforce these conservative invariants in Python:

```text
strict=true requires assurance=strict_replay
strict=true requires eligibleAsOosEvidence=true
eligibleAsOosEvidence=true requires assurance in {externally_timestamped, strict_replay}
```

The validator does not infer or upgrade assurance from hashes or timestamps.

- [ ] **Step 4: Verify GREEN**

Run the focused tests and confirm run/evidence behavior passes.

- [ ] **Step 5: Commit**

Commit message:

```text
feat: add agent run and evidence contracts
```

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

- [ ] **Step 1: Write failing eval/export tests**

Add a minimal eval helper and assert:

```python
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
```

- [ ] **Step 2: Verify RED**

Run the focused module. Expected failures concern the missing eval contract/export symbols.

- [ ] **Step 3: Implement eval schema, duplicate check, and exports**

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

Enforce unique `metricId` values in Python. Do not load an experiment from disk or perform cross-file metric-reference checks in this validator.

Update `research_core.__init__` imports and `__all__`.

- [ ] **Step 4: Verify GREEN**

Run `test_experiments.py` and existing `research-core` tests.

- [ ] **Step 5: Commit**

Commit message:

```text
feat: add evaluation result contract
```

---

### Task 4: Documentation and complete verification

**Files:**
- Modify: `packages/research-core/README.md`
- Update PR description after verification.

**Interfaces:**
- Documents the four new canonical contracts, validators, and ownership boundaries.

- [ ] **Step 1: Update README**

Document:

```text
trading_research.research_experiment.v1
trading_research.agent_run.v1
trading_research.research_evidence.v1
trading_research.eval_result.v1
```

Add the four validators to the shared-package API list and state that detailed producer artifacts remain producer-owned; `research-core` stores canonical wire records and does not confer strict PIT/OOS status by itself.

- [ ] **Step 2: Run focused tests**

```bash
uv run --locked --package research-core pytest packages/research-core/tests/test_experiments.py -q
```

Expected: PASS.

- [ ] **Step 3: Run full research-core test suite**

```bash
uv run --locked --package research-core pytest packages/research-core/tests -q
```

Expected: PASS.

- [ ] **Step 4: Run lint**

```bash
uv run --locked --package research-core ruff check packages/research-core/src packages/research-core/tests
```

Expected: PASS.

- [ ] **Step 5: Inspect PR diff and secret/data boundaries**

Confirm changed files are limited to design/plan docs plus `research-core` schemas, module, tests, exports, and README. Confirm no `.env`, credentials, raw market data, provider responses, large research artifacts, or local absolute paths were added.

- [ ] **Step 6: Update PR description and mark ready for review**

Record only commands that actually ran and their observed results. Keep external adapters/UI/live trading explicitly out of scope.

- [ ] **Step 7: Final commit if README/cleanup is not already committed**

Commit message:

```text
docs: document research run contracts
```
