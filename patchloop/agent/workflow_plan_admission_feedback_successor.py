"""Bounded model-facing projection of durable work-plan admission feedback.

The durable ``ToolFailed`` event and its result artifact remain complete.  This
module only replaces repeated nested plan/catalog values in one request-local
``recent_events`` projection with hashes and canonical byte counts.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.context_event_compaction import (
    CompactedEventContext,
    validate_lean_context_event_compaction,
)
from patchloop.agent.workflow_causal_alternative_successor import (
    CAUSAL_ALTERNATIVE_POLICY,
)
from patchloop.agent.workflow_self_directed_exploration_successor import (
    SELF_DIRECTED_EXPLORATION_POLICY,
)
from patchloop.agent.workflow_successor_v2 import WORK_PLAN_ADMISSION_POLICY
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json, sha256_text

PLAN_ADMISSION_FEEDBACK_PROJECTION_POLICY = "bounded-plan-admission-feedback-v1"
PLAN_ADMISSION_FEEDBACK_PROJECTION_SCHEMA = "lean-plan-admission-feedback-projection-evidence-v1"
PROJECTED_FEEDBACK_SCHEMA = "bounded-work-plan-admission-feedback-v1"
SOURCE_FEEDBACK_SCHEMA = "work-plan-admission-feedback-v1"

_HASH_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
_REQUIRED_DETAIL_KEYS = frozenset(
    {
        "schema_version",
        "policy_version",
        "plan_gate_id",
        "attempt",
        "reason_codes",
        "eligible_catalog_hash",
        "eligible_plan_evidence_catalog",
        "activated_exploration_plan_request",
        "activated_exploration_plan_request_hash",
        "causal_plan_request_projection",
        "causal_plan_request_projection_hash",
        "semantic_progress_state",
        "required_prior_hypothesis_disposition",
        "worktree_diff_hash",
        "request_artifact_id",
        "request_body_hash",
        "execution",
        "guidance",
    }
)
_OPTIONAL_DETAIL_KEYS = frozenset(
    {
        "cross_reset_failure_trigger",
        "causal_mechanism_history",
    }
)
_OMITTED_DETAIL_KEYS = (
    "eligible_plan_evidence_catalog",
    "activated_exploration_plan_request",
    "causal_plan_request_projection",
    "semantic_progress_state",
    "cross_reset_failure_trigger",
    "causal_mechanism_history",
)
_CAUSAL_GUIDANCE = (
    "Retry once using only the exact cspan and support IDs in "
    "causal_plan_request_projection. Do not supply paths, ranges, roles, "
    "evidence bindings, observation status, or check order."
)


class OmittedPlanAdmissionDetail(BaseModel):
    """Hash-only descriptor for one value retained in durable state."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    field: Literal[
        "eligible_plan_evidence_catalog",
        "activated_exploration_plan_request",
        "causal_plan_request_projection",
        "semantic_progress_state",
        "cross_reset_failure_trigger",
        "causal_mechanism_history",
    ]
    value_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    canonical_bytes: int = Field(ge=1)


class BoundedWorkPlanAdmissionFeedback(BaseModel):
    """Exact model-facing replacement for one complete durable failure."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["bounded-work-plan-admission-feedback-v1"]
    projection_policy_version: Literal["bounded-plan-admission-feedback-v1"]
    source_schema_version: Literal["work-plan-admission-feedback-v1"]
    source_event_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_error_details_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    policy_version: Literal[
        "work-plan-admission-recovery-v1",
        "bounded-public-causal-alternative-gate-v1",
    ]
    plan_gate_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    attempt: Literal[1, 2]
    reason_codes: tuple[str, ...] = Field(min_length=1, max_length=8)
    eligible_catalog_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    activated_exploration_plan_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    causal_plan_request_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    required_prior_hypothesis_disposition: Literal["retained", "refined", "rejected"] | None
    worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    request_artifact_id: str = Field(min_length=1, max_length=200)
    request_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    execution: Literal["not_dispatched"]
    guidance: str = Field(min_length=1, max_length=500)
    omitted_details: tuple[OmittedPlanAdmissionDetail, ...] = Field(min_length=4)

    @model_validator(mode="after")
    def validate_feedback(self) -> Self:
        fields = {item.field for item in self.omitted_details}
        required = {
            "eligible_plan_evidence_catalog",
            "activated_exploration_plan_request",
            "causal_plan_request_projection",
            "semantic_progress_state",
        }
        cross = {"cross_reset_failure_trigger", "causal_mechanism_history"}
        if (
            len(fields) != len(self.omitted_details)
            or not required.issubset(fields)
            or bool(fields & cross) is not cross.issubset(fields)
            or len(set(self.reason_codes)) != len(self.reason_codes)
            or any(not 1 <= len(item) <= 100 for item in self.reason_codes)
        ):
            raise ValueError("bounded plan feedback descriptor contract differs")
        return self


class CompatibleBoundedWorkPlanAdmissionFeedback(BoundedWorkPlanAdmissionFeedback):
    """V25-only feedback envelope that also accepts self-directed admission."""

    policy_version: Literal[
        "work-plan-admission-recovery-v1",
        "bounded-public-causal-alternative-gate-v1",
        "bounded-self-directed-exploration-v1",
    ]


class PlanAdmissionFeedbackEventProjection(BaseModel):
    """Exact source/projected identity for one bounded feedback event."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    event_sequence: int = Field(ge=1)
    event_index: int = Field(ge=0)
    source_event_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_event_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_error_details_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_error_details_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_error_details_bytes: int = Field(ge=1)
    projected_error_details_bytes: int = Field(ge=1, le=4_096)
    omitted_details: tuple[OmittedPlanAdmissionDetail, ...] = Field(min_length=4)

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        fields = tuple(item.field for item in self.omitted_details)
        if len(set(fields)) != len(fields):
            raise ValueError("bounded plan feedback omitted fields repeat")
        if self.projected_error_details_bytes >= self.source_error_details_bytes:
            raise ValueError("bounded plan feedback does not reduce its details")
        return self


