# Agent 纸面组合实验

Dashboard 现在包含一个低频 Agent 投资实验。GitHub Actions 每个工作日运行一次，获取 SPY、QQQ、TLT 和 GLD 的最近收盘价，调用智谱 `glm-4.7-flash` 生成目标仓位，再由固定的 Python 模拟器计算纸面成交和净值。

当前功能只用于研究：

- 只支持做多
- 不使用杠杆
- 不连接券商
- 不发送真实订单
- 不接受券商密钥
- 模型只提供目标权重和文字说明
- 成交、手续费、净值和回撤由固定程序计算

## 配置 GitHub Actions

在仓库设置中增加 Secret：

```text
ZHIPU_API_KEY
```

工作流名称为 `Agent paper portfolio`，支持手动运行和每个工作日 22:30 UTC 自动运行。自动运行时间按 UTC 解释，实际行情日期以价格输入中的 `asOf` 为准。

当前工作流只在同时配置以下变量时部署 Cloudflare：

```text
CLOUDFLARE_API_TOKEN
CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_PUBLIC_URL
```

没有这些 Cloudflare 配置时，工作流仍会执行模型决策、模拟器、前端测试和构建，并上传运行 artifact，不会更新线上页面。

如果配置了 `CLOUDFLARE_PUBLIC_URL`，工作流会优先读取线上 `/agent/latest.json` 作为下一次运行的组合状态。没有可读取的线上状态时，会使用仓库内的初始样例。

配置了 `CLOUDFLARE_PUBLIC_URL` 后，如果线上状态读取失败，工作流会直接失败并停止部署，避免用初始样例覆盖已有历史。只有未配置线上地址时，才会使用仓库内的初始样例，适合首次离线运行。

手动运行时可以通过 `as_of` 指定 `YYYY-MM-DD` 格式的历史日期。工作流会校验日期，且模拟器会拒绝重复日期或早于上一期的日期。

## 本地离线重放

可以使用固定模型响应测试模拟流程，不需要配置 API key：

```bash
uv run --locked --package trading-research-dashboard-app agent-portfolio \
  --prices apps/dashboard/tests/fixtures/agent_portfolio/prices.json \
  --previous apps/dashboard/tests/fixtures/agent_portfolio/previous.json \
  --model-response apps/dashboard/tests/fixtures/agent_portfolio/model-response.json \
  --output /tmp/agent-latest.json \
  --as-of 2026-09-01 \
  --generated-at 2026-09-01T22:00:00Z
```

获取最近收盘价：

```bash
uv run --locked --package trading-research-dashboard-app agent-prices \
  --output /tmp/agent-prices.json
```

实时模型运行时省略 `--model-response`，并设置：

```bash
export ZHIPU_API_KEY=...
```

## 查看结果

线上页面的 `Agent 组合` 区域读取以下静态文件：

```text
/agent/latest.json
/agent/history.json
/agent/decisions.json
```

工作流 artifact 也会保存这些文件和本次价格输入，方便检查模型决策、价格日期和模拟结果。

## 成本与限制

智谱当前将 `GLM-4.7-Flash` 列为免费模型，但免费不代表永久无限量。请求频率、并发量和平台政策可能变化。模型 API 仍需要 API key，GitHub Actions 运行时间和行情数据服务也可能有各自限制。

## 回滚

如需暂停实验，可以关闭 `Agent paper portfolio` 的 schedule，或删除 `ZHIPU_API_KEY`。现有行情页面、策略研究页面和原有研究快照不依赖 Agent 组合文件。
