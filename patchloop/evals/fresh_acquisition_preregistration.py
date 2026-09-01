"""Outcome-blind acquisition preregistration for a fresh Lean Harness A/C panel.

The current dataset manifest contains no unused core task.  This module freezes
how a successor panel may be acquired without opening task packages, consulting
R16 row outcomes, running an agent, or authorizing network/provider/Docker use.
It is deliberately not an executable experiment suite.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.errors import ContractError
from patchloop.util import ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-harness-fresh-acquisition-preregistration-v1"
PREREGISTRATION_ID = "lean-harness-fresh-ac-panel-acquisition-20260817-v1"
STATUS = "PREREGISTERED_ACQUISITION_CLOSED_NO_FRESH_TASKS"
OUTPUT_PATH = "experiments/lean-harness-fresh-acquisition-preregistration-20260817-v1.json"

DATASET_MANIFEST_PATH = "data/dataset-manifest.yaml"
DATASET_MANIFEST_BYTES = 47_368
DATASET_MANIFEST_SHA256 = "sha256:e8cf14ca9dabebcc03c3522e400dfcb79606541e9b11e59f49510ea5c40bebed"
HELDOUT_PREREGISTRATION_PATH = "experiments/heldout-ac-preregistration-20260814-v1.yaml"
HELDOUT_PREREGISTRATION_BYTES = 31_338
HELDOUT_PREREGISTRATION_SHA256 = (
    "sha256:f6d9d015329823f3f888aac5f15296b2ddefda9e45b5d5501b8d94587bb11d8f"
)
HELDOUT_PREREGISTRATION_CONTENT_HASH = (
    "sha256:3b75f049649850b7561f310229e1e5429f72ea24024e835ccf4910fb2c901f74"
)
R16_INDEX_PATH = "reports/heldout-ac/artifacts/heldout-ac-r16-campaign-complete-r1.json"
R16_INDEX_BYTES = 10_375
R16_INDEX_SHA256 = "sha256:999fa9e42f010b03b96013d089f662ad3f50b1c5c6469b2aa8ddb901c522391e"
R16_INDEX_CONTENT_HASH = "sha256:945e8e9ff1df60a255d20fb406ca7b7ab20ca16a3b50da5cbce12f2fb38a6521"
LEAN_SOURCE_QUALIFICATION_PATH = (
    "experiments/lean-harness-runtime-source-qualification-20260817-v1.json"
)
LEAN_SOURCE_QUALIFICATION_BYTES = 72_420
LEAN_SOURCE_QUALIFICATION_SHA256 = (
    "sha256:7104310a700822bde8343b7ed37facdb3fa09709ced41540cb9ccb431642fdab"
)
LEAN_SOURCE_QUALIFICATION_CONTENT_HASH = (
    "sha256:b0f28eb86eb8463c389708af500dede582048c3f7910876dac5aa9d610768226"
)

ROLE_COUNTS = {
    "calibration": 5,
    "memory-development": 6,
    "development-validation": 2,
    "core-same-repo": 6,
    "core-cross-repo": 6,
}
SAME_REPOSITORY_TARGETS = (
    "agronholm/anyio",
    "delgan/loguru",
    "huggingface/huggingface_hub",
    "pdm-project/pdm",
    "pytest-dev/pyfakefs",
    "tox-dev/tox",
)


class FreshAcquisitionPreregistrationError(ContractError):
    """The fresh-panel acquisition preregistration is invalid or has drifted."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class FileBinding(FrozenModel):
    path: str
    file_bytes: int = Field(ge=1)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    role: Literal[
        "frozen-dataset-registry",
        "consumed-panel-preregistration",
        "consumed-panel-evidence-index",
        "qualified-lean-runtime-source",
    ]


