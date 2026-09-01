"""Fail-closed admission for continuing after one settled Rapid row.

The consumed Rapid runners halted the complete batch after every
``infrastructure_error``.  That is safe, but it also discards later independent
rows when the runner has already returned a complete, atomically persisted
terminal result and released all row-local resources.  This module defines the
narrow successor boundary without changing any consumed runner:

* only a returned, typed ``RECOVERY_ERROR`` before evaluation is eligible;
* state, artifacts, cost, capability use, worker ownership and workspace
  isolation must all reconcile;
* every missing or conflicting observation halts the batch; and
* the decision itself grants no provider, Docker or next-row authority.

The projection intentionally excludes exception messages, model reasoning,
private task material, evaluator internals and source bodies.
"""

from __future__ import annotations

import json
import os
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.runner import (
    AgentRunner,
    BatchExecutionAuthorization,
    RowExecutionAuthorization,
    batch_execution_authorization_receipt,
    issue_row_execution_authorization,
    row_execution_authorization_receipt,
)
from patchloop.contracts import EventType, RunManifest, RunOutcomeKind, RunResult, RunStatus
from patchloop.errors import ContractError, RecoveryError, RunOwnershipConflict
from patchloop.evals.rapid_public_development import _usage_cost_nanos
from patchloop.util import sha256_bytes, sha256_json

RAPID_ROW_CONTINUATION_EVIDENCE_SCHEMA = "rapid-row-settlement-evidence-v1"
RAPID_ROW_CONTINUATION_DECISION_SCHEMA = "rapid-row-continuation-decision-v1"
RAPID_ROW_CONTINUATION_POLICY_VERSION = "settled-row-local-infrastructure-continuation-v1"

_ELIGIBLE_TERMINAL_CODE = "RECOVERY_ERROR"


class RapidRowSettlementChecks(BaseModel):
    """Closed set of independently auditable continuation preconditions."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    runner_returned_without_exception: bool
    result_schema_valid: bool
    projection_matches_result: bool
    terminal_state_atomic: bool
    typed_recovery_terminal: bool
    artifact_triad_matches: bool
    evaluation_receipt_absent: bool
    worker_lock_released: bool
    workspace_isolated: bool
    row_capability_consumed: bool
    provider_dispatch_started: bool
    batch_manifest_slots_match: bool
    batch_next_order_ready: bool
    cost_settled_under_cap: bool


class RapidRowSettlementEvidence(BaseModel):
    """Public, bounded evidence for one post-row continuation decision."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["rapid-row-settlement-evidence-v1"]
    policy_version: Literal["settled-row-local-infrastructure-continuation-v1"]
    authority_kind: str | None
    execution_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    plan_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    schedule_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    cost_control_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    current_schedule_order: int = Field(ge=1)
    next_schedule_order: int = Field(ge=1)
    current_schedule_row_id: str = Field(min_length=1)
    next_schedule_row_id: str = Field(min_length=1)
    current_run_id: str = Field(pattern=r"^run_[a-zA-Z0-9_-]+$")
    next_run_id: str = Field(pattern=r"^run_[a-zA-Z0-9_-]+$")
    current_manifest_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    next_manifest_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    batch_receipt_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    row_receipt_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    outcome_kind: str | None
    evaluation_status: str | None
    agent_submission_status: str | None
    terminal_error_code: str | None
    terminal_event_sequence: int | None = Field(default=None, ge=1)
    terminal_event_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    state_manifest_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    state_result_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    returned_result_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    manifest_file_sha256: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    result_file_sha256: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    provenance_file_sha256: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    model_cost_nanos: int = Field(ge=0)
    row_reserve_nanos: int = Field(gt=0)
    accrued_cost_nanos_before: int = Field(ge=0)
    accrued_cost_nanos_after: int = Field(ge=0)
    hard_cap_nanos: int = Field(gt=0)
    checks: RapidRowSettlementChecks
    public_projection_only: Literal[True]
    raw_trace_mutated: Literal[False]
    next_row_capability_issued: Literal[False]
    provider_calls_authorized: Literal[False]
    docker_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_content_hash(self) -> Self:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("Rapid row settlement evidence hash differs")
        return self


