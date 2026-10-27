"""Finite real edits and scripted public receipts; no paid model or target execution."""
from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

from test_exception_frame_repair import edit_call, no_external, read_call, stop_call  # noqa: F401
from test_repair_cycle import RecordedGateway

from diagnostics import feedback_source as d
from diagnostics.checkpoint_continuation import ScriptedClient
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.errors import ContractError
from patchloop.util import sha256_json


def read(action="read"):
    call = read_call(action)
    call["arguments"].pop("turn_decision")
    call["arguments"]["memory_update"] = None
    return call


def setup(gateway_factory, tmp_path, monkeypatch, *, seed=False, limits=None):
    gateway, journal, workspace = gateway_factory()
    gateway.agent_policy = "thin"
    gateway.read_range_only = True
    gateway.deadline = ExecutionDeadline.from_remaining(600)
    gateway.limits.max_accepted_mutations = 3
    gateway.limits.max_tool_actions = 24
    if seed:
        path = workspace / "mini_data_utils/csvlite.py"
        path.write_text(path.read_text(encoding="utf-8") + "\n# saved bad attempt\n",
                        encoding="utf-8")
    monkeypatch.setattr(d, "SEED_HASH", gateway.current_diff_hash)
    loaded = SimpleNamespace(public=gateway.public_task,
        original_arguments={"python_source": "original public caller",
                            "purpose": {"kind": "helper"}},
        common={"feedback": {"public_issue": "fixture failure"},
                "source_packets": {"R0": [], "R1": []}})
    cycle = d.OriginalCallRecheck(loaded, gateway, tmp_path / "recheck",
                                 limits=limits or d.CYCLE_LIMITS)
    base = RecordedGateway(cycle.base_journal, d.host.EMPTY_DIFF)
    monkeypatch.setattr(cycle, "_baseline_gateway", lambda: base)
    monkeypatch.setattr(cycle, "_gateway", lambda *_: RecordedGateway(cycle.journal,
        gateway.current_diff_hash, failed=gateway.accepted_mutations < 2))
    return gateway, journal, loaded, cycle, base


def run(gateway, loaded, cycle, steps, *, cap="2.40"):
    client = ScriptedClient(steps)
    adapter = d.loop.OpenAIResponsesAdapter(d.loop.config(), api_key="", client=client)
    result = d.loop.run_model(loaded, "R1", gateway, adapter,
        DevCostLedger(Decimal(cap), pricing_for_model(d.loop.MODEL)),
        first_hash=sha256_json(d.request_payload(loaded.common, "R1")),
        profile=d.PROFILE, request_builder=d.request_payload, cycle=cycle)
    return result, client


def test_failed_first_edit_is_rechecked_delivered_and_repaired(
    gateway_factory, tmp_path, monkeypatch,
):
    gateway, _, loaded, cycle, base = setup(gateway_factory, tmp_path, monkeypatch)
    first = edit_call()
    initial = first["arguments"]["old_text"]
    temporary = "# exploratory version\n" + initial
    first["arguments"]["new_text"] = temporary
    second = edit_call()
    second["action_id"] = "edit-two"
    second["arguments"]["old_text"] = temporary
    actual, client = run(gateway, loaded, cycle,
                         [[read()], [first], [read("reread")], [second], [stop_call()]])
    assert actual["terminal"] == "AGENT_STOPPED" and actual["new_mutations"] == 2
    assert actual["normal_calls"] == actual["tool_actions"] == 5
    assert actual["host_original_actions"] == 3 and base.dispatches == 1
    assert actual["final_verification"] == {"public": "not_run", "isolated": "not_run"}
    assert actual["task_acceptance"] == "NOT_RUN"
    after_failure = json.loads(client.created[2]["input"][1]["content"])
    feedback = after_failure["current_original_recheck"]
    assert feedback["status"] == "failed" and "F0010" in str(feedback["observed"])
    assert "current_source" not in after_failure and "initial_source" in after_failure
    assert {tool["name"] for tool in client.created[2]["tools"]} >= {
        "read_file", "search_files", "replace_text", "run_probe"}
    after_repair = json.loads(client.created[4]["input"][1]["content"])["current_original_recheck"]
    assert after_repair["status"] == "supported"
    assert after_repair["candidate_diff_hash"] == gateway.current_diff_hash
    assert after_repair["candidate_diff_hash"] != feedback["candidate_diff_hash"]
    assert cycle.current_receipts()[1]["workspace_diff_hash"] == gateway.current_diff_hash
    assert actual["new_cost_nanos"] < 1_200_000_000


