# Dashboard Editorial Research UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the approved editorial research visual language to the existing Dashboard without changing business data, strategy logic, or market-data contracts.

**Architecture:** Keep the existing React component hierarchy and ECharts integration. Refine CSS design tokens, flatten navigation/panels/cards, and update chart palettes so overview, intraday workspace, and strategy research share one research-terminal visual system. Any component changes are presentation-only class/wrapper changes.

**Tech Stack:** React, TypeScript, CSS, ECharts, Playwright, Vite

**Spec:** `docs/superpowers/specs/2026-08-27-dashboard-editorial-ui-design.md`

## Global Constraints

- Preserve the three existing primary views: overview, intraday workspace, strategy research.
- Do not add reference-image-specific business metrics or fabricated data.
- Preserve light/dark/system theme behavior.
- Preserve current market color semantics.
- Keep all existing chart/business data flows unchanged.
- 390px viewport must not have document-level horizontal overflow.

---

### Task 1: Add visual-structure regression assertions

**Files:**
- Modify: `apps/dashboard/web/tests/e2e/dashboard.spec.mjs`

- [ ] Add assertions for an editorial root class while retaining existing functional navigation assertions.
- [ ] Run the focused E2E test and confirm it fails before the root class exists.
- [ ] Add only the presentation marker required by the test.

### Task 2: Replace SaaS shell tokens with editorial research tokens

**Files:**
- Modify: `apps/dashboard/web/src/styles.css`
- Modify: `apps/dashboard/web/src/App.tsx` only for a root presentation class.

- [ ] Update warm-paper/dark-terminal tokens and subtle grid background.
- [ ] Flatten section navigation while preserving sticky behavior.
- [ ] Flatten overview cards/workspace panels and preserve selected/focus states.
- [ ] Run frontend unit tests.

### Task 3: Align ECharts palette

**Files:**
- Modify: `apps/dashboard/web/src/theme.ts`

- [ ] Reduce axis/grid/tooltip visual noise while preserving up/down and key-level semantics.
- [ ] Run frontend unit tests.

### Task 4: Apply the same system to strategy research

**Files:**
- Modify: `apps/dashboard/web/src/research.css`

- [ ] Flatten research cards and tab chrome.
- [ ] Preserve table scroll containers.
- [ ] Preserve textual warning/pass state cues.
- [ ] Run frontend unit tests.

### Task 5: Responsive and production verification

- [ ] Run `npm run test:e2e --prefix apps/dashboard/web`.
- [ ] Run `npm run build --prefix apps/dashboard/web`.
- [ ] Run `npm test --prefix apps/dashboard/web`.
- [ ] Open a dedicated UI PR only after fresh verification output is available.
