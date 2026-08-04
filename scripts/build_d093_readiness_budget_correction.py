from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from patchloop.util import sha256_bytes, sha256_json

RECORDED_AT = "2026-08-04T13:59:37Z"
D092_RELATIVE_PATH = (
    "reports/live-pilot/artifacts/d092-public-policy-replay-decision.json"
)
D092_BYTES = 52_901
D092_FILE_SHA256 = (
    "sha256:541b890e2b123a5431060e23dcf4544fce3f7b810cb8cb1a560fbcc245b3fe22"
)
D092_BODY_SHA256 = (
    "sha256:6fde1253a7ba92a2cb60b09f05bc070849c1f868e96cc00870cf03eff62782ec"
)
D092_DECISION_ID = (
    "d092_6fde1253a7ba92a2cb60b09f05bc070849c1f868e96cc00870cf03eff62782ec"
)
D092_SOURCE_COMMIT = "4f830cfa9de465e9640da82ecdd20aea412c914d"
D088_RELATIVE_PATH = (
    "reports/live-pilot/"
    "dev-no-memory-condition-neutral-accrued-cap-20260804-r1.json"
)
D088_BYTES = 32_251
D088_FILE_SHA256 = (
    "sha256:2e24bfb0d98c2a7b2b0d8b5bf80c238ae048d782ce43c1cf08a2c10a6c6b5269"
)
D088_BODY_SHA256 = (
    "sha256:b8401884eeffde2c26c9346108c578d8cbf2e24fe4ac84435219a6aa8911c3c3"
)
D088_REPORT_ID = (
    "d088_b8401884eeffde2c26c9346108c578d8cbf2e24fe4ac84435219a6aa8911c3c3"
)
D090_RELATIVE_PATH = (
    "reports/live-pilot/"
    "anyio-workflow-completion-budget-only-v2v5-20260804-r1.json"
)
D090_BYTES = 13_652
D090_FILE_SHA256 = (
    "sha256:06006c95454618b7adcea305465fa63611d2043c70aaa3e1df2de9a3f5a192f1"
)
D090_BODY_SHA256 = (
    "sha256:815881cebc761187636ae2992c5dd4ff95c0c471a0c79d7250373b513a3bc94e"
)
D090_REPORT_ID = (
    "d090_815881cebc761187636ae2992c5dd4ff95c0c471a0c79d7250373b513a3bc94e"
)
ORIGINAL_DECISION = (
    "retain-current-policy-and-count-qualified-budget-terminal-as-agent-failure"
)
CORRECTED_DECISION = (
    "retain-current-policy-and-treat-readiness-budget-terminal-as-inconclusive"
)
EXPECTED_BUDGET_RUNS = {
    "run_4613c65b2a254349": "anyio-interrupt-runner-cleanup",
    "run_e444de1bb20a4325": "anyio-interrupt-runner-cleanup",
}


class D093BuildError(RuntimeError):
    pass


