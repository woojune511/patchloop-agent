from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from openai import OpenAI
from test_dev_conversation_v22 import _provider_smoke
from test_dev_runner import _crash_journal_once, _enveloped_run_id, _SimulatedCrash

import patchloop.dev.runner as runner
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.agent.usage_diagnostics import provider_usage_evidence
from patchloop.contracts import ModelConfig
from patchloop.dev.state import DevJournal
from patchloop.errors import RecoveryError
from patchloop.util import canonical_json

_ABSENT = object()
_PRIVATE = "private-spec/hidden-test/reference-patch/raw-reasoning-sentinel"
_CIPHER = "encrypted-test-state"
_COUNT = 79_749
_MODEL = "gpt-5.4-mini-2026-03-17"


def _usage(input_tokens=_COUNT, output_tokens=10):
    return {
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "input_tokens_details": {"cached_tokens": 0},
        "output_tokens_details": {"reasoning_tokens": output_tokens},
        "total_tokens": input_tokens + output_tokens,
    }


def _response(usage=_ABSENT):
    return {
        "id": "resp_usage_test", "model": _MODEL, "status": "incomplete",
        "incomplete_details": {"reason": "max_output_tokens"},
        "output": [{
            "type": "reasoning", "id": "rs_usage_test", "status": "incomplete",
            "encrypted_content": _CIPHER,
            "summary": [{"type": "summary_text", "text": _PRIVATE}],
            "content": [{"type": "reasoning_text", "text": _PRIVATE}],
        }],
        **({"usage": usage} if usage is not _ABSENT else {}),
        "extra_untrusted": _PRIVATE,
    }


def _config():
    return ModelConfig(
        provider="openai", model_id=_MODEL, reasoning_effort="medium",
        transport_max_retries=0, reasoning_continuation="encrypted-v1",
        max_output_tokens=25_000,
    )


def _sdk_turn(usage):
    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(200, json=_response(usage))

    with OpenAI(api_key="unused", max_retries=0, http_client=httpx.Client(
        transport=httpx.MockTransport(respond), trust_env=False,
    )) as client:
        adapter = OpenAIResponsesAdapter(_config(), api_key="unused", client=client)
        request = adapter.request_payload("public task", [], system_prompt="test")
        turn = adapter.execute_request(request, requested_input_tokens=_COUNT)
    assert len(seen) == 1
    assert json.loads(seen[0].content) == request  # No diagnostic fields added to requests.
    assert _PRIVATE not in repr(turn)
    assert _CIPHER not in repr(turn)
    assert len(canonical_json(turn.usage_evidence)) < 2_000
    return turn


@pytest.mark.parametrize(("usage", "state", "relation", "kind", "delta"), [
    (_ABSENT, "missing", "unavailable", "usage_missing", None),
    (None, "null", "unavailable", "usage_null", None),
    (_usage(0, 0), "object", "mismatched", "input_token_count_mismatch", -_COUNT),
    (_usage(_COUNT - 1), "object", "mismatched", "input_token_count_mismatch", -1),
    (_usage(), "object", "matched", None, 0),
])
def test_sdk_usage_absence_null_zero_and_real_mismatch_are_distinct(
    usage, state, relation, kind, delta,
):
    turn = _sdk_turn(usage)
    evidence = turn.usage_evidence
    assert evidence["observation_layer"] == "sdk_response"
    assert evidence["usage_state"] == state
    assert evidence["input_count_relation"] == relation
    assert evidence["input_token_delta"] == delta
    assert evidence["failure_kind"] == kind
    assert evidence["fields"]["input_tokens"]["state"] == (
        "integer" if state == "object" else "unavailable"
    )
    assert turn.error.code == ("input_token_count_mismatch" if kind else "incomplete_response")
    assert turn.response_status == "incomplete"
    assert turn.response_incomplete_reason == "max_output_tokens"
    assert turn.output_item_types == ("reasoning",) and turn.tool_calls == []
    assert turn.provider_continuation[0].encrypted_content == _CIPHER


