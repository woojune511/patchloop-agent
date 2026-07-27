"""Load and validate audited public/private task packages."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from patchloop.contracts import PrivateTask, PublicTask, TaskEnvironment, TaskPackage
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
        environment_path = root / "environment.yaml"
        environment = (
            TaskEnvironment.model_validate(_load_yaml(environment_path))
            if environment_path.is_file()
            else None
        )
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
    if private.schema_version == "task-private-v2":
        declared_paths = {artifact.path for artifact in private.hidden_artifacts}
        actual_paths = {
            path.relative_to(root).as_posix()
            for path in hidden_root.rglob("*")
            if path.is_file()
        }
        if actual_paths != declared_paths:
            missing = sorted(declared_paths - actual_paths)
            undeclared = sorted(actual_paths - declared_paths)
            raise ContractError(
                "hidden artifact inventory mismatch: "
                f"missing={missing}, undeclared={undeclared}"
            )
        for artifact in private.hidden_artifacts:
            artifact_path = ensure_within(root, artifact.path)
            actual_hash = sha256_bytes(artifact_path.read_bytes())
            if actual_hash != artifact.sha256:
                raise ContractError(
                    "hidden artifact hash mismatch: "
                    f"{artifact.path} expected {artifact.sha256}, got {actual_hash}"
                )

    private_identity = private.model_dump(mode="json")
    if private.schema_version == "task-private-v1":
        # Preserve the frozen v1 identity algorithm after adding the v2-only field.
        private_identity.pop("hidden_artifacts", None)

    try:
        return TaskPackage(
            public=public,
            private=private,
            environment=environment,
            root=str(root),
            public_spec_hash=sha256_json(public.model_dump(mode="json")),
            private_spec_hash=sha256_json(private_identity),
        )
    except ValidationError as exc:
        raise ContractError(f"task package identity validation failed: {exc}") from exc


def load_public_task(path: str | Path) -> PublicTask:
    try:
        return PublicTask.model_validate(_load_yaml(Path(path)))
    except ValidationError as exc:
        raise ContractError(f"public task validation failed: {exc}") from exc
