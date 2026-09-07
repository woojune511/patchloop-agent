"""Public synthetic execution is not automatic semantic verification."""

from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest
from native_history_support import input_context
from test_dev_completion_v27 import _batch
from test_dev_feedback_integration_v18 import _context, _input, _outputs
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _read, _restart
from test_dev_probes import FakeProbe, probe_call

import patchloop.dev.runner as runner
from patchloop.dev.contracts import DevLimits, PublicTurnDecision, RequestedTool
from patchloop.dev.model import DEV_SYSTEM_PROMPT
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.probe_observation import probe_observation, project_probe_result
from patchloop.dev.tools import dev_tool_schemas
from patchloop.sandbox.execution_feedback import make_request, public_feedback
from patchloop.util import canonical_json, sha256_bytes


def _result(*, status="passed", observed=(10, 11, 12), collected=True):
    targets = make_request("public-diff", [{
        "path": "public_module.py", "file_hash": sha256_bytes(b"public source"),
        "changed_lines": list(range(10, 16)),
    }], execution_identity=None, omitted_file_count=0, deleted_line_count=0)
    report = {"request_hash": targets["request_hash"], "files": [{
        "index": 0, "status": "collected", "executable": list(range(10, 16)),
        "executed": list(observed),
    }]} if collected else None
    return {
        "action_id": "public-probe", "tool": "run_probe", "status": "succeeded",
        "output": {
            "status": status, "exit_code": 0 if status == "passed" else 1,
            "stdout": "False\n", "stderr": "", "question": "Does the edge preserve the value?",
            "diff_hash": targets["diff_hash"],
            "public_execution": public_feedback(targets, report),
        },
    }


@pytest.mark.parametrize("stdout", ["False\n", "ERR ValueError\n", "expected\n"])
def test_normal_exit_is_not_a_behavior_pass_and_body_is_preserved(stdout):
    result = _result()
    result["output"]["stdout"] = stdout
    before = copy.deepcopy(result)
    projected = project_probe_result(result)
    assert result == before
    assert projected["status"] == "succeeded"
    assert projected["observation"]["execution_status"] == "completed"
    assert projected["observation"]["behavior_verdict"] == "not_assessed"
    assert projected["output"] == {key: value for key, value in result["output"].items()
                                   if key != "status"}
    encoded = canonical_json(projected)
    assert encoded.index('"observation":') < encoded.index('"output":')
    assert '"passed"' not in encoded
    lines = projected["observation"]["line_entry_observation"]["files"][0]
    assert lines["observed_ranges"] == [[10, 12]]
    assert lines["not_observed_ranges"] == [[13, 15]]
    assert lines["observed_changed_line_count"] == 3
    assert lines["not_observed_changed_line_count"] == 3


@pytest.mark.parametrize("status", ["failed", "timeout", "output_limit", "cleanup_failed"])
def test_execution_failures_keep_their_identity_without_a_semantic_verdict(status):
    observation = probe_observation(_result(status=status, collected=False))
    assert observation["execution_status"] == status
    assert observation["behavior_verdict"] == "not_assessed"
    lines = observation["line_entry_observation"]["files"][0]
    assert lines["observed_ranges"] is None
    assert lines["not_observed_ranges"] is None
    assert lines["not_observed_changed_line_count"] is None


@pytest.mark.parametrize("hits", [(), tuple(range(10, 16))])
def test_no_hits_or_all_hits_do_not_certify_or_falsify_behavior(hits):
    observation = probe_observation(_result(observed=hits))
    assert observation["behavior_verdict"] == "not_assessed"
    assert observation["line_entry_observation"]["files"][0][
        "observed_changed_line_count"
    ] == len(hits)


def test_summary_is_bounded_allowlisted_and_keeps_unknown_distinct_from_zero():
    result = _result()
    feedback = result["output"]["public_execution"]
    file = feedback["files"][0]
    file.update(executed_changed_ranges=[[n, n] for n in range(10, 30, 2)],
                private_spec="PRIVATE_SENTINEL", reasoning="REASONING_SENTINEL")
    feedback["files"] = [copy.deepcopy(file) for _ in range(6)]
    feedback["files"][1]["status"] = "unknown"
    feedback["omitted_file_count"] = 2
    summary = probe_observation(result)
    observed = summary["line_entry_observation"]
    assert len(observed["files"]) == 4 and observed["omitted_file_count"] == 4
    first = observed["files"][0]
    assert first["observed_ranges"] == [[10, 10], [12, 12], [14, 14]]
    assert first["observed_changed_line_count"] == 10
    assert first["observed_omitted_range_count"] == 7
    assert observed["files"][1]["observed_ranges"] is None
    assert "SENTINEL" not in canonical_json(summary)
    assert len(canonical_json(summary).encode()) < 4000
    not_run = probe_observation({"status": "failed", "output": {}})
    assert not_run["execution_status"] == "not_run"
    assert not_run["line_entry_observation"]["status"] == "unknown"
    assert not_run["line_entry_observation"]["files"] == []


def test_check_verdict_and_other_tools_are_not_relabelled():
    result = _result()
    result["tool"] = "run_check"
    result["output"]["passed"] = True
    assert project_probe_result(result) == result
    assert "observation" not in result


