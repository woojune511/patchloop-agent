"""Small action transport preserves actual annotation presence and legacy receipts."""

from __future__ import annotations

import copy
import json

import pytest

from patchloop.agent.model import RequestedTool as ProviderCall
from patchloop.dev import runner, thin_policy
from patchloop.dev.contracts import (
    ANNOTATION_OPTIONAL_TOOLS,
    DEV_SINGLE_ACTION_TOOLS,
    DevModelTurn,
    PublicTurnDecision,
    RequestedTool,
    TextReplacementIntent,
)
from patchloop.dev.model import DEV_SYSTEM_PROMPT, MockDevAdapter

CORE_TOOLS = ("replace_text", "stop_task", "observe_original")
ANNOTATIONS = {"turn_decision", "memory_update", "rejected_turn_decision"}
REPLACEMENT = {
    "path": "public.py", "old_text": "return 1", "new_text": "return 2",
    "occurrence": 1, "hypothesis": "The old branch returns the wrong value.",
    "expected_behavior": "The selected public input returns 2.",
}
REVISION = {
    "falsified_prior_hypothesis": "The earlier helper change did not affect this call.",
    "alternative_mechanism": "The original caller enters a different branch.",
}


def arguments(name):
    if name == "replace_text":
        return dict(REPLACEMENT)
    if name == "stop_task":
        return {"reason_code": "insufficient_public_evidence", "summary": "Evidence is incomplete."}
    # This test concerns transport; the registered observation intent is validated separately.
    return {}


def decision(name):
    return {
        "mode": {"replace_text": "mutate", "stop_task": "stop", "observe_original": "verify"}[
            name],
        "basis": "Previously observed public evidence.", "evidence_goal": None,
        "memory_update": None,
    }


def schema(name, fields):
    return {"name": name, "parameters": {
        "type": "object", "properties": {field: {} for field in fields},
        "required": list(fields), "additionalProperties": False,
    }}


@pytest.mark.parametrize("name", CORE_TOOLS)
@pytest.mark.parametrize("policy", ["current", "thin"])
def test_provider_absent_annotations_remain_absent_after_durable_round_trip(name, policy):
    original = arguments(name)
    parsed = runner._requested_tool_from_openai(
        ProviderCall(name, "fresh", original), agent_policy=policy,
    )
    restored = RequestedTool.model_validate(parsed.model_dump(mode="json"))
    assert not ANNOTATIONS & parsed.model_fields_set
    assert not ANNOTATIONS & restored.model_fields_set
    assert runner._provider_tool_arguments(restored) == original
    assert runner._provider_rejected_call_arguments(restored) == original
    assert parsed.arguments == original


@pytest.mark.parametrize("name", CORE_TOOLS)
@pytest.mark.parametrize("policy", ["current", "thin"])
@pytest.mark.parametrize("explicit_null", [False, True])
def test_provider_legacy_decision_and_explicit_null_preserve_actual_presence(
    name, policy, explicit_null,
):
    original = {**arguments(name), "turn_decision": None if explicit_null else decision(name)}
    parsed = runner._requested_tool_from_openai(
        ProviderCall(name, "legacy", original), agent_policy=policy,
    )
    restored = RequestedTool.model_validate(parsed.model_dump(mode="json"))
    assert "turn_decision" in restored.model_fields_set
    assert "rejected_turn_decision" not in restored.model_fields_set
    assert runner._provider_tool_arguments(restored) == original
    assert runner._provider_rejected_call_arguments(restored) == original


@pytest.mark.parametrize("name", CORE_TOOLS)
def test_thin_legacy_root_null_memory_is_preserved_without_a_decision(name):
    original = {**arguments(name), "memory_update": None}
    parsed = runner._requested_tool_from_openai(
        ProviderCall(name, "legacy-memory", original), agent_policy="thin",
    )
    restored = RequestedTool.model_validate(parsed.model_dump(mode="json"))
    assert "memory_update" in restored.model_fields_set
    assert "turn_decision" not in restored.model_fields_set
    assert runner._provider_tool_arguments(restored) == original


