"""Deterministic qualification of live no-memory development traces."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Artifact,
    Budget,
    Checkpoint,
    DatasetRole,
    EventType,
    ExperimentPurpose,
    FailureRecord,
    MemoryCondition,
    Phase,
    RunManifest,
    RunOutcomeKind,
    RunResult,
    RunStatus,
    TaskPackage,
    VerdictState,
)
from patchloop.dataset import (
    find_dataset_entry,
    load_dataset_manifest,
    require_frozen_dataset,
)
from patchloop.errors import ContractError, RecoveryError
from patchloop.runtime import calculate_model_cost, repository_root, runtime_root
from patchloop.sandbox.runner import probe_execution_policy
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import (
    canonical_json,
    safe_relative_path,
    sha256_bytes,
    sha256_text,
)

LEGACY_QUALIFICATION_SCHEMA_VERSION = "trace-qualification-v1"
QUALIFICATION_SCHEMA_VERSION = "trace-qualification-v2"
_SUPPORTED_QUALIFICATION_SCHEMA_VERSIONS = {
    LEGACY_QUALIFICATION_SCHEMA_VERSION,
    QUALIFICATION_SCHEMA_VERSION,
}
_LEGACY_TERRA_MODEL_ID = "gpt-5.6-terra"
_GPT54_MINI_PILOT_MODEL_ID = "gpt-5.4-mini-2026-03-17"
_GPT54_MINI_PILOT_BUDGET = Budget(max_total_tokens=90_000)
_GPT54_MINI_D037_CORRECTIVE_BUDGET = Budget(max_total_tokens=120_000)
_GPT54_MINI_D037_TAIL_RESERVE_BUDGET = Budget(max_total_tokens=200_000)
_GPT54_MINI_HISTORICAL_200K_CAMPAIGN_BUDGET = Budget(
    max_model_calls=21,
    max_total_tokens=200_000,
)
_GPT54_MINI_CAMPAIGN_BUDGET = Budget(
    max_model_calls=21,
    max_total_tokens=250_000,
)
_GPT54_MINI_COMPLETION_BUDGET = Budget(
    max_model_calls=40,
    max_tool_calls=100,
    max_total_tokens=600_000,
    wall_clock_timeout_seconds=1_800,
)
_GPT54_MINI_MEMORY_DEVELOPMENT_BUDGET_PILOT = Budget(
    max_model_calls=40,
    max_tool_calls=100,
    max_total_tokens=480_000,
    wall_clock_timeout_seconds=1_800,
)
_GPT54_MINI_MEMORY_DEVELOPMENT_CORRECTIVE_PILOT = Budget(
    max_model_calls=40,
    max_tool_calls=100,
    max_total_tokens=900_000,
    wall_clock_timeout_seconds=1_800,
)
_GPT54_MINI_MEMORY_DEVELOPMENT_SATURATION_PILOT = Budget(
    max_model_calls=40,
    max_tool_calls=100,
    max_total_tokens=900_000,
    wall_clock_timeout_seconds=1_800,
)
_GPT54_MINI_MEMORY_DEVELOPMENT_REVIEW_EVIDENCE_PILOT = Budget(
    max_model_calls=60,
    max_tool_calls=100,
    max_total_tokens=1_200_000,
    wall_clock_timeout_seconds=1_800,
)
_GPT54_MINI_MEMORY_DEVELOPMENT_COVERAGE_REVIEW_PILOT = Budget(
    max_model_calls=60,
    max_tool_calls=100,
    max_total_tokens=1_200_000,
    wall_clock_timeout_seconds=1_800,
)
_SUPERSEDED_250K_LIVE_EXPERIMENT_IDS = frozenset(
    {"dev-validation-gpt54mini-token-tail-v5-20260730-r1"}
)
_HISTORICAL_MINI_CAMPAIGN_EXPERIMENT_IDS = frozenset(
    {"dev-validation-gpt54mini-campaign-20260730-r1"}
)
_HISTORICAL_MINI_200K_CAMPAIGN_EXPERIMENT_IDS = frozenset(
    {
        "dev-validation-gpt54mini-campaign-20260730-r2",
        "dev-no-memory-20260728",
        "dev-validation-gpt54mini-investigation-v4-20260730-r1",
        "dev-no-memory-v4-20260730-r1",
    }
)
_EXACT_REQUEST_GENERATION_BLOCK_SCHEMA = "model-generation-block-v1"
_COUNTER_GENERATION_BLOCK_SCHEMA = "model-generation-block-v2"
_COUNTER_GENERATION_BLOCK_REASONS = frozenset(
    {
        "model_call_budget_exhausted",
        "tool_call_budget_exhausted",
        "wall_clock_budget_exhausted",
    }
)
_CAMPAIGN_PURPOSES = {
    ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT,
    ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY,
    ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_BUDGET_PILOT,
    ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT,
    ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT,
    ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT,
    ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT,
    ExperimentPurpose.CORE,
}

_TERMINAL_EVENTS = {EventType.RUN_COMPLETED, EventType.RUN_FAILED}
_AGENT_VISIBLE_ARTIFACT_EVENTS = {
    EventType.RUN_STARTED,
    EventType.CONTEXT_BUILT,
    EventType.MEMORY_RETRIEVED,
    EventType.MODEL_CALLED,
    EventType.TOOL_CALLED,
    EventType.PATCH_PREPARED,
    EventType.TOOL_SUCCEEDED,
    EventType.TOOL_FAILED,
}
_REQUIRED_ARTIFACT_EVENTS = {
    EventType.RUN_STARTED,
    EventType.CONTEXT_BUILT,
    EventType.MODEL_CALLED,
}
_SOURCE_EVIDENCE_SCHEMA_VERSION = "trace-source-evidence-v1"
_SOURCE_EVIDENCE_SCHEMA_VERSION_V2 = "trace-source-evidence-v2"
_SOURCE_EVIDENCE_SCHEMA_VERSION_V3 = "trace-source-evidence-v3"
_SOURCE_EVIDENCE_SCHEMA_VERSION_V4 = "trace-source-evidence-v4"
_SOURCE_EVIDENCE_SCHEMA_VERSION_V5 = "trace-source-evidence-v5"
_SOURCE_EVIDENCE_SCHEMA_VERSION_V6 = "trace-source-evidence-v6"
_SOURCE_EVIDENCE_SCHEMA_VERSION_V7 = "trace-source-evidence-v7"
_SOURCE_EVIDENCE_SCHEMA_VERSION_V8 = "trace-source-evidence-v8"
_SOURCE_EVIDENCE_SCHEMA_VERSION_V9 = "trace-source-evidence-v9"
_SOURCE_EVIDENCE_SCHEMA_VERSION_V10 = "trace-source-evidence-v10"
_SOURCE_EVIDENCE_SCHEMA_VERSION_V11 = "trace-source-evidence-v11"
_V8_EVIDENCE_SATURATION_THRESHOLD = 6
_V9_REVIEW_TOOL_RESULT_CHARACTER_LIMIT = 12_000
_EMPTY_DIFF_HASH = sha256_text("")


def _runtime_root(root: str | Path | None) -> Path:
    return Path(root) if root is not None else runtime_root()


def qualification_path(run_id: str, *, root: str | Path | None = None) -> Path:
    return _runtime_root(root) / "qualifications" / f"{run_id}.json"


def _checked_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") not in _SUPPORTED_QUALIFICATION_SCHEMA_VERSIONS:
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


def _normalized_qualification_semantics(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Ignore one historical, semantically neutral v2 detail-shape change."""

    normalized = json.loads(json.dumps(payload))
    normalized.pop("qualification_hash", None)
    checks = normalized.get("checks")
    if not isinstance(checks, list):
        return normalized
    for check in checks:
        if (
            isinstance(check, dict)
            and check.get("check_id") == "terminal_result_integrity"
            and isinstance(check.get("details"), dict)
        ):
            details = check["details"]
            if (
                details.get("model_generation_block_binding_required")
                is False
                and details.get("model_generation_block_binding_valid")
                is True
            ):
                details.pop(
                    "model_generation_block_binding_required",
                    None,
                )
                details.pop(
                    "model_generation_block_binding_valid",
                    None,
                )
    return normalized


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


def _v2_checkpoint_event_integrity(
    checkpoints,
    events,
) -> tuple[bool, dict[str, Any]]:
    """Require a bijection between durable checkpoints and their trace events."""

    checkpoint_events = [event for event in events if event.type == EventType.CHECKPOINT_SAVED]
    durable_by_id = {checkpoint.checkpoint_id: checkpoint for checkpoint in checkpoints}
    events_by_id: dict[str, list[Any]] = {}
    invalid_id_sequences: list[int] = []
    for event in checkpoint_events:
        checkpoint_id = event.payload.get("checkpoint_id")
        if not isinstance(checkpoint_id, str):
            invalid_id_sequences.append(event.sequence)
            continue
        events_by_id.setdefault(checkpoint_id, []).append(event)

    durable_ids = set(durable_by_id)
    event_ids = set(events_by_id)
    missing_event_ids = sorted(durable_ids - event_ids)
    orphan_event_ids = sorted(event_ids - durable_ids)
    duplicate_event_ids = sorted(
        checkpoint_id
        for checkpoint_id, matching_events in events_by_id.items()
        if len(matching_events) != 1
    )
    payload_mismatches: list[dict[str, Any]] = []
    for checkpoint_id in sorted(durable_ids & event_ids):
        matching_events = events_by_id[checkpoint_id]
        if len(matching_events) != 1:
            continue
        event = matching_events[0]
        checkpoint = durable_by_id[checkpoint_id]
        mismatched_fields: list[str] = []
        through_sequence = event.payload.get("through_sequence")
        if type(through_sequence) is not int or through_sequence != checkpoint.through_sequence:
            mismatched_fields.append("through_sequence")
        worktree_diff_hash = event.payload.get("worktree_diff_hash")
        if (
            not isinstance(worktree_diff_hash, str)
            or worktree_diff_hash != checkpoint.worktree_diff_hash
        ):
            mismatched_fields.append("worktree_diff_hash")
        if mismatched_fields:
            payload_mismatches.append(
                {
                    "checkpoint_id": checkpoint_id,
                    "fields": mismatched_fields,
                }
            )

    passed = bool(checkpoints) and not any(
        (
            len(checkpoint_events) != len(checkpoints),
            invalid_id_sequences,
            missing_event_ids,
            orphan_event_ids,
            duplicate_event_ids,
            payload_mismatches,
        )
    )
    return passed, {
        "checkpoint_event_count": len(checkpoint_events),
        "missing_checkpoint_event_ids": missing_event_ids,
        "orphan_checkpoint_event_ids": orphan_event_ids,
        "duplicate_checkpoint_event_ids": duplicate_event_ids,
        "invalid_checkpoint_event_sequences": invalid_id_sequences,
        "checkpoint_payload_mismatches": payload_mismatches,
    }


def _runtime_contract_content_hash(events) -> str | None:
    candidates = [
        event
        for event in events
        if event.type == EventType.RUN_STARTED
        and isinstance(event.payload.get("artifact_path"), str)
    ]
    if len(candidates) != 1:
        return None
    try:
        return sha256_bytes(Path(candidates[0].payload["artifact_path"]).read_bytes())
    except OSError:
        return None


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
    environment = plan.get("environment")
    pilot_qualification = plan.get("pilot_qualification")
    schedule = plan.get("schedule")
    suite = plan.get("suite")
    tasks = plan.get("tasks")
    pricing = plan.get("pricing")
    runtime_contract = plan.get("runtime_contract")
    schedule_hash = plan.get("schedule_hash")
    if (
        plan.get("schema_version") != "experiment-execution-plan-v1"
        or plan.get("ready") is not True
        or plan.get("blockers") != []
        or not isinstance(approval, dict)
        or approval.get("invocation_approve_live_cost") is not True
        or approval.get("invocation_approved_execution_hash") != experiment.execution_hash
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
        or not isinstance(environment, dict)
        or not isinstance(environment.get("git"), dict)
        or not isinstance(environment.get("docker"), dict)
        or not isinstance(environment.get("openai_sdk"), dict)
        or not isinstance(pilot_qualification, dict)
        or not isinstance(schedule, list)
        or not isinstance(schedule_hash, str)
        or schedule_hash != sha256_text(canonical_json(schedule))
        or plan.get("expected_runs") != len(schedule)
        or not isinstance(tasks, list)
    ):
        return False
    try:
        # Keep post-run qualification independent from the plan's own declared
        # suite hash. Re-parse the complete frozen suite, require its canonical
        # payload, and recalculate the hash using the same contract as preflight.
        from patchloop.evals.runner import (
            ExperimentSuite,
            _corrective_runtime_contract,
            _diagnostic_fault,
            _execution_hash,
            _make_schedule,
            _pricing_contract_matches,
            _suite_hash,
            _suite_payload,
        )

        parsed_suite = ExperimentSuite.model_validate(suite)
        normalized_suite = _suite_payload(parsed_suite)
        completion_plan_matches = True
        if (
            (
                parsed_suite.purpose
                == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT
                and parsed_suite.budget == _GPT54_MINI_COMPLETION_BUDGET
            )
            or (
                parsed_suite.purpose
                == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_BUDGET_PILOT
                and parsed_suite.budget
                == _GPT54_MINI_MEMORY_DEVELOPMENT_BUDGET_PILOT
            )
            or (
                parsed_suite.purpose
                == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT
                and parsed_suite.budget
                == _GPT54_MINI_MEMORY_DEVELOPMENT_CORRECTIVE_PILOT
            )
            or (
                parsed_suite.purpose
                == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT
                and parsed_suite.budget
                == _GPT54_MINI_MEMORY_DEVELOPMENT_SATURATION_PILOT
            )
            or (
                parsed_suite.purpose
                == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT
                and parsed_suite.budget
                == _GPT54_MINI_MEMORY_DEVELOPMENT_REVIEW_EVIDENCE_PILOT
            )
            or (
                parsed_suite.purpose
                == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT
                and parsed_suite.budget
                == _GPT54_MINI_MEMORY_DEVELOPMENT_COVERAGE_REVIEW_PILOT
            )
        ):
            if (
                len(tasks) != len(parsed_suite.tasks)
                or any(not isinstance(task, dict) for task in tasks)
                or [task.get("task") for task in tasks] != parsed_suite.tasks
                or len({task.get("task_id") for task in tasks}) != len(tasks)
            ):
                return False
            expected_schedule, expected_schedule_hash = _make_schedule(
                parsed_suite,
                tasks,
            )
            completion_plan_matches = bool(
                canonical_json(schedule) == canonical_json(expected_schedule)
                and schedule_hash == expected_schedule_hash
                and plan.get("expected_runs") == len(expected_schedule)
            )
        expected_execution_hash = _execution_hash(
            parsed_suite,
            dataset=dataset,
            task_rows=tasks,
            schedule_hash=schedule_hash,
            git_state=environment["git"],
            docker_state=environment["docker"],
            openai_sdk=environment["openai_sdk"],
            pilot_qualification=pilot_qualification,
            runtime_contract=(
                _corrective_runtime_contract(
                    parsed_suite,
                    harness_git_commit=environment["git"].get(
                        "commit"
                    ),
                )
            ),
        )
    except (ImportError, KeyError, TypeError, ValueError):
        return False
    expected_runtime_contract = _corrective_runtime_contract(
        parsed_suite,
        harness_git_commit=environment["git"].get("commit"),
    )
    corrective_runtime = bool(expected_runtime_contract is not None)
    runtime_pair_matches = bool(
        (
            manifest.tool_schema_version == "v4"
            and manifest.context_policy_version == "phase-evidence-v7"
            and isinstance(expected_runtime_contract, dict)
            and expected_runtime_contract.get("schema_version")
            == "corrective-runtime-contract-v1"
            and expected_runtime_contract.get("context_policy_version")
            == "phase-evidence-v7"
        )
        or (
            manifest.tool_schema_version == "v4"
            and manifest.context_policy_version == "phase-evidence-v8"
            and isinstance(expected_runtime_contract, dict)
            and expected_runtime_contract.get("schema_version")
            == "corrective-runtime-contract-v2"
            and expected_runtime_contract.get("context_policy_version")
            == "phase-evidence-v8"
        )
        or (
            manifest.tool_schema_version == "v4"
            and manifest.context_policy_version == "phase-evidence-v9"
            and isinstance(expected_runtime_contract, dict)
            and expected_runtime_contract.get("schema_version")
            == "corrective-runtime-contract-v3"
            and expected_runtime_contract.get("context_policy_version")
            == "phase-evidence-v9"
        )
        or (
            manifest.tool_schema_version == "v5"
            and manifest.context_policy_version == "phase-evidence-v10"
            and isinstance(expected_runtime_contract, dict)
            and expected_runtime_contract.get("schema_version")
            == "corrective-runtime-contract-v4"
            and expected_runtime_contract.get("context_policy_version")
            == "phase-evidence-v10"
        )
    )
    runtime_contract_matches = bool(
        (
            corrective_runtime
            and isinstance(runtime_contract, dict)
            and canonical_json(runtime_contract)
            == canonical_json(expected_runtime_contract)
            and runtime_pair_matches
            and manifest.harness_git_commit
            == expected_runtime_contract["harness_git_commit"]
        )
        or (not corrective_runtime and runtime_contract is None)
    )
    pricing_contract_matches = bool(
        not corrective_runtime
        or _pricing_contract_matches(
            parsed_suite,
            pricing,
            schedule_size=len(schedule),
        )
    )
    suite_contract_matches = bool(
        canonical_json(suite) == canonical_json(normalized_suite)
        and _suite_hash(parsed_suite) == experiment.suite_hash
        and expected_execution_hash == experiment.execution_hash
        and parsed_suite.model == manifest.model.provider
        and parsed_suite.model_id == manifest.model.model_id
        and parsed_suite.reasoning_effort == manifest.model.reasoning_effort
        and parsed_suite.reasoning_mode == manifest.model.reasoning_mode
        and parsed_suite.service_tier == manifest.model.service_tier
        and parsed_suite.max_output_tokens == manifest.model.max_output_tokens
        and parsed_suite.input_price_per_million_usd
        == manifest.model.input_price_per_million_usd
        and parsed_suite.cached_input_price_per_million_usd
        == manifest.model.cached_input_price_per_million_usd
        and parsed_suite.cache_write_input_price_per_million_usd
        == manifest.model.cache_write_input_price_per_million_usd
        and parsed_suite.output_price_per_million_usd
        == manifest.model.output_price_per_million_usd
        and parsed_suite.budget == manifest.budget
        and parsed_suite.memory_token_budget == manifest.memory.max_context_tokens
        and parsed_suite.seed == experiment.schedule_seed
        and parsed_suite.dataset_manifest_hash
        == experiment.dataset_manifest_hash
        and manifest.memory.condition in parsed_suite.conditions
        and _diagnostic_fault(parsed_suite) == manifest.fault
        and completion_plan_matches
        and runtime_contract_matches
        and pricing_contract_matches
    )
    if not suite_contract_matches:
        return False
    matching_tasks = [
        row for row in tasks if isinstance(row, dict) and row.get("task_id") == manifest.task_id
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
    if experiment.purpose in {
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT,
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT,
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT,
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT,
    }:
        task_matches = bool(
            task_matches
            and isinstance(task.get("public_review_contract_path"), str)
            and manifest.public_review_contract is not None
            and task.get("public_review_contract")
            == manifest.public_review_contract.model_dump(mode="json")
        )
    elif manifest.public_review_contract is not None:
        task_matches = False
    if not task_matches:
        return False
    matching_rows = [
        row
        for row in schedule
        if isinstance(row, dict) and row.get("schedule_row_id") == experiment.schedule_row_id
    ]
    if len(matching_rows) != 1:
        return False
    row = matching_rows[0]
    return bool(
        row.get("order") == experiment.schedule_order
        and row.get("task_id") == manifest.task_id
        and row.get("dataset_role")
        == (experiment.dataset_role.value if experiment.dataset_role is not None else None)
        and row.get("condition") == manifest.memory.condition.value
        and row.get("repetition") == experiment.repetition
    )


def _artifact_evidence(
    *,
    root: Path,
    events,
    private_tokens: set[str],
    event_types: set[EventType] | None = None,
    required_event_types: set[EventType] | None = None,
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
    selected_event_types = (
        _AGENT_VISIBLE_ARTIFACT_EVENTS
        if event_types is None
        else event_types
    )
    required_types = (
        _REQUIRED_ARTIFACT_EVENTS
        if required_event_types is None
        else required_event_types
    )
    for event in events:
        if event.type not in selected_event_types:
            continue
        raw_path = event.payload.get("artifact_path")
        raw_id = event.payload.get("artifact_id")
        path_present = isinstance(raw_path, str) and bool(raw_path.strip())
        id_present = isinstance(raw_id, str) and bool(raw_id.strip())
        if event.type in required_types and not (path_present and id_present):
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

    lower_markers = {token.lower() for token in private_tokens if token}
    matches = sum(
        1 for text in texts for marker in lower_markers if marker and marker in text.lower()
    )
    return integrity, scanned, matches, evidence, sorted(missing_identities)


def _accepted_patch_artifact_evidence(
    *,
    root: Path,
    events,
) -> tuple[bool, list[dict[str, Any]]]:
    """Bind accepted v2 patch bytes, not only their nested event metadata."""

    artifact_root = (root / "artifacts").resolve()
    integrity = True
    evidence: list[dict[str, Any]] = []
    for event in events:
        if event.type != EventType.SUBMISSION_ACCEPTED:
            continue
        raw_artifact = event.payload.get("submitted_patch_artifact")
        item: dict[str, Any] = {
            "event_id": event.event_id,
            "artifact_id": (
                raw_artifact.get("artifact_id") if isinstance(raw_artifact, dict) else None
            ),
            "declared_content_hash": (
                raw_artifact.get("content_hash") if isinstance(raw_artifact, dict) else None
            ),
            "actual_content_hash": None,
            "declared_size_bytes": (
                raw_artifact.get("size_bytes") if isinstance(raw_artifact, dict) else None
            ),
            "actual_size_bytes": None,
        }
        try:
            artifact = Artifact.model_validate(raw_artifact)
            path = Path(artifact.path).resolve()
            relative = path.relative_to(artifact_root)
            parts = relative.parts
            if (
                len(parts) != 4
                or parts[0:2] != ("objects", "sha256")
                or len(parts[2]) != 2
                or len(parts[3]) != 62
            ):
                raise ValueError("accepted patch is not stored at a CAS path")
            content = path.read_bytes()
            actual_hash = sha256_bytes(content)
            path_hash = f"sha256:{parts[2]}{parts[3]}"
            item["actual_content_hash"] = actual_hash
            item["actual_size_bytes"] = len(content)
            if (
                actual_hash != artifact.content_hash
                or actual_hash != path_hash
                or len(content) != artifact.size_bytes
            ):
                integrity = False
        except (OSError, TypeError, ValueError):
            integrity = False
        evidence.append(item)
    return integrity, evidence


def _nested_cas_artifact_evidence(
    *,
    artifact_root: Path,
    event_id: str,
    role: str,
    raw_artifact: Any,
) -> tuple[bool, dict[str, Any], bytes | None]:
    item: dict[str, Any] = {
        "event_id": event_id,
        "role": role,
        "artifact_id": (
            raw_artifact.get("artifact_id") if isinstance(raw_artifact, dict) else None
        ),
        "declared_content_hash": (
            raw_artifact.get("content_hash") if isinstance(raw_artifact, dict) else None
        ),
        "declared_path": (raw_artifact.get("path") if isinstance(raw_artifact, dict) else None),
        "actual_content_hash": None,
        "declared_size_bytes": (
            raw_artifact.get("size_bytes") if isinstance(raw_artifact, dict) else None
        ),
        "actual_size_bytes": None,
    }
    try:
        artifact = Artifact.model_validate(raw_artifact)
        path = Path(artifact.path).resolve()
        relative = path.relative_to(artifact_root)
        parts = relative.parts
        if (
            len(parts) != 4
            or parts[0:2] != ("objects", "sha256")
            or len(parts[2]) != 2
            or len(parts[3]) != 62
        ):
            raise ValueError("artifact is not stored at a CAS path")
        content = path.read_bytes()
        actual_hash = sha256_bytes(content)
        path_hash = f"sha256:{parts[2]}{parts[3]}"
        item["actual_content_hash"] = actual_hash
        item["actual_size_bytes"] = len(content)
        valid = bool(
            actual_hash == artifact.content_hash
            and actual_hash == path_hash
            and len(content) == artifact.size_bytes
        )
        return valid, item, content
    except (OSError, TypeError, ValueError):
        return False, item, None


def _corrective_runtime_contract_evidence(
    *,
    root: Path,
    manifest: RunManifest,
    events: list[Any],
) -> tuple[bool, dict[str, Any]]:
    """Validate one corrective runtime contract through its full CAS descriptor."""

    from patchloop.agent.model import (
        SYSTEM_PROMPT_V5,
        SYSTEM_PROMPT_V6,
        SYSTEM_PROMPT_V7,
        SYSTEM_PROMPT_V8,
    )
    from patchloop.agent.tools import (
        TOOL_SCHEMAS_V4,
        TOOL_SCHEMAS_V5,
        TOOL_SCHEMAS_V6,
    )

    candidates = [
        event for event in events if event.type == EventType.RUN_STARTED
    ]
    details: dict[str, Any] = {
        "run_started_count": len(candidates),
        "event_sequence": (
            candidates[0].sequence if len(candidates) == 1 else None
        ),
        "event_identity_valid": False,
        "descriptor_binding_valid": False,
        "cas_integrity_valid": False,
        "semantic_contract_valid": False,
        "content_hash": None,
    }
    if len(candidates) != 1:
        return False, details
    event = candidates[0]
    raw_artifact = event.payload.get("runtime_contract_artifact")
    cas_valid, cas_item, content = _nested_cas_artifact_evidence(
        artifact_root=(root / "artifacts").resolve(),
        event_id=event.event_id,
        role="runtime-contract",
        raw_artifact=raw_artifact,
    )
    details["cas_integrity_valid"] = cas_valid
    details["content_hash"] = cas_item.get("actual_content_hash")
    event_identity_valid = bool(
        event.actor == "runner"
        and event.run_id == manifest.run_id
        and event.payload.get("task_id") == manifest.task_id
        and event.payload.get("artifact_role") == "runtime-contract"
    )
    descriptor_binding_valid = bool(
        isinstance(raw_artifact, dict)
        and event.payload.get("artifact_id")
        == raw_artifact.get("artifact_id")
        and event.payload.get("artifact_path") == raw_artifact.get("path")
        and raw_artifact.get("media_type")
        == "application/json; charset=utf-8"
    )
    details["event_identity_valid"] = event_identity_valid
    details["descriptor_binding_valid"] = descriptor_binding_valid
    if manifest.context_policy_version == "phase-evidence-v7":
        expected = {
            "system_prompt": SYSTEM_PROMPT_V5,
            "tools": TOOL_SCHEMAS_V4,
            "tool_schema_version": "v4",
            "context_policy_version": "phase-evidence-v7",
        }
    elif manifest.context_policy_version == "phase-evidence-v8":
        expected = {
            "schema_version": "corrective-runtime-contract-v2",
            "system_prompt": SYSTEM_PROMPT_V5,
            "tools": TOOL_SCHEMAS_V4,
            "tool_schema_version": "v4",
            "context_policy_version": "phase-evidence-v8",
        }
    elif manifest.context_policy_version == "phase-evidence-v9":
        expected = {
            "schema_version": "corrective-runtime-contract-v3",
            "system_prompt": SYSTEM_PROMPT_V6,
            "tools": TOOL_SCHEMAS_V4,
            "tool_schema_version": "v4",
            "context_policy_version": "phase-evidence-v9",
        }
    elif manifest.context_policy_version == "phase-evidence-v10":
        expected = {
            "schema_version": "corrective-runtime-contract-v4",
            "system_prompt": SYSTEM_PROMPT_V7,
            "tools": TOOL_SCHEMAS_V5,
            "tool_schema_version": "v5",
            "context_policy_version": "phase-evidence-v10",
        }
    elif manifest.context_policy_version == "phase-evidence-v11":
        expected = {
            "schema_version": "corrective-runtime-contract-v5",
            "system_prompt": SYSTEM_PROMPT_V8,
            "tools": TOOL_SCHEMAS_V6,
            "tool_schema_version": "v6",
            "context_policy_version": "phase-evidence-v11",
        }
    else:
        expected = None
    try:
        observed = json.loads(content) if content is not None else None
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
        observed = None
    semantic_valid = bool(
        expected is not None
        and isinstance(observed, dict)
        and canonical_json(observed) == canonical_json(expected)
        and (
            (
                manifest.tool_schema_version == "v4"
                and manifest.context_policy_version
                in {
                    "phase-evidence-v7",
                    "phase-evidence-v8",
                    "phase-evidence-v9",
                }
            )
            or (
                manifest.tool_schema_version == "v5"
                and manifest.context_policy_version == "phase-evidence-v10"
            )
            or (
                manifest.tool_schema_version == "v6"
                and manifest.context_policy_version == "phase-evidence-v11"
            )
        )
    )
    details["semantic_contract_valid"] = semantic_valid
    return bool(
        event_identity_valid
        and descriptor_binding_valid
        and cas_valid
        and semantic_valid
    ), details


def _self_validation_nested_artifact_evidence(
    *,
    root: Path,
    events,
    private_tokens: set[str],
) -> tuple[bool, int, int, list[dict[str, Any]], list[str]]:
    """Bind v3 probe-source and semantic-review CAS bytes."""

    artifact_root = (root / "artifacts").resolve()
    integrity = True
    scanned = 0
    texts: list[str] = []
    evidence: list[dict[str, Any]] = []
    missing: list[str] = []
    for event in events:
        tool = event.payload.get("tool")
        if (
            event.type == EventType.TOOL_CALLED
            and tool == "run_probe"
        ):
            role, field = "probe-source", "source_artifact"
        elif (
            event.type == EventType.TOOL_SUCCEEDED
            and tool == "review_task"
        ):
            role, field = "task-review", "review_artifact"
        else:
            continue
        valid, item, content = _nested_cas_artifact_evidence(
            artifact_root=artifact_root,
            event_id=event.event_id,
            role=role,
            raw_artifact=event.payload.get(field),
        )
        evidence.append(item)
        integrity = bool(integrity and valid)
        if not valid or content is None:
            missing.append(f"{event.event_id}:{field}")
            continue
        scanned += 1
        try:
            texts.append(content.decode("utf-8"))
        except UnicodeDecodeError:
            integrity = False
    lower_markers = {
        token.lower() for token in private_tokens if token
    }
    matches = sum(
        1
        for text in texts
        for marker in lower_markers
        if marker and marker in text.lower()
    )
    return integrity, scanned, matches, evidence, sorted(missing)


def _patch_source_snapshot_artifact_evidence(
    *,
    root: Path,
    events,
    private_tokens: set[str],
) -> tuple[bool, int, int, list[dict[str, Any]], list[str]]:
    """Bind v4 rejected-patch source slices to the exact dispatched call."""

    artifact_root = (root / "artifacts").resolve()
    integrity = True
    scanned = 0
    texts: list[str] = []
    evidence: list[dict[str, Any]] = []
    missing: list[str] = []
    for event in events:
        if (
            event.type != EventType.TOOL_CALLED
            or event.payload.get("tool") != "apply_patch"
        ):
            continue
        valid, item, content = _nested_cas_artifact_evidence(
            artifact_root=artifact_root,
            event_id=event.event_id,
            role="patch-source-snapshot",
            raw_artifact=event.payload.get("source_snapshot_artifact"),
        )
        payload: dict[str, Any] | None = None
        if content is not None:
            try:
                parsed = json.loads(content.decode("utf-8"))
                payload = parsed if isinstance(parsed, dict) else None
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None
        patch_artifact = event.payload.get("patch_artifact")
        expected_candidate_hash = (
            patch_artifact.get("content_hash")
            if isinstance(patch_artifact, dict)
            else None
        )
        payload_hash = (
            sha256_text(
                canonical_json(
                    {
                        key: value
                        for key, value in payload.items()
                        if key != "content_hash"
                    }
                )
            )
            if isinstance(payload, dict)
            else None
        )
        shape_valid = bool(
            valid
            and isinstance(payload, dict)
            and payload.get("schema_version") == "patch-source-snapshot-v1"
            and payload.get("candidate_content_hash")
            == expected_candidate_hash
            and payload.get("input_hash") == event.payload.get("input_hash")
            and payload.get("worktree_diff_hash")
            == event.payload.get("worktree_diff_hash")
            and payload.get("content_hash") == payload_hash
            and isinstance(payload.get("entries"), list)
            and isinstance(payload.get("unavailable"), list)
        )
        item["snapshot_shape_valid"] = shape_valid
        evidence.append(item)
        integrity = bool(integrity and shape_valid)
        if not shape_valid or content is None:
            missing.append(f"{event.event_id}:source_snapshot_artifact")
            continue
        scanned += 1
        texts.append(content.decode("utf-8"))
    lower_markers = {token.lower() for token in private_tokens if token}
    matches = sum(
        1
        for text in texts
        for marker in lower_markers
        if marker and marker in text.lower()
    )
    return integrity, scanned, matches, evidence, sorted(missing)


def _v4_admission_nested_artifact_evidence(
    *,
    root: Path,
    events,
    private_tokens: set[str],
) -> tuple[bool, int, int, list[dict[str, Any]], list[str]]:
    """Bind admission input, preflight, and target CAS bytes."""

    artifact_root = (root / "artifacts").resolve()
    integrity = True
    scanned = 0
    matches = 0
    evidence: list[dict[str, Any]] = []
    missing: list[str] = []
    lower_markers = {
        token.lower()
        for token in private_tokens
        if token
    }

    def add_artifact(
        *,
        event,
        role: str,
        descriptor: Any,
        require_utf8: bool = True,
    ) -> bytes | None:
        nonlocal integrity, scanned, matches
        valid, item, content = _nested_cas_artifact_evidence(
            artifact_root=artifact_root,
            event_id=event.event_id,
            role=role,
            raw_artifact=descriptor,
        )
        item["valid"] = valid
        evidence.append(item)
        if not valid or content is None:
            integrity = False
            missing.append(
                f"{EventType.TOOL_ADMISSION_BLOCKED.value}:{role}"
            )
            return None
        scanned += 1
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            if require_utf8:
                integrity = False
                return content
            text = content.decode("utf-8", errors="ignore")
        matches += sum(
            1
            for marker in lower_markers
            if marker and marker in text.lower()
        )
        return content

    for event in events:
        if event.type != EventType.TOOL_ADMISSION_BLOCKED:
            continue
        add_artifact(
            event=event,
            role=(
                "turn-barrier-input"
                if event.payload.get("policy_version")
                == "turn-mutation-barrier-v1"
                else "investigation-admission-input"
            ),
            descriptor=event.payload.get("input_artifact"),
        )
        if (
            event.payload.get("policy_version")
            == "turn-mutation-barrier-v1"
        ):
            add_artifact(
                event=event,
                role="turn-barrier-result",
                descriptor=event.payload.get("result_artifact"),
            )
            continue
        preflight_content = add_artifact(
            event=event,
            role="investigation-admission-preflight",
            descriptor=event.payload.get("preflight_artifact"),
        )
        if preflight_content is None:
            continue
        try:
            preflight = json.loads(preflight_content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            integrity = False
            missing.append(
                f"{EventType.TOOL_ADMISSION_BLOCKED.value}:"
                "investigation-admission-preflight-json"
            )
            continue
        if not isinstance(preflight, dict):
            integrity = False
            continue
        if "target_artifact" in preflight:
            add_artifact(
                event=event,
                role="investigation-admission-target",
                descriptor=preflight.get("target_artifact"),
                require_utf8=False,
            )
    return integrity, scanned, matches, evidence, sorted(missing)


def _qualification_patch_paths(patch: str) -> list[str]:
    """Extract the ordered, unique in-place paths from a raw Git diff."""

    sections: list[list[str]] = []
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            sections.append([line])
        elif sections:
            sections[-1].append(line)
        elif line.strip():
            raise ValueError("content before the first diff section")
    if not sections:
        raise ValueError("raw patch has no diff sections")
    paths: list[str] = []
    for section in sections:
        old_headers = [line for line in section if line.startswith("--- ")]
        new_headers = [line for line in section if line.startswith("+++ ")]
        if len(old_headers) != 1 or len(new_headers) != 1:
            raise ValueError("raw patch has ambiguous file headers")

        def normalized(header: str) -> str:
            value = header[4:].split("\t", 1)[0]
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            if value.startswith(("a/", "b/")):
                value = value[2:]
            return value

        old_path = safe_relative_path(
            normalized(old_headers[0]),
            field_name="patch path",
        )
        new_path = normalized(new_headers[0])
        if new_path != "/dev/null":
            new_path = safe_relative_path(
                new_path,
                field_name="patch path",
            )
            if new_path != old_path:
                raise ValueError("raw patch changes its file path")
        if old_path in paths:
            raise ValueError("raw patch repeats a file path")
        paths.append(old_path)
    return paths


def _verifier_artifact_evidence(
    *,
    root: Path,
    result: RunResult | None,
    required: bool,
) -> tuple[bool, list[dict[str, Any]]]:
    """Bind private evaluator outputs without copying their contents."""

    if result is None:
        return not required, []
    artifact_root = (root / "artifacts").resolve()
    integrity = True
    evidence: list[dict[str, Any]] = []
    referenced = 0
    for verifier_result in result.verifier_results:
        artifact_ids = verifier_result.evidence_artifact_ids
        raw_artifacts = verifier_result.details.get("evidence_artifacts")
        if not artifact_ids:
            if raw_artifacts not in (None, []):
                integrity = False
            continue
        referenced += len(artifact_ids)
        if not isinstance(raw_artifacts, list) or len(raw_artifacts) != len(artifact_ids):
            integrity = False
            continue
        for expected_id, raw_artifact in zip(
            artifact_ids,
            raw_artifacts,
            strict=True,
        ):
            valid, item, _ = _nested_cas_artifact_evidence(
                artifact_root=artifact_root,
                event_id=verifier_result.verifier_result_id,
                role=f"verifier:{verifier_result.check_type}",
                raw_artifact=raw_artifact,
            )
            if item.get("artifact_id") != expected_id:
                valid = False
            evidence.append(item)
            integrity = integrity and valid
    if required and len(evidence) != referenced:
        integrity = False
    return integrity, evidence


def _evaluation_receipt_evidence(
    *,
    root: Path,
    run_id: str,
    manifest: RunManifest,
    result: RunResult | None,
) -> tuple[bool, dict[str, Any]]:
    """Validate the evaluator-ready marker and every file hash it binds."""

    run_dir = root / "artifacts" / "runs" / run_id
    receipt_path = run_dir / "evaluation-receipt.json"
    item: dict[str, Any] = {
        "receipt_content_hash": None,
        "declared_file_hashes": None,
        "actual_file_hashes": {},
        "worktree_diff_hash": None,
        "submitted_patch_artifact_id": None,
        "evaluator_duration_ms": None,
    }
    try:
        receipt_bytes = receipt_path.read_bytes()
        item["receipt_content_hash"] = sha256_bytes(receipt_bytes)
        receipt = json.loads(receipt_bytes)
        if not isinstance(receipt, dict):
            raise ValueError("receipt is not an object")
        file_hashes = receipt.get("file_hashes")
        duration_ms = receipt.get("evaluator_duration_ms")
        item["declared_file_hashes"] = file_hashes
        item["worktree_diff_hash"] = receipt.get("worktree_diff_hash")
        item["submitted_patch_artifact_id"] = receipt.get("submitted_patch_artifact_id")
        item["evaluator_duration_ms"] = duration_ms
        if (
            receipt.get("schema_version") != "evaluation-receipt-v1"
            or receipt.get("run_id") != run_id
            or not isinstance(duration_ms, int)
            or duration_ms < 0
            or not isinstance(file_hashes, dict)
            or set(file_hashes) != {"manifest.json", "result.json", "provenance.json"}
        ):
            raise ValueError("receipt contract mismatch")
        contents: dict[str, bytes] = {}
        for name in ("manifest.json", "result.json", "provenance.json"):
            content = (run_dir / name).read_bytes()
            actual_hash = sha256_bytes(content)
            item["actual_file_hashes"][name] = actual_hash
            if file_hashes.get(name) != actual_hash:
                raise ValueError("receipt file hash mismatch")
            contents[name] = content
        persisted_manifest = RunManifest.model_validate_json(contents["manifest.json"])
        persisted_result = RunResult.model_validate_json(contents["result.json"])
        provenance = json.loads(contents["provenance.json"])
        if not isinstance(provenance, dict):
            raise ValueError("provenance is not an object")
        verifier_descriptors = [
            raw_artifact
            for verifier_result in persisted_result.verifier_results
            for raw_artifact in verifier_result.details.get(
                "evidence_artifacts",
                [],
            )
        ]
        patch_hash = receipt.get("worktree_diff_hash")
        submitted_id = receipt.get("submitted_patch_artifact_id")
        if (
            persisted_manifest != manifest
            or result is None
            or persisted_result != result
            or persisted_result.run_id != run_id
            or persisted_result.evaluation_status != "completed"
            or persisted_result.submitted_patch_artifact_id != submitted_id
            or provenance.get("patch_hash") != patch_hash
            or provenance.get("diff_hash") != patch_hash
            or provenance.get("submitted_patch_content_hash") != patch_hash
            or provenance.get("submitted_patch_artifact_id") != submitted_id
            or provenance.get("verifier_evidence_schema_version") != "verifier-evidence-v1"
            or provenance.get("verifier_evidence_artifacts") != verifier_descriptors
        ):
            raise ValueError("receipt evidence mismatch")
        return True, item
    except (
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return False, item


def _patch_intent_artifact_evidence(
    *,
    root: Path,
    events,
    private_tokens: set[str],
) -> tuple[bool, int, int, list[dict[str, Any]]]:
    """Bind every CAS object needed to classify an interrupted v2 patch."""

    artifact_root = (root / "artifacts").resolve()
    integrity = True
    evidence: list[dict[str, Any]] = []
    texts: list[str] = []
    scanned = 0
    for event in events:
        if event.type != EventType.PATCH_PREPARED:
            continue
        valid, item, content = _nested_cas_artifact_evidence(
            artifact_root=artifact_root,
            event_id=event.event_id,
            role="patch-intent",
            raw_artifact=event.payload.get("intent_artifact"),
        )
        evidence.append(item)
        integrity = integrity and valid
        if content is None:
            continue
        scanned += 1
        texts.append(content.decode("utf-8", errors="replace"))
        try:
            intent = json.loads(content.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            integrity = False
            continue
        matching_calls = [
            candidate
            for candidate in events
            if candidate.type == EventType.TOOL_CALLED
            and candidate.sequence < event.sequence
            and candidate.correlation_id == event.correlation_id
            and candidate.payload.get("tool") == "apply_patch"
        ]
        matching_call = matching_calls[0] if len(matching_calls) == 1 else None
        if (
            not isinstance(intent, dict)
            or intent.get("schema_version") != "patch-mutation-intent-v1"
            or intent.get("run_id") != event.run_id
            or intent.get("action_id") != event.correlation_id
            or matching_call is None
            or intent.get("input_hash") != matching_call.payload.get("input_hash")
            or intent.get("patch_artifact") != matching_call.payload.get("patch_artifact")
            or not isinstance(intent.get("patch_artifact"), dict)
            or matching_call.payload.get("artifact_id")
            != intent["patch_artifact"].get("artifact_id")
            or matching_call.payload.get("artifact_path") != intent["patch_artifact"].get("path")
            or intent.get("baseline_worktree_diff_hash")
            != event.payload.get("baseline_worktree_diff_hash")
            or intent.get("expected_worktree_diff_hash")
            != event.payload.get("expected_worktree_diff_hash")
            or event.payload.get("artifact_id") != item["artifact_id"]
            or event.payload.get("artifact_path") != item["declared_path"]
            or event.payload.get("content_hash") != item["actual_content_hash"]
            or event.payload.get("size_bytes") != item["actual_size_bytes"]
        ):
            integrity = False
            continue
        nested: list[tuple[str, Any]] = [("raw-patch", intent.get("patch_artifact"))]
        files = intent.get("files")
        if not isinstance(files, list) or not files:
            integrity = False
            continue
        intent_paths: list[str] = []
        for index, file_entry in enumerate(files):
            if (
                not isinstance(file_entry, dict)
                or set(file_entry)
                != {
                    "path",
                    "mode",
                    "git_mode",
                    "preimage_artifact",
                    "postimage_artifact",
                }
                or type(file_entry.get("mode")) is not int
                or not 0 <= file_entry["mode"] <= 0o7777
                or file_entry.get("git_mode") not in {"100644", "100755"}
            ):
                integrity = False
                continue
            try:
                path = safe_relative_path(
                    str(file_entry["path"]),
                    field_name="prepared patch path",
                )
            except ContractError:
                integrity = False
                continue
            if path in intent_paths:
                integrity = False
                continue
            intent_paths.append(path)
            nested.append(
                (
                    f"preimage:{index}:{path}",
                    file_entry.get("preimage_artifact"),
                )
            )
            if file_entry.get("postimage_artifact") is not None:
                nested.append(
                    (
                        f"postimage:{index}:{path}",
                        file_entry.get("postimage_artifact"),
                    )
                )
        raw_patch_content: bytes | None = None
        for role, raw_artifact in nested:
            nested_valid, nested_item, nested_content = _nested_cas_artifact_evidence(
                artifact_root=artifact_root,
                event_id=event.event_id,
                role=role,
                raw_artifact=raw_artifact,
            )
            evidence.append(nested_item)
            integrity = integrity and nested_valid
            if nested_content is not None:
                scanned += 1
                texts.append(nested_content.decode("utf-8", errors="replace"))
                if role == "raw-patch":
                    raw_patch_content = nested_content
        if raw_patch_content is None:
            integrity = False
            continue
        try:
            raw_patch = raw_patch_content.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            integrity = False
            continue
        expected_input_hash = sha256_text(
            canonical_json(
                {
                    "tool": "apply_patch",
                    "input": {"patch": raw_patch},
                }
            )
        )
        if (
            intent.get("input_hash") != expected_input_hash
            or matching_call is None
            or matching_call.payload.get("input_hash") != expected_input_hash
        ):
            integrity = False
        try:
            raw_patch_paths = _qualification_patch_paths(raw_patch)
        except (ContractError, ValueError):
            integrity = False
            continue
        if intent_paths != raw_patch_paths:
            integrity = False
        expected_patch_hash = sha256_text(raw_patch)
        outcomes = [
            candidate
            for candidate in events
            if candidate.type in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}
            and candidate.correlation_id == event.correlation_id
            and candidate.payload.get("tool") == "apply_patch"
        ]
        applications = [
            candidate
            for candidate in events
            if candidate.type == EventType.PATCH_APPLIED
            and candidate.correlation_id == event.correlation_id
        ]
        if len(outcomes) != 1 or outcomes[0].sequence <= event.sequence:
            integrity = False
            continue
        outcome = outcomes[0]
        if outcome.type == EventType.TOOL_SUCCEEDED:
            if (
                len(applications) != 1
                or not outcome.sequence < applications[0].sequence
                or outcome.payload.get("patch_hash") != expected_patch_hash
                or applications[0].payload.get("patch_hash") != expected_patch_hash
                or outcome.payload.get("worktree_diff_hash")
                != intent.get("expected_worktree_diff_hash")
                or applications[0].payload.get("worktree_diff_hash")
                != intent.get("expected_worktree_diff_hash")
            ):
                integrity = False
        elif applications or outcome.payload.get("status") not in {"failed", "rejected"}:
            integrity = False

    lower_markers = {token.lower() for token in private_tokens if token}
    matches = sum(
        1 for text in texts for marker in lower_markers if marker and marker in text.lower()
    )
    return integrity, scanned, matches, evidence


def _request_context(
    request_body: Any,
    *,
    allow_direct_context: bool = False,
) -> str | None:
    """Extract the exact user context from PatchLoop's Responses request."""

    if not isinstance(request_body, dict):
        return None
    direct_context = request_body.get("context")
    if allow_direct_context and isinstance(direct_context, str):
        return direct_context
    inputs = request_body.get("input")
    if not isinstance(inputs, list):
        return None
    user_messages = [
        item for item in inputs if isinstance(item, dict) and item.get("role") == "user"
    ]
    if len(user_messages) != 1:
        return None
    content = user_messages[0].get("content")
    return content if isinstance(content, str) else None


def _request_evidence_payload(
    context_event,
    *,
    artifact_root: Path | None = None,
    expected_provider: str | None = None,
) -> tuple[bool, dict[str, Any] | None]:
    """Load and validate one content-addressed model request artifact."""

    try:
        artifact_path = Path(str(context_event.payload["artifact_path"])).resolve()
        content = artifact_path.read_bytes()
        if artifact_root is not None:
            relative = artifact_path.relative_to(artifact_root.resolve())
            parts = relative.parts
            if (
                len(parts) != 4
                or parts[0:2] != ("objects", "sha256")
                or len(parts[2]) != 2
                or len(parts[3]) != 62
                or sha256_bytes(content) != f"sha256:{parts[2]}{parts[3]}"
            ):
                return False, None
        request_evidence = json.loads(content.decode("utf-8"))
        if not isinstance(request_evidence, dict):
            return False, None
        request_body = request_evidence["request_body"]
        provider = request_evidence.get("provider")
        recorded_request_hash = request_evidence["request_body_hash"]
        calculated_request_hash = sha256_text(canonical_json(request_body))
        provider_valid = bool(
            expected_provider is None
            or (
                isinstance(provider, str)
                and provider == expected_provider
            )
        )
        rendered_context = _request_context(
            request_body,
            allow_direct_context=provider in {"mock", "replay"},
        )
        valid = bool(
            request_evidence.get("schema_version") == "model-request-evidence-v1"
            and provider_valid
            and isinstance(recorded_request_hash, str)
            and recorded_request_hash == calculated_request_hash
            and context_event.payload.get("request_body_hash") == calculated_request_hash
            and isinstance(rendered_context, str)
            and context_event.payload.get("context_hash") == sha256_text(rendered_context)
        )
        return valid, request_evidence if valid else None
    except (
        KeyError,
        OSError,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return False, None


def _v4_investigation_context_evidence(
    *,
    root: Path,
    manifest: RunManifest,
    package: TaskPackage,
    events: list,
    checkpoints: list,
    context_events: list,
) -> tuple[bool, dict[str, Any]]:
    """Recompute every versioned investigation ledger from its durable prefix."""

    from patchloop.agent.context import build_context_with_evidence

    artifact_root = root / "artifacts"
    artifact_store = ArtifactStore(artifact_root)
    checkpoints_by_id = {
        checkpoint.checkpoint_id: checkpoint
        for checkpoint in checkpoints
    }
    failed_sequences: list[int] = []
    verified_hashes: list[str] = []
    policy_version = manifest.context_policy_version
    evidence_schema = (
        "context-build-evidence-v11"
        if policy_version == "phase-evidence-v11"
        else (
            "context-build-evidence-v10"
            if policy_version == "phase-evidence-v10"
            else (
                "context-build-evidence-v9"
                if policy_version == "phase-evidence-v9"
                else (
                    "context-build-evidence-v8"
                    if policy_version == "phase-evidence-v8"
                    else (
                        "context-build-evidence-v7"
                        if policy_version == "phase-evidence-v7"
                        else (
                            "context-build-evidence-v6"
                            if policy_version == "phase-evidence-v6"
                            else (
                                "context-build-evidence-v5"
                                if policy_version == "phase-evidence-v5"
                                else "context-build-evidence-v4"
                            )
                        )
                    )
                )
            )
        )
    )
    for context_event in context_events:
        try:
            request_valid, request_evidence = _request_evidence_payload(
                context_event,
                artifact_root=artifact_root,
                expected_provider=manifest.model.provider,
            )
            if not request_valid or request_evidence is None:
                raise RecoveryError("model request evidence is invalid")
            rendered = _request_context(
                request_evidence["request_body"],
                allow_direct_context=(
                    manifest.model.provider in {"mock", "replay"}
                ),
            )
            context_build = request_evidence.get("context_build")
            if (
                not isinstance(rendered, str)
                or not isinstance(context_build, dict)
                or context_build.get("schema_version")
                != evidence_schema
            ):
                raise RecoveryError("v4 context build evidence is invalid")
            recorded_ledger = context_build.get("investigation_ledger")
            if not isinstance(recorded_ledger, dict):
                raise RecoveryError("v4 context lacks investigation evidence")
            source_through = recorded_ledger.get(
                "source_through_sequence"
            )
            if type(source_through) is not int or source_through < 0:
                raise RecoveryError(
                    "v4 investigation source sequence is invalid"
                )
            if source_through != context_event.sequence - 1:
                raise RecoveryError(
                    "v4 investigation source sequence is not the exact "
                    "ContextBuilt prefix"
                )
            source_events = [
                event
                for event in events
                if event.sequence <= source_through
            ]
            checkpoint_events = [
                event
                for event in source_events
                if event.type == EventType.CHECKPOINT_SAVED
                and isinstance(
                    event.payload.get("checkpoint_id"),
                    str,
                )
            ]
            checkpoint = None
            if checkpoint_events:
                checkpoint_id = checkpoint_events[-1].payload[
                    "checkpoint_id"
                ]
                checkpoint = checkpoints_by_id.get(checkpoint_id)
                if checkpoint is None:
                    raise RecoveryError(
                        "v4 context checkpoint is unavailable"
                    )
            parsed_context = json.loads(rendered)
            if not isinstance(parsed_context, dict):
                raise RecoveryError("v4 rendered context is not an object")
            selected_memory = parsed_context.get("selected_memory")
            if selected_memory is not None and not isinstance(
                selected_memory,
                str,
            ):
                raise RecoveryError("v4 selected memory is invalid")
            rebuilt = build_context_with_evidence(
                package.public,
                source_events,
                checkpoint,
                selected_memory or "",
                policy_version=policy_version,
                artifact_store=artifact_store,
                budget=manifest.budget,
                max_output_tokens=manifest.model.max_output_tokens,
                public_review_contract=manifest.public_review_contract,
            )
            ledger_evidence = rebuilt.evidence[
                "investigation_ledger"
            ]
            if (
                rebuilt.rendered != rendered
                or rebuilt.evidence != context_build
                or context_event.payload.get(
                    "investigation_ledger_hash"
                )
                != ledger_evidence["content_hash"]
                or context_event.payload.get(
                    "investigation_source_through_sequence"
                )
                != ledger_evidence["source_through_sequence"]
                or context_event.payload.get(
                    "investigation_no_progress_streak"
                )
                != ledger_evidence["no_progress_streak"]
                or context_event.payload.get(
                    "investigation_exploration_admitted"
                )
                != ledger_evidence["exploration_admitted"]
            ):
                raise RecoveryError(
                    "v4 investigation context failed recomputation"
                )
            if policy_version in {
                "phase-evidence-v5",
                "phase-evidence-v6",
                "phase-evidence-v7",
                "phase-evidence-v8",
                "phase-evidence-v9",
                "phase-evidence-v10",
                "phase-evidence-v11",
            }:
                expected_tail = _v5_expected_tail_policy(
                    task=package.public,
                    events=source_events,
                    manifest=manifest,
                    projection_stage="pre_generation",
                )
                rendered_ledger = parsed_context.get(
                    "investigation_ledger"
                )
                if (
                    not isinstance(rendered_ledger, dict)
                    or rendered_ledger.get("tail_policy")
                    != expected_tail
                ):
                    raise RecoveryError(
                        "v5 investigation token tail failed independent "
                        "recomputation"
                    )
                v5_mirrors = {
                    "investigation_tail_block_reasons": ledger_evidence[
                        "tail_block_reasons"
                    ],
                    "investigation_tail_remaining_tokens": ledger_evidence[
                        "tail_remaining_tokens"
                    ],
                    "investigation_tail_observation_count": ledger_evidence[
                        "tail_observation_count"
                    ],
                    "investigation_tail_max_observed_input_tokens": (
                        ledger_evidence[
                            "tail_max_observed_input_tokens"
                        ]
                    ),
                    "investigation_tail_max_positive_growth": (
                        ledger_evidence["tail_max_positive_growth"]
                    ),
                    "investigation_tail_projected_next_input_tokens": (
                        ledger_evidence[
                            "tail_projected_next_input_tokens"
                        ]
                    ),
                    "investigation_tail_projected_model_turns": (
                        ledger_evidence[
                            "tail_projected_model_turns"
                        ]
                    ),
                    "investigation_tail_reserved_tokens": ledger_evidence[
                        "tail_reserved_tokens"
                    ],
                    "investigation_tail_max_output_tokens": ledger_evidence[
                        "tail_max_output_tokens"
                    ],
                }
                if any(
                    context_event.payload.get(field) != expected
                    for field, expected in v5_mirrors.items()
                ):
                    raise RecoveryError(
                        "v5 investigation tail mirrors failed recomputation"
                    )
            verified_hashes.append(ledger_evidence["content_hash"])
        except (
            KeyError,
            OSError,
            RecoveryError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            failed_sequences.append(context_event.sequence)
    return (
        not failed_sequences,
        {
            "context_count": len(context_events),
            "verified_context_count": (
                len(context_events) - len(failed_sequences)
            ),
            "failed_context_sequences": failed_sequences,
            "ledger_hashes": verified_hashes,
        },
    )


def _v9_truncate_review_json_strings(value: Any, limit: int) -> Any:
    """Frozen independent copy of V9 model-context field truncation."""

    if isinstance(value, str):
        if len(value) <= limit:
            return value
        marker = "\n...[field truncated for model context]"
        return value[: max(0, limit - len(marker))] + marker
    if isinstance(value, list):
        return [
            _v9_truncate_review_json_strings(item, limit)
            for item in value
        ]
    if isinstance(value, dict):
        return {
            key: _v9_truncate_review_json_strings(item, limit)
            for key, item in value.items()
        }
    return value


def _v9_semantic_review_tool_result(raw: str) -> tuple[Any, bool]:
    """Recompute the V9 rendered result without calling the context builder."""

    parsed = json.loads(raw)
    if len(raw) <= _V9_REVIEW_TOOL_RESULT_CHARACTER_LIMIT:
        return parsed, False
    per_string_limit = _V9_REVIEW_TOOL_RESULT_CHARACTER_LIMIT
    truncated = parsed
    while per_string_limit > 256:
        truncated = _v9_truncate_review_json_strings(
            parsed,
            per_string_limit,
        )
        if len(
            json.dumps(truncated, ensure_ascii=False, default=str)
        ) <= _V9_REVIEW_TOOL_RESULT_CHARACTER_LIMIT:
            return truncated, True
        per_string_limit //= 2
    truncated = _v9_truncate_review_json_strings(parsed, 256)
    if len(
        json.dumps(truncated, ensure_ascii=False, default=str)
    ) <= _V9_REVIEW_TOOL_RESULT_CHARACTER_LIMIT:
        return truncated, True
    top_level_keys = (
        [str(key)[:120] for key in list(parsed)[:20]]
        if isinstance(parsed, dict)
        else []
    )
    return {
        "truncated": True,
        "original_characters": len(raw),
        "top_level_keys": top_level_keys,
        "summary": (
            "Tool result exceeded the context limit after semantic field "
            "truncation; inspect targeted evidence instead."
        ),
    }, True


def _v9_recompute_review_anchor(
    event: Any,
    *,
    artifact_store: ArtifactStore,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Rebuild one pinned anchor from its durable event and CAS bytes."""

    if event.type != EventType.TOOL_SUCCEEDED:
        raise RecoveryError("v9 review anchor is not ToolSucceeded")
    try:
        descriptor = Artifact.model_validate(
            event.payload.get("result_artifact")
        )
    except ValueError as exc:
        raise RecoveryError(
            "v9 review anchor lacks a valid result artifact"
        ) from exc
    if (
        event.payload.get("artifact_id") != descriptor.artifact_id
        or event.payload.get("artifact_path") != descriptor.path
    ):
        raise RecoveryError(
            "v9 review anchor conflicts with its CAS descriptor"
        )
    raw = artifact_store.read_bytes(descriptor).decode(
        "utf-8",
        errors="strict",
    )
    rendered_result, truncated = _v9_semantic_review_tool_result(raw)
    payload = dict(event.payload)
    payload["tool_result"] = rendered_result
    included_characters = len(
        json.dumps(rendered_result, ensure_ascii=False, default=str)
    )
    return (
        {
            "sequence": event.sequence,
            "type": event.type.value,
            "actor": event.actor,
            "payload": payload,
        },
        {
            "event_sequence": event.sequence,
            "original_characters": len(raw),
            "included_characters": included_characters,
            "truncated": truncated,
            "available": True,
            "tool": payload.get("tool"),
            "worktree_diff_hash": payload.get("worktree_diff_hash"),
            "artifact_id": payload.get("artifact_id"),
        },
    )


def _v10_recompute_review_anchor(
    event: Any,
    *,
    artifact_store: ArtifactStore,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Rebuild a V10 anchor and bind selection metadata to its CAS bytes."""

    rendered, evidence = _v9_recompute_review_anchor(
        event,
        artifact_store=artifact_store,
    )
    tool = event.payload.get("tool")
    if tool not in {"run_check", "read_file"}:
        return rendered, evidence
    if (
        event.actor != "tool-gateway"
        or event.payload.get("status") != "succeeded"
    ):
        raise RecoveryError("v10 review anchor has an invalid tool identity")
    descriptor = Artifact.model_validate(event.payload.get("result_artifact"))
    document = json.loads(
        artifact_store.read_bytes(descriptor).decode("utf-8", errors="strict")
    )
    tool_result = rendered.get("payload", {}).get("tool_result")
    if not isinstance(document, dict) or not isinstance(tool_result, dict):
        raise RecoveryError("v10 review anchor result is not an object")
    event_diff_hash = event.payload.get("worktree_diff_hash")
    if (
        not isinstance(event_diff_hash, str)
        or document.get("worktree_diff_hash") != event_diff_hash
        or tool_result.get("worktree_diff_hash") != event_diff_hash
    ):
        raise RecoveryError(
            "v10 review anchor conflicts with its current-diff result"
        )

    rendered_truncated = evidence.get("truncated") is True
    if tool == "run_check":
        if (
            not isinstance(document.get("check_id"), str)
            or type(document.get("passed")) is not bool
            or type(document.get("timed_out")) is not bool
            or type(document.get("truncated")) is not bool
            or event.payload.get("check_id") != document.get("check_id")
            or event.payload.get("passed") is not document.get("passed")
            or event.payload.get("timed_out") is not document.get("timed_out")
            or (
                not rendered_truncated
                and any(
                    tool_result.get(key) != document.get(key)
                    for key in (
                        "check_id",
                        "passed",
                        "timed_out",
                        "truncated",
                        "worktree_diff_hash",
                    )
                )
            )
            or (document["passed"] is True and document["timed_out"] is True)
        ):
            raise RecoveryError(
                "v10 run_check anchor conflicts with its result document"
            )
        evidence["truncated"] = bool(
            rendered_truncated
            or document["timed_out"]
            or document["truncated"]
        )
        return rendered, evidence

    if (
        not isinstance(document.get("path"), str)
        or not isinstance(document.get("content"), str)
        or (
            "truncated" in document
            and type(document.get("truncated")) is not bool
        )
        or (
            not rendered_truncated
            and (
                tool_result.get("path") != document.get("path")
                or tool_result.get("content") != document.get("content")
                or tool_result.get("worktree_diff_hash")
                != document.get("worktree_diff_hash")
            )
        )
    ):
        raise RecoveryError(
            "v10 read_file anchor conflicts with its result document"
        )
    evidence["truncated"] = bool(
        rendered_truncated or document.get("truncated") is True
    )
    return rendered, evidence


def _v9_review_evidence_context_contract(
    *,
    root: Path,
    manifest: RunManifest,
    package: TaskPackage,
    events: list[Any],
    context_events: list[Any],
) -> tuple[bool, dict[str, Any]]:
    """Independently recompute V9 current-diff review citation anchors."""

    from patchloop.agent.context import REVIEW_EVIDENCE_SCHEMA
    from patchloop.agent.phases import diff_bound_evidence

    artifact_root = root / "artifacts"
    artifact_store = ArtifactStore(artifact_root)
    failed_sequences: list[int] = []
    failure_reasons: list[dict[str, Any]] = []
    active_sequences: list[int] = []
    verified_anchor_sequences: list[int] = []
    for context_event in context_events:
        try:
            request_valid, request_evidence = _request_evidence_payload(
                context_event,
                artifact_root=artifact_root,
                expected_provider=manifest.model.provider,
            )
            if not request_valid or request_evidence is None:
                raise RecoveryError("v9 request evidence is invalid")
            rendered = _request_context(
                request_evidence["request_body"],
                allow_direct_context=manifest.model.provider in {"mock", "replay"},
            )
            parsed = json.loads(rendered)
            if not isinstance(parsed, dict):
                raise RecoveryError("v9 rendered context is not an object")
            context_build = request_evidence.get("context_build")
            visible = parsed.get("review_evidence")
            build = (
                context_build.get("review_evidence")
                if isinstance(context_build, dict)
                else None
            )
            if (
                not isinstance(context_build, dict)
                or context_build.get("schema_version")
                != "context-build-evidence-v9"
                or not isinstance(visible, dict)
                or not isinstance(build, dict)
                or visible.get("schema_version") != REVIEW_EVIDENCE_SCHEMA
                or build.get("schema_version") != REVIEW_EVIDENCE_SCHEMA
            ):
                raise RecoveryError("v9 review evidence envelope is invalid")
            checkpoint = parsed.get("checkpoint")
            phase = Phase(parsed.get("phase"))
            diff_hash = (
                checkpoint.get("worktree_diff_hash")
                if isinstance(checkpoint, dict)
                else _EMPTY_DIFF_HASH
            )
            if not isinstance(diff_hash, str):
                raise RecoveryError("v9 review evidence has no diff identity")
            source_events = [
                event
                for event in events
                if event.sequence < context_event.sequence
            ]
            readiness = diff_bound_evidence(
                package.public,
                source_events,
                diff_hash,
                phase=phase,
                structured_review_required=True,
                probe_available=bool(package.public.probe_profiles),
            )
            active = bool(
                phase == Phase.REVIEW
                and readiness.mutation_present
                and not readiness.pending_checks
                and readiness.review_event_sequence is not None
            )
            requested_check_sequences = (
                list(readiness.current_diff_check_event_sequences)
                if active
                else []
            )
            requested_diff_sequence = (
                readiness.review_event_sequence if active else None
            )
            requested_sequences = [
                *requested_check_sequences,
                *(
                    [requested_diff_sequence]
                    if requested_diff_sequence is not None
                    else []
                ),
            ]
            events_by_sequence = {
                event.sequence: event for event in source_events
            }
            expected_pinned_results: list[dict[str, Any]] = []
            expected_pinned_tool_results: list[dict[str, Any]] = []
            complete_sequences: list[int] = []
            incomplete_sequences: list[int] = []
            for sequence in requested_sequences:
                source_event = events_by_sequence.get(sequence)
                if source_event is None:
                    raise RecoveryError(
                        "v9 review anchor durable event is unavailable"
                    )
                rendered_anchor, tool_anchor = (
                    _v9_recompute_review_anchor(
                        source_event,
                        artifact_store=artifact_store,
                    )
                )
                if tool_anchor.get("worktree_diff_hash") != diff_hash:
                    raise RecoveryError(
                        "v9 review anchor is not bound to the current diff"
                    )
                expected_pinned_results.append(rendered_anchor)
                expected_pinned_tool_results.append(tool_anchor)
                if (
                    tool_anchor["available"] is True
                    and tool_anchor["truncated"] is False
                ):
                    complete_sequences.append(sequence)
                else:
                    incomplete_sequences.append(sequence)
            check_sequences = [
                sequence
                for sequence in requested_check_sequences
                if sequence in complete_sequences
            ]
            diff_sequence = (
                requested_diff_sequence
                if requested_diff_sequence in complete_sequences
                else None
            )
            citable = [
                *check_sequences,
                *([diff_sequence] if diff_sequence is not None else []),
            ]
            visible_fields = {
                "schema_version": REVIEW_EVIDENCE_SCHEMA,
                "pinning_active": active,
                "worktree_diff_hash": diff_hash,
                "mutation_event_sequence": readiness.mutation_event_sequence,
                "passing_check_event_sequences": check_sequences,
                "source_get_diff_sequence": diff_sequence,
                "citable_event_sequences": citable,
                "incomplete_event_sequences": incomplete_sequences,
            }
            if set(visible) != {
                *visible_fields,
                "pinned_results",
                "citation_rule",
            } or set(build) != {
                *visible_fields,
                "pinned_tool_results",
            }:
                raise RecoveryError(
                    "v9 review evidence has unknown or missing fields"
                )
            if any(
                canonical_json(visible.get(key))
                != canonical_json(value)
                for key, value in visible_fields.items()
            ):
                raise RecoveryError("v9 visible review anchors failed recomputation")
            if any(
                canonical_json(build.get(key))
                != canonical_json(value)
                for key, value in visible_fields.items()
            ):
                raise RecoveryError("v9 review build anchors failed recomputation")
            mirror_fields = {
                "review_evidence_pinning_active": active,
                "review_evidence_worktree_diff_hash": diff_hash,
                "review_evidence_mutation_event_sequence": (
                    readiness.mutation_event_sequence
                ),
                "review_evidence_passing_check_event_sequences": (
                    check_sequences
                ),
                "review_evidence_source_get_diff_sequence": diff_sequence,
                "review_evidence_citable_event_sequences": citable,
                "review_evidence_incomplete_event_sequences": (
                    incomplete_sequences
                ),
            }
            if any(
                canonical_json(context_event.payload.get(key))
                != canonical_json(value)
                for key, value in mirror_fields.items()
            ):
                raise RecoveryError("v9 review evidence mirrors are invalid")
            pinned_results = visible.get("pinned_results")
            pinned_tool_results = build.get("pinned_tool_results")
            if (
                canonical_json(pinned_results)
                != canonical_json(expected_pinned_results)
                or canonical_json(pinned_tool_results)
                != canonical_json(expected_pinned_tool_results)
            ):
                raise RecoveryError(
                    "v9 pinned review results failed CAS recomputation"
                )
            recent_events = parsed.get("recent_events")
            recent_sequences = (
                [
                    item.get("sequence")
                    for item in recent_events
                    if isinstance(item, dict)
                    and type(item.get("sequence")) is int
                ]
                if isinstance(recent_events, list)
                else []
            )
            pinned_sequences = [
                item["sequence"] for item in expected_pinned_results
            ]
            if (
                not isinstance(recent_events, list)
                or len(recent_sequences) != len(recent_events)
                or len(pinned_sequences) != len(set(pinned_sequences))
                or set(pinned_sequences).intersection(recent_sequences)
            ):
                raise RecoveryError(
                    "v9 review anchors are duplicated in recent events"
                )
            if visible.get("citation_rule") != (
                "review_task may cite only citable_event_sequences; "
                "investigation_ledger source_call_sequence values are not "
                "review citations"
            ):
                raise RecoveryError("v9 review citation rule is invalid")
            presented = context_build.get("tool_results")
            if (
                not isinstance(presented, list)
                or not all(
                    isinstance(item, dict)
                    and type(item.get("event_sequence")) is int
                    for item in presented
                )
            ):
                raise RecoveryError("v9 review tool results are invalid")
            for expected in expected_pinned_tool_results:
                matches = [
                    item
                    for item in presented
                    if isinstance(item, dict)
                    and type(item.get("event_sequence")) is int
                    and item.get("event_sequence")
                    == expected["event_sequence"]
                    and canonical_json(item)
                    == canonical_json(expected)
                ]
                if len(matches) != 1:
                    raise RecoveryError(
                        "v9 review anchor presentation failed CAS recomputation"
                    )
            if active:
                active_sequences.append(context_event.sequence)
                verified_anchor_sequences.extend(citable)
        except (
            KeyError,
            OSError,
            RecoveryError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            failed_sequences.append(context_event.sequence)
            failure_reasons.append(
                {"sequence": context_event.sequence, "reason": str(exc)}
            )
    return bool(context_events) and not failed_sequences, {
        "context_count": len(context_events),
        "verified_context_count": len(context_events) - len(failed_sequences),
        "active_context_sequences": active_sequences,
        "verified_anchor_sequences": sorted(set(verified_anchor_sequences)),
        "failed_context_sequences": failed_sequences,
        "failure_reasons": failure_reasons,
    }


def _v9_review_rejection_terminal_contract(
    events: list[Any],
) -> tuple[bool, dict[str, Any]]:
    """Verify the three-rejection stop and mutation-epoch reset contract."""

    mutations = sorted(
        (
            event
            for event in events
            if event.type == EventType.PATCH_APPLIED
        ),
        key=lambda event: event.sequence,
    )
    terminal_rejection_sequences: list[int] = []
    failed_terminal_rejection_sequences: list[int] = []
    reset_mutation_sequences: list[int] = []
    forbidden_after_terminal: dict[int, list[int]] = {}
    for index, mutation in enumerate(mutations):
        next_mutation_sequence = (
            mutations[index + 1].sequence
            if index + 1 < len(mutations)
            else None
        )
        epoch_failures = [
            event
            for event in events
            if event.sequence > mutation.sequence
            and (
                next_mutation_sequence is None
                or event.sequence < next_mutation_sequence
            )
            and event.type == EventType.TOOL_FAILED
            and event.payload.get("tool") == "review_task"
        ]
        if index > 0:
            previous_mutation = mutations[index - 1]
            previous_failures = [
                event
                for event in events
                if previous_mutation.sequence < event.sequence
                < mutation.sequence
                and event.type == EventType.TOOL_FAILED
                and event.payload.get("tool") == "review_task"
            ]
            if previous_failures:
                reset_mutation_sequences.append(mutation.sequence)
        if len(epoch_failures) < 3:
            continue
        third = epoch_failures[2]
        terminal_rejection_sequences.append(third.sequence)
        later_forbidden = [
            event.sequence
            for event in events
            if event.sequence > third.sequence
            and (
                event.type
                in {
                    EventType.CONTEXT_BUILT,
                    EventType.MEMORY_RETRIEVED,
                    EventType.MODEL_CALLED,
                    EventType.TOOL_CALLED,
                    EventType.TOOL_REPLAYED,
                    EventType.TOOL_SUCCEEDED,
                    EventType.TOOL_FAILED,
                    EventType.TOOL_ADMISSION_BLOCKED,
                    EventType.PATCH_PREPARED,
                    EventType.PATCH_APPLIED,
                    EventType.CHECK_STARTED,
                    EventType.CHECK_FINISHED,
                    EventType.REVIEW_RECORDED,
                    EventType.SUBMISSION_ATTEMPTED,
                    EventType.SUBMISSION_REJECTED,
                    EventType.SUBMISSION_ACCEPTED,
                }
            )
        ]
        run_failed_after = [
            event
            for event in events
            if event.sequence > third.sequence
            and event.type == EventType.RUN_FAILED
        ]
        terminal_failure_bound = bool(
            len(run_failed_after) == 1
            and run_failed_after[0].payload.get("error_type")
            == "SubmissionProtocolError"
            and run_failed_after[0].payload.get("error_code")
            == "SUBMISSION_PROTOCOL_ERROR"
            and run_failed_after[0].payload.get("message")
            == "structured review evidence was rejected three times"
        )
        terminal_ok = bool(
            not later_forbidden
            and terminal_failure_bound
            and not any(
                event.sequence > third.sequence
                and event.type == EventType.RUN_COMPLETED
                for event in events
            )
        )
        if not terminal_ok:
            failed_terminal_rejection_sequences.append(third.sequence)
            forbidden_after_terminal[third.sequence] = later_forbidden
    return not failed_terminal_rejection_sequences, {
        "mutation_epoch_count": len(mutations),
        "terminal_rejection_count": len(terminal_rejection_sequences),
        "terminal_rejection_sequences": terminal_rejection_sequences,
        "verified_terminal_rejection_count": (
            len(terminal_rejection_sequences)
            - len(failed_terminal_rejection_sequences)
        ),
        "failed_terminal_rejection_sequences": (
            failed_terminal_rejection_sequences
        ),
        "forbidden_after_terminal_sequences": forbidden_after_terminal,
        "reset_mutation_sequences": reset_mutation_sequences,
    }


def _v10_base_provenance_source_evidence(
    *,
    root: Path,
    manifest: RunManifest,
    events: list[Any],
) -> dict[str, Any]:
    """Bind the V10 nested provenance descriptor and exact CAS bytes."""

    started = [
        event for event in events if event.type == EventType.RUN_STARTED
    ]
    details: dict[str, Any] = {
        "run_started_count": len(started),
        "event_sequence": None,
        "event_identity_valid": False,
        "descriptor": None,
        "cas": None,
        "json_object_valid": False,
    }
    if len(started) != 1:
        return details
    event = started[0]
    details["event_sequence"] = event.sequence
    raw_descriptor = event.payload.get(
        "public_review_base_provenance_artifact"
    )
    cas_valid, cas_item, content = _nested_cas_artifact_evidence(
        artifact_root=(root / "artifacts").resolve(),
        event_id=event.event_id,
        role="public-review-base-provenance",
        raw_artifact=raw_descriptor,
    )
    details["cas"] = cas_item
    try:
        descriptor = Artifact.model_validate(raw_descriptor)
        details["descriptor"] = descriptor.model_dump(mode="json")
        document = (
            json.loads(content.decode("utf-8", errors="strict"))
            if content is not None
            else None
        )
        details["json_object_valid"] = isinstance(document, dict)
        details["event_identity_valid"] = bool(
            event.actor == "runner"
            and event.run_id == manifest.run_id
            and event.payload.get("task_id") == manifest.task_id
            and descriptor.media_type
            == "application/json; charset=utf-8"
            and cas_valid
        )
    except (UnicodeDecodeError, ValueError, RecoveryError):
        pass
    return details


def _v10_public_coverage_contract_evidence(
    *,
    root: Path,
    manifest: RunManifest,
    package: TaskPackage,
    events: list[Any],
) -> tuple[bool, dict[str, Any]]:
    """Validate the ordered, public-only V10 coverage contract."""

    from patchloop.agent.review import (
        validate_public_review_base_provenance_document,
        validate_public_review_contract,
    )

    contract = manifest.public_review_contract
    target_ids: list[str] = []
    requirement_ids: list[str] = []
    contract_valid = False
    if contract is not None:
        requirement_ids = [
            requirement.requirement_id
            for requirement in contract.requirements
        ]
        target_ids = [
            target.coverage_target_id
            for requirement in contract.requirements
            for target in requirement.coverage_targets
        ]
        try:
            validate_public_review_contract(
                contract,
                task=package.public,
                public_spec_hash=package.public_spec_hash,
            )
            contract_valid = True
        except ContractError:
            contract_valid = False
    v10_selector = bool(
        manifest.tool_schema_version == "v5"
        and manifest.context_policy_version == "phase-evidence-v10"
        and (
            (
                manifest.model.provider == "mock"
                and manifest.experiment is None
            )
            or (
                manifest.model.provider == "openai"
                and manifest.experiment is not None
                and manifest.experiment.purpose
                == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT
            )
        )
    )
    v11_selector = bool(
        manifest.tool_schema_version == "v6"
        and manifest.context_policy_version == "phase-evidence-v11"
        and manifest.model.provider == "mock"
        and manifest.experiment is None
    )
    exact_selector = v10_selector or v11_selector
    started = [
        event for event in events if event.type == EventType.RUN_STARTED
    ]
    base_provenance_valid = False
    base_provenance_event_sequence: int | None = None
    base_provenance_descriptor: dict[str, Any] | None = None
    base_provenance_cas: dict[str, Any] | None = None
    base_provenance_document: dict[str, Any] | None = None
    if len(started) == 1 and contract is not None:
        event = started[0]
        base_provenance_event_sequence = event.sequence
        raw_descriptor = event.payload.get(
            "public_review_base_provenance_artifact"
        )
        cas_valid, cas_item, content = _nested_cas_artifact_evidence(
            artifact_root=(root / "artifacts").resolve(),
            event_id=event.event_id,
            role="public-review-base-provenance",
            raw_artifact=raw_descriptor,
        )
        base_provenance_cas = cas_item
        try:
            descriptor = Artifact.model_validate(raw_descriptor)
            base_provenance_descriptor = descriptor.model_dump(mode="json")
            document = (
                json.loads(content.decode("utf-8", errors="strict"))
                if content is not None
                else None
            )
            base_provenance_document = (
                validate_public_review_base_provenance_document(
                    document,
                    contract=contract,
                    repository_url=package.public.repository.url,
                    base_commit=package.public.repository.base_commit,
                )
            )
            base_provenance_valid = bool(
                cas_valid
                and event.actor == "runner"
                and event.run_id == manifest.run_id
                and event.payload.get("task_id") == manifest.task_id
                and descriptor.media_type
                == "application/json; charset=utf-8"
            )
        except (
            UnicodeDecodeError,
            ValueError,
            RecoveryError,
            ContractError,
        ):
            base_provenance_valid = False
    passed = bool(
        exact_selector
        and contract_valid
        and base_provenance_valid
        and contract is not None
        and contract.schema_version == "public-review-contract-v2"
        and bool(requirement_ids)
        and len(requirement_ids) == len(set(requirement_ids))
        and bool(target_ids)
        and len(target_ids) == len(set(target_ids))
        and all(
            requirement.coverage_targets
            for requirement in contract.requirements
        )
    )
    return passed, {
        "selector_valid": exact_selector,
        "contract_declared": contract is not None,
        "contract_schema_version": (
            contract.schema_version if contract is not None else None
        ),
        "contract_content_hash": (
            contract.content_hash if contract is not None else None
        ),
        "requirement_ids": requirement_ids,
        "coverage_target_ids": target_ids,
        "coverage_target_count": len(target_ids),
        "base_provenance_valid": base_provenance_valid,
        "base_provenance_event_sequence": (
            base_provenance_event_sequence
        ),
        "base_provenance_descriptor": base_provenance_descriptor,
        "base_provenance_cas": base_provenance_cas,
        "base_provenance_document": base_provenance_document,
    }


def _v10_review_evidence_context_contract(
    *,
    root: Path,
    manifest: RunManifest,
    package: TaskPackage,
    events: list[Any],
    context_events: list[Any],
) -> tuple[bool, dict[str, Any]]:
    """Independently rebuild ordered V10/V11 target-to-evidence authority."""

    from patchloop.agent.context import REVIEW_EVIDENCE_V2_SCHEMA
    from patchloop.agent.phases import diff_bound_evidence

    contract = manifest.public_review_contract
    expected_context_schema = (
        "context-build-evidence-v11"
        if manifest.context_policy_version == "phase-evidence-v11"
        else "context-build-evidence-v10"
    )
    if contract is None or contract.schema_version != "public-review-contract-v2":
        return False, {
            "context_count": len(context_events),
            "verified_context_count": 0,
            "active_context_sequences": [],
            "failed_context_sequences": [
                event.sequence for event in context_events
            ],
            "failure_reasons": [
                {
                    "sequence": event.sequence,
                    "reason": "v10 public coverage contract is unavailable",
                }
                for event in context_events
            ],
        }
    ordered_targets = [
        target
        for requirement in contract.requirements
        for target in requirement.coverage_targets
    ]
    target_ids = [target.coverage_target_id for target in ordered_targets]
    artifact_root = root / "artifacts"
    artifact_store = ArtifactStore(artifact_root)
    failed_sequences: list[int] = []
    failure_reasons: list[dict[str, Any]] = []
    active_sequences: list[int] = []
    verified_target_sequences: list[int] = []
    for context_event in context_events:
        try:
            request_valid, request_evidence = _request_evidence_payload(
                context_event,
                artifact_root=artifact_root,
                expected_provider=manifest.model.provider,
            )
            if not request_valid or request_evidence is None:
                raise RecoveryError("v10 request evidence is invalid")
            rendered = _request_context(
                request_evidence["request_body"],
                allow_direct_context=True,
            )
            parsed = json.loads(rendered) if rendered is not None else None
            context_build = request_evidence.get("context_build")
            visible = (
                parsed.get("review_evidence")
                if isinstance(parsed, dict)
                else None
            )
            build = (
                context_build.get("review_evidence")
                if isinstance(context_build, dict)
                else None
            )
            if (
                not isinstance(parsed, dict)
                or not isinstance(context_build, dict)
                or context_build.get("schema_version")
                != expected_context_schema
                or not isinstance(visible, dict)
                or not isinstance(build, dict)
                or visible.get("schema_version")
                != REVIEW_EVIDENCE_V2_SCHEMA
                or build.get("schema_version")
                != REVIEW_EVIDENCE_V2_SCHEMA
                or parsed.get("public_review_contract")
                != contract.model_dump(mode="json")
            ):
                raise RecoveryError("v10 review evidence envelope is invalid")
            checkpoint = parsed.get("checkpoint")
            phase = Phase(parsed.get("phase"))
            diff_hash = (
                checkpoint.get("worktree_diff_hash")
                if isinstance(checkpoint, dict)
                else _EMPTY_DIFF_HASH
            )
            if not isinstance(diff_hash, str):
                raise RecoveryError("v10 review evidence has no diff identity")
            source_events = [
                event
                for event in events
                if event.sequence < context_event.sequence
            ]
            readiness = diff_bound_evidence(
                package.public,
                source_events,
                diff_hash,
                phase=phase,
                structured_review_required=True,
                coverage_review_required=True,
                probe_available=bool(package.public.probe_profiles),
            )
            active = bool(
                phase == Phase.REVIEW
                and readiness.mutation_present
                and not readiness.pending_checks
                and readiness.review_event_sequence is not None
            )
            events_by_sequence = {
                event.sequence: event for event in source_events
            }
            rendered_by_sequence: dict[
                int,
                tuple[dict[str, Any], dict[str, Any]],
            ] = {}

            def render_anchor(
                source_event: Any,
                *,
                cache: dict[
                    int,
                    tuple[dict[str, Any], dict[str, Any]],
                ] = rendered_by_sequence,
                expected_diff_hash: str = diff_hash,
            ) -> tuple[dict[str, Any], dict[str, Any]]:
                cached = cache.get(source_event.sequence)
                if cached is not None:
                    return cached
                rendered_anchor, tool_anchor = _v10_recompute_review_anchor(
                    source_event,
                    artifact_store=artifact_store,
                )
                if (
                    tool_anchor.get("worktree_diff_hash")
                    != expected_diff_hash
                ):
                    raise RecoveryError(
                        "v10 review anchor is not bound to the current diff"
                    )
                cache[source_event.sequence] = (
                    rendered_anchor,
                    tool_anchor,
                )
                return rendered_anchor, tool_anchor

            target_mapping: dict[str, list[int]] = {
                target_id: [] for target_id in target_ids
            }
            if active:
                mutation_sequence = readiness.mutation_event_sequence
                if type(mutation_sequence) is not int:
                    raise RecoveryError("v10 mutation identity is invalid")
                passing_events = [
                    events_by_sequence[sequence]
                    for sequence in readiness.current_diff_check_event_sequences
                ]
                inspection_candidates = [
                    event
                    for event in reversed(source_events)
                    if event.sequence > mutation_sequence
                    and event.type == EventType.TOOL_SUCCEEDED
                    and event.payload.get("tool") == "read_file"
                    and event.payload.get("worktree_diff_hash") == diff_hash
                ]
                for target in ordered_targets:
                    if target.evidence_kind == "passing_validation":
                        target_mapping[target.coverage_target_id] = sorted(
                            {
                                event.sequence
                                for event in passing_events
                                if event.payload.get("check_id")
                                in target.check_ids
                            }
                        )
                        continue
                    for candidate in inspection_candidates:
                        rendered_anchor, _ = render_anchor(candidate)
                        tool_result = rendered_anchor["payload"].get(
                            "tool_result"
                        )
                        content = (
                            tool_result.get("content")
                            if isinstance(tool_result, dict)
                            else None
                        )
                        if (
                            isinstance(tool_result, dict)
                            and tool_result.get("path") == target.path
                            and isinstance(content, str)
                            and target.anchor in content
                        ):
                            target_mapping[target.coverage_target_id] = [
                                candidate.sequence
                            ]
                            break

            requested_sequences: list[int] = []
            for sequences in target_mapping.values():
                for sequence in sequences:
                    if sequence not in requested_sequences:
                        requested_sequences.append(sequence)
            if active:
                for sequence in readiness.current_diff_check_event_sequences:
                    if sequence not in requested_sequences:
                        requested_sequences.append(sequence)
                source_sequence = readiness.review_event_sequence
                if (
                    type(source_sequence) is int
                    and source_sequence not in requested_sequences
                ):
                    requested_sequences.append(source_sequence)

            expected_pinned_results: list[dict[str, Any]] = []
            expected_pinned_tool_results: list[dict[str, Any]] = []
            complete_sequences: list[int] = []
            incomplete_sequences: list[int] = []
            for sequence in requested_sequences:
                source_event = events_by_sequence.get(sequence)
                if source_event is None:
                    raise RecoveryError(
                        "v10 review anchor durable event is unavailable"
                    )
                rendered_anchor, tool_anchor = render_anchor(source_event)
                expected_pinned_results.append(rendered_anchor)
                expected_pinned_tool_results.append(tool_anchor)
                if (
                    tool_anchor.get("available") is True
                    and tool_anchor.get("truncated") is False
                ):
                    complete_sequences.append(sequence)
                else:
                    incomplete_sequences.append(sequence)
            complete_set = set(complete_sequences)
            target_mapping = {
                target_id: [
                    sequence
                    for sequence in sequences
                    if sequence in complete_set
                ]
                for target_id, sequences in target_mapping.items()
            }
            passing_sequences = [
                sequence
                for sequence in readiness.current_diff_check_event_sequences
                if sequence in complete_set
            ]
            source_get_diff_sequence = (
                readiness.review_event_sequence
                if readiness.review_event_sequence in complete_set
                else None
            )
            citable: list[int] = []
            for sequences in target_mapping.values():
                for sequence in sequences:
                    if sequence not in citable:
                        citable.append(sequence)
            for sequence in passing_sequences:
                if sequence not in citable:
                    citable.append(sequence)
            if (
                source_get_diff_sequence is not None
                and source_get_diff_sequence not in citable
            ):
                citable.append(source_get_diff_sequence)
            visible_fields = {
                "schema_version": REVIEW_EVIDENCE_V2_SCHEMA,
                "pinning_active": active,
                "worktree_diff_hash": diff_hash,
                "mutation_event_sequence": readiness.mutation_event_sequence,
                "coverage_target_event_sequences": target_mapping,
                "passing_check_event_sequences": passing_sequences,
                "source_get_diff_sequence": source_get_diff_sequence,
                "citable_event_sequences": citable,
                "incomplete_event_sequences": incomplete_sequences,
            }
            if set(visible) != {
                *visible_fields,
                "pinned_results",
                "citation_rule",
            } or set(build) != {
                *visible_fields,
                "pinned_tool_results",
            }:
                raise RecoveryError(
                    "v10 review evidence has unknown or missing fields"
                )
            if any(
                canonical_json(visible.get(key)) != canonical_json(value)
                or canonical_json(build.get(key)) != canonical_json(value)
                for key, value in visible_fields.items()
            ):
                raise RecoveryError(
                    "v10 target evidence failed prefix recomputation"
                )
            if visible.get("pinned_results") != expected_pinned_results or build.get(
                "pinned_tool_results"
            ) != expected_pinned_tool_results:
                raise RecoveryError(
                    "v10 pinned target evidence failed CAS recomputation"
                )
            expected_rule = (
                "review_task may cite only citable_event_sequences and must "
                "resolve every public coverage target; investigation_ledger "
                "source_call_sequence values are not review citations"
            )
            if visible.get("citation_rule") != expected_rule:
                raise RecoveryError("v10 review citation rule is invalid")
            event_mirrors = {
                "review_evidence_pinning_active": active,
                "review_evidence_worktree_diff_hash": diff_hash,
                "review_evidence_mutation_event_sequence": (
                    readiness.mutation_event_sequence
                ),
                "review_evidence_coverage_target_event_sequences": (
                    target_mapping
                ),
                "review_evidence_passing_check_event_sequences": (
                    passing_sequences
                ),
                "review_evidence_source_get_diff_sequence": (
                    source_get_diff_sequence
                ),
                "review_evidence_citable_event_sequences": citable,
                "review_evidence_incomplete_event_sequences": (
                    incomplete_sequences
                ),
            }
            if any(
                canonical_json(context_event.payload.get(key))
                != canonical_json(value)
                for key, value in event_mirrors.items()
            ):
                raise RecoveryError("v10 ContextBuilt mirrors are invalid")
            phase_contract = parsed.get("phase_contract")
            if (
                not isinstance(phase_contract, dict)
                or phase_contract.get("schema_version")
                != "phase-contract-v4"
                or phase_contract.get("task_review_coverage_complete")
                != readiness.task_review_coverage_complete
                or phase_contract.get("unresolved_coverage_target_ids")
                != list(readiness.unresolved_coverage_target_ids)
            ):
                raise RecoveryError("v10 coverage phase contract is invalid")
            recent_events = parsed.get("recent_events")
            recent_sequences = (
                [item.get("sequence") for item in recent_events]
                if isinstance(recent_events, list)
                and all(isinstance(item, dict) for item in recent_events)
                else None
            )
            pinned_sequences = [
                item["sequence"] for item in expected_pinned_results
            ]
            if (
                recent_sequences is None
                or any(type(sequence) is not int for sequence in recent_sequences)
                or len(pinned_sequences) != len(set(pinned_sequences))
                or set(pinned_sequences).intersection(recent_sequences)
            ):
                raise RecoveryError(
                    "v10 review anchors are duplicated in recent events"
                )
            presented = context_build.get("tool_results")
            if not isinstance(presented, list):
                raise RecoveryError("v10 presented tool results are invalid")
            for expected in expected_pinned_tool_results:
                matches = [
                    item
                    for item in presented
                    if isinstance(item, dict)
                    and item.get("event_sequence")
                    == expected["event_sequence"]
                    and canonical_json(item) == canonical_json(expected)
                ]
                if len(matches) != 1:
                    raise RecoveryError(
                        "v10 target presentation failed CAS recomputation"
                    )
            if active:
                active_sequences.append(context_event.sequence)
                verified_target_sequences.extend(
                    sequence
                    for sequences in target_mapping.values()
                    for sequence in sequences
                )
        except (
            KeyError,
            OSError,
            RecoveryError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            failed_sequences.append(context_event.sequence)
            failure_reasons.append(
                {"sequence": context_event.sequence, "reason": str(exc)}
            )
    return bool(context_events) and not failed_sequences, {
        "context_count": len(context_events),
        "verified_context_count": len(context_events) - len(failed_sequences),
        "active_context_sequences": active_sequences,
        "verified_target_sequences": sorted(set(verified_target_sequences)),
        "failed_context_sequences": failed_sequences,
        "failure_reasons": failure_reasons,
    }


def _v10_validate_review_supporting_rows(
    *,
    artifact_store: ArtifactStore,
    events: list[Any],
    call_sequence: int,
    mutation_sequence: int,
    worktree_diff_hash: str,
    review_evidence: dict[str, Any],
    execution_context: dict[str, Any],
    arguments: dict[str, Any],
    review_document: dict[str, Any],
    result_document: dict[str, Any],
    outcome: Any,
    authoritative_requirement_ids: list[str],
    nonverified_requirement_ids: set[str],
) -> None:
    """Validate V10 validation and residual-risk rows independently of coverage."""

    citable = review_evidence.get("citable_event_sequences")
    presented = execution_context.get("presented_tool_results")
    if (
        not isinstance(citable, list)
        or any(type(sequence) is not int for sequence in citable)
        or len(citable) != len(set(citable))
        or not isinstance(presented, list)
    ):
        raise RecoveryError("v10 supporting evidence authority is invalid")
    citable_set = set(citable)
    complete_presented = {
        item["event_sequence"]
        for item in presented
        if (
            isinstance(item, dict)
            and type(item.get("event_sequence")) is int
            and item.get("available") is True
            and item.get("truncated") is False
        )
    }
    events_by_sequence = {event.sequence: event for event in events}
    raw_validation = arguments.get("targeted_validation")
    if not isinstance(raw_validation, list) or not 1 <= len(raw_validation) <= 20:
        raise RecoveryError("v10 targeted validation shape is invalid")
    normalized_validation: list[dict[str, Any]] = []
    seen_sequences: set[int] = set()
    passing_validation = False
    expected_tools = {
        "probe": {"run_probe"},
        "registered_check": {"run_check"},
        "repository_evidence": {"read_file", "search_files", "get_diff"},
    }
    for row in raw_validation:
        if not isinstance(row, dict) or set(row) != {
            "kind",
            "event_sequence",
            "outcome",
            "notes",
        }:
            raise RecoveryError("v10 targeted validation row is invalid")
        kind = row.get("kind")
        sequence = row.get("event_sequence")
        declared_outcome = row.get("outcome")
        notes = row.get("notes")
        source = (
            events_by_sequence.get(sequence)
            if type(sequence) is int
            else None
        )
        if (
            kind not in expected_tools
            or type(sequence) is not int
            or sequence in seen_sequences
            or sequence <= mutation_sequence
            or sequence >= call_sequence
            or sequence not in citable_set
            or sequence not in complete_presented
            or declared_outcome not in {"passed", "failed", "inconclusive"}
            or not isinstance(notes, str)
            or not notes.strip()
            or len(notes) > 2000
            or source is None
            or source.type != EventType.TOOL_SUCCEEDED
            or source.payload.get("tool") not in expected_tools[kind]
            or source.payload.get("worktree_diff_hash") != worktree_diff_hash
        ):
            raise RecoveryError("v10 targeted validation evidence is invalid")
        if source.payload.get("tool") in {"run_check", "read_file"}:
            _, source_evidence = _v10_recompute_review_anchor(
                source,
                artifact_store=artifact_store,
            )
            if (
                source_evidence.get("available") is not True
                or source_evidence.get("truncated") is not False
            ):
                raise RecoveryError(
                    "v10 targeted validation result is incomplete"
                )
        if source.payload.get("timed_out") is True:
            actual_outcome = "inconclusive"
        elif kind in {"probe", "registered_check"}:
            actual_outcome = (
                "passed"
                if source.payload.get("passed") is True
                else "failed"
            )
        else:
            actual_outcome = "passed"
        if declared_outcome != actual_outcome:
            raise RecoveryError("v10 targeted validation outcome is invalid")
        if kind in {"probe", "registered_check"} and actual_outcome == "passed":
            passing_validation = True
        seen_sequences.add(sequence)
        normalized_validation.append(
            {
                "kind": kind,
                "event_sequence": sequence,
                "outcome": declared_outcome,
                "notes": notes.strip(),
            }
        )
    if not passing_validation:
        raise RecoveryError("v10 review has no passing targeted validation")
    if (
        review_document.get("targeted_validation") != normalized_validation
        or result_document.get("targeted_validation_count")
        != len(normalized_validation)
        or outcome.payload.get("targeted_validation_count")
        != len(normalized_validation)
    ):
        raise RecoveryError("v10 targeted validation artifact is invalid")

    raw_risks = arguments.get("residual_risks")
    if not isinstance(raw_risks, list) or len(raw_risks) > 20:
        raise RecoveryError("v10 residual-risk shape is invalid")
    authoritative_ids = set(authoritative_requirement_ids)
    covered_risk_ids: set[str] = set()
    normalized_risks: list[dict[str, Any]] = []
    for row in raw_risks:
        if not isinstance(row, dict) or set(row) != {
            "requirement_ids",
            "risk",
            "mitigation",
        }:
            raise RecoveryError("v10 residual-risk row is invalid")
        requirement_ids = row.get("requirement_ids")
        risk = row.get("risk")
        mitigation = row.get("mitigation")
        if (
            not isinstance(requirement_ids, list)
            or not requirement_ids
            or len(requirement_ids) > 20
            or len(requirement_ids) != len(set(requirement_ids))
            or any(
                not isinstance(requirement_id, str)
                or requirement_id not in authoritative_ids
                for requirement_id in requirement_ids
            )
            or not isinstance(risk, str)
            or not risk.strip()
            or len(risk) > 1000
            or not isinstance(mitigation, str)
            or not mitigation.strip()
            or len(mitigation) > 1000
        ):
            raise RecoveryError("v10 residual-risk fields are invalid")
        covered_risk_ids.update(requirement_ids)
        normalized_risks.append(
            {
                "requirement_ids": list(requirement_ids),
                "risk": risk.strip(),
                "mitigation": mitigation.strip(),
            }
        )
    if not nonverified_requirement_ids.issubset(covered_risk_ids):
        raise RecoveryError("v10 unresolved requirement lacks a residual risk")
    if (
        review_document.get("residual_risks") != normalized_risks
        or result_document.get("residual_risk_count") != len(normalized_risks)
        or outcome.payload.get("residual_risk_count") != len(normalized_risks)
    ):
        raise RecoveryError("v10 residual-risk artifact is invalid")


def _v10_coverage_decision_evidence(
    *,
    root: Path,
    manifest: RunManifest,
    package: TaskPackage,
    events: list[Any],
    context_events: list[Any],
) -> tuple[bool, dict[str, Any]]:
    """Recompute every V10/V11 review decision from request and result CAS bytes."""

    context_ok, context_details = _v10_review_evidence_context_contract(
        root=root,
        manifest=manifest,
        package=package,
        events=events,
        context_events=context_events,
    )
    expected_context_schema = (
        "context-build-evidence-v11"
        if manifest.context_policy_version == "phase-evidence-v11"
        else "context-build-evidence-v10"
    )
    contract = manifest.public_review_contract
    if contract is None or contract.schema_version != "public-review-contract-v2":
        return False, {
            "context_contract_valid": context_ok,
            "review_call_count": 0,
            "verified_review_count": 0,
            "verified_review_sequences": [],
            "coverage_complete_review_count": 0,
            "coverage_complete_review_sequences": [],
            "failed_review_call_sequences": [],
            "context_details": context_details,
        }
    requirements = list(contract.requirements)
    requirement_ids = [item.requirement_id for item in requirements]
    requirement_by_id = {
        item.requirement_id: item for item in requirements
    }
    targets = [
        target
        for requirement in requirements
        for target in requirement.coverage_targets
    ]
    target_ids = [target.coverage_target_id for target in targets]
    target_by_id = {target.coverage_target_id: target for target in targets}
    target_parent = {
        target.coverage_target_id: requirement.requirement_id
        for requirement in requirements
        for target in requirement.coverage_targets
    }
    allow_reordered_input = (
        manifest.context_policy_version == "phase-evidence-v11"
    )
    artifact_root = (root / "artifacts").resolve()
    artifact_store = ArtifactStore(artifact_root)
    calls = [
        event
        for event in events
        if event.type == EventType.TOOL_CALLED
        and event.payload.get("tool") == "review_task"
    ]
    outcomes = [
        event
        for event in events
        if event.type in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}
        and event.payload.get("tool") == "review_task"
    ]
    failed_calls: list[int] = []
    failure_reasons: list[dict[str, Any]] = []
    verified_reviews: list[int] = []
    coverage_complete_reviews: list[int] = []
    for call in calls:
        try:
            matching_outcomes = [
                event
                for event in outcomes
                if event.correlation_id == call.correlation_id
                and event.sequence > call.sequence
            ]
            if (
                call.actor != "agent"
                or not isinstance(call.correlation_id, str)
                or not call.correlation_id
                or len(matching_outcomes) != 1
            ):
                raise RecoveryError("v10 review action lifecycle is ambiguous")
            outcome = matching_outcomes[0]
            input_valid, input_item, input_bytes = (
                _nested_cas_artifact_evidence(
                    artifact_root=artifact_root,
                    event_id=call.event_id,
                    role="review-task-input",
                    raw_artifact=call.payload.get("input_artifact"),
                )
            )
            if not input_valid or input_bytes is None:
                raise RecoveryError("v10 review input CAS is invalid")
            input_document = json.loads(input_bytes.decode("utf-8"))
            arguments = (
                input_document.get("input")
                if isinstance(input_document, dict)
                else None
            )
            execution_context = (
                input_document.get("execution_context")
                if isinstance(input_document, dict)
                else None
            )
            expected_input_hash = (
                sha256_text(
                    canonical_json(
                        {"tool": "review_task", "input": arguments}
                    )
                )
                if isinstance(arguments, dict)
                else None
            )
            diff_hash = call.payload.get("worktree_diff_hash")
            expected_normalized_hash = (
                sha256_text(
                    canonical_json(
                        {
                            "tool": "review_task",
                            "input": arguments,
                            "worktree_diff_hash": diff_hash,
                            "state_marker": None,
                        }
                    )
                )
                if isinstance(arguments, dict)
                and isinstance(diff_hash, str)
                else None
            )
            expected_execution_context_keys = {
                "request_artifact_id",
                "phase",
                "presented_tool_results",
                "review_evidence",
            }
            if manifest.context_policy_version == "phase-evidence-v11":
                expected_execution_context_keys.add(
                    "coverage_rejection_feedback"
                )
            if (
                call.actor != "agent"
                or not isinstance(input_document, dict)
                or set(input_document)
                != {"tool", "input", "execution_context"}
                or input_document.get("tool") != "review_task"
                or not isinstance(arguments, dict)
                or set(arguments)
                != {
                    "requirements",
                    "coverage_targets",
                    "targeted_validation",
                    "residual_risks",
                }
                or not isinstance(execution_context, dict)
                or set(execution_context)
                != expected_execution_context_keys
                or execution_context.get("phase") != "REVIEW"
                or call.payload.get("artifact_id")
                != input_item.get("artifact_id")
                or call.payload.get("artifact_path")
                != input_item.get("declared_path")
                or call.payload.get("input_hash") != expected_input_hash
                or call.payload.get("normalized_call_hash")
                != expected_normalized_hash
                or call.payload.get("execution") != "dispatched"
                or call.payload.get("request_artifact_id")
                != execution_context.get("request_artifact_id")
                or call.payload.get("request_phase") != "REVIEW"
            ):
                raise RecoveryError("v10 review input binding is invalid")
            request_artifact_id = execution_context[
                "request_artifact_id"
            ]
            matching_contexts = [
                event
                for event in context_events
                if event.sequence < call.sequence
                and event.payload.get("artifact_id") == request_artifact_id
            ]
            if len(matching_contexts) != 1:
                raise RecoveryError("v10 review request context is ambiguous")
            context_event = matching_contexts[0]
            request_valid, request_evidence = _request_evidence_payload(
                context_event,
                artifact_root=artifact_root,
                expected_provider=manifest.model.provider,
            )
            context_build = (
                request_evidence.get("context_build")
                if isinstance(request_evidence, dict)
                else None
            )
            review_evidence = (
                context_build.get("review_evidence")
                if isinstance(context_build, dict)
                else None
            )
            model_calls = [
                event
                for event in events
                if event.type == EventType.MODEL_CALLED
                and event.payload.get("request_artifact_id")
                == request_artifact_id
                and context_event.sequence < event.sequence < call.sequence
            ]
            if (
                not request_valid
                or not isinstance(request_evidence, dict)
                or not _request_runtime_contract_valid(
                    request_evidence.get("request_body"),
                    manifest,
                )
                or not isinstance(context_build, dict)
                or context_build.get("schema_version")
                != expected_context_schema
                or not isinstance(review_evidence, dict)
                or review_evidence.get("schema_version")
                != "review-evidence-v2"
                or execution_context.get("review_evidence")
                != review_evidence
                or execution_context.get("presented_tool_results")
                != context_build.get("tool_results")
                or set(
                    review_evidence.get(
                        "coverage_target_event_sequences",
                        {},
                    )
                )
                != set(target_ids)
                or len(model_calls) != 1
            ):
                raise RecoveryError("v10 review context binding is invalid")
            result_valid, result_item, result_bytes = (
                _nested_cas_artifact_evidence(
                    artifact_root=artifact_root,
                    event_id=outcome.event_id,
                    role="review-task-result",
                    raw_artifact=outcome.payload.get("result_artifact"),
                )
            )
            if (
                not result_valid
                or result_bytes is None
                or outcome.payload.get("artifact_id")
                != result_item.get("artifact_id")
                or outcome.payload.get("artifact_path")
                != result_item.get("declared_path")
            ):
                raise RecoveryError("v10 review result CAS is invalid")
            result_document = json.loads(result_bytes.decode("utf-8"))
            if outcome.type == EventType.TOOL_FAILED:
                if outcome.actor != "tool-gateway":
                    raise RecoveryError("v10 rejected review actor is invalid")
                continue
            if outcome.actor != "tool-gateway":
                raise RecoveryError("v10 accepted review actor is invalid")
            if not isinstance(result_document, dict):
                raise RecoveryError("v10 review result is not an object")
            review_valid, review_item, review_bytes = (
                _nested_cas_artifact_evidence(
                    artifact_root=artifact_root,
                    event_id=outcome.event_id,
                    role="task-review",
                    raw_artifact=outcome.payload.get("review_artifact"),
                )
            )
            if not review_valid or review_bytes is None:
                raise RecoveryError("v10 task review CAS is invalid")
            review_document = json.loads(review_bytes.decode("utf-8"))
            review_descriptor = outcome.payload.get("review_artifact")
            if (
                not isinstance(review_document, dict)
                or result_document.get("schema_version")
                != "task-review-result-v3"
                or result_document.get("review_schema_version")
                != "task-review-v3"
                or result_document.get("review") != review_document
                or result_document.get("review_artifact")
                != review_descriptor
                or result_document.get("review_content_hash")
                != review_item.get("actual_content_hash")
                or outcome.payload.get("review_content_hash")
                != review_item.get("actual_content_hash")
                or review_document.get("schema_version")
                != "task-review-v3"
                or review_document.get("run_id") != manifest.run_id
                or review_document.get("request_artifact_id")
                != request_artifact_id
                or review_document.get("worktree_diff_hash") != diff_hash
                or review_document.get("public_review_contract_hash")
                != contract.content_hash
                or review_document.get(
                    "public_review_contract_schema_version"
                )
                != "public-review-contract-v2"
                or review_document.get("authoritative_requirement_ids")
                != requirement_ids
                or review_document.get("deterministic_correctness_claimed")
                is not False
            ):
                raise RecoveryError("v10 review document binding is invalid")
            mutation_sequence = review_document.get(
                "mutation_event_sequence"
            )
            source_sequence = review_document.get(
                "source_get_diff_sequence"
            )
            mutation = next(
                (
                    event
                    for event in events
                    if event.sequence == mutation_sequence
                ),
                None,
            )
            source_diff = next(
                (
                    event
                    for event in events
                    if event.sequence == source_sequence
                ),
                None,
            )
            if (
                type(mutation_sequence) is not int
                or mutation is None
                or mutation.type != EventType.PATCH_APPLIED
                or mutation.payload.get("worktree_diff_hash") != diff_hash
                or type(source_sequence) is not int
                or source_diff is None
                or source_diff.type != EventType.TOOL_SUCCEEDED
                or source_diff.payload.get("tool") != "get_diff"
                or source_diff.payload.get("worktree_diff_hash") != diff_hash
                or review_evidence.get("mutation_event_sequence")
                != mutation_sequence
                or review_evidence.get("source_get_diff_sequence")
                != source_sequence
                or not mutation_sequence < source_sequence < call.sequence
                or any(
                    event.type == EventType.PATCH_APPLIED
                    and mutation_sequence < event.sequence < call.sequence
                    for event in events
                )
            ):
                raise RecoveryError("v10 review epoch binding is invalid")
            input_requirements = arguments.get("requirements")
            input_targets = arguments.get("coverage_targets")
            review_requirements = review_document.get("requirements")
            review_targets = review_document.get("coverage_targets")
            input_requirement_ids = (
                [
                    item.get("requirement_id")
                    for item in input_requirements
                    if isinstance(item, dict)
                ]
                if isinstance(input_requirements, list)
                else []
            )
            input_target_ids = (
                [
                    item.get("coverage_target_id")
                    for item in input_targets
                    if isinstance(item, dict)
                ]
                if isinstance(input_targets, list)
                else []
            )
            input_order_valid = (
                len(input_requirement_ids) == len(requirement_ids)
                and len(set(input_requirement_ids))
                == len(input_requirement_ids)
                and set(input_requirement_ids) == set(requirement_ids)
                and len(input_target_ids) == len(target_ids)
                and len(set(input_target_ids)) == len(input_target_ids)
                and set(input_target_ids) == set(target_ids)
            )
            if not allow_reordered_input:
                input_order_valid = bool(
                    input_order_valid
                    and input_requirement_ids == requirement_ids
                    and input_target_ids == target_ids
                )
            if (
                not isinstance(input_requirements, list)
                or not isinstance(input_targets, list)
                or not input_order_valid
                or not isinstance(review_requirements, list)
                or not isinstance(review_targets, list)
                or [
                    item.get("requirement_id")
                    for item in review_requirements
                    if isinstance(item, dict)
                ]
                != requirement_ids
                or [
                    item.get("coverage_target_id")
                    for item in review_targets
                    if isinstance(item, dict)
                ]
                != target_ids
            ):
                raise RecoveryError("v10 review row order is invalid")
            target_evidence = review_evidence[
                "coverage_target_event_sequences"
            ]
            input_targets_by_id = {
                item["coverage_target_id"]: item
                for item in input_targets
            }
            status_by_target: dict[str, str] = {}
            normalized_review_targets: list[dict[str, Any]] = []
            for review_row in review_targets:
                target_id = review_row.get("coverage_target_id")
                input_row = input_targets_by_id[target_id]
                target = target_by_id.get(target_id)
                status = input_row.get("status")
                sequences = input_row.get("evidence_event_sequences")
                advertised = target_evidence.get(target_id)
                if (
                    target is None
                    or status
                    not in {"verified", "partially_verified", "unverified"}
                    or not isinstance(sequences, list)
                    or any(type(sequence) is not int for sequence in sequences)
                    or not isinstance(advertised, list)
                    or (
                        status == "verified"
                        and (not advertised or sequences != advertised)
                    )
                    or (
                        status == "partially_verified"
                        and (
                            not sequences
                            or not set(sequences).issubset(advertised)
                        )
                    )
                    or (status == "unverified" and sequences)
                ):
                    raise RecoveryError(
                        "v10 target status or evidence is invalid"
                    )
                normalized_row = {
                    **input_row,
                    "requirement_id": target_parent[target_id],
                    "notes": str(input_row.get("notes", "")).strip(),
                }
                if review_row != normalized_row:
                    raise RecoveryError("v10 target artifact row is invalid")
                status_by_target[target_id] = status
                normalized_review_targets.append(normalized_row)
            input_requirements_by_id = {
                item["requirement_id"]: item
                for item in input_requirements
            }
            normalized_review_requirements: list[dict[str, Any]] = []
            for review_row in review_requirements:
                requirement_id = review_row.get("requirement_id")
                input_row = input_requirements_by_id[requirement_id]
                requirement = requirement_by_id.get(requirement_id)
                if requirement is None:
                    raise RecoveryError("v10 requirement row is unknown")
                child_ids = [
                    target.coverage_target_id
                    for target in requirement.coverage_targets
                ]
                child_statuses = [
                    status_by_target[target_id]
                    for target_id in child_ids
                ]
                expected_status = (
                    "verified"
                    if all(status == "verified" for status in child_statuses)
                    else (
                        "unverified"
                        if all(
                            status == "unverified"
                            for status in child_statuses
                        )
                        else "partially_verified"
                    )
                )
                expected_sequences: list[int] = []
                for target_id in child_ids:
                    target_row = next(
                        row
                        for row in normalized_review_targets
                        if row["coverage_target_id"] == target_id
                    )
                    for sequence in target_row["evidence_event_sequences"]:
                        if sequence not in expected_sequences:
                            expected_sequences.append(sequence)
                expected_row = {
                    **input_row,
                    "source_excerpt": requirement.source_excerpt,
                    "notes": str(input_row.get("notes", "")).strip(),
                }
                if (
                    input_row.get("status") != expected_status
                    or input_row.get("evidence_event_sequences")
                    != expected_sequences
                    or review_row != expected_row
                ):
                    raise RecoveryError(
                        "v10 requirement roll-up is invalid"
                    )
                normalized_review_requirements.append(expected_row)
            _v10_validate_review_supporting_rows(
                artifact_store=artifact_store,
                events=events,
                call_sequence=call.sequence,
                mutation_sequence=mutation_sequence,
                worktree_diff_hash=diff_hash,
                review_evidence=review_evidence,
                execution_context=execution_context,
                arguments=arguments,
                review_document=review_document,
                result_document=result_document,
                outcome=outcome,
                authoritative_requirement_ids=requirement_ids,
                nonverified_requirement_ids={
                    row["requirement_id"]
                    for row in normalized_review_requirements
                    if row["status"] != "verified"
                },
            )
            verified_target_ids = [
                target_id
                for target_id in target_ids
                if status_by_target[target_id] == "verified"
            ]
            unresolved_target_ids = [
                target_id
                for target_id in target_ids
                if status_by_target[target_id] != "verified"
            ]
            coverage_complete = not unresolved_target_ids
            expected_coverage = {
                "schema_version": "public-review-coverage-v1",
                "authoritative_coverage_target_ids": target_ids,
                "verified_coverage_target_ids": verified_target_ids,
                "unresolved_coverage_target_ids": unresolved_target_ids,
                "coverage_complete": coverage_complete,
                "ready_for_submission": coverage_complete,
                "deterministic_correctness_claimed": False,
            }
            if (
                review_document.get("public_review_coverage")
                != expected_coverage
                or result_document.get("public_review_coverage")
                != expected_coverage
                or result_document.get("coverage_target_count")
                != len(target_ids)
                or result_document.get("coverage_complete")
                is not coverage_complete
                or result_document.get("verified_coverage_target_ids")
                != verified_target_ids
                or result_document.get("unresolved_coverage_target_ids")
                != unresolved_target_ids
                or outcome.payload.get("coverage_target_count")
                != len(target_ids)
                or outcome.payload.get("coverage_complete")
                is not coverage_complete
                or outcome.payload.get("verified_coverage_target_ids")
                != verified_target_ids
                or outcome.payload.get("unresolved_coverage_target_ids")
                != unresolved_target_ids
                or outcome.payload.get("request_artifact_id")
                != request_artifact_id
                or outcome.payload.get("worktree_diff_hash") != diff_hash
                or outcome.payload.get("mutation_event_sequence")
                != mutation_sequence
                or outcome.payload.get("source_get_diff_sequence")
                != source_sequence
            ):
                raise RecoveryError("v10 coverage decision is invalid")
            verified_reviews.append(outcome.sequence)
            if coverage_complete:
                coverage_complete_reviews.append(outcome.sequence)
        except (
            KeyError,
            OSError,
            RecoveryError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            failed_calls.append(call.sequence)
            failure_reasons.append(
                {"sequence": call.sequence, "reason": str(exc)}
            )
    called_correlations = {call.correlation_id for call in calls}
    orphan_outcomes = [
        outcome.sequence
        for outcome in outcomes
        if outcome.correlation_id not in called_correlations
    ]
    passed = bool(
        context_ok
        and coverage_complete_reviews
        and not failed_calls
        and not orphan_outcomes
    )
    return passed, {
        "context_contract_valid": context_ok,
        "review_call_count": len(calls),
        "review_outcome_count": len(outcomes),
        "verified_review_count": len(verified_reviews),
        "verified_review_sequences": verified_reviews,
        "coverage_complete_review_count": len(coverage_complete_reviews),
        "coverage_complete_review_sequences": coverage_complete_reviews,
        "failed_review_call_sequences": failed_calls,
        "orphan_review_outcome_sequences": orphan_outcomes,
        "failure_reasons": failure_reasons,
        "context_details": context_details,
    }


def _v10_coverage_submission_evidence(
    *,
    root: Path,
    manifest: RunManifest,
    events: list[Any],
    context_events: list[Any],
    result: RunResult | None,
) -> tuple[bool, dict[str, Any]]:
    """Bind accepted finish provenance to one coverage-complete V10 review."""

    artifact_root = (root / "artifacts").resolve()
    accepted_events = [
        event
        for event in events
        if event.type == EventType.SUBMISSION_ACCEPTED
    ]
    finish_calls = [
        event
        for event in events
        if event.type == EventType.TOOL_CALLED
        and event.payload.get("tool") == "finish_task"
    ]
    failed_accepted_sequences: list[int] = []
    failure_reasons: list[dict[str, Any]] = []
    for accepted in accepted_events:
        try:
            correlated = [
                event
                for event in events
                if event.correlation_id == accepted.correlation_id
            ]
            calls = [
                event
                for event in correlated
                if event.type == EventType.TOOL_CALLED
                and event.payload.get("tool") == "finish_task"
            ]
            reviews = [
                event
                for event in correlated
                if event.type == EventType.REVIEW_RECORDED
            ]
            attempts = [
                event
                for event in correlated
                if event.type == EventType.SUBMISSION_ATTEMPTED
            ]
            outcomes = [
                event
                for event in correlated
                if event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool") == "finish_task"
            ]
            if not all(
                len(items) == 1
                for items in (calls, reviews, attempts, outcomes)
            ):
                raise RecoveryError("v10 accepted finish lifecycle is ambiguous")
            call = calls[0]
            recorded = reviews[0]
            attempt = attempts[0]
            finish_outcome = outcomes[0]
            recovery_result = call.payload.get("recovery_result")
            output = (
                recovery_result.get("output")
                if isinstance(recovery_result, dict)
                else None
            )
            if (
                not isinstance(recovery_result, dict)
                or recovery_result.get("action_id") != call.correlation_id
                or recovery_result.get("status") != "succeeded"
                or not isinstance(output, dict)
                or output.get("accepted_for_evaluation") is not True
            ):
                raise RecoveryError("v10 finish decision is not durable")
            review_sequence = output.get("source_task_review_sequence")
            source_review = next(
                (
                    event
                    for event in events
                    if event.sequence == review_sequence
                ),
                None,
            )
            raw_review_artifact = output.get("task_review_artifact")
            review_valid, review_item, review_bytes = (
                _nested_cas_artifact_evidence(
                    artifact_root=artifact_root,
                    event_id=call.event_id,
                    role="accepted-task-review",
                    raw_artifact=raw_review_artifact,
                )
            )
            review_document = (
                json.loads(review_bytes.decode("utf-8"))
                if review_valid and review_bytes is not None
                else None
            )
            diff_hash = output.get("worktree_diff_hash")
            source_diff_sequence = output.get("source_get_diff_sequence")
            request_artifact_id = output.get("request_artifact_id")
            matching_contexts = [
                event
                for event in context_events
                if event.sequence < call.sequence
                and event.payload.get("artifact_id") == request_artifact_id
            ]
            request_valid = False
            parsed_context = None
            context_build = None
            if len(matching_contexts) == 1:
                request_valid, request_evidence = _request_evidence_payload(
                    matching_contexts[0],
                    artifact_root=artifact_root,
                    expected_provider=manifest.model.provider,
                )
                if request_valid and request_evidence is not None:
                    rendered = _request_context(
                        request_evidence.get("request_body"),
                        allow_direct_context=True,
                    )
                    parsed_context = (
                        json.loads(rendered)
                        if isinstance(rendered, str)
                        else None
                    )
                    context_build = request_evidence.get("context_build")
            presented_results = (
                context_build.get("tool_results")
                if isinstance(context_build, dict)
                else None
            )
            phase_contract = (
                parsed_context.get("phase_contract")
                if isinstance(parsed_context, dict)
                else None
            )
            review_presented = bool(
                isinstance(presented_results, list)
                and sum(
                    isinstance(item, dict)
                    and item.get("event_sequence") == review_sequence
                    and item.get("available") is True
                    and item.get("truncated") is False
                    for item in presented_results
                )
                == 1
            )
            common_provenance = {
                "source_task_review_sequence": review_sequence,
                "task_review_artifact": raw_review_artifact,
                "task_review_content_hash": review_item.get(
                    "actual_content_hash"
                ),
            }
            if (
                type(review_sequence) is not int
                or source_review is None
                or source_review.type != EventType.TOOL_SUCCEEDED
                or source_review.payload.get("tool") != "review_task"
                or source_review.payload.get("coverage_complete") is not True
                or source_review.payload.get("review_artifact")
                != raw_review_artifact
                or source_review.payload.get("review_content_hash")
                != review_item.get("actual_content_hash")
                or not isinstance(review_document, dict)
                or review_document.get("schema_version")
                != "task-review-v3"
                or review_document.get("run_id") != manifest.run_id
                or review_document.get("worktree_diff_hash") != diff_hash
                or review_document.get("source_get_diff_sequence")
                != source_diff_sequence
                or review_document.get("public_review_coverage", {}).get(
                    "coverage_complete"
                )
                is not True
                or output.get("task_review_content_hash")
                != review_item.get("actual_content_hash")
                or not request_valid
                or not review_presented
                or not isinstance(phase_contract, dict)
                or phase_contract.get("schema_version")
                != "phase-contract-v4"
                or phase_contract.get("task_review_coverage_complete")
                is not True
                or phase_contract.get("unresolved_coverage_target_ids") != []
                or recorded.payload.get("worktree_diff_hash") != diff_hash
                or recorded.payload.get("source_get_diff_sequence")
                != source_diff_sequence
                or recorded.payload.get("request_artifact_id")
                != request_artifact_id
                or any(
                    recorded.payload.get(key) != value
                    for key, value in common_provenance.items()
                )
                or attempt.payload.get("attempt_number")
                != accepted.payload.get("attempt_number")
                or attempt.payload.get("worktree_diff_hash") != diff_hash
                or finish_outcome.payload.get("worktree_diff_hash")
                != diff_hash
                or any(
                    finish_outcome.payload.get(key) != value
                    for key, value in common_provenance.items()
                )
                or accepted.payload.get("worktree_diff_hash") != diff_hash
                or accepted.payload.get("accepted_for")
                != "deterministic_evaluation"
                or accepted.payload.get("evaluation_success_claimed")
                is not False
                or any(
                    accepted.payload.get(key) != value
                    for key, value in common_provenance.items()
                )
                or not (
                    source_review.sequence
                    < call.sequence
                    < recorded.sequence
                    < attempt.sequence
                    < finish_outcome.sequence
                    < accepted.sequence
                )
            ):
                raise RecoveryError(
                    "v10 accepted submission provenance is invalid"
                )
        except (
            KeyError,
            OSError,
            RecoveryError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            failed_accepted_sequences.append(accepted.sequence)
            failure_reasons.append(
                {"sequence": accepted.sequence, "reason": str(exc)}
            )
    evaluation_completed = bool(
        result is not None and result.evaluation_status == "completed"
    )
    cardinality_valid = bool(
        evaluation_completed
        and len(accepted_events) == 1
        and bool(finish_calls)
    )
    return bool(cardinality_valid and not failed_accepted_sequences), {
        "finish_call_count": len(finish_calls),
        "accepted_submission_count": len(accepted_events),
        "evaluation_completed": evaluation_completed,
        "cardinality_valid": cardinality_valid,
        "failed_accepted_sequences": failed_accepted_sequences,
        "failure_reasons": failure_reasons,
    }


def _v10_coverage_recovery_evidence(
    events: list[Any],
) -> tuple[bool, dict[str, Any]]:
    """Verify review and finish action histories are exact idempotent prefixes."""

    calls = [
        event
        for event in events
        if event.type == EventType.TOOL_CALLED
        and event.payload.get("tool") in {"review_task", "finish_task"}
    ]
    failed_sequences: list[int] = []
    prefix_shapes: dict[int, list[str]] = {}
    for call in calls:
        correlated = sorted(
            (
                event
                for event in events
                if event.correlation_id == call.correlation_id
                and event.type
                in {
                    EventType.TOOL_CALLED,
                    EventType.TOOL_SUCCEEDED,
                    EventType.TOOL_FAILED,
                    EventType.REVIEW_RECORDED,
                    EventType.SUBMISSION_ATTEMPTED,
                    EventType.SUBMISSION_REJECTED,
                    EventType.SUBMISSION_ACCEPTED,
                }
            ),
            key=lambda event: event.sequence,
        )
        actual = [event.type for event in correlated]
        prefix_shapes[call.sequence] = [item.value for item in actual]
        valid = bool(
            actual
            and actual[0] == EventType.TOOL_CALLED
            and len(
                [
                    event
                    for event in correlated
                    if event.type == EventType.TOOL_CALLED
                ]
            )
            == 1
        )
        if call.payload.get("tool") == "review_task":
            valid = bool(
                valid
                and len(actual) == 2
                and actual[1]
                in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}
            )
        else:
            recovery_result = call.payload.get("recovery_result")
            accepted = bool(
                isinstance(recovery_result, dict)
                and recovery_result.get("status") == "succeeded"
                and isinstance(recovery_result.get("output"), dict)
                and recovery_result["output"].get(
                    "accepted_for_evaluation"
                )
                is True
            )
            expected = (
                [
                    EventType.TOOL_CALLED,
                    EventType.REVIEW_RECORDED,
                    EventType.SUBMISSION_ATTEMPTED,
                    EventType.TOOL_SUCCEEDED,
                    EventType.SUBMISSION_ACCEPTED,
                ]
                if accepted
                else [
                    EventType.TOOL_CALLED,
                    EventType.SUBMISSION_ATTEMPTED,
                    EventType.TOOL_FAILED,
                    EventType.SUBMISSION_REJECTED,
                ]
            )
            valid = bool(
                valid
                and isinstance(recovery_result, dict)
                and recovery_result.get("action_id") == call.correlation_id
                and actual == expected
            )
        if not valid:
            failed_sequences.append(call.sequence)
    relevant_correlations = {call.correlation_id for call in calls}
    orphan_sequences = [
        event.sequence
        for event in events
        if event.type
        in {
            EventType.REVIEW_RECORDED,
            EventType.SUBMISSION_ATTEMPTED,
            EventType.SUBMISSION_REJECTED,
            EventType.SUBMISSION_ACCEPTED,
        }
        and event.correlation_id not in relevant_correlations
    ]
    review_call_count = sum(
        call.payload.get("tool") == "review_task" for call in calls
    )
    accepted_finish_count = sum(
        call.payload.get("tool") == "finish_task"
        and isinstance(call.payload.get("recovery_result"), dict)
        and call.payload["recovery_result"].get("status") == "succeeded"
        and isinstance(call.payload["recovery_result"].get("output"), dict)
        and call.payload["recovery_result"]["output"].get(
            "accepted_for_evaluation"
        )
        is True
        for call in calls
    )
    nonvacuous = bool(review_call_count and accepted_finish_count == 1)
    return bool(
        nonvacuous and not failed_sequences and not orphan_sequences
    ), {
        "action_count": len(calls),
        "review_call_count": review_call_count,
        "accepted_finish_count": accepted_finish_count,
        "nonvacuous": nonvacuous,
        "verified_action_count": len(calls) - len(failed_sequences),
        "failed_action_sequences": failed_sequences,
        "orphan_lifecycle_sequences": orphan_sequences,
        "observed_prefix_shapes": prefix_shapes,
    }


def _v10_coverage_terminal_evidence(
    *,
    events: list[Any],
    result: RunResult | None,
) -> tuple[bool, dict[str, Any]]:
    """Ensure incomplete coverage returns to correction and cannot terminate accepted."""

    review_events = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "review_task"
    ]
    incomplete_reviews = [
        event
        for event in review_events
        if event.payload.get("coverage_complete") is False
    ]
    complete_reviews = [
        event
        for event in review_events
        if event.payload.get("coverage_complete") is True
        and event.payload.get("unresolved_coverage_target_ids") == []
    ]
    accepted = [
        event
        for event in events
        if event.type == EventType.SUBMISSION_ACCEPTED
    ]
    failed_incomplete: list[int] = []
    for review in incomplete_reviews:
        next_review_or_terminal = next(
            (
                event.sequence
                for event in events
                if event.sequence > review.sequence
                and (
                    (
                        event.type == EventType.TOOL_SUCCEEDED
                        and event.payload.get("tool") == "review_task"
                    )
                    or event.type in _TERMINAL_EVENTS
                )
            ),
            len(events) + 1,
        )
        corrective_transitions = [
            event
            for event in events
            if review.sequence < event.sequence < next_review_or_terminal
            and event.type == EventType.PHASE_CHANGED
            and event.payload.get("from") == "REVIEW"
            and event.payload.get("to") == "IMPLEMENT"
        ]
        referenced_by_acceptance = any(
            event.payload.get("source_task_review_sequence")
            == review.sequence
            for event in accepted
        )
        if len(corrective_transitions) != 1 or referenced_by_acceptance:
            failed_incomplete.append(review.sequence)
    accepted_review_sequences = {
        event.payload.get("source_task_review_sequence")
        for event in accepted
    }
    accepted_sources_valid = all(
        type(sequence) is int
        and any(
            review.sequence == sequence
            and review.payload.get("coverage_complete") is True
            and review.payload.get("unresolved_coverage_target_ids") == []
            for review in review_events
        )
        for sequence in accepted_review_sequences
    )
    evaluation_completed = bool(
        result is not None and result.evaluation_status == "completed"
    )
    terminal_events = [
        event for event in events if event.type in _TERMINAL_EVENTS
    ]
    rejection_ok, rejection_details = (
        _v9_review_rejection_terminal_contract(events)
    )
    terminal_valid = bool(
        len(terminal_events) == 1
        and evaluation_completed
        and len(accepted) == 1
        and complete_reviews
        and accepted_sources_valid
        and not failed_incomplete
        and rejection_ok
    )
    return terminal_valid, {
        "review_count": len(review_events),
        "incomplete_review_sequences": [
            event.sequence for event in incomplete_reviews
        ],
        "coverage_complete_review_sequences": [
            event.sequence for event in complete_reviews
        ],
        "failed_incomplete_review_sequences": failed_incomplete,
        "accepted_submission_count": len(accepted),
        "accepted_review_sources_valid": accepted_sources_valid,
        "evaluation_completed": evaluation_completed,
        "review_rejection_terminal_valid": rejection_ok,
        "review_rejection_details": rejection_details,
    }


def _v11_correlated_success_call_evidence(
    *,
    artifact_root: Path,
    events: list[Any],
    outcome: Any,
    expected_tool: str,
    worktree_diff_hash: str,
) -> tuple[Any, dict[str, Any]]:
    """Bind one V11 success outcome to its exact dispatched call and input."""

    action_id = outcome.correlation_id
    calls = [
        event
        for event in events
        if event.sequence < outcome.sequence
        and event.type == EventType.TOOL_CALLED
        and event.correlation_id == action_id
        and event.payload.get("tool") == expected_tool
    ]
    outcomes = [
        event
        for event in events
        if event.type in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}
        and event.correlation_id == action_id
        and event.payload.get("tool") == expected_tool
    ]
    if (
        outcome.actor != "tool-gateway"
        or outcome.payload.get("status") != "succeeded"
        or not isinstance(action_id, str)
        or not action_id
        or len(calls) != 1
        or len(outcomes) != 1
        or outcomes[0].event_id != outcome.event_id
    ):
        raise RecoveryError(
            f"v11 {expected_tool} outcome lacks one correlated call"
        )
    call = calls[0]
    input_valid, input_item, input_bytes = _nested_cas_artifact_evidence(
        artifact_root=artifact_root,
        event_id=call.event_id,
        role=f"v11-{expected_tool}-input",
        raw_artifact=call.payload.get("input_artifact"),
    )
    if not input_valid or input_bytes is None:
        raise RecoveryError(f"v11 {expected_tool} input CAS is invalid")
    input_document = json.loads(input_bytes.decode("utf-8"))
    arguments = (
        input_document.get("input")
        if isinstance(input_document, dict)
        else None
    )
    state_marker = None
    if expected_tool == "get_diff":
        state_marker = max(
            (
                event.sequence
                for event in events
                if event.sequence < call.sequence
                and event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool") == "run_check"
                and event.payload.get("worktree_diff_hash")
                == worktree_diff_hash
            ),
            default=None,
        )
    expected_input_hash = (
        sha256_text(
            canonical_json({"tool": expected_tool, "input": arguments})
        )
        if isinstance(arguments, dict)
        else None
    )
    expected_normalized_hash = (
        sha256_text(
            canonical_json(
                {
                    "tool": expected_tool,
                    "input": arguments,
                    "worktree_diff_hash": worktree_diff_hash,
                    "state_marker": state_marker,
                }
            )
        )
        if isinstance(arguments, dict)
        else None
    )
    if (
        call.actor != "agent"
        or not isinstance(input_document, dict)
        or set(input_document) != {"tool", "input"}
        or input_document.get("tool") != expected_tool
        or not isinstance(arguments, dict)
        or call.payload.get("artifact_id") != input_item.get("artifact_id")
        or call.payload.get("artifact_path")
        != input_item.get("declared_path")
        or call.payload.get("input_hash") != expected_input_hash
        or call.payload.get("normalized_call_hash")
        != expected_normalized_hash
        or call.payload.get("worktree_diff_hash") != worktree_diff_hash
        or call.payload.get("execution") != "dispatched"
    ):
        raise RecoveryError(f"v11 {expected_tool} call binding is invalid")
    return call, arguments


def _v11_get_diff_result_evidence(
    *,
    artifact_root: Path,
    artifact_store: ArtifactStore,
    events: list[Any],
    outcome: Any,
    worktree_diff_hash: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind V11 get_diff call, result CAS, and exact patch bytes."""

    _, arguments = _v11_correlated_success_call_evidence(
        artifact_root=artifact_root,
        events=events,
        outcome=outcome,
        expected_tool="get_diff",
        worktree_diff_hash=worktree_diff_hash,
    )
    if arguments != {}:
        raise RecoveryError("v11 get_diff call arguments are invalid")
    rendered, result_evidence = _v10_recompute_review_anchor(
        outcome,
        artifact_store=artifact_store,
    )
    result_document = rendered.get("payload", {}).get("tool_result")
    if (
        outcome.type != EventType.TOOL_SUCCEEDED
        or outcome.payload.get("tool") != "get_diff"
        or outcome.payload.get("patch_hash") != worktree_diff_hash
        or outcome.payload.get("worktree_diff_hash")
        != worktree_diff_hash
        or not isinstance(result_document, dict)
        or set(result_document)
        != {
            "patch",
            "patch_hash",
            "worktree_diff_hash",
            "changed_files",
            "added_lines",
            "deleted_lines",
        }
        or not isinstance(result_document.get("patch"), str)
        or sha256_text(result_document["patch"]) != worktree_diff_hash
        or result_document.get("patch_hash") != worktree_diff_hash
        or result_document.get("worktree_diff_hash")
        != worktree_diff_hash
        or not isinstance(result_document.get("changed_files"), list)
        or any(
            not isinstance(path, str) or not path
            for path in result_document.get("changed_files", [])
        )
        or type(result_document.get("added_lines")) is not int
        or result_document["added_lines"] < 0
        or type(result_document.get("deleted_lines")) is not int
        or result_document["deleted_lines"] < 0
        or result_evidence.get("available") is not True
        or result_evidence.get("truncated") is True
    ):
        raise RecoveryError("v11 get_diff result binding is invalid")
    return result_document, result_evidence


def _v11_latest_worker_claim(
    *,
    worker_claims: list[dict[str, Any]],
    claim_evidence: Any,
    context_timestamp: datetime,
    label: str,
) -> tuple[dict[str, Any], datetime]:
    """Resolve one request claim by durable SQLite row order at build time."""

    if (
        not isinstance(claim_evidence, dict)
        or claim_evidence.get("schema_version")
        != "worker-claim-evidence-v1"
    ):
        raise RecoveryError(f"v11 {label} worker claim evidence is invalid")
    matching_claims = [
        claim
        for claim in worker_claims
        if claim_evidence
        == {
            "schema_version": "worker-claim-evidence-v1",
            **claim,
        }
    ]
    try:
        matching_time = datetime.fromisoformat(
            str(matching_claims[0].get("claimed_at"))
        )
        parsed_claims = [
            (datetime.fromisoformat(str(claim.get("claimed_at"))), claim)
            for claim in worker_claims
        ]
    except (IndexError, TypeError, ValueError) as exc:
        raise RecoveryError(f"v11 {label} worker claim is malformed") from exc
    if any(
        current[0] < previous[0]
        for previous, current in zip(
            parsed_claims,
            parsed_claims[1:],
            strict=False,
        )
    ):
        raise RecoveryError(
            f"v11 {label} worker claims conflict with durable row order"
        )
    prior_claims = [
        claim
        for claimed_at, claim in parsed_claims
        if claimed_at <= context_timestamp
    ]
    if (
        len(matching_claims) != 1
        or matching_time > context_timestamp
        or not prior_claims
        or prior_claims[-1] != matching_claims[0]
    ):
        raise RecoveryError(
            f"v11 {label} worker claim is not the active durable claim"
        )
    return matching_claims[0], matching_time


def _v11_bind_model_request(
    *,
    artifact_root: Path,
    context_event: Any,
    model_event: Any,
    label: str,
    expected_call: Any | None = None,
    expected_tool: str | None = None,
    expected_arguments: dict[str, Any] | None = None,
) -> None:
    """Bind one request and optional tool call to exact model CAS objects."""

    try:
        request_path = Path(
            str(context_event.payload["artifact_path"])
        ).resolve()
        request_path.relative_to(artifact_root.resolve())
        content_hash = sha256_bytes(request_path.read_bytes())
        response_path = Path(
            str(model_event.payload["artifact_path"])
        ).resolve()
        relative = response_path.relative_to(artifact_root.resolve())
        response_bytes = response_path.read_bytes()
        response_document = json.loads(response_bytes.decode("utf-8"))
    except (
        KeyError,
        OSError,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise RecoveryError(
            f"v11 {label} request artifact cannot be rebound"
        ) from exc
    parts = relative.parts
    declared_calls = (
        response_document.get("tool_calls")
        if isinstance(response_document, dict)
        else None
    )
    expected_tool_call = (
        {
            "name": expected_tool,
            "action_id": expected_call.correlation_id,
            "arguments": expected_arguments,
        }
        if expected_call is not None
        and isinstance(expected_tool, str)
        and isinstance(expected_arguments, dict)
        else None
    )
    matching_calls = (
        [item for item in declared_calls if item == expected_tool_call]
        if expected_tool_call is not None
        and isinstance(declared_calls, list)
        else []
    )
    if (
        context_event.type != EventType.CONTEXT_BUILT
        or context_event.actor != "context-builder"
        or model_event.type != EventType.MODEL_CALLED
        or model_event.actor != "model-adapter"
        or context_event.sequence >= model_event.sequence
        or model_event.payload.get("request_artifact_id")
        != context_event.payload.get("artifact_id")
        or model_event.payload.get("request_artifact_path")
        != context_event.payload.get("artifact_path")
        or model_event.payload.get("request_artifact_hash") != content_hash
        or model_event.payload.get("request_body_hash")
        != context_event.payload.get("request_body_hash")
        or len(parts) != 4
        or parts[0:2] != ("objects", "sha256")
        or len(parts[2]) != 2
        or len(parts[3]) != 62
        or sha256_bytes(response_bytes) != f"sha256:{parts[2]}{parts[3]}"
        or not isinstance(model_event.payload.get("artifact_id"), str)
        or not model_event.payload["artifact_id"]
        or model_event.payload.get("artifact_path") != str(response_path)
        or not isinstance(declared_calls, list)
        or any(
            not isinstance(item, dict)
            or set(item) != {"name", "action_id", "arguments"}
            for item in declared_calls
        )
        or (
            expected_call is not None
            and (
                expected_tool_call is None
                or len(matching_calls) != 1
                or not model_event.sequence < expected_call.sequence
            )
        )
    ):
        raise RecoveryError(
            f"v11 {label} context was not consumed by its model request"
        )


def _v11_bind_tool_call_generation(
    *,
    artifact_root: Path,
    events: list[Any],
    context_events: list[Any],
    call: Any,
    expected_tool: str,
    expected_arguments: dict[str, Any],
    label: str,
) -> tuple[Any, Any]:
    """Bind a tool call to the immediately preceding model generation."""

    prior_models = [
        event
        for event in events
        if event.type == EventType.MODEL_CALLED
        and event.sequence < call.sequence
    ]
    if not prior_models:
        raise RecoveryError(f"v11 {label} lacks a source generation")
    model_event = prior_models[-1]
    matching_contexts = [
        event
        for event in context_events
        if event.sequence < model_event.sequence
        and event.payload.get("artifact_id")
        == model_event.payload.get("request_artifact_id")
    ]
    intervening_contexts = [
        event
        for event in context_events
        if matching_contexts
        and matching_contexts[0].sequence
        < event.sequence
        < model_event.sequence
    ]
    if len(matching_contexts) != 1 or intervening_contexts:
        raise RecoveryError(f"v11 {label} request context is ambiguous")
    context_event = matching_contexts[0]
    _v11_bind_model_request(
        artifact_root=artifact_root,
        context_event=context_event,
        model_event=model_event,
        label=label,
        expected_call=call,
        expected_tool=expected_tool,
        expected_arguments=expected_arguments,
    )
    return context_event, model_event


def _v11_validate_rejected_review_arguments(
    *,
    contract: Any,
    arguments: dict[str, Any],
    review_evidence: dict[str, Any],
    execution_context: dict[str, Any],
    events: list[Any],
    artifact_store: ArtifactStore,
    call_sequence: int,
    worktree_diff_hash: str,
    rejected_target_id: str,
    expected_rejection_reason: str,
) -> None:
    """Rebuild the complete V11 source request before trusting its rejection."""

    expected_argument_keys = {
        "requirements",
        "coverage_targets",
        "targeted_validation",
        "residual_risks",
    }
    if (
        set(arguments) != expected_argument_keys
        or len(canonical_json(arguments).encode("utf-8")) > 16_000
    ):
        raise RecoveryError("v11 rejected review argument envelope is invalid")

    requirements = list(contract.requirements)
    requirement_ids = [item.requirement_id for item in requirements]
    requirement_by_id = {
        item.requirement_id: item for item in requirements
    }
    targets = [
        target
        for requirement in requirements
        for target in requirement.coverage_targets
    ]
    target_ids = [target.coverage_target_id for target in targets]
    target_by_id = {target.coverage_target_id: target for target in targets}
    raw_requirements = arguments.get("requirements")
    raw_targets = arguments.get("coverage_targets")
    if (
        not isinstance(raw_requirements, list)
        or len(raw_requirements) != len(requirement_ids)
        or not isinstance(raw_targets, list)
        or len(raw_targets) != len(target_ids)
    ):
        raise RecoveryError("v11 rejected review row cardinality is invalid")

    target_mapping = review_evidence.get(
        "coverage_target_event_sequences"
    )
    citable = review_evidence.get("citable_event_sequences")
    passing = review_evidence.get("passing_check_event_sequences")
    mutation_sequence = review_evidence.get("mutation_event_sequence")
    source_diff_sequence = review_evidence.get("source_get_diff_sequence")
    presented = execution_context.get("presented_tool_results")
    if (
        review_evidence.get("schema_version") != "review-evidence-v2"
        or review_evidence.get("pinning_active") is not True
        or review_evidence.get("worktree_diff_hash") != worktree_diff_hash
        or type(mutation_sequence) is not int
        or type(source_diff_sequence) is not int
        or not mutation_sequence < source_diff_sequence < call_sequence
        or not isinstance(target_mapping, dict)
        or set(target_mapping) != set(target_ids)
        or not isinstance(citable, list)
        or any(type(sequence) is not int for sequence in citable)
        or len(citable) != len(set(citable))
        or not isinstance(passing, list)
        or any(type(sequence) is not int for sequence in passing)
        or len(passing) != len(set(passing))
        or not isinstance(presented, list)
    ):
        raise RecoveryError("v11 rejected review evidence authority is invalid")
    for sequences in target_mapping.values():
        if (
            not isinstance(sequences, list)
            or any(type(sequence) is not int for sequence in sequences)
            or sequences != sorted(set(sequences))
        ):
            raise RecoveryError(
                "v11 rejected review target evidence mapping is invalid"
            )
    expected_citable: list[int] = []
    for target_id in target_ids:
        for sequence in target_mapping[target_id]:
            if sequence not in expected_citable:
                expected_citable.append(sequence)
    for sequence in passing:
        if sequence not in expected_citable:
            expected_citable.append(sequence)
    if source_diff_sequence not in expected_citable:
        expected_citable.append(source_diff_sequence)
    if citable != expected_citable:
        raise RecoveryError(
            "v11 rejected review citable evidence is not canonical"
        )

    complete_presented = {
        item["event_sequence"]
        for item in presented
        if (
            isinstance(item, dict)
            and type(item.get("event_sequence")) is int
            and item.get("available") is True
            and item.get("truncated") is False
        )
    }
    events_by_sequence = {event.sequence: event for event in events}
    for target_id, target in target_by_id.items():
        for sequence in target_mapping[target_id]:
            event = events_by_sequence.get(sequence)
            if (
                sequence <= mutation_sequence
                or sequence >= call_sequence
                or sequence not in complete_presented
                or sequence not in citable
                or event is None
                or event.type != EventType.TOOL_SUCCEEDED
                or event.payload.get("worktree_diff_hash")
                != worktree_diff_hash
            ):
                raise RecoveryError(
                    "v11 rejected review advertises invalid target evidence"
                )
            rendered_anchor, anchor_evidence = _v10_recompute_review_anchor(
                event,
                artifact_store=artifact_store,
            )
            tool_result = rendered_anchor.get("payload", {}).get(
                "tool_result"
            )
            if (
                anchor_evidence.get("available") is not True
                or anchor_evidence.get("truncated") is not False
                or not isinstance(tool_result, dict)
                or tool_result.get("worktree_diff_hash")
                != worktree_diff_hash
                or (
                    target.evidence_kind == "current_diff_inspection"
                    and (
                        event.payload.get("tool") != "read_file"
                        or tool_result.get("path") != target.path
                        or target.anchor
                        not in tool_result.get("content", "")
                    )
                )
                or (
                    target.evidence_kind == "passing_validation"
                    and (
                        event.payload.get("tool") != "run_check"
                        or tool_result.get("check_id")
                        not in target.check_ids
                        or tool_result.get("passed") is not True
                        or tool_result.get("timed_out") is not False
                    )
                )
            ):
                raise RecoveryError(
                    "v11 rejected review target evidence is not public-bound"
                )

    observed_requirement_ids: set[str] = set()
    for row in raw_requirements:
        if not isinstance(row, dict) or set(row) != {
            "requirement_id",
            "status",
            "evidence_event_sequences",
            "notes",
        }:
            raise RecoveryError("v11 rejected requirement row is invalid")
        requirement_id = row.get("requirement_id")
        status = row.get("status")
        sequences = row.get("evidence_event_sequences")
        notes = row.get("notes")
        if (
            requirement_id not in requirement_by_id
            or requirement_id in observed_requirement_ids
            or status
            not in {"verified", "partially_verified", "unverified"}
            or not isinstance(sequences, list)
            or len(sequences) > 20
            or any(
                type(sequence) is not int or sequence < 1
                for sequence in sequences
            )
            or len(sequences) != len(set(sequences))
            or not isinstance(notes, str)
            or not notes.strip()
            or len(notes) > 2_000
            or (status != "unverified" and not sequences)
        ):
            raise RecoveryError("v11 rejected requirement fields are invalid")
        observed_requirement_ids.add(requirement_id)
    if observed_requirement_ids != set(requirement_ids):
        raise RecoveryError(
            "v11 rejected review requirement IDs are invalid"
        )
    active_feedback = execution_context.get("coverage_rejection_feedback")
    if active_feedback is not None and (
        not isinstance(active_feedback, dict)
        or active_feedback.get("schema_version")
        != "coverage-rejection-feedback-v1"
        or active_feedback.get("coverage_target_id") not in target_by_id
        or type(active_feedback.get("source_failure_sequence")) is not int
        or active_feedback.get("source_failure_sequence", 0) < 1
        or active_feedback.get("worktree_diff_hash") != worktree_diff_hash
    ):
        raise RecoveryError("v11 rejected review active feedback is invalid")

    reproduced_target_id: str | None = None
    observed_target_ids: set[str] = set()
    for row in raw_targets:
        if reproduced_target_id is not None:
            break
        if not isinstance(row, dict) or set(row) != {
            "coverage_target_id",
            "status",
            "evidence_event_sequences",
            "notes",
        }:
            raise RecoveryError("v11 rejected coverage target row is invalid")
        target_id = row.get("coverage_target_id")
        status = row.get("status")
        sequences = row.get("evidence_event_sequences")
        notes = row.get("notes")
        if (
            target_id not in target_by_id
            or target_id in observed_target_ids
            or status
            not in {"verified", "partially_verified", "unverified"}
            or not isinstance(sequences, list)
            or len(sequences) > 20
            or any(
                type(sequence) is not int or sequence < 1
                for sequence in sequences
            )
            or len(sequences) != len(set(sequences))
            or not isinstance(notes, str)
            or not notes.strip()
            or len(notes) > 2_000
        ):
            raise RecoveryError(
                "v11 rejected coverage target fields are invalid"
            )
        observed_target_ids.add(target_id)
        advertised = target_mapping[target_id]
        reason: str | None = None
        if not set(sequences).issubset(advertised):
            reason = "target_evidence_not_allowed"
        elif status == "verified" and (
            not advertised or sequences != advertised
        ):
            reason = "verified_target_evidence_mismatch"
        elif (
            isinstance(active_feedback, dict)
            and active_feedback.get("coverage_target_id") == target_id
            and (
                status != "verified"
                or not any(
                    sequence > active_feedback["source_failure_sequence"]
                    for sequence in sequences
                )
            )
        ):
            reason = "fresh_target_evidence_required"
        if reason is not None:
            if (
                target_id != rejected_target_id
                or reason != expected_rejection_reason
                or reproduced_target_id is not None
            ):
                raise RecoveryError(
                    "v11 rejected review has another target citation failure"
                )
            reproduced_target_id = target_id
        elif (
            (status == "partially_verified" and not sequences)
            or (status == "unverified" and sequences)
        ):
            raise RecoveryError(
                "v11 rejected coverage target status is invalid"
            )
    if reproduced_target_id != rejected_target_id:
        raise RecoveryError("v11 source target rejection was not reproduced")


def _v11_coverage_rejection_recovery_evidence(
    *,
    root: Path,
    manifest: RunManifest,
    package: TaskPackage,
    events: list[Any],
    context_events: list[Any],
    worker_claims: list[dict[str, Any]],
) -> tuple[bool, dict[str, Any]]:
    """Bind a V11 target rejection to restart, fresh evidence, and retry."""

    selector_valid = bool(
        manifest.tool_schema_version == "v6"
        and manifest.context_policy_version == "phase-evidence-v11"
        and manifest.model.provider == "mock"
        and manifest.experiment is None
    )
    contract = manifest.public_review_contract
    targets = (
        {
            target.coverage_target_id: (requirement.requirement_id, target)
            for requirement in contract.requirements
            for target in requirement.coverage_targets
        }
        if contract is not None
        and contract.schema_version == "public-review-contract-v2"
        else {}
    )
    artifact_root = (root / "artifacts").resolve()
    artifact_store = ArtifactStore(artifact_root)
    events_by_sequence = {event.sequence: event for event in events}
    rejections = [
        event
        for event in events
        if event.type == EventType.TOOL_FAILED
        and event.payload.get("tool") == "review_task"
        and event.payload.get("error_code")
        == "COVERAGE_CITATION_REJECTED"
    ]
    failed_sequences: list[int] = []
    failure_reasons: list[dict[str, Any]] = []
    verified_rejection_sequences: list[int] = []
    restart_rejection_sequences: list[int] = []
    rehydrated_context_sequences: list[int] = []
    recovery_evidence_sequences: list[int] = []
    refreshed_diff_sequences: list[int] = []
    complete_review_sequences: list[int] = []
    cleared_context_sequences: list[int] = []

    for failure in rejections:
        try:
            action_id = failure.correlation_id
            calls = [
                event
                for event in events
                if event.type == EventType.TOOL_CALLED
                and event.payload.get("tool") == "review_task"
                and event.correlation_id == action_id
                and event.sequence < failure.sequence
            ]
            outcomes = [
                event
                for event in events
                if event.type
                in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}
                and event.payload.get("tool") == "review_task"
                and event.correlation_id == action_id
            ]
            if (
                failure.actor != "tool-gateway"
                or failure.payload.get("status") != "rejected"
                or not isinstance(action_id, str)
                or not action_id
                or len(calls) != 1
                or outcomes != [failure]
            ):
                raise RecoveryError(
                    "v11 rejected review lifecycle is ambiguous"
                )
            call = calls[0]

            input_valid, input_item, input_bytes = (
                _nested_cas_artifact_evidence(
                    artifact_root=artifact_root,
                    event_id=call.event_id,
                    role="v11-rejected-review-input",
                    raw_artifact=call.payload.get("input_artifact"),
                )
            )
            if not input_valid or input_bytes is None:
                raise RecoveryError("v11 rejected review input CAS is invalid")
            input_document = json.loads(input_bytes.decode("utf-8"))
            arguments = (
                input_document.get("input")
                if isinstance(input_document, dict)
                else None
            )
            execution_context = (
                input_document.get("execution_context")
                if isinstance(input_document, dict)
                else None
            )
            expected_input_hash = (
                sha256_text(
                    canonical_json(
                        {"tool": "review_task", "input": arguments}
                    )
                )
                if isinstance(arguments, dict)
                else None
            )
            diff_hash = call.payload.get("worktree_diff_hash")
            expected_normalized_hash = (
                sha256_text(
                    canonical_json(
                        {
                            "tool": "review_task",
                            "input": arguments,
                            "worktree_diff_hash": diff_hash,
                            "state_marker": None,
                        }
                    )
                )
                if isinstance(arguments, dict)
                and isinstance(diff_hash, str)
                else None
            )
            if (
                call.actor != "agent"
                or not isinstance(input_document, dict)
                or set(input_document)
                != {"tool", "input", "execution_context"}
                or input_document.get("tool") != "review_task"
                or not isinstance(arguments, dict)
                or not isinstance(execution_context, dict)
                or set(execution_context)
                != {
                    "request_artifact_id",
                    "phase",
                    "presented_tool_results",
                    "review_evidence",
                    "coverage_rejection_feedback",
                }
                or execution_context.get("phase") != "REVIEW"
                or call.payload.get("artifact_id")
                != input_item.get("artifact_id")
                or call.payload.get("artifact_path")
                != input_item.get("declared_path")
                or call.payload.get("input_hash") != expected_input_hash
                or call.payload.get("normalized_call_hash")
                != expected_normalized_hash
                or call.payload.get("execution") != "dispatched"
                or call.payload.get("request_artifact_id")
                != execution_context.get("request_artifact_id")
                or call.payload.get("request_phase") != "REVIEW"
            ):
                raise RecoveryError(
                    "v11 rejected review input binding is invalid"
                )

            source_contexts = [
                event
                for event in context_events
                if event.sequence < call.sequence
                and event.actor == "context-builder"
                and event.payload.get("artifact_id")
                == execution_context.get("request_artifact_id")
            ]
            if len(source_contexts) != 1:
                raise RecoveryError(
                    "v11 rejected review request context is ambiguous"
                )
            source_context = source_contexts[0]
            request_valid, request_evidence = _request_evidence_payload(
                source_context,
                artifact_root=artifact_root,
                expected_provider=manifest.model.provider,
            )
            context_build = (
                request_evidence.get("context_build")
                if isinstance(request_evidence, dict)
                else None
            )
            source_claim_evidence = (
                request_evidence.get("worker_claim")
                if isinstance(request_evidence, dict)
                else None
            )
            source_rendered_context = _request_context(
                request_evidence.get("request_body")
                if isinstance(request_evidence, dict)
                else None,
                allow_direct_context=True,
            )
            source_rendered_payload = json.loads(
                source_rendered_context or ""
            )
            review_evidence = (
                context_build.get("review_evidence")
                if isinstance(context_build, dict)
                else None
            )
            if (
                not request_valid
                or not isinstance(request_evidence, dict)
                or not _request_runtime_contract_valid(
                    request_evidence.get("request_body"), manifest
                )
                or not isinstance(context_build, dict)
                or context_build.get("schema_version")
                != "context-build-evidence-v11"
                or not isinstance(review_evidence, dict)
                or review_evidence.get("schema_version")
                != "review-evidence-v2"
                or execution_context.get("review_evidence")
                != review_evidence
                or execution_context.get("presented_tool_results")
                != context_build.get("tool_results")
                or not isinstance(source_rendered_payload, dict)
                or source_rendered_payload.get(
                    "coverage_rejection_feedback"
                )
                != execution_context.get(
                    "coverage_rejection_feedback"
                )
                or not isinstance(source_claim_evidence, dict)
                or source_claim_evidence.get("schema_version")
                != "worker-claim-evidence-v1"
                or source_context.payload.get("worker_claim")
                != source_claim_evidence
            ):
                raise RecoveryError(
                    "v11 rejected review source context is invalid"
                )
            source_models = [
                event
                for event in events
                if event.type == EventType.MODEL_CALLED
                and source_context.sequence < event.sequence < call.sequence
            ]
            if len(source_models) != 1:
                raise RecoveryError(
                    "v11 rejected review source generation is ambiguous"
                )
            _v11_bind_model_request(
                artifact_root=artifact_root,
                context_event=source_context,
                model_event=source_models[0],
                label="rejected review source",
                expected_call=call,
                expected_tool="review_task",
                expected_arguments=arguments,
            )
            source_claim, source_claim_time = _v11_latest_worker_claim(
                worker_claims=worker_claims,
                claim_evidence=source_claim_evidence,
                context_timestamp=source_context.timestamp,
                label="rejected review source",
            )

            result_valid, result_item, result_bytes = (
                _nested_cas_artifact_evidence(
                    artifact_root=artifact_root,
                    event_id=failure.event_id,
                    role="v11-coverage-rejection-result",
                    raw_artifact=failure.payload.get("result_artifact"),
                )
            )
            if not result_valid or result_bytes is None:
                raise RecoveryError(
                    "v11 coverage rejection result CAS is invalid"
                )
            result_document = json.loads(result_bytes.decode("utf-8"))
            details = (
                result_document.get("error_details")
                if isinstance(result_document, dict)
                else None
            )
            target_id = (
                details.get("coverage_target_id")
                if isinstance(details, dict)
                else None
            )
            target_binding = targets.get(target_id)
            target_rows = arguments.get("coverage_targets")
            submitted_rows = (
                [
                    row
                    for row in target_rows
                    if isinstance(row, dict)
                    and row.get("coverage_target_id") == target_id
                ]
                if isinstance(target_rows, list)
                else []
            )
            allowed_mapping = review_evidence.get(
                "coverage_target_event_sequences"
            )
            if (
                target_binding is None
                or len(submitted_rows) != 1
                or not isinstance(allowed_mapping, dict)
            ):
                raise RecoveryError(
                    "v11 coverage rejection target is not public-bound"
                )
            requirement_id, target = target_binding
            submitted_row = submitted_rows[0]
            submitted_sequences = submitted_row.get(
                "evidence_event_sequences"
            )
            allowed_sequences = allowed_mapping.get(target_id)
            if (
                not isinstance(submitted_sequences, list)
                or any(type(item) is not int for item in submitted_sequences)
                or not isinstance(allowed_sequences, list)
                or any(type(item) is not int for item in allowed_sequences)
            ):
                raise RecoveryError(
                    "v11 coverage rejection sequences are invalid"
                )
            invalid_sequences = [
                sequence
                for sequence in submitted_sequences
                if sequence not in allowed_sequences
            ]
            active_feedback = execution_context.get(
                "coverage_rejection_feedback"
            )
            if not set(submitted_sequences).issubset(allowed_sequences):
                expected_reason = "target_evidence_not_allowed"
            elif (
                submitted_row.get("status") == "verified"
                and (
                    not allowed_sequences
                    or submitted_sequences != allowed_sequences
                )
            ):
                expected_reason = "verified_target_evidence_mismatch"
            elif (
                isinstance(active_feedback, dict)
                and active_feedback.get("schema_version")
                == "coverage-rejection-feedback-v1"
                and active_feedback.get("coverage_target_id")
                == target_id
                and (
                    submitted_row.get("status") != "verified"
                    or type(
                        active_feedback.get(
                            "source_failure_sequence"
                        )
                    )
                    is not int
                    or not any(
                        sequence
                        > active_feedback[
                            "source_failure_sequence"
                        ]
                        for sequence in submitted_sequences
                    )
                )
            ):
                expected_reason = "fresh_target_evidence_required"
            else:
                raise RecoveryError(
                    "v11 rejection reason cannot be reproduced"
                )
            _v11_validate_rejected_review_arguments(
                contract=contract,
                arguments=arguments,
                review_evidence=review_evidence,
                execution_context=execution_context,
                events=events,
                artifact_store=artifact_store,
                call_sequence=call.sequence,
                worktree_diff_hash=diff_hash,
                rejected_target_id=target_id,
                expected_rejection_reason=expected_reason,
            )
            if target.evidence_kind == "current_diff_inspection":
                required_evidence: dict[str, Any] = {
                    "tool": "read_file",
                    "path": target.path,
                    "anchor": target.anchor,
                }
                guidance = (
                    "Locate the exact public anchor if needed, then use "
                    "read_file to obtain a complete current-diff result "
                    "containing it. Retry with only the refreshed "
                    "target-specific advertised sequences."
                )
            else:
                required_evidence = {
                    "tool": "run_check",
                    "check_ids": list(target.check_ids),
                }
                guidance = (
                    "Run an allowed registered check for this target on the "
                    "current diff, then retry with only the refreshed "
                    "target-specific advertised sequences."
                )
            expected_details = {
                "schema_version": "coverage-citation-error-v1",
                "stage": "review",
                "reason": expected_reason,
                "coverage_target_id": target_id,
                "requirement_id": requirement_id,
                "submitted_event_sequences": submitted_sequences,
                "allowed_event_sequences": allowed_sequences,
                "invalid_event_sequences": invalid_sequences,
                "evidence_kind": target.evidence_kind,
                "required_evidence": required_evidence,
                "mutation_event_sequence": review_evidence.get(
                    "mutation_event_sequence"
                ),
                "worktree_diff_hash": review_evidence.get(
                    "worktree_diff_hash"
                ),
                "source_get_diff_sequence": review_evidence.get(
                    "source_get_diff_sequence"
                ),
                "guidance": guidance,
            }
            expected_message = (
                "review_task coverage target citation was rejected"
            )
            expected_result = {
                "tool": "review_task",
                "status": "rejected",
                "error_code": "COVERAGE_CITATION_REJECTED",
                "error_message": expected_message,
                "error_details": expected_details,
            }
            source_diff = events_by_sequence.get(
                expected_details["source_get_diff_sequence"]
            )
            mutation = events_by_sequence.get(
                expected_details["mutation_event_sequence"]
            )
            if (
                result_document != expected_result
                or failure.payload.get("artifact_id")
                != result_item.get("artifact_id")
                or failure.payload.get("artifact_path")
                != result_item.get("declared_path")
                or failure.payload.get("error_message") != expected_message
                or failure.payload.get("error_details") != expected_details
                or diff_hash != expected_details["worktree_diff_hash"]
                or mutation is None
                or mutation.type != EventType.PATCH_APPLIED
                or mutation.payload.get("worktree_diff_hash") != diff_hash
                or source_diff is None
                or source_diff.type != EventType.TOOL_SUCCEEDED
                or source_diff.payload.get("tool") != "get_diff"
                or not mutation.sequence < source_diff.sequence < call.sequence
            ):
                raise RecoveryError(
                    "v11 coverage rejection result is not independently reproducible"
                )

            from patchloop.agent.context import (
                _coverage_rejection_feedback_v11,
            )

            prior_events = [
                event
                for event in events
                if event.sequence < source_context.sequence
            ]
            (
                expected_active_feedback,
                expected_active_feedback_build,
                _,
            ) = _coverage_rejection_feedback_v11(
                prior_events,
                worktree_diff_hash=diff_hash,
                artifact_store=artifact_store,
                public_review_contract=contract,
            )
            if (
                expected_active_feedback_build.get(
                    "source_through_sequence"
                )
                != source_context.sequence - 1
                or execution_context.get("coverage_rejection_feedback")
                != expected_active_feedback
                or source_rendered_payload.get(
                    "coverage_rejection_feedback"
                )
                != expected_active_feedback
                or context_build.get("coverage_rejection_feedback")
                != expected_active_feedback_build
                or source_context.payload.get(
                    "coverage_rejection_feedback"
                )
                != expected_active_feedback_build
            ):
                raise RecoveryError(
                    "v11 rejected review active feedback is not predecessor-bound"
                )
            _v11_get_diff_result_evidence(
                artifact_root=artifact_root,
                artifact_store=artifact_store,
                events=events,
                outcome=source_diff,
                worktree_diff_hash=diff_hash,
            )
            for sequence in allowed_sequences:
                anchor_event = events_by_sequence.get(sequence)
                if anchor_event is None or anchor_event.sequence >= call.sequence:
                    raise RecoveryError(
                        "v11 rejection advertises unavailable evidence"
                    )
                rendered_anchor, anchor_evidence = (
                    _v10_recompute_review_anchor(
                        anchor_event,
                        artifact_store=artifact_store,
                    )
                )
                tool_result = rendered_anchor.get("payload", {}).get(
                    "tool_result"
                )
                if (
                    anchor_evidence.get("truncated") is True
                    or not isinstance(tool_result, dict)
                    or tool_result.get("worktree_diff_hash") != diff_hash
                    or (
                        target.evidence_kind == "current_diff_inspection"
                        and (
                            anchor_event.payload.get("tool") != "read_file"
                            or tool_result.get("path") != target.path
                            or target.anchor not in tool_result.get("content", "")
                        )
                    )
                    or (
                        target.evidence_kind == "passing_validation"
                        and (
                            anchor_event.payload.get("tool") != "run_check"
                            or tool_result.get("check_id")
                            not in target.check_ids
                            or tool_result.get("passed") is not True
                        )
                    )
                ):
                    raise RecoveryError(
                        "v11 rejection allowed evidence is invalid"
                    )

            next_models = [
                event
                for event in events
                if event.type == EventType.MODEL_CALLED
                and event.sequence > failure.sequence
            ]
            if not next_models:
                raise RecoveryError(
                    "v11 rejection has no post-failure model request"
                )
            next_model = next_models[0]
            later_contexts = [
                event
                for event in context_events
                if failure.sequence < event.sequence < next_model.sequence
            ]
            if len(later_contexts) != 1:
                raise RecoveryError(
                    "v11 rejection rehydrated request context is ambiguous"
                )
            rehydrated = later_contexts[0]
            if failure.event_id == rejections[0].event_id:
                restart_boundary_events = [
                    event
                    for event in events
                    if failure.sequence
                    < event.sequence
                    < rehydrated.sequence
                ]
                if (
                    not restart_boundary_events
                    or any(
                        event.type != EventType.CHECKPOINT_SAVED
                        or event.actor != "state-store"
                        for event in restart_boundary_events
                    )
                ):
                    raise RecoveryError(
                        "v11 designated rejection did not stop at the durable "
                        "restart boundary"
                    )
            _v11_bind_model_request(
                artifact_root=artifact_root,
                context_event=rehydrated,
                model_event=next_model,
                label="rehydrated rejection",
            )
            rehydrated_valid, rehydrated_request = (
                _request_evidence_payload(
                    rehydrated,
                    artifact_root=artifact_root,
                    expected_provider=manifest.model.provider,
                )
            )
            rendered_context = _request_context(
                rehydrated_request.get("request_body")
                if isinstance(rehydrated_request, dict)
                else None,
                allow_direct_context=True,
            )
            rendered_payload = json.loads(rendered_context or "")
            rehydrated_build = (
                rehydrated_request.get("context_build")
                if isinstance(rehydrated_request, dict)
                else None
            )
            feedback_build = (
                rehydrated_build.get("coverage_rejection_feedback")
                if isinstance(rehydrated_build, dict)
                else None
            )
            rehydrated_claim_evidence = (
                rehydrated_request.get("worker_claim")
                if isinstance(rehydrated_request, dict)
                else None
            )
            expected_visible = {
                "schema_version": "coverage-rejection-feedback-v1",
                "source_call_sequence": call.sequence,
                "source_failure_sequence": failure.sequence,
                "action_id": action_id,
                "error_code": "COVERAGE_CITATION_REJECTED",
                **{
                    key: expected_details[key]
                    for key in (
                        "reason",
                        "coverage_target_id",
                        "requirement_id",
                        "submitted_event_sequences",
                        "allowed_event_sequences",
                        "invalid_event_sequences",
                        "evidence_kind",
                        "required_evidence",
                        "mutation_event_sequence",
                        "worktree_diff_hash",
                        "source_get_diff_sequence",
                        "guidance",
                    )
                },
            }
            recent_sequences = {
                item.get("sequence")
                for item in rendered_payload.get("recent_events", [])
                if isinstance(item, dict)
            }
            build_result_artifact = (
                {
                    "artifact_id": result_item.get("artifact_id"),
                    "content_hash": result_item.get(
                        "declared_content_hash"
                    ),
                    "size_bytes": result_item.get("declared_size_bytes"),
                }
            )
            build_input_artifact = {
                "artifact_id": input_item.get("artifact_id"),
                "content_hash": input_item.get("declared_content_hash"),
                "size_bytes": input_item.get("declared_size_bytes"),
            }
            expected_feedback_build = {
                "schema_version": "coverage-rejection-feedback-v1",
                "included": True,
                "source_call_sequence": call.sequence,
                "source_failure_sequence": failure.sequence,
                "action_id": action_id,
                "content_hash": sha256_text(canonical_json(expected_visible)),
                "input_artifact": build_input_artifact,
                "result_artifact": build_result_artifact,
                "source_through_sequence": rehydrated.sequence - 1,
            }
            if (
                not rehydrated_valid
                or rehydrated.actor != "context-builder"
                or not isinstance(rendered_payload, dict)
                or not isinstance(rehydrated_build, dict)
                or rehydrated_build.get("schema_version")
                != "context-build-evidence-v11"
                or rendered_payload.get("coverage_rejection_feedback")
                != expected_visible
                or feedback_build != expected_feedback_build
                or rehydrated.payload.get("coverage_rejection_feedback")
                != expected_feedback_build
                or not isinstance(rehydrated_claim_evidence, dict)
                or rehydrated_claim_evidence.get("schema_version")
                != "worker-claim-evidence-v1"
                or rehydrated.payload.get("worker_claim")
                != rehydrated_claim_evidence
                or failure.sequence in recent_sequences
            ):
                raise RecoveryError(
                    "v11 coverage rejection feedback rehydration is invalid"
                )

            rehydrated_claim, rehydrated_claim_time = (
                _v11_latest_worker_claim(
                    worker_claims=worker_claims,
                    claim_evidence=rehydrated_claim_evidence,
                    context_timestamp=rehydrated.timestamp,
                    label="rehydrated rejection",
                )
            )
            same_claim = bool(
                rehydrated_claim.get("claim_id")
                == source_claim.get("claim_id")
                and rehydrated_claim.get("owner_id")
                == source_claim.get("owner_id")
            )
            if same_claim:
                if (
                    rehydrated_claim != source_claim
                    or rehydrated_claim_time != source_claim_time
                    or not failure.timestamp < rehydrated.timestamp
                ):
                    raise RecoveryError(
                        "v11 rejection continuing worker claim is invalid"
                    )
            else:
                if (
                    rehydrated_claim.get("prior_status")
                    != RunStatus.RUNNING.value
                    or rehydrated_claim.get("reclaimed") is not True
                    or rehydrated_claim.get("claim_id")
                    == source_claim.get("claim_id")
                    or rehydrated_claim.get("owner_id")
                    == source_claim.get("owner_id")
                    or not failure.timestamp
                    < rehydrated_claim_time
                    <= rehydrated.timestamp
                ):
                    raise RecoveryError(
                        "v11 rejection post-failure worker claim is invalid"
                    )
                restart_rejection_sequences.append(failure.sequence)

            later_mutations = [
                event
                for event in events
                if event.type == EventType.PATCH_APPLIED
                and event.sequence > failure.sequence
            ]
            if later_mutations:
                raise RecoveryError(
                    "v11 rejection recovery crossed a mutation boundary"
                )
            recovery_candidates = []
            recovery_tool = (
                "read_file"
                if target.evidence_kind == "current_diff_inspection"
                else "run_check"
            )
            for event in events:
                if (
                    event.sequence <= next_model.sequence
                    or event.type != EventType.TOOL_SUCCEEDED
                    or event.payload.get("tool") != recovery_tool
                    or event.payload.get("worktree_diff_hash") != diff_hash
                ):
                    continue
                _, recovery_arguments = (
                    _v11_correlated_success_call_evidence(
                        artifact_root=artifact_root,
                        events=events,
                        outcome=event,
                        expected_tool=recovery_tool,
                        worktree_diff_hash=diff_hash,
                    )
                )
                rendered_anchor, anchor_evidence = (
                    _v10_recompute_review_anchor(
                        event,
                        artifact_store=artifact_store,
                    )
                )
                tool_result = rendered_anchor.get("payload", {}).get(
                    "tool_result"
                )
                if not isinstance(tool_result, dict) or anchor_evidence.get(
                    "truncated"
                ) is True:
                    continue
                if target.evidence_kind == "current_diff_inspection":
                    matches = bool(
                        event.payload.get("tool") == "read_file"
                        and recovery_arguments.get("path") == target.path
                        and tool_result.get("path") == target.path
                        and target.anchor in tool_result.get("content", "")
                    )
                else:
                    matches = bool(
                        event.payload.get("tool") == "run_check"
                        and recovery_arguments.get("check_id")
                        == tool_result.get("check_id")
                        and tool_result.get("check_id") in target.check_ids
                        and tool_result.get("passed") is True
                    )
                if matches:
                    recovery_candidates.append(event)
            if not recovery_candidates:
                raise RecoveryError(
                    "v11 rejection lacks fresh exact target evidence"
                )
            successful_reviews = [
                event
                for event in events
                if event.sequence > rehydrated.sequence
                and event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool") == "review_task"
                and event.payload.get("coverage_complete") is True
                and event.payload.get("unresolved_coverage_target_ids") == []
            ]
            if not successful_reviews:
                raise RecoveryError(
                    "v11 rejection lacks a complete retry review"
                )
            complete_review = successful_reviews[0]
            clearing_review_valid, clearing_review_details = (
                _v10_coverage_decision_evidence(
                    root=root,
                    manifest=manifest,
                    package=package,
                    events=events,
                    context_events=context_events,
                )
            )
            if (
                not clearing_review_valid
                or complete_review.sequence
                not in clearing_review_details.get(
                    "verified_review_sequences",
                    [],
                )
                or complete_review.sequence
                not in clearing_review_details.get(
                    "coverage_complete_review_sequences",
                    [],
                )
            ):
                raise RecoveryError(
                    "v11 clearing review failed independent reconstruction"
                )

            clearing_calls = [
                event
                for event in events
                if event.type == EventType.TOOL_CALLED
                and event.payload.get("tool") == "review_task"
                and event.correlation_id == complete_review.correlation_id
                and event.sequence < complete_review.sequence
            ]
            if len(clearing_calls) != 1:
                raise RecoveryError(
                    "v11 clearing review call is ambiguous"
                )
            clearing_call = clearing_calls[0]
            (
                clearing_input_valid,
                clearing_input_item,
                clearing_input_bytes,
            ) = _nested_cas_artifact_evidence(
                artifact_root=artifact_root,
                event_id=clearing_call.event_id,
                role="v11-clearing-review-input",
                raw_artifact=clearing_call.payload.get("input_artifact"),
            )
            clearing_input_document = (
                json.loads(clearing_input_bytes.decode("utf-8"))
                if clearing_input_bytes is not None
                else None
            )
            clearing_execution_context = (
                clearing_input_document.get("execution_context")
                if isinstance(clearing_input_document, dict)
                else None
            )
            clearing_request_id = (
                clearing_execution_context.get("request_artifact_id")
                if isinstance(clearing_execution_context, dict)
                else None
            )
            clearing_contexts = [
                event
                for event in context_events
                if event.actor == "context-builder"
                and event.sequence < clearing_call.sequence
                and event.payload.get("artifact_id") == clearing_request_id
            ]
            if len(clearing_contexts) != 1:
                raise RecoveryError(
                    "v11 clearing review request context is ambiguous"
                )
            clearing_context = clearing_contexts[0]
            clearing_request_valid, clearing_request = (
                _request_evidence_payload(
                    clearing_context,
                    artifact_root=artifact_root,
                    expected_provider=manifest.model.provider,
                )
            )
            clearing_rendered = _request_context(
                clearing_request.get("request_body")
                if isinstance(clearing_request, dict)
                else None,
                allow_direct_context=True,
            )
            clearing_rendered_payload = json.loads(clearing_rendered or "")
            clearing_build = (
                clearing_request.get("context_build")
                if isinstance(clearing_request, dict)
                else None
            )
            clearing_models = [
                event
                for event in events
                if event.type == EventType.MODEL_CALLED
                and clearing_context.sequence
                < event.sequence
                < clearing_call.sequence
            ]
            if len(clearing_models) != 1:
                raise RecoveryError(
                    "v11 clearing review generation is ambiguous"
                )
            _v11_bind_model_request(
                artifact_root=artifact_root,
                context_event=clearing_context,
                model_event=clearing_models[0],
                label="clearing review",
                expected_call=clearing_call,
                expected_tool="review_task",
                expected_arguments=(
                    clearing_input_document.get("input")
                    if isinstance(clearing_input_document, dict)
                    else None
                ),
            )
            clearing_prefix = [
                event
                for event in events
                if event.sequence < clearing_context.sequence
            ]
            (
                expected_clearing_feedback,
                expected_clearing_feedback_build,
                _,
            ) = _coverage_rejection_feedback_v11(
                clearing_prefix,
                worktree_diff_hash=diff_hash,
                artifact_store=artifact_store,
                public_review_contract=contract,
            )
            if (
                not clearing_input_valid
                or not isinstance(clearing_input_document, dict)
                or set(clearing_input_document)
                != {"tool", "input", "execution_context"}
                or clearing_input_document.get("tool") != "review_task"
                or not isinstance(clearing_execution_context, dict)
                or clearing_call.payload.get("artifact_id")
                != clearing_input_item.get("artifact_id")
                or clearing_call.payload.get("artifact_path")
                != clearing_input_item.get("declared_path")
                or clearing_call.payload.get("request_artifact_id")
                != clearing_request_id
                or not clearing_request_valid
                or not isinstance(clearing_rendered_payload, dict)
                or not isinstance(clearing_build, dict)
                or expected_clearing_feedback is None
                or expected_clearing_feedback_build.get(
                    "source_through_sequence"
                )
                != clearing_context.sequence - 1
                or clearing_execution_context.get(
                    "coverage_rejection_feedback"
                )
                != expected_clearing_feedback
                or clearing_rendered_payload.get(
                    "coverage_rejection_feedback"
                )
                != expected_clearing_feedback
                or clearing_build.get("coverage_rejection_feedback")
                != expected_clearing_feedback_build
                or clearing_context.payload.get(
                    "coverage_rejection_feedback"
                )
                != expected_clearing_feedback_build
            ):
                raise RecoveryError(
                    "v11 clearing review did not consume exact active feedback"
                )
            review_valid, _, review_bytes = _nested_cas_artifact_evidence(
                artifact_root=artifact_root,
                event_id=complete_review.event_id,
                role="v11-recovery-task-review",
                raw_artifact=complete_review.payload.get("review_artifact"),
            )
            review_document = (
                json.loads(review_bytes.decode("utf-8"))
                if review_bytes is not None
                else None
            )
            recovery_diff_sequence = (
                review_document.get("source_get_diff_sequence")
                if isinstance(review_document, dict)
                else None
            )
            recovery_diff = events_by_sequence.get(recovery_diff_sequence)
            recovery_diff_evidence: dict[str, Any] | None = None
            recovery_diff_result: dict[str, Any] | None = None
            if recovery_diff is not None:
                recovery_diff_result, recovery_diff_evidence = (
                    _v11_get_diff_result_evidence(
                        artifact_root=artifact_root,
                        artifact_store=artifact_store,
                        events=events,
                        outcome=recovery_diff,
                        worktree_diff_hash=diff_hash,
                    )
                )
            recovered_rows = (
                [
                    row
                    for row in review_document.get("coverage_targets", [])
                    if isinstance(row, dict)
                    and row.get("coverage_target_id") == target_id
                ]
                if isinstance(review_document, dict)
                else []
            )
            fresh_recovery_sequences = (
                [
                    sequence
                    for sequence in recovered_rows[0].get(
                        "evidence_event_sequences",
                        [],
                    )
                    if type(sequence) is int
                    and sequence > failure.sequence
                ]
                if len(recovered_rows) == 1
                else []
            )
            recovery_candidates_by_sequence = {
                event.sequence: event
                for event in recovery_candidates
                if event.sequence < complete_review.sequence
            }
            if (
                not fresh_recovery_sequences
                or any(
                    sequence not in recovery_candidates_by_sequence
                    for sequence in fresh_recovery_sequences
                )
            ):
                raise RecoveryError(
                    "v11 complete retry does not resolve every fresh target "
                    "evidence event"
                )
            cited_recovery_candidates = [
                recovery_candidates_by_sequence[sequence]
                for sequence in fresh_recovery_sequences
            ]
            recovery_bindings: list[
                tuple[Any, Any, Any, Any]
            ] = []
            for recovery in cited_recovery_candidates:
                recovery_call, recovery_arguments = (
                    _v11_correlated_success_call_evidence(
                        artifact_root=artifact_root,
                        events=events,
                        outcome=recovery,
                        expected_tool=recovery_tool,
                        worktree_diff_hash=diff_hash,
                    )
                )
                (
                    recovery_request_context,
                    recovery_request_model,
                ) = _v11_bind_tool_call_generation(
                    artifact_root=artifact_root,
                    events=events,
                    context_events=context_events,
                    call=recovery_call,
                    expected_tool=recovery_tool,
                    expected_arguments=recovery_arguments,
                    label="fresh target recovery",
                )
                recovery_bindings.append(
                    (
                        recovery_request_context,
                        recovery_request_model,
                        recovery_call,
                        recovery,
                    )
                )
            recovery_diff_call, recovery_diff_arguments = (
                _v11_correlated_success_call_evidence(
                    artifact_root=artifact_root,
                    events=events,
                    outcome=recovery_diff,
                    expected_tool="get_diff",
                    worktree_diff_hash=diff_hash,
                )
                if recovery_diff is not None
                else (None, None)
            )
            if (
                recovery_diff_call is None
                or not isinstance(recovery_diff_arguments, dict)
            ):
                raise RecoveryError(
                    "v11 refreshed diff lacks its dispatched call"
                )
            (
                recovery_diff_context,
                recovery_diff_model,
            ) = _v11_bind_tool_call_generation(
                artifact_root=artifact_root,
                events=events,
                context_events=context_events,
                call=recovery_diff_call,
                expected_tool="get_diff",
                expected_arguments=recovery_diff_arguments,
                label="refreshed diff",
            )
            recovery_outcome_sequences = [
                binding[3].sequence for binding in recovery_bindings
            ]
            causal_valid = bool(
                failure.sequence < rehydrated.sequence
                and recovery_bindings
                and recovery_outcome_sequences
                == sorted(set(recovery_outcome_sequences))
                and all(
                    rehydrated.sequence
                    <= recovery_request_context.sequence
                    < recovery_request_model.sequence
                    < recovery_call.sequence
                    < recovery.sequence
                    < recovery_diff_context.sequence
                    for (
                        recovery_request_context,
                        recovery_request_model,
                        recovery_call,
                        recovery,
                    ) in recovery_bindings
                )
                and recovery_outcome_sequences[-1]
                < recovery_diff_context.sequence
                < recovery_diff_model.sequence
                < recovery_diff_call.sequence
                < recovery_diff.sequence
                < clearing_context.sequence
                < clearing_models[0].sequence
                < clearing_call.sequence
                < complete_review.sequence
            )
            if not causal_valid:
                raise RecoveryError(
                    "v11 recovery evidence causal order is invalid"
                )
            feedback_contexts = [
                (binding[0], "fresh target recovery")
                for binding in recovery_bindings
            ]
            feedback_contexts.append(
                (recovery_diff_context, "refreshed diff")
            )
            for feedback_context, feedback_label in feedback_contexts:
                feedback_valid, feedback_request = (
                    _request_evidence_payload(
                        feedback_context,
                        artifact_root=artifact_root,
                        expected_provider=manifest.model.provider,
                    )
                )
                feedback_rendered = _request_context(
                    feedback_request.get("request_body")
                    if isinstance(feedback_request, dict)
                    else None,
                    allow_direct_context=True,
                )
                feedback_rendered_payload = json.loads(
                    feedback_rendered or ""
                )
                feedback_context_build = (
                    feedback_request.get("context_build")
                    if isinstance(feedback_request, dict)
                    else None
                )
                feedback_claim = (
                    feedback_request.get("worker_claim")
                    if isinstance(feedback_request, dict)
                    else None
                )
                feedback_prefix = [
                    event
                    for event in events
                    if event.sequence < feedback_context.sequence
                ]
                (
                    expected_persistent_feedback,
                    expected_persistent_build,
                    _,
                ) = _coverage_rejection_feedback_v11(
                    feedback_prefix,
                    worktree_diff_hash=diff_hash,
                    artifact_store=artifact_store,
                    public_review_contract=contract,
                )
                _v11_latest_worker_claim(
                    worker_claims=worker_claims,
                    claim_evidence=feedback_claim,
                    context_timestamp=feedback_context.timestamp,
                    label=feedback_label,
                )
                if (
                    not feedback_valid
                    or expected_persistent_feedback is None
                    or expected_persistent_build.get(
                        "source_through_sequence"
                    )
                    != feedback_context.sequence - 1
                    or feedback_rendered_payload.get(
                        "coverage_rejection_feedback"
                    )
                    != expected_persistent_feedback
                    or not isinstance(feedback_context_build, dict)
                    or feedback_context_build.get(
                        "coverage_rejection_feedback"
                    )
                    != expected_persistent_build
                    or feedback_context.payload.get(
                        "coverage_rejection_feedback"
                    )
                    != expected_persistent_build
                    or feedback_context.payload.get("worker_claim")
                    != feedback_claim
                ):
                    raise RecoveryError(
                        f"v11 {feedback_label} lost active rejection feedback"
                    )
            if (
                not review_valid
                or recovery_diff is None
                or recovery_diff.type != EventType.TOOL_SUCCEEDED
                or recovery_diff.actor != "tool-gateway"
                or recovery_diff.payload.get("tool") != "get_diff"
                or recovery_diff.payload.get("status") != "succeeded"
                or recovery_diff.payload.get("worktree_diff_hash")
                != diff_hash
                or recovery_diff.payload.get("patch_hash") != diff_hash
                or not isinstance(recovery_diff_result, dict)
                or not isinstance(recovery_diff_evidence, dict)
                or recovery_diff_evidence.get("available") is not True
                or recovery_diff_evidence.get("truncated") is True
                or not all(
                    recovery.sequence < recovery_diff.sequence
                    for recovery in cited_recovery_candidates
                )
                or not recovery_diff.sequence < complete_review.sequence
                or complete_review.payload.get("source_get_diff_sequence")
                != recovery_diff.sequence
                or len(recovered_rows) != 1
                or recovered_rows[0].get("status") != "verified"
                or any(
                    recovery.sequence
                    not in recovered_rows[0].get(
                        "evidence_event_sequences",
                        [],
                    )
                    for recovery in cited_recovery_candidates
                )
                or review_document.get("worktree_diff_hash") != diff_hash
            ):
                raise RecoveryError(
                    "v11 complete retry does not cite fresh target evidence"
                )

            clear_models = [
                event
                for event in events
                if event.type == EventType.MODEL_CALLED
                and event.sequence > complete_review.sequence
            ]
            if not clear_models:
                raise RecoveryError(
                    "v11 successful review has no cleared model request"
                )
            clear_model = clear_models[0]
            clear_contexts = [
                event
                for event in context_events
                if complete_review.sequence
                < event.sequence
                < clear_model.sequence
            ]
            if len(clear_contexts) != 1:
                raise RecoveryError(
                    "v11 successful review cleared request is ambiguous"
                )
            clear_context = clear_contexts[0]
            _v11_bind_model_request(
                artifact_root=artifact_root,
                context_event=clear_context,
                model_event=clear_model,
                label="cleared feedback",
            )
            clear_valid, clear_request = _request_evidence_payload(
                clear_context,
                artifact_root=artifact_root,
                expected_provider=manifest.model.provider,
            )
            clear_rendered = _request_context(
                clear_request.get("request_body")
                if isinstance(clear_request, dict)
                else None,
                allow_direct_context=True,
            )
            clear_payload = json.loads(clear_rendered or "")
            clear_build = (
                clear_request.get("context_build")
                if isinstance(clear_request, dict)
                else None
            )
            clear_feedback = (
                clear_build.get("coverage_rejection_feedback")
                if isinstance(clear_build, dict)
                else None
            )
            clear_claim_evidence = (
                clear_request.get("worker_claim")
                if isinstance(clear_request, dict)
                else None
            )
            _v11_latest_worker_claim(
                worker_claims=worker_claims,
                claim_evidence=clear_claim_evidence,
                context_timestamp=clear_context.timestamp,
                label="cleared context",
            )
            expected_clear_feedback = {
                "schema_version": "coverage-rejection-feedback-v1",
                "included": False,
                "source_through_sequence": clear_context.sequence - 1,
            }
            if (
                not clear_valid
                or clear_context.actor != "context-builder"
                or clear_payload.get("coverage_rejection_feedback") is not None
                or clear_feedback != expected_clear_feedback
                or clear_context.payload.get("coverage_rejection_feedback")
                != expected_clear_feedback
                or clear_context.payload.get("worker_claim")
                != clear_claim_evidence
            ):
                raise RecoveryError(
                    "v11 rejection feedback did not clear after review"
                )

            verified_rejection_sequences.append(failure.sequence)
            rehydrated_context_sequences.append(rehydrated.sequence)
            recovery_evidence_sequences.extend(
                recovery.sequence
                for recovery in cited_recovery_candidates
            )
            refreshed_diff_sequences.append(recovery_diff.sequence)
            complete_review_sequences.append(complete_review.sequence)
            cleared_context_sequences.append(clear_context.sequence)
        except (
            KeyError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            RecoveryError,
        ) as exc:
            failed_sequences.append(failure.sequence)
            failure_reasons.append(
                {"sequence": failure.sequence, "reason": str(exc)}
            )

    mutation_sequences = [
        event.sequence
        for event in events
        if event.type == EventType.PATCH_APPLIED
    ]
    nonvacuous = bool(rejections)
    designated_restart_rejection_sequence = (
        rejections[0].sequence if rejections else None
    )
    passed = bool(
        selector_valid
        and targets
        and nonvacuous
        and len(verified_rejection_sequences) == len(rejections)
        and not failed_sequences
        and designated_restart_rejection_sequence
        in restart_rejection_sequences
        and len(mutation_sequences) == 1
    )
    return passed, {
        "selector_valid": selector_valid,
        "public_target_count": len(targets),
        "rejection_count": len(rejections),
        "nonvacuous": nonvacuous,
        "verified_rejection_sequences": verified_rejection_sequences,
        "restart_rejection_sequences": restart_rejection_sequences,
        "restart_observed": bool(restart_rejection_sequences),
        "designated_restart_rejection_sequence": (
            designated_restart_rejection_sequence
        ),
        "rehydrated_context_sequences": rehydrated_context_sequences,
        "recovery_evidence_sequences": recovery_evidence_sequences,
        "refreshed_diff_sequences": refreshed_diff_sequences,
        "complete_review_sequences": complete_review_sequences,
        "cleared_context_sequences": cleared_context_sequences,
        "patch_applied_sequences": mutation_sequences,
        "worker_claim_count": len(worker_claims),
        "running_reclaim_count": sum(
            claim.get("reclaimed") is True for claim in worker_claims
        ),
        "failed_rejection_sequences": failed_sequences,
        "failure_reasons": failure_reasons,
    }


def _v4_no_progress_streak(events: list[Any]) -> int:
    from patchloop.agent.investigation import (
        INVESTIGATION_LOOP_SCHEMA,
        mutation_epoch,
    )

    epoch = mutation_epoch(events)
    streak = 0
    for event in events:
        if epoch is not None and event.sequence <= epoch:
            continue
        if (
            event.type == EventType.LOOP_DETECTED
            and event.payload.get("schema_version")
            == INVESTIGATION_LOOP_SCHEMA
        ):
            streak += 1
        elif (
            event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool")
            in {"read_file", "search_files"}
        ):
            novelty = event.payload.get("novelty")
            if (
                isinstance(novelty, dict)
                and novelty.get("classification") == "seen_only"
            ):
                streak += 1
            else:
                streak = 0
        elif (
            event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool")
            not in {"read_file", "search_files"}
        ):
            streak = 0
    return streak


def _v5_expected_tail_policy(
    *,
    task,
    events: list[Any],
    manifest: RunManifest,
    projection_stage: str,
) -> dict[str, Any]:
    """Independently reconstruct the immutable v5 token-tail contract."""

    if projection_stage not in {"pre_generation", "post_generation"}:
        raise RecoveryError("invalid v5 token-tail projection stage")
    context_policy_version = manifest.context_policy_version
    if context_policy_version == "phase-evidence-v5":
        corrective_tool_calls = 0
        corrective_model_calls = 3
    elif context_policy_version in {
        "phase-evidence-v6",
        "phase-evidence-v7",
        "phase-evidence-v8",
        "phase-evidence-v9",
        "phase-evidence-v10",
        "phase-evidence-v11",
    }:
        corrective_tool_calls = 1
        corrective_model_calls = 4
    else:
        raise RecoveryError(
            "invalid v5 token-tail context policy version"
        )
    reserve = {
        "tool_calls": (
            4
            + 2 * len(task.visible_checks)
            + corrective_tool_calls
        ),
        "model_calls": corrective_model_calls,
        "feedback_model_calls": 1,
    }
    model_calls_used = 0
    tool_calls_used = 0
    observations: list[dict[str, Any]] = []
    total_tokens_used = 0
    for event in events:
        if event.type == EventType.TOOL_CALLED:
            tool_calls_used += 1
        if event.type != EventType.MODEL_CALLED:
            continue
        model_calls_used += 1
        requested = event.payload.get("requested_input_tokens")
        actual_input = event.payload.get("input_tokens")
        actual_output = event.payload.get("output_tokens")
        if type(actual_input) is not int or actual_input < 0:
            raise RecoveryError(
                "v5 token tail source has invalid input token usage"
            )
        if type(actual_output) is not int or actual_output < 0:
            raise RecoveryError(
                "v5 token tail source has invalid output token usage"
            )
        total_tokens_used += actual_input + actual_output
        if type(requested) is int and requested >= 0:
            input_tokens = requested
            source = "requested_input_tokens"
        elif requested is None:
            input_tokens = actual_input
            source = "input_tokens_fallback"
        else:
            raise RecoveryError(
                "v5 token tail source has invalid requested input tokens"
            )
        observations.append(
            {
                "event_sequence": event.sequence,
                "input_tokens": input_tokens,
                "source": source,
            }
        )

    observed_values = [item["input_tokens"] for item in observations]
    max_observed = max(observed_values, default=None)
    max_positive_growth = max(
        [0]
        + [
            current - previous
            for previous, current in zip(
                observed_values,
                observed_values[1:],
                strict=False,
            )
            if current > previous
        ]
    )
    projected_next_input = (
        max_observed + max_positive_growth
        if max_observed is not None
        else None
    )
    projected_model_turns = (
        reserve["model_calls"]
        + reserve["feedback_model_calls"]
        + (1 if projection_stage == "pre_generation" else 0)
    )
    reserved_tokens = (
        manifest.model.max_output_tokens
        + projected_next_input * projected_model_turns
        if projected_next_input is not None
        else manifest.model.max_output_tokens
    )
    remaining_tokens = (
        manifest.budget.max_total_tokens - total_tokens_used
    )
    token_blocked = bool(
        max_observed is not None
        and max_observed > 0
        and remaining_tokens <= reserved_tokens
    )
    remaining_model_calls = (
        manifest.budget.max_model_calls - model_calls_used
    )
    remaining_tool_calls = (
        manifest.budget.max_tool_calls - tool_calls_used
    )
    remaining_after_next = (
        max(0, remaining_model_calls - 1)
        if projection_stage == "pre_generation"
        else remaining_model_calls
    )
    reasons = []
    if remaining_tool_calls <= reserve["tool_calls"]:
        reasons.append("tool_tail_reserved")
    if remaining_after_next <= (
        reserve["model_calls"] + reserve["feedback_model_calls"]
    ):
        reasons.append("model_tail_reserved")
    if token_blocked:
        reasons.append("token_tail_reserved")

    token_projection = {
        "projection_stage": projection_stage,
        "observations": observations,
        "observed_model_call_count": len(observations),
        "max_observed_input_tokens": max_observed,
        "max_positive_consecutive_growth": max_positive_growth,
        "projected_next_input_tokens": projected_next_input,
        "projected_model_turns": projected_model_turns,
        "max_output_tokens": manifest.model.max_output_tokens,
        "reserved_tokens": reserved_tokens,
        "total_tokens_used": total_tokens_used,
        "max_total_tokens": manifest.budget.max_total_tokens,
        "remaining_tokens": remaining_tokens,
        "admission_threshold_reached": token_blocked,
    }
    return {
        "schema_version": "investigation-tail-policy-v2",
        "policy_version": "investigation-policy-v2",
        "projection_stage": projection_stage,
        "nominal_reserve": reserve,
        "remaining_budget": {
            "tool_calls": remaining_tool_calls,
            "model_calls": remaining_model_calls,
            "model_calls_after_next_generation": remaining_after_next,
            "tokens": remaining_tokens,
        },
        "token_projection": token_projection,
        "exploration_admitted": not reasons,
        "block_reasons": reasons,
    }


def _v8_expected_read_search_policy(
    *,
    events: list[Any],
    tail_policy: dict[str, Any],
) -> dict[str, Any]:
    """Independently derive the v8 model-visible inspection policy.

    This deliberately does not import the runtime saturation helper or its
    threshold. The semantic replay lifecycle is qualified separately; this
    projection mirrors the gateway's durable-event counting rule so a context
    cannot advertise an action that the same prefix would reject.
    """

    mutation_epoch_sequence = max(
        (
            event.sequence
            for event in events
            if event.type == EventType.PATCH_APPLIED
        ),
        default=None,
    )
    semantic_replay_count = sum(
        event.type == EventType.TOOL_REPLAYED
        and event.payload.get("semantic_replay") is True
        and (
            mutation_epoch_sequence is None
            or event.sequence > mutation_epoch_sequence
        )
        for event in events
    )
    raw_tail_reasons = tail_policy.get("block_reasons")
    if not isinstance(raw_tail_reasons, list) or not all(
        isinstance(reason, str) for reason in raw_tail_reasons
    ):
        raise RecoveryError("v8 token-tail reasons are invalid")
    reason_codes = list(raw_tail_reasons)
    if semantic_replay_count >= _V8_EVIDENCE_SATURATION_THRESHOLD:
        reason_codes.append("evidence_saturated")
    return {
        "schema_version": "read-search-policy-v1",
        "policy_version": "evidence-saturation-v1",
        "admitted": not reason_codes,
        "reason_codes": reason_codes,
        "semantic_replay_count": semantic_replay_count,
        "semantic_replay_threshold": (
            _V8_EVIDENCE_SATURATION_THRESHOLD
        ),
        "mutation_epoch_sequence": mutation_epoch_sequence,
    }


def _v8_expected_phase_contract(
    *,
    task,
    events: list[Any],
    checkpoint: Checkpoint | None,
    presented_tool_results: Any,
    read_search_policy: dict[str, Any],
    coverage_review_required: bool = False,
) -> dict[str, Any]:
    """Independently derive the v8 readiness fields and allowed actions."""

    if not isinstance(presented_tool_results, list) or not all(
        isinstance(item, dict) for item in presented_tool_results
    ):
        raise RecoveryError("v8 presented tool-result evidence is invalid")
    presented_sequences = {
        item["event_sequence"]
        for item in presented_tool_results
        if (
            type(item.get("event_sequence")) is int
            and item.get("available") is True
            and item.get("truncated") is False
        )
    }
    source_by_sequence = {event.sequence: event for event in events}
    for item in presented_tool_results:
        sequence = item.get("event_sequence")
        if type(sequence) is not int:
            raise RecoveryError("v8 presented event sequence is invalid")
        source = source_by_sequence.get(sequence)
        if (
            source is None
            or source.type
            not in {
                EventType.TOOL_SUCCEEDED,
                EventType.TOOL_FAILED,
                EventType.TOOL_REPLAYED,
            }
            or item.get("tool") != source.payload.get("tool")
            or item.get("worktree_diff_hash")
            != source.payload.get("worktree_diff_hash")
            or item.get("artifact_id") != source.payload.get("artifact_id")
        ):
            raise RecoveryError(
                "v8 presented tool result is not durable-prefix bound"
            )

    phase = checkpoint.phase if checkpoint is not None else Phase.INTAKE
    worktree_diff_hash = (
        checkpoint.worktree_diff_hash
        if checkpoint is not None
        else _EMPTY_DIFF_HASH
    )
    latest_mutation = next(
        (
            event
            for event in reversed(events)
            if event.type == EventType.PATCH_APPLIED
        ),
        None,
    )
    mutation_epoch = latest_mutation.sequence if latest_mutation else 0
    mutation_present = bool(
        latest_mutation is not None
        and worktree_diff_hash != _EMPTY_DIFF_HASH
        and latest_mutation.payload.get("worktree_diff_hash")
        == worktree_diff_hash
    )
    required_checks = tuple(check.id for check in task.visible_checks)
    latest_checks: dict[str, Any] = {}
    review_candidates: list[Any] = []
    task_review_candidates: list[Any] = []
    for event in events:
        if (
            event.sequence <= mutation_epoch
            or event.type != EventType.TOOL_SUCCEEDED
            or event.payload.get("worktree_diff_hash")
            != worktree_diff_hash
        ):
            continue
        tool = event.payload.get("tool")
        if (
            tool == "run_check"
            and event.payload.get("check_id") in required_checks
        ):
            latest_checks[str(event.payload["check_id"])] = event
        elif tool == "get_diff":
            review_candidates.append(event)
        elif tool == "review_task":
            task_review_candidates.append(event)

    completed_checks = tuple(
        check_id
        for check_id in required_checks
        if (
            check_id in latest_checks
            and latest_checks[check_id].payload.get("passed") is True
        )
    )
    pending_checks = tuple(
        check_id
        for check_id in required_checks
        if check_id not in completed_checks
    )
    latest_check_sequence = (
        max(event.sequence for event in latest_checks.values())
        if latest_checks
        else None
    )
    review_event = next(
        (
            event
            for event in reversed(review_candidates)
            if not pending_checks
            and (
                latest_check_sequence is None
                or event.sequence > latest_check_sequence
            )
        ),
        None,
    )
    review_presented = bool(
        review_event is not None
        and review_event.sequence in presented_sequences
    )
    task_review_event = next(
        (
            event
            for event in reversed(task_review_candidates)
            if (
                review_event is not None
                and event.sequence > review_event.sequence
                and event.payload.get("source_get_diff_sequence")
                == review_event.sequence
                and not any(
                    later.sequence > event.sequence
                    and later.type == EventType.TOOL_SUCCEEDED
                    and later.payload.get("tool")
                    in {"run_probe", "run_check", "get_diff"}
                    and later.payload.get("worktree_diff_hash")
                    == worktree_diff_hash
                    for later in events
                )
            )
        ),
        None,
    )
    task_review_presented = bool(
        task_review_event is not None
        and task_review_event.sequence in presented_sequences
    )
    task_review_coverage_complete = (
        task_review_event.payload.get("coverage_complete") is True
        if task_review_event is not None
        else None
    )
    unresolved_coverage_target_ids = (
        [
            value
            for value in (
                task_review_event.payload.get(
                    "unresolved_coverage_target_ids",
                    [],
                )
                if task_review_event is not None
                else []
            )
            if isinstance(value, str)
        ]
    )
    optional_probe = ("run_probe",) if task.probe_profiles else ()
    if not mutation_present:
        allowed = (
            "apply_patch",
            "run_check",
            "read_file",
            "search_files",
            *optional_probe,
        )
    elif pending_checks:
        allowed = (
            "run_check",
            "apply_patch",
            "read_file",
            "search_files",
            *optional_probe,
        )
    elif review_event is None or not review_presented:
        allowed = (
            "get_diff",
            "apply_patch",
            "read_file",
            "search_files",
            *optional_probe,
        )
    elif task_review_event is None:
        allowed = (
            "review_task",
            "apply_patch",
            *(("read_file", "search_files") if coverage_review_required else ()),
            *optional_probe,
        )
    elif coverage_review_required and not task_review_coverage_complete:
        allowed = (
            "get_diff",
            "run_check",
            "apply_patch",
            "read_file",
            "search_files",
            *optional_probe,
        )
    elif not task_review_presented:
        allowed = ("apply_patch",)
    else:
        allowed = ("finish_task", "apply_patch")

    tail_reasons = [
        reason
        for reason in read_search_policy["reason_codes"]
        if reason != "evidence_saturated"
    ]
    if tail_reasons:
        blocked_actions = {"read_file", "search_files", "run_probe"}
    elif "evidence_saturated" in read_search_policy["reason_codes"]:
        blocked_actions = {"read_file", "search_files"}
    else:
        blocked_actions = set()
    filtered_allowed = [
        action for action in allowed if action not in blocked_actions
    ]
    result = {
        "current_phase": phase.value,
        "allowed_next_actions": filtered_allowed,
        "completed_checks": list(completed_checks),
        "pending_checks": list(pending_checks),
        "mutation_event_sequence": (
            latest_mutation.sequence if latest_mutation is not None else None
        ),
        "mutation_present": mutation_present,
        "review_event_sequence": (
            review_event.sequence if review_event is not None else None
        ),
        "task_review_event_sequence": (
            task_review_event.sequence
            if task_review_event is not None
            else None
        ),
    }
    if coverage_review_required:
        result.update(
            {
                "task_review_coverage_complete": (
                    task_review_coverage_complete
                ),
                "unresolved_coverage_target_ids": (
                    unresolved_coverage_target_ids
                ),
            }
        )
    return result


def _v8_saturation_context_evidence(
    *,
    root: Path,
    manifest: RunManifest,
    package: TaskPackage,
    events: list[Any],
    checkpoints: list[Checkpoint],
    context_events: list[Any],
) -> tuple[bool, dict[str, Any]]:
    """Verify v8 saturation visibility without replaying the context builder."""

    artifact_root = root / "artifacts"
    expected_context_build_schema = {
        "phase-evidence-v8": "context-build-evidence-v8",
        "phase-evidence-v9": "context-build-evidence-v9",
        "phase-evidence-v10": "context-build-evidence-v10",
        "phase-evidence-v11": "context-build-evidence-v11",
    }.get(manifest.context_policy_version)
    failed_sequences: list[int] = []
    failed_reasons: dict[int, str] = {}
    verified_sequences: list[int] = []
    saturated_sequences: list[int] = []
    policy_hashes: list[str] = []
    policies_by_context_sequence: dict[int, dict[str, Any]] = {}
    checkpoints_by_id = {
        checkpoint.checkpoint_id: checkpoint for checkpoint in checkpoints
    }
    for context_event in context_events:
        try:
            request_valid, request_evidence = _request_evidence_payload(
                context_event,
                artifact_root=artifact_root,
                expected_provider=manifest.model.provider,
            )
            if not request_valid or request_evidence is None:
                raise RecoveryError("v8 model request evidence is invalid")
            rendered = _request_context(
                request_evidence["request_body"],
                allow_direct_context=(
                    manifest.model.provider in {"mock", "replay"}
                ),
            )
            context_build = request_evidence.get("context_build")
            if (
                expected_context_build_schema is None
                or not isinstance(rendered, str)
                or not isinstance(context_build, dict)
                or context_build.get("schema_version")
                != expected_context_build_schema
            ):
                raise RecoveryError("v8 context build evidence is invalid")
            parsed_context = json.loads(rendered)
            if not isinstance(parsed_context, dict):
                raise RecoveryError("v8 rendered context is not an object")
            phase_contract = parsed_context.get("phase_contract")
            if (
                not isinstance(phase_contract, dict)
                or phase_contract.get("schema_version")
                != (
                    "phase-contract-v4"
                    if manifest.context_policy_version
                    in {"phase-evidence-v10", "phase-evidence-v11"}
                    else "phase-contract-v3"
                )
            ):
                raise RecoveryError("v8 phase contract is invalid")

            source_events = [
                event
                for event in events
                if event.sequence < context_event.sequence
            ]
            expected_tail = _v5_expected_tail_policy(
                task=package.public,
                events=source_events,
                manifest=manifest,
                projection_stage="pre_generation",
            )
            expected_policy = _v8_expected_read_search_policy(
                events=source_events,
                tail_policy=expected_tail,
            )
            checkpoint_events = [
                event
                for event in source_events
                if event.type == EventType.CHECKPOINT_SAVED
                and isinstance(event.payload.get("checkpoint_id"), str)
            ]
            checkpoint = None
            if checkpoint_events:
                checkpoint = checkpoints_by_id.get(
                    checkpoint_events[-1].payload["checkpoint_id"]
                )
                if checkpoint is None:
                    raise RecoveryError(
                        "v8 context checkpoint is unavailable"
                    )
            expected_phase = _v8_expected_phase_contract(
                task=package.public,
                events=source_events,
                checkpoint=checkpoint,
                presented_tool_results=context_build.get("tool_results"),
                read_search_policy=expected_policy,
                coverage_review_required=(
                    manifest.context_policy_version
                    in {"phase-evidence-v10", "phase-evidence-v11"}
                ),
            )
            allowed_next_actions = phase_contract.get(
                "allowed_next_actions"
            )
            if not isinstance(allowed_next_actions, list) or not all(
                isinstance(action, str) for action in allowed_next_actions
            ):
                raise RecoveryError("v8 allowed actions are invalid")
            if allowed_next_actions != expected_phase["allowed_next_actions"]:
                raise RecoveryError(
                    "v8 allowed actions failed independent recomputation"
                )
            phase_mirrors = {
                key: expected_phase[key]
                for key in (
                    "current_phase",
                    "completed_checks",
                    "pending_checks",
                    "mutation_event_sequence",
                    "mutation_present",
                    "review_event_sequence",
                    "task_review_event_sequence",
                )
            }
            if manifest.context_policy_version in {
                "phase-evidence-v10",
                "phase-evidence-v11",
            }:
                phase_mirrors.update(
                    {
                        "task_review_coverage_complete": expected_phase[
                            "task_review_coverage_complete"
                        ],
                        "unresolved_coverage_target_ids": expected_phase[
                            "unresolved_coverage_target_ids"
                        ],
                    }
                )
            if any(
                phase_contract.get(field) != expected
                for field, expected in phase_mirrors.items()
            ):
                raise RecoveryError(
                    "v8 phase readiness failed independent recomputation"
                )
            if phase_contract.get("read_search_policy") != expected_policy:
                raise RecoveryError(
                    "v8 rendered read/search policy failed recomputation"
                )
            if context_build.get("read_search_policy") != expected_policy:
                raise RecoveryError(
                    "v8 read/search evidence mirror failed recomputation"
                )

            event_mirrors = {
                "investigation_read_search_admitted": expected_policy[
                    "admitted"
                ],
                "investigation_read_search_reason_codes": expected_policy[
                    "reason_codes"
                ],
                "investigation_semantic_replay_count": expected_policy[
                    "semantic_replay_count"
                ],
                "investigation_semantic_replay_threshold": (
                    expected_policy["semantic_replay_threshold"]
                ),
                "investigation_saturation_mutation_epoch_sequence": (
                    expected_policy["mutation_epoch_sequence"]
                ),
            }
            if any(
                field not in context_event.payload
                or context_event.payload.get(field) != expected
                for field, expected in event_mirrors.items()
            ):
                raise RecoveryError(
                    "v8 ContextBuilt read/search mirrors failed recomputation"
                )

            verified_sequences.append(context_event.sequence)
            policies_by_context_sequence[context_event.sequence] = expected_policy
            if "evidence_saturated" in expected_policy["reason_codes"]:
                saturated_sequences.append(context_event.sequence)
            policy_hashes.append(
                sha256_text(canonical_json(expected_policy))
            )
        except (
            KeyError,
            OSError,
            RecoveryError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            failed_sequences.append(context_event.sequence)
            failed_reasons[context_event.sequence] = str(exc)
    applied_events = sorted(
        (
            event
            for event in events
            if event.type == EventType.PATCH_APPLIED
        ),
        key=lambda event: event.sequence,
    )
    post_saturation_patch_sequences: list[int] = []
    reset_opportunity_sequences: list[int] = []
    reset_context_sequences: list[int] = []
    failed_reset_context_sequences: list[int] = []
    for patch_event in applied_events:
        prior_patch_sequence = max(
            (
                event.sequence
                for event in applied_events
                if event.sequence < patch_event.sequence
            ),
            default=None,
        )
        active_epoch_saturation = any(
            sequence < patch_event.sequence
            and policies_by_context_sequence[sequence].get(
                "mutation_epoch_sequence"
            )
            == prior_patch_sequence
            for sequence in saturated_sequences
        )
        if not active_epoch_saturation:
            continue
        post_saturation_patch_sequences.append(patch_event.sequence)
        next_context = next(
            (
                event
                for event in context_events
                if event.sequence > patch_event.sequence
            ),
            None,
        )
        next_patch_sequence = min(
            (
                event.sequence
                for event in applied_events
                if event.sequence > patch_event.sequence
            ),
            default=None,
        )
        if next_context is None or (
            next_patch_sequence is not None
            and next_patch_sequence < next_context.sequence
        ):
            continue
        reset_opportunity_sequences.append(patch_event.sequence)
        policy = policies_by_context_sequence.get(next_context.sequence)
        reset_valid = bool(
            isinstance(policy, dict)
            and policy.get("semantic_replay_count") == 0
            and policy.get("mutation_epoch_sequence")
            == patch_event.sequence
            and "evidence_saturated"
            not in policy.get("reason_codes", [])
        )
        if reset_valid:
            reset_context_sequences.append(next_context.sequence)
        else:
            failed_reset_context_sequences.append(next_context.sequence)
    return bool(context_events) and not failed_sequences, {
        "context_count": len(context_events),
        "verified_context_count": len(verified_sequences),
        "verified_context_sequences": verified_sequences,
        "failed_context_sequences": failed_sequences,
        "failed_context_reasons": failed_reasons,
        "saturated_context_count": len(saturated_sequences),
        "saturated_context_sequences": saturated_sequences,
        "read_search_removed_saturated_context_sequences": saturated_sequences,
        "post_saturation_patch_count": len(post_saturation_patch_sequences),
        "post_saturation_patch_sequences": post_saturation_patch_sequences,
        "reset_opportunity_count": len(reset_opportunity_sequences),
        "reset_opportunity_patch_sequences": reset_opportunity_sequences,
        "reset_context_count": len(reset_context_sequences),
        "reset_context_sequences": reset_context_sequences,
        "failed_reset_context_sequences": failed_reset_context_sequences,
        "read_search_policy_hashes": policy_hashes,
    }


def _v4_investigation_lifecycle_evidence(
    *,
    root: Path,
    manifest: RunManifest,
    package: TaskPackage,
    events: list[Any],
) -> tuple[bool, dict[str, Any]]:
    """Independently verify semantic replay and tail-admission lifecycles."""

    from patchloop.agent.investigation import (
        INSPECTION_ADMISSION_PREFLIGHT_SCHEMA,
        INVESTIGATION_LOOP_SCHEMA,
        INVESTIGATION_POLICY_VERSION,
        NO_PROGRESS_STRATEGY_THRESHOLD,
        TOOL_ADMISSION_SCHEMA,
        TOOL_REPLAY_SCHEMA,
        load_inspection_records,
        mutation_epoch,
        nominal_tail_reserve,
        reconstruct_covered_read,
        validate_inspection_arguments,
    )

    artifact_root = (root / "artifacts").resolve()
    artifact_store = ArtifactStore(artifact_root)
    by_sequence = {event.sequence: event for event in events}
    failed_replay_sequences: list[int] = []
    verified_replay_sequences: list[int] = []
    failed_admission_sequences: list[int] = []
    verified_admission_sequences: list[int] = []
    expected_policy_version = (
        "investigation-policy-v2"
        if manifest.context_policy_version
        in {
            "phase-evidence-v5",
            "phase-evidence-v6",
            "phase-evidence-v7",
            "phase-evidence-v8",
            "phase-evidence-v9",
            "phase-evidence-v10",
            "phase-evidence-v11",
        }
        else INVESTIGATION_POLICY_VERSION
    )
    expected_admission_schema = (
        "tool-admission-blocked-v2"
        if manifest.context_policy_version
        in {
            "phase-evidence-v5",
            "phase-evidence-v6",
            "phase-evidence-v7",
            "phase-evidence-v8",
            "phase-evidence-v9",
            "phase-evidence-v10",
            "phase-evidence-v11",
        }
        else TOOL_ADMISSION_SCHEMA
    )

    def nested_json(
        event,
        *,
        role: str,
        descriptor: Any,
    ) -> tuple[bool, dict[str, Any] | None, dict[str, Any]]:
        valid, item, content = _nested_cas_artifact_evidence(
            artifact_root=artifact_root,
            event_id=event.event_id,
            role=role,
            raw_artifact=descriptor,
        )
        value = None
        if content is not None:
            try:
                parsed = json.loads(content.decode("utf-8"))
                if isinstance(parsed, dict):
                    value = parsed
                else:
                    valid = False
            except (UnicodeDecodeError, json.JSONDecodeError):
                valid = False
        return valid, value, item

    semantic_loops = [
        event
        for event in events
        if event.type == EventType.LOOP_DETECTED
        and (
            event.payload.get("schema_version")
            == INVESTIGATION_LOOP_SCHEMA
            or event.payload.get("enforcement")
            == "semantic-cache-replay"
            or event.payload.get("reason_code")
            in {"duplicate_search", "fully_covered_read"}
            or (
                by_sequence.get(event.sequence + 1) is not None
                and by_sequence[event.sequence + 1].type
                == EventType.TOOL_REPLAYED
                and by_sequence[event.sequence + 1].correlation_id
                == event.correlation_id
            )
        )
    ]
    semantic_replays = [
        event
        for event in events
        if event.type == EventType.TOOL_REPLAYED
        and (
            event.payload.get("schema_version") == TOOL_REPLAY_SCHEMA
            or event.payload.get("semantic_replay") is True
            or event.payload.get("replay_kind")
            == "semantic-investigation"
            or event.actor == "semantic-cache"
            or (
                by_sequence.get(event.sequence - 1) is not None
                and by_sequence[event.sequence - 1].type
                == EventType.LOOP_DETECTED
                and by_sequence[event.sequence - 1].correlation_id
                == event.correlation_id
            )
        )
    ]
    for replay in semantic_replays:
        replay_ok = True
        call = by_sequence.get(replay.sequence - 2)
        loop = by_sequence.get(replay.sequence - 1)
        action_id = replay.correlation_id
        if not (
            isinstance(action_id, str)
            and action_id
            and call is not None
            and call.type == EventType.TOOL_CALLED
            and call.actor == "agent"
            and call.correlation_id == action_id
            and loop is not None
            and loop.type == EventType.LOOP_DETECTED
            and loop.actor == "tool-gateway"
            and loop.correlation_id == action_id
            and replay.actor == "semantic-cache"
        ):
            replay_ok = False
        if not replay_ok:
            failed_replay_sequences.append(replay.sequence)
            continue

        tool = call.payload.get("tool")
        input_descriptor = call.payload.get("input_artifact")
        input_valid, input_payload, input_item = nested_json(
            call,
            role="investigation-replay-input",
            descriptor=input_descriptor,
        )
        arguments = (
            input_payload.get("input")
            if isinstance(input_payload, dict)
            else None
        )
        worktree_diff_hash = call.payload.get("worktree_diff_hash")
        input_hash = call.payload.get("input_hash")
        normalized_call_hash = call.payload.get("normalized_call_hash")
        replay_ok = bool(
            replay_ok
            and tool in {"read_file", "search_files"}
            and call.payload.get("execution") == "semantic-cache-replay"
            and input_valid
            and isinstance(input_payload, dict)
            and input_payload.get("tool") == tool
            and isinstance(arguments, dict)
            and call.payload.get("artifact_id")
            == input_item.get("artifact_id")
            and call.payload.get("artifact_path")
            == input_item.get("declared_path")
            and isinstance(worktree_diff_hash, str)
            and isinstance(input_hash, str)
            and isinstance(normalized_call_hash, str)
        )
        if not replay_ok:
            failed_replay_sequences.append(replay.sequence)
            continue
        expected_input_hash = sha256_text(
            canonical_json({"tool": tool, "input": arguments})
        )
        expected_normalized_hash = sha256_text(
            canonical_json(
                {
                    "tool": tool,
                    "input": arguments,
                    "worktree_diff_hash": worktree_diff_hash,
                    "state_marker": None,
                }
            )
        )
        prefix = [
            event for event in events if event.sequence < call.sequence
        ]
        checkpoint_events = [
            event
            for event in prefix
            if event.type == EventType.CHECKPOINT_SAVED
        ]
        replay_ok = bool(
            input_hash == expected_input_hash
            and normalized_call_hash == expected_normalized_hash
            and checkpoint_events
            and checkpoint_events[-1].payload.get(
                "worktree_diff_hash"
            )
            == worktree_diff_hash
        )
        try:
            records = load_inspection_records(
                prefix,
                artifact_store,
                worktree_diff_hash=worktree_diff_hash,
            )
        except RecoveryError:
            records = []
            replay_ok = False

        sources = []
        replay_output: dict[str, Any] | None = None
        reason_code: str | None = None
        if replay_ok and tool == "search_files":
            exact = [
                record
                for record in records
                if record.tool == tool
                and record.normalized_call_hash
                == normalized_call_hash
                and record.result["truncated"] is False
            ]
            if exact:
                sources = [exact[-1]]
                replay_output = dict(exact[-1].result)
                reason_code = "duplicate_search"
        elif (
            replay_ok
            and tool == "read_file"
            and isinstance(arguments.get("path"), str)
            and type(arguments.get("start_line")) is int
            and type(arguments.get("end_line")) is int
        ):
            try:
                reconstructed = reconstruct_covered_read(
                    records,
                    path=arguments["path"],
                    start_line=arguments["start_line"],
                    end_line=arguments["end_line"],
                    worktree_diff_hash=worktree_diff_hash,
                )
            except RecoveryError:
                reconstructed = None
                replay_ok = False
            if reconstructed is not None:
                replay_output, sources = reconstructed
                reason_code = "fully_covered_read"
        if replay_output is None or reason_code is None:
            replay_ok = False

        source_call_sequences = [
            source.call_sequence for source in sources
        ]
        source_outcome_sequences = [
            source.outcome_sequence for source in sources
        ]
        expected_result = {
            **(replay_output or {}),
            "novelty": {
                "classification": "seen_only",
                "new_evidence_count": 0,
                "reason": reason_code,
            },
            "semantic_replay": True,
            "replay_kind": "semantic-investigation",
            "replay_reason": reason_code,
            "source_call_sequences": source_call_sequences,
            "source_outcome_sequences": source_outcome_sequences,
        }
        result_valid, result_payload, result_item = nested_json(
            replay,
            role="investigation-replay-result",
            descriptor=replay.payload.get("result_artifact"),
        )
        replay_ok = bool(
            replay_ok
            and result_valid
            and result_payload == expected_result
            and replay.payload.get("artifact_id")
            == result_item.get("artifact_id")
            and replay.payload.get("artifact_path")
            == result_item.get("declared_path")
        )

        new_streak = _v4_no_progress_streak(prefix) + 1
        expected_loop = {
            "schema_version": INVESTIGATION_LOOP_SCHEMA,
            "policy_version": INVESTIGATION_POLICY_VERSION,
            "tool": tool,
            "reason_code": reason_code,
            "normalized_call_hash": normalized_call_hash,
            "source_call_sequences": source_call_sequences,
            "source_outcome_sequences": source_outcome_sequences,
            "mutation_epoch_sequence": mutation_epoch(prefix),
            "worktree_diff_hash": worktree_diff_hash,
            "no_progress_streak": new_streak,
            "strategy_change_required": (
                new_streak >= NO_PROGRESS_STRATEGY_THRESHOLD
            ),
            "occurrences": new_streak + 1,
            "enforcement": "semantic-cache-replay",
        }
        replay_without_duration = dict(replay.payload)
        duration_ms = replay_without_duration.pop("duration_ms", None)
        expected_replay = {
            "schema_version": TOOL_REPLAY_SCHEMA,
            "tool": tool,
            "status": "succeeded",
            "semantic_replay": True,
            "replay_kind": "semantic-investigation",
            "reason_code": reason_code,
            "input_hash": input_hash,
            "normalized_call_hash": normalized_call_hash,
            "source_action_ids": [
                source.action_id for source in sources
            ],
            "source_call_sequences": source_call_sequences,
            "source_outcome_sequences": source_outcome_sequences,
            "mutation_epoch_sequence": mutation_epoch(prefix),
            "worktree_diff_hash": worktree_diff_hash,
            "artifact_id": result_item.get("artifact_id"),
            "artifact_path": result_item.get("declared_path"),
            "result_artifact": replay.payload.get("result_artifact"),
        }
        replay_ok = bool(
            replay_ok
            and loop.payload == expected_loop
            and type(duration_ms) is int
            and duration_ms >= 0
            and replay_without_duration == expected_replay
        )
        if replay_ok:
            verified_replay_sequences.append(replay.sequence)
        else:
            failed_replay_sequences.append(replay.sequence)

    admission_events = [
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version")
        != "turn-mutation-barrier-v1"
    ]
    reserve = (
        _v5_expected_tail_policy(
            task=package.public,
            events=[],
            manifest=manifest,
            projection_stage="post_generation",
        )["nominal_reserve"]
        if manifest.context_policy_version
        in {
            "phase-evidence-v8",
            "phase-evidence-v9",
            "phase-evidence-v10",
            "phase-evidence-v11",
        }
        else nominal_tail_reserve(
            package.public,
            context_policy_version=manifest.context_policy_version,
        )
    )
    for admission in admission_events:
        prefix = [
            event
            for event in events
            if event.sequence < admission.sequence
        ]
        action_id = admission.correlation_id
        payload = admission.payload
        tool = payload.get("tool")
        model_calls_used = sum(
            event.type == EventType.MODEL_CALLED for event in prefix
        )
        tool_calls_used = sum(
            event.type == EventType.TOOL_CALLED for event in prefix
        )
        remaining_model_calls = (
            manifest.budget.max_model_calls - model_calls_used
        )
        remaining_tool_calls = (
            manifest.budget.max_tool_calls - tool_calls_used
        )
        calculated_tail_policy = None
        if manifest.context_policy_version in {
            "phase-evidence-v5",
            "phase-evidence-v6",
            "phase-evidence-v7",
            "phase-evidence-v8",
            "phase-evidence-v9",
            "phase-evidence-v10",
            "phase-evidence-v11",
        }:
            calculated_tail_policy = _v5_expected_tail_policy(
                task=package.public,
                events=prefix,
                manifest=manifest,
                projection_stage="post_generation",
            )
            reason_codes = list(
                calculated_tail_policy["block_reasons"]
            )
        else:
            reason_codes = []
            if remaining_tool_calls <= reserve["tool_calls"]:
                reason_codes.append("tool_tail_reserved")
            if remaining_model_calls <= (
                reserve["model_calls"]
                + reserve["feedback_model_calls"]
            ):
                reason_codes.append("model_tail_reserved")
        epoch = mutation_epoch(prefix)
        semantic_replay_count = sum(
            event.type == EventType.TOOL_REPLAYED
            and event.payload.get("semantic_replay") is True
            and (epoch is None or event.sequence > epoch)
            for event in prefix
        )
        saturation_threshold = (
            _V8_EVIDENCE_SATURATION_THRESHOLD
            if manifest.context_policy_version
            in {
                "phase-evidence-v8",
                "phase-evidence-v9",
                "phase-evidence-v10",
                "phase-evidence-v11",
            }
            else 6
        )
        evidence_saturated = bool(
            manifest.context_policy_version
            in {
                "phase-evidence-v7",
                "phase-evidence-v8",
                "phase-evidence-v9",
                "phase-evidence-v10",
                "phase-evidence-v11",
            }
            and tool in {"read_file", "search_files"}
            and semantic_replay_count >= saturation_threshold
        )
        if evidence_saturated:
            reason_codes.append("evidence_saturated")
        input_valid, input_payload, input_item = nested_json(
            admission,
            role="investigation-admission-input",
            descriptor=payload.get("input_artifact"),
        )
        result_valid, result_payload, result_item = nested_json(
            admission,
            role="investigation-admission-result",
            descriptor=payload.get("result_artifact"),
        )
        preflight_valid, preflight_payload, preflight_item = nested_json(
            admission,
            role="investigation-admission-preflight",
            descriptor=payload.get("preflight_artifact"),
        )
        arguments = (
            input_payload.get("input")
            if isinstance(input_payload, dict)
            else None
        )
        input_hash = payload.get("input_hash")
        normalized_call_hash = payload.get("normalized_call_hash")
        worktree_diff_hash = payload.get("worktree_diff_hash")
        expected_input_hash = (
            sha256_text(
                canonical_json({"tool": tool, "input": arguments})
            )
            if tool in {"read_file", "search_files"}
            and isinstance(arguments, dict)
            else None
        )
        expected_normalized_hash = (
            sha256_text(
                canonical_json(
                    {
                        "tool": tool,
                        "input": arguments,
                        "worktree_diff_hash": worktree_diff_hash,
                        "state_marker": None,
                    }
                )
            )
            if expected_input_hash is not None
            and isinstance(worktree_diff_hash, str)
            else None
        )
        admission_request_valid = False
        preflight_evidence_valid = False
        try:
            validate_inspection_arguments(
                None,
                str(tool),
                arguments if isinstance(arguments, dict) else {},
                require_current_target=False,
            )
            admission_request_valid = True
            expected_preflight: dict[str, Any] = {
                "schema_version": (
                    INSPECTION_ADMISSION_PREFLIGHT_SCHEMA
                ),
                "policy_version": expected_policy_version,
                "tool": tool,
                "worktree_diff_hash": worktree_diff_hash,
            }
            if tool == "read_file":
                resolved_path = (
                    preflight_payload.get("resolved_relative_path")
                    if isinstance(preflight_payload, dict)
                    else None
                )
                if not isinstance(resolved_path, str):
                    raise ContractError(
                        "read admission preflight lacks a resolved path"
                    )
                safe_relative_path(
                    resolved_path,
                    field_name="resolved_relative_path",
                )
                target_descriptor = (
                    preflight_payload.get("target_artifact")
                    if isinstance(preflight_payload, dict)
                    else None
                )
                (
                    target_valid,
                    target_item,
                    target_content,
                ) = _nested_cas_artifact_evidence(
                    artifact_root=artifact_root,
                    event_id=admission.event_id,
                    role="investigation-admission-target",
                    raw_artifact=target_descriptor,
                )
                expected_preflight.update(
                    {
                        "requested_path": arguments["path"],
                        "resolved_relative_path": resolved_path,
                        "target_artifact": target_descriptor,
                    }
                )
                preflight_evidence_valid = bool(
                    target_valid
                    and target_content is not None
                    and target_item.get("artifact_id")
                    == target_descriptor.get("artifact_id")
                )
            else:
                expected_preflight.update(
                    {
                        "query": arguments["query"],
                        "path_glob": arguments.get(
                            "path_glob",
                            "**/*",
                        ),
                    }
                )
                preflight_evidence_valid = True
            preflight_evidence_valid = bool(
                preflight_evidence_valid
                and preflight_valid
                and preflight_payload == expected_preflight
                and payload.get("preflight_artifact", {}).get(
                    "artifact_id"
                )
                == preflight_item.get("artifact_id")
            )
        except (AttributeError, ContractError, TypeError):
            admission_request_valid = False
            preflight_evidence_valid = False
        error_message = (
            "inspection was not admitted because the active mutation epoch "
            "has exhausted its semantic replay allowance; use the durable "
            "evidence or make a scoped mutation"
            if evidence_saturated
            else (
                "inspection was not admitted because the nominal corrective "
                "lifecycle tail is reserved; use apply_patch or another "
                "phase-advancing action"
            )
        )
        error_details = {
            "schema_version": expected_admission_schema,
            "policy_version": expected_policy_version,
            "reason_codes": reason_codes,
            "nominal_reserve": reserve,
            "remaining_model_calls": remaining_model_calls,
            "remaining_tool_calls": remaining_tool_calls,
            "guidance": (
                "Use the durable investigation ledger and move to a scoped "
                "patch, registered validation, diff review, or submission."
            ),
        }
        if calculated_tail_policy is not None:
            error_details["tail_policy"] = calculated_tail_policy
        if evidence_saturated:
            error_details.update(
                {
                    "evidence_saturation_policy_version": (
                        "evidence-saturation-v1"
                    ),
                    "semantic_replay_count": semantic_replay_count,
                    "semantic_replay_threshold": saturation_threshold,
                    "mutation_epoch_sequence": epoch,
                }
            )
        expected_result = {
            "tool": tool,
            "status": "rejected",
            "error_code": "TOOL_ADMISSION_BLOCKED",
            "error_message": error_message,
            "error_details": error_details,
            "admission_blocked": True,
            "worktree_diff_hash": worktree_diff_hash,
            "preflight_artifact": payload.get(
                "preflight_artifact"
            ),
        }
        expected_event = {
            "schema_version": expected_admission_schema,
            "policy_version": expected_policy_version,
            "tool": tool,
            "status": "rejected",
            "input_hash": input_hash,
            "normalized_call_hash": normalized_call_hash,
            "worktree_diff_hash": worktree_diff_hash,
            "mutation_epoch_sequence": epoch,
            "reason_codes": reason_codes,
            "nominal_reserve": reserve,
            "model_calls_used": model_calls_used,
            "max_model_calls": manifest.budget.max_model_calls,
            "tool_calls_used": tool_calls_used,
            "max_tool_calls": manifest.budget.max_tool_calls,
            "input_artifact": payload.get("input_artifact"),
            "preflight_artifact": payload.get(
                "preflight_artifact"
            ),
            "result_artifact": payload.get("result_artifact"),
            "artifact_id": result_item.get("artifact_id"),
            "artifact_path": result_item.get("declared_path"),
            "error_code": "TOOL_ADMISSION_BLOCKED",
            "error_message": error_message,
            "error_details": error_details,
        }
        if calculated_tail_policy is not None:
            token_projection = calculated_tail_policy[
                "token_projection"
            ]
            expected_event.update(
                {
                    "tail_policy": calculated_tail_policy,
                    "tokens_used": token_projection[
                        "total_tokens_used"
                    ],
                    "remaining_tokens": token_projection[
                        "remaining_tokens"
                    ],
                    "max_total_tokens": (
                        manifest.budget.max_total_tokens
                    ),
                    "max_output_tokens": (
                        manifest.model.max_output_tokens
                    ),
                }
            )
        if evidence_saturated:
            expected_event.update(
                {
                    "evidence_saturation_policy_version": (
                        "evidence-saturation-v1"
                    ),
                    "semantic_replay_count": semantic_replay_count,
                    "semantic_replay_threshold": saturation_threshold,
                }
            )
        checkpoint_events = [
            event
            for event in prefix
            if event.type == EventType.CHECKPOINT_SAVED
        ]
        correlated_calls = [
            event
            for event in events
            if event.type == EventType.TOOL_CALLED
            and event.correlation_id == action_id
        ]
        admission_ok = bool(
            isinstance(action_id, str)
            and action_id
            and admission.actor == "tool-admission-policy"
            and reason_codes
            and admission_request_valid
            and preflight_evidence_valid
            and input_valid
            and result_valid
            and isinstance(input_payload, dict)
            and input_payload.get("tool") == tool
            and isinstance(arguments, dict)
            and input_hash == expected_input_hash
            and normalized_call_hash == expected_normalized_hash
            and checkpoint_events
            and checkpoint_events[-1].payload.get(
                "worktree_diff_hash"
            )
            == worktree_diff_hash
            and result_payload == expected_result
            and payload.get("artifact_id")
            == result_item.get("artifact_id")
            and payload.get("artifact_path")
            == result_item.get("declared_path")
            and payload == expected_event
            and not correlated_calls
            and input_item.get("artifact_id")
            == payload.get("input_artifact", {}).get("artifact_id")
        )
        if admission_ok:
            verified_admission_sequences.append(admission.sequence)
        else:
            failed_admission_sequences.append(admission.sequence)

    orphan_loop_sequences = [
        loop.sequence
        for loop in semantic_loops
        if not any(
            replay.sequence == loop.sequence + 1
            and replay.correlation_id == loop.correlation_id
            for replay in semantic_replays
        )
    ]
    malformed_semantic_replays = [
        event.sequence
        for event in semantic_replays
        if (
            event.payload.get("schema_version") != TOOL_REPLAY_SCHEMA
            or event.payload.get("semantic_replay") is not True
            or event.payload.get("replay_kind")
            != "semantic-investigation"
            or event.actor != "semantic-cache"
        )
    ]
    failed_replay_sequences.extend(malformed_semantic_replays)
    failed_replay_sequences.extend(orphan_loop_sequences)
    passed = not failed_replay_sequences and not failed_admission_sequences
    return passed, {
        "semantic_replay_count": len(semantic_replays),
        "verified_semantic_replay_count": len(
            verified_replay_sequences
        ),
        "failed_semantic_replay_sequences": sorted(
            set(failed_replay_sequences)
        ),
        "admission_block_count": len(admission_events),
        "verified_admission_block_count": len(
            verified_admission_sequences
        ),
        "failed_admission_block_sequences": sorted(
            set(failed_admission_sequences)
        ),
    }


def _v7_turn_mutation_barrier_evidence(
    *,
    root: Path,
    events: list[Any],
) -> tuple[bool, dict[str, Any]]:
    """Verify every post-apply same-turn call is durably nonexecuted."""

    artifact_root = (root / "artifacts").resolve()
    by_id = {event.event_id: event for event in events}
    blocked = [
        event
        for event in events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version")
        == "turn-mutation-barrier-v1"
    ]
    failed_sequences: list[int] = []
    verified_sequences: list[int] = []
    for event in blocked:
        payload = event.payload
        source_model = by_id.get(payload.get("source_model_event_id"))
        source_action_id = payload.get("source_action_id")
        source_calls = [
            candidate
            for candidate in events
            if candidate.type == EventType.TOOL_CALLED
            and candidate.correlation_id == source_action_id
            and candidate.payload.get("tool") == "apply_patch"
            and candidate.sequence < event.sequence
        ]
        source_outcomes = [
            candidate
            for candidate in events
            if candidate.type in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}
            and candidate.correlation_id == source_action_id
            and candidate.payload.get("tool") == "apply_patch"
            and candidate.sequence < event.sequence
        ]
        input_valid, input_item, input_content = _nested_cas_artifact_evidence(
            artifact_root=artifact_root,
            event_id=event.event_id,
            role="turn-barrier-input",
            raw_artifact=payload.get("input_artifact"),
        )
        result_valid, result_item, result_content = _nested_cas_artifact_evidence(
            artifact_root=artifact_root,
            event_id=event.event_id,
            role="turn-barrier-result",
            raw_artifact=payload.get("result_artifact"),
        )
        try:
            input_payload = json.loads(input_content or b"")
            result_payload = json.loads(result_content or b"")
            model_path = Path(str(source_model.payload["artifact_path"])).resolve()
            relative = model_path.relative_to(artifact_root)
            parts = relative.parts
            model_content = model_path.read_bytes()
            model_payload = json.loads(model_content.decode("utf-8"))
            model_artifact_valid = bool(
                len(parts) == 4
                and parts[0:2] == ("objects", "sha256")
                and sha256_bytes(model_content)
                == f"sha256:{parts[2]}{parts[3]}"
            )
        except (
            KeyError,
            OSError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            input_payload = None
            result_payload = None
            model_payload = None
            model_artifact_valid = False
        source_index = payload.get("source_call_index")
        blocked_index = payload.get("blocked_call_index")
        tool_calls = (
            model_payload.get("tool_calls")
            if isinstance(model_payload, dict)
            else None
        )
        source_declared = (
            tool_calls[source_index - 1]
            if isinstance(tool_calls, list)
            and type(source_index) is int
            and 1 <= source_index <= len(tool_calls)
            else None
        )
        blocked_declared = (
            tool_calls[blocked_index - 1]
            if isinstance(tool_calls, list)
            and type(blocked_index) is int
            and 1 <= blocked_index <= len(tool_calls)
            else None
        )
        expected_input_hash = (
            sha256_text(
                canonical_json(
                    {
                        "tool": blocked_declared.get("name"),
                        "input": blocked_declared.get("arguments"),
                    }
                )
            )
            if isinstance(blocked_declared, dict)
            else None
        )
        expected_details = {
            "schema_version": "tool-admission-blocked-v3",
            "policy_version": "turn-mutation-barrier-v1",
            "reason_codes": ["prior_apply_patch_same_turn"],
            "source_action_id": source_action_id,
            "source_result_status": payload.get("source_result_status"),
            "source_model_event_id": payload.get("source_model_event_id"),
            "source_call_index": source_index,
            "blocked_call_index": blocked_index,
            "guidance": (
                "Inspect the apply_patch result in the next request before "
                "choosing any follow-up tool."
            ),
        }
        expected_result = {
            "tool": payload.get("tool"),
            "status": "rejected",
            "error_code": "TOOL_ADMISSION_BLOCKED",
            "error_message": payload.get("error_message"),
            "error_details": expected_details,
            "admission_blocked": True,
            "worktree_diff_hash": payload.get("worktree_diff_hash"),
        }
        correlated_dispatches = [
            candidate
            for candidate in events
            if candidate.type == EventType.TOOL_CALLED
            and candidate.correlation_id == event.correlation_id
        ]
        valid = bool(
            event.actor == "tool-admission-policy"
            and model_artifact_valid
            and isinstance(source_model, object)
            and source_model is not None
            and source_model.type == EventType.MODEL_CALLED
            and len(source_calls) == 1
            and len(source_outcomes) == 1
            and isinstance(source_declared, dict)
            and source_declared.get("name") == "apply_patch"
            and source_declared.get("action_id") == source_action_id
            and isinstance(blocked_declared, dict)
            and blocked_declared.get("name") == payload.get("tool")
            and blocked_declared.get("action_id") == event.correlation_id
            and blocked_index > source_index
            and payload.get("source_result_status")
            == source_outcomes[0].payload.get("status")
            and input_valid
            and input_payload
            == {
                "tool": blocked_declared.get("name"),
                "input": blocked_declared.get("arguments"),
            }
            and payload.get("input_hash") == expected_input_hash
            and result_valid
            and result_payload == expected_result
            and payload.get("artifact_id")
            == result_item.get("artifact_id")
            and payload.get("artifact_path")
            == result_item.get("declared_path")
            and input_item.get("artifact_id")
            == payload.get("input_artifact", {}).get("artifact_id")
            and not correlated_dispatches
        )
        if valid:
            verified_sequences.append(event.sequence)
        else:
            failed_sequences.append(event.sequence)
    expected_barriers: set[tuple[str, int, str]] = set()
    for model_event in events:
        if model_event.type != EventType.MODEL_CALLED:
            continue
        try:
            model_path = Path(
                str(model_event.payload["artifact_path"])
            ).resolve()
            relative = model_path.relative_to(artifact_root)
            parts = relative.parts
            content = model_path.read_bytes()
            payload = json.loads(content.decode("utf-8"))
            calls = payload.get("tool_calls")
            if (
                len(parts) != 4
                or parts[0:2] != ("objects", "sha256")
                or sha256_bytes(content)
                != f"sha256:{parts[2]}{parts[3]}"
                or not isinstance(calls, list)
            ):
                continue
            first_apply = next(
                (
                    index
                    for index, call in enumerate(calls, 1)
                    if isinstance(call, dict)
                    and call.get("name") == "apply_patch"
                ),
                None,
            )
            if first_apply is None:
                continue
            source_call = calls[first_apply - 1]
            source_action_id = (
                source_call.get("action_id")
                if isinstance(source_call, dict)
                else None
            )
            source_completed = any(
                event.type
                in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}
                and event.correlation_id == source_action_id
                and event.payload.get("tool") == "apply_patch"
                for event in events
            )
            if not source_completed:
                continue
            expected_barriers.update(
                (
                    model_event.event_id,
                    index,
                    str(call.get("action_id")),
                )
                for index, call in enumerate(calls, 1)
                if index > first_apply and isinstance(call, dict)
            )
        except (
            KeyError,
            OSError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            continue
    actual_barriers = {
        (
            str(event.payload.get("source_model_event_id")),
            int(event.payload.get("blocked_call_index")),
            str(event.correlation_id),
        )
        for event in blocked
        if type(event.payload.get("blocked_call_index")) is int
    }
    coverage_valid = expected_barriers == actual_barriers
    return not failed_sequences and coverage_valid, {
        "barrier_block_count": len(blocked),
        "verified_barrier_block_count": len(verified_sequences),
        "verified_barrier_sequences": verified_sequences,
        "failed_barrier_sequences": failed_sequences,
        "expected_barrier_count": len(expected_barriers),
        "barrier_coverage_valid": coverage_valid,
    }


def _request_runtime_contract_valid(
    request_body: Any,
    manifest: RunManifest,
) -> bool:
    """Bind a no-generation request to the frozen adapter/runtime contract."""

    from patchloop.agent.model import (
        SYSTEM_PROMPT_V1,
        SYSTEM_PROMPT_V2,
        SYSTEM_PROMPT_V3,
        SYSTEM_PROMPT_V4,
        SYSTEM_PROMPT_V5,
        SYSTEM_PROMPT_V6,
        SYSTEM_PROMPT_V7,
        SYSTEM_PROMPT_V8,
    )
    from patchloop.agent.tools import (
        TOOL_SCHEMAS_V1,
        TOOL_SCHEMAS_V2,
        TOOL_SCHEMAS_V3,
        TOOL_SCHEMAS_V4,
        TOOL_SCHEMAS_V5,
        TOOL_SCHEMAS_V6,
    )

    if (
        manifest.tool_schema_version == "v1"
        and manifest.context_policy_version == "v1"
    ):
        system_prompt = SYSTEM_PROMPT_V1
        tools = TOOL_SCHEMAS_V1
    elif (
        manifest.tool_schema_version == "v2"
        and manifest.context_policy_version
        in {"phase-evidence-v2", "phase-evidence-v3"}
    ):
        system_prompt = SYSTEM_PROMPT_V2
        tools = TOOL_SCHEMAS_V2
    elif (
        manifest.tool_schema_version == "v2"
        and manifest.context_policy_version
        in {"phase-evidence-v4", "phase-evidence-v5"}
    ):
        system_prompt = SYSTEM_PROMPT_V3
        tools = TOOL_SCHEMAS_V2
    elif (
        manifest.tool_schema_version == "v3"
        and manifest.context_policy_version == "phase-evidence-v6"
    ):
        system_prompt = SYSTEM_PROMPT_V4
        tools = TOOL_SCHEMAS_V3
    elif (
        manifest.tool_schema_version == "v4"
        and manifest.context_policy_version
        in {"phase-evidence-v7", "phase-evidence-v8"}
    ):
        system_prompt = SYSTEM_PROMPT_V5
        tools = TOOL_SCHEMAS_V4
    elif (
        manifest.tool_schema_version == "v4"
        and manifest.context_policy_version == "phase-evidence-v9"
    ):
        system_prompt = SYSTEM_PROMPT_V6
        tools = TOOL_SCHEMAS_V4
    elif (
        manifest.tool_schema_version == "v5"
        and manifest.context_policy_version == "phase-evidence-v10"
    ):
        system_prompt = SYSTEM_PROMPT_V7
        tools = TOOL_SCHEMAS_V5
    elif (
        manifest.tool_schema_version == "v6"
        and manifest.context_policy_version == "phase-evidence-v11"
    ):
        system_prompt = SYSTEM_PROMPT_V8
        tools = TOOL_SCHEMAS_V6
    else:
        return False

    if manifest.model.provider in {"mock", "replay"}:
        return bool(
            isinstance(request_body, dict)
            and set(request_body)
            == {"model", "system_prompt", "context", "tools"}
            and request_body.get("model")
            == manifest.model.model_id
            and request_body.get("system_prompt") == system_prompt
            and isinstance(request_body.get("context"), str)
            and request_body.get("tools") == tools
        )

    reasoning: dict[str, str] = {
        "effort": manifest.model.reasoning_effort,
    }
    if manifest.model.model_id.startswith("gpt-5.6"):
        reasoning.update(
            {
                "mode": manifest.model.reasoning_mode,
                "context": "current_turn",
            }
        )
    if not isinstance(request_body, dict):
        return False
    inputs = request_body.get("input")
    return bool(
        set(request_body)
        == {
            "model",
            "input",
            "tools",
            "store",
            "reasoning",
            "service_tier",
            "max_output_tokens",
            "truncation",
        }
        and isinstance(inputs, list)
        and len(inputs) == 2
        and inputs[0] == {"role": "system", "content": system_prompt}
        and isinstance(inputs[1], dict)
        and set(inputs[1]) == {"role", "content"}
        and inputs[1].get("role") == "user"
        and isinstance(inputs[1].get("content"), str)
        and request_body.get("model") == manifest.model.model_id
        and request_body.get("tools") == tools
        and request_body.get("store") is False
        and request_body.get("reasoning") == reasoning
        and request_body.get("service_tier")
        == manifest.model.service_tier
        and request_body.get("max_output_tokens")
        == manifest.model.max_output_tokens
        and request_body.get("truncation") == "disabled"
    )


def _generation_block_common_valid(
    *,
    root: Path,
    manifest: RunManifest,
    events,
    context_event,
    blocked_event,
    expected_retry_candidate_hash: str | None,
) -> bool:
    """Validate request, retry, and terminal bindings shared by block versions."""

    payload = blocked_event.payload
    request_valid, request_evidence = _request_evidence_payload(
        context_event,
        artifact_root=(root / "artifacts"),
        expected_provider=(
            manifest.model.provider
            if manifest.context_policy_version
            in {
                "phase-evidence-v4",
                "phase-evidence-v5",
                "phase-evidence-v6",
                "phase-evidence-v7",
                "phase-evidence-v8",
                "phase-evidence-v9",
                "phase-evidence-v10",
                "phase-evidence-v11",
            }
            else None
        ),
    )
    rendered_payload = None
    retry_build_evidence = None
    if request_valid and request_evidence is not None:
        try:
            request_body = request_evidence["request_body"]
            rendered_context = _request_context(
                request_body,
                allow_direct_context=(
                    request_evidence.get("provider")
                    in {"mock", "replay"}
                ),
            )
            rendered_payload = json.loads(str(rendered_context))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            request_body = None
            rendered_payload = None
        context_build = request_evidence.get("context_build")
        if isinstance(context_build, dict):
            retry_build_evidence = context_build.get(
                "rejected_mutation_retry"
            )
    else:
        request_body = None

    if expected_retry_candidate_hash is None:
        retry_mode_valid = bool(
            payload.get("retry_context_present") is False
            and payload.get("retry_candidate_content_hash") is None
            and isinstance(rendered_payload, dict)
            and "rejected_mutation_retry" in rendered_payload
            and rendered_payload["rejected_mutation_retry"] is None
            and isinstance(retry_build_evidence, dict)
            and retry_build_evidence.get("included") is False
            and retry_build_evidence.get("truncated") is False
        )
    else:
        rendered_retry = (
            rendered_payload.get("rejected_mutation_retry")
            if isinstance(rendered_payload, dict)
            else None
        )
        rendered_candidate = (
            rendered_retry.get("candidate")
            if isinstance(rendered_retry, dict)
            else None
        )
        build_candidate = (
            retry_build_evidence.get("candidate")
            if isinstance(retry_build_evidence, dict)
            else None
        )
        retry_mode_valid = bool(
            payload.get("retry_context_present") is True
            and payload.get("retry_candidate_content_hash")
            == expected_retry_candidate_hash
            and isinstance(rendered_candidate, dict)
            and rendered_candidate.get("content_hash")
            == expected_retry_candidate_hash
            and isinstance(retry_build_evidence, dict)
            and retry_build_evidence.get("included") is True
            and retry_build_evidence.get("truncated") is False
            and isinstance(build_candidate, dict)
            and build_candidate.get("content_hash")
            == expected_retry_candidate_hash
        )

    max_output = blocked_event.payload.get("max_output_tokens")
    trailing_events = [
        event for event in events if event.sequence > blocked_event.sequence
    ]
    return bool(
        request_valid
        and _request_runtime_contract_valid(request_body, manifest)
        and retry_mode_valid
        and blocked_event.type == EventType.MODEL_GENERATION_BLOCKED
        and blocked_event.sequence == context_event.sequence + 1
        and blocked_event.payload.get("error_code") == "MODEL_GENERATION_BUDGET_EXCEEDED"
        and blocked_event.payload.get("generation_started") is False
        and blocked_event.payload.get("request_artifact_id")
        == context_event.payload.get("artifact_id")
        and blocked_event.payload.get("request_artifact_path")
        == context_event.payload.get("artifact_path")
        and blocked_event.payload.get("request_body_hash")
        == context_event.payload.get("request_body_hash")
        and type(max_output) is int
        and max_output == manifest.model.max_output_tokens
        and isinstance(request_body, dict)
        and request_body.get("max_output_tokens") == max_output
        and sum(event.type == EventType.RUN_FAILED for event in trailing_events) == 1
        and bool(trailing_events)
        and trailing_events[-1].type == EventType.RUN_FAILED
        and all(
            event.type in {EventType.FAILURE_TAGGED, EventType.RUN_FAILED}
            for event in trailing_events
        )
    )


def _exact_request_generation_block_valid(
    *,
    root: Path,
    manifest: RunManifest,
    events,
    context_event,
    blocked_event,
    expected_retry_candidate_hash: str | None,
) -> bool:
    """Validate one exact-token no-generation block in generic or retry mode."""

    payload = blocked_event.payload
    schema_version = payload.get("schema_version")
    legacy_retry_block = bool(
        schema_version is None and isinstance(expected_retry_candidate_hash, str)
    )
    if (
        schema_version != _EXACT_REQUEST_GENERATION_BLOCK_SCHEMA
        and not legacy_retry_block
    ):
        return False

    requested = payload.get("requested_input_tokens")
    remaining = payload.get("remaining_tokens")
    preceding_token_usage = 0
    for event in events:
        if (
            event.type != EventType.MODEL_CALLED
            or event.sequence >= blocked_event.sequence
        ):
            continue
        input_tokens = event.payload.get("input_tokens")
        output_tokens = event.payload.get("output_tokens")
        if (
            type(input_tokens) is not int
            or input_tokens < 0
            or type(output_tokens) is not int
            or output_tokens < 0
        ):
            return False
        preceding_token_usage += input_tokens + output_tokens
    expected_remaining = (
        manifest.budget.max_total_tokens - preceding_token_usage
    )
    return bool(
        _generation_block_common_valid(
            root=root,
            manifest=manifest,
            events=events,
            context_event=context_event,
            blocked_event=blocked_event,
            expected_retry_candidate_hash=expected_retry_candidate_hash,
        )
        and payload.get("reason_code") == "exact_request_budget_exceeded"
        and type(requested) is int
        and requested >= 0
        and type(remaining) is int
        and remaining >= 0
        and remaining == expected_remaining
        and requested + manifest.model.max_output_tokens > remaining
        and payload.get("input_token_count_calls") == 1
    )


def _budget_usage_before(events, sequence: int) -> dict[str, int] | None:
    """Recompute the runner's durable budget counters before one event."""

    usage = {
        "model_calls": 0,
        "tool_calls": 0,
        "wall_clock_ms": 0,
        "total_tokens": 0,
    }
    for event in events:
        if event.sequence >= sequence:
            continue
        if event.type == EventType.MODEL_CALLED:
            input_tokens = event.payload.get("input_tokens")
            output_tokens = event.payload.get("output_tokens")
            duration_ms = event.payload.get("duration_ms")
            if (
                type(input_tokens) is not int
                or input_tokens < 0
                or type(output_tokens) is not int
                or output_tokens < 0
                or type(duration_ms) is not int
                or duration_ms < 0
            ):
                return None
            usage["model_calls"] += 1
            usage["total_tokens"] += input_tokens + output_tokens
            usage["wall_clock_ms"] += duration_ms
        elif event.type == EventType.TOOL_CALLED:
            usage["tool_calls"] += 1
        elif event.type in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}:
            duration_ms = event.payload.get("duration_ms")
            if type(duration_ms) is not int or duration_ms < 0:
                return None
            usage["wall_clock_ms"] += duration_ms
    return usage


def _counter_generation_block_valid(
    *,
    root: Path,
    manifest: RunManifest,
    events,
    context_event,
    blocked_event,
    expected_retry_candidate_hash: str | None,
) -> bool:
    """Validate a v2 call/tool/wall pre-generation budget block."""

    payload = blocked_event.payload
    reason_code = payload.get("reason_code")
    usage = _budget_usage_before(events, blocked_event.sequence)
    if (
        payload.get("schema_version") != _COUNTER_GENERATION_BLOCK_SCHEMA
        or reason_code not in _COUNTER_GENERATION_BLOCK_REASONS
        or blocked_event.actor != "budget-guard"
        or usage is None
    ):
        return False
    expected_fields = {
        "schema_version",
        "reason_code",
        "error_code",
        "generation_started",
        "request_artifact_id",
        "request_artifact_path",
        "request_body_hash",
        "requested_input_tokens",
        "remaining_tokens",
        "max_output_tokens",
        "input_token_count_calls",
        "retry_context_present",
        "retry_candidate_content_hash",
        "model_calls_used",
        "max_model_calls",
        "tool_calls_used",
        "max_tool_calls",
        "wall_clock_ms",
        "wall_clock_timeout_ms",
        "total_tokens_used",
        "max_total_tokens",
    }
    if set(payload) != expected_fields:
        return False
    integer_fields = {
        "input_token_count_calls",
        "model_calls_used",
        "max_model_calls",
        "tool_calls_used",
        "max_tool_calls",
        "wall_clock_ms",
        "wall_clock_timeout_ms",
        "total_tokens_used",
        "max_total_tokens",
    }
    if any(
        type(payload.get(field)) is not int or payload[field] < 0
        for field in integer_fields
    ):
        return False

    model_calls = usage["model_calls"]
    tool_calls = usage["tool_calls"]
    wall_clock_ms = usage["wall_clock_ms"]
    model_limit = manifest.budget.max_model_calls
    tool_limit = manifest.budget.max_tool_calls
    wall_limit_ms = manifest.budget.wall_clock_timeout_seconds * 1000
    if reason_code == "model_call_budget_exhausted":
        reason_valid = model_calls == model_limit
    elif reason_code == "tool_call_budget_exhausted":
        reason_valid = model_calls < model_limit and tool_calls == tool_limit
    else:
        reason_valid = bool(
            model_calls < model_limit
            and tool_calls < tool_limit
            and wall_clock_ms >= wall_limit_ms
        )

    return bool(
        _generation_block_common_valid(
            root=root,
            manifest=manifest,
            events=events,
            context_event=context_event,
            blocked_event=blocked_event,
            expected_retry_candidate_hash=expected_retry_candidate_hash,
        )
        and reason_valid
        and model_calls <= model_limit
        and tool_calls <= tool_limit
        and payload.get("requested_input_tokens") is None
        and payload.get("remaining_tokens") is None
        and payload.get("input_token_count_calls") == 0
        and payload.get("model_calls_used") == model_calls
        and payload.get("max_model_calls") == model_limit
        and payload.get("tool_calls_used") == tool_calls
        and payload.get("max_tool_calls") == tool_limit
        and payload.get("wall_clock_ms") == wall_clock_ms
        and payload.get("wall_clock_timeout_ms") == wall_limit_ms
        and payload.get("total_tokens_used") == usage["total_tokens"]
        and payload.get("max_total_tokens")
        == manifest.budget.max_total_tokens
        and usage["total_tokens"] <= manifest.budget.max_total_tokens
    )


def _model_generation_block_valid(
    *,
    root: Path,
    manifest: RunManifest,
    events,
    context_event,
    blocked_event,
    expected_retry_candidate_hash: str | None,
) -> bool:
    """Dispatch validation without reinterpreting historical unversioned blocks."""

    if (
        blocked_event.payload.get("schema_version")
        == _COUNTER_GENERATION_BLOCK_SCHEMA
    ):
        return _counter_generation_block_valid(
            root=root,
            manifest=manifest,
            events=events,
            context_event=context_event,
            blocked_event=blocked_event,
            expected_retry_candidate_hash=expected_retry_candidate_hash,
        )
    return _exact_request_generation_block_valid(
        root=root,
        manifest=manifest,
        events=events,
        context_event=context_event,
        blocked_event=blocked_event,
        expected_retry_candidate_hash=expected_retry_candidate_hash,
    )


def _rejected_patch_retry_context_evidence(
    *,
    root: Path,
    manifest: RunManifest,
    events,
) -> tuple[bool, dict[str, Any]]:
    """Prove every v3 rejected patch episode is rehydrated in its next request."""

    if manifest.context_policy_version == "phase-evidence-v7":
        return _v7_rejected_patch_retry_context_evidence(
            root=root,
            manifest=manifest,
            events=events,
        )
    if manifest.context_policy_version in {
        "phase-evidence-v8",
        "phase-evidence-v9",
        "phase-evidence-v10",
        "phase-evidence-v11",
    }:
        return _v7_rejected_patch_retry_context_evidence(
            root=root,
            manifest=manifest,
            events=events,
        )

    failures = [
        event
        for event in events
        if event.type == EventType.TOOL_FAILED
        and event.actor == "tool-gateway"
        and event.payload.get("tool") == "apply_patch"
        and event.payload.get("status") == "rejected"
    ]
    contexts = [event for event in events if event.type == EventType.CONTEXT_BUILT]
    model_events = [event for event in events if event.type == EventType.MODEL_CALLED]
    blocked_events = [event for event in events if event.type == EventType.MODEL_GENERATION_BLOCKED]
    failures_by_context: dict[str, list[Any]] = {}
    missing_context_sequences: list[int] = []
    context_by_id: dict[str, Any] = {}
    for failure in failures:
        next_context = next(
            (context for context in contexts if context.sequence > failure.sequence),
            None,
        )
        if next_context is None:
            missing_context_sequences.append(failure.sequence)
            continue
        context_by_id[next_context.event_id] = next_context
        failures_by_context.setdefault(next_context.event_id, []).append(failure)

    failed_sequences = list(missing_context_sequences)
    verified_sequences: list[int] = []
    verified_candidate_hashes: list[str] = []
    blocked_sequences: list[int] = []
    artifact_root = (root / "artifacts").resolve()

    for context_id, grouped_failures in sorted(
        failures_by_context.items(),
        key=lambda item: context_by_id[item[0]].sequence,
    ):
        context_event = context_by_id[context_id]
        failure = max(grouped_failures, key=lambda event: event.sequence)
        action_id = failure.correlation_id
        calls = [
            event
            for event in events
            if event.type == EventType.TOOL_CALLED
            and event.actor == "agent"
            and event.payload.get("tool") == "apply_patch"
            and event.correlation_id == action_id
            and event.sequence < failure.sequence
        ]
        call = calls[0] if len(calls) == 1 else None
        episode_ok = bool(isinstance(action_id, str) and action_id and call is not None)
        patch = None
        patch_hash = None
        patch_size = None
        input_hash = None
        if call is not None:
            candidate_ok, candidate_evidence, candidate_bytes = _nested_cas_artifact_evidence(
                artifact_root=artifact_root,
                event_id=call.event_id,
                role="rejected-patch-candidate",
                raw_artifact=call.payload.get("patch_artifact"),
            )
            episode_ok = bool(
                episode_ok
                and candidate_ok
                and call.payload.get("artifact_id") == candidate_evidence.get("artifact_id")
                and call.payload.get("artifact_path") == candidate_evidence.get("declared_path")
            )
            if candidate_bytes is not None:
                try:
                    patch = candidate_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    episode_ok = False
                patch_hash = candidate_evidence.get("actual_content_hash")
                patch_size = candidate_evidence.get("actual_size_bytes")
            input_hash = call.payload.get("input_hash")
            if isinstance(patch, str):
                episode_ok = bool(
                    episode_ok
                    and isinstance(input_hash, str)
                    and input_hash
                    == sha256_text(
                        canonical_json(
                            {
                                "tool": "apply_patch",
                                "input": {"patch": patch},
                            }
                        )
                    )
                )

        rejection = None
        result_ok, result_evidence, result_bytes = _nested_cas_artifact_evidence(
            artifact_root=artifact_root,
            event_id=failure.event_id,
            role="rejected-patch-result",
            raw_artifact=failure.payload.get("result_artifact"),
        )
        episode_ok = bool(
            episode_ok
            and result_ok
            and failure.payload.get("artifact_id") == result_evidence.get("artifact_id")
            and failure.payload.get("artifact_path") == result_evidence.get("declared_path")
        )
        if result_bytes is not None:
            try:
                result_payload = json.loads(result_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                result_payload = None
            if isinstance(result_payload, dict):
                rejection = {
                    "status": result_payload.get("status"),
                    "error_code": result_payload.get("error_code"),
                    "error_message": result_payload.get("error_message"),
                    "error_details": result_payload.get("error_details"),
                }
                event_message = failure.payload.get("error_message")
                episode_ok = bool(
                    episode_ok
                    and result_payload.get("tool") == "apply_patch"
                    and rejection["status"] == "rejected"
                    and isinstance(rejection["error_code"], str)
                    and isinstance(rejection["error_message"], str)
                    and isinstance(rejection["error_details"], dict)
                    and failure.payload.get("status") == rejection["status"]
                    and failure.payload.get("error_code") == rejection["error_code"]
                    and failure.payload.get("error_details") == rejection["error_details"]
                    and isinstance(event_message, str)
                    and rejection["error_message"].startswith(event_message)
                )
            else:
                episode_ok = False

        request_valid, request_evidence = _request_evidence_payload(
            context_event,
            artifact_root=artifact_root,
            expected_provider=(
                manifest.model.provider
                if manifest.context_policy_version
                in {
                    "phase-evidence-v4",
                    "phase-evidence-v5",
                    "phase-evidence-v6",
                    "phase-evidence-v7",
                    "phase-evidence-v8",
                    "phase-evidence-v9",
                    "phase-evidence-v10",
                    "phase-evidence-v11",
                }
                else None
            ),
        )
        rendered_payload = None
        if request_valid and request_evidence is not None:
            rendered_context = _request_context(
                request_evidence["request_body"],
                allow_direct_context=(
                    request_evidence.get("provider")
                    in {"mock", "replay"}
                ),
            )
            try:
                rendered_payload = json.loads(str(rendered_context))
            except (TypeError, ValueError, json.JSONDecodeError):
                rendered_payload = None
        expected_retry = {
            "schema_version": "rejected-mutation-retry-v1",
            "tool": "apply_patch",
            "action_id": action_id,
            "source_call_sequence": call.sequence if call is not None else None,
            "source_failure_sequence": failure.sequence,
            "candidate": {
                "patch": patch,
                "content_hash": patch_hash,
                "size_bytes": patch_size,
                "input_hash": input_hash,
            },
            "rejection": rejection,
        }
        episode_ok = bool(
            episode_ok
            and request_valid
            and isinstance(rendered_payload, dict)
            and rendered_payload.get("rejected_mutation_retry") == expected_retry
        )

        next_context_sequence = min(
            (
                candidate.sequence
                for candidate in contexts
                if candidate.sequence > context_event.sequence
            ),
            default=None,
        )
        consumers = [
            event
            for event in [*model_events, *blocked_events]
            if event.sequence > context_event.sequence
            and (next_context_sequence is None or event.sequence < next_context_sequence)
        ]
        consumers.sort(key=lambda event: event.sequence)
        consumer = consumers[0] if len(consumers) == 1 else None
        if consumer is None:
            episode_ok = False
        elif consumer.type == EventType.MODEL_CALLED:
            episode_ok = bool(
                episode_ok
                and consumer.payload.get("request_artifact_id")
                == context_event.payload.get("artifact_id")
                and consumer.payload.get("request_artifact_path")
                == context_event.payload.get("artifact_path")
                and consumer.payload.get("request_body_hash")
                == context_event.payload.get("request_body_hash")
            )
            next_failure_sequence = min(
                (
                    candidate.sequence
                    for candidate in failures
                    if candidate.sequence > consumer.sequence
                ),
                default=None,
            )
            later_contexts = [
                candidate
                for candidate in contexts
                if candidate.sequence > consumer.sequence
                and (next_failure_sequence is None or candidate.sequence < next_failure_sequence)
            ]
            for later_context in later_contexts:
                later_valid, later_request = _request_evidence_payload(
                    later_context,
                    artifact_root=artifact_root,
                    expected_provider=(
                        manifest.model.provider
                        if manifest.context_policy_version
                        in {
                            "phase-evidence-v4",
                            "phase-evidence-v5",
                            "phase-evidence-v6",
                            "phase-evidence-v7",
                            "phase-evidence-v8",
                            "phase-evidence-v9",
                            "phase-evidence-v10",
                            "phase-evidence-v11",
                        }
                        else None
                    ),
                )
                later_payload = None
                if later_valid and later_request is not None:
                    later_rendered = _request_context(
                        later_request["request_body"],
                        allow_direct_context=(
                            later_request.get("provider")
                            in {"mock", "replay"}
                        ),
                    )
                    try:
                        later_payload = json.loads(str(later_rendered))
                    except (
                        TypeError,
                        ValueError,
                        json.JSONDecodeError,
                    ):
                        later_payload = None
                episode_ok = bool(
                    episode_ok
                    and isinstance(later_payload, dict)
                    and "rejected_mutation_retry" in later_payload
                    and later_payload["rejected_mutation_retry"] is None
                )
        else:
            blocked_ok = bool(
                isinstance(patch_hash, str)
                and _model_generation_block_valid(
                    root=root,
                    manifest=manifest,
                    events=events,
                    context_event=context_event,
                    blocked_event=consumer,
                    expected_retry_candidate_hash=patch_hash,
                )
            )
            episode_ok = episode_ok and blocked_ok
            episode_ok = bool(
                episode_ok
                and not any(candidate.sequence > consumer.sequence for candidate in contexts)
            )
            if blocked_ok:
                blocked_sequences.append(consumer.sequence)

        if episode_ok and isinstance(patch_hash, str):
            verified_sequences.append(failure.sequence)
            verified_candidate_hashes.append(patch_hash)
        else:
            failed_sequences.append(failure.sequence)

    passed = not failed_sequences and len(verified_sequences) == len(failures_by_context)
    return passed, {
        "rejected_candidate_count": len(failures),
        "retry_episode_count": len(failures_by_context),
        "verified_retry_count": len(verified_sequences),
        "model_generation_blocked_count": len(blocked_sequences),
        "verified_source_failure_sequences": sorted(verified_sequences),
        "failed_source_failure_sequences": sorted(set(failed_sequences)),
        "verified_candidate_content_hashes": sorted(verified_candidate_hashes),
    }


def _v7_rejected_patch_retry_context_evidence(
    *,
    root: Path,
    manifest: RunManifest,
    events,
) -> tuple[bool, dict[str, Any]]:
    """Prove v7 retry context persists until the next apply outcome."""

    failures = [
        event
        for event in events
        if event.type == EventType.TOOL_FAILED
        and event.actor == "tool-gateway"
        and event.payload.get("tool") == "apply_patch"
        and event.payload.get("status") == "rejected"
    ]
    apply_outcomes = [
        event
        for event in events
        if event.type in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}
        and event.payload.get("tool") == "apply_patch"
    ]
    contexts = [
        event for event in events if event.type == EventType.CONTEXT_BUILT
    ]
    artifact_root = (root / "artifacts").resolve()
    failed_sequences: list[int] = []
    verified_sequences: list[int] = []
    verified_hashes: list[str] = []
    persisted_context_counts: dict[str, int] = {}

    def rendered_retry(context_event) -> tuple[bool, dict[str, Any] | None]:
        request_valid, request_evidence = _request_evidence_payload(
            context_event,
            artifact_root=artifact_root,
            expected_provider=manifest.model.provider,
        )
        if not request_valid or request_evidence is None:
            return False, None
        request_body = request_evidence.get("request_body")
        rendered = _request_context(
            request_body,
            allow_direct_context=(manifest.model.provider in {"mock", "replay"}),
        )
        try:
            payload = json.loads(str(rendered))
        except (TypeError, ValueError, json.JSONDecodeError):
            return False, None
        context_build = request_evidence.get("context_build")
        return bool(
            isinstance(payload, dict)
            and isinstance(context_build, dict)
            and _request_runtime_contract_valid(request_body, manifest)
            and context_build.get("rejected_mutation_retry") is not None
        ), payload.get("rejected_mutation_retry")

    for failure in failures:
        action_id = failure.correlation_id
        calls = [
            event
            for event in events
            if event.type == EventType.TOOL_CALLED
            and event.payload.get("tool") == "apply_patch"
            and event.correlation_id == action_id
            and event.sequence < failure.sequence
        ]
        call = calls[0] if len(calls) == 1 else None
        patch_artifact = (
            call.payload.get("patch_artifact")
            if call is not None
            else None
        )
        candidate_hash = (
            patch_artifact.get("content_hash")
            if isinstance(patch_artifact, dict)
            else None
        )
        resolution = next(
            (
                event
                for event in apply_outcomes
                if event.sequence > failure.sequence
            ),
            None,
        )
        interval_contexts = [
            context
            for context in contexts
            if context.sequence > failure.sequence
            and (
                resolution is None
                or context.sequence < resolution.sequence
            )
        ]
        episode_ok = bool(
            isinstance(action_id, str)
            and action_id
            and call is not None
            and isinstance(candidate_hash, str)
            and interval_contexts
        )
        for context in interval_contexts:
            valid, retry = rendered_retry(context)
            source_snapshot = (
                retry.get("source_snapshot")
                if isinstance(retry, dict)
                else None
            )
            episode_ok = bool(
                episode_ok
                and valid
                and isinstance(retry, dict)
                and retry.get("schema_version")
                == "rejected-mutation-retry-v2"
                and retry.get("action_id") == action_id
                and retry.get("source_call_sequence") == call.sequence
                and retry.get("source_failure_sequence")
                == failure.sequence
                and retry.get("candidate", {}).get("content_hash")
                == candidate_hash
                and retry.get("persistence")
                == {
                    "state": "pending",
                    "resolution": "next_apply_patch_outcome",
                }
                and isinstance(source_snapshot, dict)
                and source_snapshot.get("schema_version")
                == "patch-source-snapshot-v1"
                and source_snapshot.get("candidate_content_hash")
                == candidate_hash
            )
        if resolution is not None and resolution.type == EventType.TOOL_SUCCEEDED:
            next_failure = next(
                (
                    event
                    for event in failures
                    if event.sequence > resolution.sequence
                ),
                None,
            )
            cleared_contexts = [
                context
                for context in contexts
                if context.sequence > resolution.sequence
                and (
                    next_failure is None
                    or context.sequence < next_failure.sequence
                )
            ]
            for context in cleared_contexts:
                request_valid, request_evidence = _request_evidence_payload(
                    context,
                    artifact_root=artifact_root,
                    expected_provider=manifest.model.provider,
                )
                rendered = (
                    _request_context(
                        request_evidence.get("request_body"),
                        allow_direct_context=(
                            manifest.model.provider in {"mock", "replay"}
                        ),
                    )
                    if request_valid and request_evidence is not None
                    else None
                )
                try:
                    payload = json.loads(str(rendered))
                except (TypeError, ValueError, json.JSONDecodeError):
                    payload = None
                episode_ok = bool(
                    episode_ok
                    and isinstance(payload, dict)
                    and payload.get("rejected_mutation_retry") is None
                )
        if episode_ok:
            verified_sequences.append(failure.sequence)
            verified_hashes.append(candidate_hash)
            persisted_context_counts[str(failure.sequence)] = len(
                interval_contexts
            )
        else:
            failed_sequences.append(failure.sequence)

    return not failed_sequences, {
        "retry_schema_version": "rejected-mutation-retry-v2",
        "rejected_candidate_count": len(failures),
        "retry_episode_count": len(failures),
        "verified_retry_count": len(verified_sequences),
        "model_generation_blocked_count": sum(
            event.type == EventType.MODEL_GENERATION_BLOCKED
            for event in events
        ),
        "verified_source_failure_sequences": sorted(verified_sequences),
        "failed_source_failure_sequences": sorted(failed_sequences),
        "verified_candidate_content_hashes": sorted(verified_hashes),
        "persisted_context_counts": persisted_context_counts,
    }


def _controlled_rejection_evidence(
    *,
    manifest: RunManifest,
    events,
) -> tuple[bool, dict[str, Any]]:
    """Bind the one diagnostic rejection to a prepared, unmutated patch."""

    failures = [
        event
        for event in events
        if (
            event.type == EventType.TOOL_FAILED
            and event.payload.get("error_code")
            == "CONTROLLED_DIAGNOSTIC_REJECTION"
        )
    ]
    verified_sequences: list[int] = []
    failed_sequences: list[int] = []
    patch_applied_sequences: list[int] = []
    all_prepared = [
        event
        for event in events
        if event.type == EventType.PATCH_PREPARED
    ]

    for index, failure in enumerate(failures):
        action_id = failure.correlation_id
        calls = [
            event
            for event in events
            if (
                event.type == EventType.TOOL_CALLED
                and event.actor == "agent"
                and event.payload.get("tool") == "apply_patch"
                and event.correlation_id == action_id
                and event.sequence < failure.sequence
            )
        ]
        prepared = [
            event
            for event in all_prepared
            if (
                event.correlation_id == action_id
                and event.sequence < failure.sequence
            )
        ]
        applied = [
            event
            for event in events
            if (
                event.type == EventType.PATCH_APPLIED
                and event.correlation_id == action_id
            )
        ]
        patch_applied_sequences.extend(
            event.sequence for event in applied
        )
        call = calls[0] if len(calls) == 1 else None
        intent = prepared[0] if len(prepared) == 1 else None
        details = failure.payload.get("error_details")
        expected_details = None
        if call is not None and intent is not None:
            patch_artifact = call.payload.get("patch_artifact")
            candidate_hash = (
                patch_artifact.get("content_hash")
                if isinstance(patch_artifact, dict)
                else None
            )
            expected_details = {
                "schema_version": "controlled-rejection-v1",
                "stage": "diagnostic",
                "reason": "controlled_rejection",
                "guidance": (
                    "Review the rehydrated candidate and rejection evidence, "
                    "then retry with a new action_id."
                ),
                "fault_type": (
                    "controlled-reject-first-prepared-patch"
                ),
                "trigger": "first-preflight-valid-apply-patch",
                "trigger_after": 1,
                "source_call_sequence": call.sequence,
                "source_prepared_sequence": intent.sequence,
                "candidate_content_hash": candidate_hash,
                "input_hash": call.payload.get("input_hash"),
                "prepared_intent_content_hash": intent.payload.get(
                    "content_hash"
                ),
                "baseline_worktree_diff_hash": intent.payload.get(
                    "baseline_worktree_diff_hash"
                ),
                "expected_worktree_diff_hash": intent.payload.get(
                    "expected_worktree_diff_hash"
                ),
                "observed_worktree_diff_hash": intent.payload.get(
                    "baseline_worktree_diff_hash"
                ),
                "worktree_mutated": False,
            }
        episode_ok = bool(
            index == 0
            and failure.actor == "tool-gateway"
            and failure.payload.get("tool") == "apply_patch"
            and failure.payload.get("status") == "rejected"
            and isinstance(action_id, str)
            and action_id
            and call is not None
            and intent is not None
            and intent.actor == "tool-gateway"
            and intent.payload.get("schema_version")
            == "patch-mutation-intent-v1"
            and call.sequence < intent.sequence < failure.sequence
            and failure.sequence == intent.sequence + 1
            and all_prepared
            and intent.sequence == all_prepared[0].sequence
            and expected_details is not None
            and all(
                isinstance(expected_details.get(field), str)
                and expected_details[field]
                for field in (
                    "candidate_content_hash",
                    "input_hash",
                    "prepared_intent_content_hash",
                    "baseline_worktree_diff_hash",
                    "expected_worktree_diff_hash",
                    "observed_worktree_diff_hash",
                )
            )
            and details == expected_details
            and not applied
        )
        if episode_ok:
            verified_sequences.append(failure.sequence)
        else:
            failed_sequences.append(failure.sequence)

    passed = bool(
        manifest.fault.type
        == "controlled-reject-first-prepared-patch"
        and manifest.fault.trigger_after == 1
        and manifest.experiment is not None
        and manifest.experiment.purpose
        == ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT
        and EventType.FAULT_INJECTED
        not in {event.type for event in events}
        and len(failures) == 1
        and len(verified_sequences) == 1
        and not failed_sequences
        and not patch_applied_sequences
    )
    return passed, {
        "controlled_rejection_count": len(failures),
        "verified_controlled_rejection_count": len(
            verified_sequences
        ),
        "controlled_source_failure_sequences": sorted(
            verified_sequences
        ),
        "failed_controlled_source_failure_sequences": sorted(
            failed_sequences
        ),
        "controlled_patch_applied_sequences": sorted(
            patch_applied_sequences
        ),
    }


def _complete_get_diff_in_request(
    *,
    context_event,
    source_event,
    accepted_diff: str,
    expected_provider: str | None,
    context_policy_version: str | None = None,
    artifact_root: Path | None = None,
) -> tuple[bool, bool]:
    """Validate the request body and prove it contains the full get_diff result."""

    request_valid = False
    complete_source = False
    try:
        request_valid, request_evidence = _request_evidence_payload(
            context_event,
            artifact_root=(
            artifact_root
                if context_policy_version
                in {
                    "phase-evidence-v9",
                    "phase-evidence-v10",
                    "phase-evidence-v11",
                }
                else None
            ),
            expected_provider=expected_provider,
        )
        if not request_valid or request_evidence is None:
            return False, False
        request_body = request_evidence["request_body"]
        rendered_context = _request_context(
            request_body,
            allow_direct_context=(
                request_evidence.get("provider")
                in {"mock", "replay"}
            ),
        )
        if not request_valid or rendered_context is None:
            return request_valid, False

        rendered_payload = json.loads(rendered_context)
        if not isinstance(rendered_payload, dict):
            return request_valid, False
        recent_events = rendered_payload.get("recent_events", [])
        if not isinstance(recent_events, list):
            return request_valid, False
        if context_policy_version in {
            "phase-evidence-v9",
            "phase-evidence-v10",
            "phase-evidence-v11",
        }:
            if artifact_root is None:
                return request_valid, False
            expected_rendered_event, expected_tool_result = (
                _v9_recompute_review_anchor(
                    source_event,
                    artifact_store=ArtifactStore(artifact_root),
                )
            )
            source_artifact = expected_rendered_event["payload"][
                "tool_result"
            ]
            if not isinstance(source_artifact, dict):
                return request_valid, False
            review_evidence = rendered_payload.get("review_evidence")
            context_build = request_evidence.get("context_build")
            build_review_evidence = (
                context_build.get("review_evidence")
                if isinstance(context_build, dict)
                else None
            )
            if (
                not isinstance(review_evidence, dict)
                or not isinstance(context_build, dict)
                or context_build.get("schema_version")
                != (
                    "context-build-evidence-v11"
                    if context_policy_version == "phase-evidence-v11"
                    else (
                        "context-build-evidence-v10"
                        if context_policy_version == "phase-evidence-v10"
                        else "context-build-evidence-v9"
                    )
                )
                or not isinstance(build_review_evidence, dict)
            ):
                return request_valid, False
            pinned_results = review_evidence.get("pinned_results")
            pinned_tool_results = build_review_evidence.get(
                "pinned_tool_results"
            )
            presented_results = context_build.get("tool_results")
            if (
                not isinstance(pinned_results, list)
                or not isinstance(pinned_tool_results, list)
                or not isinstance(presented_results, list)
                or not all(
                    isinstance(item, dict)
                    and type(item.get("sequence")) is int
                    for item in pinned_results
                )
                or not all(
                    isinstance(item, dict)
                    and type(item.get("event_sequence")) is int
                    for item in pinned_tool_results
                )
                or not all(
                    isinstance(item, dict)
                    and type(item.get("event_sequence")) is int
                    for item in presented_results
                )
                or not all(
                    isinstance(item, dict)
                    and type(item.get("sequence")) is int
                    for item in recent_events
                )
            ):
                return request_valid, False

            source_sequence = source_event.sequence
            recent_source = [
                item
                for item in recent_events
                if item.get("sequence") == source_sequence
            ]
            pinned_source = [
                item
                for item in pinned_results
                if item.get("sequence") == source_sequence
            ]
            pinned_tool_source = [
                item
                for item in pinned_tool_results
                if item.get("event_sequence") == source_sequence
            ]
            presented_source = [
                item
                for item in presented_results
                if item.get("event_sequence") == source_sequence
            ]
            citable_sequences = review_evidence.get(
                "citable_event_sequences"
            )
            incomplete_sequences = review_evidence.get(
                "incomplete_event_sequences"
            )
            build_citable_sequences = build_review_evidence.get(
                "citable_event_sequences"
            )
            build_incomplete_sequences = build_review_evidence.get(
                "incomplete_event_sequences"
            )
            complete_source = bool(
                review_evidence.get("schema_version")
                == (
                    "review-evidence-v2"
                    if context_policy_version
                    in {"phase-evidence-v10", "phase-evidence-v11"}
                    else "review-evidence-v1"
                )
                and review_evidence.get("pinning_active") is True
                and review_evidence.get("worktree_diff_hash")
                == accepted_diff
                and type(
                    review_evidence.get("source_get_diff_sequence")
                )
                is int
                and review_evidence["source_get_diff_sequence"]
                == source_sequence
                and isinstance(citable_sequences, list)
                and all(
                    type(sequence) is int
                    for sequence in citable_sequences
                )
                and citable_sequences.count(source_sequence) == 1
                and isinstance(incomplete_sequences, list)
                and all(
                    type(sequence) is int
                    for sequence in incomplete_sequences
                )
                and source_sequence not in incomplete_sequences
                and build_review_evidence.get("schema_version")
                == (
                    "review-evidence-v2"
                    if context_policy_version
                    in {"phase-evidence-v10", "phase-evidence-v11"}
                    else "review-evidence-v1"
                )
                and build_review_evidence.get("pinning_active") is True
                and build_review_evidence.get("worktree_diff_hash")
                == accepted_diff
                and type(
                    build_review_evidence.get(
                        "source_get_diff_sequence"
                    )
                )
                is int
                and build_review_evidence[
                    "source_get_diff_sequence"
                ]
                == source_sequence
                and isinstance(build_citable_sequences, list)
                and all(
                    type(sequence) is int
                    for sequence in build_citable_sequences
                )
                and build_citable_sequences.count(source_sequence)
                == 1
                and isinstance(build_incomplete_sequences, list)
                and all(
                    type(sequence) is int
                    for sequence in build_incomplete_sequences
                )
                and source_sequence
                not in build_incomplete_sequences
                and not recent_source
                and len(pinned_source) == 1
                and canonical_json(pinned_source[0])
                == canonical_json(expected_rendered_event)
                and len(pinned_tool_source) == 1
                and canonical_json(pinned_tool_source[0])
                == canonical_json(expected_tool_result)
                and len(presented_source) == 1
                and canonical_json(presented_source[0])
                == canonical_json(expected_tool_result)
                and expected_tool_result.get("tool") == "get_diff"
                and expected_tool_result.get("worktree_diff_hash")
                == accepted_diff
                and expected_tool_result.get("available") is True
                and expected_tool_result.get("truncated") is False
                and source_artifact.get("patch_hash") == accepted_diff
                and source_artifact.get("worktree_diff_hash")
                == accepted_diff
                and isinstance(source_artifact.get("patch"), str)
                and sha256_text(source_artifact["patch"])
                == accepted_diff
            )
            return request_valid, complete_source
        source_artifact = json.loads(
            Path(str(source_event.payload["artifact_path"])).read_text(encoding="utf-8")
        )
        if not isinstance(source_artifact, dict):
            return request_valid, False
        expected_rendered_event = {
            "sequence": source_event.sequence,
            "type": source_event.type.value,
            "actor": source_event.actor,
            "payload": {
                **source_event.payload,
                "tool_result": source_artifact,
            },
        }
        actual_matches = [item for item in recent_events if item == expected_rendered_event]
        context_build = request_evidence.get("context_build", {})
        presented_results = (
            context_build.get("tool_results", []) if isinstance(context_build, dict) else []
        )
        sidecar_matches = [
            item
            for item in presented_results
            if isinstance(item, dict)
            and item.get("event_sequence") == source_event.sequence
            and item.get("tool") == "get_diff"
            and item.get("worktree_diff_hash") == accepted_diff
            and item.get("artifact_id") == source_event.payload.get("artifact_id")
            and item.get("available") is True
            and item.get("truncated") is False
        ]
        complete_source = bool(
            len(actual_matches) == 1
            and len(sidecar_matches) == 1
            and source_artifact.get("patch_hash") == accepted_diff
            and source_artifact.get("worktree_diff_hash") == accepted_diff
            and isinstance(source_artifact.get("patch"), str)
            and sha256_text(source_artifact["patch"]) == accepted_diff
        )
    except (
        KeyError,
        OSError,
        RecoveryError,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return False, False
    return request_valid, complete_source


def _ordered_submission_evidence(
    *,
    task,
    events,
    accepted_event,
    source_event,
    accepted_diff: str,
) -> tuple[bool, dict[str, Any]]:
    """Reconstruct apply -> current-diff checks -> get_diff for accepted v2 runs."""

    mutations = [
        event
        for event in events
        if event.type == EventType.PATCH_APPLIED and event.sequence < accepted_event.sequence
    ]
    mutation = mutations[-1] if mutations else None
    mutation_ok = bool(
        mutation is not None
        and accepted_diff != _EMPTY_DIFF_HASH
        and mutation.payload.get("worktree_diff_hash") == accepted_diff
    )
    apply_call_ok = False
    patch_intent_ok = False
    if mutation is not None and mutation.correlation_id is not None:
        apply_successes = [
            event
            for event in events
            if event.type == EventType.TOOL_SUCCEEDED
            and event.correlation_id == mutation.correlation_id
            and event.payload.get("tool") == "apply_patch"
            and event.payload.get("worktree_diff_hash") == accepted_diff
            and event.sequence < mutation.sequence
        ]
        apply_calls = [
            event
            for event in events
            if event.type == EventType.TOOL_CALLED
            and event.correlation_id == mutation.correlation_id
            and event.payload.get("tool") == "apply_patch"
            and apply_successes
            and event.sequence < apply_successes[0].sequence
        ]
        prepared_intents = [
            event
            for event in events
            if event.type == EventType.PATCH_PREPARED
            and event.correlation_id == mutation.correlation_id
            and apply_calls
            and apply_successes
            and apply_calls[0].sequence < event.sequence < apply_successes[0].sequence
        ]
        patch_intent_ok = len(prepared_intents) == 1
        apply_call_ok = bool(
            len(apply_successes) == 1 and len(apply_calls) == 1 and patch_intent_ok
        )

    check_sequences: dict[str, int | None] = {}
    checks_ok = mutation is not None
    for check in task.visible_checks:
        candidates = [
            event
            for event in events
            if mutation is not None
            and mutation.sequence < event.sequence < accepted_event.sequence
            and event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") == "run_check"
            and event.payload.get("check_id") == check.id
        ]
        latest = candidates[-1] if candidates else None
        check_sequences[check.id] = latest.sequence if latest is not None else None
        checks_ok = bool(
            checks_ok
            and latest is not None
            and latest.payload.get("passed") is True
            and latest.payload.get("worktree_diff_hash") == accepted_diff
            and source_event is not None
            and latest.sequence < source_event.sequence
        )
    get_diff_events = [
        event
        for event in events
        if mutation is not None
        and mutation.sequence < event.sequence < accepted_event.sequence
        and event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "get_diff"
        and event.payload.get("worktree_diff_hash") == accepted_diff
    ]
    source_calls = [
        event
        for event in events
        if source_event is not None
        and event.type == EventType.TOOL_CALLED
        and event.correlation_id == source_event.correlation_id
        and event.payload.get("tool") == "get_diff"
        and event.sequence < source_event.sequence
    ]
    source_order_ok = bool(
        mutation is not None
        and source_event is not None
        and mutation.sequence < source_event.sequence < accepted_event.sequence
        and get_diff_events
        and get_diff_events[-1].event_id == source_event.event_id
        and len(source_calls) == 1
    )
    ordered = mutation_ok and apply_call_ok and checks_ok and source_order_ok
    return ordered, {
        "mutation_sequence": mutation.sequence if mutation is not None else None,
        "mutation_valid": mutation_ok,
        "apply_call_valid": apply_call_ok,
        "patch_intent_valid": patch_intent_ok,
        "visible_checks_valid": checks_ok,
        "visible_check_sequences": check_sequences,
        "latest_get_diff_valid": bool(
            get_diff_events
            and source_event is not None
            and get_diff_events[-1].event_id == source_event.event_id
        ),
        "get_diff_call_valid": len(source_calls) == 1,
        "source_order_valid": source_order_ok,
    }


def _self_validation_lifecycle_evidence(
    *,
    root: Path,
    manifest: RunManifest,
    package: TaskPackage,
    events: list[Any],
    result: RunResult | None,
) -> tuple[bool, dict[str, Any]]:
    """Independently bind versioned probes and semantic review evidence."""

    artifact_root = (root / "artifacts").resolve()
    review_v2 = manifest.tool_schema_version == "v4"
    coverage_v10 = bool(
        (
            manifest.tool_schema_version == "v5"
            and manifest.context_policy_version == "phase-evidence-v10"
        )
        or (
            manifest.tool_schema_version == "v6"
            and manifest.context_policy_version == "phase-evidence-v11"
        )
    )
    review_v9 = manifest.context_policy_version == "phase-evidence-v9"
    review_contract = manifest.public_review_contract
    authoritative_requirements = {
        item.requirement_id: item.source_excerpt
        for item in (
            review_contract.requirements
            if review_contract is not None
            else []
        )
    }
    events_by_sequence = {event.sequence: event for event in events}
    special_tools = (
        {"run_probe"}
        if coverage_v10
        else {"run_probe", "review_task"}
    )
    calls = [
        event
        for event in events
        if event.type == EventType.TOOL_CALLED
        and event.payload.get("tool") in special_tools
    ]
    outcomes = [
        event
        for event in events
        if event.type in {
            EventType.TOOL_SUCCEEDED,
            EventType.TOOL_FAILED,
        }
        and event.payload.get("tool") in special_tools
    ]
    failed_call_sequences: list[int] = []
    verified_probe_sequences: list[int] = []
    verified_review_sequences: list[int] = []
    review_artifacts: dict[int, dict[str, Any]] = {}
    probe_profiles = {
        profile.id: profile
        for profile in package.public.probe_profiles
    }
    probe_observed = any(
        event.payload.get("tool") == "run_probe"
        for event in [*calls, *outcomes]
    )
    probe_manifest_binding_valid = bool(
        not probe_observed
        or (
            manifest.tool_schema_version in {"v3", "v4", "v5", "v6"}
            and isinstance(manifest.probe_image_digest, str)
            and manifest.probe_image_digest
        )
    )

    def nested_json(
        event,
        *,
        role: str,
        descriptor: Any,
    ) -> tuple[bool, dict[str, Any] | None, dict[str, Any]]:
        valid, item, content = _nested_cas_artifact_evidence(
            artifact_root=artifact_root,
            event_id=event.event_id,
            role=role,
            raw_artifact=descriptor,
        )
        payload = None
        if content is not None:
            try:
                parsed = json.loads(content.decode("utf-8"))
                if isinstance(parsed, dict):
                    payload = parsed
                else:
                    valid = False
            except (UnicodeDecodeError, json.JSONDecodeError):
                valid = False
        return valid, payload, item

    def complete_presented_sequences(
        presented: Any,
    ) -> set[int]:
        if not isinstance(presented, list):
            return set()
        return {
            int(item["event_sequence"])
            for item in presented
            if (
                isinstance(item, dict)
                and type(item.get("event_sequence")) is int
                and item.get("available") is True
                and item.get("truncated") is False
            )
        }

    def v9_failed_review_input_shape_valid(arguments: Any) -> bool:
        """Require citation failures to follow a structurally valid review."""

        if not isinstance(arguments, dict) or set(arguments) != {
            "requirements",
            "targeted_validation",
            "residual_risks",
        }:
            return False
        requirements = arguments["requirements"]
        targeted = arguments["targeted_validation"]
        residual_risks = arguments["residual_risks"]
        if (
            not isinstance(requirements, list)
            or not 1 <= len(requirements) <= 20
            or not isinstance(targeted, list)
            or not 1 <= len(targeted) <= 20
            or not isinstance(residual_risks, list)
            or len(residual_risks) > 20
        ):
            return False
        observed_requirement_ids: list[str] = []
        for item in requirements:
            if not isinstance(item, dict) or set(item) != {
                "requirement_id",
                "status",
                "evidence_event_sequences",
                "notes",
            }:
                return False
            requirement_id = item.get("requirement_id")
            sequences = item.get("evidence_event_sequences")
            notes = item.get("notes")
            if (
                not isinstance(requirement_id, str)
                or requirement_id not in authoritative_requirements
                or requirement_id in observed_requirement_ids
                or item.get("status")
                not in {
                    "verified",
                    "partially_verified",
                    "unverified",
                }
                or not isinstance(sequences, list)
                or len(sequences) > 20
                or any(type(sequence) is not int for sequence in sequences)
                or len(sequences) != len(set(sequences))
                or (
                    item.get("status") != "unverified"
                    and not sequences
                )
                or not isinstance(notes, str)
                or not notes.strip()
                or len(notes) > 2000
            ):
                return False
            observed_requirement_ids.append(requirement_id)
        if set(observed_requirement_ids) != set(authoritative_requirements):
            return False
        seen_targeted_sequences: set[int] = set()
        for item in targeted:
            if not isinstance(item, dict) or set(item) != {
                "kind",
                "event_sequence",
                "outcome",
                "notes",
            }:
                return False
            sequence = item.get("event_sequence")
            notes = item.get("notes")
            if (
                item.get("kind")
                not in {
                    "probe",
                    "registered_check",
                    "repository_evidence",
                }
                or type(sequence) is not int
                or sequence in seen_targeted_sequences
                or item.get("outcome")
                not in {"passed", "failed", "inconclusive"}
                or not isinstance(notes, str)
                or not notes.strip()
                or len(notes) > 2000
            ):
                return False
            seen_targeted_sequences.add(sequence)
        return all(
            isinstance(item, dict)
            and set(item) == {"requirement_ids", "risk", "mitigation"}
            and isinstance(item.get("requirement_ids"), list)
            and bool(item["requirement_ids"])
            and len(item["requirement_ids"]) <= 20
            and all(
                isinstance(requirement_id, str)
                for requirement_id in item["requirement_ids"]
            )
            and len(item["requirement_ids"])
            == len(set(item["requirement_ids"]))
            and all(
                requirement_id in authoritative_requirements
                for requirement_id in item["requirement_ids"]
            )
            and isinstance(item.get("risk"), str)
            and bool(item["risk"].strip())
            and len(item["risk"]) <= 1000
            and isinstance(item.get("mitigation"), str)
            and bool(item["mitigation"].strip())
            and len(item["mitigation"]) <= 1000
            for item in residual_risks
        )

    for call in calls:
        tool = str(call.payload.get("tool"))
        action_id = call.correlation_id
        matching_outcomes = [
            event
            for event in outcomes
            if event.correlation_id == action_id
            and event.payload.get("tool") == tool
            and event.sequence > call.sequence
        ]
        outcome = (
            matching_outcomes[0]
            if len(matching_outcomes) == 1
            else None
        )
        call_ok = bool(
            call.actor == "agent"
            and isinstance(action_id, str)
            and action_id
            and outcome is not None
        )
        input_valid, input_payload, input_item = nested_json(
            call,
            role=f"{tool}-input",
            descriptor=call.payload.get("input_artifact"),
        )
        arguments = (
            input_payload.get("input")
            if isinstance(input_payload, dict)
            else None
        )
        expected_input_keys = (
            {"tool", "input", "execution_context"}
            if tool == "review_task"
            else {"tool", "input"}
        )
        input_hash = (
            sha256_text(
                canonical_json({"tool": tool, "input": arguments})
            )
            if isinstance(arguments, dict)
            else None
        )
        worktree_diff_hash = call.payload.get(
            "worktree_diff_hash"
        )
        normalized_call_hash = (
            sha256_text(
                canonical_json(
                    {
                        "tool": tool,
                        "input": arguments,
                        "worktree_diff_hash": worktree_diff_hash,
                        "state_marker": None,
                    }
                )
            )
            if (
                isinstance(arguments, dict)
                and isinstance(worktree_diff_hash, str)
            )
            else None
        )
        call_ok = bool(
            call_ok
            and input_valid
            and isinstance(input_payload, dict)
            and set(input_payload) == expected_input_keys
            and input_payload.get("tool") == tool
            and isinstance(arguments, dict)
            and call.payload.get("artifact_id")
            == input_item.get("artifact_id")
            and call.payload.get("artifact_path")
            == input_item.get("declared_path")
            and call.payload.get("input_hash") == input_hash
            and call.payload.get("normalized_call_hash")
            == normalized_call_hash
        )
        probe_source_valid = True
        probe_source_item: dict[str, Any] = {}
        probe_source_bytes: bytes | None = None
        probe_profile = None
        if tool == "run_probe":
            source = arguments.get("source")
            probe_id = arguments.get("probe_id")
            probe_profile = (
                probe_profiles.get(probe_id)
                if isinstance(probe_id, str)
                else None
            )
            if isinstance(source, str):
                (
                    probe_source_valid,
                    probe_source_item,
                    probe_source_bytes,
                ) = _nested_cas_artifact_evidence(
                    artifact_root=artifact_root,
                    event_id=call.event_id,
                    role="probe-source",
                    raw_artifact=call.payload.get(
                        "source_artifact"
                    ),
                )
                probe_source_valid = bool(
                    probe_source_valid
                    and probe_source_bytes
                    == source.encode("utf-8")
                    and call.payload.get("source_hash")
                    == probe_source_item.get(
                        "actual_content_hash"
                    )
                    and call.payload.get("probe_id")
                    == probe_id
                    and call.payload.get(
                        "probe_policy_version"
                    )
                    == "ephemeral-python-probe-v2"
                )
            else:
                probe_source_valid = bool(
                    call.payload.get("source_artifact") is None
                    and call.payload.get("source_hash") is None
                    and call.payload.get("probe_id") is None
                    and call.payload.get(
                        "probe_policy_version"
                    )
                    is None
                )
            call_ok = bool(
                call_ok and probe_source_valid
            )
        result_valid, result_payload, result_item = nested_json(
            outcome if outcome is not None else call,
            role=f"{tool}-result",
            descriptor=(
                outcome.payload.get("result_artifact")
                if outcome is not None
                else None
            ),
        )
        call_ok = bool(
            call_ok
            and outcome is not None
            and result_valid
            and isinstance(result_payload, dict)
            and outcome.payload.get("artifact_id")
            == result_item.get("artifact_id")
            and outcome.payload.get("artifact_path")
            == result_item.get("declared_path")
        )
        if not call_ok or outcome is None or input_payload is None:
            failed_call_sequences.append(call.sequence)
            continue
        if outcome.type == EventType.TOOL_FAILED:
            v9_failed_review_ok = True
            if review_v9 and tool == "review_task":
                execution_context = input_payload.get(
                    "execution_context"
                )
                request_artifact_id = (
                    execution_context.get("request_artifact_id")
                    if isinstance(execution_context, dict)
                    else None
                )
                matching_contexts = [
                    event
                    for event in events
                    if event.type == EventType.CONTEXT_BUILT
                    and event.payload.get("artifact_id")
                    == request_artifact_id
                    and event.sequence < call.sequence
                ]
                context_event = (
                    matching_contexts[0]
                    if len(matching_contexts) == 1
                    else None
                )
                request_valid = False
                request_evidence = None
                if context_event is not None:
                    request_valid, request_evidence = (
                        _request_evidence_payload(
                            context_event,
                            artifact_root=artifact_root,
                            expected_provider=manifest.model.provider,
                        )
                    )
                context_build = (
                    request_evidence.get("context_build")
                    if isinstance(request_evidence, dict)
                    else None
                )
                request_review_evidence = (
                    context_build.get("review_evidence")
                    if isinstance(context_build, dict)
                    else None
                )
                presented = (
                    execution_context.get("presented_tool_results")
                    if isinstance(execution_context, dict)
                    else None
                )
                matching_model_calls = [
                    event
                    for event in events
                    if event.type == EventType.MODEL_CALLED
                    and event.payload.get("request_artifact_id")
                    == request_artifact_id
                    and context_event is not None
                    and context_event.sequence
                    < event.sequence
                    < call.sequence
                ]
                request_binding_ok = bool(
                    isinstance(execution_context, dict)
                    and set(execution_context)
                    == {
                        "request_artifact_id",
                        "phase",
                        "presented_tool_results",
                        "review_evidence",
                    }
                    and execution_context.get("phase") == "REVIEW"
                    and isinstance(request_artifact_id, str)
                    and call.payload.get("request_artifact_id")
                    == request_artifact_id
                    and call.payload.get("request_phase") == "REVIEW"
                    and request_valid
                    and isinstance(context_build, dict)
                    and context_build.get("tool_results") == presented
                    and isinstance(request_review_evidence, dict)
                    and execution_context.get("review_evidence")
                    == request_review_evidence
                    and _request_runtime_contract_valid(
                        request_evidence.get("request_body"),
                        manifest,
                    )
                    and len(matching_model_calls) == 1
                )
                rejection_details = result_payload.get("error_details")
                expected_citable = (
                    request_review_evidence.get(
                        "citable_event_sequences"
                    )
                    if isinstance(request_review_evidence, dict)
                    else None
                )
                expected_passing = (
                    request_review_evidence.get(
                        "passing_check_event_sequences"
                    )
                    if isinstance(request_review_evidence, dict)
                    else None
                )
                expected_diff = (
                    request_review_evidence.get(
                        "source_get_diff_sequence"
                    )
                    if isinstance(request_review_evidence, dict)
                    else None
                )
                expected_mutation = (
                    request_review_evidence.get(
                        "mutation_event_sequence"
                    )
                    if isinstance(request_review_evidence, dict)
                    else None
                )
                current_diff_hash = call.payload.get(
                    "worktree_diff_hash"
                )
                mutation_event = (
                    events_by_sequence.get(expected_mutation)
                    if type(expected_mutation) is int
                    else None
                )
                diff_event = (
                    events_by_sequence.get(expected_diff)
                    if type(expected_diff) is int
                    else None
                )
                epoch_binding_ok = bool(
                    isinstance(current_diff_hash, str)
                    and isinstance(request_review_evidence, dict)
                    and request_review_evidence.get("pinning_active")
                    is True
                    and request_review_evidence.get(
                        "worktree_diff_hash"
                    )
                    == current_diff_hash
                    and mutation_event is not None
                    and mutation_event.type == EventType.PATCH_APPLIED
                    and mutation_event.payload.get("worktree_diff_hash")
                    == current_diff_hash
                    and diff_event is not None
                    and diff_event.type == EventType.TOOL_SUCCEEDED
                    and diff_event.payload.get("tool") == "get_diff"
                    and diff_event.payload.get("worktree_diff_hash")
                    == current_diff_hash
                    and context_event is not None
                    and mutation_event.sequence < diff_event.sequence
                    < context_event.sequence < call.sequence
                    and not any(
                        event.type == EventType.PATCH_APPLIED
                        and mutation_event.sequence
                        < event.sequence
                        < call.sequence
                        for event in events
                    )
                )
                raw_requirements = (
                    arguments.get("requirements")
                    if isinstance(arguments, dict)
                    else None
                )
                raw_targeted_validation = (
                    arguments.get("targeted_validation")
                    if isinstance(arguments, dict)
                    else None
                )
                citation_sequences: set[int] = set()
                for requirement in (
                    raw_requirements
                    if isinstance(raw_requirements, list)
                    else []
                ):
                    raw_sequences = (
                        requirement.get("evidence_event_sequences")
                        if isinstance(requirement, dict)
                        else None
                    )
                    citation_sequences.update(
                        sequence
                        for sequence in (
                            raw_sequences
                            if isinstance(raw_sequences, list)
                            else []
                        )
                        if type(sequence) is int
                    )
                citation_sequences.update(
                    item["event_sequence"]
                    for item in (
                        raw_targeted_validation
                        if isinstance(raw_targeted_validation, list)
                        else []
                    )
                    if isinstance(item, dict)
                    and type(item.get("event_sequence")) is int
                )
                sequence_failure_reasons = {
                    "invalid_event_sequence",
                    "evidence_precedes_current_mutation",
                    "evidence_event_missing",
                    "evidence_not_tool_succeeded",
                    "evidence_not_current_diff",
                    "evidence_not_presented",
                    "evidence_not_citable",
                }
                reason = (
                    rejection_details.get("reason")
                    if isinstance(rejection_details, dict)
                    else None
                )
                expected_detail_keys = {
                    "schema_version",
                    "stage",
                    "reason",
                    "citable_event_sequences",
                    "passing_validation_event_sequences",
                    "source_get_diff_sequence",
                    *(
                        {"invalid_event_sequence"}
                        if reason in sequence_failure_reasons
                        else set()
                    ),
                }
                rejection_binding_ok = bool(
                    v9_failed_review_input_shape_valid(arguments)
                    and isinstance(rejection_details, dict)
                    and set(rejection_details) == expected_detail_keys
                    and rejection_details.get("schema_version")
                    == "review-citation-error-v1"
                    and rejection_details.get("stage") == "review"
                    and reason
                    in {
                        *sequence_failure_reasons,
                        "targeted_validation_missing",
                    }
                    and rejection_details.get(
                        "citable_event_sequences"
                    )
                    == (
                        sorted(expected_citable)
                        if isinstance(expected_citable, list)
                        and all(
                            type(sequence) is int
                            for sequence in expected_citable
                        )
                        else None
                    )
                    and rejection_details.get(
                        "passing_validation_event_sequences"
                    )
                    == (
                        sorted(expected_passing)
                        if isinstance(expected_passing, list)
                        and all(
                            type(sequence) is int
                            for sequence in expected_passing
                        )
                        else None
                    )
                    and rejection_details.get(
                        "source_get_diff_sequence"
                    )
                    == expected_diff
                    and (
                        reason == "targeted_validation_missing"
                        or rejection_details.get(
                            "invalid_event_sequence"
                        )
                        in citation_sequences
                    )
                )
                v9_failed_review_ok = bool(
                    request_binding_ok
                    and epoch_binding_ok
                    and rejection_binding_ok
                )
            failure_ok = bool(
                result_payload.get("tool") == tool
                and result_payload.get("status")
                == outcome.payload.get("status")
                and outcome.payload.get("status")
                in {"rejected", "failed"}
                and result_payload.get("error_code")
                == outcome.payload.get("error_code")
                and result_payload.get("error_message")
                == outcome.payload.get("error_message")
                and result_payload.get("error_details")
                == outcome.payload.get("error_details")
                and v9_failed_review_ok
            )
            if not failure_ok:
                failed_call_sequences.append(call.sequence)
            continue

        if tool == "run_probe":
            source = arguments.get("source")
            probe_id = arguments.get("probe_id")
            passed = result_payload.get("passed")
            probe_timed_out = result_payload.get("timed_out")
            probe_exit_code = result_payload.get("exit_code")
            expected_execution_policy = (
                probe_execution_policy(
                    image_identity=manifest.probe_image_digest,
                    timeout_seconds=probe_profile.timeout_seconds,
                    output_limit_bytes=probe_profile.output_limit_bytes,
                )
                if (
                    probe_profile is not None
                    and probe_manifest_binding_valid
                    and manifest.probe_image_digest is not None
                )
                else None
            )
            probe_ok = bool(
                probe_manifest_binding_valid
                and probe_source_valid
                and set(arguments) == {"probe_id", "source"}
                and isinstance(source, str)
                and isinstance(probe_id, str)
                and probe_profile is not None
                and result_payload.get("schema_version")
                == "ephemeral-python-probe-result-v2"
                and result_payload.get("probe_policy_version")
                == "ephemeral-python-probe-v2"
                and result_payload.get("authoritative") is False
                and result_payload.get("probe_id")
                == probe_profile.id
                and result_payload.get("probe_runtime")
                == probe_profile.runtime
                and result_payload.get("timeout_seconds")
                == probe_profile.timeout_seconds
                and result_payload.get("output_limit_bytes")
                == probe_profile.output_limit_bytes
                and result_payload.get("source_limit_bytes")
                == probe_profile.source_limit_bytes
                and result_payload.get("source_artifact")
                == call.payload.get("source_artifact")
                == outcome.payload.get("source_artifact")
                and result_payload.get("source_hash")
                == call.payload.get("source_hash")
                == outcome.payload.get("source_hash")
                == probe_source_item.get(
                    "actual_content_hash"
                )
                and result_payload.get("execution_policy")
                == outcome.payload.get("execution_policy")
                == expected_execution_policy
                and result_payload.get("command")
                == ["python", "-I", "<ephemeral-probe>"]
                and result_payload.get("worktree_diff_hash")
                == worktree_diff_hash
                and outcome.payload.get("probe_id")
                == probe_profile.id
                and outcome.payload.get("probe_runtime")
                == probe_profile.runtime
                and outcome.payload.get("timeout_seconds")
                == probe_profile.timeout_seconds
                and outcome.payload.get("output_limit_bytes")
                == probe_profile.output_limit_bytes
                and outcome.payload.get("source_limit_bytes")
                == probe_profile.source_limit_bytes
                and (
                    (
                        type(probe_exit_code) is int
                        and probe_timed_out is False
                    )
                    or (
                        probe_exit_code is None
                        and probe_timed_out is True
                    )
                )
                and passed
                is (
                    not probe_timed_out
                    and probe_exit_code == 0
                )
                and outcome.payload.get("probe_policy_version")
                == result_payload.get("probe_policy_version")
                and outcome.payload.get("worktree_diff_hash")
                == worktree_diff_hash
                and outcome.payload.get("passed") == passed
                and outcome.payload.get("timed_out")
                == probe_timed_out
                and outcome.payload.get("exit_code")
                == probe_exit_code
            )
            if probe_ok:
                verified_probe_sequences.append(outcome.sequence)
            else:
                failed_call_sequences.append(call.sequence)
            continue

        execution_context = input_payload.get(
            "execution_context"
        )
        expected_execution_context_keys = {
            "request_artifact_id",
            "phase",
            "presented_tool_results",
            *({"review_evidence"} if review_v9 else set()),
        }
        request_artifact_id = (
            execution_context.get("request_artifact_id")
            if isinstance(execution_context, dict)
            else None
        )
        presented = (
            execution_context.get("presented_tool_results")
            if isinstance(execution_context, dict)
            else None
        )
        matching_contexts = [
            event
            for event in events
            if event.type == EventType.CONTEXT_BUILT
            and event.payload.get("artifact_id")
            == request_artifact_id
            and event.sequence < call.sequence
        ]
        context_event = (
            matching_contexts[0]
            if len(matching_contexts) == 1
            else None
        )
        request_valid = False
        request_evidence = None
        if context_event is not None:
            request_valid, request_evidence = (
                _request_evidence_payload(
                    context_event,
                    artifact_root=artifact_root,
                    expected_provider=manifest.model.provider,
                )
            )
        matching_model_calls = [
            event
            for event in events
            if event.type == EventType.MODEL_CALLED
            and event.payload.get("request_artifact_id")
            == request_artifact_id
            and context_event is not None
            and context_event.sequence < event.sequence < call.sequence
        ]
        request_context_build = (
            request_evidence.get("context_build")
            if isinstance(request_evidence, dict)
            else None
        )
        request_review_evidence = (
            request_context_build.get("review_evidence")
            if isinstance(request_context_build, dict)
            else None
        )
        execution_review_evidence = (
            execution_context.get("review_evidence")
            if isinstance(execution_context, dict)
            else None
        )
        v9_citable_sequences = (
            request_review_evidence.get("citable_event_sequences")
            if isinstance(request_review_evidence, dict)
            else None
        )
        v9_passing_check_sequences = (
            request_review_evidence.get(
                "passing_check_event_sequences"
            )
            if isinstance(request_review_evidence, dict)
            else None
        )
        v9_source_get_diff_sequence = (
            request_review_evidence.get("source_get_diff_sequence")
            if isinstance(request_review_evidence, dict)
            else None
        )
        v9_citable_sequence_set = {
            sequence
            for sequence in (
                v9_citable_sequences
                if isinstance(v9_citable_sequences, list)
                else []
            )
            if type(sequence) is int
        }
        v9_passing_check_sequence_set = {
            sequence
            for sequence in (
                v9_passing_check_sequences
                if isinstance(v9_passing_check_sequences, list)
                else []
            )
            if type(sequence) is int
        }
        v9_review_context_ok = bool(
            not review_v9
            or (
                isinstance(request_review_evidence, dict)
                and execution_review_evidence
                == request_review_evidence
                and isinstance(v9_citable_sequences, list)
                and all(
                    type(sequence) is int
                    for sequence in v9_citable_sequences
                )
                and len(v9_citable_sequences)
                == len(set(v9_citable_sequences))
                and isinstance(v9_passing_check_sequences, list)
                and all(
                    type(sequence) is int
                    for sequence in v9_passing_check_sequences
                )
                and set(v9_passing_check_sequences).issubset(
                    v9_citable_sequence_set
                )
                and (
                    v9_source_get_diff_sequence is None
                    or (
                        type(v9_source_get_diff_sequence) is int
                        and v9_source_get_diff_sequence
                        in v9_citable_sequence_set
                    )
                )
            )
        )
        request_context_ok = bool(
            isinstance(execution_context, dict)
            and set(execution_context) == expected_execution_context_keys
            and execution_context.get("phase") == "REVIEW"
            and isinstance(request_artifact_id, str)
            and call.payload.get("request_artifact_id")
            == request_artifact_id
            and call.payload.get("request_phase") == "REVIEW"
            and request_valid
            and isinstance(request_evidence, dict)
            and isinstance(request_context_build, dict)
            and request_context_build.get("tool_results") == presented
            and v9_review_context_ok
            and _request_runtime_contract_valid(
                request_evidence.get("request_body"),
                manifest,
            )
            and len(matching_model_calls) == 1
        )
        review_valid, review_payload, review_item = nested_json(
            outcome,
            role="task-review",
            descriptor=outcome.payload.get("review_artifact"),
        )
        mutation_sequence = result_payload.get(
            "mutation_event_sequence"
        )
        source_get_diff_sequence = result_payload.get(
            "source_get_diff_sequence"
        )
        mutation = (
            events_by_sequence.get(mutation_sequence)
            if type(mutation_sequence) is int
            else None
        )
        source_get_diff = (
            events_by_sequence.get(source_get_diff_sequence)
            if type(source_get_diff_sequence) is int
            else None
        )
        presented_sequences = complete_presented_sequences(
            presented
        )
        binding_ok = bool(
            review_valid
            and isinstance(review_payload, dict)
            and mutation is not None
            and mutation.type == EventType.PATCH_APPLIED
            and mutation.payload.get("worktree_diff_hash")
            == worktree_diff_hash
            and source_get_diff is not None
            and source_get_diff.type == EventType.TOOL_SUCCEEDED
            and source_get_diff.payload.get("tool") == "get_diff"
            and source_get_diff.payload.get("worktree_diff_hash")
            == worktree_diff_hash
            and (
                not review_v9
                or source_get_diff.sequence
                == v9_source_get_diff_sequence
            )
            and mutation.sequence < source_get_diff.sequence
            < call.sequence < outcome.sequence
            and source_get_diff.sequence in presented_sequences
            and not any(
                event.type == EventType.PATCH_APPLIED
                and mutation.sequence < event.sequence < outcome.sequence
                for event in events
            )
        )
        current_checks = {
            str(event.payload.get("check_id")): event
            for event in events
            if (
                mutation is not None
                and source_get_diff is not None
                and mutation.sequence < event.sequence
                < source_get_diff.sequence
                and event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool") == "run_check"
                and event.payload.get("passed") is True
                and event.payload.get("worktree_diff_hash")
                == worktree_diff_hash
            )
        }
        checks_ok = all(
            check.id in current_checks
            for check in package.public.visible_checks
        )

        requirements = arguments.get("requirements")
        targeted_validation = arguments.get(
            "targeted_validation"
        )
        residual_risks = arguments.get("residual_risks")
        review_shape_ok = bool(
            isinstance(requirements, list)
            and 1 <= len(requirements) <= 20
            and isinstance(targeted_validation, list)
            and 1 <= len(targeted_validation) <= 20
            and isinstance(residual_risks, list)
            and len(residual_risks) <= 20
            and len(
                canonical_json(
                    {
                        "requirements": requirements,
                        "targeted_validation": targeted_validation,
                        "residual_risks": residual_risks,
                    }
                ).encode("utf-8")
            )
            <= 12_000
        )
        normalized_requirements: list[dict[str, Any]] = []
        observed_requirement_ids: list[str] = []
        if isinstance(requirements, list):
            for item in requirements:
                expected_requirement_keys = (
                    {
                        "requirement_id",
                        "status",
                        "evidence_event_sequences",
                        "notes",
                    }
                    if review_v2
                    else {
                        "requirement",
                        "status",
                        "evidence_event_sequences",
                        "notes",
                    }
                )
                if (
                    not isinstance(item, dict)
                    or set(item) != expected_requirement_keys
                ):
                    review_shape_ok = False
                    continue
                requirement_id = item.get("requirement_id")
                requirement = (
                    authoritative_requirements.get(requirement_id)
                    if review_v2
                    else item.get("requirement")
                )
                status = item.get("status")
                sequences = item.get(
                    "evidence_event_sequences"
                )
                notes = item.get("notes")
                item_ok = bool(
                    isinstance(requirement, str)
                    and requirement.strip()
                    and len(requirement) <= 1000
                    and status
                    in {
                        "verified",
                        "partially_verified",
                        "unverified",
                    }
                    and isinstance(sequences, list)
                    and len(sequences) <= 20
                    and len(sequences) == len(set(sequences))
                    and (
                        status == "unverified"
                        or bool(sequences)
                    )
                    and isinstance(notes, str)
                    and notes.strip()
                    and len(notes) <= 2000
                )
                if review_v2:
                    item_ok = bool(
                        item_ok
                        and isinstance(requirement_id, str)
                        and requirement_id in authoritative_requirements
                        and requirement_id not in observed_requirement_ids
                    )
                for sequence in (
                    sequences
                    if isinstance(sequences, list)
                    else []
                ):
                    cited = (
                        events_by_sequence.get(sequence)
                        if type(sequence) is int
                        else None
                    )
                    item_ok = bool(
                        item_ok
                        and mutation is not None
                        and type(sequence) is int
                        and sequence > mutation.sequence
                        and sequence in presented_sequences
                        and (
                            not review_v9
                            or sequence in v9_citable_sequence_set
                        )
                        and cited is not None
                        and cited.type
                        == EventType.TOOL_SUCCEEDED
                        and cited.payload.get(
                            "worktree_diff_hash"
                        )
                        == worktree_diff_hash
                    )
                review_shape_ok = bool(
                    review_shape_ok and item_ok
                )
                if item_ok:
                    normalized_requirement = {
                            "status": status,
                            "evidence_event_sequences": list(
                                sequences
                            ),
                            "notes": notes.strip(),
                        }
                    if review_v2:
                        observed_requirement_ids.append(requirement_id)
                        normalized_requirement.update(
                            {
                                "requirement_id": requirement_id,
                                "source_excerpt": requirement.strip(),
                            }
                        )
                    else:
                        normalized_requirement["requirement"] = (
                            requirement.strip()
                        )
                    normalized_requirements.append(normalized_requirement)
        if review_v2 and set(observed_requirement_ids) != set(
            authoritative_requirements
        ):
            review_shape_ok = False

        normalized_validation: list[dict[str, Any]] = []
        passing_targeted_validation = False
        seen_validation_sequences: set[int] = set()
        expected_tools = {
            "probe": {"run_probe"},
            "registered_check": {"run_check"},
            "repository_evidence": {
                "read_file",
                "search_files",
                "get_diff",
            },
        }
        if isinstance(targeted_validation, list):
            for item in targeted_validation:
                if (
                    not isinstance(item, dict)
                    or set(item)
                    != {
                        "kind",
                        "event_sequence",
                        "outcome",
                        "notes",
                    }
                ):
                    review_shape_ok = False
                    continue
                kind = item.get("kind")
                sequence = item.get("event_sequence")
                declared_outcome = item.get("outcome")
                notes = item.get("notes")
                cited = (
                    events_by_sequence.get(sequence)
                    if type(sequence) is int
                    else None
                )
                actual_outcome = None
                if cited is not None:
                    if cited.payload.get("timed_out") is True:
                        actual_outcome = "inconclusive"
                    elif kind in {"probe", "registered_check"}:
                        actual_outcome = (
                            "passed"
                            if cited.payload.get("passed") is True
                            else "failed"
                        )
                    else:
                        actual_outcome = "passed"
                item_ok = bool(
                    kind in expected_tools
                    and type(sequence) is int
                    and sequence not in seen_validation_sequences
                    and declared_outcome
                    in {"passed", "failed", "inconclusive"}
                    and isinstance(notes, str)
                    and notes.strip()
                    and len(notes) <= 2000
                    and mutation is not None
                    and sequence > mutation.sequence
                    and sequence in presented_sequences
                    and (
                        not review_v9
                        or (
                            sequence in v9_citable_sequence_set
                            and (
                                (
                                    kind
                                    in {"probe", "registered_check"}
                                    and sequence
                                    in v9_passing_check_sequence_set
                                )
                                or (
                                    kind == "repository_evidence"
                                    and sequence
                                    == v9_source_get_diff_sequence
                                )
                            )
                        )
                    )
                    and cited is not None
                    and cited.type == EventType.TOOL_SUCCEEDED
                    and cited.payload.get("tool")
                    in expected_tools.get(str(kind), set())
                    and cited.payload.get("worktree_diff_hash")
                    == worktree_diff_hash
                    and declared_outcome == actual_outcome
                )
                review_shape_ok = bool(
                    review_shape_ok and item_ok
                )
                if item_ok:
                    seen_validation_sequences.add(sequence)
                    if (
                        kind in {"probe", "registered_check"}
                        and actual_outcome == "passed"
                    ):
                        passing_targeted_validation = True
                    normalized_validation.append(
                        {
                            "kind": kind,
                            "event_sequence": sequence,
                            "outcome": declared_outcome,
                            "notes": notes.strip(),
                        }
                    )
        normalized_residual_risks: list[Any] = []
        residual_risks_ok = isinstance(residual_risks, list)
        risk_requirement_ids: set[str] = set()
        if isinstance(residual_risks, list):
            for item in residual_risks:
                if review_v2:
                    item_ok = bool(
                        isinstance(item, dict)
                        and set(item)
                        == {"requirement_ids", "risk", "mitigation"}
                        and isinstance(item.get("requirement_ids"), list)
                        and bool(item["requirement_ids"])
                        and len(item["requirement_ids"]) <= 20
                        and len(set(item["requirement_ids"]))
                        == len(item["requirement_ids"])
                        and all(
                            isinstance(requirement_id, str)
                            and requirement_id in authoritative_requirements
                            for requirement_id in item["requirement_ids"]
                        )
                        and isinstance(item.get("risk"), str)
                        and bool(item["risk"].strip())
                        and len(item["risk"]) <= 1000
                        and isinstance(item.get("mitigation"), str)
                        and bool(item["mitigation"].strip())
                        and len(item["mitigation"]) <= 1000
                    )
                    if item_ok:
                        risk_requirement_ids.update(item["requirement_ids"])
                        normalized_residual_risks.append(
                            {
                                "requirement_ids": list(
                                    item["requirement_ids"]
                                ),
                                "risk": item["risk"].strip(),
                                "mitigation": item["mitigation"].strip(),
                            }
                        )
                else:
                    item_ok = bool(
                        isinstance(item, str)
                        and item.strip()
                        and len(item) <= 1000
                    )
                    if item_ok:
                        normalized_residual_risks.append(item.strip())
                residual_risks_ok = bool(
                    residual_risks_ok and item_ok
                )
        if review_v2:
            nonverified_ids = {
                item["requirement_id"]
                for item in normalized_requirements
                if item["status"] != "verified"
            }
            residual_risks_ok = bool(
                residual_risks_ok
                and review_contract is not None
                and nonverified_ids.issubset(risk_requirement_ids)
            )
        expected_review = {
            "schema_version": (
                "task-review-v2" if review_v2 else "task-review-v1"
            ),
            "run_id": manifest.run_id,
            "request_artifact_id": request_artifact_id,
            "worktree_diff_hash": worktree_diff_hash,
            "mutation_event_sequence": mutation_sequence,
            "source_get_diff_sequence": (
                source_get_diff_sequence
            ),
            "requirements": normalized_requirements,
            "targeted_validation": normalized_validation,
            "residual_risks": (
                normalized_residual_risks if residual_risks_ok else []
            ),
            "deterministic_correctness_claimed": False,
        }
        if review_v2 and review_contract is not None:
            expected_review.update(
                {
                    "public_review_contract_hash": review_contract.content_hash,
                    "public_review_contract_schema_version": (
                        review_contract.schema_version
                    ),
                    "authoritative_requirement_ids": list(
                        authoritative_requirements
                    ),
                }
            )
        review_result_ok = bool(
            request_context_ok
            and binding_ok
            and checks_ok
            and review_shape_ok
            and residual_risks_ok
            and passing_targeted_validation
            and review_payload == expected_review
            and result_payload.get("schema_version")
            == (
                "task-review-result-v2"
                if review_v2
                else "task-review-result-v1"
            )
            and result_payload.get("review_schema_version")
            == expected_review["schema_version"]
            and result_payload.get("review_artifact")
            == outcome.payload.get("review_artifact")
            and result_payload.get("review_content_hash")
            == review_item.get("actual_content_hash")
            and result_payload.get("review") == expected_review
            and result_payload.get("request_artifact_id")
            == request_artifact_id
            and result_payload.get("worktree_diff_hash")
            == worktree_diff_hash
            and result_payload.get("mutation_event_sequence")
            == mutation_sequence
            and result_payload.get("source_get_diff_sequence")
            == source_get_diff_sequence
            and result_payload.get("requirement_count")
            == len(normalized_requirements)
            and result_payload.get("targeted_validation_count")
            == len(normalized_validation)
            and result_payload.get("residual_risk_count")
            == len(residual_risks or [])
            and result_payload.get("self_attestation") is True
            and result_payload.get(
                "deterministic_correctness_claimed"
            )
            is False
            and (
                not review_v2
                or result_payload.get("public_review_contract_hash")
                == review_contract.content_hash
            )
            and outcome.payload.get("review_content_hash")
            == review_item.get("actual_content_hash")
            and outcome.payload.get("requirement_count")
            == len(normalized_requirements)
            and outcome.payload.get("targeted_validation_count")
            == len(normalized_validation)
            and outcome.payload.get("residual_risk_count")
            == len(residual_risks or [])
            and outcome.payload.get("request_artifact_id")
            == request_artifact_id
            and outcome.payload.get("worktree_diff_hash")
            == worktree_diff_hash
            and outcome.payload.get("mutation_event_sequence")
            == mutation_sequence
            and outcome.payload.get("source_get_diff_sequence")
            == source_get_diff_sequence
            and outcome.payload.get("self_attestation") is True
            and outcome.payload.get(
                "deterministic_correctness_claimed"
            )
            is False
        )
        if review_result_ok:
            verified_review_sequences.append(outcome.sequence)
            review_artifacts[outcome.sequence] = {
                "descriptor": outcome.payload.get(
                    "review_artifact"
                ),
                "content_hash": review_item.get(
                    "actual_content_hash"
                ),
                "source_get_diff_sequence": (
                    source_get_diff_sequence
                ),
                "worktree_diff_hash": worktree_diff_hash,
                "review": expected_review,
            }
        else:
            failed_call_sequences.append(call.sequence)

    orphan_outcomes = [
        event.sequence
        for event in outcomes
        if not any(
            call.correlation_id == event.correlation_id
            and call.payload.get("tool")
            == event.payload.get("tool")
            and call.sequence < event.sequence
            for call in calls
        )
    ]
    failed_call_sequences.extend(orphan_outcomes)

    evaluation_completed = bool(
        result is not None
        and result.evaluation_status == "completed"
    )
    review_body_presented = False
    post_review_validation_sequences: list[int] = []
    final_binding_ok = bool(coverage_v10 or not evaluation_completed)
    if evaluation_completed and not coverage_v10:
        acceptances = [
            event
            for event in events
            if event.type == EventType.SUBMISSION_ACCEPTED
        ]
        reviews = [
            event
            for event in events
            if event.type == EventType.REVIEW_RECORDED
        ]
        accepted = acceptances[0] if len(acceptances) == 1 else None
        final_review = (
            reviews[0]
            if (
                accepted is not None
                and len(reviews) == 1
                and reviews[0].correlation_id
                == accepted.correlation_id
            )
            else None
        )
        source_review_sequence = (
            final_review.payload.get(
                "source_task_review_sequence"
            )
            if final_review is not None
            else None
        )
        review_evidence = (
            review_artifacts.get(source_review_sequence)
            if type(source_review_sequence) is int
            else None
        )
        finish_contexts = [
            event
            for event in events
            if final_review is not None
            and event.type == EventType.CONTEXT_BUILT
            and event.payload.get("artifact_id")
            == final_review.payload.get("request_artifact_id")
            and event.sequence < final_review.sequence
        ]
        finish_context = (
            finish_contexts[0]
            if len(finish_contexts) == 1
            else None
        )
        finish_request_valid = False
        finish_request = None
        if finish_context is not None:
            finish_request_valid, finish_request = (
                _request_evidence_payload(
                    finish_context,
                    artifact_root=artifact_root,
                    expected_provider=manifest.model.provider,
                )
            )
        finish_presented = (
            finish_request.get("context_build", {}).get(
                "tool_results"
            )
            if isinstance(finish_request, dict)
            else None
        )
        review_presented = bool(
            type(source_review_sequence) is int
            and source_review_sequence
            in complete_presented_sequences(finish_presented)
        )
        review_body_presented = False
        if (
            finish_request_valid
            and isinstance(finish_request, dict)
            and review_evidence is not None
        ):
            rendered_context = _request_context(
                finish_request.get("request_body"),
                allow_direct_context=(
                    manifest.model.provider in {"mock", "replay"}
                ),
            )
            try:
                rendered_payload = json.loads(rendered_context or "")
            except (TypeError, json.JSONDecodeError):
                rendered_payload = None
            recent_events = (
                rendered_payload.get("recent_events")
                if isinstance(rendered_payload, dict)
                else None
            )
            if isinstance(recent_events, list):
                matching_rendered_reviews = [
                    item
                    for item in recent_events
                    if (
                        isinstance(item, dict)
                        and item.get("sequence")
                        == source_review_sequence
                    )
                ]
                rendered_review_result = (
                    matching_rendered_reviews[0]["payload"].get(
                        "tool_result"
                    )
                    if (
                        len(matching_rendered_reviews) == 1
                        and isinstance(
                            matching_rendered_reviews[0].get("payload"),
                            dict,
                        )
                    )
                    else None
                )
                review_body_presented = bool(
                    isinstance(rendered_review_result, dict)
                    and rendered_review_result.get("review")
                    == review_evidence["review"]
                )
        post_review_validation_sequences = [
            event.sequence
            for event in events
            if (
                type(source_review_sequence) is int
                and accepted is not None
                and source_review_sequence < event.sequence
                < accepted.sequence
                and event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool")
                in {"run_probe", "run_check", "get_diff"}
                and review_evidence is not None
                and event.payload.get("worktree_diff_hash")
                == review_evidence["worktree_diff_hash"]
            )
        ]
        final_binding_ok = bool(
            accepted is not None
            and final_review is not None
            and review_evidence is not None
            and review_evidence["worktree_diff_hash"]
            == accepted.payload.get("worktree_diff_hash")
            == final_review.payload.get("worktree_diff_hash")
            and final_review.payload.get(
                "source_get_diff_sequence"
            )
            == review_evidence["source_get_diff_sequence"]
            and final_review.payload.get("task_review_artifact")
            == review_evidence["descriptor"]
            and accepted.payload.get("task_review_artifact")
            == review_evidence["descriptor"]
            and final_review.payload.get(
                "task_review_content_hash"
            )
            == review_evidence["content_hash"]
            and accepted.payload.get("task_review_content_hash")
            == review_evidence["content_hash"]
            and final_review.payload.get("complete_tool_result")
            is True
            and finish_request_valid
            and isinstance(finish_request, dict)
            and _request_runtime_contract_valid(
                finish_request.get("request_body"),
                manifest,
            )
            and review_presented
            and review_body_presented
            and not post_review_validation_sequences
        )
    version_pair_valid = bool(
        (
            manifest.tool_schema_version == "v3"
            and manifest.context_policy_version == "phase-evidence-v6"
        )
        or (
            manifest.tool_schema_version == "v4"
            and manifest.context_policy_version == "phase-evidence-v7"
            and manifest.public_review_contract is not None
        )
        or (
            manifest.tool_schema_version == "v4"
            and manifest.context_policy_version == "phase-evidence-v8"
            and manifest.public_review_contract is not None
        )
        or (
            manifest.tool_schema_version == "v4"
            and manifest.context_policy_version == "phase-evidence-v9"
            and manifest.public_review_contract is not None
        )
        or (
            manifest.tool_schema_version == "v5"
            and manifest.context_policy_version == "phase-evidence-v10"
            and manifest.public_review_contract is not None
        )
        or (
            manifest.tool_schema_version == "v6"
            and manifest.context_policy_version == "phase-evidence-v11"
            and manifest.public_review_contract is not None
        )
    )
    passed = bool(
        version_pair_valid
        and probe_manifest_binding_valid
        and not failed_call_sequences
        and final_binding_ok
    )
    return passed, {
        "probe_call_count": sum(
            call.payload.get("tool") == "run_probe"
            for call in calls
        ),
        "verified_probe_count": len(verified_probe_sequences),
        "review_call_count": sum(
            call.payload.get("tool") == "review_task"
            for call in calls
        ),
        "verified_review_count": len(verified_review_sequences),
        "failed_call_sequences": sorted(
            set(failed_call_sequences)
        ),
        "evaluation_completed": evaluation_completed,
        "final_submission_binding_valid": final_binding_ok,
        "review_body_presented": (
            review_body_presented if evaluation_completed else False
        ),
        "probe_manifest_binding_valid": (
            probe_manifest_binding_valid
        ),
        "post_review_validation_sequences": (
            post_review_validation_sequences
        ),
    }


def _private_leak_tokens(
    package: TaskPackage,
    *,
    api_key: str | None,
) -> set[str]:
    public_text = canonical_json(package.public.model_dump(mode="json")).lower()
    disclosure_tolerant = {
        "private.yaml",
        "reference.patch",
        ".patchloop-hidden",
        *(check.id for check in package.private.hidden_checks),
    }
    tokens = {token for token in disclosure_tolerant if token and token.lower() not in public_text}

    if package.private.reference_patch.sha256:
        tokens.add(package.private.reference_patch.sha256)
    for artifact in package.private.hidden_artifacts:
        tokens.update({artifact.path, artifact.sha256})
    if api_key:
        tokens.add(api_key)
    return tokens


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
        worker_claims = state.list_worker_claims(run_id)
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
        "checkpoints": [checkpoint.model_dump(mode="json") for checkpoint in checkpoints],
        # Preserve source-evidence hashes when backward-compatible result fields
        # gain defaults after an immutable run was recorded.
        "result": (
            result.model_dump(mode="json", exclude_unset=True) if result is not None else None
        ),
        "persisted_result_hash": persisted_result_hash,
        "agent_visible_artifacts": artifacts,
        "execution_plan_hash": (sha256_bytes(plan_bytes) if plan_bytes is not None else None),
    }
    if manifest.tool_schema_version in {"v2", "v3", "v4", "v5", "v6"}:
        _, accepted_patch_artifacts = _accepted_patch_artifact_evidence(
            root=run_root,
            events=events,
        )
        snapshot["schema_version"] = _SOURCE_EVIDENCE_SCHEMA_VERSION_V3
        snapshot["accepted_patch_artifacts"] = accepted_patch_artifacts
        if any(event.type == EventType.PATCH_PREPARED for event in events):
            _, _, _, patch_intent_artifacts = _patch_intent_artifact_evidence(
                root=run_root,
                events=events,
                private_tokens=set(),
            )
            snapshot["patch_intent_artifacts"] = patch_intent_artifacts
        snapshot["worker_claims"] = worker_claims
    verifier_evidence_declared = bool(
        result is not None
        and any(
            "evidence_artifacts" in verifier_result.details
            for verifier_result in result.verifier_results
        )
    )
    receipt_path = run_root / "artifacts" / "runs" / run_id / "evaluation-receipt.json"
    if verifier_evidence_declared or receipt_path.exists():
        # Fresh v1/replay runs also use the modern evaluator receipt. Bind
        # those new artifacts without changing hashes for historical v1 runs
        # that have neither receipt nor full verifier descriptors.
        snapshot["schema_version"] = _SOURCE_EVIDENCE_SCHEMA_VERSION_V3
        _, verifier_evidence = _verifier_artifact_evidence(
            root=run_root,
            result=result,
            required=True,
        )
        _, receipt_evidence = _evaluation_receipt_evidence(
            root=run_root,
            run_id=run_id,
            manifest=manifest,
            result=result,
        )
        snapshot["verifier_evidence_artifacts"] = verifier_evidence
        snapshot["evaluation_receipt"] = receipt_evidence
    if manifest.context_policy_version == "phase-evidence-v4":
        _, _, _, investigation_artifacts, _ = _artifact_evidence(
            root=run_root,
            events=events,
            private_tokens=set(),
            event_types={
                EventType.TOOL_REPLAYED,
                EventType.TOOL_ADMISSION_BLOCKED,
            },
            required_event_types={
                EventType.TOOL_REPLAYED,
                EventType.TOOL_ADMISSION_BLOCKED,
            },
        )
        (
            _,
            _,
            _,
            admission_input_artifacts,
            _,
        ) = _v4_admission_nested_artifact_evidence(
            root=run_root,
            events=events,
            private_tokens=set(),
        )
        snapshot["schema_version"] = _SOURCE_EVIDENCE_SCHEMA_VERSION_V4
        snapshot["investigation_artifacts"] = investigation_artifacts
        snapshot[
            "investigation_admission_nested_artifacts"
        ] = admission_input_artifacts
    elif manifest.context_policy_version in {
        "phase-evidence-v5",
        "phase-evidence-v6",
        "phase-evidence-v7",
        "phase-evidence-v8",
        "phase-evidence-v9",
        "phase-evidence-v10",
        "phase-evidence-v11",
    }:
        _, _, _, investigation_artifacts, _ = _artifact_evidence(
            root=run_root,
            events=events,
            private_tokens=set(),
            event_types={
                EventType.TOOL_REPLAYED,
                EventType.TOOL_ADMISSION_BLOCKED,
            },
            required_event_types={
                EventType.TOOL_REPLAYED,
                EventType.TOOL_ADMISSION_BLOCKED,
            },
        )
        (
            _,
            _,
            _,
            admission_input_artifacts,
            _,
        ) = _v4_admission_nested_artifact_evidence(
            root=run_root,
            events=events,
            private_tokens=set(),
        )
        snapshot["schema_version"] = {
            "phase-evidence-v5": _SOURCE_EVIDENCE_SCHEMA_VERSION_V5,
            "phase-evidence-v6": _SOURCE_EVIDENCE_SCHEMA_VERSION_V6,
            "phase-evidence-v7": _SOURCE_EVIDENCE_SCHEMA_VERSION_V7,
            "phase-evidence-v8": _SOURCE_EVIDENCE_SCHEMA_VERSION_V8,
            "phase-evidence-v9": _SOURCE_EVIDENCE_SCHEMA_VERSION_V9,
            "phase-evidence-v10": _SOURCE_EVIDENCE_SCHEMA_VERSION_V10,
            "phase-evidence-v11": _SOURCE_EVIDENCE_SCHEMA_VERSION_V11,
        }[manifest.context_policy_version]
        snapshot["investigation_artifacts"] = investigation_artifacts
        snapshot[
            "investigation_admission_nested_artifacts"
        ] = admission_input_artifacts
        if manifest.tool_schema_version in {"v3", "v4", "v5", "v6"}:
            (
                _,
                _,
                _,
                self_validation_artifacts,
                _,
            ) = _self_validation_nested_artifact_evidence(
                root=run_root,
                events=events,
                private_tokens=set(),
            )
            snapshot[
                "self_validation_nested_artifacts"
            ] = self_validation_artifacts
        if manifest.tool_schema_version in {"v4", "v5", "v6"}:
            (
                _,
                _,
                _,
                patch_source_artifacts,
                _,
            ) = _patch_source_snapshot_artifact_evidence(
                root=run_root,
                events=events,
                private_tokens=set(),
            )
            snapshot[
                "patch_source_snapshot_artifacts"
            ] = patch_source_artifacts
        if manifest.context_policy_version in {
            "phase-evidence-v10",
            "phase-evidence-v11",
        }:
            snapshot["public_review_base_provenance"] = (
                _v10_base_provenance_source_evidence(
                    root=run_root,
                    manifest=manifest,
                    events=events,
                )
            )
    return sha256_text(canonical_json(snapshot))


def qualify_run(
    run_id: str,
    *,
    task_dir: str | Path,
    dataset_manifest_path: str | Path | None = None,
    root: str | Path | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Qualify one terminal run and optionally persist its immutable artifact.

    ``persist=False`` is the read-only recomputation path used by append-only
    postmortem corrections. It still validates an existing qualification's
    task, dataset, and source-evidence bindings, but never replaces or creates
    the canonical qualification artifact.
    """

    run_root = _runtime_root(root)
    state = StateStore(run_root / "state.sqlite3")
    try:
        manifest = state.get_manifest(run_id)
    except RecoveryError as exc:
        raise ContractError(f"run manifest is unavailable: {run_id}") from exc
    package = load_task_package(task_dir)
    events = state.list_events(run_id)
    checkpoints = state.list_checkpoints(run_id)
    worker_claims = state.list_worker_claims(run_id)
    result = _result_for_run(state, run_id)
    path = qualification_path(run_id, root=run_root)
    if path.is_file():
        existing = load_trace_qualification(run_id, root=run_root)
        existing_is_legacy = (
            existing["schema_version"]
            == LEGACY_QUALIFICATION_SCHEMA_VERSION
        )
        task_identity = (
            manifest.task_id == package.public.task_id
            and manifest.task_version == package.public.task_version
            and manifest.public_spec_hash == package.public_spec_hash
            and manifest.private_spec_hash == package.private_spec_hash
        )
        if not task_identity:
            raise ContractError(
                "legacy trace qualification task identity mismatch"
                if existing_is_legacy
                else "trace qualification task identity mismatch"
            )
        _, current_dataset_hash, _ = load_dataset_manifest(
            dataset_manifest_path
        )
        if existing.get("dataset_manifest_hash") != current_dataset_hash:
            raise ContractError(
                "legacy trace qualification dataset manifest changed"
                if existing_is_legacy
                else "trace qualification dataset manifest changed"
            )
        current_source_hash = calculate_source_evidence_hash(
            run_id,
            root=run_root,
            require_valid_plan=False,
        )
        if existing["source_evidence_hash"] != current_source_hash:
            raise ContractError(
                "legacy trace qualification source evidence changed"
                if existing_is_legacy
                else f"trace qualification is immutable: {run_id}"
            )
        if existing_is_legacy:
            if manifest.tool_schema_version != "v1":
                raise ContractError(
                    "legacy trace qualification does not match the run contract"
                )
            return existing

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
    corrective_runtime_content_hash: str | None = None
    if manifest.tool_schema_version in {"v4", "v5", "v6"}:
        from patchloop.agent.review import (
            validate_public_review_contract,
        )

        review_contract = manifest.public_review_contract
        review_contract_valid = False
        if review_contract is not None:
            try:
                validate_public_review_contract(
                    review_contract,
                    task=package.public,
                    public_spec_hash=package.public_spec_hash,
                )
                review_contract_valid = True
            except ContractError:
                review_contract_valid = False
        if manifest.tool_schema_version == "v4":
            add(
                "public_review_contract",
                review_contract_valid,
                declared=review_contract is not None,
                content_hash=(
                    review_contract.content_hash
                    if review_contract is not None
                    else None
                ),
            )
        else:
            (
                public_coverage_contract_ok,
                public_coverage_contract_details,
            ) = _v10_public_coverage_contract_evidence(
                root=run_root,
                manifest=manifest,
                package=package,
                events=events,
            )
            add(
                "public_coverage_contract",
                public_coverage_contract_ok,
                **public_coverage_contract_details,
            )
        (
            corrective_runtime_ok,
            corrective_runtime_details,
        ) = _corrective_runtime_contract_evidence(
            root=run_root,
            manifest=manifest,
            events=events,
        )
        corrective_runtime_content_hash = (
            corrective_runtime_details.get("content_hash")
        )
        add(
            "corrective_runtime_contract",
            corrective_runtime_ok,
            **corrective_runtime_details,
        )

    contiguous = [event.sequence for event in events] == list(range(1, len(events) + 1))
    add("contiguous_events", contiguous, event_count=len(events))
    if manifest.tool_schema_version in {"v2", "v3", "v4", "v5", "v6"}:
        claim_ids = [claim.get("claim_id") for claim in worker_claims]
        owner_ids = [claim.get("owner_id") for claim in worker_claims]
        claimed_at = [claim.get("claimed_at") for claim in worker_claims]
        claims_ok = all(
            claim.get("run_id") == run_id
            and isinstance(claim.get("owner_id"), str)
            and bool(claim["owner_id"])
            and isinstance(claim.get("owner_pid"), int)
            and claim["owner_pid"] > 0
            and isinstance(claim.get("owner_hostname"), str)
            and bool(claim["owner_hostname"])
            and claim.get("prior_status")
            in {
                RunStatus.CREATED.value,
                RunStatus.SUSPENDED.value,
                RunStatus.RUNNING.value,
            }
            and claim.get("reclaimed") == (claim.get("prior_status") == RunStatus.RUNNING.value)
            for claim in worker_claims
        )
        claims_ok = bool(
            claims_ok
            and worker_claims
            and worker_claims[0].get("prior_status") == RunStatus.CREATED.value
            and all(
                claim.get("prior_status")
                in {
                    RunStatus.SUSPENDED.value,
                    RunStatus.RUNNING.value,
                }
                for claim in worker_claims[1:]
            )
            and len(set(claim_ids)) == len(claim_ids)
            and len(set(owner_ids)) == len(owner_ids)
            and claimed_at == sorted(claimed_at)
        )
        add(
            "worker_claim_provenance",
            claims_ok,
            claim_count=len(worker_claims),
            running_reclaim_count=sum(claim.get("reclaimed") is True for claim in worker_claims),
        )

    terminals = [event for event in events if event.type in _TERMINAL_EVENTS]
    terminal_ok = (
        len(terminals) == 1 and bool(events) and events[-1].event_id == terminals[0].event_id
    )
    terminal_type = terminals[0].type.value if len(terminals) == 1 else None
    add(
        "single_terminal_event",
        terminal_ok,
        terminal_count=len(terminals),
        terminal_type=terminal_type,
    )

    lifecycle_types = {
        EventType.REVIEW_RECORDED,
        EventType.SUBMISSION_ATTEMPTED,
        EventType.SUBMISSION_REJECTED,
        EventType.SUBMISSION_ACCEPTED,
    }
    lifecycle_events = [event for event in events if event.type in lifecycle_types]
    structured_lifecycle_contract = bool(manifest.tool_schema_version != "v1" or lifecycle_events)
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
    if structured_lifecycle_contract:
        checkpoint_integrity, checkpoint_details = _v2_checkpoint_event_integrity(
            checkpoints, events
        )
        add(
            "required_trace_evidence",
            not required_missing and checkpoint_integrity,
            missing_event_types=required_missing,
            checkpoint_count=len(checkpoints),
            **checkpoint_details,
        )
    else:
        checkpoint_ids = {
            event.payload.get("checkpoint_id")
            for event in events
            if event.type == EventType.CHECKPOINT_SAVED
        }
        durable_ids = {checkpoint.checkpoint_id for checkpoint in checkpoints}
        required_trace = (
            not required_missing and bool(checkpoints) and checkpoint_ids.issubset(durable_ids)
        )
        add(
            "required_trace_evidence",
            required_trace,
            missing_event_types=required_missing,
            checkpoint_count=len(checkpoints),
        )

    lifecycle_evidence: dict[str, Any] = {}
    if manifest.tool_schema_version == "v1" and not lifecycle_events:
        lifecycle_ok = True
        lifecycle_mode = "legacy-unavailable"
    elif not lifecycle_events and result is not None and result.evaluation_status != "completed":
        lifecycle_ok = True
        lifecycle_mode = "structured-v2-no-submission"
    else:
        lifecycle_mode = "structured-v2"
        reviews = [event for event in lifecycle_events if event.type == EventType.REVIEW_RECORDED]
        attempts = [
            event for event in lifecycle_events if event.type == EventType.SUBMISSION_ATTEMPTED
        ]
        rejections = [
            event for event in lifecycle_events if event.type == EventType.SUBMISSION_REJECTED
        ]
        acceptances = [
            event for event in lifecycle_events if event.type == EventType.SUBMISSION_ACCEPTED
        ]

        def submission_key(event) -> tuple[str, ...] | None:
            if event.correlation_id:
                return ("correlation", event.correlation_id)
            attempt_number = event.payload.get("attempt_number")
            diff_hash = event.payload.get("worktree_diff_hash")
            if isinstance(attempt_number, int) and isinstance(diff_hash, str):
                return ("attempt", str(attempt_number), diff_hash)
            return None

        attempts_by_key: dict[tuple[str, ...], Any] = {}
        duplicate_attempt_keys = False
        for attempt_event in attempts:
            key = submission_key(attempt_event)
            if key is None or key in attempts_by_key:
                duplicate_attempt_keys = True
                continue
            attempts_by_key[key] = attempt_event
        outcomes = [*rejections, *acceptances]
        outcomes_by_key: dict[tuple[str, ...], list[Any]] = {}
        unkeyed_outcomes = 0
        for outcome_event in outcomes:
            key = submission_key(outcome_event)
            if key is None:
                unkeyed_outcomes += 1
                continue
            outcomes_by_key.setdefault(key, []).append(outcome_event)
        paired_attempts = all(
            len(outcomes_by_key.get(key, [])) == 1
            and attempt_event.sequence < outcomes_by_key[key][0].sequence
            for key, attempt_event in attempts_by_key.items()
        )
        orphan_outcomes = [key for key in outcomes_by_key if key not in attempts_by_key]
        lifecycle_ok = bool(
            attempts
            and len(attempts_by_key) == len(attempts)
            and not duplicate_attempt_keys
            and paired_attempts
            and not orphan_outcomes
            and unkeyed_outcomes == 0
            and len(outcomes) == len(attempts)
            and len(acceptances) <= 1
        )
        lifecycle_evidence.update(
            {
                "attempt_count": len(attempts),
                "paired_attempt_count": sum(
                    len(outcomes_by_key.get(key, [])) == 1 for key in attempts_by_key
                ),
                "orphan_outcome_count": len(orphan_outcomes) + unkeyed_outcomes,
            }
        )
        if acceptances:
            accepted = acceptances[0]
            accepted_key = submission_key(accepted)
            matching_reviews = [
                review for review in reviews if review.correlation_id == accepted.correlation_id
            ]
            attempt = attempts_by_key.get(accepted_key) if accepted_key is not None else None
            review = matching_reviews[0] if len(matching_reviews) == 1 else None
            accepted_diff = accepted.payload.get("worktree_diff_hash")
            submitted_patch_valid = False
            submitted_patch_payload = accepted.payload.get("submitted_patch_artifact")
            (
                accepted_patch_artifact_integrity,
                accepted_patch_artifact_evidence,
            ) = _accepted_patch_artifact_evidence(
                root=run_root,
                events=events,
            )
            try:
                submitted_patch_artifact = Artifact.model_validate(submitted_patch_payload)
                submitted_patch_valid = bool(
                    accepted_patch_artifact_integrity
                    and len(accepted_patch_artifact_evidence) == 1
                    and submitted_patch_artifact.content_hash == accepted_diff
                    and sha256_bytes(Path(submitted_patch_artifact.path).read_bytes())
                    == accepted_diff
                    and result is not None
                    and result.submitted_patch_artifact_id == submitted_patch_artifact.artifact_id
                )
            except (OSError, TypeError, ValueError):
                submitted_patch_valid = False
            source_sequence = (
                review.payload.get("source_get_diff_sequence") if review is not None else None
            )
            source_event = (
                next(
                    (event for event in events if event.sequence == source_sequence),
                    None,
                )
                if isinstance(source_sequence, int)
                else None
            )
            source_ok = bool(
                source_event is not None
                and source_event.type == EventType.TOOL_SUCCEEDED
                and source_event.payload.get("tool") == "get_diff"
                and source_event.payload.get("worktree_diff_hash") == accepted_diff
            )
            request_artifact_id = (
                review.payload.get("request_artifact_id") if review is not None else None
            )
            matching_contexts = [
                event
                for event in events
                if event.type == EventType.CONTEXT_BUILT
                and event.payload.get("artifact_id") == request_artifact_id
                and source_event is not None
                and source_event.sequence < event.sequence
                and review is not None
                and event.sequence < review.sequence
            ]
            context_event = matching_contexts[0] if len(matching_contexts) == 1 else None
            matching_model_calls = [
                event
                for event in events
                if event.type == EventType.MODEL_CALLED
                and event.payload.get("request_artifact_id") == request_artifact_id
                and context_event is not None
                and context_event.sequence < event.sequence
                and review is not None
                and event.sequence < review.sequence
            ]
            finish_calls = [
                event
                for event in events
                if event.type == EventType.TOOL_CALLED
                and event.correlation_id == accepted.correlation_id
                and event.payload.get("tool") == "finish_task"
            ]
            finish_call = finish_calls[0] if len(finish_calls) == 1 else None
            request_context_ok = (
                context_event is not None
                and len(matching_model_calls) == 1
                and finish_call is not None
                and matching_model_calls[0].sequence < finish_call.sequence
                and review is not None
                and finish_call.sequence < review.sequence
            )
            request_body_valid = False
            complete_source_in_context = False
            if (
                request_context_ok
                and context_event is not None
                and source_event is not None
                and isinstance(accepted_diff, str)
            ):
                (
                    request_body_valid,
                    complete_source_in_context,
                ) = _complete_get_diff_in_request(
                    context_event=context_event,
                    source_event=source_event,
                    accepted_diff=accepted_diff,
                    context_policy_version=(
                        manifest.context_policy_version
                    ),
                    artifact_root=run_root / "artifacts",
                    expected_provider=(
                        manifest.model.provider
                        if manifest.context_policy_version
                        in {
                            "phase-evidence-v4",
                            "phase-evidence-v5",
                            "phase-evidence-v6",
                            "phase-evidence-v7",
                            "phase-evidence-v8",
                            "phase-evidence-v9",
                        }
                        else None
                    ),
                )
            ordered_submission_ok = False
            ordered_submission_details: dict[str, Any] = {}
            if source_event is not None and isinstance(accepted_diff, str):
                (
                    ordered_submission_ok,
                    ordered_submission_details,
                ) = _ordered_submission_evidence(
                    task=package.public,
                    events=events,
                    accepted_event=accepted,
                    source_event=source_event,
                    accepted_diff=accepted_diff,
                )
            finish_successes = [
                event
                for event in events
                if event.type == EventType.TOOL_SUCCEEDED
                and event.correlation_id == accepted.correlation_id
                and event.payload.get("tool") == "finish_task"
            ]
            finish_success = finish_successes[0] if len(finish_successes) == 1 else None
            finish_success_ok = bool(
                attempt is not None
                and finish_success is not None
                and attempt.sequence < finish_success.sequence < accepted.sequence
                and finish_success.payload.get("worktree_diff_hash") == accepted_diff
                and finish_success.payload.get("submitted_patch_artifact")
                == submitted_patch_payload
            )
            done_transitions = [
                event
                for event in events
                if event.type == EventType.PHASE_CHANGED
                and event.sequence > accepted.sequence
                and event.payload.get("from") == "REVIEW"
                and event.payload.get("to") == "DONE"
            ]
            done_transition = done_transitions[0] if len(done_transitions) == 1 else None
            final_checkpoint = checkpoints[-1] if checkpoints else None
            final_checkpoint_ok = bool(
                done_transition is not None
                and final_checkpoint is not None
                and final_checkpoint.phase.value == "DONE"
                and final_checkpoint.worktree_diff_hash == accepted_diff
                and final_checkpoint.through_sequence >= done_transition.sequence
            )
            lifecycle_ok = bool(
                lifecycle_ok
                and len(matching_reviews) == 1
                and attempt is not None
                and review is not None
                and review.sequence < attempt.sequence < accepted.sequence
                and accepted.payload.get("worktree_diff_hash")
                == review.payload.get("worktree_diff_hash")
                == attempt.payload.get("worktree_diff_hash")
                and review.payload.get("complete_tool_result") is True
                and source_ok
                and request_context_ok
                and request_body_valid
                and complete_source_in_context
                and ordered_submission_ok
                and finish_success_ok
                and submitted_patch_valid
                and final_checkpoint_ok
                and accepted.payload.get("accepted_for") == "deterministic_evaluation"
                and accepted.payload.get("evaluation_success_claimed") is False
                and result is not None
                and result.agent_submission_status == "completed"
            )
            lifecycle_evidence.update(
                {
                    "source_get_diff_valid": source_ok,
                    "review_context_valid": request_context_ok,
                    "request_body_valid": request_body_valid,
                    "complete_source_in_context": complete_source_in_context,
                    "ordered_submission_valid": ordered_submission_ok,
                    **ordered_submission_details,
                    "finish_tool_success_valid": finish_success_ok,
                    "submitted_patch_artifact_valid": submitted_patch_valid,
                    "done_checkpoint_valid": final_checkpoint_ok,
                }
            )
        elif result is not None and result.evaluation_status == "completed":
            lifecycle_ok = False
    if structured_lifecycle_contract:
        add(
            "submission_lifecycle",
            lifecycle_ok,
            mode=lifecycle_mode,
            lifecycle_event_count=len(lifecycle_events),
            accepted_count=sum(
                event.type == EventType.SUBMISSION_ACCEPTED for event in lifecycle_events
            ),
            rejected_count=sum(
                event.type == EventType.SUBMISSION_REJECTED for event in lifecycle_events
            ),
            **lifecycle_evidence,
        )
    if manifest.tool_schema_version in {"v3", "v4", "v5", "v6"}:
        (
            self_validation_lifecycle_ok,
            self_validation_lifecycle_details,
        ) = _self_validation_lifecycle_evidence(
            root=run_root,
            manifest=manifest,
            package=package,
            events=events,
            result=result,
        )
        add(
            "self_validation_lifecycle",
            self_validation_lifecycle_ok,
            **self_validation_lifecycle_details,
        )

    no_memory = manifest.memory.condition == MemoryCondition.NO_MEMORY
    no_retrieval = EventType.MEMORY_RETRIEVED not in event_types
    no_index = manifest.memory.index_version is None and manifest.memory.index_hash is None
    no_memory_ok = no_memory and no_retrieval and no_index
    add(
        "no_memory_boundary",
        no_memory_ok,
        condition=manifest.memory.condition.value,
        retrieval_event_count=sum(event.type == EventType.MEMORY_RETRIEVED for event in events),
        index_declared=not no_index,
    )

    provider_ok = manifest.model.provider == "openai"
    add("live_openai_provider", provider_ok, provider=manifest.model.provider)
    common_model_contract = (
        manifest.model.reasoning_effort == "medium"
        and manifest.model.reasoning_mode == "standard"
        and manifest.model.service_tier == "default"
    )
    legacy_terra_model_contract = (
        manifest.model.model_id == _LEGACY_TERRA_MODEL_ID
        and manifest.budget == Budget()
        and manifest.model.max_output_tokens == 4096
    )
    mini_campaign_contract = (
        manifest.experiment is not None
        and manifest.experiment.purpose in _CAMPAIGN_PURPOSES
        and manifest.model.model_id == _GPT54_MINI_PILOT_MODEL_ID
        and (
            (
                manifest.experiment.experiment_id
                in _HISTORICAL_MINI_CAMPAIGN_EXPERIMENT_IDS
                and manifest.budget
                == _GPT54_MINI_D037_TAIL_RESERVE_BUDGET
            )
            or (
                manifest.experiment.experiment_id
                in _HISTORICAL_MINI_200K_CAMPAIGN_EXPERIMENT_IDS
                and manifest.budget
                == _GPT54_MINI_HISTORICAL_200K_CAMPAIGN_BUDGET
            )
            or (
                manifest.experiment.purpose
                == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT
                and manifest.experiment.experiment_id
                not in (
                    _HISTORICAL_MINI_CAMPAIGN_EXPERIMENT_IDS
                    | _HISTORICAL_MINI_200K_CAMPAIGN_EXPERIMENT_IDS
                    | _SUPERSEDED_250K_LIVE_EXPERIMENT_IDS
                )
                and manifest.budget == _GPT54_MINI_COMPLETION_BUDGET
            )
            or (
                manifest.experiment.purpose
                == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_BUDGET_PILOT
                and manifest.budget
                == _GPT54_MINI_MEMORY_DEVELOPMENT_BUDGET_PILOT
            )
            or (
                manifest.experiment.purpose
                == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT
                and manifest.budget
                == _GPT54_MINI_MEMORY_DEVELOPMENT_CORRECTIVE_PILOT
            )
            or (
                manifest.experiment.purpose
                == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT
                and manifest.budget
                == _GPT54_MINI_MEMORY_DEVELOPMENT_SATURATION_PILOT
            )
            or (
                manifest.experiment.purpose
                == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT
                and manifest.budget
                == _GPT54_MINI_MEMORY_DEVELOPMENT_REVIEW_EVIDENCE_PILOT
            )
            or (
                manifest.experiment.purpose
                == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT
                and manifest.budget
                == _GPT54_MINI_MEMORY_DEVELOPMENT_COVERAGE_REVIEW_PILOT
            )
            or (
                (
                    manifest.experiment.purpose
                    in {
                        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY,
                        ExperimentPurpose.CORE,
                    }
                    or manifest.experiment.experiment_id
                    in _SUPERSEDED_250K_LIVE_EXPERIMENT_IDS
                )
                and manifest.budget == _GPT54_MINI_CAMPAIGN_BUDGET
            )
        )
        and manifest.model.max_output_tokens == 25_000
    )
    mini_budget_and_output_contract = (
        (
            manifest.budget == _GPT54_MINI_PILOT_BUDGET
            and manifest.model.max_output_tokens == 4096
        )
        or (
            manifest.budget == _GPT54_MINI_D037_CORRECTIVE_BUDGET
            and manifest.model.max_output_tokens == 25_000
        )
        or (
            manifest.budget == _GPT54_MINI_D037_TAIL_RESERVE_BUDGET
            and manifest.model.max_output_tokens == 25_000
        )
    )
    mini_pilot_contract = (
        manifest.experiment is not None
        and manifest.experiment.purpose
        == ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT
        and manifest.model.model_id == _GPT54_MINI_PILOT_MODEL_ID
        and mini_budget_and_output_contract
    )
    model_contract_ok = common_model_contract and (
        legacy_terra_model_contract
        or mini_campaign_contract
        or mini_pilot_contract
    )
    model_contract_details = {
        "model_id": manifest.model.model_id,
        "reasoning_effort": manifest.model.reasoning_effort,
        "reasoning_mode": manifest.model.reasoning_mode,
        "service_tier": manifest.model.service_tier,
        "max_output_tokens": manifest.model.max_output_tokens,
    }
    if manifest.model.model_id == _GPT54_MINI_PILOT_MODEL_ID:
        model_contract_details["max_total_tokens"] = manifest.budget.max_total_tokens
    add(
        "frozen_model_contract",
        model_contract_ok,
        **model_contract_details,
    )
    controlled_rejection_mode = (
        manifest.fault.type
        == "controlled-reject-first-prepared-patch"
    )
    if not controlled_rejection_mode:
        fault_ok = (
            manifest.fault.type == "none"
            and EventType.FAULT_INJECTED not in event_types
        )
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
        ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT: {DatasetRole.DEVELOPMENT_VALIDATION},
        ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT: {
            DatasetRole.DEVELOPMENT_VALIDATION
        },
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY: {DatasetRole.MEMORY_DEVELOPMENT},
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_BUDGET_PILOT: {
            DatasetRole.MEMORY_DEVELOPMENT
        },
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT: {
            DatasetRole.MEMORY_DEVELOPMENT
        },
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT: {
            DatasetRole.MEMORY_DEVELOPMENT
        },
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT: {
            DatasetRole.MEMORY_DEVELOPMENT
        },
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT: {
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
        and Path(package.root).resolve() == (repository_root() / dataset_entry.path).resolve()
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
            sha256_bytes(execution_plan_bytes) if execution_plan_bytes is not None else None
        ),
        ready=bool(execution_plan is not None and execution_plan.get("ready") is True),
        approval_matches=bool(
            execution_plan is not None
            and isinstance(execution_plan.get("approval"), dict)
            and execution_plan["approval"].get("matches_execution_hash") is True
        ),
    )
    if (
        experiment is not None
        and experiment.purpose
        in {
            ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT,
            ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT,
            ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT,
            ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT,
        }
    ):
        from patchloop.evals.runner import (
            ExperimentSuite,
            _pricing_freshness_evidence,
            _pricing_freshness_passed,
        )

        pricing_freshness: dict[str, Any] = {
            "schema_version": "pricing-start-verification-v1",
            "checked_at": None,
            "age_seconds": None,
            "timezone_valid": False,
            "date_not_future": False,
            "within_maximum_age": False,
            "official_source_matches": False,
            "official_rates_match": False,
        }
        pricing_suite_valid = False
        run_started = [
            event
            for event in events
            if event.type == EventType.RUN_STARTED
        ]
        if (
            execution_plan_ok
            and execution_plan is not None
            and isinstance(execution_plan.get("suite"), dict)
            and len(run_started) == 1
            and run_started[0].actor == "runner"
        ):
            try:
                pricing_suite = ExperimentSuite.model_validate(
                    execution_plan["suite"]
                )
                pricing_freshness = _pricing_freshness_evidence(
                    pricing_suite,
                    boundary_at=run_started[0].timestamp,
                )
                pricing_suite_valid = True
            except (TypeError, ValueError):
                pricing_suite_valid = False
        add(
            "pricing_start_freshness",
            bool(
                pricing_suite_valid
                and _pricing_freshness_passed(pricing_freshness)
            ),
            run_started_count=len(run_started),
            **pricing_freshness,
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

    private_tokens = _private_leak_tokens(
        package,
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
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
    investigation_artifact_count = 0
    if manifest.context_policy_version in {
        "phase-evidence-v4",
        "phase-evidence-v5",
        "phase-evidence-v6",
        "phase-evidence-v7",
        "phase-evidence-v8",
        "phase-evidence-v9",
        "phase-evidence-v10",
        "phase-evidence-v11",
    }:
        (
            investigation_artifact_integrity,
            investigation_artifact_count,
            investigation_leak_matches,
            _,
            investigation_missing_identities,
        ) = _artifact_evidence(
            root=run_root,
            events=events,
            private_tokens=private_tokens,
            event_types={
                EventType.TOOL_REPLAYED,
                EventType.TOOL_ADMISSION_BLOCKED,
            },
            required_event_types={
                EventType.TOOL_REPLAYED,
                EventType.TOOL_ADMISSION_BLOCKED,
            },
        )
        artifact_integrity = bool(
            artifact_integrity and investigation_artifact_integrity
        )
        artifact_count += investigation_artifact_count
        leak_matches += investigation_leak_matches
        missing_artifact_identities.extend(
            investigation_missing_identities
        )
        (
            admission_input_integrity,
            admission_input_count,
            admission_input_leak_matches,
            _,
            admission_input_missing,
        ) = _v4_admission_nested_artifact_evidence(
            root=run_root,
            events=events,
            private_tokens=private_tokens,
        )
        artifact_integrity = bool(
            artifact_integrity and admission_input_integrity
        )
        investigation_artifact_count += admission_input_count
        artifact_count += admission_input_count
        leak_matches += admission_input_leak_matches
        missing_artifact_identities.extend(admission_input_missing)
    accepted_patch_artifact_count = 0
    patch_intent_artifact_count = 0
    self_validation_artifact_count = 0
    patch_source_snapshot_artifact_count = 0
    if manifest.tool_schema_version in {"v2", "v3", "v4", "v5", "v6"}:
        (
            accepted_patch_artifact_integrity,
            accepted_patch_artifact_evidence,
        ) = _accepted_patch_artifact_evidence(
            root=run_root,
            events=events,
        )
        artifact_integrity = artifact_integrity and accepted_patch_artifact_integrity
        accepted_patch_artifact_count = len(accepted_patch_artifact_evidence)
        has_patch_prepared = any(event.type == EventType.PATCH_PREPARED for event in events)
        has_patch_applied = any(event.type == EventType.PATCH_APPLIED for event in events)
        patch_intent_required = has_patch_prepared or has_patch_applied
        if patch_intent_required:
            (
                patch_intent_integrity,
                patch_intent_scanned,
                patch_intent_matches,
                patch_intent_evidence,
            ) = _patch_intent_artifact_evidence(
                root=run_root,
                events=events,
                private_tokens=private_tokens,
            )
            artifact_integrity = bool(
                artifact_integrity
                and patch_intent_integrity
                and (not has_patch_applied or has_patch_prepared)
            )
            artifact_count += patch_intent_scanned
            leak_matches += patch_intent_matches
            patch_intent_artifact_count = len(patch_intent_evidence)
    if manifest.tool_schema_version in {"v3", "v4", "v5", "v6"}:
        (
            self_validation_artifact_integrity,
            self_validation_artifact_count,
            self_validation_leak_matches,
            _,
            self_validation_missing,
        ) = _self_validation_nested_artifact_evidence(
            root=run_root,
            events=events,
            private_tokens=private_tokens,
        )
        artifact_integrity = bool(
            artifact_integrity
            and self_validation_artifact_integrity
        )
        artifact_count += self_validation_artifact_count
        leak_matches += self_validation_leak_matches
        missing_artifact_identities.extend(
            self_validation_missing
        )
    if manifest.tool_schema_version in {"v4", "v5", "v6"}:
        (
            patch_source_integrity,
            patch_source_snapshot_artifact_count,
            patch_source_leak_matches,
            _,
            patch_source_missing,
        ) = _patch_source_snapshot_artifact_evidence(
            root=run_root,
            events=events,
            private_tokens=private_tokens,
        )
        artifact_integrity = bool(
            artifact_integrity and patch_source_integrity
        )
        artifact_count += patch_source_snapshot_artifact_count
        leak_matches += patch_source_leak_matches
        missing_artifact_identities.extend(patch_source_missing)
    artifact_details = {
        "scanned_artifact_count": artifact_count,
        "missing_required_artifact_events": missing_artifact_identities,
    }
    if manifest.tool_schema_version in {"v2", "v3", "v4", "v5", "v6"}:
        artifact_details["accepted_patch_artifact_count"] = accepted_patch_artifact_count
        if any(
            event.type in {EventType.PATCH_PREPARED, EventType.PATCH_APPLIED} for event in events
        ):
            artifact_details["patch_intent_artifact_count"] = patch_intent_artifact_count
    if manifest.tool_schema_version in {"v3", "v4", "v5", "v6"}:
        artifact_details[
            "self_validation_nested_artifact_count"
        ] = self_validation_artifact_count
    if manifest.tool_schema_version in {"v4", "v5", "v6"}:
        artifact_details[
            "patch_source_snapshot_artifact_count"
        ] = patch_source_snapshot_artifact_count
    if manifest.context_policy_version in {
        "phase-evidence-v4",
        "phase-evidence-v5",
        "phase-evidence-v6",
        "phase-evidence-v7",
        "phase-evidence-v8",
        "phase-evidence-v9",
        "phase-evidence-v10",
        "phase-evidence-v11",
    }:
        artifact_details[
            "investigation_artifact_count"
        ] = investigation_artifact_count
    add(
        "agent_visible_artifacts",
        artifact_integrity,
        **artifact_details,
    )
    if manifest.context_policy_version in {
        "phase-evidence-v3",
        "phase-evidence-v4",
        "phase-evidence-v5",
        "phase-evidence-v6",
        "phase-evidence-v7",
        "phase-evidence-v8",
        "phase-evidence-v9",
        "phase-evidence-v10",
        "phase-evidence-v11",
    }:
        (
            rejected_patch_retry_context_ok,
            rejected_patch_retry_context_details,
        ) = _rejected_patch_retry_context_evidence(
            root=run_root,
            manifest=manifest,
            events=events,
        )
        add(
            "rejected_patch_retry_context",
            rejected_patch_retry_context_ok,
            **rejected_patch_retry_context_details,
        )
        if controlled_rejection_mode:
            (
                controlled_rejection_ok,
                controlled_rejection_details,
            ) = _controlled_rejection_evidence(
                manifest=manifest,
                events=events,
            )
            rejected_patch_retry_context_details.update(
                controlled_rejection_details
            )
            checks[-1]["details"].update(
                controlled_rejection_details
            )
            add(
                "controlled_diagnostic_boundary",
                controlled_rejection_ok,
                fault=manifest.fault.type,
                trigger_after=manifest.fault.trigger_after,
                **controlled_rejection_details,
            )
    elif controlled_rejection_mode:
        add(
            "controlled_diagnostic_boundary",
            False,
            fault=manifest.fault.type,
            trigger_after=manifest.fault.trigger_after,
            reason="phase-evidence-v3-required",
        )
    verifier_evidence_declared = bool(
        result is not None
        and any(
            "evidence_artifacts" in verifier_result.details
            for verifier_result in result.verifier_results
        )
    )
    evaluation_receipt_path = run_root / "artifacts" / "runs" / run_id / "evaluation-receipt.json"
    if verifier_evidence_declared or evaluation_receipt_path.exists():
        (
            verifier_artifact_integrity,
            verifier_artifact_evidence,
        ) = _verifier_artifact_evidence(
            root=run_root,
            result=result,
            required=True,
        )
        (
            evaluation_receipt_integrity,
            evaluation_receipt_evidence,
        ) = _evaluation_receipt_evidence(
            root=run_root,
            run_id=run_id,
            manifest=manifest,
            result=result,
        )
        add(
            "verifier_evidence_artifacts",
            verifier_artifact_integrity and evaluation_receipt_integrity,
            evidence_artifact_count=len(verifier_artifact_evidence),
            evaluation_receipt_present=evaluation_receipt_path.is_file(),
            evaluation_receipt_content_hash=(
                evaluation_receipt_evidence.get("receipt_content_hash")
            ),
        )
    leakage_ok = leak_matches == 0
    add("public_private_boundary", leakage_ok, private_match_count=leak_matches)

    model_events = [event for event in events if event.type == EventType.MODEL_CALLED]
    tool_events = [event for event in events if event.type == EventType.TOOL_CALLED]
    context_events = [event for event in events if event.type == EventType.CONTEXT_BUILT]
    if manifest.context_policy_version in {
        "phase-evidence-v4",
        "phase-evidence-v5",
        "phase-evidence-v6",
        "phase-evidence-v7",
        "phase-evidence-v8",
        "phase-evidence-v9",
        "phase-evidence-v10",
        "phase-evidence-v11",
    }:
        (
            investigation_evidence_ok,
            investigation_evidence_details,
        ) = _v4_investigation_context_evidence(
            root=run_root,
            manifest=manifest,
            package=package,
            events=events,
            checkpoints=checkpoints,
            context_events=context_events,
        )
        add(
            "investigation_evidence",
            investigation_evidence_ok,
            **investigation_evidence_details,
        )
        (
            investigation_lifecycle_ok,
            investigation_lifecycle_details,
        ) = _v4_investigation_lifecycle_evidence(
            root=run_root,
            manifest=manifest,
            package=package,
            events=events,
        )
        add(
            "investigation_lifecycle",
            investigation_lifecycle_ok,
            **investigation_lifecycle_details,
        )
        if manifest.context_policy_version in {
            "phase-evidence-v8",
            "phase-evidence-v9",
            "phase-evidence-v10",
            "phase-evidence-v11",
        }:
            (
                saturation_context_ok,
                saturation_context_details,
            ) = _v8_saturation_context_evidence(
                root=run_root,
                manifest=manifest,
                package=package,
                events=events,
                checkpoints=checkpoints,
                context_events=context_events,
            )
            add(
                "saturation_context_contract",
                saturation_context_ok,
                **saturation_context_details,
            )
        if manifest.context_policy_version == "phase-evidence-v9":
            (
                review_evidence_context_ok,
                review_evidence_context_details,
            ) = _v9_review_evidence_context_contract(
                root=run_root,
                manifest=manifest,
                package=package,
                events=events,
                context_events=context_events,
            )
            add(
                "review_evidence_context_contract",
                review_evidence_context_ok,
                **review_evidence_context_details,
            )
            (
                review_rejection_terminal_ok,
                review_rejection_terminal_details,
            ) = _v9_review_rejection_terminal_contract(events)
            add(
                "review_rejection_terminal_contract",
                review_rejection_terminal_ok,
                **review_rejection_terminal_details,
            )
        if manifest.context_policy_version in {
            "phase-evidence-v10",
            "phase-evidence-v11",
        }:
            (
                coverage_decision_ok,
                coverage_decision_details,
            ) = _v10_coverage_decision_evidence(
                root=run_root,
                manifest=manifest,
                package=package,
                events=events,
                context_events=context_events,
            )
            add(
                "coverage_decision_integrity",
                coverage_decision_ok,
                **coverage_decision_details,
            )
            (
                coverage_submission_ok,
                coverage_submission_details,
            ) = _v10_coverage_submission_evidence(
                root=run_root,
                manifest=manifest,
                events=events,
                context_events=context_events,
                result=result,
            )
            add(
                "coverage_submission_lifecycle",
                coverage_submission_ok,
                **coverage_submission_details,
            )
            (
                coverage_recovery_ok,
                coverage_recovery_details,
            ) = _v10_coverage_recovery_evidence(events)
            add(
                "coverage_recovery_contract",
                coverage_recovery_ok,
                **coverage_recovery_details,
            )
            (
                coverage_terminal_ok,
                coverage_terminal_details,
            ) = _v10_coverage_terminal_evidence(
                events=events,
                result=result,
            )
            add(
                "coverage_terminal_contract",
                coverage_terminal_ok,
                **coverage_terminal_details,
            )
            if manifest.context_policy_version == "phase-evidence-v11":
                (
                    coverage_rejection_recovery_ok,
                    coverage_rejection_recovery_details,
                ) = _v11_coverage_rejection_recovery_evidence(
                    root=run_root,
                    manifest=manifest,
                    package=package,
                    events=events,
                    context_events=context_events,
                    worker_claims=worker_claims,
                )
                add(
                    "coverage_rejection_recovery_contract",
                    coverage_rejection_recovery_ok,
                    **coverage_rejection_recovery_details,
                )
    if manifest.tool_schema_version in {"v4", "v5", "v6"}:
        (
            mutation_barrier_ok,
            mutation_barrier_details,
        ) = _v7_turn_mutation_barrier_evidence(
            root=run_root,
            events=events,
        )
        add(
            "turn_mutation_barrier",
            mutation_barrier_ok,
            **mutation_barrier_details,
        )
    generation_blocked_events = [
        event for event in events if event.type == EventType.MODEL_GENERATION_BLOCKED
    ]
    versioned_generation_block_declared = any(
        event.payload.get("schema_version")
        in {
            _EXACT_REQUEST_GENERATION_BLOCK_SCHEMA,
            _COUNTER_GENERATION_BLOCK_SCHEMA,
        }
        for event in generation_blocked_events
    )
    terminal_generation_block_ok = False
    terminal_generation_block_kind: str | None = None
    if (
        manifest.context_policy_version
        in {
            "phase-evidence-v3",
            "phase-evidence-v4",
            "phase-evidence-v5",
            "phase-evidence-v6",
            "phase-evidence-v7",
            "phase-evidence-v8",
            "phase-evidence-v9",
        }
        and len(generation_blocked_events) == 1
        and context_events
    ):
        blocked_event = generation_blocked_events[0]
        blocked_context = context_events[-1]
        candidate_hash = blocked_event.payload.get("retry_candidate_content_hash")
        retry_context_present = blocked_event.payload.get(
            "retry_context_present"
        )
        expected_retry_candidate_hash = (
            candidate_hash
            if retry_context_present is True and isinstance(candidate_hash, str)
            else None
        )
        retry_mode_shape_valid = bool(
            (
                retry_context_present is True
                and isinstance(candidate_hash, str)
            )
            or (
                retry_context_present is False
                and candidate_hash is None
            )
        )
        retry_source_binding_valid = bool(
            retry_context_present is not True
            or (
                rejected_patch_retry_context_ok
                and rejected_patch_retry_context_details.get(
                    "retry_episode_count"
                )
                >= 1
                and rejected_patch_retry_context_details.get(
                    "model_generation_blocked_count"
                )
                == 1
                and candidate_hash
                in rejected_patch_retry_context_details.get(
                    "verified_candidate_content_hashes",
                    [],
                )
                and not rejected_patch_retry_context_details.get(
                    "failed_source_failure_sequences"
                )
            )
        )
        terminal_generation_block_ok = bool(
            retry_mode_shape_valid
            and retry_source_binding_valid
            and _model_generation_block_valid(
                root=run_root,
                manifest=manifest,
                events=events,
                context_event=blocked_context,
                blocked_event=blocked_event,
                expected_retry_candidate_hash=(
                    expected_retry_candidate_hash
                ),
            )
            and not any(event.sequence > blocked_context.sequence for event in model_events)
            and all(event.sequence < blocked_event.sequence for event in context_events[:-1])
        )
        if terminal_generation_block_ok:
            terminal_generation_block_kind = (
                "rejected_patch_retry"
                if retry_context_present is True
                else "generic"
            )
    model_telemetry_declared = any(
        event.payload.get("prompt_telemetry_version") is not None for event in model_events
    )
    terminal_block_telemetry_declared = terminal_generation_block_ok
    telemetry_declared = bool(
        model_telemetry_declared or terminal_block_telemetry_declared
    )
    telemetry_contract_required = bool(
        experiment is not None
        and (
            experiment.purpose
            in {
                ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT,
                ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY,
                ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_BUDGET_PILOT,
                ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT,
                ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT,
                ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT,
                ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT,
                ExperimentPurpose.CORE,
            }
            or (
                experiment.purpose
                == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT
                and manifest.model.model_id == _GPT54_MINI_PILOT_MODEL_ID
            )
        )
    )
    telemetry_required = telemetry_contract_required or telemetry_declared
    prompt_telemetry_ok = not telemetry_required or telemetry_declared
    prompt_telemetry_failures: list[int] = []
    if telemetry_declared:
        matched_context_events = (
            context_events[:-1] if terminal_generation_block_ok else context_events
        )
        prompt_telemetry_ok = bool(
            len(matched_context_events) == len(model_events)
            and (
                not generation_blocked_events
                or terminal_generation_block_ok
            )
        )
        for index, model_event in enumerate(model_events):
            payload = model_event.payload
            context_event = (
                matched_context_events[index] if index < len(matched_context_events) else None
            )
            requested_input_tokens = payload.get("requested_input_tokens")
            input_tokens = int(payload.get("input_tokens", 0))
            output_tokens = int(payload.get("output_tokens", 0))
            total_tokens = payload.get("total_tokens")
            reasoning_tokens = int(payload.get("reasoning_output_tokens", 0))
            event_ok = bool(
                payload.get("prompt_telemetry_version") == "prompt-token-integrity-v1"
                and isinstance(requested_input_tokens, int)
                and requested_input_tokens == input_tokens
                and payload.get("input_token_count_match") is True
                and payload.get("input_token_count_calls") == 1
                and isinstance(total_tokens, int)
                and total_tokens == input_tokens + output_tokens
                and payload.get("total_token_count_match") is True
                and reasoning_tokens <= output_tokens
                and payload.get("response_status") == "completed"
                and payload.get("response_truncation") == "disabled"
                and payload.get("response_incomplete_reason") is None
                and payload.get("response_model") == manifest.model.model_id
                and context_event is not None
                and payload.get("request_artifact_id") == context_event.payload.get("artifact_id")
                and payload.get("request_artifact_path")
                == context_event.payload.get("artifact_path")
                and payload.get("request_body_hash")
                == context_event.payload.get("request_body_hash")
            )
            if not event_ok:
                prompt_telemetry_ok = False
                prompt_telemetry_failures.append(model_event.sequence)
    elif telemetry_contract_required:
        prompt_telemetry_failures.extend(event.sequence for event in model_events)
    prompt_telemetry_details: dict[str, Any] = {
        "required": telemetry_required,
        "declared": telemetry_declared,
        "model_event_count": len(model_events),
        "failed_event_sequences": prompt_telemetry_failures,
    }
    if manifest.context_policy_version in {
        "phase-evidence-v3",
        "phase-evidence-v4",
        "phase-evidence-v5",
        "phase-evidence-v6",
        "phase-evidence-v7",
        "phase-evidence-v8",
        "phase-evidence-v9",
        "phase-evidence-v10",
        "phase-evidence-v11",
    }:
        prompt_telemetry_details.update(
            {
                "model_generation_blocked_count": len(generation_blocked_events),
                "terminal_generation_block_valid": (terminal_generation_block_ok),
            }
        )
        if versioned_generation_block_declared:
            prompt_telemetry_details[
                "terminal_generation_block_kind"
            ] = terminal_generation_block_kind
            prompt_telemetry_details[
                "terminal_generation_block_schema_version"
            ] = generation_blocked_events[0].payload.get(
                "schema_version"
            )
            prompt_telemetry_details[
                "terminal_generation_block_reason"
            ] = generation_blocked_events[0].payload.get("reason_code")
    add(
        "prompt_token_integrity",
        prompt_telemetry_ok,
        **prompt_telemetry_details,
    )

    expected_usage = {
        "input_tokens": sum(int(event.payload.get("input_tokens", 0)) for event in model_events),
        "cached_input_tokens": sum(
            int(event.payload.get("cached_input_tokens", 0)) for event in model_events
        ),
        "cache_write_input_tokens": sum(
            int(event.payload.get("cache_write_input_tokens", 0)) for event in model_events
        ),
        "output_tokens": sum(int(event.payload.get("output_tokens", 0)) for event in model_events),
        "reasoning_output_tokens": sum(
            int(event.payload.get("reasoning_output_tokens", 0)) for event in model_events
        ),
        "model_calls": len(model_events),
        "input_token_count_calls": sum(
            int(event.payload.get("input_token_count_calls", 0)) for event in model_events
        )
        + sum(
            int(event.payload.get("input_token_count_calls", 0))
            for event in generation_blocked_events
        ),
        "tool_calls": len(tool_events),
    }
    counter_usage_required = bool(
        len(generation_blocked_events) == 1
        and generation_blocked_events[0].payload.get("schema_version")
        == _COUNTER_GENERATION_BLOCK_SCHEMA
    )
    counter_usage = (
        _budget_usage_before(
            events,
            generation_blocked_events[0].sequence,
        )
        if counter_usage_required
        else None
    )
    if counter_usage is not None:
        expected_usage["wall_clock_ms"] = counter_usage["wall_clock_ms"]
    usage_matches = bool(
        result is not None
        and (not counter_usage_required or counter_usage is not None)
        and all(getattr(result.usage, field) == value for field, value in expected_usage.items())
        and abs(result.usage.model_cost_usd - calculate_model_cost(result.usage, manifest.model))
        <= 1e-9
    )
    add(
        "usage_reconciliation",
        usage_matches,
        model_event_count=len(model_events),
        tool_event_count=len(tool_events),
    )

    persisted_result_path = run_root / "artifacts" / "runs" / run_id / "result.json"
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

    pilot_purposes = {
        ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT,
        ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT,
    }
    pilot_tool_ok = bool(
        experiment is None or experiment.purpose not in pilot_purposes or tool_events
    )
    add(
        "pilot_tool_loop",
        pilot_tool_ok,
        required=bool(experiment is not None and experiment.purpose in pilot_purposes),
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
    generation_block_contract_declared = any(
        "schema_version" in event.payload
        for event in generation_blocked_events
    )
    generation_block_terminal_binding_required = bool(
        terminal_generation_block_ok
        or generation_block_contract_declared
    )
    generation_block_terminal_binding_ok = True
    if generation_block_terminal_binding_required:
        blocked_event = (
            generation_blocked_events[0]
            if len(generation_blocked_events) == 1
            else None
        )
        terminal_event = terminals[0] if len(terminals) == 1 else None
        terminal_error = (
            result.terminal_error
            if result is not None and isinstance(result.terminal_error, dict)
            else None
        )
        expected_details = (
            blocked_event.payload
            if blocked_event is not None
            else None
        )
        generation_block_terminal_binding_ok = bool(
            terminal_generation_block_ok
            and blocked_event is not None
            and result is not None
            and result.outcome_kind == RunOutcomeKind.AGENT_FAILURE
            and terminal_event is not None
            and terminal_event.type == EventType.RUN_FAILED
            and terminal_error is not None
            and terminal_error.get("type") == "ModelGenerationBudgetError"
            and terminal_error.get("code") == "MODEL_GENERATION_BUDGET_EXCEEDED"
            and terminal_error.get("details") == expected_details
            and isinstance(terminal_error.get("message"), str)
            and terminal_event.payload.get("error_type")
            == "ModelGenerationBudgetError"
            and terminal_event.payload.get("error_code")
            == "MODEL_GENERATION_BUDGET_EXCEEDED"
            and terminal_event.payload.get("error_details") == expected_details
            and terminal_event.payload.get("message")
            == terminal_error.get("message")
        )
        evaluation_ok = evaluation_ok and generation_block_terminal_binding_ok
    terminal_result_details: dict[str, Any] = {
        "result_present": result is not None,
        "evaluation_reached": evaluation_reached,
        "official": bool(result is not None and result.official),
        "verdicts_terminal": terminal_verdicts,
    }
    if generation_blocked_events:
        terminal_result_details.update(
            {
                "model_generation_block_binding_required": (
                    generation_block_terminal_binding_required
                ),
                "model_generation_block_binding_valid": (
                    generation_block_terminal_binding_ok
                ),
            }
        )
    add(
        "terminal_result_integrity",
        evaluation_ok,
        **terminal_result_details,
    )

    outcome = result.outcome_kind if result is not None else RunOutcomeKind.INFRASTRUCTURE_ERROR
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
            len(records) == 1 and len(tagged_ids) == 1 and tagged_ids[0] == records[0].failure_id
        )
    else:
        failure_linked = not records and not tagged_ids
    failure_record_id = records[0].failure_id if len(records) == 1 else None
    failure_record_hash = (
        sha256_bytes(
            (
                run_root / "failures" / package.public.split / f"{failure_record_id}.json"
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
        "verifier_evidence_artifacts",
        "prompt_token_integrity",
        "usage_reconciliation",
        "persisted_result",
        "pilot_tool_loop",
        "terminal_result_integrity",
        "failure_record_linkage",
    }
    if structured_lifecycle_contract:
        trace_check_ids.add("submission_lifecycle")
        trace_check_ids.add("worker_claim_provenance")
    if manifest.tool_schema_version in {"v3", "v4", "v5", "v6"}:
        trace_check_ids.add("self_validation_lifecycle")
    if manifest.tool_schema_version == "v4":
        trace_check_ids.add("public_review_contract")
        trace_check_ids.add("corrective_runtime_contract")
        trace_check_ids.add("pricing_start_freshness")
        trace_check_ids.add("turn_mutation_barrier")
    if manifest.tool_schema_version == "v5":
        trace_check_ids.add("public_coverage_contract")
        trace_check_ids.add("corrective_runtime_contract")
        trace_check_ids.add("turn_mutation_barrier")
        if (
            experiment is not None
            and experiment.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT
        ):
            trace_check_ids.add("pricing_start_freshness")
    if manifest.tool_schema_version == "v6":
        trace_check_ids.add("public_coverage_contract")
        trace_check_ids.add("corrective_runtime_contract")
        trace_check_ids.add("turn_mutation_barrier")
        trace_check_ids.add("coverage_rejection_recovery_contract")
    if manifest.context_policy_version in {
        "phase-evidence-v3",
        "phase-evidence-v4",
        "phase-evidence-v5",
        "phase-evidence-v6",
        "phase-evidence-v7",
        "phase-evidence-v8",
        "phase-evidence-v9",
        "phase-evidence-v10",
        "phase-evidence-v11",
    }:
        trace_check_ids.add("rejected_patch_retry_context")
    if manifest.context_policy_version in {
        "phase-evidence-v4",
        "phase-evidence-v5",
        "phase-evidence-v6",
        "phase-evidence-v7",
        "phase-evidence-v8",
        "phase-evidence-v9",
        "phase-evidence-v10",
        "phase-evidence-v11",
    }:
        trace_check_ids.add("investigation_evidence")
        trace_check_ids.add("investigation_lifecycle")
    if manifest.context_policy_version in {
        "phase-evidence-v8",
        "phase-evidence-v9",
        "phase-evidence-v10",
        "phase-evidence-v11",
    }:
        trace_check_ids.add("saturation_context_contract")
    if manifest.context_policy_version == "phase-evidence-v9":
        trace_check_ids.add("review_evidence_context_contract")
        trace_check_ids.add("review_rejection_terminal_contract")
    if manifest.context_policy_version in {
        "phase-evidence-v10",
        "phase-evidence-v11",
    }:
        trace_check_ids.update(
            {
                "coverage_decision_integrity",
                "coverage_submission_lifecycle",
                "coverage_recovery_contract",
                "coverage_terminal_contract",
            }
        )
    if controlled_rejection_mode:
        trace_check_ids.add("controlled_diagnostic_boundary")
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
        "schema_version": (
            QUALIFICATION_SCHEMA_VERSION
            if structured_lifecycle_contract
            else LEGACY_QUALIFICATION_SCHEMA_VERSION
        ),
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
    if structured_lifecycle_contract:
        payload.update(
            {
                "model_id": manifest.model.model_id,
                "reasoning_effort": manifest.model.reasoning_effort,
                "reasoning_mode": manifest.model.reasoning_mode,
                "service_tier": manifest.model.service_tier,
                "max_output_tokens": manifest.model.max_output_tokens,
                "budget": manifest.budget.model_dump(mode="json"),
                "harness_git_commit": manifest.harness_git_commit,
                "tool_schema_version": manifest.tool_schema_version,
                "context_policy_version": manifest.context_policy_version,
                "runtime_contract_content_hash": (
                    corrective_runtime_content_hash
                    if manifest.tool_schema_version in {"v4", "v5", "v6"}
                    else _runtime_contract_content_hash(events)
                ),
            }
        )
    payload["qualification_hash"] = sha256_text(canonical_json(payload))

    if not persist:
        return payload

    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    if path.exists():
        existing = load_trace_qualification(run_id, root=run_root)
        if (
            _normalized_qualification_semantics(existing)
            != _normalized_qualification_semantics(payload)
        ):
            raise ContractError(f"trace qualification is immutable: {run_id}")
        return existing
    else:
        path.write_text(encoded, encoding="utf-8")
    return payload
