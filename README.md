# Trading Dashboard

这是 `trading-research-dashboard` 的集成 monorepo，用于集中维护 Dashboard、共享契约、策略包和行情服务。

本地 checkout 的推荐目录名也是 `trading-research-dashboard`。根 workspace 使用同名项目；Dashboard Python distribution 使用 `trading-research-dashboard-app`，其稳定 import 包名仍为 `trading_research`。

当前 Dashboard 已完整导入 `apps/dashboard/`，其 Python 代码、React 前端、测试和 Cloudflare Workers 部署配置都在本仓库维护。Niu Men 策略源码和共享研究契约也已进入对应 package；实时行情服务和完整平台迁移仍在进行中。

当前仓库没有使用 Git submodule。`research-workspace`、`market-data-platform` 和 `etf-minute-fetcher` 继续作为仓库外基础设施，通过稳定的数据或文件契约与本项目协作。

截至 2026 年 8 月 27 日，monorepo 基础、Dashboard/Niu Men 导入、共享 `research-core`、R-Breaker 快照生成和 M5 实时行情服务核心已合并到 `main`；港美股扩展和 M6 shadow runtime 仍在 Draft PR 中。

## 当前目录

```text
trading-research-dashboard/
├── apps/
│   └── dashboard/                 # Dashboard 应用、测试与前端
├── packages/
│   ├── research-core/             # 共享契约的目标位置，尚未进入 M2 抽取
│   └── niu-men-line-strategy/     # Niu Men 策略源码、测试与契约（M1 已导入）
├── docs/
│   ├── migration/                 # 迁移状态、导入边界与回滚记录
│   ├── capabilities/              # 已实现能力与后续 roadmap
│   ├── architecture/              # 项目结构和模块边界
│   └── superpowers/               # 已批准的设计与实施计划
├── scripts/                       # 根级仓库边界检查
├── tests/                         # 根级仓库测试
├── pyproject.toml
└── uv.lock
```

## Dashboard

Dashboard 位于 `apps/dashboard/`，支持 A 股股票与 ETF 行情研究、ATR、VWAP、ORB、聚类支撑阻力、Excel 输出、静态 Web 工作台和 R-Breaker 回测。

生产 Worker 当前为：

<https://trading-research-dashboard.xiaowang01.workers.dev>

具体运行、测试、前端和部署方法见 [`apps/dashboard/README.md`](apps/dashboard/README.md)。

行情生成、PNG 图表导出和实时行情 roadmap 见 [`docs/capabilities/market-data-and-chart-export.md`](docs/capabilities/market-data-and-chart-export.md)。项目结构和后续 package 化方向见 [`docs/architecture/project-structure.md`](docs/architecture/project-structure.md)。

R-Breaker 快照可由研究 artifact 在构建阶段生成，具体输入契约和命令见 [`apps/dashboard/docs/backtest.md`](apps/dashboard/docs/backtest.md)。
手动部署时可在 `Deploy Dashboard` workflow 中提供 `research_run_id`，让构建任务使用锁定的 `backtrader` 生成最新静态策略快照。

## 验证

根级 GitHub Actions 当前只允许手动触发。仓库自 M3 起是统一 uv workspace，根 `uv.lock` 是唯一锁文件；成员测试在各自目录执行，共享同一解析环境：

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

手动 CI 还会执行与上述命令相同的 Ruff、Python 依赖审计和 `npm audit`。浏览器 E2E 测试不会在默认 workflow 中运行，需要时在具备 Chromium 的环境单独执行。

## 迁移状态

当前阶段可以概括为：

1. 根级 monorepo 基础和治理规则已经建立。
2. Dashboard 已完成保留历史的导入，并可从本仓库构建和部署。
3. Niu Men 已完成保留历史的首批导入，策略源码、测试和契约资产由本仓库维护；runtime cutover 前旧仓库仍可独立运行。
4. `research-core` 的共享 schema、fixture 和 provenance 规则尚未抽取。
5. R-Breaker 与 Dashboard 数据层仍有后续重构空间，本阶段优先保持行为稳定。

当前仍未完成的主要工作包括 `research-core` 实现、统一 Python workspace、实时行情服务、跨仓库快照自动发布和旧仓库运行时切换。旧 Dashboard 与 Niu Men 仓库暂不停止维护。

完整的阶段状态、验收标准和后续顺序见 [`docs/roadmap/README.md`](docs/roadmap/README.md)。

迁移细节见 [`docs/migration/README.md`](docs/migration/README.md)，Dashboard 首次导入边界见 [`docs/migration/dashboard-import.md`](docs/migration/dashboard-import.md)，源仓库回滚点见 [`docs/migration/source-commits.md`](docs/migration/source-commits.md)。
