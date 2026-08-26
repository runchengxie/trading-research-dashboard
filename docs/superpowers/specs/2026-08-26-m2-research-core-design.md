# M2 Research Core 设计

## 状态

方案 A 的方向已经批准。本设计文档定义 M2 `research-core` 的正式边界，提交后仍需要一次书面 spec 审查，审查通过后才进入实施计划和代码阶段。

当前存在一个硬前置问题：PR #9 已合并到 `main`，但 `packages/niu-men-line-strategy/` 仍只有 `README.md`，真正的 Niu Men 源码和历史尚未进入 monorepo。因此 M2 可以先完成设计，但实现不得在真实 Niu Men M1 导入修复之前开始。

## 目标

把 `niu_men.research_snapshot.v2` 的共享契约资产和与策略无关的 Python 校验逻辑收敛到一个最小、可安装、可独立测试的 `research-core` package，同时保持现有 wire contract、Dashboard consumer 行为和 Niu Men producer 语义兼容。

M2 建立 canonical ownership。M3 再负责 uv workspace 和本地 package dependency 收敛。

## 当前事实

当前共享契约分散在两个项目中：

- Niu Men 源仓库在 `schemas/research-snapshot.schema.json` 保存 JSON Schema。
- Niu Men 源仓库在 `tests/fixtures/research_snapshot/` 保存四个契约 fixture。
- Niu Men 的 `scripts/snapshot_contract.py` 使用 `jsonschema.Draft202012Validator` 提供 `validate_snapshot()` 和 `load_snapshot()`。
- Dashboard 在 `apps/dashboard/schemas/research-snapshot.schema.json` 保存 consumer 侧 schema 副本。
- Dashboard 在 `apps/dashboard/tests/fixtures/research_snapshot/` 保存相同 fixture 副本。
- Dashboard TypeScript 的 `parseResearchSnapshot()` 还包含 consumer 侧运行时解析、版本检查、freshness 语义和 UI 所需错误信息。

M2 只抽取真正共享的 contract 层，不尝试把 Dashboard TypeScript parser 迁成 Python，也不把策略或展示逻辑塞进共享包。

## 实现前硬前置条件

M2 实现开始前，`main` 必须满足以下条件：

1. `packages/niu-men-line-strategy/src/` 已包含真实 Niu Men 源码。
2. `packages/niu-men-line-strategy/tests/`、`scripts/`、`schemas/` 和 `pyproject.toml` 已按批准的 M1 边界导入。
3. 代表性 Niu Men 文件的源 Git 历史可追溯到记录的 source commit `1be7f725772fa824ce34e2bb833867cb4c3e9fcb`。
4. M1 保护路径审计、Niu Men 原测试和 monorepo foundation 检查通过。

如果上述条件没有满足，应先通过独立 M1 corrective PR 修复。M2 不通过复制当前源仓库文件来掩盖错误的 M1 合并状态。

## 范围

M2 包含：

- 创建可安装的 `research-core` Python package。
- 建立 `niu_men.research_snapshot.v2` canonical JSON Schema。
- 建立 canonical contract fixtures。
- 提供共享的 schema validation API。
- 提供 provenance completeness 和声明一致性校验。
- 保留 Dashboard 和 Niu Men 的 schema / fixture 兼容副本。
- 增加 monorepo 级同步测试，防止兼容副本漂移。
- 更新 package README、迁移状态和 foundation allowlist。

M2 不包含：

- 修改 Niu Men 指标、信号、回测或研究结果。
- 修改 `niu_men.research_snapshot.v2` 字段或 wire version。
- 引入 `trading_research.strategy_snapshot.v1`。
- 建立根 uv workspace。
- 让 Dashboard Python 或 Niu Men production code 依赖本地 `research-core`。
- 重写 Dashboard TypeScript parser。
- 实时行情服务、Redis、FastAPI 或 WebSocket。
- Niu Men 自动发布链路。
- runtime cutover 或旧仓库归档。

## Package 结构

目标结构：

```text
packages/research-core/
├── README.md
├── pyproject.toml
├── src/
│   └── research_core/
│       ├── __init__.py
│       ├── snapshot.py
│       ├── provenance.py
│       └── schemas/
│           └── research-snapshot.schema.json
└── tests/
    ├── fixtures/
    │   └── research_snapshot/
    │       ├── valid_v2.json
    │       ├── warning_v2.json
    │       ├── invalid_missing_required.json
    │       └── unsupported_version.json
    ├── test_snapshot.py
    └── test_provenance.py
```

最初方案草图把 schema 放在 `packages/research-core/schemas/`。正式设计将 canonical schema 放入 `src/research_core/schemas/`，原因是 `research-core` 需要在 wheel / installed package 环境中通过 `importlib.resources` 可靠读取 schema，不能依赖 monorepo 相对路径。

