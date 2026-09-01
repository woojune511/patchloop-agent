"""Deterministic public-only attribution for the consumed Rapid R12 batch.

The projector reads the immutable R12 result bundle, public run events, public
tool artifacts, and durable structured work plans.  It never reads model
response text, reasoning text, private task data, evaluator details, or a
reference patch.  A byte-identical SQLite snapshot may be used when the source
trace has a harmless zero-length WAL plus a stale shared-memory sidecar.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from patchloop.agent.lean_runtime import validate_persisted_lean_harness_request
from patchloop.agent.workflow_successor_v2 import RecordedWorkPlanV2
from patchloop.contracts import EventType, RunEvent
from patchloop.errors import ContractError
from patchloop.evals.rapid_workflow_diagnosis import (
    _artifact_json,
    _diagnose_row,
    _load_bundle,
    _load_public_task,
    _tool_input,
)
from patchloop.trace_view import ReadOnlyTraceStore
from patchloop.util import canonical_json, sha256_json, sha256_text

SCHEMA_VERSION = "rapid-r12-public-terminal-diagnosis-v1"
R12_BUNDLE_PATH = Path(
    "reports/rapid-development/"
    "rapid-public-dev-anyio-semantic-progress-ab-20260825-r12-4d4fbf5839ed.jsonl"
)
PUBLIC_TASK_PATH = Path("fixtures/task-packages/anyio-interrupt-runner-cleanup-v4/public.yaml")
V16_QUALIFICATION_PATH = Path(
    "experiments/lean-harness-candidate-binding-public-qualification-20260825-v1.json"
)
R12_BUNDLE_FILE_HASH = "sha256:da653feb1578ffca9234fd6b976f6d62a1518dd73b0a5397bef5f5b820f4ca16"
R12_EXECUTION_HASH = "sha256:4d4fbf5839ed3a498c99fe513c11c83fa3b90e2a75452c8bebd10ed0c572ac20"
R12_TERMINAL_CONTENT_HASH = (
    "sha256:ac45cceea6a27632c03f0674fcf99d3bee1356ce4b207c734d39376b12a9fc26"
)
V16_QUALIFICATION_FILE_HASH = (
    "sha256:55038c7be91138c1863e59f37169276974960255978c87ad94b1b574acf0a2d1"
)
V16_QUALIFICATION_CONTENT_HASH = (
    "sha256:9e973d1b7976148861af71399d5cfe6e43d436eaff713f3ed171dbb94fc88b4c"
)

_RUN_IDS = (
    "run_rapid_v18_4d4fbf5839ed_01",
    "run_rapid_v18_4d4fbf5839ed_02",
    "run_rapid_v18_4d4fbf5839ed_03",
    "run_rapid_v18_4d4fbf5839ed_04",
    "run_rapid_v18_4d4fbf5839ed_05",
    "run_rapid_v18_4d4fbf5839ed_06",
)
_EVENT_COUNTS = (247, 110, 165, 338, 110, 37)
_TARGET_CHECK = "public-interrupt-runner-lifecycle"
_UPSTREAM_CHECK = "upstream-pytest-plugin-regression"
_FAILURE_SIGNATURE = "AssertionError: PUBLIC_CASE:anyio:test-resumed"


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _inside(root: Path, path: str | Path, *, label: str) -> Path:
    selected = Path(path)
    if not selected.is_absolute():
        selected = root / selected
    selected = selected.resolve()
    if not selected.is_relative_to(root):
        raise ContractError(f"R12 terminal diagnosis {label} escapes the repository")
    return selected


def _zero_wal(source: Path) -> int:
    wal = Path(str(source) + "-wal")
    journal = Path(str(source) + "-journal")
    wal_bytes = wal.stat().st_size if wal.exists() else 0
    if wal_bytes != 0 or journal.exists():
        raise ContractError("R12 terminal diagnosis source trace is not quiescent")
    return wal_bytes


def prepare_read_only_snapshot(
    *,
    repository_root: str | Path = ".",
    source_state_path: str | Path = ".patchloop/state.sqlite3",
    snapshot_path: str | Path = ".tmp/r12-terminal-diagnosis/state.sqlite3",
) -> Path:
    """Copy a quiescent source DB without mutating it or its sidecars."""

    root = Path(repository_root).resolve()
    source = _inside(root, source_state_path, label="source state")
    snapshot = _inside(root, snapshot_path, label="snapshot")
    if source == snapshot or not source.is_file():
        raise ContractError("R12 terminal diagnosis source state is invalid")
    for suffix in ("-wal", "-shm", "-journal"):
        if Path(str(snapshot) + suffix).exists():
            raise ContractError("R12 terminal diagnosis snapshot has SQLite sidecars")

    _zero_wal(source)
    before = _file_sha256(source)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, snapshot)
    after = _file_sha256(source)
    _zero_wal(source)
    if before != after or _file_sha256(snapshot) != before:
        raise ContractError("R12 terminal diagnosis snapshot is not byte-identical")
    return snapshot


def _validated_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError(f"R12 terminal diagnosis {label} is invalid") from exc
    if type(value) is not dict:
        raise ContractError(f"R12 terminal diagnosis {label} is not an object")
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError(f"R12 terminal diagnosis {label} content hash differs")
    return value


def _request_document(event: RunEvent, *, artifact_state_path: Path) -> tuple[Any, dict[str, Any]]:
    raw_path = event.payload.get("request_artifact_path")
    digest = event.payload.get("request_artifact_hash")
    if not isinstance(raw_path, str) or not isinstance(digest, str):
        raise ContractError(f"R12 terminal diagnosis request is absent at {event.sequence}")
    ref_event = event.model_copy(
        update={
            "payload": {
                **event.payload,
                "request_ref": {"path": raw_path, "content_hash": digest},
            }
        }
    )
    document = _artifact_json(
        ref_event,
        state_path=artifact_state_path,
        field="request_ref",
    )
    if document is None:
        raise ContractError(f"R12 terminal diagnosis request is invalid at {event.sequence}")
    evidence = validate_persisted_lean_harness_request(document)
    request_body = evidence.request_body
    if not isinstance(request_body, dict):
        raise ContractError("R12 terminal diagnosis request body is invalid")
    return evidence, request_body


def _request_projection(event: RunEvent, *, artifact_state_path: Path) -> dict[str, Any]:
    evidence, request_body = _request_document(event, artifact_state_path=artifact_state_path)
    decision = getattr(evidence, "workflow_decision", None) or getattr(
        evidence, "completion_loop_decision", None
    )
    target = getattr(decision, "target", None)
    tools = request_body.get("tools")
    if not isinstance(tools, list):
        raise ContractError("R12 terminal diagnosis request tools are invalid")
    tool_names: list[str] = []
    check_enums: list[str] | None = None
    for schema in tools:
        if type(schema) is not dict or not isinstance(schema.get("name"), str):
            raise ContractError("R12 terminal diagnosis tool schema is invalid")
        tool_names.append(schema["name"])
        if schema["name"] == "run_check":
            raw_enum = (
                schema.get("parameters", {}).get("properties", {}).get("check_id", {}).get("enum")
            )
            if raw_enum is not None and (
                not isinstance(raw_enum, list)
                or any(not isinstance(item, str) for item in raw_enum)
            ):
                raise ContractError("R12 terminal diagnosis check enum is invalid")
            check_enums = raw_enum
    return {
        "model_event_sequence": event.sequence,
        "request_artifact_hash": event.payload.get("request_artifact_hash"),
        "target": target,
        "effective_max_output_tokens": getattr(evidence, "effective_max_output_tokens", None),
        "request_max_output_tokens": request_body.get("max_output_tokens"),
        "allowed_tool_names": tool_names,
        "run_check_enum": check_enums,
    }


def _last_model(events: tuple[RunEvent, ...]) -> RunEvent:
    selected = next(
        (event for event in reversed(events) if event.type == EventType.MODEL_CALLED),
        None,
    )
    if selected is None:
        raise ContractError("R12 terminal diagnosis row lacks a model event")
    return selected


def _model_before(events: tuple[RunEvent, ...], sequence: int) -> RunEvent:
    selected = next(
        (
            event
            for event in reversed(events)
            if event.sequence < sequence and event.type == EventType.MODEL_CALLED
        ),
        None,
    )
    if selected is None:
        raise ContractError("R12 terminal diagnosis tool lacks a model request")
    return selected


def _reasoning_only_incomplete(
    row: dict[str, Any],
    events: tuple[RunEvent, ...],
    *,
    artifact_state_path: Path,
    manifest: Any,
) -> dict[str, Any]:
    model = _last_model(events)
    request = _request_projection(model, artifact_state_path=artifact_state_path)
    output_tokens = model.payload.get("output_tokens")
    if not (
        model.payload.get("response_status") == "incomplete"
        and model.payload.get("response_error_code") == "incomplete_response"
        and model.payload.get("response_incomplete_reason") == "max_output_tokens"
        and type(output_tokens) is int
        and output_tokens == model.payload.get("reasoning_output_tokens")
        and model.payload.get("response_text_present") is False
        and model.payload.get("response_tool_call_count") == 0
        and request["target"] == "corrective-mutation"
        and request["effective_max_output_tokens"] == output_tokens == 8_192
        and request["allowed_tool_names"] == ["apply_structured_edit"]
    ):
        raise ContractError("R12 terminal diagnosis incomplete attribution differs")
    if events[-1].sequence != model.sequence + 2:
        raise ContractError("R12 terminal diagnosis incomplete terminal order differs")
    cumulative_limit = manifest.budget.max_cumulative_output_tokens
    observed_output = row["usage"]["output_tokens"]
    return {
        "classification": "legacy_reasoning_only_per_turn_truncation",
        "request": request,
        "response": {
            "status": "incomplete",
            "incomplete_reason": "max_output_tokens",
            "output_tokens": output_tokens,
            "reasoning_output_tokens": model.payload.get("reasoning_output_tokens"),
            "response_text_present": False,
            "response_tool_call_count": 0,
        },
        "cumulative_output_tokens": observed_output,
        "cumulative_output_limit": cumulative_limit,
        "cumulative_output_budget_exhausted": observed_output >= cumulative_limit,
        "recovery_model_call_after_incomplete": False,
        "terminal_as_pure_agent_failure_supported": False,
    }


def _wrong_check_contract(
    row: dict[str, Any],
    events: tuple[RunEvent, ...],
    *,
    artifact_state_path: Path,
) -> dict[str, Any]:
    model = _last_model(events)
    request = _request_projection(model, artifact_state_path=artifact_state_path)
    terminal = events[-1]
    if not (
        model.payload.get("response_status") == "completed"
        and model.payload.get("response_error_code") is None
        and model.payload.get("response_tool_call_count") == 1
        and request["target"] == "phase-policy"
        and "run_check" in request["allowed_tool_names"]
        and request["run_check_enum"] is None
        and terminal.payload.get("message")
        == "Lean V8 response used a check outside the request binding"
        and row["first_mutation_evidence"]["event_sequence"] is None
    ):
        raise ContractError("R12 terminal diagnosis wrong-check attribution differs")
    return {
        "classification": "legacy_unbound_run_check_schema_contract_failure",
        "request": request,
        "response_status": "completed",
        "response_tool_call_count": 1,
        "requested_check_id_observed": False,
        "why_exact_check_is_unknown": "model-response-artifact-not-read",
        "dispatchable_run_check_ids": [],
        "terminal_as_pure_agent_failure_supported": False,
    }


def _check_projection(event: RunEvent, *, artifact_state_path: Path) -> dict[str, Any]:
    artifact = _artifact_json(
        event,
        state_path=artifact_state_path,
        field="result_artifact",
    )
    if artifact is None or artifact.get("public_visible_only") is not True:
        raise ContractError("R12 terminal diagnosis check artifact is not public")
    summary = artifact.get("failure_summary")
    lines = (
        [line.strip() for line in summary.replace("\r\n", "\n").split("\n") if line.strip()]
        if isinstance(summary, str)
        else []
    )
    tail = lines[-1] if lines else None
    return {
        "event_sequence": event.sequence,
        "check_id": event.payload.get("check_id"),
        "passed": event.payload.get("passed"),
        "invocation_status": event.payload.get("invocation_status"),
        "behavior_status": event.payload.get("behavior_status"),
        "worktree_diff_hash": event.payload.get("worktree_diff_hash"),
        "result_artifact_hash": event.payload.get("result_artifact", {}).get("content_hash"),
        "failure_signature": tail,
        "failure_signature_hash": sha256_text(tail) if tail is not None else None,
        "stderr_hash": artifact.get("stderr_hash"),
        "truncated": artifact.get("truncated"),
        "public_visible_only": True,
    }


def _information_action(event: RunEvent, *, artifact_state_path: Path) -> dict[str, Any]:
    tool = event.payload.get("tool")
    arguments = _tool_input(event, state_path=artifact_state_path)
    if tool == "search_files":
        query = arguments.get("query")
        if not isinstance(query, str):
            raise ContractError("R12 terminal diagnosis search input is invalid")
        body = {
            "tool": tool,
            "path_glob": arguments.get("path_glob"),
            "query_hash": sha256_text(query),
        }
    elif tool == "read_file":
        body = {
            "tool": tool,
            "path": arguments.get("path"),
            "start_line": arguments.get("start_line"),
            "end_line": arguments.get("end_line"),
        }
    else:
        raise ContractError("R12 terminal diagnosis information tool differs")
    return {"event_sequence": event.sequence, **body, "action_hash": sha256_json(body)}


def _mechanism_markers(hypothesis: str) -> dict[str, bool]:
    normalized = hypothesis.lower()
    return {
        "runner_lifecycle": "runner" in normalized
        and any(marker in normalized for marker in ("close", "exit", "torn down", "teardown")),
        "pytest_reentry_or_resume": any(
            marker in normalized for marker in ("resume", "resumable", "re-enter", "re-entry")
        ),
        "interrupt_propagation": any(
            marker in normalized for marker in ("interrupt", "keyboardinterrupt", "sigint")
        ),
    }


def _semantic_correction(
    row: dict[str, Any],
    events: tuple[RunEvent, ...],
    *,
    artifact_state_path: Path,
) -> dict[str, Any]:
    check_events = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "run_check"
    ]
    checks = [
        _check_projection(event, artifact_state_path=artifact_state_path) for event in check_events
    ]
    if not (
        len(checks) == 4
        and all(item["check_id"] == _TARGET_CHECK for item in checks)
        and all(item["passed"] is False for item in checks)
        and all(item["invocation_status"] == "completed" for item in checks)
        and all(item["behavior_status"] == "failed" for item in checks)
        and all(item["failure_signature"] == _FAILURE_SIGNATURE for item in checks)
        and len({item["worktree_diff_hash"] for item in checks}) == 4
        and len({item["stderr_hash"] for item in checks}) == 1
    ):
        raise ContractError("R12 terminal diagnosis semantic check trajectory differs")

    plan_events = [event for event in events if event.type == EventType.PLAN_RECORDED]
    if [event.sequence for event in plan_events] != [17, 93, 121, 149]:
        raise ContractError("R12 terminal diagnosis plan sequence differs")
    plans: list[RecordedWorkPlanV2] = []
    projected_plans: list[dict[str, Any]] = []
    seen_correction_actions: set[str] = set()
    for event in plan_events:
        try:
            plan = RecordedWorkPlanV2.model_validate_json(canonical_json(event.payload.get("plan")))
        except ValueError as exc:
            raise ContractError("R12 terminal diagnosis durable plan is invalid") from exc
        if event.payload.get("plan_hash") != plan.content_hash:
            raise ContractError("R12 terminal diagnosis durable plan hash differs")
        plans.append(plan)
        actions: list[dict[str, Any]] = []
        if plan.trigger_event_sequence is not None:
            actions = [
                _information_action(candidate, artifact_state_path=artifact_state_path)
                for candidate in events
                if plan.trigger_event_sequence < candidate.sequence < event.sequence
                and candidate.type == EventType.TOOL_CALLED
                and candidate.payload.get("tool") in {"search_files", "read_file"}
            ]
        action_hashes = [item["action_hash"] for item in actions]
        repeated = sum(item in seen_correction_actions for item in action_hashes)
        novel = len(action_hashes) - repeated
        if plan.trigger_event_sequence is not None:
            seen_correction_actions.update(action_hashes)
        markers = _mechanism_markers(plan.hypothesis)
        projected_plans.append(
            {
                "event_sequence": event.sequence,
                "revision_index": plan.revision_index,
                "trigger": plan.trigger,
                "trigger_event_sequence": plan.trigger_event_sequence,
                "plan_hash": plan.content_hash,
                "parent_plan_hash": plan.parent_plan_hash,
                "prior_hypothesis_disposition": plan.prior_hypothesis_disposition,
                "candidate_files": [item.path for item in plan.candidate_files],
                "hypothesis_hash": sha256_text(plan.hypothesis),
                "intended_change_hash": sha256_text(plan.intended_change),
                "semantic_reset_required": event.payload.get("semantic_reset_required"),
                "same_signature_failed_diff_count": event.payload.get(
                    "same_signature_failed_diff_count"
                ),
                "mechanism_family": "runner-lifecycle-before-pytest-reentry"
                if all(markers.values())
                else None,
                "mechanism_markers": markers,
                "information_actions": actions,
                "novel_information_action_count": novel,
                "repeated_information_action_count": repeated,
            }
        )

    if not (
        [plan.revision_index for plan in plans] == [0, 1, 2, 3]
        and [plan.prior_hypothesis_disposition for plan in plans]
        == [None, "refined", "rejected", "rejected"]
        and [item["semantic_reset_required"] for item in projected_plans]
        == [False, False, True, True]
        and all(
            item["mechanism_family"] == "runner-lifecycle-before-pytest-reentry"
            for item in projected_plans
        )
        and len({plan.content_hash for plan in plans}) == 4
    ):
        raise ContractError("R12 terminal diagnosis semantic reset projection differs")
    for parent, child in zip(plans[:-1], plans[1:], strict=True):
        if child.parent_plan_hash != parent.content_hash:
            raise ContractError("R12 terminal diagnosis plan chain differs")

    patch_events = [event for event in events if event.type == EventType.PATCH_APPLIED]
    if [event.sequence for event in patch_events] != [67, 101, 129, 157]:
        raise ContractError("R12 terminal diagnosis patch order differs")
    if [event.payload.get("plan_hash") for event in patch_events] != [
        plan.content_hash for plan in plans
    ]:
        raise ContractError("R12 terminal diagnosis patch-plan binding differs")
    if not (
        row["edit_path"]["attempts"] == 4
        and row["edit_path"]["accepted"] == 4
        and row["edit_path"]["rejected"] == 0
        and row["visible_checks"]["upstream_before_target_pass"] == 0
        and row["terminal_attribution"]["error_code"] == "CORRECTION_ATTEMPT_LIMIT"
    ):
        raise ContractError("R12 terminal diagnosis correction terminal differs")

    return {
        "classification": "semantic_reset_without_alternative_causal_mechanism",
        "checks": checks,
        "plans": projected_plans,
        "patch_applied_sequences": [event.sequence for event in patch_events],
        "initial_plus_corrective_mutations": "1+3",
        "all_edit_dispatches_accepted": True,
        "correction_limit_respected": True,
        "semantic_reset_revision_indices": [2, 3],
        "distinct_plan_hashes": 4,
        "distinct_failed_diff_hashes": 4,
        "single_public_failure_signature": True,
        "shared_mechanism_family_markers": True,
        "semantic_equivalence_claimed": False,
        "rejected_label_forced_alternative_mechanism": False,
        "increase_correction_limit_supported": False,
        "mechanical_friction_supported": False,
    }


def _submitted_failure(
    row: dict[str, Any],
    events: tuple[RunEvent, ...],
    *,
    artifact_state_path: Path,
) -> dict[str, Any]:
    get_diff = next(
        (
            event
            for event in events
            if event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "get_diff"
        ),
        None,
    )
    if get_diff is None:
        raise ContractError("R12 terminal diagnosis submitted row lacks a diff")
    artifact = _artifact_json(
        get_diff,
        state_path=artifact_state_path,
        field="result_artifact",
    )
    if artifact is None:
        raise ContractError("R12 terminal diagnosis submitted diff is invalid")
    invocations = row["visible_checks"]["invocations"]
    if not (
        row["evaluator_reached"]
        and row["submission_completed"]
        and not row["success_at_budget"]
        and row["review_submission"]["completed_get_diff_to_finish"]
        and [item["passed"] for item in invocations] == [False, True, True]
        and [item["check_id"] for item in invocations]
        == [_TARGET_CHECK, _TARGET_CHECK, _UPSTREAM_CHECK]
        and artifact.get("changed_files") == ["src/anyio/pytest_plugin.py"]
        and artifact.get("patch_hash") == invocations[-1]["worktree_diff_hash"]
    ):
        raise ContractError("R12 terminal diagnosis submitted path differs")
    return {
        "classification": "submitted_visible_checks_passed_task_failure",
        "visible_check_path": [
            {
                "event_sequence": item["sequence"],
                "check_id": item["check_id"],
                "passed": item["passed"],
                "worktree_diff_hash": item["worktree_diff_hash"],
            }
            for item in invocations
        ],
        "diff": {
            "event_sequence": get_diff.sequence,
            "patch_hash": artifact.get("patch_hash"),
            "changed_files": artifact.get("changed_files"),
            "added_lines": artifact.get("added_lines"),
            "deleted_lines": artifact.get("deleted_lines"),
            "raw_patch_emitted": False,
        },
        "get_diff_to_finish_completed": True,
        "evaluator_reached": True,
        "exact_task_failure_cause_observed": False,
        "why_exact_cause_is_unknown": "hidden-evaluator-content-not-read",
        "harness_completion_failure_supported": False,
        "task_specific_tuning_supported": False,
    }


def _plan_admission_failure(
    row: dict[str, Any],
    events: tuple[RunEvent, ...],
    *,
    v16: dict[str, Any],
) -> dict[str, Any]:
    rejections = [
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == "work-plan-admission-recovery-v1"
    ]
    if not (
        [event.payload.get("attempt") for event in rejections] == [1, 2]
        and all(
            event.payload.get("reason_codes") == ["plan_schema_invalid"] for event in rejections
        )
        and row["terminal_attribution"]["error_code"] == "WORK_PLAN_ADMISSION_REPEATED"
        and v16.get("successor_runtime") == "lean-harness-v16"
        and v16.get("rapid_candidate_created") is False
        and v16.get("paid_execution_authorized") is False
    ):
        raise ContractError("R12 terminal diagnosis plan-admission attribution differs")
    return {
        "classification": "duplicate_candidate_path_plan_schema_friction",
        "admission_sequences": [event.sequence for event in rejections],
        "reason_codes": [event.payload.get("reason_codes") for event in rejections],
        "provider_calls_after_second_rejection": 0,
        "offline_successor": {
            "runtime": v16.get("successor_runtime"),
            "tool_schema_version": v16.get("tool_schema_version"),
            "context_policy_version": v16.get("context_policy_version"),
            "qualification_file_hash": V16_QUALIFICATION_FILE_HASH,
            "qualification_content_hash": V16_QUALIFICATION_CONTENT_HASH,
            "live_candidate_created": False,
            "quality_improvement_established": False,
        },
        "selected_for_next_successor": False,
    }


def build_rapid_r12_terminal_diagnosis(
    *,
    repository_root: str | Path = ".",
    bundle_path: str | Path = R12_BUNDLE_PATH,
    public_task_path: str | Path = PUBLIC_TASK_PATH,
    source_state_path: str | Path = ".patchloop/state.sqlite3",
    state_snapshot_path: str | Path = ".tmp/r12-terminal-diagnosis/state.sqlite3",
) -> dict[str, Any]:
    """Build the exact zero-call R12 terminal diagnosis."""

    root = Path(repository_root).resolve()
    bundle = _inside(root, bundle_path, label="bundle")
    task_path = _inside(root, public_task_path, label="public task")
    source_state = _inside(root, source_state_path, label="source state")
    snapshot = _inside(root, state_snapshot_path, label="snapshot")
    v16_path = _inside(root, V16_QUALIFICATION_PATH, label="V16 qualification")
    if not all(path.is_file() for path in (bundle, task_path, source_state, snapshot, v16_path)):
        raise ContractError("R12 terminal diagnosis input is unavailable")
    if _file_sha256(bundle) != R12_BUNDLE_FILE_HASH:
        raise ContractError("R12 terminal diagnosis bundle file hash differs")
    _zero_wal(source_state)
    source_hash_before = _file_sha256(source_state)
    if _file_sha256(snapshot) != source_hash_before:
        raise ContractError("R12 terminal diagnosis snapshot differs from source")
    if _file_sha256(v16_path) != V16_QUALIFICATION_FILE_HASH:
        raise ContractError("R12 terminal diagnosis V16 qualification file hash differs")
    v16 = _validated_json(v16_path, label="V16 qualification")
    if v16.get("content_hash") != V16_QUALIFICATION_CONTENT_HASH:
        raise ContractError("R12 terminal diagnosis V16 qualification content differs")

    bundle_events = _load_bundle(bundle)
    if not (
        bundle_events[0].get("execution_hash") == R12_EXECUTION_HASH
        and bundle_events[-1].get("content_hash") == R12_TERMINAL_CONTENT_HASH
    ):
        raise ContractError("R12 terminal diagnosis bundle identity differs")
    bundle_rows = [item for item in bundle_events if item.get("event") == "row-terminal"]
    if [row.get("run_id") for row in bundle_rows] != list(_RUN_IDS):
        raise ContractError("R12 terminal diagnosis row order differs")

    task = _load_public_task(task_path)
    store = ReadOnlyTraceStore(snapshot)
    event_rows = [tuple(store.list_events(run_id)) for run_id in _RUN_IDS]
    if [len(events) for events in event_rows] != list(_EVENT_COUNTS):
        raise ContractError("R12 terminal diagnosis event counts differ")
    workflow_rows = [
        _diagnose_row(
            bundle_row,
            store=store,
            state_path=source_state,
            task=task,
        )
        for bundle_row in bundle_rows
    ]
    manifests = [store.get_manifest(run_id) for run_id in _RUN_IDS]

    incomplete_rows = [
        {
            "order": order,
            "run_id": _RUN_IDS[order - 1],
            **_reasoning_only_incomplete(
                workflow_rows[order - 1],
                event_rows[order - 1],
                artifact_state_path=source_state,
                manifest=manifests[order - 1],
            ),
        }
        for order in (1, 4)
    ]
    wrong_check = _wrong_check_contract(
        workflow_rows[4],
        event_rows[4],
        artifact_state_path=source_state,
    )
    treatment_check = next(
        event
        for event in event_rows[1]
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        and event.payload.get("check_id") == _TARGET_CHECK
        and event.payload.get("passed") is True
    )
    treatment_check_request = _request_projection(
        _model_before(event_rows[1], treatment_check.sequence),
        artifact_state_path=source_state,
    )
    if treatment_check_request["run_check_enum"] != [_TARGET_CHECK]:
        raise ContractError("R12 terminal diagnosis treatment check binding differs")

    submitted = _submitted_failure(
        workflow_rows[1],
        event_rows[1],
        artifact_state_path=source_state,
    )
    semantic = _semantic_correction(
        workflow_rows[2],
        event_rows[2],
        artifact_state_path=source_state,
    )
    admission = _plan_admission_failure(workflow_rows[5], event_rows[5], v16=v16)
    if _file_sha256(source_state) != source_hash_before or _zero_wal(source_state) != 0:
        raise ContractError("R12 terminal diagnosis source state changed during projection")

    row_attributions = [
        {"order": 1, "run_id": _RUN_IDS[0], **incomplete_rows[0]},
        {"order": 2, "run_id": _RUN_IDS[1], **submitted},
        {"order": 3, "run_id": _RUN_IDS[2], **semantic},
        {"order": 4, "run_id": _RUN_IDS[3], **incomplete_rows[1]},
        {
            "order": 5,
            "run_id": _RUN_IDS[4],
            **wrong_check,
            "successor_exact_check_request": treatment_check_request,
        },
        {"order": 6, "run_id": _RUN_IDS[5], **admission},
    ]
    body = {
        "schema_version": SCHEMA_VERSION,
        "official": False,
        "source_bundle": {
            "path": bundle.relative_to(root).as_posix(),
            "bytes": bundle.stat().st_size,
            "file_sha256": R12_BUNDLE_FILE_HASH,
            "execution_hash": R12_EXECUTION_HASH,
            "terminal_content_hash": R12_TERMINAL_CONTENT_HASH,
        },
        "source_trace": {
            "authoritative_path": source_state.relative_to(root).as_posix(),
            "snapshot_provenance": "byte-identical-local-copy-of-authoritative-state",
            "snapshot_byte_identical_at_build": True,
            "source_wal_bytes": 0,
            "source_shared_memory_ignored": True,
            "read_only_immutable_snapshot": True,
            "raw_events_mutated": False,
            "event_counts_by_order": list(_EVENT_COUNTS),
            "terminal_event_hashes_by_order": [
                row["state_evidence"]["terminal_event_hash"] for row in workflow_rows
            ],
        },
        "public_task": {
            "path": task_path.relative_to(root).as_posix(),
            "task_id": task.task_id,
            "task_version": task.task_version,
            "public_task_hash": sha256_json(task.model_dump(mode="json")),
            "visible_check_order": [check.id for check in task.visible_checks],
        },
        "immutable_batch": {
            "rows_started": 6,
            "bundle_agent_failures": 5,
            "evaluator_reached": 1,
            "submissions_completed": 1,
            "successes_at_budget": 0,
            "token_terminals": 0,
            "model_cost_nanos": 2_658_231_750,
        },
        "row_attributions": row_attributions,
        "attribution_summary": {
            "legacy_v8_reasoning_only_per_turn_truncation": 2,
            "legacy_v8_unbound_check_contract": 1,
            "v15_submitted_task_failure_exact_cause_unknown": 1,
            "v15_semantic_no_progress": 1,
            "v15_duplicate_candidate_path_schema_friction": 1,
            "pure_agent_failures_supported_for_all_five_bundle_agent_failures": False,
            "r12_is_a_clean_v8_quality_baseline": False,
        },
        "selected_failure_class": {
            "id": "semantic-reset-without-alternative-causal-mechanism",
            "affected_orders": [3],
            "selection_scope": "largest-actionable-public-treatment-side-non-mechanical-class",
            "why_selected": [
                "four accepted mutations preserved one public failure signature across four diffs",
                "the bounded 1+3 correction policy was respected",
                "revisions 2 and 3 rejected the prior hypothesis label but "
                "retained one mechanism family",
                "the submitted task failure has no public exact evaluator cause",
                "the remaining control and plan-schema terminals are legacy or "
                "offline-fixed mechanical friction",
            ],
            "next_successor_scope": "bounded-public-causal-alternative-gate",
            "required_offline_properties": [
                "a rejected-hypothesis revision names the prior and alternative "
                "public causal mechanisms separately",
                "the alternative mechanism cites current-diff public evidence not "
                "already exhausted by its parent",
                "same-family relabeling fails admission or terminates before "
                "another correction mutation",
                "the existing check-specific 1+3 mutation limit remains unchanged",
                "no task-specific solution, hidden evidence, or reference patch enters the gate",
            ],
            "candidate_ready": False,
            "paid_execution_authorized": False,
        },
        "evidence_boundary": {
            "public_bundle_events_read": True,
            "public_tool_metadata_read": True,
            "public_visible_check_artifacts_read": True,
            "durable_structured_plan_text_read_for_marker_projection": True,
            "raw_plan_text_emitted": False,
            "raw_patch_emitted": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "reasoning_text_read": False,
            "llm_response_text_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "source_state_mutations": 0,
            "local_snapshot_files_created": 1,
            "added_cost_nanos": 0,
        },
        "interpretation_limits": {
            "semantic_marker_projection_proves_equivalence": False,
            "submitted_hidden_failure_exactly_attributed": False,
            "v16_live_quality_established": False,
            "general_agent_quality_established": False,
            "r12_retry_allowed": False,
        },
    }
    return {**body, "content_hash": sha256_json(body)}


def diagnosis_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("R12 terminal diagnosis content hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


__all__ = [
    "R12_BUNDLE_PATH",
    "SCHEMA_VERSION",
    "build_rapid_r12_terminal_diagnosis",
    "diagnosis_bytes",
    "prepare_read_only_snapshot",
]
