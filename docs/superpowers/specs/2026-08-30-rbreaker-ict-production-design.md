# R-Breaker and ICT Production Research Design

## Goal

Close the operational gap between Alpaca minute data, R-Breaker publication, and the contextual ICT research already implemented in the Dashboard, while adding one explicitly defined executable ICT strategy for falsifiable research.

## Scope

This work is split into two independently reviewable pull requests.

### PR1: Alpaca artifact producer and contextual deployment

Add a manually dispatched GitHub Actions workflow that:

1. accepts a US symbol, regular-session date, Alpaca feed, and an optional incomplete-session override;
2. reads `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` only from GitHub secrets;
3. runs the existing `build_rbreaker_alpaca_artifact.py` producer with SIP by default;
4. validates regular-session coverage, previous-day OHLC, manifest fields, file allowlist, sizes, and SHA-256;
5. uploads the sanitized artifact under the exact name `rbreaker-input-v1`;
6. generates a R-Breaker strategy snapshot from that artifact;
7. runs the existing contextual enrichment so ICT-related context, sessions, reference-level events, day archetypes, intermarket context, and event-study fields enter `data.json`;
8. validates the static assets, runs frontend tests/build, and deploys only when Cloudflare credentials are present;
9. publishes artifact/run metadata in the workflow summary without printing credentials.

The existing `deploy-dashboard.yml` and `publish-rbreaker-snapshot.yml` remain available for consuming or publishing an already-created artifact. Their artifact naming must be made consistent with `rbreaker-input-v1`.

PR1 does not claim that contextual ICT observations are an executable strategy or that a single R-Breaker session is rolling OOS evidence.

### PR2: Executable ICT liquidity-reclaim strategy

Add one strategy-independent, deterministic ICT-inspired strategy with an explicit neutral name: `liquidity_reclaim_v1`.

The first implementation is US regular-session minute-bar research because the Alpaca artifact is US minute data. It uses no discretionary concepts and no hidden model score:

- Long setup: after the opening session begins, a bar trades below the previous regular-session low and closes back above that level.
- Short setup: a bar trades above the previous regular-session high and closes back below that level.
- Entry: next available bar open after the reclaim bar; no same-bar fill.
- Stop: reclaim-bar extreme plus a configurable non-negative buffer in price units.
- Target: a configurable fixed risk multiple, default 1.5R.
- Exit: first stop/target touch using a deterministic same-bar tie rule, or regular-session close if neither is reached.
- Position limit: one completed trade per symbol/session and no overlapping position.
- Costs: explicit per-side bps and slippage parameters, reported separately from gross returns.
- Missing, out-of-session, duplicate, or non-monotonic bars fail validation instead of being silently repaired.

The strategy produces a trade ledger and a generic `trading_research.strategy_snapshot.v1` summary with gross/net return, Sharpe, max drawdown, trade count, win rate, profit factor, MFE, MAE, and explicit provenance. It supports date-based train/test splits, but the initial PR must not call one split “rolling” unless multiple calendar folds are actually present.

The strategy must be exposed as a separate snapshot target in the Dashboard registry. It should display the actual strategy label and a clear “research rule, not investment advice” description. No ICT score, Smart Money causal claim, or unvalidated alpha claim is introduced.

## Data flow

```text
Alpaca SIP
  -> validated rbreaker_input.v1 artifact
  -> R-Breaker snapshot producer
  -> ICT/contextual enrichment of reviewed Dashboard data
  -> strict contract validation
  -> frontend build
  -> Cloudflare Worker deployment

US minute artifact
  -> liquidity_reclaim_v1 signal engine
  -> trade ledger / OOS fold summaries
  -> strategy_snapshot.v1
  -> Dashboard strategy registry
```

## Failure and safety policy

- No API key or secret may be written to logs, JSON artifacts, or Git.
- SIP is the default feed; IEX is opt-in and must be visible in provenance.
- Incomplete sessions are rejected by default; `--allow-incomplete` must be explicit and mark quality as warning.
- A missing artifact, missing previous-day bar, malformed timestamp, schema mismatch, or failed coverage check fails closed.
- A deploy step is skipped when Cloudflare credentials are absent; validation still runs.
- Existing checked-in snapshots are not overwritten by failed generation.
- PR2’s strategy metrics are not mixed into R-Breaker or Niu Men comparison rows unless the generic registry has a distinct strategy identity.

## Verification

PR1 must have:

- workflow contract tests for inputs, secrets, exact artifact name, feed default, contextual enrichment ordering, strict validation, and no credential echo;
- producer and artifact validation tests covering complete, incomplete, duplicate, and missing data;
- Dashboard Python tests, frontend tests, TypeScript build, and static asset validation.

PR2 must have:

- red/green tests for long reclaim, short reclaim, next-bar entry, stop/target ordering, session-close exit, one-trade limit, costs, and malformed input rejection;
- deterministic date-split/OOS tests with real fold dates;
- canonical strategy snapshot schema validation;
- full repository tests, lint, type checks, coverage, and a fixture-based end-to-end snapshot generation test.

## Out of scope

- true multi-window R-Breaker OOS generation;
- claiming ICT setup events are profitable before a cost-aware OOS result exists;
- raw tick storage in GitHub artifacts or the repository;
- automatic daily production deployment;
- discretionary FVG, order-block, liquidity-pool, or “smart money” labels without an objective contract and test.
