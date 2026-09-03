from __future__ import annotations

import json
import os
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

import patchloop.dev.runner as runner
from patchloop.agent.model import (
    EncryptedReasoningContinuationItem as ProviderReasoningItem,
)
from patchloop.agent.model import FunctionCallContinuationRef as ProviderFunctionCallRef
from patchloop.agent.model import ModelTurn, ModelTurnError, OpenAIResponsesAdapter
from patchloop.agent.model import RequestedTool as ProviderRequestedTool
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import ModelConfig
from patchloop.dev.contracts import (
    DevLimits,
    DevModelTurn,
    DevRunRequest,
    DevToolResult,
    EncryptedReasoningContinuationItem,
    FunctionCallContinuationRef,
    ProviderContinuationArtifact,
    PublicTurnDecision,
    RequestedTool,
)
from patchloop.dev.cost import DEFAULT_OUTPUT_CEILING, pricing_for_model
from patchloop.dev.model import MOCK_MUTATIONS, MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ContractError, RecoveryError, ResumeContractMismatch
from patchloop.repository import WorkspaceManager as RealWorkspaceManager
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, sha256_json


def inspection_decision(label: str) -> PublicTurnDecision:
    return PublicTurnDecision(
        mode="inspect",
        basis=f"basis-{label}",
        evidence_goal=f"goal-{label}",
    )


def test_latest_tool_result_is_not_evicted_by_working_set(gateway_factory, smoke_package) -> None:
    gateway, journal, _ = gateway_factory()
    for index in range(12):
        gateway.spans[f"span_ffffffffffff{index:04d}"] = {
            "span_id": f"span_ffffffffffff{index:04d}",
            "path": "mini_data_utils/csvlite.py",
            "start_line": 1,
            "end_line": 1,
            "content": f"old-{index}",
            "file_hash": "sha256:" + "0" * 64,
            "last_observed_seq": index + 1,
        }
    latest_call = RequestedTool(
            name="read_file",
            action_id="latest-read",
            arguments={
                "path": "mini_data_utils/csvlite.py",
                "start_line": 1,
                "end_line": 13,
            },
            turn_decision=inspection_decision("latest-read"),
        )
    latest = gateway.execute(latest_call)
    context = json.loads(
        runner._build_context(  # noqa: SLF001 - direct context contract test
            package=smoke_package,
            gateway=gateway,
            journal=journal,
            correction=None,
            latest_tool_results=[latest],
            counters=runner._RunCounters(),  # noqa: SLF001
            elapsed_seconds=0,
            limits=DevRunRequest(
                provider="mock",
                task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
                model="mock-dev",
            ).limits,
        )
    )
    projected = context["latest_tool_results"][0]["output"]["spans"]
    assert projected[0]["span_id"] == latest.output["spans"][0]["span_id"]
    assert len(context["source_spans"]) == 8

    limits = DevLimits()
    horizon = runner._tool_policy(  # noqa: SLF001 - direct scheduler contract test
        gateway,
        runner._RunCounters(model_calls=limits.max_model_calls - 3),  # noqa: SLF001
        limits,
    )
    assert horizon.minimum_completion_calls == 3
    assert horizon.exploration_allowed is False
    assert horizon.exploration_state == "closed"
    assert horizon.closure_reason == "completion_horizon"
    assert horizon.allowed_tools == frozenset({"apply_git_diff", "stop_task"})
    assert horizon.max_parallel_reads == 0

    legacy_limit_reached = runner._tool_policy(  # noqa: SLF001
        gateway,
        runner._RunCounters(  # noqa: SLF001
            model_calls=24,
            inspection_turns_at_diff=limits.max_consecutive_inspection_turns,
        ),
        limits,
    )
    assert legacy_limit_reached.exploration_allowed is True
    assert legacy_limit_reached.exploration_state == "open"
    assert {"read_file", "search_files"}.issubset(
        legacy_limit_reached.allowed_tools
    )

    gateway.last_failed_mutation = {"action_id": "failed-mutation"}
    repair = runner._tool_policy(  # noqa: SLF001 - direct scheduler contract test
        gateway,
        runner._RunCounters(  # noqa: SLF001
            model_calls=24,
            inspection_turns_at_diff=limits.max_consecutive_inspection_turns,
            failed_mutation_repair_turns=(
                limits.max_failed_mutation_repair_turns - 1
            ),
            failed_mutation_pending=True,
        ),
        limits,
    )
    assert {"read_file", "search_files"}.issubset(repair.allowed_tools)
    exhausted_repair = runner._tool_policy(  # noqa: SLF001
        gateway,
        runner._RunCounters(  # noqa: SLF001
            model_calls=24,
            inspection_turns_at_diff=limits.max_consecutive_inspection_turns,
            failed_mutation_repair_turns=limits.max_failed_mutation_repair_turns,
            failed_mutation_pending=True,
        ),
        limits,
    )
    assert {"read_file", "search_files"}.issubset(exhausted_repair.allowed_tools)

    last_opportunity = runner._tool_policy(  # noqa: SLF001
        gateway,
        runner._RunCounters(  # noqa: SLF001
            model_calls=limits.max_model_calls - horizon.minimum_completion_calls - 1,
        ),
        limits,
    )
    assert last_opportunity.exploration_state == "last_opportunity"
    assert last_opportunity.tools_closing_after_this_turn == (
        "read_file",
        "search_files",
    )

    saved_spans = dict(gateway.spans)
    gateway.spans.clear()
    required_read = runner._tool_policy(  # noqa: SLF001
        gateway,
        runner._RunCounters(  # noqa: SLF001
            model_calls=limits.max_model_calls - 4,
        ),
        limits.model_copy(
            update={
                "max_consecutive_inspection_turns": 0,
                "max_failed_mutation_repair_turns": 0,
            }
        ),
    )
    assert required_read.exploration_allowed is False
    assert required_read.required_inspection_for_completion is True
    assert required_read.max_parallel_reads == 1
    assert {"read_file", "search_files"}.issubset(required_read.allowed_tools)
    gateway.spans.update(saved_spans)

    journal.append(
        "turn_started",
        {
            "turn_id": "turn-before-horizon",
            "available_tool_names": [
                "apply_git_diff",
                "read_file",
                "search_files",
                "stop_task",
            ],
        },
    )
    journal.append(
        "turn_decision_recorded",
        {"turn_id": "turn-before-horizon", "tool_calls": []},
    )
    transition = runner._tool_policy_transition(  # noqa: SLF001
        journal,
        horizon,
    )
    assert transition == {
        "from": "inspection_open",
        "to": "execution_only",
        "reason": "completion_horizon",
        "removed_tools": ["read_file", "search_files"],
        "added_tools": [],
        "remaining_tools": ["apply_git_diff", "stop_task"],
    }
    journal.append(
        "tool_policy_transition",
        {"turn_id": "turn-after-horizon", **transition},
    )
    assert sum(
        row["event_type"] == "tool_policy_transition" for row in journal.events()
    ) == 1
    projected_transition = json.loads(
        runner._build_context(  # noqa: SLF001
            package=smoke_package,
            gateway=gateway,
            journal=journal,
            correction=None,
            latest_tool_results=[],
            counters=runner._RunCounters(  # noqa: SLF001
                model_calls=limits.max_model_calls - 3,
            ),
            elapsed_seconds=0,
            limits=limits,
            policy=horizon,
            tool_policy_transition=transition,
        )
    )
    assert projected_transition["action_horizon"]["tool_policy_transition"] == transition

    correction = runner._protocol_correction(  # noqa: SLF001
        turn_id="turn-after-horizon",
        code="MISSING_REQUIRED_TOOL",
        issue="A tool call is required.",
        gateway=gateway,
        policy=horizon,
    )
    assert correction["available_tool_names"] == ["apply_git_diff", "stop_task"]
    assert "read_file" not in correction["message"]
    assert "search_files" not in correction["message"]
    last_correction = runner._protocol_correction(  # noqa: SLF001
        turn_id="turn-last-inspection",
        code="MISSING_REQUIRED_TOOL",
        issue="A tool call is required.",
        gateway=gateway,
        policy=last_opportunity,
    )
    assert "last inspection opportunity" in last_correction["message"]

    open_policy = runner._tool_policy(  # noqa: SLF001
        gateway,
        runner._RunCounters(),  # noqa: SLF001
        limits,
    )
    journal.append(
        "turn_started",
        {
            "turn_id": "turn-before-anchor",
            "workflow_gate": "needs_mutation",
            "available_tool_names": [
                "read_file",
                "run_check",
                "search_files",
                "stop_task",
            ],
        },
    )
    journal.append(
        "turn_decision_recorded",
        {"turn_id": "turn-before-anchor", "tool_calls": []},
    )
    evidence_transition = runner._tool_policy_transition(  # noqa: SLF001
        journal,
        open_policy,
    )
    assert evidence_transition is not None
    assert evidence_transition["from"] == "inspection_open"
    assert evidence_transition["to"] == "inspection_open"
    assert evidence_transition["reason"] == "evidence_changed"
    assert evidence_transition["added_tools"] == ["apply_git_diff"]


