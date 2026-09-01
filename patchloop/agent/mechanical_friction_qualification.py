"""Deterministic zero-call qualification for Lean Harness V5 mechanics."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.mechanical_friction import (
    project_reasoning_incomplete_recovery,
    project_registered_check_outcome,
)
from patchloop.agent.structured_edit import (
    FreshStructuredEditArguments,
    FreshStructuredFileEdit,
    FreshStructuredReplacement,
    project_fresh_atomic_structured_edit,
)
from patchloop.contracts import Budget, EventType, RunEvent, TaskConstraints, Usage
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes, sha256_json

QUALIFICATION_PATH = Path(
    "experiments/lean-harness-mechanical-friction-public-qualification-20260823-v1.json"
)
R5_DIAGNOSIS_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-finalization-20260822-r5-public-trace-diagnosis-v1.json"
)
R5_DIAGNOSIS_BYTES = 6_757
R5_DIAGNOSIS_SHA256 = "sha256:7a6f1ae99f1f245e8bf3cfad90f45c908262f3e9b40e14ae89a22641b5388974"

SOURCE_FILES = (
    "patchloop/agent/structured_edit.py",
    "patchloop/agent/mechanical_friction.py",
    "patchloop/agent/saturation_recovery_shadow.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/tools.py",
    "patchloop/agent/runner.py",
    "patchloop/contracts.py",
)


class FileBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    bytes: int = Field(ge=1)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class QualificationScenario(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    scenario_id: str = Field(min_length=1)
    observed: dict[str, Any]
    observation_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_scenario(self) -> Self:
        if self.observation_hash != sha256_json(self.observed):
            raise ValueError("mechanical qualification observation hash differs")
        return self


class MechanicalFrictionQualification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-mechanical-friction-qualification-v1"]
    qualification_id: Literal["lean-harness-mechanical-friction-public-20260823-v1"]
    status: Literal["PUBLIC_OFFLINE_MECHANICAL_FRICTION_QUALIFIED_RUNTIME_CLOSED"]
    official: Literal[False]
    source_diagnosis: FileBinding
    source_files: tuple[FileBinding, ...]
    runtime_policy_version: Literal["lean-harness-v5"]
    tool_schema_version: Literal["v10"]
    context_policy_version: Literal["phase-evidence-v15"]
    structured_edit_policy_version: Literal["gateway-fresh-preimage-unique-text-v1"]
    check_outcome_policy_version: Literal["invocation-vs-behavior-v1"]
    incomplete_recovery_policy_version: Literal["reasoning-only-single-retry-split-reserved-v1"]
    scenarios: tuple[QualificationScenario, ...] = Field(min_length=5)
    scenario_set_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    r5_raw_context_mismatch_failures: Literal[7]
    r5_structured_preimage_hash_failures: Literal[6]
    r5_reasoning_only_incomplete_rows: Literal[3]
    historical_runtime_bytes_mutated: Literal[False]
    task_or_evaluator_contract_changed: Literal[False]
    hidden_or_private_data_read: Literal[False]
    provider_calls: Literal[0]
    docker_calls: Literal[0]
    evaluator_calls: Literal[0]
    added_cost_usd: Literal["0"]
    runtime_activation_authorized: Literal[False]
    paid_execution_authorized: Literal[False]
    quality_improvement_established: Literal[False]
    mechanical_paths_offline_qualified: Literal[True]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_qualification(self) -> Self:
        if self.source_diagnosis.path != R5_DIAGNOSIS_PATH.as_posix():
            raise ValueError("mechanical qualification diagnosis path differs")
        if (
            self.source_diagnosis.bytes != R5_DIAGNOSIS_BYTES
            or self.source_diagnosis.file_sha256 != R5_DIAGNOSIS_SHA256
        ):
            raise ValueError("mechanical qualification diagnosis binding differs")
        if tuple(item.path for item in self.source_files) != SOURCE_FILES:
            raise ValueError("mechanical qualification source inventory differs")
        scenario_ids = tuple(item.scenario_id for item in self.scenarios)
        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("mechanical qualification scenarios repeat")
        if self.scenario_set_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.scenarios]
        ):
            raise ValueError("mechanical qualification scenario set differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("mechanical qualification content hash differs")
        return self


def _binding(root: Path, relative: Path | str) -> FileBinding:
    relative_path = Path(relative)
    raw = (root / relative_path).read_bytes()
    return FileBinding(
        path=relative_path.as_posix(),
        bytes=len(raw),
        file_sha256=sha256_bytes(raw),
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


def _scenario(scenario_id: str, observed: dict[str, Any]) -> QualificationScenario:
    return QualificationScenario(
        scenario_id=scenario_id,
        observed=observed,
        observation_hash=sha256_json(observed),
    )


def build_mechanical_friction_qualification(
    repository: str | Path = ".",
) -> MechanicalFrictionQualification:
    root = Path(repository).resolve()
    diagnosis = _binding(root, R5_DIAGNOSIS_PATH)
    if diagnosis.bytes != R5_DIAGNOSIS_BYTES or diagnosis.file_sha256 != R5_DIAGNOSIS_SHA256:
        raise ContractError("R5 public trace diagnosis differs")
    diagnosis_document = json.loads((root / R5_DIAGNOSIS_PATH).read_text(encoding="utf-8"))
    edit_counts = diagnosis_document["edit_recovery_evidence"]["lean-harness-v4"]
    terminal_rows = diagnosis_document["lean_terminal_rows"]
    if (
        edit_counts["raw_context_mismatch_failures"] != 7
        or edit_counts["structured_preimage_hash_failures"] != 6
        or len(terminal_rows) != 3
    ):
        raise ContractError("R5 public mechanical diagnosis tuple differs")

    current = b"alpha\r\ncurrent target\r\nomega\r\n"
    fresh = project_fresh_atomic_structured_edit(
        action_id="qualification-fresh-edit",
        arguments=FreshStructuredEditArguments(
            files=(
                FreshStructuredFileEdit(
                    path="src/example.py",
                    replacements=(
                        FreshStructuredReplacement(
                            expected_text="alpha\ncurrent target",
                            replacement_text="alpha\nfixed target",
                        ),
                    ),
                ),
            ),
        ),
        source_worktree_diff_hash="sha256:" + "1" * 64,
        preimages={"src/example.py": current},
        constraints=TaskConstraints(allowed_paths=["src/**"]),
    )
    check = project_registered_check_outcome(
        check_id="public-check",
        exit_code=1,
        passed=False,
        timed_out=False,
        truncated=False,
        stdout="",
        stderr="targeted public behavior still fails",
        worktree_diff_hash="sha256:" + "2" * 64,
    )
    primary = project_reasoning_incomplete_recovery(
        phase_mode="finalization",
        events=(),
        usage=Usage(input_tokens=900_000, output_tokens=60_000),
        budget=_budget(),
        requested_input_tokens=5_000,
        configured_max_output_tokens=25_000,
    )
    incomplete_event = RunEvent(
        event_id="qualification-incomplete",
        run_id="qualification-run",
        sequence=1,
        type=EventType.MODEL_CALLED,
        timestamp=datetime(2026, 8, 23, tzinfo=UTC),
        actor="model-adapter",
        payload={
            "response_error_code": "incomplete_response",
            "response_incomplete_reason": "max_output_tokens",
            "output_tokens": primary.effective_max_output_tokens,
            "reasoning_output_tokens": primary.effective_max_output_tokens,
            "lean_incomplete_recovery_mode": primary.mode,
            "lean_reserved_retry_output_tokens": (primary.reserved_retry_output_tokens),
            "response_text_present": False,
            "response_tool_call_count": 0,
        },
    )
    retry = project_reasoning_incomplete_recovery(
        phase_mode="finalization",
        events=(incomplete_event,),
        usage=Usage(input_tokens=905_000, output_tokens=85_000, model_calls=1),
        budget=_budget(),
        requested_input_tokens=5_000,
        configured_max_output_tokens=25_000,
    )
    consumed_retry_event = RunEvent(
        event_id="qualification-consumed-retry",
        run_id="qualification-run",
        sequence=2,
        type=EventType.MODEL_CALLED,
        timestamp=datetime(2026, 8, 23, tzinfo=UTC),
        actor="model-adapter",
        payload={
            "lean_incomplete_recovery_mode": "retry",
            "response_text_present": False,
            "response_tool_call_count": 1,
        },
    )
    after_retry = project_reasoning_incomplete_recovery(
        phase_mode="finalization",
        events=(incomplete_event, consumed_retry_event),
        usage=Usage(input_tokens=910_000, output_tokens=87_048, model_calls=2),
        budget=_budget(),
        requested_input_tokens=5_000,
        configured_max_output_tokens=25_000,
    )
    direct_low = project_reasoning_incomplete_recovery(
        phase_mode="finalization",
        events=(),
        usage=Usage(input_tokens=990_000, output_tokens=98_284),
        budget=_budget(),
        requested_input_tokens=5_000,
        configured_max_output_tokens=25_000,
    )
    scenarios = (
        _scenario(
            "fresh-current-preimage",
            {
                "requested_schema": fresh.requested_arguments.schema_version,
                "refreshed_file_hashes": fresh.refreshed_file_hashes,
                "postimage_hash": fresh.atomic_projection.postimage_set_hash,
                "crlf_preserved": "\r\n" in fresh.atomic_projection.files[0].postimage_text,
                "model_supplied_preimage_hashes": fresh.model_supplied_preimage_hashes,
                "model_supplied_byte_offsets": fresh.model_supplied_byte_offsets,
            },
        ),
        _scenario(
            "typed-failed-visible-check",
            {
                "invocation_status": check.invocation_status,
                "behavior_status": check.behavior_status,
                "correction_required": check.correction_required,
                "failure_summary_hash": sha256_bytes(check.failure_summary.encode("utf-8")),
            },
        ),
        _scenario(
            "primary-output-reserve",
            primary.model_dump(mode="json"),
        ),
        _scenario(
            "reasoning-only-low-effort-retry",
            retry.model_dump(mode="json"),
        ),
        _scenario(
            "second-retry-reserve-disabled",
            after_retry.model_dump(mode="json"),
        ),
        _scenario(
            "tight-budget-direct-low",
            direct_low.model_dump(mode="json"),
        ),
    )
    body: dict[str, Any] = {
        "schema_version": "lean-harness-mechanical-friction-qualification-v1",
        "qualification_id": "lean-harness-mechanical-friction-public-20260823-v1",
        "status": "PUBLIC_OFFLINE_MECHANICAL_FRICTION_QUALIFIED_RUNTIME_CLOSED",
        "official": False,
        "source_diagnosis": diagnosis.model_dump(mode="python"),
        "source_files": tuple(
            _binding(root, relative).model_dump(mode="python") for relative in SOURCE_FILES
        ),
        "runtime_policy_version": "lean-harness-v5",
        "tool_schema_version": "v10",
        "context_policy_version": "phase-evidence-v15",
        "structured_edit_policy_version": "gateway-fresh-preimage-unique-text-v1",
        "check_outcome_policy_version": "invocation-vs-behavior-v1",
        "incomplete_recovery_policy_version": ("reasoning-only-single-retry-split-reserved-v1"),
        "scenarios": tuple(item.model_dump(mode="python") for item in scenarios),
        "scenario_set_hash": sha256_json([item.model_dump(mode="json") for item in scenarios]),
        "r5_raw_context_mismatch_failures": 7,
        "r5_structured_preimage_hash_failures": 6,
        "r5_reasoning_only_incomplete_rows": 3,
        "historical_runtime_bytes_mutated": False,
        "task_or_evaluator_contract_changed": False,
        "hidden_or_private_data_read": False,
        "provider_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "added_cost_usd": "0",
        "runtime_activation_authorized": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "mechanical_paths_offline_qualified": True,
    }
    return MechanicalFrictionQualification.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )


def qualification_bytes(qualification: MechanicalFrictionQualification) -> bytes:
    return (canonical_json(qualification.model_dump(mode="json")) + "\n").encode("utf-8")


def load_mechanical_friction_qualification(
    repository: str | Path = ".",
) -> MechanicalFrictionQualification:
    path = Path(repository).resolve() / QUALIFICATION_PATH
    raw = path.read_bytes()
    try:
        qualification = MechanicalFrictionQualification.model_validate_json(raw)
    except ValueError as exc:
        raise ContractError("mechanical friction qualification is invalid") from exc
    if qualification_bytes(qualification) != raw:
        raise ContractError("mechanical friction qualification bytes are not canonical")
    return qualification
