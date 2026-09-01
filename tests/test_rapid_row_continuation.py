from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from patchloop.agent import runner as runner_module
from patchloop.agent.runner import (
    AgentRunner,
    BatchExecutionAuthorization,
    RowExecutionAuthorization,
    batch_execution_authorization_receipt,
    row_execution_authorization_receipt,
)
from patchloop.contracts import EventType, RunOutcomeKind, RunResult, RunStatus, Usage, Verdicts
from patchloop.errors import ContractError
from patchloop.evals import rapid_public_development_v19 as rapid
from patchloop.evals.rapid_public_development import _row_projection, _usage_cost_nanos
from patchloop.evals.rapid_row_continuation import (
    RapidRowSettlementChecks,
    RapidRowSettlementEvidence,
    build_rapid_row_settlement_evidence,
    classify_rapid_row_continuation,
    collect_rapid_row_settlement_evidence,
    issue_next_rapid_row_after_settlement,
)
from patchloop.util import sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _all_checks(**changes: bool) -> RapidRowSettlementChecks:
    body = {
        "runner_returned_without_exception": True,
        "result_schema_valid": True,
        "projection_matches_result": True,
        "terminal_state_atomic": True,
        "typed_recovery_terminal": True,
        "artifact_triad_matches": True,
        "evaluation_receipt_absent": True,
        "worker_lock_released": True,
        "workspace_isolated": True,
        "row_capability_consumed": True,
        "provider_dispatch_started": True,
        "batch_manifest_slots_match": True,
        "batch_next_order_ready": True,
        "cost_settled_under_cap": True,
    }
    body.update(changes)
    return RapidRowSettlementChecks.model_validate(body)


def _synthetic_evidence(
    *,
    checks: RapidRowSettlementChecks | None = None,
    **changes: Any,
) -> RapidRowSettlementEvidence:
    current_manifest_hash = sha256_json("manifest-01")
    result_hash = sha256_json("result-01")
    body: dict[str, Any] = {
        "authority_kind": "live",
        "execution_hash": sha256_json("execution"),
        "plan_hash": sha256_json("plan"),
        "schedule_hash": sha256_json("schedule"),
        "cost_control_hash": sha256_json("cost-control"),
        "current_schedule_order": 1,
        "next_schedule_order": 2,
        "current_schedule_row_id": "row-01",
        "next_schedule_row_id": "row-02",
        "current_run_id": "run_row_01",
        "next_run_id": "run_row_02",
        "current_manifest_hash": current_manifest_hash,
        "next_manifest_hash": sha256_json("manifest-02"),
        "batch_receipt_hash": sha256_json("batch-receipt"),
        "row_receipt_hash": sha256_json("row-receipt"),
        "outcome_kind": "infrastructure_error",
        "evaluation_status": "not_run",
        "agent_submission_status": "failed",
        "terminal_error_code": "RECOVERY_ERROR",
        "terminal_event_sequence": 143,
        "terminal_event_hash": sha256_json("event"),
        "state_manifest_hash": current_manifest_hash,
        "state_result_hash": result_hash,
        "returned_result_hash": result_hash,
        "manifest_file_sha256": sha256_json("manifest-file"),
        "result_file_sha256": sha256_json("result-file"),
        "provenance_file_sha256": sha256_json("provenance-file"),
        "model_cost_nanos": 534_452_250,
        "row_reserve_nanos": 1_200_000_000,
        "accrued_cost_nanos_before": 0,
        "accrued_cost_nanos_after": 534_452_250,
        "hard_cap_nanos": 7_500_000_000,
        "checks": checks or _all_checks(),
    }
    body.update(changes)
    return build_rapid_row_settlement_evidence(**body)


def _reseal(
    evidence: RapidRowSettlementEvidence,
    **changes: Any,
) -> RapidRowSettlementEvidence:
    body = evidence.model_dump(mode="json", exclude={"content_hash"})
    body.update(changes)
    return RapidRowSettlementEvidence.model_validate({**body, "content_hash": sha256_json(body)})


def test_exact_settled_row_is_the_only_continue_shape_and_is_deterministic() -> None:
    evidence = _synthetic_evidence()

    first = classify_rapid_row_continuation(evidence)
    second = classify_rapid_row_continuation(evidence.model_dump(mode="json"))

    assert first == second
    assert first.decision == "continue"
    assert first.continuation_eligible is True
    assert first.reason_codes == ("ELIGIBLE_SETTLED_ROW_LOCAL_INFRASTRUCTURE",)
    assert first.next_row_capability_issued is False


@pytest.mark.parametrize("field_name", tuple(_all_checks().model_dump(mode="python")))
def test_every_missing_settlement_check_halts(field_name: str) -> None:
    evidence = _synthetic_evidence(checks=_all_checks(**{field_name: False}))

    decision = classify_rapid_row_continuation(evidence)

    assert decision.decision == "halt"
    assert decision.continuation_eligible is False
    assert f"CHECK_FAILED_{field_name.upper()}" in decision.reason_codes


