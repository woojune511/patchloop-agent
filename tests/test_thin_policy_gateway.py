from __future__ import annotations

import copy
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.agent.model import RequestedTool as ProviderCall
from patchloop.dev.contracts import (
    DevRunRequest,
    PublicTurnDecision,
    RequestedTool,
    dev_tool_surface_hash,
)
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.dev.runner import _requested_tool_from_openai
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas, validate_tool_batch
from patchloop.errors import ActionConflict, ContractError
from patchloop.sandbox.runner import SandboxResult
from patchloop.util import sha256_json

PATH = "mini_data_utils/csvlite.py"
MODES = {
    "read_file": "inspect", "search_files": "inspect", "replace_text": "mutate",
    "run_check": "verify", "run_tests": "verify", "run_probe": "verify",
    "finish_task": "finish", "stop_task": "stop",
}


def call(policy, name="read_file", action_id="source", arguments=None, update=None):
    values = {"name": name, "action_id": action_id, "arguments": arguments or {
        "path": PATH, "start_line": 1, "end_line": 80,
    }}
    if policy == "thin":
        values["memory_update"] = update
    else:
        values["turn_decision"] = PublicTurnDecision(
            mode=MODES[name], basis="Inspect the relevant source.",
            evidence_goal="Find the current implementation." if MODES[name] == "inspect" else None,
            memory_update=update,
        )
    return RequestedTool(**values)


def restart(gateway, policy):
    return DevToolGateway(
        workspace=gateway.workspace, public_task=gateway.public_task, sandbox=gateway.sandbox,
        journal=gateway.journal, limits=gateway.limits, agent_policy=policy,
    )


def mutation(policy, action_id="edit"):
    item = MOCK_MUTATIONS["csv-quoted-newline"]
    return call(policy, "replace_text", action_id, {
        "path": item.path, "old_text": item.old_text, "new_text": item.new_text,
        "occurrence": 1, "hypothesis": item.hypothesis,
        "expected_behavior": item.expected_behavior, "causal_revision": None,
    })


class PassingSandbox:
    official = False

    def __init__(self):
        self.calls = 0

    def run_check(self, workspace, check):
        self.calls += 1
        return SandboxResult(
            command=["mock-check"], exit_code=0, stdout="passed", stderr="",
            duration_ms=1, timed_out=False, truncated=False, original_output_bytes=6,
        )


def test_default_serialization_and_schema_identities_remain_exact():
    old = call("current", arguments={"path": "src.py", "start_line": 1, "end_line": 4})
    assert sha256_json(old.model_dump(mode="json")) == (
        "sha256:df91ee4711a27b708c2c8bc070d1b6778f1e37b04cd94c77b39be2f95cac92e3"
    )
    assert "memory_update" not in RequestedTool(name="read_file", action_id="x").model_dump()
    assert dev_tool_surface_hash() == (
        "sha256:c1dddeac2c94f30a29543fc9e3e5a2c0cef913203906cace717a552a55815383"
    )
    schemas = dev_tool_schemas(
        finish_enabled=True, check_ids=["public-check"], test_suite_ids=["public-tests"],
        allowed_tools=list(MODES),
    )
    assert sha256_json(schemas) == (
        "sha256:f1b235fcd18ee4d4b8d75545e4d0a878f7e8b68afbd233507fcd413c4b338984"
    )
    request = DevRunRequest(provider="mock", task=Path("public.yaml"), model="mock-dev")
    assert "agent_policy" not in request.model_dump(mode="json")
    thin = request.model_copy(update={"agent_policy": "thin"})
    assert thin.model_dump(mode="json").pop("agent_policy") == "thin"
    with pytest.raises(ValidationError, match="planning-policy none"):
        DevRunRequest(
            provider="mock", task=Path("public.yaml"), model="mock-dev",
            agent_policy="thin", planning_policy="brief-v1",
        )


@pytest.mark.parametrize("probe_policy", ["none", "cases-v1", "reference-cases-v1"])
def test_thin_changes_only_annotation_schema(probe_policy):
    options = {
        "finish_enabled": True, "check_ids": ["public-check"],
        "test_suite_ids": ["public-tests"], "allowed_tools": list(MODES),
        "read_paths": [PATH], "probe_policy": probe_policy,
    }
    current = dev_tool_schemas(**options)
    thin = dev_tool_schemas(**options, agent_policy="thin")
    assert [entry["name"] for entry in thin] == [entry["name"] for entry in current]
    for a, b in zip(current, thin, strict=True):
        decision = a["parameters"]["properties"].pop("turn_decision")
        a["parameters"]["required"].remove("turn_decision")
        annotation = b["parameters"]["properties"].pop("memory_update")
        b["parameters"]["required"].remove("memory_update")
        assert annotation == decision["properties"]["memory_update"]
        assert a == b


