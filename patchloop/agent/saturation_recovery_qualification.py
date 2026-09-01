"""Public-development threshold qualification for Lean Harness V1.

This module reads only the exact R8 public-development evidence index and the
already-bound main SQLite snapshot.  It projects agent-visible lifecycle
metadata, freezes condition-neutral candidate thresholds, and grants no
runtime or provider authority.  The projection is deliberately separate from
``AgentRunner`` so that a later no-call admission shadow must qualify the seam
before any live integration.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.finalization import (
    R8_DEVELOPMENT_EVIDENCE_FILE_BYTES,
    R8_DEVELOPMENT_EVIDENCE_FILE_SHA256,
    R8_DEVELOPMENT_EVIDENCE_PATH,
    R8_FINALIZATION_RESERVE_ARTIFACT_FILE_BYTES,
    R8_FINALIZATION_RESERVE_ARTIFACT_FILE_SHA256,
    R8_FINALIZATION_RESERVE_ARTIFACT_PATH,
    R8_TRACE_SNAPSHOT_FILE_BYTES,
    R8_TRACE_SNAPSHOT_FILE_SHA256,
    R8_TRACE_SNAPSHOT_PATH,
)
from patchloop.agent.investigation import (
    EVIDENCE_SATURATION_THRESHOLD,
    NO_PROGRESS_STRATEGY_THRESHOLD,
)
from patchloop.agent.tools import (
    _EVIDENCE_SATURATION_THRESHOLD as TOOL_GATEWAY_SATURATION_THRESHOLD,
)
from patchloop.errors import RecoveryError
from patchloop.util import ensure_within, sha256_bytes, sha256_json

QUALIFICATION_SCHEMA = "lean-harness-saturation-recovery-public-qualification-v1"
QUALIFICATION_ID = "lean-harness-saturation-recovery-public-20260816-v1"
QUALIFICATION_PATH = (
    "experiments/lean-harness-saturation-recovery-public-qualification-20260816-v1.json"
)

COMPACTED_SHADOW_PATH = (
    "experiments/lean-harness-compacted-shadow-public-qualification-20260816-v1.json"
)
COMPACTED_SHADOW_BYTES = 52_449
COMPACTED_SHADOW_FILE_SHA256 = (
    "sha256:c26a8318d0f3ba5d132c003398a97d83eef317b8192021c9fd81b6266dbcbbe1"
)
COMPACTED_SHADOW_CONTENT_HASH = (
    "sha256:566589fe6ecc246bfa31720c141b321e13b6764de37cc80fa8be0dee1f59e8c5"
)
FINALIZATION_RESERVE_CONTENT_HASH = (
    "sha256:9458bb1d59d51aaf94a082504a3883d799bf4d807ce7a83376bdc391ab6348db"
)
R8_EVIDENCE_CONTENT_HASH = "sha256:0ef31d2b27a7601800d4352e352f67262e462f19b5c2aef25d1d3f0106aade83"

SOURCE_PATHS = (
    "patchloop/agent/context.py",
    "patchloop/agent/finalization.py",
    "patchloop/agent/investigation.py",
    "patchloop/agent/saturation_recovery_qualification.py",
    "patchloop/agent/structured_edit.py",
    "patchloop/agent/tools.py",
    "patchloop/errors.py",
    "patchloop/util.py",
    "scripts/build_lean_harness_saturation_recovery_qualification.py",
)
VALIDATION_PATHS = (
    "tests/test_finalization.py",
    "tests/test_saturation_recovery_qualification.py",
    "tests/test_structured_edit.py",
    "tests/test_structured_edit_replay.py",
    "tests/test_tool_gateway.py",
)

RUN_FRAME = (
    (
        "run_5a3113600554429e",
        "moto-query-scanned-count",
        "no_memory",
    ),
    (
        "run_69f76b4948af4d9d",
        "moto-query-scanned-count",
        "structured",
    ),
    (
        "run_d10f4197b45342d5",
        "babel-strict-grouped-decimal-trailing-zeroes",
        "structured",
    ),
    (
        "run_cc33bef38c8a42d0",
        "babel-strict-grouped-decimal-trailing-zeroes",
        "no_memory",
    ),
)
RUN_PROJECTION_FRAME = (
    (
        "run_5a3113600554429e",
        20,
        "sha256:d3cfe84c92cbaa2e9aaa1a7ac6891409a9f7a50e4980beb50d914a42dcc429fe",
    ),
    (
        "run_69f76b4948af4d9d",
        10,
        "sha256:f2df6074fe0cec88096807c341e6fef89726ce32f3f4a49ae5fbfd8cff114d6c",
    ),
    (
        "run_d10f4197b45342d5",
        9,
        "sha256:7830389c603ee85de3609cf7caace077d4a7766dea687d8e910cb2b38fa88755",
    ),
    (
        "run_cc33bef38c8a42d0",
        14,
        "sha256:717add6766d8cab6c722684979dbfaf632095653ebb554ad558f4c8d89ebe420",
    ),
)

Condition = Literal["no_memory", "structured"]


class FileBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    file_bytes: int = Field(gt=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class ArtifactBinding(FileBinding):
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class TraceSnapshotBinding(FileBinding):
    checked_in: Literal[False]
    wal_bytes_at_projection: Literal[0]
    read_contract: Literal["sqlite-main-db-immutable-read-v1"]
    source_metadata_unchanged_during_read: Literal[True]


class ThresholdRunObservation(BaseModel):
    """Sanitized agent-visible lifecycle statistics for one resolved row."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    order: int = Field(ge=1, le=4)
    run_id: str = Field(pattern=r"^run_[0-9a-f]{16}$")
    task_id: str = Field(min_length=1)
    condition: Condition
    outcome_kind: Literal["resolved"]
    trace_qualified: Literal[True]
    event_count: int = Field(gt=0)
    semantic_replay_count: int = Field(ge=0)
    semantic_replay_sequences: tuple[int, ...]
    semantic_replay_tools: tuple[Literal["read_file", "search_files"], ...]
    max_semantic_replays_in_one_mutation_epoch: int = Field(ge=0)
    loop_detection_count: int = Field(ge=0)
    max_no_progress_streak: int = Field(ge=0)
    strategy_change_required_count: int = Field(ge=0)
    rejected_patch_count: int = Field(ge=0)
    rejected_patch_sequences: tuple[int, ...]
    max_consecutive_patch_rejections: int = Field(ge=0)
    successful_mutation_count: int = Field(ge=1)
    first_recovery_mutation_sequence: int | None
    model_turns_from_rejection_to_recovery: int = Field(ge=0)
    selected_event_projection_count: int = Field(gt=0)
    selected_event_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        if self.semantic_replay_count != len(self.semantic_replay_sequences) or (
            self.semantic_replay_count != len(self.semantic_replay_tools)
        ):
            raise ValueError("semantic replay observation differs")
        if tuple(sorted(self.semantic_replay_sequences)) != self.semantic_replay_sequences:
            raise ValueError("semantic replay sequences must be increasing")
        if self.rejected_patch_count != len(self.rejected_patch_sequences):
            raise ValueError("rejected patch observation differs")
        if tuple(sorted(self.rejected_patch_sequences)) != self.rejected_patch_sequences:
            raise ValueError("rejected patch sequences must be increasing")
        if self.max_semantic_replays_in_one_mutation_epoch > self.semantic_replay_count:
            raise ValueError("mutation-epoch replay maximum exceeds total")
        if self.strategy_change_required_count > self.loop_detection_count:
            raise ValueError("strategy-change count exceeds loop detections")
        if self.max_consecutive_patch_rejections > self.rejected_patch_count:
            raise ValueError("consecutive rejection maximum exceeds total")
        has_rejection = self.rejected_patch_count > 0
        if has_rejection != (self.first_recovery_mutation_sequence is not None):
            raise ValueError("patch rejection recovery evidence is incomplete")
        if has_rejection != (self.model_turns_from_rejection_to_recovery > 0):
            raise ValueError("patch rejection recovery turn count differs")
        return self


