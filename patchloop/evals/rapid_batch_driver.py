"""Append-only Rapid batch driver with row-local infrastructure isolation.

This driver is intentionally candidate-neutral.  A future Rapid candidate may
bind it as its execution driver only after the offline qualification has
passed.  The driver never creates live authority: it consumes an already
validated batch capability and records the exact order in which row terminals,
continuation decisions and derived one-use row capabilities are observed.

The critical ordering rule is::

    row capability -> row terminal -> typed decision -> next row capability

For a row-local infrastructure terminal, the bounded settlement evidence and
the row-continuation gateway decision are persisted between the terminal and
the next capability.  Missing, stale or restarted ephemeral capability state
halts the batch without starting another row.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
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
from patchloop.errors import ContractError, HarnessAdmissionError, RecoveryError
from patchloop.evals.rapid_public_development import (
    _append_bundle_event,
    _usage_cost_nanos,
)
from patchloop.evals.rapid_row_continuation import (
    RapidRowContinuationDecision,
    RapidRowSettlementEvidence,
    classify_rapid_row_continuation,
    collect_rapid_row_settlement_evidence,
    issue_next_rapid_row_after_settlement,
)
from patchloop.util import sha256_json

RAPID_BATCH_DRIVER_CONTRACT_SCHEMA = "rapid-append-only-batch-driver-contract-v1"
RAPID_BATCH_DRIVER_EVENT_SCHEMA = "rapid-append-only-batch-driver-event-v1"
RAPID_BATCH_DRIVER_POLICY_VERSION = "append-only-row-settlement-driver-v1"
RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION = "append-only-row-settlement-driver-v2"

_ORDINARY_OUTCOMES = frozenset(
    {
        RunOutcomeKind.RESOLVED,
        RunOutcomeKind.TASK_FAILURE,
        RunOutcomeKind.AGENT_FAILURE,
    }
)
_CLOSED_EVENTS = frozenset({"batch-completed", "batch-halted"})


class RapidBatchDriverContract(BaseModel):
    """Immutable driver identity derived from a prevalidated batch capability."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["rapid-append-only-batch-driver-contract-v1"]
    policy_version: Literal[
        "append-only-row-settlement-driver-v1",
        "append-only-row-settlement-driver-v2",
    ]
    official: Literal[False]
    experiment_id: str = Field(min_length=1)
    execution_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    plan_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_build_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    schedule_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    cost_control_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    manifest_hashes: tuple[str, ...] = Field(min_length=1)
    schedule_row_ids: tuple[str, ...] = Field(min_length=1)
    run_ids: tuple[str, ...] = Field(min_length=1)
    row_reserve_nanos: int = Field(gt=0)
    full_schedule_reserve_nanos: int = Field(gt=0)
    hard_cap_nanos: int = Field(gt=0)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        count = len(self.manifest_hashes)
        if not (
            len(self.schedule_row_ids) == count
            and len(self.run_ids) == count
            and len(set(self.schedule_row_ids)) == count
            and len(set(self.run_ids)) == count
            and all(
                value.startswith("sha256:") and len(value) == 71 for value in self.manifest_hashes
            )
        ):
            raise ValueError("Rapid driver schedule identities differ")
        if self.full_schedule_reserve_nanos != self.row_reserve_nanos * count:
            raise ValueError("Rapid driver full reserve differs from row reserves")
        if self.hard_cap_nanos < self.full_schedule_reserve_nanos:
            raise ValueError("Rapid driver hard cap is below its full reserve")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("Rapid driver contract hash differs")
        return self


@dataclass(frozen=True)
class RecordedRapidRowTerminal:
    """Validated local observation retained while one driver process is alive."""

    event: dict[str, Any]
    result: RunResult | None
    projected_row: dict[str, Any]
    error: Exception | None
    accrued_cost_nanos_after: int
    ordinary_terminal_valid: bool
    infrastructure_observed: bool


RapidRowExecutor = Callable[..., dict[str, Any] | RunResult | None]
RapidRowProjector = Callable[..., dict[str, Any]]


def _hashed_contract(body: dict[str, Any]) -> RapidBatchDriverContract:
    return RapidBatchDriverContract.model_validate({**body, "content_hash": sha256_json(body)})


def _build_rapid_batch_driver_contract(
    *,
    policy_version: Literal[
        "append-only-row-settlement-driver-v1",
        "append-only-row-settlement-driver-v2",
    ],
    experiment_id: str,
    manifests: tuple[RunManifest, ...],
    batch_authorization: BatchExecutionAuthorization,
    row_reserve_nanos: int,
    full_schedule_reserve_nanos: int,
    hard_cap_nanos: int,
) -> RapidBatchDriverContract:
    """Bind a fresh, order-zero live batch capability to the successor driver."""

    if not manifests:
        raise HarnessAdmissionError("Rapid driver requires at least one manifest")
    if any(
        type(value) is not int
        for value in (row_reserve_nanos, full_schedule_reserve_nanos, hard_cap_nanos)
    ):
        raise ContractError("Rapid driver cost controls must be exact integers")
    receipt = batch_execution_authorization_receipt(batch_authorization)
    manifest_hashes = tuple(sha256_json(manifest.model_dump(mode="json")) for manifest in manifests)
    schedule_row_ids: list[str] = []
    run_ids: list[str] = []
    for order, (manifest, manifest_hash) in enumerate(
        zip(manifests, manifest_hashes, strict=True),
        start=1,
    ):
        experiment = manifest.experiment
        if (
            experiment is None
            or experiment.execution_hash != receipt.get("execution_hash")
            or experiment.experiment_id != experiment_id
            or experiment.schedule_order != order
            or receipt.get("manifest_count") != len(manifests)
            or batch_authorization.manifest_hashes[order - 1] != manifest_hash
        ):
            raise HarnessAdmissionError("Rapid driver manifest binding differs")
        schedule_row_ids.append(experiment.schedule_row_id)
        run_ids.append(manifest.run_id)
    if receipt.get("authority_kind") != "live" or receipt.get("next_order") != 1:
        raise HarnessAdmissionError("Rapid driver requires a fresh live batch capability")
    body = {
        "schema_version": RAPID_BATCH_DRIVER_CONTRACT_SCHEMA,
        "policy_version": policy_version,
        "official": False,
        "experiment_id": experiment_id,
        "execution_hash": receipt["execution_hash"],
        "plan_hash": receipt["plan_hash"],
        "runtime_build_hash": receipt["runtime_build_hash"],
        "schedule_hash": receipt["schedule_hash"],
        "cost_control_hash": receipt["cost_control_hash"],
        "manifest_hashes": manifest_hashes,
        "schedule_row_ids": tuple(schedule_row_ids),
        "run_ids": tuple(run_ids),
        "row_reserve_nanos": row_reserve_nanos,
        "full_schedule_reserve_nanos": full_schedule_reserve_nanos,
        "hard_cap_nanos": hard_cap_nanos,
    }
    return _hashed_contract(body)


