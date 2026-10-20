"""Predicate behavior and execution errors are independent of report metadata."""
from __future__ import annotations

import json

import pytest

from diagnostics import output_predicate_controls as controls
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package


@pytest.fixture
def panel():
    path = repository_root() / "tasks/dev-train" / controls.TASK
    return controls.controls(load_task_package(path).public.issue.description)


def result(panel, values):
    return {"exit_code": 0, "timed_out": False, "cleanup_failed": False, "truncated": False,
            "stdout": json.dumps([{"id": case["id"], "accepted": value,
                                   "valid_bool": type(value) is bool, "error": None}
                                  for case, value in zip(panel, values, strict=True)])}


def test_public_controls_distinguish_positive_result_from_symptom_absence(panel):
    expected = panel[0]["actual"]
    exact = [p["actual"].splitlines() == expected.splitlines() for p in panel]
    symptom = ["         my_id," not in p["actual"] for p in panel]
    assert exact == [True, False, False, False]
    assert symptom == [True, False, True, True]
    assert controls.classify(result(panel, exact), panel)["status"] == "CONTROL_MATCH"
    assert controls.classify(result(panel, symptom), panel)["matches"] == [True, True, False, False]


@pytest.mark.parametrize("field,value", [("exit_code", 1), ("timed_out", True),
                                        ("cleanup_failed", True), ("truncated", True)])
def test_execution_failure_never_counts_as_rejection(panel, field, value):
    observation = {**result(panel, [True, False, False, False]), field: value}
    assert controls.classify(observation, panel) == {
        "status": "EXECUTION_INCOMPLETE", "matches": None}


@pytest.mark.parametrize("stdout", ["invalid", "null", "{}", "[]", "[null,null,null,null]"])
def test_invalid_observation_is_not_behavior_evidence(panel, stdout):
    observation = {**result(panel, [True, False, False, False]), "stdout": stdout}
    assert controls.classify(observation, panel)["status"] == "INVALID_OUTPUT"


def test_wrong_type_and_exception_do_not_count_as_rejection(panel):
    observation = result(panel, [True, False, False, False])
    rows = json.loads(observation["stdout"])
    rows[1].update(accepted=None, valid_bool=False, error="ValueError")
    observation["stdout"] = json.dumps(rows)
    assert controls.classify(observation, panel)["status"] == "INVALID_OUTPUT"
    wrong_type = controls.classify(result(panel, [True, 0, False, False]), panel)
    assert wrong_type["status"] == "INVALID_OUTPUT"


def test_program_does_not_send_operator_labels_or_expected_answers(panel):
    program = controls.program("def accepts(actual):\n    return False\n", panel)
    assert "expected_accept" not in program
    assert "quote_valid" not in program


def test_saved_source_hash_checked_before_sandbox_or_workspace(tmp_path):
    response = tmp_path / "response.json"
    response.write_text("{}", encoding="utf-8")
    target = tmp_path / "calibration"
    with pytest.raises(ContractError, match="hash mismatch"):
        controls.calibrate(target, saved_report=response, saved_report_hash="wrong")
    assert not target.exists()


def test_calibration_writes_summary_outside_cas_without_requiring_valid_quote(
    tmp_path, monkeypatch, panel,
):
    from patchloop.util import sha256_bytes

    observed = []

    class Sandbox:
        def preflight(self):
            return {"test": "fake-profile"}

        def run_probe(self, workspace, question, source, *, execution_identity, **kwargs):
            name = execution_identity["action_id"]
            observed.append(name)
            values = {"positive_expected": [True, False, False, False],
                      "symptom_only": [True, False, True, True],
                      "constant_true": [True, True, True, True],
                      "predicate_error": [None, None, None, None],
                      "saved_model_predicate": [True, False, False, False]}
            return result(panel, values[name])

    monkeypatch.setattr(controls, "DockerProbeSandbox", Sandbox)
    response = tmp_path / "response.json"
    response.write_text(json.dumps({
        "report_status": "NOT_ASSESSABLE", "tool_calls": [{"name": "submit_predicate",
        "arguments": {"python_source": "unexecuted test fixture",
                      "requirement_quote": "not quoted"}}]
    }), encoding="utf-8")
    root = tmp_path / "new-calibration"
    summary = controls.calibrate(root, saved_report=response,
                                 saved_report_hash=sha256_bytes(response.read_bytes()))
    assert len(observed) == 5
    assert json.loads((root / "calibration.json").read_bytes()) == summary
    assert summary["calibration_passed"]
    assert not summary["provenance"]["saved_response"]["quote_valid"]
    assert summary["rows"]["saved_model_predicate"]["classification"]["status"] == "CONTROL_MATCH"
