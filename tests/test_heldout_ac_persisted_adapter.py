from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from patchloop.contracts import (
    EventType,
    RunEvent,
    RunResult,
    TaskPackage,
    VerdictState,
    task_package_spec_hashes,
)
from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_completion import (
    HeldoutACDurableUsage,
    heldout_ac_schedule_row_id,
)
from patchloop.evals.heldout_ac_execution import (
    build_heldout_ac_run_manifest,
    materialize_heldout_ac_runtime_task_authority,
)
from patchloop.evals.heldout_ac_persisted_adapter import (
    HeldoutACAuthenticatedPersistedEvidence,
    HeldoutACPersistedUsageEvidence,
    authenticate_heldout_ac_persisted_evidence,
    has_heldout_ac_runtime_authentication_capability,
    project_authenticated_heldout_ac_persisted_evidence,
    project_authenticated_heldout_ac_persisted_row,
)
from patchloop.evals.heldout_ac_suite import load_heldout_ac_suite
from patchloop.evals.heldout_ac_task_evaluator import (
    HeldoutACTaskEvaluatorBindingPlan,
    HeldoutACTaskMetadataBinding,
    load_heldout_ac_task_evaluator_plan,
    materialize_heldout_ac_task_evaluator_binding,
)
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, sha256_json
from patchloop.verifier.runtime_evidence import evaluator_v2_runtime_tuple_hash
from tests.test_evaluator_v2_contracts import _v2_chain
from tests.test_heldout_ac_execution import _candidate as _lower_budget_execution_candidate

ROOT = Path(__file__).resolve().parents[1]
SUITE_PATH = Path("experiments/heldout-ac-suite-20260814-v1.yaml")
EXECUTION_HASH = "sha256:" + "e" * 64
SOURCE_HASH = "sha256:" + "a" * 64
PRICING_HASH = "sha256:" + "c" * 64
CAMPAIGN_COST_CONTROL_HASH = "sha256:" + "9" * 64
PER_RUN_RESERVE_NANOS = 1_200_000_000
CANDIDATE_MAX_CUMULATIVE_INPUT_TOKENS = 1_000_000
CANDIDATE_MAX_CUMULATIVE_OUTPUT_TOKENS = 100_000
CANDIDATE_MAX_TOTAL_TOKENS = 1_100_000

BASE_CHECK_IDS = (
    "task_identity",
    "heldout_ac_runtime_contract",
    "bounded_call_guard_contract",
    "contiguous_events",
    "worker_claim_provenance",
    "single_terminal_event",
    "required_trace_evidence",
    "submission_lifecycle",
    "fixed_memory_delivery_integrity",
    "live_openai_provider",
    "frozen_model_contract",
    "fault_free",
    "frozen_campaign_provenance",
    "approved_execution_plan",
    "heldout_ac_full_schedule_cost_contract",
    "sandbox_provenance",
    "agent_visible_artifacts",
    "rejected_patch_retry_context",
    "public_private_boundary",
    "investigation_evidence",
    "investigation_lifecycle",
    "prompt_token_integrity",
    "usage_reconciliation",
    "persisted_result",
    "pilot_tool_loop",
    "terminal_result_integrity",
    "failure_record_linkage",
)


def _synthetic_package(task_id: str) -> TaskPackage:
    base = load_task_package(ROOT / "tasks/dev-validation/moto-query-scanned-count")
    public_payload = base.public.model_dump(mode="json")
    private_payload = base.private.model_dump(mode="json")
    public_payload["task_id"] = task_id
    private_payload["task_id"] = task_id
    public = type(base.public).model_validate(public_payload)
    private = type(base.private).model_validate(private_payload)
    public_hash, private_hash = task_package_spec_hashes(public, private)
    return TaskPackage(
        public=public,
        private=private,
        environment=base.environment,
        root=f"C:/synthetic/{task_id}",
        public_spec_hash=public_hash,
        private_spec_hash=private_hash,
    )


def _runtime_tuple_hash_for_qualification(
    suite: object,
    qualification: dict[str, object],
) -> str:
    runtime = suite.runtime  # type: ignore[attr-defined]
    budget = qualification["budget"]
    assert isinstance(budget, dict)
    return evaluator_v2_runtime_tuple_hash(
        provider=str(qualification["model_provider"]),
        model_id=str(qualification["model_id"]),
        reasoning_effort=str(qualification["reasoning_effort"]),
        reasoning_mode=str(qualification["reasoning_mode"]),
        service_tier=str(qualification["service_tier"]),
        transport_max_retries=qualification["transport_max_retries"],  # type: ignore[arg-type]
        max_output_tokens=qualification["max_output_tokens"],  # type: ignore[arg-type]
        max_total_tokens=budget["max_total_tokens"],  # type: ignore[arg-type]
        wall_clock_timeout_seconds=budget["wall_clock_timeout_seconds"],  # type: ignore[arg-type]
        tool_schema_version=str(qualification["tool_schema_version"]),
        context_policy_version=str(qualification["context_policy_version"]),
        memory_policy_version=runtime.memory_policy_version,
        sandbox_backend=runtime.sandbox_backend,
        token_budget_schema_version=budget["token_budget_schema_version"],  # type: ignore[arg-type]
        max_model_calls=budget["max_model_calls"],  # type: ignore[arg-type]
        max_tool_calls=budget["max_tool_calls"],  # type: ignore[arg-type]
        max_cumulative_input_tokens=budget["max_cumulative_input_tokens"],  # type: ignore[arg-type]
        max_cumulative_output_tokens=budget["max_cumulative_output_tokens"],  # type: ignore[arg-type]
    )


