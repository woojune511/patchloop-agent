from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

ARTIFACT_PATH = Path(
    "reports/live-pilot/artifacts/d081-condition-neutral-budget-candidate.json"
)


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _walk_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            nested for child in value.values() for nested in _walk_keys(child)
        }
    if isinstance(value, list):
        return {nested for child in value for nested in _walk_keys(child)}
    return set()


def test_d081_candidate_has_exact_schema_and_strict_types() -> None:
    payload = _load_json(ARTIFACT_PATH)

    assert set(payload) == {
        "schema_version",
        "candidate_id",
        "evidence_scope",
        "eligible_process_runs",
        "derivation",
        "candidate_budget",
        "source_contract",
        "pricing",
        "readiness_panel",
        "claims_boundary",
    }
    assert payload["schema_version"] == "condition-neutral-budget-candidate-v1"
    assert payload["candidate_id"] == "d081-condition-neutral-budget-candidate"

    evidence_scope = payload["evidence_scope"]
    assert isinstance(evidence_scope, dict)
    assert set(evidence_scope) == {
        "schema_version",
        "public_process_only",
        "selection_rule",
        "task_success_used_for_selection",
        "private_evaluator_outcomes_used_for_selection",
        "sources",
    }
    assert evidence_scope["public_process_only"] is True
    assert evidence_scope["task_success_used_for_selection"] is False
    assert evidence_scope["private_evaluator_outcomes_used_for_selection"] is False
    sources = evidence_scope["sources"]
    assert isinstance(sources, list)
    assert len(sources) == 2
    assert all(
        isinstance(source, dict) and set(source) == {"role", "path", "sha256"}
        for source in sources
    )

    runs = payload["eligible_process_runs"]
    assert isinstance(runs, list)
    assert len(runs) == 4
    for run in runs:
        assert isinstance(run, dict)
        assert set(run) == {
            "experiment_id",
            "task_id",
            "dataset_role",
            "run_id",
            "agent_submission_completed",
            "official_evaluator_completed",
            "trace_qualified",
            "usage",
        }
        assert run["agent_submission_completed"] is True
        assert run["official_evaluator_completed"] is True
        assert run["trace_qualified"] is True
        usage = run["usage"]
        assert isinstance(usage, dict)
        assert set(usage) == {
            "model_calls",
            "tool_calls",
            "total_tokens",
            "wall_clock_ms",
        }
        assert all(type(value) is int and value > 0 for value in usage.values())

    budget = payload["candidate_budget"]
    assert isinstance(budget, dict)
    assert set(budget) == {
        "schema_version",
        "max_model_calls",
        "max_tool_calls",
        "max_total_tokens",
        "wall_clock_timeout_seconds",
        "max_output_tokens",
        "count_limits_are_observability_only",
        "call_guard_policy",
        "condition_neutral",
        "implementation_status",
    }
    assert budget["max_model_calls"] is None
    assert budget["max_tool_calls"] is None
    for key in (
        "max_total_tokens",
        "wall_clock_timeout_seconds",
        "max_output_tokens",
    ):
        assert type(budget[key]) is int
        assert budget[key] > 0
    assert budget["count_limits_are_observability_only"] is True
    assert budget["call_guard_policy"] == "model-tool-observability-only-v1"
    assert budget["condition_neutral"] is True
    assert budget["implementation_status"] == "source-contract-implemented"

    source_contract = payload["source_contract"]
    assert isinstance(source_contract, dict)
    assert set(source_contract) == {
        "schema_version",
        "implementation_status",
        "experiment_id",
        "source_config_path",
        "runtime_contract_schema_version",
        "runtime_evidence_schema_version",
        "call_guard_policy",
        "readiness_gate_schema_version",
        "qualification_projection_schema_version",
        "qualification_projection_check_id",
    }
    assert source_contract == {
        "schema_version": "condition-neutral-source-contract-binding-v1",
        "implementation_status": "source-contract-implemented",
        "experiment_id": "generic-baseline-readiness-v2v5-20260803-r3",
        "source_config_path": (
            "experiments/generic-baseline-readiness-v2v5-20260803-r3.yaml"
        ),
        "runtime_contract_schema_version": "generic-baseline-runtime-contract-v2",
        "runtime_evidence_schema_version": "generic-baseline-runtime-evidence-v2",
        "call_guard_policy": "model-tool-observability-only-v1",
        "readiness_gate_schema_version": "generic-baseline-readiness-gate-v2",
        "qualification_projection_schema_version": (
            "qualification-gate-check-projection-v1"
        ),
        "qualification_projection_check_id": "disabled_call_guard_contract",
    }


