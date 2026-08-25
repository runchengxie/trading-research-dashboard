# 本地 A 股 daily-clean 数据契约

本项目的首个真实数据接入使用本机 market-data-platform 中的稳定读取路径：

```text
~/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest
```

该目录按证券代码保存 `data/<ts_code>.parquet`。加载器读取指定证券文件，不扫描
模糊文件名，也不复制整个数据目录。

## 字段映射

| daily-clean 字段 | 策略字段 | 用途 |
| --- | --- | --- |
| `trade_date` | DataFrame index (`date`) | 升序交易日 |
| `adj_open/high/low/close` | `open/high/low/close` | 默认信号与回测价格 |
| `vol` | `volume` | 成交量过滤 |
| `amount` | `amount` | 可选成本代理 |
| `up_limit`、`down_limit` | `up_limit`、`down_limit` | 涨跌停成交约束 |

默认使用复权 OHLC，避免公司行为在价格图上制造不存在的突破或止损。`--unadjusted`
只能用于研究原始报价版本，不能与默认结果混为一谈。

TuShare 当前这份资产的 `vol` 单位为手、`amount` 单位为千元人民币。因此若调用
股票/ETF 成本代理，必须显式使用：

```python
cost_line_proxy(data, window=20, asset_class="stock", amount_scale=10)
```

该换算将千元/手转换为元/股。成本线仍是价格代理。

## 清洗与当前限制

- 加载器会删除 `is_suspended=True` 的 bar，也不会前填停牌价。
- 它保留输入证券原有的上市起点，因此不同证券的回测区间可能不同。
- 点时股票池使用月度快照，并从下一交易日生效。行业归属按生效日与失效日匹配。
- 宽基指数历史数据可提供 `market_volume` 代理。它不等同于全市场成交量。
- 日线数据无法提供涨跌停排队顺序和实际成交量。回测在开盘涨停时取消买入，在开盘
  跌停时延后卖出和止损。
- 板块退潮 gate 仍需行业日线 `sector_close`。当前本地资产只提供行业成员历史。

因此 `niu-men-experiments` 的输出应称为“单证券、当前数据契约下的研究比较”，
而不是策略已验证的历史业绩。
