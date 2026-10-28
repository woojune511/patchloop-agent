"""Canonical diagnostic codes from public fixture captures; no provider or Docker."""
from __future__ import annotations

import copy
import os
import subprocess
import sys

import pytest
from test_exception_frame_repair import no_external  # noqa: F401
from test_probe_judgment import trace

from patchloop.dev import probe_invocation, probe_judgment, reproduction
from patchloop.errors import ContractError
from patchloop.util import canonical_json

RULES = [
    {"field": "bug", "call_id": "call-1", "code": "F0010"},
    {"field": "control", "call_id": "call-2", "code": "F0010"},
]
DESIRED = canonical_json({"bug": False, "control": False})
FAILURE = canonical_json({"bug": True, "control": False})


@pytest.mark.parametrize("text", [
    "src/project/__init__.py:1:0: F0010: Unable to load file",
    "src/project:1:0: F0010: No module named src.project",
])
def test_changed_failure_wording_retains_same_host_diagnostic(text):
    judgment = probe_judgment.evaluate(RULES, trace(text), DESIRED)
    assert judgment["policy"] == probe_judgment.CANONICAL_POLICY == "captured-diagnostic-v2"
    assert judgment["status"] == "computed" and judgment["source"] == "host"
    assert judgment["host_json"] == FAILURE
    assert judgment["authored_json"] == DESIRED  # A mistaken extractor has no authority.
    assert judgment["witnesses"][0]["matches"][0]["text"] == "F0010"
    assert judgment["witnesses"][1]["matches"] == []


@pytest.mark.parametrize("text,present", [
    ("XF00100", False), ("F00100", False), ("XF0010", False),
    ("F0010_EXTRA", False), ("F0010-extra", False), ("X-F0010", False),
    ("path.py:1:0: F0010: error", True), ("(F0010)", True),
])
def test_code_boundaries_do_not_match_longer_identifiers(text, present):
    result = probe_judgment.evaluate(RULES, trace(stderr=text), None)
    assert result["status"] == "computed"
    assert result["host_json"] == canonical_json({"bug": present, "control": False})


@pytest.mark.parametrize("fault", ["missing_call", "truncated", "missing_stream", "raised"])
def test_unavailable_capture_or_unexpected_exception_never_means_no_error(fault):
    value = trace("")
    if fault == "missing_call":
        value["calls"] = value["calls"][1:]
    elif fault == "truncated":
        value["calls"][0]["capture"]["status"] = "truncated"
    elif fault == "missing_stream":
        value["calls"][0]["capture"].pop("stderr")
    else:
        value["calls"][0].update(outcome="raised", exception={"type": "RuntimeError"})
    result = probe_judgment.evaluate(RULES, value, DESIRED)
    assert result["status"] == "unknown" and result["host_json"] is None
    assert result["witnesses"] == []


def test_fresh_wire_declares_codes_instead_of_message_substrings():
    original = reproduction.purpose_schema()["anyOf"][1]
    item = original["properties"]["diagnostic_rules"]["anyOf"][0]["items"]
    assert set(item["properties"]) == set(item["required"]) == {
        "field", "call_id", "code", "role"}
    assert item["additionalProperties"] is False
    assert item["properties"]["code"]["maxLength"] == 32
    assert probe_invocation.CHANNEL == "invoke-declared-call-v11"
    assert probe_invocation.CANONICAL_CHANNEL == "invoke-declared-call-v6"
    assert probe_invocation.DIAGNOSTIC_CHANNEL == "invoke-declared-call-v5"


