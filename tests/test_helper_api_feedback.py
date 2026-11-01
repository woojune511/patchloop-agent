"""Concrete helper API feedback reaches counted input without resetting resources."""

from __future__ import annotations

import copy
import json
from decimal import Decimal

import httpx
import pytest
from test_dev_probe_cases import ExecutingProbe
from test_dev_runner import _crash_journal_once, _enveloped_run_id, _SimulatedCrash
from test_dev_segments import configured, records
from test_original_obligation import restore, view
from test_probe_purpose import SOURCE, probe

from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn, RequestedTool
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.cost import COMPLETION_RECOVERY_POLICY, usd_to_nanos
from patchloop.errors import ActionConflict
from patchloop.sandbox import probe_setup
from patchloop.util import sha256_bytes

BAD_SETUP = "check_setup('mode')\n" + SOURCE
BAD_PATHS = "paths = [str(i) for i in range(7)]\nobserved_target(input_paths=paths)\n"
CORRECTED = "check_setup('mode', 'offline', 'offline')\n" + SOURCE


class SetupProbe(ExecutingProbe):
    """Inject the real setup API around the existing trusted local smoke fixture."""

    def run_probe(self, workspace, question, python_source, **kwargs):
        prefix = (
            "import runpy as _test_runpy\n"
            f"_test_setup = _test_runpy.run_path({probe_setup.__file__!r})"
            "['SetupChecks']({'request_hash': 'local-test'})\n"
            "check_setup = _test_setup.invoke\n"
        )
        receipt = super().run_probe(workspace, question, prefix + python_source, **kwargs)
        # The local-only injected setup wrapper is not model-authored probe source.
        return {**receipt, "source_hash": sha256_bytes(python_source.encode())}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("helper feedback tests must not use a network provider or Docker")

    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def delivered_result(items, action_id):
    for item in items:
        if item.get("type") == "function_call_output" and item.get("call_id") == action_id:
            return json.loads(item["output"])
    state = reconstruct_state(items, context_policy="segmented-v1")
    return next(row for row in state["latest_tool_results"] if row["action_id"] == action_id)


