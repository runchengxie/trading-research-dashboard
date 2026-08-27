# M6 Runtime Cutover 设计

## 状态

方案 A 已获方向批准。本文件定义 monorepo 成为生产权威来源的切换流程。书面 spec 审查通过后，才进入 implementation plan 和实际生产切换。

## 当前事实

截至 `main@055f84e1456e2463a0339f079f1660cf5945cb46`：

- Dashboard、Niu Men、`research-core` 和通用 strategy snapshot contract 已进入 monorepo。
- 根 uv workspace 和唯一根 `uv.lock` 已建立。
- M4 research snapshot publication 已实现：`scripts/publish_research_snapshot.py` 会做 canonical schema/provenance 校验、原子写入、失败恢复，并可打开 scoped update PR。
- `.github/workflows/publish-research-snapshot.yml` 可以按 repository/run/artifact 参数下载 research artifact 后触发上述发布路径。
- monorepo 的 `.github/workflows/deploy-dashboard.yml` 仍只有 `workflow_dispatch`，负责静态快照校验、测试、build、Workers deploy 和 smoke check。
- 旧 `wu-t0-trading-dashboard` 的 `report.yml` 仍在 `push main` 和工作日 `01:00 UTC` cron 上运行，会生成行情、构建并部署 Cloudflare Workers。
- 旧 `niu-men-line-strategy` 仍保留 `publish-dashboard-snapshot.yml`，默认向旧 Dashboard 仓库开研究快照 PR。
- 两个旧仓库都仍 active，`archived=false`。

因此代码迁移基本完成，但工作日行情生产、旧仓库写路径和生产 authority 尚未真正切换。

## 目标

把生产职责从旧 Dashboard / Niu Men 仓库迁到 monorepo，同时保证：

1. 切换前有 shadow 运行证据。
2. 切换当天没有数据生成或部署空窗。
3. 旧仓库自动生产写路径被明确冻结，而不是仅靠文档约定。
4. rollback 入口保留并可操作。
5. 外部 `research-workspace`、`market-data-platform`、`etf-minute-fetcher` 继续通过稳定契约协作。
6. GitHub Archive 留给 M6b，不与第一次 cutover 混在一起。

## 非目标

M6 不包含：

- 删除或 archive 旧仓库。
- 删除 rollback 历史。
- 把 raw market data 或完整 OOS 研究数据提交到 monorepo。
- 重新设计策略。
- 把 M5 realtime service 变成 Dashboard 启动硬依赖。
- 仅通过 README 文字宣称 production cutover 成功。

## Runtime authority

### 切换前

| 职责 | 权威来源 |
| --- | --- |
| Dashboard source/build config | monorepo |
| Dashboard 手动 deploy | monorepo |
| 工作日行情生成 + 自动 deploy | 旧 Dashboard repo |
| reviewed static `data.json` fallback | monorepo |
| research snapshot validation/publication | monorepo |
| 旧 Niu Men → 旧 Dashboard publish workflow | 旧 Niu Men repo 仍存在 |
| Niu Men source code | monorepo 已导入；旧 repo 仍可运行 |
| realtime market service | M5 完成前不存在 |

### 切换后

| 职责 | 目标权威来源 |
| --- | --- |
| Dashboard source/build/deploy | monorepo |
| 工作日行情生成 + production deploy | monorepo |
| reviewed static `data.json` | monorepo fallback |
| research snapshot validation/publication | monorepo |
| Niu Men code version used for publication | monorepo commit |
| realtime service | monorepo M5 service；故障时静态 fallback |
| 旧 Dashboard scheduled writes | disabled |
| 旧 Niu Men Dashboard publish writes | disabled |
| legacy rollback | old repos manual-only + explicit acknowledgement |

## 硬前置条件

M6 authoritative cutover 不得开始，直到：

1. M4 publication (`#17`) 已在 `main`。
2. M5 完成到 Dashboard static fallback 可验证的 production-readiness 阶段。
3. monorepo 配置了当前 Dashboard deploy 所需 Cloudflare secrets/variables。
4. monorepo 具备工作日行情生成需要的数据源配置；token 缺失时有明确 fallback 行为。
5. 最新 `main` 全量 foundation、Python、Web、audit、build 验证通过。
6. 旧 Dashboard 与旧 Niu Men 的 last-known-good SHA 已记录。
7. M4 publication 至少有一条**真实可运行**的 artifact 或本地 publication 路径，不只存在 workflow 文件。

## Cross-repository artifact authentication gate

当前 `publish-research-snapshot.yml` 使用 `actions/download-artifact@v4` 读取可配置的其他仓库 artifact。跨仓库下载必须使用对目标仓库有 `actions:read` 权限的 token。

因此 M6 不允许仅凭当前 workflow 定义宣称跨 private repo artifact handoff 已验证。cutover 前必须满足以下二选一：

### 方案 A：真实跨仓库 run 通过

