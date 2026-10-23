"""Fast request controls; one real local gateway chain covers the integration seam."""

from __future__ import annotations

import copy

import pytest
from test_dev_probe_cases import ExecutingProbe
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_original_obligation import restore, view
from test_probe_purpose import SOURCE, probe

from patchloop.dev import probe_invocation, probe_requests, reproduction
from patchloop.errors import ActionConflict, ContractError, RecoveryError
from patchloop.util import sha256_json


def validate(call, task):
    try:
        raw, channel = reproduction.selection(call.arguments)
        reproduction.bind(raw, task, call.arguments["python_source"], call.action_id,
                          observation_channel=channel)
    except ContractError as exc:
        return exc
    return None


def receipt(call, task, events=()):
    return probe_requests.review(call.arguments, validate(call, task), events,
                                 public_task_hash=sha256_json(task.model_dump(mode="json")),
                                 kind="original_requirement")


def rejected_event(call, validation):
    return {"event_type": "action_started", "payload": {
        "tool": "run_probe", "action_id": call.action_id,
        "arguments": copy.deepcopy(call.arguments),
        "probe_request": {"kind": "original_requirement", "status": "rejected",
                          "validation": validation},
    }}


def test_fresh_schema_and_binding_use_the_whole_host_task(smoke_package):
    task = smoke_package.public
    call = probe(task)
    schema = reproduction.purpose_schema()["anyOf"][1]
    assert "requirement_quote" not in schema["properties"]
    assert "requirement_quote" not in schema["required"]
    raw, channel = reproduction.selection(call.arguments)
    bound = reproduction.bind(raw, task, SOURCE, "first", observation_channel=channel)
    definition = bound["definition"]
    assert "requirement_quote" not in definition
    assert definition["public_task_hash"] == sha256_json(task.model_dump(mode="json"))
    assert definition["requirement_source"] == {
        "field": "issue", "issue_hash": sha256_json(task.issue.model_dump(mode="json")),
    }
    altered = task.model_copy(update={"issue": task.issue.model_copy(update={
        "description": task.issue.description + "\nAdditional public condition.",
    })})
    assert reproduction.bind(raw, altered, SOURCE, "first", observation_channel=channel)[
        "case_id"] != bound["case_id"]


@pytest.mark.parametrize("field,value", [
    ("requirement_quote", "Fails with invented wording"),
    ("entrypoint", "not qualified"), ("input_conditions", ""),
    ("environment_conditions", ""), ("reported_failure_json", "NaN"),
    ("expected_json", '{"x":1,"x":2}'),
])
def test_rejection_names_the_actual_field(smoke_package, field, value):
    call = probe(smoke_package.public)
    call.arguments["purpose"][field] = value
    result = receipt(call, smoke_package.public)
    assert {row["path"] for row in result["invalid_fields"]} == {f"/purpose/{field}"}
    assert result["correction"]["status"] == "not_attempted"


def test_correction_requires_argument_changes_and_full_validation(smoke_package):
    task = smoke_package.public
    bad = probe(task, "bad")
    bad.arguments["purpose"]["entrypoint"] = "invalid"
    first = receipt(bad, task)
    events = [rejected_event(bad, first)]
    retry = copy.deepcopy(bad)
    retry.action_id = "different-action"
    retry.turn_decision.basis = "I corrected the field."
    repeated = receipt(retry, task, events)
    assert repeated["arguments_hash"] == first["arguments_hash"]
    assert repeated["correction"] == {
        "status": "unchanged", "previous_action_id": "bad", "changed_error_fields": [],
    }
    retry.arguments["question"] += " Another explanation."
    assert receipt(retry, task, events)["correction"]["status"] == "invalid"
    retry.arguments["purpose"]["entrypoint"] = "still invalid"
    changed = receipt(retry, task, events)["correction"]
    assert changed["status"] == "invalid"
    assert changed["changed_error_fields"] == ["/purpose/entrypoint"]
    fixed = receipt(probe(task, "fixed"), task, events)
    assert fixed["invalid_fields"] == [] and fixed["correction"]["status"] == "corrected"
    # Changing a named field is insufficient when another field is still invalid.
    retry.arguments["purpose"]["entrypoint"] = probe(task).arguments["purpose"]["entrypoint"]
    retry.arguments["purpose"]["expected_json"] = "NaN"
    assert receipt(retry, task, events)["correction"]["status"] == "invalid"


