"""No-call shadow projection for a future lean request path.

The projector reuses the production Responses request builder and token-count
method with a caller-attested isolated client.  It never executes a model
request, persists evidence, mutates run state, or activates the runner.  Its
only purpose is to close the offline producer/consumer seam between the
phase-evidence filter and the finalization allowance before public-development
qualification.
"""

from __future__ import annotations

import copy
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.context import BuiltContext
from patchloop.agent.finalization import (
    FinalizationRequestEvidence,
    FinalizationRequestMode,
    FinalizationReserveContract,
    PhaseToolSurfaceProjection,
    project_finalization_request_mode,
    project_phase_tool_surface,
    project_recounted_finalization_request,
)
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.agent.phases import EvidenceState
from patchloop.contracts import Budget, Usage
from patchloop.util import canonical_json, sha256_json, sha256_text

SHADOW_REQUEST_STAGE_SCHEMA = "lean-harness-shadow-request-stage-v1"
SHADOW_REQUEST_EVIDENCE_SCHEMA = "lean-harness-shadow-request-evidence-v1"

ShadowStageName = Literal[
    "source",
    "phase-filtered",
    "finalization-candidate",
    "final",
]


class ShadowRequestStage(BaseModel):
    """Sanitized identity for one request body built by the real adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-shadow-request-stage-v1"]
    stage: ShadowStageName
    context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    system_prompt_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    tool_names: tuple[str, ...]
    model_id: str = Field(min_length=1)
    service_tier: str = Field(min_length=1)
    reasoning_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    max_output_tokens: int = Field(ge=1)
    request_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    request_body_bytes: int = Field(ge=1)
    token_count_payload_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    token_count_payload_bytes: int = Field(ge=1)
    counted_input_tokens: int | None = Field(default=None, ge=0)
    offline_input_token_counted: bool
    request_persisted: Literal[False]
    provider_generation_called: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_stage(self) -> Self:
        if len(set(self.tool_names)) != len(self.tool_names):
            raise ValueError("shadow request tool names must be unique")
        if self.offline_input_token_counted is not (self.counted_input_tokens is not None):
            raise ValueError("shadow count flag differs from counted tokens")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("shadow request stage content hash differs")
        return self


class LeanHarnessShadowRequestEvidence(BaseModel):
    """Closed shadow result; no nested value confers runtime authority."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-shadow-request-evidence-v1"]
    status: Literal["isolated-client-shadow-runtime-closed"]
    reserve_contract_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    reserve_contract: FinalizationReserveContract
    built_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_request: ShadowRequestStage
    phase_tool_surface: PhaseToolSurfaceProjection
    phase_request: ShadowRequestStage
    request_mode: FinalizationRequestMode
    finalization_tool_surface: PhaseToolSurfaceProjection | None
    finalization_candidate_request: ShadowRequestStage | None
    finalization_request_evidence: FinalizationRequestEvidence | None
    final_request: ShadowRequestStage | None
    request_ready: bool
    adapter_payload_build_count: int = Field(ge=1)
    offline_input_token_count_calls: int = Field(ge=0)
    counter_transport: Literal["caller-attested-isolated-client"]
    provider_transport_calls: Literal[0]
    provider_calls_authorized: Literal[False]
    runtime_activation_authorized: Literal[False]
    request_persistence_authorized: Literal[False]
    state_mutation_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        if self.reserve_contract_hash != self.reserve_contract.content_hash:
            raise ValueError("shadow reserve contract hash differs")
        if self.built_context_hash != self.source_request.context_hash:
            raise ValueError("shadow source request context differs")
        if self.phase_request.context_hash != self.built_context_hash:
            raise ValueError("shadow phase request context differs")
        if self.source_request.stage != "source":
            raise ValueError("shadow source request stage differs")
        if self.source_request.counted_input_tokens is not None:
            raise ValueError("shadow source request must remain uncounted")
        if self.source_request.tool_schema_hash != (
            self.phase_tool_surface.source_tool_schema_hash
        ):
            raise ValueError("shadow source tools differ from phase projection")
        if self.phase_request.stage != "phase-filtered":
            raise ValueError("shadow phase request stage differs")
        if self.phase_request.tool_schema_hash != (
            self.phase_tool_surface.selected_tool_schema_hash
        ):
            raise ValueError("shadow phase tools differ from phase request")
        if self.phase_request.counted_input_tokens != (self.request_mode.requested_input_tokens):
            raise ValueError("shadow phase recount differs from request mode")
        if self.phase_request.max_output_tokens != (self.request_mode.configured_max_output_tokens):
            raise ValueError("shadow configured output differs from request mode")
        if self.request_mode.reserve_contract_hash != self.reserve_contract_hash:
            raise ValueError("shadow request mode reserve differs")

        common_stages = tuple(
            item
            for item in (
                self.phase_request,
                self.finalization_candidate_request,
                self.final_request,
            )
            if item is not None
        )
        if any(
            item.context_hash != self.built_context_hash
            or item.system_prompt_hash != self.source_request.system_prompt_hash
            or item.model_id != self.source_request.model_id
            or item.service_tier != self.source_request.service_tier
            or item.reasoning_hash != self.source_request.reasoning_hash
            for item in common_stages
        ):
            raise ValueError("shadow request identity changes across rebuilds")

        if self.request_mode.mode in {"exploration", "block"}:
            if any(
                item is not None
                for item in (
                    self.finalization_tool_surface,
                    self.finalization_candidate_request,
                    self.finalization_request_evidence,
                )
            ):
                raise ValueError("non-finalization shadow has finalization evidence")
            expected_final = self.phase_request if self.request_mode.mode == "exploration" else None
            if self.final_request != expected_final:
                raise ValueError("non-finalization final request differs")
            expected_ready = self.request_mode.mode == "exploration"
            if self.request_ready is not expected_ready:
                raise ValueError("non-finalization request readiness differs")
            if (
                self.adapter_payload_build_count,
                self.offline_input_token_count_calls,
            ) != (2, 1):
                raise ValueError("non-finalization shadow call counts differ")
        else:
            surface = self.finalization_tool_surface
            candidate = self.finalization_candidate_request
            evidence = self.finalization_request_evidence
            if surface is None or candidate is None or evidence is None:
                raise ValueError("finalization shadow evidence is incomplete")
            if surface.mode != "finalization":
                raise ValueError("shadow finalization surface mode differs")
            if candidate.stage != "finalization-candidate":
                raise ValueError("shadow finalization candidate stage differs")
            if candidate.tool_schema_hash != surface.selected_tool_schema_hash:
                raise ValueError("shadow finalization candidate tools differ")
            if candidate.counted_input_tokens != evidence.recounted_input_tokens:
                raise ValueError("shadow finalization recount differs")
            if evidence.request_mode_hash != self.request_mode.content_hash:
                raise ValueError("shadow finalization mode binding differs")
            if evidence.tool_surface_hash != surface.content_hash:
                raise ValueError("shadow finalization surface binding differs")
            allowance = evidence.allowance
            if allowance.decision == "block":
                if self.final_request is not None or self.request_ready is not False:
                    raise ValueError("blocked finalization exposes a final request")
                expected_counts = (3, 2)
            else:
                final_request = self.final_request
                if final_request is None or final_request.stage != "final":
                    raise ValueError("admitted finalization lacks final request")
                if final_request.tool_schema_hash != surface.selected_tool_schema_hash:
                    raise ValueError("shadow final request tools differ")
                if final_request.max_output_tokens != (allowance.effective_max_output_tokens):
                    raise ValueError("shadow final request output differs")
                if final_request.counted_input_tokens != evidence.recounted_input_tokens:
                    raise ValueError("shadow final request recount differs")
                if final_request.token_count_payload_hash != (candidate.token_count_payload_hash):
                    raise ValueError("output-only rebuild changed count payload")
                if self.request_ready is not True:
                    raise ValueError("admitted finalization is not request-ready")
                expected_counts = (3, 3)
            if (
                self.adapter_payload_build_count,
                self.offline_input_token_count_calls,
            ) != expected_counts:
                raise ValueError("finalization shadow call counts differ")

        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("shadow request evidence content hash differs")
        return self