@pytest.mark.parametrize(
    ("field_name", "reason"),
    (
        ("plan_hash", "PLAN_HASH_MISSING"),
        ("schedule_hash", "SCHEDULE_HASH_MISSING"),
        ("cost_control_hash", "COST_CONTROL_HASH_MISSING"),
        ("batch_receipt_hash", "BATCH_RECEIPT_HASH_MISSING"),
        ("row_receipt_hash", "ROW_RECEIPT_HASH_MISSING"),
        ("terminal_event_sequence", "TERMINAL_EVENT_SEQUENCE_MISSING"),
        ("terminal_event_hash", "TERMINAL_EVENT_HASH_MISSING"),
        ("state_manifest_hash", "STATE_MANIFEST_HASH_MISSING"),
        ("state_result_hash", "STATE_RESULT_HASH_MISSING"),
        ("returned_result_hash", "RETURNED_RESULT_HASH_MISSING"),
        ("manifest_file_sha256", "MANIFEST_FILE_HASH_MISSING"),
        ("result_file_sha256", "RESULT_FILE_HASH_MISSING"),
        ("provenance_file_sha256", "PROVENANCE_FILE_HASH_MISSING"),
    ),
)
def test_every_missing_required_identity_halts(field_name: str, reason: str) -> None:
    decision = classify_rapid_row_continuation(_synthetic_evidence(**{field_name: None}))

    assert decision.decision == "halt"
    assert reason in decision.reason_codes


@pytest.mark.parametrize(
    ("changes", "reason"),
    (
        ({"authority_kind": "rehearsal"}, "AUTHORITY_NOT_LIVE"),
        ({"next_schedule_order": 3}, "NEXT_ORDER_NOT_CONTIGUOUS"),
        ({"next_schedule_row_id": "row-01"}, "NEXT_ROW_ID_NOT_DISTINCT"),
        ({"next_run_id": "run_row_01"}, "NEXT_RUN_ID_NOT_DISTINCT"),
        ({"outcome_kind": "agent_failure"}, "OUTCOME_NOT_INFRASTRUCTURE"),
        ({"evaluation_status": "completed"}, "EVALUATION_STATUS_NOT_NOT_RUN"),
        ({"agent_submission_status": "completed"}, "SUBMISSION_STATUS_NOT_FAILED"),
        ({"terminal_error_code": "OTHER"}, "TERMINAL_CODE_NOT_ELIGIBLE"),
        (
            {"returned_result_hash": sha256_json("different-result")},
            "STATE_RESULT_HASH_DIFFERS",
        ),
        ({"accrued_cost_nanos_after": 1}, "COST_ARITHMETIC_DIFFERS"),
        (
            {"row_reserve_nanos": 500_000_000},
            "ROW_RESERVE_EXCEEDED",
        ),
        (
            {
                "accrued_cost_nanos_after": 534_452_250,
                "hard_cap_nanos": 500_000_000,
            },
            "HARD_CAP_EXCEEDED",
        ),
    ),
)
def test_semantic_identity_and_cost_conflicts_halt(
    changes: dict[str, Any],
    reason: str,
) -> None:
    decision = classify_rapid_row_continuation(_synthetic_evidence(**changes))

    assert decision.decision == "halt"
    assert reason in decision.reason_codes


def test_tampered_evidence_fails_before_classification() -> None:
    evidence = _synthetic_evidence().model_dump(mode="json")
    evidence["terminal_error_code"] = "RECOVERY_ERROR_TAMPERED"

    with pytest.raises(ContractError, match="evidence is invalid"):
        classify_rapid_row_continuation(evidence)


def _live_authorizations(
    manifests: tuple[Any, ...],
    *,
    current_order: int = 1,
    consumed: bool = True,
    provider_started: bool = True,
) -> tuple[BatchExecutionAuthorization, RowExecutionAuthorization]:
    current = manifests[current_order - 1]
    assert current.experiment is not None
    manifest_hashes = tuple(sha256_json(item.model_dump(mode="json")) for item in manifests)
    batch = BatchExecutionAuthorization(
        authority_kind="live",
        execution_hash=current.experiment.execution_hash,
        plan_hash=sha256_json("approved-plan"),
        runtime_build_hash=sha256_json("runtime"),
        schedule_hash=sha256_json("schedule"),
        cost_control_hash=sha256_json("cost"),
        manifest_hashes=manifest_hashes,
        _state=runner_module._BatchExecutionAuthorizationState(next_order=current_order + 1),
        _guard=runner_module._BATCH_EXECUTION_AUTHORIZATION_GUARD,
    )
    row = RowExecutionAuthorization(
        authority_kind="live",
        execution_hash=current.experiment.execution_hash,
        plan_hash=batch.plan_hash,
        schedule_order=current_order,
        schedule_row_id=current.experiment.schedule_row_id,
        run_id=current.run_id,
        manifest_hash=manifest_hashes[current_order - 1],
        _state=runner_module._RowExecutionAuthorizationState(
            consumed=consumed,
            provider_dispatch_started=provider_started,
        ),
        _guard=runner_module._ROW_EXECUTION_AUTHORIZATION_GUARD,
    )
    return batch, row


