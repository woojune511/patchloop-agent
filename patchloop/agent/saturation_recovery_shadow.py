"""Pure no-call shadow for public saturation and recovery thresholds.

The active gateway still owns tool execution and persistence.  This module
only projects how one exact durable event prefix would change the already
phase-filtered tool surface under the public-development 4/2/2 candidate.  It
does not write state, dispatch a tool, build a provider request, or activate
the candidate policy.
"""

from __future__ import annotations

import copy
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.finalization import PhaseToolSurfaceProjection
from patchloop.agent.investigation import INVESTIGATION_LOOP_SCHEMA
from patchloop.agent.saturation_recovery_qualification import (
    SaturationRecoveryPublicQualification,
)
from patchloop.agent.structured_edit import (
    STRUCTURED_EDIT_TOOL_NAME,
    STRUCTURED_EDIT_TOOL_SCHEMA_V1,
    STRUCTURED_EDIT_TOOL_SCHEMA_V2,
)
from patchloop.contracts import EventType, RunEvent
from patchloop.util import sha256_json

SATURATION_RECOVERY_SHADOW_SCHEMA = "lean-harness-saturation-recovery-admission-shadow-v1"
SATURATION_RECOVERY_SHADOW_SCHEMA_V2 = "lean-harness-saturation-recovery-admission-shadow-v2"
SATURATION_RECOVERY_SHADOW_SCHEMA_V3 = "lean-harness-saturation-recovery-admission-shadow-v3"
SATURATION_RECOVERY_SHADOW_POLICY = "lean-harness-saturation-recovery-v1"
THRESHOLD_QUALIFICATION_ID = "lean-harness-saturation-recovery-public-20260816-v1"
THRESHOLD_QUALIFICATION_CONTENT_HASH = (
    "sha256:f07374bca99d1046c66f7ade6d96caf2bd06cbafe307dcabcad681f473485db6"
)

_SEMANTIC_REPLAY_THRESHOLD = 4
_NO_PROGRESS_THRESHOLD = 2
_STRUCTURED_EDIT_THRESHOLD = 2
_DIRECT_CORRECTIVE_RETRIES = 1
_SATURATION_BLOCKED_TOOLS = ("read_file", "search_files")
_REASON_ORDER = (
    "semantic_replay_limit_reached",
    "no_progress_strategy_change_required",
    "structured_edit_recovery_required",
)

EventEffect = Literal[
    "semantic-replay",
    "no-progress-increment",
    "progress-reset",
    "patch-rejection",
    "mutation-reset",
]
AdmissionMode = Literal[
    "normal",
    "strategy-change-required",
    "evidence-saturated",
    "structured-edit-recovery",
    "saturated-structured-edit-recovery",
]


