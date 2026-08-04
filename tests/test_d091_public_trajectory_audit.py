from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import pytest

from patchloop.evals import runner as eval_runner
from patchloop.evals.qualification import load_trace_qualification
from patchloop.state import StateStore
from patchloop.task_loader import load_public_task
from patchloop.util import (
    canonical_json,
    sha256_bytes,
    sha256_json,
    sha256_text,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / ".patchloop"
REPORT_PATH = (
    ROOT
    / "reports/live-pilot/artifacts/d091-anyio-public-trajectory-audit.json"
)
REPORT_FILE_SHA256 = (
    "sha256:74b6b229520d3358e7fbd33faad3b0be532405bbe5711a35c4d064114ba8e9a7"
)
D087_RUN_ID = "run_4613c65b2a254349"
D089_RUN_ID = "run_e444de1bb20a4325"
D087_CONTROL_RUN_ID = "run_b6038236132749e1"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _body() -> dict[str, Any]:
    return _load(REPORT_PATH)["semantic_body"]


def _skip_without_raw() -> StateStore:
    state_path = RUNTIME_ROOT / "state.sqlite3"
    if not state_path.is_file():
        pytest.skip("local immutable D-087/D-089 public trace is unavailable")
    state = StateStore(state_path)
    if not all(state.get_manifest(run_id) for run_id in (D087_RUN_ID, D089_RUN_ID)):
        pytest.skip("local immutable D-087/D-089 manifests are unavailable")
    return state


def _phase_summaries(events: list[Any]) -> dict[str, dict[str, Any]]:
    phase = "INTAKE"
    rows: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "event_count": 0,
            "model_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "reasoning_output_tokens": 0,
            "model_duration_ms": 0,
            "tool_calls": Counter(),
            "tool_successes": 0,
            "tool_failures": 0,
            "loops": 0,
            "tool_replays": 0,
            "patches_prepared": 0,
            "patches_applied": 0,
        }
    )
    phase_started_at: dict[str, Any] = {}
    phase_ended_at: dict[str, Any] = {}

    for event in events:
        if event.type.value == "PhaseChanged":
            phase_ended_at[event.payload["from"]] = event.timestamp
            phase = event.payload["to"]
            phase_started_at[phase] = event.timestamp

        row = rows[phase]
        row["event_count"] += 1
        event_type = event.type.value
        if event_type == "ModelCalled":
            row["model_calls"] += 1
            for source, target in (
                ("input_tokens", "input_tokens"),
                ("output_tokens", "output_tokens"),
                ("reasoning_output_tokens", "reasoning_output_tokens"),
                ("duration_ms", "model_duration_ms"),
            ):
                row[target] += event.payload[source]
        elif event_type == "ToolCalled":
            row["tool_calls"][event.payload["tool"]] += 1
        elif event_type == "ToolSucceeded":
            row["tool_successes"] += 1
        elif event_type == "ToolFailed":
            row["tool_failures"] += 1
        elif event_type == "LoopDetected":
            row["loops"] += 1
        elif event_type == "ToolReplayed":
            row["tool_replays"] += 1
        elif event_type == "PatchPrepared":
            row["patches_prepared"] += 1
        elif event_type == "PatchApplied":
            row["patches_applied"] += 1

    phase_ended_at[phase] = events[-1].timestamp
    for name, row in rows.items():
        if name in {"REPRODUCE", "IMPLEMENT"}:
            row["trace_elapsed_ms"] = round(
                (
                    phase_ended_at[name] - phase_started_at[name]
                ).total_seconds()
                * 1000
            )
            row["tool_calls"] = {
                tool: row["tool_calls"].get(tool, 0)
                for tool in (
                    "search_files",
                    "read_file",
                    "apply_patch",
                    "run_check",
                )
            }
    return rows


def _tail_after(events: list[Any], sequence: int) -> dict[str, Any]:
    tail = [event for event in events if event.sequence > sequence]
    model_events = [event for event in tail if event.type.value == "ModelCalled"]
    tool_events = [event for event in tail if event.type.value == "ToolCalled"]
    return {
        "elapsed_to_terminal_ms": round(
            (
                events[-1].timestamp
                - next(event.timestamp for event in events if event.sequence == sequence)
            ).total_seconds()
            * 1000
        ),
        "model_calls": len(model_events),
        "tokens": sum(event.payload["total_tokens"] for event in model_events),
        "tool_calls": len(tool_events),
        "additional_patches_applied": sum(
            event.type.value == "PatchApplied" for event in tail
        ),
        "rejected_apply_patch_calls": sum(
            event.type.value == "ToolFailed"
            and event.payload.get("tool") == "apply_patch"
            for event in tail
        ),
    }


def test_d091_manifest_is_strict_and_content_addressed() -> None:
    payload = _load(REPORT_PATH)

    assert sha256_bytes(REPORT_PATH.read_bytes()) == REPORT_FILE_SHA256
    assert set(payload) == {
        "schema_version",
        "audit_id",
        "semantic_body_hash",
        "semantic_body",
    }
    assert payload["schema_version"] == "public-trajectory-audit-manifest-v1"
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    assert payload["semantic_body_hash"] == body_hash
    assert payload["audit_id"] == f"d091_{body_hash.removeprefix('sha256:')}"

    body = payload["semantic_body"]
    assert set(body) == {
        "schema_version",
        "milestone",
        "recorded_at",
        "evidence_kind",
        "source_binding",
        "audit_scope",
        "comparison_contract",
        "runs",
        "cross_run_comparison",
        "bounded_counterfactuals",
        "classification",
        "claims_boundary",
        "next_gate",
    }
    assert body["schema_version"] == "anyio-public-trajectory-audit-v1"
    assert set(body["runs"]) == {
        "d087_anyio_repetition_2",
        "d089_budget_only_probe",
    }


