from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from test_dev_context_v12 import note_call, observe, source_note
from test_dev_context_v12 import source_gateway as source_gateway

import patchloop.dev.runner as runner
from patchloop.artifacts import ArtifactStore
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.model import DEV_SYSTEM_PROMPT, MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.dev.working_notes import memory_update_schema
from patchloop.runtime import repository_root


def tool_note(action_id: str, *, note_id: str | None = None) -> dict:
    update = source_note("A preceding public observation informs the next action.")
    update["findings"][0]["note_id"] = note_id
    update["findings"][0]["evidence"] = [{
        "kind": "tool_result", "action_id": action_id,
    }]
    return update


def restore(gateway, tracked):
    restored = DevToolGateway(
        workspace=gateway.workspace, public_task=gateway.public_task,
        sandbox=None, journal=gateway.journal, limits=gateway.limits,
    )
    restored._tracked_path = tracked
    return restored


def test_row22_rejected_reference_then_unknown_id_recovers_without_blocking_actions(
    source_gateway,
):
    gateway, _, tracked = source_gateway
    attempts = [
        ("first", tool_note("pending")),
        ("second", tool_note("first", note_id="n1")),
        ("third", tool_note("first")),
    ]
    receipts = []
    for action_id, update in attempts:
        call = note_call(action_id, update)
        payload = gateway.record_working_notes_update([call], turn_id=action_id)
        receipt = payload["receipt"]
        receipts.append(receipt)
        assert receipt["action_id"] == action_id
        assert receipt["turn_id"] == action_id
        assert gateway.execute(call).status == "succeeded"
        assert gateway.working_notes()["last_update_result"] == receipt

    for receipt in receipts[:2]:
        assert receipt["status"] in {"rejected", "partially_applied"}
        assert receipt["findings"][0]["finding_index"] == 0
        assert receipt["findings"][0]["status"] == "rejected"
        assert receipt["findings"][0]["code"]
        assert receipt["findings"][0]["message"]
        assert receipt["note_ids_after_update"] == []
    unknown = receipts[1]["findings"][0]
    assert unknown["code"] == "unknown_note_id"
    assert unknown["note_id"] == "n1"
    assert "null" in unknown["message"]
    assert json.dumps(receipts[1]).count(unknown["message"]) == 1
    assert receipts[2]["status"] == "applied"
    assert receipts[2]["findings"][0]["status"] == "created"
    assert receipts[2]["findings"][0]["note_id"] == "n1"
    assert receipts[2]["note_ids_after_update"] == ["n1"]
    assert len(gateway.working_notes()["findings"]) == 1

    before = gateway.journal.path.read_bytes()
    restored = restore(gateway, tracked)
    assert restored.working_notes() == gateway.working_notes()
    replay = restored.record_working_notes_update(
        [note_call("third", attempts[-1][1])], turn_id="third",
    )
    assert replay["receipt"] == receipts[-1]
    assert gateway.journal.path.read_bytes() == before


def test_first_nonnull_update_owns_parallel_receipt_and_ignored_update_is_reported(
    source_gateway,
):
    gateway, _, _ = source_gateway
    observe(gateway, "src.py", 1, 4)
    calls = [
        note_call("no-update", None),
        note_call("owner", source_note()),
        note_call("ignored", source_note("Do not silently apply this second update.")),
    ]
    payload = gateway.record_working_notes_update(calls, turn_id="parallel")
    receipt = payload["receipt"]
    assert receipt["action_id"] == "owner"
    assert receipt["note_ids_after_update"] == ["n1"]
    assert len(receipt["findings"]) == 1
    assert "ignored_additional_memory_updates" in {
        diagnostic["code"] for diagnostic in receipt["diagnostics"]
    }
    assert all(diagnostic["message"] for diagnostic in receipt["diagnostics"])
    assert all(result.status == "succeeded" for result in gateway.execute_batch(calls))
    assert len(gateway.working_notes()["findings"]) == 1


