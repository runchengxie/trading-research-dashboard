# Trading Research Dashboard

这是一个用于研究和展示交易策略的 monorepo，包含行情数据、研究计算、策略回测和 Web 看板。

## 先看这里

- 想启动看板：进入 [`apps/dashboard/`](apps/dashboard/README.md)
- 想运行行情服务：进入 [`apps/market-data-service/`](apps/market-data-service/README.md)
- 想了解项目结构：阅读 [`docs/architecture/project-structure.md`](docs/architecture/project-structure.md)
- 想了解当前进度：阅读 [`docs/roadmap/README.md`](docs/roadmap/README.md)
- 想了解部署和生产切换：阅读 [`docs/operations/runtime-cutover.md`](docs/operations/runtime-cutover.md)

## 项目包含什么

```text
apps/dashboard/                 数据处理、策略研究和 Web 看板
apps/market-data-service/       美股实时与历史行情服务
packages/research-core/         研究快照和 JSON Schema
packages/niu-men-line-strategy/ Niu Men 策略与研究工具
docs/                           架构、配置、部署和维护文档
tests/                          根目录契约与 workflow 测试
```

当前看板支持 A 股、港股和美股股票/ETF。默认美股标的是 AAPL、MSFT、NVDA 和 TSLA。R-Breaker 研究结果可在看板的策略研究区域查看。

当前线上地址：

<https://trading-research-dashboard.xiaowang01.workers.dev>

## 快速开始

需要 Python 3.11 或更高版本、`uv` 和 Node.js。完整安装说明见 [`docs/getting-started.md`](docs/getting-started.md)。

```bash
uv sync
(cd apps/dashboard && uv run --extra backtest pytest -q)
npm ci --prefix apps/dashboard/web
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
```

## 重要边界

`research-workspace`、`market-data-platform` 和 `etf-minute-fetcher` 是仓库外的独立项目，当前仓库没有 Git submodule。原始行情、凭据和大型回测产物也不提交到本仓库。

## 当前状态

- M0 至 M4：已完成，包含一次真实 R-Breaker Tushare 快照发布
- M5：核心代码已完成，真实 Redis、provider 和部署环境故障验证仍待执行
- M6：shadow runtime 已完成，生产切换和连续运行观察仍待执行
- M6b：旧仓库 freeze、调用方审计和 archive 等待 M6 完成

详细状态以 [`docs/roadmap/README.md`](docs/roadmap/README.md) 为准。

## 免责声明

本项目用于策略研究和工程验证。历史数据和回测结果不代表未来收益，使用者需要自行评估交易风险。
