# M6b Legacy Repository Retirement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move each legacy repository from a verified frozen rollback mirror to an evidence-backed final state, archiving only repositories that have completed their observation and caller-audit gates.

**Architecture:** M6 owns runtime cutover and freeze actions. M6b starts only after #19 is complete, records retirement evidence independently for Dashboard and Niu Men, audits GitHub-visible and external callers, and treats GitHub Archive as a repository-setting operation outside ordinary Git PRs.

**Tech Stack:** GitHub repositories/PRs, GitHub Actions, monorepo operations documentation, repository metadata and code search.

**Spec:** `docs/superpowers/specs/2026-08-26-m6b-legacy-retirement-design.md`

## Current prepared state

- M6 design #28: merged.
- M6 shadow implementation #38: prepared; production observation not complete.
- Legacy Dashboard freeze PR: `runchengxie/wu-t0-trading-dashboard#44`, Draft.
- Legacy Niu Men freeze PR: `runchengxie/niu-men-line-strategy#22`, Draft.
- Legacy Dashboard rollback SHA: `e03617a6d6922e2b3fec66a96f1ae3b51f66c38e`.
- Legacy Niu Men rollback SHA: `1be7f725772fa824ce34e2bb833867cb4c3e9fcb`.
- #21 remains blocked by #19. Freeze PR preparation does not satisfy the observation gates below.

## Global Constraints

- Do not begin archive decisions until #19 runtime cutover is completed and closed.
- State transitions are `active -> frozen-rollback -> archive-approved -> archived`.
- Never delete repositories, tags, branches or rollback history as part of retirement.
- Dashboard archive readiness requires at least 10 consecutive trading days without legacy production writes and no rollback-triggering incident.
- Niu Men additionally requires at least three research publication cycles using monorepo Niu Men code and no ongoing requirement for the old repo to produce new artifacts.
- External cron/systemd/Hermes/self-hosted-runner dependencies cannot be proven absent by GitHub search alone.
- GitHub Archive setting is executed only after readiness approval and must be verified through repository metadata.

---

### Task 1: Verify M6 completed before starting retirement observation

**Files:**
- Read: `docs/operations/runtime-cutover.md`
- Read legacy freeze PRs #44 and #22

- [ ] **Step 1: Verify #19 is closed from real evidence**

Require five post-cutover trading-day authoritative runs, post-cutover smoke, real research publication evidence and recorded freeze merge SHAs.

- [ ] **Step 2: Verify legacy Dashboard is actually frozen**

Require merged PR #44, no `push`/`schedule` trigger, no cache push and exact acknowledgement before rollback execution.

- [ ] **Step 3: Verify legacy Niu Men is actually frozen**

Require merged PR #22, no default legacy Dashboard target and exact acknowledgement before rollback publication.

- [ ] **Step 4: Verify both repositories still report `archived=false`**

Retirement review starts from frozen rollback mirrors, not silently archived repositories.

### Task 2: Create retirement evidence record

**Files:**
- Create: `docs/operations/legacy-retirement.md`
- Modify: `docs/roadmap/README.md`

- [ ] **Step 1: Create one independent section per legacy repository**

Each section records exact values for repository, status, freeze PR/merge SHA, last-known-good SHA, cutover SHA, observation dates, caller audits, rollback evidence, final decision and archive operation metadata.

Use factual values such as `not-yet-run`, `in-progress` or a precise blocker. Do not use placeholder markers rejected by foundation checks.

- [ ] **Step 2: Link retirement status from roadmap**

Roadmap must distinguish runtime cutover from long-term repository archive decisions.

### Task 3: Audit GitHub-visible legacy Dashboard callers

**Files:**
- Modify: `docs/operations/legacy-retirement.md`

- [ ] **Step 1: Search accessible repositories for `wu-t0-trading-dashboard`**
- [ ] **Step 2: Search exact checkout/clone forms and old production URLs**
- [ ] **Step 3: Classify each hit as active runtime/development, historical documentation, migration record or explicit exemption**
- [ ] **Step 4: Open separate migration PRs for any active callers**
- [ ] **Step 5: Record `GitHub caller audit: clear` only after active callers are migrated/excepted**

