"""Registered-check execution with bounded output and optional Docker isolation."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from patchloop.contracts import DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V2, RegisteredCheck
from patchloop.deadline import ExecutionDeadline
from patchloop.sandbox.capture import SandboxCleanupError, bounded_text, capture_process
from patchloop.sandbox.execution_feedback import public_feedback, trace_launch
from patchloop.util import canonical_json, ensure_within, sha256_bytes

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
    deadline_exhausted: bool = False
    cleanup_failed: bool = False
    public_execution: dict[str, object] | None = None

    @property
    def passed(self) -> bool:
        return (
            not self.timed_out
            and not self.deadline_exhausted
            and not self.cleanup_failed
            and self.exit_code == 0
        )


class Sandbox(Protocol):
    official: bool
    backend: str

    def run_check(
        self, workspace: Path, check: RegisteredCheck, *,
        deadline: ExecutionDeadline | None = None,
        execution_identity: dict[str, str] | None = None,
        execution_targets: dict | None = None,
    ) -> SandboxResult: ...


def _bounded_text(stdout: bytes, stderr: bytes, limit: int) -> tuple[str, str, bool, int]:
    return bounded_text(stdout, stderr, limit)


def registered_check_execution_policy(
    *, image: str, working_directory: str, timeout_seconds: int, output_limit_bytes: int,
    effective_timeout_seconds: float | None = None,
    row_deadline_limited: bool = False,
    cleanup_status: str = "confirmed",
) -> dict[str, object]:
    if not image or image != image.strip() or any(ord(char) < 32 for char in image):
        raise ValueError("registered-check image reference is invalid")
    if not working_directory.startswith("/workspace") or ".." in Path(working_directory).parts:
        raise ValueError("registered-check working directory is invalid")
    if timeout_seconds < 1 or output_limit_bytes < 1:
        raise ValueError("registered-check limits must be positive")
    effective = (
        float(timeout_seconds) if effective_timeout_seconds is None else effective_timeout_seconds
    )
    if not 0 < effective <= timeout_seconds:
        raise ValueError("effective timeout must be positive and no greater than declared timeout")
    if cleanup_status not in {"confirmed", "failed"}:
        raise ValueError("invalid owned-container cleanup status")
    policy = dict(DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V2)
    policy.update(
        {
            "working_directory": working_directory,
            "image": image,
            "requested_timeout_seconds": timeout_seconds,
            "launcher_timeout_seconds": effective,
            "effective_timeout_seconds": effective,
            "row_deadline_limited": row_deadline_limited,
            "cleanup_status": cleanup_status,
            "output_limit_bytes": output_limit_bytes,
        }
    )
    return policy


class LocalSandbox:
    """Deterministic non-official backend used only by tests and mock smoke."""

    official = False
    backend = "local"
    supports_execution_deadline = True
    supports_public_execution = True

    def run_check(
        self, workspace: Path, check: RegisteredCheck, *,
        deadline: ExecutionDeadline | None = None,
        execution_identity: dict[str, str] | None = None,
        execution_targets: dict | None = None,
    ) -> SandboxResult:
        del execution_identity
        if deadline is not None:
            deadline.check()
        workdir = workspace if check.working_directory == "." else ensure_within(
            workspace, check.working_directory
        )
        declared_command = list(check.command)
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": str(workspace),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_ADDOPTS": "-p no:cacheprovider",
            **check.environment,
        }
        started = time.monotonic()
        with trace_launch(declared_command, execution_targets, workspace) as launch:
            command, _mounts = launch
            if command[0] in {"python", "python3"}:
                command[0] = sys.executable
            # Even the local test backend reserves bounded process/pipe teardown
            # inside the active budget; short remaining windows are shared fairly.
            timeout = (
                deadline.bounded_timeout(
                    check.timeout_seconds,
                    reserve_seconds=min(5.0, deadline.remaining_seconds() / 2),
                ) if deadline is not None else float(check.timeout_seconds)
            )
            captured = capture_process(
                command, cwd=workdir, env=environment, timeout=timeout,
                output_limit_bytes=check.output_limit_bytes,
                execution_targets=execution_targets, deadline=deadline,
            )
        feedback = None
        if execution_targets is not None:
            feedback = public_feedback(
                execution_targets, None if captured.timed_out else captured.report,
            )
        return SandboxResult(
            command=declared_command,
            exit_code=captured.exit_code,
            stdout=captured.stdout,
            stderr=captured.stderr,
            duration_ms=int((time.monotonic() - started) * 1_000),
            timed_out=captured.timed_out,
            truncated=captured.truncated,
            original_output_bytes=captured.original_output_bytes,
            public_execution=feedback,
            deadline_exhausted=(
                deadline is not None
                and (
                    deadline.remaining_seconds() <= 0
                    or (captured.timed_out and timeout < check.timeout_seconds)
                )
            ),
        )


class DockerSandbox:
    """Digest-pinned, no-network registered checks; never pulls or builds images."""

    official = False
    backend = "docker"
    supports_execution_deadline = True
    supports_public_execution = True

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
    def available(*, deadline: ExecutionDeadline | None = None) -> bool:
        docker = DockerSandbox.cli_path()
        if docker is None:
            return False
        try:
            result = subprocess.run(
                [docker, "version", "--format", "{{.Server.Version}}"],
                capture_output=True,
                timeout=deadline.bounded_timeout(10) if deadline else 10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            if deadline is not None:
                deadline.check()
            return False
        if deadline is not None:
            deadline.check()
        return result.returncode == 0 and bool(result.stdout.strip())

    def image_identity(self, *, deadline: ExecutionDeadline | None = None) -> str | None:
        docker = self.cli_path()
        if docker is None or "@" not in self.image:
            return None
        requested_digest = self.image.rsplit("@", 1)[1]
        if _DOCKER_IMAGE_ID.fullmatch(requested_digest) is None:
            return None
        # Digest references are immutable; their optional tag is not part of
        # Docker's stored RepoDigest name. Preserve a registry port, if present.
        repository = self.image.rsplit("@", 1)[0]
        if ":" in repository.rsplit("/", 1)[-1]:
            repository = repository.rsplit(":", 1)[0]
        requested = f"{repository}@{requested_digest}"
        try:
            result = subprocess.run(
                [docker, "image", "inspect", requested, "--format", _IMAGE_INSPECT_FORMAT],
                capture_output=True,
                timeout=deadline.bounded_timeout(10) if deadline else 10,
                check=False,
            )
            if deadline is not None:
                deadline.check()
            if result.returncode != 0 or result.stderr or len(result.stdout) > 65_536:
                return None
            payload = json.loads(result.stdout.decode("utf-8").rstrip("\r\n"))
        except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError, json.JSONDecodeError):
            if deadline is not None:
                deadline.check()
            return None
        repo_digests = payload.get("RepoDigests") if isinstance(payload, dict) else None
        if not isinstance(repo_digests, list) or not all(
            isinstance(item, str) and _DOCKER_REPO_DIGEST.fullmatch(item)
            for item in repo_digests
        ):
            return None
        aliases = {requested}
        if requested.startswith("docker.io/"):
            aliases.add(requested.removeprefix("docker.io/"))
        return requested_digest if len(aliases.intersection(repo_digests)) == 1 else None

    def run_check(
        self, workspace: Path, check: RegisteredCheck, *,
        deadline: ExecutionDeadline | None = None,
        execution_identity: dict[str, str] | None = None,
        execution_targets: dict | None = None,
    ) -> SandboxResult:
        docker = self.cli_path()
        if docker is None:
            raise RuntimeError("Docker CLI is not available")
        working_directory = "/workspace"
        if check.working_directory != ".":
            working_directory += f"/{check.working_directory}"
        identity = execution_identity or {"execution_id": uuid.uuid4().hex}
        name = "patchloop-" + sha256_bytes(canonical_json(identity).encode())[7:31]
        started = time.monotonic()

        def cleanup(budget_seconds: float = 5.0) -> bool:
            cleanup_started = time.monotonic()

            def timeout() -> float:
                remaining = min(5.0, budget_seconds) - (time.monotonic() - cleanup_started)
                return min(remaining, deadline.remaining_seconds()) if deadline else remaining

            try:
                inspect_timeout = timeout()
                if inspect_timeout <= 0:
                    return False
                inspected = subprocess.run(
                    [docker, "container", "inspect", "--format",
                     '{{index .Config.Labels "patchloop.execution"}}', name],
                    capture_output=True, timeout=inspect_timeout, check=False,
                )
                if inspected.returncode != 0:
                    return (
                        any(message in (inspected.stderr or b"") for message in
                            (b"No such container", b"No such object"))
                        and name.encode() in (inspected.stderr or b"")
                    )
                if inspected.stdout.strip() != name.encode():
                    return False
                remove_timeout = timeout()
                if remove_timeout <= 0:
                    return False
                removed = subprocess.run(
                    [docker, "rm", "--force", name], capture_output=True,
                    timeout=remove_timeout, check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                return False
            return removed.returncode == 0 or (
                b"No such container" in (removed.stderr or b"")
                and name.encode() in (removed.stderr or b"")
            )

        if deadline is not None:
            deadline.check(reserve_seconds=5)
        if execution_identity is not None and not cleanup():
            return SandboxResult(
                command=list(check.command), exit_code=None, stdout="", stderr="",
                duration_ms=int((time.monotonic() - started) * 1000), timed_out=False,
                truncated=False, original_output_bytes=0, cleanup_failed=True,
                execution_policy=registered_check_execution_policy(
                    image=self.image, working_directory=working_directory,
                    timeout_seconds=check.timeout_seconds,
                    output_limit_bytes=check.output_limit_bytes, cleanup_status="failed",
                ),
            )
        timeout = (
            deadline.bounded_timeout(check.timeout_seconds, reserve_seconds=5)
            if deadline else float(check.timeout_seconds)
        )
        command = [
            docker,
            "run",
            "--rm",
            "--name",
            name,
            "--label",
            f"patchloop.execution={name}",
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
            ]
        )
        cleanup_ok = False
        cleanup_called = False

        def capture_cleanup(budget_seconds: float) -> bool:
            nonlocal cleanup_ok, cleanup_called
            cleanup_called = True
            cleanup_ok = cleanup(budget_seconds)
            return cleanup_ok

        with trace_launch(
            list(check.command), execution_targets, workspace, docker=True,
        ) as (entrypoint, mounts):
            try:
                try:
                    if deadline is not None:
                        timeout = deadline.bounded_timeout(check.timeout_seconds, reserve_seconds=5)
                    captured = capture_process(
                        [*command, *mounts, self.image, *entrypoint],
                        timeout=timeout, output_limit_bytes=check.output_limit_bytes,
                        execution_targets=execution_targets, deadline=deadline,
                        cleanup=capture_cleanup,
                    )
                finally:
                    # The mounted collector must outlive exact-container cleanup.
                    if not cleanup_called:
                        cleanup_ok = cleanup()
            except BaseException as exc:
                if cleanup_ok and not isinstance(exc, SandboxCleanupError):
                    raise
                # An interrupted launcher must not erase the stronger fact that
                # ownership/cleanup is uncertain. The gateway preserves these
                # typed details and stops the run before any further execution.
                policy = registered_check_execution_policy(
                    image=self.image, working_directory=working_directory,
                    timeout_seconds=check.timeout_seconds,
                    output_limit_bytes=check.output_limit_bytes,
                    effective_timeout_seconds=timeout,
                    row_deadline_limited=timeout < check.timeout_seconds,
                    cleanup_status="failed",
                )
                raise SandboxCleanupError(
                    "owned sandbox cleanup could not be confirmed after execution error",
                    details={
                        **(exc.details if isinstance(exc, SandboxCleanupError) else {}),
                        "cleanup_failed": True,
                        "execution_error_type": (
                            exc.details.get("execution_error_type")
                            if isinstance(exc, SandboxCleanupError) else type(exc).__name__
                        ),
                        "execution_policy": policy,
                        "execution_policy_hash": sha256_bytes(canonical_json(policy).encode()),
                    },
                ) from exc
        feedback = None
        if execution_targets is not None:
            feedback = public_feedback(
                execution_targets,
                captured.report if not captured.timed_out and cleanup_ok else None,
            )
        return SandboxResult(
            command=list(check.command),
            exit_code=captured.exit_code,
            stdout=captured.stdout,
            stderr=captured.stderr,
            duration_ms=int((time.monotonic() - started) * 1_000),
            timed_out=captured.timed_out,
            truncated=captured.truncated,
            original_output_bytes=captured.original_output_bytes,
            public_execution=feedback,
            execution_policy=registered_check_execution_policy(
                image=self.image, working_directory=working_directory,
                timeout_seconds=check.timeout_seconds,
                output_limit_bytes=check.output_limit_bytes,
                effective_timeout_seconds=timeout,
                row_deadline_limited=timeout < check.timeout_seconds,
                cleanup_status="confirmed" if cleanup_ok else "failed",
            ),
            deadline_exhausted=(
                deadline is not None
                and (
                    deadline.remaining_seconds() <= 0
                    or (captured.timed_out and timeout < check.timeout_seconds)
                )
            ),
            cleanup_failed=not cleanup_ok,
        )
