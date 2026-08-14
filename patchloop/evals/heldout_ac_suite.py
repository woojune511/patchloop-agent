"""Metadata-only loaders for the execution-closed held-out A/C suite."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_contracts import HeldoutACSuite, HeldoutACSuitePlan
from patchloop.runtime import repository_root
from patchloop.util import (
    canonical_json,
    load_unique_yaml,
    sha256_bytes,
    sha256_text,
)


def _load_heldout_ac_yaml(path: Path, *, label: str) -> tuple[dict[str, Any], bytes]:
    """Read one metadata-only held-out contract without opening task packages."""

    try:
        raw_bytes = path.read_bytes()
        raw = load_unique_yaml(raw_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ContractError(f"{label} YAML validation failed: {exc}") from exc
    if not isinstance(raw, dict):
        raise ContractError(f"{label} must be a YAML mapping")
    return raw, raw_bytes


def _heldout_ac_self_hash(payload: dict[str, Any]) -> str:
    return sha256_text(
        canonical_json({key: value for key, value in payload.items() if key != "content_hash"})
    )


def _heldout_ac_repository_root(repository: str | Path | None) -> Path:
    return Path(repository).resolve() if repository is not None else repository_root().resolve()


def load_heldout_ac_suite(
    path: str | Path,
    *,
    repository: str | Path | None = None,
) -> HeldoutACSuite:
    """Validate the execution-closed 48-row suite using metadata only."""

    root = _heldout_ac_repository_root(repository)
    suite_path = Path(path)
    if not suite_path.is_absolute():
        suite_path = root / suite_path
    raw, _ = _load_heldout_ac_yaml(suite_path, label="held-out A/C suite")
    try:
        suite = HeldoutACSuite.model_validate(raw)
    except ValidationError as exc:
        raise ContractError(f"held-out A/C suite contract validation failed: {exc}") from exc
    if suite.content_hash != _heldout_ac_self_hash(raw):
        raise ContractError("held-out A/C suite content_hash does not match canonical content")

    from patchloop.evals.heldout_ac_preregistration import (
        PREREGISTRATION_PATH,
        load_heldout_ac_preregistration,
    )

    prereg_summary = load_heldout_ac_preregistration(repository=root)
    prereg_path = root / PREREGISTRATION_PATH
    prereg_raw, prereg_bytes = _load_heldout_ac_yaml(
        prereg_path,
        label="held-out A/C preregistration",
    )
    binding = suite.preregistration
    if (
        binding.path != PREREGISTRATION_PATH.as_posix()
        or binding.preregistration_id != prereg_summary["preregistration_id"]
        or binding.content_hash != prereg_summary["content_hash"]
        or binding.file_bytes != len(prereg_bytes)
        or binding.file_sha256 != sha256_bytes(prereg_bytes)
    ):
        raise ContractError("held-out A/C suite preregistration binding drifted")

    section_hashes = binding.section_hashes.model_dump(mode="json")
    for section_name, expected_hash in section_hashes.items():
        section = prereg_raw.get(section_name)
        if (
            not isinstance(section, (dict, list))
            or sha256_text(canonical_json(section)) != expected_hash
        ):
            raise ContractError(
                f"held-out A/C preregistration {section_name} section binding drifted"
            )

    prereg_dataset = prereg_raw["dataset"]
    prereg_manifest = prereg_dataset["manifest"]
    expected_dataset = {
        "manifest_path": prereg_manifest["path"],
        "manifest_file_bytes": prereg_manifest["file_bytes"],
        "manifest_file_sha256": prereg_manifest["file_sha256"],
        "dataset_id": prereg_manifest["dataset_id"],
        "status": prereg_manifest["status"],
        "selection_rule": prereg_dataset["task_selection_rule"],
    }
    if suite.dataset.model_dump(mode="json") != expected_dataset:
        raise ContractError("held-out A/C suite dataset binding differs from preregistration")
    expected_tasks = [
        {"task_id": task["task_id"], "role": task["role"]} for task in prereg_dataset["tasks"]
    ]
    if [task.model_dump(mode="json") for task in suite.tasks] != expected_tasks:
        raise ContractError("held-out A/C suite task projection differs from preregistration")
    if suite.treatment.model_dump(mode="json") != prereg_raw["treatment"]:
        raise ContractError("held-out A/C suite treatment differs from preregistration")
    expected_schedule_binding = {
        key: prereg_raw["schedule_design"][key] for key in type(suite.schedule_binding).model_fields
    }
    if suite.schedule_binding.model_dump(mode="json") != expected_schedule_binding:
        raise ContractError("held-out A/C suite schedule binding differs from preregistration")
    if [row.model_dump(mode="json") for row in suite.schedule] != prereg_raw["schedule"]:
        raise ContractError("held-out A/C suite schedule differs from preregistration")
    if suite.runtime.model_dump(mode="json") != prereg_raw["runtime"]:
        raise ContractError("held-out A/C suite runtime differs from preregistration")
    if suite.cost.model_dump(mode="json") != prereg_raw["cost"]:
        raise ContractError("held-out A/C suite cost differs from preregistration")
    return suite


def load_heldout_ac_suite_plan(
    path: str | Path,
    *,
    repository: str | Path | None = None,
) -> tuple[HeldoutACSuitePlan, HeldoutACSuite]:
    """Validate the offline-only plan and its exact suite file binding."""

    root = _heldout_ac_repository_root(repository)
    plan_path = Path(path)
    if not plan_path.is_absolute():
        plan_path = root / plan_path
    raw, _ = _load_heldout_ac_yaml(plan_path, label="held-out A/C suite plan")
    try:
        plan = HeldoutACSuitePlan.model_validate(raw)
    except ValidationError as exc:
        raise ContractError(f"held-out A/C suite plan validation failed: {exc}") from exc
    if plan.content_hash != _heldout_ac_self_hash(raw):
        raise ContractError("held-out A/C suite plan content_hash does not match canonical content")

    suite_path = root / plan.suite.path
    suite_bytes = suite_path.read_bytes()
    suite = load_heldout_ac_suite(suite_path, repository=root)
    if (
        plan.suite.suite_id != suite.suite_id
        or plan.suite.content_hash != suite.content_hash
        or plan.suite.file_bytes != len(suite_bytes)
        or plan.suite.file_sha256 != sha256_bytes(suite_bytes)
        or plan.preregistration != suite.preregistration
    ):
        raise ContractError("held-out A/C suite plan file binding drifted")
    return plan, suite


__all__ = ["load_heldout_ac_suite", "load_heldout_ac_suite_plan"]
