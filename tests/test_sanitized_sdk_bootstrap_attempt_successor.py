from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.evals import sanitized_sdk_bootstrap_attempt_successor as successor

REPOSITORY = Path(__file__).resolve().parents[1]
SHA_A = "sha256:" + "a" * 64


@lru_cache(maxsize=1)
def contract() -> successor.AttemptSuccessorContract:
    raw = (REPOSITORY / successor.CONTRACT_PATH).read_bytes()
    value = successor.AttemptSuccessorContract.model_validate_json(raw)
    assert raw == successor.v11.v10._canonical(value)
    return value


def approval() -> successor.v11.ExactApprovalBinding:
    return successor.v11.ExactApprovalBinding.model_validate_json(
        (REPOSITORY / successor.v11.APPROVAL_BINDING_PATH).read_bytes()
    )


def _file(path: Path) -> successor.v11.v10.CommittedFileBinding:
    return successor.v11.v10.CommittedFileBinding(
        path=path.as_posix(),
        blob_oid="b" * 40,
        file_bytes=1,
        file_sha256=SHA_A,
    )


def qualification(
    selected_contract: successor.AttemptSuccessorContract,
    selected_approval: successor.v11.ExactApprovalBinding,
) -> successor.SourceQualification:
    files = tuple(_file(path) for path in successor.SOURCE_FILES)
    body = {
        "schema_version": successor.QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": successor.QUALIFICATION_ID,
        "status": successor.QUALIFICATION_STATUS,
        "recorded_at": selected_approval.recorded_at,
        "source_commit": successor.SourceCommitBinding(
            commit="c" * 40,
            tree="d" * 40,
            parents=(successor.SOURCE_PARENT_COMMIT,),
            added_paths=successor.SOURCE_ADDED_PATHS,
        ).model_dump(mode="json"),
        "source_files": tuple(item.model_dump(mode="json") for item in files),
        "contract_id": selected_contract.contract_id,
        "contract_content_hash": selected_contract.content_hash,
        "predecessor_approval_id": selected_approval.approval_id,
        "predecessor_approval_content_hash": selected_approval.content_hash,
        "authority": successor.QualificationAuthority().model_dump(mode="json"),
        "next_gate": successor.QUALIFICATION_NEXT_GATE,
    }
    return successor.SourceQualification(
        **body,
        content_hash=successor.v11.v10._hash_body(body),
    )


def _contract_error_observation() -> successor.v9.ParentObservation:
    return successor.v9.ParentObservation(
        state=successor.v9.ParentState.ERROR,
        reason=successor.v9.ParentReason.CONTRACT_BINDING_ERROR,
        activity_accounting_complete=True,
        unknown_post_marker_activity_possible=False,
        passed=False,
    )


def test_contract_binds_exact_v11_approval_and_v9_runtime() -> None:
    value = contract()
    bound = approval()
    assert value.predecessor.approval_id == bound.approval_id
    assert value.predecessor.approval_content_hash == bound.content_hash
    assert value.predecessor.approval_evidence_commit == successor.V11_APPROVAL_EVIDENCE_COMMIT
    assert value.runtime.entrypoint == successor.APPROVED_RUNTIME
    assert value.runtime.source_commit == successor.v11.v10.V9_SOURCE_COMMIT
    assert value.runtime.approved_scopes == successor.APPROVED_SCOPES
    assert value.lifecycle.attempt_limit == 1
    assert value.lifecycle.retry_replacement_or_resume_allowed is False


def test_source_authority_is_offline_and_exact_run_gated() -> None:
    value = contract()
    assert value.future_exact_run_entrypoint_implemented is True
    assert value.execution_currently_authorized is False
    assert value.authority.execution_during_source_qualification_authorized is False
    assert value.authority.runtime_artifact_creation_during_source_qualification_authorized is False
    assert value.authority.environment_docker_dotenv_sdk_or_network_observation_authorized is False
    assert value.next_gate == "fresh-exact-v12-run-statement"


