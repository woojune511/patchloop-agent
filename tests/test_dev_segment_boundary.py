from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from test_dev_planning import request as mock_request
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_dev_segments import assert_submitted, configured, records
from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.dev import runner, segments
from patchloop.dev.contracts import DevModelTurn, DevRunEnvelope, DevRunRequest, RequestedTool
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.errors import RecoveryError, ResumeContractMismatch
from patchloop.util import canonical_json

POLICIES = [segments.DEFAULT_BOUNDARY_POLICY, segments.SIZE_ONLY_BOUNDARY_POLICY]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("boundary policy tests must not call a real provider")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


class RepairAdapter(MockDevAdapter):
    """Wrong edit, public failure, one inspection, repair, recheck, finish."""

    inspected_failure = False

    def _next_action(self, context, tools):
        state = json.loads(context)
        wrong = self.mutation.old_text.replace("return rows", "return []")
        if state["current_public_failure"]:
            if not self.inspected_failure:
                self.inspected_failure = True
                call = RequestedTool(
                    name="read_file", action_id="boundary-failure-read",
                    arguments={"path": self.mutation.path, "start_line": 1, "end_line": 80},
                    turn_decision={"mode": "inspect", "basis": "Inspect the failed candidate.",
                                   "evidence_goal": "Locate the incorrect return value."},
                )
            else:
                call = RequestedTool(
                    name="replace_text", action_id="boundary-repair",
                    arguments={"path": self.mutation.path, "old_text": wrong,
                               "new_text": self.mutation.new_text, "occurrence": 1,
                               "hypothesis": "Parse the complete CSV input.",
                               "expected_behavior": "Return the public CSV rows."},
                    turn_decision={"mode": "mutate", "basis": "Repair the observed return path."},
                )
            return DevModelTurn(tool_calls=[call])
        turn = super()._next_action(context, tools)
        if turn.tool_calls[0].name == "replace_text":
            turn.tool_calls[0].arguments["new_text"] = wrong
        return turn


@pytest.mark.parametrize("policy", POLICIES)
def test_cli_request_policy_and_model_identity(tmp_path, monkeypatch, policy):
    base = mock_request(tmp_path).model_copy(update={"context_policy": segments.POLICY})
    captured = []
    monkeypatch.setattr(runner, "run_dev", lambda request: captured.append(request) or {})
    result = CliRunner().invoke(app, [
        "dev", "--provider", "mock", "--task", str(base.task), "--model", "mock-dev",
        "--planning-policy", "brief-v1", "--context-policy", "segmented-v1",
        "--segment-boundary-policy", policy,
    ])
    assert result.exit_code == 0, result.output
    assert captured[0].segment_boundary_policy == policy
    assert (runner._model_hash(captured[0], None) == runner._model_hash(base, None)) == (
        policy == segments.DEFAULT_BOUNDARY_POLICY
    )
    default = segments.contract()
    assert default["boundary"] == "major-result-next-valid-decision-completed-batch-or-size-v1"
    treatment = segments.contract(segments.SIZE_ONLY_BOUNDARY_POLICY)
    assert {k: v for k, v in treatment.items() if k != "boundary"} == {
        k: v for k, v in default.items() if k != "boundary"
    }


@pytest.mark.parametrize("context,policy", [
    ("append-v1", "size-only-v1"), ("native-window-v1", "size-only-v1"),
    ("segmented-v1", "unknown"),
])
def test_invalid_policy_rejects_before_run(tmp_path, monkeypatch, context, policy):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid configuration must not reach run_dev")
    monkeypatch.setattr(runner, "run_dev", forbidden)
    with pytest.raises(ValidationError, match="segment.boundary.policy"):
        DevRunRequest.model_validate({**mock_request(tmp_path).model_dump(),
                                      "context_policy": context, "segment_boundary_policy": policy})
    result = CliRunner().invoke(app, [
        "dev", "--provider", "mock", "--task", str(mock_request(tmp_path).task),
        "--model", "mock-dev", "--context-policy", context, "--segment-boundary-policy", policy,
    ])
    assert result.exit_code != 0


