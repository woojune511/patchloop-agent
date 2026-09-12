from __future__ import annotations

import json
from decimal import Decimal

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError, BadRequestError, OpenAI

import patchloop.dev.runner as runner
from patchloop.agent.count_diagnostics import (
    input_count_error_metadata,
    input_count_request_metadata,
)
from patchloop.agent.model import (
    EncryptedReasoningContinuationItem,
    ModelTurn,
    ModelTurnError,
    OpenAIResponsesAdapter,
)
from patchloop.contracts import ModelConfig, TaskEnvironment
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.state import DevJournal
from patchloop.errors import ActionConflict, RecoveryError
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json

_SECRET = "sk-credential-sentinel"
_PRIVATE = "private-spec/hidden-test/reference-patch/raw-reasoning-sentinel"
_CIPHER = "ciphertext-sentinel"
_REQUEST_ID = "req_" + "a" * 32


def _bad_request(request=None, *, body=None, request_id=_REQUEST_ID):
    request = request or httpx.Request(
        "POST", "https://api.openai.com/v1/responses/input_tokens",
        headers={"Authorization": "Bearer " + _SECRET}, json={"input": _CIPHER},
    )
    return BadRequestError(
        _PRIVATE + _SECRET + _CIPHER,
        response=httpx.Response(400, request=request, headers={"x-request-id": request_id}),
        body=body if body is not None else {
            "message": _PRIVATE + _SECRET + _CIPHER, "type": "invalid_request_error",
            "code": "string_above_max_length", "param": "input[78].encrypted_content",
        },
    )


def _assert_private_absent(value):
    encoded = json.dumps(value, ensure_ascii=False)
    assert len(encoded) < 5_000
    for sentinel in (_SECRET, _PRIVATE, _CIPHER):
        assert sentinel not in encoded


def test_mock_sdk_rejection_records_wire_size_without_logging_payload_or_retries():
    calls = []

    def reject(request):
        calls.append(request)
        return httpx.Response(400, headers={"x-request-id": _REQUEST_ID}, json={
            "error": {
                "code": "string_above_max_length", "type": "invalid_request_error",
                "param": "input[1].encrypted_content", "message": _PRIVATE + _SECRET + _CIPHER,
            },
        })

    config = ModelConfig(
        provider="openai", model_id="gpt-5.4-mini-2026-03-17", transport_max_retries=0,
        reasoning_continuation="encrypted-v1", max_output_tokens=25000,
    )
    with OpenAI(api_key=_SECRET, max_retries=0, http_client=httpx.Client(
        transport=httpx.MockTransport(reject), trust_env=False,
    )) as client:
        adapter = OpenAIResponsesAdapter(config, api_key=_SECRET, client=client)
        payload = adapter.request_payload([
            {"role": "system", "content": "공개 source"},
            {"type": "reasoning", "id": "rs-test", "encrypted_content": _CIPHER * 100_000},
        ], [], system_prompt="already in input")
        before = canonical_json(payload)
        shape = input_count_request_metadata(payload)
        with pytest.raises(BadRequestError) as raised:
            adapter.count_input_tokens_v2(payload, timeout_seconds=3)
        error = input_count_error_metadata(raised.value)
    assert len(calls) == 1
    assert canonical_json(payload) == before
    count_body = json.loads(calls[0].content)
    assert count_body == OpenAIResponsesAdapter._count_payload(payload)
    assert "timeout" not in count_body and "max_output_tokens" not in count_body
    encoded = canonical_json(count_body).encode("utf-8")
    assert shape["count_payload_canonical_utf8_bytes"] == len(encoded)
    assert shape["count_payload_canonical_hash"] == sha256_bytes(encoded)
    assert shape["largest_encrypted_content_characters"] == len(_CIPHER) * 100_000
    assert shape["encrypted_content_characters"] == len(_CIPHER) * 100_000
    assert shape["input_item_count"] == 2 and shape["reasoning_item_count"] == 1
    assert error["observed_request_body_bytes"] == len(calls[0].content)
    assert error["observed_request_body_hash"] == sha256_bytes(calls[0].content)
    assert error["http_status"] == 400 and error["category"] == "http_error"
    assert error["code"] == "string_above_max_length"
    assert error["param"] == "input[1].encrypted_content"
    assert error["request_id"] == _REQUEST_ID
    _assert_private_absent({"shape": shape, "error": error})


