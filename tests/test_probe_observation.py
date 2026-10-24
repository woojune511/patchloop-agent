"""Fast executable controls for the current caller adapter, no Docker/provider."""
from __future__ import annotations

import ast
import copy
import json

import pytest
from test_probe_invocation import execute, review

from patchloop.dev import probe_call_capture, probe_invocation, reproduction
from patchloop.util import sha256_bytes


def current(root, source, implementation, **kwargs):
    return execute(root / "execution", source=source, implementation=implementation,
                   channel=probe_invocation.CHANNEL, **kwargs)


def test_native_arguments_bind_and_capture_the_two_calls_separately(tmp_path):
    source = '''print("outside")
target = observed_target(input_paths=["input.txt"])
first = target(["src/project"], do_exit=False)
second = target(args=["control"], do_exit=False)
assert first.value is None and first.call_id != second.call_id
assert first.capture_status == second.capture_status == "complete"
record_observation("F0010" in first.stdout and "F0010" not in second.stdout
                   and first.stderr == second.stderr == "diagnostic\\n")
'''
    result = current(tmp_path, source,
                     'import sys; print("F0010" if args == ["src/project"] else "ok"); '
                     'print("diagnostic", file=sys.stderr)', parameters="args, do_exit=False")
    assert result["comparison"] == "matched", result
    first, second = result["call_observation"]["calls"]
    assert first["bound_parameters"] == {"args": ["src/project"], "do_exit": False}
    assert first["arguments"] == {"args": [["src/project"]], "kwargs": {"do_exit": False}}
    assert second["capture"]["stdout"] == "ok\n"
    assert first["capture"]["scope"] == "python-streams"
    assert "outside" not in str(first["capture"])


@pytest.mark.parametrize("arguments_fixed,output_fixed", [(False, False), (True, False),
                                                        (False, True), (True, True)])
def test_four_condition_mechanism_control(tmp_path, arguments_fixed, output_fixed):
    # A trusted tiny callable deliberately emits diagnostics but returns an object.
    # The separate real-Astroid experiment owns applicability to the public task.
    source = f'''call = observed_target()({["src/project"] if arguments_fixed else "src/project"!r})
text = call.stdout if {output_fixed!r} else repr(call.value)
record_observation("target-error" in text)
'''
    result = current(tmp_path, source,
                     'print("target-error" if args == ["src/project"] else "argument-error"); '
                     'return object()', parameters="args")
    assert (result["comparison"] == "matched") == (arguments_fixed and output_fixed)
    # Binding alone admits both a string and a list; it is not type certification.
    assert result["call_observation"]["calls"][0]["bound_parameters"]["args"] == (
        ["src/project"] if arguments_fixed else "src/project")


@pytest.mark.parametrize("implementation,settings,expected", [
    ("raise RuntimeError('unexpected')", "", "not_compared"),
    ("raise ValueError('reported')", "expected_exceptions=(ValueError,)", "matched"),
    ("raise ValueError('unexpected subtype')", "expected_exceptions=(Exception,)", "not_compared"),
    ("raise SystemExit(7)", "", "matched"),
    ("return (x for x in [])", "", "not_compared"),
    ("print('x' * 5000)", "", "not_compared"),
    ("import sys, io; sys.stdout = io.StringIO()", "", "not_compared"),
])
def test_missing_or_unexpected_evidence_cannot_become_a_no_error_value(
    tmp_path, implementation, settings, expected,
):
    source = f"call = observed_target({settings})()\nrecord_observation(True)"
    result = current(tmp_path, source, implementation, parameters="")
    assert result["comparison"] == expected, result
    if "SystemExit" in implementation:
        assert result["call_observation"]["calls"][0]["exit_code"] == 7
    if "5000" in implementation:
        capture = result["call_observation"]["calls"][0]["capture"]
        assert capture["status"] == "truncated"
        assert len(capture["stdout"].encode()) <= probe_call_capture.CAPTURE_BYTES


