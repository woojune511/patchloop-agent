from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from pydantic import ValidationError

from patchloop.contracts import DatasetRole
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
    dataset = load_dataset_manifest()
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        yaml.safe_dump(_core_suite_payload(dataset[1]), sort_keys=False),
        encoding="utf-8",
    )
    preflight_calls = 0

    def frozen_preflight():
        nonlocal preflight_calls
        preflight_calls += 1
        return dataset

    monkeypatch.setattr(eval_runner, "require_frozen_dataset", frozen_preflight)
    monkeypatch.setattr(eval_runner, "load_task_package", lambda _: package)

    with pytest.raises(ContractError, match="dataset role calibration is not eligible"):
        eval_runner.evaluate_suite(suite_path)
    assert preflight_calls == 1


def test_core_campaign_rejects_dataset_manifest_hash_drift(tmp_path, monkeypatch) -> None:
    dataset = load_dataset_manifest()
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        yaml.safe_dump(
            _core_suite_payload("sha256:" + ("f" * 64)),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(eval_runner, "require_frozen_dataset", lambda: dataset)

    with pytest.raises(ContractError, match="does not match"):
        eval_runner.evaluate_suite(suite_path)


def test_core_campaign_runs_complete_frozen_dataset_preflight_first(
    tmp_path: Path,
    monkeypatch,
) -> None:
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        yaml.safe_dump(
            _core_suite_payload("sha256:" + ("a" * 64)),
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    def reject_incomplete_dataset():
        raise ContractError("core experiment requires a complete frozen dataset")

    def fail_if_task_loading_starts(_):
        pytest.fail("task loading must not start before the frozen-dataset preflight")

    monkeypatch.setattr(
        eval_runner,
        "require_frozen_dataset",
        reject_incomplete_dataset,
    )
    monkeypatch.setattr(eval_runner, "load_task_package", fail_if_task_loading_starts)

    with pytest.raises(ContractError, match="complete frozen dataset"):
        eval_runner.evaluate_suite(suite_path)


def test_core_campaign_schedule_remains_96_runs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manifest_hash = "sha256:" + ("a" * 64)
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        yaml.safe_dump(_core_suite_payload(manifest_hash), sort_keys=False),
        encoding="utf-8",
    )
    dataset = SimpleNamespace(dataset_id="core-role-test")
    preflight_calls = 0

    def frozen_preflight():
        nonlocal preflight_calls
        preflight_calls += 1
        return dataset, manifest_hash, tmp_path / "dataset.yaml"

    def fake_load_task_package(path):
        index = int(Path(path).name.removeprefix("task-"))
        split = "same-repo-heldout" if index < 6 else "cross-repo-heldout"
        public = SimpleNamespace(
            task_id=f"task-{index}",
            task_version=1,
            split=split,
        )
        return SimpleNamespace(
            public=public,
            public_spec_hash="sha256:" + f"{index:064x}",
        )

    def fake_require_dataset_role(*, task_id, **_):
        index = int(task_id.removeprefix("task-"))
        role = (
            DatasetRole.CORE_SAME_REPO
            if index < 6
            else DatasetRole.CORE_CROSS_REPO
        )
        return SimpleNamespace(role=role)

    index_path = tmp_path / "memory-index.json"
    index_path.write_text(
        json.dumps(
            {
                "entries": [{"memory_id": "mem_test"}],
                "embedding": {
                    "implementation": "sentence-transformers",
                    "revision": "test-revision",
                },
                "dataset_manifest_hash": manifest_hash,
            }
        ),
        encoding="utf-8",
    )

    starts: list[tuple[str, object]] = []

    class FakeRunner:
        def start(self, task, *, memory_condition, **_):
            starts.append((task, memory_condition))
            return {"usage": {"model_cost_usd": 0.0}}

    monkeypatch.setattr(eval_runner, "require_frozen_dataset", frozen_preflight)
    monkeypatch.setattr(eval_runner, "load_task_package", fake_load_task_package)
    monkeypatch.setattr(eval_runner, "require_dataset_role", fake_require_dataset_role)
    monkeypatch.setattr(eval_runner, "latest_frozen_index", lambda: index_path)
    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path / "runtime")

    result = eval_runner.evaluate_suite(suite_path)

    assert preflight_calls == 1
    assert result["expected_runs"] == 96
    assert result["completed_runs"] == 96
    assert result["infrastructure_errors"] == 0
    assert len(result["runs"]) == 96
    assert len(starts) == 96
    assert {row["task_id"] for row in result["runs"]} == {
        f"task-{index}" for index in range(12)
    }
    assert {
        row["condition"] for row in result["runs"]
    } == {
        "no_memory",
        "raw_trace",
        "structured",
        "selective_structured",
    }
    assert {row["repetition"] for row in result["runs"]} == {1, 2}


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
