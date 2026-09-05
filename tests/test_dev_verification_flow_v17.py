from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_dev_context_v12 import note_call, source_note
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _read, _restart
from test_dev_probes import FakeProbe, probe_call

import patchloop.dev.runner as runner
from patchloop.artifacts import ArtifactStore
from patchloop.dev.contracts import (
    DevLimits,
    DevRunRequest,
    DevToolResult,
    PublicTurnDecision,
    RequestedTool,
)
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.util import sha256_json


def _operation(operation="upsert", *, concern_id=None, statement=None, evidence=None, reason=None):
    return {
        "operation": operation, "concern_id": concern_id, "statement": statement,
        "evidence_action_id": evidence, "reason": reason,
    }


def _update(operations=(), *, question=None, findings=()):
    return {
        "findings": list(findings), "remove_note_ids": [], "open_question": question,
        "verification_updates": list(operations),
    }


def _apply_update(gateway, action_id, update):
    call = note_call(action_id, update)
    payload = gateway.record_working_notes_update([call], turn_id=f"turn-{action_id}")
    assert gateway.execute(call).status == "succeeded"
    return payload


def _add_concern(gateway, action_id="retain-concern"):
    return _apply_update(gateway, action_id, _update([_operation(
        statement="An alternative public input may take an unverified branch.",
    )]))


def _completed_check(gateway, action_id, *, passed=True):
    output = {
        "check_id": "behavior", "passed": passed, "diff_hash": gateway.current_diff_hash,
        "failure_signature": None if passed else "synthetic-public-comparison",
    }
    result = DevToolResult(
        action_id=action_id, input_hash=sha256_json(action_id), tool="run_check",
        status="succeeded", output=output, workspace_diff_hash=gateway.current_diff_hash,
    )
    gateway.journal.append("action_finished", {"result": result.model_dump(mode="json")})
    gateway._remember_check(output)
    return result


def _evidence(gateway, action_id, kind):
    if kind == "check":
        return _completed_check(gateway, action_id)
    gateway.probe_sandbox = FakeProbe(status="passed")
    result = gateway.execute(probe_call(action_id))
    assert result.status == "succeeded"
    assert gateway.probe_sandbox.calls == 1
    return result


def test_concern_survives_focus_failure_source_note_expiry_and_two_mutations(tmp_path):
    gateway = _gateway(tmp_path)
    gateway.public_task.visible_checks = [SimpleNamespace(id="behavior")]
    _read(gateway)
    note = source_note("The observed declaration controls a public value.", 3, 3)
    payload = _apply_update(gateway, "remember", _update(
        [_operation(statement="A distinct input branch still needs public verification.")],
        question="How does the public branch behave?", findings=note["findings"],
    ))
    assert payload["receipt"]["verification"]["unresolved_ids"] == ["v1"]
    assert gateway.working_notes()["findings"]
    first = _mutation(
        "initial-edit", "stable = 'observed mechanism'", "stable = 'revised mechanism'",
    )
    assert gateway.execute(first).status == "succeeded"
    assert gateway.working_notes()["findings"] == []
    _completed_check(gateway, "public-value-failure", passed=False)
    _apply_update(gateway, "change-focus", _update(
        question="Why did the public value comparison fail?",
    ))
    assert gateway.working_notes()["verification"]["unresolved_ids"] == ["v1"]
    _read(gateway, "reobserve")
    assert gateway.execute(_mutation("repair-value")).status == "succeeded"
    _apply_update(gateway, "close-focus", _update(question=None))
    notes = gateway.working_notes()
    assert notes["open_question"] is None
    assert notes["verification"]["unresolved_ids"] == ["v1"]
    assert notes["verification"]["items"][0]["status"] == "unresolved"
    assert gateway.accepted_mutations == 2
    before = gateway.journal.path.read_bytes()
    assert _restart(gateway).working_notes() == notes
    assert gateway.journal.path.read_bytes() == before


