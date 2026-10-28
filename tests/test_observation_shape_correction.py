"""Bounded observation repair, using public local fixtures rather than a provider."""
from __future__ import annotations

import copy
import json
from dataclasses import replace

import pytest
from test_dev_completion_resources import Gateway, counters
from test_dev_probe_cases import TEXT, ExecutingProbe
from test_dev_probes import context
from test_finish_reproduction import checks, finish, mutate, results_for
from test_finish_reproduction_budget import snapshot
from test_probe_purpose import probe

from patchloop.dev import completion_reproduction, probe_comparison, runner
from patchloop.dev import observation_correction as correction
from patchloop.dev.contracts import DevLimits
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json

EXPECTED = {"rows": 2, "control_rows": 2}
FAILURE = {"rows": 3, "control_rows": 2}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("observation correction tests must not access the network")
    monkeypatch.setattr("socket.socket.connect", forbidden)


def shape_probe(task, action="malformed", *, corrected=False, corrects=None):
    source = (
        "target = observed_target()\n"
        f"rows = target({TEXT!r}).value\n"
        "control = target('h,v\\na,b\\n').value\n"
        "value = {'rows': len(rows), 'control_rows': len(control)}\n"
    )
    if not corrected:
        source += "value.update({f'log_{i}': i for i in range(7)})\n"
    source += "record_observation(value)\n"
    call = probe(task, action, source=source)
    call.arguments["purpose"].update(
        expected_json=json.dumps(EXPECTED), reported_failure_json=json.dumps(FAILURE),
        diagnostic_rules=None, corrects_action_id=corrects,
    )
    return call


def gateway_for(factory, *, policy="reproduction-gated-v1"):
    initial, journal, workspace = factory()
    backend = ExecutingProbe()
    gateway = DevToolGateway(
        workspace=workspace, public_task=initial.public_task, journal=journal,
        sandbox=initial.sandbox, limits=initial.limits, probe_sandbox=backend,
        reproduction_acquisition="bounded-v1", verification_policy=policy,
    )
    return gateway, journal, backend


def verification(gateway):
    return gateway.completion_verification(diff_hash=gateway.current_diff_hash)


@pytest.fixture
def corrected_gateway(gateway_factory):
    gateway, journal, backend = gateway_for(gateway_factory)
    original = gateway.execute(shape_probe(gateway.public_task))
    corrected = shape_probe(gateway.public_task, "corrected", corrected=True, corrects="malformed")
    result = gateway.execute(corrected)
    assert result.status == "succeeded", result
    assert verification(gateway)["observation_correction"]["status"] == "corrected"
    return gateway, journal, backend, original, corrected, result


def test_two_field_contract_rejects_nine_field_observation_then_repairs_and_verifies(
    corrected_gateway, smoke_package,
):
    gateway, journal, backend, original, corrected, result = corrected_gateway
    observation = original.output["reproduction"]
    assert len(json.loads(observation["observed_json"])) == 9
    assert observation["reason"] == "observation_shape_mismatch"
    assert observation["comparison"] == observation["declared_failure_comparison"] == "not_compared"
    assert observation["observation_error"]["kind"] == "object_field_mismatch"
    assert observation["call_observation"]["incomplete"] is False
    prior = journal.events()[:next(i for i, e in enumerate(journal.events())
                                  if e["event_type"] == "action_started"
                                  and e["payload"]["action_id"] == "corrected")]
    pending = correction.review(prior, correction.EMPTY_DIFF)
    assert pending["status"] == "pending" and pending["attempts_used"] == 0
    assert pending["kind"] == "object_field_mismatch"
    assert pending["target_action_id"] == "malformed"
    assert pending["target_observation_error"] == observation["observation_error"]
    corrected_repro = result.output["reproduction"]
    assert corrected_repro["comparison"] == "mismatched"
    assert corrected_repro["declared_failure_comparison"] == "matched"
    state = verification(gateway)
    assert state["superseded_case_count"] == 1
    assert state["baseline_failure_case_ids"] == [corrected_repro["binding"]["case_id"]]
    assert state["observation_correction"]["attempts_used"] == 1
    before = journal.path.read_bytes()
    assert gateway.execute(corrected).replayed
    assert journal.path.read_bytes() == before and backend.calls == 2

    public = compact_model_state(context(gateway, smoke_package), [])
    delivered = reconstruct_state(assemble_model_input(
        system_prompt="fixed", state=public, history=[], context_policy="segmented-v1"))
    assert delivered["reproduction_review"]["completion"]["observation_correction"][
        "corrections"][0]["corrected_action_id"] == "corrected"

    mutate(gateway)
    runner._replay_original_cases(
        journal=journal, gateway=gateway, counters=runner._restore_counters(journal),
        active_elapsed_ms=lambda: 20, acquired_only=True,
    )
    assert verification(gateway)["status"] == "cases_verified"
    checks(gateway)
    submitted, _ = finish(gateway)
    assert submitted.output["delivery_state"] == "cases_verified_delivery"
    assert backend.calls == 3
    assert results_for(journal, "run_probe")[0]["output"]["reproduction"] == observation


