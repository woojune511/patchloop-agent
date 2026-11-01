"""Bounded correction uses settled pre-target evidence, never arbitrary TypeErrors."""
from __future__ import annotations

import copy

import pytest

from patchloop.dev import helper_recovery as recovery
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes

DIFF = sha256_bytes(b"")
SOURCE = 'observed_target()(["path"])\n'
PURPOSE = {
    "kind": "original_requirement", "entrypoint": "public.run", "input_conditions": "fixture",
    "environment_conditions": "CLI argv", "expected_json": '{"failed":false}',
    "reported_failure_json": '{"failed":true}', "diagnostic_rules": None,
    "corrects_action_id": None,
}


def obligation(**changes):
    return {
        "stage": "pending", "reason": "awaiting_original", "original_attempts_reserved": 1,
        "max_original_attempts": 2, "request_errors": 0, "max_request_errors": 2,
        "pending_original_requests": 0, "pending_original_dispatches": 0,
        "pending_original_results": 0, "uncertain_original_dispatches": 0, **changes,
    }


def execution(action="root", *, entered=False, source=SOURCE, link=None):
    arguments = {"question": "Does the original caller fail?", "python_source": source,
                 "purpose": copy.deepcopy(PURPOSE), "call_path": None, "replay_action_id": None}
    binding = {
        "root_action_id": action, "case_id": "case-" + action,
        "program_hash": sha256_bytes(source.encode()),
        "definition": {"entrypoint": "public.run",
                       "observation_channel": recovery.ARGUMENT_CHANNEL},
    }
    start = {"action_id": action, "tool": "run_probe", "input_hash": "input-" + action,
             "baseline_diff_hash": DIFF, "arguments": arguments,
             "probe_request": {"status": "accepted"}, "reproduction_binding": binding}
    if link:
        start["helper_recovery_link"] = link
    call = {
        "entrypoint": "public.run", "resolved_entrypoint": "public.run",
        "arguments": {"args": [] if entered else [["path"]], "kwargs": {}},
        "argv": ["public", "path"], "cwd": "/tmp/case", "sys_path": [], "start_cwd": "/tmp",
        "inputs": [], "environment": {}, "outcome": "returned" if entered else "incomplete",
        "call_id": "call-1", "bound_parameters": {} if entered else None, "exception_policy": [],
        "capture": {"scope": "python-streams", "status": "complete" if entered else "incomplete",
                    "stdout": "" if not entered else "PUBLIC_FAILURE", "stderr": ""},
        "exception": None if entered else {"type": "builtins.TypeError",
                                            "message": "too many positional arguments"},
        "exit_code": None, "target_started": entered, "signature": "()",
        "binding_error": not entered,
    }
    identity = {"action_id": action, "input_hash": start["input_hash"],
                "execution_source_hash": "execution-" + action, "baseline_diff_hash": DIFF}
    raw = {"status": "passed" if entered else "failed", "exit_code": 0 if entered else 1,
           "source_hash": identity["execution_source_hash"], "timed_out": False,
           "truncated": False, "cleanup_failed": False, "deadline_exhausted": False,
           "execution_policy": {"cleanup_status": "confirmed"}}
    output = {**copy.deepcopy(raw), "source_hash": binding["program_hash"],
              "execution_source_hash": identity["execution_source_hash"],
              "diff_hash": DIFF, "probe_stage": "execution_returned",
              "reproduction": {"binding": copy.deepcopy(binding), "call_observation": {
                  "binding_method": recovery.ARGUMENT_CHANNEL, "calls": [call],
                  "incomplete": not entered}}}
    result = {"action_id": action, "input_hash": start["input_hash"], "tool": "run_probe",
              "status": "succeeded", "workspace_diff_hash": DIFF, "output": output}
    return [
        {"event_type": "action_started", "payload": start},
        {"event_type": "probe_execution_started", "payload": identity},
        {"event_type": "probe_execution_finished", "payload": {**identity, "output": raw}},
        {"event_type": "action_finished", "payload": {"result": result}},
    ]


def test_original_binding_ticket_retains_exact_purpose_and_settles_only_on_entry():
    events = execution()
    state = recovery.review(events, DIFF)
    assert state["policy"] == recovery.ARGUMENT_POLICY and state["status"] == "pending"
    assert state["purpose"] == PURPOSE and state["python_source"] == SOURCE
    assert state["error"]["calls"][0]["signature"] == "()"
    corrected = {**events[0]["payload"]["arguments"], "python_source": "observed_target()()\n"}
    link = recovery.validate(state, "run_probe", corrected, original_obligation=obligation())
    completed = events + execution("correction", entered=True, source=corrected["python_source"],
                                   link=link)
    final = recovery.review(completed, DIFF)
    assert final["status"] == "execution_returned" and not final["blocked"]
    assert final["behavior_verdict"] == "not_assessed" and final["remaining_attempts"] == 0
    assert recovery.review(completed + execution("another-failure"), DIFF) == final


