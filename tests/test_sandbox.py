from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from patchloop.contracts import RegisteredCheck
from patchloop.sandbox import DockerSandbox, LocalSandbox


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
