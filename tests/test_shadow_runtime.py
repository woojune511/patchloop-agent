from __future__ import annotations

import copy
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.agent.context import BuiltContext
from patchloop.agent.finalization import r8_public_development_finalization_reserve
from patchloop.agent.model import SYSTEM_PROMPT_V3, OpenAIResponsesAdapter
from patchloop.agent.phases import EvidenceState
from patchloop.agent.shadow_runtime import (
    LeanHarnessShadowRequestEvidence,
    project_lean_harness_shadow_request,
)
from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.contracts import Budget, ModelConfig, Usage
from patchloop.util import canonical_json, sha256_json, sha256_text

REPOSITORY = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class _CountResult:
    input_tokens: int


class _InputTokenCounter:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []

    def count(self, **payload: Any) -> _CountResult:
        snapshot = copy.deepcopy(payload)
        self.payloads.append(snapshot)
        return _CountResult(input_tokens=400 + len(canonical_json(snapshot).encode("utf-8")))


class _Responses:
    def __init__(self) -> None:
        self.input_tokens = _InputTokenCounter()
        self.create_calls = 0

    def create(self, **request: Any) -> None:
        del request
        self.create_calls += 1
        raise AssertionError("shadow runtime must not execute a provider request")


class _IsolatedClient:
    max_retries = 0

    def __init__(self) -> None:
        self.responses = _Responses()


def _adapter() -> tuple[OpenAIResponsesAdapter, _IsolatedClient]:
    client = _IsolatedClient()
    adapter = OpenAIResponsesAdapter(
        ModelConfig(
            provider="openai",
            model_id="gpt-5.4-mini-2026-03-17",
            reasoning_effort="medium",
            service_tier="default",
            transport_max_retries=0,
            max_output_tokens=25_000,
        ),
        client=client,  # type: ignore[arg-type]
    )
    return adapter, client


def _context() -> BuiltContext:
    rendered = canonical_json(
        {
            "task": {"task_id": "public-development-shadow"},
            "phase_contract": {"allowed_next_actions": ["read_file"]},
        }
    )
    return BuiltContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence={"source": "public-development-synthetic"},
    )


def _phase(actions: tuple[str, ...]) -> EvidenceState:
    return EvidenceState(
        worktree_diff_hash="sha256:" + "1" * 64,
        mutation_event_sequence=1,
        mutation_present=True,
        completed_checks=(),
        pending_checks=("public-check",),
        current_diff_check_event_sequences=(),
        latest_check_sequence=None,
        review_event_sequence=None,
        review_presented_to_model=False,
        task_review_event_sequence=None,
        task_review_presented_to_model=False,
        task_review_coverage_complete=None,
        unresolved_coverage_target_ids=(),
        submission_ready=False,
        missing_evidence=("public-check",),
        allowed_next_actions=actions,
    )


def _budget() -> Budget:
    return Budget(
        max_model_calls=240,
        max_tool_calls=400,
        max_total_tokens=1_100_000,
        wall_clock_timeout_seconds=3_600,
        token_budget_schema_version="cumulative-split-v1",
        max_cumulative_input_tokens=1_000_000,
        max_cumulative_output_tokens=100_000,
    )


