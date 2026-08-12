from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from patchloop.evals import supervised_frame_activation_successor as successor

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def contract() -> successor.SupervisedFrameActivationContract:
    return successor._build_contract(REPOSITORY)


@pytest.fixture(autouse=True)
def cached_contract(
    monkeypatch: pytest.MonkeyPatch,
    contract: successor.SupervisedFrameActivationContract,
) -> None:
    monkeypatch.setattr(successor, "load_contract", lambda **_kwargs: contract)


def _blocked_observation() -> successor.v17.SupervisedParentObservation:
    terminal = successor.v17.v15.v13.TerminalTransition.model_validate_json(
        (REPOSITORY / successor.v17.v15.v13.TERMINAL_PATH).read_bytes()
    )
    assert terminal.observation is not None
    base = terminal.observation.base
    return successor.v17.SupervisedParentObservation(
        base=base,
        activity_accounting_complete=base.activity_accounting_complete,
        unknown_post_marker_activity_possible=base.unknown_post_marker_activity_possible,
        passed=base.passed,
    )


def test_contract_binds_source_qualified_v17_and_keeps_authority_closed(
    contract: successor.SupervisedFrameActivationContract,
) -> None:
    assert contract.predecessor.source_commit == successor.V17_SOURCE_COMMIT
    assert contract.predecessor.source_tree == successor.V17_SOURCE_TREE
    assert contract.predecessor.qualification_commit == successor.V17_QUALIFICATION_COMMIT
    assert contract.predecessor.source_qualification_hash == successor.V17_QUALIFICATION_HASH
    assert contract.predecessor.state_approval_attempt_or_terminal_count == 0
    assert contract.predecessor.execution_authorized is False
    assert contract.runtime.delegate_semantics_unchanged is True
    assert contract.runtime.approved_scopes == successor.APPROVED_SCOPES
    assert contract.runtime.default_observers_reachable_only_after_action_started is True
    assert contract.runtime.direct_observer_cli_exposed is False
    assert contract.runtime.parent_to_supervisor_launch_limit == 1
    assert contract.runtime.supervisor_to_worker_launch_limit == 1
    assert contract.lifecycle.v17_source_or_qualification_mutation_allowed is False
    assert contract.execution_currently_authorized is False


def test_delegate_preserves_docker_first_block(
    contract: successor.SupervisedFrameActivationContract,
) -> None:
    blocked = _blocked_observation()
    assert blocked.base.docker_observation is not None
    result = successor._run_parent_preflight(
        contract,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: blocked.base.docker_observation,
        child_observer=lambda *_args, **_kwargs: pytest.fail("child must not run"),
    )

    assert result.base.state == "blocked"
    assert result.base.reason == "docker_not_ready"
    assert result.supervised_child_execution is None
    assert result.activity_accounting_complete is True


def test_forged_contract_suppresses_docker(
    contract: successor.SupervisedFrameActivationContract,
) -> None:
    forged = contract.model_copy(update={"content_hash": "sha256:" + "0" * 64})
    result = successor._run_parent_preflight(
        forged,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: pytest.fail("Docker must not run"),
    )

    assert result.base.state == "error"
    assert result.base.reason == "contract_binding_error"
    assert result.supervised_child_execution is None


def test_exact_state_approval_and_run_statements_are_distinct(
    contract: successor.SupervisedFrameActivationContract,
) -> None:
    now = datetime.now(UTC)
    qualification = SimpleNamespace(
        contract_id=contract.contract_id,
        content_hash="sha256:" + "1" * 64,
        recorded_at=now,
    )
    state_statement = successor.expected_state_statement(contract, qualification)
    state = successor.build_state_evidence(
        contract, qualification, statement=state_statement, recorded_at=now
    )
    approval_statement = successor.expected_approval_statement(contract, qualification, state)
    approval = successor.build_approval(
        contract,
        qualification,
        state,
        statement=approval_statement,
        recorded_at=now + timedelta(seconds=1),
    )
    run_statement = successor.expected_run_statement(contract, qualification, state, approval)

    assert state.docker_running_reported is True
    assert state.dotenv_only_openai_api_key_reported is True
    assert state.execution_authorized is False
    assert approval.dotenv_only_openai_api_key_reconfirmed is True
    assert approval.parent_to_supervisor_launch_limit == 1
    assert approval.supervisor_to_worker_launch_limit == 1
    assert approval.attempt_started is False
    assert state_statement != approval_statement != run_statement
    with pytest.raises(successor.SupervisedFrameActivationError):
        successor.build_state_evidence(
            contract, qualification, statement="진행해줘", recorded_at=now
        )


