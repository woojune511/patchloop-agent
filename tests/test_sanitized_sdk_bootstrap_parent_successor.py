from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.evals import executable_no_call_preflight as v3
from patchloop.evals import no_start_executable_preflight as v5
from patchloop.evals import sanitized_sdk_bootstrap_parent_successor as successor

REPOSITORY = Path(__file__).resolve().parents[1]
SENSITIVE_SYSTEMROOT = r"C:\must-never-persist\private-systemroot"
SENSITIVE_EXCEPTION = "must-never-persist-parent-exception"


@pytest.fixture(scope="module")
def contract() -> successor.ParentSuccessorContract:
    return successor.load_contract(repository=REPOSITORY)


@pytest.fixture(autouse=True)
def cached_contract_validation(
    monkeypatch: pytest.MonkeyPatch,
    contract: successor.ParentSuccessorContract,
) -> None:
    monkeypatch.setattr(successor, "load_contract", lambda **_kwargs: contract)


def _blocked_child() -> bytes:
    return json.dumps(
        {
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
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


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


def test_contract_binds_v8_and_keeps_live_authority_closed(
    contract: successor.ParentSuccessorContract,
) -> None:
    assert contract.predecessor.source_commit == successor.V8_SOURCE_COMMIT
    assert contract.predecessor.qualification_commit == successor.V8_QUALIFICATION_COMMIT
    assert contract.runtime_profile.passthrough_environment_names == ("SYSTEMROOT",)
    assert contract.runtime_profile.bootstrap_child_path.endswith(
        "run_sanitized_sdk_import_bootstrap_child.py"
    )
    assert contract.runtime_profile.diagnostic_child_path.endswith(
        "run_sanitized_sdk_diagnostic_child.py"
    )
    assert contract.runtime_profile.docker_expected_command_count == 8
    assert contract.runtime_profile.systemroot_value_return_hash_prefix_or_length_limit == 0
    assert contract.runtime_profile.parent_runtime_integration_implemented is True
    assert contract.runtime_profile.injected_observer_tests_only is True
    assert contract.transition_policy.fresh_state_required is True
    assert contract.transition_policy.approval_attempt_limit == 1
    assert contract.transition_policy.retry_replacement_or_resume_allowed is False
    assert contract.source_authority.runtime_execution_authorized is False
    assert contract.source_authority.state_approval_attempt_or_terminal_creation_authorized is False


def test_dirty_parent_suppresses_systemroot_and_child_observation(
    contract: successor.ParentSuccessorContract,
) -> None:
    calls: list[str] = []
    result = successor.run_isolated_diagnostic_child(
        contract,
        repository=REPOSITORY,
        environment_present=lambda name: name == "PYTHONHOME",
        environment_value=lambda name: calls.append(name) or SENSITIVE_SYSTEMROOT,
        run=lambda *_args, **_kwargs: pytest.fail("child must not run"),
    )

    assert result.code == "parent_python_environment_not_clean"
    assert result.activity.child_launch_attempt_count == 0
    assert result.activity.systemroot_membership_check_count == 0
    assert calls == []


def test_parent_presence_exception_is_sanitized_and_counted(
    contract: successor.ParentSuccessorContract,
) -> None:
    def present(name: str) -> bool:
        if name == "PYTHONPATH":
            raise RuntimeError(SENSITIVE_EXCEPTION)
        return False

    result = successor.run_isolated_diagnostic_child(
        contract,
        repository=REPOSITORY,
        environment_present=present,
        environment_value=lambda _name: pytest.fail("SYSTEMROOT must not be read"),
        run=lambda *_args, **_kwargs: pytest.fail("child must not run"),
    )
    serialized = result.model_dump_json()

    assert result.code == "parent_presence_error"
    assert result.activity.parent_environment_membership_check_count == 2
    assert result.activity.parent_environment_membership_check_completed_count == 1
    assert result.activity.child_launch_attempt_count == 0
    assert SENSITIVE_EXCEPTION not in serialized


@pytest.mark.parametrize(
    ("systemroot", "expected"), ((None, "systemroot_missing"), ("", "systemroot_empty"))
)
def test_missing_or_empty_systemroot_suppresses_child(
    systemroot: str | None,
    expected: str,
    contract: successor.ParentSuccessorContract,
) -> None:
    result = successor.run_isolated_diagnostic_child(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda _name: systemroot,
        run=lambda *_args, **_kwargs: pytest.fail("child must not run"),
    )

    assert result.code == expected
    assert result.activity.child_launch_attempt_count == 0
    assert result.activity.systemroot_value_passed_to_child_count == 0


def test_environment_exception_is_sanitized_and_suppresses_child(
    contract: successor.ParentSuccessorContract,
) -> None:
    def environment_value(_name: str) -> str | None:
        raise RuntimeError(SENSITIVE_EXCEPTION)

    result = successor.run_isolated_diagnostic_child(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=environment_value,
        run=lambda *_args, **_kwargs: pytest.fail("child must not run"),
    )
    serialized = result.model_dump_json()

    assert result.code == "systemroot_presence_error"
    assert result.activity.child_launch_attempt_count == 0
    assert SENSITIVE_EXCEPTION not in serialized
    assert "RuntimeError" not in serialized


def test_forged_runtime_contract_suppresses_child(
    contract: successor.ParentSuccessorContract,
) -> None:
    forged = contract.model_copy(update={"content_hash": "sha256:" + "0" * 64})
    result = successor.run_isolated_diagnostic_child(
        forged,
        repository=REPOSITORY,
        environment_present=lambda _name: pytest.fail("environment must not be read"),
        environment_value=lambda _name: pytest.fail("SYSTEMROOT must not be read"),
        run=lambda *_args, **_kwargs: pytest.fail("child must not run"),
    )

    assert result.code == "child_binding_error"
    assert result.activity.child_launch_attempt_count == 0


def test_forged_parent_contract_suppresses_docker(
    contract: successor.ParentSuccessorContract,
) -> None:
    forged = contract.model_copy(update={"content_hash": "sha256:" + "0" * 64})
    result = successor.run_parent_preflight(
        forged,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: pytest.fail("Docker must not be observed"),
        child_observer=lambda *_args, **_kwargs: pytest.fail("child must not run"),
    )

    assert result.state == successor.ParentState.ERROR
    assert result.reason == successor.ParentReason.CONTRACT_BINDING_ERROR
    assert result.docker_observation is None
    assert result.activity_accounting_complete is True
    assert result.unknown_post_marker_activity_possible is False


def test_exact_child_invocation_passes_systemroot_only_in_environment(
    contract: successor.ParentSuccessorContract,
) -> None:
    seen: dict[str, Any] = {}

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        seen.update({"argv": argv, **kwargs})
        return subprocess.CompletedProcess(argv, 0, stdout=_blocked_child(), stderr=b"")

    result = successor.run_isolated_diagnostic_child(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda name: SENSITIVE_SYSTEMROOT if name == "SYSTEMROOT" else None,
        run=run,
    )
    serialized = result.model_dump_json()

    assert result.passed is False
    assert result.child is not None and result.child.state == "blocked"
    assert seen["argv"][1:5] == list(successor.CHILD_FLAGS)
    assert seen["argv"][5].endswith("run_sanitized_sdk_diagnostic_child.py")
    assert seen["argv"][6:] == ["--repository", str(REPOSITORY.resolve())]
    assert seen["env"] == {
        **successor.FIXED_CHILD_ENVIRONMENT,
        "SYSTEMROOT": SENSITIVE_SYSTEMROOT,
    }
    assert seen["shell"] is False
    assert SENSITIVE_SYSTEMROOT not in json.dumps(seen["argv"])
    assert SENSITIVE_SYSTEMROOT not in serialized
    assert result.activity.systemroot_value_passed_to_child_count == 1
    assert result.child.activity.network_call_count == 0


def test_launch_exception_is_value_free_and_unknown_activity_is_explicit(
    contract: successor.ParentSuccessorContract,
) -> None:
    def run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        raise RuntimeError(SENSITIVE_EXCEPTION)

    result = successor.run_isolated_diagnostic_child(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda _name: SENSITIVE_SYSTEMROOT,
        run=run,
    )
    serialized = result.model_dump_json()

    assert result.code == "child_launch_error"
    assert result.activity_accounting_complete is False
    assert result.unknown_post_launch_activity_possible is True
    assert SENSITIVE_SYSTEMROOT not in serialized
    assert SENSITIVE_EXCEPTION not in serialized


def test_parent_docker_block_suppresses_corrected_child(
    contract: successor.ParentSuccessorContract,
) -> None:
    calls: list[str] = []

    def child_observer(*_args: Any, **_kwargs: Any) -> successor.ParentChildExecution:
        calls.append("child")
        raise AssertionError("child crossed Docker block")

    result = successor.run_parent_preflight(
        contract,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: _docker_blocked(),
        child_observer=child_observer,
    )

    assert result.state == successor.ParentState.BLOCKED
    assert result.reason == successor.ParentReason.DOCKER_NOT_READY
    assert result.docker_cli_command_count == 8
    assert result.child_launch_attempt_count == 0
    assert calls == []


def test_parent_maps_ready_docker_and_missing_dotenv_to_blocked(
    contract: successor.ParentSuccessorContract,
) -> None:
    execution = successor.run_isolated_diagnostic_child(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda _name: SENSITIVE_SYSTEMROOT,
        run=lambda argv, **_kwargs: subprocess.CompletedProcess(
            argv, 0, stdout=_blocked_child(), stderr=b""
        ),
    )
    result = successor.run_parent_preflight(
        contract,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: _docker_ready(),
        child_observer=lambda *_args, **_kwargs: execution,
    )

    assert result.state == successor.ParentState.BLOCKED
    assert result.reason == successor.ParentReason.DOTENV_NOT_READY
    assert result.child_launch_attempt_count == 1
    assert result.network_call_count == 0
    assert result.provider_evaluator_agent_call_count == 0
    assert result.activity_accounting_complete is True


def test_parent_revalidates_child_observer_and_fails_unknown(
    contract: successor.ParentSuccessorContract,
) -> None:
    execution = successor.run_isolated_diagnostic_child(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda _name: None,
        run=lambda *_args, **_kwargs: pytest.fail("child must not run"),
    )
    forged = execution.model_copy(update={"passed": True})
    result = successor.run_parent_preflight(
        contract,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: _docker_ready(),
        child_observer=lambda *_args, **_kwargs: forged,
    )

    assert result.state == successor.ParentState.ERROR
    assert result.reason == successor.ParentReason.CHILD_CHECKER_ERROR
    assert result.child_execution is not None
    assert result.child_execution.code == "parent_child_observer_error"
    assert result.network_call_count is None
    assert result.activity_accounting_complete is False
    assert result.unknown_post_marker_activity_possible is True


@pytest.mark.parametrize(
    ("returncode", "stderr", "stdout", "expected"),
    (
        (1, b"", b"", "child_nonzero_exit"),
        (0, b"not-empty", b"", "child_stderr_not_empty"),
        (0, b"", b"x" * (successor.CHILD_OUTPUT_LIMIT + 1), "child_output_limit"),
        (0, b"", b"{}", "child_output_invalid"),
    ),
    ids=("nonzero", "stderr", "oversize", "invalid-json"),
)
def test_returned_child_failures_are_fixed_and_accounted(
    returncode: int,
    stderr: bytes,
    stdout: bytes,
    expected: str,
    contract: successor.ParentSuccessorContract,
) -> None:
    result = successor.run_isolated_diagnostic_child(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda _name: SENSITIVE_SYSTEMROOT,
        run=lambda argv, **_kwargs: subprocess.CompletedProcess(
            argv, returncode, stdout=stdout, stderr=stderr
        ),
    )

    assert result.code == expected
    assert result.activity_accounting_complete is True
    assert result.unknown_post_launch_activity_possible is False
    assert SENSITIVE_SYSTEMROOT not in result.model_dump_json()


def test_typed_result_rejects_false_ready_projection(
    contract: successor.ParentSuccessorContract,
) -> None:
    result = successor.run_isolated_diagnostic_child(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda _name: None,
        run=lambda *_args, **_kwargs: pytest.fail("child must not run"),
    )
    payload = result.model_dump(mode="json")
    payload["passed"] = True
    with pytest.raises(ValidationError):
        successor.ParentChildExecution.model_validate(payload)

    payload = result.model_dump(mode="json")
    payload["activity"]["parent_environment_membership_check_completed_count"] = 1
    with pytest.raises(ValidationError):
        successor.ParentChildExecution.model_validate(payload)


def test_parent_observation_rejects_false_ready_projection(
    contract: successor.ParentSuccessorContract,
) -> None:
    execution = successor.run_isolated_diagnostic_child(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda _name: SENSITIVE_SYSTEMROOT,
        run=lambda argv, **_kwargs: subprocess.CompletedProcess(
            argv, 0, stdout=_blocked_child(), stderr=b""
        ),
    )
    payload = successor.run_parent_preflight(
        contract,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: _docker_ready(),
        child_observer=lambda *_args, **_kwargs: execution,
    ).model_dump(mode="json")
    payload.update({"state": "ready", "reason": None, "passed": True})
    with pytest.raises(ValidationError):
        successor.ParentObservation.model_validate(payload)


def test_checked_in_source_qualification_when_present() -> None:
    if not (REPOSITORY / successor.QUALIFICATION_PATH).exists():
        pytest.skip("qualification is created only after the exact source commit")
    summary = successor.validate_source_qualification(repository=REPOSITORY)
    assert summary["external_observations_made"] == 0
    assert summary["external_mutations_made"] == 0
    assert summary["execution_authorized"] is False
