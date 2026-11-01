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
    gateway.read_range_only = False
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


def run(gateway, loaded, cycle, steps, *, cap="2.40", client=None):
    client = client or ScriptedClient(steps)
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


class InputBoundaryClient(ScriptedClient):
    """Simulate a counted boundary, not tokenization or real provider acceptance."""

    def __init__(self, steps, *, fresh_too_large=False, count_uncertain=False,
                 normal_after=None):
        super().__init__(steps)
        self.fresh_too_large = fresh_too_large
        self.count_uncertain = count_uncertain
        self.normal_after = normal_after

    def count(self, **request):
        correction = json.loads(request["input"][-1]["content"])["protocol_correction"]
        opaque = any(item.get("type") == "reasoning" for item in request["input"])
        boundary = bool(correction) or (correction is None
            and self.normal_after is not None and len(self.created) == self.normal_after)
        self.input_tokens = 68_124 if boundary and (opaque or self.fresh_too_large) else 100
        if boundary and self.count_uncertain:
            raise TimeoutError("uncertain count")
        return super().count(**request)


def null_helper():
    return {"name": "run_probe", "action_id": "missing-code", "arguments": {
        "question": "Observe the original caller", "python_source": None,
        "memory_update": None}}


def test_normal_handoff_preserves_seed_observation_before_first_edit(
    gateway_factory, tmp_path, monkeypatch,
):
    gateway, journal, loaded, cycle, base = setup(
        gateway_factory, tmp_path, monkeypatch, seed=True)
    seed_hash = gateway.current_diff_hash
    whole = read("whole-after-handoff")
    whole["arguments"].update(start_line=None, end_line=None)
    client = InputBoundaryClient([
        [{"name": "recheck_original", "action_id": "observe-seed", "arguments": {}}],
        [whole], [edit_call()], [stop_call()]], normal_after=1)
    actual, _ = run(gateway, loaded, cycle, [], client=client)
    assert actual["terminal"] == "AGENT_STOPPED" and actual["new_mutations"] == 1
    assert actual["normal_calls"] == actual["tool_actions"] == len(client.created) == 4
    assert actual["correction_calls"] == actual["diagnostic_probes"] == 0
    assert actual["context_handoffs"] == actual["original_requests"] == 1
    assert actual["host_original_actions"] == 3 and base.dispatches == 1
    assert actual["candidate_diff_hash"] != seed_hash
    assert actual["original_recheck"]["candidate_diff_hash"] == gateway.current_diff_hash
    assert actual["original_recheck"]["status"] == "failed"
    fresh = client.created[1]
    assert fresh["max_output_tokens"] == 40_000
    assert not any(item.get("type") in {"reasoning", "function_call", "function_call_output"}
                   for item in fresh["input"])
    original = json.loads(fresh["input"][1]["content"])["current_original_recheck"]
    assert original["candidate_diff_hash"] == seed_hash and original["status"] == "failed"
    assert "F0010" in str(original["observed"])
    handoff = next(json.loads(item["content"])["state"] for item in fresh["input"]
                   if item.get("role") == "developer"
                   and json.loads(item["content"]).get("kind")
                   == "diagnostic_repair_cycle_handoff_v1")
    assert handoff["current_diff"]["diff_hash"] == seed_hash
    assert "saved bad attempt" in handoff["current_diff"]["patch"]
    assert handoff["current_original_recheck"] == original
    assert handoff["protocol_correction"] is None
    counters = handoff["counters"]
    assert counters["normal_calls"] == counters["tool_actions"] == 1
    assert counters["original_requests"] == 1
    assert counters["correction_calls"] == counters["new_mutations"] == 0
    assert counters["host_original_actions"] == 2
    remaining = json.loads(fresh["input"][-1]["content"])
    assert remaining["protocol_correction"] is None
    assert remaining["remaining"]["normal_calls"] == 15
    assert remaining["remaining"]["tool_actions"] == 23
    assert remaining["remaining"]["accepted_mutations"] == 3
    assert remaining["remaining"]["original_rechecks"] == 0
    assert "recheck_original" not in {tool["name"] for tool in fresh["tools"]}
    assert "synthetic_cipher" not in json.dumps(fresh["input"])
    assert "PRIVATE_SENTINEL" not in json.dumps(fresh["input"])
    committed = [event["payload"] for event in journal.events()
                 if event["event_type"] == "repair_context_committed"]
    assert len(committed) == 1 and committed[0]["parent_input_tokens"] == 68_124
    assert committed[0]["input_tokens"] == 100
    assert committed[0]["counters"]["correction_calls"] == 0
    assert len(client.counted) == len(client.created) + 1


