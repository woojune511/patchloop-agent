"""Diagnostic extraction controls; no provider, Docker or target benchmark."""

from __future__ import annotations

import copy
import json

import pytest
from test_probe_invocation import execute

from patchloop.dev import probe_invocation, probe_judgment, reproduction
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes, sha256_json

RULES = [
    {"field": "bug", "call_id": "call-1", "contains": "F0010"},
    {"field": "control", "call_id": "call-2", "contains": "F0010"},
]
DESIRED = canonical_json({"bug": False, "control": False})
FAILURE = canonical_json({"bug": True, "control": False})


def trace(stdout="", stderr=""):
    return {"incomplete": False, "calls": [
        {"call_id": "call-1", "outcome": "returned", "exception": None,
         "exception_policy": [], "capture": {"scope": "python-streams",
         "status": "complete", "stdout": stdout, "stderr": stderr}},
        {"call_id": "call-2", "outcome": "returned", "exception": None,
         "exception_policy": [], "capture": {"scope": "python-streams",
         "status": "complete", "stdout": "W0611: unused import", "stderr": ""}},
    ]}


def intent():
    return {"entrypoint": "public_api.entry", "input_conditions": "bug and control",
            "environment_conditions": "fixed", "expected_json": DESIRED,
            "reported_failure_json": FAILURE, "diagnostic_rules": copy.deepcopy(RULES)}


@pytest.mark.parametrize("channel", ["stdout", "stderr"])
def test_wrong_no_error_value_conflicts_with_either_complete_stream(channel):
    value = trace(**{channel: "file.py:1:0: F0010: parse error"})
    result = probe_judgment.evaluate(RULES, value, DESIRED)
    assert result["status"] == "conflict" and result["reason"] == "observation_conflict"
    assert result["host_json"] == FAILURE and result["authored_json"] == DESIRED
    assert result["witnesses"][0]["matches"] == [
        {"channel": channel, "character_offset": 13, "text": "F0010"}]
    assert result["witnesses"][1]["matches"] == []


def test_both_streams_and_controls_retain_separate_witnesses():
    result = probe_judgment.evaluate(RULES, trace("F0010", "F0010"), FAILURE)
    assert result["status"] == "consistent" and result["host_json"] == FAILURE
    assert [m["channel"] for m in result["witnesses"][0]["matches"]] == ["stdout", "stderr"]
    assert result["witnesses"][1]["matches"] == []
    assert result["rules_hash"] == sha256_json(RULES)


@pytest.mark.parametrize("text", ["", "C0114: missing docstring", "F001: different code"])
def test_complete_absence_and_unrelated_diagnostics_are_false(text):
    result = probe_judgment.evaluate(RULES, trace(text, "W0611: warning"), DESIRED)
    assert result["status"] == "consistent" and result["host_json"] == DESIRED


def test_do_not_concatenate_streams_or_take_a_different_calls_diagnostic():
    value = trace("F00", "10")
    value["calls"][1]["capture"]["stdout"] = "F0010"
    result = probe_judgment.evaluate(RULES, value, canonical_json({"bug": False, "control": True}))
    assert result["status"] == "consistent"
    assert result["witnesses"][0]["matches"] == []
    assert result["witnesses"][1]["matches"][0]["channel"] == "stdout"


@pytest.mark.parametrize("fault", ["truncated", "missing", "wrong_scope", "missing_stream",
                                  "incomplete_call", "incomplete_trace", "raised", "duplicate"])
def test_incomplete_or_unobserved_captures_never_become_false(fault):
    value = trace("F0010")
    call = value["calls"][0]
    if fault == "truncated":
        call["capture"]["status"] = "truncated"
    elif fault == "missing":
        value["calls"] = value["calls"][1:]
    elif fault == "wrong_scope":
        call["capture"]["scope"] = "whole-probe"
    elif fault == "missing_stream":
        call["capture"].pop("stderr")
    elif fault == "incomplete_call":
        call["outcome"] = "incomplete"
    elif fault == "incomplete_trace":
        value["incomplete"] = True
    elif fault == "raised":
        call.update(outcome="raised", exception={"type": "RuntimeError"})
    else:
        value["calls"].append(copy.deepcopy(call))
    result = probe_judgment.evaluate(RULES, value, DESIRED)
    assert result["status"] == "unknown" and result["host_json"] is None
    assert result["witnesses"] == []


def test_execution_failure_precedes_an_apparent_judgment_conflict():
    result = probe_judgment.evaluate(RULES, trace("F0010"), DESIRED, reason="setup_check_failed")
    assert result["status"] == "unknown" and result["reason"] == "setup_check_failed"
    assert result["host_json"] is None