def test_d081_candidate_recomputes_source_hashes_and_process_selection() -> None:
    payload = _load_json(ARTIFACT_PATH)
    evidence_scope = payload["evidence_scope"]
    assert isinstance(evidence_scope, dict)
    sources = evidence_scope["sources"]
    assert isinstance(sources, list)

    source_by_role = {source["role"]: source for source in sources}
    assert set(source_by_role) == {
        "d077-readiness-report",
        "d080-workflow-completion-report",
    }
    for source in sources:
        source_path = Path(source["path"])
        assert source_path.is_file()
        assert _sha256_file(source_path) == source["sha256"]

    d077 = _load_json(Path(source_by_role["d077-readiness-report"]["path"]))
    d080 = _load_json(
        Path(source_by_role["d080-workflow-completion-report"]["path"])
    )
    qualification_rows = d077["qualifications"]
    assert isinstance(qualification_rows, list)
    qualifications = {
        qualification["run_id"]: qualification
        for qualification in qualification_rows
    }

    expected_runs: list[dict[str, object]] = []
    for source_run in d077["runs"]:
        assert isinstance(source_run, dict)
        if not (
            source_run["agent_submission_status"] == "completed"
            and source_run["evaluation_status"] == "completed"
            and source_run["official"] is True
        ):
            continue
        qualification = qualifications[source_run["run_id"]]
        expected_runs.append(
            {
                "experiment_id": d077["experiment_id"],
                "task_id": source_run["task_id"],
                "dataset_role": source_run["dataset_role"],
                "run_id": source_run["run_id"],
                "agent_submission_completed": True,
                "official_evaluator_completed": True,
                "trace_qualified": qualification["qualified"],
                "usage": {
                    key: source_run["usage"][key]
                    for key in (
                        "model_calls",
                        "tool_calls",
                        "total_tokens",
                        "wall_clock_ms",
                    )
                },
            }
        )

    d080_run = d080["run"]
    d080_usage = d080["budget"]["actual_usage"]
    assert d080_run["agent_submission_status"] == "completed"
    assert d080_run["evaluation_status"] == "completed"
    assert d080_run["official"] is True
    expected_runs.append(
        {
            "experiment_id": d080["experiment_id"],
            "task_id": d080_run["task_id"],
            "dataset_role": d080_run["dataset_role"],
            "run_id": d080_run["run_id"],
            "agent_submission_completed": True,
            "official_evaluator_completed": True,
            "trace_qualified": d080["qualification"]["qualified"],
            "usage": {
                key: d080_usage[key]
                for key in (
                    "model_calls",
                    "tool_calls",
                    "total_tokens",
                    "wall_clock_ms",
                )
            },
        }
    )

    actual_runs = payload["eligible_process_runs"]
    assert isinstance(actual_runs, list)
    assert {run["task_id"] for run in actual_runs} == {
        "babel-strict-grouped-decimal-trailing-zeroes",
        "moto-query-scanned-count",
        "hf-hub-xet-endpoint-propagation",
        "pyfakefs-makedirs-parent-traversal",
    }
    assert {run["run_id"]: run for run in actual_runs} == {
        run["run_id"]: run for run in expected_runs
    }


