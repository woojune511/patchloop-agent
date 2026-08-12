from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from patchloop.evals import dual_pipe_preflight_successor as successor
from scripts import run_sanitized_sdk_bootstrap_dual_pipe_supervisor as outer_shim
from scripts import run_sanitized_sdk_bootstrap_supervised_frame_child as v17_child

REPOSITORY = Path(__file__).resolve().parents[1]
SENSITIVE = "sk-v19-dual-pipe-must-not-escape"
SYSTEMROOT = r"C:\synthetic-systemroot-must-not-persist"


@pytest.fixture(scope="module")
def contract() -> successor.DualPipeContract:
    return successor._build_contract(REPOSITORY)


@pytest.fixture(autouse=True)
def cached_contract(monkeypatch: pytest.MonkeyPatch, contract: successor.DualPipeContract) -> None:
    monkeypatch.setattr(successor, "load_contract", lambda **_kwargs: contract)
    v17_contract = successor.v17.SupervisedFrameContract.model_validate_json(
        (REPOSITORY / successor.v17.CONTRACT_PATH).read_bytes()
    )
    monkeypatch.setattr(successor.v17, "load_contract", lambda **_kwargs: v17_contract)
    v9_contract = successor.v9.ParentSuccessorContract.model_validate_json(
        (REPOSITORY / successor.v9.CONTRACT_PATH).read_bytes()
    )
    monkeypatch.setattr(successor.v9, "load_contract", lambda **_kwargs: v9_contract)


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


def _worker_outcome(message: dict[str, Any]) -> v17_child.WorkerProcessOutcome:
    return v17_child.WorkerProcessOutcome(
        launch_attempt_count=1,
        process_return_count=1,
        result_bytes=v17_child._canonical(message),
        result_within_limit=True,
        returncode=0,
        complete=True,
        unknown=False,
    )


def _success_envelope_bytes() -> bytes:
    message = v17_child._worker_success(_blocked_child())
    envelope = v17_child.build_supervised_envelope(
        REPOSITORY, worker_runner=lambda _root: _worker_outcome(message)
    )
    return v17_child._canonical(envelope)


def _outcome(
    *,
    payload: bytes = b"",
    returncode: int | None = 0,
    complete: bool = True,
    within_limit: bool = True,
) -> successor.SupervisorProcessOutcome:
    return successor.SupervisorProcessOutcome(
        launch_attempt_count=1,
        process_return_count=int(returncode is not None),
        result_bytes=payload,
        result_within_limit=within_limit,
        returncode=returncode,
        complete=complete,
        unknown=not complete,
    )


def _docker_blocked() -> dict[str, Any]:
    terminal = successor.v17.v15.v13.TerminalTransition.model_validate_json(
        (REPOSITORY / successor.v17.v15.v13.TERMINAL_PATH).read_bytes()
    )
    assert terminal.observation is not None
    assert terminal.observation.base.docker_observation is not None
    return terminal.observation.base.docker_observation


def _write_pipe_supervisor(path: Path, payload: bytes | None) -> None:
    path.write_text(
        f"""
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument('--repository', required=True)
channels = parser.add_mutually_exclusive_group(required=True)
channels.add_argument('--parent-result-handle', type=int)
channels.add_argument('--parent-result-fd', type=int)
args = parser.parse_args()
if os.name == 'nt':
    import msvcrt
    descriptor = msvcrt.open_osfhandle(
        args.parent_result_handle, os.O_WRONLY | os.O_BINARY
    )
else:
    descriptor = args.parent_result_fd
os.write(1, {SENSITIVE.encode()!r})
os.write(2, {SENSITIVE.encode()!r})
payload = {payload!r}
if payload is not None:
    os.write(descriptor, payload)
os.close(descriptor)
os._exit(0)
""",
        encoding="utf-8",
    )


def test_contract_binds_consumed_v18_without_claiming_cause(
    contract: successor.DualPipeContract,
) -> None:
    predecessor = contract.predecessor
    assert predecessor.evidence_commit == successor.V18_EVIDENCE_COMMIT
    assert predecessor.terminal_id.endswith("e5938acca516")
    assert predecessor.base_child_code == "child_output_invalid"
    assert predecessor.supervisor_code == "supervised_output_invalid"
    assert predecessor.envelope_received is False
    assert predecessor.activity_accounting_complete is False
    assert predecessor.unknown_post_marker_activity_possible is True
    assert predecessor.causal_detail_available is False
    assert predecessor.retry_or_resume_allowed is False
    assert contract.predecessor_retry_or_repair is False
    assert contract.execution_currently_authorized is False


def test_contract_limits_change_to_parent_supervisor_result_transport(
    contract: successor.DualPipeContract,
) -> None:
    runtime = contract.runtime
    assert contract.correction_scope == "parent-supervisor-result-transport-only"
    assert runtime.parent_to_supervisor_launch_limit == 1
    assert runtime.supervisor_to_worker_launch_limit == 1
    assert runtime.parent_supervisor_stdout_null_from_process_start is True
    assert runtime.parent_supervisor_stderr_null_from_process_start is True
    assert runtime.parent_result_uses_dedicated_anonymous_pipe is True
    assert runtime.v17_supervisor_worker_semantics_unchanged is True
    assert runtime.raw_supervisor_or_worker_output_persistence_allowed is False
    assert runtime.live_default_observers_exposed is False


def test_outer_supervisor_top_level_imports_remain_stdlib_only() -> None:
    tree = ast.parse((REPOSITORY / successor.SUPERVISOR_PATH).read_text(encoding="utf-8"))
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    imported = {alias.name.split(".", 1)[0] for node in imports for alias in node.names}
    assert "patchloop" not in imported
    assert "scripts" not in imported


