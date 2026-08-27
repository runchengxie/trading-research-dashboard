# 维护性审查记录

本文记录 2026 年 8 月 27 日对仓库文档、测试和代码结构的审查结果。它区分已经修复的问题和仍需要单独安排的重构，避免把建议误读为已完成工作。

## 仓库边界

当前仓库没有 Git submodule，也没有 gitlink。`git submodule status` 和 gitlink 检查均为空。

以下目录是同级的独立仓库，不属于当前项目的 submodule：

- `research-workspace`
- `market-data-platform`
- `etf-minute-fetcher`
- `wu-t0-trading-dashboard`
- `niu-men-line-strategy`

当前仓库只通过稳定的 Python package、文件目录、API 和 GitHub artifact 与它们协作。

## 本次已处理

- 行情服务 README 改成快速开始页，接口、运行配置和 Dashboard 接入说明移到 `apps/market-data-service/docs/`。
- 根 README 补充行情服务测试入口和当前仓库边界。
- 迁移文档、能力文档和路线图修正过期状态。
- foundation workflow 新增行情服务测试、行情服务 Ruff、Dashboard Ruff 和 research-core 测试。
- Dashboard Ruff 增加 `B` 和 `UP` 检查。
- 修复 Dashboard 循环中的闭包捕获变量问题。
- 删除不再需要的 Python UTF-8 编码声明和失效的 `noqa`。
- 修正 Niu Men 文档中指向未提交研究产物的失效链接，并明确研究产物的外部存储边界。
- Redis runtime 代码增加独立的同步 collector sink、异步 API store、Pub/Sub WebSocket 路径和 `/readyz` 基础检查。

## 仍需单独处理的代码问题

### 类型检查

market-data-service 和 Niu Men 的 `ty check` 当前通过。Dashboard 仍有既有类型问题，主要集中在：

- 动态配置的 `vwap_dev_k` 可能是字符串或浮点数。
- R-Breaker 对可选 `backtrader` 模块的导入和调用缺少可供 ty 理解的类型边界。
- R-Breaker 输入的固定长度元组推断不够精确。

这些问题不影响当前运行时测试，但适合在单独的类型收敛 PR 中处理。该 PR 应先为可选 backtest 依赖建立明确的 Protocol 或 guard，再开启 Dashboard 的 ty gate。

### 大模块

以下文件体量较大，后续可以按职责拆分：

- `apps/dashboard/src/trading_research/dashboard/astock_tech.py`
- `apps/dashboard/src/trading_research/data/data_sources.py`
- `apps/dashboard/src/trading_research/strategies/rbreaker.py`
- `packages/niu-men-line-strategy/portfolio.py`
- `packages/niu-men-line-strategy/scripts/run_industry_context_oos.py`

建议先提取纯函数和数据结构，再移动文件。不要在拆分时同时修改策略参数、数据字段或研究结果。

### 兼容入口与一次性脚本

`apps/dashboard/backtest/rbreaker.py`、Niu Men 的 snapshot wrapper、历史数据源适配器和多个 OOS 脚本可能包含迁移期兼容代码。当前不能只根据文件名删除。删除前需要搜索仓库内调用方，并检查兄弟仓库、cron、systemd、Hermes 和手动 workflow。

### 测试覆盖

- Dashboard 全量测试当前通过，但 coverage 报告约为 61%，R-Breaker 主模块覆盖率偏低，当前没有 Dashboard coverage 阈值。
- market-data-service 有 59 个单元测试，默认不连接真实 Redis，也没有真实 Redis 集成 gate。
- Niu Men 已有 80% coverage gate。
- 前端有单元测试和生产构建，Playwright E2E 受 Actions 配额限制，需单独运行。

下一步应增加隔离的 Redis integration job，覆盖连接失败、过期心跳、Pub/Sub 重连和单调写入。Dashboard 的 coverage 阈值应在补齐 backtest 和 provider fallback 测试后再设定。

## lint 配置说明

当前代码保留中文用户界面字符串和中文注释。Ruff 的 `RUF001`、`RUF002`、`RUF003` 会把中文全角标点当作可疑字符，因此不适合直接作为中文项目的全局强制规则。`B`、`UP`、导入顺序和基础错误检查适合继续开启。

当前 CI 已覆盖：

- 根契约和 workflow 测试
- Dashboard Python 测试、Ruff、前端测试和构建
- market-data-service 测试、Ruff
- research-core 测试、Ruff
- Niu Men 测试、Ruff、ty 和 coverage
- Python 依赖审计与前端 `npm audit`

Dashboard 的 ty、真实 Redis、真实 provider 和浏览器 E2E 仍属于独立验证任务。
