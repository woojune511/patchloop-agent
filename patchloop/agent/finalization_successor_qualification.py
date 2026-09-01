"""Offline qualification for the post-R4 Lean finalization successor.

The qualification reads the immutable public Rapid R4 bundle and exercises
only deterministic request projections.  It does not open runtime state,
dispatch a model, execute a tool, or grant a future Rapid identity.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.context import BuiltContext
from patchloop.agent.lean_runtime import (
    LEAN_COMPLETION_POLICY_VERSION_V4,
    LEAN_FINALIZATION_ALLOWANCE_POLICY_VERSION_V4,
    LEAN_RUNTIME_POLICY_VERSION_V4,
    LeanHarnessRequestEvidenceV4,
    assemble_lean_harness_request,
    load_lean_harness_dependencies,
)
from patchloop.agent.phases import EvidenceState
from patchloop.agent.tools import TOOL_SCHEMAS_V9
from patchloop.contracts import Budget, MemoryCondition, Usage
from patchloop.errors import RecoveryError
from patchloop.memory.fixed_bundle import build_fixed_memory_delivery
from patchloop.util import ensure_within, sha256_bytes, sha256_json, sha256_text

QUALIFICATION_SCHEMA = "lean-finalization-successor-qualification-v1"
QUALIFICATION_ID = "anyio-r4-finalization-successor-20260822-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-finalization-successor-public-qualification-20260822-v1.json"
)
QUALIFICATION_FILE_BYTES = 10_944
QUALIFICATION_FILE_SHA256 = (
    "sha256:3dc973ec737058b6dd964de1c652f174c6274e060eabc8ace29c3b77694604f1"
)
R4_RESULT_PATH = Path(
    "reports/rapid-development/"
    "rapid-public-dev-anyio-targeted-20260822-r4-041dbeddae57.jsonl"
)
R4_RESULT_FILE_BYTES = 9_530
R4_RESULT_FILE_SHA256 = (
    "sha256:dc3fdc8d35f236cd810d47b7be4dff55599d0a242f5c4be9cd98071d7d8ccf8c"
)
R4_RESULT_HEAD = (
    "sha256:65222f5a733ee2c757c87b6db76d03dd0a182a90b44e6889429041424e164f74"
)
R4_EXECUTION_HASH = (
    "sha256:041dbeddae57ae3b512207b064f9475175333f0cc134db1fc6b6fb8ece92bd98"
)
SOURCE_PATHS = (
    "patchloop/agent/finalization_successor_qualification.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/phases.py",
    "patchloop/agent/request_allowance.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/contracts.py",
)
VALIDATION_PATHS = (
    "tests/test_finalization_successor_qualification.py",
    "tests/test_lean_runtime.py",
    "tests/test_phase_evidence.py",
)


class FileBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    file_bytes: int = Field(ge=1)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class FinalizationScenarioObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    scenario_id: str = Field(pattern=r"^[a-z0-9-]+$")
    condition: Literal["no_memory", "structured"]
    input_tokens_used: int = Field(ge=0)
    output_tokens_used: int = Field(ge=0)
    completion_target: Literal[
        "mutation",
        "corrective-mutation",
        "visible-check",
        "diff-review",
        "submission",
    ]
    selected_tool_names: tuple[str, ...] = Field(min_length=1)
    registered_check_preferred: Literal[True]
    recheck_after_mutation_required: bool
    request_mode: Literal["finalization"]
    configured_max_output_tokens: Literal[25000]
    effective_max_output_tokens: int = Field(ge=1, le=25_000)
    allowance_decision: Literal["admit_full", "admit_reduced"]
    allowance_binding_dimension: Literal["input_tokens", "output_tokens", "total_tokens"] | None
    request_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    normalized_no_memory_request_body_sha256: str = Field(
        pattern=r"^sha256:[0-9a-f]{64}$"
    )
    request_evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    provider_authority_granted: Literal[False]

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        expected_recheck = self.completion_target in {
            "mutation",
            "corrective-mutation",
        }
        if self.recheck_after_mutation_required is not expected_recheck:
            raise ValueError("scenario recheck binding differs")
        if self.allowance_decision == "admit_full":
            if self.effective_max_output_tokens != self.configured_max_output_tokens:
                raise ValueError("full scenario does not retain the configured ceiling")
        elif self.effective_max_output_tokens >= self.configured_max_output_tokens:
            raise ValueError("reduced scenario does not reduce the configured ceiling")
        return self


class FinalizationSuccessorQualification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-finalization-successor-qualification-v1"]
    qualification_id: Literal["anyio-r4-finalization-successor-20260822-v1"]
    status: Literal[
        "PUBLIC_OFFLINE_FINALIZATION_SUCCESSOR_QUALIFIED_RUNTIME_CLOSED"
    ]
    evidence_date: Literal["2026-08-22"]
    source_result: FileBinding
    source_execution_hash: Literal[
        "sha256:041dbeddae57ae3b512207b064f9475175333f0cc134db1fc6b6fb8ece92bd98"
    ]
    source_result_head: Literal[
        "sha256:65222f5a733ee2c757c87b6db76d03dd0a182a90b44e6889429041424e164f74"
    ]
    source_rows: Literal[6]
    source_evaluator_reached: Literal[0]
    source_baseline_token_terminals: Literal[3]
    source_lean_agent_failures: Literal[3]
    runtime_policy_version: Literal["lean-harness-v4"]
    tool_schema_version: Literal["v9"]
    context_policy_version: Literal["phase-evidence-v14"]
    completion_policy_version: Literal["completion-driven-current-diff-v2"]
    finalization_allowance_policy_version: Literal[
        "configured-ceiling-split-bounded-v1"
    ]
    predecessor_finalization_max_output_tokens: Literal[5000]
    successor_configured_max_output_tokens: Literal[25000]
    scenarios: tuple[FinalizationScenarioObservation, ...]
    condition_neutral_check_projection: Literal[True]
    corrective_mutation_requires_recheck: Literal[True]
    unchanged_failed_diff_recheck_forced: Literal[False]
    split_budget_remains_hard: Literal[True]
    policy_arithmetic_qualified: Literal[True]
    reasoning_adequacy_established: Literal[False]
    completion_improvement_established: Literal[False]
    quality_improvement_established: Literal[False]
    source_files: tuple[FileBinding, ...]
    validation_files: tuple[FileBinding, ...]
    source_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    public_result_files_read: Literal[1]
    runtime_state_files_read: Literal[0]
    public_task_files_read: Literal[0]
    private_task_files_read: Literal[0]
    hidden_files_read: Literal[0]
    reference_patches_read: Literal[0]
    provider_calls: Literal[0]
    runner_calls: Literal[0]
    tool_calls: Literal[0]
    docker_calls: Literal[0]
    evaluator_calls: Literal[0]
    added_model_cost_usd: Literal[0]
    runtime_activation_authorized: Literal[False]
    provider_calls_authorized: Literal[False]
    docker_execution_authorized: Literal[False]
    paid_execution_authorized: Literal[False]
    fresh_panel_authorized: Literal[False]
    next_gate: Literal[
        "review-offline-successor-before-any-new-rapid-candidate"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_qualification(self) -> Self:
        expected_ids = (
            "initial-mutation",
            "check-preferred-a",
            "check-preferred-c",
            "corrective-mutation",
            "diff-review",
            "submission",
            "split-reduced",
        )
        if tuple(item.scenario_id for item in self.scenarios) != expected_ids:
            raise ValueError("finalization scenarios differ")
        a_check, c_check = self.scenarios[1:3]
        if not (
            a_check.condition == "no_memory"
            and c_check.condition == "structured"
            and a_check.completion_target == c_check.completion_target == "visible-check"
            and a_check.selected_tool_names == c_check.selected_tool_names == ("run_check",)
            and a_check.effective_max_output_tokens
            == c_check.effective_max_output_tokens
            == 25_000
            and c_check.normalized_no_memory_request_body_sha256
            == a_check.request_body_hash
        ):
            raise ValueError("A/C check projection is not condition neutral")
        if self.source_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.source_files]
        ):
            raise ValueError("source inventory hash differs")
        if self.validation_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.validation_files]
        ):
            raise ValueError("validation inventory hash differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("qualification content hash differs")
        return self


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise ValueError(f"duplicate qualification key: {key}")
        output[key] = value
    return output


def _file_binding(root: Path, relative: str | Path) -> FileBinding:
    path = ensure_within(root, Path(relative).as_posix())
    raw = path.read_bytes()
    return FileBinding(
        path=path.relative_to(root).as_posix(),
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
    )


def _load_r4_result(root: Path) -> tuple[FileBinding, list[dict[str, Any]]]:
    binding = _file_binding(root, R4_RESULT_PATH)
    if (
        binding.file_bytes != R4_RESULT_FILE_BYTES
        or binding.file_sha256 != R4_RESULT_FILE_SHA256
    ):
        raise RecoveryError("Rapid R4 result bytes differ")
    path = ensure_within(root, R4_RESULT_PATH.as_posix())
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line, object_pairs_hook=_reject_duplicate_pairs)
        if type(event) is not dict:
            raise RecoveryError("Rapid R4 result event is not a mapping")
        events.append(event)
    previous: str | None = None
    for event in events:
        body = {key: value for key, value in event.items() if key != "content_hash"}
        if body.get("previous_event_hash") != previous:
            raise RecoveryError("Rapid R4 result hash chain differs")
        if event.get("content_hash") != sha256_json(body):
            raise RecoveryError("Rapid R4 result event hash differs")
        previous = event["content_hash"]
    if len(events) != 8 or previous != R4_RESULT_HEAD:
        raise RecoveryError("Rapid R4 result terminal differs")
    return binding, events


def _context(selected_memory: str | None) -> BuiltContext:
    payload = {
        "task": {"id": "offline-finalization-successor"},
        "selected_memory": selected_memory,
        "phase_policy": {"phase": "IMPLEMENT"},
        "recent_events": [],
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    return BuiltContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence={
            "schema_version": "context-build-evidence-v5",
            "rendered_characters": len(rendered),
            "rendered_bytes": len(rendered.encode("utf-8")),
            "tool_results": [],
        },
    )


def _phase() -> EvidenceState:
    return EvidenceState(
        worktree_diff_hash="sha256:current",
        mutation_event_sequence=1,
        mutation_present=True,
        completed_checks=(),
        pending_checks=("public-check",),
        current_diff_check_event_sequences=(),
        latest_check_sequence=None,
        review_event_sequence=None,
        review_presented_to_model=False,
        task_review_event_sequence=None,
        task_review_presented_to_model=False,
        task_review_coverage_complete=None,
        unresolved_coverage_target_ids=(),
        submission_ready=False,
        missing_evidence=(
            "visible_checks_current_diff",
            "final_diff_review_current_diff",
        ),
        allowed_next_actions=(
            "run_check",
            "apply_patch",
            "read_file",
            "search_files",
        ),
    )


def _budget() -> Budget:
    return Budget(
        max_model_calls=240,
        max_tool_calls=400,
        max_total_tokens=1_100_000,
        wall_clock_timeout_seconds=3_600,
        token_budget_schema_version="cumulative-split-v1",
        max_cumulative_input_tokens=1_000_000,
        max_cumulative_output_tokens=100_000,
    )


def _observation(
    *,
    repository: Path,
    scenario_id: str,
    condition: MemoryCondition,
    phase: EvidenceState,
    usage: Usage,
) -> FinalizationScenarioObservation:
    delivery = build_fixed_memory_delivery(condition=condition, token_budget=2_000)
    normalized_context = _context(None)
    built_context = _context(delivery.text or None)
    assembled = assemble_lean_harness_request(
        dependencies=load_lean_harness_dependencies(repository),
        built_context=built_context,
        normalized_no_memory_context=normalized_context,
        base_tool_schemas=TOOL_SCHEMAS_V9,
        phase_evidence=phase,
        events=(),
        usage=usage,
        budget=_budget(),
        model_id="patchloop-public-calibration-mock-v1",
        system_prompt="public mock prompt",
        configured_max_output_tokens=25_000,
        memory_delivery_evidence_sha256=delivery.evidence_sha256,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V4,
    )
    evidence = assembled.evidence
    if not isinstance(evidence, LeanHarnessRequestEvidenceV4):
        raise RecoveryError("finalization successor evidence type differs")
    surface = evidence.phase_tool_surface
    return FinalizationScenarioObservation(
        scenario_id=scenario_id,
        condition=condition.value,
        input_tokens_used=usage.input_tokens,
        output_tokens_used=usage.output_tokens,
        completion_target=surface.completion_target,
        selected_tool_names=surface.selected_tool_names,
        registered_check_preferred=surface.registered_check_preferred,
        recheck_after_mutation_required=surface.recheck_after_mutation_required,
        request_mode=evidence.finalization_request_mode.mode,
        configured_max_output_tokens=25_000,
        effective_max_output_tokens=evidence.effective_max_output_tokens,
        allowance_decision=evidence.split_allowance.decision,
        allowance_binding_dimension=evidence.split_allowance.binding_dimension,
        request_body_hash=evidence.request_body_hash,
        normalized_no_memory_request_body_sha256=(
            evidence.normalized_no_memory_request_body_sha256
        ),
        request_evidence_hash=evidence.content_hash,
        provider_authority_granted=evidence.provider_authority_granted,
    )


def build_finalization_successor_qualification(
    repository: str | Path = ".",
) -> FinalizationSuccessorQualification:
    root = Path(repository).resolve()
    source_result, events = _load_r4_result(root)
    rows = [event for event in events if event.get("event") == "row-terminal"]
    summary = events[-1]
    baseline = [row for row in rows if row.get("variant") == "baseline-v2v5"]
    lean = [row for row in rows if row.get("variant") == "lean-harness-v2"]
    if not (
        summary.get("execution_hash") == R4_EXECUTION_HASH
        and summary.get("evaluator_reached") == 0
        and len(rows) == len(baseline) + len(lean) == 6
        and sum(row.get("token_terminal") is True for row in baseline) == 3
        and all(row.get("outcome_kind") == "agent_failure" for row in lean)
    ):
        raise RecoveryError("Rapid R4 result projection differs")

    base = _phase()
    full_usage = Usage(input_tokens=890_000, output_tokens=60_000)
    scenarios = (
        _observation(
            repository=root,
            scenario_id="initial-mutation",
            condition=MemoryCondition.NO_MEMORY,
            phase=replace(
                base,
                mutation_event_sequence=None,
                mutation_present=False,
                allowed_next_actions=(
                    "apply_patch",
                    "run_check",
                    "read_file",
                    "search_files",
                ),
            ),
            usage=full_usage,
        ),
        _observation(
            repository=root,
            scenario_id="check-preferred-a",
            condition=MemoryCondition.NO_MEMORY,
            phase=base,
            usage=full_usage,
        ),
        _observation(
            repository=root,
            scenario_id="check-preferred-c",
            condition=MemoryCondition.STRUCTURED,
            phase=base,
            usage=full_usage,
        ),
        _observation(
            repository=root,
            scenario_id="corrective-mutation",
            condition=MemoryCondition.NO_MEMORY,
            phase=replace(
                base,
                latest_check_sequence=2,
                allowed_next_actions=("apply_patch", "read_file", "search_files"),
            ),
            usage=full_usage,
        ),
        _observation(
            repository=root,
            scenario_id="diff-review",
            condition=MemoryCondition.NO_MEMORY,
            phase=replace(
                base,
                completed_checks=("public-check",),
                pending_checks=(),
                current_diff_check_event_sequences=(2,),
                latest_check_sequence=2,
                allowed_next_actions=("get_diff",),
            ),
            usage=full_usage,
        ),
        _observation(
            repository=root,
            scenario_id="submission",
            condition=MemoryCondition.NO_MEMORY,
            phase=replace(
                base,
                completed_checks=("public-check",),
                pending_checks=(),
                current_diff_check_event_sequences=(2,),
                latest_check_sequence=2,
                review_event_sequence=3,
                review_presented_to_model=True,
                submission_ready=True,
                missing_evidence=(),
                allowed_next_actions=("finish_task",),
            ),
            usage=full_usage,
        ),
        _observation(
            repository=root,
            scenario_id="split-reduced",
            condition=MemoryCondition.NO_MEMORY,
            phase=base,
            usage=Usage(input_tokens=890_000, output_tokens=90_000),
        ),
    )
    source_files = tuple(_file_binding(root, path) for path in SOURCE_PATHS)
    validation_files = tuple(_file_binding(root, path) for path in VALIDATION_PATHS)
    body: dict[str, Any] = {
        "schema_version": QUALIFICATION_SCHEMA,
        "qualification_id": QUALIFICATION_ID,
        "status": "PUBLIC_OFFLINE_FINALIZATION_SUCCESSOR_QUALIFIED_RUNTIME_CLOSED",
        "evidence_date": "2026-08-22",
        "source_result": source_result.model_dump(mode="python"),
        "source_execution_hash": R4_EXECUTION_HASH,
        "source_result_head": R4_RESULT_HEAD,
        "source_rows": len(rows),
        "source_evaluator_reached": summary["evaluator_reached"],
        "source_baseline_token_terminals": sum(
            row["token_terminal"] is True for row in baseline
        ),
        "source_lean_agent_failures": sum(
            row["outcome_kind"] == "agent_failure" for row in lean
        ),
        "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V4,
        "tool_schema_version": "v9",
        "context_policy_version": "phase-evidence-v14",
        "completion_policy_version": LEAN_COMPLETION_POLICY_VERSION_V4,
        "finalization_allowance_policy_version": (
            LEAN_FINALIZATION_ALLOWANCE_POLICY_VERSION_V4
        ),
        "predecessor_finalization_max_output_tokens": (
            load_lean_harness_dependencies(root).reserve.max_output_tokens_per_turn
        ),
        "successor_configured_max_output_tokens": 25_000,
        "scenarios": tuple(item.model_dump(mode="python") for item in scenarios),
        "condition_neutral_check_projection": True,
        "corrective_mutation_requires_recheck": True,
        "unchanged_failed_diff_recheck_forced": False,
        "split_budget_remains_hard": True,
        "policy_arithmetic_qualified": True,
        "reasoning_adequacy_established": False,
        "completion_improvement_established": False,
        "quality_improvement_established": False,
        "source_files": tuple(item.model_dump(mode="python") for item in source_files),
        "validation_files": tuple(
            item.model_dump(mode="python") for item in validation_files
        ),
        "source_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in source_files]
        ),
        "validation_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in validation_files]
        ),
        "public_result_files_read": 1,
        "runtime_state_files_read": 0,
        "public_task_files_read": 0,
        "private_task_files_read": 0,
        "hidden_files_read": 0,
        "reference_patches_read": 0,
        "provider_calls": 0,
        "runner_calls": 0,
        "tool_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "added_model_cost_usd": 0,
        "runtime_activation_authorized": False,
        "provider_calls_authorized": False,
        "docker_execution_authorized": False,
        "paid_execution_authorized": False,
        "fresh_panel_authorized": False,
        "next_gate": "review-offline-successor-before-any-new-rapid-candidate",
    }
    return FinalizationSuccessorQualification.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )


def qualification_bytes(qualification: FinalizationSuccessorQualification) -> bytes:
    return (
        json.dumps(qualification.model_dump(mode="json"), indent=2, ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def load_finalization_successor_qualification(
    repository: str | Path = ".",
    path: str | Path = QUALIFICATION_PATH,
) -> FinalizationSuccessorQualification:
    root = Path(repository).resolve()
    selected = ensure_within(root, Path(path).as_posix())
    raw = selected.read_bytes()
    try:
        text = raw.decode("utf-8", errors="strict")
        json.loads(text, object_pairs_hook=_reject_duplicate_pairs)
        loaded = FinalizationSuccessorQualification.model_validate_json(text)
    except (UnicodeDecodeError, ValueError) as exc:
        raise RecoveryError("finalization successor qualification is invalid") from exc
    if qualification_bytes(loaded) != raw:
        raise RecoveryError("finalization successor qualification bytes are not canonical")
    canonical_consumed = ensure_within(root, QUALIFICATION_PATH.as_posix())
    if selected == canonical_consumed:
        if len(raw) != QUALIFICATION_FILE_BYTES or sha256_bytes(raw) != (
            QUALIFICATION_FILE_SHA256
        ):
            raise RecoveryError("consumed finalization qualification identity differs")
        return loaded
    expected = build_finalization_successor_qualification(root)
    if loaded != expected:
        raise RecoveryError("finalization successor qualification differs from source")
    return loaded


__all__ = [
    "QUALIFICATION_ID",
    "QUALIFICATION_FILE_BYTES",
    "QUALIFICATION_FILE_SHA256",
    "QUALIFICATION_PATH",
    "QUALIFICATION_SCHEMA",
    "FinalizationScenarioObservation",
    "FinalizationSuccessorQualification",
    "build_finalization_successor_qualification",
    "load_finalization_successor_qualification",
    "qualification_bytes",
]
