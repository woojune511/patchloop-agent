from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from patchloop.evals import executable_no_call_preflight as v3
from patchloop.evals import no_start_executable_preflight as v5
from patchloop.evals import sanitized_sdk_bootstrap_framed_successor as successor
from scripts import run_sanitized_sdk_bootstrap_framed_child as framed_child

REPOSITORY = Path(__file__).resolve().parents[1]
SENSITIVE = "sk-must-never-persist-v13-sensitive-marker"
SYSTEMROOT = r"C:\synthetic-systemroot-must-not-persist"


@pytest.fixture(scope="module")
def contract() -> successor.FramedSuccessorContract:
    return successor._build_contract(REPOSITORY)


@pytest.fixture(scope="module")
def v9_pair() -> tuple[successor.v9.ParentSuccessorContract, successor.v9.SourceQualification]:
    return successor._load_v9_contract(REPOSITORY)


@pytest.fixture(autouse=True)
def cached_contract(
    monkeypatch: pytest.MonkeyPatch,
    contract: successor.FramedSuccessorContract,
    v9_pair: tuple[successor.v9.ParentSuccessorContract, successor.v9.SourceQualification],
) -> None:
    monkeypatch.setattr(successor, "load_contract", lambda **_kwargs: contract)
    monkeypatch.setattr(successor, "_load_v9_contract", lambda _root: v9_pair)
    monkeypatch.setattr(successor.v9, "load_contract", lambda **_kwargs: v9_pair[0])


def _blocked_child() -> dict[str, Any]:
    return {
        "schema_version": "isolated-dotenv-sanitized-sdk-diagnostic-v1",
        "state": "blocked",
        "dotenv": {
            "file_present": False,
            "exact_subject_declared": False,
            "exact_subject_nonempty": False,
            "duplicate_subject": False,
            "error_code": "dotenv_missing",
            "raw_value_returned": False,
            "value_hash_prefix_or_length_returned": False,
        },
        "diagnostic": None,
        "error_code": "dotenv_missing",
        "activity": {
            "dotenv_file_read_count": 0,
            "dotenv_subject_membership_check_count": 0,
            "credential_assignment_parse_count": 0,
            "credential_value_return_count": 0,
            "credential_value_hash_prefix_or_length_count": 0,
            "exception_message_type_repr_or_traceback_return_count": 0,
            "transport_dispatch_count": 0,
            "network_call_count": 0,
            "provider_evaluator_agent_call_count": 0,
        },
        "raw_credential_value_returned": False,
        "credential_hash_prefix_or_length_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
    }


def _envelope(*, child: dict[str, Any] | None = None, code: str | None = None) -> bytes:
    complete = child is not None or code == "diagnostic_wrapper_import_error"
    payload = {
        "schema_version": framed_child.SCHEMA_VERSION,
        "child": child,
        "code": code,
        "activity": {
            "diagnostic_invocation_count": 1
            if child is not None or code != "diagnostic_wrapper_import_error"
            else 0,
            "typed_validation_count": 1
            if child is not None or code == "diagnostic_result_invalid"
            else 0,
            "suppressed_stdout_channel_count": 1,
            "suppressed_stderr_channel_count": 1,
            "raw_workload_output_return_count": 0,
            "exception_message_type_repr_or_traceback_return_count": 0,
            "credential_value_return_hash_prefix_or_length_count": 0,
            "activity_accounting_complete": complete,
            "unknown_workload_activity_possible": not complete,
        },
        "raw_output_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
        "credential_value_hash_prefix_or_length_returned": False,
    }
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _docker_ready() -> dict[str, Any]:
    terminal = v5.TerminalTransition.model_validate_json(
        (REPOSITORY / v5.TERMINAL_PATH).read_bytes()
    )
    assert terminal.docker_observation is not None
    return terminal.docker_observation


