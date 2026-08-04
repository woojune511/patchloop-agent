from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from patchloop.util import sha256_bytes, sha256_json

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts/build_d094_high_headroom_readiness_source_gate.py"
ARTIFACT_PATH = ROOT / "reports/live-pilot/artifacts/d094-high-headroom-readiness-source-gate.json"
ARTIFACT_FILE_SHA256 = "sha256:6887936ec141496e35e3a9d3bd6c34cf04cf02d1849bf80208677151a692c6ed"


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
    return _load(ARTIFACT_PATH)["semantic_body"]


def _copy_bound_sources(builder: ModuleType, destination: Path) -> None:
    relative_paths = [
        builder.D093_RELATIVE_PATH,
        builder.D084_RELATIVE_PATH,
        builder.SUITE_RELATIVE_PATH,
        builder.DATASET_RELATIVE_PATH,
    ]
    relative_paths.extend(
        descriptor[key]
        for descriptor in builder.TASK_DESCRIPTORS
        for key in ("public_path", "environment_path")
    )
    for relative_path in relative_paths:
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative_path, target)


def test_d094_wrapper_is_strict_content_addressed_and_reproducible() -> None:
    payload = _load(ARTIFACT_PATH)
    builder = _module(BUILDER_PATH, "d094_builder_reproducible")

    assert sha256_bytes(ARTIFACT_PATH.read_bytes()) == ARTIFACT_FILE_SHA256
    assert set(payload) == {
        "schema_version",
        "gate_id",
        "semantic_body_hash",
        "semantic_body",
    }
    assert payload["schema_version"] == ("high-headroom-readiness-source-gate-manifest-v1")
    body_hash = sha256_json(payload["semantic_body"])
    assert payload["semantic_body_hash"] == body_hash
    assert payload["gate_id"] == "d094_" + body_hash.removeprefix("sha256:")
    assert (
        builder.build_source_gate(
            repo_root=ROOT,
            recorded_at=payload["semantic_body"]["recorded_at"],
        )
        == payload
    )


def test_d094_binds_predecessors_suite_dataset_and_public_environments() -> None:
    body = _body()
    sources = body["source_binding"]

    assert sources["d093_readiness_budget_correction"] == {
        "path": ("reports/live-pilot/artifacts/d093-readiness-budget-outcome-correction.json"),
        "bytes": 9_611,
        "file_sha256": ("sha256:df8a35d7818dba3055ee4bb34519bd39abdc97d4d6add178d3d41b0521273941"),
        "semantic_body_hash": (
            "sha256:3a5790e57252132387b803681339e00032c62f7026a81d9acbd9f4598fc64ccd"
        ),
        "correction_id": (
            "rbocor_3a5790e57252132387b803681339e00032c62f7026a81d9acbd9f4598fc64ccd"
        ),
        "source_git_commit": "147263328d678601be86b4cf334f135d840dc98f",
        "modified": False,
    }
    assert sources["d084_runtime_gate"]["file_sha256"] == (
        "sha256:e7fb7b7e7e9dad3e6b31fb781f09151b940bf226bdd5876e5e75e472ff24b701"
    )
    assert sources["experiment_suite"] == {
        "path": "experiments/generic-high-headroom-readiness-v2v5-20260804-r1.yaml",
        "bytes": 1_666,
        "file_sha256": ("sha256:a7d8382a7e46167bf3c439bcb93ed93a28797d83fb276c22180c74a236a39f67"),
        "experiment_id": "generic-high-headroom-readiness-v2v5-20260804-r1",
    }
    dataset = sources["frozen_dataset"]
    assert dataset == {
        "path": "data/dataset-manifest.yaml",
        "bytes": 47_368,
        "file_sha256": ("sha256:e8cf14ca9dabebcc03c3522e400dfcb79606541e9b11e59f49510ea5c40bebed"),
        "canonical_manifest_hash": (
            "sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786"
        ),
        "dataset_id": "patchloop-benchmark-v1",
        "status": "frozen",
        "manifest_body_embedded": False,
    }

    descriptors = body["panel_source"]["task_descriptors"]
    assert [descriptor["task_id"] for descriptor in descriptors] == [
        "anyio-interrupt-runner-cleanup",
        "pyfakefs-makedirs-parent-traversal",
        "hf-hub-xet-endpoint-propagation",
    ]
    for descriptor in descriptors:
        assert (
            sha256_bytes((ROOT / descriptor["public_path"]).read_bytes())
            == (descriptor["public_file_sha256"])
        )
        assert (
            sha256_bytes((ROOT / descriptor["environment_path"]).read_bytes())
            == descriptor["environment_file_sha256"]
        )
        assert descriptor["evaluator_image"].endswith("@" + descriptor["image_digest"])
        assert descriptor["dataset_role"] == "memory-development"
        assert descriptor["admission_state"] == "admitted"


