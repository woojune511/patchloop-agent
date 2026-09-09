"""Public synthetic observations, never copies of private evaluator cases."""

from __future__ import annotations

import copy
import io
import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest
from native_history_support import input_context
from test_dev_feedback_integration_v18 import _completed_batch, _context, _input, _outputs
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _read, _restart
from test_dev_probe_sandbox import FakeProcess, backend, mock_launch
from test_dev_probe_sandbox import public_repo as public_repo
from test_sandbox_capture import fake_capture

from patchloop.contracts import RegisteredCheck
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.runtime import repository_root
from patchloop.sandbox import execution_feedback as feedback
from patchloop.sandbox.line_trace import marker
from patchloop.sandbox.probes import _WRAPPER as PROBE_WRAPPER
from patchloop.sandbox.probes import _OutputCollector
from patchloop.sandbox.runner import DockerSandbox, LocalSandbox
from patchloop.task_loader import load_public_task
from patchloop.util import canonical_json, sha256_bytes

SOURCE = (
    "def choose(flag):\n"
    "    if flag:\n"
    "        return 7\n"
    "    raise ValueError('PUBLIC_EDGE_SENTINEL')\n"
    "# comment is not a line-entry obligation\n"
)


def request(root, raw=None):
    raw = SOURCE.encode() if raw is None else raw
    (root / "sample.py").write_bytes(raw)
    return feedback.make_request(
        sha256_bytes(b"public-diff"), [{
            "path": "sample.py", "file_hash": sha256_bytes(raw),
            "changed_lines": [1, 2, 3, 4, 5],
        }], execution_identity={"run_id": "synthetic", "action_id": "check"},
        omitted_file_count=0, deleted_line_count=1,
    )


def report(targets, *, hits=(1, 2, 3)):
    return {"request_hash": targets["request_hash"], "files": [{
        "index": 0, "status": "collected", "executable": [1, 2, 3, 4], "executed": list(hits),
    }]}


def wire(targets, payload=None):
    body = canonical_json(report(targets) if payload is None else payload).encode()
    return marker(targets) + body + b"\n"


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("mode", ["inline", "module", "script"])
@pytest.mark.parametrize("executable", ["python", sys.executable])
def test_public_pass_reports_unobserved_changed_error_line(tmp_path, newline, mode, executable):
    targets = request(tmp_path, SOURCE.replace("\n", newline).encode())
    source = "import sample; assert sample.choose(True) == 7; print('PUBLIC_PASS')"
    if mode == "inline":
        command = [executable, "-c", source]
    else:
        (tmp_path / "public_check.py").write_text(source)
        command = [executable, "-m", "public_check"] if mode == "module" else [
            executable, "public_check.py",
        ]
    before = (tmp_path / "sample.py").read_bytes()
    check = RegisteredCheck(id="public", command=command)
    result = LocalSandbox().run_check(tmp_path, check, execution_targets=targets)
    assert result.passed and result.stdout.splitlines() == ["PUBLIC_PASS"] and result.stderr == ""
    assert result.command == command
    observed = result.public_execution
    assert observed["status"] == "collected"
    row = observed["files"][0]
    assert row["executed_changed_ranges"] == [[1, 3]]
    assert row["not_observed_changed_ranges"] == [[4, 4]]
    assert row["no_line_event_ranges"] == [[5, 5]]
    assert observed["diff_hash"] == targets["diff_hash"]
    assert row["file_hash"] == sha256_bytes(before)
    assert "PUBLIC_EDGE_SENTINEL" not in canonical_json(observed)
    assert "semantic correctness" in observed["interpretation"]
    assert (tmp_path / "sample.py").read_bytes() == before
    assert not (tmp_path / "__pycache__").exists()
    assert not list(tmp_path.glob("*line_request*"))


