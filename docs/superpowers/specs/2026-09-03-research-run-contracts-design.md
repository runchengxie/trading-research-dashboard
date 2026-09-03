# Research Experiment / Agent Run Contracts 设计

## 背景

`trading-research-dashboard` 已经拥有策略快照、contextual research、provenance 校验、Agent 纸面组合以及 workspace research evidence 的静态发布链路。下一阶段需要承接更多研究 producer，例如 `ai-stock-picker`、外部 Agent Harness、Vibe-Trading 类 Swarm，以及未来不同模型/Prompt/Harness 的对照实验。

如果 Dashboard 直接理解每个外部项目的内部 JSON，会形成 producer-specific coupling：页面、验证器和研究逻辑会随着每个外部项目一起变化，也难以建立统一的 Case / Run / Evidence / Scorecard 评估。因此，本设计在 `packages/research-core` 增加一层最小的运行与评估契约，使 Dashboard 只依赖 canonical contracts，外部项目通过 adapter 或发布投影接入。

本设计不把外部仓库复制或作为 submodule 引入，也不改变现有 `market-data-service` 的行情 authority。

## 目标

新增四类 canonical contract：

- `trading_research.research_experiment.v1`
- `trading_research.agent_run.v1`
- `trading_research.research_evidence.v1`
- `trading_research.eval_result.v1`

它们共同表达：

```text
Experiment
  ├─ Case / variant definition
  ├─ Agent Run
  │    ├─ task / worker summaries
  │    ├─ artifact refs
  │    └─ evidence refs
  └─ Eval Result
       └─ scorecard metrics
```

目标是让以下 producer 最终可以投影到同一套研究语义：

- `ai-stock-picker` 的 frozen plan、selection、shadow repetition、consensus 与 evidence；
- Vibe-Trading 类 Harness 的 SwarmRun、SwarmTask、worker status、token/latency 与 artifact；
- 本仓库现有或未来的单 Agent、Agent paper portfolio 与策略研究实验；
- 其他 Frontier Model / Harness 的对照运行。

## 非目标

本 PR 不负责：

- 把 `ai-stock-picker` 合并进 monorepo；
- vendor 或复制 Vibe-Trading 源码；
- 新增真实交易或券商连接；
- 新增 canonical 行情 provider；
- 在 JSON 中保存完整 chain-of-thought；
- 把原始 Prompt、HTTP body、大型回测结果或原始行情提交到 Git；
- 声称任何历史运行已经满足严格 Point-in-time 或 OOS 证明。

## 方案选择

### 方案 A：Dashboard 直接消费各 producer schema

优点是初期代码少。缺点是 Dashboard 会同时理解 `ai_stock_selection`、SwarmRun、未来其他 Agent 的内部模型，长期无法形成统一 Eval。

不采用。

### 方案 B：把 Agent runtime 统一搬进 Dashboard monorepo

优点是部署集中。缺点是会复制行情、工具和 LLM provider 层，扩大依赖面，也违反当前仓库对外部项目边界的治理方向。

不采用。

### 方案 C：Canonical contracts + adapters / publication projections

`research-core` 只定义稳定研究语义；producer 自己拥有执行逻辑和详细 artifact，通过 adapter 或已验证的静态 publication 生成 canonical records。Dashboard 只做 validate / index / render / compare / evaluate。

采用此方案。

## Contract 1：`research_experiment.v1`

### 职责

定义一个可重复比较的研究实验。它描述研究问题、baseline、variants 和 scorecard，而不保存单次运行结果。

### 核心字段

```text
schemaVersion
experimentId
objective
taskType
market
createdAt
caseSet
baselineVariantId
variants[]
scorecard[]
constraints[]
provenance
```

`variants[]` 至少包含：

```text
variantId
label
kind              # numeric_baseline | single_agent | multi_agent | model | harness | custom
model             # 可选公共标识，不保存 endpoint/credential
harness           # 可选稳定标识
promptVersion     # 可选
configurationRef  # 可选 artifact/publication ref
```

`scorecard[]` 定义指标合同，不保存最终数值：

```text
metricId
label
direction          # maximize | minimize | target
unit
required
threshold          # 可选
```

### 设计约束

- baseline 必须显式存在于 `variants`；
- metric ID 在同一实验中唯一；
- 不允许把一次运行产生的模型解释文本放进 experiment；
- experiment 是“评估设计”，不代表任何 variant 已经运行。

## Contract 2：`agent_run.v1`

### 职责

保存一次 Harness/Agent 执行的可审计摘要。它是 vendor-neutral 的运行 envelope，不复制具体 Harness 的完整内部状态。

### 核心字段

```text
schemaVersion
runId
experimentId       # 可选，允许独立研究运行
caseId              # 可选
variantId           # 可选
status
startedAt
completedAt
model
harness
budget
usage
tasks[]
artifactRefs[]
evidenceRefs[]
limitations[]
provenance
```

`status` 采用比 HTTP success 更严格的状态：

