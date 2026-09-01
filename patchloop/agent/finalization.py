"""Offline contracts for a future evidence-bound finalization mode.

The public-development candidate in this module is intentionally not a
runtime policy.  It records the smallest safe projection needed to qualify a
successor request path: reserve arithmetic, phase tool filtering, an exact
input recount, and a split-aware request allowance.  Provider authority stays
closed until a later public-development comparison qualifies the complete
runtime seam.
"""

from __future__ import annotations

import copy
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.phases import EvidenceState
from patchloop.agent.request_allowance import (
    SplitAwareRequestAllowance,
    project_split_aware_request_allowance,
)
from patchloop.util import ensure_within, sha256_bytes, sha256_json

FINALIZATION_RESERVE_CONTRACT_SCHEMA = "finalization-reserve-contract-v1"
FINALIZATION_REQUEST_MODE_SCHEMA = "finalization-request-mode-v1"
PHASE_TOOL_SURFACE_PROJECTION_SCHEMA = "phase-tool-surface-projection-v1"
FINALIZATION_REQUEST_EVIDENCE_SCHEMA = "finalization-request-evidence-v1"

R8_FINALIZATION_RESERVE_CONTRACT_ID = "r8-public-development-finalization-reserve-20260816-v1"
R8_DEVELOPMENT_EVIDENCE_PATH = (
    "reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r8-evidence-r4.json"
)
R8_DEVELOPMENT_EVIDENCE_FILE_SHA256 = (
    "sha256:5035421a63d58fededab133b77c72e23ee4ad6d380a37c8d1157ce7480b7c62c"
)
R8_DEVELOPMENT_EVIDENCE_FILE_BYTES = 19_557
R8_TRACE_SNAPSHOT_PATH = ".patchloop/state.sqlite3"
R8_TRACE_SNAPSHOT_FILE_SHA256 = (
    "sha256:6b5d40b52dd21fd905d1a3fd5039de6a5559365aa33e9b5e817466b4201f672a"
)
R8_TRACE_SNAPSHOT_FILE_BYTES = 98_025_472
R8_FINALIZATION_RESERVE_ARTIFACT_PATH = (
    "experiments/lean-harness-finalization-reserve-20260816-v1.json"
)
R8_FINALIZATION_RESERVE_ARTIFACT_FILE_SHA256 = (
    "sha256:30cf34a19c94025777df612b283376be5d08047069f3c49e19b58e950434bf06"
)
R8_FINALIZATION_RESERVE_ARTIFACT_FILE_BYTES = 6_036

FinalizationToolName = Literal[
    "read_file",
    "apply_patch",
    "run_check",
    "get_diff",
    "finish_task",
]
RequestMode = Literal["exploration", "finalization", "block"]
TokenDimension = Literal["input_tokens", "output_tokens", "total_tokens"]
Condition = Literal["no_memory", "structured"]

_FINALIZATION_TOOLS: tuple[FinalizationToolName, ...] = (
    "read_file",
    "apply_patch",
    "run_check",
    "get_diff",
    "finish_task",
)
_DIMENSION_ORDER: tuple[TokenDimension, ...] = (
    "input_tokens",
    "output_tokens",
    "total_tokens",
)
_EVIDENCE_STATE_FIELDS = {
    "worktree_diff_hash",
    "mutation_event_sequence",
    "mutation_present",
    "completed_checks",
    "pending_checks",
    "current_diff_check_event_sequences",
    "latest_check_sequence",
    "review_event_sequence",
    "review_presented_to_model",
    "task_review_event_sequence",
    "task_review_presented_to_model",
    "task_review_coverage_complete",
    "unresolved_coverage_target_ids",
    "submission_ready",
    "missing_evidence",
    "allowed_next_actions",
}


