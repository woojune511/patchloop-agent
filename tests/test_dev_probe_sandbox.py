from __future__ import annotations

import errno
import io
import runpy
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from patchloop.deadline import ExecutionDeadline
from patchloop.errors import ContractError
from patchloop.sandbox import probes
from patchloop.util import sha256_bytes, sha256_json


@pytest.fixture
def public_repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
    (root / "module.py").write_text("VALUE = 1\n")
    (root / "private.py").write_bytes(b"PUBLIC_HELPER = True\n")
    (root / ".env").write_text("CREDENTIAL_SENTINEL")
    (root / ".patchloop-hidden").mkdir()
    (root / ".patchloop-hidden" / "test_private.py").write_text("HIDDEN_SENTINEL")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True)
    (root / "untracked.py").write_text("UNTRACKED_SENTINEL")
    (root / "module.py").write_bytes(b"VALUE = 2\n")
    return root


class FakeProcess:
    def __init__(self, stdout=b"ok\n", stderr=b"", running=False):
        self.stdin = io.BytesIO()
        self.stdout = io.BytesIO(stdout)
        self.stderr = io.BytesIO(stderr)
        self.returncode = None if running else 0
        self.killed = False

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout):
        return self.returncode


def backend(monkeypatch):
    sandbox = probes.DockerProbeSandbox()
    monkeypatch.setattr(
        probes.DockerSandbox, "image_identity", lambda self, **kwargs: probes.PROBE_IMAGE_DIGEST
    )
    monkeypatch.setattr(probes.DockerSandbox, "cli_path", lambda: "docker")
    sandbox.preflight()
    monkeypatch.setattr(sandbox, "_cleanup", lambda *args: True)
    return sandbox


def mock_launch(monkeypatch, launch):
    original = subprocess.Popen

    def dispatch(command, **kwargs):
        return launch(command, **kwargs) if command[0] == "docker" else original(command, **kwargs)

    monkeypatch.setattr(probes.subprocess, "Popen", dispatch)


def test_probe_preflight_requires_exact_reviewed_image(monkeypatch):
    with pytest.raises(ContractError, match="reviewed"):
        probes.DockerProbeSandbox("private-evaluator@sha256:" + "f" * 64)
    monkeypatch.setattr(probes.DockerSandbox, "image_identity", lambda self, **kwargs: None)
    with pytest.raises(ContractError, match="not available"):
        probes.DockerProbeSandbox().preflight()


def test_probe_rejects_wrapper_drift_after_preflight(monkeypatch, public_repo, tmp_path):
    wrapper = tmp_path / "probe_runner.py"
    wrapper.write_bytes(probes._WRAPPER.read_bytes())
    monkeypatch.setattr(probes, "_WRAPPER", wrapper)
    sandbox = backend(monkeypatch)
    original_identity = sandbox.identity
    wrapper.write_bytes(wrapper.read_bytes() + b"\n# unexpected change\n")
    monkeypatch.setattr(probes.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("launched"))
    with pytest.raises(ContractError, match="changed after preflight"):
        sandbox.run_probe(public_repo, "observe", "print(1)", deadline=None,
                          execution_identity={"run_id": "r", "action_id": "a"})
    assert sandbox.identity == original_identity


def test_snapshot_uses_current_tracked_public_bytes(public_repo, tmp_path):
    exported = tmp_path / "exported"
    exported.mkdir()
    digest = probes._snapshot(public_repo, exported, None)
    assert (exported / "module.py").read_text() == "VALUE = 2\n"
    assert (exported / "private.py").is_file()
    assert sorted(path.name for path in exported.iterdir()) == ["module.py", "private.py"]
    assert digest == sha256_json([
        {"path": "module.py", "content_hash": sha256_bytes(b"VALUE = 2\n")},
        {"path": "private.py", "content_hash": sha256_bytes(b"PUBLIC_HELPER = True\n")},
    ])


def test_snapshot_rejects_tracked_symlinks_before_read(monkeypatch, tmp_path):
    monkeypatch.setattr(probes.subprocess, "run", lambda *args, **kwargs:
                        subprocess.CompletedProcess([], 0, b"120000 abc 0\tlink.py\0", b""))
    with pytest.raises(ContractError, match="regular"):
        probes._snapshot(tmp_path, tmp_path / "exported", None)


