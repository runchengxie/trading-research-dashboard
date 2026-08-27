# M5 实时行情运行时设计

## 状态

已批准设计的书面化版本。本文定义 M5 实时行情运行时的稳定边界，作为后续 collector、Redis、API、WebSocket 和 Dashboard 实时模式 PR 的共同契约。

当前 `main` 已有 `apps/market-data-service/` 第一阶段骨架：统一 A 股 symbol、`Quote`、`Freshness`、`ServiceConfig` 和异步 `MarketDataProvider` protocol。该骨架刻意没有外部 provider、常驻 collector、Redis、网络 API、WebSocket 或 Dashboard live mode。M5 在这些边界上增加运行时能力，不重写现有契约层。

## 目标

建立一条可独立运行、可降级、可替换 provider 的实时行情链路：

```text
external market-data provider
          │
          ▼
 MarketDataProvider adapter
          │
          ▼
      collector
 retry / backoff / validation
          │
          ▼
        Redis
   latest state + Pub/Sub
      │             │
      ▼             ▼
    REST         WebSocket
      │             │
      └──────┬──────┘
             ▼
      React Dashboard
             │
      live unavailable/stale
             ▼
   existing static data.json
```

第一版服务 Dashboard 配置的有限标的集合，并保留未来替换为全市场数据源的接口。M5 不把本仓库扩张成新的全市场行情平台；`market-data-platform`、`etf-minute-fetcher` 等外部基础设施继续保持仓库边界。

## 明确暂不做

本阶段不实现：

- 全 A 股逐 tick 或逐笔成交基础设施；
- 实时 1 分钟 OHLCV 聚合；
- 历史行情长期存储、回放或事件审计日志；
- Kafka、Redis Streams 等持久事件总线；
- 浏览器直接访问 Eastmoney、AKShare 或其他行情供应商；
- 将实时 quote 强行写入现有历史 `intraday` 数组；
- 将静态 `data.json` 描述成实时 API；
- 在实时链路未稳定前删除静态快照降级路径；
- 本阶段执行 M6 runtime cutover。

实时 Bar、累计成交量语义和 session aggregation 需要单独设计，因为 quote 更新不能自动推出正确 OHLCV。

## 架构原则

### 进程分离

collector 与 API 是两个独立运行职责：

- collector 只负责 provider 调用、校验、重试、写 Redis 和发布更新；
- API 只负责读取 Redis、暴露健康状态、提供 REST 和订阅 Redis Pub/Sub 后推送 WebSocket；
- Dashboard 只依赖版本化 HTTP/WebSocket contract，不知道具体 provider 或 Redis 实现。

不把 collector 放进 FastAPI background task，避免多 worker 重复采集、API 重启中断采集，以及后续横向扩展时职责混乱。

### 轻量 provider adapter

首个 provider 使用独立 HTTP adapter，默认实现为 Eastmoney snapshot adapter，并通过 `httpx` 访问外部 HTTP 接口。供应商字段、市场代码映射和响应解析仅存在于 adapter 内部；collector、Redis、API 和 Dashboard 只依赖 `MarketDataProvider` 与标准 `Quote`。

AKShare 可以作为后续 fallback adapter，但 M5 常驻服务不因为 Dashboard 已依赖 AKShare 就反向继承完整研究依赖栈。

### 状态流而非审计流

Redis 保存“最新已知状态”，Pub/Sub 只负责低延迟通知。WebSocket 客户端断线期间允许丢失中间消息，重连后重新读取 latest state 再继续订阅。

因此 M5 不需要 Kafka 或 Redis Streams。以后出现逐事件审计、重放或成交序列严格完整性的需求，再引入持久事件流。

## Domain contract

现有 `Quote` 保持 provider-neutral：

```python
@dataclass(frozen=True, slots=True)
class Quote:
    symbol: str
    price: float
    timestamp: datetime
    source: str
    status: QuoteStatus = QuoteStatus.LIVE
```

M5 不为了网络传输把 provider contract 改造成 Web DTO。网络层增加独立 versioned envelope。

## Live quote wire contract

线协议版本固定为：

```text
trading_research.live_quote.v1
```

REST、Redis latest value 与 WebSocket `quote` 消息共享同一 canonical JSON payload：

```json
{
  "schemaVersion": "trading_research.live_quote.v1",
  "symbol": "sz300246",
  "price": 12.34,
  "timestamp": "2026-08-26T14:31:22+08:00",
  "receivedAt": "2026-08-26T14:31:22.184+08:00",
  "source": "eastmoney",
  "status": "live",
  "freshness": "current"
}
```

