from __future__ import annotations

import copy
import inspect
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.agent.context import BuiltContext
from patchloop.agent.context_event_shadow import (
    LeanHarnessCompactedShadowRequestEvidence,
    project_lean_harness_compacted_shadow_request,
)
from patchloop.agent.finalization import r8_public_development_finalization_reserve
from patchloop.agent.model import SYSTEM_PROMPT_V3, OpenAIResponsesAdapter
from patchloop.agent.phases import EvidenceState
from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.contracts import Artifact, Budget, ModelConfig, Usage
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

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
        raise AssertionError("compacted shadow must not execute a provider request")


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


def _artifact(identity: str, content: bytes) -> Artifact:
    return Artifact(
        artifact_id=f"art_{identity}",
        content_hash=sha256_bytes(content),
        media_type="application/json; charset=utf-8",
        size_bytes=len(content),
        path=f"objects/{identity}.json",
        created_at=datetime(2026, 8, 16, tzinfo=UTC),
    )


def _context(*, descriptors: bool = True) -> BuiltContext:
    input_artifact = _artifact("input", b'{"path":"parser.py"}')
    result_artifact = _artifact("result", b'{"content":"public source"}')
    call_payload: dict[str, Any] = {
        "tool": "read_file",
        "artifact_id": input_artifact.artifact_id,
        "artifact_path": input_artifact.path,
        "arguments": {"path": "parser.py"},
    }
    result_payload: dict[str, Any] = {
        "tool": "read_file",
        "status": "succeeded",
        "artifact_id": result_artifact.artifact_id,
        "artifact_path": result_artifact.path,
        "tool_result": {"path": "parser.py", "content": "public source"},
    }
    if descriptors:
        call_payload["input_artifact"] = input_artifact.model_dump(mode="json")
        result_payload["result_artifact"] = result_artifact.model_dump(mode="json")
    payload = {
        "public_task": {"task_id": "public-event-shadow"},
        "phase_contract": {"allowed_next_actions": ["read_file", "apply_patch"]},
        "recent_events": [
            {
                "run_id": "run_public",
                "sequence": 1,
                "type": "ToolCalled",
                "timestamp": "2026-08-16T00:00:00Z",
                "actor": "agent",
                "payload": call_payload,
            },
            {
                "run_id": "run_public",
                "sequence": 2,
                "type": "ToolSucceeded",
                "timestamp": "2026-08-16T00:00:01Z",
                "actor": "tool-gateway",
                "payload": result_payload,
            },
        ],
        "selected_memory": None,
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    return BuiltContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence={
            "schema_version": "context-build-evidence-v11",
            "rendered_characters": len(rendered),
            "rendered_bytes": len(rendered.encode("utf-8")),
        },
    )


def _phase() -> EvidenceState:
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
        allowed_next_actions=("read_file", "apply_patch"),
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
    context: BuiltContext | None = None,
    output_tokens: int = 0,
) -> tuple[LeanHarnessCompactedShadowRequestEvidence, _IsolatedClient]:
    adapter, client = _adapter()
    projected = project_lean_harness_compacted_shadow_request(
        reserve=r8_public_development_finalization_reserve(),
        adapter=adapter,
        built_context=context or _context(),
        system_prompt=SYSTEM_PROMPT_V3,
        tool_schemas=TOOL_SCHEMAS_V2,
        phase_evidence=_phase(),
        usage=Usage(output_tokens=output_tokens),
        budget=_budget(),
        isolated_client_attested=True,
    )
    return projected, client


def _rehash(body: dict[str, Any]) -> dict[str, Any]:
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def test_compacted_shadow_rebuilds_same_phase_surface_and_reduces_requests() -> None:
    projected, client = _project()

    assert projected.context_compaction.removed_descriptor_count == 2
    assert projected.phase_tool_surface_unchanged is True
    assert projected.request_mode_class_unchanged is True
    assert projected.request_ready_unchanged is True
    assert projected.baseline_shadow.phase_request.tool_names == (
        "read_file",
        "apply_patch",
    )
    assert projected.compacted_shadow.phase_request.tool_names == (
        "read_file",
        "apply_patch",
    )
    assert projected.source_request_body_bytes_saved > 0
    assert projected.phase_request_body_bytes_saved > 0
    assert projected.phase_counted_input_tokens_saved > 0
    assert len(client.responses.input_tokens.payloads) == 2
    assert client.responses.create_calls == 0
    assert projected.provider_calls_authorized is False
    assert projected.runtime_activation_authorized is False
    assert projected.request_persistence_authorized is False


def test_no_descriptor_shadow_is_an_exact_noop() -> None:
    projected, client = _project(context=_context(descriptors=False))

    assert projected.context_compaction.removed_descriptor_count == 0
    assert projected.source_request_body_bytes_saved == 0
    assert projected.phase_request_body_bytes_saved == 0
    assert projected.phase_counted_input_tokens_saved == 0
    assert projected.baseline_shadow.source_request.request_body_hash == (
        projected.compacted_shadow.source_request.request_body_hash
    )
    assert len(client.responses.input_tokens.payloads) == 2
    assert client.responses.create_calls == 0


def test_finalization_shadow_keeps_mode_tools_and_output_allowance() -> None:
    projected, client = _project(output_tokens=50_001)

    assert projected.baseline_shadow.request_mode.mode == "finalization"
    assert projected.compacted_shadow.request_mode.mode == "finalization"
    assert projected.finalization_candidate_body_bytes_saved is not None
    assert projected.finalization_candidate_body_bytes_saved > 0
    assert projected.final_request_body_bytes_saved is not None
    assert projected.final_request_body_bytes_saved > 0
    assert projected.baseline_shadow.final_request is not None
    assert projected.compacted_shadow.final_request is not None
    assert projected.baseline_shadow.final_request.max_output_tokens == 5_000
    assert projected.compacted_shadow.final_request.max_output_tokens == 5_000
    assert len(client.responses.input_tokens.payloads) == 6
    assert client.responses.create_calls == 0


def test_rehashed_context_or_authority_drift_is_rejected() -> None:
    projected, _ = _project()
    context = projected.model_dump(mode="python")
    context["compacted_context_hash"] = "sha256:" + "f" * 64
    with pytest.raises(ValidationError, match="context binding differs"):
        LeanHarnessCompactedShadowRequestEvidence.model_validate(_rehash(context))

    authority = projected.model_dump(mode="python")
    authority["provider_calls_authorized"] = True
    with pytest.raises(ValidationError):
        LeanHarnessCompactedShadowRequestEvidence.model_validate(_rehash(authority))


def test_compacted_shadow_is_condition_neutral_and_runner_closed() -> None:
    signature = inspect.signature(project_lean_harness_compacted_shadow_request)
    runner = (REPOSITORY / "patchloop/agent/runner.py").read_text(encoding="utf-8")

    assert "condition" not in signature.parameters
    assert "execute_request" not in inspect.getsource(project_lean_harness_compacted_shadow_request)
    assert "project_lean_harness_compacted_shadow_request" not in runner
    assert "patchloop.agent.shadow_runtime" not in runner
