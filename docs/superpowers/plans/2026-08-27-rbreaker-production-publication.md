# R-Breaker Production Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fail-closed, repeatable R-Breaker input-artifact → generic snapshot → scoped Dashboard publication PR pipeline without changing R-Breaker strategy calculations.

**Architecture:** Extend the existing snapshot publisher with an explicit strategy publication-target registry instead of duplicating a second publisher. Add one R-Breaker-specific manual workflow that downloads the validated input artifact, runs the existing generator, then invokes the shared publisher with `strategy_id=r-breaker`. Keep Niu Men as the default publisher target for backward compatibility.

**Tech Stack:** Python 3.11+, pytest, research-core JSON Schema validators, GitHub Actions, uv, existing Dashboard static-asset validator.

**Spec:** `docs/superpowers/specs/2026-08-27-rbreaker-production-publication-design.md`

## Global Constraints

- Do not modify R-Breaker trading rules, parameters, signal logic, or backtest calculations.
- Do not commit raw minute bars or downloaded artifact contents.
- Preserve existing Niu Men `research.json` publication behavior and default CLI semantics.
- Publication target must be selected explicitly by strategy id; do not infer it from filenames.
- Wrong-strategy, invalid-schema, and incomplete-provenance candidates must fail before any target write.
- GitHub Actions remain manual-only.

---

### Task 1: Define multi-strategy publisher behavior with failing tests

**Files:**
- Modify: `tests/test_publish_research_snapshot.py`
- Read: `packages/research-core/src/research_core/strategy_snapshot.py`
- Read: `apps/dashboard/web/public/rbreaker-research.json`

**Interfaces:**
- Consumes: existing `publish(snapshot_path, *, data_path, target)` compatibility API.
- Produces: tests requiring `publish(..., strategy_id="r-breaker")`, R-Breaker identity/provenance validation, and Niu Men default compatibility.

- [ ] **Step 1: Add a helper that creates a valid production-shaped R-Breaker envelope**

Base it on the committed generic R-Breaker fixture but set `quality.status="pass"` and populate all required provenance fields including `artifactRunId` and `inputSha256`.

- [ ] **Step 2: Add failing tests**

Add tests proving:

```python
published = publish(candidate, strategy_id="r-breaker", data_path=data_path, target=target)
assert published == target
assert read_json(target)["strategy"]["id"] == "r-breaker"
```

Add a wrong strategy test changing `strategy.id` to `niu-men-line`, expecting a `ValueError` before the previous target bytes change.

Add incomplete provenance test removing `artifactRunId`, expecting failure before write.

Keep the existing Niu Men `publish(candidate, data_path=..., target=...)` test unchanged to prove default compatibility.

- [ ] **Step 3: Run focused tests and confirm RED**

Run: `uv run pytest tests/test_publish_research_snapshot.py -q`

Expected: new R-Breaker tests fail because `publish()` does not accept/handle `strategy_id` yet; existing Niu Men tests remain green.

---

### Task 2: Implement explicit publication targets

**Files:**
- Modify: `scripts/publish_research_snapshot.py`
- Test: `tests/test_publish_research_snapshot.py`

**Interfaces:**
- Produces: `PublicationTarget`, `PUBLICATION_TARGETS`, `publication_target(strategy_id)`, and `publish(..., strategy_id="niu-men-line")`.
- `r-breaker` validator uses `validate_strategy_snapshot()` and explicit identity/provenance checks.

- [ ] **Step 1: Add target constants and validator imports**

Add `R_BREAKER_RESEARCH_PATH` and import `validate_strategy_snapshot`.

- [ ] **Step 2: Add target-specific validators**

Niu Men validator keeps `validate_snapshot()` + `validate_provenance_consistency()`.

R-Breaker validator must reject unless:

```python
payload["strategy"]["id"] == "r-breaker"
payload["quality"]["status"] == "pass"
```

and each required provenance field is a non-empty string.

- [ ] **Step 3: Route `publish()` through explicit strategy id**

Default strategy id remains `niu-men-line`. Resolve the configured default target only when the caller does not supply a test target override. Validate before reading/storing previous target bytes.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run: `uv run pytest tests/test_publish_research_snapshot.py -q`

Expected: all publisher tests pass.

- [ ] **Step 5: Commit**

Commit message: `feat: publish R-Breaker strategy snapshots`

---

### Task 3: Make scoped PR metadata strategy-aware

**Files:**
- Modify: `tests/test_publish_research_snapshot.py`
- Modify: `scripts/publish_research_snapshot.py`

**Interfaces:**
- Produces: `_snapshot_data_date(payload)`, strategy-aware branch/title/body generation, `open_update_pr(..., strategy_id=...)`.

- [ ] **Step 1: Add failing metadata tests**

Test generic envelope date extraction from top-level `dataDate` and Niu Men compatibility from `source.dataDate`.

Test that R-Breaker branch prefix/title/body contain `r-breaker` and only the supplied target path is staged.

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `uv run pytest tests/test_publish_research_snapshot.py -q`

Expected: metadata tests fail against the current hard-coded branch/date behavior.

- [ ] **Step 3: Implement minimal strategy-aware PR metadata**

