"""Pure, source-only v24 projection for an already observed diagnostic child.

The legacy child is validated before canonical key sorting can change the
order-sensitive D-137 mapping.  Only a typed, value-free summary crosses the
future frame boundary.  This module has no CLI, callback, process, dotenv,
SDK, Docker, transport, or provider entrypoint.
"""

from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path
from typing import Any

SUMMARY_SCHEMA_VERSION = "order-stable-isolated-diagnostic-summary-v24"
PROJECTION_SCHEMA_VERSION = "order-stable-typed-diagnostic-projection-v24"
DIAGNOSTIC_SUMMARY_SCHEMA_VERSION = "sanitized-sdk-diagnostic-summary-v24"
INVALID_CODE = "diagnostic_result_invalid"

_DOTENV_CODES = {
    "dotenv_missing",
    "dotenv_stat_error",
    "dotenv_not_regular_file",
    "dotenv_size_limit",
    "dotenv_read_error",
    "dotenv_changed_during_read",
    "dotenv_not_utf8",
    "dotenv_line_limit",
    "dotenv_duplicate_subject",
    "dotenv_parse_error",
    "dotenv_path_escape",
    "dotenv_subject_empty",
    "dotenv_parser_import_error",
    "diagnostic_runtime_import_error",
    "isolated_diagnostic_error",
}
_SDK_STAGES = {
    "dependency_build",
    "presence",
    "python_resolution",
    "python_binding",
    "httpx_origin",
    "openai_origin",
    "httpx_preimport",
    "openai_preimport",
    "httpx_import",
    "openai_import",
    "httpx_loaded_provenance",
    "openai_loaded_provenance",
    "factory_contract",
    "httpx_client",
    "openai_client",
    "probe_assertions",
    "client_close",
    "post_probe_bindings",
    "aggregate_validation",
    "internal_sanitizer",
    "complete",
}
_SDK_CODES = {
    "ready",
    "sdk_blocked",
    "dependency_build_error",
    "presence_error",
    "python_resolution_error",
    "python_binding_error",
    "httpx_origin_error",
    "openai_origin_error",
    "httpx_preimport_error",
    "openai_preimport_error",
    "httpx_import_error",
    "openai_import_error",
    "httpx_loaded_provenance_error",
    "openai_loaded_provenance_error",
    "factory_contract_error",
    "httpx_client_error",
    "openai_client_error",
    "transport_dispatch_rejected",
    "probe_assertions_error",
    "client_close_error",
    "post_probe_bindings_error",
    "aggregate_validation_error",
    "internal_sanitizer_error",
}
_ERROR_CODE_BY_STAGE = {
    "dependency_build": "dependency_build_error",
    "presence": "presence_error",
    "python_resolution": "python_resolution_error",
    "python_binding": "python_binding_error",
    "httpx_origin": "httpx_origin_error",
    "openai_origin": "openai_origin_error",
    "httpx_preimport": "httpx_preimport_error",
    "openai_preimport": "openai_preimport_error",
    "httpx_import": "httpx_import_error",
    "openai_import": "openai_import_error",
    "httpx_loaded_provenance": "httpx_loaded_provenance_error",
    "openai_loaded_provenance": "openai_loaded_provenance_error",
    "factory_contract": "factory_contract_error",
    "httpx_client": "httpx_client_error",
    "openai_client": "openai_client_error",
    "probe_assertions": "probe_assertions_error",
    "client_close": "client_close_error",
    "post_probe_bindings": "post_probe_bindings_error",
    "aggregate_validation": "aggregate_validation_error",
    "internal_sanitizer": "internal_sanitizer_error",
}