def _settled_runtime(
    tmp_path: Path,
) -> tuple[
    AgentRunner,
    tuple[Any, ...],
    RunResult,
    dict[str, Any],
    BatchExecutionAuthorization,
    RowExecutionAuthorization,
]:
    candidate = rapid.load_consumed_rapid_public_development_v19_candidate(REPOSITORY)
    manifests = tuple(
        rapid.build_rapid_v19_run_manifest(candidate, order, repository=REPOSITORY)
        for order in range(1, 7)
    )
    manifest = manifests[0]
    runner = AgentRunner(tmp_path / ".patchloop")
    runner.state.create_run(manifest)
    runner.state.set_run_status(manifest.run_id, RunStatus.RUNNING)

    usage = Usage(
        input_tokens=100,
        output_tokens=20,
        model_calls=2,
        tool_calls=3,
    )
    usage.model_cost_usd = _usage_cost_nanos(usage) / 1_000_000_000
    result = RunResult(
        run_id=manifest.run_id,
        agent_submission_status="failed",
        evaluation_status="not_run",
        scope_compliant_success=False,
        official=False,
        verdicts=Verdicts(),
        usage=usage,
        outcome_kind=RunOutcomeKind.INFRASTRUCTURE_ERROR,
        terminal_error={
            "type": "RecoveryError",
            "message": "sanitized public terminal",
            "code": "RECOVERY_ERROR",
        },
    )
    run_dir = runner.artifacts.root / "runs" / manifest.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    runner.artifacts.write_text_atomic(
        run_dir / "manifest.json",
        manifest.model_dump_json(indent=2),
    )
    runner.artifacts.write_text_atomic(
        run_dir / "result.json",
        result.model_dump_json(indent=2),
    )
    runner.artifacts.write_text_atomic(
        run_dir / "provenance.json",
        json.dumps(
            {
                "evaluation_reached": False,
                "outcome_kind": "infrastructure_error",
                "error_type": "RecoveryError",
                "error_code": "RECOVERY_ERROR",
            },
            indent=2,
        ),
    )
    runner.state.finalize_run(
        manifest.run_id,
        status=RunStatus.FAILED,
        result=result,
        event_type=EventType.RUN_FAILED,
        actor="runner",
        payload={
            "outcome_kind": "infrastructure_error",
            "error_type": "RecoveryError",
            "error_code": "RECOVERY_ERROR",
            "message": "sanitized public terminal",
            "model_cost_usd": usage.model_cost_usd,
        },
    )
    workspace = runner.root / "workspaces" / manifest.run_id / "repo"
    workspace.mkdir(parents=True)
    projected = _row_projection(
        schedule_row=candidate["schedule"][0],
        result=result.model_dump(mode="json"),
        runner=runner,
        error=None,
    )
    batch, row = _live_authorizations(manifests)
    return runner, manifests, result, projected, batch, row


def test_receipts_commit_exact_mutable_capability_state(tmp_path: Path) -> None:
    _, manifests, _, _, batch, row = _settled_runtime(tmp_path)

    batch_receipt = batch_execution_authorization_receipt(batch)
    row_receipt = row_execution_authorization_receipt(row)

    assert batch_receipt["next_order"] == 2
    assert batch_receipt["content_hash"] == sha256_json(
        {key: value for key, value in batch_receipt.items() if key != "content_hash"}
    )
    assert row_receipt["manifest_hash"] == sha256_json(manifests[0].model_dump(mode="json"))
    assert row_receipt["consumed"] is True
    assert row_receipt["provider_dispatch_started"] is True
    assert row_receipt["provider_dispatch_rehearsed"] is False
    assert row_receipt["content_hash"] == sha256_json(
        {key: value for key, value in row_receipt.items() if key != "content_hash"}
    )


