from __future__ import annotations

import ast
import io
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from patchloop.contracts import RegisteredCheck
from patchloop.sandbox import DockerSandbox, LocalSandbox
from patchloop.sandbox.runner import PROBE_IMAGE

_IMAGE_ID = f"sha256:{'a' * 64}"
_OTHER_IMAGE_ID = f"sha256:{'b' * 64}"
_CONTAINER_ID = "c" * 64


def _probe_control_result(
    command: list[str],
    *,
    stale_container_ids: bytes = b"",
    cleanup_returncode: int = 0,
    cleanup_remaining: bytes = b"",
    actual_image_identity: str = _IMAGE_ID,
) -> subprocess.CompletedProcess[bytes]:
    if command[1:3] == ["image", "inspect"]:
        return subprocess.CompletedProcess(
            command,
            0,
            (_IMAGE_ID + "\n").encode(),
            b"",
        )
    if command[1] == "create":
        return subprocess.CompletedProcess(
            command,
            0,
            (_CONTAINER_ID + "\n").encode(),
            b"",
        )
    if command[1:3] == ["container", "inspect"]:
        return subprocess.CompletedProcess(
            command,
            0,
            (actual_image_identity + "\n").encode(),
            b"",
        )
    if command[1:3] == ["ps", "--all"]:
        is_reaper = any(
            item == "label=io.patchloop.managed=probe"
            for item in command
        )
        return subprocess.CompletedProcess(
            command,
            0,
            stale_container_ids if is_reaper else cleanup_remaining,
            b"",
        )
    if command[1:3] == ["rm", "--force"]:
        return subprocess.CompletedProcess(
            command,
            cleanup_returncode,
            b"",
            b"cleanup failed" if cleanup_returncode else b"",
        )
    raise AssertionError(f"unexpected Docker control command: {command}")


def test_probe_runner_is_stdlib_only_and_copied_into_clean_image() -> None:
    source = Path("docker/probe_runner.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        str(node.module).split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module != "__future__"
    )
    assert imported == {
        "contextlib",
        "ctypes",
        "errno",
        "os",
        "platform",
        "signal",
        "sys",
        "time",
        "traceback",
    }
    dockerfile = Path("docker/Dockerfile.sandbox").read_text(
        encoding="utf-8"
    )
    assert (
        "COPY --chmod=0555 probe_runner.py "
        "/opt/patchloop/probe_runner.py"
    ) in dockerfile


class _RecordingInput:
    def __init__(self) -> None:
        self.data = bytearray()
        self.closed = False

    def write(self, value: bytes) -> int:
        self.data.extend(value)
        return len(value)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


class _FakeProbeProcess:
    def __init__(
        self,
        *,
        stdout: bytes = b"",
        stderr: bytes = b"",
        times_out: bool = False,
        exit_code: int = 0,
    ) -> None:
        self.stdin = _RecordingInput()
        self.stdout = io.BytesIO(stdout)
        self.stderr = io.BytesIO(stderr)
        self.times_out = times_out
        self.exit_code = exit_code
        self.killed = False

    def wait(self, timeout=None) -> int:
        if self.times_out and not self.killed:
            raise subprocess.TimeoutExpired(["docker", "run"], timeout)
        return -9 if self.killed else self.exit_code

    def kill(self) -> None:
        self.killed = True


