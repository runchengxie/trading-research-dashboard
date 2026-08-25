# Dashboard 研究快照契约

`niu-men-line-strategy` 继续负责研究计算和回测，Dashboard 只消费版本化 JSON 快照。这个边界避免前端重复实现 NML、行业上下文、滚动样本外和成交约束逻辑。

## 文件

- `schemas/research-snapshot.schema.json` 定义对外 JSON 契约。
- `scripts/export_dashboard_snapshot.py` 把全市场 OOS 产物压缩成前端可直接读取的快照。
- 推荐把输出文件复制或提交为 Dashboard 的 `web/public/research.json`。

当前契约版本是 `niu_men.research_snapshot.v1`。

## 输入

导出器以 `scripts/run_industry_context_oos.py` 生成的 JSON manifest 为主入口，并读取其中记录的 folds、summary 和 skips CSV。若产物被移动过，可通过 `--folds-csv`、`--summary-csv` 和 `--skips-csv` 显式覆盖路径。

可选的 `--research-manifest` 用于补充 ETF 行业映射覆盖率、上下文 ready/warmup 行数和原始数据截止日。当前 tracked manifest 是 `artifacts/etf-industry-context-20260825/manifest.json`。

## 示例

```bash
uv run python scripts/export_dashboard_snapshot.py \
  --oos-json /path/to/niu_men_industry_context_oos_full_market_expanded_20260825.json \
  --research-manifest artifacts/etf-industry-context-20260825/manifest.json \
  --output ../wu-t0-trading-dashboard/web/public/research.json
```

导出器不会把本机绝对目录写入公开快照，只保留资产文件名和语义来源。

## 快照内容

快照包含：

- 数据截止日、研究引擎和数据平台来源
- 行业映射置信度、映射行业数和可选覆盖率
- 请求、评估和跳过标的数，以及跳过原因
- 行业上下文 warmup 规则、最小 bar 数和 warmup 跳过数
- 六个固定策略变体的全 OOS 中位指标
- 按 `fold_id` 汇总的滚动结果
- 涨跌停开盘无法成交的聚合计数
- 覆盖数量对账、六变体完整性、fold key 唯一性和 OOS 非空检查

六个固定变体是：

1. `nml_baseline`
2. `nml_no_price_volume_filters`
3. `simple_20_day_breakout`
4. `nml_simple_trend_gate`
5. `nml_sector_retreat`
6. `buy_and_hold`

## `fold_id` 的解释限制

现有 OOS runner 对每只股票独立生成 walk-forward folds，所以同一个 `fold_id` 是每只股票内部的顺序编号，不保证对应相同的自然日区间。

因此 Dashboard 中按 `fold_id` 展示的滚动曲线只能理解为“第 N 个样本外窗口”的横截面摘要，不能当成统一的日历时间序列。若以后需要严格按时间比较，应在研究层新增统一日历窗口定义，再升级快照 schema，而不是让前端猜测日期对齐。

## 版本规则

前端必须按 `schemaVersion` 判断兼容性。新增可选展示字段时可以继续保持 v1；删除字段、改变字段含义或修改指标口径时应升级 schema 版本。