def test_corrected_baseline_needs_same_inputs_unchanged_values_and_actual_failure(
    corrected_gateway,
):
    gateway, journal, _, _, corrected, result = corrected_gateway
    events = journal.events()
    original_events = copy.deepcopy(events)
    result_id = "corrected"
    for change in ("input", "incomplete", "not_failure", "candidate", "expected", "failure"):
        changed = copy.deepcopy(events)
        finished = next(e["payload"]["result"] for e in changed
                        if e["event_type"] == "action_finished"
                        and e["payload"]["result"]["action_id"] == result_id)
        repro = finished["output"]["reproduction"]
        if change == "input":
            repro["call_observation"]["calls"][0]["arguments"]["args"] = ["different input"]
        elif change == "incomplete":
            repro["call_observation"]["incomplete"] = True
        elif change == "not_failure":
            repro.update(comparison="matched", declared_failure_comparison="mismatched",
                         observed_json=repro["binding"]["definition"]["expected_json"])
        elif change == "candidate":
            finished["workspace_diff_hash"] = "candidate"
        else:
            field = "expected_json" if change == "expected" else "reported_failure_json"
            repro["binding"]["definition"][field] = '{"rows": 0, "control_rows": 2}'
        review = correction.review(changed, correction.EMPTY_DIFF)
        assert review["status"] == "failed", change
        assert review["superseded_case_ids"] == [], change
    assert events == original_events

    prior = [e for e in events if not (
        e["event_type"] in {"action_started", "action_finished"}
        and (e["payload"].get("action_id") or e["payload"].get("result", {}).get("action_id"))
        == result_id)]
    binding = result.output["reproduction"]["binding"]
    for field in ("expected_json", "reported_failure_json", "entrypoint"):
        changed_binding = copy.deepcopy(binding)
        changed_binding["definition"][field] = "changed"
        with pytest.raises(ContractError, match="preserves"):
            correction.validate(changed_binding, corrected.arguments["python_source"], prior,
                                current_diff=correction.EMPTY_DIFF, action_id="corrected")
    assert gateway.execute(corrected.model_copy(update={"action_id": "again"})).status == "failed"


def test_optional_diagnosis_does_not_force_correction_and_cannot_correct_after_edit(
    gateway_factory, smoke_package,
):
    gateway, _, backend = gateway_for(gateway_factory, policy="public-checks-v1")
    gateway.execute(shape_probe(gateway.public_task))
    state = verification(gateway)
    assert state["status"] == "unverified" and state["failed_count"] == 0
    selected = runner._tool_policy(
        gateway, runner._restore_counters(gateway.journal), gateway.limits)
    public = context(gateway, smoke_package)
    public["action_horizon"] = runner._repair_inspection_payload(selected)
    delivered = reconstruct_state(assemble_model_input(
        system_prompt="fixed", state=compact_model_state(public, []), history=[],
        context_policy="segmented-v1"))
    pending = delivered["reproduction_review"]["completion"]["observation_correction"]
    assert pending["target_action_id"] == "malformed"
    assert pending["target_observation_error"]["kind"] == "object_field_mismatch"
    offered = delivered["action_horizon"]["observation_correction"]
    assert offered["required"] is False and offered["offered"] is True
    helper = probe(gateway.public_task, "helper", source="print('independent diagnostic')")
    helper.arguments["purpose"] = {"kind": "helper"}
    assert gateway.execute(helper).status == "succeeded"
    assert verification(gateway)["observation_correction"]["attempts_used"] == 0
    mutate(gateway)
    correction_call = shape_probe(
        gateway.public_task, "too-late", corrected=True, corrects="malformed")
    result = gateway.execute(correction_call)
    assert result.status == "failed"
    assert backend.calls == 2
    assert verification(gateway)["observation_correction"]["superseded_case_ids"] == []
    checks(gateway)
    submitted, _ = finish(gateway)
    assert submitted.status == "succeeded"
    assert submitted.output["delivery_state"] == "unverified_delivery"


def test_unsuccessful_correction_spends_one_attempt_without_retiring_bad_observation(
    gateway_factory,
):
    gateway, _, backend = gateway_for(gateway_factory)
    gateway.execute(shape_probe(gateway.public_task))
    failed = shape_probe(gateway.public_task, "not-reproduced",
                         corrected=True, corrects="malformed")
    failed.arguments["python_source"] = failed.arguments["python_source"].replace(
        "record_observation(value)", f"record_observation({EXPECTED!r})")
    assert gateway.execute(failed).status == "succeeded"
    state = verification(gateway)["observation_correction"]
    assert state["status"] == "failed" and state["attempts_used"] == 1
    assert state["superseded_case_ids"] == []
    second = shape_probe(gateway.public_task, "second", corrected=True, corrects="malformed")
    assert gateway.execute(second).status == "failed"
    assert backend.calls == 2


