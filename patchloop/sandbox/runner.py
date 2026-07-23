"""Registered command execution with bounded output and optional Docker isolation."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from patchloop.contracts import RegisteredCheck
from patchloop.util import ensure_within


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

    @property
    def passed(self) -> bool:
        return not self.timed_out and self.exit_code == 0


class Sandbox(Protocol):
    official: bool

    def run_check(self, workspace: Path, check: RegisteredCheck) -> SandboxResult: ...


def _bounded_text(stdout: bytes, stderr: bytes, limit: int) -> tuple[str, str, bool, int]:
    original = len(stdout) + len(stderr)
    truncated = original > limit
    remaining = limit
    stdout_slice = stdout[:remaining]
    remaining -= len(stdout_slice)
    stderr_slice = stderr[: max(0, remaining)]
    return (
        stdout_slice.decode("utf-8", errors="replace"),
        stderr_slice.decode("utf-8", errors="replace"),
        truncated,
        original,
    )


class LocalSandbox:
    """Non-official backend for deterministic unit and smoke tests."""

    official = False

    def run_check(self, workspace: Path, check: RegisteredCheck) -> SandboxResult:
        workdir = (
            workspace
            if check.working_directory == "."
            else ensure_within(workspace, check.working_directory)
        )
        declared_command = list(check.command)
        command = list(declared_command)
        if command[0] in {"python", "python3"}:
            command[0] = sys.executable
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(workspace)}
        env.update(check.environment)
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                cwd=workdir,
                env=env,
                capture_output=True,
                timeout=check.timeout_seconds,
                check=False,
            )
            timed_out = False
            exit_code = completed.returncode
            stdout, stderr = completed.stdout, completed.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = None
            stdout = exc.stdout or b""
            stderr = exc.stderr or b""
        duration = int((time.monotonic() - started) * 1000)
        stdout_text, stderr_text, truncated, original = _bounded_text(
            stdout, stderr, check.output_limit_bytes
        )
        return SandboxResult(
            command=declared_command,
            exit_code=exit_code,
            stdout=stdout_text,
            stderr=stderr_text,
            duration_ms=duration,
            timed_out=timed_out,
            truncated=truncated,
            original_output_bytes=original,
        )


class DockerSandbox:
    official = True

    def __init__(self, image: str = "patchloop-sandbox:py312") -> None:
        self.image = image

    @staticmethod
    def cli_path() -> str | None:
        """Find Docker without requiring a machine-wide PATH entry.

        Docker Desktop can be installed per-user on Windows.  In that case its
        CLI is not necessarily added to PATH, even though the desktop engine is
        installed and running.
        """
        override = os.environ.get("PATCHLOOP_DOCKER_CLI")
        if override:
            candidate = Path(override).expanduser()
            try:
                return str(candidate) if candidate.is_file() else None
            except OSError:
                return None

        discovered = shutil.which("docker")
        if discovered:
            return discovered

        candidates: list[Path] = []
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidates.extend(
                [
                    Path(local_app_data)
                    / "Programs"
                    / "DockerDesktop"
                    / "resources"
                    / "bin"
                    / "docker.exe",
                    Path(local_app_data)
                    / "Docker"
                    / "resources"
                    / "bin"
                    / "docker.exe",
                ]
            )
        program_files = os.environ.get("PROGRAMFILES")
        if program_files:
            candidates.append(
                Path(program_files)
                / "Docker"
                / "Docker"
                / "resources"
                / "bin"
                / "docker.exe"
            )
        for candidate in candidates:
            try:
                if candidate.is_file():
                    return str(candidate)
            except OSError:
                continue
        return None

    @staticmethod
    def available() -> bool:
        docker = DockerSandbox.cli_path()
        if not docker:
            return False
        result = subprocess.run(
            [docker, "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0 and bool(result.stdout.strip())

    def image_identity(self) -> str | None:
        docker = self.cli_path()
        if not docker:
            return None
        result = subprocess.run(
            [docker, "image", "inspect", self.image, "--format", "{{.Id}}"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else None

    def run_check(self, workspace: Path, check: RegisteredCheck) -> SandboxResult:
        docker = self.cli_path()
        if not docker:
            raise RuntimeError("Docker CLI is not available")
        workdir = "/workspace"
        if check.working_directory != ".":
            workdir = f"/workspace/{check.working_directory}"
        command = [
            docker,
            "run",
            "--rm",
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
        environment = {"PYTHONDONTWRITEBYTECODE": "1", **check.environment}
        for key, value in sorted(environment.items()):
            command.extend(["--env", f"{key}={value}"])
        command.extend(
            [
                "--mount",
                f"type=bind,source={workspace.resolve()},target=/workspace,readonly",
                "--workdir",
                workdir,
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
            timed_out = False
            exit_code = completed.returncode
            stdout, stderr = completed.stdout, completed.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = None
            stdout = exc.stdout or b""
            stderr = exc.stderr or b""
        duration = int((time.monotonic() - started) * 1000)
        stdout_text, stderr_text, truncated, original = _bounded_text(
            stdout, stderr, check.output_limit_bytes
        )
        return SandboxResult(
            command=list(check.command),
            exit_code=exit_code,
            stdout=stdout_text,
            stderr=stderr_text,
            duration_ms=duration,
            timed_out=timed_out,
            truncated=truncated,
            original_output_bytes=original,
        )


class TimeoutOnceSandbox:
    """Deterministic reliability-test wrapper; never used in core normal runs."""

    def __init__(self, delegate: Sandbox) -> None:
        self.delegate = delegate
        self.official = delegate.official
        self.injected = False

    def run_check(self, workspace: Path, check: RegisteredCheck) -> SandboxResult:
        if not self.injected:
            self.injected = True
            return SandboxResult(
                command=list(check.command),
                exit_code=None,
                stdout="",
                stderr="injected deterministic timeout",
                duration_ms=check.timeout_seconds * 1000,
                timed_out=True,
                truncated=False,
                original_output_bytes=30,
            )
        return self.delegate.run_check(workspace, check)
