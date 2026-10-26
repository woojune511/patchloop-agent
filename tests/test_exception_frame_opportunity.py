"""Finite source-ready scheduling tests; registered reads and edits, stub probes only."""
from __future__ import annotations

import json

import pytest
from test_dev_probes import FakeProbe
from test_exception_frame_repair import (
    common,
    edit_call,
    no_external,  # noqa: F401 -- keep the imported autouse external-call guard.
    read_call,
    run,
    stop_call,
)

from diagnostics import exception_frame_repair as diagnostic
from diagnostics.checkpoint_continuation import ScriptedClient
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool

PACKET = {"sources": []}
EDIT_OR_STOP = frozenset({"replace_text", "stop_task"})
WITH_PROBE = EDIT_OR_STOP | {"run_probe"}
WITH_READS = WITH_PROBE | {"read_file", "search_files"}


def _probe_call():
    return {"name": "run_probe", "action_id": "diagnose", "arguments": {
        "question": "Does the public behavior hold?", "python_source": "assert True",
        "purpose": None, "replay_action_id": None, "call_path": None,
        "turn_decision": {"mode": "verify", "basis": "Check the public repair premise.",
                          "evidence_goal": None, "memory_update": None}}}


def _factory(gateway_factory, *, observe_seed=False):
    def build():
        gateway, journal, workspace = gateway_factory()
        gateway.probe_sandbox = FakeProbe(status="passed")
        if observe_seed:
            observed = gateway.execute(RequestedTool(
                name="read_file", action_id="host-source-anchor",
                arguments={"path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": 90},
                turn_decision=PublicTurnDecision(mode="inspect", basis="Observe the saved source.",
                                                evidence_goal="Register the source edit anchor.")))
            assert observed.status == "succeeded"
        return gateway, journal, workspace
    return build


def _run(gateway_factory, steps, *, cap="1.20", observe_seed=False):
    return run(_factory(gateway_factory, observe_seed=observe_seed), steps, cap=cap,
               profile=diagnostic.OPPORTUNITY_PROFILE, source_packet=PACKET)


def _opportunity(request):
    assert request["input"][-1]["role"] == "developer"
    value = json.loads(request["input"][-1]["content"])["opportunity"]
    assert value["allowed_tools"] == sorted(item["name"] for item in request["tools"])
    return value


def _finished(journal):
    return [event["payload"]["result"] for event in journal.events()
            if event["event_type"] == "action_finished"]


def _started(journal):
    return [event["payload"] for event in journal.events()
            if event["event_type"] == "provider_call_started"]


def _assert_counted_input(counted, dispatched):
    assert {key: value for key, value in counted.items() if key != "timeout"} == {
        key: dispatched[key] for key in counted if key != "timeout"}


def test_response_and_tool_boundaries_protect_the_successor():
    # Responses include the current correction when one is pending.
    cases = [
        (8, 12, False, False, WITH_READS, 4, 2),
        (8, 4, False, False, WITH_READS, 2, 2),
        (3, 3, False, False, WITH_READS, 1, 2),
        (8, 2, False, False, WITH_PROBE, 0, 1),
        (2, 12, False, False, WITH_PROBE, 0, 1),
        (1, 12, False, False, EDIT_OR_STOP, 0, 0),
        (1, 12, False, True, WITH_PROBE, 0, 1),
        (1, 12, True, True, EDIT_OR_STOP | {"read_file", "search_files"}, 4, 1),
        (0, 12, False, True, EDIT_OR_STOP, 0, 0),
        (0, 12, False, False, frozenset(), 0, 0),
        (8, 0, False, False, frozenset(), 0, 0),
    ]
    for normal, tools, used, correction, allowed, parallel, successor in cases:
        opportunity = diagnostic.repair_opportunity(
            normal_remaining=normal, tool_remaining=tools, probe_used=used,
            correction=correction)
        assert opportunity.allowed == allowed
        assert isinstance(opportunity.allowed, frozenset)
        assert (opportunity.max_parallel_reads, opportunity.successor_calls) == (
            parallel, successor)
        assert opportunity.public() == {"allowed_tools": sorted(allowed),
            "max_parallel_reads": parallel, "reserved_successor_calls": successor}