def test_d081_candidate_recomputes_budget_and_cost_derivation() -> None:
    payload = _load_json(ARTIFACT_PATH)
    runs = payload["eligible_process_runs"]
    derivation = payload["derivation"]
    budget = payload["candidate_budget"]
    pricing = payload["pricing"]
    assert isinstance(runs, list)
    assert isinstance(derivation, dict)
    assert isinstance(budget, dict)
    assert isinstance(pricing, dict)

    assert set(derivation) == {
        "schema_version",
        "maximum_observed_process_usage",
        "memory_allowance",
        "next_response_allowance_tokens",
        "token_subtotal",
        "token_headroom_multiplier",
        "unrounded_token_budget",
        "token_round_up_quantum",
        "rounded_token_budget",
        "wall_headroom_multiplier",
        "unrounded_wall_budget_seconds",
        "wall_round_up_quantum_seconds",
        "rounded_wall_budget_seconds",
    }
    maximum = derivation["maximum_observed_process_usage"]
    assert isinstance(maximum, dict)
    assert set(maximum) == {
        "source_run_id",
        "model_calls",
        "tool_calls",
        "total_tokens",
        "wall_clock_ms",
    }
    expected_maximum = {
        metric: max(run["usage"][metric] for run in runs)
        for metric in ("model_calls", "tool_calls", "total_tokens", "wall_clock_ms")
    }
    assert maximum["source_run_id"] == "run_606349c2c56342d4"
    assert {metric: maximum[metric] for metric in expected_maximum} == expected_maximum

    memory_allowance = derivation["memory_allowance"]
    assert isinstance(memory_allowance, dict)
    assert set(memory_allowance) == {
        "tokens_per_model_call",
        "observed_model_calls",
        "total_tokens",
    }
    assert all(type(value) is int for value in memory_allowance.values())
    assert memory_allowance["total_tokens"] == (
        memory_allowance["tokens_per_model_call"]
        * memory_allowance["observed_model_calls"]
    )
    assert memory_allowance == {
        "tokens_per_model_call": 2000,
        "observed_model_calls": 84,
        "total_tokens": 168000,
    }

    subtotal = (
        maximum["total_tokens"]
        + memory_allowance["total_tokens"]
        + derivation["next_response_allowance_tokens"]
    )
    assert subtotal == derivation["token_subtotal"] == 1983707
    unrounded_tokens = subtotal * derivation["token_headroom_multiplier"]
    assert unrounded_tokens == pytest.approx(
        derivation["unrounded_token_budget"]
    )
    token_quantum = derivation["token_round_up_quantum"]
    rounded_tokens = math.ceil(unrounded_tokens / token_quantum) * token_quantum
    assert rounded_tokens == derivation["rounded_token_budget"] == 2400000
    assert budget["max_total_tokens"] == rounded_tokens

    unrounded_wall = (
        maximum["wall_clock_ms"]
        / 1000
        * derivation["wall_headroom_multiplier"]
    )
    assert unrounded_wall == pytest.approx(
        derivation["unrounded_wall_budget_seconds"]
    )
    wall_quantum = derivation["wall_round_up_quantum_seconds"]
    rounded_wall = math.ceil(unrounded_wall / wall_quantum) * wall_quantum
    assert rounded_wall == derivation["rounded_wall_budget_seconds"] == 1800
    assert budget["wall_clock_timeout_seconds"] == rounded_wall

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
        "readiness_run_count",
        "readiness_panel_reserve_usd",
        "recommended_cost_cap_usd",
    }
    for key in (
        "input_price_per_million_usd",
        "cached_input_price_per_million_usd",
        "output_price_per_million_usd",
        "reserve_rate_per_million_usd",
        "per_run_cost_reserve_usd",
        "readiness_panel_reserve_usd",
        "recommended_cost_cap_usd",
    ):
        assert type(pricing[key]) is float
    assert type(pricing["readiness_run_count"]) is int
    reserve = (
        budget["max_total_tokens"] + budget["max_output_tokens"]
    ) * pricing["reserve_rate_per_million_usd"] / 1_000_000
    assert reserve == pytest.approx(pricing["per_run_cost_reserve_usd"])
    assert reserve == pytest.approx(10.9125)
    assert pricing["readiness_panel_reserve_usd"] == pytest.approx(
        reserve * pricing["readiness_run_count"]
    )
    assert pricing["readiness_panel_reserve_usd"] == pytest.approx(43.65)
    assert pricing["recommended_cost_cap_usd"] == pytest.approx(44.0)


