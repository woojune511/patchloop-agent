"""Completed mutation identity is its post-state, with an explicit pre-state."""

from __future__ import annotations

import json

import pytest
from native_history_support import input_context
from test_dev_completion_v27 import CheckSandbox, _batch, _check
from test_dev_feedback_integration_v18 import _context, _input, _outputs
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _read, _restart

from patchloop.contracts import RegisteredCheck
from patchloop.dev.contracts import DEV_RUN_SCHEMA, RequestedTool, dev_tool_surface_hash
from patchloop.dev.state import DevJournal
from patchloop.repository import WorkspaceManager
from patchloop.util import canonical_json


def _assert_identity(result, before, after):
    assert result.status == "succeeded", result.message
    assert result.workspace_diff_hash == after
    assert result.output["worktree_diff_hash"] == after
    assert result.output["mutation"]["diff_hash"] == after
    assert result.output["mutation_evidence"]["source_diff_hash"] == after
    assert result.output["baseline_diff_hash"] == before
    assert before != after


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_two_mutations_bind_complete_before_and_after_diff_and_replay(tmp_path, newline):
    gateway = _gateway(tmp_path, newline=newline)
    _read(gateway)
    before = gateway.current_diff_hash
    calls = [_mutation("first"), _mutation("second", "editable = 1", "editable = 2")]
    results = []
    for call in calls:
        result = gateway.execute(call)
        after = gateway.current_diff_hash
        _assert_identity(result, before, after)
        admission = next(event["payload"] for event in gateway.journal.events()
                         if event["event_type"] == "action_started"
                         and event["payload"]["action_id"] == call.action_id)
        assert admission["baseline_diff_hash"] == before
        assert admission["mutation_expected_worktree_diff_hash"] == after
        results.append(result)
        before = after
    # The second action's patch is incremental, not the complete candidate identity.
    assert results[-1].output["patch_hash"] != before
    journal_bytes = gateway.journal.path.read_bytes()
    source_bytes = (gateway.workspace / "src.py").read_bytes()
    restored = _restart(gateway)
    for call, result in zip(calls, results, strict=True):
        replay = restored.execute(call)
        assert replay.replayed
        assert replay.model_dump(exclude={"replayed"}) == result.model_dump(exclude={"replayed"})
    assert restored.accepted_mutations == 2
    assert restored.current_diff_hash == before
    assert gateway.journal.path.read_bytes() == journal_bytes
    assert (gateway.workspace / "src.py").read_bytes() == source_bytes


class SimulatedCrash(BaseException):
    pass


@pytest.mark.parametrize("boundary", ["after_admission", "after_replace", "after_result"])
def test_pending_and_completed_mutation_recovery_preserve_both_identities(
    tmp_path, monkeypatch, boundary,
):
    gateway = _gateway(tmp_path)
    _read(gateway)
    gateway.execute(_mutation("baseline"))
    before = gateway.current_diff_hash
    call = _mutation("interrupted", "editable = 1", "editable = 2")
    append = DevJournal.append
    replace = WorkspaceManager.atomic_replace_source
    crashed = False
    writes = 0

    def intercept_append(self, event_type, payload=None):
        nonlocal crashed
        event = append(self, event_type, payload)
        target = "action_started" if boundary == "after_admission" else "action_finished"
        if (not crashed and boundary != "after_replace" and event_type == target
                and payload.get("action_id") == call.action_id):
            crashed = True
            raise SimulatedCrash()
        return event

    def intercept_replace(*args):
        nonlocal crashed, writes
        replace(*args)
        writes += 1
        if not crashed and boundary == "after_replace":
            crashed = True
            raise SimulatedCrash()

    monkeypatch.setattr(DevJournal, "append", intercept_append)
    monkeypatch.setattr(WorkspaceManager, "atomic_replace_source", staticmethod(intercept_replace))
    with pytest.raises(SimulatedCrash):
        gateway.execute(call)
    restored = _restart(gateway)
    result = restored.execute(call)
    _assert_identity(result, before, restored.current_diff_hash)
    assert writes == 1
    assert restored.accepted_mutations == 2
    for event_type in ("action_started", "action_finished"):
        assert sum(event["event_type"] == event_type
                   and event["payload"].get("action_id") == call.action_id
                   for event in restored.journal.events()) == 1
    journal_bytes = restored.journal.path.read_bytes()
    replay = _restart(restored).execute(call)
    assert replay.replayed and writes == 1
    assert replay.model_dump(exclude={"replayed"}) == result.model_dump(exclude={"replayed"})
    assert restored.journal.path.read_bytes() == journal_bytes