@pytest.mark.parametrize("body", [
    _PRIVATE,
    {"code": _SECRET, "type": _PRIVATE, "param": _CIPHER},
    {"code": [_SECRET], "type": {"secret": _PRIVATE}, "param": 42},
    {"code": "x" * 10_000, "param": "input[0]." + _PRIVATE * 1_000},
])
def test_unknown_provider_fields_are_omitted_not_truncated(body):
    result = input_count_error_metadata(_bad_request(body=body, request_id=_SECRET))
    assert result["http_status"] == 400
    assert all(result[field] is None for field in ("code", "type", "param", "request_id"))
    assert "request_id" in result["redacted_fields"]
    _assert_private_absent(result)


@pytest.mark.parametrize("param", ["input[78].encrypted_content", "input.78.encrypted_content",
                                    "reasoning.effort", "tools[2].parameters", "model"])
def test_structural_error_parameter_is_retained(param):
    result = input_count_error_metadata(_bad_request(body={"error": {
        "param": param, "type": "invalid_request_error", "code": "invalid_value",
    }}))
    assert result["param"] == param and result["code"] == "invalid_value"


@pytest.mark.parametrize("kind,category", [
    (TimeoutError, "timeout"), (APITimeoutError, "timeout"),
    (APIConnectionError, "transport_error"), (RuntimeError, "unknown"),
])
def test_non_http_errors_are_bounded_and_distinct(kind, category):
    request = httpx.Request("POST", "https://api.openai.com/v1/responses/input_tokens")
    error = (kind(request=request) if kind in (APIConnectionError, APITimeoutError)
             else kind(_PRIVATE))
    result = input_count_error_metadata(error)
    assert result["category"] == category and result["http_status"] is None
    _assert_private_absent(result)


def test_unread_request_stream_is_not_consumed_for_diagnostics():
    def forbidden_stream():
        raise AssertionError("diagnostics consumed request stream")
        yield b""  # pragma: no cover

    request = httpx.Request("POST", "https://api.openai.com", content=forbidden_stream())
    result = input_count_error_metadata(_bad_request(request))
    assert "observed_request_body_bytes" not in result


@pytest.fixture
def synthetic_count_run(tmp_path, monkeypatch):
    counts, generations, inputs = [], [], []

    class FakeAdapter:
        def __init__(self, config, *, api_key):
            assert api_key == "unused"

        def request_payload(self, context, tools, *, system_prompt):
            return {"input": context, "tools": tools, "max_output_tokens": 25000}

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            counts.append(request)
            if len(counts) > 1:
                raise _bad_request()
            return 20

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            generations.append(request)
            inputs.append(request["input"])
            return ModelTurn(
                input_tokens=20, output_tokens=25000, reasoning_output_tokens=25000,
                response_status="incomplete", response_incomplete_reason="max_output_tokens",
                error=ModelTurnError("incomplete_response", "max_output_tokens"),
                output_item_types=("reasoning",),
                provider_continuation=(EncryptedReasoningContinuationItem("rs-test", "opaque"),),
            )

    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", FakeAdapter)
    monkeypatch.setattr(runner, "_live_task_is_admitted", lambda *args: None)
    monkeypatch.setattr(runner, "_live_source_preflight", lambda *args, **kwargs: None)
    monkeypatch.setattr(runner, "_live_sandbox_preflight", lambda *args, **kwargs: LocalSandbox())
    monkeypatch.setattr(runner, "load_exact_openai_api_key", lambda path: "unused")
    request = DevRunRequest(
        provider="openai", model="gpt-5.4-mini-2026-03-17", state_root=tmp_path,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        env_file=tmp_path / "unused.env", max_cost_usd=Decimal("1.20"),
    )
    task_dir, package = runner._resolve_task_file(request.task)
    package = package.model_copy(update={"environment": TaskEnvironment(
        evaluator_image="audit/image@sha256:" + "a" * 64, image_digest="sha256:" + "a" * 64,
    )})
    monkeypatch.setattr(runner, "_resolve_task_file", lambda task: (task_dir, package))
    return request, counts, generations


