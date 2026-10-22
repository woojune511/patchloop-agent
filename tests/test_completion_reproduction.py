"""Public completion evidence and bounded replay protocol; no model-quality claim."""

from __future__ import annotations

import copy

import pytest
from test_dev_probe_cases import ExecutingProbe
from test_dev_tools import mutation_call, read_calls
from test_probe_purpose import SOURCE, probe

from patchloop.dev import completion_reproduction as completion
from patchloop.dev import probe_invocation, reproduction
from patchloop.dev.contracts import RequestedTool
from patchloop.errors import RecoveryError
from patchloop.util import canonical_json, sha256_json


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("completion evidence tests must not access the network")
    monkeypatch.setattr("socket.socket.connect", forbidden)


@pytest.fixture
def original(gateway_factory):
    gateway, journal, _ = gateway_factory()
    backend = gateway.probe_sandbox = ExecutingProbe()
    result = gateway.execute(probe(gateway.public_task))
    assert result.output["reproduction"]["comparison"] == "mismatched", result
    return gateway, journal, backend


def project(gateway, journal, *, events=None, diff=None):
    return completion.review(journal.events() if events is None else events,
                             gateway.current_diff_hash if diff is None else diff,
                             public_task=gateway.public_task, run_id=journal.run_id)


def observation(events, action, diff, *, comparison="matched", change=None):
    """Build a synthetic public receipt from the real completed root's schema."""
    event = copy.deepcopy(next(e for e in events if e["event_type"] == "action_finished"
                               and e["payload"]["result"]["action_id"] == "original"))
    result = event["payload"]["result"]
    event["payload"]["action_id"] = result["action_id"] = action
    result["workspace_diff_hash"] = result["output"]["diff_hash"] = diff
    value = result["output"]["reproduction"]
    value["comparison"] = comparison
    if action.startswith("completion-reproduction-"):
        result["input_hash"] = sha256_json({"tool": "run_probe", "arguments": {
            "question": None, "python_source": None,
            "replay_action_id": value["binding"]["root_action_id"], "purpose": None}})
    if change is not None:
        change(value["call_observation"])
    return event


def automatic_identity(review):
    item = review["pending_cases"][0]
    return {"action_id": item["auto_action_id"], "case_id": item["case_id"],
            "root_action_id": item["root_action_id"],
            "candidate_diff_hash": item["current_diff"]}


def test_real_replay_uses_original_program_and_current_diff_with_recoverable_identity(original):
    gateway, journal, backend = original
    before = project(gateway, journal)
    assert before["status"] == "refuted" and before["failed_count"] == 1
    gateway.execute_batch(read_calls())
    assert gateway.execute(mutation_call(gateway)).status == "succeeded"
    pending = project(gateway, journal)
    assert pending["status"] == "pending" and pending["pending_count"] == 1
    item = pending["pending_cases"][0]
    call = completion.replay_call(journal.run_id, item["case_id"], item["root_action_id"],
                                  gateway.current_diff_hash)
    first = gateway.execute(call)
    assert first.output["reproduction"]["comparison"] == "matched", first
    assert gateway.execute(call).replayed and backend.calls == 2
    assert backend.sources[0] == backend.sources[1]
    result = project(gateway, journal)
    assert result["status"] == "cases_verified" and result["pending_count"] == 0
    assert result["requirement_mapping"] == "model_authored_unverified"
    assert result["repair_success"] == "not_assessed"
    assert result["cases"][0]["automatic_attempt"]["status"] == "finished"
    # A later candidate loses current evidence and gets a different replay identity.
    later = project(gateway, journal, diff="new-candidate")
    assert later["status"] == "pending"
    assert later["pending_cases"][0]["auto_action_id"] != call.action_id
    assert completion.replay_call("run_dev_other", item["case_id"], item["root_action_id"],
                                  gateway.current_diff_hash).action_id != call.action_id


