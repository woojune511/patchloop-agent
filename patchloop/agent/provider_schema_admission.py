"""Offline, opt-in Responses tool admission for Lean V27.

This checks PatchLoop's bounded JSON Schema subset, not every provider feature.
It never rewrites schemas, performs I/O, or grants execution authority.
"""

from __future__ import annotations

import copy
import math
import re
from typing import Any

from patchloop.errors import ContractError, HarnessAdmissionError
from patchloop.util import canonical_json, sha256_json

PROVIDER_SCHEMA_POLICY = "responses-strict-tool-admission-v1"
STRICT_ANCHORED_READ_POLICY = "required-nullable-anchored-read-v1"
_TYPES = {"object", "array", "string", "integer", "number", "boolean", "null"}
_KEYS = {
    "type",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "anyOf",
    "enum",
    "const",
    "description",
    "title",
    "default",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "minLength",
    "maxLength",
    "pattern",
    "format",
    "minItems",
    "maxItems",
}
_FORMATS = {"date-time", "time", "date", "duration", "email", "hostname", "ipv4", "ipv6", "uuid"}


class ProviderToolSchemaError(HarnessAdmissionError):
    code = "PROVIDER_TOOL_SCHEMA_INVALID"


def _reject(path: str, reason: str) -> None:
    # Paths and reason codes only: never echo a request, tool result or credential.
    raise ProviderToolSchemaError(
        "final provider tool schema failed local admission",
        details={
            "policy_version": PROVIDER_SCHEMA_POLICY,
            "schema_path": path,
            "reason_code": reason,
            "provider_transport_started": False,
            "failure_origin": "harness_request_schema",
        },
    )


def _matches(value: Any, types: set[str]) -> bool:
    return bool(
        (value is None and "null" in types)
        or (type(value) is str and "string" in types)
        or (type(value) is bool and "boolean" in types)
        or (type(value) is int and bool(types & {"integer", "number"}))
        or (type(value) is float and math.isfinite(value) and "number" in types)
        or (type(value) is dict and "object" in types)
        or (type(value) is list and "array" in types)
    )