def test_partial_receipt_identifies_each_finding_without_losing_valid_question(source_gateway):
    gateway, _, _ = source_gateway
    observe(gateway, "src.py", 1, 4)
    update = source_note()
    update["findings"].append(tool_note("never-observed")["findings"][0])
    payload = gateway.record_working_notes_update(
        [note_call("partial", update)], turn_id="partial",
    )
    receipt = payload["receipt"]
    assert receipt["status"] == "partially_applied"
    assert [(item["finding_index"], item["status"]) for item in receipt["findings"]] == [
        (0, "created"), (1, "rejected"),
    ]
    assert receipt["note_ids_after_update"] == ["n1"]
    assert receipt["open_question_applied"] is True
    assert gateway.working_notes()["open_question"] == update["open_question"]


@pytest.mark.parametrize("invalid_kind", ["shape", "source", "tool_result"])
def test_receipt_does_not_echo_rejected_raw_notes_or_private_looking_references(
    source_gateway, invalid_kind,
):
    gateway, _, _ = source_gateway
    statement = "PRIVATE_NOTE_SENTINEL"
    reference = ".patchloop-hidden/PRIVATE_REFERENCE_SENTINEL.py"
    if invalid_kind == "shape":
        update = {"raw_reasoning": statement, "private_path": reference}
    else:
        update = source_note(statement)
        evidence = (
            {"kind": "source", "path": reference, "start_line": 1, "end_line": 2}
            if invalid_kind == "source"
            else {"kind": "tool_result", "action_id": reference}
        )
        update["findings"][0]["evidence"] = [evidence]
    call = note_call(f"invalid-{invalid_kind}", update)
    payload = gateway.record_working_notes_update([call], turn_id=call.action_id)
    receipt = payload["receipt"]
    serialized = json.dumps(receipt)
    assert statement not in serialized
    assert reference not in serialized
    assert "raw_reasoning" not in serialized
    assert receipt["note_ids_after_update"] == []
    assert len(receipt["findings"]) <= 2
    assert len(receipt["diagnostics"]) <= 12
    assert all(len(item["message"]) <= 500 for item in receipt["diagnostics"])
    if invalid_kind == "shape":
        assert receipt["status"] == "rejected"
        assert receipt["open_question_applied"] is False
    else:
        assert receipt["findings"][0]["status"] == "rejected"
    assert gateway.execute(call).status == "succeeded"


def test_question_before_observation_and_null_update_have_distinct_effects(source_gateway):
    gateway, _, _ = source_gateway
    question = "Which public branch determines the behavior?"
    update = {"findings": [], "remove_note_ids": [], "open_question": question}
    receipt = gateway.record_working_notes_update(
        [note_call("question", update)], turn_id="question",
    )["receipt"]
    assert receipt["status"] == "applied"
    assert receipt["findings"] == []
    assert receipt["open_question_applied"] is True
    before = gateway.journal.path.read_bytes()
    gateway.record_working_notes_update([note_call("none", None)], turn_id="none")
    assert gateway.working_notes()["open_question"] == question
    assert gateway.working_notes()["last_update_result"] == receipt
    assert gateway.journal.path.read_bytes() == before


