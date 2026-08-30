# 牛门线日历感知滚动窗口设计

## 背景

Dashboard 当前加载的牛门线 `research.json` 有 10 个 variant、7 个 `foldId`，但滚动汇总
没有 `startDate/endDate`。原始快照已经明确说明不同股票的交易日历可能不同，因此前端只能
显示“窗口 1–7”。这不是前端日期格式问题，而是导出层没有把 fold 明细中的日期信息带到
汇总快照。

## 目标

1. 在不伪造全市场统一日期的前提下，保留每个 fold 的真实测试日期信息。
2. 对所有股票日期一致的 fold 显示精确日期区间。
3. 对股票日期不一致的 fold 显示真实的日期范围、日期覆盖数和有日期的股票数。
4. 没有日期字段的旧快照继续可读，并明确标记为序号窗口。
5. 多 variant 的滚动图只使用唯一 fold 坐标，避免同一窗口被重复绘制。

## 非目标

- 不从 `foldId`、快照生成日或训练 bar 数量反推日期。
- 不把个股日期范围伪装成一个统一的全市场回测区间。
- 不在本次改动中重跑全市场牛门线 OOS，也不改变现有收益、Sharpe 或回撤计算。
- 不强行让 R-Breaker、ICT 或其他策略共享牛门线 variant。

## 方案

### 导出层

`packages/niu-men-line-strategy/scripts/export_dashboard_snapshot.py` 在读取 `folds.csv`
后，为每个 `fold_id` 聚合日期元数据。日期字段优先读取 fold 明细中的 `test_start` 和
`test_end`；日期值统一为 ISO `YYYY-MM-DD`，无效或缺失值不进入统计。

每条滚动汇总新增可选的 `calendar` 对象：

```json
{
  "mode": "exact | range | unknown",
  "startDate": "2024-01-02",
  "endDate": "2024-12-31",
  "startDateMin": "2019-03-01",
  "startDateMax": "2020-01-02",
  "endDateMin": "2020-02-28",
  "endDateMax": "2021-02-28",
  "datedSymbols": 3500,
  "totalSymbols": 3808,
  "distinctDatePairs": 12
}
```

字段规则：

- `exact`：所有参与该 fold 的股票都有日期，且拥有同一 start/end pair，写入 `startDate/endDate`。
- `range`：日期不一致，写入 min/max 字段及覆盖数量；不写入单一的 `startDate/endDate`。
- `unknown`：fold 明细没有可用日期，仅保留现有 `foldId`。

为了兼容已有 dashboard 代码，顶层滚动汇总仍保留原有指标字段；`calendar` 为 optional，
旧消费者可以忽略它。旧版 `startDate/endDate`（如果上游 summary 已经提供）仍可被读取，
但导出器会优先使用 fold 明细的聚合结果并避免与其矛盾。

### 契约层

同步更新牛门线快照 schema 及其仓库内镜像，使 `rollingSummary.calendar` 可选且严格限制
字段类型、日期格式和枚举值。所有现有字段继续保持兼容，不改变顶层 schema version；这是
对 v2 快照的向后兼容 enrichment。

### 前端层

标准化 `StrategyRollingSummary` 的日历字段，并将标签选择顺序设为：

1. `startDate/endDate`：`YYYY-MM-DD → YYYY-MM-DD`；
2. `calendar.mode=range`：显示测试日期范围，并标识为“个股日期范围”；
3. 旧版只有 `foldId`：显示“窗口 N”，同时在评估方式 KPI 中说明“原始快照未提供统一日历区间”。

滚动图的 x 轴基于唯一的 `foldId` 集合，而不是每个 variant 的所有 summary 行。每个 variant
仍通过 `(variant, foldId)` 映射到同一个 x 轴位置。

### 生成与发布

新导出器只能在输入 fold 明细包含日期时产生日期标签；当前已发布的旧 `research.json` 不会
被人工补日期。重新运行牛门线 OOS 并执行导出后，日期信息才会进入线上快照。发布前继续
执行 Dashboard 静态快照校验、前端单元测试和生产构建。

## 错误处理

- fold 明细不存在日期列：输出 `unknown`，保持旧兼容行为。
- 只有部分股票有有效日期：输出 `range`，`datedSymbols` 记录实际覆盖，不静默升级为 `exact`。
- 日期无法解析：忽略该值并计入未覆盖数量；如果没有任何有效日期则为 `unknown`。
- 日期聚合与 summary 的 fold/variant 键无法对齐：导出失败，避免发布错位指标。

## 测试

- 导出器单元测试：精确日期、日期不一致、部分缺失日期、完全缺失日期。
- schema 测试：合法 `calendar` 通过，非法 mode/日期/类型拒绝。
- 前端标签测试：精确日期、范围日期、旧序号三种输入。
- 前端滚动图源代码测试：确认 x 轴使用唯一 fold 坐标。
- 回归运行现有牛门线、Dashboard Python/Node 测试和静态资产校验。

## 迁移结果

代码合并后，旧线上快照仍可能显示“窗口 1–7”，直到使用包含 fold 日期的 OOS artifact
重新导出 `research.json`。这是数据缺失而非部署失败；迁移完成的判据是线上快照中至少一条
牛门线 rolling summary 含有 `calendar.mode`，且页面按真实日期或真实日期范围显示。
