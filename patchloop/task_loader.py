"""Load and validate audited public/private task packages."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from patchloop.contracts import (
    PrivateTask,
    PublicTask,
    TaskEnvironment,
    TaskPackage,
    task_package_spec_hashes,
)
from patchloop.errors import ContractError
from patchloop.util import (
    ensure_within,
    load_unique_yaml,
    require_yaml_scalar_type_identity,
    sha256_bytes,
)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ContractError(f"missing task file: {path}")
    try:
        value = load_unique_yaml(path.read_text(encoding="utf-8"))
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
        require_yaml_scalar_type_identity(
            public_data,
            public.model_dump(mode="python"),
            source="public.yaml",
        )
        require_yaml_scalar_type_identity(
            private_data,
            private.model_dump(mode="python"),
            source="private.yaml",
        )
        environment_path = root / "environment.yaml"
        environment = None
        if environment_path.is_file():
            environment_data = _load_yaml(environment_path)
            environment = TaskEnvironment.model_validate(environment_data)
            require_yaml_scalar_type_identity(
                environment_data,
                environment.model_dump(mode="python"),
                source="environment.yaml",
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
            path.relative_to(root).as_posix() for path in hidden_root.rglob("*") if path.is_file()
        }
        if actual_paths != declared_paths:
            missing = sorted(declared_paths - actual_paths)
            undeclared = sorted(actual_paths - declared_paths)
            raise ContractError(
                f"hidden artifact inventory mismatch: missing={missing}, undeclared={undeclared}"
            )
        for artifact in private.hidden_artifacts:
            artifact_path = ensure_within(root, artifact.path)
            actual_hash = sha256_bytes(artifact_path.read_bytes())
            if actual_hash != artifact.sha256:
                raise ContractError(
                    "hidden artifact hash mismatch: "
                    f"{artifact.path} expected {artifact.sha256}, got {actual_hash}"
                )

    public_spec_hash, private_spec_hash = task_package_spec_hashes(public, private)

    try:
        return TaskPackage(
            public=public,
            private=private,
            environment=environment,
            root=str(root),
            public_spec_hash=public_spec_hash,
            private_spec_hash=private_spec_hash,
        )
    except ValidationError as exc:
        raise ContractError(f"task package identity validation failed: {exc}") from exc


def load_public_task(path: str | Path) -> PublicTask:
    try:
        raw = _load_yaml(Path(path))
        public = PublicTask.model_validate(raw)
        require_yaml_scalar_type_identity(
            raw,
            public.model_dump(mode="python"),
            source=Path(path).name,
        )
        return public
    except ValidationError as exc:
        raise ContractError(f"public task validation failed: {exc}") from exc
