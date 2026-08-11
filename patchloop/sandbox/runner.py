"""Registered command execution with bounded output and optional Docker isolation."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol

from patchloop.contracts import (
    DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V1,
    RegisteredCheck,
)
from patchloop.util import ensure_within, sha256_text

PROBE_IMAGE = "patchloop-sandbox:py312"
_PROBE_MANAGED_LABEL = "io.patchloop.managed=probe"
_PROBE_ROLE_LABEL = "io.patchloop.role=agent-probe"
_PROBE_WORKSPACE_LABEL_KEY = "io.patchloop.workspace"
_PROBE_RUNNER_PATH = "/opt/patchloop/probe_runner.py"
_PROBE_TIMEOUT_EXIT_CODE = 124
_PROBE_LAUNCHER_GRACE_SECONDS = 10
_PROXY_ENVIRONMENT_KEYS = (
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
)
_DOCKER_IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}")
_DOCKER_REPO_DIGEST = re.compile(r"[^\x00-\x20\x7f]+@sha256:[0-9a-f]{64}")
_DOCKER_CONTAINER_ID = re.compile(r"[0-9a-f]{12,64}")
_DOCKER_IMAGE_INSPECT_FORMAT = '{"Id":{{json .Id}},"RepoDigests":{{json .RepoDigests}}}'
_DOCKER_IMAGE_INSPECT_OUTPUT_LIMIT_BYTES = 64 * 1024
_DOCKER_IMAGE_INSPECT_MAX_REPO_DIGESTS = 128
_PROBE_RUNTIME_GUARD = """\
import sys as _patchloop_sys

def _patchloop_install_audit_guard():
    denied_import_roots = frozenset({
        "_posixsubprocess",
        "commands",
        "ctypes",
        "importlib",
        "multiprocessing",
        "pty",
        "runpy",
        "subprocess",
    })
    denied_events = frozenset({
        "os.system",
        "pty.spawn",
        "subprocess.Popen",
    })
    denied_prefixes = (
        "ctypes.",
        "os.exec",
        "os.fork",
        "os.kill",
        "os.posix_spawn",
        "os.spawn",
        "pty.",
        "subprocess.",
    )
    def guard(event, args, _roots=denied_import_roots,
              _events=denied_events, _prefixes=denied_prefixes):
        if event == "import" and args:
            root = str(args[0]).split(".", 1)[0]
            if root in _roots:
                raise PermissionError(
                    "PatchLoop probe policy denied import: " + root
                )
        if event in _events or event.startswith(_prefixes):
            raise PermissionError(
                "PatchLoop probe policy denied audit event: " + event
            )

    _patchloop_sys.addaudithook(guard)

