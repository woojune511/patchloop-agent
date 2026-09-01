"""No-call state machine for a future fresh-panel task-admission transcript.

This module starts only after a public candidate registry has been source
qualified.  It deterministically consumes each frozen admission queue, derives
candidate rejection codes from a closed audit record, and stops on the first
infrastructure/qualification confound or exhausted required queue.

The consumer deliberately does not authenticate the audit producer.  Its
projection is therefore always unqualified: it may prove that the queue and
state-machine contracts are wired correctly, but it cannot materialize a task
panel or authorize task/private/Docker/provider/runtime access.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, Self, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.errors import ContractError
from patchloop.evals.fresh_acquisition_preregistration import SAME_REPOSITORY_TARGETS
from patchloop.evals.fresh_candidate_registry import (
    AdmissionQueuePolicy,
    QualifiedFreshCandidateRegistry,
    RankedCandidate,
)
from patchloop.util import sha256_json

SCHEMA_VERSION = "lean-fresh-task-admission-projection-v1"

RejectionCode = Literal[
    "below-medium-difficulty-audit",
    "reference-pass-count-insufficient",
    "bad-patch-rejection-count-insufficient",
    "base-visible-hidden-contract-failed",
    "reference-verdict-bundle-failed",
    "task-binding-incomplete",
    "remaining-identity-overlap",
    "license-incompatible",
    "cross-repository-already-admitted",
]
ConfoundCode = Literal[
    "admission-producer-source-drift",
    "task-package-unavailable",
    "evaluator-qualification-failed",
    "docker-infrastructure-error",
    "evidence-persistence-error",
]


class FreshTaskAdmissionError(ContractError):
    """A task-admission transcript or state transition is invalid."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    @model_validator(mode="before")
    @classmethod
    def reject_literal_scalar_type_drift(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        for name, field in cls.model_fields.items():
            annotation = field.annotation
            if get_origin(annotation) is not Literal:
                continue
            expected_values = get_args(annotation)
            if len(expected_values) != 1 or name not in value:
                continue
            expected = expected_values[0]
            if isinstance(expected, (bool, int, float, str)) and type(value[name]) is not type(
                expected
            ):
                raise ValueError(f"{name} has a non-exact scalar type")
        return value


def _canonical_task_path(value: str) -> str:
    candidate = Path(value)
    normalized = candidate.as_posix()
    if (
        candidate.is_absolute()
        or "\\" in value
        or normalized != value
        or not value.startswith("tasks/")
        or normalized.startswith("../")
        or "/../" in normalized
    ):
        raise ValueError("task path must be canonical and repository-relative under tasks")
    return value


class TaskPackageBinding(FrozenModel):
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    task_version: int = Field(ge=1)
    task_path: str
    environment_image: str = Field(pattern=r"^[A-Za-z0-9._/-]+@sha256:[0-9a-f]{64}$")
    public_spec_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_spec_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_contract_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_package_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("task_version", mode="before")
    @classmethod
    def require_exact_version(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("task_version must be a JSON integer")
        return value

    @field_validator("task_path")
    @classmethod
    def validate_task_path(cls, value: str) -> str:
        return _canonical_task_path(value)


class RemainingIdentityAudit(FrozenModel):
    comparison_manifest_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_id_and_version_disjoint: bool
    solution_lineage_id: str = Field(min_length=1, max_length=256)
    solution_lineage_disjoint: bool
    public_spec_hash_disjoint: bool
    private_spec_hash_disjoint: bool


class AdmissionAuditEvidence(FrozenModel):
    audit_completed: bool
    confound_code: ConfoundCode | None
    difficulty_tier: Literal["easy", "medium", "hard", "not-run"]
    official_reference_pass_count: int = Field(ge=0)
    rejected_bad_patch_count: int = Field(ge=0)
    base_visible_verdict: Literal["PASS", "FAIL", "NOT_RUN"]
    base_hidden_verdict: Literal["PASS", "FAIL", "NOT_RUN"]
    reference_visible_verdict: Literal["PASS", "FAIL", "NOT_RUN"]
    reference_hidden_verdict: Literal["PASS", "FAIL", "NOT_RUN"]
    reference_scope_verdict: Literal["PASS", "FAIL", "NOT_RUN"]
    reference_safety_verdict: Literal["PASS", "FAIL", "NOT_RUN"]
    task_package_binding: TaskPackageBinding | None
    remaining_identity_audit: RemainingIdentityAudit | None
    license_compatible: bool
    producer_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    producer_validation_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator(
        "official_reference_pass_count",
        "rejected_bad_patch_count",
        mode="before",
    )
    @classmethod
    def require_exact_counts(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("admission evidence counts must be JSON integers")
        return value

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        if self.audit_completed != (self.confound_code is None):
            raise ValueError("admission audit completion/confound envelope differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"evidence_hash"}))
        if self.evidence_hash != expected:
            raise ValueError("admission evidence hash differs")
        return self


class AdmissionAttempt(FrozenModel):
    sequence: int = Field(ge=1)
    stratum: Literal["same", "cross"]
    same_repository_target: str | None
    queue_position: int = Field(ge=1)
    canonical_public_instance_id: str
    upstream_repository: str
    ranking_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    public_row_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence: AdmissionAuditEvidence
    attempt_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("sequence", "queue_position", mode="before")
    @classmethod
    def require_exact_positions(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("admission positions must be JSON integers")
        return value

    @model_validator(mode="after")
    def validate_attempt(self) -> Self:
        if (self.stratum == "same") != (self.same_repository_target is not None):
            raise ValueError("admission attempt same-target envelope differs")
        if (
            self.same_repository_target is not None
            and self.same_repository_target not in SAME_REPOSITORY_TARGETS
        ):
            raise ValueError("admission attempt same target differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"attempt_hash"}))
        if self.attempt_hash != expected:
            raise ValueError("admission attempt hash differs")
        return self


class AdmissionDecisionRow(FrozenModel):
    sequence: int = Field(ge=1)
    stratum: Literal["same", "cross"]
    same_repository_target: str | None
    queue_position: int = Field(ge=1)
    canonical_public_instance_id: str
    upstream_repository: str
    ranking_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    public_row_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    decision: Literal["accepted", "rejected", "confounded"]
    rejection_code: RejectionCode | None
    confound_code: ConfoundCode | None
    selected_role: Literal["core-same-repo", "core-cross-repo"] | None
    task_package_binding: TaskPackageBinding | None
    solution_lineage_id: str | None
    decision_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        accepted = self.decision == "accepted"
        rejected = self.decision == "rejected"
        confounded = self.decision == "confounded"
        if accepted != (
            self.rejection_code is None
            and self.confound_code is None
            and self.selected_role is not None
            and self.task_package_binding is not None
            and self.solution_lineage_id is not None
        ):
            raise ValueError("accepted admission decision envelope differs")
        if rejected != (
            self.rejection_code is not None
            and self.confound_code is None
            and self.selected_role is None
            and self.task_package_binding is None
            and self.solution_lineage_id is None
        ):
            raise ValueError("rejected admission decision envelope differs")
        if confounded != (
            self.rejection_code is None
            and self.confound_code is not None
            and self.selected_role is None
            and self.task_package_binding is None
            and self.solution_lineage_id is None
        ):
            raise ValueError("confounded admission decision envelope differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"decision_hash"}))
        if self.decision_hash != expected:
            raise ValueError("admission decision hash differs")
        return self


class QualifiedRegistryIdentity(FrozenModel):
    registry_id: str
    registry_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_completeness_qualification_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    current_manifest_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class TaskAdmissionProjectionAuthority(FrozenModel):
    qualified_registry_consumed: Literal[True]
    admission_transcript_structurally_validated: Literal[True]
    task_admission_evidence_source_qualified: Literal[False]
    consumer_task_package_files_read: Literal[0]
    consumer_private_task_files_read: Literal[0]
    consumer_oracle_or_reference_patch_fields_read: Literal[0]
    r16_row_outcomes_or_traces_read: Literal[0]
    network_calls: Literal[0]
    docker_calls: Literal[0]
    provider_calls: Literal[0]
    evaluator_calls: Literal[0]
    agent_runs: Literal[0]
    added_model_cost_usd: Literal[0]
    offline_admission_projection_created: Literal[True]
    task_admission_authorized: Literal[False]
    fresh_task_panel_materialized: Literal[False]
    full_experiment_preregistered: Literal[False]
    candidate_created: Literal[False]
    approval_granted: Literal[False]
    execution_authorized: Literal[False]
    official_analysis_authorized: Literal[False]
    memory_effect_claim_authorized: Literal[False]


class FreshTaskAdmissionProjection(FrozenModel):
    schema_version: Literal[SCHEMA_VERSION]
    projection_id: str = Field(pattern=r"^lean-fresh-task-admission-[a-z0-9-]+-v1$")
    status: Literal[
        "OFFLINE_TASK_ADMISSION_PROJECTION_COMPLETE_UNQUALIFIED",
        "OFFLINE_TASK_ADMISSION_PROJECTION_STOPPED_INSUFFICIENT_UNQUALIFIED",
        "OFFLINE_TASK_ADMISSION_PROJECTION_STOPPED_CONFOUNDED_UNQUALIFIED",
    ]
    qualified_registry_identity: QualifiedRegistryIdentity
    admission_queue_policy: AdmissionQueuePolicy
    decisions: tuple[AdmissionDecisionRow, ...]
    attempted_candidate_count: int = Field(ge=0)
    accepted_same_repository_count: int = Field(ge=0, le=6)
    accepted_cross_repository_count: int = Field(ge=0, le=6)
    rejected_candidate_count: int = Field(ge=0)
    confounded_candidate_count: int = Field(ge=0, le=1)
    complete_panel_shape_present: bool
    decision_transcript_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    accepted_task_identity_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authority: TaskAdmissionProjectionAuthority
    next_gate: Literal[
        "source-qualify-the-task-admission-producer-and-replay-the-exact-transcript-before-panel-materialization"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("decisions", mode="before")
    @classmethod
    def freeze_decisions(cls, value: Any) -> Any:
        if isinstance(value, list):
            return tuple(value)
        return value

    @field_validator(
        "attempted_candidate_count",
        "accepted_same_repository_count",
        "accepted_cross_repository_count",
        "rejected_candidate_count",
        "confounded_candidate_count",
        mode="before",
    )
    @classmethod
    def require_exact_counts(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("admission projection counts must be JSON integers")
        return value

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        if self.attempted_candidate_count != len(self.decisions):
            raise ValueError("admission attempted count differs")
        same = sum(row.selected_role == "core-same-repo" for row in self.decisions)
        cross = sum(row.selected_role == "core-cross-repo" for row in self.decisions)
        rejected = sum(row.decision == "rejected" for row in self.decisions)
        confounded = sum(row.decision == "confounded" for row in self.decisions)
        if (
            self.accepted_same_repository_count != same
            or self.accepted_cross_repository_count != cross
            or self.rejected_candidate_count != rejected
            or self.confounded_candidate_count != confounded
        ):
            raise ValueError("admission projection decision counts differ")
        complete = same == 6 and cross == 6 and confounded == 0
        if self.complete_panel_shape_present != complete:
            raise ValueError("admission complete-panel shape differs")
        expected_status = (
            "OFFLINE_TASK_ADMISSION_PROJECTION_COMPLETE_UNQUALIFIED"
            if complete
            else (
                "OFFLINE_TASK_ADMISSION_PROJECTION_STOPPED_CONFOUNDED_UNQUALIFIED"
                if confounded == 1
                else "OFFLINE_TASK_ADMISSION_PROJECTION_STOPPED_INSUFFICIENT_UNQUALIFIED"
            )
        )
        if self.status != expected_status:
            raise ValueError("admission projection status differs")
        expected_transcript_hash = sha256_json(
            [row.model_dump(mode="json") for row in self.decisions]
        )
        if self.decision_transcript_hash != expected_transcript_hash:
            raise ValueError("admission decision transcript hash differs")
        accepted = [
            {
                "canonical_public_instance_id": row.canonical_public_instance_id,
                "upstream_repository": row.upstream_repository,
                "selected_role": row.selected_role,
                "task_package_binding": row.task_package_binding.model_dump(mode="json"),
                "solution_lineage_id": row.solution_lineage_id,
            }
            for row in self.decisions
            if row.decision == "accepted" and row.task_package_binding is not None
        ]
        if self.accepted_task_identity_hash != sha256_json(accepted):
            raise ValueError("accepted task identity hash differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("fresh task admission projection content hash differs")
        return self


def admission_evidence(**body: Any) -> AdmissionAuditEvidence:
    """Build a canonically self-hashed admission audit record."""

    if "evidence_hash" in body:
        raise FreshTaskAdmissionError("admission evidence input must exclude evidence_hash")
    hashed = {
        key: value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        for key, value in body.items()
    }
    return AdmissionAuditEvidence(**body, evidence_hash=sha256_json(hashed))


def admission_attempt(**body: Any) -> AdmissionAttempt:
    """Build a canonically self-hashed queue attempt."""

    if "attempt_hash" in body:
        raise FreshTaskAdmissionError("admission attempt input must exclude attempt_hash")
    hashed = {
        key: value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        for key, value in body.items()
    }
    return AdmissionAttempt(**body, attempt_hash=sha256_json(hashed))


def _registry_identity(registry: QualifiedFreshCandidateRegistry) -> QualifiedRegistryIdentity:
    qualification_hash = registry.source_completeness_qualification_binding.content_hash
    if qualification_hash is None:
        raise FreshTaskAdmissionError("qualified registry lacks qualification content identity")
    return QualifiedRegistryIdentity(
        registry_id=registry.registry_id,
        registry_content_hash=registry.content_hash,
        source_completeness_qualification_content_hash=qualification_hash,
        source_revision=registry.projection.source_revision,
        current_manifest_file_sha256=registry.projection.current_manifest_binding.file_sha256,
    )


def _first_audit_failure(
    evidence: AdmissionAuditEvidence,
    *,
    manifest_file_sha256: str,
    accepted_identity: dict[str, set[Any]],
) -> RejectionCode | None:
    if evidence.difficulty_tier not in {"medium", "hard"}:
        return "below-medium-difficulty-audit"
    if evidence.official_reference_pass_count < 3:
        return "reference-pass-count-insufficient"
    if evidence.rejected_bad_patch_count < 8:
        return "bad-patch-rejection-count-insufficient"
    if not (evidence.base_visible_verdict == "PASS" and evidence.base_hidden_verdict == "FAIL"):
        return "base-visible-hidden-contract-failed"
    if not all(
        verdict == "PASS"
        for verdict in (
            evidence.reference_visible_verdict,
            evidence.reference_hidden_verdict,
            evidence.reference_scope_verdict,
            evidence.reference_safety_verdict,
        )
    ):
        return "reference-verdict-bundle-failed"
    package = evidence.task_package_binding
    if package is None:
        return "task-binding-incomplete"
    identity = evidence.remaining_identity_audit
    if identity is None or not (
        identity.comparison_manifest_file_sha256 == manifest_file_sha256
        and identity.task_id_and_version_disjoint
        and identity.solution_lineage_disjoint
        and identity.public_spec_hash_disjoint
        and identity.private_spec_hash_disjoint
    ):
        return "remaining-identity-overlap"
    identity_values: dict[str, Any] = {
        "task_id_version": (package.task_id, package.task_version),
        "task_path": package.task_path,
        "solution_lineage": identity.solution_lineage_id,
        "spec_hash": package.public_spec_sha256,
        "private_spec_hash": package.private_spec_sha256,
    }
    if any(value in accepted_identity[name] for name, value in identity_values.items()):
        return "remaining-identity-overlap"
    if not evidence.license_compatible:
        return "license-incompatible"
    return None


def _decision(
    attempt: AdmissionAttempt,
    *,
    rejection_code: RejectionCode | None,
    accepted: bool,
) -> AdmissionDecisionRow:
    if attempt.evidence.confound_code is not None:
        decision = "confounded"
        selected_role = None
        package = None
        lineage = None
        rejection_code = None
    elif accepted:
        decision = "accepted"
        selected_role = "core-same-repo" if attempt.stratum == "same" else "core-cross-repo"
        package = attempt.evidence.task_package_binding
        identity = attempt.evidence.remaining_identity_audit
        assert package is not None and identity is not None
        lineage = identity.solution_lineage_id
    else:
        decision = "rejected"
        selected_role = None
        package = None
        lineage = None
        if rejection_code is None:
            raise FreshTaskAdmissionError("rejected admission decision lacks a typed code")
    body: dict[str, Any] = {
        "sequence": attempt.sequence,
        "stratum": attempt.stratum,
        "same_repository_target": attempt.same_repository_target,
        "queue_position": attempt.queue_position,
        "canonical_public_instance_id": attempt.canonical_public_instance_id,
        "upstream_repository": attempt.upstream_repository,
        "ranking_hash": attempt.ranking_hash,
        "public_row_hash": attempt.public_row_hash,
        "evidence_hash": attempt.evidence.evidence_hash,
        "decision": decision,
        "rejection_code": rejection_code,
        "confound_code": attempt.evidence.confound_code,
        "selected_role": selected_role,
        "task_package_binding": package,
        "solution_lineage_id": lineage,
    }
    hashed = {
        key: value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        for key, value in body.items()
    }
    return AdmissionDecisionRow(**body, decision_hash=sha256_json(hashed))


def _validate_attempt_binding(
    attempt: AdmissionAttempt,
    candidate: RankedCandidate,
    *,
    sequence: int,
    stratum: Literal["same", "cross"],
    target: str | None,
    position: int,
) -> None:
    expected = (
        sequence,
        stratum,
        target,
        position,
        candidate.canonical_public_instance_id,
        candidate.upstream_repository,
        candidate.ranking_hash,
        candidate.public_row_hash,
    )
    actual = (
        attempt.sequence,
        attempt.stratum,
        attempt.same_repository_target,
        attempt.queue_position,
        attempt.canonical_public_instance_id,
        attempt.upstream_repository,
        attempt.ranking_hash,
        attempt.public_row_hash,
    )
    if actual != expected:
        raise FreshTaskAdmissionError("admission attempt skips or reorders the frozen queue")


def _authority() -> TaskAdmissionProjectionAuthority:
    return TaskAdmissionProjectionAuthority(
        qualified_registry_consumed=True,
        admission_transcript_structurally_validated=True,
        task_admission_evidence_source_qualified=False,
        consumer_task_package_files_read=0,
        consumer_private_task_files_read=0,
        consumer_oracle_or_reference_patch_fields_read=0,
        r16_row_outcomes_or_traces_read=0,
        network_calls=0,
        docker_calls=0,
        provider_calls=0,
        evaluator_calls=0,
        agent_runs=0,
        added_model_cost_usd=0,
        offline_admission_projection_created=True,
        task_admission_authorized=False,
        fresh_task_panel_materialized=False,
        full_experiment_preregistered=False,
        candidate_created=False,
        approval_granted=False,
        execution_authorized=False,
        official_analysis_authorized=False,
        memory_effect_claim_authorized=False,
    )


def project_fresh_task_admission(
    registry: QualifiedFreshCandidateRegistry,
    attempts: tuple[AdmissionAttempt, ...] | list[AdmissionAttempt],
) -> FreshTaskAdmissionProjection:
    """Derive the exact queue decisions without reading task or runtime files."""

    frozen_attempts = tuple(attempts)
    identity = _registry_identity(registry)
    projection = registry.projection
    if not projection.public_pool_sufficient_for_admission:
        if frozen_attempts:
            raise FreshTaskAdmissionError("insufficient public pool cannot enter task admission")
        return _projection(
            registry=registry,
            identity=identity,
            decisions=(),
        )
    if registry.status != "QUALIFIED_PUBLIC_REGISTRY_TASK_ADMISSION_PENDING":
        raise FreshTaskAdmissionError("qualified registry is not pending task admission")

    candidates = {
        candidate.canonical_public_instance_id: candidate
        for candidate in projection.ranked_candidates
    }
    accepted_identity: dict[str, set[Any]] = {
        "task_id_version": set(),
        "task_path": set(),
        "solution_lineage": set(),
        "spec_hash": set(),
        "private_spec_hash": set(),
    }
    decisions: list[AdmissionDecisionRow] = []
    cursor = 0
    stopped = False

    def consume(
        candidate_id: str, *, stratum: Literal["same", "cross"], target: str | None, position: int
    ) -> AdmissionDecisionRow:
        nonlocal cursor
        if cursor >= len(frozen_attempts):
            raise FreshTaskAdmissionError("admission transcript ends before the queue decision")
        candidate = candidates[candidate_id]
        attempt = frozen_attempts[cursor]
        _validate_attempt_binding(
            attempt,
            candidate,
            sequence=cursor + 1,
            stratum=stratum,
            target=target,
            position=position,
        )
        cursor += 1
        if attempt.evidence.confound_code is not None:
            return _decision(attempt, rejection_code=None, accepted=False)
        rejection = _first_audit_failure(
            attempt.evidence,
            manifest_file_sha256=identity.current_manifest_file_sha256,
            accepted_identity=accepted_identity,
        )
        return _decision(attempt, rejection_code=rejection, accepted=rejection is None)

    for target in SAME_REPOSITORY_TARGETS:
        accepted_target = False
        for position, candidate_id in enumerate(projection.same_repository_queues[target], start=1):
            row = consume(candidate_id, stratum="same", target=target, position=position)
            decisions.append(row)
            if row.decision == "confounded":
                stopped = True
                break
            if row.decision == "accepted":
                _record_accepted_identity(row, accepted_identity)
                accepted_target = True
                break
        if stopped or not accepted_target:
            stopped = True
            break

    if not stopped:
        accepted_cross_repositories: set[str] = set()
        for position, candidate_id in enumerate(projection.cross_repository_queue, start=1):
            row = consume(candidate_id, stratum="cross", target=None, position=position)
            if (
                row.decision == "accepted"
                and row.upstream_repository in accepted_cross_repositories
            ):
                attempt = frozen_attempts[cursor - 1]
                row = _decision(
                    attempt,
                    rejection_code="cross-repository-already-admitted",
                    accepted=False,
                )
            decisions.append(row)
            if row.decision == "confounded":
                stopped = True
                break
            if row.decision == "accepted":
                accepted_cross_repositories.add(row.upstream_repository)
                _record_accepted_identity(row, accepted_identity)
                if len(accepted_cross_repositories) == 6:
                    break
        if len(accepted_cross_repositories) != 6:
            stopped = True

    if cursor != len(frozen_attempts):
        raise FreshTaskAdmissionError("admission transcript continues after its terminal state")
    return _projection(
        registry=registry,
        identity=identity,
        decisions=tuple(decisions),
    )


def _record_accepted_identity(
    row: AdmissionDecisionRow,
    accepted_identity: dict[str, set[Any]],
) -> None:
    package = row.task_package_binding
    lineage = row.solution_lineage_id
    assert package is not None and lineage is not None
    accepted_identity["task_id_version"].add((package.task_id, package.task_version))
    accepted_identity["task_path"].add(package.task_path)
    accepted_identity["solution_lineage"].add(lineage)
    accepted_identity["spec_hash"].add(package.public_spec_sha256)
    accepted_identity["private_spec_hash"].add(package.private_spec_sha256)


def _projection(
    *,
    registry: QualifiedFreshCandidateRegistry,
    identity: QualifiedRegistryIdentity,
    decisions: tuple[AdmissionDecisionRow, ...],
) -> FreshTaskAdmissionProjection:
    same = sum(row.selected_role == "core-same-repo" for row in decisions)
    cross = sum(row.selected_role == "core-cross-repo" for row in decisions)
    rejected = sum(row.decision == "rejected" for row in decisions)
    confounded = sum(row.decision == "confounded" for row in decisions)
    complete = same == 6 and cross == 6 and confounded == 0
    status = (
        "OFFLINE_TASK_ADMISSION_PROJECTION_COMPLETE_UNQUALIFIED"
        if complete
        else (
            "OFFLINE_TASK_ADMISSION_PROJECTION_STOPPED_CONFOUNDED_UNQUALIFIED"
            if confounded == 1
            else "OFFLINE_TASK_ADMISSION_PROJECTION_STOPPED_INSUFFICIENT_UNQUALIFIED"
        )
    )
    accepted = [
        {
            "canonical_public_instance_id": row.canonical_public_instance_id,
            "upstream_repository": row.upstream_repository,
            "selected_role": row.selected_role,
            "task_package_binding": row.task_package_binding.model_dump(mode="json"),
            "solution_lineage_id": row.solution_lineage_id,
        }
        for row in decisions
        if row.decision == "accepted" and row.task_package_binding is not None
    ]
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "projection_id": registry.registry_id.replace(
            "lean-fresh-qualified-candidate-registry-",
            "lean-fresh-task-admission-",
            1,
        ),
        "status": status,
        "qualified_registry_identity": identity,
        "admission_queue_policy": registry.projection.admission_queue_policy,
        "decisions": decisions,
        "attempted_candidate_count": len(decisions),
        "accepted_same_repository_count": same,
        "accepted_cross_repository_count": cross,
        "rejected_candidate_count": rejected,
        "confounded_candidate_count": confounded,
        "complete_panel_shape_present": complete,
        "decision_transcript_hash": sha256_json([row.model_dump(mode="json") for row in decisions]),
        "accepted_task_identity_hash": sha256_json(accepted),
        "authority": _authority(),
        "next_gate": (
            "source-qualify-the-task-admission-producer-and-replay-the-exact-transcript-"
            "before-panel-materialization"
        ),
    }
    hashed = {
        key: (
            [item.model_dump(mode="json") for item in value]
            if key == "decisions"
            else value.model_dump(mode="json")
            if isinstance(value, BaseModel)
            else value
        )
        for key, value in body.items()
    }
    return FreshTaskAdmissionProjection(**body, content_hash=sha256_json(hashed))


def task_admission_projection_bytes(value: FreshTaskAdmissionProjection) -> bytes:
    return (
        json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
