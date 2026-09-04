# Dashboard Coverage and Module Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 R-Breaker 纯指标计算独立出来，并补强配置与 provider 策略的行为测试。

**Architecture:** 新模块只依赖 NumPy，不依赖回测引擎。旧入口通过导入继续提供兼容 API。测试直接验证公开函数和 provider 重试行为。

**Tech Stack:** Python 3.11、NumPy、pytest、Ruff、ty、coverage。

**Spec:** `docs/superpowers/specs/2026-09-05-coverage-refactor-design.md`

## Global Constraints

- 不修改回测参数和研究口径。
- 不删除兼容导入路径。
- 行为变更必须有失败测试和通过测试记录。

---

### Task 1: 提取纯指标模块

**Files:** `apps/dashboard/src/trading_research/strategies/rbreaker_metrics.py`、`apps/dashboard/src/trading_research/strategies/rbreaker.py`、`apps/dashboard/tests/test_rbreaker_metrics.py`

- [x] 先写测试并确认新模块不存在时失败。
- [x] 提取 Sharpe 计算并保留旧入口导入。
- [x] 运行指标测试和 Ruff。

### Task 2: 补强边界测试

**Files:** `apps/dashboard/tests/test_instrument_config.py`、`apps/dashboard/tests/test_provider_policy.py`

- [x] 覆盖未知美股 ticker 的动态配置。
- [x] 覆盖非正 VWAP 参数拒绝。
- [x] 覆盖 provider 瞬时错误重试和退避。

### Task 3: 验证

- [x] 运行 Dashboard 全量测试、coverage、Ruff、ty 和 `git diff --check`。
