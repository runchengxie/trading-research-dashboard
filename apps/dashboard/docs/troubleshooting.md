# 常见问题与排错

## 1. 中文乱码或负号显示为方块

更换字体为已有的中文字体，例如 `SimHei`，并保留 `axes.unicode_minus=False`。

## 2. Excel 文件被占用，无法写入

关闭已打开的 Excel 再运行脚本。

## 3. Akshare 拉取分时失败或为空

控制台会给出提示，脚本继续基于日线输出结果，但 VWAP 和 ORB 可能缺失。

## 4. 网络或数据源限流

akshare 与 tushare 访问国内数据源时偶发断连属正常。`src/trading_research/data/data_sources.py` 已对 tushare 做指数退避重试与配额感知处理，并对三个数据源做顺序兜底。若全部实时源在某次运行失败，会回退到本地 `data/raw/` 的上次成功缓存（该缓存不随导入提交），报告仍可用，但数据可能不是最新的。网络恢复后重新运行 `uv run python -m trading_research.dashboard.astock_tech` 即可更新缓存。

## 5. KMeans 收敛告警或效果不理想

调整 `N_CLUSTERS`，常见取 4 到 7，或先对价格做标准化再聚类，这需要自行扩展。