@pytest.mark.parametrize("rule", [
    {"contains": "Unable to load file"}, {"code": "Unable to load file"},
    {"code": "F0010", "contains": "Unable to load file"},
])
def test_fresh_binding_rejects_message_predicates_and_mixed_definitions(smoke_package, rule):
    with pytest.raises(ContractError) as caught:
        reproduction.bind({
            "entrypoint": "public_api.entry", "input_conditions": "bug",
            "environment_conditions": "fixed", "expected_json": '{"bug":false}',
            "reported_failure_json": '{"bug":true}',
            "diagnostic_rules": [{"field": "bug", "call_id": "call-1", **rule}],
        }, smoke_package.public, "observed_target()()", "bad-rule",
            observation_channel=probe_invocation.CHANNEL)
    assert {row["path"] for row in caught.value.details["invalid_fields"]} == {
        "/purpose/diagnostic_rules"}


def execute_fixture(root, public, message, *, authored=False):
    root.mkdir()
    (root / "public_api.py").write_text(
        f"def entry(bug):\n    print({message!r} if bug else 'C0114: public control')\n",
        encoding="utf-8")
    source = "target = observed_target()\ntarget(True)\ntarget(False)\n"
    if authored:
        source += "record_observation({'bug': False, 'control': False})\n"
    binding = reproduction.bind({
        "entrypoint": "public_api.entry", "input_conditions": "bug then public control",
        "environment_conditions": "fixed local fixture", "expected_json": DESIRED,
        "reported_failure_json": FAILURE, "diagnostic_rules": copy.deepcopy(RULES),
    }, public, source, "fixture-original", observation_channel=probe_invocation.CANONICAL_CHANNEL)
    process = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", reproduction.program(source, binding)],
        cwd=root, env={**os.environ, "PYTHONPATH": str(root)}, capture_output=True,
        encoding="utf-8", timeout=10, check=False)
    assert process.returncode == 0, process.stderr
    output = {"status": "passed", "exit_code": process.returncode,
              "stdout": process.stdout, "stderr": process.stderr,
              "truncated": False, "timed_out": False, "cleanup_failed": False,
              "deadline_exhausted": False}
    return binding, output


def test_program_without_record_preserves_failure_and_desired_roles(tmp_path, smoke_package):
    for name, message, expected, declared in (
        ("baseline", "F0010: Unable to load file", "mismatched", "matched"),
        ("failed_candidate", "F0010: No module named project", "mismatched", "matched"),
        ("resolved", "W0611: unused import", "matched", "mismatched"),
    ):
        binding, output = execute_fixture(tmp_path / name, smoke_package.public, message)
        value = reproduction.compare(output, binding)["reproduction"]
        assert value["comparison"] == expected, value
        assert value["declared_failure_comparison"] == declared
        assert value["observed_json"] == (DESIRED if name == "resolved" else FAILURE)
        assert value["judgment"]["status"] == "computed"
        assert value["judgment"]["source"] == "host"
        assert value["judgment"]["authored_json"] is None
        assert binding["definition"]["expected_json"] == DESIRED
        assert binding["definition"]["reported_failure_json"] == FAILURE


def test_authored_json_cannot_override_captured_failure(tmp_path, smoke_package):
    binding, output = execute_fixture(
        tmp_path / "stray_authored", smoke_package.public, "F0010: still failing", authored=True)
    value = reproduction.compare(output, binding)["reproduction"]
    assert value["comparison"] == "mismatched"
    assert value["declared_failure_comparison"] == "matched"
    assert value["observed_json"] == FAILURE
    assert value["judgment"]["authored_json"] == DESIRED
    assert value["judgment"]["source"] == "host"


@pytest.mark.parametrize("fault", [
    {"status": "failed", "exit_code": 1}, {"truncated": True},
    {"setup_checks": {"status": "failed"}},
])
def test_failed_or_incomplete_execution_cannot_become_a_resolved_case(
    tmp_path, smoke_package, fault,
):
    binding, output = execute_fixture(tmp_path / "incomplete", smoke_package.public, "")
    output.update(fault)
    value = reproduction.compare(output, binding)["reproduction"]
    assert value["comparison"] == value["declared_failure_comparison"] == "not_compared"
    assert value["judgment"]["status"] == "unknown"
    assert value["judgment"]["host_json"] is None
