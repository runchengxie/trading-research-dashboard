# Market Data Service

这是 Dashboard 的行情服务，负责两件事：

1. 从 Alpaca 接收美股实时成交，并提供最新价格。
2. 为 Dashboard 提供美股日线和 1 分钟历史行情。

Dashboard 浏览器不会直接连接 Alpaca。没有配置行情服务时，Dashboard 仍会使用自己的静态快照。

## 快速开始

在仓库根目录执行：

```bash
uv run --package market-data-service \
  uvicorn market_data_service.app:app --host 127.0.0.1 --port 8000
```

启动后可以访问：

```text
http://127.0.0.1:8000/healthz
http://127.0.0.1:8000/v1/quotes/AAPL.US
ws://127.0.0.1:8000/v1/stream?symbols=AAPL,MSFT
```

没有 Alpaca 凭据时，服务仍能启动，`/healthz` 可用，实时行情接口会返回暂时没有数据。这个模式适合本地开发和运行 Dashboard 静态页面。

## 配置 Alpaca

配置以下环境变量后，服务会启动美股实时采集和历史行情 provider：

```bash
export APCA_API_KEY_ID="你的 Alpaca key"
export APCA_API_SECRET_KEY="你的 Alpaca secret"
export ALPACA_DATA_FEED="iex"
export MARKET_DATA_SYMBOLS="AAPL.US,MSFT.US,NVDA.US,TSLA.US"
export MARKET_DATA_QUOTE_MAX_AGE_SECONDS="15"
```

支持 `iex`、`sip` 和 `delayed_sip` 三种行情源。`delayed_sip` 返回的行情状态为 `delayed`。

密钥只能放在服务端环境变量中，不能写入 `data.json`、前端环境变量或浏览器代码。

## 支持的代码

服务会把不同写法转换成统一格式：

| 市场 | 示例 | 币种 | 时区 |
| --- | --- | --- | --- |
| A 股 | `sz300246` | CNY | `Asia/Shanghai` |
| 港股 | `hk00700` | HKD | `Asia/Hong_Kong` |
| 美股 | `us:AAPL` | USD | `America/New_York` |

美股也接受 `AAPL.US`。API 路径和 WebSocket 参数还接受裸代码 `AAPL`。

## 本地测试

在服务目录执行：

```bash
cd apps/market-data-service
uv run --locked pytest -q
uv run --locked ruff check src tests
```

默认测试不需要公网行情、Alpaca 凭据或 Redis。测试 Redis 行为使用 fake client。需要验证真实 Redis 时，参考 [运行配置与故障处理](docs/runtime.md)。

## 接入 Dashboard

启动 Dashboard 前设置服务地址：

```bash
export VITE_MARKET_DATA_URL="http://127.0.0.1:8000"
```

Dashboard 会先加载静态 `data.json`，再为美股建立 WebSocket 连接，只覆盖当前价格和实时状态。历史数据由 Dashboard 的数据层请求，服务不可用时继续使用本地缓存。

## 文档索引

- [接口与数据格式](docs/api.md)：健康检查、报价、历史 K 线和 WebSocket。
- [运行配置与故障处理](docs/runtime.md)：Redis、Alpaca、readiness、过期行情和降级行为。
- [Dashboard 数据接入](docs/dashboard-integration.md)：浏览器如何使用实时和历史行情。

本服务只提供行情读取能力，不提供账户、下单、持仓或交易接口。
