"""Require discriminating public processing evidence without inventing output."""

from __future__ import annotations

import copy
import os
import subprocess
import sys

import pytest
from test_exception_frame_repair import no_external  # noqa: F401
from test_probe_invocation import inject_api

from patchloop.dev import probe_invocation, probe_judgment, reproduction
from patchloop.errors import ContractError
from patchloop.util import canonical_json

RULES = [
    {"field": "error", "call_id": "call-1", "code": "E1001", "role": "failure"},
    {"field": "processed", "call_id": "call-1", "code": "P1001", "role": "processing"},
]
DESIRED = canonical_json({"error": False, "processed": True})
FAILURE = canonical_json({"error": True, "processed": False})


@pytest.mark.parametrize("fault", ["missing_pair", "different_call", "wrong_expected",
                                  "same_signal"])
def test_incomplete_or_contradictory_declaration_has_actionable_error(fault):
    rules, desired = copy.deepcopy(RULES), DESIRED
    failure = FAILURE
    if fault == "missing_pair":
        rules.pop()
        desired, failure = '{"error":false}', '{"error":true}'
    elif fault == "different_call":
        rules[1]["call_id"] = "call-2"
    elif fault == "wrong_expected":
        desired = '{"error":false,"processed":false}'
    else:
        rules[1]["code"] = "E1001"
    with pytest.raises(ContractError) as caught:
        probe_judgment.validate(rules, desired, failure)
    assert "/purpose/diagnostic_rules" in {
        row["path"] for row in caught.value.details["invalid_fields"]}


@pytest.mark.parametrize("message,expected", [
    ("E1001: failure", "mismatched"),
    ("", "mismatched"),
    ("E1001: different message\nP1001: item processed", "mismatched"),
    ("P1001: item processed", "matched"),
])
def test_host_rejects_empty_result_even_when_control_was_processed(
    tmp_path, smoke_package, message, expected,
):
    (tmp_path / "public_api.py").write_text(
        "def entry(bug):\n"
        f"    message = {message!r} if bug else 'P1001: control processed'\n"
        "    if message:\n        print(message)\n", encoding="utf-8")
    source = "target = observed_target()\ntarget(True)\ntarget(False)\n"
    binding = reproduction.bind({
        "entrypoint": "public_api.entry", "input_conditions": "bug then control",
        "environment_conditions": "local fixture", "expected_json": DESIRED,
        "reported_failure_json": FAILURE, "diagnostic_rules": RULES,
    }, smoke_package.public, source, "joint-evidence",
        observation_channel=probe_invocation.CHANNEL)
    result = execute(tmp_path, source, binding)
    assert result["comparison"] == expected
    assert result["judgment"]["status"] == "computed"
    assert result["observed_json"] == canonical_json({
        "error": "E1001" in message, "processed": "P1001" in message})
    calls = result["call_observation"]["calls"]
    assert all(call["target_started"] for call in calls)
    assert "P1001" in calls[1]["capture"]["stdout"]


def execute(root, source, binding):
    process = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", inject_api(reproduction.program(source, binding))],
        cwd=root, env={**os.environ, "PYTHONPATH": str(root)}, capture_output=True,
        encoding="utf-8", timeout=10, check=False)
    assert process.returncode == 0, process.stderr
    output = {"status": "passed", "exit_code": 0, "stdout": process.stdout,
              "stderr": process.stderr, "truncated": False, "timed_out": False,
              "cleanup_failed": False, "deadline_exhausted": False}
    return reproduction.compare(output, binding)["reproduction"]


def test_silent_api_can_observe_actual_processed_return_value(tmp_path, smoke_package):
    (tmp_path / "public_api.py").write_text(
        "def entry(items):\n    return [item.upper() for item in items]\n", encoding="utf-8")
    source = ("call = observed_target()(['item'])\n"
              "record_observation({'error': call.outcome != 'returned', "
              "'items': call.value})\n")
    desired = canonical_json({"error": False, "items": ["ITEM"]})
    binding = reproduction.bind({
        "entrypoint": "public_api.entry", "input_conditions": "one input item",
        "environment_conditions": "local fixture", "diagnostic_rules": None,
        "expected_json": desired,
        "reported_failure_json": canonical_json({"error": True, "items": []}),
    }, smoke_package.public, source, "silent-processing",
        observation_channel=probe_invocation.CHANNEL)
    result = execute(tmp_path, source, binding)
    assert result["comparison"] == "matched" and result["observed_json"] == desired
    assert result["call_observation"]["calls"][0]["capture"]["stdout"] == ""


def test_invocation_guidance_has_no_unsupported_keyword_or_no_error_only_example():
    assert "target.signature()" in reproduction.DESCRIPTION
    assert "target(*args, **kwargs)" in reproduction.DESCRIPTION
    assert "target() after setting sys.argv" in reproduction.DESCRIPTION
    assert "option=False" not in reproduction.DESCRIPTION
    assert "root=Path(reproduction_workspace())" in reproduction.DESCRIPTION
    assert "outputs=Path(reproduction_outputs())" in reproduction.DESCRIPTION
    assert "positive evidence" in reproduction.DESCRIPTION
    assert "desired={bug_has_error:false,control_has_error:false}" not in reproduction.DESCRIPTION
