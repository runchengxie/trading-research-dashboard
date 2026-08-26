# Agent and contributor guidance

- Keep `research-workspace` and market-data infrastructure outside this repository.
- Do not commit raw market data, full OOS CSV files, credentials, or local data roots.
- Preserve `niu_men.research_snapshot.v2` during migration.
- Keep Dashboard and Niu Men boundaries separate until a migration PR explicitly changes them.
- Use a worktree and a pull request for each migration phase.