class SaturationRecoveryEventProjection(BaseModel):
    """Sanitized lifecycle event sufficient to replay the candidate state."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    sequence: int = Field(ge=1)
    event_type: Literal[
        "ToolReplayed",
        "LoopDetected",
        "ToolSucceeded",
        "ToolFailed",
        "PatchApplied",
    ]
    effect: EventEffect
    tool: str | None
    source_event_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        expected_event = {
            "semantic-replay": "ToolReplayed",
            "no-progress-increment": None,
            "progress-reset": "ToolSucceeded",
            "patch-rejection": "ToolFailed",
            "mutation-reset": "PatchApplied",
        }[self.effect]
        if expected_event is not None and self.event_type != expected_event:
            raise ValueError("shadow event effect differs from its event type")
        if self.effect == "no-progress-increment" and self.event_type not in {
            "LoopDetected",
            "ToolSucceeded",
        }:
            raise ValueError("no-progress shadow event has an invalid source type")
        if self.effect == "semantic-replay" and (not isinstance(self.tool, str) or not self.tool):
            raise ValueError("semantic replay shadow tool differs")
        if self.effect == "patch-rejection" and self.tool != "apply_patch":
            raise ValueError("patch rejection shadow tool differs")
        if self.effect == "mutation-reset" and self.tool != "apply_patch":
            raise ValueError("mutation reset shadow tool differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("shadow event projection hash differs")
        return self


class SaturationRecoveryAdmissionShadow(BaseModel):
    """Content-addressed no-call projection of the candidate policy."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-saturation-recovery-admission-shadow-v1"]
    status: Literal["no-call-admission-recovery-shadow-runtime-closed"]
    policy_version: Literal["lean-harness-saturation-recovery-v1"]
    threshold_qualification_id: Literal["lean-harness-saturation-recovery-public-20260816-v1"]
    threshold_qualification_content_hash: Literal[
        "sha256:f07374bca99d1046c66f7ade6d96caf2bd06cbafe307dcabcad681f473485db6"
    ]
    semantic_replay_threshold: Literal[4]
    no_progress_strategy_threshold: Literal[2]
    structured_edit_escalation_rejections: Literal[2]
    direct_corrective_patch_retries_before_escalation: Literal[1]
    source_run_id: str = Field(min_length=1)
    source_event_count: int = Field(ge=0)
    source_through_sequence: int = Field(ge=0)
    source_event_prefix_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    event_projections: tuple[SaturationRecoveryEventProjection, ...]
    selected_event_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    mutation_epoch_sequence: int | None = Field(default=None, ge=1)
    semantic_replay_count: int = Field(ge=0)
    no_progress_streak: int = Field(ge=0)
    patch_rejection_count: int = Field(ge=0)
    direct_corrective_patch_retries_remaining: int = Field(ge=0, le=1)
    evidence_saturated: bool
    strategy_change_required: bool
    structured_edit_required: bool
    admission_mode: AdmissionMode
    reason_codes: tuple[
        Literal[
            "semantic_replay_limit_reached",
            "no_progress_strategy_change_required",
            "structured_edit_recovery_required",
        ],
        ...,
    ]
    source_phase_tool_surface: PhaseToolSurfaceProjection
    source_phase_tool_surface_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_phase_tool_names: tuple[str, ...]
    selected_tool_schemas: tuple[dict[str, Any], ...] = Field(min_length=1)
    selected_tool_names: tuple[str, ...] = Field(min_length=1)
    removed_tool_names: tuple[str, ...]
    added_tool_names: tuple[str, ...]
    selected_tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    structured_edit_tool_schema: dict[str, Any]
    structured_edit_tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    freeform_patch_admitted: bool
    structured_edit_admitted: bool
    tool_surface_changed: bool
    request_rebuild_required: bool
    exact_input_recount_required: bool
    counters_reset_only_by_patch_applied: Literal[True]
    strategy_change_is_required_not_terminal: Literal[True]
    structured_edit_runtime_registered: Literal[False]
    condition_specific_policy_authorized: Literal[False]
    provider_transport_calls: Literal[0]
    provider_calls_authorized: Literal[False]
    runner_calls: Literal[0]
    runner_activation_authorized: Literal[False]
    tool_execution_calls: Literal[0]
    tool_policy_activation_authorized: Literal[False]
    request_persistence_authorized: Literal[False]
    state_mutation_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_shadow(self) -> Self:
        sequences = tuple(item.sequence for item in self.event_projections)
        if sequences != tuple(sorted(sequences)) or len(sequences) != len(set(sequences)):
            raise ValueError("shadow event projections must be ordered and unique")
        if self.source_event_count < len(self.event_projections):
            raise ValueError("shadow selected events exceed the source prefix")
        if sequences and self.source_through_sequence < sequences[-1]:
            raise ValueError("shadow source boundary precedes a selected event")
        if self.selected_event_projection_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.event_projections]
        ):
            raise ValueError("shadow selected-event projection hash differs")

        expected_epoch, replay_count, no_progress, rejection_count = _candidate_state(
            self.event_projections
        )
        if (
            self.mutation_epoch_sequence,
            self.semantic_replay_count,
            self.no_progress_streak,
            self.patch_rejection_count,
        ) != (expected_epoch, replay_count, no_progress, rejection_count):
            raise ValueError("shadow candidate state differs from event projections")
        expected_saturated = replay_count >= _SEMANTIC_REPLAY_THRESHOLD
        expected_strategy = no_progress >= _NO_PROGRESS_THRESHOLD
        mutation_recovery_available = getattr(
            self,
            "mutation_recovery_available",
            True,
        )
        expected_structured = (
            rejection_count >= _STRUCTURED_EDIT_THRESHOLD and mutation_recovery_available
        )
        if (
            self.evidence_saturated,
            self.strategy_change_required,
            self.structured_edit_required,
        ) != (expected_saturated, expected_strategy, expected_structured):
            raise ValueError("shadow policy decision differs")
        expected_direct_retries = (
            max(0, _DIRECT_CORRECTIVE_RETRIES - rejection_count)
            if mutation_recovery_available
            else 0
        )
        if self.direct_corrective_patch_retries_remaining != expected_direct_retries:
            raise ValueError("shadow corrective retry allowance differs")
        if self.admission_mode != _admission_mode(
            saturated=expected_saturated,
            strategy=expected_strategy,
            structured=expected_structured,
        ):
            raise ValueError("shadow admission mode differs")
        expected_reasons = tuple(
            reason
            for reason, active in zip(
                _REASON_ORDER,
                (expected_saturated, expected_strategy, expected_structured),
                strict=True,
            )
            if active
        )
        if self.reason_codes != expected_reasons:
            raise ValueError("shadow reason codes differ")

        if self.source_phase_tool_surface_hash != (self.source_phase_tool_surface.content_hash):
            raise ValueError("shadow source phase surface hash differs")
        base_schemas = self.source_phase_tool_surface.selected_tool_schemas
        base_names = _tool_names(base_schemas)
        if self.source_phase_tool_names != base_names:
            raise ValueError("shadow source phase tools differ")
        if mutation_recovery_available is not ("apply_patch" in base_names):
            raise ValueError("shadow mutation-recovery availability differs")
        expected_schemas = _selected_schemas(
            base_schemas,
            saturated=expected_saturated,
            structured=expected_structured,
            structured_edit_tool_schema=(
                STRUCTURED_EDIT_TOOL_SCHEMA_V2
                if getattr(self, "structured_edit_refresh_policy_version", None)
                == "gateway-fresh-preimage-unique-text-v1"
                else STRUCTURED_EDIT_TOOL_SCHEMA_V1
            ),
        )
        expected_names = _tool_names(expected_schemas)
        if self.selected_tool_schemas != expected_schemas:
            raise ValueError("shadow selected tool schemas differ")
        if self.selected_tool_names != expected_names:
            raise ValueError("shadow selected tool names differ")
        selected_set = set(expected_names)
        expected_removed = tuple(name for name in base_names if name not in selected_set)
        expected_added = tuple(name for name in expected_names if name not in set(base_names))
        if (
            self.removed_tool_names,
            self.added_tool_names,
        ) != (expected_removed, expected_added):
            raise ValueError("shadow tool delta differs")
        if self.selected_tool_schema_hash != sha256_json(list(expected_schemas)):
            raise ValueError("shadow selected tool schema hash differs")
        expected_structured_schema = (
            STRUCTURED_EDIT_TOOL_SCHEMA_V2
            if getattr(self, "structured_edit_refresh_policy_version", None)
            == "gateway-fresh-preimage-unique-text-v1"
            else STRUCTURED_EDIT_TOOL_SCHEMA_V1
        )
        if self.structured_edit_tool_schema != expected_structured_schema or (
            self.structured_edit_tool_schema_hash != sha256_json(expected_structured_schema)
        ):
            raise ValueError("shadow structured-edit schema differs")
        if self.freeform_patch_admitted is not ("apply_patch" in expected_names):
            raise ValueError("shadow freeform patch admission differs")
        if self.structured_edit_admitted is not (STRUCTURED_EDIT_TOOL_NAME in expected_names):
            raise ValueError("shadow structured edit admission differs")
        changed = tuple(base_schemas) != expected_schemas
        if self.tool_surface_changed is not changed:
            raise ValueError("shadow tool-surface change differs")
        rebuild = expected_saturated or expected_strategy or expected_structured
        if (
            self.request_rebuild_required,
            self.exact_input_recount_required,
        ) != (rebuild, rebuild):
            raise ValueError("shadow request rebuild decision differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("saturation/recovery shadow content hash differs")
        return self


class SaturationRecoveryAdmissionShadowV2(SaturationRecoveryAdmissionShadow):
    """Successor projection that also permits completion-only tool surfaces."""

    schema_version: Literal["lean-harness-saturation-recovery-admission-shadow-v2"]
    mutation_recovery_available: bool


class SaturationRecoveryAdmissionShadowV3(SaturationRecoveryAdmissionShadowV2):
    """Successor that injects the gateway-refreshed structured edit schema."""

    schema_version: Literal["lean-harness-saturation-recovery-admission-shadow-v3"]
    structured_edit_refresh_policy_version: Literal["gateway-fresh-preimage-unique-text-v1"]


def _tool_names(schemas: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
    names: list[str] = []
    for schema in schemas:
        if type(schema) is not dict:
            raise TypeError("shadow tool schemas must be exact mappings")
        name = schema.get("name")
        if schema.get("type") != "function" or type(name) is not str or not name:
            raise ValueError("shadow tool schema identity is invalid")
        names.append(name)
    if len(names) != len(set(names)):
        raise ValueError("shadow tool schema names must be unique")
    return tuple(names)


def _selected_schemas(
    base_schemas: tuple[dict[str, Any], ...],
    *,
    saturated: bool,
    structured: bool,
    structured_edit_tool_schema: dict[str, Any] = STRUCTURED_EDIT_TOOL_SCHEMA_V1,
) -> tuple[dict[str, Any], ...]:
    selected: list[dict[str, Any]] = []
    for schema in base_schemas:
        name = schema["name"]
        if saturated and name in _SATURATION_BLOCKED_TOOLS:
            continue
        if structured and name == "apply_patch":
            selected.append(copy.deepcopy(structured_edit_tool_schema))
            continue
        selected.append(copy.deepcopy(schema))
    if not selected:
        raise ValueError("shadow policy leaves no callable tool")
    return tuple(selected)


def _event_projection(event: RunEvent) -> SaturationRecoveryEventProjection | None:
    effect: EventEffect | None = None
    tool = event.payload.get("tool")
    if (
        event.type == EventType.TOOL_REPLAYED
        and event.payload.get("semantic_replay") is True
        and isinstance(tool, str)
        and tool
    ):
        effect = "semantic-replay"
    elif (
        event.type == EventType.LOOP_DETECTED
        and event.payload.get("schema_version") == INVESTIGATION_LOOP_SCHEMA
    ):
        effect = "no-progress-increment"
    elif event.type == EventType.TOOL_SUCCEEDED:
        novelty = event.payload.get("novelty")
        seen_only = (
            tool in {"read_file", "search_files"}
            and isinstance(novelty, dict)
            and novelty.get("classification") == "seen_only"
        )
        effect = "no-progress-increment" if seen_only else "progress-reset"
    elif event.type == EventType.TOOL_FAILED and tool == "apply_patch":
        effect = "patch-rejection"
    elif event.type == EventType.PATCH_APPLIED:
        effect = "mutation-reset"
        tool = "apply_patch"
    if effect is None:
        return None
    source_hash = sha256_json(event.model_dump(mode="json"))
    body = {
        "sequence": event.sequence,
        "event_type": event.type.value,
        "effect": effect,
        "tool": tool if isinstance(tool, str) else None,
        "source_event_hash": source_hash,
    }
    return SaturationRecoveryEventProjection.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )


def _candidate_state(
    events: tuple[SaturationRecoveryEventProjection, ...],
) -> tuple[int | None, int, int, int]:
    epoch = max(
        (item.sequence for item in events if item.effect == "mutation-reset"),
        default=None,
    )
    active = tuple(item for item in events if epoch is None or item.sequence > epoch)
    replay_count = sum(item.effect == "semantic-replay" for item in active)
    no_progress = 0
    for item in active:
        if item.effect == "no-progress-increment":
            no_progress += 1
        elif item.effect in {"progress-reset", "mutation-reset"}:
            no_progress = 0
    rejection_count = sum(item.effect == "patch-rejection" for item in active)
    return epoch, replay_count, no_progress, rejection_count


def _admission_mode(
    *,
    saturated: bool,
    strategy: bool,
    structured: bool,
) -> AdmissionMode:
    if saturated and structured:
        return "saturated-structured-edit-recovery"
    if structured:
        return "structured-edit-recovery"
    if saturated:
        return "evidence-saturated"
    if strategy:
        return "strategy-change-required"
    return "normal"


def project_saturation_recovery_admission_shadow(
    *,
    thresholds: SaturationRecoveryPublicQualification,
    events: list[RunEvent] | tuple[RunEvent, ...],
    phase_tool_surface: PhaseToolSurfaceProjection,
    allow_non_mutation_surface: bool = False,
    structured_edit_tool_schema: dict[str, Any] = STRUCTURED_EDIT_TOOL_SCHEMA_V1,
) -> (
    SaturationRecoveryAdmissionShadow
    | SaturationRecoveryAdmissionShadowV2
    | SaturationRecoveryAdmissionShadowV3
):
    """Project the frozen candidate against one exact durable prefix."""

    if type(thresholds) is not SaturationRecoveryPublicQualification:
        raise TypeError("shadow thresholds require the exact public qualification")
    if (
        thresholds.qualification_id != THRESHOLD_QUALIFICATION_ID
        or thresholds.content_hash != THRESHOLD_QUALIFICATION_CONTENT_HASH
        or thresholds.candidate_semantic_replay_saturation_threshold != _SEMANTIC_REPLAY_THRESHOLD
        or thresholds.candidate_no_progress_strategy_threshold != _NO_PROGRESS_THRESHOLD
        or thresholds.candidate_structured_edit_escalation_rejections != _STRUCTURED_EDIT_THRESHOLD
        or thresholds.direct_corrective_patch_retries_before_escalation
        != _DIRECT_CORRECTIVE_RETRIES
    ):
        raise ValueError("shadow threshold qualification differs")
    if type(events) not in {list, tuple}:
        raise TypeError("shadow events must be an exact list or tuple")
    if structured_edit_tool_schema not in (
        STRUCTURED_EDIT_TOOL_SCHEMA_V1,
        STRUCTURED_EDIT_TOOL_SCHEMA_V2,
    ):
        raise ValueError("shadow structured-edit tool schema is unsupported")
    event_tuple = tuple(events)
    if any(type(item) is not RunEvent for item in event_tuple):
        raise TypeError("shadow events must be exact RunEvent values")
    sequences = tuple(item.sequence for item in event_tuple)
    if sequences != tuple(sorted(sequences)) or len(sequences) != len(set(sequences)):
        raise ValueError("shadow source events must be ordered and unique")
    run_ids = {item.run_id for item in event_tuple}
    if len(run_ids) > 1:
        raise ValueError("shadow source events must belong to one run")
    if type(phase_tool_surface) is not PhaseToolSurfaceProjection:
        raise TypeError("shadow phase surface must be exact phase evidence")
    canonical_phase_surface = PhaseToolSurfaceProjection.model_validate_json(
        phase_tool_surface.model_dump_json()
    )

    projected = tuple(
        item for event in event_tuple if (item := _event_projection(event)) is not None
    )
    epoch, replay_count, no_progress, rejection_count = _candidate_state(projected)
    saturated = replay_count >= _SEMANTIC_REPLAY_THRESHOLD
    strategy = no_progress >= _NO_PROGRESS_THRESHOLD
    structured = rejection_count >= _STRUCTURED_EDIT_THRESHOLD
    base_schemas = canonical_phase_surface.selected_tool_schemas
    base_names = _tool_names(base_schemas)
    mutation_recovery_available = "apply_patch" in base_names
    if not mutation_recovery_available and not allow_non_mutation_surface:
        raise ValueError("shadow phase surface lacks the recovery mutation tool")
    structured = structured and mutation_recovery_available
    selected_schemas = _selected_schemas(
        base_schemas,
        saturated=saturated,
        structured=structured,
        structured_edit_tool_schema=structured_edit_tool_schema,
    )
    selected_names = _tool_names(selected_schemas)
    selected_set = set(selected_names)
    reason_codes = tuple(
        reason
        for reason, active in zip(
            _REASON_ORDER,
            (saturated, strategy, structured),
            strict=True,
        )
        if active
    )
    body: dict[str, Any] = {
        "schema_version": (
            SATURATION_RECOVERY_SHADOW_SCHEMA_V3
            if structured_edit_tool_schema == STRUCTURED_EDIT_TOOL_SCHEMA_V2
            else SATURATION_RECOVERY_SHADOW_SCHEMA_V2
            if allow_non_mutation_surface
            else SATURATION_RECOVERY_SHADOW_SCHEMA
        ),
        **(
            {"mutation_recovery_available": mutation_recovery_available}
            if allow_non_mutation_surface
            else {}
        ),
        **(
            {"structured_edit_refresh_policy_version": ("gateway-fresh-preimage-unique-text-v1")}
            if structured_edit_tool_schema == STRUCTURED_EDIT_TOOL_SCHEMA_V2
            else {}
        ),
        "status": "no-call-admission-recovery-shadow-runtime-closed",
        "policy_version": SATURATION_RECOVERY_SHADOW_POLICY,
        "threshold_qualification_id": thresholds.qualification_id,
        "threshold_qualification_content_hash": thresholds.content_hash,
        "semantic_replay_threshold": _SEMANTIC_REPLAY_THRESHOLD,
        "no_progress_strategy_threshold": _NO_PROGRESS_THRESHOLD,
        "structured_edit_escalation_rejections": _STRUCTURED_EDIT_THRESHOLD,
        "direct_corrective_patch_retries_before_escalation": (_DIRECT_CORRECTIVE_RETRIES),
        "source_run_id": next(iter(run_ids), "synthetic-empty-prefix"),
        "source_event_count": len(event_tuple),
        "source_through_sequence": max(sequences, default=0),
        "source_event_prefix_hash": sha256_json(
            [item.model_dump(mode="json") for item in event_tuple]
        ),
        "event_projections": tuple(item.model_dump(mode="python") for item in projected),
        "selected_event_projection_hash": sha256_json(
            [item.model_dump(mode="json") for item in projected]
        ),
        "mutation_epoch_sequence": epoch,
        "semantic_replay_count": replay_count,
        "no_progress_streak": no_progress,
        "patch_rejection_count": rejection_count,
        "direct_corrective_patch_retries_remaining": (
            max(0, _DIRECT_CORRECTIVE_RETRIES - rejection_count)
            if mutation_recovery_available
            else 0
        ),
        "evidence_saturated": saturated,
        "strategy_change_required": strategy,
        "structured_edit_required": structured,
        "admission_mode": _admission_mode(
            saturated=saturated,
            strategy=strategy,
            structured=structured,
        ),
        "reason_codes": reason_codes,
        "source_phase_tool_surface": canonical_phase_surface.model_dump(mode="python"),
        "source_phase_tool_surface_hash": canonical_phase_surface.content_hash,
        "source_phase_tool_names": base_names,
        "selected_tool_schemas": selected_schemas,
        "selected_tool_names": selected_names,
        "removed_tool_names": tuple(name for name in base_names if name not in selected_set),
        "added_tool_names": tuple(name for name in selected_names if name not in set(base_names)),
        "selected_tool_schema_hash": sha256_json(list(selected_schemas)),
        "structured_edit_tool_schema": copy.deepcopy(structured_edit_tool_schema),
        "structured_edit_tool_schema_hash": sha256_json(structured_edit_tool_schema),
        "freeform_patch_admitted": "apply_patch" in selected_names,
        "structured_edit_admitted": STRUCTURED_EDIT_TOOL_NAME in selected_names,
        "tool_surface_changed": tuple(base_schemas) != selected_schemas,
        "request_rebuild_required": saturated or strategy or structured,
        "exact_input_recount_required": saturated or strategy or structured,
        "counters_reset_only_by_patch_applied": True,
        "strategy_change_is_required_not_terminal": True,
        "structured_edit_runtime_registered": False,
        "condition_specific_policy_authorized": False,
        "provider_transport_calls": 0,
        "provider_calls_authorized": False,
        "runner_calls": 0,
        "runner_activation_authorized": False,
        "tool_execution_calls": 0,
        "tool_policy_activation_authorized": False,
        "request_persistence_authorized": False,
        "state_mutation_authorized": False,
    }
    model_type = (
        SaturationRecoveryAdmissionShadowV3
        if structured_edit_tool_schema == STRUCTURED_EDIT_TOOL_SCHEMA_V2
        else SaturationRecoveryAdmissionShadowV2
        if allow_non_mutation_surface
        else SaturationRecoveryAdmissionShadow
    )
    return model_type.model_validate({**body, "content_hash": sha256_json(body)})
