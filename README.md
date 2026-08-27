# Trading Dashboard

这是 `trading-research-dashboard` 的集成 monorepo，用于集中维护 Dashboard、共享研究契约、策略包和行情服务。

仓库根目录是统一的 uv workspace。Dashboard 的 Python distribution 名称是 `trading-research-dashboard-app`，代码导入名仍是 `trading_research`。

Dashboard 位于 `apps/dashboard/`，Niu Men 策略位于 `packages/niu-men-line-strategy/`，共享研究契约位于 `packages/research-core/`，行情服务位于 `apps/market-data-service/`。当前仓库没有 Git submodule。`research-workspace`、`market-data-platform` 和 `etf-minute-fetcher` 保留在仓库外，通过文件、API 或 artifact 契约协作。

截至 2026 年 8 月 27 日，基础设施、Dashboard、Niu Men、研究契约、美股行情、R-Breaker 发布链路、前端界面和 M6 shadow runtime 已进入 `main`。M4 还缺真实 R-Breaker 发布证据，M5 的 Redis runtime 和 readiness 代码已接入，真实 Redis 故障验证仍待运行环境完成，M6 还需要完成生产切换。详见 [路线图](docs/roadmap/README.md)。

## 当前目录

```text
trading-research-dashboard/
├── apps/
│   ├── dashboard/                 # Dashboard Python、React 前端与研究适配
│   └── market-data-service/       # 实时行情服务、provider 与 API
├── packages/
│   ├── research-core/             # canonical research / strategy snapshot contracts
│   └── niu-men-line-strategy/     # Niu Men 策略源码、测试与 producer
├── docs/
│   ├── migration/                 # 迁移状态、导入边界与回滚记录
│   ├── capabilities/              # 已实现能力与后续 roadmap
│   ├── architecture/              # 项目结构和模块边界
│   ├── operations/                # M6 cutover / runtime runbook
│   └── superpowers/               # 已批准的设计与实施计划
├── scripts/                       # 根级发布与仓库边界工具
├── tests/                         # 根级契约和 workflow 测试
├── pyproject.toml
└── uv.lock
```

## Dashboard

Dashboard 支持 A 股、港股和美股股票/ETF 行情研究、Alpaca 美股日线/1 分钟历史行情和实时 quote overlay，以及 ATR、VWAP、ORB、聚类支撑阻力、静态 Web 工作台、Niu Men 策略研究和 R-Breaker 回测/研究快照。默认标的包括宝莱特、AAPL、MSFT、NVDA 和 TSLA；实时或历史服务不可用时继续沿用已有缓存与静态 `data.json` 降级路径。

生产 Worker 当前为：

<https://trading-research-dashboard.xiaowang01.workers.dev>

具体运行、测试、前端和部署方法见 [`apps/dashboard/README.md`](apps/dashboard/README.md)。行情服务入口见 [`apps/market-data-service/README.md`](apps/market-data-service/README.md)。行情生成、PNG 图表导出和实时行情说明见 [`docs/capabilities/market-data-and-chart-export.md`](docs/capabilities/market-data-and-chart-export.md)。项目结构见 [`docs/architecture/project-structure.md`](docs/architecture/project-structure.md)。

R-Breaker snapshot generator 和输入 artifact contract 见 [`apps/dashboard/docs/backtest.md`](apps/dashboard/docs/backtest.md)。R-Breaker 生产发布使用独立 strategy target：校验后的 `trading_research.rbreaker_input.v1` artifact 先生成 `trading_research.strategy_snapshot.v1`，再通过共享 publisher 只更新 `apps/dashboard/web/public/rbreaker-research.json`。该代码链路已进入 `main`；workflow 定义存在仍不等于真实生产发布证据，首次真实 artifact run 需要单独记录。

## 验证

常用验证命令如下。命令默认从仓库根目录执行，服务和 package 的专属命令会切换到对应目录：

```bash
uv lock --check
uv run --locked --extra dev pytest -q
(cd apps/dashboard && uv run --locked --extra backtest pytest -q)
(cd apps/dashboard && uv run --locked ruff check src scripts tests)
(cd apps/market-data-service && uv run --locked pytest -q)
(cd apps/market-data-service && uv run --locked ruff check src tests)
(cd packages/niu-men-line-strategy && uv run --locked --extra dev pytest)
uv run --locked python scripts/check_foundation.py
npm ci --prefix apps/dashboard/web
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
uv run --locked --all-packages --all-extras --with pip-audit==2.10.1 pip-audit --progress-spinner off
npm audit --prefix apps/dashboard/web --audit-level=high
```

GitHub Actions 目前只允许手动触发。完整检查还包括行情服务测试、Ruff、Niu Men 类型检查、Python 依赖审计、前端构建和 `npm audit`。浏览器 E2E 需要单独安装 Chromium 后执行。

## 当前阶段

当前状态可以概括为：

1. monorepo 基础、目录治理和手动质量门槛已经建立。
2. Dashboard 与 Niu Men 已完成保留历史的导入，Python workspace 与 `research-core` 依赖已经统一。
3. `trading_research.strategy_snapshot.v1` 已作为跨策略通用 envelope。R-Breaker 已具备 artifact 校验、generic producer 和独立发布 workflow，仍缺真实 publication 证据。
4. 港股兼容、Alpaca 美股实时行情、美股历史行情和 Redis runtime 已进入 `main`。真实 Redis 集成、断线重连和故障验证仍属于 M5。
5. Dashboard 默认包含宝莱特、AAPL、MSFT、NVDA 和 TSLA，`--codes` 支持显式传入任意带市场标记的美股 ticker。
6. editorial research UI 已进入 `main`，保留现有业务数据和三段式信息架构。
7. M6 shadow workflow 已进入 `main`，scheduled mode 仍固定为 `shadow`；五个连续交易日、人工同日对比、真实 research publication、authoritative cutover 和 post-cutover observation 尚未完成。
8. legacy Dashboard/Niu Men 的 freeze PR 已准备但仍不得提前合并；archive 只有在 M6/M6b 的 observation 与 caller-audit gate 通过后才可执行。

完整阶段状态、验收标准和后续顺序见 [`docs/roadmap/README.md`](docs/roadmap/README.md)，生产切换证据见 [`docs/operations/runtime-cutover.md`](docs/operations/runtime-cutover.md)。

代码维护性、测试门槛和已知重构候选见 [`docs/maintenance/quality-audit.md`](docs/maintenance/quality-audit.md)。