class RapidRowContinuationDecision(BaseModel):
    """Deterministic policy result; it is not an execution capability."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["rapid-row-continuation-decision-v1"]
    policy_version: Literal["settled-row-local-infrastructure-continuation-v1"]
    evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    decision: Literal["continue", "halt"]
    continuation_eligible: bool
    reason_codes: tuple[str, ...] = Field(min_length=1)
    next_schedule_order: int = Field(ge=1)
    next_schedule_row_id: str = Field(min_length=1)
    next_run_id: str = Field(pattern=r"^run_[a-zA-Z0-9_-]+$")
    fail_closed: Literal[True]
    next_row_capability_issued: Literal[False]
    provider_calls_authorized: Literal[False]
    docker_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        if self.continuation_eligible is not (self.decision == "continue"):
            raise ValueError("Rapid row continuation decision flag differs")
        expected_reason = "ELIGIBLE_SETTLED_ROW_LOCAL_INFRASTRUCTURE"
        if self.decision == "continue" and self.reason_codes != (expected_reason,):
            raise ValueError("Rapid row continuation eligibility reason differs")
        if self.decision == "halt" and expected_reason in self.reason_codes:
            raise ValueError("Rapid row halt carries an eligibility reason")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("Rapid row continuation decision hash differs")
        return self


def _json_hash_projection(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _json_hash_projection(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_hash_projection(item) for item in value]
    return value


def _hashed(model_type: type[BaseModel], body: dict[str, Any]) -> Any:
    return model_type.model_validate(
        {**body, "content_hash": sha256_json(_json_hash_projection(body))}
    )


def build_rapid_row_settlement_evidence(
    **body: Any,
) -> RapidRowSettlementEvidence:
    """Seal an already bounded evidence body for pure tests and qualification."""

    fixed = {
        "schema_version": RAPID_ROW_CONTINUATION_EVIDENCE_SCHEMA,
        "policy_version": RAPID_ROW_CONTINUATION_POLICY_VERSION,
        **body,
        "public_projection_only": True,
        "raw_trace_mutated": False,
        "next_row_capability_issued": False,
        "provider_calls_authorized": False,
        "docker_calls_authorized": False,
    }
    return _hashed(RapidRowSettlementEvidence, fixed)


def classify_rapid_row_continuation(
    evidence: RapidRowSettlementEvidence | dict[str, Any],
) -> RapidRowContinuationDecision:
    """Permit continuation only for the complete typed allowlist intersection."""

    try:
        observed = RapidRowSettlementEvidence.model_validate(evidence)
    except ValueError as exc:
        raise ContractError("Rapid row settlement evidence is invalid") from exc

    reasons: list[str] = []
    fixed_requirements = (
        (observed.authority_kind == "live", "AUTHORITY_NOT_LIVE"),
        (observed.plan_hash is not None, "PLAN_HASH_MISSING"),
        (observed.schedule_hash is not None, "SCHEDULE_HASH_MISSING"),
        (observed.cost_control_hash is not None, "COST_CONTROL_HASH_MISSING"),
        (observed.batch_receipt_hash is not None, "BATCH_RECEIPT_HASH_MISSING"),
        (observed.row_receipt_hash is not None, "ROW_RECEIPT_HASH_MISSING"),
        (observed.terminal_event_sequence is not None, "TERMINAL_EVENT_SEQUENCE_MISSING"),
        (observed.terminal_event_hash is not None, "TERMINAL_EVENT_HASH_MISSING"),
        (observed.state_manifest_hash is not None, "STATE_MANIFEST_HASH_MISSING"),
        (observed.state_result_hash is not None, "STATE_RESULT_HASH_MISSING"),
        (observed.returned_result_hash is not None, "RETURNED_RESULT_HASH_MISSING"),
        (observed.manifest_file_sha256 is not None, "MANIFEST_FILE_HASH_MISSING"),
        (observed.result_file_sha256 is not None, "RESULT_FILE_HASH_MISSING"),
        (observed.provenance_file_sha256 is not None, "PROVENANCE_FILE_HASH_MISSING"),
        (
            observed.next_schedule_order == observed.current_schedule_order + 1,
            "NEXT_ORDER_NOT_CONTIGUOUS",
        ),
        (
            observed.current_schedule_row_id != observed.next_schedule_row_id,
            "NEXT_ROW_ID_NOT_DISTINCT",
        ),
        (observed.current_run_id != observed.next_run_id, "NEXT_RUN_ID_NOT_DISTINCT"),
        (
            observed.current_manifest_hash != observed.next_manifest_hash,
            "NEXT_MANIFEST_HASH_NOT_DISTINCT",
        ),
        (
            observed.state_manifest_hash == observed.current_manifest_hash,
            "STATE_MANIFEST_HASH_DIFFERS",
        ),
        (
            observed.state_result_hash == observed.returned_result_hash,
            "STATE_RESULT_HASH_DIFFERS",
        ),
        (
            observed.outcome_kind == RunOutcomeKind.INFRASTRUCTURE_ERROR.value,
            "OUTCOME_NOT_INFRASTRUCTURE",
        ),
        (observed.evaluation_status == "not_run", "EVALUATION_STATUS_NOT_NOT_RUN"),
        (
            observed.agent_submission_status == "failed",
            "SUBMISSION_STATUS_NOT_FAILED",
        ),
        (
            observed.terminal_error_code == _ELIGIBLE_TERMINAL_CODE,
            "TERMINAL_CODE_NOT_ELIGIBLE",
        ),
        (
            observed.accrued_cost_nanos_after
            == observed.accrued_cost_nanos_before + observed.model_cost_nanos,
            "COST_ARITHMETIC_DIFFERS",
        ),
        (
            observed.accrued_cost_nanos_after <= observed.hard_cap_nanos,
            "HARD_CAP_EXCEEDED",
        ),
        (
            observed.model_cost_nanos <= observed.row_reserve_nanos,
            "ROW_RESERVE_EXCEEDED",
        ),
    )
    reasons.extend(code for passed, code in fixed_requirements if not passed)
    for field_name, passed in observed.checks.model_dump(mode="python").items():
        if not passed:
            reasons.append(f"CHECK_FAILED_{field_name.upper()}")

    eligible = not reasons
    if eligible:
        reasons = ["ELIGIBLE_SETTLED_ROW_LOCAL_INFRASTRUCTURE"]
    decision_body = {
        "schema_version": RAPID_ROW_CONTINUATION_DECISION_SCHEMA,
        "policy_version": RAPID_ROW_CONTINUATION_POLICY_VERSION,
        "evidence_hash": observed.content_hash,
        "decision": "continue" if eligible else "halt",
        "continuation_eligible": eligible,
        "reason_codes": tuple(reasons),
        "next_schedule_order": observed.next_schedule_order,
        "next_schedule_row_id": observed.next_schedule_row_id,
        "next_run_id": observed.next_run_id,
        "fail_closed": True,
        "next_row_capability_issued": False,
        "provider_calls_authorized": False,
        "docker_calls_authorized": False,
    }
    return _hashed(RapidRowContinuationDecision, decision_body)


def issue_next_rapid_row_after_settlement(
    *,
    evidence: RapidRowSettlementEvidence | dict[str, Any],
    batch_authorization: BatchExecutionAuthorization,
    next_manifest: RunManifest,
) -> tuple[RapidRowContinuationDecision, RowExecutionAuthorization | None]:
    """Issue one fresh row capability only from an unchanged eligible receipt."""

    observed = RapidRowSettlementEvidence.model_validate(evidence)
    decision = classify_rapid_row_continuation(observed)
    if not decision.continuation_eligible:
        return decision, None

    experiment = next_manifest.experiment
    manifest_hash = sha256_json(next_manifest.model_dump(mode="json"))
    batch_receipt = batch_execution_authorization_receipt(batch_authorization)
    if not (
        experiment is not None
        and observed.batch_receipt_hash is not None
        and batch_receipt.get("content_hash") == observed.batch_receipt_hash
        and batch_receipt.get("authority_kind") == "live"
        and batch_receipt.get("execution_hash") == observed.execution_hash
        and batch_receipt.get("plan_hash") == observed.plan_hash
        and batch_receipt.get("schedule_hash") == observed.schedule_hash
        and batch_receipt.get("cost_control_hash") == observed.cost_control_hash
        and batch_receipt.get("next_order") == observed.next_schedule_order
        and experiment.execution_hash == observed.execution_hash
        and experiment.schedule_order == observed.next_schedule_order
        and experiment.schedule_row_id == observed.next_schedule_row_id
        and next_manifest.run_id == observed.next_run_id
        and manifest_hash == observed.next_manifest_hash
    ):
        raise ContractError("Rapid row continuation grant binding differs")

    authorization = issue_row_execution_authorization(
        batch_authorization,
        next_manifest,
        active_schedule_order=observed.next_schedule_order,
    )
    return decision, authorization


def _artifact_projection(
    runner: AgentRunner,
    manifest: RunManifest,
    result: RunResult | None,
) -> tuple[bool, bool, str | None, str | None, str | None]:
    run_dir = runner.artifacts.root / "runs" / manifest.run_id
    manifest_path = run_dir / "manifest.json"
    result_path = run_dir / "result.json"
    provenance_path = run_dir / "provenance.json"
    receipt_path = run_dir / "evaluation-receipt.json"
    try:
        artifact_runs = (runner.artifacts.root / "runs").resolve()
        if (
            run_dir.is_symlink()
            or run_dir.resolve(strict=True).parent != artifact_runs
            or any(
                path.is_symlink() or not path.is_file()
                for path in (manifest_path, result_path, provenance_path)
            )
        ):
            raise OSError("row artifact path is not a local regular-file triad")
        manifest_bytes = manifest_path.read_bytes()
        result_bytes = result_path.read_bytes()
        provenance_bytes = provenance_path.read_bytes()
        persisted_manifest = RunManifest.model_validate_json(manifest_bytes)
        persisted_result = RunResult.model_validate_json(result_bytes)
        provenance = json.loads(provenance_bytes)
        triad_matches = bool(
            result is not None
            and persisted_manifest == manifest
            and persisted_result == result
            and isinstance(provenance, dict)
            and provenance.get("evaluation_reached") is False
            and provenance.get("outcome_kind") == RunOutcomeKind.INFRASTRUCTURE_ERROR.value
            and provenance.get("error_code") == _ELIGIBLE_TERMINAL_CODE
            and isinstance(provenance.get("error_type"), str)
            and bool(provenance["error_type"])
        )
        hashes = (
            sha256_bytes(manifest_bytes),
            sha256_bytes(result_bytes),
            sha256_bytes(provenance_bytes),
        )
    except (OSError, ValueError, json.JSONDecodeError):
        triad_matches = False
        hashes = (None, None, None)
    return triad_matches, not os.path.lexists(receipt_path), *hashes


def _worker_lock_released(runner: AgentRunner, run_id: str) -> bool:
    try:
        with runner.ownership.acquire(run_id):
            return True
    except (OSError, RunOwnershipConflict):
        return False


def _workspace_isolated(
    runner: AgentRunner,
    current_run_id: str,
    next_run_id: str,
) -> bool:
    workspace_root = (runner.root / "workspaces").resolve()
    current_parts = (
        workspace_root / current_run_id,
        workspace_root / current_run_id / "repo",
    )
    next_parts = (
        workspace_root / next_run_id,
        workspace_root / next_run_id / "repo",
    )
    try:
        current_repo = current_parts[-1]
        if (
            current_run_id == next_run_id
            or not current_repo.is_dir()
            or any(path.is_symlink() for path in current_parts)
            or any(path.is_symlink() for path in next_parts if path.exists())
        ):
            return False
        current_resolved = current_repo.resolve(strict=True)
        next_resolved = next_parts[-1].resolve(strict=False)
        return bool(
            current_resolved != next_resolved
            and current_resolved.parent.parent == workspace_root
            and next_resolved.parent.parent == workspace_root
        )
    except OSError:
        return False


def collect_rapid_row_settlement_evidence(
    *,
    runner: AgentRunner,
    manifest: RunManifest,
    next_manifest: RunManifest,
    result: dict[str, Any] | RunResult | None,
    projected_row: dict[str, Any] | None,
    error: Exception | None,
    row_authorization: RowExecutionAuthorization | None,
    batch_authorization: BatchExecutionAuthorization | None,
    accrued_cost_nanos_before: int,
    row_reserve_nanos: int,
    hard_cap_nanos: int,
) -> RapidRowSettlementEvidence:
    """Collect local post-return evidence without external or evaluator calls."""

    current_experiment = manifest.experiment
    next_experiment = next_manifest.experiment
    if current_experiment is None or next_experiment is None:
        raise ContractError("Rapid row continuation requires experiment-bound manifests")
    if current_experiment.execution_hash != next_experiment.execution_hash:
        raise ContractError("Rapid row continuation manifests belong to different executions")
    if (
        type(accrued_cost_nanos_before) is not int
        or type(row_reserve_nanos) is not int
        or type(hard_cap_nanos) is not int
        or row_reserve_nanos <= 0
        or hard_cap_nanos <= 0
    ):
        raise ContractError("Rapid row continuation cost inputs must be exact integers")

    parsed: RunResult | None = None
    result_schema_valid = False
    try:
        if result is not None:
            parsed = RunResult.model_validate(result)
            result_schema_valid = parsed.run_id == manifest.run_id
    except ValueError:
        parsed = None

    current_manifest_hash = sha256_json(manifest.model_dump(mode="json"))
    next_manifest_hash = sha256_json(next_manifest.model_dump(mode="json"))
    model_cost_nanos = _usage_cost_nanos(parsed.usage) if parsed is not None else 0
    accrued_after = accrued_cost_nanos_before + model_cost_nanos

    projection_matches = False
    if parsed is not None and isinstance(projected_row, dict):
        projection_matches = bool(
            projected_row.get("run_id") == parsed.run_id
            and projected_row.get("outcome_kind")
            == (parsed.outcome_kind.value if parsed.outcome_kind is not None else None)
            and projected_row.get("evaluator_reached") is (parsed.evaluation_status == "completed")
            and projected_row.get("submission_completed")
            is (parsed.agent_submission_status == "completed")
            and projected_row.get("success_at_budget") is parsed.scope_compliant_success
            and projected_row.get("usage") == parsed.usage.model_dump(mode="json")
            and projected_row.get("model_cost_nanos") == model_cost_nanos
        )

    state_manifest_hash: str | None = None
    state_result_hash: str | None = None
    returned_result_hash = (
        sha256_json(parsed.model_dump(mode="json")) if parsed is not None else None
    )
    terminal_event_sequence: int | None = None
    terminal_event_hash: str | None = None
    terminal_state_atomic = False
    try:
        stored_manifest = runner.state.get_manifest(manifest.run_id)
        stored_result = runner.state.get_run_result(manifest.run_id)
        events = runner.state.list_events(manifest.run_id)
        terminal_events = [
            event
            for event in events
            if event.type in {EventType.RUN_COMPLETED, EventType.RUN_FAILED}
        ]
        state_manifest_hash = sha256_json(stored_manifest.model_dump(mode="json"))
        if stored_result is not None:
            state_result_hash = sha256_json(stored_result.model_dump(mode="json"))
        terminal = terminal_events[0] if len(terminal_events) == 1 else None
        if terminal is not None:
            terminal_event_sequence = terminal.sequence
            terminal_event_hash = sha256_json(terminal.model_dump(mode="json"))
        terminal_state_atomic = bool(
            parsed is not None
            and stored_manifest == manifest
            and stored_result == parsed
            and runner.state.get_run_status(manifest.run_id) == RunStatus.FAILED
            and terminal is not None
            and events[-1] == terminal
            and terminal.type == EventType.RUN_FAILED
            and terminal.payload.get("outcome_kind") == RunOutcomeKind.INFRASTRUCTURE_ERROR.value
            and terminal.payload.get("error_code") == _ELIGIBLE_TERMINAL_CODE
        )
    except (OSError, ValueError, ContractError, RecoveryError):
        terminal_state_atomic = False

    terminal_error = parsed.terminal_error if parsed is not None else None
    terminal_code = terminal_error.get("code") if isinstance(terminal_error, dict) else None
    typed_terminal = bool(
        parsed is not None
        and parsed.outcome_kind == RunOutcomeKind.INFRASTRUCTURE_ERROR
        and parsed.evaluation_status == "not_run"
        and parsed.agent_submission_status == "failed"
        and terminal_code == _ELIGIBLE_TERMINAL_CODE
    )

    (
        artifact_triad_matches,
        evaluation_receipt_absent,
        manifest_file_sha256,
        result_file_sha256,
        provenance_file_sha256,
    ) = _artifact_projection(runner, manifest, parsed)

    batch_receipt: dict[str, Any] | None = None
    row_receipt: dict[str, Any] | None = None
    try:
        if batch_authorization is not None:
            batch_receipt = batch_execution_authorization_receipt(batch_authorization)
        if row_authorization is not None:
            row_receipt = row_execution_authorization_receipt(row_authorization)
    except ContractError:
        batch_receipt = None
        row_receipt = None

    batch_slots_match = bool(
        batch_authorization is not None
        and batch_receipt is not None
        and batch_authorization.execution_hash == current_experiment.execution_hash
        and 0 < current_experiment.schedule_order <= len(batch_authorization.manifest_hashes)
        and 0 < next_experiment.schedule_order <= len(batch_authorization.manifest_hashes)
        and batch_authorization.manifest_hashes[current_experiment.schedule_order - 1]
        == current_manifest_hash
        and batch_authorization.manifest_hashes[next_experiment.schedule_order - 1]
        == next_manifest_hash
    )
    row_capability_consumed = bool(
        row_receipt is not None
        and row_receipt.get("authority_kind") == "live"
        and row_receipt.get("execution_hash") == current_experiment.execution_hash
        and row_receipt.get("schedule_order") == current_experiment.schedule_order
        and row_receipt.get("schedule_row_id") == current_experiment.schedule_row_id
        and row_receipt.get("run_id") == manifest.run_id
        and row_receipt.get("manifest_hash") == current_manifest_hash
        and row_receipt.get("consumed") is True
    )
    provider_dispatch_started = bool(
        row_capability_consumed
        and row_receipt is not None
        and row_receipt.get("provider_dispatch_started") is True
        and row_receipt.get("provider_dispatch_rehearsed") is False
    )
    batch_next_order_ready = bool(
        batch_receipt is not None
        and batch_receipt.get("authority_kind") == "live"
        and batch_receipt.get("execution_hash") == current_experiment.execution_hash
        and batch_receipt.get("next_order") == next_experiment.schedule_order
    )
    cost_settled = bool(
        parsed is not None
        and projected_row is not None
        and projected_row.get("model_cost_nanos") == model_cost_nanos
        and model_cost_nanos <= row_reserve_nanos
        and accrued_after <= hard_cap_nanos
    )

    checks = RapidRowSettlementChecks(
        runner_returned_without_exception=error is None and result is not None,
        result_schema_valid=result_schema_valid,
        projection_matches_result=projection_matches,
        terminal_state_atomic=terminal_state_atomic,
        typed_recovery_terminal=typed_terminal,
        artifact_triad_matches=artifact_triad_matches,
        evaluation_receipt_absent=evaluation_receipt_absent,
        worker_lock_released=_worker_lock_released(runner, manifest.run_id),
        workspace_isolated=_workspace_isolated(
            runner,
            manifest.run_id,
            next_manifest.run_id,
        ),
        row_capability_consumed=row_capability_consumed,
        provider_dispatch_started=provider_dispatch_started,
        batch_manifest_slots_match=batch_slots_match,
        batch_next_order_ready=batch_next_order_ready,
        cost_settled_under_cap=cost_settled,
    )
    return build_rapid_row_settlement_evidence(
        authority_kind=(batch_receipt.get("authority_kind") if batch_receipt is not None else None),
        execution_hash=current_experiment.execution_hash,
        plan_hash=(batch_receipt.get("plan_hash") if batch_receipt is not None else None),
        schedule_hash=(batch_receipt.get("schedule_hash") if batch_receipt is not None else None),
        cost_control_hash=(
            batch_receipt.get("cost_control_hash") if batch_receipt is not None else None
        ),
        current_schedule_order=current_experiment.schedule_order,
        next_schedule_order=next_experiment.schedule_order,
        current_schedule_row_id=current_experiment.schedule_row_id,
        next_schedule_row_id=next_experiment.schedule_row_id,
        current_run_id=manifest.run_id,
        next_run_id=next_manifest.run_id,
        current_manifest_hash=current_manifest_hash,
        next_manifest_hash=next_manifest_hash,
        batch_receipt_hash=(
            batch_receipt.get("content_hash") if batch_receipt is not None else None
        ),
        row_receipt_hash=(row_receipt.get("content_hash") if row_receipt is not None else None),
        outcome_kind=(parsed.outcome_kind.value if parsed and parsed.outcome_kind else None),
        evaluation_status=parsed.evaluation_status if parsed is not None else None,
        agent_submission_status=(parsed.agent_submission_status if parsed is not None else None),
        terminal_error_code=terminal_code if isinstance(terminal_code, str) else None,
        terminal_event_sequence=terminal_event_sequence,
        terminal_event_hash=terminal_event_hash,
        state_manifest_hash=state_manifest_hash,
        state_result_hash=state_result_hash,
        returned_result_hash=returned_result_hash,
        manifest_file_sha256=manifest_file_sha256,
        result_file_sha256=result_file_sha256,
        provenance_file_sha256=provenance_file_sha256,
        model_cost_nanos=model_cost_nanos,
        row_reserve_nanos=row_reserve_nanos,
        accrued_cost_nanos_before=accrued_cost_nanos_before,
        accrued_cost_nanos_after=accrued_after,
        hard_cap_nanos=hard_cap_nanos,
        checks=checks,
    )