def test_d081_candidate_preserves_panel_and_claims_boundaries() -> None:
    payload = _load_json(ARTIFACT_PATH)
    panel = payload["readiness_panel"]
    claims = payload["claims_boundary"]
    assert isinstance(panel, dict)
    assert isinstance(claims, dict)

    assert set(panel) == {
        "schema_version",
        "purpose",
        "conditions",
        "repetitions",
        "seed",
        "expected_runs",
        "ordered_tasks",
        "gate",
    }
    assert panel["conditions"] == ["no_memory"]
    assert type(panel["repetitions"]) is int and panel["repetitions"] == 1
    assert type(panel["seed"]) is int and panel["seed"] == 20260723
    assert type(panel["expected_runs"]) is int and panel["expected_runs"] == 4
    tasks = panel["ordered_tasks"]
    assert isinstance(tasks, list)
    assert [task["task_id"] for task in tasks] == [
        "babel-strict-grouped-decimal-trailing-zeroes",
        "moto-query-scanned-count",
        "pyfakefs-makedirs-parent-traversal",
        "hf-hub-xet-endpoint-propagation",
    ]
    assert all(
        isinstance(task, dict)
        and set(task) == {"task_id", "dataset_role", "path", "public_pattern"}
        and Path(task["path"]).is_file()
        for task in tasks
    )
    assert [task["dataset_role"] for task in tasks] == [
        "development-validation",
        "development-validation",
        "memory-development",
        "memory-development",
    ]

    gate = panel["gate"]
    assert isinstance(gate, dict)
    assert set(gate) == {
        "schema_version",
        "expected_runs",
        "required_terminal_runs",
        "required_trace_qualified_runs",
        "required_official_evaluator_completed_runs",
        "allowed_infrastructure_errors",
        "allowed_qualification_errors",
        "allowed_diagnostic_errors",
        "allowed_budget_terminal_runs",
        "call_guard_policy",
        "qualification_projection_schema_version",
        "qualification_projection_check_id",
        "required_disabled_call_guard_projection_runs",
        "required_disabled_call_guard_projection_count_per_run",
        "required_call_guard_contract_passed",
        "required_terminal_loop_failure_runs",
        "task_success_required",
    }
    for key in (
        "expected_runs",
        "required_terminal_runs",
        "required_trace_qualified_runs",
        "required_official_evaluator_completed_runs",
        "allowed_infrastructure_errors",
        "allowed_qualification_errors",
        "allowed_diagnostic_errors",
        "allowed_budget_terminal_runs",
        "required_disabled_call_guard_projection_runs",
        "required_disabled_call_guard_projection_count_per_run",
        "required_terminal_loop_failure_runs",
    ):
        assert type(gate[key]) is int
    assert gate["schema_version"] == "generic-baseline-readiness-gate-v2"
    assert gate["expected_runs"] == gate["required_terminal_runs"] == 4
    assert gate["required_trace_qualified_runs"] == 4
    assert gate["required_official_evaluator_completed_runs"] == 4
    assert gate["allowed_infrastructure_errors"] == 0
    assert gate["allowed_qualification_errors"] == 0
    assert gate["allowed_diagnostic_errors"] == 0
    assert gate["allowed_budget_terminal_runs"] == 0
    assert gate["call_guard_policy"] == "model-tool-observability-only-v1"
    assert gate["qualification_projection_schema_version"] == (
        "qualification-gate-check-projection-v1"
    )
    assert gate["qualification_projection_check_id"] == (
        "disabled_call_guard_contract"
    )
    assert gate["required_disabled_call_guard_projection_runs"] == 4
    assert gate["required_disabled_call_guard_projection_count_per_run"] == 1
    assert gate["required_call_guard_contract_passed"] is True
    assert gate["required_terminal_loop_failure_runs"] == 0
    assert gate["task_success_required"] is False

    assert set(claims) == {
        "source_contract_implemented",
        "calibration_only",
        "comparison_budget_frozen",
        "live_execution_approved",
        "provider_calls_made",
        "model_cost_usd",
        "comparison_denominator_eligible",
        "no_memory_baseline_unlocked",
        "memory_admission_unlocked",
        "core_campaign_unlocked",
        "historical_artifacts_modified",
        "private_evaluator_outcomes_used_for_selection",
    }
    assert claims == {
        "source_contract_implemented": True,
        "calibration_only": True,
        "comparison_budget_frozen": False,
        "live_execution_approved": False,
        "provider_calls_made": 0,
        "model_cost_usd": 0.0,
        "comparison_denominator_eligible": False,
        "no_memory_baseline_unlocked": False,
        "memory_admission_unlocked": False,
        "core_campaign_unlocked": False,
        "historical_artifacts_modified": False,
        "private_evaluator_outcomes_used_for_selection": False,
    }
    assert type(claims["provider_calls_made"]) is int
    assert type(claims["model_cost_usd"]) is float