def test_native_parallel_receipt_is_attached_once_without_echoing_annotation(
    source_gateway, tmp_path,
):
    gateway, _, _ = source_gateway
    calls = [
        note_call("no-update", None),
        note_call("owner", tool_note("pending")),
        note_call("ignored", tool_note("pending")),
    ]
    turn_id = "native-parallel"
    from native_history_support import start_turn

    start_turn(gateway.journal, ArtifactStore(tmp_path / "artifacts"), turn_id)
    gateway.journal.append("turn_decision_recorded", {
        "turn_id": turn_id, "tool_calls": [call.model_dump(mode="json") for call in calls],
    })
    payload = gateway.record_working_notes_update(calls, turn_id=turn_id)
    results = gateway.execute_batch(calls)
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
    assert "memory_update_result" not in outputs["no-update"]
    assert "memory_update_result" not in outputs["ignored"]
    for output in outputs.values():
        assert output["status"] == "succeeded"
        assert "memory_update" not in output["output"].get("inspection_intent", {})
    echoed_arguments = {
        item["call_id"]: json.loads(item["arguments"])
        for item in model_input if item.get("type") == "function_call"
    }
    for call in calls:
        assert echoed_arguments[call.action_id]["turn_decision"] == (
            call.turn_decision.model_dump(mode="json")
        )
    notes = json.loads(model_input[1]["content"])["working_notes"]
    assert notes["last_update_result"]["action_id"] == "owner"
    assert notes["last_update_result"]["delivery"] == "preceding_function_call_output"
    assert "findings" not in notes["last_update_result"]
    assert "last_update_diagnostics" not in notes


def test_mock_row_recovers_notes_via_native_receipts_without_extra_model_or_tool_calls(
    tmp_path: Path, monkeypatch,
):
    class NotingMock(MockDevAdapter):
        def next_turn(self, context, tools):
            turn = super().next_turn(context, tools)
            # The stock mock shares its decision instance across its first two reads.
            for call in turn.tool_calls:
                call.turn_decision = copy.deepcopy(call.turn_decision)
                call.turn_decision.memory_update = None
            owner = turn.tool_calls[0]
            if owner.name == "search_files":
                owner.turn_decision.memory_update = tool_note("pending")
            elif owner.name == "replace_text":
                owner.turn_decision.memory_update = tool_note("mock-read-source", note_id="n1")
            elif owner.name == "run_check":
                owner.turn_decision.memory_update = tool_note("mock-apply-mutation")
            return turn

    monkeypatch.setattr(runner, "MockDevAdapter", NotingMock)
    request = DevRunRequest(
        provider="mock", model="mock-dev", state_root=tmp_path,
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
    )
    run = runner.run_dev(request)["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    assert run["call_counts"] == {"model": 4, "input_count": 0, "tool": 5}
    assert run["evaluator"]["claim_eligible"] is False
    events = DevJournal(tmp_path, run["run_id"]).events()
    payloads = [event["payload"] for event in events
                if event["event_type"] == "working_notes_updated"]
    assert len(payloads) == 3
    assert [payload["receipt"]["findings"][0]["status"] for payload in payloads] == [
        "rejected", "rejected", "created",
    ]
    turns = [event["payload"] for event in events if event["event_type"] == "turn_started"]
    inputs = [json.loads(Path(turn["model_input_artifact"]["path"]).read_text(encoding="utf-8"))
              for turn in turns]
    assert len(inputs) == 4
    for index, (items, _payload) in enumerate(zip(inputs[1:], payloads, strict=True), start=1):
        outputs = [json.loads(item["output"]) for item in items
                   if item.get("type") == "function_call_output"]
        receipts = [output["memory_update_result"] for output in outputs
                    if "memory_update_result" in output]
        assert receipts == [prior["receipt"] for prior in payloads[:index]]
        assert all(output["status"] == "succeeded" for output in outputs)
        notes = json.loads(items[1]["content"])["working_notes"]
        assert notes["last_update_result"]["delivery"] == "preceding_function_call_output"
        assert "last_update_diagnostics" not in notes
    final_notes = json.loads(inputs[-1][1]["content"])["working_notes"]["findings"]
    assert [note["note_id"] for note in final_notes] == ["n1"]
    assert final_notes[0]["status"] == "current"


def test_prompt_and_memory_schema_explain_before_batch_timing_and_initial_question():
    description = memory_update_schema()["description"].lower()
    prompt = DEV_SYSTEM_PROMPT.lower()
    for text in (description, prompt):
        assert "before" in text
        assert "batch" in text
        assert "open_question" in text
        assert "note_id=null" in text
