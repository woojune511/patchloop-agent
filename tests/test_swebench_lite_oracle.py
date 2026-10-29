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
from patchloop.contracts import RegisteredCheck
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


def captured_failure_bytes(capture):
    return b"".join(base64.b64decode(segment["content"])
                    for block in capture["blocks"] for segment in block["segments"])


def assert_failure_offsets(raw, capture):
    for block in capture["blocks"]:
        assert block["original_bytes"] == block["end_byte"] - block["start_byte"]
        assert block["original_bytes"] == block["retained_bytes"] + block["omitted_bytes"]
        for segment in block["segments"]:
            assert base64.b64decode(segment["content"]) == raw[
                segment["start_byte"]:segment["end_byte"]]


def test_failure_capture_keeps_traceback_between_megabytes_of_verbose_output():
    failure = (b"________________ test_synthetic ________________\r\n"
               b"    assert actual == expected\r\n"
               b"E   AssertionError: synthetic unequal value\r\n")
    raw = (b"verbose setup\n" * 100_000 + b"================ FAILURES ================\r\n"
           + failure + b"------------ Captured stdout call ------------\r\n"
           + b"verbose captured output\n" * 100_000
           + b"================ short test summary info ================\r\n"
           + b"FAILED synthetic_test\r\n")
    packet = swebench_lite_oracle.execution_log("tests", raw, b"")
    stream = packet["stdout"]
    assert b"AssertionError" not in base64.b64decode(stream["content"])
    assert stream["sha256"] == hashlib.sha256(raw).hexdigest()
    capture = stream["failure_capture"]
    assert captured_failure_bytes(capture) == failure
    assert capture["recognized_block_count"] == capture["retained_block_count"] == 1
    assert capture["omitted_bytes"] == capture["unclosed_block_count"] == 0
    assert_failure_offsets(raw, capture)


def test_failure_capture_scans_whitespace_heavy_nonheaders_in_bounded_time():
    failure = (b"____________ test_synthetic ____________\n"
               b"E   AssertionError: synthetic mismatch\n")
    raw = (b"===" + b" " * 10_000 + b"x\n"
           + b"___" + b"\t" * 10_000 + b"x\n"
           + b"================ FAILURES ================\n" + failure
           + b"================ short test summary info ================\n")
    # Keep this regression bounded even if a backtracking matcher is reintroduced.
    result = subprocess.run(
        [sys.executable, "-B", "-c",
         "import json, sys; from diagnostics.swebench_lite_oracle import execution_log; "
         "print(json.dumps(execution_log('tests', sys.stdin.buffer.read(), None)))"],
        input=raw, capture_output=True, timeout=5, check=True,
    )
    capture = json.loads(result.stdout)["stdout"]["failure_capture"]
    assert captured_failure_bytes(capture) == failure
    assert capture["recognized_block_count"] == 1
    assert_failure_offsets(raw, capture)


def test_failure_capture_preserves_collection_setup_and_test_errors():
    raw = (b"================ ERRORS ================\n"
           b"____________ ERROR collecting test_synthetic.py ____________\n"
           b"ImportError: synthetic missing module\n"
           b"____________ ERROR at setup of test_one ____________\n"
           b"RuntimeError: synthetic fixture error\n"
           b"------------ Captured stderr setup ------------\nignored captured output\n"
           b"================ FAILURES ================\n"
           b"____________ test_two ____________\nE   AssertionError: synthetic mismatch\n"
           b"================ short test summary info ================\n")
    capture = swebench_lite_oracle.execution_log("tests", raw, None)["stdout"][
        "failure_capture"]
    retained = captured_failure_bytes(capture)
    assert capture["recognized_block_count"] == capture["retained_block_count"] == 3
    assert capture["omitted_bytes"] == capture["unclosed_block_count"] == 0
    for message in (b"ImportError:", b"RuntimeError:", b"AssertionError:"):
        assert message in retained
    assert b"ignored captured output" not in retained
    assert_failure_offsets(raw, capture)


def test_failure_capture_preserves_unittest_failure_and_error():
    raw = (b"test_one ... FAIL\n"
           b"======================================================================\n"
           b"FAIL: test_one (SyntheticTest)\n"
           b"----------------------------------------------------------------------\n"
           b"Traceback (most recent call last):\nAssertionError: unequal\n\n"
           b"======================================================================\n"
           b"ERROR: test_two (SyntheticTest)\n"
           b"----------------------------------------------------------------------\n"
           b"Traceback (most recent call last):\nValueError: invalid\n\n"
           b"----------------------------------------------------------------------\n"
           b"Ran 2 tests in 0.001s\nFAILED (failures=1, errors=1)\n")
    capture = swebench_lite_oracle.execution_log("tests", None, raw)["stderr"][
        "failure_capture"]
    assert capture["recognized_block_count"] == capture["retained_block_count"] == 2
    assert all(block["format"] == "unittest" for block in capture["blocks"])
    assert capture["omitted_bytes"] == capture["unclosed_block_count"] == 0
    assert b"AssertionError: unequal" in captured_failure_bytes(capture)
    assert b"ValueError: invalid" in captured_failure_bytes(capture)
    assert b"Ran 2 tests" not in captured_failure_bytes(capture)
    assert_failure_offsets(raw, capture)