def test_legacy_bindings_keep_their_definition_and_new_requests_reject_quotes(smoke_package):
    task = smoke_package.public
    call = probe(task)
    call.arguments["purpose"]["requirement_quote"] = task.issue.title
    assert receipt(call, task)["invalid_fields"][0]["path"] == "/purpose/requirement_quote"
    raw, channel = reproduction.selection(call.arguments, allow_legacy=True)
    bound = reproduction.bind(raw, task, SOURCE, "legacy", observation_channel=channel)
    assert "requirement_source" not in bound["definition"]
    assert bound["definition"]["requirement_quote"] == task.issue.title
    assert bound["definition"]["observation_channel"] == probe_invocation.CHANNEL


def test_correction_does_not_cross_task_or_execution_boundaries(smoke_package):
    task = smoke_package.public
    bad = probe(task, "bad")
    bad.arguments["purpose"]["entrypoint"] = "invalid"
    first = receipt(bad, task)
    events = [rejected_event(bad, first)]
    arguments = probe(task).arguments
    helper = {**arguments, "purpose": {"kind": "helper"}}
    result = probe_requests.review(helper, None, events,
        public_task_hash=first["public_task_hash"], kind="helper")
    assert result["correction"]["status"] == "different_purpose"
    result = probe_requests.review(arguments, None, events,
        public_task_hash="other-task", kind="original_requirement")
    assert result["correction"]["status"] == "not_attempted"
    for exc, args in [(RecoveryError("uncertain"), arguments),
                      (None, probe(task, replay="done").arguments)]:
        assert probe_requests.review(args, exc, events,
            public_task_hash=first["public_task_hash"], kind="original_requirement") is None
    # An accepted setup failure closes the preflight correction chain.
    events.append({"event_type": "action_started", "payload": {
        "tool": "run_probe", "probe_request": {"status": "accepted"},
    }})
    assert receipt(probe(task), task, events)["correction"]["status"] == "not_attempted"


def test_corrected_request_recovers_once_then_executes_the_real_public_caller(
    gateway_factory, monkeypatch,
):
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("offline only"))
    initial, _, _ = gateway_factory()
    gateway = restore(initial, backend=ExecutingProbe())
    bad = probe(gateway.public_task, "bad")
    bad.arguments["purpose"]["entrypoint"] = "invalid"
    rejected = gateway.execute(bad)
    assert rejected.output["request_validation"]["invalid_fields"][0]["path"] == (
        "/purpose/entrypoint")
    assert gateway.probe_sandbox.calls == 0 and view(gateway)["original_attempts"] == 0
    corrected = probe(gateway.public_task, "corrected")
    _crash_journal_once(monkeypatch, event_type="action_started", when="after")
    with pytest.raises(_SimulatedCrash):
        gateway.execute(corrected)
    start = gateway.journal.events()[-1]["payload"]
    admitted = start["probe_request"]["validation"]
    assert admitted["correction"]["status"] == "corrected"
    restored = restore(gateway)
    result = restored.execute(corrected)
    assert result.status == "succeeded", result
    assert result.output["request_validation"] == admitted
    assert result.output["probe_stage"] == "execution_returned"
    assert result.output["reproduction"]["declared_failure_comparison"] == "matched"
    assert result.output["reproduction"]["call_observation"]["calls"]
    assert view(restored)["original_attempts"] == 1 and view(restored)["request_errors"] == 1
    before = restored.journal.path.read_bytes()
    assert restored.execute(corrected).replayed and restored.probe_sandbox.calls == 1
    assert restored.journal.path.read_bytes() == before
    conflict = copy.deepcopy(corrected)
    conflict.arguments["question"] += " changed"
    with pytest.raises(ActionConflict):
        restored.execute(conflict)
