from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from patchloop.contracts import RunResult, TaskPackage, VerdictState, task_package_spec_hashes
from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_completion import heldout_ac_schedule_row_id
from patchloop.evals.heldout_ac_persisted_adapter import (
    HeldoutACPersistedUsageEvidence,
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
from tests.test_evaluator_v2_contracts import _v2_chain

ROOT = Path(__file__).resolve().parents[1]
SUITE_PATH = Path("experiments/heldout-ac-suite-20260814-v1.yaml")
EXECUTION_HASH = "sha256:" + "e" * 64
SOURCE_HASH = "sha256:" + "a" * 64
PRICING_HASH = "sha256:" + "c" * 64


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


def _row_files():
    suite, binding, result = _binding_and_agent_result()
    row_id = heldout_ac_schedule_row_id(suite=suite, execution_hash=EXECUTION_HASH, order=1)
    result_bytes = result.model_dump_json(indent=2).encode("utf-8")
    qualification_body = {
        "schema_version": "trace-qualification-v2",
        "qualified": True,
        "run_id": result.run_id,
        "task_id": suite.schedule[0].task_id,
        "dataset_role": suite.schedule[0].role,
        "memory_condition": suite.schedule[0].condition,
        "suite_hash": suite.content_hash,
        "execution_hash": EXECUTION_HASH,
        "schedule_row_id": row_id,
        "source_evidence_hash": "sha256:" + "d" * 64,
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


def test_authenticated_agent_terminal_binds_exact_persisted_bytes() -> None:
    suite, binding, result_bytes, qualification, qualification_bytes, usage_bytes = _row_files()
    row = project_authenticated_heldout_ac_persisted_row(
        suite=suite,
        execution_hash=EXECUTION_HASH,
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
    assert row.result.evaluation_status == "not_run"
    assert row.persisted_result_file_hash == sha256_bytes(result_bytes)
    assert row.qualification_file_hash == sha256_bytes(qualification_bytes)


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