@pytest.mark.parametrize(("expected", "failure", "actual"), [
    ({"rows": 2}, {"rows": 3}, {"rows": 4}),
    ([1, 2], [1, 2, 3], [1]),
    ({"rows": [1, 2]}, {"rows": [1, 2, 3]}, {"rows": [1]}),
    ({"rows": 2}, {"error": True}, {"unexpected": True}),
])
def test_value_and_array_cardinality_failures_are_not_observation_contract_errors(
    expected, failure, actual,
):
    definition = {"expected_json": json.dumps(expected),
                  "reported_failure_json": json.dumps(failure)}
    assert probe_comparison.object_field_mismatch(definition, json.dumps(actual)) is None


def test_optional_correction_feedback_reaches_policy_without_reserving_a_required_stage():
    gateway = Gateway(("PASS",), initial=False)
    gateway.verification_policy = "public-checks-v1"
    clean = snapshot(gateway, status="unverified", case_count=0, pending_count=0)
    advice = {"blocked": True, "status": "pending", "pending_started": False,
              "target_action_id": "malformed", "kind": "object_field_mismatch",
              "target_observation_error": {"kind": "object_field_mismatch"}}
    broken = replace(clean, completion_verification={
        **clean.completion_verification, "observation_correction": advice})
    policies = [runner._tool_policy(
        gateway, counters(model=4, tools=5), DevLimits(), snapshot=state,
        repair_recheck=False, _preview_inspection=False,
    ) for state in (clean, broken)]
    assert policies[0].allowed_tools == policies[1].allowed_tools
    assert policies[0].minimum_completion_calls == policies[1].minimum_completion_calls
    assert (policies[0].minimum_completion_tool_actions
            == policies[1].minimum_completion_tool_actions)
    info = policies[1].observation_correction
    assert info["required"] is False and info["uses_minimum_completion_reserve"] is False
    assert info["target_action_id"] == advice["target_action_id"]
    assert info["target_observation_error"] == advice["target_observation_error"]


def test_probe_tool_description_matches_optional_submission_policy():
    descriptions = {}
    for policy in ("reproduction-gated-v1", "public-checks-v1"):
        schemas = dev_tool_schemas(
            finish_enabled=True, allowed_tools=["run_probe", "finish_task", "stop_task"],
            verification_policy=policy,
        )
        descriptions[policy] = next(s["description"] for s in schemas if s["name"] == "run_probe")
    assert "At finish the host replays" in descriptions["reproduction-gated-v1"]
    assert "At finish the host replays" not in descriptions["public-checks-v1"]
    assert "optional diagnostics" in descriptions["public-checks-v1"]


def test_candidate_shape_error_cannot_create_a_new_baseline_correction(corrected_gateway):
    gateway, journal, _, _, _, fixed = corrected_gateway
    events = copy.deepcopy(journal.events())
    candidate_diff = "candidate-diff"
    replay = probe(gateway.public_task, "candidate-shape", replay="corrected")
    input_hash = sha256_json({"tool": replay.name, "arguments": replay.arguments})
    current = copy.deepcopy(fixed.model_dump(mode="json"))
    current.update(action_id=replay.action_id, input_hash=input_hash,
                   workspace_diff_hash=candidate_diff)
    current["output"].update(diff_hash=candidate_diff, workspace_diff_hash=candidate_diff)
    observation = current["output"]["reproduction"]
    observation.update(observed_json=canonical_json({**EXPECTED, "unexpected_log": 1}),
                       reason="observation_shape_mismatch", comparison="not_compared",
                       declared_failure_comparison="not_compared")
    observation["observation_error"] = probe_comparison.object_field_mismatch(
        observation["binding"]["definition"], observation["observed_json"])
    events.extend([
        {"event_type": "action_started", "payload": {
            "action_id": replay.action_id, "tool": replay.name, "input_hash": input_hash,
            "arguments": replay.arguments, "baseline_diff_hash": candidate_diff,
            "reproduction_binding": observation["binding"],
        }},
        {"event_type": "action_finished", "payload": {"result": current}},
    ])
    state = correction.review(events, candidate_diff)
    assert state["status"] == "corrected" and state["blocked"] is False
    assert state["target_action_id"] is None and state["attempts_used"] == 1
    completion = completion_reproduction.review(
        events, candidate_diff, public_task=gateway.public_task, run_id=journal.run_id)
    assert completion["failed_count"] == 0 and completion["target_failure_count"] == 0
    case = next(row for row in completion["cases"]
                if row["case_id"] == observation["binding"]["case_id"])
    assert case["current"]["reason"] == "observation_shape_mismatch"
    assert case["current"]["comparison"] == "not_compared"
    assert case["evidence"]["status"] == "UNKNOWN"
