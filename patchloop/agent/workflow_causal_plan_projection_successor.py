"""Offline server-owned causal-plan projection for a post-V17 successor.

R13 showed that a model could provide a useful public causal explanation while
still failing admission because it also had to reproduce server invariants:
path roles, the final null relationship, a matching read/path/range tuple, and
an observation status.  This module makes those invariants unrepresentable in
the model-facing request.  The model selects only catalogued public source
spans and writes semantic descriptions; the server binds the exact evidence
and supplies workflow state.

The module is deliberately not wired into a runtime or tool schema.  It is an
append-only, public-only contract that must be qualified before activation.
It does not execute tools, checks, evaluators, containers, or providers.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.agent.workflow_successor_v2 import (
    CandidateFileEvidence,
    EligiblePlanEvidence,
    EligiblePlanEvidenceCatalog,
    ObservationStatus,
    PlanTrigger,
    _path_allowed,
)
from patchloop.contracts import PublicTask
from patchloop.errors import ContractError
from patchloop.util import safe_relative_path, sha256_json

CAUSAL_PLAN_PROJECTION_POLICY = "server-owned-public-causal-plan-projection-v1"
CAUSAL_SOURCE_SPAN_CATALOG_SCHEMA = "eligible-causal-source-span-catalog-v1"
CAUSAL_PLAN_REQUEST_SCHEMA = "causal-plan-request-projection-v1"
CAUSAL_MECHANISM_SCHEMA_V2 = "public-causal-mechanism-v2"
RECORDED_CAUSAL_PLAN_SCHEMA_V2 = "recorded-causal-plan-v2"

EvidenceId = Annotated[str, Field(pattern=r"^pev:[1-9][0-9]*$")]
SourceSpanId = Annotated[str, Field(pattern=r"^cspan:[1-9][0-9]*:[0-9]+$")]
Hash = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]

_SERVER_OWNED_FIELDS = (
    "observation_status",
    "observation_evidence_id",
    "foundation_evidence_ids",
    "candidate_files",
    "planned_check_ids",
    "causal_path_roles",
    "causal_path_ordinals",
    "causal_path_locations",
    "final_relationship_to_next",
    "run_id",
    "task_id",
    "task_version",
    "public_task_hash",
    "worktree_diff_hash",
)


def _reject(reason_code: str, message: str) -> None:
    raise ContractError(message, details={"reason_codes": [reason_code]})


def _hashed(model: type[BaseModel], body: dict[str, Any]) -> Any:
    return model.model_validate({**body, "content_hash": sha256_json(body)})


def _normalized_public_text(value: str, *, field_name: str) -> str:
    if not value or value != value.strip() or "\x00" in value:
        raise ValueError(f"{field_name} must be trimmed public text")
    return value


class EligibleCausalSourceSpan(BaseModel):
    """One exact visible range from one current-diff public source read."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_span_id: SourceSpanId
    run_id: str = Field(min_length=1)
    worktree_diff_hash: Hash
    read_evidence_id: EvidenceId
    canonical_event_sequence: int = Field(ge=1)
    visible_range_index: int = Field(ge=0)
    path: str = Field(min_length=1)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    partial_line: bool
    artifact_hash: Hash
    visible_projection_hash: Hash
    coverage_key: Hash
    public_current_diff_source_only: Literal[True]
    content_hash: Hash

    @field_validator("path")
    @classmethod
    def normalize_path(cls, value: str) -> str:
        normalized = safe_relative_path(value, field_name="causal source span path")
        if normalized != value:
            raise ValueError("causal source span path differs")
        return value

    @model_validator(mode="after")
    def validate_span(self) -> Self:
        expected_id = f"cspan:{self.canonical_event_sequence}:{self.visible_range_index}"
        expected_coverage = sha256_json(
            {
                "schema_version": "public-source-coverage-key-v2",
                "path": self.path,
                "start_line": self.start_line,
                "end_line": self.end_line,
            }
        )
        if (
            self.source_span_id != expected_id
            or self.read_evidence_id != f"pev:{self.canonical_event_sequence}"
            or self.end_line < self.start_line
            or self.coverage_key != expected_coverage
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("causal source span binding differs")
        return self


class EligibleCausalSourceSpanCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["eligible-causal-source-span-catalog-v1"]
    policy_version: Literal["server-owned-public-causal-plan-projection-v1"]
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    task_version: int = Field(ge=1)
    public_task_hash: Hash
    worktree_diff_hash: Hash
    evidence_catalog_hash: Hash
    spans: tuple[EligibleCausalSourceSpan, ...] = Field(min_length=1)
    public_source_only: Literal[True]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: Hash

    @model_validator(mode="after")
    def validate_catalog(self) -> Self:
        ids = tuple(item.source_span_id for item in self.spans)
        order = tuple(
            (item.canonical_event_sequence, item.visible_range_index) for item in self.spans
        )
        if (
            ids != tuple(dict.fromkeys(ids))
            or order != tuple(sorted(order))
            or any(
                item.run_id != self.run_id or item.worktree_diff_hash != self.worktree_diff_hash
                for item in self.spans
            )
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("causal source span catalog differs")
        return self


class CausalLinkedSpanInput(BaseModel):
    """A model-selected span that must explain its link to the next span."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_span_id: SourceSpanId
    symbol: str | None = Field(default=None, min_length=1, max_length=300)
    observation: str = Field(min_length=1, max_length=1_000)
    relationship_to_next: str = Field(min_length=1, max_length=1_000)

    @field_validator("symbol", "observation", "relationship_to_next")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _normalized_public_text(value, field_name="causal path text")


class CausalMutationSpanInput(BaseModel):
    """The final semantic edit location; no final relationship can be supplied."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_span_id: SourceSpanId
    symbol: str | None = Field(default=None, min_length=1, max_length=300)
    observation: str = Field(min_length=1, max_length=1_000)

    @field_validator("symbol", "observation")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _normalized_public_text(value, field_name="causal mutation text")


class PublicCausalMechanismInputV2(BaseModel):
    """Task-generic semantics with structural fields owned by the server."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    summary: str = Field(min_length=1, max_length=2_000)
    causal_boundary: CausalLinkedSpanInput
    intermediate_steps: list[CausalLinkedSpanInput] = Field(max_length=6)
    mutation_site: CausalMutationSpanInput
    mutation_site_rationale: str = Field(min_length=1, max_length=2_000)
    expected_observable_effect: str = Field(min_length=1, max_length=2_000)
    falsification_condition: str = Field(min_length=1, max_length=2_000)

    @field_validator(
        "summary",
        "mutation_site_rationale",
        "expected_observable_effect",
        "falsification_condition",
    )
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _normalized_public_text(value, field_name="causal mechanism text")


class CausalPlanModelInputV2(BaseModel):
    """The entire model-owned part of record/revise work plan."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    hypothesis: str = Field(min_length=1, max_length=2_000)
    supporting_evidence_ids: list[EvidenceId] = Field(max_length=20)
    candidate_source_span_ids: list[SourceSpanId] = Field(min_length=1, max_length=20)
    intended_change: str = Field(min_length=1, max_length=2_000)
    expected_behavior: str = Field(min_length=1, max_length=2_000)
    unknowns: list[str] = Field(max_length=20)
    prior_hypothesis_disposition: Literal["retained", "refined", "rejected"] | None
    causal_mechanism: PublicCausalMechanismInputV2

    @field_validator("hypothesis", "intended_change", "expected_behavior")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _normalized_public_text(value, field_name="causal plan text")

    @field_validator("unknowns")
    @classmethod
    def normalize_unknowns(cls, values: list[str]) -> list[str]:
        if any(
            not value or value != value.strip() or "\x00" in value or len(value) > 1_000
            for value in values
        ):
            raise ValueError("causal plan unknowns differ")
        return values


class EvidenceBoundCausalPathStepV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    ordinal: int = Field(ge=0, le=7)
    role: Literal["causal_boundary", "intermediate", "mutation_site"]
    source_span: EligibleCausalSourceSpan
    symbol: str | None = Field(default=None, min_length=1, max_length=300)
    observation: str = Field(min_length=1, max_length=1_000)
    relationship_to_next: str | None = Field(default=None, min_length=1, max_length=1_000)


class PublicCausalMechanismV2(BaseModel):
    """Durable evidence-bound mechanism; repeated locations are representable."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["public-causal-mechanism-v2"]
    policy_version: Literal["server-owned-public-causal-plan-projection-v1"]
    run_id: str = Field(min_length=1)
    worktree_diff_hash: Hash
    summary: str = Field(min_length=1, max_length=2_000)
    causal_path: tuple[EvidenceBoundCausalPathStepV2, ...] = Field(min_length=2, max_length=8)
    mutation_site_rationale: str = Field(min_length=1, max_length=2_000)
    expected_observable_effect: str = Field(min_length=1, max_length=2_000)
    falsification_condition: str = Field(min_length=1, max_length=2_000)
    mechanism_family_key: Hash
    source_coverage_keys: tuple[Hash, ...] = Field(min_length=2, max_length=8)
    source_evidence_ids: tuple[EvidenceId, ...] = Field(min_length=1, max_length=8)
    repeated_source_locations_allowed: Literal[True]
    roles_server_owned: Literal[True]
    locations_server_bound: Literal[True]
    final_relationship_server_owned: Literal[True]
    public_current_diff_source_only: Literal[True]
    symbol_text_used_for_admission: Literal[False]
    prose_used_for_distinctness: Literal[False]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: Hash

    @model_validator(mode="after")
    def validate_mechanism(self) -> Self:
        roles = tuple(step.role for step in self.causal_path)
        keys = tuple(step.source_span.coverage_key for step in self.causal_path)
        evidence_ids = tuple(
            dict.fromkeys(step.source_span.read_evidence_id for step in self.causal_path)
        )
        expected_family = sha256_json(
            {
                "schema_version": "public-causal-mechanism-family-v2",
                "causal_path_coverage_keys": keys,
            }
        )
        if (
            tuple(step.ordinal for step in self.causal_path) != tuple(range(len(self.causal_path)))
            or roles[0] != "causal_boundary"
            or roles[-1] != "mutation_site"
            or any(role != "intermediate" for role in roles[1:-1])
            or any(step.relationship_to_next is None for step in self.causal_path[:-1])
            or self.causal_path[-1].relationship_to_next is not None
            or self.source_coverage_keys != keys
            or self.source_evidence_ids != evidence_ids
            or self.mechanism_family_key != expected_family
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("public causal mechanism v2 differs")
        return self


class CausalPlanRequestProjection(BaseModel):
    """Deterministic dynamic schema shown to the model in a future runtime."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["causal-plan-request-projection-v1"]
    policy_version: Literal["server-owned-public-causal-plan-projection-v1"]
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    task_version: int = Field(ge=1)
    public_task_hash: Hash
    worktree_diff_hash: Hash
    trigger: PlanTrigger
    observation_status: ObservationStatus
    observation_evidence_id: EvidenceId | None
    source_span_catalog: EligibleCausalSourceSpanCatalog
    eligible_supporting_evidence_ids: tuple[EvidenceId, ...]
    server_owned_fields: tuple[str, ...]
    parameters: dict[str, Any]
    parameter_schema_hash: Hash
    runtime_surface_activated: Literal[False]
    content_hash: Hash

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        serialized = str(self.parameters)
        forbidden_model_fields = {
            "observation_status",
            "foundation_evidence_ids",
            "candidate_files",
            "planned_check_ids",
            "role",
            "path",
            "start_line",
            "end_line",
            "read_evidence_id",
            "relationship_to_next_final",
        }
        if (
            self.server_owned_fields != _SERVER_OWNED_FIELDS
            or any(f"'{field}'" in serialized for field in forbidden_model_fields)
            or self.parameter_schema_hash != sha256_json(self.parameters)
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("causal plan request projection differs")
        return self


class RecordedCausalPlanV2(BaseModel):
    """Server-normalized durable plan suitable for a later opt-in activation."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["recorded-causal-plan-v2"]
    policy_version: Literal["server-owned-public-causal-plan-projection-v1"]
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    task_version: int = Field(ge=1)
    public_task_hash: Hash
    worktree_diff_hash: Hash
    trigger: PlanTrigger
    revision_index: int = Field(ge=0, le=3)
    parent_plan_hash: Hash | None
    trigger_check_id: str | None
    trigger_event_sequence: int | None = Field(default=None, ge=1)
    observation_status: ObservationStatus
    observation_evidence: EligiblePlanEvidence | None
    hypothesis: str = Field(min_length=1, max_length=2_000)
    foundation_evidence: tuple[EligiblePlanEvidence, ...] = Field(min_length=1, max_length=20)
    supporting_evidence: tuple[EligiblePlanEvidence, ...] = Field(max_length=20)
    candidate_source_spans: tuple[EligibleCausalSourceSpan, ...] = Field(
        min_length=1, max_length=20
    )
    candidate_files: tuple[CandidateFileEvidence, ...] = Field(min_length=1, max_length=20)
    intended_change: str = Field(min_length=1, max_length=2_000)
    expected_behavior: str = Field(min_length=1, max_length=2_000)
    unknowns: tuple[str, ...] = Field(max_length=20)
    prior_hypothesis_disposition: Literal["retained", "refined", "rejected"] | None
    planned_check_ids: tuple[str, ...] = Field(min_length=1)
    causal_mechanism: PublicCausalMechanismV2
    source_span_catalog_hash: Hash
    server_owned_fields: tuple[str, ...]
    public_evidence_only: Literal[True]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: Hash

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        foundation_ids = {item.evidence_id for item in self.foundation_evidence}
        candidate_pairs = {(item.path, item.read_evidence_id) for item in self.candidate_files}
        candidate_span_ids = {item.source_span_id for item in self.candidate_source_spans}
        mechanism_span_ids = {
            step.source_span.source_span_id for step in self.causal_mechanism.causal_path
        }
        expected_by_path: dict[str, EligibleCausalSourceSpan] = {}
        for item in self.candidate_source_spans:
            previous = expected_by_path.get(item.path)
            if (
                previous is None
                or item.canonical_event_sequence > previous.canonical_event_sequence
            ):
                expected_by_path[item.path] = item
        expected_candidate_pairs = {
            (path, item.read_evidence_id) for path, item in expected_by_path.items()
        }
        trigger_valid = (
            self.revision_index == 0
            and self.parent_plan_hash is None
            and self.trigger_check_id is None
            and self.trigger_event_sequence is None
            and self.prior_hypothesis_disposition is None
            if self.trigger == "initial"
            else self.revision_index >= 1
            and self.parent_plan_hash is not None
            and self.trigger_event_sequence is not None
            and self.prior_hypothesis_disposition is not None
        )
        if (
            not trigger_valid
            or self.server_owned_fields != _SERVER_OWNED_FIELDS
            or self.worktree_diff_hash != self.causal_mechanism.worktree_diff_hash
            or not candidate_span_ids.issubset(mechanism_span_ids)
            or candidate_pairs != expected_candidate_pairs
            or any(item.read_evidence_id not in foundation_ids for item in self.candidate_files)
            or (
                self.observation_evidence is not None
                and self.observation_evidence.evidence_id not in foundation_ids
            )
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("recorded causal plan v2 differs")
        return self


def project_eligible_causal_source_spans(
    *, task: PublicTask, catalog: EligiblePlanEvidenceCatalog
) -> EligibleCausalSourceSpanCatalog:
    """Convert exact model-visible source ranges into finite selectable IDs."""

    if (
        task.task_id != catalog.task_id
        or task.task_version != catalog.task_version
        or sha256_json(task.model_dump(mode="json")) != catalog.public_task_hash
    ):
        _reject("causal_span_task_binding_invalid", "causal source catalog task differs")
    spans: list[dict[str, Any]] = []
    for item in catalog.items:
        if (
            item.kind != "source_read"
            or item.role != "foundation"
            or item.source is None
            or not _path_allowed(task, item.source.path)
        ):
            continue
        for index, (start, end) in enumerate(item.source.visible_ranges):
            span_body = {
                "source_span_id": f"cspan:{item.canonical_event_sequence}:{index}",
                "run_id": catalog.run_id,
                "worktree_diff_hash": catalog.worktree_diff_hash,
                "read_evidence_id": item.evidence_id,
                "canonical_event_sequence": item.canonical_event_sequence,
                "visible_range_index": index,
                "path": item.source.path,
                "start_line": start,
                "end_line": end,
                "partial_line": item.source.partial_line,
                "artifact_hash": item.artifact_hash,
                "visible_projection_hash": item.visible_projection_hash,
                "coverage_key": sha256_json(
                    {
                        "schema_version": "public-source-coverage-key-v2",
                        "path": item.source.path,
                        "start_line": start,
                        "end_line": end,
                    }
                ),
                "public_current_diff_source_only": True,
            }
            spans.append(_hashed(EligibleCausalSourceSpan, span_body).model_dump(mode="python"))
    if not spans:
        _reject("causal_source_evidence_unavailable", "no public causal source span exists")
    body = {
        "schema_version": CAUSAL_SOURCE_SPAN_CATALOG_SCHEMA,
        "policy_version": CAUSAL_PLAN_PROJECTION_POLICY,
        "run_id": catalog.run_id,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_task_hash": catalog.public_task_hash,
        "worktree_diff_hash": catalog.worktree_diff_hash,
        "evidence_catalog_hash": catalog.content_hash,
        "spans": tuple(spans),
        "public_source_only": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(EligibleCausalSourceSpanCatalog, body)


def _derive_observation(
    *,
    catalog: EligiblePlanEvidenceCatalog,
    trigger: PlanTrigger,
    trigger_check_id: str | None,
    trigger_event_sequence: int | None,
) -> tuple[ObservationStatus, EligiblePlanEvidence | None]:
    if trigger == "initial":
        checks = [
            item
            for item in catalog.items
            if item.kind == "targeted_check_result"
            and item.check is not None
            and item.check.invocation_status == "completed"
            and item.check.behavior_status in {"passed", "failed"}
        ]
        if not checks:
            return "static_source", None
        selected = max(checks, key=lambda item: item.canonical_event_sequence)
        assert selected.check is not None
        status: ObservationStatus = (
            "targeted_check_passed"
            if selected.check.behavior_status == "passed"
            else "targeted_check_failed"
        )
        return status, selected
    if trigger_event_sequence is None:
        _reject("causal_observation_trigger_invalid", "causal plan trigger sequence is absent")
    selected = next(
        (item for item in catalog.items if item.canonical_event_sequence == trigger_event_sequence),
        None,
    )
    if trigger == "check_failure":
        if (
            selected is None
            or selected.kind not in {"targeted_check_result", "visible_check_result"}
            or selected.check is None
            or selected.check.check_id != trigger_check_id
            or selected.check.invocation_status != "completed"
            or selected.check.behavior_status != "failed"
        ):
            _reject(
                "causal_observation_trigger_invalid",
                "causal revision lacks its exact public failed-check trigger",
            )
        return "visible_check_failed", selected
    if selected is None or selected.kind != "diff_review_result":
        _reject(
            "causal_observation_trigger_invalid",
            "causal review revision lacks its exact public diff trigger",
        )
    return "review_diff", selected


def _linked_step_schema(span_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "source_span_id": {"type": "string", "enum": span_ids},
            "symbol": {"type": ["string", "null"], "minLength": 1, "maxLength": 300},
            "observation": {"type": "string", "minLength": 1, "maxLength": 1_000},
            "relationship_to_next": {
                "type": "string",
                "minLength": 1,
                "maxLength": 1_000,
            },
        },
        "required": ["source_span_id", "symbol", "observation", "relationship_to_next"],
        "additionalProperties": False,
    }


def _mutation_step_schema(span_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "source_span_id": {"type": "string", "enum": span_ids},
            "symbol": {"type": ["string", "null"], "minLength": 1, "maxLength": 300},
            "observation": {"type": "string", "minLength": 1, "maxLength": 1_000},
        },
        "required": ["source_span_id", "symbol", "observation"],
        "additionalProperties": False,
    }


def project_causal_plan_request(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
    trigger: PlanTrigger,
    trigger_check_id: str | None = None,
    trigger_event_sequence: int | None = None,
) -> CausalPlanRequestProjection:
    """Build a strict dynamic request with workflow invariants removed from input."""

    spans = project_eligible_causal_source_spans(task=task, catalog=catalog)
    observation_status, observation = _derive_observation(
        catalog=catalog,
        trigger=trigger,
        trigger_check_id=trigger_check_id,
        trigger_event_sequence=trigger_event_sequence,
    )
    span_ids = [item.source_span_id for item in spans.spans]
    support_ids = [item.evidence_id for item in catalog.items if item.role == "support"]
    support_items: dict[str, Any] = (
        {"type": "string", "enum": support_ids} if support_ids else {"type": "string"}
    )
    mechanism = {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "minLength": 1, "maxLength": 2_000},
            "causal_boundary": _linked_step_schema(span_ids),
            "intermediate_steps": {
                "type": "array",
                "maxItems": 6,
                "items": _linked_step_schema(span_ids),
            },
            "mutation_site": _mutation_step_schema(span_ids),
            "mutation_site_rationale": {
                "type": "string",
                "minLength": 1,
                "maxLength": 2_000,
            },
            "expected_observable_effect": {
                "type": "string",
                "minLength": 1,
                "maxLength": 2_000,
            },
            "falsification_condition": {
                "type": "string",
                "minLength": 1,
                "maxLength": 2_000,
            },
        },
        "required": [
            "summary",
            "causal_boundary",
            "intermediate_steps",
            "mutation_site",
            "mutation_site_rationale",
            "expected_observable_effect",
            "falsification_condition",
        ],
        "additionalProperties": False,
    }
    parameters = {
        "type": "object",
        "properties": {
            "hypothesis": {"type": "string", "minLength": 1, "maxLength": 2_000},
            "supporting_evidence_ids": {
                "type": "array",
                "maxItems": 20 if support_ids else 0,
                "items": support_items,
            },
            "candidate_source_span_ids": {
                "type": "array",
                "minItems": 1,
                "maxItems": 20,
                "items": {"type": "string", "enum": span_ids},
            },
            "intended_change": {"type": "string", "minLength": 1, "maxLength": 2_000},
            "expected_behavior": {"type": "string", "minLength": 1, "maxLength": 2_000},
            "unknowns": {
                "type": "array",
                "maxItems": 20,
                "items": {"type": "string", "minLength": 1, "maxLength": 1_000},
            },
            "prior_hypothesis_disposition": {
                "type": ["string", "null"],
                "enum": ["retained", "refined", "rejected", None],
            },
            "causal_mechanism": mechanism,
        },
        "required": [
            "hypothesis",
            "supporting_evidence_ids",
            "candidate_source_span_ids",
            "intended_change",
            "expected_behavior",
            "unknowns",
            "prior_hypothesis_disposition",
            "causal_mechanism",
        ],
        "additionalProperties": False,
    }
    body = {
        "schema_version": CAUSAL_PLAN_REQUEST_SCHEMA,
        "policy_version": CAUSAL_PLAN_PROJECTION_POLICY,
        "run_id": catalog.run_id,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_task_hash": catalog.public_task_hash,
        "worktree_diff_hash": catalog.worktree_diff_hash,
        "trigger": trigger,
        "observation_status": observation_status,
        "observation_evidence_id": None if observation is None else observation.evidence_id,
        "source_span_catalog": spans.model_dump(mode="python"),
        "eligible_supporting_evidence_ids": tuple(support_ids),
        "server_owned_fields": _SERVER_OWNED_FIELDS,
        "parameters": parameters,
        "parameter_schema_hash": sha256_json(parameters),
        "runtime_surface_activated": False,
    }
    return _hashed(CausalPlanRequestProjection, body)


def _normalize_mechanism(
    *,
    projection: CausalPlanRequestProjection,
    submitted: PublicCausalMechanismInputV2,
) -> PublicCausalMechanismV2:
    by_id = {item.source_span_id: item for item in projection.source_span_catalog.spans}
    raw_steps: list[tuple[str, CausalLinkedSpanInput | CausalMutationSpanInput]] = [
        ("causal_boundary", submitted.causal_boundary),
        *(("intermediate", item) for item in submitted.intermediate_steps),
        ("mutation_site", submitted.mutation_site),
    ]
    steps: list[dict[str, Any]] = []
    for ordinal, (role, raw) in enumerate(raw_steps):
        span = by_id.get(raw.source_span_id)
        if span is None:
            _reject(
                "causal_source_span_ineligible",
                "causal plan cites a source span outside the current request",
            )
        relationship = raw.relationship_to_next if isinstance(raw, CausalLinkedSpanInput) else None
        steps.append(
            {
                "ordinal": ordinal,
                "role": role,
                "source_span": span.model_dump(mode="python"),
                "symbol": raw.symbol,
                "observation": raw.observation,
                "relationship_to_next": relationship,
            }
        )
    keys = tuple(step["source_span"]["coverage_key"] for step in steps)
    family = sha256_json(
        {
            "schema_version": "public-causal-mechanism-family-v2",
            "causal_path_coverage_keys": keys,
        }
    )
    body = {
        "schema_version": CAUSAL_MECHANISM_SCHEMA_V2,
        "policy_version": CAUSAL_PLAN_PROJECTION_POLICY,
        "run_id": projection.run_id,
        "worktree_diff_hash": projection.worktree_diff_hash,
        "summary": submitted.summary,
        "causal_path": tuple(steps),
        "mutation_site_rationale": submitted.mutation_site_rationale,
        "expected_observable_effect": submitted.expected_observable_effect,
        "falsification_condition": submitted.falsification_condition,
        "mechanism_family_key": family,
        "source_coverage_keys": keys,
        "source_evidence_ids": tuple(
            dict.fromkeys(step["source_span"]["read_evidence_id"] for step in steps)
        ),
        "repeated_source_locations_allowed": True,
        "roles_server_owned": True,
        "locations_server_bound": True,
        "final_relationship_server_owned": True,
        "public_current_diff_source_only": True,
        "symbol_text_used_for_admission": False,
        "prose_used_for_distinctness": False,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(PublicCausalMechanismV2, body)


def normalize_causal_plan_request(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
    trigger: PlanTrigger,
    revision_index: int,
    parent_plan_hash: str | None,
    trigger_check_id: str | None,
    trigger_event_sequence: int | None,
    raw_arguments: dict[str, Any],
) -> RecordedCausalPlanV2:
    """Validate only model-owned semantics, then supply every server invariant."""

    projection = project_causal_plan_request(
        task=task,
        catalog=catalog,
        trigger=trigger,
        trigger_check_id=trigger_check_id,
        trigger_event_sequence=trigger_event_sequence,
    )
    try:
        submitted = CausalPlanModelInputV2.model_validate(raw_arguments)
    except ValueError as exc:
        _reject("causal_plan_input_shape_invalid", "causal plan model input differs")
        raise AssertionError from exc
    if trigger == "initial":
        if (
            revision_index != 0
            or parent_plan_hash is not None
            or trigger_check_id is not None
            or trigger_event_sequence is not None
            or submitted.prior_hypothesis_disposition is not None
        ):
            _reject("causal_plan_revision_binding_invalid", "initial causal plan binding differs")
    elif (
        revision_index < 1
        or parent_plan_hash is None
        or trigger_event_sequence is None
        or submitted.prior_hypothesis_disposition is None
    ):
        _reject("causal_plan_revision_binding_invalid", "causal plan revision binding differs")
    span_by_id = {item.source_span_id: item for item in projection.source_span_catalog.spans}
    candidate_spans: list[EligibleCausalSourceSpan] = []
    for span_id in dict.fromkeys(submitted.candidate_source_span_ids):
        span = span_by_id.get(span_id)
        if span is None:
            _reject(
                "causal_candidate_span_ineligible",
                "causal plan candidate is outside the current source-span catalog",
            )
        candidate_spans.append(span)
    mechanism = _normalize_mechanism(projection=projection, submitted=submitted.causal_mechanism)
    mechanism_span_ids = {step.source_span.source_span_id for step in mechanism.causal_path}
    if any(item.source_span_id not in mechanism_span_ids for item in candidate_spans):
        _reject(
            "causal_candidate_not_in_mechanism",
            "causal plan candidate is not one of its evidence-bound mechanism spans",
        )
    catalog_by_id = {item.evidence_id: item for item in catalog.items}
    support: list[EligiblePlanEvidence] = []
    for evidence_id in dict.fromkeys(submitted.supporting_evidence_ids):
        evidence = catalog_by_id.get(evidence_id)
        if evidence is None or evidence.role != "support":
            _reject(
                "causal_support_evidence_ineligible",
                "causal plan support evidence differs from the current request",
            )
        support.append(evidence)
    observation = (
        None
        if projection.observation_evidence_id is None
        else catalog_by_id[projection.observation_evidence_id]
    )
    foundation_ids = set(mechanism.source_evidence_ids)
    foundation_ids.update(item.read_evidence_id for item in candidate_spans)
    if observation is not None:
        foundation_ids.add(observation.evidence_id)
    foundation = tuple(
        item
        for item in catalog.items
        if item.evidence_id in foundation_ids and item.role == "foundation"
    )
    candidates_by_path: dict[str, EligibleCausalSourceSpan] = {}
    for span in candidate_spans:
        previous = candidates_by_path.get(span.path)
        if previous is None or span.canonical_event_sequence > previous.canonical_event_sequence:
            candidates_by_path[span.path] = span
    candidates = tuple(
        CandidateFileEvidence(path=path, read_evidence_id=span.read_evidence_id)
        for path, span in sorted(candidates_by_path.items())
    )
    body = {
        "schema_version": RECORDED_CAUSAL_PLAN_SCHEMA_V2,
        "policy_version": CAUSAL_PLAN_PROJECTION_POLICY,
        "run_id": catalog.run_id,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_task_hash": catalog.public_task_hash,
        "worktree_diff_hash": catalog.worktree_diff_hash,
        "trigger": trigger,
        "revision_index": revision_index,
        "parent_plan_hash": parent_plan_hash,
        "trigger_check_id": trigger_check_id,
        "trigger_event_sequence": trigger_event_sequence,
        "observation_status": projection.observation_status,
        "observation_evidence": None
        if observation is None
        else observation.model_dump(mode="python"),
        "hypothesis": submitted.hypothesis,
        "foundation_evidence": tuple(item.model_dump(mode="python") for item in foundation),
        "supporting_evidence": tuple(item.model_dump(mode="python") for item in support),
        "candidate_source_spans": tuple(item.model_dump(mode="python") for item in candidate_spans),
        "candidate_files": tuple(item.model_dump(mode="python") for item in candidates),
        "intended_change": submitted.intended_change,
        "expected_behavior": submitted.expected_behavior,
        "unknowns": tuple(submitted.unknowns),
        "prior_hypothesis_disposition": submitted.prior_hypothesis_disposition,
        "planned_check_ids": tuple(check.id for check in task.visible_checks),
        "causal_mechanism": mechanism.model_dump(mode="python"),
        "source_span_catalog_hash": projection.source_span_catalog.content_hash,
        "server_owned_fields": _SERVER_OWNED_FIELDS,
        "public_evidence_only": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(RecordedCausalPlanV2, body)


__all__ = [
    "CAUSAL_MECHANISM_SCHEMA_V2",
    "CAUSAL_PLAN_PROJECTION_POLICY",
    "CAUSAL_PLAN_REQUEST_SCHEMA",
    "CAUSAL_SOURCE_SPAN_CATALOG_SCHEMA",
    "CausalPlanModelInputV2",
    "CausalPlanRequestProjection",
    "EligibleCausalSourceSpan",
    "EligibleCausalSourceSpanCatalog",
    "PublicCausalMechanismV2",
    "RECORDED_CAUSAL_PLAN_SCHEMA_V2",
    "RecordedCausalPlanV2",
    "normalize_causal_plan_request",
    "project_causal_plan_request",
    "project_eligible_causal_source_spans",
]