def test_turn_decision_is_bound_to_cache_action_and_projected_once_per_batch(
    gateway_factory,
    smoke_package,
) -> None:
    gateway, journal, _ = gateway_factory()
    arguments = {
        "path": "mini_data_utils/csvlite.py",
        "start_line": 1,
        "end_line": 13,
    }
    first_decision = inspection_decision("initial-cause")
    first_call = RequestedTool(
            name="read_file",
            action_id="working-state-first",
            arguments=arguments,
            turn_decision=first_decision,
        )
    first = gateway.execute(first_call)
    runner._record_tool_batch(  # noqa: SLF001 - direct context contract test
        journal=journal,
        gateway=gateway,
        turn_id="working-state-first-turn",
        calls=[first_call],
        results=[first],
        active_elapsed_ms=1,
    )

    revised_decision = PublicTurnDecision(
        mode="inspect",
        basis="The visible loop confirms physical-line parsing.",
        evidence_goal="Confirm that replacing the loop preserves the return type.",
    )
    revised_call = RequestedTool(
            name="read_file",
            action_id="working-state-revised",
            arguments=arguments,
            turn_decision=revised_decision,
        )
    revised = gateway.execute(revised_call)
    runner._record_tool_batch(  # noqa: SLF001 - direct context contract test
        journal=journal,
        gateway=gateway,
        turn_id="working-state-revised-turn",
        calls=[revised_call],
        results=[revised],
        active_elapsed_ms=2,
    )
    context = json.loads(
        runner._build_context(  # noqa: SLF001 - direct context contract test
            package=smoke_package,
            gateway=gateway,
            journal=journal,
            correction=None,
            latest_tool_results=[revised],
            counters=runner._RunCounters(),  # noqa: SLF001
            elapsed_seconds=0,
            limits=DevRunRequest(
                provider="mock",
                task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
                model="mock-dev",
            ).limits,
        )
    )
    expected = revised_decision.model_dump(mode="json")

    assert revised.evidence_cache_hit is True
    assert revised.input_hash != first.input_hash
    assert revised.output["read_request_hash"] == first.output["read_request_hash"]
    assert "turn_decision" not in revised.output
    assert "turn_decision" not in context["latest_tool_results"][0]["output"]
    card = context["recent_attempt_result_next_question"][-1]
    assert "turn_decision" not in card
    assert card["result"]["actions"][0]["turn_decision"] == expected
    parallel_card = runner._batch_attempt_card(  # noqa: SLF001 - context contract test
        turn_id="call-specific-parallel-turn",
        calls=[first_call, revised_call],
        results=[first, revised],
        gateway=gateway,
    )
    assert [
        action["turn_decision"] for action in parallel_card["result"]["actions"]
    ] == [
        first_decision.model_dump(mode="json"),
        revised_decision.model_dump(mode="json"),
    ]


def test_failed_read_batch_retains_its_bounded_action_decision(gateway_factory) -> None:
    gateway, _, _ = gateway_factory()
    decision = inspection_decision("failed-read")
    call = RequestedTool(
            name="read_file",
            action_id="working-state-failed-read",
            arguments={"path": "missing.py", "start_line": 1, "end_line": 10},
            turn_decision=decision,
        )
    result = gateway.execute(call)
    card = runner._batch_attempt_card(  # noqa: SLF001 - context contract test
        turn_id="failed-read-turn",
        calls=[call],
        results=[result],
        gateway=gateway,
    )

    assert result.status == "failed"
    assert "turn_decision" not in result.output
    assert "turn_decision" not in card
    assert card["result"]["actions"][0]["turn_decision"] == decision.model_dump(
        mode="json"
    )
    assert card["result"]["actions"][0]["status"] == "failed"


def test_openai_request_requires_a_tool_and_records_only_output_shape() -> None:
    observed: dict[str, dict] = {}

    class FakeInputTokens:
        def count(self, **payload):
            observed["count"] = payload
            return SimpleNamespace(input_tokens=17)

    class FakeResponses:
        input_tokens = FakeInputTokens()

        def create(self, **payload):
            observed["create"] = payload
            return SimpleNamespace(
                id="response-shape-only",
                model="gpt-5.4-mini-2026-03-17",
                status="completed",
                incomplete_details=None,
                output=[
                    SimpleNamespace(
                        type="reasoning",
                        id="reasoning-shape-only",
                        encrypted_content="encrypted-shape-only-sentinel",
                        status="completed",
                        content="private-reasoning-sentinel",
                    ),
                    SimpleNamespace(type="message", content="public-message-sentinel"),
                ],
                usage=SimpleNamespace(
                    input_tokens=17,
                    input_tokens_details=SimpleNamespace(cached_tokens=3),
                    output_tokens=5,
                    output_tokens_details=SimpleNamespace(reasoning_tokens=2),
                ),
            )

    fake_client = SimpleNamespace(max_retries=0, responses=FakeResponses())
    adapter = OpenAIResponsesAdapter(
        ModelConfig(
            provider="openai",
            model_id="gpt-5.4-mini-2026-03-17",
            reasoning_continuation="encrypted-v1",
            transport_max_retries=0,
            max_output_tokens=DEFAULT_OUTPUT_CEILING,
        ),
        api_key="unused-test-key",
        client=fake_client,
    )
    request = adapter.request_payload(
        "{}",
        dev_tool_schemas(finish_enabled=False, check_ids=["public-check"]),
        system_prompt="test prompt",
    )

    assert request["tool_choice"] == "required"
    assert request["store"] is False
    assert request["include"] == ["reasoning.encrypted_content"]
    assert request["max_output_tokens"] == DEFAULT_OUTPUT_CEILING == 25_000
    native_input = [
        {"role": "system", "content": "test prompt"},
        {
            "type": "function_call_output",
            "call_id": "call-public",
            "output": "{}",
        },
        {"role": "user", "content": "{}"},
    ]
    native_request = adapter.request_payload(
        native_input,
        dev_tool_schemas(finish_enabled=False, check_ids=["public-check"]),
        system_prompt="test prompt",
    )
    assert native_request["input"] == native_input
    assert adapter.count_input_tokens_v2(request) == 17
    assert observed["count"]["tool_choice"] == "required"
    assert "include" not in observed["count"]

    turn = adapter.execute_request(request, requested_input_tokens=17)

    assert observed["create"]["tool_choice"] == "required"
    assert turn.error is None
    assert turn.tool_calls == []
    assert turn.output_item_count == 2
    assert turn.non_tool_output_item_count == 2
    assert turn.output_item_types == ("reasoning", "message")
    assert turn.output_shape_hash == sha256_json(
        {"item_count": 2, "item_types": ("reasoning", "message")}
    )
    assert "private-reasoning-sentinel" not in repr(turn)
    assert "public-message-sentinel" not in repr(turn)
    assert "encrypted-shape-only-sentinel" not in repr(turn)
    assert len(turn.provider_continuation) == 1


def test_openai_incomplete_reason_remains_typed_metadata(tmp_path) -> None:
    class FakeInputTokens:
        def count(self, **payload):
            del payload
            return SimpleNamespace(input_tokens=17)

    class FakeResponses:
        input_tokens = FakeInputTokens()

        def create(self, **payload):
            del payload
            return SimpleNamespace(
                id="response-incomplete",
                model="gpt-5.4-mini-2026-03-17",
                status="incomplete",
                incomplete_details={"reason": "max_output_tokens"},
                output=[
                    SimpleNamespace(
                        type="reasoning",
                        id="reasoning-incomplete",
                        encrypted_content="encrypted-incomplete-sentinel",
                        status="incomplete",
                        content="not persisted",
                    )
                ],
                usage=SimpleNamespace(
                    input_tokens=17,
                    input_tokens_details=SimpleNamespace(cached_tokens=0),
                    output_tokens=DEFAULT_OUTPUT_CEILING,
                    output_tokens_details=SimpleNamespace(
                        reasoning_tokens=DEFAULT_OUTPUT_CEILING
                    ),
                ),
            )

    adapter = OpenAIResponsesAdapter(
        ModelConfig(
            provider="openai",
            model_id="gpt-5.4-mini-2026-03-17",
            reasoning_continuation="encrypted-v1",
            transport_max_retries=0,
            max_output_tokens=DEFAULT_OUTPUT_CEILING,
        ),
        api_key="unused-test-key",
        client=SimpleNamespace(max_retries=0, responses=FakeResponses()),
    )
    request = adapter.request_payload(
        "{}",
        dev_tool_schemas(finish_enabled=False, check_ids=["public-check"]),
        system_prompt="test prompt",
    )

    raw = adapter.execute_request(request, requested_input_tokens=17)
    turn = runner._turn_from_openai(raw)  # noqa: SLF001 - provider boundary test

    assert turn.error_code == "incomplete_response"
    assert turn.incomplete_reason == "max_output_tokens"
    assert turn.output_tokens == turn.reasoning_output_tokens == DEFAULT_OUTPUT_CEILING
    assert turn.tool_calls == []
    assert "not persisted" not in repr(turn)
    assert "encrypted-incomplete-sentinel" not in repr(turn)
    assert turn.provider_continuation is not None
    reference = runner._store_provider_continuation(  # noqa: SLF001
        ArtifactStore(tmp_path / "artifacts"),
        turn.provider_continuation,
    )
    artifact_text = Path(reference.artifact.path).read_text(encoding="utf-8")
    assert "not persisted" not in artifact_text
    assert "encrypted-incomplete-sentinel" in artifact_text


