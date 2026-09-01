from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from patchloop.agent import runner as runner_module
from patchloop.agent.runner import (
    AgentRunner,
    BatchExecutionAuthorization,
    RowExecutionAuthorization,
    batch_execution_authorization_receipt,
)
from patchloop.contracts import EventType, RunOutcomeKind, RunResult, RunStatus, Usage, Verdicts
from patchloop.errors import ContractError, RecoveryError
from patchloop.evals import rapid_batch_driver as driver_module
from patchloop.evals import rapid_public_development_v19 as rapid
from patchloop.evals.rapid_batch_driver import (
    RapidBatchDriverContract,
    begin_rapid_batch_driver,
    build_rapid_batch_driver_contract,
    build_rapid_batch_driver_terminal_parity_contract,
    close_interrupted_rapid_batch_driver,
    decide_rapid_driver_row_continuation,
    issue_persisted_rapid_driver_next_row,
    load_rapid_batch_driver_journal,
    record_rapid_driver_row_terminal,
    run_append_only_rapid_batch_driver,
)
from patchloop.evals.rapid_public_development import _usage_cost_nanos
from patchloop.evals.rapid_public_development_v4 import _rapid_v4_row_projection
from patchloop.util import sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _manifests(count: int = 2) -> tuple[Any, ...]:
    candidate = rapid.load_consumed_rapid_public_development_v19_candidate(REPOSITORY)
    return tuple(
        rapid.build_rapid_v19_run_manifest(candidate, order, repository=REPOSITORY)
        for order in range(1, count + 1)
    )


def _schedule_rows(count: int = 2) -> tuple[dict[str, Any], ...]:
    candidate = rapid.load_consumed_rapid_public_development_v19_candidate(REPOSITORY)
    return tuple(candidate["schedule"][:count])


def _fresh_batch(manifests: tuple[Any, ...]) -> BatchExecutionAuthorization:
    first = manifests[0]
    assert first.experiment is not None
    return BatchExecutionAuthorization(
        authority_kind="live",
        execution_hash=first.experiment.execution_hash,
        plan_hash=sha256_json("driver-plan"),
        runtime_build_hash=sha256_json("driver-runtime"),
        schedule_hash=sha256_json("driver-schedule"),
        cost_control_hash=sha256_json("driver-cost"),
        manifest_hashes=tuple(
            sha256_json(manifest.model_dump(mode="json")) for manifest in manifests
        ),
        _state=runner_module._BatchExecutionAuthorizationState(),
        _guard=runner_module._BATCH_EXECUTION_AUTHORIZATION_GUARD,
    )


def _contract(
    manifests: tuple[Any, ...],
    batch: BatchExecutionAuthorization,
) -> RapidBatchDriverContract:
    experiment = manifests[0].experiment
    assert experiment is not None
    return build_rapid_batch_driver_terminal_parity_contract(
        experiment_id=experiment.experiment_id,
        manifests=manifests,
        batch_authorization=batch,
        row_reserve_nanos=rapid.PER_RUN_RESERVE_NANOS,
        full_schedule_reserve_nanos=rapid.PER_RUN_RESERVE_NANOS * len(manifests),
        hard_cap_nanos=rapid.PER_RUN_RESERVE_NANOS * len(manifests) + 300_000_000,
    )


def _predecessor_contract(
    manifests: tuple[Any, ...],
    batch: BatchExecutionAuthorization,
) -> RapidBatchDriverContract:
    experiment = manifests[0].experiment
    assert experiment is not None
    return build_rapid_batch_driver_contract(
        experiment_id=experiment.experiment_id,
        manifests=manifests,
        batch_authorization=batch,
        row_reserve_nanos=rapid.PER_RUN_RESERVE_NANOS,
        full_schedule_reserve_nanos=rapid.PER_RUN_RESERVE_NANOS * len(manifests),
        hard_cap_nanos=rapid.PER_RUN_RESERVE_NANOS * len(manifests) + 300_000_000,
    )


def _consume_for_dispatch(authorization: RowExecutionAuthorization) -> None:
    with authorization._state.lock:
        authorization._state.consumed = True
        authorization._state.provider_dispatch_started = True


