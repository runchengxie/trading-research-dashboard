# Code quality refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提高 R-Breaker 的可测试性，拆分共享职责，并消除项目可以自行控制的测试弃用警告。

**Architecture:** 保留现有命令行入口和兼容导入。把纯计算和 OOS 共享数据处理移到无副作用模块，把外部 SDK 的动态调用限制在明确边界。大文件按职责逐步拆分，每次重构都运行原有测试。

**Tech Stack:** Python 3.11+、pandas、pytest、Ruff、uv、FastAPI、Starlette、httpx2、Backtrader。

**Spec:** `docs/maintenance/quality-audit.md`

## Global Constraints

- 保留现有 CLI、workflow 和历史兼容入口。
- 不删除未完成调用方审计的 wrapper、OOS 脚本或数据源适配器。
- 每次模块移动都必须先有行为测试，再运行受影响模块和全量测试。
- 不通过忽略规则或 warning filter 隐藏项目自身问题。

### Task 1: R-Breaker pure logic

**Files:**
- Create: `apps/dashboard/src/trading_research/strategies/rbreaker_math.py`
- Modify: `apps/dashboard/src/trading_research/strategies/rbreaker.py`
- Test: `apps/dashboard/tests/test_rbreaker_strategy.py`

- [x] 把六个价位计算提取为纯函数。
- [x] 让策略类调用纯函数并保留原有无效区间行为。
- [x] 验证纯函数和策略测试。

### Task 2: OOS shared helpers

**Files:**
- Create: `packages/niu-men-line-strategy/src/niu_men_line_strategy/oos_support.py`
- Modify: `packages/niu-men-line-strategy/scripts/run_industry_context_oos.py`
- Modify: `packages/niu-men-line-strategy/scripts/run_portfolio_oos.py`
- Test: `packages/niu-men-line-strategy/tests/test_oos_support.py`

- [x] 提取日期、研究提交、PIT 资格、行业归属和上下文拼接工具。
- [x] 保留旧脚本中的兼容别名，确保既有测试和入口不变。
- [x] 验证两个 OOS 脚本及共享工具。

### Task 3: Dashboard instrument configuration

**Files:**
- Create: `apps/dashboard/src/trading_research/dashboard/instrument_config.py`
- Modify: `apps/dashboard/src/trading_research/dashboard/astock_tech.py`
- Test: `apps/dashboard/tests/test_default_instrument.py`

- [x] 移动默认证券配置、动态 US ticker 解析和 VWAP 参数校验。
- [x] 在旧模块保留公开兼容名称。
- [x] 验证配置和 Dashboard 相关测试。

### Task 4: Dependency warning cleanup

**Files:**
- Modify: `apps/market-data-service/pyproject.toml`
- Modify: `uv.lock`
- Test: `apps/market-data-service/tests/`

- [x] 使用 Starlette 推荐的 `httpx2` 测试客户端依赖。
- [x] 保留并记录 Alpaca SDK 引发的 `websockets.legacy` 上游警告。
- [x] 验证测试、Ruff 和锁文件一致性。

### Task 5: Full verification

- [ ] 运行根测试、Dashboard 测试、行情服务测试和 Niu Men 测试。
- [ ] 运行各包 Ruff、ty、foundation check 和 `git diff --check`。
- [ ] 更新维护审计记录，说明剩余未拆分模块和线上验证项。
