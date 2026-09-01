"""Public-only diagnosis of the R11 failed-check trigger eviction.

The projector reads the consumed R11 public diagnosis and exact persisted
request evidence from the trace store.  It emits only typed workflow/catalog
metadata: no model response text, reasoning text, evaluator content, private
task data, or reference patch is inspected or copied into the result.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from patchloop.agent.lean_runtime import validate_persisted_lean_harness_request
from patchloop.contracts import EventType, RunEvent
from patchloop.errors import ContractError
from patchloop.evals.rapid_workflow_diagnosis import _artifact_json
from patchloop.trace_view import ReadOnlyTraceStore
from patchloop.util import canonical_json, sha256_json

SCHEMA_VERSION = "rapid-required-trigger-diagnosis-v1"
R11_DIAGNOSIS_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-workflow-diagnosis-v1.json"
)
R11_ROW3_RUN_ID = "run_rapid_v17_c64654b6bdba_03"
R11_ROW6_RUN_ID = "run_rapid_v17_c64654b6bdba_06"


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _validated_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("required-trigger diagnosis input is invalid") from exc
    if type(value) is not dict:
        raise ContractError("required-trigger diagnosis input is not an object")
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("required-trigger diagnosis input hash differs")
    return value


def _request_evidence(event: RunEvent, *, state_path: Path):
    path = event.payload.get("request_artifact_path")
    digest = event.payload.get("request_artifact_hash")
    if not isinstance(path, str) or not isinstance(digest, str):
        raise ContractError(f"model request artifact is absent at {event.sequence}")
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
        raise ContractError(f"model request artifact is invalid at {event.sequence}")
    evidence = validate_persisted_lean_harness_request(document)
    if evidence.runtime_policy_version != "lean-harness-v12":
        raise ContractError("required-trigger diagnosis selected a non-V12 request")
    return evidence


def _request_sample(event: RunEvent, *, state_path: Path, trigger_sequence: int) -> dict[str, Any]:
    evidence = _request_evidence(event, state_path=state_path)
    decision = evidence.workflow_decision
    catalog = evidence.eligible_plan_evidence_catalog
    item_ids = tuple(item.evidence_id for item in catalog.items)
    return {
        "model_event_sequence": event.sequence,
        "request_artifact_hash": event.payload["request_artifact_hash"],
        "workflow_target": decision.target,
        "workflow_decision_hash": decision.content_hash,
        "information_actions_in_episode": decision.information_actions_in_episode,
        "fresh_current_read": decision.fresh_current_read,
        "allowed_tool_names": list(decision.allowed_tool_names),
        "required_trigger_evidence_id": decision.required_trigger_evidence_id,
        "catalog_hash": catalog.content_hash,
        "catalog_has_trigger": f"pev:{trigger_sequence}" in item_ids,
        "recent_context_has_trigger": (
            trigger_sequence in catalog.model_visible_recent_event_sequences
        ),
    }


def _selected_row(diagnosis: dict[str, Any], *, order: int, run_id: str) -> dict[str, Any]:
    rows = diagnosis.get("rows")
    if not isinstance(rows, list):
        raise ContractError("R11 diagnosis rows are unavailable")
    selected = [row for row in rows if row.get("order") == order and row.get("run_id") == run_id]
    if len(selected) != 1:
        raise ContractError("R11 diagnosis row identity differs")
    return selected[0]


def build_rapid_required_trigger_diagnosis(
    *,
    repository_root: str | Path = ".",
    state_path: str | Path = ".patchloop/state.sqlite3",
) -> dict[str, Any]:
    """Build deterministic evidence for the one observed V12 request-loop class."""

    root = Path(repository_root).resolve()
    diagnosis_path = (root / R11_DIAGNOSIS_PATH).resolve()
    state = (root / state_path).resolve()
    if not diagnosis_path.is_relative_to(root) or not state.is_relative_to(root):
        raise ContractError("required-trigger diagnosis inputs escape the repository")
    diagnosis = _validated_json(diagnosis_path)
    row3 = _selected_row(diagnosis, order=3, run_id=R11_ROW3_RUN_ID)
    row6 = _selected_row(diagnosis, order=6, run_id=R11_ROW6_RUN_ID)
    store = ReadOnlyTraceStore(state)
    row3_events = store.list_events(R11_ROW3_RUN_ID)
    row6_events = store.list_events(R11_ROW6_RUN_ID)
    if [event.sequence for event in row6_events] != list(range(1, 304)):
        raise ContractError("R11 row 6 durable sequence differs")
    if row6_events[-1].type != EventType.RUN_FAILED:
        raise ContractError("R11 row 6 terminal differs")

    failed_checks = [
        event
        for event in row6_events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        and event.payload.get("invocation_status") == "completed"
        and event.payload.get("behavior_status") == "failed"
    ]
    if not failed_checks:
        raise ContractError("R11 row 6 lacks a failed public check")
    trigger = failed_checks[-1]
    if trigger.sequence != 101:
        raise ContractError("R11 row 6 correction trigger differs")
    if not isinstance(trigger.payload.get("result_artifact"), dict):
        raise ContractError("R11 row 6 trigger artifact differs")

    samples = [
        _request_sample(event, state_path=state, trigger_sequence=trigger.sequence)
        for event in row6_events
        if event.sequence > trigger.sequence and event.type == EventType.MODEL_CALLED
    ]
    correction_samples = [
        sample for sample in samples if sample["workflow_target"] == "correction-investigation"
    ]
    present = [sample for sample in correction_samples if sample["catalog_has_trigger"]]
    if not present:
        raise ContractError("R11 row 6 request never exposed its failed-check trigger")
    last_present = present[-1]
    absent = [
        sample
        for sample in correction_samples
        if sample["model_event_sequence"] > last_present["model_event_sequence"]
        and not sample["catalog_has_trigger"]
    ]
    if not absent:
        raise ContractError("R11 row 6 request did not reproduce trigger eviction")
    first_absent = absent[0]
    if not all(
        sample["information_actions_in_episode"] == 3
        and sample["fresh_current_read"] is True
        and sample["allowed_tool_names"] == ["read_file"]
        and sample["required_trigger_evidence_id"] is None
        for sample in absent
    ):
        raise ContractError("R11 row 6 post-eviction request surface differs")
    decision_hashes = sorted({sample["workflow_decision_hash"] for sample in absent})
    if len(decision_hashes) != 1:
        raise ContractError("R11 row 6 post-eviction decision was not stable")
    post_eviction_reads = [
        event.sequence
        for event in row6_events
        if event.sequence > first_absent["model_event_sequence"]
        and event.type == EventType.TOOL_CALLED
        and event.payload.get("tool") == "read_file"
    ]
    if any(
        event.sequence > trigger.sequence
        and event.type in {EventType.PLAN_RECORDED, EventType.PATCH_APPLIED}
        for event in row6_events
    ):
        raise ContractError("R11 row 6 unexpectedly revised or mutated after the trigger")

    row3_failed_sequences = [
        event.sequence
        for event in row3_events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        and event.payload.get("behavior_status") == "failed"
    ]
    row3_patches = [
        event.sequence for event in row3_events if event.type == EventType.PATCH_APPLIED
    ]
    if row3_failed_sequences != [52, 80, 113, 146] or len(row3_patches) != 4:
        raise ContractError("R11 row 3 correction-limit trajectory differs")

    body = {
        "schema_version": SCHEMA_VERSION,
        "official": False,
        "scope": "single-r11-v12-required-failed-check-trigger-eviction-class",
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
        "configured_limit_control": {
            "order": row3["order"],
            "run_id": R11_ROW3_RUN_ID,
            "terminal_message": row3["terminal_attribution"]["message"],
            "failed_check_sequences": row3_failed_sequences,
            "patch_applied_sequences": row3_patches,
            "initial_plus_corrective_mutations": "1+3",
            "correction_limit_bypassed": False,
        },
        "eviction_failure": {
            "order": row6["order"],
            "run_id": R11_ROW6_RUN_ID,
            "trigger_event_sequence": trigger.sequence,
            "trigger_check_id": trigger.payload.get("check_id"),
            "trigger_worktree_diff_hash": trigger.payload.get("worktree_diff_hash"),
            "trigger_artifact_hash": trigger.payload["result_artifact"].get("content_hash"),
            "last_request_with_trigger": last_present,
            "first_request_without_trigger": first_absent,
            "last_request_without_trigger": absent[-1],
            "post_eviction_request_count": len(absent),
            "post_eviction_model_event_sequences": [
                sample["model_event_sequence"] for sample in absent
            ],
            "post_eviction_decision_hash": decision_hashes[0],
            "post_eviction_read_call_sequences": post_eviction_reads,
            "revision_recorded_after_trigger": False,
            "mutation_applied_after_trigger": False,
            "terminal_event_sequence": row6["state_evidence"]["terminal_sequence"],
            "terminal_classification": row6["terminal_attribution"]["classification"],
        },
        "diagnosis": {
            "correction_attempt_limit_operated_as_configured": True,
            "failed_check_trigger_left_recent_event_window": True,
            "revision_became_unrepresentable": True,
            "fallback_read_surface_became_self_perpetuating": True,
            "next_successor_scope": "pin-one-typed-public-failed-check-trigger-until-revision",
            "increase_correction_limit_supported": False,
        },
        "evidence_boundary": {
            "public_tool_metadata_only": True,
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
    }
    return {**body, "content_hash": sha256_json(body)}


def diagnosis_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("required-trigger diagnosis content hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


__all__ = [
    "R11_DIAGNOSIS_PATH",
    "SCHEMA_VERSION",
    "build_rapid_required_trigger_diagnosis",
    "diagnosis_bytes",
]
