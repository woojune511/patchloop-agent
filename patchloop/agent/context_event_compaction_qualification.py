"""Public-only byte-proxy qualification for event-descriptor compaction."""

from __future__ import annotations

import json
import os
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
    _request_projection,
    _task_binding,
)
from patchloop.agent.context_event_compaction import (
    project_lean_context_event_descriptors,
    restore_lean_context_event_descriptors,
)
from patchloop.agent.model import SYSTEM_PROMPT_V3
from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.contracts import Budget, MemoryCondition
from patchloop.errors import RecoveryError
from patchloop.memory.fixed_bundle import (
    FIXED_BUNDLE_BYTES,
    FIXED_BUNDLE_SHA256,
    build_fixed_memory_delivery,
)
from patchloop.task_loader import load_public_task
from patchloop.util import sha256_json, sha256_text

QUALIFICATION_SCHEMA = "lean-harness-event-descriptor-compaction-public-qualification-v1"
QUALIFICATION_ID = "lean-harness-event-descriptor-compaction-public-20260816-v1"
QUALIFICATION_PATH = (
    "experiments/lean-harness-event-descriptor-compaction-public-qualification-20260816-v1.json"
)
INTEGRATION_THRESHOLD_BASIS_POINTS = 100

SOURCE_PATHS = (
    "patchloop/agent/context.py",
    "patchloop/agent/context_dedup_qualification.py",
    "patchloop/agent/context_event_compaction.py",
    "patchloop/agent/context_event_compaction_qualification.py",
    "patchloop/agent/model.py",
    "patchloop/agent/tools.py",
    "patchloop/memory/fixed_bundle.py",
    "patchloop/task_loader.py",
    "patchloop/contracts.py",
    "patchloop/errors.py",
    "patchloop/util.py",
    "scripts/build_lean_harness_event_compaction_qualification.py",
)
VALIDATION_PATHS = (
    "tests/test_context_event_compaction.py",
    "tests/test_context_event_compaction_qualification.py",
)


class EventCompactionQualificationObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    frame_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_id: str = Field(min_length=1)
    task_path: str = Field(pattern=r"^tasks/dev-validation/[^/]+/public\.yaml$")
    condition: Literal["no_memory", "structured"]
    phase: Literal["INTAKE", "REPRODUCE", "PLAN", "IMPLEMENT", "VERIFY", "REVIEW"]
    frame_order: int = Field(ge=1, le=6)
    selected_memory_present: bool
    selected_memory_bytes: int = Field(ge=0)
    source_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_context_bytes: int = Field(gt=0)
    projected_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_context_bytes: int = Field(gt=0)
    context_bytes_saved: int = Field(ge=0)
    source_proxy_input_units: int = Field(gt=0)
    projected_proxy_input_units: int = Field(gt=0)
    proxy_input_units_saved: int = Field(ge=0)
    removed_descriptor_count: int = Field(ge=0)
    removed_descriptor_canonical_bytes: int = Field(ge=0)
    compaction_evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_request_surface_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_request_surface_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    exact_source_roundtrip: Literal[True]
    direct_components_preserved: Literal[True]
    tool_result_bodies_preserved: Literal[True]
    artifact_id_and_path_preserved: Literal[True]

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        memory_present = self.condition == "structured"
        expected_memory = FIXED_BUNDLE_BYTES if memory_present else 0
        if (
            self.selected_memory_present is not memory_present
            or self.selected_memory_bytes != expected_memory
        ):
            raise ValueError("event compaction memory condition differs")
        if self.context_bytes_saved != (self.source_context_bytes - self.projected_context_bytes):
            raise ValueError("event compaction context savings differ")
        if self.proxy_input_units_saved != (
            self.source_proxy_input_units - self.projected_proxy_input_units
        ):
            raise ValueError("event compaction proxy savings differ")
        if self.source_request_surface_hash != self.projected_request_surface_hash:
            raise ValueError("event compaction request surface differs")
        if self.removed_descriptor_count == 0:
            if (
                self.context_bytes_saved != 0
                or self.proxy_input_units_saved != 0
                or self.removed_descriptor_canonical_bytes != 0
                or self.source_context_hash != self.projected_context_hash
            ):
                raise ValueError("empty event compaction observation differs")
        elif (
            self.context_bytes_saved <= 0
            or self.proxy_input_units_saved <= 0
            or self.removed_descriptor_canonical_bytes <= 0
        ):
            raise ValueError("event compaction observation did not decrease")
        return self


