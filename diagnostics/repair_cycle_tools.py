"""Small request contracts for the opt-in saved-candidate repair diagnostic."""
from __future__ import annotations

from types import SimpleNamespace

from patchloop import probe_limits
from patchloop.dev import probe_replay, runner
from patchloop.dev.tools import dev_tool_schemas, validate_tool_batch
from patchloop.errors import ContractError

ORIGINAL = "recheck_original"


def schemas(opportunity, probe_environment=None, dependency_sources=None):
    tools = dev_tool_schemas(finish_enabled=False, allowed_tools=opportunity.allowed - {ORIGINAL},
        probe_environment=probe_environment, agent_policy="thin", read_range_only=False,
        dependency_sources=dependency_sources)
    for tool in tools:
        if tool["name"] != "run_probe":
            continue
        # A new helper program has no replay/purpose union. Its two executable
        # inputs go directly through the gateway's existing default helper path.
        properties = tool["parameters"]["properties"]
        properties = {key: properties[key] for key in ("question", "python_source")}
        for value in properties.values():
            value["type"] = "string"
        properties["memory_update"] = {"type": "null"}
        tool["parameters"] = {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}
        tool["description"] = (
            "Run a new helper experiment. Supply the executable Python source and question. "
            "To execute the registered original caller, use recheck_original instead. "
            + tool["description"].split(probe_replay.DESCRIPTION, 1)[0])
    if ORIGINAL in opportunity.allowed:
        tools.append({"type": "function", "name": ORIGINAL, "strict": True,
            "description": "Execute the registered original public caller on the current diff. "
                "The host supplies the frozen program, arguments and comparison. No code or "
                "failure rules are required. This is an observation, not task acceptance.",
            "parameters": {"type": "object", "properties": {}, "required": [],
                           "additionalProperties": False}})
    return tools


def parallel_calls(opportunity):
    return runner._parallel_tool_calls(SimpleNamespace(
        max_parallel_reads=opportunity.max_parallel_reads, allowed_tools=opportunity.allowed))


def validate(calls, opportunity):
    if any(call.name == ORIGINAL for call in calls):
        if (len(calls) != 1 or ORIGINAL not in opportunity.allowed
                or calls[0].arguments != {}
                or {"turn_decision", "memory_update", "rejected_turn_decision"}
                    & calls[0].model_fields_set):
            raise ContractError("recheck_original requires one call with empty arguments")
        return
    validate_tool_batch(calls, allowed_tools=opportunity.allowed, agent_policy="thin",
                        read_range_only=False, max_parallel_reads=opportunity.max_parallel_reads)
    for call in calls:
        if call.name != "run_probe":
            continue
        args = call.arguments
        if (set(args) != {"question", "python_source"}
                or not isinstance(args["question"], str) or not 1 <= len(args["question"]) <= 500
                or not isinstance(args["python_source"], str)
                or not 1 <= len(args["python_source"]) <= probe_limits.SOURCE_LIMIT_CHARS
                or call.memory_update is not None):
            raise ContractError("new helper probe requires question and executable python_source; "
                                "use recheck_original for the registered caller")
