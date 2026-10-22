"""Bounded acquisition and truthful delivery controls; no model-quality claim."""

from __future__ import annotations

import json

import pytest
from test_dev_probe_cases import ExecutingProbe
from test_dev_probes import context
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_dev_tools import mutation_call, read_calls
from test_finish_reproduction import checks, finish, mutate, request, results_for
from test_probe_purpose import probe

from diagnostics.finish_reproduction_experiment import original_case
from patchloop.dev import original_obligation as obligation
from patchloop.dev import runner
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import RecoveryError


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Original obligation controls must not use the network")

    monkeypatch.setattr("socket.socket.connect", forbidden)


def restore(gateway, *, backend=None, policy=obligation.ACQUISITION, task=None):
    return DevToolGateway(
        workspace=gateway.workspace, public_task=task or gateway.public_task,
        sandbox=gateway.sandbox, journal=gateway.journal, limits=gateway.limits,
        probe_sandbox=backend if backend is not None else gateway.probe_sandbox,
        reproduction_acquisition=policy,
    )


@pytest.fixture
def acquired_gateway(gateway_factory):
    base, _, _ = gateway_factory()
    return restore(base, backend=ExecutingProbe())


def view(gateway):
    verification = gateway.completion_verification(diff_hash=gateway.current_diff_hash)
    return verification["original_obligation"]


def read(gateway, number):
    call = read_calls()[1].model_copy(update={"action_id": f"investigate-{number}"})
    return gateway.execute(call)


def test_helper_notes_plan_and_rejected_edits_do_not_discharge_root(
    acquired_gateway, smoke_package,
):
    gateway = acquired_gateway
    root = view(gateway)
    assert root["stage"] == "pending" and root["status"] == "unverified"
    assert read(gateway, 1).status == "succeeded"
    rejected = gateway.execute(mutation_call(gateway, action_id="too-early"))
    assert rejected.status == "failed" and gateway.accepted_mutations == 0
    assert view(gateway)["investigation_actions"] == 1
    helper = probe(gateway.public_task, "helper", source="print('helper passed')")
    helper.arguments["purpose"] = {"kind": "helper"}
    assert gateway.execute(helper).output["status"] == "passed"
    assert gateway.execute(helper).replayed
    assert view(gateway)["investigation_actions"] == 2
    assert view(gateway)["original_attempts"] == 0
    gateway.journal.append("diagnostic_model_interpretation", {
        "plan": "Only helper tests remain.", "notes": "Everything is complete.",
    })
    compact = compact_model_state(context(gateway, smoke_package), [])
    delivered = reconstruct_state(assemble_model_input(
        system_prompt="fixed", state=compact, history=[], context_policy="segmented-v1",
    ))
    assert delivered["reproduction_review"]["completion"]["original_obligation"] == view(gateway)
    before = gateway.journal.path.read_bytes()
    gateway = restore(gateway)
    assert gateway.journal.path.read_bytes() == before
    assert view(gateway)["obligation_id"] == root["obligation_id"]
    for number in range(3, obligation.MAX_ACTIONS + 1):
        read(gateway, number)
    limited = view(gateway)
    assert limited["stage"] == "released" and limited["reason"] == "investigation_action_limit"
    assert limited["status"] == "unverified"
    mutate(gateway)
    checks(gateway)
    result, _ = finish(gateway)
    assert result.output["delivery_state"] == "unverified_delivery"
    assert result.output["original_verification"]["status"] == "unverified"


@pytest.mark.parametrize("correct", [True, False])
def test_acquired_failure_still_requires_current_replay(acquired_gateway, correct):
    gateway = acquired_gateway
    baseline = gateway.execute(probe(gateway.public_task))
    assert baseline.output["reproduction"]["comparison"] == "mismatched"
    assert view(gateway)["stage"] == "acquired"
    mutate(gateway, correct=correct)
    checks(gateway)
    result, _ = finish(gateway)
    if correct:
        assert result.output["delivery_state"] == "cases_verified_delivery"
        assert result.output["original_verification"]["status"] == "verified"
    else:
        assert result.status == "failed"
        assert view(gateway)["status"] == "refuted"


def test_two_matched_baselines_release_without_original_failure_credit(acquired_gateway):
    gateway = acquired_gateway
    for index in range(2):
        call = original_case(gateway.public_task, normal=True).model_copy(
            update={"action_id": f"normal-{index}"})
        assert gateway.execute(call).output["reproduction"]["comparison"] == "matched"
    state = view(gateway)
    assert state["stage"] == "released" and state["original_attempts"] == 2
    assert state["acquisition_status"] == "not_reproduced"
    assert state["baseline_failure_case_ids"] == []
    mutate(gateway)
    checks(gateway)
    result, _ = finish(gateway)
    assert result.output["delivery_state"] == "unverified_delivery"
    assert result.output["original_verification"]["status"] == "unverified"


def test_two_incomplete_original_attempts_release_as_setup_blocked(acquired_gateway):
    gateway = acquired_gateway
    for index in range(2):
        result = gateway.execute(probe(gateway.public_task, f"unavailable-{index}",
                                       source="raise ImportError('controlled missing setup')"))
        assert result.output["reproduction"]["comparison"] == "not_compared"
    state = view(gateway)
    assert state["stage"] == "released" and state["status"] == "unverified"
    assert state["acquisition_status"] == "setup_blocked"
    mutate(gateway)
    checks(gateway)
    result, _ = finish(gateway)
    assert result.output["delivery_state"] == "unverified_delivery"


