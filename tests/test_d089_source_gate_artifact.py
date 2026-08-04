from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals import runner as eval_runner
from patchloop.util import sha256_bytes

ARTIFACT = Path(
    "reports/live-pilot/artifacts/"
    "d089-anyio-budget-only-readiness-probe-source-gate.json"
)
D088_PORTABLE = Path(
    "reports/live-pilot/"
    "dev-no-memory-condition-neutral-accrued-cap-20260804-r1.json"
)
EXPECTED_PREDECESSORS = {
    "immutable-d087-suite": (
        "experiments/dev-no-memory-condition-neutral-accrued-cap-20260804-r1.yaml",
        "sha256:44de6899656c96830d3a0aa3326777848c5d632ef903eccc166839fa1caeaf79",
    ),
    "immutable-d087-source-gate": (
        "reports/live-pilot/artifacts/"
        "d087-condition-neutral-comparison-accrued-spend-cap-source-gate.json",
        "sha256:5f038999b65930a0f155d5eb00a530ac06b6e359de0bdac12fff22398aaa7efe",
    ),
    "immutable-d088-portable-result-seal": (
        str(D088_PORTABLE).replace("\\", "/"),
        "sha256:2e24bfb0d98c2a7b2b0d8b5bf80c238ae048d782ce43c1cf08a2c10a6c6b5269",
    ),
    "immutable-d083-comparison-budget-freeze": (
        "reports/live-pilot/artifacts/"
        "d083-condition-neutral-comparison-budget-freeze.json",
        "sha256:e01c5f0107592e1c29c1ec8264f32bf05c979a718c353c37acb0d87fafd2cb88",
    ),
}


def _payload() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_d089_source_gate_binds_the_failed_d087_row_without_rewriting_it() -> None:
    payload = _payload()

    assert payload["schema_version"] == (
        "anyio-budget-only-readiness-probe-source-gate-v1"
    )
    assert payload["gate_id"] == (
        "d089-anyio-budget-only-readiness-probe-source-gate"
    )
    assert len(payload["predecessors"]) == len(EXPECTED_PREDECESSORS)
    predecessors = {
        predecessor["kind"]: (predecessor["path"], predecessor["sha256"])
        for predecessor in payload["predecessors"]
    }
    assert predecessors == EXPECTED_PREDECESSORS
    for predecessor in payload["predecessors"]:
        assert predecessor["modified"] is False
        assert sha256_bytes(Path(predecessor["path"]).read_bytes()) == (
            predecessor["sha256"]
        )

    failure = payload["source_failure"]
    portable = json.loads(D088_PORTABLE.read_text(encoding="utf-8"))
    rows = [
        row
        for row in portable["semantic_body"]["runs"]
        if row["run_id"] == failure["run_id"]
    ]
    assert len(rows) == 1
    row = rows[0]
    assert failure == {
        "schema_version": "d087-budget-confounded-row-v1",
        "experiment_id": portable["semantic_body"]["experiment"][
            "experiment_id"
        ],
        "task_id": row["task_id"],
        "repetition": row["repetition"],
        "schedule_order": row["order"],
        "schedule_row_id": row["schedule_row_id"],
        "run_id": row["run_id"],
        "outcome_kind": row["result"]["outcome_kind"],
        "terminal_error_code": row["result"]["terminal_error"]["code"],
        "terminal_reason_code": row["result"]["terminal_error"][
            "reason_code"
        ],
        "generation_started": row["result"]["terminal_error"][
            "generation_started"
        ],
        "evaluator_reached": row["qualification"]["evaluation_reached"],
        "trace_qualified": row["qualification"]["qualified"],
        "input_tokens": row["usage"]["input_tokens"],
        "output_tokens": row["usage"]["output_tokens"],
        "total_tokens": row["usage"]["total_tokens"],
        "model_calls": row["usage"]["model_calls"],
        "tool_calls": row["usage"]["tool_calls"],
        "wall_clock_ms": row["usage"]["wall_clock_ms"],
        "observed_list_price_cost_usd": row["usage"]["model_cost_usd"],
        "next_requested_input_tokens": row["budget_pressure"][
            "requested_input_tokens"
        ],
        "next_max_output_tokens": row["budget_pressure"][
            "max_output_tokens"
        ],
        "next_required_tokens": row["budget_pressure"]["required_tokens"],
        "remaining_tokens": row["budget_pressure"]["remaining_tokens"],
        "deficit_tokens": row["budget_pressure"]["deficit_tokens"],
        "same_prefix_minimum_tokens": (
            row["usage"]["total_tokens"]
            + row["budget_pressure"]["required_tokens"]
        ),
    }


