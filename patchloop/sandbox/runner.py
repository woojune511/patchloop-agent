"""Registered-check execution with bounded output and optional Docker isolation."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from patchloop.contracts import DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V1, RegisteredCheck
from patchloop.util import ensure_within

_DOCKER_IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}")
_DOCKER_REPO_DIGEST = re.compile(r"[^\x00-\x20\x7f]+@sha256:[0-9a-f]{64}")
_IMAGE_INSPECT_FORMAT = '{"Id":{{json .Id}},"RepoDigests":{{json .RepoDigests}}}'


@dataclass(frozen=True)
class SandboxResult:
    command: list[str]
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool
    truncated: bool
    original_output_bytes: int
    execution_policy: dict[str, object] | None = None

    @property
    def passed(self) -> bool:
        return not self.timed_out and self.exit_code == 0


class Sandbox(Protocol):
    official: bool
    backend: str

    def run_check(self, workspace: Path, check: RegisteredCheck) -> SandboxResult: ...


def _bounded_text(stdout: bytes, stderr: bytes, limit: int) -> tuple[str, str, bool, int]:
    original = len(stdout) + len(stderr)
    remaining = limit
    stdout_slice = stdout[:remaining]
    remaining -= len(stdout_slice)
    stderr_slice = stderr[: max(0, remaining)]
    return (
        stdout_slice.decode("utf-8", errors="replace"),
        stderr_slice.decode("utf-8", errors="replace"),
        original > limit,
        original,
    )


def registered_check_execution_policy(
    *, image: str, working_directory: str, timeout_seconds: int, output_limit_bytes: int
) -> dict[str, object]:
    if not image or image != image.strip() or any(ord(char) < 32 for char in image):
        raise ValueError("registered-check image reference is invalid")
    if not working_directory.startswith("/workspace") or ".." in Path(working_directory).parts:
        raise ValueError("registered-check working directory is invalid")
    if timeout_seconds < 1 or output_limit_bytes < 1:
        raise ValueError("registered-check limits must be positive")
    policy = dict(DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V1)
    policy.update(
        {
            "working_directory": working_directory,
            "image": image,
            "requested_timeout_seconds": timeout_seconds,
            "launcher_timeout_seconds": timeout_seconds + 5,
            "output_limit_bytes": output_limit_bytes,
        }
    )
    return policy


class LocalSandbox:
    """Deterministic non-official backend used only by tests and mock smoke."""

    official = False
    backend = "local"

    def run_check(self, workspace: Path, check: RegisteredCheck) -> SandboxResult:
        workdir = workspace if check.working_directory == "." else ensure_within(
            workspace, check.working_directory
        )
        declared_command = list(check.command)
        command = list(declared_command)
        if command[0] in {"python", "python3"}:
            command[0] = sys.executable
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": str(workspace),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_ADDOPTS": "-p no:cacheprovider",
            **check.environment,
        }
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                cwd=workdir,
                env=environment,
                capture_output=True,
                timeout=check.timeout_seconds,
                check=False,
            )
            exit_code = completed.returncode
            timed_out = False
            stdout, stderr = completed.stdout, completed.stderr
        except subprocess.TimeoutExpired as exc:
            exit_code = None
            timed_out = True
            stdout, stderr = exc.stdout or b"", exc.stderr or b""
        stdout_text, stderr_text, truncated, original = _bounded_text(
            stdout, stderr, check.output_limit_bytes
        )
        return SandboxResult(
            command=declared_command,
            exit_code=exit_code,
            stdout=stdout_text,
            stderr=stderr_text,
            duration_ms=int((time.monotonic() - started) * 1_000),
            timed_out=timed_out,
            truncated=truncated,
            original_output_bytes=original,
        )


class DockerSandbox:
    """Digest-pinned, no-network registered checks; never pulls or builds images."""

    official = False
    backend = "docker"

    def __init__(self, image: str) -> None:
        self.image = image

    @staticmethod
    def cli_path() -> str | None:
        override = os.environ.get("PATCHLOOP_DOCKER_CLI")
        if override:
            return str(Path(override)) if Path(override).is_file() else None
        discovered = shutil.which("docker")
        if discovered:
            return discovered
        candidates: list[Path] = []
        local_app_data = os.environ.get("LOCALAPPDATA")
        program_files = os.environ.get("PROGRAMFILES")
        if local_app_data:
            candidates.append(
                Path(local_app_data)
                / "Programs"
                / "DockerDesktop"
                / "resources"
                / "bin"
                / "docker.exe"
            )
        if program_files:
            candidates.append(
                Path(program_files) / "Docker" / "Docker" / "resources" / "bin" / "docker.exe"
            )
        return next((str(path) for path in candidates if path.is_file()), None)

    @staticmethod
    def available() -> bool:
        docker = DockerSandbox.cli_path()
        if docker is None:
            return False
        try:
            result = subprocess.run(
                [docker, "version", "--format", "{{.Server.Version}}"],
                capture_output=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0 and bool(result.stdout.strip())

    def image_identity(self) -> str | None:
        docker = self.cli_path()
        if docker is None or "@" not in self.image:
            return None
        requested_digest = self.image.rsplit("@", 1)[1]
        if _DOCKER_IMAGE_ID.fullmatch(requested_digest) is None:
            return None
        try:
            result = subprocess.run(
                [docker, "image", "inspect", self.image, "--format", _IMAGE_INSPECT_FORMAT],
                capture_output=True,
                timeout=10,
                check=False,
            )
            if result.returncode != 0 or result.stderr or len(result.stdout) > 65_536:
                return None
            payload = json.loads(result.stdout.decode("utf-8").rstrip("\r\n"))
        except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError, json.JSONDecodeError):
            return None
        repo_digests = payload.get("RepoDigests") if isinstance(payload, dict) else None
        if not isinstance(repo_digests, list) or not all(
            isinstance(item, str) and _DOCKER_REPO_DIGEST.fullmatch(item)
            for item in repo_digests
        ):
            return None
        requested = self.image
        aliases = {requested}
        if requested.startswith("docker.io/"):
            aliases.add(requested.removeprefix("docker.io/"))
        return requested_digest if len(aliases.intersection(repo_digests)) == 1 else None

    def run_check(self, workspace: Path, check: RegisteredCheck) -> SandboxResult:
        docker = self.cli_path()
        if docker is None:
            raise RuntimeError("Docker CLI is not available")
        working_directory = "/workspace"
        if check.working_directory != ".":
            working_directory += f"/{check.working_directory}"
        policy = registered_check_execution_policy(
            image=self.image,
            working_directory=working_directory,
            timeout_seconds=check.timeout_seconds,
            output_limit_bytes=check.output_limit_bytes,
        )
        command = [
            docker,
            "run",
            "--rm",
            "--pull",
            "never",
            "--network",
            "none",
            "--cpus",
            "2",
            "--memory",
            "2g",
            "--pids-limit",
            "128",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=256m",
        ]
        for key, value in sorted({"PYTHONDONTWRITEBYTECODE": "1", **check.environment}.items()):
            command.extend(["--env", f"{key}={value}"])
        command.extend(
            [
                "--mount",
                f"type=bind,source={workspace.resolve()},target=/workspace,readonly",
                "--workdir",
                working_directory,
                self.image,
                *check.command,
            ]
        )
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                timeout=check.timeout_seconds + 5,
                check=False,
            )
            exit_code = completed.returncode
            timed_out = False
            stdout, stderr = completed.stdout, completed.stderr
        except subprocess.TimeoutExpired as exc:
            exit_code = None
            timed_out = True
            stdout, stderr = exc.stdout or b"", exc.stderr or b""
        stdout_text, stderr_text, truncated, original = _bounded_text(
            stdout, stderr, check.output_limit_bytes
        )
        return SandboxResult(
            command=list(check.command),
            exit_code=exit_code,
            stdout=stdout_text,
            stderr=stderr_text,
            duration_ms=int((time.monotonic() - started) * 1_000),
            timed_out=timed_out,
            truncated=truncated,
            original_output_bytes=original,
            execution_policy=policy,
        )
