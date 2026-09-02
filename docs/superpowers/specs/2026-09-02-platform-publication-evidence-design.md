# Dashboard Platform Publication Evidence Design

## Goal

Expose workspace research evidence in the Dashboard without adding a live backend dependency and without weakening the existing GitHub Pages / Cloudflare Workers static deployment model.

## Design

The Dashboard treats `research.platform-publication.v1` as an external wire contract. A build/publication installer validates the manifest, rejects internal Dashboard-targeted artifacts, verifies SHA-256, filters the public projection, and writes only static files under `web/public/platform/` plus a filtered `platform-publication.json`.

A dedicated publication workflow opens a scoped PR for those static files. This makes the research evidence durable across ordinary future deployments instead of keeping it as ephemeral workflow state.

The browser has a small TypeScript parser for the filtered public manifest and a Strategy Research `研究证据` tab. Missing or malformed publication is isolated from market and strategy snapshot loading.

## Non-goals

- no workspace Python package/runtime dependency in the browser;
- no research metric recomputation in React;
- no internal/private artifact disclosure;
- no large raw research outputs committed to the Dashboard;
- no replacement of existing strategy snapshot contracts.