### Task 4: Audit GitHub-visible legacy Niu Men callers and artifact dependency

**Files:**
- Modify: `docs/operations/legacy-retirement.md`

- [ ] **Step 1: Search accessible repositories for legacy `niu-men-line-strategy` checkout/clone/workflow references**
- [ ] **Step 2: Inspect current monorepo research artifact producer configuration**
- [ ] **Step 3: If new production artifacts still require the legacy repo, keep final decision `frozen-rollback`**
- [ ] **Step 4: If needed, migrate the producer in a separate PR and collect three monorepo-code publication cycles**

### Task 5: Complete external caller audit

**Files:**
- Modify: `docs/operations/legacy-retirement.md`
- Read: `docs/operations/runtime-cutover.md`

- [ ] **Step 1: Check cron, systemd, Hermes, self-hosted runners, local research runners, PAT automation and Cloudflare scripts**
- [ ] **Step 2: Migrate or explicitly exempt every active external caller**
- [ ] **Step 3: Record category-by-category results; do not substitute a generic “none known” statement**

### Task 6: Evaluate Dashboard archive readiness

**Files:**
- Modify: `docs/operations/legacy-retirement.md`

- [ ] **Step 1: Verify 10 consecutive trading days without legacy Dashboard production write**
- [ ] **Step 2: Verify monorepo deployment remained authoritative and no rollback trigger fired**
- [ ] **Step 3: Verify Cloudflare production path no longer checks out legacy Dashboard**
- [ ] **Step 4: Verify caller audits and rollback evidence**
- [ ] **Step 5: Set final decision to `archive-approved` or retain `frozen-rollback` with an exact reason and next review condition**

### Task 7: Evaluate Niu Men archive readiness independently

**Files:**
- Modify: `docs/operations/legacy-retirement.md`

- [ ] **Step 1: Verify at least three publication cycles identify the monorepo Niu Men commit/version used**
- [ ] **Step 2: Verify 10 trading days without production rollback**
- [ ] **Step 3: Verify legacy Niu Men is no longer required to produce new production artifacts**
- [ ] **Step 4: Verify GitHub and external caller audits**
- [ ] **Step 5: Set final decision independently of the Dashboard repository**

### Task 8: Review and merge retirement evidence

**Files:**
- `docs/operations/legacy-retirement.md`
- `docs/roadmap/README.md`

- [ ] **Step 1: Run repository tests/foundation checks**

```bash
uv run --locked --extra dev pytest -q
uv run --locked python scripts/check_foundation.py
git diff --check
```

- [ ] **Step 2: Verify documentation never claims `archived` while repository metadata remains false**
- [ ] **Step 3: Merge the evidence PR after review**

### Task 9: Execute GitHub Archive setting for approved repositories

**Repository-setting action, not a Git PR.**

- [ ] **Step 1: Archive only repositories whose evidence says `archive-approved`**
- [ ] **Step 2: Re-read repository metadata and require `archived=true`**
- [ ] **Step 3: Verify successor banner and rollback SHA remain readable**
- [ ] **Step 4: Verify monorepo Dashboard smoke and research publication still work**
- [ ] **Step 5: Record archive date/operator and status `archived` in a follow-up monorepo PR**

### Task 10: Close #21 with explicit final states

**Files:**
- Modify: `docs/roadmap/README.md`

- [ ] **Step 1: Confirm Dashboard final state is `archived` or intentionally retained `frozen-rollback`**
- [ ] **Step 2: Confirm Niu Men final state independently**
- [ ] **Step 3: Confirm rollback history was not deleted or rewritten**
- [ ] **Step 4: Record reasons/next review conditions for any repository retained frozen**
- [ ] **Step 5: Close #21 only after those final states and evidence are recorded**
