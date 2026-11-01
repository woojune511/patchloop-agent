"""Read-only public choice audits preserve evidence and counterfactual boundaries."""

import json
from types import SimpleNamespace

import pytest

from diagnostics.finish_choice_audit import _evidence, audit_saved_turn, slot_comparison
from patchloop.artifacts import ArtifactStore
from patchloop.dev.conversation import assemble_model_input
from patchloop.dev.state import DevJournal
from patchloop.errors import RecoveryError
from patchloop.util import sha256_json


def test_extra_edits_do_not_replace_the_response_spent_on_a_probe():
    report = slot_comparison(calls=4, corrections=1, actions=12, used_edits=1, check_count=1)
    assert [row["edits_remaining"] for row in report["rows"]] == [2, 3, 11]
    assert all(row["immediate_shortfalls"] == [] for row in report["rows"])
    assert all(row["after_one_probe_shortfalls"] == ["model_calls"] for row in report["rows"])
    assert "No model choice" in report["assumptions"]
    later = slot_comparison(calls=3, corrections=1, actions=11, used_edits=1, check_count=1)
    assert all(row["immediate_shortfalls"] == ["model_calls"] for row in later["rows"])


def test_four_edits_already_remove_the_observed_three_edit_exhaustion():
    report = slot_comparison(calls=7, corrections=1, actions=19, used_edits=3, check_count=1)
    assert [row["immediate_shortfalls"] for row in report["rows"]] == [
        ["accepted_mutations"], [], [],
    ]
    assert [row["edits_remaining"] for row in report["rows"]] == [0, 1, 9]
    assert all(row["edit_route_minimum"] == {"calls": 3, "actions": 3} for row in report["rows"])


@pytest.fixture
def saved_turn(tmp_path, monkeypatch):
    root = tmp_path / "existing"
    journal = DevJournal(root, "run_dev_publicaudit")
    store = ArtifactStore(root / "artifacts")
    result = {"action_id": "public-observation", "input_hash": "public-input",
              "tool": "run_probe", "status": "succeeded", "workspace_diff_hash": "candidate",
              "output": {"stdout": "original failure remains", "stderr": "", "exit_code": 0}}
    journal.append("action_finished", {"result": result})
    state = {
        "public_task": {"issue": {"title": "public task"}},
        "current_diff": {"patch_hash": "candidate"}, "workflow_gate": "ready_to_submit",
        "completion_guidance": {"verification_policy": "public-checks-v1"},
        "available_tool_names": ["finish_task", "replace_text", "run_probe"],
        "remaining_budget": {"model_calls": 5, "tool_actions": 13, "accepted_mutations": 2,
            "active_wall_time_seconds": 1500, "cost": {"remaining": 3_000_000_000,
                "completion_cost": {"correction_model_calls_reserved": 1}}},
        "action_horizon": {"mutation_completion_horizon": {
            "minimum_calls": 3, "minimum_tool_actions": 3, "minimum_possible": True}},
        "latest_tool_results": [result],
    }
    items = assemble_model_input(system_prompt="public only", state=state, history=[],
                                 context_policy="segmented-v1")
    input_ref = store.put_json(items)
    request = {"input": items, "tools": [{"name": name} for name in state["available_tool_names"]]}
    prepared_ref = store.put_json({"request": request})
    turn = journal.append("turn_started", {
        "turn_id": "t1", "model_input_artifact": input_ref.model_dump(mode="json"),
        "model_input_hash": input_ref.content_hash,
        "prepared_input": {"artifact": prepared_ref.model_dump(mode="json"),
                           "request_hash": sha256_json(request)},
    })
    journal.append("provider_call_started", {"turn_id": "t1",
        "request_hash": sha256_json(request), "counted_request_hash": sha256_json(request)})
    journal.append("turn_decision_recorded", {"turn_id": "t1", "tool_calls": [{
        "name": "finish_task", "action_id": "finish", "arguments": {
            "assessment": "Not verified to repair the original failure."}}]})
    journal.append("evaluator_finished", {"private": "PRIVATE_EVALUATOR_SENTINEL"})
    monkeypatch.setattr(DevJournal, "load_envelope", lambda self: SimpleNamespace(
        limits=SimpleNamespace(max_accepted_mutations=3)))
    return root, journal, turn["sequence"], input_ref, prepared_ref, request


