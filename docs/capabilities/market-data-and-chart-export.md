# 行情与图表导出能力

本文说明当前已经可以使用的功能，以及仍处于 roadmap 阶段的实时行情计划。

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
npm run build
npm run export:charts
```

从线上 Worker 导出：

```bash
cd apps/dashboard/web
npm run export:charts -- \
  --url https://trading-research-dashboard.xiaowang01.workers.dev/ \
  --output /var/lib/trading-research/charts \
  --theme light
```

导出结果包含 PNG 和 `manifest.json`。manifest 使用 `trading_research.chart_export.v1`，记录行情日期、导出时间、来源地址、主题和图片文件列表。Hermes Agent、cron 或消息机器人可以先读取 manifest，再决定是否推送当天的图片。

完整参数和 cron 示例见 [输出文件与目录结构](../../apps/dashboard/docs/outputs.md)。

## 当前尚未实现

### 实时行情服务

当前项目没有常驻的实时行情服务，也没有 Redis、WebSocket 或 FastAPI 行情接口。网页不会直接连接行情供应商，生产 Worker 只发布已经提交并通过校验的静态 JSON。

当前可以生成行情快照，但这和实时行情服务属于不同层次：

- 已支持：运行 Python 命令生成日线、分时和指标快照。
- 已支持：Dashboard 展示已发布的静态快照。
- 尚未支持：按秒持续采集全市场行情并推送到浏览器。
- 尚未支持：统一的实时 `MarketDataProvider` 接口、Redis 状态层和 WebSocket 推送。
- 尚未支持：把 AKShare、东财网页接口或 TDX 作为带限频、重试和健康状态的长期服务运行。

### 实时行情 roadmap

后续可以按以下顺序建设：

1. 定义统一的 Quote、MarketStatus、Health 和 timestamp 契约。
2. 实现可替换的数据源适配器，先接入 AKShare 或东财快照，再评估 TDX 作为重点标的补充来源。
3. 增加单独的行情采集进程和限频、重试、来源切换、数据新鲜度判断。
4. 用 Redis 保存最新状态，按需要异步保存历史数据。
5. 通过 FastAPI 和 WebSocket 为 Dashboard 提供实时数据。
6. 在实时服务稳定后，再让前端增加实时模式，并继续保留静态快照作为降级入口。

实时行情服务属于后续独立阶段。当前不应把静态 `data.json` 描述成实时 API，也不应让前端直接依赖网页内部接口。

## 相关文档

- [数据源与 ETF 接入](../../apps/dashboard/docs/data-sources.md)
- [输出文件与目录结构](../../apps/dashboard/docs/outputs.md)
- [前端说明](../../apps/dashboard/docs/web-frontend.md)
- [Cloudflare Workers 部署](../../apps/dashboard/docs/cloudflare-workers.md)
- [迁移路线图](../migration/README.md)
