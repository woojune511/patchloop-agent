from __future__ import annotations

import copy
import json

import pytest

from patchloop.dev.verification_concerns import (
    empty_verification_state,
    project_verification_concerns,
    update_verification_concerns,
)
from patchloop.dev.working_notes import WorkingNotesUpdate, memory_update_schema


def concern(operation="upsert", concern_id=None, *, statement="Public branch behavior is untested.",
            evidence=None, reason=None):
    return {
        "operation": operation, "concern_id": concern_id, "statement": statement,
        "evidence_action_id": evidence, "reason": reason,
    }


def result(tool="run_probe", diff="candidate", **output):
    return {
        "action_id": "checked", "input_hash": "sha256:input", "tool": tool,
        "status": "succeeded", "workspace_diff_hash": diff,
        "output": {
            "diff_hash": diff, "passed": True, "status": "passed", "exit_code": 0,
            "stdout": "UNRETAINED_OUTPUT_SENTINEL", **output,
        },
    }


def apply(state, updates, *, diff="candidate", prior=None, turn="t1"):
    return update_verification_concerns(
        state, updates, diff_hash=diff, prior_results=prior or {}, turn_id=turn,
    )


def initial():
    return apply(empty_verification_state(), [concern()])[0]


def project(state, diff="candidate"):
    return project_verification_concerns(state, diff_hash=diff)


def test_new_concerns_are_unverified_without_source_requirements_and_inputs_are_immutable():
    state = empty_verification_state()
    updates = [concern()]
    snapshot = copy.deepcopy(updates)
    updated, receipt = apply(state, updates)
    assert state == empty_verification_state()
    assert updates == snapshot
    assert updated["next_id"] == 2
    assert receipt["status"] == "applied"
    assert receipt["updates"][0]["concern_id"] == "v1"
    projection = project(updated)
    assert projection["unresolved_ids"] == ["v1"]
    assert projection["items"][0]["status"] == "unresolved"
    assert projection["items"][0]["model_authored"] is True
    assert projection["items"][0]["interpretation_status"] == "model_authored_unverified"
    assert "does not prove" in projection["interpretation"]
    projection["items"][0]["statement"] = "projection-only mutation"
    assert updated["items"][0]["statement"] == snapshot[0]["statement"]


@pytest.mark.parametrize("tool", ["run_check", "run_probe"])
def test_resolve_binds_successful_current_diff_result_not_its_output_or_semantic_claim(tool):
    updated, receipt = apply(initial(), [concern(
        "resolve", "v1", statement=None, evidence="checked", reason="Observed public behavior.",
    )], prior={"checked": result(tool)})
    assert receipt["status"] == "applied"
    assert project(updated)["unresolved_ids"] == []
    decision = project(updated)["items"][0]["decision"]
    assert decision["outcome"] == "resolved"
    assert decision["currency"] == "current"
    assert decision["evidence"] == {
        "action_id": "checked", "input_hash": "sha256:input", "tool": tool,
        "diff_hash": "candidate", "currency": "current",
    }
    assert "UNRETAINED_OUTPUT_SENTINEL" not in json.dumps(updated)
    assert "UNRETAINED_OUTPUT_SENTINEL" not in json.dumps(receipt)


@pytest.mark.parametrize("tool", ["run_check", "run_probe"])
def test_baseline_success_cannot_resolve_candidate_uncertainty(tool):
    state = initial()
    updated, receipt = apply(state, [concern(
        "resolve", "v1", statement=None, evidence="checked", reason="Baseline succeeded.",
    )], prior={"checked": result(tool, diff="baseline")})
    assert updated == state
    assert receipt["updates"][0]["code"] == "verification_result_not_current"
    assert receipt["unresolved_ids"] == ["v1"]


