from __future__ import annotations

import pytest
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
from patchloop.dataset import audit_dataset, require_dataset_role
from patchloop.task_loader import load_task_package


def test_calibration_fixtures_are_excluded_from_research_dataset() -> None:
    result = audit_dataset("tasks")
    assert result["complete"] is False
    assert result["calibration_ready"] is True
    assert result["research_ready"] is False
    assert result["stress_ready"] is False
    assert result["task_count"] == 22
    assert result["calibration_task_count"] == 5
    assert result["research_task_count"] == 17
    assert result["candidate_package_count"] == 0
    assert result["unregistered_task_paths"] == []
    assert result["role_counts"] == {
        "calibration": 5,
        "memory-development": 6,
        "development-validation": 2,
        "core-same-repo": 4,
        "core-cross-repo": 5,
    }
    assert "memory-development" not in result["missing"]
    assert "development-validation" not in result["missing"]
    assert result["missing"]["core-same-repo"] == 2
    assert result["missing"]["core-cross-repo"] == 1
    assert result["repositories"] == [
        "agronholm/anyio",
        "dagster-io/dagster",
        "delgan/loguru",
        "getmoto/moto",
        "holoviz/param",
        "huggingface/huggingface_hub",
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
    assert result["research_task_count"] == 17
    assert result["source_counts"] == {
        "synthetic-control": 5,
        "benchmark-instance": 17,
    }
    assert result["difficulty_counts"] == {"easy": 5, "medium": 3, "hard": 14}


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
