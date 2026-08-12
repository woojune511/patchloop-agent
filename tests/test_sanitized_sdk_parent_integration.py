from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.evals import executable_no_call_preflight as v3
from patchloop.evals import no_start_executable_preflight as v5
from patchloop.evals import sanitized_sdk_parent_integration as parent

REPOSITORY = Path(__file__).resolve().parents[1]
SENSITIVE_EXCEPTION_TEXT = "must-never-persist-from-parent-exception"


def _blocked_child_dict() -> dict[str, Any]:
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


def _blocked_child_execution() -> parent.ChildExecution:
    child = parent.IsolatedDiagnosticChild.model_validate(_blocked_child_dict())
    return parent.ChildExecution(
        parent_pythonhome_absent=True,
        parent_pythonpath_absent=True,
        launch_attempt_count=1,
        process_returned=True,
        child=child,
        error_code=None,
        activity_accounting_complete=True,
        unknown_post_launch_activity_possible=False,
        passed=False,
    )


def _v5_docker_ready() -> dict[str, Any]:
    terminal = v5.TerminalTransition.model_validate_json(
        (REPOSITORY / v5.TERMINAL_PATH).read_bytes()
    )
    assert terminal.docker_observation is not None
    return terminal.docker_observation


def _v3_docker_blocked() -> dict[str, Any]:
    terminal = v3.TerminalTransition.model_validate_json(
        (REPOSITORY / v3.TERMINAL_PATH).read_bytes()
    )
    assert terminal.docker_observation is not None
    return terminal.docker_observation


def test_contract_binds_v6_and_keeps_state_approval_and_execution_closed() -> None:
    summary = parent.materialize_contract(repository=REPOSITORY)
    contract = parent.load_contract(repository=REPOSITORY)

    assert summary["external_observations_made"] == 0
    assert summary["execution_authorized"] is False
    assert contract.v6.source_commit == parent.V6_SOURCE_COMMIT
    assert contract.v6.qualification_commit == parent.V6_QUALIFICATION_COMMIT
    assert contract.v6.v5_retry_or_resume_allowed is False
    assert contract.runtime_profile.parent_observer_integration_implemented is True
    assert contract.runtime_profile.one_use_lifecycle_implemented is True
    assert contract.fresh_state_required is True
    assert contract.v5_state_or_approval_reuse_allowed is False
    assert contract.source_authority.state_change_evidence_creation_authorized is False
    assert contract.source_authority.external_preflight_attempt_authorized is False
    assert contract.source_authority.docker_sdk_or_dotenv_observation_authorized is False


def test_dirty_parent_environment_suppresses_child_launch() -> None:
    contract = parent.load_contract(repository=REPOSITORY)
    calls = {"run": 0}

    def run(*_args: Any, **_kwargs: Any) -> Any:
        calls["run"] += 1
        raise AssertionError("child launch crossed dirty-parent boundary")

    result = parent.run_isolated_diagnostic_child(
        contract,
        repository=REPOSITORY,
        environment_present=lambda name: name == "PYTHONHOME",
        run=run,
    )

    assert result.error_code == "parent_python_environment_not_clean"
    assert result.launch_attempt_count == 0
    assert result.activity_accounting_complete is True
    assert calls["run"] == 0


def test_forged_runtime_contract_suppresses_child_launch() -> None:
    contract = parent.load_contract(repository=REPOSITORY)
    forged = contract.model_copy(update={"contract_id": f"ncpcontract_{'0' * 64}"})
    calls = {"run": 0}

    def run(*_args: Any, **_kwargs: Any) -> Any:
        calls["run"] += 1
        raise AssertionError("child launch crossed contract boundary")

    result = parent.run_isolated_diagnostic_child(
        forged,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        run=run,
    )

    assert result.error_code == "child_binding_error"
    assert result.launch_attempt_count == 0
    assert result.activity_accounting_complete is True
    assert result.unknown_post_launch_activity_possible is False
    assert calls["run"] == 0


def test_isolated_child_invocation_uses_exact_flags_environment_and_typed_output() -> None:
    contract = parent.load_contract(repository=REPOSITORY)
    observed: dict[str, Any] = {}
    raw = (json.dumps(_blocked_child_dict(), sort_keys=True, separators=(",", ":")) + "\n").encode()

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        observed["argv"] = argv
        observed["kwargs"] = kwargs
        return subprocess.CompletedProcess(argv, 0, stdout=raw, stderr=b"")

    result = parent.run_isolated_diagnostic_child(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        run=run,
    )

    assert result.child is not None and result.child.state == "blocked"
    assert result.passed is False
    assert tuple(observed["argv"][1:5]) == parent.CHILD_FLAGS
    assert observed["kwargs"]["env"] == parent.CHILD_ENVIRONMENT
    assert observed["kwargs"]["shell"] is False
    assert observed["kwargs"]["timeout"] == parent.CHILD_TIMEOUT_SECONDS


def test_child_launch_exception_is_fixed_and_preserves_unknown_activity() -> None:
    contract = parent.load_contract(repository=REPOSITORY)

    def run(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(SENSITIVE_EXCEPTION_TEXT)

    result = parent.run_isolated_diagnostic_child(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        run=run,
    )
    serialized = json.dumps(result.model_dump(mode="json"), sort_keys=True)

    assert result.error_code == "child_launch_error"
    assert result.launch_attempt_count == 1
    assert result.activity_accounting_complete is False
    assert result.unknown_post_launch_activity_possible is True
    assert SENSITIVE_EXCEPTION_TEXT not in serialized
    assert "RuntimeError" not in serialized


def test_parent_docker_block_suppresses_child_and_is_typed() -> None:
    contract = parent.load_contract(repository=REPOSITORY)
    calls = {"child": 0}

    def child_observer(*_args: Any, **_kwargs: Any) -> parent.ChildExecution:
        calls["child"] += 1
        raise AssertionError("child crossed Docker block")

    result = parent.run_parent_preflight(
        contract,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: _v3_docker_blocked(),
        child_observer=child_observer,
    )

    assert result.state == parent.ParentState.BLOCKED
    assert result.reason == parent.ParentReason.DOCKER_NOT_READY
    assert result.docker_cli_command_count == 8
    assert result.child_launch_attempt_count == 0
    assert result.activity_accounting_complete is True
    assert calls["child"] == 0


def test_parent_maps_ready_docker_and_missing_dotenv_to_blocked() -> None:
    contract = parent.load_contract(repository=REPOSITORY)
    execution = _blocked_child_execution()
    result = parent.run_parent_preflight(
        contract,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: _v5_docker_ready(),
        child_observer=lambda *_args, **_kwargs: execution,
    )

    assert result.state == parent.ParentState.BLOCKED
    assert result.reason == parent.ParentReason.DOTENV_NOT_READY
    assert result.child_launch_attempt_count == 1
    assert result.activity_accounting_complete is True
    assert result.network_call_count == 0


def test_parent_revalidates_child_observer_output() -> None:
    contract = parent.load_contract(repository=REPOSITORY)
    forged = _blocked_child_execution().model_copy(update={"passed": True})
    result = parent.run_parent_preflight(
        contract,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: _v5_docker_ready(),
        child_observer=lambda *_args, **_kwargs: forged,
    )

    assert result.state == parent.ParentState.ERROR
    assert result.reason == parent.ParentReason.CHILD_CHECKER_ERROR
    assert result.child_execution is not None
    assert result.child_execution.error_code == "parent_child_observer_error"
    assert result.activity_accounting_complete is False
    assert result.unknown_post_marker_activity_possible is True


def test_suppressed_child_accounting_matrix_is_fail_closed() -> None:
    invalid = {
        "parent_pythonhome_absent": True,
        "parent_pythonpath_absent": True,
        "launch_attempt_count": 0,
        "process_returned": False,
        "child": None,
        "error_code": "child_binding_error",
        "activity_accounting_complete": False,
        "unknown_post_launch_activity_possible": True,
        "passed": False,
    }
    with pytest.raises(ValidationError):
        parent.ChildExecution.model_validate(invalid)


def test_parent_observation_rejects_false_ready_projection() -> None:
    contract = parent.load_contract(repository=REPOSITORY)
    valid = parent.run_parent_preflight(
        contract,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: _v5_docker_ready(),
        child_observer=lambda *_args, **_kwargs: _blocked_child_execution(),
    ).model_dump(mode="json")
    valid["state"] = "ready"
    valid["reason"] = None
    valid["passed"] = True
    with pytest.raises(ValidationError):
        parent.ParentObservation.model_validate(valid)


def test_current_checkout_has_no_v7_state_approval_or_attempt_artifact() -> None:
    for path in (
        parent.STATE_PATH,
        parent.APPROVAL_RECEIPT_PATH,
        parent.APPROVAL_PATH,
        parent.ATTEMPT_PATH,
        parent.ACTION_STARTED_PATH,
        parent.TERMINAL_PATH,
    ):
        assert not (REPOSITORY / path).exists()


def test_run_once_fails_before_observer_without_state_and_approval() -> None:
    calls = {"observer": 0}

    def observer(*_args: Any, **_kwargs: Any) -> parent.ParentObservation:
        calls["observer"] += 1
        raise AssertionError("observer crossed authority boundary")

    with pytest.raises((FileNotFoundError, parent.SanitizedSDKParentError)):
        parent.run_once(repository=REPOSITORY, parent_observer=observer)
    assert calls["observer"] == 0
    assert not (REPOSITORY / parent.ATTEMPT_PATH).exists()
    assert not (REPOSITORY / parent.ACTION_STARTED_PATH).exists()
    assert not (REPOSITORY / parent.TERMINAL_PATH).exists()


def test_checked_in_source_qualification_when_present() -> None:
    if not (REPOSITORY / parent.QUALIFICATION_PATH).exists():
        pytest.skip("qualification is created only after the exact source commit")
    summary = parent.validate_source_qualification(repository=REPOSITORY)
    assert summary["external_observations_made"] == 0
    assert summary["external_mutations_made"] == 0
    assert summary["execution_authorized"] is False
