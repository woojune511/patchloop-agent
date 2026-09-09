from __future__ import annotations

import subprocess

import pytest

from patchloop.contracts import RegisteredCheck
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.runner import _batch_execution_abort
from patchloop.sandbox.runner import DockerSandbox, SandboxCleanupError
from patchloop.util import sha256_json


def _failing_docker(monkeypatch, error, *, cleanup_confirmed):
    original_run = subprocess.run
    commands = []
    launched = False

    def run(command, **kwargs):
        nonlocal launched
        if command[0] != "fake-docker":
            return original_run(command, **kwargs)
        commands.append(command)
        if command[1] == "run":
            launched = True
            raise error
        assert command[1:3] == ["container", "inspect"]
        if launched and not cleanup_confirmed:
            raise OSError("synthetic cleanup transport error")
        return subprocess.CompletedProcess(
            command, 1, b"", b"No such container: " + command[-1].encode(),
        )

    monkeypatch.setattr(DockerSandbox, "cli_path", staticmethod(lambda: "fake-docker"))
    monkeypatch.setattr(subprocess, "run", run)
    return commands


@pytest.mark.parametrize("error_type", [OSError, RuntimeError, KeyboardInterrupt])
@pytest.mark.parametrize("cleanup_confirmed", [True, False])
def test_docker_exception_retains_cleanup_outcome(
    tmp_path, monkeypatch, error_type, cleanup_confirmed,
):
    error = error_type("synthetic launch interruption")
    commands = _failing_docker(monkeypatch, error, cleanup_confirmed=cleanup_confirmed)
    expected = error_type if cleanup_confirmed else SandboxCleanupError
    with pytest.raises(expected) as caught:
        DockerSandbox("test@sha256:" + "a" * 64).run_check(
            tmp_path, RegisteredCheck(id="check", command=["python", "-c", "pass"]),
        )
    assert sum(command[1] == "run" for command in commands) == 1
    assert len(commands) == 2
    if cleanup_confirmed:
        assert caught.value is error
    else:
        assert caught.value.__cause__ is error
        details = caught.value.details
        assert details["cleanup_failed"] is True
        assert details["execution_error_type"] == error_type.__name__
        assert details["execution_policy"]["cleanup_status"] == "failed"
        assert details["execution_policy_hash"] == sha256_json(details["execution_policy"])


@pytest.mark.parametrize("cleanup_confirmed", [True, False])
def test_gateway_cleanup_exception_preserves_abort_and_replay(
    gateway_factory, monkeypatch, cleanup_confirmed,
):
    gateway, journal, _ = gateway_factory(sandbox=DockerSandbox("test@sha256:" + "a" * 64))
    commands = _failing_docker(
        monkeypatch, OSError("synthetic launch error"), cleanup_confirmed=cleanup_confirmed,
    )
    call = RequestedTool(
        name="run_check", action_id="cleanup-check",
        arguments={"check_id": gateway.public_task.visible_checks[0].id},
        turn_decision=PublicTurnDecision(mode="verify", basis="Observe public behavior"),
    )
    result = gateway.execute(call)
    before = journal.path.read_bytes()
    call_count = len(commands)
    replay = gateway.execute(call)
    assert replay.replayed is True
    assert replay.model_dump(exclude={"replayed"}) == result.model_dump(exclude={"replayed"})
    assert len(commands) == call_count
    assert journal.path.read_bytes() == before
    terminal, message = _batch_execution_abort([result])
    assert result.status == "failed"
    assert "public_check_failure" not in result.output
    if cleanup_confirmed:
        assert result.error_code == "TOOL_CONTRACT_ERROR"
        assert terminal is message is None
    else:
        assert result.error_code == "SANDBOX_CLEANUP_FAILED"
        assert result.output["cleanup_failed"] is True
        assert terminal == "TASK_FAILED"
        assert message == "owned sandbox cleanup could not be confirmed"
