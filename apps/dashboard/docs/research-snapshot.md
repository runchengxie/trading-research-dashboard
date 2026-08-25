# 牛门线研究快照接入

Dashboard 保留原有 `web/public/data.json` 作为盘前与日内数据源，并可选读取 `web/public/research.json` 展示牛门线全市场样本外研究。

## 数据边界

- `data.json` 仍由 `astock_tech.py` 生成，负责最新价格、ATR、VWAP、ORB、K 线和分时图。
- `research.json` 必须由 `niu-men-line-strategy` 的研究快照导出器生成，Dashboard 不重新计算 NML、行业上下文、滚动样本外或涨跌停成交约束。
- 当前支持的研究契约版本是 `niu_men.research_snapshot.v1`。

这样可以让前端继续作为纯静态站点，不需要增加后端接口，也不需要把两个仓库做成 submodule。

## 生成与放置

在 `niu-men-line-strategy` 中运行：

```bash
uv run python scripts/export_dashboard_snapshot.py \
  --oos-json /path/to/niu_men_industry_context_oos_full_market_expanded_20260825.json \
  --research-manifest artifacts/etf-industry-context-20260825/manifest.json \
  --output ../wu-t0-trading-dashboard/web/public/research.json
```

然后正常构建 Dashboard：

```bash
cd web
npm run build
```

Vite 会像处理 `data.json` 一样把 `research.json` 原样复制到 `web/dist/`，Cloudflare Pages 无需增加运行时服务。

## 缺少快照时

`research.json` 是可选输入。文件不存在时，盘前与日内区域继续正常工作，策略研究区域显示尚未部署快照的提示。这样行情更新不会被研究产物缺失阻断。

如果文件存在但 `schemaVersion` 不是 `niu_men.research_snapshot.v1`，前端会把它视为不兼容快照并显示错误，而不会尝试猜字段含义。

## 展示内容

策略研究区域展示：

- 请求、评估和跳过标的覆盖
- 行业 ETF 映射置信度和覆盖率
- 行业上下文 warmup 跳过情况
- 六个固定策略变体的 OOS 年化收益、Sharpe、最大回撤和交易次数中位数
- 涨停阻止买入和跌停阻止卖出日计数
- 按 `foldId` 的滚动窗口年化收益中位数
- 快照内置的数据质量检查

当前 `foldId` 是每只股票内部的滚动窗口序号，不保证不同股票的同一编号对应同一自然日区间。图表因此表示第 N 个样本外窗口的横截面摘要，不应解释为统一日历时间序列。