class FinalizationTurnObservation(BaseModel):
    """Sanitized public-development evidence for one model turn."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    event_sequence: int = Field(ge=1)
    requested_input_tokens: int = Field(ge=1)
    output_tokens: int = Field(ge=0)
    tool_names: tuple[FinalizationToolName, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_turn(self) -> Self:
        if len(set(self.tool_names)) != len(self.tool_names):
            raise ValueError("finalization turn tool names must be unique")
        return self


class FinalizationRunObservation(BaseModel):
    """Trailing finalization lifecycle for one resolved public run."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    run_id: str = Field(pattern=r"^run_[0-9a-f]{16}$")
    task_id: str = Field(min_length=1)
    condition: Condition
    visible_check_count: Literal[1]
    turns: tuple[FinalizationTurnObservation, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_lifecycle(self) -> Self:
        sequences = tuple(turn.event_sequence for turn in self.turns)
        if tuple(sorted(sequences)) != sequences or len(set(sequences)) != len(sequences):
            raise ValueError("finalization turn sequences must be unique and increasing")
        if not any("apply_patch" in turn.tool_names for turn in self.turns):
            raise ValueError("finalization lifecycle must include its final mutation")
        terminal_tools = tuple(turn.tool_names for turn in self.turns[-3:])
        if terminal_tools != (("run_check",), ("get_diff",), ("finish_task",)):
            raise ValueError("finalization lifecycle must end check, diff, submit")
        return self


class FinalizationReserveContract(BaseModel):
    """Closed, zero-authority reserve candidate derived from public traces."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["finalization-reserve-contract-v1"]
    contract_id: Literal["r8-public-development-finalization-reserve-20260816-v1"]
    status: Literal["development-candidate-runtime-closed"]
    development_evidence_path: Literal[
        "reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r8-evidence-r4.json"
    ]
    development_evidence_file_sha256: Literal[
        "sha256:5035421a63d58fededab133b77c72e23ee4ad6d380a37c8d1157ce7480b7c62c"
    ]
    development_evidence_file_bytes: Literal[19557]
    trace_snapshot_path: Literal[".patchloop/state.sqlite3"]
    trace_snapshot_file_sha256: Literal[
        "sha256:6b5d40b52dd21fd905d1a3fd5039de6a5559365aa33e9b5e817466b4201f672a"
    ]
    trace_snapshot_file_bytes: Literal[98025472]
    trace_snapshot_checked_in: Literal[False]
    source_tool_schema_version: Literal["v2"]
    source_context_policy_version: Literal["phase-evidence-v5"]
    public_task_count: Literal[2]
    resolved_run_count: Literal[4]
    observations: tuple[FinalizationRunObservation, ...]
    observed_max_model_turns: Literal[5]
    observed_max_requested_input_tokens_per_turn: Literal[15801]
    observed_max_output_tokens_per_turn: Literal[3046]
    rounding_quantum_tokens: Literal[5000]
    max_requested_input_tokens_per_turn: Literal[20000]
    max_output_tokens_per_turn: Literal[5000]
    base_non_check_model_turns: Literal[4]
    check_model_turns_per_visible_check: Literal[1]
    supported_visible_check_count: Literal[1]
    reserved_model_turns: Literal[5]
    reserved_input_tokens: Literal[100000]
    reserved_output_tokens: Literal[25000]
    reserved_total_tokens: Literal[125000]
    finalization_tool_names: tuple[FinalizationToolName, ...]
    raw_trace_replayable_from_checked_in_files: Literal[False]
    requires_public_development_requalification: Literal[True]
    runtime_activation_authorized: Literal[False]
    provider_calls_authorized: Literal[False]
    fresh_panel_authorized: Literal[False]
    content_hash: Literal["sha256:9458bb1d59d51aaf94a082504a3883d799bf4d807ce7a83376bdc391ab6348db"]

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        if len(self.observations) != self.resolved_run_count:
            raise ValueError("resolved run observations are incomplete")
        if len({item.run_id for item in self.observations}) != len(self.observations):
            raise ValueError("resolved run IDs must be unique")
        if len({item.task_id for item in self.observations}) != self.public_task_count:
            raise ValueError("public task count does not match observations")
        task_conditions: dict[str, set[Condition]] = {}
        for item in self.observations:
            task_conditions.setdefault(item.task_id, set()).add(item.condition)
        if any(values != {"no_memory", "structured"} for values in task_conditions.values()):
            raise ValueError("each public task must contribute equal A/C observations")

        observed_turns = max(len(item.turns) for item in self.observations)
        observed_input = max(
            turn.requested_input_tokens for item in self.observations for turn in item.turns
        )
        observed_output = max(
            turn.output_tokens for item in self.observations for turn in item.turns
        )
        if (
            observed_turns,
            observed_input,
            observed_output,
        ) != (
            self.observed_max_model_turns,
            self.observed_max_requested_input_tokens_per_turn,
            self.observed_max_output_tokens_per_turn,
        ):
            raise ValueError("observed reserve maxima do not match turn evidence")

        quantum = self.rounding_quantum_tokens
        rounded_input = ((observed_input + quantum - 1) // quantum) * quantum
        rounded_output = ((observed_output + quantum - 1) // quantum) * quantum
        if (
            self.max_requested_input_tokens_per_turn,
            self.max_output_tokens_per_turn,
        ) != (rounded_input, rounded_output):
            raise ValueError("per-turn reserve must be the exact rounded public maximum")
        turns = (
            self.base_non_check_model_turns
            + self.check_model_turns_per_visible_check * self.supported_visible_check_count
        )
        if self.reserved_model_turns != turns or turns != observed_turns:
            raise ValueError("reserved model turns do not match the frozen formula")
        if self.reserved_input_tokens != turns * rounded_input:
            raise ValueError("reserved input tokens do not match per-turn reserve")
        if self.reserved_output_tokens != turns * rounded_output:
            raise ValueError("reserved output tokens do not match per-turn reserve")
        if self.reserved_total_tokens != (self.reserved_input_tokens + self.reserved_output_tokens):
            raise ValueError("reserved total tokens do not match split reserve")
        if self.finalization_tool_names != _FINALIZATION_TOOLS:
            raise ValueError("finalization tool surface differs from public evidence")

        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("finalization reserve content hash differs")
        return self


class FinalizationRequestMode(BaseModel):
    """Pre-rebuild decision that preserves the candidate finalization reserve."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["finalization-request-mode-v1"]
    mode: RequestMode
    reserve_contract_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    requested_input_tokens: int = Field(ge=0)
    configured_max_output_tokens: int = Field(ge=1)
    input_tokens_used: int = Field(ge=0)
    output_tokens_used: int = Field(ge=0)
    max_cumulative_input_tokens: int = Field(ge=1)
    max_cumulative_output_tokens: int = Field(ge=1)
    max_total_tokens: int = Field(ge=1)
    reserved_input_tokens: int = Field(ge=1)
    reserved_output_tokens: int = Field(ge=1)
    reserved_total_tokens: int = Field(ge=1)
    reserve_constrained_dimensions: tuple[TokenDimension, ...]
    request_rebuild_required: bool
    exact_input_recount_required: bool
    investigation_allowed: bool
    provider_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_mode(self) -> Self:
        total_used = self.input_tokens_used + self.output_tokens_used
        if self.input_tokens_used > self.max_cumulative_input_tokens:
            raise ValueError("input usage exceeds the cumulative limit")
        if self.output_tokens_used > self.max_cumulative_output_tokens:
            raise ValueError("output usage exceeds the cumulative limit")
        if total_used > self.max_total_tokens:
            raise ValueError("total usage exceeds the cumulative limit")
        if self.reserved_total_tokens != (self.reserved_input_tokens + self.reserved_output_tokens):
            raise ValueError("mode reserve split is inconsistent")

        remaining_input = self.max_cumulative_input_tokens - self.input_tokens_used
        remaining_output = self.max_cumulative_output_tokens - self.output_tokens_used
        remaining_total = self.max_total_tokens - total_used
        constrained = {
            "input_tokens": (
                self.requested_input_tokens + self.reserved_input_tokens > remaining_input
            ),
            "output_tokens": (
                self.configured_max_output_tokens + self.reserved_output_tokens > remaining_output
            ),
            "total_tokens": (
                self.requested_input_tokens
                + self.configured_max_output_tokens
                + self.reserved_total_tokens
                > remaining_total
            ),
        }
        expected_constraints = tuple(
            dimension for dimension in _DIMENSION_ORDER if constrained[dimension]
        )
        no_request_possible = remaining_input == 0 or remaining_output == 0 or remaining_total == 0
        if no_request_possible:
            expected_mode: RequestMode = "block"
        elif expected_constraints:
            expected_mode = "finalization"
        else:
            expected_mode = "exploration"
        if self.reserve_constrained_dimensions != expected_constraints:
            raise ValueError("reserve-constrained dimensions are inconsistent")
        if self.mode != expected_mode:
            raise ValueError("request mode is inconsistent")
        expected_rebuild = expected_mode == "finalization"
        if self.request_rebuild_required is not expected_rebuild:
            raise ValueError("request rebuild decision is inconsistent")
        if self.exact_input_recount_required is not expected_rebuild:
            raise ValueError("exact input recount decision is inconsistent")
        if self.investigation_allowed is not (expected_mode == "exploration"):
            raise ValueError("investigation decision is inconsistent")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("request mode content hash differs")
        return self


class PhaseToolSurfaceProjection(BaseModel):
    """Exact phase filter over the tool schemas that will enter a request."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["phase-tool-surface-projection-v1"]
    mode: Literal["exploration", "finalization"]
    reserve_contract_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    finalization_tool_names: tuple[FinalizationToolName, ...]
    phase_evidence: dict[str, Any]
    phase_evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    phase_allowed_actions: tuple[str, ...]
    source_tool_schemas: tuple[dict[str, Any], ...]
    selected_tool_schemas: tuple[dict[str, Any], ...]
    source_tool_names: tuple[str, ...]
    selected_tool_names: tuple[str, ...]
    removed_tool_names: tuple[str, ...]
    source_tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    selected_tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    request_rebuild_required: bool
    exact_input_recount_required: bool
    provider_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_surface(self) -> Self:
        source_names = _tool_names(self.source_tool_schemas)
        selected_names = _tool_names(self.selected_tool_schemas)
        if self.source_tool_names != source_names:
            raise ValueError("source tool names differ from source schemas")
        if self.selected_tool_names != selected_names:
            raise ValueError("selected tool names differ from selected schemas")
        if set(self.phase_evidence) != _EVIDENCE_STATE_FIELDS:
            raise ValueError("phase evidence fields differ from EvidenceState")
        if self.phase_evidence_hash != sha256_json(self.phase_evidence):
            raise ValueError("phase evidence hash differs")
        evidence_actions = self.phase_evidence.get("allowed_next_actions")
        if type(evidence_actions) not in {tuple, list}:
            raise ValueError("phase evidence allowed actions are invalid")
        if self.phase_allowed_actions != tuple(evidence_actions):
            raise ValueError("phase allowed actions differ from phase evidence")
        if len(set(self.phase_allowed_actions)) != len(self.phase_allowed_actions):
            raise ValueError("phase allowed actions must be unique")
        if any(name not in source_names for name in self.phase_allowed_actions):
            raise ValueError("phase allowed actions contain an unknown tool")
        allowed = set(self.phase_allowed_actions)
        if self.mode == "finalization":
            if self.finalization_tool_names != _FINALIZATION_TOOLS:
                raise ValueError("finalization tool names differ from the contract")
            allowed &= set(self.finalization_tool_names)
        expected_selected = tuple(name for name in source_names if name in allowed)
        if selected_names != expected_selected:
            raise ValueError("selected tool surface is inconsistent")
        selected_set = set(selected_names)
        expected_removed = tuple(name for name in source_names if name not in selected_set)
        if self.removed_tool_names != expected_removed:
            raise ValueError("removed tool names are inconsistent")
        if self.source_tool_schema_hash != sha256_json(list(self.source_tool_schemas)):
            raise ValueError("source tool schema hash differs")
        if self.selected_tool_schema_hash != sha256_json(list(self.selected_tool_schemas)):
            raise ValueError("selected tool schema hash differs")
        changed = self.source_tool_schema_hash != self.selected_tool_schema_hash
        if self.request_rebuild_required is not changed:
            raise ValueError("tool-surface rebuild decision is inconsistent")
        if self.exact_input_recount_required is not changed:
            raise ValueError("tool-surface recount decision is inconsistent")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("tool surface content hash differs")
        return self


class FinalizationRequestEvidence(BaseModel):
    """Recounted finalization request evidence, still without call authority."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["finalization-request-evidence-v1"]
    request_mode_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    reserve_contract_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    tool_surface_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    selected_tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    reserve_contract: FinalizationReserveContract
    request_mode: FinalizationRequestMode
    tool_surface: PhaseToolSurfaceProjection
    recounted_input_tokens: int = Field(ge=0)
    allowance: SplitAwareRequestAllowance
    provider_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        if self.reserve_contract_hash != self.reserve_contract.content_hash:
            raise ValueError("nested reserve contract hash differs")
        if self.request_mode_hash != self.request_mode.content_hash:
            raise ValueError("nested request mode hash differs")
        if self.tool_surface_hash != self.tool_surface.content_hash:
            raise ValueError("nested tool surface hash differs")
        if self.selected_tool_schema_hash != self.tool_surface.selected_tool_schema_hash:
            raise ValueError("selected tool schema hash differs")
        if self.request_mode.reserve_contract_hash != self.reserve_contract_hash:
            raise ValueError("request mode reserve contract differs")
        if self.tool_surface.reserve_contract_hash != self.reserve_contract_hash:
            raise ValueError("tool surface reserve contract differs")
        if self.request_mode.mode != "finalization":
            raise ValueError("request evidence requires finalization mode")
        if self.tool_surface.mode != "finalization":
            raise ValueError("request evidence requires a finalization surface")
        if self.allowance.requested_input_tokens != self.recounted_input_tokens:
            raise ValueError("recounted input differs from split allowance")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("finalization request evidence hash differs")
        return self


def _exact_ints(values: dict[str, int]) -> None:
    for name, value in values.items():
        if type(value) is not int:
            raise TypeError(f"{name} must be an exact integer")


def _tool_names(schemas: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
    names: list[str] = []
    for schema in schemas:
        if type(schema) is not dict:
            raise TypeError("each tool schema must be an exact mapping")
        if schema.get("type") != "function":
            raise ValueError("tool schema type must be function")
        name = schema.get("name")
        if type(name) is not str or not name:
            raise ValueError("tool schema name must be a nonempty exact string")
        names.append(name)
    if len(set(names)) != len(names):
        raise ValueError("tool schema names must be unique")
    return tuple(names)


def _build_hashed(model_type: type[BaseModel], body: dict[str, Any]) -> Any:
    return model_type.model_validate({**body, "content_hash": sha256_json(body)})


def _reject_duplicate_json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate finalization contract key: {key}")
        result[key] = value
    return result


def r8_public_development_finalization_reserve() -> FinalizationReserveContract:
    """Return the immutable R8-derived reserve candidate with zero authority."""

    observations = (
        FinalizationRunObservation(
            run_id="run_5a3113600554429e",
            task_id="moto-query-scanned-count",
            condition="no_memory",
            visible_check_count=1,
            turns=(
                FinalizationTurnObservation(
                    event_sequence=58,
                    requested_input_tokens=14_327,
                    output_tokens=1_552,
                    tool_names=("apply_patch",),
                ),
                FinalizationTurnObservation(
                    event_sequence=63,
                    requested_input_tokens=14_248,
                    output_tokens=1_336,
                    tool_names=("apply_patch",),
                ),
                FinalizationTurnObservation(
                    event_sequence=72,
                    requested_input_tokens=7_620,
                    output_tokens=75,
                    tool_names=("run_check",),
                ),
                FinalizationTurnObservation(
                    event_sequence=78,
                    requested_input_tokens=5_986,
                    output_tokens=150,
                    tool_names=("get_diff",),
                ),
                FinalizationTurnObservation(
                    event_sequence=84,
                    requested_input_tokens=5_795,
                    output_tokens=85,
                    tool_names=("finish_task",),
                ),
            ),
        ),
        FinalizationRunObservation(
            run_id="run_69f76b4948af4d9d",
            task_id="moto-query-scanned-count",
            condition="structured",
            visible_check_count=1,
            turns=(
                FinalizationTurnObservation(
                    event_sequence=36,
                    requested_input_tokens=15_801,
                    output_tokens=992,
                    tool_names=("apply_patch",),
                ),
                FinalizationTurnObservation(
                    event_sequence=45,
                    requested_input_tokens=8_926,
                    output_tokens=106,
                    tool_names=("run_check",),
                ),
                FinalizationTurnObservation(
                    event_sequence=51,
                    requested_input_tokens=6_605,
                    output_tokens=130,
                    tool_names=("get_diff",),
                ),
                FinalizationTurnObservation(
                    event_sequence=57,
                    requested_input_tokens=6_384,
                    output_tokens=244,
                    tool_names=("finish_task",),
                ),
            ),
        ),
        FinalizationRunObservation(
            run_id="run_d10f4197b45342d5",
            task_id="babel-strict-grouped-decimal-trailing-zeroes",
            condition="structured",
            visible_check_count=1,
            turns=(
                FinalizationTurnObservation(
                    event_sequence=25,
                    requested_input_tokens=13_578,
                    output_tokens=1_868,
                    tool_names=("apply_patch",),
                ),
                FinalizationTurnObservation(
                    event_sequence=34,
                    requested_input_tokens=8_441,
                    output_tokens=115,
                    tool_names=("run_check",),
                ),
                FinalizationTurnObservation(
                    event_sequence=40,
                    requested_input_tokens=8_736,
                    output_tokens=242,
                    tool_names=("get_diff",),
                ),
                FinalizationTurnObservation(
                    event_sequence=46,
                    requested_input_tokens=8_525,
                    output_tokens=133,
                    tool_names=("finish_task",),
                ),
            ),
        ),
        FinalizationRunObservation(
            run_id="run_cc33bef38c8a42d0",
            task_id="babel-strict-grouped-decimal-trailing-zeroes",
            condition="no_memory",
            visible_check_count=1,
            turns=(
                FinalizationTurnObservation(
                    event_sequence=53,
                    requested_input_tokens=11_975,
                    output_tokens=3_046,
                    tool_names=("apply_patch",),
                ),
                FinalizationTurnObservation(
                    event_sequence=60,
                    requested_input_tokens=7_667,
                    output_tokens=168,
                    tool_names=("read_file",),
                ),
                FinalizationTurnObservation(
                    event_sequence=65,
                    requested_input_tokens=8_319,
                    output_tokens=122,
                    tool_names=("run_check",),
                ),
                FinalizationTurnObservation(
                    event_sequence=71,
                    requested_input_tokens=10_517,
                    output_tokens=66,
                    tool_names=("get_diff",),
                ),
                FinalizationTurnObservation(
                    event_sequence=77,
                    requested_input_tokens=10_281,
                    output_tokens=140,
                    tool_names=("finish_task",),
                ),
            ),
        ),
    )
    body: dict[str, Any] = {
        "schema_version": FINALIZATION_RESERVE_CONTRACT_SCHEMA,
        "contract_id": R8_FINALIZATION_RESERVE_CONTRACT_ID,
        "status": "development-candidate-runtime-closed",
        "development_evidence_path": R8_DEVELOPMENT_EVIDENCE_PATH,
        "development_evidence_file_sha256": R8_DEVELOPMENT_EVIDENCE_FILE_SHA256,
        "development_evidence_file_bytes": R8_DEVELOPMENT_EVIDENCE_FILE_BYTES,
        "trace_snapshot_path": R8_TRACE_SNAPSHOT_PATH,
        "trace_snapshot_file_sha256": R8_TRACE_SNAPSHOT_FILE_SHA256,
        "trace_snapshot_file_bytes": R8_TRACE_SNAPSHOT_FILE_BYTES,
        "trace_snapshot_checked_in": False,
        "source_tool_schema_version": "v2",
        "source_context_policy_version": "phase-evidence-v5",
        "public_task_count": 2,
        "resolved_run_count": 4,
        "observations": tuple(item.model_dump(mode="python") for item in observations),
        "observed_max_model_turns": 5,
        "observed_max_requested_input_tokens_per_turn": 15_801,
        "observed_max_output_tokens_per_turn": 3_046,
        "rounding_quantum_tokens": 5_000,
        "max_requested_input_tokens_per_turn": 20_000,
        "max_output_tokens_per_turn": 5_000,
        "base_non_check_model_turns": 4,
        "check_model_turns_per_visible_check": 1,
        "supported_visible_check_count": 1,
        "reserved_model_turns": 5,
        "reserved_input_tokens": 100_000,
        "reserved_output_tokens": 25_000,
        "reserved_total_tokens": 125_000,
        "finalization_tool_names": _FINALIZATION_TOOLS,
        "raw_trace_replayable_from_checked_in_files": False,
        "requires_public_development_requalification": True,
        "runtime_activation_authorized": False,
        "provider_calls_authorized": False,
        "fresh_panel_authorized": False,
    }
    return _build_hashed(FinalizationReserveContract, body)


def load_r8_public_development_finalization_reserve(
    repository: str | Path = ".",
) -> FinalizationReserveContract:
    """Load the exact append-only candidate without opening trace/runtime state."""

    root = Path(repository).resolve()
    path = ensure_within(root, R8_FINALIZATION_RESERVE_ARTIFACT_PATH)
    raw = path.read_bytes()
    if len(raw) != R8_FINALIZATION_RESERVE_ARTIFACT_FILE_BYTES:
        raise ValueError("finalization reserve artifact byte length differs")
    if sha256_bytes(raw) != R8_FINALIZATION_RESERVE_ARTIFACT_FILE_SHA256:
        raise ValueError("finalization reserve artifact file hash differs")
    try:
        text = raw.decode("utf-8")
        json.loads(text, object_pairs_hook=_reject_duplicate_json_pairs)
        loaded = FinalizationReserveContract.model_validate_json(text)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("finalization reserve artifact is invalid") from exc
    expected = r8_public_development_finalization_reserve()
    if loaded != expected:
        raise ValueError("finalization reserve artifact differs from source contract")
    return loaded


def project_finalization_request_mode(
    *,
    reserve: FinalizationReserveContract,
    requested_input_tokens: int,
    configured_max_output_tokens: int,
    input_tokens_used: int,
    output_tokens_used: int,
    max_cumulative_input_tokens: int,
    max_cumulative_output_tokens: int,
    max_total_tokens: int,
) -> FinalizationRequestMode:
    """Decide whether exploration still leaves the frozen finalization reserve."""

    values = {
        "requested_input_tokens": requested_input_tokens,
        "configured_max_output_tokens": configured_max_output_tokens,
        "input_tokens_used": input_tokens_used,
        "output_tokens_used": output_tokens_used,
        "max_cumulative_input_tokens": max_cumulative_input_tokens,
        "max_cumulative_output_tokens": max_cumulative_output_tokens,
        "max_total_tokens": max_total_tokens,
    }
    _exact_ints(values)
    if requested_input_tokens < 0 or input_tokens_used < 0 or output_tokens_used < 0:
        raise ValueError("request and usage tokens must be nonnegative")
    if (
        configured_max_output_tokens <= 0
        or max_cumulative_input_tokens <= 0
        or max_cumulative_output_tokens <= 0
        or max_total_tokens <= 0
    ):
        raise ValueError("configured output and cumulative limits must be positive")

    total_used = input_tokens_used + output_tokens_used
    if input_tokens_used > max_cumulative_input_tokens:
        raise ValueError("input usage exceeds the cumulative limit")
    if output_tokens_used > max_cumulative_output_tokens:
        raise ValueError("output usage exceeds the cumulative limit")
    if total_used > max_total_tokens:
        raise ValueError("total usage exceeds the cumulative limit")
    remaining_input = max_cumulative_input_tokens - input_tokens_used
    remaining_output = max_cumulative_output_tokens - output_tokens_used
    remaining_total = max_total_tokens - total_used
    constrained = {
        "input_tokens": requested_input_tokens + reserve.reserved_input_tokens > remaining_input,
        "output_tokens": configured_max_output_tokens + reserve.reserved_output_tokens
        > remaining_output,
        "total_tokens": (
            requested_input_tokens + configured_max_output_tokens + reserve.reserved_total_tokens
            > remaining_total
        ),
    }
    constrained_dimensions = tuple(
        dimension for dimension in _DIMENSION_ORDER if constrained[dimension]
    )
    if remaining_input == 0 or remaining_output == 0 or remaining_total == 0:
        mode: RequestMode = "block"
    elif constrained_dimensions:
        mode = "finalization"
    else:
        mode = "exploration"
    body: dict[str, Any] = {
        "schema_version": FINALIZATION_REQUEST_MODE_SCHEMA,
        "mode": mode,
        "reserve_contract_hash": reserve.content_hash,
        **values,
        "reserved_input_tokens": reserve.reserved_input_tokens,
        "reserved_output_tokens": reserve.reserved_output_tokens,
        "reserved_total_tokens": reserve.reserved_total_tokens,
        "reserve_constrained_dimensions": constrained_dimensions,
        "request_rebuild_required": mode == "finalization",
        "exact_input_recount_required": mode == "finalization",
        "investigation_allowed": mode == "exploration",
        "provider_calls_authorized": False,
    }
    return _build_hashed(FinalizationRequestMode, body)


def project_phase_tool_surface(
    *,
    reserve: FinalizationReserveContract,
    tool_schemas: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    phase_evidence: EvidenceState,
    mode: Literal["exploration", "finalization"],
) -> PhaseToolSurfaceProjection:
    """Filter an exact tool surface by phase and finalization mode."""

    if type(tool_schemas) not in {list, tuple}:
        raise TypeError("tool_schemas must be an exact list or tuple")
    if type(phase_evidence) is not EvidenceState:
        raise TypeError("phase_evidence must be an exact EvidenceState")
    if type(mode) is not str or mode not in {"exploration", "finalization"}:
        raise ValueError("mode must be exploration or finalization")
    source_schemas = tuple(copy.deepcopy(item) for item in tool_schemas)
    source_names = _tool_names(source_schemas)
    phase_evidence_body = asdict(phase_evidence)
    phase_allowed_actions = phase_evidence.allowed_next_actions
    if len(set(phase_allowed_actions)) != len(phase_allowed_actions):
        raise ValueError("phase allowed actions must be unique")
    if any(type(name) is not str or name not in source_names for name in phase_allowed_actions):
        raise ValueError("phase allowed actions contain an unknown tool")
    allowed = set(phase_allowed_actions)
    if mode == "finalization":
        allowed &= set(reserve.finalization_tool_names)
    selected_schemas = tuple(
        copy.deepcopy(schema)
        for name, schema in zip(source_names, source_schemas, strict=True)
        if name in allowed
    )
    if not selected_schemas:
        raise ValueError("phase filter leaves no callable tool")
    selected_names = _tool_names(selected_schemas)
    removed_names = tuple(name for name in source_names if name not in set(selected_names))
    source_hash = sha256_json(list(source_schemas))
    selected_hash = sha256_json(list(selected_schemas))
    changed = source_hash != selected_hash
    body: dict[str, Any] = {
        "schema_version": PHASE_TOOL_SURFACE_PROJECTION_SCHEMA,
        "mode": mode,
        "reserve_contract_hash": reserve.content_hash,
        "finalization_tool_names": reserve.finalization_tool_names,
        "phase_evidence": phase_evidence_body,
        "phase_evidence_hash": sha256_json(phase_evidence_body),
        "phase_allowed_actions": phase_allowed_actions,
        "source_tool_schemas": source_schemas,
        "selected_tool_schemas": selected_schemas,
        "source_tool_names": source_names,
        "selected_tool_names": selected_names,
        "removed_tool_names": removed_names,
        "source_tool_schema_hash": source_hash,
        "selected_tool_schema_hash": selected_hash,
        "request_rebuild_required": changed,
        "exact_input_recount_required": changed,
        "provider_calls_authorized": False,
    }
    return _build_hashed(PhaseToolSurfaceProjection, body)


def project_recounted_finalization_request(
    *,
    reserve: FinalizationReserveContract,
    request_mode: FinalizationRequestMode,
    tool_surface: PhaseToolSurfaceProjection,
    recounted_input_tokens: int,
) -> FinalizationRequestEvidence:
    """Bind a rebuilt tool surface to a newly counted split-aware allowance."""

    if request_mode.mode != "finalization":
        raise ValueError("recounted finalization requires finalization mode")
    if tool_surface.mode != "finalization":
        raise ValueError("recounted finalization requires a finalization surface")
    if request_mode.reserve_contract_hash != reserve.content_hash:
        raise ValueError("request mode reserve binding differs")
    if tool_surface.reserve_contract_hash != reserve.content_hash:
        raise ValueError("tool surface reserve binding differs")
    if type(recounted_input_tokens) is not int:
        raise TypeError("recounted_input_tokens must be an exact integer")
    allowance = project_split_aware_request_allowance(
        requested_input_tokens=recounted_input_tokens,
        configured_max_output_tokens=reserve.max_output_tokens_per_turn,
        input_tokens_used=request_mode.input_tokens_used,
        output_tokens_used=request_mode.output_tokens_used,
        max_cumulative_input_tokens=request_mode.max_cumulative_input_tokens,
        max_cumulative_output_tokens=request_mode.max_cumulative_output_tokens,
        max_total_tokens=request_mode.max_total_tokens,
    )
    body: dict[str, Any] = {
        "schema_version": FINALIZATION_REQUEST_EVIDENCE_SCHEMA,
        "request_mode_hash": request_mode.content_hash,
        "reserve_contract_hash": reserve.content_hash,
        "tool_surface_hash": tool_surface.content_hash,
        "selected_tool_schema_hash": tool_surface.selected_tool_schema_hash,
        "reserve_contract": reserve.model_dump(mode="python"),
        "request_mode": request_mode.model_dump(mode="python"),
        "tool_surface": tool_surface.model_dump(mode="python"),
        "recounted_input_tokens": recounted_input_tokens,
        "allowance": allowance.model_dump(mode="python"),
        "provider_calls_authorized": False,
    }
    return _build_hashed(FinalizationRequestEvidence, body)
