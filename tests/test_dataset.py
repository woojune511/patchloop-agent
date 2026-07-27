from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from patchloop.contracts import (
    AdmissionEvidence,
    DatasetAdmissionState,
    DatasetRole,
    DatasetSourceKind,
    DatasetTaskEntry,
    DifficultyAudit,
    DifficultyTier,
    SourceProvenance,
    WorkflowType,
)
from patchloop.dataset import (
    _same_repo_pairing_violations,
    audit_dataset,
    require_dataset_role,
)
from patchloop.task_loader import load_task_package


def test_calibration_fixtures_are_excluded_from_research_dataset() -> None:
    result = audit_dataset("tasks")
    assert result["complete"] is False
    assert result["calibration_ready"] is True
    assert result["research_ready"] is False
    assert result["stress_ready"] is False
    assert result["task_count"] == 25
    assert result["calibration_task_count"] == 5
    assert result["research_task_count"] == 20
    assert result["candidate_package_count"] == 0
    assert result["unregistered_task_paths"] == []
    assert result["role_counts"] == {
        "calibration": 5,
        "memory-development": 6,
        "development-validation": 2,
        "core-same-repo": 6,
        "core-cross-repo": 6,
    }
    assert "memory-development" not in result["missing"]
    assert "development-validation" not in result["missing"]
    assert result["missing"] == {}
    assert "core-cross-repo" not in result["missing"]
    assert result["repositories"] == [
        "agronholm/anyio",
        "dagster-io/dagster",
        "delgan/loguru",
        "getmoto/moto",
        "holoviz/param",
        "huggingface/huggingface_hub",
        "kubeflow/pipelines",
        "olofk/fusesoc",
        "pdm-project/pdm",
        "pytest-dev/pyfakefs",
        "python-babel/babel",
        "tobymao/sqlglot",
        "tox-dev/tox",
        "youssofal/mtplx",
    ]
    assert result["repository_policy_passed"] is True
    assert result["headline_excluded_task_ids"] == [
        "config-falsy-override",
        "csv-final-record-flush",
        "csv-quoted-newline",
        "duration-minute-boundary",
        "path-prefix-boundary",
    ]
    assert result["errors"] == []


def test_research_tasks_have_real_benchmark_admission_evidence() -> None:
    result = audit_dataset("tasks")
    assert result["research_task_count"] == 20
    assert result["source_counts"] == {
        "synthetic-control": 5,
        "benchmark-instance": 20,
    }
    assert result["difficulty_counts"] == {"easy": 5, "medium": 4, "hard": 16}


def test_first_research_task_is_eligible_only_for_memory_development() -> None:
    package = load_task_package("tasks/dev-train/loguru-invalid-format-feedback")
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.MEMORY_DEVELOPMENT},
    )
    assert entry.role == DatasetRole.MEMORY_DEVELOPMENT
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 5


def test_easy_task_cannot_be_admitted_to_research_dataset() -> None:
    with pytest.raises(ValidationError, match="easy tasks are not eligible"):
        DatasetTaskEntry(
            task_id="real-upstream-task",
            task_version=1,
            path="tasks/dev-train/real-upstream-task",
            role=DatasetRole.MEMORY_DEVELOPMENT,
            admission_state=DatasetAdmissionState.ADMITTED,
            public_spec_hash="sha256:" + ("a" * 64),
            private_spec_hash="sha256:" + ("b" * 64),
            source=SourceProvenance(
                kind=DatasetSourceKind.BENCHMARK_INSTANCE,
                benchmark_family="swe-rebench",
                benchmark_revision="a" * 40,
                benchmark_instance_id="owner__repo-1",
                upstream_repository="owner/repo",
                upstream_base_commit="c" * 40,
                issue_url="https://github.com/owner/repo/issues/1",
                license_spdx="MIT",
                retrieved_at="2026-07-24T00:00:00Z",
                contamination_risk="high",
                workflow_type=WorkflowType.ISSUE_FIX,
            ),
            difficulty=DifficultyAudit(
                localization=0,
                reasoning_depth=1,
                implementation_breadth=0,
                verification_breadth=1,
                total=2,
                tier=DifficultyTier.EASY,
                rationale="Too small for research use.",
            ),
            failure_pattern_id="boundary-condition",
            solution_lineage_id="owner-repo-issue-1",
            admission_evidence=AdmissionEvidence(
                path="reports/admission/owner-repo-1.json",
                sha256="sha256:" + ("d" * 64),
                official=True,
                base_visible_pass=True,
                base_hidden_fail=True,
                reference_pass=True,
                reference_pass_runs=3,
                rejected_bad_patches=3,
            ),
        )