def test_d091_nested_schema_and_narrative_are_exact() -> None:
    body = _body()
    source = body["source_binding"]
    assert set(source) == {
        "d088_campaign_seal",
        "d090_probe_seal",
        "d087_predecessors",
        "d089_predecessors",
        "public_task",
    }
    assert set(source["d088_campaign_seal"]) == {
        "path",
        "bytes",
        "file_sha256",
        "experiment_id",
        "execution_hash",
        "run_id",
        "qualification_hash",
        "source_evidence_hash",
    }
    assert set(source["d090_probe_seal"]) == {
        "path",
        "bytes",
        "file_sha256",
        "report_id",
        "semantic_body_hash",
        "experiment_id",
        "execution_hash",
        "run_id",
        "qualification_hash",
        "source_evidence_hash",
    }
    for group_name in ("d087_predecessors", "d089_predecessors"):
        assert set(source[group_name]) == {"suite", "source_gate"}
        assert all(
            set(descriptor) == {"path", "bytes", "sha256"}
            for descriptor in source[group_name].values()
        )
    assert set(source["public_task"]) == {
        "path",
        "task_id",
        "base_commit",
        "public_spec_hash",
    }

    comparison_contract = body["comparison_contract"]
    assert set(comparison_contract) == {
        "same",
        "different",
        "paired_randomized_budget_effect_estimate",
        "causal_budget_attribution_allowed",
        "reason",
    }
    assert set(comparison_contract["same"]) == {
        "task_id",
        "base_commit",
        "model_id",
        "reasoning_effort",
        "reasoning_mode",
        "service_tier",
        "transport_max_retries",
        "max_output_tokens",
        "max_model_calls",
        "max_tool_calls",
        "wall_clock_timeout_seconds",
        "memory_condition",
        "memory_max_context_tokens",
        "system_prompt_hash",
        "tool_schema_version",
        "tool_schema_hash",
        "context_policy_version",
        "call_guard_policy",
    }
    assert set(comparison_contract["different"]) == {
        "d087_total_token_ceiling",
        "d089_total_token_ceiling",
        "d087_repetition",
        "d089_repetition",
        "d087_schedule_order",
        "d089_schedule_order",
        "d087_harness_git_commit",
        "d089_harness_git_commit",
        "experiment_and_execution_identity_equal",
    }
    assert comparison_contract["paired_randomized_budget_effect_estimate"] is False
    assert comparison_contract["causal_budget_attribution_allowed"] is False
    assert comparison_contract["reason"] == (
        "fresh stochastic trajectories differ in repetition, schedule, execution "
        "identity and harness commit; only bounded process observations are compared"
    )

    for run in body["runs"].values():
        assert set(run) == {
            "run_id",
            "terminal_phase",
            "terminal_reason",
            "generation_started_for_blocked_request",
            "trace_qualified",
            "qualification_passed_checks",
            "qualification_total_checks",
            "submission_accepted",
            "evaluator_reached",
            "task_outcome_observed",
            "configured_budget",
            "usage",
            "terminal_budget",
            "trace",
            "phase_summary",
            "tool_and_recovery",
            "post_last_applied_patch",
            "post_last_executed_check",
        }
        assert set(run["configured_budget"]) == {
            "max_total_tokens",
            "wall_clock_timeout_seconds",
        }
        assert set(run["usage"]) == {
            "input_tokens",
            "output_tokens",
            "reasoning_output_tokens",
            "total_tokens",
            "model_calls",
            "input_token_count_calls",
            "tool_calls",
            "wall_clock_ms",
            "model_duration_ms",
            "model_cost_usd",
        }
        assert set(run["terminal_budget"]) == {
            "remaining_tokens",
            "blocked_requested_input_tokens",
            "max_output_tokens",
            "required_tokens",
            "deficit_tokens",
            "same_prefix_next_call_minimum",
            "wall_clock_headroom_ms",
        }
        assert set(run["trace"]) == {
            "events",
            "checkpoints",
            "checkpoint_reproduction_status_unknown",
            "final_completed_checks",
            "final_pending_checks",
            "event_elapsed_ms",
            "phase_transitions",
            "context_builds",
            "context_characters_minimum",
            "context_characters_maximum",
            "context_characters_final",
            "included_event_count_maximum",
            "included_event_count_final",
            "omitted_event_count_final",
            "provider_state_used_count",
            "truncated_tool_result_contexts",
            "observed_input_tokens_minimum",
            "observed_input_tokens_maximum",
            "observed_input_tokens_final",
        }
        assert set(run["phase_summary"]) == {"REPRODUCE", "IMPLEMENT"}
        for phase in run["phase_summary"].values():
            assert set(phase) == {
                "event_count",
                "trace_elapsed_ms",
                "model_calls",
                "input_tokens",
                "output_tokens",
                "reasoning_output_tokens",
                "model_duration_ms",
                "tool_calls",
                "tool_successes",
                "tool_failures",
                "loops",
                "tool_replays",
                "patches_prepared",
                "patches_applied",
            }
            assert set(phase["tool_calls"]) == {
                "search_files",
                "read_file",
                "apply_patch",
                "run_check",
            }
        tools = run["tool_and_recovery"]
        assert set(tools) == {
            "tool_calls",
            "outcomes",
            "patches_prepared",
            "patches_applied",
            "apply_patch_failures",
            "apply_patch_policy_violations",
            "apply_patch_contract_errors",
            "rejected_candidate_count",
            "verified_retry_count",
            "failed_source_failure_sequences",
            "visible_checks_executed",
            "visible_checks_passed",
            "get_diff_calls",
            "finish_task_calls",
            "loops",
        }
        assert set(tools["tool_calls"]) == {
            "search_files",
            "read_file",
            "apply_patch",
            "run_check",
        }
        assert set(tools["outcomes"]) == {"succeeded", "failed", "replayed"}
        assert set(tools["loops"]) == {
            "observed",
            "fully_covered_read",
            "duplicate_search",
            "unclassified",
            "maximum_no_progress_streak",
            "terminal_loop_failure",
        }
        assert set(run["post_last_applied_patch"]) == {
            "last_patch_applied_sequence",
            "elapsed_to_terminal_ms",
            "model_calls",
            "tokens",
            "tool_calls",
            "additional_patches_applied",
            "rejected_apply_patch_calls",
        }
        assert set(run["post_last_executed_check"]) == {
            "last_check_sequence",
            "last_check_passed",
            "elapsed_to_terminal_ms",
            "model_calls",
            "tokens",
            "tool_calls",
            "additional_patches_applied",
            "rejected_apply_patch_calls",
        }

    cross_run = body["cross_run_comparison"]
    assert set(cross_run) == {
        "same_task_process_control",
        "d089_minus_d087",
        "average_total_tokens_per_completed_model_call",
        "post_last_patch_delta_d089_minus_d087",
        "direct_observations",
    }
    control = cross_run["same_task_process_control"]
    assert set(control) == {
        "source",
        "run_id",
        "repetition",
        "schedule_order",
        "total_tokens",
        "model_calls",
        "tool_calls",
        "wall_clock_ms",
        "evaluator_reached",
        "official_evaluator_completed",
        "task_or_hidden_outcome_used",
        "bounded_implication",
    }
    assert control["source"] == (
        "D-087 AnyIO repetition 1 portable process metadata"
    )
    assert control["bounded_implication"] == (
        "the same task reached the evaluator below 1.6M in another fresh "
        "trajectory, so no single observed ceiling is established as necessary"
    )
    assert cross_run["direct_observations"] == [
        "both runs were trace-qualified and ended at the exact-request "
        "total-token guard before submission or evaluator",
        "all 14 executed visible checks across both runs completed but failed",
        "D-089 used more tokens and wall time with fewer model and tool calls than D-087",
        "D-089 spent 90.6 percent of its observed tokens after its only "
        "applied patch without another PatchApplied event",
        "verified rejected-patch retry context had zero failed source sequences in both runs",
        "the same-task D-087 repetition 1 reached the evaluator at 534,853 "
        "tokens, showing large process variance without using its task outcome",
    ]

    assert set(body["bounded_counterfactuals"]) == {
        "d087_exact_next_call",
        "d089_exact_next_call",
        "d089_same_observed_prefix_at_2400000",
        "d089_same_observed_prefix_at_3000000",
        "token_only_escalation_removes_wall_constraint",
        "future_generation_count_or_submission_time_identifiable",
    }
    classification = body["classification"]
    assert set(classification) == {
        "schema_version",
        "method",
        "primary",
        "direct_terminal_trigger",
        "trace_or_recovery_integrity_failure_observed",
        "rejected_patch_rehydration_failure_observed",
        "harness_defect_confirmed",
        "harness_defect_ruled_out",
        "process_nonconvergence_observed",
        "task_outcome_observed",
        "budget_shortage_as_completion_root_cause_proven",
        "more_budget_alone_as_completion_remedy_supported",
        "cross_run_budget_effect_identified",
        "evidence",
    }
    assert classification["schema_version"] == (
        "qualified-process-nonconvergence-classification-v1"
    )
    assert classification["method"] == (
        "deterministic public-trace predicates plus bounded non-causal inference"
    )
    assert classification["primary"] == (
        "qualified-process-nonconvergence-ending-in-budget-terminal"
    )
    assert classification["direct_terminal_trigger"] == (
        "exact-request total-token admission guard"
    )
    assert classification["evidence"] == [
        "both trace qualifications passed and rejected-patch retry source failures were empty",
        "D-089 had no additional PatchApplied event during 68 post-patch "
        "model calls and 96 post-patch tool calls",
        "D-089 had 14 post-patch contract-error candidates and 20 post-patch loop observations",
        "neither run passed a visible check, submitted, reached REVIEW, or reached the evaluator",
        "the two runs are fresh trajectories rather than a paired deterministic replay",
        "a separate same-task trajectory reached the evaluator below the "
        "lower ceiling, so budget necessity is not identified",
    ]

    assert body["claims_boundary"] == {
        "source_artifacts_modified": False,
        "original_gates_replaced": False,
        "d087_immutable": True,
        "d089_immutable_and_hard_consumed": True,
        "provider_calls_made_by_audit": 0,
        "evaluator_calls_made_by_audit": 0,
        "added_model_cost_usd": 0.0,
        "task_outcome_or_hidden_acceptance_observed": False,
        "agent_correctness_score_established": False,
        "harness_root_cause_proven": False,
        "completion_budget_established": False,
        "automatic_rerun_authorized": False,
        "new_budget_policy_authorized": False,
        "prompt_tool_context_change_authorized": False,
        "task_specific_tuning_authorized": False,
        "no_memory_baseline_established": False,
        "comparison_denominator_eligible": False,
        "memory_review_admission_or_index_unlocked": False,
        "core_campaign_unlocked": False,
    }
    next_gate = body["next_gate"]
    assert set(next_gate) == {
        "d091_analysis_complete",
        "new_live_execution_authorized",
        "required_next_action",
        "allowed_evidence",
        "forbidden_inputs",
        "decision_options",
        "budget_freeze_or_live_probe_after_this_artifact",
    }
    assert next_gate["required_next_action"] == (
        "offline condition-neutral decision on repeated invalid-patch handling, "
        "context growth and finite fail-fast policy"
    )
    assert next_gate["forbidden_inputs"] == [
        "hidden acceptance",
        "private assertions",
        "reference patch",
        "task-specific prompt or tool tuning",
    ]
    assert next_gate["decision_options"] == [
        "retain current policy and count bounded budget terminals as agent failures",
        "add a generic repeated-invalid-patch fail-fast guard and validate it offline",
        "add a generic context-growth ceiling and validate it offline",
    ]


