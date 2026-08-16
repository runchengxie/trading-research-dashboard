# 配置说明

所有配置都在 `astock_tech.py` 顶部的参数区，改完保存即可生效。

## 股票池 `STOCK_CONFIG`

```python
STOCK_CONFIG = {
    "sh600199": {"name": "金种子酒"}
}

ATR_PERIOD = 20        # ATR 滚动周期
N_CLUSTERS = 5         # KMeans 聚类中心数量
OUTPUT_ROOT = "out"    # 输出根目录，图表和 Excel 分别写入其下的 charts 和 indicators
```

添加更多股票，键名格式为交易所前缀加 6 位代码：

```python
STOCK_CONFIG = {
    "sh600199": {"name": "金种子酒"},
    "sz000001": {"name": "平安银行"},
    "sh600519": {"name": "贵州茅台"},
}
```

每个股票配置里可以带 `vwap_dev_k` 和 `roll_ratio` 字段，用于覆盖自动推导的 ATR 系数和仓位滚动比例，这也是从 `wu-t0-trading-assitant` 迁移过来的机制。

## 数据区间

日线数据默认从 `20240101` 到脚本运行当天，可按需调整 `start_date`。

## 命令行参数

```text
--codes         逗号分隔的股票代码列表，例如 sh600199,sz000001，默认使用 STOCK_CONFIG
--output-root   输出根目录，默认 out
--report        同时生成静态 HTML 报告
--report-output 报告输出目录，默认 out/site
```
