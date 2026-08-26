# Agent and contributor guidance

- Keep `research-workspace` and market-data infrastructure outside this repository.
- Do not commit raw market data, full OOS CSV files, credentials, or local data roots.
- Preserve `niu_men.research_snapshot.v2` during migration.
- Keep Dashboard and Niu Men boundaries separate until a migration PR explicitly changes them.
- Use a worktree and a pull request for each migration phase.

## Parallel development workflow

- Every independent change must use its own worktree and branch.
- Open a pull request for each worktree's completed change; do not edit the
  shared `main` checkout while parallel work is in progress.
- Merge the pull request into `main` before cleaning up the worktree.
- After a successful merge, fetch `main`, delete the remote and local feature
  branch, and remove the completed worktree.
- Multiple agents must not share a worktree or branch. If changes touch the
  same files, serialize the work or coordinate through a reviewed PR instead
  of allowing concurrent edits to compete.

## GitHub Actions quota

- GitHub Actions workflows are intentionally manual-only for now because the
  repository has limited Actions quota.
- Do not re-enable automatic pull-request or push-triggered CI without an
  explicit decision from the repository owner.
- Run the workflows manually only when a deployment or validation run is
  specifically requested.
