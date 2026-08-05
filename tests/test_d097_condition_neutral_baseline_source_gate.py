from __future__ import annotations

import importlib.util
import json
import shutil
from copy import deepcopy
from pathlib import Path
from types import ModuleType

import pytest
import yaml

from patchloop.util import sha256_bytes, sha256_json

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts/build_d097_condition_neutral_baseline_source_gate.py"
SUITE_PATH = ROOT / "experiments/dev-no-memory-condition-neutral-3000k-20260805-r1.yaml"
ARTIFACT_PATH = (
    ROOT / "reports/live-pilot/artifacts/d097-condition-neutral-baseline-source-gate.json"
)
ARTIFACT_BYTES = 21_029
ARTIFACT_FILE_SHA = "sha256:21ed073ad1fbe1985e7a46cabebbfdc836baa303c4434e0777152c1d2d88a777"
ARTIFACT_BODY_SHA = "sha256:05d952065136a45914e2fb3c44edcbb553732c9f33484c5412b9135062c6481b"
SUITE_FILE_SHA = "sha256:7b3c217388e86a2760694e98031b7ac974c8c450075e3433ee977e35b344abb0"
EXPECTED_TASKS = [
    "loguru-invalid-format-feedback",
    "anyio-interrupt-runner-cleanup",
    "tox-cross-section-empty-substitution",
    "hf-hub-xet-endpoint-propagation",
    "pdm-ignore-active-venv-resolution",
    "pyfakefs-makedirs-parent-traversal",
]
EXPECTED_RANDOMIZED_ROWS = [
    ("pyfakefs-makedirs-parent-traversal", 1),
    ("pyfakefs-makedirs-parent-traversal", 2),
    ("anyio-interrupt-runner-cleanup", 1),
    ("hf-hub-xet-endpoint-propagation", 1),
    ("pdm-ignore-active-venv-resolution", 1),
    ("hf-hub-xet-endpoint-propagation", 2),
    ("anyio-interrupt-runner-cleanup", 2),
    ("loguru-invalid-format-feedback", 1),
    ("loguru-invalid-format-feedback", 2),
    ("tox-cross-section-empty-substitution", 2),
    ("tox-cross-section-empty-substitution", 1),
    ("pdm-ignore-active-venv-resolution", 2),
]


