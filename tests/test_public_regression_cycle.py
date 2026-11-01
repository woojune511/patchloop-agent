"""Real CSV edits and public-check receipts; finite fake model and sandbox outputs."""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from test_exception_frame_repair import edit_call, no_external, stop_call  # noqa: F401
from test_feedback_repair_cycle import read, setup
from test_first_edit_checkpoint import evidence
from test_repair_cycle import RecordedGateway

from diagnostics import first_edit_checkpoint as checkpoint
from diagnostics.checkpoint_continuation import ScriptedClient
from diagnostics.public_regression import PublicRegressionRecheck
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.contracts import RequestedTool
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.sandbox.runner import SandboxResult
from patchloop.util import sha256_json

FAILURE = "AssertionError: CSV_REGRESSION_FIRST_EDIT"


class RegressionSandbox:
    official = False

    def __init__(self, gateway, *, always_fail=False, immediately_pass=False):
        self.gateway = gateway
        self.always_fail, self.immediately_pass = always_fail, immediately_pass
        self.executions = []

    def run_check(self, workspace, check):
        assert workspace == self.gateway.workspace
        failed = self.always_fail or (
            not self.immediately_pass and self.gateway.accepted_mutations < 2)
        self.executions.append({"diff": self.gateway.current_diff_hash, "check_id": check.id,
                                "failed": failed})
        stdout = "Public existing CSV suite\n" + (FAILURE if failed else "public suite passed")
        stderr = ("Traceback (most recent call last):\n"
                  '  File "tests/test_existing.py", line 3, in test_rows\n'
                  "    assert actual == expected\n" + FAILURE if failed else "")
        return SandboxResult(command=list(check.command), exit_code=int(failed),
            stdout=stdout, stderr=stderr, duration_ms=1, timed_out=False, truncated=False,
            original_output_bytes=len((stdout + stderr).encode()),
            execution_policy={"cleanup_status": "confirmed"})


class BoundaryClient(ScriptedClient):
    def __init__(self, steps, *, still_large=False):
        super().__init__(steps)
        self.still_large = still_large

    def count(self, **request):
        body = json.loads(request["input"][1]["content"])
        if body.get("format") == checkpoint.dedup.FORMAT:
            body = checkpoint.dedup.expand(body)
        self.input_tokens = (60_001 if len(self.created) == 1
            and (self.still_large or "current_handoff" not in body) else 100)
        return super().count(**request)


def prepare(gateway_factory, tmp_path, monkeypatch, *, always_fail=False, immediately_pass=False):
    gateway, journal, loaded, cycle, baseline = setup(
        gateway_factory, tmp_path, monkeypatch, limits=checkpoint.LIMITS)
    host_read = read("registered-initial-source")
    host_read["arguments"].pop("memory_update")
    assert gateway.execute(RequestedTool.model_validate(host_read)).status == "succeeded"
    gateway.limits.max_tool_actions = checkpoint.LIMITS.model_tools + 1
    gateway.limits.max_accepted_mutations = checkpoint.LIMITS.accepted_edits
    loaded.common = evidence()
    # Isolate regression-driven revision: the original caller already passes after edit one.
    monkeypatch.setattr(cycle, "_gateway", lambda *_: RecordedGateway(
        cycle.journal, gateway.current_diff_hash, failed=False))
    sandbox = RegressionSandbox(gateway, always_fail=always_fail,
                                 immediately_pass=immediately_pass)
    gateway.sandbox = sandbox
    regression = PublicRegressionRecheck(loaded, gateway, tmp_path / "public-regression")
    feedbacks = []
    check = regression.check

    def record_feedback():
        feedback = check()
        feedbacks.append(copy.deepcopy(feedback))
        return feedback

    monkeypatch.setattr(regression, "check", record_feedback)
    first, second = edit_call(), edit_call()
    original = first["arguments"]["old_text"]
    temporary = "# first attempted repair\n" + original
    first["arguments"]["new_text"] = temporary
    second["action_id"] = "revise-regression"
    second["arguments"]["old_text"] = temporary
    return SimpleNamespace(gateway=gateway, journal=journal, loaded=loaded, cycle=cycle,
        baseline=baseline, regression=regression, sandbox=sandbox, feedbacks=feedbacks,
        steps=[[first], [read("inspect-regression")], [second], [stop_call()]])


