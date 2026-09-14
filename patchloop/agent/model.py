"""Journal-managed model adapter with zero SDK transport retries."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

import httpx
from openai import OpenAI

from patchloop.agent.usage_diagnostics import (
    provider_usage_evidence,
    usage_failure_message,
    usage_token_value,
)
from patchloop.contracts import ModelConfig
from patchloop.errors import ContractError
from patchloop.util import sha256_json

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
class EncryptedReasoningContinuationItem:
    id: str
    encrypted_content: str = field(repr=False)
    status: Literal["in_progress", "completed", "incomplete"] | None = None


@dataclass(frozen=True)
class FunctionCallContinuationRef:
    action_id: str


ProviderContinuationItem = (
    EncryptedReasoningContinuationItem | FunctionCallContinuationRef
)


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
    response_reasoning_context: Literal["current_turn", "all_turns"] | None = None
    response_incomplete_reason: str | None = None
    usage_evidence: dict[str, Any] | None = None
    error: ModelTurnError | None = None
    output_item_count: int = 0
    non_tool_output_item_count: int = 0
    output_item_types: tuple[str, ...] = ()
    output_shape_hash: str | None = None
    provider_continuation: tuple[ProviderContinuationItem, ...] = field(
        default=(),
        repr=False,
    )


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
    """One journal-managed Responses request per turn with exact input counting."""

    def __init__(
        self,
        config: ModelConfig,
        *,
        api_key: str,
        client: OpenAI | None = None,
    ) -> None:
        if config.provider != "openai" or config.transport_max_retries != 0:
            raise ContractError("OpenAI dev-head adapter requires provider=openai and retries=0")
        if config.reasoning_continuation != "encrypted-v1":
            raise ContractError(
                "OpenAI dev-head adapter requires encrypted stateless reasoning continuation"
            )
        if client is not None and getattr(client, "max_retries", 0) != 0:
            raise ContractError("injected OpenAI client does not enforce zero retries")
        self.config = config
        self.client = client or create_openai_client(config, api_key=api_key)

    def request_payload(
        self,
        context: str | list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        system_prompt: str,
    ) -> dict[str, Any]:
        reasoning: dict[str, str] = {"effort": self.config.reasoning_effort}
        if self.config.model_id.startswith("gpt-5.6"):
            reasoning.update({"mode": self.config.reasoning_mode, "context": "current_turn"})
        input_items = (
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context},
            ]
            if isinstance(context, str)
            else context
        )
        if not isinstance(input_items, list) or not all(
            isinstance(item, dict) for item in input_items
        ):
            raise ContractError("dev-head model input must be a list of public input items")
        return {
            "model": self.config.model_id,
            "input": input_items,
            "tools": tools,
            "tool_choice": "required",
            "parallel_tool_calls": True,
            "store": False,
            "include": ["reasoning.encrypted_content"],
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
            "tool_choice",
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
        usage_evidence = provider_usage_evidence(response, requested_input_tokens)
        input_tokens = usage_token_value(usage_evidence, "input_tokens")
        cached_input_tokens = usage_token_value(usage_evidence, "cached_input_tokens")
        output_tokens = usage_token_value(usage_evidence, "output_tokens")
        reasoning_output_tokens = usage_token_value(usage_evidence, "reasoning_output_tokens")
        response_status = getattr(response, "status", None)
        response_reasoning = getattr(response, "reasoning", None)
        reasoning_context = (
            response_reasoning.get("context") if isinstance(response_reasoning, dict)
            else getattr(response_reasoning, "context", None)
        )
        incomplete_details = getattr(response, "incomplete_details", None)
        incomplete_reason = (
            incomplete_details.get("reason")
            if isinstance(incomplete_details, dict)
            else getattr(incomplete_details, "reason", None)
        )
        error: ModelTurnError | None = None
        if usage_evidence["failure_kind"] is not None:
            error = ModelTurnError(
                # Compatibility umbrella: existing consumers must still stop all
                # paid work. The evidence distinguishes absence from mismatch.
                "input_token_count_mismatch",
                usage_failure_message(usage_evidence),
            )
        elif response_status not in {None, "completed"} or incomplete_reason:
            error = ModelTurnError(
                "incomplete_response",
                f"provider response was incomplete: {incomplete_reason or response_status}",
            )
        output_items = list(response.output or [])
        output_item_types = tuple(
            item_type if isinstance(item_type := getattr(item, "type", None), str) else "unknown"
            for item in output_items
        )
        output_shape_hash = sha256_json(
            {
                "item_count": len(output_items),
                "item_types": output_item_types,
            }
        )
        calls: list[RequestedTool] = []
        continuation: list[ProviderContinuationItem] = []
        for item in output_items:
            item_type = getattr(item, "type", None)
            if item_type == "reasoning":
                item_id = getattr(item, "id", None)
                encrypted_content = getattr(item, "encrypted_content", None)
                status = getattr(item, "status", None)
                if (
                    not isinstance(item_id, str)
                    or not item_id
                    or not isinstance(encrypted_content, str)
                    or not encrypted_content
                    or status not in {None, "in_progress", "completed", "incomplete"}
                ):
                    if error is None or error.code != "input_token_count_mismatch":
                        error = ModelTurnError(
                            "provider_continuation_error",
                            "provider reasoning output is missing a valid encrypted continuation",
                        )
                    continuation = []
                    break
                continuation.append(
                    EncryptedReasoningContinuationItem(
                        id=item_id,
                        encrypted_content=encrypted_content,
                        status=status,
                    )
                )
                continue
            if item_type != "function_call" or error is not None:
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
            continuation.append(FunctionCallContinuationRef(action_id=item.call_id))
        if error is not None:
            calls = []
            if error.code != "provider_continuation_error":
                continuation = [
                    item
                    for item in continuation
                    if isinstance(item, EncryptedReasoningContinuationItem)
                ]
        if not any(
            isinstance(item, EncryptedReasoningContinuationItem) for item in continuation
        ):
            continuation = []
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
            response_reasoning_context=(
                reasoning_context if isinstance(reasoning_context, str)
                and reasoning_context in {"current_turn", "all_turns"} else None
            ),
            response_incomplete_reason=incomplete_reason,
            usage_evidence=usage_evidence,
            error=error,
            output_item_count=len(output_items),
            non_tool_output_item_count=sum(
                item_type != "function_call" for item_type in output_item_types
            ),
            output_item_types=output_item_types,
            output_shape_hash=output_shape_hash,
            provider_continuation=tuple(continuation),
        )

    def next_turn(self, context: str, tools: list[dict[str, Any]]) -> ModelTurn:
        from patchloop.dev.model import DEV_SYSTEM_PROMPT

        request = self.request_payload(context, tools, system_prompt=DEV_SYSTEM_PROMPT)
        counted = self.count_input_tokens_v2(request)
        return self.execute_request(request, requested_input_tokens=counted)
