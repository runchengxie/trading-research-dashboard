# Trading Dashboard

Dashboard 是 Trading Dashboard 的 Web 与数据应用，当前重点支持 A 股股票和 ETF，负责行情整理、日内指标计算、Excel 输出、静态 Web 展示、PNG 图表导出和可选的 R-Breaker 回测。应用已经迁入 monorepo 的 `apps/dashboard/`，根级治理、CI 和部署由 monorepo 统一管理。

## 主要功能

- 获取股票和 ETF 日线、分时数据，并在数据源失败时使用本地运行时缓存兜底
- ETF 分钟数据优先读取 `etf-minute-fetcher` 归档的本地 Parquet
- 计算 20 日 ATR、VWAP、ORB、KMeans 支撑阻力和交易风格
- 生成 Excel 指标表和前端 `data.json`
- 维护经过审查的静态行情与研究发布基线
- 使用 React、TypeScript 和 ECharts 展示盘前概览、日内工作台和策略研究区
- 读取版本化研究快照，目前支持牛门线 v1/v2 契约
- 使用 Playwright 把现有 Web 图表导出为 PNG，方便 cron、Hermes Agent 或其他自动化工具推送
- 提供可选的 R-Breaker 回测模块

## 快速开始

以下命令默认在 `apps/dashboard/` 目录运行：

```bash
uv sync
uv run python -m trading_research.dashboard.astock_tech
```

默认会在 `out/indicators/` 生成 Excel 指标表。需要指定证券或输出目录时可以使用：

```bash
uv run python -m trading_research.dashboard.astock_tech \
  --codes sz300246,sz000001 \
  --output-root out
```

需要刷新前端行情快照时使用：

```bash
uv run python -m trading_research.dashboard.astock_tech \
  --json web/public/data.json
python scripts/validate_static_assets.py
```

`web/public/data.json` 当前作为受版本控制的行情发布基线。刷新它应在能够访问可靠行情源或有效本地缓存的环境完成，并通过 PR 审查。不要在无数据环境中用空 `stocks` 覆盖现有基线。

当前默认标的是宝莱特、美股 AAPL、MSFT、NVDA 和 TSLA。页面也支持通过配置和 `--codes` 选择其他股票、ETF 或美股 ticker，例如 `AMD.US,us:GOOGL`。美股没有服务或缓存数据时会跳过该标的，不生成伪造行情。

命令行参数和证券配置见 [配置说明](docs/configuration.md)。静态发布基线的职责见 [输出文件与目录结构](docs/outputs.md)。

## ETF 数据

先由独立的 `etf-minute-fetcher` 维护分钟历史，例如：

```bash
cd ../../../etf-minute-fetcher
uv run etf-min --symbols 510050.SH
```

然后在 `STOCK_CONFIG` 中配置 ETF：

```python
"510050.SH": {
    "name": "上证50ETF",
    "instrument_type": "etf",
}
```

默认分钟数据目录为：

```text
~/data/etf-minute-fetcher/minute/fund_min_1m
```

完整的数据源优先级、缓存和字段契约见 [数据源与 ETF 接入](docs/data-sources.md)。

## Web 工作台

前端位于 `web/`，页面由浏览器使用 ECharts 渲染，Python 不再维护第二套静态图表实现。

使用仓库中的当前发布基线启动开发服务器：

```bash
cd web
npm ci
npm run dev
```

生产构建前先验证静态快照：

```bash
cd ..
python scripts/validate_static_assets.py
cd web
npm test
npm run build
npm run preview
```

线上 Worker 当前为：

<https://trading-research-dashboard.xiaowang01.workers.dev/>

Cloudflare Workers Static Assets 和 GitHub Actions 部署方式见 [Cloudflare Workers 部署](docs/cloudflare-workers.md)。

## 导出图表图片

图片导出直接复用 React 和 ECharts 已经渲染好的页面。浏览器工作台与 PNG 因此使用同一套指标、组件和配色逻辑。

第一次使用 Playwright Chromium 时执行：

```bash
cd web
npx playwright install chromium
```

本地 `dist` 已构建时：

```bash
npm run build
npm run export:charts
```