def run(fixture, *, client=None):
    client = client or ScriptedClient(fixture.steps)
    adapter = checkpoint.loop.OpenAIResponsesAdapter(checkpoint.loop.config(), api_key="",
                                                     client=client)
    actual = checkpoint.loop.run_model(fixture.loaded, "B", fixture.gateway, adapter,
        DevCostLedger(Decimal("1.20"), pricing_for_model(checkpoint.loop.MODEL)),
        first_hash=sha256_json(checkpoint.request_payload(fixture.loaded.common, "B")),
        profile=checkpoint.PROFILE, request_builder=checkpoint.request_payload,
        cycle=fixture.cycle, regression=fixture.regression)
    return actual, client


def state(request):
    return json.loads(request["input"][-1]["content"])


def tools(request):
    return {tool["name"] for tool in request["tools"]}


def test_regression_failure_reaches_next_request_and_second_edit_is_checked_fresh(
    gateway_factory, tmp_path, monkeypatch,
):
    fixture = prepare(gateway_factory, tmp_path, monkeypatch)
    actual, client = run(fixture)
    assert actual["terminal"] == "AGENT_STOPPED" and actual["new_mutations"] == 2
    assert actual["normal_calls"] == actual["tool_actions"] == len(client.created) == 4
    assert actual["correction_calls"] == actual["diagnostic_probes"] == 0
    assert tools(client.created[0]) == {"replace_text", "stop_task"}
    after_failure = state(client.created[1])
    original = after_failure["current_trial_original_recheck"]
    failed = after_failure["current_trial_public_regression"]
    assert failed == fixture.feedbacks[0]
    assert original["status"] == "supported" and failed["status"] == "failed"
    assert original["candidate_diff_hash"] == failed["candidate_diff_hash"]
    assert failed["checks"][0]["check_id"] == "existing-unit-tests"
    assert failed["checks"][0]["stdout_tail"] == "Public existing CSV suite\n" + FAILURE
    assert failed["checks"][0]["exception_type"] == "AssertionError"
    assert {"read_file", "search_files", "replace_text", "stop_task"} <= tools(client.created[1])
    assert "run_probe" not in tools(client.created[1])
    final = state(client.created[-1])
    passed = final["current_trial_public_regression"]
    assert passed == fixture.feedbacks[1]
    assert final["current_trial_original_recheck"]["status"] == "supported"
    assert passed["status"] == "passed" and tools(client.created[-1]) == {"stop_task"}
    assert passed["candidate_diff_hash"] == fixture.gateway.current_diff_hash
    assert passed["candidate_diff_hash"] != failed["candidate_diff_hash"]
    assert passed["receipts"] != failed["receipts"]
    assert passed["task_acceptance"] == failed["task_acceptance"] == "NOT_ASSESSED"
    assert fixture.sandbox.executions == [
        {"diff": failed["candidate_diff_hash"], "check_id": "existing-unit-tests", "failed": True},
        {"diff": passed["candidate_diff_hash"], "check_id": "existing-unit-tests", "failed": False},
    ]
    assert fixture.regression.host_actions == 2 and fixture.cycle.host_actions == 3
    assert fixture.baseline.dispatches == 1
    assert fixture.regression.current_receipts()[0]["workspace_diff_hash"] == (
        fixture.gateway.current_diff_hash)
    assert actual["task_acceptance"] == "NOT_RUN"
    assert actual["registered_verification"] == "passed" and actual["public_regression"] == passed
    assert actual["host_regression_actions"] == 2
    assert actual["new_cost_nanos"] < 1_200_000_000
    assert "PRIVATE_SENTINEL" not in str(client.created)


def test_failed_second_regression_is_reported_when_no_edit_budget_remains(
    gateway_factory, tmp_path, monkeypatch,
):
    fixture = prepare(gateway_factory, tmp_path, monkeypatch, always_fail=True)
    actual, client = run(fixture)
    assert actual["terminal"] == "AGENT_STOPPED" and actual["new_mutations"] == 2
    final = state(client.created[-1])
    assert final["current_trial_public_regression"]["status"] == "failed"
    assert final["current_trial_public_regression"]["candidate_diff_hash"] == (
        fixture.gateway.current_diff_hash)
    assert final["remaining"]["accepted_mutations"] == 0
    assert tools(client.created[-1]) == {"stop_task"}
    assert len(fixture.sandbox.executions) == 2
    assert actual["task_acceptance"] == "NOT_RUN"
    assert actual["registered_verification"] == "unverified"
    assert actual["public_regression"] == final["current_trial_public_regression"]