class PlanAdmissionFeedbackProjectionEvidence(BaseModel):
    """Request-local evidence for the model-only feedback projection."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-plan-admission-feedback-projection-evidence-v1"]
    policy_version: Literal["bounded-plan-admission-feedback-v1"]
    scope: Literal["single-model-request"]
    source_compaction_evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_context_bytes: int = Field(ge=1)
    projected_context_bytes: int = Field(ge=1)
    context_bytes_saved: int = Field(ge=0)
    source_recent_events_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_recent_events_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_event_count: int = Field(ge=0)
    event_projections: tuple[PlanAdmissionFeedbackEventProjection, ...]
    non_target_events_preserved: Literal[True]
    durable_event_changed: Literal[False]
    durable_result_artifact_changed: Literal[False]
    model_facing_projection_only: Literal[True]
    raw_reasoning_included: Literal[False]
    private_or_hidden_material_included: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        if self.context_bytes_saved != self.source_context_bytes - self.projected_context_bytes:
            raise ValueError("bounded plan feedback context savings differ")
        if self.projected_event_count != len(self.event_projections):
            raise ValueError("bounded plan feedback projection count differs")
        identities = {(item.event_sequence, item.event_index) for item in self.event_projections}
        if len(identities) != len(self.event_projections):
            raise ValueError("bounded plan feedback event identities repeat")
        if self.event_projections:
            if self.context_bytes_saved <= 0:
                raise ValueError("bounded plan feedback must reduce the request context")
        elif (
            self.context_bytes_saved != 0
            or self.source_context_hash != self.projected_context_hash
            or self.source_recent_events_hash != self.projected_recent_events_hash
        ):
            raise ValueError("empty bounded plan feedback must preserve context")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("bounded plan feedback evidence hash differs")
        return self


@dataclass(frozen=True)
class BoundedPlanAdmissionFeedbackContext:
    rendered: str
    content_hash: str
    evidence: PlanAdmissionFeedbackProjectionEvidence


def _canonical_bytes(value: Any) -> int:
    return len(canonical_json(value).encode("utf-8"))


def _content_hash(raw: Any, *, field: str) -> str:
    if not isinstance(raw, dict):
        raise ContractError(f"bounded plan feedback {field} must be an object")
    value = raw.get("content_hash")
    if not isinstance(value, str) or _HASH_PATTERN.fullmatch(value) is None:
        raise ContractError(f"bounded plan feedback {field} lacks a content hash")
    if value != sha256_json({key: item for key, item in raw.items() if key != "content_hash"}):
        raise ContractError(f"bounded plan feedback {field} content hash differs")
    return value


def _validate_source_details(
    details: dict[str, Any],
    *,
    accepted_policy_versions: frozenset[str],
) -> None:
    keys = set(details)
    if not _REQUIRED_DETAIL_KEYS.issubset(keys) or not keys.issubset(
        _REQUIRED_DETAIL_KEYS | _OPTIONAL_DETAIL_KEYS
    ):
        raise ContractError("bounded plan feedback source fields differ")
    cross_fields = {"cross_reset_failure_trigger", "causal_mechanism_history"}
    if bool(keys & cross_fields) is not cross_fields.issubset(keys):
        raise ContractError("bounded plan feedback cross-reset fields are incomplete")
    if (
        details.get("schema_version") != SOURCE_FEEDBACK_SCHEMA
        or details.get("policy_version") not in accepted_policy_versions
        or details.get("execution") != "not_dispatched"
        or details.get("attempt") not in {1, 2}
        or details.get("guidance") != _CAUSAL_GUIDANCE
    ):
        raise ContractError("bounded plan feedback source contract differs")
    for field in (
        "plan_gate_id",
        "eligible_catalog_hash",
        "activated_exploration_plan_request_hash",
        "causal_plan_request_projection_hash",
        "worktree_diff_hash",
        "request_body_hash",
    ):
        if (
            not isinstance(details.get(field), str)
            or _HASH_PATTERN.fullmatch(details[field]) is None
        ):
            raise ContractError(f"bounded plan feedback {field} differs")
    reason_codes = details.get("reason_codes")
    if (
        not isinstance(reason_codes, list)
        or not 1 <= len(reason_codes) <= 8
        or len(set(reason_codes)) != len(reason_codes)
        or any(not isinstance(item, str) or not 1 <= len(item) <= 100 for item in reason_codes)
    ):
        raise ContractError("bounded plan feedback reason codes differ")
    if (
        not isinstance(details.get("request_artifact_id"), str)
        or not details["request_artifact_id"]
    ):
        raise ContractError("bounded plan feedback request artifact differs")
    if details.get("required_prior_hypothesis_disposition") not in {
        None,
        "retained",
        "refined",
        "rejected",
    }:
        raise ContractError("bounded plan feedback prior disposition differs")
    if (
        _content_hash(
            details["eligible_plan_evidence_catalog"],
            field="eligible catalog",
        )
        != details["eligible_catalog_hash"]
        or _content_hash(
            details["activated_exploration_plan_request"],
            field="activated request",
        )
        != details["activated_exploration_plan_request_hash"]
        or _content_hash(
            details["causal_plan_request_projection"],
            field="causal request",
        )
        != details["causal_plan_request_projection_hash"]
    ):
        raise ContractError("bounded plan feedback nested binding differs")
    semantic = details.get("semantic_progress_state")
    if semantic is not None:
        _content_hash(semantic, field="semantic progress state")
    cross = details.get("cross_reset_failure_trigger")
    if cross is not None:
        _content_hash(cross, field="cross-reset trigger")
        history = details.get("causal_mechanism_history")
        if not isinstance(history, list) or any(not isinstance(item, dict) for item in history):
            raise ContractError("bounded plan feedback causal history differs")


def _project_details(
    details: dict[str, Any],
    *,
    source_event_hash: str,
    accepted_policy_versions: frozenset[str],
    compatible_self_directed: bool,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    _validate_source_details(
        details,
        accepted_policy_versions=accepted_policy_versions,
    )
    omitted = tuple(
        {
            "field": field,
            "value_hash": sha256_json(details[field]),
            "canonical_bytes": _canonical_bytes(details[field]),
        }
        for field in _OMITTED_DETAIL_KEYS
        if field in details
    )
    projected = {
        "schema_version": PROJECTED_FEEDBACK_SCHEMA,
        "projection_policy_version": PLAN_ADMISSION_FEEDBACK_PROJECTION_POLICY,
        "source_schema_version": details["schema_version"],
        "source_event_hash": source_event_hash,
        "source_error_details_hash": sha256_json(details),
        **{
            key: copy.deepcopy(value)
            for key, value in details.items()
            if key not in _OMITTED_DETAIL_KEYS and key != "schema_version"
        },
        "omitted_details": omitted,
    }
    feedback_model = (
        CompatibleBoundedWorkPlanAdmissionFeedback
        if compatible_self_directed
        else BoundedWorkPlanAdmissionFeedback
    )
    projected = feedback_model.model_validate_json(canonical_json(projected)).model_dump(
        mode="json"
    )
    if _canonical_bytes(projected) > 4_096:
        raise ContractError("bounded plan feedback projection exceeds its byte ceiling")
    return projected, omitted


def _project_bounded_plan_admission_feedback(
    compacted: CompactedEventContext,
    *,
    accepted_policy_versions: frozenset[str],
    compatible_self_directed: bool,
) -> BoundedPlanAdmissionFeedbackContext:
    """Project repeated plan feedback without mutating its durable source."""

    if type(compacted) is not CompactedEventContext:
        raise TypeError("bounded plan feedback requires an exact compacted context")
    validate_lean_context_event_compaction(compacted)
    try:
        source = json.loads(compacted.rendered)
    except json.JSONDecodeError as exc:
        raise ContractError("bounded plan feedback context is not JSON") from exc
    if not isinstance(source, dict) or not isinstance(source.get("recent_events"), list):
        raise ContractError("bounded plan feedback context shape differs")
    projected = copy.deepcopy(source)
    source_recent = source["recent_events"]
    projected_recent = projected["recent_events"]
    records: list[dict[str, Any]] = []
    for event_index, event in enumerate(projected_recent):
        if not isinstance(event, dict) or not isinstance(event.get("payload"), dict):
            raise ContractError("bounded plan feedback event shape differs")
        payload = event["payload"]
        if not (
            event.get("type") == "ToolFailed"
            and payload.get("tool") == "record_work_plan"
            and payload.get("error_code") == "WORK_PLAN_ADMISSION_REJECTED"
        ):
            continue
        if (
            event.get("actor") != "tool-gateway"
            or payload.get("status") != "rejected"
            or payload.get("admission_blocked") is not True
            or not isinstance(event.get("sequence"), int)
        ):
            raise ContractError("bounded plan feedback event contract differs")
        details = payload.get("error_details")
        if not isinstance(details, dict):
            raise ContractError("bounded plan feedback lacks typed error details")
        source_event_hash = sha256_json(event)
        source_details_hash = sha256_json(details)
        projected_details, omitted = _project_details(
            details,
            source_event_hash=source_event_hash,
            accepted_policy_versions=accepted_policy_versions,
            compatible_self_directed=compatible_self_directed,
        )
        payload["error_details"] = projected_details
        records.append(
            {
                "event_sequence": event["sequence"],
                "event_index": event_index,
                "source_event_hash": source_event_hash,
                "projected_event_hash": sha256_json(event),
                "source_error_details_hash": source_details_hash,
                "projected_error_details_hash": sha256_json(projected_details),
                "source_error_details_bytes": _canonical_bytes(details),
                "projected_error_details_bytes": _canonical_bytes(projected_details),
                "omitted_details": omitted,
            }
        )
    rendered = json.dumps(projected, indent=2, ensure_ascii=False, default=str)
    body = {
        "schema_version": PLAN_ADMISSION_FEEDBACK_PROJECTION_SCHEMA,
        "policy_version": PLAN_ADMISSION_FEEDBACK_PROJECTION_POLICY,
        "scope": "single-model-request",
        "source_compaction_evidence_hash": compacted.evidence.content_hash,
        "source_context_hash": compacted.content_hash,
        "projected_context_hash": sha256_text(rendered),
        "source_context_bytes": len(compacted.rendered.encode("utf-8")),
        "projected_context_bytes": len(rendered.encode("utf-8")),
        "context_bytes_saved": len(compacted.rendered.encode("utf-8"))
        - len(rendered.encode("utf-8")),
        "source_recent_events_hash": sha256_json(source_recent),
        "projected_recent_events_hash": sha256_json(projected_recent),
        "projected_event_count": len(records),
        "event_projections": tuple(records),
        "non_target_events_preserved": True,
        "durable_event_changed": False,
        "durable_result_artifact_changed": False,
        "model_facing_projection_only": True,
        "raw_reasoning_included": False,
        "private_or_hidden_material_included": False,
    }
    evidence = PlanAdmissionFeedbackProjectionEvidence.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )
    return BoundedPlanAdmissionFeedbackContext(
        rendered=rendered,
        content_hash=evidence.projected_context_hash,
        evidence=evidence,
    )


def project_bounded_plan_admission_feedback(
    compacted: CompactedEventContext,
) -> BoundedPlanAdmissionFeedbackContext:
    """Preserve the V22-V24 fail-closed source-policy contract."""

    return _project_bounded_plan_admission_feedback(
        compacted,
        accepted_policy_versions=frozenset({WORK_PLAN_ADMISSION_POLICY, CAUSAL_ALTERNATIVE_POLICY}),
        compatible_self_directed=False,
    )


def project_compatible_bounded_plan_admission_feedback(
    compacted: CompactedEventContext,
) -> BoundedPlanAdmissionFeedbackContext:
    """Bound V25 feedback while accepting the exact self-directed admission policy."""

    return _project_bounded_plan_admission_feedback(
        compacted,
        accepted_policy_versions=frozenset(
            {
                WORK_PLAN_ADMISSION_POLICY,
                CAUSAL_ALTERNATIVE_POLICY,
                SELF_DIRECTED_EXPLORATION_POLICY,
            }
        ),
        compatible_self_directed=True,
    )


__all__ = [
    "BoundedWorkPlanAdmissionFeedback",
    "CompatibleBoundedWorkPlanAdmissionFeedback",
    "BoundedPlanAdmissionFeedbackContext",
    "OmittedPlanAdmissionDetail",
    "PLAN_ADMISSION_FEEDBACK_PROJECTION_POLICY",
    "PLAN_ADMISSION_FEEDBACK_PROJECTION_SCHEMA",
    "PROJECTED_FEEDBACK_SCHEMA",
    "PlanAdmissionFeedbackEventProjection",
    "PlanAdmissionFeedbackProjectionEvidence",
    "project_bounded_plan_admission_feedback",
    "project_compatible_bounded_plan_admission_feedback",
]