脚本会临时启动 Vite preview，并把图片写入 monorepo 根目录：

```text
artifacts/charts/<数据日期>/
```

也可以直接从已部署站点导出：

```bash
npm run export:charts -- \
  --url https://trading-research-dashboard.xiaowang01.workers.dev/ \
  --output /var/lib/trading-research/charts \
  --theme light
```

每次导出包含盘前概览、每只证券的完整日内工作台、K 线图、可用时的分时图，以及机器可读的 `manifest.json`。manifest 使用 `trading_research.chart_export.v1`，包含行情 `generatedAt` 和图片文件列表，适合 Hermes Agent、cron 或消息机器人判断当日应该推送哪些图片。

详细目录和 cron 示例见 [输出文件与目录结构](docs/outputs.md)。

## 指标概览

| 指标 | 用途 |
| --- | --- |
| ATR | 估计日均波动空间，并参与 VWAP 偏离阈值计算 |
| VWAP | 分时成交量加权均价，用于衡量价格偏离 |
| ORB | 09:30 至 09:45 的开盘区间高低点 |
| KMeans | 从历史收盘价中提取支撑、阻力和关键价格 |

指标计算和交易风格规则见 [指标与逻辑](docs/indicators.md)。

## R-Breaker 回测

R-Breaker 是可选模块，需要额外安装回测依赖：

```bash
uv sync --extra backtest
uv run python -m trading_research.strategies.rbreaker \
  --symbol 603356 \
  --data-source akshare
```

详细说明见 [回测模块](docs/backtest.md)。当前 R-Breaker 仍保留一部分历史数据下载和缓存实现，后续会单独评估与统一数据层收敛，本轮维护不改变其策略行为。

## 功能来源与边界

| 来源 | 当前保留内容 | 位置 |
| --- | --- | --- |
| `wu-t0-trading-assitant` | 按证券覆盖 `vwap_dev_k` 的配置能力 | `apps/dashboard/src/trading_research/dashboard/astock_tech.py` |
| `wu-intraday-strategy` | R-Breaker 回测、参数优化和样本内外测试 | `apps/dashboard/src/trading_research/strategies/rbreaker.py` |
| `etf-minute-fetcher` | ETF 1 分钟 Parquet 数据契约 | `apps/dashboard/src/trading_research/data/data_sources.py` |

`etf-minute-fetcher` 仍独立维护。Dashboard 只消费稳定的数据目录契约，不会自动启动它，也不会把它作为 submodule 引入。

## 测试与质量检查

Dashboard Python 测试：

```bash
cd apps/dashboard
uv run --locked --extra backtest pytest -q
cd ../..
```

测试覆盖包入口、数据源回退、缓存、ETF 接入、静态发布基线、研究快照契约、部署检查和 Dashboard 集成等行为。

前端单元测试和构建：

```bash
cd apps/dashboard/web
npm ci
npm test
npm run build
```

浏览器 E2E：

```bash
npx playwright install chromium
npm run test:e2e
```

monorepo 根级 `Monorepo foundation` workflow 还会运行 Ruff、Python 依赖审计和 `npm audit`。GitHub Actions 目前只允许手动触发。

## 文档

- [前端说明](docs/web-frontend.md)：前端结构、策略注册表、主题和图片导出
- [指标与逻辑](docs/indicators.md)：ATR、VWAP、ORB、KMeans 和交易风格
- [配置说明](docs/configuration.md)：证券配置、环境变量和 CLI
- [数据源与 ETF 接入](docs/data-sources.md)：数据源优先级、Parquet 和运行时缓存
- [研究快照](docs/research-snapshot.md)：牛门线研究快照契约和发布边界
- [回测模块](docs/backtest.md)：R-Breaker 回测
- [输出文件与目录结构](docs/outputs.md)：发布快照、Excel、Web 构建和 PNG 导出
- [Cloudflare Workers 部署](docs/cloudflare-workers.md)：Workers Static Assets 部署
- [常见问题与排错](docs/troubleshooting.md)：常见运行问题

## 免责声明

本项目用于策略研究和工程验证。历史数据、指标和回测结果不能保证未来收益，使用者需要自行评估交易风险。