def test_failing_line_is_entered_not_a_correctness_claim(tmp_path):
    targets = request(tmp_path)
    check = RegisteredCheck(
        id="edge", command=["python", "-c", "import sample; sample.choose(False)"],
    )
    result = LocalSandbox().run_check(tmp_path, check, execution_targets=targets)
    assert not result.passed and result.exit_code == 1
    assert "ValueError: PUBLIC_EDGE_SENTINEL" in result.stderr
    row = result.public_execution["files"][0]
    assert row["executed_changed_ranges"] == [[1, 2], [4, 4]]
    assert row["not_observed_changed_ranges"] == [[3, 3]]
    assert "PATCHLOOP-LINES" not in result.stderr


@pytest.mark.parametrize("source", [
    "import sample; import sys; sys.settrace(None); assert sample.choose(True) == 7",
    "import os; os._exit(0)",
])
def test_trace_loss_does_not_turn_unknown_into_unexecuted_or_change_pass(tmp_path, source):
    targets = request(tmp_path)
    result = LocalSandbox().run_check(
        tmp_path, RegisteredCheck(id="public", command=["python", "-c", source]),
        execution_targets=targets,
    )
    assert result.passed
    assert result.public_execution["status"] == "unknown"
    assert result.public_execution["files"][0]["not_observed_changed_ranges"] is None


def test_other_thread_is_explicitly_outside_observation_scope(tmp_path):
    targets = request(tmp_path)
    result = LocalSandbox().run_check(
        tmp_path, RegisteredCheck(id="thread", command=[
            "python", "-c", "import sample, threading; "
            "t = threading.Thread(target=lambda: sample.choose(True)); t.start(); t.join()",
        ]), execution_targets=targets,
    )
    assert result.passed
    assert result.public_execution["scope"] == "python_launch_thread"
    assert result.public_execution["files"][0]["not_observed_changed_ranges"] == [[2, 4]]


def test_source_drift_and_syntax_failure_are_unknown(tmp_path):
    targets = request(tmp_path)
    (tmp_path / "sample.py").write_bytes(b"changed = 1\n")
    result = LocalSandbox().run_check(
        tmp_path, RegisteredCheck(id="public", command=["python", "-c", "assert True"]),
        execution_targets=targets,
    )
    assert result.passed
    assert result.public_execution["files"][0]["reason"] == "source_hash_mismatch"
    targets = request(tmp_path, b"if malformed\n")
    result = LocalSandbox().run_check(
        tmp_path, RegisteredCheck(id="public", command=["python", "-c", "assert True"]),
        execution_targets=targets,
    )
    assert result.passed
    assert result.public_execution["files"][0]["reason"] == "source_unavailable_or_uncompilable"


@pytest.mark.parametrize("executable", ["python", sys.executable])
def test_noninstrumented_private_or_unsupported_command_keeps_original_execution(
    tmp_path, executable,
):
    targets = request(tmp_path)
    check = RegisteredCheck(id="private-synthetic", command=[executable, "-c", "print('same')"])
    plain = LocalSandbox().run_check(tmp_path, check)
    assert plain.public_execution is None and plain.stdout.splitlines() == ["same"]
    flagged = check.model_copy(update={"command": [executable, "-B", "-c", "print('same')"]})
    result = LocalSandbox().run_check(tmp_path, flagged, execution_targets=targets)
    assert result.passed and result.stdout == plain.stdout and result.command == flagged.command
    assert result.public_execution["status"] == "unknown"


@pytest.mark.parametrize("executable", [
    "python", "python3", "/usr/local/bin/python", "/usr/bin/python3",
    "/venv/bin/python3.12", r"C:\Python312\python.exe", "C:/venv/Scripts/python3.exe",
    r"C:\Python312\Python.EXE", sys.executable,
])
def test_python_executable_names_are_independent_of_host_and_target_path_syntax(executable):
    assert feedback.python_command_supported([executable, "-c", "assert True"])