def test_d089_source_gate_limits_the_budget_only_claim_to_runtime_knobs() -> None:
    payload = _payload()
    source = payload["probe_source"]
    suite_path = Path(source["suite_path"])
    suite = eval_runner.load_suite(suite_path)
    predecessor_suite = eval_runner.load_suite(
        Path(EXPECTED_PREDECESSORS["immutable-d087-suite"][0])
    )
    delta = payload["budget_only_delta"]
    failure = payload["source_failure"]
    harness_commit = "a" * 40
    runtime = eval_runner._experiment_runtime_contract(
        suite,
        harness_git_commit=harness_commit,
    )
    predecessor_runtime = eval_runner._experiment_runtime_contract(
        predecessor_suite,
        harness_git_commit=harness_commit,
    )
    assert runtime is not None
    assert predecessor_runtime is not None

    def comparable_runtime_tuple(
        candidate: eval_runner.ExperimentSuite,
        contract: dict,
    ) -> dict[str, object]:
        return {
            "model.provider": candidate.model,
            "model.id": candidate.model_id,
            "model.reasoning_effort": candidate.reasoning_effort,
            "model.reasoning_mode": candidate.reasoning_mode,
            "model.service_tier": candidate.service_tier,
            "model.transport_max_retries": candidate.transport_max_retries,
            "model.max_output_tokens": candidate.max_output_tokens,
            "memory.conditions": tuple(
                condition.value for condition in candidate.conditions
            ),
            "memory.max_context_tokens": candidate.memory_token_budget,
            "prompt.hash": contract["system_prompt_hash"],
            "tool.schema_version": contract["tool_schema_version"],
            "tool.schema_hash": contract["tool_schema_hash"],
            "context.policy_version": contract["context_policy_version"],
            "call_guard.policy": contract["call_guard_policy"],
            "budget.max_model_calls": candidate.budget.max_model_calls,
            "budget.max_tool_calls": candidate.budget.max_tool_calls,
            "budget.max_total_tokens": candidate.budget.max_total_tokens,
            "budget.wall_clock_timeout_seconds": (
                candidate.budget.wall_clock_timeout_seconds
            ),
        }

    previous_tuple = comparable_runtime_tuple(
        predecessor_suite,
        predecessor_runtime,
    )
    probe_tuple = comparable_runtime_tuple(suite, runtime)
    changed_fields = sorted(
        key
        for key in previous_tuple
        if previous_tuple[key] != probe_tuple[key]
    )

    assert sha256_bytes(suite_path.read_bytes()) == source["suite_sha256"]
    assert suite.experiment_id == source["experiment_id"]
    assert suite.tasks == [source["task"]]
    assert suite.budget.model_dump(mode="json") == source["budget"]
    assert delta["comparison_scope"] == "per-run-agent-model-runtime-knobs"
    assert changed_fields == ["budget.max_total_tokens"]
    assert delta["per_run_runtime_changed_fields"] == changed_fields
    assert set(delta["new_suite_identity_fields"]) == {
        "experiment_id",
        "purpose",
        "task_schedule",
        "repetitions",
        "estimated_cost_usd",
        "cost_limit_usd",
        "pricing_verified_at",
        "pilot_run_id",
        "campaign_cost_policy",
    }
    assert delta["previous_max_total_tokens"] == 1_600_000
    assert delta["probe_max_total_tokens"] == 2_000_000
    assert delta["absolute_headroom_over_same_prefix_minimum_tokens"] == 382_712
    assert delta["relative_headroom_over_same_prefix_minimum"] == (
        delta["absolute_headroom_over_same_prefix_minimum_tokens"]
        / failure["same_prefix_minimum_tokens"]
    )
    assert delta["completion_guaranteed"] is False
    for invariant in (
        "unchanged_model",
        "unchanged_prompt",
        "unchanged_tool_schema",
        "unchanged_context_policy",
        "unchanged_memory_condition",
        "unchanged_max_output_tokens",
        "unchanged_call_limit_policy",
        "unchanged_wall_clock_timeout",
    ):
        assert delta[invariant] is True


