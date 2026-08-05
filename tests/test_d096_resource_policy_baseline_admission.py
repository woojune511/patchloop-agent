from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

from patchloop.evals import runner as eval_runner
from patchloop.evals.qualification import _private_leak_tokens
from patchloop.task_loader import load_public_task, load_task_package
from patchloop.util import sha256_bytes, sha256_json

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts/build_d096_resource_policy_baseline_admission.py"
DECISION_PATH = (
    ROOT
    / "reports/live-pilot/artifacts/"
    "d096-condition-neutral-resource-policy-baseline-admission.json"
)
DECISION_FILE_SHA256 = (
    "sha256:5c032cff1045a39d1d8d9757205a920b1cd1cfd948c7c4e3e5b526ae6744661d"
)
DECISION_BODY_SHA256 = (
    "sha256:2e9360d92db5224d181fe8f18254da3850f324b33b24f3833633589085e3b75d"
)
TASK_PATHS = (
    "tasks/dev-train/loguru-invalid-format-feedback/public.yaml",
    "tasks/dev-train/anyio-interrupt-runner-cleanup/public.yaml",
    "tasks/dev-train/tox-cross-section-empty-substitution/public.yaml",
    "tasks/dev-train/hf-hub-xet-endpoint-propagation/public.yaml",
    "tasks/dev-train/pdm-ignore-active-venv-resolution/public.yaml",
    "tasks/dev-train/pyfakefs-makedirs-parent-traversal/public.yaml",
)
EXPECTED_PUBLIC_CAS = {
    "loguru-invalid-format-feedback": (
        2_392,
        "sha256:efec17dc692c0935553e9e3c67ad5463d977254ea52a536c1dcf4a4c43831f10",
        "sha256:4839d8e5e1e57efa2a33a458ab0fe839d5ef4200bbe53b0f56683d8b8b98e7ea",
    ),
    "anyio-interrupt-runner-cleanup": (
        1_864,
        "sha256:ea977422306f9ce7203b4fc92aac83a73bc41554813d9ce1d794546767e76ddd",
        "sha256:b6d5b8d42a003795ed38256fa9a0e07c94578a6e0996179588a15d42604b86bf",
    ),
    "tox-cross-section-empty-substitution": (
        1_903,
        "sha256:cf100f771e799824b2928f28faec4be76f011aa84667b1573b6fa373860b0c82",
        "sha256:e371eddfbc9e8c73f7b47def95480496d7f88ddccb0348c00a12a9b78c496521",
    ),
    "hf-hub-xet-endpoint-propagation": (
        1_825,
        "sha256:3500452712d3977761f24da95170f073f86ec2a0589b69522321f91f5f473c4f",
        "sha256:8f7b0ea5f92ec9d843b8053f0739b42570b7407d76fe6f7a7ea6fd08c481a075",
    ),
    "pdm-ignore-active-venv-resolution": (
        1_986,
        "sha256:3d819ce8136e11d0572954f1afcc1918134aeef2e84d8fa365970c45ff671c24",
        "sha256:6bbb24f06a3dd43956abaee9ca72ecf69f2cfc4e68b2cdc10d877209afe39d27",
    ),
    "pyfakefs-makedirs-parent-traversal": (
        1_852,
        "sha256:5be7e6f6d2ad9722ee90c5a829aa043bf94c70ac317d5ce45254e4f3f9458eb0",
        "sha256:4d5de049d133ee29adf726733b7ace99b9d55518cc0433c72d2aa7b1576664d8",
    ),
}


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
    return _load(DECISION_PATH)["semantic_body"]


