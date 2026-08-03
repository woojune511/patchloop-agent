from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

GATE_PATH = Path(
    "reports/live-pilot/artifacts/"
    "d084-condition-neutral-comparison-runtime-gate.json"
)
D083_PATH = Path(
    "reports/live-pilot/artifacts/"
    "d083-condition-neutral-comparison-budget-freeze.json"
)
D083_SHA256 = (
    "sha256:e01c5f0107592e1c29c1ec8264f32bf05c979a718c353c37acb0d87fafd2cb88"
)
D084_SHA256 = (
    "sha256:e7fb7b7e7e9dad3e6b31fb781f09151b940bf226bdd5876e5e75e472ff24b701"
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _walk_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            nested for child in value.values() for nested in _walk_keys(child)
        }
    if isinstance(value, list):
        return {
            nested for child in value for nested in _walk_keys(child)
        }
    return set()


def test_d084_gate_binds_the_exact_d083_profile() -> None:
    payload = _load_json(GATE_PATH)

    assert payload["schema_version"] == (
        "condition-neutral-comparison-runtime-gate-v1"
    )
    assert payload["gate_id"] == (
        "d084-condition-neutral-comparison-runtime-gate"
    )
    predecessor = payload["predecessor"]
    assert predecessor == {
        "schema_version": "condition-neutral-comparison-budget-freeze-v1",
        "freeze_id": "d083-condition-neutral-comparison-budget-freeze",
        "path": D083_PATH.as_posix(),
        "sha256": D083_SHA256,
        "historical_artifact_modified": False,
    }
    assert _sha256_file(D083_PATH) == D083_SHA256

    profile = payload["comparison_profile"]
    assert profile["profile_id"] == (
        "gpt54mini-v2v5-condition-neutral-1600k-v1"
    )
    assert profile["transport_max_retries"] == 0
    assert profile["max_output_tokens"] == 25_000
    assert profile["memory_max_context_tokens"] == 2_000
    assert profile["budget"] == {
        "max_model_calls": None,
        "max_tool_calls": None,
        "max_total_tokens": 1_600_000,
        "wall_clock_timeout_seconds": 1_800,
    }
    assert profile["call_guard_policy"] == (
        "model-tool-observability-only-v1"
    )


def test_d084_gate_seals_the_plan_manifest_start_resume_chain() -> None:
    payload = _load_json(GATE_PATH)
    runtime = payload["runtime_contract"]
    evidence = payload["runtime_evidence"]
    matrix = payload["offline_binding_matrix"]

    assert runtime["schema_version"] == (
        "condition-neutral-comparison-runtime-contract-v1"
    )
    assert runtime["comparison_budget_policy"]["content_hash"] == D083_SHA256
    assert runtime["included_in_execution_hash"] is True
    assert runtime["manifest_reconstructed_before_start"] is True
    assert set(runtime["execution_plan_bound_fields"]) == {
        "purpose",
        "memory_conditions",
        "model_provider",
        "model_id",
        "reasoning_effort",
        "reasoning_mode",
        "service_tier",
        "transport_max_retries",
        "max_output_tokens",
        "budget",
        "memory_max_context_tokens",
        "tool_schema_version",
        "context_policy_version",
        "system_prompt_hash",
        "tool_schema_hash",
        "call_guard_policy",
        "comparison_budget_policy",
        "harness_git_commit",
    }

    assert evidence == {
        "schema_version": "condition-neutral-comparison-runtime-evidence-v1",
        "storage_boundary": "RunStarted.runtime_contract_artifact",
        "content_addressed": True,
        "descriptor_and_bytes_verified": True,
        "start_validation": True,
        "resume_validation": True,
        "purpose_and_memory_condition_bound": True,
        "budget_and_call_guard_policy_bound": True,
    }
    for field in (
        "source_suite_exact_selector",
        "execution_plan_runtime_contract",
        "execution_hash_binding",
        "run_manifest_exact_profile",
        "pre_start_manifest_reconstruction",
        "run_started_runtime_cas",
        "resume_runtime_cas_validation",
        "budget_diagnostic_exact_profile",
        "no_memory_trace_qualification",
        "core_four_condition_plan_manifest_runtime_structure",
        "core_live_authorization_fail_closed",
    ):
        assert matrix[field] is True
    assert matrix["core_memory_condition_terminal_qualification"] is False