字段语义：

- `timestamp`：行情供应商代表的市场数据时间，必须带时区；
- `receivedAt`：collector 接收并接受该 quote 的时间，必须带时区；
- `source`：provider 稳定标识；
- `status`：沿用 domain `QuoteStatus`；
- `freshness`：根据 `timestamp` 和 `quote_max_age_seconds` 计算；
- 不允许旧 `timestamp` 覆盖同 symbol 已存在的较新 quote。

Redis 可以保存写入当刻的 `freshness`，但所有读取边界必须重新计算它。这样 Redis 里曾经的 `current` 不会永久保鲜。

网络 consumer 必须按 `schemaVersion` 显式判断。前端收到未知版本时忽略 live payload 并进入静态降级状态，不能猜字段。

## Redis contract

Redis key/channel 使用固定 namespace：

```text
trading-research:live:v1:quote:<symbol>
trading-research:live:v1:collector:heartbeat
trading-research:live:v1:quotes
```

### Latest quote

每个 symbol 使用一个 string key，value 为 `trading_research.live_quote.v1` JSON。

latest quote key 不设置短 TTL。collector 暂停或市场休市时，最后一份已知状态仍有诊断价值；API 使用 `timestamp` 明确标记 `stale`，不会把旧值伪装成 live 数据。

写入满足单调时间规则：只有新 quote 的 `timestamp >= existing.timestamp` 时才可覆盖。相同 timestamp 允许覆盖，以便供应商修正同一时刻状态。

### Collector heartbeat

collector 每个完成的采集循环都更新：

```text
trading-research:live:v1:collector:heartbeat
```

value 固定包含：

```json
{
  "loopAt": "2026-08-26T06:31:22Z",
  "lastSuccessAt": "2026-08-26T06:31:22Z",
  "successCount": 1,
  "failureCount": 0
}
```

语义：

- `loopAt`：最近一个已完成 collector loop 的 UTC 时间，无论该轮有无成功 quote 都更新；
- `lastSuccessAt`：最近一次至少成功接受一个 quote 的 UTC 时间，没有成功历史时为 `null`；
- `successCount` / `failureCount`：最近一轮 symbol 结果计数。

heartbeat key 使用有限 TTL，默认 30 秒。这样 readiness 可以区分“collector 进程停止”和“collector 仍运行但上游长期没有有效数据”。

### Pub/Sub

channel：

```text
trading-research:live:v1:quotes
```

collector 只有在 latest quote 成功写入后才 publish 同一 canonical payload。订阅者不得把 Pub/Sub 当历史来源。

## Runtime interfaces

为了让 Redis、API 和 collector 独立 PR 开发，M5.1 先冻结以下 Python protocol：

```python
class QuoteStore(Protocol):
    async def get_quote(self, symbol: str) -> LiveQuote | None: ...
    async def get_quotes(self, symbols: Sequence[str]) -> list[LiveQuote]: ...
    async def put_quote(self, quote: LiveQuote) -> bool: ...

class QuotePublisher(Protocol):
    async def publish_quote(self, quote: LiveQuote) -> None: ...

class QuoteSubscription(Protocol):
    async def __aenter__(self) -> QuoteSubscription: ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...
    def __aiter__(self) -> AsyncIterator[LiveQuote]: ...

class QuoteSubscriber(Protocol):
    def subscribe_quotes(self, symbols: Sequence[str]) -> QuoteSubscription: ...
```

`LiveQuote` 是 wire envelope 的 typed Python 表示，不替换 domain `Quote`。

Redis implementation 同时实现 `QuoteStore`、`QuotePublisher` 和 `QuoteSubscriber`。API tests 使用 fake/in-memory implementation，因此 API PR 不要求真实 Redis 才能开发和测试。

## 配置

现有环境变量继续保留：

```text
MARKET_DATA_SYMBOLS
MARKET_DATA_QUOTE_MAX_AGE_SECONDS
```

新增：

```text
MARKET_DATA_PROVIDER=eastmoney
MARKET_DATA_POLL_INTERVAL_SECONDS=3
MARKET_DATA_REQUEST_TIMEOUT_SECONDS=5
MARKET_DATA_RETRY_ATTEMPTS=3
MARKET_DATA_RETRY_BASE_DELAY_SECONDS=0.5
MARKET_DATA_REDIS_URL=redis://localhost:6379/0
MARKET_DATA_HEARTBEAT_TTL_SECONDS=30
MARKET_DATA_ALLOWED_ORIGINS=http://localhost:5173
```

约束：

