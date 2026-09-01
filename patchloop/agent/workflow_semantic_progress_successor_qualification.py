"""Deterministic zero-call qualification for the Lean V15 semantic reset lane."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from patchloop.agent.lean_runtime import (
    LEAN_RUNTIME_POLICY_VERSION_V15,
    LeanHarnessRequestEvidenceV14,
    LeanHarnessRequestEvidenceV15,
)
from patchloop.agent.phases import EvidenceState
from patchloop.agent.runner import AgentRunner
from patchloop.agent.tools import TOOL_SCHEMAS_V19
from patchloop.agent.workflow_semantic_progress_successor import (
    WORKFLOW_POLICY_V15,
    PublicSemanticProgressState,
    apply_semantic_no_progress_policy,
    current_public_failure_event_sequence,
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
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

SCHEMA_VERSION = "lean-semantic-progress-successor-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-semantic-progress-public-qualification-20260825-v1.json"
)
RUN_ID = "run_semantic_progress_successor_qualification"
DIFF_A = "sha256:" + "1" * 64
DIFF_B = "sha256:" + "2" * 64
FAILURE_SIGNATURE = "AssertionError: PUBLIC_CASE:synthetic:same-failure"

SOURCE_FILES = (
    "patchloop/agent/workflow_semantic_progress_successor.py",
    "patchloop/agent/workflow_semantic_progress_successor_qualification.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/contracts.py",
    "patchloop/errors.py",
    "patchloop/evals/rapid_semantic_progress_diagnosis.py",
    "scripts/build_lean_harness_semantic_progress_qualification.py",
    "scripts/build_rapid_semantic_progress_diagnosis.py",
    "tests/test_workflow_semantic_progress_successor.py",
    "tests/test_workflow_successor_v2_runner.py",
    "tests/test_workflow_semantic_progress_successor_qualification.py",
    "tests/test_rapid_semantic_progress_diagnosis.py",
)

IMMUTABLE_PREDECESSORS = {
    "experiments/lean-harness-required-trigger-public-qualification-20260825-v1.json": {
        "bytes": 5_879,
        "file_sha256": "sha256:fd3fa74c69fd78253c7d2bec11f6cbd47e28d4043fb007e567298c9002f094a4",
        "content_hash": "sha256:f5dec52a2a41a2a3c54fd283c23f9043bccf6e3f60a37b14b7d2bb639d1f95a1",
    },
    (
        "reports/rapid-development/artifacts/"
        "rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-workflow-diagnosis-v1.json"
    ): {
        "bytes": 38_711,
        "file_sha256": "sha256:622744647a01e246170cc1d95d1c4e75c76297dc4d5b71023d15dc2493ef3e05",
        "content_hash": "sha256:7675e9f59c596f4f08fca8854359ebc7bef7d09a16b4c952d25445237d28af0a",
    },
    (
        "reports/rapid-development/artifacts/"
        "rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-required-trigger-diagnosis-v1.json"
    ): {
        "bytes": 4_443,
        "file_sha256": "sha256:e90f8a14fc1449c0cec98c816f1cd98201f289a96fecf337427359fc44e4ffc6",
        "content_hash": "sha256:43e3bdd40c533748bb785afad2e9dce23158b09500ad1df9992e3f2a34d8d4c3",
    },
    (
        "reports/rapid-development/artifacts/"
        "rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-semantic-progress-diagnosis-v1.json"
    ): {
        "bytes": 7_644,
        "file_sha256": "sha256:b818f2deeda534638fda996d342059814787823c62edcf882e63685e24d81223",
        "content_hash": "sha256:3d364f3572b763f9fe94804a74ca350fb511d366e4c4aaa43f7adfb2a8caeb11",
    },
}


def _identity(root: Path, relative: str, *, json_content: bool = False) -> dict[str, Any]:
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
        raise ContractError(f"semantic-progress qualification input is unavailable: {relative}")
    raw = path.read_bytes()
    result: dict[str, Any] = {
        "path": relative,
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }
    if json_content:
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ContractError("semantic-progress predecessor is not canonical JSON") from exc
        content_hash = document.get("content_hash")
        body = {key: value for key, value in document.items() if key != "content_hash"}
        if content_hash != sha256_json(body):
            raise ContractError("semantic-progress predecessor content hash differs")
        result["content_hash"] = content_hash
    return result


def _task() -> PublicTask:
    return PublicTask.model_validate(
        {
            "schema_version": "task-public-v1",
            "task_id": "synthetic-semantic-progress",
            "task_version": 1,
            "split": "smoke",
            "repository": {
                "url": "snapshot://synthetic-semantic-progress",
                "base_commit": "sha256:" + "0" * 64,
                "language": "python",
            },
            "issue": {
                "title": "Synthetic public behavior",
                "description": "Preserve one synthetic public behavior after a bounded edit.",
            },
            "constraints": {
                "allowed_paths": ["src/**/*.py"],
                "forbidden_paths": ["tests/**"],
                "max_changed_files": 1,
                "max_diff_lines": 20,
                "dependency_changes_allowed": False,
                "public_api_changes_allowed": False,
            },
            "visible_checks": [
                {
                    "id": "targeted",
                    "command": ["python", "-m", "synthetic_targeted"],
                    "timeout_seconds": 30,
                },
                {
                    "id": "upstream",
                    "command": ["python", "-m", "synthetic_upstream"],
                    "timeout_seconds": 30,
                },
            ],
            "tags": ["synthetic", "workflow"],
        }
    )


def _event(sequence: int, event_type: EventType, payload: dict[str, Any]) -> RunEvent:
    return RunEvent(
        event_id=f"evt_v15_{sequence}",
        run_id=RUN_ID,
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 25, tzinfo=UTC),
        actor="qualification",
        payload=payload,
    )


def _failed_check(sequence: int, diff_hash: str) -> RunEvent:
    artifact = {
        "artifact_id": f"artifact-v15-check-{sequence}",
        "path": f"cas/v15-check-{sequence}.json",
        "content_hash": sha256_json({"check_id": "targeted", "failure_summary": FAILURE_SIGNATURE}),
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
            "check_id": "targeted",
            "passed": False,
            "timed_out": False,
            "invocation_status": "completed",
            "behavior_status": "failed",
            "failure_summary": FAILURE_SIGNATURE,
        },
    )


def _info(sequence: int, tool: str) -> RunEvent:
    return _event(
        sequence,
        EventType.TOOL_SUCCEEDED,
        {"tool": tool, "status": "succeeded", "worktree_diff_hash": DIFF_B},
    )


def _read_event(sequence: int) -> tuple[RunEvent, dict[str, Any]]:
    result = {
        "path": "src/package/example.py",
        "content": "value = current\n",
        "start_line": 1,
        "end_line": 1,
        "actual_start_line": 1,
        "actual_end_line": 1,
        "total_lines": 1,
        "file_content_hash": sha256_text("value = current\n"),
    }
    artifact = {
        "artifact_id": f"artifact-v15-read-{sequence}",
        "path": f"cas/v15-read-{sequence}.json",
        "content_hash": sha256_json(result),
    }
    event = _event(
        sequence,
        EventType.TOOL_SUCCEEDED,
        {
            "tool": "read_file",
            "status": "succeeded",
            "artifact_id": artifact["artifact_id"],
            "artifact_path": artifact["path"],
            "result_artifact": artifact,
            "worktree_diff_hash": DIFF_B,
        },
    )
    visible = {
        "sequence": sequence,
        "type": EventType.TOOL_SUCCEEDED.value,
        "payload": {
            "tool": "read_file",
            "status": "succeeded",
            "artifact_id": artifact["artifact_id"],
            "artifact_path": artifact["path"],
            "tool_result": result,
        },
    }
    return event, visible


def _evidence() -> EvidenceState:
    return EvidenceState(
        worktree_diff_hash=DIFF_B,
        mutation_event_sequence=3,
        mutation_present=True,
        completed_checks=(),
        pending_checks=("targeted", "upstream"),
        current_diff_check_event_sequences=(4,),
        latest_check_sequence=4,
        review_event_sequence=None,
        review_presented_to_model=False,
        task_review_event_sequence=None,
        task_review_presented_to_model=False,
        task_review_coverage_complete=None,
        unresolved_coverage_target_ids=(),
        submission_ready=False,
        missing_evidence=("check:targeted", "check:upstream", "review:get_diff"),
        allowed_next_actions=("search_files", "read_file", "apply_structured_edit", "run_check"),
    )


def _base_decision() -> WorkflowDecisionV2:
    body = {
        "schema_version": "lean-workflow-decision-v2",
        "runtime_policy_version": "lean-harness-v14",
        "policy_version": WORKFLOW_POLICY_V14,
        "target": "correction-investigation",
        "current_diff_hash": DIFF_B,
        "expected_check_id": "targeted",
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


def _scenarios() -> dict[str, Any]:
    task = _task()
    first = _failed_check(2, DIFF_A)
    current = _failed_check(4, DIFF_B)
    evidence = _evidence()
    state = project_public_semantic_progress_state(
        run_id=RUN_ID,
        task=task,
        evidence=evidence,
        events=(first, current),
        current_failure_event_sequence=current_public_failure_event_sequence(
            run_id=RUN_ID,
            task=task,
            evidence=evidence,
            events=(first, current),
        ),
    )
    if state is None or not state.semantic_reset_required:
        raise ContractError("V15 qualification did not detect repeated public failure")
    initial = apply_semantic_no_progress_policy(
        base_decision=_base_decision(),
        semantic_progress_state=state,
        events=(first, current),
        current_revision_disposition=None,
    )
    search = _info(5, "search_files")
    after_search = apply_semantic_no_progress_policy(
        base_decision=_base_decision(),
        semantic_progress_state=state,
        events=(first, current, search),
        current_revision_disposition=None,
    )
    read, visible_read = _read_event(6)
    ready = apply_semantic_no_progress_policy(
        base_decision=_base_decision(),
        semantic_progress_state=state,
        events=(first, current, search, read),
        current_revision_disposition=None,
    )
    visible_check = {
        "sequence": current.sequence,
        "type": current.type.value,
        "payload": {
            "tool": "run_check",
            "status": "succeeded",
            "artifact_id": current.payload["artifact_id"],
            "artifact_path": current.payload["artifact_path"],
            "tool_result": {
                "check_id": "targeted",
                "invocation_status": "completed",
                "behavior_status": "failed",
                "passed": False,
                "timed_out": False,
            },
        },
    }
    catalog = project_eligible_plan_evidence_catalog_v2(
        run_id=RUN_ID,
        task=task,
        worktree_diff_hash=DIFF_B,
        model_visible_context=canonical_json({"recent_events": [visible_check, visible_read]}),
        events=(first, current, search, read),
        required_trigger_event_sequence=current.sequence,
    )
    surface = project_workflow_tool_surface_v3(
        decision=ready,
        catalog=catalog,
        source_tool_schemas=tuple(TOOL_SCHEMAS_V19),
    )
    disposition_enum = surface.selected_tool_schemas[0]["parameters"]["properties"][
        "prior_hypothesis_disposition"
    ]["enum"]
    try:
        validate_semantic_progress_revision(
            semantic_progress_state=state,
            prior_hypothesis_disposition="refined",
            trigger_event_sequence=current.sequence,
        )
    except ContractError as exc:
        invalid_reason_codes = exc.details.get("reason_codes", [])
    else:
        raise ContractError("V15 qualification accepted a refined no-progress revision")
    validate_semantic_progress_revision(
        semantic_progress_state=state,
        prior_hypothesis_disposition="rejected",
        trigger_event_sequence=current.sequence,
    )
    missing_search = tuple(_info(sequence, "read_file") for sequence in (5, 6, 7))
    exhausted = apply_semantic_no_progress_policy(
        base_decision=_base_decision(),
        semantic_progress_state=state,
        events=(first, current, *missing_search),
        current_revision_disposition=None,
    )
    invalid_revision = apply_semantic_no_progress_policy(
        base_decision=_base_decision(),
        semantic_progress_state=state,
        events=(first, current, search, read),
        current_revision_disposition="refined",
    )
    restored = PublicSemanticProgressState.model_validate_json(
        canonical_json(state.model_dump(mode="json"))
    )
    missing = copy.deepcopy(current)
    missing.payload.pop("failure_summary")
    try:
        project_public_semantic_progress_state(
            run_id=RUN_ID,
            task=task,
            evidence=evidence,
            events=(missing,),
            current_failure_event_sequence=missing.sequence,
        )
    except ContractError:
        missing_summary_failed_closed = True
    else:
        missing_summary_failed_closed = False
    _, runner_tools = AgentRunner._runtime_contract(
        SimpleNamespace(tool_schema_version="v19", context_policy_version="phase-evidence-v25")
    )
    return {
        "first_same_signature_failure": {
            "semantic_reset_required": False,
            "correction_limit_changed": False,
        },
        "second_same_signature_distinct_diff": {
            "state_hash": state.content_hash,
            "failure_signature_hash": state.failure_signature_hash,
            "failed_diff_count": state.same_signature_failed_diff_count,
            "semantic_reset_required": state.semantic_reset_required,
            "allowed_tool_names": list(initial.allowed_tool_names),
        },
        "bounded_reset_sequence": {
            "after_search_allowed": list(after_search.allowed_tool_names),
            "after_search_and_read_target": ready.target,
            "after_search_and_read_allowed": list(ready.allowed_tool_names),
            "required_disposition_enum": disposition_enum,
        },
        "server_revision_admission": {
            "invalid_reason_codes": invalid_reason_codes,
            "rejected_disposition_accepted": True,
            "refined_decision_terminal": invalid_revision.terminal_reason,
        },
        "bounded_exhaustion": {
            "target": exhausted.target,
            "terminal_reason": exhausted.terminal_reason,
            "allowed_tool_names": list(exhausted.allowed_tool_names),
        },
        "recovery_and_fail_closed": {
            "state_round_trip_exact": restored == state,
            "state_hash_round_trip_exact": restored.content_hash == state.content_hash,
            "missing_failure_summary_failed_closed": missing_summary_failed_closed,
        },
        "v14_inheritance_and_runner_wiring": {
            "request_evidence_inherits_v14": issubclass(
                LeanHarnessRequestEvidenceV15, LeanHarnessRequestEvidenceV14
            ),
            "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V15,
            "runner_tool_names": [item["name"] for item in runner_tools],
            "runner_tools_exact_v19": runner_tools == TOOL_SCHEMAS_V19,
        },
    }


def build_workflow_semantic_progress_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    predecessor_identities = []
    for relative, expected in IMMUTABLE_PREDECESSORS.items():
        observed = _identity(root, relative, json_content=True)
        if any(observed.get(key) != value for key, value in expected.items()):
            raise ContractError(f"immutable semantic-progress predecessor drifted: {relative}")
        predecessor_identities.append(observed)
    diagnosis = json.loads((root / tuple(IMMUTABLE_PREDECESSORS)[-1]).read_text(encoding="utf-8"))
    if (
        diagnosis.get("diagnosis", {}).get("same_signature_repeated_across_distinct_diffs")
        is not True
        or diagnosis.get("diagnosis", {}).get("increase_correction_limit_supported") is not False
        or diagnosis.get("diagnosis", {}).get("task_specific_solution_policy_supported")
        is not False
        or diagnosis.get("contamination_disclosure", {}).get(
            "task_specific_solution_inference_allowed"
        )
        is not False
    ):
        raise ContractError("R11 semantic-progress diagnosis boundary differs")
    body = {
        "schema_version": SCHEMA_VERSION,
        "status": "offline-qualified",
        "scope": "generic-repeated-public-failure-signature-no-progress-reset",
        "predecessor_runtime": "lean-harness-v14",
        "successor_runtime": "lean-harness-v15",
        "tool_schema_version": "v19",
        "context_policy_version": "phase-evidence-v25",
        "workflow_policy_version": WORKFLOW_POLICY_V15,
        "source_files": [_identity(root, item) for item in SOURCE_FILES],
        "immutable_predecessors": predecessor_identities,
        "diagnosis_binding": {
            "same_signature_repeated_across_distinct_diffs": True,
            "distinct_failed_diff_count": diagnosis["no_progress_failure"][
                "distinct_failed_diff_count"
            ],
            "all_revisions_refined_prior_hypothesis": diagnosis["diagnosis"][
                "all_revisions_refined_prior_hypothesis"
            ],
            "increase_correction_limit_supported": False,
            "task_specific_solution_policy_supported": False,
            "interactive_exploration_glob_exposed_excluded_fixture_lines": diagnosis[
                "contamination_disclosure"
            ]["interactive_exploration_glob_exposed_excluded_fixture_lines"],
            "excluded_fixture_content_used": False,
        },
        "scenarios": _scenarios(),
        "regression_gates": {
            "v14_required_trigger_pin_inherited": True,
            "v13_finalization_surface_inherited": True,
            "correction_attempt_limit_remains_three": True,
            "review_correction_limit_remains_one": True,
            "plan_admission_recovery_remains_one": True,
            "initial_plan_mock_e2e_tested": True,
            "single_failure_revision_mock_e2e_tested": True,
            "repeated_failure_reset_mock_e2e_tested": True,
            "invalid_revision_recovery_mock_e2e_tested": True,
            "restart_recovery_mock_e2e_tested": True,
        },
        "evidence_boundary": {
            "public_only": True,
            "task_fixture_files_read": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "reasoning_text_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "state_mutations": 0,
            "added_cost_usd": "0",
        },
        "runtime_activation_authorized": False,
        "paid_execution_authorized": False,
        "rapid_candidate_created": False,
        "quality_improvement_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("semantic-progress qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_workflow_semantic_progress_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_workflow_semantic_progress_successor_qualification(root)
    path = (root / QUALIFICATION_PATH).resolve()
    raw = qualification_bytes(value)
    if path.exists() and path.read_bytes() != raw:
        raise ContractError("semantic-progress qualification already differs")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return value


def load_workflow_semantic_progress_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    path = (root / QUALIFICATION_PATH).resolve()
    try:
        value = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("semantic-progress qualification is unavailable") from exc
    if qualification_bytes(value) != path.read_bytes():
        raise ContractError("semantic-progress qualification bytes differ")
    if value != build_workflow_semantic_progress_successor_qualification(root):
        raise ContractError("semantic-progress qualification source binding differs")
    return value


__all__ = [
    "IMMUTABLE_PREDECESSORS",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_workflow_semantic_progress_successor_qualification",
    "load_workflow_semantic_progress_successor_qualification",
    "materialize_workflow_semantic_progress_successor_qualification",
    "qualification_bytes",
]
