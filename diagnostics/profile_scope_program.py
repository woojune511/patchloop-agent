"""Fixed public-issue contrast, executed inside the registered project environment.

Hold the serializer trigger fixed while varying the supplied profile's origin.
No private evaluator, reference patch, provider request, or implementation marker.
"""

from __future__ import annotations

import asyncio
import json
import socket
from dataclasses import replace
from pathlib import Path

FIELDS = ("reasoning_content", "scope_reasoning")
ORIGINS = ("ordinary", "provider_supplied")
MODEL_NAME = "profile-scope-fixture"


def expected_message(field: str, origin: str) -> dict:
    result = {
        "role": "assistant", "content": None,
        "tool_calls": [{"id": "public-scope-call", "type": "function",
                        "function": {"name": "roll_dice", "arguments": "{}"}}],
    }
    if origin == "provider_supplied":
        result[field] = ""
    return result


def forbidden(*args, **kwargs):
    raise AssertionError("The public profile contrast cannot use network connections")


async def main() -> int:
    # Imports stay inside main so operator-side receipt validation is stdlib-only.
    import httpx
    import pydantic_ai
    from openai import AsyncOpenAI
    from pydantic_ai import ModelResponse, ToolCallPart
    from pydantic_ai.models import openai as model_module
    from pydantic_ai.profiles import openai as profile_module
    from pydantic_ai.providers import deepseek as provider_module
    from pydantic_ai.providers.openai import OpenAIProvider

    modules = (pydantic_ai, model_module, profile_module, provider_module)
    paths = {module.__name__: str(Path(module.__file__).resolve()) for module in modules}
    if not all(Path(path).is_relative_to("/workspace/pydantic_ai_slim")
               for path in paths.values()):
        raise RuntimeError("The contrast must import the current workspace implementation")
    socket.socket.connect = forbidden
    socket.create_connection = forbidden
    rows = []
    async with httpx.AsyncClient(transport=httpx.MockTransport(forbidden)) as http:
        client = AsyncOpenAI(api_key="fixture-only", base_url="https://fixture.invalid",
                             max_retries=0, http_client=http)
        provider = OpenAIProvider(openai_client=client)
        supplied = provider_module.DeepSeekProvider.model_profile("deepseek-v4-flash")
        if supplied is None:
            raise RuntimeError("The public DeepSeek provider did not supply a profile")
        for field in FIELDS:
            profiles = {
                "ordinary": profile_module.OpenAIModelProfile(
                    openai_chat_send_back_thinking_parts="field", openai_chat_thinking_field=field,
                ),
                "provider_supplied": replace(supplied, openai_chat_thinking_field=field),
            }
            for origin in ORIGINS:
                model = model_module.OpenAIChatModel(
                    MODEL_NAME, provider=provider, profile=profiles[origin],
                )
                profile = profile_module.OpenAIModelProfile.from_profile(model.profile)
                if (profile.openai_chat_send_back_thinking_parts != "field"
                        or profile.openai_chat_thinking_field != field):
                    raise RuntimeError("The contrast failed to hold the field trigger fixed")
                response = ModelResponse(parts=[
                    ToolCallPart("roll_dice", {}, tool_call_id="public-scope-call"),
                ])
                actual = model._map_model_response(response)
                expected = expected_message(field, origin)
                row = {
                    "case": f"{origin}:{field}", "profile_origin": origin,
                    "mode": "field", "field": field, "provider": "openai",
                    "model": MODEL_NAME, "message_kind": "tool_only_without_thinking",
                    "actual": actual, "expected": expected, "passed": actual == expected,
                }
                rows.append(row)
                print(json.dumps(row, sort_keys=True), flush=True)
    passed = sum(row["passed"] for row in rows)
    print(json.dumps({"summary": {"passed": passed, "failed": len(rows) - passed},
                      "project_modules": paths}, sort_keys=True), flush=True)
    return int(passed != len(rows))


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