```text
pending
running
completed
incomplete
failed
timeout
budget_limited
cancelled
```

其中 `incomplete` 表示运行没有异常退出，但没有产生满足合同的 deliverable；不得折叠为 `completed`。

`tasks[]` 只保存可审计摘要：

```text
taskId
agentId
role
status
dependsOn[]
startedAt
completedAt
iterations
summary
artifactRefs[]
evidenceRefs[]
```

`usage` 可以保存：

```text
inputTokens
outputTokens
wallTimeMs
modelCost         # 可选；金额必须带 currency
```

`budget` 与 `usage` envelope 始终存在，但内部字段可以为空，表示 producer 没有声明限制或没有观测到用量。adapter 不得为了满足 schema 伪造 token、成本或 latency。

### Task graph 规则

- `taskId` 在同一 run 内唯一；
- `dependsOn` 只能引用同一 run 中已声明的 task；
- task graph 必须无环；
- terminal run/task 必须有 `completedAt`；
- 整体 run 为 `completed` 时，所有 task 也必须为 `completed`。

### Trace 边界

canonical `agent_run` 不保存隐藏 chain-of-thought。可保存：

- task graph；
- tool / evidence / artifact 引用；
- 可公开的 task summary；
- 状态、预算、token、latency；
- producer 提供的可审查日志 artifact ref。

完整 provider response、Prompt 或工具原始结果继续由 producer 的 evidence/archive 机制管理。

## Contract 3：`research_evidence.v1`

### 职责

表示一个研究 claim / criterion / run 所依赖的可追溯证据记录。它与现有 workspace research evidence publication 不是第二套发布系统：本 contract 是 canonical research record；现有 publication 继续负责把经过筛选的 public projection 安装到 Dashboard 静态资产。

### 核心字段

```text
schemaVersion
evidenceId
runId               # 可选
claimId              # 可选
criterionId          # 可选
evidenceType
source
retrievedAt
dataAsOf
freshnessStatus
verificationStatus
artifactRef
contentSha256
pointInTime
limitations[]
provenance
```

`source` 至少允许：

```text
provider
sourceType
sourceUri            # 可选；不得包含 secret
symbolUniverse[]
benchmark[]
timeframe
method
```

`pointInTime` 显式表达证据等级，例如：

```text
assurance             # unverified | signal_date_only | externally_timestamped | strict_replay
strict                # boolean
eligibleAsOosEvidence # boolean
```

### PIT / OOS 规则

- 哈希只能证明内容 identity，不能证明历史存在时间；
- `strict=true` 不能仅依赖 producer 自报日期或 SHA-256，且必须使用 `strict_replay` assurance；
- strict PIT 与 OOS eligibility 是两条独立轴。严格历史回放仍可能属于模型训练期、研究开发期或其他 in-sample 区间，因此 `strict=true` 可以同时保持 `eligibleAsOosEvidence=false`；
- `eligibleAsOosEvidence=true` 至少要求 `externally_timestamped` 或 `strict_replay` assurance，但这一最低门槛仍不能单独证明完整 OOS 有效性；
- 默认 adapter 应保守降级 assurance；
- `ai-stock-picker` 当前的 `strict_point_in_time=false` 与 `eligible_as_oos_evidence=false` 必须原样保留，不能在 Dashboard adapter 中升级；
- Vibe-Trading 类实时 grounding 数据即使有 `data_as_of`，也不能自动视为历史严格 PIT。

## Contract 4：`eval_result.v1`

### 职责

绑定 experiment/case/run 与 Scorecard 结果，使不同 model / harness / baseline 可以被同一 Dashboard 比较。

### 核心字段

```text
schemaVersion
evalId
experimentId
caseId
runId
variantId
evaluatedAt
status
metrics[]
scorecardStatus
limitations[]
provenance
```

`metrics[]`：

```text
metricId
value
unit
status              # pass | fail | informational | unavailable
threshold           # 可选
notes               # 可选，短文本
```

`scorecardStatus`：

```text
pass
fail
partial
insufficient_evidence
```

Eval 不允许把“端到端分数高”自动解释成研究有效。PIT、evidence completeness 或必需指标失败时，可以使整个 scorecard 失败或进入 `insufficient_evidence`。

## Canonical provenance

四种新增 record 都要求 `provenance` 至少包含非空 `source`。其余 producer-specific lineage 字段保持开放，便于 adapter 保存 owner contract/version、artifact hash、producer run identity 等信息，而不用强迫外部 producer 伪装成本仓库现有 snapshot/data-platform provenance。

## 与 `ai-stock-picker` 的映射

首个外部 adapter 后续应采用只读转换，不复制其 owner schema。

建议映射：

```text
ai_pick_plan / shadow decision plan
        -> research_experiment variant/config ref

selection / repetition / consensus
        -> agent_run artifact refs

selection evidence directory
        -> research_evidence records

numeric ranking vs LLM ranking + forward evaluation
        -> eval_result metrics
```

重要边界：

