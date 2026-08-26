# M1 Dashboard 导入实施计划

> Agent 执行提示：本计划按任务拆分，原执行流程要求使用 superpowers 的计划执行能力逐项完成。下列复选框保留首次迁移时的任务结构，当前 Dashboard M1 已经完成。

目标：把 Dashboard 导入 `apps/dashboard/`，保留有价值的源历史，同时排除原始数据、生成快照、凭据和无关自动化。

架构：从精确 Dashboard 源 commit 构造经过路径过滤的临时历史，把选定路径统一改写到 `apps/dashboard/` 后合入 monorepo。根项目继续承担集成层职责，嵌套 Dashboard 元数据和迁移期兼容入口留到后续 M3 再处理。

技术栈：`git-filter-repo`、Git、Python、uv、pytest、Node.js、npm、Vite，以及根级 foundation checker。

设计依据：`docs/superpowers/specs/2026-08-26-m1-history-preserving-imports-design.md`

## 全局约束

- 使用 Dashboard 源 commit `8f809f58b2cdb4b6c6dee8e8d4c767a6ea30a114`。
- 目标位置为 `apps/dashboard/`，不把 Dashboard 代码放进根 package。
- 排除 `data/raw/`、`web/public/data.json`、`web/public/research.json`、`.env*`、缓存、源仓库 CI 和已经被 `src/` 维护版本替代的历史根级脚本。
- 这个 PR 不导入 Niu Men、`research-workspace`、`market-data-platform` 或 `etf-minute-fetcher`。
- 保持 `research_snapshot.v2`、Dashboard 行为和当时默认证券不变。
- 不创建 submodule、gitlink、长期临时 remote 或根 uv workspace。
- 保持原 Dashboard 和 Niu Men 工作树不变。
- Python 版本保持 `>=3.11`。

---

### Task 1：记录 Dashboard 导入清单

涉及文件：

- 新建 `docs/migration/dashboard-import.md`
- 修改 `docs/migration/source-commits.md`
- 修改 `docs/migration/README.md`

输出：可复现的源路径映射、排除列表和回滚记录。

- [ ] Step 1：记录精确路径映射

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

排除项需要明确记录，并说明这些排除作用于重写历史，不只删除最终 checkout 中的文件。

- [ ] Step 2：更新迁移状态

当时将 Dashboard M1 标记为进行中，Niu Men 保持为下一独立 PR，并在 `source-commits.md` 记录源 commit。

- [ ] Step 3：验证并提交文档

```bash
rg -n "8f809f58b2cdb4b6c6dee8e8d4c767a6ea30a114|data/raw|research.json|apps/dashboard" docs/migration
git diff --check
git add docs/migration
git commit -m "docs: record Dashboard M1 import manifest"
```

### Task 2：过滤并合入 Dashboard 历史

输出：保留源历史的 Dashboard 合并提交，并确保保护路径没有进入导入历史。

- [ ] Step 1：创建临时源 clone

```bash
IMPORT_TMP=$(mktemp -d)
git clone --no-local /path/to/user/code/wu-t0-trading-dashboard "$IMPORT_TMP/dashboard"
cd "$IMPORT_TMP/dashboard"
git checkout --detach 8f809f58b2cdb4b6c6dee8e8d4c767a6ea30a114
```

- [ ] Step 2：用 `git-filter-repo` 重写路径

根据 Task 1 的 `--path` 和 `--path-rename` 规则，将五个目录和列出的单文件全部写到 `apps/dashboard/`。

随后再次过滤生成数据：

```bash
uvx --from git-filter-repo git-filter-repo --force --invert-paths \
  --path apps/dashboard/web/public/data.json \
  --path apps/dashboard/web/public/research.json
```

合入前确认过滤后的 clone 不包含 `data/`、`artifacts/`、`.env*` 或源 CI 路径。

- [ ] Step 3：合并并清理临时历史

```bash
git remote add dashboard-m1 "$IMPORT_TMP/dashboard"
git fetch dashboard-m1 HEAD
git merge --allow-unrelated-histories --no-commit FETCH_HEAD
```

