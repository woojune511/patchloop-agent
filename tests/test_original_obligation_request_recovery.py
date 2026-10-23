"""Request correction, execution accounting and crash recovery using public local probes."""

from __future__ import annotations

import copy

import pytest
from test_dev_probe_cases import ExecutingProbe
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_original_obligation import restore, view
from test_probe_purpose import probe

from patchloop.dev import original_obligation as obligation
from patchloop.dev import reproduction, runner
from patchloop.errors import ActionConflict, ContractError
from patchloop.util import sha256_json


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("request recovery tests must not use the network")

    monkeypatch.setattr("socket.socket.connect", forbidden)


@pytest.fixture
def gateway(gateway_factory):
    initial, _, _ = gateway_factory()
    return restore(initial, backend=ExecutingProbe())


def bad_quote(gateway, action="bad-quote"):
    call = probe(gateway.public_task, action)
    call.arguments["purpose"]["requirement_quote"] = "This is not a literal public issue quote."
    return call


def test_quote_rejection_keeps_original_execution_allowance_for_corrected_request(gateway):
    rejected = gateway.execute(bad_quote(gateway))
    assert rejected.error_code == "CONTRACT_ERROR"
    assert rejected.output["probe_stage"] == "preflight_rejected"
    assert runner._batch_execution_abort([rejected]) == (None, None)
    rejected_state = view(gateway)
    assert rejected_state["request_errors"] == 1 and rejected_state["original_attempts"] == 0
    assert rejected_state["stage"] == "pending" and rejected_state["status"] == "unverified"
    assert gateway.probe_sandbox.calls == 0
    corrected = gateway.execute(probe(gateway.public_task, "corrected"))
    correction = corrected.output["request_validation"]["correction"]
    assert correction["status"] == "corrected"
    assert correction["changed_error_fields"] == ["/purpose/requirement_quote"]
    assert corrected.output["probe_stage"] == "execution_returned"
    assert corrected.output["reproduction"]["comparison"] == "mismatched"
    state = view(gateway)
    assert state["request_errors"] == 1 and state["original_attempts"] == 1
    assert state["investigation_actions"] == 2 and state["original_execution_results"] == 1
    assert state["stage"] == "acquired" and len(state["baseline_failure_case_ids"]) == 1
    assert gateway.probe_sandbox.calls == 1


def test_two_request_errors_release_without_execution_or_original_evidence(gateway):
    calls = [bad_quote(gateway, f"bad-{index}") for index in range(obligation.MAX_REQUEST_ERRORS)]
    calls[-1].turn_decision.basis = "I corrected the rejected request."
    for call in calls:
        result = gateway.execute(call)
        assert result.output["probe_stage"] == "preflight_rejected"
    assert result.output["request_validation"]["correction"]["status"] == "unchanged"
    state = view(gateway)
    assert state["stage"] == "released" and state["reason"] == "request_error_limit"
    assert state["acquisition_status"] == "request_blocked"
    assert state["status"] == "unverified" and state["baseline_failure_case_ids"] == []
    assert state["request_errors"] == 2 and state["original_attempts"] == 0
    assert state["investigation_actions"] == 2
    assert state["max_original_attempts"] == 2 and state["max_investigation_actions"] == 6
    before = gateway.journal.path.read_bytes()
    restored = restore(gateway)
    for call in calls:
        assert restored.execute(call).replayed
    assert view(restored) == state and restored.probe_sandbox.calls == 0
    assert gateway.journal.path.read_bytes() == before
    changed = copy.deepcopy(calls[0])
    changed.arguments["purpose"]["requirement_quote"] = "Changed request with reused action id."
    with pytest.raises(ActionConflict):
        restored.execute(changed)


