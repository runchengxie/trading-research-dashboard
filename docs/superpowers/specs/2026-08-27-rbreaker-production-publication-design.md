# R-Breaker Production Publication 设计

## 目标

把现有 R-Breaker 策略实现、输入 artifact 校验和 generic strategy snapshot generator 串成可重复、可审查的生产发布链路。最终由 GitHub Actions 从一个经过声明与哈希校验的 `trading_research.rbreaker_input.v1` artifact 生成 `trading_research.strategy_snapshot.v1`，校验 strategy identity 与 provenance，然后只更新 `apps/dashboard/web/public/rbreaker-research.json` 并创建独立 PR。

## 现状

- `apps/dashboard/src/trading_research/strategies/rbreaker.py` 已包含迁移后的 R-Breaker 回测逻辑。
- `apps/dashboard/src/trading_research/rbreaker_artifact.py` 已校验输入 manifest、文件白名单、大小和 SHA-256。
- `apps/dashboard/src/trading_research/scripts/generate_rbreaker_snapshot.py` 已能从 artifact 生成 `trading_research.strategy_snapshot.v1`。
- Dashboard registry 已把 `r-breaker` 映射到 `./rbreaker-research.json`。
- 当前仓库中的 `rbreaker-research.json` 仍是样本快照，不构成真实生产发布证据。
- `scripts/publish_research_snapshot.py` 当前只理解 Niu Men wire contract，并把发布目标固定为 `research.json`。
- `.github/workflows/publish-research-snapshot.yml` 当前只接受已经生成好的 snapshot artifact；它不能把 R-Breaker 输入 artifact 转成 generic snapshot。

## 边界

本阶段只落地生产发布能力，不修改 R-Breaker 交易逻辑、参数、信号规则或回测算法，不增加多标的参数网格和 walk-forward 研究，不把样本 JSON 冒充真实运行证据。

Niu Men 的现有 `research.json` 发布行为必须保持向后兼容。R-Breaker 与 Niu Men 可以共用安全发布基础设施，但发布目标和 contract 校验必须显式区分，防止一个策略覆盖另一个策略的静态文件。

## 发布目标注册表

`scripts/publish_research_snapshot.py` 增加显式 publication target 注册表：

- `niu-men-line` → `apps/dashboard/web/public/research.json`
- `r-breaker` → `apps/dashboard/web/public/rbreaker-research.json`

CLI 新增 `--strategy-id`，默认值为 `niu-men-line`，因此现有 Niu Men workflow 和直接调用不需要修改即可继续工作。

每个 target 定义：

1. 目标静态文件路径；
2. contract validator；
3. strategy identity validator；
4. PR branch/title 标签。

不得根据文件名或 payload 内容静默猜测目标策略。

## Contract 校验

### Niu Men

继续执行当前：

- `validate_snapshot()`；
- `validate_provenance_consistency()`。

### R-Breaker

执行：

- `validate_strategy_snapshot()`；
- `schemaVersion == trading_research.strategy_snapshot.v1`；
- `strategy.id == r-breaker`；
- `quality.status == pass`；
- `provenance.researchCommit`、`dataPlatform`、`dataPlatformSchemaVersion`、`dataPlatformGeneratedAt`、`oosSchemaVersion`、`oosGeneratedAt`、`artifactRunId`、`inputSha256` 必须非空。

Generator 已负责产出这些字段；publisher 再做边界校验，避免调用方绕过 generator 发布样本 fixture 或手工拼装的不完整 envelope。

## 原子发布与回滚

发布顺序保持 fail-closed：

1. 加载 candidate；
2. 根据显式 `strategy_id` 完整校验；
3. 保存目标文件旧 bytes；
4. 原子替换目标静态文件；
5. 运行 Dashboard 静态资产校验；
6. 任一步骤失败都恢复旧 bytes 或删除刚创建的新文件。

R-Breaker 发布失败不得影响现有 Niu Men `research.json`，反之亦然。

## Scoped PR

`open_update_pr()` 根据策略生成独立 branch：

- Niu Men: `publish/niu-men-line-snapshot-<timestamp>`
- R-Breaker: `publish/r-breaker-snapshot-<timestamp>`

提交和 PR 只 stage 对应的 snapshot 文件。generic envelope 的日期取顶层 `dataDate`；Niu Men 继续兼容原 `source.dataDate`。

PR body 明确记录：

- strategy id；
- wire version；
- data date；
- 已执行 contract/provenance 校验；
- review scope 只包含目标 snapshot 文件。

## R-Breaker Workflow

新增 `.github/workflows/publish-rbreaker-snapshot.yml`，只允许 `workflow_dispatch`。输入：

- `artifact_repository`；
- `artifact_run_id`；
- `artifact_name`，默认 `rbreaker-input`。

流程：

1. checkout monorepo；
2. 安装固定 Python/uv 环境；
3. 跨仓库 artifact 时要求 `RESEARCH_ARTIFACT_TOKEN`；
4. 下载 R-Breaker 输入 artifact 到 `incoming-rbreaker/`；
5. 运行 `generate_rbreaker_snapshot.py`，producer run id 使用输入 run id；
6. 运行 publisher：`--strategy-id r-breaker --open-pr`；
7. 失败时运行 foundation check，保证仓库静态 fallback 不受破坏。

workflow 不直接提交原始 minute bars，也不把 artifact 内容复制到 Git。

## 测试

### Publisher tests

新增覆盖：

- valid generic R-Breaker snapshot 可以发布到独立目标；
- generic snapshot strategy id 错误时在写入前失败；
- incomplete R-Breaker provenance 在写入前失败；
- Niu Men 默认调用行为保持不变；
- generic `dataDate` 用于 PR metadata；
- scoped staging 只引用对应目标文件。

### Workflow contract tests

新增根级 workflow test，验证：

- 只有 `workflow_dispatch`；
- 存在 cross-repo token gate；
- 下载输入 artifact；
- 调用 R-Breaker generator；
- publisher 明确传 `--strategy-id r-breaker --open-pr`；
- 不出现 raw artifact git add/commit 路径。

## 成功标准

1. R-Breaker 可以从真实 artifact 可重复生成 generic snapshot。
2. publisher 不再硬编码只有 Niu Men，同时 Niu Men 现有行为无回归。
3. R-Breaker 发布只能写 `rbreaker-research.json`。
4. wrong-strategy、invalid-schema、incomplete-provenance candidate 在任何写操作前失败。
5. R-Breaker workflow 只生成/发布 snapshot，不提交原始行情。
6. Dashboard 现有 registry 无需改业务模型即可读取新的生产 snapshot。
7. 完整仓库测试、Ruff、前端测试/build、foundation check 通过后才能把 PR 转为 ready。
