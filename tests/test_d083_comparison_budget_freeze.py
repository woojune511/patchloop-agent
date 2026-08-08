from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from typing import Any

import yaml

from patchloop.evals.qualification import _private_leak_tokens
from patchloop.task_loader import load_task_package

FREEZE_PATH = Path(
    "reports/live-pilot/artifacts/d083-condition-neutral-comparison-budget-freeze.json"
)
D082_PATH = Path("reports/live-pilot/generic-baseline-readiness-v2v5-20260803-r3.json")
D081_PATH = Path("reports/live-pilot/artifacts/d081-condition-neutral-budget-candidate.json")
D082_SHA256 = "sha256:2a8f650e73e01aed9d629290627999232ec6aebd1769d2179bc22f084ddbede2"
D081_SHA256 = "sha256:6f871c13aee71043c20c54c72a93667600462e8369483e9354507a94d0063193"
D083_SHA256 = "sha256:e01c5f0107592e1c29c1ec8264f32bf05c979a718c353c37acb0d87fafd2cb88"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _walk_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {nested for child in value.values() for nested in _walk_keys(child)}
    if isinstance(value, list):
        return {nested for child in value for nested in _walk_keys(child)}
    return set()


def _eligible_rows(source: dict[str, Any]) -> list[dict[str, Any]]:
    qualifications = {item["run_id"]: item for item in source["qualifications"]}
    rows: list[dict[str, Any]] = []
    for run in source["runs"]:
        qualification = qualifications[run["run_id"]]
        if not (
            run["agent_submission_status"] == "completed"
            and run["evaluation_status"] == "completed"
            and run["official"] is True
            and qualification["qualified"] is True
        ):
            continue
        rows.append(
            {
                "order": run["order"],
                "task_id": run["task_id"],
                "dataset_role": run["dataset_role"],
                "run_id": run["run_id"],
                "agent_submission_completed": True,
                "official_evaluator_completed": True,
                "trace_qualified": True,
                "observed_prefix_minimum_total_budget": run["budget_pressure"][
                    "observed_prefix_minimum_total_budget"
                ],
            }
        )
    return rows


def test_d083_freeze_bytes_and_documented_identity_are_sealed() -> None:
    assert _sha256_file(FREEZE_PATH) == D083_SHA256
    for path in (
        Path("docs/archive/snapshots/d121/AGENTS.full.md"),
        Path("docs/archive/snapshots/d121/README.full.md"),
        Path("docs/archive/snapshots/d121/03-contracts.full.md"),
        Path("docs/archive/snapshots/d121/06-decisions.full.md"),
        Path("docs/archive/snapshots/d121/07-reproduction.full.md"),
        Path("docs/archive/snapshots/d121/09-evidence.full.md"),
    ):
        assert D083_SHA256 in path.read_text(encoding="utf-8")


