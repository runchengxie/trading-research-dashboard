# 接口与数据格式

## OpenAPI

FastAPI 会根据命名的 Pydantic response models 生成 `/openapi.json` 和 `/docs`。需要给 codegen 使用稳定的 JSON 文件时，在 `apps/market-data-service` 执行：

```bash
uv run --locked python scripts/export_openapi.py /tmp/market-data-openapi.json
```

当前 REST schema 包含 `HealthResponse`、`ReadyResponse`、`QuoteResponse`、`BarResponse` 和 `BarsResponse`。WebSocket payload 继续按运行时契约维护，不由 OpenAPI 描述。

## 健康检查

```text
GET /healthz
```

返回服务进程和 collector 的基本状态。它适合确认进程是否还活着，也是 Dashboard 在配置 `VITE_MARKET_DATA_URL` 后使用的服务状态接口。

## 最新报价

```text
GET /v1/quotes/{symbol}
```

示例：

```json
{
  "symbol": "us:AAPL",
  "price": 201.25,
  "timestamp": "2026-08-27T14:31:00+00:00",
  "source": "alpaca",
  "status": "live",
  "freshness": "current"
}
```

`freshness` 由服务根据 `MARKET_DATA_QUOTE_MAX_AGE_SECONDS` 计算。行情超过这个时间会标记为 `stale`。

没有可用报价时返回 `404`。代码格式错误时返回 `400`。

## 历史行情

```text
GET /v1/bars/{symbol}?start=2026-08-01T00:00:00Z&end=2026-08-27T00:00:00Z&timeframe=1d
```

`timeframe` 支持 `1d` 和 `1m`。历史 provider 未配置时返回 `503`。服务不会用空数据或手工数据填充行情。

## WebSocket 实时流

```text
WS /v1/stream?symbols=AAPL,MSFT
```

连接建立后，服务发送请求标的的最新报价和后续变化。连接断开后，Dashboard 负责重连并回退到静态价格。

浏览器可以通过 Dashboard 配置的服务 origin 访问行情 REST API 和 WebSocket，但不能直接访问 Alpaca 或 Redis。跨 origin REST 访问必须把 Dashboard origin 显式加入 `MARKET_DATA_CORS_ORIGINS`；服务拒绝通配符 `*`。