def test_thin_wire_round_trip_preserves_absence_and_explicit_null():
    original = call("thin")
    wire = original.model_dump(mode="json")
    assert "turn_decision" not in wire
    assert wire["memory_update"] is None
    restored = RequestedTool.model_validate(wire)
    assert validate_tool_batch([restored], agent_policy="thin") == "parallel_read"
    assert restored.model_fields_set == original.model_fields_set
    with pytest.raises(ContractError, match="does not accept turn_decision"):
        validate_tool_batch([
            RequestedTool.model_validate({**wire, "turn_decision": None}),
        ], agent_policy="thin")
    with pytest.raises(ContractError, match="requires nullable"):
        validate_tool_batch([RequestedTool(name="read_file", action_id="x")], agent_policy="thin")
    with pytest.raises(ContractError, match="top-level memory_update"):
        validate_tool_batch([call("current").model_copy(update={"memory_update": None})])


def test_current_provider_stray_root_memory_stays_an_operational_argument(gateway_factory):
    proposed = mutation("current")
    wire = {
        **proposed.arguments,
        "turn_decision": proposed.turn_decision.model_dump(mode="json"),
        "memory_update": None,
    }
    parsed = _requested_tool_from_openai(
        ProviderCall(proposed.name, proposed.action_id, wire), agent_policy="current",
    )
    assert "memory_update" in parsed.arguments
    assert parsed.arguments["memory_update"] is None
    assert "memory_update" not in parsed.model_fields_set
    assert validate_tool_batch([parsed]) == "single_action"
    gateway, _, workspace = gateway_factory()
    assert gateway.execute_batch([call("current")])[0].status == "succeeded"
    before = (workspace / PATH).read_bytes()
    diff_before = gateway.current_diff_hash
    result, = gateway.execute_batch([parsed])
    assert result.status == "failed"
    assert "memory_update" in result.message
    assert "Extra inputs are not permitted" in result.message
    assert gateway.accepted_mutations == 0
    assert (workspace / PATH).read_bytes() == before
    assert gateway.current_diff_hash == diff_before


@pytest.mark.parametrize("policy", ["current", "thin"])
@pytest.mark.parametrize("invalid", ["mixed", "fifth", "duplicate", "unavailable", "path"])
def test_batch_boundaries_match(policy, invalid):
    calls = [call(policy, action_id=str(index)) for index in range(4)]
    options = {"agent_policy": policy}
    assert validate_tool_batch(calls, **options) == "parallel_read"
    if invalid == "mixed":
        calls[-1] = mutation(policy)
    elif invalid == "fifth":
        calls.append(call(policy, action_id="fifth"))
    elif invalid == "duplicate":
        calls[-1] = calls[0]
    elif invalid == "unavailable":
        options["allowed_tools"] = {"stop_task"}
    else:
        options["allowed_read_paths"] = ["different.py"]
    with pytest.raises(ContractError):
        validate_tool_batch(calls, **options)


def test_thin_ordered_reads_have_real_evidence_without_fabricated_intent(gateway_factory):
    gateway = restart(gateway_factory()[0], "thin")
    calls = [call("thin", action_id="read1"), call(
        "thin", "search_files", "negative", {"query": "NOT_PRESENT_ABC", "path_glob": "**/*.py"},
    ), call("thin", action_id="read2"), call("thin", action_id="read3")]
    results = gateway.execute_batch(calls)
    assert [result.action_id for result in results] == [item.action_id for item in calls]
    assert all(result.status == "succeeded" for result in results)
    assert results[0].output["spans"]
    assert results[1].output["spans"] == []
    assert all("inspection_intent" not in result.output for result in results)
    assert gateway.evidence_ledger()["latest_inspection_intent"] is None
    events = [event["payload"] for event in gateway.journal.events()
              if event["event_type"] == "action_started"]
    assert all("turn_decision" not in event and event["memory_update"] is None for event in events)
    restored = restart(gateway, "thin")
    assert restored.execute(calls[0]).model_dump(exclude={"replayed"}) == (
        results[0].model_dump(exclude={"replayed"})
    )
    assert restored.spans == gateway.spans
    changed = calls[0].model_copy(update={"memory_update": {"open_question": "Changed"}})
    with pytest.raises(ActionConflict, match="different input"):
        restored.execute(changed)
    # Explicit null is part of B identity; it cannot replay an unannotated legacy call.
    legacy = RequestedTool(name=calls[0].name, action_id=calls[0].action_id,
                           arguments=calls[0].arguments)
    with pytest.raises(ActionConflict, match="different input"):
        restored.execute(legacy)


