"""Offline public causal-alternative contract for the post-V16 workflow.

This module deliberately has no runtime, tool-schema, or context-policy version.
It defines and qualifies the contract that a future opt-in runtime must satisfy
before it can restore a failed mutation family and admit another semantic edit.

The contract is task-generic.  A mechanism is represented by a public,
evidence-bound causal boundary, an ordered causal path, a mutation site, and a
general mutation-site rationale.  It never contains exception-specific fields,
task solutions, evaluator data, reference patches, or model reasoning.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.agent.workflow_candidate_binding_successor import (
    CandidateBindingNormalization,
    normalize_same_path_candidate_bindings,
)
from patchloop.agent.workflow_semantic_progress_successor import PublicSemanticProgressState
from patchloop.agent.workflow_successor_v2 import (
    CandidateFileEvidence,
    EligiblePlanEvidence,
    EligiblePlanEvidenceCatalog,
    _path_allowed,
)
from patchloop.contracts import EventType, PublicTask, RunEvent
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import safe_relative_path, sha256_json

CAUSAL_ALTERNATIVE_POLICY = "bounded-public-causal-alternative-gate-v1"
CAUSAL_MECHANISM_SCHEMA = "public-causal-mechanism-v1"
MUTATION_BASELINE_SCHEMA = "mutation-baseline-projection-v1"
MUTATION_BASELINE_RESTORE_SCHEMA = "mutation-baseline-restore-receipt-v1"
CAUSAL_ALTERNATIVE_PLAN_SCHEMA = "recorded-causal-alternative-plan-v1"
CAUSAL_ALTERNATIVE_CHECKPOINT_SCHEMA = "causal-alternative-admission-checkpoint-v1"
CAUSAL_ALTERNATIVE_INPUT_SCHEMA = "causal-alternative-input-contract-v1"

EvidenceId = Annotated[str, Field(pattern=r"^pev:[1-9][0-9]*$")]
Hash = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
PlanTrigger = Literal["initial", "check_failure", "review_correction"]


def _reject(reason_code: str, message: str) -> None:
    raise ContractError(message, details={"reason_codes": [reason_code]})


def _hashed(model: type[BaseModel], body: dict[str, Any]) -> Any:
    return model.model_validate({**body, "content_hash": sha256_json(body)})


def _normalized_public_text(value: str, *, field_name: str) -> str:
    if value != value.strip() or not value or "\x00" in value:
        raise ValueError(f"{field_name} must be trimmed public text")
    return value


class CausalSourceLocationInput(BaseModel):
    """One model-supplied location inside a fully visible public source read."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    read_evidence_id: EvidenceId
    symbol: str | None = Field(min_length=1, max_length=300)

    @field_validator("path")
    @classmethod
    def normalize_path(cls, value: str) -> str:
        normalized = safe_relative_path(value, field_name="causal source path")
        if normalized != value:
            raise ValueError("causal source path differs")
        return value

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str | None) -> str | None:
        if value is not None:
            return _normalized_public_text(value, field_name="causal symbol")
        return value

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.end_line < self.start_line:
            raise ValueError("causal source range differs")
        return self


class CausalPathStepInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    role: Literal[
        "causal_boundary",
        "intermediate",
        "mutation_site",
        "boundary_and_mutation_site",
    ]
    location: CausalSourceLocationInput
    observation: str = Field(min_length=1, max_length=1_000)
    relationship_to_next: str | None = Field(min_length=1, max_length=1_000)

    @field_validator("observation")
    @classmethod
    def normalize_observation(cls, value: str) -> str:
        return _normalized_public_text(value, field_name="causal observation")

    @field_validator("relationship_to_next")
    @classmethod
    def normalize_relationship(cls, value: str | None) -> str | None:
        if value is not None:
            return _normalized_public_text(value, field_name="causal relationship")
        return value


