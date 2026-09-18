"""Explicit real-Docker diagnostics; never acquire images or start Docker Desktop.

Run only with PATCHLOOP_TEST_REAL_PROBES=1 and an external pytest --basetemp.
Each test executes a synthetic probe; the first also replays its durable result.
The SDK test additionally requires an existing public dependency descriptor.
"""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest

from patchloop.contracts import IssueSpec, PublicTask, RegisteredCheck, RepositorySpec
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.contracts import DevLimits, PublicTurnDecision, RequestedTool
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.prepared_probe_dependencies import PreparedDependencies, read_descriptor
from patchloop.runtime import repository_root
from patchloop.sandbox.probes import PROBE_IMAGE_DIGEST, DockerProbeSandbox
from patchloop.sandbox.runner import DockerSandbox
from patchloop.util import sha256_bytes, sha256_json

pytestmark = pytest.mark.skipif(
    os.environ.get("PATCHLOOP_TEST_REAL_PROBES") != "1",
    reason="real Docker probes require explicit PATCHLOOP_TEST_REAL_PROBES=1",
)


@dataclass
class _RealSession:
    backend: DockerProbeSandbox
    evidence_root: Path
    blocked: bool = False


@pytest.fixture(scope="module")
def real_probe_session(tmp_path_factory):
    evidence_root = tmp_path_factory.mktemp("real-probe-evidence").resolve()
    assert not evidence_root.is_relative_to(repository_root().resolve()), (
        "real probe evidence requires an external pytest --basetemp"
    )
    backend = DockerProbeSandbox()
    # Explicitly enabled missing-image/daemon/profile problems must fail visibly.
    # This method inspects only: it cannot pull/build images or start the daemon.
    identity = backend.preflight()
    (evidence_root / "preflight.json").write_text(
        json.dumps({"official": False, "provider_calls": 0, **identity}, indent=2),
        encoding="utf-8",
    )
    return _RealSession(backend, evidence_root)


def _git(root, *arguments):
    return subprocess.run(
        ["git", "-C", str(root), *arguments], capture_output=True,
        check=True, timeout=10, text=True,
    ).stdout.strip()


@pytest.fixture
def real_probe_gateway(tmp_path, real_probe_session):
    if real_probe_session.blocked:
        pytest.fail("further execution forbidden after uncertain cleanup")
    assert not tmp_path.resolve().is_relative_to(repository_root().resolve())
    workspace = tmp_path / "public-repo"
    workspace.mkdir()
    _git(workspace, "init")
    _git(workspace, "config", "core.autocrlf", "false")
    files = {
        "module.py": b"VALUE = 1\n",
        "helper.py": b"PUBLIC_HELPER = True\n",
        ".env": b"FAKE_CREDENTIAL_SENTINEL\n",
        ".env.local": b"FAKE_LOCAL_CREDENTIAL_SENTINEL\n",
        ".patchloop-hidden/test_private.py": b"FAKE_HIDDEN_SENTINEL\n",
    }
    for relative, body in files.items():
        path = workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    _git(workspace, "add", "--force", "--", ".")
    _git(
        workspace, "-c", "user.name=PatchLoop Probe Test",
        "-c", "user.email=probe-test@example.invalid", "commit", "-m", "Public probe fixture",
    )
    revision = _git(workspace, "rev-parse", "HEAD")
    (workspace / "module.py").write_bytes(b"VALUE = 2\n")
    (workspace / "untracked_secret.txt").write_bytes(b"FAKE_UNTRACKED_SENTINEL\n")
    public = PublicTask(
        task_id="probe-isolation-fixture", split="smoke",
        repository=RepositorySpec(url=str(workspace), base_commit=revision),
        issue=IssueSpec(title="Public probe fixture", description="Observe current public source."),
        visible_checks=[RegisteredCheck(
            id="required-visible", command=["python", "-c", "raise AssertionError"],
            timeout_seconds=10,
        )],
    )
    run_id = "run_dev_probevalidation_" + uuid.uuid4().hex[:16]
    journal = DevJournal(real_probe_session.evidence_root / "state", run_id)
    return DevToolGateway(
        workspace=workspace, public_task=public, sandbox=None, journal=journal,
        limits=DevLimits(), probe_sandbox=real_probe_session.backend,
    )


