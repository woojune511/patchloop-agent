"""Diagnostic request contracts against the public gateway; no external execution."""
from __future__ import annotations

import pytest
from test_dev_probes import FakeProbe
from test_exception_frame_repair import no_external  # noqa: F401

from diagnostics import repair_cycle_tools as d
from diagnostics.repair_cycle_budget import cycle_opportunity
from patchloop.dev.contracts import RequestedTool
from patchloop.errors import ContractError


def opportunity(**changes):
    return cycle_opportunity(**{"normal_remaining": 3, "tool_remaining": 5,
        "probes_remaining": 2, "edits_remaining": 1, **changes})


def helper(**changes):
    return RequestedTool(name="run_probe", action_id="helper", memory_update=None,
        arguments={"question": "Does a public helper execute?", "python_source": "print(1)",
                   **changes})


def test_helper_schema_requires_source_without_original_replay_union():
    schema = next(row for row in d.schemas(opportunity()) if row["name"] == "run_probe")
    params = schema["parameters"]
    assert set(params["properties"]) == set(params["required"]) == {
        "question", "python_source", "memory_update"}
    assert params["properties"]["python_source"]["type"] == "string"
    assert params["properties"]["question"]["type"] == "string"
    assert params["properties"]["memory_update"] == {"type": "null"}
    assert not params["additionalProperties"]
    assert "recheck_original" in schema["description"]


@pytest.mark.parametrize("changes", [
    {"python_source": None}, {"python_source": ""}, {"question": None},
    {"purpose": {"kind": "helper"}}, {"replay_action_id": "old-action"},
])
def test_invalid_helper_is_rejected_before_gateway(changes):
    called = []
    with pytest.raises(ContractError):
        d.validate([helper(**changes)], opportunity())
        called.append("gateway dispatch")
    assert called == []


def test_new_helper_uses_existing_default_helper_execution_path(gateway_factory):
    gateway, _, _ = gateway_factory()
    gateway.agent_policy = "thin"
    backend = FakeProbe(status="passed")
    gateway.probe_sandbox = backend
    call = helper()
    d.validate([call], opportunity())
    result = gateway.execute(call)
    assert result.status == "succeeded" and result.error_code is None
    assert result.output["stdout"] == "PUBLIC_PROBE_OUTPUT" and backend.calls == 1
    assert "purpose" not in call.arguments and "replay_action_id" not in call.arguments


def test_original_schema_is_empty_and_selection_is_single_without_annotations():
    schema = next(row for row in d.schemas(opportunity()) if row["name"] == d.ORIGINAL)
    assert schema["parameters"] == {"type": "object", "properties": {}, "required": [],
                                    "additionalProperties": False}
    original = RequestedTool(name=d.ORIGINAL, action_id="original", arguments={})
    d.validate([original], opportunity())
    for calls in ([original, helper()],
                  [original.model_copy(update={"arguments": {"python_source": "print(1)"}})],
                  [RequestedTool(name=d.ORIGINAL, action_id="annotated", memory_update=None)],
                  [RequestedTool(name=d.ORIGINAL, action_id="annotated", turn_decision=None)],
                  [RequestedTool(name=d.ORIGINAL, action_id="annotated",
                                 rejected_turn_decision={})]):
        with pytest.raises(ContractError, match="one call with empty arguments"):
            d.validate(calls, opportunity())
    with pytest.raises(ContractError, match="one call with empty arguments"):
        d.validate([original], opportunity(original_remaining=0))


@pytest.mark.parametrize("actions, parallel", [(3, False), (4, True)])
def test_parallel_generation_and_validation_share_the_read_batch_bound(actions, parallel):
    offered = opportunity(tool_remaining=actions)
    assert d.parallel_calls(offered) is parallel
    calls = [RequestedTool(name="read_file", action_id=f"read-{index}", memory_update=None,
                          arguments={"path": "public.py", "start_line": None, "end_line": None})
             for index in range(2)]
    d.validate(calls[:1], offered)
    if parallel:
        d.validate(calls, offered)
    else:
        with pytest.raises(ContractError):
            d.validate(calls, offered)