_patchloop_install_audit_guard()
del _patchloop_install_audit_guard
_patchloop_sys.dont_write_bytecode = True
_patchloop_sys.path.insert(0, "/workspace")
"""


def probe_execution_policy(
    *,
    image_identity: str,
    timeout_seconds: int,
    output_limit_bytes: int,
) -> dict[str, object]:
    """Return the sanitized policy that must match one probe invocation."""

    if _DOCKER_IMAGE_ID.fullmatch(image_identity) is None:
        raise ValueError("probe image identity must be a sha256 Docker image ID")
    return {
        "schema_version": "probe-execution-policy-v2",
        "image": PROBE_IMAGE,
        "image_identity": image_identity,
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
            "requested_timeout_seconds": timeout_seconds,
            "container_runner": _PROBE_RUNNER_PATH,
            "container_timeout_exit_code": _PROBE_TIMEOUT_EXIT_CODE,
            "launcher_timeout_seconds": (timeout_seconds + _PROBE_LAUNCHER_GRACE_SECONDS),
            "output_limit_bytes": output_limit_bytes,
        },
    }


def registered_check_execution_policy(
    *,
    image: str,
    working_directory: str,
    timeout_seconds: int,
    output_limit_bytes: int,
) -> dict[str, object]:
    """Return the path-free policy requested for one normal Docker check.

    This describes the arguments PatchLoop asks Docker to apply.  It is not a
    container-inspection result and must not be presented as proof that Docker
    or the host enforced the request.
    """

    if not image or image != image.strip() or any(ord(char) < 32 for char in image):
        raise ValueError("registered-check image reference is invalid")
    if not working_directory.startswith("/workspace") or ".." in Path(working_directory).parts:
        raise ValueError("registered-check working directory is invalid")
    if timeout_seconds < 1 or output_limit_bytes < 1:
        raise ValueError("registered-check limits must be positive")
    return {
        "schema_version": "docker-registered-check-requested-policy-v1",
        "image": image,
        "working_directory": working_directory,
        "sandbox_backend": "docker",
        "requested_network": DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V1["requested_network"],
        "read_only_root": DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V1["read_only_root"],
        "read_only_workspace": DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V1["read_only_workspace"],
        "cpus": DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V1["cpus"],
        "memory": DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V1["memory"],
        "pids_limit": DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V1["pids_limit"],
        "tmpfs": DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V1["tmpfs"],
        "requested_timeout_seconds": timeout_seconds,
        "launcher_timeout_seconds": timeout_seconds + 5,
        "output_limit_bytes": output_limit_bytes,
    }


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


@dataclass(frozen=True)
class DockerImageIdentityProjection:
    """Bounded local identity for one digest-pinned repository reference.

    Docker's ``.Id`` is the image configuration digest.  A reference such as
    ``repository@sha256:...`` instead names a repository/manifest digest.  They
    are intentionally kept separate so callers cannot accept a valid image only
    when those unrelated digest namespaces happen to have the same text.
    """

    requested_repo_digest: str
    requested_digest: str
    config_id: str
    repo_digests: tuple[str, ...]
    matched_repo_digest: str | None

    @property
    def verified_identity(self) -> str | None:
        """Return the manifest-bound digest only after RepoDigests membership."""

        return self.requested_digest if self.matched_repo_digest is not None else None


class Sandbox(Protocol):
    official: bool

    def run_check(self, workspace: Path, check: RegisteredCheck) -> SandboxResult: ...

    def run_probe(
        self,
        workspace: Path,
        source: str,
        *,
        timeout_seconds: int,
        output_limit_bytes: int,
        image_identity: str | None = None,
    ) -> SandboxResult: ...


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


class _BoundedPipeCapture:
    """Drain a subprocess pipe while retaining only a bounded prefix in memory."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.prefix = bytearray()
        self.original_bytes = 0

    def drain(self, stream: BinaryIO) -> None:
        try:
            while chunk := stream.read(64 * 1024):
                self.original_bytes += len(chunk)
                remaining = self.limit - len(self.prefix)
                if remaining > 0:
                    self.prefix.extend(chunk[:remaining])
        except OSError:
            pass
        finally:
            stream.close()


def _run_with_bounded_pipes(
    command: list[str],
    *,
    input_bytes: bytes,
    timeout_seconds: int,
    output_limit_bytes: int,
) -> tuple[int | None, bool, bytes, bytes, int]:
    """Run a process without accumulating unbounded stdout/stderr on the host."""

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stdin is None or process.stdout is None or process.stderr is None:
        process.kill()
        process.wait()
        raise RuntimeError("failed to create bounded probe subprocess pipes")

    stdout_capture = _BoundedPipeCapture(output_limit_bytes)
    stderr_capture = _BoundedPipeCapture(output_limit_bytes)
    readers = [
        threading.Thread(
            target=stdout_capture.drain,
            args=(process.stdout,),
            daemon=True,
        ),
        threading.Thread(
            target=stderr_capture.drain,
            args=(process.stderr,),
            daemon=True,
        ),
    ]
    for reader in readers:
        reader.start()

    try:
        try:
            process.stdin.write(input_bytes)
            process.stdin.flush()
        except OSError:
            pass
        finally:
            process.stdin.close()
        try:
            exit_code = process.wait(timeout=timeout_seconds)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            exit_code = None
            process.kill()
            process.wait()
    finally:
        for reader in readers:
            reader.join(timeout=5)
        for stream in (process.stdout, process.stderr):
            if not stream.closed:
                stream.close()

    original_bytes = stdout_capture.original_bytes + stderr_capture.original_bytes
    return (
        exit_code,
        timed_out,
        bytes(stdout_capture.prefix),
        bytes(stderr_capture.prefix),
        original_bytes,
    )


def _requested_repo_digest(image: str) -> tuple[str, str] | None:
    if "@" not in image:
        return None
    repository, digest = image.rsplit("@", 1)
    if not repository or _DOCKER_IMAGE_ID.fullmatch(digest) is None:
        return None
    return image, digest