def test_ten_reads_leave_one_probe_and_one_actual_edit(gateway_factory):
    steps = [[read_call(str(i)) for i in range(start, end)]
             for start, end in ((0, 4), (4, 8), (8, 10))]
    actual, client, journal, _ = _run(gateway_factory, steps + [[_probe_call()], [edit_call()]])
    assert actual["terminal"] == "CANDIDATE_PRODUCED"
    assert (actual["normal_calls"], actual["tool_actions"], actual["new_mutations"],
            actual["diagnostic_probes"]) == (5, 12, 1, 1)
    opportunities = [_opportunity(request) for request in client.created]
    assert [row["max_parallel_reads"] for row in opportunities] == [4, 4, 2, 0, 0]
    assert [row["reserved_successor_calls"] for row in opportunities] == [2, 2, 2, 1, 0]
    assert {row["tool"] for row in _finished(journal)[-2:]} == {"run_probe", "replace_text"}
    assert len(client.counted) == len(client.created) == 5


def test_six_single_reads_preserve_the_last_two_normal_responses(gateway_factory):
    steps = [[read_call(str(i))] for i in range(6)] + [[_probe_call()], [edit_call()]]
    actual, client, journal, _ = _run(gateway_factory, steps)
    assert actual["terminal"] == "CANDIDATE_PRODUCED" and actual["new_mutations"] == 1
    assert (actual["normal_calls"], actual["correction_calls"], actual["tool_actions"]) == (8, 0, 8)
    assert set(_opportunity(client.created[-2])["allowed_tools"]) == WITH_PROBE
    assert set(_opportunity(client.created[-1])["allowed_tools"]) == EDIT_OR_STOP
    assert [row["tool"] for row in _finished(journal)[-2:]] == ["run_probe", "replace_text"]


def test_oversized_read_batch_is_rejected_and_correction_keeps_both_successors(gateway_factory):
    steps = [[read_call(str(i)) for i in range(start, end)] for start, end in ((0, 4), (4, 8))]
    steps += [[read_call("rejected-" + str(i)) for i in range(3)],
              [read_call("correction-" + str(i)) for i in range(2)],
              [_probe_call()], [edit_call()]]
    actual, client, journal, _ = _run(gateway_factory, steps)
    assert actual["terminal"] == "CANDIDATE_PRODUCED"
    assert (actual["normal_calls"], actual["correction_calls"], actual["tool_actions"]) == (
        5, 1, 12)
    assert not any(row["action_id"].startswith("rejected-") for row in _finished(journal))
    correction = client.created[3]
    assert correction["max_output_tokens"] == diagnostic.CORRECTION_OUTPUT
    assert _opportunity(correction)["max_parallel_reads"] == 2
    assert _opportunity(correction)["reserved_successor_calls"] == 2
    assert _started(journal)[3]["future_cost_reserve_nanos"] == 450_000_000
    assert len(client.counted) == len(client.created) == 6


def test_boundary_protocol_correction_can_probe_then_use_last_normal_response(gateway_factory):
    steps = [[read_call(str(i))] for i in range(6)] + [[], [_probe_call()], [edit_call()]]
    actual, client, journal, _ = _run(gateway_factory, steps)
    assert actual["terminal"] == "CANDIDATE_PRODUCED"
    assert (actual["normal_calls"], actual["correction_calls"], actual["tool_actions"],
            actual["new_mutations"]) == (8, 1, 8, 1)
    correction = client.created[-2]
    assert correction["max_output_tokens"] == 25_000
    assert set(_opportunity(correction)["allowed_tools"]) == WITH_PROBE
    assert _opportunity(correction)["reserved_successor_calls"] == 1
    assert _started(journal)[-2]["future_cost_reserve_nanos"] == 225_000_000
    assert set(_opportunity(client.created[-1])["allowed_tools"]) == EDIT_OR_STOP