@pytest.mark.parametrize("fault", [
    "no_marker", "unknown_signature", "target_entered", "mixed_calls", "legacy", "input",
    "binding", "diff", "no_dispatch", "no_return", "return_identity", "source_identity",
    "timed_out", "truncated", "cleanup", "negative_exit", "target_exception", "after_mutation",
])
def test_uncertain_or_entered_or_unbound_failures_cannot_create_ticket(fault):
    events = execution()
    start, result = events[0]["payload"], events[-1]["payload"]["result"]
    output = result["output"]
    trace = output["reproduction"]["call_observation"]
    call = trace["calls"][0]
    if fault == "no_marker":
        call["binding_error"] = False
    elif fault == "unknown_signature":
        call["signature"] = None
    elif fault in {"target_entered", "target_exception"}:
        call.update(target_started=True, binding_error=False, outcome="raised")
        call["capture"]["status"] = "complete"
    elif fault == "mixed_calls":
        other = copy.deepcopy(call)
        other.update(call_id="call-2", target_started=True, binding_error=False, outcome="returned",
                     bound_parameters={}, exception=None)
        other["capture"]["status"] = "complete"
        trace["calls"].append(other)
    elif fault == "legacy":
        start["reproduction_binding"]["definition"]["observation_channel"] = (
            "invoke-declared-call-v8")
    elif fault == "input":
        result["input_hash"] = "other"
    elif fault == "binding":
        output["reproduction"]["binding"]["case_id"] = "other"
    elif fault == "diff":
        result["workspace_diff_hash"] = "different"
    elif fault == "no_dispatch":
        events.pop(1)
    elif fault == "no_return":
        events.pop(2)
    elif fault == "return_identity":
        events[2]["payload"]["input_hash"] = "other"
    elif fault == "source_identity":
        events[2]["payload"]["output"]["source_hash"] = "other"
    elif fault in {"timed_out", "truncated"}:
        output[fault] = True
    elif fault == "cleanup":
        output["execution_policy"]["cleanup_status"] = "unknown"
    elif fault == "negative_exit":
        output["exit_code"] = -1
    else:
        events.insert(0, {"event_type": "action_finished", "payload": {"result": {
            "action_id": "edit", "tool": "replace_text", "status": "succeeded"}}})
    assert recovery.review(events, DIFF)["status"] == "not_needed"


@pytest.mark.parametrize("change", ["same_source", "question", "purpose", "path", "replay", "read"])
def test_correction_preserves_question_and_obligation_and_consumes_rejections(change):
    events = execution()
    state = recovery.review(events, DIFF)
    arguments = {**copy.deepcopy(events[0]["payload"]["arguments"]),
                 "python_source": SOURCE + "# fix"}
    tool = "run_probe"
    if change == "same_source":
        arguments["python_source"] = SOURCE
    elif change == "question":
        arguments["question"] += " other"
    elif change == "purpose":
        arguments["purpose"]["expected_json"] = "{}"
    elif change == "path":
        arguments["call_path"] = {"changed": True}
    elif change == "replay":
        arguments["replay_action_id"] = "root"
    else:
        tool = "read_file"
    with pytest.raises(ContractError, match="same question and purpose"):
        recovery.validate(state, tool, arguments, original_obligation=obligation())
    rejected = {"action_id": "rejected", "tool": tool, "arguments": arguments,
                "helper_recovery_link": recovery.link(state)}
    events.append({"event_type": "action_started", "payload": rejected})
    final = recovery.review(events, DIFF)
    assert final["status"] == "verification_incomplete" and final["remaining_attempts"] == 0
    assert recovery.validate(final, "stop_task", {}) is None


def test_repeated_binding_failure_and_changed_diff_do_not_renew_ticket():
    events = execution()
    state = recovery.review(events, DIFF)
    repeated = events + execution("retry", source=SOURCE + "# changed", link=recovery.link(state))
    final = recovery.review(repeated, DIFF)
    assert final["status"] == "verification_incomplete" and final["remaining_attempts"] == 0
    assert recovery.review(repeated + execution("third"), DIFF)["root_action_id"] == "root"
    assert recovery.review(events, "changed")["status"] == "verification_incomplete"


def test_partial_corrected_execution_does_not_hide_a_later_binding_failure():
    events = execution()
    state = recovery.review(events, DIFF)
    corrected = execution("retry", entered=True, source=SOURCE + "# changed",
                          link=recovery.link(state))
    trace = corrected[-1]["payload"]["result"]["output"]["reproduction"]["call_observation"]
    failed = copy.deepcopy(events[-1]["payload"]["result"]["output"][
        "reproduction"]["call_observation"]["calls"][0])
    failed["call_id"] = "call-2"
    trace["calls"].append(failed)
    trace["incomplete"] = True
    final = recovery.review(events + corrected, DIFF)
    assert final["status"] == "verification_incomplete" and final["remaining_attempts"] == 0


@pytest.mark.parametrize("changes", [
    {"stage": "released"}, {"original_attempts_reserved": 2}, {"request_errors": 2},
    {"pending_original_results": 1}, {"uncertain_original_dispatches": 1},
    {"reason": "completion_budget"},
])
def test_correction_cannot_bypass_acquisition_limits(changes):
    events = execution()
    state = recovery.review(events, DIFF)
    assert not recovery.correction_available(state, obligation(**changes))
    arguments = {**events[0]["payload"]["arguments"], "python_source": SOURCE + "# correction"}
    with pytest.raises(ContractError):
        recovery.validate(state, "run_probe", arguments, original_obligation=obligation(**changes))
    assert recovery.correction_available(state, obligation(stage="disabled"))