@pytest.mark.parametrize("kind", ["check", "probe"])
def test_resolution_requires_current_evidence_and_reopens_after_next_edit(tmp_path, kind):
    gateway = _gateway(tmp_path)
    _read(gateway)
    old_evidence = _evidence(gateway, "before-edit", kind)
    _add_concern(gateway)
    assert gateway.execute(_mutation("initial-edit")).status == "succeeded"
    rejected = _apply_update(gateway, "old-resolution", _update([_operation(
        "resolve", concern_id="v1", evidence=old_evidence.action_id,
        reason="This earlier observation was incorrectly offered for the new candidate.",
    )]))
    assert rejected["receipt"]["verification"]["updates"][0]["status"] == "rejected"
    assert gateway.working_notes()["verification"]["unresolved_ids"] == ["v1"]
    current = _evidence(gateway, "current-evidence", kind)
    applied = _apply_update(gateway, "current-resolution", _update([_operation(
        "resolve", concern_id="v1", evidence=current.action_id,
        reason="The completed public evidence checks the outstanding behavior.",
    )]))
    assert applied["receipt"]["verification"]["updates"][0]["status"] == "applied"
    resolved = gateway.working_notes()["verification"]
    assert resolved["unresolved_ids"] == []
    assert resolved["items"][0]["status"] == "resolved"
    decision = resolved["items"][0]["decision"]
    assert decision["evidence"]["action_id"] == current.action_id
    assert decision["evidence"]["input_hash"] == current.input_hash
    assert decision["diff_hash"] == gateway.current_diff_hash
    assert gateway.execute(_mutation("followup-edit", "editable = 1", "editable = 2")).status == (
        "succeeded"
    )
    reopened = gateway.working_notes()["verification"]
    assert reopened["unresolved_ids"] == ["v1"]
    assert reopened["items"][0]["status"] == "unresolved"
    assert reopened["items"][0]["decision"]["currency"] == "historical"
    assert _restart(gateway).working_notes() == gateway.working_notes()


def test_dismissal_requires_a_reason_and_is_not_permanent_across_edits(tmp_path):
    gateway = _gateway(tmp_path)
    _read(gateway)
    _add_concern(gateway)
    bad = _apply_update(gateway, "unexplained-dismissal", _update([_operation(
        "dismiss", concern_id="v1",
    )]))
    assert bad["receipt"]["verification"]["updates"][0]["status"] == "rejected"
    assert gateway.working_notes()["verification"]["unresolved_ids"] == ["v1"]
    _apply_update(gateway, "explained-dismissal", _update([_operation(
        "dismiss", concern_id="v1", reason="The public scope excludes this assumption.",
    )]))
    assert gateway.working_notes()["verification"]["items"][0]["status"] == "dismissed"
    assert gateway.execute(_mutation("edit")).status == "succeeded"
    assert gateway.working_notes()["verification"]["unresolved_ids"] == ["v1"]


def test_parallel_owner_receipt_delivery_and_restart_replay_are_exactly_once(tmp_path):
    gateway = _gateway(tmp_path)
    calls = [
        note_call("no-update", None),
        note_call("owner", _update([_operation(statement="A public branch remains unverified.")])),
        note_call("ignored", _update([_operation(statement="This second update is ignored.")])),
    ]
    before_calls = [call.model_dump(mode="json") for call in calls]
    turn_id = "parallel"
    gateway.journal.append("turn_started", {"turn_id": turn_id})
    gateway.journal.append("turn_decision_recorded", {
        "turn_id": turn_id, "tool_calls": before_calls,
    })
    payload = gateway.record_working_notes_update(calls, turn_id=turn_id)
    assert payload["verification_state"]["items"][0]["concern_id"] == "v1"
    assert payload["receipt"]["verification"]["available_concern_ids"] == ["v1"]
    assert any(item["code"] == "ignored_additional_memory_updates"
               for item in payload["receipt"]["diagnostics"])
    results = gateway.execute_batch(calls)
    assert all(result.status == "succeeded" for result in results)
    gateway.journal.append("tool_batch_finished", {
        "turn_id": turn_id, "action_ids": [call.action_id for call in calls],
    })
    context = json.dumps({
        "working_notes": gateway.working_notes(),
        "latest_tool_results": [result.model_dump(mode="json") for result in results],
    })
    model_input = runner._build_model_input(
        journal=gateway.journal, artifact_store=ArtifactStore(tmp_path / "artifacts"),
        context=context, latest_tool_results=results,
    )
    outputs = {
        item["call_id"]: json.loads(item["output"])
        for item in model_input if item.get("type") == "function_call_output"
    }
    assert outputs["owner"]["memory_update_result"] == payload["receipt"]
    assert all("memory_update_result" not in outputs[owner] for owner in ["no-update", "ignored"])
    projected = json.loads(model_input[-1]["content"])["working_notes"]
    assert projected["verification"]["unresolved_ids"] == ["v1"]
    assert projected["last_update_result"]["delivery"] == "preceding_function_call_output"
    assert "verification" not in projected["last_update_result"]
    echoed = {
        item["call_id"]: json.loads(item["arguments"])
        for item in model_input if item.get("type") == "function_call"
    }
    for call in calls:
        assert echoed[call.action_id]["turn_decision"] == call.turn_decision.model_dump(mode="json")
    assert [call.model_dump(mode="json") for call in calls] == before_calls
    before = gateway.journal.path.read_bytes()
    restarted = _restart(gateway)
    assert restarted.working_notes() == gateway.working_notes()
    assert restarted.record_working_notes_update(calls, turn_id=turn_id) == payload
    assert all(result.replayed for result in restarted.execute_batch(calls))
    assert gateway.journal.path.read_bytes() == before


