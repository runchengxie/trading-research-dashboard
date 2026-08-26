# Cloudflare Workers deployment

The dashboard is a static React application. The repository keeps Python
research and data generation outside the browser and deploys only the Vite
output from `web/dist` to Cloudflare Workers Static Assets.

## Local deployment

Build and deploy the site from the monorepo root:

```bash
npm ci --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
npx wrangler@4 deploy --config apps/dashboard/wrangler.jsonc --dry-run
```

The deployment configuration is [wrangler.jsonc](../wrangler.jsonc). It
serves `apps/dashboard/web/dist`, enables SPA fallback for client-side
navigation, and does not bundle the Python research repositories.

For a live deployment, authenticate Wrangler with a Cloudflare API token and
account ID, then run:

```bash
export CLOUDFLARE_API_TOKEN=...
export CLOUDFLARE_ACCOUNT_ID=...
npx wrangler@4 deploy --config apps/dashboard/wrangler.jsonc
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

## Optional Cloudflare Pages deployment

The private GitHub repository can also be connected to Cloudflare Pages, or a
Pages Direct Upload project can be deployed with Wrangler. This is a separate
deployment mode from the Workers Static Assets configuration above:

```bash
npm ci --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
npx wrangler@4 pages deploy apps/dashboard/web/dist \
  --project-name a-share-trading-dashboard
```

Keep this as a separate deployment choice. Do not use both `wrangler deploy`
and `wrangler pages deploy` for the same production project. Pages Direct
Upload is useful when Cloudflare Pages is the desired product or URL; the
current Workers Static Assets route remains the default for this repository.

The static `data.json` and `research.json` snapshot boundary is unchanged. A
future Worker or R2 binding can be added behind that boundary if the dashboard
eventually needs live APIs or larger snapshot storage.
