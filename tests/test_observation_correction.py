"""Pure lineage controls: no provider, process, container or target execution."""

from __future__ import annotations

import copy

import pytest

from patchloop.dev import observation_correction as correction
from patchloop.dev import probe_invocation
from patchloop.dev.verification_concerns import (
    _resolution_evidence,
    project_verification_concerns,
)
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes, sha256_json

WRONG = "record_observation({'bug': False, 'control': False})"
FIXED = "record_observation({'bug': 'F0010' in bug.stdout, 'control': False})"


def binding(action, source, *, corrects=None):
    definition = {
        "entrypoint": "public.main", "input_conditions": "bug and control fixtures",
        "environment_conditions": "fixed workspace", "public_task_hash": "public-task",
        "observation_channel": probe_invocation.CHANNEL,
        "expected_json": canonical_json({"bug": False, "control": False}),
        "reported_failure_json": canonical_json({"bug": True, "control": False}),
        "diagnostic_rules": [{"field": "bug", "call_id": "call-1", "contains": "F0010"},
                             {"field": "control", "call_id": "call-2", "contains": "F0010"}],
    }
    if corrects is not None:
        definition["corrects_action_id"] = corrects
    program_hash = sha256_bytes(source.encode())
    return {"definition": definition, "program_hash": program_hash, "root_action_id": action,
            "case_id": sha256_json({"definition": definition, "program_hash": program_hash})}


def calls():
    return [{"entrypoint": "public.main", "resolved_entrypoint": "public.main",
             "arguments": {"args": [label], "kwargs": {}}, "argv": ["entry", label],
             "cwd": "/tmp/case", "start_cwd": "/tmp", "sys_path": ["/workspace"],
             "inputs": [{"path": "/tmp/case", "hash": "fixture-content", "entries": 3}],
             "environment": {"variables": {"HOME": "home-hash"}, "python": [3, 9, 25]},
             "outcome": "returned", "call_id": f"call-{index}",
             "bound_parameters": {"path": label}, "exception_policy": [],
             "capture": {"scope": "python-streams", "status": "complete", "stderr": "",
                         "stdout": "F0010: parse-error\n" if index == 1 else "warning\n"},
             "exception": None, "exit_code": None}
            for index, label in enumerate(("bug", "control"), 1)]


def action(action_id="baseline", *, corrects=None, status="conflict", source=None):
    source = source or (FIXED if corrects else WRONG)
    b = binding(action_id, source, corrects=corrects)
    value_field = "reported_failure_json" if status == "consistent" else "expected_json"
    authored = b["definition"][value_field]
    result = {
        "action_id": action_id, "tool": "run_probe", "status": "succeeded",
        "workspace_diff_hash": correction.EMPTY_DIFF,
        "output": {"status": "passed", "exit_code": 0,
                   "execution_policy": {"cleanup_status": "confirmed"},
                   "reproduction": {
                       "binding": b, "observed_json": authored,
                       "comparison": "mismatched" if status == "consistent" else "not_compared",
                       "declared_failure_comparison": (
                           "matched" if status == "consistent" else "not_compared"),
                       "reason": None if status == "consistent" else "observation_conflict",
                       "judgment": {"policy": correction.JUDGMENT_POLICY, "status": status,
                                    "host_json": b["definition"]["reported_failure_json"],
                                    "authored_json": authored},
                       "call_observation": {"binding_method": probe_invocation.CHANNEL,
                                            "calls": calls(), "incomplete": False,
                                            "execution_environment": {"image": "image-hash"}},
                   }},
    }
    start = {"action_id": action_id, "tool": "run_probe",
             "baseline_diff_hash": correction.EMPTY_DIFF,
             "arguments": {"python_source": source, "purpose": {
                 "kind": "original_requirement", **b["definition"]}},
             "reproduction_binding": b}
    return [{"event_type": "action_started", "payload": start},
            {"event_type": "action_finished", "payload": {"result": result}}]


