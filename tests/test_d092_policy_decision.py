from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from patchloop.util import sha256_bytes, sha256_json

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    ROOT
    / "reports/live-pilot/artifacts/d092-public-policy-replay-decision.json"
)
REPORT_FILE_SHA256 = (
    "sha256:541b890e2b123a5431060e23dcf4544fce3f7b810cb8cb1a560fbcc245b3fe22"
)
DECISION = (
    "retain-current-policy-and-count-qualified-budget-terminal-as-agent-failure"
)


def _load() -> dict[str, Any]:
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def _body() -> dict[str, Any]:
    return _load()["semantic_body"]


def _evaluations(section: str) -> list[dict[str, Any]]:
    return [
        row["evaluation"]
        for row in _body()["replay_projection"][section]
    ]


def test_d092_manifest_is_content_addressed_and_strict() -> None:
    payload = _load()

    assert sha256_bytes(REPORT_PATH.read_bytes()) == REPORT_FILE_SHA256
    assert set(payload) == {
        "schema_version",
        "decision_id",
        "semantic_body_hash",
        "semantic_body",
    }
    assert payload["schema_version"] == (
        "public-cross-task-policy-decision-manifest-v1"
    )
    assert payload["semantic_body_hash"] == sha256_json(payload["semantic_body"])
    assert payload["decision_id"] == (
        "d092_" + payload["semantic_body_hash"].removeprefix("sha256:")
    )

    body = payload["semantic_body"]
    assert set(body) == {
        "schema_version",
        "milestone",
        "recorded_at",
        "evidence_kind",
        "source_binding",
        "audit_scope",
        "panel_contract",
        "progress_contract",
        "candidate_grid",
        "replay_projection",
        "decision",
        "claims_boundary",
        "next_gate",
    }
    assert body["schema_version"] == "public-cross-task-policy-decision-v1"


def test_d092_source_files_are_bound_by_bytes_without_outcome_projection() -> None:
    sources = _body()["source_binding"]

    assert set(sources) == {
        "d082_four_run_readiness_seal",
        "d086_condition_neutral_pilot_seal",
        "d088_twelve_run_campaign_seal",
        "d090_anyio_probe_seal",
        "d091_anyio_public_trajectory_audit",
    }
    for source in sources.values():
        assert set(source) == {
            "path",
            "bytes",
            "file_sha256",
            "experiment_ids",
            "read_mode",
        }
        path = ROOT / source["path"]
        content = path.read_bytes()
        assert len(content) == source["bytes"]
        assert sha256_bytes(content) == source["file_sha256"]
        assert source["read_mode"] == "bytes-for-content-address-only"


def test_d092_public_panel_contract_is_exact_and_noncausal() -> None:
    panel = _body()["panel_contract"]

    assert set(panel) == {
        "run_count",
        "task_count",
        "task_ids",
        "public_event_count",
        "experiment_run_counts",
        "sealed_qualification_claim",
        "qualification_recomputed_in_d092",
        "common_model_tuple",
        "common_runtime_tuple",
        "varying_noncausal_fields",
        "excluded_primary_strata",
    }
    assert panel["run_count"] == 18
    assert panel["task_count"] == 8
    assert len(set(panel["task_ids"])) == 8
    assert panel["public_event_count"] == 4_079
    assert panel["experiment_run_counts"] == {
        "generic-baseline-readiness-v2v5-20260803-r3": 4,
        "dev-validation-condition-neutral-v2v5-pilot-20260803-r1": 1,
        "dev-no-memory-condition-neutral-accrued-cap-20260804-r1": 12,
        "anyio-workflow-completion-budget-only-v2v5-20260804-r1": 1,
    }
    assert panel["sealed_qualification_claim"] == "18/18 trace-qualified"
    assert panel["qualification_recomputed_in_d092"] is False
    assert panel["common_model_tuple"] == {
        "provider": "openai",
        "model_id": "gpt-5.4-mini-2026-03-17",
        "reasoning_effort": "medium",
        "reasoning_mode": "standard",
        "service_tier": "default",
        "max_output_tokens": 25_000,
        "transport_max_retries": 0,
    }
    varying = panel["varying_noncausal_fields"]
    assert varying["max_total_token_ceilings"] == [1_600_000, 2_000_000, 2_400_000]
    assert len(varying["harness_git_commits"]) == 4
    assert "not a causal performance comparison" in varying["interpretation"]


