# Dashboard Release Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or **superpowers:executing-plans** to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 将最新行情、contextual research 和 R-Breaker 快照通过可验证流程发布到 Dashboard，并改善分时、VWAP/ORB 和策略对比的缺失状态展示。

**Architecture:** 保留静态资产架构。authoritative workflow 生成并 enrichment `data.json`，R-Breaker workflow 生成快照，部署前统一验证。前端兼容旧快照，但区分数值、未提供和未建模状态。

**Tech Stack:** Python 3.11、uv、pytest、React 19、TypeScript、Node test、Vite、GitHub Actions、Cloudflare Workers Static Assets。

**Spec:** `docs/superpowers/specs/2026-08-30-dashboard-research-publication-and-contracts-design.md`

## Global Constraints

- 不恢复 `push`、`pull_request` 或定时自动部署。
- 不提交原始行情、完整 OOS CSV、凭据、缓存或本机绝对路径。
- contextual enrichment 失败时阻止 authoritative 发布。
- 未计算的 R-Breaker 指标保持 `null`，不填充 0。
- 保持旧版 `niu_men.research_snapshot.v2` 和旧 data snapshot 可读取。

---

### Task 1: 发布流程自动 enrichment 和严格校验

**Files:**
- Modify: `.github/workflows/dashboard-report.yml`
- Modify: `.github/workflows/deploy-dashboard.yml`
- Modify: `apps/dashboard/scripts/validate_static_assets.py`
- Test: `apps/dashboard/tests/test_static_assets.py`
- Test: `apps/dashboard/tests/test_workflow_contracts.py`

**Interfaces:**
- Consumes: `enrich_contextual_research` CLI 和生成的 `web/public/data.json`。
- Produces: authoritative candidate containing `contextualResearch`。

- [ ] **Step 1: Write failing tests.**

在 `test_static_assets.py` 增加 `require_contextual=True` 的缺失字段和正 coverage 测试；新增 `test_workflow_contracts.py`，检查 enrichment 位于 `astock_tech` 之后、静态校验之前，并确认没有 `push:` 或 `pull_request:` trigger。

- [ ] **Step 2: Verify RED.**

~~~bash
uv run --locked --package trading-research-dashboard-app pytest -q apps/dashboard/tests/test_static_assets.py apps/dashboard/tests/test_workflow_contracts.py
~~~

Expected: strict validation API 和 workflow contract 尚不存在。

- [ ] **Step 3: Implement minimal validation and workflow steps.**

让 `validate_snapshots(data_path=DATA_PATH, research_path=RESEARCH_PATH, *, require_contextual=False)` 在 strict mode 检查 `data.contextualResearch.coverage.evaluated > 0`，并给脚本增加 `--require-contextual` CLI 参数。在 `dashboard-report.yml` 的候选数据生成后运行：

~~~bash
uv run --locked --package trading-research-dashboard-app python -m trading_research.scripts.enrich_contextual_research --input apps/dashboard/web/public/data.json
~~~

authoritative runtime 负责调用行情生成器并执行 enrichment 后发布最新候选；`deploy-dashboard.yml` 只对当前候选执行 enrichment/校验和 Worker 部署，不自行拉取另一份行情。authoritative 使用 strict validation，shadow 保持兼容验证；不添加自动 push/PR 部署。

- [ ] **Step 4: Verify GREEN.**

~~~bash
uv run --locked --package trading-research-dashboard-app pytest -q apps/dashboard/tests/test_static_assets.py apps/dashboard/tests/test_workflow_contracts.py apps/dashboard/tests/test_enrich_contextual_research.py
uv run --locked --package trading-research-dashboard-app python apps/dashboard/scripts/validate_static_assets.py
~~~

- [ ] **Step 5: Commit.**

~~~bash
git add .github/workflows/dashboard-report.yml .github/workflows/deploy-dashboard.yml apps/dashboard/scripts/validate_static_assets.py apps/dashboard/tests/test_static_assets.py apps/dashboard/tests/test_workflow_contracts.py
git commit -m "feat: publish contextual research with dashboard candidates"
~~~

### Task 2: 明确主要指标和缺失状态

**Files:**
- Modify: `apps/dashboard/web/src/components/SelectedInstrumentWorkspace.tsx`
- Modify: `apps/dashboard/web/src/components/StrategyComparisonPanel.tsx`
- Modify: `apps/dashboard/web/src/components/ResearchPanel.tsx`
- Modify: `apps/dashboard/web/src/research/strategySnapshot.ts`
- Modify: `apps/dashboard/web/src/research/genericSnapshot.ts`
- Create: `apps/dashboard/web/src/research/comparisonLabels.ts`
- Test: `apps/dashboard/web/src/contextualResearchPanel.test.mjs`
- Test: `apps/dashboard/web/src/genericSnapshot.test.mjs`
- Test: `apps/dashboard/web/src/strategyComparison.test.mjs`

**Interfaces:**
- Consumes: `StockData.indicators`、`ContextualResearchSnapshot`、`StrategySnapshot`。
- Produces: primary VWAP/ORB readings and explicit availability labels。

- [ ] **Step 1: Write failing frontend tests.**

