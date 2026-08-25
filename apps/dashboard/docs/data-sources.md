# 数据源与 ETF 接入

本项目的数据层统一放在 `data_sources.py`。指标计算只依赖稳定字段，不需要知道底层数据来自 AKShare、Tushare、本地 Parquet 还是缓存。

## 支持的证券类型

当前支持：

```text
stock
etf
```

旧配置没有 `instrument_type` 时默认按 `stock` 处理，因此原来的股票配置可以继续使用。

ETF 推荐使用 Tushare 风格代码：

```text
510050.SH
159915.SZ
```

股票仍兼容原来的 AKShare 风格：

```text
sh600199
sz000001
```

数据层也接受 `600199.SH` 这种写法。

## ETF 日线

ETF 日线通过 AKShare 的 `fund_etf_hist_em` 获取，并使用前复权数据，使 ATR、历史价格聚类和其他跨日指标尽量保持连续。

返回给指标层的字段固定为：

```text
date
open
close
high
low
volume
```

如果实时请求失败，会尝试读取 Dashboard 自己在 `data/raw/daily/` 保存的 CSV 快照。

## ETF 1 分钟数据

ETF 分钟数据优先读取兄弟项目 `etf-minute-fetcher` 生成的 Parquet。

默认目录：

```text
~/data/etf-minute-fetcher/minute/fund_min_1m
```

也可以通过环境变量覆盖：

```bash
export ETF_MINUTE_DATA_ROOT="$HOME/data/etf-minute-fetcher/minute/fund_min_1m"
```

目录契约：

```text
<root>/
  510050.SH/
    trade_date=20260824/
      part.parquet
```

Dashboard 读取以下字段：

```text
trade_time
close
vol
```

并转换成现有指标层使用的：

```text
trade_time -> time
close      -> price
vol        -> volume
```

因此现有 VWAP、ORB 和前端分时图逻辑不需要理解 fetcher 的内部实现。

## ETF 分钟数据优先级

ETF 分钟数据按下面顺序读取：

```text
etf-minute-fetcher 本地 Parquet
        ↓ 缺失或无效
AKShare fund_etf_hist_min_em 1 分钟
        ↓ 失败
Dashboard data/raw/intraday CSV 缓存
```

本地 Parquet 排在第一位，是为了让历史结果更稳定和更容易复现。AKShare 的 ETF 1 分钟接口只提供近期数据，不能替代长期本地归档。

Dashboard 不会自动启动 `etf-minute-fetcher`。两个项目通过稳定的数据目录契约连接，各自仍可独立运行。

## 推荐工作流

先用 fetcher 维护 ETF 分钟历史：

```bash
cd ../etf-minute-fetcher
uv run etf-min --symbols 510050.SH,159915.SZ
```

然后在 Dashboard 配置 ETF：

```python
STOCK_CONFIG = {
    "510050.SH": {
        "name": "上证50ETF",
        "instrument_type": "etf",
    },
}
```

再正常生成报告：

```bash
uv run python astock_tech.py
```

如果只想运行配置中的某一只 ETF：

```bash
uv run python astock_tech.py --codes 510050.SH
```

## 股票数据路径保持不变

股票仍按原来的顺序获取数据。

日线：

```text
AKShare 股票日线
    ↓
Tushare token2
    ↓
Tushare token1
    ↓
CSV 缓存
```

历史分时仍主要使用 Tushare，当前交易日可使用 AKShare 实时分时。

因此增加 ETF 支持不会改变已有股票配置的默认行为。

## 为什么暂时不直接把两个仓库合并

当前采用数据契约融合，而不是复制代码。

这样做有几个好处：

- fetcher 仍可独立服务其他研究项目
- Dashboard 不承担分钟接口重试和历史归档逻辑
- 回测可以复用同一批本地数据
- 两边可以独立测试和发布
- 以后如果真的需要 monorepo，可以在接口稳定后再迁移

如果未来两个项目几乎总是同步修改，再考虑把数据层抽成共享 package 或合并为 monorepo会更合理。
