"""Append-only, execution-closed successor for the discovered all-cross panel.

The original acquisition preregistration required six same-repository and six
cross-repository tasks from a post-window snapshot.  The public July Harbor
snapshot cannot satisfy that shape.  This module does not rewrite that design.
It records a post-public-screening, pre-A/C-outcome successor for the exact 12
validated cross-repository tasks, qualifies only their public snapshot
membership, freezes a metadata-only 48-row schedule, and leaves task admission,
runtime candidate creation, preflight, provider execution, and spend closed.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.errors import ContractError
from patchloop.util import ensure_within, sha256_bytes, sha256_json

PREREG_SCHEMA = "lean-fresh-all-cross-preregistration-v1"
REGISTRY_SCHEMA = "lean-fresh-all-cross-public-registry-qualification-v1"
SUITE_SCHEMA = "lean-fresh-all-cross-metadata-suite-v1"
PLAN_SCHEMA = "lean-fresh-all-cross-activation-plan-v1"

PREREG_ID = "lean-harness-fresh-all-cross-ac-20260818-v1"
REGISTRY_ID = "lean-fresh-all-cross-public-registry-20260818-r1"
SUITE_ID = "lean-harness-fresh-all-cross-ac-suite-20260818-v1"
PLAN_ID = "lean-harness-fresh-all-cross-activation-20260818-v1"

PREREG_PATH = "experiments/lean-harness-fresh-all-cross-preregistration-20260818-v1.json"
REGISTRY_PATH = "reports/fresh-panel/artifacts/lean-fresh-all-cross-registry-qualification-r1.json"
SUITE_PATH = "experiments/lean-harness-fresh-all-cross-suite-20260818-v1.json"
PLAN_PATH = "experiments/lean-harness-fresh-all-cross-activation-plan-20260818-v1.json"

ORIGINAL_PREREG_PATH = "experiments/lean-harness-fresh-acquisition-preregistration-20260817-v1.json"
ORIGINAL_PREREG_BYTES = 7_255
ORIGINAL_PREREG_SHA256 = "sha256:086b9fc56ab5eca3ae23cd367243d9b71c3805d7f3edd3613afdb73a34bbf359"
ORIGINAL_PREREG_CONTENT_HASH = (
    "sha256:adec1153d8eab532d118fe24d0f60247385d154dbcc840db8dc24167c0c1cb94"
)
DATASET_MANIFEST_PATH = "data/dataset-manifest.yaml"
DATASET_MANIFEST_BYTES = 47_368
DATASET_MANIFEST_SHA256 = "sha256:e8cf14ca9dabebcc03c3522e400dfcb79606541e9b11e59f49510ea5c40bebed"
R16_INDEX_PATH = "reports/heldout-ac/artifacts/heldout-ac-r16-campaign-complete-r1.json"
R16_INDEX_BYTES = 10_375
R16_INDEX_SHA256 = "sha256:999fa9e42f010b03b96013d089f662ad3f50b1c5c6469b2aa8ddb901c522391e"
R16_INDEX_CONTENT_HASH = "sha256:945e8e9ff1df60a255d20fb406ca7b7ab20ca16a3b50da5cbce12f2fb38a6521"
LEAN_SOURCE_PATH = "experiments/lean-harness-runtime-source-qualification-20260817-v1.json"
LEAN_SOURCE_BYTES = 72_420
LEAN_SOURCE_SHA256 = "sha256:7104310a700822bde8343b7ed37facdb3fa09709ced41540cb9ccb431642fdab"
LEAN_SOURCE_CONTENT_HASH = "sha256:b0f28eb86eb8463c389708af500dede582048c3f7910876dac5aa9d610768226"
OBSERVATION_PATH = "reports/fresh-panel/artifacts/fresh-all-cross-search-observation-v1.json"
OBSERVATION_BYTES = 15_689
OBSERVATION_SHA256 = "sha256:fb947e2e6ba227f1993fe41a625ab5fac028d38b4e9ec42a7e859101c85e6e1a"
MEMBERSHIP_PATH = "reports/fresh-panel/raw/harbor-swe-rebench-07-2026-r1-membership.json"
MEMBERSHIP_BYTES = 21_512
MEMBERSHIP_SHA256 = "sha256:b0e489931259f8643a94d47b6b52d9b3e467571c0ad3bcf80d97f0c5069b2527"
HARBOR_SOURCE_COMMIT = "f03db62fd2ed2ed1f79aefe024cfcbc68a0d759e"
DATASET_VERSION_ID = "574acb72-70aa-46fb-8758-0a814a5eb213"
SCHEDULE_SEED = "lean-fresh-all-cross-20260818-v1"

CANDIDATE_IDS = (
    "harbor-framework__harbor-1764",
    "marimo-team__marimo-9626",
    "microsoft__apm-1553",
    "pydantic__pydantic-ai-5842",
    "hkuds__nanobot-4048",
    "soju06__codex-lb-744",
    "nesquena__hermes-webui-3069",
    "agno-agi__agno-8148",
    "mozilla-ai__any-llm-1121",
    "livekit__agents-5944",
    "verl-project__verl-6506",
    "raullenchai__rapid-mlx-426",
)


class FreshAllCrossSuccessorError(ContractError):
    """The all-cross successor or one of its exact public bindings differs."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class FileBinding(FrozenModel):
    path: str
    file_bytes: int = Field(ge=1)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    role: str = Field(min_length=1)


class ArchiveBinding(FrozenModel):
    bytes: int = Field(ge=1)
    sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class PartialVariants(FrozenModel):
    tested: int = Field(ge=8)
    rejected: int = Field(ge=8)

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if self.rejected > self.tested:
            raise ValueError("rejected partial variants exceed tested variants")
        return self


