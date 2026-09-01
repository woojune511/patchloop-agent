"""Request-local successor for exact pre-plan tools and bounded public context.

Lean V23's durable events, investigation ledger, and workflow state remain the
source of truth.  This module creates two request-only projections:

* remove ``run_check`` from an active pre-plan self-directed gate; and
* retain one usable copy of current public source evidence while replacing old
  recent-event payloads and duplicate investigation inventories with bounded
  references and summaries.

Neither projection mutates durable state or grants provider authority.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.completion_loop_successor import ProjectedEditCorrectionContext
from patchloop.agent.workflow_self_directed_exploration_successor import (
    SelfDirectedExplorationState,
    WorkflowDecisionV4,
)
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json, sha256_text

EXACT_PRE_PLAN_SURFACE_POLICY = "exact-self-directed-pre-plan-surface-v1"
BOUNDED_REQUEST_CONTEXT_POLICY = "bounded-public-investigation-request-context-v1"
BOUNDED_LEDGER_SCHEMA = "bounded-investigation-ledger-projection-v1"
BOUNDED_EVENT_REFERENCE_SCHEMA = "bounded-public-event-reference-v1"
BOUNDED_REQUEST_CONTEXT_SCHEMA = "bounded-investigation-request-context-evidence-v1"
EXACT_PRE_PLAN_SURFACE_SCHEMA = "exact-pre-plan-surface-projection-evidence-v1"

_FOUNDATION_TOOLS = frozenset({"read_file", "run_check", "get_diff"})
# One exact outcome is enough because the self-directed state already carries
# three bounded question-target-result cards.  Older call/outcome identities
# remain sequence/hash references, while read/check/diff foundations stay exact.
_RECENT_EVENT_TAIL = 1
_RECENT_RESULT_SUMMARIES = 2
_TOKEN_OBSERVATION_TAIL = 3
_READ_COVERAGE_TAIL = 8


class ExactPrePlanSurfaceProjectionEvidence(BaseModel):
    """Identity of the V23 decision and its request-local exact surface."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["exact-pre-plan-surface-projection-evidence-v1"]
    policy_version: Literal["exact-self-directed-pre-plan-surface-v1"]
    source_decision_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_decision_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    self_directed_state_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_allowed_tool_names: tuple[str, ...]
    projected_allowed_tool_names: tuple[str, ...]
    active_pre_plan_gate: bool
    run_check_removed: bool
    other_tool_names_changed: Literal[False]
    durable_state_changed: Literal[False]
    provider_authority_granted: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        expected = tuple(
            name
            for name in self.source_allowed_tool_names
            if not (self.active_pre_plan_gate and name == "run_check")
        )
        if (
            self.projected_allowed_tool_names != expected
            or self.run_check_removed
            is not (self.active_pre_plan_gate and "run_check" in self.source_allowed_tool_names)
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("exact pre-plan surface projection differs")
        return self


@dataclass(frozen=True)
class ExactPrePlanSurfaceProjection:
    decision: WorkflowDecisionV4
    evidence: ExactPrePlanSurfaceProjectionEvidence


class BoundedRecentEventProjection(BaseModel):
    """One exact or reference-only model-visible event projection."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    event_index: int = Field(ge=0)
    event_sequence: int = Field(ge=1)
    source_event_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_event_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    disposition: Literal[
        "exact_tail",
        "exact_foundation",
        "exact_plan_feedback",
        "exact_compact_not_beneficial",
        "reference",
    ]
    source_payload_bytes: int = Field(ge=1)
    projected_payload_bytes: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_event(self) -> Self:
        if self.disposition == "reference":
            if self.projected_payload_bytes >= self.source_payload_bytes:
                raise ValueError("bounded event reference does not reduce its payload")
        elif self.projected_event_hash != self.source_event_hash:
            raise ValueError("exact bounded event changed")
        return self


class BoundedInvestigationRequestContextEvidence(BaseModel):
    """Exact binding between full public context and its model-only projection."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["bounded-investigation-request-context-evidence-v1"]
    policy_version: Literal["bounded-public-investigation-request-context-v1"]
    source_correction_context_evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_context_bytes: int = Field(ge=1)
    projected_context_bytes: int = Field(ge=1)
    context_bytes_saved: int = Field(ge=0)
    source_recent_events_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_recent_events_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_investigation_ledger_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_investigation_ledger_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    event_projections: tuple[BoundedRecentEventProjection, ...]
    exact_event_count: int = Field(ge=0)
    reference_event_count: int = Field(ge=0)
    source_detail_count: int = Field(ge=0)
    retained_detail_count: int = Field(ge=0, le=3)
    omitted_detail_count: int = Field(ge=0)
    source_search_inventory_count: int = Field(ge=0)
    retained_search_inventory_count: Literal[0]
    omitted_search_inventory_count: int = Field(ge=0)
    source_read_coverage_count: int = Field(ge=0)
    retained_read_coverage_count: int = Field(ge=0, le=8)
    omitted_read_coverage_count: int = Field(ge=0)
    source_token_observation_count: int = Field(ge=0)
    retained_token_observation_count: int = Field(ge=0, le=3)
    omitted_token_observation_count: int = Field(ge=0)
    source_read_body_count: int = Field(ge=0)
    retained_usable_source_body_count: int = Field(ge=0)
    duplicate_source_outcome_count: Literal[0]
    bounded_result_summary_count: int = Field(ge=0, le=2)
    durable_event_changed: Literal[False]
    durable_ledger_changed: Literal[False]
    durable_result_artifact_changed: Literal[False]
    model_facing_projection_only: Literal[True]
    raw_reasoning_included: Literal[False]
    private_or_hidden_material_included: Literal[False]
    reference_patch_included: Literal[False]
    provider_authority_granted: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        dispositions = [item.disposition for item in self.event_projections]
        if (
            self.context_bytes_saved != self.source_context_bytes - self.projected_context_bytes
            or self.exact_event_count != sum(item != "reference" for item in dispositions)
            or self.reference_event_count != dispositions.count("reference")
            or len(self.event_projections) != self.exact_event_count + self.reference_event_count
            or self.omitted_detail_count != self.source_detail_count - self.retained_detail_count
            or self.omitted_search_inventory_count != self.source_search_inventory_count
            or self.omitted_read_coverage_count
            != self.source_read_coverage_count - self.retained_read_coverage_count
            or self.omitted_token_observation_count
            != self.source_token_observation_count - self.retained_token_observation_count
            or (self.source_read_body_count > 0 and self.retained_usable_source_body_count < 1)
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("bounded investigation context projection differs")
        return self


@dataclass(frozen=True)
class BoundedInvestigationRequestContext:
    rendered: str
    content_hash: str
    evidence: BoundedInvestigationRequestContextEvidence


def _canonical_bytes(value: Any) -> int:
    return len(canonical_json(value).encode("utf-8"))


def project_exact_pre_plan_surface(
    *,
    source_decision: WorkflowDecisionV4,
    state: SelfDirectedExplorationState | None,
) -> ExactPrePlanSurfaceProjection:
    """Remove only pre-plan ``run_check`` from one V23 core decision."""

    if type(source_decision) is not WorkflowDecisionV4:
        raise TypeError("exact pre-plan surface requires an exact V23 decision")
    if state is not None and type(state) is not SelfDirectedExplorationState:
        raise TypeError("exact pre-plan surface requires exact self-directed state")
    active = bool(state is not None and state.active_plan_hash is None)
    source_names = source_decision.allowed_tool_names
    projected_names = tuple(name for name in source_names if not (active and name == "run_check"))
    body = source_decision.model_dump(mode="python", exclude={"content_hash"})
    body["allowed_tool_names"] = projected_names
    if active and "run_check" in source_names:
        body["expected_check_id"] = None
    projected = WorkflowDecisionV4.model_validate({**body, "content_hash": sha256_json(body)})
    evidence_body = {
        "schema_version": EXACT_PRE_PLAN_SURFACE_SCHEMA,
        "policy_version": EXACT_PRE_PLAN_SURFACE_POLICY,
        "source_decision_hash": source_decision.content_hash,
        "projected_decision_hash": projected.content_hash,
        "self_directed_state_hash": (
            state.content_hash if state is not None else sha256_json(None)
        ),
        "source_allowed_tool_names": source_names,
        "projected_allowed_tool_names": projected_names,
        "active_pre_plan_gate": active,
        "run_check_removed": active and "run_check" in source_names,
        "other_tool_names_changed": False,
        "durable_state_changed": False,
        "provider_authority_granted": False,
    }
    evidence = ExactPrePlanSurfaceProjectionEvidence.model_validate(
        {**evidence_body, "content_hash": sha256_json(evidence_body)}
    )
    return ExactPrePlanSurfaceProjection(decision=projected, evidence=evidence)


def _is_plan_feedback(event: dict[str, Any]) -> bool:
    payload = event.get("payload")
    return bool(
        event.get("type") == "ToolFailed"
        and isinstance(payload, dict)
        and payload.get("tool") in {"record_work_plan", "revise_work_plan"}
        and payload.get("error_code") == "WORK_PLAN_ADMISSION_REJECTED"
    )


def _is_foundation(event: dict[str, Any]) -> bool:
    payload = event.get("payload")
    return bool(
        event.get("type") in {"ToolSucceeded", "ToolReplayed"}
        and isinstance(payload, dict)
        and payload.get("tool") in _FOUNDATION_TOOLS
    )


def _read_body_count(events: list[dict[str, Any]]) -> int:
    count = 0
    for event in events:
        payload = event.get("payload")
        result = payload.get("tool_result") if isinstance(payload, dict) else None
        if (
            isinstance(payload, dict)
            and payload.get("tool") == "read_file"
            and isinstance(result, dict)
            and isinstance(result.get("content"), str)
        ):
            count += 1
    return count


def _bounded_event_reference(event: dict[str, Any]) -> dict[str, Any]:
    payload = event["payload"]
    reference = {
        "tool": payload.get("tool"),
        "projection_ref": {
            "schema_version": BOUNDED_EVENT_REFERENCE_SCHEMA,
            "source_event_hash": sha256_json(event),
            "source_payload_hash": sha256_json(payload),
            "source_payload_bytes": _canonical_bytes(payload),
        },
    }
    return {
        "sequence": event["sequence"],
        "type": event["type"],
        "actor": event["actor"],
        "payload": reference,
    }


def project_bounded_investigation_request_context(
    source: ProjectedEditCorrectionContext,
) -> BoundedInvestigationRequestContext:
    """Project one correction context without changing its durable sources."""

    if type(source) is not ProjectedEditCorrectionContext:
        raise TypeError("bounded investigation context requires exact correction context")
    if source.content_hash != sha256_text(source.rendered):
        raise ContractError("bounded investigation source context hash differs")
    try:
        payload = json.loads(source.rendered)
    except json.JSONDecodeError as exc:
        raise ContractError("bounded investigation source context is not JSON") from exc
    if not isinstance(payload, dict):
        raise ContractError("bounded investigation source context must be an object")
    recent = payload.get("recent_events")
    ledger = payload.get("investigation_ledger")
    if not isinstance(recent, list) or not isinstance(ledger, dict):
        raise ContractError("bounded investigation source inventory differs")
    if any(
        not isinstance(event, dict)
        or type(event.get("sequence")) is not int
        or not isinstance(event.get("type"), str)
        or not isinstance(event.get("actor"), str)
        or not isinstance(event.get("payload"), dict)
        for event in recent
    ):
        raise ContractError("bounded investigation recent-event shape differs")
    ledger_hash = ledger.get("content_hash")
    if not isinstance(ledger_hash, str) or ledger_hash != sha256_json(
        {key: item for key, item in ledger.items() if key != "content_hash"}
    ):
        raise ContractError("bounded investigation source ledger hash differs")
    details = ledger.get("recent_details")
    searches = ledger.get("searches")
    reads = ledger.get("reads")
    omitted = ledger.get("omitted")
    observations = ledger.get("tail_policy", {}).get("token_projection", {}).get("observations")
    if not (
        isinstance(details, list)
        and isinstance(searches, list)
        and isinstance(reads, list)
        and isinstance(omitted, dict)
        and isinstance(observations, list)
        and all(
            type(omitted.get(key)) is int and omitted[key] >= 0
            for key in ("searches", "read_files", "details")
        )
    ):
        raise ContractError("bounded investigation ledger projection source differs")

    projected = copy.deepcopy(payload)
    projected_recent: list[dict[str, Any]] = []
    event_records: list[dict[str, Any]] = []
    tail_start = max(0, len(recent) - _RECENT_EVENT_TAIL)
    exact_read_outcomes: set[int] = set()
    for index, event in enumerate(recent):
        if index >= tail_start:
            disposition = "exact_tail"
        elif _is_foundation(event):
            disposition = "exact_foundation"
        elif _is_plan_feedback(event):
            disposition = "exact_plan_feedback"
        else:
            disposition = "reference"
        projected_event = copy.deepcopy(event)
        if disposition == "reference":
            candidate_reference = _bounded_event_reference(event)
            if _canonical_bytes(candidate_reference["payload"]) < _canonical_bytes(
                event["payload"]
            ):
                projected_event = candidate_reference
            else:
                disposition = "exact_compact_not_beneficial"
        if (
            disposition != "reference"
            and event["payload"].get("tool") == "read_file"
            and event["type"] in {"ToolSucceeded", "ToolReplayed"}
        ):
            exact_read_outcomes.add(event["sequence"])
        projected_recent.append(projected_event)
        event_records.append(
            {
                "event_index": index,
                "event_sequence": event["sequence"],
                "source_event_hash": sha256_json(event),
                "projected_event_hash": sha256_json(projected_event),
                "disposition": disposition,
                "source_payload_bytes": _canonical_bytes(event["payload"]),
                "projected_payload_bytes": _canonical_bytes(projected_event["payload"]),
            }
        )
    projected["recent_events"] = projected_recent

    read_details = [
        item
        for item in details
        if isinstance(item, dict)
        and item.get("tool") == "read_file"
        and item.get("source_outcome_sequence") not in exact_read_outcomes
    ]
    result_details = [
        item for item in details if isinstance(item, dict) and item.get("tool") != "read_file"
    ]
    retained_details = [*read_details[-1:], *result_details[-_RECENT_RESULT_SUMMARIES:]]
    retained_details.sort(key=lambda item: int(item.get("source_outcome_sequence", 0)))
    projected_ledger = copy.deepcopy(ledger)
    projected_ledger["schema_version"] = BOUNDED_LEDGER_SCHEMA
    projected_ledger["policy_version"] = BOUNDED_REQUEST_CONTEXT_POLICY
    projected_ledger["source_ledger_schema_version"] = ledger.get("schema_version")
    projected_ledger["source_ledger_policy_version"] = ledger.get("policy_version")
    projected_ledger["source_ledger_content_hash"] = ledger_hash
    projected_ledger["source_ledger_canonical_bytes"] = _canonical_bytes(ledger)
    projected_ledger["searches"] = []
    projected_ledger["reads"] = copy.deepcopy(reads[-_READ_COVERAGE_TAIL:])
    projected_ledger["recent_details"] = copy.deepcopy(retained_details)
    projected_ledger["omitted"] = {
        "searches": omitted["searches"] + len(searches),
        "read_files": omitted["read_files"] + max(0, len(reads) - _READ_COVERAGE_TAIL),
        "details": omitted["details"] + len(details) - len(retained_details),
    }
    token_projection = projected_ledger["tail_policy"]["token_projection"]
    token_projection["observations"] = copy.deepcopy(observations[-_TOKEN_OBSERVATION_TAIL:])
    token_projection["omitted_observation_count"] = max(
        0, len(observations) - _TOKEN_OBSERVATION_TAIL
    )
    projected_ledger["projection"] = {
        "schema_version": BOUNDED_REQUEST_CONTEXT_SCHEMA,
        "policy_version": BOUNDED_REQUEST_CONTEXT_POLICY,
        "durable_source_chain_hash": ledger_hash,
        "recent_event_source_hash": sha256_json(recent),
        "full_search_inventory_removed": True,
        "retained_result_summary_count": len(result_details[-_RECENT_RESULT_SUMMARIES:]),
        "durable_state_changed": False,
    }
    projected_ledger["content_hash"] = sha256_json(
        {key: item for key, item in projected_ledger.items() if key != "content_hash"}
    )
    projected["investigation_ledger"] = projected_ledger
    rendered = canonical_json(projected)

    source_read_body_count = sum(
        isinstance(item, dict)
        and item.get("tool") == "read_file"
        and isinstance(item.get("content"), str)
        for item in details
    )
    retained_ledger_read_bodies = sum(
        item.get("tool") == "read_file" and isinstance(item.get("content"), str)
        for item in retained_details
    )
    retained_source_bodies = _read_body_count(projected_recent) + retained_ledger_read_bodies
    body = {
        "schema_version": BOUNDED_REQUEST_CONTEXT_SCHEMA,
        "policy_version": BOUNDED_REQUEST_CONTEXT_POLICY,
        "source_correction_context_evidence_hash": source.evidence.content_hash,
        "source_context_hash": source.content_hash,
        "projected_context_hash": sha256_text(rendered),
        "source_context_bytes": len(source.rendered.encode("utf-8")),
        "projected_context_bytes": len(rendered.encode("utf-8")),
        "context_bytes_saved": len(source.rendered.encode("utf-8")) - len(rendered.encode("utf-8")),
        "source_recent_events_hash": sha256_json(recent),
        "projected_recent_events_hash": sha256_json(projected_recent),
        "source_investigation_ledger_hash": ledger_hash,
        "projected_investigation_ledger_hash": projected_ledger["content_hash"],
        "event_projections": tuple(event_records),
        "exact_event_count": sum(item["disposition"] != "reference" for item in event_records),
        "reference_event_count": sum(item["disposition"] == "reference" for item in event_records),
        "source_detail_count": len(details),
        "retained_detail_count": len(retained_details),
        "omitted_detail_count": len(details) - len(retained_details),
        "source_search_inventory_count": len(searches),
        "retained_search_inventory_count": 0,
        "omitted_search_inventory_count": len(searches),
        "source_read_coverage_count": len(reads),
        "retained_read_coverage_count": min(len(reads), _READ_COVERAGE_TAIL),
        "omitted_read_coverage_count": max(0, len(reads) - _READ_COVERAGE_TAIL),
        "source_token_observation_count": len(observations),
        "retained_token_observation_count": min(len(observations), _TOKEN_OBSERVATION_TAIL),
        "omitted_token_observation_count": max(0, len(observations) - _TOKEN_OBSERVATION_TAIL),
        "source_read_body_count": source_read_body_count,
        "retained_usable_source_body_count": retained_source_bodies,
        "duplicate_source_outcome_count": 0,
        "bounded_result_summary_count": len(result_details[-_RECENT_RESULT_SUMMARIES:]),
        "durable_event_changed": False,
        "durable_ledger_changed": False,
        "durable_result_artifact_changed": False,
        "model_facing_projection_only": True,
        "raw_reasoning_included": False,
        "private_or_hidden_material_included": False,
        "reference_patch_included": False,
        "provider_authority_granted": False,
    }
    if body["context_bytes_saved"] < 0:
        raise ContractError("bounded investigation projection expands its source")
    evidence = BoundedInvestigationRequestContextEvidence.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )
    return BoundedInvestigationRequestContext(
        rendered=rendered,
        content_hash=evidence.projected_context_hash,
        evidence=evidence,
    )


def bind_bounded_request_instruction(
    instruction: dict[str, Any],
    *,
    surface: ExactPrePlanSurfaceProjectionEvidence,
    context: BoundedInvestigationRequestContextEvidence,
) -> dict[str, Any]:
    """Bind both request-only projections into the visible workflow instruction."""

    if not isinstance(instruction, dict) or instruction.get("content_hash") != sha256_json(
        {key: item for key, item in instruction.items() if key != "content_hash"}
    ):
        raise ContractError("bounded request instruction source differs")
    body = {
        **{
            key: copy.deepcopy(value) for key, value in instruction.items() if key != "content_hash"
        },
        "exact_pre_plan_surface_policy_version": EXACT_PRE_PLAN_SURFACE_POLICY,
        "exact_pre_plan_surface_projection_hash": surface.content_hash,
        "bounded_investigation_context_policy_version": BOUNDED_REQUEST_CONTEXT_POLICY,
        "bounded_investigation_context_projection_hash": context.content_hash,
    }
    return {**body, "content_hash": sha256_json(body)}


__all__ = [
    "BOUNDED_REQUEST_CONTEXT_POLICY",
    "BoundedInvestigationRequestContext",
    "BoundedInvestigationRequestContextEvidence",
    "EXACT_PRE_PLAN_SURFACE_POLICY",
    "ExactPrePlanSurfaceProjection",
    "ExactPrePlanSurfaceProjectionEvidence",
    "bind_bounded_request_instruction",
    "project_bounded_investigation_request_context",
    "project_exact_pre_plan_surface",
]
