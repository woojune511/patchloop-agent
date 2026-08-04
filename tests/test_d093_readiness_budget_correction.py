from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from patchloop.util import sha256_bytes, sha256_json

ROOT = Path(__file__).resolve().parents[1]
D092_PATH = (
    ROOT
    / "reports/live-pilot/artifacts/d092-public-policy-replay-decision.json"
)
D088_PATH = (
    ROOT
    / "reports/live-pilot/"
    "dev-no-memory-condition-neutral-accrued-cap-20260804-r1.json"
)
D090_PATH = (
    ROOT
    / "reports/live-pilot/"
    "anyio-workflow-completion-budget-only-v2v5-20260804-r1.json"
)
CORRECTION_PATH = (
    ROOT
    / "reports/live-pilot/artifacts/d093-readiness-budget-outcome-correction.json"
)
BUILDER_PATH = ROOT / "scripts/build_d093_readiness_budget_correction.py"
D092_BUILDER_PATH = ROOT / "scripts/build_d092_policy_decision.py"
STATE_PATH = ROOT / ".patchloop/state.sqlite3"
D092_FILE_SHA256 = (
    "sha256:541b890e2b123a5431060e23dcf4544fce3f7b810cb8cb1a560fbcc245b3fe22"
)
CORRECTION_FILE_SHA256 = (
    "sha256:df8a35d7818dba3055ee4bb34519bd39abdc97d4d6add178d3d41b0521273941"
)
ORIGINAL_DECISION = (
    "retain-current-policy-and-count-qualified-budget-terminal-as-agent-failure"
)
CORRECTED_DECISION = (
    "retain-current-policy-and-treat-readiness-budget-terminal-as-inconclusive"
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _body() -> dict[str, Any]:
    return _load(CORRECTION_PATH)["semantic_body"]


def _stat(path: Path) -> tuple[int, int] | None:
    if not path.exists():
        return None
    value = path.stat()
    return value.st_size, value.st_mtime_ns


def test_d093_wrapper_is_strict_and_content_addressed() -> None:
    payload = _load(CORRECTION_PATH)

    assert sha256_bytes(CORRECTION_PATH.read_bytes()) == CORRECTION_FILE_SHA256
    assert set(payload) == {
        "schema_version",
        "correction_id",
        "semantic_body_hash",
        "semantic_body",
    }
    assert payload["schema_version"] == (
        "readiness-budget-outcome-correction-manifest-v1"
    )
    body_hash = sha256_json(payload["semantic_body"])
    assert payload["semantic_body_hash"] == body_hash
    assert payload["correction_id"] == (
        "rbocor_" + body_hash.removeprefix("sha256:")
    )
    assert set(payload["semantic_body"]) == {
        "schema_version",
        "milestone",
        "recorded_at",
        "source_binding",
        "cause",
        "preserved_policy_decision",
        "corrected_readiness_stage_contract",
        "correction_boundary",
        "claims_boundary",
        "next_gate",
    }


def test_d093_binds_byte_immutable_d092_source() -> None:
    source = _body()["source_binding"]["d092_policy_decision"]
    d092 = _load(D092_PATH)

    assert sha256_bytes(D092_PATH.read_bytes()) == D092_FILE_SHA256
    assert source == {
        "path": (
            "reports/live-pilot/artifacts/"
            "d092-public-policy-replay-decision.json"
        ),
        "bytes": 52_901,
        "file_sha256": D092_FILE_SHA256,
        "semantic_body_hash": d092["semantic_body_hash"],
        "decision_id": d092["decision_id"],
        "source_git_commit": "4f830cfa9de465e9640da82ecdd20aea412c914d",
        "original_selected_decision": ORIGINAL_DECISION,
        "original_runtime_policy_action": "retain-current-runtime-policy",
        "original_budget_terminal_outcome": "agent_failure",
        "original_outcome_binding_status": (
            "selected-but-denominator-binding-pending"
        ),
        "panel_projection_hash": d092["semantic_body"]["replay_projection"][
            "panel_projection_hash"
        ],
        "candidate_grid_hash": sha256_json(
            d092["semantic_body"]["candidate_grid"]
        ),
        "replay_projection_hash": sha256_json(
            d092["semantic_body"]["replay_projection"]
        ),
    }


def test_d093_binds_portable_seals_for_raw_outcome_and_resource_facts() -> None:
    sources = _body()["source_binding"]

    assert sha256_bytes(D088_PATH.read_bytes()) == (
        "sha256:2e24bfb0d98c2a7b2b0d8b5bf80c238ae048d782ce43c1cf08a2c10a6c6b5269"
    )
    assert sha256_bytes(D090_PATH.read_bytes()) == (
        "sha256:06006c95454618b7adcea305465fa63611d2043c70aaa3e1df2de9a3f5a192f1"
    )
    assert sources["d088_campaign_seal"] == {
        "path": (
            "reports/live-pilot/"
            "dev-no-memory-condition-neutral-accrued-cap-20260804-r1.json"
        ),
        "bytes": 32_251,
        "file_sha256": (
            "sha256:2e24bfb0d98c2a7b2b0d8b5bf80c238ae048d782ce43c1cf08a2c10a6c6b5269"
        ),
        "semantic_body_hash": (
            "sha256:b8401884eeffde2c26c9346108c578d8cbf2e24fe4ac84435219a6aa8911c3c3"
        ),
        "report_id": (
            "d088_b8401884eeffde2c26c9346108c578d8cbf2e24fe4ac84435219a6aa8911c3c3"
        ),
        "affected_run_projection_hash": (
            "sha256:bd982568bc136c780da191b7d8436016347860a7f6f69c1f55a00bb0a85287ac"
        ),
        "read_mode": "portable-semantic-field-validation",
    }
    assert sources["d090_anyio_probe_seal"] == {
        "path": (
            "reports/live-pilot/"
            "anyio-workflow-completion-budget-only-v2v5-20260804-r1.json"
        ),
        "bytes": 13_652,
        "file_sha256": (
            "sha256:06006c95454618b7adcea305465fa63611d2043c70aaa3e1df2de9a3f5a192f1"
        ),
        "semantic_body_hash": (
            "sha256:815881cebc761187636ae2992c5dd4ff95c0c471a0c79d7250373b513a3bc94e"
        ),
        "report_id": (
            "d090_815881cebc761187636ae2992c5dd4ff95c0c471a0c79d7250373b513a3bc94e"
        ),
        "affected_run_projection_hash": (
            "sha256:179d34455f327947f1c532a24be9b279d056775af16b08cfcfd31e1c480011a4"
        ),
        "read_mode": "portable-semantic-field-validation",
    }


def test_d093_preserves_stall_policy_replay_and_corrects_only_stage_meaning() -> None:
    body = _body()
    cause = body["cause"]
    preserved = body["preserved_policy_decision"]
    corrected = body["corrected_readiness_stage_contract"]

    assert cause["category"] == "stage-purpose-outcome-misclassification"
    assert cause["budget_is_target_experimental_factor"] is False
    assert cause["runtime_or_trace_defect"] is False
    assert cause["policy_replay_error"] is False
    assert cause["hidden_or_task_outcome_used"] is False

    assert preserved["selected"] == "retain-current-runtime-policy"
    assert preserved["admitted_candidate_count"] == 0
    assert preserved["repeated_rejection_result_preserved"] is True
    assert preserved["relative_context_result_preserved"] is True
    assert preserved["absolute_context_sensitivity_preserved"] is True
    assert preserved["d092_artifact_byte_immutable"] is True

    assert corrected["corrected_selected_decision"] == CORRECTED_DECISION
    assert corrected["evaluation_stage"] == "workflow-readiness"
    assert corrected["evaluation_stage_binding"] == (
        "explicit-content-addressed-policy"
    )
    assert corrected["experiment_purpose_inference_allowed"] is False
    assert corrected["raw_runtime_outcome_kind_preserved"] == "agent_failure"
    assert corrected["readiness_disposition"] == "readiness_inconclusive"
    assert corrected["readiness_reason"] == "budget_confounded"
    assert corrected["budget_role"] == (
        "finite-emergency-safety-ceiling-intended-to-be-non-binding"
    )
    assert corrected["performance_denominator_eligible"] is False
    assert corrected["automatic_rerun_authorized"] is False
    assert corrected["historical_exact_run_rerun_allowed"] is False
    assert corrected["new_successor_readiness_probe_allowed"] is True
    assert corrected["comparison_disposition"] == (
        "pending-explicit-resource-policy-freeze"
    )
    assert corrected["comparison_analysis_failure_selected"] is False


def test_d093_budget_confounded_runs_keep_raw_outcome_but_leave_denominator() -> None:
    rows = _body()["corrected_readiness_stage_contract"][
        "affected_public_runs"
    ]

    assert rows == [
        {
            "run_id": "run_4613c65b2a254349",
            "task_id": "anyio-interrupt-runner-cleanup",
            "raw_runtime_outcome_kind_preserved": "agent_failure",
            "readiness_disposition": "readiness_inconclusive",
            "readiness_reason": "budget_confounded",
            "historical_exact_run_rerun_allowed": False,
        },
        {
            "run_id": "run_e444de1bb20a4325",
            "task_id": "anyio-interrupt-runner-cleanup",
            "raw_runtime_outcome_kind_preserved": "agent_failure",
            "readiness_disposition": "readiness_inconclusive",
            "readiness_reason": "budget_confounded",
            "historical_exact_run_rerun_allowed": False,
        },
    ]


def test_d093_completion_gate_requires_evaluator_without_hidden_success() -> None:
    gate = _body()["corrected_readiness_stage_contract"][
        "readiness_completion_gate"
    ]

    assert gate["required_true"] == [
        "all_rows_started_and_terminal",
        "all_rows_trace_qualified",
        "all_rows_submission_accepted",
        "all_rows_evaluator_reached",
        "all_rows_official_evaluator",
        "persisted_qualification_matches_read_only_recomputation",
        "exact_input_telemetry_complete",
        "responses_completed",
        "truncation_disabled",
    ]
    assert gate["required_zero"] == [
        "infrastructure_errors",
        "qualification_errors",
        "diagnostic_errors",
        "budget_terminal_runs",
        "terminal_loop_failure_runs",
        "model_or_tool_call_budget_blocks",
    ]
    assert gate["task_success_required"] is False
    assert gate["hidden_acceptance_required"] is False
    assert gate["scrr_required"] is False


def test_d093_correction_and_authority_boundaries_are_fail_closed() -> None:
    boundary = _body()["correction_boundary"]
    claims = _body()["claims_boundary"]

    assert boundary["superseded_d092_fields"] == [
        "decision.selected analytical suffix",
        "decision.qualified_budget_terminal_outcome as readiness analysis",
        "decision.outcome_binding_status",
        "next_gate.budget_terminal_rule",
    ]
    assert all(
        boundary[key] is False
        for key in (
            "original_d092_artifact_modified",
            "original_d092_decision_string_modified",
            "original_run_result_modified",
            "original_journal_or_qualification_modified",
            "runtime_policy_modified",
            "candidate_grid_or_replay_modified",
            "historical_gate_replaced",
            "comparison_or_baseline_policy_selected",
        )
    )
    assert claims["readiness_stage_interpretation_corrected"] is True
    assert claims["workflow_readiness_established"] is False
    assert claims["budget_sufficiency_established"] is False
    assert claims["high_headroom_probe_source_frozen"] is False
    assert claims["high_headroom_probe_execution_authorized"] is False
    assert claims["provider_calls_made"] == 0
    assert claims["evaluator_calls_made"] == 0
    assert claims["added_model_cost_usd"] == 0.0
    assert claims["comparison_denominator_opened"] is False
    assert claims["no_memory_baseline_opened"] is False
    assert claims["memory_review_or_admission_or_index_opened"] is False
    assert claims["core_experiment_opened"] is False


def test_d093_next_gate_is_source_only_and_requires_fresh_approval() -> None:
    gate = _body()["next_gate"]

    assert gate["gate"] == "high-headroom-diverse-readiness-source-gate"
    assert gate["candidate_tasks"] == [
        "anyio-interrupt-runner-cleanup",
        "pyfakefs-makedirs-parent-traversal",
        "hf-hub-xet-endpoint-propagation",
    ]
    resources = gate["candidate_resource_derivation"]
    assert resources["source_run_ids"] == [
        "run_4613c65b2a254349",
        "run_e444de1bb20a4325",
    ]
    assert resources["observed_public_maximum_tokens"] == 1_956_109
    assert resources["token_multiplier_numerator"] == 3
    assert resources["token_multiplier_denominator"] == 2
    assert resources["token_unrounded_numerator"] == 5_868_327
    assert resources["token_unrounded_denominator"] == 2
    assert resources["token_rounding_quantum"] == 100_000
    assert resources["candidate_max_total_tokens"] == 3_000_000
    assert resources["observed_public_maximum_wall_clock_ms"] == 1_628_695
    assert resources["wall_multiplier_numerator"] == 2
    assert resources["wall_multiplier_denominator"] == 1
    assert resources["wall_unrounded_milliseconds"] == 3_257_390
    assert resources["wall_unit_conversion_milliseconds_per_second"] == 1_000
    assert resources["wall_rounding_quantum_seconds"] == 600
    assert resources["candidate_wall_clock_timeout_seconds"] == 3_600
    assert resources["max_model_calls"] is None
    assert resources["max_tool_calls"] is None
    assert gate["candidate_values_are_source_frozen"] is False
    assert gate["fresh_official_price_check_required"] is True
    assert gate["fresh_no_call_preflight_required"] is True
    assert gate["new_execution_hash_required"] is True
    assert gate["separate_user_cost_approval_required"] is True
    assert gate["automatic_successor_execution_authorized"] is False
    assert gate["provider_execution_authorized"] is False


def test_d093_builder_reproduces_artifact_and_rejects_source_tampering(
    tmp_path: Path,
) -> None:
    builder = _module(BUILDER_PATH, "d093_builder")
    payload = _load(CORRECTION_PATH)

    rebuilt = builder.build_correction(
        repo_root=ROOT,
        recorded_at=payload["semantic_body"]["recorded_at"],
    )
    assert rebuilt == payload

    copied = tmp_path / builder.D092_RELATIVE_PATH
    copied.parent.mkdir(parents=True)
    data = bytearray(D092_PATH.read_bytes())
    data[-2] = ord(" ")
    copied.write_bytes(data)
    with pytest.raises(builder.D093BuildError, match="source file hash drifted"):
        builder.build_correction(
            repo_root=tmp_path,
            recorded_at=payload["semantic_body"]["recorded_at"],
        )

    seal_root = tmp_path / "seal-tamper"
    for relative_path, source_path in (
        (builder.D092_RELATIVE_PATH, D092_PATH),
        (builder.D088_RELATIVE_PATH, D088_PATH),
        (builder.D090_RELATIVE_PATH, D090_PATH),
    ):
        copied = seal_root / relative_path
        copied.parent.mkdir(parents=True, exist_ok=True)
        copied.write_bytes(source_path.read_bytes())
    d088_copy = seal_root / builder.D088_RELATIVE_PATH
    d088_data = bytearray(d088_copy.read_bytes())
    d088_data[-2] = ord(" ")
    d088_copy.write_bytes(d088_data)
    with pytest.raises(builder.D093BuildError, match="D-088 source file hash drifted"):
        builder.build_correction(
            repo_root=seal_root,
            recorded_at=payload["semantic_body"]["recorded_at"],
        )


def test_d093_portable_payload_is_leak_safe_and_cwd_independent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    serialized = CORRECTION_PATH.read_text(encoding="utf-8").lower()
    for forbidden in (
        "diff --git",
        "@@ -",
        "private_spec_hash",
        "hidden_tests",
        "reference_patch",
        "submitted_patch",
        "patch_artifact",
        "request_body",
        "response_body",
        "artifact_path",
        "openai_api_key",
        "authorization:",
    ):
        assert forbidden not in serialized

    monkeypatch.chdir(tmp_path)
    assert _load(CORRECTION_PATH)["semantic_body"][
        "corrected_readiness_stage_contract"
    ]["readiness_disposition"] == "readiness_inconclusive"


def test_d093_source_reconciles_with_existing_read_only_d092_replay() -> None:
    if not STATE_PATH.is_file():
        pytest.skip("local immutable D-092 public event source is unavailable")
    d092_builder = _module(D092_BUILDER_PATH, "d092_builder_for_d093")
    d092 = _load(D092_PATH)
    before = {
        path.name: _stat(path)
        for path in (
            STATE_PATH,
            STATE_PATH.with_name(STATE_PATH.name + "-wal"),
            STATE_PATH.with_name(STATE_PATH.name + "-shm"),
        )
    }

    rebuilt = d092_builder.build_manifest(
        repo_root=ROOT,
        state_path=STATE_PATH,
        recorded_at=d092["semantic_body"]["recorded_at"],
    )

    after = {
        path.name: _stat(path)
        for path in (
            STATE_PATH,
            STATE_PATH.with_name(STATE_PATH.name + "-wal"),
            STATE_PATH.with_name(STATE_PATH.name + "-shm"),
        )
    }
    assert rebuilt == d092
    assert after == before


def test_d093_builder_has_no_runtime_or_provider_capability() -> None:
    source = BUILDER_PATH.read_text(encoding="utf-8")

    assert "sqlite3" not in source
    assert "StateStore" not in source
    assert "OPENAI_API_KEY" not in source
    assert "provider" not in " ".join(
        re.findall(r"(?:import|from)\s+([^\n]+)", source)
    ).lower()