def test_d089_source_gate_separates_reserve_projection_and_authority() -> None:
    payload = _payload()
    pricing = payload["pricing"]
    readiness = payload["readiness_predicate"]
    authorization = payload["authorization_boundary"]
    claims = payload["claims_boundary"]
    verification = payload["verification"]

    assert pricing["worst_rate_reserve_usd"] == 9.1125
    assert pricing["source_cost_limit_usd"] == 10.0
    assert pricing["same_prefix_one_full_call_projection_usd"] == 1.866201
    assert pricing["projection_is_expected_cost"] is False
    assert pricing["reserve_is_invoice_prediction"] is False
    assert readiness["gate_id"] == eval_runner.ANYIO_BUDGET_READINESS_PROBE_GATE_ID
    assert readiness["budget_only_probe"] is True
    assert readiness["calibration_only"] is True
    assert readiness["task_success_required"] is False
    assert readiness["hidden_acceptance_required"] is False
    assert readiness["scrr_required"] is False
    assert authorization["clean_no_call_preflight_performed"] is False
    assert authorization["candidate_execution_hash"] is None
    assert authorization["maximum_future_approval_cap_usd"] == 10.0
    assert authorization["provider_execution_authorized"] is False
    assert claims["provider_calls_made"] == 0
    assert claims["added_model_cost_usd"] == 0.0
    assert claims["probe_executed"] is False
    assert claims["no_memory_baseline_result_established"] is False
    assert claims["comparison_denominator_eligible"] is False
    assert claims["memory_admission_unlocked"] is False
    assert claims["core_campaign_unlocked"] is False
    assert verification["status"] == "passed"
    assert verification["focused"] == {
        "command": (
            ".venv\\Scripts\\python.exe -m pytest -q -o addopts='' "
            "tests/test_d089_anyio_budget_only_probe.py "
            "tests/test_d089_source_gate_artifact.py "
            "tests/test_workflow_completion_probe.py "
            "tests/test_workflow_completion_probe_qualification.py "
            "tests/test_d085_condition_neutral_pilot_preflight.py "
            "tests/test_d085_manifest_runtime.py "
            "tests/test_d085_qualification.py "
            "tests/test_d086_runtime_hardening.py "
            "tests/test_d087_campaign_cost_policy.py "
            "tests/test_d087_execution_binding.py "
            "tests/test_d087_source_gate_artifact.py "
            "tests/test_d088_condition_neutral_campaign_seal.py "
            "tests/test_d088_runtime_hardening.py"
        ),
        "passed": 228,
        "failed": 0,
    }
    assert verification["repository_wide"] == {
        "command": ".venv\\Scripts\\python.exe -m pytest -q -o addopts=''",
        "collected": 1_529,
        "passed": 1_522,
        "skipped": 7,
        "failed": 0,
    }
    assert verification["ruff"] is True
    assert verification["compileall"] is True
    assert verification["json_parse"] is True
    assert verification["git_diff_check"] is True
    assert verification["provider_calls"] == 0
    assert verification["added_model_cost_usd"] == 0.0