def _binding_and_agent_result():
    suite = load_heldout_ac_suite(SUITE_PATH, repository=ROOT)
    sealed = load_heldout_ac_task_evaluator_plan(repository=ROOT)
    scheduled = suite.schedule[0]
    package = _synthetic_package(scheduled.task_id)
    assert package.environment is not None
    expected = HeldoutACTaskMetadataBinding(
        task_id=scheduled.task_id,
        task_version=1,
        role=scheduled.role,
        task_path=f"tasks/same-repo-heldout/{scheduled.task_id}",
        public_spec_hash=package.public_spec_hash,
        private_spec_hash=package.private_spec_hash,
        evaluator_image=package.environment.evaluator_image,
        evaluator_image_digest=package.environment.image_digest,
    )
    plan_body = sealed.model_dump(mode="json", exclude={"content_hash"})
    selected_index = next(
        index
        for index, item in enumerate(plan_body["tasks"])
        if item["task_id"] == scheduled.task_id
    )
    plan_body["tasks"][selected_index] = expected.model_dump(mode="json")
    plan = HeldoutACTaskEvaluatorBindingPlan(
        **{key: value for key, value in plan_body.items() if key != "tasks"},
        tasks=tuple(
            HeldoutACTaskMetadataBinding.model_validate(item) for item in plan_body["tasks"]
        ),
        content_hash=sha256_json(plan_body),
    )
    with patch(
        "patchloop.evals.heldout_ac_task_evaluator.SEALED_PLAN_CONTENT_HASH",
        plan.content_hash,
    ):
        binding = materialize_heldout_ac_task_evaluator_binding(
            plan=plan,
            expected_task=expected,
            package=package,
            evaluator_source_hash=SOURCE_HASH,
            runtime_secret_markers=(b"synthetic-run-secret",),
        )
    template = deepcopy(_v2_chain(VerdictState.PASS).result.model_dump(mode="json"))
    template.update(
        {
            "run_id": "run_heldout_adapter_01",
            "agent_submission_status": "failed",
            "evaluation_status": "not_run",
            "scope_compliant_success": False,
            "official": False,
            "verdicts": {
                "hidden_tests": "not_run",
                "regression_tests": "not_run",
                "scope_policy": "not_run",
                "safety_policy": "not_run",
            },
            "usage": {
                "input_tokens": 120,
                "cached_input_tokens": 20,
                "cache_write_input_tokens": 0,
                "output_tokens": 10,
                "reasoning_output_tokens": 5,
                "model_cost_usd": 0.0001215,
                "model_calls": 2,
                "input_token_count_calls": 2,
                "tool_calls": 3,
                "wall_clock_ms": 4_000,
            },
            "submitted_patch_artifact_id": None,
            "submitted_patch_artifact": None,
            "verifier_results": [],
            "outcome_kind": "agent_failure",
            "terminal_error": {"code": "AGENT_SUBMISSION_FAILED", "phase": "agent"},
            "safety_evidence_bundle": None,
            "safety_evidence_bundle_hash": None,
            "safety_evidence": [],
            "evaluator_contract": binding.evaluator_contract.model_dump(mode="json"),
        }
    )
    result = RunResult.model_validate(template)
    return suite, binding, result


