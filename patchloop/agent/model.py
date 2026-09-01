"""Stateless model adapter with zero SDK transport retries."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
from openai import OpenAI

from patchloop.contracts import ModelConfig
from patchloop.errors import ContractError

OFFICIAL_API_BASE_URL = "https://api.openai.com/v1"


@dataclass(frozen=True)
class RequestedTool:
    name: str
    action_id: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ModelTurnError:
    code: str
    message: str


@dataclass(frozen=True)
class ModelTurn:
    tool_calls: list[RequestedTool] = field(default_factory=list)
    requested_input_tokens: int | None = None
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0
    response_id: str | None = None
    response_model: str | None = None
    response_status: str | None = None
    response_incomplete_reason: str | None = None
    error: ModelTurnError | None = None


class ModelAdapter(Protocol):
    def next_turn(self, context: str, tools: list[dict[str, Any]]) -> ModelTurn: ...


def create_openai_client(config: ModelConfig, *, api_key: str) -> OpenAI:
    if config.transport_max_retries != 0:
        raise ContractError("dev-head OpenAI transport retries must be exactly zero")
    http_client = httpx.Client(trust_env=False)
    try:
        return OpenAI(
            api_key=api_key,
            base_url=OFFICIAL_API_BASE_URL,
            http_client=http_client,
            max_retries=0,
        )
    except BaseException:
        http_client.close()
        raise


class OpenAIResponsesAdapter:
    """One stateless Responses request per turn with exact input counting."""

    def __init__(
        self,
        config: ModelConfig,
        *,
        api_key: str,
        client: OpenAI | None = None,
    ) -> None:
        if config.provider != "openai" or config.transport_max_retries != 0:
            raise ContractError("OpenAI dev-head adapter requires provider=openai and retries=0")
        if client is not None and getattr(client, "max_retries", 0) != 0:
            raise ContractError("injected OpenAI client does not enforce zero retries")
        self.config = config
        self.client = client or create_openai_client(config, api_key=api_key)

    def request_payload(
        self,
        context: str,
        tools: list[dict[str, Any]],
        *,
        system_prompt: str,
    ) -> dict[str, Any]:
        reasoning: dict[str, str] = {"effort": self.config.reasoning_effort}
        if self.config.model_id.startswith("gpt-5.6"):
            reasoning.update({"mode": self.config.reasoning_mode, "context": "current_turn"})
        return {
            "model": self.config.model_id,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context},
            ],
            "tools": tools,
            "parallel_tool_calls": True,
            "store": False,
            "reasoning": reasoning,
            "service_tier": self.config.service_tier,
            "max_output_tokens": self.config.max_output_tokens,
            "truncation": "disabled",
        }

    @staticmethod
    def _count_payload(request: dict[str, Any]) -> dict[str, Any]:
        keys = (
            "model",
            "input",
            "tools",
            "reasoning",
            "truncation",
            "parallel_tool_calls",
        )
        return {key: request[key] for key in keys if key in request}

    def count_input_tokens_v2(
        self,
        request: dict[str, Any],
        *,
        timeout_seconds: float | None = None,
    ) -> int:
        payload = self._count_payload(request)
        if timeout_seconds is not None:
            payload["timeout"] = timeout_seconds
        counted = self.client.responses.input_tokens.count(**payload)
        return int(counted.input_tokens)

    def execute_request(
        self,
        request: dict[str, Any],
        *,
        requested_input_tokens: int,
        timeout_seconds: float | None = None,
    ) -> ModelTurn:
        payload = dict(request)
        if timeout_seconds is not None:
            payload["timeout"] = timeout_seconds
        response = self.client.responses.create(**payload)
        usage = getattr(response, "usage", None)
        input_details = getattr(usage, "input_tokens_details", None) if usage else None
        output_details = getattr(usage, "output_tokens_details", None) if usage else None
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
        cached_input_tokens = int(
            (getattr(input_details, "cached_tokens", 0) if input_details else 0) or 0
        )
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
        reasoning_output_tokens = int(
            (getattr(output_details, "reasoning_tokens", 0) if output_details else 0) or 0
        )
        response_status = getattr(response, "status", None)
        incomplete_details = getattr(response, "incomplete_details", None)
        incomplete_reason = (
            incomplete_details.get("reason")
            if isinstance(incomplete_details, dict)
            else getattr(incomplete_details, "reason", None)
        )
        error: ModelTurnError | None = None
        if usage is None or requested_input_tokens != input_tokens:
            error = ModelTurnError(
                "input_token_count_mismatch",
                "pre-dispatch input count did not match provider usage",
            )
        elif response_status not in {None, "completed"} or incomplete_reason:
            error = ModelTurnError(
                "incomplete_response",
                f"provider response was incomplete: {incomplete_reason or response_status}",
            )
        calls: list[RequestedTool] = []
        if error is None:
            for item in response.output or []:
                if getattr(item, "type", None) != "function_call":
                    continue
                try:
                    arguments = json.loads(item.arguments)
                except (json.JSONDecodeError, TypeError):
                    error = ModelTurnError(
                        "invalid_tool_arguments_json",
                        "provider tool arguments were not valid JSON",
                    )
                    break
                if not isinstance(arguments, dict):
                    error = ModelTurnError(
                        "invalid_tool_arguments_type",
                        "provider tool arguments were not an object",
                    )
                    break
                calls.append(RequestedTool(item.name, item.call_id, arguments))
        if error is not None:
            calls = []
        return ModelTurn(
            tool_calls=calls,
            requested_input_tokens=requested_input_tokens,
            input_tokens=input_tokens,
            cached_input_tokens=cached_input_tokens,
            output_tokens=output_tokens,
            reasoning_output_tokens=reasoning_output_tokens,
            response_id=getattr(response, "id", None),
            response_model=getattr(response, "model", None),
            response_status=response_status,
            response_incomplete_reason=incomplete_reason,
            error=error,
        )

    def next_turn(self, context: str, tools: list[dict[str, Any]]) -> ModelTurn:
        from patchloop.dev.model import DEV_SYSTEM_PROMPT

        request = self.request_payload(context, tools, system_prompt=DEV_SYSTEM_PROMPT)
        counted = self.count_input_tokens_v2(request)
        return self.execute_request(request, requested_input_tokens=counted)
