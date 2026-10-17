from __future__ import annotations

import copy

from test_dev_context_v12 import observe
from test_dev_context_v12 import source_gateway as source_gateway
from test_dev_notes_v14 import note_call, restore, source_note

from patchloop.dev.context import project_observed_sources
from patchloop.dev.evidence_focus import (
    bind_question,
    optional_exchanges,
    project_interpretations,
    source_references,
)
from patchloop.dev.verification_concerns import project_verification_concerns
from patchloop.dev.working_notes import memory_update_schema
from patchloop.util import canonical_json


def focus(start=2, end=2):
    return {"text": "Which branch is relevant?", "evidence": [
        {"kind": "source", "path": "src.py", "start_line": start, "end_line": end},
    ]}


def update(question):
    return {"findings": [], "remove_note_ids": [], "open_question": question}


def test_question_independent_admission_null_and_recovery(source_gateway):
    gateway, _, tracked = source_gateway
    observe(gateway, "src.py", 1, 4)
    payload = gateway.record_working_notes_update(
        [note_call("q", update(focus()))], turn_id="q",
    )
    question = gateway.working_notes()["open_question"]
    assert question["evidence"][0]["file_hash"]
    assert payload["question_bodies"] == ["second"]
    invalid = source_note()
    invalid["open_question"] = focus(2, 99)
    receipt = gateway.record_working_notes_update([note_call("bad", invalid)], turn_id="bad")
    assert not receipt["receipt"]["open_question_applied"]
    assert len(gateway.working_notes()["findings"]) == 1
    assert gateway.working_notes()["open_question"] == question
    assert restore(gateway, tracked).working_notes()["open_question"] == question
    gateway.record_working_notes_update([note_call("keep", None)], turn_id="keep")
    assert gateway.working_notes()["open_question"] == question
    gateway.record_working_notes_update([note_call("clear", update(None))], turn_id="clear")
    assert gateway.working_notes()["open_question"] is None


def test_question_unique_rebind_then_persistent_expiry(source_gateway):
    gateway, sources, tracked = source_gateway
    observe(gateway, "src.py", 1, 4)
    gateway.record_working_notes_update([note_call("q", update(focus()))], turn_id="q")
    sources["src.py"] = b"inserted\nfirst\nsecond\nthird\nfourth\n"
    question = gateway.working_notes()["open_question"]
    assert question["evidence"][0]["start_line"] == 3
    assert any(s["content"] == "second" for s in gateway.prepare_context_projection().source_spans)
    assert restore(gateway, tracked).working_notes()["open_question"] == question
    refreshed = gateway.record_working_notes_update(
        [note_call("rebound", update(focus(3, 3)))], turn_id="rebound",
    )
    assert refreshed["receipt"]["open_question_applied"]
    assert gateway.context_spans()
    sources["src.py"] = b"second\nsecond\n"
    question = gateway.working_notes()["open_question"]
    assert question["evidence"][0]["unavailable_reason"]
    # A subsequent annotation durably preserves expiry, not an instruction to rediscover it.
    gateway.record_working_notes_update([note_call("bad", update(focus(99, 99)))], turn_id="bad")
    sources["src.py"] = b"first\nsecond\nthird\nfourth\n"
    assert restore(gateway, tracked).working_notes()["open_question"]["evidence"][0][
        "unavailable_reason"]


def span(start, content, seq=0, path="x.py", digest="hash"):
    return {"path": path, "file_hash": digest, "start_line": start,
            "end_line": start + content.count("\n"), "content": content,
            "last_observed_seq": seq}


def select(spans, refs=(), limit=5, priorities=(), native=()):
    return project_observed_sources(spans, native_spans=list(native),
                                    priorities=list(priorities), editable_paths={"x.py"},
                                    max_chars=limit, focus_references=list(refs))


def ref(start, end, digest="hash"):
    return {"kind": "source", "path": "x.py", "file_hash": digest,
            "start_line": start, "end_line": end}


def test_priority_preserves_focus_and_accounts_displacement():
    spans = [span(1, "aaa", 1), span(10, "bbb", 2)]
    baseline = select(spans, limit=3)
    focused = select(spans, [ref(1, 1)], limit=3)
    assert baseline.source_spans[0]["start_line"] == 10
    assert focused.source_spans[0]["start_line"] == 1
    assert focused.omitted_observed_line_count == baseline.omitted_observed_line_count == 1
    pinned = select(spans, [ref(1, 1)], limit=3, priorities=[("x.py", 10, 10, 1)])
    assert pinned.source_spans == baseline.source_spans


