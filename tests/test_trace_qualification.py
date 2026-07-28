from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Checkpoint,
    DatasetRole,
    EventType,
    ExperimentPurpose,
    ExperimentRunContext,
    Phase,
    RunOutcomeKind,
    RunResult,
    RunStatus,
    Usage,
    Verdicts,
    VerdictState,
    VerifierResult,
)
from patchloop.dataset import load_dataset_manifest
from patchloop.errors import ContractError
from patchloop.evals.failures import classify_failure
from patchloop.evals.qualification import (
    calculate_source_evidence_hash,
    load_trace_qualification,
    qualify_run,
)
from patchloop.memory.store import review_failure
from patchloop.runtime import build_manifest
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import utc_now

MEMORY_TASK = Path("tasks/dev-train/loguru-invalid-format-feedback")
PILOT_TASK = Path("tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes")
HASH = "sha256:" + ("a" * 64)


def _execution_plan_path_for_test(root: Path, execution_hash: str) -> Path:
    return (
        root
        / "experiments"
        / "plans"
        / f"{execution_hash.removeprefix('sha256:')}.json"
    )


def _write_execution_plan(
    root: Path,
    *,
    manifest,
    dataset_hash: str,
) -> Path:
    assert manifest.experiment is not None
    experiment = manifest.experiment
    payload = {
        "schema_version": "experiment-execution-plan-v1",
        "experiment_id": experiment.experiment_id,
        "purpose": experiment.purpose.value,
        "suite_hash": experiment.suite_hash,
        "execution_hash": experiment.execution_hash,
        "suite": {
            "experiment_id": experiment.experiment_id,
            "purpose": experiment.purpose.value,
        },
        "dataset": {"manifest_hash": dataset_hash},
        "tasks": [
            {
                "task_id": manifest.task_id,
                "task_version": manifest.task_version,
                "public_spec_hash": manifest.public_spec_hash,
                "private_spec_hash": manifest.private_spec_hash,
                "base_commit": manifest.base_commit,
                "evaluator_image_digest": manifest.evaluator_image_digest,
            }
        ],
        "schedule": [
            {
                "order": experiment.schedule_order,
                "schedule_row_id": experiment.schedule_row_id,
                "task_id": manifest.task_id,
                "dataset_role": (
                    experiment.dataset_role.value
                    if experiment.dataset_role is not None
                    else None
                ),
                "condition": manifest.memory.condition.value,
                "repetition": experiment.repetition,
            }
        ],
        "approval": {
            "invocation_approve_live_cost": True,
            "invocation_approved_execution_hash": experiment.execution_hash,
            "matches_execution_hash": True,
        },
        "blockers": [],
        "ready": True,
    }
    path = _execution_plan_path_for_test(root, experiment.execution_hash)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _result(run_id: str, *, resolved: bool, hidden_check_id: str) -> RunResult:
    verifier = VerifierResult(
        verifier_result_id="vr_test",
        run_id=run_id,
        check_type="hidden",
        check_id=hidden_check_id,
        state=VerdictState.PASS if resolved else VerdictState.FAIL,
        duration_ms=1,
    )
    return RunResult(
        run_id=run_id,
        agent_submission_status="completed",
        evaluation_status="completed",
        scope_compliant_success=resolved,
        official=True,
        verdicts=Verdicts(
            hidden_tests=VerdictState.PASS if resolved else VerdictState.FAIL,
            regression_tests=VerdictState.PASS,
            scope_policy=VerdictState.PASS,
            safety_policy=VerdictState.PASS,
        ),
        usage=Usage(model_calls=1, tool_calls=1),
        submitted_patch_artifact_id="art_patch",
        verifier_results=[verifier],
        outcome_kind=(
            RunOutcomeKind.RESOLVED if resolved else RunOutcomeKind.TASK_FAILURE
        ),
    )


