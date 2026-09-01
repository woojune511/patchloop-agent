"""Deterministic public-only diagnosis of Lean V20 in consumed Rapid R18."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from patchloop.contracts import EventType, PublicTask, RunEvent, RunManifest
from patchloop.errors import ContractError
from patchloop.evals.rapid_driver_policy_label_qualification import R18_RESULT_IDENTITY
from patchloop.util import (
    canonical_json,
    ensure_within,
    load_unique_yaml,
    sha256_bytes,
    sha256_json,
)

SCHEMA_VERSION = "rapid-r18-v20-exploration-public-diagnosis-v1"
DIAGNOSIS_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-v5-terminal-parity-ab-20260827-r18-"
    "v20-exploration-diagnosis-v1.json"
)
R18_RESULT_PATH = Path(R18_RESULT_IDENTITY["path"])
PUBLIC_TASK_PATH = Path("fixtures/task-packages/anyio-interrupt-runner-cleanup-v5/public.yaml")
STATE_PATH = Path(".patchloop/state.sqlite3")
V20_RUN_IDS = (
    "run_rapid_v26_afcc526c747f_02",
    "run_rapid_v26_afcc526c747f_03",
    "run_rapid_v26_afcc526c747f_06",
)

SOURCE_FILES = (
    "patchloop/agent/workflow_successor_v2.py",
    "patchloop/agent/workflow_exploration_gate_successor.py",
    "patchloop/agent/workflow_exploration_gate_activation.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/evals/rapid_r18_exploration_diagnosis.py",
    "scripts/build_rapid_r18_exploration_diagnosis.py",
    "tests/test_rapid_r18_exploration_diagnosis.py",
)


def _source_identity(root: Path, relative: str) -> dict[str, Any]:
    selected = ensure_within(root, relative)
    if selected.is_symlink() or not selected.is_file():
        raise ContractError(f"Rapid R18 diagnosis source is unavailable: {relative}")
    raw = selected.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _load_r18_rows(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    selected = ensure_within(root, R18_RESULT_PATH.as_posix())
    try:
        raw = selected.read_bytes()
        events = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("Consumed Rapid R18 result is unavailable") from exc
    previous: str | None = None
    for event in events:
        if not isinstance(event, dict):
            raise ContractError("Consumed Rapid R18 result event is invalid")
        body = {key: value for key, value in event.items() if key != "content_hash"}
        if event.get("previous_event_hash") != previous or event.get("content_hash") != sha256_json(
            body
        ):
            raise ContractError("Consumed Rapid R18 result chain differs")
        previous = event["content_hash"]
    final = events[-1] if events else {}
    identity = {
        "path": R18_RESULT_PATH.as_posix(),
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "execution_hash": final.get("execution_hash"),
        "final_event_content_hash": final.get("content_hash"),
    }
    if identity != R18_RESULT_IDENTITY:
        raise ContractError("Consumed Rapid R18 result identity differs")
    rows = {}
    for event in events:
        if event.get("event") != "row-terminal":
            continue
        projection = event.get("projected_row")
        if isinstance(projection, dict) and projection.get("variant") == "lean-harness-v20":
            rows[str(event.get("run_id"))] = projection
    if tuple(rows) != V20_RUN_IDS:
        raise ContractError("Consumed Rapid R18 V20 row order differs")
    return identity, rows


def _load_public_task(root: Path) -> tuple[PublicTask, dict[str, Any]]:
    selected = ensure_within(root, PUBLIC_TASK_PATH.as_posix())
    try:
        raw = selected.read_bytes()
        task = PublicTask.model_validate(load_unique_yaml(raw.decode("utf-8")))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("Rapid R18 public task is unavailable") from exc
    identity = {
        "path": PUBLIC_TASK_PATH.as_posix(),
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "public_task_hash": sha256_json(task.model_dump(mode="json")),
        "task_id": task.task_id,
        "task_version": task.task_version,
    }
    return task, identity


def _load_immutable_trace_snapshot(
    state_path: Path,
) -> dict[str, tuple[RunManifest, list[RunEvent]]]:
    """Read only the consumed runs while refusing any nonempty SQLite journal."""

    if not state_path.is_file():
        raise ContractError("Rapid R18 trace state is unavailable")
    for suffix in ("-wal", "-journal"):
        sidecar = Path(str(state_path) + suffix)
        if sidecar.exists() and sidecar.stat().st_size != 0:
            raise ContractError("Rapid R18 trace state has uncheckpointed SQLite data")
    before = state_path.stat()
    connection = sqlite3.connect(
        state_path.as_uri() + "?mode=ro&immutable=1",
        uri=True,
    )
    try:
        snapshot: dict[str, tuple[RunManifest, list[RunEvent]]] = {}
        for run_id in V20_RUN_IDS:
            run_row = connection.execute(
                "SELECT manifest_json FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            event_rows = connection.execute(
                "SELECT event_json FROM events WHERE run_id = ? ORDER BY sequence",
                (run_id,),
            ).fetchall()
            if run_row is None or not event_rows:
                raise ContractError(f"Rapid R18 trace run is unavailable: {run_id}")
            snapshot[run_id] = (
                RunManifest.model_validate_json(run_row[0]),
                [RunEvent.model_validate_json(row[0]) for row in event_rows],
            )
    finally:
        connection.close()
    after = state_path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ContractError("Rapid R18 trace state changed during immutable read")
    return snapshot


def _cas_json(
    event: RunEvent,
    *,
    state_path: Path,
    path: str,
    content_hash: str,
) -> dict[str, Any]:
    artifact_root = (state_path.parent / "artifacts" / "objects" / "sha256").resolve()
    selected = Path(path).resolve()
    if not selected.is_relative_to(artifact_root) or not selected.is_file():
        raise ContractError(f"Rapid R18 diagnosis artifact escapes CAS at {event.sequence}")
    raw = selected.read_bytes()
    if sha256_bytes(raw) != content_hash:
        raise ContractError(f"Rapid R18 diagnosis artifact hash differs at {event.sequence}")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ContractError(
            f"Rapid R18 diagnosis artifact JSON differs at {event.sequence}"
        ) from exc
    if not isinstance(value, dict):
        raise ContractError(f"Rapid R18 diagnosis artifact shape differs at {event.sequence}")
    return value


def _request_projection(event: RunEvent, *, state_path: Path) -> dict[str, Any]:
    path = event.payload.get("request_artifact_path")
    digest = event.payload.get("request_artifact_hash")
    if not isinstance(path, str) or not isinstance(digest, str):
        raise ContractError(f"Rapid R18 request reference differs at {event.sequence}")
    value = _cas_json(event, state_path=state_path, path=path, content_hash=digest)
    lean = value.get("lean_harness_request")
    if not isinstance(lean, dict):
        raise ContractError(f"Rapid R18 Lean request differs at {event.sequence}")
    decision = lean.get("workflow_decision")
    catalog = lean.get("eligible_plan_evidence_catalog")
    causal = lean.get("causal_plan_request_projection")
    if not isinstance(decision, dict) or not isinstance(catalog, dict):
        raise ContractError(f"Rapid R18 request projection differs at {event.sequence}")
    if causal is None:
        spans: list[dict[str, Any]] = []
    elif isinstance(causal, dict):
        source_projection = causal.get("source_projection")
        span_catalog = (
            source_projection.get("source_span_catalog")
            if isinstance(source_projection, dict)
            else None
        )
        raw_spans = span_catalog.get("spans") if isinstance(span_catalog, dict) else None
        if not isinstance(raw_spans, list) or any(not isinstance(item, dict) for item in raw_spans):
            raise ContractError(f"Rapid R18 source-span projection differs at {event.sequence}")
        spans = raw_spans
    else:
        raise ContractError(f"Rapid R18 causal projection differs at {event.sequence}")
    coverage_keys = sorted(
        {
            str(item["coverage_key"])
            for item in spans
            if isinstance(item, dict) and isinstance(item.get("coverage_key"), str)
        }
    )
    allowed = decision.get("allowed_tool_names")
    items = catalog.get("items")
    if not isinstance(allowed, list) or not isinstance(items, list):
        raise ContractError(f"Rapid R18 decision projection differs at {event.sequence}")
    return {
        "model_event_sequence": event.sequence,
        "request_artifact_hash": digest,
        "target": decision.get("target"),
        "allowed_tool_names": allowed,
        "pre_mutation_actions_used": decision.get("pre_mutation_actions_used"),
        "plan_admission_recovery_used": decision.get("plan_admission_recovery_used"),
        "plan_admission_recovery_remaining": decision.get("plan_admission_recovery_remaining"),
        "eligible_catalog_item_count": len(items),
        "source_span_count": len(spans),
        "distinct_source_coverage_count": len(coverage_keys),
        "source_coverage_keys": coverage_keys,
        "plan_selectable": "record_work_plan" in allowed,
        "plan_forced": allowed == ["record_work_plan"],
    }


def _tool_input(event: RunEvent, *, state_path: Path) -> dict[str, Any]:
    reference = event.payload.get("input_artifact")
    if not isinstance(reference, dict):
        raise ContractError(f"Rapid R18 tool input reference differs at {event.sequence}")
    path = reference.get("path")
    digest = reference.get("content_hash")
    if not isinstance(path, str) or not isinstance(digest, str):
        raise ContractError(f"Rapid R18 tool input identity differs at {event.sequence}")
    value = _cas_json(event, state_path=state_path, path=path, content_hash=digest)
    arguments = value.get("input")
    if value.get("tool") != event.payload.get("tool") or not isinstance(arguments, dict):
        raise ContractError(f"Rapid R18 tool input binding differs at {event.sequence}")
    return arguments


def _safe_tool_projection(event: RunEvent, *, state_path: Path) -> dict[str, Any]:
    tool = str(event.payload.get("tool"))
    arguments = _tool_input(event, state_path=state_path)
    selected: dict[str, Any] = {}
    for key in ("path", "query", "check_id", "start_line", "end_line"):
        if key in arguments:
            selected[key] = arguments[key]
    if tool == "record_work_plan":
        exploration = arguments.get("exploration_state")
        dispositions = (
            exploration.get("unknown_dispositions") if isinstance(exploration, dict) else None
        )
        unknowns = arguments.get("unknowns")
        questions = (
            [item.get("question") for item in dispositions if isinstance(item, dict)]
            if isinstance(dispositions, list)
            else []
        )
        selected.update(
            {
                "declared_unknowns": unknowns if isinstance(unknowns, list) else [],
                "disposition_questions": questions,
                "exact_ordered_unknown_match": unknowns == questions,
            }
        )
    return {
        "sequence": event.sequence,
        "tool": tool,
        "arguments": selected,
    }


def _diagnose_run(
    run_id: str,
    row: dict[str, Any],
    *,
    manifest: RunManifest,
    events: list[RunEvent],
    state_path: Path,
    task: PublicTask,
) -> dict[str, Any]:
    if (
        not events
        or [event.sequence for event in events] != list(range(1, len(events) + 1))
        or events[-1].type != EventType.RUN_FAILED
    ):
        raise ContractError(f"Rapid R18 V20 event sequence differs for {run_id}")
    if not (
        manifest.task_id == task.task_id
        and manifest.task_version == task.task_version
        and manifest.tool_schema_version == "v24"
        and manifest.context_policy_version == "phase-evidence-v30"
    ):
        raise ContractError(f"Rapid R18 V20 manifest differs for {run_id}")
    model_events = [event for event in events if event.type == EventType.MODEL_CALLED]
    decisions = [_request_projection(event, state_path=state_path) for event in model_events]
    calls = [event for event in events if event.type == EventType.TOOL_CALLED]
    actions = [_safe_tool_projection(event, state_path=state_path) for event in calls]
    mutations = [event for event in events if event.type == EventType.PATCH_APPLIED]
    rejections = [
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("tool") == "record_work_plan"
    ]
    terminal = events[-1]
    if not (
        row.get("outcome_kind") == "agent_failure"
        and row.get("evaluator_reached") is False
        and row.get("submission_completed") is False
        and terminal.payload.get("error_code") == "PRE_MUTATION_EVIDENCE_EXHAUSTED"
        and not mutations
    ):
        raise ContractError(f"Rapid R18 V20 terminal differs for {run_id}")
    read_paths = [
        action["arguments"]["path"]
        for action in actions
        if action["tool"] == "read_file" and "path" in action["arguments"]
    ]
    plan_actions = [action for action in actions if action["tool"] == "record_work_plan"]
    peak_coverage = max(
        (decision["distinct_source_coverage_count"] for decision in decisions),
        default=0,
    )
    first_plan_ready = next(
        (decision for decision in decisions if decision["plan_selectable"]),
        None,
    )
    return {
        "order": row.get("order"),
        "run_id": run_id,
        "repetition": row.get("repetition"),
        "event_count": len(events),
        "public_event_envelope_hash": sha256_json(
            [event.model_dump(mode="json") for event in events]
        ),
        "decision_history": decisions,
        "tool_actions": actions,
        "tool_counts": dict(sorted(Counter(action["tool"] for action in actions).items())),
        "unique_read_paths": list(dict.fromkeys(read_paths)),
        "plan_ready_decision_count": sum(decision["plan_selectable"] for decision in decisions),
        "first_plan_ready_model_sequence": (
            first_plan_ready["model_event_sequence"] if first_plan_ready else None
        ),
        "plan_attempt_count": len(plan_actions),
        "plan_attempts": plan_actions,
        "admission_rejections": [
            {
                "sequence": event.sequence,
                "attempt": event.payload.get("attempt"),
                "reason_codes": event.payload.get("reason_codes"),
                "plan_gate_id": event.payload.get("plan_gate_id"),
                "eligible_catalog_hash": event.payload.get("eligible_catalog_hash"),
            }
            for event in rejections
        ],
        "peak_distinct_source_coverage": peak_coverage,
        "final_presented_source_coverage": decisions[-1]["distinct_source_coverage_count"],
        "coverage_shrank_without_mutation": bool(
            peak_coverage > decisions[-1]["distinct_source_coverage_count"]
        ),
        "mutation_count": 0,
        "terminal": {
            "sequence": terminal.sequence,
            "error_code": terminal.payload.get("error_code"),
            "error_type": terminal.payload.get("error_type"),
            "message": terminal.payload.get("message"),
        },
    }


def _system_findings(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_run = {row["run_id"]: row for row in rows}
    no_attempt = by_run[V20_RUN_IDS[0]]
    late_rejection = by_run[V20_RUN_IDS[1]]
    early_rejection = by_run[V20_RUN_IDS[2]]
    mismatch_rows = [
        row
        for row in rows
        if row["plan_attempts"]
        and row["plan_attempts"][0]["arguments"].get("exact_ordered_unknown_match") is False
    ]
    if not (
        no_attempt["plan_attempt_count"] == 0
        and no_attempt["plan_ready_decision_count"] >= 1
        and late_rejection["decision_history"][-1]["plan_forced"] is True
        and early_rejection["decision_history"][5]["plan_admission_recovery_used"] is True
        and len(mismatch_rows) == 2
        and all(row["coverage_shrank_without_mutation"] for row in rows)
    ):
        raise ContractError("Rapid R18 V20 systemic finding preconditions differ")
    return {
        "observed": {
            "all_three_terminated_before_mutation": True,
            "plan_became_selectable_before_exhaustion_in_all_rows": True,
            "row_without_plan_attempt": V20_RUN_IDS[0],
            "rows_with_one_plan_rejection": [row["run_id"] for row in mismatch_rows],
            "rejection_reason": "exploration_unknown_disposition_mismatch",
            "declared_unknown_and_disposition_text_were_semantic_paraphrases": True,
            "exact_ordered_text_equality_was_false": True,
            "first_rejection_consumed_recovery_slot": True,
            "recovery_retry_was_not_forced": True,
            "source_coverage_was_non_monotonic_without_mutation": True,
        },
        "source_characterization": {
            "pre_mutation_action_limit": 10,
            "counted_action_types": ["search_files", "read_file", "run_check"],
            "record_work_plan_counts_toward_exploration_limit": False,
            "minimum_distinct_source_coverage_keys": 2,
            "base_layer_forces_plan_at_limit_when_source_read_exists": True,
            "exploration_overlay_can_replace_that_with_terminal_when_coverage_is_low": True,
            "unknown_disposition_questions_must_exactly_equal_declared_unknowns": True,
        },
        "causal_attribution": {
            "class": "plan-gate-liveness-contract-friction",
            "agent_contribution": (
                "The model continued optional exploration after plan admission became available, "
                "and both submitted plans duplicated unknowns with paraphrased text."
            ),
            "harness_contribution": (
                "Readiness was optional and non-monotonic, duplicate semantic text required exact "
                "equality, and the one recovery slot did not reserve an immediate plan retry."
            ),
            "task_semantic_difficulty_measured": False,
            "reason": "no V20 row reached a mutation or evaluator",
        },
        "next_successor_seam": {
            "name": "pinned-plan-gate-liveness-v1",
            "changes": [
                "pin bounded current-diff source spans once the two-range readiness floor is met",
                "force record_work_plan when readiness first becomes constructible",
                "represent each unknown once and derive its disposition binding server-side",
                "after the first invalid plan force one retry before consulting "
                "exploration exhaustion",
            ],
            "offline_acceptance_tests": [
                "readiness survives recent-event compaction without stale-diff authority",
                "the first ready decision exposes only record_work_plan",
                "unknown disposition has no duplicated free-text equality field",
                "one invalid plan yields exactly one forced retry with the same gate and "
                "pinned catalog",
                "a second invalid plan terminates without a third provider dispatch",
                "targeted check evidence cannot evict already pinned current-diff source readiness",
            ],
            "new_paid_candidate_allowed": False,
        },
    }


def build_rapid_r18_exploration_diagnosis(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    state_path = ensure_within(root, STATE_PATH.as_posix())
    result_identity, bundle_rows = _load_r18_rows(root)
    task, task_identity = _load_public_task(root)
    snapshot = _load_immutable_trace_snapshot(state_path)
    rows = [
        _diagnose_run(
            run_id,
            bundle_rows[run_id],
            manifest=snapshot[run_id][0],
            events=snapshot[run_id][1],
            state_path=state_path,
            task=task,
        )
        for run_id in V20_RUN_IDS
    ]
    body = {
        "schema_version": SCHEMA_VERSION,
        "official": False,
        "scope": "consumed-r18-v20-pre-mutation-public-diagnosis",
        "source_result": result_identity,
        "source_trace": {
            "path": STATE_PATH.as_posix(),
            "read_only_immutable_sqlite": True,
            "run_ids": list(V20_RUN_IDS),
            "raw_events_mutated": False,
        },
        "public_task": task_identity,
        "rows": rows,
        "system_findings": _system_findings(rows),
        "source_files": [_source_identity(root, relative) for relative in SOURCE_FILES],
        "evidence_boundary": {
            "public_task_and_agent_visible_request_projection_only": True,
            "tool_input_arguments_projected": True,
            "raw_reasoning_read": False,
            "llm_response_text_read": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "agent_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "network_calls": 0,
            "state_mutations": 0,
            "added_cost_usd": "0",
        },
        "consumed_r18_modified": False,
        "consumed_r18_retry_allowed": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def diagnosis_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("Rapid R18 exploration diagnosis hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_rapid_r18_exploration_diagnosis(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_rapid_r18_exploration_diagnosis(root)
    target = ensure_within(root, DIAGNOSIS_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(diagnosis_bytes(value))
    return value


def load_rapid_r18_exploration_diagnosis(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, DIAGNOSIS_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("Rapid R18 exploration diagnosis is unavailable") from exc
    if diagnosis_bytes(value) != raw:
        raise ContractError("Rapid R18 exploration diagnosis bytes differ")
    if value != build_rapid_r18_exploration_diagnosis(root):
        raise ContractError("Rapid R18 exploration diagnosis source binding differs")
    return value


__all__ = [
    "DIAGNOSIS_PATH",
    "PUBLIC_TASK_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "STATE_PATH",
    "V20_RUN_IDS",
    "build_rapid_r18_exploration_diagnosis",
    "diagnosis_bytes",
    "load_rapid_r18_exploration_diagnosis",
    "materialize_rapid_r18_exploration_diagnosis",
]
