"""Deterministic qualification of live no-memory development traces."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from patchloop.contracts import (
    DatasetRole,
    EventType,
    ExperimentPurpose,
    FailureRecord,
    MemoryCondition,
    RunOutcomeKind,
    RunResult,
    VerdictState,
)
from patchloop.dataset import (
    find_dataset_entry,
    load_dataset_manifest,
    require_frozen_dataset,
)
from patchloop.errors import ContractError, RecoveryError
from patchloop.runtime import calculate_model_cost, repository_root, runtime_root
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_text

QUALIFICATION_SCHEMA_VERSION = "trace-qualification-v1"

_TERMINAL_EVENTS = {EventType.RUN_COMPLETED, EventType.RUN_FAILED}
_AGENT_VISIBLE_ARTIFACT_EVENTS = {
    EventType.RUN_STARTED,
    EventType.CONTEXT_BUILT,
    EventType.MEMORY_RETRIEVED,
    EventType.MODEL_CALLED,
    EventType.TOOL_SUCCEEDED,
    EventType.TOOL_FAILED,
}
_REQUIRED_ARTIFACT_EVENTS = {
    EventType.RUN_STARTED,
    EventType.CONTEXT_BUILT,
    EventType.MODEL_CALLED,
}
_SOURCE_EVIDENCE_SCHEMA_VERSION = "trace-source-evidence-v1"


def _runtime_root(root: str | Path | None) -> Path:
    return Path(root) if root is not None else runtime_root()


def qualification_path(run_id: str, *, root: str | Path | None = None) -> Path:
    return _runtime_root(root) / "qualifications" / f"{run_id}.json"


def _checked_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != QUALIFICATION_SCHEMA_VERSION:
        raise ContractError("unsupported trace qualification schema")
    source_hash = payload.get("source_evidence_hash")
    if (
        not isinstance(source_hash, str)
        or not source_hash.startswith("sha256:")
        or len(source_hash) != 71
    ):
        raise ContractError("trace qualification has no source evidence hash")
    recorded_hash = payload.get("qualification_hash")
    if not isinstance(recorded_hash, str):
        raise ContractError("trace qualification has no content hash")
    unhashed = {key: value for key, value in payload.items() if key != "qualification_hash"}
    if sha256_text(canonical_json(unhashed)) != recorded_hash:
        raise ContractError("trace qualification content hash mismatch")
    return payload


def load_trace_qualification(
    run_id: str,
    *,
    root: str | Path | None = None,
) -> dict[str, Any]:
    path = qualification_path(run_id, root=root)
    if not path.is_file():
        raise ContractError(f"trace qualification is unavailable: {run_id}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid trace qualification: {run_id}") from exc
    if not isinstance(payload, dict) or payload.get("run_id") != run_id:
        raise ContractError("trace qualification run identity mismatch")
    return _checked_payload(payload)


def _result_for_run(state: StateStore, run_id: str) -> RunResult | None:
    matches = [row for row in state.list_runs() if row["run_id"] == run_id]
    if len(matches) != 1:
        return None
    raw = matches[0]["result"]
    return RunResult.model_validate(raw) if raw is not None else None


def _failure_records(root: Path, split: str, run_id: str) -> list[FailureRecord]:
    source = root / "failures" / split
    records: list[FailureRecord] = []
    for path in sorted(source.glob("*.json")) if source.is_dir() else []:
        try:
            record = FailureRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if record.run_id == run_id:
            records.append(record)
    return records


def _execution_plan_path(root: Path, execution_hash: str) -> Path:
    digest = execution_hash.removeprefix("sha256:")
    return root / "experiments" / "plans" / f"{digest}.json"


def _load_execution_plan(
    *,
    root: Path,
    manifest,
) -> tuple[dict[str, Any] | None, bytes | None]:
    experiment = manifest.experiment
    if experiment is None:
        return None, None
    path = _execution_plan_path(root, experiment.execution_hash)
    try:
        raw = path.read_bytes()
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None, None
    if not isinstance(payload, dict):
        return None, raw
    return payload, raw


def _execution_plan_matches(
    *,
    plan: dict[str, Any] | None,
    manifest,
) -> bool:
    experiment = manifest.experiment
    if experiment is None or plan is None:
        return False
    approval = plan.get("approval")
    dataset = plan.get("dataset")
    schedule = plan.get("schedule")
    suite = plan.get("suite")
    tasks = plan.get("tasks")
    if (
        plan.get("schema_version") != "experiment-execution-plan-v1"
        or plan.get("ready") is not True
        or plan.get("blockers") != []
        or not isinstance(approval, dict)
        or approval.get("invocation_approve_live_cost") is not True
        or approval.get("invocation_approved_execution_hash")
        != experiment.execution_hash
        or approval.get("matches_execution_hash") is not True
        or plan.get("experiment_id") != experiment.experiment_id
        or plan.get("purpose") != experiment.purpose.value
        or plan.get("suite_hash") != experiment.suite_hash
        or plan.get("execution_hash") != experiment.execution_hash
        or not isinstance(suite, dict)
        or suite.get("experiment_id") != experiment.experiment_id
        or suite.get("purpose") != experiment.purpose.value
        or not isinstance(dataset, dict)
        or dataset.get("manifest_hash") != experiment.dataset_manifest_hash
        or not isinstance(schedule, list)
        or not isinstance(tasks, list)
    ):
        return False
    matching_tasks = [
        row
        for row in tasks
        if isinstance(row, dict) and row.get("task_id") == manifest.task_id
    ]
    if len(matching_tasks) != 1:
        return False
    task = matching_tasks[0]
    task_matches = bool(
        task.get("task_version") == manifest.task_version
        and task.get("public_spec_hash") == manifest.public_spec_hash
        and task.get("private_spec_hash") == manifest.private_spec_hash
        and task.get("base_commit") == manifest.base_commit
        and task.get("evaluator_image_digest") == manifest.evaluator_image_digest
        and task.get("evaluator_image_digest") == manifest.agent_image_digest
    )
    if not task_matches:
        return False
    matching_rows = [
        row
        for row in schedule
        if isinstance(row, dict)
        and row.get("schedule_row_id") == experiment.schedule_row_id
    ]
    if len(matching_rows) != 1:
        return False
    row = matching_rows[0]
    return bool(
        row.get("order") == experiment.schedule_order
        and row.get("task_id") == manifest.task_id
        and row.get("dataset_role")
        == (
            experiment.dataset_role.value
            if experiment.dataset_role is not None
            else None
        )
        and row.get("condition") == manifest.memory.condition.value
        and row.get("repetition") == experiment.repetition
    )


def _artifact_evidence(
    *,
    root: Path,
    events,
    private_tokens: set[str],
) -> tuple[bool, int, int, list[dict[str, Any]], list[str]]:
    """Return integrity, scan counts, canonical evidence, and missing identities.

    Private token values are deliberately never returned or persisted.
    """

    artifact_root = (root / "artifacts").resolve()
    texts = [canonical_json(event.payload) for event in events]
    scanned = 0
    integrity = True
    evidence: list[dict[str, Any]] = []
    missing_identities: list[str] = []
    for event in events:
        if event.type not in _AGENT_VISIBLE_ARTIFACT_EVENTS:
            continue
        raw_path = event.payload.get("artifact_path")
        raw_id = event.payload.get("artifact_id")
        path_present = isinstance(raw_path, str) and bool(raw_path.strip())
        id_present = isinstance(raw_id, str) and bool(raw_id.strip())
        if event.type in _REQUIRED_ARTIFACT_EVENTS and not (
            path_present and id_present
        ):
            integrity = False
            missing_identities.append(event.type.value)
        if not path_present:
            continue
        if not id_present:
            integrity = False
        path = Path(raw_path).resolve()
        item: dict[str, Any] = {
            "event_id": event.event_id,
            "artifact_id": raw_id if id_present else None,
            "content_hash": None,
            "size_bytes": None,
        }
        try:
            relative = path.relative_to(artifact_root)
        except ValueError:
            integrity = False
            evidence.append(item)
            continue
        if not path.is_file():
            integrity = False
            evidence.append(item)
            continue
        parts = relative.parts
        if (
            len(parts) != 4
            or parts[0:2] != ("objects", "sha256")
            or len(parts[2]) != 2
            or len(parts[3]) != 62
        ):
            integrity = False
            evidence.append(item)
            continue
        try:
            content = path.read_bytes()
        except OSError:
            integrity = False
            evidence.append(item)
            continue
        expected_hash = f"sha256:{parts[2]}{parts[3]}"
        actual_hash = sha256_bytes(content)
        item["content_hash"] = actual_hash
        item["size_bytes"] = len(content)
        if actual_hash != expected_hash:
            integrity = False
        try:
            texts.append(content.decode("utf-8"))
        except UnicodeDecodeError:
            integrity = False
        evidence.append(item)
        scanned += 1

    generic_markers = {
        "private.yaml",
        "reference.patch",
        ".patchloop-hidden",
    }
    lower_markers = {marker.lower() for marker in generic_markers}
    lower_markers.update(token.lower() for token in private_tokens if token)
    matches = sum(
        1
        for text in texts
        for marker in lower_markers
        if marker and marker in text.lower()
    )
    return integrity, scanned, matches, evidence, sorted(missing_identities)


def calculate_source_evidence_hash(
    run_id: str,
    *,
    root: str | Path | None = None,
    require_valid_plan: bool = True,
) -> str:
    """Hash the current durable sources behind a trace qualification.

    Only hashes are returned; artifact, plan, and trace contents are never copied
    into the qualification artifact.
    """

    run_root = _runtime_root(root)
    state = StateStore(run_root / "state.sqlite3")
    try:
        manifest = state.get_manifest(run_id)
        events = state.list_events(run_id)
        checkpoints = state.list_checkpoints(run_id)
        result = _result_for_run(state, run_id)
    except (RecoveryError, ValueError) as exc:
        raise ContractError(f"source evidence is unavailable: {run_id}") from exc
    plan, plan_bytes = _load_execution_plan(root=run_root, manifest=manifest)
    if require_valid_plan and not _execution_plan_matches(plan=plan, manifest=manifest):
        raise ContractError("approved execution plan is unavailable or no longer matches")
    _, _, _, artifacts, _ = _artifact_evidence(
        root=run_root,
        events=events,
        private_tokens=set(),
    )
    persisted_result_path = run_root / "artifacts" / "runs" / run_id / "result.json"
    try:
        persisted_result_hash = sha256_bytes(persisted_result_path.read_bytes())
    except OSError:
        persisted_result_hash = None
    snapshot = {
        "schema_version": _SOURCE_EVIDENCE_SCHEMA_VERSION,
        "manifest": manifest.model_dump(mode="json"),
        "events": [event.model_dump(mode="json") for event in events],
        "checkpoints": [
            checkpoint.model_dump(mode="json") for checkpoint in checkpoints
        ],
        "result": result.model_dump(mode="json") if result is not None else None,
        "persisted_result_hash": persisted_result_hash,
        "agent_visible_artifacts": artifacts,
        "execution_plan_hash": (
            sha256_bytes(plan_bytes) if plan_bytes is not None else None
        ),
    }
    return sha256_text(canonical_json(snapshot))


def qualify_run(
    run_id: str,
    *,
    task_dir: str | Path,
    dataset_manifest_path: str | Path | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Qualify one terminal run and persist an immutable, private-safe artifact."""

    run_root = _runtime_root(root)
    state = StateStore(run_root / "state.sqlite3")
    try:
        manifest = state.get_manifest(run_id)
    except RecoveryError as exc:
        raise ContractError(f"run manifest is unavailable: {run_id}") from exc
    package = load_task_package(task_dir)
    events = state.list_events(run_id)
    checkpoints = state.list_checkpoints(run_id)
    result = _result_for_run(state, run_id)

    checks: list[dict[str, Any]] = []

    def add(check_id: str, passed: bool, **details: Any) -> bool:
        checks.append({"check_id": check_id, "passed": passed, "details": details})
        return passed

    task_identity = (
        manifest.task_id == package.public.task_id
        and manifest.task_version == package.public.task_version
        and manifest.public_spec_hash == package.public_spec_hash
        and manifest.private_spec_hash == package.private_spec_hash
    )
    add("task_identity", task_identity)

    contiguous = [event.sequence for event in events] == list(range(1, len(events) + 1))
    add("contiguous_events", contiguous, event_count=len(events))

    terminals = [event for event in events if event.type in _TERMINAL_EVENTS]
    terminal_ok = (
        len(terminals) == 1
        and bool(events)
        and events[-1].event_id == terminals[0].event_id
    )
    terminal_type = terminals[0].type.value if len(terminals) == 1 else None
    add(
        "single_terminal_event",
        terminal_ok,
        terminal_count=len(terminals),
        terminal_type=terminal_type,
    )

    event_types = {event.type for event in events}
    required_missing = sorted(
        event_type.value
        for event_type in {
            EventType.RUN_STARTED,
            EventType.CONTEXT_BUILT,
            EventType.MODEL_CALLED,
            EventType.CHECKPOINT_SAVED,
        }
        if event_type not in event_types
    )
    checkpoint_ids = {
        event.payload.get("checkpoint_id")
        for event in events
        if event.type == EventType.CHECKPOINT_SAVED
    }
    durable_ids = {checkpoint.checkpoint_id for checkpoint in checkpoints}
    required_trace = not required_missing and bool(checkpoints) and checkpoint_ids.issubset(
        durable_ids
    )
    add(
        "required_trace_evidence",
        required_trace,
        missing_event_types=required_missing,
        checkpoint_count=len(checkpoints),
    )

    no_memory = manifest.memory.condition == MemoryCondition.NO_MEMORY
    no_retrieval = EventType.MEMORY_RETRIEVED not in event_types
    no_index = manifest.memory.index_version is None and manifest.memory.index_hash is None
    no_memory_ok = no_memory and no_retrieval and no_index
    add(
        "no_memory_boundary",
        no_memory_ok,
        condition=manifest.memory.condition.value,
        retrieval_event_count=sum(
            event.type == EventType.MEMORY_RETRIEVED for event in events
        ),
        index_declared=not no_index,
    )

    provider_ok = manifest.model.provider == "openai"
    add("live_openai_provider", provider_ok, provider=manifest.model.provider)
    model_contract_ok = (
        manifest.model.model_id == "gpt-5.6-terra"
        and manifest.model.reasoning_effort == "medium"
        and manifest.model.reasoning_mode == "standard"
        and manifest.model.service_tier == "default"
        and manifest.model.max_output_tokens == 4096
    )
    add(
        "frozen_model_contract",
        model_contract_ok,
        model_id=manifest.model.model_id,
        reasoning_effort=manifest.model.reasoning_effort,
        reasoning_mode=manifest.model.reasoning_mode,
        service_tier=manifest.model.service_tier,
        max_output_tokens=manifest.model.max_output_tokens,
    )
    fault_ok = manifest.fault.type == "none" and EventType.FAULT_INJECTED not in event_types
    add("fault_free", fault_ok, fault=manifest.fault.type)

    try:
        dataset, dataset_hash, _ = require_frozen_dataset(dataset_manifest_path)
        dataset_frozen = True
    except ContractError:
        dataset, dataset_hash, _ = load_dataset_manifest(dataset_manifest_path)
        dataset_frozen = False
    try:
        dataset_entry = find_dataset_entry(
            task_id=manifest.task_id,
            task_version=manifest.task_version,
            public_spec_hash=manifest.public_spec_hash,
            manifest_path=dataset_manifest_path,
        )
    except ContractError:
        dataset_entry = None
    experiment = manifest.experiment
    purpose_roles = {
        ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT: {
            DatasetRole.DEVELOPMENT_VALIDATION
        },
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY: {
            DatasetRole.MEMORY_DEVELOPMENT
        },
        ExperimentPurpose.CORE: {
            DatasetRole.CORE_SAME_REPO,
            DatasetRole.CORE_CROSS_REPO,
        },
    }
    purpose_role_ok = bool(
        experiment is not None
        and dataset_entry is not None
        and dataset_entry.role in purpose_roles.get(experiment.purpose, set())
    )
    canonical_package_ok = bool(
        dataset_entry is not None
        and Path(package.root).resolve()
        == (repository_root() / dataset_entry.path).resolve()
    )
    private_evaluator_ok = bool(
        dataset_entry is not None
        and dataset_entry.private_spec_hash == package.private_spec_hash
        and package.private_spec_hash == manifest.private_spec_hash
    )
    provenance_ok = (
        dataset_frozen
        and dataset_entry is not None
        and experiment is not None
        and experiment.dataset_manifest_hash == dataset_hash
        and experiment.dataset_role == dataset_entry.role
        and purpose_role_ok
        and canonical_package_ok
        and private_evaluator_ok
    )
    add(
        "frozen_campaign_provenance",
        provenance_ok,
        dataset_status=dataset.status,
        manifest_hash_matches=bool(
            experiment is not None and experiment.dataset_manifest_hash == dataset_hash
        ),
        dataset_role=dataset_entry.role.value if dataset_entry is not None else None,
        purpose=experiment.purpose.value if experiment is not None else None,
        canonical_package=canonical_package_ok,
        private_evaluator_matches=private_evaluator_ok,
    )

    execution_plan, execution_plan_bytes = _load_execution_plan(
        root=run_root,
        manifest=manifest,
    )
    execution_plan_ok = _execution_plan_matches(
        plan=execution_plan,
        manifest=manifest,
    )
    add(
        "approved_execution_plan",
        execution_plan_ok,
        plan_present=execution_plan is not None,
        plan_content_hash=(
            sha256_bytes(execution_plan_bytes)
            if execution_plan_bytes is not None
            else None
        ),
        ready=bool(execution_plan is not None and execution_plan.get("ready") is True),
        approval_matches=bool(
            execution_plan is not None
            and isinstance(execution_plan.get("approval"), dict)
            and execution_plan["approval"].get("matches_execution_hash") is True
        ),
    )

    expected_image_digest = (
        package.environment.image_digest if package.environment is not None else None
    )
    sandbox_ok = (
        package.environment is not None
        and manifest.sandbox_backend == "docker"
        and manifest.agent_image_digest == expected_image_digest
        and manifest.evaluator_image_digest == expected_image_digest
    )
    add(
        "sandbox_provenance",
        sandbox_ok,
        sandbox_backend=manifest.sandbox_backend,
        task_environment_declared=package.environment is not None,
        agent_image_matches=manifest.agent_image_digest == expected_image_digest,
        evaluator_image_matches=manifest.evaluator_image_digest == expected_image_digest,
    )

    private_tokens = {check.id for check in package.private.hidden_checks}
    if package.private.reference_patch.sha256:
        private_tokens.add(package.private.reference_patch.sha256)
    private_tokens.update(artifact.path for artifact in package.private.hidden_artifacts)
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        private_tokens.add(api_key)
    (
        artifact_integrity,
        artifact_count,
        leak_matches,
        _,
        missing_artifact_identities,
    ) = _artifact_evidence(
        root=run_root,
        events=events,
        private_tokens=private_tokens,
    )
    add(
        "agent_visible_artifacts",
        artifact_integrity,
        scanned_artifact_count=artifact_count,
        missing_required_artifact_events=missing_artifact_identities,
    )
    leakage_ok = leak_matches == 0
    add("public_private_boundary", leakage_ok, private_match_count=leak_matches)

    model_events = [event for event in events if event.type == EventType.MODEL_CALLED]
    tool_events = [event for event in events if event.type == EventType.TOOL_CALLED]
    expected_usage = {
        "input_tokens": sum(int(event.payload.get("input_tokens", 0)) for event in model_events),
        "cached_input_tokens": sum(
            int(event.payload.get("cached_input_tokens", 0)) for event in model_events
        ),
        "cache_write_input_tokens": sum(
            int(event.payload.get("cache_write_input_tokens", 0))
            for event in model_events
        ),
        "output_tokens": sum(
            int(event.payload.get("output_tokens", 0)) for event in model_events
        ),
        "model_calls": len(model_events),
        "tool_calls": len(tool_events),
    }
    usage_matches = bool(
        result is not None
        and all(
            getattr(result.usage, field) == value
            for field, value in expected_usage.items()
        )
        and abs(
            result.usage.model_cost_usd
            - calculate_model_cost(result.usage, manifest.model)
        )
        <= 1e-9
    )
    add(
        "usage_reconciliation",
        usage_matches,
        model_event_count=len(model_events),
        tool_event_count=len(tool_events),
    )

    persisted_result_path = (
        run_root / "artifacts" / "runs" / run_id / "result.json"
    )
    try:
        persisted_result = RunResult.model_validate_json(
            persisted_result_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        persisted_result = None
    persisted_result_ok = bool(
        result is not None and persisted_result is not None and persisted_result == result
    )
    add("persisted_result", persisted_result_ok, artifact_present=persisted_result is not None)

    pilot_tool_ok = bool(
        experiment is None
        or experiment.purpose != ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT
        or tool_events
    )
    add(
        "pilot_tool_loop",
        pilot_tool_ok,
        required=bool(
            experiment is not None
            and experiment.purpose
            == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT
        ),
        tool_event_count=len(tool_events),
    )

    evaluation_reached = bool(result is not None and result.evaluation_status == "completed")
    terminal_verdicts = bool(
        result is not None
        and all(
            value in {VerdictState.PASS, VerdictState.FAIL}
            for value in result.verdicts.model_dump().values()
        )
    )
    if evaluation_reached:
        evaluation_ok = bool(
            result is not None
            and result.official
            and terminal_type == EventType.RUN_COMPLETED.value
            and terminal_verdicts
            and result.verifier_results
            and all(item.run_id == run_id for item in result.verifier_results)
        )
    else:
        evaluation_ok = bool(
            result is not None
            and terminal_type == EventType.RUN_FAILED.value
            and result.outcome_kind
            in {RunOutcomeKind.AGENT_FAILURE, RunOutcomeKind.INFRASTRUCTURE_ERROR}
        )
    add(
        "terminal_result_integrity",
        evaluation_ok,
        result_present=result is not None,
        evaluation_reached=evaluation_reached,
        official=bool(result is not None and result.official),
        verdicts_terminal=terminal_verdicts,
    )

    outcome = (
        result.outcome_kind
        if result is not None
        else RunOutcomeKind.INFRASTRUCTURE_ERROR
    )
    if evaluation_reached and not terminal_verdicts:
        outcome = RunOutcomeKind.INFRASTRUCTURE_ERROR
    records = _failure_records(run_root, package.public.split, run_id)
    tagged_ids = [
        event.payload.get("failure_id")
        for event in events
        if event.type == EventType.FAILURE_TAGGED
    ]
    failure_expected = outcome in {
        RunOutcomeKind.TASK_FAILURE,
        RunOutcomeKind.AGENT_FAILURE,
    }
    if failure_expected:
        failure_linked = (
            len(records) == 1
            and len(tagged_ids) == 1
            and tagged_ids[0] == records[0].failure_id
        )
    else:
        failure_linked = not records and not tagged_ids
    failure_record_id = records[0].failure_id if len(records) == 1 else None
    failure_record_hash = (
        sha256_bytes(
            (
                run_root
                / "failures"
                / package.public.split
                / f"{failure_record_id}.json"
            ).read_bytes()
        )
        if failure_record_id is not None
        else None
    )
    add(
        "failure_record_linkage",
        failure_linked,
        failure_expected=failure_expected,
        failure_record_count=len(records),
        failure_tag_count=len(tagged_ids),
    )

    trace_check_ids = {
        "task_identity",
        "contiguous_events",
        "single_terminal_event",
        "required_trace_evidence",
        "no_memory_boundary",
        "approved_execution_plan",
        "agent_visible_artifacts",
        "usage_reconciliation",
        "persisted_result",
        "pilot_tool_loop",
        "terminal_result_integrity",
        "failure_record_linkage",
    }
    trace_integrity = all(
        check["passed"] for check in checks if check["check_id"] in trace_check_ids
    )
    qualified = all(check["passed"] for check in checks)
    memory_candidate_eligible = bool(
        qualified
        and trace_integrity
        and leakage_ok
        and dataset_entry is not None
        and dataset_entry.role == DatasetRole.MEMORY_DEVELOPMENT
        and experiment is not None
        and experiment.purpose == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY
        and outcome in {RunOutcomeKind.TASK_FAILURE, RunOutcomeKind.AGENT_FAILURE}
    )
    source_evidence_hash = calculate_source_evidence_hash(
        run_id,
        root=run_root,
        require_valid_plan=False,
    )
    payload: dict[str, Any] = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "run_id": run_id,
        "qualified": qualified,
        "trace_integrity_passed": trace_integrity,
        "leakage_scan_passed": leakage_ok,
        "evaluation_reached": evaluation_reached,
        "outcome_kind": outcome.value,
        "purpose": experiment.purpose.value if experiment is not None else None,
        "dataset_role": dataset_entry.role.value if dataset_entry is not None else None,
        "dataset_manifest_hash": dataset_hash,
        "suite_hash": experiment.suite_hash if experiment is not None else None,
        "execution_hash": experiment.execution_hash if experiment is not None else None,
        "schedule_row_id": experiment.schedule_row_id if experiment is not None else None,
        "model_provider": manifest.model.provider,
        "memory_condition": manifest.memory.condition.value,
        "fault_type": manifest.fault.type,
        "memory_candidate_eligible": memory_candidate_eligible,
        "failure_record_id": failure_record_id,
        "failure_record_hash": failure_record_hash,
        "source_evidence_hash": source_evidence_hash,
        "checks": checks,
    }
    payload["qualification_hash"] = sha256_text(canonical_json(payload))

    path = qualification_path(run_id, root=run_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    if path.exists():
        existing = load_trace_qualification(run_id, root=run_root)
        if existing != payload:
            raise ContractError(f"trace qualification is immutable: {run_id}")
    else:
        path.write_text(encoded, encoding="utf-8")
    return payload