@pytest.mark.parametrize("command", [
    [], ["python"], ["/usr/local/bin/python", "-c"], ["/usr/local/bin/python", "-m"],
    ["/usr/local/bin/notpython", "-c", "assert True"],
    ["/venv/bin/python3.12-config", "public.py"], ["/bin/sh", "public.py"],
    ["/usr/bin/env", "python", "-c", "assert True"],
    ["/usr/local/bin/python", "-B", "-c", "assert True"],
])
def test_unrecognized_executable_or_launch_shape_stays_uninstrumented(command):
    assert not feedback.python_command_supported(command)


@pytest.mark.parametrize("alter", [
    lambda value: value.update(request_hash="wrong"),
    lambda value: value["files"][0].update(executed=[999]),
    lambda value: value["files"][0].update(executed=[True]),
    lambda value: value["files"][0].update(executable=[1, 1]),
    lambda value: value["files"][0].update(index=1),
    lambda value: value["files"][0].update(reason=["PRIVATE_SENTINEL"], status="unknown"),
])
def test_invalid_report_never_supplies_false_negative_or_private_metadata(tmp_path, alter):
    targets = request(tmp_path)
    value = report(targets)
    alter(value)
    value["private_spec"] = "PRIVATE_SENTINEL"
    result = feedback.public_feedback(targets, value)
    assert result["status"] == "unknown"
    assert result["files"][0]["not_observed_changed_ranges"] is None
    assert "PRIVATE_SENTINEL" not in canonical_json(result)


@pytest.mark.parametrize("block_size", [1, 19, 4096])
def test_report_channel_does_not_consume_public_output_budget(tmp_path, block_size):
    targets = request(tmp_path)
    value = b"public error\n" + wire(targets) + b"after\n"
    parts = []
    channel = feedback.ReportChannel(targets, parts.append)
    for offset in range(0, len(value), block_size):
        channel.feed(value[offset:offset + block_size])
    assert channel.finish() == report(targets)
    assert b"".join(parts) == b"public error\nafter\n"
    collector = _OutputCollector(targets)
    collector.drain(io.BytesIO(b"x" * 12000), "stdout")
    collector.drain(io.BytesIO(wire(targets)), "stderr")
    assert collector.observed == 12000 and not collector.limit_hit.is_set()
    assert collector.report == report(targets)


@pytest.mark.parametrize("bad", ["duplicate", "oversized", "incomplete", "malformed"])
def test_report_channel_is_bounded_and_fail_unknown(tmp_path, bad):
    targets = request(tmp_path)
    payload = {
        "duplicate": wire(targets) * 2,
        "oversized": marker(targets) + b"x" * 100000 + b"\n",
        "incomplete": wire(targets)[:-1],
        "malformed": marker(targets) + b"not-json\n",
    }[bad]
    public, value = feedback.split_report(payload, targets)
    assert value is None and public == b""
    collector = _OutputCollector(targets)
    collector.drain(io.BytesIO(payload), "stderr")
    assert collector.report is None
    assert len(collector.streams["stderr"]) <= 12000


def test_diff_selection_uses_postimage_lines_and_never_deleted_context():
    patch = (
        "diff --git a/sample.py b/sample.py\n--- a/sample.py\n+++ b/sample.py\n"
        "@@ -1,3 +1,4 @@\n context\n-old\n+new\n+also_new\n context\n"
        "@@ -9,2 +10,1 @@\n-deleted\n context\n"
    )
    assert feedback.changed_lines(patch) == {"sample.py": {2, 3}}


def check_call(action="check"):
    return RequestedTool(
        name="run_check", action_id=action, arguments={"check_id": "public"},
        turn_decision=PublicTurnDecision(mode="verify", basis="Exercise the public behavior."),
    )


