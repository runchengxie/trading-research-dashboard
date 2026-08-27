# 港美股行情支持设计

## 目标

在保持现有 A 股与 ETF Dashboard 行为兼容的前提下：

1. 为港股增加 market-aware 兼容层，并通过 AKShare 接入港股历史日线和近期分钟线。
2. 为美股增加 Alpaca 实时行情支持，API key 只保存在服务端。
3. 保留现有静态 `data.json` 作为生产 fallback；实时行情属于增强层，实时服务不可用时 Dashboard 继续可用。

## 现状与约束

- `apps/dashboard` 原数据层只认识 A 股/ETF symbol 与 A 股交易日历。
- `apps/market-data-service` 已有 provider-neutral `Quote`、freshness、config 与 `MarketDataProvider` contract，但原 symbol 只支持 `sh/sz/bj`，尚无 collector/API。
- Dashboard Web 是静态 SPA，不能暴露 Alpaca credentials。
- 仓库不提交 credentials、raw market data 或机器专属路径。
- 旧 A 股 symbol、旧 `data.json` 和现有测试必须继续工作。
- 本阶段不引入 Redis；单实例内存 quote store 足够，后续可在不改 API contract 的前提下替换。

## Symbol 与市场模型

`market-data-service` 引入 `Market` 与 `Instrument`：

- CN：`sz300246`、`SZ.300246`、`300246.SZ` 规范为 `sz300246`。
- HK：`00700.HK`、`hk00700`、`HK.00700` 规范为 `hk00700`，provider symbol 为 `00700`。
- US：`AAPL.US`、`us:AAPL` 规范为 `us:AAPL`，provider symbol 为 `AAPL`。裸 `AAPL` 仅允许 US-aware 入口解析，避免和未知市场代码混淆。

Instrument 元数据包含 `market`、`symbol`、`provider_symbol`、`currency`、`timezone`：CN/CNY/Asia/Shanghai，HK/HKD/Asia/Hong_Kong，US/USD/America/New_York。

保留 `normalize_symbol(raw) -> str` 作为兼容入口，同时新增 `parse_instrument()` 返回完整元数据。

## 港股兼容层

实施时采用独立 `trading_research.data.market_compat` facade，而不直接扩写原有 560 多行 `data_sources.py`。这是有意的边界收敛：

- CN 请求直接委托现有 `data_sources`，保持 AKShare/Tushare/ETF fallback 顺序不变。
- HK 请求在 facade 内调用 `ak.stock_hk_hist()` 和 `ak.stock_hk_hist_min_em()`，再转换为现有统一 schema。
- `astock_tech` 只将数据层 import 切换到 facade，因此旧方法名继续可用。
- facade 可从 `00700.HK` / `hk00700` 自动识别 HK；旧无市场信息的代码默认 CN。
- HK 日线输出仍为 `date/open/close/high/low/volume`，分钟输出仍为 `time/price/volume`。
- 港股分钟数据明确作为延迟兼容来源，不声明为 live。
- HK provider 失败时继续使用 Dashboard 原有 runtime CSV cache。
- CN 继续用 A 股交易日历选择上一交易日；HK 从自身 daily 日期序列选择，避免两地节假日不一致造成错配。

`astock_tech` 输出新增 `market/currency/timezone`，同时把指标文本的价格单位按 CNY/HKD/USD 区分。字段为前端 optional contract，因此旧快照仍可读取。

## 美股 Alpaca 实时数据

`apps/market-data-service` 新增 Alpaca provider 与轻量 HTTP/WebSocket API：

