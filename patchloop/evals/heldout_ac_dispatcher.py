"""Authoritative append-only dispatcher for the preregistered held-out A/C panel.

Importing this module grants no runtime authority.  A campaign can start only
from a persisted no-call candidate whose exact execution hash has a separate
paid approval.  Every row is consumed once before provider entry, authenticated
from durable evaluator-v2/qualification/usage files, and settled before the next
row.  Any prespecified confound stops the panel and seals the remainder as not
started; no retry, replacement or resume path exists.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from patchloop.agent.runner import AgentRunner, issue_live_execution_authorization
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import EventType, RunResult
from patchloop.environment import (
    exact_openai_api_key_environment,
    exact_openai_api_key_present,
)
from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_analysis import (
    EvaluatorCompletedOutcome,
    HeldoutACAnalysis,
    HeldoutACOutcomeProjection,
    HeldoutACOutcomeRow,
    HeldoutACUsage,
    TypedAgentTerminalOutcome,
    analyze_heldout_ac,
)
from patchloop.evals.heldout_ac_completion import HeldoutACDurableUsage
from patchloop.evals.heldout_ac_contracts import (
    HELDOUT_AC_SUITE_ID,
    HeldoutACFrozenModel,
)
from patchloop.evals.heldout_ac_execution import (
    HeldoutACExecutionCandidate,
    build_heldout_ac_run_manifest,
    materialize_heldout_ac_runtime_task_authority,
)
from patchloop.evals.heldout_ac_live_contract import (
    DISPATCH_SOURCE_QUALIFICATION_ID,
    JOURNAL_SCHEMA_VERSION,
    PLAN_KIND,
    PLAN_SCHEMA_VERSION,
    _exact_typed_equal,
    _load_journal_events,
    heldout_ac_candidate_has_current_source_binding,
    heldout_ac_runtime_contract,
)
from patchloop.evals.heldout_ac_persisted_adapter import (
    HeldoutACAuthenticatedPersistedRow,
    HeldoutACPersistedUsageEvidence,
    authenticate_heldout_ac_persisted_row,
)
from patchloop.evals.heldout_ac_suite import load_heldout_ac_suite
from patchloop.runtime import make_run_id, repository_root, runtime_root
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, sha256_json, utc_now

CAMPAIGN_RESULT_SCHEMA_VERSION = "heldout-ac-authoritative-campaign-result-v1"
PREPARED_RESULT_SCHEMA_VERSION = "heldout-ac-campaign-prepared-result-v1"
SETTLED_ROW_SCHEMA_VERSION = "heldout-ac-settled-campaign-row-v1"
CONFOUND_SCHEMA_VERSION = "heldout-ac-campaign-confound-v1"
NOT_STARTED_SCHEMA_VERSION = "heldout-ac-campaign-not-started-row-v1"

MatrixConfound = Literal[
    "provider-sdk-docker-or-evaluator-infrastructure-error",
    "qualification-or-completion-contract-mismatch",
    "private-marker-or-leakage-hit",
    "schedule-treatment-runtime-source-or-hash-drift",
    "missing-durable-usage-or-cost-settlement",
    "duplicate-retried-replaced-or-resumed-row",
    "full-schedule-reservation-or-hard-cap-boundary-failure",
]
ConfoundPhase = Literal["row-dispatch", "qualification", "authentication", "settlement"]
AgentTerminalType = Literal[
    "token-budget-exhaustion",
    "model-call-limit",
    "tool-call-limit",
    "wall-clock-timeout",
    "submission-failure",
]

_SUITE_PATH = Path("experiments/heldout-ac-suite-20260814-v1.yaml")
_DATASET_PATH = Path("data/dataset-manifest.yaml")
_PRICES = {
    "uncached_input": 750,
    "cached_input": 75,
    "cache_write_input": 750,
    "output": 4_500,
}


class HeldoutACDispatcherError(ContractError):
    """The dedicated campaign dispatcher failed closed."""


class HeldoutACSettledCampaignRow(HeldoutACFrozenModel):
    schema_version: Literal[SETTLED_ROW_SCHEMA_VERSION] = SETTLED_ROW_SCHEMA_VERSION
    authenticated_row: HeldoutACAuthenticatedPersistedRow
    terminal_type: AgentTerminalType | None
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_settled_row(self) -> HeldoutACSettledCampaignRow:
        evaluator_completed = self.authenticated_row.result.evaluation_status == "completed"
        if evaluator_completed != (self.terminal_type is None):
            raise ValueError("held-out settled row terminal classification differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out settled row content hash differs")
        return self


class HeldoutACCampaignConfound(HeldoutACFrozenModel):
    schema_version: Literal[CONFOUND_SCHEMA_VERSION] = CONFOUND_SCHEMA_VERSION
    order: int = Field(ge=1, le=48)
    schedule_row_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_id: str
    run_id: str = Field(pattern=r"^run_[A-Za-z0-9_-]+$")
    trigger: MatrixConfound
    phase: ConfoundPhase
    exception_type: str = Field(min_length=1)
    run_started_event_written: bool
    secret_or_exception_message_persisted: Literal[False] = False
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_confound(self) -> HeldoutACCampaignConfound:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out campaign confound content hash differs")
        return self


class HeldoutACNotStartedRow(HeldoutACFrozenModel):
    schema_version: Literal[NOT_STARTED_SCHEMA_VERSION] = NOT_STARTED_SCHEMA_VERSION
    order: int = Field(ge=1, le=48)
    schedule_row_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_id: str
    role: Literal["core-same-repo", "core-cross-repo"]
    condition: Literal["no_memory", "structured"]
    repetition: Literal[1, 2]
    reason: Literal["campaign-stopped-after-prespecified-confound"]
    trigger: MatrixConfound


class HeldoutACCampaignResult(HeldoutACFrozenModel):
    schema_version: Literal[CAMPAIGN_RESULT_SCHEMA_VERSION] = CAMPAIGN_RESULT_SCHEMA_VERSION
    evidence_status: Literal["authenticated-persisted-campaign"]
    disposition: Literal["complete-matrix", "inconclusive-matrix"]
    suite_id: Literal[HELDOUT_AC_SUITE_ID]
    suite_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    execution_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    execution_plan_path: str
    execution_plan_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    journal_path: str
    journal_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    campaign_completed_event_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    prepared_result_path: str
    prepared_result_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    prepared_result_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    expected_runs: Literal[48]
    terminal_settled_runs: int = Field(ge=0, le=48)
    not_started_runs: int = Field(ge=0, le=48)
    settled_model_cost_nanos: int = Field(ge=0, le=252_000_000_000)
    unsettled_dispatched_runs: int = Field(ge=0, le=1)
    cost_accounting_complete: bool
    full_schedule_reserve_nanos: Literal[252_000_000_000]
    hard_cap_nanos: Literal[275_000_000_000]
    settled_rows: tuple[HeldoutACSettledCampaignRow, ...]
    confound: HeldoutACCampaignConfound | None
    not_started_rows: tuple[HeldoutACNotStartedRow, ...]
    outcome_projection: HeldoutACOutcomeProjection | None
    analysis: HeldoutACAnalysis | None
    analysis_ready: bool
    official_heldout_analysis: bool
    memory_benefit_claim_authorized: Literal[False]
    broad_generalization_claim_authorized: Literal[False]
    retry_replacement_or_resume_performed: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_result(self) -> HeldoutACCampaignResult:
        settled_orders = tuple(row.authenticated_row.order for row in self.settled_rows)
        not_started_orders = tuple(row.order for row in self.not_started_rows)
        if self.terminal_settled_runs != len(self.settled_rows):
            raise ValueError("held-out settled run count differs")
        if self.not_started_runs != len(self.not_started_rows):
            raise ValueError("held-out not-started run count differs")
        if self.settled_model_cost_nanos != sum(
            row.authenticated_row.usage_evidence.token_derived_cost_nanos
            for row in self.settled_rows
        ):
            raise ValueError("held-out settled model cost differs")
        expected_unsettled = int(
            self.confound is not None and self.confound.run_started_event_written
        )
        if (
            self.unsettled_dispatched_runs != expected_unsettled
            or self.cost_accounting_complete != (expected_unsettled == 0)
        ):
            raise ValueError("held-out unsettled dispatch accounting differs")
        if self.disposition == "complete-matrix":
            complete = (
                settled_orders == tuple(range(1, 49))
                and not not_started_orders
                and self.confound is None
                and self.outcome_projection is not None
                and self.analysis is not None
                and self.analysis_ready is True
                and self.official_heldout_analysis is True
            )
        else:
            confound_order = self.confound.order if self.confound is not None else None
            complete = (
                settled_orders == tuple(range(1, len(settled_orders) + 1))
                and confound_order == len(settled_orders) + 1
                and not_started_orders == tuple(range(confound_order + 1, 49))
                and self.outcome_projection is None
                and self.analysis is None
                and self.analysis_ready is False
                and self.official_heldout_analysis is False
            )
        if not complete:
            raise ValueError("held-out result disposition does not match its rows")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out campaign result content hash differs")
        return self


def _root(path: str | Path | None) -> Path:
    return Path(path).resolve() if path is not None else runtime_root().resolve()


def _repository(path: str | Path | None) -> Path:
    return Path(path).resolve() if path is not None else repository_root().resolve()


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise HeldoutACDispatcherError("held-out dispatcher timestamp must be UTC")
    return value.isoformat().replace("+00:00", "Z")


def _write_new(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise HeldoutACDispatcherError(f"append-only held-out path already exists: {path.name}")
    try:
        with path.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise HeldoutACDispatcherError(
            f"append-only held-out path already exists: {path.name}"
        ) from exc


def _candidate_from_mapping(
    value: HeldoutACExecutionCandidate | dict[str, Any],
) -> HeldoutACExecutionCandidate:
    try:
        candidate = (
            HeldoutACExecutionCandidate.model_validate(value.model_dump(mode="python"))
            if isinstance(value, HeldoutACExecutionCandidate)
            else HeldoutACExecutionCandidate.model_validate_json(json.dumps(value))
        )
    except ValidationError as exc:
        raise HeldoutACDispatcherError("held-out candidate contract is invalid") from exc
    if candidate.source_qualification.qualification_id != DISPATCH_SOURCE_QUALIFICATION_ID:
        raise HeldoutACDispatcherError(
            "held-out candidate is not the dispatcher-qualified successor"
        )
    return candidate


def prepare_heldout_ac_approved_plan(
    *,
    candidate: HeldoutACExecutionCandidate | dict[str, Any],
    approve_live_cost: bool,
    approved_execution_hash: str,
    root: str | Path | None = None,
    repository: str | Path | None = None,
    created_at: datetime | None = None,
) -> Path:
    """Persist one new-only paid plan after exact external approval."""

    if type(approve_live_cost) is not bool or approve_live_cost is not True:
        raise HeldoutACDispatcherError("held-out paid approval must be the exact boolean true")
    parsed = _candidate_from_mapping(candidate)
    if approved_execution_hash != parsed.execution_hash:
        raise HeldoutACDispatcherError("held-out paid approval hash differs from the candidate")
    suite = load_heldout_ac_suite(_SUITE_PATH, repository=_repository(repository))
    if parsed.suite_content_hash != suite.content_hash:
        raise HeldoutACDispatcherError("held-out candidate uses another suite")
    if not heldout_ac_candidate_has_current_source_binding(
        parsed,
        repository=_repository(repository),
    ):
        raise HeldoutACDispatcherError(
            "held-out candidate source qualification differs from the current successor"
        )
    run_root = _root(root)
    digest = parsed.execution_hash.removeprefix("sha256:")
    plan_path = run_root / "experiments" / "plans" / f"{digest}.json"
    journal_path = run_root / "experiments" / "journals" / f"{digest}.jsonl"
    result_path = run_root / "experiments" / "heldout-ac" / f"{digest}.json"
    if any(path.exists() or path.is_symlink() for path in (journal_path, result_path)):
        raise HeldoutACDispatcherError("held-out campaign identity already has runtime state")
    body = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "plan_kind": PLAN_KIND,
        "created_at": _utc_text(created_at or utc_now()),
        "ready": True,
        "blockers": [],
        "suite": suite.model_dump(mode="json"),
        "candidate": parsed.model_dump(mode="json"),
        "execution_hash": parsed.execution_hash,
        "schedule_hash": parsed.schedule_hash,
        "runtime_contract": heldout_ac_runtime_contract(parsed),
        "campaign_cost_control": parsed.campaign_cost_control.model_dump(mode="json"),
        "approval": {
            "invocation_approve_live_cost": True,
            "invocation_approved_execution_hash": parsed.execution_hash,
            "matches_execution_hash": True,
            "scheduled_run_count": 48,
            "full_schedule_reserve_nanos": 252_000_000_000,
            "hard_cap_nanos": 275_000_000_000,
        },
        "journal_path": str(journal_path.resolve(strict=False)),
        "result_path": str(result_path.resolve(strict=False)),
    }
    encoded = (json.dumps(body, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    _write_new(plan_path, encoded)
    return plan_path


def _load_approved_plan(execution_hash: str, run_root: Path) -> tuple[dict[str, Any], bytes]:
    authorization = issue_live_execution_authorization(execution_hash, root=run_root)
    try:
        raw = Path(authorization.plan_path).read_bytes()
        plan = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise HeldoutACDispatcherError("held-out approved plan is unavailable") from exc
    if not isinstance(plan, dict) or sha256_bytes(raw) != authorization.plan_hash:
        raise HeldoutACDispatcherError("held-out approved plan bytes differ")
    _candidate_from_mapping(plan.get("candidate"))
    return plan, raw


def _journal_event(
    *,
    sequence: int,
    event_type: str,
    payload: dict[str, Any],
    previous_event_hash: str | None,
    recorded_at: datetime | None = None,
) -> dict[str, Any]:
    body = {
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "sequence": sequence,
        "event_type": event_type,
        "recorded_at": _utc_text(recorded_at or utc_now()),
        "previous_event_hash": previous_event_hash,
        "payload": payload,
    }
    return {**body, "event_hash": sha256_json(body)}


def _create_journal(path: Path, candidate: HeldoutACExecutionCandidate, plan_hash: str) -> None:
    started = _journal_event(
        sequence=1,
        event_type="CampaignStarted",
        payload={
            "suite_id": candidate.suite_id,
            "suite_content_hash": candidate.suite_content_hash,
            "execution_hash": candidate.execution_hash,
            "execution_plan_file_sha256": plan_hash,
            "schedule_hash": candidate.schedule_hash,
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
            "expected_runs": 48,
        },
        previous_event_hash=None,
    )
    reserved = _journal_event(
        sequence=2,
        event_type="FullScheduleCostReserved",
        payload={
            "suite_id": candidate.suite_id,
            "execution_hash": candidate.execution_hash,
            "execution_plan_file_sha256": plan_hash,
            "schedule_hash": candidate.schedule_hash,
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
            "reserved_runs": 48,
            "per_run_reserve_nanos": 5_250_000_000,
            "full_schedule_reserve_nanos": 252_000_000_000,
            "hard_cap_nanos": 275_000_000_000,
            "cost_censoring_allowed": False,
        },
        previous_event_hash=started["event_hash"],
    )
    encoded = (
        json.dumps(started, sort_keys=True, separators=(",", ":"))
        + "\n"
        + json.dumps(reserved, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    _write_new(path, encoded)


def _append_journal(path: Path, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        last = json.loads(raw.decode("utf-8").splitlines()[-1])
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, IndexError) as exc:
        raise HeldoutACDispatcherError("held-out journal prefix is unavailable") from exc
    event = _journal_event(
        sequence=int(last["sequence"]) + 1,
        event_type=event_type,
        payload=payload,
        previous_event_hash=last["event_hash"],
    )
    encoded = (json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    with path.open("ab") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    return event


def _row_identity(row: Any) -> dict[str, Any]:
    return {
        "order": row.order,
        "wave": row.wave,
        "schedule_row_id": row.schedule_row_id,
        "task_id": row.task_id,
        "role": row.role,
        "condition": row.condition,
        "repetition": row.repetition,
    }


def _persist_usage_and_authenticate(
    *,
    candidate: HeldoutACExecutionCandidate,
    order: int,
    run_id: str,
    run_root: Path,
    repository: Path,
    task_dir: Path,
    authority: Any,
) -> HeldoutACAuthenticatedPersistedRow:
    from patchloop.evals.qualification import qualify_run

    row = candidate.schedule[order - 1]
    artifacts = ArtifactStore(run_root / "artifacts")
    result_file = artifacts.root / "runs" / run_id / "result.json"
    result_bytes = result_file.read_bytes()
    result = RunResult.model_validate_json(result_bytes)
    qualification = qualify_run(
        run_id,
        task_dir=task_dir,
        dataset_manifest_path=repository / _DATASET_PATH,
        root=run_root,
        evaluator_v2_authority=authority.qualification_authority,
    )
    qualification_hash = qualification.get("qualification_hash")
    source_evidence_hash = qualification.get("source_evidence_hash")
    if not isinstance(qualification_hash, str) or not isinstance(source_evidence_hash, str):
        raise HeldoutACDispatcherError("held-out trace qualification has no durable identities")
    usage_raw = result.usage.model_dump(mode="json")
    durable_usage = HeldoutACDurableUsage(
        **{
            key: usage_raw[key]
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
    receipt_file = artifacts.root / "runs" / run_id / "evaluation-receipt.json"
    receipt_file_hash = (
        sha256_bytes(receipt_file.read_bytes()) if result.evaluation_status == "completed" else None
    )
    usage_body = {
        "schema_version": "heldout-ac-durable-usage-evidence-v1",
        "run_id": run_id,
        "schedule_row_id": row.schedule_row_id,
        "pricing_binding_hash": candidate.pricing_binding_hash,
        "price_nanos_per_token": _PRICES,
        "usage": durable_usage.model_dump(mode="json"),
        "token_derived_cost_nanos": durable_usage.token_derived_cost_nanos(),
        "qualification_hash": qualification_hash,
        "source_evidence_hash": source_evidence_hash,
        "persisted_result_file_hash": sha256_bytes(result_bytes),
        "evaluator_v2_receipt_file_hash": receipt_file_hash,
    }
    usage = HeldoutACPersistedUsageEvidence(
        **usage_body,
        content_hash=sha256_json(usage_body),
    )
    relative = (
        Path("experiments")
        / "heldout-ac"
        / "rows"
        / candidate.execution_hash.removeprefix("sha256:")
        / f"{order:02d}-{run_id}-usage.json"
    )
    usage_path = run_root / relative
    usage_bytes = json.dumps(
        usage.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False
    ).encode("utf-8")
    _write_new(usage_path, usage_bytes)
    return authenticate_heldout_ac_persisted_row(
        suite=load_heldout_ac_suite(_SUITE_PATH, repository=repository),
        execution_hash=candidate.execution_hash,
        expected_pricing_binding_hash=candidate.pricing_binding_hash,
        order=order,
        task_evaluator_binding=authority.task_binding,
        run_root=run_root,
        task_dir=task_dir,
        dataset_manifest_path=repository / _DATASET_PATH,
        evaluator_authority=authority.qualification_authority,
        usage_evidence_relative_path=relative.as_posix(),
    )


def _terminal_type(run_root: Path, row: HeldoutACAuthenticatedPersistedRow) -> AgentTerminalType:
    state = StateStore(run_root / "state.sqlite3")
    reason_codes = [
        event.payload.get("reason_code")
        for event in state.list_events(row.run_id)
        if event.type == EventType.MODEL_GENERATION_BLOCKED
    ]
    mapping: dict[Any, AgentTerminalType] = {
        "exact_request_budget_exceeded": "token-budget-exhaustion",
        "model_call_budget_exhausted": "model-call-limit",
        "tool_call_budget_exhausted": "tool-call-limit",
        "wall_clock_budget_exhausted": "wall-clock-timeout",
    }
    for reason in reversed(reason_codes):
        if reason in mapping:
            return mapping[reason]
    return "submission-failure"


def _settled_row(
    row: HeldoutACAuthenticatedPersistedRow,
    *,
    run_root: Path,
) -> HeldoutACSettledCampaignRow:
    terminal_type = (
        None if row.result.evaluation_status == "completed" else _terminal_type(run_root, row)
    )
    body = {
        "schema_version": SETTLED_ROW_SCHEMA_VERSION,
        "authenticated_row": row.model_dump(mode="json"),
        "terminal_type": terminal_type,
    }
    return HeldoutACSettledCampaignRow(**body, content_hash=sha256_json(body))


def _validate_settlement_limits(
    row: HeldoutACAuthenticatedPersistedRow,
    *,
    accrued_before: int,
) -> int:
    usage = row.usage_evidence.usage
    cost = row.usage_evidence.token_derived_cost_nanos
    within_runtime = (
        usage.input_tokens <= 4_000_000
        and usage.output_tokens <= 500_000
        and usage.input_tokens + usage.output_tokens <= 4_500_000
        and usage.model_calls <= 240
        and usage.tool_calls <= 400
        and cost <= 5_250_000_000
    )
    if not within_runtime:
        raise HeldoutACDispatcherError(
            "held-out authenticated usage exceeds the frozen per-row boundary"
        )
    if accrued_before + cost > 252_000_000_000:
        raise HeldoutACDispatcherError("held-out settled cost exceeds the full-schedule reserve")
    return cost


def _analysis_projection(
    rows: list[HeldoutACSettledCampaignRow],
) -> HeldoutACOutcomeProjection:
    projected: list[HeldoutACOutcomeRow] = []
    for settled in rows:
        authenticated = settled.authenticated_row
        result = authenticated.result
        usage = authenticated.usage_evidence.usage
        if result.evaluation_status == "completed":
            outcome: Any = EvaluatorCompletedOutcome(
                kind="evaluator_completed",
                terminal_outcome=True,
                trace_qualified=True,
                cost_settled=True,
                durable_usage_reconciled=True,
                matrix_inconclusive_triggers=[],
                evaluator_v2_runtime_authenticated=True,
                evaluator_v2_completion_eligible=True,
                hidden_verdict=result.verdicts.hidden_tests.value.upper(),
                regression_verdict=result.verdicts.regression_tests.value.upper(),
                scope_verdict=result.verdicts.scope_policy.value.upper(),
                safety_verdict=result.verdicts.safety_policy.value.upper(),
            )
        else:
            if settled.terminal_type is None:
                raise HeldoutACDispatcherError(
                    "held-out agent terminal has no typed classification"
                )
            outcome = TypedAgentTerminalOutcome(
                kind="typed_pre_evaluator_agent_terminal",
                terminal_outcome=True,
                trace_qualified=True,
                cost_settled=True,
                durable_usage_reconciled=True,
                matrix_inconclusive_triggers=[],
                evaluator_not_run=True,
                terminal_type=settled.terminal_type,
            )
        projected.append(
            HeldoutACOutcomeRow(
                order=authenticated.order,
                task_id=authenticated.task_id,
                role=authenticated.role,
                condition=authenticated.condition,
                repetition=authenticated.repetition,
                outcome=outcome,
                usage=HeldoutACUsage(
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    reasoning_tokens=usage.reasoning_output_tokens,
                    total_tokens=usage.input_tokens + usage.output_tokens,
                    model_cost_nanos=(authenticated.usage_evidence.token_derived_cost_nanos),
                    model_calls=usage.model_calls,
                    tool_calls=usage.tool_calls,
                    wall_time_milliseconds=usage.wall_clock_ms,
                ),
            )
        )
    return HeldoutACOutcomeProjection(
        schema_version="heldout-ac-outcome-projection-v1",
        preregistration_id="core-ac-fixed-bundle-heldout-20260814-v1",
        preregistration_content_hash=(
            "sha256:3b75f049649850b7561f310229e1e5429f72ea24024e835ccf4910fb2c901f74"
        ),
        rows=projected,
    )


def _confound_trigger(exc: Exception) -> MatrixConfound:
    text = str(exc).lower()
    if "marker" in text or "leak" in text:
        return "private-marker-or-leakage-hit"
    if "already" in text or "duplicate" in text or "resume" in text or "retry" in text:
        return "duplicate-retried-replaced-or-resumed-row"
    if "usage" in text or "settle" in text or "cost" in text:
        return "missing-durable-usage-or-cost-settlement"
    if "schedule" in text or "manifest" in text or "source" in text or "plan" in text:
        return "schedule-treatment-runtime-source-or-hash-drift"
    if "qualification" in text or "receipt" in text or "contract" in text:
        return "qualification-or-completion-contract-mismatch"
    return "provider-sdk-docker-or-evaluator-infrastructure-error"


def _record_confound(
    *,
    candidate: HeldoutACExecutionCandidate,
    journal_path: Path,
    row: Any,
    run_id: str,
    exc: Exception,
    phase: ConfoundPhase,
    run_started_event_written: bool,
) -> tuple[HeldoutACCampaignConfound, list[HeldoutACNotStartedRow]]:
    trigger = _confound_trigger(exc)
    confound_body = {
        "schema_version": CONFOUND_SCHEMA_VERSION,
        "order": row.order,
        "schedule_row_id": row.schedule_row_id,
        "task_id": row.task_id,
        "run_id": run_id,
        "trigger": trigger,
        "phase": phase,
        "exception_type": type(exc).__name__,
        "run_started_event_written": run_started_event_written,
        "secret_or_exception_message_persisted": False,
    }
    confound = HeldoutACCampaignConfound(
        **confound_body,
        content_hash=sha256_json(confound_body),
    )
    _append_journal(
        journal_path,
        "RunConfounded",
        {
            **_row_identity(row),
            "run_id": run_id,
            "execution_hash": candidate.execution_hash,
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
            "trigger": trigger,
            "phase": phase,
            "run_started_event_written": run_started_event_written,
            "confound_content_hash": confound.content_hash,
            "exception_message_persisted": False,
        },
    )
    not_started: list[HeldoutACNotStartedRow] = []
    for remaining in candidate.schedule[row.order :]:
        not_started_row = HeldoutACNotStartedRow(
            schema_version=NOT_STARTED_SCHEMA_VERSION,
            order=remaining.order,
            schedule_row_id=remaining.schedule_row_id,
            task_id=remaining.task_id,
            role=remaining.role,
            condition=remaining.condition,
            repetition=remaining.repetition,
            reason="campaign-stopped-after-prespecified-confound",
            trigger=trigger,
        )
        not_started.append(not_started_row)
        _append_journal(
            journal_path,
            "RunNotStarted",
            {
                **_row_identity(remaining),
                "execution_hash": candidate.execution_hash,
                "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
                "reason": "campaign-stopped-after-prespecified-confound",
                "trigger": trigger,
            },
        )
    return confound, not_started


def _prepared_result(
    *,
    candidate: HeldoutACExecutionCandidate,
    plan_path: Path,
    plan_hash: str,
    journal_path: Path,
    settled: list[HeldoutACSettledCampaignRow],
    confound: HeldoutACCampaignConfound | None,
    not_started: list[HeldoutACNotStartedRow],
) -> tuple[dict[str, Any], HeldoutACOutcomeProjection | None, HeldoutACAnalysis | None]:
    for index, settled_row in enumerate(settled, start=1):
        authenticated = settled_row.authenticated_row
        expected = candidate.schedule[index - 1]
        evaluator_contract = authenticated.result.evaluator_contract
        evaluator_completed = authenticated.result.evaluation_status == "completed"
        if not (
            authenticated.order == expected.order
            and authenticated.wave == expected.wave
            and authenticated.task_id == expected.task_id
            and authenticated.role == expected.role
            and authenticated.condition == expected.condition
            and authenticated.repetition == expected.repetition
            and authenticated.schedule_row_id == expected.schedule_row_id
            and authenticated.execution_hash == candidate.execution_hash
            and authenticated.usage_evidence.schedule_row_id == expected.schedule_row_id
            and authenticated.usage_evidence.pricing_binding_hash == candidate.pricing_binding_hash
            and evaluator_contract is not None
            and evaluator_contract.task_id == expected.task_id
            and evaluator_contract.evaluator_source_hash
            == candidate.source_qualification.evaluator_source_hash
            and (
                (
                    evaluator_completed
                    and authenticated.evaluator_v2_receipt_hash is not None
                    and authenticated.evaluator_v2_receipt_file_hash is not None
                    and settled_row.terminal_type is None
                )
                or (
                    not evaluator_completed
                    and authenticated.evaluator_v2_receipt_hash is None
                    and authenticated.evaluator_v2_receipt_file_hash is None
                    and settled_row.terminal_type is not None
                )
            )
        ):
            raise HeldoutACDispatcherError(
                f"authenticated held-out row differs from candidate at order {index}"
            )
    if confound is not None:
        expected_confound = candidate.schedule[confound.order - 1]
        if (
            confound.schedule_row_id != expected_confound.schedule_row_id
            or confound.task_id != expected_confound.task_id
        ):
            raise HeldoutACDispatcherError("held-out confound belongs to another schedule row")
    for item in not_started:
        expected_not_started = candidate.schedule[item.order - 1]
        if (
            item.schedule_row_id,
            item.task_id,
            item.role,
            item.condition,
            item.repetition,
        ) != (
            expected_not_started.schedule_row_id,
            expected_not_started.task_id,
            expected_not_started.role,
            expected_not_started.condition,
            expected_not_started.repetition,
        ):
            raise HeldoutACDispatcherError("held-out not-started row differs from the schedule")
    projection = _analysis_projection(settled) if len(settled) == 48 and confound is None else None
    analysis = analyze_heldout_ac(projection) if projection is not None else None
    disposition = "complete-matrix" if analysis is not None else "inconclusive-matrix"
    body = {
        "schema_version": PREPARED_RESULT_SCHEMA_VERSION,
        "evidence_status": "authenticated-persisted-campaign",
        "disposition": disposition,
        "suite_id": candidate.suite_id,
        "suite_content_hash": candidate.suite_content_hash,
        "execution_hash": candidate.execution_hash,
        "source_qualification_hash": candidate.source_qualification.source_qualification_hash,
        "evaluator_source_hash": candidate.source_qualification.evaluator_source_hash,
        "execution_plan_path": str(plan_path.resolve(strict=False)),
        "execution_plan_file_sha256": plan_hash,
        "journal_path": str(journal_path.resolve(strict=False)),
        "expected_runs": 48,
        "terminal_settled_runs": len(settled),
        "not_started_runs": len(not_started),
        "settled_model_cost_nanos": sum(
            row.authenticated_row.usage_evidence.token_derived_cost_nanos for row in settled
        ),
        "unsettled_dispatched_runs": int(
            confound is not None and confound.run_started_event_written
        ),
        "cost_accounting_complete": not (
            confound is not None and confound.run_started_event_written
        ),
        "full_schedule_reserve_nanos": 252_000_000_000,
        "hard_cap_nanos": 275_000_000_000,
        "settled_rows": [row.model_dump(mode="json") for row in settled],
        "confound": confound.model_dump(mode="json") if confound is not None else None,
        "not_started_rows": [row.model_dump(mode="json") for row in not_started],
        "outcome_projection": projection.model_dump(mode="json")
        if projection is not None
        else None,
        "analysis": analysis.model_dump(mode="json") if analysis is not None else None,
        "analysis_ready": analysis is not None,
        "official_heldout_analysis": analysis is not None,
        "memory_benefit_claim_authorized": False,
        "broad_generalization_claim_authorized": False,
        "retry_replacement_or_resume_performed": False,
    }
    return {**body, "content_hash": sha256_json(body)}, projection, analysis


def _finalize_result(
    *,
    candidate: HeldoutACExecutionCandidate,
    plan_path: Path,
    plan_hash: str,
    journal_path: Path,
    result_path: Path,
    settled: list[HeldoutACSettledCampaignRow],
    confound: HeldoutACCampaignConfound | None,
    not_started: list[HeldoutACNotStartedRow],
) -> HeldoutACCampaignResult:
    prepared, projection, analysis = _prepared_result(
        candidate=candidate,
        plan_path=plan_path,
        plan_hash=plan_hash,
        journal_path=journal_path,
        settled=settled,
        confound=confound,
        not_started=not_started,
    )
    prepared_path = result_path.with_name(f"{result_path.stem}.prepared.json")
    prepared_bytes = (
        json.dumps(prepared, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    _write_new(prepared_path, prepared_bytes)
    completed = _append_journal(
        journal_path,
        "CampaignCompleted",
        {
            "suite_id": candidate.suite_id,
            "execution_hash": candidate.execution_hash,
            "disposition": prepared["disposition"],
            "terminal_settled_runs": len(settled),
            "not_started_runs": len(not_started),
            "settled_model_cost_nanos": prepared["settled_model_cost_nanos"],
            "unsettled_dispatched_runs": prepared["unsettled_dispatched_runs"],
            "cost_accounting_complete": prepared["cost_accounting_complete"],
            "prepared_result_path": str(prepared_path.resolve(strict=False)),
            "prepared_result_file_sha256": sha256_bytes(prepared_bytes),
            "prepared_result_content_hash": prepared["content_hash"],
        },
    )
    journal_hash = sha256_bytes(journal_path.read_bytes())
    body = {
        **{
            key: value
            for key, value in prepared.items()
            if key not in {"schema_version", "content_hash"}
        },
        "schema_version": CAMPAIGN_RESULT_SCHEMA_VERSION,
        "journal_file_sha256": journal_hash,
        "campaign_completed_event_hash": completed["event_hash"],
        "prepared_result_path": str(prepared_path.resolve(strict=False)),
        "prepared_result_file_sha256": sha256_bytes(prepared_bytes),
        "prepared_result_content_hash": prepared["content_hash"],
    }
    result_payload = {**body, "content_hash": sha256_json(body)}
    result = HeldoutACCampaignResult.model_validate_json(
        json.dumps(result_payload, sort_keys=True, ensure_ascii=False)
    )
    result_bytes = (result.model_dump_json(indent=2) + "\n").encode("utf-8")
    _write_new(result_path, result_bytes)
    return result


def validate_heldout_ac_campaign_result(
    *,
    execution_hash: str,
    root: str | Path | None = None,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Replay the persisted plan, rows, journal, prepared result, and final result."""

    run_root = _root(root)
    repo = _repository(repository)
    plan, plan_bytes = _load_approved_plan(execution_hash, run_root)
    candidate = _candidate_from_mapping(plan["candidate"])
    if not heldout_ac_candidate_has_current_source_binding(candidate, repository=repo):
        raise HeldoutACDispatcherError("held-out result candidate source qualification differs")
    result_path = Path(str(plan["result_path"])).resolve(strict=False)
    expected_result_path = (
        run_root / "experiments" / "heldout-ac" / f"{execution_hash[7:]}.json"
    ).resolve(strict=False)
    try:
        result_bytes = result_path.read_bytes()
        result = HeldoutACCampaignResult.model_validate_json(result_bytes)
    except (OSError, ValidationError) as exc:
        raise HeldoutACDispatcherError("held-out campaign result is invalid") from exc
    if (
        result_path != expected_result_path
        or result_path.is_symlink()
        or result_bytes != (result.model_dump_json(indent=2) + "\n").encode("utf-8")
    ):
        raise HeldoutACDispatcherError("held-out campaign result bytes differ")
    plan_path = (run_root / "experiments" / "plans" / f"{execution_hash[7:]}.json").resolve(
        strict=False
    )
    journal_path = Path(result.journal_path).resolve(strict=False)
    prepared_path = Path(result.prepared_result_path).resolve(strict=False)
    expected_prepared_path = result_path.with_name(f"{result_path.stem}.prepared.json")
    try:
        prepared_bytes = prepared_path.read_bytes()
        prepared = json.loads(prepared_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeldoutACDispatcherError("held-out prepared result is invalid") from exc
    if not isinstance(prepared, dict):
        raise HeldoutACDispatcherError("held-out prepared result is not an object")
    prepared_body = {key: value for key, value in prepared.items() if key != "content_hash"}
    expected_prepared, _projection, _analysis = _prepared_result(
        candidate=candidate,
        plan_path=plan_path,
        plan_hash=sha256_bytes(plan_bytes),
        journal_path=journal_path,
        settled=list(result.settled_rows),
        confound=result.confound,
        not_started=list(result.not_started_rows),
    )
    canonical_prepared = (
        json.dumps(prepared, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    if not (
        prepared_path == expected_prepared_path
        and prepared_path.is_symlink() is False
        and prepared_bytes == canonical_prepared
        and prepared.get("content_hash") == sha256_json(prepared_body)
        and _exact_typed_equal(prepared, expected_prepared)
        and result.prepared_result_file_sha256 == sha256_bytes(prepared_bytes)
        and result.prepared_result_content_hash == prepared["content_hash"]
    ):
        raise HeldoutACDispatcherError("held-out prepared result replay differs")

    events, journal_bytes = _load_journal_events(journal_path)
    expected_started = {
        "suite_id": candidate.suite_id,
        "suite_content_hash": candidate.suite_content_hash,
        "execution_hash": candidate.execution_hash,
        "execution_plan_file_sha256": sha256_bytes(plan_bytes),
        "schedule_hash": candidate.schedule_hash,
        "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
        "expected_runs": 48,
    }
    expected_reserved = {
        "suite_id": candidate.suite_id,
        "execution_hash": candidate.execution_hash,
        "execution_plan_file_sha256": sha256_bytes(plan_bytes),
        "schedule_hash": candidate.schedule_hash,
        "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
        "reserved_runs": 48,
        "per_run_reserve_nanos": 5_250_000_000,
        "full_schedule_reserve_nanos": 252_000_000_000,
        "hard_cap_nanos": 275_000_000_000,
        "cost_censoring_allowed": False,
    }
    if not (
        len(events) >= 3
        and events[0]["event_type"] == "CampaignStarted"
        and _exact_typed_equal(events[0]["payload"], expected_started)
        and events[1]["event_type"] == "FullScheduleCostReserved"
        and _exact_typed_equal(events[1]["payload"], expected_reserved)
    ):
        raise HeldoutACDispatcherError("held-out campaign opening journal differs")

    cursor = 2
    accrued = 0
    for settled in result.settled_rows:
        authenticated = settled.authenticated_row
        row = candidate.schedule[authenticated.order - 1]
        if len(events) < cursor + 3:
            raise HeldoutACDispatcherError("held-out settled journal row is absent")
        start_event, terminal_event, cost_event = events[cursor : cursor + 3]
        terminal_payload = terminal_event["payload"]
        relative = terminal_payload.get("authenticated_row_path")
        if not isinstance(relative, str):
            raise HeldoutACDispatcherError("held-out terminal row path is absent")
        row_path = (run_root / relative).resolve(strict=False)
        try:
            row_bytes = row_path.read_bytes()
            persisted_row = HeldoutACAuthenticatedPersistedRow.model_validate_json(row_bytes)
        except (OSError, ValidationError) as exc:
            raise HeldoutACDispatcherError("held-out authenticated row file is invalid") from exc
        cost = authenticated.usage_evidence.token_derived_cost_nanos
        expected_start = {
            **_row_identity(row),
            "run_id": authenticated.run_id,
            "execution_hash": candidate.execution_hash,
            "execution_plan_file_sha256": sha256_bytes(plan_bytes),
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
        }
        expected_terminal = {
            **_row_identity(row),
            "run_id": authenticated.run_id,
            "execution_hash": candidate.execution_hash,
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
            "authenticated_row_path": relative,
            "authenticated_row_file_sha256": sha256_bytes(row_bytes),
            "authenticated_row_content_hash": authenticated.content_hash,
            "result_outcome_kind": authenticated.result.outcome_kind.value,
            "evaluation_status": authenticated.result.evaluation_status,
            "qualification_hash": authenticated.qualification_hash,
            "source_evidence_hash": authenticated.source_evidence_hash,
            "actual_run_cost_nanos": cost,
        }
        expected_cost = {
            "order": row.order,
            "schedule_row_id": row.schedule_row_id,
            "run_id": authenticated.run_id,
            "execution_hash": candidate.execution_hash,
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
            "authenticated_row_file_sha256": sha256_bytes(row_bytes),
            "authenticated_row_content_hash": authenticated.content_hash,
            "actual_run_cost_nanos": cost,
            "accrued_cost_nanos_before": accrued,
            "accrued_cost_nanos_after": accrued + cost,
            "remaining_reserved_rows_after": 48 - row.order,
        }
        if not (
            len(events) >= cursor + 3
            and start_event["event_type"] == "RunStarted"
            and _exact_typed_equal(start_event["payload"], expected_start)
            and terminal_event["event_type"] == "RunTerminal"
            and _exact_typed_equal(terminal_payload, expected_terminal)
            and cost_event["event_type"] == "RunCostSettled"
            and _exact_typed_equal(cost_event["payload"], expected_cost)
            and row_path.is_relative_to(run_root)
            and row_path.is_symlink() is False
            and persisted_row == authenticated
            and row_bytes == authenticated.model_dump_json(indent=2).encode("utf-8")
        ):
            raise HeldoutACDispatcherError("held-out settled journal row differs")
        accrued += cost
        cursor += 3

    if result.confound is not None:
        confound = result.confound
        row = candidate.schedule[confound.order - 1]
        if confound.run_started_event_written:
            if len(events) <= cursor:
                raise HeldoutACDispatcherError("held-out confounded row start is absent")
            expected_start = {
                **_row_identity(row),
                "run_id": confound.run_id,
                "execution_hash": candidate.execution_hash,
                "execution_plan_file_sha256": sha256_bytes(plan_bytes),
                "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
            }
            if not (
                events[cursor]["event_type"] == "RunStarted"
                and _exact_typed_equal(events[cursor]["payload"], expected_start)
            ):
                raise HeldoutACDispatcherError("held-out confounded row start differs")
            cursor += 1
        expected_confound = {
            **_row_identity(row),
            "run_id": confound.run_id,
            "execution_hash": candidate.execution_hash,
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
            "trigger": confound.trigger,
            "phase": confound.phase,
            "run_started_event_written": confound.run_started_event_written,
            "confound_content_hash": confound.content_hash,
            "exception_message_persisted": False,
        }
        if len(events) <= cursor:
            raise HeldoutACDispatcherError("held-out confound journal event is absent")
        if not (
            events[cursor]["event_type"] == "RunConfounded"
            and _exact_typed_equal(events[cursor]["payload"], expected_confound)
        ):
            raise HeldoutACDispatcherError("held-out confound journal event differs")
        cursor += 1
        for item in result.not_started_rows:
            row = candidate.schedule[item.order - 1]
            expected_not_started = {
                **_row_identity(row),
                "execution_hash": candidate.execution_hash,
                "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
                "reason": item.reason,
                "trigger": item.trigger,
            }
            if len(events) <= cursor:
                raise HeldoutACDispatcherError("held-out not-started journal row is absent")
            if not (
                events[cursor]["event_type"] == "RunNotStarted"
                and _exact_typed_equal(events[cursor]["payload"], expected_not_started)
            ):
                raise HeldoutACDispatcherError("held-out not-started journal row differs")
            cursor += 1

    completed_payload = {
        "suite_id": candidate.suite_id,
        "execution_hash": candidate.execution_hash,
        "disposition": result.disposition,
        "terminal_settled_runs": result.terminal_settled_runs,
        "not_started_runs": result.not_started_runs,
        "settled_model_cost_nanos": result.settled_model_cost_nanos,
        "unsettled_dispatched_runs": result.unsettled_dispatched_runs,
        "cost_accounting_complete": result.cost_accounting_complete,
        "prepared_result_path": str(prepared_path),
        "prepared_result_file_sha256": sha256_bytes(prepared_bytes),
        "prepared_result_content_hash": prepared["content_hash"],
    }
    if not (
        len(events) > cursor
        and cursor == len(events) - 1
        and events[cursor]["event_type"] == "CampaignCompleted"
        and _exact_typed_equal(events[cursor]["payload"], completed_payload)
        and result.campaign_completed_event_hash == events[cursor]["event_hash"]
        and result.journal_file_sha256 == sha256_bytes(journal_bytes)
    ):
        raise HeldoutACDispatcherError("held-out campaign completion journal differs")

    final_body = {
        **{
            key: value
            for key, value in prepared.items()
            if key not in {"schema_version", "content_hash"}
        },
        "schema_version": CAMPAIGN_RESULT_SCHEMA_VERSION,
        "journal_file_sha256": sha256_bytes(journal_bytes),
        "campaign_completed_event_hash": events[cursor]["event_hash"],
        "prepared_result_path": str(prepared_path),
        "prepared_result_file_sha256": sha256_bytes(prepared_bytes),
        "prepared_result_content_hash": prepared["content_hash"],
    }
    expected_final = {**final_body, "content_hash": sha256_json(final_body)}
    if not _exact_typed_equal(result.model_dump(mode="json"), expected_final):
        raise HeldoutACDispatcherError("held-out final result projection differs")
    return {
        "disposition": result.disposition,
        "execution_hash": result.execution_hash,
        "terminal_settled_runs": result.terminal_settled_runs,
        "not_started_runs": result.not_started_runs,
        "settled_model_cost_nanos": result.settled_model_cost_nanos,
        "cost_accounting_complete": result.cost_accounting_complete,
        "analysis_ready": result.analysis_ready,
        "official_heldout_analysis": result.official_heldout_analysis,
        "result_file_sha256": sha256_bytes(result_bytes),
        "journal_file_sha256": sha256_bytes(journal_bytes),
        "provider_calls_made_by_validation": 0,
    }


def run_heldout_ac_campaign(
    *,
    execution_hash: str,
    env_file: str | Path,
    root: str | Path | None = None,
    repository: str | Path | None = None,
) -> HeldoutACCampaignResult:
    """Run the exact approved 48-row schedule once; no retry or resume is exposed."""

    run_root = _root(root)
    repo = _repository(repository)
    plan, plan_bytes = _load_approved_plan(execution_hash, run_root)
    candidate = _candidate_from_mapping(plan["candidate"])
    if not heldout_ac_candidate_has_current_source_binding(
        candidate,
        repository=repo,
    ):
        raise HeldoutACDispatcherError(
            "held-out candidate source qualification differs at dispatch"
        )
    plan_path = run_root / "experiments" / "plans" / f"{execution_hash[7:]}.json"
    journal_path = Path(plan["journal_path"])
    result_path = Path(plan["result_path"])
    if journal_path.exists() or result_path.exists():
        raise HeldoutACDispatcherError("held-out campaign cannot retry or resume existing state")
    plan_hash = sha256_bytes(plan_bytes)
    settled: list[HeldoutACSettledCampaignRow] = []
    confound: HeldoutACCampaignConfound | None = None
    not_started: list[HeldoutACNotStartedRow] = []
    current_phase: ConfoundPhase = "row-dispatch"
    _create_journal(journal_path, candidate, plan_hash)

    def seal_pre_row_failure(exc: Exception) -> HeldoutACCampaignResult:
        first_row = candidate.schedule[0]
        pre_row_confound, remaining = _record_confound(
            candidate=candidate,
            journal_path=journal_path,
            row=first_row,
            run_id=make_run_id("heldout"),
            exc=exc,
            phase="row-dispatch",
            run_started_event_written=False,
        )
        return _finalize_result(
            candidate=candidate,
            plan_path=plan_path,
            plan_hash=plan_hash,
            journal_path=journal_path,
            result_path=result_path,
            settled=[],
            confound=pre_row_confound,
            not_started=remaining,
        )

    try:
        try:
            installed_sdk = version("openai")
        except PackageNotFoundError as exc:
            raise HeldoutACDispatcherError("held-out OpenAI SDK is unavailable") from exc
        if installed_sdk != candidate.readiness.openai_sdk.version:
            raise HeldoutACDispatcherError("held-out OpenAI SDK version differs from the candidate")
        if os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE"):
            raise HeldoutACDispatcherError("custom OpenAI base URLs are forbidden")
        exact_openai_api_key_present(env_file)
        authorization = issue_live_execution_authorization(execution_hash, root=run_root)
        runner = AgentRunner(root=run_root)
    except Exception as exc:
        return seal_pre_row_failure(exc)

    with exact_openai_api_key_environment(env_file):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not isinstance(api_key, str) or not api_key:
            raise HeldoutACDispatcherError("held-out runtime credential was not installed")
        for row in candidate.schedule:
            run_id = make_run_id("heldout")
            task_dir = repo / row.task_path
            run_started_event_written = False
            current_phase = "row-dispatch"
            try:
                package = load_task_package(task_dir)
                runtime_authority = materialize_heldout_ac_runtime_task_authority(
                    candidate=candidate,
                    task_id=row.task_id,
                    package=package,
                    api_key=api_key,
                    repository=repo,
                )
                manifest = build_heldout_ac_run_manifest(
                    candidate=candidate,
                    row_order=row.order,
                    run_id=run_id,
                    created_at=utc_now(),
                    authority=runtime_authority,
                )
                _append_journal(
                    journal_path,
                    "RunStarted",
                    {
                        **_row_identity(row),
                        "run_id": run_id,
                        "execution_hash": candidate.execution_hash,
                        "execution_plan_file_sha256": plan_hash,
                        "campaign_cost_control_hash": (
                            candidate.campaign_cost_control.content_hash
                        ),
                    },
                )
                run_started_event_written = True
                current_phase = "row-dispatch"
                runner.start(
                    task_dir,
                    model="openai",
                    manifest=manifest,
                    live_authorization=authorization,
                    evaluator_v2_authority=runtime_authority.qualification_authority,
                )
                current_phase = "qualification"
                authenticated = _persist_usage_and_authenticate(
                    candidate=candidate,
                    order=row.order,
                    run_id=run_id,
                    run_root=run_root,
                    repository=repo,
                    task_dir=task_dir,
                    authority=runtime_authority,
                )
                current_phase = "authentication"
                settled_row = _settled_row(authenticated, run_root=run_root)
                accrued_before = sum(
                    item.authenticated_row.usage_evidence.token_derived_cost_nanos
                    for item in settled
                )
                cost = _validate_settlement_limits(
                    authenticated,
                    accrued_before=accrued_before,
                )
                row_path = (
                    run_root
                    / "experiments"
                    / "heldout-ac"
                    / "rows"
                    / candidate.execution_hash[7:]
                    / f"{row.order:02d}-{run_id}-authenticated.json"
                )
                row_bytes = authenticated.model_dump_json(indent=2).encode("utf-8")
                _write_new(row_path, row_bytes)
                relative = row_path.relative_to(run_root).as_posix()
                _append_journal(
                    journal_path,
                    "RunTerminal",
                    {
                        **_row_identity(row),
                        "run_id": run_id,
                        "execution_hash": candidate.execution_hash,
                        "campaign_cost_control_hash": (
                            candidate.campaign_cost_control.content_hash
                        ),
                        "authenticated_row_path": relative,
                        "authenticated_row_file_sha256": sha256_bytes(row_bytes),
                        "authenticated_row_content_hash": authenticated.content_hash,
                        "result_outcome_kind": authenticated.result.outcome_kind.value,
                        "evaluation_status": authenticated.result.evaluation_status,
                        "qualification_hash": authenticated.qualification_hash,
                        "source_evidence_hash": authenticated.source_evidence_hash,
                        "actual_run_cost_nanos": cost,
                    },
                )
                current_phase = "settlement"
                _append_journal(
                    journal_path,
                    "RunCostSettled",
                    {
                        "order": row.order,
                        "schedule_row_id": row.schedule_row_id,
                        "run_id": run_id,
                        "execution_hash": candidate.execution_hash,
                        "campaign_cost_control_hash": (
                            candidate.campaign_cost_control.content_hash
                        ),
                        "authenticated_row_file_sha256": sha256_bytes(row_bytes),
                        "authenticated_row_content_hash": authenticated.content_hash,
                        "actual_run_cost_nanos": cost,
                        "accrued_cost_nanos_before": accrued_before,
                        "accrued_cost_nanos_after": accrued_before + cost,
                        "remaining_reserved_rows_after": 48 - row.order,
                    },
                )
                settled.append(settled_row)
            except Exception as exc:
                confound, not_started = _record_confound(
                    candidate=candidate,
                    journal_path=journal_path,
                    row=row,
                    run_id=run_id,
                    exc=exc,
                    phase=current_phase,
                    run_started_event_written=run_started_event_written,
                )
                break

    return _finalize_result(
        candidate=candidate,
        plan_path=plan_path,
        plan_hash=plan_hash,
        journal_path=journal_path,
        result_path=result_path,
        settled=settled,
        confound=confound,
        not_started=not_started,
    )


__all__ = [
    "CAMPAIGN_RESULT_SCHEMA_VERSION",
    "HeldoutACCampaignConfound",
    "HeldoutACCampaignResult",
    "HeldoutACDispatcherError",
    "HeldoutACNotStartedRow",
    "HeldoutACSettledCampaignRow",
    "prepare_heldout_ac_approved_plan",
    "run_heldout_ac_campaign",
    "validate_heldout_ac_campaign_result",
]
