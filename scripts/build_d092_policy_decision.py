from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from patchloop.contracts import RunEvent
from patchloop.evals.policy_replay import (
    PolicyEvaluation,
    PublicTrajectory,
    aggregate_policy_replays,
    project_public_trajectory,
    replay_absolute_context_ceiling,
    replay_relative_context_growth,
    replay_repeated_rejection,
    select_panel_decision,
)
from patchloop.util import sha256_bytes, sha256_json

RECORDED_AT = "2026-08-04T10:30:30Z"


@dataclass(frozen=True, slots=True)
class SourceDescriptor:
    source_id: str
    path: str
    bytes: int
    file_sha256: str
    experiment_ids: tuple[str, ...]


SOURCES = (
    SourceDescriptor(
        source_id="d082_four_run_readiness_seal",
        path="reports/live-pilot/generic-baseline-readiness-v2v5-20260803-r3.json",
        bytes=27_641,
        file_sha256=(
            "sha256:2a8f650e73e01aed9d629290627999232ec6aebd1769d2179bc22f084ddbede2"
        ),
        experiment_ids=("generic-baseline-readiness-v2v5-20260803-r3",),
    ),
    SourceDescriptor(
        source_id="d086_condition_neutral_pilot_seal",
        path=(
            "reports/live-pilot/"
            "dev-validation-condition-neutral-v2v5-pilot-20260803-r1.json"
        ),
        bytes=17_403,
        file_sha256=(
            "sha256:520ae8408c4e090a2c66a0ed3b2c5c29738762eec1b4f7d87b9452e551635464"
        ),
        experiment_ids=("dev-validation-condition-neutral-v2v5-pilot-20260803-r1",),
    ),
    SourceDescriptor(
        source_id="d088_twelve_run_campaign_seal",
        path=(
            "reports/live-pilot/"
            "dev-no-memory-condition-neutral-accrued-cap-20260804-r1.json"
        ),
        bytes=32_251,
        file_sha256=(
            "sha256:2e24bfb0d98c2a7b2b0d8b5bf80c238ae048d782ce43c1cf08a2c10a6c6b5269"
        ),
        experiment_ids=("dev-no-memory-condition-neutral-accrued-cap-20260804-r1",),
    ),
    SourceDescriptor(
        source_id="d090_anyio_probe_seal",
        path=(
            "reports/live-pilot/"
            "anyio-workflow-completion-budget-only-v2v5-20260804-r1.json"
        ),
        bytes=13_652,
        file_sha256=(
            "sha256:06006c95454618b7adcea305465fa63611d2043c70aaa3e1df2de9a3f5a192f1"
        ),
        experiment_ids=("anyio-workflow-completion-budget-only-v2v5-20260804-r1",),
    ),
    SourceDescriptor(
        source_id="d091_anyio_public_trajectory_audit",
        path="reports/live-pilot/artifacts/d091-anyio-public-trajectory-audit.json",
        bytes=23_039,
        file_sha256=(
            "sha256:74b6b229520d3358e7fbd33faad3b0be532405bbe5711a35c4d064114ba8e9a7"
        ),
        experiment_ids=(
            "dev-no-memory-condition-neutral-accrued-cap-20260804-r1",
            "anyio-workflow-completion-budget-only-v2v5-20260804-r1",
        ),
    ),
)

RUN_IDS = (
    "run_aa9c911512a547d2",
    "run_3995a029dc1f4b19",
    "run_f29df61ba1bc455a",
    "run_741ad42bf680486a",
    "run_c355405d826641b9",
    "run_eece333f601040b1",
    "run_28c86262518b4bba",
    "run_b6038236132749e1",
    "run_697fc8ab4ab04890",
    "run_277e06953fc14232",
    "run_c6683ae9a038435c",
    "run_4613c65b2a254349",
    "run_725807ab880a4719",
    "run_c04aa62b587d415e",
    "run_d17e180d1e344650",
    "run_d5c54d65ab6b4a60",
    "run_c0e186e798024698",
    "run_e444de1bb20a4325",
)

EXPERIMENT_RUN_COUNTS = {
    "generic-baseline-readiness-v2v5-20260803-r3": 4,
    "dev-validation-condition-neutral-v2v5-pilot-20260803-r1": 1,
    "dev-no-memory-condition-neutral-accrued-cap-20260804-r1": 12,
    "anyio-workflow-completion-budget-only-v2v5-20260804-r1": 1,
}