def test_d091_sources_and_public_only_boundary_are_exact() -> None:
    body = _body()
    source = body["source_binding"]

    for name in ("d088_campaign_seal", "d090_probe_seal"):
        descriptor = source[name]
        path = ROOT / descriptor["path"]
        content = path.read_bytes()
        assert len(content) == descriptor["bytes"]
        assert sha256_bytes(content) == descriptor["file_sha256"]
    for group_name in ("d087_predecessors", "d089_predecessors"):
        for descriptor in source[group_name].values():
            content = (ROOT / descriptor["path"]).read_bytes()
            assert len(content) == descriptor["bytes"]
            assert sha256_bytes(content) == descriptor["sha256"]

    d088 = _load(ROOT / source["d088_campaign_seal"]["path"])
    d088_body = d088["semantic_body"]
    assert d088_body["experiment"]["experiment_id"] == (
        source["d088_campaign_seal"]["experiment_id"]
    )
    assert d088_body["experiment"]["execution_hash"] == (
        source["d088_campaign_seal"]["execution_hash"]
    )
    d087_row = next(
        row for row in d088_body["runs"] if row["run_id"] == D087_RUN_ID
    )
    assert d087_row["qualification"]["qualification_hash"] == (
        source["d088_campaign_seal"]["qualification_hash"]
    )
    assert d087_row["qualification"]["source_evidence_hash"] == (
        source["d088_campaign_seal"]["source_evidence_hash"]
    )
    projected_d087 = body["runs"]["d087_anyio_repetition_2"]
    assert d087_row["usage"] == {
        key: value
        for key, value in projected_d087["usage"].items()
        if key != "model_duration_ms"
    }
    d087_pressure = d087_row["budget_pressure"]
    assert d087_pressure["total_token_headroom"] == projected_d087[
        "terminal_budget"
    ]["remaining_tokens"]
    for source_key, report_key in (
        ("requested_input_tokens", "blocked_requested_input_tokens"),
        ("max_output_tokens", "max_output_tokens"),
        ("required_tokens", "required_tokens"),
        ("remaining_tokens", "remaining_tokens"),
        ("deficit_tokens", "deficit_tokens"),
    ):
        assert d087_pressure[source_key] == projected_d087["terminal_budget"][
            report_key
        ]
    d087_trace = d087_row["trace"]
    d087_tools = projected_d087["tool_and_recovery"]
    assert {
        "events": d087_trace["events"],
        "checkpoints": d087_trace["checkpoints"],
        "patches_prepared": d087_trace["patches_prepared"],
        "patches_applied": d087_trace["patches_applied"],
        "rejected_candidates": d087_trace["rejected_candidates"],
        "verified_retries": d087_trace["verified_retries"],
        "tool_failures": d087_trace["tool_failures"],
        "loops": d087_trace["loops"],
        "tool_replays": d087_trace["tool_replays"],
        "submission_accepted": d087_trace["submission_accepted"],
    } == {
        "events": projected_d087["trace"]["events"],
        "checkpoints": projected_d087["trace"]["checkpoints"],
        "patches_prepared": d087_tools["patches_prepared"],
        "patches_applied": d087_tools["patches_applied"],
        "rejected_candidates": d087_tools["rejected_candidate_count"],
        "verified_retries": d087_tools["verified_retry_count"],
        "tool_failures": d087_tools["outcomes"]["failed"],
        "loops": d087_tools["loops"]["observed"],
        "tool_replays": d087_tools["outcomes"]["replayed"],
        "submission_accepted": projected_d087["submission_accepted"],
    }
    d088_source = d088_body["source_contract"]
    assert d088_source["suite_path"] == source["d087_predecessors"]["suite"][
        "path"
    ]
    assert d088_source["suite_source_sha256"] == source[
        "d087_predecessors"
    ]["suite"]["sha256"]
    assert d088_source["d087_source_gate_path"] == source[
        "d087_predecessors"
    ]["source_gate"]["path"]
    assert d088_source["d087_source_gate_sha256"] == source[
        "d087_predecessors"
    ]["source_gate"]["sha256"]

    control = next(
        row for row in d088_body["runs"] if row["run_id"] == D087_CONTROL_RUN_ID
    )
    projected_control = body["cross_run_comparison"][
        "same_task_process_control"
    ]
    assert {
        "run_id": control["run_id"],
        "repetition": control["repetition"],
        "schedule_order": control["order"],
        "total_tokens": control["usage"]["total_tokens"],
        "model_calls": control["usage"]["model_calls"],
        "tool_calls": control["usage"]["tool_calls"],
        "wall_clock_ms": control["usage"]["wall_clock_ms"],
        "evaluator_reached": control["qualification"]["evaluation_reached"],
        "official_evaluator_completed": control["result"]["official"],
    } == {
        key: projected_control[key]
        for key in (
            "run_id",
            "repetition",
            "schedule_order",
            "total_tokens",
            "model_calls",
            "tool_calls",
            "wall_clock_ms",
            "evaluator_reached",
            "official_evaluator_completed",
        )
    }
    assert projected_control["task_or_hidden_outcome_used"] is False

    d090 = _load(ROOT / source["d090_probe_seal"]["path"])
    assert d090["report_id"] == source["d090_probe_seal"]["report_id"]
    assert d090["semantic_body_hash"] == source["d090_probe_seal"][
        "semantic_body_hash"
    ]
    assert d090["semantic_body"]["experiment"]["execution_hash"] == (
        source["d090_probe_seal"]["execution_hash"]
    )
    assert d090["semantic_body"]["run"]["run_id"] == D089_RUN_ID
    d090_body = d090["semantic_body"]
    projected_d089 = body["runs"]["d089_budget_only_probe"]
    projected_d090_usage = {
        key: value
        for key, value in projected_d089["usage"].items()
        if key != "model_duration_ms"
    }
    assert {
        key: d090_body["run"]["usage"][key] for key in projected_d090_usage
    } == projected_d090_usage
    assert d090_body["qualification"]["qualification_hash"] == source[
        "d090_probe_seal"
    ]["qualification_hash"]
    assert d090_body["qualification"]["source_evidence_hash"] == source[
        "d090_probe_seal"
    ]["source_evidence_hash"]
    assert d090_body["qualification"]["passed_checks"] == projected_d089[
        "qualification_passed_checks"
    ]
    assert d090_body["qualification"]["total_checks"] == projected_d089[
        "qualification_total_checks"
    ]
    d090_terminal = d090_body["run"]["terminal_error"]
    for key in (
        "remaining_tokens",
        "max_output_tokens",
        "required_tokens",
        "deficit_tokens",
    ):
        assert d090_terminal[key] == projected_d089["terminal_budget"][key]
    assert d090_terminal["requested_input_tokens"] == projected_d089[
        "terminal_budget"
    ]["blocked_requested_input_tokens"]
    d090_trace = d090_body["public_trace_diagnostics"]
    d089_tools = projected_d089["tool_and_recovery"]
    assert d090_trace["events"] == projected_d089["trace"]["events"]
    assert d090_trace["checkpoints"] == projected_d089["trace"]["checkpoints"]
    assert d090_trace["tools"] == {
        **d089_tools["tool_calls"],
        **d089_tools["outcomes"],
    }
    assert d090_trace["loops"] == d089_tools["loops"]
    assert d090_trace["mutations"] == {
        "patches_prepared": d089_tools["patches_prepared"],
        "patches_applied": d089_tools["patches_applied"],
        "submission_accepted": projected_d089["submission_accepted"],
        "rejected_candidate_count": d089_tools["rejected_candidate_count"],
        "verified_retry_count": d089_tools["verified_retry_count"],
        "failed_source_failure_sequences": [],
    }
    d090_source = d090_body["source_contract"]
    assert d090_source["suite"] == {
        "path": source["d089_predecessors"]["suite"]["path"],
        "sha256": source["d089_predecessors"]["suite"]["sha256"],
    }
    assert d090_source["source_gate"] == {
        "path": source["d089_predecessors"]["source_gate"]["path"],
        "sha256": source["d089_predecessors"]["source_gate"]["sha256"],
    }

    public_path = ROOT / source["public_task"]["path"]
    public_task = load_public_task(public_path)
    assert public_task.task_id == source["public_task"]["task_id"]
    assert public_task.repository.base_commit == source["public_task"][
        "base_commit"
    ]
    assert sha256_json(public_task.model_dump(mode="json")) == source[
        "public_task"
    ]["public_spec_hash"]

    scope = body["audit_scope"]
    assert scope == {
        "public_task_read": True,
        "portable_public_reports_read": True,
        "durable_public_event_metadata_read": True,
        "manifest_and_qualification_metadata_read": True,
        "private_task_or_hidden_assertions_read_for_analysis": False,
        "reference_or_candidate_patch_body_read_for_analysis": False,
        "model_request_or_response_body_read_for_analysis": False,
        "tool_input_or_output_artifact_body_read_for_analysis": False,
        "credential_read_or_logged": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "added_model_cost_usd": 0.0,
    }

    report_text = REPORT_PATH.read_text(encoding="utf-8")
    forbidden_keys = {
        "api_key",
        "authorization",
        "private_spec_hash",
        "hidden_artifacts",
        "reference_patch",
        "patch_body",
        "request_body",
        "response_body",
        "response_id",
        "checks",
        "details",
        "verifier_results",
        "evidence_artifacts",
        "error_details",
        "input_artifact",
        "result_artifact",
        "candidate_content_hash",
    }

    def walk_keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {
                nested for child in value.values() for nested in walk_keys(child)
            }
        if isinstance(value, list):
            return {
                nested for child in value for nested in walk_keys(child)
            }
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(_load(REPORT_PATH)))
    for marker in (
        "OPENAI_API_KEY",
        "Bearer ",
        "diff --git",
        "@@ -",
        "*** Begin Patch",
        "*** End Patch",
    ):
        assert marker not in report_text
    assert re.search(
        r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{8,}", report_text
    ) is None


