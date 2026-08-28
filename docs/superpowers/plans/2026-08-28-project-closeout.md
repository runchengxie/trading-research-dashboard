# Trading Research Dashboard Project Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收口 trading-research-dashboard 的开发层工作，改善深色图表视觉，支持同一页面切换 A/HK/US 标的，并提供不携带凭据的朋友分享包，同时把 M5/M6/M6b 的真实环境门槛记录清楚。

**Architecture:** 前端从已加载的 `DashboardData.stocks` 中按市场筛选，使用单页面市场切换，不新增第二套 Dashboard。分享包由根级 Python 脚本复制受控源码、静态数据和 `.env.example`，明确排除 `.env`、缓存、密钥和构建产物；yfinance 继续作为无 Alpaca key 时的 US 历史数据 provider。

**Tech Stack:** React/TypeScript、ECharts、Node test runner、Python 3.11、pytest、uv、shell/Python packaging。

**Spec:** 本计划承接 `docs/roadmap/README.md`、`docs/operations/runtime-cutover.md` 和现有 yfinance provider 设计。

## Global Constraints

- 分享包默认不得包含真实 API key、`.env`、原始行情缓存或本机绝对路径。
- US 数据必须通过 `AAPL.US` 等显式市场代码进入生成链路；前端没有 US 数据时显示可操作提示，不伪造行情。
- M5 Redis/provider 故障演练、M6 生产切换和 M6b archive 只有真实外部证据后才能标记完成。
- 兼容旧数据快照，`market` 缺失时按 CN 处理。

---

### Task 1: Add failing tests for visual, market switch and package safety

**Files:**
- Modify: `apps/dashboard/web/src/chartVisuals.test.mjs`
- Modify: `apps/dashboard/web/src/editorialTokens.test.mjs`
- Create: `scripts/package_share.test.py`

- [ ] Add assertions for subdued dark grid tokens, chart surface, market switch labels/filters, and package exclusion rules.
- [ ] Run the targeted tests and confirm they fail for the missing behavior.

### Task 2: Implement UI closeout

**Files:**
- Modify: `apps/dashboard/web/src/App.tsx`
- Modify: `apps/dashboard/web/src/editorial.css`
- Modify: `apps/dashboard/web/src/theme.ts`
- Modify: `apps/dashboard/web/src/components/StockChart.tsx`
- Modify: `apps/dashboard/web/src/components/IntradayChart.tsx`

- [ ] Add a single-page market switch with CN/HK/US counts and empty-state guidance.
- [ ] Reduce dark page grid contrast, add a distinct chart surface, and make minor chart lines dashed/subtle.
- [ ] Keep the selected instrument valid when switching markets.
- [ ] Run web unit tests and build.

### Task 3: Implement credential-safe share packaging

**Files:**
- Create: `scripts/package_share.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `docs/getting-started.md`

- [ ] Add `uv run python scripts/package_share.py --output ...` with deterministic allowlisted files/directories.
- [ ] Reject output paths inside the repository and refuse to copy secret-like files.
- [ ] Include `.env.example`, source, docs, frontend package metadata and reviewed static data; exclude `.env`, caches, node_modules, dist and raw artifacts.
- [ ] Add a manifest with file list and SHA-256 hashes, but no credentials.

### Task 4: Merge yfinance and update maintenance status

**Files:**
- Modify: `docs/roadmap/README.md`
- Modify: `docs/operations/runtime-cutover.md`
- Create: `docs/operations/legacy-retirement.md`
- Modify: legacy sibling READMEs only if their maintenance notice is missing.

- [ ] Merge the existing yfinance implementation into this closeout branch without overwriting unrelated work.
- [ ] Record M5/M6/M6b as code-complete or externally pending with exact evidence requirements.
- [ ] Record both old repositories as unified-maintenance/frozen-candidate, without claiming GitHub archive.

### Task 5: Verify and commit

- [ ] Run frontend tests/build, Python tests, package tests, foundation checks, Ruff and `git diff --check`.
- [ ] Inspect the generated share archive contents and ensure no secret-like files are present.
- [ ] Commit the closeout changes with a focused message.