def test_exact_statement_builds_one_use_run_authorization() -> None:
    selected_contract = contract()
    selected_approval = approval()
    selected_qualification = qualification(selected_contract, selected_approval)
    statement = successor.expected_run_statement(
        selected_contract,
        selected_qualification,
        selected_approval,
    )
    value = successor.build_run_authorization(
        selected_contract,
        selected_qualification,
        selected_approval,
        statement=statement,
        recorded_at=selected_approval.recorded_at,
    )
    assert selected_contract.contract_id in statement
    assert selected_qualification.content_hash in statement
    assert selected_approval.approval_id in statement
    assert value.run_now_authorized is True
    assert value.one_use is True
    assert value.network_or_transport_authorized is False
    assert value.candidate_cost_or_paid_execution_authorized is False


def test_generic_or_stale_run_statement_fails() -> None:
    selected_contract = contract()
    selected_approval = approval()
    selected_qualification = qualification(selected_contract, selected_approval)
    with pytest.raises(successor.AttemptSuccessorError):
        successor.build_run_authorization(
            selected_contract,
            selected_qualification,
            selected_approval,
            statement="진행해줘",
            recorded_at=selected_approval.recorded_at,
        )


def test_run_authorization_and_terminal_hash_tamper_fail() -> None:
    selected_contract = contract()
    selected_approval = approval()
    selected_qualification = qualification(selected_contract, selected_approval)
    statement = successor.expected_run_statement(
        selected_contract,
        selected_qualification,
        selected_approval,
    )
    authorization = successor.build_run_authorization(
        selected_contract,
        selected_qualification,
        selected_approval,
        statement=statement,
        recorded_at=selected_approval.recorded_at,
    )
    changed = authorization.model_dump(mode="json")
    changed["content_hash"] = SHA_A
    with pytest.raises(ValidationError):
        successor.RunAuthorization.model_validate(changed)

    attempt = successor._build_attempt(
        selected_contract,
        selected_qualification,
        selected_approval,
        authorization,
        ledger_snapshot_hash=successor._empty_ledger_hash(),
        created_at=selected_approval.recorded_at,
    )
    action = successor._build_action(attempt, recorded_at=selected_approval.recorded_at)
    terminal = successor._build_terminal(
        attempt,
        action,
        observation=_contract_error_observation(),
        recorded_at=selected_approval.recorded_at,
    )
    changed_terminal = terminal.model_dump(mode="json")
    changed_terminal["outcome"] = "ready"
    with pytest.raises(ValidationError):
        successor.TerminalTransition.model_validate(changed_terminal)


def test_simulated_run_writes_ordered_terminal_and_rejects_reuse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected_contract = contract()
    selected_approval = approval()
    selected_qualification = qualification(selected_contract, selected_approval)
    statement = successor.expected_run_statement(
        selected_contract,
        selected_qualification,
        selected_approval,
    )
    monkeypatch.setattr(
        successor,
        "load_contract",
        lambda **_kwargs: selected_contract,
    )
    monkeypatch.setattr(
        successor,
        "_load_qualification",
        lambda _root: selected_qualification,
    )
    monkeypatch.setattr(
        successor,
        "_load_v11_approval",
        lambda _root: (None, None, None, selected_approval, b"", b""),
    )
    monkeypatch.setattr(successor, "_load_v9_contract", lambda _root: object())
    calls = {"observer": 0}

    def observer(*_args: Any, **_kwargs: Any) -> successor.v9.ParentObservation:
        calls["observer"] += 1
        for path in (
            successor.RUN_AUTHORIZATION_PATH,
            successor.ATTEMPT_PATH,
            successor.ACTION_STARTED_PATH,
        ):
            assert (tmp_path / path).is_file()
        assert not (tmp_path / successor.TERMINAL_PATH).exists()
        return _contract_error_observation()

    summary = successor.run_once(
        statement=statement,
        repository=tmp_path,
        parent_observer=observer,
    )
    assert summary["status"] == "V12_SANITIZED_SDK_BOOTSTRAP_ATTEMPT_TERMINAL_VALID"
    assert summary["outcome"] == "error"
    assert summary["reason"] == "contract_binding_error"
    assert summary["retry_or_resume_allowed"] is False
    assert calls == {"observer": 1}
    with pytest.raises(successor.AttemptSuccessorError):
        successor.run_once(
            statement=statement,
            repository=tmp_path,
            parent_observer=observer,
        )
    assert calls == {"observer": 1}