class CandidateObservation(FrozenModel):
    instance: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]+$")
    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    rank_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    package_content_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    archive: ArchiveBinding
    image_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    base_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    resolution_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    license: Literal["MIT", "Apache-2.0"]
    public_issue_created_at: str
    public_issue_source: str | None = None
    resolution_merged_at: str
    base_counts: dict[str, int]
    reference_report_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    partial_variants: PartialVariants
    operational_note: str | None = None

    @model_validator(mode="after")
    def validate_candidate(self) -> Self:
        if set(self.base_counts) - {"pass_to_pass_passed", "fail_to_pass_failed", "skipped"}:
            raise ValueError("candidate base-count fields differ")
        if (
            type(self.base_counts.get("pass_to_pass_passed")) is not int
            or type(self.base_counts.get("fail_to_pass_failed")) is not int
        ):
            raise ValueError("candidate base counts must be exact integers")
        created = datetime.fromisoformat(self.public_issue_created_at.replace("Z", "+00:00"))
        merged = datetime.fromisoformat(self.resolution_merged_at.replace("Z", "+00:00"))
        cutoff = datetime(2026, 3, 17, 23, 59, 59, tzinfo=UTC)
        snapshot = datetime(2026, 7, 27, 23, 59, 59, tzinfo=UTC)
        if not (cutoff < created <= merged <= snapshot):
            raise ValueError("candidate public chronology differs")
        return self


class RejectionObservation(FrozenModel):
    instance: str
    code: str
    detail: str | None = None
    applied_partial_variants: int | None = None
    rejected_partial_variants: int | None = None


class SearchSource(FrozenModel):
    dataset: Literal["ibragim-badertdinov/swe-rebench-07-2026"]
    dataset_version_id: Literal[DATASET_VERSION_ID]
    revision: Literal[1]
    published_at: Literal["2026-07-27"]
    membership_rows: Literal[111]
    membership_response_bytes: Literal[MEMBERSHIP_BYTES]
    membership_response_sha256: Literal[MEMBERSHIP_SHA256]
    harbor_source_commit: Literal[HARBOR_SOURCE_COMMIT]


