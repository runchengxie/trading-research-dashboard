# Agent 与协作者指南

## 仓库边界

- `research-workspace`、`market-data-platform`、`etf-minute-fetcher` 等研究与行情基础设施继续放在本仓库之外。这些目录是独立仓库，不是当前项目的 Git submodule。
- 不提交原始行情、完整 OOS CSV、凭据、本机数据根目录或其他仅适用于单台机器的产物。
- 迁移期间保持 `niu_men.research_snapshot.v2` 兼容。
- Dashboard 与 Niu Men 继续保持清晰边界，只有经过审查的迁移 PR 才能调整所有权或依赖关系。
- 当前仓库不使用 Git submodule，也不应通过 gitlink 引入外部项目。
- 前端依赖由根目录 `pnpm-workspace.yaml` 和 `pnpm-lock.yaml` 管理，禁止重新提交 `apps/dashboard/web/package-lock.json`。

## 并行开发

- 每项独立改动使用单独的 worktree 和分支。
- 每个 worktree 的改动通过独立 pull request 合入，进行并行工作时不要直接修改共享的 `main` 工作区。
- PR 合入 `main` 后再清理对应 worktree。
- 合并完成后同步 `main`，删除已经完成的远端和本地功能分支，并移除 worktree。
- 多个 agent 不得共用同一个 worktree 或分支。若改动会触及相同文件，应按顺序处理，或通过经过审查的 PR 协调。

### 标准任务生命周期

除只读审计、状态查询和用户明确要求的紧急 hotfix 外，所有代码、测试、配置和可发布数据改动都遵循下面的顺序：

1. 从最新的 `origin/main` 创建独立 worktree 和任务分支。推荐分支名为 `feat/<topic>`、`fix/<topic>`、`research/<topic>` 或 `chore/<topic>`。
2. 在该 worktree 内完成需求分析、实现和验证。一个 agent 只能占用一个任务 worktree；不得在另一个 agent 的目录中修改文件。
3. 提交前检查工作树、测试结果、差异范围、敏感文件和生成物。原始行情、缓存、虚拟环境、完整回测产物和本机路径不得进入 PR。
4. 将任务分支推送到远程并创建 PR，目标分支固定为 `main`。PR 描述必须说明目的、主要改动、验证命令、已知限制和是否需要部署。
5. 只在 PR review、必需检查和冲突处理完成后合并。默认采用 squash merge；若仓库维护者另有要求，以维护者要求为准。禁止多个 agent 同时直接向 `main` 推送互相竞争的提交。
6. 合并后回到主仓库同步 `main`，确认合并提交已存在，再依次删除远程任务分支、本地任务分支，并移除对应 worktree，最后运行 `git worktree prune`。
7. 清理后再次确认：主仓库工作树干净、`main` 与 `origin/main` 一致、没有残留任务分支或 worktree；如果 PR 未合并，不得删除仍承载唯一改动的 worktree。

### Worktree 与 PR 安全边界

- 创建 worktree 前先执行 `git fetch origin`，以 `origin/main` 为基线；不要从可能落后的本地 `main` 分叉。
- worktree 路径应集中在仓库外的明确目录，例如 `/path/to/user/code/worktrees/<repo>-<topic>`，避免在仓库内部产生嵌套 worktree。
- 删除 worktree 前必须确认其改动已经进入合并后的 `main`。如果存在未提交或未推送内容，先列出文件并选择提交、转移或明确放弃；不得使用 `--force` 静默丢弃。
- 发现已有未处理的 worktree、分支或 PR 时，先做只读盘点并标注归属，不要把它们自动并入当前任务，也不要因为“看起来过期”就删除。
- 同一任务若需要多个 agent，先拆成文件边界清晰、可独立 review 的 PR；共享接口变更应由一个 agent 负责，其他 agent 基于已合并的接口继续。
- 直接在 `main` 工作树上的改动只有在用户明确要求、且不适合开 PR 时才允许；完成后仍需记录原因和验证结果。

### 合并与清理记录

每个完成的任务至少保留以下可追溯信息：PR URL、合并后的 main commit、实际运行的验证命令、部署结果（如有）以及未完成项。记录可以放在 PR 描述、提交信息或对应的研究/维护文档中。

如果测试失败、PR 有冲突、远程分支发生 ahead/behind，先停止合并和清理，报告具体阻塞原因。只有在确认改动归属和恢复路径后，才可以继续处理；不得通过强制推送、硬重置或删除 worktree 来掩盖状态。

## 验证原则

- 修复行为问题时先补能复现问题的测试，再修改实现。
- 文档中的命令、目录、部署方式和功能说明应以当前代码与 workflow 为事实来源。
- 新增功能应优先复用现有模块边界，避免重复实现数据获取、缓存、契约解析等已有能力。
- 删除兼容入口、迁移脚本或历史代码前，先确认仓库内外是否仍有调用方，并在独立 PR 中完成。

## GitHub Actions 配额

- GitHub Actions 目前仅支持手动触发，因为仓库的 Actions 配额有限。
- 未经仓库所有者明确决定，不要重新启用 pull request 或 push 自动触发。
- 只有在明确需要部署或完整验证时才手动运行 workflow。
- `Agent paper portfolio` 是已明确批准的例外，保留每个工作日一次的 schedule。它只运行纸面组合实验，不接收券商凭据，也不发送真实订单。
- `Monorepo foundation` 用于完整质量检查，`Deploy Dashboard` 用于前端测试、构建、Workers 部署和可选的部署后检查。前端 CI 使用 `pnpm/action-setup`、`pnpm install --frozen-lockfile`、workspace filter 和 `pnpm audit`。

## 文档规范

- 当前状态、命令、目录和 workflow 名称以代码、配置和现行 workflow 为准。历史迁移记录可以保留当时的测试结果，但需要明确标注为历史结果。
- 中文说明使用中文标点。路径、命令、代码标识符、schema 名称和必要的技术名词保持原样。
- 文案尽量直接、简洁，避免翻译腔、无必要的中英混排、连续使用否定式铺垫，以及用视觉强调替代清晰结构。
- 修改文档中的命令后，至少检查命令的执行目录、相对路径和当前依赖入口。不要记录未经实际运行的验证结果。
- 维护性审查记录放在 `docs/maintenance/quality-audit.md`。大范围重构应先记录调用方、依赖边界和回滚方式。