@pytest.mark.parametrize(
    ("contract_factory", "expected_policy"),
    (
        (_predecessor_contract, "append-only-row-settlement-driver-v1"),
        (_contract, "append-only-row-settlement-driver-v2"),
    ),
)
def test_journal_serializes_the_selected_contract_policy(
    tmp_path: Path,
    contract_factory: Callable[
        [tuple[Any, ...], BatchExecutionAuthorization], RapidBatchDriverContract
    ],
    expected_policy: str,
) -> None:
    manifests = _manifests(1)
    batch = _fresh_batch(manifests)
    contract = contract_factory(manifests, batch)
    journal = tmp_path / "driver.jsonl"

    begin_rapid_batch_driver(
        journal_path=journal,
        contract=contract,
        manifests=manifests,
        batch_authorization=batch,
    )
    events = load_rapid_batch_driver_journal(journal, contract)

    assert contract.policy_version == expected_policy
    assert {event["driver_policy_version"] for event in events} == {expected_policy}
    assert {event["driver_contract_hash"] for event in events} == {contract.content_hash}


@pytest.mark.parametrize(
    ("contract_factory", "tampered_policy"),
    (
        (_predecessor_contract, "append-only-row-settlement-driver-v2"),
        (_contract, "append-only-row-settlement-driver-v1"),
    ),
)
def test_rehashed_cross_policy_label_fails_closed(
    tmp_path: Path,
    contract_factory: Callable[
        [tuple[Any, ...], BatchExecutionAuthorization], RapidBatchDriverContract
    ],
    tampered_policy: str,
) -> None:
    manifests = _manifests(1)
    batch = _fresh_batch(manifests)
    contract = contract_factory(manifests, batch)
    journal = tmp_path / "driver.jsonl"
    begin_rapid_batch_driver(
        journal_path=journal,
        contract=contract,
        manifests=manifests,
        batch_authorization=batch,
    )
    events = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
    previous: str | None = None
    rehashed: list[dict[str, Any]] = []
    for event in events:
        body = {key: value for key, value in event.items() if key != "content_hash"}
        body["driver_policy_version"] = tampered_policy
        body["previous_event_hash"] = previous
        sealed = {**body, "content_hash": sha256_json(body)}
        rehashed.append(sealed)
        previous = sealed["content_hash"]
    journal.write_text(
        "\n".join(json.dumps(event) for event in rehashed) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RecoveryError, match="contract binding differs"):
        load_rapid_batch_driver_journal(journal, contract)


def _result(manifest: Any, outcome: RunOutcomeKind) -> RunResult:
    usage = Usage(input_tokens=100, output_tokens=20, model_calls=2, tool_calls=3)
    usage.model_cost_usd = _usage_cost_nanos(usage) / 1_000_000_000
    if outcome == RunOutcomeKind.INFRASTRUCTURE_ERROR:
        return RunResult(
            run_id=manifest.run_id,
            agent_submission_status="failed",
            evaluation_status="not_run",
            scope_compliant_success=False,
            official=False,
            verdicts=Verdicts(),
            usage=usage,
            outcome_kind=outcome,
            terminal_error={
                "type": "RecoveryError",
                "message": "sanitized public terminal",
                "code": "RECOVERY_ERROR",
            },
        )
    return RunResult(
        run_id=manifest.run_id,
        agent_submission_status="completed",
        evaluation_status="completed",
        scope_compliant_success=outcome == RunOutcomeKind.RESOLVED,
        official=False,
        verdicts=Verdicts(),
        usage=usage,
        outcome_kind=outcome,
    )


def _persist_terminal(
    runner: AgentRunner,
    manifest: Any,
    result: RunResult,
    *,
    tamper_provenance: bool = False,
    tamper_completed_payload: bool = False,
) -> None:
    runner.state.create_run(manifest)
    runner.state.set_run_status(manifest.run_id, RunStatus.RUNNING)
    failed = result.outcome_kind in {
        RunOutcomeKind.AGENT_FAILURE,
        RunOutcomeKind.INFRASTRUCTURE_ERROR,
    }
    if failed:
        payload = {
            "outcome_kind": result.outcome_kind.value,
            "error_type": (result.terminal_error.get("type") if result.terminal_error else None),
            "error_code": (result.terminal_error.get("code") if result.terminal_error else None),
        }
    else:
        payload = {
            "scope_compliant_success": (
                not result.scope_compliant_success
                if tamper_completed_payload
                else result.scope_compliant_success
            ),
            "official": result.official,
            "duration_ms": 1,
            "failure_classification_error": None,
        }
    runner.state.finalize_run(
        manifest.run_id,
        status=RunStatus.FAILED if failed else RunStatus.COMPLETED,
        result=result,
        event_type=EventType.RUN_FAILED if failed else EventType.RUN_COMPLETED,
        actor="runner" if failed else "evaluator",
        payload=payload,
    )
    workspace = runner.root / "workspaces" / manifest.run_id / "repo"
    workspace.mkdir(parents=True)
    if result.outcome_kind != RunOutcomeKind.INFRASTRUCTURE_ERROR:
        return
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
                "error_code": "TAMPERED" if tamper_provenance else "RECOVERY_ERROR",
            },
            indent=2,
        ),
    )


