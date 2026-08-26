# Migration roadmap

The A-share trading research integration monorepo is introduced in five
reviewable phases. Existing source repositories remain active until a later
cutover decision.

- **M0 — foundation:** establish governance, target-layout markers, migration
  records, and a structural CI check. The monorepo is not the runtime source of
  truth.
- **M1 — history-preserving imports:** Dashboard is imported into
  `apps/dashboard` with practical history and compatibility entry points
  retained. Niu Men is the next separate PR.
- **M2 — shared contract extraction:** move snapshot schema, fixtures, and
  provenance rules to `packages/research-core` and compatible root schema
  locations, without changing the `niu_men.research_snapshot.v2` wire version.
- **M3 — Python package and runtime convergence:** package the Dashboard
  boundary and introduce explicit local package dependencies on Python 3.11 or
  newer.
- **M4 — CI and release cutover:** expand path-aware validation and add release
  workflows; any decision to make this repository authoritative is separately
  reviewed after successful release cycles.

The approved [design specification](../superpowers/specs/2026-08-26-a-share-trading-research-monorepo-design.md)
defines the ownership and compatibility boundaries. The [implementation plan](../superpowers/plans/2026-08-26-monorepo-foundation.md)
contains the task sequence. See the [Dashboard import manifest](dashboard-import.md)
and [source commits](source-commits.md) for the import boundary and first import
rollback points.