def test_correction_handoff_keeps_failed_diff_and_allows_registered_original_then_revision(
    gateway_factory, tmp_path, monkeypatch,
):
    gateway, journal, loaded, cycle, _ = setup(gateway_factory, tmp_path, monkeypatch)
    first = edit_call()
    initial = first["arguments"]["old_text"]
    temporary = "# exploratory version\n" + initial
    first["arguments"]["new_text"] = temporary
    second = edit_call()
    second["action_id"] = "second-edit"
    second["arguments"]["old_text"] = temporary
    whole = read()
    whole["arguments"].update(start_line=None, end_line=None)
    steps = [[whole], [first], [null_helper()],
        [{"name": "recheck_original", "action_id": "original", "arguments": {}}],
        [read("current-source")], [second], [stop_call()]]
    client = InputBoundaryClient(steps)
    actual, _ = run(gateway, loaded, cycle, [], client=client)
    assert actual["terminal"] == "AGENT_STOPPED" and actual["new_mutations"] == 2
    assert actual["context_handoffs"] == actual["correction_calls"] == 1
    assert actual["original_requests"] == 1 and actual["diagnostic_probes"] == 0
    assert actual["normal_calls"] == 6 and actual["tool_actions"] == 6
    assert actual["original_recheck"]["status"] == "supported"
    corrected = client.created[3]
    assert corrected["max_output_tokens"] == 25_000
    assert not any(item.get("type") in {"reasoning", "function_call", "function_call_output"}
                   for item in corrected["input"])
    text = json.dumps(corrected["input"])
    assert "F0010" in text and "exploratory version" in text and "missing-code" in text
    assert "synthetic_cipher" not in text and "PRIVATE_SENTINEL" not in text
    state = json.loads(corrected["input"][-1]["content"])
    assert state["remaining"]["accepted_mutations"] == 2
    assert state["remaining"]["tool_actions"] == 22
    assert state["protocol_correction"]
    original_delivered = json.loads(client.created[4]["input"][1]["content"])
    assert original_delivered["current_original_recheck"]["candidate_receipt_reused"]
    assert "recheck_original" not in {t["name"] for t in client.created[4]["tools"]}
    events = journal.events()
    assert sum(e["event_type"] == "repair_context_prepared" for e in events) == 1
    committed = next(e["payload"] for e in events if e["event_type"] == "repair_context_committed")
    assert committed["input_tokens"] == 100 and "segment-1" in committed["count_id"]
    assert len(client.counted) == len(client.created) + 1


def test_handoff_cannot_renew_global_correction(
    gateway_factory, tmp_path, monkeypatch,
):
    gateway, _, loaded, cycle, _ = setup(gateway_factory, tmp_path, monkeypatch)
    client = InputBoundaryClient([[null_helper()], [null_helper()], [stop_call()]])
    actual, _ = run(gateway, loaded, cycle, [], client=client)
    assert actual["terminal"] == "CORRECTION_EXHAUSTED"
    assert actual["normal_calls"] == actual["correction_calls"] == 1
    assert len(client.created) == 2 and actual["context_handoffs"] == 1


def test_fresh_public_seed_over_limit_stops_without_repeated_handoffs(
    gateway_factory, tmp_path, monkeypatch,
):
    gateway, journal, loaded, cycle, _ = setup(gateway_factory, tmp_path, monkeypatch)
    client = InputBoundaryClient([[null_helper()], [stop_call()]], fresh_too_large=True)
    actual, _ = run(gateway, loaded, cycle, [], client=client)
    assert actual["terminal"] == "INPUT_LIMIT" and len(client.created) == 1
    assert actual["correction_calls"] == actual["context_handoffs"] == 0
    assert sum(e["event_type"] == "repair_context_prepared" for e in journal.events()) == 1


def test_uncertain_count_never_falls_back_to_a_handoff(
    gateway_factory, tmp_path, monkeypatch,
):
    gateway, journal, loaded, cycle, _ = setup(gateway_factory, tmp_path, monkeypatch)
    client = InputBoundaryClient([[null_helper()], [stop_call()]], count_uncertain=True)
    actual, _ = run(gateway, loaded, cycle, [], client=client)
    assert actual["terminal"] == "COUNT_UNCERTAIN" and actual["stop_remaining"]
    assert len(client.created) == 1 and actual["correction_calls"] == 0
    assert not any(e["event_type"] == "repair_context_prepared" for e in journal.events())
