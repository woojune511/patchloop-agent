"""Append-only held-out task/evaluator template and pricing materialization.

This gate is deliberately narrower than an execution candidate.  It opens the
12 preregistered task packages inside the evaluator-side process, validates
their private files, and persists only opaque hashes, counts, and a
run-secret-independent evaluator-v2 contract template.  It never serializes a
private marker, hidden check identifier, hidden path, reference patch, or task
content.

R5 is a cost-only successor.  It reuses the exact opaque task bindings and the
R1-origin official pricing capture from immutable R4, then applies the sealed
development-evidence budget amendment.  It does not reopen a task package and
makes no added pricing GET.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.contracts import TaskPackage, build_evaluator_contract_binding
from patchloop.errors import ContractError
from patchloop.evals.evaluator_v2_source_qualification import (
    evaluator_v2_task_private_markers,
)
from patchloop.evals.heldout_ac_budget_amendment import (
    AMENDMENT_CONTENT_HASH,
    FULL_SCHEDULE_RESERVE_NANOS,
    HARD_CAP_NANOS,
    HARD_CAP_SLACK_NANOS,
    MAX_CUMULATIVE_INPUT_TOKENS,
    MAX_CUMULATIVE_OUTPUT_TOKENS,
    PER_RUN_RESERVE_NANOS,
    HeldoutACBudgetAmendmentBinding,
    heldout_ac_budget_amendment_binding,
)
from patchloop.evals.heldout_ac_contracts import HeldoutACFrozenModel
from patchloop.evals.heldout_ac_task_evaluator import (
    HeldoutACTaskEvaluatorBindingPlan,
    HeldoutACTaskMetadataBinding,
    load_heldout_ac_task_evaluator_plan,
)
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package
from patchloop.util import ensure_within, safe_relative_path, sha256_bytes, sha256_json, sha256_text
from patchloop.verifier.evidence import evaluator_v2_marker_set_hash
from patchloop.verifier.runtime_evidence import build_evaluator_safety_contract_v2

SCHEMA_VERSION = "heldout-ac-task-pricing-materialization-v5"
MATERIALIZATION_ID = "core-ac-fixed-bundle-heldout-task-pricing-20260815-r5"
STATUS = "OPAQUE_TASK_EVALUATOR_TEMPLATES_MATERIALIZED_RETAINED_PRICING_RUNTIME_CLOSED"
OUTPUT_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-task-pricing-materialization-r5.json")
R9_PATH = Path(
    "reports/heldout-ac/artifacts/heldout-ac-binding-adapter-source-qualification-r9.json"
)
R9_FILE_BYTES = 5_683
R9_FILE_SHA256 = "sha256:6b1597d3b0f4202aeadaa424b67e06ec6e37ff7abfd8fd62f4af23208f3aaf68"
R9_CONTENT_HASH = "sha256:a26bb59cb5b16d6d3a94676b195b3fb36a21e974216088780c90c92aaac2bd2b"
R9_SOURCE_HASH = "sha256:04eeab81a9a8130dbe5624068317ee3d68711465d18e3e8032ffbeb92e3fdcf6"
R9_CONTRACT_SOURCE_HASH = "sha256:77de0d1519cfc7032bda023bf1f1cca86449533fe3a1be39887d5784fc2d013b"
R4_PATH = Path("reports/heldout-ac/artifacts/heldout-ac-task-pricing-materialization-r4.json")
R4_FILE_BYTES = 52_056
R4_FILE_SHA256 = "sha256:37c5cb805e137e55f5b0a11b3a3235dc0514aa2a77938abfc6d74695113d5380"
R4_CONTENT_HASH = "sha256:7c6ecc31b471da83cf46ddb5a3fb687008e4a6648ae55485d0109e0d6114af58"
R4_SOURCE_HASH = "sha256:010b8c1fd2d46c58a56976fd1ce750f4640e54a8d38758beecbe3c75e896b888"
R4_TASK_BINDINGS_HASH = "sha256:10505056de7f4bd95a06f9c3a16414ce120442c485413e52d113c2aba4c5157f"
LEGACY_PRICING_HASH = "sha256:03e9cde4d6d04a09995da669d7e3aea26fda31310615640508f6bd0a9c2cbd34"
PRICING_HASH = "sha256:83bb15d171564f32d0ca6df24f733a957032e144bbd0dfed49071e1b205a27e9"
TEMPLATE_BINDING_SOURCE_HASH = (
    "sha256:20eb314516985fd6aa8e7f1970fd754bb3c839607f5b73b55f526b305662118c"
)
PLAN_HASH = "sha256:34edbad3f5a31f5d7e16ed2358905c195372a0d1f420c0ac03bd3be6a68668a8"
NEXT_GATE = "qualify-executable-heldout-runner-and-runtime-secret-boundary-before-candidate"

SOURCE_PATHS = tuple(
    sorted(
        (
            Path("patchloop/agent/tools.py"),
            Path("patchloop/contracts.py"),
            Path("patchloop/evals/evaluator_v2_source_qualification.py"),
            Path("patchloop/evals/heldout_ac_binding_source_qualification.py"),
            Path("patchloop/evals/heldout_ac_budget_amendment.py"),
            Path("patchloop/evals/heldout_ac_contracts.py"),
            Path("patchloop/evals/heldout_ac_suite.py"),
            Path("patchloop/evals/heldout_ac_task_evaluator.py"),
            Path("patchloop/evals/heldout_ac_task_pricing_materialization.py"),
            Path("patchloop/task_loader.py"),
            Path("patchloop/util.py"),
            Path("patchloop/verifier/evidence.py"),
            Path("patchloop/verifier/runtime_evidence.py"),
        ),
        key=lambda item: item.as_posix(),
    )
)
VALIDATION_PATHS = tuple(
    sorted(
        (
            Path("scripts/build_heldout_ac_task_pricing_materialization.py"),
            Path("tests/test_heldout_ac_budget_amendment.py"),
            Path("tests/test_heldout_ac_task_pricing_materialization.py"),
        ),
        key=lambda item: item.as_posix(),
    )
)


class HeldoutACTaskPricingMaterializationError(ContractError):
    pass


class FileBinding(HeldoutACFrozenModel):
    path: str
    file_bytes: int = Field(ge=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class R9BindingSourcePredecessor(FileBinding):
    path: Literal[
        "reports/heldout-ac/artifacts/heldout-ac-binding-adapter-source-qualification-r9.json"
    ]
    file_bytes: Literal[R9_FILE_BYTES]
    file_sha256: Literal[R9_FILE_SHA256]
    source_qualification_hash: Literal[R9_CONTENT_HASH]
    source_hash: Literal[R9_SOURCE_HASH]
    contract_source_qualification_hash: Literal[R9_CONTRACT_SOURCE_HASH]
    task_evaluator_plan_content_hash: Literal[PLAN_HASH]
    original_status: Literal[
        "OFFLINE_BINDING_ADAPTER_SOURCE_QUALIFIED_RUNTIME_MATERIALIZATION_CLOSED"
    ]


class R4MaterializationPredecessor(FileBinding):
    path: Literal["reports/heldout-ac/artifacts/heldout-ac-task-pricing-materialization-r4.json"]
    file_bytes: Literal[R4_FILE_BYTES]
    file_sha256: Literal[R4_FILE_SHA256]
    content_hash: Literal[R4_CONTENT_HASH]
    source_hash: Literal[R4_SOURCE_HASH]
    task_bindings_hash: Literal[R4_TASK_BINDINGS_HASH]
    pricing_binding_hash: Literal[LEGACY_PRICING_HASH]
    original_status: Literal[
        "OPAQUE_TASK_EVALUATOR_TEMPLATES_MATERIALIZED_RETAINED_PRICING_RUNTIME_CLOSED"
    ]
    disposition: Literal["invalidated-by-development-budget-amendment-successor"]
    invalidation_reason: Literal["post-r4-development-evidence-budget-amendment"]
    current_source_replay_valid: Literal[False]
    retained_task_bindings_reused: Literal[True]
    retained_pricing_capture_reused: Literal[True]


class TaskPackageFileProjection(HeldoutACFrozenModel):
    public_yaml_bytes: int = Field(ge=1)
    public_yaml_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_yaml_bytes: int = Field(ge=1)
    private_yaml_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    environment_yaml_bytes: int = Field(ge=1)
    environment_yaml_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    reference_patch_bytes: int = Field(ge=1)
    reference_patch_content_commitment: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    hidden_artifact_count: int = Field(ge=0)
    hidden_artifact_total_bytes: int = Field(ge=0)
    hidden_artifact_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_content_hash(self) -> TaskPackageFileProjection:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out task file projection content hash mismatch")
        return self


class TaskEvaluatorTemplateBinding(HeldoutACFrozenModel):
    schema_version: Literal["heldout-ac-task-evaluator-template-binding-v4"] = (
        "heldout-ac-task-evaluator-template-binding-v4"
    )
    task: HeldoutACTaskMetadataBinding
    package_files: TaskPackageFileProjection
    base_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    visible_check_count: int = Field(ge=1)
    hidden_check_count: int = Field(ge=1)
    task_private_marker_count: int = Field(ge=1)
    task_private_marker_set_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    baseline_private_contract_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    run_secret_independent_contract_template_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    hidden_check_ids_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    regression_check_ids_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    scope_check_ids_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    registered_check_specs_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    binding_projection_source_hash: Literal[TEMPLATE_BINDING_SOURCE_HASH]
    runtime_secret_markers_materialized: Literal[0] = 0
    final_evaluator_contract_materialized: Literal[False] = False
    private_values_serialized: Literal[False] = False
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_binding(self) -> TaskEvaluatorTemplateBinding:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out task/evaluator template content hash mismatch")
        return self


class LegacyOfficialPricingBinding(HeldoutACFrozenModel):
    schema_version: Literal["heldout-ac-official-pricing-binding-v1"] = (
        "heldout-ac-official-pricing-binding-v1"
    )
    model_id: Literal["gpt-5.4-mini-2026-03-17"]
    official_model_page_url: Literal[
        "https://developers.openai.com/api/docs/models/gpt-5.4-mini.md"
    ]
    observed_at: datetime
    official_capture: dict[str, Any]
    official_capture_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    input_usd_per_million: Literal[0.75]
    cached_input_usd_per_million: Literal[0.075]
    output_usd_per_million: Literal[4.5]
    cache_write_price_published: Literal[False] = False
    cache_write_reserve_policy: Literal["use-uncached-input-rate"] = "use-uncached-input-rate"
    price_nanos_per_token: dict[
        Literal["uncached_input", "cached_input", "cache_write_input", "output"], int
    ]
    max_cumulative_input_tokens_per_run: Literal[4_000_000]
    max_cumulative_output_tokens_per_run: Literal[500_000]
    scheduled_runs: Literal[48]
    per_run_reserve_nanos: Literal[5_250_000_000]
    full_schedule_reserve_nanos: Literal[252_000_000_000]
    hard_cap_nanos: Literal[275_000_000_000]
    hard_cap_slack_nanos: Literal[23_000_000_000]
    rates_match_preregistered_planning_rates: Literal[True]
    supersedes_planning_timestamp: Literal[True]
    candidate_must_bind_this_exact_observation: Literal[True]
    execution_candidate_created: Literal[False] = False
    content_hash: Literal[LEGACY_PRICING_HASH]

    @model_validator(mode="after")
    def validate_pricing(self) -> LegacyOfficialPricingBinding:
        if self.official_capture_hash != sha256_json(dict(self.official_capture)):
            raise ValueError("held-out retained official pricing capture hash differs")
        expected_prices = {
            "uncached_input": 750,
            "cached_input": 75,
            "cache_write_input": 750,
            "output": 4_500,
        }
        if self.price_nanos_per_token != expected_prices:
            raise ValueError("held-out token price nanos differ")
        if (
            self.max_cumulative_input_tokens_per_run * expected_prices["uncached_input"]
            + self.max_cumulative_output_tokens_per_run * expected_prices["output"]
            != self.per_run_reserve_nanos
            or self.per_run_reserve_nanos * self.scheduled_runs != self.full_schedule_reserve_nanos
            or self.hard_cap_nanos - self.full_schedule_reserve_nanos != self.hard_cap_slack_nanos
        ):
            raise ValueError("held-out pricing reserve arithmetic differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != LEGACY_PRICING_HASH or self.content_hash != expected:
            raise ValueError("held-out official pricing binding content hash mismatch")
        return self


class OfficialPricingBinding(HeldoutACFrozenModel):
    schema_version: Literal["heldout-ac-official-pricing-binding-v2"] = (
        "heldout-ac-official-pricing-binding-v2"
    )
    model_id: Literal["gpt-5.4-mini-2026-03-17"]
    official_model_page_url: Literal[
        "https://developers.openai.com/api/docs/models/gpt-5.4-mini.md"
    ]
    observed_at: datetime
    official_capture: dict[str, Any]
    official_capture_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    input_usd_per_million: Literal[0.75]
    cached_input_usd_per_million: Literal[0.075]
    output_usd_per_million: Literal[4.5]
    cache_write_price_published: Literal[False] = False
    cache_write_reserve_policy: Literal["use-uncached-input-rate"] = "use-uncached-input-rate"
    price_nanos_per_token: dict[
        Literal["uncached_input", "cached_input", "cache_write_input", "output"], int
    ]
    budget_amendment_content_hash: Literal[AMENDMENT_CONTENT_HASH]
    max_cumulative_input_tokens_per_run: Literal[MAX_CUMULATIVE_INPUT_TOKENS]
    max_cumulative_output_tokens_per_run: Literal[MAX_CUMULATIVE_OUTPUT_TOKENS]
    scheduled_runs: Literal[48]
    per_run_reserve_nanos: Literal[PER_RUN_RESERVE_NANOS]
    full_schedule_reserve_nanos: Literal[FULL_SCHEDULE_RESERVE_NANOS]
    hard_cap_nanos: Literal[HARD_CAP_NANOS]
    hard_cap_slack_nanos: Literal[HARD_CAP_SLACK_NANOS]
    rates_match_preregistered_planning_rates: Literal[True]
    supersedes_planning_timestamp: Literal[True]
    candidate_must_bind_this_exact_observation: Literal[True]
    execution_candidate_created: Literal[False] = False
    content_hash: Literal[PRICING_HASH]

    @model_validator(mode="after")
    def validate_pricing(self) -> OfficialPricingBinding:
        if self.official_capture_hash != sha256_json(dict(self.official_capture)):
            raise ValueError("held-out retained official pricing capture hash differs")
        expected_prices = {
            "uncached_input": 750,
            "cached_input": 75,
            "cache_write_input": 750,
            "output": 4_500,
        }
        if self.price_nanos_per_token != expected_prices:
            raise ValueError("held-out token price nanos differ")
        if (
            self.max_cumulative_input_tokens_per_run * expected_prices["uncached_input"]
            + self.max_cumulative_output_tokens_per_run * expected_prices["output"]
            != self.per_run_reserve_nanos
            or self.per_run_reserve_nanos * self.scheduled_runs != self.full_schedule_reserve_nanos
            or self.hard_cap_nanos - self.full_schedule_reserve_nanos != self.hard_cap_slack_nanos
        ):
            raise ValueError("held-out amended pricing reserve arithmetic differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != PRICING_HASH or self.content_hash != expected:
            raise ValueError("held-out amended pricing binding content hash mismatch")
        return self


class MaterializationAuthority(HeldoutACFrozenModel):
    evaluator_side_task_package_access_authorized: Literal[False] = False
    evaluator_side_private_spec_validation_authorized: Literal[False] = False
    reference_patch_hash_validation_authorized: Literal[False] = False
    hidden_artifact_hash_validation_authorized: Literal[False] = False
    task_evaluator_template_materialization_authorized: Literal[False] = False
    predecessor_opaque_task_bindings_reuse_authorized: Literal[True] = True
    retained_r1_pricing_reuse_authorized: Literal[True] = True
    development_budget_amendment_application_authorized: Literal[True] = True
    official_pricing_public_get_authorized: Literal[False] = False
    agent_task_content_access_authorized: Literal[False] = False
    task_selection_or_tuning_authorized: Literal[False] = False
    heldout_outcome_access_authorized: Literal[False] = False
    private_content_serialization_authorized: Literal[False] = False
    credential_or_runtime_secret_observation_authorized: Literal[False] = False
    final_evaluator_contract_materialization_authorized: Literal[False] = False
    docker_sdk_provider_evaluator_or_agent_execution_authorized: Literal[False] = False
    execution_candidate_authorized: Literal[False] = False
    approval_reservation_or_spend_authorized: Literal[False] = False
    official_analysis_or_memory_claim_authorized: Literal[False] = False
    predecessor_distinct_task_packages_materialized: Literal[12] = 12
    added_distinct_task_packages_materialized: Literal[0] = 0
    retained_task_evaluator_templates: Literal[12] = 12
    added_task_evaluator_templates_materialized: Literal[0] = 0
    final_evaluator_contracts_materialized: Literal[0] = 0
    predecessor_official_pricing_public_get_requests: Literal[1] = 1
    added_official_pricing_public_get_requests: Literal[0] = 0
    heldout_outcomes_opened: Literal[0] = 0
    credential_values_observed: Literal[0] = 0
    provider_calls_made: Literal[0] = 0
    evaluator_calls_made: Literal[0] = 0
    agent_runs_made: Literal[0] = 0
    docker_calls_made: Literal[0] = 0
    sdk_calls_made: Literal[0] = 0
    added_model_cost_usd: Literal[0.0] = 0.0


class HeldoutACTaskPricingMaterialization(HeldoutACFrozenModel):
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    materialization_id: Literal[MATERIALIZATION_ID] = MATERIALIZATION_ID
    status: Literal[STATUS] = STATUS
    recorded_at: datetime
    binding_source_predecessor: R9BindingSourcePredecessor
    materialization_predecessor: R4MaterializationPredecessor
    budget_amendment: HeldoutACBudgetAmendmentBinding
    suite_content_hash: Literal[
        "sha256:1d023e8837e99889d76acf6f3a2d970261cb7aa4b3e978c84cef2ef5cf517aaa"
    ]
    task_evaluator_plan_content_hash: Literal[PLAN_HASH]
    source_files: tuple[FileBinding, ...] = Field(
        min_length=len(SOURCE_PATHS), max_length=len(SOURCE_PATHS)
    )
    source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_files: tuple[FileBinding, ...] = Field(
        min_length=len(VALIDATION_PATHS), max_length=len(VALIDATION_PATHS)
    )
    validation_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_bindings: tuple[TaskEvaluatorTemplateBinding, ...] = Field(min_length=12, max_length=12)
    task_bindings_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    pricing: OfficialPricingBinding
    authority: MaterializationAuthority
    next_gate: Literal[NEXT_GATE] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_record(self) -> HeldoutACTaskPricingMaterialization:
        if tuple(item.path for item in self.source_files) != tuple(
            item.as_posix() for item in SOURCE_PATHS
        ):
            raise ValueError("held-out materialization source inventory differs")
        if tuple(item.path for item in self.validation_files) != tuple(
            item.as_posix() for item in VALIDATION_PATHS
        ):
            raise ValueError("held-out materialization validation inventory differs")
        source_projection = [item.model_dump(mode="json") for item in self.source_files]
        validation_projection = [item.model_dump(mode="json") for item in self.validation_files]
        task_projection = [item.model_dump(mode="json") for item in self.task_bindings]
        if (
            self.source_hash != sha256_json(source_projection)
            or self.validation_hash != sha256_json(validation_projection)
            or self.task_bindings_hash != sha256_json(task_projection)
        ):
            raise ValueError("held-out materialization projection hash differs")
        identities = [(item.task.task_id, item.task.task_version) for item in self.task_bindings]
        if len(identities) != 12 or len(identities) != len(set(identities)):
            raise ValueError("held-out materialization task set differs")
        if sum(item.task.role == "core-same-repo" for item in self.task_bindings) != 6:
            raise ValueError("held-out materialization same-repo task count differs")
        if sum(item.task.role == "core-cross-repo" for item in self.task_bindings) != 6:
            raise ValueError("held-out materialization cross-repo task count differs")
        if self.pricing.budget_amendment_content_hash != self.budget_amendment.content_hash:
            raise ValueError("held-out materialization budget amendment binding differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out task/pricing materialization content hash mismatch")
        return self


def _root(repository: str | Path | None) -> Path:
    return Path(repository).resolve() if repository is not None else repository_root().resolve()


def _file_binding(root: Path, relative: Path) -> FileBinding:
    safe = Path(safe_relative_path(relative.as_posix()))
    selected = (root / safe).resolve()
    if not selected.is_relative_to(root) or selected.is_symlink() or not selected.is_file():
        raise HeldoutACTaskPricingMaterializationError(
            f"held-out materialization file is unavailable: {relative.as_posix()}"
        )
    raw = selected.read_bytes()
    return FileBinding(
        path=relative.as_posix(),
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
    )


def _r9_binding_source_predecessor(root: Path) -> R9BindingSourcePredecessor:
    selected = root / R9_PATH
    try:
        raw = selected.read_bytes()
        payload = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise HeldoutACTaskPricingMaterializationError(
            "held-out R9 binding-source predecessor is invalid"
        ) from exc
    if (
        len(raw) != R9_FILE_BYTES
        or sha256_bytes(raw) != R9_FILE_SHA256
        or not isinstance(payload, dict)
        or payload.get("content_hash") != R9_CONTENT_HASH
        or payload.get("source_hash") != R9_SOURCE_HASH
        or payload.get("contract_source_qualification_hash") != R9_CONTRACT_SOURCE_HASH
        or (payload.get("projection") or {}).get("task_evaluator_plan_content_hash") != PLAN_HASH
    ):
        raise HeldoutACTaskPricingMaterializationError(
            "held-out R9 binding-source predecessor drifted"
        )
    return R9BindingSourcePredecessor(
        path=R9_PATH.as_posix(),
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        source_qualification_hash=payload["content_hash"],
        source_hash=payload["source_hash"],
        contract_source_qualification_hash=payload["contract_source_qualification_hash"],
        task_evaluator_plan_content_hash=payload["projection"]["task_evaluator_plan_content_hash"],
        original_status=payload["status"],
    )


def _r4_materialization_predecessor(
    root: Path,
) -> tuple[
    R4MaterializationPredecessor,
    tuple[TaskEvaluatorTemplateBinding, ...],
    LegacyOfficialPricingBinding,
]:
    selected = root / R4_PATH
    try:
        raw = selected.read_bytes()
        payload = json.loads(raw)
        pricing = LegacyOfficialPricingBinding.model_validate_json(
            json.dumps(payload["pricing"], sort_keys=True)
        )
        task_bindings = tuple(
            TaskEvaluatorTemplateBinding.model_validate(item) for item in payload["task_bindings"]
        )
    except (KeyError, OSError, TypeError, UnicodeDecodeError, ValueError) as exc:
        raise HeldoutACTaskPricingMaterializationError(
            "held-out R4 materialization predecessor is invalid"
        ) from exc
    if (
        len(raw) != R4_FILE_BYTES
        or sha256_bytes(raw) != R4_FILE_SHA256
        or not isinstance(payload, dict)
        or payload.get("content_hash") != R4_CONTENT_HASH
        or payload.get("source_hash") != R4_SOURCE_HASH
        or payload.get("task_bindings_hash") != R4_TASK_BINDINGS_HASH
        or sha256_json([item.model_dump(mode="json") for item in task_bindings])
        != R4_TASK_BINDINGS_HASH
        or pricing.content_hash != LEGACY_PRICING_HASH
        or (payload.get("authority") or {}).get("predecessor_official_pricing_public_get_requests")
        != 1
        or (payload.get("authority") or {}).get("added_official_pricing_public_get_requests") != 0
    ):
        raise HeldoutACTaskPricingMaterializationError(
            "held-out R4 materialization predecessor drifted"
        )
    predecessor = R4MaterializationPredecessor(
        path=R4_PATH.as_posix(),
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        content_hash=payload["content_hash"],
        source_hash=payload["source_hash"],
        task_bindings_hash=payload["task_bindings_hash"],
        pricing_binding_hash=pricing.content_hash,
        original_status=payload["status"],
        disposition="invalidated-by-development-budget-amendment-successor",
        invalidation_reason="post-r4-development-evidence-budget-amendment",
        current_source_replay_valid=False,
        retained_task_bindings_reused=True,
        retained_pricing_capture_reused=True,
    )
    return predecessor, task_bindings, pricing


def _amended_pricing(
    legacy: LegacyOfficialPricingBinding,
) -> OfficialPricingBinding:
    body = {
        "schema_version": "heldout-ac-official-pricing-binding-v2",
        "model_id": legacy.model_id,
        "official_model_page_url": legacy.official_model_page_url,
        "observed_at": legacy.observed_at,
        "official_capture": dict(legacy.official_capture),
        "official_capture_hash": legacy.official_capture_hash,
        "input_usd_per_million": legacy.input_usd_per_million,
        "cached_input_usd_per_million": legacy.cached_input_usd_per_million,
        "output_usd_per_million": legacy.output_usd_per_million,
        "cache_write_price_published": legacy.cache_write_price_published,
        "cache_write_reserve_policy": legacy.cache_write_reserve_policy,
        "price_nanos_per_token": dict(legacy.price_nanos_per_token),
        "budget_amendment_content_hash": AMENDMENT_CONTENT_HASH,
        "max_cumulative_input_tokens_per_run": MAX_CUMULATIVE_INPUT_TOKENS,
        "max_cumulative_output_tokens_per_run": MAX_CUMULATIVE_OUTPUT_TOKENS,
        "scheduled_runs": 48,
        "per_run_reserve_nanos": PER_RUN_RESERVE_NANOS,
        "full_schedule_reserve_nanos": FULL_SCHEDULE_RESERVE_NANOS,
        "hard_cap_nanos": HARD_CAP_NANOS,
        "hard_cap_slack_nanos": HARD_CAP_SLACK_NANOS,
        "rates_match_preregistered_planning_rates": True,
        "supersedes_planning_timestamp": True,
        "candidate_must_bind_this_exact_observation": True,
        "execution_candidate_created": False,
    }
    hash_body = dict(body)
    hash_body["observed_at"] = legacy.observed_at.isoformat().replace("+00:00", "Z")
    return OfficialPricingBinding(**body, content_hash=sha256_json(hash_body))


def _contract_template_hash(contract: Any) -> str:
    payload = contract.model_dump(mode="json", exclude={"content_hash"})
    for requirement in payload["requirements"]:
        if requirement["control"] == "secret":
            requirement["policy_input_hash"] = "run-bound-private-marker-set"
            requirement["policy_input_count"] = "run-bound-private-marker-count"
    return sha256_json(payload)


def _task_file_projection(root: Path, package: TaskPackage) -> TaskPackageFileProjection:
    task_root = Path(package.root).resolve()
    if not task_root.is_relative_to(root) or task_root.is_symlink():
        raise HeldoutACTaskPricingMaterializationError("held-out task package root is invalid")

    def read_named(name: str) -> bytes:
        selected = ensure_within(task_root, name)
        if selected.is_symlink() or not selected.is_file():
            raise HeldoutACTaskPricingMaterializationError(
                "held-out task package file is unavailable"
            )
        return selected.read_bytes()

    public_raw = read_named("public.yaml")
    private_raw = read_named("private.yaml")
    environment_raw = read_named("environment.yaml")
    reference_raw = read_named(package.private.reference_patch.path)
    hidden_projection: list[dict[str, object]] = []
    for artifact in package.private.hidden_artifacts:
        raw = read_named(artifact.path)
        hidden_projection.append(
            {
                "path_hash": sha256_text(artifact.path),
                "file_bytes": len(raw),
                "file_sha256": sha256_bytes(raw),
            }
        )
    hidden_projection.sort(key=lambda item: str(item["path_hash"]))
    body = {
        "public_yaml_bytes": len(public_raw),
        "public_yaml_sha256": sha256_bytes(public_raw),
        "private_yaml_bytes": len(private_raw),
        "private_yaml_sha256": sha256_bytes(private_raw),
        "environment_yaml_bytes": len(environment_raw),
        "environment_yaml_sha256": sha256_bytes(environment_raw),
        "reference_patch_bytes": len(reference_raw),
        # The raw reference-patch SHA is itself a private marker.  Commit to it
        # once more so the materialization can replay the file without
        # serializing a marker value.
        "reference_patch_content_commitment": sha256_text(sha256_bytes(reference_raw)),
        "hidden_artifact_count": len(hidden_projection),
        "hidden_artifact_total_bytes": sum(int(item["file_bytes"]) for item in hidden_projection),
        "hidden_artifact_inventory_hash": sha256_json(hidden_projection),
    }
    return TaskPackageFileProjection(**body, content_hash=sha256_json(body))


def _materialize_task_template(
    *,
    root: Path,
    plan: HeldoutACTaskEvaluatorBindingPlan,
    expected: HeldoutACTaskMetadataBinding,
) -> TaskEvaluatorTemplateBinding:
    if plan.content_hash != PLAN_HASH or expected not in plan.tasks:
        raise HeldoutACTaskPricingMaterializationError(
            "held-out task is outside the sealed evaluator plan"
        )
    package = load_task_package(root / expected.task_path)
    package = TaskPackage.model_validate(package.model_dump(mode="json"))
    environment = package.environment
    identity = (
        package.public.task_id,
        package.public.task_version,
        package.public_spec_hash,
        package.private_spec_hash,
    )
    expected_identity = (
        expected.task_id,
        expected.task_version,
        expected.public_spec_hash,
        expected.private_spec_hash,
    )
    if (
        identity != expected_identity
        or environment is None
        or (environment.evaluator_image, environment.image_digest)
        != (expected.evaluator_image, expected.evaluator_image_digest)
    ):
        raise HeldoutACTaskPricingMaterializationError(
            "held-out task package differs from its sealed metadata"
        )
    markers = evaluator_v2_task_private_markers(package)
    contract = build_evaluator_safety_contract_v2(
        package=package,
        tool_schemas=TOOL_SCHEMAS_V2,
        private_markers=markers,
        contract_id=f"heldout_ac_evaluator_v2_{expected.task_id.replace('-', '_')}",
    )
    projection = build_evaluator_contract_binding(
        contract,
        package,
        evaluator_source_hash=TEMPLATE_BINDING_SOURCE_HASH,
    )
    body = {
        "schema_version": "heldout-ac-task-evaluator-template-binding-v4",
        "task": expected.model_dump(mode="json"),
        "package_files": _task_file_projection(root, package).model_dump(mode="json"),
        "base_commit": package.public.repository.base_commit,
        "visible_check_count": len(package.public.visible_checks),
        "hidden_check_count": len(package.private.hidden_checks),
        "task_private_marker_count": len(markers),
        "task_private_marker_set_hash": evaluator_v2_marker_set_hash(markers),
        "baseline_private_contract_hash": contract.content_hash,
        "run_secret_independent_contract_template_hash": _contract_template_hash(contract),
        "hidden_check_ids_hash": projection.hidden_check_ids_hash,
        "regression_check_ids_hash": projection.regression_check_ids_hash,
        "scope_check_ids_hash": projection.scope_check_ids_hash,
        "registered_check_specs_hash": projection.registered_check_specs_hash,
        "binding_projection_source_hash": TEMPLATE_BINDING_SOURCE_HASH,
        "runtime_secret_markers_materialized": 0,
        "final_evaluator_contract_materialized": False,
        "private_values_serialized": False,
    }
    return TaskEvaluatorTemplateBinding(**body, content_hash=sha256_json(body))


def _build_candidate(
    root: Path,
    *,
    recorded_at: datetime,
) -> HeldoutACTaskPricingMaterialization:
    binding_predecessor = _r9_binding_source_predecessor(root)
    materialization_predecessor, task_bindings, legacy_pricing = _r4_materialization_predecessor(
        root
    )
    budget_amendment = heldout_ac_budget_amendment_binding(repository=root)
    pricing = _amended_pricing(legacy_pricing)
    plan = load_heldout_ac_task_evaluator_plan(repository=root)
    if tuple(item.task for item in task_bindings) != plan.tasks:
        raise HeldoutACTaskPricingMaterializationError(
            "held-out retained task bindings differ from the sealed evaluator plan"
        )
    source_files = tuple(_file_binding(root, item) for item in SOURCE_PATHS)
    validation_files = tuple(_file_binding(root, item) for item in VALIDATION_PATHS)
    source_projection = [item.model_dump(mode="json") for item in source_files]
    validation_projection = [item.model_dump(mode="json") for item in validation_files]
    task_projection = [item.model_dump(mode="json") for item in task_bindings]
    body = {
        "schema_version": SCHEMA_VERSION,
        "materialization_id": MATERIALIZATION_ID,
        "status": STATUS,
        "recorded_at": recorded_at.isoformat().replace("+00:00", "Z"),
        "binding_source_predecessor": binding_predecessor.model_dump(mode="json"),
        "materialization_predecessor": materialization_predecessor.model_dump(mode="json"),
        "budget_amendment": budget_amendment.model_dump(mode="json"),
        "suite_content_hash": plan.suite_content_hash,
        "task_evaluator_plan_content_hash": plan.content_hash,
        "source_files": source_projection,
        "source_hash": sha256_json(source_projection),
        "validation_files": validation_projection,
        "validation_hash": sha256_json(validation_projection),
        "task_bindings": task_projection,
        "task_bindings_hash": sha256_json(task_projection),
        "pricing": pricing.model_dump(mode="json"),
        "authority": MaterializationAuthority().model_dump(mode="json"),
        "next_gate": NEXT_GATE,
    }
    return HeldoutACTaskPricingMaterialization(
        schema_version=SCHEMA_VERSION,
        materialization_id=MATERIALIZATION_ID,
        status=STATUS,
        recorded_at=recorded_at,
        binding_source_predecessor=binding_predecessor,
        materialization_predecessor=materialization_predecessor,
        budget_amendment=budget_amendment,
        suite_content_hash=plan.suite_content_hash,
        task_evaluator_plan_content_hash=plan.content_hash,
        source_files=source_files,
        source_hash=body["source_hash"],
        validation_files=validation_files,
        validation_hash=body["validation_hash"],
        task_bindings=task_bindings,
        task_bindings_hash=body["task_bindings_hash"],
        pricing=pricing,
        authority=MaterializationAuthority(),
        next_gate=NEXT_GATE,
        content_hash=sha256_json(body),
    )


def _canonical_bytes(value: HeldoutACTaskPricingMaterialization) -> bytes:
    return (value.model_dump_json(indent=2) + "\n").encode("utf-8")


def _load_validated(
    root: Path,
) -> tuple[HeldoutACTaskPricingMaterialization, bytes]:
    selected = root / OUTPUT_PATH
    try:
        raw = selected.read_bytes()
        payload = HeldoutACTaskPricingMaterialization.model_validate_json(raw)
    except (OSError, ValidationError) as exc:
        raise HeldoutACTaskPricingMaterializationError(
            "held-out task/pricing materialization is invalid"
        ) from exc
    if raw != _canonical_bytes(payload):
        raise HeldoutACTaskPricingMaterializationError(
            "held-out task/pricing materialization bytes are not canonical"
        )
    expected = _build_candidate(
        root,
        recorded_at=payload.recorded_at,
    )
    if payload != expected:
        raise HeldoutACTaskPricingMaterializationError(
            "held-out task/pricing materialization has drifted"
        )
    return payload, raw


def _summary(payload: HeldoutACTaskPricingMaterialization, raw: bytes) -> dict[str, object]:
    return {
        "status": payload.status,
        "materialization_id": payload.materialization_id,
        "materialization_hash": payload.content_hash,
        "task_bindings_hash": payload.task_bindings_hash,
        "retained_task_evaluator_templates": len(payload.task_bindings),
        "added_task_evaluator_templates_materialized": 0,
        "runtime_secret_markers_materialized": 0,
        "final_evaluator_contracts_materialized": 0,
        "pricing_observed_at": payload.pricing.observed_at.isoformat().replace("+00:00", "Z"),
        "predecessor_pricing_public_get_requests": (
            payload.authority.predecessor_official_pricing_public_get_requests
        ),
        "added_pricing_public_get_requests": (
            payload.authority.added_official_pricing_public_get_requests
        ),
        "full_schedule_reserve_usd": payload.pricing.full_schedule_reserve_nanos / 1e9,
        "hard_cap_usd": payload.pricing.hard_cap_nanos / 1e9,
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "execution_candidate_created": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "agent_runs_made": 0,
        "docker_calls_made": 0,
        "sdk_calls_made": 0,
        "added_model_cost_usd": 0.0,
    }


def validate_heldout_ac_task_pricing_materialization(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    root = _root(repository)
    payload, raw = _load_validated(root)
    return _summary(payload, raw)


def run_heldout_ac_task_pricing_materialization(
    *, repository: str | Path | None = None
) -> dict[str, object]:
    root = _root(repository)
    output = root / OUTPUT_PATH
    if output.exists():
        return validate_heldout_ac_task_pricing_materialization(repository=root)
    payload = _build_candidate(
        root,
        recorded_at=datetime.now(UTC),
    )
    content = _canonical_bytes(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise HeldoutACTaskPricingMaterializationError(
            "held-out task/pricing materialization already exists"
        ) from None
    validated, observed = _load_validated(root)
    if validated != payload or observed != content:
        raise HeldoutACTaskPricingMaterializationError(
            "held-out task/pricing materialization reread differs"
        )
    return _summary(validated, observed)


__all__ = [
    "MATERIALIZATION_ID",
    "NEXT_GATE",
    "OUTPUT_PATH",
    "PLAN_HASH",
    "PRICING_HASH",
    "R4_CONTENT_HASH",
    "R4_FILE_BYTES",
    "R4_FILE_SHA256",
    "R4_PATH",
    "R4_SOURCE_HASH",
    "R4_TASK_BINDINGS_HASH",
    "R9_CONTENT_HASH",
    "R9_FILE_BYTES",
    "R9_FILE_SHA256",
    "R9_PATH",
    "R9_SOURCE_HASH",
    "SCHEMA_VERSION",
    "SOURCE_PATHS",
    "STATUS",
    "VALIDATION_PATHS",
    "HeldoutACTaskPricingMaterialization",
    "HeldoutACTaskPricingMaterializationError",
    "OfficialPricingBinding",
    "TaskEvaluatorTemplateBinding",
    "run_heldout_ac_task_pricing_materialization",
    "validate_heldout_ac_task_pricing_materialization",
]