def _project(**kwargs: Any) -> dict[str, Any]:
    result = kwargs["result"]
    return _rapid_v4_row_projection(
        schedule_row=kwargs["schedule_row"],
        manifest=kwargs["manifest"],
        result=(result.model_dump(mode="json") if isinstance(result, RunResult) else result),
        runner=kwargs["runner"],
        error=kwargs["error"],
    )


def _executor(
    runner: AgentRunner,
    outcomes: tuple[RunOutcomeKind, ...],
    *,
    raise_after_persist: bool = False,
    tamper_provenance: bool = False,
    tamper_completed_payload: bool = False,
) -> Callable[..., RunResult]:
    calls = 0

    def execute(**kwargs: Any) -> RunResult:
        nonlocal calls
        manifest = kwargs["manifest"]
        authorization = kwargs["row_authorization"]
        _consume_for_dispatch(authorization)
        result = _result(manifest, outcomes[calls])
        calls += 1
        _persist_terminal(
            runner,
            manifest,
            result,
            tamper_provenance=tamper_provenance and calls == 1,
            tamper_completed_payload=tamper_completed_payload and calls == 1,
        )
        if raise_after_persist and calls == 1:
            raise RecoveryError("escaped runner failure")
        return result

    return execute


def _run(
    tmp_path: Path,
    *,
    outcomes: tuple[RunOutcomeKind, ...],
    execute_row: Callable[..., RunResult] | None = None,
    project_row: Callable[..., dict[str, Any]] = _project,
) -> tuple[
    dict[str, Any],
    tuple[dict[str, Any], ...],
    BatchExecutionAuthorization,
    AgentRunner,
]:
    manifests = _manifests(len(outcomes))
    batch = _fresh_batch(manifests)
    contract = _contract(manifests, batch)
    runner = AgentRunner(tmp_path / ".patchloop")
    journal = tmp_path / "driver.jsonl"
    terminal = run_append_only_rapid_batch_driver(
        journal_path=journal,
        contract=contract,
        manifests=manifests,
        schedule_rows=_schedule_rows(len(outcomes)),
        runner=runner,
        batch_authorization=batch,
        execute_row=execute_row or _executor(runner, outcomes),
        project_row=project_row,
    )
    return terminal, load_rapid_batch_driver_journal(journal, contract), batch, runner


def test_eligible_returned_infrastructure_row_advances_only_after_persisted_decision(
    tmp_path: Path,
) -> None:
    terminal, events, batch, _ = _run(
        tmp_path,
        outcomes=(RunOutcomeKind.INFRASTRUCTURE_ERROR, RunOutcomeKind.TASK_FAILURE),
    )

    assert terminal["event"] == "batch-completed"
    assert terminal["terminal_row_count"] == 2
    assert terminal["cost_fully_settled"] is True
    kinds = [event["event"] for event in events]
    assert kinds == [
        "batch-started",
        "row-capability-issued",
        "row-terminal",
        "row-settlement-evidence",
        "row-decision",
        "row-capability-issued",
        "row-terminal",
        "row-decision",
        "batch-completed",
    ]
    decision = events[4]
    grant = events[5]
    assert decision["decision"] == "continue"
    assert decision["decision_source"] == "row-local-infrastructure-gateway"
    assert decision["schedule_advanced"] is False
    assert grant["source_decision_event_hash"] == decision["content_hash"]
    assert grant["issuance_kind"] == "row-local-infrastructure"
    assert batch_execution_authorization_receipt(batch)["next_order"] == 3


