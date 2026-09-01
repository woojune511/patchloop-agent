"""Public-only, no-call qualification for Lean Harness context references.

This module freezes six deterministic model-context frames for the two R8
development-validation tasks, under both A-null and exact C-bundle delivery.
It builds the real phase-evidence-v5 context and Responses request payload,
then compares the source and reversible-reference forms through the adapter's
input-count method using an isolated canonical-UTF-8 byte proxy.

The proxy is deliberately not called a provider token count.  No generation,
network, Docker, evaluator, runner state, private task data, or paid authority
is reachable from this qualification.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.context import BuiltContext, build_context_with_evidence
from patchloop.agent.context_dedup import (
    DeduplicatedContext,
    project_lean_context_dedup,
    restore_lean_context_references,
)
from patchloop.agent.model import (
    SYSTEM_PROMPT_V3,
    OpenAIResponsesAdapter,
)
from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.contracts import (
    Artifact,
    Budget,
    Checkpoint,
    EventType,
    MemoryCondition,
    ModelConfig,
    Phase,
    PublicTask,
    RunEvent,
)
from patchloop.errors import ContractError, RecoveryError
from patchloop.memory.fixed_bundle import (
    FIXED_BUNDLE_BYTES,
    FIXED_BUNDLE_SHA256,
    build_fixed_memory_delivery,
)
from patchloop.task_loader import load_public_task
from patchloop.util import (
    canonical_json,
    sha256_bytes,
    sha256_json,
    sha256_text,
)

QUALIFICATION_SCHEMA = "lean-harness-context-dedup-public-qualification-v2"
QUALIFICATION_ID = "lean-harness-context-dedup-public-20260816-v2"
QUALIFICATION_PATH = "experiments/lean-harness-context-dedup-public-qualification-20260816-v2.json"
PREDECESSOR_PATH = "experiments/lean-harness-context-dedup-public-qualification-20260816-v1.json"
PREDECESSOR_BYTES = 54_968
PREDECESSOR_FILE_SHA256 = "sha256:95b89ed118c0cecbe6c95c49d432908f4be002e36a1712560380f6491118521a"
PREDECESSOR_CONTENT_HASH = "sha256:bc7877e535574b816402b1ea3b7734eb37b7d7ada42ed5e1100ebd66f707137b"
CONTEXT_POLICY_VERSION = "phase-evidence-v5"
COUNTER_CONTRACT = "caller-attested-canonical-utf8-byte-proxy-v1"
FIXTURE_ROOT = "qualification-fixtures/lean-harness-context-dedup-public-v1"
FIXED_TIME = datetime(2026, 8, 16, 0, 0, tzinfo=UTC)

TASK_PATHS = (
    "tasks/dev-validation/moto-query-scanned-count/public.yaml",
    "tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes/public.yaml",
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
SOURCE_PATHS = (
    "patchloop/agent/context.py",
    "patchloop/agent/context_dedup.py",
    "patchloop/agent/context_dedup_qualification.py",
    "patchloop/agent/model.py",
    "patchloop/agent/tools.py",
    "patchloop/memory/fixed_bundle.py",
    "patchloop/task_loader.py",
    "patchloop/contracts.py",
    "patchloop/util.py",
    "scripts/build_lean_harness_context_dedup_qualification.py",
)
VALIDATION_PATHS = (
    "tests/test_context_dedup.py",
    "tests/test_context_dedup_qualification.py",
)


class QualificationFileBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    file_bytes: int = Field(gt=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class PublicTaskBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    task_id: str = Field(min_length=1)
    task_version: int = Field(ge=1)
    split: Literal["dev-validation"]
    path: str = Field(pattern=r"^tasks/dev-validation/[^/]+/public\.yaml$")
    file_bytes: int = Field(gt=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    base_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    private_file_opened: Literal[False]
    hidden_file_opened: Literal[False]
    reference_patch_opened: Literal[False]


class ContextDedupQualificationObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    frame_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_id: str = Field(min_length=1)
    task_path: str = Field(pattern=r"^tasks/dev-validation/[^/]+/public\.yaml$")
    condition: Literal["no_memory", "structured"]
    phase: Literal["INTAKE", "REPRODUCE", "PLAN", "IMPLEMENT", "VERIFY", "REVIEW"]
    frame_order: int = Field(ge=1, le=6)
    context_policy_version: Literal["phase-evidence-v5"]
    selected_memory_present: bool
    selected_memory_bytes: int = Field(ge=0)
    source_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_context_bytes: int = Field(gt=0)
    projected_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_context_bytes: int = Field(gt=0)
    context_bytes_saved: int = Field(ge=0)
    reference_count: int = Field(ge=0)
    replacement_count: int = Field(ge=0)
    dedup_evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_request_bytes: int = Field(gt=0)
    source_count_payload_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_count_payload_bytes: int = Field(gt=0)
    source_proxy_input_units: int = Field(gt=0)
    projected_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_request_bytes: int = Field(gt=0)
    projected_count_payload_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_count_payload_bytes: int = Field(gt=0)
    projected_proxy_input_units: int = Field(gt=0)
    proxy_input_units_saved: int = Field(ge=0)
    source_request_surface_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_request_surface_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    exact_source_roundtrip: Literal[True]
    direct_components_preserved: Literal[True]
    request_surface_held_constant: Literal[True]

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        if self.selected_memory_present is (self.condition == "no_memory"):
            raise ValueError("qualification memory presence differs from condition")
        expected_memory_bytes = FIXED_BUNDLE_BYTES if self.condition == "structured" else 0
        if self.selected_memory_bytes != expected_memory_bytes:
            raise ValueError("qualification selected-memory bytes differ")
        if self.context_bytes_saved != (self.source_context_bytes - self.projected_context_bytes):
            raise ValueError("qualification context byte savings differ")
        if self.proxy_input_units_saved != (
            self.source_proxy_input_units - self.projected_proxy_input_units
        ):
            raise ValueError("qualification proxy savings differ")
        if self.source_proxy_input_units != self.source_count_payload_bytes:
            raise ValueError("source proxy differs from exact count payload bytes")
        if self.projected_proxy_input_units != self.projected_count_payload_bytes:
            raise ValueError("projected proxy differs from count payload bytes")
        if self.source_request_surface_hash != self.projected_request_surface_hash:
            raise ValueError("qualification request surface differs")
        if self.reference_count == 0:
            if (
                self.replacement_count != 0
                or self.context_bytes_saved != 0
                or self.source_context_hash != self.projected_context_hash
            ):
                raise ValueError("no-op qualification observation differs")
        elif self.replacement_count < self.reference_count:
            raise ValueError("qualification reference replacements are incomplete")
        return self


class ContextDedupPublicQualification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-context-dedup-public-qualification-v2"]
    qualification_id: Literal["lean-harness-context-dedup-public-20260816-v2"]
    status: Literal["PUBLIC_BYTE_PROXY_SAFE_EFFECT_NEGLIGIBLE_PROVIDER_TOKEN_OPEN"]
    evidence_date: Literal["2026-08-16"]
    predecessor_v1: QualificationFileBinding
    predecessor_v1_content_hash: Literal[
        "sha256:bc7877e535574b816402b1ea3b7734eb37b7d7ada42ed5e1100ebd66f707137b"
    ]
    predecessor_disposition: Literal["superseded-by-explicit-synthetic-frame-provenance"]
    task_frame: Literal["r8-public-spec-deterministic-synthetic-events"]
    frame_source: Literal["deterministic-synthetic-public-events"]
    live_public_trace_files_read: Literal[0]
    live_public_trace_replay_verified: Literal[False]
    task_repository_files_read: Literal[0]
    task_bindings: tuple[PublicTaskBinding, ...]
    frame_phases: tuple[str, ...]
    conditions: tuple[str, ...]
    expected_observations: Literal[24]
    context_policy_version: Literal["phase-evidence-v5"]
    model_id: Literal["gpt-5.4-mini-2026-03-17"]
    reasoning_effort: Literal["medium"]
    service_tier: Literal["default"]
    transport_max_retries: Literal[0]
    max_output_tokens: Literal[25000]
    system_prompt_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    fixed_bundle_sha256: Literal[
        "sha256:572667d431aa75e4fe74bfc030a99f64245b77d9afa1c88e5d531129f708accf"
    ]
    fixed_bundle_bytes: Literal[3528]
    counter_contract: Literal["caller-attested-canonical-utf8-byte-proxy-v1"]
    counter_unit: Literal["canonical-count-payload-utf8-byte"]
    provider_token_count_verified: Literal[False]
    observations: tuple[ContextDedupQualificationObservation, ...]
    aggregate_source_context_bytes: int = Field(gt=0)
    aggregate_projected_context_bytes: int = Field(gt=0)
    aggregate_context_bytes_saved: int = Field(gt=0)
    aggregate_source_proxy_input_units: int = Field(gt=0)
    aggregate_projected_proxy_input_units: int = Field(gt=0)
    aggregate_proxy_input_units_saved: int = Field(gt=0)
    observations_with_references: int = Field(ge=1)
    noop_observations: int = Field(ge=0)
    every_context_nonincreasing: Literal[True]
    every_proxy_count_nonincreasing: Literal[True]
    aggregate_context_reduced: Literal[True]
    aggregate_proxy_count_reduced: Literal[True]
    exact_roundtrip_all: Literal[True]
    direct_components_preserved_all: Literal[True]
    condition_neutral_non_memory_projection: Literal[True]
    structural_acceptance_passed: Literal[True]
    public_integration_threshold_basis_points: Literal[100]
    observed_proxy_reduction_basis_points_floor: int = Field(ge=0)
    efficiency_gate_passed: Literal[False]
    runtime_integration_recommended: Literal[False]
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
        "retain-reference-projection-offline-and-qualify-higher-yield-phase-or-producer-compaction-on-public-development"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_qualification(self) -> Self:
        if self.predecessor_v1 != QualificationFileBinding(
            path=PREDECESSOR_PATH,
            file_bytes=PREDECESSOR_BYTES,
            file_sha256=PREDECESSOR_FILE_SHA256,
        ):
            raise ValueError("qualification predecessor identity differs")
        if self.frame_phases != FRAME_PHASES or self.conditions != CONDITIONS:
            raise ValueError("qualification frame ordering differs")
        if (
            len(self.task_bindings) != 2
            or tuple(item.path for item in self.task_bindings) != TASK_PATHS
        ):
            raise ValueError("qualification public task frame differs")
        if len(self.observations) != self.expected_observations:
            raise ValueError("qualification observation count differs")
        identities = {(item.task_id, item.condition, item.phase) for item in self.observations}
        if len(identities) != self.expected_observations:
            raise ValueError("qualification observation identities repeat")
        if any(
            item.frame_order != FRAME_PHASES.index(item.phase) + 1 for item in self.observations
        ):
            raise ValueError("qualification frame order differs")
        sums = {
            "source_context": sum(item.source_context_bytes for item in self.observations),
            "projected_context": sum(item.projected_context_bytes for item in self.observations),
            "source_proxy": sum(item.source_proxy_input_units for item in self.observations),
            "projected_proxy": sum(item.projected_proxy_input_units for item in self.observations),
        }
        if (
            self.aggregate_source_context_bytes != sums["source_context"]
            or self.aggregate_projected_context_bytes != sums["projected_context"]
            or self.aggregate_context_bytes_saved
            != sums["source_context"] - sums["projected_context"]
            or self.aggregate_source_proxy_input_units != sums["source_proxy"]
            or self.aggregate_projected_proxy_input_units != sums["projected_proxy"]
            or self.aggregate_proxy_input_units_saved
            != sums["source_proxy"] - sums["projected_proxy"]
        ):
            raise ValueError("qualification aggregate arithmetic differs")
        with_refs = sum(item.reference_count > 0 for item in self.observations)
        if (
            self.observations_with_references != with_refs
            or self.noop_observations != len(self.observations) - with_refs
        ):
            raise ValueError("qualification reference counts differ")
        if any(
            item.projected_context_bytes > item.source_context_bytes
            or item.projected_proxy_input_units > item.source_proxy_input_units
            for item in self.observations
        ):
            raise ValueError("qualification contains an increasing projection")
        if not (
            self.aggregate_projected_context_bytes < self.aggregate_source_context_bytes
            and self.aggregate_projected_proxy_input_units < self.aggregate_source_proxy_input_units
        ):
            raise ValueError("qualification aggregate did not decrease")
        observed_basis_points = (
            self.aggregate_proxy_input_units_saved * 10_000
        ) // self.aggregate_source_proxy_input_units
        if (
            self.observed_proxy_reduction_basis_points_floor != observed_basis_points
            or observed_basis_points >= self.public_integration_threshold_basis_points
        ):
            raise ValueError("qualification efficiency disposition differs")
        if tuple(item.path for item in self.source_files) != SOURCE_PATHS:
            raise ValueError("qualification source inventory differs")
        if tuple(item.path for item in self.validation_files) != VALIDATION_PATHS:
            raise ValueError("qualification validation inventory differs")
        if self.source_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.source_files]
        ):
            raise ValueError("qualification source inventory hash differs")
        if self.validation_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.validation_files]
        ):
            raise ValueError("qualification validation inventory hash differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("qualification content hash differs")
        return self


@dataclass(frozen=True)
class _CountResult:
    input_tokens: int


class _ProxyInputCounter:
    def __init__(self) -> None:
        self.calls = 0

    def count(self, **payload: Any) -> _CountResult:
        self.calls += 1
        return _CountResult(input_tokens=len(canonical_json(payload).encode("utf-8")))


class _NoGenerationResponses:
    def __init__(self) -> None:
        self.input_tokens = _ProxyInputCounter()
        self.create_calls = 0

    def create(self, **request: Any) -> None:
        del request
        self.create_calls += 1
        raise AssertionError("public qualification must not generate")


class _IsolatedClient:
    max_retries = 0

    def __init__(self) -> None:
        self.responses = _NoGenerationResponses()


class _FixtureStore:
    def __init__(self) -> None:
        self.contents: dict[str, bytes] = {}

    def register(self, relative: str, content: bytes) -> None:
        previous = self.contents.setdefault(relative, content)
        if previous != content:
            raise RecoveryError("qualification fixture identity collides")

    def read_bytes(self, artifact: Artifact) -> bytes:
        content = self.contents.get(artifact.path)
        if content is None:
            raise RecoveryError("qualification fixture artifact is missing")
        if len(content) != artifact.size_bytes or sha256_bytes(content) != artifact.content_hash:
            raise RecoveryError("qualification fixture artifact differs")
        return content


def _repository_root(repository: str | Path) -> Path:
    root = Path(repository).resolve(strict=True)
    if not root.is_dir():
        raise ContractError("qualification repository root is not a directory")
    if Path.cwd().resolve() != root:
        raise ContractError("qualification must run from the repository root")
    return root


def _file_binding(root: Path, relative: str) -> QualificationFileBinding:
    path = root / relative
    content = path.read_bytes()
    return QualificationFileBinding(
        path=relative,
        file_bytes=len(content),
        file_sha256=sha256_bytes(content),
    )


def _fixture_artifact(
    store: _FixtureStore,
    *,
    identity: str,
    payload: dict[str, Any],
) -> Artifact:
    content = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    digest = sha256_bytes(content)
    hex_digest = digest.removeprefix("sha256:")
    relative = Path(FIXTURE_ROOT) / "objects" / "sha256" / hex_digest[:2] / hex_digest[2:]
    store.register(relative.as_posix(), content)
    artifact_id = "art_" + sha256_text(identity).removeprefix("sha256:")[:32]
    return Artifact(
        artifact_id=artifact_id,
        content_hash=digest,
        media_type="application/json; charset=utf-8",
        size_bytes=len(content),
        path=relative.as_posix(),
        created_at=FIXED_TIME,
    )


def _event(
    *,
    task_id: str,
    sequence: int,
    event_type: EventType,
    actor: str,
    payload: dict[str, Any],
    correlation_id: str | None = None,
) -> RunEvent:
    return RunEvent(
        event_id=f"event_{task_id}_{sequence}",
        run_id=f"qualification_{task_id}",
        sequence=sequence,
        type=event_type,
        timestamp=FIXED_TIME + timedelta(seconds=sequence),
        actor=actor,
        correlation_id=correlation_id,
        payload=payload,
    )


def _public_events(
    store: _FixtureStore,
    task: PublicTask,
) -> tuple[tuple[RunEvent, ...], str, int]:
    empty_diff = sha256_text("")
    diff_hash = sha256_text(f"lean-harness-public-development|{task.task_id}|diff-v1")
    allowed_path = task.constraints.allowed_paths[0]
    read_input = {"path": allowed_path, "start_line": 1, "end_line": 4}
    input_document = {"tool": "read_file", "input": read_input}
    input_artifact = _fixture_artifact(
        store,
        identity=f"{task.task_id}|read-input",
        payload=input_document,
    )
    public_content = (
        f"# public-development synthetic inspection for {task.task_id}\n"
        "def public_surface():\n"
        "    return 'unchanged'\n"
        "# end public inspection\n"
    )
    result_document = {
        "path": allowed_path,
        "start_line": 1,
        "end_line": 4,
        "content": public_content,
        "actual_start_line": 1,
        "actual_end_line": 4,
        "line_count": 4,
        "total_lines": 120,
        "eof_reached": False,
        "file_content_hash": sha256_text(public_content),
        "worktree_diff_hash": empty_diff,
    }
    read_artifact = _fixture_artifact(
        store,
        identity=f"{task.task_id}|read-result",
        payload=result_document,
    )
    input_hash = sha256_text(canonical_json(input_document))
    normalized_call_hash = sha256_text(
        canonical_json(
            {
                "tool": "read_file",
                "input": read_input,
                "worktree_diff_hash": empty_diff,
                "state_marker": None,
            }
        )
    )
    read_action = f"{task.task_id}-read"
    events = [
        _event(
            task_id=task.task_id,
            sequence=1,
            event_type=EventType.TOOL_CALLED,
            actor="agent",
            correlation_id=read_action,
            payload={
                "tool": "read_file",
                "input_hash": input_hash,
                "normalized_call_hash": normalized_call_hash,
                "worktree_diff_hash": empty_diff,
                "input_artifact": input_artifact.model_dump(mode="json"),
                "artifact_id": input_artifact.artifact_id,
                "artifact_path": input_artifact.path,
            },
        ),
        _event(
            task_id=task.task_id,
            sequence=2,
            event_type=EventType.TOOL_SUCCEEDED,
            actor="tool-gateway",
            correlation_id=read_action,
            payload={
                "tool": "read_file",
                "status": "succeeded",
                "worktree_diff_hash": empty_diff,
                "artifact_id": read_artifact.artifact_id,
                "artifact_path": read_artifact.path,
                "result_artifact": read_artifact.model_dump(mode="json"),
            },
        ),
        _event(
            task_id=task.task_id,
            sequence=3,
            event_type=EventType.PATCH_APPLIED,
            actor="tool-gateway",
            payload={
                "tool": "apply_patch",
                "worktree_diff_hash": diff_hash,
                "changed_paths": [allowed_path],
            },
        ),
    ]
    check_id = task.visible_checks[0].id
    check_document = {
        "tool": "run_check",
        "check_id": check_id,
        "passed": True,
        "timed_out": False,
        "truncated": False,
        "stdout": "public-development synthetic check passed",
        "stderr": "",
        "worktree_diff_hash": diff_hash,
    }
    check_artifact = _fixture_artifact(
        store,
        identity=f"{task.task_id}|check-result",
        payload=check_document,
    )
    events.append(
        _event(
            task_id=task.task_id,
            sequence=4,
            event_type=EventType.TOOL_SUCCEEDED,
            actor="tool-gateway",
            correlation_id=f"{task.task_id}-check",
            payload={
                "tool": "run_check",
                "status": "succeeded",
                "check_id": check_id,
                "passed": True,
                "timed_out": False,
                "worktree_diff_hash": diff_hash,
                "artifact_id": check_artifact.artifact_id,
                "artifact_path": check_artifact.path,
                "result_artifact": check_artifact.model_dump(mode="json"),
            },
        )
    )
    diff_document = {
        "tool": "get_diff",
        "patch": f"diff --git a/{allowed_path} b/{allowed_path}\n",
        "patch_hash": diff_hash,
        "worktree_diff_hash": diff_hash,
    }
    diff_artifact = _fixture_artifact(
        store,
        identity=f"{task.task_id}|diff-result",
        payload=diff_document,
    )
    events.append(
        _event(
            task_id=task.task_id,
            sequence=5,
            event_type=EventType.TOOL_SUCCEEDED,
            actor="tool-gateway",
            correlation_id=f"{task.task_id}-diff",
            payload={
                "tool": "get_diff",
                "status": "succeeded",
                "worktree_diff_hash": diff_hash,
                "artifact_id": diff_artifact.artifact_id,
                "artifact_path": diff_artifact.path,
                "result_artifact": diff_artifact.model_dump(mode="json"),
            },
        )
    )
    return tuple(events), diff_hash, 4


def _checkpoint(
    task: PublicTask,
    *,
    phase: Phase,
    through_sequence: int,
    diff_hash: str,
) -> Checkpoint:
    return Checkpoint(
        checkpoint_id=f"checkpoint_{task.task_id}_{phase.value.lower()}",
        run_id=f"qualification_{task.task_id}",
        through_sequence=through_sequence,
        phase=phase,
        repository_head=task.repository.base_commit,
        worktree_diff_hash=diff_hash,
        created_at=FIXED_TIME + timedelta(minutes=through_sequence),
    )


def _phase_frame(
    task: PublicTask,
    events: tuple[RunEvent, ...],
    diff_hash: str,
    phase_name: str,
) -> tuple[list[RunEvent], Checkpoint | None]:
    empty_diff = sha256_text("")
    if phase_name == "INTAKE":
        return [], None
    if phase_name in {"REPRODUCE", "PLAN"}:
        prefix = list(events[:2])
        phase = Phase(phase_name)
        return prefix, _checkpoint(
            task,
            phase=phase,
            through_sequence=2,
            diff_hash=empty_diff,
        )
    lengths = {"IMPLEMENT": 3, "VERIFY": 4, "REVIEW": 5}
    through = lengths[phase_name]
    phase = Phase(phase_name)
    return list(events[:through]), _checkpoint(
        task,
        phase=phase,
        through_sequence=through,
        diff_hash=diff_hash,
    )


def _adapter() -> tuple[OpenAIResponsesAdapter, _IsolatedClient]:
    client = _IsolatedClient()
    adapter = OpenAIResponsesAdapter(
        ModelConfig(
            provider="openai",
            model_id="gpt-5.4-mini-2026-03-17",
            reasoning_effort="medium",
            service_tier="default",
            transport_max_retries=0,
            max_output_tokens=25_000,
        ),
        client=client,  # type: ignore[arg-type]
    )
    return adapter, client


def _request_projection(
    adapter: OpenAIResponsesAdapter,
    context: str,
) -> tuple[str, int, str, int, int, str]:
    request = adapter.request_payload(
        context,
        [dict(item) for item in TOOL_SCHEMAS_V2],
        system_prompt=SYSTEM_PROMPT_V3,
    )
    request_json = canonical_json(request)
    count_payload = adapter._token_count_payload(request)
    count_json = canonical_json(count_payload)
    counted = adapter.count_input_tokens(request)
    if counted != len(count_json.encode("utf-8")):
        raise RecoveryError("isolated proxy counter returned different units")
    surface = json.loads(request_json)
    surface["input"][1]["content"] = "<QUALIFICATION_CONTEXT>"
    return (
        sha256_text(request_json),
        len(request_json.encode("utf-8")),
        sha256_text(count_json),
        len(count_json.encode("utf-8")),
        counted,
        sha256_json(surface),
    )


def _observation(
    *,
    task_path: str,
    task: PublicTask,
    condition: str,
    phase_name: str,
    frame_order: int,
    built: BuiltContext,
    projected: DeduplicatedContext,
    adapter: OpenAIResponsesAdapter,
    memory_bytes: int,
) -> ContextDedupQualificationObservation:
    source_request = _request_projection(adapter, built.rendered)
    projected_request = _request_projection(adapter, projected.rendered)
    body = {
        "task_id": task.task_id,
        "task_path": task_path,
        "condition": condition,
        "phase": phase_name,
        "frame_order": frame_order,
        "context_policy_version": CONTEXT_POLICY_VERSION,
    }
    return ContextDedupQualificationObservation(
        frame_id=sha256_json(body),
        **body,
        selected_memory_present=condition == "structured",
        selected_memory_bytes=memory_bytes,
        source_context_hash=built.content_hash,
        source_context_bytes=len(built.rendered.encode("utf-8")),
        projected_context_hash=projected.content_hash,
        projected_context_bytes=len(projected.rendered.encode("utf-8")),
        context_bytes_saved=projected.evidence.bytes_saved,
        reference_count=len(projected.evidence.references),
        replacement_count=sum(item.replacement_count for item in projected.evidence.references),
        dedup_evidence_hash=projected.evidence.content_hash,
        source_request_hash=source_request[0],
        source_request_bytes=source_request[1],
        source_count_payload_hash=source_request[2],
        source_count_payload_bytes=source_request[3],
        source_proxy_input_units=source_request[4],
        projected_request_hash=projected_request[0],
        projected_request_bytes=projected_request[1],
        projected_count_payload_hash=projected_request[2],
        projected_count_payload_bytes=projected_request[3],
        projected_proxy_input_units=projected_request[4],
        proxy_input_units_saved=source_request[4] - projected_request[4],
        source_request_surface_hash=source_request[5],
        projected_request_surface_hash=projected_request[5],
        exact_source_roundtrip=(
            restore_lean_context_references(projected.rendered) == built.rendered
        ),
        direct_components_preserved=(projected.evidence.direct_components_preserved),
        request_surface_held_constant=True,
    )


def _task_binding(
    root: Path,
    relative: str,
    task: PublicTask,
) -> PublicTaskBinding:
    content = (root / relative).read_bytes()
    return PublicTaskBinding(
        task_id=task.task_id,
        task_version=task.task_version,
        split="dev-validation",
        path=relative,
        file_bytes=len(content),
        file_sha256=sha256_bytes(content),
        public_spec_hash=sha256_json(task.model_dump(mode="json")),
        base_commit=task.repository.base_commit,
        private_file_opened=False,
        hidden_file_opened=False,
        reference_patch_opened=False,
    )


def _condition_neutral(observations: list[dict[str, Any]]) -> bool:
    grouped: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for item in observations:
        key = (item["task_id"], item["phase"])
        grouped.setdefault(key, {})[item["condition"]] = item
    for pair in grouped.values():
        if set(pair) != set(CONDITIONS):
            return False
        left = pair["no_memory"]
        right = pair["structured"]
        if (
            left["context_bytes_saved"] != right["context_bytes_saved"]
            or left["reference_count"] != right["reference_count"]
            or left["replacement_count"] != right["replacement_count"]
            or left["proxy_input_units_saved"] != right["proxy_input_units_saved"]
        ):
            return False
    return True


def build_context_dedup_public_qualification(
    repository: str | Path = ".",
) -> ContextDedupPublicQualification:
    root = _repository_root(repository)
    predecessor = _file_binding(root, PREDECESSOR_PATH)
    try:
        predecessor_payload = json.loads((root / PREDECESSOR_PATH).read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError("context dedup predecessor is invalid JSON") from exc
    if (
        predecessor.file_bytes != PREDECESSOR_BYTES
        or predecessor.file_sha256 != PREDECESSOR_FILE_SHA256
        or predecessor_payload.get("content_hash") != PREDECESSOR_CONTENT_HASH
    ):
        raise RecoveryError("context dedup predecessor identity differs")
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
    observations: list[ContextDedupQualificationObservation] = []
    raw_observations: list[dict[str, Any]] = []
    task_bindings: list[PublicTaskBinding] = []
    fixture_files: set[str] = set()
    for task_path in TASK_PATHS:
        task = load_public_task(root / task_path)
        task_bindings.append(_task_binding(root, task_path, task))
        events, diff_hash, files_per_task = _public_events(store, task)
        del files_per_task
        fixture_files.update(
            artifact.path
            for event in events
            for descriptor in (
                event.payload.get("input_artifact"),
                event.payload.get("result_artifact"),
            )
            if isinstance(descriptor, dict)
            for artifact in (Artifact.model_validate(descriptor),)
        )
        for frame_order, phase_name in enumerate(FRAME_PHASES, start=1):
            frame_events, checkpoint = _phase_frame(
                task,
                events,
                diff_hash,
                phase_name,
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
                projected = project_lean_context_dedup(built)
                observation = _observation(
                    task_path=task_path,
                    task=task,
                    condition=condition,
                    phase_name=phase_name,
                    frame_order=frame_order,
                    built=built,
                    projected=projected,
                    adapter=adapter,
                    memory_bytes=len(delivery.text.encode("utf-8")),
                )
                observations.append(observation)
                raw_observations.append(observation.model_dump(mode="python"))
    if client.responses.create_calls != 0:
        raise RecoveryError("qualification unexpectedly generated a response")
    if client.responses.input_tokens.calls != len(observations) * 2:
        raise RecoveryError("qualification isolated count call total differs")

    source_files = tuple(_file_binding(root, path) for path in SOURCE_PATHS)
    validation_files = tuple(_file_binding(root, path) for path in VALIDATION_PATHS)
    aggregate_source_context = sum(item.source_context_bytes for item in observations)
    aggregate_projected_context = sum(item.projected_context_bytes for item in observations)
    aggregate_source_proxy = sum(item.source_proxy_input_units for item in observations)
    aggregate_projected_proxy = sum(item.projected_proxy_input_units for item in observations)
    body: dict[str, Any] = {
        "schema_version": QUALIFICATION_SCHEMA,
        "qualification_id": QUALIFICATION_ID,
        "status": "PUBLIC_BYTE_PROXY_SAFE_EFFECT_NEGLIGIBLE_PROVIDER_TOKEN_OPEN",
        "evidence_date": "2026-08-16",
        "predecessor_v1": predecessor.model_dump(mode="python"),
        "predecessor_v1_content_hash": PREDECESSOR_CONTENT_HASH,
        "predecessor_disposition": ("superseded-by-explicit-synthetic-frame-provenance"),
        "task_frame": "r8-public-spec-deterministic-synthetic-events",
        "frame_source": "deterministic-synthetic-public-events",
        "live_public_trace_files_read": 0,
        "live_public_trace_replay_verified": False,
        "task_repository_files_read": 0,
        "task_bindings": tuple(item.model_dump(mode="python") for item in task_bindings),
        "frame_phases": FRAME_PHASES,
        "conditions": CONDITIONS,
        "expected_observations": 24,
        "context_policy_version": CONTEXT_POLICY_VERSION,
        "model_id": "gpt-5.4-mini-2026-03-17",
        "reasoning_effort": "medium",
        "service_tier": "default",
        "transport_max_retries": 0,
        "max_output_tokens": 25_000,
        "system_prompt_hash": sha256_text(SYSTEM_PROMPT_V3),
        "tool_schema_hash": sha256_json(TOOL_SCHEMAS_V2),
        "fixed_bundle_sha256": FIXED_BUNDLE_SHA256,
        "fixed_bundle_bytes": FIXED_BUNDLE_BYTES,
        "counter_contract": COUNTER_CONTRACT,
        "counter_unit": "canonical-count-payload-utf8-byte",
        "provider_token_count_verified": False,
        "observations": tuple(raw_observations),
        "aggregate_source_context_bytes": aggregate_source_context,
        "aggregate_projected_context_bytes": aggregate_projected_context,
        "aggregate_context_bytes_saved": (aggregate_source_context - aggregate_projected_context),
        "aggregate_source_proxy_input_units": aggregate_source_proxy,
        "aggregate_projected_proxy_input_units": aggregate_projected_proxy,
        "aggregate_proxy_input_units_saved": (aggregate_source_proxy - aggregate_projected_proxy),
        "observations_with_references": sum(item.reference_count > 0 for item in observations),
        "noop_observations": sum(item.reference_count == 0 for item in observations),
        "every_context_nonincreasing": True,
        "every_proxy_count_nonincreasing": True,
        "aggregate_context_reduced": True,
        "aggregate_proxy_count_reduced": True,
        "exact_roundtrip_all": all(item.exact_source_roundtrip for item in observations),
        "direct_components_preserved_all": all(
            item.direct_components_preserved for item in observations
        ),
        "condition_neutral_non_memory_projection": _condition_neutral(raw_observations),
        "structural_acceptance_passed": True,
        "public_integration_threshold_basis_points": 100,
        "observed_proxy_reduction_basis_points_floor": (
            (aggregate_source_proxy - aggregate_projected_proxy) * 10_000
        )
        // aggregate_source_proxy,
        "efficiency_gate_passed": False,
        "runtime_integration_recommended": False,
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
        "in_memory_fixture_artifacts": len(fixture_files),
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
            "retain-reference-projection-offline-and-qualify-higher-yield-"
            "phase-or-producer-compaction-on-public-development"
        ),
    }
    return ContextDedupPublicQualification.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )


def qualification_bytes(
    qualification: ContextDedupPublicQualification,
) -> bytes:
    return (
        json.dumps(
            qualification.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def materialize_context_dedup_public_qualification(
    repository: str | Path = ".",
    output_path: str | Path = QUALIFICATION_PATH,
) -> ContextDedupPublicQualification:
    root = _repository_root(repository)
    qualification = build_context_dedup_public_qualification(root)
    content = qualification_bytes(qualification)
    output = root / output_path
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if output.read_bytes() != content:
            raise RecoveryError("existing context dedup qualification differs")
        return qualification
    with output.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    return qualification


def load_context_dedup_public_qualification(
    repository: str | Path = ".",
    path: str | Path = QUALIFICATION_PATH,
) -> ContextDedupPublicQualification:
    root = _repository_root(repository)
    raw = (root / path).read_bytes()
    try:
        qualification = ContextDedupPublicQualification.model_validate_json(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise RecoveryError("context dedup qualification is invalid JSON") from exc
    if qualification_bytes(qualification) != raw:
        raise RecoveryError("context dedup qualification bytes are not canonical")
    expected = build_context_dedup_public_qualification(root)
    if qualification != expected:
        raise RecoveryError("context dedup qualification differs from source")
    return qualification
