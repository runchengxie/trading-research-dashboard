# A 股 Agent 纸面组合 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Agent 纸面组合实验切换为 Tushare 驱动的 A 股日线组合，并实现整数手、费用和涨跌停约束。

**Architecture:** 保留现有快照和模型决策接口，替换价格获取模块并在模拟器边界增加 A 股规则配置。工作流通过环境变量注入 Tushare 和 OpenRouter 配置，Dashboard 继续消费相同快照格式。

**Tech Stack:** Python、pandas、Tushare、pytest、uv、GitHub Actions、React/Vite、Cloudflare Workers。

**Spec:** `docs/superpowers/specs/2026-09-01-a-share-agent-portfolio-design.md`

## Global Constraints

- 只做纸面交易，不连接券商，不发送真实订单。
- 默认决策频率为每个工作日一次。
- 默认模型为 `openrouter/free`，没有 OpenRouter Key 时回退智谱。
- A 股交易标的按 100 股整数手计算。
- 本地密钥只放在 `.env`，不写入仓库。

---

### Task 1: A 股价格输入

**Files:**
- Modify: `apps/dashboard/src/trading_research/scripts/prepare_agent_prices.py`
- Test: `apps/dashboard/tests/test_prepare_agent_prices.py`
- Modify: `.env.example`

- [ ] **Step 1: Write failing tests** for A 股 defaults and Tushare payload conversion.
- [ ] **Step 2: Run the focused tests and confirm they fail because the current implementation uses yfinance and US symbols.**
- [ ] **Step 3: Implement Tushare daily price loading with token and proxy environment resolution.**
- [ ] **Step 4: Run the focused tests and confirm they pass.**

### Task 2: A 股模拟成交规则

**Files:**
- Modify: `apps/dashboard/src/trading_research/agent_portfolio.py`
- Test: `apps/dashboard/tests/test_agent_portfolio.py`

- [ ] **Step 1: Write failing tests** for 100-share lots, stock stamp duty, ETF fee exemption, limit-up buys and limit-down sells.
- [ ] **Step 2: Run the focused tests and confirm they fail with the current fractional-share and single-fee behavior.**
- [ ] **Step 3: Add explicit market rule parameters while preserving existing callers.**
- [ ] **Step 4: Run the focused tests and confirm they pass.**

### Task 3: Agent workflow and model context

**Files:**
- Modify: `apps/dashboard/src/trading_research/scripts/generate_agent_portfolio.py`
- Modify: `.github/workflows/agent-paper-portfolio.yml`
- Test: `scripts/test_agent_paper_workflow.py`
- Test: `apps/dashboard/tests/test_generate_agent_portfolio.py`

- [ ] **Step 1: Write failing tests** for A 股 defaults and Tushare environment wiring.
- [ ] **Step 2: Run the focused tests and confirm they fail with US defaults.**
- [ ] **Step 3: Wire the new price payload and A 股 simulator rules into the workflow.**
- [ ] **Step 4: Run the focused tests and confirm they pass.**

### Task 4: Documentation and full verification

**Files:**
- Modify: `docs/agent-paper-portfolio.md`
- Modify: `README.md`
- Modify: `.env.example`

- [ ] **Step 1: Update local and GitHub configuration examples.**
- [ ] **Step 2: Document A 股 assumptions, limitations and paper-only boundary.**
- [ ] **Step 3: Run the complete relevant pytest, ruff, type and frontend checks.**
- [ ] **Step 4: Commit the implementation and push it to the feature branch.**
