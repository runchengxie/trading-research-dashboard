# 本地 A 股 daily-clean 数据契约

本项目的首个真实数据接入使用本机 market-data-platform 中的稳定读取路径：

```text
~/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_20150101_20260824_daily_clean
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
- 板块退潮 gate 使用数据平台生成的 ETF 行业复合日线 `sector_close`。行业成员历史只负责
  将股票按日期连接到 SW2021 L3，再通过审计后的代理映射连接到复合上下文。

因此 `niu-men-experiments` 的输出应称为“单证券、当前数据契约下的研究比较”，
而不是策略已验证的历史业绩。

## 全市场研究前的验证

`validate_research_inputs` 会检查 daily-clean 文件覆盖、点时股票池主键、行业区间
覆盖和市场上下文的时间范围。全市场研究应先运行这项检查，并将市场数据截断到与
股票池共同覆盖的最后一个交易日。当前研究使用 2015-01-05 至 2026-08-24 的日线资产。

行业 ETF 日线和复权因子已经覆盖 2015-01-05 至 2026-08-24。扩展映射由
`scripts/audit_etf_industry_mapping.py` 生成，产物包括：

- `etf_industry_mapping_candidates_expanded_20260825.csv`：有明确行业基准和可用历史的候选基金；
- `sw2021_l3_etf_mapping_audit_20260825.csv`：逐个 SW2021 L3 行业的规则、置信度和覆盖审计；
- `industry_etf_context_composite_expanded_20260825.parquet`：28 个行业代理的日线复合上下文。

映射覆盖 6688/7780 条行业变更记录和 5258/5851 只股票。高置信度规则覆盖较低，扩展结果
包含中等置信度的名称规则，因此全市场报告必须同时查看映射置信度和未覆盖清单。

使用 `scripts/run_industry_context_oos.py` 可以重跑点时股票池下的滚动样本外对照。参数
`--mapping-confidence expanded` 使用高、中置信度的全部已映射行业，`high` 只使用高置信度
行业。两种模式都会固定输出 NML 基线、去价格量能过滤、普通 20 日突破、63 日收益趋势
gate、板块退潮过滤和买入持有六个变体。

2026-08-25 的扩展映射报告评估 3808 只股票，1375 只因 `sector_ma60` 预热后不足 1008
根 bar 被跳过。高置信度报告评估 2229 只股票，1109 只因相同原因跳过。跳过样本不应被
当作收益结果，也不能通过缩短预热期来补齐。完整报告路径和参数快照见
`artifacts/etf-industry-context-20260825/manifest.json`。
