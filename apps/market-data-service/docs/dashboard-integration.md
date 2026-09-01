# Dashboard 数据接入

Dashboard 的数据顺序如下：

1. 浏览器加载静态 `data.json`。
2. 如果配置了 `VITE_MARKET_DATA_URL`，页面请求行情服务的 `GET /healthz`，只用来判断服务状态。
3. 页面发现美股标的后，连接行情服务 WebSocket。
4. WebSocket 只更新当前价格、行情状态和 freshness。
5. 日线、1 分钟历史数据仍由 Dashboard 的 Python 数据层请求。
6. 服务或数据源不可用时，页面保留静态快照和本地缓存。

构建前端时设置：

```bash
export VITE_MARKET_DATA_URL="https://market-data.example.com"
```

该地址必须是服务 origin，不要填写 `/v1/stream` 路径。浏览器会根据 origin 自动使用对应的 `ws://` 或 `wss://` 协议。

如果 Dashboard 与 `VITE_MARKET_DATA_URL` 不同源，行情服务还需要允许 Dashboard 的浏览器 origin：

```bash
export MARKET_DATA_CORS_ORIGINS="https://trading-dashboard.example.com"
```

本地 Vite 开发通常使用：

```bash
export MARKET_DATA_CORS_ORIGINS="http://localhost:5173"
```

多个 origin 用逗号分隔。服务只接受显式的 `http://` / `https://` origin，并拒绝 `*`。

页面的数据状态文案按下面的规则显示：

- 未配置 `VITE_MARKET_DATA_URL`：`静态快照`
- `/healthz` 请求成功并通过 payload 校验：`行情服务在线`
- 已配置服务地址，但 health 请求、CORS 或 payload 校验失败：`静态快照 · 行情服务状态未知`

第三种状态只表示浏览器没有成功验证 health。它不等价于服务宕机，因为 WebSocket 仍可能正常连接并推送报价。

health 检查失败不会设置 Dashboard 的页面级错误状态，也不会阻止 `data.json` 和研究快照加载。行情服务的实时数据仍不会改写 Dashboard 的日线、分时和研究快照。这样可以把实时连接或 REST 服务故障限制在行情 overlay 与状态提示范围内。

## REST 与 OpenAPI 契约

前端的 `src/marketDataApi.ts` 集中处理行情 REST URL、HTTP 错误和运行时 payload 校验。目前提供 health 和 quote client；现有 WebSocket streaming 逻辑保持独立。

FastAPI REST endpoint 使用命名 response models。需要生成机器可读契约时，在 `apps/market-data-service` 执行：

```bash
uv run --locked python scripts/export_openapi.py /tmp/market-data-openapi.json
```

后续引入 OpenAPI-to-TypeScript codegen 时，应从该 schema 生成 client/types，并逐步替代手写 REST 类型；不要让 codegen 接管静态研究 snapshot 的独立 JSON Schema 契约。