def test_encrypted_reasoning_and_parallel_calls_replay_in_provider_order(tmp_path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    journal = DevJournal(tmp_path, "run_dev_reasoning_order")
    turn_id = "turn-reasoning-order"
    calls = [
        RequestedTool(
            name="read_file",
            action_id="read-a",
            arguments={"path": "a.py", "start_line": 1, "end_line": 2},
            turn_decision=inspection_decision("read-a"),
        ),
        RequestedTool(
            name="search_files",
            action_id="search-b",
            arguments={"query": "needle", "path": "."},
            turn_decision=inspection_decision("search-b"),
        ),
    ]
    continuation = ProviderContinuationArtifact(
        output_order=[
            EncryptedReasoningContinuationItem(
                id="reasoning-a",
                encrypted_content="encrypted-order-a",
                status="completed",
            ),
            FunctionCallContinuationRef(action_id="read-a"),
            EncryptedReasoningContinuationItem(
                id="reasoning-b",
                encrypted_content="encrypted-order-b",
                status="completed",
            ),
            FunctionCallContinuationRef(action_id="search-b"),
        ]
    )
    reference = runner._store_provider_continuation(  # noqa: SLF001
        store,
        continuation,
    )
    journal.append(
        "turn_started",
        {"turn_id": turn_id, "context_hash": "sha256:" + "0" * 64},
    )
    journal.append(
        "turn_decision_recorded",
        {
            "turn_id": turn_id,
            "tool_calls": [call.model_dump(mode="json") for call in calls],
            "error_code": None,
            "output_item_types": [
                "reasoning",
                "function_call",
                "reasoning",
                "function_call",
            ],
            "continuation_ref": reference.model_dump(mode="json"),
        },
    )
    journal.append(
        "tool_batch_finished",
        {"turn_id": turn_id, "action_ids": ["read-a", "search-b"]},
    )
    results = [
        DevToolResult(
            action_id="read-a",
            input_hash="sha256:" + "1" * 64,
            tool="read_file",
            status="succeeded",
            output={"spans": []},
        ),
        DevToolResult(
            action_id="search-b",
            input_hash="sha256:" + "2" * 64,
            tool="search_files",
            status="succeeded",
            output={"spans": []},
        ),
    ]
    context = json.dumps(
        {"latest_tool_results": [result.model_dump(mode="json") for result in results]}
    )

    model_input = runner._build_model_input(  # noqa: SLF001
        journal=journal,
        artifact_store=store,
        context=context,
        latest_tool_results=results,
    )

    replayed = [
        item
        for item in model_input
        if item.get("type") in {"reasoning", "function_call", "function_call_output"}
    ]
    assert [item["type"] for item in replayed] == [
        "reasoning",
        "function_call",
        "reasoning",
        "function_call",
        "function_call_output",
        "function_call_output",
    ]
    assert [item.get("id") for item in replayed if item["type"] == "reasoning"] == [
        "reasoning-a",
        "reasoning-b",
    ]
    assert all(
        item["summary"] == [] for item in replayed if item["type"] == "reasoning"
    )
    assert "encrypted-order-a" not in journal.path.read_text(encoding="utf-8")
    artifact_text = reference.artifact.path
    assert "encrypted-order-a" in Path(artifact_text).read_text(encoding="utf-8")


def test_protocol_rejection_preserves_reasoning_and_call_linkage(tmp_path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    journal = DevJournal(tmp_path, "run_dev_reasoning_rejection")
    turn_id = "turn-reasoning-rejection"
    call = RequestedTool(
        name="read_file",
        action_id="rejected-read",
        arguments={"path": "a.py", "start_line": 1, "end_line": 2},
        turn_decision=inspection_decision("rejected-read"),
    )
    reference = runner._store_provider_continuation(  # noqa: SLF001
        store,
        ProviderContinuationArtifact(
            output_order=[
                EncryptedReasoningContinuationItem(
                    id="reasoning-rejected",
                    encrypted_content="encrypted-rejected-sentinel",
                    status="completed",
                ),
                FunctionCallContinuationRef(action_id=call.action_id),
            ]
        ),
    )
    journal.append(
        "turn_started",
        {"turn_id": turn_id, "context_hash": "sha256:" + "0" * 64},
    )
    journal.append(
        "turn_decision_recorded",
        {
            "turn_id": turn_id,
            "tool_calls": [call.model_dump(mode="json")],
            "continuation_ref": reference.model_dump(mode="json"),
        },
    )
    journal.append(
        "protocol_correction",
        {
            "turn_id": turn_id,
            "code": "INVALID_TOOL_BATCH",
            "message": "The requested read is not currently available.",
            "available_tool_names": ["apply_git_diff", "stop_task"],
        },
    )

    model_input = runner._build_model_input(  # noqa: SLF001
        journal=journal,
        artifact_store=store,
        context=json.dumps({"latest_tool_results": []}),
        latest_tool_results=[],
    )

    assert [item.get("type") for item in model_input[1:-1]] == [
        "reasoning",
        "function_call",
        "function_call_output",
    ]
    rejection = json.loads(model_input[-2]["output"])
    assert rejection == {
        "action_id": "rejected-read",
        "available_tool_names": ["apply_git_diff", "stop_task"],
        "error_code": "INVALID_TOOL_BATCH",
        "message": "The requested read is not currently available.",
        "status": "rejected",
    }
    mismatched = ProviderContinuationArtifact(
        output_order=[
            EncryptedReasoningContinuationItem(
                id="reasoning-mismatch",
                encrypted_content="encrypted-mismatch",
                status="completed",
            ),
            FunctionCallContinuationRef(action_id="different-action"),
        ]
    )
    with pytest.raises(
        runner._ProviderContinuationError,  # noqa: SLF001
        match="actions do not match",
    ):
        runner._validate_continuation_action_order(  # noqa: SLF001
            mismatched,
            [call],
        )


def test_missing_encrypted_reasoning_is_a_typed_provider_error() -> None:
    class FakeInputTokens:
        def count(self, **payload):
            del payload
            return SimpleNamespace(input_tokens=5)

    class FakeResponses:
        input_tokens = FakeInputTokens()

        def create(self, **payload):
            del payload
            return SimpleNamespace(
                id="response-missing-encrypted-reasoning",
                model="gpt-5.4-mini-2026-03-17",
                status="completed",
                incomplete_details=None,
                output=[SimpleNamespace(type="reasoning", id="reasoning-missing")],
                usage=SimpleNamespace(
                    input_tokens=5,
                    input_tokens_details=SimpleNamespace(cached_tokens=0),
                    output_tokens=3,
                    output_tokens_details=SimpleNamespace(reasoning_tokens=3),
                ),
            )

    adapter = OpenAIResponsesAdapter(
        ModelConfig(
            provider="openai",
            model_id="gpt-5.4-mini-2026-03-17",
            reasoning_continuation="encrypted-v1",
            transport_max_retries=0,
        ),
        api_key="unused-test-key",
        client=SimpleNamespace(max_retries=0, responses=FakeResponses()),
    )
    request = adapter.request_payload("{}", [], system_prompt="test prompt")

    turn = adapter.execute_request(request, requested_input_tokens=5)

    assert turn.error is not None
    assert turn.error.code == "provider_continuation_error"
    assert turn.provider_continuation == ()


def test_invalid_provider_turn_decision_becomes_bounded_protocol_error() -> None:
    raw = ModelTurn(
        tool_calls=[
            ProviderRequestedTool(
                name="read_file",
                action_id="invalid-provider-state",
                arguments={
                    "path": "mini_data_utils/csvlite.py",
                    "start_line": 1,
                    "end_line": 10,
                    "turn_decision": {
                        "mode": "inspect",
                        "basis": "x" * 801,
                        "evidence_goal": "gap",
                    },
                },
            )
        ],
        requested_input_tokens=17,
        input_tokens=17,
        output_tokens=5,
        reasoning_output_tokens=2,
        response_id="invalid-state-response",
        response_status="completed",
        output_item_count=2,
        non_tool_output_item_count=1,
        output_item_types=("reasoning", "function_call"),
        output_shape_hash=sha256_json(
            {"item_count": 2, "item_types": ("reasoning", "function_call")}
        ),
    )

    converted = runner._turn_from_openai(raw)  # noqa: SLF001 - provider boundary test

    assert converted.error_code == "invalid_dev_tool_contract"
    assert converted.tool_calls == []
    assert converted.input_tokens == 17
    assert converted.output_tokens == 5
    assert converted.output_item_types == ["reasoning", "function_call"]


def test_failed_mutation_stays_projected_after_read_cards_without_protocol_label(
    gateway_factory,
    smoke_package,
) -> None:
    gateway, journal, _ = gateway_factory()
    source = gateway.execute(
        RequestedTool(
            name="read_file",
            action_id="failed-mutation-source",
            arguments={
                "path": "mini_data_utils/csvlite.py",
                "start_line": 1,
                "end_line": 20,
            },
        )
    )
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    malformed_patch = mutation.patch.replace(" import csv\n", " import csv_missing\n")
    failed_call = RequestedTool(
            name="apply_git_diff",
            action_id="failed-mutation",
            arguments={
                "git_diff": malformed_patch,
                "hypothesis": mutation.hypothesis,
                "expected_behavior": mutation.expected_behavior,
                "evidence_span_ids": [source.output["spans"][0]["span_id"]],
                "edit_anchor": {
                    "path": mutation.path,
                    "old_text": mutation.anchor,
                    "occurrence": 1,
                },
                "falsified_prior_hypothesis": None,
                "alternative_mechanism": None,
            },
            turn_decision=PublicTurnDecision(
                mode="mutate",
                basis="The public source supplies the mutation anchor.",
                evidence_goal=None,
            ),
        )
    failed = gateway.execute(failed_call)
    _, correction = runner._record_tool_batch(  # noqa: SLF001 - context contract test
        journal=journal,
        gateway=gateway,
        turn_id="failed-mutation-turn",
        calls=[failed_call],
        results=[failed],
        active_elapsed_ms=1,
    )
    assert correction is None

    repair_decision = inspection_decision("failed-mutation-repair")
    read_calls = [
            RequestedTool(
                name="read_file",
                action_id=f"read-after-failure-{index}",
                arguments={
                    "path": "mini_data_utils/csvlite.py",
                    "start_line": index,
                    "end_line": index + 5,
                },
                turn_decision=repair_decision,
            )
            for index in range(1, 5)
        ]
    reads = gateway.execute_batch(read_calls)
    runner._record_tool_batch(  # noqa: SLF001 - displace the bounded attempt cards
        journal=journal,
        gateway=gateway,
        turn_id="read-after-failure-turn",
        calls=read_calls,
        results=reads,
        active_elapsed_ms=2,
    )
    context = json.loads(
        runner._build_context(  # noqa: SLF001 - direct context contract test
            package=smoke_package,
            gateway=gateway,
            journal=journal,
            correction=None,
            latest_tool_results=reads,
            counters=runner._RunCounters(),  # noqa: SLF001
            elapsed_seconds=0,
            limits=DevRunRequest(
                provider="mock",
                task=repository_root()
                / "tasks"
                / "smoke"
                / "csv-quoted-newline"
                / "public.yaml",
                model="mock-dev",
            ).limits,
        )
    )

    assert context["last_failed_mutation"]["git_diff"] == malformed_patch
    assert "patch failed: mini_data_utils/csvlite.py:1" in context[
        "last_failed_mutation"
    ]["error_message"]
    assert [
        card["attempt"] for card in context["recent_attempt_result_next_question"]
    ] == ["apply_git_diff", "inspect"]
    assert len(context["recent_attempt_result_next_question"][-1]["result"]["actions"]) == 4


def test_context_projects_every_current_diff_check_and_names_the_remaining_one(
    gateway_factory,
    smoke_package,
) -> None:
    gateway, journal, _ = gateway_factory()
    source = gateway.execute(
        RequestedTool(
            name="read_file",
            action_id="four-check-source",
            arguments={
                "path": "mini_data_utils/csvlite.py",
                "start_line": 1,
                "end_line": 20,
            },
        )
    )
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    applied = gateway.execute(
        RequestedTool(
            name="apply_git_diff",
            action_id="four-check-mutation",
            arguments={
                "git_diff": mutation.patch,
                "hypothesis": mutation.hypothesis,
                "expected_behavior": mutation.expected_behavior,
                "evidence_span_ids": [source.output["spans"][0]["span_id"]],
                "edit_anchor": {
                    "path": mutation.path,
                    "old_text": mutation.anchor,
                    "occurrence": 1,
                },
                "falsified_prior_hypothesis": None,
                "alternative_mechanism": None,
            },
        )
    )
    assert applied.status == "succeeded"

    original_check = smoke_package.public.visible_checks[0]
    check_ids = ["contract", "basic-regression", "field-regression", "upstream-regression"]
    public = smoke_package.public.model_copy(
        update={
            "visible_checks": [
                original_check.model_copy(update={"id": check_id}) for check_id in check_ids
            ]
        }
    )
    gateway.public_task = public
    diff_hash = gateway.current_diff_hash
    for check_id in check_ids[:3]:
        gateway._remember_check(  # noqa: SLF001 - reconstruct current public evidence
            {
                "check_id": check_id,
                "diff_hash": diff_hash,
                "passed": True,
                "failure_signature": None,
            }
        )
    last_pass = DevToolResult(
        action_id="third-visible-pass",
        input_hash=sha256_json("third-visible-pass"),
        tool="run_check",
        status="succeeded",
        output={
            "check_id": check_ids[2],
            "diff_hash": diff_hash,
            "passed": True,
            "failure_signature": None,
        },
    )

    context = json.loads(
        runner._build_context(  # noqa: SLF001 - direct context contract test
            package=SimpleNamespace(public=public),
            gateway=gateway,
            journal=journal,
            correction=None,
            latest_tool_results=[last_pass],
            counters=runner._RunCounters(),  # noqa: SLF001
            elapsed_seconds=0,
            limits=DevRunRequest(
                provider="mock",
                task=repository_root()
                / "tasks"
                / "smoke"
                / "csv-quoted-newline"
                / "public.yaml",
                model="mock-dev",
            ).limits,
        )
    )
    card = runner._attempt_card(last_pass, gateway)  # noqa: SLF001

    assert [row["check_id"] for row in context["visible_check_status"]] == check_ids
    assert [row["status"] for row in context["visible_check_status"]] == [
        "PASS",
        "PASS",
        "PASS",
        "NOT_RUN",
    ]
    assert context["remaining_visible_check_ids"] == ["upstream-regression"]
    assert context["workflow_gate"] == "needs_visible_checks"
    assert card["next_question"] == (
        "Run one remaining visible check for the current diff: upstream-regression"
    )
    assert "failure" not in card["next_question"].lower()
    encoded = json.dumps(context)
    assert "hidden-multiline-csv" not in encoded
    assert "reference_patch" not in encoded


def test_mock_end_to_end_isolated_evaluator_and_public_context(tmp_path, monkeypatch) -> None:
    contexts: list[str] = []
    tool_names: list[list[str]] = []

    class CapturingMock(MockDevAdapter):
        def next_turn(self, context, tools):
            contexts.append(context)
            tool_names.append([tool["name"] for tool in tools])
            return super().next_turn(context, tools)

    monkeypatch.setattr(runner, "MockDevAdapter", CapturingMock)
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    result = runner.run_dev(request)
    run = result["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    assert run["evaluator"] == {
        "task_acceptance": "PASS",
        "safety_state": "NOT_RUN",
        "failure_class": None,
        "claim_eligible": False,
    }
    assert run["call_counts"] == {"model": 4, "input_count": 0, "tool": 5}
    assert run["accepted_mutations"] == 1
    assert all("hidden-multiline-csv" not in context for context in contexts)
    assert all("reference_patch" not in context for context in contexts)
    context_keys = {
        "public_task",
        "current_diff",
        "latest_tool_results",
        "source_spans",
        "recent_checks",
        "visible_check_status",
        "remaining_visible_check_ids",
        "last_successful_mutation",
        "last_failed_mutation",
        "recent_attempt_result_next_question",
        "workflow_gate",
        "available_tool_names",
        "action_horizon",
        "remaining_budget",
    }
    assert all(set(json.loads(context)) == context_keys for context in contexts)
    assert [sorted(names) for names in tool_names] == [
        json.loads(context)["available_tool_names"] for context in contexts
    ]
    projected = [
        json.loads(context)["current_diff"]
        for context in contexts
        if json.loads(context)["current_diff"]["patch"]
    ]
    assert projected
    assert all(item["truncated"] is False for item in projected)

    journal_path = tmp_path / "runs" / f"{run['run_id']}.jsonl"
    rows = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    assert all(row["schema_version"] == "dev-run-v1" for row in rows)
    assert all(row["official"] is False for row in rows)
    assert all(row["event_type"] != "state_changed" for row in rows)
    assert [json.loads(context)["workflow_gate"] for context in contexts] == [
        "needs_mutation",
        "needs_mutation",
        "needs_visible_checks",
        "ready_to_submit",
    ]
    assert [
        json.loads(context)["action_horizon"]["inspection_turns_at_current_diff"]
        for context in contexts
    ] == [0, 1, 0, 0]
    assert len([row for row in rows if row["event_type"] == "turn_decision_recorded"]) == 4
    assert len([row for row in rows if row["event_type"] == "tool_batch_finished"]) == 4
    terminal = next(row for row in rows if row["event_type"] == "terminal")
    assert terminal["payload"]["milestones"]["submission"]["patch_hash"].startswith("sha256:")
    turns = [row for row in rows if row["event_type"] == "turn_started"]
    assert len(turns) == 4
    assert all(row["payload"]["context_hash"].startswith("sha256:") for row in turns)
    assert all(row["payload"]["model_input_hash"].startswith("sha256:") for row in turns)
    second_input_path = Path(turns[1]["payload"]["model_input_artifact"]["path"])
    second_input = json.loads(second_input_path.read_text(encoding="utf-8"))
    assert sha256_bytes(second_input_path.read_bytes()) == turns[1]["payload"][
        "model_input_hash"
    ]
    function_calls = [item for item in second_input if item.get("type") == "function_call"]
    function_outputs = [
        item for item in second_input if item.get("type") == "function_call_output"
    ]
    assert [item["call_id"] for item in function_calls] == [
        item["call_id"] for item in function_outputs
    ]
    assert [item["call_id"] for item in function_outputs] == turns[1]["payload"][
        "transcript_action_ids"
    ]
    prior_results = json.loads(contexts[1])["latest_tool_results"]
    assert [json.loads(item["output"]) for item in function_outputs] == prior_results
    current_input_context = json.loads(second_input[-1]["content"])
    assert current_input_context["latest_tool_results"] == []
    assert current_input_context["latest_tool_results_delivery"] == {
        "format": "preceding_function_call_output_items",
        "action_ids": turns[1]["payload"]["transcript_action_ids"],
    }
    assert "working_state" not in json.dumps(second_input)
    assert "hidden-multiline-csv" not in json.dumps(second_input)
    assert "reference_patch" not in json.dumps(second_input)
    assert any(
        result["output"].get("spans")
        for context in contexts[1:]
        for result in json.loads(context)["latest_tool_results"]
    )
    evaluator = next(row for row in rows if row["event_type"] == "evaluator_finished")
    assert evaluator["payload"]["agent_context_reinjected"] is False
    event_types = [row["event_type"] for row in rows]
    assert event_types.index("submission_recorded") < event_types.index("manifest_recorded")
    assert event_types.index("manifest_recorded") < event_types.index("evaluator_finished")
    envelope_path = tmp_path / "runs" / f"{run['run_id']}.envelope.json"
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    assert envelope["schema_version"] == "dev-run-envelope-v1"
    manifest = json.loads(
        (tmp_path / "artifacts" / "runs" / run["run_id"] / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["task_content_hash"] == envelope["task_content_hash"]
    assert manifest["runtime_content_hash"] == envelope["runtime_hash"]
    assert manifest["model"]["max_output_tokens"] == DEFAULT_OUTPUT_CEILING
    assert manifest["model"]["reasoning_continuation"] == "none"
    assert manifest["submitted_patch_content_hash"] == run["artifact_hashes"][
        "submitted_patch"
    ]
    assert manifest["visible_check_diff_hash"] == manifest["submitted_patch_content_hash"]
    assert manifest["submitted_changed_files"] == ["mini_data_utils/csvlite.py"]
    workspace_roots = [path for path in (tmp_path / "workspaces").iterdir() if path.is_dir()]
    assert len(workspace_roots) == 2

    journal_before_resume = journal_path.read_bytes()

    class ForbiddenAdapter:
        def __init__(self, task_id):
            del task_id
            raise AssertionError("terminal resume must not initialize the model")

    monkeypatch.setattr(runner, "MockDevAdapter", ForbiddenAdapter)
    resumed = runner.run_dev(request.model_copy(update={"resume_run_id": run["run_id"]}))
    assert resumed["runs"][0] == run
    assert journal_path.read_bytes() == journal_before_resume


def test_unexpected_tool_gateway_failure_writes_terminal(tmp_path, monkeypatch) -> None:
    class ExplodingGateway(runner.DevToolGateway):
        def execute_batch(self, calls):
            del calls
            raise RuntimeError("simulated gateway crash")

    monkeypatch.setattr(runner, "DevToolGateway", ExplodingGateway)
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    result = runner.run_dev(request)
    run = result["runs"][0]
    assert run["terminal"] == "TASK_FAILED"

    journal_path = tmp_path / "runs" / f"{run['run_id']}.jsonl"
    rows = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    terminal = [row for row in rows if row["event_type"] == "terminal"]
    assert len(terminal) == 1
    assert terminal[0]["payload"]["message"] == "tool gateway failed: RuntimeError"


def test_manifest_submission_and_terminal_provenance_survive_evaluator_error(
    tmp_path,
    monkeypatch,
) -> None:
    observed = {"called": False}

    def fail_after_manifest(
        self,
        task_dir,
        patch_path,
        manifest,
        usage=None,
        submitted_patch_artifact=None,
    ):
        del task_dir, usage
        observed["called"] = True
        manifest_path = self.artifact_store.root / "runs" / manifest.run_id / "manifest.json"
        assert manifest_path.is_file()
        assert submitted_patch_artifact is not None
        assert Path(patch_path).read_bytes() == self.artifact_store.read_bytes(
            submitted_patch_artifact
        )
        raise RuntimeError("simulated evaluator failure")

    monkeypatch.setattr(runner.EvaluationEngine, "evaluate", fail_after_manifest)
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    result = runner.run_dev(request)
    run = result["runs"][0]
    assert observed["called"] is True
    assert run["terminal"] == "EVALUATOR_ERROR"
    assert run["evaluator"] == {
        "task_acceptance": "ERROR",
        "safety_state": "ERROR",
        "failure_class": "EVALUATOR_INFRA_FAILURE",
        "claim_eligible": False,
    }
    run_artifacts = tmp_path / "artifacts" / "runs" / run["run_id"]
    assert (run_artifacts / "manifest.json").is_file()
    assert (run_artifacts / "terminal-provenance.json").is_file()
    manifest_text = (run_artifacts / "manifest.json").read_text(encoding="utf-8")
    assert "hidden-multiline-csv" not in manifest_text
    assert "reference.patch" not in manifest_text
    assert {"submitted_patch", "manifest", "terminal_provenance"}.issubset(
        run["artifact_hashes"]
    )


def test_invalid_tool_batch_gets_one_correction_then_stops(tmp_path, monkeypatch) -> None:
    class InvalidBatchMock:
        calls = 0

        def __init__(self, task_id) -> None:
            del task_id

        def next_turn(self, context, tools):
            del context, tools
            self.calls += 1
            return DevModelTurn(
                tool_calls=[
                    RequestedTool(
                        name="read_file",
                        action_id=f"bad-read-{self.calls}",
                        arguments={"path": "mini_data_utils/csvlite.py"},
                    ),
                    RequestedTool(
                        name="run_check",
                        action_id=f"bad-check-{self.calls}",
                        arguments={"check_id": "existing-unit-tests"},
                    ),
                ]
            )

    monkeypatch.setattr(runner, "MockDevAdapter", InvalidBatchMock)
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    result = runner.run_dev(request)
    run = result["runs"][0]
    assert run["terminal"] == "PROTOCOL_VIOLATION"
    assert run["call_counts"] == {"model": 2, "input_count": 0, "tool": 0}

    journal_path = tmp_path / "runs" / f"{run['run_id']}.jsonl"
    rows = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    assert len([row for row in rows if row["event_type"] == "protocol_correction"]) == 1


def test_protocol_correction_limit_is_consecutive_and_stop_is_structured(
    tmp_path,
    monkeypatch,
) -> None:
    class AlternatingBatchMock:
        def __init__(self, task_id) -> None:
            del task_id
            self.calls = 0

        def next_turn(self, context, tools):
            del context, tools
            self.calls += 1
            if self.calls in {1, 3}:
                return DevModelTurn(
                    tool_calls=[
                        RequestedTool(
                            name="read_file",
                            action_id=f"mixed-read-{self.calls}",
                            arguments={
                                "path": "mini_data_utils/csvlite.py",
                                "start_line": 1,
                                "end_line": 20,
                            },
                            turn_decision=inspection_decision("invalid-mixed"),
                        ),
                        RequestedTool(
                            name="run_check",
                            action_id=f"mixed-check-{self.calls}",
                            arguments={"check_id": "existing-unit-tests"},
                            turn_decision=PublicTurnDecision(
                                mode="verify",
                                basis="invalid mixed batch",
                                evidence_goal=None,
                            ),
                        ),
                    ]
                )
            if self.calls == 2:
                return DevModelTurn(
                    tool_calls=[
                        RequestedTool(
                            name="read_file",
                            action_id="valid-read-between-corrections",
                            arguments={
                                "path": "mini_data_utils/csvlite.py",
                                "start_line": 1,
                                "end_line": 20,
                            },
                            turn_decision=inspection_decision(
                                "valid-between-corrections"
                            ),
                        )
                    ]
                )
            return DevModelTurn(
                tool_calls=[
                    RequestedTool(
                        name="stop_task",
                        action_id="structured-stop",
                        arguments={
                            "reason_code": "insufficient_public_evidence",
                            "summary": "No additional public evidence supports a safe edit.",
                            "evidence_span_ids": [],
                        },
                        turn_decision=PublicTurnDecision(
                            mode="stop",
                            basis="No further safe public action is available.",
                            evidence_goal=None,
                        ),
                    )
                ]
            )

    monkeypatch.setattr(runner, "MockDevAdapter", AlternatingBatchMock)
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )

    run = runner.run_dev(request)["runs"][0]

    assert run["terminal"] == "AGENT_STOPPED"
    assert run["call_counts"] == {"model": 4, "input_count": 0, "tool": 2}
    assert run["accepted_mutations"] == 0
    assert run["agent_stop"] == {
        "reason_code": "insufficient_public_evidence",
        "summary": "No additional public evidence supports a safe edit.",
        "evidence_span_ids": [],
        "diff_hash": sha256_bytes(b""),
    }
    journal = DevJournal(tmp_path, run["run_id"])
    rows = journal.events()
    assert len([row for row in rows if row["event_type"] == "protocol_correction"]) == 2
    assert len([row for row in rows if row["event_type"] == "tool_batch_finished"]) == 2
    assert not any(row["event_type"] == "submission_recorded" for row in rows)
    assert not any(row["event_type"] == "evaluator_finished" for row in rows)


def test_resume_counter_restores_only_corrections_since_last_valid_batch(tmp_path) -> None:
    journal = DevJournal(tmp_path, "run_dev_consecutive01")
    journal.append("protocol_correction", {"turn_id": "turn-invalid-before"})
    journal.append("tool_batch_finished", {"turn_id": "turn-valid"})
    journal.append("protocol_correction", {"turn_id": "turn-invalid-after"})

    counters = runner._restore_counters(journal)  # noqa: SLF001 - resume contract test

    assert counters.protocol_recoveries == 1


def test_resume_recovers_the_exact_incomplete_reason(tmp_path) -> None:
    journal = DevJournal(tmp_path, "run_dev_incomplete_reason")
    journal.append(
        "provider_call_finished",
        {
            "call_id": "call-incomplete",
            "turn_id": "turn-incomplete",
            "tool_calls": [],
            "error_code": "incomplete_response",
            "incomplete_reason": "max_output_tokens",
        },
    )

    runner._recover_unrecorded_decision(journal)  # noqa: SLF001 - recovery contract test

    decision = next(
        row["payload"]
        for row in journal.events()
        if row["event_type"] == "turn_decision_recorded"
    )
    assert decision["error_code"] == "incomplete_response"
    assert decision["incomplete_reason"] == "max_output_tokens"


def test_live_rejects_non_dev_train_before_credential_or_provider(tmp_path) -> None:
    env_file = tmp_path / "credential.env"
    env_file.write_text("OPENAI_API_KEY=not-used\n", encoding="utf-8")
    request = DevRunRequest(
        provider="openai",
        task=(
            repository_root()
            / "tasks"
            / "dev-validation"
            / "babel-strict-grouped-decimal-trailing-zeroes-v2"
            / "public.yaml"
        ),
        model="gpt-5.4-mini-2026-03-17",
        env_file=env_file,
        max_cost_usd=Decimal("0.01"),
        state_root=tmp_path / "state",
    )
    with pytest.raises(ContractError, match="dev-train"):
        runner.run_dev(request)


def test_live_source_preflight_scopes_cleanliness_to_relevant_tracked_paths(tmp_path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "patchloop@example.invalid"],
        cwd=repository,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "PatchLoop Test"],
        cwd=repository,
        check=True,
    )
    runtime_file = repository / "patchloop" / "runtime.py"
    runtime_file.parent.mkdir()
    runtime_file.write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repository, check=True)

    scratch = repository / "scratch" / "untracked.txt"
    scratch.parent.mkdir()
    scratch.write_text("ignored by the selected pathspec\n", encoding="utf-8")
    runner._require_tracked_clean_paths(repository, ["patchloop/runtime.py"])

    runtime_file.write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(ContractError, match="match HEAD"):
        runner._require_tracked_clean_paths(repository, ["patchloop/runtime.py"])

    with pytest.raises(ContractError, match="must all be tracked"):
        runner._require_tracked_clean_paths(repository, ["missing.py"])