def test_retraction_does_not_finish_and_reuses_clean_failure(
    gateway_factory, tmp_path, monkeypatch,
):
    gateway, _, loaded, cycle, base = setup(gateway_factory, tmp_path, monkeypatch, seed=True)
    retract = edit_call()
    retract["arguments"].update(old_text="\n# saved bad attempt\n", new_text="")
    repair = edit_call()
    repair["action_id"] = "repair-after-retraction"
    actual, client = run(gateway, loaded, cycle,
        [[read()], [retract], [read("after-undo")], [repair], [stop_call()]])
    feedback = json.loads(client.created[2]["input"][1]["content"])["current_original_recheck"]
    assert feedback["candidate_diff_hash"] == d.host.EMPTY_DIFF
    assert feedback["status"] == "failed" and feedback["candidate_receipt_reused"]
    assert actual["new_mutations"] == 2 and actual["host_original_actions"] == 2
    assert base.dispatches == 1


def test_incomplete_original_recheck_stops_before_another_model_response(
    gateway_factory, tmp_path, monkeypatch,
):
    gateway, _, loaded, cycle, _ = setup(gateway_factory, tmp_path, monkeypatch)
    monkeypatch.setattr(cycle, "check", lambda: (_ for _ in ()).throw(
        ContractError("unknown cleanup")))
    actual, client = run(gateway, loaded, cycle, [[read()], [edit_call()], [stop_call()]])
    assert actual["terminal"] == "ORIGINAL_RECHECK_INCOMPLETE" and actual["stop_remaining"]
    assert len(client.created) == 2 and actual["original_recheck"] is None


def test_last_edit_cost_narrowing_skips_unchanged_reservation_stage(
    gateway_factory, tmp_path, monkeypatch,
):
    gateway, journal, loaded, cycle, _ = setup(gateway_factory, tmp_path, monkeypatch)
    # Match preparation, then consume the two earlier mutation opportunities.
    gateway.accepted_mutations = 2
    cycle.limits = replace(cycle.limits, accepted_edits=3)
    # A full-output future edit reserve no longer fits, but edit+final response does.
    first = d.request_payload(loaded.common, "R1", opportunity=
        d.cycle_opportunity(normal_remaining=16, tool_remaining=24, probes_remaining=2,
                            edits_remaining=1))
    client = ScriptedClient([[stop_call()]])
    adapter = d.loop.OpenAIResponsesAdapter(d.loop.config(), api_key="", client=client)
    actual = d.loop.run_model(loaded, "R1", gateway, adapter,
        DevCostLedger(Decimal("0.23"), pricing_for_model(d.loop.MODEL)),
        first_hash=sha256_json(first), profile=d.PROFILE,
        request_builder=d.request_payload, cycle=cycle)
    assert actual["terminal"] == "AGENT_STOPPED"
    assert {tool["name"] for tool in client.created[0]["tools"]} == {"replace_text", "stop_task"}
    assert any(e["event_type"] == "opportunity_cost_narrowed" for e in journal.events())


def test_insufficient_original_recheck_time_does_not_dispatch_model(
    gateway_factory, tmp_path, monkeypatch,
):
    gateway, _, loaded, cycle, _ = setup(gateway_factory, tmp_path, monkeypatch)
    gateway.deadline = ExecutionDeadline.from_remaining(100)
    actual, client = run(gateway, loaded, cycle, [[edit_call()]])
    assert actual["terminal"] == "RECHECK_TIME_UNAVAILABLE" and not client.created