def test_protocol_correction_keeps_failed_regression_and_funds_second_edit(
    gateway_factory, tmp_path, monkeypatch,
):
    fixture = prepare(gateway_factory, tmp_path, monkeypatch)
    fixture.steps = [fixture.steps[0], [], fixture.steps[2], [stop_call()]]
    actual, client = run(fixture)
    assert actual["terminal"] == "AGENT_STOPPED" and actual["new_mutations"] == 2
    assert actual["normal_calls"] == actual["tool_actions"] == 3
    assert actual["correction_calls"] == 1 and len(client.created) == 4
    failed = fixture.feedbacks[0]
    correction = state(client.created[2])
    assert correction["protocol_correction"]
    assert correction["current_trial_public_regression"] == failed
    assert correction["current_trial_original_recheck"]["status"] == "supported"
    assert correction["remaining"]["normal_calls"] == 2
    assert correction["remaining"]["tool_actions"] == 4
    assert correction["remaining"]["accepted_mutations"] == 1
    assert client.created[2]["max_output_tokens"] == 25_000
    assert "replace_text" in tools(client.created[2])
    assert state(client.created[-1])["current_trial_public_regression"] == fixture.feedbacks[1]
    assert fixture.feedbacks[1]["status"] == "passed"
    assert fixture.feedbacks[1]["candidate_diff_hash"] != failed["candidate_diff_hash"]
    assert tools(client.created[-1]) == {"stop_task"}
    assert fixture.regression.host_actions == 2 and fixture.cycle.host_actions == 3
    assert actual["registered_verification"] == "passed" and actual["task_acceptance"] == "NOT_RUN"


def test_passing_first_regression_does_not_offer_an_unnecessary_second_edit(
    gateway_factory, tmp_path, monkeypatch,
):
    fixture = prepare(gateway_factory, tmp_path, monkeypatch, immediately_pass=True)
    fixture.steps = [fixture.steps[0], [stop_call()]]
    actual, client = run(fixture)
    assert actual["terminal"] == "AGENT_STOPPED" and actual["new_mutations"] == 1
    assert state(client.created[-1])["current_trial_public_regression"]["status"] == "passed"
    assert tools(client.created[-1]) == {"stop_task"}
    assert len(fixture.sandbox.executions) == fixture.regression.host_actions == 1


def test_original_and_regression_reserves_block_an_unfunded_first_edit(
    gateway_factory, tmp_path, monkeypatch,
):
    fixture = prepare(gateway_factory, tmp_path, monkeypatch)
    # Enough for the original-only reserve; insufficient for two full public-check
    # passes and the response opportunities that consume their results.
    fixture.gateway.deadline = ExecutionDeadline.from_remaining(300)
    actual, client = run(fixture)
    assert actual["terminal"] == "RECHECK_TIME_UNAVAILABLE"
    assert client.counted == client.created == []
    assert actual["new_mutations"] == 0 and actual["task_acceptance"] == "NOT_RUN"
    assert fixture.sandbox.executions == [] and fixture.regression.host_actions == 0


@pytest.mark.parametrize("still_large", [False, True])
def test_regression_feedback_survives_handoff_or_honest_input_limit(
    gateway_factory, tmp_path, monkeypatch, still_large,
):
    fixture = prepare(gateway_factory, tmp_path, monkeypatch)
    client = BoundaryClient(fixture.steps, still_large=still_large)
    actual, client = run(fixture, client=client)
    events = fixture.journal.events()
    prepared = [event["payload"] for event in events
                if event["event_type"] == "repair_context_prepared"]
    committed = [event["payload"] for event in events
                 if event["event_type"] == "repair_context_committed"]
    assert len(prepared) == 1 and len(committed) == int(not still_large)
    failed = state(client.counted[1])["current_trial_public_regression"]
    assert failed["status"] == "failed" and FAILURE in str(failed)
    recounted = state(client.counted[2])
    assert recounted["current_trial_public_regression"] == failed
    assert recounted["remaining"]["normal_calls"] == 3
    assert recounted["remaining"]["accepted_mutations"] == 1
    assert recounted["remaining"]["tool_actions"] == 4
    if still_large:
        assert actual["terminal"] == "INPUT_LIMIT" and len(client.created) == 1
        assert actual["new_mutations"] == 1 and actual["task_acceptance"] == "NOT_RUN"
        assert len(fixture.sandbox.executions) == 1
        return
    assert actual["terminal"] == "AGENT_STOPPED" and actual["new_mutations"] == 2
    assert state(client.created[1])["current_trial_public_regression"] == failed
    body = checkpoint.dedup.expand(json.loads(client.created[1]["input"][1]["content"]))
    handoff_state = body["current_handoff"]["state"]
    assert handoff_state["current_diff"]["diff_hash"] == failed["candidate_diff_hash"]
    assert handoff_state["current_public_regression"] == failed
    assert actual["normal_calls"] == actual["tool_actions"] == 4