def test_d091_portable_arithmetic_and_claims_do_not_overreach() -> None:
    body = _body()
    d087 = body["runs"]["d087_anyio_repetition_2"]
    d089 = body["runs"]["d089_budget_only_probe"]

    for run in (d087, d089):
        usage = run["usage"]
        assert usage["input_tokens"] + usage["output_tokens"] == usage[
            "total_tokens"
        ]
        tools = run["tool_and_recovery"]
        assert sum(tools["tool_calls"].values()) == usage["tool_calls"]
        assert sum(tools["outcomes"].values()) == usage["tool_calls"]
        assert sum(
            value
            for key, value in tools["loops"].items()
            if key
            in {"fully_covered_read", "duplicate_search", "unclassified"}
        ) == tools["loops"]["observed"]
        assert tools["rejected_candidate_count"] == tools[
            "verified_retry_count"
        ]
        assert tools["failed_source_failure_sequences"] == []
        assert tools["visible_checks_passed"] == 0
        assert tools["get_diff_calls"] == tools["finish_task_calls"] == 0

        budget = run["terminal_budget"]
        assert budget["blocked_requested_input_tokens"] + budget[
            "max_output_tokens"
        ] == budget["required_tokens"]
        assert budget["required_tokens"] - budget["remaining_tokens"] == (
            budget["deficit_tokens"]
        )
        assert usage["total_tokens"] + budget["required_tokens"] == (
            budget["same_prefix_next_call_minimum"]
        )

    delta = body["cross_run_comparison"]["d089_minus_d087"]
    for key in (
        "input_tokens",
        "output_tokens",
        "reasoning_output_tokens",
        "total_tokens",
        "model_calls",
        "tool_calls",
        "wall_clock_ms",
        "model_duration_ms",
    ):
        assert delta[key] == d089["usage"][key] - d087["usage"][key]
    assert delta["context_characters_maximum"] == (
        d089["trace"]["context_characters_maximum"]
        - d087["trace"]["context_characters_maximum"]
    )
    assert delta["context_characters_final"] == (
        d089["trace"]["context_characters_final"]
        - d087["trace"]["context_characters_final"]
    )

    averages = body["cross_run_comparison"][
        "average_total_tokens_per_completed_model_call"
    ]
    expected_d087 = (
        Decimal(d087["usage"]["total_tokens"])
        / Decimal(d087["usage"]["model_calls"])
    ).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    expected_d089 = (
        Decimal(d089["usage"]["total_tokens"])
        / Decimal(d089["usage"]["model_calls"])
    ).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    assert Decimal(str(averages["d087"])) == expected_d087
    assert Decimal(str(averages["d089"])) == expected_d089

    counterfactuals = body["bounded_counterfactuals"]
    assert counterfactuals["d089_same_observed_prefix_at_2400000"][
        "tokens_remaining_before_blocked_request"
    ] == 2_400_000 - d089["usage"]["total_tokens"]
    assert counterfactuals["d089_same_observed_prefix_at_3000000"][
        "tokens_remaining_before_blocked_request"
    ] == 3_000_000 - d089["usage"]["total_tokens"]
    assert all(
        row["completion_guarantee"] is False
        for row in (
            counterfactuals["d087_exact_next_call"],
            counterfactuals["d089_exact_next_call"],
            counterfactuals["d089_same_observed_prefix_at_2400000"],
            counterfactuals["d089_same_observed_prefix_at_3000000"],
        )
    )

    classification = body["classification"]
    assert classification["trace_or_recovery_integrity_failure_observed"] is False
    assert classification["rejected_patch_rehydration_failure_observed"] is False
    assert classification["harness_defect_confirmed"] is False
    assert classification["harness_defect_ruled_out"] is False
    assert classification["process_nonconvergence_observed"] is True
    assert classification["budget_shortage_as_completion_root_cause_proven"] is False
    assert classification["more_budget_alone_as_completion_remedy_supported"] is False
    assert classification["cross_run_budget_effect_identified"] is False

    claims = body["claims_boundary"]
    assert claims["d087_immutable"] is True
    assert claims["d089_immutable_and_hard_consumed"] is True
    assert claims["provider_calls_made_by_audit"] == 0
    assert claims["evaluator_calls_made_by_audit"] == 0
    assert claims["added_model_cost_usd"] == 0
    for key in (
        "automatic_rerun_authorized",
        "new_budget_policy_authorized",
        "prompt_tool_context_change_authorized",
        "task_specific_tuning_authorized",
        "no_memory_baseline_established",
        "comparison_denominator_eligible",
        "memory_review_admission_or_index_unlocked",
        "core_campaign_unlocked",
    ):
        assert claims[key] is False


