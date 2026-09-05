"""Opt-in Python experiments over an exported public snapshot, never the worktree.

The image is one reviewed public Python base, not an evaluator image. The trusted
wrapper and all launcher restrictions are part of the profile identity. Python
source is deliberately not AST-filtered: Docker and the wrapper are the boundary.
"""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import threading
import time
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from patchloop.deadline import ExecutionDeadline
from patchloop.errors import ContractError
from patchloop.sandbox.runner import DockerSandbox
from patchloop.util import sha256_bytes, sha256_json

PROBE_IMAGE_DIGEST = "sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de"
# This digest pins the reviewed Python 3.12-slim image. Use Docker's canonical
# repository@digest name for lookup and execution, not a tag+digest alias.
PROBE_IMAGE = "python@" + PROBE_IMAGE_DIGEST
PROBE_TIMEOUT_SECONDS = 30
PROBE_OUTPUT_LIMIT_BYTES = 12_000
PROBE_SOURCE_LIMIT_CHARS = 8_000
PROBE_SOURCE_LIMIT_BYTES = 32_000
_SNAPSHOT_LIMIT_BYTES = 128 * 1024 * 1024
_CLEANUP_SECONDS = 5.0
_WRAPPER = Path(__file__).resolve().parents[2] / "docker" / "probe_runner.py"


def probe_profile() -> dict[str, object]:
    return {
        "version": "docker-python-probe-v1",
        "image": PROBE_IMAGE,
        "image_digest": PROBE_IMAGE_DIGEST,
        "wrapper_hash": sha256_bytes(_WRAPPER.read_bytes()),
        "network": "none",
        "read_only": True,
        "user": "10001:10001",
        "cap_drop": "ALL",
        "no_new_privileges": True,
        "pids_limit": 2,
        "memory": "512m",
        "memory_swap": "512m",
        "cpus": "1",
        "tmpfs": "/tmp:rw,noexec,nosuid,nodev,size=64m",
        "entrypoint": "/usr/local/bin/python",
        "working_directory": "/tmp",
        "source_mount": "/workspace:readonly",
        "source_limit_chars": PROBE_SOURCE_LIMIT_CHARS,
        "source_limit_bytes": PROBE_SOURCE_LIMIT_BYTES,
        "timeout_seconds": PROBE_TIMEOUT_SECONDS,
        "output_limit_bytes": PROBE_OUTPUT_LIMIT_BYTES,
        "snapshot": "tracked-public-current-v1",
        "snapshot_limit_bytes": _SNAPSHOT_LIMIT_BYTES,
    }


def probe_profile_hash() -> str:
    return sha256_json(probe_profile())


def probe_execution_policy(
    *, effective_timeout_seconds: float, row_deadline_limited: bool, cleanup_status: str,
    profile: dict[str, object] | None = None,
) -> dict[str, object]:
    if not 0 < effective_timeout_seconds <= PROBE_TIMEOUT_SECONDS:
        raise ValueError("invalid probe effective timeout")
    if cleanup_status not in {"confirmed", "failed"}:
        raise ValueError("invalid probe cleanup status")
    profile = probe_profile() if profile is None else dict(profile)
    return {
        **profile,
        "profile_hash": sha256_json(profile),
        "requested_timeout_seconds": PROBE_TIMEOUT_SECONDS,
        "effective_timeout_seconds": effective_timeout_seconds,
        "row_deadline_limited": row_deadline_limited,
        "cleanup_status": cleanup_status,
    }


def _is_public_path(relative: str) -> bool:
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ContractError("invalid tracked probe source path")
    return all(
        part.casefold() not in {".git", ".patchloop-hidden"}
        and not part.casefold().startswith(".env")
        for part in path.parts
    )