def test_feedback_is_durable_native_and_advisory_without_source_admission(tmp_path, monkeypatch):
    gateway = _gateway(tmp_path)
    gateway.sandbox = LocalSandbox()
    gateway.public_task.visible_checks = [RegisteredCheck(
        id="public", command=["python", "-c", "import src; assert src.choose(True) == 7"],
    )]
    _read(gateway)
    assert gateway.execute(_mutation("edit", new=SOURCE)).status == "succeeded"
    # Deliberately clear the source cache: execution metadata must not create an anchor.
    gateway.spans.clear()
    before_coverage = copy.deepcopy(gateway._coverage_by_diff)
    _, results = _completed_batch(gateway, [check_call()], "check-turn")
    output = results[0].output["public_execution"]
    assert output["files"][0]["not_observed_changed_ranges"] == [[53, 53]]
    assert gateway.spans == {} and gateway._coverage_by_diff == before_coverage
    assert gateway.visible_checks_pass()
    assert gateway._finish_task({})["patch_hash"] == gateway.current_diff_hash
    items = _input(gateway, results, tmp_path)
    assert _outputs(items)["check"]["output"]["public_execution"] == output
    summary = input_context(items)["public_execution_summary"]
    assert summary == json.loads(_context(gateway, results))["public_execution_summary"]
    assert summary["files"][0]["not_observed_changed_ranges"] == [[53, 53]]
    before = gateway.journal.path.read_bytes()
    monkeypatch.setattr(gateway.sandbox, "run_check", lambda *a, **k: pytest.fail("reexecuted"))
    restored = _restart(gateway)
    assert restored.execute(check_call()).replayed
    assert restored.public_execution_summary(diff_hash=restored.current_diff_hash) == summary
    assert gateway.journal.path.read_bytes() == before
    # Further edits cannot inherit executed-line evidence or current PASS.
    _read(restored, "read-again")
    assert restored.execute(_mutation("next", old="return 7", new="return 8")).status == "succeeded"
    assert restored.public_execution_summary(diff_hash=restored.current_diff_hash)["files"] == []
    assert not restored.visible_checks_pass()


def test_summary_unions_check_probe_observations_but_never_stale_bytes(tmp_path):
    targets = request(tmp_path)
    one = feedback.public_feedback(targets, report(targets, hits=(1, 2, 3)))
    two = feedback.public_feedback(targets, report(targets, hits=(1, 2, 4)))
    records = [{"action_id": "check", "feedback": one}, {"action_id": "probe", "feedback": two}]
    hashes = {"sample.py": targets["files"][0]["file_hash"]}
    summary = feedback.summarize_execution(records, targets["diff_hash"], hashes)
    assert summary["files"][0]["executed_changed_ranges"] == [[1, 4]]
    assert summary["files"][0]["not_observed_changed_ranges"] == []
    assert summary["recent_action_ids"] == ["check", "probe"]
    assert feedback.summarize_execution(records, "new-diff", hashes)["files"] == []
    assert feedback.summarize_execution(records, targets["diff_hash"], {})["files"] == []


def test_mocked_docker_mounts_only_trusted_collector_and_preserves_check_policy(
    tmp_path, monkeypatch,
):
    targets = request(tmp_path)
    commands = []
    sandbox = DockerSandbox("public@sha256:" + "a" * 64)
    monkeypatch.setattr(sandbox, "cli_path", lambda: "docker")

    def run(command, **kwargs):
        commands.append(command)
        if command[1] == "container":
            return subprocess.CompletedProcess(
                command, 1, b"", b"No such container " + command[-1].encode(),
            )
        assert command[1] == "run"
        mount = next(arg for arg in command if "target=/opt/patchloop-lines," in arg)
        directory = Path(mount.split("source=", 1)[1].split(",target=")[0])
        assert mount.endswith(",readonly") and not directory.is_relative_to(tmp_path)
        assert (directory / "line_trace.py").read_bytes() == feedback.TRACE_WRAPPER.read_bytes()
        assert json.loads((directory / "line_request.json").read_bytes()) == targets
        assert command[-2:] == ["-c", "assert True"]
        return subprocess.CompletedProcess(command, 0, b"ok\n", wire(targets))

    monkeypatch.setattr("patchloop.sandbox.runner.subprocess.run", run)
    monkeypatch.setattr("patchloop.sandbox.runner.capture_process", fake_capture(run))
    result = sandbox.run_check(
        tmp_path, RegisteredCheck(id="public", command=["python", "-c", "assert True"]),
        execution_targets=targets,
    )
    assert result.passed and result.stderr == ""
    assert result.public_execution["status"] == "collected"
    assert result.execution_policy["cleanup_status"] == "confirmed"
    assert result.execution_policy["requested_network"] == "none"
    assert len(commands) == 2


