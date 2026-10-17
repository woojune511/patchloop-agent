from __future__ import annotations

import copy
from unittest.mock import PropertyMock

import pytest
from test_dev_context_v12 import observe
from test_dev_context_v12 import source_gateway as source_gateway
from test_dev_notes_v14 import note_call, restore, source_note
from test_evidence_focus import focus, ref, select, span, update

from patchloop.dev.evidence_focus import (
    bind_question,
    optional_exchanges,
    priority_status,
    project_interpretations,
    source_references,
)
from patchloop.dev.tools import DevToolGateway
from patchloop.dev.working_notes import memory_update_schema
from patchloop.util import canonical_json


def declared():
    question = focus()
    question["evidence"][0]["role"] = "primary"
    return question


def test_countercheck_precedes_primary_but_never_mutation_anchor():
    spans = [span(1, "aaa", 1), span(10, "bbb", 2)]
    refs = [{**ref(10, 10), "role": "primary"}, {**ref(1, 1), "role": "countercheck"}]
    got = select(spans, refs, limit=3)
    assert got.source_spans[0]["content"] == "aaa"
    assert got == select(spans, list(reversed(refs)), limit=3)
    assert got.retained_content_chars == 3 and got.omitted_observed_line_count == 1
    anchored = select(spans, refs, limit=3, priorities=[("x.py", 10, 10, 1)])
    assert anchored.source_spans[0]["content"] == "bbb"
    assert select(spans, refs, limit=6).omitted_observed_line_count == 0


def test_question_scope_survives_recovery_but_requires_refresh_after_diff(
    source_gateway, monkeypatch,
):
    gateway, _, tracked = source_gateway
    current = {"hash": "D1"}
    monkeypatch.setattr(DevToolGateway, "current_diff_hash", PropertyMock(
        side_effect=lambda: current["hash"],
    ))
    observe(gateway, "src.py", 1, 4)
    gateway.record_working_notes_update([note_call("q", update(declared()))], turn_id="q")
    before = gateway.working_notes()["open_question"]
    assert before["declared_diff_hash"] == "D1" and before["priority_status"] == "eligible"
    assert gateway.focus_source_references()
    current["hash"] = "D2"  # Source bytes did not change; question's patch scope did.
    stale = gateway.working_notes()["open_question"]
    assert stale["evidence"] == before["evidence"]
    assert stale["priority_status"] == "needs_refresh" and gateway.focus_source_references() == []
    assert restore(gateway, tracked).working_notes()["open_question"] == stale
    gateway.record_working_notes_update([note_call("keep", None)], turn_id="keep")
    assert gateway.working_notes()["open_question"] == stale
    # The same question can be reconsidered in a normal response, without a new read.
    gateway.record_working_notes_update(
        [note_call("refresh", update(declared()))], turn_id="refresh",
    )
    refreshed = gateway.working_notes()["open_question"]
    assert refreshed["declared_diff_hash"] == "D2" and gateway.focus_source_references()
    assert refreshed["revision_hash"] != before["revision_hash"]
    assert restore(gateway, tracked).working_notes()["open_question"] == refreshed
    receipt = gateway.record_working_notes_update(
        [note_call("repeat", update(declared()))], turn_id="refresh",
    )
    assert receipt["open_question"]["revision_hash"] == refreshed["revision_hash"]


@pytest.mark.parametrize("bad", ["duplicate", "mixed", "forged_scope"])
def test_bad_role_update_preserves_question_and_independent_finding(source_gateway, bad):
    gateway, _, _ = source_gateway
    observe(gateway, "src.py", 1, 4)
    gateway.record_working_notes_update([note_call("q", update(declared()))], turn_id="q")
    before = gateway.working_notes()["open_question"]
    invalid = declared()
    if bad == "forged_scope":
        invalid["declared_diff_hash"] = "MODEL_SUPPLIED"
    else:
        second = copy.deepcopy(invalid["evidence"][0])
        if bad == "mixed":
            second.pop("role")
        invalid["evidence"].append(second)
    annotation = source_note()
    annotation["open_question"] = invalid
    receipt = gateway.record_working_notes_update([note_call("bad", annotation)], turn_id="bad")
    assert not receipt["receipt"]["open_question_applied"]
    assert gateway.working_notes()["open_question"] == before
    assert len(gateway.working_notes()["findings"]) == 1