def test_incomplete_then_count_failure_stops_repetitions_with_operator_only_evidence(
    synthetic_count_run,
):
    request, counts, generations = synthetic_count_run
    result = runner.run_dev(request.model_copy(update={"repeat": 3}))
    assert result["completed_repetitions"] == 1
    row = result["runs"][0]
    assert row["terminal"] == "COUNT_TIMEOUT_OR_UNKNOWN"
    assert row["call_counts"] == {"model": 1, "input_count": 2, "tool": 0}
    assert len(counts) == 2 and len(generations) == 1
    assert row["input_count_failure"]["error"]["http_status"] == 400
    assert row["input_count_failure"]["request_metadata"]["reasoning_item_count"] == 1
    assert sum(item.get("type") == "reasoning" for item in counts[-1]["input"]) == 1
    for request_payload in counts:
        assert "input_count_failure" not in json.dumps(request_payload)
        assert "request_metadata" not in json.dumps(request_payload)
    journal = DevJournal(request.state_root, row["run_id"])
    assert journal.terminal()["payload"]["input_count_failure"] == row["input_count_failure"]
    assert len([r for r in journal.events() if r["event_type"] == "input_count_failed"]) == 1
    _assert_private_absent(row)
    for sentinel in (_SECRET, _PRIVATE, _CIPHER):
        assert sentinel not in journal.path.read_text(encoding="utf-8")
        for path in (request.state_root / "artifacts").rglob("*.json"):
            assert sentinel not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("boundary", ["input_count_started", "input_count_failed", "terminal"])
def test_count_interruption_resumes_metadata_only_and_terminal_is_idempotent(
    synthetic_count_run, monkeypatch, boundary,
):
    request, counts, generations = synthetic_count_run
    append = DevJournal.append
    crashed = False

    class Crash(BaseException):
        pass

    def crash_after_record(self, event_type, payload=None):
        nonlocal crashed
        result = append(self, event_type, payload)
        if not crashed and len(generations) == 1 and event_type == boundary:
            crashed = True
            raise Crash()
        return result

    monkeypatch.setattr(DevJournal, "append", crash_after_record)
    with pytest.raises(Crash):
        runner.run_dev(request)
    path = next((request.state_root / "runs").glob("*.jsonl"))
    journal = DevJournal(request.state_root, path.stem)
    failed_before = journal.unresolved_input_count()
    calls_before = len(counts)
    spent = sum(row["cost_nanos"] for row in journal.provider_usage())

    def forbidden(*args, **kwargs):
        raise AssertionError("metadata-only resume reached execution or credentials")

    for name in ("OpenAIResponsesAdapter", "WorkspaceManager", "load_exact_openai_api_key",
                 "_live_sandbox_preflight", "_live_source_preflight"):
        monkeypatch.setattr(runner, name, forbidden)
    resumed = request.model_copy(update={"resume_run_id": path.stem})
    first = runner.run_dev(resumed)["runs"][0]
    assert first["terminal"] == "COUNT_TIMEOUT_OR_UNKNOWN"
    assert first["input_count_failure"] == failed_before
    assert first["call_counts"] == {"model": 1, "input_count": 2, "tool": 0}
    assert first["cost_nanos"] == spent > 0
    expected = "interrupted" if boundary == "input_count_started" else "http_error"
    assert first["input_count_failure"]["error"]["category"] == expected
    before = journal.path.read_bytes()
    assert runner.run_dev(resumed)["runs"][0] == first
    assert journal.path.read_bytes() == before
    assert len(counts) == calls_before and len(generations) == 1


def test_count_failure_receipt_is_idempotent_and_bound_to_admitted_request(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_count_failure")
    start = {"count_id": "count_a", "turn_id": "turn_a", "request_hash": sha256_json({})}
    journal.append("input_count_started", start)
    payload = {**start, "error": input_count_error_metadata(_bad_request())}
    recorded = journal.append("input_count_failed", payload)
    assert journal.append("input_count_failed", payload) == recorded
    assert journal.unresolved_input_count()["error"] == payload["error"]
    with pytest.raises(ActionConflict):
        journal.append("input_count_failed", {**payload, "request_hash": sha256_json("other")})
    journal.append("input_count_finished", {**start, "input_tokens": 100})
    with pytest.raises(RecoveryError, match="conflicting outcomes"):
        journal.unresolved_input_count()


@pytest.mark.parametrize("key", ["count_id", "turn_id", "request_hash"])
def test_count_failure_with_mismatched_admission_is_rejected(tmp_path, key):
    journal = DevJournal(tmp_path, "run_dev_count_mismatch")
    start = {"count_id": "count_a", "turn_id": "turn_a", "request_hash": sha256_json({})}
    journal.append("input_count_started", start)
    journal.append("input_count_failed", {**start, key: "different", "error": {}})
    with pytest.raises(RecoveryError, match="match"):
        journal.unresolved_input_count()
