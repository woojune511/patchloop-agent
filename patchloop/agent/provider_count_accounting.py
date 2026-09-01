"""Opt-in durable input-token-count attempts, independent of generation usage.

Started means a logical SDK attempt was reserved, not proof of HTTP delivery.
An interrupted attempt is outcome-unknown and cannot be automatically retried.
No provider error message, request body, source body, or reasoning is recorded.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any

from patchloop.agent.provider_schema_admission import (
    PROVIDER_SCHEMA_POLICY,
    validate_provider_tool_schemas,
)
from patchloop.contracts import EventType, RunEvent
from patchloop.errors import PatchLoopError, RecoveryError
from patchloop.util import sha256_json

if TYPE_CHECKING:
    from patchloop.state.store import StateStore

COUNT_ACCOUNTING_POLICY = "durable-input-token-count-attempt-v1"
_PROVIDER_CODES = {
    "invalid_function_parameters",
    "invalid_request_error",
    "rate_limit_exceeded",
    "context_length_exceeded",
    "server_error",
}
_COMMON_KEYS = {
    "schema_version",
    "policy_version",
    "run_id",
    "attempt_id",
    "attempt_index",
    "request_body_hash",
    "tool_schema_hash",
    "content_hash",
}


class ProviderInputTokenCountError(PatchLoopError):
    code = "PROVIDER_INPUT_TOKEN_COUNT_FAILED"


class ProviderInputTokenCountUncertainError(RecoveryError):
    code = "PROVIDER_INPUT_TOKEN_COUNT_OUTCOME_UNKNOWN"


def _body_hash(document: dict[str, Any]) -> str:
    return sha256_json({key: value for key, value in document.items() if key != "content_hash"})


def project_input_token_count_attempts(run_id: str, events: Sequence[RunEvent]) -> dict[str, Any]:
    """Validate and reconstruct accounting; never infer zero transport from zero generations."""
    pending: dict[str, Any] | None = None
    attempts: list[dict[str, Any]] = []
    duration_ms = completed = failed = 0
    last_sequence = 0
    receipt_hashes = []
    for event in events:
        if event.type not in {
            EventType.INPUT_TOKEN_COUNT_STARTED,
            EventType.INPUT_TOKEN_COUNT_FINISHED,
        }:
            continue
        body = event.payload
        if (
            event.run_id != run_id
            or body.get("run_id") != run_id
            or event.sequence <= last_sequence
            or event.actor != "provider-count-accounting"
            or event.correlation_id != body.get("attempt_id")
            or body.get("policy_version") != COUNT_ACCOUNTING_POLICY
            or body.get("content_hash") != _body_hash(body)
            or type(body.get("attempt_index")) is not int
            or body["attempt_index"] < 1
            or any(
                not isinstance(body.get(key), str)
                or re.fullmatch(r"sha256:[0-9a-f]{64}", body[key]) is None
                for key in ("request_body_hash", "tool_schema_hash", "attempt_id")
            )
        ):
            raise RecoveryError("input-token count receipt identity differs")
        last_sequence = event.sequence
        receipt_hashes.append(body["content_hash"])
        if event.type == EventType.INPUT_TOKEN_COUNT_STARTED:
            expected_index = len(attempts) + 1
            expected_id = sha256_json(
                {
                    "run_id": run_id,
                    "attempt_index": expected_index,
                    "request_body_hash": body.get("request_body_hash"),
                }
            )
            if (
                pending is not None
                or failed
                or body.get("attempt_index") != expected_index
                or body.get("attempt_id") != expected_id
                or body.get("transport_max_retries") != 0
                or body.get("endpoint") != "responses.input_tokens.count"
                or type(body.get("transport_max_retries")) is not int
                or body.get("transport_delivery_confirmed") is not False
                or body.get("schema_version") != "input-token-count-attempt-started-v1"
                or set(body)
                != _COMMON_KEYS
                | {
                    "endpoint",
                    "transport_max_retries",
                    "schema_admission",
                    "transport_delivery_confirmed",
                }
            ):
                raise RecoveryError("input-token count attempt sequence differs")
            admission = body.get("schema_admission")
            if (
                not isinstance(admission, dict)
                or admission.get("content_hash") != _body_hash(admission)
                or admission.get("tool_schema_hash") != body.get("tool_schema_hash")
                or admission.get("policy_version") != PROVIDER_SCHEMA_POLICY
                or admission.get("provider_authority_granted") is not False
                or admission.get("provider_acceptance_observed") is not False
                or admission.get("schema_version") != "provider-tool-schema-admission-v1"
                or set(admission)
                != {
                    "schema_version",
                    "policy_version",
                    "tool_schema_hash",
                    "tool_names",
                    "property_count",
                    "enum_value_count",
                    "max_schema_depth",
                    "provider_acceptance_observed",
                    "provider_authority_granted",
                    "content_hash",
                }
                or type(admission.get("tool_names")) is not list
                or not admission["tool_names"]
                or any(
                    type(name) is not str or re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", name) is None
                    for name in admission["tool_names"]
                )
                or len(set(admission["tool_names"])) != len(admission["tool_names"])
                or any(
                    type(admission.get(key)) is not int or admission[key] < 0
                    for key in ("property_count", "enum_value_count", "max_schema_depth")
                )
            ):
                raise RecoveryError("input-token count schema binding differs")
            pending = body
            attempts.append(body)
        else:
            if body.get("schema_version") != "input-token-count-attempt-finished-v1" or set(
                body
            ) != _COMMON_KEYS | {
                "started_receipt_hash",
                "outcome",
                "input_tokens",
                "duration_ms",
                "error",
            }:
                raise RecoveryError("input-token count completion schema differs")
            if pending is None or any(
                body.get(key) != pending.get(key)
                for key in ("attempt_id", "attempt_index", "request_body_hash", "tool_schema_hash")
            ):
                raise RecoveryError("input-token count completion binding differs")
            if body.get("started_receipt_hash") != pending["content_hash"]:
                raise RecoveryError("input-token count start receipt differs")
            duration = body.get("duration_ms")
            if type(duration) is not int or duration < 0:
                raise RecoveryError("input-token count duration differs")
            if body.get("outcome") == "completed":
                value = body.get("input_tokens")
                if type(value) is not int or value <= 0 or body.get("error") is not None:
                    raise RecoveryError("input-token count result differs")
                completed += 1
            elif body.get("outcome") == "failed":
                error = body.get("error")
                if (
                    body.get("input_tokens") is not None
                    or not isinstance(error, dict)
                    or set(error) != {"http_status", "provider_code", "failure_class"}
                    or error.get("failure_class")
                    not in {
                        "invalid_count_result",
                        "provider_http_rejection",
                        "transport_or_adapter_error",
                    }
                    or (
                        error.get("http_status") is not None
                        and (
                            type(error["http_status"]) is not int
                            or not 100 <= error["http_status"] <= 599
                        )
                    )
                    or (
                        error.get("provider_code") is not None
                        and (
                            type(error["provider_code"]) is not str
                            or error["provider_code"] not in _PROVIDER_CODES
                        )
                    )
                ):
                    raise RecoveryError("input-token count failure differs")
                failed += 1
            else:
                raise RecoveryError("input-token count outcome differs")
            duration_ms += duration
            pending = None
    body = {
        "schema_version": "input-token-count-attempt-summary-v1",
        "policy_version": COUNT_ACCOUNTING_POLICY,
        "run_id": run_id,
        "logical_attempts": len(attempts),
        "completed": completed,
        "failed": failed,
        "outcome_unknown": int(pending is not None),
        "duration_ms": duration_ms,
        "last_attempt_id": attempts[-1]["attempt_id"] if attempts else None,
        "attempt_chain_hash": sha256_json(receipt_hashes),
        "http_request_total": None,
        "billing_observed": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def assert_input_token_count_recoverable(run_id: str, events: Sequence[RunEvent]) -> None:
    state = project_input_token_count_attempts(run_id, events)
    if state["outcome_unknown"]:
        raise ProviderInputTokenCountUncertainError(
            "an input-token count attempt has an unknown outcome; automatic retry is closed",
            details={"input_token_count_accounting": state},
        )
    if state["failed"]:
        raise ProviderInputTokenCountError(
            "a prior input-token count attempt failed; automatic retry is closed",
            details={"input_token_count_accounting": state},
        )


def _safe_error(error: Exception) -> dict[str, Any]:
    status = getattr(error, "status_code", None)
    code = getattr(error, "code", None)
    return {
        "http_status": status if type(status) is int and 100 <= status <= 599 else None,
        "provider_code": code if type(code) is str and code in _PROVIDER_CODES else None,
        "failure_class": (
            "invalid_count_result"
            if isinstance(error, ValueError)
            else "provider_http_rejection"
            if type(status) is int
            else "transport_or_adapter_error"
        ),
    }


def counted_request_with_receipts(
    *,
    state: StateStore,
    run_id: str,
    request: dict[str, Any],
    count: Callable[[dict[str, Any]], int],
    monotonic: Callable[[], float] = time.monotonic,
) -> int:
    # The gate is before the intent receipt and before the callback. Adapter V3
    # validates again immediately before its transport, covering request drift.
    admission = validate_provider_tool_schemas(request)
    events = state.list_events(run_id)
    assert_input_token_count_recoverable(run_id, events)
    prior = project_input_token_count_attempts(run_id, events)
    index = prior["logical_attempts"] + 1
    request_hash = sha256_json(request)
    attempt_id = sha256_json(
        {
            "run_id": run_id,
            "attempt_index": index,
            "request_body_hash": request_hash,
        }
    )
    common = {
        "policy_version": COUNT_ACCOUNTING_POLICY,
        "run_id": run_id,
        "attempt_id": attempt_id,
        "attempt_index": index,
        "request_body_hash": request_hash,
        "tool_schema_hash": admission["tool_schema_hash"],
    }
    started_body = {
        **common,
        "schema_version": "input-token-count-attempt-started-v1",
        "endpoint": "responses.input_tokens.count",
        "transport_max_retries": 0,
        "schema_admission": admission,
        "transport_delivery_confirmed": False,
    }
    started = {**started_body, "content_hash": sha256_json(started_body)}
    state.append_event(
        run_id,
        EventType.INPUT_TOKEN_COUNT_STARTED,
        actor="provider-count-accounting",
        correlation_id=attempt_id,
        payload=started,
    )
    clock = monotonic()
    counted: int | None = None
    error: dict[str, Any] | None = None
    original_error: Exception | None = None
    try:
        counted = count(request)
        if type(counted) is not int or counted <= 0:
            raise ValueError("input-token count must be a positive integer")
    except Exception as exc:
        original_error = exc
        error = _safe_error(exc)
        counted = None
    # BaseException deliberately leaves a durable uncertain attempt. Likewise,
    # a failure while saving this receipt cannot authorize a repeated call.
    finished_body = {
        **common,
        "schema_version": "input-token-count-attempt-finished-v1",
        "started_receipt_hash": started["content_hash"],
        "outcome": "failed" if error is not None else "completed",
        "input_tokens": counted,
        "duration_ms": int((monotonic() - clock) * 1000),
        "error": error,
    }
    state.append_event(
        run_id,
        EventType.INPUT_TOKEN_COUNT_FINISHED,
        actor="provider-count-accounting",
        correlation_id=attempt_id,
        payload={**finished_body, "content_hash": sha256_json(finished_body)},
    )
    if error is not None:
        summary = project_input_token_count_attempts(run_id, state.list_events(run_id))
        raise ProviderInputTokenCountError(
            "provider input-token count failed before model generation",
            details={"input_token_count_accounting": summary, "error": error},
        ) from original_error
    assert counted is not None
    return counted
