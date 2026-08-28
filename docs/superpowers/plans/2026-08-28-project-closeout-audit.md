# Project Closeout Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the monorepo documentation, quality gates, and maintenance guidance accurately describe the current trading research dashboard and its embedded strategy packages.

**Architecture:** First establish an evidence-based audit of repository facts, quality tooling, workflows, and package boundaries. Then apply only low-risk, independently verifiable documentation and gate improvements. Runtime behavior changes remain separate from this closeout unless a failing check proves they are required.

**Tech Stack:** Markdown, GitHub Actions, Python with uv/pytest/ruff/ty/coverage/pip-audit, TypeScript/Vite with npm tests and build.

**Spec:** `docs/roadmap/README.md` and the user-requested documentation and maintenance audit.

## Global Constraints

- Preserve the current monorepo ownership model and embedded package boundaries.
- Do not commit credentials, raw provider data, local caches, build output, or generated test artifacts.
- Keep documentation in natural Chinese with Chinese punctuation where the surrounding text is Chinese.
- Use an isolated worktree and one PR for this closeout batch.
- Run fresh verification before claiming any item complete.

---

### Task 1: Establish repository and subproject inventory

**Files:**
- Read: `AGENTS.md`, `README.md`, `pyproject.toml`
- Read: `apps/dashboard/pyproject.toml`, `apps/market-data-service/pyproject.toml`
- Read: `packages/research-core/pyproject.toml`, `packages/niu-men-line-strategy/pyproject.toml`
- Read: `.gitmodules`, `.github/workflows/`

- [x] Confirm whether external Git submodules exist. None are registered.
- [x] Record package ownership, public entry points, provider support, and deployment paths.
- [x] Record discrepancies between roadmap claims and current workflow behavior.

### Task 2: Audit documentation and maintenance claims

**Files:**
- Read: `AGENTS.md`, `README.md`, `docs/README.md`
- Read: `docs/getting-started.md`, `docs/architecture/project-structure.md`
- Read: `docs/maintenance/quality-audit.md`, `docs/roadmap/README.md`
- Read: `docs/operations/runtime-cutover.md`, `docs/operations/legacy-retirement.md`
- Read: `apps/dashboard/README.md`, `apps/market-data-service/README.md`
- Read: `packages/research-core/README.md`, `packages/niu-men-line-strategy/README.md`

- [x] Compare every current-state statement with repository code and workflows.
- [x] Update current docs for yfinance, market switching, sharing, static TSLA demo data, M6, and M6b.
- [x] Clarify known limitations such as R-Breaker single-symbol snapshots and optional Cloudflare smoke checks.
- [x] Rewrite the concrete setup and current-state passages that were difficult to use.

### Task 3: Audit quality gates and ignored checks

**Files:**
- Read: `pyproject.toml`
- Read: all package `pyproject.toml` files
- Read: `.github/workflows/foundation.yml`, `.github/workflows/deploy-dashboard.yml`
- Read: `apps/dashboard/web/package.json`, `apps/dashboard/web/tsconfig.json`
- Read: `.gitignore` files and source-level `# noqa` / `# type: ignore` occurrences

- [x] Run the repository's existing Python tests, package tests, web tests, builds, lint, type, coverage, dependency audit, and foundation checks.
- [x] Separate the pre-existing `ty` failures from intentional exclusions and document the remaining maintenance limits.
- [x] Verify that Playwright output, cache, raw data, and credentials cannot enter the repository or share archive.
- [x] Add a committed TSLA demo snapshot regression check.

### Task 4: Audit code structure and dead code

**Files:**
- Read: Python source and scripts under `apps/`, `packages/`, and `scripts/`
- Read: TypeScript source under `apps/dashboard/web/src/`

- [x] Find duplicate entry points, compatibility shims, one-off scripts, unreachable branches, and unused dependencies.
- [x] Trace imports between dashboard, market-data service, research-core, and Niu Men package.
- [x] Check long functions, oversized modules, broad exception handling, and unnecessary abstraction layers.
- [x] Do not delete code based only on name matching. No deletion was justified by the audit evidence.

### Task 5: Implement high-value closeout changes

**Files:**
- Modify: documentation files identified in Tasks 2–4
- Modify: quality workflow or configuration only when a reproducible gap is found
- Test: relevant existing tests plus any new regression check

- [x] Write a regression test for the committed demo snapshot requirement.
- [x] Apply the smallest changes that resolve the documented discrepancies and CI type failures.
- [x] Run targeted checks after each change, then run the full closeout verification matrix.
- [x] Commit the closeout changes with a focused message.

### Task 6: Review, merge, and clean up

**Files:**
- Read: final diff, final plan, and generated audit output

- [ ] Confirm no secrets, raw data, caches, or test artifacts are in the diff.
- [ ] Push the feature branch and open a PR.
- [ ] Merge the PR into `main`.
- [ ] Delete the feature branch and worktree after merge.
- [ ] Report verified results and any external configuration still needed.
