from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from patchloop.agent.phases import EvidenceState
from patchloop.agent.tools import TOOL_SCHEMAS_V19
from patchloop.agent.workflow_semantic_progress_successor import (
    WORKFLOW_POLICY_V15,
    WorkflowDecisionV3,
    apply_semantic_no_progress_policy,
    project_public_semantic_progress_state,
    project_workflow_tool_surface_v3,
    validate_semantic_progress_revision,
)
from patchloop.agent.workflow_successor_v2 import (
    WORKFLOW_POLICY_V14,
    WorkflowDecisionV2,
    project_eligible_plan_evidence_catalog_v2,
)
from patchloop.contracts import EventType, PublicTask, RunEvent
from patchloop.errors import ContractError
from patchloop.util import load_unique_yaml, sha256_json, sha256_text

ROOT = Path(__file__).resolve().parents[1]
TASK = PublicTask.model_validate(
    load_unique_yaml(
        (ROOT / "fixtures/task-packages/anyio-interrupt-runner-cleanup-v4/public.yaml").read_text(
            encoding="utf-8"
        )
    )
)
RUN_ID = "run_semantic_progress"
DIFF_A = "sha256:" + "1" * 64
DIFF_B = "sha256:" + "2" * 64
FAILURE = "AssertionError: PUBLIC_CASE:generic:same-failure"


def _event(sequence: int, event_type: EventType, payload: dict | None = None) -> RunEvent:
    return RunEvent(
        event_id=f"evt_{sequence}",
        run_id=RUN_ID,
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 25, tzinfo=UTC),
        actor="test",
        correlation_id=None,
        payload=payload or {},
    )


def _failed_check(sequence: int, diff_hash: str, summary: str = FAILURE) -> RunEvent:
    artifact = {
        "artifact_id": f"artifact-{sequence}",
        "path": f"cas/{sequence}.json",
        "content_hash": sha256_json({"failure_summary": summary}),
    }
    return _event(
        sequence,
        EventType.TOOL_SUCCEEDED,
        {
            "tool": "run_check",
            "status": "succeeded",
            "artifact_id": artifact["artifact_id"],
            "artifact_path": artifact["path"],
            "result_artifact": artifact,
            "worktree_diff_hash": diff_hash,
            "check_id": TASK.visible_checks[0].id,
            "passed": False,
            "invocation_status": "completed",
            "behavior_status": "failed",
            "failure_summary": summary,
            "timed_out": False,
        },
    )


def _info(sequence: int, tool: str, diff_hash: str) -> RunEvent:
    return _event(
        sequence,
        EventType.TOOL_SUCCEEDED,
        {"tool": tool, "status": "succeeded", "worktree_diff_hash": diff_hash},
    )


def _evidence(diff_hash: str) -> EvidenceState:
    return EvidenceState(
        worktree_diff_hash=diff_hash,
        mutation_event_sequence=3,
        mutation_present=True,
        completed_checks=(),
        pending_checks=tuple(check.id for check in TASK.visible_checks),
        current_diff_check_event_sequences=(),
        latest_check_sequence=None,
        review_event_sequence=None,
        review_presented_to_model=False,
        task_review_event_sequence=None,
        task_review_presented_to_model=False,
        task_review_coverage_complete=None,
        unresolved_coverage_target_ids=(),
        submission_ready=False,
        missing_evidence=(),
        allowed_next_actions=("search_files", "read_file", "apply_structured_edit", "run_check"),
    )


def _base_decision() -> WorkflowDecisionV2:
    body = {
        "schema_version": "lean-workflow-decision-v2",
        "runtime_policy_version": "lean-harness-v14",
        "policy_version": WORKFLOW_POLICY_V14,
        "target": "correction-investigation",
        "current_diff_hash": DIFF_B,
        "expected_check_id": TASK.visible_checks[0].id,
        "allowed_tool_names": ("search_files", "read_file", "revise_work_plan"),
        "information_actions_in_episode": 0,
        "fresh_current_read": False,
        "corrective_mutations_for_check": 1,
        "review_corrections_used": 0,
        "pre_mutation_actions_used": 4,
        "active_plan_hash": "sha256:" + "3" * 64,
        "plan_gate_id": "sha256:" + "4" * 64,
        "plan_admission_recovery_used": False,
        "plan_admission_recovery_remaining": 1,
        "required_trigger_evidence_id": "pev:4",
        "revision_trigger": "check_failure",
        "terminal_reason": None,
        "configured_max_output_tokens": 12_288,
        "effective_max_output_tokens": 4_096,
        "reasoning_effort": "low",
        "parallel_tool_calls": False,
        "one_tool_call_per_response": True,
        "provider_calls_authorized": False,
    }
    return WorkflowDecisionV2.model_validate({**body, "content_hash": sha256_json(body)})


def _visible_check(event: RunEvent) -> dict:
    return {
        "sequence": event.sequence,
        "type": event.type.value,
        "payload": {
            "tool": "run_check",
            "status": "succeeded",
            "artifact_id": event.payload["artifact_id"],
            "artifact_path": event.payload["artifact_path"],
            "tool_result": {
                "check_id": event.payload["check_id"],
                "invocation_status": "completed",
                "behavior_status": "failed",
                "passed": False,
                "timed_out": False,
                "failure_summary": event.payload["failure_summary"],
            },
        },
    }


