# 接口与数据格式

## 健康检查

```text
GET /healthz
```

返回服务进程和 collector 的基本状态。它适合确认进程是否还活着。

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

浏览器只能访问行情服务的 WebSocket，不能访问 Alpaca 或 Redis。