def test_d083_freeze_has_strict_source_only_contract() -> None:
    payload = _load_json(FREEZE_PATH)

    assert set(payload) == {
        "schema_version",
        "freeze_id",
        "source_evidence",
        "eligible_process_rows",
        "derivation",
        "frozen_budget",
        "model_runtime_tuple",
        "source_contract",
        "pricing",
        "authorization_boundary",
        "claims_boundary",
    }
    assert payload["schema_version"] == ("condition-neutral-comparison-budget-freeze-v1")
    assert payload["freeze_id"] == ("d083-condition-neutral-comparison-budget-freeze")

    source = payload["source_evidence"]
    assert set(source) == {
        "schema_version",
        "evidence_scope",
        "public_process_only",
        "selection_rule",
        "task_success_used_for_selection",
        "private_evaluator_outcomes_used_for_selection",
        "sources",
    }
    assert source["schema_version"] == "public-process-budget-selection-v2"
    assert source["evidence_scope"] == "exact-d081-r3-only"
    assert source["public_process_only"] is True
    assert source["task_success_used_for_selection"] is False
    assert source["private_evaluator_outcomes_used_for_selection"] is False

    row_keys = {
        "order",
        "task_id",
        "dataset_role",
        "run_id",
        "agent_submission_completed",
        "official_evaluator_completed",
        "trace_qualified",
        "observed_prefix_minimum_total_budget",
    }
    rows = payload["eligible_process_rows"]
    assert isinstance(rows, list) and len(rows) == 4
    for row in rows:
        assert isinstance(row, dict) and set(row) == row_keys
        assert type(row["order"]) is int and row["order"] > 0
        assert type(row["observed_prefix_minimum_total_budget"]) is int
        assert row["observed_prefix_minimum_total_budget"] > 0
        assert row["agent_submission_completed"] is True
        assert row["official_evaluator_completed"] is True
        assert row["trace_qualified"] is True

    derivation = payload["derivation"]
    assert set(derivation) == {
        "schema_version",
        "selected_metric",
        "selected_run_id",
        "selected_task_id",
        "observed_prefix_minimum_total_budget",
        "headroom_multiplier",
        "unrounded_total_token_budget",
        "round_up_mode",
        "round_up_quantum_tokens",
        "rounded_total_token_budget",
        "completion_guaranteed",
    }
    assert type(derivation["observed_prefix_minimum_total_budget"]) is int
    assert type(derivation["headroom_multiplier"]) is float
    assert type(derivation["unrounded_total_token_budget"]) is float
    assert type(derivation["round_up_quantum_tokens"]) is int
    assert type(derivation["rounded_total_token_budget"]) is int
    assert derivation["completion_guaranteed"] is False

    budget = payload["frozen_budget"]
    assert set(budget) == {
        "schema_version",
        "profile_id",
        "max_model_calls",
        "max_tool_calls",
        "max_total_tokens",
        "wall_clock_timeout_seconds",
        "max_output_tokens",
        "count_limits_are_observability_only",
        "call_guard_policy",
        "condition_neutral",
        "same_budget_for_all_memory_conditions",
        "memory_conditions",
        "retained_guards",
    }
    assert budget["schema_version"] == "condition-neutral-comparison-budget-v1"
    assert budget["profile_id"] == "gpt54mini-v2v5-condition-neutral-1600k-v1"
    assert budget["max_model_calls"] is None
    assert budget["max_tool_calls"] is None
    assert budget["max_total_tokens"] == 1_600_000
    assert budget["wall_clock_timeout_seconds"] == 1_800
    assert budget["max_output_tokens"] == 25_000
    assert budget["count_limits_are_observability_only"] is True
    assert budget["call_guard_policy"] == "model-tool-observability-only-v1"
    assert budget["condition_neutral"] is True
    assert budget["same_budget_for_all_memory_conditions"] is True
    assert budget["memory_conditions"] == [
        "no_memory",
        "raw_trace",
        "structured",
        "selective_structured",
    ]
    assert budget["retained_guards"] == [
        "total-token",
        "wall-clock",
        "exact-request",
        "cost",
        "loop",
        "constrained-tool",
        "docker-network",
        "evaluator",
    ]


def test_d083_freeze_recomputes_source_hashes_and_public_row_selection() -> None:
    payload = _load_json(FREEZE_PATH)
    sources = {item["role"]: item for item in payload["source_evidence"]["sources"]}

    assert set(sources) == {
        "d082-measured-readiness-report",
        "d081-pre-run-budget-candidate",
    }
    assert sources["d082-measured-readiness-report"] == {
        "role": "d082-measured-readiness-report",
        "path": D082_PATH.as_posix(),
        "sha256": D082_SHA256,
    }
    assert sources["d081-pre-run-budget-candidate"] == {
        "role": "d081-pre-run-budget-candidate",
        "path": D081_PATH.as_posix(),
        "sha256": D081_SHA256,
    }
    assert _sha256_file(D082_PATH) == D082_SHA256
    assert _sha256_file(D081_PATH) == D081_SHA256

    d082 = _load_json(D082_PATH)
    expected = _eligible_rows(d082)
    assert payload["eligible_process_rows"] == expected
    assert [row["order"] for row in expected] == [1, 2, 3, 4]

    changed_outcomes = deepcopy(d082)
    for run in changed_outcomes["runs"]:
        run["outcome_kind"] = "ignored-by-public-process-selection"
        run["scope_compliant_success"] = not run["scope_compliant_success"]
        run["verdicts"] = {"ignored": "ignored"}
    assert _eligible_rows(changed_outcomes) == expected


def test_d083_freeze_recomputes_token_derivation_exactly() -> None:
    payload = _load_json(FREEZE_PATH)
    rows = payload["eligible_process_rows"]
    derivation = payload["derivation"]
    budget = payload["frozen_budget"]

    selected = max(
        rows,
        key=lambda row: row["observed_prefix_minimum_total_budget"],
    )
    assert selected["run_id"] == derivation["selected_run_id"]
    assert selected["task_id"] == derivation["selected_task_id"]
    assert (
        selected["observed_prefix_minimum_total_budget"]
        == (derivation["observed_prefix_minimum_total_budget"])
    )
    assert derivation["observed_prefix_minimum_total_budget"] == 1_303_223

    observed = Decimal(str(derivation["observed_prefix_minimum_total_budget"]))
    multiplier = Decimal(str(derivation["headroom_multiplier"]))
    unrounded = observed * multiplier
    assert unrounded == Decimal("1563867.6")
    assert unrounded == Decimal(str(derivation["unrounded_total_token_budget"]))

    quantum = Decimal(str(derivation["round_up_quantum_tokens"]))
    rounded = (unrounded / quantum).to_integral_value(rounding=ROUND_CEILING) * quantum
    assert rounded == Decimal("1600000")
    assert int(rounded) == derivation["rounded_total_token_budget"]
    assert int(rounded) == budget["max_total_tokens"]
    assert all(
        row["observed_prefix_minimum_total_budget"] <= budget["max_total_tokens"] for row in rows
    )
    assert derivation["completion_guaranteed"] is False


