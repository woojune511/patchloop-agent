"""Trusted PID-1 wrapper for bounded agent-authored Python probes."""

from __future__ import annotations

import ctypes
import errno
import os
import platform
import runpy
import signal
import sys
import time
import traceback
from contextlib import suppress

TIMEOUT_EXIT_CODE = 124
CHILD_RESERVED_EXIT_CODE = 125
INPUT_TIMEOUT_SECONDS = 5
_PR_SET_NO_NEW_PRIVS = 38
_PR_SET_SECCOMP = 22
_SECCOMP_MODE_FILTER = 2
_SECCOMP_RET_ERRNO = 0x00050000
_SECCOMP_RET_ALLOW = 0x7FFF0000
_BPF_LD_W_ABS = 0x20
_BPF_JMP_JEQ_K = 0x15
_BPF_JMP_JGE_K = 0x35
_BPF_JMP_JSET_K = 0x45
_BPF_ALU_AND_K = 0x54
_BPF_RET_K = 0x06
# Require a single process sharing VM, filesystem state, file descriptors, signal
# handlers and SysV semaphores. Only pthread TLS/TID bookkeeping is optional.
_THREAD_REQUIRED_FLAGS = 0x00050F00
_THREAD_ALLOWED_FLAGS = _THREAD_REQUIRED_FLAGS | 0x00080000 | 0x00100000 | 0x00200000 | 0x01000000


class _InputTimeout(Exception):
    pass


class _SockFilter(ctypes.Structure):
    _fields_ = [
        ("code", ctypes.c_ushort),
        ("jt", ctypes.c_ubyte),
        ("jf", ctypes.c_ubyte),
        ("k", ctypes.c_uint32),
    ]


class _SockFprog(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_ushort),
        ("filter", ctypes.POINTER(_SockFilter)),
    ]


def _input_timeout(_signum: int, _frame: object) -> None:
    raise _InputTimeout


def _read_source() -> bytes:
    signal.signal(signal.SIGALRM, _input_timeout)
    signal.setitimer(signal.ITIMER_REAL, INPUT_TIMEOUT_SECONDS)
    try:
        source = sys.stdin.buffer.read(32_001)
        if len(source) > 32_000:
            raise ValueError("probe source exceeds 32000 bytes")
        return source
    except _InputTimeout:
        os.write(
            sys.stderr.fileno(),
            b"[patchloop] probe input did not close within 5 seconds\n",
        )
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def _denied_syscalls() -> tuple[int, ...]:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return (
            57,   # fork
            58,   # vfork
            59,   # execve
            62,   # kill
            101,  # ptrace
            129,  # rt_sigqueueinfo
            200,  # tkill
            234,  # tgkill
            297,  # rt_tgsigqueueinfo
            310,  # process_vm_readv
            311,  # process_vm_writev
            322,  # execveat
            424,  # pidfd_send_signal
        )
    if machine in {"aarch64", "arm64"}:
        return (
            117,  # ptrace
            129,  # kill
            130,  # tkill
            131,  # tgkill
            138,  # rt_sigqueueinfo
            221,  # execve
            240,  # rt_tgsigqueueinfo
            270,  # process_vm_readv
            271,  # process_vm_writev
            281,  # execveat
            424,  # pidfd_send_signal
        )
    raise RuntimeError(f"unsupported probe architecture: {machine}")


def _install_process_boundary() -> None:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        audit_arch = 0xC000003E
        clone_number = 56
    elif machine in {"aarch64", "arm64"}:
        audit_arch = 0xC00000B7
        clone_number = 220
    else:
        raise RuntimeError(f"unsupported probe architecture: {machine}")
    # seccomp syscall numbers only have meaning within their declared ABI.
    # Reject alternate audit architectures and the x32 syscall-number bit.
    instructions = [
        _SockFilter(_BPF_LD_W_ABS, 0, 0, 4),
        _SockFilter(_BPF_JMP_JEQ_K, 1, 0, audit_arch),
        _SockFilter(_BPF_RET_K, 0, 0, _SECCOMP_RET_ERRNO | errno.EPERM),
        _SockFilter(_BPF_LD_W_ABS, 0, 0, 0),
        _SockFilter(_BPF_JMP_JGE_K, 0, 1, 0x40000000),
        _SockFilter(_BPF_RET_K, 0, 0, _SECCOMP_RET_ERRNO | errno.EPERM),
        # Both supported ABIs put clone flags in args[0], little-endian. Check
        # both words and reject exit signals, namespaces and all unknown flags.
        # A non-clone syscall skips the ten-instruction flags branch unchanged.
        _SockFilter(_BPF_JMP_JEQ_K, 0, 10, clone_number),
        _SockFilter(_BPF_LD_W_ABS, 0, 0, 20),
        _SockFilter(_BPF_JMP_JEQ_K, 1, 0, 0),
        _SockFilter(_BPF_RET_K, 0, 0, _SECCOMP_RET_ERRNO | errno.EPERM),
        _SockFilter(_BPF_LD_W_ABS, 0, 0, 16),
        _SockFilter(_BPF_JMP_JSET_K, 0, 1, ~_THREAD_ALLOWED_FLAGS & 0xFFFFFFFF),
        _SockFilter(_BPF_RET_K, 0, 0, _SECCOMP_RET_ERRNO | errno.EPERM),
        _SockFilter(_BPF_ALU_AND_K, 0, 0, _THREAD_REQUIRED_FLAGS),
        _SockFilter(_BPF_JMP_JEQ_K, 1, 0, _THREAD_REQUIRED_FLAGS),
        _SockFilter(_BPF_RET_K, 0, 0, _SECCOMP_RET_ERRNO | errno.EPERM),
        _SockFilter(_BPF_RET_K, 0, 0, _SECCOMP_RET_ALLOW),
        # Classic seccomp cannot inspect clone3's pointed-to argument struct.
        # ENOSYS keeps it disabled while allowing libc's checked clone fallback.
        _SockFilter(_BPF_JMP_JEQ_K, 0, 1, 435),
        _SockFilter(_BPF_RET_K, 0, 0, _SECCOMP_RET_ERRNO | errno.ENOSYS),
    ]
    for syscall_number in _denied_syscalls():
        instructions.extend(
            [
                _SockFilter(
                    _BPF_JMP_JEQ_K,
                    0,
                    1,
                    syscall_number,
                ),
                _SockFilter(
                    _BPF_RET_K,
                    0,
                    0,
                    _SECCOMP_RET_ERRNO | errno.EPERM,
                ),
            ]
        )
    instructions.append(
        _SockFilter(_BPF_RET_K, 0, 0, _SECCOMP_RET_ALLOW)
    )
    filters = (_SockFilter * len(instructions))(*instructions)
    program = _SockFprog(len(instructions), filters)
    libc = ctypes.CDLL(None, use_errno=True)
    prctl = libc.prctl
    prctl.restype = ctypes.c_int
    if prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    if (
        prctl(
            _PR_SET_SECCOMP,
            _SECCOMP_MODE_FILTER,
            ctypes.byref(program),
        )
        != 0
    ):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def _child_exit_code(code: object) -> int:
    if code is None:
        return 0
    if isinstance(code, int):
        return code % 256
    print(code, file=sys.stderr)
    return 1


