# 数据源与 ETF 接入

行情访问的既有 A 股/ETF 实现收口在 `src/trading_research/data/data_sources.py`。跨市场入口使用 `src/trading_research/data/market_compat.py`：CN 请求继续委托既有实现，HK 请求进入独立兼容适配层。指标层只接收规范化后的 DataFrame，不直接依赖 AKShare、Tushare 或本地 Parquet 的原始字段。

## 支持的证券类型

当前支持：

```text
stock
etf
```

`instrument_type` 为空时按 `stock` 处理。

推荐代码格式：

```text
A 股股票：sh600199、sz000001、600199.SH
ETF：510050.SH、159915.SZ
港股：hk00700、00700.HK
美股实时标识：us:AAPL、AAPL.US
```

兼容层会从带市场前缀/后缀的代码识别 CN/HK/US。没有市场信息的历史六位 A 股代码仍按 CN 处理。美股裸 ticker 只在 US-aware 的 market-data-service API 中接受，Dashboard 历史生成器不会猜测裸 ticker 的市场。

## 市场元数据

兼容层提供统一 market profile：

| Market | Currency | Timezone | Live provider |
| --- | --- | --- | --- |
| CN | CNY | `Asia/Shanghai` | - |
| HK | HKD | `Asia/Hong_Kong` | - |
| US | USD | `America/New_York` | Alpaca |

生成的 Dashboard payload 会为 CN/HK 写入 `market`、`currency`、`timezone`。前端把这些字段视为 optional，因此旧 `data.json` 仍可读取。

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

A 股读取顺序：

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

港股不复用 A 股交易日历选择上一交易日。`astock_tech` 会从港股自身日线日期中选择严格早于当天的最近日期，避免两地节假日不一致时把错误日期交给港股分钟接口。

## 股票日线

A 股读取顺序：

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

## 港股兼容层

港股通过 `trading_research.data.market_compat` 接入。CN 分支仍委托旧 `data_sources`，因此 A 股/ETF 的 provider 顺序和函数调用签名不改变。

示例：

```python
from trading_research.data import market_compat

profile = market_compat.market_profile("HK")
assert profile.currency == "HKD"
assert profile.timezone == "Asia/Hong_Kong"

daily = market_compat.fetch_daily(
    "00700.HK",
    "20260801",
    "20260826",
    market="HK",
)

intraday = market_compat.fetch_intraday(
    "hk00700",
    "2026-08-26",
    market="HK",
)
```

港股日线通过 AKShare `stock_hk_hist` 获取前复权数据，并转换为统一日线字段。失败时回退到现有 runtime daily cache。

港股分钟通过 AKShare `stock_hk_hist_min_em` 获取，目标时间窗口为 09:30-16:00，并转换为 `time/price/volume`。该接口属于延迟兼容数据，不能当作真正的 live quote 或标记为实时。失败时回退到目标交易日对应的 runtime intraday cache。

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

## 美股 Alpaca 实时层

美股实时行情由 `apps/market-data-service` 在服务端接入 Alpaca。浏览器不直接持有或使用 Alpaca credentials。

服务端环境变量：

```bash
export APCA_API_KEY_ID="..."
export APCA_API_SECRET_KEY="..."
export ALPACA_DATA_FEED="iex"
export MARKET_DATA_SYMBOLS="AAPL.US,MSFT.US"
export MARKET_DATA_QUOTE_MAX_AGE_SECONDS="15"
```

`ALPACA_DATA_FEED` 支持 `iex`、`sip`、`delayed_sip`。IEX/SIP 返回 `status="live"`，`delayed_sip` 明确返回 `status="delayed"`；延迟行情不会冒充实时行情。

market-data-service 提供：

```text
GET /healthz
GET /v1/quotes/AAPL.US
WS  /v1/stream?symbols=AAPL,MSFT
```

前端构建时只配置自己的行情服务地址：

```bash
export VITE_MARKET_DATA_URL="https://market-data.example.com"
```

`VITE_MARKET_DATA_URL` 必须是绝对 HTTP/HTTPS origin。SPA 先加载静态 `data.json`，若快照里存在 US instrument，再建立 WebSocket 并只覆盖当前显示价格与实时状态。`daily`、`intraday` 和研究快照不被实时 tick 修改。连接断开后已有 live quote 标记为 stale，显示逻辑回退到静态价格并自动重连。

Alpaca API key 不得放入 `VITE_*`。Vite 环境变量会进入浏览器 bundle，把券商 key 放进去等价于公开发布，只是多绕了一层构建工具，事故并不会因此更有技术含量。

本阶段不把美股历史日线/分钟线全面迁移到 Alpaca。`market_compat` 的 US 历史入口会明确报错，避免把实时 tick 误当成完整历史 provider。

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
│   ├── 510050.SH.csv
│   └── 00700.HK.csv
└── intraday/
    ├── sh600199/
    │   └── 20260825.csv
    ├── 510050.SH/
    │   └── 20260825.csv
    └── 00700.HK/
        └── 20260826.csv
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

## 港股推荐工作流

在 `STOCK_CONFIG` 中使用带市场信息的港股代码：

```python
STOCK_CONFIG = {
    "00700.HK": {
        "name": "腾讯控股",
        "instrument_type": "stock",
    },
}
```

生成器通过 `market_compat` 自动识别 HK，并输出 `market=HK`、`currency=HKD`、`timezone=Asia/Hong_Kong`。

## 与 `etf-minute-fetcher` 的边界

`etf-minute-fetcher` 继续作为独立基础设施维护，也没有以 submodule 方式进入当前 monorepo。Dashboard 消费它的稳定目录和字段契约，不负责自动启动 fetcher，也不复制它的分钟数据抓取和归档实现。

如果以后两个项目需要频繁同步修改，可以再评估把稳定的数据访问协议抽进共享 package。当前先保持接口清楚和独立测试能力。
