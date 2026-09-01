from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from patchloop.agent.provider_schema_adapter import StrictOpenAIResponsesAdapter
from patchloop.agent.provider_schema_admission import (
    ProviderToolSchemaError,
    normalize_strict_read_arguments,
    validate_provider_tool_schemas,
)
from patchloop.agent.tools import TOOL_SCHEMAS_V27, TOOL_SCHEMAS_V28
from patchloop.contracts import ModelConfig
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json
from tests.test_model_adapter import FakeResponses


def _request() -> dict:
    return {"tools": copy.deepcopy(TOOL_SCHEMAS_V28)}


def _read(request: dict) -> dict:
    return next(t["parameters"] for t in request["tools"] if t["name"] == "read_file")


def test_strict_successor_preserves_invalid_predecessor_and_is_deterministic() -> None:
    old = copy.deepcopy(TOOL_SCHEMAS_V27)
    invalid = next(t for t in old if t["name"] == "read_file")
    assert sha256_json(invalid) == (
        "sha256:4890d95f65864f0ac203374eeaf4f8942c814bf4e74bfaac21bdc5c12931a799"
    )
    with pytest.raises(ProviderToolSchemaError) as caught:
        validate_provider_tool_schemas({"tools": [invalid]})
    assert caught.value.details["reason_code"] == "required_property_mismatch"
    request = _request()
    raw = canonical_json(request)
    one = validate_provider_tool_schemas(request)
    two = validate_provider_tool_schemas(request)
    assert canonical_json(one) == canonical_json(two)
    assert canonical_json(request) == raw
    assert one["provider_authority_granted"] is False
    assert one["provider_acceptance_observed"] is False
    assert old == TOOL_SCHEMAS_V27


@pytest.mark.parametrize(
    "damage",
    [
        "root_required",
        "nested_required",
        "nested_open",
        "nested_missing_required",
        "empty_enum",
        "invalid_enum_type",
        "unsupported_oneof",
        "unsupported_ref",
        "root_anyof",
        "duplicate_required",
        "extra_required",
        "invalid_items",
        "unknown_type",
        "duplicate_names",
        "not_strict",
        "non_function",
        "invalid_pattern",
        "impossible_bounds",
        "unknown_format",
        "nested_property_array",
        "invalid_nullable",
    ],
)
def test_final_schema_negatives_fail_locally(damage: str) -> None:
    request = _request()
    read = _read(request)
    anchor = read["properties"]["search_anchor"]
    if damage == "root_required":
        read["required"] = []
    elif damage == "nested_required":
        anchor["required"].remove("match_index")
    elif damage == "nested_open":
        anchor["additionalProperties"] = True
    elif damage == "nested_missing_required":
        del anchor["required"]
    elif damage == "empty_enum":
        read["properties"]["path"]["enum"] = []
    elif damage == "invalid_enum_type":
        read["properties"]["path"]["enum"] = [12]
    elif damage == "unsupported_oneof":
        anchor["oneOf"] = [{"type": "null"}]
    elif damage == "unsupported_ref":
        anchor["$ref"] = "#/$defs/unresolved"
    elif damage == "root_anyof":
        read["anyOf"] = [{"type": "null"}]
    elif damage == "duplicate_required":
        anchor["required"].append("match_index")
    elif damage == "extra_required":
        anchor["required"].append("unavailable")
    elif damage == "invalid_items":
        read["properties"]["path"] = {"type": "array", "items": False}
    elif damage == "unknown_type":
        anchor["type"] = "numberish"
    elif damage == "duplicate_names":
        request["tools"].append(copy.deepcopy(request["tools"][0]))
    elif damage == "not_strict":
        request["tools"][0]["strict"] = False
    elif damage == "non_function":
        request["tools"][0]["type"] = "web_search"
    elif damage == "invalid_pattern":
        read["properties"]["path"]["pattern"] = "["
    elif damage == "impossible_bounds":
        anchor["properties"]["match_index"]["minimum"] = 1000
    elif damage == "unknown_format":
        read["properties"]["path"]["format"] = "hostnameish"
    elif damage == "nested_property_array":
        anchor["properties"] = []
    else:
        anchor["type"] = ["object", "object", "null"]
    with pytest.raises(ProviderToolSchemaError) as caught:
        validate_provider_tool_schemas(request)
    assert caught.value.details["provider_transport_started"] is False


def test_nullable_direct_and_anchor_are_lossless_and_exclusive() -> None:
    direct = {"path": "src/example.py", "start_line": 5, "end_line": 12, "search_anchor": None}
    anchor = {"search_event_sequence": 9, "match_index": 0, "before_lines": 2, "after_lines": 6}
    anchored = {"path": None, "start_line": None, "end_line": None, "search_anchor": anchor}
    assert normalize_strict_read_arguments(direct) == {
        "path": "src/example.py",
        "start_line": 5,
        "end_line": 12,
    }
    assert normalize_strict_read_arguments(anchored) == {"search_anchor": anchor}
    assert direct["search_anchor"] is None
    for invalid in (
        {},
        {**direct, "search_anchor": anchor},
        {**anchored, "search_anchor": None},
        {**direct, "start_line": None},
        {**direct, "start_line": True},
        {**direct, "end_line": 4},
        {**direct, "extra": "ignored?"},
        {key: value for key, value in direct.items() if key != "search_anchor"},
    ):
        with pytest.raises(ContractError):
            normalize_strict_read_arguments(invalid)


def _adapter(responses: FakeResponses) -> StrictOpenAIResponsesAdapter:
    return StrictOpenAIResponsesAdapter(
        ModelConfig(provider="openai", model_id="gpt-5.4-mini-2026-03-17", transport_max_retries=0),
        client=SimpleNamespace(responses=responses, max_retries=0),
    )


@pytest.mark.parametrize("operation", ["count", "generate"])
def test_adapter_gate_precedes_both_sdk_methods(operation: str) -> None:
    responses = FakeResponses()
    adapter = _adapter(responses)
    request = adapter.request_payload("bounded public context", _request()["tools"])
    _read(request)["required"] = []
    with pytest.raises(ProviderToolSchemaError):
        if operation == "count":
            adapter.count_input_tokens_v3(request)
        else:
            adapter.execute_request_v3(request, requested_input_tokens=10)
    assert responses.count_kwargs is None and responses.kwargs is None


def test_count_create_projection_parity_and_late_schema_tamper() -> None:
    responses = FakeResponses()
    adapter = _adapter(responses)
    request = adapter.request_payload("bounded public context", _request()["tools"])
    request["parallel_tool_calls"] = False
    assert adapter.count_input_tokens_v3(request) == 10
    adapter.execute_request_v3(request, requested_input_tokens=10)
    assert responses.count_kwargs == adapter._token_count_payload_v2(responses.kwargs)
    responses.kwargs = None
    _read(request)["properties"]["path"]["enum"] = []
    with pytest.raises(ProviderToolSchemaError):
        adapter.execute_request_v3(request, requested_input_tokens=10)
    assert responses.kwargs is None
