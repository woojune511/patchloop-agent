"""Small, always-unofficial public-task loop for rapid agent development."""

from __future__ import annotations

import json
import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.agent.runner import AgentRunner, issue_live_execution_authorization
from patchloop.contracts import (
    Budget,
    DatasetRole,
    ExperimentPurpose,
    ExperimentRunContext,
    MemoryCondition,
    RunManifest,
    RunOutcomeKind,
    RunResult,
    Usage,
)
from patchloop.errors import ContractError
from patchloop.memory.fixed_bundle import FIXED_BUNDLE_POLICY_VERSION
from patchloop.runtime import build_manifest, runtime_root
from patchloop.sandbox import DockerSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "rapid-public-development-v1"
EXPERIMENT_ID = "rapid-public-dev-lean-harness-20260818-r1"
MODEL_ID = "gpt-5.4-mini-2026-03-17"
SCHEDULE_SEED = 20260818
CONFIG_PATH = Path("experiments/rapid-public-development-lean-harness-20260818-r1.yaml")
RESULT_SCHEMA = "rapid-public-development-bundle-event-v1"
PLAN_SCHEMA = "experiment-execution-plan-v2"

TASK_PATHS = (
    "tasks/dev-validation/moto-query-scanned-count/public.yaml",
    "tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes/public.yaml",
)
VARIANTS = ("baseline-v2v5", "lean-harness-v1")
PRICES_NANOS = {
    "uncached_input": 750,
    "cached_input": 75,
    "cache_write_input": 750,
    "output": 4500,
}
PER_RUN_RESERVE_NANOS = 1_200_000_000
FULL_SCHEDULE_RESERVE_NANOS = 9_600_000_000
HARD_CAP_NANOS = 10_000_000_000
RUNTIME_BUDGET = Budget(
    max_model_calls=240,
    max_tool_calls=400,
    max_total_tokens=1_100_000,
    wall_clock_timeout_seconds=3_600,
    token_budget_schema_version="cumulative-split-v1",
    max_cumulative_input_tokens=1_000_000,
    max_cumulative_output_tokens=100_000,
)


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(
    loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ContractError(f"rapid config repeats key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


class RapidScheduleRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    order: int = Field(ge=1, le=12)
    task: str
    variant: Literal["baseline-v2v5", "lean-harness-v1"]
    repetition: int = Field(ge=1, le=20)

    @field_validator("order", "repetition", mode="before")
    @classmethod
    def exact_int(cls, value: Any) -> Any:
        if type(value) is not int:
            raise ValueError("rapid schedule counters must be exact integers")
        return value


class RapidCostPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    per_run_reserve_nanos: Literal[1_200_000_000]
    full_schedule_reserve_nanos: Literal[9_600_000_000]
    hard_cap_nanos: Literal[10_000_000_000]
    pricing_nanos_per_token: dict[str, int]

    @model_validator(mode="after")
    def validate_cost(self) -> Self:
        if self.pricing_nanos_per_token != PRICES_NANOS:
            raise ValueError("rapid pricing differs")
        if self.full_schedule_reserve_nanos != 8 * self.per_run_reserve_nanos:
            raise ValueError("rapid full-schedule reserve differs")
        if self.full_schedule_reserve_nanos > self.hard_cap_nanos:
            raise ValueError("rapid reserve exceeds hard cap")
        return self


class RapidPublicDevelopmentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["rapid-public-development-v1"]
    experiment_id: Literal["rapid-public-dev-lean-harness-20260818-r1"]
    status: Literal["development-only"]
    official: Literal[False]
    tasks: tuple[str, str]
    variants: tuple[Literal["baseline-v2v5"], Literal["lean-harness-v1"]]
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
    schedule: tuple[RapidScheduleRow, ...] = Field(min_length=8, max_length=8)
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
                raise ValueError(f"rapid {field} must be a YAML sequence")
            frozen[field] = tuple(sequence)
        return frozen

    @model_validator(mode="after")
    def validate_design(self) -> Self:
        if self.tasks != TASK_PATHS or self.variants != VARIANTS:
            raise ValueError("rapid task or variant panel differs")
        if self.budget != RUNTIME_BUDGET:
            raise ValueError("rapid runtime budget differs")
        if self.metrics != (
            "evaluator_reached",
            "token_terminal",
            "submission_completed",
            "success_at_budget",
            "model_cost_nanos",
        ):
            raise ValueError("rapid metric set differs")
        if tuple(row.order for row in self.schedule) != tuple(range(1, 9)):
            raise ValueError("rapid schedule order is not contiguous")
        expected_cells = {
            (task, variant, repetition)
            for task in TASK_PATHS
            for variant in VARIANTS
            for repetition in (1, 2)
        }
        actual_cells = {(row.task, row.variant, row.repetition) for row in self.schedule}
        if actual_cells != expected_cells or len(actual_cells) != 8:
            raise ValueError("rapid schedule is not the exact 2x2x2 matrix")
        for task in TASK_PATHS:
            first = [
                row.variant for row in self.schedule if row.task == task and row.repetition == 1
            ]
            second = [
                row.variant for row in self.schedule if row.task == task and row.repetition == 2
            ]
            if second != list(reversed(first)):
                raise ValueError("rapid task order is not reversed across repetitions")
        return self


def _within(root: Path, value: str | Path) -> Path:
    selected = Path(value)
    if selected.is_absolute():
        try:
            selected = selected.relative_to(root)
        except ValueError as exc:
            raise ContractError("rapid path escaped repository") from exc
    return ensure_within(root, selected.as_posix())


def _read_config(path: str | Path, root: Path) -> tuple[RapidPublicDevelopmentConfig, bytes, Path]:
    selected = _within(root, path)
    if selected.is_symlink() or not selected.is_file():
        raise ContractError("rapid config must be a regular repository file")
    raw = selected.read_bytes()
    try:
        payload = yaml.load(raw.decode("utf-8"), Loader=_UniqueKeyLoader)
        config = RapidPublicDevelopmentConfig.model_validate(payload)
    except (UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
        raise ContractError("rapid config is invalid") from exc
    return config, raw, selected


def _source_snapshot(root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "patchloop").rglob("*.py")):
        resolved = path.resolve()
        if path.is_symlink() or root not in resolved.parents:
            raise ContractError("rapid source inventory contains a link or escape")
        raw = path.read_bytes()
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "file_bytes": len(raw),
                "file_sha256": sha256_bytes(raw),
            }
        )
    if not rows:
        raise ContractError("rapid source inventory is empty")
    return {
        "scope": "all-patchloop-python-v1",
        "file_count": len(rows),
        "content_hash": sha256_json(rows),
    }


