# 常见问题与排错

## 中文字体或负号显示异常

这个问题主要出现在 R-Breaker 的 Matplotlib 绘图。当前代码配置了 `SimHei` 和 `axes.unicode_minus=False`。运行机器没有对应字体时，需要安装可用中文字体，或把 Matplotlib 字体配置改成系统实际存在的字体。

## Excel 无法写入

如果目标 Excel 正在被桌面程序占用，`openpyxl` 可能无法覆盖文件。关闭已经打开的工作簿后重新运行。

## AKShare 分时为空

股票历史分时不会直接调用 `stock_intraday_em`，因为这个接口没有历史日期参数。历史请求会优先走 Tushare，再尝试 AKShare/market-data-platform，最后读取目标日期的本地缓存。

ETF 分时优先读取 `etf-minute-fetcher` 的本地 Parquet，随后尝试 AKShare。

所有分时来源都失败时，Dashboard 仍会基于日线生成结果。此时：

```text
vwap = null
vwapDev = null
orbHigh = null
orbLow = null
```

ATR、支撑阻力和 `vwapDevThreshold` 等只依赖日线的字段仍可输出。

## 网络断开或数据源限流

`data_sources.py` 会识别常见连接错误、5xx、Tushare 频率限制和单日配额耗尽，并按数据源顺序回退。

运行时缓存位于：

```text
data/raw/
```

分时缓存已经按交易日分区，不会再把旧的无日期 CSV 当作任意历史日期的数据。

缓存只用于容错，整个 `data/` 目录不提交到 Git。网络恢复后重新运行 Dashboard 可以刷新缓存。

## Tushare token 没有生效

检查环境变量：

```text
TUSHARE_TOKEN_2
TUSHARE_TOKEN
TUSHARE_API_URL_2
TUSHARE_API_URL
```

`TUSHARE_TOKEN_2` 优先。API URL 只有在配置对应 token 时才有意义。

如果只设置 `TUSHARE_TOKEN_2`，系统默认请求 `https://your-tushare-proxy.example.com`；若设置 `TUSHARE_API_URL_2`，则使用显式配置的地址。

美股历史日线或近期分钟数据在 market-data-service 不可用时，会由 Dashboard 直接尝试 yfinance；这仍然不是实时行情。

不要把 token 写进 `STOCK_CONFIG`、Markdown 或 GitHub 普通变量。

## KMeans 收敛告警

默认 `N_CLUSTERS = 5`。数据样本太少、价格重复很多或有效聚类中心不足时，KMeans 可能产生警告。

不要全局屏蔽 Python warning。应先确认数据是否正常，再决定是否需要调整 `N_CLUSTERS` 或针对已知第三方 warning 做精确过滤。

## `npm run export:charts` 提示没有 Chromium

第一次运行图片导出需要安装 Playwright 浏览器：

```bash
cd apps/dashboard/web
npx playwright install chromium
```

服务器或容器环境还可能需要 Playwright 的系统依赖，按 Playwright 对应平台的安装方式处理。

## 本地图片导出提示没有 `dist`

先构建前端：

```bash
cd apps/dashboard/web
npm run build
npm run export:charts
```

图片脚本只负责预览已经存在的 `dist`，不会替代生产构建。

## 从线上导出的图片还是昨天的数据

`export:charts --url ...` 读取目标站点当前的 `data.json`。如果当天数据尚未部署，截图自然仍会使用上一版。

检查：

```text
<Dashboard URL>/data.json
```

确认 `generatedAt` 后再排查截图流程。cron 应安排在数据生成和 Workers 部署完成之后。

## 部署成功但 smoke check 失败

部署检查要求：

- 首页能加载 React 根节点
- `data.json` 存在并包含非空 `stocks`
- `research.json` 存在时 schema 必须受支持

`research.json` 本身是可选的，缺少研究快照不会让 smoke check 失败。若 `data.json.stocks` 为空，说明行情生成没有成功处理任何证券，应修复数据问题后再部署。