def test_live_missing_local_image_stops_before_provider(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / "credential.env"
    env_file.write_text("OPENAI_API_KEY=test-only-sentinel\n", encoding="utf-8")
    monkeypatch.setattr(runner.DockerSandbox, "available", staticmethod(lambda: True))
    monkeypatch.setattr(runner.DockerSandbox, "image_identity", lambda self: None)
    monkeypatch.setattr(runner, "_live_source_preflight", lambda task_dir, package: None)
    request = DevRunRequest(
        provider="openai",
        task=(
            repository_root()
            / "tasks"
            / "dev-train"
            / "anyio-interrupt-runner-cleanup"
            / "public.yaml"
        ),
        model="gpt-5.4-mini-2026-03-17",
        env_file=env_file,
        max_cost_usd=Decimal("0.01"),
        state_root=tmp_path / "state",
    )
    result = runner.run_dev(request)
    assert result["runs"][0]["terminal"] == "PREFLIGHT_FAILED"
    assert result["runs"][0]["call_counts"]["model"] == 0


class _SnapshotWorkspaceManager:
    smoke = load_task_package(repository_root() / "tasks" / "smoke" / "csv-quoted-newline")
    diff_summary = staticmethod(RealWorkspaceManager.diff_summary)

    def __init__(self, fixture_root, workspace_root) -> None:
        self.delegate = RealWorkspaceManager(fixture_root, workspace_root)

    def create(self, run_id, repository_url, expected_revision=None):
        del repository_url, expected_revision
        return self.delegate.create(
            run_id,
            self.smoke.public.repository.url,
            self.smoke.public.repository.base_commit,
        )

    def validate_managed_workspace(self, workspace):
        return self.delegate.validate_managed_workspace(workspace)


def _live_request(tmp_path: Path, *, repeat: int = 3, cap: str = "0.01") -> DevRunRequest:
    tmp_path.mkdir(parents=True, exist_ok=True)
    env_file = tmp_path / "credential.env"
    env_file.write_text("OPENAI_API_KEY=test-only-sentinel\n", encoding="utf-8")
    return DevRunRequest(
        provider="openai",
        task=(
            repository_root()
            / "tasks"
            / "dev-train"
            / "anyio-interrupt-runner-cleanup"
            / "public.yaml"
        ),
        model="gpt-5.4-mini-2026-03-17",
        env_file=env_file,
        max_cost_usd=Decimal(cap),
        repeat=repeat,
        state_root=tmp_path / "state",
    )


def _patch_live_boundaries(monkeypatch) -> None:
    monkeypatch.setattr(runner, "_live_source_preflight", lambda task_dir, package: None)
    monkeypatch.setattr(runner, "_live_sandbox_preflight", lambda package: LocalSandbox())
    monkeypatch.setattr(runner, "WorkspaceManager", _SnapshotWorkspaceManager)


def test_model_hash_binds_the_configured_output_ceiling(tmp_path, monkeypatch) -> None:
    request = _live_request(tmp_path, repeat=1, cap="1.20")
    pricing = pricing_for_model(request.model)
    initial = runner._model_hash(request, pricing)  # noqa: SLF001 - model identity test

    monkeypatch.setattr(runner, "DEFAULT_OUTPUT_CEILING", DEFAULT_OUTPUT_CEILING + 1)

    assert runner._model_hash(request, pricing) != initial  # noqa: SLF001


def test_live_output_ceiling_replay_and_missing_continuation_are_durable(
    tmp_path,
    monkeypatch,
) -> None:
    configured_ceilings: list[int] = []
    configured_continuations: list[str] = []
    model_inputs: list[list[dict]] = []
    execute_calls = 0

    class IncompleteAdapter:
        def __init__(self, config, *, api_key) -> None:
            assert api_key == "test-only-sentinel"
            configured_ceilings.append(config.max_output_tokens)
            configured_continuations.append(config.reasoning_continuation)

        def request_payload(self, context, tools, *, system_prompt):
            model_inputs.append(context)
            return {"context": context, "tools": tools, "system": system_prompt}

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            del request
            assert timeout_seconds > 0
            return 100

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            nonlocal execute_calls
            assert timeout_seconds > 0
            assert request["max_output_tokens"] == DEFAULT_OUTPUT_CEILING
            execute_calls += 1
            if execute_calls == 2:
                return ModelTurn(
                    requested_input_tokens=requested_input_tokens,
                    input_tokens=requested_input_tokens,
                    output_tokens=3,
                    reasoning_output_tokens=3,
                    response_id="response-missing-continuation",
                    response_model="gpt-5.4-mini-2026-03-17",
                    response_status="completed",
                    output_item_count=1,
                    non_tool_output_item_count=1,
                    output_item_types=("reasoning",),
                    output_shape_hash=sha256_json(
                        {"item_count": 1, "item_types": ("reasoning",)}
                    ),
                )
            return ModelTurn(
                requested_input_tokens=requested_input_tokens,
                input_tokens=requested_input_tokens,
                output_tokens=DEFAULT_OUTPUT_CEILING,
                reasoning_output_tokens=DEFAULT_OUTPUT_CEILING,
                response_id=f"response-incomplete-{execute_calls}",
                response_model="gpt-5.4-mini-2026-03-17",
                response_status="incomplete",
                response_incomplete_reason="max_output_tokens",
                error=ModelTurnError(
                    "incomplete_response",
                    "provider response was incomplete: max_output_tokens",
                ),
                output_item_count=1,
                non_tool_output_item_count=1,
                output_item_types=("reasoning",),
                output_shape_hash=sha256_json(
                    {"item_count": 1, "item_types": ("reasoning",)}
                ),
                provider_continuation=(
                    ProviderReasoningItem(
                        id=f"reasoning-incomplete-{execute_calls}",
                        encrypted_content=f"encrypted-incomplete-{execute_calls}",
                        status="incomplete",
                    ),
                ),
            )

    _patch_live_boundaries(monkeypatch)
    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", IncompleteAdapter)
    request = _live_request(tmp_path, repeat=1, cap="0.30").model_copy(
        update={"limits": DevLimits(max_model_calls=2)}
    )

    result = runner.run_dev(request)
    run = result["runs"][0]

    assert run["terminal"] == "PROVIDER_CONTINUATION_ERROR"
    assert run["call_counts"] == {"model": 2, "input_count": 2, "tool": 0}
    assert configured_ceilings == [DEFAULT_OUTPUT_CEILING]
    assert configured_continuations == ["encrypted-v1"]
    assert execute_calls == 2
    replayed_reasoning = [
        item for item in model_inputs[1] if item.get("type") == "reasoning"
    ]
    assert replayed_reasoning == [
        {
            "type": "reasoning",
            "id": "reasoning-incomplete-1",
            "encrypted_content": "encrypted-incomplete-1",
            "summary": [],
            "status": "incomplete",
        }
    ]
    assert not any(
        item.get("type") == "function_call_output" for item in model_inputs[1]
    )
    journal = DevJournal(request.state_root, run["run_id"])
    events = journal.events()
    starts = [row["payload"] for row in events if row["event_type"] == "provider_call_started"]
    provider_turns = [
        row["payload"] for row in events if row["event_type"] == "provider_call_finished"
    ]
    decisions = [
        row["payload"] for row in events if row["event_type"] == "turn_decision_recorded"
    ]
    correction = next(
        row["payload"] for row in events if row["event_type"] == "protocol_correction"
    )
    terminal = next(row["payload"] for row in events if row["event_type"] == "terminal")
    assert [row["output_ceiling"] for row in starts] == [
        DEFAULT_OUTPUT_CEILING,
        DEFAULT_OUTPUT_CEILING,
    ]
    assert provider_turns[0]["incomplete_reason"] == "max_output_tokens"
    assert provider_turns[0]["continuation_ref"] is not None
    assert provider_turns[1]["incomplete_reason"] is None
    assert provider_turns[1]["continuation_ref"] is None
    assert provider_turns[1]["error_code"] == "provider_continuation_error"
    assert decisions[0]["incomplete_reason"] == "max_output_tokens"
    assert decisions[1]["error_code"] == "provider_continuation_error"
    assert "encrypted-incomplete" not in journal.path.read_text(encoding="utf-8")
    assert "max_output_tokens" in correction["message"]
    assert terminal["message"] == "provider reasoning output has no encrypted continuation"
    assert not any(
        row["event_type"] == "tool_batch_started" for row in events
    )


class _SimulatedCrash(BaseException):
    pass


def _enveloped_run_id(state_root: Path) -> str:
    envelopes = list((state_root / "runs").glob("run_dev_*.envelope.json"))
    assert len(envelopes) == 1
    return envelopes[0].name.removesuffix(".envelope.json")


def _crash_journal_once(
    monkeypatch,
    *,
    event_type: str,
    when: str,
    predicate=lambda payload: True,
) -> None:
    original = DevJournal.append
    fired = False

    def append(self, current_type, payload=None):
        nonlocal fired
        matches = not fired and current_type == event_type and predicate(payload or {})
        if matches and when == "before":
            fired = True
            raise _SimulatedCrash(current_type)
        result = original(self, current_type, payload)
        if matches and when == "after":
            fired = True
            raise _SimulatedCrash(current_type)
        return result

    monkeypatch.setattr(DevJournal, "append", append)


@pytest.mark.parametrize(
    "crash_case",
    [
        "decision_recorded",
        "mutation_before_result",
        "check_result_recorded",
        "batch_before_finished",
    ],
)
def test_mock_resume_replays_durable_work_without_duplicate_mutation(
    tmp_path,
    monkeypatch,
    crash_case,
) -> None:
    if crash_case == "decision_recorded":
        _crash_journal_once(
            monkeypatch,
            event_type="turn_decision_recorded",
            when="after",
        )
    elif crash_case == "mutation_before_result":
        _crash_journal_once(
            monkeypatch,
            event_type="action_finished",
            when="before",
            predicate=lambda payload: payload.get("result", {}).get("tool")
            == "apply_git_diff",
        )
    elif crash_case == "check_result_recorded":
        _crash_journal_once(
            monkeypatch,
            event_type="action_finished",
            when="after",
            predicate=lambda payload: payload.get("result", {}).get("tool") == "run_check",
        )
    else:
        _crash_journal_once(
            monkeypatch,
            event_type="tool_batch_finished",
            when="before",
            predicate=lambda payload: any(
                action_id.startswith("mock-visible-check-")
                for action_id in payload.get("action_ids", [])
            ),
        )

    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)

    run_id = _enveloped_run_id(tmp_path)
    resumed = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    run = resumed["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    assert run["call_counts"] == {"model": 4, "input_count": 0, "tool": 5}
    assert run["accepted_mutations"] == 1

    journal = DevJournal(tmp_path, run_id)
    action_results = [
        row["payload"]["result"]
        for row in journal.events()
        if row["event_type"] == "action_finished"
    ]
    mutation_results = [row for row in action_results if row["tool"] == "apply_git_diff"]
    assert len(mutation_results) == 1
    assert len([row for row in journal.events() if row["event_type"] == "run_resumed"]) == 1


def test_resume_contract_and_workspace_mismatch_do_not_change_journal(
    tmp_path,
    monkeypatch,
) -> None:
    _crash_journal_once(
        monkeypatch,
        event_type="turn_decision_recorded",
        when="after",
    )
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(tmp_path)
    journal = DevJournal(tmp_path, run_id)
    before = journal.path.read_bytes()

    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(
            request.model_copy(
                update={"resume_run_id": run_id, "model": "different-mock-model"}
            )
        )
    assert journal.path.read_bytes() == before

    workspace = tmp_path / "workspaces" / run_id / "repo"
    target = workspace / "mini_data_utils" / "csvlite.py"
    target.write_text(target.read_text(encoding="utf-8") + "\n# external drift\n", encoding="utf-8")
    with pytest.raises(ResumeContractMismatch, match="workspace diff"):
        runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    assert journal.path.read_bytes() == before


def test_runtime_mismatch_and_pre_envelope_run_fail_before_journal_change(
    tmp_path,
    monkeypatch,
) -> None:
    _crash_journal_once(
        monkeypatch,
        event_type="turn_decision_recorded",
        when="after",
    )
    request = DevRunRequest(
        provider="mock",
        task=repository_root() / "tasks" / "smoke" / "csv-quoted-newline" / "public.yaml",
        model="mock-dev",
        state_root=tmp_path,
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(tmp_path)
    journal = DevJournal(tmp_path, run_id)
    before = journal.path.read_bytes()
    monkeypatch.setattr(runner, "_runtime_hash", lambda: "sha256:" + "f" * 64)
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    assert journal.path.read_bytes() == before

    old = DevJournal(tmp_path, "run_dev_oldformat0001")
    old.append("run_started", {"runtime": "dev-head"})
    old_before = old.path.read_bytes()
    with pytest.raises(RecoveryError, match="predates resumable envelopes"):
        runner.run_dev(
            request.model_copy(update={"resume_run_id": "run_dev_oldformat0001"})
        )
    assert old.path.read_bytes() == old_before


def test_resume_rejects_raw_task_content_drift_without_journal_change(
    tmp_path,
    monkeypatch,
) -> None:
    task_dir = tmp_path / "copied-task"
    shutil.copytree(
        repository_root() / "tasks" / "smoke" / "csv-quoted-newline",
        task_dir,
    )
    state_root = tmp_path / "state"
    _crash_journal_once(
        monkeypatch,
        event_type="turn_decision_recorded",
        when="after",
    )
    request = DevRunRequest(
        provider="mock",
        task=task_dir / "public.yaml",
        model="mock-dev",
        state_root=state_root,
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(state_root)
    journal = DevJournal(state_root, run_id)
    before = journal.path.read_bytes()
    public = task_dir / "public.yaml"
    public.write_text(
        public.read_text(encoding="utf-8") + "\n# raw task drift\n",
        encoding="utf-8",
    )

    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    assert journal.path.read_bytes() == before


def test_provider_response_resume_does_not_repeat_provider_call(tmp_path, monkeypatch) -> None:
    calls = {"execute": 0}

    class OneReadAdapter:
        def __init__(self, config, *, api_key) -> None:
            del config, api_key

        def request_payload(self, context, tools, *, system_prompt):
            return {"context": context, "tools": tools, "system": system_prompt}

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            del request
            assert timeout_seconds > 0
            return 100

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            del request
            assert timeout_seconds > 0
            calls["execute"] += 1
            return ModelTurn(
                tool_calls=[
                    ProviderRequestedTool(
                        name="stop_task",
                        action_id="provider-stop-once",
                        arguments={
                            "reason_code": "insufficient_public_evidence",
                            "summary": "Stop at the one-call test horizon.",
                            "evidence_span_ids": [],
                            "turn_decision": PublicTurnDecision(
                                mode="stop",
                                basis="Only an explicit stop fits the current horizon.",
                                evidence_goal=None,
                            ).model_dump(mode="json"),
                        },
                    )
                ],
                requested_input_tokens=requested_input_tokens,
                input_tokens=requested_input_tokens,
                output_tokens=1,
                response_id="response-once",
                response_model="mocked-provider",
                response_status="completed",
                output_item_count=2,
                non_tool_output_item_count=1,
                output_item_types=("reasoning", "function_call"),
                output_shape_hash=sha256_json(
                    {
                        "item_count": 2,
                        "item_types": ("reasoning", "function_call"),
                    }
                ),
                provider_continuation=(
                    ProviderReasoningItem(
                        id="reasoning-provider-stop",
                        encrypted_content="encrypted-provider-stop",
                        status="completed",
                    ),
                    ProviderFunctionCallRef(action_id="provider-stop-once"),
                ),
            )

    _patch_live_boundaries(monkeypatch)
    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", OneReadAdapter)
    _crash_journal_once(
        monkeypatch,
        event_type="provider_call_finished",
        when="after",
    )
    request = _live_request(tmp_path, repeat=1, cap="0.10").model_copy(
        update={"limits": DevLimits(max_model_calls=1)}
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)

    resumed = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    run = resumed["runs"][0]
    assert run["terminal"] == "AGENT_STOPPED"
    assert run["call_counts"] == {"model": 1, "input_count": 1, "tool": 1}
    assert run["cost_nanos"] > 0
    assert calls["execute"] == 1
    journal = DevJournal(request.state_root, run_id)
    for event_type in {"provider_call_finished", "turn_decision_recorded"}:
        payload = next(
            row["payload"] for row in journal.events() if row["event_type"] == event_type
        )
        assert payload["output_item_count"] == 2
        assert payload["non_tool_output_item_count"] == 1
        assert payload["output_item_types"] == ["reasoning", "function_call"]
        assert payload["output_shape_hash"].startswith("sha256:")
        assert payload["continuation_ref"]["order_hash"].startswith("sha256:")
    decision = next(
        row["payload"]
        for row in journal.events()
        if row["event_type"] == "turn_decision_recorded"
    )
    recorded_call = decision["tool_calls"][0]
    assert "turn_decision" not in recorded_call["arguments"]
    assert recorded_call["turn_decision"] == PublicTurnDecision(
        mode="stop",
        basis="Only an explicit stop fits the current horizon.",
        evidence_goal=None,
    ).model_dump(
        mode="json"
    )


def test_resume_rejects_tampered_reasoning_before_tool_or_provider_call(
    tmp_path,
    monkeypatch,
) -> None:
    calls = {"execute": 0}

    class OneStopAdapter:
        def __init__(self, config, *, api_key) -> None:
            del config, api_key

        def request_payload(self, context, tools, *, system_prompt):
            return {"context": context, "tools": tools, "system": system_prompt}

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            del request
            assert timeout_seconds > 0
            return 100

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            del request
            assert timeout_seconds > 0
            calls["execute"] += 1
            return ModelTurn(
                tool_calls=[
                    ProviderRequestedTool(
                        name="stop_task",
                        action_id="tamper-stop",
                        arguments={
                            "reason_code": "insufficient_public_evidence",
                            "summary": "Stop after the integrity test.",
                            "evidence_span_ids": [],
                            "turn_decision": PublicTurnDecision(
                                mode="stop",
                                basis="The integrity test uses one bounded action.",
                            ).model_dump(mode="json"),
                        },
                    )
                ],
                requested_input_tokens=requested_input_tokens,
                input_tokens=requested_input_tokens,
                output_tokens=2,
                reasoning_output_tokens=1,
                response_id="response-tamper",
                response_status="completed",
                output_item_count=2,
                non_tool_output_item_count=1,
                output_item_types=("reasoning", "function_call"),
                output_shape_hash=sha256_json(
                    {
                        "item_count": 2,
                        "item_types": ("reasoning", "function_call"),
                    }
                ),
                provider_continuation=(
                    ProviderReasoningItem(
                        id="reasoning-tamper",
                        encrypted_content="encrypted-tamper",
                        status="completed",
                    ),
                    ProviderFunctionCallRef(action_id="tamper-stop"),
                ),
            )

    _patch_live_boundaries(monkeypatch)
    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", OneStopAdapter)
    _crash_journal_once(
        monkeypatch,
        event_type="provider_call_finished",
        when="after",
    )
    request = _live_request(tmp_path, repeat=1, cap="0.10").model_copy(
        update={"limits": DevLimits(max_model_calls=1)}
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)
    journal = DevJournal(request.state_root, run_id)
    provider = next(
        row["payload"]
        for row in journal.events()
        if row["event_type"] == "provider_call_finished"
    )
    continuation_path = Path(provider["continuation_ref"]["artifact"]["path"])
    continuation_path.write_text("tampered", encoding="utf-8")

    resumed = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    run = resumed["runs"][0]

    assert run["terminal"] == "PROVIDER_CONTINUATION_ERROR"
    assert run["call_counts"] == {"model": 1, "input_count": 1, "tool": 0}
    assert calls["execute"] == 1
    assert not any(
        row["event_type"] == "tool_batch_started" for row in journal.events()
    )


def test_unfinished_provider_dispatch_with_orphan_continuation_is_unknown(
    tmp_path,
    monkeypatch,
) -> None:
    calls = {"adapter": 0, "preflight": 0, "execute": 0}

    class ReasoningAdapter:
        def __init__(self, config, *, api_key) -> None:
            del config, api_key
            calls["adapter"] += 1

        def request_payload(self, context, tools, *, system_prompt):
            return {"context": context, "tools": tools, "system": system_prompt}

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            del request
            assert timeout_seconds > 0
            return 100

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            del request
            assert timeout_seconds > 0
            calls["execute"] += 1
            return ModelTurn(
                requested_input_tokens=requested_input_tokens,
                input_tokens=requested_input_tokens,
                output_tokens=5,
                reasoning_output_tokens=5,
                response_id="response-orphan-continuation",
                response_status="incomplete",
                response_incomplete_reason="max_output_tokens",
                error=ModelTurnError(
                    "incomplete_response",
                    "provider response was incomplete: max_output_tokens",
                ),
                output_item_count=1,
                non_tool_output_item_count=1,
                output_item_types=("reasoning",),
                output_shape_hash=sha256_json(
                    {"item_count": 1, "item_types": ("reasoning",)}
                ),
                provider_continuation=(
                    ProviderReasoningItem(
                        id="reasoning-orphan",
                        encrypted_content="encrypted-orphan",
                        status="incomplete",
                    ),
                ),
            )

    def preflight(package):
        del package
        calls["preflight"] += 1
        return LocalSandbox()

    monkeypatch.setattr(runner, "_live_source_preflight", lambda task_dir, package: None)
    monkeypatch.setattr(runner, "_live_sandbox_preflight", preflight)
    monkeypatch.setattr(runner, "WorkspaceManager", _SnapshotWorkspaceManager)
    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", ReasoningAdapter)
    _crash_journal_once(
        monkeypatch,
        event_type="provider_call_finished",
        when="before",
    )
    request = _live_request(tmp_path, repeat=1, cap="0.10").model_copy(
        update={"limits": DevLimits(max_model_calls=1)}
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)
    object_files = [
        path
        for path in (request.state_root / "artifacts" / "objects" / "sha256").rglob("*")
        if path.is_file()
    ]
    assert any(b"encrypted-orphan" in path.read_bytes() for path in object_files)

    resumed = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
    assert resumed["runs"][0]["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert resumed["runs"][0]["call_counts"] == {
        "model": 1,
        "input_count": 1,
        "tool": 0,
    }
    assert calls == {"adapter": 1, "preflight": 1, "execute": 1}
    journal = DevJournal(request.state_root, run_id)
    assert len([row for row in journal.events() if row["event_type"] == "terminal"]) == 1


def test_provider_timeout_stops_remaining_repetitions(tmp_path, monkeypatch) -> None:
    calls = {"create": 0}
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    class TimeoutAdapter:
        def __init__(self, config, *, api_key) -> None:
            del config
            assert api_key == "test-only-sentinel"
            assert "OPENAI_API_KEY" not in os.environ

        def request_payload(self, context, tools, *, system_prompt):
            return {"context": context, "tools": tools, "system": system_prompt}

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            del request
            assert timeout_seconds > 0
            return 100

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            del request, requested_input_tokens
            assert timeout_seconds > 0
            calls["create"] += 1
            raise TimeoutError("ambiguous provider timeout")

    _patch_live_boundaries(monkeypatch)
    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", TimeoutAdapter)
    result = runner.run_dev(_live_request(tmp_path))
    assert result["completed_repetitions"] == 1
    assert result["runs"][0]["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert calls["create"] == 1


def test_count_timeout_and_cost_cap_stop_without_generation(tmp_path, monkeypatch) -> None:
    class CountTimeoutAdapter:
        execute_calls = 0

        def __init__(self, config, *, api_key) -> None:
            del config, api_key

        def request_payload(self, context, tools, *, system_prompt):
            return {"context": context, "tools": tools, "system": system_prompt}

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            del request
            assert timeout_seconds > 0
            raise TimeoutError("count timeout")

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            del request, requested_input_tokens, timeout_seconds
            self.execute_calls += 1

    _patch_live_boundaries(monkeypatch)
    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", CountTimeoutAdapter)
    timed_out = runner.run_dev(_live_request(tmp_path / "count"))
    assert timed_out["completed_repetitions"] == 1
    assert timed_out["runs"][0]["terminal"] == "COUNT_TIMEOUT_OR_UNKNOWN"

    class TooExpensiveAdapter(CountTimeoutAdapter):
        create_calls = 0

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            del request
            assert timeout_seconds > 0
            return 1_000_000

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            del request, requested_input_tokens, timeout_seconds
            self.create_calls += 1
            raise AssertionError("generation must not be dispatched")

    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", TooExpensiveAdapter)
    capped = runner.run_dev(_live_request(tmp_path / "cap", cap="0.0001"))
    assert capped["runs"][0]["terminal"] == "COST_CAP_REACHED"