def _assert_no_container(session, identity):
    docker = DockerSandbox.cli_path()
    name = session.backend.container_name(identity)
    if docker is None:
        return False, "Docker CLI disappeared before cleanup verification"
    try:
        inspected = subprocess.run(
            [docker, "container", "inspect", name], capture_output=True,
            check=False, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, type(exc).__name__
    absent = bool(
        inspected.returncode
        and name.encode() in inspected.stderr
        and any(token in inspected.stderr for token in (b"No such container", b"No such object"))
    )
    return absent, inspected.stderr.decode("utf-8", errors="replace")[:1_000]


def _run(session, gateway, action_id, source, *, seconds=45):
    if session.blocked:
        pytest.fail("further execution forbidden after uncertain cleanup")
    source = textwrap.dedent(source).strip() + "\n"
    call = RequestedTool(
        name="run_probe", action_id=action_id,
        arguments={
            "question": f"Verify public probe boundary: {action_id}", "python_source": source,
        },
        turn_decision=PublicTurnDecision(
            mode="verify", basis="Verify the explicitly approved synthetic Docker probe boundary.",
        ),
    )
    identity = {"run_id": gateway.journal.run_id, "action_id": action_id}
    before_diff = gateway.current_diff_hash
    gateway.deadline = ExecutionDeadline.from_remaining(seconds)
    started = time.monotonic()
    result = gateway.execute(call)
    elapsed = time.monotonic() - started
    absent, inspection = _assert_no_container(session, identity)
    report = {
        "official": False, "provider_calls": 0, "run_id": gateway.journal.run_id,
        "action_id": action_id, "elapsed_seconds": elapsed,
        "journal_path": str(gateway.journal.path), "container_absent": absent,
        "cleanup_inspection": inspection, "result": result.model_dump(mode="json"),
    }
    (session.evidence_root / f"{action_id}.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8",
    )
    if result.output.get("cleanup_failed") or not absent:
        session.blocked = True
        pytest.exit("real probe cleanup uncertain; further executions stopped", returncode=1)
    assert result.status == "succeeded", result.message
    output = result.output
    assert output["execution_policy"]["cleanup_status"] == "confirmed"
    assert output["execution_policy_hash"] == sha256_json(output["execution_policy"])
    assert output["profile_hash"] == session.backend.identity["profile_hash"]
    assert output["image_digest"] == PROBE_IMAGE_DIGEST
    assert output["source_hash"] == sha256_bytes(source.encode("utf-8"))
    assert output["snapshot_hash"] == sha256_json([
        {"path": "helper.py", "content_hash": sha256_bytes(b"PUBLIC_HELPER = True\n")},
        {"path": "module.py", "content_hash": sha256_bytes(b"VALUE = 2\n")},
    ])
    assert output["diff_hash"] == result.workspace_diff_hash == before_diff
    assert gateway.current_diff_hash == before_diff
    assert gateway.checks_by_diff == {}
    assert not gateway.visible_checks_pass()
    return call, result, elapsed


def test_real_probe_isolation_current_source_and_completed_replay(
    real_probe_session, real_probe_gateway, monkeypatch,
):
    session, gateway = real_probe_session, real_probe_gateway
    monkeypatch.setenv("PATCHLOOP_PROBE_TEST_SECRET", "FAKE_HOST_ONLY_SENTINEL")
    before = {
        path.relative_to(gateway.workspace).as_posix(): path.read_bytes()
        for path in gateway.workspace.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(gateway.workspace).parts
    }
    call, result, _ = _run(session, gateway, "isolation", """
        import errno
        import os
        import sys
        from pathlib import Path
        import helper
        import module

        assert module.VALUE == 2 and helper.PUBLIC_HELPER is True
        assert Path(module.__file__).read_bytes() == b'VALUE = 2\\n'
        assert os.getuid() == os.geteuid() == 10001
        assert os.getgid() == os.getegid() == 10001
        assert 'PATCHLOOP_PROBE_TEST_SECRET' not in os.environ
        assert 'OPENAI_API_KEY' not in os.environ
        assert {p.name for p in Path('/workspace').iterdir()} == {'module.py', 'helper.py'}
        for target in ('/workspace/.git', '/workspace/.env', '/workspace/.env.local',
                       '/workspace/.patchloop-hidden', '/workspace/untracked_secret.txt'):
            assert not Path(target).exists(), target
        for target in ('/workspace/module.py', '/workspace/unexpected.txt', '/readonly-test'):
            try:
                Path(target).write_text('must not write')
            except OSError as exc:
                assert exc.errno in (errno.EROFS, errno.EACCES, errno.EPERM)
            else:
                raise AssertionError('read-only boundary failed: ' + target)
        scratch = Path('/tmp/probe-scratch.txt')
        scratch.write_text('ephemeral')
        assert scratch.read_text() == 'ephemeral'
        routes = Path('/proc/net/route').read_text().splitlines()[1:]
        assert not any(line.split()[1] == '00000000' for line in routes if line.split())
        try:
            child = os.fork()
        except OSError as exc:
            assert exc.errno in (errno.EPERM, errno.EAGAIN)
        else:
            if child == 0:
                os._exit(0)
            os.waitpid(child, 0)
            raise AssertionError('fork unexpectedly allowed')
        try:
            os.execve(sys.executable, [sys.executable, '-c', 'raise SystemExit(77)'], {})
        except OSError as exc:
            assert exc.errno == errno.EPERM
        print('ISOLATION_OK', flush=True)
    """)
    assert result.output["status"] == "passed"
    assert result.output["exit_code"] == 0
    assert "ISOLATION_OK" in result.output["stdout"]
    after = {
        path.relative_to(gateway.workspace).as_posix(): path.read_bytes()
        for path in gateway.workspace.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(gateway.workspace).parts
    }
    assert after == before
    journal_before = gateway.journal.path.read_bytes()

    def cannot_execute(*args, **kwargs):
        pytest.fail("completed action replay attempted a new backend execution")

    with monkeypatch.context() as replay_patch:
        replay_patch.setattr(session.backend, "run_probe", cannot_execute)
        replay_patch.setattr(session.backend, "preflight", cannot_execute)
        restarted = DevToolGateway(
            workspace=gateway.workspace, public_task=gateway.public_task, sandbox=None,
            journal=DevJournal(gateway.journal.root, gateway.journal.run_id),
            limits=gateway.limits, probe_sandbox=session.backend,
            deadline=ExecutionDeadline.from_remaining(0),
        )
        replay = restarted.execute(call)
    assert replay.replayed is True
    assert replay.model_dump(exclude={"replayed"}) == result.model_dump(exclude={"replayed"})
    assert gateway.journal.path.read_bytes() == journal_before
    assert [event["event_type"] for event in gateway.journal.events()] == [
        "action_started", "action_finished",
    ]
    (session.evidence_root / "replay.json").write_text(json.dumps({
        "official": False, "provider_calls": 0, "run_id": gateway.journal.run_id,
        "action_id": call.action_id, "replayed": True, "additional_backend_calls": 0,
        "journal_unchanged": True, "same_result": True,
    }, indent=2), encoding="utf-8")


@pytest.mark.parametrize("case,source,execution,setup,reached", [
    ("mismatch", "settings = dict(mode='chosen'); settings.update(dict(mode='inherited'))\n"
     "check_setup('mode', settings['mode'], 'chosen')\nprint('BEHAVIOR_REACHED')",
     "failed", "failed", False),
    ("behavior", "check_setup('mode', 'chosen', 'chosen')\n"
     "print('BEHAVIOR_REACHED')\nassert False, 'behavior assertion'",
     "failed", "passed", True),
    ("caught", "try:\n check_setup('mode', 'actual', 'expected')\n"
     "except AssertionError:\n pass\nprint('BEHAVIOR_REACHED')",
     "passed", "failed", True),
    ("unused", "print('BEHAVIOR_REACHED')", "passed", "not_checked", True),
])
def test_real_probe_setup_checks(
    real_probe_session, real_probe_gateway, case, source, execution, setup, reached,
):
    session, gateway = real_probe_session, real_probe_gateway
    call, result, _ = _run(session, gateway, "setup-" + case, source)
    assert result.output["status"] == execution
    assert result.output["setup_checks"]["status"] == setup
    assert ("BEHAVIOR_REACHED" in result.output["stdout"]) is reached
    assert "PATCHLOOP-SETUP" not in result.output["stderr"]
    if case == "mismatch":
        assert "SetupMismatchError" in result.output["stderr"]
    before = gateway.journal.path.read_bytes()
    replay = gateway.execute(call)
    assert replay.replayed
    assert replay.model_dump(exclude={"replayed"}) == result.model_dump(exclude={"replayed"})
    assert gateway.journal.path.read_bytes() == before


def test_real_probe_two_stream_output_limit(real_probe_session, real_probe_gateway):
    _, result, _ = _run(real_probe_session, real_probe_gateway, "output-limit", """
        import os
        block = b'PUBLIC_FLOOD' * 512
        while True:
            os.write(1, block)
            os.write(2, block)
    """)
    output = result.output
    assert output["status"] == "output_limit"
    assert output["truncated"] is True
    assert output["captured_output_bytes"] == 12_000
    assert len(output["stdout"].encode()) + len(output["stderr"].encode()) <= 12_000
    assert output["observed_output_bytes"] > 12_000
    assert output["deadline_exhausted"] is False


def test_real_probe_shortened_deadline_and_cleanup(real_probe_session, real_probe_gateway):
    _, result, elapsed = _run(real_probe_session, real_probe_gateway, "deadline", """
        import time
        print('DEADLINE_LOOP_STARTED', flush=True)
        while True:
            time.sleep(0.05)
    """, seconds=12)
    output = result.output
    assert "DEADLINE_LOOP_STARTED" in output["stdout"]
    assert output["status"] == "timeout"
    assert output["timed_out"] is True
    assert output["deadline_exhausted"] is True
    assert 0 < output["execution_policy"]["effective_timeout_seconds"] <= 7
    assert output["execution_policy"]["row_deadline_limited"] is True
    assert elapsed <= 12.5


def test_real_probe_async_thread_retains_process_file_and_network_isolation(
    real_probe_session, real_probe_gateway,
):
    _, result, _ = _run(real_probe_session, real_probe_gateway, "async-thread", """
        import asyncio
        import errno
        import os
        import socket
        from pathlib import Path

        def worker():
            try:
                child = os.fork()
            except OSError as exc:
                assert exc.errno == errno.EPERM
            else:
                if child == 0:
                    os._exit(0)
                os.waitpid(child, 0)
                raise AssertionError('worker escaped process boundary')
            try:
                os.kill(os.getppid(), 0)
            except OSError as exc:
                assert exc.errno == errno.EPERM
            else:
                raise AssertionError('worker can signal the supervisor')
            try:
                Path('/workspace/module.py').write_text('changed')
            except OSError as exc:
                assert exc.errno in (errno.EROFS, errno.EACCES, errno.EPERM)
            else:
                raise AssertionError('worker changed source')
            with socket.socket() as sock:
                sock.settimeout(0.2)
                assert sock.connect_ex(('192.0.2.1', 80)) != 0
            return os.getpid(), Path('/workspace/module.py').read_text()

        async def main():
            pid, text = await asyncio.to_thread(worker)
            assert pid == os.getpid() and text == 'VALUE = 2\\n'

        try:
            asyncio.run(main())
        except RuntimeError as exc:
            print('THREAD_ERROR', str(exc), flush=True)
            raise SystemExit(1)
        print('ASYNC_THREAD_AND_SHUTDOWN_OK', flush=True)
    """)
    assert result.output["status"] == "passed", result.output["stdout"]
    assert result.output["exit_code"] == 0
    assert "ASYNC_THREAD_AND_SHUTDOWN_OK" in result.output["stdout"]


@pytest.mark.skipif(not os.environ.get("PATCHLOOP_TEST_PROBE_DEPENDENCIES"),
                    reason="SDK compatibility needs an existing public dependency descriptor")
def test_real_probe_openai_sdk_offline_transport_and_shutdown(
    real_probe_session, real_probe_gateway,
):
    path = Path(os.environ["PATCHLOOP_TEST_PROBE_DEPENDENCIES"])
    descriptor, identity = read_descriptor(path)
    dependencies = PreparedDependencies(path, identity, descriptor["repository_url"],
                                        descriptor["base_commit"])
    # Only public libraries are reused. The workspace is the independent toy fixture,
    # never the closed discovery candidate or any private evaluation package.
    backend = DockerProbeSandbox(dependencies=dependencies)
    backend.preflight(deadline=ExecutionDeadline.from_remaining(180))
    session = _RealSession(backend, real_probe_session.evidence_root)
    real_probe_gateway.probe_sandbox = backend
    _, result, _ = _run(session, real_probe_gateway, "sdk-thread", """
        import asyncio
        import json
        import socket
        import httpx
        import openai
        from openai import AsyncOpenAI

        def forbidden(*args, **kwargs):
            raise AssertionError('no network access in SDK compatibility fixture')

        socket.socket.connect = forbidden
        socket.create_connection = forbidden
        seen = []

        async def handler(request):
            assert request.url.host == 'fixture.invalid'
            seen.append(json.loads(request.content))
            return httpx.Response(200, json={
                'id': 'fixture-response', 'object': 'chat.completion', 'created': 1,
                'model': 'fixture-model',
                'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'offline'},
                             'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2},
            })

        async def main():
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
                async with AsyncOpenAI(api_key='fixture-only', base_url='https://fixture.invalid',
                                       max_retries=0, http_client=http) as client:
                    reply = await client.chat.completions.create(
                        model='fixture-model', messages=[{'role': 'user', 'content': 'fixture'}])
                    assert reply.choices[0].message.content == 'offline'
                    assert len(seen) == 1

        try:
            asyncio.run(main())
        except RuntimeError as exc:
            print('SDK_THREAD_ERROR', str(exc), flush=True)
            raise SystemExit(1)
        print('SDK_OFFLINE_AND_SHUTDOWN_OK', openai.__version__, flush=True)
    """, seconds=180)
    assert result.output["status"] == "passed", result.output["stdout"]
    assert result.output["exit_code"] == 0 and not result.output["truncated"]
    assert "SDK_OFFLINE_AND_SHUTDOWN_OK" in result.output["stdout"]


def test_real_probe_threads_are_bounded_and_background_workers_end_with_child(
    real_probe_session, real_probe_gateway,
):
    _, result, elapsed = _run(real_probe_session, real_probe_gateway, "thread-bound", """
        import threading
        import time

        release = threading.Event()
        threads = []
        try:
            for _ in range(64):
                worker = threading.Thread(target=release.wait)
                try:
                    worker.start()
                except RuntimeError:
                    break
                threads.append(worker)
            assert len(threads) == 6, len(threads)
            print('THREAD_LIMIT', len(threads), flush=True)
        finally:
            release.set()
            for worker in threads:
                worker.join(timeout=2)
                assert not worker.is_alive()
        # The trusted child exits the entire process even with an unjoined worker.
        threading.Thread(target=time.sleep, args=(60,)).start()
        print('BACKGROUND_WORKER_STARTED', flush=True)
    """)
    assert result.output["status"] == "passed" and result.output["exit_code"] == 0
    assert "THREAD_LIMIT 6" in result.output["stdout"]
    assert "BACKGROUND_WORKER_STARTED" in result.output["stdout"]
    assert elapsed < 20


def test_real_probe_timeout_cleans_up_running_worker_threads(
    real_probe_session, real_probe_gateway,
):
    _, result, elapsed = _run(real_probe_session, real_probe_gateway, "thread-timeout", """
        import asyncio
        import time

        def worker():
            print('THREAD_TIMEOUT_STARTED', flush=True)
            while True:
                time.sleep(0.05)

        async def main():
            await asyncio.to_thread(worker)

        asyncio.run(main())
    """, seconds=12)
    assert "THREAD_TIMEOUT_STARTED" in result.output["stdout"]
    assert result.output["status"] == "timeout" and result.output["timed_out"]
    assert result.output["deadline_exhausted"]
    assert elapsed <= 12.5