def _terminal_trace(
    tmp_path: Path,
    *,
    task_dir: Path = MEMORY_TASK,
    purpose: ExperimentPurpose = ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY,
    role: DatasetRole = DatasetRole.MEMORY_DEVELOPMENT,
    resolved: bool = False,
    agent_failure: bool = False,
    context_text: str = "public task context",
    write_execution_plan: bool = True,
) -> tuple[str, RunResult, str]:
    package = load_task_package(task_dir)
    _, dataset_hash, _ = load_dataset_manifest()
    outcome_label = "agent" if agent_failure else ("resolved" if resolved else "failure")
    run_id = f"run_qualification_{outcome_label}"
    manifest = build_manifest(
        package,
        run_id=run_id,
        provider="openai",
        model_id="gpt-5.6-terra",
        sandbox_backend="docker",
        agent_image_digest=(
            package.environment.image_digest if package.environment is not None else None
        ),
        evaluator_image_digest=(
            package.environment.image_digest if package.environment is not None else None
        ),
    )
    manifest.experiment = ExperimentRunContext(
        experiment_id="qualification-test",
        purpose=purpose,
        suite_hash=HASH,
        execution_hash=HASH,
        dataset_manifest_hash=dataset_hash,
        dataset_role=role,
        schedule_seed=20260723,
        schedule_order=1,
        schedule_row_id=HASH,
        repetition=1,
    )
    if write_execution_plan:
        _write_execution_plan(
            tmp_path,
            manifest=manifest,
            dataset_hash=dataset_hash,
        )
    state = StateStore(tmp_path / "state.sqlite3")
    state.create_run(manifest)
    artifacts = ArtifactStore(tmp_path / "artifacts")
    runtime_contract = artifacts.put_text("public runtime contract")
    context = artifacts.put_text(context_text)
    model = artifacts.put_text("public model response")
    state.append_event(
        run_id,
        EventType.RUN_STARTED,
        actor="runner",
        payload={
            "artifact_id": runtime_contract.artifact_id,
            "artifact_path": runtime_contract.path,
        },
    )
    state.append_event(
        run_id,
        EventType.CONTEXT_BUILT,
        actor="context-builder",
        payload={"artifact_id": context.artifact_id, "artifact_path": context.path},
    )
    state.append_event(
        run_id,
        EventType.MODEL_CALLED,
        actor="model-adapter",
        payload={
            "artifact_id": model.artifact_id,
            "artifact_path": model.path,
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "cache_write_input_tokens": 0,
            "output_tokens": 0,
        },
    )
    state.append_event(
        run_id,
        EventType.TOOL_CALLED,
        actor="tool-gateway",
        payload={"tool": "read_file"},
    )
    checkpoint = Checkpoint(
        checkpoint_id="ckpt_qualification",
        run_id=run_id,
        through_sequence=4,
        phase=Phase.DONE,
        repository_head=package.public.repository.base_commit,
        worktree_diff_hash=HASH,
        created_at=utc_now(),
    )
    state.save_checkpoint(checkpoint)
    state.append_event(
        run_id,
        EventType.CHECKPOINT_SAVED,
        actor="state-store",
        payload={"checkpoint_id": checkpoint.checkpoint_id},
    )
    hidden_id = package.private.hidden_checks[0].id
    if agent_failure:
        result = RunResult(
            run_id=run_id,
            agent_submission_status="failed",
            evaluation_status="not_run",
            scope_compliant_success=False,
            official=False,
            verdicts=Verdicts(),
            usage=Usage(model_calls=1, tool_calls=1),
            outcome_kind=RunOutcomeKind.AGENT_FAILURE,
            terminal_error={"type": "ContractError", "message": "public failure"},
        )
    else:
        result = _result(run_id, resolved=resolved, hidden_check_id=hidden_id)
    failure_id = ""
    failure = classify_failure(
        result,
        package.public.split,
        root=tmp_path,
    )
    if failure is not None:
        failure_id = failure.failure_id
        state.append_event(
            run_id,
            EventType.FAILURE_TAGGED,
            actor="failure-classifier",
            payload={"failure_id": failure.failure_id},
        )
    state.append_event(
        run_id,
        EventType.RUN_FAILED if agent_failure else EventType.RUN_COMPLETED,
        actor="runner" if agent_failure else "evaluator",
    )
    state.set_run_status(
        run_id,
        RunStatus.FAILED if agent_failure else RunStatus.COMPLETED,
        result.model_dump(mode="json"),
    )
    result_path = tmp_path / "artifacts" / "runs" / run_id / "result.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return run_id, result, failure_id