def test_plan_assessment_helper_and_new_requirement_do_not_close_original(original):
    gateway, journal, _ = original
    helper = RequestedTool(name="run_probe", action_id="helper", arguments={
        "question": "Does the helper succeed?", "python_source": "print(True)",
        "replay_action_id": None, "purpose": {"kind": "helper"},
    }, turn_decision={"mode": "verify", "basis": "Try a helper."})
    assert gateway.execute(helper).status == "succeeded"
    changed = probe(gateway.public_task, "different", source=SOURCE + "\n# different experiment")
    # Replace the expectation with the actually observed baseline value: this new
    # declaration passes, but its different binding cannot erase the failing one.
    changed.arguments["purpose"]["expected_json"] = next(
        e["payload"]["result"]["output"]["reproduction"]["observed_json"]
        for e in journal.events() if e["event_type"] == "action_finished"
        and e["payload"]["result"]["action_id"] == "original")
    assert gateway.execute(changed).output["reproduction"]["comparison"] == "matched"
    events = journal.events() + [{"event_type": "model_plan_changed", "payload": {
        "plan": "Only helper work remains.", "assessment": "Everything is complete."}}]
    result = project(gateway, journal, events=events)
    assert result["case_count"] == 2 and result["failed_count"] == 1
    assert result["status"] == "refuted"
    assert result["cases"][0]["root_action_id"] == "original"


@pytest.mark.parametrize("change", [
    lambda trace: trace["calls"][0]["arguments"].update(args=["different input"]),
    lambda trace: trace["calls"][0]["environment"].update(MODE="different"),
    lambda trace: trace["calls"][0].update(inputs=[{
        "path": "fixture", "hash": "changed-contents", "entries": 1}]),
    lambda trace: trace["execution_environment"].update(image_digest="different-image"),
])
def test_changed_actual_conditions_remain_pending_then_unverified_after_one_attempt(
    original, change,
):
    gateway, journal, _ = original
    events = journal.events()
    events.append(observation(events, "changed-conditions", "D1", change=change))
    pending = project(gateway, journal, events=events, diff="D1")
    assert pending["status"] == "pending"
    identity = automatic_identity(pending)
    events.append(observation(events, identity["action_id"], "D1", change=change))
    result = project(gateway, journal, events=events, diff="D1")
    assert result["status"] == "unverified" and result["pending_count"] == 0
    assert result["cases"][0]["evidence"]["status"] == "UNKNOWN"
    assert project(gateway, journal, events=events, diff="D2")["pending_count"] == 1


def test_conflicting_current_results_remain_refuted_even_after_a_later_success(original):
    gateway, journal, _ = original
    events = journal.events()
    events.extend([observation(events, "still-fails", "D1", comparison="mismatched"),
                   observation(events, "passes-later", "D1")])
    result = project(gateway, journal, events=events, diff="D1")
    case = result["cases"][0]
    assert result["status"] == "refuted" and result["failed_count"] == 1
    assert case["evidence"]["status"] == "CONFLICT"
    assert set(case["evidence"]["evidence_action_ids"]) == {"still-fails", "passes-later"}


def test_case_display_limit_does_not_limit_replay_obligations_or_omit_controls(original):
    gateway, journal, _ = original
    expected = next(e["payload"]["result"]["output"]["reproduction"]["observed_json"]
                    for e in journal.events() if e["event_type"] == "action_finished")
    for number in range(4):
        call = probe(gateway.public_task, f"control-{number}", source=SOURCE + f"\n# {number}")
        call.arguments["purpose"]["expected_json"] = expected
        assert gateway.execute(call).output["reproduction"]["comparison"] == "matched"
    result = project(gateway, journal, diff="D1")
    assert len(result["cases"]) == 3 and result["omitted_count"] == 2
    assert result["case_count"] == result["replayable_case_count"] == result["pending_count"] == 5
    assert {p["root_action_id"] for p in result["pending_cases"]} == {
        "original", "control-0", "control-1", "control-2", "control-3"}
    # Every omitted case must also settle before the aggregate leaves pending.
    events = journal.events()
    for pending in result["pending_cases"]:
        events.append({"event_type": "completion_reproduction_skipped", "payload": {
            "action_id": pending["auto_action_id"], "case_id": pending["case_id"],
            "root_action_id": pending["root_action_id"], "candidate_diff_hash": "D1",
            "reason": "budget_exhausted"}})
    result = project(gateway, journal, events=events, diff="D1")
    assert result["status"] == "unverified" and result["pending_count"] == 0
    assert result["case_count"] == 5


