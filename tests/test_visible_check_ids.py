"""Each required command must retain a distinct identity at task admission."""

from __future__ import annotations

import pytest
import yaml
from pydantic import ValidationError

from patchloop.contracts import PublicTask
from patchloop.errors import ContractError
from patchloop.repair import RepairTask
from patchloop.task_loader import load_public_task


def public_task(version: str, *, duplicate: bool) -> dict:
    task = {
        "schema_version": version,
        "task_id": "distinct-required-checks",
        "split": "dev-train",
        "repository": {"url": "https://example.invalid/repo.git", "base_commit": "base"},
        "issue": {"title": "Required checks", "description": "Run both registered commands."},
        "constraints": {"allowed_paths": ["src/**"]},
        "visible_checks": [
            {"id": "required-check", "command": ["python", "-c", "raise SystemExit(1)"]},
            {
                "id": "required-check" if duplicate else "other-required-check",
                "command": ["python", "-c", "raise SystemExit(0)"],
            },
        ],
    }
    if version == "task-public-v2":
        task["probe_profiles"] = [{"id": "public-python"}]
    return task


@pytest.mark.parametrize("version", ["task-public-v1", "task-public-v2"])
def test_duplicate_required_check_ids_are_rejected_by_public_task_loader(tmp_path, version):
    path = tmp_path / "public.yaml"
    path.write_text(yaml.safe_dump(public_task(version, duplicate=True)), encoding="utf-8")
    with pytest.raises(ContractError, match="visible check IDs must be unique"):
        load_public_task(path)


@pytest.mark.parametrize("version", ["task-public-v1", "task-public-v2"])
def test_distinct_required_check_ids_preserve_both_commands(tmp_path, version):
    raw = public_task(version, duplicate=False)
    path = tmp_path / "public.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    task = load_public_task(path)
    assert [check.id for check in task.visible_checks] == [
        "required-check", "other-required-check",
    ]
    assert [check.command for check in task.visible_checks] == [
        check["command"] for check in raw["visible_checks"]
    ]


@pytest.mark.parametrize("version", ["task-public-v1", "task-public-v2"])
def test_empty_visible_checks_remain_supported_for_development_tasks(version):
    raw = public_task(version, duplicate=False)
    raw["visible_checks"] = []
    assert PublicTask.model_validate(raw).visible_checks == []


def test_repair_duplicate_check_rejection_retains_its_contract():
    raw = public_task("repair-task-v1", duplicate=True)
    raw["split"] = "repair"
    with pytest.raises(ValidationError, match="repair check IDs must be unique"):
        RepairTask.model_validate(raw)