@pytest.mark.parametrize("has_observation", [False, True])
def test_missing_native_observation_keeps_inline_fallback(has_observation):
    result = _result()
    record = {"action_id": result["action_id"], "diff_hash": "public-diff"}
    if has_observation:
        record["observation"] = probe_observation(result)
    history = [{"type": "function_call_output", "call_id": result["action_id"],
                "output": canonical_json(result)}]
    view = compact_model_state({"recent_probes": [record]}, history)
    assert view["recent_probes"][0].get("observation") == record.get("observation")


class ObservedProbe(FakeProbe):
    supports_public_execution = True

    def run_probe(self, workspace, question, python_source, *, execution_targets, **kwargs):
        output = super().run_probe(workspace, question, python_source, **kwargs)
        lines = execution_targets["files"][0]["changed_lines"]
        output["stdout"] = "False\n"
        output["public_execution"] = public_feedback(execution_targets, {
            "request_hash": execution_targets["request_hash"], "files": [{
                "index": 0, "status": "collected", "executable": lines, "executed": lines[:1],
            }],
        })
        return output


def test_actual_native_projection_restart_and_historical_probe_keep_evidence(tmp_path):
    gateway = _gateway(tmp_path)
    gateway.probe_sandbox = ObservedProbe(status="passed")
    _read(gateway)
    edit = _batch(gateway, _mutation("edit", new="editable = 1\nother_value = 2"), tmp_path)
    before_input = _input(gateway, [edit], tmp_path)
    before_tools = runner._tool_policy(gateway, runner._RunCounters(), DevLimits()).allowed_tools
    result = _batch(gateway, probe_call(), tmp_path)
    raw = result.model_dump(mode="json", exclude={"replayed"})
    context = json.loads(_context(gateway, [result]))
    items = _input(gateway, [result], tmp_path)
    native = _outputs(items)[result.action_id]
    assert native == context["latest_tool_results"][0] == project_probe_result(raw)
    assert items[:len(before_input)] == before_input
    assert input_context(items)["recent_probes"][0]["observation"] == {
        "execution_status": "completed", "behavior_verdict": "not_assessed",
        "details_delivery": "preceding_function_call_output.observation",
    }
    assert result.output["status"] == "passed" and result.output["stdout"] == "False\n"
    assert gateway.checks_by_diff == {} and gateway.working_notes()["findings"] == []
    assert before_tools == runner._tool_policy(
        gateway, runner._RunCounters(), DevLimits(),
    ).allowed_tools
    journal_bytes = gateway.journal.path.read_bytes()
    restarted = _restart(gateway)
    restarted.probe_sandbox = gateway.probe_sandbox
    assert restarted.execute(probe_call()).replayed
    assert _input(restarted, [result], tmp_path) == items
    assert gateway.journal.path.read_bytes() == journal_bytes
    assert gateway.probe_sandbox.calls == 1
    later = _batch(gateway, _mutation("later-edit", "editable = 1", "editable = 2"), tmp_path)
    after = _input(gateway, [later], tmp_path)
    assert after[:len(items)] == items
    assert _outputs(after)[result.action_id] == native
    view = input_context(after)
    assert view["recent_probes"][0]["historical"]
    assert view["recent_probes"][0]["observation"]["behavior_verdict"] == "not_assessed"
    assert view["public_execution_summary"]["files"] == []
    finish = _batch(gateway, RequestedTool(
        name="finish_task", action_id="finish", arguments={},
        turn_decision=PublicTurnDecision(mode="finish", basis="Submit the eligible candidate."),
    ), tmp_path)
    assert finish.output["patch_hash"] == gateway.current_diff_hash


@pytest.mark.parametrize("probe_available", [True, False])
def test_submission_remains_available_without_required_probe_or_review(probe_available):
    allowed = {"finish_task", "stop_task"} | ({"run_probe"} if probe_available else set())
    snapshot = SimpleNamespace(
        diff=SimpleNamespace(patch_hash="current"), ready_to_submit=True,
        visible_check_status=({"check_id": "public", "status": "PASS"},),
    )
    policy = SimpleNamespace(workflow_gate="ready_to_submit", allowed_tools=allowed)
    guidance = runner._completion_guidance(snapshot, policy)
    assert guidance["submission_ready"] and guidance["next_action"] == {"tool": "finish_task"}
    assert "not proof of untested behavior" in guidance["message"]
    assert ("run_probe" in guidance["message"]) is probe_available
    assert len(canonical_json(guidance)) < 650


def test_experiment_guidance_is_generic_optional_and_uses_existing_inputs():
    schema = dev_tool_schemas(finish_enabled=False, allowed_tools=frozenset({"run_probe"}))[0]
    assert "public input variation" in schema["description"]
    assert "expected observation" in schema["description"]
    assert "normal exit, not behavior verified" in schema["description"]
    assert set(schema["parameters"]["properties"]) == {"question", "python_source", "turn_decision"}
    assert "No separate review call or annotation is required" in DEV_SYSTEM_PROMPT
    assert len(DEV_SYSTEM_PROMPT) <= 8007
    for task_specific in ("pyfakefs", "makedirs", "0o700", "ENOTDIR"):
        assert task_specific not in schema["description"] + DEV_SYSTEM_PROMPT
