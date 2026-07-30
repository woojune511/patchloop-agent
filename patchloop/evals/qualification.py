"""Deterministic qualification of live no-memory development traces."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Artifact,
    Budget,
    DatasetRole,
    EventType,
    ExperimentPurpose,
    FailureRecord,
    MemoryCondition,
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
_GPT54_MINI_CAMPAIGN_BUDGET = Budget(
    max_model_calls=21,
    max_total_tokens=200_000,
)
_HISTORICAL_MINI_CAMPAIGN_EXPERIMENT_IDS = frozenset(
    {"dev-validation-gpt54mini-campaign-20260730-r1"}
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
            _diagnostic_fault,
            _execution_hash,
            _suite_hash,
            _suite_payload,
        )

        parsed_suite = ExperimentSuite.model_validate(suite)
        normalized_suite = _suite_payload(parsed_suite)
        expected_execution_hash = _execution_hash(
            parsed_suite,
            dataset=dataset,
            task_rows=tasks,
            schedule_hash=schedule_hash,
            git_state=environment["git"],
            docker_state=environment["docker"],
            openai_sdk=environment["openai_sdk"],
            pilot_qualification=pilot_qualification,
        )
    except (ImportError, TypeError, ValueError):
        return False
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
            role="investigation-admission-input",
            descriptor=event.payload.get("input_artifact"),
        )
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
    """Recompute every v4 investigation ledger from its durable prefix."""

    from patchloop.agent.context import build_context_with_evidence

    artifact_root = root / "artifacts"
    artifact_store = ArtifactStore(artifact_root)
    checkpoints_by_id = {
        checkpoint.checkpoint_id: checkpoint
        for checkpoint in checkpoints
    }
    failed_sequences: list[int] = []
    verified_hashes: list[str] = []
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
                != "context-build-evidence-v4"
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
                policy_version="phase-evidence-v4",
                artifact_store=artifact_store,
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
    ]
    reserve = nominal_tail_reserve(package.public)
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
        reason_codes = []
        if remaining_tool_calls <= reserve["tool_calls"]:
            reason_codes.append("tool_tail_reserved")
        if remaining_model_calls <= (
            reserve["model_calls"] + reserve["feedback_model_calls"]
        ):
            reason_codes.append("model_tail_reserved")
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
                "policy_version": INVESTIGATION_POLICY_VERSION,
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
            "inspection was not admitted because the nominal corrective "
            "lifecycle tail is reserved; use apply_patch or another "
            "phase-advancing action"
        )
        error_details = {
            "schema_version": TOOL_ADMISSION_SCHEMA,
            "policy_version": INVESTIGATION_POLICY_VERSION,
            "reason_codes": reason_codes,
            "nominal_reserve": reserve,
            "remaining_model_calls": remaining_model_calls,
            "remaining_tool_calls": remaining_tool_calls,
            "guidance": (
                "Use the durable investigation ledger and move to a scoped "
                "patch, registered validation, diff review, or submission."
            ),
        }
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
            "schema_version": TOOL_ADMISSION_SCHEMA,
            "policy_version": INVESTIGATION_POLICY_VERSION,
            "tool": tool,
            "status": "rejected",
            "input_hash": input_hash,
            "normalized_call_hash": normalized_call_hash,
            "worktree_diff_hash": worktree_diff_hash,
            "mutation_epoch_sequence": mutation_epoch(prefix),
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


def _request_runtime_contract_valid(
    request_body: Any,
    manifest: RunManifest,
) -> bool:
    """Bind a no-generation request to the frozen adapter/runtime contract."""

    from patchloop.agent.model import (
        SYSTEM_PROMPT_V1,
        SYSTEM_PROMPT_V2,
        SYSTEM_PROMPT_V3,
    )
    from patchloop.agent.tools import TOOL_SCHEMAS_V1, TOOL_SCHEMAS_V2

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
        and manifest.context_policy_version == "phase-evidence-v4"
    ):
        system_prompt = SYSTEM_PROMPT_V3
        tools = TOOL_SCHEMAS_V2
    else:
        return False

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
            if manifest.context_policy_version == "phase-evidence-v4"
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
                == "phase-evidence-v4"
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
                        == "phase-evidence-v4"
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
) -> tuple[bool, bool]:
    """Validate the request body and prove it contains the full get_diff result."""

    request_valid = False
    complete_source = False
    try:
        request_valid, request_evidence = _request_evidence_payload(
            context_event,
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
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
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
    if manifest.tool_schema_version == "v2":
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

    contiguous = [event.sequence for event in events] == list(range(1, len(events) + 1))
    add("contiguous_events", contiguous, event_count=len(events))
    if manifest.tool_schema_version == "v2":
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
                    expected_provider=(
                        manifest.model.provider
                        if manifest.context_policy_version
                        == "phase-evidence-v4"
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
                not in _HISTORICAL_MINI_CAMPAIGN_EXPERIMENT_IDS
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
    if manifest.context_policy_version == "phase-evidence-v4":
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
    if manifest.tool_schema_version == "v2":
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
    artifact_details = {
        "scanned_artifact_count": artifact_count,
        "missing_required_artifact_events": missing_artifact_identities,
    }
    if manifest.tool_schema_version == "v2":
        artifact_details["accepted_patch_artifact_count"] = accepted_patch_artifact_count
        if any(
            event.type in {EventType.PATCH_PREPARED, EventType.PATCH_APPLIED} for event in events
        ):
            artifact_details["patch_intent_artifact_count"] = patch_intent_artifact_count
    if manifest.context_policy_version == "phase-evidence-v4":
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
    if manifest.context_policy_version == "phase-evidence-v4":
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
        in {"phase-evidence-v3", "phase-evidence-v4"}
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
    if manifest.context_policy_version in {
        "phase-evidence-v3",
        "phase-evidence-v4",
    }:
        trace_check_ids.add("rejected_patch_retry_context")
    if manifest.context_policy_version == "phase-evidence-v4":
        trace_check_ids.add("investigation_evidence")
        trace_check_ids.add("investigation_lifecycle")
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
                "runtime_contract_content_hash": (_runtime_contract_content_hash(events)),
            }
        )
    payload["qualification_hash"] = sha256_text(canonical_json(payload))

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