def _runtime_dependencies(root: Path) -> dict[str, str]:
    lock_path = _within(root, "uv.lock")
    if lock_path.is_symlink() or not lock_path.is_file():
        raise ContractError("rapid runtime lock is unavailable")
    try:
        openai_version = version("openai")
    except PackageNotFoundError as exc:
        raise ContractError("rapid OpenAI SDK is unavailable") from exc
    return {
        "uv_lock_sha256": sha256_bytes(lock_path.read_bytes()),
        "openai_sdk_version": openai_version,
    }


def _task_bindings(config: RapidPublicDevelopmentConfig, root: Path) -> tuple[dict[str, Any], ...]:
    bindings: list[dict[str, Any]] = []
    for task in config.tasks:
        if not task.startswith("tasks/dev-validation/") or not task.endswith("/public.yaml"):
            raise ContractError("rapid loop accepts only development-validation public tasks")
        package = load_task_package(_within(root, task).parent)
        if package.public.split != "dev-validation" or package.environment is None:
            raise ContractError("rapid task lacks a development Docker evaluator")
        bindings.append(
            {
                "task_path": task,
                "task_id": package.public.task_id,
                "task_version": package.public.task_version,
                "base_commit": package.public.repository.base_commit,
                "public_spec_hash": package.public_spec_hash,
                "private_spec_hash": package.private_spec_hash,
                "evaluator_image": package.environment.evaluator_image,
                "evaluator_image_digest": package.environment.image_digest,
            }
        )
    return tuple(bindings)