def test_live_memory_development_failure_is_qualified_and_eligible(tmp_path) -> None:
    run_id, _, failure_id = _terminal_trace(tmp_path)

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    assert qualification["qualified"] is True
    assert qualification["trace_integrity_passed"] is True
    assert qualification["leakage_scan_passed"] is True
    assert qualification["outcome_kind"] == "task_failure"
    assert qualification["memory_candidate_eligible"] is True
    assert qualification["failure_record_id"] == failure_id
    assert qualification["source_evidence_hash"] == calculate_source_evidence_hash(
        run_id,
        root=tmp_path,
    )
    assert load_trace_qualification(run_id, root=tmp_path) == qualification


def test_resolved_live_pilot_is_qualified_but_not_memory_eligible(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(
        tmp_path,
        task_dir=PILOT_TASK,
        purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT,
        role=DatasetRole.DEVELOPMENT_VALIDATION,
        resolved=True,
    )

    qualification = qualify_run(run_id, task_dir=PILOT_TASK, root=tmp_path)

    assert qualification["qualified"] is True
    assert qualification["purpose"] == "development-validation-live-pilot"
    assert qualification["dataset_role"] == "development-validation"
    assert qualification["outcome_kind"] == "resolved"
    assert qualification["memory_candidate_eligible"] is False


def test_terminal_agent_failure_is_qualified_and_memory_eligible(tmp_path) -> None:
    run_id, _, failure_id = _terminal_trace(tmp_path, agent_failure=True)

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    assert qualification["qualified"] is True
    assert qualification["evaluation_reached"] is False
    assert qualification["outcome_kind"] == "agent_failure"
    assert qualification["failure_record_id"] == failure_id
    assert qualification["memory_candidate_eligible"] is True


def test_private_token_leak_fails_without_copying_token_to_artifact(
    tmp_path,
    monkeypatch,
) -> None:
    package = load_task_package(MEMORY_TASK)
    hidden_id = package.private.hidden_checks[0].id
    api_key = "sk-test-private-qualification-key"
    monkeypatch.setenv("OPENAI_API_KEY", api_key)
    run_id, _, _ = _terminal_trace(
        tmp_path,
        context_text=f"leaked: {hidden_id} {api_key}",
    )

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)
    persisted = json.dumps(qualification, sort_keys=True)

    assert qualification["qualified"] is False
    assert qualification["leakage_scan_passed"] is False
    assert qualification["memory_candidate_eligible"] is False
    assert hidden_id not in persisted
    assert api_key not in persisted
    assert package.private.reference_patch.sha256 not in persisted


def test_modified_content_addressed_artifact_fails_trace_integrity(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path)
    object_paths = sorted(
        path
        for path in (tmp_path / "artifacts" / "objects" / "sha256").rglob("*")
        if path.is_file()
    )
    assert object_paths
    object_paths[0].write_text("modified after event persistence", encoding="utf-8")

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    assert qualification["qualified"] is False
    assert qualification["trace_integrity_passed"] is False
    artifact_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "agent_visible_artifacts"
    )
    assert artifact_check["passed"] is False


def test_required_event_without_artifact_identity_fails_qualification(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path)
    database = tmp_path / "state.sqlite3"
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT event_json FROM events WHERE run_id = ? AND sequence = 2",
            (run_id,),
        ).fetchone()
        assert row is not None
        payload = json.loads(row[0])
        assert payload["type"] == EventType.CONTEXT_BUILT.value
        payload["payload"].pop("artifact_id")
        connection.execute(
            "UPDATE events SET event_json = ? WHERE run_id = ? AND sequence = 2",
            (json.dumps(payload), run_id),
        )

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    assert qualification["qualified"] is False
    artifact_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "agent_visible_artifacts"
    )
    assert artifact_check["passed"] is False
    assert artifact_check["details"]["missing_required_artifact_events"] == [
        EventType.CONTEXT_BUILT.value
    ]


def test_trace_without_approved_execution_plan_is_not_qualified(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path, write_execution_plan=False)

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    assert qualification["qualified"] is False
    plan_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "approved_execution_plan"
    )
    assert plan_check["passed"] is False
    assert plan_check["details"]["plan_present"] is False