当时只允许解决 `apps/dashboard/README.md` 的占位冲突，保留导入 README 并增加 monorepo 边界说明。提交后删除临时 remote 和临时 clone。

- [ ] Step 4：验证历史边界

```bash
git log --follow --oneline -- apps/dashboard/src/trading_research/dashboard/astock_tech.py | head -20
git log --all --name-only --format= -- apps/dashboard/data apps/dashboard/web/public/data.json apps/dashboard/web/public/research.json
git ls-files --stage | awk '$1 == "160000" {print}'
git submodule status
git diff --check
```

保护路径、gitlink 和 submodule 查询都应为空。

### Task 3：接入 monorepo 治理

涉及：

- `scripts/check_foundation.py`
- `tests/test_foundation.py`
- 根 `README.md`
- `docs/migration/README.md`
- `docs/migration/source-commits.md`
- `.github/workflows/foundation.yml`

输出：M1 边界检查明确接受 Dashboard 路径，同时继续拒绝受保护和无关路径。

- [ ] Step 1：增加失败边界测试

| 测试路径 | 预期 |
| --- | --- |
| `apps/dashboard/src/trading_research/dashboard/astock_tech.py` | 接受 |
| `apps/dashboard/web/src/App.tsx` | 接受 |
| `apps/dashboard/data/raw/example.csv` | 拒绝 |
| `apps/dashboard/web/public/research.json` | 拒绝 |
| `apps/dashboard/.env` | 拒绝 |
| `packages/niu-men-line-strategy/src/placeholder.py` | 拒绝 |

- [ ] Step 2：更新 checker

把 M0 的精确文件集合扩展成显式 M1 allowlist，继续保留原始数据、生成快照、artifact、凭据、gitlink 和外部目录的禁止规则。

- [ ] Step 3：更新状态文档

当时根 README 需要说明 Dashboard M1 已导入，Niu Men 仍是下一阶段，并链接 Dashboard import manifest。

- [ ] Step 4：验证并提交

```bash
uv run --locked --extra dev pytest tests/test_foundation.py -q
uv run --locked python scripts/check_foundation.py
git add scripts/check_foundation.py tests/test_foundation.py README.md docs/migration .github/workflows/foundation.yml
git commit -m "build: integrate Dashboard M1 boundary checks"
```

### Task 4：验证 Dashboard Python 与 Web

除非发现明确的导入兼容缺陷，这一任务不改生产代码。

- [ ] Step 1：运行嵌套 Python 测试

```bash
uv run --project apps/dashboard --locked pytest -q
```

- [ ] Step 2：运行 Web 测试和生产构建

```bash
npm ci --prefix apps/dashboard/web
npm test --prefix apps/dashboard/web -- --run
npm run build --prefix apps/dashboard/web
```

- [ ] Step 3：运行 monorepo 验证

```bash
uv lock --check
uv run --locked --extra dev pytest -q
uv run --locked python scripts/check_foundation.py
git status --short
git diff --check
```

- [ ] Step 4：记录验证审计

把精确命令结果、代表性 `git log --follow`、空的保护路径查询和原 Dashboard 工作树未变化证据追加到 `docs/migration/dashboard-import.md`。

这些首次验证结果已经保留在该历史记录中，后续不应改写成新的测试数量。

### Task 5：发布 Dashboard 迁移 PR

- [ ] Step 1：整理最终分支

最终分支名：

```text
feat/m1-dashboard-history-import
```

只包含 Dashboard M1 和已批准的设计、计划文档。

- [ ] Step 2：推送并建立 PR

```bash
git push -u origin feat/m1-dashboard-history-import
gh pr create --base main --head feat/m1-dashboard-history-import \
  --title "feat: import Dashboard history into monorepo" \
  --body-file docs/migration/dashboard-import.md
```

- [ ] Step 3：等待审查

在 PR 审查通过前不合并，也不清理对应 branch 或 worktree。Niu Men 使用单独计划和 PR。

## 当前结果

这份历史计划已经执行完成，Dashboard 已进入 `apps/dashboard/`。后续功能、部署和维护状态应查看现行 Dashboard 文档与 `docs/migration/README.md`，不要把本文件中的首次迁移命令当成日常开发流程。