- poll interval、timeout、retry attempts、retry delay、heartbeat TTL 必须为正值；
- symbols 继续通过现有 `normalize_symbol()` 规范化；
- secrets 不写入仓库；
- Dashboard 构建期 live endpoint 使用 Vite 环境变量，不把本机地址写死在源码。

前端变量：

```text
VITE_MARKET_DATA_API_URL
VITE_MARKET_DATA_WS_URL
```

两个变量都未配置时，Dashboard 明确运行在 static-only 模式。

## Collector

collector 是独立 async entrypoint，负责：

1. 从 `ServiceConfig` 读取 symbol 集合；
2. 通过 provider adapter 获取 quote；
3. 对单个 symbol 的临时失败执行有限重试和指数退避；
4. 校验 symbol、price、timezone、source；
5. 拒绝比 Redis latest state 更旧的 quote；
6. 成功写 Redis 后 publish；
7. 每轮结束都写 heartbeat，并维护 `lastSuccessAt`；
8. 单个 symbol 失败不会取消整轮其他 symbol；
9. cancellation 时正常退出，不吞掉 `CancelledError`。

第一版只采集配置 symbol，不因为 API 请求临时扩展任意 symbol。这样公开 API 不会变成未经控制的免费行情代理。

provider 失败时不在同一个 PR 中引入多供应商切换状态机。fallback provider 在 adapter contract 稳定后另行增加。

## REST API

FastAPI 路由固定为：

```text
GET /healthz
GET /readyz
GET /v1/quotes/{symbol}
GET /v1/quotes?symbols=sz300246,sh600000
WS  /v1/stream/quotes?symbols=sz300246,sh600000
```

### `GET /healthz`

仅表示 API 进程可响应，不要求 Redis 或 collector 正常。返回 HTTP 200。

### `GET /readyz`

检查 Redis connectivity 与 heartbeat：

- Redis 可用、heartbeat key 存在且 `loopAt` 当前，同时 `lastSuccessAt` 未超过 `max(2 * quote_max_age_seconds, heartbeat_ttl_seconds)`：HTTP 200，`status=ready`；
- Redis 可用但 heartbeat 缺失/过期或 `loopAt` 过旧：HTTP 503，`status=collector_stale`；
- collector 仍有新 loop，但 `lastSuccessAt` 缺失或超过上述阈值：HTTP 503，`status=upstream_stale`；
- Redis 不可用：HTTP 503，`status=redis_unavailable`。

休市期间 quote 自然会 stale，因此生产部署如果需要 24x7 readiness，后续必须引入明确 `MarketStatus`/交易时段 contract。M5 第一版的 readiness 面向实时采集时段，部署监控不得把闭市后的 `upstream_stale` 当作服务进程死亡。

### `GET /v1/quotes/{symbol}`

- symbol 非法：HTTP 422；
- symbol 合法但没有 latest state：HTTP 404；
- 有状态：HTTP 200，返回 canonical live quote envelope；
- freshness 在响应时重新计算。

### `GET /v1/quotes`

`symbols` 必填，逗号分隔并去重，返回已找到 payload 和 missing symbols。第一版不提供无参数扫描 Redis 全量 symbol 的接口。

## WebSocket

连接：

```text
/v1/stream/quotes?symbols=<comma-separated-symbols>
```

服务端行为：

1. 校验并去重 symbols；
2. 建立 Redis Pub/Sub subscription；
3. 从 `QuoteStore` 读取请求 symbols 的 latest state，重新计算 freshness 后发送 `snapshot`；
4. 把匹配 symbol 的 Pub/Sub 更新作为 `quote` 消息发送；
5. 客户端断开后立即清理 subscription；
6. Redis subscription 异常导致连接关闭，让客户端重连并重新 bootstrap latest state。

snapshot：

```json
{
  "type": "snapshot",
  "quotes": [],
  "missingSymbols": []
}
```

后续更新：

```json
{
  "type": "quote",
  "quote": {
    "schemaVersion": "trading_research.live_quote.v1"
  }
}
```

第一版不支持连接后动态 subscribe/unsubscribe command。标的变化时前端重建连接。

## Dashboard live mode

现有 `loadDashboard()` 和静态 `data.json` 保持启动基线。实时模式是增强层，不成为页面首屏单点故障。

### 启动顺序

1. 正常加载现有 `data.json`；
2. 没有配置 live endpoint 时保持 static-only；
3. 配置 live endpoint 时，对当前 Dashboard symbols 做 REST bootstrap；
4. 建立 WebSocket；
5. live quote 只覆盖“最新价格/来源/时间/连接状态”展示，不重写历史 daily/intraday/indicator 数据；
6. WebSocket 消息只有 `timestamp >= 当前 live quote timestamp` 时才更新；
7. 连接断开后指数退避重连，重连成功重新 bootstrap snapshot。