@pytest.mark.parametrize("policy", ["current", "thin"])
def test_mutation_check_invalidation_and_recovery_match(gateway_factory, policy):
    sandbox = PassingSandbox()
    gateway = restart(gateway_factory(sandbox=sandbox)[0], policy)
    rejected = gateway.execute(mutation(policy, "unobserved"))
    assert rejected.status == "failed"
    assert gateway.accepted_mutations == 0
    gateway.execute_batch([call(policy)])
    edited = gateway.execute(mutation(policy))
    assert edited.status == "succeeded"
    check_id = gateway.public_task.visible_checks[0].id
    check = call(policy, "run_check", "check", {"check_id": check_id})
    checked = gateway.execute(check)
    assert checked.output["passed"]
    restored = restart(gateway, policy)
    assert restored.execute(mutation(policy)).model_dump(exclude={"replayed"}) == (
        edited.model_dump(exclude={"replayed"})
    )
    assert restored.execute(check).model_dump(exclude={"replayed"}) == (
        checked.model_dump(exclude={"replayed"})
    )
    assert restored.accepted_mutations == 1
    assert sandbox.calls == 1
    restored.execute(call(policy, action_id="fresh-source"))
    subsequent = mutation(policy, "follow-up")
    subsequent.arguments.update({
        "old_text": MOCK_MUTATIONS["csv-quoted-newline"].new_text,
        "new_text": MOCK_MUTATIONS["csv-quoted-newline"].new_text + "\n",
    })
    assert restored.execute(subsequent).status == "succeeded"
    assert not restored.visible_checks_pass()
    assert not restored.ready_to_submit()


@pytest.mark.parametrize("policy", ["current", "thin"])
def test_notes_precede_batch_first_nonnull_and_invalid_notes_do_not_block(gateway_factory, policy):
    gateway = restart(gateway_factory()[0], policy)
    update = {"findings": [], "remove_note_ids": [], "open_question": "Inspect the parser.",
              "verification_updates": []}
    later = copy.deepcopy(update)
    later["open_question"] = "This update must be ignored."
    calls = [call(policy, action_id="no-note"), call(policy, action_id="note", update=update),
             call(policy, action_id="ignored", update=later)]
    receipt = gateway.record_working_notes_update(calls, turn_id="turn1")
    assert receipt["diagnostics"] == ["ignored_additional_memory_updates"]
    assert gateway.working_notes()["open_question"] == update["open_question"]
    assert all(result.status == "succeeded" for result in gateway.execute_batch(calls))
    invalid = call(policy, action_id="invalid-note", update="not a note")
    bad = gateway.record_working_notes_update([invalid], turn_id="turn2")
    assert bad["diagnostics"] == ["invalid_memory_update_shape"]
    assert gateway.execute(invalid).status == "succeeded"
    restored = restart(gateway, policy)
    assert restored.working_notes() == gateway.working_notes()
    assert restored.record_working_notes_update(calls, turn_id="turn1") == receipt


@pytest.mark.parametrize("policy", ["current", "thin"])
@pytest.mark.parametrize("invalid", ["partial", "stale", "forbidden", "new_file"])
def test_rejected_anchor_and_scope_preserve_workspace_and_capacity(
    gateway_factory, policy, invalid,
):
    gateway = restart(gateway_factory()[0], policy)
    source = call(policy)
    if invalid == "partial":
        source.arguments["end_line"] = 1
    gateway.execute(source)
    attempted = mutation(policy)
    if invalid == "stale":
        path = gateway.workspace / PATH
        path.write_bytes(path.read_bytes() + b"\n# External source change.\n")
    elif invalid == "forbidden":
        attempted.arguments["path"] = ".patchloop-hidden/spec.py"
    elif invalid == "new_file":
        attempted.arguments["path"] = "mini_data_utils/new.py"
    before = gateway.current_diff_hash
    checks = gateway.visible_check_status()
    result = gateway.execute(attempted)
    assert result.status == "failed"
    assert gateway.current_diff_hash == before
    assert gateway.accepted_mutations == 0
    assert gateway.visible_check_status() == checks
    assert not (gateway.workspace / "mini_data_utils/new.py").exists()


@pytest.mark.parametrize("policy", ["current", "thin"])
def test_interrupted_mutation_reconciles_actual_annotations_once(
    gateway_factory, monkeypatch, policy,
):
    gateway = restart(gateway_factory()[0], policy)
    gateway.execute(call(policy))
    attempted = mutation(policy)
    original_append = gateway.journal.append

    def interrupted(event_type, payload):
        if event_type == "action_finished" and payload["result"]["tool"] == "replace_text":
            raise OSError("simulated loss before the completed receipt")
        return original_append(event_type, payload)

    with monkeypatch.context() as patch:
        patch.setattr(gateway.journal, "append", interrupted)
        with pytest.raises(OSError, match="simulated loss"):
            gateway.execute(attempted)
    candidate = gateway.current_diff_hash
    restored = restart(gateway, policy)
    result = restored.execute(attempted)
    assert result.status == "succeeded"
    assert result.output["recovered_after_crash"] is True
    assert restored.current_diff_hash == candidate
    assert restored.accepted_mutations == 1
    assert restored.execute(attempted).replayed is True
    assert restored.accepted_mutations == 1
