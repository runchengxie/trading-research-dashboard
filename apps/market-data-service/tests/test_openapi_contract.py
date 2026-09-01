from market_data_service.app import create_app


def test_openapi_exposes_named_market_data_response_models() -> None:
    schema = create_app().openapi()
    components = schema["components"]["schemas"]

    assert "HealthResponse" in components
    assert "ReadyResponse" in components
    assert "QuoteResponse" in components
    assert "BarsResponse" in components
    assert (
        schema["paths"]["/v1/quotes/{symbol}"]["get"]["responses"]["200"]["content"]
        ["application/json"]["schema"]["$ref"]
        == "#/components/schemas/QuoteResponse"
    )
    assert (
        schema["paths"]["/v1/bars/{symbol}"]["get"]["responses"]["200"]["content"]
        ["application/json"]["schema"]["$ref"]
        == "#/components/schemas/BarsResponse"
    )