def test_execution_plan_schedule_row_must_match_run_manifest(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path)
    plan_path = _execution_plan_path_for_test(tmp_path, HASH)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["schedule"][0]["dataset_role"] = DatasetRole.CORE_CROSS_REPO.value
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    assert qualification["qualified"] is False
    plan_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "approved_execution_plan"
    )
    assert plan_check["passed"] is False


def test_execution_plan_private_evaluator_identity_must_match_manifest(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path)
    plan_path = _execution_plan_path_for_test(tmp_path, HASH)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["tasks"][0]["private_spec_hash"] = "sha256:" + ("f" * 64)
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)

    assert qualification["qualified"] is False
    plan_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "approved_execution_plan"
    )
    assert plan_check["passed"] is False


def test_noncanonical_copy_of_dataset_package_is_not_qualified(tmp_path) -> None:
    run_id, _, _ = _terminal_trace(tmp_path)
    copied_task = tmp_path / "copied-task-package"
    shutil.copytree(MEMORY_TASK, copied_task)

    qualification = qualify_run(run_id, task_dir=copied_task, root=tmp_path)

    assert qualification["qualified"] is False
    provenance_check = next(
        check
        for check in qualification["checks"]
        if check["check_id"] == "frozen_campaign_provenance"
    )
    assert provenance_check["passed"] is False
    assert provenance_check["details"]["canonical_package"] is False


def test_source_event_changed_after_qualification_cannot_be_reviewed(tmp_path) -> None:
    run_id, _, failure_id = _terminal_trace(tmp_path)
    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)
    database = tmp_path / "state.sqlite3"
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT event_json FROM events WHERE run_id = ? AND sequence = 1",
            (run_id,),
        ).fetchone()
        assert row is not None
        event = json.loads(row[0])
        event["actor"] = "tampered-after-qualification"
        connection.execute(
            "UPDATE events SET event_json = ? WHERE run_id = ? AND sequence = 1",
            (json.dumps(event), run_id),
        )

    assert qualification["source_evidence_hash"] != calculate_source_evidence_hash(
        run_id,
        root=tmp_path,
    )
    with pytest.raises(ContractError, match="source evidence changed"):
        review_failure(failure_id, root=tmp_path, approve=True)


def test_execution_plan_changed_after_qualification_cannot_be_reviewed(tmp_path) -> None:
    run_id, _, failure_id = _terminal_trace(tmp_path)
    qualification = qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)
    plan_path = _execution_plan_path_for_test(tmp_path, qualification["execution_hash"])
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["audit_note"] = "changed after qualification"
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    with pytest.raises(ContractError, match="source evidence changed"):
        review_failure(failure_id, root=tmp_path, approve=True)


def test_failure_symptoms_do_not_expose_hidden_check_id(tmp_path) -> None:
    package = load_task_package(MEMORY_TASK)
    hidden_id = package.private.hidden_checks[0].id
    result = _result("run_hidden_id_sanitization", resolved=False, hidden_check_id=hidden_id)

    record = classify_failure(result, package.public.split, root=tmp_path)

    assert record is not None
    assert record.observed_symptoms == ["hidden:fail"]
    assert hidden_id not in record.model_dump_json()


def test_unqualified_failure_cannot_enter_review_history(tmp_path) -> None:
    _, _, failure_id = _terminal_trace(tmp_path)
    failure_path = tmp_path / "failures" / "dev-train" / f"{failure_id}.json"
    original = failure_path.read_bytes()

    with pytest.raises(ContractError, match="qualification is unavailable"):
        review_failure(failure_id, root=tmp_path, approve=True)

    assert failure_path.read_bytes() == original
    assert not failure_path.with_suffix(".review-history.jsonl").exists()


def test_failure_record_changed_after_qualification_cannot_be_reviewed(tmp_path) -> None:
    run_id, _, failure_id = _terminal_trace(tmp_path)
    qualify_run(run_id, task_dir=MEMORY_TASK, root=tmp_path)
    failure_path = tmp_path / "failures" / "dev-train" / f"{failure_id}.json"
    record = json.loads(failure_path.read_text(encoding="utf-8"))
    record["confidence"] = 0.5
    failure_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    with pytest.raises(ContractError, match="changed after trace qualification"):
        review_failure(failure_id, root=tmp_path, approve=True)