def _visible_read(event: RunEvent) -> dict:
    artifact = {
        "artifact_id": f"artifact-{event.sequence}",
        "path": f"cas/{event.sequence}.json",
        "content_hash": sha256_json({"path": "src/anyio/pytest_plugin.py"}),
    }
    event.payload.update(
        {
            "artifact_id": artifact["artifact_id"],
            "artifact_path": artifact["path"],
            "result_artifact": artifact,
        }
    )
    return {
        "sequence": event.sequence,
        "type": event.type.value,
        "payload": {
            "tool": "read_file",
            "status": "succeeded",
            "artifact_id": artifact["artifact_id"],
            "artifact_path": artifact["path"],
            "tool_result": {
                "path": "src/anyio/pytest_plugin.py",
                "content": "line 20\n",
                "start_line": 20,
                "end_line": 20,
                "actual_start_line": 20,
                "actual_end_line": 20,
                "total_lines": 100,
                "file_content_hash": "sha256:" + "5" * 64,
            },
        },
    }


def test_same_signature_on_two_diffs_requires_bounded_hypothesis_reset() -> None:
    first = _failed_check(2, DIFF_A)
    current = _failed_check(4, DIFF_B)
    state = project_public_semantic_progress_state(
        run_id=RUN_ID,
        task=TASK,
        evidence=_evidence(DIFF_B),
        events=(first, current),
        current_failure_event_sequence=4,
    )
    assert state is not None
    assert state.same_signature_failed_diff_count == 2
    assert state.semantic_reset_required is True
    assert state.failure_signature_hash == sha256_text(FAILURE)

    initial = apply_semantic_no_progress_policy(
        base_decision=_base_decision(),
        semantic_progress_state=state,
        events=(first, current),
        current_revision_disposition=None,
    )
    assert isinstance(initial, WorkflowDecisionV3)
    assert initial.policy_version == WORKFLOW_POLICY_V15
    assert initial.allowed_tool_names == ("search_files", "read_file")
    assert initial.required_prior_hypothesis_disposition == "rejected"

    searched = _info(5, "search_files", DIFF_B)
    after_search = apply_semantic_no_progress_policy(
        base_decision=_base_decision(),
        semantic_progress_state=state,
        events=(first, current, searched),
        current_revision_disposition=None,
    )
    assert after_search.allowed_tool_names == ("read_file",)

    read = _info(6, "read_file", DIFF_B)
    ready = apply_semantic_no_progress_policy(
        base_decision=_base_decision(),
        semantic_progress_state=state,
        events=(first, current, searched, read),
        current_revision_disposition=None,
    )
    assert ready.target == "revise-work-plan"
    assert ready.allowed_tool_names == ("revise_work_plan",)
    assert ready.fresh_current_read is True


def test_reset_revision_schema_and_server_both_require_rejected_disposition() -> None:
    first = _failed_check(2, DIFF_A)
    current = _failed_check(4, DIFF_B)
    searched = _info(5, "search_files", DIFF_B)
    read = _info(6, "read_file", DIFF_B)
    state = project_public_semantic_progress_state(
        run_id=RUN_ID,
        task=TASK,
        evidence=_evidence(DIFF_B),
        events=(first, current, searched, read),
        current_failure_event_sequence=4,
    )
    assert state is not None
    decision = apply_semantic_no_progress_policy(
        base_decision=_base_decision(),
        semantic_progress_state=state,
        events=(first, current, searched, read),
        current_revision_disposition=None,
    )
    visible_read = _visible_read(read)
    catalog = project_eligible_plan_evidence_catalog_v2(
        run_id=RUN_ID,
        task=TASK,
        worktree_diff_hash=DIFF_B,
        model_visible_context=json.dumps(
            {"recent_events": [_visible_check(current), visible_read]}
        ),
        events=(first, current, searched, read),
        required_trigger_event_sequence=4,
    )
    surface = project_workflow_tool_surface_v3(
        decision=decision,
        catalog=catalog,
        source_tool_schemas=tuple(TOOL_SCHEMAS_V19),
    )
    revise = surface.selected_tool_schemas[0]
    assert revise["name"] == "revise_work_plan"
    assert revise["parameters"]["properties"]["prior_hypothesis_disposition"]["enum"] == [
        "rejected"
    ]
    with pytest.raises(ContractError, match="must reject"):
        validate_semantic_progress_revision(
            semantic_progress_state=state,
            prior_hypothesis_disposition="refined",
            trigger_event_sequence=4,
        )
    validate_semantic_progress_revision(
        semantic_progress_state=state,
        prior_hypothesis_disposition="rejected",
        trigger_event_sequence=4,
    )


def test_reset_fails_closed_when_three_information_actions_lack_search() -> None:
    first = _failed_check(2, DIFF_A)
    current = _failed_check(4, DIFF_B)
    reads = tuple(_info(sequence, "read_file", DIFF_B) for sequence in (5, 6, 7))
    state = project_public_semantic_progress_state(
        run_id=RUN_ID,
        task=TASK,
        evidence=_evidence(DIFF_B),
        events=(first, current, *reads),
        current_failure_event_sequence=4,
    )
    assert state is not None
    decision = apply_semantic_no_progress_policy(
        base_decision=_base_decision(),
        semantic_progress_state=state,
        events=(first, current, *reads),
        current_revision_disposition=None,
    )
    assert decision.target == "terminal"
    assert decision.terminal_reason == "semantic_no_progress_evidence_exhausted"
    assert decision.allowed_tool_names == ()


def test_missing_public_failure_summary_fails_closed() -> None:
    event = _failed_check(4, DIFF_B)
    event.payload.pop("failure_summary")
    with pytest.raises(ContractError, match="failure summary"):
        project_public_semantic_progress_state(
            run_id=RUN_ID,
            task=TASK,
            evidence=_evidence(DIFF_B),
            events=(event,),
            current_failure_event_sequence=4,
        )
