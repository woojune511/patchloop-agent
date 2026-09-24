from __future__ import annotations

import copy
import json
from dataclasses import replace
from decimal import Decimal

import httpx
import pytest
from pydantic import ValidationError
from test_dev_planning import request as mock_request
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_dev_segments import assert_submitted, configured, records
from typer.testing import CliRunner

from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.cli import app
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunEnvelope, DevRunRequest
from patchloop.dev.model import MockDevAdapter
from patchloop.errors import ResumeContractMismatch


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("output-ceiling tests must not make network requests")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


@pytest.mark.parametrize("value", [0, 127, 128_001, True, 25_000.5, "50000"])
def test_invalid_ceiling_rejects_before_execution(tmp_path, value):
    with pytest.raises(ValidationError, match="max_output_tokens"):
        DevRunRequest.model_validate({**mock_request(tmp_path).model_dump(),
                                      "max_output_tokens": value})


@pytest.mark.parametrize("value", [128, 25_000, 50_000, 128_000])
def test_cli_selects_ceiling_and_default_identity_is_preserved(tmp_path, monkeypatch, value):
    captures = []
    monkeypatch.setattr(runner, "run_dev", lambda request: captures.append(request) or {})
    base = mock_request(tmp_path)
    result = CliRunner().invoke(app, [
        "dev", "--provider", "mock", "--task", str(base.task), "--model", base.model,
        "--planning-policy", "brief-v1", "--max-output-tokens", str(value),
    ])
    assert result.exit_code == 0, result.output
    assert captures[0].max_output_tokens == value
    default = base.model_copy(update={"max_output_tokens": 25_000})
    assert default.model_dump() == base.model_dump()
    assert "max_output_tokens" not in base.model_dump(mode="json")
    assert runner._model_hash(base, None) == runner._model_hash(default, None)
    assert (runner._model_hash(base, None) == runner._model_hash(captures[0], None)) == (
        value == 25_000
    )


def instrument_provider(monkeypatch):
    """Use the real request serializer with an offline provider and real admission."""
    implementation = runner.OpenAIResponsesAdapter
    execute, count = implementation.execute_request, implementation.count_input_tokens_v2
    configs, dispatched, counted = [], [], []

    def init(self, config, *, api_key):
        self.config = config
        configs.append(config)

    def capture_count(self, payload, **kwargs):
        counted.append(copy.deepcopy(payload))
        return count(self, payload, **kwargs)

    def capture_dispatch(self, payload, **kwargs):
        dispatched.append(copy.deepcopy(payload))
        return execute(self, payload, **kwargs)

    monkeypatch.setattr(implementation, "__init__", init)
    monkeypatch.setattr(implementation, "request_payload", OpenAIResponsesAdapter.request_payload)
    monkeypatch.setattr(implementation, "count_input_tokens_v2", capture_count)
    monkeypatch.setattr(implementation, "execute_request", capture_dispatch)
    return configs, counted, dispatched


@pytest.mark.parametrize("ceiling", [25_000, 50_000])
def test_selected_ceiling_binds_count_dispatch_resume_and_envelope(tmp_path, monkeypatch, ceiling):
    request, inputs, counts, views = configured(monkeypatch, tmp_path, planning="brief-v1")
    request = request.model_copy(update={"max_output_tokens": ceiling})
    configs, counted, dispatched = instrument_provider(monkeypatch)
    _crash_journal_once(monkeypatch, event_type="tool_batch_finished", when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, _ = records(request)
    before = journal.path.read_bytes()
    resumed = request.model_copy(update={"resume_run_id": journal.run_id})
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(resumed.model_copy(update={
            "max_output_tokens": 50_000 if ceiling == 25_000 else 25_000,
        }))
    assert journal.path.read_bytes() == before and len(dispatched) == 1
    result = runner.run_dev(resumed)["runs"][0]
    assert_submitted(result)
    assert len(dispatched) == len(counted) == 4
    assert counts == inputs
    assert all(c.max_output_tokens == ceiling for c in configs)
    assert all(p["max_output_tokens"] == ceiling for p in counted + dispatched)
    assert counted == dispatched
    assert all(view["public_task"] and view["current_diff"] is not None for view in views)
    assert views[-1]["visible_check_status"][0]["status"] == "PASS"
    envelope = journal.load_envelope()
    raw = envelope.model_dump(mode="json")
    assert ("max_output_tokens" in raw) == (ceiling != 25_000)
    assert DevRunEnvelope.model_validate(raw).model_dump(mode="json") == raw
    assert envelope.max_output_tokens == ceiling
    started = next(e["payload"] for e in journal.events() if e["event_type"] == "run_started")
    assert started.get("max_output_tokens", 25_000) == ceiling
    for event in journal.events():
        if event["event_type"] == "provider_call_started":
            assert event["payload"]["output_ceiling"] == ceiling
    closed = journal.path.read_bytes()
    assert runner.run_dev(resumed)["runs"][0] == result
    assert journal.path.read_bytes() == closed and len(dispatched) == 4


def test_remaining_money_lowers_fifty_thousand_and_stops_without_retry(tmp_path, monkeypatch):
    request, _, _, _ = configured(monkeypatch, tmp_path, planning="brief-v1")
    request = request.model_copy(update={"max_output_tokens": 50_000,
                                         "max_cost_usd": Decimal("0.35")})
    _, counted, dispatched = instrument_provider(monkeypatch)
    implementation = runner.OpenAIResponsesAdapter
    count, execute = implementation.count_input_tokens_v2, implementation.execute_request

    def exact_count(self, payload, **kwargs):
        count(self, payload, **kwargs)
        return 60_000

    def spend(self, payload, **kwargs):
        return replace(execute(self, payload, **kwargs), output_tokens=payload["max_output_tokens"])

    monkeypatch.setattr(implementation, "count_input_tokens_v2", exact_count)
    monkeypatch.setattr(implementation, "execute_request", spend)
    result = runner.run_dev(request)["runs"][0]
    assert [p["max_output_tokens"] for p in dispatched] == [50_000, 7_777]
    assert all(p["max_output_tokens"] == 50_000 for p in counted)
    assert len(counted) == 3
    assert result["terminal"] == "COST_CAP_REACHED" and result["evaluator"] is None
    assert result["cost_nanos"] == 349_996_500


@pytest.mark.parametrize("ceiling", [25_000, 50_000])
def test_mock_smoke_reaches_isolated_evaluation_with_public_state(tmp_path, monkeypatch, ceiling):
    request = mock_request(tmp_path).model_copy(update={
        "context_policy": "segmented-v1", "max_output_tokens": ceiling,
    })
    inputs, manifests = [], []
    next_turn, manifest = MockDevAdapter.next_turn, runner._manifest

    def capture(self, context, tools):
        inputs.append(json.loads(context))
        return next_turn(self, context, tools)

    def capture_manifest(**kwargs):
        result = manifest(**kwargs)
        manifests.append(result)
        return result

    monkeypatch.setattr(MockDevAdapter, "next_turn", capture)
    monkeypatch.setattr(runner, "_manifest", capture_manifest)
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert result["evaluator"]["safety_state"] == "NOT_RUN"
    assert result["accepted_mutations"] == 1 and result["artifact_hashes"]["submitted_patch"]
    assert len(inputs) == 4
    assert all(v["public_task"] and "current_diff" in v and "visible_check_status" in v
               for v in inputs)
    assert inputs[-1]["visible_check_status"][0]["status"] == "PASS"
    assert len(manifests) == 1 and manifests[0].model.max_output_tokens == ceiling
