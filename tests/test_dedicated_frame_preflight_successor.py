from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from patchloop.evals import dedicated_frame_preflight_successor as successor
from scripts import run_sanitized_sdk_bootstrap_dedicated_frame_child as child_script

REPOSITORY = Path(__file__).resolve().parents[1]
SENSITIVE = "sk-v15-dedicated-frame-must-not-escape"
SYSTEMROOT = r"C:\synthetic-systemroot-must-not-persist"


@pytest.fixture(scope="module")
def contract() -> successor.DedicatedFrameContract:
    return successor._build_contract(REPOSITORY)


@pytest.fixture(autouse=True)
def cached_contract(
    monkeypatch: pytest.MonkeyPatch, contract: successor.DedicatedFrameContract
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


def _envelope(*, child: dict[str, Any] | None = None, code: str | None = None) -> bytes:
    complete = child is not None or code == "diagnostic_wrapper_import_error"
    payload = {
        "schema_version": child_script.SCHEMA_VERSION,
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


def _docker_blocked() -> dict[str, Any]:
    terminal = successor.v13.TerminalTransition.model_validate_json(
        (REPOSITORY / successor.v13.TERMINAL_PATH).read_bytes()
    )
    assert terminal.observation is not None
    assert terminal.observation.base.docker_observation is not None
    return terminal.observation.base.docker_observation


def test_contract_binds_consumed_v14_without_claiming_cause(
    contract: successor.DedicatedFrameContract,
) -> None:
    assert contract.predecessor.evidence_commit == successor.V14_EVIDENCE_COMMIT
    assert contract.predecessor.terminal_id.endswith("d424e801e5f")
    assert contract.predecessor.frame_code == "framed_output_invalid"
    assert contract.predecessor.envelope_received is False
    assert contract.predecessor.activity_accounting_complete is False
    assert contract.predecessor.unknown_post_marker_activity_possible is True
    assert contract.predecessor.causal_detail_available is False
    assert contract.predecessor.retry_or_resume_allowed is False
    assert contract.predecessor_retry_or_repair is False
    assert contract.execution_currently_authorized is False


def test_contract_limits_change_to_dedicated_result_channel(
    contract: successor.DedicatedFrameContract,
) -> None:
    runtime = contract.runtime
    assert contract.correction_scope == "child-envelope-result-channel-only"
    assert runtime.result_descriptor_duplicated_before_workload is True
    assert runtime.workload_stdout_stderr_redirected_to_null is True
    assert runtime.envelope_written_directly_to_saved_descriptor is True
    assert runtime.fd1_fd2_restore_required_before_envelope is False
    assert runtime.raw_child_output_persistence_allowed is False
    assert runtime.live_default_observers_exposed is False


def test_real_windows_subprocess_uses_saved_descriptor_and_discards_noise() -> None:
    child_json = json.dumps(_blocked_child(), sort_keys=True, separators=(",", ":"))
    code = f"""
import json, os, sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root))
from scripts.run_sanitized_sdk_bootstrap_dedicated_frame_child import emit_dedicated_envelope
child = json.loads({child_json!r})
def noisy(_root):
    print({SENSITIVE!r})
    print({SENSITIVE!r}, file=sys.stderr)
    os.write(1, {SENSITIVE.encode()!r})
    os.write(2, {SENSITIVE.encode()!r})
    os.close(1)
    os.close(2)
    return child
emit_dedicated_envelope(root, diagnostic_runner=noisy, typed_validator=lambda value: value)
"""
    result = subprocess.run(
        [sys.executable, "-I", "-E", "-s", "-B", "-c", code, str(REPOSITORY)],
        cwd=REPOSITORY,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        shell=False,
        timeout=10,
        env={"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "SYSTEMROOT": r"C:\Windows"},
    )

    envelope = successor.v13.FramedChildEnvelope.model_validate_json(result.stdout)
    assert result.returncode == 0
    assert result.stderr == b""
    assert envelope.child is not None and envelope.child.state == "blocked"
    assert SENSITIVE.encode() not in result.stdout


def test_injected_parent_maps_one_typed_envelope(
    contract: successor.DedicatedFrameContract,
) -> None:
    seen: dict[str, Any] = {}

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        seen.update({"argv": argv, **kwargs})
        return subprocess.CompletedProcess(
            argv, 0, stdout=_envelope(child=_blocked_child()), stderr=b""
        )

    result = successor.run_dedicated_frame_child_injected(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda name: SYSTEMROOT if name == "SYSTEMROOT" else None,
        python=sys.executable,
        run=run,
    )

    assert result.base.child is not None and result.base.child.state == "blocked"
    assert result.envelope_received is True
    assert result.activity_accounting_complete is True
    assert seen["argv"][1:5] == list(successor.CHILD_FLAGS)
    assert seen["argv"][5].endswith("run_sanitized_sdk_bootstrap_dedicated_frame_child.py")
    assert seen["env"] == {**successor.FIXED_CHILD_ENVIRONMENT, "SYSTEMROOT": SYSTEMROOT}
    assert SYSTEMROOT not in result.model_dump_json()


def test_malformed_envelope_fails_closed_without_raw_output(
    contract: successor.DedicatedFrameContract,
) -> None:
    result = successor.run_dedicated_frame_child_injected(
        contract,
        repository=REPOSITORY,
        environment_present=lambda _name: False,
        environment_value=lambda _name: SYSTEMROOT,
        python=sys.executable,
        run=lambda argv, **_kwargs: subprocess.CompletedProcess(
            argv, 0, stdout=SENSITIVE.encode(), stderr=b""
        ),
    )

    assert result.frame_code == "framed_output_invalid"
    assert result.envelope_received is False
    assert result.activity_accounting_complete is False
    assert result.unknown_workload_activity_possible is True
    assert SENSITIVE not in result.model_dump_json()


def test_injected_parent_keeps_docker_first_suppression(
    contract: successor.DedicatedFrameContract,
) -> None:
    result = successor.run_parent_preflight_injected(
        contract,
        repository=REPOSITORY,
        docker_observer=lambda **_kwargs: _docker_blocked(),
        child_observer=lambda *_args, **_kwargs: pytest.fail("child must not run"),
    )

    assert result.base.state == "blocked"
    assert result.base.reason == "docker_not_ready"
    assert result.framed_child_execution is None
    assert result.activity_accounting_complete is True


def test_source_authority_has_no_activation_or_external_observation(
    contract: successor.DedicatedFrameContract,
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
    assert summary["execution_authorized"] is False
