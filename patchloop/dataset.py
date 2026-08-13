"""Manifest-driven dataset admission, completeness, and leakage audit."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import yaml
from pydantic import ValidationError

from patchloop.contracts import (
    RESEARCH_DATASET_ROLES,
    DatasetManifest,
    DatasetRole,
    DatasetTaskEntry,
    PublicTask,
    StressLane,
)
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package
from patchloop.util import (
    ensure_within,
    load_unique_yaml,
    require_yaml_scalar_type_identity,
    sha256_bytes,
    sha256_json,
)

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
        raw = load_unique_yaml(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ContractError(f"invalid dataset manifest YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ContractError("dataset manifest must contain a mapping")
    try:
        manifest = DatasetManifest.model_validate(raw)
    except ValidationError as exc:
        raise ContractError(f"dataset manifest validation failed: {exc}") from exc
    require_yaml_scalar_type_identity(
        raw,
        manifest.model_dump(mode="python"),
        source=manifest_path.name,
    )
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


def _github_repository_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https" or parsed.netloc.lower() != "github.com":
        return None
    path = parsed.path.strip("/")
    if path.lower().endswith(".git"):
        path = path[:-4]
    parts = path.split("/")
    if len(parts) != 2 or not all(parts):
        return None
    return "/".join(parts).lower()


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
            "same-repo lane has repositories outside development: " + ", ".join(unexpected)
        )
    if duplicated_development:
        violations.append(
            "memory-development lane is not one task per repository: "
            + ", ".join(duplicated_development)
        )
    if duplicated_same_repo:
        violations.append(
            "same-repo lane is not one task per repository: " + ", ".join(duplicated_same_repo)
        )
    return violations


def select_stress_sentinels(
    entries: list[DatasetTaskEntry],
    public_tasks: dict[str, PublicTask],
) -> dict[str, str]:
    """Select the preregistered stress panel using public contracts only."""

    eligible = [
        entry
        for entry in entries
        if entry.role
        in {
            DatasetRole.CORE_SAME_REPO,
            DatasetRole.CORE_CROSS_REPO,
        }
        and entry.task_id in public_tasks
    ]
    if len(eligible) < 3:
        raise ContractError("stress selection requires at least three valid held-out tasks")

    remaining = {entry.task_id: public_tasks[entry.task_id] for entry in eligible}
    wide_change = min(
        remaining.values(),
        key=lambda task: (-task.constraints.max_changed_files, task.task_id),
    )
    remaining.pop(wide_change.task_id)

    narrow_mutation = min(
        remaining.values(),
        key=lambda task: (
            task.constraints.max_changed_files,
            task.constraints.max_diff_lines,
            task.task_id,
        ),
    )
    remaining.pop(narrow_mutation.task_id)

    missing_checks = sorted(task.task_id for task in remaining.values() if not task.visible_checks)
    if missing_checks:
        raise ContractError(
            "stress timeout selection requires registered visible checks: "
            + ", ".join(missing_checks)
        )
    longest_check = min(
        remaining.values(),
        key=lambda task: (
            -max(check.timeout_seconds for check in task.visible_checks),
            task.task_id,
        ),
    )
    return {
        "wide-change-surface": wide_change.task_id,
        "narrow-mutation-surface": narrow_mutation.task_id,
        "longest-visible-check": longest_check.task_id,
    }


def expand_stress_schedule(lane: StressLane) -> list[dict[str, object]]:
    """Expand and deterministically order the frozen stress matrix."""

    if lane.schedule is None:
        return []
    rows: list[dict[str, object]] = []
    for task_id in lane.task_ids:
        for case in lane.schedule.cases:
            for persistent_state in case.persistent_state_modes:
                for repetition in range(1, case.repetitions + 1):
                    rows.append(
                        {
                            "schedule_id": lane.schedule.schedule_id,
                            "task_id": task_id,
                            "fault": case.fault,
                            "trigger": case.trigger,
                            "persistent_state": persistent_state,
                            "repetition": repetition,
                            "memory_condition": lane.schedule.memory_condition,
                            "baseline_source": lane.schedule.baseline_source,
                        }
                    )
    rows.sort(
        key=lambda row: sha256_bytes(
            (
                f"{lane.schedule.seed}|{row['task_id']}|{row['fault']}|"
                f"{row['persistent_state']}|{row['repetition']}"
            ).encode()
        )
    )
    return [{"schedule_index": index, **row} for index, row in enumerate(rows, 1)]


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
            "stress_plan_ready": False,
            "freeze_eligible": False,
            "freeze_blockers": ["dataset manifest contract validation failed"],
            "errors": [{"path": str(selected_manifest), "error": str(exc)}],
        }

    errors: list[dict[str, str]] = []
    valid_entries: list[DatasetTaskEntry] = []
    public_tasks: dict[str, PublicTask] = {}
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
            if entry.role in RESEARCH_DATASET_ROLES:
                source_repository = _repository_for(entry)
                if source_repository is None:
                    raise ContractError("research source repository is missing")
                package_repository = _github_repository_from_url(package.public.repository.url)
                if package_repository != source_repository:
                    raise ContractError(
                        "source repository mismatch: "
                        f"{entry.source.upstream_repository} != "
                        f"{package.public.repository.url}"
                    )
                if entry.source.upstream_base_commit != package.public.repository.base_commit:
                    raise ContractError(
                        "source base commit mismatch: "
                        f"{entry.source.upstream_base_commit} != "
                        f"{package.public.repository.base_commit}"
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
            public_tasks[entry.task_id] = package.public
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
    if manifest.policy.same_repo_requires_one_to_one_development_coverage and pairing_lane_filled:
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
    heldout_task_ids = {
        entry.task_id
        for entry in research
        if entry.role
        in {
            DatasetRole.CORE_SAME_REPO,
            DatasetRole.CORE_CROSS_REPO,
        }
    }
    stress_errors: list[str] = []
    for lane in manifest.stress_lanes:
        unknown = sorted(set(lane.task_ids) - research_task_ids)
        if unknown:
            stress_errors.append(
                f"{lane.lane_id} references non-research tasks: {', '.join(unknown)}"
            )
        non_heldout = sorted(set(lane.task_ids) - heldout_task_ids - set(unknown))
        if non_heldout:
            stress_errors.append(
                f"{lane.lane_id} references non-held-out research tasks: " + ", ".join(non_heldout)
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
    expected_stress_selection: dict[str, str] = {}
    selection_error = None
    try:
        expected_stress_selection = select_stress_sentinels(research, public_tasks)
    except ContractError as exc:
        selection_error = str(exc)

    freeze_blockers: list[str] = []
    if not calibration_ready:
        freeze_blockers.append(
            f"calibration lane has {calibration_count}/{manifest.calibration_target} valid tasks"
        )
    if not exact_research_counts:
        freeze_blockers.append("research role targets are incomplete")
    if not repository_policy_passed:
        freeze_blockers.append("research repository policy is not satisfied")
    if errors:
        freeze_blockers.append("dataset audit has contract errors")
    if selection_error is not None:
        freeze_blockers.append(selection_error)
    if len(manifest.stress_lanes) != 1:
        freeze_blockers.append("dataset requires exactly one stress lane")

    stress_plan_ready = False
    expected_stress_runs = 0
    stress_schedule_hash = None
    if len(manifest.stress_lanes) == 1:
        lane = manifest.stress_lanes[0]
        selected_ids = list(expected_stress_selection.values())
        if lane.sentinel_count != 3 or len(lane.task_ids) != 3:
            freeze_blockers.append(f"{lane.lane_id} has {len(lane.task_ids)}/3 selected sentinels")
        if lane.task_ids != selected_ids:
            freeze_blockers.append(
                f"{lane.lane_id} does not match public-contract-structure-v1 selection"
            )
        if lane.selection_policy != "public-contract-structure-v1":
            freeze_blockers.append(f"{lane.lane_id} is missing the frozen selection policy")
        if set(lane.selection_rationale) != set(lane.task_ids):
            freeze_blockers.append(
                f"{lane.lane_id} is missing public rationale for selected sentinels"
            )
        if lane.schedule is None:
            freeze_blockers.append(f"{lane.lane_id} is missing a fault schedule")
        else:
            schedule_rows = expand_stress_schedule(lane)
            expected_stress_runs = len(schedule_rows)
            stress_schedule_hash = sha256_json(lane.schedule.model_dump(mode="json"))
            if expected_stress_runs != lane.schedule.expected_derived_runs:
                freeze_blockers.append(
                    f"{lane.lane_id} expands to {expected_stress_runs}/"
                    f"{lane.schedule.expected_derived_runs} stress runs"
                )
        stress_plan_ready = (
            not stress_errors
            and lane.sentinel_count == 3
            and len(lane.task_ids) == 3
            and lane.task_ids == selected_ids
            and lane.selection_policy == "public-contract-structure-v1"
            and set(lane.selection_rationale) == set(lane.task_ids)
            and lane.schedule is not None
            and expected_stress_runs == 30
        )

    freeze_eligible = (
        calibration_ready
        and exact_research_counts
        and repository_policy_passed
        and not errors
        and stress_plan_ready
        and not freeze_blockers
    )
    research_ready = (
        manifest.status == "frozen"
        and exact_research_counts
        and repository_policy_passed
        and not errors
    )
    stress_ready = manifest.status == "frozen" and stress_plan_ready
    return {
        "complete": manifest.status == "frozen" and freeze_eligible,
        "dataset_id": manifest.dataset_id,
        "dataset_status": manifest.status,
        "manifest_hash": manifest_hash,
        "manifest_path": str(resolved_manifest),
        "calibration_ready": calibration_ready,
        "research_ready": research_ready,
        "stress_ready": stress_ready,
        "stress_plan_ready": stress_plan_ready,
        "freeze_eligible": freeze_eligible,
        "freeze_blockers": freeze_blockers,
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
        "expected_stress_selection": expected_stress_selection,
        "stress_schedule_hash": stress_schedule_hash,
        "expected_stress_runs": expected_stress_runs,
        "core_expected_runs": 96,
        "stress_lanes": [
            {
                "lane_id": lane.lane_id,
                "sentinel_count": lane.sentinel_count,
                "selected": len(lane.task_ids),
                "task_ids": lane.task_ids,
                "scenarios": lane.scenarios,
                "selection_policy": lane.selection_policy,
                "schedule_id": lane.schedule.schedule_id if lane.schedule else None,
            }
            for lane in manifest.stress_lanes
        ],
        "errors": errors,
    }


def require_frozen_dataset(
    manifest_path: str | Path | None = None,
) -> tuple[DatasetManifest, str, Path]:
    manifest, manifest_hash, resolved_manifest = load_dataset_manifest(manifest_path)
    audit = audit_dataset(manifest_path=resolved_manifest)
    if manifest.status != "frozen" or not audit.get("complete"):
        details = [
            *(error["error"] for error in audit.get("errors", [])),
            *audit.get("freeze_blockers", []),
        ]
        suffix = "; ".join(dict.fromkeys(details))
        raise ContractError(
            "core experiment requires a complete frozen dataset" + (f": {suffix}" if suffix else "")
        )
    if audit.get("manifest_hash") != manifest_hash:
        raise ContractError("dataset manifest changed during frozen-dataset audit")
    return manifest, manifest_hash, resolved_manifest
