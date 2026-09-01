# Trading Research Dashboard

> 本仓库已停止公开维护，仅用于历史归档和内部回滚。
>
> 当前维护版本已迁移到新的公开仓库：[trading-research-dashboard](https://github.com/runchengxie/trading-research-dashboard)

这是一个用于研究和展示交易策略的项目，包含行情数据、策略回测、研究快照和 Web 看板。

## 项目维护状态

本仓库是统一维护主线，已整合 `wu-t0-trading-dashboard` 和
`niu-men-line-strategy` 的 Dashboard、策略研究与共享契约代码。后续功能开发、问题修复、发布和运行维护均以本仓库为准；两个旧仓库保留用于历史追溯和回滚，不再作为独立功能开发主线。

## 从哪里开始

- [新人上手](docs/getting-started.md)
- [项目结构](docs/architecture/project-structure.md)
- [当前路线图](docs/roadmap/README.md)
- [生产切换手册](docs/operations/runtime-cutover.md)
- [Agent 纸面组合实验](docs/agent-paper-portfolio.md)

## 项目包含什么

```text
apps/dashboard/                 数据处理、策略研究和 Web 看板
apps/market-data-service/       美股实时与历史行情服务
packages/research-core/         研究快照和 JSON Schema
packages/niu-men-line-strategy/ Niu Men 策略与研究工具
docs/                           架构、配置、部署和维护文档
tests/                          根目录契约和 workflow 测试
apps/dashboard/web/public/agent/ Agent 纸面组合快照
```

当前看板支持 A 股、港股和美股股票/ETF。生成器默认配置包括 AAPL、MSFT、NVDA 和 TSLA，仓库内的可直接运行 demo 快照目前包含宝莱特和 TSLA。R-Breaker 研究结果可在看板的策略研究区域查看。

线上地址：<https://trading-research-dashboard.xiaowang01.workers.dev>

## 快速开始

需要 Python 3.11 或更高版本、`uv`、Node.js 22 和 `pnpm` 11：

```bash
uv sync
(cd apps/dashboard && uv run --extra backtest pytest -q)
pnpm install
pnpm --filter wu-t0-dashboard-web test
pnpm --filter wu-t0-dashboard-web build
```

仓库内的 `apps/dashboard/web/public/data.json` 是可直接部署的静态 demo 快照，当前包含宝莱特和 TSLA。快照可以滞后于最新交易日，适合演示页面功能。需要重新生成时，在 `apps/dashboard` 目录执行：

```bash
MARKET_DATA_SERVICE_URL=http://127.0.0.1:8000 \
  uv run python -m trading_research.dashboard.astock_tech \
  --codes sz300246,TSLA.US --json web/public/data.json
```

Dashboard 还提供一个 `Agent 组合` 页面，用于查看 `GLM-4.7-Flash` 纸面投资实验的净值、持仓、决策和成交记录。实验通过 GitHub Actions 每个工作日运行一次，配置方法和边界见 [Agent 纸面组合实验](docs/agent-paper-portfolio.md)。它不连接券商，也不发送真实订单。

行情服务使用 FastAPI，并为 health、ready、quote 和 bars REST endpoint 提供命名的 Pydantic response models。FastAPI 会据此生成 OpenAPI schema。需要给前端 codegen 或其他工具使用时：

```bash
cd apps/market-data-service
uv run --locked python scripts/export_openapi.py /tmp/market-data-openapi.json
```

Web Dashboard 继续优先使用静态快照；配置 `VITE_MARKET_DATA_URL` 后，会额外检查行情服务 health 并连接现有 WebSocket。行情服务不可用时页面继续保留静态降级模式。

生成一份用于私下分享的安全源码包（包含完整项目源码、workflow、Dashboard 静态快照和 `SHARE-MANIFEST.json`，默认不包含 `.env`、真实 key、原始缓存或构建产物）：

```bash
uv run python scripts/package_share.py --output /tmp/trading-research-dashboard-share.zip
```

分享包不包含外部 `market-data-platform` 和 `etf-minute-fetcher` 的原始数据；`SHARE-MANIFEST.json` 会记录这两个外部数据源、对应环境变量和未打包状态。接收方可以直接使用包内的静态 `data.json` 和研究快照运行 Dashboard；如需重新抓取行情，再按文档配置外部数据目录或 yfinance/Alpaca provider。

如需在同一页面查看美股，请生成包含显式美股 ticker 的快照，例如
`--codes sz300246,AAPL.US,MSFT.US,NVDA.US,TSLA.US`。没有美股快照时，页面的“美股”筛选会保留为空态提示，不会伪造行情。

## 重要边界

`research-workspace`、`market-data-platform` 和 `etf-minute-fetcher` 是仓库外的独立项目，当前仓库没有 Git submodule。原始行情、凭据和大型回测产物不提交到本仓库。

## 当前状态

- M0 至 M4：已完成，包含一次真实 R-Breaker Tushare 快照发布
- M5：代码和 yfinance 历史回退已完成；真实 Redis、provider 和部署环境故障验证仍待执行
- M6：shadow runtime 和安全检查已完成；生产切换、连续运行观察仍待真实运行证据
- M6b：两个旧仓库已声明统一维护主线；freeze、调用方审计和 archive 仍是外部运维事项

详细状态以 [`docs/roadmap/README.md`](docs/roadmap/README.md) 为准。

本项目用于策略研究和工程验证。历史数据和回测结果不代表未来收益，使用者需要自行评估交易风险。
