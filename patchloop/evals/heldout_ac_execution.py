"""No-call activation contract for the preregistered held-out A/C panel.

This module deliberately stops before campaign state or provider dispatch.  It
binds the sealed 48-row suite, the evaluator-side R4 materialization, a fresh
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
from patchloop.evals.heldout_ac_contracts import (
    HELDOUT_AC_SUITE_ID,
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
    "reports/heldout-ac/artifacts/heldout-ac-task-pricing-materialization-r4.json"
)
MATERIALIZATION_FILE_BYTES = 52_056
MATERIALIZATION_FILE_SHA256 = (
    "sha256:37c5cb805e137e55f5b0a11b3a3235dc0514aa2a77938abfc6d74695113d5380"
)
MATERIALIZATION_CONTENT_HASH = (
    "sha256:7c6ecc31b471da83cf46ddb5a3fb687008e4a6648ae55485d0109e0d6114af58"
)
MATERIALIZATION_TASK_BINDINGS_HASH = (
    "sha256:10505056de7f4bd95a06f9c3a16414ce120442c485413e52d113c2aba4c5157f"
)
MATERIALIZATION_PRICING_HASH = (
    "sha256:03e9cde4d6d04a09995da669d7e3aea26fda31310615640508f6bd0a9c2cbd34"
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
    schema_version: Literal["heldout-ac-full-schedule-cost-control-v1"]
    suite_id: Literal[HELDOUT_AC_SUITE_ID]
    suite_content_hash: str = Field(pattern=_SHA256_PATTERN)
    execution_hash: str = Field(pattern=_SHA256_PATTERN)
    schedule_hash: str = Field(pattern=_SHA256_PATTERN)
    scheduled_run_count: Literal[48]
    per_run_reserve_nanos: Literal[5_250_000_000]
    full_schedule_reserve_nanos: Literal[252_000_000_000]
    hard_cap_nanos: Literal[275_000_000_000]
    cost_censoring_allowed: Literal[False]
    live_resume_supported: Literal[False]
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_content_hash(self) -> HeldoutACCampaignCostControl:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out campaign cost control hash differs")
        return self


class HeldoutACExecutionCandidate(HeldoutACFrozenModel):
    schema_version: Literal["heldout-ac-execution-candidate-v1"]
    status: Literal["NO_CALL_CANDIDATE_READY_EXECUTION_NOT_AUTHORIZED"]
    suite_id: Literal[HELDOUT_AC_SUITE_ID]
    suite_content_hash: str = Field(pattern=_SHA256_PATTERN)
    dataset_manifest_hash: str = Field(pattern=_SHA256_PATTERN)
    materialization: HeldoutACFileBinding
    task_bindings_hash: Literal[MATERIALIZATION_TASK_BINDINGS_HASH]
    pricing_binding_hash: Literal[MATERIALIZATION_PRICING_HASH]
    source_qualification: HeldoutACSourceQualificationBinding
    runtime_tuple_hash: str = Field(pattern=_SHA256_PATTERN)
    base_schedule_hash: str = Field(pattern=_SHA256_PATTERN)
    readiness: HeldoutACNoCallReadiness
    execution_hash: str = Field(pattern=_SHA256_PATTERN)
    schedule: tuple[HeldoutACExecutionScheduleRow, ...] = Field(min_length=48, max_length=48)
    schedule_hash: str = Field(pattern=_SHA256_PATTERN)
    campaign_cost_control: HeldoutACCampaignCostControl
    full_schedule_reserve_usd: Literal[252.0]
    hard_cap_usd: Literal[275.0]
    exact_paid_approval_present: Literal[False]
    provider_execution_authorized: Literal[False]
    evaluator_execution_authorized: Literal[False]
    agent_execution_authorized: Literal[False]
    cost_reservation_or_spend_authorized: Literal[False]

    @model_validator(mode="after")
    def validate_candidate(self) -> HeldoutACExecutionCandidate:
        if len(self.schedule) != 48 or tuple(row.order for row in self.schedule) != tuple(
            range(1, 49)
        ):
            raise ValueError("held-out candidate schedule is not exactly 48 ordered rows")
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
        raise HeldoutACExecutionError("held-out R4 materialization is invalid") from exc
    if (
        len(raw) != MATERIALIZATION_FILE_BYTES
        or sha256_bytes(raw) != MATERIALIZATION_FILE_SHA256
        or payload.content_hash != MATERIALIZATION_CONTENT_HASH
        or payload.task_bindings_hash != MATERIALIZATION_TASK_BINDINGS_HASH
        or payload.pricing.content_hash != MATERIALIZATION_PRICING_HASH
        or raw != (payload.model_dump_json(indent=2) + "\n").encode("utf-8")
    ):
        raise HeldoutACExecutionError("held-out R4 materialization bytes drifted")
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
        max_total_tokens=runtime.max_total_tokens,
        wall_clock_timeout_seconds=runtime.wall_clock_timeout_seconds,
        tool_schema_version=runtime.tool_schema_version,
        context_policy_version=runtime.context_policy_version,
        memory_policy_version=runtime.memory_policy_version,
        sandbox_backend=runtime.sandbox_backend,
        token_budget_schema_version=runtime.token_budget_schema_version,
        max_model_calls=runtime.max_model_calls,
        max_tool_calls=runtime.max_tool_calls,
        max_cumulative_input_tokens=runtime.max_cumulative_input_tokens,
        max_cumulative_output_tokens=runtime.max_cumulative_output_tokens,
    )


def _base_schedule_hash(suite: HeldoutACSuite) -> str:
    return sha256_json([item.model_dump(mode="json") for item in suite.schedule])


def _execution_projection(candidate: HeldoutACExecutionCandidate) -> dict[str, Any]:
    return {
        "schema_version": "heldout-ac-execution-v1",
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


def heldout_ac_campaign_identity_hash(candidate: HeldoutACExecutionCandidate) -> str:
    """Return the one-use paid-campaign identity, excluding transient readiness.

    ``observed_at`` and other readiness observations intentionally affect the
    execution hash, but they must not create another paid opportunity for the
    same qualified source, suite, runtime and base schedule.
    """

    checked = HeldoutACExecutionCandidate.model_validate_json(candidate.model_dump_json())
    return sha256_json(
        {
            "schema_version": "heldout-ac-paid-campaign-identity-v1",
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
            "full_schedule_reserve_nanos": 252_000_000_000,
            "hard_cap_nanos": 275_000_000_000,
        }
    )


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
    templates = {item.task.task_id: item for item in materialization.task_bindings}
    metadata = {
        item.task_id: item for item in load_heldout_ac_task_evaluator_plan(repository=root).tasks
    }
    if set(templates) != set(metadata):
        raise HeldoutACExecutionError("held-out task template set differs from metadata plan")

    base_rows: list[dict[str, Any]] = []
    for row in suite.schedule:
        task = metadata[row.task_id]
        template = templates[row.task_id]
        base_rows.append(
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

    provisional = HeldoutACExecutionCandidate.model_construct(
        schema_version="heldout-ac-execution-candidate-v1",
        status="NO_CALL_CANDIDATE_READY_EXECUTION_NOT_AUTHORIZED",
        suite_id=suite.suite_id,
        suite_content_hash=suite.content_hash,
        dataset_manifest_hash=dataset_manifest_hash,
        materialization=_materialization_binding(materialization),
        task_bindings_hash=materialization.task_bindings_hash,
        pricing_binding_hash=materialization.pricing.content_hash,
        source_qualification=source_qualification,
        runtime_tuple_hash=_runtime_tuple_hash(suite),
        base_schedule_hash=_base_schedule_hash(suite),
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
        "schema_version": "heldout-ac-full-schedule-cost-control-v1",
        "suite_id": suite.suite_id,
        "suite_content_hash": suite.content_hash,
        "execution_hash": execution_hash,
        "schedule_hash": schedule_hash,
        "scheduled_run_count": 48,
        "per_run_reserve_nanos": 5_250_000_000,
        "full_schedule_reserve_nanos": 252_000_000_000,
        "hard_cap_nanos": 275_000_000_000,
        "cost_censoring_allowed": False,
        "live_resume_supported": False,
    }
    return HeldoutACExecutionCandidate(
        schema_version="heldout-ac-execution-candidate-v1",
        status="NO_CALL_CANDIDATE_READY_EXECUTION_NOT_AUTHORIZED",
        suite_id=suite.suite_id,
        suite_content_hash=suite.content_hash,
        dataset_manifest_hash=dataset_manifest_hash,
        materialization=_materialization_binding(materialization),
        task_bindings_hash=materialization.task_bindings_hash,
        pricing_binding_hash=materialization.pricing.content_hash,
        source_qualification=source_qualification,
        runtime_tuple_hash=_runtime_tuple_hash(suite),
        base_schedule_hash=_base_schedule_hash(suite),
        readiness=readiness,
        execution_hash=execution_hash,
        schedule=schedule,
        schedule_hash=schedule_hash,
        campaign_cost_control=HeldoutACCampaignCostControl(
            **cost_body, content_hash=sha256_json(cost_body)
        ),
        full_schedule_reserve_usd=252.0,
        hard_cap_usd=275.0,
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
            max_total_tokens=4_500_000,
            wall_clock_timeout_seconds=3_600,
            token_budget_schema_version="cumulative-split-v1",
            max_cumulative_input_tokens=4_000_000,
            max_cumulative_output_tokens=500_000,
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

    return candidate.model_dump_json(indent=2) + "\n"


__all__ = [
    "MATERIALIZATION_CONTENT_HASH",
    "MATERIALIZATION_FILE_BYTES",
    "MATERIALIZATION_FILE_SHA256",
    "MATERIALIZATION_PATH",
    "MATERIALIZATION_PRICING_HASH",
    "MATERIALIZATION_TASK_BINDINGS_HASH",
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
    "heldout_ac_campaign_identity_hash",
    "materialize_heldout_ac_runtime_task_authority",
]