def test_oversized_focus_does_not_suppress_fallback_or_smaller_reference():
    spans = [span(1, "aa\nbb", 2), span(10, "z", 1)]
    assert select(spans, [ref(1, 2)], limit=2).source_spans == select(spans, limit=2).source_spans
    got = select(spans, [ref(1, 2), ref(10, 10)], limit=2)
    assert got.source_spans[0]["start_line"] == 10
    exact = select(spans, [ref(1, 2)], limit=5)
    assert exact.retained_content_chars == 5
    assert exact.source_spans[0]["content"] == "aa\nbb"


def test_overlap_native_wrong_version_and_unseen_gap():
    spans = [span(1, "a\nb\nc"), span(10, "new", 2)]
    got = select(spans, [ref(1, 2), ref(2, 3)], limit=5)
    assert got.retained_content_chars == 5
    assert select(spans, [ref(1, 3, "old")], limit=3) == select(spans, limit=3)
    assert select(spans, [ref(1, 9)], limit=3) == select(spans, limit=3)
    got = select(spans, [ref(1, 3)], limit=3, native=[spans[0]])
    assert got.retained_content_chars == 3 and got.source_spans[0]["content"] == "new"


def test_projection_distinguishes_current_missing_and_model_closure():
    evidence = ref(1, 2)
    view = {"current_diff": {"patch_hash": "D2"}, "current_sources": [], "working_notes": {
        "open_question": {"text": "q", "evidence": [evidence]},
        "findings": [{"note_id": "n1", "statement": "The patch is correct.",
                      "status": "current", "evidence": [evidence],
                      "interpretation_status": "model_authored_unverified"}],
        "verification": {"items": [{"status": "resolved", "statement": "Target behavior?"}]},
    }}
    project_interpretations(view, [])
    notes = view["working_notes"]
    assert notes["open_question"]["evidence_delivery"] == "incomplete"
    assert notes["findings"][0]["evidence_currency"] == "current"
    assert notes["findings"][0]["model_interpretation"] == "The patch is correct."
    assert notes["verification"]["items"][0]["status"] == "closed_by_model"
    assert notes["verification"]["items"][0]["behavior_coverage"] == "not_assessed"


def test_probe_false_value_is_not_a_verdict_and_old_failure_is_historical():
    result = {"action_id": "probe", "input_hash": "input", "tool": "run_probe",
              "status": "succeeded", "workspace_diff_hash": "D1",
              "output": {"exit_code": 0, "stdout": "equals_expected=False", "truncated": False}}
    question, error = bind_question({"text": "Solved?", "evidence": [
        {"kind": "tool_result", "action_id": "probe"},
    ]}, [], {"probe": result})
    assert error is None
    view = {"current_diff": {"patch_hash": "D2"}, "working_notes": {"open_question": question}}
    original = copy.deepcopy(result)
    project_interpretations(view, [{"type": "function_call_output", "call_id": "probe",
                                    "output": canonical_json(result)}])
    ref = view["working_notes"]["open_question"]["evidence"][0]
    assert ref["evidence_currency"] == "historical"
    assert ref["execution"]["exit_code"] == 0 and ref["behavior_coverage"] == "not_assessed"
    assert original == result
    assert memory_update_schema()["properties"]["open_question"]["type"] == ["object", "null"]


def test_source_bearing_tool_reference_cannot_bypass_source_budget():
    result = {"tool": "read_file", "input_hash": "input", "action_id": "read",
              "output": {"spans": [span(1, "too much source")]}}
    question, error = bind_question({"text": "Read?", "evidence": [
        {"kind": "tool_result", "action_id": "read"},
    ]}, [], {"read": result})
    assert error is None
    events = [{"event_type": "action_finished", "payload": {"result": result}},
              {"event_type": "turn_decision_recorded", "payload": {"tool_calls": [
                  {"action_id": "read", "name": "read_file", "arguments": {"path": "x.py"}},
              ]}}]
    assert optional_exchanges(question, events) == []
    refs = source_references(question)
    assert refs == []  # Unscoped legacy declarations receive no extra priority.
    selected = select(result["output"]["spans"], refs, limit=5)
    assert selected.source_spans == ()
    view = {"working_notes": {"open_question": question}}
    project_interpretations(view, [])
    assert view["working_notes"]["open_question"]["evidence_delivery"] == "incomplete"


