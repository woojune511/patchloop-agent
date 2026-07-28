"""Frozen, randomized experiment campaign runner and live-execution preflight."""

from __future__ import annotations

import hmac
import json
import os
import random
import subprocess
from datetime import UTC, datetime, timedelta
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from patchloop.agent.runner import AgentRunner, issue_live_execution_authorization
from patchloop.contracts import (
    Budget,
    DatasetRole,
    ExperimentPurpose,
    ExperimentRunContext,
    MemoryCondition,
    RunManifest,
    TaskPackage,
)
from patchloop.dataset import require_dataset_role, require_frozen_dataset
from patchloop.errors import ContractError
from patchloop.memory.store import latest_frozen_index
from patchloop.runtime import build_manifest, repository_root, runtime_root
from patchloop.sandbox import DockerSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_text, utc_now

OFFICIAL_PRICING_URL = "https://developers.openai.com/api/docs/pricing"
PRICING_MAX_AGE = timedelta(hours=72)
OFFICIAL_PRICES = {
    "input_price_per_million_usd": 2.5,
    "cached_input_price_per_million_usd": 0.25,
    "cache_write_input_price_per_million_usd": 3.125,
    "output_price_per_million_usd": 15.0,
}
DEFAULT_BUDGET = Budget()

PILOT_TASK = (
    "tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes/public.yaml"
)
PILOT_TASK_ID = "babel-strict-grouped-decimal-trailing-zeroes"
MEMORY_DEVELOPMENT_TASKS = {
    "tasks/dev-train/loguru-invalid-format-feedback/public.yaml",
    "tasks/dev-train/anyio-interrupt-runner-cleanup/public.yaml",
    "tasks/dev-train/tox-cross-section-empty-substitution/public.yaml",
    "tasks/dev-train/hf-hub-xet-endpoint-propagation/public.yaml",
    "tasks/dev-train/pdm-ignore-active-venv-resolution/public.yaml",
    "tasks/dev-train/pyfakefs-makedirs-parent-traversal/public.yaml",
}
MEMORY_DEVELOPMENT_TASK_IDS = {
    Path(path).parent.name for path in MEMORY_DEVELOPMENT_TASKS
}


def _normalized_task_path(value: str) -> str:
    return value.replace("\\", "/").removeprefix("./")


