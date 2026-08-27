# R-Breaker runtime publication closure

## Goal

Make the Dashboard deployment path fail when an R-Breaker-enabled deployment serves the SPA HTML fallback instead of the generated JSON snapshot, while keeping the snapshot generation based on a real `rbreaker-input.v1` artifact.

## Tasks

1. Replace stale package names in Dashboard workflows with the current workspace package.
2. Add a required R-Breaker deployment check for JSON content and the strategy snapshot schema.
3. Add regression tests for the workflow and deployment checker.
4. Run focused tests, lint, and diff checks, then merge the verified code into `main`.
5. Record the remaining operational steps: obtain a real research artifact, run the publish/deploy workflows, and verify the public endpoint and UI.

## Constraints

- Do not replace the checked-in sample snapshot with fabricated production data.
- Do not claim production publication until the deployed endpoint returns JSON generated from a real artifact.
- Preserve the optional legacy `research.json` behavior for deployments without R-Breaker enabled.
