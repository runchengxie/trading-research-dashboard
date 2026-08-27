# M6 Runtime Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move weekday Dashboard generation/deploy and research publication authority to the monorepo, prove the new path in shadow mode, freeze legacy production writes only after a successful authoritative run, and retain explicit rollback paths.

**Architecture:** Implement monorepo runtime safety and a scheduled `dashboard-report.yml` in shadow mode first. After five successful trading-day shadows and verified research publication, switch production authority through a small schedule activation PR, then merge two legacy freeze PRs. Observe five additional trading days before closing #19; GitHub Archive remains outside M6.

**Tech Stack:** GitHub Actions, Python 3.11/uv workspace, existing Dashboard generator/validator/build/deploy scripts, Cloudflare Workers Static Assets, GitHub artifacts, repository PRs.

**Spec:** `docs/superpowers/specs/2026-08-26-m6-runtime-cutover-design.md`

## Global Constraints

- M4 publication from PR #26 is an existing dependency; do not reimplement snapshot publishing.
- M5 must have reached production-readiness with verified static fallback before authoritative cutover.
- Never disable a legacy production write path before the replacement path has a successful authoritative run.
- Scheduled shadow runs use `01:10 UTC` on weekdays; the old Dashboard currently runs at `01:00 UTC`.
- Shadow mode may generate artifacts but must not deploy, push, commit cache or modify production.
- Do not commit raw market data/cache generated at runtime.
- Git `apps/dashboard/web/public/data.json` remains reviewed fallback; daily runtime candidates are not pushed to `main` automatically.
- Current connector cannot dispatch arbitrary workflows; required workflow runs are explicit human/runner gates and must be recorded as evidence.
- Cross-private-repo artifact downloads require a token with target-repository `actions:read`; do not assume the current repository `GITHUB_TOKEN` has that scope.
- M6 does not archive or delete repositories.

---

### Task 1: Harden cross-repository research artifact authentication

**Files:**
- Modify: `.github/workflows/publish-research-snapshot.yml`
- Modify: `tests/test_foundation.py`
- Modify: `docs/operations/runtime-cutover.md` (create initially with auth section and evidence placeholders expressed as `not-yet-run`, not TODO markers)

**Interfaces:**
- Same-repository artifacts use `github.token`.
- Cross-repository artifacts require `secrets.RESEARCH_ARTIFACT_TOKEN`.

- [ ] **Step 1: Add a failing structural workflow test**

Require the workflow to fail fast when `artifact_repository != github.repository` and `RESEARCH_ARTIFACT_TOKEN` is empty. Require `actions/download-artifact` to select the dedicated token for cross-repo input.

- [ ] **Step 2: Run targeted root tests and verify RED**

```bash
uv run --locked --extra dev pytest -q tests/test_foundation.py
```

Expected: FAIL because the workflow still unconditionally passes the local token.

- [ ] **Step 3: Implement explicit token selection**

Use workflow environment values:

```yaml
env:
  RESEARCH_ARTIFACT_TOKEN: ${{ secrets.RESEARCH_ARTIFACT_TOKEN }}
```

Add a preflight shell step that exits nonzero for cross-repo input without the secret. For the download step use a GitHub expression selecting `github.token` only when `inputs.artifact_repository == github.repository`; otherwise select the dedicated secret.

- [ ] **Step 4: Re-run root tests and foundation checker**

