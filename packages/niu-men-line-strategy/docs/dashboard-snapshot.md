# Dashboard 研究快照契约

`niu-men-line-strategy` 继续负责研究计算和回测，Dashboard 只消费版本化 JSON 快照。这个边界避免前端重复实现 NML、行业上下文、滚动样本外和成交约束逻辑。

## 文件

- `schemas/research-snapshot.schema.json` 定义对外 JSON 契约。
- `scripts/export_dashboard_snapshot.py` 把全市场 OOS 产物压缩成前端可直接读取的快照。
- `scripts/publish_dashboard_snapshot.py` 是 CI 和本地发布使用的稳定入口，负责输入检查、v2 校验和原子写入。
- 推荐把输出文件复制或提交为 Dashboard 的 `web/public/research.json`。

当前契约版本是 `niu_men.research_snapshot.v2`。历史 v1 快照仍可作为历史产物保留，Dashboard 在迁移期同时兼容 v1 和 v2。

## 输入

导出器以 `scripts/run_industry_context_oos.py` 生成的 JSON manifest 为主入口，并读取其中记录的 folds、summary 和 skips CSV。若产物被移动过，可通过 `--folds-csv`、`--summary-csv` 和 `--skips-csv` 显式覆盖路径。

OOS runner 在运行时把 `research_commit` 写入 manifest。默认值来自当次研究运行所在仓库的 HEAD，也可以通过 `--research-commit` 显式提供。快照导出器只透传 OOS manifest 中记录的 commit，不会用导出时的仓库 HEAD 猜测研究来源。

可选的 `--research-manifest` 用于补充 ETF 行业映射覆盖率、上下文 ready/warmup 行数、原始数据截止日、manifest schema 和 manifest 生成时间。该文件应来自实际研究运行，研究产物不随当前代码包提交。

## 示例

```bash
uv run python scripts/export_dashboard_snapshot.py \
  --oos-json /path/to/niu_men_industry_context_oos_full_market_expanded_20260825.json \
  --research-manifest artifacts/etf-industry-context-20260825/manifest.json \
  --output ../wu-t0-trading-dashboard/web/public/research.json
```

测试或可复现发布可额外传入 `--snapshot-generated-at 2026-08-25T10:15:00Z`。正常发布不传该参数，导出器会记录实际 UTC 生成时间。

导出器不会把本机绝对目录写入公开快照，只保留资产文件名和语义来源。

## 发布命令与跨仓库 PR

发布时优先使用稳定入口：

```bash
uv run python scripts/publish_dashboard_snapshot.py \
  --oos-json /path/to/niu_men_industry_context_oos_full_market_expanded_20260825.json \
  --research-manifest artifacts/etf-industry-context-20260825/manifest.json \
  --output /tmp/research.json
```

发布命令在写文件前检查两个输入文件存在，调用现有 v2 exporter，拒绝非 v2 结果和空 OOS 记录，并通过临时文件原子替换输出。质量状态为 `warning` 的历史或 provenance 不完整快照仍然可以被真实发布，但不会被改写成 `pass`。

仓库中的 `.github/workflows/publish-dashboard-snapshot.yml` 提供跨仓库 PR handoff。它目前通过 `workflow_dispatch` 接收研究运行产物路径，因为完整 OOS CSV/JSON 不是本仓库的 tracked 文件；未来研究运行 workflow 可以复用同一发布步骤。运行前需要在 Niu Men 仓库配置 `DASHBOARD_REPOSITORY_TOKEN`，该 token 需要对 Dashboard 仓库具有创建分支和 Pull Request 的权限。

示例输入：

```text
oos_json: artifacts/oos-run/full-market.json
research_manifest: artifacts/data-platform/manifest.json
dashboard_repository: runchengxie/wu-t0-trading-dashboard
```

workflow 会生成并验证 `research.json`，复制到 Dashboard 的 `web/public/research.json`，然后打开一个 `automation/niu-men-dashboard-snapshot` 分支 PR。它不会直接推送 Dashboard `main`。如果输入缺失或快照校验失败，PR 步骤不会执行；Dashboard 继续使用仓库中上一次成功的快照或显示缺失状态。

## 契约资产同步

`schemas/research-snapshot.schema.json` 是 Niu Men 的规范 schema。契约 fixture 固定放在 `tests/fixtures/research_snapshot/`，包括：

1. `valid_v2.json`，结构完整且质量通过的 v2 快照。
2. `warning_v2.json`，来源追踪不完整且质量为 warning 的 v2 快照。
3. `invalid_missing_required.json`，缺少必填字段的非法样例。
4. `unsupported_version.json`，schema 版本不受支持的非法样例。

发布 workflow 会把 schema 和 fixture 一并复制到 Dashboard 的 reviewable PR：

```text
schemas/research-snapshot.schema.json
  -> Dashboard/schemas/research-snapshot.schema.json

tests/fixtures/research_snapshot/*.json
  -> Dashboard/tests/fixtures/research_snapshot/*.json
```

Niu Men 发布命令在写入输出前使用同一份 schema 校验快照。Dashboard 的 Web CI 再验证复制后的 schema、fixture 和 `web/public/research.json`。任一输入或契约校验失败时都不会创建 Dashboard PR。

在契约稳定阶段，Niu Men 和 Dashboard 仍然是两个独立的活动仓库。此次同步只改变可审查的发布资产，不把 Niu Men 的策略 Python 内部发布为 Dashboard 依赖。

## 与 Dashboard 的发布边界

发布链路固定为：

```text
niu-men-line-strategy 的 OOS 产物
  -> export_dashboard_snapshot.py
  -> wu-t0-trading-dashboard/web/public/research.json
  -> Dashboard 静态构建
```

Niu Men 仓库负责研究计算、快照字段、schema 和来源追踪。Dashboard 只负责读取快照、渲染研究结果以及在快照不可用时保持行情页面可用。两个仓库不互相导入对方的 Python 内部模块。

发布前应依次完成：

1. 在 Niu Men 仓库运行 OOS 和快照导出测试。
2. 使用导出器把快照写入 Dashboard 的 `web/public/research.json`。
3. 在 Dashboard 仓库运行 Web 单元测试、构建和浏览器 smoke check。
4. 检查快照没有本机绝对路径，且 `schemaVersion` 保持为 `niu_men.research_snapshot.v2`。

如果 `research.json` 缺失、返回非 JSON 或 schema 不受支持，Dashboard 应只在策略研究页显示相应状态，不能阻塞 `data.json` 的盘前和日内行情视图。v2 provenance 不完整时，研究新鲜度应显示为未知或警告，不得伪造为当前数据。

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
