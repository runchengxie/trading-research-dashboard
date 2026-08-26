# Niu Men 策略包

`packages/niu-men-line-strategy/` 是 Niu Men 后续保留历史导入到 monorepo 的目标位置。

当前 Niu Men 源码仍由独立仓库 `runchengxie/niu-men-line-strategy` 维护，本目录尚未包含策略实现。

迁移后该 package 仍应负责：

- Niu Men 指标和信号
- 回测与滚动样本外研究
- 行业上下文和相关研究逻辑
- 研究快照生成

它不应负责 Dashboard React 展示代码，也不应把 Dashboard 当作内部 Python 模块直接 import。

Niu Men 与 Dashboard 当前通过 `niu_men.research_snapshot.v2` JSON 契约连接。正式导入应通过独立 PR 完成，保留必要 Git 历史、源 commit 和回滚记录，并在导入步骤中避免顺便改写策略行为。