Use `publish/<strategy-id>-snapshot-<timestamp>` and `chore: publish <strategy-id> snapshot for <date>`.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run: `uv run pytest tests/test_publish_research_snapshot.py -q`

Expected: pass.

- [ ] **Step 5: Commit**

Commit message: `feat: scope strategy publication pull requests`

---

### Task 4: Add R-Breaker publication workflow contract tests

**Files:**
- Create: `tests/test_rbreaker_publish_workflow.py`
- Create later: `.github/workflows/publish-rbreaker-snapshot.yml`

**Interfaces:**
- Produces contract for a manual-only workflow with artifact auth, generator invocation, and shared publisher invocation.

- [ ] **Step 1: Write failing workflow tests**

Parse `.github/workflows/publish-rbreaker-snapshot.yml` and assert:

```python
assert set(workflow["on"]) == {"workflow_dispatch"}
assert "RESEARCH_ARTIFACT_TOKEN" in text
assert "generate_rbreaker_snapshot" in text
assert "--strategy-id r-breaker" in text
assert "--open-pr" in text
assert "git add incoming-rbreaker" not in text
```

Also assert workflow inputs include `artifact_repository`, `artifact_run_id`, and `artifact_name`.

- [ ] **Step 2: Run test and confirm RED**

Run: `uv run pytest tests/test_rbreaker_publish_workflow.py -q`

Expected: fail because workflow file does not exist.

---

### Task 5: Implement manual R-Breaker publication workflow

**Files:**
- Create: `.github/workflows/publish-rbreaker-snapshot.yml`
- Modify: `scripts/check_foundation.py`
- Test: `tests/test_rbreaker_publish_workflow.py`
- Test: `tests/test_foundation.py` if workflow allowlist behavior requires an explicit assertion.

**Interfaces:**
- Consumes: `trading_research.scripts.generate_rbreaker_snapshot` and `scripts/publish_research_snapshot.py --strategy-id r-breaker`.
- Produces: manual production publication path from artifact run id to scoped snapshot PR.

- [ ] **Step 1: Add workflow**

Use `workflow_dispatch` only. Download artifact with same-repo `github.token` or cross-repo `RESEARCH_ARTIFACT_TOKEN`. Generate to a temporary `generated-snapshot/rbreaker-research.json` path, then publish/open PR.

- [ ] **Step 2: Add workflow to foundation allowlist**

Add only `.github/workflows/publish-rbreaker-snapshot.yml` to `M1_FOUNDATION_TRACKED_FILES`.

- [ ] **Step 3: Run focused tests**

Run: `uv run pytest tests/test_rbreaker_publish_workflow.py tests/test_foundation.py -q`

Expected: pass.

- [ ] **Step 4: Parse workflow YAML**

Run: `python -c "import yaml,pathlib; yaml.safe_load(pathlib.Path('.github/workflows/publish-rbreaker-snapshot.yml').read_text())"`

Expected: exit 0.

- [ ] **Step 5: Commit**

Commit message: `ci: publish R-Breaker research snapshots`

---

### Task 6: Update CLI and documentation state

**Files:**
- Modify: `scripts/publish_research_snapshot.py`
- Modify: `docs/roadmap/README.md`
- Modify: `README.md`
- Modify: `apps/dashboard/docs/research-snapshot.md`
- Test: `tests/test_publish_research_snapshot.py`

**Interfaces:**
- CLI adds `--strategy-id` with explicit supported choices and default `niu-men-line`.

- [ ] **Step 1: Add CLI test or direct parser coverage for explicit R-Breaker target**

Ensure the production workflow command is supported and unknown strategy ids fail clearly.

- [ ] **Step 2: Implement CLI option**

Pass `strategy_id` to both `publish()` and `open_update_pr()`.

- [ ] **Step 3: Refresh documentation**

Record PR #37/#38 as merged, describe R-Breaker publication as implemented by this branch, and do not claim any real publication run or M6 shadow evidence until it occurs.

- [ ] **Step 4: Run focused tests**

Run: `uv run pytest tests/test_publish_research_snapshot.py tests/test_rbreaker_publish_workflow.py -q`

Expected: pass.

- [ ] **Step 5: Commit**

Commit message: `docs: document R-Breaker publication path`

---

### Task 7: Full verification and review

**Files:** all files touched above.

- [ ] **Step 1: Run root Python tests**

Run: `uv run pytest`

Expected: all pass.

- [ ] **Step 2: Run Dashboard tests**

Run: `uv run --package t0-trading-dashboard pytest apps/dashboard/tests`

Expected: all pass.

- [ ] **Step 3: Run Ruff**

Run: `uv run ruff check .`

Expected: pass.

- [ ] **Step 4: Run frontend tests/build**

Run from `apps/dashboard/web`: `npm test`, then `npm run build`.

Expected: both pass.

- [ ] **Step 5: Run foundation and lock checks**

Run: `uv run python scripts/check_foundation.py`

Run: `uv lock --check`

Expected: both pass.

- [ ] **Step 6: Review diff for protected data and credentials**

Confirm the diff contains no downloaded artifact, minute bars, credentials, tokens, or machine-specific paths.

- [ ] **Step 7: Open PR**

Title: `feat: add R-Breaker production publication`

Keep PR draft if any full verification command could not be executed or if a real artifact publication smoke run remains outstanding.