class SearchObservation(FrozenModel):
    schema_version: Literal["fresh-task-search-audit-v1"]
    status: Literal["EXPLORATORY_ALL_CROSS_PANEL_FOUND_NON_AUTHORIZING"]
    source: SearchSource
    design_boundary: dict[str, Any]
    common_checks: dict[str, Any]
    candidates: tuple[CandidateObservation, ...]
    rejections: tuple[RejectionObservation, ...]
    authority: dict[str, Any]
    next_gate: Literal[
        "write-and-seal-a-successor-all-cross-preregistration-before-promoting-these-exploratory-candidates-into-an-official-panel"
    ]

    @field_validator("candidates", "rejections", mode="before")
    @classmethod
    def freeze_rows(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        if tuple(row.instance for row in self.candidates) != CANDIDATE_IDS:
            raise ValueError("all-cross candidate order differs")
        if tuple(row.rank_sha256 for row in self.candidates) != tuple(
            sorted(row.rank_sha256 for row in self.candidates)
        ):
            raise ValueError("all-cross candidates are not in recorded rank order")
        repositories = [row.repository.lower() for row in self.candidates]
        if len(set(repositories)) != 12:
            raise ValueError("all-cross candidate repositories are not distinct")
        expected_checks = {
            "all_difficulty_medium": True,
            "all_issue_or_public_problem_created_after_2026_03_17": True,
            "all_resolutions_merged_by_2026_08_16": True,
            "all_licenses_mit_or_apache_2_0": True,
            "all_repositories_python_and_not_archived": True,
            "all_package_inventories_exact_seven_files": True,
            "all_images_clean_at_bound_base_commit": True,
            "all_base_visible_pass_hidden_fail": True,
            "all_reference_runs_three_of_three_resolved_with_identical_reports": True,
            "all_reject_at_least_eight_applied_partial_patches": True,
            "candidate_repository_count": 12,
            "candidate_repository_unique_count": 12,
            "overlap_with_current_manifest_repository_count": 0,
            "partial_variants_tested": 133,
            "partial_variants_rejected": 105,
        }
        if self.common_checks != expected_checks:
            raise ValueError("all-cross exploratory common checks differ")
        if self.design_boundary.get("original_six_same_six_cross_satisfied") is not False:
            raise ValueError("original design disposition differs")
        if self.authority != {
            "candidate_registry_materialized": False,
            "fresh_panel_authorized": False,
            "execution_authorized": False,
            "provider_calls": 0,
            "agent_runs": 0,
            "added_model_cost_usd": 0,
            "memory_effect_claim_authorized": False,
        }:
            raise ValueError("exploratory authority differs")
        return self


class ScheduleRow(FrozenModel):
    order: int = Field(ge=1, le=48)
    wave: int = Field(ge=1, le=4)
    task_id: str
    condition: Literal["no_memory", "structured"]
    repetition: Literal[1, 2]
    row_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class MetadataTask(FrozenModel):
    task_id: str
    repository: str
    package_content_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    archive: ArchiveBinding
    environment_image_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    base_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    resolution_commit_evaluator_only: str = Field(pattern=r"^[0-9a-f]{40}$")
    license_spdx: Literal["MIT", "Apache-2.0"]


class SuccessorAuthority(FrozenModel):
    provider_calls_authorized: Literal[False]
    evaluator_calls_authorized: Literal[False]
    agent_runs_authorized: Literal[False]
    docker_calls_authorized: Literal[False]
    sdk_calls_authorized: Literal[False]
    task_package_materialization_authorized: Literal[False]
    private_or_reference_material_agent_visible: Literal[False]
    candidate_creation_authorized: Literal[False]
    preflight_authorized: Literal[False]
    approval_granted: Literal[False]
    spend_authorized: Literal[False]
    official_analysis_authorized: Literal[False]
    memory_benefit_claim_authorized: Literal[False]
    authorized_provider_calls: Literal[0]
    authorized_agent_runs: Literal[0]
    authorized_cost_usd: Literal[0.0]


def _authority() -> SuccessorAuthority:
    return SuccessorAuthority(
        provider_calls_authorized=False,
        evaluator_calls_authorized=False,
        agent_runs_authorized=False,
        docker_calls_authorized=False,
        sdk_calls_authorized=False,
        task_package_materialization_authorized=False,
        private_or_reference_material_agent_visible=False,
        candidate_creation_authorized=False,
        preflight_authorized=False,
        approval_granted=False,
        spend_authorized=False,
        official_analysis_authorized=False,
        memory_benefit_claim_authorized=False,
        authorized_provider_calls=0,
        authorized_agent_runs=0,
        authorized_cost_usd=0.0,
    )


def _design_change() -> dict[str, Any]:
    return {
        "predecessor_disposition": "preserved-unsatisfied-not-amended",
        "change_trigger": "public-source-feasibility-only-not-ac-outcomes",
        "selection_timing": (
            "post-public-screening-and-admission-observation-pre-ac-provider-outcome"
        ),
        "original_design": {"same_repository_tasks": 6, "cross_repository_tasks": 6},
        "successor_design": {"same_repository_tasks": 0, "cross_repository_tasks": 12},
        "all_repositories_distinct": True,
        "all_repositories_disjoint_from_current_manifest": True,
        "original_post-window-snapshot-rule_satisfied": False,
        "july_snapshot_covers_original_window_through_2026_08_16": False,
        "effective_public_chronology": (
            "issue-created-after-2026-03-17-and-resolution-merged-before-the-2026-07-27-snapshot"
        ),
        "broad_snapshot-universe-optimal-selection_claimed": False,
        "task-specific-admission-information_used_to_change_harness": False,
        "r16-outcomes_used_to-select-these-tasks": False,
        "successor-required_before_any-ac-provider-outcome": True,
    }


def _runtime_and_cost() -> dict[str, Any]:
    return {
        "harness": "lean-harness-v1",
        "tool_schema": "v7",
        "phase_evidence": "phase-evidence-v12",
        "memory_policy": "fixed-d110-bundle-v1",
        "conditions": ["no_memory", "structured"],
        "only_treatment_difference": "memory",
        "repetitions_per_task": 2,
        "expected_rows": 48,
        "model": "gpt-5.4-mini-2026-03-17",
        "input_token_limit": 1_000_000,
        "output_token_limit": 100_000,
        "total_token_limit": 1_100_000,
        "maximum_output_tokens_per_request": 25_000,
        "model_call_limit": 240,
        "tool_call_limit": 400,
        "wall_time_limit_seconds": 3_600,
        "per_row_cost_reserve_usd": 1.2,
        "full_schedule_planning_reserve_usd": 57.6,
        "hard_cap_usd": 60.0,
        "price_nanos_per_token": {
            "uncached_input": 750,
            "cached_input": 75,
            "cache_write_input": 750,
            "output": 4_500,
        },
        "price_refresh_required_before_candidate": True,
        "price_drift_disposition": "block-candidate-and-require-successor-cost-binding",
        "equal_condition_budget_required": True,
        "condition_specific_resource_relief_allowed": False,
        "typed_token_terminals_score_zero": True,
    }


def _analysis_contract() -> dict[str, Any]:
    return {
        "analysis_scope": "exact-frozen-12-task-all-cross-panel-only",
        "primary_gate": {
            "required_scheduled_rows": 48,
            "required_eligible_rows": 48,
            "inconclusive_trigger_count_required": 0,
            "partial_panel_primary_analysis_authorized": False,
        },
        "primary_estimand": {
            "id": "equal-task-weighted-scheduled-row-success-at-budget-c-minus-a",
            "formula": (
                "mean-over-12-tasks-of-mean-over-2-repetitions-of-y-structured-minus-y-no-memory"
            ),
            "unit": "task",
            "task_weighting": "equal",
            "effect_scale": "absolute-proportion-and-percentage-points",
        },
        "task_role_strata": [],
        "role-stratified-effect-authorized": False,
        "directional_flips": {
            "pairing_unit": "task-by-repetition",
            "pair_count": 24,
            "benefit": "no-memory-fail-and-structured-success",
            "negative_transfer": "no-memory-success-and-structured-fail",
            "inference": "counts-and-rates-only",
        },
        "descriptive_stability": {
            "method": "deterministic-task-cluster-percentile-resampling",
            "samples": 100_000,
            "tasks_drawn_per_sample": 12,
            "hash_algorithm": "sha256",
            "preimage_template": (
                "fresh-all-cross-percentile-v1|20260818|b={zero_based_sample}|"
                "j={zero_based_draw}|nonce={zero_based_nonce}"
            ),
            "acceptance_threshold_integer": 18_446_744_073_709_551_612,
            "selected_task_index_formula": "u-mod-12",
            "endpoint_method": "hyndman-fan-type-7-exact-rational",
            "lower_endpoint_formula": "(m_sorted[2499]+39*m_sorted[2500])/960",
            "upper_endpoint_formula": "(39*m_sorted[97499]+m_sorted[97500])/960",
            "confidence_interval_claim_authorized": False,
            "interpretation": "descriptive-stability-for-this-frozen-panel-only",
        },
        "sign_flip_sensitivity": {
            "method": "all-4096-task-level-sign-vectors-inclusive-two-sided",
            "null_assumption": (
                "conditional-on-ordered-absolute-task-effects-the-joint-sign-vector-is-uniform"
            ),
            "headline_use_authorized": False,
        },
        "resource_metrics": [
            "input_tokens",
            "output_tokens",
            "reasoning_tokens",
            "total_tokens",
            "model_cost_usd",
            "model_calls",
            "tool_calls",
            "wall_time_seconds",
        ],
        "cost_per_success": {
            "grouping": "per-condition",
            "complete_panel_gate_required": True,
            "zero_success_value": None,
            "zero_success_status": "undefined-zero-success-denominator",
        },
        "causal_population_uncontaminated_or_general_claim_authorized": False,
    }


class AllCrossPreregistration(FrozenModel):
    schema_version: Literal[PREREG_SCHEMA]
    preregistration_id: Literal[PREREG_ID]
    status: Literal["PREREGISTERED_EXACT_ALL_CROSS_PANEL_EXECUTION_CLOSED"]
    predecessor_bindings: tuple[FileBinding, ...]
    design_change: dict[str, Any]
    exact_candidate_ids: tuple[str, ...]
    runtime_and_cost: dict[str, Any]
    analysis: dict[str, Any]
    exclusions_and_stops: dict[str, Any]
    authority: SuccessorAuthority
    next_gate: Literal[
        "qualify-public-membership-and-bind-admission-observation-before-task-package-materialization"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("predecessor_bindings", "exact_candidate_ids", mode="before")
    @classmethod
    def freeze_tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_preregistration(self) -> Self:
        if self.design_change != _design_change():
            raise ValueError("all-cross design change differs")
        if self.exact_candidate_ids != CANDIDATE_IDS:
            raise ValueError("all-cross preregistered candidate IDs differ")
        if self.runtime_and_cost != _runtime_and_cost() or self.analysis != _analysis_contract():
            raise ValueError("all-cross runtime or analysis contract differs")
        if self.authority != _authority():
            raise ValueError("all-cross preregistration authority differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("all-cross preregistration content hash differs")
        return self


class PublicRegistryQualification(FrozenModel):
    schema_version: Literal[REGISTRY_SCHEMA]
    registry_id: Literal[REGISTRY_ID]
    status: Literal["PUBLIC_MEMBERSHIP_QUALIFIED_EXACT_PANEL_BOUND_ADMISSION_RAW_REPLAY_PENDING"]
    bindings: tuple[FileBinding, ...]
    source: SearchSource
    raw_membership_complete: Literal[True]
    selected_candidates_present: Literal[True]
    selected_content_hashes_match_membership: Literal[True]
    selected_repository_count: Literal[12]
    selected_repository_unique_count: Literal[12]
    current_manifest_repository_overlap_count: Literal[0]
    candidates: tuple[CandidateObservation, ...]
    rejections: tuple[RejectionObservation, ...]
    admission_summary: dict[str, Any]
    qualification_limits: dict[str, Any]
    authority: SuccessorAuthority
    next_gate: Literal[
        "preserve-and-source-qualify-the-task-admission-evidence-producer-before-materializing-runtime-task-packages"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("bindings", "candidates", "rejections", mode="before")
    @classmethod
    def freeze_tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_registry(self) -> Self:
        if tuple(row.instance for row in self.candidates) != CANDIDATE_IDS:
            raise ValueError("registry candidate IDs differ")
        if self.admission_summary != {
            "difficulty": "medium-for-all-12",
            "package_inventory": "exact-seven-files-for-all-12",
            "base_visible_pass_hidden_fail": True,
            "reference_resolved_runs_per_task": 3,
            "reference_report_repeatability": "identical-within-each-task",
            "partial_variants_tested": 133,
            "partial_variants_rejected": 105,
            "minimum_rejected_partial_variants_per_task": 8,
            "environment_images_clean_at_bound_base_commit": True,
            "licenses": ["Apache-2.0", "MIT"],
        }:
            raise ValueError("registry admission summary differs")
        if self.qualification_limits != {
            "full-111-row-public-metadata-normalization-transcript-present": False,
            "original-window-through-2026-08-16-completeness-established": False,
            "raw-github-metadata-receipts-checked-in": False,
            "raw-docker-and-evaluator-admission-evidence-checked-in": False,
            "task-admission-producer-source-qualified": False,
            "task-packages-materialized-in-patchloop-format": False,
            "runtime-evaluator-source-qualified-for-these-task-identities": False,
            "broad-registry-optimal-selection-claim-authorized": False,
        }:
            raise ValueError("registry qualification limits differ")
        if self.authority != _authority():
            raise ValueError("registry authority differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("registry content hash differs")
        return self


class MetadataSuite(FrozenModel):
    schema_version: Literal[SUITE_SCHEMA]
    suite_id: Literal[SUITE_ID]
    status: Literal["METADATA_SUITE_FROZEN_EXECUTION_CLOSED"]
    preregistration_binding: FileBinding
    registry_binding: FileBinding
    tasks: tuple[MetadataTask, ...]
    conditions: tuple[Literal["no_memory", "structured"], ...]
    repetitions: Literal[2]
    rows: tuple[ScheduleRow, ...]
    schedule_seed: Literal[SCHEDULE_SEED]
    orientation_a_first_in_repetition_one: tuple[str, ...]
    schedule_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_and_cost: dict[str, Any]
    authority: SuccessorAuthority
    next_gate: Literal[
        "task-admission-source-qualification-and-runtime-task-package-materialization-not-candidate-creation"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator(
        "tasks",
        "conditions",
        "rows",
        "orientation_a_first_in_repetition_one",
        mode="before",
    )
    @classmethod
    def freeze_tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_suite(self) -> Self:
        if len(self.tasks) != 12 or len(self.rows) != 48:
            raise ValueError("metadata suite shape differs")
        if self.conditions != ("no_memory", "structured"):
            raise ValueError("metadata suite conditions differ")
        if [row.order for row in self.rows] != list(range(1, 49)):
            raise ValueError("metadata suite row order differs")
        if len({row.row_id for row in self.rows}) != 48:
            raise ValueError("metadata suite row IDs are not unique")
        for task in self.tasks:
            for repetition in (1, 2):
                rows = [
                    row
                    for row in self.rows
                    if row.task_id == task.task_id and row.repetition == repetition
                ]
                if len(rows) != 2 or {row.condition for row in rows} != {
                    "no_memory",
                    "structured",
                }:
                    raise ValueError("metadata suite task-condition cells differ")
                if rows[1].order != rows[0].order + 1:
                    raise ValueError("metadata suite A/C task block is not adjacent")
                if repetition == 2:
                    first_rep_one = next(
                        item.condition
                        for item in self.rows
                        if item.task_id == task.task_id and item.repetition == 1
                    )
                    if rows[0].condition == first_rep_one:
                        raise ValueError("metadata suite repetition orientation did not reverse")
        for wave in range(1, 5):
            wave_rows = [row for row in self.rows if row.wave == wave]
            if len(wave_rows) != 12 or len({row.task_id for row in wave_rows}) != 6:
                raise ValueError("metadata suite wave shape differs")
            firsts = wave_rows[::2]
            if sum(row.condition == "no_memory" for row in firsts) != 3:
                raise ValueError("metadata suite wave orientation balance differs")
        expected_schedule_hash = sha256_json([row.model_dump(mode="json") for row in self.rows])
        if self.schedule_hash != expected_schedule_hash:
            raise ValueError("metadata suite schedule hash differs")
        if self.runtime_and_cost != _runtime_and_cost() or self.authority != _authority():
            raise ValueError("metadata suite runtime or authority differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("metadata suite content hash differs")
        return self


class ActivationGate(FrozenModel):
    order: int = Field(ge=1)
    gate: str
    status: Literal["complete", "blocked"]
    completion_evidence: str


class ActivationPlan(FrozenModel):
    schema_version: Literal[PLAN_SCHEMA]
    plan_id: Literal[PLAN_ID]
    status: Literal["ACTIVATION_BLOCKED_BEFORE_CANDIDATE_AND_PREFLIGHT"]
    preregistration_binding: FileBinding
    registry_binding: FileBinding
    suite_binding: FileBinding
    gates: tuple[ActivationGate, ...]
    first_blocked_gate: Literal[3]
    candidate_hash: None
    no_call_preflight_artifact: None
    approval: None
    full_schedule_reserve_authorized_usd: Literal[0.0]
    spend_authorized_usd: Literal[0.0]
    authority: SuccessorAuthority
    next_gate: Literal["source-qualify-admission-and-materialize-evaluator-separated-task-packages"]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("gates", mode="before")
    @classmethod
    def freeze_gates(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        if [gate.order for gate in self.gates] != list(range(1, len(self.gates) + 1)):
            raise ValueError("activation gate order differs")
        if next(gate.order for gate in self.gates if gate.status == "blocked") != 3:
            raise ValueError("activation first blocked gate differs")
        if self.authority != _authority():
            raise ValueError("activation authority differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("activation plan content hash differs")
        return self


def _json_object(raw: bytes, *, label: str) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise FreshAllCrossSuccessorError(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FreshAllCrossSuccessorError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise FreshAllCrossSuccessorError(f"{label} must be a JSON object")
    return value


def _binding(*, path: str, raw: bytes, role: str, content_hash: str | None = None) -> FileBinding:
    return FileBinding(
        path=path,
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        content_hash=content_hash,
        role=role,
    )


def _read_exact(
    root: Path,
    *,
    path: str,
    file_bytes: int,
    file_sha256: str,
) -> bytes:
    selected = ensure_within(root, path)
    if selected.is_symlink():
        raise FreshAllCrossSuccessorError(f"all-cross binding is a symlink: {path}")
    try:
        raw = selected.read_bytes()
    except OSError as exc:
        raise FreshAllCrossSuccessorError(f"all-cross binding is unavailable: {path}") from exc
    if len(raw) != file_bytes or sha256_bytes(raw) != file_sha256:
        raise FreshAllCrossSuccessorError(f"all-cross binding differs: {path}")
    return raw


def _read_inputs(root: Path) -> tuple[dict[str, bytes], SearchObservation, dict[str, str]]:
    specs = (
        (ORIGINAL_PREREG_PATH, ORIGINAL_PREREG_BYTES, ORIGINAL_PREREG_SHA256),
        (DATASET_MANIFEST_PATH, DATASET_MANIFEST_BYTES, DATASET_MANIFEST_SHA256),
        (R16_INDEX_PATH, R16_INDEX_BYTES, R16_INDEX_SHA256),
        (LEAN_SOURCE_PATH, LEAN_SOURCE_BYTES, LEAN_SOURCE_SHA256),
        (OBSERVATION_PATH, OBSERVATION_BYTES, OBSERVATION_SHA256),
        (MEMBERSHIP_PATH, MEMBERSHIP_BYTES, MEMBERSHIP_SHA256),
    )
    raw_by_path = {
        path: _read_exact(root, path=path, file_bytes=size, file_sha256=digest)
        for path, size, digest in specs
    }
    observation = SearchObservation.model_validate(
        _json_object(raw_by_path[OBSERVATION_PATH], label="all-cross search observation")
    )
    membership = json.loads(raw_by_path[MEMBERSHIP_PATH])
    if not isinstance(membership, list) or len(membership) != 111:
        raise FreshAllCrossSuccessorError("all-cross raw membership row count differs")
    membership_hashes: dict[str, str] = {}
    for row in membership:
        try:
            task = row["task_version"]
            package = task["package"]
            name = str(package["name"]).lower()
            digest = f"sha256:{str(task['content_hash']).removeprefix('sha256:')}"
        except (KeyError, TypeError) as exc:
            raise FreshAllCrossSuccessorError("all-cross membership shape differs") from exc
        if name in membership_hashes:
            raise FreshAllCrossSuccessorError("all-cross membership contains duplicate task names")
        membership_hashes[name] = digest
    for candidate in observation.candidates:
        if membership_hashes.get(candidate.instance.lower()) != candidate.package_content_sha256:
            raise FreshAllCrossSuccessorError(
                "all-cross candidate is absent or hash-mismatched in membership: "
                f"{candidate.instance}"
            )

    manifest = yaml.safe_load(raw_by_path[DATASET_MANIFEST_PATH])
    manifest_tasks = manifest.get("tasks") if isinstance(manifest, dict) else None
    if not isinstance(manifest_tasks, list):
        raise FreshAllCrossSuccessorError("all-cross current manifest is invalid")
    current_repositories = {
        str((task.get("source") or {}).get("upstream_repository", "")).lower()
        for task in manifest_tasks
        if isinstance(task, dict)
    }
    overlap = {
        candidate.repository.lower()
        for candidate in observation.candidates
        if candidate.repository.lower() in current_repositories
    }
    if overlap:
        raise FreshAllCrossSuccessorError(
            "all-cross candidates overlap current manifest repositories"
        )
    return raw_by_path, observation, membership_hashes


def _predecessor_bindings(raw: dict[str, bytes]) -> tuple[FileBinding, ...]:
    return (
        _binding(
            path=ORIGINAL_PREREG_PATH,
            raw=raw[ORIGINAL_PREREG_PATH],
            role="preserved-unsatisfied-acquisition-preregistration",
            content_hash=ORIGINAL_PREREG_CONTENT_HASH,
        ),
        _binding(
            path=DATASET_MANIFEST_PATH,
            raw=raw[DATASET_MANIFEST_PATH],
            role="current-consumed-task-manifest",
        ),
        _binding(
            path=R16_INDEX_PATH,
            raw=raw[R16_INDEX_PATH],
            role="consumed-unblinded-panel-evidence",
            content_hash=R16_INDEX_CONTENT_HASH,
        ),
        _binding(
            path=LEAN_SOURCE_PATH,
            raw=raw[LEAN_SOURCE_PATH],
            role="public-mock-qualified-lean-harness-source",
            content_hash=LEAN_SOURCE_CONTENT_HASH,
        ),
        _binding(
            path=OBSERVATION_PATH,
            raw=raw[OBSERVATION_PATH],
            role="exploratory-public-task-search-observation",
        ),
        _binding(
            path=MEMBERSHIP_PATH,
            raw=raw[MEMBERSHIP_PATH],
            role="exact-public-harbor-membership-response",
        ),
    )


def build_preregistration(root: Path) -> AllCrossPreregistration:
    raw, _observation, _membership = _read_inputs(root)
    body: dict[str, Any] = {
        "schema_version": PREREG_SCHEMA,
        "preregistration_id": PREREG_ID,
        "status": "PREREGISTERED_EXACT_ALL_CROSS_PANEL_EXECUTION_CLOSED",
        "predecessor_bindings": _predecessor_bindings(raw),
        "design_change": _design_change(),
        "exact_candidate_ids": CANDIDATE_IDS,
        "runtime_and_cost": _runtime_and_cost(),
        "analysis": _analysis_contract(),
        "exclusions_and_stops": {
            "task_exclusion_after_preregistration_allowed": False,
            "post-outcome_exclusion_allowed": False,
            "row_retry_replacement_or_resume_allowed": False,
            "adaptive_budget_allowed": False,
            "condition_specific_budget_allowed": False,
            "private-or-reference-material-in-agent-context": False,
            "infrastructure-or-contract-confound_action": "stop-before-next-provider-call",
            "partial_matrix_disposition": "inconclusive-diagnostic-only",
            "new-successor-required-after-any-outcome-access": True,
        },
        "authority": _authority(),
        "next_gate": (
            "qualify-public-membership-and-bind-admission-observation-before-"
            "task-package-materialization"
        ),
    }
    return AllCrossPreregistration(**body, content_hash=sha256_json(_jsonable(body)))


def _artifact_binding(path: str, model: BaseModel, role: str) -> FileBinding:
    raw = artifact_bytes(model)
    return _binding(
        path=path,
        raw=raw,
        role=role,
        content_hash=str(model.model_dump(mode="json")["content_hash"]),
    )


def build_registry(
    root: Path, preregistration: AllCrossPreregistration
) -> PublicRegistryQualification:
    raw, observation, _membership = _read_inputs(root)
    body: dict[str, Any] = {
        "schema_version": REGISTRY_SCHEMA,
        "registry_id": REGISTRY_ID,
        "status": "PUBLIC_MEMBERSHIP_QUALIFIED_EXACT_PANEL_BOUND_ADMISSION_RAW_REPLAY_PENDING",
        "bindings": (
            _artifact_binding(PREREG_PATH, preregistration, "all-cross-successor-preregistration"),
            _binding(
                path=OBSERVATION_PATH,
                raw=raw[OBSERVATION_PATH],
                role="exploratory-public-task-search-observation",
            ),
            _binding(
                path=MEMBERSHIP_PATH,
                raw=raw[MEMBERSHIP_PATH],
                role="exact-public-harbor-membership-response",
            ),
            _binding(
                path=DATASET_MANIFEST_PATH,
                raw=raw[DATASET_MANIFEST_PATH],
                role="current-repository-exclusion-manifest",
            ),
        ),
        "source": observation.source,
        "raw_membership_complete": True,
        "selected_candidates_present": True,
        "selected_content_hashes_match_membership": True,
        "selected_repository_count": 12,
        "selected_repository_unique_count": 12,
        "current_manifest_repository_overlap_count": 0,
        "candidates": observation.candidates,
        "rejections": observation.rejections,
        "admission_summary": {
            "difficulty": "medium-for-all-12",
            "package_inventory": "exact-seven-files-for-all-12",
            "base_visible_pass_hidden_fail": True,
            "reference_resolved_runs_per_task": 3,
            "reference_report_repeatability": "identical-within-each-task",
            "partial_variants_tested": 133,
            "partial_variants_rejected": 105,
            "minimum_rejected_partial_variants_per_task": 8,
            "environment_images_clean_at_bound_base_commit": True,
            "licenses": ["Apache-2.0", "MIT"],
        },
        "qualification_limits": {
            "full-111-row-public-metadata-normalization-transcript-present": False,
            "original-window-through-2026-08-16-completeness-established": False,
            "raw-github-metadata-receipts-checked-in": False,
            "raw-docker-and-evaluator-admission-evidence-checked-in": False,
            "task-admission-producer-source-qualified": False,
            "task-packages-materialized-in-patchloop-format": False,
            "runtime-evaluator-source-qualified-for-these-task-identities": False,
            "broad-registry-optimal-selection-claim-authorized": False,
        },
        "authority": _authority(),
        "next_gate": (
            "preserve-and-source-qualify-the-task-admission-evidence-producer-before-"
            "materializing-runtime-task-packages"
        ),
    }
    return PublicRegistryQualification(**body, content_hash=sha256_json(_jsonable(body)))


def _sha_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _schedule(task_ids: tuple[str, ...]) -> tuple[tuple[ScheduleRow, ...], tuple[str, ...]]:
    a_first = tuple(
        sorted(task_ids, key=lambda task: _sha_text(f"{SCHEDULE_SEED}|orientation|{task}"))[:6]
    )
    a_first_set = set(a_first)
    rows: list[ScheduleRow] = []
    order = 1
    for repetition in (1, 2):
        groups = {
            "a": sorted(
                a_first,
                key=lambda task: _sha_text(
                    f"{SCHEDULE_SEED}|rep={repetition}|orientation-group=a|task={task}"
                ),
            ),
            "c": sorted(
                (task for task in task_ids if task not in a_first_set),
                key=lambda task: _sha_text(
                    f"{SCHEDULE_SEED}|rep={repetition}|orientation-group=c|task={task}"
                ),
            ),
        }
        for half in (0, 1):
            wave = (repetition - 1) * 2 + half + 1
            selected = groups["a"][half * 3 : half * 3 + 3] + groups["c"][half * 3 : half * 3 + 3]
            selected = sorted(
                selected,
                key=lambda task: _sha_text(
                    f"{SCHEDULE_SEED}|rep={repetition}|wave={wave}|task={task}"
                ),
            )
            for task_id in selected:
                no_memory_first = task_id in a_first_set
                if repetition == 2:
                    no_memory_first = not no_memory_first
                conditions = (
                    ("no_memory", "structured") if no_memory_first else ("structured", "no_memory")
                )
                for condition in conditions:
                    projection = {
                        "schedule_seed": SCHEDULE_SEED,
                        "order": order,
                        "wave": wave,
                        "task_id": task_id,
                        "condition": condition,
                        "repetition": repetition,
                    }
                    rows.append(
                        ScheduleRow(
                            order=order,
                            wave=wave,
                            task_id=task_id,
                            condition=condition,
                            repetition=repetition,
                            row_id=sha256_json(projection),
                        )
                    )
                    order += 1
    return tuple(rows), a_first


def build_suite(
    preregistration: AllCrossPreregistration,
    registry: PublicRegistryQualification,
) -> MetadataSuite:
    tasks = tuple(
        MetadataTask(
            task_id=row.instance,
            repository=row.repository,
            package_content_sha256=row.package_content_sha256,
            archive=row.archive,
            environment_image_sha256=row.image_sha256,
            base_commit=row.base_commit,
            resolution_commit_evaluator_only=row.resolution_commit,
            license_spdx=row.license,
        )
        for row in registry.candidates
    )
    rows, a_first = _schedule(tuple(task.task_id for task in tasks))
    body: dict[str, Any] = {
        "schema_version": SUITE_SCHEMA,
        "suite_id": SUITE_ID,
        "status": "METADATA_SUITE_FROZEN_EXECUTION_CLOSED",
        "preregistration_binding": _artifact_binding(
            PREREG_PATH, preregistration, "all-cross-successor-preregistration"
        ),
        "registry_binding": _artifact_binding(
            REGISTRY_PATH, registry, "all-cross-public-registry-qualification"
        ),
        "tasks": tasks,
        "conditions": ("no_memory", "structured"),
        "repetitions": 2,
        "rows": rows,
        "schedule_seed": SCHEDULE_SEED,
        "orientation_a_first_in_repetition_one": a_first,
        "schedule_hash": sha256_json([row.model_dump(mode="json") for row in rows]),
        "runtime_and_cost": _runtime_and_cost(),
        "authority": _authority(),
        "next_gate": (
            "task-admission-source-qualification-and-runtime-task-package-materialization-"
            "not-candidate-creation"
        ),
    }
    return MetadataSuite(**body, content_hash=sha256_json(_jsonable(body)))


def build_activation_plan(
    preregistration: AllCrossPreregistration,
    registry: PublicRegistryQualification,
    suite: MetadataSuite,
) -> ActivationPlan:
    gates = (
        ActivationGate(
            order=1,
            gate="successor-design-and-analysis-freeze",
            status="complete",
            completion_evidence=preregistration.content_hash,
        ),
        ActivationGate(
            order=2,
            gate="public-membership-and-exact-panel-binding",
            status="complete",
            completion_evidence=registry.content_hash,
        ),
        ActivationGate(
            order=3,
            gate="task-admission-producer-and-raw-evidence-source-qualification",
            status="blocked",
            completion_evidence="missing-checked-in-replayable-admission-evidence-bundle",
        ),
        ActivationGate(
            order=4,
            gate="patchloop-public-private-task-package-materialization",
            status="blocked",
            completion_evidence="not-started",
        ),
        ActivationGate(
            order=5,
            gate="task-evaluator-and-lean-runtime-source-qualification",
            status="blocked",
            completion_evidence="not-started",
        ),
        ActivationGate(
            order=6,
            gate="candidate-and-no-call-preflight",
            status="blocked",
            completion_evidence="not-authorized-before-gates-3-through-5",
        ),
        ActivationGate(
            order=7,
            gate="exact-paid-campaign-approval",
            status="blocked",
            completion_evidence="no-candidate-no-approval",
        ),
    )
    body: dict[str, Any] = {
        "schema_version": PLAN_SCHEMA,
        "plan_id": PLAN_ID,
        "status": "ACTIVATION_BLOCKED_BEFORE_CANDIDATE_AND_PREFLIGHT",
        "preregistration_binding": _artifact_binding(
            PREREG_PATH, preregistration, "all-cross-successor-preregistration"
        ),
        "registry_binding": _artifact_binding(
            REGISTRY_PATH, registry, "all-cross-public-registry-qualification"
        ),
        "suite_binding": _artifact_binding(SUITE_PATH, suite, "all-cross-metadata-suite"),
        "gates": gates,
        "first_blocked_gate": 3,
        "candidate_hash": None,
        "no_call_preflight_artifact": None,
        "approval": None,
        "full_schedule_reserve_authorized_usd": 0.0,
        "spend_authorized_usd": 0.0,
        "authority": _authority(),
        "next_gate": "source-qualify-admission-and-materialize-evaluator-separated-task-packages",
    }
    return ActivationPlan(**body, content_hash=sha256_json(_jsonable(body)))


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def artifact_bytes(value: BaseModel) -> bytes:
    return (
        json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _materialize(root: Path, path: str, value: BaseModel) -> FileBinding:
    selected = ensure_within(root, path)
    if selected.is_symlink():
        raise FreshAllCrossSuccessorError(f"all-cross output is a symlink: {path}")
    raw = artifact_bytes(value)
    if selected.exists():
        if selected.read_bytes() != raw:
            raise FreshAllCrossSuccessorError(f"all-cross append-only output differs: {path}")
    else:
        selected.parent.mkdir(parents=True, exist_ok=True)
        try:
            with selected.open("xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            if selected.read_bytes() != raw:
                raise FreshAllCrossSuccessorError(
                    f"all-cross output appeared concurrently with different bytes: {path}"
                ) from None
    return _binding(
        path=path,
        raw=raw,
        role=value.__class__.__name__,
        content_hash=str(value.model_dump(mode="json")["content_hash"]),
    )


def build_all(
    repository: str | Path,
) -> tuple[
    AllCrossPreregistration,
    PublicRegistryQualification,
    MetadataSuite,
    ActivationPlan,
]:
    root = Path(repository).resolve()
    preregistration = build_preregistration(root)
    registry = build_registry(root, preregistration)
    suite = build_suite(preregistration, registry)
    plan = build_activation_plan(preregistration, registry, suite)
    return preregistration, registry, suite, plan


def materialize_all_cross_successor(repository: str | Path) -> tuple[FileBinding, ...]:
    root = Path(repository).resolve()
    preregistration, registry, suite, plan = build_all(root)
    return (
        _materialize(root, PREREG_PATH, preregistration),
        _materialize(root, REGISTRY_PATH, registry),
        _materialize(root, SUITE_PATH, suite),
        _materialize(root, PLAN_PATH, plan),
    )


def _load_model(root: Path, path: str, model: type[BaseModel]) -> BaseModel:
    selected = ensure_within(root, path)
    if selected.is_symlink():
        raise FreshAllCrossSuccessorError(f"all-cross artifact is a symlink: {path}")
    try:
        raw = selected.read_bytes()
    except OSError as exc:
        raise FreshAllCrossSuccessorError(f"all-cross artifact is unavailable: {path}") from exc
    return model.model_validate(_json_object(raw, label=path))


def load_all_cross_successor(
    repository: str | Path,
) -> tuple[
    AllCrossPreregistration,
    PublicRegistryQualification,
    MetadataSuite,
    ActivationPlan,
]:
    root = Path(repository).resolve()
    preregistration = _load_model(root, PREREG_PATH, AllCrossPreregistration)
    registry = _load_model(root, REGISTRY_PATH, PublicRegistryQualification)
    suite = _load_model(root, SUITE_PATH, MetadataSuite)
    plan = _load_model(root, PLAN_PATH, ActivationPlan)
    assert isinstance(preregistration, AllCrossPreregistration)
    assert isinstance(registry, PublicRegistryQualification)
    assert isinstance(suite, MetadataSuite)
    assert isinstance(plan, ActivationPlan)
    expected = build_all(root)
    loaded = (preregistration, registry, suite, plan)
    for actual, rebuilt in zip(loaded, expected, strict=True):
        if actual != rebuilt:
            raise FreshAllCrossSuccessorError(
                "all-cross artifact differs from current exact inputs"
            )
    return loaded
