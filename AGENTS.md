# Agent 与协作者指南

## 仓库边界

- `research-workspace`、`market-data-platform`、`etf-minute-fetcher` 等研究与行情基础设施继续放在本仓库之外。
- 不提交原始行情、完整 OOS CSV、凭据、本机数据根目录或其他仅适用于单台机器的产物。
- 迁移期间保持 `niu_men.research_snapshot.v2` 兼容。
- Dashboard 与 Niu Men 继续保持清晰边界，只有经过审查的迁移 PR 才能调整所有权或依赖关系。
- 当前仓库不使用 Git submodule，也不应通过 gitlink 引入外部项目。

## 并行开发

- 每项独立改动使用单独的 worktree 和分支。
- 每个 worktree 的改动通过独立 pull request 合入，进行并行工作时不要直接修改共享的 `main` 工作区。
- PR 合入 `main` 后再清理对应 worktree。
- 合并完成后同步 `main`，删除已经完成的远端和本地功能分支，并移除 worktree。
- 多个 agent 不得共用同一个 worktree 或分支。若改动会触及相同文件，应按顺序处理，或通过经过审查的 PR 协调。

## 验证原则

- 修复行为问题时先补能复现问题的测试，再修改实现。
- 文档中的命令、目录、部署方式和功能说明应以当前代码与 workflow 为事实来源。
- 新增功能应优先复用现有模块边界，避免重复实现数据获取、缓存、契约解析等已有能力。
- 删除兼容入口、迁移脚本或历史代码前，先确认仓库内外是否仍有调用方，并在独立 PR 中完成。

## GitHub Actions 配额

- GitHub Actions 目前仅支持手动触发，因为仓库的 Actions 配额有限。
- 未经仓库所有者明确决定，不要重新启用 pull request 或 push 自动触发。
- 只有在明确需要部署或完整验证时才手动运行 workflow。
- `Monorepo foundation` 用于完整质量检查，`Deploy Dashboard` 用于前端测试、构建、Workers 部署和可选的部署后检查。