def test_docker_cli_discovers_per_user_windows_install(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("PATCHLOOP_DOCKER_CLI", raising=False)
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    docker_cli = (
        tmp_path / "Programs" / "DockerDesktop" / "resources" / "bin" / "docker.exe"
    )
    docker_cli.parent.mkdir(parents=True)
    docker_cli.touch()

    assert DockerSandbox.cli_path() == str(docker_cli)


def test_docker_cli_override_requires_an_existing_file(tmp_path, monkeypatch) -> None:
    docker_cli = tmp_path / "docker.exe"
    monkeypatch.setenv("PATCHLOOP_DOCKER_CLI", str(docker_cli))
    assert DockerSandbox.cli_path() is None

    docker_cli.touch()
    assert DockerSandbox.cli_path() == str(docker_cli)


def test_docker_cli_ignores_inaccessible_install_candidates(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("PATCHLOOP_DOCKER_CLI", raising=False)
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    def deny_stat(_path: Path) -> bool:
        raise PermissionError("inaccessible Docker install")

    monkeypatch.setattr(Path, "is_file", deny_stat)
    assert DockerSandbox.cli_path() is None


def test_docker_availability_probe_uses_binary_output(monkeypatch) -> None:
    monkeypatch.setattr(
        DockerSandbox, "cli_path", staticmethod(lambda: "C:\\tools\\docker.exe")
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(
            command, 0, b"\xffserver", b""
        ),
    )

    assert DockerSandbox.available() is True


def test_docker_identity_probe_handles_timeout(monkeypatch) -> None:
    monkeypatch.setattr(
        DockerSandbox, "cli_path", staticmethod(lambda: "C:\\tools\\docker.exe")
    )

    def timeout(command, **_kwargs):
        raise subprocess.TimeoutExpired(command, 10)

    monkeypatch.setattr(subprocess, "run", timeout)

    assert DockerSandbox().image_identity() is None


def test_probe_image_identity_ignores_task_evaluator_image(
    monkeypatch,
) -> None:
    docker = "C:\\tools\\docker.exe"
    calls: list[list[str]] = []
    monkeypatch.setattr(DockerSandbox, "cli_path", staticmethod(lambda: docker))

    def inspect(command, **_kwargs):
        calls.append(list(command))
        return _probe_control_result(list(command))

    monkeypatch.setattr(subprocess, "run", inspect)

    assert (
        DockerSandbox("task-evaluator-image").probe_image_identity()
        == _IMAGE_ID
    )
    assert calls == [
        [
            docker,
            "image",
            "inspect",
            PROBE_IMAGE,
            "--format",
            "{{.Id}}",
        ]
    ]


def test_local_sandbox_truncates_output(tmp_path) -> None:
    result = LocalSandbox().run_check(
        tmp_path,
        RegisteredCheck(
            id="large-output",
            command=["python", "-c", "print('x' * 1000)"],
            output_limit_bytes=64,
        ),
    )
    assert result.exit_code == 0
    assert result.truncated is True
    assert len(result.stdout.encode()) <= 64


def test_local_sandbox_reports_timeout(tmp_path) -> None:
    result = LocalSandbox().run_check(
        tmp_path,
        RegisteredCheck(
            id="timeout",
            command=["python", "-c", "import time; time.sleep(2)"],
            timeout_seconds=1,
        ),
    )
    assert result.timed_out is True
    assert result.exit_code is None


def test_local_sandbox_rejects_agent_authored_probe(tmp_path, monkeypatch) -> None:
    def unexpected_subprocess(*_args, **_kwargs):
        raise AssertionError("LocalSandbox must not execute an agent-authored probe")

    monkeypatch.setattr(subprocess, "run", unexpected_subprocess)

    with pytest.raises(
        RuntimeError,
        match="agent-authored probes require an isolated Docker sandbox",
    ):
        LocalSandbox().run_probe(
            tmp_path,
            "print('must-not-run')",
            timeout_seconds=1,
            output_limit_bytes=64,
        )


@pytest.mark.parametrize("git_kind", ["absent", "file"])
def test_docker_probe_fails_closed_without_real_git_directory(
    tmp_path,
    monkeypatch,
    git_kind,
) -> None:
    if git_kind == "file":
        (tmp_path / ".git").write_text(
            "gitdir: C:/host/repository",
            encoding="utf-8",
        )
    monkeypatch.setattr(
        DockerSandbox,
        "cli_path",
        staticmethod(lambda: "C:\\tools\\docker.exe"),
    )

    def unexpected_subprocess(*_args, **_kwargs):
        raise AssertionError("invalid Git metadata must fail before Docker")

    monkeypatch.setattr(subprocess, "run", unexpected_subprocess)
    monkeypatch.setattr(subprocess, "Popen", unexpected_subprocess)

    with pytest.raises(
        RuntimeError,
        match="real non-symlink .git directory",
    ):
        DockerSandbox().run_probe(
            tmp_path,
            "print('must-not-run')",
            timeout_seconds=1,
            output_limit_bytes=64,
        )


def test_docker_probe_rejects_symlink_git_directory(
    tmp_path,
    monkeypatch,
) -> None:
    target = tmp_path / "external-git"
    target.mkdir()
    try:
        (tmp_path / ".git").symlink_to(
            target,
            target_is_directory=True,
        )
    except OSError:
        pytest.skip("directory symlinks are unavailable")
    monkeypatch.setattr(
        DockerSandbox,
        "cli_path",
        staticmethod(lambda: "C:\\tools\\docker.exe"),
    )

    with pytest.raises(
        RuntimeError,
        match="real non-symlink .git directory",
    ):
        DockerSandbox().run_probe(
            tmp_path,
            "print('must-not-run')",
            timeout_seconds=1,
            output_limit_bytes=64,
        )


def test_docker_probe_uses_hardened_container_stdin_and_bounded_output(
    tmp_path, monkeypatch
) -> None:
    docker = "C:\\tools\\docker.exe"
    source = "print('PROBE_SOURCE_SENTINEL')"
    (tmp_path / ".git").mkdir()
    calls: list[tuple[list[str], dict[str, object]]] = []
    process = _FakeProbeProcess(stdout=b"x" * 40, stderr=b"y" * 20)
    monkeypatch.setattr(DockerSandbox, "cli_path", staticmethod(lambda: docker))

    def start(command, **kwargs):
        calls.append((list(command), kwargs))
        return process

    monkeypatch.setattr(subprocess, "Popen", start)
    control_calls: list[list[str]] = []

    def control(command, **_kwargs):
        control_calls.append(list(command))
        return _probe_control_result(list(command))

    monkeypatch.setattr(subprocess, "run", control)

    result = DockerSandbox("probe-image").run_probe(
        tmp_path,
        source,
        timeout_seconds=2,
        output_limit_bytes=32,
    )

    assert len(calls) == 1
    start_command, kwargs = calls[0]
    assert start_command[:4] == [
        docker,
        "start",
        "--attach",
        "--interactive",
    ]
    create_command = next(
        call for call in control_calls if call[1] == "create"
    )
    assert create_command[create_command.index("--network") + 1] == "none"
    assert "--read-only" in create_command
    assert create_command[create_command.index("--cap-drop") + 1] == "ALL"
    assert (
        create_command[create_command.index("--security-opt") + 1]
        == "no-new-privileges"
    )
    labels = [
        create_command[index + 1]
        for index, value in enumerate(create_command)
        if value == "--label"
    ]
    assert "io.patchloop.managed=probe" in labels
    assert "io.patchloop.role=agent-probe" in labels
    assert any(
        label.startswith("io.patchloop.workspace=")
        for label in labels
    )
    tmpfs = create_command[create_command.index("--tmpfs") + 1]
    assert tmpfs.startswith("/tmp:rw,")
    assert "noexec" in tmpfs
    assert "nosuid" in tmpfs
    tmpfs_mounts = [
        create_command[index + 1]
        for index, value in enumerate(create_command)
        if value == "--tmpfs"
    ]
    assert any(
        mount.startswith("/workspace/.git:")
        for mount in tmpfs_mounts
    )
    assert (
        create_command[create_command.index("--user") + 1]
        == "10001:10001"
    )
    mount = create_command[create_command.index("--mount") + 1]
    assert "target=/workspace" in mount
    assert mount.endswith(",readonly")
    assert create_command[-5:] == [
        _IMAGE_ID,
        "python",
        "-I",
        "/opt/patchloop/probe_runner.py",
        "2",
    ]
    assert PROBE_IMAGE not in create_command
    assert "probe-image" not in create_command
    environment = [
        create_command[index + 1]
        for index, value in enumerate(create_command)
        if value == "--env"
    ]
    for key in (
        "ALL_PROXY",
        "FTP_PROXY",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "all_proxy",
        "ftp_proxy",
        "http_proxy",
        "https_proxy",
        "no_proxy",
    ):
        assert f"{key}=" in environment
    assert source not in create_command
    assert all(
        "PROBE_SOURCE_SENTINEL" not in item
        for item in create_command + start_command
    )
    assert "env" not in kwargs
    assert bytes(process.stdin.data).endswith(source.encode("utf-8"))
    assert b"_patchloop_sys.addaudithook(guard)" in process.stdin.data
    assert b"_patchloop_sys.dont_write_bytecode = True" in process.stdin.data
    assert result.command == ["python", "-I", "<ephemeral-probe>"]
    assert result.truncated is True
    assert result.original_output_bytes == 60
    assert len(result.stdout.encode()) + len(result.stderr.encode()) <= 32
    assert result.execution_policy == {
        "schema_version": "probe-execution-policy-v2",
        "image": PROBE_IMAGE,
        "image_identity": _IMAGE_ID,
        "network": "none",
        "root_filesystem": "read_only",
        "workspace_mount": "read_only",
        "git_metadata": "masked",
        "cap_drop": ["ALL"],
        "no_new_privileges": True,
        "user": "10001:10001",
        "proxy_environment": "cleared",
        "process_boundary": {
            "mechanism": "seccomp-bpf-v1",
            "trusted_parent": True,
            "untrusted_child": True,
            "fork_clone_exec": "errno",
            "parent_signal_and_trace": "errno",
        },
        "limits": {
            "cpus": 1,
            "memory": "512m",
            "pids": 2,
            "tmpfs": "/tmp:64m",
            "requested_timeout_seconds": 2,
            "container_runner": "/opt/patchloop/probe_runner.py",
            "container_timeout_exit_code": 124,
            "launcher_timeout_seconds": 12,
            "output_limit_bytes": 32,
        },
    }
    assert str(tmp_path) not in json.dumps(result.execution_policy)
    assert any(
        call[1:3] == ["image", "inspect"]
        and call[3] == PROBE_IMAGE
        for call in control_calls
    )
    assert any(
        call[1:3] == ["container", "inspect"]
        and call[-2:] == ["--format", "{{.Image}}"]
        for call in control_calls
    )


def test_docker_probe_rejects_manifest_tag_mismatch_before_create(
    tmp_path,
    monkeypatch,
) -> None:
    docker = "C:\\tools\\docker.exe"
    (tmp_path / ".git").mkdir()
    calls: list[list[str]] = []
    monkeypatch.setattr(
        DockerSandbox,
        "cli_path",
        staticmethod(lambda: docker),
    )

    def control(command, **_kwargs):
        calls.append(list(command))
        return _probe_control_result(list(command))

    monkeypatch.setattr(subprocess, "run", control)
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail(
            "mismatched manifest image must not start"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="tag does not match the manifest-bound identity",
    ):
        DockerSandbox().run_probe(
            tmp_path,
            "print('must-not-run')",
            timeout_seconds=2,
            output_limit_bytes=1024,
            image_identity=_OTHER_IMAGE_ID,
        )

    assert not any(command[1] == "create" for command in calls)


def test_docker_probe_rejects_created_container_image_before_start(
    tmp_path,
    monkeypatch,
) -> None:
    docker = "C:\\tools\\docker.exe"
    (tmp_path / ".git").mkdir()
    calls: list[list[str]] = []
    monkeypatch.setattr(
        DockerSandbox,
        "cli_path",
        staticmethod(lambda: docker),
    )

    def control(command, **_kwargs):
        calls.append(list(command))
        return _probe_control_result(
            list(command),
            actual_image_identity=_OTHER_IMAGE_ID,
        )

    monkeypatch.setattr(subprocess, "run", control)
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail(
            "unverified container image must not start"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="container image does not match",
    ):
        DockerSandbox().run_probe(
            tmp_path,
            "print('must-not-run')",
            timeout_seconds=2,
            output_limit_bytes=1024,
            image_identity=_IMAGE_ID,
        )

    assert any(command[1] == "create" for command in calls)
    assert any(
        command[1:3] == ["container", "inspect"]
        for command in calls
    )
    assert any(
        command[1:3] == ["rm", "--force"]
        for command in calls
    )


def test_docker_probe_reaps_same_workspace_stale_container(
    tmp_path,
    monkeypatch,
) -> None:
    docker = "C:\\tools\\docker.exe"
    stale_id = b"0123456789ab\n"
    (tmp_path / ".git").mkdir()
    process = _FakeProbeProcess()
    control_calls: list[list[str]] = []
    monkeypatch.setattr(DockerSandbox, "cli_path", staticmethod(lambda: docker))
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *_args, **_kwargs: process,
    )

    def control(command, **_kwargs):
        control_calls.append(list(command))
        return _probe_control_result(
            list(command),
            stale_container_ids=stale_id,
        )

    monkeypatch.setattr(subprocess, "run", control)

    result = DockerSandbox("task-evaluator-image").run_probe(
        tmp_path,
        "print('ok')",
        timeout_seconds=2,
        output_limit_bytes=1024,
    )

    assert result.passed is True
    assert [
        command
        for command in control_calls
        if command[1:3] == ["rm", "--force"]
        and command[-1] == stale_id.decode().strip()
    ] == [[docker, "rm", "--force", stale_id.decode().strip()]]


def test_docker_probe_attempts_cleanup_when_launcher_raises(
    tmp_path,
    monkeypatch,
) -> None:
    docker = "C:\\tools\\docker.exe"
    (tmp_path / ".git").mkdir()
    control_calls: list[list[str]] = []
    monkeypatch.setattr(DockerSandbox, "cli_path", staticmethod(lambda: docker))

    def fail_start(*_args, **_kwargs):
        raise OSError("synthetic launcher failure")

    def control(command, **_kwargs):
        control_calls.append(list(command))
        return _probe_control_result(list(command))

    monkeypatch.setattr(subprocess, "Popen", fail_start)
    monkeypatch.setattr(subprocess, "run", control)

    with pytest.raises(OSError, match="synthetic launcher failure"):
        DockerSandbox().run_probe(
            tmp_path,
            "print('never-started')",
            timeout_seconds=2,
            output_limit_bytes=1024,
        )

    assert any(
        command[1:3] == ["rm", "--force"]
        for command in control_calls
    )


def test_docker_probe_fails_before_run_without_dedicated_image(
    tmp_path,
    monkeypatch,
) -> None:
    docker = "C:\\tools\\docker.exe"
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(DockerSandbox, "cli_path", staticmethod(lambda: docker))

    def control(command, **_kwargs):
        if command[1:3] == ["ps", "--all"]:
            return subprocess.CompletedProcess(command, 0, b"", b"")
        if command[1:3] == ["image", "inspect"]:
            assert command[3] == PROBE_IMAGE
            return subprocess.CompletedProcess(
                command,
                1,
                b"",
                b"image absent",
            )
        raise AssertionError(f"unexpected command: {command}")

    def unexpected_start(*_args, **_kwargs):
        raise AssertionError("probe must not start without its clean image")

    monkeypatch.setattr(subprocess, "run", control)
    monkeypatch.setattr(subprocess, "Popen", unexpected_start)

    with pytest.raises(
        RuntimeError,
        match="dedicated PatchLoop probe image is unavailable or invalid",
    ):
        DockerSandbox("task-evaluator-image").run_probe(
            tmp_path,
            "print('must-not-run')",
            timeout_seconds=2,
            output_limit_bytes=1024,
        )


def test_docker_probe_timeout_force_removes_named_container(
    tmp_path, monkeypatch
) -> None:
    docker = "C:\\tools\\docker.exe"
    source = "while True: pass  # TIMEOUT_SOURCE_SENTINEL"
    run_calls: list[list[str]] = []
    cleanup_calls: list[list[str]] = []
    process = _FakeProbeProcess(
        stdout=b"partial stdout",
        stderr=b"partial stderr",
        times_out=True,
    )
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(DockerSandbox, "cli_path", staticmethod(lambda: docker))

    def start(command, **_kwargs):
        run_calls.append(list(command))
        return process

    def cleanup(command, **_kwargs):
        cleanup_calls.append(list(command))
        return _probe_control_result(list(command))

    monkeypatch.setattr(subprocess, "Popen", start)
    monkeypatch.setattr(subprocess, "run", cleanup)

    result = DockerSandbox("probe-image").run_probe(
        tmp_path,
        source,
        timeout_seconds=2,
        output_limit_bytes=1024,
    )

    assert result.timed_out is True
    assert result.exit_code is None
    assert process.killed is True
    assert len(run_calls) == 1
    assert len(cleanup_calls) >= 6
    start_command = run_calls[0]
    cleanup_command = next(
        command
        for command in cleanup_calls
        if command[1:3] == ["rm", "--force"]
    )
    container_name = start_command[-1]
    assert container_name.startswith("patchloop-probe-")
    assert cleanup_command == [docker, "rm", "--force", container_name]
    assert all("TIMEOUT_SOURCE_SENTINEL" not in item for item in cleanup_command)


def test_docker_probe_maps_container_runner_timeout_exit(
    tmp_path,
    monkeypatch,
) -> None:
    docker = "C:\\tools\\docker.exe"
    (tmp_path / ".git").mkdir()
    process = _FakeProbeProcess(
        stdout=b"partial output",
        stderr=b"[patchloop] probe exceeded timeout\n",
        exit_code=124,
    )
    monkeypatch.setattr(DockerSandbox, "cli_path", staticmethod(lambda: docker))
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *_args, **_kwargs: process,
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_kwargs: _probe_control_result(
            list(command)
        ),
    )

    result = DockerSandbox("task-evaluator-image").run_probe(
        tmp_path,
        "import time; time.sleep(100)",
        timeout_seconds=2,
        output_limit_bytes=1024,
    )

    assert result.timed_out is True
    assert result.exit_code is None
    assert result.stdout == "partial output"
    assert "probe exceeded timeout" in result.stderr