def _root(repository: str | Path) -> Path:
    return Path(repository).resolve(strict=True)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _ordered(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _has_exact_json_types(value: Any) -> bool:
    if value is None or type(value) in {str, int, float, bool}:
        return True
    if type(value) is list:
        return all(_has_exact_json_types(item) for item in value)
    if type(value) is dict:
        return all(type(key) is str and _has_exact_json_types(item) for key, item in value.items())
    return False


def _strict_legacy_child(repository: str | Path, value: dict[str, Any]) -> Any:
    """Validate before canonical sorting destroys legacy mapping order."""

    if type(value) is not dict or not _has_exact_json_types(value):
        raise ValueError("diagnostic input uses non-JSON runtime types")
    root = _root(repository)
    selected = str(root)
    added = False
    if selected not in sys.path:
        sys.path.insert(0, selected)
        added = True
    try:
        from patchloop.evals.sanitized_sdk_parent_integration import IsolatedDiagnosticChild

        model = IsolatedDiagnosticChild.model_validate_json(_ordered(value), strict=True)
        projected = model.model_dump(mode="json")
        if _canonical(value) != _canonical(projected):
            raise ValueError("diagnostic input requires coercion")
        return model
    finally:
        if added:
            with contextlib.suppress(ValueError):
                sys.path.remove(selected)


def _diagnostic_summary(value: Any) -> dict[str, Any] | None:
    diagnostic = value.diagnostic
    if diagnostic is None:
        return None
    return {
        "schema_version": DIAGNOSTIC_SUMMARY_SCHEMA_VERSION,
        "state": diagnostic.state,
        "stage": diagnostic.stage.value,
        "code": diagnostic.code.value,
        "transport_dispatch_count": diagnostic.activity.transport_dispatch_count,
        "network_call_count": diagnostic.activity.network_call_count,
        "provider_evaluator_agent_call_count": (
            diagnostic.activity.provider_evaluator_agent_call_count
        ),
        "raw_credential_value_returned": False,
        "credential_hash_prefix_or_length_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
    }


def _child_summary(value: Any) -> dict[str, Any]:
    error_code = value.error_code
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "state": value.state,
        "dotenv": value.dotenv.model_dump(mode="json"),
        "diagnostic": _diagnostic_summary(value),
        "error_code": None if error_code is None else error_code.value,
        "activity": value.activity.model_dump(mode="json"),
        "raw_credential_value_returned": False,
        "credential_hash_prefix_or_length_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
    }


def _projection_error() -> dict[str, Any]:
    return {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "summary": None,
        "code": INVALID_CODE,
        "activity": {
            "input_validation_count": 1,
            "summary_projection_count": 0,
            "activity_accounting_complete": False,
            "unknown_workload_activity_possible": True,
        },
        "raw_output_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
        "credential_value_hash_prefix_or_length_returned": False,
    }


def project_observed_child(
    repository: str | Path,
    observed_child: dict[str, Any],
) -> dict[str, Any]:
    """Project one supplied child; never invoke the child or retain failure material."""

    try:
        child = _strict_legacy_child(repository, observed_child)
        summary = _child_summary(child)
        value = {
            "schema_version": PROJECTION_SCHEMA_VERSION,
            "summary": summary,
            "code": None,
            "activity": {
                "input_validation_count": 1,
                "summary_projection_count": 1,
                "activity_accounting_complete": True,
                "unknown_workload_activity_possible": False,
            },
            "raw_output_returned": False,
            "exception_message_type_repr_or_traceback_returned": False,
            "credential_value_hash_prefix_or_length_returned": False,
        }
        if not validate_projection(value):
            return _projection_error()
        return value
    except BaseException:
        return _projection_error()


def _exact_keys(value: Any, expected: set[str]) -> bool:
    return type(value) is dict and set(value) == expected and len(value) == len(expected)


def _exact_count(value: Any, *, maximum: int = 1) -> bool:
    return type(value) is int and 0 <= value <= maximum