@pytest.mark.parametrize("policy", POLICIES)
def test_failure_read_repair_preserves_native_history_and_current_public_state(
    tmp_path, monkeypatch, policy,
):
    request, inputs, counted, views = configured(
        monkeypatch, tmp_path, planning="brief-v1", boundary_policy=policy,
        script=RepairAdapter("csv-quoted-newline"),
    )
    request = request.model_copy(update={"repair_recheck": True})
    result = runner.run_dev(request)["runs"][0]
    assert_submitted(result)
    assert result["accepted_mutations"] == 2
    assert inputs == counted
    failed = [i for i, view in enumerate(views) if view["current_public_failure"]]
    assert len(failed) == 2
    before, after = failed
    assert after == before + 1
    assert views[before]["current_diff"] == views[after]["current_diff"]
    assert views[before]["current_public_failure"] == views[after]["current_public_failure"]
    execution = views[before]["public_execution_summary"]
    assert "Other threads/subprocesses are unmeasured." in execution["interpretation"]
    assert views[after]["public_execution_summary"] == execution
    assert "replace_text" in views[after]["available_tool_names"]
    assert views[after]["remaining_budget"]["model_calls"] == (
        views[before]["remaining_budget"]["model_calls"] - 1
    )
    assert views[after]["remaining_budget"]["cost"]["remaining"] < (
        views[before]["remaining_budget"]["cost"]["remaining"]
    )
    assert views[-1]["visible_check_status"][0]["status"] == "PASS"
    if policy == segments.SIZE_ONLY_BOUNDARY_POLICY:
        assert result["context_management"]["transition_reasons"] == ["initial"]
        assert all(not view["segment_handoff"]["review_requested"] for view in views[1:])
        assert "check_result" in views[before]["working_plan"]["review_request"]["reasons"]
        assert "context_handoff" not in views[before]["working_plan"]["review_request"]["reasons"]
        old_native = [item for item in inputs[before] if "type" in item]
        new_native = [item for item in inputs[after] if "type" in item]
        assert old_native and new_native[:len(old_native)] == old_native
        assert sum(item.get("type") == "reasoning" for item in new_native) == before + 1
    else:
        assert views[after]["segment_handoff"]["review_requested"]
        assert not any(item.get("type") == "reasoning" for item in inputs[after])
    journal, store = records(request)
    for event in journal.events():
        if event["event_type"] == "turn_started":
            runner._load_active_model_input(event["payload"], store, context_policy=segments.POLICY)
    envelope = journal.load_envelope()
    serialized = json.loads(journal.envelope_path.read_text(encoding="utf-8"))
    assert envelope.segment_boundary_policy == policy
    assert ("segment_boundary_policy" in serialized) == (policy == "size-only-v1")
    assert DevRunEnvelope.model_validate(serialized).model_dump(mode="json") == serialized
    before_resume = journal.path.read_bytes()
    calls = len(inputs)
    resumed = request.model_copy(update={"resume_run_id": journal.run_id})
    assert runner.run_dev(resumed)["runs"][0] == result
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(resumed.model_copy(update={
            "segment_boundary_policy": POLICIES[policy == POLICIES[0]],
        }))
    assert journal.path.read_bytes() == before_resume and len(inputs) == calls
    with pytest.raises(RecoveryError, match="boundary policy changed"):
        segments.active(journal, store, boundary_policy=POLICIES[policy == POLICIES[0]])
    serialized["segment_boundary_policy"] = POLICIES[policy == POLICIES[0]]
    with pytest.raises(ValidationError, match="boundary policy and contract differ"):
        DevRunEnvelope.model_validate(serialized)


@pytest.mark.parametrize("policy", POLICIES)
def test_real_mock_failure_read_repair_reaches_isolated_acceptance(tmp_path, monkeypatch, policy):
    monkeypatch.setattr(runner, "MockDevAdapter", RepairAdapter)
    request = mock_request(tmp_path).model_copy(update={
        "context_policy": segments.POLICY, "segment_boundary_policy": policy,
        "repair_recheck": True,
    })
    inputs = []
    build = runner._build_model_input

    def capture(**kwargs):
        native = build(**kwargs)
        inputs.append(reconstruct_state(native, context_policy=segments.POLICY))
        return native
    monkeypatch.setattr(runner, "_build_model_input", capture)
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert result["evaluator"]["safety_state"] == "NOT_RUN"
    assert result["accepted_mutations"] == 2
    assert result["cost_nanos"] == result["call_counts"]["input_count"] == 0
    assert any(view["current_public_failure"] for view in inputs)
    assert inputs[-1]["visible_check_status"][0]["status"] == "PASS"
    assert all(view["public_task"]["task_id"] == "csv-quoted-newline" for view in inputs)