def _docker_blocked() -> dict[str, Any]:
    terminal = v3.TerminalTransition.model_validate_json(
        (REPOSITORY / v3.TERMINAL_PATH).read_bytes()
    )
    assert terminal.docker_observation is not None
    return terminal.docker_observation


def test_contract_binds_consumed_v12_and_keeps_authority_closed(
    contract: successor.FramedSuccessorContract,
) -> None:
    assert contract.predecessor.evidence_commit == successor.V12_EVIDENCE_COMMIT
    assert contract.predecessor.outcome == "error"
    assert contract.predecessor.child_code == "child_output_invalid"
    assert contract.predecessor.retry_or_resume_allowed is False
    assert contract.runtime.stdout_stderr_descriptor_isolation_required is True
    assert contract.runtime.canonical_single_envelope_required is True
    assert contract.runtime.raw_child_output_persistence_allowed is False
    assert contract.lifecycle.separate_exact_approval_required is True
    assert contract.lifecycle.retry_replacement_or_resume_allowed is False
    assert (
        contract.authority.environment_docker_dotenv_sdk_or_network_observation_authorized is False
    )
    assert contract.execution_currently_authorized is False


def test_wrapper_discards_python_and_fd_noise(capfd: pytest.CaptureFixture[str]) -> None:
    def noisy(_root: Path) -> dict[str, Any]:
        print(SENSITIVE)
        print(SENSITIVE, file=os.sys.stderr)
        os.write(1, SENSITIVE.encode())
        os.write(2, SENSITIVE.encode())
        return _blocked_child()

    envelope = framed_child.build_framed_envelope(
        REPOSITORY,
        diagnostic_runner=noisy,
        typed_validator=lambda value: value,
    )
    captured = capfd.readouterr()
    parsed = successor.FramedChildEnvelope.model_validate(envelope)

    assert captured.out == ""
    assert captured.err == ""
    assert parsed.child is not None and parsed.child.state == "blocked"
    assert SENSITIVE not in json.dumps(envelope)


def test_wrapper_schema_failure_returns_fixed_value_free_code() -> None:
    envelope = framed_child.build_framed_envelope(
        REPOSITORY,
        diagnostic_runner=lambda _root: {"secret": SENSITIVE},
        typed_validator=lambda _value: (_ for _ in ()).throw(ValueError(SENSITIVE)),
    )
    parsed = successor.FramedChildEnvelope.model_validate(envelope)

    assert parsed.code == "diagnostic_result_invalid"
    assert parsed.child is None
    assert parsed.activity.activity_accounting_complete is False
    assert parsed.activity.unknown_workload_activity_possible is True
    assert SENSITIVE not in json.dumps(envelope)


def test_exact_framed_invocation_maps_typed_child(
    contract: successor.FramedSuccessorContract,
) -> None:
    seen: dict[str, Any] = {}

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        seen.update({"argv": argv, **kwargs})
        return subprocess.CompletedProcess(
            argv, 0, stdout=_envelope(child=_blocked_child()), stderr=b""
        )

    result = successor.run_framed_diagnostic_child(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda name: SYSTEMROOT if name == "SYSTEMROOT" else None,
        run=run,
    )

    assert result.base.child is not None and result.base.child.state == "blocked"
    assert result.frame_code is None
    assert result.envelope_received is True
    assert seen["argv"][1:5] == list(successor.CHILD_FLAGS)
    assert seen["argv"][5].endswith("run_sanitized_sdk_bootstrap_framed_child.py")
    assert seen["env"] == {**successor.FIXED_CHILD_ENVIRONMENT, "SYSTEMROOT": SYSTEMROOT}
    assert SYSTEMROOT not in result.model_dump_json()