def test_invalid_verification_reference_is_nonblocking_and_does_not_echo_raw_content(tmp_path):
    gateway = _gateway(tmp_path)
    _add_concern(gateway)
    invalid_reference = "PRIVATE_REFERENCE_SENTINEL"
    rejected_reason = "PRIVATE_REASON_SENTINEL"
    payload = _apply_update(gateway, "invalid-resolution", _update([_operation(
        "resolve", concern_id="v1", evidence=invalid_reference, reason=rejected_reason,
    )]))
    verification = payload["receipt"]["verification"]
    assert verification["updates"][0]["status"] == "rejected"
    assert invalid_reference not in json.dumps(verification)
    assert rejected_reason not in json.dumps(verification)
    assert gateway.working_notes()["verification"]["unresolved_ids"] == ["v1"]


def test_all_checks_pass_advises_review_but_still_allows_finish_with_concern(tmp_path):
    gateway = _gateway(tmp_path)
    gateway.public_task.visible_checks = [SimpleNamespace(id="behavior")]
    _read(gateway)
    _add_concern(gateway)
    assert gateway.execute(_mutation("edit")).status == "succeeded"
    result = _completed_check(gateway, "checked")
    assert gateway.ready_to_submit()
    policy = runner._tool_policy(gateway, runner._RunCounters(), DevLimits())
    assert "finish_task" in policy.allowed_tools
    card = runner._attempt_card(result, gateway)
    assert card["next_question"] != "Submit the projected diff."
    assert "v1" in json.dumps(card)
    assert "review" in card["next_question"].lower()
    assert "submit" in card["next_question"].lower()
    finish = gateway.execute(RequestedTool(
        name="finish_task", action_id="finish", arguments={},
        turn_decision=PublicTurnDecision(mode="finish", basis="Submit with the recorded caveat."),
    ))
    assert finish.status == "succeeded"
    assert finish.output["patch_hash"] == gateway.current_diff_hash
    assert gateway.working_notes()["verification"]["unresolved_ids"] == ["v1"]


def test_mock_verification_annotations_keep_call_counts_and_native_delivery(tmp_path, monkeypatch):
    class VerifyingMock(MockDevAdapter):
        def next_turn(self, context, tools):
            payload = json.loads(context)
            turn = super().next_turn(context, tools)
            for call in turn.tool_calls:
                call.turn_decision = copy.deepcopy(call.turn_decision)
                call.turn_decision.memory_update = None
            owner = turn.tool_calls[0]
            if owner.name == "search_files":
                update = _update([_operation(statement="The public parser behavior needs review.")])
            elif owner.name == "replace_text":
                assert payload["working_notes"]["verification"]["unresolved_ids"] == ["v1"]
                update = _update(question="Does the public comparison accept the candidate?")
            elif owner.name == "run_check":
                update = _update([_operation(
                    "resolve", concern_id="v1", evidence=owner.action_id,
                    reason="This same-batch check is not completed yet.",
                )])
            else:
                assert payload["working_notes"]["verification"]["unresolved_ids"] == ["v1"]
                current_check = next(
                    result for result in payload["latest_tool_results"]
                    if result["tool"] == "run_check"
                )
                update = _update([_operation(
                    "resolve", concern_id="v1", evidence=current_check["action_id"],
                    reason="The completed public check covers the noted behavior.",
                )])
            owner.turn_decision.memory_update = update
            return turn

    monkeypatch.setattr(runner, "MockDevAdapter", VerifyingMock)
    request = DevRunRequest(
        provider="mock", model="mock-dev", state_root=tmp_path,
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
    )
    run = runner.run_dev(request)["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    assert run["call_counts"] == {"model": 4, "input_count": 0, "tool": 5}
    assert run["evaluator"]["claim_eligible"] is False
    events = DevJournal(tmp_path, run["run_id"]).events()
    updates = [event["payload"] for event in events
               if event["event_type"] == "working_notes_updated"]
    assert len(updates) == 4
    assert updates[0]["receipt"]["verification"]["status"] == "applied"
    assert "verification" not in updates[1]["receipt"]
    assert updates[2]["receipt"]["verification"]["status"] == "rejected"
    assert updates[3]["verification_state"]["items"][0]["decision"]["outcome"] == "resolved"
    turns = [event["payload"] for event in events if event["event_type"] == "turn_started"]
    for turn, update in zip(turns[1:], updates[:3], strict=True):
        items = json.loads(Path(turn["model_input_artifact"]["path"]).read_text(encoding="utf-8"))
        outputs = [json.loads(item["output"]) for item in items
                   if item.get("type") == "function_call_output"]
        receipts = [output["memory_update_result"] for output in outputs
                    if "memory_update_result" in output]
        assert receipts == [update["receipt"]]
        notes = json.loads(items[-1]["content"])["working_notes"]
        assert notes["verification"]["unresolved_ids"] == ["v1"]
        assert notes["last_update_result"]["delivery"] == "preceding_function_call_output"
        assert "verification" not in notes["last_update_result"]
