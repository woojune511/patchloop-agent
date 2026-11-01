"""Fixed-review delivery preserves public observations without reviving repair controls."""

from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest

from diagnostics import counterexample_discovery as design
from diagnostics import counterexample_discovery_rollout as rollout
from diagnostics import discovery_review_context as review
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import PublicTask
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.contracts import DevLimits, PublicTurnDecision
from patchloop.dev.conversation import TASK_MESSAGE
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import canonical_json


@pytest.fixture
def saved_request():
    public = PublicTask.model_validate({
        "schema_version": "task-public-v1", "task_id": "review-context-toy", "split": "dev-train",
        "repository": {"url": "snapshot://review-context-toy",
                       "base_commit": "sha256:" + "a" * 64, "language": "python"},
        "issue": {"title": "Public caller", "description": "value() returns zero."},
        "constraints": {"allowed_paths": ["toy.py"]},
        "visible_checks": [{"id": "public-example", "command": ["python", "public_test.py"]}],
    })
    request = design.initial_request(public, "fixed patch", {
        "python": "3.12", "snapshot_scope": "all_tracked_regular_files",
        "source_roots": ["/workspace"],
    })
    state = {
        "workflow_gate": "needs_visible_checks", "available_tool_names": ["run_check"],
        "remaining_visible_check_ids": ["public-example"], "ready_to_submit": False,
        "completion_guidance": "run_check then finish_task", "completion_stage": "finish",
        "action_horizon": {"next": "run_check"}, "segment_handoff": {"review_requested": True},
        "mutation_scope_budget": {"remaining": 3}, "mutation_readiness": {"ready": True},
        "commitment_signal": {"stop": True}, "protocol_correction": {"try": "finish_task"},
        "diagnosis_stage": {}, "repair_stage": {}, "repair_intent": {},
        "completion_cost": 99, "minimum_completion_tool_actions": 2,
        "completion_budget_tool_actions": 3,
        "remaining_budget": {"model_calls": 4, "probe_calls": 2},
        "current_diff": {"patch_hash": "sha256:fixed", "patch": "fixed patch"},
        "visible_check_status": [{"check_id": "public-example", "status": "NOT_RUN"}],
        "current_sources": [{
            "path": "toy.py", "file_hash": "sha256:source", "edit_permission": "allowed_path",
            "inline_spans": [{"start_line": 1, "end_line": 2,
                              "content": 'def value():\n    return "run_check"'}],
        }],
        "latest_tool_results": [{"tool": "run_probe", "action_id": "prior-probe",
                                 "output": {"stdout": "exact observation\n", "status": "failed"}}],
        "working_plan": {"plan": {"text": "An authored plan, not execution evidence."}},
        "repair_recheck": {"enabled": True, "policy": "automatic", "last_result": "NOT_RUN"},
        "probe_recheck": {"enabled": True, "last_result": {"status": "failed"}},
        "reproduction_review": {
            "submission_gate": "blocked", "status": "unverified",
            "cases": [{"case_id": "public-case", "diff_hash": "sha256:old",
                       "observations": [{"comparison": "not_compared", "stdout": "unchanged"}]}],
            "completion": {
                "blocks_submission": True, "early_replay_reusable": True,
                "original_obligation": {
                    "requirement": "value() returns zero.", "status": "NOT_RUN",
                    "original_attempts": 1, "max_original_attempts": 2,
                    "max_investigation_actions": 4, "max_preparation_actions": 6,
                    "max_request_errors": 2, "preparation_actions_remaining": 5,
                },
                "helper_correction": {
                    "available": True, "test_available": True, "case_id": "public-case",
                    "attempted_action_ids": ["prior-probe"], "last_result": {"status": "failed"},
                    "preparation_available": True, "preparation_limit": 6,
                    "preparation_tool_actions_available": 5, "offered_tools": ["run_tests"],
                    "blocks_submission": True,
                },
            },
            "probe_followup": {"replay": {
                "available": True, "reference_valid": True, "action_id": "prior-probe",
                "arguments": {"replay_action_id": "prior-probe"}, "argument_scope": "replay",
            }},
        },
    }
    request["input"].extend([
        {"role": "developer", "content": canonical_json({
            "kind": "harness_current_state", "state": state,
        })},
        copy.deepcopy(TASK_MESSAGE),
        {"role": "developer", "content": canonical_json({
            "kind": "harness_historical_public_evidence_v1", "state": state,
        })},
        {"type": "function_call", "call_id": "prior-probe", "name": "run_probe",
         "arguments": '{"python_source":"print(\\\"run_check\\\")\\n"}'},
        {"type": "function_call_output", "call_id": "prior-probe",
         "output": '{ "tool": "run_probe", "output": {"stdout": "exact\\n"} }'},
    ])
    return request


