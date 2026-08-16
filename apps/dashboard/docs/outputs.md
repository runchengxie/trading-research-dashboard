# 输出文件与目录结构

## 目录结构

```text
.
├── astock_tech.py
├── report.py
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
│   ├── charts/
│   ├── indicators/
│   └── site/
└── pyproject.toml
```

## 图表

* 路径为 `out/charts/<code>_<yyyymmdd>.png`
* 内容包含收盘价折线、聚类中心、支撑阻力、最近关键价、成交量，副标题为交易风格摘要

## Excel 仪表盘

* 文件名为 `out/indicators/T0交易指标_<最近交易日>.xlsx`
* Sheet `T0_Trading_Dashboard` 字段：
  * `股票代码` 和 `股票名称`
  * `指标/参数`
  * `计算值`
  * `使用说明`，由脚本内置字典自动映射，包含核心解释与风控提示
* Sheet `图表索引`，列出图表文件名与路径

## 静态 HTML 报告

* 加 `--report` 参数生成，输出到 `out/site/` 目录
* `index.html` 是入口，图表复制进同目录的 `charts/` 下，整体自包含，可直接部署到 GitHub Pages
* 也可以用 `--report-output` 指定输出目录

## GitHub Actions 定时任务

`.github/workflows/report.yml` 在每个工作日开盘前（北京时间约 09:00）自动跑一次：

1. 用 uv 装依赖
2. 运行 `astock_tech.py --report` 生成报告
3. 把 `out/site/` 发布到 gh-pages

akshare 从 CI 的海外环境访问可能不稳定，生成步骤设了 `continue-on-error`，失败时不会覆盖已有站点。需要手动触发时可在 GitHub 的 Actions 页点击 Run workflow。

## 可选：Cloudflare Pages 部署

除 GitHub Pages 外，报告也可发布到 Cloudflare Pages 作托管（GitHub Pages 仍保留作兜底）。在仓库设置里配置以下项后，定时任务会自动多出一步 `wrangler pages deploy`：

* `secrets.CLOUDFLARE_API_TOKEN`，Cloudflare API Token，需 `Account > Cloudflare Pages > Edit` 权限
* `vars.CLOUDFLARE_ACCOUNT_ID`，Cloudflare 账户 ID
* `vars.CF_PAGES_PROJECT`，Pages 项目名称，留空则跳过 Cloudflare 部署

部署步骤同样受 `continue-on-error` 保护：报告生成失败（无 `out/site/index.html`）时不覆盖线上站点。首次运行会自动创建对应的 Pages 项目。
