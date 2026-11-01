"""Public checkpoint representation and first edit with scripted model/check receipts."""
from __future__ import annotations

import copy
import json
import math
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
from patchloop.git_execution import run_git
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


def successful_regression(gateway):
    return SimpleNamespace(host_actions=1, needed_seconds=lambda **_: 0,
        check=lambda: {"schema": "public-regression-feedback-v1", "status": "passed",
                       "candidate_diff_hash": gateway.current_diff_hash, "checks": []})


@pytest.mark.parametrize("stage", ["first", "correction", "after_edit"])
def test_requests_differ_only_by_lossless_evidence_with_fresh_allowances(stage):
    common = evidence()
    options = {}
    if stage == "correction":
        options.update(correction={"reason": "missing tool"}, remaining={
            "normal_calls": 1, "tool_actions": 2, "diagnostic_probes": 0,
            "original_rechecks": 0, "accepted_mutations": 2, "cost_nanos": 900_000_000})
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
        assert state["remaining"]["normal_calls"] == 4
        assert state["remaining"]["tool_actions"] == 5
        assert state["remaining"]["accepted_mutations"] == 2
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
        request_builder=d.request_payload, cycle=cycle, regression=successful_regression(gateway),
        minimum_correction_seconds=d.MINIMUM_CORRECTION_SECONDS)
    assert actual["terminal"] == "AGENT_STOPPED" and actual["new_mutations"] == 1
    assert actual["normal_calls"] == actual["tool_actions"] == 2
    assert actual["correction_calls"] == int(correction)
    assert actual["host_original_actions"] == 2 and baseline.dispatches == 1
    final = client.created[-1]
    assert {tool["name"] for tool in final["tools"]} == (
        {"stop_task", "replace_text", "read_file", "search_files"} if failed else {"stop_task"})
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


class DeliveryBoundaryClient(ScriptedClient):
    """A deterministic character/structure boundary, not real token measurement."""

    def __init__(self, steps, char_limit, *, force_handoff=False, still_large=False):
        super().__init__(steps)
        self.char_limit = char_limit
        self.force_handoff = force_handoff
        self.still_large = still_large

    def count(self, **request):
        body = json.loads(request["input"][1]["content"])
        if body.get("format") == d.dedup.FORMAT:
            body = d.dedup.expand(body)
        self.input_tokens = math.ceil(len(canonical_json(request)) * 60_000 / self.char_limit)
        if self.created and self.force_handoff:
            self.input_tokens = (60_001 if self.still_large or "current_handoff" not in body
                                 else 30_000)
        return super().count(**request)


@pytest.mark.parametrize("arm,failed,force_handoff,still_large", [
    ("A", False, False, False), ("B", True, False, False),
    ("A", True, True, False), ("A", False, True, True),
])
def test_large_source_feedback_reaches_actual_next_dispatch_without_budget_reset(
    gateway_factory, tmp_path, monkeypatch, arm, failed, force_handoff, still_large,
):
    gateway, journal, loaded, cycle, _ = setup(
        gateway_factory, tmp_path, monkeypatch, limits=d.LIMITS)
    path = gateway.workspace / "mini_data_utils/csvlite.py"
    path.write_text(path.read_text(encoding="utf-8")
                    + "\n" * 20 + "# observed public fixture padding " + "x" * 14_000 + "\n",
                    encoding="utf-8")
    # Make padding baseline source, not a huge unrelated candidate patch.
    run_git(gateway.workspace, "-c", "user.name=Fixture", "-c", "user.email=fixture@local",
            "commit", "--no-verify", "--no-gpg-sign", "-am", "Large public source fixture")
    host_read = read("host-complete-source")
    host_read["arguments"].pop("memory_update")
    host_read["arguments"].update(start_line=None, end_line=None)
    observed = gateway.execute(RequestedTool.model_validate(host_read))
    assert observed.status == "succeeded"
    loaded.common = evidence()
    doc = loaded.common["evidence"]
    doc["saved_public_evidence"][0]["initial_source"] = observed.output["spans"]
    doc["saved_public_evidence"][1]["state"]["current_sources"] = observed.output["spans"]
    loaded.common["deduplicated_evidence"] = d.dedup.deduplicate(doc)
    monkeypatch.setattr(cycle, "_gateway", lambda *_: RecordedGateway(
        cycle.journal, gateway.current_diff_hash, failed=failed))
    first = d.request_payload(loaded.common, arm)
    # Failure now also offers bounded read/search schemas; leave room for that
    # public action surface while still requiring source-reference savings.
    margin = 20_000 if arm == "B" and failed else 8_000
    client = DeliveryBoundaryClient([[edit_call()], [stop_call()]],
        len(canonical_json(first)) + margin, force_handoff=force_handoff,
        still_large=still_large)
    adapter = d.loop.OpenAIResponsesAdapter(d.loop.config(), api_key="", client=client)
    actual = d.loop.run_model(loaded, arm, gateway, adapter,
        DevCostLedger(Decimal("2.40"), pricing_for_model(d.loop.MODEL)),
        first_hash=sha256_json(first), profile=d.PROFILE,
        request_builder=d.request_payload, cycle=cycle, regression=successful_regression(gateway))
    events = journal.events()
    prepared = [e["payload"] for e in events if e["event_type"] == "repair_context_prepared"]
    committed = [e["payload"] for e in events if e["event_type"] == "repair_context_committed"]
    assert len(prepared) == int(force_handoff)
    assert len(committed) == int(force_handoff and not still_large)
    assert actual["new_mutations"] == 1 and actual["host_original_actions"] == 2
    assert actual["correction_calls"] == actual["diagnostic_probes"] == 0
    if still_large:
        assert actual["terminal"] == "INPUT_LIMIT" and len(client.created) == 1
        assert actual["normal_calls"] == actual["tool_actions"] == 1
        assert len(client.counted) == 3  # Initial, failed successor, one rebuilt successor.
        return
    assert actual["terminal"] == "AGENT_STOPPED" and len(client.created) == 2
    assert actual["normal_calls"] == actual["tool_actions"] == 2
    final = client.created[-1]
    info = json.loads(final["input"][-1]["content"])
    assert info["current_trial_original_recheck"] == actual["original_recheck"]
    assert info["current_trial_original_recheck"]["status"] == (
        "failed" if failed else "supported")
    assert info["remaining"]["normal_calls"] == 3
    assert info["remaining"]["tool_actions"] == 4
    assert info["remaining"]["accepted_mutations"] == 1
    assert "PRIVATE_SENTINEL" not in str(client.created)
    counted = {key: value for key, value in client.counted[-1].items() if key != "timeout"}
    sent = {key: value for key, value in final.items() if key != "timeout"}
    assert counted == adapter._count_payload(sent)
    if force_handoff:
        body = d.dedup.expand(json.loads(final["input"][1]["content"]))
        state = body["current_handoff"]["state"]
        assert state["current_original_recheck"] == actual["original_recheck"]
        assert state["current_diff"]["diff_hash"] == gateway.current_diff_hash
        assert state["counters"]["normal_calls"] == 1
        assert state["last_successful_mutation"]
        assert body["saved_public_evidence"] == doc["saved_public_evidence"]
        assert sha256_json(client.counted[-2]) != sha256_json(client.counted[-1])
    else:
        archived = json.loads(final["input"][-2]["content"])["referenced_public_exchanges"]
        restored = d.delivery.expand_exchanges(doc, archived)
        assert restored != archived
        full = copy.deepcopy(final)
        full["input"][-2] = d.SEGMENT_RULES.archive(exchanges=restored)
        assert len(canonical_json(full)) > client.char_limit >= len(canonical_json(final))
