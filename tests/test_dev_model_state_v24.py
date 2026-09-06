from __future__ import annotations

import copy
import json

import pytest
from test_dev_conversation_v23 import _output, _span
from test_dev_tools import mutation_call, read_calls

from patchloop.dev.conversation import assemble_model_input, history_metadata, reconstruct_state
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.native_sources import reference_native_sources
from patchloop.dev.runner import _RunCounters, _tool_policy
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import RecoveryError
from patchloop.util import canonical_json, sha256_json


def _size(value):
    return len(canonical_json(value).encode("utf-8"))


def test_rolling_audit_state_is_not_repeated_as_model_edit_operations():
    previous = None
    history = []
    projection_bytes = audit_bytes = 0
    for turn in range(30):
        spans = [{**_span(f"line {i}", start=i + 1), "span_id": f"{turn}-{i}",
                  "last_observed_seq": turn} for i in range(24)]
        exchange = [_output(f"read-{turn}", spans)]
        history.extend(exchange)
        cards = [{"attempt": "inspect", "action_id": f"r-{turn-i}", "result": {
            "spans": spans, "fingerprint": sha256_json([turn, i]),
        }} for i in range(3)]
        raw = {
            "workflow_gate": "needs_mutation", "remaining_budget": {"model_calls": 40-turn},
            "public_task": {"description": "STABLE_PUBLIC_TASK"}, "source_spans": spans,
            "observed_source_index": {"entries": [], "omitted_count": 0},
            "recent_attempt_result_next_question": cards,
            "evidence_ledger": {"recent_inspection_outcomes": cards, "covered_files": spans,
                                "search_summary": {"total_search_count": turn}},
            "current_diff": {"patch": "", "patch_hash": "baseline"},
            "working_notes": {"findings": [], "available_note_ids": [],
                              "open_question": f"Question {turn}"},
            "available_tool_names": ["read_file", "replace_text", "stop_task"],
        }
        before = copy.deepcopy((raw, history))
        view = compact_model_state(reference_native_sources(raw, history), history)
        items = assemble_model_input(system_prompt="fixed", state=view, history=exchange,
                                     previous_input=previous)
        latest = json.loads(items[-1]["content"])["state"] if previous else view
        if previous:
            assert latest == {k: v for k, v in view.items() if k != "public_task"}
        assert reconstruct_state(items) == view
        if previous:
            assert items[:len(previous)] == previous
        assert [i for i in items[3:] if i.get("type")] == history
        assert (raw, history) == before
        assert view["evidence_ledger"] == {"search_summary": {"total_search_count": turn}}
        assert view["recent_attempt_result_next_question"] == []
        assert "span_id" not in canonical_json(view)
        assert _size(view) < _size(raw) / 3
        projection_bytes += _size(view)
        audit_bytes += _size(raw)
        previous = items
    assert projection_bytes < audit_bytes / 3  # Bytes, not billed tokens or an agent success claim.
    assert canonical_json(previous).count("STABLE_PUBLIC_TASK") == 1
    assert "harness_state_delta" not in canonical_json(previous)
    assert history_metadata(previous)["state_update_count"] == 29


def test_audit_only_sequence_and_rolling_cards_do_not_change_current_model_view():
    span = _span()
    history = [_output("read", [span])]
    state = {"source_spans": [span], "recent_attempt_result_next_question": [],
             "context_projection": {"delivered_source_hash": "first"},
             "evidence_ledger": {"search_summary": {}, "recent_inspection_outcomes": []}}
    first = compact_model_state(reference_native_sources(state, history), history)
    state["source_spans"][0].update(span_id="new", last_observed_seq=999)
    state["context_projection"]["delivered_source_hash"] = "new"
    state["recent_attempt_result_next_question"] = [{"attempt": "inspect", "result": "new"}]
    state["evidence_ledger"]["recent_inspection_outcomes"] = [{"result": "new"}]
    second = compact_model_state(reference_native_sources(state, history), history)
    assert second == first


def test_catalog_preserves_exact_deliveries_gaps_hashes_headers_and_inline_fallback():
    history = [_output("read", [_span("one\ntwo\nthree\nfour", file_hash="current")])]
    spans = [_span("one", file_hash="current"), _span("two", start=2, file_hash="current"),
             _span("four", start=4, file_hash="current"),
             _span("same\r\nbytes", start=8, file_hash="new-hash")]
    state = {"source_spans": spans, "observed_source_index": {"omitted_count": 2, "entries": [
        {"path": "src.py", "file_hash": "current", "start_line": 1,
         "kind": "def", "name": "observed_header"},
    ]}}
    current, fallback = compact_model_state(
        reference_native_sources(state, history), history,
    )["current_sources"]
    assert current["path"] == "src.py" and current["file_hash"] == "current"
    assert current["content_delivery"] == {"read": {"output.spans[0]": [[1, 2], [4, 4]]}}
    assert current["headers"] == [{"kind": "def", "name": "observed_header", "start_line": 1}]
    assert fallback["file_hash"] == "new-hash"
    assert fallback["content_delivery"] == {}
    assert fallback["inline_spans"] == [
        {"content": "same\r\nbytes", "start_line": 8, "end_line": 9},
    ]


