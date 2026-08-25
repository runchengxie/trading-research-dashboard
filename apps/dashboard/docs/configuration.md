# 配置说明

主要配置在 `src/trading_research/dashboard/astock_tech.py` 顶部参数区。仓库根目录的
`astock_tech.py` 是兼容入口。项目现在同时支持股票和 ETF，历史变量名 `STOCK_CONFIG`
保留用于兼容已有用法。

## 证券池 `STOCK_CONFIG`

股票配置：

```python
STOCK_CONFIG = {
    "sz300246": {
        "name": "宝莱特",
        "instrument_type": "stock",
    },
}
```

ETF 配置：

```python
STOCK_CONFIG = {
    "510050.SH": {
        "name": "上证50ETF",
        "instrument_type": "etf",
    },
    "159915.SZ": {
        "name": "创业板ETF",
        "instrument_type": "etf",
    },
}
```

`instrument_type` 支持：

```text
stock
etf
```

旧配置没有这个字段时默认按 `stock` 处理。

股票代码仍兼容 `sh600199`、`sz000001` 这种格式。当前默认标的是宝莱特 `sz300246`。ETF 推荐写成 `510050.SH`、`159915.SZ`，与 `etf-minute-fetcher` 的目录和 Parquet 数据保持一致。

每个证券配置还可以带 `vwap_dev_k` 和 `roll_ratio`，用于覆盖自动推导的 ATR 系数和仓位滚动比例。

```python
STOCK_CONFIG = {
    "510050.SH": {
        "name": "上证50ETF",
        "instrument_type": "etf",
        "vwap_dev_k": 0.4,
        "roll_ratio": 0.3,
    },
}
```

## ETF 分钟数据目录

Dashboard 默认从下面的位置读取 `etf-minute-fetcher` 保存的 1 分钟 Parquet：

```text
~/data/etf-minute-fetcher/minute/fund_min_1m
```

如果数据在其他目录，设置环境变量：

```bash
export ETF_MINUTE_DATA_ROOT="$HOME/data/etf-minute-fetcher/minute/fund_min_1m"
```

也可以把这行放进本地 `.envrc`。仓库提供了 `.envrc.example` 作为参考。

数据目录格式、字段映射和回退顺序见 [数据源与 ETF 接入](data-sources.md)。

## 其他参数

```python
ATR_PERIOD = 20
N_CLUSTERS = 5
OUTPUT_ROOT = "out"
```

`ATR_PERIOD` 控制 ATR 滚动周期，`N_CLUSTERS` 控制 KMeans 聚类中心数量，`OUTPUT_ROOT` 控制输出根目录。

## 数据区间

日线数据默认从 `20240101` 到脚本运行当天，可按需调整 `astock_tech.py` 中的起始日期。

ETF 1 分钟历史由 `etf-minute-fetcher` 本地归档决定。Dashboard 在线回退使用 AKShare ETF 分钟接口，只适合近期数据。

## 命令行参数

```text
--codes         逗号分隔的配置代码，例如 sz300246,510050.SH，默认使用 STOCK_CONFIG
--output-root   输出根目录，默认 out
--json          输出结构化 JSON 到指定路径，例如 web/public/data.json，供前端 SPA 使用
```

`--codes` 只会选择已经存在于 `STOCK_CONFIG` 中的项目，不会临时创建未知证券配置。