COMMON_MODEL_TUPLE = {
    "provider": "openai",
    "model_id": "gpt-5.4-mini-2026-03-17",
    "reasoning_effort": "medium",
    "reasoning_mode": "standard",
    "service_tier": "default",
    "max_output_tokens": 25_000,
    "transport_max_retries": 0,
}

COMMON_RUNTIME_TUPLE = {
    "memory_condition": "no_memory",
    "memory_max_context_tokens": 2_000,
    "system_prompt_hash": (
        "sha256:441c71fdea2defed14f06b32c3fba7a7aaa19f7a3ca749bc994e72708d8a733b"
    ),
    "tool_schema_version": "v2",
    "tool_schema_hash": (
        "sha256:2ee296c2cf515bf2e0937ec1727dc02046a8560581d39b71246c5b91eccf0827"
    ),
    "context_policy_version": "phase-evidence-v5",
    "max_model_calls": None,
    "max_tool_calls": None,
    "wall_clock_timeout_seconds": 1_800,
}


class D092BuildError(RuntimeError):
    pass


def _source_bindings(repo_root: Path) -> dict[str, dict[str, object]]:
    bindings: dict[str, dict[str, object]] = {}
    for source in SOURCES:
        path = repo_root / source.path
        data = path.read_bytes()
        actual_hash = sha256_bytes(data)
        if len(data) != source.bytes or actual_hash != source.file_sha256:
            raise D092BuildError(f"source drift: {source.path}")
        bindings[source.source_id] = {
            "path": source.path,
            "bytes": source.bytes,
            "file_sha256": source.file_sha256,
            "experiment_ids": list(source.experiment_ids),
            "read_mode": "bytes-for-content-address-only",
        }
    return bindings


def _connect_read_only(state_path: Path) -> sqlite3.Connection:
    if not state_path.is_file():
        raise D092BuildError(f"state database not found: {state_path}")
    connection = sqlite3.connect(
        state_path.resolve().as_uri() + "?mode=ro&immutable=1",
        uri=True,
    )
    connection.execute("PRAGMA query_only=ON")
    if connection.execute("PRAGMA query_only").fetchone() != (1,):
        connection.close()
        raise D092BuildError("SQLite query_only mode was not enforced")
    return connection