def test_complete_view_keeps_failure_notes_scope_correction_and_check_currency():
    exact = {
        "current_diff": {"patch_hash": "candidate", "patch": "public diff"},
        "current_public_failure": {"check_id": "public", "message": "public error"},
        "mutation_scope_budget": {"max_diff_lines": 50, "current_diff_lines": 49},
        "visible_check_status": [{"check_id": "public", "diff_hash": "old", "status": "FAIL"}],
        "remaining_visible_check_ids": ["public"],
        "protocol_correction": {"message": "Use an available action"},
        "working_notes": {"findings": [{"note_id": "n1", "statement": "Public interpretation",
                          "status": "historical", "model_authored": True,
                          "evidence": [{"action_id": "old-check", "currency": "historical"}]}],
                          "available_note_ids": ["n1"], "open_question": "Untested behavior?"},
    }
    view = compact_model_state(exact, [])
    assert view == exact
    initial = assemble_model_input(system_prompt="fixed", state=view, history=[])
    del view["protocol_correction"]
    view["working_notes"].update(findings=[], available_note_ids=[], open_question=None)
    final = assemble_model_input(system_prompt="fixed", state=view, history=[],
                                 previous_input=initial)
    assert reconstruct_state(final) == view
    # The latest mutable view can be read alone, not by replaying any earlier state record.
    assert json.loads(final[-1]["content"])["state"] == view
    assert "protocol_correction" not in reconstruct_state(final)


def test_immutable_task_cannot_change_within_episode():
    initial = assemble_model_input(system_prompt="fixed", state={"public_task": {"id": "one"}},
                                   history=[])
    with pytest.raises(RecoveryError, match="immutable public task"):
        assemble_model_input(system_prompt="fixed", state={"public_task": {"id": "two"}},
                             history=[], previous_input=initial)


@pytest.mark.parametrize("mismatch", [None, "diff_hash", "check_id", "missing"])
def test_older_check_body_reference_requires_exact_native_identity(mismatch):
    check = {"action_id": "check", "check_id": "public", "diff_hash": "current",
             "passed": False, "stdout": "PUBLIC_ERROR_BODY", "stderr": "", "historical": False}
    result = {"action_id": "check", "tool": "run_check", "status": "succeeded",
              "output": {**check}}
    if mismatch in {"diff_hash", "check_id"}:
        result["output"][mismatch] = "different"
    history = [] if mismatch == "missing" else [{
        "type": "function_call_output", "call_id": "check", "output": canonical_json(result),
    }]
    state = {"recent_checks": [check], "current_public_failure": {"message": "PUBLIC_ERROR_BODY"}}
    before = copy.deepcopy((state, history))
    view = compact_model_state(state, history)
    assert (state, history) == before
    projected = view["recent_checks"][0]
    if mismatch is None:
        assert "stdout" not in projected
        assert projected["delivery"] == "preceding_function_call_output"
        assert projected["passed"] is False and projected["diff_hash"] == "current"
    else:
        assert projected == check
    assert view["current_public_failure"] == state["current_public_failure"]


@pytest.mark.parametrize("crash_after_admission", [False, True])
@pytest.mark.parametrize("allowance", ["mini_data_utils/**", "mini_data_utils/csvlite.py"])
def test_path_feedback_is_explicit_preapply_and_durable_without_new_restrictions(
    gateway_factory, monkeypatch, crash_after_admission, allowance,
):
    gateway, journal, workspace = gateway_factory()
    gateway.public_task.constraints.allowed_paths = [allowance]
    gateway.execute_batch(read_calls())
    call = mutation_call(gateway, action_id="wrong-owner")
    call.arguments["path"] = "tests/test_csvlite.py"
    baseline = gateway.current_diff_hash
    target = workspace / call.arguments["path"]
    original = target.read_bytes()
    if crash_after_admission:
        append = journal.append

        def crash(event_type, payload):
            event = append(event_type, payload)
            if event_type == "action_started":
                raise KeyboardInterrupt("crash after rejected admission")
            return event

        monkeypatch.setattr(journal, "append", crash)
        with pytest.raises(KeyboardInterrupt):
            gateway.execute(call)
        monkeypatch.setattr(journal, "append", append)
    result = gateway.execute(call)
    assert result.status == "failed" and result.error_code == "CONTRACT_ERROR"
    failure = result.output["mutation_failure"]
    assert failure["class"] == "path_not_allowed"
    assert failure["rejected_path"] == call.arguments["path"]
    assert failure["allowed_paths"] == gateway.public_task.constraints.allowed_paths
    assert failure["forbidden_paths"] == gateway.public_task.constraints.forbidden_paths
    assert failure["candidate"] is None and failure["rolled_back"] is True
    assert failure["baseline"]["diff_hash"] == result.workspace_diff_hash == baseline
    assert call.arguments["path"] in result.message
    assert allowance in result.message
    assert gateway.accepted_mutations == 0 and target.read_bytes() == original
    before = journal.path.read_bytes()
    restarted = DevToolGateway(
        workspace=workspace, public_task=gateway.public_task, sandbox=gateway.sandbox,
        journal=DevJournal(journal.root, journal.run_id), limits=gateway.limits,
    )
    assert restarted.last_failed_mutation == gateway.last_failed_mutation
    replay = restarted.execute(call)
    assert replay.replayed and replay.output == result.output
    assert journal.path.read_bytes() == before
    assert target.read_bytes() == original and restarted.current_diff_hash == baseline
    policy = _tool_policy(restarted, _RunCounters(), restarted.limits)
    assert {"read_file", "search_files", "replace_text", "stop_task"} <= policy.allowed_tools
    view = compact_model_state({"last_failed_mutation": restarted.last_failed_mutation}, [{
        "type": "function_call_output", "call_id": call.action_id,
        "output": canonical_json(result.model_dump(mode="json")),
    }])
    assert view["last_failed_mutation"]["mutation_failure"] == failure
    assert view["last_failed_mutation"]["replacement_delivery"] == (
        "preceding_function_call_arguments"
    )
