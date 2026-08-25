import json

import pytest

from scripts.check_deployment import check_once, check_with_retries


class _Response:
    def __init__(self, body: str, content_type: str) -> None:
        self._body = body.encode("utf-8")
        self.headers = {"Content-Type": content_type}

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _opener(payloads: dict[str, tuple[str, str]]):
    def open_url(url: str, timeout: float = 0):
        del timeout
        path = "/" + url.split("/", 3)[-1] if url.count("/") >= 3 else "/"
        if url.endswith("/"):
            path = "/"
        body, content_type = payloads[path]
        return _Response(body, content_type)

    return open_url


def test_check_once_accepts_complete_static_deployment() -> None:
    opener = _opener(
        {
            "/": ('<html><div id="root"></div></html>', "text/html"),
            "/data.json": (
                json.dumps({"generatedAt": "2026-08-25", "stocks": []}),
                "application/json",
            ),
            "/research.json": (
                json.dumps({"schemaVersion": "niu_men.research_snapshot.v1"}),
                "application/json",
            ),
        }
    )

    check_once("https://example.pages.dev", opener=opener)


def test_check_once_accepts_research_schema_v2() -> None:
    opener = _opener(
        {
            "/": ('<html><div id="root"></div></html>', "text/html"),
            "/data.json": (
                json.dumps({"generatedAt": "2026-08-25", "stocks": []}),
                "application/json",
            ),
            "/research.json": (
                json.dumps({"schemaVersion": "niu_men.research_snapshot.v2"}),
                "application/json",
            ),
        }
    )

    check_once("https://example.pages.dev", opener=opener)


def test_check_once_rejects_missing_research_schema() -> None:
    opener = _opener(
        {
            "/": ('<div id="root"></div>', "text/html"),
            "/data.json": (
                json.dumps({"generatedAt": "2026-08-25", "stocks": []}),
                "application/json",
            ),
            "/research.json": (json.dumps({}), "application/json"),
        }
    )

    with pytest.raises(ValueError, match="research.json schemaVersion"):
        check_once("https://example.pages.dev", opener=opener)


def test_check_once_rejects_unsupported_research_schema() -> None:
    opener = _opener(
        {
            "/": ('<div id="root"></div>', "text/html"),
            "/data.json": (
                json.dumps({"generatedAt": "2026-08-25", "stocks": []}),
                "application/json",
            ),
            "/research.json": (
                json.dumps({"schemaVersion": "niu_men.research_snapshot.v999"}),
                "application/json",
            ),
        }
    )

    with pytest.raises(ValueError, match="research.json schemaVersion"):
        check_once("https://example.pages.dev", opener=opener)


def test_check_with_retries_raises_after_last_attempt() -> None:
    attempts = 0

    def failing_check(base_url: str) -> None:
        nonlocal attempts
        del base_url
        attempts += 1
        raise ValueError("not ready")

    with pytest.raises(RuntimeError, match="3 attempts"):
        check_with_retries(
            "https://example.pages.dev",
            retries=3,
            delay_seconds=0,
            check=failing_check,
            sleeper=lambda _: None,
        )

    assert attempts == 3
