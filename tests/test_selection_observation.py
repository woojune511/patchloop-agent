"""Finite offline tests of the observation-only comparison and its stop boundaries."""
from __future__ import annotations

import copy
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from test_exception_frame_repair import edit_call, no_external, read_call, stop_call  # noqa: F401
from test_exception_frame_repair import result as original_result

from diagnostics import selection_observation as d
from diagnostics.checkpoint_continuation import ScriptedClient
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json


def common(public):
    a = {"public_task": {"issue": "fixture task"}, "baseline_call": {"stdout": "F0010"}}
    b = {**copy.deepcopy(a), "additional_observations": [{"selected": ["synthetic-init"]}]}
    return {"public_task": public.model_dump(mode="json"), "packets": {"A": a, "B": b}}


def run(gateway_factory, arm, steps, failure=None):
    gateway, journal, _ = gateway_factory()
    gateway.agent_policy = "thin"
    gateway.deadline = ExecutionDeadline.from_remaining(60)
    gateway.limits.max_accepted_mutations = 1
    loaded = SimpleNamespace(common=common(gateway.public_task))
    client = ScriptedClient(steps, failure=failure)
    adapter = d.loop.OpenAIResponsesAdapter(d.loop.config(), api_key="", client=client)
    group = DevCostLedger(d.PROFILE.invocation_cap, pricing_for_model(d.loop.MODEL))
    row = d.loop.run_model(loaded, arm, gateway, adapter, group,
        first_hash=sha256_json(d.request_payload(loaded.common, arm)),
        profile=d.PROFILE, request_builder=d.request_payload)
    return row, client, journal


def thin_read():
    call = read_call()
    call["arguments"].pop("turn_decision")
    call["arguments"]["memory_update"] = None
    return call


def test_only_extra_observations_differ_through_correction_and_later_turn(smoke_package):
    data = common(smoke_package.public)
    for options in ({}, {"history": [{"role": "user", "content": "same result"}],
                        "remaining": {"normal_calls": 4, "tool_actions": 5},
                        "correction": "malformed request", "probe_used": True}):
        a, b = [d.request_payload(data, arm, **options) for arm in ("A", "B")]
        d.verify_pair(a, b)
        assert a["model"] == b["model"] == "gpt-5.4-mini-2026-03-17"
        assert a["tools"] == b["tools"]
        assert a["max_output_tokens"] == (25_000 if options else 40_000)
        assert "saved candidate" not in canonical_json(a)
        assert "synthetic-init" not in canonical_json(a)
        assert "synthetic-init" in canonical_json(b)
        altered = copy.deepcopy(b)
        altered["max_output_tokens"] += 1
        with pytest.raises(ContractError, match="beyond"):
            d.verify_pair(a, altered)


@pytest.mark.parametrize("arm", ["A", "B"])
def test_model_edits_clean_fixture_once_and_does_not_continue(gateway_factory, arm):
    row, client, journal = run(gateway_factory, arm,
                              [[thin_read()], [edit_call()], [stop_call()]])
    assert row["terminal"] == "CANDIDATE_PRODUCED"
    assert row["new_mutations"] == 1 and row["normal_calls"] == 2
    assert len(client.created) == 2 and not row["stop_remaining"]
    events = journal.events()
    before = next(e["payload"] for e in events if e["event_type"] == "action_started")
    assert before["tool"] == "read_file"
    assert not any(e["event_type"] == "seed_restored" for e in events)
    for request in client.created:
        payload = json.loads(request["input"][1]["content"])
        assert ("additional_observations" in payload["public_observations"]) == (arm == "B")


@pytest.mark.parametrize("failure", ["count", "transport", "usage"])
def test_uncertainty_cancels_pair_before_any_tool(gateway_factory, failure):
    row, client, journal = run(gateway_factory, "A", [[thin_read()]], failure)
    assert row["stop_remaining"] and not row["billing_known"]
    assert len(client.created) <= 1
    assert not any(e["event_type"] == "action_started" for e in journal.events())


def test_one_correction_uses_separate_output_cap(gateway_factory):
    row, client, _ = run(gateway_factory, "B", [[], [stop_call()]])
    assert row["correction_calls"] == 1 and row["terminal"] == "AGENT_STOPPED"
    assert [request["max_output_tokens"] for request in client.created] == [40_000, 25_000]


