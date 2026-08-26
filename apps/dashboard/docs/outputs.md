# 输出文件与目录结构

## 目录结构

```text
.
├── src/trading_research/
│   ├── dashboard/astock_tech.py
│   ├── data/data_sources.py
│   └── strategies/rbreaker.py
├── web/
│   ├── public/
│   │   └── data.json
│   ├── src/
│   ├── package.json
│   ├── vite.config.ts
│   └── dist/
├── tests/
├── docs/
│   ├── indicators.md
│   ├── configuration.md
│   ├── backtest.md
│   ├── outputs.md
│   └── troubleshooting.md
├── out/
│   └── indicators/
└── pyproject.toml
```

## 结构化数据

* 加 `--json <path>` 参数，脚本把每只股票的计算结果写成结构化 JSON，供前端 SPA 渲染
* 典型用法：`uv run python -m trading_research.dashboard.astock_tech --json web/public/data.json`
* 字段包含 code、name、tradingStyle、lastTradeDay、indicators、levels、daily、intraday、usageNotes
* 无分时数据时 intraday 为 null，vwap 等分时相关指标为 null

## Excel 仪表盘

* 文件名为 `out/indicators/T0交易指标_<最近交易日>.xlsx`
* Sheet `T0_Trading_Dashboard` 字段：
  * `股票代码` 和 `股票名称`
  * `指标/参数`
  * `计算值`
  * `使用说明`，由脚本内置字典自动映射，包含核心解释与风控提示

## 前端 SPA 报告

* 图表不再由 Python 生成 PNG，改由 `web/` 下的 React 加 TypeScript 加 ECharts 在浏览器端渲染
* 本地预览：`cd web && npm install && npm run dev`，前端会读取 `web/public/data.json`
* 构建产物在 `web/dist/`，包含原样拷贝的 `data.json`，可直接部署到任意静态托管

## 自动化边界

源仓库的 GitHub Actions 工作流未随应用导入。任何自动化由 monorepo 根目录的
集成配置负责；本应用生成静态数据时使用以下维护中的模块命令：

1. 用 uv 安装依赖
2. 运行 `uv run python -m trading_research.dashboard.astock_tech --json web/public/data.json`
3. 在 `web/` 下运行 `npm ci` 和 `npm run build`

akshare 在网络受限环境中可能不稳定；数据生成失败时不会生成新的静态数据文件。

## Cloudflare Workers 部署

站点使用 `apps/dashboard/wrangler.jsonc`，把 `web/dist/` 作为 Workers Static Assets 发布。部署集成在配置了 Cloudflare 账户变量时可执行 `wrangler deploy`。

仓库需要配置：

* `secrets.CLOUDFLARE_API_TOKEN`，具备 Workers 部署权限的 Cloudflare API Token
* `vars.CLOUDFLARE_ACCOUNT_ID`，Cloudflare 账户 ID
* `vars.CLOUDFLARE_PUBLIC_URL`，可选，部署后用于运行首页、`data.json` 和 `research.json` 烟雾检查

若 `CLOUDFLARE_ACCOUNT_ID` 留空，部署集成应跳过外部部署。更多本地命令见 [Cloudflare Workers 部署说明](cloudflare-workers.md)。
