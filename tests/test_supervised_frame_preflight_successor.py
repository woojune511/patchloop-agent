from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from patchloop.evals import supervised_frame_preflight_successor as successor
from scripts import run_sanitized_sdk_bootstrap_supervised_frame_child as child_script

REPOSITORY = Path(__file__).resolve().parents[1]
SENSITIVE = "sk-v17-supervised-frame-must-not-escape"
SYSTEMROOT = r"C:\synthetic-systemroot-must-not-persist"


@pytest.fixture(scope="module")
def contract() -> successor.SupervisedFrameContract:
    return successor._build_contract(REPOSITORY)


@pytest.fixture(autouse=True)
def cached_contract(
    monkeypatch: pytest.MonkeyPatch, contract: successor.SupervisedFrameContract
) -> None:
    monkeypatch.setattr(successor, "load_contract", lambda **_kwargs: contract)


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


def _worker_outcome(
    *,
    message: dict[str, Any] | None = None,
    returncode: int = 0,
    complete: bool = True,
) -> child_script.WorkerProcessOutcome:
    raw = b"" if message is None else child_script._canonical(message)
    return child_script.WorkerProcessOutcome(
        launch_attempt_count=1,
        process_return_count=1,
        result_bytes=raw,
        result_within_limit=True,
        returncode=returncode,
        complete=complete,
        unknown=not complete,
    )


def _success_envelope_bytes() -> bytes:
    worker = child_script._worker_success(_blocked_child())
    value = child_script.build_supervised_envelope(
        REPOSITORY, worker_runner=lambda _root: _worker_outcome(message=worker)
    )
    return child_script._canonical(value)


def _docker_blocked() -> dict[str, Any]:
    terminal = successor.v15.v13.TerminalTransition.model_validate_json(
        (REPOSITORY / successor.v15.v13.TERMINAL_PATH).read_bytes()
    )
    assert terminal.observation is not None
    assert terminal.observation.base.docker_observation is not None
    return terminal.observation.base.docker_observation


def _write_pipe_worker(path: Path, payload: bytes | None) -> None:
    payload_literal = repr(payload)
    path.write_text(
        f"""
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument('--repository', required=True)
channels = parser.add_mutually_exclusive_group(required=True)
channels.add_argument('--worker-result-handle', type=int)
channels.add_argument('--worker-result-fd', type=int)
args = parser.parse_args()
if os.name == 'nt':
    import msvcrt
    descriptor = msvcrt.open_osfhandle(
        args.worker_result_handle, os.O_WRONLY | os.O_BINARY
    )
else:
    descriptor = args.worker_result_fd
os.write(1, {SENSITIVE.encode()!r})
os.write(2, {SENSITIVE.encode()!r})
os.close(1)
os.close(2)
payload = {payload_literal}
if payload is not None:
    os.write(descriptor, payload)
os.close(descriptor)
os._exit(0)
""",
        encoding="utf-8",
    )


def test_contract_binds_consumed_v16_without_claiming_cause(
    contract: successor.SupervisedFrameContract,
) -> None:
    predecessor = contract.predecessor
    assert predecessor.evidence_commit == successor.V16_EVIDENCE_COMMIT
    assert predecessor.terminal_id.endswith("896f8737c907")
    assert predecessor.frame_code == "framed_output_invalid"
    assert predecessor.envelope_received is False
    assert predecessor.activity_accounting_complete is False
    assert predecessor.unknown_post_marker_activity_possible is True
    assert predecessor.causal_detail_available is False
    assert predecessor.retry_or_resume_allowed is False
    assert contract.predecessor_retry_or_repair is False
    assert contract.execution_currently_authorized is False


def test_contract_limits_change_to_supervisor_worker_pipe(
    contract: successor.SupervisedFrameContract,
) -> None:
    runtime = contract.runtime
    assert contract.correction_scope == "supervisor-worker-process-and-result-pipe-only"
    assert runtime.parent_to_supervisor_launch_limit == 1
    assert runtime.supervisor_to_worker_launch_limit == 1
    assert runtime.supervisor_stdlib_only_until_worker_result is True
    assert runtime.diagnostic_workload_runs_only_in_worker is True
    assert runtime.worker_stdout_stderr_null_from_process_start is True
    assert runtime.worker_result_uses_dedicated_anonymous_pipe is True
    assert runtime.supervisor_alone_owns_parent_stdout is True
    assert runtime.raw_supervisor_or_worker_output_persistence_allowed is False
    assert runtime.live_default_observers_exposed is False