def test_d081_candidate_binds_the_implemented_source_contract() -> None:
    from patchloop.evals import runner as eval_runner

    payload = _load_json(ARTIFACT_PATH)
    source_contract = payload["source_contract"]
    budget = payload["candidate_budget"]
    panel = payload["readiness_panel"]
    assert isinstance(source_contract, dict)
    assert isinstance(budget, dict)
    assert isinstance(panel, dict)

    source_config = Path(source_contract["source_config_path"])
    assert source_config.is_file()
    suite = eval_runner.load_suite(source_config)
    assert suite.experiment_id == source_contract["experiment_id"]
    assert suite.experiment_id == (
        eval_runner.GENERIC_BASELINE_READINESS_D081_EXPERIMENT_ID
    )
    assert suite.budget.max_model_calls is budget["max_model_calls"]
    assert suite.budget.max_tool_calls is budget["max_tool_calls"]
    assert suite.budget.max_total_tokens == budget["max_total_tokens"]
    assert (
        suite.budget.wall_clock_timeout_seconds
        == budget["wall_clock_timeout_seconds"]
    )
    assert suite.max_output_tokens == budget["max_output_tokens"]

    runtime_contract = eval_runner._experiment_runtime_contract(
        suite,
        harness_git_commit="a" * 40,
    )
    assert runtime_contract is not None
    assert runtime_contract["schema_version"] == source_contract[
        "runtime_contract_schema_version"
    ]
    assert runtime_contract["call_guard_policy"] == source_contract[
        "call_guard_policy"
    ]
    assert source_contract["runtime_evidence_schema_version"] == (
        "generic-baseline-runtime-evidence-v2"
    )
    assert source_contract["readiness_gate_schema_version"] == panel["gate"][
        "schema_version"
    ]
    assert source_contract["qualification_projection_schema_version"] == panel[
        "gate"
    ]["qualification_projection_schema_version"]
    assert source_contract["qualification_projection_check_id"] == panel["gate"][
        "qualification_projection_check_id"
    ]


def test_d081_candidate_excludes_sensitive_or_private_payloads() -> None:
    checked_text = ARTIFACT_PATH.read_text(encoding="utf-8")
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
