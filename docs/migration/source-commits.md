# 首次导入源 commit

| 来源 | 源仓库 | 首次导入基准 commit | 当前角色 |
| --- | --- | --- | --- |
| Dashboard | `runchengxie/wu-t0-trading-dashboard` | `8f809f58b2cdb4b6c6dee8e8d4c767a6ea30a114` | 已导入 `apps/dashboard/`，当前由 monorepo 维护 |
| Niu Men | `runchengxie/niu-men-line-strategy` | `1be7f725772fa824ce34e2bb833867cb4c3e9fcb` | M1 历史保留导入正在独立分支准备；runtime cutover 前仍由原仓库维护 |

这些 SHA 记录的是首次保留历史导入时选定的源基准，用于追溯导入边界和必要时对照原仓库内容。它们不代表源仓库未来永远停留在对应 commit。

首次路径映射、排除规则和验证证据分别见：

- [Dashboard 导入记录](dashboard-import.md)
- [Niu Men 导入记录](niu-men-import.md)

Niu Men 的 `1be7f725772fa824ce34e2bb833867cb4c3e9fcb` 是本次 M1 首次导入的明确 rollback point。M1 只迁移已批准路径与可追溯历史，不改变 `niu_men.research_snapshot.v2`、策略逻辑或外部数据基础设施边界。

当前迁移范围有意排除：

```text
research-workspace
market-data-platform
etf-minute-fetcher
```

这些项目继续通过稳定的数据、文件或研究契约与 monorepo 协作，不作为 Git submodule 引入。