def test_docker_probe_reports_unconfirmed_timeout_cleanup(
    tmp_path, monkeypatch
) -> None:
    docker = "C:\\tools\\docker.exe"
    process = _FakeProbeProcess(times_out=True)
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(DockerSandbox, "cli_path", staticmethod(lambda: docker))
    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: process)

    def failed_cleanup(command, **_kwargs):
        if command[1:3] == ["rm", "--force"]:
            return _probe_control_result(
                list(command),
                cleanup_returncode=1,
            )
        if (
            command[1:3] == ["ps", "--all"]
            and not any(
                item == "label=io.patchloop.managed=probe"
                for item in command
            )
        ):
            return subprocess.CompletedProcess(
                command,
                1,
                b"",
                b"daemon unavailable",
            )
        return _probe_control_result(list(command))

    monkeypatch.setattr(subprocess, "run", failed_cleanup)

    with pytest.raises(
        RuntimeError,
        match="probe container cleanup could not be confirmed",
    ):
        DockerSandbox("probe-image").run_probe(
            tmp_path,
            "import time; time.sleep(100)",
            timeout_seconds=2,
            output_limit_bytes=1024,
        )


@pytest.mark.docker
@pytest.mark.skipif(not DockerSandbox.available(), reason="Docker daemon unavailable")
def test_docker_sandbox_has_no_network(tmp_path) -> None:
    sandbox = DockerSandbox()
    if sandbox.image_identity() is None:
        pytest.skip(f"{sandbox.image} is not built")
    result = sandbox.run_check(
        tmp_path,
        RegisteredCheck(
            id="no-network",
            command=[
                "python",
                "-c",
                "import socket; socket.create_connection(('1.1.1.1', 53), timeout=.5)",
            ],
        ),
    )
    assert result.exit_code != 0
    assert DockerSandbox.cli_path() is not None


