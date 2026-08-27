# R-Breaker publication verification note

This branch implements the approved production publication boundary for R-Breaker. Full repository verification remains required before the pull request can be marked ready.

Required verification in a real checkout:

```text
uv lock --check
uv run --locked --extra dev pytest -q
uv run --locked --all-packages ruff check .
uv run --locked python scripts/check_foundation.py
npm ci --prefix apps/dashboard/web
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
```

The implementation must remain draft until those commands have fresh successful output. This note is evidence of an open gate, not evidence that the gate passed.