def test_real_shaped_settlement_collects_and_continues(tmp_path: Path) -> None:
    runner, manifests, result, projected, batch, row = _settled_runtime(tmp_path)

    evidence = collect_rapid_row_settlement_evidence(
        runner=runner,
        manifest=manifests[0],
        next_manifest=manifests[1],
        result=result,
        projected_row=projected,
        error=None,
        row_authorization=row,
        batch_authorization=batch,
        accrued_cost_nanos_before=0,
        row_reserve_nanos=rapid.PER_RUN_RESERVE_NANOS,
        hard_cap_nanos=7_500_000_000,
    )

    assert all(evidence.checks.model_dump(mode="python").values())
    assert evidence.terminal_error_code == "RECOVERY_ERROR"
    assert evidence.terminal_event_sequence == 1
    assert classify_rapid_row_continuation(evidence).decision == "continue"

    decision, next_row = issue_next_rapid_row_after_settlement(
        evidence=evidence,
        batch_authorization=batch,
        next_manifest=manifests[1],
    )
    assert decision.decision == "continue"
    assert next_row is not None
    next_receipt = row_execution_authorization_receipt(next_row)
    assert next_receipt["schedule_order"] == 2
    assert next_receipt["consumed"] is False
    assert next_receipt["provider_dispatch_started"] is False
    assert batch_execution_authorization_receipt(batch)["next_order"] == 3

    with pytest.raises(ContractError, match="grant binding differs"):
        issue_next_rapid_row_after_settlement(
            evidence=evidence,
            batch_authorization=batch,
            next_manifest=manifests[1],
        )
    assert batch_execution_authorization_receipt(batch)["next_order"] == 3


def test_active_lock_and_missing_ephemeral_receipts_halt(tmp_path: Path) -> None:
    runner, manifests, result, projected, batch, row = _settled_runtime(tmp_path)

    with runner.ownership.acquire(manifests[0].run_id):
        locked = collect_rapid_row_settlement_evidence(
            runner=runner,
            manifest=manifests[0],
            next_manifest=manifests[1],
            result=result,
            projected_row=projected,
            error=None,
            row_authorization=row,
            batch_authorization=batch,
            accrued_cost_nanos_before=0,
            row_reserve_nanos=rapid.PER_RUN_RESERVE_NANOS,
            hard_cap_nanos=7_500_000_000,
        )
    assert locked.checks.worker_lock_released is False
    assert classify_rapid_row_continuation(locked).decision == "halt"
    next_order_before = batch_execution_authorization_receipt(batch)["next_order"]
    decision, next_row = issue_next_rapid_row_after_settlement(
        evidence=locked,
        batch_authorization=batch,
        next_manifest=manifests[1],
    )
    assert decision.decision == "halt"
    assert next_row is None
    assert batch_execution_authorization_receipt(batch)["next_order"] == next_order_before

    restarted = AgentRunner(runner.root)
    without_receipts = collect_rapid_row_settlement_evidence(
        runner=restarted,
        manifest=manifests[0],
        next_manifest=manifests[1],
        result=result,
        projected_row=projected,
        error=None,
        row_authorization=None,
        batch_authorization=None,
        accrued_cost_nanos_before=0,
        row_reserve_nanos=rapid.PER_RUN_RESERVE_NANOS,
        hard_cap_nanos=7_500_000_000,
    )
    assert without_receipts.checks.row_capability_consumed is False
    assert without_receipts.checks.provider_dispatch_started is False
    assert without_receipts.checks.batch_next_order_ready is False
    assert classify_rapid_row_continuation(without_receipts).decision == "halt"


def test_artifact_tamper_and_over_cap_are_row_local_faults_that_halt(
    tmp_path: Path,
) -> None:
    runner, manifests, result, projected, batch, row = _settled_runtime(tmp_path)
    run_dir = runner.artifacts.root / "runs" / manifests[0].run_id
    runner.artifacts.write_text_atomic(
        run_dir / "provenance.json",
        json.dumps(
            {
                "evaluation_reached": False,
                "outcome_kind": "infrastructure_error",
                "error_type": "RecoveryError",
                "error_code": "TAMPERED",
            },
            indent=2,
        ),
    )

    tampered = collect_rapid_row_settlement_evidence(
        runner=runner,
        manifest=manifests[0],
        next_manifest=manifests[1],
        result=result,
        projected_row=projected,
        error=None,
        row_authorization=row,
        batch_authorization=batch,
        accrued_cost_nanos_before=0,
        row_reserve_nanos=rapid.PER_RUN_RESERVE_NANOS,
        hard_cap_nanos=7_500_000_000,
    )
    assert tampered.checks.artifact_triad_matches is False
    assert classify_rapid_row_continuation(tampered).decision == "halt"

    over_cap = collect_rapid_row_settlement_evidence(
        runner=runner,
        manifest=manifests[0],
        next_manifest=manifests[1],
        result=result,
        projected_row=projected,
        error=None,
        row_authorization=row,
        batch_authorization=batch,
        accrued_cost_nanos_before=7_499_999_999,
        row_reserve_nanos=rapid.PER_RUN_RESERVE_NANOS,
        hard_cap_nanos=7_500_000_000,
    )
    assert over_cap.checks.cost_settled_under_cap is False
    assert "HARD_CAP_EXCEEDED" in classify_rapid_row_continuation(over_cap).reason_codes