def test_capture_budget_is_shared_and_utf8_safe(tmp_path):
    source = '''target = observed_target()
first, second = target(), target()
assert first.capture_status == "complete" and second.capture_status == "truncated"
record_observation(True)
'''
    result = current(tmp_path, source, "print('한' * 1000)", parameters="")
    assert result["comparison"] == "not_compared", result
    captures = [c["capture"] for c in result["call_observation"]["calls"]]
    assert sum(len(c["stdout"].encode()) for c in captures) <= probe_call_capture.CAPTURE_BYTES


def test_signature_failure_does_not_execute_target(tmp_path):
    source = '''try:
    observed_target()(wrong=True)
except TypeError:
    record_observation(True)
'''
    result = current(tmp_path, source, "raise AssertionError('must not execute')",
                     parameters="args")
    assert result["comparison"] == "not_compared", result
    assert result["call_observation"]["calls"][0]["outcome"] == "incomplete"


def test_results_are_excluded_from_input_identity_but_arguments_are_not(tmp_path):
    source = '''call = observed_target(input_paths=["input.txt"])(["src/project"])
record_observation("F0010" not in call.stdout)
'''
    before = current(tmp_path / "before", source, "print('F0010')", parameters="args")
    after = current(tmp_path / "after", source, "print('ok')", parameters="args")
    assert review(before, after)["comparison_status"] == "mismatch_to_match"
    assert before["binding"] == after["binding"]
    assert probe_invocation.conditions(before["call_observation"]) == (
        probe_invocation.conditions(after["call_observation"]))
    rebound = copy.deepcopy(after)
    rebound["call_observation"]["calls"][0]["bound_parameters"] = {"renamed": ["src/project"]}
    assert review(before, rebound)["comparison_status"] == "mismatch_to_match"
    changed = copy.deepcopy(after)
    changed["call_observation"]["calls"][0]["arguments"]["args"] = ["src/project"]
    assert review(before, changed)["evidence"]["status"] == "UNKNOWN"


def test_reader_enforces_capture_health_even_if_report_incomplete_flag_is_false(tmp_path):
    result = current(tmp_path, "observed_target()()\nrecord_observation(True)",
                     "return None", parameters="")
    call = result["call_observation"]["calls"][0]
    call["capture"]["status"] = "truncated"
    trace = {"calls": [call], "incomplete": False,
             "observation": {"count": 1, "call_count": 1, "json": "true", "error": None}}
    output = {"status": "passed", "exit_code": 0, "stdout": "",
              "stderr": reproduction.marker(result["binding"]) + json.dumps(trace)}
    compared = reproduction.compare(output, result["binding"])["reproduction"]
    assert compared["comparison"] == "not_compared"


def test_new_observer_fits_existing_budget_and_old_bytes_remain_frozen():
    assert sha256_bytes(probe_invocation.observer(probe_invocation.ARGV_CHANNEL).encode()) == (
        "sha256:e040de896a21492a92fe92ad69dd2317dafc3246fe8ecffe56165a81ef4c9f3d")
    prefix, rest = probe_invocation.OBSERVER_V2.split("def call_target(", 1)
    suffix = "def record_observation(" + rest.split("def record_observation(", 1)[1]
    suffix = suffix.replace("if len(report) > 6000:", 'if len(report.encode("utf-8")) > 10000:')
    suffix = suffix.replace("ensure_ascii=True, allow_nan=False",
                            "ensure_ascii=False, allow_nan=False")
    assert ast.dump(ast.parse(prefix + probe_call_capture.CALLS + suffix)) == ast.dump(
        ast.parse(probe_invocation.observer(probe_invocation.CHANNEL)))
    binding = {"case_id": "sha256:" + "c" * 64, "definition": {
        "entrypoint": "x." + "a" * 198, "observation_channel": probe_invocation.CHANNEL}}
    assert len(reproduction.program("", binding)) - len(repr("")) <= 8000