@pytest.mark.parametrize("output", [
    {"status": "failed"}, {"exit_code": 1}, {"exit_code": False},
    {"timed_out": True}, {"truncated": True}, {"deadline_exhausted": True},
    {"cleanup_failed": True},
])
def test_unhealthy_probe_cannot_resolve(output):
    state = initial()
    updated, receipt = apply(state, [concern(
        "resolve", "v1", evidence="checked", reason="Claimed success.",
    )], prior={"checked": result(**output)})
    assert updated == state
    assert receipt["updates"][0]["code"] == "verification_result_not_successful"


@pytest.mark.parametrize("output", [
    {"passed": False}, {"timed_out": True}, {"deadline_exhausted": True},
    {"cleanup_failed": True},
])
def test_nonpassing_check_cannot_resolve(output):
    updated, receipt = apply(initial(), [concern(
        "resolve", "v1", evidence="checked", reason="Claimed success.",
    )], prior={"checked": result("run_check", **output)})
    assert project(updated)["unresolved_ids"] == ["v1"]
    assert receipt["updates"][0]["code"] == "verification_result_not_successful"


@pytest.mark.parametrize("override,expected", [
    ({"status": "failed"}, "verification_result_not_successful"),
    ({"tool": "read_file"}, "unobserved_verification_result"),
    ({"action_id": "another"}, "unobserved_verification_result"),
    ({"input_hash": None}, "unobserved_verification_result"),
    ({"workspace_diff_hash": "baseline"}, "verification_result_not_current"),
])
def test_resolution_requires_bound_completed_action(override, expected):
    prior = {"checked": {**result(), **override}}
    updated, receipt = apply(initial(), [concern(
        "resolve", "v1", evidence="checked", reason="Observed public behavior.",
    )], prior=prior)
    assert project(updated)["unresolved_ids"] == ["v1"]
    assert receipt["updates"][0]["code"] == expected


def test_pending_or_missing_action_never_resolves():
    state, receipt = apply(initial(), [concern(
        "resolve", "v1", evidence="pending", reason="Current batch will pass.",
    )])
    assert project(state)["unresolved_ids"] == ["v1"]
    assert receipt["updates"][0]["code"] == "unobserved_verification_result"


@pytest.mark.parametrize("operation", ["resolve", "dismiss"])
def test_decision_reopens_on_new_diff_without_losing_historical_evidence(operation):
    state, _ = apply(initial(), [concern(
        operation, "v1", statement=None,
        evidence="checked" if operation == "resolve" else None,
        reason="Public experiment addressed it." if operation == "resolve" else "Out of scope.",
    )], prior={"checked": result()})
    assert project(state)["items"][0]["status"] == (
        "resolved" if operation == "resolve" else "dismissed"
    )
    snapshot = copy.deepcopy(state)
    next_view = project(state, "next-candidate")
    assert next_view["unresolved_ids"] == ["v1"]
    assert next_view["items"][0]["decision"]["currency"] == "historical"
    if operation == "resolve":
        assert next_view["items"][0]["decision"]["evidence"]["currency"] == "historical"
    assert state == snapshot


def test_upsert_existing_reopens_and_json_restart_preserves_stable_id_allocation():
    state, _ = apply(initial(), [concern("dismiss", "v1", reason="Not currently relevant.")])
    state = json.loads(json.dumps(state))
    state, receipt = apply(state, [
        concern(concern_id="v1", statement="Revised public uncertainty."),
        concern(statement="A different behavior is untested."),
    ], turn="t3")
    assert receipt["available_concern_ids"] == ["v1", "v2"]
    assert project(state)["unresolved_ids"] == ["v1", "v2"]
    assert state["items"][0]["decision"] is None
    assert state["items"][0]["created_turn_id"] == "t1"
    assert state["items"][0]["updated_turn_id"] == "t3"
    assert state["next_id"] == 3