def test_d094_exact_tuple_reserve_and_readiness_meaning_are_narrow() -> None:
    body = _body()
    source = body["panel_source"]
    pricing = body["pricing"]
    readiness = body["readiness_predicate"]
    runtime = body["runtime_binding"]

    assert source["memory_conditions"] == ["no_memory"]
    assert source["repetitions"] == 1
    assert source["model"] == {
        "provider": "openai",
        "model_id": "gpt-5.4-mini-2026-03-17",
        "reasoning_effort": "medium",
        "reasoning_mode": "standard",
        "service_tier": "default",
        "transport_max_retries": 0,
        "max_output_tokens": 25_000,
    }
    assert source["budget"] == {
        "max_model_calls": None,
        "max_tool_calls": None,
        "max_total_tokens": 3_000_000,
        "wall_clock_timeout_seconds": 3_600,
    }
    assert source["agent_tuple"] == {
        "system_prompt_version": "SYSTEM_PROMPT_V3",
        "system_prompt_hash": (
            "sha256:441c71fdea2defed14f06b32c3fba7a7aaa19f7a3ca749bc994e72708d8a733b"
        ),
        "tool_schema_version": "v2",
        "tool_schema_hash": (
            "sha256:2ee296c2cf515bf2e0937ec1727dc02046a8560581d39b71246c5b91eccf0827"
        ),
        "context_policy_version": "phase-evidence-v5",
        "call_guard_policy": "model-tool-observability-only-v1",
        "memory_max_context_tokens": 2_000,
    }
    assert pricing["verified_at"] == "2026-08-04T14:47:00Z"
    assert pricing["input_price_per_million_usd"] == 0.75
    assert pricing["cached_input_price_per_million_usd"] == 0.075
    assert pricing["output_price_per_million_usd"] == 4.5
    assert pricing["per_run_worst_rate_reserve_usd"] == 13.6125
    assert pricing["suite_worst_rate_reserve_usd"] == 40.8375
    assert pricing["source_cost_limit_usd"] == 41.0
    assert pricing["reserve_is_expected_invoice"] is False

    assert runtime["runtime_contract_schema"] == (
        "generic-high-headroom-readiness-runtime-contract-v1"
    )
    assert runtime["runtime_evidence_schema"] == (
        "generic-high-headroom-readiness-runtime-evidence-v1"
    )
    assert readiness["gate_id"] == "d094-generic-high-headroom-readiness"
    for key in (
        "expected_runs",
        "terminal_runs_required",
        "trace_qualified_runs_required",
        "accepted_submission_runs_required",
        "evaluator_reached_runs_required",
        "official_evaluator_runs_required",
    ):
        assert readiness[key] == 3
    for key in (
        "persisted_qualification_matches_read_only_recomputation_required",
        "exact_input_telemetry_complete_required",
        "responses_completed_required",
        "truncation_disabled_required",
    ):
        assert readiness[key] is True
    for key in (
        "infrastructure_errors_allowed",
        "qualification_errors_allowed",
        "diagnostic_errors_allowed",
        "budget_terminal_runs_allowed",
        "terminal_loop_failure_runs_allowed",
        "model_or_tool_call_budget_blocks_allowed",
    ):
        assert readiness[key] == 0
    assert readiness["task_success_required"] is False
    assert readiness["hidden_acceptance_required"] is False
    assert readiness["scrr_required"] is False


