# 行情与图表导出能力

本文说明当前可用的行情和图表能力。服务的详细配置见 [`apps/market-data-service/README.md`](../../apps/market-data-service/README.md)。

## 当前已经实现

### 行情数据生成

Dashboard 可以通过 AKShare、Tushare、本地运行时缓存和 ETF Parquet 数据生成静态行情快照。生成结果写入：

```text
apps/dashboard/web/public/data.json
```

该文件包含股票或 ETF 的日线、分时、指标和关键价位。它经过校验后随 Web 应用部署，浏览器打开页面时读取这份 JSON。

当前系统支持日线研究和上一交易日分时展示，也支持在生成数据时使用数据源回退和按交易日隔离的分时缓存。

### 图表图片导出

图表导出已经实现。脚本位于：

```text
apps/dashboard/web/scripts/export-charts.mjs
```

脚本使用 Playwright 打开已经构建的 React 页面，截取 ECharts 渲染结果。因此网页和 PNG 共用同一套图表逻辑，不需要维护第二套 Python 绘图代码。

本地导出：

```bash
cd apps/dashboard/web
npx playwright install chromium
pnpm build
pnpm export:charts
```

从线上 Worker 导出：

```bash
cd apps/dashboard/web
pnpm export:charts -- \
  --url https://trading-research-dashboard.xiaowang01.workers.dev/ \
  --output /var/lib/trading-research/charts \
  --theme light
```

导出结果包含 PNG 和 `manifest.json`。manifest 使用 `trading_research.chart_export.v1`，记录行情日期、导出时间、来源地址、主题和图片文件列表。Hermes Agent、cron 或消息机器人可以先读取 manifest，再决定是否推送当天的图片。

完整参数和 cron 示例见 [输出文件与目录结构](../../apps/dashboard/docs/outputs.md)。

## 实时行情服务

当前已提供 FastAPI 行情服务，支持 Alpaca 美股实时报价、美股日线和 1 分钟历史行情、WebSocket 推送，以及 Redis latest state/Pub/Sub/heartbeat 基础模块。Dashboard 仍以静态 `data.json` 作为首屏和降级数据。

当前运行时收尾工作：

- API、collector 和 WebSocket 是否全部使用 Redis，需以 M5 runtime wiring 的合入状态为准。
- Redis readiness、上游断线、重连和故障降级需要在真实运行环境验证。
- 服务不会把静态快照描述成实时数据，也不会让浏览器直接访问行情供应商。

## 相关文档

- [数据源与 ETF 接入](../../apps/dashboard/docs/data-sources.md)
- [输出文件与目录结构](../../apps/dashboard/docs/outputs.md)
- [前端说明](../../apps/dashboard/docs/web-frontend.md)
- [Cloudflare Workers 部署](../../apps/dashboard/docs/cloudflare-workers.md)
- [迁移路线图](../migration/README.md)
