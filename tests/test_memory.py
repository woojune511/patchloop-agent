from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
import yaml

from patchloop.contracts import (
    DatasetRole,
    ExperimentPurpose,
    ExperimentRunContext,
    FailureRecord,
    MemoryCondition,
    Phase,
)
from patchloop.dataset import load_dataset_manifest
from patchloop.errors import ContractError
from patchloop.evals.qualification import calculate_source_evidence_hash
from patchloop.evals.runner import (
    MEMORY_DEVELOPMENT_TASKS,
    ExperimentSuite,
    _execution_hash,
    _suite_payload,
)
from patchloop.memory import store as memory_store
from patchloop.memory.retrieval import retrieve_memory
from patchloop.runtime import build_manifest
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_text


def _write_dataset_manifest(
    path: Path,
    *,
    role: str,
    public_spec_hash: str,
    private_spec_hash: str,
) -> Path:
    calibration = role == "calibration"
    source = (
        {
            "kind": "synthetic-control",
            "contamination_risk": "none",
            "workflow_type": "issue-fix",
        }
        if calibration
        else {
            "kind": "upstream-incident",
            "upstream_repository": "https://github.com/example/project",
            "upstream_base_commit": "a" * 40,
            "issue_url": "https://github.com/example/project/issues/1",
            "license_spdx": "MIT",
            "retrieved_at": "2026-07-24T00:00:00Z",
            "contamination_risk": "low",
            "workflow_type": "issue-fix",
        }
    )
    difficulty = (
        {
            "localization": 0,
            "reasoning_depth": 1,
            "implementation_breadth": 0,
            "verification_breadth": 1,
            "total": 2,
            "tier": "easy",
            "rationale": "Calibration boundary fixture.",
        }
        if calibration
        else {
            "localization": 1,
            "reasoning_depth": 1,
            "implementation_breadth": 1,
            "verification_breadth": 0,
            "total": 3,
            "tier": "medium",
            "rationale": "Requires non-local repository reasoning.",
        }
    )
    entry = {
        "task_id": "duration-minute-boundary",
        "task_version": 1,
        "path": "tasks/dev-train/duration-minute-boundary",
        "role": role,
        "admission_state": "fixture" if calibration else "admitted",
        "public_spec_hash": public_spec_hash,
        "private_spec_hash": private_spec_hash,
        "source": source,
        "difficulty": difficulty,
        "failure_pattern_id": "boundary-semantics",
        "solution_lineage_id": "duration-minute-v1",
        "admission_evidence": (
            None
            if calibration
            else {
                "path": "reports/example.json",
                "sha256": "sha256:" + ("b" * 64),
                "official": True,
                "base_visible_pass": True,
                "base_hidden_fail": True,
                "reference_pass": True,
                "reference_pass_runs": 3,
                "rejected_bad_patches": 3,
            }
        ),
    }
    payload = {
        "schema_version": "dataset-manifest-v1",
        "dataset_id": "memory-role-test",
        "status": "draft",
        "calibration_target": 1,
        "targets": {
            "memory-development": 1,
            "development-validation": 1,
            "core-same-repo": 1,
            "core-cross-repo": 1,
        },
        "tasks": [entry],
        "stress_lanes": [],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _write_failure_source(tmp_path: Path) -> tuple[str, str, str]:
    package = load_task_package("tasks/dev-train/duration-minute-boundary")
    manifest = build_manifest(package, run_id="run_memory_role_test")
    StateStore(tmp_path / "state.sqlite3").create_run(manifest)
    record = FailureRecord(
        failure_id="fail_memory_role_test",
        run_id=manifest.run_id,
        primary_cause="hidden-acceptance-failure",
        phase=Phase.REVIEW,
        confidence=1.0,
        classification_method="test",
    )
    failure_dir = tmp_path / "failures" / "dev-train"
    failure_dir.mkdir(parents=True)
    failure_path = failure_dir / f"{record.failure_id}.json"
    failure_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    return record.failure_id, package.public_spec_hash, package.private_spec_hash


def _write_qualification(
    tmp_path: Path,
    *,
    run_id: str,
    failure_id: str,
    dataset_manifest_hash: str,
) -> None:
    state = StateStore(tmp_path / "state.sqlite3")
    manifest = state.get_manifest(run_id)
    hash_value = "sha256:" + ("a" * 64)
    manifest.model.provider = "openai"
    manifest.model.model_id = "gpt-5.6-terra"
    manifest.model.provider_sdk_version = "test"
    suite = ExperimentSuite.model_validate(
        {
            "schema_version": "experiment-v2",
            "experiment_id": "memory-role-test",
            "purpose": "memory-development-no-memory",
            "tasks": sorted(MEMORY_DEVELOPMENT_TASKS),
            "conditions": ["no_memory"],
            "repetitions": 2,
            "model": "openai",
            "model_id": "gpt-5.6-terra",
            "cost_limit_usd": 20,
            "dataset_manifest_hash": dataset_manifest_hash,
        }
    )
    suite_payload = _suite_payload(suite)
    suite_hash = sha256_text(canonical_json(suite_payload))
    dataset = {"manifest_hash": dataset_manifest_hash}
    tasks = [
        {
            "task_id": manifest.task_id,
            "task_version": manifest.task_version,
            "public_spec_hash": manifest.public_spec_hash,
            "private_spec_hash": manifest.private_spec_hash,
            "base_commit": manifest.base_commit,
            "evaluator_image_digest": manifest.evaluator_image_digest,
        }
    ]
    schedule = [
        {
            "order": 1,
            "schedule_row_id": hash_value,
            "task_id": manifest.task_id,
            "dataset_role": DatasetRole.MEMORY_DEVELOPMENT.value,
            "condition": manifest.memory.condition.value,
            "repetition": 1,
        }
    ]
    schedule_hash = sha256_text(canonical_json(schedule))
    environment = {
        "git": {"commit": manifest.harness_git_commit},
        "docker": {"images": []},
        "openai_sdk": {
            "installed": True,
            "version": manifest.model.provider_sdk_version,
        },
    }
    pilot_qualification: dict[str, object] = {}
    execution_hash = _execution_hash(
        suite,
        dataset=dataset,
        task_rows=tasks,
        schedule_hash=schedule_hash,
        git_state=environment["git"],
        docker_state=environment["docker"],
        openai_sdk=environment["openai_sdk"],
        pilot_qualification=pilot_qualification,
    )
    manifest.experiment = ExperimentRunContext(
        experiment_id="memory-role-test",
        purpose=ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY,
        suite_hash=suite_hash,
        execution_hash=execution_hash,
        dataset_manifest_hash=dataset_manifest_hash,
        dataset_role=DatasetRole.MEMORY_DEVELOPMENT,
        schedule_seed=20260723,
        schedule_order=1,
        schedule_row_id=hash_value,
        repetition=1,
    )
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        connection.execute(
            "UPDATE runs SET manifest_json = ? WHERE run_id = ?",
            (canonical_json(manifest.model_dump(mode="json")), run_id),
        )
    plan = {
        "schema_version": "experiment-execution-plan-v1",
        "experiment_id": manifest.experiment.experiment_id,
        "purpose": manifest.experiment.purpose.value,
        "suite_hash": manifest.experiment.suite_hash,
        "execution_hash": manifest.experiment.execution_hash,
        "schedule_hash": schedule_hash,
        "expected_runs": len(schedule),
        "suite": suite_payload,
        "dataset": dataset,
        "tasks": tasks,
        "schedule": schedule,
        "environment": environment,
        "approval": {
            "invocation_approve_live_cost": True,
            "invocation_approved_execution_hash": manifest.experiment.execution_hash,
            "matches_execution_hash": True,
        },
        "pilot_qualification": pilot_qualification,
        "blockers": [],
        "ready": True,
    }
    plan_path = (
        tmp_path
        / "experiments"
        / "plans"
        / f"{manifest.experiment.execution_hash.removeprefix('sha256:')}.json"
    )
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    payload = {
        "schema_version": "trace-qualification-v1",
        "run_id": run_id,
        "qualified": True,
        "trace_integrity_passed": True,
        "leakage_scan_passed": True,
        "evaluation_reached": True,
        "outcome_kind": "task_failure",
        "purpose": "memory-development-no-memory",
        "dataset_role": "memory-development",
        "dataset_manifest_hash": dataset_manifest_hash,
        "model_provider": "openai",
        "memory_condition": "no_memory",
        "fault_type": "none",
        "memory_candidate_eligible": True,
        "failure_record_id": failure_id,
        "failure_record_hash": sha256_bytes(
            (
                tmp_path
                / "failures"
                / "dev-train"
                / f"{failure_id}.json"
            ).read_bytes()
        ),
        "source_evidence_hash": calculate_source_evidence_hash(run_id, root=tmp_path),
        "checks": [],
    }
    payload["qualification_hash"] = sha256_text(canonical_json(payload))
    path = tmp_path / "qualifications" / f"{run_id}.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_selective_memory_has_auditable_no_match(tmp_path) -> None:
    index = tmp_path / "index.json"
    index.write_text(
        json.dumps(
            {
                "index_version": "idx_test",
                "entries": [],
            }
        ),
        encoding="utf-8",
    )
    text, decision = retrieve_memory(
        run_id="run_test",
        query="quoted csv newline",
        phase=Phase.REPRODUCE,
        condition=MemoryCondition.SELECTIVE_STRUCTURED,
        index_path=index,
    )
    assert text == ""
    assert decision is not None and decision.no_match is True
    assert decision.selected_memory_ids == []


def test_empty_memory_index_cannot_be_frozen(tmp_path, monkeypatch) -> None:
    root = tmp_path / "indexes"
    index_dir = root / "idx_empty"
    index_dir.mkdir(parents=True)
    (index_dir / "index.json").write_text(
        json.dumps(
            {
                "index_version": "idx_empty",
                "entries": [],
                "embedding": {
                    "model": memory_store.EMBEDDING_MODEL,
                    "revision": "abc123",
                    "implementation": "empty-no-embedding",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(memory_store, "index_root", lambda: root)
    with pytest.raises(ContractError, match="empty"):
        memory_store.freeze_index("idx_empty", "abc123")


def test_calibration_failure_cannot_be_approved_as_memory_source(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(memory_store, "runtime_root", lambda: tmp_path)
    failure_id, public_hash, private_hash = _write_failure_source(tmp_path)
    dataset_path = _write_dataset_manifest(
        tmp_path / "dataset.yaml",
        role="calibration",
        public_spec_hash=public_hash,
        private_spec_hash=private_hash,
    )
    failure_path = tmp_path / "failures" / "dev-train" / f"{failure_id}.json"
    original = failure_path.read_bytes()

    with pytest.raises(ContractError, match="dataset role calibration is not eligible"):
        memory_store.review_failure(
            failure_id,
            approve=True,
            dataset_manifest_path=dataset_path,
        )

    assert failure_path.read_bytes() == original


def test_memory_index_records_admitted_dataset_identity(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(memory_store, "runtime_root", lambda: tmp_path)
    failure_id, public_hash, private_hash = _write_failure_source(tmp_path)
    dataset_path = _write_dataset_manifest(
        tmp_path / "dataset.yaml",
        role="memory-development",
        public_spec_hash=public_hash,
        private_spec_hash=private_hash,
    )
    failure_path = tmp_path / "failures" / "dev-train" / f"{failure_id}.json"
    record = FailureRecord.model_validate_json(failure_path.read_text(encoding="utf-8"))
    _, dataset_manifest_hash, _ = load_dataset_manifest(dataset_path)
    _write_qualification(
        tmp_path,
        run_id=record.run_id,
        failure_id=failure_id,
        dataset_manifest_hash=dataset_manifest_hash,
    )
    monkeypatch.setattr(
        memory_store,
        "require_frozen_dataset",
        lambda path: load_dataset_manifest(path),
    )
    original = failure_path.read_bytes()
    review = memory_store.review_failure(
        failure_id,
        approve=True,
        dataset_manifest_path=dataset_path,
    )
    second_review = memory_store.review_failure(
        failure_id,
        approve=True,
        reviewer="second-reviewer",
        dataset_manifest_path=dataset_path,
    )
    monkeypatch.setattr(
        memory_store,
        "_build_embeddings",
        lambda entries, revision: {entry.memory_id: [1.0, 0.0] for entry in entries},
    )

    built = memory_store.build_index_from_failures(
        embedding_revision="test-revision",
        dataset_manifest_path=dataset_path,
    )
    payload = json.loads(Path(built["path"]).read_text(encoding="utf-8"))

    assert review["dataset_role"] == "memory-development"
    assert review["history_length"] == 1
    assert second_review["history_length"] == 2
    assert failure_path.read_bytes() == original
    history = [
        json.loads(line)
        for line in Path(review["audit_path"]).read_text(encoding="utf-8").splitlines()
    ]
    assert history[0]["previous_review_hash"] is None
    assert history[1]["previous_review_hash"] == history[0]["review_hash"]
    assert payload["dataset_id"] == "memory-role-test"
    assert payload["dataset_manifest_hash"] == review["dataset_manifest_hash"]
    assert payload["entries"][0]["validation_count"] == 0
