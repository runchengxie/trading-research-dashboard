# Dashboard 数据接入

Dashboard 的数据顺序如下：

1. 浏览器加载静态 `data.json`。
2. 页面发现美股标的后，连接行情服务 WebSocket。
3. WebSocket 只更新当前价格、行情状态和 freshness。
4. 日线、1 分钟历史数据仍由 Dashboard 的 Python 数据层请求。
5. 服务或数据源不可用时，页面保留静态快照和本地缓存。

构建前端时设置：

```bash
export VITE_MARKET_DATA_URL="https://market-data.example.com"
```

该地址必须是服务 origin，不要填写 `/v1/stream` 路径。浏览器会根据 origin 自动使用对应的 `ws://` 或 `wss://` 协议。

行情服务的实时数据不会改写 Dashboard 的日线、分时和研究快照。这样可以把实时连接故障限制在价格 overlay 范围内。
