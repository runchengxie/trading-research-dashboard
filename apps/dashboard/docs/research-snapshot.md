# 研究快照接入

Dashboard 当前使用三类静态 JSON：

```text
web/public/data.json                行情、指标、K 线和分时数据
web/public/research.json            Niu Men 兼容研究快照
web/public/rbreaker-research.json   R-Breaker generic strategy snapshot
web/public/ict-liquidity-reclaim-research.json
                                    ICT 流动性回收 generic strategy snapshot
```

`data.json` 是行情工作区的必需 fallback。两个策略研究文件相互独立；任意一个策略快照缺失或失败都不能让盘前概览和日内工作台失效。

## 契约边界

共享契约位于 `packages/research-core/`。

Niu Men 继续支持历史 wire contract：

```text
niu_men.research_snapshot.v1
niu_men.research_snapshot.v2
```

跨策略通用 envelope 为：

```text
trading_research.strategy_snapshot.v1
```

前端 registry 把不同 wire payload 适配成通用 `StrategySnapshot`：

- `niu-men-line` → `./research.json`
- `r-breaker` → `./rbreaker-research.json`
- `ict-liquidity-reclaim` → `./ict-liquidity-reclaim-research.json`

研究 UI 只消费 adapter 后的通用模型，不需要了解 producer Python 内部实现。

## Niu Men 发布

Niu Men producer 位于：

```text
packages/niu-men-line-strategy/
```

共享 publisher 的默认 strategy target 仍是 `niu-men-line`，因此现有调用兼容：

```bash
uv run --locked --extra dev python scripts/publish_research_snapshot.py \
  --snapshot /path/to/research.json \
  --open-pr
```

publisher 在写入 `apps/dashboard/web/public/research.json` 前执行 Niu Men canonical schema 和 provenance consistency 校验；任何失败都保留上一份有效静态快照。

## R-Breaker 输入 artifact

R-Breaker 生产研究输入使用：

```text
trading_research.rbreaker_input.v1
```

artifact 根目录必须包含 `manifest.json`，以及 manifest 明确声明的 `bars/*.parquet`。`trading_research.rbreaker_artifact` 会检查：

- schema version
- symbol 与 1m bar interval
- previous-day high/low/close
- 文件路径不能逃逸 artifact root
- 每个文件的 byte size
- SHA-256
- 不允许 manifest 未声明的额外文件
- minute bars 的时间、重复行、数值列和正价格约束

原始 minute bars 不进入 Git。

## R-Breaker snapshot generator

生成器：

```text
apps/dashboard/src/trading_research/scripts/generate_rbreaker_snapshot.py
```

执行示例：

```bash
uv run --locked --package trading-research-dashboard-app --extra backtest \
  python -m trading_research.scripts.generate_rbreaker_snapshot \
  --artifact-root /path/to/rbreaker-input \
  --output /tmp/rbreaker-research.json \
  --producer-run-id <workflow-run-id>
```

输出为 `trading_research.strategy_snapshot.v1`，包含：

- `strategy.id = r-breaker`
- generated/data date
- quality
- research/data platform provenance
- producer artifact run id
- input SHA-256
- backtrader version
- coverage
- execution timing
- variant metrics

Generator 只把已声明输入转成研究快照，不负责发布，也不修改 R-Breaker 策略参数。

## R-Breaker production publication

共享 publisher 通过显式 strategy id 选择独立目标：

```bash
uv run --locked --extra dev python scripts/publish_research_snapshot.py \
  --snapshot /tmp/rbreaker-research.json \
  --strategy-id r-breaker \
  --open-pr
```

R-Breaker publication gate 在任何目标写入前要求：

1. generic strategy schema 校验通过；
2. `strategy.id == r-breaker`；
3. `quality.status == pass`；
4. `researchCommit`、`dataPlatform`、`dataPlatformSchemaVersion`、`dataPlatformGeneratedAt`、`oosSchemaVersion`、`oosGeneratedAt`、`artifactRunId` 和 `inputSha256` 非空。

通过后只允许更新：

```text
apps/dashboard/web/public/rbreaker-research.json
```

publisher 使用原子替换；后续静态校验失败时恢复目标文件旧 bytes。Niu Men `research.json` 与 R-Breaker 文件不能互相覆盖。

## ICT liquidity reclaim snapshot

`ict-liquidity-reclaim` 是第一个可执行的 ICT 假说基准，不把 ICT 叙事或
"smart money" 判断硬编码进系统。它只测试以下可观测规则：