def test_settled_ordinary_terminal_uses_the_same_decision_before_grant_order(
    tmp_path: Path,
) -> None:
    terminal, events, batch, runner = _run(
        tmp_path,
        outcomes=(RunOutcomeKind.TASK_FAILURE, RunOutcomeKind.TASK_FAILURE),
    )

    assert terminal["event"] == "batch-completed"
    assert [event["event"] for event in events] == [
        "batch-started",
        "row-capability-issued",
        "row-terminal",
        "row-decision",
        "row-capability-issued",
        "row-terminal",
        "row-decision",
        "batch-completed",
    ]
    decision = events[3]
    grant = events[4]
    assert decision["decision_source"] == "ordinary-terminal"
    assert decision["decision"] == "continue"
    assert grant["source_decision_event_hash"] == decision["content_hash"]
    assert grant["issuance_kind"] == "ordinary"
    assert batch_execution_authorization_receipt(batch)["next_order"] == 3
    for manifest in _manifests(2):
        completed = [
            event
            for event in runner.state.list_events(manifest.run_id)
            if event.type == EventType.RUN_COMPLETED
        ]
        assert len(completed) == 1
        assert "outcome_kind" not in completed[0].payload
    assert all(
        event["terminal_state_atomic"] is True
        for event in events
        if event["event"] == "row-terminal"
    )


@pytest.mark.parametrize(
    "outcome",
    (RunOutcomeKind.RESOLVED, RunOutcomeKind.TASK_FAILURE),
)
def test_production_shaped_completed_terminal_matches_durable_result(
    tmp_path: Path,
    outcome: RunOutcomeKind,
) -> None:
    manifests = _manifests(1)
    batch = _fresh_batch(manifests)
    contract = _contract(manifests, batch)
    runner = AgentRunner(tmp_path / ".patchloop")
    journal = tmp_path / "driver.jsonl"

    terminal = run_append_only_rapid_batch_driver(
        journal_path=journal,
        contract=contract,
        manifests=manifests,
        schedule_rows=_schedule_rows(1),
        runner=runner,
        batch_authorization=batch,
        execute_row=_executor(runner, (outcome,)),
        project_row=_project,
    )
    events = load_rapid_batch_driver_journal(journal, contract)
    completed = [
        event
        for event in runner.state.list_events(manifests[0].run_id)
        if event.type == EventType.RUN_COMPLETED
    ]

    assert terminal["event"] == "batch-completed"
    assert (
        next(event for event in events if event["event"] == "row-terminal")["terminal_state_atomic"]
        is True
    )
    assert len(completed) == 1
    assert "outcome_kind" not in completed[0].payload
    assert completed[0].payload["scope_compliant_success"] is (outcome == RunOutcomeKind.RESOLVED)
    assert completed[0].payload["official"] is False


def test_completed_terminal_payload_mismatch_halts_before_next_row(tmp_path: Path) -> None:
    manifests = _manifests(2)
    batch = _fresh_batch(manifests)
    contract = _contract(manifests, batch)
    runner = AgentRunner(tmp_path / ".patchloop")
    executed: list[int] = []
    base_executor = _executor(
        runner,
        (RunOutcomeKind.TASK_FAILURE, RunOutcomeKind.TASK_FAILURE),
        tamper_completed_payload=True,
    )

    def execute(**kwargs: Any) -> RunResult:
        executed.append(kwargs["manifest"].experiment.schedule_order)
        return base_executor(**kwargs)

    journal = tmp_path / "driver.jsonl"
    terminal = run_append_only_rapid_batch_driver(
        journal_path=journal,
        contract=contract,
        manifests=manifests,
        schedule_rows=_schedule_rows(2),
        runner=runner,
        batch_authorization=batch,
        execute_row=execute,
        project_row=_project,
    )
    events = load_rapid_batch_driver_journal(journal, contract)

    assert terminal["event"] == "batch-halted"
    assert terminal["reason_codes"] == ["TERMINAL_STATE_NOT_ATOMIC"]
    assert executed == [1]
    row_terminal = next(event for event in events if event["event"] == "row-terminal")
    assert row_terminal["terminal_state_atomic"] is False
    assert batch_execution_authorization_receipt(batch)["next_order"] == 2