def _flush_child_output(
    stdout: object,
    stderr: object,
) -> None:
    for stream in (stdout, stderr):
        flush = getattr(stream, "flush", None)
        if flush is not None:
            with suppress(BaseException):
                flush()


def _execute_child(code: object, collector=None, import_paths=None, setup=None) -> None:
    stdout = sys.stdout
    stderr = sys.stderr
    try:
        os.setsid()
        _install_process_boundary()
        # Trusted imports above finish before public source becomes importable.
        # Work happens in ephemeral /tmp; the public snapshot is read-only.
        sys.dont_write_bytecode = True
        # Plain paths, never site.addsitedir: dependency .pth/startup hooks are not run.
        sys.path[:0] = import_paths or ["/workspace"]
        namespace = {
            "__name__": "__main__",
            "__file__": "<patchloop-probe>",
        }
        if setup is not None:
            namespace["check_setup"] = setup.check
        if collector is not None:
            collector.start()
        try:
            exec(code, namespace, namespace)
        finally:
            try:
                if collector is not None:
                    collector.finish()
            finally:
                if setup is not None:
                    setup.finish()
    except SystemExit as exc:
        exit_code = _child_exit_code(exc.code)
        _flush_child_output(stdout, stderr)
        os._exit(exit_code)
    except BaseException:
        traceback.print_exc(file=stderr)
        _flush_child_output(stdout, stderr)
        os._exit(1)
    _flush_child_output(stdout, stderr)
    os._exit(0)


def _wait_for_child(child_pid: int, timeout_seconds: int) -> int:
    deadline = time.monotonic() + timeout_seconds
    while True:
        waited_pid, status = os.waitpid(child_pid, os.WNOHANG)
        if waited_pid == child_pid:
            if os.WIFEXITED(status):
                exit_code = os.WEXITSTATUS(status)
                return (
                    CHILD_RESERVED_EXIT_CODE
                    if exit_code == TIMEOUT_EXIT_CODE
                    else exit_code
                )
            if os.WIFSIGNALED(status):
                return min(255, 128 + os.WTERMSIG(status))
            return CHILD_RESERVED_EXIT_CODE
        if time.monotonic() >= deadline:
            with suppress(ProcessLookupError):
                os.killpg(child_pid, signal.SIGKILL)
            with suppress(ProcessLookupError):
                os.kill(child_pid, signal.SIGKILL)
            os.waitpid(child_pid, 0)
            os.write(
                sys.stderr.fileno(),
                (
                    "[patchloop] probe exceeded its "
                    f"{timeout_seconds}-second execution timeout\n"
                ).encode("ascii"),
            )
            return TIMEOUT_EXIT_CODE
        time.sleep(0.01)


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        return 2
    try:
        timeout_seconds = int(sys.argv[1])
    except ValueError:
        return 2
    if not 1 <= timeout_seconds <= 60:
        return 2
    try:
        source = _read_source().decode("utf-8")
    except (_InputTimeout, UnicodeDecodeError, ValueError):
        return TIMEOUT_EXIT_CODE
    try:
        code = compile(source, "<patchloop-probe>", "exec")
    except (SyntaxError, ValueError):
        traceback.print_exc()
        return 1

    import json
    from pathlib import Path

    configuration = Path(__file__).with_name("dependencies.json")
    import_paths = json.loads(configuration.read_bytes())["import_paths"] if (
        configuration.is_file()) else None
    setup_module = runpy.run_path(str(Path(__file__).with_name("probe_setup.py")))
    setup = setup_module["SetupChecks"](
        json.loads(Path(__file__).with_name("setup_request.json").read_bytes()),
    )
    collector = None
    if len(sys.argv) == 3:
        # Load only the host-copied stdlib collector before exposing project imports.
        module = runpy.run_path(str(Path(__file__).with_name("line_trace.py")))
        collector = module["LineTrace"](json.loads(Path(sys.argv[2]).read_bytes()), "/workspace")

    try:
        child_pid = os.fork()
    except OSError:
        traceback.print_exc()
        return CHILD_RESERVED_EXIT_CODE
    if child_pid == 0:
        _execute_child(code, collector, import_paths, setup)
    return _wait_for_child(child_pid, timeout_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
