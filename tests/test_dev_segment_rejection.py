"""Rejected batches can cross size boundaries without becoming completed actions."""
from __future__ import annotations

import pytest
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_dev_segments import assert_submitted, configured, records
from test_dev_segments import no_network as no_network

from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner, segments
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.errors import RecoveryError
from patchloop.util import canonical_json


class RejectedEdits(MockDevAdapter):
    def __init__(self, repeats=1):
        super().__init__("csv-quoted-newline")
        self.repeats = repeats
        self.rejected = 0

    def next_turn(self, context, tools):
        turn = super().next_turn(context, tools)
        call = turn.tool_calls[0]
        if call.name == "replace_text" and self.rejected < self.repeats:
            self.rejected += 1
            turn.tool_calls = [call.model_copy(update={
                "action_id": f"rejected-{self.rejected}-{i}",
            }) for i in range(2)]
        return turn


@pytest.mark.parametrize("limit,crash,repeats", [
    ("tokens", None, 1),
    ("encrypted_item_bytes", None, 1),
    ("tokens", segments.PREPARED_EVENT, 1),
    ("tokens", "input_count_finished", 1),
    ("tokens", None, 2),
])
def test_rejected_edits_cross_size_boundary_with_correction_budget_intact(
    tmp_path, monkeypatch, limit, crash, repeats,
):
    request, inputs, counted, views = configured(
        monkeypatch, tmp_path, script=RejectedEdits(repeats),
        oversized_at=(1,) if limit == "encrypted_item_bytes" else (),
    )
    if limit == "tokens":
        count = runner.OpenAIResponsesAdapter.count_input_tokens_v2

        def tokens(self, payload, **kwargs):
            normal = count(self, payload, **kwargs)
            return 60_001 if len(counted) == 3 else normal

        monkeypatch.setattr(runner.OpenAIResponsesAdapter, "count_input_tokens_v2", tokens)
    if crash:
        def at_correction(payload):
            if crash == segments.PREPARED_EVENT:
                return payload["reason"] == "input_tokens"
            return len(counted) == 4  # Fresh correction counted, not yet dispatched.

        _crash_journal_once(monkeypatch, event_type=crash, when="after",
                            predicate=at_correction)
        with pytest.raises(_SimulatedCrash):
            runner.run_dev(request)
        journal, _ = records(request)
        request = request.model_copy(update={"resume_run_id": journal.run_id})

    result = runner.run_dev(request)["runs"][0]
    if repeats == 1:
        assert_submitted(result)
        assert result["accepted_mutations"] == 1
        assert len(inputs) == 5
    else:
        assert result["terminal"] == "PROTOCOL_VIOLATION"
        assert result["accepted_mutations"] == 0
        assert len(inputs) == 3
    assert len(counted) == len(inputs) + (limit == "tokens")
    assert result["call_counts"]["model"] == len(inputs)
    assert "INVALID_TOOL_BATCH" in canonical_json(views[2])
    assert views[2]["current_diff"] == views[1]["current_diff"]
    assert views[2]["remaining_budget"]["consecutive_protocol_corrections"] == 0
    assert views[2]["remaining_budget"]["model_calls"] < views[1]["remaining_budget"]["model_calls"]
    assert not any(i.get("type") in {"reasoning", "function_call", "function_call_output"}
                   for i in inputs[2])
    journal, store = records(request)
    events = journal.events()
    correction, = [e for e in events if e["event_type"] == "protocol_correction"]
    rejected_turn = correction["payload"]["turn_id"]
    assert not any(e["payload"].get("turn_id") == rejected_turn for e in events
                   if e["event_type"] in {"tool_batch_started", "tool_batch_finished"})
    assert not any(e["payload"].get("action_id", "").startswith("rejected-") for e in events
                   if e["event_type"] in {"action_started", "action_finished"})
    for event in events:
        if event["event_type"] == "turn_started":
            runner._load_active_model_input(event["payload"], store, context_policy=segments.POLICY)
    before = journal.path.read_bytes()
    assert runner.run_dev(request.model_copy(update={"resume_run_id": journal.run_id}))[
        "runs"][0] == result
    assert journal.path.read_bytes() == before


@pytest.mark.parametrize("case", [
    "rejected", "missing_tool", "missing_rejection", "other_turn", "stale", "started", "other_code",
])
def test_handoff_requires_current_unstarted_batch_rejection(tmp_path, case):
    journal = DevJournal(tmp_path, "run_dev_rejectedsegment")
    store = ArtifactStore(tmp_path / "artifacts")
    state = {"public_task": {"task_id": "fixture"}}
    base = [{"role": "system", "content": "fixture"},
            {"role": "user", "content": canonical_json(state)},
            {"role": "developer", "content": "fixture state"}]
    correction = {"turn_id": "other" if case == "other_turn" else "t1",
                  "code": {"missing_tool": "MISSING_REQUIRED_TOOL", "other_code": "unknown"}.get(
                      case, "INVALID_TOOL_BATCH")}
    with journal.execution_lock():
        previous = segments.start(journal, store, base=base, state=state, reason="initial",
                                  parent_input_artifact=None)
        journal.append("turn_started", {"turn_id": "t1"})
        if case == "stale":
            journal.append("protocol_correction", correction)
        journal.append("turn_decision_recorded", {"turn_id": "t1"})
        if case == "started":
            journal.append("tool_batch_started", {"turn_id": "t1"})
        if case not in {"stale", "missing_rejection"}:
            journal.append("protocol_correction", correction)
        assert segments.boundary_reason(journal, previous) is None
        if case not in {"rejected", "missing_tool"}:
            with pytest.raises(RecoveryError, match="unfinished tool batch"):
                segments.start(journal, store, base=base, state=state, reason="input_tokens",
                               parent_input_artifact=None, prepare=True)
            return
        pending = segments.start(journal, store, base=base, state=state, reason="input_tokens",
                                 parent_input_artifact=None, prepare=True)
        assert pending["reviewed_through_sequence"] == previous["reviewed_through_sequence"]
        assert pending["last_exchange_turn_id"] == "t1"
        assert pending["last_batch_turn_id"] is None
        assert segments.commit(journal, store) == pending
        assert runner._pending_protocol_correction(journal) == correction