class SaturationRecoveryPublicQualification(BaseModel):
    """Closed public-development qualification for future policy thresholds."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-saturation-recovery-public-qualification-v1"]
    qualification_id: Literal["lean-harness-saturation-recovery-public-20260816-v1"]
    status: Literal["PUBLIC_THRESHOLDS_FROZEN_RUNTIME_CLOSED"]
    evidence_date: Literal["2026-08-16"]
    evidence_scope: Literal["r8-public-development-agent-visible-lifecycle-metadata"]
    r16_outcomes_used_for_threshold_selection: Literal[False]
    heldout_task_files_read: Literal[0]
    private_task_files_read: Literal[0]
    hidden_files_read: Literal[0]
    reference_patches_read: Literal[0]
    predecessor_compacted_shadow: ArtifactBinding
    predecessor_finalization_reserve: ArtifactBinding
    r8_development_evidence: ArtifactBinding
    trace_snapshot: TraceSnapshotBinding
    trace_snapshot_replayable_from_checked_in_files: Literal[False]
    source_tool_schema_version: Literal["v2"]
    source_context_policy_version: Literal["phase-evidence-v5"]
    public_task_count: Literal[2]
    resolved_run_count: Literal[4]
    observations: tuple[ThresholdRunObservation, ...]
    total_event_rows_read: Literal[296]
    selected_event_projection_rows: int = Field(gt=0)
    runs_with_semantic_replay: Literal[1]
    runs_with_patch_rejection: Literal[1]
    observed_max_semantic_replays_per_mutation_epoch: Literal[3]
    observed_max_no_progress_streak: Literal[2]
    observed_max_consecutive_patch_rejections: Literal[1]
    observed_max_recovery_model_turns: Literal[1]
    source_semantic_replay_saturation_threshold: Literal[6]
    source_tool_gateway_saturation_threshold: Literal[6]
    source_no_progress_strategy_threshold: Literal[2]
    candidate_policy_version: Literal["lean-harness-saturation-recovery-v1"]
    candidate_semantic_replay_saturation_threshold: Literal[4]
    candidate_semantic_replay_formula: Literal["public-observed-max-plus-one-v1"]
    candidate_no_progress_strategy_threshold: Literal[2]
    candidate_no_progress_formula: Literal["public-observed-max-v1"]
    candidate_structured_edit_escalation_rejections: Literal[2]
    candidate_patch_escalation_formula: Literal["public-observed-max-plus-one-v1"]
    direct_corrective_patch_retries_before_escalation: Literal[1]
    replay_counter_reset_event: Literal["PatchApplied"]
    rejection_counter_reset_event: Literal["PatchApplied"]
    saturation_blocks_tools: tuple[Literal["read_file", "search_files"], ...]
    saturation_preserves_mutation_and_finalization_tools: Literal[True]
    strategy_change_is_required_not_terminal: Literal[True]
    structured_edit_required_at_escalation: Literal[True]
    freeform_patch_blocked_at_escalation: Literal[True]
    condition_neutral_thresholds: Literal[True]
    observed_success_prefix_preserved: Literal[True]
    threshold_optimality_established: Literal[False]
    provider_token_savings_verified: Literal[False]
    success_effect_verified: Literal[False]
    source_files: tuple[FileBinding, ...]
    validation_files: tuple[FileBinding, ...]
    source_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sqlite_queries: Literal[4]
    provider_transport_calls: Literal[0]
    provider_generation_calls: Literal[0]
    runner_calls: Literal[0]
    docker_calls: Literal[0]
    evaluator_calls: Literal[0]
    added_model_cost_usd: Literal[0]
    provider_calls_authorized: Literal[False]
    runner_activation_authorized: Literal[False]
    tool_policy_activation_authorized: Literal[False]
    state_mutation_authorized: Literal[False]
    paid_execution_authorized: Literal[False]
    next_gate: Literal["bind-frozen-thresholds-to-versioned-no-call-admission-and-recovery-shadow"]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_qualification(self) -> Self:
        if self.predecessor_compacted_shadow != ArtifactBinding(
            path=COMPACTED_SHADOW_PATH,
            file_bytes=COMPACTED_SHADOW_BYTES,
            file_sha256=COMPACTED_SHADOW_FILE_SHA256,
            content_hash=COMPACTED_SHADOW_CONTENT_HASH,
        ):
            raise ValueError("compacted-shadow predecessor differs")
        if self.predecessor_finalization_reserve != ArtifactBinding(
            path=R8_FINALIZATION_RESERVE_ARTIFACT_PATH,
            file_bytes=R8_FINALIZATION_RESERVE_ARTIFACT_FILE_BYTES,
            file_sha256=R8_FINALIZATION_RESERVE_ARTIFACT_FILE_SHA256,
            content_hash=FINALIZATION_RESERVE_CONTENT_HASH,
        ):
            raise ValueError("finalization-reserve predecessor differs")
        if self.r8_development_evidence != ArtifactBinding(
            path=R8_DEVELOPMENT_EVIDENCE_PATH,
            file_bytes=R8_DEVELOPMENT_EVIDENCE_FILE_BYTES,
            file_sha256=R8_DEVELOPMENT_EVIDENCE_FILE_SHA256,
            content_hash=R8_EVIDENCE_CONTENT_HASH,
        ):
            raise ValueError("R8 development evidence differs")
        if self.trace_snapshot != TraceSnapshotBinding(
            path=R8_TRACE_SNAPSHOT_PATH,
            file_bytes=R8_TRACE_SNAPSHOT_FILE_BYTES,
            file_sha256=R8_TRACE_SNAPSHOT_FILE_SHA256,
            checked_in=False,
            wal_bytes_at_projection=0,
            read_contract="sqlite-main-db-immutable-read-v1",
            source_metadata_unchanged_during_read=True,
        ):
            raise ValueError("R8 trace snapshot differs")

        identities = tuple(
            (item.run_id, item.task_id, item.condition) for item in self.observations
        )
        if identities != RUN_FRAME or tuple(item.order for item in self.observations) != (
            1,
            2,
            3,
            4,
        ):
            raise ValueError("public threshold observation frame differs")
        if (
            tuple(
                (
                    item.run_id,
                    item.selected_event_projection_count,
                    item.selected_event_projection_hash,
                )
                for item in self.observations
            )
            != RUN_PROJECTION_FRAME
        ):
            raise ValueError("public selected-event projection frame differs")
        task_conditions: dict[str, set[str]] = {}
        for item in self.observations:
            task_conditions.setdefault(item.task_id, set()).add(item.condition)
        if len(task_conditions) != self.public_task_count or any(
            conditions != {"no_memory", "structured"} for conditions in task_conditions.values()
        ):
            raise ValueError("public threshold evidence is not A/C balanced")

        if self.total_event_rows_read != sum(item.event_count for item in self.observations):
            raise ValueError("event-row total differs")
        if self.selected_event_projection_rows != sum(
            item.selected_event_projection_count for item in self.observations
        ):
            raise ValueError("selected event-row total differs")
        aggregates = (
            sum(item.semantic_replay_count > 0 for item in self.observations),
            sum(item.rejected_patch_count > 0 for item in self.observations),
            max(item.max_semantic_replays_in_one_mutation_epoch for item in self.observations),
            max(item.max_no_progress_streak for item in self.observations),
            max(item.max_consecutive_patch_rejections for item in self.observations),
            max(item.model_turns_from_rejection_to_recovery for item in self.observations),
        )
        if aggregates != (
            self.runs_with_semantic_replay,
            self.runs_with_patch_rejection,
            self.observed_max_semantic_replays_per_mutation_epoch,
            self.observed_max_no_progress_streak,
            self.observed_max_consecutive_patch_rejections,
            self.observed_max_recovery_model_turns,
        ):
            raise ValueError("public threshold aggregates differ")
        if (
            self.source_semantic_replay_saturation_threshold != (EVIDENCE_SATURATION_THRESHOLD)
            or self.source_tool_gateway_saturation_threshold != (TOOL_GATEWAY_SATURATION_THRESHOLD)
            or self.source_no_progress_strategy_threshold != (NO_PROGRESS_STRATEGY_THRESHOLD)
        ):
            raise ValueError("source threshold binding differs")
        if self.candidate_semantic_replay_saturation_threshold != (
            self.observed_max_semantic_replays_per_mutation_epoch + 1
        ):
            raise ValueError("candidate saturation threshold formula differs")
        if self.candidate_no_progress_strategy_threshold != (self.observed_max_no_progress_streak):
            raise ValueError("candidate strategy threshold formula differs")
        if self.candidate_structured_edit_escalation_rejections != (
            self.observed_max_consecutive_patch_rejections + 1
        ):
            raise ValueError("candidate patch escalation formula differs")
        if self.direct_corrective_patch_retries_before_escalation != (
            self.candidate_structured_edit_escalation_rejections - 1
        ):
            raise ValueError("corrective patch retry allowance differs")
        if self.saturation_blocks_tools != ("read_file", "search_files"):
            raise ValueError("saturation tool boundary differs")
        if self.candidate_semantic_replay_saturation_threshold <= (
            self.observed_max_semantic_replays_per_mutation_epoch
        ):
            raise ValueError("candidate saturation would alter the observed prefix")
        if self.candidate_structured_edit_escalation_rejections <= (
            self.observed_max_consecutive_patch_rejections
        ):
            raise ValueError("candidate recovery would alter the observed prefix")

        if (
            tuple(item.path for item in self.source_files) != SOURCE_PATHS
            or tuple(item.path for item in self.validation_files) != VALIDATION_PATHS
        ):
            raise ValueError("qualification file inventory differs")
        if self.source_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.source_files]
        ) or self.validation_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.validation_files]
        ):
            raise ValueError("qualification inventory hash differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("saturation/recovery qualification content hash differs")
        return self


def _repository_root(repository: str | Path) -> Path:
    root = Path(repository).resolve()
    if not (root / "pyproject.toml").is_file():
        raise RecoveryError("saturation/recovery qualification repository is invalid")
    return root


def _reject_duplicate_json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RecoveryError(f"duplicate qualification source key: {key}")
        result[key] = value
    return result


def _file_binding(root: Path, relative: str) -> FileBinding:
    path = ensure_within(root, relative)
    raw = path.read_bytes()
    return FileBinding(
        path=relative,
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
    )


def _artifact_binding(
    root: Path,
    relative: str,
    *,
    expected_bytes: int,
    expected_file_sha256: str,
    expected_content_hash: str,
) -> tuple[ArtifactBinding, dict[str, Any]]:
    raw = ensure_within(root, relative).read_bytes()
    if len(raw) != expected_bytes or sha256_bytes(raw) != expected_file_sha256:
        raise RecoveryError(f"qualification predecessor differs: {relative}")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_json_pairs,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError(f"qualification predecessor is invalid: {relative}") from exc
    if type(value) is not dict or value.get("content_hash") != expected_content_hash:
        raise RecoveryError(f"qualification predecessor content differs: {relative}")
    return (
        ArtifactBinding(
            path=relative,
            file_bytes=len(raw),
            file_sha256=sha256_bytes(raw),
            content_hash=expected_content_hash,
        ),
        value,
    )


def _trace_snapshot_binding(root: Path) -> tuple[TraceSnapshotBinding, tuple[int, int]]:
    path = ensure_within(root, R8_TRACE_SNAPSHOT_PATH)
    before = path.stat()
    raw_hash = sha256_bytes(path.read_bytes())
    if before.st_size != R8_TRACE_SNAPSHOT_FILE_BYTES or (
        raw_hash != R8_TRACE_SNAPSHOT_FILE_SHA256
    ):
        raise RecoveryError("R8 trace snapshot differs")
    wal = Path(str(path) + "-wal")
    wal_bytes = wal.stat().st_size if wal.exists() else 0
    if wal_bytes != 0:
        raise RecoveryError("R8 trace snapshot has authoritative WAL frames")
    return (
        TraceSnapshotBinding(
            path=R8_TRACE_SNAPSHOT_PATH,
            file_bytes=before.st_size,
            file_sha256=raw_hash,
            checked_in=False,
            wal_bytes_at_projection=0,
            read_contract="sqlite-main-db-immutable-read-v1",
            source_metadata_unchanged_during_read=True,
        ),
        (before.st_size, before.st_mtime_ns),
    )


def _safe_selected_projection(event: dict[str, Any]) -> dict[str, Any] | None:
    sequence = event.get("sequence")
    event_type = event.get("type")
    payload = event.get("payload")
    if type(sequence) is not int or type(event_type) is not str or type(payload) is not dict:
        raise RecoveryError("R8 event projection is malformed")
    if event_type == "ModelCalled":
        return {"sequence": sequence, "type": event_type}
    if event_type == "PatchApplied":
        return {
            "sequence": sequence,
            "type": event_type,
            "patch_hash": payload.get("patch_hash"),
            "worktree_diff_hash": payload.get("worktree_diff_hash"),
        }
    if event_type == "LoopDetected":
        return {
            "sequence": sequence,
            "type": event_type,
            "tool": payload.get("tool"),
            "reason_code": payload.get("reason_code"),
            "mutation_epoch_sequence": payload.get("mutation_epoch_sequence"),
            "no_progress_streak": payload.get("no_progress_streak"),
            "occurrences": payload.get("occurrences"),
            "strategy_change_required": payload.get("strategy_change_required"),
        }
    if event_type == "ToolReplayed" and payload.get("semantic_replay") is True:
        return {
            "sequence": sequence,
            "type": event_type,
            "tool": payload.get("tool"),
            "reason_code": payload.get("reason_code"),
            "replay_kind": payload.get("replay_kind"),
            "semantic_replay": True,
            "mutation_epoch_sequence": payload.get("mutation_epoch_sequence"),
        }
    if event_type == "ToolFailed" and payload.get("tool") == "apply_patch":
        return {
            "sequence": sequence,
            "type": event_type,
            "tool": "apply_patch",
            "status": payload.get("status"),
            "error_code": payload.get("error_code"),
        }
    return None


def _run_observation(
    *,
    order: int,
    run_id: str,
    task_id: str,
    condition: Condition,
    row: dict[str, Any],
    event_json_rows: list[str],
) -> ThresholdRunObservation:
    events: list[dict[str, Any]] = []
    for raw in event_json_rows:
        try:
            event = json.loads(raw, object_pairs_hook=_reject_duplicate_json_pairs)
        except json.JSONDecodeError as exc:
            raise RecoveryError("R8 event JSON is invalid") from exc
        if type(event) is not dict or event.get("run_id") != run_id:
            raise RecoveryError("R8 event run identity differs")
        events.append(event)
    sequences = tuple(event.get("sequence") for event in events)
    if (
        any(type(item) is not int for item in sequences)
        or sequences != tuple(sorted(sequences))
        or len(set(sequences)) != len(sequences)
    ):
        raise RecoveryError("R8 event sequences are invalid")

    selected = [
        projection
        for event in events
        if (projection := _safe_selected_projection(event)) is not None
    ]
    semantic = [item for item in selected if item["type"] == "ToolReplayed"]
    loops = [item for item in selected if item["type"] == "LoopDetected"]
    rejections = [item for item in selected if item["type"] == "ToolFailed"]
    mutations = [item for item in selected if item["type"] == "PatchApplied"]
    model_sequences = [item["sequence"] for item in selected if item["type"] == "ModelCalled"]

    epoch_counts: dict[int | None, int] = {}
    active_epoch: int | None = None
    consecutive_rejections = 0
    max_consecutive_rejections = 0
    for item in selected:
        if item["type"] == "ToolReplayed":
            epoch_counts[active_epoch] = epoch_counts.get(active_epoch, 0) + 1
        elif item["type"] == "ToolFailed":
            consecutive_rejections += 1
            max_consecutive_rejections = max(
                max_consecutive_rejections,
                consecutive_rejections,
            )
        elif item["type"] == "PatchApplied":
            active_epoch = item["sequence"]
            consecutive_rejections = 0

    recovery_sequence: int | None = None
    recovery_turns = 0
    if rejections:
        last_rejection = rejections[-1]["sequence"]
        recovery_sequence = next(
            (item["sequence"] for item in mutations if item["sequence"] > last_rejection),
            None,
        )
        if recovery_sequence is None:
            raise RecoveryError("R8 rejected patch lacks a successful recovery mutation")
        recovery_turns = sum(
            last_rejection < sequence < recovery_sequence for sequence in model_sequences
        )

    return ThresholdRunObservation(
        order=order,
        run_id=run_id,
        task_id=task_id,
        condition=condition,
        outcome_kind=row["outcome_kind"],
        trace_qualified=row["trace_qualified"],
        event_count=len(events),
        semantic_replay_count=len(semantic),
        semantic_replay_sequences=tuple(item["sequence"] for item in semantic),
        semantic_replay_tools=tuple(item["tool"] for item in semantic),
        max_semantic_replays_in_one_mutation_epoch=max(
            epoch_counts.values(),
            default=0,
        ),
        loop_detection_count=len(loops),
        max_no_progress_streak=max(
            (item["no_progress_streak"] for item in loops),
            default=0,
        ),
        strategy_change_required_count=sum(
            item["strategy_change_required"] is True for item in loops
        ),
        rejected_patch_count=len(rejections),
        rejected_patch_sequences=tuple(item["sequence"] for item in rejections),
        max_consecutive_patch_rejections=max_consecutive_rejections,
        successful_mutation_count=len(mutations),
        first_recovery_mutation_sequence=recovery_sequence,
        model_turns_from_rejection_to_recovery=recovery_turns,
        selected_event_projection_count=len(selected),
        selected_event_projection_hash=sha256_json(selected),
    )


def build_saturation_recovery_public_qualification(
    repository: str | Path = ".",
) -> SaturationRecoveryPublicQualification:
    root = _repository_root(repository)
    shadow, _ = _artifact_binding(
        root,
        COMPACTED_SHADOW_PATH,
        expected_bytes=COMPACTED_SHADOW_BYTES,
        expected_file_sha256=COMPACTED_SHADOW_FILE_SHA256,
        expected_content_hash=COMPACTED_SHADOW_CONTENT_HASH,
    )
    finalization, _ = _artifact_binding(
        root,
        R8_FINALIZATION_RESERVE_ARTIFACT_PATH,
        expected_bytes=R8_FINALIZATION_RESERVE_ARTIFACT_FILE_BYTES,
        expected_file_sha256=R8_FINALIZATION_RESERVE_ARTIFACT_FILE_SHA256,
        expected_content_hash=FINALIZATION_RESERVE_CONTENT_HASH,
    )
    r8_evidence, evidence = _artifact_binding(
        root,
        R8_DEVELOPMENT_EVIDENCE_PATH,
        expected_bytes=R8_DEVELOPMENT_EVIDENCE_FILE_BYTES,
        expected_file_sha256=R8_DEVELOPMENT_EVIDENCE_FILE_SHA256,
        expected_content_hash=R8_EVIDENCE_CONTENT_HASH,
    )
    rows = evidence.get("rows")
    if type(rows) is not list or len(rows) != len(RUN_FRAME):
        raise RecoveryError("R8 public-development rows are incomplete")
    for row, expected in zip(rows, RUN_FRAME, strict=True):
        if (
            type(row) is not dict
            or (
                row.get("run_id"),
                row.get("task_id"),
                row.get("condition"),
            )
            != expected
        ):
            raise RecoveryError("R8 public-development schedule differs")
        if row.get("outcome_kind") != "resolved" or row.get("trace_qualified") is not True:
            raise RecoveryError("R8 public-development row is not resolved and qualified")

    trace, trace_metadata = _trace_snapshot_binding(root)
    trace_path = ensure_within(root, R8_TRACE_SNAPSHOT_PATH)
    uri = f"file:{trace_path.as_posix()}?mode=ro&immutable=1"
    observations: list[ThresholdRunObservation] = []
    try:
        with sqlite3.connect(uri, uri=True) as connection:
            for order, (row, expected) in enumerate(
                zip(rows, RUN_FRAME, strict=True),
                start=1,
            ):
                raw_events = [
                    item[0]
                    for item in connection.execute(
                        "SELECT event_json FROM events WHERE run_id = ? ORDER BY sequence",
                        (expected[0],),
                    ).fetchall()
                ]
                observations.append(
                    _run_observation(
                        order=order,
                        run_id=expected[0],
                        task_id=expected[1],
                        condition=expected[2],
                        row=row,
                        event_json_rows=raw_events,
                    )
                )
    except sqlite3.Error as exc:
        raise RecoveryError("R8 public trace projection failed") from exc
    after = trace_path.stat()
    if (after.st_size, after.st_mtime_ns) != trace_metadata:
        raise RecoveryError("R8 trace snapshot changed during immutable projection")

    source_files = tuple(_file_binding(root, path) for path in SOURCE_PATHS)
    validation_files = tuple(_file_binding(root, path) for path in VALIDATION_PATHS)
    body: dict[str, Any] = {
        "schema_version": QUALIFICATION_SCHEMA,
        "qualification_id": QUALIFICATION_ID,
        "status": "PUBLIC_THRESHOLDS_FROZEN_RUNTIME_CLOSED",
        "evidence_date": "2026-08-16",
        "evidence_scope": "r8-public-development-agent-visible-lifecycle-metadata",
        "r16_outcomes_used_for_threshold_selection": False,
        "heldout_task_files_read": 0,
        "private_task_files_read": 0,
        "hidden_files_read": 0,
        "reference_patches_read": 0,
        "predecessor_compacted_shadow": shadow.model_dump(mode="python"),
        "predecessor_finalization_reserve": finalization.model_dump(mode="python"),
        "r8_development_evidence": r8_evidence.model_dump(mode="python"),
        "trace_snapshot": trace.model_dump(mode="python"),
        "trace_snapshot_replayable_from_checked_in_files": False,
        "source_tool_schema_version": "v2",
        "source_context_policy_version": "phase-evidence-v5",
        "public_task_count": 2,
        "resolved_run_count": 4,
        "observations": tuple(item.model_dump(mode="python") for item in observations),
        "total_event_rows_read": sum(item.event_count for item in observations),
        "selected_event_projection_rows": sum(
            item.selected_event_projection_count for item in observations
        ),
        "runs_with_semantic_replay": sum(item.semantic_replay_count > 0 for item in observations),
        "runs_with_patch_rejection": sum(item.rejected_patch_count > 0 for item in observations),
        "observed_max_semantic_replays_per_mutation_epoch": max(
            item.max_semantic_replays_in_one_mutation_epoch for item in observations
        ),
        "observed_max_no_progress_streak": max(
            item.max_no_progress_streak for item in observations
        ),
        "observed_max_consecutive_patch_rejections": max(
            item.max_consecutive_patch_rejections for item in observations
        ),
        "observed_max_recovery_model_turns": max(
            item.model_turns_from_rejection_to_recovery for item in observations
        ),
        "source_semantic_replay_saturation_threshold": EVIDENCE_SATURATION_THRESHOLD,
        "source_tool_gateway_saturation_threshold": TOOL_GATEWAY_SATURATION_THRESHOLD,
        "source_no_progress_strategy_threshold": NO_PROGRESS_STRATEGY_THRESHOLD,
        "candidate_policy_version": "lean-harness-saturation-recovery-v1",
        "candidate_semantic_replay_saturation_threshold": 4,
        "candidate_semantic_replay_formula": "public-observed-max-plus-one-v1",
        "candidate_no_progress_strategy_threshold": 2,
        "candidate_no_progress_formula": "public-observed-max-v1",
        "candidate_structured_edit_escalation_rejections": 2,
        "candidate_patch_escalation_formula": "public-observed-max-plus-one-v1",
        "direct_corrective_patch_retries_before_escalation": 1,
        "replay_counter_reset_event": "PatchApplied",
        "rejection_counter_reset_event": "PatchApplied",
        "saturation_blocks_tools": ("read_file", "search_files"),
        "saturation_preserves_mutation_and_finalization_tools": True,
        "strategy_change_is_required_not_terminal": True,
        "structured_edit_required_at_escalation": True,
        "freeform_patch_blocked_at_escalation": True,
        "condition_neutral_thresholds": True,
        "observed_success_prefix_preserved": True,
        "threshold_optimality_established": False,
        "provider_token_savings_verified": False,
        "success_effect_verified": False,
        "source_files": tuple(item.model_dump(mode="python") for item in source_files),
        "validation_files": tuple(item.model_dump(mode="python") for item in validation_files),
        "source_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in source_files]
        ),
        "validation_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in validation_files]
        ),
        "sqlite_queries": 4,
        "provider_transport_calls": 0,
        "provider_generation_calls": 0,
        "runner_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "added_model_cost_usd": 0,
        "provider_calls_authorized": False,
        "runner_activation_authorized": False,
        "tool_policy_activation_authorized": False,
        "state_mutation_authorized": False,
        "paid_execution_authorized": False,
        "next_gate": ("bind-frozen-thresholds-to-versioned-no-call-admission-and-recovery-shadow"),
    }
    return SaturationRecoveryPublicQualification.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )


def qualification_bytes(
    qualification: SaturationRecoveryPublicQualification,
) -> bytes:
    return (
        json.dumps(
            qualification.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def materialize_saturation_recovery_public_qualification(
    repository: str | Path = ".",
    output_path: str | Path = QUALIFICATION_PATH,
) -> SaturationRecoveryPublicQualification:
    root = _repository_root(repository)
    qualification = build_saturation_recovery_public_qualification(root)
    content = qualification_bytes(qualification)
    output = ensure_within(root, str(output_path))
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if output.read_bytes() != content:
            raise RecoveryError("existing saturation/recovery qualification differs")
        return qualification
    with output.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    return qualification


def load_saturation_recovery_public_qualification(
    repository: str | Path = ".",
    path: str | Path = QUALIFICATION_PATH,
) -> SaturationRecoveryPublicQualification:
    root = _repository_root(repository)
    raw = ensure_within(root, str(path)).read_bytes()
    try:
        qualification = SaturationRecoveryPublicQualification.model_validate_json(raw)
    except ValueError as exc:
        raise RecoveryError("saturation/recovery qualification is invalid JSON") from exc
    if qualification_bytes(qualification) != raw:
        raise RecoveryError("saturation/recovery qualification bytes are not canonical")
    expected = build_saturation_recovery_public_qualification(root)
    if qualification != expected:
        raise RecoveryError("saturation/recovery qualification differs from source")
    return qualification
