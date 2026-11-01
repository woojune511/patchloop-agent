"""Keep exact public experiments inspectable without granting verification credit."""

from __future__ import annotations

import copy

import pytest
from test_dev_probes import FakeProbe, context, probe_call
from test_dev_tools import mutation_call, read_calls

from patchloop.dev import completion_context, probe_observation, repair_context, runner, segments
from patchloop.dev.conversation import SEGMENT_RULES, assemble_model_input, reconstruct_state
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SOURCE = "value = bytes([1, 2])\nassert isinstance(value, bytes)\nprint(value)\n"
QUESTION = "Does the public caller preserve the supplied bytes?"
DIFF = sha256_bytes(b"candidate")


def bound_pair(*, source=SOURCE, binding=None):
    program = {"question": QUESTION, "python_source": source}
    arguments = (dict(program) if binding is None else
                 {"replay_action_id": "earlier", "question": None, "python_source": None})
    started = {
        "action_id": "probe", "tool": "run_probe", "arguments": arguments,
        "baseline_diff_hash": DIFF,
        "input_hash": sha256_json({"tool": "run_probe", "arguments": arguments}),
    }
    if binding is not None:
        started[binding] = program
    result = {
        "action_id": "probe", "tool": "run_probe", "status": "succeeded",
        "input_hash": started["input_hash"], "workspace_diff_hash": DIFF,
        "output": {"question": QUESTION, "source_hash": sha256_bytes(source.encode()),
                   "diff_hash": DIFF, "status": "failed", "exit_code": 1,
                   "stdout": "False\n", "stderr": "AssertionError\n"},
    }
    return result, started


def probe_record(result, program):
    return {
        "action_id": result["action_id"], "diff_hash": result["workspace_diff_hash"],
        "question": QUESTION, "historical": False, "diagnostic_only": True,
        "program": program, "stdout": result["output"]["stdout"],
        "observation": probe_observation.probe_observation(result),
    }


def exchanges(result, started):
    return [{"type": "function_call", "call_id": started["action_id"],
             "name": started["tool"], "arguments": canonical_json(started["arguments"])},
            {"type": "function_call_output", "call_id": result["action_id"],
             "output": canonical_json(result)}]


@pytest.mark.parametrize("binding", [None, "probe_replay_request", "probe_case_request"])
def test_bound_program_uses_executed_request_and_preserves_assertion(binding):
    result, started = bound_pair(binding=binding)
    result["private_spec"] = started["reasoning"] = "DO_NOT_PROJECT"
    before = copy.deepcopy((result, started))
    program = probe_observation.bound_probe_program(result, started)
    assert program == {"python_source": SOURCE, "source_hash": sha256_bytes(SOURCE.encode())}
    assert (result, started) == before
    assert probe_observation.probe_observation(result)["behavior_verdict"] == "not_assessed"
    assert "DO_NOT_PROJECT" not in canonical_json(program)


@pytest.mark.parametrize("drift", [
    "action_id", "input_hash", "arguments", "tool", "baseline_diff", "output_diff",
    "question", "source_hash", "resolved_source",
])
def test_inconsistent_program_binding_is_not_presented_as_executed(drift):
    result, started = bound_pair(binding="probe_replay_request")
    if drift == "action_id":
        started["action_id"] = "other"
    elif drift == "input_hash":
        result["input_hash"] = sha256_bytes(b"other")
    elif drift == "arguments":
        started["arguments"]["replay_action_id"] = "different"
    elif drift == "tool":
        started["tool"] = "run_check"
    elif drift == "baseline_diff":
        started["baseline_diff_hash"] = "different"
    elif drift == "output_diff":
        result["output"]["diff_hash"] = "different"
    elif drift == "question":
        result["output"]["question"] = "A different question"
    elif drift == "source_hash":
        result["output"]["source_hash"] = sha256_bytes(b"different")
    else:
        started["probe_replay_request"]["python_source"] += "print('changed')\n"
    assert probe_observation.bound_probe_program(result, started) is None


@pytest.mark.parametrize("source", ["", "x" * 8001])
def test_program_bound_does_not_expand_or_truncate_the_execution_contract(source):
    result, started = bound_pair(source=source)
    assert probe_observation.bound_probe_program(result, started) is None


@pytest.mark.parametrize("archived", [False, True])
def test_program_is_referenced_only_when_exact_native_arguments_are_visible(archived):
    result, started = bound_pair()
    program = probe_observation.bound_probe_program(result, started)
    state = {"recent_probes": [probe_record(result, program)]}
    history = exchanges(result, started)
    if archived:
        history = [SEGMENT_RULES.archive(exchanges=history)]
    view = compact_model_state(state, history, archive_kind=PUBLIC_EVIDENCE_KIND)
    retained = view["recent_probes"][0]
    assert retained["program"] == {
        "source_hash": program["source_hash"], "delivery": "preceding_function_call_arguments",
    }
    assert retained["observation"]["behavior_verdict"] == "not_assessed"
    assert state["recent_probes"][0]["program"]["python_source"] == SOURCE


@pytest.mark.parametrize("delivery", [
    "absent", "result_only", "replay", "different_source", "different_question",
    "different_action", "different_tool",
])
def test_missing_or_nonmatching_native_program_keeps_exact_inline_body(delivery):
    binding = "probe_replay_request" if delivery == "replay" else None
    result, started = bound_pair(binding=binding)
    program = probe_observation.bound_probe_program(result, started)
    state = {"recent_probes": [probe_record(result, program)]}
    history = exchanges(result, started)
    if delivery == "absent":
        history = []
    elif delivery == "result_only":
        history = history[1:]
    elif delivery == "different_source":
        history[0]["arguments"] = canonical_json({"question": QUESTION, "python_source": "pass"})
    elif delivery == "different_question":
        history[0]["arguments"] = canonical_json({"question": "Different", "python_source": SOURCE})
    elif delivery == "different_action":
        history[0]["call_id"] = "other"
    elif delivery == "different_tool":
        history[0]["name"] = "run_check"
    view = compact_model_state(state, history)
    assert view["recent_probes"][0]["program"] == program