def test_outer_shim_injected_builder_preserves_v17_envelope() -> None:
    expected = successor.v17.SupervisedFrameEnvelope.model_validate_json(
        _success_envelope_bytes()
    ).model_dump(mode="json")
    actual = outer_shim.build_pipe_envelope(
        REPOSITORY, supervisor_builder=lambda root: expected if root == REPOSITORY else {}
    )
    assert successor.v17.SupervisedFrameEnvelope.model_validate(actual).child is not None
    assert SENSITIVE not in json.dumps(actual)


def test_injected_child_maps_one_typed_result_pipe_envelope(
    contract: successor.DualPipeContract,
) -> None:
    seen: dict[str, Any] = {}

    def runner(root: Path, **kwargs: Any) -> successor.SupervisorProcessOutcome:
        seen.update({"root": root, **kwargs})
        return _outcome(payload=_success_envelope_bytes())

    result = successor.run_dual_pipe_child_injected(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda name: SYSTEMROOT if name == "SYSTEMROOT" else None,
        python=sys.executable,
        supervisor_runner=runner,
    )

    assert result.base.base.child is not None
    assert result.base.base.child.state == "blocked"
    assert result.base.envelope_received is True
    assert result.parent_supervisor_transport is not None
    assert result.parent_supervisor_transport.result_message_nonempty_count == 1
    assert result.activity_accounting_complete is True
    assert seen["systemroot"] == SYSTEMROOT
    assert seen["supervisor_script"] == REPOSITORY / successor.SUPERVISOR_PATH
    assert SYSTEMROOT not in result.model_dump_json()


@pytest.mark.parametrize(
    ("payload", "within_limit"),
    [(SENSITIVE.encode(), True), (b"{}", False), (b"", True)],
)
def test_invalid_result_pipe_fails_closed_without_raw_output(
    contract: successor.DualPipeContract, payload: bytes, within_limit: bool
) -> None:
    result = successor.run_dual_pipe_child_injected(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda _name: SYSTEMROOT,
        python=sys.executable,
        supervisor_runner=lambda *_args, **_kwargs: _outcome(
            payload=payload, within_limit=within_limit
        ),
    )

    assert result.base.supervisor_code == successor.v17.SupervisorCode.SUPERVISED_OUTPUT_INVALID
    assert result.base.envelope_received is False
    assert result.activity_accounting_complete is False
    assert result.unknown_workload_activity_possible is True
    assert SENSITIVE not in result.model_dump_json()


def test_injected_parent_keeps_docker_first_suppression(
    contract: successor.DualPipeContract,
) -> None:
    result = successor.run_parent_preflight_injected(
        contract,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: _docker_blocked(),
        child_observer=lambda *_args, **_kwargs: pytest.fail("child must not run"),
    )
    assert result.base.base.state == "blocked"
    assert result.base.base.reason == "docker_not_ready"
    assert result.dual_pipe_child_execution is None
    assert result.activity_accounting_complete is True


def test_forged_contract_suppresses_all_observers(
    contract: successor.DualPipeContract,
) -> None:
    forged = contract.model_copy(update={"content_hash": "sha256:" + "0" * 64})
    called = {"docker": 0, "child": 0}

    def docker(**_kwargs: Any) -> dict[str, Any]:
        called["docker"] += 1
        return _docker_blocked()

    def child(*_args: Any, **_kwargs: Any) -> successor.DualPipeChildExecution:
        called["child"] += 1
        raise AssertionError("forged contract must suppress child")

    result = successor.run_parent_preflight_injected(
        forged, repository=REPOSITORY, docker_observer=docker, child_observer=child
    )
    assert called == {"docker": 0, "child": 0}
    assert result.base.base.reason == "contract_binding_error"
    assert result.activity_accounting_complete is True


def test_real_supervisor_uses_anonymous_result_after_null_stdio(tmp_path: Path) -> None:
    script = tmp_path / "synthetic_dual_pipe_supervisor.py"
    _write_pipe_supervisor(script, _success_envelope_bytes())
    outcome = successor._run_supervisor_process(
        REPOSITORY,
        systemroot=SYSTEMROOT,
        supervisor_script=script,
        python=sys.executable,
    )
    typed = successor.v17.SupervisedFrameEnvelope.model_validate_json(outcome.result_bytes)
    assert outcome.returncode == 0
    assert outcome.complete is True
    assert typed.child is not None and typed.child.state == "blocked"
    assert SENSITIVE not in outcome.result_bytes.decode("utf-8")


def test_real_supervisor_hard_exit_without_message_is_incomplete(tmp_path: Path) -> None:
    script = tmp_path / "synthetic_empty_dual_pipe_supervisor.py"
    _write_pipe_supervisor(script, None)
    outcome = successor._run_supervisor_process(
        REPOSITORY,
        systemroot=SYSTEMROOT,
        supervisor_script=script,
        python=sys.executable,
    )
    assert outcome.returncode == 0
    assert outcome.result_bytes == b""
    assert outcome.complete is True
    result = successor.run_dual_pipe_child_injected(
        successor._build_contract(REPOSITORY),
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda _name: SYSTEMROOT,
        python=sys.executable,
        supervisor_runner=lambda *_args, **_kwargs: outcome,
    )
    assert result.base.supervisor_code == successor.v17.SupervisorCode.SUPERVISED_OUTPUT_INVALID
    assert result.activity_accounting_complete is False


def test_source_authority_has_no_activation_or_external_observation(
    contract: successor.DualPipeContract,
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
