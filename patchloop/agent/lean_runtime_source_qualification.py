"""Closed public-mock source qualification for Lean Harness V1 integration.

The qualification executes only the preregistered three public smoke fixtures
with PatchLoop's deterministic mock adapter and local sandbox. It binds every
persisted v7/v12 request, compares condition-neutral request semantics, and
records no effect estimate. Provider, network, and Docker access are guarded
to fail before any such call.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.lean_runtime import (
    LeanHarnessRequestEvidence,
    build_lean_harness_calibration_manifest,
    validate_persisted_lean_harness_request,
)
from patchloop.agent.lean_runtime_preregistration import (
    PREREGISTRATION_ID,
    PREREGISTRATION_PATH,
    LeanRuntimeIntegrationPreregistration,
    load_lean_runtime_integration_preregistration,
)
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.agent.runner import AgentRunner
from patchloop.contracts import EventType, MemoryCondition
from patchloop.errors import RecoveryError
from patchloop.sandbox import DockerSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import (
    canonical_json,
    ensure_within,
    sha256_bytes,
    sha256_json,
)

QUALIFICATION_SCHEMA = "lean-harness-runtime-source-qualification-v1"
QUALIFICATION_ID = "lean-harness-runtime-public-calibration-20260817-v1"
QUALIFICATION_PATH = "experiments/lean-harness-runtime-source-qualification-20260817-v1.json"
EVIDENCE_DATE = "2026-08-17"

CONSUMED_QUALIFICATION_FILE_BYTES = 72_420
CONSUMED_QUALIFICATION_FILE_SHA256 = (
    "sha256:7104310a700822bde8343b7ed37facdb3fa09709ced41540cb9ccb431642fdab"
)

PREREGISTRATION_FILE_BYTES = 16_030
PREREGISTRATION_FILE_SHA256 = (
    "sha256:e36659fd23b4d2eaac60265c0023110791341d08cad20728572d9ee8e73a2683"
)
PREREGISTRATION_CONTENT_HASH = (
    "sha256:9eb9b137fd021bafb4ef2ac8d43dd0b34fbd1c5f4c64317c63bc1f88e04e0d63"
)

SOURCE_PATHS = (
    "patchloop/agent/context.py",
    "patchloop/agent/context_event_compaction.py",
    "patchloop/agent/finalization.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/lean_runtime_preregistration.py",
    "patchloop/agent/lean_runtime_source_qualification.py",
    "patchloop/agent/model.py",
    "patchloop/agent/phases.py",
    "patchloop/agent/request_allowance.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/saturation_recovery_shadow.py",
    "patchloop/agent/structured_edit.py",
    "patchloop/agent/structured_edit_replay.py",
    "patchloop/agent/tools.py",
    "patchloop/contracts.py",
    "patchloop/memory/fixed_bundle.py",
    "scripts/build_lean_harness_runtime_source_qualification.py",
)
VALIDATION_PATHS = (
    "tests/test_context_event_compaction.py",
    "tests/test_finalization.py",
    "tests/test_lean_runtime.py",
    "tests/test_lean_runtime_source_qualification.py",
    "tests/test_request_allowance.py",
    "tests/test_saturation_recovery_shadow.py",
    "tests/test_structured_edit.py",
    "tests/test_structured_edit_replay.py",
)

_VOLATILE_SEMANTIC_KEYS = frozenset(
    {
        "artifact_id",
        "artifact_path",
        "checkpoint_id",
        "created_at",
        "duration_ms",
        "repository_head",
        "run_id",
    }
)
_ARTIFACT_DESCRIPTOR_KEYS = frozenset(
    {"artifact_id", "content_hash", "media_type", "size_bytes", "path", "created_at"}
)


class FileBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    file_bytes: int = Field(gt=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")


class RequestObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    request_index: int = Field(ge=1)
    request_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    phase: Literal["REPRODUCE", "PLAN", "IMPLEMENT", "VERIFY", "REVIEW", "SUBMIT"]
    selected_tool_names: tuple[str, ...]
    selected_tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    request_mode: Literal["exploration", "finalization"]
    effective_max_output_tokens: int = Field(ge=1)
    requested_input_tokens: int = Field(ge=1)
    non_memory_request_semantics_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    persisted_before_dispatch: Literal[True]
    provider_authority_granted: Literal[False]


class CalibrationRowObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    order: int = Field(ge=1, le=12)
    preregistered_row_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    run_id: str = Field(pattern=r"^run_lean_calibration_[0-9]{2}_[0-9a-f]{12}$")
    task_id: str = Field(min_length=1)
    task_version: Literal[1]
    task_path: str = Field(min_length=1)
    condition: Literal["no_memory", "structured"]
    repetition: Literal[1, 2]
    resolved: Literal[True]
    scope_compliant_success: Literal[True]
    official: Literal[False]
    model_calls: Literal[5]
    tool_calls: Literal[5]
    input_tokens: Literal[0]
    output_tokens: Literal[0]
    model_cost_usd: Literal[0.0]
    typed_token_terminal: Literal[False]
    tool_sequence: tuple[str, ...]
    request_observations: tuple[RequestObservation, ...]
    every_model_turn_has_request_evidence: Literal[True]
    terminal_result_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    observation_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        if len(self.request_observations) != self.model_calls:
            raise ValueError("Lean calibration request coverage differs")
        if tuple(item.request_index for item in self.request_observations) != tuple(
            range(1, self.model_calls + 1)
        ):
            raise ValueError("Lean calibration request order differs")
        expected_tools = ("read_file", "apply_patch", "run_check", "get_diff", "finish_task")
        if self.tool_sequence != expected_tools:
            raise ValueError("Lean calibration terminal tool sequence differs")
        expected_id = sha256_json(self.model_dump(mode="json", exclude={"observation_id"}))
        if self.observation_id != expected_id:
            raise ValueError("Lean calibration observation identity differs")
        return self


class PairParityObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    task_id: str
    repetition: Literal[1, 2]
    no_memory_row_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    structured_row_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    terminal_tool_sequence_equal: Literal[True]
    request_count_equal: Literal[True]
    non_memory_request_semantics_equal: Literal[True]
    pair_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_pair(self) -> Self:
        expected = sha256_json(self.model_dump(mode="json", exclude={"pair_hash"}))
        if self.pair_hash != expected:
            raise ValueError("Lean calibration pair identity differs")
        return self


class BoundaryRevalidation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    phase_surface_cases: Literal[6]
    saturation_boundary_cases: Literal[9]
    split_budget_terminal_dimensions: Literal[3]
    all_phase_surfaces_exact: Literal[True]
    all_saturation_boundary_decisions_exact: Literal[True]
    all_split_budget_dimensions_present: Literal[True]
    source: Literal["exact-preregistered-predecessor-artifacts"]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_boundary(self) -> Self:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("Lean boundary revalidation hash differs")
        return self


class LeanRuntimeSourceQualification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-runtime-source-qualification-v1"]
    qualification_id: Literal["lean-harness-runtime-public-calibration-20260817-v1"]
    status: Literal["PUBLIC_MOCK_RUNTIME_SOURCE_QUALIFIED_NO_PROVIDER_AUTHORITY"]
    evidence_date: Literal["2026-08-17"]
    preregistration: FileBinding
    preregistration_id: Literal["lean-harness-runtime-integration-public-calibration-20260816-v1"]
    preregistration_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_contract_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    development_validation_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    realized_schedule_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    semantic_projection_policy: Literal[
        "remove-memory-delivery-event-selected-memory-and-volatile-runtime-artifact-provenance-v1"
    ]
    rows: tuple[CalibrationRowObservation, ...]
    pair_parity: tuple[PairParityObservation, ...]
    boundary_revalidation: BoundaryRevalidation
    expected_rows: Literal[12]
    resolved_rows: Literal[12]
    rows_per_condition: Literal[6]
    pair_count: Literal[6]
    model_turns: Literal[60]
    persisted_request_evidence_rows: Literal[60]
    terminal_tool_calls: Literal[60]
    typed_token_terminals: Literal[0]
    every_model_turn_has_request_evidence: Literal[True]
    every_pair_has_terminal_tool_sequence_parity: Literal[True]
    every_pair_has_non_memory_request_semantics_parity: Literal[True]
    all_rows_resolved: Literal[True]
    source_files: tuple[FileBinding, ...]
    validation_files: tuple[FileBinding, ...]
    source_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    public_calibration_task_package_loads: Literal[15]
    private_calibration_evaluator_runs: Literal[12]
    runner_calls: Literal[12]
    local_tool_execution_calls: Literal[60]
    local_evaluator_calls: Literal[12]
    provider_transport_calls: Literal[0]
    provider_generation_calls: Literal[0]
    network_calls: Literal[0]
    docker_cli_calls: Literal[0]
    added_model_cost_usd: Literal[0]
    source_integration_completed: Literal[True]
    source_qualification_completed: Literal[True]
    validation_frame_executed: Literal[True]
    quality_effect_estimate_authorized: Literal[False]
    memory_effect_estimate_authorized: Literal[False]
    official_analysis_authorized: Literal[False]
    provider_calls_authorized: Literal[False]
    paid_execution_authorized: Literal[False]
    future_runner_activation_authorized: Literal[False]
    fresh_memory_comparison_authorized: Literal[False]
    next_gate: Literal[
        "separately-preregister-fresh-design-before-any-provider-or-new-memory-comparison"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_qualification(self) -> Self:
        if tuple(item.order for item in self.rows) != tuple(range(1, 13)):
            raise ValueError("Lean qualification row order differs")
        if len({item.preregistered_row_id for item in self.rows}) != 12:
            raise ValueError("Lean qualification row identity is duplicated")
        if (
            sum(item.condition == "no_memory" for item in self.rows) != 6
            or sum(item.condition == "structured" for item in self.rows) != 6
        ):
            raise ValueError("Lean qualification condition denominator differs")
        if len(self.pair_parity) != 6:
            raise ValueError("Lean qualification pair denominator differs")
        if tuple(item.path for item in self.source_files) != SOURCE_PATHS:
            raise ValueError("Lean qualification source inventory differs")
        if tuple(item.path for item in self.validation_files) != VALIDATION_PATHS:
            raise ValueError("Lean qualification validation inventory differs")
        if self.source_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.source_files]
        ):
            raise ValueError("Lean qualification source inventory hash differs")
        if self.validation_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.validation_files]
        ):
            raise ValueError("Lean qualification validation inventory hash differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("Lean qualification content hash differs")
        return self


def _binding(root: Path, relative: str, *, content_hash: str | None = None) -> FileBinding:
    selected = ensure_within(root, relative)
    if not selected.is_file() or selected.is_symlink():
        raise RecoveryError(f"Lean qualification input is unavailable: {relative}")
    raw = selected.read_bytes()
    return FileBinding(
        path=relative,
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        content_hash=content_hash,
    )


def _scrub_non_memory_semantics(value: Any) -> Any:
    if type(value) is dict:
        keys = set(value)
        if keys >= _ARTIFACT_DESCRIPTOR_KEYS:
            return {"media_type": value["media_type"]}
        has_artifact_descriptor = any(
            key.endswith("_artifact") and type(item) is dict for key, item in value.items()
        )
        return {
            key: _scrub_non_memory_semantics(item)
            for key, item in value.items()
            if key not in _VOLATILE_SEMANTIC_KEYS
            and not (has_artifact_descriptor and key in {"content_hash", "size_bytes"})
        }
    if type(value) is list:
        return [_scrub_non_memory_semantics(item) for item in value]
    return value


def non_memory_request_semantics_hash(evidence: LeanHarnessRequestEvidence) -> str:
    """Hash task/tool/request meaning while excluding treatment and runtime nonce data."""

    body = json.loads(canonical_json(evidence.request_body))
    try:
        context = json.loads(body["context"])
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RecoveryError("Lean qualification request context is invalid") from exc
    if type(context) is not dict or type(context.get("recent_events")) is not list:
        raise RecoveryError("Lean qualification request context shape differs")
    context["selected_memory"] = None
    context["recent_events"] = [
        item
        for item in context["recent_events"]
        if type(item) is dict and item.get("type") != "MemoryRetrieved"
    ]
    body["context"] = _scrub_non_memory_semantics(context)
    return sha256_json(_scrub_non_memory_semantics(body))


def _request_observations(
    runner: AgentRunner,
    run_id: str,
) -> tuple[RequestObservation, ...]:
    events = runner.state.list_events(run_id)
    context_events = [item for item in events if item.type == EventType.CONTEXT_BUILT]
    model_events = [item for item in events if item.type == EventType.MODEL_CALLED]
    if len(context_events) != len(model_events):
        raise RecoveryError("Lean calibration request/model coverage differs")
    observations: list[RequestObservation] = []
    for index, event in enumerate(context_events, 1):
        try:
            payload = json.loads(Path(str(event.payload["artifact_path"])).read_text("utf-8"))
        except (KeyError, OSError, TypeError, json.JSONDecodeError) as exc:
            raise RecoveryError("Lean calibration request artifact is unavailable") from exc
        evidence = validate_persisted_lean_harness_request(payload)
        try:
            phase = json.loads(evidence.request_body["context"])["phase"]
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise RecoveryError("Lean calibration request phase is unavailable") from exc
        observations.append(
            RequestObservation(
                request_index=index,
                request_evidence_content_hash=evidence.content_hash,
                phase=phase,
                selected_tool_names=evidence.phase_tool_surface.selected_tool_names,
                selected_tool_schema_hash=evidence.selected_tool_schema_hash,
                request_mode=evidence.finalization_request_mode.mode,
                effective_max_output_tokens=evidence.effective_max_output_tokens,
                requested_input_tokens=evidence.requested_input_tokens,
                non_memory_request_semantics_hash=non_memory_request_semantics_hash(evidence),
                persisted_before_dispatch=(evidence.request_evidence_persisted_before_dispatch),
                provider_authority_granted=evidence.provider_authority_granted,
            )
        )
    return tuple(observations)


def _row_observation(
    *,
    runner: AgentRunner,
    schedule_row: Any,
    result: dict[str, Any],
) -> CalibrationRowObservation:
    events = runner.state.list_events(result["run_id"])
    tools = tuple(
        str(item.payload["tool"]) for item in events if item.type == EventType.TOOL_CALLED
    )
    requests = _request_observations(runner, result["run_id"])
    stable_result = {
        "agent_submission_status": result.get("agent_submission_status"),
        "evaluation_status": result.get("evaluation_status"),
        "scope_compliant_success": result.get("scope_compliant_success"),
        "official": result.get("official"),
        "verdicts": result.get("verdicts"),
        "outcome_kind": result.get("outcome_kind"),
        "terminal_error": result.get("terminal_error"),
    }
    body: dict[str, Any] = {
        "order": schedule_row.order,
        "preregistered_row_id": schedule_row.row_id,
        "run_id": result["run_id"],
        "task_id": schedule_row.task_id,
        "task_version": schedule_row.task_version,
        "task_path": schedule_row.task_path,
        "condition": schedule_row.condition,
        "repetition": schedule_row.repetition,
        "resolved": result.get("outcome_kind") == "resolved",
        "scope_compliant_success": result.get("scope_compliant_success"),
        "official": result.get("official"),
        "model_calls": result["usage"]["model_calls"],
        "tool_calls": result["usage"]["tool_calls"],
        "input_tokens": result["usage"]["input_tokens"],
        "output_tokens": result["usage"]["output_tokens"],
        "model_cost_usd": result["usage"]["model_cost_usd"],
        "typed_token_terminal": False,
        "tool_sequence": tools,
        "request_observations": tuple(item.model_dump(mode="python") for item in requests),
        "every_model_turn_has_request_evidence": len(requests) == result["usage"]["model_calls"],
        "terminal_result_hash": sha256_json(stable_result),
    }
    return CalibrationRowObservation.model_validate({**body, "observation_id": sha256_json(body)})


def _pair_parity(rows: tuple[CalibrationRowObservation, ...]) -> tuple[PairParityObservation, ...]:
    pairs: list[PairParityObservation] = []
    for task_id in ("config-falsy-override", "csv-quoted-newline", "path-prefix-boundary"):
        for repetition in (1, 2):
            block = tuple(
                item for item in rows if item.task_id == task_id and item.repetition == repetition
            )
            no_memory = next(item for item in block if item.condition == "no_memory")
            structured = next(item for item in block if item.condition == "structured")
            no_semantics = tuple(
                item.non_memory_request_semantics_hash for item in no_memory.request_observations
            )
            structured_semantics = tuple(
                item.non_memory_request_semantics_hash for item in structured.request_observations
            )
            body = {
                "task_id": task_id,
                "repetition": repetition,
                "no_memory_row_id": no_memory.preregistered_row_id,
                "structured_row_id": structured.preregistered_row_id,
                "terminal_tool_sequence_equal": no_memory.tool_sequence == structured.tool_sequence,
                "request_count_equal": len(no_memory.request_observations)
                == len(structured.request_observations),
                "non_memory_request_semantics_equal": no_semantics == structured_semantics,
            }
            pairs.append(
                PairParityObservation.model_validate({**body, "pair_hash": sha256_json(body)})
            )
    return tuple(pairs)


def _boundary_revalidation(
    root: Path, preregistration: LeanRuntimeIntegrationPreregistration
) -> BoundaryRevalidation:
    predecessor_by_path = {item.path: item for item in preregistration.predecessor_artifacts}
    saturation_path = (
        "experiments/lean-harness-saturation-recovery-shadow-public-qualification-20260816-v2.json"
    )
    budget_path = "experiments/lean-harness-budget-adequacy-public-qualification-20260816-v1.json"
    documents: dict[str, dict[str, Any]] = {}
    for relative in (saturation_path, budget_path):
        binding = predecessor_by_path[relative]
        raw = ensure_within(root, relative).read_bytes()
        if len(raw) != binding.file_bytes or sha256_bytes(raw) != binding.file_sha256:
            raise RecoveryError("Lean qualification predecessor boundary file differs")
        value = json.loads(raw)
        if value.get("content_hash") != binding.content_hash:
            raise RecoveryError("Lean qualification predecessor boundary content differs")
        documents[relative] = value
    saturation = documents[saturation_path]
    budget = documents[budget_path]
    terminal_dimensions = {
        item["expected_terminal_dimension"]
        for item in budget["boundary_observations"]
        if item["expected_terminal_dimension"] != "none"
    }
    body = {
        "phase_surface_cases": len(saturation["phase_observations"]),
        "saturation_boundary_cases": len(saturation["boundary_observations"]),
        "split_budget_terminal_dimensions": len(terminal_dimensions),
        "all_phase_surfaces_exact": saturation["all_phase_surfaces_exact"],
        "all_saturation_boundary_decisions_exact": saturation["all_boundary_decisions_exact"],
        "all_split_budget_dimensions_present": terminal_dimensions
        == {"input_tokens", "output_tokens", "total_tokens"},
        "source": "exact-preregistered-predecessor-artifacts",
    }
    return BoundaryRevalidation.model_validate({**body, "content_hash": sha256_json(body)})


def _guarded_frame(
    root: Path,
    preregistration: LeanRuntimeIntegrationPreregistration,
) -> tuple[CalibrationRowObservation, ...]:
    packages = {
        item.task_id: load_task_package(ensure_within(root, item.path))
        for item in preregistration.development_validation.tasks
    }
    original_available = DockerSandbox.available
    original_next_turn = OpenAIResponsesAdapter.next_turn
    original_create_connection = socket.create_connection
    original_socket_connect = socket.socket.connect
    original_popen = subprocess.Popen

    def blocked_external(*_args: Any, **_kwargs: Any) -> Any:
        raise RecoveryError("Lean public qualification attempted a forbidden external call")

    def guarded_popen(args: Any, *popen_args: Any, **popen_kwargs: Any) -> Any:
        command = args[0] if isinstance(args, (list, tuple)) and args else args
        executable = str(command).lower()
        if executable.endswith("docker") or executable.endswith("docker.exe"):
            raise RecoveryError("Lean public qualification attempted Docker CLI")
        return original_popen(args, *popen_args, **popen_kwargs)

    DockerSandbox.available = staticmethod(lambda: False)
    OpenAIResponsesAdapter.next_turn = blocked_external
    socket.create_connection = blocked_external
    socket.socket.connect = blocked_external
    subprocess.Popen = guarded_popen
    observations: list[CalibrationRowObservation] = []
    scratch_parent = ensure_within(root, ".tmp")
    scratch_parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(
            prefix="lean-runtime-source-qualification-",
            dir=scratch_parent,
        ) as temporary:
            runtime_root = Path(temporary) / "runtime"
            for schedule_row in preregistration.development_validation.schedule:
                package = packages[schedule_row.task_id]
                run_id = (
                    f"run_lean_calibration_{schedule_row.order:02d}_"
                    f"{schedule_row.row_id.removeprefix('sha256:')[:12]}"
                )
                manifest = build_lean_harness_calibration_manifest(
                    package,
                    run_id=run_id,
                    condition=MemoryCondition(schedule_row.condition),
                )
                runner = AgentRunner(runtime_root)
                result = runner.start(
                    ensure_within(root, schedule_row.task_path) / "public.yaml",
                    model="mock",
                    manifest=manifest,
                )
                observations.append(
                    _row_observation(
                        runner=runner,
                        schedule_row=schedule_row,
                        result=result,
                    )
                )
    finally:
        DockerSandbox.available = staticmethod(original_available)
        OpenAIResponsesAdapter.next_turn = original_next_turn
        socket.create_connection = original_create_connection
        socket.socket.connect = original_socket_connect
        subprocess.Popen = original_popen
    return tuple(observations)


def build_lean_runtime_source_qualification(
    repository: str | Path = ".",
) -> LeanRuntimeSourceQualification:
    root = Path(repository).resolve()
    preregistration = load_lean_runtime_integration_preregistration(root)
    preregistration_binding = _binding(
        root,
        PREREGISTRATION_PATH,
        content_hash=preregistration.content_hash,
    )
    if preregistration_binding != FileBinding(
        path=PREREGISTRATION_PATH,
        file_bytes=PREREGISTRATION_FILE_BYTES,
        file_sha256=PREREGISTRATION_FILE_SHA256,
        content_hash=PREREGISTRATION_CONTENT_HASH,
    ):
        raise RecoveryError("Lean runtime preregistration binding differs")
    source_files = tuple(_binding(root, item) for item in SOURCE_PATHS)
    validation_files = tuple(_binding(root, item) for item in VALIDATION_PATHS)
    rows = _guarded_frame(root, preregistration)
    pairs = _pair_parity(rows)
    boundary = _boundary_revalidation(root, preregistration)
    body: dict[str, Any] = {
        "schema_version": QUALIFICATION_SCHEMA,
        "qualification_id": QUALIFICATION_ID,
        "status": "PUBLIC_MOCK_RUNTIME_SOURCE_QUALIFIED_NO_PROVIDER_AUTHORITY",
        "evidence_date": EVIDENCE_DATE,
        "preregistration": preregistration_binding.model_dump(mode="python"),
        "preregistration_id": PREREGISTRATION_ID,
        "preregistration_content_hash": preregistration.content_hash,
        "runtime_contract_hash": preregistration.runtime_contract_hash,
        "development_validation_hash": preregistration.development_validation_hash,
        "realized_schedule_hash": preregistration.development_validation.realized_schedule_hash,
        "semantic_projection_policy": (
            "remove-memory-delivery-event-selected-memory-and-volatile-runtime-artifact-provenance-v1"
        ),
        "rows": tuple(item.model_dump(mode="python") for item in rows),
        "pair_parity": tuple(item.model_dump(mode="python") for item in pairs),
        "boundary_revalidation": boundary.model_dump(mode="python"),
        "expected_rows": 12,
        "resolved_rows": sum(item.resolved for item in rows),
        "rows_per_condition": 6,
        "pair_count": len(pairs),
        "model_turns": sum(item.model_calls for item in rows),
        "persisted_request_evidence_rows": sum(len(item.request_observations) for item in rows),
        "terminal_tool_calls": sum(item.tool_calls for item in rows),
        "typed_token_terminals": sum(item.typed_token_terminal for item in rows),
        "every_model_turn_has_request_evidence": all(
            item.every_model_turn_has_request_evidence for item in rows
        ),
        "every_pair_has_terminal_tool_sequence_parity": all(
            item.terminal_tool_sequence_equal for item in pairs
        ),
        "every_pair_has_non_memory_request_semantics_parity": all(
            item.non_memory_request_semantics_equal for item in pairs
        ),
        "all_rows_resolved": all(item.resolved for item in rows),
        "source_files": tuple(item.model_dump(mode="python") for item in source_files),
        "validation_files": tuple(item.model_dump(mode="python") for item in validation_files),
        "source_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in source_files]
        ),
        "validation_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in validation_files]
        ),
        "public_calibration_task_package_loads": 15,
        "private_calibration_evaluator_runs": 12,
        "runner_calls": 12,
        "local_tool_execution_calls": 60,
        "local_evaluator_calls": 12,
        "provider_transport_calls": 0,
        "provider_generation_calls": 0,
        "network_calls": 0,
        "docker_cli_calls": 0,
        "added_model_cost_usd": 0,
        "source_integration_completed": True,
        "source_qualification_completed": True,
        "validation_frame_executed": True,
        "quality_effect_estimate_authorized": False,
        "memory_effect_estimate_authorized": False,
        "official_analysis_authorized": False,
        "provider_calls_authorized": False,
        "paid_execution_authorized": False,
        "future_runner_activation_authorized": False,
        "fresh_memory_comparison_authorized": False,
        "next_gate": (
            "separately-preregister-fresh-design-before-any-provider-or-new-memory-comparison"
        ),
    }
    return LeanRuntimeSourceQualification.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )


def qualification_bytes(qualification: LeanRuntimeSourceQualification) -> bytes:
    return (
        json.dumps(
            qualification.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def _validate_current_bindings(
    root: Path,
    qualification: LeanRuntimeSourceQualification,
) -> None:
    preregistration = load_lean_runtime_integration_preregistration(root)
    if (
        qualification.preregistration
        != _binding(root, PREREGISTRATION_PATH, content_hash=preregistration.content_hash)
        or qualification.preregistration_id != preregistration.preregistration_id
        or qualification.preregistration_content_hash != preregistration.content_hash
        or qualification.runtime_contract_hash != preregistration.runtime_contract_hash
        or qualification.development_validation_hash != preregistration.development_validation_hash
        or qualification.realized_schedule_hash
        != preregistration.development_validation.realized_schedule_hash
        or qualification.source_files != tuple(_binding(root, item) for item in SOURCE_PATHS)
        or qualification.validation_files
        != tuple(_binding(root, item) for item in VALIDATION_PATHS)
    ):
        raise RecoveryError("Lean runtime qualification current binding differs")
    if qualification.boundary_revalidation != _boundary_revalidation(root, preregistration):
        raise RecoveryError("Lean runtime qualification predecessor boundary differs")


def load_lean_runtime_source_qualification(
    repository: str | Path = ".",
    qualification_path: str = QUALIFICATION_PATH,
) -> LeanRuntimeSourceQualification:
    root = Path(repository).resolve()
    selected = ensure_within(root, qualification_path)
    if not selected.is_file() or selected.is_symlink():
        raise RecoveryError("Lean runtime source qualification is unavailable")
    raw = selected.read_bytes()
    try:
        qualification = LeanRuntimeSourceQualification.model_validate_json(raw)
    except ValueError as exc:
        raise RecoveryError("Lean runtime source qualification is invalid") from exc
    if qualification_bytes(qualification) != raw:
        raise RecoveryError("Lean runtime source qualification bytes differ")
    canonical_consumed = ensure_within(root, QUALIFICATION_PATH)
    if selected == canonical_consumed:
        if (
            len(raw) != CONSUMED_QUALIFICATION_FILE_BYTES
            or sha256_bytes(raw) != CONSUMED_QUALIFICATION_FILE_SHA256
        ):
            raise RecoveryError("consumed Lean runtime qualification identity differs")
        return qualification
    _validate_current_bindings(root, qualification)
    return qualification


def materialize_lean_runtime_source_qualification(
    repository: str | Path = ".",
    output_path: str = QUALIFICATION_PATH,
) -> LeanRuntimeSourceQualification:
    root = Path(repository).resolve()
    output = ensure_within(root, output_path)
    if output.exists():
        return load_lean_runtime_source_qualification(root, output_path)
    qualification = build_lean_runtime_source_qualification(root)
    raw = qualification_bytes(qualification)
    output.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(output, flags, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        raise
    return load_lean_runtime_source_qualification(root, output_path)