def current_state(request):
    return next(
        json.loads(item["content"])["state"] for item in request["input"]
        if item.get("role") == "developer"
        and json.loads(item["content"]).get("kind") == "harness_current_state"
    )


def test_projection_preserves_public_facts_and_only_replaces_current_controls(saved_request):
    original = copy.deepcopy(saved_request)
    projected = review.project_request(saved_request)
    assert saved_request == original
    assert review.project_request(projected) == projected
    before, after = current_state(original), current_state(projected)
    assert after["workflow_gate"] == "fixed_candidate_review"
    assert after["available_tool_names"] == [tool["name"] for tool in original["tools"]]
    assert "run_check" not in after["available_tool_names"]
    for field in (
        "remaining_visible_check_ids", "ready_to_submit", "completion_guidance",
        "completion_stage", "action_horizon", "segment_handoff", "mutation_scope_budget",
        "mutation_readiness", "commitment_signal", "protocol_correction", "diagnosis_stage",
        "repair_stage", "repair_intent", "completion_cost", "minimum_completion_tool_actions",
        "completion_budget_tool_actions",
    ):
        assert field not in after
    for field in ("remaining_budget", "current_diff", "visible_check_status", "current_sources",
                  "latest_tool_results", "working_plan"):
        assert after[field] == before[field]
    # Public task/command text, archives, program bytes and result bytes are
    # evidence. Their tool-name strings must not be recursively scrubbed.
    assert projected["input"][:2] == original["input"][:2]
    assert projected["input"][3] == review.DIAGNOSTIC_TASK_MESSAGE
    assert projected["input"][4:] == original["input"][4:]
    assert projected["tools"] == original["tools"]


def test_saved_reproduction_receipts_remain_without_old_recovery_or_replay_grants(saved_request):
    before = current_state(saved_request)
    after = current_state(review.project_request(saved_request))
    for field in ("repair_recheck", "probe_recheck"):
        assert after[field]["enabled"] is False
        assert after[field]["last_result"] == before[field]["last_result"]
    evidence = after["reproduction_review"]
    assert evidence["status"] == before["reproduction_review"]["status"]
    assert evidence["cases"] == before["reproduction_review"]["cases"]
    assert "submission_gate" not in evidence
    completion = evidence["completion"]
    assert "blocks_submission" not in completion and "early_replay_reusable" not in completion
    obligation = completion["original_obligation"]
    for key in ("requirement", "status", "original_attempts"):
        assert obligation[key] == before["reproduction_review"]["completion"][
            "original_obligation"][key]
    assert not {"max_original_attempts", "max_investigation_actions", "max_preparation_actions",
                "max_request_errors", "preparation_actions_remaining"}.intersection(obligation)
    correction = completion["helper_correction"]
    assert correction["available"] is False and correction["test_available"] is False
    assert correction["case_id"] == "public-case"
    assert correction["attempted_action_ids"] == ["prior-probe"]
    assert correction["last_result"] == {"status": "failed"}
    assert not {
        "offered_tools", "blocks_submission", "preparation_limit",
        "preparation_available", "preparation_tool_actions_available",
    }.intersection(correction)
    replay = evidence["probe_followup"]["replay"]
    assert replay["available"] is False and replay["reference_valid"] is True
    assert replay["action_id"] == "prior-probe"
    assert "arguments" not in replay and "argument_scope" not in replay
    probe = next(tool for tool in saved_request["tools"] if tool["name"] == "run_probe")
    assert "replay_action_id" not in probe["parameters"]["properties"]


