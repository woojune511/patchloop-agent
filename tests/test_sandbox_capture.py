from __future__ import annotations

import io
import json
import subprocess
import sys
import threading
import time

import pytest

from patchloop.contracts import RegisteredCheck
from patchloop.deadline import ExecutionDeadline
from patchloop.sandbox import capture as capture_module
from patchloop.sandbox import runner
from patchloop.sandbox.capture import (
    CapturedProcess,
    OutputCollector,
    SandboxCleanupError,
    capture_process,
)
from patchloop.sandbox.execution_feedback import MAX_REPORT_BYTES, make_request
from patchloop.sandbox.line_trace import marker
from patchloop.util import sha256_bytes, sha256_json


def fake_capture(run):
    """Adapt an existing deterministic launch double at the new capture boundary."""

    def capture(command, *, timeout, output_limit_bytes, execution_targets=None,
                deadline=None, cleanup=None, **kwargs):
        cleanup_ok = True
        try:
            try:
                result = run(command, timeout=timeout, **kwargs)
                exit_code, stdout, stderr, timed_out = (
                    result.returncode, result.stdout, result.stderr, False,
                )
            except subprocess.TimeoutExpired as exc:
                exit_code, stdout, stderr, timed_out = (
                    None, exc.stdout or b"", exc.stderr or b"", True,
                )
        finally:
            if cleanup is not None:
                cleanup_ok = cleanup(min(5.0, deadline.remaining_seconds() if deadline else 5.0))
        collector = OutputCollector(output_limit_bytes, execution_targets)
        collector.drain(io.BytesIO(stdout), "stdout")
        collector.drain(io.BytesIO(stderr), "stderr")
        stdout_text, stderr_text, truncated, original = collector.public_text()
        return CapturedProcess(
            exit_code, timed_out, stdout_text, stderr_text, truncated, original,
            collector.report, not cleanup_ok,
        )

    return capture


def test_registered_check_does_not_capture_complete_output_with_subprocess_run(
    tmp_path, monkeypatch,
):
    def unbounded(*args, **kwargs):
        pytest.fail("registered check still uses whole-output subprocess.run capture")

    monkeypatch.setattr(runner.subprocess, "run", unbounded)
    result = runner.LocalSandbox().run_check(
        tmp_path, RegisteredCheck(id="small", command=["python", "-c", "print('ok')"]),
    )
    assert result.passed and result.stdout.splitlines() == ["ok"]


def test_large_synthetic_chunks_keep_bounded_prefixes_without_stopping_drain():
    collector = OutputCollector(128)
    block = b"a" * 4_095 + b"\n"
    for _ in range(10_000):
        collector.feed(block, "stderr")
        collector.feed(block, "stdout")
        assert sum(map(len, collector.streams.values())) <= 256
    assert collector.observed == {"stdout": 40_960_000, "stderr": 40_960_000}
    assert collector.public_text() == ("", "", True, 81_920_000)
    assert not collector.failed.is_set()


@pytest.mark.parametrize("stdout,stderr,cap", [
    (b"ok\r\npartial", b"stderr\n", 7),
    ("가나다\n".encode(), "바\n".encode(), 7),
    (b"a", b"b", 2),
    (b"a\n", b"last unterminated line", 6),
    (b"stdout without newline", b"err\n", 5),
    (b"", b"eof without newline", 100),
])
def test_streaming_retains_existing_byte_line_and_stdout_priority_semantics(stdout, stderr, cap):
    collector = OutputCollector(cap)
    # Stderr may arrive first; it never wins a race for stdout's eventual quota.
    for stream, name in ((stderr, "stderr"), (stdout, "stdout")):
        for offset in range(0, len(stream), 3):
            collector.feed(stream[offset:offset + 3], name)
    assert collector.public_text() == runner._bounded_text(stdout, stderr, cap)


def _targets():
    return make_request(
        sha256_bytes(b"public diff"), [], execution_identity=None,
        omitted_file_count=0, deleted_line_count=0,
    )