def test_disabled_backend_has_persistent_projection_without_root_write(gateway_factory):
    gateway, journal, _ = gateway_factory()
    before = journal.path.read_bytes() if journal.path.exists() else b""
    result = view(gateway)
    assert result["stage"] == "disabled" and result["status"] == "unverified"
    assert result["reason"] == "probe_unavailable"
    assert (journal.path.read_bytes() if journal.path.exists() else b"") == before


def test_root_crash_restore_and_public_task_identity(gateway_factory, monkeypatch):
    gateway, journal, _ = gateway_factory()
    backend = ExecutingProbe()
    _crash_journal_once(monkeypatch, event_type="original_obligation_registered", when="after")
    with pytest.raises(_SimulatedCrash):
        restore(gateway, backend=backend)
    restored = restore(gateway, backend=backend)
    assert view(restored)["stage"] == "pending"
    assert sum(e["event_type"] == "original_obligation_registered" for e in journal.events()) == 1
    changed = gateway.public_task.model_copy(update={"task_id": "different-public-task"})
    with pytest.raises(RecoveryError, match="obligation identity"):
        restore(gateway, backend=backend, task=changed)


def test_durable_original_result_is_not_executed_or_counted_again(acquired_gateway, monkeypatch):
    gateway = acquired_gateway
    request = probe(gateway.public_task)
    _crash_journal_once(monkeypatch, event_type="action_finished", when="after",
                        predicate=lambda p: p.get("result", {}).get("action_id") == "original")
    with pytest.raises(_SimulatedCrash):
        gateway.execute(request)
    restored = restore(gateway)
    assert restored.execute(request).replayed
    assert restored.probe_sandbox.calls == 1
    assert view(restored)["original_attempts"] == 1
    assert view(restored)["stage"] == "acquired"


def test_release_crash_remains_unverified_and_does_not_reopen(acquired_gateway, monkeypatch):
    gateway = acquired_gateway
    _crash_journal_once(monkeypatch, event_type="original_acquisition_released", when="after")
    with pytest.raises(_SimulatedCrash):
        gateway.release_original_acquisition("completion_budget")
    restored = restore(gateway)
    restored.release_original_acquisition("completion_budget")
    state = view(restored)
    assert state["stage"] == "released" and state["reason"] == "completion_budget"
    assert state["status"] == "unverified"
    assert sum(e["event_type"] == "original_acquisition_released"
               for e in gateway.journal.events()) == 1


def test_second_admitted_original_is_pending_until_its_result_is_durable(acquired_gateway):
    gateway = acquired_gateway
    completed = gateway.execute(probe(gateway.public_task, "first-unavailable",
                                      source="raise ImportError('controlled missing setup')"))
    assert completed.output["reproduction"]["comparison"] == "not_compared"
    events = gateway.journal.events()
    # Pure interrupted-admission projection: no second sandbox execution occurs.
    events.append({"event_type": "action_started", "payload": {
        "action_id": "second-pending", "tool": "run_probe",
        "arguments": {"purpose": {"kind": "original_requirement"}},
        "baseline_diff_hash": obligation.EMPTY_DIFF,
        "probe_request": {"policy": obligation.PROBE_STAGES, "status": "accepted",
                          "kind": "original_requirement"},
    }})
    completion = gateway.completion_verification(diff_hash=gateway.current_diff_hash)
    interrupted = obligation.review(events, gateway.public_task, completion,
                                    acquisition=obligation.ACQUISITION)
    assert interrupted["original_attempts"] == 1
    assert interrupted["pending_original_requests"] == 1
    assert interrupted["original_attempts_reserved"] == 1
    assert interrupted["stage"] == "pending" and interrupted["reason"] == "attempt_pending"


def test_full_loop_releases_acquisition_when_no_probe_fits_protected_budget(tmp_path, monkeypatch):
    backend = ExecutingProbe()

    class SingleReadMock(MockDevAdapter):
        def next_turn(self, context, tools):
            turn = super().next_turn(context, tools)
            if len(turn.tool_calls) > 1:
                turn.tool_calls = [call for call in turn.tool_calls if call.name == "read_file"]
            return turn

    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    monkeypatch.setattr(runner, "MockDevAdapter", SingleReadMock)
    req = request(tmp_path)
    req = req.model_copy(update={
        "reproduction_acquisition": obligation.ACQUISITION,
        "limits": req.limits.model_copy(update={"max_model_calls": 6}),
    })
    result = runner.run_dev(req)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert backend.calls == 0
    journal = DevJournal(tmp_path, result["run_id"])
    releases = [e for e in journal.events() if e["event_type"] == "original_acquisition_released"]
    assert len(releases) == 1 and releases[0]["payload"]["reason"] == "completion_budget"
    submitted = results_for(journal, "finish_task")[-1]
    assert submitted["output"]["delivery_state"] == "unverified_delivery"
    assert submitted["output"]["original_verification"]["status"] == "unverified"
    # An isolated mock acceptance must not overwrite the public verification label.
    encoded = json.dumps(result)
    assert "unverified_delivery" in encoded
