"""Source-qualified Rapid V2 batch for the completion-driven Lean Harness.

This successor is deliberately separate from consumed Rapid R1.  It binds the
V8/V13 runtime, task-version-2 public checks, exact eight-row schedule and cost
controls.  Qualification and candidate materialization are local/no-call; live
execution remains closed until one exact execution hash is explicitly approved.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.agent.runner import AgentRunner, issue_live_execution_authorization
from patchloop.contracts import (
    Budget,
    DatasetRole,
    ExperimentPurpose,
    ExperimentRunContext,
    MemoryCondition,
    RunManifest,
    RunOutcomeKind,
)
from patchloop.errors import ContractError, RecoveryError
from patchloop.evals.rapid_public_development import (
    FULL_SCHEDULE_RESERVE_NANOS,
    HARD_CAP_NANOS,
    MODEL_ID,
    RUNTIME_BUDGET,
    RapidCostPolicy,
    _append_bundle_event,
    _persisted_result,
    _row_projection,
    _runtime_dependencies,
    _source_snapshot,
    _UniqueKeyLoader,
    _within,
)
from patchloop.memory.fixed_bundle import FIXED_BUNDLE_POLICY_VERSION
from patchloop.runtime import build_manifest, runtime_root
from patchloop.sandbox import DockerSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "rapid-public-development-v2"
EXPERIMENT_ID = "rapid-public-dev-lean-harness-20260821-r2"
SCHEDULE_SEED = 20260821
CONFIG_PATH = Path("experiments/rapid-public-development-lean-harness-20260821-r2.yaml")
QUALIFICATION_SCHEMA = "rapid-public-development-source-qualification-v1"
QUALIFICATION_ID = "rapid-public-dev-v2-source-qualification-20260821-r1"
QUALIFICATION_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-v2-source-qualification-20260821-r1.json"
)
CANDIDATE_SCHEMA = "rapid-public-development-candidate-v2"
CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-lean-harness-20260821-r2-candidate-v1.json"
)
CONSUMED_RESULT_PATH = Path(
    "reports/rapid-development/"
    "rapid-public-dev-lean-harness-20260821-r2-f066bd044465.jsonl"
)
RESULT_SCHEMA = "rapid-public-development-bundle-event-v2"
PLAN_SCHEMA = "experiment-execution-plan-v2"
EVIDENCE_DATE = "2026-08-21"

TASK_PATHS = (
    "tasks/dev-validation/moto-query-scanned-count-v2/public.yaml",
    "tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes-v2/public.yaml",
)
VARIANTS = ("baseline-v2v5", "lean-harness-v2")
VARIANT_CONTRACTS = {
    "baseline-v2v5": {
        "tool_schema_version": "v2",
        "context_policy_version": "phase-evidence-v5",
        "runtime_policy_version": None,
    },
    "lean-harness-v2": {
        "tool_schema_version": "v8",
        "context_policy_version": "phase-evidence-v13",
        "runtime_policy_version": "lean-harness-v2",
        "completion_policy_version": "completion-driven-current-diff-v1",
        "patch_normalization_policy_version": "safe-raw-diff-normalization-v1",
    },
}
EXPECTED_CHECK_IDS = {
    "moto-query-scanned-count": (
        "public-query-page-scanned-count",
        "upstream-dynamodb-regression",
    ),
    "babel-strict-grouped-decimal-trailing-zeroes": (
        "public-strict-trailing-zero-behavior",
        "upstream-number-regression",
    ),
}
SOURCE_PATHS = (
    "patchloop/agent/context.py",
    "patchloop/agent/finalization.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/model.py",
    "patchloop/agent/phases.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/saturation_recovery_shadow.py",
    "patchloop/agent/tools.py",
    "patchloop/cli.py",
    "patchloop/contracts.py",
    "patchloop/evals/rapid_public_development.py",
    "patchloop/evals/rapid_public_development_v2.py",
    "patchloop/runtime.py",
    "patchloop/task_loader.py",
)
VALIDATION_PATHS = (
    CONFIG_PATH.as_posix(),
    "scripts/build_rapid_public_development_v2_source_qualification.py",
    "scripts/build_rapid_public_development_v2_candidate.py",
    "tests/test_phase_evidence.py",
    "tests/test_lean_runtime.py",
    "tests/test_tool_gateway.py",
    "tests/test_benchmark_tasks.py",
    "tests/test_rapid_public_development.py",
    "tests/test_rapid_public_development_v2.py",
)


class RapidV2ScheduleRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    order: int = Field(ge=1, le=8)
    task: str
    variant: Literal["baseline-v2v5", "lean-harness-v2"]
    repetition: int = Field(ge=1, le=2)

    @field_validator("order", "repetition", mode="before")
    @classmethod
    def exact_int(cls, value: Any) -> Any:
        if type(value) is not int:
            raise ValueError("Rapid V2 schedule counters must be exact integers")
        return value


class RapidPublicDevelopmentV2Config(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["rapid-public-development-v2"]
    experiment_id: Literal["rapid-public-dev-lean-harness-20260821-r2"]
    status: Literal["development-only"]
    official: Literal[False]
    tasks: tuple[str, str]
    variants: tuple[Literal["baseline-v2v5"], Literal["lean-harness-v2"]]
    repetitions: Literal[2]
    memory_condition: Literal["no_memory"]
    model_provider: Literal["openai"]
    model_id: Literal["gpt-5.4-mini-2026-03-17"]
    reasoning_effort: Literal["medium"]
    reasoning_mode: Literal["standard"]
    service_tier: Literal["default"]
    transport_max_retries: Literal[0]
    max_output_tokens: Literal[25_000]
    budget: Budget
    schedule: tuple[RapidV2ScheduleRow, ...] = Field(min_length=8, max_length=8)
    metrics: tuple[str, ...]
    cost_policy: RapidCostPolicy
    provider_execution_authorized: Literal[False]
    approved_execution_hash: None

    @model_validator(mode="before")
    @classmethod
    def freeze_yaml_sequences(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        frozen = dict(value)
        for field in ("tasks", "variants", "schedule", "metrics"):
            sequence = frozen.get(field)
            if type(sequence) is not list:
                raise ValueError(f"Rapid V2 {field} must be a YAML sequence")
            frozen[field] = tuple(sequence)
        return frozen

    @model_validator(mode="after")
    def validate_design(self) -> Self:
        if self.tasks != TASK_PATHS or self.variants != VARIANTS:
            raise ValueError("Rapid V2 task or variant panel differs")
        if self.budget != RUNTIME_BUDGET:
            raise ValueError("Rapid V2 runtime budget differs")
        if self.metrics != (
            "evaluator_reached",
            "token_terminal",
            "submission_completed",
            "success_at_budget",
            "model_cost_nanos",
        ):
            raise ValueError("Rapid V2 metric set differs")
        if tuple(row.order for row in self.schedule) != tuple(range(1, 9)):
            raise ValueError("Rapid V2 schedule order is not contiguous")
        expected_cells = {
            (task, variant, repetition)
            for task in TASK_PATHS
            for variant in VARIANTS
            for repetition in (1, 2)
        }
        actual_cells = {(row.task, row.variant, row.repetition) for row in self.schedule}
        if actual_cells != expected_cells or len(actual_cells) != 8:
            raise ValueError("Rapid V2 schedule is not the exact 2x2x2 matrix")
        for task in TASK_PATHS:
            first = [
                row.variant
                for row in self.schedule
                if row.task == task and row.repetition == 1
            ]
            second = [
                row.variant
                for row in self.schedule
                if row.task == task and row.repetition == 2
            ]
            if second != list(reversed(first)):
                raise ValueError("Rapid V2 task order is not reversed across repetitions")
        return self


class FileBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    file_bytes: int = Field(gt=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class TaskBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    task_path: str
    task_id: str
    task_version: Literal[2]
    base_commit: str
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_image: str
    evaluator_image_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    package_file_count: int = Field(gt=0)
    package_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    targeted_check_id: str
    targeted_check_command_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    regression_check_id: str
    targeted_check_source: Literal["public-issue-derived"]

    @model_validator(mode="after")
    def validate_task(self) -> Self:
        expected = EXPECTED_CHECK_IDS.get(self.task_id)
        if expected != (self.targeted_check_id, self.regression_check_id):
            raise ValueError("Rapid V2 visible check identity differs")
        return self


class RapidV2SourceQualification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["rapid-public-development-source-qualification-v1"]
    qualification_id: Literal[
        "rapid-public-dev-v2-source-qualification-20260821-r1"
    ]
    status: Literal["PUBLIC_SOURCE_QUALIFIED_CANDIDATE_GENERATION_ONLY"]
    evidence_date: Literal["2026-08-21"]
    config: FileBinding
    config_semantic_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_snapshot_scope: Literal["all-patchloop-python-v1"]
    source_file_count: int = Field(gt=0)
    source_snapshot_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_dependencies: dict[str, str]
    task_bindings: tuple[TaskBinding, TaskBinding]
    schedule_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_files: tuple[FileBinding, ...]
    validation_files: tuple[FileBinding, ...]
    source_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    scheduled_rows: Literal[8]
    rows_per_variant: Literal[4]
    task_packages_complete: Literal[True]
    public_private_hashes_bound: Literal[True]
    runtime_pair_bound: Literal[True]
    provider_transport_calls: Literal[0]
    provider_generation_calls: Literal[0]
    agent_runner_calls: Literal[0]
    evaluator_calls: Literal[0]
    docker_cli_calls: Literal[0]
    network_calls: Literal[0]
    added_model_cost_usd: Literal[0]
    official: Literal[False]
    candidate_generation_authorized: Literal[True]
    provider_calls_authorized: Literal[False]
    docker_execution_authorized: Literal[False]
    paid_execution_authorized: Literal[False]
    result_claim_authorized: Literal[False]
    next_gate: Literal["materialize-exact-rapid-v2-candidate"]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_qualification(self) -> Self:
        if self.config.path != CONFIG_PATH.as_posix():
            raise ValueError("Rapid V2 qualification config path differs")
        if tuple(item.path for item in self.source_files) != SOURCE_PATHS:
            raise ValueError("Rapid V2 source inventory paths differ")
        if tuple(item.path for item in self.validation_files) != VALIDATION_PATHS:
            raise ValueError("Rapid V2 validation inventory paths differ")
        if self.source_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.source_files]
        ):
            raise ValueError("Rapid V2 source inventory hash differs")
        if self.validation_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.validation_files]
        ):
            raise ValueError("Rapid V2 validation inventory hash differs")
        if tuple(item.task_path for item in self.task_bindings) != TASK_PATHS:
            raise ValueError("Rapid V2 qualification task order differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("Rapid V2 qualification content hash differs")
        return self


def _read_config(
    path: str | Path = CONFIG_PATH,
    repository: str | Path = ".",
) -> tuple[RapidPublicDevelopmentV2Config, bytes, Path]:
    root = Path(repository).resolve()
    selected = _within(root, path)
    if selected.relative_to(root).as_posix() != CONFIG_PATH.as_posix():
        raise ContractError("Rapid V2 requires its canonical config path")
    if selected.is_symlink() or not selected.is_file():
        raise ContractError("Rapid V2 config must be a regular repository file")
    raw = selected.read_bytes()
    try:
        payload = yaml.load(raw.decode("utf-8"), Loader=_UniqueKeyLoader)
        config = RapidPublicDevelopmentV2Config.model_validate(payload)
    except (UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
        raise ContractError("Rapid V2 config is invalid") from exc
    return config, raw, selected


def _binding(root: Path, relative: str | Path) -> FileBinding:
    selected = ensure_within(root, Path(relative).as_posix())
    if selected.is_symlink() or not selected.is_file():
        raise RecoveryError(f"Rapid V2 source is unavailable: {relative}")
    raw = selected.read_bytes()
    return FileBinding(
        path=selected.relative_to(root).as_posix(),
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
    )


def _package_inventory(task_dir: Path) -> tuple[int, str]:
    required = {
        "public.yaml",
        "private.yaml",
        "environment.yaml",
        "reference.patch",
    }
    if not required.issubset({item.name for item in task_dir.iterdir()}):
        raise RecoveryError("Rapid V2 task package is incomplete")
    rows: list[dict[str, Any]] = []
    for path in sorted(task_dir.rglob("*")):
        if path.is_symlink():
            raise RecoveryError("Rapid V2 task package contains a link or escape")
        if path.is_dir():
            continue
        resolved = path.resolve()
        if task_dir not in resolved.parents:
            raise RecoveryError("Rapid V2 task package contains a link or escape")
        raw = path.read_bytes()
        rows.append(
            {
                "path": path.relative_to(task_dir).as_posix(),
                "file_bytes": len(raw),
                "file_sha256": sha256_bytes(raw),
            }
        )
    if not rows:
        raise RecoveryError("Rapid V2 task package inventory is empty")
    return len(rows), sha256_json(rows)


def _task_bindings(
    config: RapidPublicDevelopmentV2Config,
    root: Path,
) -> tuple[TaskBinding, TaskBinding]:
    bindings: list[TaskBinding] = []
    for task_path in config.tasks:
        if not task_path.startswith("tasks/dev-validation/") or not task_path.endswith(
            "-v2/public.yaml"
        ):
            raise ContractError("Rapid V2 accepts only version-2 development tasks")
        task_dir = _within(root, task_path).parent
        package = load_task_package(task_dir)
        if (
            package.public.split != "dev-validation"
            or package.public.task_version != 2
            or package.environment is None
        ):
            raise ContractError("Rapid V2 task lacks its exact development evaluator")
        check_ids = tuple(item.id for item in package.public.visible_checks)
        if check_ids != EXPECTED_CHECK_IDS.get(package.public.task_id):
            raise ContractError("Rapid V2 targeted/regression check order differs")
        count, inventory_hash = _package_inventory(task_dir)
        targeted = package.public.visible_checks[0]
        bindings.append(
            TaskBinding(
                task_path=task_path,
                task_id=package.public.task_id,
                task_version=package.public.task_version,
                base_commit=package.public.repository.base_commit,
                public_spec_hash=package.public_spec_hash,
                private_spec_hash=package.private_spec_hash,
                evaluator_image=package.environment.evaluator_image,
                evaluator_image_digest=package.environment.image_digest,
                package_file_count=count,
                package_inventory_hash=inventory_hash,
                targeted_check_id=targeted.id,
                targeted_check_command_hash=sha256_json(list(targeted.command)),
                regression_check_id=package.public.visible_checks[1].id,
                targeted_check_source="public-issue-derived",
            )
        )
    if len(bindings) != 2:
        raise ContractError("Rapid V2 requires exactly two task bindings")
    return bindings[0], bindings[1]


def _schedule_projection(
    config: RapidPublicDevelopmentV2Config,
    bindings: tuple[TaskBinding, TaskBinding],
) -> tuple[dict[str, Any], ...]:
    by_path = {item.task_path: item for item in bindings}
    projected: list[dict[str, Any]] = []
    for row in config.schedule:
        task = by_path[row.task]
        runtime = VARIANT_CONTRACTS[row.variant]
        body = {
            "order": row.order,
            "task": row.task,
            "task_id": task.task_id,
            "task_version": task.task_version,
            "variant": row.variant,
            "tool_schema_version": runtime["tool_schema_version"],
            "context_policy_version": runtime["context_policy_version"],
            "repetition": row.repetition,
            "memory_condition": "no_memory",
        }
        projected.append({**body, "schedule_row_id": sha256_json(body)})
    return tuple(projected)


def _qualification_body(repository: str | Path = ".") -> dict[str, Any]:
    root = Path(repository).resolve()
    config, raw, selected = _read_config(repository=root)
    source = _source_snapshot(root)
    dependencies = _runtime_dependencies(root)
    task_bindings = _task_bindings(config, root)
    schedule = _schedule_projection(config, task_bindings)
    source_files = tuple(_binding(root, item) for item in SOURCE_PATHS)
    validation_files = tuple(_binding(root, item) for item in VALIDATION_PATHS)
    return {
        "schema_version": QUALIFICATION_SCHEMA,
        "qualification_id": QUALIFICATION_ID,
        "status": "PUBLIC_SOURCE_QUALIFIED_CANDIDATE_GENERATION_ONLY",
        "evidence_date": EVIDENCE_DATE,
        "config": _binding(root, selected.relative_to(root)).model_dump(mode="python"),
        "config_semantic_hash": sha256_json(config.model_dump(mode="json")),
        "source_snapshot_scope": source["scope"],
        "source_file_count": source["file_count"],
        "source_snapshot_hash": source["content_hash"],
        "runtime_dependencies": dependencies,
        "task_bindings": tuple(item.model_dump(mode="python") for item in task_bindings),
        "schedule_hash": sha256_json(list(schedule)),
        "source_files": tuple(item.model_dump(mode="python") for item in source_files),
        "validation_files": tuple(item.model_dump(mode="python") for item in validation_files),
        "source_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in source_files]
        ),
        "validation_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in validation_files]
        ),
        "scheduled_rows": 8,
        "rows_per_variant": 4,
        "task_packages_complete": True,
        "public_private_hashes_bound": True,
        "runtime_pair_bound": True,
        "provider_transport_calls": 0,
        "provider_generation_calls": 0,
        "agent_runner_calls": 0,
        "evaluator_calls": 0,
        "docker_cli_calls": 0,
        "network_calls": 0,
        "added_model_cost_usd": 0,
        "official": False,
        "candidate_generation_authorized": True,
        "provider_calls_authorized": False,
        "docker_execution_authorized": False,
        "paid_execution_authorized": False,
        "result_claim_authorized": False,
        "next_gate": "materialize-exact-rapid-v2-candidate",
    }


def build_rapid_v2_source_qualification(
    repository: str | Path = ".",
) -> RapidV2SourceQualification:
    original_available = DockerSandbox.available
    original_next_turn = OpenAIResponsesAdapter.next_turn
    original_start = AgentRunner.start
    original_create_connection = socket.create_connection
    original_socket_connect = socket.socket.connect
    original_popen = subprocess.Popen

    def blocked_external(*_args: Any, **_kwargs: Any) -> Any:
        raise RecoveryError("Rapid V2 source qualification attempted an external call")

    DockerSandbox.available = staticmethod(blocked_external)
    OpenAIResponsesAdapter.next_turn = blocked_external
    AgentRunner.start = blocked_external
    socket.create_connection = blocked_external
    socket.socket.connect = blocked_external
    subprocess.Popen = blocked_external
    try:
        body = _qualification_body(repository)
    finally:
        DockerSandbox.available = staticmethod(original_available)
        OpenAIResponsesAdapter.next_turn = original_next_turn
        AgentRunner.start = original_start
        socket.create_connection = original_create_connection
        socket.socket.connect = original_socket_connect
        subprocess.Popen = original_popen
    return RapidV2SourceQualification.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )


def qualification_bytes(qualification: RapidV2SourceQualification) -> bytes:
    return (
        json.dumps(
            qualification.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_once(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        raise


def materialize_rapid_v2_source_qualification(
    repository: str | Path = ".",
    output_path: str | Path = QUALIFICATION_PATH,
) -> RapidV2SourceQualification:
    root = Path(repository).resolve()
    output = ensure_within(root, Path(output_path).as_posix())
    if output.exists():
        return load_rapid_v2_source_qualification(root, output_path)
    qualification = build_rapid_v2_source_qualification(root)
    _write_once(output, qualification_bytes(qualification))
    return load_rapid_v2_source_qualification(root, output_path)


def load_rapid_v2_source_qualification(
    repository: str | Path = ".",
    qualification_path: str | Path = QUALIFICATION_PATH,
) -> RapidV2SourceQualification:
    root = Path(repository).resolve()
    selected = ensure_within(root, Path(qualification_path).as_posix())
    if selected.is_symlink() or not selected.is_file():
        raise RecoveryError("Rapid V2 source qualification is unavailable")
    raw = selected.read_bytes()
    try:
        qualification = RapidV2SourceQualification.model_validate_json(raw)
    except ValueError as exc:
        raise RecoveryError("Rapid V2 source qualification is invalid") from exc
    if qualification_bytes(qualification) != raw:
        raise RecoveryError("Rapid V2 source qualification bytes differ")
    current = build_rapid_v2_source_qualification(root)
    if qualification != current:
        raise RecoveryError("Rapid V2 source qualification current binding differs")
    return qualification


def _execution_body(candidate: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "schema_version",
        "experiment_id",
        "purpose",
        "official",
        "config_path",
        "config_file_sha256",
        "config_semantic_hash",
        "source_qualification",
        "source_snapshot_hash",
        "source_file_count",
        "runtime_dependencies",
        "variant_contracts",
        "task_bindings",
        "schedule",
        "schedule_hash",
        "cost_control",
        "cost_control_hash",
    )
    try:
        return {key: candidate[key] for key in keys}
    except KeyError as exc:
        raise RecoveryError("Rapid V2 candidate execution body is incomplete") from exc


def _candidate_content_body(candidate: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in candidate.items() if key != "content_hash"}


def build_rapid_public_development_v2_candidate(
    config_path: str | Path = CONFIG_PATH,
    *,
    repository: str | Path = ".",
    qualification_path: str | Path = QUALIFICATION_PATH,
) -> dict[str, Any]:
    root = Path(repository).resolve()
    qualification = load_rapid_v2_source_qualification(root, qualification_path)
    qualification_file = ensure_within(root, Path(qualification_path).as_posix())
    config, raw, selected = _read_config(config_path, root)
    task_bindings = _task_bindings(config, root)
    schedule = _schedule_projection(config, task_bindings)
    if (
        tuple(item.model_dump(mode="json") for item in task_bindings)
        != tuple(item.model_dump(mode="json") for item in qualification.task_bindings)
        or sha256_json(list(schedule)) != qualification.schedule_hash
    ):
        raise RecoveryError("Rapid V2 candidate differs from source qualification")
    cost_control = {
        **config.cost_policy.model_dump(mode="json"),
        "scheduled_run_count": len(schedule),
        "cost_censoring_allowed": False,
        "official": False,
    }
    body: dict[str, Any] = {
        "schema_version": CANDIDATE_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "purpose": ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT.value,
        "official": False,
        "config_path": selected.relative_to(root).as_posix(),
        "config_file_sha256": sha256_bytes(raw),
        "config_semantic_hash": sha256_json(config.model_dump(mode="json")),
        "source_qualification": {
            "path": qualification_file.relative_to(root).as_posix(),
            "file_bytes": qualification_file.stat().st_size,
            "file_sha256": sha256_bytes(qualification_file.read_bytes()),
            "content_hash": qualification.content_hash,
        },
        "source_snapshot_hash": qualification.source_snapshot_hash,
        "source_file_count": qualification.source_file_count,
        "runtime_dependencies": qualification.runtime_dependencies,
        "variant_contracts": VARIANT_CONTRACTS,
        "task_bindings": [item.model_dump(mode="json") for item in task_bindings],
        "schedule": list(schedule),
        "schedule_hash": sha256_json(list(schedule)),
        "cost_control": cost_control,
        "cost_control_hash": sha256_json(cost_control),
    }
    execution_hash = sha256_json(body)
    candidate = {
        **body,
        "execution_hash": execution_hash,
        "source_qualified": True,
        "execution_authorized": False,
        "provider_calls_made": 0,
        "docker_calls_made": 0,
        "added_model_cost_usd": 0.0,
        "approval_required": True,
    }
    return {**candidate, "content_hash": sha256_json(candidate)}


def _validate_candidate(candidate: dict[str, Any]) -> None:
    if (
        candidate.get("schema_version") != CANDIDATE_SCHEMA
        or candidate.get("experiment_id") != EXPERIMENT_ID
        or candidate.get("official") is not False
        or candidate.get("source_qualified") is not True
        or candidate.get("execution_authorized") is not False
        or candidate.get("provider_calls_made") != 0
        or candidate.get("docker_calls_made") != 0
        or candidate.get("added_model_cost_usd") != 0.0
        or candidate.get("approval_required") is not True
        or candidate.get("execution_hash") != sha256_json(_execution_body(candidate))
        or candidate.get("content_hash")
        != sha256_json(_candidate_content_body(candidate))
    ):
        raise RecoveryError("Rapid V2 candidate identity differs")


def candidate_bytes(candidate: dict[str, Any]) -> bytes:
    _validate_candidate(candidate)
    return (json.dumps(candidate, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def materialize_rapid_public_development_v2_candidate(
    repository: str | Path = ".",
    output_path: str | Path = CANDIDATE_PATH,
) -> dict[str, Any]:
    root = Path(repository).resolve()
    output = ensure_within(root, Path(output_path).as_posix())
    if output.exists():
        return load_rapid_public_development_v2_candidate(root, output_path)
    candidate = build_rapid_public_development_v2_candidate(repository=root)
    for order in range(1, 9):
        manifest = build_rapid_v2_run_manifest(candidate, order, repository=root)
        if not _manifest_matches_candidate(candidate, manifest):
            raise RecoveryError("Rapid V2 candidate manifest validation differs")
    _write_once(output, candidate_bytes(candidate))
    return load_rapid_public_development_v2_candidate(root, output_path)


def load_rapid_public_development_v2_candidate(
    repository: str | Path = ".",
    candidate_path: str | Path = CANDIDATE_PATH,
) -> dict[str, Any]:
    root = Path(repository).resolve()
    selected = ensure_within(root, Path(candidate_path).as_posix())
    if selected.is_symlink() or not selected.is_file():
        raise RecoveryError("Rapid V2 candidate is unavailable")
    try:
        candidate = json.loads(selected.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError("Rapid V2 candidate is invalid") from exc
    if type(candidate) is not dict or candidate_bytes(candidate) != selected.read_bytes():
        raise RecoveryError("Rapid V2 candidate bytes differ")
    try:
        qualification_path = candidate["source_qualification"]["path"]
    except (KeyError, TypeError) as exc:
        raise RecoveryError("Rapid V2 candidate qualification binding is invalid") from exc
    current = build_rapid_public_development_v2_candidate(
        repository=root,
        qualification_path=qualification_path,
    )
    if candidate != current:
        raise RecoveryError("Rapid V2 candidate current binding differs")
    return candidate


def _plan(candidate: dict[str, Any], *, approved: bool) -> dict[str, Any]:
    _validate_candidate(candidate)
    body = {
        "schema_version": PLAN_SCHEMA,
        "ready": approved,
        "blockers": [] if approved else ["EXACT_APPROVAL_REQUIRED"],
        "purpose": ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT.value,
        "official": False,
        "execution_hash": candidate["execution_hash"],
        "suite_hash": candidate["config_semantic_hash"],
        "source_snapshot_hash": candidate["source_snapshot_hash"],
        "source_qualification": candidate["source_qualification"],
        "runtime_dependencies": candidate["runtime_dependencies"],
        "variant_contracts": candidate["variant_contracts"],
        "task_bindings": candidate["task_bindings"],
        "schedule": candidate["schedule"],
        "schedule_hash": candidate["schedule_hash"],
        "campaign_cost_control": {
            "content_hash": candidate["cost_control_hash"],
            "descriptor": candidate["cost_control"],
        },
        "approval": {
            "invocation_approve_live_cost": approved,
            "invocation_approved_execution_hash": (
                candidate["execution_hash"] if approved else None
            ),
            "matches_execution_hash": approved,
        },
    }
    return {**body, "content_hash": sha256_json(body)}


def build_rapid_v2_run_manifest(
    candidate: dict[str, Any],
    order: int,
    *,
    repository: str | Path = ".",
) -> RunManifest:
    _validate_candidate(candidate)
    root = Path(repository).resolve()
    row = next(item for item in candidate["schedule"] if item["order"] == order)
    binding = next(
        item for item in candidate["task_bindings"] if item["task_id"] == row["task_id"]
    )
    package = load_task_package(_within(root, row["task"]).parent)
    experiment = ExperimentRunContext(
        experiment_id=EXPERIMENT_ID,
        purpose=ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT,
        suite_hash=candidate["config_semantic_hash"],
        execution_hash=candidate["execution_hash"],
        campaign_cost_control_hash=candidate["cost_control_hash"],
        dataset_manifest_hash=None,
        dataset_role=DatasetRole.DEVELOPMENT_VALIDATION,
        schedule_seed=SCHEDULE_SEED,
        schedule_order=order,
        schedule_row_id=row["schedule_row_id"],
        repetition=row["repetition"],
    )
    manifest = build_manifest(
        package,
        run_id=f"run_rapid_v2_{candidate['execution_hash'][7:19]}_{order:02d}",
        provider="openai",
        model_id=MODEL_ID,
        memory_condition=MemoryCondition.NO_MEMORY,
        memory_policy_version=FIXED_BUNDLE_POLICY_VERSION,
        sandbox_backend="docker",
        budget=RUNTIME_BUDGET,
        agent_image_digest=binding["evaluator_image_digest"],
        evaluator_image_digest=binding["evaluator_image_digest"],
        input_price_per_million_usd=0.75,
        cached_input_price_per_million_usd=0.075,
        cache_write_input_price_per_million_usd=0.75,
        output_price_per_million_usd=4.5,
        reasoning_effort="medium",
        reasoning_mode="standard",
        service_tier="default",
        transport_max_retries=0,
        max_output_tokens=25_000,
        experiment_context=experiment,
    )
    payload = manifest.model_dump(mode="python")
    payload["model"]["temperature"] = 0.0
    payload["tool_schema_version"] = row["tool_schema_version"]
    payload["context_policy_version"] = row["context_policy_version"]
    return RunManifest.model_validate(payload)


def _row_for_manifest(candidate: dict[str, Any], manifest: RunManifest) -> dict[str, Any] | None:
    experiment = manifest.experiment
    if experiment is None:
        return None
    return next(
        (
            row
            for row in candidate["schedule"]
            if row["schedule_row_id"] == experiment.schedule_row_id
        ),
        None,
    )


def _manifest_matches_candidate(candidate: dict[str, Any], manifest: RunManifest) -> bool:
    try:
        row = _row_for_manifest(candidate, manifest)
        assert row is not None
        binding = next(
            item
            for item in candidate["task_bindings"]
            if item["task_id"] == manifest.task_id
        )
        experiment = manifest.experiment
        assert experiment is not None
        return bool(
            experiment.purpose == ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT
            and experiment.experiment_id == EXPERIMENT_ID
            and experiment.suite_hash == candidate["config_semantic_hash"]
            and experiment.execution_hash == candidate["execution_hash"]
            and experiment.campaign_cost_control_hash == candidate["cost_control_hash"]
            and experiment.dataset_role == DatasetRole.DEVELOPMENT_VALIDATION
            and experiment.schedule_seed == SCHEDULE_SEED
            and experiment.schedule_order == row["order"]
            and experiment.repetition == row["repetition"]
            and manifest.task_id == row["task_id"] == binding["task_id"]
            and manifest.task_version == row["task_version"] == binding["task_version"] == 2
            and manifest.tool_schema_version == row["tool_schema_version"]
            and manifest.context_policy_version == row["context_policy_version"]
            and manifest.memory.condition == MemoryCondition.NO_MEMORY
            and manifest.memory.index_version is None
            and manifest.memory.index_hash is None
            and manifest.budget == RUNTIME_BUDGET
            and manifest.model.provider == "openai"
            and manifest.model.model_id == MODEL_ID
            and manifest.model.provider_sdk_version
            == candidate["runtime_dependencies"]["openai_sdk_version"]
            and manifest.model.reasoning_effort == "medium"
            and manifest.model.reasoning_mode == "standard"
            and manifest.model.service_tier == "default"
            and manifest.model.transport_max_retries == 0
            and manifest.model.temperature == 0.0
            and manifest.model.max_output_tokens == 25_000
            and manifest.sandbox_backend == "docker"
            and manifest.evaluator_image_digest == binding["evaluator_image_digest"]
            and manifest.agent_image_digest == binding["evaluator_image_digest"]
            and manifest.public_spec_hash == binding["public_spec_hash"]
            and manifest.private_spec_hash == binding["private_spec_hash"]
            and manifest.base_commit == binding["base_commit"]
        )
    except (AssertionError, KeyError, StopIteration, TypeError, ValueError):
        return False


def rapid_v2_live_plan_matches_manifest(
    *,
    plan: dict[str, Any],
    manifest: RunManifest,
    repository: str | Path = ".",
) -> bool:
    try:
        if (Path(repository).resolve() / CONSUMED_RESULT_PATH).is_file():
            return False
        candidate = load_rapid_public_development_v2_candidate(repository)
        return bool(
            plan == _plan(candidate, approved=True)
            and _manifest_matches_candidate(candidate, manifest)
        )
    except (ContractError, RecoveryError, TypeError, ValueError):
        return False


def _write_or_validate_plan(candidate: dict[str, Any], root: Path) -> Path:
    plan = _plan(candidate, approved=True)
    raw = (canonical_json(plan) + "\n").encode("utf-8")
    path = (
        root
        / ".patchloop"
        / "experiments"
        / "plans"
        / (candidate["execution_hash"].removeprefix("sha256:") + ".json")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        if path.read_bytes() != raw:
            raise ContractError("Rapid V2 approved plan path contains different bytes") from None
    return path


def run_rapid_public_development_v2(
    config_path: str | Path = CONFIG_PATH,
    *,
    approve_live_cost: bool,
    approved_execution_hash: str | None,
    repository: str | Path = ".",
) -> dict[str, Any]:
    """Run the exact R2 batch only after hash-and-cap approval."""

    root = Path(repository).resolve()
    if (root / CONSUMED_RESULT_PATH).is_file():
        raise ContractError("Rapid V2 execution is consumed and cannot be retried")
    _read_config(config_path, root)
    candidate = load_rapid_public_development_v2_candidate(root)
    if not approve_live_cost or approved_execution_hash != candidate["execution_hash"]:
        raise ContractError("Rapid V2 live execution requires its exact hash and cost-cap approval")
    if not os.environ.get("OPENAI_API_KEY"):
        raise ContractError("Rapid V2 live execution requires OPENAI_API_KEY")
    if not DockerSandbox.available():
        raise ContractError("Rapid V2 live execution requires the local Docker daemon")
    for binding in candidate["task_bindings"]:
        if (
            DockerSandbox(binding["evaluator_image"]).image_identity()
            != binding["evaluator_image_digest"]
        ):
            raise ContractError(f"Rapid V2 evaluator image is unavailable: {binding['task_id']}")

    _write_or_validate_plan(candidate, root)
    authorization = issue_live_execution_authorization(
        candidate["execution_hash"],
        root=runtime_root(),
    )
    bundle_path = (
        root
        / "reports"
        / "rapid-development"
        / (f"{EXPERIMENT_ID}-{candidate['execution_hash'][7:19]}.jsonl")
    )
    _append_bundle_event(
        bundle_path,
        {
            "schema_version": RESULT_SCHEMA,
            "event": "batch-started",
            "official": False,
            "experiment_id": EXPERIMENT_ID,
            "execution_hash": candidate["execution_hash"],
            "schedule_hash": candidate["schedule_hash"],
            "cost_control_hash": candidate["cost_control_hash"],
            "full_schedule_reserve_nanos": FULL_SCHEDULE_RESERVE_NANOS,
            "hard_cap_nanos": HARD_CAP_NANOS,
        },
        create=True,
    )

    runner = AgentRunner()
    rows: list[dict[str, Any]] = []
    accrued_nanos = 0
    halted = False
    for schedule_row in candidate["schedule"]:
        if halted:
            _append_bundle_event(
                bundle_path,
                {
                    "schema_version": RESULT_SCHEMA,
                    "event": "row-not-started",
                    "official": False,
                    **schedule_row,
                    "reason": "prior-infrastructure-terminal",
                },
            )
            continue
        manifest = build_rapid_v2_run_manifest(
            candidate,
            schedule_row["order"],
            repository=root,
        )
        result: dict[str, Any] | None = None
        error: Exception | None = None
        try:
            result = runner.start(
                schedule_row["task"],
                model="openai",
                memory_condition=MemoryCondition.NO_MEMORY,
                manifest=manifest,
                live_authorization=authorization,
            )
        except Exception as exc:  # terminal projection preserves the exact failure
            error = exc
            result = _persisted_result(runner, manifest.run_id)
        projected = _row_projection(
            schedule_row=schedule_row,
            result=result,
            runner=runner,
            error=error,
        )
        accrued_nanos += projected["model_cost_nanos"]
        if accrued_nanos > HARD_CAP_NANOS:
            raise ContractError("Rapid V2 observed cost exceeds the approved hard cap")
        _append_bundle_event(
            bundle_path,
            {"schema_version": RESULT_SCHEMA, "event": "row-terminal", **projected},
        )
        rows.append(projected)
        halted = projected["outcome_kind"] == RunOutcomeKind.INFRASTRUCTURE_ERROR.value

    summary = {
        "schema_version": RESULT_SCHEMA,
        "event": "batch-completed",
        "official": False,
        "experiment_id": EXPERIMENT_ID,
        "execution_hash": candidate["execution_hash"],
        "started_rows": len(rows),
        "evaluator_reached": sum(row["evaluator_reached"] for row in rows),
        "token_terminals": sum(row["token_terminal"] for row in rows),
        "submissions_completed": sum(row["submission_completed"] for row in rows),
        "successes_at_budget": sum(row["success_at_budget"] for row in rows),
        "model_cost_nanos": accrued_nanos,
        "result_bundle": bundle_path.relative_to(root).as_posix(),
        "external_claim_authorized": False,
        "confirmatory_promotion_automatic": False,
    }
    return _append_bundle_event(bundle_path, summary)


__all__ = [
    "CANDIDATE_PATH",
    "CONSUMED_RESULT_PATH",
    "CONFIG_PATH",
    "EXPERIMENT_ID",
    "QUALIFICATION_PATH",
    "RapidPublicDevelopmentV2Config",
    "RapidV2SourceQualification",
    "build_rapid_public_development_v2_candidate",
    "build_rapid_v2_run_manifest",
    "build_rapid_v2_source_qualification",
    "load_rapid_public_development_v2_candidate",
    "load_rapid_v2_source_qualification",
    "materialize_rapid_public_development_v2_candidate",
    "materialize_rapid_v2_source_qualification",
    "rapid_v2_live_plan_matches_manifest",
    "run_rapid_public_development_v2",
]