- 依赖：`alpaca-py`、`fastapi`、`uvicorn`。
- 配置：`APCA_API_KEY_ID`、`APCA_API_SECRET_KEY`、`ALPACA_DATA_FEED`，feed 允许 `iex`、`sip`、`delayed_sip`。
- 使用 `alpaca.data.live.StockDataStream`。
- 一个服务进程维护一个共享 StockDataStream，不为每个浏览器创建 Alpaca 连接。
- `data_timeout=60` 用于检测连接仍存活但长期不再出数据的静默断流。
- trade event 转换为内部 `Quote` 并写入内存 `QuoteStore`。
- IEX/SIP quote 标 `live`；`delayed_sip` 明确标 `delayed`。
- `QuoteStore` 根据 `quote_max_age_seconds` 暴露 current/stale 状态。
- API：`GET /v1/quotes/{symbol}` 返回当前 quote/freshness；`WS /v1/stream?symbols=AAPL,MSFT` 将 store 中更新后的 quote 推给前端。
- 两个 credentials 都未设置时 collector 禁用但服务仍可启动；部分 credentials、非法 feed 或非 US symbol 属于配置错误并快速失败。

## Dashboard wire contract

现有 `StockData` 字段继续保留。新增字段均为 optional，确保旧 snapshot 可读取：

- `market?: 'CN' | 'HK' | 'US'`
- `currency?: 'CNY' | 'HKD' | 'USD'`
- `timezone?: string`
- `liveQuote?: { symbol, price, timestamp, source, status, freshness }`

Python snapshot generator 对其能处理的 CN/HK 配置输出 market/currency/timezone。US 历史日线/分钟线不在本阶段范围，因此 generator 不把 Alpaca realtime 伪装成完整历史 provider。

Web 前端读取绝对 `VITE_MARKET_DATA_URL`。若静态 snapshot 中存在 US instrument，则建立一个 WebSocket；收到 quote 后只覆盖当前显示价格/实时状态，不改写历史 daily/intraday 数组。连接失败时已有 live quote 标记 stale，展示逻辑回退到静态价格并自动重连。

## 错误与安全

- Alpaca credentials 只从服务端环境变量读取，不写入 JSON、日志或浏览器 bundle。
- `VITE_*` 只保存 market-data-service origin，不保存券商凭据。
- stale 与 delayed 是独立语义：延迟 feed 可以是 current，但仍必须显示 delayed。
- HK provider 异常继续使用现有 runtime cache 策略。
- symbol 无法识别时立即 `ValueError`，不做含糊市场猜测。

## 测试策略

遵循 TDD：

1. `market-data-service` symbol tests：CN 兼容、HK/US normalize、metadata、invalid cases。
2. Alpaca provider tests：feed 映射、trade 到 Quote 转换、delayed/live status、credentials/config validation；不依赖真实 Alpaca 网络。
3. QuoteStore/API tests：current/stale/missing、HTTP quote、WebSocket payload contract。
4. Dashboard compatibility tests：HK daily/minute adapter、cache、CN delegation。
5. Dashboard generator tests：market/currency/timezone，以及 HK 不复用 A 股交易日历。
6. Web tests：US detection、live overlay、URL construction、stale/static fallback。
7. 最终需要完整 Python tests、Ruff、前端 tests/build、`uv lock` 同步与 foundation checks。

## 非目标

- 不实现港股真正实时 streaming provider。
- 不把 US 历史行情全面迁移到 Alpaca；本阶段重点是实时 overlay。
- 不引入 Redis/Kafka/数据库。
- 不做下单、账户、portfolio 或交易 API。
- 不重写现有 A 股/ETF 数据链。

## 成功标准

- 现有 A 股/ETF 行为与旧 wire snapshot 向后兼容。
- HK symbol 可通过兼容 facade 生成历史/分钟 Dashboard 数据，币种和时区正确。
- HK 上一交易日由其自身 daily 日期决定，不依赖 A 股节假日。
- US symbol 可由服务端 Alpaca stream 更新实时 quote，credentials 不进入浏览器。
- IEX/SIP 与 delayed SIP 的 status 不混淆；stale quote 不冒充当前价。
- 实时服务停止时静态 Dashboard 继续正常显示。
- 所有新增和现有相关测试、lint、type/build/foundation 门槛通过后，PR 才可转为 ready。
