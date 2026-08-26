# Cloudflare Workers deployment

The dashboard is a static React application. The repository keeps Python
research and data generation outside the browser and deploys only the Vite
output from `web/dist` to Cloudflare Workers Static Assets.

## Local deployment

Build the site from the repository root:

```bash
cd web
npm ci
npm run build
cd ..
npx wrangler@4 deploy --dry-run
```

The deployment configuration is [wrangler.jsonc](../wrangler.jsonc). It
serves `web/dist`, enables SPA fallback for client-side navigation, and does
not bundle the Python research repositories.

For a live deployment, authenticate Wrangler with a Cloudflare API token and
account ID, then run:

```bash
export CLOUDFLARE_API_TOKEN=...
export CLOUDFLARE_ACCOUNT_ID=...
npx wrangler@4 deploy
```

The token needs permission to deploy Workers. Keep it in the shell environment
or a CI secret; do not write it to this repository.

## GitHub Actions

The scheduled report workflow builds the static site first and deploys it when
the repository variable `CLOUDFLARE_ACCOUNT_ID` is set. Configure:

- secret `CLOUDFLARE_API_TOKEN`
- variable `CLOUDFLARE_ACCOUNT_ID`
- optional variable `CLOUDFLARE_PUBLIC_URL`, used for the post-deploy smoke check

If the account variable is empty, the workflow still generates and tests the
site but skips the external deployment step. This keeps forks and local CI
usable without Cloudflare credentials.

The static `data.json` and `research.json` snapshot boundary is unchanged. A
future Worker or R2 binding can be added behind that boundary if the dashboard
eventually needs live APIs or larger snapshot storage.
