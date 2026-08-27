# 新人上手

## 环境准备

安装以下工具：

- Python 3.11 或更高版本
- `uv`
- Node.js 和 npm

在仓库根目录执行：

```bash
uv sync
npm ci --prefix apps/dashboard/web
```

## 运行 Dashboard 数据生成器

```bash
cd apps/dashboard
uv run python -m trading_research.dashboard.astock_tech \
  --codes sz300246,AAPL.US,TSLA.US \
  --output-root out
```

生成结果通常包括指标 Excel 文件和前端使用的 `web/public/data.json`。数据源不可用时会尝试读取缓存。没有可靠数据时不要手工填写行情。

## 启动 Web 看板

```bash
cd apps/dashboard/web
npm run dev
```

浏览器打开终端输出的本地地址。生产构建：

```bash
npm test
npm run build
```

## 运行测试

```bash
# 根目录契约和 workflow 测试
uv run --locked --extra dev pytest -q

# Dashboard Python 测试
cd apps/dashboard
uv run --locked --extra backtest pytest -q
uv run --locked ruff check src scripts tests

# 行情服务测试
cd ../market-data-service
uv run --locked pytest -q
uv run --locked ruff check src tests

# Niu Men 测试
cd ../../packages/niu-men-line-strategy
uv run --locked --extra dev pytest
```

真实 Redis 测试需要运行 Redis，并设置 `REDIS_URL`：

```bash
cd apps/market-data-service
REDIS_URL=redis://127.0.0.1:6379/0 uv run --locked --group dev pytest -q -m integration
```

## 需要密钥的功能

美股历史和实时行情需要在行情服务进程中配置 `APCA_API_KEY_ID` 和 `APCA_API_SECRET_KEY`。密钥不要放进 `data.json`、前端环境变量或浏览器代码。

R-Breaker 的 Tushare 数据需要 `TUSHARE_TOKEN`。研究数据和生成的 artifact 默认保存在仓库外的 `~/data` 目录。

## 进一步阅读

- [Dashboard 文档](../apps/dashboard/docs/)
- [行情服务文档](../apps/market-data-service/docs/)
- [路线图](roadmap/README.md)
- [维护性审查](maintenance/quality-audit.md)
- [生产切换手册](operations/runtime-cutover.md)