def fixed_binding():
    return binding("fixed", FIXED, corrects="baseline")


@pytest.mark.parametrize("status", ["conflict", "unknown"])
def test_unverified_judgment_cannot_resolve_a_verification_concern(status):
    result = action()[1]["payload"]["result"]
    result["input_hash"] = "input"
    result["output"]["diff_hash"] = correction.EMPTY_DIFF
    result["output"]["reproduction"]["judgment"]["status"] = status
    evidence, reason = _resolution_evidence(
        "baseline", {"baseline": result}, correction.EMPTY_DIFF,
    )
    assert evidence is None and reason == "verification_judgment_unverified"


def test_superseded_judgment_reopens_only_its_own_concern_without_rewriting_it():
    state = {"items": [{"concern_id": "v1", "statement": "Original failure is absent",
                       "decision": {"outcome": "resolved", "diff_hash": correction.EMPTY_DIFF,
                                    "evidence": {"action_id": "baseline"}}}]}
    unchanged = copy.deepcopy(state)
    updates = correction.note_updates(correction.review(
        action() + action("fixed", corrects="baseline", status="consistent"),
        correction.EMPTY_DIFF,
    ))
    view = project_verification_concerns(
        state, diff_hash=correction.EMPTY_DIFF, judgment_updates=updates,
    )
    assert view["unresolved_ids"] == ["v1"]
    assert view["items"][0]["judgment_update"]["corrected_action_id"] == "fixed"
    assert state == unchanged
    assert project_verification_concerns(state, diff_hash=correction.EMPTY_DIFF)[
        "items"][0]["status"] == "resolved"


def test_conflict_can_admit_exactly_one_changed_fresh_program():
    events = action()
    original = copy.deepcopy(events)
    view = correction.review(events, correction.EMPTY_DIFF)
    assert view["status"] == "pending" and view["blocked"]
    assert view["attempts_used"] == 0 and view["target_action_id"] == "baseline"
    correction.validate(fixed_binding(), FIXED, events,
                        current_diff=correction.EMPTY_DIFF, action_id="fixed")
    assert events == original
    for b, source in ((None, "helper()"), (binding("no-link", FIXED), FIXED),
                      (binding("fixed", WRONG, corrects="baseline"), WRONG),
                      (binding("fixed", FIXED, corrects="other"), FIXED)):
        with pytest.raises(ContractError):
            correction.validate(b, source, events,
                                current_diff=correction.EMPTY_DIFF, action_id="fixed")
    with pytest.raises(ContractError):
        correction.validate(fixed_binding(), FIXED, events,
                            current_diff=correction.EMPTY_DIFF, action_id="fixed", replay=True)


def test_verified_correction_preserves_receipts_and_supersedes_only_conflict():
    unrelated = action("healthy", status="consistent")
    events = unrelated + action() + action("fixed", corrects="baseline", status="consistent")
    original = copy.deepcopy(events)
    view = correction.review(events, correction.EMPTY_DIFF)
    assert view["status"] == "corrected" and not view["blocked"]
    old_case = events[3]["payload"]["result"]["output"]["reproduction"]["binding"]["case_id"]
    assert view["superseded_case_ids"] == [old_case]
    assert view["corrections"] == [{
        "previous_action_id": "baseline", "corrected_action_id": "fixed",
        "previous_case_id": view["superseded_case_ids"][0],
        "corrected_case_id": fixed_binding()["case_id"],
    }]
    assert events == original
    assert correction.review(events, "candidate")["status"] == "corrected"
    correction.validate(fixed_binding(), FIXED, events, current_diff="candidate",
                        action_id="replay", replay=True)
    with pytest.raises(ContractError, match="already spent"):
        correction.validate(binding("again", FIXED, corrects="baseline"), FIXED, events,
                            current_diff=correction.EMPTY_DIFF, action_id="again")


@pytest.mark.parametrize("field", ["expected_json", "reported_failure_json", "entrypoint",
                                 "diagnostic_rules"])