@pytest.mark.parametrize("cap,probe,reserve,narrowings", [
    ("0.50", True, 382_500_000, 1),
    ("0.20", False, 157_500_000, 2),
])
def test_unaffordable_exploration_recounts_a_narrower_request_before_repair(
        gateway_factory, cap, probe, reserve, narrowings):
    steps = ([[_probe_call()]] if probe else []) + [[edit_call()]]
    actual, client, journal, _ = _run(gateway_factory, steps, cap=cap, observe_seed=True)
    assert actual["terminal"] == "CANDIDATE_PRODUCED" and actual["new_mutations"] == 1
    assert actual["billing_known"] and not actual["stop_remaining"]
    assert actual["normal_calls"] == len(steps)
    assert actual["diagnostic_probes"] == int(probe)
    expected = WITH_PROBE if probe else EDIT_OR_STOP
    assert set(_opportunity(client.created[0])["allowed_tools"]) == expected
    assert _started(journal)[0]["future_cost_reserve_nanos"] == reserve
    changes = [event for event in journal.events()
               if event["event_type"] == "opportunity_cost_narrowed"]
    assert len(changes) == narrowings
    assert len(client.counted) == len(client.created) + narrowings
    assert set(_opportunity(client.counted[0])["allowed_tools"]) == WITH_READS
    _assert_counted_input(client.counted[narrowings], client.created[0])
    if probe:
        _assert_counted_input(client.counted[-1], client.created[-1])


def test_reserved_opportunity_does_not_force_a_probe_or_edit(gateway_factory):
    actual, client, journal, _ = _run(gateway_factory,
        [[read_call(str(i))] for i in range(6)] + [[stop_call()]])
    assert actual["terminal"] == "AGENT_STOPPED"
    assert (actual["normal_calls"], actual["tool_actions"], actual["new_mutations"],
            actual["diagnostic_probes"]) == (7, 7, 0, 0)
    assert set(_opportunity(client.created[-1])["allowed_tools"]) == WITH_PROBE
    assert _finished(journal)[-1]["tool"] == "stop_task"


def test_uncertain_recount_stops_without_generation_or_another_reduction(
        gateway_factory, monkeypatch):
    original = ScriptedClient.count

    def fail_second_count(self, **request):
        value = original(self, **request)
        if len(self.counted) == 2:
            raise TimeoutError("uncertain narrowed count")
        return value

    monkeypatch.setattr(ScriptedClient, "count", fail_second_count)
    actual, client, journal, _ = _run(gateway_factory, [[stop_call()]], cap="0.50")
    assert actual["terminal"] == "COUNT_UNCERTAIN"
    assert actual["stop_remaining"] and not actual["billing_known"]
    assert len(client.counted) == 2 and not client.created
    assert actual["tool_actions"] == actual["new_mutations"] == 0
    assert len([e for e in journal.events()
                if e["event_type"] == "opportunity_cost_narrowed"]) == 1


def test_legacy_first_requests_keep_their_existing_tool_and_message_contract(smoke_package):
    data = common(smoke_package.public)
    ordinary = diagnostic.request_payload(data, "B")
    explicit = diagnostic.request_payload(data, "B", profile=diagnostic.DEFAULT_PROFILE)
    assert ordinary == explicit
    source_ready = diagnostic.request_payload(data, "B", profile=diagnostic.SOURCE_READY_PROFILE,
                                               source_packet=PACKET)
    assert [row["role"] for row in ordinary["input"]] == ["system", "user"]
    assert [row["role"] for row in source_ready["input"]] == ["system", "user", "user"]
    assert ordinary["tools"] == source_ready["tools"]
    assert ordinary["max_output_tokens"] == source_ready["max_output_tokens"] == 40_000
