from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import patchloop.dev.runner as runner
from patchloop.dev.contracts import DevRunRequest, DevToolResult
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root


@pytest.mark.parametrize("valid_note", [True, False])
def test_working_notes_are_nonblocking_in_actual_model_input(
    tmp_path: Path, monkeypatch, valid_note: bool,
) -> None:
    class NotingMock(MockDevAdapter):
        def next_turn(self, context, tools):
            turn = super().next_turn(context, tools)
            call = turn.tool_calls[0]
            if call.name == "replace_text":
                call.turn_decision.memory_update = {
                    "findings": [{
                        "statement": "The observed parser splits the input into physical lines.",
                        "evidence": [{
                            "kind": "tool_result",
                            "action_id": "mock-read-source" if valid_note else "unobserved-action",
                        }],
                    }],
                    "open_question": "Does the replacement preserve quoted multiline fields?",
                }
            return turn

    monkeypatch.setattr(runner, "MockDevAdapter", NotingMock)
    request = DevRunRequest(
        provider="mock", model="mock-dev", state_root=tmp_path,
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
    )
    run = runner.run_dev(request)["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    assert run["call_counts"] == {"model": 4, "input_count": 0, "tool": 5}
    journal = DevJournal(tmp_path, run["run_id"])
    events = journal.events()
    updates = [event["payload"] for event in events
               if event["event_type"] == "working_notes_updated"]
    assert len(updates) == 1
    assert bool(updates[0]["findings"]) is valid_note
    assert bool(updates[0]["diagnostics"]) is not valid_note
    turns = [event["payload"] for event in events if event["event_type"] == "turn_started"]
    inputs = [json.loads(Path(turn["model_input_artifact"]["path"]).read_text(encoding="utf-8"))
              for turn in turns]
    contexts = [json.loads(items[1]["content"]) for items in inputs]
    assert all("canonical_searches" not in item["evidence_ledger"] for item in contexts)
    assert all(len(item["evidence_ledger"]["recent_inspection_outcomes"]) <= 3
               for item in contexts)
    assert contexts[2]["last_successful_mutation"]["delivery"] == (
        "preceding_function_call_output"
    )
    assert contexts[2]["latest_tool_results"] == []
    assert bool(contexts[2]["working_notes"]["findings"]) is valid_note
    if valid_note:
        finding = contexts[2]["working_notes"]["findings"][0]
        assert finding["status"] == "historical"
        assert finding["model_authored"] is True
    # Once the native batch changes, the retained accepted edit becomes self-contained again.
    assert "hypothesis" in contexts[3]["last_successful_mutation"]
    assert all("stdout" not in check and "stderr" not in check
               for check in contexts[3]["recent_checks"])
    for items in inputs:
        assert "hidden-multiline-csv" not in json.dumps(items)
        assert "reference.patch" not in json.dumps(items)
    assert run["evaluator"]["claim_eligible"] is False


def test_attempt_projection_keeps_annotations_and_fingerprints_only_in_journal(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_note_projection")
    journal.append("attempt_card", {
        "action_id": "batch:inspect",
        "attempt": "inspect",
        "result": {"actions": [{
            "evidence_fingerprint": "journal-only-fingerprint",
            "turn_decision": {"basis": "Public question", "memory_update": {
                "findings": [], "open_question": "Validated separately",
            }},
        }]},
    })
    card = runner._cards(journal, None)[0]
    action = card["result"]["actions"][0]
    assert "evidence_fingerprint" not in action
    assert action["turn_decision"] == {"basis": "Public question"}
    assert "journal-only-fingerprint" in journal.path.read_text()


def test_repeated_failure_card_does_not_assume_the_hypothesis_is_falsified():
    result = DevToolResult(
        action_id="failed-check", input_hash="hash", tool="run_check", status="succeeded",
        output={"check_id": "visible", "passed": False, "failure_signature": "failure",
                "public_check_failure": {"comparison_with_previous_failure": {
                    "relation": "same_public_failure_site",
                }}},
    )
    card = runner._attempt_card(result, SimpleNamespace())
    assert "partial repair" in card["next_question"]
    assert "different explanation" in card["next_question"]
    assert "falsified" not in card["next_question"]
