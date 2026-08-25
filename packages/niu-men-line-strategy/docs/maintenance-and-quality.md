# 维护与质量检查

## 日常验证

项目使用 `uv` 管理环境。提交代码前运行：

```bash
uv run --extra dev pytest
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
uv run --extra dev ty check src
uv run --extra dev coverage run -m pytest
uv run --extra dev coverage report --fail-under=80
uv run --extra dev pip-audit --skip-editable
```

测试覆盖率阈值针对 `src/niu_men_line_strategy`，当前设置为 80%，脚本和测试代码不计入统计范围。项目启用了分支覆盖率，因此这个阈值会同时约束条件分支。`pip-audit` 会跳过本地可编辑安装包，只检查第三方依赖。

## 当前代码结构

- `indicators.py` 负责指标和成本代理。
- `signals.py` 负责 NML 信号、过滤器和状态重置。
- `backtest.py` 负责单资产事件驱动执行。
- `portfolio.py` 负责共享现金的组合级回测与交易归因。
- `context.py`、`industry_mapping.py` 负责点时股票池、行业历史和 ETF 代理上下文。
- `walk_forward.py` 负责滚动样本外窗口。
- `scripts/` 中的文件是可复现的研究入口，不属于运行时核心库。

目前没有发现可以安全删除的核心模块。研究脚本虽然数量较多，但都对应数据校验、快照导出、样本外运行或归因报告，并且由文档或测试覆盖。删除前应先确认没有外部数据平台任务调用它们。

## 静态检查边界

Ruff 检查错误、导入、常见简化规则、类型升级提示和项目约定的代码异味。`RUF001` 被保留为例外，因为中文文档和面向用户的错误信息需要中文标点。`TRY003` 也暂不强制，它会把已有的用户提示拆成大量自定义异常类型，当前收益有限。

`ty` 目前检查 `src` 目录，并作为合并门槛。pandas、Parquet 和动态 DataFrame 列仍可能产生推断噪声。新增模块应优先为公开函数补充输入输出类型，再逐步收紧范围。

## 研究结果的可追溯性

每份正式研究结果都应记录：

- 数据截止日和执行时点
- 股票池与行业映射版本
- 训练窗口、测试窗口和预热规则
- 请求、评估、跳过数量及原因
- 成本、手数、仓位和涨跌停处理
- 研究代码 commit 和产物 manifest

组合级报告使用统一自然日期窗口。逐标的报告中的 `fold_id` 只表示每只股票自己的第 N 个窗口，不能直接当作自然日期序列。

## 跨仓库边界

`wu-t0-trading-dashboard` 是独立的兄弟仓库，不是本项目的 Git submodule。研究快照由本项目生成，Dashboard 只消费 `web/public/research.json`。两边应分别建分支、测试和 PR。