### UI 状态

前端明确区分：

```text
LIVE
RECONNECTING
STALE
STATIC
```

语义：

- `LIVE`：WebSocket 已连接且当前选中标的 quote freshness=current；
- `RECONNECTING`：live endpoint 已配置但 WebSocket 正在恢复；
- `STALE`：有 live latest state，但 quote 已超过 freshness threshold；
- `STATIC`：没有配置 live endpoint，或 live bootstrap/连接不可用且只能使用 `data.json`。

实时链路失败不会把盘前概览、历史图表或策略研究一起渲染失败。

### Cloudflare 边界

当前 Dashboard Worker 主要发布静态资产。Python market-data service 作为独立 origin 部署，生产环境通过 HTTPS/WSS URL 配置给前端。

M5 不假设 Cloudflare Static Assets 能承载 Python FastAPI、Redis 或长期 collector 进程。跨域访问使用显式 CORS allowlist，不能默认 `*`。

## 依赖策略

`apps/market-data-service` 增加最小运行时依赖：

- `httpx`：provider HTTP client；
- `redis`：使用 `redis.asyncio`；
- `fastapi`；
- `uvicorn`：本地/服务进程入口。

测试继续使用 pytest。Redis 单元测试优先 fake protocol implementation；真实 Redis integration test 通过显式环境开关运行，不成为默认无基础设施测试的硬要求。

不把 pandas、numpy、matplotlib 或 Dashboard 的完整行情研究依赖加入 market-data-service。

## 测试策略

### Runtime core

覆盖 live envelope serialize/deserialize、schema version、timezone enforcement、freshness 重算、older quote rejection、heartbeat model 和 config validation。

### Provider / collector

provider 使用固定 HTTP fixture，普通测试不访问公网。覆盖 symbol/market id 映射、正常响应解析、空响应/错误字段、HTTP timeout/retry、单 symbol 失败隔离、write-before-publish、heartbeat 更新和 cancellation。

### Redis

覆盖 key naming、canonical JSON round trip、monotonic write、heartbeat TTL、publish/subscribe filtering 和 subscription cleanup。

### API / WebSocket

通过 FastAPI test client + fake store/pubsub 覆盖 health/readiness、invalid/missing/current/stale quote、multi-symbol query、WebSocket initial snapshot、后续 quote update、disconnect cleanup 和 store/subscription failure。

### Frontend

覆盖 live DTO parser、未知 schema version、timestamp ordering、static-only、REST bootstrap、WebSocket reconnect、stale/static fallback，并要求 `npm test` 和 `npm run build` 继续通过。

### Repository gates

每个 PR 运行其作用域相关测试；integration PR 运行完整现有门槛：

```text
uv lock --check
uv run --locked --extra dev pytest -q
uv run --locked ruff check ...
uv run --locked python scripts/check_foundation.py
npm ci --prefix apps/dashboard/web
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
```

依赖变化后更新根 `uv.lock`，不恢复成员独立 lockfile。

## PR 与 worktree 拆分

所有实现改动遵守仓库 `AGENTS.md`：独立分支、独立 worktree、独立 PR；多个 agent 不共享 worktree 或 branch。

### PR 0：设计

```text
branch: docs/m5-live-runtime-design
```

只包含本文档，作为实现共同契约。

### PR 1：M5.1 runtime core

```text
branch: feat/m5-runtime-core
```

负责 `LiveQuote` wire type/serializer、heartbeat type、store/publisher/subscriber protocols、config 扩展、market-data-service runtime dependencies、tests 和根 lockfile。

这是后续并行 PR 唯一共同前置依赖。合入 `main` 后，其余实现 worktree 都从新的 `origin/main` 创建。

### PR 2：M5.2 Eastmoney provider + collector

```text
branch: feat/m5-eastmoney-collector
```

主要拥有：

```text
apps/market-data-service/src/market_data_service/providers/
apps/market-data-service/src/market_data_service/collector.py
apps/market-data-service/tests/test_eastmoney_provider.py
apps/market-data-service/tests/test_collector.py
```

通过 protocols 与 Redis 层解耦，测试使用 fake store/publisher。

### PR 3：M5.3 Redis state layer

```text
branch: feat/m5-redis-store
```

主要拥有：

```text
apps/market-data-service/src/market_data_service/redis_store.py
apps/market-data-service/tests/test_redis_store.py
```