def _module(path: Path = BUILDER_PATH, name: str = "d097_builder") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _artifact() -> dict:
    payload = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _suite() -> dict:
    payload = yaml.safe_load(SUITE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _copy_inputs(builder: ModuleType, target: Path) -> None:
    paths = {descriptor["path"] for descriptor in builder.SOURCE_FILES.values()}
    paths.update(descriptor["path"] for descriptor in builder.ENVIRONMENT_FILES.values())
    d096 = json.loads(
        (ROOT / builder.SOURCE_FILES["d096-resource-policy-and-admission"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    paths.update(
        row["public_path"]
        for row in d096["semantic_body"]["no_memory_baseline_admission"]["task_descriptors"]
    )
    for relative in paths:
        source = ROOT / relative
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def test_d097_artifact_is_strictly_content_addressed() -> None:
    raw = ARTIFACT_PATH.read_bytes()
    payload = json.loads(raw)
    body = payload["semantic_body"]

    assert len(raw) == ARTIFACT_BYTES
    assert sha256_bytes(raw) == ARTIFACT_FILE_SHA
    assert payload["schema_version"] == ("condition-neutral-baseline-source-gate-d097-evidence-v1")
    assert payload["semantic_body_hash"] == ARTIFACT_BODY_SHA
    assert sha256_json(body) == ARTIFACT_BODY_SHA
    assert payload["gate_id"] == f"d097_{ARTIFACT_BODY_SHA.removeprefix('sha256:')}"


def test_d097_builder_reproduces_the_exact_portable_artifact() -> None:
    builder = _module()

    rebuilt = builder.build_source_gate(repo_root=ROOT)

    assert rebuilt == _artifact()


def test_d097_exact_successor_suite_is_source_only() -> None:
    suite = _suite()

    assert sha256_bytes(SUITE_PATH.read_bytes()) == SUITE_FILE_SHA
    assert suite["schema_version"] == "experiment-v2"
    assert suite["experiment_id"] == ("dev-no-memory-condition-neutral-3000k-20260805-r1")
    assert suite["purpose"] == "memory-development-no-memory"
    assert [Path(path).parent.name for path in suite["tasks"]] == EXPECTED_TASKS
    assert suite["conditions"] == ["no_memory"]
    assert suite["repetitions"] == 2
    assert suite["seed"] == 20260723
    assert suite["pilot_run_id"] is None
    assert suite["live_cost_approved"] is False
    assert suite["approved_execution_hash"] is None


def test_d097_suite_uses_the_exact_condition_neutral_v2_tuple() -> None:
    suite = _suite()

    assert suite["model"] == "openai"
    assert suite["model_id"] == "gpt-5.4-mini-2026-03-17"
    assert suite["reasoning_effort"] == "medium"
    assert suite["reasoning_mode"] == "standard"
    assert suite["service_tier"] == "default"
    assert suite["transport_max_retries"] == 0
    assert suite["max_output_tokens"] == 25_000
    assert suite["budget"] == {
        "max_model_calls": None,
        "max_tool_calls": None,
        "max_total_tokens": 3_000_000,
        "wall_clock_timeout_seconds": 3_600,
    }
    assert suite["memory_token_budget"] == 2_000
    assert suite["dataset_manifest_hash"] == (
        "sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786"
    )


def test_d097_source_loads_as_the_registered_runtime_v2_profile() -> None:
    from patchloop.evals import runner as eval_runner

    suite = eval_runner.load_suite(SUITE_PATH)
    contract = eval_runner._experiment_runtime_contract(
        suite,
        harness_git_commit="a" * 40,
    )

    assert eval_runner._is_condition_neutral_runtime_v2_profile(suite)
    assert contract is not None
    assert contract["schema_version"] == ("condition-neutral-comparison-runtime-contract-v2")
    assert contract["comparison_resource_policy"]["semantic_body_hash"] == (
        "sha256:2e9360d92db5224d181fe8f18254da3850f324b33b24f3833633589085e3b75d"
    )
    assert contract["baseline_admission"]["admission_id"] == (
        "memory-development-no-memory-12-row-v1"
    )
    assert suite.campaign_cost_policy is not None
    assert suite.campaign_cost_policy.model_dump(mode="json") == _module().COST_POLICY


def test_d097_binds_the_exact_d096_policy_and_admission() -> None:
    body = _artifact()["semantic_body"]
    binding = body["resource_policy_binding"]
    runtime = body["runtime_binding"]

    assert binding == {
        "schema_version": "d096-resource-policy-binding-v1",
        "path": (
            "reports/live-pilot/artifacts/"
            "d096-condition-neutral-resource-policy-baseline-admission.json"
        ),
        "file_sha256": ("sha256:5c032cff1045a39d1d8d9757205a920b1cd1cfd948c7c4e3e5b526ae6744661d"),
        "semantic_body_hash": (
            "sha256:2e9360d92db5224d181fe8f18254da3850f324b33b24f3833633589085e3b75d"
        ),
        "decision_id": ("d096_2e9360d92db5224d181fe8f18254da3850f324b33b24f3833633589085e3b75d"),
        "profile_id": "gpt54mini-v2v5-condition-neutral-3000k-v1",
        "baseline_admission_id": "memory-development-no-memory-12-row-v1",
        "schedule_identity_hash": (
            "sha256:e399114a6ea516821a30104a612f7222c0caf3f88def7b5d7472d15f7cc4c27b"
        ),
        "historical_v1_contracts_modified": False,
        "d087_or_d095_retroactively_admitted": False,
    }
    assert runtime["runtime_contract_schema"] == (
        "condition-neutral-comparison-runtime-contract-v2"
    )
    assert runtime["runtime_evidence_schema"] == (
        "condition-neutral-comparison-runtime-evidence-v2"
    )
    assert runtime["campaign_cost_policy_schema"] == (
        "campaign-list-price-full-schedule-reserve-v1"
    )
    assert runtime["campaign_cost_control_schema"] == (
        "campaign-full-schedule-cost-control-evidence-v1"
    )
    assert runtime["durable_usage_evidence_schema"] == (
        "condition-neutral-full-schedule-durable-usage-evidence-v1"
    )
    assert runtime["execution_plan_binding_required"] is True
    assert runtime["run_manifest_binding_required"] is True
    assert runtime["run_started_cas_binding_required"] is True
    assert runtime["qualification_read_only_recomputation_required"] is True


def test_d097_full_schedule_cost_policy_is_non_censoring_but_not_a_guarantee() -> None:
    body = _artifact()["semantic_body"]
    policy = body["campaign_cost_policy"]

    assert policy["schema_version"] == ("campaign-list-price-full-schedule-reserve-v1")
    assert policy["scheduled_run_count"] == 12
    assert policy["per_run_worst_rate_reserve_usd"] == 13.6125
    assert policy["full_schedule_worst_rate_reserve_usd"] == 163.35
    assert policy["hard_cap_usd"] == 164.0
    assert policy["hard_cap_slack_usd"] == 0.65
    assert policy["per_run_reserve_nanos"] == 13_612_500_000
    assert policy["full_schedule_reserve_nanos"] == 163_350_000_000
    assert policy["hard_cap_nanos"] == 164_000_000_000
    assert policy["hard_cap_nanos"] - policy["full_schedule_reserve_nanos"] == (650_000_000)
    assert policy["row_reserve_count"] == 12
    assert policy["reservation_mode"] == "row-bound-full-schedule-up-front"
    assert policy["full_schedule_reserve_recorded_before_first_provider_call"] is True
    assert policy["later_row_admission_conditioned_on_earlier_row_settlement"] is False
    assert policy["per_row_atomic_sqlite_consumption_implemented"] is False
    assert policy["duplicate_paid_call_prevention_claimed"] is False
    assert (
        "one-use-paid-boundary-capability"
        not in policy["d087_journal_safety_properties_carried_forward"]
    )
    assert (
        "atomic-sqlite-reservation-consumption"
        not in policy["d087_journal_safety_properties_carried_forward"]
    )
    assert policy["cost_censoring_allowed"] is False
    assert policy["not_started_due_to_cost_allowed"] is False
    assert policy["completion_guaranteed"] is False
    assert policy["historical_d087_policy_reused"] is False
    assert policy["external_or_request_level_billing_ledger_implemented"] is False


def test_d097_cost_arithmetic_matches_the_frozen_formula() -> None:
    suite = _suite()
    policy = suite["campaign_cost_policy"]
    per_run = (
        (suite["budget"]["max_total_tokens"] + suite["max_output_tokens"])
        * suite["output_price_per_million_usd"]
        / 1_000_000
    )

    assert per_run == 13.6125
    assert per_run * 12 == pytest.approx(163.35)
    assert policy["per_run_worst_rate_reserve_usd"] == per_run
    assert policy["full_schedule_worst_rate_reserve_usd"] == pytest.approx(per_run * 12)
    assert suite["estimated_cost_usd"] == 163.35
    assert suite["cost_limit_usd"] == 164.0


def test_d097_expanded_schedule_is_exact_and_repetition_complete() -> None:
    schedule = _artifact()["semantic_body"]["successor_suite"]["expanded_schedule"]

    assert [(row["task_id"], row["repetition"]) for row in schedule] == EXPECTED_RANDOMIZED_ROWS
    assert [row["order"] for row in schedule] == list(range(1, 13))
    assert {row["condition"] for row in schedule} == {"no_memory"}
    assert {
        task_id: sorted(row["repetition"] for row in schedule if row["task_id"] == task_id)
        for task_id in EXPECTED_TASKS
    } == {task_id: [1, 2] for task_id in EXPECTED_TASKS}


def test_d097_task_and_evaluator_descriptors_are_exactly_pinned() -> None:
    descriptors = _artifact()["semantic_body"]["successor_suite"]["task_descriptors"]

    assert [row["task_id"] for row in descriptors] == EXPECTED_TASKS
    assert [row["base_order"] for row in descriptors] == list(range(1, 7))
    assert all(row["dataset_role"] == "memory-development" for row in descriptors)
    assert all(row["admission_state"] == "admitted" for row in descriptors)
    assert all(row["public_file_sha256"].startswith("sha256:") for row in descriptors)
    assert all(row["environment_file_sha256"].startswith("sha256:") for row in descriptors)
    assert all(row["evaluator_image"].endswith(f"@{row['image_digest']}") for row in descriptors)


def test_d097_pricing_is_fresh_official_source_evidence_not_invoice_claim() -> None:
    pricing = _artifact()["semantic_body"]["pricing"]

    assert pricing["verified_at"] == "2026-08-05T02:24:14Z"
    assert pricing["verification_method"] == "official-openai-docs-mcp-read-only"
    assert pricing["pricing_source_url"] == ("https://developers.openai.com/api/docs/pricing")
    assert pricing["input_price_per_million_usd"] == 0.75
    assert pricing["cached_input_price_per_million_usd"] == 0.075
    assert pricing["cache_write_input_price_per_million_usd"] is None
    assert pricing["output_price_per_million_usd"] == 4.5
    assert pricing["reserve_is_expected_invoice"] is False
    assert pricing["free_tier_or_billed_charge_claimed"] is False
    assert pricing["fresh_revalidation_required_at_clean_preflight"] is True


def test_d097_164_source_cap_is_not_live_or_project_cap_approval() -> None:
    body = _artifact()["semantic_body"]
    authorization = body["authorization_boundary"]
    claims = body["claims_boundary"]

    assert authorization["prospective_suite_cap_selected"] is True
    assert authorization["maximum_future_approval_cap_usd"] == 164.0
    assert authorization["historical_project_cap_usd"] == 150.0
    assert authorization["historical_project_cap_changed"] is False
    assert authorization["campaign_scoped_cap_exception_user_approved"] is False
    assert authorization["clean_no_call_preflight_performed"] is False
    assert authorization["candidate_execution_hash"] is None
    assert authorization["live_cost_approval_embedded"] is False
    assert authorization["provider_execution_authorized"] is False
    assert authorization["evaluator_execution_authorized"] is False
    assert authorization["blocker_code"] == (
        "NO_MEMORY_CLEAN_PREFLIGHT_AND_164_USD_APPROVAL_PENDING"
    )
    assert claims["live_execution_authorized"] is False
    assert claims["provider_calls_made"] == 0
    assert claims["evaluator_calls_made"] == 0
    assert claims["added_model_cost_usd"] == 0.0


def test_d097_source_does_not_claim_a_baseline_or_memory_result() -> None:
    claims = _artifact()["semantic_body"]["claims_boundary"]

    assert claims["d097_source_contract_created"] is True
    assert claims["no_memory_baseline_result_established"] is False
    assert claims["development_baseline_denominator_complete"] is False
    assert claims["memory_review_authorized"] is False
    assert claims["memory_admission_unlocked"] is False
    assert claims["memory_index_frozen"] is False
    assert claims["core_campaign_unlocked"] is False
    assert claims["analysis_ready"] is False
    assert claims["historical_artifacts_modified"] is False


def test_d097_completion_predicate_preserves_budget_terminal_denominator_rule() -> None:
    predicate = _artifact()["semantic_body"]["baseline_completion_predicate"]

    assert predicate["expected_rows"] == 12
    assert predicate["terminal_rows"] == 12
    assert predicate["trace_qualified_rows"] == 12
    assert predicate["cost_settled_rows"] == 12
    assert predicate["not_started_rows"] == 0
    assert predicate["campaign_cost_censored_rows"] == 0
    assert predicate["allowed_terminal_branches"] == [
        "official-evaluator-completed",
        "trace-qualified-frozen-policy-budget-terminal",
    ]
    assert predicate["terminal_branches_mutually_exclusive_and_exhaustive"] is True
    assert predicate["task_success_required"] is False
    assert predicate["budget_terminal_is_denominator_agent_failure"] is True
    assert predicate["budget_terminal_automatic_rerun_allowed"] is False
    assert predicate["budget_or_infrastructure_failure_memory_candidate_eligible"] is False


def test_d097_portable_artifact_contains_no_private_or_provider_payload() -> None:
    text = ARTIFACT_PATH.read_text(encoding="utf-8").lower()

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


@pytest.mark.parametrize(
    "role",
    tuple(
        sorted(
            {
                "d096-resource-policy-and-admission",
                "d087-cost-journal-source",
                "d094-pricing-source",
                "dataset-manifest",
                "successor-suite",
            }
        )
    ),
)
def test_d097_builder_fails_closed_on_each_source_byte_drift(
    role: str,
    tmp_path: Path,
) -> None:
    builder = _module(name=f"d097_builder_source_{role}")
    _copy_inputs(builder, tmp_path)
    target = tmp_path / builder.SOURCE_FILES[role]["path"]
    target.write_bytes(target.read_bytes() + b"\n")

    with pytest.raises(builder.D097BuildError, match=f"{role} .* drifted"):
        builder.build_source_gate(repo_root=tmp_path)


@pytest.mark.parametrize("task_id", EXPECTED_TASKS)
def test_d097_builder_fails_closed_on_each_environment_byte_drift(
    task_id: str,
    tmp_path: Path,
) -> None:
    builder = _module(name=f"d097_builder_environment_{task_id}")
    _copy_inputs(builder, tmp_path)
    target = tmp_path / builder.ENVIRONMENT_FILES[task_id]["path"]
    target.write_bytes(target.read_bytes() + b"\n")

    with pytest.raises(
        builder.D097BuildError,
        match=f"task environment {task_id} .* drifted",
    ):
        builder.build_source_gate(repo_root=tmp_path)


def test_d097_builder_rejects_semantically_rehashed_d096_tamper(
    tmp_path: Path,
) -> None:
    builder = _module(name="d097_builder_d096_semantic_tamper")
    _copy_inputs(builder, tmp_path)
    descriptor = builder.SOURCE_FILES["d096-resource-policy-and-admission"]
    target = tmp_path / descriptor["path"]
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["semantic_body"]["selected_resource_policy"]["budget"]["max_total_tokens"] = 3_000_001
    payload["semantic_body_hash"] = sha256_json(payload["semantic_body"])
    payload["decision_id"] = f"d096_{payload['semantic_body_hash'].removeprefix('sha256:')}"
    target.write_text(json.dumps(payload), encoding="utf-8", newline="\n")
    descriptor["bytes"] = len(target.read_bytes())
    descriptor["sha256"] = sha256_bytes(target.read_bytes())

    with pytest.raises(
        builder.D097BuildError,
        match="D-096 decision semantic hash drifted",
    ):
        builder.build_source_gate(repo_root=tmp_path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("live_cost_approved", True, "embeds live authority"),
        ("approved_execution_hash", "sha256:" + "f" * 64, "embeds live authority"),
        ("pilot_run_id", "run_forbidden", "embeds live authority"),
        ("cost_limit_usd", 163.35, "cost policy drifted"),
    ],
)
def test_d097_builder_rejects_suite_authority_or_cap_drift(
    field: str,
    value: object,
    message: str,
) -> None:
    builder = _module(name=f"d097_builder_suite_{field}")
    suite = _suite()
    suite[field] = value

    with pytest.raises(builder.D097BuildError, match=message):
        builder._validate_suite(suite)


def test_d097_next_gate_is_clean_no_call_preflight_only() -> None:
    next_gate = _artifact()["semantic_body"]["next_gate"]

    assert next_gate["gate"] == "clean-no-call-preflight"
    assert next_gate["clean_committed_source_required"] is True
    assert next_gate["fresh_official_pricing_revalidation_required"] is True
    assert next_gate["candidate_execution_hash_required"] is True
    assert next_gate["separate_user_approval_required"] is True
    assert next_gate["maximum_future_approval_cap_usd"] == 164.0
    assert next_gate["approval_must_acknowledge_campaign_scoped_150_cap_exception"]
    assert next_gate["provider_or_evaluator_call_allowed_during_preflight"] is False
    assert next_gate["automatic_execution_authorized"] is False


def test_d097_historical_source_bindings_remain_exact() -> None:
    bindings = {row["role"]: row for row in _artifact()["semantic_body"]["source_bindings"]}

    for role in (
        "d096-resource-policy-and-admission",
        "d087-cost-journal-source",
        "d094-pricing-source",
        "dataset-manifest",
    ):
        descriptor = bindings[role]
        raw = (ROOT / descriptor["path"]).read_bytes()
        assert len(raw) == descriptor["bytes"]
        assert sha256_bytes(raw) == descriptor["sha256"]


def test_d097_source_builder_has_no_provider_or_evaluator_dependency() -> None:
    source = BUILDER_PATH.read_text(encoding="utf-8")

    assert "OpenAI(" not in source
    assert "responses.create" not in source
    assert "EvaluationEngine" not in source
    assert "DockerSandbox" not in source
    assert "subprocess" not in source
    assert "requests." not in source
    assert "httpx." not in source


def test_d097_cost_policy_rejects_semantic_drift_even_without_file_checks() -> None:
    builder = _module(name="d097_builder_cost_semantic_tamper")
    suite = deepcopy(_suite())
    suite["campaign_cost_policy"]["cost_censoring_allowed"] = True

    with pytest.raises(builder.D097BuildError, match="cost policy drifted"):
        builder._validate_suite(suite)
