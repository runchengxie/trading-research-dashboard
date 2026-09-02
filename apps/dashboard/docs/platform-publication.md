# Platform research publication

The Dashboard can persist and display public research projections from `research-workspace` while remaining a static Vite application deployable to both GitHub Pages and Cloudflare Workers Static Assets.

## Boundary

The Dashboard never needs a live `research-workspace` API. Research owners produce a `research.platform-publication.v1` bundle. The Dashboard publication workflow downloads that bundle, validates the public projection, verifies SHA-256 identities, and opens a scoped PR that changes only:

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
- any `audience=internal` artifact explicitly targeted at `trading-research-dashboard`.

The installed public manifest is filtered before it enters Git. It contains only `public` artifacts explicitly declaring the Dashboard as a consumer. Internal artifact ids and paths are not copied into the public site.

## UI

The Strategy Research workspace includes a **研究证据** tab. It reads only the checked-in static `platform-publication.json` and shows:

- producer repository and commit;
- research run id and generation timestamp;
- public projection count;
- artifact id, schema, media type, SHA-256 prefix, and static projection link.

Missing publication is an allowed empty state and does not affect market data or existing strategy snapshots. Malformed publication is isolated to the evidence view.

## Publication workflow

Run `.github/workflows/publish-platform-publication.yml` with:

- producer repository;
- producer workflow run id;
- artifact name (default `dashboard-publication-v1`).

Cross-repository download uses `RESEARCH_ARTIFACT_TOKEN`, matching existing research-artifact boundaries. The workflow validates, tests, builds, stages only the public publication paths, and opens a scoped PR.
