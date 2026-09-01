from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Set
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from research_core.agent_portfolio import validate_target_weights

Transport = Callable[[str, dict[str, str], bytes, float], tuple[int, bytes]]


@dataclass(frozen=True)
class AgentDecision:
    target_weights: dict[str, float]
    reasoning_summary: str
    provider: str
    model: str
    prompt_version: str
    input_hash: str


def build_input_hash(context: Mapping[str, Any]) -> str:
    serialized = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _extract_json_text(content: str) -> str:
    text = content.strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return text


def parse_model_response(content: str, allowed_symbols: Set[str]) -> AgentDecision:
    try:
        payload = json.loads(_extract_json_text(content))
    except json.JSONDecodeError as exc:
        raise ValueError(f"model response is not valid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("model response must be a JSON object")
    weights = payload.get("target_weights")
    reasoning = payload.get("reasoning_summary")
    if not isinstance(weights, dict):
        raise ValueError("model response target_weights must be an object")
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise ValueError("model response reasoning_summary must be a non-empty string")
    normalized = validate_target_weights(weights, allowed_symbols, 1.0, 0.0)
    return AgentDecision(
        target_weights=normalized,
        reasoning_summary=reasoning.strip(),
        provider="zhipu",
        model="glm-4.7-flash",
        prompt_version="unknown",
        input_hash="",
    )


class GLMModelClient:
    def __init__(
        self,
        api_key: str,
        model: str = "glm-4.7-flash",
        endpoint: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        transport: Transport | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not api_key.strip():
            raise ValueError("ZHIPU_API_KEY must not be empty")
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint
        self.transport = transport or self._request
        self.timeout = timeout

    def _request(
        self, url: str, headers: dict[str, str], body: bytes, timeout: float
    ) -> tuple[int, bytes]:
        http_request = request.Request(url, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(http_request, timeout=timeout) as response:
                return int(response.status), response.read()
        except error.HTTPError as exc:
            return int(exc.code), exc.read()

    def complete_decision(
        self, context: Mapping[str, Any], prompt_version: str, allowed_symbols: Set[str] | None = None
    ) -> AgentDecision:
        symbols = allowed_symbols or set(context.get("prices", {})) | {"CASH"}
        input_hash = build_input_hash(context)
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是纸面投资实验的组合决策模块。只输出 JSON，不要输出 Markdown。"
                            "target_weights 必须只包含允许标的，权重为 0 到 1 的小数，总和为 1。"
                            "只能做多，必须包含 CASH。reasoning_summary 用简洁中文说明依据。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {"allowed_symbols": sorted(symbols), "context": context},
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                    },
                ],
                "response_format": {"type": "json_object"},
                "thinking": {"type": "enabled"},
                "temperature": 0.2,
                "max_tokens": 2048,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        status, response_body = self.transport(
            self.endpoint,
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            body,
            self.timeout,
        )
        if status < 200 or status >= 300:
            raise RuntimeError(f"GLM API request failed with status {status}")
        try:
            response = json.loads(response_body)
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("GLM API response has an unsupported shape") from exc
        if not isinstance(content, str):
            raise ValueError("GLM API response content must be a string")
        decision = parse_model_response(content, symbols)
        return AgentDecision(
            target_weights=decision.target_weights,
            reasoning_summary=decision.reasoning_summary,
            provider="zhipu",
            model=self.model,
            prompt_version=prompt_version,
            input_hash=input_hash,
        )
