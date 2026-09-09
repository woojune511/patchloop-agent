"""Time-bounded Git execution with exact byte capture and explicit row deadlines.

Capture uses files, not reader pipes: a Windows helper retaining stdout cannot
make post-timeout communicate() wait forever. Only the direct Git process is
reaped here. A timeout never claims that descendants were cleaned up; callers
must stop the row/repetitions on the typed uncertain outcome.
"""

from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Mapping
from pathlib import Path

from patchloop.deadline import ExecutionDeadline
from patchloop.errors import ContractError, RecoveryError

GIT_TIMEOUT_SECONDS = 120.0
GIT_CLEANUP_SECONDS = 1.0


class GitExecutionUncertain(RecoveryError):
    code = "GIT_EXECUTION_UNCERTAIN"


def run_git(
    workspace: Path,
    *arguments: str,
    deadline: ExecutionDeadline | None = None,
    timeout_seconds: float = GIT_TIMEOUT_SECONDS,
    check: bool = True,
    text: bool = True,
    input: bytes | None = None,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run once; never retry, truncate output, invoke a shell or expose stdin bytes."""
    if timeout_seconds <= 0:
        raise ValueError("Git timeout must be positive")
    remaining = deadline.check() if deadline is not None else None
    cleanup_reserve = min(GIT_CLEANUP_SECONDS, remaining / 10) if remaining else 1.0
    timeout = min(timeout_seconds, remaining - cleanup_reserve) if remaining else timeout_seconds
    deadline_limited = remaining is not None and timeout < timeout_seconds
    command = ["git", *arguments]
    # File-backed stdio avoids the unbounded Windows pipe-drain branch in run().
    with (
        tempfile.TemporaryFile() as stdout,
        tempfile.TemporaryFile() as stderr,
        tempfile.TemporaryFile() as stdin,
    ):
        if input is not None:
            stdin.write(input)
            stdin.seek(0)
        process = subprocess.Popen(
            command, cwd=workspace, env=env, stdin=stdin, stdout=stdout, stderr=stderr,
        )
        try:
            process.wait(timeout=timeout)
        except BaseException as exc:
            reaped = False
            try:
                process.kill()
                cleanup_timeout = (
                    min(cleanup_reserve, deadline.remaining_seconds())
                    if deadline is not None else cleanup_reserve
                )
                if cleanup_timeout > 0:
                    process.wait(timeout=cleanup_timeout)
                    reaped = True
            except BaseException:
                pass
            raise GitExecutionUncertain(
                "Git execution interrupted; descendant cleanup is not established",
                details={
                    "git_execution_uncertain": True,
                    "deadline_exhausted": (
                        isinstance(exc, subprocess.TimeoutExpired) and deadline_limited
                    ) or (
                        deadline is not None and deadline.remaining_seconds() <= 0
                    ),
                    "effective_timeout_seconds": timeout,
                    "direct_process_reaped": reaped,
                    "descendant_cleanup": "unknown",
                    "cause_type": type(exc).__name__,
                },
            ) from None
        if deadline is not None:
            deadline.check()
        stdout.seek(0)
        stderr.seek(0)
        captured_stdout = stdout.read()
        captured_stderr = stderr.read()
    if text:
        captured_stdout = captured_stdout.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        captured_stderr = captured_stderr.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    result = subprocess.CompletedProcess(
        command, process.returncode, captured_stdout, captured_stderr,
    )
    if check and result.returncode:
        detail = captured_stderr if text else captured_stderr.decode("utf-8", errors="replace")
        raise ContractError(f"Git operation failed: {detail.strip()}")
    return result
