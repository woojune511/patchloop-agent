from __future__ import annotations

import copy
from datetime import UTC, datetime

import pytest

from patchloop.agent.provider_count_accounting import (
    ProviderInputTokenCountError,
    ProviderInputTokenCountUncertainError,
    counted_request_with_receipts,
    project_input_token_count_attempts,
)
from patchloop.agent.provider_schema_admission import ProviderToolSchemaError
from patchloop.agent.tools import TOOL_SCHEMAS_V28
from patchloop.contracts import EventType, RunEvent
from patchloop.errors import RecoveryError
from patchloop.util import canonical_json, sha256_json


class _MemoryState:
    def __init__(self):
        self.events = []

    def list_events(self, run_id):
        return list(self.events)

    def append_event(self, run_id, kind, *, actor, correlation_id, payload):
        event = RunEvent(
            event_id=f"evt_count_{len(self.events) + 1}",
            run_id=run_id,
            sequence=len(self.events) + 1,
            type=kind,
            actor=actor,
            correlation_id=correlation_id,
            payload=payload,
            timestamp=datetime(2026, 8, 31, tzinfo=UTC),
        )
        self.events.append(event)
        return event


def _request():
    return {"tools": copy.deepcopy(TOOL_SCHEMAS_V28), "input": "synthetic public context"}


def test_count_success_failure_unknown_and_invalid_schema_are_distinct():
    for mode in ("success", "failure", "unknown", "schema"):
        state = _MemoryState()
        calls = []
        request = _request()

        def count(body, *, observed=calls, scenario=mode):
            observed.append(body)
            if scenario == "unknown":
                raise SystemExit(90)
            if scenario == "failure":
                raise RuntimeError("NEVER_PRINT_PROVIDER_BODY")
            return 123

        if mode == "schema":
            request["tools"][0]["parameters"]["required"] = []
        expected = {
            "failure": ProviderInputTokenCountError,
            "unknown": SystemExit,
            "schema": ProviderToolSchemaError,
        }
        if mode == "success":
            assert (
                counted_request_with_receipts(
                    state=state, run_id="run_count", request=request, count=count
                )
                == 123
            )
        else:
            with pytest.raises(expected[mode]):
                counted_request_with_receipts(
                    state=state, run_id="run_count", request=request, count=count
                )
        result = project_input_token_count_attempts("run_count", state.events)
        assert result["logical_attempts"] == len(calls) == int(mode != "schema")
        assert result["completed"] == int(mode == "success")
        assert result["failed"] == int(mode == "failure")
        assert result["outcome_unknown"] == int(mode == "unknown")
        assert result["http_request_total"] is None
        assert "NEVER_PRINT_PROVIDER_BODY" not in canonical_json(
            [e.model_dump(mode="json") for e in state.events]
        )
        if mode in {"failure", "unknown"}:
            error = (
                ProviderInputTokenCountError
                if mode == "failure"
                else ProviderInputTokenCountUncertainError
            )
            with pytest.raises(error):
                counted_request_with_receipts(
                    state=state, run_id="run_count", request=request, count=count
                )
            assert len(calls) == 1


@pytest.mark.parametrize(
    "damage",
    [
        "hash",
        "foreign_run",
        "finish_binding",
        "missing_start",
        "duplicate_finish",
        "reverse",
        "index_bool",
        "retry_bool",
        "correlation",
        "extra_source",
        "tool_schema",
        "nested_source",
    ],
)
def test_count_receipt_tamper_is_fail_closed(damage):
    state = _MemoryState()
    counted_request_with_receipts(
        state=state, run_id="run_count", request=_request(), count=lambda _: 123
    )
    events = copy.deepcopy(state.events)
    if damage == "hash":
        events[0].payload["content_hash"] = "sha256:" + "f" * 64
    elif damage == "foreign_run":
        events[0] = events[0].model_copy(update={"run_id": "run_foreign"})
    elif damage == "missing_start":
        events = events[1:]
    elif damage == "duplicate_finish":
        events.append(events[-1].model_copy(update={"sequence": 3}))
    elif damage == "reverse":
        events.reverse()
    elif damage == "correlation":
        events[0] = events[0].model_copy(update={"correlation_id": "foreign"})
    elif damage == "nested_source":
        receipt = events[0].payload
        admission = receipt["schema_admission"]
        admission["source_body"] = "unrequested"
        admission["content_hash"] = sha256_json(
            {k: v for k, v in admission.items() if k != "content_hash"}
        )
        receipt["content_hash"] = sha256_json(
            {k: v for k, v in receipt.items() if k != "content_hash"}
        )
    else:
        event = events[1] if damage == "finish_binding" else events[0]
        key, value = {
            "finish_binding": ("started_receipt_hash", "sha256:" + "f" * 64),
            "index_bool": ("attempt_index", True),
            "retry_bool": ("transport_max_retries", False),
            "extra_source": ("source_body", "unrequested"),
            "tool_schema": ("tool_schema_hash", "sha256:" + "f" * 64),
        }[damage]
        event.payload[key] = value
        event.payload["content_hash"] = sha256_json(
            {k: v for k, v in event.payload.items() if k != "content_hash"}
        )
    with pytest.raises(RecoveryError):
        project_input_token_count_attempts("run_count", events)


def test_count_success_recovery_is_repeatable_and_invalid_return_is_recorded():
    state = _MemoryState()
    counted_request_with_receipts(
        state=state, run_id="run_count", request=_request(), count=lambda _: 12
    )
    one = project_input_token_count_attempts("run_count", state.events)
    assert one == project_input_token_count_attempts("run_count", copy.deepcopy(state.events))
    with pytest.raises(ProviderInputTokenCountError):
        counted_request_with_receipts(
            state=state, run_id="run_count", request=_request(), count=lambda _: True
        )
    result = project_input_token_count_attempts("run_count", state.events)
    assert result["logical_attempts"] == 2 and result["completed"] == result["failed"] == 1
    assert [e.type for e in state.events] == [
        EventType.INPUT_TOKEN_COUNT_STARTED,
        EventType.INPUT_TOKEN_COUNT_FINISHED,
    ] * 2


@pytest.mark.parametrize(
    "field,value", [("provider_code", "unrequested secret body"), ("http_status", True)]
)
def test_failed_count_recovery_rejects_unsanitized_fields(field, value):
    state = _MemoryState()
    with pytest.raises(ProviderInputTokenCountError):
        counted_request_with_receipts(
            state=state, run_id="run_count", request=_request(), count=lambda _: None
        )
    event = state.events[-1]
    event.payload["error"][field] = value
    event.payload["content_hash"] = sha256_json(
        {k: v for k, v in event.payload.items() if k != "content_hash"}
    )
    with pytest.raises(RecoveryError):
        project_input_token_count_attempts("run_count", state.events)
