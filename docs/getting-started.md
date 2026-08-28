# 新人上手

## 环境准备

需要 Python 3.11 或更高版本、`uv`、Node.js 和 npm。在仓库根目录执行：

```bash
uv sync
npm ci --prefix apps/dashboard/web
```

## 运行 Dashboard

生成本地数据：

```bash
cd apps/dashboard
uv run python -m trading_research.dashboard.astock_tech \
  --codes sz300246,AAPL.US,TSLA.US \
  --output-root out
```

启动前端：

```bash
cd web
npm run dev
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

原始行情和大型研究产物默认保存在仓库外的 `~/data` 目录。数据源、发布和部署的详细说明见各子项目 `docs/` 目录，以及 [项目路线图](roadmap/README.md)。
