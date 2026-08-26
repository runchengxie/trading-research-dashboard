# 文档导航

本目录按用途整理研究资料。源材料、研究规格、数据契约、实验结果和发布说明分开维护，便于区分事实、假设与实现。

## 源材料

- [`original-transcript.md`](original-transcript.md)：视频转录与画面整理，保留原始措辞，用于追溯来源。
- [`restricted-strategy-notes.md`](restricted-strategy-notes.md)：对源材料的结构化整理。它仍属于资料整理，不等同于已验证的策略规格。

## 规格与数据

- [`strategy-spec.md`](strategy-spec.md)：NML、QRL、ATR、SMX、信号时点、过滤器和回测假设。
- [`data-contract.md`](data-contract.md)：本地 A 股日线、点时股票池、行业历史和 ETF 行业代理的数据契约。

## 研究结果

- [`research-findings-20260825.md`](research-findings-20260825.md)：逐标的滚动样本外结果与交易事件归因。
- [`portfolio-oos-research-20260826.md`](portfolio-oos-research-20260826.md)：统一自然日期窗口下的组合级样本外结果、成本敏感性和市场阶段分析。
- [`a1-integration.md`](a1-integration.md)：A1 趋势状态思想的接入边界与当前 comparator。

## 发布与协作

- [`dashboard-snapshot.md`](dashboard-snapshot.md)：研究快照 v2、来源追踪和 Dashboard 发布边界。
- [`maintenance-and-quality.md`](maintenance-and-quality.md)：测试、静态检查、依赖审计和常见维护问题。
- `../artifacts/`：可追踪的产物清单。大型行情和回测文件保留在数据平台目录，不复制进代码仓库。

`original-transcript.md` 是来源存档，后续修改策略规格时应在规格文件中记录冲突，不要直接改写转录内容。
