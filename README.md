# Trading Research Dashboard

这是一个用于研究和展示交易策略的项目，包含行情数据、策略回测、研究快照和 Web 看板。

## 从哪里开始

- [新人上手](docs/getting-started.md)
- [项目结构](docs/architecture/project-structure.md)
- [当前路线图](docs/roadmap/README.md)
- [生产切换手册](docs/operations/runtime-cutover.md)

## 项目包含什么

```text
apps/dashboard/                 数据处理、策略研究和 Web 看板
apps/market-data-service/       美股实时与历史行情服务
packages/research-core/         研究快照和 JSON Schema
packages/niu-men-line-strategy/ Niu Men 策略与研究工具
docs/                           架构、配置、部署和维护文档
tests/                          根目录契约和 workflow 测试
```

当前看板支持 A 股、港股和美股股票/ETF。默认美股标的是 AAPL、MSFT、NVDA 和 TSLA。R-Breaker 研究结果可在看板的策略研究区域查看。

线上地址：<https://trading-research-dashboard.xiaowang01.workers.dev>

## 快速开始

需要 Python 3.11 或更高版本、`uv`、Node.js 和 npm：

```bash
uv sync
(cd apps/dashboard && uv run --extra backtest pytest -q)
npm ci --prefix apps/dashboard/web
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
```

## 重要边界

`research-workspace`、`market-data-platform` 和 `etf-minute-fetcher` 是仓库外的独立项目，当前仓库没有 Git submodule。原始行情、凭据和大型回测产物不提交到本仓库。

## 当前状态

- M0 至 M4：已完成，包含一次真实 R-Breaker Tushare 快照发布
- M5：核心代码已完成，真实 Redis、provider 和部署环境故障验证仍待执行
- M6：shadow runtime 已完成，生产切换和连续运行观察仍待执行
- M6b：旧仓库 freeze、调用方审计和 archive 等待 M6 完成

详细状态以 [`docs/roadmap/README.md`](docs/roadmap/README.md) 为准。

本项目用于策略研究和工程验证。历史数据和回测结果不代表未来收益，使用者需要自行评估交易风险。
