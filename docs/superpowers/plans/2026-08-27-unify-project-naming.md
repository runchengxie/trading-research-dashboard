# Unify Trading Research Dashboard Project Naming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `trading-research-dashboard` the canonical project and distribution name while preserving historical source-repository names and stable Python import paths.

**Architecture:** Update active project metadata, lockfile metadata, and current-facing documentation. Keep `wu-t0-trading-dashboard` and `a-share-trading-research` only where they are historical migration evidence; keep `trading_research` unchanged as the Dashboard Python import package.

**Tech Stack:** Python packaging, uv workspace, Markdown documentation, GitHub repository metadata.

**Spec:** Naming decisions established from the current repository audit and existing `docs/superpowers/specs/` records.

## Global Constraints

- Canonical repository and project name: `trading-research-dashboard`.
- Do not rename the Python import package `trading_research`.
- Do not rewrite historical source repository names in migration records.
- Do not enable new GitHub Actions triggers.
- Work only on branch `chore/unify-project-naming`.

---

### Task 1: Align Dashboard distribution metadata

**Files:**
- Modify: `apps/dashboard/pyproject.toml`

- [x] Change the Dashboard distribution to `trading-research-dashboard-app` because the root workspace owns the canonical `trading-research-dashboard` name.
- [x] Keep `trading_research` in the script entry points and wheel package configuration.
- [x] Check that no code imports the distribution name directly.

### Task 2: Refresh workspace lock metadata

**Files:**
- Modify: `uv.lock`

- [x] Regenerate the lock file with `uv lock` so workspace members match the active `pyproject.toml` files.
- [x] Confirm the old `t0-trading-dashboard` workspace package is removed and the app package is `trading-research-dashboard-app`.

### Task 3: Update active documentation and validation expectations

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture/project-structure.md`
- Modify: `docs/roadmap/README.md`
- Modify: `scripts/check_foundation.py`
- Modify: active documentation that describes the current monorepo name

- [x] State that the local checkout should be named `trading-research-dashboard`.
- [x] Replace active references to `a-share-trading-research` with the canonical name.
- [x] Preserve old names in migration history, source commit tables, and historical design records.
- [x] Update foundation checks only when a current canonical path or filename is being validated.

### Task 4: Verify and publish the naming cleanup

- [x] Run targeted searches for stale active names and review every remaining occurrence.
- [x] Run `uv lock --check`, focused foundation tests, and the repository foundation check.
- [x] Review the diff for accidental import/package or historical-record changes.
- [x] Commit the changes with `chore: unify project naming`.
- [x] Push the branch and open Draft PR #40.
