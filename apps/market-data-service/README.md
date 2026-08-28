# Market Data Service

这是 Dashboard 使用的行情服务，负责统一证券代码、连接 Alpaca、提供美股历史行情和实时报价。

## 快速开始

在仓库根目录执行：

```bash
uv run --project apps/market-data-service uvicorn market_data_service.app:app \
  --host 127.0.0.1 --port 8000
```

启用 Alpaca 前先设置：

```bash
export APCA_API_KEY_ID="你的 key id"
export APCA_API_SECRET_KEY="你的 secret"
export ALPACA_DATA_FEED="iex"
```

密钥只放在服务端，不要写入前端配置或提交到仓库。

不配置 Alpaca key 时，服务默认使用 yfinance 提供美股历史日线和近期分钟数据。可通过 `MARKET_DATA_HISTORICAL_PROVIDER=alpaca|yfinance|none|auto` 选择历史数据源；yfinance 只用于历史数据，不替代 Alpaca 实时行情。

## 接口

```text
GET /healthz
GET /readyz
GET /v1/quotes/AAPL.US
GET /v1/bars/AAPL.US?start=2026-08-01T00:00:00Z&end=2026-08-27T00:00:00Z&timeframe=1d
WS  /v1/stream?symbols=AAPL,MSFT
```

支持的市场包括 A 股、港股和美股。美股统一使用 `us:AAPL` 或 `AAPL.US`，时区为 `America/New_York`。

## 测试

```bash
uv run --locked pytest -q
uv run --locked ruff check src tests
```

真实 Redis 集成测试：

```bash
REDIS_URL=redis://127.0.0.1:6379/0 \
  uv run --locked --group dev pytest -q -m integration
```

## 进一步阅读

- [API 说明](docs/api.md)
- [运行配置](docs/runtime.md)
- [Dashboard 接入](docs/dashboard-integration.md)

Dashboard 在历史行情或实时服务不可用时会保留静态快照和缓存作为降级路径。该服务不提供交易、账户、下单或资产管理接口。
