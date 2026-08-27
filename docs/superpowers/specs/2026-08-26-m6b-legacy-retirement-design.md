# M6b Legacy Repository Retirement 设计

## 状态

本设计已获方向批准，并基于 2026-08-27 的实际仓库状态刷新。M6b 负责在 runtime cutover 完成后评估旧 Dashboard 与旧 Niu Men 的长期状态；它不会提前执行生产 cutover，也不会把 GitHub Archive setting 伪装成普通 Git PR。

## 当前事实

截至本设计刷新时：

- M6 runtime cutover 设计 PR #28 已合并到 `trading-research-dashboard` main。
- M6 shadow runtime implementation PR #38 已准备，scheduled mode 固定为 `shadow`，尚未完成真实 5 个交易日证据。
- 旧 Dashboard freeze PR 已准备：`runchengxie/wu-t0-trading-dashboard#44`，尚未合并。
- 旧 Niu Men freeze PR 已准备：`runchengxie/niu-men-line-strategy#22`，尚未合并。
- 旧 Dashboard last-known-good SHA 为 `e03617a6d6922e2b3fec66a96f1ae3b51f66c38e`。
- 旧 Niu Men last-known-good SHA 为 `1be7f725772fa824ce34e2bb833867cb4c3e9fcb`。
- issue #19 仍处于 cutover / observation 阶段，因此 issue #21 仍被 #19 阻塞。
- 两个 legacy repository 当前都应保持 `archived=false`，直到 freeze、observation 和 caller audit 完成。
- 当前 GitHub connector 可以创建/审查 freeze PR 并读取 repository metadata，但没有 repository-settings archive 写接口。

## 目标

1. 让旧仓库从正常 production source 逐步变成明确的 rollback mirror。
2. 保留可验证的 last-known-good checkout、历史和必要 rollback workflow。
3. 对 Dashboard 与 Niu Men 分别完成 GitHub 内部和 GitHub 外部调用方审计。
4. 在 observation gate 达标后，独立决定每个 repository 继续 frozen 或进入 archive-approved。
5. 只有真实 GitHub repository setting 变成 archived 后，状态才可记录为 `archived`。

## 状态模型

每个 legacy repository 独立遵循：

```text
active
  ↓
frozen-rollback
  ↓
archive-approved
  ↓
archived
```

`active` 不允许直接跳到 `archived`。

### active

仍有正常生产职责、schedule/push write 或正常 publication path。

### frozen-rollback

- 正常 production write 已禁用。
- README 第一屏明确 successor 和 last-known-good SHA。
- 只保留需要精确 acknowledgement 的 manual rollback workflow。
- repository 仍可 clone、测试和查看历史。

### archive-approved

所有 observation 和 caller-audit gate 已通过，但 GitHub repository setting 尚未实际变成 archived。

### archived

GitHub repository metadata 已验证 `archived=true`。

## M6b 硬前置条件

Archive decision 只有在以下条件全部满足后才开始：

1. issue #19 已以真实 cutover/post-cutover 证据关闭。
2. monorepo 已通过 M6 runbook 规定的 post-cutover observation。
3. legacy Dashboard freeze PR #44 已合并并验证正常 trigger 消失。
4. legacy Niu Men freeze PR #22 已合并并验证正常 publication path 消失。
5. `docs/operations/runtime-cutover.md` 已记录 cutover SHA、freeze merge SHA 和 rollback evidence。
6. 没有正常 production job 继续写 legacy Dashboard。
7. Niu Men 的新研究产物不再依赖即将 archive 的 legacy repository 作为 active producer；若仍依赖，则只能保持 frozen。
8. GitHub-visible 和 external consumer 已迁移或有明确不会要求 repository 保持 active 的豁免。

## 已准备的 freeze 变更

### Legacy Dashboard

Repository：`runchengxie/wu-t0-trading-dashboard`

Prepared PR：#44。

设计要求：

- README 第一屏指向 `runchengxie/trading-research-dashboard`。
- 固定记录 legacy SHA `e03617a6d6922e2b3fec66a96f1ae3b51f66c38e`。
- `report.yml` 无 `push` 和无 weekday `schedule`。
- workflow 只允许 `workflow_dispatch`。
- acknowledgement 必须精确等于 `legacy-dashboard-rollback`。
- acknowledgement 失败发生在 generate/deploy 之前。
- workflow 不再自动 commit/push `data/raw`。
- rollback generation failure 不能被 `continue-on-error` 吞掉。

PR #44 在 monorepo authoritative cutover 成功前保持 Draft，不允许提前合并。

### Legacy Niu Men

Repository：`runchengxie/niu-men-line-strategy`

Prepared PR：#22。

设计要求：

- README 第一屏指向 `trading-research-dashboard/packages/niu-men-line-strategy`。
- 固定记录 legacy SHA `1be7f725772fa824ce34e2bb833867cb4c3e9fcb`。
- legacy Dashboard publication 只允许 manual rollback。
- acknowledgement 必须精确等于 `legacy-niu-men-publish-rollback`。
- rollback caller 必须显式填写目标 Dashboard repository，不保留旧 production target 默认值。
- acknowledgement 失败发生在 checkout target Dashboard / create PR 之前。

PR #22 在 monorepo publication authority 未得到真实证据前保持 Draft，不允许提前合并。

## Legacy banner

两个旧 repository README 的第一屏必须同时表达：

- authoritative successor；
- legacy repository 只保留历史与 rollback 能力；
- 正常开发/deploy/publication 已迁出；
- exact last-known-good legacy SHA；
- rollback 参考 monorepo `docs/operations/runtime-cutover.md`。

