"""Frozen, randomized experiment campaign runner."""

from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from patchloop.agent.runner import AgentRunner
from patchloop.contracts import DatasetRole, MemoryCondition
from patchloop.dataset import require_dataset_role, require_frozen_dataset
from patchloop.errors import ContractError
from patchloop.memory.store import latest_frozen_index
from patchloop.runtime import runtime_root
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_text, utc_now


class ExperimentSuite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["experiment-v1"] = "experiment-v1"
    experiment_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]+$")
    core: bool = False
    tasks: list[str] = Field(min_length=1)
    conditions: list[MemoryCondition] = Field(min_length=1)
    repetitions: int = Field(default=2, ge=1, le=20)
    model: Literal["mock", "openai"] = "mock"
    model_id: str = "gpt-5.6-terra"
    seed: int = 20260723
    live_cost_approved: bool = False
    estimated_cost_usd: float = Field(default=0, ge=0)
    cost_limit_usd: float = Field(default=150, ge=0)
    pricing_verified_at: datetime | None = None
    pricing_source_url: str | None = None
    input_price_per_million_usd: float | None = Field(default=None, gt=0)
    output_price_per_million_usd: float | None = Field(default=None, gt=0)
    retrieval_threshold: float = 0.72
    memory_token_budget: int = 2000
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_revision: str = "PIN_AT_FREEZE"
    dataset_manifest_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )

    @model_validator(mode="after")
    def validate_campaign(self) -> ExperimentSuite:
        if self.model == "openai" and not self.live_cost_approved:
            raise ValueError("live OpenAI campaign requires live_cost_approved=true")
        if self.model == "openai" and (
            self.estimated_cost_usd <= 0
            or self.pricing_verified_at is None
            or self.input_price_per_million_usd is None
            or self.output_price_per_million_usd is None
            or not (self.pricing_source_url or "").startswith(
                "https://developers.openai.com/api/docs/models/"
            )
        ):
            raise ValueError(
                "live OpenAI campaign requires a positive estimate and "
                "dated official pricing source"
            )
        if self.estimated_cost_usd > self.cost_limit_usd:
            raise ValueError("estimated campaign cost exceeds cost_limit_usd")
        if self.core:
            if len(set(self.tasks)) != 12:
                raise ValueError("core experiment requires exactly 12 unique held-out tasks")
            if set(self.conditions) != set(MemoryCondition):
                raise ValueError("core experiment requires all four memory conditions")
            if self.repetitions != 2:
                raise ValueError("core experiment requires two repetitions")
            if self.embedding_revision == "PIN_AT_FREEZE":
                raise ValueError("core experiment requires a pinned embedding revision")
            if self.dataset_manifest_hash is None:
                raise ValueError("core experiment requires a frozen dataset manifest hash")
        return self


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
    if suite.core and index_payload.get("dataset_manifest_hash") != suite.dataset_manifest_hash:
        raise ContractError(
            "frozen memory index dataset manifest hash does not match the core experiment"
        )


def evaluate_suite(path: str | Path) -> dict:
    suite = load_suite(path)
    dataset_identity = None
    dataset_manifest_path = None
    if suite.core:
        dataset, actual_dataset_hash, dataset_manifest_path = require_frozen_dataset()
        if suite.dataset_manifest_hash != actual_dataset_hash:
            raise ContractError(
                "experiment dataset manifest hash does not match the current registry"
            )
        dataset_identity = {
            "dataset_id": dataset.dataset_id,
            "manifest_hash": actual_dataset_hash,
        }

    task_rows = []
    for task in suite.tasks:
        task_path = Path(task)
        package = load_task_package(task_path.parent if task_path.is_file() else task_path)
        if suite.core:
            entry = require_dataset_role(
                task_id=package.public.task_id,
                task_version=package.public.task_version,
                public_spec_hash=package.public_spec_hash,
                allowed_roles={
                    DatasetRole.CORE_SAME_REPO,
                    DatasetRole.CORE_CROSS_REPO,
                },
                manifest_path=dataset_manifest_path,
            )
            expected_role = {
                "same-repo-heldout": DatasetRole.CORE_SAME_REPO,
                "cross-repo-heldout": DatasetRole.CORE_CROSS_REPO,
            }.get(package.public.split)
            if expected_role is None:
                raise ContractError(f"core task is not held-out: {package.public.task_id}")
            if entry.role != expected_role:
                raise ContractError(
                    f"core task role/split mismatch for {package.public.task_id}: "
                    f"{entry.role.value} != {expected_role.value}"
                )
        task_rows.append((task, package.public.task_id, package.public.split))

    if (
        any(condition != MemoryCondition.NO_MEMORY for condition in suite.conditions)
        and latest_frozen_index() is None
    ):
        raise ContractError("memory conditions require one frozen dev-train index")
    frozen_index = latest_frozen_index()
    if frozen_index is not None and any(
        condition != MemoryCondition.NO_MEMORY for condition in suite.conditions
    ):
        index_payload = json.loads(frozen_index.read_text(encoding="utf-8"))
        _validate_memory_index(index_payload, suite)
    schedule = [
        {
            "task": task,
            "task_id": task_id,
            "split": split,
            "condition": condition,
            "repetition": repetition,
        }
        for task, task_id, split in task_rows
        for condition in suite.conditions
        for repetition in range(1, suite.repetitions + 1)
    ]
    random.Random(suite.seed).shuffle(schedule)
    runner = AgentRunner()
    results = []
    actual_model_cost_usd = 0.0
    for index, item in enumerate(schedule, 1):
        if suite.model == "openai" and actual_model_cost_usd >= suite.cost_limit_usd:
            result = None
            infrastructure_error = {
                "type": "CostLimitReached",
                "message": "campaign stopped before this run at the approved cost limit",
            }
        else:
            try:
                result = runner.start(
                    item["task"],
                    model=suite.model,
                    memory_condition=item["condition"],
                    input_price_per_million_usd=suite.input_price_per_million_usd,
                    output_price_per_million_usd=suite.output_price_per_million_usd,
                    model_id=suite.model_id,
                )
                infrastructure_error = None
                actual_model_cost_usd += float(result["usage"]["model_cost_usd"])
            except Exception as exc:
                result = None
                infrastructure_error = {"type": type(exc).__name__, "message": str(exc)}
        results.append(
            {
                "order": index,
                "task_id": item["task_id"],
                "split": item["split"],
                "condition": item["condition"].value,
                "repetition": item["repetition"],
                "result": result,
                "infrastructure_error": infrastructure_error,
            }
        )
    record = {
        "schema_version": "experiment-result-v1",
        "experiment_id": suite.experiment_id,
        "suite_hash": sha256_text(canonical_json(suite.model_dump(mode="json"))),
        "created_at": utc_now().isoformat(),
        "schedule_seed": suite.seed,
        "expected_runs": len(schedule),
        "completed_runs": sum(row["result"] is not None for row in results),
        "infrastructure_errors": sum(row["infrastructure_error"] is not None for row in results),
        "actual_model_cost_usd": actual_model_cost_usd,
        "dataset": dataset_identity,
        "suite": suite.model_dump(mode="json"),
        "runs": results,
    }
    output = runtime_root() / "experiments" / f"{suite.experiment_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"experiment_id": suite.experiment_id, "path": str(output), **record}