实际从目标 private research repository 的 run 下载 artifact，并成功走完 validation + scoped PR。

### 方案 B：最小权限专用 token

将 workflow 的 `github-token` 改为独立 secret，例如：

```text
RESEARCH_ARTIFACT_TOKEN
```

该 token 只授予目标 research artifact repository 的 `Actions: read` 和实际需要的最小 repository read 权限，不复用宽权限 PAT。

若目标 artifact 来自当前 monorepo，则可以继续使用当前 repo token，不需要额外 secret。

## 工作日 Dashboard report 迁移

旧 Dashboard `report.yml` 当前承担实际日常 production job。M6 新增：

```text
.github/workflows/dashboard-report.yml
```

### 触发

```yaml
on:
  workflow_dispatch:
    inputs:
      mode:
        type: choice
        options: [shadow, authoritative]
        default: shadow
  schedule:
    - cron: "10 1 * * 1-5"
```

schedule 初期固定运行 `shadow`。`01:10 UTC` 故意晚于旧 Dashboard 当前 `01:00 UTC` cron，方便比较同日结果而不争夺生产 deploy。

这是 Actions “manual-only” 历史政策的显式生产例外。例外只覆盖这个工作日 report workflow；其他 workflow 不因此自动改成 schedule。

## Shadow mode

shadow mode：

1. checkout monorepo。
2. 使用根 uv lock。
3. 在 `apps/dashboard/` 运行 canonical generator：

```bash
uv run --locked python -m trading_research.dashboard.astock_tech \
  --json web/public/data.json
```

4. 运行 `scripts/validate_static_assets.py`。
5. 运行 Dashboard Web unit tests 和 production build。
6. 运行 runtime candidate safety check。
7. 上传本次候选 `data.json` 和 validation manifest 为 workflow artifact。
8. **不 deploy、不 push、不 commit cache**。

GitHub hosted runner 对 tracked `web/public/data.json` 的修改只存在于临时 checkout。

monorepo 不复制旧 Dashboard “提交 `data/raw` cache” 的行为；raw/cache 继续被仓库边界排除。

## Runtime candidate safety check

新增：

```text
apps/dashboard/scripts/check_runtime_candidate.py
```

至少拒绝：

- `stocks` 为空。
- production baseline 有默认标的而候选缺失。
- 候选 `generatedAt` 早于当前 baseline。
- 候选数据日期明显倒退。
- 所有数据源失败后产生空/无意义 snapshot。

它只做 runtime publication safety，不重新实现指标业务逻辑。

## Shadow 观察门槛

进入 authoritative cutover 前至少满足：

- 5 个连续交易日 scheduled shadow run 成功。
- 5 次均通过 candidate validation、Web tests 和 build。
- 没有一次生成空 snapshot 覆盖风险。
- 至少人工抽查 2 次 shadow artifact 与当日旧 production 页面在默认标的/日期上相符。
- M4 publication 有 3 次成功 reviewed cycle；若研究发布频率较低，则允许 3 次 dry-run + 至少 1 次真实 publication。
- cross-repository artifact authentication gate 已有真实运行证据，或 production path 改为 local/direct publication。

## Authoritative mode

authoritative mode 在 shadow 步骤上增加：

1. 使用本次生成的 `data.json` build Dashboard。
2. 使用 monorepo `apps/dashboard/wrangler.jsonc` deploy Workers Static Assets。
3. 运行 `check_deployment.py`。
4. 上传 deployed manifest，记录 monorepo SHA、data generatedAt、deploy time 和 public URL。

每日 runtime candidate **不直接 push 回 main**。Git 中 reviewed static `data.json` 继续作为 fallback。若某次 runtime candidate 需要固化为新的 fallback，走独立 reviewed PR。

## Schedule activation

shadow workflow 初次落地时，schedule 固定：

```text
SCHEDULE_MODE=shadow
```

经过 shadow gate 后，独立小 PR 将 schedule 默认改成：

```text
SCHEDULE_MODE=authoritative
```

`workflow_dispatch` 继续保留 mode 选择。

这个小 PR 是 production authority 的明确 Git rollback point。

## Cutover day 顺序

1. 从最新 `main` 手动 dispatch monorepo `dashboard-report.yml`，选择 `authoritative`。
2. generate、validate、build、deploy、post-deploy smoke 全部成功。
3. production URL 展示本次 monorepo data date。
4. 合并旧 Dashboard freeze PR，关闭 schedule/push production writes。
5. 合并旧 Niu Men freeze PR，关闭正常的旧 Dashboard publish path。
6. 合并 monorepo schedule activation PR，将 schedule 从 shadow 切成 authoritative。
7. 再运行一次 monorepo foundation/deploy smoke。

顺序始终是“新路径先成功，再关旧路径”。

当前 connector 没有暴露通用 workflow-dispatch，因此第 1/7 步是明确的人为运行 gate，不能由 PR 文本替代。

## Research publication authority

