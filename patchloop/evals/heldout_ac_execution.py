"""No-call activation contract for the preregistered held-out A/C panel.

This module deliberately stops before campaign state or provider dispatch.  It
binds the sealed 48-row suite, the evaluator-side R6 materialization, a fresh
source qualification and read-only local readiness into one execution hash.
It also owns the only supported expansion from an explicitly supplied runtime
secret to a task-bound evaluator-v2 authority.  Secret bytes are never returned
by the no-call path and are never included in a candidate.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.contracts import (
    Budget,
    DatasetRole,
    ExperimentPurpose,
    ExperimentRunContext,
    FaultSpec,
    MemoryCondition,
    MemoryConfig,
    ModelConfig,
    RunManifest,
    TaskPackage,
)
from patchloop.dataset import load_dataset_manifest
from patchloop.errors import ContractError
from patchloop.evals.evaluator_v2_source_qualification import (
    evaluator_v2_task_private_markers,
)
from patchloop.evals.heldout_ac_budget_amendment import (
    FULL_SCHEDULE_RESERVE_NANOS,
    HARD_CAP_NANOS,
    MAX_CUMULATIVE_INPUT_TOKENS,
    MAX_CUMULATIVE_OUTPUT_TOKENS,
    MAX_TOTAL_TOKENS,
    PER_RUN_RESERVE_NANOS,
    HeldoutACBudgetAmendmentBinding,
    heldout_ac_budget_amendment_binding,
)
from patchloop.evals.heldout_ac_contracts import (
    HELDOUT_AC_SUITE_ID,
    HeldoutACCompletionCampaignAuthority,
    HeldoutACFrozenModel,
    HeldoutACSuite,
)
from patchloop.evals.heldout_ac_suite import load_heldout_ac_suite
from patchloop.evals.heldout_ac_task_evaluator import (
    HeldoutACTaskEvaluatorBinding,
    load_heldout_ac_task_evaluator_plan,
    materialize_heldout_ac_task_evaluator_binding,
)
from patchloop.evals.heldout_ac_task_pricing_materialization import (
    HeldoutACTaskPricingMaterialization,
)
from patchloop.memory.fixed_bundle import D110_INDEX_CONTENT_HASH, D110_INDEX_VERSION
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes, sha256_json
from patchloop.verifier.evidence import evaluator_v2_marker_set_hash
from patchloop.verifier.receipt import EvaluatorV2QualificationAuthority
from patchloop.verifier.runtime_evidence import (
    EvaluatorV2RuntimeAuthority,
    evaluator_v2_manifest_runtime_tuple_hash,
    evaluator_v2_runtime_tuple_hash,
)

SUITE_PATH = Path("experiments/heldout-ac-suite-20260814-v1.yaml")
MATERIALIZATION_PATH = Path(
    "reports/heldout-ac/artifacts/heldout-ac-task-pricing-materialization-r6.json"
)
MATERIALIZATION_FILE_BYTES = 53_250
MATERIALIZATION_FILE_SHA256 = (
    "sha256:1a3568e372c9b3af1e384addfb3b5d8351138625072b3af95ccc6290bed3d975"
)
MATERIALIZATION_CONTENT_HASH = (
    "sha256:61f65a54891ef60c07c1edbadd67040cdf5d31e21e4c6e1d3ac97d7f94e419fb"
)
MATERIALIZATION_SOURCE_HASH = (
    "sha256:7135f82bebfee3b635cd67347fee258be57fa2ef15cce09e3df838897c197131"
)
MATERIALIZATION_TASK_BINDINGS_HASH = (
    "sha256:10505056de7f4bd95a06f9c3a16414ce120442c485413e52d113c2aba4c5157f"
)
MATERIALIZATION_PRICING_HASH = (
    "sha256:83bb15d171564f32d0ca6df24f733a957032e144bbd0dfed49071e1b205a27e9"
)
LEGACY_MATERIALIZATION_PATH = Path(
    "reports/heldout-ac/artifacts/heldout-ac-task-pricing-materialization-r5.json"
)
LEGACY_MATERIALIZATION_FILE_BYTES = 53_234
LEGACY_MATERIALIZATION_FILE_SHA256 = (
    "sha256:34186e94134bffceaa05f893c24f9cdf5e1981e4e13c8b37de541ba49a5d6e17"
)
LEGACY_MATERIALIZATION_CONTENT_HASH = (
    "sha256:a7d6347c13368c60b65933041cfc33748fdb780549fa0ad9d358fcfcf4843f60"
)

_SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"
_GIT_PATTERN = r"^[0-9a-f]{40}$"


class HeldoutACExecutionError(ContractError):
    """The held-out activation contract failed closed."""


class HeldoutACFileBinding(HeldoutACFrozenModel):
    path: str
    file_bytes: int = Field(gt=0)
    file_sha256: str = Field(pattern=_SHA256_PATTERN)
    content_hash: str = Field(pattern=_SHA256_PATTERN)


class HeldoutACSourceQualificationBinding(HeldoutACFrozenModel):
    schema_version: Literal["heldout-ac-execution-source-qualification-binding-v1"]
    qualification_id: str = Field(min_length=1)
    qualification_file: HeldoutACFileBinding
    source_qualification_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_source_hash: str = Field(pattern=_SHA256_PATTERN)
    source_replay_valid: Literal[True]
    provider_evaluator_agent_calls_made: Literal[0]

    @model_validator(mode="after")
    def validate_binding(self) -> HeldoutACSourceQualificationBinding:
        if self.source_qualification_hash != self.qualification_file.content_hash:
            raise ValueError("held-out source qualification content binding differs")
        return self


class HeldoutACGitReadiness(HeldoutACFrozenModel):
    commit: str = Field(pattern=_GIT_PATTERN)
    tree: str = Field(pattern=_GIT_PATTERN)
    execution_clean: Literal[True]
    execution_dirty_paths: tuple[()] = ()


class HeldoutACDockerImageReadiness(HeldoutACFrozenModel):
    evaluator_image: str = Field(min_length=1)
    image_digest: str = Field(pattern=_SHA256_PATTERN)
    available: Literal[True]


class HeldoutACDockerReadiness(HeldoutACFrozenModel):
    cli_available: Literal[True]
    daemon_available: Literal[True]
    images: tuple[HeldoutACDockerImageReadiness, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_images(self) -> HeldoutACDockerReadiness:
        identities = tuple((item.evaluator_image, item.image_digest) for item in self.images)
        if identities != tuple(sorted(identities)) or len(identities) != len(set(identities)):
            raise ValueError("held-out Docker image readiness is not canonical")
        return self


class HeldoutACSDKReadiness(HeldoutACFrozenModel):
    installed: Literal[True]
    version: str = Field(min_length=1)


class HeldoutACCredentialReadiness(HeldoutACFrozenModel):
    name: Literal["OPENAI_API_KEY"]
    present: Literal[True]
    custom_base_url_present: Literal[False]
    value_observed_or_serialized: Literal[False]


class HeldoutACNoCallReadiness(HeldoutACFrozenModel):
    schema_version: Literal["heldout-ac-no-call-readiness-v1"]
    observed_at: datetime
    git: HeldoutACGitReadiness
    docker: HeldoutACDockerReadiness
    openai_sdk: HeldoutACSDKReadiness
    credential: HeldoutACCredentialReadiness
    provider_calls_made: Literal[0]
    evaluator_calls_made: Literal[0]
    agent_runs_made: Literal[0]
    model_cost_usd: Literal[0.0]
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_content_hash(self) -> HeldoutACNoCallReadiness:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out no-call readiness content hash differs")
        return self


class HeldoutACExecutionScheduleRow(HeldoutACFrozenModel):
    order: int = Field(ge=1, le=48)
    wave: int = Field(ge=1, le=4)
    schedule_row_id: str = Field(pattern=_SHA256_PATTERN)
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    task_version: Literal[1]
    task_path: str
    role: Literal["core-same-repo", "core-cross-repo"]
    condition: Literal["no_memory", "structured"]
    repetition: Literal[1, 2]
    public_spec_hash: str = Field(pattern=_SHA256_PATTERN)
    private_spec_hash: str = Field(pattern=_SHA256_PATTERN)
    base_commit: str = Field(pattern=_GIT_PATTERN)
    evaluator_image: str
    evaluator_image_digest: str = Field(pattern=_SHA256_PATTERN)
    evaluator_contract_template_hash: str = Field(pattern=_SHA256_PATTERN)


class HeldoutACCampaignCostControl(HeldoutACFrozenModel):
    schema_version: Literal[
        "heldout-ac-full-schedule-cost-control-v1",
        "heldout-ac-full-schedule-cost-control-v2",
    ]
    suite_id: Literal[HELDOUT_AC_SUITE_ID]
    suite_content_hash: str = Field(pattern=_SHA256_PATTERN)
    execution_hash: str = Field(pattern=_SHA256_PATTERN)
    schedule_hash: str = Field(pattern=_SHA256_PATTERN)
    scheduled_run_count: Literal[48]
    per_run_reserve_nanos: int = Field(gt=0)
    full_schedule_reserve_nanos: int = Field(gt=0)
    hard_cap_nanos: int = Field(gt=0)
    cost_censoring_allowed: Literal[False]
    live_resume_supported: Literal[False]
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_content_hash(self) -> HeldoutACCampaignCostControl:
        expected_costs = (
            (5_250_000_000, 252_000_000_000, 275_000_000_000)
            if self.schema_version == "heldout-ac-full-schedule-cost-control-v1"
            else (PER_RUN_RESERVE_NANOS, FULL_SCHEDULE_RESERVE_NANOS, HARD_CAP_NANOS)
        )
        if (
            self.per_run_reserve_nanos,
            self.full_schedule_reserve_nanos,
            self.hard_cap_nanos,
        ) != expected_costs:
            raise ValueError("held-out campaign cost control values differ")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out campaign cost control hash differs")
        return self


class HeldoutACExecutionCandidate(HeldoutACFrozenModel):
    schema_version: Literal[
        "heldout-ac-execution-candidate-v1",
        "heldout-ac-execution-candidate-v2",
        "heldout-ac-execution-candidate-v3",
    ]
    status: Literal["NO_CALL_CANDIDATE_READY_EXECUTION_NOT_AUTHORIZED"]
    suite_id: Literal[HELDOUT_AC_SUITE_ID]
    suite_content_hash: str = Field(pattern=_SHA256_PATTERN)
    dataset_manifest_hash: str = Field(pattern=_SHA256_PATTERN)
    materialization: HeldoutACFileBinding
    task_bindings_hash: str = Field(pattern=_SHA256_PATTERN)
    pricing_binding_hash: str = Field(pattern=_SHA256_PATTERN)
    budget_amendment: HeldoutACBudgetAmendmentBinding | None = None
    source_qualification: HeldoutACSourceQualificationBinding
    runtime_tuple_hash: str = Field(pattern=_SHA256_PATTERN)
    base_schedule_hash: str = Field(pattern=_SHA256_PATTERN)
    realized_schedule_hash: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    readiness: HeldoutACNoCallReadiness
    execution_hash: str = Field(pattern=_SHA256_PATTERN)
    schedule: tuple[HeldoutACExecutionScheduleRow, ...] = Field(min_length=48, max_length=48)
    schedule_hash: str = Field(pattern=_SHA256_PATTERN)
    campaign_cost_control: HeldoutACCampaignCostControl
    full_schedule_reserve_usd: float = Field(gt=0)
    hard_cap_usd: float = Field(gt=0)
    exact_paid_approval_present: Literal[False]
    provider_execution_authorized: Literal[False]
    evaluator_execution_authorized: Literal[False]
    agent_execution_authorized: Literal[False]
    cost_reservation_or_spend_authorized: Literal[False]

    @model_validator(mode="after")
    def validate_candidate(self) -> HeldoutACExecutionCandidate:
        if self.schema_version == "heldout-ac-execution-candidate-v1":
            if self.budget_amendment is not None or (
                self.full_schedule_reserve_usd,
                self.hard_cap_usd,
                self.campaign_cost_control.schema_version,
            ) != (252.0, 275.0, "heldout-ac-full-schedule-cost-control-v1"):
                raise ValueError("held-out historical candidate budget binding differs")
        elif self.schema_version == "heldout-ac-execution-candidate-v2":
            if (
                self.budget_amendment is None
                or self.task_bindings_hash != MATERIALIZATION_TASK_BINDINGS_HASH
                or self.pricing_binding_hash != MATERIALIZATION_PRICING_HASH
                or self.materialization.path != LEGACY_MATERIALIZATION_PATH.as_posix()
                or self.materialization.file_bytes != LEGACY_MATERIALIZATION_FILE_BYTES
                or self.materialization.file_sha256 != LEGACY_MATERIALIZATION_FILE_SHA256
                or self.materialization.content_hash != LEGACY_MATERIALIZATION_CONTENT_HASH
                or (
                    self.full_schedule_reserve_usd,
                    self.hard_cap_usd,
                    self.campaign_cost_control.schema_version,
                )
                != (57.6, 60.0, "heldout-ac-full-schedule-cost-control-v2")
            ):
                raise ValueError("held-out historical cost-bounded candidate binding differs")
        elif (
            self.budget_amendment is None
            or self.task_bindings_hash != MATERIALIZATION_TASK_BINDINGS_HASH
            or self.pricing_binding_hash != MATERIALIZATION_PRICING_HASH
            or self.materialization.path != MATERIALIZATION_PATH.as_posix()
            or self.materialization.file_bytes != MATERIALIZATION_FILE_BYTES
            or self.materialization.file_sha256 != MATERIALIZATION_FILE_SHA256
            or self.materialization.content_hash != MATERIALIZATION_CONTENT_HASH
            or (
                self.full_schedule_reserve_usd,
                self.hard_cap_usd,
                self.campaign_cost_control.schema_version,
            )
            != (57.6, 60.0, "heldout-ac-full-schedule-cost-control-v2")
        ):
            raise ValueError("held-out current cost-bounded candidate binding differs")
        if len(self.schedule) != 48 or tuple(row.order for row in self.schedule) != tuple(
            range(1, 49)
        ):
            raise ValueError("held-out candidate schedule is not exactly 48 ordered rows")
        if self.schema_version == "heldout-ac-execution-candidate-v3":
            if self.base_schedule_hash != sha256_json(_base_schedule_projection(self.schedule)):
                raise ValueError("held-out candidate base schedule hash differs")
            expected_realized_schedule_hash = sha256_json(
                _realized_schedule_projection(self.schedule)
            )
            if self.realized_schedule_hash != expected_realized_schedule_hash:
                raise ValueError("held-out candidate realized schedule hash differs")
        elif self.realized_schedule_hash is not None:
            raise ValueError("held-out historical candidate has a realized schedule hash")
        expected_hash = sha256_json(_execution_projection(self))
        if self.execution_hash != expected_hash:
            raise ValueError("held-out candidate execution hash differs")
        for row in self.schedule:
            expected_row_id = _schedule_row_id(
                suite_id=self.suite_id,
                suite_content_hash=self.suite_content_hash,
                execution_hash=self.execution_hash,
                row=row,
            )
            if row.schedule_row_id != expected_row_id:
                raise ValueError("held-out candidate schedule row identity differs")
        if self.schedule_hash != sha256_json(_runtime_schedule_projection(self.schedule)):
            raise ValueError("held-out candidate schedule hash differs")
        if (
            self.campaign_cost_control.execution_hash != self.execution_hash
            or self.campaign_cost_control.schedule_hash != self.schedule_hash
            or self.campaign_cost_control.suite_content_hash != self.suite_content_hash
        ):
            raise ValueError("held-out candidate cost control belongs to another execution")
        return self


@dataclass(frozen=True)
class HeldoutACRuntimeTaskAuthority:
    """Ephemeral final binding.  It deliberately contains private marker bytes."""

    task_binding: HeldoutACTaskEvaluatorBinding
    qualification_authority: EvaluatorV2QualificationAuthority


def _root(repository: str | Path | None) -> Path:
    return Path(repository).resolve() if repository is not None else repository_root().resolve()


def _read_materialization(root: Path) -> tuple[HeldoutACTaskPricingMaterialization, bytes]:
    selected = root / MATERIALIZATION_PATH
    try:
        raw = selected.read_bytes()
        payload = HeldoutACTaskPricingMaterialization.model_validate_json(raw)
    except (OSError, ValidationError) as exc:
        raise HeldoutACExecutionError("held-out R6 materialization is invalid") from exc
    if (
        len(raw) != MATERIALIZATION_FILE_BYTES
        or sha256_bytes(raw) != MATERIALIZATION_FILE_SHA256
        or payload.content_hash != MATERIALIZATION_CONTENT_HASH
        or payload.source_hash != MATERIALIZATION_SOURCE_HASH
        or payload.task_bindings_hash != MATERIALIZATION_TASK_BINDINGS_HASH
        or payload.pricing.content_hash != MATERIALIZATION_PRICING_HASH
        or raw != (payload.model_dump_json(indent=2) + "\n").encode("utf-8")
    ):
        raise HeldoutACExecutionError("held-out R6 materialization bytes drifted")
    return payload, raw


def _runtime_tuple_hash(suite: HeldoutACSuite) -> str:
    runtime = suite.runtime
    return evaluator_v2_runtime_tuple_hash(
        provider=runtime.model,
        model_id=runtime.model_id,
        reasoning_effort=runtime.reasoning_effort,
        reasoning_mode=runtime.reasoning_mode,
        service_tier=runtime.service_tier,
        transport_max_retries=runtime.transport_max_retries,
        max_output_tokens=runtime.max_output_tokens,
        max_total_tokens=MAX_TOTAL_TOKENS,
        wall_clock_timeout_seconds=runtime.wall_clock_timeout_seconds,
        tool_schema_version=runtime.tool_schema_version,
        context_policy_version=runtime.context_policy_version,
        memory_policy_version=runtime.memory_policy_version,
        sandbox_backend=runtime.sandbox_backend,
        token_budget_schema_version=runtime.token_budget_schema_version,
        max_model_calls=runtime.max_model_calls,
        max_tool_calls=runtime.max_tool_calls,
        max_cumulative_input_tokens=MAX_CUMULATIVE_INPUT_TOKENS,
        max_cumulative_output_tokens=MAX_CUMULATIVE_OUTPUT_TOKENS,
    )


def _base_schedule_hash(suite: HeldoutACSuite) -> str:
    return sha256_json([item.model_dump(mode="json") for item in suite.schedule])


def _base_schedule_projection(
    rows: Sequence[HeldoutACExecutionScheduleRow],
) -> list[dict[str, Any]]:
    return [
        {
            "order": row.order,
            "wave": row.wave,
            "task_id": row.task_id,
            "role": row.role,
            "condition": row.condition,
            "repetition": row.repetition,
        }
        for row in rows
    ]


def _execution_projection(candidate: HeldoutACExecutionCandidate) -> dict[str, Any]:
    execution_schema_versions = {
        "heldout-ac-execution-candidate-v1": "heldout-ac-execution-v1",
        "heldout-ac-execution-candidate-v2": "heldout-ac-execution-v2",
        "heldout-ac-execution-candidate-v3": "heldout-ac-execution-v3",
    }
    projection = {
        "schema_version": execution_schema_versions[candidate.schema_version],
        "suite_id": candidate.suite_id,
        "suite_content_hash": candidate.suite_content_hash,
        "dataset_manifest_hash": candidate.dataset_manifest_hash,
        "materialization": candidate.materialization.model_dump(mode="json"),
        "task_bindings_hash": candidate.task_bindings_hash,
        "pricing_binding_hash": candidate.pricing_binding_hash,
        "source_qualification": candidate.source_qualification.model_dump(mode="json"),
        "runtime_tuple_hash": candidate.runtime_tuple_hash,
        "base_schedule_hash": candidate.base_schedule_hash,
        "readiness": candidate.readiness.model_dump(mode="json"),
    }
    if candidate.schema_version in {
        "heldout-ac-execution-candidate-v2",
        "heldout-ac-execution-candidate-v3",
    }:
        if candidate.budget_amendment is None:  # pragma: no cover - model invariant
            raise ValueError("held-out cost-bounded candidate amendment is absent")
        projection["budget_amendment"] = candidate.budget_amendment.model_dump(mode="json")
    if candidate.schema_version == "heldout-ac-execution-candidate-v3":
        if candidate.realized_schedule_hash is None:  # pragma: no cover - model invariant
            raise ValueError("held-out realized schedule binding is absent")
        projection["realized_schedule_hash"] = candidate.realized_schedule_hash
    return projection


def heldout_ac_campaign_identity_hash(candidate: HeldoutACExecutionCandidate) -> str:
    """Return the one-use paid-campaign identity, excluding transient readiness.

    ``observed_at`` and other readiness observations intentionally affect the
    execution hash, but they must not create another paid opportunity for the
    same qualified source, suite, runtime and base schedule.
    """

    checked = HeldoutACExecutionCandidate.model_validate(
        candidate.model_dump(mode="python", exclude_none=True)
    )
    paid_identity_schema_versions = {
        "heldout-ac-execution-candidate-v1": "heldout-ac-paid-campaign-identity-v1",
        "heldout-ac-execution-candidate-v2": "heldout-ac-paid-campaign-identity-v2",
        "heldout-ac-execution-candidate-v3": "heldout-ac-paid-campaign-identity-v3",
    }
    body = {
        "schema_version": paid_identity_schema_versions[checked.schema_version],
        "suite_id": checked.suite_id,
        "suite_content_hash": checked.suite_content_hash,
        "dataset_manifest_hash": checked.dataset_manifest_hash,
        "materialization_content_hash": checked.materialization.content_hash,
        "task_bindings_hash": checked.task_bindings_hash,
        "pricing_binding_hash": checked.pricing_binding_hash,
        "source_qualification_hash": (checked.source_qualification.source_qualification_hash),
        "evaluator_source_hash": checked.source_qualification.evaluator_source_hash,
        "runtime_tuple_hash": checked.runtime_tuple_hash,
        "base_schedule_hash": checked.base_schedule_hash,
        "scheduled_run_count": 48,
        "full_schedule_reserve_nanos": (checked.campaign_cost_control.full_schedule_reserve_nanos),
        "hard_cap_nanos": checked.campaign_cost_control.hard_cap_nanos,
    }
    if checked.budget_amendment is not None:
        body["budget_amendment_content_hash"] = checked.budget_amendment.content_hash
    if checked.realized_schedule_hash is not None:
        body["realized_schedule_hash"] = checked.realized_schedule_hash
    return sha256_json(body)


def heldout_ac_candidate_token_limits(
    candidate: HeldoutACExecutionCandidate,
) -> tuple[int, int, int]:
    """Return the schema-bound input, output, and aggregate token ceilings."""

    checked = HeldoutACExecutionCandidate.model_validate(
        candidate.model_dump(mode="python", exclude_none=True)
    )
    if checked.schema_version == "heldout-ac-execution-candidate-v1":
        return 4_000_000, 500_000, 4_500_000
    return (
        MAX_CUMULATIVE_INPUT_TOKENS,
        MAX_CUMULATIVE_OUTPUT_TOKENS,
        MAX_TOTAL_TOKENS,
    )


def heldout_ac_completion_campaign_authority(
    *,
    candidate: HeldoutACExecutionCandidate,
    suite: HeldoutACSuite,
) -> HeldoutACCompletionCampaignAuthority:
    """Project one validated candidate into the execution-free completion boundary."""

    checked = HeldoutACExecutionCandidate.model_validate(candidate.model_dump(mode="python"))
    if checked.suite_id != suite.suite_id or checked.suite_content_hash != suite.content_hash:
        raise HeldoutACExecutionError("held-out completion authority candidate differs from suite")
    if checked.base_schedule_hash != _base_schedule_hash(suite):
        raise HeldoutACExecutionError("held-out completion authority base schedule differs")
    expected_schedule = tuple(
        (row.order, row.wave, row.task_id, row.role, row.condition, row.repetition)
        for row in suite.schedule
    )
    observed_schedule = tuple(
        (row.order, row.wave, row.task_id, row.role, row.condition, row.repetition)
        for row in checked.schedule
    )
    if observed_schedule != expected_schedule:
        raise HeldoutACExecutionError("held-out completion authority schedule differs")
    max_input, max_output, max_total = heldout_ac_candidate_token_limits(checked)
    body = {
        "schema_version": "heldout-ac-completion-campaign-authority-v1",
        "candidate_schema_version": checked.schema_version,
        "suite_id": checked.suite_id,
        "suite_content_hash": checked.suite_content_hash,
        "execution_hash": checked.execution_hash,
        "schedule_hash": checked.schedule_hash,
        "schedule_row_ids": tuple(row.schedule_row_id for row in checked.schedule),
        "runtime_tuple_hash": checked.runtime_tuple_hash,
        "pricing_binding_hash": checked.pricing_binding_hash,
        "evaluator_source_hash": checked.source_qualification.evaluator_source_hash,
        "evaluator_source_qualification_hash": (
            checked.source_qualification.source_qualification_hash
        ),
        "max_cumulative_input_tokens": max_input,
        "max_cumulative_output_tokens": max_output,
        "max_total_tokens": max_total,
        "max_model_calls": suite.runtime.max_model_calls,
        "max_tool_calls": suite.runtime.max_tool_calls,
        "wall_clock_timeout_seconds": suite.runtime.wall_clock_timeout_seconds,
        "campaign_cost_control_hash": checked.campaign_cost_control.content_hash,
        "per_run_reserve_nanos": checked.campaign_cost_control.per_run_reserve_nanos,
        "full_schedule_reserve_nanos": (checked.campaign_cost_control.full_schedule_reserve_nanos),
        "hard_cap_nanos": checked.campaign_cost_control.hard_cap_nanos,
    }
    if checked.realized_schedule_hash is not None:
        body["realized_schedule_hash"] = checked.realized_schedule_hash
    return HeldoutACCompletionCampaignAuthority(**body, content_hash=sha256_json(body))


def _schedule_row_id(
    *,
    suite_id: str,
    suite_content_hash: str,
    execution_hash: str,
    row: HeldoutACExecutionScheduleRow,
) -> str:
    return sha256_json(
        {
            "schema_version": "heldout-ac-schedule-row-v1",
            "suite_id": suite_id,
            "suite_content_hash": suite_content_hash,
            "execution_hash": execution_hash,
            "order": row.order,
            "wave": row.wave,
            "task_id": row.task_id,
            "role": row.role,
            "condition": row.condition,
            "repetition": row.repetition,
        }
    )


def _runtime_schedule_projection(
    rows: Sequence[HeldoutACExecutionScheduleRow],
) -> list[dict[str, Any]]:
    return [
        {
            "order": row.order,
            "wave": row.wave,
            "schedule_row_id": row.schedule_row_id,
            "task_id": row.task_id,
            "role": row.role,
            "condition": row.condition,
            "repetition": row.repetition,
        }
        for row in rows
    ]


def _realized_schedule_projection(
    rows: Sequence[HeldoutACExecutionScheduleRow] | Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Project every pre-dispatch row field without the execution-derived row ID."""

    field_names = (
        "order",
        "wave",
        "task_id",
        "task_version",
        "task_path",
        "role",
        "condition",
        "repetition",
        "public_spec_hash",
        "private_spec_hash",
        "base_commit",
        "evaluator_image",
        "evaluator_image_digest",
        "evaluator_contract_template_hash",
    )
    return [
        {
            field_name: (row[field_name] if isinstance(row, dict) else getattr(row, field_name))
            for field_name in field_names
        }
        for row in rows
    ]