def validate_provider_tool_schemas(request: dict[str, Any]) -> dict[str, Any]:
    """Validate the *final request* and return a deterministic, non-authorizing receipt.

    All nested objects are closed and required/property sets are identical.
    Local refs/recursion and unsupported keywords are deliberately fail-closed;
    none is emitted by this runtime. Provider acceptance is not claimed.
    """

    tools = request.get("tools") if type(request) is dict else None
    if type(tools) is not list or not tools or len(tools) > 128:
        _reject("tools", "function_list_invalid")
    names: set[str] = set()
    total_properties = total_enums = total_strings = max_depth = 0

    def visit(schema: Any, path: str, depth: int, *, root: bool = False) -> None:
        nonlocal total_properties, total_enums, total_strings, max_depth
        if type(schema) is not dict or not schema or not set(schema).issubset(_KEYS):
            _reject(path, "unsupported_schema_shape_or_keyword")
        if depth > 10:
            _reject(path, "schema_depth_limit")
        max_depth = max(max_depth, depth)
        for key in ("description", "title"):
            if key in schema and type(schema[key]) is not str:
                _reject(path, "schema_annotation_invalid")
        if "anyOf" in schema:
            branches = schema["anyOf"]
            if root or set(schema) - {"anyOf", "description", "title"}:
                _reject(path, "union_position_invalid")
            if type(branches) is not list or not branches or len(branches) > 32:
                _reject(path, "union_branches_invalid")
            for index, branch in enumerate(branches):
                visit(branch, f"{path}.anyOf[{index}]", depth + 1)
            return
        raw_types = schema.get("type")
        if type(raw_types) is str:
            types = {raw_types}
        elif (
            type(raw_types) is list
            and len(raw_types) == 2
            and all(type(t) is str for t in raw_types)
            and len(set(raw_types)) == 2
            and "null" in raw_types
        ):
            types = set(raw_types)
        else:
            _reject(path, "schema_type_invalid")
        if not types.issubset(_TYPES) or (root and types != {"object"}):
            _reject(path, "root_or_type_invalid")
        if "object" in types:
            props, required = schema.get("properties"), schema.get("required")
            if type(props) is not dict or any(type(key) is not str for key in props):
                _reject(path, "object_properties_invalid")
            if (
                type(required) is not list
                or any(type(key) is not str for key in required)
                or len(required) != len(set(required))
                or set(required) != set(props)
            ):
                _reject(path, "required_property_mismatch")
            if schema.get("additionalProperties") is not False:
                _reject(path, "object_not_closed")
            total_properties += len(props)
            total_strings += sum(len(key) for key in props)
            for key, child in props.items():
                visit(child, f"{path}.properties.{key}", depth + 1)
        elif any(key in schema for key in ("properties", "required", "additionalProperties")):
            _reject(path, "object_keyword_on_non_object")
        if "array" in types:
            visit(schema.get("items"), f"{path}.items", depth + 1)
        elif any(key in schema for key in ("items", "minItems", "maxItems")):
            _reject(path, "array_keyword_on_non_array")
        for keyword, required_type in (
            ("minLength", "string"),
            ("maxLength", "string"),
            ("minItems", "array"),
            ("maxItems", "array"),
        ):
            if keyword in schema and (
                required_type not in types
                or type(schema[keyword]) is not int
                or schema[keyword] < 0
            ):
                _reject(path, "length_constraint_invalid")
        for low, high in (("minLength", "maxLength"), ("minItems", "maxItems")):
            if low in schema and high in schema and schema[low] > schema[high]:
                _reject(path, "impossible_length_bounds")
        for keyword in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf"):
            if keyword in schema:
                value = schema[keyword]
                if (
                    not types & {"integer", "number"}
                    or type(value) not in {int, float}
                    or not math.isfinite(value)
                    or (keyword == "multipleOf" and value <= 0)
                ):
                    _reject(path, "numeric_constraint_invalid")
        if "minimum" in schema and "maximum" in schema and schema["minimum"] > schema["maximum"]:
            _reject(path, "impossible_numeric_bounds")
        if "pattern" in schema:
            if "string" not in types or type(schema["pattern"]) is not str:
                _reject(path, "pattern_invalid")
            try:
                re.compile(schema["pattern"])
            except re.error:
                _reject(path, "pattern_invalid")
        if "format" in schema and (
            "string" not in types
            or type(schema["format"]) is not str
            or schema["format"] not in _FORMATS
        ):
            _reject(path, "format_invalid")
        for keyword in ("enum", "const"):
            if keyword not in schema:
                continue
            values = schema[keyword] if keyword == "enum" else [schema[keyword]]
            if (
                type(values) is not list
                or not values
                or any(not _matches(v, types) or type(v) in {dict, list} for v in values)
                or len({canonical_json(v) for v in values}) != len(values)
            ):
                _reject(path, "enum_or_const_invalid")
            string_size = sum(len(v) for v in values if isinstance(v, str))
            if len(values) > 250 and string_size > 15_000:
                _reject(path, "enum_string_limit")
            total_enums += len(values)
            total_strings += string_size
        if total_properties > 5_000 or total_enums > 1_000 or total_strings > 120_000:
            _reject(path, "schema_size_limit")

    for index, tool in enumerate(tools):
        path = f"tools[{index}]"
        if (
            type(tool) is not dict
            or tool.get("type") != "function"
            or tool.get("strict") is not True
            or set(tool) - {"type", "name", "description", "parameters", "strict"}
        ):
            _reject(path, "strict_function_invalid")
        name = tool.get("name")
        if type(name) is not str or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", name) or name in names:
            _reject(path, "function_name_invalid_or_duplicate")
        if "description" in tool and type(tool["description"]) is not str:
            _reject(path, "function_description_invalid")
        names.add(name)
        visit(tool.get("parameters"), f"{path}.parameters", 1, root=True)
    body = {
        "schema_version": "provider-tool-schema-admission-v1",
        "policy_version": PROVIDER_SCHEMA_POLICY,
        "tool_schema_hash": sha256_json(tools),
        "tool_names": [tool["name"] for tool in tools],
        "property_count": total_properties,
        "enum_value_count": total_enums,
        "max_schema_depth": max_depth,
        "provider_acceptance_observed": False,
        "provider_authority_granted": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def strict_anchored_read_schema(predecessor: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(predecessor)
    parameters = result["parameters"]
    for key in ("path", "start_line", "end_line", "search_anchor"):
        field = parameters["properties"][key]
        field["type"] = [field["type"], "null"]
    parameters["required"] = list(parameters["properties"])
    result["description"] = (
        "Read one explicit source range OR one exact prior search match. Include every field. "
        "Direct: path/start_line/end_line are non-null, search_anchor is null. "
        "Anchor: search_anchor is non-null, path/start_line/end_line are null. "
        "The server resolves the same current-diff search match; never guess its path/range."
    )
    return result


def normalize_strict_read_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    """Normalize only the versioned wire representation; preserve raw input identity."""
    keys = {"path", "start_line", "end_line", "search_anchor"}
    valid = (
        type(arguments) is dict
        and keys.issubset(arguments)
        and not (set(arguments) - keys - {"investigation_intent"})
    )
    direct = valid and (
        arguments["search_anchor"] is None
        and type(arguments["path"]) is str
        and bool(arguments["path"])
        and type(arguments["start_line"]) is int
        and type(arguments["end_line"]) is int
        and 1 <= arguments["start_line"] <= arguments["end_line"]
    )
    anchor = valid and (
        type(arguments["search_anchor"]) is dict
        and all(arguments[key] is None for key in ("path", "start_line", "end_line"))
    )
    if not (direct or anchor):
        raise ContractError(
            "read_file requires one complete direct range or one search anchor",
            details={"reason_codes": ["self_directed_investigation_read_mode_invalid"]},
        )
    return {key: copy.deepcopy(value) for key, value in arguments.items() if value is not None}