class PublicCausalMechanismInput(BaseModel):
    """Generic model-facing mechanism shape used by every task family."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    summary: str = Field(min_length=1, max_length=2_000)
    causal_path: list[CausalPathStepInput] = Field(min_length=1, max_length=8)
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

    @model_validator(mode="after")
    def validate_path_shape(self) -> Self:
        roles = tuple(step.role for step in self.causal_path)
        if len(roles) == 1:
            if roles != ("boundary_and_mutation_site",):
                raise ValueError("single-step causal path role differs")
        elif (
            roles[0] != "causal_boundary"
            or roles[-1] != "mutation_site"
            or any(role != "intermediate" for role in roles[1:-1])
        ):
            raise ValueError("causal path roles differ")
        if any(step.relationship_to_next is None for step in self.causal_path[:-1]):
            raise ValueError("non-final causal path step lacks a relationship")
        if self.causal_path[-1].relationship_to_next is not None:
            raise ValueError("final causal path step unexpectedly has a relationship")
        return self


class EvidenceBoundSourceLocation(CausalSourceLocationInput):
    coverage_key: Hash

    @model_validator(mode="after")
    def validate_coverage_key(self) -> Self:
        expected = sha256_json(
            {
                "schema_version": "public-source-coverage-key-v1",
                "path": self.path,
                "start_line": self.start_line,
                "end_line": self.end_line,
            }
        )
        if self.coverage_key != expected:
            raise ValueError("causal source coverage key differs")
        return self


class EvidenceBoundCausalPathStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    ordinal: int = Field(ge=0, le=7)
    role: Literal[
        "causal_boundary",
        "intermediate",
        "mutation_site",
        "boundary_and_mutation_site",
    ]
    location: EvidenceBoundSourceLocation
    observation: str = Field(min_length=1, max_length=1_000)
    relationship_to_next: str | None = Field(default=None, min_length=1, max_length=1_000)


class PublicCausalMechanism(BaseModel):
    """Durable public descriptor; prose is not used to decide distinctness."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["public-causal-mechanism-v1"]
    run_id: str = Field(min_length=1)
    worktree_diff_hash: Hash
    summary: str = Field(min_length=1, max_length=2_000)
    causal_boundary: EvidenceBoundSourceLocation
    causal_path: tuple[EvidenceBoundCausalPathStep, ...] = Field(min_length=1, max_length=8)
    mutation_site: EvidenceBoundSourceLocation
    mutation_site_rationale: str = Field(min_length=1, max_length=2_000)
    expected_observable_effect: str = Field(min_length=1, max_length=2_000)
    falsification_condition: str = Field(min_length=1, max_length=2_000)
    mechanism_family_key: Hash
    source_coverage_keys: tuple[Hash, ...] = Field(min_length=1, max_length=8)
    source_evidence_ids: tuple[EvidenceId, ...] = Field(min_length=1, max_length=8)
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
        path_keys = tuple(step.location.coverage_key for step in self.causal_path)
        roles = tuple(step.role for step in self.causal_path)
        roles_valid = (
            roles == ("boundary_and_mutation_site",)
            if len(roles) == 1
            else roles[0] == "causal_boundary"
            and roles[-1] == "mutation_site"
            and all(role == "intermediate" for role in roles[1:-1])
        )
        if (
            tuple(step.ordinal for step in self.causal_path) != tuple(range(len(self.causal_path)))
            or self.causal_path[0].location != self.causal_boundary
            or self.causal_path[-1].location != self.mutation_site
            or not roles_valid
            or len(set(path_keys)) != len(path_keys)
            or self.source_coverage_keys != path_keys
            or self.source_evidence_ids
            != tuple(dict.fromkeys(step.location.read_evidence_id for step in self.causal_path))
        ):
            raise ValueError("causal mechanism path binding differs")
        expected_family = sha256_json(
            {
                "schema_version": "public-causal-mechanism-family-v1",
                "causal_boundary_coverage_key": self.causal_boundary.coverage_key,
                "causal_path_coverage_keys": path_keys,
                "mutation_site_coverage_key": self.mutation_site.coverage_key,
            }
        )
        if self.mechanism_family_key != expected_family:
            raise ValueError("causal mechanism family key differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("causal mechanism content hash differs")
        return self


class CausalMechanismHistoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    revision_index: int = Field(ge=0, le=3)
    plan_hash: Hash
    parent_plan_hash: Hash | None = None
    trigger: PlanTrigger
    mechanism: PublicCausalMechanism

    @model_validator(mode="after")
    def validate_entry(self) -> Self:
        if self.revision_index == 0:
            if self.parent_plan_hash is not None or self.trigger != "initial":
                raise ValueError("initial causal history entry differs")
        elif self.parent_plan_hash is None or self.trigger == "initial":
            raise ValueError("causal history revision binding differs")
        return self


class MutationBaselineProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["mutation-baseline-projection-v1"]
    policy_version: Literal["bounded-public-causal-alternative-gate-v1"]
    run_id: str = Field(min_length=1)
    check_id: str = Field(min_length=1)
    semantic_progress_state_hash: Hash
    failure_signature_hash: Hash
    failure_event_sequences: tuple[int, ...] = Field(min_length=2, max_length=4)
    failed_diff_hashes: tuple[Hash, ...] = Field(min_length=2, max_length=4)
    baseline_diff_hash: Hash
    current_failed_diff_hash: Hash
    first_mutation_prepared_sequence: int = Field(ge=1)
    first_mutation_applied_sequence: int = Field(ge=1)
    forward_action_ids: tuple[str, ...] = Field(min_length=1, max_length=4)
    forward_intent_hashes: tuple[Hash, ...] = Field(min_length=1, max_length=4)
    forward_diff_chain: tuple[Hash, ...] = Field(min_length=2, max_length=5)
    restore_action_ids: tuple[str, ...] = Field(min_length=1, max_length=4)
    restore_intent_hashes: tuple[Hash, ...] = Field(min_length=1, max_length=4)
    restore_required: Literal[True]
    append_only_failure_history_preserved: Literal[True]
    private_evidence_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: Hash

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        failure_positions = tuple(
            self.forward_diff_chain.index(item)
            for item in self.failed_diff_hashes
            if item in self.forward_diff_chain
        )
        if (
            self.first_mutation_prepared_sequence >= self.first_mutation_applied_sequence
            or self.first_mutation_applied_sequence >= self.failure_event_sequences[0]
            or tuple(sorted(set(self.failure_event_sequences))) != self.failure_event_sequences
            or len(self.failure_event_sequences) != len(self.failed_diff_hashes)
            or self.forward_diff_chain[0] != self.baseline_diff_hash
            or self.forward_diff_chain[-1] != self.current_failed_diff_hash
            or len(self.forward_diff_chain) != len(self.forward_action_ids) + 1
            or len(self.forward_intent_hashes) != len(self.forward_action_ids)
            or len(set(self.forward_action_ids)) != len(self.forward_action_ids)
            or self.restore_action_ids != tuple(reversed(self.forward_action_ids))
            or self.restore_intent_hashes != tuple(reversed(self.forward_intent_hashes))
            or self.current_failed_diff_hash == self.baseline_diff_hash
            or len(failure_positions) != len(self.failed_diff_hashes)
            or failure_positions != tuple(sorted(failure_positions))
            or any(position < 1 for position in failure_positions)
        ):
            raise ValueError("mutation baseline projection differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("mutation baseline projection hash differs")
        return self


class MutationBaselineRestoreReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["mutation-baseline-restore-receipt-v1"]
    policy_version: Literal["bounded-public-causal-alternative-gate-v1"]
    run_id: str = Field(min_length=1)
    baseline_projection_hash: Hash
    observed_before_diff_hash: Hash
    observed_after_diff_hash: Hash
    restored_action_ids: tuple[str, ...] = Field(min_length=1, max_length=4)
    restored_intent_hashes: tuple[Hash, ...] = Field(min_length=1, max_length=4)
    preserved_failure_event_sequences: tuple[int, ...] = Field(min_length=2, max_length=4)
    exact_restore_verified: Literal[True]
    append_only_events_deleted: Literal[False]
    provider_calls: Literal[0]
    visible_check_calls: Literal[0]
    content_hash: Hash

    @model_validator(mode="after")
    def validate_receipt_hash(self) -> Self:
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("mutation baseline restore receipt hash differs")
        return self


class CausalContrast(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    prior_mechanism_hash: Hash
    alternative_mechanism_hash: Hash
    prior_boundary_coverage_key: Hash
    alternative_boundary_coverage_key: Hash
    exhausted_boundary_coverage_keys: tuple[Hash, ...] = Field(min_length=1, max_length=4)
    alternative_boundary_is_non_exhausted: Literal[True]
    mechanism_family_changed: Literal[True]
    prose_only_relabel_accepted: Literal[False]

    @model_validator(mode="after")
    def validate_contrast(self) -> Self:
        if (
            len(set(self.exhausted_boundary_coverage_keys))
            != len(self.exhausted_boundary_coverage_keys)
            or self.prior_boundary_coverage_key not in self.exhausted_boundary_coverage_keys
            or self.alternative_boundary_coverage_key in self.exhausted_boundary_coverage_keys
            or self.alternative_boundary_coverage_key == self.prior_boundary_coverage_key
        ):
            raise ValueError("causal contrast differs")
        return self


class RecordedCausalAlternativePlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["recorded-causal-alternative-plan-v1"]
    policy_version: Literal["bounded-public-causal-alternative-gate-v1"]
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    task_version: int = Field(ge=1)
    public_task_hash: Hash
    worktree_diff_hash: Hash
    observation_status: Literal["visible_check_failed"]
    hypothesis: str = Field(min_length=1, max_length=2_000)
    foundation_evidence: tuple[EligiblePlanEvidence, ...] = Field(min_length=1, max_length=20)
    supporting_evidence: tuple[EligiblePlanEvidence, ...] = Field(max_length=20)
    candidate_files: tuple[CandidateFileEvidence, ...] = Field(min_length=1, max_length=20)
    intended_change: str = Field(min_length=1, max_length=2_000)
    expected_behavior: str = Field(min_length=1, max_length=2_000)
    unknowns: tuple[str, ...] = Field(max_length=20)
    planned_check_ids: tuple[str, ...] = Field(min_length=1)
    evidence_catalog_hash: Hash
    revision_index: int = Field(ge=1, le=3)
    parent_plan_hash: Hash
    trigger_check_id: str = Field(min_length=1)
    trigger_failure_event_sequences: tuple[int, ...] = Field(min_length=2, max_length=4)
    semantic_progress_state_hash: Hash
    mutation_baseline_projection_hash: Hash
    mutation_baseline_restore_receipt_hash: Hash
    prior_hypothesis_disposition: Literal["rejected"]
    prior_causal_mechanism: PublicCausalMechanism
    alternative_causal_mechanism: PublicCausalMechanism
    causal_contrast: CausalContrast
    candidate_binding_normalization_hash: Hash
    candidate_binding_normalization: CandidateBindingNormalization
    public_evidence_only: Literal[True]
    hidden_evidence_used: Literal[False]
    private_evidence_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: Hash

    @field_validator("hypothesis", "intended_change", "expected_behavior")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _normalized_public_text(value, field_name="causal alternative plan text")

    @field_validator("unknowns")
    @classmethod
    def normalize_unknowns(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item or item != item.strip() or len(item) > 1_000 for item in values):
            raise ValueError("causal alternative plan unknowns differ")
        return values

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        foundation_ids = {item.evidence_id for item in self.foundation_evidence}
        normalized_candidates = tuple(
            (item.path, item.read_evidence_id) for item in self.candidate_files
        )
        recorded_candidates = tuple(
            (item.path, item.selected_read_evidence_id)
            for item in self.candidate_binding_normalization.path_bindings
        )
        if (
            self.worktree_diff_hash != self.alternative_causal_mechanism.worktree_diff_hash
            or self.prior_causal_mechanism.content_hash != self.causal_contrast.prior_mechanism_hash
            or self.alternative_causal_mechanism.content_hash
            != self.causal_contrast.alternative_mechanism_hash
            or self.planned_check_ids[0] != self.trigger_check_id
            or len(set(self.planned_check_ids)) != len(self.planned_check_ids)
            or len({item.path for item in self.candidate_files}) != len(self.candidate_files)
            or any(
                item.role != "foundation"
                or item.run_id != self.run_id
                or item.worktree_diff_hash != self.worktree_diff_hash
                for item in self.foundation_evidence
            )
            or any(
                item.role != "support"
                or item.run_id != self.run_id
                or item.worktree_diff_hash != self.worktree_diff_hash
                for item in self.supporting_evidence
            )
            or not set(self.alternative_causal_mechanism.source_evidence_ids).issubset(
                foundation_ids
            )
            or self.causal_contrast.prior_boundary_coverage_key
            != self.prior_causal_mechanism.causal_boundary.coverage_key
            or self.causal_contrast.alternative_boundary_coverage_key
            != self.alternative_causal_mechanism.causal_boundary.coverage_key
            or self.prior_causal_mechanism.mechanism_family_key
            == self.alternative_causal_mechanism.mechanism_family_key
            or self.candidate_binding_normalization_hash
            != self.candidate_binding_normalization.content_hash
            or self.candidate_binding_normalization.run_id != self.run_id
            or self.candidate_binding_normalization.worktree_diff_hash != self.worktree_diff_hash
            or normalized_candidates != recorded_candidates
        ):
            raise ValueError("causal alternative plan binding differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("causal alternative plan hash differs")
        return self


class CausalAlternativeAdmissionCheckpoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["causal-alternative-admission-checkpoint-v1"]
    policy_version: Literal["bounded-public-causal-alternative-gate-v1"]
    gate_id: Hash
    rejection_count: int = Field(ge=0, le=2)
    recovery_remaining: int = Field(ge=0, le=1)
    status: Literal["active", "accepted", "terminal"]
    accepted_plan_hash: Hash | None = None
    terminal_reason: Literal["causal_alternative_admission_repeated"] | None = None
    last_reason_codes: tuple[str, ...] = Field(max_length=10)
    provider_dispatch_after_terminal: Literal[False]
    content_hash: Hash

    @model_validator(mode="after")
    def validate_checkpoint(self) -> Self:
        if self.recovery_remaining != (1 if self.rejection_count == 0 else 0):
            raise ValueError("causal alternative recovery count differs")
        if self.status == "active":
            if self.accepted_plan_hash is not None or self.terminal_reason is not None:
                raise ValueError("active causal alternative checkpoint differs")
        elif self.status == "accepted":
            if self.accepted_plan_hash is None or self.terminal_reason is not None:
                raise ValueError("accepted causal alternative checkpoint differs")
        elif (
            self.rejection_count != 2
            or self.accepted_plan_hash is not None
            or self.terminal_reason != "causal_alternative_admission_repeated"
        ):
            raise ValueError("terminal causal alternative checkpoint differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("causal alternative checkpoint hash differs")
        return self


class CausalAlternativeInputContract(BaseModel):
    """Prospective model-facing schema; it is not an activated tool surface."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["causal-alternative-input-contract-v1"]
    policy_version: Literal["bounded-public-causal-alternative-gate-v1"]
    evidence_catalog_hash: Hash
    prior_causal_mechanism_hash: Hash
    parameters: dict[str, Any]
    parameter_schema_hash: Hash
    task_specific_field_names: tuple[()] = ()
    runtime_surface_activated: Literal[False]
    content_hash: Hash

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        if (
            self.parameter_schema_hash != sha256_json(self.parameters)
            or "why_exception_reaches_mutation_site" in str(self.parameters)
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("causal alternative input contract differs")
        return self


def project_causal_alternative_input_contract(
    *,
    catalog: EligiblePlanEvidenceCatalog,
    prior_causal_mechanism_hash: str,
) -> CausalAlternativeInputContract:
    """Project the deterministic generic JSON shape for a future reset request."""

    source_items = tuple(
        item
        for item in catalog.items
        if item.kind == "source_read" and item.role == "foundation" and item.source is not None
    )
    if not source_items:
        _reject(
            "causal_source_evidence_unavailable",
            "causal alternative input lacks public source evidence",
        )
    source_ids = [item.evidence_id for item in source_items]
    source_paths = sorted({item.source.path for item in source_items if item.source is not None})
    support_ids = [item.evidence_id for item in catalog.items if item.role == "support"]
    support_item_schema = (
        {"type": "string", "enum": support_ids} if support_ids else {"type": "string"}
    )
    location = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "enum": source_paths},
            "start_line": {"type": "integer", "minimum": 1},
            "end_line": {"type": "integer", "minimum": 1},
            "read_evidence_id": {"type": "string", "enum": source_ids},
            "symbol": {"type": ["string", "null"], "minLength": 1, "maxLength": 300},
        },
        "required": ["path", "start_line", "end_line", "read_evidence_id", "symbol"],
        "additionalProperties": False,
    }
    path_step = {
        "type": "object",
        "properties": {
            "role": {
                "type": "string",
                "enum": [
                    "causal_boundary",
                    "intermediate",
                    "mutation_site",
                    "boundary_and_mutation_site",
                ],
            },
            "location": location,
            "observation": {"type": "string", "minLength": 1, "maxLength": 1_000},
            "relationship_to_next": {
                "type": ["string", "null"],
                "minLength": 1,
                "maxLength": 1_000,
            },
        },
        "required": ["role", "location", "observation", "relationship_to_next"],
        "additionalProperties": False,
    }
    mechanism = {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "minLength": 1, "maxLength": 2_000},
            "causal_path": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": path_step,
            },
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
            "causal_path",
            "mutation_site_rationale",
            "expected_observable_effect",
            "falsification_condition",
        ],
        "additionalProperties": False,
    }
    parameters = {
        "type": "object",
        "properties": {
            "observation_status": {"type": "string", "enum": ["visible_check_failed"]},
            "hypothesis": {"type": "string", "minLength": 1, "maxLength": 2_000},
            "foundation_evidence_ids": {
                "type": "array",
                "minItems": 1,
                "maxItems": 20,
                "items": {"type": "string", "enum": source_ids},
            },
            "supporting_evidence_ids": {
                "type": "array",
                "maxItems": 20 if support_ids else 0,
                "items": support_item_schema,
            },
            "candidate_files": {
                "type": "array",
                "minItems": 1,
                "maxItems": 20,
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "enum": source_paths},
                        "read_evidence_id": {"type": "string", "enum": source_ids},
                    },
                    "required": ["path", "read_evidence_id"],
                    "additionalProperties": False,
                },
            },
            "intended_change": {"type": "string", "minLength": 1, "maxLength": 2_000},
            "expected_behavior": {"type": "string", "minLength": 1, "maxLength": 2_000},
            "unknowns": {
                "type": "array",
                "maxItems": 20,
                "items": {"type": "string", "minLength": 1, "maxLength": 1_000},
            },
            "prior_causal_mechanism_hash": {
                "type": "string",
                "enum": [prior_causal_mechanism_hash],
            },
            "alternative_causal_mechanism": mechanism,
        },
        "required": [
            "observation_status",
            "hypothesis",
            "foundation_evidence_ids",
            "supporting_evidence_ids",
            "candidate_files",
            "intended_change",
            "expected_behavior",
            "unknowns",
            "prior_causal_mechanism_hash",
            "alternative_causal_mechanism",
        ],
        "additionalProperties": False,
    }
    body = {
        "schema_version": CAUSAL_ALTERNATIVE_INPUT_SCHEMA,
        "policy_version": CAUSAL_ALTERNATIVE_POLICY,
        "evidence_catalog_hash": catalog.content_hash,
        "prior_causal_mechanism_hash": prior_causal_mechanism_hash,
        "parameters": parameters,
        "parameter_schema_hash": sha256_json(parameters),
        "task_specific_field_names": (),
        "runtime_surface_activated": False,
    }
    return _hashed(CausalAlternativeInputContract, body)


def _coverage_key(location: CausalSourceLocationInput) -> str:
    return sha256_json(
        {
            "schema_version": "public-source-coverage-key-v1",
            "path": location.path,
            "start_line": location.start_line,
            "end_line": location.end_line,
        }
    )


def _bind_location(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
    by_id: dict[str, EligiblePlanEvidence],
    foundation_ids: set[str],
    location: CausalSourceLocationInput,
) -> EvidenceBoundSourceLocation:
    evidence = by_id.get(location.read_evidence_id)
    if (
        evidence is None
        or evidence.evidence_id not in foundation_ids
        or evidence.kind != "source_read"
        or evidence.role != "foundation"
        or evidence.run_id != catalog.run_id
        or evidence.worktree_diff_hash != catalog.worktree_diff_hash
        or evidence.source is None
        or evidence.source.path != location.path
        or not _path_allowed(task, location.path)
    ):
        _reject(
            "causal_source_binding_invalid",
            "causal mechanism location lacks current public source evidence",
        )
    if not any(
        visible_start <= location.start_line <= location.end_line <= visible_end
        for visible_start, visible_end in evidence.source.visible_ranges
    ):
        _reject(
            "causal_source_range_not_visible",
            "causal mechanism location is not fully visible to the model",
        )
    return EvidenceBoundSourceLocation(
        **location.model_dump(mode="python"),
        coverage_key=_coverage_key(location),
    )


def validate_public_causal_mechanism(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
    foundation_evidence_ids: list[str] | tuple[str, ...],
    raw_mechanism: dict[str, Any],
) -> PublicCausalMechanism:
    """Validate one generic mechanism against exact current visible source ranges."""

    try:
        submitted = PublicCausalMechanismInput.model_validate(raw_mechanism)
    except ValueError as exc:
        _reject("causal_mechanism_shape_invalid", "causal mechanism shape differs")
        raise AssertionError from exc
    by_id = {item.evidence_id: item for item in catalog.items}
    if not foundation_evidence_ids or any(
        type(item) is not str or item not in by_id for item in foundation_evidence_ids
    ):
        _reject("causal_foundation_evidence_invalid", "causal foundation evidence differs")
    foundation_ids = set(foundation_evidence_ids)

    def bind(location: CausalSourceLocationInput) -> EvidenceBoundSourceLocation:
        return _bind_location(
            task=task,
            catalog=catalog,
            by_id=by_id,
            foundation_ids=foundation_ids,
            location=location,
        )

    steps = tuple(
        EvidenceBoundCausalPathStep(
            ordinal=index,
            role=step.role,
            location=bind(step.location),
            observation=step.observation,
            relationship_to_next=step.relationship_to_next,
        )
        for index, step in enumerate(submitted.causal_path)
    )
    boundary = steps[0].location
    mutation_site = steps[-1].location
    keys = tuple(step.location.coverage_key for step in steps)
    if len(set(keys)) != len(keys):
        _reject("causal_path_repeats_location", "causal path repeats one source location")
    family = sha256_json(
        {
            "schema_version": "public-causal-mechanism-family-v1",
            "causal_boundary_coverage_key": boundary.coverage_key,
            "causal_path_coverage_keys": keys,
            "mutation_site_coverage_key": mutation_site.coverage_key,
        }
    )
    body = {
        "schema_version": CAUSAL_MECHANISM_SCHEMA,
        "run_id": catalog.run_id,
        "worktree_diff_hash": catalog.worktree_diff_hash,
        "summary": submitted.summary,
        "causal_boundary": boundary.model_dump(mode="python"),
        "causal_path": tuple(step.model_dump(mode="python") for step in steps),
        "mutation_site": mutation_site.model_dump(mode="python"),
        "mutation_site_rationale": submitted.mutation_site_rationale,
        "expected_observable_effect": submitted.expected_observable_effect,
        "falsification_condition": submitted.falsification_condition,
        "mechanism_family_key": family,
        "source_coverage_keys": keys,
        "source_evidence_ids": tuple(
            dict.fromkeys(step.location.read_evidence_id for step in steps)
        ),
        "public_current_diff_source_only": True,
        "symbol_text_used_for_admission": False,
        "prose_used_for_distinctness": False,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(PublicCausalMechanism, body)


def _prepared_for_action(events: tuple[RunEvent, ...], action_id: str, before: int) -> RunEvent:
    matches = [
        event
        for event in events
        if event.sequence < before
        and event.type == EventType.PATCH_PREPARED
        and event.correlation_id == action_id
        and event.payload.get("schema_version") == "patch-mutation-intent-v1"
    ]
    if len(matches) != 1:
        raise RecoveryError("mutation baseline patch preparation binding differs")
    return matches[0]


def project_mutation_baseline(
    *,
    semantic_progress_state: PublicSemanticProgressState,
    events: tuple[RunEvent, ...] | list[RunEvent],
) -> MutationBaselineProjection:
    """Bind the exact reversible mutation chain that produced the repeated failure."""

    state = semantic_progress_state
    event_tuple = tuple(events)
    if (
        not state.semantic_reset_required
        or state.same_signature_failed_diff_count < 2
        or any(event.run_id != state.run_id for event in event_tuple)
    ):
        raise ContractError("mutation baseline requires one exact semantic reset state")
    first_failure_sequence = state.failure_event_sequences[0]
    current_failure_sequence = state.failure_event_sequences[-1]
    first_failed_diff = state.failed_diff_hashes[0]
    current_failed_diff = state.failed_diff_hashes[-1]
    applied = [
        event
        for event in event_tuple
        if event.type == EventType.PATCH_APPLIED
        and event.sequence < first_failure_sequence
        and event.payload.get("worktree_diff_hash") == first_failed_diff
    ]
    if not applied:
        raise RecoveryError("mutation baseline lacks the first failed mutation")
    first_applied = applied[-1]
    if not isinstance(first_applied.correlation_id, str) or not first_applied.correlation_id:
        raise RecoveryError("mutation baseline action identity differs")
    chain_events = [
        event
        for event in event_tuple
        if event.type == EventType.PATCH_APPLIED
        and first_applied.sequence <= event.sequence < current_failure_sequence
    ]
    if not 1 <= len(chain_events) <= 4:
        raise RecoveryError("mutation baseline chain exceeds the correction envelope")
    action_ids: list[str] = []
    intent_hashes: list[str] = []
    diff_chain: list[str] = []
    first_prepared: RunEvent | None = None
    expected_baseline: str | None = None
    for applied_event in chain_events:
        action_id = applied_event.correlation_id
        if not isinstance(action_id, str) or not action_id or action_id in action_ids:
            raise RecoveryError("mutation baseline action chain differs")
        prepared = _prepared_for_action(event_tuple, action_id, applied_event.sequence)
        baseline = prepared.payload.get("baseline_worktree_diff_hash")
        expected = prepared.payload.get("expected_worktree_diff_hash")
        intent_hash = prepared.payload.get("content_hash")
        observed = applied_event.payload.get("worktree_diff_hash")
        if not (
            isinstance(baseline, str)
            and isinstance(expected, str)
            and isinstance(intent_hash, str)
            and expected == observed
            and (expected_baseline is None or baseline == expected_baseline)
        ):
            raise RecoveryError("mutation baseline diff chain differs")
        if first_prepared is None:
            first_prepared = prepared
            diff_chain.append(baseline)
        action_ids.append(action_id)
        intent_hashes.append(intent_hash)
        diff_chain.append(expected)
        expected_baseline = expected
    assert first_prepared is not None
    if diff_chain[-1] != current_failed_diff:
        raise RecoveryError("mutation baseline chain does not reach the current failure")
    body = {
        "schema_version": MUTATION_BASELINE_SCHEMA,
        "policy_version": CAUSAL_ALTERNATIVE_POLICY,
        "run_id": state.run_id,
        "check_id": state.check_id,
        "semantic_progress_state_hash": state.content_hash,
        "failure_signature_hash": state.failure_signature_hash,
        "failure_event_sequences": state.failure_event_sequences,
        "failed_diff_hashes": state.failed_diff_hashes,
        "baseline_diff_hash": diff_chain[0],
        "current_failed_diff_hash": current_failed_diff,
        "first_mutation_prepared_sequence": first_prepared.sequence,
        "first_mutation_applied_sequence": first_applied.sequence,
        "forward_action_ids": tuple(action_ids),
        "forward_intent_hashes": tuple(intent_hashes),
        "forward_diff_chain": tuple(diff_chain),
        "restore_action_ids": tuple(reversed(action_ids)),
        "restore_intent_hashes": tuple(reversed(intent_hashes)),
        "restore_required": True,
        "append_only_failure_history_preserved": True,
        "private_evidence_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(MutationBaselineProjection, body)


def record_mutation_baseline_restore(
    *,
    baseline: MutationBaselineProjection,
    observed_before_diff_hash: str,
    observed_after_diff_hash: str,
    restored_action_ids: tuple[str, ...] | list[str],
    restored_intent_hashes: tuple[str, ...] | list[str],
) -> MutationBaselineRestoreReceipt:
    """Verify an exact future gateway restore without erasing append-only trace data."""

    restored = tuple(restored_action_ids)
    restored_intents = tuple(restored_intent_hashes)
    if (
        observed_before_diff_hash != baseline.current_failed_diff_hash
        or observed_after_diff_hash != baseline.baseline_diff_hash
        or restored != baseline.restore_action_ids
        or restored_intents != baseline.restore_intent_hashes
    ):
        _reject("mutation_baseline_restore_mismatch", "mutation baseline restore differs")
    body = {
        "schema_version": MUTATION_BASELINE_RESTORE_SCHEMA,
        "policy_version": CAUSAL_ALTERNATIVE_POLICY,
        "run_id": baseline.run_id,
        "baseline_projection_hash": baseline.content_hash,
        "observed_before_diff_hash": observed_before_diff_hash,
        "observed_after_diff_hash": observed_after_diff_hash,
        "restored_action_ids": restored,
        "restored_intent_hashes": restored_intents,
        "preserved_failure_event_sequences": baseline.failure_event_sequences,
        "exact_restore_verified": True,
        "append_only_events_deleted": False,
        "provider_calls": 0,
        "visible_check_calls": 0,
    }
    return _hashed(MutationBaselineRestoreReceipt, body)


def _validate_history(
    history: tuple[CausalMechanismHistoryEntry, ...],
    *,
    parent_plan_hash: str,
) -> None:
    if not history or len(history) > 4:
        _reject("causal_history_invalid", "causal mechanism history differs")
    for index, item in enumerate(history):
        if index and (
            item.revision_index != history[index - 1].revision_index + 1
            or item.parent_plan_hash != history[index - 1].plan_hash
        ):
            _reject("causal_history_invalid", "causal mechanism history chain differs")
    if history[-1].plan_hash != parent_plan_hash:
        _reject("causal_history_parent_mismatch", "causal history parent differs")


def validate_causal_alternative_plan(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
    semantic_progress_state: PublicSemanticProgressState,
    baseline: MutationBaselineProjection,
    restore_receipt: MutationBaselineRestoreReceipt,
    history: tuple[CausalMechanismHistoryEntry, ...],
    parent_plan_hash: str,
    arguments: dict[str, Any],
) -> tuple[RecordedCausalAlternativePlan, CandidateBindingNormalization]:
    """Admit a reset revision only after a source-backed causal-boundary change."""

    required = {
        "observation_status",
        "hypothesis",
        "foundation_evidence_ids",
        "supporting_evidence_ids",
        "candidate_files",
        "intended_change",
        "expected_behavior",
        "unknowns",
        "prior_causal_mechanism_hash",
        "alternative_causal_mechanism",
    }
    if type(arguments) is not dict or set(arguments) != required:
        _reject("causal_plan_shape_invalid", "causal alternative plan arguments differ")
    if arguments.get("observation_status") != "visible_check_failed":
        _reject("causal_observation_invalid", "causal alternative observation differs")
    if (
        baseline.semantic_progress_state_hash != semantic_progress_state.content_hash
        or restore_receipt.baseline_projection_hash != baseline.content_hash
        or restore_receipt.observed_after_diff_hash != catalog.worktree_diff_hash
        or catalog.run_id != semantic_progress_state.run_id
    ):
        _reject("causal_reset_binding_invalid", "causal reset binding differs")
    _validate_history(history, parent_plan_hash=parent_plan_hash)
    prior = history[-1].mechanism
    if arguments.get("prior_causal_mechanism_hash") != prior.content_hash:
        _reject("prior_causal_mechanism_mismatch", "prior causal mechanism differs")

    foundation_ids = arguments.get("foundation_evidence_ids")
    supporting_ids = arguments.get("supporting_evidence_ids")
    candidates = arguments.get("candidate_files")
    unknowns = arguments.get("unknowns")
    if not (
        isinstance(foundation_ids, list)
        and foundation_ids
        and isinstance(supporting_ids, list)
        and isinstance(candidates, list)
        and candidates
        and isinstance(unknowns, list)
    ):
        _reject("causal_plan_collection_invalid", "causal alternative collections differ")
    by_id = {item.evidence_id: item for item in catalog.items}
    if any(type(item) is not str or item not in by_id for item in foundation_ids):
        _reject("causal_foundation_evidence_invalid", "causal foundation evidence differs")
    if any(type(item) is not str or item not in by_id for item in supporting_ids):
        _reject("causal_supporting_evidence_invalid", "causal supporting evidence differs")
    foundation = tuple(by_id[item] for item in dict.fromkeys(foundation_ids))
    supporting = tuple(by_id[item] for item in dict.fromkeys(supporting_ids))
    if any(item.role != "foundation" for item in foundation):
        _reject("causal_foundation_role_invalid", "causal foundation role differs")
    if any(item.role != "support" for item in supporting):
        _reject("causal_support_role_invalid", "causal support role differs")

    base_arguments = {
        key: arguments[key]
        for key in (
            "observation_status",
            "hypothesis",
            "foundation_evidence_ids",
            "supporting_evidence_ids",
            "candidate_files",
            "intended_change",
            "expected_behavior",
            "unknowns",
        )
    }
    normalized_arguments, normalization = normalize_same_path_candidate_bindings(
        task=task,
        catalog=catalog,
        arguments=base_arguments,
    )
    alternative = validate_public_causal_mechanism(
        task=task,
        catalog=catalog,
        foundation_evidence_ids=foundation_ids,
        raw_mechanism=arguments.get("alternative_causal_mechanism"),
    )
    exhausted_boundaries = tuple(
        dict.fromkeys(item.mechanism.causal_boundary.coverage_key for item in history)
    )
    exhausted_families = {item.mechanism.mechanism_family_key for item in history}
    if alternative.causal_boundary.coverage_key in exhausted_boundaries:
        _reject(
            "causal_boundary_already_exhausted",
            "alternative causal boundary was already exhausted",
        )
    if alternative.mechanism_family_key in exhausted_families:
        _reject("causal_mechanism_family_unchanged", "causal mechanism family did not change")

    try:
        normalized_candidates = tuple(
            CandidateFileEvidence.model_validate(item)
            for item in normalized_arguments["candidate_files"]
        )
    except ValueError as exc:
        _reject("causal_candidate_invalid", "causal candidate files differ")
        raise AssertionError from exc
    mutation_candidate = next(
        (item for item in normalized_candidates if item.path == alternative.mutation_site.path),
        None,
    )
    if (
        mutation_candidate is None
        or mutation_candidate.read_evidence_id != alternative.mutation_site.read_evidence_id
    ):
        _reject(
            "causal_mutation_site_candidate_mismatch",
            "causal mutation site lacks its exact candidate binding",
        )

    contrast = CausalContrast(
        prior_mechanism_hash=prior.content_hash,
        alternative_mechanism_hash=alternative.content_hash,
        prior_boundary_coverage_key=prior.causal_boundary.coverage_key,
        alternative_boundary_coverage_key=alternative.causal_boundary.coverage_key,
        exhausted_boundary_coverage_keys=exhausted_boundaries,
        alternative_boundary_is_non_exhausted=True,
        mechanism_family_changed=True,
        prose_only_relabel_accepted=False,
    )
    revision_index = history[-1].revision_index + 1
    if revision_index > 3:
        _reject("correction_attempt_limit", "causal alternative exceeds the 1+3 limit")
    body = {
        "schema_version": CAUSAL_ALTERNATIVE_PLAN_SCHEMA,
        "policy_version": CAUSAL_ALTERNATIVE_POLICY,
        "run_id": catalog.run_id,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_task_hash": catalog.public_task_hash,
        "worktree_diff_hash": catalog.worktree_diff_hash,
        "observation_status": "visible_check_failed",
        "hypothesis": arguments.get("hypothesis"),
        "foundation_evidence": tuple(
            item.model_dump(mode="python")
            for item in sorted(foundation, key=lambda item: item.canonical_event_sequence)
        ),
        "supporting_evidence": tuple(
            item.model_dump(mode="python")
            for item in sorted(supporting, key=lambda item: item.canonical_event_sequence)
        ),
        "candidate_files": tuple(
            item.model_dump(mode="python")
            for item in sorted(normalized_candidates, key=lambda item: item.path)
        ),
        "intended_change": arguments.get("intended_change"),
        "expected_behavior": arguments.get("expected_behavior"),
        "unknowns": tuple(unknowns),
        "planned_check_ids": tuple(check.id for check in task.visible_checks),
        "evidence_catalog_hash": catalog.content_hash,
        "revision_index": revision_index,
        "parent_plan_hash": parent_plan_hash,
        "trigger_check_id": semantic_progress_state.check_id,
        "trigger_failure_event_sequences": semantic_progress_state.failure_event_sequences,
        "semantic_progress_state_hash": semantic_progress_state.content_hash,
        "mutation_baseline_projection_hash": baseline.content_hash,
        "mutation_baseline_restore_receipt_hash": restore_receipt.content_hash,
        "prior_hypothesis_disposition": "rejected",
        "prior_causal_mechanism": prior.model_dump(mode="python"),
        "alternative_causal_mechanism": alternative.model_dump(mode="python"),
        "causal_contrast": contrast.model_dump(mode="python"),
        "candidate_binding_normalization_hash": normalization.content_hash,
        "candidate_binding_normalization": normalization.model_dump(mode="python"),
        "public_evidence_only": True,
        "hidden_evidence_used": False,
        "private_evidence_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(RecordedCausalAlternativePlan, body), normalization


def initial_causal_alternative_checkpoint(
    *,
    semantic_progress_state_hash: str,
    restore_receipt_hash: str,
    parent_plan_hash: str,
) -> CausalAlternativeAdmissionCheckpoint:
    gate_id = sha256_json(
        {
            "schema_version": "causal-alternative-gate-identity-v1",
            "semantic_progress_state_hash": semantic_progress_state_hash,
            "restore_receipt_hash": restore_receipt_hash,
            "parent_plan_hash": parent_plan_hash,
        }
    )
    body = {
        "schema_version": CAUSAL_ALTERNATIVE_CHECKPOINT_SCHEMA,
        "policy_version": CAUSAL_ALTERNATIVE_POLICY,
        "gate_id": gate_id,
        "rejection_count": 0,
        "recovery_remaining": 1,
        "status": "active",
        "accepted_plan_hash": None,
        "terminal_reason": None,
        "last_reason_codes": (),
        "provider_dispatch_after_terminal": False,
    }
    return _hashed(CausalAlternativeAdmissionCheckpoint, body)


def record_causal_alternative_rejection(
    checkpoint: CausalAlternativeAdmissionCheckpoint,
    *,
    reason_codes: tuple[str, ...] | list[str],
) -> CausalAlternativeAdmissionCheckpoint:
    if checkpoint.status != "active":
        raise RecoveryError("causal alternative gate is no longer active")
    reasons = tuple(reason_codes)
    if not reasons or len(reasons) > 10 or any(not item for item in reasons):
        raise ContractError("causal alternative rejection reasons differ")
    count = checkpoint.rejection_count + 1
    status = "terminal" if count >= 2 else "active"
    body = {
        **checkpoint.model_dump(mode="python", exclude={"content_hash"}),
        "rejection_count": count,
        "recovery_remaining": 0,
        "status": status,
        "terminal_reason": (
            "causal_alternative_admission_repeated" if status == "terminal" else None
        ),
        "last_reason_codes": reasons,
    }
    return _hashed(CausalAlternativeAdmissionCheckpoint, body)


def record_causal_alternative_acceptance(
    checkpoint: CausalAlternativeAdmissionCheckpoint,
    *,
    plan_hash: str,
) -> CausalAlternativeAdmissionCheckpoint:
    if checkpoint.status != "active":
        raise RecoveryError("causal alternative gate is no longer active")
    body = {
        **checkpoint.model_dump(mode="python", exclude={"content_hash"}),
        "status": "accepted",
        "accepted_plan_hash": plan_hash,
        "terminal_reason": None,
    }
    return _hashed(CausalAlternativeAdmissionCheckpoint, body)


__all__ = [
    "CAUSAL_ALTERNATIVE_CHECKPOINT_SCHEMA",
    "CAUSAL_ALTERNATIVE_INPUT_SCHEMA",
    "CAUSAL_ALTERNATIVE_PLAN_SCHEMA",
    "CAUSAL_ALTERNATIVE_POLICY",
    "CAUSAL_MECHANISM_SCHEMA",
    "MUTATION_BASELINE_RESTORE_SCHEMA",
    "MUTATION_BASELINE_SCHEMA",
    "CausalAlternativeAdmissionCheckpoint",
    "CausalAlternativeInputContract",
    "CausalMechanismHistoryEntry",
    "CausalSourceLocationInput",
    "MutationBaselineProjection",
    "MutationBaselineRestoreReceipt",
    "PublicCausalMechanism",
    "PublicCausalMechanismInput",
    "RecordedCausalAlternativePlan",
    "initial_causal_alternative_checkpoint",
    "project_mutation_baseline",
    "project_causal_alternative_input_contract",
    "record_causal_alternative_acceptance",
    "record_causal_alternative_rejection",
    "record_mutation_baseline_restore",
    "validate_causal_alternative_plan",
    "validate_public_causal_mechanism",
]