@pytest.mark.docker
@pytest.mark.skipif(not DockerSandbox.available(), reason="Docker daemon unavailable")
def test_docker_sandbox_is_non_root_read_only_and_does_not_forward_host_secret(
    tmp_path, monkeypatch
) -> None:
    sandbox = DockerSandbox()
    if sandbox.image_identity() is None:
        pytest.skip(f"{sandbox.image} is not built")
    monkeypatch.setenv("PATCHLOOP_HOST_SECRET", "must-not-enter-container")
    result = sandbox.run_check(
        tmp_path,
        RegisteredCheck(
            id="isolation-policy",
            command=[
                "python",
                "-c",
                (
                    "import os, pathlib; "
                    "assert os.getuid() == 10001; "
                    "assert 'PATCHLOOP_HOST_SECRET' not in os.environ; "
                    "pathlib.Path('/workspace/probe').write_text('forbidden')"
                ),
            ],
        ),
    )
    assert result.exit_code != 0
    assert "Read-only file system" in result.stderr


@pytest.mark.docker
@pytest.mark.skipif(not DockerSandbox.available(), reason="Docker daemon unavailable")
def test_docker_probe_is_non_root_networkless_and_workspace_read_only(
    tmp_path, monkeypatch
) -> None:
    sandbox = DockerSandbox()
    if sandbox.image_identity() is None:
        pytest.skip(f"{sandbox.image} is not built")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "solution-marker").write_text(
        "must-not-be-visible",
        encoding="utf-8",
    )
    monkeypatch.setenv("PATCHLOOP_HOST_SECRET", "must-not-enter-container")
    result = sandbox.run_probe(
        tmp_path,
        (
            "import os\n"
            "import pathlib\n"
            "import socket\n"
            "assert os.getuid() == 10001\n"
            "assert 'PATCHLOOP_HOST_SECRET' not in os.environ\n"
            "for key in (\n"
            "    'ALL_PROXY', 'FTP_PROXY', 'HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY',\n"
            "    'all_proxy', 'ftp_proxy', 'http_proxy', 'https_proxy', 'no_proxy',\n"
            "):\n"
            "    assert os.environ.get(key, '') == ''\n"
            "assert not pathlib.Path('/workspace/.git/solution-marker').exists()\n"
            "assert not pathlib.Path('/testbed').exists()\n"
            "assert not pathlib.Path('/babel').exists()\n"
            "try:\n"
            "    pathlib.Path('/workspace/probe').write_text('forbidden')\n"
            "except OSError:\n"
            "    pass\n"
            "else:\n"
            "    raise AssertionError('workspace write succeeded')\n"
            "try:\n"
            "    socket.create_connection(('1.1.1.1', 53), timeout=.5)\n"
            "except OSError:\n"
            "    pass\n"
            "else:\n"
            "    raise AssertionError('network connection succeeded')\n"
        ),
        timeout_seconds=5,
        output_limit_bytes=1024,
    )
    assert result.passed is True
    assert result.execution_policy is not None
    assert result.execution_policy["image"] == PROBE_IMAGE
    assert str(result.execution_policy["image_identity"]).startswith(
        "sha256:"
    )
    assert not (tmp_path / "probe").exists()