@pytest.mark.parametrize("value", [_ABSENT, None, 0])
@pytest.mark.parametrize("field", ["input_tokens", "output_tokens"])
def test_sdk_missing_billing_field_is_not_a_reported_zero(field, value):
    usage = _usage()
    if value is _ABSENT:
        usage.pop(field)
    else:
        usage[field] = value
    turn = _sdk_turn(usage)
    state = "missing" if value is _ABSENT else "null" if value is None else "integer"
    assert turn.usage_evidence["fields"][field]["state"] == state
    if value is _ABSENT or value is None:
        assert turn.error.code == "input_token_count_mismatch"
        assert turn.usage_evidence["failure_kind"] == f"{field}_{state}"
    if field == "output_tokens":
        assert turn.usage_evidence["input_count_relation"] == "matched"


@pytest.mark.parametrize("value", [True, 1.25, "17", _PRIVATE, [], {}, -1, 1 << 100])
def test_unusable_input_is_bounded_evidence_not_int_coercion_or_exception(value):
    usage = _usage()
    usage["input_tokens"] = value
    evidence = provider_usage_evidence(SimpleNamespace(usage=usage), _COUNT)
    assert evidence["input_count_relation"] == "unavailable"
    assert evidence["failure_kind"] in {"input_tokens_invalid_type", "input_tokens_invalid_value"}
    assert "value" not in evidence["fields"]["input_tokens"]
    assert _PRIVATE not in canonical_json(evidence)
    assert len(canonical_json(evidence)) < 2_000


@pytest.mark.parametrize("value", [_ABSENT, None])
def test_absent_breakdowns_keep_conservative_uncached_compatibility(value):
    usage = _usage()
    if value is _ABSENT:
        usage.pop("input_tokens_details")
    else:
        usage["input_tokens_details"] = value
    usage.pop("output_tokens_details")
    usage.pop("total_tokens")
    turn = _sdk_turn(usage)
    assert turn.usage_evidence["failure_kind"] is None
    assert turn.usage_evidence["cached_tokens_defaulted"] is True
    assert turn.usage_evidence["fields"]["total_tokens"]["state"] == "missing"
    assert turn.cached_input_tokens == turn.reasoning_output_tokens == 0
    assert turn.error.code == "incomplete_response"


@pytest.mark.parametrize("value", [-1, _COUNT + 1, _PRIVATE])
def test_invalid_cache_usage_is_not_silently_clamped(value):
    usage = _usage()
    usage["input_tokens_details"]["cached_tokens"] = value
    evidence = provider_usage_evidence({"usage": usage}, _COUNT)
    assert evidence["failure_kind"] == "cached_input_tokens_invalid"
    assert _PRIVATE not in canonical_json(evidence)


