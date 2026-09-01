"""Public no-call qualification for descriptor-compacted request shadows."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.context import build_context_with_evidence
from patchloop.agent.context_dedup_qualification import (
    CONDITIONS,
    CONTEXT_POLICY_VERSION,
    FRAME_PHASES,
    TASK_PATHS,
    PublicTaskBinding,
    QualificationFileBinding,
    _adapter,
    _file_binding,
    _FixtureStore,
    _phase_frame,
    _public_events,
    _repository_root,
    _task_binding,
)
from patchloop.agent.context_event_compaction_qualification import (
    QUALIFICATION_PATH as PREDECESSOR_PATH,
)
from patchloop.agent.context_event_compaction_qualification import (
    EventCompactionPublicQualification,
    load_event_compaction_public_qualification,
)
from patchloop.agent.context_event_shadow import (
    project_lean_harness_compacted_shadow_request,
)
from patchloop.agent.finalization import (
    r8_public_development_finalization_reserve,
)
from patchloop.agent.model import SYSTEM_PROMPT_V3
from patchloop.agent.phases import EvidenceState
from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.contracts import Budget, MemoryCondition, Usage
from patchloop.errors import RecoveryError
from patchloop.memory.fixed_bundle import (
    FIXED_BUNDLE_BYTES,
    FIXED_BUNDLE_SHA256,
    build_fixed_memory_delivery,
)
from patchloop.task_loader import load_public_task
from patchloop.util import sha256_bytes, sha256_json

QUALIFICATION_SCHEMA = "lean-harness-compacted-shadow-public-qualification-v1"
QUALIFICATION_ID = "lean-harness-compacted-shadow-public-20260816-v1"
QUALIFICATION_PATH = (
    "experiments/lean-harness-compacted-shadow-public-qualification-20260816-v1.json"
)
PREDECESSOR_BYTES = 41_798
PREDECESSOR_FILE_SHA256 = "sha256:3d1a7b4c2f11f3ab749fdc45e6ec27c170f626dfbd9cdde8e61366f44d99aa05"
PREDECESSOR_CONTENT_HASH = "sha256:53f625b335f09bf8144a2b8b2d58425e84bbc151e5207bd82c46f35d2fa5562e"
INTEGRATION_THRESHOLD_BASIS_POINTS = 100
EXPECTED_PHASE_ALLOWED_ACTIONS = {
    "INTAKE": ("apply_patch", "run_check", "read_file", "search_files"),
    "REPRODUCE": ("apply_patch", "run_check", "read_file", "search_files"),
    "PLAN": ("apply_patch", "run_check", "read_file", "search_files"),
    "IMPLEMENT": ("run_check", "apply_patch", "read_file", "search_files"),
    "VERIFY": ("get_diff", "apply_patch", "read_file", "search_files"),
    "REVIEW": ("get_diff", "apply_patch", "read_file", "search_files"),
}

SOURCE_PATHS = (
    "patchloop/agent/context.py",
    "patchloop/agent/context_dedup_qualification.py",
    "patchloop/agent/context_event_compaction.py",
    "patchloop/agent/context_event_compaction_qualification.py",
    "patchloop/agent/context_event_shadow.py",
    "patchloop/agent/context_event_shadow_qualification.py",
    "patchloop/agent/shadow_runtime.py",
    "patchloop/agent/finalization.py",
    "patchloop/agent/request_allowance.py",
    "patchloop/agent/model.py",
    "patchloop/agent/tools.py",
    "patchloop/agent/phases.py",
    "patchloop/memory/fixed_bundle.py",
    "patchloop/task_loader.py",
    "patchloop/contracts.py",
    "patchloop/errors.py",
    "patchloop/util.py",
    "scripts/build_lean_harness_compacted_shadow_qualification.py",
)
VALIDATION_PATHS = (
    "tests/test_context_event_compaction.py",
    "tests/test_context_event_shadow.py",
    "tests/test_shadow_runtime.py",
    "tests/test_context_event_shadow_qualification.py",
)


class CompactedShadowQualificationObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    frame_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_id: str = Field(min_length=1)
    task_path: str = Field(pattern=r"^tasks/dev-validation/[^/]+/public\.yaml$")
    condition: Literal["no_memory", "structured"]
    phase: Literal["INTAKE", "REPRODUCE", "PLAN", "IMPLEMENT", "VERIFY", "REVIEW"]
    frame_order: int = Field(ge=1, le=6)
    selected_memory_bytes: int = Field(ge=0)
    phase_evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    phase_allowed_actions: tuple[str, ...]
    selected_tool_names: tuple[str, ...]
    removed_tool_names: tuple[str, ...]
    source_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    compacted_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    removed_descriptor_count: int = Field(ge=0)
    baseline_source_request_bytes: int = Field(gt=0)
    compacted_source_request_bytes: int = Field(gt=0)
    source_request_bytes_saved: int = Field(ge=0)
    baseline_phase_request_bytes: int = Field(gt=0)
    compacted_phase_request_bytes: int = Field(gt=0)
    phase_request_bytes_saved: int = Field(ge=0)
    baseline_counted_input_units: int = Field(gt=0)
    compacted_counted_input_units: int = Field(gt=0)
    counted_input_units_saved: int = Field(ge=0)
    request_mode: Literal["exploration"]
    request_ready: Literal[True]
    compaction_evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    shadow_evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    exact_source_roundtrip: Literal[True]
    phase_tool_surface_unchanged: Literal[True]

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        expected_memory = FIXED_BUNDLE_BYTES if self.condition == "structured" else 0
        if self.selected_memory_bytes != expected_memory:
            raise ValueError("compacted shadow memory condition differs")
        if (
            self.source_request_bytes_saved
            != self.baseline_source_request_bytes - self.compacted_source_request_bytes
            or self.phase_request_bytes_saved
            != self.baseline_phase_request_bytes - self.compacted_phase_request_bytes
            or self.counted_input_units_saved
            != self.baseline_counted_input_units - self.compacted_counted_input_units
        ):
            raise ValueError("compacted shadow observation savings differ")
        if self.removed_descriptor_count:
            if (
                self.source_request_bytes_saved <= 0
                or self.phase_request_bytes_saved <= 0
                or self.counted_input_units_saved <= 0
            ):
                raise ValueError("compacted shadow observation did not decrease")
        elif any(
            value != 0
            for value in (
                self.source_request_bytes_saved,
                self.phase_request_bytes_saved,
                self.counted_input_units_saved,
            )
        ):
            raise ValueError("compacted shadow noop observation differs")
        return self


class CompactedShadowPublicQualification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-compacted-shadow-public-qualification-v1"]
    qualification_id: Literal["lean-harness-compacted-shadow-public-20260816-v1"]
    status: Literal["PUBLIC_NO_CALL_SHADOW_PHASE_POLICY_QUALIFIED_RUNTIME_CLOSED"]
    evidence_date: Literal["2026-08-16"]
    frame_source: Literal["deterministic-synthetic-public-events"]
    phase_evidence_source: Literal["rendered-phase-contract-derived-synthetic-evidence-state"]
    live_public_trace_files_read: Literal[0]
    live_public_trace_replay_verified: Literal[False]
    non_public_task_repository_files_read: Literal[0]
    predecessor_event_compaction: QualificationFileBinding
    predecessor_event_compaction_content_hash: Literal[
        "sha256:53f625b335f09bf8144a2b8b2d58425e84bbc151e5207bd82c46f35d2fa5562e"
    ]
    task_bindings: tuple[PublicTaskBinding, ...]
    frame_phases: tuple[str, ...]
    conditions: tuple[str, ...]
    expected_observations: Literal[24]
    context_policy_version: Literal["phase-evidence-v5"]
    model_id: Literal["gpt-5.4-mini-2026-03-17"]
    fixed_bundle_sha256: Literal[
        "sha256:572667d431aa75e4fe74bfc030a99f64245b77d9afa1c88e5d531129f708accf"
    ]
    fixed_bundle_bytes: Literal[3528]
    runtime_input_limit: Literal[1000000]
    runtime_output_limit: Literal[100000]
    runtime_total_limit: Literal[1100000]
    configured_max_output_tokens: Literal[25000]
    counter_contract: Literal["caller-attested-canonical-utf8-byte-proxy-v1"]
    provider_token_count_verified: Literal[False]
    observations: tuple[CompactedShadowQualificationObservation, ...]
    aggregate_baseline_phase_request_bytes: int = Field(gt=0)
    aggregate_compacted_phase_request_bytes: int = Field(gt=0)
    aggregate_phase_request_bytes_saved: int = Field(gt=0)
    aggregate_baseline_counted_input_units: int = Field(gt=0)
    aggregate_compacted_counted_input_units: int = Field(gt=0)
    aggregate_counted_input_units_saved: int = Field(gt=0)
    aggregate_removed_descriptor_count: int = Field(gt=0)
    frames_with_compaction: int = Field(gt=0)
    noop_frames: int = Field(ge=0)
    observed_phase_proxy_reduction_basis_points_floor: int = Field(ge=100)
    public_integration_threshold_basis_points: Literal[100]
    all_phase_tool_surfaces_exact: Literal[True]
    all_request_modes_unchanged: Literal[True]
    all_request_readiness_unchanged: Literal[True]
    exact_roundtrip_all: Literal[True]
    condition_neutral_projection: Literal[True]
    current_phase_policy_requalified: Literal[True]
    source_files: tuple[QualificationFileBinding, ...]
    validation_files: tuple[QualificationFileBinding, ...]
    source_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    public_task_files_read: Literal[2]
    private_task_files_read: Literal[0]
    hidden_files_read: Literal[0]
    reference_patches_read: Literal[0]
    in_memory_fixture_artifacts: Literal[8]
    adapter_payload_builds: Literal[96]
    isolated_count_calls: Literal[48]
    provider_transport_calls: Literal[0]
    provider_generation_calls: Literal[0]
    runner_calls: Literal[0]
    docker_calls: Literal[0]
    evaluator_calls: Literal[0]
    added_model_cost_usd: Literal[0]
    provider_calls_authorized: Literal[False]
    runner_activation_authorized: Literal[False]
    request_integration_authorized: Literal[False]
    request_persistence_authorized: Literal[False]
    state_mutation_authorized: Literal[False]
    paid_execution_authorized: Literal[False]
    next_gate: Literal[
        "freeze-condition-neutral-saturation-and-recovery-thresholds-from-separate-public-development-evidence"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_qualification(self) -> Self:
        predecessor = self.predecessor_event_compaction
        if (
            predecessor.path != PREDECESSOR_PATH
            or predecessor.file_bytes != PREDECESSOR_BYTES
            or predecessor.file_sha256 != PREDECESSOR_FILE_SHA256
        ):
            raise ValueError("compacted shadow predecessor differs")
        if (
            self.frame_phases != FRAME_PHASES
            or self.conditions != CONDITIONS
            or tuple(item.path for item in self.task_bindings) != TASK_PATHS
            or len(self.observations) != self.expected_observations
        ):
            raise ValueError("compacted shadow qualification frame differs")
        task_paths = {item.task_id: item.path for item in self.task_bindings}
        identities = {(item.task_id, item.phase, item.condition) for item in self.observations}
        expected_identities = {
            (task.task_id, phase, condition)
            for task in self.task_bindings
            for phase in FRAME_PHASES
            for condition in CONDITIONS
        }
        if identities != expected_identities or any(
            item.task_path != task_paths.get(item.task_id)
            or item.frame_order != FRAME_PHASES.index(item.phase) + 1
            or item.frame_id
            != sha256_json(
                {
                    "task_id": item.task_id,
                    "task_path": item.task_path,
                    "condition": item.condition,
                    "phase": item.phase,
                    "frame_order": item.frame_order,
                }
            )
            for item in self.observations
        ):
            raise ValueError("compacted shadow observation identity differs")
        source_tool_names = tuple(item["name"] for item in TOOL_SCHEMAS_V2)
        for item in self.observations:
            allowed = EXPECTED_PHASE_ALLOWED_ACTIONS[item.phase]
            selected = tuple(name for name in source_tool_names if name in set(allowed))
            removed = tuple(name for name in source_tool_names if name not in set(selected))
            if (
                item.phase_allowed_actions != allowed
                or item.selected_tool_names != selected
                or item.removed_tool_names != removed
            ):
                raise ValueError("compacted shadow phase policy differs")
        baseline_bytes = sum(item.baseline_phase_request_bytes for item in self.observations)
        compacted_bytes = sum(item.compacted_phase_request_bytes for item in self.observations)
        baseline_count = sum(item.baseline_counted_input_units for item in self.observations)
        compacted_count = sum(item.compacted_counted_input_units for item in self.observations)
        if (
            self.aggregate_baseline_phase_request_bytes != baseline_bytes
            or self.aggregate_compacted_phase_request_bytes != compacted_bytes
            or self.aggregate_phase_request_bytes_saved != baseline_bytes - compacted_bytes
            or self.aggregate_baseline_counted_input_units != baseline_count
            or self.aggregate_compacted_counted_input_units != compacted_count
            or self.aggregate_counted_input_units_saved != baseline_count - compacted_count
            or self.aggregate_removed_descriptor_count
            != sum(item.removed_descriptor_count for item in self.observations)
            or self.frames_with_compaction
            != sum(item.removed_descriptor_count > 0 for item in self.observations)
            or self.noop_frames
            != sum(item.removed_descriptor_count == 0 for item in self.observations)
        ):
            raise ValueError("compacted shadow aggregate differs")
        observed_basis_points = (
            self.aggregate_counted_input_units_saved * 10_000
        ) // self.aggregate_baseline_counted_input_units
        if (
            self.observed_phase_proxy_reduction_basis_points_floor != observed_basis_points
            or observed_basis_points < self.public_integration_threshold_basis_points
        ):
            raise ValueError("compacted shadow efficiency gate differs")
        if (
            tuple(item.path for item in self.source_files) != SOURCE_PATHS
            or tuple(item.path for item in self.validation_files) != VALIDATION_PATHS
        ):
            raise ValueError("compacted shadow source inventory differs")
        if self.source_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.source_files]
        ) or self.validation_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.validation_files]
        ):
            raise ValueError("compacted shadow inventory hash differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("compacted shadow qualification hash differs")
        return self


def _phase_evidence(rendered_context: str) -> EvidenceState:
    try:
        payload = json.loads(rendered_context)
    except json.JSONDecodeError as exc:
        raise RecoveryError("compacted shadow context is invalid JSON") from exc
    contract = payload.get("phase_contract")
    if type(contract) is not dict:
        raise RecoveryError("compacted shadow phase contract is absent")
    return EvidenceState(
        worktree_diff_hash=contract["current_diff_hash"],
        mutation_event_sequence=contract["mutation_event_sequence"],
        mutation_present=contract["mutation_present"],
        completed_checks=tuple(contract["completed_checks"]),
        pending_checks=tuple(contract["pending_checks"]),
        current_diff_check_event_sequences=(),
        latest_check_sequence=None,
        review_event_sequence=contract["review_event_sequence"],
        review_presented_to_model=False,
        task_review_event_sequence=None,
        task_review_presented_to_model=False,
        task_review_coverage_complete=None,
        unresolved_coverage_target_ids=(),
        submission_ready=contract["submission_ready"],
        missing_evidence=tuple(contract["missing_evidence"]),
        allowed_next_actions=tuple(contract["allowed_next_actions"]),
    )


def _condition_neutral(
    observations: list[CompactedShadowQualificationObservation],
) -> bool:
    grouped: dict[tuple[str, str], dict[str, CompactedShadowQualificationObservation]] = {}
    for item in observations:
        grouped.setdefault((item.task_id, item.phase), {})[item.condition] = item
    return all(
        set(pair) == set(CONDITIONS)
        and pair["no_memory"].phase_request_bytes_saved
        == pair["structured"].phase_request_bytes_saved
        and pair["no_memory"].counted_input_units_saved
        == pair["structured"].counted_input_units_saved
        and pair["no_memory"].selected_tool_names == pair["structured"].selected_tool_names
        for pair in grouped.values()
    )


def _predecessor_binding(
    root: Path,
) -> tuple[QualificationFileBinding, EventCompactionPublicQualification]:
    predecessor = load_event_compaction_public_qualification(root)
    raw = (root / PREDECESSOR_PATH).read_bytes()
    if (
        len(raw) != PREDECESSOR_BYTES
        or sha256_bytes(raw) != PREDECESSOR_FILE_SHA256
        or predecessor.content_hash != PREDECESSOR_CONTENT_HASH
    ):
        raise RecoveryError("event compaction predecessor identity differs")
    return _file_binding(root, PREDECESSOR_PATH), predecessor


def build_compacted_shadow_public_qualification(
    repository: str | Path = ".",
) -> CompactedShadowPublicQualification:
    root = _repository_root(repository)
    predecessor_binding, _ = _predecessor_binding(root)
    adapter, client = _adapter()
    store = _FixtureStore()
    budget = Budget(
        max_model_calls=240,
        max_tool_calls=400,
        max_total_tokens=1_100_000,
        wall_clock_timeout_seconds=3_600,
        token_budget_schema_version="cumulative-split-v1",
        max_cumulative_input_tokens=1_000_000,
        max_cumulative_output_tokens=100_000,
    )
    reserve = r8_public_development_finalization_reserve()
    deliveries = {
        condition: build_fixed_memory_delivery(
            condition=MemoryCondition(condition),
            repository=root,
        )
        for condition in CONDITIONS
    }
    observations: list[CompactedShadowQualificationObservation] = []
    task_bindings: list[PublicTaskBinding] = []
    fixture_paths: set[str] = set()
    for task_path in TASK_PATHS:
        task = load_public_task(root / task_path)
        task_bindings.append(_task_binding(root, task_path, task))
        events, diff_hash, _ = _public_events(store, task)
        fixture_paths.update(
            descriptor["path"]
            for event in events
            for field in ("input_artifact", "result_artifact")
            for descriptor in (event.payload.get(field),)
            if isinstance(descriptor, dict)
        )
        for frame_order, phase in enumerate(FRAME_PHASES, start=1):
            frame_events, checkpoint = _phase_frame(task, events, diff_hash, phase)
            for condition in CONDITIONS:
                delivery = deliveries[condition]
                built = build_context_with_evidence(
                    task,
                    frame_events,
                    checkpoint,
                    delivery.text,
                    policy_version=CONTEXT_POLICY_VERSION,
                    artifact_store=store,  # type: ignore[arg-type]
                    budget=budget,
                    max_output_tokens=25_000,
                )
                phase_evidence = _phase_evidence(built.rendered)
                shadow = project_lean_harness_compacted_shadow_request(
                    reserve=reserve,
                    adapter=adapter,
                    built_context=built,
                    system_prompt=SYSTEM_PROMPT_V3,
                    tool_schemas=TOOL_SCHEMAS_V2,
                    phase_evidence=phase_evidence,
                    usage=Usage(),
                    budget=budget,
                    isolated_client_attested=True,
                )
                identity = {
                    "task_id": task.task_id,
                    "task_path": task_path,
                    "condition": condition,
                    "phase": phase,
                    "frame_order": frame_order,
                }
                baseline = shadow.baseline_shadow
                compacted = shadow.compacted_shadow
                baseline_count = baseline.phase_request.counted_input_tokens
                compacted_count = compacted.phase_request.counted_input_tokens
                if baseline_count is None or compacted_count is None:
                    raise RecoveryError("compacted shadow count is absent")
                observations.append(
                    CompactedShadowQualificationObservation(
                        frame_id=sha256_json(identity),
                        **identity,
                        selected_memory_bytes=len(delivery.text.encode("utf-8")),
                        phase_evidence_hash=sha256_json(asdict(phase_evidence)),
                        phase_allowed_actions=phase_evidence.allowed_next_actions,
                        selected_tool_names=baseline.phase_request.tool_names,
                        removed_tool_names=baseline.phase_tool_surface.removed_tool_names,
                        source_context_hash=shadow.source_built_context_hash,
                        compacted_context_hash=shadow.compacted_context_hash,
                        removed_descriptor_count=(
                            shadow.context_compaction.removed_descriptor_count
                        ),
                        baseline_source_request_bytes=(baseline.source_request.request_body_bytes),
                        compacted_source_request_bytes=(
                            compacted.source_request.request_body_bytes
                        ),
                        source_request_bytes_saved=(shadow.source_request_body_bytes_saved),
                        baseline_phase_request_bytes=(baseline.phase_request.request_body_bytes),
                        compacted_phase_request_bytes=(compacted.phase_request.request_body_bytes),
                        phase_request_bytes_saved=(shadow.phase_request_body_bytes_saved),
                        baseline_counted_input_units=baseline_count,
                        compacted_counted_input_units=compacted_count,
                        counted_input_units_saved=(shadow.phase_counted_input_tokens_saved),
                        request_mode=baseline.request_mode.mode,
                        request_ready=baseline.request_ready,
                        compaction_evidence_hash=(shadow.context_compaction.content_hash),
                        shadow_evidence_hash=shadow.content_hash,
                        exact_source_roundtrip=shadow.exact_source_roundtrip,
                        phase_tool_surface_unchanged=(shadow.phase_tool_surface_unchanged),
                    )
                )
    if client.responses.create_calls != 0:
        raise RecoveryError("compacted shadow qualification generated")
    source_files = tuple(_file_binding(root, path) for path in SOURCE_PATHS)
    validation_files = tuple(_file_binding(root, path) for path in VALIDATION_PATHS)
    baseline_phase_bytes = sum(item.baseline_phase_request_bytes for item in observations)
    compacted_phase_bytes = sum(item.compacted_phase_request_bytes for item in observations)
    baseline_count = sum(item.baseline_counted_input_units for item in observations)
    compacted_count = sum(item.compacted_counted_input_units for item in observations)
    body: dict[str, Any] = {
        "schema_version": QUALIFICATION_SCHEMA,
        "qualification_id": QUALIFICATION_ID,
        "status": "PUBLIC_NO_CALL_SHADOW_PHASE_POLICY_QUALIFIED_RUNTIME_CLOSED",
        "evidence_date": "2026-08-16",
        "frame_source": "deterministic-synthetic-public-events",
        "phase_evidence_source": ("rendered-phase-contract-derived-synthetic-evidence-state"),
        "live_public_trace_files_read": 0,
        "live_public_trace_replay_verified": False,
        "non_public_task_repository_files_read": 0,
        "predecessor_event_compaction": predecessor_binding.model_dump(mode="python"),
        "predecessor_event_compaction_content_hash": PREDECESSOR_CONTENT_HASH,
        "task_bindings": tuple(item.model_dump(mode="python") for item in task_bindings),
        "frame_phases": FRAME_PHASES,
        "conditions": CONDITIONS,
        "expected_observations": 24,
        "context_policy_version": CONTEXT_POLICY_VERSION,
        "model_id": "gpt-5.4-mini-2026-03-17",
        "fixed_bundle_sha256": FIXED_BUNDLE_SHA256,
        "fixed_bundle_bytes": FIXED_BUNDLE_BYTES,
        "runtime_input_limit": 1_000_000,
        "runtime_output_limit": 100_000,
        "runtime_total_limit": 1_100_000,
        "configured_max_output_tokens": 25_000,
        "counter_contract": "caller-attested-canonical-utf8-byte-proxy-v1",
        "provider_token_count_verified": False,
        "observations": tuple(item.model_dump(mode="python") for item in observations),
        "aggregate_baseline_phase_request_bytes": baseline_phase_bytes,
        "aggregate_compacted_phase_request_bytes": compacted_phase_bytes,
        "aggregate_phase_request_bytes_saved": (baseline_phase_bytes - compacted_phase_bytes),
        "aggregate_baseline_counted_input_units": baseline_count,
        "aggregate_compacted_counted_input_units": compacted_count,
        "aggregate_counted_input_units_saved": baseline_count - compacted_count,
        "aggregate_removed_descriptor_count": sum(
            item.removed_descriptor_count for item in observations
        ),
        "frames_with_compaction": sum(item.removed_descriptor_count > 0 for item in observations),
        "noop_frames": sum(item.removed_descriptor_count == 0 for item in observations),
        "observed_phase_proxy_reduction_basis_points_floor": (
            (baseline_count - compacted_count) * 10_000 // baseline_count
        ),
        "public_integration_threshold_basis_points": (INTEGRATION_THRESHOLD_BASIS_POINTS),
        "all_phase_tool_surfaces_exact": True,
        "all_request_modes_unchanged": True,
        "all_request_readiness_unchanged": True,
        "exact_roundtrip_all": True,
        "condition_neutral_projection": _condition_neutral(observations),
        "current_phase_policy_requalified": True,
        "source_files": tuple(item.model_dump(mode="python") for item in source_files),
        "validation_files": tuple(item.model_dump(mode="python") for item in validation_files),
        "source_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in source_files]
        ),
        "validation_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in validation_files]
        ),
        "public_task_files_read": 2,
        "private_task_files_read": 0,
        "hidden_files_read": 0,
        "reference_patches_read": 0,
        "in_memory_fixture_artifacts": len(fixture_paths),
        "adapter_payload_builds": len(observations) * 4,
        "isolated_count_calls": client.responses.input_tokens.calls,
        "provider_transport_calls": 0,
        "provider_generation_calls": client.responses.create_calls,
        "runner_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "added_model_cost_usd": 0,
        "provider_calls_authorized": False,
        "runner_activation_authorized": False,
        "request_integration_authorized": False,
        "request_persistence_authorized": False,
        "state_mutation_authorized": False,
        "paid_execution_authorized": False,
        "next_gate": (
            "freeze-condition-neutral-saturation-and-recovery-thresholds-from-"
            "separate-public-development-evidence"
        ),
    }
    return CompactedShadowPublicQualification.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )


def qualification_bytes(
    qualification: CompactedShadowPublicQualification,
) -> bytes:
    return (
        json.dumps(
            qualification.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def materialize_compacted_shadow_public_qualification(
    repository: str | Path = ".",
    output_path: str | Path = QUALIFICATION_PATH,
) -> CompactedShadowPublicQualification:
    root = _repository_root(repository)
    qualification = build_compacted_shadow_public_qualification(root)
    content = qualification_bytes(qualification)
    output = root / output_path
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if output.read_bytes() != content:
            raise RecoveryError("existing compacted shadow qualification differs")
        return qualification
    with output.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    return qualification


def load_compacted_shadow_public_qualification(
    repository: str | Path = ".",
    path: str | Path = QUALIFICATION_PATH,
) -> CompactedShadowPublicQualification:
    root = _repository_root(repository)
    raw = (root / path).read_bytes()
    try:
        qualification = CompactedShadowPublicQualification.model_validate_json(raw)
    except ValueError as exc:
        raise RecoveryError("compacted shadow qualification is invalid JSON") from exc
    if qualification_bytes(qualification) != raw:
        raise RecoveryError("compacted shadow qualification bytes are not canonical")
    expected = build_compacted_shadow_public_qualification(root)
    if qualification != expected:
        raise RecoveryError("compacted shadow qualification differs from source")
    return qualification
