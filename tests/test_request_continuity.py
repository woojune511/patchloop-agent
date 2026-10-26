"""Fresh stage grammar and exact correction drafts across rollover/recovery."""

from __future__ import annotations

import copy
import json
from dataclasses import replace

import pytest
from test_dev_completion_resources import Gateway
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_dev_segments import assert_submitted, configured, records
from test_original_obligation_admission import pending_snapshot, policy

from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn, PublicTurnDecision, RequestedTool
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.tools import dev_tool_schemas, validate_tool_batch
from patchloop.errors import ContractError


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("request continuity tests must not use the network")
    monkeypatch.setattr("socket.socket.connect", forbidden)


def probe_schema(**kwargs):
    return next(row for row in dev_tool_schemas(
        finish_enabled=False, probe_policy="cases-v1", allowed_tools={"run_probe", "stop_task"},
        **kwargs) if row["name"] == "run_probe")


def test_probe_modes_match_the_stage_and_keep_diagnosis_small():
    general = probe_schema()
    assert general["parameters"]["properties"]["call_path"] == {"type": "null"}
    acquisition = probe_schema(original_acquisition_pending=True)
    fields = acquisition["parameters"]["properties"]
    assert fields["purpose"]["properties"]["kind"]["enum"] == ["original_requirement"]
    assert fields["python_source"]["type"] == fields["question"]["type"] == "string"
    assert fields["call_path"] == fields["replay_action_id"] == {"type": "null"}
    assert fields["case_id"] == fields["reference_action_id"] == {"type": "null"}
    assert fields["save_program"]["enum"] == [False]
    assert fields["purpose"]["properties"]["corrects_action_id"] == {"type": "null"}
    diagnosis = probe_schema(path_diagnosis_pending=True)
    assert set(diagnosis["parameters"]["properties"]) == {"focus"}


@pytest.mark.parametrize("change", [
    {"purpose": {"kind": "helper"}}, {"replay_action_id": "old"},
    {"call_path": {"focus": "candidate"}},
    {"case_id": "helper-case"}, {"reference_action_id": "helper"}, {"save_program": True},
])
def test_unoffered_probe_mode_is_rejected_before_dispatch(change):
    call = RequestedTool(name="run_probe", action_id="original", arguments={
        "purpose": {"kind": "original_requirement"}, "python_source": "print('observed')",
        "replay_action_id": None, "call_path": None,
    }, turn_decision=PublicTurnDecision(mode="verify", basis="Test the original call."))
    assert validate_tool_batch([call], original_acquisition_pending=True) == "single_action"
    call.arguments.update(change)
    with pytest.raises(ContractError, match="original acquisition requires"):
        validate_tool_batch([call], original_acquisition_pending=True)
    # Stored old batches retain their original mode contract.
    assert validate_tool_batch([call]) == "single_action"


def test_parallel_generation_requires_current_read_batch_capacity():
    gateway = Gateway()
    current = policy(gateway, pending_snapshot(gateway))
    assert runner._parallel_tool_calls(current)
    assert not runner._parallel_tool_calls(replace(current, max_parallel_reads=1))
    assert not runner._parallel_tool_calls(replace(
        current, allowed_tools=frozenset({"replace_text", "stop_task"})))
    assert not runner._parallel_tool_calls(policy(gateway, pending_snapshot(gateway, actions=6)))


class DoubleEditThenCorrect(MockDevAdapter):
    """Two proposed edits are data only until a corrected single action is returned."""

    def next_turn(self, context, tools):
        state = json.loads(context)
        correction = state.get("protocol_correction", {})
        if correction.get("code") == "INVALID_TOOL_BATCH":
            packet = correction["rejected_drafts"]
            assert packet["execution_status"] == "not_executed"
            assert len(packet["drafts"]) == 2
            assert packet["drafts"][1]["arguments"]["new_text"] == "unexecuted test proposal"
            return DevModelTurn(tool_calls=[RequestedTool(
                name="replace_text", action_id="corrected-single-edit",
                arguments=copy.deepcopy(packet["drafts"][0]["arguments"]),
                preserve_annotation_presence=True,
            )])
        turn = super().next_turn(context, tools)
        if turn.tool_calls[0].name == "replace_text":
            first = turn.tool_calls[0].model_copy(update={"action_id": "rejected-source"})
            second = first.model_copy(update={"action_id": "rejected-test", "arguments": {
                **first.arguments, "path": "tests/test_parser.py",
                "old_text": "unobserved test anchor", "new_text": "unexecuted test proposal",
            }})
            return DevModelTurn(tool_calls=[first, second])
        return turn


@pytest.mark.parametrize("crash", [None, "turn_decision_recorded", "protocol_correction"])
def test_rejected_bodies_survive_encrypted_rollover_and_resume(tmp_path, monkeypatch, crash):
    request, inputs, counted, views = configured(
        monkeypatch, tmp_path, oversized_at=(1,),
        script=DoubleEditThenCorrect("csv-quoted-newline"))
    if crash:
        _crash_journal_once(monkeypatch, event_type=crash, when="after", predicate=lambda p: (
            p.get("code") == "INVALID_TOOL_BATCH" or any(
                call["action_id"] == "rejected-source" for call in p.get("tool_calls", []))))
        with pytest.raises(_SimulatedCrash):
            runner.run_dev(request)
        journal, _ = records(request)
        request = request.model_copy(update={"resume_run_id": journal.run_id})
    assert_submitted(runner.run_dev(request)["runs"][0])
    journal, _ = records(request)
    corrections = [e["payload"] for e in journal.events()
                   if e["event_type"] == "protocol_correction"]
    assert len(corrections) == 1
    packet = corrections[0]["rejected_drafts"]
    assert views[2]["protocol_correction"]["rejected_drafts"] == packet
    assert len(inputs) == len(counted) == 5
    assert inputs[2] == counted[2]
    boundaries = [e["payload"] for e in journal.events()
                  if e["event_type"] == "context_segment_started"]
    assert any("encrypted_item_bytes" in row["reason"] for row in boundaries)
    edits = [e["payload"] for e in journal.events()
             if e["event_type"] == "action_started" and e["payload"]["tool"] == "replace_text"]
    assert [edit["action_id"] for edit in edits] == ["corrected-single-edit"]
    assert packet["drafts"][0]["arguments"] == edits[0]["arguments"]
    assert packet["drafts"][0]["input_hash"] == edits[0]["input_hash"]


def test_count_and_dispatch_use_the_same_parallel_flag(tmp_path, monkeypatch):
    request, _, _, views = configured(monkeypatch, tmp_path)
    adapter = runner.OpenAIResponsesAdapter
    count_original, execute_original = adapter.count_input_tokens_v2, adapter.execute_request
    counts, dispatched = [], []

    def count(self, payload, **kwargs):
        counts.append(copy.deepcopy(payload))
        return count_original(self, payload, **kwargs)

    def execute(self, payload, **kwargs):
        dispatched.append(copy.deepcopy(payload))
        return execute_original(self, payload, **kwargs)

    monkeypatch.setattr(adapter, "count_input_tokens_v2", count)
    monkeypatch.setattr(adapter, "execute_request", execute)
    assert_submitted(runner.run_dev(request)["runs"][0])
    assert len(counts) == len(dispatched) == len(views)
    for counted, sent, state in zip(counts, dispatched, views, strict=True):
        assert counted["parallel_tool_calls"] == sent["parallel_tool_calls"]
        if not {"read_file", "search_files"} & set(state["available_tool_names"]):
            assert sent["parallel_tool_calls"] is False
    assert dispatched[0]["parallel_tool_calls"] is True