def _load_run(
    connection: sqlite3.Connection,
    run_id: str,
) -> tuple[dict[str, Any], tuple[RunEvent, ...]]:
    manifest_row = connection.execute(
        "SELECT manifest_json FROM runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    if manifest_row is None:
        raise D092BuildError(f"missing manifest: {run_id}")
    event_rows = connection.execute(
        "SELECT event_json FROM events WHERE run_id = ? ORDER BY sequence",
        (run_id,),
    ).fetchall()
    if not event_rows:
        raise D092BuildError(f"missing event stream: {run_id}")
    manifest = json.loads(manifest_row[0])
    events = tuple(RunEvent.model_validate_json(row[0]) for row in event_rows)
    return manifest, events


def _validate_manifest(manifest: dict[str, Any], *, run_id: str) -> None:
    if manifest.get("run_id") != run_id:
        raise D092BuildError(f"manifest run ID mismatch: {run_id}")
    model = manifest.get("model")
    memory = manifest.get("memory")
    budget = manifest.get("budget")
    experiment = manifest.get("experiment")
    if not all(isinstance(item, dict) for item in (model, memory, budget, experiment)):
        raise D092BuildError(f"malformed manifest tuple: {run_id}")
    assert isinstance(model, dict)
    assert isinstance(memory, dict)
    assert isinstance(budget, dict)
    assert isinstance(experiment, dict)
    for key, expected in COMMON_MODEL_TUPLE.items():
        if model.get(key) != expected:
            raise D092BuildError(f"model tuple drift for {run_id}: {key}")
    checks = {
        "memory_condition": memory.get("condition"),
        "memory_max_context_tokens": memory.get("max_context_tokens"),
        "tool_schema_version": manifest.get("tool_schema_version"),
        "context_policy_version": manifest.get("context_policy_version"),
        "max_model_calls": budget.get("max_model_calls"),
        "max_tool_calls": budget.get("max_tool_calls"),
        "wall_clock_timeout_seconds": budget.get("wall_clock_timeout_seconds"),
    }
    for key, actual in checks.items():
        if actual != COMMON_RUNTIME_TUPLE[key]:
            raise D092BuildError(f"runtime tuple drift for {run_id}: {key}")
    if experiment.get("experiment_id") not in EXPERIMENT_RUN_COUNTS:
        raise D092BuildError(f"unexpected experiment for {run_id}")
    if type(experiment.get("repetition")) is not int:
        raise D092BuildError(f"invalid repetition for {run_id}")
    if type(experiment.get("schedule_order")) is not int:
        raise D092BuildError(f"invalid schedule order for {run_id}")
    if budget.get("max_total_tokens") not in {1_600_000, 2_000_000, 2_400_000}:
        raise D092BuildError(f"unexpected total-token ceiling for {run_id}")


def _trajectory_row(
    manifest: dict[str, Any],
    trajectory: PublicTrajectory,
) -> dict[str, object]:
    experiment = manifest["experiment"]
    budget = manifest["budget"]
    marker_counts = Counter(marker.kind for marker in trajectory.progress_markers)
    event_counts = Counter(event.type.value for event in trajectory.events)
    return {
        "run_id": trajectory.run_id,
        "task_id": trajectory.task_id,
        "experiment_id": experiment["experiment_id"],
        "repetition": experiment["repetition"],
        "schedule_order": experiment["schedule_order"],
        "harness_git_commit": manifest["harness_git_commit"],
        "max_total_tokens": budget["max_total_tokens"],
        "event_count": len(trajectory.events),
        "model_calls": trajectory.total_model_calls,
        "model_tokens": trajectory.total_model_tokens,
        "tool_calls": trajectory.total_tool_calls,
        "apply_rejection_count": len(trajectory.rejections),
        "context_observation_count": len(trajectory.contexts),
        "maximum_context_characters": max(
            item.context_characters for item in trajectory.contexts
        ),
        "progress_marker_counts": {
            key: marker_counts.get(key, 0)
            for key in (
                "forward_phase",
                "patch_applied",
                "visible_check_passed",
                "submission_attempted",
                "submission_accepted",
            )
        },
        "model_generation_blocked_count": event_counts.get(
            "ModelGenerationBlocked", 0
        ),
        "terminal_event_type": trajectory.events[-1].type.value,
        "public_event_projection_hash": trajectory.public_event_projection_hash,
    }


def _policy_projection(
    evaluation: PolicyEvaluation,
) -> dict[str, object]:
    return {"evaluation": evaluation.to_dict()}


def _build_replays(
    trajectories: list[PublicTrajectory],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    task_ids = sorted({item.task_id for item in trajectories})
    rejection_rows: list[dict[str, object]] = []
    relative_rows: list[dict[str, object]] = []
    sensitivity_rows: list[dict[str, object]] = []
    for threshold in range(3, 11):
        results = [
            replay_repeated_rejection(item, threshold=threshold)
            for item in trajectories
        ]
        evaluation = aggregate_policy_replays(results, panel_task_ids=task_ids)
        rejection_rows.append(_policy_projection(evaluation))
    for multiplier in (2, 4, 8):
        for minimum_calls in (8, 16, 32):
            results = [
                replay_relative_context_growth(
                    item,
                    multiplier=multiplier,
                    minimum_completed_model_calls=minimum_calls,
                )
                for item in trajectories
            ]
            evaluation = aggregate_policy_replays(results, panel_task_ids=task_ids)
            relative_rows.append(_policy_projection(evaluation))
    for maximum_characters in (80_000, 85_000, 90_000):
        results = [
            replay_absolute_context_ceiling(
                item,
                maximum_context_characters=maximum_characters,
            )
            for item in trajectories
        ]
        evaluation = aggregate_policy_replays(
            results,
            panel_task_ids=task_ids,
            admission_scope=False,
        )
        sensitivity_rows.append(_policy_projection(evaluation))
    return rejection_rows, relative_rows, sensitivity_rows


def build_manifest(
    *,
    repo_root: Path,
    state_path: Path,
    recorded_at: str,
) -> dict[str, object]:
    source_binding = _source_bindings(repo_root)
    manifests: list[dict[str, Any]] = []
    trajectories: list[PublicTrajectory] = []
    connection = _connect_read_only(state_path)
    try:
        for run_id in RUN_IDS:
            manifest, events = _load_run(connection, run_id)
            _validate_manifest(manifest, run_id=run_id)
            manifests.append(manifest)
            trajectories.append(
                project_public_trajectory(events, task_id=manifest["task_id"])
            )
    finally:
        connection.close()

    experiment_counts = Counter(
        manifest["experiment"]["experiment_id"] for manifest in manifests
    )
    if dict(experiment_counts) != EXPERIMENT_RUN_COUNTS:
        raise D092BuildError("primary panel experiment coverage drift")
    task_ids = sorted({item.task_id for item in trajectories})
    if len(task_ids) != 8:
        raise D092BuildError("primary panel must contain exactly eight tasks")
    if sum(len(item.events) for item in trajectories) != 4_079:
        raise D092BuildError("primary panel public event count drift")

    rejection_rows, relative_rows, sensitivity_rows = _build_replays(trajectories)
    evaluations = [
        row["evaluation"]
        for row in rejection_rows + relative_rows + sensitivity_rows
    ]
    admitted_count = sum(bool(row["admitted"]) for row in evaluations)
    typed_evaluations = [
        aggregate_policy_replays(
            [
                replay_repeated_rejection(item, threshold=threshold)
                for item in trajectories
            ],
            panel_task_ids=task_ids,
        )
        for threshold in range(3, 11)
    ]
    for multiplier in (2, 4, 8):
        for minimum_calls in (8, 16, 32):
            typed_evaluations.append(
                aggregate_policy_replays(
                    [
                        replay_relative_context_growth(
                            item,
                            multiplier=multiplier,
                            minimum_completed_model_calls=minimum_calls,
                        )
                        for item in trajectories
                    ],
                    panel_task_ids=task_ids,
                )
            )
    decision = select_panel_decision(typed_evaluations)
    if admitted_count != 0 or decision != (
        "retain-current-policy-and-count-qualified-budget-terminal-as-agent-failure"
    ):
        raise D092BuildError("unexpected policy admission result")

    trajectory_rows = [
        _trajectory_row(manifest, trajectory)
        for manifest, trajectory in zip(manifests, trajectories, strict=True)
    ]
    panel_projection_hash = sha256_json(
        {
            "schema_version": "public-policy-panel-projection-v1",
            "runs": [
                {
                    "run_id": row["run_id"],
                    "task_id": row["task_id"],
                    "public_event_projection_hash": row[
                        "public_event_projection_hash"
                    ],
                }
                for row in trajectory_rows
            ],
        }
    )
    body = {
        "schema_version": "public-cross-task-policy-decision-v1",
        "milestone": "D-092 offline public stall-policy replay",
        "recorded_at": recorded_at,
        "evidence_kind": "bounded-public-metadata-counterfactual-replay",
        "source_binding": source_binding,
        "audit_scope": {
            "durable_manifest_metadata_read": True,
            "durable_public_event_metadata_read": True,
            "portable_report_bytes_hashed_without_semantic_outcome_read": True,
            "result_json_read": False,
            "qualification_detail_read": False,
            "private_task_or_hidden_assertion_read": False,
            "reference_or_candidate_patch_body_read": False,
            "model_request_or_response_body_read": False,
            "tool_input_or_output_artifact_body_read": False,
            "credential_read_or_logged": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0.0,
        },
        "panel_contract": {
            "run_count": len(trajectories),
            "task_count": len(task_ids),
            "task_ids": task_ids,
            "public_event_count": sum(len(item.events) for item in trajectories),
            "experiment_run_counts": dict(experiment_counts),
            "sealed_qualification_claim": "18/18 trace-qualified",
            "qualification_recomputed_in_d092": False,
            "common_model_tuple": COMMON_MODEL_TUPLE,
            "common_runtime_tuple": COMMON_RUNTIME_TUPLE,
            "varying_noncausal_fields": {
                "harness_git_commits": sorted(
                    {manifest["harness_git_commit"] for manifest in manifests}
                ),
                "max_total_token_ceilings": sorted(
                    {manifest["budget"]["max_total_tokens"] for manifest in manifests}
                ),
                "interpretation": (
                    "bounded process-policy replay only; not a causal performance "
                    "comparison or denominator"
                ),
            },
            "excluded_primary_strata": {
                "d075_d077_call_limited_runs": (
                    "different model-call admission ceilings"
                ),
                "d079_extended_wall_run": "different 7200-second wall ceiling",
            },
        },
        "progress_contract": {
            "progress_markers": [
                "forward PhaseChanged",
                "PatchApplied",
                "first passing run_check per check_id and worktree_diff_hash",
                "SubmissionAttempted",
                "SubmissionAccepted",
            ],
            "false_stop_rule": (
                "any later public progress marker after the candidate trigger"
            ),
            "false_stop_false_interpretation": (
                "no later progress observed in this trace; not a future safety proof"
            ),
            "observed_suffix_interpretation": (
                "observed post-trigger resource suffix; not causal savings"
            ),
            "rejection_fingerprint": {
                "included": [
                    "tool",
                    "status",
                    "error_code",
                    "error_details.stage",
                    "error_details.reason",
                    "correlated ToolCalled.worktree_diff_hash",
                ],
                "excluded": [
                    "patch_or_input_or_candidate_hash",
                    "normalized_call_hash",
                    "error_message_or_guidance",
                    "artifact_id_or_path_or_body",
                    "action_or_correlation_id",
                    "event_sequence",
                ],
                "correlation_use": (
                    "join validation only; correlation ID is not emitted or hashed"
                ),
            },
        },
        "candidate_grid": {
            "repeated_rejection_thresholds": list(range(3, 11)),
            "relative_context_growth": {
                "multipliers": [2, 4, 8],
                "minimum_completed_model_calls_since_progress": [8, 16, 32],
            },
            "absolute_context_sensitivity_characters": [80_000, 85_000, 90_000],
            "admission_gates": {
                "zero_false_stops": True,
                "minimum_safe_intercept_task_count": 3,
                "minimum_observed_suffix_token_or_wall_fraction_ppm": 200_000,
                "leave_one_task_out_retains_all_gates": True,
            },
            "absolute_context_is_admission_candidate": False,
        },
        "replay_projection": {
            "panel_projection_hash": panel_projection_hash,
            "runs": trajectory_rows,
            "repeated_rejection": rejection_rows,
            "relative_context_growth": relative_rows,
            "absolute_context_sensitivity": sensitivity_rows,
        },
        "decision": {
            "selected": decision,
            "admitted_candidate_count": admitted_count,
            "runtime_policy_action": "retain-current-runtime-policy",
            "qualified_budget_terminal_outcome": "agent_failure",
            "outcome_binding_status": "selected-but-denominator-binding-pending",
            "repeated_rejection_result": (
                "not-admitted: every tested threshold that intercepted D-089 also "
                "false-stopped later public progress"
            ),
            "relative_context_result": (
                "not-admitted: every tested candidate had a false stop or lacked "
                "cross-task generality and leave-one-task-out stability"
            ),
            "absolute_context_result": (
                "sensitivity-only: 90000 characters safely intercepted only the "
                "observed D-089 AnyIO run and is post-hoc single-task evidence"
            ),
        },
        "claims_boundary": {
            "runtime_guard_added_or_changed": False,
            "historical_run_or_gate_reinterpreted": False,
            "live_execution_authorized": False,
            "paid_authority_created": False,
            "comparison_denominator_opened": False,
            "no_memory_baseline_opened": False,
            "memory_review_or_admission_or_index_opened": False,
            "core_experiment_opened": False,
            "hidden_correctness_used_for_policy_selection": False,
            "memory_effect_claimed": False,
            "current_policy_optimality_claimed": False,
        },
        "next_gate": {
            "gate": "condition-neutral-denominator-admission-binding",
            "required_binding": [
                "exact four-condition execution plan",
                "RunManifest",
                "trace qualification",
                "report aggregation",
                "original task and repetition identity",
            ],
            "budget_terminal_rule": (
                "a terminal trace-qualified budget stop remains an agent_failure "
                "row and is never dropped, rerun, or replaced"
            ),
            "provider_execution_authorized_by_next_offline_gate": False,
            "memory_or_core_collection_opened_by_next_offline_gate": False,
        },
    }
    semantic_body_hash = sha256_json(body)
    return {
        "schema_version": "public-cross-task-policy-decision-manifest-v1",
        "decision_id": f"d092_{semantic_body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": semantic_body_hash,
        "semantic_body": body,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the D-092 public-only offline policy decision manifest."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--state", type=Path)
    parser.add_argument("--recorded-at", default=RECORDED_AT)
    parser.add_argument(
        "--compact",
        action="store_true",
        help="emit canonical compact JSON instead of reviewer-oriented indentation",
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    state_path = (
        args.state.resolve()
        if args.state is not None
        else repo_root / ".patchloop/state.sqlite3"
    )
    payload = build_manifest(
        repo_root=repo_root,
        state_path=state_path,
        recorded_at=args.recorded_at,
    )
    if args.compact:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