def test_probe_runs_snapshot_with_fixed_policy_and_no_worktree_write(monkeypatch, public_repo):
    sandbox = backend(monkeypatch)
    commands = []
    mounts = []
    before = (public_repo / "module.py").read_bytes()

    def launch(command, **kwargs):
        commands.append(command)
        assert "capture_output" not in kwargs
        assert kwargs["bufsize"] == 0
        assert "SECRET_API_KEY" not in kwargs["env"]
        mounts.extend(item for item in command if item.startswith("type=bind"))
        source = next(item for item in mounts if "target=/workspace," in item)
        directory = Path(source.split("source=", 1)[1].split(",target=")[0])
        assert directory != public_repo
        assert not (directory / ".git").exists()
        assert not (directory / ".env").exists()
        assert (directory / "module.py").read_bytes() == before
        return FakeProcess()

    monkeypatch.setenv("SECRET_API_KEY", "never inherited")
    mock_launch(monkeypatch, launch)
    result = sandbox.run_probe(public_repo, "observe value", "print(2)", deadline=None,
                               execution_identity={"run_id": "run1", "action_id": "a1"})
    assert result["status"] == "passed"
    assert result["stdout"] == "ok\n"
    assert result["snapshot_hash"]
    assert result["execution_policy_hash"] == sha256_json(result["execution_policy"])
    assert result["execution_policy"]["version"] == "docker-python-probe-v2"
    assert result["execution_policy"]["thread_policy"] == "same-process-pthreads-only-v1"
    assert result["execution_policy"]["pids_limit"] == 8
    command = commands[0]
    for flag, value in (("--network", "none"), ("--user", "10001:10001"),
                        ("--pull", "never"), ("--pids-limit", "8"),
                        ("--cap-drop", "ALL"), ("--entrypoint", "/usr/local/bin/python")):
        assert command[command.index(flag) + 1] == value
    assert "--read-only" in command
    assert len(mounts) == 2 and all(item.endswith(",readonly") for item in mounts)
    assert (public_repo / "module.py").read_bytes() == before
    assert not list(public_repo.glob("*probe*"))


def test_output_flood_is_bounded_and_kills_owned_process(monkeypatch, public_repo):
    sandbox = backend(monkeypatch)
    process = FakeProcess(b"x" * 1_000_000, running=True)
    mock_launch(monkeypatch, lambda *args, **kwargs: process)
    result = sandbox.run_probe(public_repo, "flood", "print('x')", deadline=None,
                               execution_identity={"run_id": "run1", "action_id": "a2"})
    assert result["status"] == "output_limit"
    assert result["captured_output_bytes"] == 12000
    assert len(result["stdout"].encode()) == 12000
    assert result["observed_output_bytes"] == 1_000_000
    assert process.killed


def test_output_limit_keeps_real_pipes_drained_without_retaining_extra_bytes():
    collector = probes._OutputCollector()
    process = subprocess.Popen(
        [sys.executable, "-I", "-u", "-c",
         "import sys; "
         "sys.stdout.buffer.write(b'x' * 524288); sys.stdout.flush(); "
         "sys.stderr.buffer.write(b'y' * 524288); sys.stderr.flush()"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0,
    )
    assert process.stdout is not None and process.stderr is not None
    readers = [
        threading.Thread(target=collector.drain, args=(stream, label), daemon=True)
        for stream, label in ((process.stdout, "stdout"), (process.stderr, "stderr"))
    ]
    for reader in readers:
        reader.start()
    try:
        # Returning from a reader at the cap fills the OS pipe and strands the
        # writer. Continued discard permits exit while retained memory stays fixed.
        process.wait(timeout=2)
        for reader in readers:
            reader.join(timeout=1)
        assert process.returncode == 0
        assert not any(reader.is_alive() for reader in readers)
        assert collector.limit_hit.is_set()
        assert collector.observed == 1_048_576
        assert sum(len(value) for value in collector.streams.values()) == 12000
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=1)
        for reader in readers:
            reader.join(timeout=1)
        process.stdout.close()
        process.stderr.close()


def test_invalid_utf8_cannot_expand_public_output_beyond_limit():
    collector = probes._OutputCollector()
    collector.drain(io.BytesIO(b"\xff" * 6000), "stdout")
    collector.drain(io.BytesIO(b"\xfe" * 6000), "stderr")
    stdout, stderr = collector.public_text()
    assert len(stdout.encode()) + len(stderr.encode()) <= 12000
    assert sum(len(value) for value in collector.streams.values()) == 12000