def _schedule_projection(
    config: RapidPublicDevelopmentConfig,
    bindings: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], ...]:
    by_path = {row["task_path"]: row for row in bindings}
    projected: list[dict[str, Any]] = []
    for row in config.schedule:
        task = by_path[row.task]
        body = {
            "order": row.order,
            "task": row.task,
            "task_id": task["task_id"],
            "variant": row.variant,
            "repetition": row.repetition,
            "memory_condition": "no_memory",
        }
        projected.append({**body, "schedule_row_id": sha256_json(body)})
    return tuple(projected)


def build_rapid_public_development_candidate(
    config_path: str | Path = CONFIG_PATH,
    *,
    repository: str | Path = ".",
) -> dict[str, Any]:
    """Build the no-call candidate used by validation and later execution."""

    root = Path(repository).resolve()
    config, raw, selected = _read_config(config_path, root)
    if selected.relative_to(root).as_posix() != CONFIG_PATH.as_posix():
        raise ContractError("rapid candidate requires the canonical single config path")
    bindings = _task_bindings(config, root)
    schedule = _schedule_projection(config, bindings)
    source = _source_snapshot(root)
    dependencies = _runtime_dependencies(root)
    config_semantic_hash = sha256_json(config.model_dump(mode="json"))
    schedule_hash = sha256_json(list(schedule))
    cost_control = {
        **config.cost_policy.model_dump(mode="json"),
        "scheduled_run_count": len(schedule),
        "cost_censoring_allowed": False,
        "official": False,
    }
    cost_control_hash = sha256_json(cost_control)
    execution_body = {
        "schema_version": "rapid-public-development-candidate-v1",
        "experiment_id": config.experiment_id,
        "purpose": ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT.value,
        "official": False,
        "config_path": selected.relative_to(root).as_posix(),
        "config_file_sha256": sha256_bytes(raw),
        "config_semantic_hash": config_semantic_hash,
        "source_snapshot_hash": source["content_hash"],
        "runtime_dependencies": dependencies,
        "task_bindings": list(bindings),
        "schedule": list(schedule),
        "schedule_hash": schedule_hash,
        "cost_control": cost_control,
        "cost_control_hash": cost_control_hash,
    }
    return {
        **execution_body,
        "execution_hash": sha256_json(execution_body),
        "source_file_count": source["file_count"],
        "execution_authorized": False,
        "provider_calls_made": 0,
        "docker_calls_made": 0,
        "added_model_cost_usd": 0.0,
    }


def _candidate_body(candidate: dict[str, Any]) -> dict[str, Any]:
    omitted = {
        "execution_hash",
        "source_file_count",
        "execution_authorized",
        "provider_calls_made",
        "docker_calls_made",
        "added_model_cost_usd",
    }
    return {key: value for key, value in candidate.items() if key not in omitted}


