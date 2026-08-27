# Trading Dashboard

这是 `trading-research-dashboard` 的集成 monorepo，用于集中维护 Dashboard、共享研究契约、策略包和行情服务。

本地 checkout 的推荐目录名也是 `trading-research-dashboard`。根 workspace 使用同名项目；Dashboard Python distribution 使用 `trading-research-dashboard-app`，其稳定 import 包名仍为 `trading_research`。

Dashboard 位于 `apps/dashboard/`，Niu Men 策略位于 `packages/niu-men-line-strategy/`，共享研究契约位于 `packages/research-core/`，实时行情服务位于 `apps/market-data-service/`。当前仓库不使用 Git submodule；`research-workspace`、`market-data-platform` 和 `etf-minute-fetcher` 继续作为仓库外基础设施，通过稳定的 artifact/API 契约与本项目协作。

截至 2026 年 8 月 27 日，monorepo 基础、Dashboard/Niu Men 导入、共享 `research-core`、generic strategy snapshot、港股兼容层、Alpaca 美股实时行情以及 M6 shadow runtime 已合并到 `main`。M5 仍缺 Redis state/PubSub 与美股历史行情；M6 仍缺真实连续交易日 shadow 证据、生产切换和 legacy freeze/retirement 证据。R-Breaker 已具备 generic snapshot generator，本仓库正在补齐从校验后的研究 artifact 到独立 `rbreaker-research.json` 发布 PR 的生产链路。

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

Dashboard 支持 A 股股票与 ETF 行情研究、港股兼容行情、ATR、VWAP、ORB、聚类支撑阻力、静态 Web 工作台、Niu Men 策略研究以及 R-Breaker 回测/研究快照。美股可通过 `market-data-service` 的 Alpaca 实时 overlay 更新当前价格；实时服务不可用时仍使用已部署的静态 `data.json`。

生产 Worker 当前为：

<https://trading-research-dashboard.xiaowang01.workers.dev>

具体运行、测试、前端和部署方法见 [`apps/dashboard/README.md`](apps/dashboard/README.md)。行情生成、PNG 图表导出和实时行情说明见 [`docs/capabilities/market-data-and-chart-export.md`](docs/capabilities/market-data-and-chart-export.md)。项目结构见 [`docs/architecture/project-structure.md`](docs/architecture/project-structure.md)。

R-Breaker snapshot generator 和输入 artifact contract 见 [`apps/dashboard/docs/backtest.md`](apps/dashboard/docs/backtest.md)。R-Breaker 生产发布使用独立 strategy target：校验后的 `trading_research.rbreaker_input.v1` artifact 先生成 `trading_research.strategy_snapshot.v1`，再通过共享 publisher 只更新 `apps/dashboard/web/public/rbreaker-research.json`。workflow 定义存在并不等于真实生产发布证据，首次真实 artifact run 仍需单独记录。

## 验证

根级 GitHub Actions 当前只允许手动触发。仓库是统一 uv workspace，根 `uv.lock` 是唯一锁文件；成员测试共享同一解析环境：

```bash
uv lock --check
uv run --locked --extra dev pytest -q
(cd apps/dashboard && uv run --locked pytest -q)
(cd packages/niu-men-line-strategy && uv run --locked --extra dev pytest)
uv run --locked python scripts/check_foundation.py
npm ci --prefix apps/dashboard/web
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
uv run --locked --all-packages --all-extras --with pip-audit==2.10.1 pip-audit --progress-spinner off
npm audit --prefix apps/dashboard/web --audit-level=high
```

手动 CI 还会执行 Ruff、Python 依赖审计和 `npm audit`。浏览器 E2E 测试不会在默认 workflow 中运行，需要时在具备 Chromium 的环境单独执行。

## 当前阶段

当前状态可以概括为：

1. monorepo 基础、目录治理和手动质量门槛已经建立。
2. Dashboard 与 Niu Men 已完成保留历史的导入，Python workspace 与 `research-core` 依赖已经统一。
3. `trading_research.strategy_snapshot.v1` 已作为跨策略通用 envelope，Niu Men 保持旧 wire contract 兼容，R-Breaker 已有 generic producer/adapter。
4. 港股历史/分钟兼容和 Alpaca 美股实时 overlay 已合并；Redis state/PubSub 与美股历史 bars 仍属于 M5 未完成项。
5. M6 shadow workflow 已进入 `main`，scheduled mode 仍固定为 `shadow`；五个连续交易日、人工同日对比、真实 research publication、authoritative cutover 和 post-cutover observation 尚未完成。
6. legacy Dashboard/Niu Men 的 freeze PR 已准备但仍不得提前合并；archive 只有在 M6/M6b 的 observation 与 caller-audit gate 通过后才可执行。

完整阶段状态、验收标准和后续顺序见 [`docs/roadmap/README.md`](docs/roadmap/README.md)，生产切换证据见 [`docs/operations/runtime-cutover.md`](docs/operations/runtime-cutover.md)。