@pytest.mark.parametrize("check_id,option", [
    ("parent-traversal-contract", "-c"), ("upstream-fake-os-regression", "-m"),
])
def test_actual_task_python_paths_are_instrumented_without_rewriting_command(
    tmp_path, monkeypatch, check_id, option,
):
    # Load public declarations, not private evaluators or copied semantic fixtures.
    public = load_public_task(
        repository_root() / "tasks/dev-train/pyfakefs-makedirs-parent-traversal-v2/public.yaml",
    )
    check = next(check for check in public.visible_checks if check.id == check_id)
    declared = list(check.command)
    assert declared[:2] == ["/usr/local/bin/python", option]
    targets = request(tmp_path)
    sandbox = DockerSandbox("public@sha256:" + "a" * 64)
    monkeypatch.setattr(sandbox, "cli_path", lambda: "docker")
    launches = []

    def run(command, **kwargs):
        if command[1] == "container":
            return subprocess.CompletedProcess(
                command, 1, b"", b"No such container " + command[-1].encode(),
            )
        assert command[1] == "run"
        launches.append(command)
        mounts = [arg for arg in command if "target=/opt/patchloop-lines," in arg]
        assert len(mounts) == 1, "absolute Python command must mount the collector"
        mount = mounts[0]
        assert mount.endswith(",readonly")
        directory = Path(mount.split("source=", 1)[1].split(",target=")[0])
        assert not directory.is_relative_to(tmp_path)
        assert json.loads((directory / "line_request.json").read_bytes()) == targets
        assert (directory / "line_trace.py").read_bytes() == feedback.TRACE_WRAPPER.read_bytes()
        assert command[command.index(sandbox.image) + 1:] == [
            declared[0], "/opt/patchloop-lines/line_trace.py",
            "/opt/patchloop-lines/line_request.json", "/workspace", *declared[1:],
        ]
        return subprocess.CompletedProcess(command, 0, b"mock public result\n", wire(targets))

    # No Docker or task check is executed: verify the real declaration's launch wiring.
    monkeypatch.setattr("patchloop.sandbox.runner.subprocess.run", run)
    monkeypatch.setattr("patchloop.sandbox.runner.capture_process", fake_capture(run))
    result = sandbox.run_check(tmp_path, check, execution_targets=targets)
    assert len(launches) == 1
    assert result.command == check.command == declared
    assert result.passed and result.stderr == ""
    assert result.public_execution["status"] == "collected"
    assert result.public_execution["files"][0]["not_observed_changed_ranges"] == [[4, 4]]
    assert result.execution_policy["cleanup_status"] == "confirmed"


