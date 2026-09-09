"""Bounded retained output while registered checks keep running and draining."""

from __future__ import annotations

import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from patchloop.deadline import ExecutionDeadline
from patchloop.errors import PatchLoopError
from patchloop.sandbox.execution_feedback import ReportChannel

_BLOCK_BYTES = 4_096
_CLEANUP_SECONDS = 5.0


class SandboxCleanupError(PatchLoopError):
    code = "SANDBOX_CLEANUP_FAILED"


def bounded_text(
    stdout: bytes, stderr: bytes, limit: int, *,
    stdout_bytes: int | None = None, stderr_bytes: int | None = None,
) -> tuple[str, str, bool, int]:
    """Allocate by full observed byte counts, not clipped/line-aligned prefixes."""

    stdout_bytes = len(stdout) if stdout_bytes is None else stdout_bytes
    stderr_bytes = len(stderr) if stderr_bytes is None else stderr_bytes

    def prefix(data: bytes, observed: int, capacity: int) -> bytes:
        result = data[:capacity]
        return result if observed <= capacity else result[:result.rfind(b"\n") + 1]

    original = stdout_bytes + stderr_bytes
    return (
        prefix(stdout, stdout_bytes, limit).decode("utf-8", errors="replace"),
        prefix(stderr, stderr_bytes, max(0, limit - stdout_bytes)).decode(
            "utf-8", errors="replace",
        ),
        original > limit,
        original,
    )


class OutputCollector:
    """At most two public prefixes plus the separately bounded report channel."""

    def __init__(self, limit: int, execution_targets: dict | None = None) -> None:
        self.limit = limit
        self.streams = {"stdout": bytearray(), "stderr": bytearray()}
        self.observed = {"stdout": 0, "stderr": 0}
        self.errors: list[BaseException] = []
        self.failed = threading.Event()
        self.report = None
        self.channel = (
            ReportChannel(execution_targets, lambda block: self.retain(block, "stderr"))
            if execution_targets is not None else None
        )

    def retain(self, block: bytes, name: str) -> None:
        # One reader owns each stream; no shared arrival-order quota is used.
        stream = self.streams[name]
        stream.extend(block[:max(0, self.limit - len(stream))])
        self.observed[name] += len(block)

    def feed(self, block: bytes, name: str) -> None:
        if name == "stderr" and self.channel is not None:
            self.channel.feed(block)
        else:
            self.retain(block, name)

    def drain(self, stream: BinaryIO, name: str) -> None:
        try:
            while block := stream.read(_BLOCK_BYTES):
                self.feed(block, name)
        except BaseException as exc:
            self.errors.append(exc)
            self.failed.set()
        finally:
            try:
                if name == "stderr" and self.channel is not None:
                    self.report = self.channel.finish()
                stream.close()
            except BaseException as exc:
                self.errors.append(exc)
                self.failed.set()

    def public_text(self) -> tuple[str, str, bool, int]:
        return bounded_text(
            bytes(self.streams["stdout"]), bytes(self.streams["stderr"]), self.limit,
            stdout_bytes=self.observed["stdout"], stderr_bytes=self.observed["stderr"],
        )


@dataclass(frozen=True)
class CapturedProcess:
    exit_code: int | None
    timed_out: bool
    stdout: str
    stderr: str
    truncated: bool
    original_output_bytes: int
    report: object = None
    cleanup_failed: bool = False


def capture_process(
    command: list[str], *, timeout: float, output_limit_bytes: int,
    cwd: Path | None = None, env: dict[str, str] | None = None,
    execution_targets: dict | None = None, deadline: ExecutionDeadline | None = None,
    cleanup: Callable[[float], bool] | None = None,
) -> CapturedProcess:
    """Run once, drain past the public cap, and bound launcher/pipe teardown.

    The owner callback runs inside the same cleanup budget before pipe joins. A
    Docker container can otherwise keep inherited pipes open after its CLI exits.
    An unjoined reader or failed close is uncertainty, never a semantic verdict.
    """

    collector = OutputCollector(output_limit_bytes, execution_targets)
    process = None
    readers: list[threading.Thread] = []
    primary_error: BaseException | None = None
    resource_errors: list[str] = []
    timed_out = False
    cleanup_ok = True
    exit_code = None
    execution_end = time.monotonic() + max(0.0, timeout)
    try:
        if deadline is not None:
            deadline.check()
        process = subprocess.Popen(
            command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0,
        )
        assert process.stdout is not None and process.stderr is not None
        for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
            reader = threading.Thread(
                target=collector.drain, args=(stream, name), daemon=True,
                name=f"check-{name}",
            )
            reader.start()
            readers.append(reader)
        while process.poll() is None:
            if collector.failed.is_set():
                break
            remaining = execution_end - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            try:
                process.wait(timeout=min(0.05, remaining))
            except subprocess.TimeoutExpired:
                continue
        if not timed_out:
            exit_code = process.poll()
    except BaseException as exc:
        primary_error = exc
    finally:
        cleanup_end = time.monotonic() + min(
            _CLEANUP_SECONDS, deadline.remaining_seconds() if deadline else _CLEANUP_SECONDS,
        )

        def remaining_cleanup() -> float:
            return max(0.0, cleanup_end - time.monotonic())

        if process is not None:
            try:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=remaining_cleanup())
            except BaseException as exc:
                resource_errors.append(type(exc).__name__)
        if cleanup is not None:
            try:
                cleanup_ok = cleanup(remaining_cleanup())
            except BaseException as exc:
                cleanup_ok = False
                resource_errors.append(type(exc).__name__)
        for reader in readers:
            try:
                reader.join(timeout=remaining_cleanup())
                if reader.is_alive():
                    resource_errors.append("reader_not_joined")
            except BaseException as exc:
                resource_errors.append(type(exc).__name__)
        # A reader owns and closes its raw pipe. Close only unassigned pipes here;
        # closing an active buffered reader from another thread could block.
        if process is not None:
            for stream in (process.stdout, process.stderr)[len(readers):]:
                if stream is not None:
                    try:
                        stream.close()
                    except BaseException as exc:
                        resource_errors.append(type(exc).__name__)

    if collector.errors:
        resource_errors.extend(type(error).__name__ for error in collector.errors)
    if resource_errors or (primary_error is not None and not cleanup_ok):
        raise SandboxCleanupError(
            "registered check process or output cleanup could not be confirmed",
            details={
                "cleanup_failed": True,
                "capture_errors": resource_errors[:4],
                "execution_error_type": type(primary_error).__name__ if primary_error else None,
            },
        ) from primary_error
    if primary_error is not None:
        raise primary_error
    stdout, stderr, truncated, original = collector.public_text()
    return CapturedProcess(
        exit_code=exit_code, timed_out=timed_out, stdout=stdout, stderr=stderr,
        truncated=truncated, original_output_bytes=original, report=collector.report,
        cleanup_failed=not cleanup_ok,
    )
