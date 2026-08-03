from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from patchloop.agent.model import SYSTEM_PROMPT_V3
from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.evals import runner as eval_runner
from patchloop.evals.runner import (
    CONDITION_NEUTRAL_COMPARISON_CAMPAIGN_EXPERIMENT_ID,
    CONDITION_NEUTRAL_COMPARISON_PILOT_ADMISSION_SCHEMA,
    CONDITION_NEUTRAL_COMPARISON_PILOT_GATE_SCHEMA,
    CONDITION_NEUTRAL_COMPARISON_PILOT_REQUIRED_CHECKS,
)
from patchloop.util import canonical_json, sha256_text

GATE_PATH = Path(
    "reports/live-pilot/artifacts/"
    "d085-condition-neutral-comparison-pilot-source-gate.json"
)
D083_PATH = Path(
    "reports/live-pilot/artifacts/"
    "d083-condition-neutral-comparison-budget-freeze.json"
)
D084_PATH = Path(
    "reports/live-pilot/artifacts/"
    "d084-condition-neutral-comparison-runtime-gate.json"
)
D083_SHA256 = (
    "sha256:e01c5f0107592e1c29c1ec8264f32bf05c979a718c353c37acb0d87fafd2cb88"
)
D084_SHA256 = (
    "sha256:e7fb7b7e7e9dad3e6b31fb781f09151b940bf226bdd5876e5e75e472ff24b701"
)
D085_SHA256 = (
    "sha256:8b60cb2e62a6259db29527a600712e95b36390a1c07da9fb66e6f1d7d16f51d2"
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


def test_d085_source_gate_preserves_d083_and_d084_predecessors() -> None:
    payload = _load_json(GATE_PATH)

    assert payload["schema_version"] == (
        "condition-neutral-comparison-pilot-source-gate-v1"
    )
    assert payload["gate_id"] == (
        "d085-condition-neutral-comparison-pilot-source-gate"
    )
    assert payload["predecessors"] == [
        {
            "gate_id": "d083-condition-neutral-comparison-budget-freeze",
            "path": D083_PATH.as_posix(),
            "sha256": D083_SHA256,
            "modified": False,
        },
        {
            "gate_id": "d084-condition-neutral-comparison-runtime-gate",
            "path": D084_PATH.as_posix(),
            "sha256": D084_SHA256,
            "modified": False,
        },
    ]
    assert _sha256_file(D083_PATH) == D083_SHA256
    assert _sha256_file(D084_PATH) == D084_SHA256


def test_d085_source_gate_has_the_documented_final_content_hash() -> None:
    assert _sha256_file(GATE_PATH) == D085_SHA256


def test_d085_source_gate_matches_the_checked_in_exact_pilot() -> None:
    payload = _load_json(GATE_PATH)
    source = payload["pilot_source"]
    pricing = payload["pricing"]
    suite_path = Path(source["suite_path"])
    suite = yaml.safe_load(suite_path.read_text(encoding="utf-8"))

    assert source["experiment_id"] == (
        "dev-validation-condition-neutral-v2v5-pilot-20260803-r1"
    )
    assert suite["experiment_id"] == source["experiment_id"]
    assert suite["purpose"] == source["purpose"]
    assert suite["tasks"] == [source["task"]]
    assert suite["conditions"] == [source["memory_condition"]]
    assert suite["repetitions"] == source["repetitions"] == 1
    assert suite["model"] == source["model_provider"] == "openai"
    for field in (
        "model_id",
        "reasoning_effort",
        "reasoning_mode",
        "service_tier",
        "transport_max_retries",
        "max_output_tokens",
    ):
        assert suite[field] == source[field]
    assert suite["budget"] == source["budget"] == {
        "max_model_calls": None,
        "max_tool_calls": None,
        "max_total_tokens": 1_600_000,
        "wall_clock_timeout_seconds": 1_800,
    }
    assert suite["memory_token_budget"] == (
        source["memory_max_context_tokens"]
    ) == 2_000
    assert suite["estimated_cost_usd"] == 7.3125
    assert suite["cost_limit_usd"] == 8
    assert suite["pricing_verified_at"].isoformat().replace(
        "+00:00", "Z"
    ) == pricing["verified_at"]
    assert suite["pricing_source_url"] == pricing["source_url"]
    assert suite["model_id"] == pricing["current_snapshot"]
    for field in (
        "input_price_per_million_usd",
        "cached_input_price_per_million_usd",
        "cache_write_input_price_per_million_usd",
        "output_price_per_million_usd",
    ):
        assert suite[field] == pricing[field]
    assert suite["estimated_cost_usd"] == pricing["worst_rate_reserve_usd"]
    assert suite["cost_limit_usd"] == pricing["source_cost_limit_usd"]
    assert source["system_prompt_version"] == "SYSTEM_PROMPT_V3"
    assert source["system_prompt_hash"] == sha256_text(SYSTEM_PROMPT_V3)
    assert source["tool_schema_version"] == "v2"
    assert source["tool_schema_hash"] == sha256_text(
        canonical_json(TOOL_SCHEMAS_V2)
    )
    assert suite["live_cost_approved"] is False
    assert suite["approved_execution_hash"] is None
    assert suite.get("pilot_run_id") is None


def test_d085_source_gate_records_current_pricing_without_spend_authority() -> None:
    payload = _load_json(GATE_PATH)
    pricing = payload["pricing"]
    authorization = payload["authorization_boundary"]

    assert pricing == {
        "schema_version": "condition-neutral-comparison-pilot-pricing-v1",
        "verified_at": "2026-08-03T06:37:49Z",
        "source_url": "https://developers.openai.com/api/docs/pricing",
        "model_page_url": (
            "https://developers.openai.com/api/docs/models/gpt-5.4-mini"
        ),
        "current_snapshot": "gpt-5.4-mini-2026-03-17",
        "input_price_per_million_usd": 0.75,
        "cached_input_price_per_million_usd": 0.075,
        "cache_write_input_price_per_million_usd": None,
        "output_price_per_million_usd": 4.5,
        "worst_rate_reserve_usd": 7.3125,
        "source_cost_limit_usd": 8.0,
        "reserve_is_invoice_prediction": False,
    }
    assert authorization == {
        "schema_version": (
            "condition-neutral-comparison-pilot-source-authorization-v1"
        ),
        "source_offline_gate_only": True,
        "clean_host_preflight_performed": False,
        "candidate_execution_hash_created": False,
        "approved_execution_hash_created": False,
        "provider_execution_authorized": False,
        "live_cost_approved": False,
        "automatic_execution_authorized": False,
    }


def test_d085_readiness_is_process_only_and_keeps_research_gates_closed() -> None:
    payload = _load_json(GATE_PATH)
    binding = payload["runtime_binding"]
    predicate = payload["readiness_predicate"]
    sequencing = payload["sequencing_boundary"]
    claims = payload["claims_boundary"]

    assert binding["runtime_contract_schema"] == (
        "condition-neutral-comparison-runtime-contract-v1"
    )
    assert binding["runtime_evidence_schema"] == (
        "condition-neutral-comparison-runtime-evidence-v1"
    )
    assert all(
        binding[field] is True
        for field in (
            "execution_plan_and_hash_bound",
            "run_manifest_exact_selector",
            "pre_start_manifest_reconstruction",
            "run_started_content_addressed_evidence",
            "fresh_start_validation",
            "resume_validation",
            "paid_boundary_plan_reconstruction",
            "trace_qualification_reconstruction",
            "disabled_call_guard_qualification",
            "pricing_start_freshness_qualification",
        )
    )
    assert predicate == {
        "schema_version": (
            "condition-neutral-comparison-pilot-readiness-gate-v1"
        ),
        "expected_runs": 1,
        "terminal_runs_required": 1,
        "trace_qualified_runs_required": 1,
        "official_evaluator_runs_required": 1,
        "infrastructure_errors_allowed": 0,
        "qualification_errors_allowed": 0,
        "diagnostic_errors_allowed": 0,
        "budget_terminal_runs_allowed": 0,
        "call_guard_contract_passed_required": True,
        "terminal_loop_failure_runs_allowed": 0,
        "task_success_required": False,
        "hidden_acceptance_used_for_readiness": False,
        "scrr_used_for_readiness": False,
    }
    assert predicate["schema_version"] == (
        CONDITION_NEUTRAL_COMPARISON_PILOT_GATE_SCHEMA
    )
    assert sequencing["memory_review_before_new_no_memory_collection"] is False
    assert sequencing["memory_index_freeze_before_new_no_memory_collection"] is False
    assert sequencing["core_memory_binding_remains_pending"] is True
    assert claims["provider_calls_made"] == 0
    assert claims["added_model_cost_usd"] == 0.0
    assert claims["exact_future_campaign_pilot_admission_consumer_implemented"] is True
    assert claims["live_pilot_executed"] is False
    assert claims["pilot_readiness_result_observed"] is False
    assert claims["no_memory_baseline_result_established"] is False
    assert claims["comparison_denominator_eligible"] is False
    assert claims["memory_admission_unlocked"] is False
    assert claims["memory_index_frozen"] is False
    assert claims["core_campaign_unlocked"] is False
    assert claims["analysis_ready"] is False


def test_d085_future_campaign_admission_is_semantic_and_hash_bound() -> None:
    payload = _load_json(GATE_PATH)
    admission = payload["pilot_admission_binding"]

    assert admission == {
        "schema_version": (
            "condition-neutral-comparison-pilot-admission-binding-v1"
        ),
        "descriptor_schema": "condition-neutral-comparison-pilot-admission-v1",
        "future_campaign_experiment_id": "dev-no-memory-v5-20260730-r1",
        "pilot_and_campaign_source_commits_are_separate": True,
        "raw_source_commit_equality_required": False,
        "pilot_and_campaign_commits_require_40_hex_sha": True,
        "semantic_exact_tuple_match_required": True,
        "semantic_tuple_fields": [
            "schema_version",
            "comparison_budget_policy",
            "model_provider",
            "model_id",
            "reasoning_effort",
            "reasoning_mode",
            "service_tier",
            "transport_max_retries",
            "system_prompt_hash",
            "tool_schema_version",
            "tool_schema_hash",
            "context_policy_version",
            "max_output_tokens",
            "budget",
            "memory_max_context_tokens",
            "memory_conditions",
            "call_guard_policy",
        ],
        "qualification_source_and_approved_plan_cas_revalidated": True,
        "durable_qualification_recomputed_read_only": True,
        "persisted_and_recomputed_qualification_exact_match_required": True,
        "required_qualification_checks": [
            "approved_execution_plan",
            "comparison_runtime_contract",
            "disabled_call_guard_contract",
            "pricing_start_freshness",
        ],
        "task_success_required": False,
        "canonical_admission_hash_required_in_future_campaign_execution_plan": (
            True
        ),
        "canonical_admission_hash_required_in_future_campaign_execution_hash": (
            True
        ),
        "start_resume_and_post_run_revalidation": True,
        "future_campaign_admission_binding_implemented": True,
        "future_campaign_execution_authorized": False,
    }
    assert admission["descriptor_schema"] == (
        CONDITION_NEUTRAL_COMPARISON_PILOT_ADMISSION_SCHEMA
    )
    assert admission["future_campaign_experiment_id"] == (
        CONDITION_NEUTRAL_COMPARISON_CAMPAIGN_EXPERIMENT_ID
    )
    assert admission["required_qualification_checks"] == list(
        CONDITION_NEUTRAL_COMPARISON_PILOT_REQUIRED_CHECKS
    )
    pilot_suite = eval_runner.load_suite(
        "experiments/dev-validation-condition-neutral-v2v5-pilot-20260803-r1.yaml"
    )
    runtime_contract = eval_runner._experiment_runtime_contract(
        pilot_suite,
        harness_git_commit="0" * 40,
    )
    assert isinstance(runtime_contract, dict)
    assert set(admission["semantic_tuple_fields"]) == (
        set(runtime_contract)
        - set(eval_runner.CONDITION_NEUTRAL_COMPARISON_PILOT_RUNTIME_EXCLUSIONS)
    )


def test_d085_source_gate_records_final_offline_verification() -> None:
    verification = _load_json(GATE_PATH)["verification"]

    assert verification["schema_version"] == (
        "condition-neutral-comparison-pilot-source-verification-v1"
    )
    assert verification["verified_on"] == "2026-08-03"
    assert verification["focused"]["passed"] == 153
    assert verification["focused"]["failed"] == 0
    assert verification["repository_regression"] == {
        "command": "uv run pytest -o addopts='' -q",
        "collected": 1392,
        "passed": 1385,
        "skipped": 7,
        "failed": 0,
        "duration_seconds": 598.3,
    }
    assert all(verification["security_review"].values())
    assert all(verification["static_checks"].values())
    assert verification["provider_calls_made"] == 0
    assert verification["added_model_cost_usd"] == 0.0


def test_d085_source_gate_contains_no_secret_private_or_provider_payload() -> None:
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
        "execution_hash",
        "candidate_execution_hash",
        "approved_execution_hash",
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


def test_d085_source_identity_and_authority_boundary_are_documented() -> None:
    artifact_path = GATE_PATH.as_posix()
    for path in (
        Path("README.md"),
        Path("AGENTS.md"),
        Path("docs/02-architecture.md"),
        Path("docs/03-contracts.md"),
        Path("docs/04-evaluation-protocol.md"),
        Path("docs/05-implementation-plan.md"),
        Path("docs/06-decisions.md"),
        Path("docs/08-limitations.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert artifact_path in text
        assert "dev-validation-condition-neutral-v2v5-pilot-20260803-r1" in text
        assert "condition-neutral-comparison-runtime-contract-v1" in text
        assert "condition-neutral-comparison-runtime-evidence-v1" in text
        assert D085_SHA256 in text

    limitations = Path("docs/08-limitations.md").read_text(encoding="utf-8")
    assert "not a live result or baseline" in limitations
    assert "$20 < $87.75" in limitations
