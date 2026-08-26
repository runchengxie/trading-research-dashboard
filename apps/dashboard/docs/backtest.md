# 回测模块

从 `wu-intraday-strategy` 迁移整合的 R-Breaker 日内策略回测模块位于
`src/trading_research/strategies/rbreaker.py`。

## 安装

依赖为可选，需要时单独安装：

```bash
uv sync --extra backtest
```

## 用法

安装后使用维护中的包模块：

```bash
uv run python -m trading_research.strategies.rbreaker \
  --symbol 603356 --data-source akshare
```

akshare 数据源无需 token，开箱即用。

### tushare 数据源

需要 token，通过环境变量 `TUSHARE_TOKEN` 提供，不要写入代码或提交到仓库：

```bash
# Windows PowerShell
$env:TUSHARE_TOKEN = "你的token"
uv run python -m trading_research.strategies.rbreaker \
    --symbol 603356 --data-source tushare \
    --in-sample-start 2025-06-01 --in-sample-end 2025-06-23 --out-sample-start 2025-06-24
```

### 其他常用选项

* `--data-folder`，tushare 本地缓存目录
* `--plot`，回测结束后绘制蜡烛图

## 策略说明

R-Breaker 根据前一日的最高、最低、收盘价算出六个关键价位，再结合当前价格产生突破和反转信号，每日收盘前强制平仓，不留隔夜仓。回测会做样本内参数优化和样本外验证，并给出夏普、回撤、收益和信号准确率。
