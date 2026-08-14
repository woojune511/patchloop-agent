"""Source for authenticating future held-out A/C persisted row evidence.

This module grants no execution or task access by itself.  Its runtime entrypoint
requires an already-qualified task/evaluator binding, invokes the existing
evaluator-v2 receipt validator and read-only trace recomputation, then binds the
exact persisted result, qualification and usage-evidence bytes.  No campaign is
materialized in the current repository.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import EvaluatorV2EvaluationReceipt, RunResult, TaskPackage
from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_completion import (
    HeldoutACDurableUsage,
    heldout_ac_schedule_row_id,
)
from patchloop.evals.heldout_ac_contracts import HeldoutACFrozenModel, HeldoutACSuite
from patchloop.evals.heldout_ac_task_evaluator import HeldoutACTaskEvaluatorBinding
from patchloop.state import StateStore
from patchloop.util import canonical_json, safe_relative_path, sha256_bytes, sha256_json
from patchloop.verifier.receipt import (
    EvaluatorV2QualificationAuthority,
    EvaluatorV2ReceiptValidation,
    validate_persisted_evaluator_v2_evaluation_receipt,
)

USAGE_SCHEMA_VERSION = "heldout-ac-durable-usage-evidence-v1"
ROW_SCHEMA_VERSION = "heldout-ac-authenticated-persisted-row-v1"
_SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"


class HeldoutACPersistedUsageEvidence(HeldoutACFrozenModel):
    schema_version: Literal[USAGE_SCHEMA_VERSION] = USAGE_SCHEMA_VERSION
    run_id: str = Field(pattern=r"^run_[A-Za-z0-9_-]+$")
    schedule_row_id: str = Field(pattern=_SHA256_PATTERN)
    pricing_binding_hash: str = Field(pattern=_SHA256_PATTERN)
    price_nanos_per_token: dict[
        Literal["uncached_input", "cached_input", "cache_write_input", "output"], int
    ]
    usage: HeldoutACDurableUsage
    token_derived_cost_nanos: int = Field(ge=0)
    qualification_hash: str = Field(pattern=_SHA256_PATTERN)
    source_evidence_hash: str = Field(pattern=_SHA256_PATTERN)
    persisted_result_file_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_v2_receipt_file_hash: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_usage_evidence(self) -> HeldoutACPersistedUsageEvidence:
        expected_keys = {
            "uncached_input",
            "cached_input",
            "cache_write_input",
            "output",
        }
        if set(self.price_nanos_per_token) != expected_keys or any(
            type(value) is not int or value < 0 for value in self.price_nanos_per_token.values()
        ):
            raise ValueError("held-out price table must contain exact nonnegative integers")
        usage = self.usage
        uncached = usage.input_tokens - usage.cached_input_tokens - usage.cache_write_input_tokens
        prices = self.price_nanos_per_token
        expected_cost = (
            uncached * prices["uncached_input"]
            + usage.cached_input_tokens * prices["cached_input"]
            + usage.cache_write_input_tokens * prices["cache_write_input"]
            + usage.output_tokens * prices["output"]
        )
        if self.token_derived_cost_nanos != expected_cost:
            raise ValueError("held-out usage evidence cost does not match its counters")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("held-out usage evidence content hash mismatch")
        return self


class HeldoutACAuthenticatedPersistedRow(HeldoutACFrozenModel):
    schema_version: Literal[ROW_SCHEMA_VERSION] = ROW_SCHEMA_VERSION
    persisted_evidence_authenticated: Literal[True] = True
    order: int = Field(ge=1, le=48)
    wave: int = Field(ge=1, le=4)
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    role: Literal["core-same-repo", "core-cross-repo"]
    condition: Literal["no_memory", "structured"]
    repetition: Literal[1, 2]
    run_id: str = Field(pattern=r"^run_[A-Za-z0-9_-]+$")
    schedule_row_id: str = Field(pattern=_SHA256_PATTERN)
    execution_hash: str = Field(pattern=_SHA256_PATTERN)
    task_evaluator_binding_hash: str = Field(pattern=_SHA256_PATTERN)
    persisted_result_file_hash: str = Field(pattern=_SHA256_PATTERN)
    persisted_result_semantic_hash: str = Field(pattern=_SHA256_PATTERN)
    qualification_file_hash: str = Field(pattern=_SHA256_PATTERN)
    qualification_hash: str = Field(pattern=_SHA256_PATTERN)
    source_evidence_hash: str = Field(pattern=_SHA256_PATTERN)
    usage_evidence_file_hash: str = Field(pattern=_SHA256_PATTERN)
    usage_evidence_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_v2_receipt_hash: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    evaluator_v2_receipt_file_hash: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    result: RunResult
    usage_evidence: HeldoutACPersistedUsageEvidence
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_row(self) -> HeldoutACAuthenticatedPersistedRow:
        if self.result.run_id != self.run_id:
            raise ValueError("authenticated row result identity differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("authenticated persisted row content hash mismatch")
        return self


def _qualification_hash(payload: Mapping[str, Any]) -> str:
    recorded = payload.get("qualification_hash")
    if not isinstance(recorded, str):
        raise ContractError("held-out trace qualification has no content hash")
    expected = sha256_json(
        {key: value for key, value in payload.items() if key != "qualification_hash"}
    )
    if recorded != expected:
        raise ContractError("held-out trace qualification content hash mismatch")
    return recorded


def _usage_from_result(result: RunResult) -> dict[str, Any]:
    raw = result.usage.model_dump(mode="json")
    return {
        key: raw[key]
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


def _canonical_qualification_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(payload), indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _canonical_usage_evidence_bytes(payload: HeldoutACPersistedUsageEvidence) -> bytes:
    return json.dumps(
        payload.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False
    ).encode("utf-8")


def project_authenticated_heldout_ac_persisted_row(
    *,
    suite: HeldoutACSuite,
    execution_hash: str,
    expected_pricing_binding_hash: str,
    order: int,
    task_evaluator_binding: HeldoutACTaskEvaluatorBinding,
    persisted_result_bytes: bytes,
    qualification_bytes: bytes,
    recomputed_qualification: Mapping[str, Any],
    usage_evidence_bytes: bytes,
    receipt_validation: EvaluatorV2ReceiptValidation | None,
    receipt_bytes: bytes | None,
) -> HeldoutACAuthenticatedPersistedRow:
    """Cross-bind exact bytes after trusted receipt and trace recomputation."""

    if type(order) is not int or not 1 <= order <= len(suite.schedule):
        raise ContractError("held-out persisted row order is invalid")
    scheduled = suite.schedule[order - 1]
    expected_row_id = heldout_ac_schedule_row_id(
        suite=suite,
        execution_hash=execution_hash,
        order=order,
    )
    try:
        result = RunResult.model_validate_json(persisted_result_bytes)
        qualification = json.loads(qualification_bytes)
        usage_evidence = HeldoutACPersistedUsageEvidence.model_validate_json(usage_evidence_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise ContractError("held-out persisted row files are invalid") from exc
    if not isinstance(qualification, dict):
        raise ContractError("held-out trace qualification is not an object")
    if persisted_result_bytes != result.model_dump_json(indent=2).encode("utf-8"):
        raise ContractError("held-out persisted result bytes are not canonical")
    if qualification_bytes != _canonical_qualification_bytes(qualification):
        raise ContractError("held-out trace qualification bytes are not canonical")
    if usage_evidence_bytes != _canonical_usage_evidence_bytes(usage_evidence):
        raise ContractError("held-out usage evidence bytes are not canonical")
    if canonical_json(qualification) != canonical_json(dict(recomputed_qualification)):
        raise ContractError("held-out trace qualification differs from read-only recomputation")
    qualification_hash = _qualification_hash(qualification)
    experiment = receipt_validation.manifest.experiment if receipt_validation else None
    binding = result.evaluator_contract
    expected_task = task_evaluator_binding.task
    expected_usage = HeldoutACDurableUsage(**_usage_from_result(result))
    qualification_identity = (
        qualification.get("schema_version") == "trace-qualification-v2"
        and qualification.get("qualified") is True
        and qualification.get("run_id") == result.run_id
        and qualification.get("task_id") == scheduled.task_id
        and qualification.get("dataset_role") == scheduled.role
        and qualification.get("memory_condition") == scheduled.condition
        and qualification.get("suite_hash") == suite.content_hash
        and qualification.get("execution_hash") == execution_hash
        and qualification.get("schedule_row_id") == expected_row_id
        and isinstance(qualification.get("source_evidence_hash"), str)
    )
    common_valid = (
        expected_task.task_id == scheduled.task_id
        and result.run_id == usage_evidence.run_id
        and usage_evidence.schedule_row_id == expected_row_id
        and usage_evidence.qualification_hash == qualification_hash
        and usage_evidence.source_evidence_hash == qualification.get("source_evidence_hash")
        and usage_evidence.persisted_result_file_hash == sha256_bytes(persisted_result_bytes)
        and usage_evidence.pricing_binding_hash == expected_pricing_binding_hash
        and usage_evidence.usage == expected_usage
        and Decimal(str(result.usage.model_cost_usd))
        == Decimal(usage_evidence.token_derived_cost_nanos) / Decimal(1_000_000_000)
        and binding is not None
        and binding == task_evaluator_binding.evaluator_contract
        and qualification_identity
    )
    receipt_hash: str | None = None
    receipt_file_hash: str | None = None
    if result.evaluation_status == "completed":
        if receipt_validation is None or receipt_bytes is None:
            raise ContractError("evaluator-completed held-out row lacks receipt validation")
        receipt = receipt_validation.receipt
        try:
            persisted_receipt = EvaluatorV2EvaluationReceipt.model_validate_json(receipt_bytes)
        except ValidationError as exc:
            raise ContractError("held-out evaluator receipt bytes are invalid") from exc
        receipt_hash = receipt.content_hash
        receipt_file_hash = sha256_bytes(receipt_bytes)
        common_valid = common_valid and (
            persisted_receipt == receipt
            and receipt_validation.result == result
            and receipt.run_id == result.run_id
            and receipt.suite_hash == suite.content_hash
            and receipt.result_file_hash == sha256_bytes(persisted_result_bytes)
            and receipt_file_hash == usage_evidence.evaluator_v2_receipt_file_hash
            and experiment is not None
            and experiment.experiment_id == suite.suite_id
            and experiment.suite_hash == suite.content_hash
            and experiment.execution_hash == execution_hash
            and experiment.schedule_order == order
            and experiment.schedule_row_id == expected_row_id
        )
    elif not (
        receipt_validation is None
        and receipt_bytes is None
        and usage_evidence.evaluator_v2_receipt_file_hash is None
        and result.evaluation_status == "not_run"
        and result.agent_submission_status == "failed"
        and result.outcome_kind.value == "agent_failure"
        and result.terminal_error == {"code": "AGENT_SUBMISSION_FAILED", "phase": "agent"}
    ):
        raise ContractError("held-out agent-terminal persisted evidence is invalid")
    if not common_valid:
        raise ContractError("held-out persisted row cross-binding differs")
    body = {
        "schema_version": ROW_SCHEMA_VERSION,
        "persisted_evidence_authenticated": True,
        "order": order,
        "wave": scheduled.wave,
        "task_id": scheduled.task_id,
        "role": scheduled.role,
        "condition": scheduled.condition,
        "repetition": scheduled.repetition,
        "run_id": result.run_id,
        "schedule_row_id": expected_row_id,
        "execution_hash": execution_hash,
        "task_evaluator_binding_hash": task_evaluator_binding.content_hash,
        "persisted_result_file_hash": sha256_bytes(persisted_result_bytes),
        "persisted_result_semantic_hash": sha256_json(result.model_dump(mode="json")),
        "qualification_file_hash": sha256_bytes(qualification_bytes),
        "qualification_hash": qualification_hash,
        "source_evidence_hash": qualification["source_evidence_hash"],
        "usage_evidence_file_hash": sha256_bytes(usage_evidence_bytes),
        "usage_evidence_hash": usage_evidence.content_hash,
        "evaluator_v2_receipt_hash": receipt_hash,
        "evaluator_v2_receipt_file_hash": receipt_file_hash,
        "result": result.model_dump(mode="json"),
        "usage_evidence": usage_evidence.model_dump(mode="json"),
    }
    return HeldoutACAuthenticatedPersistedRow(**body, content_hash=sha256_json(body))


def authenticate_heldout_ac_persisted_row(
    *,
    suite: HeldoutACSuite,
    execution_hash: str,
    expected_pricing_binding_hash: str,
    order: int,
    task_evaluator_binding: HeldoutACTaskEvaluatorBinding,
    run_root: str | Path,
    task_dir: str | Path,
    dataset_manifest_path: str | Path,
    evaluator_authority: EvaluatorV2QualificationAuthority,
    usage_evidence_relative_path: str,
) -> HeldoutACAuthenticatedPersistedRow:
    """Invoke durable receipt/trace validators, then project one authenticated row.

    Calling this function is a future evaluator-side operation and is not
    authorized by importing or source-qualifying this module.
    """

    from patchloop.evals.qualification import load_trace_qualification, qualify_run
    from patchloop.task_loader import load_task_package

    root = Path(run_root).resolve()
    relative = safe_relative_path(
        usage_evidence_relative_path, field_name="held-out usage evidence path"
    )
    usage_path = (root / relative).resolve()
    if not usage_path.is_relative_to(root) or usage_path.is_symlink():
        raise ContractError("held-out usage evidence path escapes the runtime root")
    package: TaskPackage = load_task_package(task_dir)
    state = StateStore(root / "state.sqlite3")
    artifacts = ArtifactStore(root / "artifacts")
    scheduled = suite.schedule[order - 1]
    usage_bytes = usage_path.read_bytes()
    try:
        persisted_usage = HeldoutACPersistedUsageEvidence.model_validate_json(usage_bytes)
    except ValidationError as exc:
        raise ContractError("held-out usage evidence is invalid") from exc
    run_id = persisted_usage.run_id
    qualification = load_trace_qualification(run_id, root=root)
    recomputed = qualify_run(
        run_id,
        task_dir=task_dir,
        dataset_manifest_path=dataset_manifest_path,
        root=root,
        persist=False,
        evaluator_v2_authority=evaluator_authority,
    )
    run_dir = artifacts.root / "runs" / run_id
    persisted_result_bytes = (run_dir / "result.json").read_bytes()
    qualification_bytes = (root / "qualifications" / f"{run_id}.json").read_bytes()
    result = RunResult.model_validate_json(persisted_result_bytes)
    receipt_validation: EvaluatorV2ReceiptValidation | None = None
    receipt_bytes: bytes | None = None
    if result.evaluation_status == "completed":
        receipt_validation = validate_persisted_evaluator_v2_evaluation_receipt(
            state_store=state,
            artifact_store=artifacts,
            run_id=run_id,
            package=package,
            authority=evaluator_authority,
            expected_result=result,
        )
        receipt_bytes = (run_dir / "evaluation-receipt.json").read_bytes()
    if qualification != recomputed or scheduled.task_id != package.public.task_id:
        raise ContractError("held-out persisted validation task or qualification differs")
    return project_authenticated_heldout_ac_persisted_row(
        suite=suite,
        execution_hash=execution_hash,
        expected_pricing_binding_hash=expected_pricing_binding_hash,
        order=order,
        task_evaluator_binding=task_evaluator_binding,
        persisted_result_bytes=persisted_result_bytes,
        qualification_bytes=qualification_bytes,
        recomputed_qualification=recomputed,
        usage_evidence_bytes=usage_bytes,
        receipt_validation=receipt_validation,
        receipt_bytes=receipt_bytes,
    )


__all__ = [
    "ROW_SCHEMA_VERSION",
    "USAGE_SCHEMA_VERSION",
    "HeldoutACAuthenticatedPersistedRow",
    "HeldoutACPersistedUsageEvidence",
    "authenticate_heldout_ac_persisted_row",
    "project_authenticated_heldout_ac_persisted_row",
]
