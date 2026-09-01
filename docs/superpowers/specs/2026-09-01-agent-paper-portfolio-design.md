# Agent 纸面组合实验设计

## 目标

在现有 Dashboard 中增加一个低频、只用于纸面交易的 Agent 投资实验。GitHub Actions 每个交易日运行一次，调用 `GLM-4.7-Flash` 生成目标仓位，由确定性的 Python 模拟器计算调仓、手续费、组合净值和回撤，最后生成静态 Dashboard 数据。

第一阶段不接券商、不发送真实订单、不运行常驻 Agent，也不把 Codex CLI 作为生产调度器。

## 架构

```text
GitHub Actions → 固定行情输入 → GLM-4.7-Flash
       → target_weights → 合同与约束校验 → 纸面模拟器
       → agent portfolio 快照 → Dashboard 构建与 Cloudflare 发布
```

模型密钥使用 GitHub Secret `ZHIPU_API_KEY`。工作流默认使用最小权限，模型失败、响应无法解析或数据校验失败时不覆盖上一份有效快照。

## 数据合同

新增 `trading_research.agent_portfolio.v1` 合同，包含实验元信息、组合状态、目标权重、决策说明、成交记录和历史净值。记录 `provider`、`model`、`promptVersion`、`inputHash`、数据日期和价格来源。

模型只输出允许标的的目标权重和说明。程序负责 JSON 解析、标的白名单、权重总和、单标的上限、现金下限、成交、手续费、净值和回撤计算。

第一阶段只支持 long-only、无杠杆、无做空。现金使用 `CASH`。模拟器固定使用收盘价，并且可以用 fixture 在无网络、无模型环境中重放。

## 文件与发布

Agent 文件使用独立目录：

```text
apps/dashboard/web/public/agent/
├── latest.json
├── history.json
└── decisions.json
```

新增独立 workflow，支持 `workflow_dispatch` 和每个工作日一次的 `schedule`。流程包括获取行情、调用模型、合同校验、模拟执行、前端测试、构建和 artifact 上传。部署步骤保持可选，不接真实交易。

前端增加 Agent Portfolio 视图，展示当前权益、NAV、累计收益、最大回撤、净值曲线、基准曲线、持仓、最近决策和交易记录。现有研究快照、ECharts 和其他页面保持不变。

## 安全与失败处理

- API key 只从环境变量读取
- 不允许模型调用 shell、Git 写操作、Cloudflare 写操作或券商 API
- workflow 使用 `contents: read`
- 错误响应、非法权重、缺失价格直接失败
- 失败时保留上一份有效快照
- 默认不自动提交每日数据文件

## 测试与回滚

测试覆盖合同、权重限制、模拟成交、手续费、净值、API 响应、离线端到端运行、前端加载和 workflow 合同。验证使用 `pytest`、`ruff`、`ty`、pnpm 测试和前端构建。

回滚时可以停用 workflow schedule、恢复 Agent 静态资源和移除 Agent 页面，不影响已有研究快照、行情服务和 Cloudflare 页面。

后续另行设计每小时决策、多模型竞赛、D1、Codex CLI、Vibe-Trading、券商连接和真实订单。