def test_existing_nullable_report_annotation_is_terminal_without_adding_fresh_fields(saved_request):
    seven = {"outcome", "requirement_excerpt", "justification", "probe_action_id",
             "expected", "observed", "limitations"}
    fresh = review.project_request(saved_request)
    report = next(tool for tool in fresh["tools"] if tool["name"] == "report_discovery")
    assert set(report["parameters"]["properties"]) == set(report["parameters"]["required"]) == seven
    assert report == design.report_schema()
    old_report = copy.deepcopy(report)
    decision = next(tool for tool in fresh["tools"] if tool["name"] == "read_file")[
        "parameters"]["properties"]["turn_decision"]
    report["parameters"]["properties"]["turn_decision"] = {
        "anyOf": [copy.deepcopy(decision), {"type": "null"}],
    }
    report["parameters"]["required"].append("turn_decision")
    projected = review.project_request(fresh)
    annotation = next(tool for tool in projected["tools"] if tool["name"] == "report_discovery")
    parameters = annotation["parameters"]
    nullable = parameters["properties"]["turn_decision"]
    assert nullable["anyOf"][1] == {"type": "null"}
    branch = nullable["anyOf"][0]
    assert branch["properties"]["mode"] == {"type": "string", "enum": ["finish"]}
    assert branch["properties"]["evidence_goal"]["type"] == "null"
    assert set(branch["required"]) == set(decision["required"])
    assert {key: value for key, value in parameters["properties"].items()
            if key != "turn_decision"} == old_report["parameters"]["properties"]
    assert PublicTurnDecision(mode="finish", basis="The narrow public question is settled.",
                              evidence_goal=None).evidence_goal is None
    assert review.project_request(projected) == projected


def test_request_without_report_capability_is_not_rewritten(saved_request):
    saved_request["tools"] = [tool for tool in saved_request["tools"]
                              if tool["name"] != "report_discovery"]
    original = copy.deepcopy(saved_request)
    projected = review.project_request(saved_request)
    assert projected == original == saved_request
    assert projected is not saved_request


def test_first_and_followup_prepared_requests_share_projection_without_mutating_history(
    saved_request, tmp_path,
):
    journal = DevJournal(tmp_path, "run_dev_projection")
    gateway = SimpleNamespace(
        journal=journal, current_diff_hash="sha256:fixed", limits=DevLimits(),
        deadline=ExecutionDeadline.from_remaining(60),
    )
    store = ArtifactStore(tmp_path / "artifacts")
    with pytest.raises(ContractError, match="projected before freezing"):
        rollout.Session(saved_request, gateway, store, probe_identity={})
    assert journal.events() == []
    frozen = review.project_request(saved_request)
    session = rollout.Session(frozen, gateway, store, probe_identity={})
    _, first, _ = session.prepare_request()
    assert first == frozen
    assert session.seed == frozen and session.items == frozen["input"]
    # A newly appended normal-workflow state must receive the same projection;
    # preceding native observations and the caller's history are not rewritten.
    session.items.extend(copy.deepcopy(saved_request["input"][2:]))
    history = copy.deepcopy(session.items)
    session.new_provider_calls = 1
    _, later, _ = session.prepare_request()
    assert later == review.project_request({**frozen, "input": history})
    assert session.items == history and session.seed == frozen
    for item in later["input"]:
        if item.get("role") == "developer":
            envelope = json.loads(item["content"])
            if envelope.get("kind") == "harness_current_state":
                assert envelope["state"]["workflow_gate"] == "fixed_candidate_review"
    assert [item for item in later["input"] if item.get("type") == "function_call_output"] == [
        item for item in history if item.get("type") == "function_call_output"
    ]