```bash
uv run --locked --extra dev pytest -q tests/test_foundation.py
uv run --locked python scripts/check_foundation.py
git diff --check
```

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/publish-research-snapshot.yml tests/test_foundation.py docs/operations/runtime-cutover.md
git commit -m "ci: harden cross-repo research artifact auth"
```

### Task 2: Add runtime candidate safety validation

**Files:**
- Create: `apps/dashboard/scripts/check_runtime_candidate.py`
- Create: `apps/dashboard/tests/test_runtime_candidate.py`

**Interfaces:**
- Produces `validate_runtime_candidate(candidate: dict, baseline: dict) -> None`.
- CLI: `python scripts/check_runtime_candidate.py --candidate PATH --baseline PATH`.

- [ ] **Step 1: Write RED tests**

Cover empty `stocks`, missing baseline default symbol, candidate `generatedAt` older than baseline, candidate `lastTradeDay` regression for the default symbol, and a valid newer candidate.

- [ ] **Step 2: Run targeted Dashboard tests and verify RED**

```bash
cd apps/dashboard
uv run --locked pytest -q tests/test_runtime_candidate.py
```

- [ ] **Step 3: Implement the safety checker**

The checker must load JSON as objects, require at least one stock, preserve every symbol present in the baseline by default, compare parseable generated/data dates, and raise `ValueError` with a specific field/symbol reason. Do not recalculate indicators.

- [ ] **Step 4: Verify GREEN and commit**

```bash
uv run --locked pytest -q tests/test_runtime_candidate.py
```

```bash
git add scripts/check_runtime_candidate.py tests/test_runtime_candidate.py
git commit -m "feat: validate Dashboard runtime candidates"
```

### Task 3: Add shadow-capable monorepo weekday report workflow

**Files:**
- Create: `.github/workflows/dashboard-report.yml`
- Create: `apps/dashboard/scripts/write_runtime_manifest.py`
- Create: `apps/dashboard/tests/test_runtime_manifest.py`
- Modify: `tests/test_foundation.py`
- Modify: `docs/operations/runtime-cutover.md`

**Interfaces:**
- Manual input `mode` is `shadow | authoritative`, default `shadow`.
- Scheduled mode is controlled by a single literal `SCHEDULE_MODE=shadow` in the workflow until Task 6.
- Artifact name is `dashboard-runtime-candidate-${{ github.run_id }}` and contains `data.json` plus `runtime-manifest.json`.

- [ ] **Step 1: Write RED manifest tests**

`runtime-manifest.json` must contain monorepo SHA, mode, data generatedAt, workflow run id when supplied, createdAt UTC, and public URL only for authoritative mode.

- [ ] **Step 2: Implement manifest writer**

CLI accepts `--data-json`, `--mode`, `--commit`, `--output`, optional `--run-id`, optional `--public-url`. Reject `authoritative` manifest without a public URL after deploy.

- [ ] **Step 3: Add RED workflow-structure tests**

Require:

```yaml
schedule:
  - cron: "10 1 * * 1-5"
