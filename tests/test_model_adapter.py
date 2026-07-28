from __future__ import annotations

from types import SimpleNamespace

import pytest

from patchloop.agent.model import OpenAIResponsesAdapter, ReplayModelAdapter
from patchloop.contracts import ModelConfig
from patchloop.errors import ContractError


class FakeResponses:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            id="resp_test",
            model="gpt-5.6-terra",
            service_tier="default",
            system_fingerprint="fp_test",
            output=[
                SimpleNamespace(
                    type="function_call",
                    name="get_diff",
                    call_id="call_1",
                    arguments="{}",
                )
            ],
            output_text="",
            usage=SimpleNamespace(
                input_tokens=10,
                output_tokens=3,
                input_tokens_details=SimpleNamespace(
                    cached_tokens=4,
                    cache_write_tokens=2,
                ),
            ),
        )


class InvalidArgumentsResponses(FakeResponses):
    def create(self, **kwargs):
        response = super().create(**kwargs)
        response.output[0].arguments = '{"path":'
        return response


def test_openai_adapter_disables_provider_state() -> None:
    responses = FakeResponses()
    client = SimpleNamespace(responses=responses)
    adapter = OpenAIResponsesAdapter(
        ModelConfig(provider="openai", model_id="gpt-5.6-terra"), client=client
    )
    turn = adapter.next_turn("context", [])
    assert responses.kwargs["store"] is False
    assert responses.kwargs["reasoning"]["mode"] == "standard"
    assert responses.kwargs["reasoning"]["context"] == "current_turn"
    assert responses.kwargs["service_tier"] == "default"
    assert "previous_response_id" not in responses.kwargs
    assert turn.tool_calls[0].name == "get_diff"
    assert turn.cached_input_tokens == 4
    assert turn.cache_write_input_tokens == 2
    assert turn.response_model == "gpt-5.6-terra"
    assert turn.response_service_tier == "default"
    assert turn.system_fingerprint == "fp_test"


def test_openai_adapter_preserves_billed_usage_when_tool_arguments_are_invalid() -> None:
    responses = InvalidArgumentsResponses()
    adapter = OpenAIResponsesAdapter(
        ModelConfig(provider="openai", model_id="gpt-5.6-terra"),
        client=SimpleNamespace(responses=responses),
    )

    turn = adapter.next_turn("context", [])

    assert turn.tool_calls == []
    assert turn.done is False
    assert turn.error is not None
    assert turn.error.code == "invalid_tool_arguments_json"
    assert turn.input_tokens == 10
    assert turn.cached_input_tokens == 4
    assert turn.cache_write_input_tokens == 2
    assert turn.output_tokens == 3
    assert turn.response_id == "resp_test"


def test_replay_adapter_rejects_content_hash_mismatch() -> None:
    with pytest.raises(ContractError, match="replay hash mismatch"):
        ReplayModelAdapter(
            "replays/smoke/csv-quoted-newline.jsonl",
            expected_hash="sha256:" + "0" * 64,
        )