def _row_files(
    *,
    thin_qualification: bool = False,
    campaign_cost_control_hash: str = CAMPAIGN_COST_CONTROL_HASH,
    execution_hash: str = EXECUTION_HASH,
    token_limits: tuple[int, int, int] = (
        CANDIDATE_MAX_CUMULATIVE_INPUT_TOKENS,
        CANDIDATE_MAX_CUMULATIVE_OUTPUT_TOKENS,
        CANDIDATE_MAX_TOTAL_TOKENS,
    ),
):
    suite, binding, result = _binding_and_agent_result()
    input_limit, output_limit, total_limit = token_limits
    row_id = heldout_ac_schedule_row_id(suite=suite, execution_hash=execution_hash, order=1)
    result_bytes = result.model_dump_json(indent=2).encode("utf-8")
    if thin_qualification:
        qualification_body = {
            "schema_version": "trace-qualification-v2",
            "qualified": True,
            "run_id": result.run_id,
            "task_id": suite.schedule[0].task_id,
            "dataset_role": suite.schedule[0].role,
            "memory_condition": suite.schedule[0].condition,
            "suite_hash": suite.content_hash,
            "execution_hash": execution_hash,
            "schedule_row_id": row_id,
            "source_evidence_hash": "sha256:" + "d" * 64,
        }
    else:
        runtime = suite.runtime
        qualification_body = {
            "schema_version": "trace-qualification-v2",
            "run_id": result.run_id,
            "qualified": True,
            "trace_integrity_passed": True,
            "leakage_scan_passed": True,
            "evaluation_reached": False,
            "outcome_kind": "agent_failure",
            "purpose": "core",
            "experiment_id": suite.suite_id,
            "dataset_role": suite.schedule[0].role,
            "dataset_manifest_hash": "sha256:" + "1" * 64,
            "suite_hash": suite.content_hash,
            "execution_hash": execution_hash,
            "schedule_row_id": row_id,
            "model_provider": runtime.model,
            "memory_condition": suite.schedule[0].condition,
            "fault_type": "none",
            "memory_candidate_eligible": False,
            "failure_record_id": None,
            "failure_record_hash": None,
            "source_evidence_hash": "sha256:" + "d" * 64,
            "checks": [
                {
                    "check_id": check_id,
                    "passed": True,
                    "details": (
                        {
                            "campaign_cost_control_hash": campaign_cost_control_hash,
                            "manifest_cost_control_hash": campaign_cost_control_hash,
                            "schedule_row_count": 48,
                            "live_resume_supported": False,
                        }
                        if check_id == "heldout_ac_full_schedule_cost_contract"
                        else {}
                    ),
                }
                for check_id in BASE_CHECK_IDS
            ],
            "evaluator_version": "v2",
            "evaluator_v2_receipt_hash": None,
            "evaluator_v2_receipt_file_hash": None,
            "evaluator_v2_source_hash": None,
            "evaluator_v2_source_qualification_hash": None,
            "evaluator_v2_runtime_authenticated": False,
            "evaluator_v2_completion_eligible": False,
            "task_id": suite.schedule[0].task_id,
            "model_id": runtime.model_id,
            "reasoning_effort": runtime.reasoning_effort,
            "reasoning_mode": runtime.reasoning_mode,
            "service_tier": runtime.service_tier,
            "max_output_tokens": runtime.max_output_tokens,
            "budget": {
                "max_model_calls": runtime.max_model_calls,
                "max_tool_calls": runtime.max_tool_calls,
                "max_total_tokens": total_limit,
                "wall_clock_timeout_seconds": runtime.wall_clock_timeout_seconds,
                "token_budget_schema_version": runtime.token_budget_schema_version,
                "max_cumulative_input_tokens": input_limit,
                "max_cumulative_output_tokens": output_limit,
            },
            "harness_git_commit": "1" * 40,
            "tool_schema_version": runtime.tool_schema_version,
            "context_policy_version": runtime.context_policy_version,
            "runtime_contract_content_hash": "sha256:" + "2" * 64,
            "transport_max_retries": runtime.transport_max_retries,
        }
    qualification = {
        **qualification_body,
        "qualification_hash": sha256_json(qualification_body),
    }
    qualification_bytes = json.dumps(
        qualification, indent=2, sort_keys=True, ensure_ascii=False
    ).encode("utf-8")
    prices = {
        "uncached_input": 750,
        "cached_input": 75,
        "cache_write_input": 750,
        "output": 4_500,
    }
    usage_body = {
        "schema_version": "heldout-ac-durable-usage-evidence-v1",
        "run_id": result.run_id,
        "schedule_row_id": row_id,
        "pricing_binding_hash": PRICING_HASH,
        "price_nanos_per_token": prices,
        "usage": {
            key: result.usage.model_dump(mode="json")[key]
            for key in (
                "input_tokens",
                "cached_input_tokens",
                "cache_write_input_tokens",
                "output_tokens",
                "reasoning_output_tokens",
                "model_calls",
                "input_token_count_calls",
                "tool_calls",
                "wall_clock_ms",
            )
        },
        "token_derived_cost_nanos": 100 * 750 + 20 * 75 + 10 * 4_500,
        "qualification_hash": qualification["qualification_hash"],
        "source_evidence_hash": qualification["source_evidence_hash"],
        "persisted_result_file_hash": sha256_bytes(result_bytes),
        "evaluator_v2_receipt_file_hash": None,
    }
    usage = {**usage_body, "content_hash": sha256_json(usage_body)}
    usage_bytes = json.dumps(
        HeldoutACPersistedUsageEvidence.model_validate(usage).model_dump(mode="json"),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return suite, binding, result_bytes, qualification, qualification_bytes, usage_bytes


def _with_usage_updates(
    result_bytes: bytes,
    usage_bytes: bytes,
    **updates: int,
) -> tuple[bytes, bytes]:
    result_payload = json.loads(result_bytes)
    result_payload["usage"].update(updates)
    durable_usage = HeldoutACDurableUsage(
        **{
            key: result_payload["usage"][key]
            for key in (
                "input_tokens",
                "cached_input_tokens",
                "cache_write_input_tokens",
                "output_tokens",
                "reasoning_output_tokens",
                "model_calls",
                "input_token_count_calls",
                "tool_calls",
                "wall_clock_ms",
            )
        }
    )
    result_payload["usage"]["model_cost_usd"] = (
        durable_usage.token_derived_cost_nanos() / 1_000_000_000
    )
    result = RunResult.model_validate(result_payload)
    changed_result_bytes = result.model_dump_json(indent=2).encode("utf-8")

    usage_payload = json.loads(usage_bytes)
    usage_payload["usage"] = durable_usage.model_dump(mode="json")
    usage_payload["token_derived_cost_nanos"] = durable_usage.token_derived_cost_nanos()
    usage_payload["persisted_result_file_hash"] = sha256_bytes(changed_result_bytes)
    usage_payload["content_hash"] = sha256_json(
        {key: value for key, value in usage_payload.items() if key != "content_hash"}
    )
    changed_usage_bytes = json.dumps(
        HeldoutACPersistedUsageEvidence.model_validate(usage_payload).model_dump(mode="json"),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return changed_result_bytes, changed_usage_bytes


def test_authenticated_agent_terminal_binds_exact_persisted_bytes() -> None:
    suite, binding, result_bytes, qualification, qualification_bytes, usage_bytes = _row_files()
    row = project_authenticated_heldout_ac_persisted_row(
        suite=suite,
        execution_hash=EXECUTION_HASH,
        expected_runtime_tuple_hash=_runtime_tuple_hash_for_qualification(suite, qualification),
        expected_campaign_cost_control_hash=CAMPAIGN_COST_CONTROL_HASH,
        expected_per_run_reserve_nanos=PER_RUN_RESERVE_NANOS,
        expected_pricing_binding_hash=PRICING_HASH,
        order=1,
        task_evaluator_binding=binding,
        persisted_result_bytes=result_bytes,
        qualification_bytes=qualification_bytes,
        recomputed_qualification=qualification,
        usage_evidence_bytes=usage_bytes,
        receipt_validation=None,
        receipt_bytes=None,
    )

    assert row.persisted_evidence_authenticated is True
    assert row.runtime_tuple_hash == _runtime_tuple_hash_for_qualification(suite, qualification)
    assert row.campaign_cost_control_hash == CAMPAIGN_COST_CONTROL_HASH
    assert row.result.evaluation_status == "not_run"
    assert row.persisted_result_file_hash == sha256_bytes(result_bytes)
    assert row.qualification_file_hash == sha256_bytes(qualification_bytes)


def test_actual_lower_budget_candidate_authority_authenticates_manifest_budget() -> None:
    candidate = _lower_budget_execution_candidate()
    candidate_row = candidate.schedule[0]
    package = load_task_package(ROOT / candidate_row.task_path)
    authority = materialize_heldout_ac_runtime_task_authority(
        candidate=candidate,
        task_id=candidate_row.task_id,
        package=package,
        api_key="offline-test-runtime-secret",
        repository=ROOT,
    )
    manifest = build_heldout_ac_run_manifest(
        candidate=candidate,
        row_order=1,
        run_id="run_heldout_adapter_candidate_binding",
        created_at=datetime(2026, 8, 15, tzinfo=UTC),
        authority=authority,
    )
    assert manifest.experiment is not None
    suite, binding, result_bytes, qualification, qualification_bytes, usage_bytes = _row_files(
        campaign_cost_control_hash=manifest.experiment.campaign_cost_control_hash,
        execution_hash=candidate.execution_hash,
        token_limits=(
            manifest.budget.max_cumulative_input_tokens,
            manifest.budget.max_cumulative_output_tokens,
            manifest.budget.max_total_tokens,
        ),
    )
    assert manifest.budget.max_cumulative_input_tokens is not None
    assert manifest.budget.max_cumulative_output_tokens is not None

    row = project_authenticated_heldout_ac_persisted_row(
        suite=suite,
        execution_hash=candidate.execution_hash,
        expected_runtime_tuple_hash=authority.qualification_authority.runtime_tuple_hash,
        expected_campaign_cost_control_hash=candidate.campaign_cost_control.content_hash,
        expected_per_run_reserve_nanos=candidate.campaign_cost_control.per_run_reserve_nanos,
        expected_pricing_binding_hash=PRICING_HASH,
        order=1,
        task_evaluator_binding=binding,
        persisted_result_bytes=result_bytes,
        qualification_bytes=qualification_bytes,
        recomputed_qualification=qualification,
        usage_evidence_bytes=usage_bytes,
        receipt_validation=None,
        receipt_bytes=None,
    )

    assert row.runtime_tuple_hash == candidate.runtime_tuple_hash
    assert row.campaign_cost_control_hash == candidate.campaign_cost_control.content_hash


def test_candidate_budget_rejects_the_legacy_suite_runtime_authority() -> None:
    suite, binding, result_bytes, qualification, qualification_bytes, usage_bytes = _row_files()
    (
        _legacy_suite,
        _legacy_binding,
        _legacy_result_bytes,
        legacy_qualification,
        _legacy_qualification_bytes,
        _legacy_usage_bytes,
    ) = _row_files(token_limits=(4_000_000, 500_000, 4_500_000))

    with pytest.raises(ContractError, match="runtime identity differs"):
        project_authenticated_heldout_ac_persisted_row(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_runtime_tuple_hash=_runtime_tuple_hash_for_qualification(
                suite, legacy_qualification
            ),
            expected_campaign_cost_control_hash=CAMPAIGN_COST_CONTROL_HASH,
            expected_per_run_reserve_nanos=PER_RUN_RESERVE_NANOS,
            expected_pricing_binding_hash=PRICING_HASH,
            order=1,
            task_evaluator_binding=binding,
            persisted_result_bytes=result_bytes,
            qualification_bytes=qualification_bytes,
            recomputed_qualification=qualification,
            usage_evidence_bytes=usage_bytes,
            receipt_validation=None,
            receipt_bytes=None,
        )


def test_candidate_cost_control_rejects_another_campaign_authority() -> None:
    suite, binding, result_bytes, qualification, qualification_bytes, usage_bytes = _row_files()

    with pytest.raises(ContractError, match="runtime identity differs"):
        project_authenticated_heldout_ac_persisted_row(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_runtime_tuple_hash=_runtime_tuple_hash_for_qualification(suite, qualification),
            expected_campaign_cost_control_hash="sha256:" + "8" * 64,
            expected_per_run_reserve_nanos=PER_RUN_RESERVE_NANOS,
            expected_pricing_binding_hash=PRICING_HASH,
            order=1,
            task_evaluator_binding=binding,
            persisted_result_bytes=result_bytes,
            qualification_bytes=qualification_bytes,
            recomputed_qualification=qualification,
            usage_evidence_bytes=usage_bytes,
            receipt_validation=None,
            receipt_bytes=None,
        )


@pytest.mark.parametrize(
    ("usage_updates", "per_run_reserve_nanos"),
    [
        ({"input_tokens": 1_000_001}, PER_RUN_RESERVE_NANOS),
        ({"output_tokens": 100_001}, PER_RUN_RESERVE_NANOS),
        (
            {"model_calls": 241, "input_token_count_calls": 241},
            PER_RUN_RESERVE_NANOS,
        ),
        ({"tool_calls": 401}, PER_RUN_RESERVE_NANOS),
        ({"wall_clock_ms": 3_600_001}, PER_RUN_RESERVE_NANOS),
        ({}, 1),
    ],
)
def test_authenticated_row_rejects_usage_outside_candidate_bound_budget(
    usage_updates: dict[str, int],
    per_run_reserve_nanos: int,
) -> None:
    suite, binding, result_bytes, qualification, qualification_bytes, usage_bytes = _row_files()
    result_bytes, usage_bytes = _with_usage_updates(
        result_bytes,
        usage_bytes,
        **usage_updates,
    )

    with pytest.raises(ContractError, match="cross-binding"):
        project_authenticated_heldout_ac_persisted_row(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_runtime_tuple_hash=_runtime_tuple_hash_for_qualification(suite, qualification),
            expected_campaign_cost_control_hash=CAMPAIGN_COST_CONTROL_HASH,
            expected_per_run_reserve_nanos=per_run_reserve_nanos,
            expected_pricing_binding_hash=PRICING_HASH,
            order=1,
            task_evaluator_binding=binding,
            persisted_result_bytes=result_bytes,
            qualification_bytes=qualification_bytes,
            recomputed_qualification=qualification,
            usage_evidence_bytes=usage_bytes,
            receipt_validation=None,
            receipt_bytes=None,
        )


def test_legacy_suite_budget_requires_its_exact_runtime_authority() -> None:
    suite, binding, result_bytes, qualification, qualification_bytes, usage_bytes = _row_files(
        token_limits=(4_000_000, 500_000, 4_500_000)
    )
    row = project_authenticated_heldout_ac_persisted_row(
        suite=suite,
        execution_hash=EXECUTION_HASH,
        expected_runtime_tuple_hash=_runtime_tuple_hash_for_qualification(suite, qualification),
        expected_campaign_cost_control_hash=CAMPAIGN_COST_CONTROL_HASH,
        expected_per_run_reserve_nanos=PER_RUN_RESERVE_NANOS,
        expected_pricing_binding_hash=PRICING_HASH,
        order=1,
        task_evaluator_binding=binding,
        persisted_result_bytes=result_bytes,
        qualification_bytes=qualification_bytes,
        recomputed_qualification=qualification,
        usage_evidence_bytes=usage_bytes,
        receipt_validation=None,
        receipt_bytes=None,
    )

    assert row.persisted_evidence_authenticated is True


def test_pure_projection_is_unofficial_until_runtime_authenticator_issues_capability() -> None:
    suite, binding, result_bytes, qualification, qualification_bytes, usage_bytes = _row_files()
    evidence = project_authenticated_heldout_ac_persisted_evidence(
        suite=suite,
        execution_hash=EXECUTION_HASH,
        expected_runtime_tuple_hash=_runtime_tuple_hash_for_qualification(suite, qualification),
        expected_campaign_cost_control_hash=CAMPAIGN_COST_CONTROL_HASH,
        expected_per_run_reserve_nanos=PER_RUN_RESERVE_NANOS,
        expected_pricing_binding_hash=PRICING_HASH,
        order=1,
        task_evaluator_binding=binding,
        persisted_result_bytes=result_bytes,
        qualification_bytes=qualification_bytes,
        recomputed_qualification=qualification,
        usage_evidence_bytes=usage_bytes,
        receipt_validation=None,
        receipt_bytes=None,
        agent_terminal_type="submission-failure",
        agent_terminal_event=RunEvent(
            event_id="evt_agent_terminal_projection",
            run_id=RunResult.model_validate_json(result_bytes).run_id,
            sequence=10,
            type=EventType.RUN_FAILED,
            timestamp=datetime(2026, 8, 14, tzinfo=UTC),
            actor="runner",
            payload={"error_code": None},
        ),
    )
    assert type(evidence) is HeldoutACAuthenticatedPersistedEvidence
    assert evidence.official is False
    assert evidence.analysis_eligible is False
    assert evidence.runtime_tuple_hash == evidence.row.runtime_tuple_hash
    assert evidence.campaign_cost_control_hash == evidence.row.campaign_cost_control_hash
    assert has_heldout_ac_runtime_authentication_capability(evidence) is False

    with patch(
        "patchloop.evals.heldout_ac_persisted_adapter."
        "_load_and_project_heldout_ac_persisted_evidence",
        return_value=evidence,
    ):
        issued = authenticate_heldout_ac_persisted_evidence(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_campaign_cost_control_hash=CAMPAIGN_COST_CONTROL_HASH,
            expected_per_run_reserve_nanos=PER_RUN_RESERVE_NANOS,
            expected_pricing_binding_hash=PRICING_HASH,
            order=1,
            task_evaluator_binding=binding,
            run_root=ROOT,
            task_dir=ROOT,
            dataset_manifest_path=ROOT,
            evaluator_authority=object(),  # type: ignore[arg-type]
            usage_evidence_relative_path="unused.json",
        )

    assert issued is evidence
    assert has_heldout_ac_runtime_authentication_capability(issued) is True
    drifted_terminal = issued.model_dump(mode="json")
    drifted_terminal["terminal_type"] = "model-call-limit"
    drifted_terminal["content_hash"] = sha256_json(
        {key: value for key, value in drifted_terminal.items() if key != "content_hash"}
    )
    with pytest.raises(ValueError, match="terminal event differs"):
        HeldoutACAuthenticatedPersistedEvidence.model_validate(drifted_terminal)
    replayed = HeldoutACAuthenticatedPersistedEvidence.model_validate(
        issued.model_dump(mode="json")
    )
    assert has_heldout_ac_runtime_authentication_capability(replayed) is False
    assert has_heldout_ac_runtime_authentication_capability(issued.model_copy()) is False
    assert has_heldout_ac_runtime_authentication_capability(issued.model_copy(deep=True)) is False

    legacy = issued.model_dump(mode="json")
    legacy["schema_version"] = "heldout-ac-authenticated-persisted-evidence-v4"
    legacy.pop("runtime_tuple_hash")
    legacy.pop("campaign_cost_control_hash")
    legacy_row = legacy["row"]
    legacy_row["schema_version"] = "heldout-ac-authenticated-persisted-row-v1"
    legacy_row.pop("runtime_tuple_hash")
    legacy_row.pop("campaign_cost_control_hash")
    legacy_row["content_hash"] = sha256_json(
        {key: value for key, value in legacy_row.items() if key != "content_hash"}
    )
    legacy["content_hash"] = sha256_json(
        {key: value for key, value in legacy.items() if key != "content_hash"}
    )
    historical = HeldoutACAuthenticatedPersistedEvidence.model_validate(legacy)
    assert historical.runtime_tuple_hash is None
    assert historical.row.campaign_cost_control_hash is None
    assert has_heldout_ac_runtime_authentication_capability(historical) is False


def test_persisted_adapter_rejects_thin_qualification_even_when_recomputation_matches() -> None:
    suite, binding, result_bytes, qualification, qualification_bytes, usage_bytes = _row_files(
        thin_qualification=True
    )

    with pytest.raises(ContractError, match="fields are incomplete"):
        project_authenticated_heldout_ac_persisted_row(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_runtime_tuple_hash="sha256:" + "0" * 64,
            expected_campaign_cost_control_hash=CAMPAIGN_COST_CONTROL_HASH,
            expected_per_run_reserve_nanos=PER_RUN_RESERVE_NANOS,
            expected_pricing_binding_hash=PRICING_HASH,
            order=1,
            task_evaluator_binding=binding,
            persisted_result_bytes=result_bytes,
            qualification_bytes=qualification_bytes,
            recomputed_qualification=qualification,
            usage_evidence_bytes=usage_bytes,
            receipt_validation=None,
            receipt_bytes=None,
        )


@pytest.mark.parametrize("target", ["result", "qualification", "usage"])
def test_persisted_adapter_rejects_any_rehashed_or_byte_drift(target: str) -> None:
    suite, binding, result_bytes, qualification, qualification_bytes, usage_bytes = _row_files()
    if target == "result":
        result_bytes += b"\n"
    elif target == "qualification":
        changed = json.loads(qualification_bytes)
        changed["qualified"] = False
        qualification_bytes = json.dumps(
            changed, indent=2, sort_keys=True, ensure_ascii=False
        ).encode("utf-8")
    else:
        usage = json.loads(usage_bytes)
        usage["persisted_result_file_hash"] = "sha256:" + "0" * 64
        usage["content_hash"] = sha256_json(
            {key: value for key, value in usage.items() if key != "content_hash"}
        )
        usage_bytes = json.dumps(usage, indent=2, sort_keys=True).encode("utf-8")

    with pytest.raises(ContractError):
        project_authenticated_heldout_ac_persisted_row(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_runtime_tuple_hash=_runtime_tuple_hash_for_qualification(suite, qualification),
            expected_campaign_cost_control_hash=CAMPAIGN_COST_CONTROL_HASH,
            expected_per_run_reserve_nanos=PER_RUN_RESERVE_NANOS,
            expected_pricing_binding_hash=PRICING_HASH,
            order=1,
            task_evaluator_binding=binding,
            persisted_result_bytes=result_bytes,
            qualification_bytes=qualification_bytes,
            recomputed_qualification=qualification,
            usage_evidence_bytes=usage_bytes,
            receipt_validation=None,
            receipt_bytes=None,
        )


def test_evaluator_completed_row_cannot_be_authenticated_without_receipt_validation() -> None:
    suite, binding, result_bytes, qualification, qualification_bytes, usage_bytes = _row_files()
    payload = json.loads(result_bytes)
    payload["evaluation_status"] = "completed"
    payload["agent_submission_status"] = "completed"
    payload["outcome_kind"] = "resolved"
    payload["terminal_error"] = None
    with pytest.raises((ContractError, ValueError)):
        project_authenticated_heldout_ac_persisted_row(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_runtime_tuple_hash=_runtime_tuple_hash_for_qualification(suite, qualification),
            expected_campaign_cost_control_hash=CAMPAIGN_COST_CONTROL_HASH,
            expected_per_run_reserve_nanos=PER_RUN_RESERVE_NANOS,
            expected_pricing_binding_hash=PRICING_HASH,
            order=1,
            task_evaluator_binding=binding,
            persisted_result_bytes=json.dumps(payload).encode("utf-8"),
            qualification_bytes=qualification_bytes,
            recomputed_qualification=qualification,
            usage_evidence_bytes=usage_bytes,
            receipt_validation=None,
            receipt_bytes=None,
        )


def test_persisted_adapter_rejects_wrong_pricing_binding() -> None:
    suite, binding, result_bytes, qualification, qualification_bytes, usage_bytes = _row_files()

    with pytest.raises(ContractError, match="cross-binding"):
        project_authenticated_heldout_ac_persisted_row(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_runtime_tuple_hash=_runtime_tuple_hash_for_qualification(suite, qualification),
            expected_campaign_cost_control_hash=CAMPAIGN_COST_CONTROL_HASH,
            expected_per_run_reserve_nanos=PER_RUN_RESERVE_NANOS,
            expected_pricing_binding_hash="sha256:" + "f" * 64,
            order=1,
            task_evaluator_binding=binding,
            persisted_result_bytes=result_bytes,
            qualification_bytes=qualification_bytes,
            recomputed_qualification=qualification,
            usage_evidence_bytes=usage_bytes,
            receipt_validation=None,
            receipt_bytes=None,
        )


def test_persisted_adapter_rejects_result_cost_drift_after_rehash() -> None:
    suite, binding, result_bytes, qualification, qualification_bytes, usage_bytes = _row_files()
    result_payload = json.loads(result_bytes)
    result_payload["usage"]["model_cost_usd"] = 0.0001216
    result_bytes = (
        RunResult.model_validate(result_payload).model_dump_json(indent=2).encode("utf-8")
    )
    usage_payload = json.loads(usage_bytes)
    usage_payload["persisted_result_file_hash"] = sha256_bytes(result_bytes)
    usage_payload["content_hash"] = sha256_json(
        {key: value for key, value in usage_payload.items() if key != "content_hash"}
    )
    usage_bytes = json.dumps(
        HeldoutACPersistedUsageEvidence.model_validate(usage_payload).model_dump(mode="json"),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")

    with pytest.raises(ContractError, match="cross-binding"):
        project_authenticated_heldout_ac_persisted_row(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_runtime_tuple_hash=_runtime_tuple_hash_for_qualification(suite, qualification),
            expected_campaign_cost_control_hash=CAMPAIGN_COST_CONTROL_HASH,
            expected_per_run_reserve_nanos=PER_RUN_RESERVE_NANOS,
            expected_pricing_binding_hash=PRICING_HASH,
            order=1,
            task_evaluator_binding=binding,
            persisted_result_bytes=result_bytes,
            qualification_bytes=qualification_bytes,
            recomputed_qualification=qualification,
            usage_evidence_bytes=usage_bytes,
            receipt_validation=None,
            receipt_bytes=None,
        )


def _post_submission_evaluator_confound_files():
    suite, binding, result_bytes, qualification, _, usage_bytes = _row_files()
    result_payload = json.loads(result_bytes)
    completed = _v2_chain(VerdictState.PASS).result
    result_payload.update(
        {
            "agent_submission_status": "completed",
            "evaluation_status": "not_run",
            "submitted_patch_artifact_id": completed.submitted_patch_artifact_id,
            "submitted_patch_artifact": completed.submitted_patch_artifact.model_dump(mode="json"),
            "outcome_kind": "infrastructure_error",
            "terminal_error": {
                "code": "EVALUATOR_INFRASTRUCTURE_ERROR",
                "phase": "evaluator",
            },
        }
    )
    result = RunResult.model_validate(result_payload)
    result_bytes = result.model_dump_json(indent=2).encode("utf-8")

    qualification = deepcopy(qualification)
    qualification["outcome_kind"] = "infrastructure_error"
    qualification["qualification_hash"] = sha256_json(
        {key: value for key, value in qualification.items() if key != "qualification_hash"}
    )
    qualification_bytes = json.dumps(
        qualification, indent=2, sort_keys=True, ensure_ascii=False
    ).encode("utf-8")

    usage_payload = json.loads(usage_bytes)
    usage_payload["persisted_result_file_hash"] = sha256_bytes(result_bytes)
    usage_payload["qualification_hash"] = qualification["qualification_hash"]
    usage_payload["content_hash"] = sha256_json(
        {key: value for key, value in usage_payload.items() if key != "content_hash"}
    )
    usage_bytes = json.dumps(
        HeldoutACPersistedUsageEvidence.model_validate(usage_payload).model_dump(mode="json"),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    failure_event = RunEvent(
        event_id="evt_heldout_adapter_confound",
        run_id=result.run_id,
        sequence=10,
        type=EventType.RUN_FAILED,
        timestamp=datetime(2026, 8, 14, tzinfo=UTC),
        actor="runner",
        payload={
            "error_code": "EVALUATOR_CONTROL_CONTRACT_COLLISION",
            "message": "redacted by projection",
        },
    )
    return (
        suite,
        binding,
        result_bytes,
        qualification,
        qualification_bytes,
        usage_bytes,
        failure_event,
    )


def test_post_submission_evaluator_failure_is_typed_authenticated_confound() -> None:
    (
        suite,
        binding,
        result_bytes,
        qualification,
        qualification_bytes,
        usage_bytes,
        failure_event,
    ) = _post_submission_evaluator_confound_files()

    evidence = project_authenticated_heldout_ac_persisted_evidence(
        suite=suite,
        execution_hash=EXECUTION_HASH,
        expected_runtime_tuple_hash=_runtime_tuple_hash_for_qualification(suite, qualification),
        expected_campaign_cost_control_hash=CAMPAIGN_COST_CONTROL_HASH,
        expected_per_run_reserve_nanos=PER_RUN_RESERVE_NANOS,
        expected_pricing_binding_hash=PRICING_HASH,
        order=1,
        task_evaluator_binding=binding,
        persisted_result_bytes=result_bytes,
        qualification_bytes=qualification_bytes,
        recomputed_qualification=qualification,
        usage_evidence_bytes=usage_bytes,
        receipt_validation=None,
        receipt_bytes=None,
        evaluator_failure_event=failure_event,
    )

    assert evidence.analysis_eligible is False
    assert evidence.evaluator_failure_code == "EVALUATOR_CONTROL_CONTRACT_COLLISION"
    assert "message" not in evidence.model_dump_json()
    assert evidence.qualification.source_schema_version == "trace-qualification-v2"
    assert evidence.qualification.schema_version != evidence.qualification.source_schema_version

    changed_event = failure_event.model_dump(mode="json")
    changed_event["payload"]["message"] = "different redacted diagnostic"
    same_safe_projection = project_authenticated_heldout_ac_persisted_evidence(
        suite=suite,
        execution_hash=EXECUTION_HASH,
        expected_runtime_tuple_hash=_runtime_tuple_hash_for_qualification(suite, qualification),
        expected_campaign_cost_control_hash=CAMPAIGN_COST_CONTROL_HASH,
        expected_per_run_reserve_nanos=PER_RUN_RESERVE_NANOS,
        expected_pricing_binding_hash=PRICING_HASH,
        order=1,
        task_evaluator_binding=binding,
        persisted_result_bytes=result_bytes,
        qualification_bytes=qualification_bytes,
        recomputed_qualification=qualification,
        usage_evidence_bytes=usage_bytes,
        receipt_validation=None,
        receipt_bytes=None,
        evaluator_failure_event=RunEvent.model_validate(changed_event),
    )
    assert same_safe_projection.evaluator_failure_event_hash == (
        evidence.evaluator_failure_event_hash
    )
    assert same_safe_projection.content_hash == evidence.content_hash


def test_evaluator_confound_rejects_usage_outside_candidate_bound_budget() -> None:
    (
        suite,
        binding,
        result_bytes,
        qualification,
        qualification_bytes,
        usage_bytes,
        failure_event,
    ) = _post_submission_evaluator_confound_files()
    result_bytes, usage_bytes = _with_usage_updates(
        result_bytes,
        usage_bytes,
        input_tokens=CANDIDATE_MAX_CUMULATIVE_INPUT_TOKENS + 1,
    )

    with pytest.raises(ContractError, match="confound cross-binding"):
        project_authenticated_heldout_ac_persisted_evidence(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_runtime_tuple_hash=_runtime_tuple_hash_for_qualification(suite, qualification),
            expected_campaign_cost_control_hash=CAMPAIGN_COST_CONTROL_HASH,
            expected_per_run_reserve_nanos=PER_RUN_RESERVE_NANOS,
            expected_pricing_binding_hash=PRICING_HASH,
            order=1,
            task_evaluator_binding=binding,
            persisted_result_bytes=result_bytes,
            qualification_bytes=qualification_bytes,
            recomputed_qualification=qualification,
            usage_evidence_bytes=usage_bytes,
            receipt_validation=None,
            receipt_bytes=None,
            evaluator_failure_event=failure_event,
        )


@pytest.mark.parametrize(
    "failure_code",
    [None, "EVALUATOR_INFRASTRUCTURE_ERROR", "UNTRUSTED_PRIVATE_MARKER_HIT"],
)
def test_evaluator_confound_requires_exact_persisted_stable_code(
    failure_code: str | None,
) -> None:
    (
        suite,
        binding,
        result_bytes,
        qualification,
        qualification_bytes,
        usage_bytes,
        failure_event,
    ) = _post_submission_evaluator_confound_files()
    if failure_code is None:
        event = None
    else:
        event_payload = failure_event.model_dump(mode="json")
        event_payload["payload"]["error_code"] = failure_code
        event = RunEvent.model_validate(event_payload)

    if failure_code == "UNTRUSTED_PRIVATE_MARKER_HIT":
        evidence = project_authenticated_heldout_ac_persisted_evidence(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_runtime_tuple_hash=_runtime_tuple_hash_for_qualification(suite, qualification),
            expected_campaign_cost_control_hash=CAMPAIGN_COST_CONTROL_HASH,
            expected_per_run_reserve_nanos=PER_RUN_RESERVE_NANOS,
            expected_pricing_binding_hash=PRICING_HASH,
            order=1,
            task_evaluator_binding=binding,
            persisted_result_bytes=result_bytes,
            qualification_bytes=qualification_bytes,
            recomputed_qualification=qualification,
            usage_evidence_bytes=usage_bytes,
            receipt_validation=None,
            receipt_bytes=None,
            evaluator_failure_event=event,
        )
        assert evidence.evaluator_failure_code == "UNTRUSTED_PRIVATE_MARKER_HIT"
        return

    with pytest.raises(ContractError, match="typed event|not trusted"):
        project_authenticated_heldout_ac_persisted_evidence(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_runtime_tuple_hash=_runtime_tuple_hash_for_qualification(suite, qualification),
            expected_campaign_cost_control_hash=CAMPAIGN_COST_CONTROL_HASH,
            expected_per_run_reserve_nanos=PER_RUN_RESERVE_NANOS,
            expected_pricing_binding_hash=PRICING_HASH,
            order=1,
            task_evaluator_binding=binding,
            persisted_result_bytes=result_bytes,
            qualification_bytes=qualification_bytes,
            recomputed_qualification=qualification,
            usage_evidence_bytes=usage_bytes,
            receipt_validation=None,
            receipt_bytes=None,
            evaluator_failure_event=event,
        )


def test_evaluator_confound_requires_runner_event_provenance() -> None:
    (
        suite,
        binding,
        result_bytes,
        qualification,
        qualification_bytes,
        usage_bytes,
        failure_event,
    ) = _post_submission_evaluator_confound_files()
    changed = failure_event.model_dump(mode="json")
    changed["actor"] = "evaluator"

    with pytest.raises(ContractError, match="not trusted"):
        project_authenticated_heldout_ac_persisted_evidence(
            suite=suite,
            execution_hash=EXECUTION_HASH,
            expected_runtime_tuple_hash=_runtime_tuple_hash_for_qualification(suite, qualification),
            expected_campaign_cost_control_hash=CAMPAIGN_COST_CONTROL_HASH,
            expected_per_run_reserve_nanos=PER_RUN_RESERVE_NANOS,
            expected_pricing_binding_hash=PRICING_HASH,
            order=1,
            task_evaluator_binding=binding,
            persisted_result_bytes=result_bytes,
            qualification_bytes=qualification_bytes,
            recomputed_qualification=qualification,
            usage_evidence_bytes=usage_bytes,
            receipt_validation=None,
            receipt_bytes=None,
            evaluator_failure_event=RunEvent.model_validate(changed),
        )