def test_legacy_ranges_are_visible_without_implicit_roles_or_priority(source_gateway, monkeypatch):
    gateway, _, tracked = source_gateway
    observe(gateway, "src.py", 1, 4)
    gateway.record_working_notes_update([note_call("legacy", update(focus()))], turn_id="legacy")
    question = gateway.working_notes()["open_question"]
    assert question["priority_status"] == "unscoped"
    assert "role" not in question["evidence"][0] and "declared_diff_hash" not in question
    assert gateway.focus_source_references() == []
    assert restore(gateway, tracked).working_notes()["open_question"] == question
    schema = memory_update_schema()["properties"]["open_question"]
    assert schema["properties"]["evidence"]["maxItems"] == 2
    for shape in schema["properties"]["evidence"]["items"]["anyOf"]:
        assert "role" in shape["required"]
    monkeypatch.setattr(DevToolGateway, "current_diff_hash", PropertyMock(
        side_effect=AssertionError("unscoped focus needs no diff observation"),
    ))
    assert gateway.focus_source_references() == []


def test_whole_source_results_cannot_replace_explicit_minimal_ranges():
    result = {"tool": "read_file", "input_hash": "I", "action_id": "read",
              "output": {"spans": [span(1, "code\nmore code")]}}
    question, error = bind_question({"text": "Which branch?", "evidence": [
        {"kind": "tool_result", "action_id": "read", "role": "countercheck"},
    ]}, [], {"read": result}, diff_hash="D")
    assert question is None and error == "question_source_requires_range"


def test_historical_countercheck_can_be_refreshed_without_becoming_a_current_verdict():
    result = {"tool": "run_probe", "action_id": "probe", "input_hash": "I",
              "workspace_diff_hash": "D1", "output": {"exit_code": 0, "stdout": "False"}}
    raw = {"text": "Does the new route address this old failure?", "evidence": [
        {"kind": "tool_result", "action_id": "probe", "role": "countercheck"},
    ]}
    question, error = bind_question(raw, [], {"probe": result}, diff_hash="D2")
    assert error is None and priority_status(question, "D2") == "eligible"
    events = [{"event_type": "action_finished", "payload": {"result": result}},
              {"event_type": "turn_decision_recorded", "payload": {"tool_calls": [
                  {"action_id": "probe", "name": "run_probe", "arguments": {}},
              ]}}]
    quoted = optional_exchanges(question, events, diff_hash="D2")
    assert len(quoted) == 2
    assert optional_exchanges(question, events, diff_hash="D3") == []
    view = {"current_diff": {"patch_hash": "D2"}, "working_notes": {"open_question": question}}
    project_interpretations(view, quoted)
    evidence = view["working_notes"]["open_question"]["evidence"][0]
    assert evidence["evidence_delivery"] == "complete"
    assert evidence["evidence_currency"] == "historical"
    assert evidence["behavior_coverage"] == "not_assessed"
    assert "False" in canonical_json(quoted)


def test_eligible_role_is_not_a_delivery_or_minimality_guarantee():
    raw = {"text": "Which route?", "evidence": [
        {"kind": "source", "path": "x.py", "start_line": 1, "end_line": 3,
         "role": "countercheck"},
    ]}
    question, error = bind_question(raw, [span(1, "a\nb\nc")], {}, diff_hash="D")
    assert error is None and len(source_references(question, diff_hash="D")) == 1
    view = {"current_diff": {"patch_hash": "D"}, "working_notes": {"open_question": question}}
    project_interpretations(view, [])
    projected = view["working_notes"]["open_question"]
    assert projected["priority_status"] == "eligible"
    assert projected["evidence_delivery"] == "incomplete"
    assert projected["evidence"][0]["missing_ranges"] == [[1, 3]]
