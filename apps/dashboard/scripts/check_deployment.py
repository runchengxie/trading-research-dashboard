"""Check that a deployed static Dashboard exposes the required assets."""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from typing import Any
from urllib.request import urlopen

Opener = Callable[..., Any]
Checker = Callable[[str], None]
Sleeper = Callable[[float], None]
SUPPORTED_RESEARCH_SCHEMAS = {
    "niu_men.research_snapshot.v1",
    "niu_men.research_snapshot.v2",
}


def _url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def _read_text(url: str, *, opener: Opener, timeout: float) -> str:
    with opener(url, timeout=timeout) as response:
        return response.read().decode("utf-8")


def _read_json(url: str, *, opener: Opener, timeout: float) -> dict[str, Any]:
    payload = json.loads(_read_text(url, opener=opener, timeout=timeout))
    if not isinstance(payload, dict):
        raise ValueError(f"{url} must return a JSON object")
    return payload


def check_once(
    base_url: str,
    *,
    opener: Opener = urlopen,
    timeout: float = 15.0,
) -> None:
    index = _read_text(_url(base_url, "/"), opener=opener, timeout=timeout)
    if 'id="root"' not in index and "id='root'" not in index:
        raise ValueError("homepage does not contain application root")

    dashboard = _read_json(
        _url(base_url, "/data.json"), opener=opener, timeout=timeout
    )
    if not isinstance(dashboard.get("generatedAt"), str):
        raise ValueError("data.json generatedAt is missing")
    if not isinstance(dashboard.get("stocks"), list):
        raise ValueError("data.json stocks is missing")

    research = _read_json(
        _url(base_url, "/research.json"), opener=opener, timeout=timeout
    )
    schema_version = research.get("schemaVersion")
    if schema_version not in SUPPORTED_RESEARCH_SCHEMAS:
        raise ValueError("research.json schemaVersion is missing or unsupported")


def check_with_retries(
    base_url: str,
    *,
    retries: int = 10,
    delay_seconds: float = 6.0,
    check: Checker = check_once,
    sleeper: Sleeper = time.sleep,
) -> None:
    if retries <= 0:
        raise ValueError("retries must be positive")
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            check(base_url)
            return
        except Exception as exc:  # noqa: BLE001 - retain the final deployment cause
            last_error = exc
            if attempt < retries:
                sleeper(delay_seconds)
    raise RuntimeError(
        f"deployment check failed after {retries} attempts: {last_error}"
    ) from last_error


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url")
    parser.add_argument("--retries", type=int, default=10)
    parser.add_argument("--delay-seconds", type=float, default=6.0)
    return parser


def main() -> None:
    args = _parser().parse_args()
    check_with_retries(
        args.base_url,
        retries=args.retries,
        delay_seconds=args.delay_seconds,
    )
    print(f"deployment check passed: {args.base_url}")


if __name__ == "__main__":
    main()
