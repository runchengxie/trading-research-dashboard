# Cloudflare Workers 部署

Dashboard 是静态 React 应用。仓库保留经过验证的静态行情快照，浏览器读取 JSON 后渲染页面。生产环境使用 Cloudflare Workers Static Assets 发布 `web/dist/`。

## 生产地址

当前生产 Worker：

<https://trading-research-dashboard.xiaowang01.workers.dev>

Worker 名称为 `trading-research-dashboard`。旧的 `wu-t0-trading-dashboard` Worker 和历史 Pages 站点仍是独立部署，只有经过明确清理后才应停用。

## 静态快照发布基线

当前仓库跟踪：

```text
apps/dashboard/web/public/data.json
apps/dashboard/web/public/research.json
```

`data.json` 是必需行情快照，`research.json` 是可选研究快照。它们和运行时 `data/raw/` 缓存职责不同。

部署前先校验：

```bash
python apps/dashboard/scripts/validate_static_assets.py
```

校验会拒绝：

- 缺失 `data.json`
- 无效 JSON
- 空的 `generatedAt`
- 空的 `stocks`
- 存在但不是 JSON object 的 `research.json`

快照刷新应该在可以访问可靠行情或研究数据的环境完成，再通过 PR 提交。GitHub 部署 runner 不临时抓行情，这样可以避免网络限制、数据源配额和凭据状态直接改变生产部署内容。

## 本地构建与 dry run

从 monorepo 根目录运行：

```bash
python apps/dashboard/scripts/validate_static_assets.py
npm ci --prefix apps/dashboard/web
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
```

需要刷新行情基线时，可以在 `apps/dashboard/` 目录执行：

```bash
uv run python -m trading_research.dashboard.astock_tech \
  --json web/public/data.json
python scripts/validate_static_assets.py
```

然后审查并提交快照变化。

检查 Workers 配置但不发布：

```bash
npx wrangler@4 deploy \
  --config apps/dashboard/wrangler.jsonc \
  --dry-run
```

`apps/dashboard/wrangler.jsonc` 把 `apps/dashboard/web/dist` 作为静态资源目录，并使用 SPA fallback 处理前端页面路径。

## 手动发布

本地直接发布需要：

```bash
export CLOUDFLARE_API_TOKEN=...
export CLOUDFLARE_ACCOUNT_ID=...
npx wrangler@4 deploy --config apps/dashboard/wrangler.jsonc
```

API Token 需要 Workers 部署权限。凭据只放在 shell 环境或 CI secret 中，不写入仓库。

## GitHub Actions

根目录 `Deploy Dashboard` workflow 只支持 `workflow_dispatch` 手动触发。

执行顺序：

1. checkout 当前提交。
2. 准备 Python 3.11 和 Node.js 22。
3. `npm ci` 安装前端锁定依赖。
4. 运行 `validate_static_assets.py` 校验仓库中的静态快照。
5. 运行前端单元测试。
6. 运行 TypeScript 与 Vite 生产构建。
7. 配置 Cloudflare 凭据时执行 Workers 部署。
8. 配置公共 URL 时运行部署后 smoke check。

需要配置：

- secret `CLOUDFLARE_API_TOKEN`
- variable `CLOUDFLARE_ACCOUNT_ID`
- variable `CLOUDFLARE_PUBLIC_URL`，可选，例如当前 Worker 地址

如果 Cloudflare 凭据为空，workflow 会完成快照校验、测试和构建，再跳过外部部署。如果 `CLOUDFLARE_PUBLIC_URL` 为空，部署完成后跳过线上检查。

## 部署后检查

`apps/dashboard/scripts/check_deployment.py` 会验证：

- 首页存在 React 挂载节点
- `data.json.generatedAt` 合法
- `data.json.stocks` 是非空列表
- `research.json` 真正返回 JSON 时使用支持的 v1 或 v2 schema

研究快照仍是可选输入。Workers SPA fallback 可能在缺少 `research.json` 时返回 HTML，部署检查会把这种情况视为未发布研究快照，不阻塞行情 Dashboard。

手动运行：

```bash
python apps/dashboard/scripts/check_deployment.py \
  https://trading-research-dashboard.xiaowang01.workers.dev/
```

## 图表图片

部署完成后可以直接从 Worker 导出 PNG：

```bash
cd apps/dashboard/web
npm run export:charts -- \
  --url https://trading-research-dashboard.xiaowang01.workers.dev/
```

这样 Hermes Agent、cron 或消息推送程序可以直接消费线上当前版本，不需要自己重新实现 ECharts 图表。

详细格式见 [输出文件与目录结构](outputs.md)。

## Cloudflare Pages

如果以后需要 Pages，可以单独使用 Direct Upload：

```bash
npm ci --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
npx wrangler@4 pages deploy apps/dashboard/web/dist \
  --project-name a-share-trading-dashboard
```

Workers Static Assets 仍是当前默认部署方式。同一个生产入口不要同时由 Pages 与 Workers 两套发布流程维护，否则部署来源和回滚点会变得难以判断。
