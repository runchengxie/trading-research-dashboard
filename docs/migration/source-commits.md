# First import source commits

| Source | Repository | Import source commit | Current role |
| --- | --- | --- | --- |
| Dashboard | https://github.com/runchengxie/wu-t0-trading-dashboard | 8f809f58b2cdb4b6c6dee8e8d4c767a6ea30a114 | standalone Dashboard application |
| Niu Men | https://github.com/runchengxie/niu-men-line-strategy | 1be7f725772fa824ce34e2bb833867cb4c3e9fcb | standalone research and snapshot producer |

These commits are rollback points for the first history-preserving import PR.

Dashboard M1 is active and its reproducible path map and exclusions are recorded
in the [Dashboard import manifest](dashboard-import.md). Niu Men remains the
next separate PR.

`research-workspace`, `market-data-platform`, and `etf-minute-fetcher` are
intentionally excluded from this repository and its migration scope.