def _repo_digest_aliases(requested: str) -> frozenset[str]:
    """Return only Docker Hub's two equivalent printed RepoDigest spellings."""

    aliases = {requested}
    if requested.startswith("docker.io/"):
        aliases.add(requested.removeprefix("docker.io/"))
    return frozenset(aliases)


def _docker_repo_digest_projection(
    docker: str,
    image: str,
) -> DockerImageIdentityProjection | None:
    requested = _requested_repo_digest(image)
    if requested is None:
        return None
    requested_repo_digest, requested_digest = requested
    command = [
        docker,
        "image",
        "inspect",
        image,
        "--format",
        _DOCKER_IMAGE_INSPECT_FORMAT,
    ]
    try:
        exit_code, timed_out, stdout, stderr, original_bytes = _run_with_bounded_pipes(
            command,
            input_bytes=b"",
            timeout_seconds=10,
            output_limit_bytes=_DOCKER_IMAGE_INSPECT_OUTPUT_LIMIT_BYTES,
        )
    except (OSError, RuntimeError, subprocess.SubprocessError):
        return None
    if (
        timed_out
        or exit_code != 0
        or stderr
        or original_bytes > _DOCKER_IMAGE_INSPECT_OUTPUT_LIMIT_BYTES
    ):
        return None
    try:
        payload = json.loads(stdout.decode("utf-8").rstrip("\r\n"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or tuple(payload) != ("Id", "RepoDigests"):
        return None
    config_id = payload["Id"]
    repo_digests = payload["RepoDigests"]
    if not isinstance(config_id, str) or _DOCKER_IMAGE_ID.fullmatch(config_id) is None:
        return None
    if (
        not isinstance(repo_digests, list)
        or len(repo_digests) > _DOCKER_IMAGE_INSPECT_MAX_REPO_DIGESTS
        or not all(
            isinstance(item, str)
            and len(item.encode("utf-8")) <= 512
            and _DOCKER_REPO_DIGEST.fullmatch(item) is not None
            for item in repo_digests
        )
    ):
        return None
    if len(repo_digests) != len(set(repo_digests)):
        return None
    normalized = tuple(sorted(repo_digests))
    aliases = _repo_digest_aliases(requested_repo_digest)
    matches = [item for item in normalized if item in aliases]
    if len(matches) > 1:
        return None
    return DockerImageIdentityProjection(
        requested_repo_digest=requested_repo_digest,
        requested_digest=requested_digest,
        config_id=config_id,
        repo_digests=normalized,
        matched_repo_digest=matches[0] if matches else None,
    )


def _docker_image_identity(docker: str, image: str) -> str | None:
    if "@" in image:
        projection = _docker_repo_digest_projection(docker, image)
        return projection.verified_identity if projection is not None else None
    try:
        result = subprocess.run(
            [docker, "image", "inspect", image, "--format", "{{.Id}}"],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    identity = result.stdout.decode("utf-8", errors="replace").strip()
    return identity if _DOCKER_IMAGE_ID.fullmatch(identity) else None


def _probe_workspace_identity(workspace: Path) -> tuple[Path, str]:
    """Require managed-checkout Git metadata before exposing a workspace."""

    try:
        resolved = workspace.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError("probe workspace is unavailable") from exc
    if not resolved.is_dir():
        raise RuntimeError("probe workspace must be a directory")
    git_metadata = resolved / ".git"
    try:
        junction_check = getattr(git_metadata, "is_junction", None)
        is_junction = bool(junction_check is not None and junction_check())
        invalid = git_metadata.is_symlink() or is_junction or not git_metadata.is_dir()
    except OSError as exc:
        raise RuntimeError("probe workspace Git metadata cannot be inspected") from exc
    if invalid:
        raise RuntimeError("probe workspace requires a real non-symlink .git directory")
    digest = sha256_text(str(resolved)).removeprefix("sha256:")
    return resolved, f"{_PROBE_WORKSPACE_LABEL_KEY}={digest}"


def _confirm_probe_container_removed(
    docker: str,
    reference: str,
    *,
    filter_kind: str,
) -> bool:
    """Force-remove one container and independently confirm its absence."""

    with suppress(OSError, subprocess.TimeoutExpired):
        subprocess.run(
            [docker, "rm", "--force", reference],
            capture_output=True,
            timeout=10,
            check=False,
        )
    try:
        remaining = subprocess.run(
            [
                docker,
                "ps",
                "--all",
                "--quiet",
                "--filter",
                f"{filter_kind}={reference}",
            ],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return remaining.returncode == 0 and not remaining.stdout.strip()


def _reap_stale_probe_containers(
    docker: str,
    workspace_label: str,
) -> None:
    """Remove a prior worker's probe for the same managed workspace."""

    try:
        listing = subprocess.run(
            [
                docker,
                "ps",
                "--all",
                "--quiet",
                "--filter",
                f"label={_PROBE_MANAGED_LABEL}",
                "--filter",
                f"label={workspace_label}",
            ],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("stale probe container inspection could not be confirmed") from exc
    if listing.returncode != 0:
        raise RuntimeError("stale probe container inspection could not be confirmed")
    container_ids = listing.stdout.decode(
        "ascii",
        errors="strict",
    ).split()
    if any(_DOCKER_CONTAINER_ID.fullmatch(container_id) is None for container_id in container_ids):
        raise RuntimeError("stale probe container inspection returned an invalid identity")
    for container_id in container_ids:
        if not _confirm_probe_container_removed(
            docker,
            container_id,
            filter_kind="id",
        ):
            raise RuntimeError("stale probe container cleanup could not be confirmed")


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
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": str(workspace),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_ADDOPTS": "-p no:cacheprovider",
        }
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

    def run_probe(
        self,
        workspace: Path,
        source: str,
        *,
        timeout_seconds: int,
        output_limit_bytes: int,
        image_identity: str | None = None,
    ) -> SandboxResult:
        del (
            workspace,
            source,
            timeout_seconds,
            output_limit_bytes,
            image_identity,
        )
        raise RuntimeError("agent-authored probes require an isolated Docker sandbox")


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
                    Path(local_app_data) / "Docker" / "resources" / "bin" / "docker.exe",
                ]
            )
        program_files = os.environ.get("PROGRAMFILES")
        if program_files:
            candidates.append(
                Path(program_files) / "Docker" / "Docker" / "resources" / "bin" / "docker.exe"
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
        if not docker:
            return None
        return _docker_image_identity(docker, self.image)

    def image_identity_projection(self) -> DockerImageIdentityProjection | None:
        """Return separate manifest/config identities for a digest-pinned image."""

        docker = self.cli_path()
        if not docker:
            return None
        return _docker_repo_digest_projection(docker, self.image)

    def probe_image_identity(self) -> str | None:
        """Return the strict local content identity of the dedicated probe image."""

        docker = self.cli_path()
        if not docker:
            return None
        return _docker_image_identity(docker, PROBE_IMAGE)

    def run_check(self, workspace: Path, check: RegisteredCheck) -> SandboxResult:
        docker = self.cli_path()
        if not docker:
            raise RuntimeError("Docker CLI is not available")
        workdir = "/workspace"
        if check.working_directory != ".":
            workdir = f"/workspace/{check.working_directory}"
        execution_policy = registered_check_execution_policy(
            image=self.image,
            working_directory=workdir,
            timeout_seconds=check.timeout_seconds,
            output_limit_bytes=check.output_limit_bytes,
        )
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
            execution_policy=execution_policy,
        )

    def run_probe(
        self,
        workspace: Path,
        source: str,
        *,
        timeout_seconds: int,
        output_limit_bytes: int,
        image_identity: str | None = None,
    ) -> SandboxResult:
        """Execute an ephemeral Python probe without writing it into the repository."""

        docker = self.cli_path()
        if not docker:
            raise RuntimeError("Docker CLI is not available")
        resolved_workspace, workspace_label = _probe_workspace_identity(workspace)
        _reap_stale_probe_containers(docker, workspace_label)
        tag_image_identity = self.probe_image_identity()
        if tag_image_identity is None:
            raise RuntimeError("dedicated PatchLoop probe image is unavailable or invalid")
        if image_identity is not None and _DOCKER_IMAGE_ID.fullmatch(image_identity) is None:
            raise RuntimeError("manifest-bound probe image identity is invalid")
        probe_image_identity = image_identity or tag_image_identity
        if tag_image_identity != probe_image_identity:
            raise RuntimeError(
                "dedicated probe image tag does not match the manifest-bound identity"
            )
        bootstrap = (_PROBE_RUNTIME_GUARD + source).encode("utf-8")
        container_name = f"patchloop-probe-{uuid.uuid4().hex}"
        create_command = [
            docker,
            "create",
            "--name",
            container_name,
            "--label",
            _PROBE_MANAGED_LABEL,
            "--label",
            _PROBE_ROLE_LABEL,
            "--label",
            workspace_label,
            "-i",
            "--network",
            "none",
            "--cpus",
            "1",
            "--memory",
            "512m",
            "--pids-limit",
            "2",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            # The gateway requires a real Git checkout above, so this nested
            # mount always hides the underlying history and remote metadata.
            "--tmpfs",
            "/workspace/.git:ro,noexec,nosuid,nodev,size=64k",
        ]
        create_command.extend(
            [
                "--user",
                "10001:10001",
                "--env",
                "HOME=/tmp",
                "--env",
                "PYTHONDONTWRITEBYTECODE=1",
            ]
        )
        for key in _PROXY_ENVIRONMENT_KEYS:
            create_command.extend(["--env", f"{key}="])
        create_command.extend(
            [
                "--mount",
                (f"type=bind,source={resolved_workspace},target=/workspace,readonly"),
                "--workdir",
                "/workspace",
                probe_image_identity,
                "python",
                "-I",
                _PROBE_RUNNER_PATH,
                str(timeout_seconds),
            ]
        )
        start_command = [
            docker,
            "start",
            "--attach",
            "--interactive",
            container_name,
        ]
        execution_policy = probe_execution_policy(
            image_identity=probe_image_identity,
            timeout_seconds=timeout_seconds,
            output_limit_bytes=output_limit_bytes,
        )
        started = time.monotonic()
        try:
            try:
                created = subprocess.run(
                    create_command,
                    capture_output=True,
                    timeout=15,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise RuntimeError("probe container creation could not be confirmed") from exc
            container_id = created.stdout.decode(
                "ascii",
                errors="strict",
            ).strip()
            if created.returncode != 0 or _DOCKER_CONTAINER_ID.fullmatch(container_id) is None:
                raise RuntimeError("probe container creation could not be confirmed")
            try:
                inspected = subprocess.run(
                    [
                        docker,
                        "container",
                        "inspect",
                        container_name,
                        "--format",
                        "{{.Image}}",
                    ],
                    capture_output=True,
                    timeout=10,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise RuntimeError("probe container image identity could not be confirmed") from exc
            actual_image_identity = inspected.stdout.decode(
                "ascii",
                errors="strict",
            ).strip()
            if inspected.returncode != 0 or actual_image_identity != probe_image_identity:
                raise RuntimeError(
                    "probe container image does not match the manifest-bound identity"
                )
            (
                exit_code,
                timed_out,
                stdout,
                stderr,
                original,
            ) = _run_with_bounded_pipes(
                start_command,
                input_bytes=bootstrap,
                timeout_seconds=(timeout_seconds + _PROBE_LAUNCHER_GRACE_SECONDS),
                output_limit_bytes=output_limit_bytes,
            )
        finally:
            if not _confirm_probe_container_removed(
                docker,
                container_name,
                filter_kind="name",
            ):
                raise RuntimeError("probe container cleanup could not be confirmed")
        if not timed_out and exit_code == _PROBE_TIMEOUT_EXIT_CODE:
            timed_out = True
            exit_code = None
        duration = int((time.monotonic() - started) * 1000)
        stdout_text, stderr_text, truncated, bounded_original = _bounded_text(
            stdout,
            stderr,
            output_limit_bytes,
        )
        truncated = truncated or original > output_limit_bytes
        return SandboxResult(
            command=["python", "-I", "<ephemeral-probe>"],
            exit_code=exit_code,
            stdout=stdout_text,
            stderr=stderr_text,
            duration_ms=duration,
            timed_out=timed_out,
            truncated=truncated,
            original_output_bytes=max(original, bounded_original),
            execution_policy=execution_policy,
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

    def run_probe(
        self,
        workspace: Path,
        source: str,
        *,
        timeout_seconds: int,
        output_limit_bytes: int,
        image_identity: str | None = None,
    ) -> SandboxResult:
        return self.delegate.run_probe(
            workspace,
            source,
            timeout_seconds=timeout_seconds,
            output_limit_bytes=output_limit_bytes,
            image_identity=image_identity,
        )