@pytest.mark.parametrize("frame_kind", ["valid", "oversized", "duplicate", "malformed"])
def test_report_channel_survives_large_public_stderr_without_spending_its_quota(frame_kind):
    targets = _targets()
    payload = {"request_hash": targets["request_hash"], "files": []}
    body = json.dumps(payload).encode()
    if frame_kind == "oversized":
        body = b"x" * (MAX_REPORT_BYTES + 1)
    elif frame_kind == "malformed":
        body = b"{invalid json}"
    frame = marker(targets) + body + b"\n"
    if frame_kind == "duplicate":
        frame += frame
    collector = OutputCollector(32, targets)
    public = b"public\n" * 10_000
    collector.drain(io.BytesIO(public + frame), "stderr")
    assert collector.observed["stderr"] == len(public)
    assert collector.public_text() == ("", "public\n" * 4, True, len(public))
    assert collector.report == (payload if frame_kind == "valid" else None)
    assert len(collector.streams["stderr"]) == 32
    assert not collector.failed.is_set()


@pytest.mark.parametrize("exit_code", [0, 1])
def test_real_local_large_output_retains_exit_verdict_and_exact_observed_bytes(tmp_path, exit_code):
    check = RegisteredCheck(
        id="harmless-large-output", output_limit_bytes=4_096,
        command=[sys.executable, "-c", (
            "import os,sys\n"
            "for _ in range(64):\n"
            " os.write(1,b'a'*4095+b'\\n'); os.write(2,b'err\\n'*1024)\n"
            f"sys.exit({exit_code})"
        )],
    )
    result = runner.LocalSandbox().run_check(tmp_path, check)
    assert result.exit_code == exit_code
    assert result.passed is (exit_code == 0)
    assert result.stdout == "a" * 4_095 + "\n" and result.stderr == ""
    assert result.original_output_bytes == 2 * 64 * 4_096
    assert result.truncated and not result.timed_out


def test_real_local_timeout_retains_partial_output_and_leaves_no_readers(tmp_path):
    before = {thread.ident for thread in threading.enumerate()}
    started = time.monotonic()
    result = capture_process(
        [sys.executable, "-c", "import time; print('partial',flush=True); time.sleep(30)"],
        cwd=tmp_path, timeout=0.3, output_limit_bytes=128,
        deadline=ExecutionDeadline.from_remaining(3),
    )
    assert result.timed_out and result.exit_code is None
    assert result.stdout.splitlines() == ["partial"] and not result.cleanup_failed
    assert time.monotonic() - started < 3
    assert not [thread for thread in threading.enumerate()
                if thread.ident not in before and thread.name.startswith("check-")]


class FakeProcess:
    def __init__(self, *, error=None, stdout=None):
        self.stdout = io.BytesIO(b"ok\n") if stdout is None else stdout
        self.stderr = io.BytesIO()
        self.returncode = None if error else 0
        self.error = error
        self.killed = False
        self.waits = []

    def poll(self):
        return self.returncode

    def wait(self, timeout):
        self.waits.append(timeout)
        if self.error and not self.killed:
            raise self.error
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9


@pytest.mark.parametrize("error_type", [OSError, RuntimeError, KeyboardInterrupt])
@pytest.mark.parametrize("cleanup_ok", [True, False])
def test_interruption_reaps_launcher_and_preserves_cleanup_uncertainty(
    monkeypatch, error_type, cleanup_ok,
):
    error = error_type("synthetic wait interruption")
    process = FakeProcess(error=error)
    calls = []
    monkeypatch.setattr(capture_module.subprocess, "Popen", lambda *args, **kwargs: process)

    def cleanup(seconds):
        assert process.killed
        assert 0 < seconds <= 5
        calls.append(seconds)
        return cleanup_ok

    with pytest.raises(error_type if cleanup_ok else SandboxCleanupError) as caught:
        capture_process(["synthetic"], timeout=3, output_limit_bytes=128, cleanup=cleanup)
    assert len(calls) == 1 and process.stdout.closed and process.stderr.closed
    if cleanup_ok:
        assert caught.value is error
    else:
        assert caught.value.details["cleanup_failed"] is True
        assert caught.value.__cause__ is error


