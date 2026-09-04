# Dashboard 覆盖率与模块边界设计

## 目标

提高配置和 provider 策略边界的可测试性，并把 R-Breaker 的纯指标计算从回测入口中分离。

## 方案

新增 `strategies/rbreaker_metrics.py` 保存无副作用的 Sharpe 计算。`rbreaker.py` 继续导出原名称，保证现有脚本和外部调用兼容。为 `instrument_config.py` 和 `provider_policy.py` 补充真实边界测试，不改变数据源选择、策略参数和回测结果口径。

## 验收

- 新旧导入路径均可用。
- Dashboard 全量测试通过，覆盖率不低于现有 60% 门槛。
- Ruff、ty 和空白检查通过。