不得修改 provider 或 Dashboard。

### PR 4：M5.4 FastAPI + WebSocket

```text
branch: feat/m5-live-api
```

主要拥有：

```text
apps/market-data-service/src/market_data_service/api.py
apps/market-data-service/tests/test_api.py
```

使用 runtime protocols 和 fake implementation 完成单元测试，不依赖 PR 3 的 concrete Redis class 才能开发。

### PR 5：M5.5 Dashboard live mode

```text
branch: feat/m5-dashboard-live-mode
```

主要拥有：

```text
apps/dashboard/web/src/live/
apps/dashboard/web/src/api.ts
apps/dashboard/web/src/App.tsx
apps/dashboard/web/src/types.ts
对应前端 tests
```

只依赖本文定义的 REST/WS wire contract，因此可以与 PR 2/3/4 并行。

### PR 6：M5.6 runtime integration

```text
branch: feat/m5-runtime-integration
```

在 PR 2/3/4/5 合并后创建，负责 concrete Redis wiring、collector/API entrypoints、本地运行配置、README/runbook/roadmap、foundation allowlist 必要调整、全量验证以及生产 endpoint/CORS 配置。PR 6 不重新实现前几个 PR 的逻辑。

## 并行开发规则

1. PR 1 单独完成并合入 `main`；
2. PR 2、3、4、5 都从 PR 1 合并后的同一个 `origin/main` 创建独立 worktree；
3. 每个 agent 只修改自己 PR 的主要 ownership 文件；
4. `pyproject.toml`、`uv.lock`、README、roadmap 等高冲突共享文件尽量集中到 PR 1 或 PR 6；
5. 若必须修改 shared contract，先停下相关依赖 PR，把 contract 变化放到新的前置 PR 或明确串行处理；
6. PR 合并后同步 main，删除本地/远端功能分支，移除对应 worktree，再执行 `git worktree prune`；
7. 不在共享 `main` worktree 直接修改源码。

生命周期：

```text
sync main
  ↓
create branch + isolated worktree
  ↓
TDD implementation
  ↓
local verification
  ↓
commit + push
  ↓
open PR
  ↓
review + verification
  ↓
merge to main
  ↓
sync main
  ↓
delete local/remote branch
  ↓
remove worktree + prune
```

## 故障与降级语义

- provider 单 symbol 失败：保留 Redis 上一份状态，该 symbol 可能 stale；其他 symbols 继续采集；
- provider 整体失败：collector heartbeat 的 `loopAt` 继续更新、`lastSuccessAt` 停止前进，readiness 进入 `upstream_stale`；
- collector 停止：heartbeat TTL 过期，readiness 进入 `collector_stale`；
- Redis 失败：collector 不伪装写入/publish 成功；API readiness=503；WebSocket 关闭并让客户端重连；
- API 失败：Dashboard 保持 static snapshot；
- WebSocket 失败：Dashboard 进入 reconnecting，仍可使用 REST latest/static；
- 未知 wire version：consumer 拒绝 live payload，静态路径继续工作；
- 过期 quote：展示 stale，不影响历史研究界面。

## 安全与运行边界

- 不提交 provider token、Redis password、生产 host secret；
- Redis 不直接暴露给浏览器；
- API 只提供配置 symbol 集合 latest state，不按任意用户输入触发上游抓取；
- CORS 使用 allowlist；
- WebSocket 第一版不接受任意 command payload；
- provider HTTP response 一律视为不可信输入并校验；
- 日志不得打印 credentials 或 connection URL 中的密码。

## 完成标准

M5 在以下条件全部满足时视为完成：

1. collector 可持续采集配置 symbol，并在单 symbol 临时失败后恢复；
2. Redis 保存 latest quote 和 collector heartbeat；
3. REST 能读取 current/stale latest state 并暴露明确 readiness；
4. WebSocket 连接时 bootstrap latest state，随后收到实时更新；
5. Dashboard 可显示 live/reconnecting/stale/static 状态；
6. live service 不可用时 Dashboard 仍正常使用现有静态页面；
7. provider、Redis、API 和 frontend 仅通过本文冻结接口/contract 耦合；
8. 默认单元测试不要求公网或真实 Redis；
9. integration 环境可使用真实 Redis 验证完整链路；
10. 所有实现通过独立 worktree/PR 合入，没有多个 agent 共用 branch/worktree；
11. 根 Python tests、market-data-service tests、frontend tests/build 和 foundation check 通过；
12. roadmap 不再把 collector、Redis、API、WebSocket 和前端实时模式标记为未实现，但 M6 cutover 继续保持独立阶段。
