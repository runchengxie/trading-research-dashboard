# Dashboard 研究快照契约

`niu-men-line-strategy` 继续负责研究计算和回测，Dashboard 只消费版本化 JSON 快照。这个边界避免前端重复实现 NML、行业上下文、滚动样本外和成交约束逻辑。

## 文件

- `schemas/research-snapshot.schema.json` 定义对外 JSON 契约。
- `scripts/export_dashboard_snapshot.py` 把全市场 OOS 产物压缩成前端可直接读取的快照。
- 推荐把输出文件复制或提交为 Dashboard 的 `web/public/research.json`。

当前契约版本是 `niu_men.research_snapshot.v2`。历史 v1 快照仍可作为历史产物保留，Dashboard 在迁移期同时兼容 v1 和 v2。

## 输入

导出器以 `scripts/run_industry_context_oos.py` 生成的 JSON manifest 为主入口，并读取其中记录的 folds、summary 和 skips CSV。若产物被移动过，可通过 `--folds-csv`、`--summary-csv` 和 `--skips-csv` 显式覆盖路径。

OOS runner 在运行时把 `research_commit` 写入 manifest。默认值来自当次研究运行所在仓库的 HEAD，也可以通过 `--research-commit` 显式提供。快照导出器只透传 OOS manifest 中记录的 commit，不会用导出时的仓库 HEAD 猜测研究来源。

可选的 `--research-manifest` 用于补充 ETF 行业映射覆盖率、上下文 ready/warmup 行数、原始数据截止日、manifest schema 和 manifest 生成时间。当前 tracked manifest 是 `artifacts/etf-industry-context-20260825/manifest.json`。

## 示例

```bash
uv run python scripts/export_dashboard_snapshot.py \
  --oos-json /path/to/niu_men_industry_context_oos_full_market_expanded_20260825.json \
  --research-manifest artifacts/etf-industry-context-20260825/manifest.json \
  --output ../wu-t0-trading-dashboard/web/public/research.json
```

测试或可复现发布可额外传入 `--snapshot-generated-at 2026-08-25T10:15:00Z`。正常发布不传该参数，导出器会记录实际 UTC 生成时间。

导出器不会把本机绝对目录写入公开快照，只保留资产文件名和语义来源。

## 时间与来源语义

v2 明确区分三个时间概念：

- `generatedAt` 是 `research.json` 的实际导出时间。
- `source.oosGeneratedAt` 是 OOS 研究运行日期。
- `source.dataDate` 是研究所用底层行情数据的截止日。

来源追踪还包括：

- `source.researchCommit`，研究运行时记录的 `niu-men-line-strategy` commit。
- `source.dataPlatformManifest.schemaVersion`，数据平台 manifest 的 schema 版本。
- `source.dataPlatformManifest.generatedAt`，该 manifest 的生成时间。
- `source.oosSchemaVersion`，OOS 结果契约版本。

历史 OOS manifest 没有这些 provenance 字段时，导出器会输出 `null`，并把 `quality.checks.provenanceComplete` 置为 `false`，同时把质量状态降为 `warning`。不会制造看似可信的替代值。

## 快照内容

快照包含：

- 数据截止日、研究引擎、研究 commit、数据平台 manifest 和 OOS 来源
- 行业映射置信度、映射行业数和可选覆盖率
- 请求、评估和跳过标的数，以及跳过原因
- 行业上下文 warmup 规则、最小 bar 数和 warmup 跳过数
- 六个固定策略变体的全 OOS 中位指标
- 按 `fold_id` 汇总的滚动结果
- 涨跌停开盘无法成交的聚合计数
- 覆盖数量对账、六变体完整性、fold key 唯一性、OOS 非空和 provenance 完整性检查

六个固定变体是：

1. `nml_baseline`
2. `nml_no_price_volume_filters`
3. `simple_20_day_breakout`
4. `nml_simple_trend_gate`
5. `nml_sector_retreat`
6. `buy_and_hold`

## `fold_id` 的解释限制

现有 OOS runner 对每只股票独立生成 walk-forward folds，所以同一个 `fold_id` 是每只股票内部的顺序编号，不保证对应相同的自然日区间。

因此 Dashboard 中按 `fold_id` 展示的滚动曲线只能理解为第 N 个样本外窗口的横截面摘要，不能当成统一的日历时间序列。若以后需要严格按时间比较，应在研究层新增统一日历窗口定义，再升级快照 schema，避免让前端猜测日期对齐。

## 版本规则

前端必须按 `schemaVersion` 判断兼容性。新增字段且保持含义兼容时可以继续保持 v2。删除字段、改变字段含义或修改指标口径时应再次升级 schema 版本。