def test_host_case_cannot_pass_by_suppressing_child_or_just_removing_f0010():
    child = "src/project/file.py"
    data = {"events": [{"function": "expand", "selected": [{"path": child}]},
                       {"function": "file_build", "input": {"filepath": child}}],
            "stdout": "", "stderr": "", "exception": None, "exit_code": 0}
    assert d.grade_case("empty", data)["passed"]
    assert not d.grade_case("empty", {**data, "events": []})["passed"]
    assert not d.grade_case("syntax", data)["passed"]
    syntax = {**data, "stdout": "file.py: E0001", "exit_code": 2}
    assert all(d.grade_case(name, syntax)["passed"] for name in ("syntax", "direct", "package"))
    assert not d.grade_case("empty", {**data, "exception": {"type": "ValueError"}})["passed"]


def test_public_programs_are_bounded_and_include_only_named_fixtures():
    programs = d.programs()
    assert list(programs) == ["empty", "import", "syntax", "direct", "package"]
    assert all(len(code) <= 8000 and "__CHILD_SOURCE__" not in code for code in programs.values())
    assert "def broken(" not in programs["empty"]
    assert "def broken(" in programs["syntax"]
    # Observational wrapper's abspath filters paths; no target patch is installed.
    assert "path_to_check =" not in "".join(programs.values())


def test_original_call_failure_and_identity_are_not_replaced_by_supplementary_pass():
    base, current = original_result(), original_result()
    base["output"]["reproduction"]["call_observation"]["calls"][0]["capture"]["stdout"] = "F0010"
    result = d.original_summary(base, current)
    assert result["supported"] and result["call1_same_conditions"]
    current["output"]["reproduction"]["call_observation"]["calls"][0]["cwd"] = "/changed"
    result = d.original_summary(base, current)
    assert result["call1_F0010_resolved"] and not result["supported"]


def test_cap_approval_is_exact_and_precedes_validation(monkeypatch):
    monkeypatch.setattr(d, "validate", lambda *_: pytest.fail("approval must precede loading"))
    with pytest.raises(ContractError, match="exact new cap"):
        d.collect(None, "anything", Decimal("1.20"))


def test_prepare_accepts_existing_packet_folder_and_never_overwrites(
    tmp_path, monkeypatch, smoke_package,
):
    output = tmp_path / "plan"
    (output / "packet-build").mkdir(parents=True)
    data = common(smoke_package.public)
    requests = {arm: d.request_payload(data, arm) for arm in ("A", "B")}
    monkeypatch.setattr(d, "load_inputs", lambda _: SimpleNamespace(requests=requests))
    monkeypatch.setattr(d, "file_binding", lambda path: {"path": str(path), "hash": "fixture"})
    receipt = d.prepare(output, tmp_path / "live", tmp_path / "unread.env")
    assert receipt["provider_calls"] == receipt["credential_reads"] == 0
    assert json.loads((output / "manifest.json").read_bytes())["paid_execution_authorized"] is False
    before = (output / "manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        d.prepare(output, tmp_path / "live", tmp_path / "unread.env")
    assert (output / "manifest.json").read_bytes() == before


def test_collection_stops_remaining_arm_after_uncertainty(tmp_path, monkeypatch):
    plan = {"result_root": str(tmp_path / "live"), "bindings": [],
            "credential_file": "unread.env", "first_request_hashes": {"A": "a", "B": "b"},
            "interpretation": "synthetic scope"}
    monkeypatch.setattr(d, "validate", lambda *_: (plan, SimpleNamespace()))
    monkeypatch.setattr(d.loop.runner, "_require_tracked_clean_paths", lambda *_: None)
    calls = []
    monkeypatch.setattr(d, "clean_gateway", lambda _, root: calls.append(root.name))
    monkeypatch.setattr(d.loop, "load_exact_openai_api_key", lambda _: "synthetic")
    monkeypatch.setattr(d.loop, "OpenAIResponsesAdapter", lambda *_, **__: SimpleNamespace(
        client=SimpleNamespace(close=lambda: None)))
    monkeypatch.setattr(d.loop, "run_model", lambda *_, **__: {
        "stop_remaining": True, "terminal": "COUNT_UNCERTAIN"})
    result = d.collect(tmp_path / "plan/manifest.json", "hash", d.PROFILE.invocation_cap)
    assert calls == ["A"] and len(result["rows"]) == 1