def test_changed_declarations_cannot_resolve_an_old_conflict(field):
    b = fixed_binding()
    b["definition"][field] = "changed"
    with pytest.raises(ContractError, match="preserves"):
        correction.validate(b, FIXED, action(), current_diff=correction.EMPTY_DIFF,
                            action_id="fixed")


@pytest.mark.parametrize("change", ["arguments", "cwd", "fixture", "environment", "image",
                                  "truncated", "not_failure", "still_conflict", "wrong_diff"])
def test_changed_or_unhealthy_correction_does_not_supersede(change):
    events = action() + action("fixed", corrects="baseline", status="consistent")
    result = events[-1]["payload"]["result"]
    repro = result["output"]["reproduction"]
    call = repro["call_observation"]["calls"][0]
    if change == "arguments":
        call["arguments"]["args"] = ["different"]
    elif change == "cwd":
        call["cwd"] = "/unrelated"
    elif change == "fixture":
        call["inputs"][0]["hash"] = "changed-content"
    elif change == "environment":
        call["environment"]["variables"]["HOME"] = "different-home"
    elif change == "image":
        repro["call_observation"]["execution_environment"]["image"] = "different-image"
    elif change == "truncated":
        call["capture"]["status"] = "truncated"
    elif change == "not_failure":
        repro.update(comparison="matched", declared_failure_comparison="mismatched")
    elif change == "still_conflict":
        repro["judgment"]["status"] = "conflict"
        repro["reason"] = "observation_conflict"
    else:
        result["workspace_diff_hash"] = "candidate"
    view = correction.review(events, correction.EMPTY_DIFF)
    assert view["status"] == "failed" and view["blocked"]
    assert view["superseded_case_ids"] == view["corrections"] == []


def test_rejected_and_pending_attempts_consume_allowance_across_recovery():
    events = action() + action("fixed", corrects="baseline", status="consistent")[:1]
    view = correction.review(events, correction.EMPTY_DIFF)
    assert view["status"] == "pending" and view["pending_started"]
    assert view["attempts_used"] == 1 and view["attempt_action_id"] == "fixed"
    correction.validate(fixed_binding(), FIXED, events,
                        current_diff=correction.EMPTY_DIFF, action_id="fixed")
    with pytest.raises(ContractError, match="already spent"):
        correction.validate(binding("again", FIXED, corrects="baseline"), FIXED, events,
                            current_diff=correction.EMPTY_DIFF, action_id="again")
    events.append({"event_type": "action_finished", "payload": {"result": {
        "action_id": "fixed", "tool": "run_probe", "status": "failed", "output": {},
    }}})
    view = correction.review(copy.deepcopy(events), correction.EMPTY_DIFF)
    assert view["status"] == "failed" and view["attempts_used"] == 1
    assert view["blocked"] and not view["pending_started"]


def test_healthy_failure_and_candidate_conflict_cannot_be_reclassified_as_correction():
    healthy = action(status="consistent")
    assert correction.review(healthy, correction.EMPTY_DIFF)["status"] == "none"
    with pytest.raises(ContractError, match="pending baseline conflict"):
        correction.validate(fixed_binding(), FIXED, healthy,
                            current_diff=correction.EMPTY_DIFF, action_id="fixed")
    events = action()
    events[-1]["payload"]["result"]["workspace_diff_hash"] = "candidate"
    view = correction.review(events, "candidate")
    assert view["status"] == "failed" and view["blocked"]
    assert view["reason"] == "target_not_baseline_conflict"
    assert correction.review(action(), "candidate")["reason"] == (
        "baseline_changed_before_correction")


def test_unobserved_correction_target_never_receives_retrospective_credit():
    events = action("fixed", corrects="baseline", status="consistent") + action()
    view = correction.review(events, correction.EMPTY_DIFF)
    assert view["status"] == "failed" and view["superseded_case_ids"] == []
    assert view["reason"] == "correction_target_unobserved"