def test_difficulty_total_is_derived_from_dimensions() -> None:
    with pytest.raises(ValidationError, match="difficulty total must equal"):
        DifficultyAudit(
            localization=1,
            reasoning_depth=1,
            implementation_breadth=1,
            verification_breadth=1,
            total=3,
            tier=DifficultyTier.MEDIUM,
            rationale="The supplied total is deliberately wrong.",
        )


def test_research_source_provenance_rejects_blank_required_identity() -> None:
    with pytest.raises(ValidationError, match="missing provenance: upstream_repository"):
        SourceProvenance(
            kind=DatasetSourceKind.BENCHMARK_INSTANCE,
            benchmark_family="swe-rebench",
            benchmark_revision="a" * 40,
            benchmark_instance_id="owner__repo-1",
            upstream_repository=" ",
            upstream_base_commit="c" * 40,
            issue_url="https://github.com/owner/repo/issues/1",
            license_spdx="MIT",
            retrieved_at="2026-07-24T00:00:00Z",
            contamination_risk="high",
            workflow_type=WorkflowType.ISSUE_FIX,
        )


def test_same_repo_pairing_requires_one_task_per_development_repository() -> None:
    assert (
        _same_repo_pairing_violations(
            Counter({"owner/a": 1, "owner/b": 1}),
            Counter({"owner/a": 1, "owner/b": 1}),
        )
        == []
    )

    violations = _same_repo_pairing_violations(
        Counter({"owner/a": 1, "owner/b": 1}),
        Counter({"owner/a": 2}),
    )
    assert violations == [
        "same-repo lane is missing development repositories: owner/b",
        "same-repo lane is not one task per repository: owner/a",
    ]


def test_same_repo_pairing_rejects_duplicate_development_lineage_repository() -> None:
    violations = _same_repo_pairing_violations(
        Counter({"owner/a": 2, "owner/b": 1}),
        Counter({"owner/a": 1, "owner/b": 1, "owner/c": 1}),
    )
    assert violations == [
        "same-repo lane has repositories outside development: owner/c",
        "memory-development lane is not one task per repository: owner/a",
    ]


@pytest.mark.parametrize(
    ("source_field", "replacement", "expected_error"),
    [
        (
            "upstream_repository",
            "Delgan/loguru",
            "source repository mismatch",
        ),
        (
            "upstream_base_commit",
            "0" * 40,
            "source base commit mismatch",
        ),
    ],
)
def test_dataset_audit_binds_source_provenance_to_public_repository(
    tmp_path: Path,
    source_field: str,
    replacement: str,
    expected_error: str,
) -> None:
    manifest = yaml.safe_load(
        Path("data/dataset-manifest.yaml").read_text(encoding="utf-8")
    )
    pyfakefs_entry = next(
        entry
        for entry in manifest["tasks"]
        if entry["task_id"] == "pyfakefs-file-wrapper-io-capabilities"
    )
    pyfakefs_entry["source"][source_field] = replacement
    manifest_path = tmp_path / "dataset-manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )

    result = audit_dataset("tasks", manifest_path=manifest_path)

    assert any(expected_error in error["error"] for error in result["errors"])


def test_dataset_audit_enforces_one_to_one_pairing_when_lanes_are_filled(
    tmp_path: Path,
) -> None:
    manifest = yaml.safe_load(
        Path("data/dataset-manifest.yaml").read_text(encoding="utf-8")
    )
    selected_task_ids = {
        "config-falsy-override",
        "loguru-invalid-format-feedback",
        "moto-query-scanned-count",
        "pdm-target-project-options-loading",
        "sqlglot-duckdb-ignore-nulls-modifier-order",
    }
    manifest["calibration_target"] = 1
    manifest["targets"] = {
        "memory-development": 1,
        "development-validation": 1,
        "core-same-repo": 1,
        "core-cross-repo": 1,
    }
    manifest["tasks"] = [
        entry
        for entry in manifest["tasks"]
        if entry["task_id"] in selected_task_ids
    ]
    manifest["stress_lanes"] = []
    manifest_path = tmp_path / "dataset-manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )

    result = audit_dataset("tasks", manifest_path=manifest_path)

    assert result["role_counts"] == {
        "calibration": 1,
        "memory-development": 1,
        "development-validation": 1,
        "core-same-repo": 1,
        "core-cross-repo": 1,
    }
    assert [error["error"] for error in result["errors"]] == [
        "same-repo tasks lack development repository coverage: pdm-project/pdm",
        "same-repo lane is missing development repositories: delgan/loguru",
        "same-repo lane has repositories outside development: pdm-project/pdm",
    ]