def _validate_dotenv(value: Any) -> bool:
    if not _exact_keys(
        value,
        {
            "file_present",
            "exact_subject_declared",
            "exact_subject_nonempty",
            "duplicate_subject",
            "error_code",
            "raw_value_returned",
            "value_hash_prefix_or_length_returned",
        },
    ):
        return False
    if any(
        type(value[key]) is not bool
        for key in (
            "file_present",
            "exact_subject_declared",
            "exact_subject_nonempty",
            "duplicate_subject",
            "raw_value_returned",
            "value_hash_prefix_or_length_returned",
        )
    ):
        return False
    return (
        value["raw_value_returned"] is False
        and value["value_hash_prefix_or_length_returned"] is False
        and (
            value["error_code"] is None
            or (type(value["error_code"]) is str and value["error_code"] in _DOTENV_CODES)
        )
    )


def _validate_child_activity(value: Any) -> bool:
    keys = {
        "dotenv_file_read_count",
        "dotenv_subject_membership_check_count",
        "credential_assignment_parse_count",
        "credential_value_return_count",
        "credential_value_hash_prefix_or_length_count",
        "exception_message_type_repr_or_traceback_return_count",
        "transport_dispatch_count",
        "network_call_count",
        "provider_evaluator_agent_call_count",
    }
    if not _exact_keys(value, keys):
        return False
    return (
        _exact_count(value["dotenv_file_read_count"])
        and _exact_count(value["dotenv_subject_membership_check_count"])
        and _exact_count(value["credential_assignment_parse_count"], maximum=2)
        and _exact_count(value["transport_dispatch_count"])
        and all(
            value[key] == 0 and type(value[key]) is int
            for key in (
                "credential_value_return_count",
                "credential_value_hash_prefix_or_length_count",
                "exception_message_type_repr_or_traceback_return_count",
                "network_call_count",
                "provider_evaluator_agent_call_count",
            )
        )
    )


def _validate_diagnostic_summary(value: Any) -> bool:
    if not _exact_keys(
        value,
        {
            "schema_version",
            "state",
            "stage",
            "code",
            "transport_dispatch_count",
            "network_call_count",
            "provider_evaluator_agent_call_count",
            "raw_credential_value_returned",
            "credential_hash_prefix_or_length_returned",
            "exception_message_type_repr_or_traceback_returned",
        },
    ):
        return False
    if value["schema_version"] != DIAGNOSTIC_SUMMARY_SCHEMA_VERSION:
        return False
    if type(value["state"]) is not str or value["state"] not in {
        "ready",
        "blocked",
        "error",
    }:
        return False
    if (
        type(value["stage"]) is not str
        or value["stage"] not in _SDK_STAGES
        or type(value["code"]) is not str
        or value["code"] not in _SDK_CODES
    ):
        return False
    if not _exact_count(value["transport_dispatch_count"]):
        return False
    if any(
        value[key] != 0 or type(value[key]) is not int
        for key in ("network_call_count", "provider_evaluator_agent_call_count")
    ):
        return False
    if any(
        value[key] is not False
        for key in (
            "raw_credential_value_returned",
            "credential_hash_prefix_or_length_returned",
            "exception_message_type_repr_or_traceback_returned",
        )
    ):
        return False
    if value["state"] == "ready":
        return value["stage"] == "complete" and value["code"] == "ready"
    if value["state"] == "blocked":
        return value["stage"] == "complete" and value["code"] == "sdk_blocked"
    expected = _ERROR_CODE_BY_STAGE.get(value["stage"])
    return expected is not None and value["code"] in {
        expected,
        "transport_dispatch_rejected",
    }


