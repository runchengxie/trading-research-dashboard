# 输出文件与目录结构

## 目录结构

```text
.
├── astock_tech.py
├── web/
│   ├── public/
│   │   └── data.json
│   ├── src/
│   ├── package.json
│   ├── vite.config.ts
│   └── dist/
├── backtest/
│   └── rbreaker.py
├── tests/
├── docs/
│   ├── indicators.md
│   ├── configuration.md
│   ├── backtest.md
│   ├── outputs.md
│   └── troubleshooting.md
├── .github/
│   └── workflows/
│       └── report.yml
├── out/
│   └── indicators/
└── pyproject.toml
```

## 结构化数据

* 加 `--json <path>` 参数，脚本把每只股票的计算结果写成结构化 JSON，供前端 SPA 渲染
* 典型用法：`uv run python astock_tech.py --json web/public/data.json`
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

## GitHub Actions 定时任务

`.github/workflows/report.yml` 在每个工作日开盘前（北京时间约 09:00）自动跑一次：

1. 用 uv 装依赖
2. 运行 `astock_tech.py --json web/public/data.json` 生成数据
3. 在 `web/` 下 `npm ci` 加 `npm run build`
4. 把 `web/dist/` 发布到 Cloudflare Pages

akshare 从 CI 的海外环境访问可能不稳定，生成步骤设了 `continue-on-error`，失败时不会覆盖已有站点。需要手动触发时可在 GitHub 的 Actions 页点击 Run workflow。

## Cloudflare Pages 部署

站点托管在 Cloudflare Pages。在仓库设置里配置以下项后，定时任务会自动多出一步 `wrangler pages deploy`：

* `secrets.CLOUDFLARE_API_TOKEN`，Cloudflare API Token，需 `Account > Cloudflare Pages > Edit` 权限
* `vars.CLOUDFLARE_ACCOUNT_ID`，Cloudflare 账户 ID
* `vars.CF_PAGES_PROJECT`，Pages 项目名称，留空则跳过 Cloudflare 部署

部署步骤同样受 `continue-on-error` 保护：数据生成失败时不覆盖线上站点。首次运行会自动创建对应的 Pages 项目。