@pytest.mark.docker
@pytest.mark.skipif(
    not DockerSandbox.available(),
    reason="Docker daemon unavailable",
)
def test_docker_probe_runtime_and_kernel_process_boundaries(
    tmp_path,
) -> None:
    sandbox = DockerSandbox()
    image_identity = sandbox.probe_image_identity()
    if image_identity is None:
        pytest.skip(f"{PROBE_IMAGE} is not built")
    (tmp_path / ".git").mkdir()

    result = sandbox.run_probe(
        tmp_path,
        (
            "import sys\n"
            "sys.modules['os'].system("
            "'python -c \"print(123)\"')\n"
        ),
        timeout_seconds=5,
        output_limit_bytes=4096,
        image_identity=image_identity,
    )

    assert result.passed is False
    assert result.exit_code != 0
    assert "PatchLoop probe policy denied audit event: os.system" in (
        result.stderr
    )

    dynamic_result = sandbox.run_probe(
        tmp_path,
        (
            "import builtins\n"
            "capability = ''.join(('ex', 'ec'))\n"
            "getattr(builtins, capability)("
            "\"import sys\\nsys.modules['os'].system('true')\""
            ")\n"
        ),
        timeout_seconds=5,
        output_limit_bytes=4096,
        image_identity=image_identity,
    )

    assert dynamic_result.passed is False
    assert dynamic_result.exit_code != 0
    assert "PatchLoop probe policy denied audit event: os.system" in (
        dynamic_result.stderr
    )

    kernel_result = sandbox.run_probe(
        tmp_path,
        (
            "import _xxsubinterpreters as interpreters\n"
            "child = interpreters.create()\n"
            "interpreters.run_string(child, '''\n"
            "import errno\n"
            "import os\n"
            "try:\n"
            "    os.posix_spawn('/bin/true', ['true'], {})\n"
            "except OSError as exc:\n"
            "    assert exc.errno == errno.EPERM\n"
            "else:\n"
            "    raise AssertionError('process spawn unexpectedly succeeded')\n"
            "try:\n"
            "    os.kill(os.getppid(), 0)\n"
            "except OSError as exc:\n"
            "    assert exc.errno == errno.EPERM\n"
            "else:\n"
            "    raise AssertionError('parent signal unexpectedly succeeded')\n"
            "print('kernel-process-boundary-ok', flush=True)\n"
            "''')\n"
        ),
        timeout_seconds=5,
        output_limit_bytes=4096,
        image_identity=image_identity,
    )

    assert kernel_result.passed is True
    assert kernel_result.exit_code == 0
    assert "kernel-process-boundary-ok" in kernel_result.stdout