class CurrentPoolAudit(FrozenModel):
    manifest_task_count: Literal[25]
    role_counts: dict[str, int]
    consumed_core_task_count: Literal[12]
    unused_core_task_count: Literal[0]
    eligible_fresh_task_count: Literal[0]
    current_manifest_can_supply_fresh_panel: Literal[False]
    current_core_exactly_matches_consumed_preregistration: Literal[True]
    existing_task_identity_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    existing_repository_set_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    consumed_core_identity_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if self.role_counts != ROLE_COUNTS:
            raise ValueError("current dataset role counts differ")
        return self


class AcquisitionDesign(FrozenModel):
    candidate_source_family: Literal["SWE-rebench-leaderboard"]
    source_snapshot_selection: Literal[
        "earliest-published-immutable-revision-after-2026-08-16-containing-the-complete-frozen-window"
    ]
    source_window_start_exclusive: Literal["2026-03-17T23:59:59Z"]
    source_window_end_inclusive: Literal["2026-08-16T23:59:59Z"]
    source_window_basis: Literal[
        "public-issue-created-and-resolution-merged-after-model-snapshot-before-preregistration"
    ]
    registry_completeness_evidence: Literal[
        "immutable-source-snapshot-plus-complete-query-transcript-and-append-only-rejection-log"
    ]
    target_task_count: Literal[12]
    same_repository_task_count: Literal[6]
    cross_repository_task_count: Literal[6]
    same_repository_targets: tuple[str, ...]
    same_repository_selection: Literal[
        "one-lowest-ranked-eligible-new-instance-per-frozen-repository"
    ]
    cross_repository_selection: Literal[
        "six-lowest-ranked-eligible-instances-with-one-per-new-repository"
    ]
    cross_repository_disjoint_from_all_current_manifest_repositories: Literal[True]
    ranking_preimage: Literal[
        "lean-fresh-acquisition-20260817-v1|stratum={stratum}|repo={lowercase_repo}|instance={canonical_public_instance_id}"
    ]
    ranking_algorithm: Literal["ascending-sha256-utf8"]
    minimum_difficulty_tier: Literal["medium"]
    minimum_reference_pass_runs: Literal[3]
    minimum_rejected_bad_patches: Literal[8]
    required_admission_states: tuple[
        Literal[
            "base-visible-pass",
            "base-hidden-fail",
            "reference-visible-hidden-scope-safety-pass",
            "environment-image-digest-bound",
            "public-private-spec-hashes-bound",
            "license-compatible",
        ],
        ...,
    ]
    excluded_identity_dimensions: tuple[
        Literal[
            "task-id-and-version",
            "benchmark-instance-id",
            "issue-or-pull-request-url",
            "upstream-base-or-resolution-commit",
            "solution-lineage-id",
            "public-or-private-spec-hash",
        ],
        ...,
    ]
    experimental_model_runs_during_acquisition: Literal[0]
    r16_row_outcomes_or_traces_used_for_selection: Literal[False]
    condition_specific_selection_allowed: Literal[False]
    replacement_rule: Literal["next-ranked-eligible-candidate-with-recorded-rejection-code"]
    insufficient_pool_rule: Literal[
        "stop-without-relaxation-and-require-a-successor-preregistration-before-new-screening"
    ]

    @model_validator(mode="after")
    def validate_design(self) -> Self:
        if self.same_repository_targets != SAME_REPOSITORY_TARGETS:
            raise ValueError("same-repository acquisition targets differ")
        if len(self.required_admission_states) != 6 or len(self.excluded_identity_dimensions) != 6:
            raise ValueError("fresh acquisition safeguards differ")
        return self