@pytest.mark.parametrize("limit", ["tokens", "request_bytes", "encrypted_item_bytes"])
def test_size_only_still_rolls_over_at_size_and_preserves_correction(tmp_path, monkeypatch, limit):
    request, inputs, counted, views = configured(
        monkeypatch, tmp_path, boundary_policy="size-only-v1", incomplete_at=(1,),
        oversized_at=() if limit == "tokens" else (1,),
    )
    if limit == "tokens":
        count = runner.OpenAIResponsesAdapter.count_input_tokens_v2

        def tokens(self, payload, **kwargs):
            normal = count(self, payload, **kwargs)
            return 60_001 if len(counted) == 3 else normal
        monkeypatch.setattr(runner.OpenAIResponsesAdapter, "count_input_tokens_v2", tokens)
    elif limit == "request_bytes":
        monkeypatch.setattr(segments, "MAX_ENCRYPTED_ITEM_BYTES", 2_000_000)
    else:
        monkeypatch.setattr(segments, "MAX_REQUEST_BYTES", 3_000_000)
    result = runner.run_dev(request)["runs"][0]
    assert_submitted(result)
    assert result["call_counts"]["model"] == len(inputs) == 5
    assert len(counted) == 5 + (limit == "tokens")
    reason = "input_tokens" if limit == "tokens" else limit
    assert result["context_management"]["transition_reasons"] == ["initial", reason]
    assert not any(item.get("type") == "reasoning" for item in inputs[2])
    assert "max_output_tokens" in canonical_json(views[2]["recent_attempt_result_next_question"])
    assert views[2]["remaining_budget"]["consecutive_protocol_corrections"] == 0
    assert views[2]["current_diff"] == views[1]["current_diff"]


@pytest.mark.parametrize("resource", ["bytes", "tokens"])
def test_size_only_fresh_required_state_cannot_bypass_limits(tmp_path, monkeypatch, resource):
    request, inputs, counted, _ = configured(monkeypatch, tmp_path, boundary_policy="size-only-v1")
    name = "MAX_REQUEST_BYTES" if resource == "bytes" else "MAX_INPUT_TOKENS"
    monkeypatch.setattr(segments, name, 1)
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "LIMIT_REACHED"
    assert not inputs and len(counted) == (resource == "tokens")


@pytest.mark.parametrize("boundary", ["action_finished", "context_segment_started"])
def test_size_only_resume_keeps_mutation_and_handoff_idempotent(tmp_path, monkeypatch, boundary):
    request, inputs, counted, _ = configured(
        monkeypatch, tmp_path, boundary_policy="size-only-v1", oversized_at=(1,),
    )
    _crash_journal_once(
        monkeypatch, event_type=boundary,
        when="before" if boundary == "action_finished" else "after",
        predicate=lambda p: p["result"]["tool"] == "replace_text"
        if boundary == "action_finished" else p["reason"] != "initial",
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, store = records(request)
    result = runner.run_dev(request.model_copy(update={"resume_run_id": journal.run_id}))["runs"][0]
    assert_submitted(result)
    assert result["accepted_mutations"] == 1
    assert len(inputs) == len(counted) == 4
    assert len([e for e in journal.events() if e["event_type"] == segments.EVENT]) == 2
    segments.active(journal, store, boundary_policy="size-only-v1")


@pytest.mark.parametrize("boundary,terminal", [
    ("input_count_started", "COUNT_TIMEOUT_OR_UNKNOWN"),
    ("provider_call_started", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
])
def test_size_only_unknown_dispatch_stops_without_retry(tmp_path, monkeypatch, boundary, terminal):
    request, inputs, counted, _ = configured(monkeypatch, tmp_path, boundary_policy="size-only-v1")
    _crash_journal_once(monkeypatch, event_type=boundary, when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, _ = records(request)
    result = runner.run_dev(request.model_copy(update={"resume_run_id": journal.run_id}))["runs"][0]
    assert result["terminal"] == terminal
    assert not inputs and len(counted) == (boundary == "provider_call_started")


def test_size_only_corrupt_continuation_cannot_hide_behind_size_reset(tmp_path, monkeypatch):
    request, inputs, counted, _ = configured(
        monkeypatch, tmp_path, boundary_policy="size-only-v1", oversized_at=(0,),
    )
    _crash_journal_once(monkeypatch, event_type="turn_decision_recorded", when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, _ = records(request)
    decision = next(e["payload"] for e in journal.events()
                    if e["event_type"] == "turn_decision_recorded")
    Path(decision["continuation_ref"]["artifact"]["path"]).write_bytes(b"corrupt")
    result = runner.run_dev(request.model_copy(update={"resume_run_id": journal.run_id}))["runs"][0]
    assert result["terminal"] == "PROVIDER_CONTINUATION_ERROR"
    assert result["call_counts"]["tool"] == 0
    assert len(inputs) == len(counted) == 1


def test_size_only_incomplete_cannot_reset_correction_allowance(tmp_path, monkeypatch):
    request, inputs, counted, _ = configured(
        monkeypatch, tmp_path, boundary_policy="size-only-v1", incomplete_at=(0, 1),
        oversized_at=(0, 1),
    )
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "INCOMPLETE_RESPONSE"
    assert result["call_counts"]["tool"] == 0
    assert len(inputs) == len(counted) == 2
