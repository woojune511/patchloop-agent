"""Independent wire-contract oracle; all replies and reasoning strings are fixtures."""

from __future__ import annotations

import asyncio
import copy
import json
import socket
from dataclasses import replace

import httpx
from openai import AsyncOpenAI

import pydantic_ai
import pydantic_graph
from pydantic_ai import (
    Agent, ModelRequest, ModelResponse, TextPart, ThinkingPart, ToolCallPart,
    ToolReturnPart, UserPromptPart,
)
from pydantic_ai.capabilities import Capability
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.providers.deepseek import DeepSeekProvider
from pydantic_ai.providers.openai import OpenAIProvider


def deny_network(*args, **kwargs):
    raise AssertionError("Network is not part of this acceptance contract")


socket.socket.connect = deny_network
socket.create_connection = deny_network


def reply(message):
    return httpx.Response(200, json={"id": "acceptance-fixture", "object": "chat.completion",
        "model": "fixture-model", "created": 1,
        "choices": [{"index": 0, "message": message,
                     "finish_reason": "tool_calls" if message.get("tool_calls") else "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})


def normalized(message):
    value = copy.deepcopy(message)
    for call in value.get("tool_calls", []):
        call["function"]["arguments"] = json.loads(call["function"]["arguments"])
    return value


def call_dict(name, arguments, identifier):
    return {"id": identifier, "type": "function", "function": {"name": name, "arguments": arguments}}


async def verify_wire_matrix():
    requests = []

    async def capture(request):
        assert request.url.host == "oracle.invalid"
        requests.append(json.loads(request.content))
        return reply({"role": "assistant", "content": "accepted-fixture"})

    count = 0
    async with httpx.AsyncClient(transport=httpx.MockTransport(capture)) as http:
        client = AsyncOpenAI(api_key="not-a-real-key", base_url="https://oracle.invalid",
                             max_retries=0, http_client=http)
        ds = DeepSeekProvider(openai_client=client)
        compatible = OpenAIProvider(openai_client=client)
        configurations = []
        for name in ("deepseek-v4-flash", "deepseek-v4-pro", "deepseek-reasoner",
                     "deepseek-chat", "deepseek-v4-future"):
            configurations.append((name, ds, ds.model_profile(name), "field", "reasoning_content", True))
        base = ds.model_profile("deepseek-v4-flash")
        for mode in (False, "tags", "auto"):
            configurations.append(("deepseek-v4-flash", ds,
                replace(base, openai_chat_send_back_thinking_parts=mode), mode, "reasoning_content", False))
        configurations.append(("deepseek-v4-flash", ds,
            replace(base, openai_chat_thinking_field="fixture_reasoning"), "field", "fixture_reasoning", True))
        # Reusing a provider-supplied profile retains its contract even with another compatible client.
        configurations.append(("fixture-alias", compatible, base, "field", "reasoning_content", True))
        for mode in ("field", "auto", "tags", False):
            configurations.append(("deepseek-v4-flash", compatible,
                OpenAIModelProfile(openai_chat_thinking_field="reasoning_content",
                                   openai_chat_send_back_thinking_parts=mode), mode, "reasoning_content", False))

        for name, provider, profile, mode, field_name, needs_empty in configurations:
            model = OpenAIChatModel(name, provider=provider, profile=profile)
            for thoughts, text, tool_count in (([], [], 2), ([""], [], 1),
                    (["fixture-left", "fixture-right"], ["first", "second"], 2),
                    (["fixture-text-only"], ["answer"], 0), ([], ["answer"], 0), ([], [], 0)):
                parts = [ThinkingPart(t, id="reasoning_content", provider_name=provider.name) for t in thoughts]
                parts.extend(TextPart(t) for t in text)
                expected_calls = [call_dict(f"action_{i}", {"value": i + 7}, f"call-{i}-preserve")
                                  for i in range(tool_count)]
                parts.extend(ToolCallPart(c["function"]["name"], c["function"]["arguments"], tool_call_id=c["id"])
                             for c in expected_calls)
                history = [ModelRequest(parts=[UserPromptPart("fixture-input")]), ModelResponse(parts=parts)]
                if expected_calls:
                    history.append(ModelRequest(parts=[ToolReturnPart(c["function"]["name"],
                        "fixture-return", tool_call_id=c["id"]) for c in expected_calls]))
                original = copy.deepcopy(history)
                await model.request(history, None, ModelRequestParameters())
                assert history == original, "request mapping mutated input history"
                actual = [normalized(m) for m in requests[-1]["messages"] if m["role"] == "assistant"]
                expected_text = list(text)
                expected = {"role": "assistant"}
                if thoughts and mode is not False:
                    if mode in ("field", "auto"):
                        expected[field_name] = "\n\n".join(thoughts)
                    else:
                        expected_text = [f"<think>\n{t}\n</think>" for t in thoughts] + expected_text
                elif needs_empty and tool_count:
                    expected[field_name] = ""
                expected["content"] = "\n\n".join(expected_text) if expected_text else None
                if expected_calls:
                    expected["tool_calls"] = expected_calls
                should_emit = bool(expected_text or expected_calls or any(k not in {"role", "content"} for k in expected))
                assert actual == ([expected] if should_emit else []), "assistant serialization contract"
                returns = [m for m in requests[-1]["messages"] if m["role"] == "tool"]
                assert returns == [{"role": "tool", "tool_call_id": c["id"], "content": "fixture-return"}
                                   for c in expected_calls], "tool-return identity/order"
                count += 1
    return count


async def verify_two_capability_flow(deferred):
    bodies = []
    invoked = []

    def first_action() -> str:
        """Return the first acceptance fixture."""
        invoked.append("first")
        return "one"

    def second_action() -> str:
        """Return the second acceptance fixture."""
        invoked.append("second")
        return "two"

    calls = [("load_capability", {"id": "FIRST"}), ("first_action", {}),
             ("load_capability", {"id": "SECOND"}), ("second_action", {})] if deferred else [
                 ("first_action", {}), ("second_action", {})]

    async def handler(request):
        assert request.url.host == "flow.invalid"
        bodies.append(json.loads(request.content))
        turn = len(bodies)
        assert turn <= len(calls) + 1
        message = {"role": "assistant", "content": "finished",
                   "reasoning_content": f"fixture-turn-{turn}"}
        if turn <= len(calls):
            name, arguments = calls[turn - 1]
            message["content"] = None
            message["tool_calls"] = [{"id": f"expected-{turn}", "type": "function",
                "function": {"name": name, "arguments": json.dumps(arguments)}}]
        return reply(message)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = AsyncOpenAI(api_key="not-a-real-key", base_url="https://flow.invalid",
                             max_retries=0, http_client=http)
        model = OpenAIChatModel("deepseek-v4-pro", provider=DeepSeekProvider(openai_client=client))
        agent = Agent(model, capabilities=[Capability(id="FIRST", tools=[first_action], defer_loading=deferred),
                                          Capability(id="SECOND", tools=[second_action], defer_loading=deferred)])
        result = await agent.run("Perform both fixture actions.")
        assert result.output == "finished" and invoked == ["first", "second"]
    final = bodies[-1]["messages"]
    tools = [m for m in final if m["role"] == "assistant" and m.get("tool_calls")]
    names = [call["function"]["name"] for message in tools for call in message["tool_calls"]]
    assert names == (["load_capability", "search_tools", "first_action", "load_capability", "search_tools", "second_action"]
                     if deferred else ["first_action", "second_action"]), "synthesized history retained"
    for body in bodies:
        for message in body["messages"]:
            if message["role"] == "assistant" and message.get("tool_calls"):
                for call in message["tool_calls"]:
                    expected = "" if call["id"].startswith("auto_load_") else "fixture-turn-" + call["id"].split("-")[-1]
                    assert message.get("reasoning_content") == expected, "per-message reasoning integrity"
    return len(bodies)


async def main():
    assert pydantic_ai.__file__.startswith("/workspace/pydantic_ai_slim/")
    assert pydantic_graph.__file__.startswith("/workspace/pydantic_graph/")
    count = await verify_wire_matrix()
    flow_requests = await verify_two_capability_flow(False) + await verify_two_capability_flow(True)
    print(json.dumps({"passed": True, "wire_cases": count, "flow_fixture_requests": flow_requests,
                      "real_provider_requests": 0}))


if __name__ == "__main__":
    asyncio.run(main())
