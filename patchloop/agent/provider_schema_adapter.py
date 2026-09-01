"""Lean V27-only provider adapter; every transport entry validates locally."""

from __future__ import annotations

from typing import Any

from patchloop.agent.model import ModelTurn, OpenAIResponsesAdapter
from patchloop.agent.provider_schema_admission import validate_provider_tool_schemas
from patchloop.errors import HarnessAdmissionError


class StrictOpenAIResponsesAdapter(OpenAIResponsesAdapter):
    def admit_request_v3(self, request: dict[str, Any]) -> dict[str, Any]:
        """Pure last-mile gate; a receipt is not execution authority."""
        receipt = validate_provider_tool_schemas(request)
        retries = getattr(self.client, "max_retries", None)
        if self.config.transport_max_retries != 0 or type(retries) is not int or retries != 0:
            raise HarnessAdmissionError("strict transport requires zero SDK retries")
        return receipt

    def count_input_tokens_v3(self, request: dict[str, Any]) -> int:
        self.admit_request_v3(request)
        counted = self.client.responses.input_tokens.count(**self._token_count_payload_v2(request))
        if type(counted.input_tokens) is not int or counted.input_tokens <= 0:
            raise ValueError("provider input-token count must be a positive integer")
        return counted.input_tokens

    def count_input_tokens(self, request: dict[str, Any]) -> int:
        return self.count_input_tokens_v3(request)

    def count_input_tokens_v2(self, request: dict[str, Any]) -> int:
        return self.count_input_tokens_v3(request)

    def execute_request_v3(
        self,
        request: dict[str, Any],
        *,
        requested_input_tokens: int,
    ) -> ModelTurn:
        return self.execute_request(request, requested_input_tokens=requested_input_tokens)

    def execute_request(
        self,
        request: dict[str, Any],
        *,
        requested_input_tokens: int,
    ) -> ModelTurn:
        self.admit_request_v3(request)
        return super().execute_request(request, requested_input_tokens=requested_input_tokens)