def test_failure_capture_truncates_huge_block_with_explicit_head_tail_offsets():
    raw = (b"================ FAILURES ================\n"
           b"____________ test_huge ____________\nsource context\n" + b"x" * 2_000_000
           + b"\nE   AssertionError: synthetic final mismatch\n"
           b"================ short test summary info ================\n")
    capture = swebench_lite_oracle.execution_log("tests", raw, None)["stdout"][
        "failure_capture"]
    block, = capture["blocks"]
    head, tail = block["segments"]
    assert b"source context" in base64.b64decode(head["content"])
    assert b"AssertionError:" in base64.b64decode(tail["content"])
    assert capture["retained_bytes"] == swebench_lite_oracle.DIAGNOSTIC_FAILURE_LIMIT_BYTES
    assert capture["truncated_block_count"] == 1
    assert capture["omitted_bytes"] == tail["start_byte"] - head["end_byte"] > 0
    assert_failure_offsets(raw, capture)


def test_failure_capture_block_limit_and_encoded_envelope_budget():
    raw = b"================ FAILURES ================\n" + b"".join(
        f"____________ test_{index} ____________\n".encode() + b"x" * 20_000
        + b"\nE   AssertionError: synthetic\n" for index in range(30)
    ) + b"================ short test summary info ================\n"
    packet = swebench_lite_oracle.execution_log("tests", raw, raw)
    for stream in (packet["stdout"], packet["stderr"]):
        capture = stream["failure_capture"]
        assert capture["recognized_block_count"] == 30
        assert capture["retained_block_count"] == capture["truncated_block_count"] == 8
        assert capture["omitted_block_count"] == 22
        assert capture["retained_bytes"] == swebench_lite_oracle.DIAGNOSTIC_FAILURE_LIMIT_BYTES
        assert_failure_offsets(raw, capture)
    assert len(json.dumps(packet).encode()) < 110_000
    # Reserve space for the existing grading report; its semantics are unchanged.
    envelope = {"execution_log": packet, "resolved": False, "complete": True,
                "test_exit": 1, "missing_count": 0, "reported_count": 500,
                "report": {"resolved": False, "tests_status": {
                    "FAIL_TO_PASS": {"failure": [f"synthetic_case_{i}" for i in range(500)]}}}}
    registered = RegisteredCheck(id="original-oracle", command=["synthetic"])
    assert len(json.dumps(envelope).encode()) < registered.output_limit_bytes


def test_failure_capture_unrecognized_output_and_binary_timeout_are_explicit():
    raw = b"FAILED synthetic_test\nAssertionError: no supported block header\xff\x00\n"
    packet = swebench_lite_oracle.execution_log("tests", raw, None)
    capture = packet["stdout"]["failure_capture"]
    assert capture["coverage"] == "no-recognized-blocks"
    assert capture["recognized_block_count"] == 0 and capture["blocks"] == []
    assert base64.b64decode(packet["stdout"]["content"]) == raw
    partial = (b"================ ERRORS ================\n"
               b"____________ ERROR collecting synthetic.py ____________\n"
               b"partial traceback\xff\x00")
    packet = swebench_lite_oracle.execution_log("timeout", partial, raw)
    capture = packet["stdout"]["failure_capture"]
    assert packet["stage"] == "timeout"
    assert capture["coverage"] == "recognized-blocks-only"
    assert capture["unclosed_block_count"] == 1
    assert capture["blocks"][0]["closed_by_marker"] is False
    assert b"partial traceback\xff\x00" in captured_failure_bytes(capture)
    assert_failure_offsets(partial, capture)


def test_private_log_is_retained_after_finish_without_solver_feedback(tmp_path, monkeypatch):
    sentinel = "AssertionError: synthetic private evaluator detail"
    output = ("================ FAILURES ================\n"
              "____________ synthetic_test ____________\n" + sentinel + "\n"
              "================ short test summary info ================\n")
    packet = swebench_lite_oracle.execution_log("tests", output, "")
    encoded = [packet["stdout"]["content"], packet["stdout"]["failure_capture"][
        "blocks"][0]["segments"][0]["content"]]
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
        assert sentinel not in content
        assert all(value not in content for value in encoded)
    assert all(value not in json.dumps(finished["payload"]["summary"]) for value in encoded)
    assert any(all(value in path.read_text("utf-8") for value in encoded)
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