def _snapshot(workspace: Path, target: Path, deadline: ExecutionDeadline | None) -> str:
    """Export tracked current bytes without copying Git metadata or ignored state."""
    timeout = deadline.bounded_timeout(10, reserve_seconds=5) if deadline else 10
    listing = subprocess.run(
        ["git", "ls-files", "--stage", "-z"], cwd=workspace,
        capture_output=True, timeout=timeout, check=False,
    )
    if listing.returncode or len(listing.stdout) > 2_000_000:
        raise ContractError("probe cannot enumerate tracked public source")
    manifest = []
    total_bytes = 0
    root = workspace.resolve()
    seen: set[str] = set()
    for entry in listing.stdout.split(b"\0"):
        if not entry:
            continue
        metadata, path_bytes = entry.split(b"\t", 1)
        mode, _object_id, stage = metadata.decode("ascii").split()
        relative = path_bytes.decode("utf-8")
        if not _is_public_path(relative):
            continue
        if mode not in {"100644", "100755"} or stage != "0" or relative in seen:
            raise ContractError("probe source must contain only tracked regular files")
        seen.add(relative)
        source = root / relative
        for part in (source, *source.parents):
            if part == root:
                break
            attributes = part.lstat()
            if part.is_symlink() or getattr(attributes, "st_file_attributes", 0) & 0x400:
                raise ContractError("probe source symlink or reparse point is forbidden")
        if not source.resolve().is_relative_to(root) or not stat.S_ISREG(source.stat().st_mode):
            raise ContractError("probe source is not a regular workspace file")
        if deadline:
            deadline.check(reserve_seconds=5)
        size = source.stat().st_size
        if total_bytes + size > _SNAPSHOT_LIMIT_BYTES:
            raise ContractError("probe public snapshot exceeds byte limit")
        with source.open("rb") as stream:
            before = os.fstat(stream.fileno())
            content = stream.read(_SNAPSHOT_LIMIT_BYTES - total_bytes + 1)
            after = os.fstat(stream.fileno())
        current = source.lstat()
        if (
            source.is_symlink() or not source.resolve().is_relative_to(root)
            or (before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_ino, after.st_size, after.st_mtime_ns)
            or (after.st_ino, after.st_size, after.st_mtime_ns)
            != (current.st_ino, current.st_size, current.st_mtime_ns)
        ):
            raise ContractError("probe source changed during snapshot export")
        total_bytes += len(content)
        if total_bytes > _SNAPSHOT_LIMIT_BYTES:
            raise ContractError("probe public snapshot exceeds byte limit")
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        destination.chmod(0o444)
        manifest.append({"path": relative, "content_hash": sha256_bytes(content)})
    return sha256_json(sorted(manifest, key=lambda item: item["path"]))


class _OutputCollector:
    """Bound retained memory while two pipe readers drain concurrently."""

    def __init__(self) -> None:
        self.streams = {"stdout": bytearray(), "stderr": bytearray()}
        self.observed = 0
        self.limit_hit = threading.Event()
        self.lock = threading.Lock()

    def drain(self, stream: BinaryIO, name: str) -> None:
        try:
            while block := stream.read(4096):
                with self.lock:
                    retained = sum(len(value) for value in self.streams.values())
                    self.streams[name].extend(block[:max(0, PROBE_OUTPUT_LIMIT_BYTES - retained)])
                    self.observed += len(block)
                    if (
                        self.observed > PROBE_OUTPUT_LIMIT_BYTES
                        and not self.limit_hit.is_set()
                    ):
                        self.limit_hit.set()
                    # Keep draining and discard after the retention cap. Leaving
                    # Docker's attach pipe unread can block its own teardown while
                    # the main thread is removing the exact owned container.
        except (OSError, ValueError):
            return

    def public_text(self) -> tuple[str, str]:
        # Replacement characters can expand invalid UTF-8; also bound the
        # serialized public output rather than only the original pipe bytes.
        remaining = PROBE_OUTPUT_LIMIT_BYTES
        text = []
        for name in ("stdout", "stderr"):
            encoded = self.streams[name].decode("utf-8", errors="replace").encode("utf-8")
            bounded = encoded[:remaining].decode("utf-8", errors="ignore")
            text.append(bounded)
            remaining -= len(bounded.encode("utf-8"))
        return text[0], text[1]