def build_rapid_batch_driver_contract(
    *,
    experiment_id: str,
    manifests: tuple[RunManifest, ...],
    batch_authorization: BatchExecutionAuthorization,
    row_reserve_nanos: int,
    full_schedule_reserve_nanos: int,
    hard_cap_nanos: int,
) -> RapidBatchDriverContract:
    """Build the immutable predecessor contract used by consumed candidate-v25."""

    return _build_rapid_batch_driver_contract(
        policy_version=RAPID_BATCH_DRIVER_POLICY_VERSION,
        experiment_id=experiment_id,
        manifests=manifests,
        batch_authorization=batch_authorization,
        row_reserve_nanos=row_reserve_nanos,
        full_schedule_reserve_nanos=full_schedule_reserve_nanos,
        hard_cap_nanos=hard_cap_nanos,
    )


def build_rapid_batch_driver_terminal_parity_contract(
    *,
    experiment_id: str,
    manifests: tuple[RunManifest, ...],
    batch_authorization: BatchExecutionAuthorization,
    row_reserve_nanos: int,
    full_schedule_reserve_nanos: int,
    hard_cap_nanos: int,
) -> RapidBatchDriverContract:
    """Build the opt-in production-terminal-parity successor contract."""

    return _build_rapid_batch_driver_contract(
        policy_version=RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION,
        experiment_id=experiment_id,
        manifests=manifests,
        batch_authorization=batch_authorization,
        row_reserve_nanos=row_reserve_nanos,
        full_schedule_reserve_nanos=full_schedule_reserve_nanos,
        hard_cap_nanos=hard_cap_nanos,
    )


def _event_common(contract: RapidBatchDriverContract) -> dict[str, Any]:
    return {
        "schema_version": RAPID_BATCH_DRIVER_EVENT_SCHEMA,
        "driver_policy_version": contract.policy_version,
        "official": False,
        "experiment_id": contract.experiment_id,
        "execution_hash": contract.execution_hash,
        "driver_contract_hash": contract.content_hash,
    }


def _event_matches_contract(
    event: dict[str, Any],
    contract: RapidBatchDriverContract,
) -> bool:
    return all(event.get(key) == value for key, value in _event_common(contract).items())


def _sealed_projection_valid(value: Any) -> bool:
    if type(value) is not dict or type(value.get("content_hash")) is not str:
        return False
    body = {key: item for key, item in value.items() if key != "content_hash"}
    return value["content_hash"] == sha256_json(body)


def _capability_record_valid(
    event: dict[str, Any],
    contract: RapidBatchDriverContract,
    order: int,
) -> bool:
    if order < 1 or order > len(contract.manifest_hashes):
        return False
    row_receipt = event.get("row_capability_receipt")
    batch_receipt = event.get("batch_capability_receipt")
    return bool(
        event.get("schedule_order") == order
        and event.get("schedule_row_id") == contract.schedule_row_ids[order - 1]
        and event.get("run_id") == contract.run_ids[order - 1]
        and event.get("manifest_hash") == contract.manifest_hashes[order - 1]
        and _sealed_projection_valid(row_receipt)
        and event.get("row_capability_receipt_hash") == row_receipt["content_hash"]
        and row_receipt.get("authority_kind") == "live"
        and row_receipt.get("execution_hash") == contract.execution_hash
        and row_receipt.get("plan_hash") == contract.plan_hash
        and row_receipt.get("schedule_order") == order
        and row_receipt.get("schedule_row_id") == contract.schedule_row_ids[order - 1]
        and row_receipt.get("run_id") == contract.run_ids[order - 1]
        and row_receipt.get("manifest_hash") == contract.manifest_hashes[order - 1]
        and row_receipt.get("consumed") is False
        and row_receipt.get("provider_dispatch_started") is False
        and row_receipt.get("provider_dispatch_rehearsed") is False
        and _sealed_projection_valid(batch_receipt)
        and event.get("batch_capability_receipt_hash") == batch_receipt["content_hash"]
        and batch_receipt.get("authority_kind") == "live"
        and batch_receipt.get("execution_hash") == contract.execution_hash
        and batch_receipt.get("plan_hash") == contract.plan_hash
        and batch_receipt.get("runtime_build_hash") == contract.runtime_build_hash
        and batch_receipt.get("schedule_hash") == contract.schedule_hash
        and batch_receipt.get("cost_control_hash") == contract.cost_control_hash
        and batch_receipt.get("manifest_count") == len(contract.manifest_hashes)
        and batch_receipt.get("next_order") == order + 1
        and event.get("provider_dispatch_authorized_by_journal") is False
    )