def test_d083_freeze_binds_exact_model_runtime_and_pending_templates() -> None:
    payload = _load_json(FREEZE_PATH)
    runtime = payload["model_runtime_tuple"]
    assert runtime == {
        "schema_version": "condition-neutral-comparison-runtime-tuple-v1",
        "provider": "openai",
        "model_id": "gpt-5.4-mini-2026-03-17",
        "reasoning_effort": "medium",
        "reasoning_mode": "standard",
        "service_tier": "default",
        "transport_max_retries": 0,
        "max_output_tokens": 25_000,
        "system_prompt_version": "SYSTEM_PROMPT_V3",
        "system_prompt_hash": (
            "sha256:441c71fdea2defed14f06b32c3fba7a7aaa19f7a3ca749bc994e72708d8a733b"
        ),
        "tool_schema_version": "v2",
        "tool_schema_hash": (
            "sha256:2ee296c2cf515bf2e0937ec1727dc02046a8560581d39b71246c5b91eccf0827"
        ),
        "context_policy_version": "phase-evidence-v5",
        "memory_token_budget": 2_000,
    }
    assert type(runtime["transport_max_retries"]) is int
    assert type(runtime["max_output_tokens"]) is int
    assert type(runtime["memory_token_budget"]) is int

    source_contract = payload["source_contract"]
    assert set(source_contract) == {
        "schema_version",
        "implementation_status",
        "live_runnable_suite_created",
        "runtime_wiring_complete",
        "provider_execution_authority",
        "templates",
    }
    assert source_contract["schema_version"] == ("condition-neutral-comparison-source-contract-v1")
    assert source_contract["implementation_status"] == ("policy-frozen-runtime-pending")
    assert source_contract["live_runnable_suite_created"] is False
    assert source_contract["runtime_wiring_complete"] is False
    assert source_contract["provider_execution_authority"] is False

    templates = source_contract["templates"]
    assert templates == [
        {
            "purpose": "memory-development-no-memory",
            "path": "experiments/dev-no-memory-v5.template.yaml",
            "status": "policy-frozen-runtime-pending",
        },
        {
            "purpose": "core",
            "path": "experiments/core.template.yaml",
            "status": "policy-frozen-runtime-pending",
        },
    ]
    for template in templates:
        path = Path(template["path"])
        assert path.is_file()
        suite = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert suite["purpose"] == template["purpose"]
        assert suite["model_id"] == runtime["model_id"]
        assert suite["reasoning_effort"] == runtime["reasoning_effort"]
        assert suite["reasoning_mode"] == runtime["reasoning_mode"]
        assert suite["service_tier"] == runtime["service_tier"]
        assert suite["max_output_tokens"] == runtime["max_output_tokens"]