def test_d084_gate_keeps_core_terminal_qualification_closed() -> None:
    payload = _load_json(GATE_PATH)
    boundary = payload["qualification_boundary"]
    claims = payload["claims_boundary"]

    assert boundary["no_memory_required_checks"] == [
        "approved_execution_plan",
        "comparison_runtime_contract",
        "disabled_call_guard_contract",
        "pricing_start_freshness",
        "no_memory_boundary",
    ]
    assert boundary["budget_diagnostic_requires_exact_profile"] is True
    assert boundary["arbitrary_or_partial_null_count_limits_rejected"] is True
    assert boundary["core_structural_conditions_supported"] == [
        "no_memory",
        "raw_trace",
        "structured",
        "selective_structured",
    ]
    assert boundary["core_terminal_qualification_implemented"] is False
    assert boundary["core_preflight_blocker_code"] == (
        "CORE_MEMORY_RUNTIME_BINDING_PENDING"
    )
    assert claims["no_memory_trace_qualification_supported"] is True
    assert claims["core_four_condition_structure_supported"] is True
    assert claims["core_memory_condition_terminal_qualification_supported"] is False
    assert claims["core_campaign_unlocked"] is False
    assert claims["memory_admission_unlocked"] is False


def test_d084_gate_preserves_authority_and_historical_boundaries() -> None:
    payload = _load_json(GATE_PATH)
    historical = payload["historical_compatibility"]
    authorization = payload["authorization_boundary"]
    verification = payload["verification"]
    claims = payload["claims_boundary"]

    assert historical == {
        "schema_version": "condition-neutral-comparison-historical-boundary-v1",
        "d081_nullable_count_profile_reinterpreted": False,
        "historical_250k_profile_reinterpreted": False,
        "historical_artifacts_modified": False,
        "exact_profile_selection_required": True,
    }
    assert authorization["offline_gate_only"] is True
    assert authorization["provider_execution_authorized"] is False
    assert authorization["approved_execution_hash_created"] is False
    assert authorization["live_cost_approval_embedded"] is False
    assert authorization["source_cost_caps_changed"] is False
    assert authorization["core_live_authorization_blocked"] is True
    assert authorization["automatic_execution_authorized"] is False
    assert verification == {
        "schema_version": "condition-neutral-comparison-runtime-verification-v1",
        "verified_on": "2026-08-03",
        "focused": {
            "command": (
                "uv run pytest -q tests/test_d084_manifest_contract.py "
                "tests/test_d084_runtime_binding.py "
                "tests/test_d084_qualification_binding.py "
                "tests/test_d084_runtime_gate_artifact.py "
                "tests/test_experiments.py::"
                "test_generic_comparison_runtime_gate_excludes_v10_v11_and_binds_runtime_contract "
                "tests/test_experiments.py::"
                "test_d084_core_runtime_binding_stays_closed_with_a_valid_memory_index"
            ),
            "passed": 68,
            "failed": 0,
        },
        "repository_regression": {
            "command": "uv run pytest -q",
            "collected": 1304,
            "passed": 1297,
            "skipped": 7,
            "failed": 0,
            "duration_seconds": 645.5,
        },
        "static_checks": {
            "ruff_check": True,
            "compileall": True,
            "git_diff_check": True,
            "json_parse": True,
        },
        "provider_calls_made": 0,
        "added_model_cost_usd": 0.0,
    }
    assert _sha256_file(GATE_PATH) == D084_SHA256
    assert claims["provider_calls_made"] == 0
    assert claims["added_model_cost_usd"] == 0.0
    assert claims["live_execution_authorized"] is False
    assert claims["no_memory_baseline_result_established"] is False
    assert claims["comparison_denominator_eligible"] is False
    assert claims["analysis_ready"] is False
    assert claims["historical_artifacts_modified"] is False


def test_d084_gate_contains_no_private_or_provider_payload() -> None:
    checked_text = GATE_PATH.read_text(encoding="utf-8")
    payload = json.loads(checked_text)
    forbidden_keys = {
        "api_key",
        "authorization",
        "headers",
        "request",
        "request_body",
        "response",
        "response_body",
        "private_spec",
        "private_spec_hash",
        "reference_patch",
        "hidden_assertion",
        "hidden_tests",
        "patch_body",
    }
    assert forbidden_keys.isdisjoint(_walk_keys(payload))
    for marker in (
        "OPENAI_API_KEY",
        "Bearer ",
        "sk-",
        '"request_body"',
        '"response_body"',
        '"private_spec_hash"',
        '"reference_patch"',
        '"hidden_tests"',
        ".patchloop-hidden",
        "private.yaml",
        "reference.patch",
    ):
        assert marker not in checked_text


def test_d084_gate_identity_and_closed_core_boundary_are_documented() -> None:
    artifact_path = GATE_PATH.as_posix()
    for path in (
        Path("README.md"),
        Path("docs/02-architecture.md"),
        Path("docs/03-contracts.md"),
        Path("docs/04-evaluation-protocol.md"),
        Path("docs/05-implementation-plan.md"),
        Path("docs/06-decisions.md"),
        Path("docs/08-limitations.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert artifact_path in text
        assert "condition-neutral-comparison-runtime-contract-v1" in text
        assert "condition-neutral-comparison-runtime-evidence-v1" in text
        assert D084_SHA256 in text

    limitations = Path("docs/08-limitations.md").read_text(encoding="utf-8")
    assert "terminal qualification remains pending" in limitations
    assert "keep core non-runnable" in " ".join(limitations.split())
