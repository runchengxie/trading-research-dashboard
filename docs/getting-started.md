# 新人上手

## 环境准备

需要 Python 3.11 或更高版本、`uv`、Node.js 22 和 `pnpm` 11。在仓库根目录执行：

```bash
uv sync
pnpm install
```

## 运行 Dashboard

生成本地数据：

```bash
cd apps/dashboard
uv run python -m trading_research.dashboard.astock_tech \
  --codes sz300246,AAPL.US,TSLA.US \
  --output-root out \
  --json web/public/data.json
```

启动前端：

```bash
pnpm --dir apps/dashboard/web dev
```

## 运行测试

```bash
# 根目录测试
uv run --locked --extra dev pytest -q

# Dashboard 测试
cd apps/dashboard
uv run --locked --extra backtest pytest -q
uv run --locked ruff check src scripts tests

# 行情服务测试
cd ../market-data-service
uv run --locked pytest -q
uv run --locked ruff check src tests
```

## 需要密钥的功能

美股实时行情需要在行情服务进程中配置 `APCA_API_KEY_ID` 和 `APCA_API_SECRET_KEY`。R-Breaker 数据下载需要 `TUSHARE_TOKEN`。密钥不要写入前端配置或提交到仓库。

如果只需要美股历史日线或近期分钟数据，可以不配置 Alpaca，服务会在 `MARKET_DATA_HISTORICAL_PROVIDER=auto` 时使用 yfinance。复制根目录 `.env.example` 为 `.env` 后按需填写配置；`.env` 不应提交到 Git。

项目自己的缓存、研究 artifact 和运行输出默认保存在仓库外的 `~/data/trading-research-dashboard`。A 股/ETF 原始数据仍由外部 `market-data-platform` 和 `etf-minute-fetcher` 目录提供，不复制进本项目数据根目录。数据源、发布和部署的详细说明见各子项目 `docs/` 目录，以及 [项目路线图](roadmap/README.md)。

## 私下分享

如果需要把项目交给朋友本地运行，使用根目录的安全打包脚本：

```bash
uv run python scripts/package_share.py --output /tmp/trading-research-dashboard-share.zip
```

压缩包包含完整项目源码、GitHub Actions workflow、Dashboard 静态 `data.json`/研究快照、`.env.example` 和 `SHARE-MANIFEST.json`，不带 `.env`、真实 Alpaca/Tushare key、原始缓存、`node_modules` 或构建产物。`market-data-platform` 和 `etf-minute-fetcher` 的原始数据不进入压缩包，manifest 会记录外部数据源及其环境变量。接收方复制 `.env.example` 为 `.env` 后，在自己的环境中填写 key；不要把真实 key 放进压缩包或前端 `VITE_*` 变量。

默认看板会按当前 `data.json` 的内容显示市场。仓库内的 demo 快照包含宝莱特和 TSLA，数据可以滞后于最新交易日，但日线、分时、指标和日内工作台均可直接演示。重新生成美股数据时，在行情服务中设置 `MARKET_DATA_HISTORICAL_PROVIDER=yfinance`，或配置 Alpaca 后使用 Alpaca 历史数据。浏览器不会直接访问 yfinance 或 Alpaca。
