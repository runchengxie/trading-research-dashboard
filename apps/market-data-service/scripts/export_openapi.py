from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from market_data_service.openapi_export import render_openapi_json, write_openapi_json


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export Market Data Service OpenAPI schema")
    parser.add_argument("output", nargs="?", help="Optional JSON output path; stdout by default")
    args = parser.parse_args(argv)

    if args.output:
        write_openapi_json(args.output)
    else:
        sys.stdout.write(render_openapi_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