class EventCompactionPublicQualification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-event-descriptor-compaction-public-qualification-v1"]
    qualification_id: Literal["lean-harness-event-descriptor-compaction-public-20260816-v1"]
    status: Literal["PUBLIC_BYTE_PROXY_EFFICIENCY_QUALIFIED_REQUEST_SHADOW_NEXT"]
    evidence_date: Literal["2026-08-16"]
    frame_source: Literal["deterministic-synthetic-public-events"]
    task_frame: Literal["r8-public-spec-deterministic-synthetic-events"]
    live_public_trace_files_read: Literal[0]
    live_public_trace_replay_verified: Literal[False]
    non_public_task_repository_files_read: Literal[0]
    task_bindings: tuple[PublicTaskBinding, ...]
    frame_phases: tuple[str, ...]
    conditions: tuple[str, ...]
    expected_observations: Literal[24]
    context_policy_version: Literal["phase-evidence-v5"]
    model_id: Literal["gpt-5.4-mini-2026-03-17"]
    system_prompt_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    fixed_bundle_sha256: Literal[
        "sha256:572667d431aa75e4fe74bfc030a99f64245b77d9afa1c88e5d531129f708accf"
    ]
    fixed_bundle_bytes: Literal[3528]
    counter_contract: Literal["caller-attested-canonical-utf8-byte-proxy-v1"]
    provider_token_count_verified: Literal[False]
    observations: tuple[EventCompactionQualificationObservation, ...]
    aggregate_source_context_bytes: int = Field(gt=0)
    aggregate_projected_context_bytes: int = Field(gt=0)
    aggregate_context_bytes_saved: int = Field(gt=0)
    aggregate_source_proxy_input_units: int = Field(gt=0)
    aggregate_projected_proxy_input_units: int = Field(gt=0)
    aggregate_proxy_input_units_saved: int = Field(gt=0)
    aggregate_removed_descriptor_count: int = Field(gt=0)
    frames_with_compaction: int = Field(gt=0)
    noop_frames: int = Field(ge=0)
    every_context_nonincreasing: Literal[True]
    every_proxy_count_nonincreasing: Literal[True]
    exact_roundtrip_all: Literal[True]
    direct_components_preserved_all: Literal[True]
    tool_result_bodies_preserved_all: Literal[True]
    artifact_id_and_path_preserved_all: Literal[True]
    condition_neutral_projection: Literal[True]
    public_integration_threshold_basis_points: Literal[100]
    observed_proxy_reduction_basis_points_floor: int = Field(ge=100)
    structural_acceptance_passed: Literal[True]
    efficiency_gate_passed: Literal[True]
    request_shadow_integration_recommended: Literal[True]
    source_files: tuple[QualificationFileBinding, ...]
    validation_files: tuple[QualificationFileBinding, ...]
    source_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    public_task_files_read: Literal[2]
    private_task_files_read: Literal[0]
    hidden_files_read: Literal[0]
    reference_patches_read: Literal[0]
    in_memory_fixture_artifacts: Literal[8]
    adapter_payload_builds: Literal[48]
    isolated_count_calls: Literal[48]
    provider_transport_calls: Literal[0]
    provider_generation_calls: Literal[0]
    runner_calls: Literal[0]
    docker_calls: Literal[0]
    evaluator_calls: Literal[0]
    added_model_cost_usd: Literal[0]
    provider_calls_authorized: Literal[False]
    runner_activation_authorized: Literal[False]
    request_shadow_integration_authorized: Literal[False]
    state_mutation_authorized: Literal[False]
    paid_execution_authorized: Literal[False]
    next_gate: Literal[
        "bind-event-descriptor-projection-into-versioned-no-call-request-shadow-and-requalify-current-phase-policy"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_qualification(self) -> Self:
        if (
            self.frame_phases != FRAME_PHASES
            or self.conditions != CONDITIONS
            or tuple(item.path for item in self.task_bindings) != TASK_PATHS
            or len(self.task_bindings) != 2
            or len(self.observations) != self.expected_observations
        ):
            raise ValueError("event compaction qualification frame differs")
        identities = {(item.task_id, item.phase, item.condition) for item in self.observations}
        task_paths = {item.task_id: item.path for item in self.task_bindings}
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
            raise ValueError("event compaction observation identity differs")
        source_context = sum(item.source_context_bytes for item in self.observations)
        projected_context = sum(item.projected_context_bytes for item in self.observations)
        source_proxy = sum(item.source_proxy_input_units for item in self.observations)
        projected_proxy = sum(item.projected_proxy_input_units for item in self.observations)
        descriptor_count = sum(item.removed_descriptor_count for item in self.observations)
        if (
            self.aggregate_source_context_bytes != source_context
            or self.aggregate_projected_context_bytes != projected_context
            or self.aggregate_context_bytes_saved != source_context - projected_context
            or self.aggregate_source_proxy_input_units != source_proxy
            or self.aggregate_projected_proxy_input_units != projected_proxy
            or self.aggregate_proxy_input_units_saved != source_proxy - projected_proxy
            or self.aggregate_removed_descriptor_count != descriptor_count
            or self.frames_with_compaction
            != sum(item.removed_descriptor_count > 0 for item in self.observations)
            or self.noop_frames
            != sum(item.removed_descriptor_count == 0 for item in self.observations)
        ):
            raise ValueError("event compaction aggregate differs")
        observed_basis_points = (
            self.aggregate_proxy_input_units_saved * 10_000
        ) // self.aggregate_source_proxy_input_units
        if (
            self.observed_proxy_reduction_basis_points_floor != observed_basis_points
            or observed_basis_points < self.public_integration_threshold_basis_points
        ):
            raise ValueError("event compaction efficiency gate differs")
        if any(
            item.projected_context_bytes > item.source_context_bytes
            or item.projected_proxy_input_units > item.source_proxy_input_units
            for item in self.observations
        ):
            raise ValueError("event compaction contains an increasing frame")
        if (
            tuple(item.path for item in self.source_files) != SOURCE_PATHS
            or tuple(item.path for item in self.validation_files) != VALIDATION_PATHS
        ):
            raise ValueError("event compaction source inventory differs")
        if self.source_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.source_files]
        ) or self.validation_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.validation_files]
        ):
            raise ValueError("event compaction inventory hash differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("event compaction qualification hash differs")
        return self


def _condition_neutral(
    observations: list[EventCompactionQualificationObservation],
) -> bool:
    grouped: dict[tuple[str, str], dict[str, EventCompactionQualificationObservation]] = {}
    for item in observations:
        grouped.setdefault((item.task_id, item.phase), {})[item.condition] = item
    return all(
        set(pair) == set(CONDITIONS)
        and pair["no_memory"].context_bytes_saved == pair["structured"].context_bytes_saved
        and pair["no_memory"].proxy_input_units_saved == pair["structured"].proxy_input_units_saved
        and pair["no_memory"].removed_descriptor_count
        == pair["structured"].removed_descriptor_count
        for pair in grouped.values()
    )


def build_event_compaction_public_qualification(
    repository: str | Path = ".",
) -> EventCompactionPublicQualification:
    root = _repository_root(repository)
    adapter, client = _adapter()
    store = _FixtureStore()
    budget = Budget(
        max_model_calls=180,
        max_tool_calls=300,
        max_total_tokens=3_350_000,
        wall_clock_timeout_seconds=3_600,
        token_budget_schema_version="cumulative-split-v1",
        max_cumulative_input_tokens=3_000_000,
        max_cumulative_output_tokens=350_000,
    )
    deliveries = {
        condition: build_fixed_memory_delivery(
            condition=MemoryCondition(condition),
            repository=root,
        )
        for condition in CONDITIONS
    }
    observations: list[EventCompactionQualificationObservation] = []
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
            frame_events, checkpoint = _phase_frame(
                task,
                events,
                diff_hash,
                phase,
            )
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
                projected = project_lean_context_event_descriptors(built)
                source_request = _request_projection(adapter, built.rendered)
                compacted_request = _request_projection(
                    adapter,
                    projected.rendered,
                )
                identity = {
                    "task_id": task.task_id,
                    "task_path": task_path,
                    "condition": condition,
                    "phase": phase,
                    "frame_order": frame_order,
                }
                observations.append(
                    EventCompactionQualificationObservation(
                        frame_id=sha256_json(identity),
                        **identity,
                        selected_memory_present=condition == "structured",
                        selected_memory_bytes=len(delivery.text.encode("utf-8")),
                        source_context_hash=built.content_hash,
                        source_context_bytes=len(built.rendered.encode("utf-8")),
                        projected_context_hash=projected.content_hash,
                        projected_context_bytes=len(projected.rendered.encode("utf-8")),
                        context_bytes_saved=(projected.evidence.context_bytes_saved),
                        source_proxy_input_units=source_request[4],
                        projected_proxy_input_units=compacted_request[4],
                        proxy_input_units_saved=(source_request[4] - compacted_request[4]),
                        removed_descriptor_count=(projected.evidence.removed_descriptor_count),
                        removed_descriptor_canonical_bytes=(
                            projected.evidence.removed_descriptor_canonical_bytes
                        ),
                        compaction_evidence_hash=projected.evidence.content_hash,
                        source_request_surface_hash=source_request[5],
                        projected_request_surface_hash=compacted_request[5],
                        exact_source_roundtrip=(
                            restore_lean_context_event_descriptors(projected) == built.rendered
                        ),
                        direct_components_preserved=(
                            projected.evidence.direct_components_preserved
                        ),
                        tool_result_bodies_preserved=(
                            projected.evidence.tool_result_bodies_preserved
                        ),
                        artifact_id_and_path_preserved=(
                            projected.evidence.artifact_id_and_path_preserved
                        ),
                    )
                )
    if client.responses.create_calls != 0:
        raise RecoveryError("event compaction qualification generated")
    source_files = tuple(_file_binding(root, path) for path in SOURCE_PATHS)
    validation_files = tuple(_file_binding(root, path) for path in VALIDATION_PATHS)
    source_context = sum(item.source_context_bytes for item in observations)
    projected_context = sum(item.projected_context_bytes for item in observations)
    source_proxy = sum(item.source_proxy_input_units for item in observations)
    projected_proxy = sum(item.projected_proxy_input_units for item in observations)
    observed_basis_points = ((source_proxy - projected_proxy) * 10_000) // source_proxy
    body: dict[str, Any] = {
        "schema_version": QUALIFICATION_SCHEMA,
        "qualification_id": QUALIFICATION_ID,
        "status": "PUBLIC_BYTE_PROXY_EFFICIENCY_QUALIFIED_REQUEST_SHADOW_NEXT",
        "evidence_date": "2026-08-16",
        "frame_source": "deterministic-synthetic-public-events",
        "task_frame": "r8-public-spec-deterministic-synthetic-events",
        "live_public_trace_files_read": 0,
        "live_public_trace_replay_verified": False,
        "non_public_task_repository_files_read": 0,
        "task_bindings": tuple(item.model_dump(mode="python") for item in task_bindings),
        "frame_phases": FRAME_PHASES,
        "conditions": CONDITIONS,
        "expected_observations": 24,
        "context_policy_version": CONTEXT_POLICY_VERSION,
        "model_id": "gpt-5.4-mini-2026-03-17",
        "system_prompt_hash": sha256_text(SYSTEM_PROMPT_V3),
        "tool_schema_hash": sha256_json(TOOL_SCHEMAS_V2),
        "fixed_bundle_sha256": FIXED_BUNDLE_SHA256,
        "fixed_bundle_bytes": FIXED_BUNDLE_BYTES,
        "counter_contract": "caller-attested-canonical-utf8-byte-proxy-v1",
        "provider_token_count_verified": False,
        "observations": tuple(item.model_dump(mode="python") for item in observations),
        "aggregate_source_context_bytes": source_context,
        "aggregate_projected_context_bytes": projected_context,
        "aggregate_context_bytes_saved": source_context - projected_context,
        "aggregate_source_proxy_input_units": source_proxy,
        "aggregate_projected_proxy_input_units": projected_proxy,
        "aggregate_proxy_input_units_saved": source_proxy - projected_proxy,
        "aggregate_removed_descriptor_count": sum(
            item.removed_descriptor_count for item in observations
        ),
        "frames_with_compaction": sum(item.removed_descriptor_count > 0 for item in observations),
        "noop_frames": sum(item.removed_descriptor_count == 0 for item in observations),
        "every_context_nonincreasing": True,
        "every_proxy_count_nonincreasing": True,
        "exact_roundtrip_all": True,
        "direct_components_preserved_all": True,
        "tool_result_bodies_preserved_all": True,
        "artifact_id_and_path_preserved_all": True,
        "condition_neutral_projection": _condition_neutral(observations),
        "public_integration_threshold_basis_points": (INTEGRATION_THRESHOLD_BASIS_POINTS),
        "observed_proxy_reduction_basis_points_floor": observed_basis_points,
        "structural_acceptance_passed": True,
        "efficiency_gate_passed": True,
        "request_shadow_integration_recommended": True,
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
        "adapter_payload_builds": len(observations) * 2,
        "isolated_count_calls": client.responses.input_tokens.calls,
        "provider_transport_calls": 0,
        "provider_generation_calls": client.responses.create_calls,
        "runner_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "added_model_cost_usd": 0,
        "provider_calls_authorized": False,
        "runner_activation_authorized": False,
        "request_shadow_integration_authorized": False,
        "state_mutation_authorized": False,
        "paid_execution_authorized": False,
        "next_gate": (
            "bind-event-descriptor-projection-into-versioned-no-call-request-"
            "shadow-and-requalify-current-phase-policy"
        ),
    }
    return EventCompactionPublicQualification.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )


def qualification_bytes(
    qualification: EventCompactionPublicQualification,
) -> bytes:
    return (
        json.dumps(
            qualification.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def materialize_event_compaction_public_qualification(
    repository: str | Path = ".",
    output_path: str | Path = QUALIFICATION_PATH,
) -> EventCompactionPublicQualification:
    root = _repository_root(repository)
    qualification = build_event_compaction_public_qualification(root)
    content = qualification_bytes(qualification)
    output = root / output_path
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if output.read_bytes() != content:
            raise RecoveryError("existing event compaction qualification differs")
        return qualification
    with output.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    return qualification


def load_event_compaction_public_qualification(
    repository: str | Path = ".",
    path: str | Path = QUALIFICATION_PATH,
) -> EventCompactionPublicQualification:
    root = _repository_root(repository)
    raw = (root / path).read_bytes()
    try:
        qualification = EventCompactionPublicQualification.model_validate_json(raw)
    except ValueError as exc:
        raise RecoveryError("event compaction qualification is invalid JSON") from exc
    if qualification_bytes(qualification) != raw:
        raise RecoveryError("event compaction qualification bytes are not canonical")
    expected = build_event_compaction_public_qualification(root)
    if qualification != expected:
        raise RecoveryError("event compaction qualification differs from source")
    return qualification