def test_request_error_does_not_consume_either_executed_setup_attempt(gateway):
    gateway.execute(bad_quote(gateway))
    for index in range(obligation.MAX_ATTEMPTS):
        result = gateway.execute(probe(gateway.public_task, f"setup-{index}",
                                       source="raise ImportError('controlled missing setup')"))
        assert result.output["reproduction"]["comparison"] == "not_compared"
        assert runner._batch_execution_abort([result]) == (None, None)
    state = view(gateway)
    assert state["request_errors"] == 1 and state["original_attempts"] == 2
    assert state["original_execution_results"] == state["original_setup_failures"] == 2
    assert state["investigation_actions"] == 3 and state["stage"] == "released"
    assert state["reason"] == "original_attempt_limit"
    assert state["acquisition_status"] == "setup_blocked" and state["status"] == "unverified"
    assert gateway.probe_sandbox.calls == 2


@pytest.mark.parametrize("invalid", ["question", "source", "purpose"])
def test_request_validation_precedes_dispatch(gateway, invalid):
    call = probe(gateway.public_task)
    if invalid == "question":
        call.arguments["question"] = ""
    elif invalid == "source":
        call.arguments["python_source"] = ""
    else:
        call.arguments["purpose"] = {"kind": ["original_requirement"]}
    result = gateway.execute(call)
    assert result.status == "failed" and result.output["probe_stage"] == "preflight_rejected"
    assert view(gateway)["request_errors"] == 1 and view(gateway)["original_attempts"] == 0
    assert not any(e["event_type"] == "probe_execution_started" for e in gateway.journal.events())
    assert gateway.probe_sandbox.calls == 0


@pytest.mark.parametrize("rejected", [False, True])
def test_admitted_request_crash_does_not_count_execution_and_recovers(
    gateway, monkeypatch, rejected,
):
    call = bad_quote(gateway) if rejected else probe(gateway.public_task)
    _crash_journal_once(monkeypatch, event_type="action_started", when="after")
    with pytest.raises(_SimulatedCrash):
        gateway.execute(call)
    before = view(gateway)
    assert before["original_attempts"] == 0 and gateway.probe_sandbox.calls == 0
    assert before["request_errors"] == int(rejected)
    assert before["pending_original_requests"] == int(not rejected)
    restored = restore(gateway)
    result = restored.execute(call)
    assert result.output["probe_stage"] == (
        "preflight_rejected" if rejected else "execution_returned")
    assert view(restored)["original_attempts"] == int(not rejected)
    assert view(restored)["request_errors"] == int(rejected)
    assert restored.probe_sandbox.calls == int(not rejected)
    assert restored.execute(call).replayed


@pytest.mark.parametrize("event_type,when,executions", [
    ("probe_execution_started", "after", 0),
    ("probe_execution_finished", "before", 1),
])
def test_uncertain_dispatch_is_reserved_but_never_automatically_reexecuted(
    gateway, monkeypatch, event_type, when, executions,
):
    call = probe(gateway.public_task)
    _crash_journal_once(monkeypatch, event_type=event_type, when=when)
    with pytest.raises(_SimulatedCrash):
        gateway.execute(call)
    before = view(gateway)
    assert before["original_attempts"] == 1 and before["pending_original_dispatches"] == 1
    assert before["original_execution_results"] == 0 and before["request_errors"] == 0
    assert gateway.probe_sandbox.calls == executions
    restored = restore(gateway)
    result = restored.execute(call)
    assert result.error_code == "RECOVERY_ERROR"
    assert result.output["probe_stage"] == "dispatch_pending"
    assert runner._batch_execution_abort([result])[0].value == "TASK_FAILED"
    assert restored.probe_sandbox.calls == executions
    assert restored.execute(call).replayed
    after = view(restored)
    assert after["original_attempts"] == 1 and after["uncertain_original_dispatches"] == 1
    assert after["status"] == "unverified" and after["baseline_failure_case_ids"] == []


@pytest.mark.parametrize("error_type", [RuntimeError, ContractError])
def test_unreturned_backend_exception_aborts_on_first_call(gateway, error_type):
    class UncertainBackend(ExecutingProbe):
        def run_probe(self, *args, **kwargs):
            super().run_probe(*args, **kwargs)
            raise error_type("controlled error after execution without returned receipt")

    gateway.probe_sandbox = UncertainBackend()
    call = probe(gateway.public_task)
    result = gateway.execute(call)
    assert result.error_code == "RECOVERY_ERROR"
    assert result.output["probe_stage"] == "dispatch_pending"
    assert result.output["backend_error_type"] == error_type.__name__
    assert runner._batch_execution_abort([result])[0].value == "TASK_FAILED"
    state = view(gateway)
    assert state["original_attempts"] == state["uncertain_original_dispatches"] == 1
    assert state["original_execution_results"] == state["request_errors"] == 0
    assert state["status"] == "unverified" and state["baseline_failure_case_ids"] == []
    restored = restore(gateway)
    assert restored.execute(call).replayed and restored.probe_sandbox.calls == 1