def _hashed(model_type: type[BaseModel], body: dict[str, Any]) -> Any:
    return model_type.model_validate({**body, "content_hash": sha256_json(body)})


def _tool_names(tool_schemas: list[dict[str, Any]]) -> tuple[str, ...]:
    names: list[str] = []
    for schema in tool_schemas:
        if type(schema) is not dict:
            raise TypeError("shadow tool schemas must be exact mappings")
        name = schema.get("name")
        if schema.get("type") != "function" or type(name) is not str or not name:
            raise ValueError("shadow tool schema identity is invalid")
        names.append(name)
    if len(set(names)) != len(names):
        raise ValueError("shadow tool schema names must be unique")
    return tuple(names)


def _stage(
    *,
    adapter: OpenAIResponsesAdapter,
    stage: ShadowStageName,
    request_body: dict[str, Any],
    context_hash: str,
    system_prompt_hash: str,
    counted_input_tokens: int | None,
) -> ShadowRequestStage:
    if type(request_body) is not dict:
        raise TypeError("shadow request body must be an exact mapping")
    tools = request_body.get("tools")
    if type(tools) is not list:
        raise ValueError("shadow request body tools must be an exact list")
    tool_names = _tool_names(tools)
    max_output_tokens = request_body.get("max_output_tokens")
    if type(max_output_tokens) is not int or max_output_tokens <= 0:
        raise ValueError("shadow request output limit must be a positive integer")
    if counted_input_tokens is not None and (
        type(counted_input_tokens) is not int or counted_input_tokens < 0
    ):
        raise TypeError("shadow counted input tokens must be an exact nonnegative integer")
    request_json = canonical_json(request_body)
    count_payload = adapter._token_count_payload(request_body)
    count_json = canonical_json(count_payload)
    body: dict[str, Any] = {
        "schema_version": SHADOW_REQUEST_STAGE_SCHEMA,
        "stage": stage,
        "context_hash": context_hash,
        "system_prompt_hash": system_prompt_hash,
        "tool_schema_hash": sha256_json(tools),
        "tool_names": tool_names,
        "model_id": request_body["model"],
        "service_tier": request_body["service_tier"],
        "reasoning_hash": sha256_json(request_body["reasoning"]),
        "max_output_tokens": max_output_tokens,
        "request_body_hash": sha256_text(request_json),
        "request_body_bytes": len(request_json.encode("utf-8")),
        "token_count_payload_hash": sha256_text(count_json),
        "token_count_payload_bytes": len(count_json.encode("utf-8")),
        "counted_input_tokens": counted_input_tokens,
        "offline_input_token_counted": counted_input_tokens is not None,
        "request_persisted": False,
        "provider_generation_called": False,
    }
    return _hashed(ShadowRequestStage, body)


