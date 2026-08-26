import json
from urllib.error import HTTPError
from urllib.request import Request

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


def _dashboard_payload() -> str:
    return json.dumps({"generatedAt": "2026-08-25", "stocks": [{"code": "sz300246"}]})


def _opener(payloads: dict[str, tuple[str, str]]):
    def open_url(request: Request, timeout: float = 0):
        del timeout
        url = request.full_url
        path = "/" + url.split("/", 3)[-1] if url.count("/") >= 3 else "/"
        if url.endswith("/"):
            path = "/"
        body, content_type = payloads[path]
        return _Response(body, content_type)

    return open_url


def test_check_once_sets_a_descriptive_user_agent() -> None:
    requests: list[Request] = []

    def opener(request: Request, timeout: float = 0):
        del timeout
        requests.append(request)
        path = "/" + request.full_url.split("/", 3)[-1]
        payloads = {
            "/": '<html><div id="root"></div></html>',
            "/data.json": _dashboard_payload(),
            "/research.json": json.dumps(
                {"schemaVersion": "niu_men.research_snapshot.v1"}
            ),
        }
        return _Response(payloads[path], "application/json")

    check_once("https://example.pages.dev", opener=opener)

    assert requests
    assert requests[0].get_header("User-agent") == (
        "wu-t0-trading-dashboard-deployment-check/1.0"
    )


def test_check_once_accepts_complete_static_deployment() -> None:
    opener = _opener(
        {
            "/": ('<html><div id="root"></div></html>', "text/html"),
            "/data.json": (_dashboard_payload(), "application/json"),
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
            "/data.json": (_dashboard_payload(), "application/json"),
            "/research.json": (
                json.dumps({"schemaVersion": "niu_men.research_snapshot.v2"}),
                "application/json",
            ),
        }
    )

    check_once("https://example.pages.dev", opener=opener)


def test_check_once_accepts_missing_optional_research_snapshot() -> None:
    opener = _opener(
        {
            "/": ('<html><div id="root"></div></html>', "text/html"),
            "/data.json": (_dashboard_payload(), "application/json"),
            "/research.json": ('<html><div id="root"></div></html>', "text/html"),
        }
    )

    check_once("https://example.pages.dev", opener=opener)


def test_check_once_accepts_research_404() -> None:
    def opener(request: Request, timeout: float = 0):
        del timeout
        path = "/" + request.full_url.split("/", 3)[-1]
        if path == "/research.json":
            raise HTTPError(request.full_url, 404, "not found", {}, None)
        payloads = {
            "/": ('<html><div id="root"></div></html>', "text/html"),
            "/data.json": (_dashboard_payload(), "application/json"),
        }
        body, content_type = payloads[path]
        return _Response(body, content_type)

    check_once("https://example.pages.dev", opener=opener)


def test_check_once_rejects_empty_dashboard_data() -> None:
    opener = _opener(
        {
            "/": ('<html><div id="root"></div></html>', "text/html"),
            "/data.json": (
                json.dumps({"generatedAt": "2026-08-25", "stocks": []}),
                "application/json",
            ),
            "/research.json": ('<html></html>', "text/html"),
        }
    )

    with pytest.raises(ValueError, match="data.json stocks is empty"):
        check_once("https://example.pages.dev", opener=opener)


def test_check_once_rejects_missing_research_schema() -> None:
    opener = _opener(
        {
            "/": ('<div id="root"></div>', "text/html"),
            "/data.json": (_dashboard_payload(), "application/json"),
            "/research.json": (json.dumps({}), "application/json"),
        }
    )

    with pytest.raises(ValueError, match="research.json schemaVersion"):
        check_once("https://example.pages.dev", opener=opener)


def test_check_once_rejects_unsupported_research_schema() -> None:
    opener = _opener(
        {
            "/": ('<div id="root"></div>', "text/html"),
            "/data.json": (_dashboard_payload(), "application/json"),
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
