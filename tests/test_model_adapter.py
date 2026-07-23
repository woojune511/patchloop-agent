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
            output=[
                SimpleNamespace(
                    type="function_call",
                    name="get_diff",
                    call_id="call_1",
                    arguments="{}",
                )
            ],
            output_text="",
            usage=SimpleNamespace(input_tokens=10, output_tokens=3),
        )


def test_openai_adapter_disables_provider_state() -> None:
    responses = FakeResponses()
    client = SimpleNamespace(responses=responses)
    adapter = OpenAIResponsesAdapter(
        ModelConfig(provider="openai", model_id="gpt-5.6-terra"), client=client
    )
    turn = adapter.next_turn("context", [])
    assert responses.kwargs["store"] is False
    assert responses.kwargs["reasoning"]["context"] == "current_turn"
    assert "previous_response_id" not in responses.kwargs
    assert turn.tool_calls[0].name == "get_diff"


def test_replay_adapter_rejects_content_hash_mismatch() -> None:
    with pytest.raises(ContractError, match="replay hash mismatch"):
        ReplayModelAdapter(
            "replays/smoke/csv-quoted-newline.jsonl",
            expected_hash="sha256:" + "0" * 64,
        )
