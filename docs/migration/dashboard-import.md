# Dashboard M1 导入记录

本文件记录首次导入时的路径边界和验证结果。表格中的测试数量属于导入当时的历史证据，不代表当前 `main` 的测试数量。当前功能、命令和质量检查以根 README、`AGENTS.md`、`apps/dashboard/README.md` 及现行 workflow 为准。

## 状态

Dashboard 的 M1 导入已经完成。本文件记录首次保留历史导入时使用的路径边界、排除规则和验证证据，方便后续追溯。

Niu Men 不包含在这次 Dashboard 导入中，仍需要通过独立 PR 迁移。

## 来源和回滚记录

| 项目 | 值 |
| --- | --- |
| 源仓库 | `runchengxie/wu-t0-trading-dashboard` |
| 精确源 commit | `8f809f58b2cdb4b6c6dee8e8d4c767a6ea30a114` |
| 目标前缀 | `apps/dashboard/` |
| 导入方式 | 从精确源 commit 进行保留历史的路径过滤，再允许无共同祖先历史合并 |

源 commit 同时记录在 [`source-commits.md`](source-commits.md)。

这个 SHA 是首次导入边界的追溯点，不代表后续 monorepo 代码需要长期保持与该 commit 完全相同。

## 首次导入路径映射

首次导入只接受以下源仓库路径。右侧为写入 monorepo 后的目标位置：

```text
src/                                  -> apps/dashboard/src/
web/                                  -> apps/dashboard/web/
backtest/                             -> apps/dashboard/backtest/
tests/                                -> apps/dashboard/tests/
scripts/                              -> apps/dashboard/scripts/
docs/backtest.md                      -> apps/dashboard/docs/backtest.md
docs/cloudflare-workers.md            -> apps/dashboard/docs/cloudflare-workers.md
docs/configuration.md                 -> apps/dashboard/docs/configuration.md
docs/data-sources.md                  -> apps/dashboard/docs/data-sources.md
docs/indicators.md                    -> apps/dashboard/docs/indicators.md
docs/outputs.md                       -> apps/dashboard/docs/outputs.md
docs/research-snapshot.md             -> apps/dashboard/docs/research-snapshot.md
docs/troubleshooting.md               -> apps/dashboard/docs/troubleshooting.md
docs/web-frontend.md                  -> apps/dashboard/docs/web-frontend.md
schemas/research-snapshot.schema.json -> apps/dashboard/schemas/research-snapshot.schema.json
pyproject.toml                        -> apps/dashboard/pyproject.toml
uv.lock                               -> apps/dashboard/uv.lock
wrangler.jsonc                        -> apps/dashboard/wrangler.jsonc
README.md                             -> apps/dashboard/README.md
.gitignore                            -> apps/dashboard/.gitignore
```

递归目录包含其子文件，但仍受下面的显式排除规则限制。首次源仓库中不在映射表里的根级路径不会进入导入历史。

## 显式排除

以下路径和模式在历史重写阶段就被排除：

- `data/raw/**`
- `web/public/data.json`
- `web/public/research.json`
- `.github/**`
- 源仓库根目录的 `.env*`
- 任意子目录的 `**/.env*`
- `**/*credential*`
- `**/*secret*`
- `**/*token*`
- `**/*password*`
- `**/*.pem`
- `**/*.key`
- `**/*.p12`
- `**/*.pfx`
- 源仓库根目录的 `astock_tech.py`
- 源仓库根目录的 `data_sources.py`
- `docs/superpowers/**`

这些文件没有先进入最终 checkout 再删除，过滤规则直接作用于导入历史。精确源 commit、允许路径和排除模式共同定义了首次导入的历史边界。

## 首次导入保证

M1 Dashboard 导入当时的约束包括：

- 不导入 Niu Men 源码
- 不在导入步骤重写 Dashboard 业务行为
- 不改变 `research_snapshot.v2` consumer 语义
- 不把原始行情、凭据或本地生成快照带入首次导入历史
- 不引入 gitlink 或 Git submodule

后续在 monorepo 内发生的正常功能修复和维护不受首次导入 allowlist 的逐文件冻结约束。根级边界检查仍保留真正需要长期维护的安全和迁移约束。

## 2026-08-26 首次验证记录

下面结果来自 M1 迁移 worktree，当时用于确认 Dashboard 导入和根级治理集成没有破坏既有测试。

这是一份历史审计记录。后续测试数量、依赖版本和构建输出变化时，不应把下面的数字改成最新值，否则会丢失首次导入时的证据。

