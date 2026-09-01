"""Deterministic public-only audit of consumed, halted Rapid R24."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from patchloop.contracts import EventType, RunEvent
from patchloop.errors import ContractError
from patchloop.evals.rapid_batch_driver import load_rapid_batch_driver_journal
from patchloop.evals.rapid_workflow_diagnosis import (
    _artifact_json,
    _diagnose_row,
    _load_public_task,
    _tool_input,
)
from patchloop.trace_view import ReadOnlyTraceStore
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "rapid-r24-halted-public-audit-v1"
EXECUTION_HASH = "sha256:a4a8e75dfa0f1ae1365ef991b48cf18bd61f3dd717cf8d4d1bedff392236592e"
PREFIX = "rapid-public-dev-anyio-v5-provider-schema-ab-20260901-r24"
CANDIDATE_PATH = Path("reports/rapid-development/artifacts") / f"{PREFIX}-candidate-v33.json"
REHEARSAL_PATH = CANDIDATE_PATH.with_name(f"{PREFIX}-candidate-v33-rehearsal-v30.json")
QUALIFICATION_PATH = Path(
    "experiments/rapid-candidate-v33-v25-v27-provider-schema-ab-"
    "public-qualification-20260901-v1.json"
)
PLAN_PATH = Path(".patchloop/experiments/plans") / f"{EXECUTION_HASH.removeprefix('sha256:')}.json"
BUNDLE_PATH = Path("reports/rapid-development") / f"{PREFIX}-a4a8e75dfa0f.jsonl"
IMAGE_RECEIPT_PATH = BUNDLE_PATH.with_suffix(".image-admission.jsonl")
AUDIT_PATH = CANDIDATE_PATH.with_name(f"{PREFIX}-candidate-v33-halted-public-audit-v1.json")
PUBLIC_TASK_PATH = Path("fixtures/task-packages/anyio-interrupt-runner-cleanup-v5/public.yaml")
STATE_PATH = Path(".patchloop/state.sqlite3")

SOURCE_FILES = (
    "patchloop/agent/model.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/workflow_r21_reliability_successor.py",
    "patchloop/evals/rapid_batch_driver.py",
    "patchloop/evals/rapid_row_continuation.py",
    "patchloop/evals/rapid_r24_halted_audit.py",
    "scripts/build_rapid_r24_halted_audit.py",
    "tests/test_rapid_r24_halted_audit.py",
)


def _file_record(root: Path, relative: Path | str) -> dict[str, Any]:
    path = Path(relative).as_posix()
    selected = ensure_within(root, path)
    if selected.is_symlink() or not selected.is_file():
        raise ContractError(f"Rapid R24 audit source is unavailable: {path}")
    raw = selected.read_bytes()
    return {"path": path, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _load_sealed_json(root: Path, relative: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    selected = ensure_within(root, relative.as_posix())
    try:
        raw = selected.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError(f"Rapid R24 JSON is unavailable: {relative.as_posix()}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"Rapid R24 JSON is not an object: {relative.as_posix()}")
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError(f"Rapid R24 JSON content hash differs: {relative.as_posix()}")
    return value, {
        "path": relative.as_posix(),
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "content_hash": value["content_hash"],
    }


def _load_image_receipt(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected = ensure_within(root, IMAGE_RECEIPT_PATH.as_posix())
    try:
        raw = selected.read_bytes()
        rows = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("Rapid R24 image receipt is unavailable") from exc
    previous: str | None = None
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ContractError("Rapid R24 image receipt row is invalid")
        body = {key: item for key, item in row.items() if key != "content_hash"}
        if row.get("content_hash") != sha256_json(body) or row.get("previous_hash") != previous:
            raise ContractError(f"Rapid R24 image receipt chain differs at row {index}")
        previous = row["content_hash"]
    if [row.get("type") for row in rows] != [
        "image-inspection-attempt-started",
        "image-admitted",
    ]:
        raise ContractError("Rapid R24 image receipt event order differs")
    return rows, {
        "path": IMAGE_RECEIPT_PATH.as_posix(),
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "terminal_content_hash": rows[-1]["content_hash"],
    }


def _driver_contract(first: dict[str, Any], rehearsal: dict[str, Any]) -> dict[str, Any]:
    capabilities = rehearsal.get("all_row_capabilities")
    if not isinstance(capabilities, list) or len(capabilities) != 6:
        raise ContractError("Rapid R24 rehearsal row capabilities differ")
    return {
        "schema_version": "rapid-append-only-batch-driver-contract-v1",
        "policy_version": first["driver_policy_version"],
        "official": False,
        **{
            key: first[key]
            for key in (
                "experiment_id",
                "execution_hash",
                "plan_hash",
                "runtime_build_hash",
                "schedule_hash",
                "cost_control_hash",
                "row_reserve_nanos",
                "full_schedule_reserve_nanos",
                "hard_cap_nanos",
            )
        },
        "manifest_hashes": tuple(row["manifest_hash"] for row in capabilities),
        "schedule_row_ids": tuple(row["schedule_row_id"] for row in capabilities),
        "run_ids": tuple(row["run_id"] for row in capabilities),
        "content_hash": first["driver_contract_hash"],
    }


def _load_journal(
    root: Path, rehearsal: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected = ensure_within(root, BUNDLE_PATH.as_posix())
    try:
        raw = selected.read_bytes()
        unvalidated = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("Rapid R24 result bundle is unavailable") from exc
    if not unvalidated:
        raise ContractError("Rapid R24 result bundle is empty")
    journal = load_rapid_batch_driver_journal(
        selected,
        _driver_contract(unvalidated[0], rehearsal),
    )
    final = journal[-1]
    if not (
        final.get("event") == "batch-halted"
        and final.get("cost_fully_settled") is True
        and final.get("schedule_fully_observed") is False
        and final.get("terminal_row_count") == 3
        and final.get("not_started_row_count") == 3
    ):
        raise ContractError("Rapid R24 final driver state differs")
    return journal, {
        "path": BUNDLE_PATH.as_posix(),
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "terminal_content_hash": final["content_hash"],
    }


def _event_counts(events: list[RunEvent]) -> dict[str, int]:
    return dict(sorted(Counter(event.type.value for event in events).items()))


def _source_reads(events: list[RunEvent], *, state_path: Path) -> list[dict[str, Any]]:
    reads: list[dict[str, Any]] = []
    for event in events:
        if event.type != EventType.TOOL_CALLED or event.payload.get("tool") != "read_file":
            continue
        arguments = _tool_input(event, state_path=state_path)
        reads.append(
            {
                "event_sequence": event.sequence,
                **{
                    key: arguments.get(key)
                    for key in ("path", "start_line", "end_line", "search_anchor")
                },
            }
        )
    return reads


def _lifecycle_binding(arguments: dict[str, Any]) -> dict[str, Any] | None:
    lifecycle = arguments.get("lifecycle_state_transition")
    if not isinstance(lifecycle, dict):
        return None
    owners = lifecycle.get("owners")
    states = lifecycle.get("states")
    transitions = lifecycle.get("transitions")
    if (
        not isinstance(owners, list)
        or not isinstance(states, list)
        or not isinstance(transitions, list)
    ):
        return {"shape_valid": False}
    owner_components = [item.get("component") for item in owners if isinstance(item, dict)]
    state_components = [item.get("component") for item in states if isinstance(item, dict)]
    affected_components = [
        component
        for item in transitions
        if isinstance(item, dict)
        for component in (item.get("affected_components") or [])
    ]
    owner_set = set(owner_components)
    state_set = set(state_components)
    affected_set = set(affected_components)
    return {
        "shape_valid": True,
        "owner_components": owner_components,
        "state_components": state_components,
        "transition_affected_components": affected_components,
        "owner_components_unique": len(owner_set) == len(owner_components),
        "state_components_unique": len(state_set) == len(state_components),
        "owner_and_state_component_sets_equal": owner_set == state_set,
        "transition_components_subset_of_owners": affected_set.issubset(owner_set),
    }


def _plan_attempts(events: list[RunEvent], *, state_path: Path) -> list[dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    for event in events:
        if event.type != EventType.TOOL_CALLED or event.payload.get("tool") not in {
            "record_work_plan",
            "revise_work_plan",
        }:
            continue
        arguments = _tool_input(event, state_path=state_path)
        outcome = next(
            (
                item
                for item in events
                if item.sequence > event.sequence
                and item.payload.get("tool") == event.payload.get("tool")
                and item.type in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}
            ),
            None,
        )
        failed = outcome if outcome is not None and outcome.type == EventType.TOOL_FAILED else None
        succeeded = (
            outcome if outcome is not None and outcome.type == EventType.TOOL_SUCCEEDED else None
        )
        details = (
            failed.payload.get("error_details")
            if failed is not None and isinstance(failed.payload.get("error_details"), dict)
            else {}
        )
        attempts.append(
            {
                "event_sequence": event.sequence,
                "tool": event.payload.get("tool"),
                "accepted": succeeded is not None,
                "error_code": failed.payload.get("error_code") if failed is not None else None,
                "reason_codes": details.get("reason_codes", []),
                "feedback_guidance": details.get("guidance"),
                "feedback_component_mismatch_projection_present": any(
                    key in details
                    for key in (
                        "owner_components",
                        "state_components",
                        "transition_affected_components",
                    )
                ),
                "lifecycle_binding": _lifecycle_binding(arguments),
            }
        )
    return attempts


def _visible_check_results(events: list[RunEvent], *, state_path: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for event in events:
        if event.type != EventType.TOOL_SUCCEEDED or event.payload.get("tool") != "run_check":
            continue
        artifact = _artifact_json(event, state_path=state_path, field="result_artifact") or {}
        results.append(
            {
                "event_sequence": event.sequence,
                "check_id": event.payload.get("check_id"),
                "passed": event.payload.get("passed"),
                "worktree_diff_hash": event.payload.get("worktree_diff_hash"),
                "failure_summary": artifact.get("failure_summary"),
                "public_visible_only": artifact.get("public_visible_only"),
            }
        )
    return results


def _exploration_stop(events: list[RunEvent]) -> dict[str, Any] | None:
    event = next(
        (item for item in events if item.type.value == "ExplorationStopRecorded"),
        None,
    )
    if event is None:
        return None
    return {
        "event_sequence": event.sequence,
        "blocking_question": event.payload.get("blocking_question"),
        "source_span_ids": event.payload.get("source_span_ids"),
    }


def _run_artifact_records(root: Path, run_id: str) -> dict[str, Any]:
    base = Path(".patchloop/artifacts/runs") / run_id
    return {
        name.removesuffix(".json"): _file_record(root, base / name)
        for name in ("manifest.json", "result.json", "provenance.json")
    }


def _row_audit(
    *,
    root: Path,
    schedule_row: dict[str, Any],
    capability: dict[str, Any],
    terminal: dict[str, Any] | None,
    store: ReadOnlyTraceStore,
    runs: dict[str, dict[str, Any]],
    state_path: Path,
    task: Any,
) -> dict[str, Any]:
    order = schedule_row["order"]
    run_id = capability["run_id"]
    base = {"order": order, "run_id": run_id, "variant": schedule_row["variant"]}
    run = runs.get(run_id)
    if terminal is None:
        if run is not None:
            raise ContractError(f"Rapid R24 unstarted row has state: {run_id}")
        return {**base, "status": "not_started"}
    if run is None or not isinstance(run.get("result"), dict):
        raise ContractError(f"Rapid R24 terminal row lacks a state result: {run_id}")
    manifest = store.get_manifest(run_id)
    if sha256_json(manifest.model_dump(mode="json")) != capability["manifest_hash"]:
        raise ContractError(f"Rapid R24 state manifest differs: {run_id}")
    projected = terminal.get("projected_row")
    if not isinstance(projected, dict):
        raise ContractError(f"Rapid R24 terminal projection differs: {run_id}")
    diagnosis = _diagnose_row(projected, store=store, state_path=state_path, task=task)
    events = store.list_events(run_id)
    return {
        **base,
        "status": run["status"],
        "outcome_kind": projected["outcome_kind"],
        "evaluator_reached": projected["evaluator_reached"],
        "submission_completed": projected["submission_completed"],
        "success_at_budget": projected["success_at_budget"],
        "usage": projected["usage"],
        "model_cost_nanos": terminal["model_cost_nanos"],
        "event_count": len(events),
        "event_type_counts": _event_counts(events),
        "public_event_hash": sha256_json([event.model_dump(mode="json") for event in events]),
        "source_reads": _source_reads(events, state_path=state_path),
        "tool_sequence": [
            [event.sequence, event.payload.get("tool")]
            for event in events
            if event.type == EventType.TOOL_CALLED
        ],
        "plan_attempts": _plan_attempts(events, state_path=state_path),
        "visible_check_results": _visible_check_results(events, state_path=state_path),
        "exploration_stop": _exploration_stop(events),
        "workflow_diagnosis": diagnosis,
        "terminal_error": run["result"].get("terminal_error"),
        "recorded_driver_flags": {
            key: terminal[key]
            for key in (
                "row_capability_consumed_and_dispatched",
                "terminal_state_atomic",
                "projection_matches_result",
                "cost_settlement_complete",
                "ordinary_terminal_valid",
            )
        },
        "artifacts": _run_artifact_records(root, run_id),
    }


def _lifecycle_schema_observation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rejected = [
        attempt
        for row in rows
        for attempt in row.get("plan_attempts", [])
        if attempt.get("reason_codes") == ["lifecycle_state_transition_unbound"]
    ]
    if len(rejected) != 3:
        raise ContractError("Rapid R24 lifecycle rejection count differs")
    mismatches = [attempt["lifecycle_binding"] for attempt in rejected]
    return {
        "classification": "cross-field-lifecycle-component-binding-friction",
        "affected_variant": "lean-harness-v27",
        "rejected_plan_attempts": len(rejected),
        "affected_started_rows": len(
            {
                row["run_id"]
                for row in rows
                if any(attempt in rejected for attempt in row.get("plan_attempts", []))
            }
        ),
        "reason_code": "lifecycle_state_transition_unbound",
        "observed_bindings": mismatches,
        "all_owner_state_sets_mismatched": all(
            binding.get("owner_and_state_component_sets_equal") is False for binding in mismatches
        ),
        "all_transition_sets_escape_owners": all(
            binding.get("transition_components_subset_of_owners") is False for binding in mismatches
        ),
        "feedback_component_mismatch_projection_present": any(
            attempt["feedback_component_mismatch_projection_present"] for attempt in rejected
        ),
        "observed_feedback_guidance": sorted(
            {str(attempt["feedback_guidance"]) for attempt in rejected}
        ),
        "server_validation_source": (
            "patchloop/agent/workflow_r21_reliability_successor.py:751-780"
        ),
        "source_review_inference": (
            "The request schema types component identities as independent strings; "
            "the server later enforces owner/state equality and transition subset relations."
        ),
        "semantic_fix_correctness_established": False,
    }


def _provider_timeout_observation(
    rows: list[dict[str, Any]], journal: list[dict[str, Any]], root: Path
) -> dict[str, Any]:
    row = next(item for item in rows if item.get("order") == 3)
    if row.get("terminal_error", {}).get("type") != "APITimeoutError":
        raise ContractError("Rapid R24 timeout row differs")
    events = row["event_type_counts"]
    settlement_event = next(
        item
        for item in journal
        if item.get("event") == "row-settlement-evidence" and item.get("schedule_order") == 3
    )
    evidence = settlement_event["settlement_evidence"]
    provenance_path = Path(".patchloop/artifacts/runs") / row["run_id"] / "provenance.json"
    provenance = json.loads(ensure_within(root, provenance_path.as_posix()).read_bytes())
    return {
        "classification": "provider-generation-timeout-after-count-and-context",
        "run_id": row["run_id"],
        "terminal_error": row["terminal_error"],
        "input_token_count_started": events.get("InputTokenCountStarted", 0),
        "input_token_count_finished": events.get("InputTokenCountFinished", 0),
        "contexts_built": events.get("ContextBuilt", 0),
        "model_events_recorded": events.get("ModelCalled", 0),
        "generation_attempts_lower_bound": events.get("ContextBuilt", 0),
        "exact_http_request_count_recorded": False,
        "last_count_and_context_have_no_model_event": (
            events.get("InputTokenCountFinished") == 12
            and events.get("ContextBuilt") == 12
            and events.get("ModelCalled") == 11
        ),
        "continuation_policy": "settled-row-local-infrastructure-continuation-v1",
        "eligible_terminal_code": "RECOVERY_ERROR",
        "observed_terminal_code": row["terminal_error"].get("code"),
        "settlement_checks": evidence["checks"],
        "halt_reason_codes": journal[-1]["reason_codes"],
        "triad_files_present": all(
            value.get("file_sha256") is not None for value in row["artifacts"].values()
        ),
        "provenance_error_code": provenance.get("error_code"),
        "artifact_triad_failure_is_policy_mismatch_not_missing_files": (
            evidence["checks"]["artifact_triad_matches"] is False
            and provenance.get("error_code") is None
        ),
        "driver_atomic_terminal_recorded": row["recorded_driver_flags"]["terminal_state_atomic"],
        "continuation_atomic_check_requires_allowlisted_code": evidence["checks"][
            "terminal_state_atomic"
        ],
        "source_review_basis": [
            "patchloop/agent/model.py:918-925",
            "patchloop/agent/runner.py:3287-3312",
            "patchloop/evals/rapid_row_continuation.py:491-533",
        ],
    }


def build_rapid_r24_halted_audit(
    repository: str | Path = ".",
) -> dict[str, Any]:
    """Build one zero-call audit from the consumed public R24 evidence."""

    root = Path(repository).resolve()
    candidate, candidate_record = _load_sealed_json(root, CANDIDATE_PATH)
    rehearsal, rehearsal_record = _load_sealed_json(root, REHEARSAL_PATH)
    qualification, qualification_record = _load_sealed_json(root, QUALIFICATION_PATH)
    plan, plan_record = _load_sealed_json(root, PLAN_PATH)
    if not (
        candidate.get("execution_hash")
        == rehearsal.get("execution_hash")
        == plan.get("execution_hash")
        == EXECUTION_HASH
        and qualification.get("candidate", {}).get("execution_hash") == EXECUTION_HASH
    ):
        raise ContractError("Rapid R24 execution binding differs")
    journal, bundle_record = _load_journal(root, rehearsal)
    image_rows, image_record = _load_image_receipt(root)
    final = journal[-1]
    terminals = {
        item["schedule_order"]: item for item in journal if item.get("event") == "row-terminal"
    }
    if list(terminals) != [1, 2, 3]:
        raise ContractError("Rapid R24 terminal row order differs")
    state_path = ensure_within(root, STATE_PATH.as_posix())
    store = ReadOnlyTraceStore(state_path)
    runs = {row["run_id"]: row for row in store.list_runs()}
    task = _load_public_task(ensure_within(root, PUBLIC_TASK_PATH.as_posix()))
    capabilities = rehearsal["all_row_capabilities"]
    rows = [
        _row_audit(
            root=root,
            schedule_row=schedule_row,
            capability=capability,
            terminal=terminals.get(schedule_row["order"]),
            store=store,
            runs=runs,
            state_path=state_path,
            task=task,
        )
        for schedule_row, capability in zip(candidate["schedule"], capabilities, strict=True)
    ]
    started = [row for row in rows if row["status"] != "not_started"]
    if sum(row["model_cost_nanos"] for row in started) != final["accrued_cost_nanos"]:
        raise ContractError("Rapid R24 settled cost differs")
    variants = []
    for variant in ("lean-harness-v25", "lean-harness-v27"):
        selected = [row for row in rows if row["variant"] == variant]
        observed = [row for row in selected if row["status"] != "not_started"]
        variants.append(
            {
                "variant": variant,
                "scheduled_rows": len(selected),
                "started_rows": len(observed),
                "not_started_rows": len(selected) - len(observed),
                "evaluator_reached": sum(row["evaluator_reached"] for row in observed),
                "submission_completed": sum(row["submission_completed"] for row in observed),
                "success_at_budget": sum(row["success_at_budget"] for row in observed),
                "model_cost_nanos": sum(row["model_cost_nanos"] for row in observed),
            }
        )
    body = {
        "schema_version": SCHEMA_VERSION,
        "official": False,
        "execution_hash": EXECUTION_HASH,
        "status": "consumed-halted-incomplete-comparison",
        "runtime_build_hash": candidate["runtime_build_hash"],
        "source_files": {
            "candidate": candidate_record,
            "rehearsal": rehearsal_record,
            "qualification": qualification_record,
            "approved_plan": plan_record,
            "bundle": bundle_record,
            "image_receipt": image_record,
        },
        "execution_observation": {
            "entry_invocations": 1,
            "scheduled_rows": 6,
            "started_rows": len(started),
            "terminal_rows": final["terminal_row_count"],
            "settled_rows": len(started),
            "not_started_rows": final["not_started_row_count"],
            "image_inspect_adapter_calls": image_rows[-1]["inspection_adapter_calls"],
            "local_image_identity_verified": True,
            "recorded_model_calls": sum(row["usage"]["model_calls"] for row in started),
            "recorded_input_token_count_calls": sum(
                row["usage"]["input_token_count_calls"] for row in started
            ),
            "recorded_tool_calls": sum(row["usage"]["tool_calls"] for row in started),
            "evaluator_reached_rows": sum(row["evaluator_reached"] for row in started),
            "submission_completed_rows": sum(row["submission_completed"] for row in started),
            "successful_rows": sum(row["success_at_budget"] for row in started),
            "model_cost_nanos": final["accrued_cost_nanos"],
            "cost_fully_settled": final["cost_fully_settled"],
            "schedule_fully_observed": final["schedule_fully_observed"],
            "reserve_nanos": journal[0]["full_schedule_reserve_nanos"],
            "hard_cap_nanos": journal[0]["hard_cap_nanos"],
            "terminal_content_hash": final["content_hash"],
            "halt_reason_codes": final["reason_codes"],
        },
        "variants": variants,
        "rows": rows,
        "failure_diagnosis": {
            "v25_row_1": {
                "classification": "self-directed-exploration-exhausted-before-plan",
                "information_actions": rows[0]["usage"]["tool_calls"],
                "first_mutation": rows[0]["workflow_diagnosis"]["first_mutation_evidence"][
                    "event_sequence"
                ],
                "exploration_stop": rows[0]["exploration_stop"],
            },
            "v27_lifecycle_plan_admission": _lifecycle_schema_observation(rows),
            "row_3_provider_timeout_and_halt": _provider_timeout_observation(rows, journal, root),
            "comparison_conclusion": (
                "No row reached the evaluator and half the schedule was unstarted; "
                "R24 cannot compare or promote V27."
            ),
        },
        "source_review": [_file_record(root, relative) for relative in SOURCE_FILES],
        "evidence_boundary": {
            "public_task_and_agent_visible_events_only": True,
            "public_tool_inputs_and_visible_check_results_only": True,
            "raw_reasoning_read": False,
            "llm_response_text_read": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "provider_calls_added_by_audit": 0,
            "docker_calls_added_by_audit": 0,
            "agent_calls_added_by_audit": 0,
            "evaluator_calls_added_by_audit": 0,
            "visible_check_calls_added_by_audit": 0,
            "network_calls_added_by_audit": 0,
            "state_mutations_added_by_audit": 0,
            "cost_added_by_audit_nanos": 0,
            "complete_batch_diagnosis_synthesized": False,
        },
        "disposition": {
            "same_candidate_retry_authorized": False,
            "remaining_rows_authorized_to_resume": False,
            "v25_v27_comparison": "inconclusive-infrastructure-confounded-and-incomplete",
            "v27_promoted": False,
            "quality_or_efficiency_claim": False,
            "runtime_fix_implemented": False,
            "successor_candidate_created": False,
            "paid_authority_remaining": False,
            "next_offline_seam": (
                "project lifecycle component identities as machine-selectable bindings and "
                "return exact relational mismatch feedback before another candidate review"
            ),
        },
    }
    return {**body, "content_hash": sha256_json(body)}


def audit_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("Rapid R24 halted audit hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_rapid_r24_halted_audit(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_rapid_r24_halted_audit(root)
    target = ensure_within(root, AUDIT_PATH.as_posix())
    content = audit_bytes(value)
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.read_bytes() != content:
            raise ContractError("existing Rapid R24 halted audit differs; never overwrite")
        return value
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return value


def load_rapid_r24_halted_audit(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, AUDIT_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("Rapid R24 halted audit is unavailable") from exc
    if not isinstance(value, dict) or audit_bytes(value) != raw:
        raise ContractError("Rapid R24 halted audit bytes differ")
    if value != build_rapid_r24_halted_audit(root):
        raise ContractError("Rapid R24 halted audit source binding differs")
    return value


__all__ = [
    "AUDIT_PATH",
    "BUNDLE_PATH",
    "EXECUTION_HASH",
    "build_rapid_r24_halted_audit",
    "load_rapid_r24_halted_audit",
    "materialize_rapid_r24_halted_audit",
]
