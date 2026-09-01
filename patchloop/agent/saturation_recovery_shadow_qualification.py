"""Public synthetic qualification for the 4/2/2 admission shadow.

The frozen R8-derived thresholds are replayed over deterministic public event
prefixes and each current phase tool surface.  The builder reads no task or
runtime state, dispatches no tool, and grants no request or runner authority.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.finalization import (
    project_phase_tool_surface,
    r8_public_development_finalization_reserve,
)
from patchloop.agent.phases import EvidenceState
from patchloop.agent.saturation_recovery_qualification import (
    ArtifactBinding,
    FileBinding,
    SaturationRecoveryPublicQualification,
)
from patchloop.agent.saturation_recovery_qualification import (
    qualification_bytes as threshold_qualification_bytes,
)
from patchloop.agent.saturation_recovery_shadow import (
    SaturationRecoveryAdmissionShadow,
    project_saturation_recovery_admission_shadow,
)
from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.contracts import EventType, RunEvent
from patchloop.errors import RecoveryError
from patchloop.util import ensure_within, sha256_bytes, sha256_json, sha256_text

QUALIFICATION_SCHEMA = "lean-harness-saturation-recovery-shadow-public-qualification-v2"
QUALIFICATION_ID = "lean-harness-saturation-recovery-shadow-public-20260816-v2"
QUALIFICATION_PATH = (
    "experiments/lean-harness-saturation-recovery-shadow-public-qualification-20260816-v2.json"
)

PREDECESSOR_V1_PATH = (
    "experiments/lean-harness-saturation-recovery-shadow-public-qualification-20260816-v1.json"
)
PREDECESSOR_V1_BYTES = 365_372
PREDECESSOR_V1_FILE_SHA256 = (
    "sha256:5b5ffff999fff3927fc0f7288f98548c0668fca0ba295431a5a8012ad4d9cd73"
)
PREDECESSOR_V1_CONTENT_HASH = (
    "sha256:aa16f7ca06769ad964059bb691bd89398fb3ff704227e21f87af4f5b09cad3eb"
)

THRESHOLD_QUALIFICATION_PATH = (
    "experiments/lean-harness-saturation-recovery-public-qualification-20260816-v1.json"
)
THRESHOLD_QUALIFICATION_BYTES = 10_993
THRESHOLD_QUALIFICATION_FILE_SHA256 = (
    "sha256:99b30c828989b1a2cae28bd1412d27a9d4e9514768b22cea8047780792f13d0e"
)
THRESHOLD_QUALIFICATION_CONTENT_HASH = (
    "sha256:f07374bca99d1046c66f7ade6d96caf2bd06cbafe307dcabcad681f473485db6"
)

FRAME_PHASES = (
    "INTAKE",
    "REPRODUCE",
    "PLAN",
    "IMPLEMENT",
    "VERIFY",
    "REVIEW",
)
CONDITIONS = ("no_memory", "structured")
SCENARIOS = (
    "normal",
    "semantic-replay-three",
    "semantic-replay-four",
    "no-progress-one",
    "no-progress-two",
    "patch-rejection-one",
    "patch-rejection-two",
    "combined-restriction",
    "patch-applied-reset",
)
EXPECTED_PHASE_ALLOWED_ACTIONS = {
    "INTAKE": ("apply_patch", "run_check", "read_file", "search_files"),
    "REPRODUCE": ("apply_patch", "run_check", "read_file", "search_files"),
    "PLAN": ("apply_patch", "run_check", "read_file", "search_files"),
    "IMPLEMENT": ("run_check", "apply_patch", "read_file", "search_files"),
    "VERIFY": ("get_diff", "apply_patch", "read_file", "search_files"),
    "REVIEW": ("get_diff", "apply_patch", "read_file", "search_files"),
}
EXPECTED_BOUNDARY_STATE = {
    "normal": (0, 0, 0, "normal"),
    "semantic-replay-three": (3, 0, 0, "normal"),
    "semantic-replay-four": (4, 0, 0, "evidence-saturated"),
    "no-progress-one": (0, 1, 0, "normal"),
    "no-progress-two": (0, 2, 0, "strategy-change-required"),
    "patch-rejection-one": (0, 0, 1, "normal"),
    "patch-rejection-two": (0, 0, 2, "structured-edit-recovery"),
    "combined-restriction": (
        4,
        0,
        2,
        "saturated-structured-edit-recovery",
    ),
    "patch-applied-reset": (0, 0, 0, "normal"),
}

SOURCE_PATHS = (
    "patchloop/agent/finalization.py",
    "patchloop/agent/investigation.py",
    "patchloop/agent/phases.py",
    "patchloop/agent/saturation_recovery_qualification.py",
    "patchloop/agent/saturation_recovery_shadow.py",
    "patchloop/agent/saturation_recovery_shadow_qualification.py",
    "patchloop/agent/structured_edit.py",
    "patchloop/agent/tools.py",
    "patchloop/contracts.py",
    "patchloop/errors.py",
    "patchloop/util.py",
    "scripts/build_lean_harness_saturation_recovery_shadow_qualification.py",
)
VALIDATION_PATHS = (
    "tests/test_finalization.py",
    "tests/test_saturation_recovery_qualification.py",
    "tests/test_saturation_recovery_shadow.py",
    "tests/test_saturation_recovery_shadow_qualification.py",
    "tests/test_structured_edit.py",
)

FIXED_TIME = datetime(2026, 8, 16, tzinfo=UTC)


class ShadowQualificationObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    observation_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    frame_kind: Literal["boundary", "phase"]
    phase: Literal["INTAKE", "REPRODUCE", "PLAN", "IMPLEMENT", "VERIFY", "REVIEW"]
    scenario: Literal[
        "normal",
        "semantic-replay-three",
        "semantic-replay-four",
        "no-progress-one",
        "no-progress-two",
        "patch-rejection-one",
        "patch-rejection-two",
        "combined-restriction",
        "patch-applied-reset",
    ]
    conditions_compared: tuple[Literal["no_memory", "structured"], ...]
    no_memory_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    structured_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    condition_pair_equal: Literal[True]
    source_phase_allowed_actions: tuple[str, ...]
    source_phase_tool_names: tuple[str, ...]
    semantic_replay_count: int = Field(ge=0)
    no_progress_streak: int = Field(ge=0)
    patch_rejection_count: int = Field(ge=0)
    admission_mode: str
    reason_codes: tuple[str, ...]
    selected_tool_names: tuple[str, ...]
    removed_tool_names: tuple[str, ...]
    added_tool_names: tuple[str, ...]
    shadow: SaturationRecoveryAdmissionShadow

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        identity = {
            "frame_kind": self.frame_kind,
            "phase": self.phase,
            "scenario": self.scenario,
        }
        if self.observation_id != sha256_json(identity):
            raise ValueError("admission shadow observation identity differs")
        if self.conditions_compared != CONDITIONS:
            raise ValueError("admission shadow condition frame differs")
        if (
            self.no_memory_projection_hash,
            self.structured_projection_hash,
        ) != (self.shadow.content_hash, self.shadow.content_hash):
            raise ValueError("admission shadow condition projection differs")
        if self.source_phase_allowed_actions != (
            self.shadow.source_phase_tool_surface.phase_allowed_actions
        ):
            raise ValueError("admission shadow phase actions differ")
        expected = (
            self.shadow.source_phase_tool_names,
            self.shadow.semantic_replay_count,
            self.shadow.no_progress_streak,
            self.shadow.patch_rejection_count,
            self.shadow.admission_mode,
            self.shadow.reason_codes,
            self.shadow.selected_tool_names,
            self.shadow.removed_tool_names,
            self.shadow.added_tool_names,
        )
        observed = (
            self.source_phase_tool_names,
            self.semantic_replay_count,
            self.no_progress_streak,
            self.patch_rejection_count,
            self.admission_mode,
            self.reason_codes,
            self.selected_tool_names,
            self.removed_tool_names,
            self.added_tool_names,
        )
        if observed != expected:
            raise ValueError("admission shadow observation summary differs")
        return self


class SaturationRecoveryShadowPublicQualification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-saturation-recovery-shadow-public-qualification-v2"]
    qualification_id: Literal["lean-harness-saturation-recovery-shadow-public-20260816-v2"]
    status: Literal["PUBLIC_SYNTHETIC_NO_CALL_ADMISSION_RECOVERY_QUALIFIED_RUNTIME_CLOSED"]
    evidence_date: Literal["2026-08-16"]
    frame_source: Literal["deterministic-synthetic-public-durable-events-and-phase-evidence"]
    predecessor_thresholds: ArtifactBinding
    predecessor_threshold_content_hash: Literal[
        "sha256:f07374bca99d1046c66f7ade6d96caf2bd06cbafe307dcabcad681f473485db6"
    ]
    predecessor_v1: ArtifactBinding
    predecessor_v1_disposition: Literal[
        "invalidated-by-post-materialization-self-validation-hardening"
    ]
    policy_version: Literal["lean-harness-saturation-recovery-v1"]
    semantic_replay_threshold: Literal[4]
    no_progress_strategy_threshold: Literal[2]
    structured_edit_escalation_rejections: Literal[2]
    direct_corrective_patch_retries_before_escalation: Literal[1]
    frame_phases: tuple[str, ...]
    scenarios: tuple[str, ...]
    conditions: tuple[str, ...]
    canonical_boundary_phase: Literal["IMPLEMENT"]
    boundary_observations: tuple[ShadowQualificationObservation, ...]
    phase_observations: tuple[ShadowQualificationObservation, ...]
    expected_boundary_observations: Literal[9]
    expected_phase_observations: Literal[6]
    expected_condition_comparisons: Literal[30]
    all_boundary_decisions_exact: Literal[True]
    all_phase_surfaces_exact: Literal[True]
    condition_neutral_projection: Literal[True]
    fourth_semantic_replay_blocks_read_search_only: Literal[True]
    second_no_progress_increment_requires_strategy_change: Literal[True]
    second_patch_rejection_requires_structured_edit: Literal[True]
    patch_applied_resets_all_counters: Literal[True]
    freeform_patch_removed_only_at_structured_escalation: Literal[True]
    non_investigation_phase_tools_preserved: Literal[True]
    structured_edit_runtime_registered: Literal[False]
    threshold_optimality_established: Literal[False]
    provider_token_savings_verified: Literal[False]
    success_effect_verified: Literal[False]
    source_files: tuple[FileBinding, ...]
    validation_files: tuple[FileBinding, ...]
    source_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    public_task_files_read: Literal[0]
    private_task_files_read: Literal[0]
    hidden_files_read: Literal[0]
    reference_patches_read: Literal[0]
    runtime_state_files_read: Literal[0]
    provider_transport_calls: Literal[0]
    provider_generation_calls: Literal[0]
    runner_calls: Literal[0]
    tool_execution_calls: Literal[0]
    docker_calls: Literal[0]
    evaluator_calls: Literal[0]
    added_model_cost_usd: Literal[0]
    provider_calls_authorized: Literal[False]
    runner_activation_authorized: Literal[False]
    tool_policy_activation_authorized: Literal[False]
    request_integration_authorized: Literal[False]
    request_persistence_authorized: Literal[False]
    state_mutation_authorized: Literal[False]
    paid_execution_authorized: Literal[False]
    next_gate: Literal["predeclare-budget-adequacy-measurement-contract-before-fresh-design"]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_qualification(self) -> Self:
        expected_predecessor = ArtifactBinding(
            path=THRESHOLD_QUALIFICATION_PATH,
            file_bytes=THRESHOLD_QUALIFICATION_BYTES,
            file_sha256=THRESHOLD_QUALIFICATION_FILE_SHA256,
            content_hash=THRESHOLD_QUALIFICATION_CONTENT_HASH,
        )
        if self.predecessor_thresholds != expected_predecessor:
            raise ValueError("admission shadow predecessor differs")
        if self.predecessor_v1 != ArtifactBinding(
            path=PREDECESSOR_V1_PATH,
            file_bytes=PREDECESSOR_V1_BYTES,
            file_sha256=PREDECESSOR_V1_FILE_SHA256,
            content_hash=PREDECESSOR_V1_CONTENT_HASH,
        ):
            raise ValueError("admission shadow v1 predecessor differs")
        if (
            self.frame_phases,
            self.scenarios,
            self.conditions,
        ) != (FRAME_PHASES, SCENARIOS, CONDITIONS):
            raise ValueError("admission shadow qualification frame differs")
        if len(self.boundary_observations) != self.expected_boundary_observations or (
            tuple(item.scenario for item in self.boundary_observations) != SCENARIOS
        ):
            raise ValueError("admission shadow boundary frame differs")
        if any(
            item.frame_kind != "boundary" or item.phase != "IMPLEMENT"
            for item in self.boundary_observations
        ):
            raise ValueError("admission shadow boundary phase differs")
        if any(
            (
                item.semantic_replay_count,
                item.no_progress_streak,
                item.patch_rejection_count,
                item.admission_mode,
            )
            != EXPECTED_BOUNDARY_STATE[item.scenario]
            for item in self.boundary_observations
        ):
            raise ValueError("admission shadow boundary decision differs")
        if len(self.phase_observations) != self.expected_phase_observations or (
            tuple(item.phase for item in self.phase_observations) != FRAME_PHASES
        ):
            raise ValueError("admission shadow phase frame differs")
        if any(
            item.frame_kind != "phase" or item.scenario != "combined-restriction"
            for item in self.phase_observations
        ):
            raise ValueError("admission shadow phase scenario differs")
        if any(
            (
                item.semantic_replay_count,
                item.no_progress_streak,
                item.patch_rejection_count,
                item.admission_mode,
            )
            != EXPECTED_BOUNDARY_STATE["combined-restriction"]
            for item in self.phase_observations
        ):
            raise ValueError("admission shadow phase decision differs")
        comparisons = 2 * (len(self.boundary_observations) + len(self.phase_observations))
        if comparisons != self.expected_condition_comparisons:
            raise ValueError("admission shadow condition comparison total differs")
        if any(
            item.source_phase_allowed_actions != EXPECTED_PHASE_ALLOWED_ACTIONS[item.phase]
            for item in self.phase_observations
        ):
            raise ValueError("admission shadow current phase policy differs")
        if any(
            set(item.selected_tool_names)
            != (
                set(item.source_phase_tool_names) - {"read_file", "search_files", "apply_patch"}
                | {"apply_structured_edit"}
            )
            or item.shadow.freeform_patch_admitted is not False
            or item.shadow.structured_edit_admitted is not True
            for item in self.phase_observations
        ):
            raise ValueError("admission shadow phase recovery surface differs")
        if any(
            item.shadow.threshold_qualification_content_hash
            != self.predecessor_threshold_content_hash
            or item.shadow.provider_calls_authorized is not False
            or item.shadow.runner_activation_authorized is not False
            or item.shadow.state_mutation_authorized is not False
            for item in (*self.boundary_observations, *self.phase_observations)
        ):
            raise ValueError("admission shadow nested authority differs")
        if (
            tuple(item.path for item in self.source_files) != SOURCE_PATHS
            or tuple(item.path for item in self.validation_files) != VALIDATION_PATHS
        ):
            raise ValueError("admission shadow file inventory differs")
        if self.source_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.source_files]
        ) or self.validation_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.validation_files]
        ):
            raise ValueError("admission shadow inventory hash differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("admission shadow qualification content hash differs")
        return self


def _repository_root(repository: str | Path) -> Path:
    root = Path(repository).resolve()
    if not (root / "pyproject.toml").is_file():
        raise RecoveryError("admission shadow qualification repository is invalid")
    return root


def _file_binding(root: Path, relative: str) -> FileBinding:
    raw = ensure_within(root, relative).read_bytes()
    return FileBinding(
        path=relative,
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
    )


def _threshold_binding(
    root: Path,
) -> tuple[ArtifactBinding, SaturationRecoveryPublicQualification]:
    raw = ensure_within(root, THRESHOLD_QUALIFICATION_PATH).read_bytes()
    if len(raw) != THRESHOLD_QUALIFICATION_BYTES or (
        sha256_bytes(raw) != THRESHOLD_QUALIFICATION_FILE_SHA256
    ):
        raise RecoveryError("admission shadow threshold predecessor differs")
    try:
        thresholds = SaturationRecoveryPublicQualification.model_validate_json(raw)
    except ValueError as exc:
        raise RecoveryError("admission shadow threshold predecessor is invalid") from exc
    if threshold_qualification_bytes(thresholds) != raw or (
        thresholds.content_hash != THRESHOLD_QUALIFICATION_CONTENT_HASH
    ):
        raise RecoveryError("admission shadow threshold content differs")
    return (
        ArtifactBinding(
            path=THRESHOLD_QUALIFICATION_PATH,
            file_bytes=len(raw),
            file_sha256=sha256_bytes(raw),
            content_hash=thresholds.content_hash,
        ),
        thresholds,
    )


def _v1_predecessor_binding(root: Path) -> ArtifactBinding:
    raw = ensure_within(root, PREDECESSOR_V1_PATH).read_bytes()
    if len(raw) != PREDECESSOR_V1_BYTES or (sha256_bytes(raw) != PREDECESSOR_V1_FILE_SHA256):
        raise RecoveryError("admission shadow v1 predecessor differs")
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError("admission shadow v1 predecessor is invalid") from exc
    if (
        type(value) is not dict
        or value.get("schema_version")
        != "lean-harness-saturation-recovery-shadow-public-qualification-v1"
        or value.get("qualification_id")
        != "lean-harness-saturation-recovery-shadow-public-20260816-v1"
        or value.get("content_hash") != PREDECESSOR_V1_CONTENT_HASH
    ):
        raise RecoveryError("admission shadow v1 predecessor content differs")
    return ArtifactBinding(
        path=PREDECESSOR_V1_PATH,
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        content_hash=PREDECESSOR_V1_CONTENT_HASH,
    )


def _phase_evidence(phase: str) -> EvidenceState:
    allowed = EXPECTED_PHASE_ALLOWED_ACTIONS[phase]
    mutation_present = phase in {"IMPLEMENT", "VERIFY", "REVIEW"}
    checks_complete = phase in {"VERIFY", "REVIEW"}
    review_exists = phase == "REVIEW"
    return EvidenceState(
        worktree_diff_hash=(
            sha256_text("synthetic-current-diff") if mutation_present else sha256_text("")
        ),
        mutation_event_sequence=1 if mutation_present else None,
        mutation_present=mutation_present,
        completed_checks=("public-check",) if checks_complete else (),
        pending_checks=() if checks_complete else ("public-check",),
        current_diff_check_event_sequences=(2,) if checks_complete else (),
        latest_check_sequence=2 if checks_complete else None,
        review_event_sequence=3 if review_exists else None,
        review_presented_to_model=False,
        task_review_event_sequence=None,
        task_review_presented_to_model=False,
        task_review_coverage_complete=None,
        unresolved_coverage_target_ids=(),
        submission_ready=False,
        missing_evidence=("synthetic-public-phase-boundary",),
        allowed_next_actions=allowed,
    )


def _phase_surface(phase: str):
    return project_phase_tool_surface(
        reserve=r8_public_development_finalization_reserve(),
        tool_schemas=TOOL_SCHEMAS_V2,
        phase_evidence=_phase_evidence(phase),
        mode="exploration",
    )


def _event(
    sequence: int,
    event_type: EventType,
    payload: dict[str, Any],
) -> RunEvent:
    return RunEvent(
        event_id=f"evt_public_admission_shadow_{sequence:03d}",
        run_id="run_public_admission_shadow",
        sequence=sequence,
        type=event_type,
        timestamp=FIXED_TIME,
        actor="synthetic-public-fixture",
        payload=payload,
    )


def _replays(count: int, *, start: int = 1) -> list[RunEvent]:
    events: list[RunEvent] = []
    sequence = start
    for index in range(count):
        tool = "read_file" if index % 2 == 0 else "search_files"
        events.extend(
            (
                _event(
                    sequence,
                    EventType.LOOP_DETECTED,
                    {"schema_version": "investigation-loop-v1", "tool": tool},
                ),
                _event(
                    sequence + 1,
                    EventType.TOOL_REPLAYED,
                    {"tool": tool, "semantic_replay": True},
                ),
                _event(
                    sequence + 2,
                    EventType.TOOL_SUCCEEDED,
                    {"tool": "run_check", "status": "succeeded"},
                ),
            )
        )
        sequence += 3
    return events


def _seen_only(count: int, *, start: int = 1) -> list[RunEvent]:
    return [
        _event(
            start + index,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "read_file" if index % 2 == 0 else "search_files",
                "status": "succeeded",
                "novelty": {"classification": "seen_only"},
            },
        )
        for index in range(count)
    ]


def _rejections(count: int, *, start: int = 1) -> list[RunEvent]:
    return [
        _event(
            start + index,
            EventType.TOOL_FAILED,
            {
                "tool": "apply_patch",
                "status": "rejected",
                "error_code": "PATCH_REJECTED",
            },
        )
        for index in range(count)
    ]


def _scenario_events(scenario: str) -> list[RunEvent]:
    if scenario == "normal":
        return []
    if scenario == "semantic-replay-three":
        return _replays(3)
    if scenario == "semantic-replay-four":
        return _replays(4)
    if scenario == "no-progress-one":
        return _seen_only(1)
    if scenario == "no-progress-two":
        return _seen_only(2)
    if scenario == "patch-rejection-one":
        return _rejections(1)
    if scenario == "patch-rejection-two":
        return _rejections(2)
    events = _replays(4)
    events.extend(_rejections(2, start=events[-1].sequence + 1))
    if scenario == "combined-restriction":
        return events
    if scenario == "patch-applied-reset":
        events.append(
            _event(
                events[-1].sequence + 1,
                EventType.PATCH_APPLIED,
                {"tool": "apply_patch", "status": "succeeded"},
            )
        )
        return events
    raise RecoveryError(f"unsupported admission shadow scenario: {scenario}")


def _observation(
    *,
    thresholds: SaturationRecoveryPublicQualification,
    frame_kind: Literal["boundary", "phase"],
    phase: str,
    scenario: str,
) -> ShadowQualificationObservation:
    shadow = project_saturation_recovery_admission_shadow(
        thresholds=thresholds,
        events=_scenario_events(scenario),
        phase_tool_surface=_phase_surface(phase),
    )
    identity = {"frame_kind": frame_kind, "phase": phase, "scenario": scenario}
    return ShadowQualificationObservation(
        observation_id=sha256_json(identity),
        **identity,
        conditions_compared=CONDITIONS,
        no_memory_projection_hash=shadow.content_hash,
        structured_projection_hash=shadow.content_hash,
        condition_pair_equal=True,
        source_phase_allowed_actions=(shadow.source_phase_tool_surface.phase_allowed_actions),
        source_phase_tool_names=shadow.source_phase_tool_names,
        semantic_replay_count=shadow.semantic_replay_count,
        no_progress_streak=shadow.no_progress_streak,
        patch_rejection_count=shadow.patch_rejection_count,
        admission_mode=shadow.admission_mode,
        reason_codes=shadow.reason_codes,
        selected_tool_names=shadow.selected_tool_names,
        removed_tool_names=shadow.removed_tool_names,
        added_tool_names=shadow.added_tool_names,
        shadow=shadow,
    )


def build_saturation_recovery_shadow_public_qualification(
    repository: str | Path = ".",
) -> SaturationRecoveryShadowPublicQualification:
    root = _repository_root(repository)
    predecessor, thresholds = _threshold_binding(root)
    predecessor_v1 = _v1_predecessor_binding(root)
    boundary = tuple(
        _observation(
            thresholds=thresholds,
            frame_kind="boundary",
            phase="IMPLEMENT",
            scenario=scenario,
        )
        for scenario in SCENARIOS
    )
    phases = tuple(
        _observation(
            thresholds=thresholds,
            frame_kind="phase",
            phase=phase,
            scenario="combined-restriction",
        )
        for phase in FRAME_PHASES
    )
    source_files = tuple(_file_binding(root, path) for path in SOURCE_PATHS)
    validation_files = tuple(_file_binding(root, path) for path in VALIDATION_PATHS)
    body: dict[str, Any] = {
        "schema_version": QUALIFICATION_SCHEMA,
        "qualification_id": QUALIFICATION_ID,
        "status": ("PUBLIC_SYNTHETIC_NO_CALL_ADMISSION_RECOVERY_QUALIFIED_RUNTIME_CLOSED"),
        "evidence_date": "2026-08-16",
        "frame_source": ("deterministic-synthetic-public-durable-events-and-phase-evidence"),
        "predecessor_thresholds": predecessor.model_dump(mode="python"),
        "predecessor_threshold_content_hash": thresholds.content_hash,
        "predecessor_v1": predecessor_v1.model_dump(mode="python"),
        "predecessor_v1_disposition": (
            "invalidated-by-post-materialization-self-validation-hardening"
        ),
        "policy_version": "lean-harness-saturation-recovery-v1",
        "semantic_replay_threshold": 4,
        "no_progress_strategy_threshold": 2,
        "structured_edit_escalation_rejections": 2,
        "direct_corrective_patch_retries_before_escalation": 1,
        "frame_phases": FRAME_PHASES,
        "scenarios": SCENARIOS,
        "conditions": CONDITIONS,
        "canonical_boundary_phase": "IMPLEMENT",
        "boundary_observations": tuple(item.model_dump(mode="python") for item in boundary),
        "phase_observations": tuple(item.model_dump(mode="python") for item in phases),
        "expected_boundary_observations": 9,
        "expected_phase_observations": 6,
        "expected_condition_comparisons": 30,
        "all_boundary_decisions_exact": True,
        "all_phase_surfaces_exact": True,
        "condition_neutral_projection": True,
        "fourth_semantic_replay_blocks_read_search_only": True,
        "second_no_progress_increment_requires_strategy_change": True,
        "second_patch_rejection_requires_structured_edit": True,
        "patch_applied_resets_all_counters": True,
        "freeform_patch_removed_only_at_structured_escalation": True,
        "non_investigation_phase_tools_preserved": True,
        "structured_edit_runtime_registered": False,
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
        "public_task_files_read": 0,
        "private_task_files_read": 0,
        "hidden_files_read": 0,
        "reference_patches_read": 0,
        "runtime_state_files_read": 0,
        "provider_transport_calls": 0,
        "provider_generation_calls": 0,
        "runner_calls": 0,
        "tool_execution_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "added_model_cost_usd": 0,
        "provider_calls_authorized": False,
        "runner_activation_authorized": False,
        "tool_policy_activation_authorized": False,
        "request_integration_authorized": False,
        "request_persistence_authorized": False,
        "state_mutation_authorized": False,
        "paid_execution_authorized": False,
        "next_gate": ("predeclare-budget-adequacy-measurement-contract-before-fresh-design"),
    }
    return SaturationRecoveryShadowPublicQualification.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )


def qualification_bytes(
    qualification: SaturationRecoveryShadowPublicQualification,
) -> bytes:
    return (
        json.dumps(
            qualification.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def materialize_saturation_recovery_shadow_public_qualification(
    repository: str | Path = ".",
    output_path: str | Path = QUALIFICATION_PATH,
) -> SaturationRecoveryShadowPublicQualification:
    root = _repository_root(repository)
    qualification = build_saturation_recovery_shadow_public_qualification(root)
    content = qualification_bytes(qualification)
    output = ensure_within(root, str(output_path))
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if output.read_bytes() != content:
            raise RecoveryError("existing admission shadow qualification differs")
        return qualification
    with output.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    return qualification


def load_saturation_recovery_shadow_public_qualification(
    repository: str | Path = ".",
    path: str | Path = QUALIFICATION_PATH,
) -> SaturationRecoveryShadowPublicQualification:
    root = _repository_root(repository)
    raw = ensure_within(root, str(path)).read_bytes()
    try:
        qualification = SaturationRecoveryShadowPublicQualification.model_validate_json(raw)
    except ValueError as exc:
        raise RecoveryError("admission shadow qualification is invalid JSON") from exc
    if qualification_bytes(qualification) != raw:
        raise RecoveryError("admission shadow qualification bytes are not canonical")
    expected = build_saturation_recovery_shadow_public_qualification(root)
    if qualification != expected:
        raise RecoveryError("admission shadow qualification differs from source")
    return qualification