def test_supervisor_top_level_imports_remain_stdlib_only() -> None:
    tree = ast.parse((REPOSITORY / successor.CHILD_PATH).read_text(encoding="utf-8"))
    top_level_imports = [
        node
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    imported = {
        alias.name.split(".", 1)[0]
        for node in top_level_imports
        for alias in node.names
    }
    assert "patchloop" not in imported
    assert "scripts" not in imported


@pytest.mark.skipif(os.name != "nt", reason="v17 Windows handle inheritance regression")
def test_real_windows_worker_uses_anonymous_handle_after_stdio_close(tmp_path: Path) -> None:
    message = child_script._worker_success(_blocked_child())
    worker = tmp_path / "synthetic_pipe_worker.py"
    _write_pipe_worker(worker, child_script._canonical(message))

    outcome = child_script.run_worker_process(
        REPOSITORY,
        worker_script=worker,
        python=sys.executable,
    )
    envelope = child_script.build_supervised_envelope(
        REPOSITORY, worker_runner=lambda _root: outcome
    )
    typed = successor.SupervisedFrameEnvelope.model_validate(envelope)

    assert outcome.returncode == 0
    assert outcome.complete is True
    assert typed.child is not None and typed.child.state == "blocked"
    assert typed.activity.worker_launch_attempt_count == 1
    assert typed.activity.worker_process_return_count == 1
    assert typed.activity.worker_result_message_count == 1
    assert SENSITIVE not in json.dumps(envelope)


@pytest.mark.skipif(os.name != "nt", reason="v17 Windows handle inheritance regression")
def test_worker_hard_exit_without_message_becomes_fixed_incomplete_error(
    tmp_path: Path,
) -> None:
    worker = tmp_path / "synthetic_empty_worker.py"
    _write_pipe_worker(worker, None)
    outcome = child_script.run_worker_process(
        REPOSITORY,
        worker_script=worker,
        python=sys.executable,
    )
    envelope = child_script.build_supervised_envelope(
        REPOSITORY, worker_runner=lambda _root: outcome
    )
    typed = successor.SupervisedFrameEnvelope.model_validate(envelope)

    assert typed.child is None
    assert typed.code == successor.SupervisorCode.WORKER_RESULT_INVALID
    assert typed.activity.activity_accounting_complete is False
    assert typed.activity.unknown_workload_activity_possible is True
    assert SENSITIVE not in json.dumps(envelope)


def test_injected_parent_maps_one_typed_supervisor_envelope(
    contract: successor.SupervisedFrameContract,
) -> None:
    seen: dict[str, Any] = {}

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        seen.update({"argv": argv, **kwargs})
        return subprocess.CompletedProcess(
            argv, 0, stdout=_success_envelope_bytes(), stderr=b""
        )

    result = successor.run_supervised_frame_child_injected(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda name: SYSTEMROOT if name == "SYSTEMROOT" else None,
        python=sys.executable,
        run=run,
    )

    assert result.base.child is not None and result.base.child.state == "blocked"
    assert result.envelope_received is True
    assert result.worker_launch_attempt_count == 1
    assert result.worker_process_return_count == 1
    assert result.worker_result_message_count == 1
    assert result.activity_accounting_complete is True
    assert seen["argv"][1:5] == list(successor.CHILD_FLAGS)
    assert seen["argv"][5].endswith(
        "run_sanitized_sdk_bootstrap_supervised_frame_child.py"
    )
    assert seen["env"] == {**successor.FIXED_CHILD_ENVIRONMENT, "SYSTEMROOT": SYSTEMROOT}
    assert SYSTEMROOT not in result.model_dump_json()


def test_malformed_outer_envelope_fails_closed_without_raw_output(
    contract: successor.SupervisedFrameContract,
) -> None:
    result = successor.run_supervised_frame_child_injected(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda _name: SYSTEMROOT,
        python=sys.executable,
        run=lambda argv, **_kwargs: subprocess.CompletedProcess(
            argv, 0, stdout=SENSITIVE.encode(), stderr=b""
        ),
    )

    assert result.supervisor_code == successor.SupervisorCode.SUPERVISED_OUTPUT_INVALID
    assert result.envelope_received is False
    assert result.activity_accounting_complete is False
    assert result.unknown_workload_activity_possible is True
    assert SENSITIVE not in result.model_dump_json()


def test_injected_parent_keeps_docker_first_suppression(
    contract: successor.SupervisedFrameContract,
) -> None:
    result = successor.run_parent_preflight_injected(
        contract,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: _docker_blocked(),
        child_observer=lambda *_args, **_kwargs: pytest.fail("child must not run"),
    )

    assert result.base.state == "blocked"
    assert result.base.reason == "docker_not_ready"
    assert result.supervised_child_execution is None
    assert result.activity_accounting_complete is True


def test_forged_contract_suppresses_all_observers(
    contract: successor.SupervisedFrameContract,
) -> None:
    forged = contract.model_copy(update={"content_hash": "sha256:" + "0" * 64})
    called = {"docker": 0, "child": 0}

    def docker(**_kwargs: Any) -> dict[str, Any]:
        called["docker"] += 1
        return _docker_blocked()

    def child(*_args: Any, **_kwargs: Any) -> successor.SupervisedChildExecution:
        called["child"] += 1
        raise AssertionError("forged contract must suppress child")

    result = successor.run_parent_preflight_injected(
        forged,
        repository=REPOSITORY,
        docker_observer=docker,
        child_observer=child,
    )

    assert called == {"docker": 0, "child": 0}
    assert result.base.reason == "contract_binding_error"
    assert result.activity_accounting_complete is True


def test_source_authority_has_no_activation_or_external_observation(
    contract: successor.SupervisedFrameContract,
) -> None:
    authority = contract.authority
    assert authority.source_qualification_authorized is True
    assert authority.state_approval_attempt_or_terminal_creation_authorized is False
    assert authority.environment_docker_dotenv_sdk_or_network_observation_authorized is False
    assert authority.provider_evaluator_agent_execution_authorized is False
    assert contract.next_gate == "new-versioned-state-and-activation-wrapper-required"


def test_checked_in_source_qualification_when_present() -> None:
    if not (REPOSITORY / successor.QUALIFICATION_PATH).exists():
        pytest.skip("qualification is created only after the exact source commit")
    summary = successor.validate_source_qualification(repository=REPOSITORY)
    assert summary["external_observations_made"] == 0
    assert summary["external_mutations_made"] == 0
    assert summary["execution_authorized"] is False