@pytest.mark.parametrize("event_type,when", [
    ("probe_execution_finished", "after"), ("action_finished", "before"),
])
def test_durable_backend_receipt_recovers_without_duplicate_execution(gateway, monkeypatch,
                                                                    event_type, when):
    call = probe(gateway.public_task)
    _crash_journal_once(monkeypatch, event_type=event_type, when=when)
    with pytest.raises(_SimulatedCrash):
        gateway.execute(call)
    before = view(gateway)
    assert before["original_attempts"] == before["original_execution_results"] == 1
    assert before["pending_original_results"] == 1 and before["stage"] == "pending"
    assert before["baseline_failure_case_ids"] == []
    restored = restore(gateway)
    result = restored.execute(call)
    assert result.output["reproduction"]["comparison"] == "mismatched"
    assert restored.probe_sandbox.calls == 1 and restored.execute(call).replayed
    assert view(restored)["original_attempts"] == 1 and view(restored)["stage"] == "acquired"
    for kind in ("probe_execution_started", "probe_execution_finished", "action_finished"):
        assert sum(e["event_type"] == kind for e in restored.journal.events()) == 1


def test_legacy_root_and_pending_request_remain_immutable_and_uncertain(gateway_factory):
    initial, journal, _ = gateway_factory()
    task = initial.public_task
    root = {**obligation.definition(task), "acquisition_policy": obligation.ACQUISITION,
            "max_original_attempts": 2, "max_investigation_actions": 6}
    journal.append("original_obligation_registered", root)
    before = journal.path.read_bytes()
    gateway = restore(initial, backend=ExecutingProbe())
    assert journal.path.read_bytes() == before
    events = journal.events()
    events.append({"event_type": "action_started", "payload": {
        "action_id": "legacy-pending", "tool": "run_probe",
        "arguments": probe(task).arguments, "baseline_diff_hash": obligation.EMPTY_DIFF,
    }})
    state = obligation.review(events, task, gateway.completion_verification(
        diff_hash=gateway.current_diff_hash), acquisition=obligation.ACQUISITION)
    assert state["original_attempts"] == 0 and state["original_attempts_reserved"] == 1
    assert state["legacy_uncertain_original_attempts"] == 1 and state["stage"] == "pending"
    assert state["request_errors"] == 0 and state["status"] == "unverified"
    assert journal.path.read_bytes() == before


def test_legacy_pending_original_cannot_be_dispatched_without_execution_stage(gateway):
    call = probe(gateway.public_task, "legacy-original")
    selected, channel = reproduction.selection(call.arguments)
    binding = reproduction.bind(
        selected, gateway.public_task, call.arguments["python_source"], call.action_id,
        events=gateway.journal.events(), observation_channel=channel,
    )
    input_hash = sha256_json({"tool": call.name, "arguments": call.arguments,
                              "turn_decision": call.turn_decision.model_dump(mode="json")})
    gateway.journal.append("action_started", {
        "action_id": call.action_id, "input_hash": input_hash, "tool": call.name,
        "arguments": call.arguments, "baseline_diff_hash": obligation.EMPTY_DIFF,
        "reproduction_binding": binding,
    })
    result = restore(gateway).execute(call)
    assert result.error_code == "RECOVERY_ERROR"
    assert result.output["probe_stage"] == "dispatch_pending"
    assert runner._batch_execution_abort([result])[0].value == "TASK_FAILED"
    assert gateway.probe_sandbox.calls == 0
    assert view(gateway)["original_attempts"] == 0
    assert view(gateway)["legacy_uncertain_original_attempts"] == 1
    assert view(gateway)["original_attempts_reserved"] == 1
