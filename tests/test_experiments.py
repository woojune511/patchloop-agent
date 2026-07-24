from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from patchloop.dataset import load_dataset_manifest
from patchloop.errors import ContractError
from patchloop.evals import runner as eval_runner
from patchloop.evals.runner import ExperimentSuite
from patchloop.task_loader import load_task_package


def _core_suite_payload(dataset_manifest_hash: str) -> dict:
    return {
        "schema_version": "experiment-v1",
        "experiment_id": "core-role-test",
        "core": True,
        "tasks": [f"task-{index}" for index in range(12)],
        "conditions": [
            "no_memory",
            "raw_trace",
            "structured",
            "selective_structured",
        ],
        "repetitions": 2,
        "model": "mock",
        "embedding_revision": "test-revision",
        "dataset_manifest_hash": dataset_manifest_hash,
    }


def _write_frozen_manifest_with_calibration(
    path: Path,
    *,
    public_spec_hash: str,
    private_spec_hash: str,
) -> tuple[object, str, Path]:
    entries = [
        {
            "task_id": "duration-minute-boundary",
            "task_version": 1,
            "path": "tasks/dev-train/duration-minute-boundary",
            "role": "calibration",
            "admission_state": "fixture",
            "public_spec_hash": public_spec_hash,
            "private_spec_hash": private_spec_hash,
            "source": {
                "kind": "synthetic-control",
                "contamination_risk": "none",
                "workflow_type": "issue-fix",
            },
            "difficulty": {
                "localization": 0,
                "reasoning_depth": 1,
                "implementation_breadth": 0,
                "verification_breadth": 1,
                "total": 2,
                "tier": "easy",
                "rationale": "Calibration boundary fixture.",
            },
            "failure_pattern_id": "boundary-semantics",
            "solution_lineage_id": "duration-minute-v1",
            "admission_evidence": None,
        }
    ]
    for index, role in enumerate(
        [
            "memory-development",
            "development-validation",
            "core-same-repo",
            "core-cross-repo",
        ],
        1,
    ):
        entries.append(
            {
                "task_id": f"research-task-{index}",
                "task_version": 1,
                "path": f"tasks/research/task-{index}",
                "role": role,
                "admission_state": "admitted",
                "public_spec_hash": "sha256:" + (str(index) * 64),
                "private_spec_hash": "sha256:" + (str(index + 4) * 64),
                "source": {
                    "kind": "upstream-incident",
                    "upstream_repository": f"https://github.com/example/repo-{index}",
                    "upstream_base_commit": f"{index}" * 40,
                    "issue_url": f"https://github.com/example/repo-{index}/issues/1",
                    "license_spdx": "MIT",
                    "retrieved_at": "2026-07-24T00:00:00Z",
                    "contamination_risk": "low",
                    "workflow_type": "issue-fix",
                },
                "difficulty": {
                    "localization": 1,
                    "reasoning_depth": 1,
                    "implementation_breadth": 1,
                    "verification_breadth": 0,
                    "total": 3,
                    "tier": "medium",
                    "rationale": "Requires non-local repository reasoning.",
                },
                "failure_pattern_id": f"pattern-{index}",
                "solution_lineage_id": f"solution-{index}",
                "admission_evidence": {
                    "path": f"reports/gate-{index}.json",
                    "sha256": "sha256:" + ("a" * 64),
                    "official": True,
                    "base_visible_pass": True,
                    "base_hidden_fail": True,
                    "reference_pass": True,
                    "reference_pass_runs": 3,
                    "rejected_bad_patches": 3,
                },
            }
        )
    payload = {
        "schema_version": "dataset-manifest-v1",
        "dataset_id": "core-role-test",
        "status": "frozen",
        "calibration_target": 1,
        "targets": {
            "memory-development": 1,
            "development-validation": 1,
            "core-same-repo": 1,
            "core-cross-repo": 1,
        },
        "tasks": entries,
        "stress_lanes": [],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return load_dataset_manifest(path)


def test_live_campaign_requires_explicit_cost_approval() -> None:
    with pytest.raises(ValidationError, match="live_cost_approved"):
        ExperimentSuite(
            experiment_id="live-test",
            tasks=["task"],
            conditions=["no_memory"],
            model="openai",
        )


def test_core_campaign_requires_exact_design() -> None:
    with pytest.raises(ValidationError, match="12 unique"):
        ExperimentSuite(
            experiment_id="core-test",
            core=True,
            tasks=["task"],
            conditions=["no_memory"],
            model="mock",
        )


def test_core_campaign_requires_dataset_manifest_hash() -> None:
    with pytest.raises(ValidationError, match="dataset manifest hash"):
        ExperimentSuite(
            experiment_id="core-test",
            core=True,
            tasks=[f"task-{index}" for index in range(12)],
            conditions=[
                "no_memory",
                "raw_trace",
                "structured",
                "selective_structured",
            ],
            repetitions=2,
            model="mock",
            embedding_revision="test-revision",
        )


def test_offline_smoke_remains_a_calibration_suite() -> None:
    suite = eval_runner.load_suite("experiments/smoke.yaml")
    assert suite.core is False
    assert suite.dataset_manifest_hash is None


def test_core_campaign_rejects_calibration_registry_role(tmp_path, monkeypatch) -> None:
    package = load_task_package("tasks/dev-train/duration-minute-boundary")
    dataset = _write_frozen_manifest_with_calibration(
        tmp_path / "dataset.yaml",
        public_spec_hash=package.public_spec_hash,
        private_spec_hash=package.private_spec_hash,
    )
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        yaml.safe_dump(_core_suite_payload(dataset[1]), sort_keys=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(eval_runner, "load_dataset_manifest", lambda: dataset)
    monkeypatch.setattr(eval_runner, "load_task_package", lambda _: package)

    with pytest.raises(ContractError, match="dataset role calibration is not eligible"):
        eval_runner.evaluate_suite(suite_path)


def test_core_campaign_rejects_dataset_manifest_hash_drift(tmp_path, monkeypatch) -> None:
    package = load_task_package("tasks/dev-train/duration-minute-boundary")
    dataset = _write_frozen_manifest_with_calibration(
        tmp_path / "dataset.yaml",
        public_spec_hash=package.public_spec_hash,
        private_spec_hash=package.private_spec_hash,
    )
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        yaml.safe_dump(
            _core_suite_payload("sha256:" + ("f" * 64)),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(eval_runner, "load_dataset_manifest", lambda: dataset)

    with pytest.raises(ContractError, match="does not match"):
        eval_runner.evaluate_suite(suite_path)


def test_core_campaign_rejects_memory_index_from_another_dataset() -> None:
    suite = ExperimentSuite.model_validate(_core_suite_payload("sha256:" + ("a" * 64)))
    index_payload = {
        "entries": [{"memory_id": "mem_test"}],
        "embedding": {
            "implementation": "sentence-transformers",
            "revision": "test-revision",
        },
        "dataset_manifest_hash": "sha256:" + ("b" * 64),
    }

    with pytest.raises(ContractError, match="memory index dataset manifest hash"):
        eval_runner._validate_memory_index(index_payload, suite)
