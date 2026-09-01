"""Public-only diagnosis of R11 semantic no-progress behavior.

The projector reads only the consumed public workflow diagnosis, durable public
events, and the exact request/check artifacts referenced by those events.  It
does not inspect task fixtures, evaluator output, hidden data, reference patches,
or model response/reasoning text.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from patchloop.agent.lean_runtime import validate_persisted_lean_harness_request
from patchloop.agent.workflow_successor_v2 import RecordedWorkPlanV2
from patchloop.contracts import EventType, RunEvent
from patchloop.errors import ContractError
from patchloop.evals.rapid_workflow_diagnosis import _artifact_json
from patchloop.trace_view import ReadOnlyTraceStore
from patchloop.util import canonical_json, sha256_json, sha256_text

SCHEMA_VERSION = "rapid-semantic-progress-diagnosis-v1"
R11_DIAGNOSIS_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-workflow-diagnosis-v1.json"
)
R11_SUCCESS_RUN_ID = "run_rapid_v17_c64654b6bdba_02"
R11_NO_PROGRESS_RUN_ID = "run_rapid_v17_c64654b6bdba_03"


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _validated_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("semantic-progress diagnosis input is invalid") from exc
    if type(value) is not dict:
        raise ContractError("semantic-progress diagnosis input is not an object")
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("semantic-progress diagnosis input hash differs")
    return value


def _selected_row(diagnosis: dict[str, Any], *, order: int, run_id: str) -> dict[str, Any]:
    rows = diagnosis.get("rows")
    if not isinstance(rows, list):
        raise ContractError("semantic-progress diagnosis rows are unavailable")
    selected = [row for row in rows if row.get("order") == order and row.get("run_id") == run_id]
    if len(selected) != 1:
        raise ContractError("semantic-progress diagnosis row identity differs")
    return selected[0]


def _request_evidence(event: RunEvent, *, state_path: Path):
    path = event.payload.get("request_artifact_path")
    digest = event.payload.get("request_artifact_hash")
    if not isinstance(path, str) or not isinstance(digest, str):
        raise ContractError(f"semantic-progress request artifact is absent at {event.sequence}")
    ref_event = event.model_copy(
        update={
            "payload": {
                **event.payload,
                "request_ref": {"path": path, "content_hash": digest},
            }
        }
    )
    document = _artifact_json(ref_event, state_path=state_path, field="request_ref")
    if document is None:
        raise ContractError(f"semantic-progress request artifact is invalid at {event.sequence}")
    evidence = validate_persisted_lean_harness_request(document)
    if evidence.runtime_policy_version != "lean-harness-v12":
        raise ContractError("semantic-progress diagnosis selected a non-V12 request")
    return evidence


def _next_model_event(events: tuple[RunEvent, ...], after_sequence: int) -> RunEvent:
    selected = next(
        (
            event
            for event in events
            if event.sequence > after_sequence and event.type == EventType.MODEL_CALLED
        ),
        None,
    )
    if selected is None:
        raise ContractError("semantic-progress correction lacks a model request")
    return selected


def _plan(event: RunEvent) -> RecordedWorkPlanV2:
    try:
        plan = RecordedWorkPlanV2.model_validate_json(canonical_json(event.payload.get("plan")))
    except ValueError as exc:
        raise ContractError("semantic-progress durable plan is invalid") from exc
    if event.payload.get("plan_hash") != plan.content_hash:
        raise ContractError("semantic-progress durable plan hash differs")
    return plan


def build_rapid_semantic_progress_diagnosis(
    *,
    repository_root: str | Path = ".",
    state_path: str | Path = ".patchloop/state.sqlite3",
) -> dict[str, Any]:
    """Build deterministic evidence for the observed repeated-signature class."""

    root = Path(repository_root).resolve()
    diagnosis_path = (root / R11_DIAGNOSIS_PATH).resolve()
    state = (root / state_path).resolve()
    if not diagnosis_path.is_relative_to(root) or not state.is_relative_to(root):
        raise ContractError("semantic-progress diagnosis inputs escape the repository")
    diagnosis = _validated_json(diagnosis_path)
    success_row = _selected_row(diagnosis, order=2, run_id=R11_SUCCESS_RUN_ID)
    failure_row = _selected_row(diagnosis, order=3, run_id=R11_NO_PROGRESS_RUN_ID)
    store = ReadOnlyTraceStore(state)
    success_events = tuple(store.list_events(R11_SUCCESS_RUN_ID))
    failure_events = tuple(store.list_events(R11_NO_PROGRESS_RUN_ID))
    if [event.sequence for event in success_events] != list(range(1, 97)):
        raise ContractError("R11 success-control sequence differs")
    if [event.sequence for event in failure_events] != list(range(1, 150)):
        raise ContractError("R11 semantic-progress sequence differs")

    failed_checks = [
        event
        for event in failure_events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        and event.payload.get("invocation_status") == "completed"
        and event.payload.get("behavior_status") == "failed"
    ]
    if [event.sequence for event in failed_checks] != [52, 80, 113, 146]:
        raise ContractError("R11 semantic-progress failed-check order differs")
    failure_rows: list[dict[str, Any]] = []
    summary_tails: list[str] = []
    for event in failed_checks:
        artifact = _artifact_json(event, state_path=state, field="result_artifact")
        if artifact is None or artifact.get("public_visible_only") is not True:
            raise ContractError("R11 semantic-progress check artifact is not public")
        summary = artifact.get("failure_summary")
        if not isinstance(summary, str) or not summary.strip():
            raise ContractError("R11 semantic-progress check lacks a public summary")
        lines = [line.strip() for line in summary.replace("\r\n", "\n").split("\n") if line.strip()]
        tail = lines[-1]
        summary_tails.append(tail)
        failure_rows.append(
            {
                "event_sequence": event.sequence,
                "worktree_diff_hash": event.payload.get("worktree_diff_hash"),
                "result_artifact_hash": event.payload["result_artifact"].get("content_hash"),
                "failure_signature": tail,
                "failure_signature_hash": sha256_text(tail),
                "stderr_hash": artifact.get("stderr_hash"),
                "truncated": artifact.get("truncated"),
                "public_visible_only": True,
            }
        )
    signature_hashes = {row["failure_signature_hash"] for row in failure_rows}
    stderr_hashes = {row["stderr_hash"] for row in failure_rows}
    diff_hashes = {row["worktree_diff_hash"] for row in failure_rows}
    if len(signature_hashes) != 1 or len(stderr_hashes) != 1 or len(diff_hashes) != 4:
        raise ContractError("R11 semantic-progress failure signature differs")

    correction_failures = failed_checks[:-1]
    request_visibility: list[dict[str, Any]] = []
    for event, tail in zip(correction_failures, summary_tails[:-1], strict=True):
        model_event = _next_model_event(failure_events, event.sequence)
        request = _request_evidence(model_event, state_path=state)
        request_body = canonical_json(request.request_body)
        item = next(
            (
                candidate
                for candidate in request.eligible_plan_evidence_catalog.items
                if candidate.canonical_event_sequence == event.sequence
            ),
            None,
        )
        if item is None or item.check is None:
            raise ContractError("R11 semantic-progress request lacks check evidence")
        check_projection = item.check.model_dump(mode="json")
        request_visibility.append(
            {
                "failed_check_sequence": event.sequence,
                "model_event_sequence": model_event.sequence,
                "request_artifact_hash": model_event.payload.get("request_artifact_hash"),
                "failure_signature_occurrences": request_body.count(tail),
                "failure_signature_visible": tail in request_body,
                "catalog_check_fields": sorted(check_projection),
                "catalog_has_failure_signature": any(
                    key in check_projection
                    for key in ("failure_signature", "failure_signature_hash", "failure_summary")
                ),
                "semantic_progress_state_present": "semantic_progress_state" in request_body,
            }
        )
    if not all(row["failure_signature_visible"] for row in request_visibility):
        raise ContractError("R11 semantic-progress signature was not model-visible")
    if any(
        row["catalog_has_failure_signature"] or row["semantic_progress_state_present"]
        for row in request_visibility
    ):
        raise ContractError("R11 semantic-progress structure unexpectedly exists")

    plan_events = [
        event
        for event in failure_events
        if event.type == EventType.PLAN_RECORDED
        and event.payload.get("schema_version") == "plan-recorded-event-v2"
    ]
    plans = [_plan(event) for event in plan_events]
    revisions = [plan for plan in plans if plan.trigger == "check_failure"]
    if [event.sequence for event in plan_events] != [22, 67, 100, 133]:
        raise ContractError("R11 semantic-progress plan order differs")
    if [plan.prior_hypothesis_disposition for plan in revisions] != [
        "refined",
        "refined",
        "refined",
    ]:
        raise ContractError("R11 semantic-progress dispositions differ")
    revision_rows = [
        {
            "revision_index": plan.revision_index,
            "plan_hash": plan.content_hash,
            "parent_plan_hash": plan.parent_plan_hash,
            "trigger_event_sequence": plan.trigger_event_sequence,
            "prior_hypothesis_disposition": plan.prior_hypothesis_disposition,
            "candidate_files": [item.path for item in plan.candidate_files],
            "hypothesis_hash": sha256_text(plan.hypothesis),
            "intended_change_hash": sha256_text(plan.intended_change),
        }
        for plan in revisions
    ]
    patch_sequences = [
        event.sequence for event in failure_events if event.type == EventType.PATCH_APPLIED
    ]
    if patch_sequences != [46, 75, 108, 141]:
        raise ContractError("R11 semantic-progress patch order differs")

    success_plans = [
        _plan(event)
        for event in success_events
        if event.type == EventType.PLAN_RECORDED
        and event.payload.get("schema_version") == "plan-recorded-event-v2"
    ]
    if len(success_plans) != 1:
        raise ContractError("R11 success-control plan count differs")
    success_checks = success_row["visible_checks"]["invocations"]
    if [row.get("passed") for row in success_checks] != [True, True]:
        raise ContractError("R11 success-control check result differs")

    body = {
        "schema_version": SCHEMA_VERSION,
        "official": False,
        "scope": "single-r11-v12-repeated-public-failure-signature-class",
        "source_diagnosis": {
            "path": R11_DIAGNOSIS_PATH.as_posix(),
            "bytes": diagnosis_path.stat().st_size,
            "file_sha256": _file_sha256(diagnosis_path),
            "content_hash": diagnosis["content_hash"],
        },
        "source_trace": {
            "path": state.relative_to(root).as_posix(),
            "read_only_immutable_sqlite": True,
            "state_mutated": False,
        },
        "success_control": {
            "order": success_row["order"],
            "run_id": R11_SUCCESS_RUN_ID,
            "patch_applied_count": success_row["edit_path"]["patch_applied"],
            "first_mutation_read_files": success_row["first_mutation_evidence"]["read_files"],
            "first_mutation_search_calls": success_row["first_mutation_evidence"]["search_calls"],
            "first_mutation_read_calls": success_row["first_mutation_evidence"]["read_calls"],
            "initial_plan_candidate_files": [
                item.path for item in success_plans[0].candidate_files
            ],
            "targeted_then_upstream_passed": True,
            "submission_completed": success_row["submission_completed"],
        },
        "no_progress_failure": {
            "order": failure_row["order"],
            "run_id": R11_NO_PROGRESS_RUN_ID,
            "failed_checks": failure_rows,
            "distinct_failed_diff_count": len(diff_hashes),
            "single_failure_signature_across_all_diffs": True,
            "request_visibility": request_visibility,
            "patch_applied_sequences": patch_sequences,
            "revision_sequences": [event.sequence for event in plan_events[1:]],
            "revisions": revision_rows,
            "rejected_revision_count": sum(
                plan.prior_hypothesis_disposition == "rejected" for plan in revisions
            ),
            "terminal_error_code": failure_row["terminal_attribution"]["error_code"],
        },
        "diagnosis": {
            "failure_signature_was_model_visible": True,
            "failure_signature_was_structurally_pinned": False,
            "same_signature_repeated_across_distinct_diffs": True,
            "all_revisions_refined_prior_hypothesis": True,
            "semantic_no_progress_was_not_structured": True,
            "insufficient_failure_visibility_supported": False,
            "increase_correction_limit_supported": False,
            "task_specific_solution_policy_supported": False,
            "next_successor_scope": "bounded-public-failure-signature-and-no-progress-reset",
            "live_candidate_ready": False,
        },
        "evidence_boundary": {
            "accepted_inputs": [
                R11_DIAGNOSIS_PATH.as_posix(),
                state.relative_to(root).as_posix(),
                ".patchloop/artifacts/objects/sha256/<public-event-bound-cas>",
            ],
            "public_tool_and_structured_plan_data_only": True,
            "task_fixture_files_read": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "reasoning_text_read": False,
            "llm_response_text_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "state_mutations": 0,
            "added_cost_nanos": 0,
        },
        "contamination_disclosure": {
            "interactive_exploration_glob_exposed_excluded_fixture_lines": True,
            "excluded_fixture_content_used_by_this_projector": False,
            "task_specific_solution_inference_allowed": False,
            "successor_scope_must_remain_generic_workflow_policy": True,
        },
    }
    return {**body, "content_hash": sha256_json(body)}


def diagnosis_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("semantic-progress diagnosis content hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


__all__ = [
    "R11_DIAGNOSIS_PATH",
    "SCHEMA_VERSION",
    "build_rapid_semantic_progress_diagnosis",
    "diagnosis_bytes",
]