def test_authored_integer_cannot_equal_a_host_boolean():
    result = probe_judgment.evaluate(RULES, trace("F0010"), '{"bug":1,"control":false}')
    assert result["status"] == "conflict" and result["host_json"] == FAILURE


@pytest.mark.parametrize("fault", ["integer", "extra", "missing", "duplicate_field",
                                  "invalid_call", "empty_literal", "empty_rules"])
def test_rule_declarations_require_exact_boolean_fields(smoke_package, fault):
    raw = intent()
    if fault in {"integer", "extra", "missing"}:
        raw["expected_json"] = {"integer": '{"bug":0,"control":false}',
                                "extra": '{"bug":false,"control":false,"extra":false}',
                                "missing": '{"bug":false}'}[fault]
    elif fault == "duplicate_field":
        raw["diagnostic_rules"][1]["field"] = "bug"
    elif fault == "invalid_call":
        raw["diagnostic_rules"][0]["call_id"] = "call-5"
    elif fault == "empty_literal":
        raw["diagnostic_rules"][0]["contains"] = ""
    else:
        raw["diagnostic_rules"] = []
    with pytest.raises(ContractError):
        reproduction.bind(raw, smoke_package.public, "pass", "a",
                          observation_channel=probe_invocation.CHANNEL)


def test_provider_schema_is_inline_nullable_and_strict():
    value = reproduction.purpose_schema()["anyOf"][1]
    assert "$ref" not in json.dumps(value) and "$defs" not in value
    assert set(value["properties"]) == set(value["required"])
    rules = value["properties"]["diagnostic_rules"]
    assert rules["anyOf"][1] == {"type": "null"}
    assert rules["anyOf"][0]["items"]["additionalProperties"] is False


def test_omitted_and_null_new_fields_preserve_old_binding_identity(smoke_package):
    raw = intent()
    raw.pop("diagnostic_rules")
    old = reproduction.bind(raw, smoke_package.public, "pass", "old",
                            observation_channel=probe_invocation.CHANNEL)
    nulls = reproduction.bind({**raw, "diagnostic_rules": None, "corrects_action_id": None},
                              smoke_package.public, "pass", "null",
                              observation_channel=probe_invocation.CHANNEL)
    public = smoke_package.public.model_dump(mode="json")
    expected = {**raw, "public_task_hash": sha256_json(public),
                "requirement_source": {"field": "issue", "issue_hash": sha256_json(
                    smoke_package.public.issue.model_dump(mode="json"))},
                "observation_channel": probe_invocation.CHANNEL}
    assert old["definition"] == nulls["definition"] == expected
    assert old["case_id"] == nulls["case_id"] == sha256_json({
        "definition": expected, "program_hash": sha256_bytes(b"pass")})


@pytest.mark.parametrize("authored,expected", [(DESIRED, "not_compared"), (FAILURE, "mismatched")])
def test_captured_execution_is_compared_only_after_host_agreement(tmp_path, authored, expected):
    original = execute(tmp_path / "capture", source=(
        "call = observed_target()()\nrecord_observation(True)"),
        implementation='print("F0010")', parameters="", channel=probe_invocation.CHANNEL)
    binding = copy.deepcopy(original["binding"])
    binding["definition"].update(diagnostic_rules=RULES[:1],
                                  expected_json='{"bug":false}',
                                  reported_failure_json='{"bug":true}')
    recorded = canonical_json({"bug": json.loads(authored)["bug"]})
    frame = {"calls": original["call_observation"]["calls"], "incomplete": False,
             "observation": {"count": 1, "call_count": 1, "json": recorded, "error": None}}
    output = {"status": "passed", "exit_code": 0, "stdout": "outside progress F0010",
              "stderr": reproduction.marker(binding) + json.dumps(frame)}
    result = reproduction.compare(output, binding)["reproduction"]
    assert result["comparison"] == expected
    assert result["judgment"]["host_json"] == '{"bug":true}'
    if expected == "not_compared":
        assert result["reason"] == "observation_conflict"
        assert result["declared_failure_comparison"] == "not_compared"
        assert "comparison_feedback" not in result
        assert result["observed_json"] == '{"bug":false}'
    else:
        assert result["declared_failure_comparison"] == "matched"
        assert result["judgment"]["status"] == "consistent"
    binding["definition"].pop("diagnostic_rules")
    output["stderr"] = reproduction.marker(binding) + json.dumps(frame)
    legacy = reproduction.compare(output, binding)["reproduction"]
    assert "judgment" not in legacy
    assert legacy["comparison"] == ("matched" if expected == "not_compared" else "mismatched")