def _read_journal(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise RecoveryError("Rapid driver journal is unavailable")
    try:
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise RecoveryError("Rapid driver journal is invalid") from exc
    if not events:
        raise RecoveryError("Rapid driver journal is empty")
    previous: str | None = None
    for event in events:
        if type(event) is not dict or type(event.get("content_hash")) is not str:
            raise RecoveryError("Rapid driver journal event is invalid")
        body = {key: value for key, value in event.items() if key != "content_hash"}
        if event.get("previous_event_hash") != previous or event["content_hash"] != sha256_json(
            body
        ):
            raise RecoveryError("Rapid driver journal chain differs")
        previous = event["content_hash"]
    return events


def _validate_journal_sequence(
    events: list[dict[str, Any]],
    contract: RapidBatchDriverContract,
) -> None:
    if any(not _event_matches_contract(event, contract) for event in events):
        raise RecoveryError("Rapid driver journal contract binding differs")
    first = events[0]
    if (
        first.get("event") != "batch-started"
        or first.get("previous_event_hash") is not None
        or first.get("row_count") != len(contract.manifest_hashes)
        or first.get("schedule_hash") != contract.schedule_hash
        or first.get("cost_control_hash") != contract.cost_control_hash
        or first.get("plan_hash") != contract.plan_hash
        or first.get("runtime_build_hash") != contract.runtime_build_hash
    ):
        raise RecoveryError("Rapid driver batch-start event differs")

    state = "started"
    active_order = 1
    terminal_count = 0
    accrued_cost_nanos = 0
    cost_fully_settled = True
    last_terminal_order: int | None = None
    last_terminal_hash: str | None = None
    last_terminal_ordinary_valid = False
    last_evidence: RapidRowSettlementEvidence | None = None
    last_decision_hash: str | None = None
    last_decision: str | None = None
    last_decision_source: str | None = None
    for event in events[1:]:
        kind = event.get("event")
        if kind == "batch-recovery-decision":
            if (
                state in {"closed", "recovery"}
                or event.get("decision") != "halt"
                or event.get("observed_tail_event_hash") != event.get("previous_event_hash")
                or event.get("schedule_advanced") is not False
                or event.get("next_row_capability_issued") is not False
            ):
                raise RecoveryError("Rapid driver recovery decision order differs")
            last_decision_hash = event["content_hash"]
            last_decision = "halt"
            last_decision_source = "driver-recovery"
            state = "recovery"
            continue
        if state == "started":
            valid = bool(
                kind == "row-capability-issued"
                and event.get("issuance_kind") == "initial"
                and event.get("source_decision_event_hash") is None
                and _capability_record_valid(event, contract, 1)
            )
            state = "capability" if valid else "invalid"
        elif state == "capability":
            valid = bool(
                kind == "row-terminal"
                and event.get("schedule_order") == active_order
                and event.get("schedule_row_id") == contract.schedule_row_ids[active_order - 1]
                and event.get("run_id") == contract.run_ids[active_order - 1]
                and event.get("manifest_hash") == contract.manifest_hashes[active_order - 1]
                and type(event.get("projected_row")) is dict
                and event.get("projected_row_hash") == sha256_json(event["projected_row"])
                and type(event.get("model_cost_nanos")) is int
                and event.get("model_cost_nanos") >= 0
                and event.get("accrued_cost_nanos_before") == accrued_cost_nanos
                and event.get("accrued_cost_nanos_after")
                == accrued_cost_nanos + event.get("model_cost_nanos")
                and event.get("public_projection_only") is True
            )
            if valid:
                terminal_count += 1
                accrued_cost_nanos = event["accrued_cost_nanos_after"]
                cost_fully_settled = bool(
                    cost_fully_settled and event.get("cost_settlement_complete") is True
                )
                last_terminal_order = active_order
                last_terminal_hash = event["content_hash"]
                last_terminal_ordinary_valid = event.get("ordinary_terminal_valid") is True
                last_evidence = None
                state = "terminal"
            else:
                state = "invalid"
        elif state == "terminal":
            if kind == "row-settlement-evidence":
                valid = bool(
                    event.get("schedule_order") == last_terminal_order
                    and event.get("row_terminal_event_hash") == last_terminal_hash
                    and isinstance(event.get("settlement_evidence"), dict)
                    and event.get("settlement_evidence_hash")
                    == event["settlement_evidence"].get("content_hash")
                )
                if valid:
                    try:
                        last_evidence = RapidRowSettlementEvidence.model_validate(
                            event["settlement_evidence"]
                        )
                    except ValueError:
                        state = "invalid"
                    else:
                        valid = bool(
                            last_evidence.current_schedule_order == active_order
                            and last_evidence.next_schedule_order == active_order + 1
                            and active_order < len(contract.manifest_hashes)
                            and last_evidence.current_schedule_row_id
                            == contract.schedule_row_ids[active_order - 1]
                            and last_evidence.current_run_id == contract.run_ids[active_order - 1]
                            and last_evidence.next_schedule_row_id
                            == contract.schedule_row_ids[active_order]
                            and last_evidence.next_run_id == contract.run_ids[active_order]
                            and last_evidence.current_manifest_hash
                            == contract.manifest_hashes[active_order - 1]
                            and last_evidence.next_manifest_hash
                            == contract.manifest_hashes[active_order]
                        )
                        state = "evidence" if valid else "invalid"
                else:
                    state = "invalid"
            elif kind == "row-decision":
                state = "decision"
            else:
                state = "invalid"
        elif state == "evidence":
            state = "invalid" if kind != "row-decision" else "decision"
        elif state == "decision":
            if kind == "row-capability-issued":
                valid = bool(
                    last_decision == "continue"
                    and event.get("schedule_order") == active_order + 1
                    and _capability_record_valid(event, contract, active_order + 1)
                    and event.get("source_decision_event_hash") == last_decision_hash
                    and (
                        (
                            last_decision_source == "ordinary-terminal"
                            and event.get("issuance_kind") == "ordinary"
                        )
                        or (
                            last_decision_source == "row-local-infrastructure-gateway"
                            and event.get("issuance_kind") == "row-local-infrastructure"
                        )
                    )
                )
                if valid:
                    active_order += 1
                    state = "capability"
                else:
                    state = "invalid"
            elif kind in _CLOSED_EVENTS:
                valid = bool(
                    (last_decision == "complete" and kind == "batch-completed")
                    or (last_decision == "halt" and kind == "batch-halted")
                )
                valid = bool(
                    valid
                    and event.get("source_decision_event_hash") == last_decision_hash
                    and event.get("terminal_row_count") == terminal_count
                    and event.get("not_started_row_count")
                    == len(contract.manifest_hashes) - terminal_count
                    and event.get("accrued_cost_nanos") == accrued_cost_nanos
                    and event.get("cost_fully_settled") is cost_fully_settled
                    and event.get("schedule_fully_observed")
                    is (terminal_count == len(contract.manifest_hashes))
                )
                state = "closed" if valid else "invalid"
            else:
                state = "invalid"
        elif state == "recovery":
            valid = bool(
                kind == "batch-halted"
                and event.get("source_decision_event_hash") == last_decision_hash
                and event.get("terminal_row_count") == terminal_count
                and event.get("not_started_row_count")
                == len(contract.manifest_hashes) - terminal_count
                and event.get("accrued_cost_nanos") == accrued_cost_nanos
                and event.get("cost_fully_settled") is cost_fully_settled
            )
            state = "closed" if valid else "invalid"
        else:
            state = "invalid"
        if state == "invalid":
            raise RecoveryError("Rapid driver journal transition differs")

        if kind == "row-decision":
            source = event.get("decision_source")
            decision = event.get("decision")
            valid = bool(
                event.get("schedule_order") == last_terminal_order
                and event.get("row_terminal_event_hash") == last_terminal_hash
                and decision in {"continue", "halt", "complete"}
                and source
                in {
                    "ordinary-terminal",
                    "row-local-infrastructure-gateway",
                    "driver-contract",
                }
            )
            if source == "row-local-infrastructure-gateway":
                if last_evidence is None:
                    valid = False
                else:
                    expected = classify_rapid_row_continuation(last_evidence)
                    valid = bool(
                        valid
                        and event.get("settlement_evidence_hash") == last_evidence.content_hash
                        and event.get("gateway_decision_hash") == expected.content_hash
                        and decision == expected.decision
                        and event.get("reason_codes") == list(expected.reason_codes)
                    )
            elif source == "ordinary-terminal":
                valid = bool(
                    valid
                    and last_terminal_ordinary_valid
                    and last_evidence is None
                    and decision in {"continue", "complete"}
                    and event.get("settlement_evidence_hash") is None
                    and event.get("gateway_decision_hash") is None
                )
            elif source == "driver-contract":
                valid = bool(valid and not last_terminal_ordinary_valid and decision == "halt")
            if decision == "continue":
                valid = bool(
                    valid
                    and active_order < len(contract.manifest_hashes)
                    and event.get("next_schedule_order") == active_order + 1
                    and event.get("next_schedule_row_id") == contract.schedule_row_ids[active_order]
                    and event.get("next_run_id") == contract.run_ids[active_order]
                )
            elif decision == "complete":
                valid = bool(
                    valid
                    and active_order == len(contract.manifest_hashes)
                    and event.get("next_schedule_order") is None
                    and event.get("next_schedule_row_id") is None
                    and event.get("next_run_id") is None
                )
            else:
                valid = bool(
                    valid
                    and (
                        event.get("next_schedule_order") is None
                        or event.get("next_schedule_order") == active_order + 1
                    )
                )
            valid = bool(
                valid
                and event.get("schedule_advanced") is False
                and event.get("next_row_capability_issued") is False
            )
            if not valid:
                raise RecoveryError("Rapid driver row decision binding differs")
            last_decision_hash = event["content_hash"]
            last_decision = decision
            last_decision_source = source

    if state == "invalid":
        raise RecoveryError("Rapid driver journal state differs")


def load_rapid_batch_driver_journal(
    path: str | Path,
    contract: RapidBatchDriverContract | dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Load and semantically validate one append-only driver journal."""

    parsed_contract = RapidBatchDriverContract.model_validate(contract)
    events = _read_journal(Path(path))
    _validate_journal_sequence(events, parsed_contract)
    return tuple(events)


def _append_driver_event(
    path: Path,
    contract: RapidBatchDriverContract,
    event: dict[str, Any],
    *,
    create: bool = False,
) -> dict[str, Any]:
    if set(event).intersection(_event_common(contract)):
        raise ContractError("Rapid driver event cannot override its contract binding")
    if not create:
        load_rapid_batch_driver_journal(path, contract)
    sealed = _append_bundle_event(
        path,
        {**_event_common(contract), **event},
        create=create,
    )
    load_rapid_batch_driver_journal(path, contract)
    return sealed


def _capability_event(
    *,
    contract: RapidBatchDriverContract,
    manifest: RunManifest,
    authorization: RowExecutionAuthorization,
    batch_authorization: BatchExecutionAuthorization,
    issuance_kind: Literal["initial", "ordinary", "row-local-infrastructure"],
    source_decision_event_hash: str | None,
) -> dict[str, Any]:
    experiment = manifest.experiment
    row_receipt = row_execution_authorization_receipt(authorization)
    batch_receipt = batch_execution_authorization_receipt(batch_authorization)
    if experiment is None:
        raise ContractError("Rapid driver capability lacks experiment context")
    return {
        "event": "row-capability-issued",
        "issuance_kind": issuance_kind,
        "source_decision_event_hash": source_decision_event_hash,
        "schedule_order": experiment.schedule_order,
        "schedule_row_id": experiment.schedule_row_id,
        "run_id": manifest.run_id,
        "manifest_hash": sha256_json(manifest.model_dump(mode="json")),
        "row_capability_receipt": row_receipt,
        "row_capability_receipt_hash": row_receipt["content_hash"],
        "batch_capability_receipt": batch_receipt,
        "batch_capability_receipt_hash": batch_receipt["content_hash"],
        "provider_dispatch_authorized_by_journal": False,
    }


def begin_rapid_batch_driver(
    *,
    journal_path: str | Path,
    contract: RapidBatchDriverContract,
    manifests: tuple[RunManifest, ...],
    batch_authorization: BatchExecutionAuthorization,
) -> RowExecutionAuthorization:
    """Create a new journal and issue the first exact row capability once."""

    path = Path(journal_path)
    if path.exists() or path.is_symlink():
        raise ContractError("Rapid driver journal already exists and cannot be retried")
    if (
        tuple(sha256_json(manifest.model_dump(mode="json")) for manifest in manifests)
        != contract.manifest_hashes
    ):
        raise HarnessAdmissionError("Rapid driver manifests differ from its contract")
    receipt = batch_execution_authorization_receipt(batch_authorization)
    if not (
        receipt.get("content_hash")
        and receipt.get("authority_kind") == "live"
        and receipt.get("execution_hash") == contract.execution_hash
        and receipt.get("plan_hash") == contract.plan_hash
        and receipt.get("runtime_build_hash") == contract.runtime_build_hash
        and receipt.get("schedule_hash") == contract.schedule_hash
        and receipt.get("cost_control_hash") == contract.cost_control_hash
        and receipt.get("manifest_count") == len(manifests)
        and receipt.get("next_order") == 1
    ):
        raise HarnessAdmissionError("Rapid driver batch capability differs before start")
    _append_driver_event(
        path,
        contract,
        {
            "event": "batch-started",
            "plan_hash": contract.plan_hash,
            "runtime_build_hash": contract.runtime_build_hash,
            "schedule_hash": contract.schedule_hash,
            "cost_control_hash": contract.cost_control_hash,
            "row_count": len(manifests),
            "row_reserve_nanos": contract.row_reserve_nanos,
            "full_schedule_reserve_nanos": contract.full_schedule_reserve_nanos,
            "hard_cap_nanos": contract.hard_cap_nanos,
        },
        create=True,
    )
    first = issue_row_execution_authorization(
        batch_authorization,
        manifests[0],
        active_schedule_order=1,
    )
    _append_driver_event(
        path,
        contract,
        _capability_event(
            contract=contract,
            manifest=manifests[0],
            authorization=first,
            batch_authorization=batch_authorization,
            issuance_kind="initial",
            source_decision_event_hash=None,
        ),
    )
    return first


def _terminal_state_matches(
    runner: AgentRunner,
    manifest: RunManifest,
    result: RunResult | None,
    *,
    policy_version: str,
) -> bool:
    if result is None:
        return False
    try:
        stored_manifest = runner.state.get_manifest(manifest.run_id)
        stored_result = runner.state.get_run_result(manifest.run_id)
        status = runner.state.get_run_status(manifest.run_id)
        events = runner.state.list_events(manifest.run_id)
    except (OSError, ValueError, ContractError, RecoveryError):
        return False
    terminals = [
        event for event in events if event.type in {EventType.RUN_COMPLETED, EventType.RUN_FAILED}
    ]
    terminal = terminals[0] if len(terminals) == 1 else None
    if terminal is None:
        return False
    if policy_version == RAPID_BATCH_DRIVER_POLICY_VERSION:
        payload_matches = terminal.payload.get("outcome_kind") == (
            result.outcome_kind.value if result.outcome_kind is not None else None
        )
    elif policy_version == RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION:
        if terminal.type == EventType.RUN_COMPLETED:
            payload_matches = bool(
                status == RunStatus.COMPLETED
                and result.outcome_kind in {RunOutcomeKind.RESOLVED, RunOutcomeKind.TASK_FAILURE}
                and terminal.payload.get("scope_compliant_success")
                is result.scope_compliant_success
                and terminal.payload.get("official") is result.official
            )
        else:
            payload_matches = bool(
                status == RunStatus.FAILED
                and result.outcome_kind
                in {RunOutcomeKind.AGENT_FAILURE, RunOutcomeKind.INFRASTRUCTURE_ERROR}
                and terminal.payload.get("outcome_kind")
                == (result.outcome_kind.value if result.outcome_kind is not None else None)
            )
    else:
        return False
    return bool(
        stored_manifest == manifest
        and stored_result == result
        and status in {RunStatus.COMPLETED, RunStatus.FAILED}
        and events[-1] == terminal
        and payload_matches
    )


def _projection_matches_result(projected: dict[str, Any], result: RunResult) -> bool:
    return bool(
        projected.get("run_id") == result.run_id
        and projected.get("outcome_kind")
        == (result.outcome_kind.value if result.outcome_kind is not None else None)
        and projected.get("evaluator_reached") is (result.evaluation_status == "completed")
        and projected.get("submission_completed") is (result.agent_submission_status == "completed")
        and projected.get("success_at_budget") is result.scope_compliant_success
        and projected.get("usage") == result.usage.model_dump(mode="json")
        and type(projected.get("model_cost_nanos")) is int
        and projected.get("model_cost_nanos") == _usage_cost_nanos(result.usage)
    )


def record_rapid_driver_row_terminal(
    *,
    journal_path: str | Path,
    contract: RapidBatchDriverContract,
    runner: AgentRunner,
    manifest: RunManifest,
    authorization: RowExecutionAuthorization,
    result: dict[str, Any] | RunResult | None,
    projected_row: dict[str, Any],
    error: Exception | None,
    accrued_cost_nanos_before: int,
) -> RecordedRapidRowTerminal:
    """Persist one public row terminal before any continuation decision."""

    path = Path(journal_path)
    events = load_rapid_batch_driver_journal(path, contract)
    tail = events[-1]
    experiment = manifest.experiment
    if (
        experiment is None
        or tail.get("event") != "row-capability-issued"
        or tail.get("schedule_order") != experiment.schedule_order
        or type(accrued_cost_nanos_before) is not int
        or accrued_cost_nanos_before < 0
        or type(projected_row) is not dict
    ):
        raise ContractError("Rapid driver row terminal does not follow its capability")

    parsed: RunResult | None = None
    try:
        if result is not None:
            parsed = RunResult.model_validate(result)
            if parsed.run_id != manifest.run_id:
                parsed = None
    except ValueError:
        parsed = None

    settled_cost = _usage_cost_nanos(parsed.usage) if parsed is not None else 0
    accrued_after = accrued_cost_nanos_before + settled_cost
    row_receipt = row_execution_authorization_receipt(authorization)
    capability_valid = bool(
        row_receipt.get("authority_kind") == "live"
        and row_receipt.get("execution_hash") == contract.execution_hash
        and row_receipt.get("schedule_order") == experiment.schedule_order
        and row_receipt.get("schedule_row_id") == experiment.schedule_row_id
        and row_receipt.get("run_id") == manifest.run_id
        and row_receipt.get("manifest_hash") == sha256_json(manifest.model_dump(mode="json"))
        and row_receipt.get("consumed") is True
        and row_receipt.get("provider_dispatch_started") is True
        and row_receipt.get("provider_dispatch_rehearsed") is False
    )
    projection_match = bool(
        parsed is not None and _projection_matches_result(projected_row, parsed)
    )
    state_match = _terminal_state_matches(
        runner,
        manifest,
        parsed,
        policy_version=contract.policy_version,
    )
    cost_valid = bool(
        parsed is not None
        and projection_match
        and settled_cost <= contract.row_reserve_nanos
        and accrued_after <= contract.hard_cap_nanos
    )
    ordinary_valid = bool(
        error is None
        and parsed is not None
        and parsed.outcome_kind in _ORDINARY_OUTCOMES
        and capability_valid
        and state_match
        and projection_match
        and cost_valid
    )
    infrastructure_observed = bool(
        (parsed is not None and parsed.outcome_kind == RunOutcomeKind.INFRASTRUCTURE_ERROR)
        or projected_row.get("outcome_kind") == RunOutcomeKind.INFRASTRUCTURE_ERROR.value
    )
    event = _append_driver_event(
        path,
        contract,
        {
            "event": "row-terminal",
            "schedule_order": experiment.schedule_order,
            "schedule_row_id": experiment.schedule_row_id,
            "run_id": manifest.run_id,
            "manifest_hash": sha256_json(manifest.model_dump(mode="json")),
            "runner_returned_without_exception": error is None and result is not None,
            "escaped_error_type": type(error).__name__ if error is not None else None,
            "returned_result_hash": (
                sha256_json(parsed.model_dump(mode="json")) if parsed is not None else None
            ),
            "projected_row": projected_row,
            "projected_row_hash": sha256_json(projected_row),
            "outcome_kind": (
                parsed.outcome_kind.value
                if parsed is not None and parsed.outcome_kind is not None
                else projected_row.get("outcome_kind")
            ),
            "row_capability_receipt_hash": row_receipt["content_hash"],
            "row_capability_consumed_and_dispatched": capability_valid,
            "terminal_state_atomic": state_match,
            "projection_matches_result": projection_match,
            "cost_settlement_complete": cost_valid,
            "model_cost_nanos": settled_cost,
            "accrued_cost_nanos_before": accrued_cost_nanos_before,
            "accrued_cost_nanos_after": accrued_after,
            "ordinary_terminal_valid": ordinary_valid,
            "public_projection_only": True,
        },
    )
    return RecordedRapidRowTerminal(
        event=event,
        result=parsed,
        projected_row=projected_row,
        error=error,
        accrued_cost_nanos_after=accrued_after,
        ordinary_terminal_valid=ordinary_valid,
        infrastructure_observed=infrastructure_observed,
    )


def _invalid_terminal_reasons(recorded: RecordedRapidRowTerminal) -> tuple[str, ...]:
    event = recorded.event
    reasons: list[str] = []
    if event.get("runner_returned_without_exception") is not True:
        reasons.append("RUNNER_DID_NOT_RETURN_CLEANLY")
    if recorded.result is None:
        reasons.append("RESULT_SCHEMA_INVALID_OR_MISSING")
    if event.get("row_capability_consumed_and_dispatched") is not True:
        reasons.append("ROW_CAPABILITY_NOT_CONSUMED_AND_DISPATCHED")
    if event.get("terminal_state_atomic") is not True:
        reasons.append("TERMINAL_STATE_NOT_ATOMIC")
    if event.get("projection_matches_result") is not True:
        reasons.append("PROJECTION_RESULT_MISMATCH")
    if event.get("cost_settlement_complete") is not True:
        reasons.append("COST_SETTLEMENT_INVALID")
    if not reasons:
        reasons.append("OUTCOME_NOT_CONTINUABLE")
    return tuple(reasons)


def _append_row_decision(
    *,
    path: Path,
    contract: RapidBatchDriverContract,
    recorded: RecordedRapidRowTerminal,
    decision: Literal["continue", "halt", "complete"],
    source: Literal[
        "ordinary-terminal",
        "row-local-infrastructure-gateway",
        "driver-contract",
    ],
    reason_codes: tuple[str, ...],
    next_manifest: RunManifest | None,
    settlement_evidence_hash: str | None = None,
    gateway_decision_hash: str | None = None,
) -> dict[str, Any]:
    experiment = next_manifest.experiment if next_manifest is not None else None
    return _append_driver_event(
        path,
        contract,
        {
            "event": "row-decision",
            "schedule_order": recorded.event["schedule_order"],
            "schedule_row_id": recorded.event["schedule_row_id"],
            "run_id": recorded.event["run_id"],
            "row_terminal_event_hash": recorded.event["content_hash"],
            "decision": decision,
            "decision_source": source,
            "reason_codes": list(reason_codes),
            "settlement_evidence_hash": settlement_evidence_hash,
            "gateway_decision_hash": gateway_decision_hash,
            "next_schedule_order": experiment.schedule_order if experiment else None,
            "next_schedule_row_id": experiment.schedule_row_id if experiment else None,
            "next_run_id": next_manifest.run_id if next_manifest else None,
            "schedule_advanced": False,
            "next_row_capability_issued": False,
        },
    )


def decide_rapid_driver_row_continuation(
    *,
    journal_path: str | Path,
    contract: RapidBatchDriverContract,
    runner: AgentRunner,
    manifest: RunManifest,
    next_manifest: RunManifest | None,
    recorded: RecordedRapidRowTerminal,
    authorization: RowExecutionAuthorization,
    batch_authorization: BatchExecutionAuthorization,
    accrued_cost_nanos_before: int,
) -> tuple[dict[str, Any], RapidRowSettlementEvidence | None]:
    """Persist the typed row decision without issuing the next capability."""

    path = Path(journal_path)
    events = load_rapid_batch_driver_journal(path, contract)
    if events[-1].get("content_hash") != recorded.event.get("content_hash"):
        raise ContractError("Rapid driver row decision is not based on the journal tail")

    if next_manifest is None:
        if recorded.ordinary_terminal_valid:
            return (
                _append_row_decision(
                    path=path,
                    contract=contract,
                    recorded=recorded,
                    decision="complete",
                    source="ordinary-terminal",
                    reason_codes=("SCHEDULE_EXHAUSTED_AFTER_SETTLED_TERMINAL",),
                    next_manifest=None,
                ),
                None,
            )
        return (
            _append_row_decision(
                path=path,
                contract=contract,
                recorded=recorded,
                decision="halt",
                source="driver-contract",
                reason_codes=_invalid_terminal_reasons(recorded),
                next_manifest=None,
            ),
            None,
        )

    if recorded.infrastructure_observed:
        try:
            evidence = collect_rapid_row_settlement_evidence(
                runner=runner,
                manifest=manifest,
                next_manifest=next_manifest,
                result=recorded.result,
                projected_row=recorded.projected_row,
                error=recorded.error,
                row_authorization=authorization,
                batch_authorization=batch_authorization,
                accrued_cost_nanos_before=accrued_cost_nanos_before,
                row_reserve_nanos=contract.row_reserve_nanos,
                hard_cap_nanos=contract.hard_cap_nanos,
            )
        except (ContractError, RecoveryError, ValueError):
            return (
                _append_row_decision(
                    path=path,
                    contract=contract,
                    recorded=recorded,
                    decision="halt",
                    source="driver-contract",
                    reason_codes=("SETTLEMENT_EVIDENCE_COLLECTION_FAILED",),
                    next_manifest=next_manifest,
                ),
                None,
            )
        _append_driver_event(
            path,
            contract,
            {
                "event": "row-settlement-evidence",
                "schedule_order": recorded.event["schedule_order"],
                "schedule_row_id": recorded.event["schedule_row_id"],
                "run_id": recorded.event["run_id"],
                "row_terminal_event_hash": recorded.event["content_hash"],
                "settlement_evidence": evidence.model_dump(mode="json"),
                "settlement_evidence_hash": evidence.content_hash,
                "public_projection_only": True,
            },
        )
        gateway_decision = classify_rapid_row_continuation(evidence)
        return (
            _append_row_decision(
                path=path,
                contract=contract,
                recorded=recorded,
                decision=gateway_decision.decision,
                source="row-local-infrastructure-gateway",
                reason_codes=gateway_decision.reason_codes,
                next_manifest=next_manifest,
                settlement_evidence_hash=evidence.content_hash,
                gateway_decision_hash=gateway_decision.content_hash,
            ),
            evidence,
        )

    if recorded.ordinary_terminal_valid:
        return (
            _append_row_decision(
                path=path,
                contract=contract,
                recorded=recorded,
                decision="continue",
                source="ordinary-terminal",
                reason_codes=("ORDINARY_TERMINAL_SETTLED",),
                next_manifest=next_manifest,
            ),
            None,
        )
    return (
        _append_row_decision(
            path=path,
            contract=contract,
            recorded=recorded,
            decision="halt",
            source="driver-contract",
            reason_codes=_invalid_terminal_reasons(recorded),
            next_manifest=next_manifest,
        ),
        None,
    )


def issue_persisted_rapid_driver_next_row(
    *,
    journal_path: str | Path,
    contract: RapidBatchDriverContract,
    decision_event: dict[str, Any],
    settlement_evidence: RapidRowSettlementEvidence | None,
    batch_authorization: BatchExecutionAuthorization,
    next_manifest: RunManifest,
) -> RowExecutionAuthorization:
    """Issue and persist one next-row capability from the current decision tail."""

    path = Path(journal_path)
    events = load_rapid_batch_driver_journal(path, contract)
    tail = events[-1]
    experiment = next_manifest.experiment
    if (
        tail.get("content_hash") != decision_event.get("content_hash")
        or tail.get("event") != "row-decision"
        or tail.get("decision") != "continue"
        or experiment is None
        or tail.get("next_schedule_order") != experiment.schedule_order
        or tail.get("next_schedule_row_id") != experiment.schedule_row_id
        or tail.get("next_run_id") != next_manifest.run_id
        or contract.manifest_hashes[experiment.schedule_order - 1]
        != sha256_json(next_manifest.model_dump(mode="json"))
    ):
        raise ContractError("Rapid driver continuation decision is stale or mismatched")

    receipt_before = batch_execution_authorization_receipt(batch_authorization)
    if not (
        receipt_before.get("execution_hash") == contract.execution_hash
        and receipt_before.get("plan_hash") == contract.plan_hash
        and receipt_before.get("runtime_build_hash") == contract.runtime_build_hash
        and receipt_before.get("schedule_hash") == contract.schedule_hash
        and receipt_before.get("cost_control_hash") == contract.cost_control_hash
        and receipt_before.get("next_order") == experiment.schedule_order
    ):
        raise ContractError("Rapid driver batch capability changed before continuation")

    source = tail.get("decision_source")
    if source == "row-local-infrastructure-gateway":
        if (
            settlement_evidence is None
            or tail.get("settlement_evidence_hash") != settlement_evidence.content_hash
        ):
            raise ContractError("Rapid driver settlement evidence differs from its decision")
        gateway_decision, authorization = issue_next_rapid_row_after_settlement(
            evidence=settlement_evidence,
            batch_authorization=batch_authorization,
            next_manifest=next_manifest,
        )
        if (
            authorization is None
            or not isinstance(gateway_decision, RapidRowContinuationDecision)
            or gateway_decision.content_hash != tail.get("gateway_decision_hash")
        ):
            raise ContractError("Rapid driver gateway grant differs from its persisted decision")
        issuance_kind: Literal["ordinary", "row-local-infrastructure"] = "row-local-infrastructure"
    elif source == "ordinary-terminal":
        if settlement_evidence is not None:
            raise ContractError("Rapid ordinary continuation cannot carry settlement evidence")
        authorization = issue_row_execution_authorization(
            batch_authorization,
            next_manifest,
            active_schedule_order=experiment.schedule_order,
        )
        issuance_kind = "ordinary"
    else:
        raise ContractError("Rapid driver decision source cannot issue a row")

    _append_driver_event(
        path,
        contract,
        _capability_event(
            contract=contract,
            manifest=next_manifest,
            authorization=authorization,
            batch_authorization=batch_authorization,
            issuance_kind=issuance_kind,
            source_decision_event_hash=tail["content_hash"],
        ),
    )
    return authorization


def _append_batch_close(
    *,
    path: Path,
    contract: RapidBatchDriverContract,
    event: Literal["batch-completed", "batch-halted"],
    decision_event_hash: str,
    reason_codes: tuple[str, ...],
    accrued_cost_nanos: int,
) -> dict[str, Any]:
    events = load_rapid_batch_driver_journal(path, contract)
    terminal_events = [item for item in events if item.get("event") == "row-terminal"]
    terminal_count = len(terminal_events)
    return _append_driver_event(
        path,
        contract,
        {
            "event": event,
            "source_decision_event_hash": decision_event_hash,
            "reason_codes": list(reason_codes),
            "terminal_row_count": terminal_count,
            "not_started_row_count": len(contract.manifest_hashes) - terminal_count,
            "accrued_cost_nanos": accrued_cost_nanos,
            "cost_fully_settled": all(
                item.get("cost_settlement_complete") is True for item in terminal_events
            ),
            "schedule_fully_observed": terminal_count == len(contract.manifest_hashes),
            "candidate_created": False,
            "external_execution_authorized": False,
        },
    )


def close_interrupted_rapid_batch_driver(
    *,
    journal_path: str | Path,
    contract: RapidBatchDriverContract,
) -> dict[str, Any]:
    """Persist a fail-closed restart decision when ephemeral receipts are gone."""

    path = Path(journal_path)
    events = load_rapid_batch_driver_journal(path, contract)
    if events[-1].get("event") in _CLOSED_EVENTS:
        return events[-1]
    terminal_rows = [event for event in events if event.get("event") == "row-terminal"]
    accrued = terminal_rows[-1].get("accrued_cost_nanos_after", 0) if terminal_rows else 0
    if type(accrued) is not int or accrued < 0:
        accrued = 0
    if events[-1].get("event") == "batch-recovery-decision":
        reasons = events[-1].get("reason_codes")
        if not isinstance(reasons, list) or not reasons:
            raise RecoveryError("Rapid driver recovery reason is unavailable")
        return _append_batch_close(
            path=path,
            contract=contract,
            event="batch-halted",
            decision_event_hash=events[-1]["content_hash"],
            reason_codes=tuple(reasons),
            accrued_cost_nanos=accrued,
        )
    recovery = _append_driver_event(
        path,
        contract,
        {
            "event": "batch-recovery-decision",
            "decision": "halt",
            "reason_codes": ["EPHEMERAL_CAPABILITY_STATE_UNAVAILABLE_ON_RESTART"],
            "observed_tail_event_hash": events[-1]["content_hash"],
            "schedule_advanced": False,
            "next_row_capability_issued": False,
        },
    )
    return _append_batch_close(
        path=path,
        contract=contract,
        event="batch-halted",
        decision_event_hash=recovery["content_hash"],
        reason_codes=("EPHEMERAL_CAPABILITY_STATE_UNAVAILABLE_ON_RESTART",),
        accrued_cost_nanos=accrued,
    )


def _close_after_driver_fault(
    *,
    path: Path,
    contract: RapidBatchDriverContract,
    reason_code: str,
    accrued_cost_nanos: int,
) -> dict[str, Any]:
    events = load_rapid_batch_driver_journal(path, contract)
    recovery = _append_driver_event(
        path,
        contract,
        {
            "event": "batch-recovery-decision",
            "decision": "halt",
            "reason_codes": [reason_code],
            "observed_tail_event_hash": events[-1]["content_hash"],
            "schedule_advanced": False,
            "next_row_capability_issued": False,
        },
    )
    return _append_batch_close(
        path=path,
        contract=contract,
        event="batch-halted",
        decision_event_hash=recovery["content_hash"],
        reason_codes=(reason_code,),
        accrued_cost_nanos=accrued_cost_nanos,
    )


def run_append_only_rapid_batch_driver(
    *,
    journal_path: str | Path,
    contract: RapidBatchDriverContract,
    manifests: tuple[RunManifest, ...],
    schedule_rows: tuple[dict[str, Any], ...],
    runner: AgentRunner,
    batch_authorization: BatchExecutionAuthorization,
    execute_row: RapidRowExecutor,
    project_row: RapidRowProjector,
) -> dict[str, Any]:
    """Execute a preauthorized mocked-or-live row function through the driver.

    This function itself does not obtain credentials, provider authority,
    Docker access or evaluator authority.  Those remain responsibilities of a
    future candidate-specific caller and the already-issued row capability.
    """

    if len(manifests) != len(schedule_rows) or len(manifests) != len(contract.manifest_hashes):
        raise ContractError("Rapid driver schedule rows differ from its manifests")
    for order, schedule_row in enumerate(schedule_rows, start=1):
        if (
            type(schedule_row) is not dict
            or schedule_row.get("order") != order
            or schedule_row.get("schedule_row_id") != contract.schedule_row_ids[order - 1]
        ):
            raise ContractError("Rapid driver public schedule projection differs")
    path = Path(journal_path)
    authorization = begin_rapid_batch_driver(
        journal_path=path,
        contract=contract,
        manifests=manifests,
        batch_authorization=batch_authorization,
    )
    accrued = 0
    for index, (schedule_row, manifest) in enumerate(zip(schedule_rows, manifests, strict=True)):
        error: Exception | None = None
        result: dict[str, Any] | RunResult | None = None
        try:
            result = execute_row(
                schedule_row=schedule_row,
                manifest=manifest,
                row_authorization=authorization,
            )
        except Exception as exc:  # the bounded public projection records only its type
            error = exc
            try:
                result = runner.state.get_run_result(manifest.run_id)
            except (OSError, ValueError, ContractError, RecoveryError):
                result = None
        try:
            projected = project_row(
                schedule_row=schedule_row,
                manifest=manifest,
                result=result,
                runner=runner,
                error=error,
            )
        except Exception:
            return _close_after_driver_fault(
                path=path,
                contract=contract,
                reason_code="ROW_PROJECTION_FAILED",
                accrued_cost_nanos=accrued,
            )
        recorded = record_rapid_driver_row_terminal(
            journal_path=path,
            contract=contract,
            runner=runner,
            manifest=manifest,
            authorization=authorization,
            result=result,
            projected_row=projected,
            error=error,
            accrued_cost_nanos_before=accrued,
        )
        accrued = recorded.accrued_cost_nanos_after
        next_manifest = manifests[index + 1] if index + 1 < len(manifests) else None
        decision, evidence = decide_rapid_driver_row_continuation(
            journal_path=path,
            contract=contract,
            runner=runner,
            manifest=manifest,
            next_manifest=next_manifest,
            recorded=recorded,
            authorization=authorization,
            batch_authorization=batch_authorization,
            accrued_cost_nanos_before=recorded.event["accrued_cost_nanos_before"],
        )
        if decision["decision"] == "continue":
            assert next_manifest is not None
            try:
                authorization = issue_persisted_rapid_driver_next_row(
                    journal_path=path,
                    contract=contract,
                    decision_event=decision,
                    settlement_evidence=evidence,
                    batch_authorization=batch_authorization,
                    next_manifest=next_manifest,
                )
            except (ContractError, HarnessAdmissionError, RecoveryError):
                return _close_after_driver_fault(
                    path=path,
                    contract=contract,
                    reason_code="CONTINUATION_CAPABILITY_GRANT_FAILED",
                    accrued_cost_nanos=accrued,
                )
            continue
        if decision["decision"] == "complete":
            return _append_batch_close(
                path=path,
                contract=contract,
                event="batch-completed",
                decision_event_hash=decision["content_hash"],
                reason_codes=tuple(decision["reason_codes"]),
                accrued_cost_nanos=accrued,
            )
        return _append_batch_close(
            path=path,
            contract=contract,
            event="batch-halted",
            decision_event_hash=decision["content_hash"],
            reason_codes=tuple(decision["reason_codes"]),
            accrued_cost_nanos=accrued,
        )
    raise RecoveryError("Rapid driver exhausted its loop without a batch terminal")


__all__ = [
    "RAPID_BATCH_DRIVER_CONTRACT_SCHEMA",
    "RAPID_BATCH_DRIVER_EVENT_SCHEMA",
    "RAPID_BATCH_DRIVER_POLICY_VERSION",
    "RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION",
    "RapidBatchDriverContract",
    "RecordedRapidRowTerminal",
    "begin_rapid_batch_driver",
    "build_rapid_batch_driver_contract",
    "build_rapid_batch_driver_terminal_parity_contract",
    "close_interrupted_rapid_batch_driver",
    "decide_rapid_driver_row_continuation",
    "issue_persisted_rapid_driver_next_row",
    "load_rapid_batch_driver_journal",
    "record_rapid_driver_row_terminal",
    "run_append_only_rapid_batch_driver",
]