| 命令 | 当时的精确结果 |
| --- | --- |
| `uv run --project apps/dashboard --locked pytest -q`，从 `apps/dashboard/` 运行 | 失败：`Project directory apps/dashboard does not exist` |
| `uv run --project . --locked pytest -q`，从 `apps/dashboard/` 运行 | `33 passed in 7.61s` |
| `uv run --project apps/dashboard --locked pytest -q apps/dashboard/tests` | `33 passed in 5.90s` |
| `npm ci --prefix apps/dashboard/web` | 安装 39 个 package，审计 40 个 package，`found 0 vulnerabilities` |
| `npm test --prefix apps/dashboard/web -- --run` | `23` 个测试通过，`0` 个失败 |
| `npm run build --prefix apps/dashboard/web` | `tsc && vite build` 成功，转换 632 个模块 |
| `uv lock --check` | `Resolved 7 packages in 0.60ms` |
| `uv run --locked --extra dev pytest -q` | `21 passed in 1.55s` |
| `uv run --locked python scripts/check_foundation.py` | `Foundation check passed` |
| `git status --short` | 无输出，文档审计更新前工作树干净 |
| `git diff --check` | 无输出，退出码 0 |

当时 Vite 提示压缩后的主 JavaScript chunk 超过 800 kB。该提示没有阻止构建，也没有发现迁移特有的运行错误。

首次导入期间修正了三类兼容问题，没有借机改写 Dashboard 运行逻辑：

1. Web package 增加实施计划要求的 `npm test` 入口。
2. schema 测试改用保留的 v2 fixture，不再依赖有意排除的 `web/public/research.json` 生成文件。
3. 根级 foundation checker 跳过 `.gitignore` 排除的依赖目录，避免 `npm ci` 后扫描第三方 Markdown 的占位词。

继承的测试也改用保留历史后的包模块，例如：

```text
trading_research.data.data_sources
trading_research.dashboard.astock_tech
trading_research.strategies.rbreaker
```

因此测试不再依赖首次导入时明确排除的源仓库根级兼容模块和源仓库 CI。

## 保留历史证据

当时使用下面的命令抽查 Dashboard 核心模块历史：

```text
$ git log --follow --oneline -- apps/dashboard/src/trading_research/dashboard/astock_tech.py | head -20
5a7de4d refactor: package dashboard Python modules
```

保护路径历史检查只针对 M1 合并提交及其祖先。后续受控发布快照进入仓库后，直接对全部历史执行相同查询当然会命中，这是正常的时间线变化。M1 当时的查询为空：

```text
$ git log 1766170 --name-only --format= | grep -E '^(apps/dashboard/(data/|artifacts/|web/public/|\.github/|docs/superpowers/)|apps/dashboard/(astock_tech\.py|data_sources\.py)$|apps/dashboard/(.*/)?\.env[^/]*$|apps/dashboard/(.*/)?[^/]*(credential|secret|token|password)[^/]*$|apps/dashboard/(.*/)?[^/]*\.(pem|key|p12|pfx)$)' || test $? -eq 1
(no output)
```

gitlink 和 submodule 审计同样为空：

```text
$ git ls-files --stage | awk '$1 == "160000" {print}'
(no output)
$ git submodule status
(no output)
```

首次导入过程中，原 Dashboard 工作树保持不变：

```text
$ git -C /path/to/wu-t0-trading-dashboard status --short
(no output)
$ git -C /path/to/wu-t0-trading-dashboard rev-parse --short HEAD
e03617a
```

## 导入后的静态发布基线

M1 首次历史导入有意排除了 `web/public/data.json` 和 `web/public/research.json`，因为当时目标是保护导入历史，不把源仓库的本地生成产物一起搬入。

第一次 monorepo 部署随后暴露出一个不同层面的问题：纯静态 Dashboard 没有有效行情快照时无法渲染业务页面。后续 PR 因此在 `apps/dashboard/web/public/` 中引入了一组经过审查的静态发布基线：

```text
apps/dashboard/web/public/data.json
apps/dashboard/web/public/research.json
```

这两个文件属于受控 release input，与 `data/raw/` 运行时缓存不是同一类资产。原始行情缓存继续留在 Git 之外。

部署流程会先运行 `apps/dashboard/scripts/validate_static_assets.py`。缺少、损坏或 `stocks` 为空的 `data.json` 会直接阻止部署，避免静态托管把缺失 JSON 请求回退成 `index.html` 后制造一个表面部署成功、实际没有数据的站点。

## 后续维护

Dashboard 导入后已经继续在 monorepo 内演进，包括部署基线、数据源、缓存、测试和图表导出等维护工作。后续判断当前功能应以 `apps/dashboard/` 的代码和现行文档为准，本文件只承担首次导入历史记录和关键边界演进说明。
