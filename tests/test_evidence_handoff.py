from __future__ import annotations

import copy
import json
from pathlib import Path

import httpx
import pytest
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_dev_segments import assert_submitted, configured, records

from patchloop.dev import runner, segments
from patchloop.dev.contracts import DevModelTurn, RequestedTool
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND, public_exchanges


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("handoff tests must not dispatch real network requests")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


class FocusAdapter(MockDevAdapter):
    inspected = False

    def _next_action(self, context, tools):
        turn = super()._next_action(context, tools)
        if turn.tool_calls[0].name != "finish_task" or self.inspected:
            return turn
        self.inspected = True
        state = json.loads(context)
        action_id = state["recent_checks"][-1]["action_id"]
        return DevModelTurn(tool_calls=[RequestedTool(
            name="read_file", action_id="focus-extra-read",
            arguments={"path": self.mutation.path, "start_line": 1, "end_line": 80},
            turn_decision={"mode": "inspect", "basis": "Compare the check with the source.",
                           "evidence_goal": "Does this check address the changed behavior?",
                           "memory_update": {"findings": [], "open_question": {
                               "text": "What does this check actually cover?", "evidence": [
                                   {"kind": "tool_result", "action_id": action_id,
                                    "role": "primary"},
                               ]}}},
        )])


def has_optional_check(items):
    ids = {i["call_id"] for i in public_exchanges(items, archive_kind=PUBLIC_EVIDENCE_KIND)
           if i["type"] == "function_call_output"}
    return "focus-extra-read" in ids and any(i.startswith("mock-visible-check-") for i in ids)


@pytest.mark.parametrize("limit", [None, "tokens", "bytes", "unknown"])
def test_optional_result_delivery_fallback_and_unknown_stop(tmp_path, monkeypatch, limit):
    request, inputs, counted, views = configured(
        monkeypatch, tmp_path, script=FocusAdapter("csv-quoted-newline"),
    )
    original_count = runner.OpenAIResponsesAdapter.count_input_tokens_v2
    original_sizes = segments.request_sizes

    def count(self, payload, **kwargs):
        if limit in {"tokens", "unknown"} and has_optional_check(payload["input"]):
            counted.append(copy.deepcopy(payload["input"]))
            if limit == "unknown":
                raise TimeoutError("unknown fake count")
            return segments.MAX_INPUT_TOKENS + 1
        return original_count(self, payload, **kwargs)

    def sizes(payload):
        result = original_sizes(payload)
        if limit == "bytes" and has_optional_check(payload["input"]):
            result["request_bytes"] = segments.MAX_REQUEST_BYTES + 1
        return result

    monkeypatch.setattr(runner.OpenAIResponsesAdapter, "count_input_tokens_v2", count)
    monkeypatch.setattr(segments, "request_sizes", sizes)
    result = runner.run_dev(request)["runs"][0]
    journal, store = records(request)
    prepared = [e["payload"] for e in journal.events()
                if e["event_type"] == segments.PREPARED_EVENT]
    committed = [e["payload"] for e in journal.events() if e["event_type"] == segments.EVENT]
    if limit == "unknown":
        assert result["terminal"] == "COUNT_TIMEOUT_OR_UNKNOWN"
        assert len(inputs) == 4 and len(counted) == 5
        assert len(prepared) == 3 and len(committed) == 2
        before = journal.path.read_bytes()
        assert runner.run_dev(request.model_copy(update={"resume_run_id": journal.run_id}))[
            "runs"][0] == result
        assert journal.path.read_bytes() == before and len(counted) == 5
        return
    assert_submitted(result)
    assert len(inputs) == 5 and len(counted) == (6 if limit == "tokens" else 5)
    assert len(committed) == 3
    assert len(prepared) == (3 if limit is None else 4)
    final = views[-1]["working_notes"]["open_question"]
    manifest = segments.load_binding(committed[-1], store)["evidence_manifest"]
    assert final == manifest["question"]
    assert final["evidence_delivery"] == ("complete" if limit is None else "incomplete")
    assert final["evidence"][0]["execution"]["passed"] is True
    assert final["evidence"][0]["behavior_coverage"] == "not_assessed"
    assert has_optional_check(inputs[-1]) == (limit is None)
    assert not any(i.get("type") == "reasoning" for i in inputs[-1])
    assert len([e for e in journal.events() if e["event_type"] == "action_finished"
                and e["payload"]["result"]["tool"] == "run_check"]) == 1
    assert result["accepted_mutations"] == 1
    if limit is not None:
        assert prepared[-2]["previous_segment_id"] == prepared[-1]["previous_segment_id"]
        assert manifest["optional_bodies_omitted"] is True


@pytest.mark.parametrize("boundary", [
    segments.PREPARED_EVENT, "input_count_finished", segments.EVENT,
])
@pytest.mark.parametrize("fallback", [False, True])
def test_focused_candidate_count_commit_recovery(tmp_path, monkeypatch, boundary, fallback):
    request, inputs, counted, views = configured(
        monkeypatch, tmp_path, script=FocusAdapter("csv-quoted-newline"),
    )
    original_count = runner.OpenAIResponsesAdapter.count_input_tokens_v2

    def count(self, payload, **kwargs):
        tokens = original_count(self, payload, **kwargs)
        return (segments.MAX_INPUT_TOKENS + 1
                if fallback and has_optional_check(payload["input"]) else tokens)

    monkeypatch.setattr(runner.OpenAIResponsesAdapter, "count_input_tokens_v2", count)

    def focused(payload):
        if boundary == "input_count_finished":
            return len(counted) == 6 if fallback else has_optional_check(counted[-1])
        manifest = json.loads(Path(
            payload["handoff_artifact"]["path"]).read_text(encoding="utf-8"))[
                "evidence_manifest"]
        return manifest["optional_bodies_omitted"] if fallback else bool(
            manifest["optional_action_ids"])

    _crash_journal_once(monkeypatch, event_type=boundary, predicate=focused, when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, store = records(request)
    binding, candidate = segments.active(journal, store)
    assert candidate["evidence_manifest"]["optional_bodies_omitted"] == fallback
    result = runner.run_dev(request.model_copy(update={"resume_run_id": journal.run_id}))["runs"][0]
    assert_submitted(result)
    assert len(inputs) == 5 and len(counted) == (6 if fallback else 5)
    final_binding, _ = segments.active(journal, store, committed_only=True)
    assert final_binding == binding
    assert views[-1]["working_notes"]["open_question"] == candidate["evidence_manifest"]["question"]
    assert result["accepted_mutations"] == 1
