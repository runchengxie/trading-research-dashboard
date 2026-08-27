# Niu Men Line Strategy

这是项目中的 Niu Men 策略研究包，负责策略计算、单资产回测、组合回测和样本外研究。

## 快速开始

在本目录执行：

```bash
uv run --extra dev pytest
uv run --extra dev ruff check src tests scripts
```

运行单资产回测：

```bash
uv run niu-men-backtest data.csv
```

输入 CSV 至少需要 `date`、`open`、`high`、`low`、`close` 和 `volume` 列。大型行情文件和研究产物保存在仓库外。

## 代码位置

```text
src/niu_men_line_strategy/  策略、回测和研究逻辑
scripts/                    数据准备、样本外和快照发布脚本
tests/                      单元测试和回归测试
docs/                       策略定义、数据契约和研究方法
```

## 技术文档

- [策略说明](docs/strategy-spec.md)
- [数据契约](docs/data-contract.md)
- [A1 状态接入](docs/a1-integration.md)
- [样本外研究](docs/oos-stability-diagnostics.md)
- [Dashboard 快照发布](docs/dashboard-snapshot.md)
- [维护和质量检查](docs/maintenance-and-quality.md)

研究快照通过 `research-core` 校验后，才可以发布给 Dashboard。该包不负责行情抓取，也不包含 Dashboard 前端代码。