- `ai-stock-picker` 继续拥有 candidate contract、Prompt、provider 和 selection 校验；
- Dashboard 不重新实现 `pick`；
- 跨仓 consumer 优先调用 owner validator 或消费已验证 artifact，而不是复制其 schema 常量；
- Numeric baseline 与 LLM rerank 应在 experiment 中成为独立 variant，便于长期比较 rank delta 与后续收益。

## 与 Vibe-Trading 类 Harness 的映射

Vibe-Trading 当前的 Swarm 模型提供可借鉴的运行语义：AgentSpec、DAG task dependency、worker `incomplete/failed/timeout`、artifact path、token usage 和 event log。

建议映射：

```text
SwarmRun
  -> agent_run

SwarmTask
  -> agent_run.tasks[]

WorkerStatus.incomplete
  -> agent_run.status/task.status = incomplete

Goal / criterion / evidence ledger
  -> experiment objective / evidence records

Swarm artifact paths
  -> artifactRefs
```

不直接映射：

- Vibe 的 provider fallback 不能成为 Dashboard canonical market-data authority；
- live trading 路径不进入本次接入；
- producer-specific tool payload 不进入 canonical run JSON；
- 任何历史研究仍需单独处理 PIT contamination。

## 与现有 publication / provenance 的关系

现有 workspace research evidence publication 已负责：

- 跨仓 artifact 获取；
- hash identity 校验；
- public projection；
- scoped PR publication；
- Dashboard static asset 安装。

新 contracts 不替代这条链路。

建议数据流：

```text
Producer-owned detailed artifact
        ↓ owner validation
Canonical research record(s)
        ↓ publication projection / installer
Dashboard public JSON
        ↓
Dashboard UI / Eval views
```

`research-core` 负责 wire contract 和纯校验；Dashboard app 负责发布 adapter 和 UI。原始大文件、敏感请求和完整 trace 不进入 `research-core`。

## 实现边界

首个实现 PR 只加入 contract 基础设施，不同时接外部服务：

1. 四个 JSON Schema；
2. 一个 `research_core.experiments` 模块加载 schema 并提供 validator；
3. 从 `research_core.__init__` 导出版本常量与 validator；
4. schema 正向/反向测试，覆盖状态、baseline、scorecard、PIT/OOS、DAG、provenance 和 `incomplete`；
5. 更新 `packages/research-core/README.md`；
6. 将 `research-core` pytest/ruff 纳入现有 PR quality gate；
7. 不修改 Dashboard React，不修改 market-data-service，不新增网络调用。

后续单独 PR 再实现：

- `ai-stock-picker` adapter / publication projection；
- Dashboard `AI Research` / Agent Eval 页面；
- Vibe-Trading adapter 或 MCP/HTTP tool integration；
- experiment registry 与长期 scorecard aggregation。

## 测试策略

按照现有 `research-core` 模式使用 Draft 2020-12 JSON Schema validator。

测试至少覆盖：

- 四种最小合法 fixture 可以通过；
- 根对象类型错误失败；
- `additionalProperties` 按 contract 约束拒绝意外字段；
- experiment baseline 不存在于 variants 时失败；
- duplicate `variantId` / `metricId` 通过 Python 交叉校验失败；
- `completed` run 缺少完成时间失败；
- `incomplete` 可以成为合法终态；
- 空 budget/usage 可表达未知值；
- task dependency 悬空、循环和 completed-run 状态不一致失败；
- strict PIT 与 OOS eligibility 的独立语义和最低 assurance 约束得到覆盖；
- canonical provenance 缺少 `source` 失败；
- eval metric 必须引用 experiment 中已定义 metric 的跨对象检查由后续 registry/evaluator 层负责，本次 schema 不做跨文件网络式解析。

验证命令为：

```bash
cd packages/research-core
uv run --locked pytest -q
uv run --locked ruff check src tests
```

PR quality workflow 同时继续运行 Dashboard Python、Web test 和 Web build，避免共享 package 变更破坏现有 consumer。

## 兼容与回滚

- 新 schema 全部为 additive，不修改现有 snapshot wire format；
- 不修改现有 publication 静态文件；
- 没有外部 consumer 时删除新增模块和 schema 即可回滚；
- 后续 adapter 必须显式声明 producer contract/version，禁止用字段猜测来源；
- contract 一旦被跨仓 consumer 使用，破坏性变更通过新 schema version 发布，不原地重写 v1。

## 成功标准

本阶段完成后，`research-core` 应能够用统一语言回答四个问题：

1. 我们正在比较什么研究实验？
2. 某个 Agent/Harness 具体运行了什么，状态与资源消耗是什么？
3. 这个运行使用了哪些可追溯证据，PIT 可信度到什么程度？
4. 它相对 baseline 和 Scorecard 表现怎样？

做到这四点后，`ai-stock-picker`、Vibe-Trading 类 Harness 和未来 Agent 才有稳定的接入边界；是否采用 Multi-Agent 继续由任务结构和 Eval 结果决定，而不是由架构图里能塞多少个方框决定。