def test_started_marker_does_not_settle_attempt_but_exact_durable_skip_does(original):
    gateway, journal, _ = original
    events = journal.events()
    before = project(gateway, journal, events=events, diff="D1")
    identity = automatic_identity(before)
    started = {"event_type": "completion_reproduction_started", "payload": identity}
    events.append(started)
    assert project(gateway, journal, events=events, diff="D1")["pending_count"] == 1
    wrong = {"event_type": "completion_reproduction_skipped", "payload": {
        **identity, "candidate_diff_hash": "other-candidate", "reason": "budget_exhausted"}}
    assert project(gateway, journal, events=[*events, wrong], diff="D1")["pending_count"] == 1
    events.append({"event_type": "completion_reproduction_skipped", "payload": {
        **identity, "reason": "budget_exhausted"}})
    result = project(gateway, journal, events=events, diff="D1")
    assert result["status"] == "unverified" and result["pending_count"] == 0
    assert result["cases"][0]["automatic_attempt"] == {
        "status": "skipped", "reason": "budget_exhausted"}
    # A later marker for a different candidate cannot undo the durable skip.
    assert project(gateway, journal, events=[*events, wrong], diff="D1")["pending_count"] == 0
    assert project(gateway, journal, events=events, diff="D2")["pending_count"] == 1


def test_finished_marker_alone_never_claims_case_verified_and_observation_wins(original):
    gateway, journal, _ = original
    events = journal.events()
    identity = automatic_identity(project(gateway, journal, events=events, diff="D1"))
    events.append({"event_type": "completion_reproduction_finished", "payload": identity})
    result = project(gateway, journal, events=events, diff="D1")
    assert result["status"] == "unverified" and result["pending_count"] == 0
    events.append(observation(events, identity["action_id"], "D1", comparison="mismatched"))
    assert project(gateway, journal, events=events, diff="D1")["status"] == "refuted"


@pytest.mark.parametrize("field", [
    "timed_out", "truncated", "cleanup_failed", "deadline_exhausted",
])
def test_unhealthy_current_execution_never_gets_comparison_credit(original, field):
    gateway, journal, _ = original
    events = journal.events()
    identity = automatic_identity(project(gateway, journal, events=events, diff="D1"))
    bad = observation(events, identity["action_id"], "D1")
    bad["payload"]["result"]["output"][field] = True
    result = project(gateway, journal, events=[*events, bad], diff="D1")
    assert result["status"] == "unverified" and result["pending_count"] == 0


def test_first_binding_is_not_replaced_by_changed_expectation(original):
    gateway, journal, _ = original
    events = journal.events()
    changed = observation(events, "changed-binding", "D1")
    changed["payload"]["result"]["output"]["reproduction"]["binding"]["definition"][
        "expected_json"] = "true"
    result = project(gateway, journal, events=[*events, changed], diff="D1")
    assert result["status"] == "pending" and result["case_count"] == 1
    assert result["cases"][0]["purpose"]["expected_json"] != "true"


def test_automatic_action_id_cannot_be_settled_by_different_arguments(original):
    gateway, journal, _ = original
    events = journal.events()
    identity = automatic_identity(project(gateway, journal, events=events, diff="D1"))
    changed = observation(events, identity["action_id"], "D1")
    changed["payload"]["result"]["input_hash"] = "other-arguments"
    with pytest.raises(RecoveryError, match="action identity"):
        project(gateway, journal, events=[*events, changed], diff="D1")


def test_no_case_incomplete_root_and_legacy_binding_are_explicitly_unverified(gateway_factory):
    gateway, journal, _ = gateway_factory()
    gateway.probe_sandbox = ExecutingProbe()
    empty = project(gateway, journal)
    assert empty["status"] == "unverified" and empty["case_count"] == 0
    result = gateway.execute(probe(gateway.public_task, source="record_observation(True)"))
    assert result.output["reproduction"]["comparison"] == "not_compared"
    unestablished = project(gateway, journal)
    assert unestablished["status"] == "unverified"
    assert unestablished["unestablished_count"] == 1
    assert unestablished["replayable_case_count"] == unestablished["pending_count"] == 0
    # Legacy name traces do not record concrete invocation/input fingerprints.
    events = journal.events()
    for event in events:
        payload = event["payload"]
        binding = payload.get("reproduction_binding")
        if event["event_type"] == "action_finished":
            binding = payload["result"]["output"]["reproduction"]["binding"]
        if binding:
            binding["definition"]["observation_channel"] = reproduction.OBSERVATION_CHANNEL
    assert project(gateway, journal, events=events)["status"] == "unverified"


def test_projection_is_pure_and_contains_only_public_scope(original):
    gateway, journal, _ = original
    events = journal.events()
    before = canonical_json(events)
    result = project(gateway, journal, events=events)
    result["cases"][0]["purpose"]["requirement_quote"] = "edited outside projection"
    assert canonical_json(events) == before
    assert probe_invocation.CHANNEL in canonical_json(project(gateway, journal))
