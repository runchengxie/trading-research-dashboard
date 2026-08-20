# T+0 交易指标与图表生成

一个给 A 股 T+0（日内）交易做准备的 Python 工具。它能自动拉取行情、算出当天要用到的指标，再生成一份图表和 Excel 仪表盘，让你开盘前就清楚每只股票的支撑位、压力位、波动区间和该用哪种打法。

它同时是整套 T+0 交易体系的基准仓库，整合了两个兄弟项目的功能，详见下方「功能来源」和 `docs/` 目录。

## 它能做什么

* 自动拉取日线和分时数据，不用手动整理
* 算出常用日内指标：20 日 ATR、VWAP、开盘区间 ORB、聚类支撑阻力
* 自动判断股票当前适合趋势跟踪还是均值回归
* 生成一张带使用说明的图表，以及一份 Excel 交易仪表盘

## 快速开始

用 uv 安装依赖并运行：

```bash
uv sync
uv run python astock_tech.py
```

跑完会在 `out/` 目录下看到：

* `out/indicators/` 里的 Excel 仪表盘

图表不再由 Python 生成图片，改由 `web/` 下的前端在浏览器里渲染。

想指定股票或换个输出目录，可以带参数：

```bash
uv run python astock_tech.py --codes sh600199,sz000001 --output-root out
```

完整的命令行参数和配置方法见 [配置说明](docs/configuration.md)。

## 生成前端数据

加 `--json` 会把每只股票的计算结果写成结构化 JSON，供 `web/` 下的 React 前端渲染（图表不再由 Python 生成 PNG）：

```bash
uv run python astock_tech.py --json web/public/data.json
cd web && npm install && npm run dev
```

本地开发预览地址 `http://localhost:5173`。

要做一次本地生产构建（生成静态 `web/dist/`）然后起服务器自测：

```bash
cd web && npm run build && npm run preview
```

每日北京时间交易开盘前由 GitHub Actions 自动跑一次：拉数据 → 算指标 → 重新生成 `web/public/data.json` → 构建前端 → 推送到 Cloudflare Pages。生成的文件结构见 [输出文件与目录结构](docs/outputs.md)。

## 在线访问

线上站点托管在 Cloudflare Pages：[https://t0-trading-dashboard.pages.dev/](https://t0-trading-dashboard.pages.dev/)。

部署由 `.github/workflows/report.yml` 完成，无需 `wrangler.toml`，走的是 `wrangler pages deploy web/dist` 直推静态产物的模式。CF 上的项目名由仓库变量 `CF_PAGES_PROJECT` 决定，访问 token 走 `CLOUDFLARE_API_TOKEN` secret。

前端支持浅色 / 深色主题切换（默认跟随系统，右上角按钮可在「浅色 / 深色 / 跟随系统」三态间循环），并按研报风做了适度的卡片排版优化。

前端改动的工作流：

* `web/src/styles.css` 是全部 token 来源（含 dark mode 覆盖块）
* `web/src/theme.ts` 是图表配色与 `useResolvedTheme` hook
* `web/src/App.tsx` 把 `resolved` 透传给两个 chart 子组件，并写 `<html data-theme>`
* `web/index.html` 在 React 挂载前同步 `data-theme`，避免主题闪烁

自部署或 fork 时，需要在 GitHub 仓库 Settings → Secrets and variables → Actions 里配：

* `CLOUDFLARE_API_TOKEN`：Cloudflare 控制台 → My Profile → API Tokens，建一个有 Pages Edit 权限的 token
* `CF_PAGES_PROJECT`：你的 Pages 项目名（决定线上 `<project>.pages.dev` 子域）

## 指标概览

简单说，这份工具围绕这几个指标转：

| 指标 | 一句话说明 |
| --- | --- |
| ATR | 日波动空间，用来定触发阈值和止损范围 |
| VWAP | 当日成交均价，均值回归策略的参考线 |
| ORB | 开盘前 15 分钟的高低点，突破就追 |
| KMeans 聚类 | 把历史价格聚出支撑、阻力和关键价位 |

每个指标怎么算、怎么用，看 [指标与逻辑](docs/indicators.md)。

## 回测

仓库里还有一个 R-Breaker 日内策略回测模块，用来验证策略参数。它是可选的，需要单独装依赖，详细用法看 [回测模块](docs/backtest.md)。

## 功能来源

本项目是 T+0 交易体系的基准项目，整合了以下兄弟项目的功能：

| 来源项目 | 迁移内容 | 落点 |
| --- | --- | --- |
| `wu-t0-trading-assitant` | 按股票覆盖 `vwap_dev_k` 与 `roll_ratio` 的配置机制 | `astock_tech.py` |
| `wu-intraday-strategy` | R-Breaker 回测模块，含 akshare 与 tushare 双数据源、参数优化、样本内外测试 | `backtest/rbreaker.py` |

原项目均保留并标记为已转移，不再单独迭代。

## 测试

```bash
uv run pytest
```

测试覆盖脚本与回测模块的导入和命令行帮助信息。

## 文档目录

* [指标与逻辑](docs/indicators.md)，各指标的计算与用法
* [配置说明](docs/configuration.md)，股票池与命令行参数
* [回测模块](docs/backtest.md)，R-Breaker 策略回测
* [输出文件与目录结构](docs/outputs.md)，生成的文件都在哪
* [常见问题与排错](docs/troubleshooting.md)，遇到问题先看这里

## 免责声明

本项目仅用于策略研究与学习，历史回测不能保证未来收益。任何基于本工具做出的交易决策与后果，由使用者自行承担。