测试数值、`未提供`、`无共同变体` 三种 cell 状态，并增加含有 `vwap`、`orbHigh`、`orbLow` 的 workspace fixture。

- [ ] **Step 2: Verify RED.**

~~~bash
npm test --prefix apps/dashboard/web
~~~

- [ ] **Step 3: Implement presentation.**

在主要模型读数区增加 VWAP、ORB 上轨、ORB 下轨；保留高级指标表。无 contextual snapshot 时显示 `上下文研究尚未随数据发布`。将 `StrategyComparisonPanel` 的纯格式化 helper 放在新文件 `apps/dashboard/web/src/research/comparisonLabels.ts`，测试直接导入该 helper；策略对比保持 variant ID 对齐，但对跨策略行显示 `无共同变体`，对同一 variant 的 null 指标显示 `未提供`。

- [ ] **Step 4: Add execution capability metadata.**

扩展 normalized variant 的 `executionCapabilities`：`blockedEntry` 和 `blockedExitDay` 取 `observed | not_modelled`。旧快照默认 `not_modelled`，研究表显示 `未建模`。

- [ ] **Step 5: Verify and commit.**

~~~bash
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
git add apps/dashboard/web/src/components/SelectedInstrumentWorkspace.tsx apps/dashboard/web/src/components/StrategyComparisonPanel.tsx apps/dashboard/web/src/components/ResearchPanel.tsx apps/dashboard/web/src/research/strategySnapshot.ts apps/dashboard/web/src/research/genericSnapshot.ts apps/dashboard/web/src/contextualResearchPanel.test.mjs apps/dashboard/web/src/genericSnapshot.test.mjs apps/dashboard/web/src/strategyComparison.test.mjs
git commit -m "feat: clarify dashboard research metric availability"
~~~

### Task 3: 安全发布当前 R-Breaker 快照

**Files:**
- Modify: `apps/dashboard/src/trading_research/scripts/generate_rbreaker_snapshot.py`
- Modify: `apps/dashboard/tests/test_generate_rbreaker_snapshot.py`
- Modify: `.github/workflows/deploy-dashboard.yml`

**Interfaces:**
- Consumes: validated `rbreaker_input.v1` artifact。
- Produces: real artifact dates, available Sharpe, and explicit unmodeled limit capabilities。

- [ ] **Step 1: Write failing generator tests.**

断言 summary 日期等于 artifact 日期，fake `sharpe=-1.2` 同时进入 summary 和 variant，并断言 `executionCapabilities` 两项均为 `not_modelled`。

- [ ] **Step 2: Verify RED.**

~~~bash
uv run --locked --package trading-research-dashboard-app --extra backtest pytest -q apps/dashboard/tests/test_generate_rbreaker_snapshot.py
~~~

- [ ] **Step 3: Implement.**

保留真实日期和 Sharpe，缺失 profit factor 继续为 `null`，不把缺失 Sharpe 转为 0，并在 `rb_default` 写入 capability map。

- [ ] **Step 4: Verify and commit.**

~~~bash
uv run --locked --package trading-research-dashboard-app --extra backtest pytest -q apps/dashboard/tests/test_generate_rbreaker_snapshot.py apps/dashboard/tests/test_static_assets.py
git add apps/dashboard/src/trading_research/scripts/generate_rbreaker_snapshot.py apps/dashboard/tests/test_generate_rbreaker_snapshot.py .github/workflows/deploy-dashboard.yml
git commit -m "fix: publish explicit R-Breaker snapshot capabilities"
~~~

### Task 4: 文档、全量验证和 PR 1

**Files:**
- Modify: `apps/dashboard/docs/contextual-research.md`
- Modify: `apps/dashboard/docs/cloudflare-workers.md`
- Modify: `apps/dashboard/README.md`

- [ ] **Step 1: Document authoritative release.**

记录行情生成、enrichment、strict validation、R-Breaker 生成、前端 build、Worker deploy 和 post-deploy check；明确 scheduled report 仍为 shadow。

- [ ] **Step 2: Run full verification.**

~~~bash
uv run --locked --package trading-research-dashboard-app pytest -q
uv run --locked ruff check apps/dashboard/src apps/dashboard/scripts apps/dashboard/tests
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
python apps/dashboard/scripts/validate_static_assets.py
git diff --check
~~~

- [ ] **Step 3: Inspect artifacts and open PR.**

~~~bash
git status --short
git diff --stat origin/main...HEAD
git push -u origin feat/dashboard-release-contract
gh pr create --base main --head feat/dashboard-release-contract --title "feat: close dashboard research publication loop" --body-file docs/superpowers/specs/2026-08-30-dashboard-research-publication-and-contracts-design.md
~~~

- [ ] **Step 4: Verify online only after authoritative run.**

合并后手动运行 authoritative workflow，重新读取线上 `data.json` 和 `rbreaker-research.json`，核对宝莱特 intraday、contextual coverage、R-Breaker walkForward、日期和 Sharpe。

## PR 2 Boundary

PR 2 在 PR 1 合并并完成线上验证后单独制定计划，覆盖 `research.json` 生产方、真正的 R-Breaker rolling OOS、fold 日期聚合和实际涨跌停执行模拟。PR 1 不把单样本 R-Breaker 标成 rolling research。