def test_observed_failure_delivery_and_offered_repair_are_not_semantic_success(saved_turn):
    root, journal, sequence, *_ = saved_turn
    before = journal.path.read_bytes()
    report = audit_saved_turn(root, journal.run_id, sequence, evidence_ids=["public-observation"])
    evidence = report["evidence"][0]
    assert evidence["execution_status"] == "succeeded"
    assert evidence["current_candidate"] and evidence["delivered_channels"] == ["current_state"]
    assert evidence["text_fields"]["stdout"]["exact_body_delivered"]
    assert report["chosen_actions"][0]["names"] == ["finish_task"]
    assert "replace_text" in report["offered_tools"]
    assert report["local_resource_comparison"]["rows"][0]["immediate_shortfalls"] == []
    exported = json.dumps(report)
    assert "PRIVATE_EVALUATOR_SENTINEL" not in exported
    assert "original failure remains" not in exported
    assert "Not verified to repair" not in exported
    assert journal.path.read_bytes() == before


def test_audit_rejects_unbound_input_or_incompatible_edit_route(saved_turn):
    root, journal, sequence, ref, *_ = saved_turn
    with pytest.raises(ValueError, match="recorded minimum"):
        audit_saved_turn(root, journal.run_id, sequence, check_count=2)
    with pytest.raises(ValueError, match="earlier public action"):
        audit_saved_turn(root, journal.run_id, sequence, evidence_ids=["future-or-absent"])
    path = root / "artifacts/objects/sha256" / ref.content_hash[7:9] / ref.content_hash[9:]
    path.write_bytes(b"tampered public input")
    with pytest.raises(RecoveryError, match="integrity"):
        audit_saved_turn(root, journal.run_id, sequence)


def test_counterfactual_rejects_rewriting_already_spent_edits():
    with pytest.raises(ValueError, match="already accepted"):
        slot_comparison(calls=7, corrections=1, actions=19, used_edits=4, check_count=1)


def test_historical_receipt_alone_is_not_delivery_and_native_body_counts(saved_turn):
    root, journal, sequence, *_ = saved_turn
    rows = journal.events()
    state = {"current_diff": {"patch_hash": "candidate"}, "latest_tool_results": []}
    absent = _evidence(rows, [], state, "public-observation", sequence)
    assert absent["delivered_channels"] == []
    assert absent["text_fields"]["stdout"]["exact_body_delivered"] is False
    result = rows[0]["payload"]["result"]
    items = [{"type": "function_call_output", "call_id": "public-observation",
              "output": json.dumps(result)}]
    actual = _evidence(rows, items, state, "public-observation", sequence)
    assert actual["delivered_channels"] == ["native_or_public_archive"]
    assert actual["text_fields"]["stdout"]["exact_body_delivered"] is True


def test_source_identifier_without_body_does_not_count_as_exact_source_delivery():
    span = {"path": "src/a.py", "file_hash": "filehash", "start_line": 1,
            "end_line": 1, "content": "public_source = 1"}
    original = {"action_id": "read", "input_hash": "read-input", "tool": "read_file",
                "status": "succeeded", "workspace_diff_hash": "candidate",
                "output": {"spans": [span]}}
    rows = [{"sequence": 1, "event_hash": "event", "event_type": "action_finished",
             "payload": {"result": original}}]
    state = {"current_diff": {"patch_hash": "candidate"}, "latest_tool_results": [
        {**original, "output": {"spans": [{k: v for k, v in span.items() if k != "content"}]}}]}
    absent = _evidence(rows, [], state, "read", 2)
    assert absent["source_spans"][0]["exact_body_delivered"] is False
    state["latest_tool_results"] = [original]
    actual = _evidence(rows, [], state, "read", 2)
    assert actual["source_spans"][0]["exact_body_delivered"] is True
    assert span["content"] not in json.dumps(actual)
