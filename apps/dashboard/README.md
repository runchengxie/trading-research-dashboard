# Dashboard

这是项目的 Python 数据应用和 React Web 看板，支持 A 股、港股、美股股票/ETF、行情指标、研究快照、图表导出、contextual research 和 R-Breaker 回测。

## 快速开始

在本目录执行：

```bash
uv sync
uv run python -m trading_research.dashboard.astock_tech \
  --codes sz300246,AAPL.US,TSLA.US \
  --output-root out \
  --json web/public/data.json

# 可选：为现有 data.json 注入市场上下文、setup event、跨标的确认和事件研究容器
uv run python -m trading_research.scripts.enrich_contextual_research \
  --input web/public/data.json
```

前端开发服务器：

```bash
cd web
npm ci
npm run dev
```

## 常用命令

```bash
# Python 测试和检查
uv run --locked --extra backtest pytest -q
uv run --locked ruff check src scripts tests

# 前端测试和构建
npm --prefix web test
npm --prefix web run build

# R-Breaker 回测
uv run --extra backtest python -m trading_research.strategies.rbreaker \
  --symbol 603356 --data-source akshare
```

默认配置包括宝莱特、AAPL、MSFT、NVDA 和 TSLA。仓库内的静态 demo 快照目前包含宝莱特和 TSLA。重新生成美股快照时，先启动 `market-data-service`，并在服务中选择 yfinance 或 Alpaca 历史 provider。实时行情和历史数据配置见 [配置说明](docs/configuration.md)。

Contextual research 对旧快照仍保持兼容，但 authoritative 发布会强制执行 enrichment 和 coverage 校验。详细 contract、session、day archetype、setup detector、intermarket 和 event study 语义见 [Contextual Research](docs/contextual-research.md)。

## 目录

```text
src/trading_research/dashboard/   指标计算、配置、上下文研究和数据生成
src/trading_research/data/        数据源、缓存和市场兼容层
src/trading_research/strategies/  R-Breaker 策略与回测
src/trading_research/scripts/     研究快照与 contextual enrichment CLI
web/                              React、TypeScript 和 ECharts 前端
tests/                            Python 测试
docs/                             本应用的技术文档
```

## 技术文档

- [配置和环境变量](docs/configuration.md)
- [数据源和缓存](docs/data-sources.md)
- [指标计算](docs/indicators.md)
- [Contextual Research](docs/contextual-research.md)
- [R-Breaker 回测](docs/backtest.md)
- [研究快照](docs/research-snapshot.md)
- [图表导出和输出目录](docs/outputs.md)
- [前端与主题](docs/web-frontend.md)
- [常见问题](docs/troubleshooting.md)

原始行情、凭据和大型研究产物保存在仓库外。`research-workspace`、`market-data-platform` 和 `etf-minute-fetcher` 是独立项目，不会作为 Git submodule 引入。