def test_mocked_probe_copies_same_collector_in_existing_readonly_mount(monkeypatch, public_repo):
    targets = request(public_repo)
    sandbox = backend(monkeypatch)

    def launch(command, **kwargs):
        assert command[-1] == "/opt/patchloop/line_request.json"
        mounts = [value for value in command if value.startswith("type=bind")]
        assert len(mounts) == 2 and all(value.endswith(",readonly") for value in mounts)
        trusted = next(value for value in mounts if "target=/opt/patchloop," in value)
        directory = Path(trusted.split("source=", 1)[1].split(",target=")[0])
        assert (directory / "line_trace.py").read_bytes() == feedback.TRACE_WRAPPER.read_bytes()
        assert json.loads((directory / "line_request.json").read_bytes()) == targets
        return FakeProcess(b"public probe\n", wire(targets))

    mock_launch(monkeypatch, launch)
    result = sandbox.run_probe(
        public_repo, "public question", "print('public probe')", deadline=None,
        execution_identity={"run_id": "r", "action_id": "p"}, execution_targets=targets,
    )
    assert result["status"] == "passed" and result["stdout"] == "public probe\n"
    assert result["stderr"] == "" and result["public_execution"]["status"] == "collected"
    assert result["execution_policy"]["line_trace_hash"] == sha256_bytes(
        feedback.TRACE_WRAPPER.read_bytes(),
    )


def test_malformed_report_is_unknown_without_changing_probe_outcome(monkeypatch, public_repo):
    targets = request(public_repo)
    sandbox = backend(monkeypatch)
    mock_launch(monkeypatch, lambda *a, **k: FakeProcess(
        b"public result", marker(targets) + b"malformed\n",
    ))
    result = sandbox.run_probe(
        public_repo, "question", "print('public result')", deadline=None,
        execution_identity={"run_id": "r", "action_id": "p"}, execution_targets=targets,
    )
    assert result["status"] == "passed" and result["exit_code"] == 0
    assert not result["truncated"] and result["stdout"] == "public result"
    assert result["public_execution"]["status"] == "unknown"

    collector = _OutputCollector(targets)
    collector.drain(io.BytesIO(wire(targets) * 1000), "stderr")
    assert collector.limit_hit.is_set() and collector.report is None
    assert sum(len(value) for value in collector.streams.values()) <= 12000


@pytest.mark.parametrize("cleanup_ok", [True, False])
def test_timeout_preserves_deadline_and_cleans_container_before_collector_files(
    tmp_path, monkeypatch, cleanup_ok,
):
    targets = request(tmp_path)
    sandbox = DockerSandbox("public@sha256:" + "a" * 64)
    monkeypatch.setattr(sandbox, "cli_path", lambda: "docker")
    elapsed = [0.0]
    deadline = ExecutionDeadline.from_remaining(8, clock=lambda: elapsed[0])
    mounted = []

    def run(command, **kwargs):
        if command[1] == "run":
            mount = next(arg for arg in command if "target=/opt/patchloop-lines," in arg)
            directory = Path(mount.split("source=", 1)[1].split(",target=")[0])
            mounted.append(directory)
            assert kwargs["timeout"] == 3
            elapsed[0] = 3
            raise subprocess.TimeoutExpired(command, 3, stderr=wire(targets))
        assert (mounted[0] / "line_trace.py").is_file()
        if command[1] == "container":
            return subprocess.CompletedProcess(command, 0, command[-1].encode(), b"")
        assert command[1:3] == ["rm", "--force"]
        return subprocess.CompletedProcess(command, 0 if cleanup_ok else 1, b"", b"")

    monkeypatch.setattr("patchloop.sandbox.runner.subprocess.run", run)
    monkeypatch.setattr("patchloop.sandbox.runner.capture_process", fake_capture(run))
    result = sandbox.run_check(
        tmp_path, RegisteredCheck(id="public", command=["python", "-c", "assert True"]),
        deadline=deadline, execution_targets=targets,
    )
    assert not result.passed and result.deadline_exhausted and result.timed_out
    assert result.cleanup_failed is not cleanup_ok
    assert result.public_execution["status"] == "unknown"
    assert result.public_execution["files"][0]["not_observed_changed_ranges"] is None
    assert result.execution_policy["row_deadline_limited"]
    assert result.execution_policy["effective_timeout_seconds"] == 3
    assert not mounted[0].exists()


