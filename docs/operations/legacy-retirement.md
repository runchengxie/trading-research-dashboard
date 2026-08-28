# Legacy Repository Retirement Record

本记录区分“维护权已统一声明”和“生产 freeze/archive 已完成”。后者需要真实 GitHub、部署和外部调用方证据；本地代码变更不会替代这些证据。

## wu-t0-trading-dashboard

| Field | Status |
| --- | --- |
| Repository | `runchengxie/wu-t0-trading-dashboard` |
| Maintenance authority | `trading-research-dashboard`（README 已声明） |
| Current retirement state | `active-legacy / freeze-not-verified` |
| Last-known-good rollback SHA | `e03617a6d6922e2b3fec66a96f1ae3b51f66c38e` |
| Freeze PR | `#44`, prepared; merge evidence not recorded |
| Production writes | not-yet-verified absent |
| External caller audit | not-yet-run |
| Archive operation | not-yet-run |

## niu-men-line-strategy

| Field | Status |
| --- | --- |
| Repository | `runchengxie/niu-men-line-strategy` |
| Maintenance authority | `trading-research-dashboard/packages/niu-men-line-strategy`（README 已声明） |
| Current retirement state | `active-legacy / freeze-not-verified` |
| Last-known-good rollback SHA | `1be7f725772fa824ce34e2bb833867cb4c3e9fcb` |
| Freeze PR | `#22`, prepared; merge evidence not recorded |
| New production publication dependency | not-yet-verified absent |
| Research publication cycles | no qualifying real cycles recorded here |
| External caller audit | not-yet-run |
| Archive operation | not-yet-run |

## Gate interpretation

- README 维护声明已经完成，因此后续开发主线只有 monorepo。
- M6 仍需真实 authoritative run、连续观察和 publication 证据；完成前不能把旧仓库标为 frozen 或 archived。
- M6b 还需逐仓库完成 GitHub-visible、cron/systemd/Hermes/self-hosted runner、Cloudflare 和本地自动化调用方审计。
- 本仓库不删除旧仓库、不提交旧仓库凭据，也不把 archive 当作普通 Git commit。