def _require_dict(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D093BuildError(f"{label} must be an object")
    return value


def _read_bound_report(
    *,
    repo_root: Path,
    relative_path: str,
    expected_bytes: int,
    expected_file_sha256: str,
    expected_schema: str,
    expected_report_id: str,
    expected_body_sha256: str,
    label: str,
) -> dict[str, Any]:
    source_bytes = (repo_root / relative_path).read_bytes()
    if len(source_bytes) != expected_bytes:
        raise D093BuildError(f"{label} source byte count drifted")
    if sha256_bytes(source_bytes) != expected_file_sha256:
        raise D093BuildError(f"{label} source file hash drifted")
    try:
        payload = json.loads(source_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D093BuildError(f"{label} source is not valid UTF-8 JSON") from exc
    payload = _require_dict(payload, label=f"{label} wrapper")
    if set(payload) != {
        "schema_version",
        "report_id",
        "semantic_body_hash",
        "semantic_body",
    }:
        raise D093BuildError(f"{label} wrapper keys drifted")
    if payload.get("schema_version") != expected_schema:
        raise D093BuildError(f"{label} wrapper schema drifted")
    if payload.get("report_id") != expected_report_id:
        raise D093BuildError(f"{label} report ID drifted")
    if payload.get("semantic_body_hash") != expected_body_sha256:
        raise D093BuildError(f"{label} semantic body hash drifted")
    body = _require_dict(payload.get("semantic_body"), label=f"{label} body")
    if sha256_json(body) != expected_body_sha256:
        raise D093BuildError(f"{label} semantic body content drifted")
    return body


def _validate_budget_terminal_projection(
    *,
    row: dict[str, Any],
    qualification: dict[str, Any],
    budget_pressure: dict[str, Any],
    expected_run_id: str,
    label: str,
) -> dict[str, Any]:
    if row.get("run_id") != expected_run_id:
        raise D093BuildError(f"{label} run ID drifted")
    if row.get("task_id") != EXPECTED_BUDGET_RUNS[expected_run_id]:
        raise D093BuildError(f"{label} task ID drifted")
    result = row.get("result", row)
    result = _require_dict(result, label=f"{label} result")
    terminal_error = _require_dict(
        result.get("terminal_error"), label=f"{label} terminal error"
    )
    expected_result = {
        "outcome_kind": "agent_failure",
        "agent_submission_status": "failed",
        "evaluation_status": "not_run",
        "official": False,
    }
    for key, expected in expected_result.items():
        if result.get(key) != expected:
            raise D093BuildError(f"{label} result drifted: {key}")
    if terminal_error.get("code") != "MODEL_GENERATION_BUDGET_EXCEEDED":
        raise D093BuildError(f"{label} terminal error code drifted")
    if terminal_error.get("reason_code") != "exact_request_budget_exceeded":
        raise D093BuildError(f"{label} terminal reason drifted")
    if terminal_error.get("generation_started") is not False:
        raise D093BuildError(f"{label} generation-start flag drifted")
    if qualification.get("qualified") is not True:
        raise D093BuildError(f"{label} qualification drifted")
    if qualification.get("evaluation_reached") is not False:
        raise D093BuildError(f"{label} evaluator boundary drifted")
    if budget_pressure.get("binding_dimension") != "total_tokens":
        raise D093BuildError(f"{label} binding dimension drifted")
    if budget_pressure.get("binding_reason") != "exact_request_budget_exceeded":
        raise D093BuildError(f"{label} binding reason drifted")
    exact_request_blocked = budget_pressure.get("exact_request_blocked")
    if exact_request_blocked is None:
        exact_request = _require_dict(
            budget_pressure.get("exact_request"), label=f"{label} exact request"
        )
        exact_request_blocked = exact_request.get("blocked")
    if exact_request_blocked is not True:
        raise D093BuildError(f"{label} exact-request block drifted")
    usage = _require_dict(row.get("usage"), label=f"{label} usage")
    total_tokens = usage.get("total_tokens")
    wall_clock_ms = usage.get("wall_clock_ms")
    if isinstance(total_tokens, bool) or not isinstance(total_tokens, int):
        raise D093BuildError(f"{label} total tokens invalid")
    if isinstance(wall_clock_ms, bool) or not isinstance(wall_clock_ms, int):
        raise D093BuildError(f"{label} wall clock invalid")
    projection = {
        "run_id": expected_run_id,
        "task_id": EXPECTED_BUDGET_RUNS[expected_run_id],
        "raw_runtime_outcome_kind": "agent_failure",
        "agent_submission_status": "failed",
        "evaluation_status": "not_run",
        "official": False,
        "qualified": True,
        "evaluation_reached": False,
        "binding_dimension": "total_tokens",
        "binding_reason": "exact_request_budget_exceeded",
        "generation_started": False,
        "total_tokens": total_tokens,
        "wall_clock_ms": wall_clock_ms,
    }
    return projection


def _round_up_fraction(
    *, value: int, numerator: int, denominator: int, quantum: int
) -> int:
    scaled_denominator = denominator * quantum
    return ((value * numerator + scaled_denominator - 1) // scaled_denominator) * quantum


def _validate_d092(payload: dict[str, Any]) -> dict[str, Any]:
    if set(payload) != {
        "schema_version",
        "decision_id",
        "semantic_body_hash",
        "semantic_body",
    }:
        raise D093BuildError("D-092 wrapper keys drifted")
    if payload.get("schema_version") != (
        "public-cross-task-policy-decision-manifest-v1"
    ):
        raise D093BuildError("D-092 wrapper schema drifted")
    if payload.get("decision_id") != D092_DECISION_ID:
        raise D093BuildError("D-092 decision ID drifted")
    if payload.get("semantic_body_hash") != D092_BODY_SHA256:
        raise D093BuildError("D-092 semantic body hash drifted")
    body = _require_dict(payload.get("semantic_body"), label="D-092 semantic body")
    if sha256_json(body) != D092_BODY_SHA256:
        raise D093BuildError("D-092 semantic body content drifted")

    decision = _require_dict(body.get("decision"), label="D-092 decision")
    expected_decision = {
        "selected": ORIGINAL_DECISION,
        "admitted_candidate_count": 0,
        "runtime_policy_action": "retain-current-runtime-policy",
        "qualified_budget_terminal_outcome": "agent_failure",
        "outcome_binding_status": "selected-but-denominator-binding-pending",
    }
    for key, expected in expected_decision.items():
        if decision.get(key) != expected:
            raise D093BuildError(f"D-092 decision drifted: {key}")

    claims = _require_dict(body.get("claims_boundary"), label="D-092 claims")
    for key in (
        "runtime_guard_added_or_changed",
        "comparison_denominator_opened",
        "no_memory_baseline_opened",
        "memory_review_or_admission_or_index_opened",
        "core_experiment_opened",
    ):
        if claims.get(key) is not False:
            raise D093BuildError(f"D-092 authority boundary drifted: {key}")

    sources = _require_dict(body.get("source_binding"), label="D-092 sources")
    expected_sources = {
        "d088_twelve_run_campaign_seal": {
            "path": D088_RELATIVE_PATH,
            "bytes": D088_BYTES,
            "file_sha256": D088_FILE_SHA256,
        },
        "d090_anyio_probe_seal": {
            "path": D090_RELATIVE_PATH,
            "bytes": D090_BYTES,
            "file_sha256": D090_FILE_SHA256,
        },
    }
    for source_id, expected_fields in expected_sources.items():
        source = _require_dict(sources.get(source_id), label=source_id)
        for key, expected in expected_fields.items():
            if source.get(key) != expected:
                raise D093BuildError(f"D-092 source binding drifted: {source_id}.{key}")

    replay = _require_dict(body.get("replay_projection"), label="D-092 replay")
    runs = replay.get("runs")
    if not isinstance(runs, list) or len(runs) != 18:
        raise D093BuildError("D-092 replay run panel drifted")
    affected = {
        row.get("run_id"): row.get("task_id")
        for row in runs
        if isinstance(row, dict)
        and row.get("model_generation_blocked_count") == 1
        and row.get("terminal_event_type") == "RunFailed"
    }
    if affected != EXPECTED_BUDGET_RUNS:
        raise D093BuildError("D-092 public budget-terminal projection drifted")
    return body


def build_correction(*, repo_root: Path, recorded_at: str) -> dict[str, object]:
    source_path = repo_root / D092_RELATIVE_PATH
    source_bytes = source_path.read_bytes()
    if len(source_bytes) != D092_BYTES:
        raise D093BuildError("D-092 source byte count drifted")
    if sha256_bytes(source_bytes) != D092_FILE_SHA256:
        raise D093BuildError("D-092 source file hash drifted")
    try:
        source_payload = json.loads(source_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D093BuildError("D-092 source is not valid UTF-8 JSON") from exc
    source_body = _validate_d092(source_payload)
    replay = source_body["replay_projection"]

    d088_body = _read_bound_report(
        repo_root=repo_root,
        relative_path=D088_RELATIVE_PATH,
        expected_bytes=D088_BYTES,
        expected_file_sha256=D088_FILE_SHA256,
        expected_schema="condition-neutral-no-memory-campaign-d088-evidence-v1",
        expected_report_id=D088_REPORT_ID,
        expected_body_sha256=D088_BODY_SHA256,
        label="D-088",
    )
    d088_rows = d088_body.get("runs")
    if not isinstance(d088_rows, list):
        raise D093BuildError("D-088 runs must be a list")
    d088_matches = [
        row
        for row in d088_rows
        if isinstance(row, dict) and row.get("run_id") == "run_4613c65b2a254349"
    ]
    if len(d088_matches) != 1:
        raise D093BuildError("D-088 affected run exact-one invariant failed")
    d088_row = d088_matches[0]
    d088_projection = _validate_budget_terminal_projection(
        row=d088_row,
        qualification=_require_dict(
            d088_row.get("qualification"), label="D-088 qualification"
        ),
        budget_pressure=_require_dict(
            d088_row.get("budget_pressure"), label="D-088 budget pressure"
        ),
        expected_run_id="run_4613c65b2a254349",
        label="D-088 affected run",
    )

    d090_body = _read_bound_report(
        repo_root=repo_root,
        relative_path=D090_RELATIVE_PATH,
        expected_bytes=D090_BYTES,
        expected_file_sha256=D090_FILE_SHA256,
        expected_schema="anyio-budget-only-readiness-d090-evidence-v1",
        expected_report_id=D090_REPORT_ID,
        expected_body_sha256=D090_BODY_SHA256,
        label="D-090",
    )
    d090_row = _require_dict(d090_body.get("run"), label="D-090 run")
    d090_projection = _validate_budget_terminal_projection(
        row=d090_row,
        qualification=_require_dict(
            d090_body.get("qualification"), label="D-090 qualification"
        ),
        budget_pressure=_require_dict(
            d090_body.get("budget_pressure"), label="D-090 budget pressure"
        ),
        expected_run_id="run_e444de1bb20a4325",
        label="D-090 affected run",
    )

    affected_public_runs = [
        {
            "run_id": run_id,
            "task_id": task_id,
            "raw_runtime_outcome_kind_preserved": "agent_failure",
            "readiness_disposition": "readiness_inconclusive",
            "readiness_reason": "budget_confounded",
            "historical_exact_run_rerun_allowed": False,
        }
        for run_id, task_id in EXPECTED_BUDGET_RUNS.items()
    ]
    sealed_projections = [d088_projection, d090_projection]
    observed_max_tokens = max(row["total_tokens"] for row in sealed_projections)
    observed_max_wall_ms = max(row["wall_clock_ms"] for row in sealed_projections)
    candidate_max_tokens = _round_up_fraction(
        value=observed_max_tokens,
        numerator=3,
        denominator=2,
        quantum=100_000,
    )
    candidate_wall_seconds = _round_up_fraction(
        value=observed_max_wall_ms,
        numerator=2,
        denominator=1_000,
        quantum=600,
    )
    body = {
        "schema_version": "readiness-budget-outcome-correction-v1",
        "milestone": "D-093 readiness-stage budget outcome correction",
        "recorded_at": recorded_at,
        "source_binding": {
            "d092_policy_decision": {
                "path": D092_RELATIVE_PATH,
                "bytes": D092_BYTES,
                "file_sha256": D092_FILE_SHA256,
                "semantic_body_hash": D092_BODY_SHA256,
                "decision_id": D092_DECISION_ID,
                "source_git_commit": D092_SOURCE_COMMIT,
                "original_selected_decision": ORIGINAL_DECISION,
                "original_runtime_policy_action": "retain-current-runtime-policy",
                "original_budget_terminal_outcome": "agent_failure",
                "original_outcome_binding_status": (
                    "selected-but-denominator-binding-pending"
                ),
                "panel_projection_hash": replay["panel_projection_hash"],
                "candidate_grid_hash": sha256_json(source_body["candidate_grid"]),
                "replay_projection_hash": sha256_json(replay),
            },
            "d088_campaign_seal": {
                "path": D088_RELATIVE_PATH,
                "bytes": D088_BYTES,
                "file_sha256": D088_FILE_SHA256,
                "semantic_body_hash": D088_BODY_SHA256,
                "report_id": D088_REPORT_ID,
                "affected_run_projection_hash": sha256_json(d088_projection),
                "read_mode": "portable-semantic-field-validation",
            },
            "d090_anyio_probe_seal": {
                "path": D090_RELATIVE_PATH,
                "bytes": D090_BYTES,
                "file_sha256": D090_FILE_SHA256,
                "semantic_body_hash": D090_BODY_SHA256,
                "report_id": D090_REPORT_ID,
                "affected_run_projection_hash": sha256_json(d090_projection),
                "read_mode": "portable-semantic-field-validation",
            },
        },
        "cause": {
            "category": "stage-purpose-outcome-misclassification",
            "summary": (
                "D-092 correctly rejected the tested early-stop policies but "
                "prematurely selected a comparison-style failure disposition "
                "while the project is still validating end-to-end readiness."
            ),
            "readiness_objective": (
                "observe terminal, qualified submission and official evaluator "
                "arrival without a binding resource ceiling"
            ),
            "budget_is_target_experimental_factor": False,
            "runtime_or_trace_defect": False,
            "policy_replay_error": False,
            "hidden_or_task_outcome_used": False,
        },
        "preserved_policy_decision": {
            "selected": "retain-current-runtime-policy",
            "admitted_candidate_count": 0,
            "repeated_rejection_result_preserved": True,
            "relative_context_result_preserved": True,
            "absolute_context_sensitivity_preserved": True,
            "candidate_grid_hash": sha256_json(source_body["candidate_grid"]),
            "replay_projection_hash": sha256_json(replay),
            "d092_artifact_byte_immutable": True,
        },
        "corrected_readiness_stage_contract": {
            "schema_version": "workflow-readiness-budget-disposition-v1",
            "corrected_selected_decision": CORRECTED_DECISION,
            "evaluation_stage": "workflow-readiness",
            "evaluation_stage_binding": "explicit-content-addressed-policy",
            "experiment_purpose_inference_allowed": False,
            "raw_runtime_outcome_kind_preserved": "agent_failure",
            "readiness_disposition": "readiness_inconclusive",
            "readiness_reason": "budget_confounded",
            "budget_role": (
                "finite-emergency-safety-ceiling-intended-to-be-non-binding"
            ),
            "budget_is_target_experimental_factor": False,
            "performance_denominator_eligible": False,
            "automatic_rerun_authorized": False,
            "historical_exact_run_rerun_allowed": False,
            "new_successor_readiness_probe_allowed": True,
            "comparison_disposition": "pending-explicit-resource-policy-freeze",
            "comparison_analysis_failure_selected": False,
            "affected_public_runs": affected_public_runs,
            "readiness_completion_gate": {
                "required_true": [
                    "all_rows_started_and_terminal",
                    "all_rows_trace_qualified",
                    "all_rows_submission_accepted",
                    "all_rows_evaluator_reached",
                    "all_rows_official_evaluator",
                    "persisted_qualification_matches_read_only_recomputation",
                    "exact_input_telemetry_complete",
                    "responses_completed",
                    "truncation_disabled",
                ],
                "required_zero": [
                    "infrastructure_errors",
                    "qualification_errors",
                    "diagnostic_errors",
                    "budget_terminal_runs",
                    "terminal_loop_failure_runs",
                    "model_or_tool_call_budget_blocks",
                ],
                "task_success_required": False,
                "hidden_acceptance_required": False,
                "scrr_required": False,
            },
        },
        "correction_boundary": {
            "superseded_d092_fields": [
                "decision.selected analytical suffix",
                "decision.qualified_budget_terminal_outcome as readiness analysis",
                "decision.outcome_binding_status",
                "next_gate.budget_terminal_rule",
            ],
            "original_d092_artifact_modified": False,
            "original_d092_decision_string_modified": False,
            "original_run_result_modified": False,
            "original_journal_or_qualification_modified": False,
            "runtime_policy_modified": False,
            "candidate_grid_or_replay_modified": False,
            "historical_gate_replaced": False,
            "comparison_or_baseline_policy_selected": False,
        },
        "claims_boundary": {
            "readiness_stage_interpretation_corrected": True,
            "workflow_readiness_established": False,
            "budget_sufficiency_established": False,
            "high_headroom_probe_source_frozen": False,
            "high_headroom_probe_execution_authorized": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0.0,
            "comparison_denominator_opened": False,
            "no_memory_baseline_opened": False,
            "memory_review_or_admission_or_index_opened": False,
            "core_experiment_opened": False,
        },
        "next_gate": {
            "gate": "high-headroom-diverse-readiness-source-gate",
            "purpose": (
                "prepare a small no-memory completion panel whose token and wall "
                "limits are emergency ceilings rather than evaluated factors"
            ),
            "candidate_tasks": [
                "anyio-interrupt-runner-cleanup",
                "pyfakefs-makedirs-parent-traversal",
                "hf-hub-xet-endpoint-propagation",
            ],
            "candidate_resource_derivation": {
                "source_run_ids": [
                    "run_4613c65b2a254349",
                    "run_e444de1bb20a4325",
                ],
                "observed_public_maximum_tokens": observed_max_tokens,
                "token_multiplier_numerator": 3,
                "token_multiplier_denominator": 2,
                "token_unrounded_numerator": observed_max_tokens * 3,
                "token_unrounded_denominator": 2,
                "token_rounding_quantum": 100_000,
                "candidate_max_total_tokens": candidate_max_tokens,
                "observed_public_maximum_wall_clock_ms": observed_max_wall_ms,
                "wall_multiplier_numerator": 2,
                "wall_multiplier_denominator": 1,
                "wall_unrounded_milliseconds": observed_max_wall_ms * 2,
                "wall_unit_conversion_milliseconds_per_second": 1_000,
                "wall_rounding_quantum_seconds": 600,
                "candidate_wall_clock_timeout_seconds": candidate_wall_seconds,
                "max_model_calls": None,
                "max_tool_calls": None,
            },
            "candidate_values_are_source_frozen": False,
            "clean_source_commit_required": True,
            "fresh_official_price_check_required": True,
            "fresh_no_call_preflight_required": True,
            "new_execution_hash_required": True,
            "separate_user_cost_approval_required": True,
            "automatic_successor_execution_authorized": False,
            "provider_execution_authorized": False,
        },
    }
    body_hash = sha256_json(body)
    return {
        "schema_version": "readiness-budget-outcome-correction-manifest-v1",
        "correction_id": f"rbocor_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the append-only D-093 readiness budget correction."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--recorded-at", default=RECORDED_AT)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    payload = build_correction(
        repo_root=args.repo_root.resolve(),
        recorded_at=args.recorded_at,
    )
    if args.compact:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
