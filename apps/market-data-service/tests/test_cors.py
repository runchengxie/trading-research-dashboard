from fastapi.testclient import TestClient

from market_data_service.app import create_app


def test_healthz_allows_configured_browser_origin() -> None:
    client = TestClient(
        create_app(cors_origins=("https://dashboard.example",))
    )

    response = client.get(
        "/healthz",
        headers={"Origin": "https://dashboard.example"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://dashboard.example"


def test_healthz_does_not_allow_unlisted_browser_origin() -> None:
    client = TestClient(
        create_app(cors_origins=("https://dashboard.example",))
    )

    response = client.get(
        "/healthz",
        headers={"Origin": "https://other.example"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