对非 Python 消费者，继续提供稳定的兼容位置：

```text
schemas/research-snapshot.schema.json
apps/dashboard/schemas/research-snapshot.schema.json
packages/niu-men-line-strategy/schemas/research-snapshot.schema.json
```

这些文件是 canonical package data 的受测试镜像，不拥有独立语义。

## Python package 元数据

`packages/research-core/pyproject.toml` 使用 Python `>=3.11`，package import name 为 `research_core`，distribution name 为 `research-core`。

运行时依赖只包含 contract validation 所需库：

```text
jsonschema>=4.23,<5
```

测试工具放入 package 的 dev dependency group。M2 不建立根 workspace，也不引入新的跨 package runtime dependency。M3 负责统一 dependency graph 和 lock ownership。

## Snapshot API

`research_core.snapshot` 提供以下稳定接口：

```python
SCHEMA_VERSION = "niu_men.research_snapshot.v2"


def validate_snapshot(snapshot: Mapping[str, Any]) -> None:
    ...


def load_snapshot(path: str | Path) -> dict[str, Any]:
    ...
```

行为约束：

- root 不是 mapping 时抛 `TypeError`。
- JSON 文件无法解析时抛 `ValueError`。
- schema 不满足时抛 `ValueError`。
- schema error 必须包含稳定、可定位的字段路径。
- valid v2 和 warning v2 都是结构上有效的 snapshot。
- unsupported version 由 schema validation 拒绝。
- API 不修改输入 mapping。

Schema 使用 package resource 加载。模块不依赖当前工作目录，也不依赖 `Path(__file__).parents[...]` 推导 monorepo 路径。

## Provenance API

`research_core.provenance` 负责 v2 provenance 的语义一致性，不负责生成研究结果。

接口：

```python
PROVENANCE_FIELDS = (
    "source.researchCommit",
    "source.dataPlatformManifest.schemaVersion",
    "source.dataPlatformManifest.generatedAt",
)


def missing_provenance_fields(snapshot: Mapping[str, Any]) -> tuple[str, ...]:
    ...


def provenance_complete(snapshot: Mapping[str, Any]) -> bool:
    ...


def validate_provenance_consistency(snapshot: Mapping[str, Any]) -> None:
    ...
```

语义：

- `None`、缺失或空字符串都视为 provenance 缺失。
- `warning_v2.json` 中 `researchCommit`、manifest `schemaVersion` 和 `generatedAt` 为 `null`，因此 `provenance_complete()` 返回 `False`。
- `quality.checks.provenanceComplete` 必须与实际计算结果一致。
- provenance 不完整是允许的 warning 状态，不应被结构 validator 当作非法 snapshot。
- provenance 不完整时 `quality.status` 必须是 `warning`。
- provenance 完整时不强制 `quality.status == pass`，因为其他 quality checks 仍可能产生 warning。
- 声明值与实际 provenance 不一致时，`validate_provenance_consistency()` 抛 `ValueError`。

这样 producer 和 consumer 可以共享同一套 completeness 语义，同时保留现有“缺 provenance 显式 warning、但 snapshot 仍可消费”的行为。

## Canonical fixtures

以下四个 fixture 进入 `research-core` 并保持当前语义：

```text
valid_v2.json
warning_v2.json
invalid_missing_required.json
unsupported_version.json
```

M2 不重新设计 fixture 内容。首次 canonical copy 应从已记录 source commit `1be7f725772fa824ce34e2bb833867cb4c3e9fcb` 和当前 Dashboard 副本交叉校验，只有内容一致时才接受为 canonical 基线。

Package tests 对 fixture 的最低要求：

- `valid_v2.json` 通过 schema 和 provenance consistency。
- `warning_v2.json` 通过 schema，provenance incomplete，并通过声明一致性检查。
- `invalid_missing_required.json` 被结构 validator 拒绝。
- `unsupported_version.json` 被结构 validator 拒绝。

## 兼容副本与同步规则

M2 阶段暂时保留三处 schema 镜像和 producer / consumer fixture 副本，因为 M3 尚未建立 workspace dependency。

新增根级集成测试：

```text
tests/test_research_contract_sync.py
```

它逐字节或按 JSON canonical form 比较：

1. `research-core` canonical schema 与根 `schemas/` 镜像。
2. canonical schema 与 Dashboard schema 镜像。
3. canonical schema 与 Niu Men schema 镜像。
4. canonical 四个 fixture 与 Dashboard fixture。
5. canonical 四个 fixture 与 Niu Men fixture。

