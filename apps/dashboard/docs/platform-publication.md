# Platform research publication

The Dashboard can persist and display public research projections from `research-workspace` while remaining a static Vite application deployable to both GitHub Pages and Cloudflare Workers Static Assets.

## Boundary

The Dashboard never needs a live `research-workspace` API. Research owners produce a `research.platform-publication.v1` bundle. A Dashboard publisher validates the public projection, verifies SHA-256 identities, and opens a scoped PR that changes only:

```text
apps/dashboard/web/public/platform-publication.json
apps/dashboard/web/public/platform/**
```

Once the scoped PR is merged, every normal Dashboard build includes the same research evidence files. A later deployment therefore cannot silently erase the publication state.

## Disclosure firewall

`trading_research.platform_publication` rejects:

- unsupported manifest schema;
- absolute or traversal paths;
- malformed SHA-256 identities;
- missing/tampered files;
- any `audience=internal` artifact explicitly targeted at `trading-research-dashboard`;
- a bundle with no public projection for the Dashboard.

The installed public manifest is filtered before it enters Git. It contains only `public` artifacts explicitly declaring the Dashboard as a consumer. Internal artifact ids and paths are not copied into the public site.

## UI

The Strategy Research workspace includes a **研究证据** tab. It reads only the checked-in static `platform-publication.json` and shows:

- producer repository and commit;
- research run id and generation timestamp;
- public projection count;
- artifact id, schema, media type, SHA-256 prefix, and static projection link.

Missing publication is an allowed empty state and does not affect market data or existing strategy snapshots. Malformed publication is isolated to the evidence view.

## Primary publication path: local / production runner

`research-workspace` currently treats local pre-push and production runners as the source of operational truth and intentionally does not depend on GitHub Actions. The normal cross-project flow is therefore:

```text
research-workspace production/local runner
        |
        | scripts/build_platform_publication.py
        v
research.platform-publication.v1 bundle
        |
        | scripts/publish_platform_publication.py --open-pr
        v
scoped Dashboard static-data PR
        |
        v
normal Pages / Workers deploy
```

From a Dashboard checkout:

```bash
python scripts/publish_platform_publication.py \
  --bundle-root /path/to/platform-publication-bundle \
  --open-pr
```

The publisher refuses unrelated dirty working-tree files, installs only the public Dashboard projection, stages only `platform-publication.json` plus `platform/`, and opens a scoped PR with `gh`.

## Optional GitHub artifact path

`.github/workflows/publish-platform-publication.yml` is an optional convenience for producers/environments that do publish a GitHub Actions artifact. It accepts:

- producer repository;
- producer workflow run id;
- artifact name (default `dashboard-publication-v1`).

Cross-repository download uses `RESEARCH_ARTIFACT_TOKEN`, matching existing research-artifact boundaries. The workflow validates, tests, builds, stages only the public publication paths, and opens the same kind of scoped PR.

This workflow is not required for `research-workspace` itself and must not be treated as evidence that the workspace has enabled GitHub Actions.