def _realized_schedule_bodies_from_execution_inputs(
    *,
    suite: HeldoutACSuite,
    materialization: HeldoutACTaskPricingMaterialization,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    templates = {item.task.task_id: item for item in materialization.task_bindings}
    if set(templates) != set(metadata):
        raise HeldoutACExecutionError("held-out task template set differs from metadata plan")
    rows: list[dict[str, Any]] = []
    for row in suite.schedule:
        task = metadata.get(row.task_id)
        template = templates.get(row.task_id)
        if task is None or template is None:
            raise HeldoutACExecutionError("held-out realized schedule task is absent")
        rows.append(
            {
                "order": row.order,
                "wave": row.wave,
                "schedule_row_id": "sha256:" + "0" * 64,
                "task_id": row.task_id,
                "task_version": task.task_version,
                "task_path": task.task_path,
                "role": row.role,
                "condition": row.condition,
                "repetition": row.repetition,
                "public_spec_hash": task.public_spec_hash,
                "private_spec_hash": task.private_spec_hash,
                "base_commit": template.base_commit,
                "evaluator_image": task.evaluator_image,
                "evaluator_image_digest": task.evaluator_image_digest,
                "evaluator_contract_template_hash": (
                    template.run_secret_independent_contract_template_hash
                ),
            }
        )
    return rows


def heldout_ac_candidate_matches_current_execution_inputs(
    candidate: HeldoutACExecutionCandidate,
    *,
    repository: str | Path | None = None,
) -> bool:
    """Rebind a current v3 candidate to the sealed suite and public execution inputs."""

    root = _root(repository)
    try:
        checked = HeldoutACExecutionCandidate.model_validate(
            candidate.model_dump(mode="python", exclude_none=True)
        )
        suite = load_heldout_ac_suite(SUITE_PATH, repository=root)
        materialization, _raw = _read_materialization(root)
        plan = load_heldout_ac_task_evaluator_plan(repository=root)
        _manifest, dataset_manifest_hash, _path = load_dataset_manifest(
            root / suite.dataset.manifest_path
        )
        expected_rows = _realized_schedule_bodies_from_execution_inputs(
            suite=suite,
            materialization=materialization,
            metadata={item.task_id: item for item in plan.tasks},
        )
    except (ContractError, OSError, ValidationError, ValueError, TypeError):
        return False
    return bool(
        checked.schema_version == "heldout-ac-execution-candidate-v3"
        and checked.suite_id == suite.suite_id
        and checked.suite_content_hash == suite.content_hash
        and checked.dataset_manifest_hash == dataset_manifest_hash
        and checked.runtime_tuple_hash == _runtime_tuple_hash(suite)
        and checked.base_schedule_hash == _base_schedule_hash(suite)
        and checked.realized_schedule_hash
        == sha256_json(_realized_schedule_projection(expected_rows))
        and _realized_schedule_projection(checked.schedule)
        == _realized_schedule_projection(expected_rows)
    )


def _contract_template_hash(contract: Any) -> str:
    payload = contract.model_dump(mode="json", exclude={"content_hash"})
    for requirement in payload["requirements"]:
        if requirement["control"] == "secret":
            requirement["policy_input_hash"] = "run-bound-private-marker-set"
            requirement["policy_input_count"] = "run-bound-private-marker-count"
    return sha256_json(payload)


def _materialization_binding(payload: HeldoutACTaskPricingMaterialization) -> HeldoutACFileBinding:
    return HeldoutACFileBinding(
        path=MATERIALIZATION_PATH.as_posix(),
        file_bytes=MATERIALIZATION_FILE_BYTES,
        file_sha256=MATERIALIZATION_FILE_SHA256,
        content_hash=payload.content_hash,
    )


def build_heldout_ac_no_call_readiness(
    *,
    observed_at: datetime,
    git_commit: str,
    git_tree: str,
    docker_images: Sequence[tuple[str, str]],
    openai_sdk_version: str,
    credential_present: bool,
    custom_base_url_present: bool,
) -> HeldoutACNoCallReadiness:
    """Build a typed readiness record from already-observed, non-secret facts."""

    if observed_at.tzinfo is None or observed_at.utcoffset() != UTC.utcoffset(observed_at):
        raise HeldoutACExecutionError("held-out readiness timestamp must be UTC")
    if credential_present is not True or custom_base_url_present is not False:
        raise HeldoutACExecutionError("held-out credential presence boundary is not ready")
    images = tuple(
        HeldoutACDockerImageReadiness(
            evaluator_image=image,
            image_digest=digest,
            available=True,
        )
        for image, digest in sorted(docker_images)
    )
    body = {
        "schema_version": "heldout-ac-no-call-readiness-v1",
        "observed_at": observed_at,
        "git": {
            "commit": git_commit,
            "tree": git_tree,
            "execution_clean": True,
            "execution_dirty_paths": (),
        },
        "docker": {
            "cli_available": True,
            "daemon_available": True,
            "images": tuple(item.model_dump(mode="json") for item in images),
        },
        "openai_sdk": {"installed": True, "version": openai_sdk_version},
        "credential": {
            "name": "OPENAI_API_KEY",
            "present": True,
            "custom_base_url_present": False,
            "value_observed_or_serialized": False,
        },
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "agent_runs_made": 0,
        "model_cost_usd": 0.0,
    }
    hash_body = {
        **body,
        "observed_at": observed_at.isoformat().replace("+00:00", "Z"),
    }
    return HeldoutACNoCallReadiness(**body, content_hash=sha256_json(hash_body))


def build_heldout_ac_execution_candidate(
    *,
    readiness: HeldoutACNoCallReadiness,
    source_qualification: HeldoutACSourceQualificationBinding,
    repository: str | Path | None = None,
) -> HeldoutACExecutionCandidate:
    """Bind one clean no-call observation into an execution candidate."""

    root = _root(repository)
    suite = load_heldout_ac_suite(SUITE_PATH, repository=root)
    budget_amendment = heldout_ac_budget_amendment_binding(repository=root)
    materialization, _ = _read_materialization(root)
    _manifest, dataset_manifest_hash, _path = load_dataset_manifest(
        root / suite.dataset.manifest_path
    )
    expected_images = tuple(
        sorted(
            {
                (item.task.evaluator_image, item.task.evaluator_image_digest)
                for item in materialization.task_bindings
            }
        )
    )
    observed_images = tuple(
        (item.evaluator_image, item.image_digest) for item in readiness.docker.images
    )
    if observed_images != expected_images:
        raise HeldoutACExecutionError("held-out readiness does not bind every evaluator image")
    metadata = {
        item.task_id: item for item in load_heldout_ac_task_evaluator_plan(repository=root).tasks
    }
    base_rows = _realized_schedule_bodies_from_execution_inputs(
        suite=suite,
        materialization=materialization,
        metadata=metadata,
    )

    realized_schedule_hash = sha256_json(_realized_schedule_projection(base_rows))
    provisional = HeldoutACExecutionCandidate.model_construct(
        schema_version="heldout-ac-execution-candidate-v3",
        status="NO_CALL_CANDIDATE_READY_EXECUTION_NOT_AUTHORIZED",
        suite_id=suite.suite_id,
        suite_content_hash=suite.content_hash,
        dataset_manifest_hash=dataset_manifest_hash,
        materialization=_materialization_binding(materialization),
        task_bindings_hash=materialization.task_bindings_hash,
        pricing_binding_hash=materialization.pricing.content_hash,
        budget_amendment=budget_amendment,
        source_qualification=source_qualification,
        runtime_tuple_hash=_runtime_tuple_hash(suite),
        base_schedule_hash=_base_schedule_hash(suite),
        realized_schedule_hash=realized_schedule_hash,
        readiness=readiness,
    )
    execution_hash = sha256_json(_execution_projection(provisional))
    schedule = tuple(
        HeldoutACExecutionScheduleRow(
            **{
                **body,
                "schedule_row_id": sha256_json(
                    {
                        "schema_version": "heldout-ac-schedule-row-v1",
                        "suite_id": suite.suite_id,
                        "suite_content_hash": suite.content_hash,
                        "execution_hash": execution_hash,
                        **{
                            key: body[key]
                            for key in (
                                "order",
                                "wave",
                                "task_id",
                                "role",
                                "condition",
                                "repetition",
                            )
                        },
                    }
                ),
            }
        )
        for body in base_rows
    )
    schedule_hash = sha256_json(_runtime_schedule_projection(schedule))
    cost_body = {
        "schema_version": "heldout-ac-full-schedule-cost-control-v2",
        "suite_id": suite.suite_id,
        "suite_content_hash": suite.content_hash,
        "execution_hash": execution_hash,
        "schedule_hash": schedule_hash,
        "scheduled_run_count": 48,
        "per_run_reserve_nanos": PER_RUN_RESERVE_NANOS,
        "full_schedule_reserve_nanos": FULL_SCHEDULE_RESERVE_NANOS,
        "hard_cap_nanos": HARD_CAP_NANOS,
        "cost_censoring_allowed": False,
        "live_resume_supported": False,
    }
    return HeldoutACExecutionCandidate(
        schema_version="heldout-ac-execution-candidate-v3",
        status="NO_CALL_CANDIDATE_READY_EXECUTION_NOT_AUTHORIZED",
        suite_id=suite.suite_id,
        suite_content_hash=suite.content_hash,
        dataset_manifest_hash=dataset_manifest_hash,
        materialization=_materialization_binding(materialization),
        task_bindings_hash=materialization.task_bindings_hash,
        pricing_binding_hash=materialization.pricing.content_hash,
        budget_amendment=budget_amendment,
        source_qualification=source_qualification,
        runtime_tuple_hash=_runtime_tuple_hash(suite),
        base_schedule_hash=_base_schedule_hash(suite),
        realized_schedule_hash=realized_schedule_hash,
        readiness=readiness,
        execution_hash=execution_hash,
        schedule=schedule,
        schedule_hash=schedule_hash,
        campaign_cost_control=HeldoutACCampaignCostControl(
            **cost_body, content_hash=sha256_json(cost_body)
        ),
        full_schedule_reserve_usd=57.6,
        hard_cap_usd=60.0,
        exact_paid_approval_present=False,
        provider_execution_authorized=False,
        evaluator_execution_authorized=False,
        agent_execution_authorized=False,
        cost_reservation_or_spend_authorized=False,
    )


def encode_heldout_ac_runtime_secret(api_key: str) -> bytes:
    """Encode exactly one live credential marker without logging or normalizing it."""

    if type(api_key) is not str or not api_key:
        raise HeldoutACExecutionError("held-out runtime secret must be a non-empty string")
    try:
        encoded = api_key.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise HeldoutACExecutionError("held-out runtime secret is not valid UTF-8") from exc
    if len(encoded) > 16_384:
        raise HeldoutACExecutionError("held-out runtime secret exceeds the marker limit")
    return encoded


def materialize_heldout_ac_runtime_task_authority(
    *,
    candidate: HeldoutACExecutionCandidate,
    task_id: str,
    package: TaskPackage,
    api_key: str,
    repository: str | Path | None = None,
) -> HeldoutACRuntimeTaskAuthority:
    """Expand one R4 template into an ephemeral final evaluator-v2 authority."""

    root = _root(repository)
    if not heldout_ac_candidate_matches_current_execution_inputs(candidate, repository=root):
        raise HeldoutACExecutionError("held-out candidate realized schedule differs from inputs")
    suite = load_heldout_ac_suite(SUITE_PATH, repository=root)
    materialization, _ = _read_materialization(root)
    plan = load_heldout_ac_task_evaluator_plan(repository=root)
    if candidate.suite_content_hash != suite.content_hash:
        raise HeldoutACExecutionError("held-out candidate uses another suite")
    expected_task = next((item for item in plan.tasks if item.task_id == task_id), None)
    template = next(
        (item for item in materialization.task_bindings if item.task.task_id == task_id), None
    )
    if expected_task is None or template is None:
        raise HeldoutACExecutionError("held-out runtime task is outside the sealed panel")
    secret = encode_heldout_ac_runtime_secret(api_key)
    binding = materialize_heldout_ac_task_evaluator_binding(
        plan=plan,
        expected_task=expected_task,
        package=package,
        evaluator_source_hash=candidate.source_qualification.evaluator_source_hash,
        runtime_secret_markers=(secret,),
    )
    markers = tuple(sorted((*evaluator_v2_task_private_markers(package), secret)))
    if (
        _contract_template_hash(binding.safety_contract)
        != template.run_secret_independent_contract_template_hash
        or binding.private_marker_count != len(markers)
        or binding.private_marker_set_hash != evaluator_v2_marker_set_hash(markers)
    ):
        raise HeldoutACExecutionError("held-out runtime contract differs from its R4 template")
    authority = EvaluatorV2QualificationAuthority(
        runtime=EvaluatorV2RuntimeAuthority(
            safety_contract=binding.safety_contract,
            evaluator_source_hash=candidate.source_qualification.evaluator_source_hash,
            tool_schemas=tuple(TOOL_SCHEMAS_V2),
            private_markers=markers,
        ),
        suite_hash=candidate.suite_content_hash,
        source_qualification_hash=(candidate.source_qualification.source_qualification_hash),
        runtime_tuple_hash=candidate.runtime_tuple_hash,
    )
    return HeldoutACRuntimeTaskAuthority(
        task_binding=binding,
        qualification_authority=authority,
    )


def build_heldout_ac_run_manifest(
    *,
    candidate: HeldoutACExecutionCandidate,
    row_order: int,
    run_id: str,
    created_at: datetime,
    authority: HeldoutACRuntimeTaskAuthority,
) -> RunManifest:
    """Build the exact v2 manifest consumed by a future dedicated dispatcher."""

    if not heldout_ac_candidate_matches_current_execution_inputs(candidate):
        raise HeldoutACExecutionError("held-out candidate realized schedule differs from inputs")
    row = next((item for item in candidate.schedule if item.order == row_order), None)
    if row is None or authority.task_binding.task.task_id != row.task_id:
        raise HeldoutACExecutionError("held-out runtime authority belongs to another row")
    role = (
        DatasetRole.CORE_SAME_REPO if row.role == "core-same-repo" else DatasetRole.CORE_CROSS_REPO
    )
    condition = MemoryCondition(row.condition)
    memory = MemoryConfig(
        condition=condition,
        index_version=D110_INDEX_VERSION if condition == MemoryCondition.STRUCTURED else None,
        index_hash=D110_INDEX_CONTENT_HASH if condition == MemoryCondition.STRUCTURED else None,
        max_context_tokens=2_000,
    )
    manifest = RunManifest(
        schema_version="run-manifest-v2",
        run_id=run_id,
        task_id=row.task_id,
        task_version=row.task_version,
        base_commit=row.base_commit,
        public_spec_hash=row.public_spec_hash,
        private_spec_hash=row.private_spec_hash,
        evaluator_contract=authority.task_binding.evaluator_contract,
        harness_git_commit=candidate.readiness.git.commit,
        tool_schema_version="v2",
        context_policy_version="phase-evidence-v5",
        memory_policy_version="fixed-d110-bundle-v1",
        model=ModelConfig(
            provider="openai",
            model_id="gpt-5.4-mini-2026-03-17",
            provider_sdk_version=candidate.readiness.openai_sdk.version,
            reasoning_effort="medium",
            reasoning_mode="standard",
            service_tier="default",
            transport_max_retries=0,
            temperature=0.0,
            max_output_tokens=25_000,
            input_price_per_million_usd=0.75,
            cached_input_price_per_million_usd=0.075,
            cache_write_input_price_per_million_usd=0.75,
            output_price_per_million_usd=4.5,
        ),
        budget=Budget(
            max_model_calls=240,
            max_tool_calls=400,
            max_total_tokens=MAX_TOTAL_TOKENS,
            wall_clock_timeout_seconds=3_600,
            token_budget_schema_version="cumulative-split-v1",
            max_cumulative_input_tokens=MAX_CUMULATIVE_INPUT_TOKENS,
            max_cumulative_output_tokens=MAX_CUMULATIVE_OUTPUT_TOKENS,
        ),
        sandbox_backend="docker",
        agent_image_digest=row.evaluator_image_digest,
        evaluator_image_digest=row.evaluator_image_digest,
        fault=FaultSpec(),
        memory=memory,
        experiment=ExperimentRunContext(
            experiment_id=HELDOUT_AC_SUITE_ID,
            purpose=ExperimentPurpose.CORE,
            suite_hash=candidate.suite_content_hash,
            execution_hash=candidate.execution_hash,
            campaign_cost_control_hash=candidate.campaign_cost_control.content_hash,
            dataset_manifest_hash=candidate.dataset_manifest_hash,
            dataset_role=role,
            schedule_seed=20_260_814,
            schedule_order=row.order,
            schedule_row_id=row.schedule_row_id,
            repetition=row.repetition,
        ),
        created_at=created_at,
    )
    if evaluator_v2_manifest_runtime_tuple_hash(manifest) != candidate.runtime_tuple_hash:
        raise HeldoutACExecutionError("held-out manifest runtime tuple differs from candidate")
    return manifest


def candidate_json(candidate: HeldoutACExecutionCandidate) -> str:
    """Return the public, secret-free candidate representation."""

    return candidate.model_dump_json(indent=2, exclude_none=True) + "\n"


__all__ = [
    "MATERIALIZATION_CONTENT_HASH",
    "MATERIALIZATION_FILE_BYTES",
    "MATERIALIZATION_FILE_SHA256",
    "MATERIALIZATION_PATH",
    "MATERIALIZATION_PRICING_HASH",
    "MATERIALIZATION_SOURCE_HASH",
    "MATERIALIZATION_TASK_BINDINGS_HASH",
    "LEGACY_MATERIALIZATION_CONTENT_HASH",
    "LEGACY_MATERIALIZATION_FILE_BYTES",
    "LEGACY_MATERIALIZATION_FILE_SHA256",
    "LEGACY_MATERIALIZATION_PATH",
    "SUITE_PATH",
    "HeldoutACExecutionCandidate",
    "HeldoutACExecutionError",
    "HeldoutACNoCallReadiness",
    "HeldoutACRuntimeTaskAuthority",
    "HeldoutACSourceQualificationBinding",
    "build_heldout_ac_execution_candidate",
    "build_heldout_ac_no_call_readiness",
    "build_heldout_ac_run_manifest",
    "candidate_json",
    "encode_heldout_ac_runtime_secret",
    "heldout_ac_candidate_token_limits",
    "heldout_ac_candidate_matches_current_execution_inputs",
    "heldout_ac_completion_campaign_authority",
    "heldout_ac_campaign_identity_hash",
    "materialize_heldout_ac_runtime_task_authority",
]