monorepo 已经成为 snapshot validation/publication owner，但 artifact producer 可以来自外部 research infrastructure。

M6 要求至少证明一条不依赖旧 Niu Men publish workflow 的生产路径：

### 路径 A：external runner + monorepo checkout

1. checkout 精确 monorepo SHA。
2. 使用 `packages/niu-men-line-strategy` 产生候选 snapshot。
3. 在 checkout 中运行：

```bash
uv run --locked python scripts/publish_research_snapshot.py \
  --snapshot /path/outside/git/research.json \
  --open-pr
```

### 路径 B：artifact workflow

外部 run 上传 sanitized snapshot artifact，monorepo workflow 用通过 auth gate 的 token 下载并开 scoped PR。

无论哪条路径，最终 validation/publication owner 都是 monorepo。

## Legacy Dashboard freeze PR

在 `runchengxie/wu-t0-trading-dashboard` 独立 PR：

1. README 顶部加入 legacy/successor banner，指向 monorepo。
2. `report.yml` 移除 `push` 和 `schedule`。
3. 只保留 `workflow_dispatch` 作为 rollback path。
4. rollback workflow 增加必填确认输入：

```text
confirm_legacy_rollback=legacy-dashboard-rollback
```

5. 值不精确匹配时 job 立即失败。
6. 只有 explicit rollback acknowledgement 才允许执行 legacy generate/deploy。
7. `web-browser.yml` / `web-unit.yml` 可以继续保留用于 legacy checkout 可运行性验证。

## Legacy Niu Men freeze PR

在 `runchengxie/niu-men-line-strategy` 独立 PR：

1. README 顶部声明 monorepo 是 current source authority。
2. `ci.yml` 可以保留。
3. `publish-dashboard-snapshot.yml` 不再属于正常 production path。
4. workflow 只保留 manual rollback，并要求精确确认输入。
5. 普通执行不得默认 write `runchengxie/wu-t0-trading-dashboard`。

M6 freeze 关闭 production writes；M6b 才决定 GitHub Archive。

## Post-cutover observation

#19 不在 cutover day 立即关闭。至少观察 5 个连续交易日：

- monorepo scheduled authoritative report 正常运行。
- production smoke 没有持续错误。
- M5 service offline 时 static fallback 仍可用。
- 旧 Dashboard 没有 scheduled deploy。
- 旧 Niu Men 没有正常 publish 到旧 Dashboard。
- 至少一次 research snapshot publication 在 cutover 后由 monorepo path 完成。

## Rollback triggers

以下任一情况触发 rollback 评估：

- monorepo scheduled report 连续两个交易日失败且无法当日修复。
- production `data.json` 比最近成功 baseline 明显倒退或为空。
- Cloudflare deploy/smoke 连续失败导致用户不可用。
- M5 live mode 故障同时破坏 static fallback。
- monorepo publication path 无法更新 snapshot，且上一份有效 snapshot 也不可继续消费。

## Rollback procedure

1. revert schedule activation PR 回 shadow。
2. 手动触发 legacy Dashboard rollback workflow，并提供 acknowledgement。
3. 必要时 checkout 记录的 legacy last-known-good SHA。
4. 保留失败证据和 workflow artifact。
5. 修复后重新从 shadow observation 开始。

Dashboard rollback 不自动等于 Niu Men publication authority 也回滚。

## Cutover runbook

新增：

```text
docs/operations/runtime-cutover.md
```

记录：

- monorepo cutover SHA。
- old Dashboard last-known-good SHA。
- old Niu Men last-known-good SHA。
- production Worker URL。
- scheduled workflow 名称/时间。
- research publication path 和 artifact auth 方式。
- realtime endpoint（若启用）。
- rollback triggers/入口。
- shadow/cutover/observation run 证据链接。

## 验收标准

#19 只有在以下全部满足后才能关闭：

1. M4 publication 已由 monorepo 实际使用。
2. M5 production-readiness/static fallback gate 已完成。
3. cross-repository artifact auth 已验证，或 production 不依赖 cross-repo artifact。
4. 5 个 shadow trading-day cycle 通过。
5. cutover-day authoritative manual run 成功。
6. monorepo scheduled authoritative mode 已启用。
7. old Dashboard schedule/push production writes 已冻结。
8. old Niu Men normal Dashboard publish writes 已冻结。
9. cutover 后连续 5 个交易日 observation 通过。
10. 至少一次 cutover 后 research publication 通过 monorepo。
11. runbook 包含精确 rollback SHA 和证据。
12. foundation/Python/Web/audit/build/deploy smoke 全部通过。
13. GitHub repos 尚未 archive；archive 保留给 M6b。

## 回滚边界

M6 把不可逆操作推迟：

- 旧仓库仍存在。
- 旧 workflow 仍保留 explicit manual rollback 入口。
- production schedule 切换有独立小 PR rollback point。
- static `data.json` 始终是 fallback。

只有 M6 observation 完成后，才进入 M6b retirement/archive。