def test_d091_raw_public_event_metrics_recompute_when_present() -> None:
    state = _skip_without_raw()
    report_runs = _body()["runs"]
    cases = (
        (D087_RUN_ID, report_runs["d087_anyio_repetition_2"]),
        (D089_RUN_ID, report_runs["d089_budget_only_probe"]),
    )

    for run_id, projected in cases:
        events = state.list_events(run_id)
        checkpoints = state.list_checkpoints(run_id)
        manifest = state.get_manifest(run_id)
        assert [event.sequence for event in events] == list(
            range(1, len(events) + 1)
        )
        assert len(events) == projected["trace"]["events"]
        assert len(checkpoints) == projected["trace"]["checkpoints"]
        assert round(
            (events[-1].timestamp - events[0].timestamp).total_seconds() * 1000
        ) == projected["trace"]["event_elapsed_ms"]

        transitions = [
            f"{event.payload['from']}->{event.payload['to']}"
            for event in events
            if event.type.value == "PhaseChanged"
        ]
        assert transitions == projected["trace"]["phase_transitions"]
        assert all(checkpoint.reproduction_status == "unknown" for checkpoint in checkpoints)
        assert len(checkpoints) == projected["trace"][
            "checkpoint_reproduction_status_unknown"
        ]
        assert len(checkpoints[-1].completed_checks) == projected["trace"][
            "final_completed_checks"
        ]
        assert len(checkpoints[-1].pending_checks) == projected["trace"][
            "final_pending_checks"
        ]

        model_events = [
            event for event in events if event.type.value == "ModelCalled"
        ]
        usage = projected["usage"]
        assert len(model_events) == usage["model_calls"]
        assert sum(event.payload["input_tokens"] for event in model_events) == (
            usage["input_tokens"]
        )
        assert sum(event.payload["output_tokens"] for event in model_events) == (
            usage["output_tokens"]
        )
        assert sum(
            event.payload["reasoning_output_tokens"] for event in model_events
        ) == usage["reasoning_output_tokens"]
        assert sum(event.payload["duration_ms"] for event in model_events) == (
            usage["model_duration_ms"]
        )
        assert min(event.payload["input_tokens"] for event in model_events) == (
            projected["trace"]["observed_input_tokens_minimum"]
        )
        assert max(event.payload["input_tokens"] for event in model_events) == (
            projected["trace"]["observed_input_tokens_maximum"]
        )
        assert model_events[-1].payload["input_tokens"] == projected["trace"][
            "observed_input_tokens_final"
        ]
        assert all(
            event.payload["response_status"] == "completed"
            and event.payload["input_token_count_match"] is True
            and event.payload["total_token_count_match"] is True
            for event in model_events
        )

        context_events = [
            event for event in events if event.type.value == "ContextBuilt"
        ]
        context_chars = [
            event.payload["context_characters"] for event in context_events
        ]
        assert len(context_events) == projected["trace"]["context_builds"]
        assert min(context_chars) == projected["trace"][
            "context_characters_minimum"
        ]
        assert max(context_chars) == projected["trace"][
            "context_characters_maximum"
        ]
        assert context_chars[-1] == projected["trace"][
            "context_characters_final"
        ]
        assert max(
            event.payload["included_event_count"] for event in context_events
        ) == projected["trace"]["included_event_count_maximum"]
        assert context_events[-1].payload["included_event_count"] == (
            projected["trace"]["included_event_count_final"]
        )
        assert context_events[-1].payload["omitted_event_count"] == (
            projected["trace"]["omitted_event_count_final"]
        )
        assert sum(event.payload["provider_state_used"] for event in context_events) == (
            projected["trace"]["provider_state_used_count"]
        )
        assert sum(
            event.payload["truncated_tool_result_count"] > 0
            for event in context_events
        ) == projected["trace"]["truncated_tool_result_contexts"]

        phase_rows = _phase_summaries(events)
        for phase in ("REPRODUCE", "IMPLEMENT"):
            assert phase_rows[phase] == projected["phase_summary"][phase]

        tool_calls = [
            event for event in events if event.type.value == "ToolCalled"
        ]
        tool_projection = projected["tool_and_recovery"]
        assert Counter(event.payload["tool"] for event in tool_calls) == Counter(
            tool_projection["tool_calls"]
        )
        assert sum(event.type.value == "ToolSucceeded" for event in events) == (
            tool_projection["outcomes"]["succeeded"]
        )
        assert sum(event.type.value == "ToolFailed" for event in events) == (
            tool_projection["outcomes"]["failed"]
        )
        assert sum(event.type.value == "ToolReplayed" for event in events) == (
            tool_projection["outcomes"]["replayed"]
        )
        apply_failures = [
            event
            for event in events
            if event.type.value == "ToolFailed"
            and event.payload.get("tool") == "apply_patch"
        ]
        assert len(apply_failures) == tool_projection["apply_patch_failures"]
        assert Counter(event.payload["error_code"] for event in apply_failures) == (
            Counter(
                {
                    "POLICY_VIOLATION": tool_projection[
                        "apply_patch_policy_violations"
                    ],
                    "CONTRACT_ERROR": tool_projection[
                        "apply_patch_contract_errors"
                    ],
                }
            )
        )
        check_events = [
            event
            for event in events
            if event.type.value in {"ToolSucceeded", "ToolFailed"}
            and event.payload.get("tool") == "run_check"
        ]
        assert len(check_events) == tool_projection["visible_checks_executed"]
        assert sum(event.payload.get("passed") is True for event in check_events) == (
            tool_projection["visible_checks_passed"]
        )
        assert sum(
            event.type.value == "ToolCalled"
            and event.payload.get("tool") == "get_diff"
            for event in events
        ) == tool_projection["get_diff_calls"]
        assert sum(
            event.type.value == "ToolCalled"
            and event.payload.get("tool") == "finish_task"
            for event in events
        ) == tool_projection["finish_task_calls"]

        loop_events = [
            event for event in events if event.type.value == "LoopDetected"
        ]
        assert len(loop_events) == tool_projection["loops"]["observed"]
        reason_counts = Counter(event.payload.get("reason_code") for event in loop_events)
        assert reason_counts["fully_covered_read"] == tool_projection["loops"][
            "fully_covered_read"
        ]
        assert reason_counts["duplicate_search"] == tool_projection["loops"][
            "duplicate_search"
        ]
        assert reason_counts[None] == tool_projection["loops"]["unclassified"]
        assert max(
            event.payload.get("no_progress_streak", 0) for event in loop_events
        ) == (
            tool_projection["loops"]["maximum_no_progress_streak"]
        )

        patch_events = [
            event for event in events if event.type.value == "PatchApplied"
        ]
        assert len(patch_events) == tool_projection["patches_applied"]
        last_patch = patch_events[-1]
        assert last_patch.sequence == projected["post_last_applied_patch"][
            "last_patch_applied_sequence"
        ]
        assert _tail_after(events, last_patch.sequence) == {
            key: value
            for key, value in projected["post_last_applied_patch"].items()
            if key != "last_patch_applied_sequence"
        }
        last_check = check_events[-1]
        assert last_check.sequence == projected["post_last_executed_check"][
            "last_check_sequence"
        ]
        assert last_check.payload.get("passed") is projected[
            "post_last_executed_check"
        ]["last_check_passed"]
        assert _tail_after(events, last_check.sequence) == {
            key: value
            for key, value in projected["post_last_executed_check"].items()
            if key not in {"last_check_sequence", "last_check_passed"}
        }

        blocked = next(
            event
            for event in events
            if event.type.value == "ModelGenerationBlocked"
        )
        terminal_budget = projected["terminal_budget"]
        for payload_key, report_key in (
            ("remaining_tokens", "remaining_tokens"),
            ("requested_input_tokens", "blocked_requested_input_tokens"),
            ("max_output_tokens", "max_output_tokens"),
        ):
            assert blocked.payload[payload_key] == terminal_budget[report_key]
        assert blocked.payload["generation_started"] is False
        assert blocked.payload["reason_code"] == projected["terminal_reason"]

        qualification = load_trace_qualification(run_id, root=RUNTIME_ROOT)
        source_descriptor = _body()["source_binding"][
            "d088_campaign_seal"
            if run_id == D087_RUN_ID
            else "d090_probe_seal"
        ]
        assert qualification["qualification_hash"] == source_descriptor[
            "qualification_hash"
        ]
        assert qualification["source_evidence_hash"] == source_descriptor[
            "source_evidence_hash"
        ]
        retry_check = next(
            check
            for check in qualification["checks"]
            if check["check_id"] == "rejected_patch_retry_context"
        )
        assert retry_check["passed"] is True
        assert retry_check["details"]["rejected_candidate_count"] == (
            tool_projection["rejected_candidate_count"]
        )
        assert retry_check["details"]["verified_retry_count"] == (
            tool_projection["verified_retry_count"]
        )
        assert retry_check["details"]["failed_source_failure_sequences"] == []

        assert manifest.task_id == "anyio-interrupt-runner-cleanup"
        assert manifest.base_commit == (
            _body()["source_binding"]["public_task"]["base_commit"]
        )
        assert manifest.tool_schema_version == "v2"
        assert manifest.context_policy_version == "phase-evidence-v5"
        assert manifest.memory.condition.value == "no_memory"
        assert manifest.budget.max_model_calls is None
        assert manifest.budget.max_tool_calls is None
        assert manifest.budget.max_total_tokens == projected["configured_budget"][
            "max_total_tokens"
        ]
        assert manifest.budget.wall_clock_timeout_seconds == projected[
            "configured_budget"
        ]["wall_clock_timeout_seconds"]


def test_d091_is_analysis_only_and_preserves_historical_consumption() -> None:
    body = _body()
    assert eval_runner.CONDITION_NEUTRAL_COMPARISON_ACCRUED_CAP_EXPERIMENT_ID in (
        eval_runner.HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS
    )
    assert eval_runner.ANYIO_BUDGET_READINESS_PROBE_EXPERIMENT_ID in (
        eval_runner.CONSUMED_WORKFLOW_COMPLETION_PROBE_EXPERIMENT_IDS
    )
    assert eval_runner.ANYIO_BUDGET_READINESS_PROBE_EXPERIMENT_ID in (
        eval_runner.HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS
    )
    assert not (ROOT / "experiments/d091-anyio-public-trajectory-audit.yaml").exists()

    next_gate = body["next_gate"]
    assert next_gate["d091_analysis_complete"] is True
    assert next_gate["new_live_execution_authorized"] is False
    assert next_gate["budget_freeze_or_live_probe_after_this_artifact"] is False
    assert next_gate["allowed_evidence"] == (
        "public cross-task process evidence and offline replay only"
    )
