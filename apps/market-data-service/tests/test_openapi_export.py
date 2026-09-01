import json

from market_data_service.openapi_export import render_openapi_json, write_openapi_json


def test_render_openapi_json_contains_market_data_paths() -> None:
    schema = json.loads(render_openapi_json())

    assert schema["info"]["title"] == "Market Data Service"
    assert "/v1/quotes/{symbol}" in schema["paths"]
    assert "/v1/bars/{symbol}" in schema["paths"]


def test_write_openapi_json_writes_utf8_schema(tmp_path) -> None:
    output = tmp_path / "market-data-openapi.json"

    write_openapi_json(output)

    schema = json.loads(output.read_text(encoding="utf-8"))
    assert "QuoteResponse" in schema["components"]["schemas"]
    assert output.read_text(encoding="utf-8").endswith("\n")