def _copy_builder_inputs(builder: ModuleType, destination_root: Path) -> None:
    descriptors = [
        *builder.SOURCE_FILES.values(),
        *builder.PUBLIC_TASK_FILES.values(),
    ]
    for descriptor in descriptors:
        source = ROOT / descriptor["path"]
        destination = destination_root / descriptor["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def test_d096_decision_is_content_addressed_and_strict() -> None:
    payload = _load(DECISION_PATH)

    assert len(DECISION_PATH.read_bytes()) == 19_031
    assert sha256_bytes(DECISION_PATH.read_bytes()) == DECISION_FILE_SHA256
    assert set(payload) == {
        "schema_version",
        "decision_id",
        "semantic_body_hash",
        "semantic_body",
    }
    assert payload["schema_version"] == (
        "condition-neutral-resource-policy-baseline-admission-d096-evidence-v1"
    )
    assert payload["semantic_body_hash"] == DECISION_BODY_SHA256
    assert sha256_json(payload["semantic_body"]) == DECISION_BODY_SHA256
    assert payload["decision_id"] == (
        f"d096_{DECISION_BODY_SHA256.removeprefix('sha256:')}"
    )
    assert set(payload["semantic_body"]) == {
        "milestone",
        "evidence_kind",
        "recorded_at",
        "source_bindings",
        "decision",
        "evidence_basis",
        "selected_resource_policy",
        "prospective_supersession_boundary",
        "no_memory_baseline_admission",
        "cost_authorization_boundary",
        "authorization_boundary",
        "claims_boundary",
        "next_gate",
    }


def test_d096_builder_exactly_reproduces_the_checked_in_decision() -> None:
    builder = _module(BUILDER_PATH, "d096_builder_reproducible")
    payload = _load(DECISION_PATH)

    assert builder.build_decision(
        repo_root=ROOT,
        recorded_at=payload["semantic_body"]["recorded_at"],
    ) == payload


def test_d096_cli_rebuild_is_byte_for_byte_reproducible(tmp_path: Path) -> None:
    rebuilt = tmp_path / "d096-rebuilt.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(BUILDER_PATH),
            "--repo-root",
            str(ROOT),
            "--output",
            str(rebuilt),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert rebuilt.read_bytes() == DECISION_PATH.read_bytes()


def test_d096_freezes_the_exact_condition_neutral_high_headroom_policy() -> None:
    body = _body()
    decision = body["decision"]
    evidence = body["evidence_basis"]
    policy = body["selected_resource_policy"]

    assert decision == {
        "schema_version": "condition-neutral-resource-baseline-decision-v1",
        "selected": (
            "freeze-high-headroom-policy-and-admit-new-no-memory-source-authoring"
        ),
        "workflow_readiness_prerequisite_satisfied": True,
        "policy_selection_uses_public_process_evidence_only": True,
        "task_success_or_hidden_outcome_used_for_selection": False,
        "budget_is_target_experimental_factor": False,
        "automatic_live_execution_authorized": False,
    }
    assert evidence["d093_public_candidate"] == {
        "observed_public_maximum_tokens": 1_956_109,
        "token_headroom_multiplier": "3/2",
        "candidate_max_total_tokens": 3_000_000,
        "observed_public_maximum_wall_clock_ms": 1_628_695,
        "wall_headroom_multiplier": "2/1",
        "candidate_wall_clock_timeout_seconds": 3_600,
    }
    assert evidence["d095_exact_candidate_observation"] == {
        "expected_runs": 3,
        "terminal_runs": 3,
        "qualified_runs": 3,
        "accepted_submission_runs": 3,
        "official_evaluator_runs": 3,
        "budget_terminal_runs": 0,
        "terminal_loop_failure_runs": 0,
        "model_or_tool_call_budget_block_runs": 0,
        "infrastructure_errors": 0,
        "qualification_errors": 0,
        "diagnostic_errors": 0,
        "readiness_gate_passed": True,
    }
    assert policy["profile_id"] == "gpt54mini-v2v5-condition-neutral-3000k-v1"
    assert policy["budget"] == {
        "max_model_calls": None,
        "max_tool_calls": None,
        "max_total_tokens": 3_000_000,
        "wall_clock_timeout_seconds": 3_600,
    }
    assert policy["max_output_tokens"] == 25_000
    assert policy["memory_max_context_tokens"] == 2_000
    assert policy["same_budget_for_all_memory_conditions"] is True
    assert policy["memory_conditions"] == [
        "no_memory",
        "raw_trace",
        "structured",
        "selective_structured",
    ]
    assert policy["completion_guaranteed"] is False


def test_d096_directly_binds_and_derives_the_d094_pricing_evidence() -> None:
    body = _body()
    bindings = {row["role"]: row for row in body["source_bindings"]}
    cost = body["cost_authorization_boundary"]

    assert bindings["d094-readiness-source-gate"] == {
        "role": "d094-readiness-source-gate",
        "path": (
            "reports/live-pilot/artifacts/"
            "d094-high-headroom-readiness-source-gate.json"
        ),
        "bytes": 13_284,
        "sha256": (
            "sha256:6887936ec141496e35e3a9d3bd6c34cf04cf02d1849bf80208677151a692c6ed"
        ),
        "semantic_body_hash": (
            "sha256:ab7be9ad2448d1016b88d451e271330844fc11d8fd4b890f08142618446ff929"
        ),
    }
    assert cost["pricing_evidence_source_role"] == "d094-readiness-source-gate"
    assert cost["pricing_verified_at"] == "2026-08-04T14:47:00Z"
    assert cost["fixed_standard_rates_per_million_usd"] == {
        "input": 0.75,
        "cached_input": 0.075,
        "output": 4.5,
    }


def test_d096_is_prospective_and_does_not_reinterpret_historical_runs() -> None:
    boundary = _body()["prospective_supersession_boundary"]

    assert boundary == {
        "schema_version": "condition-neutral-policy-supersession-v1",
        "d083_profile_id": "gpt54mini-v2v5-condition-neutral-1600k-v1",
        "d083_d084_historical_contracts_modified": False,
        "d083_profile_valid_for_historical_runs": True,
        "d083_profile_selected_for_new_runs": False,
        "d096_profile_selected_for_new_runs": True,
        "new_runtime_contract_schema": (
            "condition-neutral-comparison-runtime-contract-v2"
        ),
        "new_runtime_evidence_schema": (
            "condition-neutral-comparison-runtime-evidence-v2"
        ),
        "new_runtime_binding_implemented": False,
        "d087_retroactively_admitted": False,
        "d095_retroactively_admitted": False,
        "historical_run_result_or_qualification_modified": False,
    }
    historical_template = yaml.safe_load(
        (ROOT / "experiments/dev-no-memory-v5.template.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert historical_template["budget"]["max_total_tokens"] == 1_600_000
    assert eval_runner.CONDITION_NEUTRAL_COMPARISON_BUDGET_POLICY["profile_id"] == (
        "gpt54mini-v2v5-condition-neutral-1600k-v1"
    )


def test_d096_admits_exactly_twelve_new_no_memory_rows() -> None:
    admission = _body()["no_memory_baseline_admission"]
    schedule = admission["schedule_identity"]

    assert admission["admission_id"] == "memory-development-no-memory-12-row-v1"
    assert [row["public_path"] for row in admission["task_descriptors"]] == list(
        TASK_PATHS
    )
    assert [row["base_order"] for row in admission["task_descriptors"]] == list(
        range(1, 7)
    )
    assert all(
        row["dataset_role"] == "memory-development"
        and row["admission_state"] == "admitted"
        for row in admission["task_descriptors"]
    )
    for row in admission["task_descriptors"]:
        public_path = ROOT / row["public_path"]
        expected_bytes, expected_file_hash, expected_spec_hash = EXPECTED_PUBLIC_CAS[
            row["task_id"]
        ]
        public_task = load_public_task(public_path)
        assert row["task_version"] == 1
        assert row["public_bytes"] == expected_bytes == len(public_path.read_bytes())
        assert row["public_file_sha256"] == expected_file_hash == sha256_bytes(
            public_path.read_bytes()
        )
        assert row["public_spec_hash"] == expected_spec_hash == sha256_json(
            public_task.model_dump(mode="json")
        )
    schedule_without_hash = {
        key: value for key, value in schedule.items() if key != "content_hash"
    }
    assert schedule_without_hash == {
        "tasks": list(TASK_PATHS),
        "condition": "no_memory",
        "repetitions": 2,
        "seed": 20260723,
        "expected_rows": 12,
    }
    assert schedule["content_hash"] == sha256_json(schedule_without_hash)
    assert admission["future_no_memory_source_authoring_unlocked"] is True
    assert admission["successor_3000k_suite_required"] is True
    assert admission["live_collection_authorized"] is False
    assert admission["baseline_result_established"] is False


def test_d096_baseline_outcome_and_memory_candidate_rules_are_fail_closed() -> None:
    admission = _body()["no_memory_baseline_admission"]
    allowed = admission["allowed_terminal_row_classes"]
    partition = admission["terminal_branch_partition"]
    requirements = admission["campaign_completion_requirements"]
    memory_rule = admission["memory_candidate_rule"]

    assert [row["class"] for row in allowed] == [
        "official-evaluator-completed",
        "trace-qualified-frozen-policy-budget-terminal",
    ]
    assert all(row["denominator_included"] is True for row in allowed)
    assert all(row["automatic_rerun_allowed"] is False for row in allowed)
    assert allowed[1]["outcome"] == "agent_failure"
    assert allowed[1]["memory_candidate_eligible"] is False
    assert allowed[0]["result_predicate"] == {
        "attempt_status": "terminal",
        "agent_submission_status": "completed",
        "evaluation_status": "completed",
        "official": True,
        "outcome_kind_one_of": ["resolved", "task_failure"],
        "terminal_error": None,
    }
    assert allowed[0]["trace_predicate"]["submission_accepted_event_count"] == 1
    assert allowed[0]["trace_predicate"]["model_generation_blocked_event_count"] == 0
    assert allowed[0]["evaluation_receipt_predicate"] == {
        "schema_version": "evaluation-receipt-v1",
        "present": True,
        "content_hash_verified": True,
        "run_patch_diff_and_verifier_hashes_bound": True,
    }
    budget_result = allowed[1]["result_predicate"]
    budget_trace = allowed[1]["trace_predicate"]
    assert budget_result["agent_submission_status"] == "failed"
    assert budget_result["evaluation_status"] == "not_run"
    assert budget_result["outcome_kind"] == "agent_failure"
    assert budget_result["terminal_error_code"] == (
        "MODEL_GENERATION_BUDGET_EXCEEDED"
    )
    assert budget_trace["model_generation_blocked_event_count"] == 1
    assert budget_trace["event_actor"] == "budget-guard"
    assert budget_trace["generation_started"] is False
    assert budget_trace["request_artifact_and_body_cas_verified"] is True
    assert budget_trace["provider_calls_after_block"] == 0
    assert budget_trace["submission_accepted_event_count"] == 0
    assert budget_trace["evaluation_receipt_present"] is False
    assert budget_trace["allowed_bindings"] == [
        {
            "dimension": "total_tokens",
            "event_schema": "model-generation-block-v1",
            "reason_code": "exact_request_budget_exceeded",
        },
        {
            "dimension": "wall_clock",
            "event_schema": "model-generation-block-v3",
            "reason_code": "wall_clock_budget_exhausted",
        },
    ]
    assert partition == {
        "schema_version": "no-memory-terminal-branch-partition-v1",
        "branches": [
            "official-evaluator-completed",
            "trace-qualified-frozen-policy-budget-terminal",
        ],
        "mutually_exclusive": True,
        "exhaustive": True,
        "intersection_rows": 0,
        "unclassified_rows": 0,
        "sum_of_branch_counts_required": 12,
    }
    assert requirements["expected_rows"] == 12
    assert requirements["terminal_rows"] == 12
    assert requirements["trace_qualified_rows"] == 12
    assert requirements["cost_settled_rows"] == 12
    for key in (
        "not_started_rows",
        "infrastructure_errors",
        "qualification_errors",
        "diagnostic_errors",
        "duplicate_or_replacement_rows",
        "unknown_terminal_rows",
        "model_or_tool_call_budget_blocks",
    ):
        assert requirements[key] == 0
    assert requirements["campaign_cost_censoring_allowed"] is False
    assert requirements["task_success_required"] is False
    assert requirements["issued_model_calls_equal_completed_responses"] is True
    assert requirements["blocked_generation_is_pre_provider_call"] is True
    assert memory_rule["official_evaluator_task_failure_required"] is True
    assert memory_rule["budget_or_infrastructure_failure_eligible"] is False
    assert memory_rule["automatic_rule_admission"] is False


def test_d096_cost_boundary_exposes_the_project_cap_conflict() -> None:
    body = _body()
    cost = body["cost_authorization_boundary"]
    policy = body["selected_resource_policy"]
    derived_per_run_reserve = (
        Decimal(policy["budget"]["max_total_tokens"])
        + Decimal(policy["max_output_tokens"])
    ) * Decimal(str(cost["fixed_standard_rates_per_million_usd"]["output"])) / Decimal(
        1_000_000
    )

    assert Decimal(str(cost["per_run_worst_rate_reserve_usd"])) == Decimal(
        "13.6125"
    )
    assert derived_per_run_reserve == Decimal(
        str(cost["per_run_worst_rate_reserve_usd"])
    )
    assert Decimal(str(cost["twelve_run_worst_rate_reserve_usd"])) == Decimal(
        "163.35"
    )
    assert Decimal(str(cost["eighteen_run_worst_rate_reserve_usd"])) == Decimal(
        "245.025"
    )
    assert Decimal(str(cost["ninety_six_run_worst_rate_reserve_usd"])) == Decimal(
        "1306.8"
    )
    assert cost["existing_project_cap_usd"] == 150.0
    assert cost["twelve_run_cap_deficit_usd"] == 13.35
    assert cost["ninety_six_run_cap_deficit_usd"] == 1156.8
    assert cost["minimum_integer_cap_for_uncensored_twelve_run_worst_case_usd"] == (
        float(
            Decimal(str(cost["twelve_run_worst_rate_reserve_usd"])).to_integral_value(
                rounding=ROUND_CEILING
            )
        )
    )
    assert cost["blocker_code"] == "NO_MEMORY_AUTHORIZATION_CAP_PENDING"
    assert cost["campaign_cost_policy_selected"] is False
    assert cost["project_cap_changed"] is False
    assert cost["actual_invoice_or_free_tier_treatment_claimed"] is False


def test_d096_opens_source_authoring_but_keeps_live_memory_and_core_closed() -> None:
    body = _body()
    claims = body["claims_boundary"]
    authorization = body["authorization_boundary"]
    next_gate = body["next_gate"]

    assert claims["workflow_readiness_prerequisite_satisfied"] is True
    assert claims["comparison_resource_policy_frozen"] is True
    assert claims["baseline_admission_contract_frozen"] is True
    assert claims["future_no_memory_source_authoring_unlocked"] is True
    for key in (
        "live_execution_authorized",
        "no_memory_baseline_result_established",
        "development_baseline_denominator_complete",
        "core_comparison_denominator_eligible",
        "memory_review_authorized",
        "memory_admission_unlocked",
        "memory_index_frozen",
        "core_campaign_unlocked",
        "analysis_ready",
        "task_success_or_hidden_outcome_used_for_policy_selection",
        "prompt_tool_context_or_task_tuning_authorized",
        "historical_artifacts_modified",
    ):
        assert claims[key] is False
    assert claims["provider_calls_made"] == 0
    assert claims["evaluator_calls_made"] == 0
    assert claims["added_model_cost_usd"] == 0.0
    assert authorization["offline_decision_only"] is True
    assert authorization["new_suite_created"] is False
    assert authorization["runtime_binding_complete"] is False
    assert authorization["execution_hash_created"] is False
    assert authorization["provider_execution_authorized"] is False
    assert next_gate["provider_execution_authorized"] is False
    assert next_gate["new_experiment_id_required"] is True
    assert next_gate["separate_user_cost_approval_required"] is True


def test_d096_portable_decision_is_leak_safe() -> None:
    text = DECISION_PATH.read_text(encoding="utf-8").lower()
    for forbidden in (
        '"private_spec_hash"',
        '"reference_patch"',
        '"verifier_results"',
        '"submitted_patch"',
        '"request_body"',
        '"response_body"',
        "diff --git",
        "openai_api_key",
        "authorization: bearer",
    ):
        assert forbidden not in text

    for task_path in TASK_PATHS:
        package = load_task_package(ROOT / Path(task_path).parent)
        leaked = [
            token
            for token in _private_leak_tokens(package, api_key=None)
            if token.lower() in text
        ]
        assert leaked == []


@pytest.mark.parametrize("role", tuple(sorted({
    "d095-readiness-seal",
    "d093-readiness-correction",
    "d094-readiness-source-gate",
    "d083-historical-budget-freeze",
    "d084-historical-runtime-gate",
    "dataset-manifest",
    "historical-baseline-template",
})))
def test_d096_builder_fails_closed_on_each_source_byte_drift(
    role: str,
    tmp_path: Path,
) -> None:
    builder = _module(BUILDER_PATH, f"d096_builder_tamper_{role}")
    _copy_builder_inputs(builder, tmp_path)
    target = tmp_path / builder.SOURCE_FILES[role]["path"]
    target.write_bytes(target.read_bytes() + b"\n")

    with pytest.raises(builder.D096BuildError, match=f"{role} .* drifted"):
        builder.build_decision(repo_root=tmp_path)


@pytest.mark.parametrize("task_id", tuple(sorted(EXPECTED_PUBLIC_CAS)))
def test_d096_builder_fails_closed_on_each_public_task_byte_drift(
    task_id: str,
    tmp_path: Path,
) -> None:
    builder = _module(BUILDER_PATH, f"d096_builder_public_tamper_{task_id}")
    _copy_builder_inputs(builder, tmp_path)
    target = tmp_path / builder.PUBLIC_TASK_FILES[task_id]["path"]
    target.write_bytes(target.read_bytes() + b"\n")

    with pytest.raises(
        builder.D096BuildError,
        match=f"public task {task_id} .* drifted",
    ):
        builder.build_decision(repo_root=tmp_path)


@pytest.mark.parametrize(
    ("kind", "identity"),
    (
        ("source", "d094-readiness-source-gate"),
        ("public", "anyio-interrupt-runner-cleanup"),
    ),
)
def test_d096_builder_rejects_same_length_source_hash_drift(
    kind: str,
    identity: str,
    tmp_path: Path,
) -> None:
    builder = _module(BUILDER_PATH, f"d096_builder_same_length_{kind}")
    _copy_builder_inputs(builder, tmp_path)
    descriptor = (
        builder.SOURCE_FILES[identity]
        if kind == "source"
        else builder.PUBLIC_TASK_FILES[identity]
    )
    target = tmp_path / descriptor["path"]
    original = target.read_bytes()
    replacement = b"[" if original[:1] != b"[" else b"{"
    target.write_bytes(replacement + original[1:])

    assert len(target.read_bytes()) == len(original)
    with pytest.raises(builder.D096BuildError, match="hash drifted"):
        builder.build_decision(repo_root=tmp_path)
