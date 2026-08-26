# 输出文件与目录结构

Dashboard 同时维护可发布静态快照，并生成 Excel、前端构建产物和可选 PNG 图表。运行时缓存、Excel、`dist` 和图片导出不提交到版本库，经过审查的 Web 静态快照可以提交，作为稳定发布基线。

## 主要目录

```text
apps/dashboard/
├── src/trading_research/
│   ├── dashboard/astock_tech.py
│   ├── data/data_sources.py
│   └── strategies/rbreaker.py
├── web/
│   ├── public/
│   │   ├── data.json             # 必需、受版本控制的行情发布基线
│   │   └── research.json         # 可选、受版本控制的研究发布基线
│   ├── scripts/export-charts.mjs
│   ├── src/
│   ├── package.json
│   └── dist/                     # 前端构建产物，不提交
├── tests/
├── docs/
├── out/
│   └── indicators/               # Excel 输出，不提交
└── pyproject.toml

<monorepo-root>/
└── artifacts/
    └── charts/                    # PNG 图表导出，不提交
```

## `data.json` 行情快照

Dashboard 生成命令：

```bash
uv run python -m trading_research.dashboard.astock_tech \
  --json web/public/data.json
```

顶层字段包括：

```text
generatedAt
stocks
```

每只证券包含：

```text
code
name
instrumentType
tradingStyle
lastTradeDay
indicators
levels
daily
intraday
usageNotes
```

缺少分时数据时 `intraday` 为 `null`，`vwap`、`vwapDev`、ORB 等依赖分时数据的指标为空。`vwapDevThreshold` 只依赖 ATR 和交易风格，仍可以输出。

仓库保留一份经过验证的 `web/public/data.json`。更新行情快照时应在能够访问真实数据源或可靠本地缓存的环境中生成，再运行静态资产校验并通过 PR 审查。不要在无数据环境里用空 `stocks` 覆盖现有基线。

校验：

```bash
python scripts/validate_static_assets.py
```

缺少 `data.json`、JSON 损坏、`generatedAt` 无效或 `stocks` 为空都会让校验失败。

## `research.json` 研究快照

`web/public/research.json` 是可选研究基线。当前仓库可以提交经过审查的 Niu Men `research_snapshot.v2` 快照，用于生产展示。

Dashboard 在没有研究快照时仍能运行行情区域。若仓库中提交了 `research.json`，静态资产校验至少要求它是 JSON object，前端和部署后检查还会校验受支持 schema。

研究生产与更新流程见 [研究快照接入](research-snapshot.md)。

## Excel 指标表

默认文件名：

```text
out/indicators/T0交易指标_<最近交易日>.xlsx
```

Sheet 名为 `T0_Trading_Dashboard`，主要列包括：

- `股票代码`
- `股票名称`
- `指标/参数`
- `计算值`
- `使用说明`

Excel 是本地研究输出，不进入 Git。

## Web 构建产物

前端使用 React、TypeScript 和 ECharts。图表逻辑统一在浏览器端维护。

```bash
cd web
npm ci
npm test
npm run build
```

生产文件生成到：

```text
web/dist/
```

Vite 会把受版本控制的 `web/public/data.json` 和当前存在的 `research.json` 一起复制到 `dist/`。

## PNG 图表导出

图片导出通过 Playwright 截取已经渲染完成的 React 和 ECharts 组件，因此 PNG 与 Web 工作台使用同一套图表实现。

第一次使用时安装 Chromium：

```bash
cd web
npx playwright install chromium
```

### 从本地构建导出

先验证当前静态快照，再构建：

```bash
cd apps/dashboard
python scripts/validate_static_assets.py
cd web
npm run build
npm run export:charts
```

如果需要刷新行情，先在可用数据环境执行：

```bash
uv run python -m trading_research.dashboard.astock_tech \
  --json web/public/data.json
```

然后重新校验和构建。

`export:charts` 会自动启动临时 Vite preview，不需要另开后台服务器。

默认输出：

```text
<monorepo-root>/artifacts/charts/<数据日期>/
├── overview-<数据日期>.png
├── <证券代码>-workspace-<数据日期>.png
├── <证券代码>-daily-<数据日期>.png
├── <证券代码>-intraday-<数据日期>.png
└── manifest.json
```

没有分时数据的证券不会生成 `intraday` 图片。

### 从线上站点导出

可以直接读取已经部署的 Dashboard：

```bash
cd apps/dashboard/web
npm run export:charts -- \
  --url https://trading-research-dashboard.xiaowang01.workers.dev/ \
  --output /var/lib/trading-research/charts \
  --theme light
```

支持参数：

```text
--url       Dashboard 地址，省略时预览本地 dist
--output    输出根目录
--theme     light 或 dark
```

也支持环境变量：

```text
DASHBOARD_EXPORT_URL
DASHBOARD_EXPORT_DIR
DASHBOARD_EXPORT_THEME
```

### `manifest.json`

每次导出都会生成机器可读 manifest，schema 为：

```text
trading_research.chart_export.v1
```

示例：

```json
{
  "schemaVersion": "trading_research.chart_export.v1",
  "generatedAt": "2026-08-26",
  "exportedAt": "2026-08-26T12:00:00.000Z",
  "sourceUrl": "https://example.com/",
  "theme": "light",
  "images": [
    {
      "kind": "daily-chart",
      "code": "510050.SH",
      "name": "上证50ETF",
      "file": "510050.SH-daily-2026-08-26.png"
    }
  ]
}
```

Hermes Agent、消息机器人或其他自动化程序可以先读取 manifest，再决定发送哪些图片。

### cron 示例

生产 Worker 的行情快照完成更新和部署后，可以在 Linux 上配置：

```cron
15 18 * * 1-5 cd /path/to/a-share-trading-research/apps/dashboard/web && npm run export:charts -- --url https://trading-research-dashboard.xiaowang01.workers.dev/ --output /var/lib/trading-research/charts >> /var/log/trading-research-chart-export.log 2>&1
```

如果当天还没有发布新快照，图片会忠实反映线上当前版本，通常意味着仍是上一交易日数据。自动推送程序可以读取 `manifest.json.generatedAt` 判断是否符合预期日期。

## 运行时缓存

行情抓取过程的本地缓存位于：

```text
data/raw/
```

这些缓存与 `web/public/data.json` 发布快照职责不同，整个 `data/` 目录仍由根 `.gitignore` 排除。

日线缓存：

```text
data/raw/daily/<证券代码>.csv
```

分时缓存按交易日隔离：

```text
data/raw/intraday/<证券代码>/<YYYYMMDD>.csv
```

按交易日分区可以避免网络失败时把其他日期的分时数据误当成目标日期。

## 自动化与部署

monorepo 根目录维护两个手动 GitHub Actions workflow：

- `Monorepo foundation`：运行 Python 测试、Ruff、前端单元测试、生产构建和依赖审计
- `Deploy Dashboard`：验证仓库中的静态快照，运行前端测试和构建，再按配置部署 Cloudflare Workers，并可执行部署后 smoke check

部署需要：

- `secrets.CLOUDFLARE_API_TOKEN`
- `vars.CLOUDFLARE_ACCOUNT_ID`
- `vars.CLOUDFLARE_PUBLIC_URL`，可选，用于部署后检查

部署 workflow 不在 GitHub runner 上重新抓取行情。快照刷新应先在可靠数据环境完成并提交审查，再部署经过验证的基线。

详细说明见 [Cloudflare Workers 部署](cloudflare-workers.md)。
