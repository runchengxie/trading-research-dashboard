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
- Dashboard 动态 `vwap_dev_k`、固定长度输入元组和可选 `backtrader` 的类型边界已收敛，Dashboard `ty check` 已加入 CI。
- Dashboard coverage 当前约为 61%，CI 暂以 60% 作为防回退基线。
- 已增加真实 Redis 集成测试和独立 workflow。workflow 会启动 Redis 7，验证状态单调写入、心跳、同步 collector sink 和 Pub/Sub。
- R-Breaker 六个价位的纯计算已移到 `strategies/rbreaker_math.py`，Dashboard 配置已移到 `dashboard/instrument_config.py`。
- 两个 OOS 脚本共用的 PIT 数据处理已移到 `niu_men_line_strategy.oos_support`，旧脚本入口保持兼容。
- market-data-service 测试已改用 Starlette 推荐的 `httpx2` 依赖。

## 仍需单独处理的代码问题

### 类型检查

market-data-service、Dashboard 和 Niu Men 的 `ty check` 当前通过。Dashboard 使用 `--extra backtest` 检查可选的 `backtrader` 路径，运行时仍会在依赖缺失时给出明确错误。

### 大模块

以下文件仍然体量较大，后续可以按职责拆分：

- `apps/dashboard/src/trading_research/dashboard/astock_tech.py`
- `apps/dashboard/src/trading_research/data/data_sources.py`
- `apps/dashboard/src/trading_research/strategies/rbreaker.py`
- `packages/niu-men-line-strategy/portfolio.py`
- `packages/niu-men-line-strategy/scripts/run_industry_context_oos.py`
- `packages/niu-men-line-strategy/scripts/run_portfolio_oos.py`

建议先提取纯函数和数据结构，再移动文件。不要在拆分时同时修改策略参数、数据字段或研究结果。

### 兼容入口与一次性脚本

`apps/dashboard/backtest/rbreaker.py`、Niu Men 的 snapshot wrapper、历史数据源适配器和多个 OOS 脚本可能包含迁移期兼容代码。当前不能只根据文件名删除。删除前需要搜索仓库内调用方，并检查兄弟仓库、cron、systemd、Hermes 和手动 workflow。

### 测试覆盖

- Dashboard 全量测试当前通过，coverage 报告约为 61%，R-Breaker 主模块覆盖率偏低，CI 已设置 60% 防回退阈值。后续应优先覆盖 R-Breaker 的信号、收盘平仓、止损和数据源失败路径。
- market-data-service 有 59 个单元测试，并新增真实 Redis 集成 workflow。默认测试仍不要求本地安装 Redis，集成测试通过 `REDIS_URL` 显式启用。
- Niu Men 已有 80% coverage gate。
- 前端有单元测试和生产构建，Playwright E2E 受 Actions 配额限制，需单独运行。

真实 Redis workflow 目前覆盖状态写入、心跳和 Pub/Sub。Redis 断线、provider 断线以及 WebSocket 重连仍需要在部署环境中做故障注入验证。过期心跳和连接失败已有单元测试，后续可补入真实 Redis job。

### 调用方审计结果

已检查当前仓库以及同级的 `research-workspace`、`niu-men-line-strategy` 和 `wu-t0-trading-dashboard`。当前发现的实际调用主要来自本仓库 workflow、Dashboard 前端和旧版 Dashboard 测试。`wu-t0-trading-dashboard` 仍保留旧版 `astock_tech`、`data_sources` 和 R-Breaker 副本，不能视为当前仓库的 submodule。

当前没有找到可安全删除的 wrapper 或 OOS 脚本。`cron` 调度位于旧版 Dashboard 和当前 workflow 中，当前仓库没有 systemd 配置，也没有 Hermes 配置文件。删除历史入口前仍应让外部部署方确认调用关系。

## lint 配置说明

当前代码保留中文用户界面字符串和中文注释。Ruff 的 `RUF001`、`RUF002`、`RUF003` 会把中文全角标点当作可疑字符，因此不适合直接作为中文项目的全局强制规则。`B`、`UP`、导入顺序和基础错误检查适合继续开启。

当前 CI 已覆盖：

- 根契约和 workflow 测试
- Dashboard Python 测试、Ruff、前端测试和构建
- market-data-service 测试、Ruff
- research-core 测试、Ruff
- Niu Men 测试、Ruff、ty 和 coverage
- Python 依赖审计与前端 `npm audit`

真实 provider、Redis 断线与重连、WebSocket 重连、生产 R-Breaker 发布和浏览器 E2E 仍属于独立验证任务。

### 已知测试警告

market-data-service 测试目前只剩 `websockets.legacy` 一条上游弃用警告。它来自 Alpaca SDK 的内部兼容层，项目没有直接导入。后续升级 Alpaca SDK 时，应重新评估是否能迁移到新的 websockets API。