def test_wrong_statement_creates_no_artifact_or_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected_contract = contract()
    selected_approval = approval()
    selected_qualification = qualification(selected_contract, selected_approval)
    monkeypatch.setattr(successor, "load_contract", lambda **_kwargs: selected_contract)
    monkeypatch.setattr(successor, "_load_qualification", lambda _root: selected_qualification)
    monkeypatch.setattr(
        successor,
        "_load_v11_approval",
        lambda _root: (None, None, None, selected_approval, b"", b""),
    )
    monkeypatch.setattr(successor, "_load_v9_contract", lambda _root: object())
    calls = {"observer": 0}

    def observer(*_args: Any, **_kwargs: Any) -> successor.v9.ParentObservation:
        calls["observer"] += 1
        return _contract_error_observation()

    with pytest.raises(successor.AttemptSuccessorError):
        successor.run_once(
            statement="진행해줘",
            repository=tmp_path,
            parent_observer=observer,
        )
    assert calls == {"observer": 0}
    for path in (
        successor.RUN_AUTHORIZATION_PATH,
        successor.ATTEMPT_PATH,
        successor.ACTION_STARTED_PATH,
        successor.TERMINAL_PATH,
    ):
        assert not (tmp_path / path).exists()


def test_observer_exception_becomes_fail_closed_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected_contract = contract()
    selected_approval = approval()
    selected_qualification = qualification(selected_contract, selected_approval)
    statement = successor.expected_run_statement(
        selected_contract,
        selected_qualification,
        selected_approval,
    )
    monkeypatch.setattr(successor, "load_contract", lambda **_kwargs: selected_contract)
    monkeypatch.setattr(successor, "_load_qualification", lambda _root: selected_qualification)
    monkeypatch.setattr(
        successor,
        "_load_v11_approval",
        lambda _root: (None, None, None, selected_approval, b"", b""),
    )
    monkeypatch.setattr(successor, "_load_v9_contract", lambda _root: object())

    def observer(*_args: Any, **_kwargs: Any) -> successor.v9.ParentObservation:
        raise RuntimeError("must-never-persist-observer-exception")

    summary = successor.run_once(
        statement=statement,
        repository=tmp_path,
        parent_observer=observer,
    )
    raw = (tmp_path / successor.TERMINAL_PATH).read_bytes()
    assert summary["outcome"] == "error"
    assert summary["reason"] == "lifecycle_checker_error"
    assert summary["activity_accounting_complete"] is False
    assert summary["unknown_post_marker_activity_possible"] is True
    assert b"must-never-persist" not in raw


def test_module_has_no_retry_replacement_or_paid_entrypoint() -> None:
    for name in (
        "retry",
        "resume",
        "replace_attempt",
        "run_provider",
        "run_agent",
        "run_evaluator",
        "create_candidate",
        "reserve_cost",
    ):
        assert not hasattr(successor, name)


def test_checked_in_source_qualification_when_present() -> None:
    if not (REPOSITORY / successor.QUALIFICATION_PATH).exists():
        pytest.skip("qualification is created only after the exact source commit")
    summary = successor.validate_source_qualification(repository=REPOSITORY)
    assert summary["status"] == successor.QUALIFICATION_STATUS
    assert summary["runtime_artifacts_created"] is False
    assert summary["external_observations_made"] == 0
    assert summary["external_mutations_made"] == 0
    assert summary["execution_authorized"] is False
    assert summary["next_gate"] == "fresh-exact-v12-run-statement"
