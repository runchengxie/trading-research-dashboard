# Runtime Report and Maintenance Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 runtime report 对缺失候选标的的错误失败，并同步项目维护文档与质量检查事实。

**Architecture:** 保留候选快照校验的基线保护，只允许 shadow 运行在 provider 缺少单个标的时继续完成。通过测试锁定行为，再更新 workflow 和维护文档，最后运行仓库现有质量门禁。

**Tech Stack:** Python 3.11、pytest、Ruff、uv、pnpm、GitHub Actions。

**Spec:** 用户提出的分支、worktree、CI、文档和代码维护审查要求。

## Global Constraints

- `main` 只通过 PR 接收改动。
- 修复行为问题必须先写失败测试，再修改实现。
- 不删除仍可能被外部调用的兼容入口或脚本。
- 中文说明使用中文标点，保留必要的行内代码引用。

---

### Task 1: 修复 runtime candidate 校验

**Files:**
- Modify: `apps/dashboard/scripts/check_runtime_candidate.py`
- Test: `tests/test_runtime_candidate.py`

- [ ] 写出 shadow 模式允许候选缺少 baseline 标的的失败测试。
- [ ] 运行该测试，确认因当前校验无模式参数而失败。
- [ ] 增加显式 `--mode shadow|authoritative` 参数，shadow 记录缺失标的并继续，authoritative 保持失败。
- [ ] 运行候选校验测试和 Dashboard 全量测试。

### Task 2: 同步 workflow 与文档

**Files:**
- Modify: `.github/workflows/dashboard-report.yml`
- Modify: `README.md`
- Modify: `docs/maintenance/quality-audit.md`

- [ ] 让 runtime report 将 `SCHEDULE_MODE` 传给候选校验脚本。
- [ ] 记录当前失败原因、修复边界和仍需观察的 provider 缺失情况。
- [ ] 检查 README、AGENTS.md、docs 中的过期命令、路径和中英文标点。

### Task 3: 质量验证与交付

- [ ] 运行 Python、前端、Ruff、类型检查和安全审计中仓库已有且可执行的门禁。
- [ ] 运行 `git diff --check` 和敏感信息扫描。
- [ ] 提交分支，创建 PR，确认检查通过后合并到 `main`。
- [ ] 删除已合并的远程和本地分支及 worktree，并复核 `main` 与 `origin/main` 一致。