def test_completion_keeps_historical_program_identity_without_old_verdict_or_output():
    result, started = bound_pair()
    program = probe_observation.bound_probe_program(result, started)
    old = probe_record(result, program)
    old.update(historical=True, diff_hash="old-diff", stdout="OLD_BULK_OUTPUT", exit_code=0)
    current = {**probe_record(result, program), "action_id": "current-probe"}
    state = {
        "public_task": {"task_id": "public-fixture"}, "workflow_gate": "ready_to_submit",
        "current_diff": {"patch_hash": DIFF}, "recent_probes": [old, current],
        "visible_check_status": [{"check_id": "base", "status": "PASS", "diff_hash": DIFF}],
        "available_tool_names": ["finish_task", "stop_task"],
    }
    before = copy.deepcopy(state)
    projected = completion_context.project(state)
    historical, latest = projected["recent_probes"]
    assert historical["program"] == program
    assert historical["historical"] is True and historical["diff_hash"] == "old-diff"
    for key in ("stdout", "stderr", "exit_code", "observation", "passed", "status"):
        assert key not in historical
    assert latest["observation"]["behavior_verdict"] == "not_assessed"
    assert latest["stdout"] == "False\n"
    assert projected["visible_check_status"] == state["visible_check_status"]
    assert "OLD_BULK_OUTPUT" not in canonical_json(projected)
    assert state == before


def test_completion_reprojection_counts_only_wholly_omitted_historical_rows():
    result, started = bound_pair()
    program = probe_observation.bound_probe_program(result, started)
    retained = {**probe_record(result, program), "historical": True, "diff_hash": "old-diff"}
    legacy = {"action_id": "legacy-probe", "historical": True,
              "diff_hash": "older-diff", "stdout": "UNRETAINED_LEGACY_OUTPUT"}
    state = {
        "public_task": {"task_id": "public-fixture"}, "workflow_gate": "ready_to_submit",
        "current_diff": {"patch_hash": DIFF}, "recent_probes": [retained, legacy],
        "available_tool_names": ["finish_task", "stop_task"],
    }
    first = completion_context.project(state)
    second = completion_context.project(first)
    assert first["completion_stage"]["omitted_historical_records"]["recent_probes"] == 1
    assert len(first["recent_probes"]) == 1
    assert first["recent_probes"][0]["program"] == program
    assert "UNRETAINED_LEGACY_OUTPUT" not in canonical_json(first)
    assert second == first


@pytest.mark.parametrize("stage", ["current", "repair", "completion"])
def test_real_gateway_program_survives_fresh_segment_without_native_probe(
    gateway_factory, smoke_package, stage,
):
    gateway, journal, _ = gateway_factory()
    gateway.probe_sandbox = FakeProbe(status="failed")
    call = probe_call()
    call.arguments.update(question=QUESTION, python_source=SOURCE)
    result = gateway.execute(call)
    gateway.execute_batch(read_calls())
    before_journal = journal.path.read_bytes()
    state = context(gateway, smoke_package)
    expected = {"python_source": SOURCE, "source_hash": sha256_bytes(SOURCE.encode())}
    assert state["recent_probes"][0]["program"] == expected
    if stage == "repair":
        state = repair_context.project({**state, "workflow_gate": "needs_mutation"})
    elif stage == "completion":
        state = completion_context.project({**state, "workflow_gate": "ready_to_submit"})
    # This is the production fresh-segment delivery path; the previous probe's
    # native arguments are absent, and only the public state can carry the body.
    base = runner._segment_public_base("Public fixture", state, [], [])
    view = runner._segment_current_view(state, base, [])
    items = assemble_model_input(system_prompt="Public fixture", state=view, history=[],
                                 previous_input=base, context_policy=segments.POLICY)
    actual = reconstruct_state(items, context_policy=segments.POLICY)
    assert actual["recent_probes"][0]["program"] == expected
    assert actual["recent_probes"][0]["observation"]["behavior_verdict"] == "not_assessed"
    assert not any(item.get("type") == "function_call" for item in items)
    assert actual["visible_check_status"] == state["visible_check_status"]
    assert gateway.checks_by_diff == {} and gateway.probe_sandbox.calls == 1
    assert result.output["status"] == "failed" and journal.path.read_bytes() == before_journal


def test_recent_bound_remains_three_and_edit_does_not_upgrade_original_program(
    gateway_factory, smoke_package,
):
    gateway, _, _ = gateway_factory()
    gateway.probe_sandbox = FakeProbe(status="passed")
    for number in range(4):
        call = probe_call(f"probe-{number}")
        call.arguments.update(question=f"Public question {number}",
                              python_source=f"print({number})")
        assert gateway.execute(call).status == "succeeded"
    gateway.execute_batch(read_calls())
    assert gateway.execute(mutation_call(gateway)).status == "succeeded"
    state = context(gateway, smoke_package)
    assert [row["action_id"] for row in state["recent_probes"]] == ["probe-1", "probe-2", "probe-3"]
    for number, row in enumerate(state["recent_probes"], 1):
        assert row["program"]["python_source"] == f"print({number})"
        assert row["historical"] is True and row["diagnostic_only"] is True
        assert row["observation"]["behavior_verdict"] == "not_assessed"
    assert gateway.checks_by_diff == {} and state["remaining_visible_check_ids"]
