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

**Interfaces:**
- Consumes: existing `.section-nav`, `.instrument-overview-card`, `.workspace-panel`, `.research-section` DOM structure.
- Produces: regression assertions that require the new editorial shell classes/attributes while preserving current view navigation.

- [ ] **Step 1: Add failing E2E assertions**

Add assertions for an editorial root class and flattened research panel marker while retaining the existing functional assertions.

- [ ] **Step 2: Run targeted E2E test and confirm RED**

Run:

```bash
npm run test:e2e --prefix apps/dashboard/web -- --grep "首页加载"
```

Expected: failure because the editorial markers do not exist yet.

- [ ] **Step 3: Do not change business behavior**

Only add presentation classes/wrappers required by the test.

---

### Task 2: Replace SaaS shell tokens with editorial research tokens

**Files:**
- Modify: `apps/dashboard/web/src/styles.css`
- Modify: `apps/dashboard/web/src/App.tsx` only if a root presentation class is needed

**Interfaces:**
- Consumes: existing CSS custom properties and current component classes.
- Produces: warm-paper light theme, research-terminal dark theme, flattened containers and navigation.

- [ ] **Step 1: Update root tokens**

Use warm neutral background, low-contrast grid lines, restrained borders, smaller radii and near-zero default shadows.

- [ ] **Step 2: Flatten section navigation**

Keep sticky behavior, replace floating segmented-pill treatment with research tabs using border/underline selection.

- [ ] **Step 3: Flatten overview and workspace panels**

Remove hover lift and large shadow. Keep focus-visible affordances and current selected-state clarity.

- [ ] **Step 4: Run frontend unit tests**

```bash
npm test --prefix apps/dashboard/web
```

Expected: PASS.

---

### Task 3: Align ECharts palette with the editorial shell

**Files:**
- Modify: `apps/dashboard/web/src/theme.ts`
- Test: existing chart/theme tests under `apps/dashboard/web/src` / current test suite

**Interfaces:**
- Consumes: `paletteFor(mode)` and existing `ChartPalette` fields.
- Produces: lower-noise axes/grid/tooltips while retaining existing up/down and key-level semantics.

- [ ] **Step 1: Add or update palette expectations if existing tests cover exact colors**
- [ ] **Step 2: Run the focused test and confirm RED when values change**
- [ ] **Step 3: Update LIGHT/DARK palettes without changing the interface**
- [ ] **Step 4: Run frontend unit tests**

```bash
npm test --prefix apps/dashboard/web
```

Expected: PASS.

---

### Task 4: Apply the same system to strategy research

**Files:**
- Modify: `apps/dashboard/web/src/research.css`

**Interfaces:**
- Consumes: existing `StrategyResearchView` DOM and data model.
- Produces: compact research tables, provenance/quality panels and strategy tabs using the shared editorial hierarchy.

- [ ] **Step 1: Flatten research cards and table chrome**
- [ ] **Step 2: Preserve horizontal table scrolling inside `.research-table-wrap`**
- [ ] **Step 3: Keep warning/pass states textually distinguishable in addition to color**
- [ ] **Step 4: Run frontend unit tests**

```bash
npm test --prefix apps/dashboard/web
```

Expected: PASS.

---

### Task 5: Responsive and production verification

**Files:**
- Modify only if verification exposes a presentation regression.

- [ ] **Step 1: Run Playwright Dashboard E2E**

```bash
npm run test:e2e --prefix apps/dashboard/web
```

Expected: all Dashboard E2E tests pass, including 390px overflow protection.

- [ ] **Step 2: Run production build**

```bash
npm run build --prefix apps/dashboard/web
```

Expected: exit 0.

- [ ] **Step 3: Run full frontend unit tests once more**

```bash
npm test --prefix apps/dashboard/web
```

Expected: PASS.

- [ ] **Step 4: Commit and open a dedicated UI PR**

The PR must contain presentation changes only and must not include Redis, market-data providers, research calculation changes, or M6 cutover changes.