@pytest.mark.parametrize(
    "fault",
    ("escaped_exception", "artifact_fault", "accounting_fault", "active_lock"),
)
def test_faults_halt_before_the_second_row_starts(tmp_path: Path, fault: str) -> None:
    manifests = _manifests(2)
    batch = _fresh_batch(manifests)
    contract = _contract(manifests, batch)
    runner = AgentRunner(tmp_path / ".patchloop")
    executed: list[int] = []
    base_executor = _executor(
        runner,
        (RunOutcomeKind.INFRASTRUCTURE_ERROR, RunOutcomeKind.TASK_FAILURE),
        raise_after_persist=fault == "escaped_exception",
        tamper_provenance=fault == "artifact_fault",
    )

    def execute(**kwargs: Any) -> RunResult:
        executed.append(kwargs["manifest"].experiment.schedule_order)
        return base_executor(**kwargs)

    def project(**kwargs: Any) -> dict[str, Any]:
        value = _project(**kwargs)
        if fault == "accounting_fault":
            value["model_cost_nanos"] += 1
        return value

    journal = tmp_path / "driver.jsonl"
    if fault == "active_lock":
        with runner.ownership.acquire(manifests[0].run_id):
            terminal = run_append_only_rapid_batch_driver(
                journal_path=journal,
                contract=contract,
                manifests=manifests,
                schedule_rows=_schedule_rows(2),
                runner=runner,
                batch_authorization=batch,
                execute_row=execute,
                project_row=project,
            )
    else:
        terminal = run_append_only_rapid_batch_driver(
            journal_path=journal,
            contract=contract,
            manifests=manifests,
            schedule_rows=_schedule_rows(2),
            runner=runner,
            batch_authorization=batch,
            execute_row=execute,
            project_row=project,
        )

    events = load_rapid_batch_driver_journal(journal, contract)
    assert terminal["event"] == "batch-halted"
    assert terminal["terminal_row_count"] == 1
    assert terminal["not_started_row_count"] == 1
    assert executed == [1]
    assert batch_execution_authorization_receipt(batch)["next_order"] == 2
    decisions = [event for event in events if event["event"] == "row-decision"]
    assert len(decisions) == 1
    assert decisions[0]["decision"] == "halt"


def test_restart_persists_halt_without_reconstructing_ephemeral_capability(
    tmp_path: Path,
) -> None:
    manifests = _manifests(2)
    batch = _fresh_batch(manifests)
    contract = _contract(manifests, batch)
    journal = tmp_path / "driver.jsonl"

    begin_rapid_batch_driver(
        journal_path=journal,
        contract=contract,
        manifests=manifests,
        batch_authorization=batch,
    )
    terminal = close_interrupted_rapid_batch_driver(
        journal_path=journal,
        contract=contract,
    )
    events = load_rapid_batch_driver_journal(journal, contract)

    assert terminal["event"] == "batch-halted"
    assert events[-2]["event"] == "batch-recovery-decision"
    assert events[-2]["reason_codes"] == ["EPHEMERAL_CAPABILITY_STATE_UNAVAILABLE_ON_RESTART"]
    assert batch_execution_authorization_receipt(batch)["next_order"] == 2


def test_restart_completes_an_already_persisted_recovery_halt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifests = _manifests(2)
    batch = _fresh_batch(manifests)
    contract = _contract(manifests, batch)
    journal = tmp_path / "driver.jsonl"
    begin_rapid_batch_driver(
        journal_path=journal,
        contract=contract,
        manifests=manifests,
        batch_authorization=batch,
    )
    original_close = driver_module._append_batch_close

    def crash_before_close(**_: Any) -> dict[str, Any]:
        raise OSError("injected close crash")

    monkeypatch.setattr(driver_module, "_append_batch_close", crash_before_close)
    with pytest.raises(OSError, match="injected close crash"):
        close_interrupted_rapid_batch_driver(
            journal_path=journal,
            contract=contract,
        )
    assert load_rapid_batch_driver_journal(journal, contract)[-1]["event"] == (
        "batch-recovery-decision"
    )

    monkeypatch.setattr(driver_module, "_append_batch_close", original_close)
    terminal = close_interrupted_rapid_batch_driver(
        journal_path=journal,
        contract=contract,
    )
    assert terminal["event"] == "batch-halted"
    assert terminal["reason_codes"] == ["EPHEMERAL_CAPABILITY_STATE_UNAVAILABLE_ON_RESTART"]