def test_d094_is_source_only_and_does_not_open_downstream_authority() -> None:
    body = _body()
    authorization = body["authorization_boundary"]
    claims = body["claims_boundary"]
    next_gate = body["next_gate"]

    assert authorization["source_offline_gate_only"] is True
    assert authorization["clean_no_call_preflight_performed"] is False
    assert authorization["candidate_execution_hash_created"] is False
    assert authorization["candidate_execution_hash"] is None
    assert authorization["approved_execution_hash_created"] is False
    assert authorization["approved_execution_hash"] is None
    assert authorization["execution_hash_consumed"] is False
    assert authorization["provider_execution_authorized"] is False
    assert authorization["evaluator_execution_authorized"] is False
    assert authorization["live_cost_approved"] is False
    assert authorization["maximum_future_approval_cap_usd"] == 41.0
    assert authorization["automatic_execution_authorized"] is False

    assert claims["provider_calls_made"] == 0
    assert claims["evaluator_calls_made"] == 0
    assert claims["runtime_rows_executed"] == 0
    assert claims["run_or_result_state_created"] is False
    assert claims["added_model_cost_usd"] == 0.0
    for key in (
        "workflow_readiness_established",
        "budget_sufficiency_established",
        "task_success_or_hidden_outcome_observed",
        "no_memory_baseline_result_established",
        "comparison_denominator_eligible",
        "comparison_resource_policy_frozen",
        "memory_review_or_admission_or_index_unlocked",
        "core_campaign_unlocked",
        "analysis_ready",
        "historical_artifacts_modified",
        "historical_exact_runs_rerun",
    ):
        assert claims[key] is False
    assert next_gate["gate"] == "clean-no-call-preflight"
    assert next_gate["provider_call_allowed_during_preflight"] is False
    assert next_gate["candidate_execution_hash_required"] is True
    assert next_gate["separate_user_approval_required"] is True


@pytest.mark.parametrize(
    ("relative_path", "old", "new", "expected_error"),
    [
        (
            "reports/live-pilot/artifacts/d093-readiness-budget-outcome-correction.json",
            b"readiness_inconclusive",
            b"readiness-inconclusive",
            "D-093 source file hash drifted",
        ),
        (
            "experiments/generic-high-headroom-readiness-v2v5-20260804-r1.yaml",
            b"max_total_tokens: 3000000",
            b"max_total_tokens: 3000001",
            "D-094 suite source file hash drifted",
        ),
        (
            "data/dataset-manifest.yaml",
            b"status: frozen",
            b"status: froZen",
            "frozen dataset manifest source file hash drifted",
        ),
        (
            "tasks/dev-train/anyio-interrupt-runner-cleanup/environment.yaml",
            b"task-environment-v1",
            b"task-environment-v2",
            "anyio-interrupt-runner-cleanup environment descriptor source file hash drifted",
        ),
    ],
)
def test_d094_builder_fails_closed_on_bound_source_tampering(
    tmp_path: Path,
    relative_path: str,
    old: bytes,
    new: bytes,
    expected_error: str,
) -> None:
    builder = _module(BUILDER_PATH, f"d094_builder_tamper_{tmp_path.name}")
    _copy_bound_sources(builder, tmp_path)
    target = tmp_path / relative_path
    source = target.read_bytes()
    assert old in source
    assert len(old) == len(new)
    target.write_bytes(source.replace(old, new, 1))

    with pytest.raises(builder.D094BuildError, match=expected_error):
        builder.build_source_gate(
            repo_root=tmp_path,
            recorded_at=builder.RECORDED_AT,
        )


def test_d094_artifact_is_leak_safe_and_builder_has_no_execution_capability() -> None:
    serialized = ARTIFACT_PATH.read_text(encoding="utf-8").lower()
    for forbidden in (
        "diff --git",
        "@@ -",
        "private_spec_hash",
        "hidden_tests",
        "reference_patch",
        "submitted_patch",
        "candidate_patch",
        "request_body",
        "response_body",
        "openai_api_key",
    ):
        assert forbidden not in serialized

    source = BUILDER_PATH.read_text(encoding="utf-8")
    imports = " ".join(re.findall(r"(?:import|from)\s+([^\n]+)", source)).lower()
    for forbidden_import in (
        "openai",
        "sqlite3",
        "subprocess",
        "patchloop.agent",
        "patchloop.evals",
        "patchloop.state",
        "patchloop.sandbox",
    ):
        assert forbidden_import not in imports