class EventualExperimentDesign(FrozenModel):
    conditions: tuple[Literal["no_memory", "structured"], ...]
    repetitions_per_task: Literal[2]
    expected_rows_after_panel_seal: Literal[48]
    harness: Literal["lean-harness-v1"]
    tool_schema: Literal["v7"]
    phase_evidence: Literal["phase-evidence-v12"]
    memory_policy: Literal["fixed-d110-bundle-v1"]
    treatment_difference_only_memory: Literal[True]
    equal_condition_budget_required: Literal[True]
    runtime_budget_binding: Literal["pending-public-development-provider-qualification"]
    pricing_and_hard_cap_binding: Literal["pending-before-candidate-and-before-any-panel-outcome"]
    primary_outcome: Literal["scheduled-row-success-at-frozen-budget"]
    primary_estimand: Literal["equal-task-weighted-mean-over-two-paired-repetitions"]
    complete_panel_required: Literal[True]
    typed_token_terminals_score_zero: Literal[True]
    typed_token_terminals_block_added_compute_interpretation: Literal[True]
    partial_panel_primary_analysis_authorized: Literal[False]
    causal_population_or_uncontaminated_claim_authorized: Literal[False]

    @model_validator(mode="after")
    def validate_experiment(self) -> Self:
        if self.conditions != ("no_memory", "structured"):
            raise ValueError("fresh experiment conditions differ")
        return self


class StoppingRules(FrozenModel):
    stop_on_current_manifest_task_reuse: Literal[True]
    stop_on_r16_outcome_informed_selection_or_threshold: Literal[True]
    stop_on_private_or_reference_material_in_agent_memory: Literal[True]
    stop_on_agent_or_provider_run_before_full_design_seal: Literal[True]
    stop_on_registry_or_rejection_log_incompleteness: Literal[True]
    stop_on_runtime_source_or_predecessor_drift: Literal[True]
    no_retry_replacement_resume_or_pooling_after_outcome_access: Literal[True]


class Authority(FrozenModel):
    current_manifest_files_read: Literal[1]
    consumed_preregistration_files_read: Literal[1]
    consumed_r16_index_files_read: Literal[1]
    lean_source_qualification_files_read: Literal[1]
    task_package_files_read: Literal[0]
    private_task_files_read: Literal[0]
    r16_runtime_or_trace_files_read: Literal[0]
    network_calls: Literal[0]
    docker_calls: Literal[0]
    provider_calls: Literal[0]
    evaluator_calls: Literal[0]
    agent_runs: Literal[0]
    added_model_cost_usd: Literal[0]
    candidate_registry_materialized: Literal[False]
    fresh_task_panel_materialized: Literal[False]
    full_experiment_preregistered: Literal[False]
    runtime_source_qualified_for_fresh_panel: Literal[False]
    candidate_created: Literal[False]
    approval_granted: Literal[False]
    execution_authorized: Literal[False]
    memory_effect_analysis_authorized: Literal[False]