def test_execution_flags_survive_missing_result_without_implying_delivery():
    result = {"tool": "run_probe", "input_hash": "input", "action_id": "probe",
              "output": {"exit_code": 0, "truncated": True, "timed_out": True,
                         "deadline_exhausted": True}}
    question, _ = bind_question({"text": "Check?", "evidence": [
        {"kind": "tool_result", "action_id": "probe"},
    ]}, [], {"probe": result})
    view = {"working_notes": {"open_question": question}, "working_plan": {"plan": "Try it."}}
    project_interpretations(view, [])
    delivered = view["working_notes"]["open_question"]["evidence"][0]
    assert delivered["evidence_delivery"] == "incomplete"
    assert delivered["execution"] == result["output"]
    assert delivered["behavior_coverage"] == "not_assessed"
    assert view["working_plan"]["role"] == "proposed_remaining_work"


def test_no_evidence_owner_does_not_add_unrelated_source_validation(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No reference requires a delivery inventory")
    monkeypatch.setattr("patchloop.dev.evidence_focus.SnapshotRules.inventory", forbidden)
    for notes in (None, {}, {"findings": [], "open_question": {"text": "q", "evidence": []}}):
        view = {"working_notes": notes, "working_plan": {"plan": "Inspect the next behavior."}}
        project_interpretations(view, [])
        assert view["working_plan"]["role"] == "proposed_remaining_work"
        if notes and notes.get("open_question"):
            assert notes["open_question"]["evidence_delivery"] == "not_requested"


def test_final_source_union_reports_exact_missing_ranges():
    citation = ref(1, 3)
    view = {"working_notes": {"open_question": {"text": "q", "evidence": [citation]}}}
    history = [{"type": "function_call_output", "call_id": "read", "output": canonical_json({
        "action_id": "read", "status": "succeeded", "tool": "read_file",
        "output": {"spans": [span(1, "a\nb\nc")]},
    })}]
    project_interpretations(view, history)
    assert view["working_notes"]["open_question"]["evidence_delivery"] == "complete"
    project_interpretations(view, [])
    ref_after_removal = view["working_notes"]["open_question"]["evidence"][0]
    assert ref_after_removal["evidence_delivery"] == "incomplete"
    assert ref_after_removal["missing_ranges"] == [[1, 3]]


def test_generic_pass_model_closure_keeps_purpose_and_reopens_after_diff_change():
    state = {"items": [{"concern_id": "v1", "statement": "Does the reported edge case work?",
                       "decision": {"outcome": "resolved", "diff_hash": "D1",
                                    "reason": "The generic suite passed.", "evidence": {
                                        "action_id": "suite", "input_hash": "I1",
                                        "tool": "run_check", "diff_hash": "D1"}}}]}
    result = {"action_id": "suite", "input_hash": "I1", "tool": "run_check",
              "output": {"passed": True, "exit_code": 0, "diff_hash": "D1"}}
    history = [{"type": "function_call_output", "call_id": "suite",
                "output": canonical_json(result)}]
    for diff in ("D1", "D2"):
        view = {"current_diff": {"patch_hash": diff}, "working_plan": {"plan": "New plan"},
                "working_notes": {"open_question": None,
                                  "verification": project_verification_concerns(
                                      state, diff_hash=diff)}}
        project_interpretations(view, history)
        concern = view["working_notes"]["verification"]["items"][0]
        assert concern["statement"] == state["items"][0]["statement"]
        assert concern["status"] == ("closed_by_model" if diff == "D1" else "unresolved")
        evidence = concern["decision"]["evidence"]
        assert evidence["execution"]["passed"] is True
        assert evidence["behavior_coverage"] == "not_assessed"
        assert evidence["evidence_currency"] == ("current" if diff == "D1" else "historical")
        project_interpretations(view, [])
        evidence = view["working_notes"]["verification"]["items"][0]["decision"]["evidence"]
        assert evidence["evidence_delivery"] == "incomplete" and "result_delivery" not in evidence