```

and require shadow scheduled runs to omit deploy/push/cache commit behavior.

- [ ] **Step 4: Implement workflow**

Workflow sequence for both modes:

```text
checkout -> uv setup -> copy tracked fallback to baseline temp path -> generate candidate -> static validation -> runtime candidate safety check -> npm ci/test/build -> upload candidate artifact
```

Only authoritative mode may run Wrangler deploy and post-deploy smoke; it then rewrites/uploads the deployed manifest. Preserve the tracked baseline copy before generator overwrite so candidate comparison is meaningful.

- [ ] **Step 5: Run structural/regression tests**

```bash
uv run --locked --extra dev pytest -q tests/test_foundation.py
(cd apps/dashboard && uv run --locked pytest -q tests/test_runtime_candidate.py tests/test_runtime_manifest.py)
uv run --locked python scripts/check_foundation.py
git diff --check
```

- [ ] **Step 6: Commit and open the shadow workflow PR**

```bash
git add .github/workflows/dashboard-report.yml apps/dashboard/scripts apps/dashboard/tests tests/test_foundation.py docs/operations/runtime-cutover.md
git commit -m "ci: add shadow Dashboard runtime report"
```

PR title: `ci: add shadow Dashboard runtime report`

### Task 4: Execute and record the pre-cutover shadow gates

**Files:**
- Modify after evidence exists: `docs/operations/runtime-cutover.md`

**Interfaces:**
- Consumes real GitHub Actions run URLs/artifact ids.
- Produces the evidence required before Task 6 can change scheduled authority.

- [ ] **Step 1: Configure repository secrets/variables outside Git**

Verify Cloudflare deployment values and market-data token variables are present in the monorepo repository settings. Do not add their values to files or comments.

- [ ] **Step 2: Run/observe five consecutive trading-day scheduled shadow cycles**

Each must have successful generation, static validation, runtime safety check, Web tests/build and candidate artifact. Record run URL, data date and artifact id in the runbook.

- [ ] **Step 3: Perform two manual same-day comparisons**

Compare the shadow artifact default symbol/date with the existing production page. Record only non-sensitive result summaries and links.

- [ ] **Step 4: Prove research publication authority**

Complete either a real cross-repo artifact publication using the dedicated token or a direct monorepo publication using `scripts/publish_research_snapshot.py`. Record at least three reviewed/dry-run cycles with at least one real publication as required by the spec.

- [ ] **Step 5: Commit evidence only after it exists**

```bash
git add docs/operations/runtime-cutover.md
git commit -m "docs: record pre-cutover runtime evidence"
```

Do not mark this task complete from planned dates or workflow definitions.

### Task 5: Prepare legacy Dashboard freeze PR

**Repository:** `runchengxie/wu-t0-trading-dashboard`

**Files:**
- Modify: `README.md`
- Modify: `.github/workflows/report.yml`

**Interfaces:**
- Normal production schedule/push paths are removed.
- Manual rollback requires exact input `confirm_legacy_rollback=legacy-dashboard-rollback`.

- [ ] **Step 1: Create a dedicated legacy freeze branch from current legacy `main`**

Record the legacy last-known-good SHA before editing.

- [ ] **Step 2: Add first-screen legacy banner**

State monorepo successor, last-known-good SHA, frozen/rollback purpose and runbook location.

- [ ] **Step 3: Change `report.yml` triggers**

Remove `push` and `schedule`. Keep only `workflow_dispatch` with required string input `confirm_legacy_rollback`.

- [ ] **Step 4: Add acknowledgement guard before any generation/write/deploy**

First executable job step must fail unless:

```bash
test "$CONFIRM_LEGACY_ROLLBACK" = "legacy-dashboard-rollback"
```

Remove the automatic `git add data/raw` cache commit step from the rollback workflow.

- [ ] **Step 5: Review diff and open freeze PR but do not merge yet**

PR title: `ops: freeze legacy Dashboard production writes`

### Task 6: Prepare legacy Niu Men freeze PR

**Repository:** `runchengxie/niu-men-line-strategy`

**Files:**
- Modify: `README.md`
- Modify: `.github/workflows/publish-dashboard-snapshot.yml`

**Interfaces:**
- Ordinary CI stays intact.
- Legacy publish rollback requires exact input `confirm_legacy_publish=legacy-niu-men-publish-rollback`.

- [ ] **Step 1: Record legacy Niu Men last-known-good SHA**

Add it to the freeze PR body and later runbook.

- [ ] **Step 2: Add first-screen successor banner**

Point to `runchengxie/a-share-trading-research/tree/main/packages/niu-men-line-strategy`.

- [ ] **Step 3: Convert publish workflow to explicit rollback-only**

Remove any normal default target behavior. Require acknowledgement before checkout of target Dashboard or PR creation.

- [ ] **Step 4: Open freeze PR but do not merge yet**

PR title: `ops: freeze legacy Niu Men Dashboard publication`

### Task 7: Perform cutover-day authoritative run and freeze legacy writes

**Files:**
- Modify after evidence: `docs/operations/runtime-cutover.md`

**Interfaces:**
- Requires Task 4 gates and both freeze PRs to be ready.

- [ ] **Step 1: Manually dispatch monorepo `dashboard-report.yml` with `mode=authoritative`**

Require generate/validate/build/deploy/smoke to pass and verify public `data.json` date matches the candidate manifest.

- [ ] **Step 2: Merge legacy Dashboard freeze PR**

Only after Step 1 production success.

- [ ] **Step 3: Merge legacy Niu Men freeze PR**

Only after Step 1 and after monorepo research publication authority has been proven.

- [ ] **Step 4: Re-run monorepo deploy/foundation smoke**

Record run URLs and freeze merge SHAs.

- [ ] **Step 5: Commit cutover-day evidence**

Update runbook with exact monorepo SHA, two legacy rollback SHAs, production URL and run links.

### Task 8: Activate authoritative schedule through a separate rollback-point PR

**Files:**
- Modify: `.github/workflows/dashboard-report.yml`
- Modify: `tests/test_foundation.py`
- Modify: `docs/operations/runtime-cutover.md`

**Interfaces:**
- Changes only scheduled mode literal from `shadow` to `authoritative`; manual input remains selectable.

- [ ] **Step 1: Add/change structural test to require authoritative schedule literal**

- [ ] **Step 2: Change only the schedule mode constant**

Do not mix unrelated workflow refactors into this PR.

- [ ] **Step 3: Run root validation**

```bash
uv run --locked --extra dev pytest -q tests/test_foundation.py
uv run --locked python scripts/check_foundation.py
git diff --check
```

- [ ] **Step 4: Open small production authority PR**

PR title: `ops: make monorepo Dashboard report authoritative`

This PR is the Git rollback point for scheduled production authority.

### Task 9: Observe five post-cutover trading days and close #19 only with evidence

**Files:**
- Modify: `docs/operations/runtime-cutover.md`
- Modify: `docs/roadmap/README.md`

- [ ] **Step 1: Record five consecutive scheduled authoritative runs**

Each needs deploy/smoke success or a documented incident resolved without legacy unscheduled writes.

- [ ] **Step 2: Confirm static fallback with M5 live service unavailable**

Run Dashboard with realtime endpoint absent/offline and verify static page remains usable.

- [ ] **Step 3: Confirm no legacy normal production writes**

Verify old Dashboard has no scheduled deploy and old Niu Men has no normal publish to old Dashboard.

- [ ] **Step 4: Complete at least one post-cutover research publication via monorepo**

- [ ] **Step 5: Run final repository gates**

```bash
uv lock --check
uv run --locked --extra dev pytest -q
(cd apps/dashboard && uv run --locked pytest -q)
uv run --locked python scripts/check_foundation.py
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
npm audit --prefix apps/dashboard/web --audit-level=high
git diff --check
```

- [ ] **Step 6: Update roadmap and close #19**

Only after all real observation evidence exists. Do not archive legacy repositories in this task.