@pytest.mark.parametrize("error_kind", ["static_setup", "dynamic_paths"])
def test_next_counted_input_names_api_error_and_corrected_call_keeps_accounting(
    tmp_path, monkeypatch, smoke_package, error_kind,
):
    backend = SetupProbe()
    source = BAD_SETUP if error_kind == "static_setup" else BAD_PATHS

    class CorrectThenStop:
        turns = 0

        def next_turn(self, context, tools):
            self.turns += 1
            if self.turns == 1:
                return DevModelTurn(tool_calls=[probe(smoke_package.public, "bad", source=source)])
            if self.turns == 2:
                result = delivered_result(inputs[-1], "bad")
                output = result["output"]
                state = json.loads(context)
                original = state["reproduction_review"]["completion"]["original_obligation"]
                assert original["stage"] == "pending" and original["status"] == "unverified"
                assert original["baseline_failure_case_ids"] == []
                if error_kind == "static_setup":
                    error = output["helper_program_error"]["api_error"]
                    assert output["probe_stage"] == "preflight_rejected"
                    assert error["api"] == "check_setup"
                    assert error["missing_parameters"] == ["actual", "expected"]
                    assert original["original_attempts"] == 0
                    assert original["request_errors"] == 1
                    assert backend.calls == 0
                else:
                    observed = output["reproduction"]
                    assert observed["call_observation"]["request_phase"] == {
                        "settings_rejected": True, "target_entries": 0,
                    }
                    assert not observed["call_observation"]["calls"]
                    assert observed["observed_json"] is None
                    assert observed["comparison"] == "not_compared"
                    assert "observed_target.input_paths: received 7 items; maximum 4" in (
                        output["stderr"])
                    assert original["original_attempts"] == 1
                    assert original["request_errors"] == 0
                    assert backend.calls == 1
                return DevModelTurn(tool_calls=[
                    probe(smoke_package.public, "corrected", source=CORRECTED)])
            assert self.turns == 3
            result = delivered_result(inputs[-1], "corrected")
            assert result["output"]["reproduction"]["declared_failure_comparison"] == "matched"
            assert result["output"]["reproduction"]["call_observation"]["calls"]
            return DevModelTurn(tool_calls=[RequestedTool(
                name="stop_task", action_id="stop", arguments={
                    "reason_code": "insufficient_public_evidence",
                    "summary": "End the local API test; reproducing a failure is not a repair.",
                }, turn_decision={"mode": "stop", "basis": "Keep the unmet repair explicit."},
            )])

    request, inputs, counted, states = configured(
        monkeypatch, tmp_path, script=CorrectThenStop())
    request = request.model_copy(update={
        "enable_probes": True, "reproduction_acquisition": "bounded-v1",
        "completion_cost_policy": COMPLETION_RECOVERY_POLICY, "max_cost_usd": Decimal("1.20"),
    })
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    _crash_journal_once(monkeypatch, event_type="action_finished", when="after",
                        predicate=lambda payload: payload["action_id"] == "bad")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)
    resumed = request.model_copy(update={"resume_run_id": run_id})
    result = runner.run_dev(resumed)["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED", result
    assert result["accepted_mutations"] == 0 and result["evaluator"] is None
    assert result["call_counts"] == {"input_count": 3, "model": 3, "tool": 3}
    assert inputs == counted and len(inputs) == 3
    assert backend.calls == (1 if error_kind == "static_setup" else 2)
    # The failed request still consumes its response/action; crash recovery refunds neither.
    assert states[1]["remaining_budget"]["model_calls"] == (
        states[0]["remaining_budget"]["model_calls"] - 1)
    assert states[1]["remaining_budget"]["tool_actions"] == (
        states[0]["remaining_budget"]["tool_actions"] - 1)
    journal, _ = records(request)
    events = journal.events()
    starts = {e["payload"]["action_id"]: e["payload"] for e in events
              if e["event_type"] == "action_started"}
    finished = [e["payload"] for e in events if e["event_type"] == "action_finished"]
    assert len(starts) == len(finished) == 3
    assert all(row["input_hash"] == starts[row["action_id"]]["input_hash"] for row in finished)
    spent = sum(e["payload"]["cost_nanos"] for e in events
                if e["event_type"] == "provider_call_finished")
    assert 0 < result["cost_nanos"] == spent <= usd_to_nanos(request.max_cost_usd)
    correction = next(row["result"] for row in finished if row["action_id"] == "corrected")
    expected = "corrected" if error_kind == "static_setup" else "not_attempted"
    assert correction["output"]["request_validation"]["correction"]["status"] == expected
    assert not any(e["event_type"] in {"submission_recorded", "evaluator_finished"} for e in events)
    before = journal.path.read_bytes()
    assert runner.run_dev(resumed)["runs"][0] == result
    assert journal.path.read_bytes() == before and len(inputs) == 3


def test_corrected_original_receipt_recovery_preserves_input_identity_and_obligation(
    gateway_factory, monkeypatch,
):
    initial, _, _ = gateway_factory()
    gateway = restore(initial, backend=SetupProbe())
    bad = probe(gateway.public_task, "bad", source=BAD_SETUP)
    rejected = gateway.execute(bad)
    assert rejected.status == "failed" and gateway.probe_sandbox.calls == 0
    assert view(gateway)["original_attempts"] == 0
    before = gateway.journal.path.read_bytes()
    assert gateway.execute(bad).replayed and gateway.journal.path.read_bytes() == before
    changed = copy.deepcopy(bad)
    changed.arguments["python_source"] = CORRECTED
    with pytest.raises(ActionConflict):
        gateway.execute(changed)
    corrected = probe(gateway.public_task, "corrected", source=CORRECTED)
    _crash_journal_once(monkeypatch, event_type="probe_execution_finished", when="after")
    with pytest.raises(_SimulatedCrash):
        gateway.execute(corrected)
    assert gateway.probe_sandbox.calls == 1
    recovered = restore(gateway)
    result = recovered.execute(corrected)
    assert result.status == "succeeded" and recovered.probe_sandbox.calls == 1
    assert result.output["reproduction"]["declared_failure_comparison"] == "matched"
    obligation = view(recovered)
    assert obligation["stage"] == "acquired" and obligation["status"] != "verified"
    assert obligation["original_attempts"] == 1 and obligation["request_errors"] == 1
    before = recovered.journal.path.read_bytes()
    replay = recovered.execute(corrected)
    assert replay.replayed and replay.input_hash == result.input_hash
    assert recovered.journal.path.read_bytes() == before and recovered.probe_sandbox.calls == 1