def _validate_summary(value: Any) -> bool:
    if not _exact_keys(
        value,
        {
            "schema_version",
            "state",
            "dotenv",
            "diagnostic",
            "error_code",
            "activity",
            "raw_credential_value_returned",
            "credential_hash_prefix_or_length_returned",
            "exception_message_type_repr_or_traceback_returned",
        },
    ):
        return False
    if value["schema_version"] != SUMMARY_SCHEMA_VERSION:
        return False
    if type(value["state"]) is not str or value["state"] not in {
        "ready",
        "blocked",
        "error",
    }:
        return False
    if not _validate_dotenv(value["dotenv"]) or not _validate_child_activity(value["activity"]):
        return False
    if any(
        value[key] is not False
        for key in (
            "raw_credential_value_returned",
            "credential_hash_prefix_or_length_returned",
            "exception_message_type_repr_or_traceback_returned",
        )
    ):
        return False
    diagnostic = value["diagnostic"]
    if diagnostic is None:
        return (
            value["state"] != "ready"
            and type(value["error_code"]) is str
            and value["error_code"] in _DOTENV_CODES
        )
    if not _validate_diagnostic_summary(diagnostic):
        return False
    if diagnostic["state"] != value["state"]:
        return False
    dotenv = value["dotenv"]
    if dotenv["exact_subject_nonempty"] is not True or dotenv["error_code"] is not None:
        return False
    expected_error = None if value["state"] == "ready" else diagnostic["code"]
    if value["error_code"] != expected_error:
        return False
    if value["activity"]["transport_dispatch_count"] != diagnostic["transport_dispatch_count"]:
        return False
    if value["activity"]["network_call_count"] != diagnostic["network_call_count"]:
        return False
    if (
        value["activity"]["provider_evaluator_agent_call_count"]
        != diagnostic["provider_evaluator_agent_call_count"]
    ):
        return False
    if value["state"] == "ready":
        return True
    return True


def validate_projection(value: dict[str, Any]) -> bool:
    if not _exact_keys(
        value,
        {
            "schema_version",
            "summary",
            "code",
            "activity",
            "raw_output_returned",
            "exception_message_type_repr_or_traceback_returned",
            "credential_value_hash_prefix_or_length_returned",
        },
    ):
        return False
    if value["schema_version"] != PROJECTION_SCHEMA_VERSION:
        return False
    if any(
        value[key] is not False
        for key in (
            "raw_output_returned",
            "exception_message_type_repr_or_traceback_returned",
            "credential_value_hash_prefix_or_length_returned",
        )
    ):
        return False
    activity = value["activity"]
    if not _exact_keys(
        activity,
        {
            "input_validation_count",
            "summary_projection_count",
            "activity_accounting_complete",
            "unknown_workload_activity_possible",
        },
    ):
        return False
    if (
        type(activity["activity_accounting_complete"]) is not bool
        or type(activity["unknown_workload_activity_possible"]) is not bool
    ):
        return False
    if not _exact_count(activity["input_validation_count"]) or not _exact_count(
        activity["summary_projection_count"]
    ):
        return False
    if value["code"] is None:
        return _validate_summary(value["summary"]) and activity == {
            "input_validation_count": 1,
            "summary_projection_count": 1,
            "activity_accounting_complete": True,
            "unknown_workload_activity_possible": False,
        }
    return (
        value["summary"] is None
        and value["code"] == INVALID_CODE
        and activity
        == {
            "input_validation_count": 1,
            "summary_projection_count": 0,
            "activity_accounting_complete": False,
            "unknown_workload_activity_possible": True,
        }
    )


def encode_projection_frame(value: dict[str, Any]) -> bytes:
    if not validate_projection(value):
        raise ValueError("v24 projection is invalid")
    from scripts import run_sanitized_sdk_bootstrap_envelope_diagnostic_v21 as framing

    return framing.encode_frame(value)


def decode_projection_frame(raw: bytes) -> Any:
    from scripts import run_sanitized_sdk_bootstrap_envelope_diagnostic_v21 as framing

    return framing.decode_frame(
        raw,
        expected_schema_version=PROJECTION_SCHEMA_VERSION,
        semantic_validator=validate_projection,
    )


__all__ = [
    "DIAGNOSTIC_SUMMARY_SCHEMA_VERSION",
    "INVALID_CODE",
    "PROJECTION_SCHEMA_VERSION",
    "SUMMARY_SCHEMA_VERSION",
    "decode_projection_frame",
    "encode_projection_frame",
    "project_observed_child",
    "validate_projection",
]