@pytest.mark.parametrize("machine,arch", [("x86_64", 0xC000003E), ("aarch64", 0xC00000B7)])
def test_trusted_wrapper_filter_rejects_process_and_alternate_abi(monkeypatch, machine, arch):
    wrapper = runpy.run_path(str(probes._WRAPPER))
    monkeypatch.setattr(wrapper["platform"], "machine", lambda: machine)
    instructions = []

    class Libc:
        def __init__(self):
            def prctl(option, *args):
                if option == wrapper["_PR_SET_SECCOMP"]:
                    program = args[1]._obj
                    instructions.extend(
                        (item.code, item.jt, item.jf, item.k)
                        for item in program.filter[:program.length]
                    )
                return 0
            self.prctl = prctl

    monkeypatch.setattr(wrapper["ctypes"], "CDLL", lambda *args, **kwargs: Libc())
    wrapper["_install_process_boundary"]()

    def verdict(syscall, audit_arch, clone_flags=0):
        offset = 0
        accumulator = 0
        while True:
            code, jt, jf, value = instructions[offset]
            if code == 0x20:
                accumulator = {0: syscall, 4: audit_arch, 16: clone_flags & 0xFFFFFFFF,
                               20: clone_flags >> 32}[value]
            elif code == 0x15:
                offset += jt if accumulator == value else jf
            elif code == 0x35:
                offset += jt if accumulator >= value else jf
            elif code == 0x45:
                offset += jt if accumulator & value else jf
            elif code == 0x54:
                accumulator &= value
            else:
                assert code == 0x06
                return value
            offset += 1

    allowed = wrapper["_SECCOMP_RET_ALLOW"]
    for syscall in wrapper["_denied_syscalls"]():
        assert verdict(syscall, arch) != allowed
    assert verdict(0, arch) == allowed
    assert verdict(0, 0x40000003) != allowed
    assert verdict(0x40000000, arch) != allowed
    clone_nr = 56 if machine == "x86_64" else 220
    pthread_flags = 0x3D0F00
    assert verdict(clone_nr, arch, pthread_flags) == allowed
    assert verdict(clone_nr, arch, pthread_flags | 0x01000000) == allowed  # CHILD_SETTID
    for required in (0x100, 0x200, 0x400, 0x800, 0x10000, 0x40000):
        assert verdict(clone_nr, arch, pthread_flags & ~required) != allowed
    # Signals, namespace creation, unknown flags and the upper word cannot bypass
    # the thread-only path, even when all required pthread sharing bits are set.
    permitted = pthread_flags | 0x01000000
    for bit in range(64):
        if not permitted & (1 << bit):
            assert verdict(clone_nr, arch, pthread_flags | (1 << bit)) != allowed
    assert verdict(clone_nr, arch, 17) != allowed  # fork-like SIGCHLD clone
    assert verdict(435, arch, pthread_flags) == wrapper["_SECCOMP_RET_ERRNO"] | errno.ENOSYS


def test_cleanup_checks_exact_owned_label_and_never_removes_other_container(monkeypatch):
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, b"other-owner\n", b"")

    monkeypatch.setattr(probes.subprocess, "run", run)
    assert not probes.DockerProbeSandbox._cleanup("docker", "patchloop-probe-own", None)
    assert len(commands) == 1 and commands[0][1:3] == ["container", "inspect"]


def test_uncertain_pending_cleanup_prevents_new_execution(monkeypatch, public_repo):
    sandbox = backend(monkeypatch)
    monkeypatch.setattr(sandbox, "_cleanup", lambda *args: False)
    monkeypatch.setattr(probes.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("launched"))
    result = sandbox.run_probe(public_repo, "observe", "print(1)", deadline=None,
                               execution_identity={"run_id": "run1", "action_id": "a2"})
    assert result["status"] == "cleanup_failed"
    assert result["cleanup_failed"]
    assert result["snapshot_hash"] is None
    assert result["execution_policy"]["cleanup_status"] == "failed"


def test_shared_deadline_limits_probe_and_preserves_cleanup_reserve(monkeypatch, public_repo):
    sandbox = backend(monkeypatch)
    elapsed = [0.0]
    deadline = ExecutionDeadline.from_remaining(8, clock=lambda: elapsed[0])

    class TimedProcess(FakeProcess):
        def poll(self):
            elapsed[0] += 0.6
            return super().poll()

    process = TimedProcess(running=True)
    monkeypatch.setattr(probes.time, "monotonic", lambda: elapsed[0])
    mock_launch(monkeypatch, lambda *args, **kwargs: process)
    result = sandbox.run_probe(public_repo, "loop", "while True: pass", deadline=deadline,
                               execution_identity={"run_id": "run1", "action_id": "a3"})
    assert result["status"] == "timeout"
    assert result["deadline_exhausted"]
    assert result["execution_policy"]["effective_timeout_seconds"] == 3
    assert result["execution_policy"]["row_deadline_limited"]
    assert process.killed