def test_failed_candidate_retains_rollback_identity_and_read_cache(tmp_path):
    gateway = _gateway(tmp_path)
    _read(gateway)
    baseline_result = gateway.execute(_mutation("baseline"))
    before = gateway.current_diff_hash
    source_bytes = (gateway.workspace / "src.py").read_bytes()
    gateway.public_task.constraints.max_diff_lines = 2
    read_call = _read(gateway, "baseline-read")
    result = gateway.execute(_mutation(
        "rejected", "editable = 1", "editable = 2\nextra = 3",
    ))
    assert result.status == "failed"
    failure = result.output["mutation_failure"]
    assert failure["class"] == "scope_violation" and failure["rolled_back"]
    assert failure["baseline"]["diff_hash"] == before
    assert failure["candidate"]["diff_hash"] != before
    assert result.workspace_diff_hash == gateway.current_diff_hash == before
    assert "baseline_diff_hash" not in result.output  # Failure's existing typed baseline remains.
    assert (gateway.workspace / "src.py").read_bytes() == source_bytes
    restored = _restart(gateway)
    assert restored.execute(_mutation("baseline")).output == baseline_result.output
    cached = restored.execute(read_call.model_copy(update={"action_id": "cached"}))
    assert cached.evidence_cache_hit and cached.workspace_diff_hash == before
    assert "baseline_diff_hash" not in cached.output


def test_final_unchecked_edit_keeps_consistent_identity_and_available_check_or_stop(tmp_path):
    gateway = _gateway(tmp_path)
    gateway.sandbox = CheckSandbox()
    gateway.public_task.visible_checks = [
        RegisteredCheck(id=name, command=["python", "-c", "pass"])
        for name in ("contract", "regression")
    ]
    _read(gateway)
    _batch(gateway, _mutation("first"), tmp_path)
    _batch(gateway, _check("contract", "old-pass"), tmp_path)
    _batch(gateway, _check("regression", "old-fail"), tmp_path)
    for number in range(2, 5):
        before = gateway.current_diff_hash
        prior_input = _input(gateway, gateway.journal.latest_tool_batch_results(), tmp_path)
        result = _batch(gateway, _mutation(
            f"edit-{number}", f"editable = {number - 1}", f"editable = {number}",
        ), tmp_path)
        canonical = _context(gateway, [result])
        native = _input(gateway, [result], tmp_path, context=canonical)
        assert native[:len(prior_input)] == prior_input
        for output in (_outputs(native)[result.action_id],
                       json.loads(canonical)["latest_tool_results"][0]):
            assert output["workspace_diff_hash"] == gateway.current_diff_hash
            assert output["output"]["baseline_diff_hash"] == before
            assert output["output"]["worktree_diff_hash"] == gateway.current_diff_hash
        assert _input(_restart(gateway), [result], tmp_path, context=canonical) == native
    state = input_context(native)
    assert gateway.accepted_mutations == 4
    assert state["action_horizon"]["completion_possible"] is True
    assert state["action_horizon"]["mutation_completion_horizon"]["minimum_possible"] is False
    assert {"run_check", "stop_task"} <= set(state["available_tool_names"])
    assert "replace_text" not in state["available_tool_names"]
    assert [row["status"] for row in state["visible_check_status"]] == ["NOT_RUN", "NOT_RUN"]
    assert state["current_public_failure"]["evidence_currency"] == "historical"
    assert state["completion_guidance"]["next_action"]["tool"] == "run_check"
    for name in ("contract", "regression"):
        checked = _batch(gateway, _check(name, f"new-{name}"), tmp_path)
        assert checked.output["passed"]
        assert checked.workspace_diff_hash == gateway.current_diff_hash
    finished = _batch(gateway, RequestedTool(
        name="finish_task", action_id="finish", arguments={},
    ), tmp_path)
    assert finished.output["patch_hash"] == gateway.current_diff_hash
    assert finished.workspace_diff_hash == gateway.current_diff_hash


def test_identity_semantics_change_surface_not_tool_inputs_or_run_schema():
    assert DEV_RUN_SCHEMA == "dev-run-v1"
    assert dev_tool_surface_hash() != (
        "sha256:0617d3a20f4e5921b9fddb00cf1e638d0f26adda1982cfe877e8587c9f1116d8"
    )
    # Existing ordered-schema tests pin all tool input shapes and descriptions.
    assert "baseline_diff_hash" not in canonical_json(_mutation("sample").arguments)
