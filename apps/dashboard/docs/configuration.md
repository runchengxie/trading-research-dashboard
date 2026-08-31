# 配置说明

Dashboard 的主要运行配置位于 `src/trading_research/dashboard/astock_tech.py`。维护中的模块入口为：

```bash
uv run python -m trading_research.dashboard.astock_tech
```

历史变量名 `STOCK_CONFIG` 继续保留，当前可以同时配置股票和 ETF。

## 证券池 `STOCK_CONFIG`

股票示例：

```python
STOCK_CONFIG = {
    "sz300246": {
        "name": "宝莱特",
        "instrument_type": "stock",
    },
}
```

ETF 示例：

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

`instrument_type` 当前支持：

```text
stock
etf
```

没有填写时按 `stock` 处理。

股票代码兼容 `sh600199`、`sz000001` 和 `600199.SH` 等形式。ETF 推荐使用 `510050.SH`、`159915.SZ`，这样可以直接对应 `etf-minute-fetcher` 的目录和 Parquet 分区。

当前默认证券为宝莱特 `sz300246`。

## VWAP 阈值覆盖

Dashboard 会根据交易风格选择 `vwap_dev_k`：

| 交易风格 | `vwap_dev_k` |
| --- | ---: |
| `Mean reversion + VWAP` | 0.4 |
| `Trend-following + Breakout` | 0.6 |
| 其他当前风格 | 0.5 |

需要针对单只证券覆盖时，可以在配置中直接指定：

```python
STOCK_CONFIG = {
    "510050.SH": {
        "name": "上证50ETF",
        "instrument_type": "etf",
        "vwap_dev_k": 0.4,
    },
}
```

历史代码中的 `roll_ratio` 当前没有进入 Dashboard 的输出或执行逻辑，维护版本已移除这段无消费者配置，避免继续形成无效参数。

## ETF 分钟数据目录

默认读取：

```text
~/data/etf-minute-fetcher/minute/fund_min_1m
```

需要覆盖时设置：

```bash
export ETF_MINUTE_DATA_ROOT="$HOME/data/etf-minute-fetcher/minute/fund_min_1m"
```

本地 `.envrc` 可以保存这个路径配置，但 `.envrc` 不提交到仓库。

详细目录契约见 [数据源与 ETF 接入](data-sources.md)。

## Tushare 配置

股票数据回退可以使用两个 Tushare token：

```text
TUSHARE_TOKEN_2
TUSHARE_TOKEN
```

优先顺序与上面一致。需要让某个 token 走独立 API 地址时可以配置：

```text
TUSHARE_API_URL_2
TUSHARE_API_URL
```

`TUSHARE_TOKEN_2` 未配置专用 URL 时默认使用 `https://your-tushare-proxy.example.com`。设置 `TUSHARE_API_URL_2` 可以显式覆盖该默认值；不会把 URL 或 token 写入仓库。

凭据只能放在本地环境变量或 GitHub secret 中，不写入源码、Markdown 或普通仓库变量。

## 指标参数

```python
ATR_PERIOD = 20
N_CLUSTERS = 5
OUTPUT_ROOT = "out"
```

- `ATR_PERIOD`：ATR 滚动周期
- `N_CLUSTERS`：KMeans 聚类中心数量
- `OUTPUT_ROOT`：Excel 等本地输出的根目录

## 数据区间

日线默认从 `20240101` 获取到运行当天。起始日期目前写在 `astock_tech.py` 的主流程中，若后续需要频繁调整，更适合提升为 CLI 或配置项。

ETF 1 分钟历史长度由 `etf-minute-fetcher` 的本地归档决定。AKShare 的 ETF 1 分钟接口主要承担近期数据回退，不适合作为长期历史存储。

## 命令行参数

```text
--codes         逗号分隔的配置代码，例如 sz300246,510050.SH
--output-root   输出根目录，默认 out
--json          结构化 JSON 输出路径，例如 web/public/data.json
```

`--codes` 只选择已经存在于 `STOCK_CONFIG` 的证券。传入未知代码时不会临时创建配置。