def test_d083_freeze_recomputes_pricing_and_scale_boundaries() -> None:
    payload = _load_json(FREEZE_PATH)
    budget = payload["frozen_budget"]
    pricing = payload["pricing"]

    assert set(pricing) == {
        "schema_version",
        "verified_at",
        "source_url",
        "input_price_per_million_usd",
        "cached_input_price_per_million_usd",
        "output_price_per_million_usd",
        "reserve_rate_per_million_usd",
        "reserve_formula",
        "per_run_cost_reserve_usd",
        "schedule_reserves",
        "existing_project_cap_usd",
        "core_cap_deficit_usd",
        "core_scale_decision_required",
    }
    for key in (
        "input_price_per_million_usd",
        "cached_input_price_per_million_usd",
        "output_price_per_million_usd",
        "reserve_rate_per_million_usd",
        "per_run_cost_reserve_usd",
        "existing_project_cap_usd",
        "core_cap_deficit_usd",
    ):
        assert type(pricing[key]) is float

    per_run = (
        Decimal(budget["max_total_tokens"] + budget["max_output_tokens"])
        * Decimal(str(pricing["reserve_rate_per_million_usd"]))
        / Decimal(1_000_000)
    )
    assert per_run == Decimal("7.3125")
    assert per_run == Decimal(str(pricing["per_run_cost_reserve_usd"]))

    expected = {
        "no_memory_baseline": (12, Decimal("87.75"), 88.0),
        "maximum_dev_collection": (18, Decimal("131.625"), 132.0),
        "core": (96, Decimal("702.0"), 702.0),
    }
    assert set(pricing["schedule_reserves"]) == set(expected)
    for name, (run_count, reserve, cap) in expected.items():
        row = pricing["schedule_reserves"][name]
        assert set(row) == {
            "run_count",
            "reserve_usd",
            "recommended_approval_cap_usd",
        }
        assert type(row["run_count"]) is int
        assert type(row["reserve_usd"]) is float
        assert type(row["recommended_approval_cap_usd"]) is float
        assert row["run_count"] == run_count
        assert Decimal(str(row["reserve_usd"])) == reserve
        assert Decimal(str(row["reserve_usd"])) == per_run * run_count
        assert row["recommended_approval_cap_usd"] == cap
        assert cap == float(math.ceil(reserve))

    core_reserve = Decimal(str(pricing["schedule_reserves"]["core"]["reserve_usd"]))
    existing_cap = Decimal(str(pricing["existing_project_cap_usd"]))
    assert core_reserve - existing_cap == Decimal("552.0")
    assert pricing["core_cap_deficit_usd"] == 552.0
    assert pricing["core_scale_decision_required"] is True


def test_d083_freeze_preserves_authorization_and_claims_boundaries() -> None:
    payload = _load_json(FREEZE_PATH)
    authorization = payload["authorization_boundary"]
    claims = payload["claims_boundary"]

    assert authorization == {
        "schema_version": "comparison-budget-authorization-boundary-v1",
        "source_only_freeze": True,
        "provider_execution_authorized": False,
        "execution_hash_created": False,
        "live_cost_approval_embedded": False,
        "fresh_pricing_required_at_preflight": True,
        "maximum_pricing_age_hours": 72,
        "clean_preflight_required": True,
        "exact_execution_hash_required": True,
        "explicit_cost_approval_required": True,
        "automatic_execution_authorized": False,
    }
    assert type(authorization["maximum_pricing_age_hours"]) is int
    assert claims == {
        "comparison_budget_policy_frozen": True,
        "condition_neutral": True,
        "completion_guaranteed": False,
        "calibration_result_reinterpreted": False,
        "provider_calls_made": 0,
        "added_model_cost_usd": 0.0,
        "no_memory_baseline_result_established": False,
        "comparison_denominator_eligible": False,
        "memory_admission_unlocked": False,
        "core_campaign_unlocked": False,
        "core_cost_cap_conflict_open": True,
        "historical_artifacts_modified": False,
        "private_evaluator_outcomes_used_for_selection": False,
        "prompt_tool_or_context_tuning_authorized": False,
    }
    assert type(claims["provider_calls_made"]) is int
    assert type(claims["added_model_cost_usd"]) is float


def test_d083_freeze_excludes_private_or_provider_payloads() -> None:
    checked_text = FREEZE_PATH.read_text(encoding="utf-8")
    payload = json.loads(checked_text)
    forbidden_keys = {
        "api_key",
        "authorization",
        "headers",
        "request",
        "request_body",
        "response",
        "response_body",
        "input",
        "output",
        "instructions",
        "private_spec",
        "private_spec_hash",
        "reference_patch",
        "hidden_assertion",
        "hidden_tests",
        "verdicts",
        "scope_compliant_success",
        "outcome_kind",
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
        '"verdicts"',
        ".patchloop-hidden",
        "private.yaml",
        "reference.patch",
    ):
        assert marker not in checked_text

    leaked: list[str] = []
    task_paths = (
        "tasks/dev-train/hf-hub-xet-endpoint-propagation",
        "tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes",
        "tasks/dev-validation/moto-query-scanned-count",
        "tasks/dev-train/pyfakefs-makedirs-parent-traversal",
    )
    for task_path in task_paths:
        package = load_task_package(task_path)
        leaked.extend(
            token for token in _private_leak_tokens(package, api_key=None) if token in checked_text
        )
    assert sorted(set(leaked)) == []


def test_d083_freeze_preserves_the_d081_predecessor_bytes() -> None:
    assert _sha256_file(D081_PATH) == D081_SHA256
    predecessor = _load_json(D081_PATH)
    assert predecessor["schema_version"] == "condition-neutral-budget-candidate-v1"
    assert predecessor["claims_boundary"]["comparison_budget_frozen"] is False
    assert predecessor["claims_boundary"]["historical_artifacts_modified"] is False