@pytest.mark.parametrize("failure", ["read", "close", "reap"])
def test_pipe_and_process_failures_do_not_become_semantic_check_results(monkeypatch, failure):
    class BrokenPipe(io.BytesIO):
        def read(self, size):
            if failure == "read":
                raise OSError("synthetic read error")
            return super().read(size)

        def close(self):
            super().close()
            if failure == "close":
                raise OSError("synthetic close error")

    process = FakeProcess(stdout=BrokenPipe(b"public\n"))
    if failure == "reap":
        process.wait = lambda timeout: (_ for _ in ()).throw(OSError("synthetic reap error"))
    monkeypatch.setattr(capture_module.subprocess, "Popen", lambda *args, **kwargs: process)
    with pytest.raises(SandboxCleanupError) as caught:
        capture_process(["synthetic"], timeout=1, output_limit_bytes=128)
    assert caught.value.details["cleanup_failed"] is True
    assert caught.value.details["capture_errors"]


def test_unjoined_reader_is_bounded_uncertainty_not_an_infinite_teardown(monkeypatch):
    release = threading.Event()

    class BlockedPipe(io.BytesIO):
        def read(self, size):
            release.wait(2)
            return b""

    process = FakeProcess(stdout=BlockedPipe())
    monkeypatch.setattr(capture_module.subprocess, "Popen", lambda *args, **kwargs: process)
    started = time.monotonic()
    try:
        with pytest.raises(SandboxCleanupError) as caught:
            capture_process(
                ["synthetic"], timeout=1, output_limit_bytes=128,
                deadline=ExecutionDeadline.from_remaining(0.1),
            )
        assert "reader_not_joined" in caught.value.details["capture_errors"]
        assert time.monotonic() - started < 0.8
    finally:
        release.set()
        for thread in threading.enumerate():
            if thread.name.startswith("check-"):
                thread.join(timeout=1)
    assert process.stdout.closed and process.stderr.closed


def test_docker_capture_resource_error_keeps_policy_hash_and_stronger_cleanup_failure(
    tmp_path, monkeypatch,
):
    class BrokenPipe(io.BytesIO):
        def read(self, size):
            raise OSError("synthetic capture read failure")

    process = FakeProcess(stdout=BrokenPipe())
    monkeypatch.setattr(capture_module.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(runner.DockerSandbox, "cli_path", staticmethod(lambda: "fake-docker"))

    def inspected_absent(command, **kwargs):
        assert command[1:3] == ["container", "inspect"]
        return subprocess.CompletedProcess(
            command, 1, b"", b"No such container: " + command[-1].encode(),
        )

    monkeypatch.setattr(runner.subprocess, "run", inspected_absent)
    with pytest.raises(SandboxCleanupError) as caught:
        runner.DockerSandbox("test@sha256:" + "a" * 64).run_check(
            tmp_path, RegisteredCheck(id="public", command=["python", "-c", "pass"]),
        )
    details = caught.value.details
    assert details["cleanup_failed"] is True
    assert details["capture_errors"] == ["OSError"]
    assert details["execution_policy"]["cleanup_status"] == "failed"
    assert details["execution_policy_hash"] == sha256_json(details["execution_policy"])


@pytest.mark.parametrize("operation", ["available", "image_identity"])
def test_docker_preflight_receives_remaining_active_deadline(monkeypatch, operation):
    clock = [0.0]
    deadline = ExecutionDeadline.from_remaining(0.5, clock=lambda: clock[0])
    monkeypatch.setattr(runner.DockerSandbox, "cli_path", staticmethod(lambda: "fake-docker"))

    def inspect(command, **kwargs):
        assert kwargs["timeout"] == 0.5
        clock[0] = 0.5
        return subprocess.CompletedProcess(command, 0, b"unknown", b"")

    monkeypatch.setattr(runner.subprocess, "run", inspect)
    from patchloop.deadline import ExecutionDeadlineExceeded

    with pytest.raises(ExecutionDeadlineExceeded):
        getattr(runner.DockerSandbox("test@sha256:" + "a" * 64), operation)(deadline=deadline)
