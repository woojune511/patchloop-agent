"""Manifest-driven dataset admission, completeness, and leakage audit."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import yaml
from pydantic import ValidationError

from patchloop.contracts import (
    RESEARCH_DATASET_ROLES,
    DatasetManifest,
    DatasetRole,
    DatasetTaskEntry,
)
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package
from patchloop.util import ensure_within, sha256_bytes, sha256_json

DEFAULT_MANIFEST = Path("data/dataset-manifest.yaml")

ROLE_TO_PUBLIC_SPLIT = {
    DatasetRole.MEMORY_DEVELOPMENT: "dev-train",
    DatasetRole.DEVELOPMENT_VALIDATION: "dev-validation",
    DatasetRole.CORE_SAME_REPO: "same-repo-heldout",
    DatasetRole.CORE_CROSS_REPO: "cross-repo-heldout",
}


def load_dataset_manifest(
    path: str | Path | None = None,
) -> tuple[DatasetManifest, str, Path]:
    manifest_path = Path(path) if path else repository_root() / DEFAULT_MANIFEST
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_file():
        raise ContractError(f"missing dataset manifest: {manifest_path}")
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ContractError(f"invalid dataset manifest YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ContractError("dataset manifest must contain a mapping")
    try:
        manifest = DatasetManifest.model_validate(raw)
    except ValidationError as exc:
        raise ContractError(f"dataset manifest validation failed: {exc}") from exc
    manifest_hash = sha256_json(manifest.model_dump(mode="json"))
    return manifest, manifest_hash, manifest_path


def find_dataset_entry(
    *,
    task_id: str,
    task_version: int,
    public_spec_hash: str | None = None,
    manifest_path: str | Path | None = None,
) -> DatasetTaskEntry:
    manifest, _, _ = load_dataset_manifest(manifest_path)
    matches = [
        entry
        for entry in manifest.tasks
        if (entry.task_id, entry.task_version) == (task_id, task_version)
    ]
    if len(matches) != 1:
        raise ContractError(
            f"task is not uniquely registered in the dataset manifest: {task_id}@{task_version}"
        )
    entry = matches[0]
    if public_spec_hash is not None and entry.public_spec_hash != public_spec_hash:
        raise ContractError(
            f"dataset public spec hash mismatch for {task_id}: "
            f"expected {entry.public_spec_hash}, got {public_spec_hash}"
        )
    return entry


def require_dataset_role(
    *,
    task_id: str,
    task_version: int,
    public_spec_hash: str,
    allowed_roles: set[DatasetRole],
    manifest_path: str | Path | None = None,
) -> DatasetTaskEntry:
    entry = find_dataset_entry(
        task_id=task_id,
        task_version=task_version,
        public_spec_hash=public_spec_hash,
        manifest_path=manifest_path,
    )
    if entry.role not in allowed_roles:
        allowed = ", ".join(sorted(role.value for role in allowed_roles))
        raise ContractError(
            f"dataset role {entry.role.value} is not eligible; required one of: {allowed}"
        )
    return entry


def _repository_for(entry: DatasetTaskEntry) -> str | None:
    repository = entry.source.upstream_repository
    return repository.lower() if repository else None


def _same_repo_pairing_violations(
    development_counts: Counter[str], same_repo_counts: Counter[str]
) -> list[str]:
    violations = []
    missing = sorted(set(development_counts) - set(same_repo_counts))
    unexpected = sorted(set(same_repo_counts) - set(development_counts))
    duplicated_development = sorted(
        repository for repository, count in development_counts.items() if count != 1
    )
    duplicated_same_repo = sorted(
        repository for repository, count in same_repo_counts.items() if count != 1
    )
    if missing:
        violations.append(
            "same-repo lane is missing development repositories: " + ", ".join(missing)
        )
    if unexpected:
        violations.append(
            "same-repo lane has repositories outside development: "
            + ", ".join(unexpected)
        )
    if duplicated_development:
        violations.append(
            "memory-development lane is not one task per repository: "
            + ", ".join(duplicated_development)
        )
    if duplicated_same_repo:
        violations.append(
            "same-repo lane is not one task per repository: "
            + ", ".join(duplicated_same_repo)
        )
    return violations


def audit_dataset(
    tasks_root: str | Path | None = None,
    *,
    manifest_path: str | Path | None = None,
) -> dict:
    repo_root = repository_root()
    if tasks_root is not None:
        root = Path(tasks_root).resolve()
        repo_root = root.parent if root.name == "tasks" else root
    selected_manifest = (
        Path(manifest_path).resolve() if manifest_path is not None else repo_root / DEFAULT_MANIFEST
    )
    try:
        manifest, manifest_hash, resolved_manifest = load_dataset_manifest(selected_manifest)
    except ContractError as exc:
        return {
            "complete": False,
            "calibration_ready": False,
            "research_ready": False,
            "stress_ready": False,
            "errors": [{"path": str(selected_manifest), "error": str(exc)}],
        }

    errors: list[dict[str, str]] = []
    valid_entries: list[DatasetTaskEntry] = []
    for entry in manifest.tasks:
        try:
            task_path = ensure_within(repo_root, entry.path)
            package = load_task_package(task_path)
            observed_identity = (package.public.task_id, package.public.task_version)
            expected_identity = (entry.task_id, entry.task_version)
            if observed_identity != expected_identity:
                raise ContractError(
                    f"registry/package identity mismatch: {expected_identity} != "
                    f"{observed_identity}"
                )
            if package.public_spec_hash != entry.public_spec_hash:
                raise ContractError(
                    "public spec hash mismatch: "
                    f"{entry.public_spec_hash} != {package.public_spec_hash}"
                )
            if package.private_spec_hash != entry.private_spec_hash:
                raise ContractError(
                    "private spec hash mismatch: "
                    f"{entry.private_spec_hash} != {package.private_spec_hash}"
                )
            expected_split = ROLE_TO_PUBLIC_SPLIT.get(entry.role)
            if expected_split is not None and package.public.split != expected_split:
                raise ContractError(
                    f"dataset role {entry.role.value} requires public split {expected_split}, "
                    f"got {package.public.split}"
                )
            if entry.admission_evidence is not None:
                evidence_path = ensure_within(repo_root, entry.admission_evidence.path)
                if not evidence_path.is_file():
                    raise ContractError(f"missing admission evidence: {evidence_path}")
                actual_hash = sha256_bytes(evidence_path.read_bytes())
                if actual_hash != entry.admission_evidence.sha256:
                    raise ContractError(
                        "admission evidence hash mismatch: "
                        f"{entry.admission_evidence.sha256} != {actual_hash}"
                    )
            valid_entries.append(entry)
        except ContractError as exc:
            errors.append({"path": entry.path, "task_id": entry.task_id, "error": str(exc)})

    registered_task_paths = {entry.path for entry in manifest.tasks}
    discovered_task_paths = {
        public_path.parent.relative_to(repo_root).as_posix()
        for public_path in (repo_root / "tasks").rglob("public.yaml")
    }
    unregistered_task_paths = sorted(discovered_task_paths - registered_task_paths)

    role_counts = Counter(entry.role.value for entry in valid_entries)
    research = [entry for entry in valid_entries if entry.role in RESEARCH_DATASET_ROLES]
    research_counts = Counter(entry.role for entry in research)
    missing = {
        role.value: target - research_counts.get(role, 0)
        for role, target in manifest.targets.items()
        if research_counts.get(role, 0) < target
    }

    development_repository_counts = Counter(
        repository
        for entry in research
        if entry.role == DatasetRole.MEMORY_DEVELOPMENT
        if (repository := _repository_for(entry)) is not None
    )
    same_repository_counts = Counter(
        repository
        for entry in research
        if entry.role == DatasetRole.CORE_SAME_REPO
        if (repository := _repository_for(entry)) is not None
    )
    development_repositories = set(development_repository_counts)
    same_repositories = set(same_repository_counts)
    cross_repositories = {
        repository
        for entry in research
        if entry.role == DatasetRole.CORE_CROSS_REPO
        if (repository := _repository_for(entry)) is not None
    }

    if (
        manifest.policy.same_repo_must_overlap_development
        and same_repositories
        and not same_repositories.issubset(development_repositories)
    ):
        unexpected = sorted(same_repositories - development_repositories)
        errors.append(
            {
                "path": str(resolved_manifest),
                "error": "same-repo tasks lack development repository coverage: "
                + ", ".join(unexpected),
            }
        )
    pairing_lane_filled = (
        research_counts.get(DatasetRole.MEMORY_DEVELOPMENT, 0)
        == manifest.targets[DatasetRole.MEMORY_DEVELOPMENT]
        and research_counts.get(DatasetRole.CORE_SAME_REPO, 0)
        == manifest.targets[DatasetRole.CORE_SAME_REPO]
    )
    if (
        manifest.policy.same_repo_requires_one_to_one_development_coverage
        and pairing_lane_filled
    ):
        errors.extend(
            {
                "path": str(resolved_manifest),
                "error": violation,
            }
            for violation in _same_repo_pairing_violations(
                development_repository_counts, same_repository_counts
            )
        )
    if manifest.policy.cross_repo_must_be_disjoint and cross_repositories.intersection(
        development_repositories
    ):
        overlap = sorted(cross_repositories.intersection(development_repositories))
        errors.append(
            {
                "path": str(resolved_manifest),
                "error": "cross-repo tasks overlap development repositories: " + ", ".join(overlap),
            }
        )

    admitted_repositories = {
        repository for entry in research if (repository := _repository_for(entry)) is not None
    }
    repository_policy_passed = (
        not research or len(admitted_repositories) >= manifest.policy.minimum_repositories
    )
    if manifest.status == "frozen" and research and not repository_policy_passed:
        errors.append(
            {
                "path": str(resolved_manifest),
                "error": "research dataset has fewer repositories than policy minimum",
            }
        )

    research_task_ids = {entry.task_id for entry in research}
    stress_errors = []
    for lane in manifest.stress_lanes:
        unknown = sorted(set(lane.task_ids) - research_task_ids)
        if unknown:
            stress_errors.append(
                f"{lane.lane_id} references non-research tasks: {', '.join(unknown)}"
            )
        if manifest.status == "frozen" and len(lane.task_ids) != lane.sentinel_count:
            stress_errors.append(
                f"{lane.lane_id} has {len(lane.task_ids)}/{lane.sentinel_count} sentinels"
            )
    errors.extend({"path": str(resolved_manifest), "error": error} for error in stress_errors)

    exact_research_counts = all(
        research_counts.get(role, 0) == target for role, target in manifest.targets.items()
    )
    calibration_count = role_counts.get(DatasetRole.CALIBRATION.value, 0)
    calibration_ready = calibration_count == manifest.calibration_target and not any(
        error["path"]
        in {entry.path for entry in manifest.tasks if entry.role == DatasetRole.CALIBRATION}
        for error in errors
    )
    research_ready = (
        manifest.status == "frozen"
        and exact_research_counts
        and repository_policy_passed
        and not errors
    )
    stress_ready = (
        manifest.status == "frozen"
        and bool(manifest.stress_lanes)
        and not stress_errors
        and all(len(lane.task_ids) == lane.sentinel_count for lane in manifest.stress_lanes)
    )
    return {
        "complete": calibration_ready and research_ready and stress_ready,
        "dataset_id": manifest.dataset_id,
        "dataset_status": manifest.status,
        "manifest_hash": manifest_hash,
        "manifest_path": str(resolved_manifest),
        "calibration_ready": calibration_ready,
        "research_ready": research_ready,
        "stress_ready": stress_ready,
        "task_count": len(valid_entries),
        "calibration_task_count": calibration_count,
        "research_task_count": len(research),
        "candidate_package_count": len(unregistered_task_paths),
        "unregistered_task_paths": unregistered_task_paths,
        "role_counts": dict(role_counts),
        "targets": {role.value: target for role, target in manifest.targets.items()},
        "missing": missing,
        "repositories": sorted(admitted_repositories),
        "repository_policy_passed": repository_policy_passed,
        "source_counts": dict(Counter(entry.source.kind.value for entry in valid_entries)),
        "difficulty_counts": dict(Counter(entry.difficulty.tier.value for entry in valid_entries)),
        "workflow_counts": dict(
            Counter(entry.source.workflow_type.value for entry in valid_entries)
        ),
        "headline_excluded_task_ids": sorted(
            entry.task_id for entry in valid_entries if entry.role == DatasetRole.CALIBRATION
        ),
        "stress_lanes": [
            {
                "lane_id": lane.lane_id,
                "sentinel_count": lane.sentinel_count,
                "selected": len(lane.task_ids),
                "scenarios": lane.scenarios,
            }
            for lane in manifest.stress_lanes
        ],
        "errors": errors,
    }