class ExperimentSuite(BaseModel):
    """Human-authored, immutable campaign configuration.

    Version 2 gives every suite an explicit purpose. Version 1 remains loadable
    for the existing offline smoke and frozen core template only.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["experiment-v1", "experiment-v2"] = "experiment-v2"
    experiment_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]+$")
    purpose: ExperimentPurpose | None = None
    core: bool | None = None
    tasks: list[str] = Field(min_length=1)
    conditions: list[MemoryCondition] = Field(min_length=1)
    repetitions: int = Field(default=2, ge=1, le=20)
    model: Literal["mock", "openai"] = "mock"
    model_id: str = "gpt-5.6-terra"
    reasoning_effort: Literal["medium"] = "medium"
    reasoning_mode: Literal["standard"] = "standard"
    service_tier: Literal["default"] = "default"
    max_output_tokens: int = Field(default=4096, ge=1)
    budget: Budget = Field(default_factory=Budget)
    seed: int = 20260723
    live_cost_approved: bool = False
    approved_execution_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    pilot_run_id: str | None = Field(
        default=None,
        pattern=r"^run_[a-zA-Z0-9_-]+$",
    )
    estimated_cost_usd: float = Field(default=0, ge=0)
    cost_limit_usd: float = Field(default=150, ge=0)
    pricing_verified_at: datetime | None = None
    pricing_source_url: str | None = None
    input_price_per_million_usd: float | None = Field(default=None, gt=0)
    cached_input_price_per_million_usd: float | None = Field(default=None, gt=0)
    cache_write_input_price_per_million_usd: float | None = Field(default=None, gt=0)
    output_price_per_million_usd: float | None = Field(default=None, gt=0)
    retrieval_threshold: float = 0.72
    memory_token_budget: int = 2000
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_revision: str = "PIN_AT_FREEZE"
    dataset_manifest_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )

    @model_validator(mode="before")
    @classmethod
    def infer_v1_purpose(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        raw = dict(value)
        if raw.get("schema_version") == "experiment-v1" or (
            "schema_version" not in raw and "core" in raw
        ):
            raw.setdefault("schema_version", "experiment-v1")
            raw.setdefault(
                "purpose",
                (
                    ExperimentPurpose.CORE.value
                    if raw.get("core", False)
                    else ExperimentPurpose.OFFLINE_SMOKE.value
                ),
            )
        return raw

    @model_validator(mode="after")
    def validate_campaign(self) -> ExperimentSuite:
        if len(set(self.tasks)) != len(self.tasks):
            raise ValueError("experiment tasks must be unique")
        if len(set(self.conditions)) != len(self.conditions):
            raise ValueError("experiment conditions must be unique")
        if self.purpose is None:
            raise ValueError("experiment-v2 requires an explicit purpose")
        if self.schema_version == "experiment-v2" and self.core is not None:
            raise ValueError("experiment-v2 uses purpose instead of the legacy core flag")
        if self.schema_version == "experiment-v1":
            legacy_purpose = (
                ExperimentPurpose.CORE if self.core else ExperimentPurpose.OFFLINE_SMOKE
            )
            if self.purpose != legacy_purpose:
                raise ValueError("experiment-v1 purpose conflicts with the legacy core flag")

        if self.purpose == ExperimentPurpose.OFFLINE_SMOKE:
            if self.schema_version == "experiment-v2" and self.model != "mock":
                raise ValueError("offline-smoke purpose requires model=mock")
            return self

        if self.seed != 20260723:
            raise ValueError("research campaigns require seed 20260723")

        if self.purpose == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT:
            if (
                [_normalized_task_path(task) for task in self.tasks] != [PILOT_TASK]
                or self.conditions != [MemoryCondition.NO_MEMORY]
                or self.repetitions != 1
            ):
                raise ValueError(
                    "development-validation live pilot requires exactly the frozen "
                    "Babel task, no_memory, and one repetition"
                )
            self._require_live_defaults(cost_limit=2)
        elif self.purpose == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY:
            if (
                {_normalized_task_path(task) for task in self.tasks}
                != MEMORY_DEVELOPMENT_TASKS
                or self.conditions != [MemoryCondition.NO_MEMORY]
                or self.repetitions != 2
            ):
                raise ValueError(
                    "memory-development no-memory campaign requires the six frozen "
                    "development tasks, no_memory, and two repetitions"
                )
            self._require_live_defaults(cost_limit=20)
        elif self.purpose == ExperimentPurpose.CORE:
            if len(set(self.tasks)) != 12:
                raise ValueError("core experiment requires exactly 12 unique held-out tasks")
            if set(self.conditions) != set(MemoryCondition):
                raise ValueError("core experiment requires all four memory conditions")
            if self.repetitions != 2:
                raise ValueError("core experiment requires two repetitions")
            if self.embedding_revision == "PIN_AT_FREEZE":
                raise ValueError("core experiment requires a pinned embedding revision")
            if self.schema_version == "experiment-v2":
                self._require_live_defaults(cost_limit=150)
        if self.dataset_manifest_hash is None:
            raise ValueError("research campaign requires a frozen dataset manifest hash")
        return self

    def _require_live_defaults(self, *, cost_limit: float) -> None:
        if (
            self.model != "openai"
            or self.model_id != "gpt-5.6-terra"
            or self.reasoning_effort != "medium"
            or self.reasoning_mode != "standard"
            or self.service_tier != "default"
        ):
            raise ValueError(
                "live research purpose requires gpt-5.6-terra, medium reasoning, "
                "standard mode, and default service tier"
            )
        if self.budget != DEFAULT_BUDGET or self.max_output_tokens != 4096:
            raise ValueError("live research purpose requires the frozen default run budget")
        if self.cost_limit_usd != cost_limit:
            raise ValueError(
                f"{self.purpose.value} requires cost_limit_usd={cost_limit:g}"
            )


def load_suite(path: str | Path) -> ExperimentSuite:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    try:
        return ExperimentSuite.model_validate(raw)
    except ValidationError as exc:
        raise ContractError(f"experiment contract validation failed: {exc}") from exc


def _validate_memory_index(index_payload: dict, suite: ExperimentSuite) -> None:
    if (
        not index_payload.get("entries")
        or index_payload["embedding"].get("implementation") != "sentence-transformers"
    ):
        raise ContractError("memory campaign requires a non-empty vectorized frozen index")
    if index_payload["embedding"].get("revision") != suite.embedding_revision:
        raise ContractError("experiment embedding revision does not match the frozen memory index")
    if (
        suite.purpose == ExperimentPurpose.CORE
        and index_payload.get("dataset_manifest_hash") != suite.dataset_manifest_hash
    ):
        raise ContractError(
            "frozen memory index dataset manifest hash does not match the core experiment"
        )


def _block(blockers: list[dict[str, str]], code: str, message: str) -> None:
    blockers.append({"code": code, "message": message})


def _campaign_journal_path(experiment_id: str) -> Path:
    return runtime_root() / "experiments" / "journals" / f"{experiment_id}.jsonl"


def _append_campaign_event(
    path: Path,
    *,
    sequence: int,
    previous_event_hash: str | None,
    event_type: str,
    payload: dict[str, Any],
) -> str:
    event = {
        "schema_version": "experiment-journal-event-v1",
        "sequence": sequence,
        "event_type": event_type,
        "recorded_at": utc_now().isoformat(),
        "previous_event_hash": previous_event_hash,
        "payload": payload,
    }
    event["event_hash"] = sha256_text(canonical_json(event))
    path.parent.mkdir(parents=True, exist_ok=True)
    exclusive_start = sequence == 1 and previous_event_hash is None
    try:
        with path.open(
            "x" if exclusive_start else "a",
            encoding="utf-8",
            newline="\n",
        ) as stream:
            stream.write(canonical_json(event) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise ContractError(
            "campaign journal already exists; refusing duplicate schedule ownership"
        ) from exc
    return str(event["event_hash"])


def _safe_error_message(error: Exception) -> str:
    message = str(error)
    for name in ("OPENAI_API_KEY",):
        secret = os.environ.get(name)
        if secret:
            message = message.replace(secret, "[REDACTED]")
    return message[:2_000]


def _git_state() -> dict[str, Any]:
    commit_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repository_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "available": commit_result.returncode == 0 and status_result.returncode == 0,
        "commit": (
            commit_result.stdout.strip() if commit_result.returncode == 0 else "uncommitted"
        ),
        "clean": status_result.returncode == 0 and not status_result.stdout.strip(),
    }


def _docker_image_state(images: list[str]) -> dict[str, Any]:
    available = DockerSandbox.available()
    rows = []
    for image in sorted(set(images)):
        identity = DockerSandbox(image).image_identity() if available else None
        rows.append(
            {
                "image": image,
                "identity": identity,
                "ready": identity is not None,
            }
        )
    return {"available": available, "images": rows}


def _openai_sdk_state() -> dict[str, Any]:
    try:
        installed_version = version("openai")
    except PackageNotFoundError:
        installed_version = None
    return {"installed": installed_version is not None, "version": installed_version}


def _pilot_qualification(run_id: str | None) -> dict[str, Any]:
    if run_id is None:
        return {"run_id": None, "qualified": False, "reason": "missing pilot_run_id"}
    try:
        from patchloop.evals.qualification import (
            calculate_source_evidence_hash,
            load_trace_qualification,
        )

        payload = load_trace_qualification(run_id, root=runtime_root())
        current_source_hash = calculate_source_evidence_hash(
            run_id,
            root=runtime_root(),
        )
    except (ContractError, FileNotFoundError) as exc:
        return {"run_id": run_id, "qualified": False, "reason": str(exc)}
    recorded_source_hash = payload["source_evidence_hash"]
    if not hmac.compare_digest(recorded_source_hash, current_source_hash):
        return {
            "run_id": run_id,
            "qualified": False,
            "qualification_hash": payload.get("qualification_hash"),
            "reason": "pilot source evidence hash mismatch",
        }
    required = (
        payload.get("purpose")
        == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT.value
        and payload.get("qualified") is True
        and payload.get("trace_integrity_passed") is True
        and payload.get("leakage_scan_passed") is True
        and payload.get("evaluation_reached") is True
    )
    return {
        "run_id": run_id,
        "qualified": required,
        "qualification_hash": payload.get("qualification_hash"),
        "source_evidence_hash": recorded_source_hash,
        "purpose": payload.get("purpose"),
        "outcome_kind": payload.get("outcome_kind"),
    }


def _suite_hash(suite: ExperimentSuite) -> str:
    return sha256_text(canonical_json(suite.model_dump(mode="json")))


def _execution_hash(
    suite: ExperimentSuite,
    *,
    dataset: dict[str, Any] | None,
    task_rows: list[dict[str, Any]],
    schedule_hash: str,
    git_state: dict[str, Any],
    docker_state: dict[str, Any],
    openai_sdk: dict[str, Any],
    pilot_qualification: dict[str, Any],
) -> str:
    payload = suite.model_dump(mode="json")
    payload.pop("live_cost_approved", None)
    payload.pop("approved_execution_hash", None)
    return sha256_text(
        canonical_json(
            {
                "schema_version": "experiment-execution-v1",
                "suite": payload,
                "dataset": dataset,
                "tasks": task_rows,
                "schedule_hash": schedule_hash,
                "git_commit": git_state.get("commit"),
                "docker_images": docker_state.get("images", []),
                "openai_sdk": openai_sdk,
                "pilot_qualification_hash": pilot_qualification.get("qualification_hash"),
            }
        )
    )


def _make_schedule(
    suite: ExperimentSuite,
    task_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    schedule = [
        {
            "task": row["task"],
            "task_id": row["task_id"],
            "task_version": row["task_version"],
            "split": row["split"],
            "dataset_role": row["dataset_role"],
            "evaluator_image_digest": row["evaluator_image_digest"],
            "condition": condition.value,
            "repetition": repetition,
        }
        for row in task_rows
        for condition in suite.conditions
        for repetition in range(1, suite.repetitions + 1)
    ]
    random.Random(suite.seed).shuffle(schedule)
    for order, row in enumerate(schedule, 1):
        row["order"] = order
        row["schedule_row_id"] = sha256_text(
            canonical_json(
                {
                    "experiment_id": suite.experiment_id,
                    "purpose": suite.purpose.value if suite.purpose else None,
                    **row,
                }
            )
        )
    return schedule, sha256_text(canonical_json(schedule))


def _expected_role_and_split(
    purpose: ExperimentPurpose,
    split: str,
) -> tuple[set[DatasetRole], DatasetRole | None]:
    if purpose == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT:
        return {DatasetRole.DEVELOPMENT_VALIDATION}, DatasetRole.DEVELOPMENT_VALIDATION
    if purpose == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY:
        return {DatasetRole.MEMORY_DEVELOPMENT}, DatasetRole.MEMORY_DEVELOPMENT
    if purpose == ExperimentPurpose.CORE:
        expected = {
            "same-repo-heldout": DatasetRole.CORE_SAME_REPO,
            "cross-repo-heldout": DatasetRole.CORE_CROSS_REPO,
        }.get(split)
        return {DatasetRole.CORE_SAME_REPO, DatasetRole.CORE_CROSS_REPO}, expected
    return set(), None


def preflight_suite(
    path: str | Path,
    *,
    approve_live_cost: bool = False,
    approved_execution_hash: str | None = None,
) -> dict[str, Any]:
    """Inspect an experiment without constructing an agent or making API calls."""

    suite = load_suite(path)
    suite_hash = _suite_hash(suite)
    blockers: list[dict[str, str]] = []
    dataset_identity: dict[str, Any] | None = None
    dataset_manifest_path: Path | None = None
    task_rows: list[dict[str, Any]] = []

    requires_dataset = suite.purpose != ExperimentPurpose.OFFLINE_SMOKE
    if requires_dataset:
        try:
            dataset, actual_dataset_hash, dataset_manifest_path = require_frozen_dataset()
            dataset_identity = {
                "dataset_id": dataset.dataset_id,
                "manifest_hash": actual_dataset_hash,
            }
            if suite.dataset_manifest_hash != actual_dataset_hash:
                _block(
                    blockers,
                    "DATASET_HASH_MISMATCH",
                    "experiment dataset manifest hash does not match the current registry",
                )
        except ContractError as exc:
            _block(blockers, "DATASET_NOT_FROZEN", str(exc))

    if not requires_dataset or dataset_manifest_path is not None:
        for task in suite.tasks:
            try:
                task_path = Path(task)
                package = load_task_package(
                    task_path.parent if task_path.is_file() else task_path
                )
                role: DatasetRole | None = None
                if requires_dataset:
                    allowed_roles, expected_role = _expected_role_and_split(
                        suite.purpose, package.public.split
                    )
                    entry = require_dataset_role(
                        task_id=package.public.task_id,
                        task_version=package.public.task_version,
                        public_spec_hash=package.public_spec_hash,
                        allowed_roles=allowed_roles,
                        manifest_path=dataset_manifest_path,
                    )
                    canonical_task_root = ensure_within(
                        repository_root(), entry.path
                    ).resolve()
                    if Path(package.root).resolve() != canonical_task_root:
                        raise ContractError(
                            "suite task path does not match the frozen dataset package: "
                            f"{package.public.task_id}"
                        )
                    if package.private_spec_hash != entry.private_spec_hash:
                        raise ContractError(
                            "suite private evaluator does not match the frozen dataset entry: "
                            f"{package.public.task_id}"
                        )
                    if package.environment is None:
                        raise ContractError(
                            "research task requires a digest-pinned evaluator environment: "
                            f"{package.public.task_id}"
                        )
                    role = entry.role
                    if expected_role is None:
                        raise ContractError(
                            f"{suite.purpose.value} task has an ineligible split: "
                            f"{package.public.task_id}@{package.public.split}"
                        )
                    if role != expected_role:
                        raise ContractError(
                            f"task role/split mismatch for {package.public.task_id}: "
                            f"{role.value} != {expected_role.value}"
                        )
                task_rows.append(
                    {
                        "task": task,
                        "task_id": package.public.task_id,
                        "task_version": package.public.task_version,
                        "split": package.public.split,
                        "dataset_role": role.value if role else None,
                        "canonical_task_path": entry.path if requires_dataset else None,
                        "public_spec_hash": package.public_spec_hash,
                        "private_spec_hash": package.private_spec_hash,
                        "base_commit": package.public.repository.base_commit,
                        "evaluator_image": (
                            package.environment.evaluator_image
                            if package.environment is not None
                            else None
                        ),
                        "evaluator_image_digest": (
                            package.environment.image_digest
                            if package.environment is not None
                            else None
                        ),
                    }
                )
            except (ContractError, OSError) as exc:
                _block(blockers, "TASK_NOT_ELIGIBLE", str(exc))

    loaded_ids = {row["task_id"] for row in task_rows}
    if len(loaded_ids) != len(task_rows):
        _block(
            blockers,
            "DUPLICATE_TASK_IDENTITY",
            "experiment task paths must resolve to unique task identities",
        )
    if (
        suite.purpose == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT
        and loaded_ids != {PILOT_TASK_ID}
    ):
        _block(
            blockers,
            "PILOT_TASK_MISMATCH",
            "live pilot must use the frozen Babel development-validation task",
        )
    if (
        suite.purpose == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY
        and loaded_ids != MEMORY_DEVELOPMENT_TASK_IDS
    ):
        _block(
            blockers,
            "DEVELOPMENT_TASK_SET_MISMATCH",
            "development campaign must use all six frozen memory-development tasks",
        )

    schedule, schedule_hash = _make_schedule(suite, task_rows)
    git_state = _git_state()
    docker_images = [
        row["evaluator_image"] for row in task_rows if row["evaluator_image"] is not None
    ]
    docker_state = (
        _docker_image_state(docker_images)
        if suite.model == "openai"
        else {"available": None, "images": []}
    )
    openai_sdk = (
        _openai_sdk_state()
        if suite.model == "openai"
        else {"installed": None, "version": None}
    )
    credential = {
        "name": "OPENAI_API_KEY",
        "present": bool(os.environ.get("OPENAI_API_KEY")),
        "custom_base_url_present": bool(
            os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE")
        ),
    }
    pilot_qualification = (
        _pilot_qualification(suite.pilot_run_id)
        if suite.purpose == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY
        else {"run_id": None, "qualified": None}
    )
    execution_hash = _execution_hash(
        suite,
        dataset=dataset_identity,
        task_rows=task_rows,
        schedule_hash=schedule_hash,
        git_state=git_state,
        docker_state=docker_state,
        openai_sdk=openai_sdk,
        pilot_qualification=pilot_qualification,
    )

    pricing = {
        "verified_at": (
            suite.pricing_verified_at.isoformat() if suite.pricing_verified_at else None
        ),
        "source_url": suite.pricing_source_url,
        **{
            field: getattr(suite, field)
            for field in OFFICIAL_PRICES
        },
        "maximum_age_hours": int(PRICING_MAX_AGE.total_seconds() / 3600),
    }
    configured_prices = [
        getattr(suite, field)
        for field in OFFICIAL_PRICES
        if getattr(suite, field) is not None
    ]
    per_run_cost_reserve = (
        (suite.budget.max_total_tokens + suite.max_output_tokens)
        * max(configured_prices)
        / 1_000_000
        if configured_prices
        else 0.0
    )
    theoretical_cost_upper_bound = len(schedule) * per_run_cost_reserve
    pricing["per_run_cost_reserve_usd"] = per_run_cost_reserve
    pricing["budget_upper_bound_usd"] = theoretical_cost_upper_bound

    if suite.model == "openai":
        if suite.schema_version != "experiment-v2":
            _block(
                blockers,
                "LIVE_SUITE_VERSION_UNSUPPORTED",
                "paid execution requires an experiment-v2 suite",
            )
        if not credential["present"]:
            _block(blockers, "OPENAI_API_KEY_MISSING", "OPENAI_API_KEY is not present")
        if credential["custom_base_url_present"]:
            _block(
                blockers,
                "CUSTOM_OPENAI_BASE_URL_FORBIDDEN",
                "OPENAI_BASE_URL and OPENAI_API_BASE must be unset for official pricing",
            )
        if not openai_sdk["installed"]:
            _block(
                blockers,
                "OPENAI_SDK_MISSING",
                "the official OpenAI Python SDK is not installed",
            )
        if not git_state["available"] or git_state["commit"] == "uncommitted":
            _block(blockers, "GIT_COMMIT_UNAVAILABLE", "Git commit identity is unavailable")
        elif not git_state["clean"]:
            _block(blockers, "GIT_WORKTREE_DIRTY", "live campaign requires a clean worktree")
        if not docker_state["available"]:
            _block(blockers, "DOCKER_UNAVAILABLE", "Docker server is unavailable")
        for image in docker_state["images"]:
            if not image["ready"]:
                _block(
                    blockers,
                    "DOCKER_IMAGE_UNAVAILABLE",
                    f"required evaluator image is unavailable: {image['image']}",
                )
            elif image["identity"] != image["image"].rsplit("@", 1)[-1]:
                _block(
                    blockers,
                    "DOCKER_IMAGE_DIGEST_MISMATCH",
                    f"required evaluator image has the wrong identity: {image['image']}",
                )

        if suite.pricing_source_url != OFFICIAL_PRICING_URL:
            _block(
                blockers,
                "PRICING_SOURCE_INVALID",
                f"pricing source must be {OFFICIAL_PRICING_URL}",
            )
        if suite.pricing_verified_at is None:
            _block(blockers, "PRICING_DATE_MISSING", "pricing verification date is missing")
        else:
            verified_at = suite.pricing_verified_at
            if verified_at.tzinfo is None:
                _block(
                    blockers,
                    "PRICING_TIMEZONE_MISSING",
                    "pricing verification date must include an explicit timezone",
                )
            else:
                age = utc_now() - verified_at.astimezone(UTC)
                if age < timedelta(0):
                    _block(
                        blockers,
                        "PRICING_DATE_FUTURE",
                        "pricing verification date is in the future",
                    )
                elif age > PRICING_MAX_AGE:
                    _block(
                        blockers,
                        "PRICING_STALE",
                        "pricing verification is older than 72 hours",
                    )
        for field, expected in OFFICIAL_PRICES.items():
            if getattr(suite, field) != expected:
                _block(
                    blockers,
                    "PRICING_RATE_MISMATCH",
                    f"{field} must equal the verified Terra rate {expected:g}",
                )
        if suite.estimated_cost_usd <= 0:
            _block(
                blockers,
                "COST_ESTIMATE_MISSING",
                "live campaign requires a positive estimated_cost_usd",
            )
        if suite.estimated_cost_usd > suite.cost_limit_usd:
            _block(
                blockers,
                "COST_ESTIMATE_EXCEEDS_LIMIT",
                "estimated campaign cost exceeds cost_limit_usd",
            )
        if theoretical_cost_upper_bound > suite.cost_limit_usd:
            _block(
                blockers,
                "TOKEN_BUDGET_EXCEEDS_COST_LIMIT",
                "the frozen token budget can exceed the campaign cost limit",
            )
        if not approve_live_cost:
            _block(
                blockers,
                "LIVE_COST_NOT_APPROVED",
                "paid execution requires the explicit --approve-live-cost invocation flag",
            )
        if approved_execution_hash != execution_hash:
            _block(
                blockers,
                "APPROVAL_HASH_MISMATCH",
                "the invocation's approved execution hash does not match this exact execution",
            )

    if (
        suite.purpose == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY
        and not pilot_qualification["qualified"]
    ):
        _block(
            blockers,
            "QUALIFIED_PILOT_REQUIRED",
            "memory-development campaign requires a qualified live pilot_run_id",
        )

    if any(condition != MemoryCondition.NO_MEMORY for condition in suite.conditions):
        frozen_index = latest_frozen_index()
        if frozen_index is None:
            _block(
                blockers,
                "FROZEN_MEMORY_INDEX_MISSING",
                "memory conditions require one frozen dev-train index",
            )
        else:
            try:
                index_payload = json.loads(frozen_index.read_text(encoding="utf-8"))
                _validate_memory_index(index_payload, suite)
            except (ContractError, OSError, json.JSONDecodeError) as exc:
                _block(blockers, "FROZEN_MEMORY_INDEX_INVALID", str(exc))

    output = runtime_root() / "experiments" / f"{suite.experiment_id}.json"
    journal = _campaign_journal_path(suite.experiment_id)
    if output.exists():
        _block(
            blockers,
            "EXPERIMENT_RESULT_EXISTS",
            f"immutable experiment result already exists: {output}",
        )
    if journal.exists():
        _block(
            blockers,
            "EXPERIMENT_JOURNAL_EXISTS",
            "an append-only campaign journal already exists; inspect or recover it "
            "instead of starting the schedule again",
        )

    return {
        "schema_version": "experiment-preflight-v1",
        "experiment_id": suite.experiment_id,
        "purpose": suite.purpose.value,
        "suite": suite.model_dump(mode="json"),
        "suite_hash": suite_hash,
        "execution_hash": execution_hash,
        "schedule_hash": schedule_hash,
        "expected_runs": len(schedule),
        "dataset": dataset_identity,
        "tasks": task_rows,
        "schedule": schedule,
        "environment": {
            "git": git_state,
            "docker": docker_state,
            "openai_sdk": openai_sdk,
            "credential": credential,
        },
        "pricing": pricing,
        "approval": {
            "suite_live_cost_approved_deprecated": suite.live_cost_approved,
            "suite_approved_execution_hash_deprecated": suite.approved_execution_hash,
            "invocation_approve_live_cost": approve_live_cost,
            "invocation_approved_execution_hash": approved_execution_hash,
            "matches_execution_hash": approved_execution_hash == execution_hash,
        },
        "pilot_qualification": pilot_qualification,
        "journal_path": str(journal),
        "blockers": blockers,
        "ready": not blockers,
    }


def _persisted_attempt_result(runner: AgentRunner, run_id: str) -> dict | None:
    for row in runner.state.list_runs():
        if row["run_id"] == run_id:
            return row.get("result")
    return None


def _assert_task_package_matches_preflight(
    package: TaskPackage,
    task_row: dict[str, Any],
) -> None:
    environment = package.environment
    actual = {
        "task_id": package.public.task_id,
        "task_version": package.public.task_version,
        "split": package.public.split,
        "public_spec_hash": package.public_spec_hash,
        "private_spec_hash": package.private_spec_hash,
        "base_commit": package.public.repository.base_commit,
        "evaluator_image": (
            environment.evaluator_image if environment is not None else None
        ),
        "evaluator_image_digest": (
            environment.image_digest if environment is not None else None
        ),
    }
    expected = {key: task_row[key] for key in actual}
    canonical_task_path = task_row.get("canonical_task_path")
    canonical_path_matches = (
        canonical_task_path is None
        or Path(package.root).resolve()
        == ensure_within(repository_root(), canonical_task_path).resolve()
    )
    if actual != expected or not canonical_path_matches:
        raise ContractError(
            "task package changed since the approved preflight: "
            f"{task_row['task_id']}"
        )


def _assert_manifest_matches_preflight(
    manifest: RunManifest,
    *,
    suite: ExperimentSuite,
    preflight: dict[str, Any],
    item: dict[str, Any],
) -> None:
    expected = {
        "task": {
            "task_id": item["task_id"],
            "task_version": item["task_version"],
            "base_commit": item["base_commit"],
            "public_spec_hash": item["public_spec_hash"],
            "private_spec_hash": item["private_spec_hash"],
        },
        "model": {
            "provider": suite.model,
            "model_id": suite.model_id,
            "provider_sdk_version": (
                preflight["environment"]["openai_sdk"]["version"]
                if suite.model == "openai"
                else None
            ),
            "reasoning_effort": suite.reasoning_effort,
            "reasoning_mode": suite.reasoning_mode,
            "service_tier": suite.service_tier,
            "max_output_tokens": suite.max_output_tokens,
            "input_price_per_million_usd": suite.input_price_per_million_usd,
            "cached_input_price_per_million_usd": (
                suite.cached_input_price_per_million_usd
            ),
            "cache_write_input_price_per_million_usd": (
                suite.cache_write_input_price_per_million_usd
            ),
            "output_price_per_million_usd": suite.output_price_per_million_usd,
        },
        "budget": suite.budget.model_dump(mode="json"),
        "sandbox": {
            "backend": "docker" if item["evaluator_image_digest"] is not None else "local",
            "agent_image_digest": item["evaluator_image_digest"],
            "evaluator_image_digest": item["evaluator_image_digest"],
        },
        "memory": {
            "condition": item["condition"],
            "max_context_tokens": suite.memory_token_budget,
        },
        "experiment": {
            "experiment_id": suite.experiment_id,
            "purpose": suite.purpose.value,
            "suite_hash": preflight["suite_hash"],
            "execution_hash": preflight["execution_hash"],
            "dataset_manifest_hash": (
                preflight["dataset"]["manifest_hash"]
                if preflight["dataset"] is not None
                else None
            ),
            "dataset_role": item["dataset_role"],
            "schedule_seed": suite.seed,
            "schedule_order": item["order"],
            "schedule_row_id": item["schedule_row_id"],
            "repetition": item["repetition"],
        },
    }
    actual = {
        "task": {
            "task_id": manifest.task_id,
            "task_version": manifest.task_version,
            "base_commit": manifest.base_commit,
            "public_spec_hash": manifest.public_spec_hash,
            "private_spec_hash": manifest.private_spec_hash,
        },
        "model": {
            key: getattr(manifest.model, key)
            for key in expected["model"]
        },
        "budget": manifest.budget.model_dump(mode="json"),
        "sandbox": {
            "backend": manifest.sandbox_backend,
            "agent_image_digest": manifest.agent_image_digest,
            "evaluator_image_digest": manifest.evaluator_image_digest,
        },
        "memory": {
            "condition": manifest.memory.condition.value,
            "max_context_tokens": manifest.memory.max_context_tokens,
        },
        "experiment": (
            manifest.experiment.model_dump(mode="json")
            if manifest.experiment is not None
            else None
        ),
    }
    if actual != expected:
        raise ContractError("run manifest does not match the approved execution plan")


def _qualify_terminal_run(run_id: str, task: str) -> dict[str, Any]:
    from patchloop.evals.qualification import qualify_run

    task_path = Path(task)
    payload = qualify_run(
        run_id,
        task_dir=task_path.parent if task_path.is_file() else task_path,
    )
    return {
        key: payload.get(key)
        for key in (
            "schema_version",
            "run_id",
            "qualified",
            "trace_integrity_passed",
            "leakage_scan_passed",
            "evaluation_reached",
            "outcome_kind",
            "purpose",
            "dataset_role",
            "memory_candidate_eligible",
            "failure_record_id",
            "qualification_hash",
        )
    }


def _persist_preflight_plan(preflight: dict[str, Any]) -> dict[str, str]:
    execution_hash = preflight["execution_hash"]
    digest = execution_hash.removeprefix("sha256:")
    output = runtime_root() / "experiments" / "plans" / f"{digest}.json"
    payload = {
        **preflight,
        "schema_version": "experiment-execution-plan-v1",
    }
    serialized = canonical_json(payload)
    plan_hash = sha256_text(serialized)
    if output.exists():
        try:
            existing = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError(f"invalid existing preflight plan: {output}") from exc
        if canonical_json(existing) != serialized:
            raise ContractError(
                "existing preflight plan conflicts with the approved execution hash"
            )
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return {"path": str(output), "artifact_hash": plan_hash}


def _assert_live_environment_unchanged(preflight: dict[str, Any]) -> None:
    expected = preflight["environment"]
    current_git = _git_state()
    current_sdk = _openai_sdk_state()
    current_docker = _docker_image_state(
        [
            row["evaluator_image"]
            for row in preflight["tasks"]
            if row["evaluator_image"] is not None
        ]
    )
    current_credential = {
        "name": "OPENAI_API_KEY",
        "present": bool(os.environ.get("OPENAI_API_KEY")),
        "custom_base_url_present": bool(
            os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE")
        ),
    }
    if (
        current_git != expected["git"]
        or current_sdk != expected["openai_sdk"]
        or current_docker != expected["docker"]
        or current_credential != expected["credential"]
    ):
        raise ContractError(
            "live execution environment changed after the approved preflight plan"
        )


def evaluate_suite(
    path: str | Path,
    *,
    approve_live_cost: bool = False,
    approved_execution_hash: str | None = None,
) -> dict:
    """Execute only after the deterministic, secret-free preflight is ready."""

    preflight = preflight_suite(
        path,
        approve_live_cost=approve_live_cost,
        approved_execution_hash=approved_execution_hash,
    )
    if not preflight["ready"]:
        messages = "; ".join(blocker["message"] for blocker in preflight["blockers"])
        raise ContractError(
            f"experiment preflight failed: {messages}",
            details={
                "execution_hash": preflight["execution_hash"],
                "blockers": preflight["blockers"],
            },
        )

    suite = ExperimentSuite.model_validate(preflight["suite"])
    if not hmac.compare_digest(_suite_hash(suite), preflight["suite_hash"]):
        raise ContractError("approved preflight suite hash mismatch")
    plan = _persist_preflight_plan(preflight)
    if suite.model == "openai":
        _assert_live_environment_unchanged(preflight)
    journal_path = Path(preflight["journal_path"])
    journal_sequence = 1
    journal_hash = _append_campaign_event(
        journal_path,
        sequence=journal_sequence,
        previous_event_hash=None,
        event_type="CampaignStarted",
        payload={
            "experiment_id": suite.experiment_id,
            "purpose": suite.purpose.value,
            "execution_hash": preflight["execution_hash"],
            "schedule_hash": preflight["schedule_hash"],
            "execution_plan_hash": plan["artifact_hash"],
        },
    )
    live_authorization = (
        issue_live_execution_authorization(
            preflight["execution_hash"],
            root=runtime_root(),
        )
        if suite.model == "openai"
        else None
    )
    runner = AgentRunner()
    results = []
    actual_model_cost_usd = 0.0
    task_packages: dict[str, Any] = {}
    per_run_cost_reserve_usd = float(
        preflight["pricing"]["per_run_cost_reserve_usd"]
    )
    qualification_required = suite.purpose in {
        ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT,
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY,
    }
    halt_reason: dict[str, str] | None = None

    for item in preflight["schedule"]:
        row_identity = {
            "order": item["order"],
            "schedule_row_id": item["schedule_row_id"],
            "task_id": item["task_id"],
            "split": item["split"],
            "dataset_role": item["dataset_role"],
            "condition": item["condition"],
            "repetition": item["repetition"],
        }
        if halt_reason is not None:
            row = {
                **row_identity,
                "attempt_status": "not_started",
                "run_id": None,
                "usage": None,
                "result": None,
                "infrastructure_error": None,
                "qualification": None,
                "qualification_error": None,
                "not_started_reason": halt_reason,
            }
            results.append(row)
            journal_sequence += 1
            journal_hash = _append_campaign_event(
                journal_path,
                sequence=journal_sequence,
                previous_event_hash=journal_hash,
                event_type="RunNotStarted",
                payload={
                    **row_identity,
                    "reason_type": halt_reason["type"],
                },
            )
            continue
        if (
            suite.model == "openai"
            and actual_model_cost_usd + per_run_cost_reserve_usd
            > suite.cost_limit_usd
        ):
            halt_reason = {
                "type": "CostReserveUnavailable",
                "message": "remaining cost limit cannot reserve one full frozen run budget",
            }
            row = {
                **row_identity,
                "attempt_status": "not_started",
                "run_id": None,
                "usage": None,
                "result": None,
                "infrastructure_error": None,
                "qualification": None,
                "qualification_error": None,
                "not_started_reason": halt_reason,
            }
            results.append(row)
            journal_sequence += 1
            journal_hash = _append_campaign_event(
                journal_path,
                sequence=journal_sequence,
                previous_event_hash=journal_hash,
                event_type="RunNotStarted",
                payload={
                    **row_identity,
                    "reason_type": halt_reason["type"],
                },
            )
            continue

        if suite.model == "openai":
            _assert_live_environment_unchanged(preflight)
        task = item["task"]
        if task not in task_packages:
            task_path = Path(task)
            task_packages[task] = load_task_package(
                task_path.parent if task_path.is_file() else task_path
            )
        package = task_packages[task]
        task_row = next(
            row for row in preflight["tasks"] if row["task_id"] == item["task_id"]
        )
        _assert_task_package_matches_preflight(package, task_row)
        evaluator_digest = item["evaluator_image_digest"]
        sandbox_backend = "docker" if evaluator_digest is not None else "local"
        experiment_context = ExperimentRunContext(
            experiment_id=suite.experiment_id,
            purpose=suite.purpose,
            suite_hash=preflight["suite_hash"],
            execution_hash=preflight["execution_hash"],
            dataset_manifest_hash=(
                preflight["dataset"]["manifest_hash"]
                if preflight["dataset"] is not None
                else None
            ),
            dataset_role=(
                DatasetRole(item["dataset_role"])
                if item["dataset_role"] is not None
                else None
            ),
            schedule_seed=suite.seed,
            schedule_order=item["order"],
            schedule_row_id=item["schedule_row_id"],
            repetition=item["repetition"],
        )
        manifest = build_manifest(
            package,
            provider=suite.model,
            model_id=suite.model_id,
            memory_condition=MemoryCondition(item["condition"]),
            sandbox_backend=sandbox_backend,
            budget=suite.budget,
            agent_image_digest=evaluator_digest,
            evaluator_image_digest=evaluator_digest,
            input_price_per_million_usd=suite.input_price_per_million_usd,
            cached_input_price_per_million_usd=(
                suite.cached_input_price_per_million_usd
            ),
            cache_write_input_price_per_million_usd=(
                suite.cache_write_input_price_per_million_usd
            ),
            output_price_per_million_usd=suite.output_price_per_million_usd,
            reasoning_effort=suite.reasoning_effort,
            reasoning_mode=suite.reasoning_mode,
            service_tier=suite.service_tier,
            max_output_tokens=suite.max_output_tokens,
            experiment_context=experiment_context,
        )
        _assert_manifest_matches_preflight(
            manifest,
            suite=suite,
            preflight=preflight,
            item={**task_row, **item},
        )
        journal_sequence += 1
        journal_hash = _append_campaign_event(
            journal_path,
            sequence=journal_sequence,
            previous_event_hash=journal_hash,
            event_type="RunStarted",
            payload={
                **row_identity,
                "run_id": manifest.run_id,
            },
        )

        try:
            result = runner.start(
                task,
                model=suite.model,
                memory_condition=MemoryCondition(item["condition"]),
                manifest=manifest,
                live_authorization=live_authorization,
            )
            infrastructure_error = None
        except Exception as exc:
            result = _persisted_attempt_result(runner, manifest.run_id)
            infrastructure_error = {
                "type": type(exc).__name__,
                "message": _safe_error_message(exc),
            }
        if (
            result is not None
            and result.get("outcome_kind") == "infrastructure_error"
        ):
            terminal_error = result.get("terminal_error") or {}
            infrastructure_error = {
                "type": terminal_error.get(
                    "type", "InfrastructureErrorOutcome"
                ),
                "message": terminal_error.get(
                    "message", "run ended with an infrastructure error"
                ),
            }
        usage = result.get("usage") if result is not None else None
        if usage is not None:
            actual_model_cost_usd += float(usage.get("model_cost_usd", 0))
        qualification = None
        qualification_error = None
        if result is not None and qualification_required:
            try:
                qualification = _qualify_terminal_run(manifest.run_id, task)
                if qualification.get("qualified") is not True:
                    qualification_error = {
                        "type": "TraceQualificationFailed",
                        "message": (
                            "terminal trace did not satisfy deterministic qualification"
                        ),
                    }
            except Exception as exc:
                qualification_error = {
                    "type": type(exc).__name__,
                    "message": _safe_error_message(exc),
                }

        results.append(
            {
                **row_identity,
                "attempt_status": "terminal",
                "run_id": manifest.run_id,
                "usage": usage,
                "result": result,
                "infrastructure_error": infrastructure_error,
                "qualification": qualification,
                "qualification_error": qualification_error,
                "not_started_reason": None,
            }
        )
        journal_sequence += 1
        journal_hash = _append_campaign_event(
            journal_path,
            sequence=journal_sequence,
            previous_event_hash=journal_hash,
            event_type="RunTerminal",
            payload={
                **row_identity,
                "run_id": manifest.run_id,
                "outcome_kind": (
                    result.get("outcome_kind") if result is not None else None
                ),
                "model_cost_usd": (
                    float(usage.get("model_cost_usd", 0)) if usage is not None else 0
                ),
                "infrastructure_error_type": (
                    infrastructure_error["type"]
                    if infrastructure_error is not None
                    else None
                ),
                "qualification_hash": (
                    qualification.get("qualification_hash")
                    if qualification is not None
                    else None
                ),
                "qualification_error_type": (
                    qualification_error["type"]
                    if qualification_error is not None
                    else None
                ),
            },
        )
        if infrastructure_error is not None:
            halt_reason = {
                "type": "InfrastructureFailureHalt",
                "message": (
                    "campaign halted after the first infrastructure error: "
                    f"{infrastructure_error['type']}"
                ),
            }
        elif qualification_error is not None:
            halt_reason = {
                "type": "QualificationFailureHalt",
                "message": (
                    "campaign halted after trace qualification failed: "
                    f"{qualification_error['type']}"
                ),
            }

    record = {
        "schema_version": "experiment-result-v2",
        "experiment_id": suite.experiment_id,
        "purpose": suite.purpose.value,
        "suite_hash": preflight["suite_hash"],
        "execution_hash": preflight["execution_hash"],
        "schedule_hash": preflight["schedule_hash"],
        "created_at": utc_now().isoformat(),
        "schedule_seed": suite.seed,
        "expected_runs": len(preflight["schedule"]),
        "completed_runs": sum(
            row["result"] is not None and row["infrastructure_error"] is None
            for row in results
        ),
        "infrastructure_errors": sum(
            row["infrastructure_error"] is not None for row in results
        ),
        "qualification_errors": sum(
            row["qualification_error"] is not None for row in results
        ),
        "not_started_runs": sum(
            row["attempt_status"] == "not_started" for row in results
        ),
        "halt_reason": halt_reason,
        "actual_model_cost_usd": actual_model_cost_usd,
        "dataset": preflight["dataset"],
        "execution_plan": plan,
        "campaign_journal": {
            "path": str(journal_path),
            "last_event_hash_before_completion": journal_hash,
        },
        "suite": suite.model_dump(mode="json"),
        "preflight": {
            key: preflight[key]
            for key in (
                "suite_hash",
                "execution_hash",
                "schedule_hash",
                "expected_runs",
            )
        },
        "runs": results,
    }
    output = runtime_root() / "experiments" / f"{suite.experiment_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded_record = json.dumps(record, indent=2, ensure_ascii=False)
    result_hash = sha256_bytes(encoded_record.encode("utf-8"))
    journal_sequence += 1
    _append_campaign_event(
        journal_path,
        sequence=journal_sequence,
        previous_event_hash=journal_hash,
        event_type="CampaignCompleted",
        payload={
            "experiment_id": suite.experiment_id,
            "result_hash": result_hash,
            "completed_runs": record["completed_runs"],
            "infrastructure_errors": record["infrastructure_errors"],
            "not_started_runs": record["not_started_runs"],
        },
    )
    temporary = output.with_suffix(".json.tmp")
    temporary.write_bytes(encoded_record.encode("utf-8"))
    os.replace(temporary, output)
    return {"experiment_id": suite.experiment_id, "path": str(output), **record}