def _uncertain_provider(monkeypatch, tmp_path, policy, *, first_valid=False):
    request, inputs, counted = _provider_smoke(monkeypatch, tmp_path)
    request = request.model_copy(update={"context_policy": policy})
    execute = runner.OpenAIResponsesAdapter.execute_request

    def uncertain(self, request, **kwargs):
        raw = execute(self, request, **kwargs)  # Existing no-network input/counter spy.
        if first_valid and len(inputs) == 1:
            return raw
        response = _response(None)
        response["output"] = [SimpleNamespace(**item) for item in response["output"]]
        client = SimpleNamespace(max_retries=0, responses=SimpleNamespace(
            create=lambda **payload: SimpleNamespace(**response),
        ))
        adapter = OpenAIResponsesAdapter(_config(), api_key="unused", client=client)
        return adapter.execute_request(request, **kwargs)

    monkeypatch.setattr(runner.OpenAIResponsesAdapter, "execute_request", uncertain)
    return request, inputs, counted


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
@pytest.mark.parametrize("boundary", [None, "provider_call_finished", "turn_decision_recorded"])
def test_usage_failure_survives_crash_and_terminal_resume_without_execution(
    tmp_path, monkeypatch, policy, boundary,
):
    request, inputs, counted = _uncertain_provider(monkeypatch, tmp_path, policy)
    if boundary:
        _crash_journal_once(monkeypatch, event_type=boundary, when="after")
        with pytest.raises(_SimulatedCrash):
            runner.run_dev(request)
        run_id = _enveloped_run_id(request.state_root)
        # Billing priority also holds if the continuation is subsequently lost.
        journal = DevJournal(request.state_root, run_id)
        event = next(e for e in journal.events() if e["event_type"] == "provider_call_finished")
        Path(event["payload"]["continuation_ref"]["artifact"]["path"]).write_text("damaged")
        request = request.model_copy(update={"resume_run_id": run_id})
    else:
        # Even with repeat>1, uncertainty stops after the first independent run.
        request = request.model_copy(update={"repeat": 3})
    result = runner.run_dev(request)
    assert len(result["runs"]) == 1
    run = result["runs"][0]
    journal = DevJournal(request.state_root, run["run_id"])
    assert run["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert run["billing_state"] == "UNKNOWN" and run["cost_nanos"] == 0
    failure = run["provider_usage_failure"]
    assert failure["response_status"] == "incomplete"
    assert failure["incomplete_reason"] == "max_output_tokens"
    assert failure["usage_evidence"]["failure_kind"] == "usage_null"
    assert failure["usage_evidence"]["input_count_relation"] == "unavailable"
    assert journal.terminal()["payload"]["message"] == "provider usage is null; billing is unknown"
    assert len(inputs) == len(counted) == 1
    assert run["call_counts"] == {"model": 1, "input_count": 1, "tool": 0}
    events = journal.events()
    assert not any(e["event_type"] in {"protocol_correction", "action_started"} for e in events)
    assert _PRIVATE not in canonical_json(events)
    for event in events:
        if event["event_type"] in {"provider_call_finished", "turn_decision_recorded"}:
            assert event["payload"]["usage_evidence"] == failure["usage_evidence"]
    before = journal.path.read_bytes()
    resumed = request.model_copy(update={"repeat": 1, "resume_run_id": run["run_id"]})
    assert runner.run_dev(resumed)["runs"][0] == run
    assert journal.path.read_bytes() == before and len(inputs) == len(counted) == 1


def test_continuation_storage_error_cannot_hide_usage_uncertainty(tmp_path, monkeypatch):
    request, inputs, counted = _uncertain_provider(monkeypatch, tmp_path, "append-v1")

    def fail_store(*args):
        raise RecoveryError("injected artifact failure")

    monkeypatch.setattr(runner, "_store_provider_continuation", fail_store)
    run = runner.run_dev(request)["runs"][0]
    assert run["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert run["provider_usage_failure"]["usage_evidence"]["failure_kind"] == "usage_null"
    assert run["call_counts"]["tool"] == 0 and len(inputs) == len(counted) == 1


def test_usage_uncertainty_keeps_preceding_recorded_cost_on_resume(tmp_path, monkeypatch):
    request, inputs, counted = _uncertain_provider(
        monkeypatch, tmp_path, "append-v1", first_valid=True,
    )
    _crash_journal_once(
        monkeypatch, event_type="provider_call_finished", when="after",
        predicate=lambda p: p.get("error_code") == "input_token_count_mismatch",
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)
    journal = DevJournal(request.state_root, run_id)
    usage = journal.provider_usage()
    assert len(usage) == 2 and usage[0]["cost_nanos"] > 0 and usage[1]["cost_nanos"] == 0
    resumed = request.model_copy(update={"resume_run_id": run_id})
    run = runner.run_dev(resumed)["runs"][0]
    assert run["cost_nanos"] == sum(p["cost_nanos"] for p in usage)
    assert run["billing_state"] == "UNKNOWN"  # Partial known sum is not a final bill.
    assert len(inputs) == len(counted) == 2
    assert run["call_counts"]["tool"] == 1 and run["accepted_mutations"] == 0