def test_capacity_never_evicts_unresolved_including_historical_decisions():
    state, _ = apply(
        empty_verification_state(), [concern(statement=f"Concern {n}") for n in range(3)],
    )
    unchanged, receipt = apply(state, [concern(statement="Fourth concern")])
    assert unchanged == state
    assert receipt["updates"][0]["code"] == "concern_capacity"
    state, _ = apply(state, [concern("dismiss", "v1", reason="Not relevant to current edit.")])
    unchanged, receipt = apply(state, [concern(statement="Fourth concern")], diff="new-diff")
    assert unchanged == state
    assert receipt["updates"][0]["code"] == "concern_capacity"
    state, receipt = apply(state, [concern(statement="Fourth concern")])
    assert receipt["evicted_concern_ids"] == ["v1"]
    assert receipt["available_concern_ids"] == ["v2", "v3", "v4"]
    assert state["next_id"] == 5


@pytest.mark.parametrize("invalid", [None, "INVALID_RAW_SENTINEL", {}, [concern()] * 4])
def test_invalid_update_collection_is_bounded_nonblocking_feedback(invalid):
    state = initial()
    updated, receipt = apply(state, invalid)
    assert updated == state
    assert receipt["status"] == "rejected"
    assert receipt["diagnostics"][0]["code"] == "invalid_verification_updates"
    assert "INVALID_RAW_SENTINEL" not in json.dumps(receipt)


def test_bad_entry_does_not_reject_valid_sibling_or_source_note_fields():
    raw = {
        "findings": [], "open_question": "Different current focus.",
        "verification_updates": ["INVALID_RAW_SENTINEL", concern()],
    }
    ordinary = WorkingNotesUpdate.model_validate(raw)
    assert ordinary.open_question == "Different current focus."
    state, receipt = apply(empty_verification_state(), ordinary.verification_updates)
    assert receipt["status"] == "partially_applied"
    assert receipt["updates"][0]["code"] == "invalid_verification_update"
    assert receipt["updates"][1]["concern_id"] == "v1"
    assert state["next_id"] == 2
    assert "INVALID_RAW_SENTINEL" not in json.dumps(receipt)


@pytest.mark.parametrize("update,code", [
    (concern(concern_id="v99"), "unknown_concern_id"),
    (concern(statement="  "), "statement_required"),
    (concern("resolve", "v1", evidence="checked"), "reason_required"),
    (concern("dismiss", "v1", reason="  "), "reason_required"),
    (concern(statement="x" * 401), "invalid_verification_update"),
    (concern(reason="x" * 401), "invalid_verification_update"),
    (concern(evidence="x" * 501), "invalid_verification_update"),
])
def test_semantic_and_shape_errors_are_nonblocking(update, code):
    state = initial()
    updated, receipt = apply(state, [update])
    assert updated == state
    assert receipt["updates"][0]["code"] == code


def test_empty_updates_preserve_concerns_and_legacy_note_shape():
    ordinary = WorkingNotesUpdate.model_validate({"findings": [], "open_question": None})
    assert ordinary.verification_updates == []
    state = initial()
    updated, receipt = apply(state, ordinary.verification_updates)
    assert updated == state
    assert receipt["status"] == "not_requested"
    assert receipt["available_concern_ids"] == ["v1"]


def test_unused_nullable_fields_do_not_reject_annotation_or_imply_verification():
    state, receipt = apply(empty_verification_state(), [concern(evidence="unused")])
    assert receipt["status"] == "applied"
    state, receipt = apply(state, [concern(
        "dismiss", "v1", evidence="unused", reason="Not necessary for this change.",
    )])
    assert receipt["status"] == "applied"
    decision = project(state)["items"][0]["decision"]
    assert decision["evidence"] is None
    assert decision["basis"] == "model_dismissal"


def test_provider_wire_schema_is_strict_and_requires_every_object_property():
    schema = memory_update_schema()

    def check(node):
        if isinstance(node, dict):
            if "properties" in node:
                assert set(node["required"]) == set(node["properties"])
                assert node["additionalProperties"] is False
            for value in node.values():
                check(value)
        elif isinstance(node, list):
            for value in node:
                check(value)

    check(schema)
    verification = schema["properties"]["verification_updates"]
    assert verification["maxItems"] == 3
    assert set(verification["items"]["required"]) == {
        "operation", "concern_id", "statement", "evidence_action_id", "reason",
    }
