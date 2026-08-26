# 文档审查与中文化实施计划

> 面向协作者：按复选框逐项完成，每项修改后检查链接、命令和事实是否与当前仓库一致。

**目标：** 统一当前 monorepo 的中文说明，修正文档中的路径、测试、部署和迁移状态，并保留必要的英文技术名称与历史记录。

**架构：** 以代码、配置和 workflow 作为事实来源，优先更新根 README、协作者指南、Dashboard 说明和迁移状态。设计与实施计划中的历史内容保留原始上下文，只在会造成当前状态误解的位置补充说明。

**技术栈：** Markdown、Python、uv、pytest、Ruff、npm、Vite、Cloudflare Workers、GitHub Actions。

**规范：** 用户提供的中文文档语言与标点要求。

## 全局约束

- 中文正文使用中文标点，路径、命令、代码标识符和技术名词保持原样。
- 不修改业务代码、数据快照或策略逻辑。
- 不把历史计划中的当时状态改写成当前事实。
- 当前 GitHub Actions 仅允许 `workflow_dispatch` 手动触发。
- 当前 Niu Men 源码尚未进入 monorepo，`research-core` 仍是占位目录。

### 任务一：校准根级文档

- [x] 更新根 README 的当前状态、验证命令、PR #7 合并结果和后续迁移边界。
- [x] 更新 `AGENTS.md` 的工作流、Actions 配额和文档事实来源说明。

### 任务二：校准 Dashboard 文档

- [x] 修正 Dashboard README 中的路径、来源名称、测试命令和当前生产地址。
- [x] 检查 `apps/dashboard/docs/` 中的部署、输出、前端、数据源和排错说明。
- [x] 统一缺失研究快照、静态 JSON、PNG 导出和 Workers Static Assets 的表述。

### 任务三：校准迁移与包说明

- [x] 更新 `docs/migration/` 的阶段状态，明确 Dashboard 已完成、Niu Men 和 `research-core` 尚未完成。
- [x] 更新两个 package README，说明当前占位状态和未来边界。
- [x] 对历史 spec 和 plan 只补充必要的历史说明，不重写已完成工作的记录。

### 任务四：验证

- [x] 检查 Markdown 链接、命令路径、workflow 名称和关键状态词。
- [ ] 运行根级测试和 foundation checker。
- [x] 检查 diff 中没有业务代码或数据文件改动。
- [ ] 提交独立 PR，等待审查后再合并和清理 worktree。