def _plan(candidate: dict[str, Any], *, approved: bool) -> dict[str, Any]:
    body = {
        "schema_version": PLAN_SCHEMA,
        "ready": approved,
        "blockers": [] if approved else ["EXACT_APPROVAL_REQUIRED"],
        "purpose": ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT.value,
        "official": False,
        "execution_hash": candidate["execution_hash"],
        "suite_hash": candidate["config_semantic_hash"],
        "source_snapshot_hash": candidate["source_snapshot_hash"],
        "runtime_dependencies": candidate["runtime_dependencies"],
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


def _row_for_manifest(plan: dict[str, Any], manifest: RunManifest) -> dict[str, Any] | None:
    experiment = manifest.experiment
    if experiment is None:
        return None
    for row in plan.get("schedule", []):
        if isinstance(row, dict) and row.get("schedule_row_id") == experiment.schedule_row_id:
            return row
    return None


def rapid_live_plan_matches_manifest(
    *,
    plan: dict[str, Any],
    manifest: RunManifest,
    repository: str | Path = ".",
) -> bool:
    """Fail closed at the paid boundary against current config and source."""

    try:
        candidate = build_rapid_public_development_candidate(repository=repository)
        row = _row_for_manifest(plan, manifest)
        binding = next(
            item for item in candidate["task_bindings"] if item["task_id"] == manifest.task_id
        )
        experiment = manifest.experiment
        assert experiment is not None and row is not None
        expected_runtime = (
            ("v7", "phase-evidence-v12")
            if row["variant"] == "lean-harness-v1"
            else ("v2", "phase-evidence-v5")
        )
        return bool(
            plan == _plan(candidate, approved=True)
            and sha256_json(_candidate_body(candidate)) == candidate["execution_hash"]
            and experiment.purpose == ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT
            and experiment.experiment_id == EXPERIMENT_ID
            and experiment.suite_hash == candidate["config_semantic_hash"]
            and experiment.execution_hash == candidate["execution_hash"]
            and experiment.campaign_cost_control_hash == candidate["cost_control_hash"]
            and experiment.dataset_role == DatasetRole.DEVELOPMENT_VALIDATION
            and experiment.schedule_seed == SCHEDULE_SEED
            and experiment.schedule_order == row["order"]
            and experiment.repetition == row["repetition"]
            and manifest.task_id == row["task_id"] == binding["task_id"]
            and (manifest.tool_schema_version, manifest.context_policy_version) == expected_runtime
            and manifest.memory.condition == MemoryCondition.NO_MEMORY
            and manifest.memory.index_version is None
            and manifest.memory.index_hash is None
            and manifest.budget == RUNTIME_BUDGET
            and manifest.model.provider == "openai"
            and manifest.model.model_id == MODEL_ID
            and manifest.model.provider_sdk_version
            == candidate["runtime_dependencies"]["openai_sdk_version"]
            and manifest.model.max_output_tokens == 25_000
            and manifest.sandbox_backend == "docker"
            and manifest.evaluator_image_digest == binding["evaluator_image_digest"]
            and manifest.agent_image_digest == binding["evaluator_image_digest"]
            and manifest.public_spec_hash == binding["public_spec_hash"]
            and manifest.private_spec_hash == binding["private_spec_hash"]
            and manifest.base_commit == binding["base_commit"]
        )
    except (AssertionError, ContractError, KeyError, StopIteration, TypeError, ValueError):
        return False


def build_rapid_run_manifest(
    candidate: dict[str, Any],
    order: int,
    *,
    repository: str | Path = ".",
) -> RunManifest:
    root = Path(repository).resolve()
    row = next(item for item in candidate["schedule"] if item["order"] == order)
    binding = next(item for item in candidate["task_bindings"] if item["task_id"] == row["task_id"])
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
        run_id=f"run_rapid_{candidate['execution_hash'][7:19]}_{order:02d}",
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
    if row["variant"] == "lean-harness-v1":
        payload["tool_schema_version"] = "v7"
        payload["context_policy_version"] = "phase-evidence-v12"
    return RunManifest.model_validate(payload)


def _usage_cost_nanos(usage: Usage) -> int:
    cached = min(usage.cached_input_tokens, usage.input_tokens)
    cache_write = min(usage.cache_write_input_tokens, usage.input_tokens - cached)
    uncached = usage.input_tokens - cached - cache_write
    return (
        uncached * PRICES_NANOS["uncached_input"]
        + cached * PRICES_NANOS["cached_input"]
        + cache_write * PRICES_NANOS["cache_write_input"]
        + usage.output_tokens * PRICES_NANOS["output"]
    )


def _persisted_result(runner: AgentRunner, run_id: str) -> dict[str, Any] | None:
    for row in runner.state.list_runs():
        if row.get("run_id") == run_id and isinstance(row.get("result"), dict):
            return row["result"]
    return None


def _token_terminal(runner: AgentRunner, run_id: str) -> bool:
    return any(
        event.type.value == "ModelGenerationBlocked"
        and event.payload.get("reason_code") == "exact_request_budget_exceeded"
        for event in runner.state.list_events(run_id)
    )


def _row_projection(
    *,
    schedule_row: dict[str, Any],
    result: dict[str, Any] | None,
    runner: AgentRunner,
    error: Exception | None,
) -> dict[str, Any]:
    parsed = RunResult.model_validate(result) if result is not None else None
    usage = parsed.usage if parsed is not None else Usage()
    cost_nanos = _usage_cost_nanos(usage)
    if cost_nanos > PER_RUN_RESERVE_NANOS:
        raise ContractError("rapid row cost exceeds its frozen reserve")
    public_error_message = None
    if isinstance(error, ContractError):
        message = " ".join(str(error).split())
        if 0 < len(message) <= 500:
            public_error_message = message
    return {
        **schedule_row,
        "run_id": parsed.run_id if parsed is not None else None,
        "evaluator_reached": bool(parsed and parsed.evaluation_status == "completed"),
        "token_terminal": bool(parsed and _token_terminal(runner, parsed.run_id)),
        "submission_completed": bool(parsed and parsed.agent_submission_status == "completed"),
        "success_at_budget": bool(parsed and parsed.scope_compliant_success),
        "outcome_kind": (
            parsed.outcome_kind.value
            if parsed is not None and parsed.outcome_kind is not None
            else (RunOutcomeKind.INFRASTRUCTURE_ERROR.value if error is not None else None)
        ),
        "usage": usage.model_dump(mode="json"),
        "model_cost_nanos": cost_nanos,
        "runtime_result_official": bool(parsed.official) if parsed is not None else None,
        "bundle_official": False,
        "error_type": type(error).__name__ if error is not None else None,
        "error_message": public_error_message,
    }


def _bundle_tail_hash(path: Path) -> str:
    previous: str | None = None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ContractError("rapid result bundle is unreadable") from exc
    if not lines:
        raise ContractError("rapid result bundle is empty")
    for line in lines:
        try:
            sealed = json.loads(line)
        except ValueError as exc:
            raise ContractError("rapid result bundle contains invalid JSON") from exc
        if type(sealed) is not dict or type(sealed.get("content_hash")) is not str:
            raise ContractError("rapid result bundle event is invalid")
        body = {key: value for key, value in sealed.items() if key != "content_hash"}
        if body.get("previous_event_hash") != previous:
            raise ContractError("rapid result bundle chain differs")
        if sealed["content_hash"] != sha256_json(body):
            raise ContractError("rapid result bundle event hash differs")
        previous = sealed["content_hash"]
    assert previous is not None
    return previous


def _append_bundle_event(
    path: Path,
    event: dict[str, Any],
    *,
    create: bool = False,
) -> dict[str, Any]:
    if "content_hash" in event or "previous_event_hash" in event:
        raise ContractError("rapid bundle hashes are writer-owned")
    previous = None if create else _bundle_tail_hash(path)
    body = {**event, "previous_event_hash": previous}
    sealed = {**body, "content_hash": sha256_json(body)}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if create else "a", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(sealed) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return sealed


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
            raise ContractError("rapid approved plan path contains different bytes") from None
    return path


def run_rapid_public_development(
    config_path: str | Path = CONFIG_PATH,
    *,
    approve_live_cost: bool,
    approved_execution_hash: str | None,
    repository: str | Path = ".",
) -> dict[str, Any]:
    """Run one exact development batch; never upgrade its evidence to official."""

    root = Path(repository).resolve()
    candidate = build_rapid_public_development_candidate(config_path, repository=root)
    if not approve_live_cost or approved_execution_hash != candidate["execution_hash"]:
        raise ContractError("rapid live execution requires its exact hash and cost-cap approval")
    if not os.environ.get("OPENAI_API_KEY"):
        raise ContractError("rapid live execution requires OPENAI_API_KEY")
    if not DockerSandbox.available():
        raise ContractError("rapid live execution requires the local Docker daemon")
    for binding in candidate["task_bindings"]:
        if (
            DockerSandbox(binding["evaluator_image"]).image_identity()
            != binding["evaluator_image_digest"]
        ):
            raise ContractError(f"rapid evaluator image is unavailable: {binding['task_id']}")

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
        manifest = build_rapid_run_manifest(candidate, schedule_row["order"], repository=root)
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
        except Exception as exc:  # terminal evidence is projected below
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
            raise ContractError("rapid observed cost exceeds the approved hard cap")
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
    "CONFIG_PATH",
    "EXPERIMENT_ID",
    "RapidPublicDevelopmentConfig",
    "build_rapid_public_development_candidate",
    "build_rapid_run_manifest",
    "rapid_live_plan_matches_manifest",
    "run_rapid_public_development",
]