def test_mock_attempt_writes_ordered_terminal_and_rejects_generic_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    contract: successor.SupervisedFrameActivationContract,
) -> None:
    now = datetime.now(UTC) - timedelta(seconds=10)
    qualification = SimpleNamespace(
        contract_id=contract.contract_id,
        content_hash="sha256:" + "2" * 64,
        recorded_at=now,
    )
    state = successor.build_state_evidence(
        contract,
        qualification,
        statement=successor.expected_state_statement(contract, qualification),
        recorded_at=now + timedelta(seconds=1),
    )
    approval = successor.build_approval(
        contract,
        qualification,
        state,
        statement=successor.expected_approval_statement(contract, qualification, state),
        recorded_at=now + timedelta(seconds=2),
    )
    statement = successor.expected_run_statement(contract, qualification, state, approval)
    observation = _blocked_observation()
    monkeypatch.setattr(successor, "_load_qualification", lambda _root: qualification)
    monkeypatch.setattr(successor, "_load_state", lambda _root: state)
    monkeypatch.setattr(successor, "_load_approval", lambda _root: approval)

    rejected_root = tmp_path / "rejected"
    rejected_root.mkdir()
    with pytest.raises(successor.SupervisedFrameActivationError):
        successor.run_once(
            statement="진행해줘",
            repository=rejected_root,
            parent_observer=lambda *_args, **_kwargs: observation,
        )
    assert not any((rejected_root / path).exists() for path in successor._ledger_paths())

    accepted_root = tmp_path / "accepted"
    accepted_root.mkdir()
    result = successor.run_once(
        statement=statement,
        repository=accepted_root,
        parent_observer=lambda *_args, **_kwargs: observation,
    )

    assert result["outcome"] == "blocked"
    assert result["reason"] == "docker_not_ready"
    assert result["retry_or_resume_allowed"] is False
    assert all((accepted_root / path).is_file() for path in successor._ledger_paths())

    failed_root = tmp_path / "observer-error"
    failed_root.mkdir()

    def fail_observer(
        *_args: object, **_kwargs: object
    ) -> successor.v17.SupervisedParentObservation:
        raise RuntimeError("synthetic observer failure")

    failed = successor.run_once(
        statement=statement,
        repository=failed_root,
        parent_observer=fail_observer,
    )
    assert failed["outcome"] == "error"
    assert failed["reason"] == "lifecycle_checker_error"
    assert failed["activity_accounting_complete"] is False
    assert failed["unknown_post_marker_activity_possible"] is True
    assert all((failed_root / path).is_file() for path in successor._ledger_paths())


def test_source_modes_have_no_runtime_side_effects(
    contract: successor.SupervisedFrameActivationContract,
) -> None:
    assert (
        contract.authority.environment_docker_dotenv_sdk_or_network_observation_authorized
        is False
    )
    for path in (
        successor.STATE_PATH,
        successor.APPROVAL_PATH,
        successor.RUN_AUTHORIZATION_PATH,
        successor.ATTEMPT_PATH,
        successor.ACTION_STARTED_PATH,
        successor.TERMINAL_PATH,
    ):
        assert not (REPOSITORY / path).exists()


def test_checked_in_source_qualification_when_present() -> None:
    if not (REPOSITORY / successor.QUALIFICATION_PATH).exists():
        pytest.skip("qualification is created only after the exact source commit")
    summary = successor.validate_source_qualification(repository=REPOSITORY)
    assert summary["external_observations_made"] == 0
    assert summary["execution_authorized"] is False