class FreshAcquisitionPreregistration(FrozenModel):
    schema_version: Literal[SCHEMA_VERSION]
    preregistration_id: Literal[PREREGISTRATION_ID]
    status: Literal[STATUS]
    preregistered_at: str = Field(pattern=r"^2026-08-(?:16|17)T[0-9:.]+Z$")
    predecessor_bindings: tuple[FileBinding, ...]
    current_pool_audit: CurrentPoolAudit
    acquisition_design: AcquisitionDesign
    eventual_experiment_design: EventualExperimentDesign
    stopping_rules: StoppingRules
    authority: Authority
    next_gate: Literal[
        "materialize-and-audit-the-frozen-public-candidate-registry-before-any-task-package-or-runtime-activation"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_content_hash(self) -> Self:
        if len(self.predecessor_bindings) != 4:
            raise ValueError("fresh acquisition predecessor binding count differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("fresh acquisition content hash differs")
        return self


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise FreshAcquisitionPreregistrationError(f"duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def _json_object(raw: bytes, *, label: str) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise FreshAcquisitionPreregistrationError(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FreshAcquisitionPreregistrationError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise FreshAcquisitionPreregistrationError(f"{label} must be an object")
    return value


def _yaml_object(raw: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = yaml.load(raw, Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise FreshAcquisitionPreregistrationError(f"{label} is invalid YAML") from exc
    if not isinstance(value, dict):
        raise FreshAcquisitionPreregistrationError(f"{label} must be an object")
    return value


def _binding_rows() -> tuple[FileBinding, ...]:
    return (
        FileBinding(
            path=DATASET_MANIFEST_PATH,
            file_bytes=DATASET_MANIFEST_BYTES,
            file_sha256=DATASET_MANIFEST_SHA256,
            role="frozen-dataset-registry",
        ),
        FileBinding(
            path=HELDOUT_PREREGISTRATION_PATH,
            file_bytes=HELDOUT_PREREGISTRATION_BYTES,
            file_sha256=HELDOUT_PREREGISTRATION_SHA256,
            content_hash=HELDOUT_PREREGISTRATION_CONTENT_HASH,
            role="consumed-panel-preregistration",
        ),
        FileBinding(
            path=R16_INDEX_PATH,
            file_bytes=R16_INDEX_BYTES,
            file_sha256=R16_INDEX_SHA256,
            content_hash=R16_INDEX_CONTENT_HASH,
            role="consumed-panel-evidence-index",
        ),
        FileBinding(
            path=LEAN_SOURCE_QUALIFICATION_PATH,
            file_bytes=LEAN_SOURCE_QUALIFICATION_BYTES,
            file_sha256=LEAN_SOURCE_QUALIFICATION_SHA256,
            content_hash=LEAN_SOURCE_QUALIFICATION_CONTENT_HASH,
            role="qualified-lean-runtime-source",
        ),
    )


def _read_exact(root: Path, binding: FileBinding) -> bytes:
    selected = ensure_within(root, binding.path)
    if selected.is_symlink():
        raise FreshAcquisitionPreregistrationError(
            f"fresh acquisition binding is a symlink: {binding.path}"
        )
    try:
        raw = selected.read_bytes()
    except OSError as exc:
        raise FreshAcquisitionPreregistrationError(
            f"fresh acquisition binding is unavailable: {binding.path}"
        ) from exc
    if len(raw) != binding.file_bytes or sha256_bytes(raw) != binding.file_sha256:
        raise FreshAcquisitionPreregistrationError(
            f"fresh acquisition binding differs: {binding.path}"
        )
    return raw


def _task_identity(task: dict[str, Any]) -> dict[str, Any]:
    source = task.get("source") or {}
    return {
        "task_id": task.get("task_id"),
        "task_version": task.get("task_version"),
        "role": task.get("role"),
        "benchmark_instance_id": source.get("benchmark_instance_id"),
        "upstream_repository": source.get("upstream_repository"),
        "issue_url": source.get("issue_url"),
        "pull_request_url": source.get("pull_request_url"),
        "upstream_base_commit": source.get("upstream_base_commit"),
        "resolution_commit": source.get("resolution_commit"),
        "solution_lineage_id": task.get("solution_lineage_id"),
        "public_spec_hash": task.get("public_spec_hash"),
        "private_spec_hash": task.get("private_spec_hash"),
    }


def _pool_audit(manifest: dict[str, Any], consumed: dict[str, Any]) -> CurrentPoolAudit:
    tasks = manifest.get("tasks")
    consumed_tasks = (consumed.get("dataset") or {}).get("tasks")
    if not isinstance(tasks, list) or not isinstance(consumed_tasks, list):
        raise FreshAcquisitionPreregistrationError("fresh acquisition task registries are invalid")
    if len(tasks) != 25 or len(consumed_tasks) != 12:
        raise FreshAcquisitionPreregistrationError("fresh acquisition task counts differ")
    role_counts: dict[str, int] = {}
    for task in tasks:
        if not isinstance(task, dict) or not isinstance(task.get("role"), str):
            raise FreshAcquisitionPreregistrationError("fresh acquisition manifest task is invalid")
        role_counts[task["role"]] = role_counts.get(task["role"], 0) + 1
    core = [task for task in tasks if str(task.get("role", "")).startswith("core-")]
    core_projection = sorted(
        (
            task.get("task_id"),
            task.get("task_version"),
            task.get("role"),
            task.get("public_spec_hash"),
            task.get("private_spec_hash"),
        )
        for task in core
    )
    consumed_projection = sorted(
        (
            task.get("task_id"),
            task.get("task_version"),
            task.get("role"),
            task.get("public_spec_hash"),
            task.get("private_spec_hash"),
        )
        for task in consumed_tasks
    )
    if role_counts != ROLE_COUNTS or core_projection != consumed_projection:
        raise FreshAcquisitionPreregistrationError("current core pool differs from consumed panel")
    memory_repositories = tuple(
        sorted(
            str((task.get("source") or {}).get("upstream_repository", "")).lower()
            for task in tasks
            if task.get("role") == "memory-development"
        )
    )
    if memory_repositories != SAME_REPOSITORY_TARGETS:
        raise FreshAcquisitionPreregistrationError("same-repository acquisition targets differ")
    repositories = sorted(
        {
            str((task.get("source") or {}).get("upstream_repository", "")).lower()
            for task in tasks
            if (task.get("source") or {}).get("upstream_repository")
        }
    )
    identities = sorted(
        (_task_identity(task) for task in tasks), key=lambda item: str(item["task_id"])
    )
    return CurrentPoolAudit(
        manifest_task_count=25,
        role_counts=role_counts,
        consumed_core_task_count=12,
        unused_core_task_count=0,
        eligible_fresh_task_count=0,
        current_manifest_can_supply_fresh_panel=False,
        current_core_exactly_matches_consumed_preregistration=True,
        existing_task_identity_hash=sha256_json(identities),
        existing_repository_set_hash=sha256_json(repositories),
        consumed_core_identity_hash=sha256_json(core_projection),
    )


def _acquisition_design() -> AcquisitionDesign:
    return AcquisitionDesign(
        candidate_source_family="SWE-rebench-leaderboard",
        source_snapshot_selection=(
            "earliest-published-immutable-revision-after-2026-08-16-containing-the-complete-"
            "frozen-window"
        ),
        source_window_start_exclusive="2026-03-17T23:59:59Z",
        source_window_end_inclusive="2026-08-16T23:59:59Z",
        source_window_basis=(
            "public-issue-created-and-resolution-merged-after-model-snapshot-before-preregistration"
        ),
        registry_completeness_evidence=(
            "immutable-source-snapshot-plus-complete-query-transcript-and-append-only-rejection-log"
        ),
        target_task_count=12,
        same_repository_task_count=6,
        cross_repository_task_count=6,
        same_repository_targets=SAME_REPOSITORY_TARGETS,
        same_repository_selection="one-lowest-ranked-eligible-new-instance-per-frozen-repository",
        cross_repository_selection=(
            "six-lowest-ranked-eligible-instances-with-one-per-new-repository"
        ),
        cross_repository_disjoint_from_all_current_manifest_repositories=True,
        ranking_preimage=(
            "lean-fresh-acquisition-20260817-v1|stratum={stratum}|repo={lowercase_repo}|"
            "instance={canonical_public_instance_id}"
        ),
        ranking_algorithm="ascending-sha256-utf8",
        minimum_difficulty_tier="medium",
        minimum_reference_pass_runs=3,
        minimum_rejected_bad_patches=8,
        required_admission_states=(
            "base-visible-pass",
            "base-hidden-fail",
            "reference-visible-hidden-scope-safety-pass",
            "environment-image-digest-bound",
            "public-private-spec-hashes-bound",
            "license-compatible",
        ),
        excluded_identity_dimensions=(
            "task-id-and-version",
            "benchmark-instance-id",
            "issue-or-pull-request-url",
            "upstream-base-or-resolution-commit",
            "solution-lineage-id",
            "public-or-private-spec-hash",
        ),
        experimental_model_runs_during_acquisition=0,
        r16_row_outcomes_or_traces_used_for_selection=False,
        condition_specific_selection_allowed=False,
        replacement_rule="next-ranked-eligible-candidate-with-recorded-rejection-code",
        insufficient_pool_rule=(
            "stop-without-relaxation-and-require-a-successor-preregistration-before-new-screening"
        ),
    )


def _experiment_design() -> EventualExperimentDesign:
    return EventualExperimentDesign(
        conditions=("no_memory", "structured"),
        repetitions_per_task=2,
        expected_rows_after_panel_seal=48,
        harness="lean-harness-v1",
        tool_schema="v7",
        phase_evidence="phase-evidence-v12",
        memory_policy="fixed-d110-bundle-v1",
        treatment_difference_only_memory=True,
        equal_condition_budget_required=True,
        runtime_budget_binding="pending-public-development-provider-qualification",
        pricing_and_hard_cap_binding="pending-before-candidate-and-before-any-panel-outcome",
        primary_outcome="scheduled-row-success-at-frozen-budget",
        primary_estimand="equal-task-weighted-mean-over-two-paired-repetitions",
        complete_panel_required=True,
        typed_token_terminals_score_zero=True,
        typed_token_terminals_block_added_compute_interpretation=True,
        partial_panel_primary_analysis_authorized=False,
        causal_population_or_uncontaminated_claim_authorized=False,
    )


def _stopping_rules() -> StoppingRules:
    return StoppingRules(
        stop_on_current_manifest_task_reuse=True,
        stop_on_r16_outcome_informed_selection_or_threshold=True,
        stop_on_private_or_reference_material_in_agent_memory=True,
        stop_on_agent_or_provider_run_before_full_design_seal=True,
        stop_on_registry_or_rejection_log_incompleteness=True,
        stop_on_runtime_source_or_predecessor_drift=True,
        no_retry_replacement_resume_or_pooling_after_outcome_access=True,
    )


def _authority() -> Authority:
    return Authority(
        current_manifest_files_read=1,
        consumed_preregistration_files_read=1,
        consumed_r16_index_files_read=1,
        lean_source_qualification_files_read=1,
        task_package_files_read=0,
        private_task_files_read=0,
        r16_runtime_or_trace_files_read=0,
        network_calls=0,
        docker_calls=0,
        provider_calls=0,
        evaluator_calls=0,
        agent_runs=0,
        added_model_cost_usd=0,
        candidate_registry_materialized=False,
        fresh_task_panel_materialized=False,
        full_experiment_preregistered=False,
        runtime_source_qualified_for_fresh_panel=False,
        candidate_created=False,
        approval_granted=False,
        execution_authorized=False,
        memory_effect_analysis_authorized=False,
    )


def build_fresh_acquisition_preregistration(
    repository: str | Path = ".", *, preregistered_at: str
) -> FreshAcquisitionPreregistration:
    root = Path(repository).resolve()
    try:
        parsed_time = datetime.fromisoformat(preregistered_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FreshAcquisitionPreregistrationError("preregistered_at is invalid") from exc
    if parsed_time.tzinfo is None or parsed_time.utcoffset() is None:
        raise FreshAcquisitionPreregistrationError("preregistered_at must include UTC authority")

    bindings = _binding_rows()
    raw_by_role = {binding.role: _read_exact(root, binding) for binding in bindings}
    manifest = _yaml_object(raw_by_role["frozen-dataset-registry"], label="dataset manifest")
    consumed = _yaml_object(
        raw_by_role["consumed-panel-preregistration"], label="consumed panel preregistration"
    )
    lean = _json_object(
        raw_by_role["qualified-lean-runtime-source"], label="Lean source qualification"
    )
    if not (
        lean.get("content_hash") == LEAN_SOURCE_QUALIFICATION_CONTENT_HASH
        and lean.get("status") == "PUBLIC_MOCK_RUNTIME_SOURCE_QUALIFIED_NO_PROVIDER_AUTHORITY"
        and lean.get("provider_calls_authorized") is False
        and lean.get("paid_execution_authorized") is False
        and lean.get("fresh_memory_comparison_authorized") is False
    ):
        raise FreshAcquisitionPreregistrationError("Lean source qualification authority differs")

    body = {
        "schema_version": SCHEMA_VERSION,
        "preregistration_id": PREREGISTRATION_ID,
        "status": STATUS,
        "preregistered_at": preregistered_at,
        "predecessor_bindings": bindings,
        "current_pool_audit": _pool_audit(manifest, consumed),
        "acquisition_design": _acquisition_design(),
        "eventual_experiment_design": _experiment_design(),
        "stopping_rules": _stopping_rules(),
        "authority": _authority(),
        "next_gate": (
            "materialize-and-audit-the-frozen-public-candidate-registry-before-any-task-package-"
            "or-runtime-activation"
        ),
    }
    json_body = {
        key: value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        for key, value in body.items()
    }
    json_body["predecessor_bindings"] = [binding.model_dump(mode="json") for binding in bindings]
    return FreshAcquisitionPreregistration(
        **body,
        content_hash=sha256_json(json_body),
    )


def preregistration_bytes(preregistration: FreshAcquisitionPreregistration) -> bytes:
    return (
        json.dumps(
            preregistration.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _validate_current_bindings(root: Path, value: FreshAcquisitionPreregistration) -> None:
    if value.predecessor_bindings != _binding_rows():
        raise FreshAcquisitionPreregistrationError("fresh acquisition predecessor bindings differ")
    raw_by_role = {
        binding.role: _read_exact(root, binding) for binding in value.predecessor_bindings
    }
    expected_pool = _pool_audit(
        _yaml_object(raw_by_role["frozen-dataset-registry"], label="dataset manifest"),
        _yaml_object(
            raw_by_role["consumed-panel-preregistration"],
            label="consumed panel preregistration",
        ),
    )
    if value.current_pool_audit != expected_pool:
        raise FreshAcquisitionPreregistrationError("fresh acquisition pool audit differs")
    if not (
        value.acquisition_design == _acquisition_design()
        and value.eventual_experiment_design == _experiment_design()
        and value.stopping_rules == _stopping_rules()
        and value.authority == _authority()
    ):
        raise FreshAcquisitionPreregistrationError("fresh acquisition frozen design differs")


def load_fresh_acquisition_preregistration(
    repository: str | Path = ".", path: str = OUTPUT_PATH
) -> FreshAcquisitionPreregistration:
    root = Path(repository).resolve()
    selected = ensure_within(root, path)
    raw = selected.read_bytes()
    _json_object(raw, label="fresh acquisition preregistration")
    try:
        value = FreshAcquisitionPreregistration.model_validate_json(raw)
    except ValueError as exc:
        raise FreshAcquisitionPreregistrationError(
            "fresh acquisition preregistration contract is invalid"
        ) from exc
    if preregistration_bytes(value) != raw:
        raise FreshAcquisitionPreregistrationError(
            "fresh acquisition preregistration bytes are not canonical"
        )
    _validate_current_bindings(root, value)
    return value


def materialize_fresh_acquisition_preregistration(
    repository: str | Path = ".",
    path: str = OUTPUT_PATH,
    *,
    preregistered_at: str | None = None,
) -> FreshAcquisitionPreregistration:
    root = Path(repository).resolve()
    selected = ensure_within(root, path)
    if selected.exists():
        return load_fresh_acquisition_preregistration(root, path)
    now = preregistered_at or datetime.now(UTC).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )
    value = build_fresh_acquisition_preregistration(root, preregistered_at=now)
    raw = preregistration_bytes(value)
    selected.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(selected, flags, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        raise
    return load_fresh_acquisition_preregistration(root, path)
