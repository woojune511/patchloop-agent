"""Versioned no-call shadow for reversible recent-event compaction.

This composition layer leaves both the v1 request shadow and the descriptor
projector independently source-qualified.  It compares their direct and
compacted request surfaces with an isolated counter, and grants no runner,
provider, persistence or state authority.
"""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.context import BuiltContext
from patchloop.agent.context_event_compaction import (
    LeanContextEventCompactionEvidence,
    project_lean_context_event_descriptors,
    restore_lean_context_event_descriptors,
)
from patchloop.agent.finalization import FinalizationReserveContract
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.agent.phases import EvidenceState
from patchloop.agent.shadow_runtime import (
    LeanHarnessShadowRequestEvidence,
    ShadowRequestStage,
    project_lean_harness_shadow_request,
)
from patchloop.contracts import Budget, Usage
from patchloop.util import sha256_json

COMPACTED_SHADOW_REQUEST_EVIDENCE_SCHEMA = "lean-harness-compacted-shadow-request-evidence-v2"


class LeanHarnessCompactedShadowRequestEvidence(BaseModel):
    """Versioned no-call comparison of direct and compacted requests."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-compacted-shadow-request-evidence-v2"]
    status: Literal["isolated-client-compacted-shadow-runtime-closed"]
    source_built_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    compacted_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    context_compaction: LeanContextEventCompactionEvidence
    baseline_shadow: LeanHarnessShadowRequestEvidence
    compacted_shadow: LeanHarnessShadowRequestEvidence
    phase_tool_surface_unchanged: Literal[True]
    request_mode_class_unchanged: Literal[True]
    request_ready_unchanged: Literal[True]
    source_request_body_bytes_saved: int = Field(ge=0)
    phase_request_body_bytes_saved: int = Field(ge=0)
    finalization_candidate_body_bytes_saved: int | None = Field(default=None, ge=0)
    final_request_body_bytes_saved: int | None = Field(default=None, ge=0)
    phase_counted_input_tokens_saved: int = Field(ge=0)
    exact_source_roundtrip: Literal[True]
    condition_specific_policy_authorized: Literal[False]
    provider_transport_calls: Literal[0]
    provider_calls_authorized: Literal[False]
    runtime_activation_authorized: Literal[False]
    request_persistence_authorized: Literal[False]
    state_mutation_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_compacted_shadow(self) -> Self:
        compaction = self.context_compaction
        baseline = self.baseline_shadow
        compacted = self.compacted_shadow
        if (
            self.source_built_context_hash != compaction.source_context_hash
            or self.compacted_context_hash != compaction.projected_context_hash
            or baseline.built_context_hash != self.source_built_context_hash
            or compacted.built_context_hash != self.compacted_context_hash
        ):
            raise ValueError("compacted shadow context binding differs")
        if (
            baseline.reserve_contract_hash != compacted.reserve_contract_hash
            or baseline.phase_tool_surface != compacted.phase_tool_surface
        ):
            raise ValueError("compacted shadow phase tool surface differs")
        if baseline.request_mode.mode != compacted.request_mode.mode:
            raise ValueError("compacted shadow request mode class differs")
        if baseline.request_ready is not compacted.request_ready:
            raise ValueError("compacted shadow request readiness differs")
        if (
            baseline.request_mode.configured_max_output_tokens
            != compacted.request_mode.configured_max_output_tokens
            or baseline.request_mode.input_tokens_used != compacted.request_mode.input_tokens_used
            or baseline.request_mode.output_tokens_used != compacted.request_mode.output_tokens_used
            or baseline.request_mode.max_cumulative_input_tokens
            != compacted.request_mode.max_cumulative_input_tokens
            or baseline.request_mode.max_cumulative_output_tokens
            != compacted.request_mode.max_cumulative_output_tokens
            or baseline.request_mode.max_total_tokens != compacted.request_mode.max_total_tokens
        ):
            raise ValueError("compacted shadow request budget differs")
        for baseline_stage, compacted_stage in (
            (baseline.source_request, compacted.source_request),
            (baseline.phase_request, compacted.phase_request),
        ):
            if (
                baseline_stage.stage != compacted_stage.stage
                or baseline_stage.system_prompt_hash != compacted_stage.system_prompt_hash
                or baseline_stage.tool_schema_hash != compacted_stage.tool_schema_hash
                or baseline_stage.tool_names != compacted_stage.tool_names
                or baseline_stage.model_id != compacted_stage.model_id
                or baseline_stage.service_tier != compacted_stage.service_tier
                or baseline_stage.reasoning_hash != compacted_stage.reasoning_hash
                or baseline_stage.max_output_tokens != compacted_stage.max_output_tokens
            ):
                raise ValueError("compacted shadow request identity differs")
        expected_source_saved = (
            baseline.source_request.request_body_bytes - compacted.source_request.request_body_bytes
        )
        expected_phase_saved = (
            baseline.phase_request.request_body_bytes - compacted.phase_request.request_body_bytes
        )
        baseline_count = baseline.phase_request.counted_input_tokens
        compacted_count = compacted.phase_request.counted_input_tokens
        if baseline_count is None or compacted_count is None:
            raise ValueError("compacted shadow phase count is absent")
        if (
            self.source_request_body_bytes_saved != expected_source_saved
            or self.phase_request_body_bytes_saved != expected_phase_saved
            or self.phase_counted_input_tokens_saved != baseline_count - compacted_count
        ):
            raise ValueError("compacted shadow request savings differ")
        optional_stage_pairs = (
            (
                baseline.finalization_candidate_request,
                compacted.finalization_candidate_request,
                self.finalization_candidate_body_bytes_saved,
            ),
            (
                baseline.final_request,
                compacted.final_request,
                self.final_request_body_bytes_saved,
            ),
        )
        for baseline_stage, compacted_stage, recorded_saved in optional_stage_pairs:
            _validate_optional_stage_pair(
                baseline_stage,
                compacted_stage,
                recorded_saved,
            )
        if compaction.removed_descriptor_count:
            if (
                self.source_request_body_bytes_saved <= 0
                or self.phase_request_body_bytes_saved <= 0
                or self.phase_counted_input_tokens_saved <= 0
            ):
                raise ValueError("compacted shadow did not reduce each request surface")
        elif any(
            value != 0
            for value in (
                self.source_request_body_bytes_saved,
                self.phase_request_body_bytes_saved,
                self.phase_counted_input_tokens_saved,
            )
        ):
            raise ValueError("compacted shadow noop savings differ")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("compacted shadow evidence content hash differs")
        return self


def _validate_optional_stage_pair(
    baseline: ShadowRequestStage | None,
    compacted: ShadowRequestStage | None,
    recorded_saved: int | None,
) -> None:
    if (baseline is None) is not (compacted is None):
        raise ValueError("compacted shadow optional stage differs")
    if baseline is None:
        if recorded_saved is not None:
            raise ValueError("compacted shadow absent stage has savings")
        return
    assert compacted is not None
    if (
        baseline.stage != compacted.stage
        or baseline.tool_schema_hash != compacted.tool_schema_hash
        or baseline.tool_names != compacted.tool_names
        or baseline.max_output_tokens != compacted.max_output_tokens
        or recorded_saved != baseline.request_body_bytes - compacted.request_body_bytes
    ):
        raise ValueError("compacted shadow optional stage identity differs")


def _optional_stage_bytes_saved(
    baseline: ShadowRequestStage | None,
    compacted: ShadowRequestStage | None,
) -> int | None:
    if baseline is None and compacted is None:
        return None
    if baseline is None or compacted is None:
        raise ValueError("compacted shadow optional stage differs")
    return baseline.request_body_bytes - compacted.request_body_bytes


def project_lean_harness_compacted_shadow_request(
    *,
    reserve: FinalizationReserveContract,
    adapter: OpenAIResponsesAdapter,
    built_context: BuiltContext,
    system_prompt: str,
    tool_schemas: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    phase_evidence: EvidenceState,
    usage: Usage,
    budget: Budget,
    isolated_client_attested: Literal[True],
) -> LeanHarnessCompactedShadowRequestEvidence:
    """Compare direct and descriptor-compacted requests without activation."""

    compacted_context = project_lean_context_event_descriptors(built_context)
    if restore_lean_context_event_descriptors(compacted_context) != built_context.rendered:
        raise ValueError("compacted shadow does not restore its source")
    projected_context = BuiltContext(
        rendered=compacted_context.rendered,
        content_hash=compacted_context.content_hash,
        evidence={
            "schema_version": (compacted_context.evidence.source_context_schema_version),
            "rendered_characters": len(compacted_context.rendered),
            "rendered_bytes": len(compacted_context.rendered.encode("utf-8")),
        },
    )
    common = {
        "reserve": reserve,
        "adapter": adapter,
        "system_prompt": system_prompt,
        "tool_schemas": tool_schemas,
        "phase_evidence": phase_evidence,
        "usage": usage,
        "budget": budget,
        "isolated_client_attested": isolated_client_attested,
    }
    baseline = project_lean_harness_shadow_request(
        built_context=built_context,
        **common,
    )
    compacted = project_lean_harness_shadow_request(
        built_context=projected_context,
        **common,
    )
    baseline_count = baseline.phase_request.counted_input_tokens
    compacted_count = compacted.phase_request.counted_input_tokens
    if baseline_count is None or compacted_count is None:
        raise ValueError("compacted shadow phase count is absent")
    body: dict[str, Any] = {
        "schema_version": COMPACTED_SHADOW_REQUEST_EVIDENCE_SCHEMA,
        "status": "isolated-client-compacted-shadow-runtime-closed",
        "source_built_context_hash": built_context.content_hash,
        "compacted_context_hash": compacted_context.content_hash,
        "context_compaction": compacted_context.evidence.model_dump(mode="python"),
        "baseline_shadow": baseline.model_dump(mode="python"),
        "compacted_shadow": compacted.model_dump(mode="python"),
        "phase_tool_surface_unchanged": (
            baseline.phase_tool_surface == compacted.phase_tool_surface
        ),
        "request_mode_class_unchanged": (baseline.request_mode.mode == compacted.request_mode.mode),
        "request_ready_unchanged": (baseline.request_ready is compacted.request_ready),
        "source_request_body_bytes_saved": (
            baseline.source_request.request_body_bytes - compacted.source_request.request_body_bytes
        ),
        "phase_request_body_bytes_saved": (
            baseline.phase_request.request_body_bytes - compacted.phase_request.request_body_bytes
        ),
        "finalization_candidate_body_bytes_saved": _optional_stage_bytes_saved(
            baseline.finalization_candidate_request,
            compacted.finalization_candidate_request,
        ),
        "final_request_body_bytes_saved": _optional_stage_bytes_saved(
            baseline.final_request,
            compacted.final_request,
        ),
        "phase_counted_input_tokens_saved": baseline_count - compacted_count,
        "exact_source_roundtrip": True,
        "condition_specific_policy_authorized": False,
        "provider_transport_calls": 0,
        "provider_calls_authorized": False,
        "runtime_activation_authorized": False,
        "request_persistence_authorized": False,
        "state_mutation_authorized": False,
    }
    return LeanHarnessCompactedShadowRequestEvidence.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )
