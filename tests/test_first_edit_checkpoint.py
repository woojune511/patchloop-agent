"""Public checkpoint representation and first edit with scripted model/check receipts."""
from __future__ import annotations

import copy
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from test_exception_frame_repair import edit_call, no_external, stop_call  # noqa: F401
from test_feedback_repair_cycle import read, setup
from test_repair_cycle import RecordedGateway

from diagnostics import first_edit_checkpoint as d
from diagnostics.checkpoint_continuation import ScriptedClient
from patchloop.dev.contracts import RequestedTool
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.util import canonical_json, sha256_json


def evidence():
    fact = {"negative_observation": "original caller retains F0010 " * 30}
    checkpoint = SimpleNamespace(bodies=[
        {"public_feedback": fact, "initial_source": []},
        {"kind": "old-handoff", "state": {"counters": {"normal_calls": 14},
            "protocol_correction": None, "current_original_recheck": fact}},
        {"helper_output": "relative root failed; absolute root passed"}])
    before = copy.deepcopy(checkpoint.bodies)
    document = d.evidence_document(checkpoint)
    assert checkpoint.bodies == before
    return {"evidence": document, "deduplicated_evidence": d.dedup.deduplicate(document)}


@pytest.mark.parametrize("stage", ["first", "correction", "after_edit"])
def test_requests_differ_only_by_lossless_evidence_with_fresh_allowances(stage):
    common = evidence()
    options = {}
    if stage == "correction":
        options.update(correction={"reason": "missing tool"}, remaining={
            "normal_calls": 1, "tool_actions": 2, "diagnostic_probes": 0,
            "original_rechecks": 0, "accepted_mutations": 1, "cost_nanos": 900_000_000})
    elif stage == "after_edit":
        options.update(remaining={"normal_calls": 1, "tool_actions": 1,
            "diagnostic_probes": 0, "original_rechecks": 0, "accepted_mutations": 0,
            "cost_nanos": 800_000_000}, original_feedback={"status": "failed", "diff": "new"})
    options["history"] = [
        {"type": "reasoning", "encrypted_content": "OPAQUE_SENTINEL"},
        {"type": "function_call", "call_id": "prior", "name": "replace_text",
         "arguments": "{}"},
        {"type": "function_call_output", "call_id": "prior",
         "output": canonical_json({"status": "failed", "error": "public error retained"})}]
    a, b = (d.request_payload(common, arm, **options) for arm in d.PROFILE.order)
    d.verify_pair(a, b)
    assert "OPAQUE_SENTINEL" not in str(a) + str(b)
    assert "public error retained" in str(a) and "public error retained" in str(b)
    names = {tool["name"] for tool in a["tools"]}
    assert names == ({"stop_task"} if stage == "after_edit" else {"replace_text", "stop_task"})
    assert not a["parallel_tool_calls"] and a["reasoning"] == {"effort": "xhigh"}
    assert a["max_output_tokens"] == (25_000 if stage == "correction" else 40_000)
    state = json.loads(a["input"][-1]["content"])
    if stage == "first":
        assert state["remaining"]["normal_calls"] == 2
        assert state["remaining"]["tool_actions"] == 2
        assert state["remaining"]["accepted_mutations"] == 1
        assert state["remaining"]["cost_nanos"] == 1_200_000_000
    assert "counters" not in common["evidence"]["saved_public_evidence"][1]["state"]
    assert d.dedup.expand(common["deduplicated_evidence"]) == common["evidence"]


@pytest.mark.parametrize("arm,failed,correction", [("A", True, False), ("B", False, True)])
def test_first_edit_rechecks_current_diff_and_delivers_result_before_stop(
    gateway_factory, tmp_path, monkeypatch, arm, failed, correction,
):
    gateway, _, loaded, cycle, baseline = setup(
        gateway_factory, tmp_path, monkeypatch, limits=d.LIMITS)
    # Host registers the source before the new model phase. It is not model action one.
    host_read = read("host-read")
    host_read["arguments"].pop("memory_update")
    gateway.execute(RequestedTool.model_validate(host_read))
    gateway.limits.max_tool_actions = 3
    gateway.limits.max_model_calls = 3
    gateway.limits.max_accepted_mutations = 1
    loaded.common = evidence()
    monkeypatch.setattr(cycle, "_gateway", lambda *_: RecordedGateway(
        cycle.journal, gateway.current_diff_hash, failed=failed))
    steps = ([[]] if correction else []) + [[edit_call()], [stop_call()]]
    client = ScriptedClient(steps)
    adapter = d.loop.OpenAIResponsesAdapter(d.loop.config(), api_key="", client=client)
    actual = d.loop.run_model(loaded, arm, gateway, adapter,
        DevCostLedger(Decimal("2.40"), pricing_for_model(d.loop.MODEL)),
        first_hash=sha256_json(d.request_payload(loaded.common, arm)), profile=d.PROFILE,
        request_builder=d.request_payload, cycle=cycle,
        minimum_correction_seconds=d.MINIMUM_CORRECTION_SECONDS)
    assert actual["terminal"] == "AGENT_STOPPED" and actual["new_mutations"] == 1
    assert actual["normal_calls"] == actual["tool_actions"] == 2
    assert actual["correction_calls"] == int(correction)
    assert actual["host_original_actions"] == 2 and baseline.dispatches == 1
    final = client.created[-1]
    assert {tool["name"] for tool in final["tools"]} == {"stop_task"}
    result = json.loads(final["input"][-1]["content"])["current_trial_original_recheck"]
    assert result["status"] == ("failed" if failed else "supported")
    assert result["candidate_diff_hash"] == gateway.current_diff_hash
    assert "PRIVATE_SENTINEL" not in str(client.created)
    assert actual["task_acceptance"] == "NOT_RUN"
    assert actual["final_verification"] == {"public": "not_run", "isolated": "not_run"}


def test_pair_validation_rejects_unrelated_condition_changes():
    common = evidence()
    a, b = (d.request_payload(common, arm) for arm in d.PROFILE.order)
    b["max_output_tokens"] = 12_000
    with pytest.raises(d.source.loop.ContractError, match="beyond lossless"):
        d.verify_pair(a, b)
