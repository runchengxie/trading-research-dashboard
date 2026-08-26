# 数据源与 ETF 接入

行情访问统一收口在 `src/trading_research/data/data_sources.py`。指标层只接收规范化后的 DataFrame，不直接依赖 AKShare、Tushare 或本地 Parquet 的原始字段。

## 支持的证券类型

当前支持：

```text
stock
etf
```

`instrument_type` 为空时按 `stock` 处理。

推荐代码格式：

```text
股票：sh600199、sz000001、600199.SH
ETF：510050.SH、159915.SZ
```

数据层会把代码统一转换为需要的六位代码或 Tushare 风格代码。

## 规范字段

日线统一返回：

```text
date
open
close
high
low
volume
```

分时统一返回：

```text
time
price
volume
```

上层指标和前端无需知道这些字段来自哪个供应商。

## 交易日历

读取顺序：

```text
AKShare tool_trade_date_hist_sina
        ↓ 失败
Tushare TUSHARE_TOKEN_2
        ↓ 失败
Tushare TUSHARE_TOKEN
        ↓ 失败
本地 calendar 缓存
```

AKShare 的交易日历可能包含未来已经公布的开市日期，数据层会先截断到运行当天，再返回或写入缓存，避免报告日期跑到未来。

## 股票日线

读取顺序：

```text
AKShare stock_zh_a_hist
        ↓ 失败
Tushare TUSHARE_TOKEN_2
        ↓ 失败
Tushare TUSHARE_TOKEN
        ↓ 失败
本地 daily 缓存
```

AKShare 日线使用前复权数据。Tushare token 和专用 API URL 的配置方法见 [配置说明](configuration.md)。

## 股票分时

`ak.stock_intraday_em` 没有历史日期参数，只能可靠代表当前交易日。因此数据层只在请求日期等于当天时使用它。

历史交易日按下面顺序获取：

```text
Tushare TUSHARE_TOKEN_2
        ↓ 失败
Tushare TUSHARE_TOKEN
        ↓ 失败
目标交易日对应的本地 intraday 缓存
```

分时缓存按证券和交易日分开保存：

```text
data/raw/intraday/sh600199/20260825.csv
```

读取历史缓存时只会查找请求日期对应的文件。旧版 `data/raw/intraday/<code>.csv` 没有日期信息，维护版本不再把它作为历史请求的兜底，避免把其他交易日的分钟数据拼到目标日期上。

## ETF 日线

ETF 日线使用 AKShare `fund_etf_hist_em`，并请求前复权数据。

读取顺序：

```text
AKShare fund_etf_hist_em
        ↓ 失败
本地 daily 缓存
```

当前没有把股票用的 Tushare `daily` 接口套到 ETF 上，避免证券类型与供应商接口语义混淆。

## ETF 1 分钟数据

ETF 分钟历史优先使用独立项目 `etf-minute-fetcher` 的 Parquet 归档。

默认目录：

```text
~/data/etf-minute-fetcher/minute/fund_min_1m
```

覆盖环境变量：

```bash
export ETF_MINUTE_DATA_ROOT="$HOME/data/etf-minute-fetcher/minute/fund_min_1m"
```

分区示例：

```text
<root>/
└── 510050.SH/
    └── trade_date=20260824/
        └── part.parquet
```

Dashboard 读取：

```text
trade_time
close
vol
```

并转换为：

```text
trade_time -> time
close      -> price
vol        -> volume
```

ETF 分钟读取顺序：

```text
etf-minute-fetcher 本地 Parquet
        ↓ 缺失或无效
AKShare fund_etf_hist_min_em
        ↓ 失败
目标交易日对应的 Dashboard intraday 缓存
```

本地 Parquet 优先级最高，主要原因是长期历史更稳定，也更容易复现。AKShare 的 ETF 分钟接口更适合作为近期数据回退。

## 运行时缓存

缓存根目录为：

```text
data/raw/
```

典型结构：

```text
data/raw/
├── calendar/
│   └── sina.csv
├── daily/
│   ├── sh600199.csv
│   └── 510050.SH.csv
└── intraday/
    ├── sh600199/
    │   └── 20260825.csv
    └── 510050.SH/
        └── 20260825.csv
```

整个 `data/` 目录由 monorepo 根 `.gitignore` 排除，根级边界检查也拒绝跟踪 `data/raw`。缓存只用于运行时容错，不属于可复现源码资产。

## ETF 推荐工作流

先更新 ETF 分钟历史：

```bash
cd /path/to/etf-minute-fetcher
uv run etf-min --symbols 510050.SH,159915.SZ
```

再在 Dashboard 配置目标 ETF：

```python
STOCK_CONFIG = {
    "510050.SH": {
        "name": "上证50ETF",
        "instrument_type": "etf",
    },
}
```

运行 Dashboard：

```bash
uv run python -m trading_research.dashboard.astock_tech --codes 510050.SH
```

## 与 `etf-minute-fetcher` 的边界

`etf-minute-fetcher` 继续作为独立基础设施维护，也没有以 submodule 方式进入当前 monorepo。Dashboard 消费它的稳定目录和字段契约，不负责自动启动 fetcher，也不复制它的分钟数据抓取和归档实现。

如果以后两个项目需要频繁同步修改，可以再评估把稳定的数据访问协议抽进共享 package。当前先保持接口清楚和独立测试能力。
