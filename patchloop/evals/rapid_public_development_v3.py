"""Lightweight hard-panel successor for Rapid Public Development.

Rapid V3 keeps the consumed V2 runtime comparison but replaces its saturated
Moto/Babel panel with two immutable public development tasks.  Candidate
materialization is the single no-call qualification artifact; live execution
remains closed until its exact execution hash and cost cap are approved.
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
from patchloop.evals.rapid_public_development_v2 import FileBinding, _write_once
from patchloop.memory.fixed_bundle import FIXED_BUNDLE_POLICY_VERSION
from patchloop.runtime import build_manifest
from patchloop.sandbox import DockerSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "rapid-public-development-v3"
EXPERIMENT_ID = "rapid-public-dev-hard-panel-20260822-r3"
SCHEDULE_SEED = 20260822
CONFIG_PATH = Path("experiments/rapid-public-development-hard-panel-20260822-r3.yaml")
CANDIDATE_SCHEMA = "rapid-public-development-candidate-v3"
CANDIDATE_REVISION = 3
CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-hard-panel-20260822-r3-candidate-v3.json"
)
PREDECESSOR_CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-hard-panel-20260822-r3-candidate-v2.json"
)
PREDECESSOR_TERMINAL_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-hard-panel-20260822-r3-live-boundary-terminal-v2.json"
)
RESULT_SCHEMA = "rapid-public-development-bundle-event-v3"
PLAN_SCHEMA = "experiment-execution-plan-v3"
PLAN_KIND = "rapid-public-development-hard-panel-v1"

TASK_PATHS = (
    "tasks/dev-train/pdm-ignore-active-venv-resolution/public.yaml",
    "tasks/dev-train/anyio-interrupt-runner-cleanup/public.yaml",
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
    "pdm-ignore-active-venv-resolution": ("upstream-project-regression",),
    "anyio-interrupt-runner-cleanup": ("upstream-pytest-plugin-regression",),
}
SELECTION_EVIDENCE = {
    "schema_version": "rapid-public-selection-evidence-v1",
    "policy_version": "public-development-success-ceiling-break-v1",
    "source": "public-development-results-through-20260805",
    "official": False,
    "heldout_outcomes_used": False,
    "private_evidence_used": False,
    "tasks": [
        {
            "task_id": "pdm-ignore-active-venv-resolution",
            "observed_runs": 9,
            "successes": 3,
            "agent_failures": 4,
            "task_failures": 2,
            "selection_role": "non-ceiling-anchor",
        },
        {
            "task_id": "anyio-interrupt-runner-cleanup",
            "observed_runs": 10,
            "successes": 0,
            "agent_failures": 7,
            "task_failures": 3,
            "selection_role": "completion-stress",
        },
    ],
}
SOURCE_PATHS = (
    "patchloop/agent/context.py",
    "patchloop/agent/finalization.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/model.py",
    "patchloop/agent/phases.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/cli.py",
    "patchloop/contracts.py",
    "patchloop/evals/rapid_public_development.py",
    "patchloop/evals/rapid_public_development_v2.py",
    "patchloop/evals/rapid_public_development_v3.py",
    "patchloop/runtime.py",
    "patchloop/task_loader.py",
)
VALIDATION_PATHS = (
    CONFIG_PATH.as_posix(),
    "scripts/build_rapid_public_development_v3_candidate.py",
    "tests/test_phase_evidence.py",
    "tests/test_lean_runtime.py",
    "tests/test_tool_gateway.py",
    "tests/test_benchmark_tasks.py",
    "tests/test_rapid_public_development_v3.py",
)


class RapidV3ScheduleRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    order: int = Field(ge=1, le=8)
    task: str
    variant: Literal["baseline-v2v5", "lean-harness-v2"]
    repetition: int = Field(ge=1, le=2)

    @field_validator("order", "repetition", mode="before")
    @classmethod
    def exact_int(cls, value: Any) -> Any:
        if type(value) is not int:
            raise ValueError("Rapid V3 schedule counters must be exact integers")
        return value


class RapidPublicDevelopmentV3Config(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["rapid-public-development-v3"]
    experiment_id: Literal["rapid-public-dev-hard-panel-20260822-r3"]
    status: Literal["development-only"]
    official: Literal[False]
    selection_policy_version: Literal["public-development-success-ceiling-break-v1"]
    public_development_history_only: Literal[True]
    heldout_outcomes_used: Literal[False]
    private_evidence_used: Literal[False]
    task_packages_modified: Literal[False]
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
    schedule: tuple[RapidV3ScheduleRow, ...] = Field(min_length=8, max_length=8)
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
                raise ValueError(f"Rapid V3 {field} must be a YAML sequence")
            frozen[field] = tuple(sequence)
        return frozen

    @model_validator(mode="after")
    def validate_design(self) -> Self:
        if self.tasks != TASK_PATHS or self.variants != VARIANTS:
            raise ValueError("Rapid V3 task or variant panel differs")
        if self.budget != RUNTIME_BUDGET:
            raise ValueError("Rapid V3 runtime budget differs")
        if self.metrics != (
            "evaluator_reached",
            "token_terminal",
            "submission_completed",
            "success_at_budget",
            "model_calls",
            "tool_calls",
            "model_cost_nanos",
        ):
            raise ValueError("Rapid V3 metric set differs")
        if tuple(row.order for row in self.schedule) != tuple(range(1, 9)):
            raise ValueError("Rapid V3 schedule order is not contiguous")
        expected = {
            (task, variant, repetition)
            for task in TASK_PATHS
            for variant in VARIANTS
            for repetition in (1, 2)
        }
        actual = {(row.task, row.variant, row.repetition) for row in self.schedule}
        if actual != expected or len(actual) != 8:
            raise ValueError("Rapid V3 schedule is not the exact 2x2x2 matrix")
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
                raise ValueError("Rapid V3 task order is not reversed across repetitions")
        return self


class RapidV3TaskBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    task_path: str
    task_id: str
    task_version: Literal[1]
    base_commit: str
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_image: str
    evaluator_image_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    package_file_count: int = Field(gt=0)
    package_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    visible_check_ids: tuple[str, ...] = Field(min_length=1)
    visible_check_command_hashes: tuple[str, ...] = Field(min_length=1)
    task_package_modified: Literal[False]

    @model_validator(mode="after")
    def validate_task(self) -> Self:
        if self.visible_check_ids != EXPECTED_CHECK_IDS.get(self.task_id):
            raise ValueError("Rapid V3 visible check identity differs")
        if len(self.visible_check_command_hashes) != len(self.visible_check_ids):
            raise ValueError("Rapid V3 visible check hash count differs")
        return self


def _read_config(
    path: str | Path = CONFIG_PATH,
    repository: str | Path = ".",
) -> tuple[RapidPublicDevelopmentV3Config, bytes, Path]:
    root = Path(repository).resolve()
    selected = _within(root, path)
    if selected.relative_to(root).as_posix() != CONFIG_PATH.as_posix():
        raise ContractError("Rapid V3 requires its canonical config path")
    if selected.is_symlink() or not selected.is_file():
        raise ContractError("Rapid V3 config must be a regular repository file")
    raw = selected.read_bytes()
    try:
        payload = yaml.load(raw.decode("utf-8"), Loader=_UniqueKeyLoader)
        config = RapidPublicDevelopmentV3Config.model_validate(payload)
    except (UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
        raise ContractError("Rapid V3 config is invalid") from exc
    return config, raw, selected


def _binding(root: Path, relative: str | Path) -> FileBinding:
    selected = ensure_within(root, Path(relative).as_posix())
    if selected.is_symlink() or not selected.is_file():
        raise RecoveryError(f"Rapid V3 source is unavailable: {relative}")
    raw = selected.read_bytes()
    return FileBinding(
        path=selected.relative_to(root).as_posix(),
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
    )


def _package_inventory(task_dir: Path) -> tuple[int, str]:
    required = {"public.yaml", "private.yaml", "environment.yaml", "reference.patch"}
    if not required.issubset({item.name for item in task_dir.iterdir()}):
        raise RecoveryError("Rapid V3 task package is incomplete")
    rows: list[dict[str, Any]] = []
    for path in sorted(task_dir.rglob("*")):
        if path.is_symlink():
            raise RecoveryError("Rapid V3 task package contains a link or escape")
        if path.is_dir():
            continue
        resolved = path.resolve()
        if task_dir not in resolved.parents:
            raise RecoveryError("Rapid V3 task package contains a link or escape")
        raw = path.read_bytes()
        rows.append(
            {
                "path": path.relative_to(task_dir).as_posix(),
                "file_bytes": len(raw),
                "file_sha256": sha256_bytes(raw),
            }
        )
    if not rows:
        raise RecoveryError("Rapid V3 task package inventory is empty")
    return len(rows), sha256_json(rows)


def _task_bindings(
    config: RapidPublicDevelopmentV3Config,
    root: Path,
) -> tuple[RapidV3TaskBinding, RapidV3TaskBinding]:
    bindings: list[RapidV3TaskBinding] = []
    for task_path in config.tasks:
        if not task_path.startswith("tasks/dev-train/"):
            raise ContractError("Rapid V3 accepts only public development tasks")
        task_dir = _within(root, task_path).parent
        package = load_task_package(task_dir)
        if (
            package.public.split != "dev-train"
            or package.public.task_version != 1
            or package.environment is None
        ):
            raise ContractError("Rapid V3 task lacks its exact development evaluator")
        check_ids = tuple(item.id for item in package.public.visible_checks)
        if check_ids != EXPECTED_CHECK_IDS.get(package.public.task_id):
            raise ContractError("Rapid V3 visible check order differs")
        count, inventory_hash = _package_inventory(task_dir)
        bindings.append(
            RapidV3TaskBinding(
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
                visible_check_ids=check_ids,
                visible_check_command_hashes=tuple(
                    sha256_json(list(item.command))
                    for item in package.public.visible_checks
                ),
                task_package_modified=False,
            )
        )
    if len(bindings) != 2:
        raise ContractError("Rapid V3 requires exactly two task bindings")
    return bindings[0], bindings[1]


def _schedule_projection(
    config: RapidPublicDevelopmentV3Config,
    bindings: tuple[RapidV3TaskBinding, RapidV3TaskBinding],
) -> tuple[dict[str, Any], ...]:
    by_path = {item.task_path: item for item in bindings}
    rows: list[dict[str, Any]] = []
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
        rows.append({**body, "schedule_row_id": sha256_json(body)})
    return tuple(rows)


def _candidate_body(repository: str | Path = ".") -> dict[str, Any]:
    root = Path(repository).resolve()
    config, raw, selected = _read_config(repository=root)
    source = _source_snapshot(root)
    bindings = _task_bindings(config, root)
    schedule = _schedule_projection(config, bindings)
    validation_files = tuple(_binding(root, item) for item in VALIDATION_PATHS)
    cost_control = {
        **config.cost_policy.model_dump(mode="json"),
        "scheduled_run_count": len(schedule),
        "cost_censoring_allowed": False,
        "official": False,
    }
    return {
        "schema_version": CANDIDATE_SCHEMA,
        "candidate_revision": CANDIDATE_REVISION,
        "experiment_id": EXPERIMENT_ID,
        "purpose": ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT.value,
        "official": False,
        "config_path": selected.relative_to(root).as_posix(),
        "config_file_sha256": sha256_bytes(raw),
        "config_semantic_hash": sha256_json(config.model_dump(mode="json")),
        "selection_evidence": SELECTION_EVIDENCE,
        "selection_evidence_hash": sha256_json(SELECTION_EVIDENCE),
        "source_snapshot_scope": source["scope"],
        "source_snapshot_hash": source["content_hash"],
        "source_file_count": source["file_count"],
        "runtime_dependencies": _runtime_dependencies(root),
        "source_files": [
            _binding(root, item).model_dump(mode="json") for item in SOURCE_PATHS
        ],
        "validation_files": [item.model_dump(mode="json") for item in validation_files],
        "validation_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in validation_files]
        ),
        "predecessor_candidate": _binding(
            root,
            PREDECESSOR_CANDIDATE_PATH,
        ).model_dump(mode="json"),
        "predecessor_terminal": _binding(
            root,
            PREDECESSOR_TERMINAL_PATH,
        ).model_dump(mode="json"),
        "variant_contracts": VARIANT_CONTRACTS,
        "task_bindings": [item.model_dump(mode="json") for item in bindings],
        "schedule": list(schedule),
        "schedule_hash": sha256_json(list(schedule)),
        "cost_control": cost_control,
        "cost_control_hash": sha256_json(cost_control),
    }


def _execution_body(candidate: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "schema_version",
        "candidate_revision",
        "experiment_id",
        "purpose",
        "official",
        "config_path",
        "config_file_sha256",
        "config_semantic_hash",
        "selection_evidence",
        "selection_evidence_hash",
        "source_snapshot_scope",
        "source_snapshot_hash",
        "source_file_count",
        "runtime_dependencies",
        "source_files",
        "validation_files",
        "validation_inventory_hash",
        "predecessor_candidate",
        "predecessor_terminal",
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
        raise RecoveryError("Rapid V3 candidate execution body is incomplete") from exc


def build_rapid_public_development_v3_candidate(
    config_path: str | Path = CONFIG_PATH,
    *,
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    _read_config(config_path, repository=root)
    original_available = DockerSandbox.available
    original_next_turn = OpenAIResponsesAdapter.next_turn
    original_start = AgentRunner.start
    original_create_connection = socket.create_connection
    original_socket_connect = socket.socket.connect
    original_popen = subprocess.Popen

    def blocked_external(*_args: Any, **_kwargs: Any) -> Any:
        raise RecoveryError("Rapid V3 candidate generation attempted an external call")

    DockerSandbox.available = staticmethod(blocked_external)
    OpenAIResponsesAdapter.next_turn = blocked_external
    AgentRunner.start = blocked_external
    socket.create_connection = blocked_external
    socket.socket.connect = blocked_external
    subprocess.Popen = blocked_external
    try:
        body = _candidate_body(root)
    finally:
        DockerSandbox.available = staticmethod(original_available)
        OpenAIResponsesAdapter.next_turn = original_next_turn
        AgentRunner.start = original_start
        socket.create_connection = original_create_connection
        socket.socket.connect = original_socket_connect
        subprocess.Popen = original_popen
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
    content_body = {key: value for key, value in candidate.items() if key != "content_hash"}
    if (
        candidate.get("schema_version") != CANDIDATE_SCHEMA
        or candidate.get("candidate_revision") != CANDIDATE_REVISION
        or candidate.get("experiment_id") != EXPERIMENT_ID
        or candidate.get("official") is not False
        or candidate.get("source_qualified") is not True
        or candidate.get("execution_authorized") is not False
        or candidate.get("provider_calls_made") != 0
        or candidate.get("docker_calls_made") != 0
        or candidate.get("added_model_cost_usd") != 0.0
        or candidate.get("approval_required") is not True
        or candidate.get("execution_hash") != sha256_json(_execution_body(candidate))
        or candidate.get("content_hash") != sha256_json(content_body)
    ):
        raise RecoveryError("Rapid V3 candidate identity differs")


def candidate_bytes(candidate: dict[str, Any]) -> bytes:
    _validate_candidate(candidate)
    return (json.dumps(candidate, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def materialize_rapid_public_development_v3_candidate(
    repository: str | Path = ".",
    output_path: str | Path = CANDIDATE_PATH,
) -> dict[str, Any]:
    root = Path(repository).resolve()
    output = ensure_within(root, Path(output_path).as_posix())
    if output.exists():
        return load_rapid_public_development_v3_candidate(root, output_path)
    candidate = build_rapid_public_development_v3_candidate(repository=root)
    for order in range(1, 9):
        manifest = build_rapid_v3_run_manifest(candidate, order, repository=root)
        if not _manifest_matches_candidate(candidate, manifest):
            raise RecoveryError("Rapid V3 candidate manifest validation differs")
    _write_once(output, candidate_bytes(candidate))
    return load_rapid_public_development_v3_candidate(root, output_path)


def load_rapid_public_development_v3_candidate(
    repository: str | Path = ".",
    candidate_path: str | Path = CANDIDATE_PATH,
) -> dict[str, Any]:
    root = Path(repository).resolve()
    selected = ensure_within(root, Path(candidate_path).as_posix())
    if selected.is_symlink() or not selected.is_file():
        raise RecoveryError("Rapid V3 candidate is unavailable")
    try:
        candidate = json.loads(selected.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError("Rapid V3 candidate is invalid") from exc
    if type(candidate) is not dict or candidate_bytes(candidate) != selected.read_bytes():
        raise RecoveryError("Rapid V3 candidate bytes differ")
    current = build_rapid_public_development_v3_candidate(repository=root)
    if candidate != current:
        raise RecoveryError("Rapid V3 candidate current binding differs")
    return candidate


def _plan(candidate: dict[str, Any], *, approved: bool) -> dict[str, Any]:
    _validate_candidate(candidate)
    body = {
        "schema_version": PLAN_SCHEMA,
        "plan_kind": PLAN_KIND,
        "experiment_id": EXPERIMENT_ID,
        "candidate_revision": CANDIDATE_REVISION,
        "ready": approved,
        "blockers": [] if approved else ["EXACT_APPROVAL_REQUIRED"],
        "purpose": ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT.value,
        "official": False,
        "execution_hash": candidate["execution_hash"],
        "suite_hash": candidate["config_semantic_hash"],
        "source_snapshot_hash": candidate["source_snapshot_hash"],
        "selection_evidence_hash": candidate["selection_evidence_hash"],
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


def build_rapid_v3_run_manifest(
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
        dataset_role=DatasetRole.MEMORY_DEVELOPMENT,
        schedule_seed=SCHEDULE_SEED,
        schedule_order=order,
        schedule_row_id=row["schedule_row_id"],
        repetition=row["repetition"],
    )
    manifest = build_manifest(
        package,
        run_id=f"run_rapid_v3_{candidate['execution_hash'][7:19]}_{order:02d}",
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
            and experiment.dataset_role == DatasetRole.MEMORY_DEVELOPMENT
            and experiment.schedule_seed == SCHEDULE_SEED
            and experiment.schedule_order == row["order"]
            and experiment.repetition == row["repetition"]
            and manifest.task_id == row["task_id"] == binding["task_id"]
            and manifest.task_version == row["task_version"] == binding["task_version"] == 1
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


def rapid_v3_live_plan_matches_manifest(
    *,
    plan: dict[str, Any],
    manifest: RunManifest,
    repository: str | Path = ".",
) -> bool:
    try:
        candidate = load_rapid_public_development_v3_candidate(repository)
        root = Path(repository).resolve()
        experiment = manifest.experiment
        return bool(
            plan == _plan(candidate, approved=True)
            and _manifest_matches_candidate(candidate, manifest)
            and experiment is not None
            and _active_bundle_next_order(candidate, root) == experiment.schedule_order
        )
    except (ContractError, RecoveryError, TypeError, ValueError):
        return False


def _result_bundle_path(candidate: dict[str, Any], root: Path) -> Path:
    return (
        root
        / "reports"
        / "rapid-development"
        / (f"{EXPERIMENT_ID}-{candidate['execution_hash'][7:19]}.jsonl")
    )


def _batch_started_event(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": RESULT_SCHEMA,
        "event": "batch-started",
        "official": False,
        "experiment_id": EXPERIMENT_ID,
        "execution_hash": candidate["execution_hash"],
        "schedule_hash": candidate["schedule_hash"],
        "cost_control_hash": candidate["cost_control_hash"],
        "full_schedule_reserve_nanos": FULL_SCHEDULE_RESERVE_NANOS,
        "hard_cap_nanos": HARD_CAP_NANOS,
    }


def _active_bundle_next_order(candidate: dict[str, Any], root: Path) -> int | None:
    """Return the one row authorized by a valid in-progress bundle prefix."""

    path = _result_bundle_path(candidate, root)
    if path.is_symlink() or not path.is_file():
        return None
    try:
        lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    if not lines:
        return None

    events: list[dict[str, Any]] = []
    previous: str | None = None
    for line in lines:
        try:
            event = json.loads(line)
        except (TypeError, ValueError):
            return None
        if type(event) is not dict or type(event.get("content_hash")) is not str:
            return None
        body = {key: value for key, value in event.items() if key != "content_hash"}
        if (
            body.get("previous_event_hash") != previous
            or event["content_hash"] != sha256_json(body)
        ):
            return None
        previous = event["content_hash"]
        events.append(event)

    expected_start = {**_batch_started_event(candidate), "previous_event_hash": None}
    first_body = {key: value for key, value in events[0].items() if key != "content_hash"}
    if first_body != expected_start or len(events) > len(candidate["schedule"]):
        return None

    for index, event in enumerate(events[1:]):
        schedule_row = candidate["schedule"][index]
        expected_run_id = (
            f"run_rapid_v3_{candidate['execution_hash'][7:19]}_{schedule_row['order']:02d}"
        )
        if (
            event.get("schema_version") != RESULT_SCHEMA
            or event.get("event") != "row-terminal"
            or event.get("bundle_official") is not False
            or event.get("runtime_result_official") is not False
            or event.get("run_id") != expected_run_id
            or event.get("outcome_kind")
            not in {
                RunOutcomeKind.RESOLVED.value,
                RunOutcomeKind.TASK_FAILURE.value,
                RunOutcomeKind.AGENT_FAILURE.value,
            }
            or any(event.get(key) != value for key, value in schedule_row.items())
        ):
            return None
    return len(events)


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
            raise ContractError("Rapid V3 approved plan path contains different bytes") from None
    return path


def run_rapid_public_development_v3(
    config_path: str | Path = CONFIG_PATH,
    *,
    approve_live_cost: bool,
    approved_execution_hash: str | None,
    repository: str | Path = ".",
) -> dict[str, Any]:
    """Run the exact hard panel only after hash-and-cap approval."""

    root = Path(repository).resolve()
    _read_config(config_path, root)
    candidate = load_rapid_public_development_v3_candidate(root)
    bundle_path = _result_bundle_path(candidate, root)
    if bundle_path.exists() or bundle_path.is_symlink():
        raise ContractError("Rapid V3 execution is consumed and cannot be retried")
    if not approve_live_cost or approved_execution_hash != candidate["execution_hash"]:
        raise ContractError("Rapid V3 live execution requires its exact hash and cost-cap approval")

    _write_or_validate_plan(candidate, root)
    authorization = issue_live_execution_authorization(
        candidate["execution_hash"],
        root=root / ".patchloop",
    )
    if not os.environ.get("OPENAI_API_KEY"):
        raise ContractError("Rapid V3 live execution requires OPENAI_API_KEY")
    if not DockerSandbox.available():
        raise ContractError("Rapid V3 live execution requires the local Docker daemon")
    for binding in candidate["task_bindings"]:
        if (
            DockerSandbox(binding["evaluator_image"]).image_identity()
            != binding["evaluator_image_digest"]
        ):
            raise ContractError(f"Rapid V3 evaluator image is unavailable: {binding['task_id']}")
    _append_bundle_event(bundle_path, _batch_started_event(candidate), create=True)

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
        manifest = build_rapid_v3_run_manifest(
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
            raise ContractError("Rapid V3 observed cost exceeds the approved hard cap")
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
        "model_calls": sum(row["usage"]["model_calls"] for row in rows),
        "tool_calls": sum(row["usage"]["tool_calls"] for row in rows),
        "model_cost_nanos": accrued_nanos,
        "result_bundle": bundle_path.relative_to(root).as_posix(),
        "external_claim_authorized": False,
        "confirmatory_promotion_automatic": False,
    }
    return _append_bundle_event(bundle_path, summary)


__all__ = [
    "CANDIDATE_PATH",
    "CONFIG_PATH",
    "EXPERIMENT_ID",
    "RapidPublicDevelopmentV3Config",
    "build_rapid_public_development_v3_candidate",
    "build_rapid_v3_run_manifest",
    "load_rapid_public_development_v3_candidate",
    "materialize_rapid_public_development_v3_candidate",
    "rapid_v3_live_plan_matches_manifest",
    "run_rapid_public_development_v3",
]