def _project(
    *,
    actions: tuple[str, ...] = (
        "search_files",
        "read_file",
        "apply_patch",
        "run_check",
        "get_diff",
        "finish_task",
    ),
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> tuple[LeanHarnessShadowRequestEvidence, _IsolatedClient]:
    adapter, client = _adapter()
    projected = project_lean_harness_shadow_request(
        reserve=r8_public_development_finalization_reserve(),
        adapter=adapter,
        built_context=_context(),
        system_prompt=SYSTEM_PROMPT_V3,
        tool_schemas=TOOL_SCHEMAS_V2,
        phase_evidence=_phase(actions),
        usage=Usage(input_tokens=input_tokens, output_tokens=output_tokens),
        budget=_budget(),
        isolated_client_attested=True,
    )
    return projected, client


def _rehash(body: dict[str, Any]) -> dict[str, Any]:
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def test_exploration_shadow_reuses_real_payload_and_count_paths_without_generation() -> None:
    projected, client = _project()
    adapter, _ = _adapter()
    expected_source = adapter.request_payload(
        _context().rendered,
        copy.deepcopy(TOOL_SCHEMAS_V2),
        system_prompt=SYSTEM_PROMPT_V3,
    )

    assert projected.request_mode.mode == "exploration"
    assert projected.source_request.request_body_hash == sha256_text(
        canonical_json(expected_source)
    )
    assert projected.phase_request.tool_names == tuple(item["name"] for item in TOOL_SCHEMAS_V2)
    assert projected.final_request == projected.phase_request
    assert projected.request_ready is True
    assert projected.adapter_payload_build_count == 2
    assert projected.offline_input_token_count_calls == 1
    assert len(client.responses.input_tokens.payloads) == 1
    assert client.responses.create_calls == 0
    assert projected.provider_transport_calls == 0
    assert projected.provider_calls_authorized is False
    assert projected.runtime_activation_authorized is False
    assert projected.request_persistence_authorized is False
    assert projected.state_mutation_authorized is False


def test_phase_filter_rebuilds_and_recounts_the_actual_request_surface() -> None:
    projected, client = _project(actions=("read_file", "apply_patch"))

    assert projected.request_mode.mode == "exploration"
    assert projected.source_request.tool_names == tuple(item["name"] for item in TOOL_SCHEMAS_V2)
    assert projected.phase_request.tool_names == ("read_file", "apply_patch")
    assert projected.phase_tool_surface.removed_tool_names == (
        "search_files",
        "run_check",
        "get_diff",
        "finish_task",
    )
    assert projected.source_request.request_body_hash != (projected.phase_request.request_body_hash)
    assert tuple(item["name"] for item in client.responses.input_tokens.payloads[0]["tools"]) == (
        "read_file",
        "apply_patch",
    )
    assert client.responses.create_calls == 0


def test_finalization_shadow_rebuilds_filters_recounts_and_caps_output() -> None:
    projected, client = _project(output_tokens=50_001)

    assert projected.request_mode.mode == "finalization"
    assert projected.finalization_tool_surface is not None
    assert projected.finalization_candidate_request is not None
    assert projected.finalization_request_evidence is not None
    assert projected.final_request is not None
    assert projected.finalization_tool_surface.selected_tool_names == (
        "read_file",
        "apply_patch",
        "run_check",
        "get_diff",
        "finish_task",
    )
    assert projected.finalization_candidate_request.max_output_tokens == 25_000
    assert projected.finalization_request_evidence.allowance.decision == "admit_full"
    assert projected.final_request.max_output_tokens == 5_000
    assert projected.final_request.counted_input_tokens == (
        projected.finalization_candidate_request.counted_input_tokens
    )
    assert projected.final_request.token_count_payload_hash == (
        projected.finalization_candidate_request.token_count_payload_hash
    )
    assert projected.request_ready is True
    assert projected.adapter_payload_build_count == 3
    assert projected.offline_input_token_count_calls == 3
    assert [
        tuple(item["name"] for item in payload["tools"])
        for payload in client.responses.input_tokens.payloads
    ] == [
        tuple(item["name"] for item in TOOL_SCHEMAS_V2),
        ("read_file", "apply_patch", "run_check", "get_diff", "finish_task"),
        ("read_file", "apply_patch", "run_check", "get_diff", "finish_task"),
    ]
    assert client.responses.create_calls == 0


def test_finalization_shadow_uses_exact_residual_output_allowance() -> None:
    projected, _ = _project(output_tokens=98_000)

    assert projected.request_mode.mode == "finalization"
    assert projected.finalization_request_evidence is not None
    assert projected.finalization_request_evidence.allowance.decision == "admit_reduced"
    assert projected.finalization_request_evidence.allowance.effective_max_output_tokens == 2_000
    assert projected.final_request is not None
    assert projected.final_request.max_output_tokens == 2_000


def test_exhausted_split_budget_blocks_without_exposing_a_request() -> None:
    projected, client = _project(output_tokens=100_000)

    assert projected.request_mode.mode == "block"
    assert projected.finalization_tool_surface is None
    assert projected.finalization_candidate_request is None
    assert projected.finalization_request_evidence is None
    assert projected.final_request is None
    assert projected.request_ready is False
    assert projected.offline_input_token_count_calls == 1
    assert client.responses.create_calls == 0


def test_finalization_recount_can_block_without_constructing_a_final_request() -> None:
    projected, client = _project(input_tokens=999_500)

    assert projected.request_mode.mode == "finalization"
    assert projected.finalization_request_evidence is not None
    assert projected.finalization_request_evidence.allowance.decision == "block"
    assert projected.final_request is None
    assert projected.request_ready is False
    assert projected.adapter_payload_build_count == 3
    assert projected.offline_input_token_count_calls == 2
    assert client.responses.create_calls == 0


def test_shadow_rejects_context_drift_non_split_budget_and_missing_attestation() -> None:
    adapter, _ = _adapter()
    context = _context()
    drifted = BuiltContext(
        rendered=context.rendered + " ",
        content_hash=context.content_hash,
        evidence=context.evidence,
    )
    arguments = {
        "reserve": r8_public_development_finalization_reserve(),
        "adapter": adapter,
        "built_context": drifted,
        "system_prompt": SYSTEM_PROMPT_V3,
        "tool_schemas": TOOL_SCHEMAS_V2,
        "phase_evidence": _phase(("read_file",)),
        "usage": Usage(),
        "budget": _budget(),
        "isolated_client_attested": True,
    }

    with pytest.raises(ValueError, match="context hash differs"):
        project_lean_harness_shadow_request(**arguments)

    arguments["built_context"] = context
    arguments["budget"] = Budget(max_total_tokens=80_000)
    with pytest.raises(ValueError, match="cumulative-split-v1"):
        project_lean_harness_shadow_request(**arguments)

    arguments["budget"] = _budget()
    arguments["isolated_client_attested"] = False
    with pytest.raises(ValueError, match="isolated client attestation"):
        project_lean_harness_shadow_request(**arguments)  # type: ignore[arg-type]


def test_rehashed_nested_authority_or_output_drift_is_rejected() -> None:
    projected, _ = _project(output_tokens=98_000)
    body = projected.model_dump(mode="python")
    assert body["final_request"] is not None
    body["final_request"]["max_output_tokens"] = 2_001
    body["final_request"] = _rehash(body["final_request"])
    body = _rehash(body)

    with pytest.raises(ValidationError, match="final request output differs"):
        LeanHarnessShadowRequestEvidence.model_validate(body)

    authority = projected.model_dump(mode="python")
    authority["provider_calls_authorized"] = True
    authority = _rehash(authority)
    with pytest.raises(ValidationError):
        LeanHarnessShadowRequestEvidence.model_validate(authority)


def test_shadow_surface_is_condition_neutral_and_not_activated_by_runner() -> None:
    signature = inspect.signature(project_lean_harness_shadow_request)
    runner_source = (REPOSITORY / "patchloop/agent/runner.py").read_text(encoding="utf-8")
    function_source = inspect.getsource(project_lean_harness_shadow_request)

    assert "condition" not in signature.parameters
    assert "execute_request" not in function_source
    assert "next_turn" not in function_source
    assert "patchloop.agent.shadow_runtime" not in runner_source
    assert "project_lean_harness_shadow_request" not in runner_source