@pytest.mark.parametrize("source,exit_code", [
    ("import sample; assert sample.choose(True) == 7", 0),
    ("import sample; sample.choose(False)", 1),
    ("import sample; sample.choose(True); raise SystemExit(7)", 7),
])
def test_probe_child_flushes_same_line_report_before_each_exit(
    tmp_path, monkeypatch, capfd, source, exit_code,
):
    # Exercise the real child execution/exception path, not Linux isolation.
    targets = request(tmp_path)
    wrapper = runpy.run_path(str(PROBE_WRAPPER))
    collector_module = runpy.run_path(str(feedback.TRACE_WRAPPER))
    collector = collector_module["LineTrace"](targets, str(tmp_path))
    execute = wrapper["_execute_child"]
    monkeypatch.setitem(execute.__globals__, "_install_process_boundary", lambda: None)
    monkeypatch.setattr(wrapper["os"], "setsid", lambda: None, raising=False)
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, "sample", raising=False)

    class ChildExit(BaseException):
        def __init__(self, code):
            self.code = code

    def exit_child(code):
        raise ChildExit(code)

    monkeypatch.setattr(wrapper["os"], "_exit", exit_child)
    with pytest.raises(ChildExit) as ended:
        execute(compile(source, "<patchloop-probe>", "exec"), collector)
    assert ended.value.code == exit_code
    captured = capfd.readouterr()
    _, observed = feedback.split_report(captured.err.encode(), targets)
    result = feedback.public_feedback(targets, observed)
    assert result["status"] == "collected"
    assert result["files"][0]["not_observed_changed_ranges"] == (
        [[3, 3]] if exit_code == 1 else [[4, 4]]
    )


def test_pending_batch_replays_completed_check_without_execution(tmp_path, monkeypatch):
    gateway = _gateway(tmp_path)
    gateway.sandbox = LocalSandbox()
    gateway.public_task.visible_checks = [RegisteredCheck(
        id="public", command=["python", "-c", "import src; assert src.choose(True) == 7"],
    )]
    _read(gateway)
    assert gateway.execute(_mutation("edit", new=SOURCE)).status == "succeeded"
    call = check_call()
    gateway.journal.append("turn_decision_recorded", {
        "turn_id": "interrupted", "tool_calls": [call.model_dump(mode="json")],
    })
    result = gateway.execute(call)
    assert result.output["public_execution"]["status"] == "collected"
    # Crash point: durable action result, no tool_batch_finished event.
    assert not any(e["event_type"] == "tool_batch_finished" for e in gateway.journal.events())
    monkeypatch.setattr(
        gateway.sandbox, "run_check", lambda *a, **k: pytest.fail("duplicate check"),
    )
    replay = _restart(gateway).execute_batch([call])[0]
    assert replay.replayed and replay.output == result.output
    assert replay.workspace_diff_hash == result.workspace_diff_hash


def test_current_targets_exclude_nonpublic_paths_and_bound_whole_files(tmp_path):
    gateway = _gateway(tmp_path)
    _read(gateway)
    assert gateway.execute(_mutation("edit", new=SOURCE)).status == "succeeded"
    for name in (".env.py", ".patchloop-hidden/private.py", "not-tracked.py"):
        path = gateway.workspace / name
        path.parent.mkdir(exist_ok=True)
        path.write_text("PRIVATE_SOURCE_SENTINEL = 1\n")
    targets = gateway._execution_targets({"action_id": "test"})
    assert [f["path"] for f in targets["files"]] == ["src.py"]
    assert "PRIVATE_SOURCE_SENTINEL" not in canonical_json(targets)
    assert targets["files"][0]["changed_lines"] == list(range(50, 56))
    # Changing more than the collector's bound is not a fabricated partial observation.
    (gateway.workspace / "src.py").write_text("\n".join(f"x{n} = 1" for n in range(300)))
    targets = gateway._execution_targets()
    assert targets["files"] == [] and targets["omitted_file_count"] == 1