class DockerProbeSandbox:
    """No local fallback, image acquisition, evaluator mounts, or caller commands."""

    def __init__(self, image: str = PROBE_IMAGE) -> None:
        if image != PROBE_IMAGE:
            raise ContractError("probe requires the reviewed public Python image")
        self.image = image
        self._profile = probe_profile()
        self._verified = False

    @property
    def identity(self) -> dict[str, str]:
        return {"image_digest": PROBE_IMAGE_DIGEST, "profile_hash": sha256_json(self._profile)}

    def preflight(self) -> dict[str, str]:
        if probe_profile() != self._profile:
            raise ContractError("probe trusted profile changed before preflight")
        if DockerSandbox(self.image).image_identity() != PROBE_IMAGE_DIGEST:
            raise ContractError("probe public Python image is not available at its pinned digest")
        self._verified = True
        return self.identity

    @staticmethod
    def container_name(execution_identity: dict[str, str]) -> str:
        if not execution_identity:
            raise ContractError("probe requires a durable run/action execution identity")
        return "patchloop-probe-" + sha256_json(execution_identity)[7:31]

    @staticmethod
    def _cleanup(docker: str, name: str, deadline: ExecutionDeadline | None) -> bool:
        started = time.monotonic()

        def remaining() -> float:
            allowance = _CLEANUP_SECONDS - (time.monotonic() - started)
            if deadline:
                allowance = min(allowance, deadline.remaining_seconds())
            if allowance <= 0:
                raise subprocess.TimeoutExpired("probe cleanup", 0)
            return allowance

        try:
            inspected = subprocess.run(
                [docker, "container", "inspect", "--format",
                 '{{index .Config.Labels "io.patchloop.probe.execution"}}', name],
                capture_output=True, timeout=remaining(), check=False,
            )
            if inspected.returncode:
                return (
                    any(token in inspected.stderr for token in
                        (b"No such container", b"No such object"))
                    and name.encode() in inspected.stderr
                )
            if inspected.stdout.strip() != name.encode():
                return False
            removed = subprocess.run(
                [docker, "rm", "--force", name], capture_output=True,
                timeout=remaining(), check=False,
            )
            return removed.returncode == 0 or (
                b"No such container" in removed.stderr and name.encode() in removed.stderr
            )
        except (OSError, subprocess.TimeoutExpired):
            return False

    def run_probe(
        self, workspace: Path, question: str, python_source: str, *,
        deadline: ExecutionDeadline | None,
        execution_identity: dict[str, str],
    ) -> dict[str, object]:
        source = python_source.encode("utf-8")
        if not question or len(question) > 500:
            raise ContractError("probe question must contain 1 to 500 characters")
        if not source or len(python_source) > 8000 or len(source) > 32000:
            raise ContractError("probe Python source exceeds its bounded input contract")
        if deadline:
            deadline.check(reserve_seconds=_CLEANUP_SECONDS)
        if not self._verified:
            raise ContractError("probe must pass preflight before execution")
        if probe_profile() != self._profile:
            raise ContractError("probe trusted profile changed after preflight")
        docker = DockerSandbox.cli_path()
        if docker is None:
            raise ContractError("Docker CLI is not available for probes")
        name = self.container_name(execution_identity)
        started = time.monotonic()
        timeout = (
            deadline.bounded_timeout(PROBE_TIMEOUT_SECONDS, reserve_seconds=_CLEANUP_SECONDS)
            if deadline else float(PROBE_TIMEOUT_SECONDS)
        )
        collector = _OutputCollector()
        timed_out = False
        exit_code = None
        snapshot_hash = None
        cleanup_ok = self._cleanup(docker, name, deadline)
        if cleanup_ok:
            with tempfile.TemporaryDirectory(prefix="patchloop-probe-") as temporary:
                temporary_path = Path(temporary)
                if temporary_path.resolve().is_relative_to(workspace.resolve()):
                    raise ContractError("probe temporary root must be outside the workspace")
                snapshot = temporary_path / "source"
                trusted = temporary_path / "trusted"
                snapshot.mkdir()
                trusted.mkdir()
                snapshot_hash = _snapshot(workspace, snapshot, deadline)
                wrapper = _WRAPPER.read_bytes()
                (trusted / "probe_runner.py").write_bytes(wrapper)
                if sha256_bytes(wrapper) != self._profile["wrapper_hash"]:
                    raise ContractError("probe trusted wrapper changed before execution")
                timeout = (
                    deadline.bounded_timeout(
                        PROBE_TIMEOUT_SECONDS, reserve_seconds=_CLEANUP_SECONDS
                    )
                    if deadline else float(PROBE_TIMEOUT_SECONDS)
                )
                command = [
                    docker, "run", "--rm", "--interactive", "--name", name,
                    "--label", f"io.patchloop.probe.execution={name}",
                    "--pull", "never", "--network", "none", "--read-only",
                    "--user", "10001:10001", "--cap-drop", "ALL",
                    "--security-opt", "no-new-privileges=true", "--pids-limit", "2",
                    "--cpus", "1", "--memory", "512m", "--memory-swap", "512m",
                    "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=64m",
                    "--env", "PYTHONDONTWRITEBYTECODE=1", "--env", "PYTHONUNBUFFERED=1",
                    "--mount", f"type=bind,source={snapshot},target=/workspace,readonly",
                    "--mount", f"type=bind,source={trusted},target=/opt/patchloop,readonly",
                    "--workdir", "/tmp", "--entrypoint", "/usr/local/bin/python",
                    self.image, "-I", "-u", "/opt/patchloop/probe_runner.py", "30",
                ]
                process = None
                readers: list[threading.Thread] = []
                try:
                    process = subprocess.Popen(
                        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, bufsize=0,
                        env={key: os.environ[key] for key in
                             ("PATH", "SystemRoot", "USERPROFILE", "HOME", "DOCKER_HOST",
                              "DOCKER_CONTEXT", "DOCKER_CONFIG", "DOCKER_CERT_PATH",
                              "DOCKER_TLS_VERIFY") if key in os.environ},
                    )
                    assert process.stdin is not None
                    assert process.stdout is not None and process.stderr is not None

                    def write_source() -> None:
                        try:
                            pending = memoryview(source)
                            while pending:
                                written = process.stdin.write(pending)
                                if not written:
                                    break
                                pending = pending[written:]
                            process.stdin.close()
                        except (OSError, ValueError):
                            pass

                    readers = [
                        threading.Thread(target=collector.drain, args=(stream, label), daemon=True)
                        for stream, label in
                        ((process.stdout, "stdout"), (process.stderr, "stderr"))
                    ]
                    writer = threading.Thread(target=write_source, daemon=True)
                    for reader in readers:
                        reader.start()
                    writer.start()
                    execution_started = time.monotonic()
                    while process.poll() is None:
                        if collector.limit_hit.is_set():
                            break
                        if time.monotonic() - execution_started >= timeout:
                            timed_out = True
                            break
                        collector.limit_hit.wait(min(0.02, timeout))
                    exit_code = process.poll()
                except OSError:
                    collector.streams["stderr"].extend(b"probe Docker launch failed")
                finally:
                    cleanup_end = time.monotonic() + min(
                        _CLEANUP_SECONDS,
                        deadline.remaining_seconds() if deadline else _CLEANUP_SECONDS,
                    )

                    def cleanup_remaining() -> float:
                        return max(0.0, cleanup_end - time.monotonic())

                    cleanup_ok = self._cleanup(docker, name, deadline)
                    if process is not None:
                        if process.poll() is None:
                            process.kill()
                        try:
                            process.wait(timeout=cleanup_remaining())
                        except subprocess.TimeoutExpired:
                            cleanup_ok = False
                        for reader in readers:
                            reader.join(timeout=cleanup_remaining())
                            if reader.is_alive():
                                cleanup_ok = False
                        for stream in (process.stdin, process.stdout, process.stderr):
                            if stream is not None:
                                stream.close()
        timed_out = timed_out or exit_code == 124
        policy = probe_execution_policy(
            effective_timeout_seconds=timeout,
            row_deadline_limited=timeout < PROBE_TIMEOUT_SECONDS,
            cleanup_status="confirmed" if cleanup_ok else "failed",
            profile=self._profile,
        )
        deadline_exhausted = bool(deadline and (
            deadline.remaining_seconds() <= 0 or (timed_out and timeout < PROBE_TIMEOUT_SECONDS)
        ))
        status = (
            "cleanup_failed" if not cleanup_ok else "timeout" if timed_out
            else "output_limit" if collector.limit_hit.is_set()
            else "passed" if exit_code == 0 else "failed"
        )
        stdout_text, stderr_text = collector.public_text()
        return {
            "status": status, "source_hash": sha256_bytes(source),
            "snapshot_hash": snapshot_hash, **self.identity,
            "exit_code": exit_code, "timed_out": timed_out,
            "deadline_exhausted": deadline_exhausted, "cleanup_failed": not cleanup_ok,
            "stdout": stdout_text, "stderr": stderr_text,
            "truncated": collector.limit_hit.is_set(),
            "captured_output_bytes": sum(len(value) for value in collector.streams.values()),
            "observed_output_bytes": collector.observed,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "execution_policy": policy, "execution_policy_hash": sha256_json(policy),
        }
