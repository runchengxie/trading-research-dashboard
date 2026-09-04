from __future__ import annotations

import json

import pytest

from trading_research.agent_decision import (
    GLMModelClient,
    build_input_hash,
    create_model_client,
    parse_model_response,
)


def test_client_parses_json_decision_from_model_response() -> None:
    decision = parse_model_response(
        '{"target_weights":{"SPY":0.8,"CASH":0.2},"reasoning_summary":"趋势稳定。"}',
        allowed_symbols={"SPY", "CASH"},
    )
    assert decision.target_weights == {"SPY": 0.8, "CASH": 0.2}
    assert decision.reasoning_summary == "趋势稳定。"


def test_client_parses_common_camel_case_weight_alias() -> None:
    decision = parse_model_response(
        json.dumps({"targetWeights": {"SPY": 0.5, "CASH": 0.5}, "reasoning_summary": "保持平衡。"}),
        allowed_symbols={"SPY", "CASH"},
    )
    assert decision.target_weights == {"SPY": 0.5, "CASH": 0.5}


def test_client_parses_one_fenced_json_block() -> None:
    decision = parse_model_response(
        "```json\n{\"target_weights\": {\"CASH\": 1}, \"reasoning_summary\": \"观望。\"}\n```",
        allowed_symbols={"SPY", "CASH"},
    )
    assert decision.target_weights == {"CASH": 1.0}


def test_client_parses_openai_content_parts() -> None:
    requests: list[tuple[str, dict[str, str], bytes, float]] = []

    def transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
        requests.append((url, headers, body, timeout))
        return (
            200,
            json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": [
                                    {"type": "text", "text": '{"target_weights":{"CASH":1},'},
                                    {"type": "text", "text": '"reasoning_summary":"观望。"}'},
                                ]
                            }
                        }
                    ]
                }
            ).encode(),
        )

    decision = GLMModelClient("secret", transport=transport).complete_decision(
        {"prices": {"SPY": 100}}, "v1"
    )

    assert decision.target_weights == {"CASH": 1.0}


def test_client_rejects_invalid_model_json() -> None:
    with pytest.raises(ValueError, match="model response"):
        parse_model_response("not json", allowed_symbols={"SPY", "CASH"})


def test_prompt_hash_changes_when_context_changes() -> None:
    assert build_input_hash({"price": 100}) != build_input_hash({"price": 101})


def test_client_sends_api_key_model_and_json_request() -> None:
    requests: list[tuple[str, dict[str, str], bytes, float]] = []

    def transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
        requests.append((url, headers, body, timeout))
        return (
            200,
            json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": '{"target_weights":{"CASH":1},"reasoning_summary":"观望。"}'
                            }
                        }
                    ]
                }
            ).encode(),
        )

    decision = GLMModelClient("secret", transport=transport).complete_decision(
        {"prices": {"SPY": 100}}, "v1"
    )
    assert decision.target_weights == {"CASH": 1.0}
    assert requests[0][0].endswith("/chat/completions")
    assert requests[0][1]["Authorization"] == "Bearer secret"
    assert json.loads(requests[0][2])["model"] == "glm-4.7-flash"
    assert requests[0][3] == 30.0


def test_client_rejects_non_success_response_without_exposing_secret() -> None:
    def transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
        return 429, b"rate limited"

    with pytest.raises(RuntimeError, match="status 429") as error:
        GLMModelClient("secret", transport=transport).complete_decision({}, "v1")
    assert "secret" not in str(error.value)


def test_openrouter_client_uses_configured_model_and_openai_endpoint() -> None:
    requests: list[tuple[str, dict[str, str], bytes, float]] = []

    def transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
        requests.append((url, headers, body, timeout))
        return (
            200,
            json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": '{"target_weights":{"CASH":1},"reasoning_summary":"观望。"}'
                            }
                        }
                    ]
                }
            ).encode(),
        )

    client = create_model_client(
        openrouter_api_key="router-secret",
        openrouter_model="openrouter/free",
        openrouter_base_url="https://openrouter.ai/api/v1",
        transport=transport,
    )
    decision = client.complete_decision({"prices": {"SPY": 100}}, "v1")

    assert decision.provider == "openrouter"
    assert decision.model == "openrouter/free"
    assert requests[0][0] == "https://openrouter.ai/api/v1/chat/completions"
    assert json.loads(requests[0][2])["model"] == "openrouter/free"
    assert "thinking" not in json.loads(requests[0][2])


def test_model_factory_falls_back_to_zhipu_when_openrouter_key_is_missing() -> None:
    client = create_model_client(zhipu_api_key="zhipu-secret")

    assert isinstance(client, GLMModelClient)


def test_model_factory_uses_gemini_before_zhipu_when_openrouter_is_missing() -> None:
    client = create_model_client(
        gemini_api_key="gemini-secret",
        gemini_model="gemini-3-flash",
        gemini_base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        zhipu_api_key="zhipu-secret",
    )

    assert client.provider == "gemini"
    assert client.model == "gemini-3-flash"
    assert client.endpoint == (
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    )


def test_model_factory_uses_next_gemini_key_when_primary_is_blank() -> None:
    client = create_model_client(
        gemini_api_key=" ",
        gemini_api_key_2="gemini-secret-2",
        gemini_api_key_3="gemini-secret-3",
    )

    assert client.api_key == "gemini-secret-2"


def test_gemini_client_falls_back_to_next_key_after_retryable_http_failure() -> None:
    requests: list[tuple[str, dict[str, str], bytes, float]] = []

    def transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
        requests.append((url, headers, body, timeout))
        if len(requests) == 1:
            return 429, b"rate limited"
        return (
            200,
            json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": '{"target_weights":{"CASH":1},"reasoning_summary":"观望。"}'
                            }
                        }
                    ]
                }
            ).encode(),
        )

    client = GLMModelClient(
        "gemini-secret-1",
        api_keys=("gemini-secret-1", "gemini-secret-2"),
        provider="gemini",
        transport=transport,
    )

    decision = client.complete_decision({"prices": {"SPY": 100}}, "v1")

    assert decision.target_weights == {"CASH": 1.0}
    assert requests[0][1]["Authorization"] == "Bearer gemini-secret-1"
    assert requests[1][1]["Authorization"] == "Bearer gemini-secret-2"