def test_malformed_or_schema_error_output_is_discarded_and_fail_closed(
    contract: successor.FramedSuccessorContract,
) -> None:
    malformed = successor.run_framed_diagnostic_child(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda _name: SYSTEMROOT,
        run=lambda argv, **_kwargs: subprocess.CompletedProcess(
            argv, 0, stdout=SENSITIVE.encode(), stderr=b""
        ),
    )
    typed_error = successor.run_framed_diagnostic_child(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda _name: SYSTEMROOT,
        run=lambda argv, **_kwargs: subprocess.CompletedProcess(
            argv,
            0,
            stdout=_envelope(code="diagnostic_result_invalid"),
            stderr=b"",
        ),
    )

    assert malformed.frame_code == "framed_output_invalid"
    assert malformed.activity_accounting_complete is False
    assert malformed.unknown_workload_activity_possible is True
    assert SENSITIVE not in malformed.model_dump_json()
    assert typed_error.frame_code == "diagnostic_result_invalid"
    assert typed_error.envelope_received is True
    assert typed_error.activity_accounting_complete is False


def test_docker_block_suppresses_framed_child(
    contract: successor.FramedSuccessorContract,
) -> None:
    result = successor.run_parent_preflight(
        contract,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: _docker_blocked(),
        child_observer=lambda *_args, **_kwargs: pytest.fail("child must not run"),
    )

    assert result.base.state == "blocked"
    assert result.base.reason == "docker_not_ready"
    assert result.framed_child_execution is None
    assert result.activity_accounting_complete is True


def test_ready_docker_and_typed_blocked_child_remain_complete(
    contract: successor.FramedSuccessorContract,
) -> None:
    execution = successor.run_framed_diagnostic_child(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda _name: SYSTEMROOT,
        run=lambda argv, **_kwargs: subprocess.CompletedProcess(
            argv, 0, stdout=_envelope(child=_blocked_child()), stderr=b""
        ),
    )
    result = successor.run_parent_preflight(
        contract,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: _docker_ready(),
        child_observer=lambda *_args, **_kwargs: execution,
    )

    assert result.base.state == "blocked"
    assert result.base.reason == "dotenv_not_ready"
    assert result.framed_child_execution == execution
    assert result.activity_accounting_complete is True
    assert result.unknown_post_marker_activity_possible is False


def test_forged_contract_suppresses_docker(
    contract: successor.FramedSuccessorContract,
) -> None:
    forged = contract.model_copy(update={"content_hash": "sha256:" + "0" * 64})
    result = successor.run_parent_preflight(
        forged,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: pytest.fail("Docker must not run"),
    )

    assert result.base.state == "error"
    assert result.base.reason == "contract_binding_error"
    assert result.framed_child_execution is None


def test_exact_state_approval_and_run_statements_are_distinct_and_fail_closed(
    contract: successor.FramedSuccessorContract,
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

    assert state.execution_authorized is False
    assert approval.attempt_started is False
    assert state_statement != approval_statement != run_statement
    with pytest.raises(successor.FramedSuccessorError):
        successor.build_state_evidence(
            contract, qualification, statement="진행해줘", recorded_at=now
        )
    with pytest.raises(successor.FramedSuccessorError):
        successor.build_approval(
            contract,
            qualification,
            state,
            statement="진행해줘",
            recorded_at=now + timedelta(seconds=1),
        )


def test_mock_attempt_writes_ordered_four_artifact_terminal_and_rejects_generic_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    contract: successor.FramedSuccessorContract,
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
    observation = successor.run_parent_preflight(
        contract,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: _docker_blocked(),
        child_observer=lambda *_args, **_kwargs: pytest.fail("child must not run"),
    )
    monkeypatch.setattr(successor, "_load_qualification", lambda _root: qualification)
    monkeypatch.setattr(successor, "_load_state", lambda _root: state)
    monkeypatch.setattr(successor, "_load_approval", lambda _root: approval)

    rejected_root = tmp_path / "rejected"
    rejected_root.mkdir()
    with pytest.raises(successor.FramedSuccessorError):
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


def test_no_runtime_artifact_exists_before_exact_activation() -> None:
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
