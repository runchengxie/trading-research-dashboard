# 运行配置与故障处理

## 配置项

| 环境变量 | 默认值 | 作用 |
| --- | --- | --- |
| `APCA_API_KEY_ID` | 空 | Alpaca key |
| `APCA_API_SECRET_KEY` | 空 | Alpaca secret |
| `ALPACA_DATA_FEED` | `iex` | Alpaca 行情源 |
| `MARKET_DATA_HISTORICAL_PROVIDER` | `auto` | 历史行情 provider：`auto`、`alpaca`、`yfinance` 或 `none` |
| `MARKET_DATA_SYMBOLS` | `sz300246` | 服务关注的标的 |
| `MARKET_DATA_QUOTE_MAX_AGE_SECONDS` | `15` | 报价过期阈值 |
| `MARKET_DATA_CORS_ORIGINS` | 空 | 允许浏览器跨 origin 访问 REST API 的显式 origin 列表，逗号分隔 |
| `REDIS_URL` | 空 | Redis runtime 地址 |
| `REDIS_HEARTBEAT_TTL_SECONDS` | `30` | collector 心跳有效期 |

没有设置 `REDIS_URL` 时，服务使用进程内存保存报价，适合本地开发。生产环境应配置 Redis，让 API、collector 和 WebSocket 共享同一份最新状态。

`MARKET_DATA_HISTORICAL_PROVIDER=auto` 在 Alpaca key 完整时使用 Alpaca，否则使用 yfinance。yfinance 不需要 key，只提供美股历史日线和近期分钟 bars，不提供本服务的实时 WebSocket 行情。设置为 `none` 可完全关闭历史 provider。

`MARKET_DATA_CORS_ORIGINS` 默认为空，因此不会额外开放跨 origin REST 访问。Dashboard 与行情服务不同源时，应填写 Dashboard 的完整浏览器 origin，例如 `https://trading.example.com`；多个 origin 用逗号分隔。只接受 `http://` 和 `https://` origin，通配符 `*` 会被拒绝。

## 运行状态

- `/healthz` 表示 API 进程能否响应。
- `/healthz.liveDataConfigured` 仅表示 Alpaca collector 已按凭据创建，不表示已经收到最新报价。
- `/readyz` 检查 Redis 连接和 collector 心跳，并返回 `200` 或 `503`。
- 报价超过过期阈值后标记为 `stale`，服务不会把它当作实时行情。
- Redis 连接失败时，collector 不应报告写入成功，API 应返回明确的不可用状态，Dashboard 继续使用静态数据。
- WebSocket 断开后，Dashboard 显示重连状态，并保留静态价格。
- 浏览器 health 请求失败或被 CORS 阻止时，Dashboard 把服务状态标记为“状态未知”；这只表示 health 未验证成功，不证明服务或 WebSocket 已宕机。

## Redis 数据

Redis 保存三类数据：

- 最新报价：按规范化标的保存。
- 报价发布：通过固定 Pub/Sub channel 通知 WebSocket 客户端。
- collector 心跳：使用有限 TTL，停止更新后自动过期。

报价写入使用时间戳单调校验，旧报价不能覆盖新报价。collector 和 FastAPI 必须分别创建自己的 Redis client，不能跨线程共享 async Redis client。

## 故障排查

1. 先访问 `/healthz`，确认 API 进程仍在运行。
2. 再检查 Redis URL、网络连接和权限。
3. 检查 collector 心跳是否在 TTL 内更新。
4. 检查 Alpaca 凭据、行情源权限和 `MARKET_DATA_SYMBOLS` 格式。
5. 检查 Dashboard 的 `VITE_MARKET_DATA_URL` 是否指向服务 origin。
6. 如果浏览器请求 `/healthz` 报跨域错误，检查 Dashboard origin 是否已加入 `MARKET_DATA_CORS_ORIGINS`。

本地单元测试使用 fake Redis。真实 Redis、provider 断开、重连和故障降级仍需要在集成环境验证。