def test_public_schedule_projection_mismatch_fails_before_journal_creation(
    tmp_path: Path,
) -> None:
    manifests = _manifests(2)
    batch = _fresh_batch(manifests)
    contract = _contract(manifests, batch)
    runner = AgentRunner(tmp_path / ".patchloop")
    schedule = list(_schedule_rows(2))
    schedule[0] = {**schedule[0], "schedule_row_id": sha256_json("wrong-row")}
    journal = tmp_path / "driver.jsonl"

    with pytest.raises(ContractError, match="public schedule projection differs"):
        run_append_only_rapid_batch_driver(
            journal_path=journal,
            contract=contract,
            manifests=manifests,
            schedule_rows=tuple(schedule),
            runner=runner,
            batch_authorization=batch,
            execute_row=_executor(
                runner,
                (RunOutcomeKind.TASK_FAILURE, RunOutcomeKind.TASK_FAILURE),
            ),
            project_row=_project,
        )
    assert not journal.exists()
    assert batch_execution_authorization_receipt(batch)["next_order"] == 1


def test_duplicate_grant_fails_before_schedule_advances_again(tmp_path: Path) -> None:
    manifests = _manifests(2)
    schedule = _schedule_rows(2)
    batch = _fresh_batch(manifests)
    contract = _contract(manifests, batch)
    runner = AgentRunner(tmp_path / ".patchloop")
    journal = tmp_path / "driver.jsonl"
    first = begin_rapid_batch_driver(
        journal_path=journal,
        contract=contract,
        manifests=manifests,
        batch_authorization=batch,
    )
    _consume_for_dispatch(first)
    result = _result(manifests[0], RunOutcomeKind.INFRASTRUCTURE_ERROR)
    _persist_terminal(runner, manifests[0], result)
    projected = _rapid_v4_row_projection(
        schedule_row=schedule[0],
        manifest=manifests[0],
        result=result.model_dump(mode="json"),
        runner=runner,
        error=None,
    )
    recorded = record_rapid_driver_row_terminal(
        journal_path=journal,
        contract=contract,
        runner=runner,
        manifest=manifests[0],
        authorization=first,
        result=result,
        projected_row=projected,
        error=None,
        accrued_cost_nanos_before=0,
    )
    decision, evidence = decide_rapid_driver_row_continuation(
        journal_path=journal,
        contract=contract,
        runner=runner,
        manifest=manifests[0],
        next_manifest=manifests[1],
        recorded=recorded,
        authorization=first,
        batch_authorization=batch,
        accrued_cost_nanos_before=0,
    )
    assert evidence is not None
    issue_persisted_rapid_driver_next_row(
        journal_path=journal,
        contract=contract,
        decision_event=decision,
        settlement_evidence=evidence,
        batch_authorization=batch,
        next_manifest=manifests[1],
    )
    order_after_first_grant = batch_execution_authorization_receipt(batch)["next_order"]

    with pytest.raises(ContractError, match="stale or mismatched"):
        issue_persisted_rapid_driver_next_row(
            journal_path=journal,
            contract=contract,
            decision_event=decision,
            settlement_evidence=evidence,
            batch_authorization=batch,
            next_manifest=manifests[1],
        )
    assert batch_execution_authorization_receipt(batch)["next_order"] == order_after_first_grant


def test_tampered_journal_fails_closed(tmp_path: Path) -> None:
    manifests = _manifests(2)
    batch = _fresh_batch(manifests)
    contract = _contract(manifests, batch)
    journal = tmp_path / "driver.jsonl"
    begin_rapid_batch_driver(
        journal_path=journal,
        contract=contract,
        manifests=manifests,
        batch_authorization=batch,
    )
    events = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
    events[-1]["schedule_order"] = 2
    journal.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    with pytest.raises(RecoveryError, match="chain differs"):
        load_rapid_batch_driver_journal(journal, contract)


def test_rehashed_semantic_journal_tamper_also_fails_closed(tmp_path: Path) -> None:
    manifests = _manifests(2)
    batch = _fresh_batch(manifests)
    contract = _contract(manifests, batch)
    journal = tmp_path / "driver.jsonl"
    begin_rapid_batch_driver(
        journal_path=journal,
        contract=contract,
        manifests=manifests,
        batch_authorization=batch,
    )
    events = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
    capability = events[-1]
    capability["issuance_kind"] = "ordinary"
    body = {key: value for key, value in capability.items() if key != "content_hash"}
    capability["content_hash"] = sha256_json(body)
    journal.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    with pytest.raises(RecoveryError, match="transition differs"):
        load_rapid_batch_driver_journal(journal, contract)