@pytest.mark.parametrize("name", CORE_TOOLS)
def test_internal_small_action_serialization_does_not_invent_a_null_decision(name):
    call = RequestedTool(name=name, action_id="fresh", arguments=arguments(name))
    assert not ANNOTATIONS & call.model_dump(mode="json").keys()
    explicit = RequestedTool(name=name, action_id="legacy", arguments=arguments(name),
                             turn_decision=None)
    assert explicit.model_dump(mode="json")["turn_decision"] is None


@pytest.mark.parametrize("extra", [{}, {"causal_revision": None}, {"causal_revision": REVISION}])
def test_replacement_intent_keeps_absent_null_and_legacy_revision_distinct(extra):
    original = {**REPLACEMENT, **extra}
    parsed = TextReplacementIntent.model_validate(original)
    assert parsed.model_dump(mode="json") == original
    assert TextReplacementIntent.model_validate(parsed.model_dump(mode="json")).model_dump(
        mode="json") == original


@pytest.mark.parametrize("name", CORE_TOOLS)
@pytest.mark.parametrize("policy", ["current", "brief-v1", "thin"])
def test_mock_follows_each_small_action_schema_without_adding_annotation_slots(
    monkeypatch, name, policy,
):
    adapter = MockDevAdapter("csv-quoted-newline")
    legacy_arguments = arguments(name)
    if name == "replace_text":
        legacy_arguments["causal_revision"] = None
    authored = RequestedTool(name=name, action_id="scripted", arguments=legacy_arguments,
                             turn_decision=PublicTurnDecision.model_validate(decision(name)))
    monkeypatch.setattr(adapter, "_next_action", lambda *_: DevModelTurn(tool_calls=[authored]))
    context = {"public_task": {"issue": {"title": "Public task"}},
               "workflow_gate": "needs_mutation"}
    if policy == "brief-v1":
        context["working_plan"] = {
            "policy": policy, "review_request": {"requested": True}, "plan": None,
        }
    schemas = [schema("read_file", ["memory_update" if policy == "thin" else "turn_decision"]),
               schema(name, arguments(name))]
    pristine = copy.deepcopy(schemas)
    call, = adapter.next_turn(json.dumps(context), schemas).tool_calls
    assert call.arguments == arguments(name)
    assert not ANNOTATIONS & call.model_fields_set
    assert runner._provider_tool_arguments(call) == arguments(name)
    assert schemas == pristine


def test_mock_thin_inspection_uses_its_own_schema_when_first_tool_has_no_annotations():
    adapter = MockDevAdapter("csv-quoted-newline")
    tools = [schema("replace_text", REPLACEMENT), schema("read_file", ["memory_update"]),
             schema("search_files", ["memory_update"])]
    calls = adapter.next_turn("{}", tools).tool_calls
    assert [call.name for call in calls] == ["search_files", "read_file"]
    assert all("memory_update" in call.model_fields_set for call in calls)
    assert all("turn_decision" not in call.model_fields_set for call in calls)


def test_mock_actual_mutation_uses_six_fields_and_legacy_schema_keeps_its_old_fields():
    adapter = MockDevAdapter("csv-quoted-newline")
    context = json.dumps({"source_spans": [{"path": adapter.mutation.path}]})
    fresh, = adapter.next_turn(context, [schema("replace_text", REPLACEMENT)]).tool_calls
    assert set(fresh.arguments) == set(REPLACEMENT)
    assert not ANNOTATIONS & fresh.model_fields_set
    legacy, = adapter.next_turn(context, [schema(
        "replace_text", [*REPLACEMENT, "causal_revision", "turn_decision"],
    )]).tool_calls
    assert legacy.arguments["causal_revision"] is None
    assert legacy.turn_decision.mode == "mutate"


def test_core_actions_are_single_actions_and_prompts_explain_annotation_exceptions():
    expected_tools = set(CORE_TOOLS) | {"edit_files"}
    assert expected_tools == ANNOTATION_OPTIONAL_TOOLS
    assert expected_tools <= DEV_SINGLE_ACTION_TOOLS
    for prompt in (DEV_SYSTEM_PROMPT, thin_policy.SYSTEM_PROMPT):
        assert (
            "replace_text, edit_files, stop_task and observe_original omit decision/plan/memory"
        ) in prompt
    assert "causal_revision" not in DEV_SYSTEM_PROMPT
    assert len(DEV_SYSTEM_PROMPT) <= 8000
