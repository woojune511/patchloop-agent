"""Fast regression of field feedback and the failed live observation's structure."""
from __future__ import annotations

import copy

import pytest
from test_probe_observation import current
from test_probe_purpose import original_intent

from patchloop.dev import probe_comparison, probe_invocation, reproduction
from patchloop.dev.probe_observation import project_probe_result
from patchloop.util import canonical_json


def diff(expected, observed):
    return probe_comparison.differences(canonical_json(expected), canonical_json(observed))


def test_live_failure_shape_has_actionable_differences_without_changing_the_verdict(tmp_path):
    # Same structural errors as the public pilot, using a tiny trusted callable.
    failure = {"outcome": "fail", "exit_code": 32, "stderr_has_F0010": True,
               "message": "F0010"}
    desired = {"outcome": "pass", "exit_code": 0, "stderr_has_F0010": False}
    source = '''call = observed_target()([], do_exit=False)
record_observation(dict(outcome=call.outcome, exit_code=call.exit_code,
    exception=call.exception, stderr_has_F0010="F0010" in call.stderr,
    stdout_tail=call.stdout, stderr_tail=call.stderr))
'''
    result = current(tmp_path, source, 'print("F0010")', parameters="args, do_exit=False",
                     expected_json=canonical_json(desired),
                     reported_failure_json=canonical_json(failure))
    assert result["comparison"] == result["declared_failure_comparison"] == "mismatched"
    feedback = result["comparison_feedback"]
    failure_rows = {row["path"]: row["kind"]
                    for row in feedback["declared_failure"]["differences"]}
    assert failure_rows == {"/exception": "extra", "/exit_code": "type", "/message": "missing",
                            "/outcome": "value", "/stderr_has_F0010": "value",
                            "/stderr_tail": "extra", "/stdout_tail": "extra"}
    assert feedback["declared_failure"]["omitted_count"] == 0
    assert "/stderr_has_F0010" not in {
        row["path"] for row in feedback["desired"]["differences"]}
    assert result["binding"]["definition"]["reported_failure_json"] == canonical_json(failure)
    receipt = {"tool": "run_probe", "output": {"status": "passed", "reproduction": result}}
    frozen = copy.deepcopy(receipt)
    projected = project_probe_result(receipt)
    assert projected["output"]["reproduction"]["comparison_feedback"] == feedback
    assert receipt == frozen  # Model projection preserves the durable receipt.
    assert result["repair_success"] == "not_assessed"


@pytest.mark.parametrize("expected,observed,path,kind", [
    ({"a/b~": [True]}, {"a/b~": [1]}, "/a~1b~0/0", "type"),
    ({"a": None}, {}, "/a", "missing"),
    ({}, {"a": None}, "/a", "extra"),
    ([1], [1, 2], "/1", "extra"),
    ([1, 2], [1], "/1", "missing"),
    (1, 1.0, "", "type"),
    (-0.0, 0.0, "", "value"),
    ({"x": "bad"}, {"x": "ok"}, "/x", "value"),
])
def test_strict_scalar_types_nested_paths_and_absent_values(expected, observed, path, kind):
    result = diff(expected, observed)
    assert result["omitted_count"] == 0 and len(result["differences"]) == 1
    assert result["differences"][0]["path"] == path
    assert result["differences"][0]["kind"] == kind


def test_feedback_bounds_do_not_hide_omissions_or_claim_complete_paths():
    expected = {"한" * 170: {str(i): False for i in range(10)}}
    observed = {"한" * 170: {str(i): True for i in range(10)}}
    assert len(canonical_json(expected).encode()) <= 2048
    result = diff(expected, observed)
    assert len(canonical_json(result).encode()) <= probe_comparison.MAX_FEEDBACK_BYTES
    assert 0 < len(result["differences"]) <= probe_comparison.MAX_DIFFERENCES
    assert all(row["path_truncated"] for row in result["differences"])
    assert len(result["differences"]) + result["omitted_count"] == 10
    assert diff({"b": 2, "a": [True]}, {"a": [True], "b": 2}) == {
        "differences": [], "omitted_count": 0}


@pytest.mark.parametrize("record", ["pass", "record_observation(object())",
                                     "record_observation(True)\nrecord_observation(True)"])
def test_missing_invalid_or_duplicate_observations_have_no_comparison_feedback(tmp_path, record):
    result = current(tmp_path, "observed_target()()\n" + record, "return None", parameters="")
    assert result["comparison"] == "not_compared"
    assert "comparison_feedback" not in result


@pytest.mark.parametrize("implementation,channel,failure,desired", [
    ('print("F0010" if args == ["bug"] else "ok")', "stdout", "matched", "mismatched"),
    ('print("ok")', "stdout", "mismatched", "matched"),
    ('print("F0010" if args == ["control"] else "ok")', "stdout", "mismatched", "mismatched"),
    ('print("F0010" if args == ["bug"] else "ok")', "stderr", "mismatched", "matched"),
])
def test_same_small_extractor_for_failure_control_and_repair(
    tmp_path, implementation, channel, failure, desired,
):
    source = f'''target = observed_target()
def has_error(call):
    if call.capture_status != "complete" or call.outcome != "returned":
        raise RuntimeError("uninterpretable call")
    return "F0010" in call.{channel}
bug = has_error(target(["bug"]))
control = has_error(target(["control"]))
record_observation(dict(bug_has_error=bug, control_has_error=control))
'''
    result = current(tmp_path, source, implementation, parameters="args",
                     reported_failure_json='{"bug_has_error":true,"control_has_error":false}',
                     expected_json='{"bug_has_error":false,"control_has_error":false}')
    assert result["declared_failure_comparison"] == failure
    assert result["comparison"] == desired
    calls = result["call_observation"]["calls"]
    assert len(calls) == 2 and all(call["exit_code"] is None for call in calls)
    if channel == "stderr":
        # A desired match from the wrong channel still fails original-failure acquisition.
        assert "F0010" in calls[0]["capture"]["stdout"]
        assert result["comparison_feedback"]["declared_failure"]["differences"] == [
            {"path": "/bug_has_error", "kind": "value"}]


def test_legitimate_failure_and_desired_shape_changes_are_not_rejected(smoke_package):
    intent = original_intent(smoke_package.public, reported_failure_json='{"error":"bug"}',
                             expected_json='["ok"]')
    binding = reproduction.bind(intent, smoke_package.public, "pass", "shape-change",
                                observation_channel=probe_invocation.CHANNEL)
    assert binding["definition"]["expected_json"] == '["ok"]'