任何一份兼容副本单独修改都必须让测试失败。更新 contract 时必须从 canonical 资产出发，在同一 PR 中同步受影响镜像。

M3 引入 workspace dependency 后，再评估删除哪些 Python 侧副本。根 `schemas/` 可以长期保留为语言中立的稳定路径。

## Producer 与 consumer 边界

### Niu Men

M2 不修改策略实现，也不要求 production code 立即 `import research_core`。Niu Men 当前 `scripts/snapshot_contract.py` 可以在 M2 保留为兼容实现，前提是它继续通过 canonical fixtures 和 schema 同步测试。

M3 建立本地 package dependency 后，再把该脚本收敛为 `research_core` 的薄 wrapper 或删除重复实现。

### Dashboard

Dashboard TypeScript `parseResearchSnapshot()` 继续负责：

- 浏览器运行时类型检查。
- v1 / v2 consumer compatibility。
- consumer 友好的中文错误信息。
- freshness 计算。
- 将 Niu Men snapshot 交给 strategy adapter。

M2 不让浏览器运行 Python validator，也不自动生成 TypeScript parser。

Dashboard contract tests 必须继续使用与 canonical fixtures 同步的副本，以证明 schema ownership 迁移没有改变 consumer 行为。

## 数据流

M2 后的 contract ownership：

```text
packages/research-core/src/research_core/schemas/
                    │
                    ├── root schemas/ compatibility mirror
                    ├── Niu Men schema + fixture mirror
                    └── Dashboard schema + fixture mirror

research_core.snapshot
        │
        └── shared Python structural validation

research_core.provenance
        │
        └── shared provenance completeness semantics
```

M3 后才形成 production import dependency：

```text
Niu Men ───────┐
               ├──> research-core
Dashboard Py ──┘
```

浏览器 TypeScript consumer 继续通过 JSON wire contract 与 canonical fixtures 对齐。

## 错误处理

M2 区分三类错误：

1. JSON / root 类型错误：输入根本无法进入 contract validation。
2. schema 错误：字段、类型、version 或 required structure 不符合 v2。
3. provenance consistency 错误：结构合法，但声明的 completeness 与实际字段状态矛盾。

provenance incomplete 本身不属于第三类错误，只要声明为 `provenanceComplete=false` 且 `quality.status=warning` 即可。

错误信息需要可测试并包含字段位置，但测试不依赖 jsonschema 完整英文文案，以免库升级造成无意义脆弱性。

## 测试策略

实施时遵循 TDD。

Package 层：

- `test_snapshot.py` 先写 valid / warning / invalid / unsupported fixture 的失败测试。
- `test_provenance.py` 先写 complete、incomplete、声明矛盾、warning status 约束测试。
- 测试 package 安装后的 resource 加载，不只测试源码目录相对路径。

Monorepo 层：

- 新增 canonical / mirror 同步测试。
- foundation checker 接受 `research-core` 的明确 package 路径，同时继续拒绝 artifacts、raw data 和凭据。
- Dashboard contract tests 全量回归。
- Niu Men contract tests 和完整现有测试回归。
- root pytest、Ruff、lock / dependency checks 和 `git diff --check` 全量通过。

## 迁移与回滚

M2 只迁移 contract ownership，不改变 wire data。回滚时可以关闭 M2 PR，Niu Men 和 Dashboard 现有兼容副本仍能独立运行。

M2 合并后若发现 package consumer 集成问题，M3 不应通过删除兼容副本来强迫迁移。兼容副本只有在本地 package dependency 和完整测试稳定后才删除。

## 成功标准

M2 完成需要同时满足：

1. 真正的 Niu Men M1 history import 已修复并存在于 `main`。
2. `research-core` 是可安装、可独立测试的 Python package。
3. v2 canonical schema 和四个 canonical fixtures 有唯一 ownership。
4. `validate_snapshot()` 与现有 Niu Men contract validator 行为兼容。
5. provenance completeness 有共享、可测试的语义。
6. warning snapshot 继续合法并保持 warning 行为。
7. 根、Dashboard、Niu Men 的兼容资产无法静默漂移。
8. Dashboard consumer 行为没有改变。
9. Niu Men 策略逻辑和研究结果没有改变。
10. 根、research-core、Niu Men、Dashboard 的相关测试与质量门槛全部通过。

## 后续阶段

M2 合并后按顺序推进：

1. M3 Python uv workspace 和显式本地 package dependency。
2. 跨策略 `trading_research.strategy_snapshot.v1` wire-level contract。
3. 实时行情 contracts、provider、collector、state 和 API 分阶段实现。
4. Niu Men snapshot publication pipeline。
5. runtime cutover。
6. 旧仓库停用或归档。
