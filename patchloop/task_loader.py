"""Load and validate audited public/private task packages."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from patchloop.contracts import PrivateTask, PublicTask, TaskPackage
from patchloop.errors import ContractError
from patchloop.util import ensure_within, sha256_bytes, sha256_json


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ContractError(f"missing task file: {path}")
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ContractError(f"invalid YAML in {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{path.name} must contain a mapping")
    return value


def load_task_package(task_dir: str | Path) -> TaskPackage:
    root = Path(task_dir).resolve()
    try:
        public_data = _load_yaml(root / "public.yaml")
        private_data = _load_yaml(root / "private.yaml")
        public = PublicTask.model_validate(public_data)
        private = PrivateTask.model_validate(private_data)
    except ValidationError as exc:
        raise ContractError(f"task contract validation failed: {exc}") from exc

    reference_path = ensure_within(root, private.reference_patch.path)
    if not reference_path.is_file():
        raise ContractError(f"missing reference patch: {reference_path}")
    if private.reference_patch.sha256:
        actual_hash = sha256_bytes(reference_path.read_bytes())
        if actual_hash != private.reference_patch.sha256:
            raise ContractError(
                "reference patch hash mismatch: "
                f"expected {private.reference_patch.sha256}, got {actual_hash}"
            )

    hidden_root = root / "hidden"
    for check in private.hidden_checks:
        if check.working_directory != ".":
            ensure_within(root, check.working_directory)
    if private.hidden_checks and not hidden_root.is_dir():
        raise ContractError("private task declares hidden checks but hidden/ is missing")

    try:
        return TaskPackage(
            public=public,
            private=private,
            root=str(root),
            public_spec_hash=sha256_json(public.model_dump(mode="json")),
            private_spec_hash=sha256_json(private.model_dump(mode="json")),
        )
    except ValidationError as exc:
        raise ContractError(f"task package identity validation failed: {exc}") from exc


def load_public_task(path: str | Path) -> PublicTask:
    try:
        return PublicTask.model_validate(_load_yaml(Path(path)))
    except ValidationError as exc:
        raise ContractError(f"public task validation failed: {exc}") from exc