def test_d092_run_projection_contains_only_process_metadata() -> None:
    projection = _body()["replay_projection"]
    rows = projection["runs"]

    assert re.fullmatch(r"sha256:[0-9a-f]{64}", projection["panel_projection_hash"])
    assert len(rows) == 18
    assert len({row["run_id"] for row in rows}) == 18
    assert sum(row["event_count"] for row in rows) == 4_079
    assert {row["task_id"] for row in rows} == set(
        _body()["panel_contract"]["task_ids"]
    )
    expected_keys = {
        "run_id",
        "task_id",
        "experiment_id",
        "repetition",
        "schedule_order",
        "harness_git_commit",
        "max_total_tokens",
        "event_count",
        "model_calls",
        "model_tokens",
        "tool_calls",
        "apply_rejection_count",
        "context_observation_count",
        "maximum_context_characters",
        "progress_marker_counts",
        "model_generation_blocked_count",
        "terminal_event_type",
        "public_event_projection_hash",
    }
    for row in rows:
        assert set(row) == expected_keys
        assert re.fullmatch(
            r"sha256:[0-9a-f]{64}", row["public_event_projection_hash"]
        )
        assert row["event_count"] > 0
        assert row["context_observation_count"] == (
            row["model_calls"] + row["model_generation_blocked_count"]
        )
        assert set(row["progress_marker_counts"]) == {
            "forward_phase",
            "patch_applied",
            "visible_check_passed",
            "submission_attempted",
            "submission_accepted",
        }

    serialized = json.dumps(projection, sort_keys=True)
    for forbidden in (
        "private_spec_hash",
        "hidden_tests",
        "reference_patch",
        "candidate_content_hash",
        "patch_artifact",
        "error_message",
        "guidance",
        "normalized_call_hash",
        "correlation_id",
        "artifact_path",
        "request_body",
        "response_body",
    ):
        assert forbidden not in serialized


def test_d092_rejection_grid_has_false_stops_and_no_admission() -> None:
    rows = _evaluations("repeated_rejection")

    assert [row["policy_id"] for row in rows] == [
        f"repeated-rejection-n{threshold}" for threshold in range(3, 11)
    ]
    assert [row["triggered_run_count"] for row in rows] == [4, 3, 3, 2, 2, 2, 2, 2]
    assert [len(row["false_stop_run_ids"]) for row in rows] == [3, 2, 2, 1, 1, 1, 1, 1]
    assert all(row["affected_task_ids"] == ["anyio-interrupt-runner-cleanup"] for row in rows)
    assert all(row["zero_false_stops_passed"] is False for row in rows)
    assert all(row["minimum_task_coverage_passed"] is False for row in rows)
    assert all(row["leave_one_task_out_passed"] is False for row in rows)
    assert all(row["admitted"] is False for row in rows)


def test_d092_relative_context_grid_has_no_safe_generic_candidate() -> None:
    rows = _evaluations("relative_context_growth")

    assert [row["policy_id"] for row in rows] == [
        f"relative-context-x{multiplier}-calls{calls}"
        for multiplier in (2, 4, 8)
        for calls in (8, 16, 32)
    ]
    assert [row["triggered_run_count"] for row in rows] == [14, 7, 2, 14, 6, 2, 12, 5, 1]
    assert [len(row["false_stop_run_ids"]) for row in rows] == [14, 6, 1, 14, 5, 1, 12, 5, 1]
    assert all(row["minimum_task_coverage_passed"] is False for row in rows)
    assert all(row["leave_one_task_out_passed"] is False for row in rows)
    assert all(row["admission_scope"] is True for row in rows)
    assert all(row["admitted"] is False for row in rows)


def test_d092_absolute_context_is_post_hoc_sensitivity_only() -> None:
    rows = _evaluations("absolute_context_sensitivity")

    assert [row["policy_id"] for row in rows] == [
        "absolute-context-80000",
        "absolute-context-85000",
        "absolute-context-90000",
    ]
    assert [row["triggered_run_count"] for row in rows] == [4, 3, 1]
    assert [len(row["false_stop_run_ids"]) for row in rows] == [3, 2, 0]
    assert [row["observed_suffix_model_tokens"] for row in rows] == [
        1_202_919,
        863_211,
        824_161,
    ]
    assert rows[-1]["zero_false_stops_passed"] is True
    assert rows[-1]["affected_task_ids"] == ["anyio-interrupt-runner-cleanup"]
    assert all(row["admission_scope"] is False for row in rows)
    assert all(row["admitted"] is False for row in rows)


def test_d092_decision_and_authority_boundary_are_fail_closed() -> None:
    body = _body()
    decision = body["decision"]
    claims = body["claims_boundary"]
    scope = body["audit_scope"]

    assert decision == {
        "selected": DECISION,
        "admitted_candidate_count": 0,
        "runtime_policy_action": "retain-current-runtime-policy",
        "qualified_budget_terminal_outcome": "agent_failure",
        "outcome_binding_status": "selected-but-denominator-binding-pending",
        "repeated_rejection_result": decision["repeated_rejection_result"],
        "relative_context_result": decision["relative_context_result"],
        "absolute_context_result": decision["absolute_context_result"],
    }
    assert all(value is False for value in claims.values())
    assert scope["provider_calls_made"] == 0
    assert scope["evaluator_calls_made"] == 0
    assert scope["added_model_cost_usd"] == 0.0
    assert scope["result_json_read"] is False
    assert scope["qualification_detail_read"] is False
    assert scope["private_task_or_hidden_assertion_read"] is False
    assert body["next_gate"]["gate"] == (
        "condition-neutral-denominator-admission-binding"
    )
    assert body["next_gate"]["provider_execution_authorized_by_next_offline_gate"] is False


def test_d092_portable_verification_is_cwd_independent(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    payload = _load()

    assert payload["semantic_body"]["decision"]["selected"] == DECISION
    assert sha256_bytes(REPORT_PATH.read_bytes()) == REPORT_FILE_SHA256
