"""Lean V16 public work-plan candidate-binding normalization.

V15 correctly required every candidate file to cite a current-diff public
``read_file`` result, but treated two valid reads of different ranges in the
same file as two conflicting candidate files.  This opt-in successor validates
every submitted binding first, then deterministically collapses bindings by
path while retaining every cited read as foundation evidence in the recorded
plan.

The module does not execute tools or inspect task-private, evaluator, reference
patch, or model-reasoning data.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.workflow_successor_v2 import (
    CandidateFileEvidence,
    EligiblePlanEvidenceCatalog,
    RecordedWorkPlanV2,
    _path_allowed,
    validate_work_plan_v2,
)
from patchloop.contracts import PublicTask
from patchloop.errors import ContractError
from patchloop.util import sha256_json

CANDIDATE_BINDING_POLICY_V16 = "same-path-public-read-binding-normalization-v1"
CANDIDATE_BINDING_PROJECTION_SCHEMA = "candidate-binding-normalization-v1"
EvidenceId = Annotated[str, Field(pattern=r"^pev:[1-9][0-9]*$")]


def _reject(reason_code: str, message: str) -> None:
    raise ContractError(message, details={"reason_codes": [reason_code]})


class CandidatePathBindingProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    submitted_binding_count: int = Field(ge=1, le=100)
    cited_read_evidence_ids: tuple[EvidenceId, ...] = Field(min_length=1)
    selected_read_evidence_id: EvidenceId
    collapsed_same_path_bindings: bool

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        if (
            tuple(dict.fromkeys(self.cited_read_evidence_ids)) != self.cited_read_evidence_ids
            or self.selected_read_evidence_id not in self.cited_read_evidence_ids
            or self.collapsed_same_path_bindings is not (self.submitted_binding_count > 1)
        ):
            raise ValueError("candidate path binding projection differs")
        return self


class CandidateBindingNormalization(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["candidate-binding-normalization-v1"]
    policy_version: Literal["same-path-public-read-binding-normalization-v1"]
    run_id: str = Field(min_length=1)
    worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    submitted_binding_count: int = Field(ge=1, le=100)
    canonical_candidate_count: int = Field(ge=1, le=20)
    path_bindings: tuple[CandidatePathBindingProjection, ...] = Field(min_length=1)
    public_current_diff_reads_only: Literal[True]
    private_evidence_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        if (
            tuple(item.path for item in self.path_bindings)
            != tuple(sorted(item.path for item in self.path_bindings))
            or len({item.path for item in self.path_bindings}) != len(self.path_bindings)
            or self.canonical_candidate_count != len(self.path_bindings)
            or self.submitted_binding_count
            != sum(item.submitted_binding_count for item in self.path_bindings)
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("candidate binding normalization differs")
        return self


def normalize_same_path_candidate_bindings(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
    arguments: dict[str, Any],
) -> tuple[dict[str, Any], CandidateBindingNormalization]:
    """Validate all raw bindings and select one latest read per candidate path.

    Selection is by ``(canonical_event_sequence, evidence_id)``.  This makes
    replay/restart deterministic and prefers the most recent visible range.  No
    cited source-read evidence is removed from ``foundation_evidence_ids``.
    """

    if type(arguments) is not dict:
        _reject("plan_shape_invalid", "work-plan arguments differ")
    raw_candidates = arguments.get("candidate_files")
    foundation_ids = arguments.get("foundation_evidence_ids")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        _reject("plan_collection_invalid", "work-plan candidate files differ")
    if not isinstance(foundation_ids, list) or not foundation_ids:
        _reject("plan_collection_invalid", "work-plan foundation evidence differs")

    by_id = {item.evidence_id: item for item in catalog.items}
    foundation_id_set = {item for item in foundation_ids if isinstance(item, str) and item in by_id}
    grouped: dict[str, list[tuple[CandidateFileEvidence, int]]] = {}
    for raw in raw_candidates:
        try:
            candidate = CandidateFileEvidence.model_validate(raw)
        except ValueError:
            _reject("candidate_shape_invalid", "work-plan candidate file differs")
        evidence = by_id.get(candidate.read_evidence_id)
        if (
            evidence is None
            or evidence.kind != "source_read"
            or evidence.role != "foundation"
            or evidence.source is None
            or evidence.source.path != candidate.path
            or evidence.evidence_id not in foundation_id_set
            or evidence.run_id != catalog.run_id
            or evidence.worktree_diff_hash != catalog.worktree_diff_hash
            or not _path_allowed(task, candidate.path)
        ):
            _reject(
                "candidate_read_binding_invalid",
                "work-plan candidate lacks its cited current source read",
            )
        grouped.setdefault(candidate.path, []).append(
            (candidate, evidence.canonical_event_sequence)
        )

    selected: list[CandidateFileEvidence] = []
    path_bindings: list[CandidatePathBindingProjection] = []
    for path in sorted(grouped):
        unique_by_evidence: dict[str, tuple[CandidateFileEvidence, int]] = {}
        for candidate, sequence in grouped[path]:
            unique_by_evidence[candidate.read_evidence_id] = (candidate, sequence)
        ordered = sorted(
            unique_by_evidence.values(),
            key=lambda item: (item[1], item[0].read_evidence_id),
        )
        chosen = ordered[-1][0]
        selected.append(chosen)
        path_bindings.append(
            CandidatePathBindingProjection(
                path=path,
                submitted_binding_count=len(grouped[path]),
                cited_read_evidence_ids=tuple(item[0].read_evidence_id for item in ordered),
                selected_read_evidence_id=chosen.read_evidence_id,
                collapsed_same_path_bindings=len(grouped[path]) > 1,
            )
        )

    projection_body = {
        "schema_version": CANDIDATE_BINDING_PROJECTION_SCHEMA,
        "policy_version": CANDIDATE_BINDING_POLICY_V16,
        "run_id": catalog.run_id,
        "worktree_diff_hash": catalog.worktree_diff_hash,
        "submitted_binding_count": sum(item.submitted_binding_count for item in path_bindings),
        "canonical_candidate_count": len(selected),
        "path_bindings": tuple(item.model_dump(mode="python") for item in path_bindings),
        "public_current_diff_reads_only": True,
        "private_evidence_used": False,
        "reasoning_text_used": False,
    }
    projection = CandidateBindingNormalization.model_validate(
        {**projection_body, "content_hash": sha256_json(projection_body)}
    )
    normalized_arguments = {
        **arguments,
        "candidate_files": [item.model_dump(mode="json") for item in selected],
    }
    return normalized_arguments, projection


def validate_work_plan_v16(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
    arguments: dict[str, Any],
    trigger: Literal["initial", "check_failure", "review_correction"],
    revision_index: int,
    parent_plan_hash: str | None,
    trigger_check_id: str | None,
    trigger_event_sequence: int | None,
) -> tuple[RecordedWorkPlanV2, CandidateBindingNormalization]:
    """Validate the V16 admission successor without changing the V15 validator."""

    normalized, projection = normalize_same_path_candidate_bindings(
        task=task,
        catalog=catalog,
        arguments=arguments,
    )
    plan = validate_work_plan_v2(
        task=task,
        catalog=catalog,
        arguments=normalized,
        trigger=trigger,
        revision_index=revision_index,
        parent_plan_hash=parent_plan_hash,
        trigger_check_id=trigger_check_id,
        trigger_event_sequence=trigger_event_sequence,
    )
    return plan, projection


__all__ = [
    "CANDIDATE_BINDING_POLICY_V16",
    "CANDIDATE_BINDING_PROJECTION_SCHEMA",
    "CandidateBindingNormalization",
    "CandidatePathBindingProjection",
    "normalize_same_path_candidate_bindings",
    "validate_work_plan_v16",
]