def _count_input_tokens(
    adapter: OpenAIResponsesAdapter,
    request_body: dict[str, Any],
) -> int:
    counted = adapter.count_input_tokens(request_body)
    if type(counted) is not int or counted < 0:
        raise TypeError("isolated input counter returned an invalid token count")
    return counted


def project_lean_harness_shadow_request(
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
) -> LeanHarnessShadowRequestEvidence:
    """Project the future request seam without generation or persistence.

    ``adapter`` must use an injected isolated client.  The explicit attestation
    is intentionally not runtime authority; passing a live provider client is
    outside this function's contract and remains prohibited by repository
    policy.
    """

    if type(reserve) is not FinalizationReserveContract:
        raise TypeError("shadow reserve must be an exact finalization contract")
    if type(adapter) is not OpenAIResponsesAdapter:
        raise TypeError("shadow adapter must be an exact OpenAIResponsesAdapter")
    if type(built_context) is not BuiltContext:
        raise TypeError("shadow context must be an exact BuiltContext")
    if type(system_prompt) is not str:
        raise TypeError("shadow system prompt must be an exact string")
    if type(tool_schemas) not in {list, tuple}:
        raise TypeError("shadow tool schemas must be an exact list or tuple")
    if type(phase_evidence) is not EvidenceState:
        raise TypeError("shadow phase evidence must be an exact EvidenceState")
    if type(usage) is not Usage or type(budget) is not Budget:
        raise TypeError("shadow usage and budget must be exact contract models")
    if isolated_client_attested is not True:
        raise ValueError("shadow projection requires an isolated client attestation")
    if sha256_text(built_context.rendered) != built_context.content_hash:
        raise ValueError("shadow built context hash differs from rendered context")
    if (
        budget.token_budget_schema_version != "cumulative-split-v1"
        or budget.max_cumulative_input_tokens is None
        or budget.max_cumulative_output_tokens is None
    ):
        raise ValueError("shadow projection requires cumulative-split-v1 budget limits")

    source_tools = [copy.deepcopy(item) for item in tool_schemas]
    source_body = adapter.request_payload(
        built_context.rendered,
        source_tools,
        system_prompt=system_prompt,
    )
    context_hash = built_context.content_hash
    prompt_hash = sha256_text(system_prompt)
    source_stage = _stage(
        adapter=adapter,
        stage="source",
        request_body=source_body,
        context_hash=context_hash,
        system_prompt_hash=prompt_hash,
        counted_input_tokens=None,
    )

    phase_surface = project_phase_tool_surface(
        reserve=reserve,
        tool_schemas=source_tools,
        phase_evidence=phase_evidence,
        mode="exploration",
    )
    phase_body = adapter.request_payload(
        built_context.rendered,
        list(phase_surface.selected_tool_schemas),
        system_prompt=system_prompt,
    )
    phase_count = _count_input_tokens(adapter, phase_body)
    phase_stage = _stage(
        adapter=adapter,
        stage="phase-filtered",
        request_body=phase_body,
        context_hash=context_hash,
        system_prompt_hash=prompt_hash,
        counted_input_tokens=phase_count,
    )
    request_mode = project_finalization_request_mode(
        reserve=reserve,
        requested_input_tokens=phase_count,
        configured_max_output_tokens=adapter.config.max_output_tokens,
        input_tokens_used=usage.input_tokens,
        output_tokens_used=usage.output_tokens,
        max_cumulative_input_tokens=budget.max_cumulative_input_tokens,
        max_cumulative_output_tokens=budget.max_cumulative_output_tokens,
        max_total_tokens=budget.max_total_tokens,
    )

    finalization_surface: PhaseToolSurfaceProjection | None = None
    finalization_candidate: ShadowRequestStage | None = None
    finalization_evidence: FinalizationRequestEvidence | None = None
    final_stage: ShadowRequestStage | None = None
    request_ready = request_mode.mode == "exploration"
    payload_builds = 2
    count_calls = 1
    if request_mode.mode == "exploration":
        final_stage = phase_stage
    elif request_mode.mode == "finalization":
        finalization_surface = project_phase_tool_surface(
            reserve=reserve,
            tool_schemas=source_tools,
            phase_evidence=phase_evidence,
            mode="finalization",
        )
        candidate_body = adapter.request_payload(
            built_context.rendered,
            list(finalization_surface.selected_tool_schemas),
            system_prompt=system_prompt,
        )
        payload_builds += 1
        candidate_count = _count_input_tokens(adapter, candidate_body)
        count_calls += 1
        finalization_candidate = _stage(
            adapter=adapter,
            stage="finalization-candidate",
            request_body=candidate_body,
            context_hash=context_hash,
            system_prompt_hash=prompt_hash,
            counted_input_tokens=candidate_count,
        )
        finalization_evidence = project_recounted_finalization_request(
            reserve=reserve,
            request_mode=request_mode,
            tool_surface=finalization_surface,
            recounted_input_tokens=candidate_count,
        )
        allowance = finalization_evidence.allowance
        if allowance.decision != "block":
            final_body = copy.deepcopy(candidate_body)
            final_body["max_output_tokens"] = allowance.effective_max_output_tokens
            final_count = _count_input_tokens(adapter, final_body)
            count_calls += 1
            if final_count != candidate_count:
                raise ValueError("output-only rebuild changed the exact input count")
            final_stage = _stage(
                adapter=adapter,
                stage="final",
                request_body=final_body,
                context_hash=context_hash,
                system_prompt_hash=prompt_hash,
                counted_input_tokens=final_count,
            )
            request_ready = True

    body: dict[str, Any] = {
        "schema_version": SHADOW_REQUEST_EVIDENCE_SCHEMA,
        "status": "isolated-client-shadow-runtime-closed",
        "reserve_contract_hash": reserve.content_hash,
        "reserve_contract": reserve.model_dump(mode="python"),
        "built_context_hash": context_hash,
        "source_request": source_stage.model_dump(mode="python"),
        "phase_tool_surface": phase_surface.model_dump(mode="python"),
        "phase_request": phase_stage.model_dump(mode="python"),
        "request_mode": request_mode.model_dump(mode="python"),
        "finalization_tool_surface": (
            finalization_surface.model_dump(mode="python")
            if finalization_surface is not None
            else None
        ),
        "finalization_candidate_request": (
            finalization_candidate.model_dump(mode="python")
            if finalization_candidate is not None
            else None
        ),
        "finalization_request_evidence": (
            finalization_evidence.model_dump(mode="python")
            if finalization_evidence is not None
            else None
        ),
        "final_request": (
            final_stage.model_dump(mode="python") if final_stage is not None else None
        ),
        "request_ready": request_ready,
        "adapter_payload_build_count": payload_builds,
        "offline_input_token_count_calls": count_calls,
        "counter_transport": "caller-attested-isolated-client",
        "provider_transport_calls": 0,
        "provider_calls_authorized": False,
        "runtime_activation_authorized": False,
        "request_persistence_authorized": False,
        "state_mutation_authorized": False,
    }
    return _hashed(LeanHarnessShadowRequestEvidence, body)
