from __future__ import annotations

from types import SimpleNamespace

import pytest

from patchloop.agent.model import OpenAIResponsesAdapter, ReplayModelAdapter
from patchloop.contracts import ModelConfig
from patchloop.errors import ContractError


class FakeResponses:
    def __init__(self) -> None:
        self.kwargs = None
        self.count_kwargs = None
        self.input_tokens = SimpleNamespace(count=self.count)

    def count(self, **kwargs):
        self.count_kwargs = kwargs
        return SimpleNamespace(input_tokens=10)

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            id="resp_test",
            model="gpt-5.6-terra",
            service_tier="default",
            system_fingerprint="fp_test",
            status="completed",
            truncation="disabled",
            incomplete_details=None,
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
                output_tokens_details=SimpleNamespace(reasoning_tokens=1),
                total_tokens=13,
            ),
        )


class InvalidArgumentsResponses(FakeResponses):
    def create(self, **kwargs):
        response = super().create(**kwargs)
        response.output[0].arguments = '{"path":'
        return response


class MismatchedTokenCountResponses(FakeResponses):
    def count(self, **kwargs):
        self.count_kwargs = kwargs
        return SimpleNamespace(input_tokens=11)


class IncompleteResponses(FakeResponses):
    def create(self, **kwargs):
        response = super().create(**kwargs)
        response.status = "incomplete"
        response.incomplete_details = SimpleNamespace(reason="max_output_tokens")
        return response


class TokenCountFailureResponses(FakeResponses):
    def __init__(self) -> None:
        super().__init__()
        self.create_called = False

    def count(self, **kwargs):
        self.count_kwargs = kwargs
        raise RuntimeError("token count unavailable")

    def create(self, **kwargs):
        self.create_called = True
        return super().create(**kwargs)


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
    assert responses.kwargs["truncation"] == "disabled"
    assert responses.count_kwargs["truncation"] == "disabled"
    assert responses.count_kwargs["input"] == responses.kwargs["input"]
    assert responses.count_kwargs["tools"] == responses.kwargs["tools"]
    assert "previous_response_id" not in responses.kwargs
    system_prompt = responses.kwargs["input"][0]["content"]
    assert "diff --git" in system_prompt
    assert "*** Begin Patch" in system_prompt
    assert turn.tool_calls[0].name == "get_diff"
    assert turn.cached_input_tokens == 4
    assert turn.cache_write_input_tokens == 2
    assert turn.response_model == "gpt-5.6-terra"
    assert turn.response_service_tier == "default"
    assert turn.system_fingerprint == "fp_test"
    assert turn.requested_input_tokens == 10
    assert turn.input_token_count_match is True
    assert turn.total_token_count_match is True
    assert turn.input_token_count_calls == 1
    assert turn.reasoning_output_tokens == 1
    assert turn.total_tokens == 13
    assert turn.response_status == "completed"
    assert turn.response_truncation == "disabled"
    assert turn.response_incomplete_reason is None


def test_openai_adapter_executes_a_precounted_request_without_counting_twice() -> None:
    responses = FakeResponses()
    adapter = OpenAIResponsesAdapter(
        ModelConfig(provider="openai", model_id="gpt-5.6-terra"),
        client=SimpleNamespace(responses=responses),
    )
    request = adapter.request_payload("context", [])

    requested_input_tokens = adapter.count_input_tokens(request)
    turn = adapter.execute_request(
        request,
        requested_input_tokens=requested_input_tokens,
    )

    assert requested_input_tokens == 10
    assert responses.count_kwargs is not None
    assert responses.kwargs == request
    assert turn.input_token_count_calls == 1
    assert turn.input_token_count_match is True


def test_gpt54mini_adapter_omits_gpt56_reasoning_controls() -> None:
    adapter = OpenAIResponsesAdapter(
        ModelConfig(
            provider="openai",
            model_id="gpt-5.4-mini-2026-03-17",
            reasoning_effort="medium",
            reasoning_mode="standard",
        ),
        client=SimpleNamespace(responses=FakeResponses()),
    )

    request = adapter.request_payload("context", [])

    assert request["reasoning"] == {"effort": "medium"}
    assert request["store"] is False
    assert request["truncation"] == "disabled"
    assert "previous_response_id" not in request


def test_openai_adapter_binds_zero_transport_retries_without_changing_legacy(
    monkeypatch,
) -> None:
    constructor_kwargs: list[dict] = []
    transport_kwargs: list[dict] = []
    transports: list[SimpleNamespace] = []

    def fake_http_client(**kwargs):
        transport_kwargs.append(kwargs)
        transport = SimpleNamespace(close=lambda: None)
        transports.append(transport)
        return transport

    def fake_openai(**kwargs):
        constructor_kwargs.append(kwargs)
        return SimpleNamespace(responses=FakeResponses())

    monkeypatch.setattr("patchloop.agent.model.httpx.Client", fake_http_client)
    monkeypatch.setattr("patchloop.agent.model.OpenAI", fake_openai)
    legacy = ModelConfig(
        provider="openai",
        model_id="gpt-5.4-mini-2026-03-17",
    )
    readiness = ModelConfig(
        provider="openai",
        model_id="gpt-5.4-mini-2026-03-17",
        transport_max_retries=0,
    )

    OpenAIResponsesAdapter(legacy)
    OpenAIResponsesAdapter(readiness)

    assert transport_kwargs == [{"trust_env": False}, {"trust_env": False}]
    assert constructor_kwargs == [
        {
            "base_url": "https://api.openai.com/v1",
            "http_client": transports[0],
        },
        {
            "base_url": "https://api.openai.com/v1",
            "http_client": transports[1],
            "max_retries": 0,
        },
    ]
    assert "transport_max_retries" not in legacy.model_dump(mode="json")
    assert readiness.model_dump(mode="json")["transport_max_retries"] == 0
    with pytest.raises(ValueError):
        ModelConfig(
            provider="openai",
            model_id="gpt-5.4-mini-2026-03-17",
            transport_max_retries=1,
        )
    with pytest.raises(ValueError, match="JSON integer 0"):
        ModelConfig(
            provider="openai",
            model_id="gpt-5.4-mini-2026-03-17",
            transport_max_retries=False,
        )


def test_openai_adapter_closes_transport_when_client_construction_fails(
    monkeypatch,
) -> None:
    transport = SimpleNamespace(closed=False)

    def close() -> None:
        transport.closed = True

    transport.close = close
    monkeypatch.setattr(
        "patchloop.agent.model.httpx.Client",
        lambda **kwargs: (
            transport
            if kwargs == {"trust_env": False}
            else pytest.fail("unexpected transport configuration")
        ),
    )

    def fail_openai(**kwargs):
        assert kwargs == {
            "base_url": "https://api.openai.com/v1",
            "http_client": transport,
            "max_retries": 0,
        }
        raise RuntimeError("synthetic constructor failure")

    monkeypatch.setattr("patchloop.agent.model.OpenAI", fail_openai)

    with pytest.raises(RuntimeError, match="synthetic constructor failure"):
        OpenAIResponsesAdapter(
            ModelConfig(
                provider="openai",
                model_id="gpt-5.4-mini-2026-03-17",
                transport_max_retries=0,
            )
        )

    assert transport.closed is True


def test_openai_adapter_rejects_injected_client_retry_drift() -> None:
    config = ModelConfig(
        provider="openai",
        model_id="gpt-5.4-mini-2026-03-17",
        transport_max_retries=0,
    )

    with pytest.raises(ContractError, match="transport retry policy"):
        OpenAIResponsesAdapter(
            config,
            client=SimpleNamespace(
                responses=FakeResponses(),
                max_retries=2,
            ),
        )

    adapter = OpenAIResponsesAdapter(
        config,
        client=SimpleNamespace(
            responses=FakeResponses(),
            max_retries=0,
        ),
    )
    assert adapter.client.max_retries == 0


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


def test_openai_adapter_rejects_input_token_count_mismatch_after_preserving_usage() -> None:
    responses = MismatchedTokenCountResponses()
    adapter = OpenAIResponsesAdapter(
        ModelConfig(provider="openai", model_id="gpt-5.6-terra"),
        client=SimpleNamespace(responses=responses),
    )

    turn = adapter.next_turn("context", [])

    assert turn.tool_calls == []
    assert turn.error is not None
    assert turn.error.code == "input_token_count_mismatch"
    assert turn.requested_input_tokens == 11
    assert turn.input_tokens == 10
    assert turn.input_token_count_match is False
    assert turn.output_tokens == 3


def test_openai_adapter_rejects_incomplete_response_after_preserving_usage() -> None:
    responses = IncompleteResponses()
    adapter = OpenAIResponsesAdapter(
        ModelConfig(provider="openai", model_id="gpt-5.6-terra"),
        client=SimpleNamespace(responses=responses),
    )

    turn = adapter.next_turn("context", [])

    assert turn.tool_calls == []
    assert turn.error is not None
    assert turn.error.code == "incomplete_response"
    assert turn.response_status == "incomplete"
    assert turn.response_incomplete_reason == "max_output_tokens"
    assert turn.input_tokens == 10
    assert turn.output_tokens == 3


def test_openai_adapter_does_not_generate_when_exact_token_count_fails() -> None:
    responses = TokenCountFailureResponses()
    adapter = OpenAIResponsesAdapter(
        ModelConfig(provider="openai", model_id="gpt-5.6-terra"),
        client=SimpleNamespace(responses=responses),
    )

    with pytest.raises(RuntimeError, match="token count unavailable"):
        adapter.next_turn("context", [])

    assert responses.create_called is False


def test_replay_adapter_rejects_content_hash_mismatch() -> None:
    with pytest.raises(ContractError, match="replay hash mismatch"):
        ReplayModelAdapter(
            "replays/smoke/csv-quoted-newline.jsonl",
            expected_hash="sha256:" + "0" * 64,
        )
