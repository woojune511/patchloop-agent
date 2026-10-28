import base64
import hashlib
import json
import subprocess
import sys
import types
from dataclasses import replace
from pathlib import Path

import pytest

from diagnostics import swebench_lite_oracle
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.runner import run_dev
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox


def test_private_execution_log_preserves_assertion_and_timeout_bytes():
    stdout = "FAILED synthetic_test\nAssertionError: expected value\n한글\n"
    stderr = b"partial timeout output\xff"
    packet = swebench_lite_oracle.execution_log("timeout", stdout, stderr)
    assert packet["stage"] == "timeout"
    for name, raw in (("stdout", stdout.encode("utf-8")), ("stderr", stderr)):
        assert base64.b64decode(packet[name]["content"]) == raw
        assert packet[name]["sha256"] == hashlib.sha256(raw).hexdigest()
        assert packet[name]["omitted_prefix_bytes"] == 0
    assert swebench_lite_oracle.execution_log("timeout", None, None)["stdout"][
        "original_bytes"] == 0


def test_private_execution_log_reports_omission_without_losing_final_failure():
    limit = swebench_lite_oracle.DIAGNOSTIC_STREAM_LIMIT_BYTES
    raw = b"x" * (limit + 100) + b"\nAssertionError: final failure\n"
    packet = swebench_lite_oracle.execution_log("tests", raw, b"")
    stdout = packet["stdout"]
    assert base64.b64decode(stdout["content"]) == raw[-limit:]
    assert stdout["original_bytes"] == len(raw)
    assert stdout["retained_bytes"] == limit
    assert stdout["omitted_prefix_bytes"] == len(raw) - limit
    assert stdout["sha256"] == hashlib.sha256(raw).hexdigest()
    assert len(json.dumps(packet)) < 70_000


def test_private_log_is_retained_after_finish_without_solver_feedback(tmp_path, monkeypatch):
    sentinel = "AssertionError: synthetic private evaluator detail"
    packet = swebench_lite_oracle.execution_log("tests", sentinel, "")
    encoded = packet["stdout"]["content"]
    original = LocalSandbox.run_check

    def execute(self, workspace, check, **kwargs):
        outcome = original(self, workspace, check, **kwargs)
        if check.id == "hidden-multiline-csv":
            return replace(outcome, exit_code=1, stdout=json.dumps({"execution_log": packet}))
        return outcome

    monkeypatch.setattr(LocalSandbox, "run_check", execute)
    result = run_dev(DevRunRequest(
        provider="mock", model="mock-dev", state_root=tmp_path,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
    ))["runs"][0]
    assert result["terminal"] == "EVALUATOR_FAIL"
    events = DevJournal(tmp_path, result["run_id"]).events()
    finished = next(event for event in events if event["event_type"] == "evaluator_finished")
    assert finished["payload"]["agent_context_reinjected"] is False
    inputs = [event for event in events if event["event_type"] == "turn_started"]
    assert inputs
    for event in inputs:
        assert event["sequence"] < finished["sequence"]
        content = Path(event["payload"]["model_input_artifact"]["path"]).read_text("utf-8")
        assert sentinel not in content and encoded not in content
    assert encoded not in json.dumps(finished["payload"]["summary"])
    assert any(encoded in path.read_text("utf-8")
               for path in (tmp_path / "artifacts/objects").rglob("*") if path.is_file())


@pytest.mark.parametrize("mode,code", [
    ("pass", 0), ("fail", 1), ("timeout", 2), ("grading", 2), ("patch", 2),
])
def test_adapter_retains_private_output_without_changing_verdict(
    tmp_path, monkeypatch, capsys, mode, code,
):
    hidden = tmp_path / "hidden"
    hidden.mkdir()
    (hidden / "oracle.json").write_text(json.dumps({
        "spec": {"instance_id": "synthetic", "log_parser": "parse",
                 "FAIL_TO_PASS": ["synthetic"], "PASS_TO_PASS": []},
        "test_patch": "synthetic patch", "test_command": ["pytest"],
    }))
    monkeypatch.setattr(swebench_lite_oracle, "__file__", str(hidden / "run_oracle.py"))
    monkeypatch.setattr(swebench_lite_oracle.shutil, "copytree", lambda *_a, **_k: None)
    modules = {}
    for name in ("swebench", "swebench.harness", "swebench.harness.log_parsers",
                 "swebench.harness.log_parsers.python", "swebench.harness.constants",
                 "swebench.harness.grading", "swebench.types"):
        modules[name] = types.ModuleType(name)
        monkeypatch.setitem(sys.modules, name, modules[name])
    modules["swebench.harness.log_parsers.python"].parse = lambda *_: {}
    constants = modules["swebench.harness.constants"]
    for name in ("START_TEST_OUTPUT", "END_TEST_OUTPUT", "TEST_EXIT_CODE"):
        setattr(constants, name, name)
    modules["swebench.types"].TestSpec = lambda **kwargs: types.SimpleNamespace(**kwargs)
    grading = modules["swebench.harness.grading"]

    def get_logs(*_):
        if mode == "grading":
            raise ValueError("synthetic parser failure")
        return {"synthetic": "PASSED" if mode == "pass" else "FAILED"}, True

    grading.get_logs_eval = get_logs
    grading.get_eval_report = lambda *_a, **_k: {"synthetic": {"resolved": mode == "pass"}}
    output = "AssertionError: operator-only synthetic output\n"

    def execute(command, **_kwargs):
        if command[0] == "git":
            return subprocess.CompletedProcess(command, int(mode == "patch"), output, "")
        if mode == "timeout":
            raise subprocess.TimeoutExpired(command, 240, output=output.encode(), stderr=b"partial")
        return subprocess.CompletedProcess(command, 0 if mode == "pass" else 1, output, "")

    monkeypatch.setattr(swebench_lite_oracle.subprocess, "run", execute)
    # main changes import plumbing, so make those changes temporary as well.
    old_path = sys.path[:]
    try:
        assert swebench_lite_oracle.main() == code
    finally:
        sys.path[:] = old_path
    packet = json.loads(capsys.readouterr().out)
    assert base64.b64decode(packet["execution_log"]["stdout"]["content"]) == output.encode()
    if mode in {"pass", "fail"}:
        assert packet["resolved"] is (mode == "pass")
        assert packet["complete"] is True
    else:
        assert packet["status"] == "ERROR"


def test_missing_private_runtime_is_infrastructure_error_not_wrong_patch():
    # The template's diagnostic directory deliberately has no vendor/oracle bundle.
    result = subprocess.run(
        [sys.executable, swebench_lite_oracle.__file__],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "ERROR"
