# 本地 A 股 daily-clean 数据契约

本项目的首个真实数据接入使用本机 market-data-platform 中的稳定读取路径：

```text
~/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest
```

该目录按证券代码保存 `data/<ts_code>.parquet`。加载器只读取一个明确指定的
证券文件，绝不通过文件名模糊匹配或把整个数据目录复制进策略仓库。

## 字段映射

| daily-clean 字段 | 策略字段 | 用途 |
| --- | --- | --- |
| `trade_date` | DataFrame index (`date`) | 升序交易日 |
| `adj_open/high/low/close` | `open/high/low/close` | 默认信号与回测价格 |
| `vol` | `volume` | 成交量过滤 |
| `amount` | `amount` | 可选成本代理 |

默认使用复权 OHLC，避免公司行为在价格图上制造不存在的突破或止损。`--unadjusted`
只能用于研究原始报价版本，不能与默认结果混为一谈。

TuShare 当前这份资产的 `vol` 单位为手、`amount` 单位为千元人民币。因此若调用
股票/ETF 成本代理，必须显式使用：

```python
cost_line_proxy(data, window=20, asset_class="stock", amount_scale=10)
```

这只是把“千元/手”转换为“元/股”；它不改变成本线只是价格代理、并非主力成本的
研究边界。

## 清洗与当前限制

- 加载器会删除 `is_suspended=True` 的 bar；不会前填停牌价来虚构可交易日。
- 它保留输入证券原有的上市起点，因此不同证券的回测区间可能不同。
- 标准对照实验目前未启用板块退潮、大盘量能或 regime gate：这些规则需要与证券
  日线严格按日期对齐的完整历史上下文。当前发现的 `index_daily_latest` 仅读取到
  最新截面，不能冒充完整历史指数序列。
- 本阶段只对明确指定的单证券做时间序列研究；尚未解决全市场选股时的幸存者偏差、
  成分股点时数据、涨跌停成交概率或组合容量问题。

因此 `niu-men-experiments` 的输出应称为“单证券、当前数据契约下的研究比较”，
而不是策略已验证的历史业绩。