只在 README 底部写 deprecated 文案不满足此 gate。

## GitHub-visible caller audit

Archive 前分别搜索并分类：

- repository workflow 中的 legacy repository 名称；
- `actions/checkout` 的 `repository:`；
- HTTPS/SSH clone URL；
- scripts/docs 中的旧 production URL；
- legacy Dashboard publication target；
- cross-repository artifact producer dependency。

每个命中必须分类为：

```text
active-runtime
active-development
historical-documentation
migration-record
explicit-exemption
```

只有 active caller 都迁移或形成不会要求 repository 保持 active 的明确豁免后，GitHub caller audit 才能写 `clear`。

## External caller audit

GitHub code search 看不到用户机器和外部 scheduler，因此还必须按 M6 runbook 核对：

- cron；
- systemd timer/service；
- Hermes Agent；
- self-hosted runner scripts；
- local research runners；
- PAT-based push/open-PR automation；
- Cloudflare deploy automation；
- 任何固定 legacy clone URL 的运维脚本。

每类都必须记录实际检查结果。笼统的 “none known” 不构成 caller audit。

## Dashboard archive readiness

Legacy Dashboard 只有在以下条件全部满足后才能从 `frozen-rollback` 进入 `archive-approved`：

1. PR #44 已合并并验证 freeze 生效。
2. monorepo weekday report/deploy 已成为 authoritative。
3. 至少 10 个连续交易日没有 legacy Dashboard production write。
4. 期间没有触发 production rollback。
5. monorepo deploy/smoke 证据持续可用。
6. production Cloudflare path 不再 checkout legacy Dashboard。
7. GitHub/internal + external caller audit 已 clear 或存在明确安全豁免。
8. rollback SHA 和 rollback procedure 已实际验证可读/可执行。

## Niu Men archive readiness

Legacy Niu Men 独立评估，并额外要求：

1. PR #22 已合并并验证 freeze 生效。
2. monorepo package 已成为实际 research source authority。
3. cutover 后至少 3 次 research publication cycle 明确记录使用的 monorepo Niu Men commit/version。
4. 正常 publication 不需要 legacy Niu Men repository 继续运行 workflow 或产生新 artifact。
5. external research runner 已迁移到 monorepo checkout/package，或有明确不依赖 legacy repository active 状态的 contract。
6. 至少 10 个连续交易日没有 production rollback。
7. GitHub/internal + external caller audit 已 clear 或存在明确安全豁免。

如果正常 publication 仍从 legacy Niu Men repository 下载新 artifact，则状态保持 `frozen-rollback`，不能进入 archive-approved。

## Retirement evidence

M6b implementation 在 monorepo 维护：

```text
docs/operations/legacy-retirement.md
```

每个 repository 独立记录：

- repository；
- status；
- freeze PR URL / merge SHA；
- last-known-good legacy SHA；
- monorepo cutover SHA；
- no-write observation 起止日期；
- GitHub caller audit；
- external caller audit；
- rollback evidence；
- final decision 与原因；
- archive date/operator（若实际执行）。

证据未发生时使用 `not-yet-run`、`in-progress` 或具体阻塞原因，不得写成已完成。

## GitHub Archive setting 边界

真正的 GitHub Archive 是 repository setting，不是 Git tree 变更。

当前 connector 没有对应的 repository-settings 写接口，因此：

- connector 可以完成 freeze PR、readiness 文档和 `archived` 状态核验；
- archive-approved 后的最终 Archive 必须由 GitHub UI 或未来支持 repository-settings write 的工具执行；
- README 中出现 “archived” 字样不能替代 GitHub setting；
- 执行后必须重新读取 repository metadata 验证 `archived=true`。

## Archive 后验证

每个实际 archived repository 必须验证：

1. repository metadata 显示 `archived=true`；
2. README 第一屏 successor 信息仍可读取；
3. exact rollback SHA 仍可读取；
4. monorepo production Dashboard smoke 不受影响；
5. research publication 不依赖 archived Niu Men 产生新 artifact；
6. retirement evidence 记录实际 archive date/operator。

## Rollback / unarchive

Archive 不是删除。若严重问题要求 legacy rollback：

1. 先按 M6 runbook 确认 rollback trigger；
2. 若 repository 已 archived，则先通过受支持的 repository setting 操作 unarchive；
3. checkout 记录的 last-known-good legacy SHA；
4. 使用 frozen repository 保留的 explicit manual rollback workflow；
5. 记录 incident，并重新开始 observation；
6. 不自动恢复 archive-approved 状态。

## 验收标准

Issue #21 只有在以下条件满足后才可关闭：

1. #19 已完成并关闭；
2. 两个 legacy repository 都完成 freeze merge 和验证；
3. 没有正常 scheduled/push production writes；
4. 两个 repository 都有 successor banner 与 exact rollback SHA；
5. Dashboard 达到 10 trading-day readiness，或明确决定继续 frozen 并记录原因；
6. Niu Men 达到 3 次 monorepo publication + 10 trading-day readiness，或明确决定继续 frozen 并记录原因；
7. caller audits 有完整记录；
8. archive-approved repository 的 GitHub Archive setting 已真实执行并验证；
9. 未 archive repository 有明确复审条件；
10. 没有删除或重写 rollback history。

M6b 的目标是让 production ownership 和 rollback 边界可证明，而不是单纯让 GitHub repository 列表更整洁。
