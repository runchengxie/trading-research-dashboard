# Trading Research Platform · A股交易研究工作台

一个面向 A 股股票和 ETF 的交易研究工作台。它能自动拉取行情、计算日内指标，并把盘前概览、单标的工作区和版本化策略研究快照放进一个静态 Web 平台。

> **Monorepo boundary:** this Dashboard application is maintained under
> `apps/dashboard/`. Its source history is preserved here; root-level tooling
> and CI remain governed by the monorepo.

更完整的设计、配置、回测与部署细节都在 `docs/` 目录。

## 它能做什么

* 自动拉取股票和 ETF 日线、分时数据
* ETF 分钟数据优先读取 `etf-minute-fetcher` 归档的本地 Parquet
* 算出常用日内指标：20 日 ATR、VWAP、开盘区间 ORB、聚类支撑阻力
* 自动判断当前更接近趋势跟踪还是均值回归环境
* 生成 Excel 和 Trading Research Platform Web 工作台

## 快速开始

用 uv 安装依赖并运行：

```bash
uv sync
uv run python astock_tech.py
```

Python 业务代码的正式包路径是 `src/trading_research/`；仓库根目录的
`astock_tech.py`、`data_sources.py` 和 `backtest/rbreaker.py` 只作为兼容入口保留，
因此旧命令和现有自动化无需一次性改写。

跑完会在 `out/` 目录下看到：

* `out/indicators/` 里的 Excel 仪表盘

想指定股票或换个输出目录，可以带参数：

```bash
uv run python astock_tech.py --codes sz300246,sz000001 --output-root out
```

完整的命令行参数和配置方法见 [配置说明](docs/configuration.md)。

## 接入 ETF

先让 `etf-minute-fetcher` 归档 1 分钟数据：

```bash
cd ../etf-minute-fetcher
uv run etf-min --symbols 510050.SH
```

然后在 `STOCK_CONFIG` 中把目标标记为 ETF：

```python
"510050.SH": {
    "name": "上证50ETF",
    "instrument_type": "etf",
}
```

Dashboard 会优先读取 `~/data/etf-minute-fetcher/minute/fund_min_1m` 下的本地 Parquet。详细目录契约和回退逻辑见 [数据源与 ETF 接入](docs/data-sources.md)。

## 在线访问

线上站点当前地址为 [https://t0-trading-dashboard.pages.dev/](https://t0-trading-dashboard.pages.dev/)，每个交易日北京时间 09:00 自动更新。新的自部署配置使用 Cloudflare Workers Static Assets，详见 [输出文件与目录结构](docs/outputs.md)。

## 本地改前端

前端是一个 React 单页应用，图表在浏览器里渲染（不再由 Python 生成图片）。产品分为盘前概览、日内工作台和策略研究三个一级区域；研究区通过策略注册表承载牛门线和未来的 R-Breaker 快照。本地自测：

```bash
uv run python astock_tech.py --json web/public/data.json
cd web && npm install && npm run dev      # 开发预览 http://localhost:5173
# 或做生产构建后本地起服务器自测：
npm run build && npm run preview          # http://localhost:4173
```

前端架构、主题系统（浅色 / 深色 / 跟随系统三态）、防主题闪烁机制，见 [前端说明](docs/web-frontend.md)。

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
| `etf-minute-fetcher` | ETF 1 分钟 Parquet 数据契约与本地历史归档 | `data_sources.py` |

前两个历史项目已标记为转移。`etf-minute-fetcher` 仍保持独立迭代，Dashboard 只消费它的稳定数据目录契约。

## 测试

```bash
uv run pytest
```

测试覆盖脚本与回测模块的导入和命令行帮助信息。

## 文档目录

* [前端说明](docs/web-frontend.md)，三段式导航、策略 Tab、单标的工作区、前端技术栈与主题系统
* [指标与逻辑](docs/indicators.md)，各指标的计算与用法
* [配置说明](docs/configuration.md)，股票、ETF 与命令行参数
* [数据源与 ETF 接入](docs/data-sources.md)，本地 Parquet、ETF 日线和数据回退顺序
* [回测模块](docs/backtest.md)，R-Breaker 策略回测
* [输出文件与目录结构](docs/outputs.md)，生成的文件都在哪、CI 与部署配置
* [常见问题与排错](docs/troubleshooting.md)，遇到问题先看这里

## 免责声明

本项目仅用于策略研究与学习，历史回测不能保证未来收益。任何基于本工具做出的交易决策与后果，由使用者自行承担。