- 当前 regular US session 的 bar 低点跌破 previous-day low 后收盘收回，做多；
- 当前 bar 高点突破 previous-day high 后收盘跌回，做空；
- 下一根 bar 开盘成交；信号 bar 极值外设止损，固定 1.5R 目标；
- OHLC 无法判断同 bar 路径时，止损优先；每侧 2bp 滑点单独计入成本。

生成器为：

```text
apps/dashboard/src/trading_research/scripts/generate_ict_liquidity_reclaim_snapshot.py
```

单日 artifact 只用于验证生产链路，快照会明确标记 `quality=warning`，并抑制年化收益和
Sharpe。只有多日、多折 OOS 输入完成后，才允许把结果解释为策略证据。

## GitHub Actions

`.github/workflows/publish-rbreaker-snapshot.yml` 是手动 workflow，输入：

- `artifact_repository`
- `artifact_run_id`
- `artifact_name`，默认 `rbreaker-input-v1`

流程：

```text
validated input artifact
        ↓
download-artifact
      ↓
generate_rbreaker_snapshot
        ↓
canonical generic snapshot validation
        ↓
shared publisher --strategy-id r-breaker
        ↓
scoped publication PR
```

跨仓库下载必须提供 `RESEARCH_ARTIFACT_TOKEN`；同仓库 artifact 使用 `github.token`。workflow 不提交下载的 artifact 或 raw minute bars。

`.github/workflows/rbreaker-artifact-and-deploy.yml` 是从 Alpaca 拉取并校验 artifact、同时
生成 R-Breaker 与 ICT 流动性回收快照的入口。它在生成两个快照后统一执行 contextual
enrichment、静态校验和前端构建；`deploy=true` 才会调用 Wrangler。

workflow 成功定义只表示发布路径存在。至少一次真实 artifact run、生成、publication PR 和审查合并发生后，才能把该链路记录成真实生产 publication 证据。

## Scoped PR

publisher 根据 strategy id 创建独立发布分支：

```text
publish/niu-men-line-snapshot-<timestamp>
publish/r-breaker-snapshot-<timestamp>
```

PR 只 stage 目标 snapshot 文件，并记录：

- strategy id
- wire version
- data date
- contract/provenance validation

R-Breaker generic envelope 使用顶层 `dataDate`；Niu Men 继续兼容 `source.dataDate`。

## 缺少或错误的研究快照

前端必须正确处理：

- strategy snapshot 404
- SPA fallback 返回 HTML
- schema version 不支持
- provenance 不完整
- 单个策略错误

这些情况只影响对应策略研究区域。`data.json` 仍然驱动行情页面。

## 新鲜度

Niu Men 使用：

```text
research.json.source.dataDate
```

Generic strategy snapshot 使用：

```text
<data snapshot>.dataDate
```

两者与 `data.json.generatedAt` 的数据日期语义比较。浏览器当前日期不参与判断，因此周末、节假日和夜间不会产生自然时间流逝导致的假过期。

## 策略研究展示

当前研究区可以：

- 加载 Niu Men 与 R-Breaker 独立快照
- 加载 ICT 流动性回收独立快照，并显示规则、成本与单日样本限制
- 展示 coverage、quality、provenance 和 variant metrics
- 在至少两个有效策略都可用时展示共同指标对比
- 单个策略缺失时保持其他策略和行情区域可用

## 执行约束状态

快照中的 `executionCapabilities` 用来区分指标语义，而不是把所有空值都当成同一种缺失：

- `observed`：生成器实际建模并统计了该约束，前端显示计数。
- `not_modelled`：该约束适用于策略，但当前生成器尚未建模，前端显示“未建模”。
- `not_applicable`：该约束不属于策略的数据或市场范围，前端显示“不适用”。例如基于美股 Alpaca 数据的 R-Breaker 与 ICT 快照不适用 A 股涨跌停约束。

策略对比同时提供两种视角：严格的共同 `variant id` 对齐表用于可比性检查；默认版本概览按各策略自己的默认变体并列展示，仅用于方向性观察，不应解读为同条件横向回测。

R-Breaker 当前生产落地范围是可重复 publication，不在本阶段增加多标的参数搜索或 walk-forward 优化。

## 与 M6 的关系

R-Breaker publication 可以为 monorepo research authority 提供额外证据，但 M6 的真实 gate 仍由 `docs/operations/runtime-cutover.md` 定义。创建 workflow 或生成样本文件不能代替真实 publication cycle、五个连续交易日 shadow run、人工同日比较或 authoritative cutover。
