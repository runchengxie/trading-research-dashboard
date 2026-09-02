# Dashboard Platform Publication Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist and display public workspace research projections while preserving a static Dashboard runtime.

**Architecture:** Build-time installer validates/filter/copies a public projection into `web/public`; browser-time code only reads the filtered static manifest. A dedicated publication workflow turns a research artifact into a scoped static-data PR.

**Tech Stack:** Python 3.11, React/TypeScript, Node test runner, GitHub Actions, existing Vite build.

**Spec:** `docs/superpowers/specs/2026-09-02-platform-publication-evidence-design.md`

## Global Constraints

- No live workspace API.
- No internal artifact metadata in public static output.
- SHA-256 verification before static writes.
- Missing publication does not break existing pages.
- Publication state is committed through a scoped PR so subsequent deployments preserve it.

---

### Task 1: Build-time public projection installer

**Files:**
- Create: `apps/dashboard/tests/test_platform_publication.py`
- Create: `apps/dashboard/src/trading_research/platform_publication.py`

- [x] Write tests for public filtering, internal fail-closed behavior, tampering, and traversal.
- [ ] Run focused test and confirm RED before implementation.
- [x] Implement validation, verification, filtered manifest generation, and staged static replacement.
- [ ] Run `uv run --locked --package trading-research-dashboard-app pytest -q apps/dashboard/tests/test_platform_publication.py`.

### Task 2: Browser evidence view

**Files:**
- Create: `apps/dashboard/web/src/platformPublication.test.mjs`
- Create: `apps/dashboard/web/src/platformPublication.ts`
- Create: `apps/dashboard/web/src/components/PlatformEvidencePanel.tsx`
- Modify: `apps/dashboard/web/src/components/StrategyResearchView.tsx`

- [x] Write parser tests for public filtering and malformed/internal artifacts.
- [x] Implement static manifest loader and fail-isolated result type.
- [x] Add evidence panel and Strategy Research tab.
- [ ] Run `pnpm --filter wu-t0-dashboard-web test`.
- [ ] Run `pnpm --filter wu-t0-dashboard-web build`.

### Task 3: Durable scoped publication

**Files:**
- Create: `tests/test_platform_publication_workflow.py`
- Create: `.github/workflows/publish-platform-publication.yml`

- [x] Write a workflow contract test requiring cross-repo artifact download, scoped static paths, PR creation, and write permissions.
- [x] Add a manual publication workflow that downloads, validates, tests, builds, commits only platform publication files, and opens a scoped PR.
- [ ] Run the root workflow test.
- [ ] Exercise one real workspace artifact publication before recording the flow as production evidence.

### Task 4: Full gates

- [ ] Run the Dashboard Python suite and ruff checks.
- [ ] Run Web unit tests and build.
- [ ] Run `apps/dashboard/scripts/validate_static_assets.py`.
- [ ] Review a generated public manifest and confirm no internal artifact id/path survived filtering.
