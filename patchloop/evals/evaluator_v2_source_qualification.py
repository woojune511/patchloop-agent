"""Offline qualification for the evaluator-v2 A/C successor.

The artifact produced here binds exact local source, the frozen R3 treatment,
the two development-validation task packages, and a new successor-suite
identity.  It never starts an agent, evaluator, provider, Docker process, or
credential observation and grants none of those authorities.
"""

from __future__ import annotations

import os
import stat
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field, ValidationError, field_validator, model_validator

from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.contracts import (
    EvaluatorSafetyContract,
    FrozenStrictModel,
    MemoryCondition,
    RunManifest,
    TaskPackage,
    build_evaluator_contract_binding,
)
from patchloop.errors import ContractError
from patchloop.memory.fixed_bundle import (
    D110_INDEX_CONTENT_HASH,
    D110_INDEX_VERSION,
    FIXED_BUNDLE_BYTES,
    FIXED_BUNDLE_POLICY_VERSION,
    FIXED_BUNDLE_SHA256,
    build_fixed_memory_delivery,
)
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, safe_relative_path, sha256_bytes, sha256_json
from patchloop.verifier.evidence import evaluator_v2_marker_set_hash
from patchloop.verifier.runtime_evidence import (
    EvaluatorV2RuntimeAuthority,
    build_evaluator_safety_contract_v2,
    evaluator_v2_runtime_tuple_hash,
)

SCHEMA_VERSION = "evaluator-v2-ac-source-qualification-v6"
QUALIFICATION_ID = "dev-validation-ac-fixed-bundle-evaluator-v2-20260814-r6"
STATUS = "OFFLINE_SOURCE_QUALIFIED_LIVE_CLOSED"

PLAN_PATH = Path("experiments/ac-structured-pilot-v7.plan.yaml")
BASE_SUITE_PATH = Path("experiments/dev-validation-ac-fixed-bundle-readiness-20260814-r4.yaml")
FAST_PREDECESSOR_SUITE_PATH = Path(
    "experiments/dev-validation-ac-fixed-bundle-readiness-20260813-r3.yaml"
)
OUTPUT_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-ac-successor-offline-source-qualification-r6.json"
)

TASK_PATHS = (
    Path("tasks/dev-validation/moto-query-scanned-count"),
    Path("tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes"),
)

SOURCE_PATHS = tuple(
    sorted(
        (
            Path("pyproject.toml"),
            Path("uv.lock"),
            BASE_SUITE_PATH,
            FAST_PREDECESSOR_SUITE_PATH,
            Path("patchloop/artifacts.py"),
            Path("patchloop/cli.py"),
            Path("patchloop/contracts.py"),
            Path("patchloop/environment.py"),
            Path("patchloop/errors.py"),
            Path("patchloop/runtime.py"),
            Path("patchloop/task_loader.py"),
            Path("patchloop/util.py"),
            Path("patchloop/repository.py"),
            Path("patchloop/agent/runner.py"),
            Path("patchloop/agent/context.py"),
            Path("patchloop/agent/investigation.py"),
            Path("patchloop/agent/tools.py"),
            Path("patchloop/evals/budget.py"),
            Path("patchloop/evals/evaluator_v2_source_qualification.py"),
            Path("patchloop/evals/policy_replay.py"),
            Path("patchloop/evals/qualification.py"),
            Path("patchloop/evals/report.py"),
            Path("patchloop/evals/runner.py"),
            Path("patchloop/memory/__init__.py"),
            Path("patchloop/memory/fixed_bundle.py"),
            Path("patchloop/sandbox/runner.py"),
            Path("patchloop/state/ownership.py"),
            Path("patchloop/state/store.py"),
            Path("patchloop/verifier/core.py"),
            Path("patchloop/verifier/evidence.py"),
            Path("patchloop/verifier/receipt.py"),
            Path("patchloop/verifier/runtime_evidence.py"),
        ),
        key=lambda item: item.as_posix(),
    )
)

VALIDATION_PATHS = tuple(
    sorted(
        (
            Path("scripts/build_evaluator_v2_ac_source_qualification.py"),
            Path("tests/test_ac_campaign_finalization.py"),
            Path("tests/test_ac_fixed_bundle_cost_completion.py"),
            Path("tests/test_ac_row_start_consumption.py"),
            Path("tests/test_agent_runtime.py"),
            Path("tests/test_budget_diagnostics.py"),
            Path("tests/test_documentation_structure.py"),
            Path("tests/test_evaluator_v2_contracts.py"),
            Path("tests/test_evaluator_v2_source_qualification.py"),
            Path("tests/test_fast_preflight.py"),
            Path("tests/test_report.py"),
            Path("tests/test_sandbox.py"),
            Path("tests/test_split_token_qualification.py"),
            Path("tests/test_split_token_suite.py"),
            Path("tests/test_trace_qualification.py"),
        ),
        key=lambda item: item.as_posix(),
    )
)

_EXPECTED_SCHEDULE = (
    (1, "moto-query-scanned-count", MemoryCondition.NO_MEMORY, 1),
    (2, "moto-query-scanned-count", MemoryCondition.STRUCTURED, 1),
    (3, "babel-strict-grouped-decimal-trailing-zeroes", MemoryCondition.STRUCTURED, 1),
    (4, "babel-strict-grouped-decimal-trailing-zeroes", MemoryCondition.NO_MEMORY, 1),
)

_EXPECTED_RUNTIME = {
    "evaluator_version": "v2",
    "safety_contract_schema": "evaluator-safety-contract-v2",
    "receipt_schema": "evaluator-v2-evaluation-receipt-v1",
    "raw_result_official": False,
    "model": "openai",
    "model_id": "gpt-5.4-mini-2026-03-17",
    "reasoning_effort": "medium",
    "reasoning_mode": "standard",
    "service_tier": "default",
    "transport_max_retries": 0,
    "max_output_tokens": 25_000,
    "token_budget_schema_version": "cumulative-split-v1",
    "max_model_calls": 180,
    "max_tool_calls": 300,
    "max_cumulative_input_tokens": 3_000_000,
    "max_cumulative_output_tokens": 350_000,
    "max_total_tokens": 3_350_000,
    "wall_clock_timeout_seconds": 3_600,
    "tool_schema_version": "v2",
    "context_policy_version": "phase-evidence-v5",
    "memory_policy_version": "fixed-d110-bundle-v1",
    "sandbox_backend": "docker",
    "marker_profile": "task-private-plus-run-secret-exact-v1",
}

_EXPECTED_TREATMENT = {
    "no_memory_selected_memory": None,
    "structured_delivery": "exact-d110-three-entry-bundle-every-request",
    "fixed_bundle_bytes": FIXED_BUNDLE_BYTES,
    "fixed_bundle_sha256": FIXED_BUNDLE_SHA256,
    "query_embedding_or_similarity_used": False,
    "threshold_or_reranking_used": False,
}

_EXPECTED_AUTHORITY = {
    "offline_source_qualification_authorized": True,
    "source_gate_materialization_authorized": True,
    "docker_or_sdk_observation_authorized": False,
    "credential_observation_or_provisioning_authorized": False,
    "provider_or_evaluator_execution_authorized": False,
    "agent_execution_authorized": False,
    "runtime_memory_injection_authorized": False,
    "exact_execution_hash_authorized": False,
    "execution_candidate_authorized": False,
    "cost_reservation_or_spend_authorized": False,
    "automatic_retry_replacement_or_resume_authorized": False,
    "memory_benefit_claim_authorized": False,
}


def _qualified_runtime_tuple_hash() -> str:
    return evaluator_v2_runtime_tuple_hash(
        provider=_EXPECTED_RUNTIME["model"],
        model_id=_EXPECTED_RUNTIME["model_id"],
        reasoning_effort=_EXPECTED_RUNTIME["reasoning_effort"],
        reasoning_mode=_EXPECTED_RUNTIME["reasoning_mode"],
        service_tier=_EXPECTED_RUNTIME["service_tier"],
        transport_max_retries=_EXPECTED_RUNTIME["transport_max_retries"],
        max_output_tokens=_EXPECTED_RUNTIME["max_output_tokens"],
        max_total_tokens=_EXPECTED_RUNTIME["max_total_tokens"],
        wall_clock_timeout_seconds=_EXPECTED_RUNTIME["wall_clock_timeout_seconds"],
        tool_schema_version=_EXPECTED_RUNTIME["tool_schema_version"],
        context_policy_version=_EXPECTED_RUNTIME["context_policy_version"],
        memory_policy_version=_EXPECTED_RUNTIME["memory_policy_version"],
        sandbox_backend=_EXPECTED_RUNTIME["sandbox_backend"],
        token_budget_schema_version=_EXPECTED_RUNTIME["token_budget_schema_version"],
        max_model_calls=_EXPECTED_RUNTIME["max_model_calls"],
        max_tool_calls=_EXPECTED_RUNTIME["max_tool_calls"],
        max_cumulative_input_tokens=_EXPECTED_RUNTIME["max_cumulative_input_tokens"],
        max_cumulative_output_tokens=_EXPECTED_RUNTIME["max_cumulative_output_tokens"],
    )


class EvaluatorV2SourceQualificationError(ContractError):
    """Raised when the offline successor qualification drifts or is malformed."""


class QualificationFileBinding(FrozenStrictModel):
    path: str
    file_bytes: int = Field(ge=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return safe_relative_path(value, field_name="qualification file path")


class QualifiedScheduleRow(FrozenStrictModel):
    order: int = Field(ge=1, le=4)
    schedule_row_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    condition: Literal["no_memory", "structured"]
    repetition: Literal[1]


class QualifiedTaskBinding(FrozenStrictModel):
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    task_version: int = Field(ge=1)
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    base_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    evaluator_image_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_marker_set_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_marker_count: int = Field(ge=1)
    contract_template_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    baseline_contract_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    hidden_check_ids_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    regression_check_ids_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    scope_check_ids_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    registered_check_specs_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class SuccessorSuiteBinding(FrozenStrictModel):
    suite_id: Literal[QUALIFICATION_ID] = QUALIFICATION_ID
    base_suite_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_tuple_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    treatment_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_binding_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    schedule_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    schedule: tuple[QualifiedScheduleRow, ...] = Field(min_length=4, max_length=4)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_content_hash(self) -> SuccessorSuiteBinding:
        if tuple(item.order for item in self.schedule) != (1, 2, 3, 4):
            raise ValueError("successor schedule is not canonically ordered")
        if len({item.schedule_row_id for item in self.schedule}) != 4:
            raise ValueError("successor schedule row identities are not unique")
        if self.schedule_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.schedule]
        ):
            raise ValueError("successor schedule hash mismatch")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("successor suite content hash mismatch")
        return self


class QualificationAuthorityBoundary(FrozenStrictModel):
    offline_source_qualification_authorized: Literal[True] = True
    source_gate_materialization_authorized: Literal[True] = True
    docker_or_sdk_observation_authorized: Literal[False] = False
    credential_observation_or_provisioning_authorized: Literal[False] = False
    provider_or_evaluator_execution_authorized: Literal[False] = False
    agent_execution_authorized: Literal[False] = False
    runtime_memory_injection_authorized: Literal[False] = False
    exact_execution_hash_authorized: Literal[False] = False
    execution_candidate_authorized: Literal[False] = False
    cost_reservation_or_spend_authorized: Literal[False] = False
    automatic_retry_replacement_or_resume_authorized: Literal[False] = False
    memory_benefit_claim_authorized: Literal[False] = False
    provider_calls_made: Literal[0] = 0
    evaluator_calls_made: Literal[0] = 0
    docker_calls_made: Literal[0] = 0
    agent_runs_made: Literal[0] = 0
    retrieval_calls_made: Literal[0] = 0
    added_model_cost_usd: Literal[0] = 0


class EvaluatorV2ACSourceQualification(FrozenStrictModel):
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    qualification_id: Literal[QUALIFICATION_ID] = QUALIFICATION_ID
    status: Literal[STATUS] = STATUS
    recorded_at: datetime
    plan: QualificationFileBinding
    base_suite: QualificationFileBinding
    base_suite_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_source_files: tuple[QualificationFileBinding, ...] = Field(min_length=1)
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_files: tuple[QualificationFileBinding, ...] = Field(min_length=1)
    validation_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_bindings: tuple[QualifiedTaskBinding, ...] = Field(min_length=2, max_length=2)
    successor_suite: SuccessorSuiteBinding
    marker_profile: Literal["task-private-plus-run-secret-exact-v1"] = (
        "task-private-plus-run-secret-exact-v1"
    )
    fixed_bundle_policy_version: Literal["fixed-d110-bundle-v1"] = FIXED_BUNDLE_POLICY_VERSION
    fixed_bundle_sha256: Literal[FIXED_BUNDLE_SHA256] = FIXED_BUNDLE_SHA256
    d110_index_version: Literal[D110_INDEX_VERSION] = D110_INDEX_VERSION
    d110_index_content_hash: Literal[D110_INDEX_CONTENT_HASH] = D110_INDEX_CONTENT_HASH
    authority: QualificationAuthorityBoundary
    next_gate: Literal["bounded-no-call-readiness"] = "bounded-no-call-readiness"
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_content_hash(self) -> EvaluatorV2ACSourceQualification:
        source_paths = tuple(item.path for item in self.evaluator_source_files)
        validation_paths = tuple(item.path for item in self.validation_files)
        task_ids = tuple(item.task_id for item in self.task_bindings)
        if source_paths != tuple(sorted(source_paths)) or len(source_paths) != len(
            set(source_paths)
        ):
            raise ValueError("evaluator source inventory is not canonical")
        if validation_paths != tuple(sorted(validation_paths)) or len(validation_paths) != len(
            set(validation_paths)
        ):
            raise ValueError("qualification validation inventory is not canonical")
        if task_ids != (
            "babel-strict-grouped-decimal-trailing-zeroes",
            "moto-query-scanned-count",
        ):
            raise ValueError("qualified task inventory differs")
        if self.evaluator_source_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.evaluator_source_files]
        ):
            raise ValueError("evaluator source fingerprint mismatch")
        if self.validation_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.validation_files]
        ):
            raise ValueError("qualification validation fingerprint mismatch")
        if self.successor_suite.evaluator_source_hash != self.evaluator_source_hash:
            raise ValueError("successor suite uses another evaluator source")
        if self.successor_suite.base_suite_hash != self.base_suite_hash:
            raise ValueError("successor suite uses another predecessor suite")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("evaluator-v2 source qualification content hash mismatch")
        return self


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EvaluatorV2SourceQualificationError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        root = selected.resolve(strict=True)
    except OSError as exc:
        raise EvaluatorV2SourceQualificationError(
            "evaluator-v2 qualification repository is unavailable"
        ) from exc
    _require(root.is_dir(), "evaluator-v2 qualification root is not a directory")
    return root


def _is_linklike(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _logical_path(root: Path, relative: Path, *, must_exist: bool) -> Path:
    safe = Path(safe_relative_path(relative.as_posix()))
    candidate = root / safe
    current = root
    for part in safe.parts:
        current = current / part
        if current.exists() and _is_linklike(current):
            raise EvaluatorV2SourceQualificationError(
                f"qualification path is link-like: {relative.as_posix()}"
            )
    try:
        resolved = candidate.resolve(strict=must_exist)
    except OSError as exc:
        raise EvaluatorV2SourceQualificationError(
            f"qualification path is unavailable: {relative.as_posix()}"
        ) from exc
    _require(
        resolved.is_relative_to(root),
        f"qualification path escapes repository: {relative.as_posix()}",
    )
    if must_exist:
        _require(resolved.is_file(), f"qualification source is not a file: {relative}")
    return resolved


def _file_binding(root: Path, relative: Path) -> QualificationFileBinding:
    selected = _logical_path(root, relative, must_exist=True)
    try:
        content = selected.read_bytes()
    except OSError as exc:
        raise EvaluatorV2SourceQualificationError(
            f"qualification source cannot be read: {relative.as_posix()}"
        ) from exc
    return QualificationFileBinding(
        path=relative.as_posix(),
        file_bytes=len(content),
        file_sha256=sha256_bytes(content),
    )


def _bindings(root: Path, paths: Sequence[Path]) -> tuple[QualificationFileBinding, ...]:
    values = tuple(_file_binding(root, item) for item in paths)
    _require(
        tuple(item.path for item in values) == tuple(sorted(item.path for item in values)),
        "qualification inventory is not ordered",
    )
    return values


def evaluator_v2_task_private_markers(package: TaskPackage) -> tuple[bytes, ...]:
    """Return the exact task-private marker set without persisting marker values."""

    package = TaskPackage.model_validate(package.model_dump(mode="json"))
    public_text = canonical_json(package.public.model_dump(mode="json")).lower()
    candidates = {
        "private.yaml",
        "reference.patch",
        ".patchloop-hidden",
        package.private.reference_patch.path,
        package.private.reference_patch.sha256,
        *(check.id for check in package.private.hidden_checks),
        *(artifact.path for artifact in package.private.hidden_artifacts),
        *(artifact.sha256 for artifact in package.private.hidden_artifacts),
    }
    markers = tuple(
        sorted(
            {
                item.encode("utf-8")
                for item in candidates
                if item and len(item.encode("utf-8")) >= 8 and item.lower() not in public_text
            }
        )
    )
    _require(bool(markers), "qualified task has no private marker projection")
    evaluator_v2_marker_set_hash(markers)
    return markers


def _contract_id(task_id: str) -> str:
    return f"ac_evaluator_v2_{task_id.replace('-', '_')}"


def _contract_template_hash(contract: EvaluatorSafetyContract) -> str:
    payload = contract.model_dump(mode="json", exclude={"content_hash"})
    requirements = payload["requirements"]
    for requirement in requirements:
        if requirement["control"] == "secret":
            requirement["policy_input_hash"] = "run-bound-private-marker-set"
            requirement["policy_input_count"] = "run-bound-private-marker-count"
    return sha256_json(payload)


def _task_binding(
    package: TaskPackage,
    *,
    evaluator_source_hash: str,
) -> QualifiedTaskBinding:
    markers = evaluator_v2_task_private_markers(package)
    contract = build_evaluator_safety_contract_v2(
        package=package,
        tool_schemas=TOOL_SCHEMAS_V2,
        private_markers=markers,
        contract_id=_contract_id(package.public.task_id),
    )
    binding = build_evaluator_contract_binding(
        contract,
        package,
        evaluator_source_hash=evaluator_source_hash,
    )
    environment = package.environment
    _require(environment is not None, "qualified A/C task has no Docker environment")
    return QualifiedTaskBinding(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        private_spec_hash=package.private_spec_hash,
        base_commit=package.public.repository.base_commit,
        evaluator_image_digest=environment.image_digest,
        private_marker_set_hash=evaluator_v2_marker_set_hash(markers),
        private_marker_count=len(markers),
        contract_template_hash=_contract_template_hash(contract),
        baseline_contract_hash=contract.content_hash,
        hidden_check_ids_hash=binding.hidden_check_ids_hash,
        regression_check_ids_hash=binding.regression_check_ids_hash,
        scope_check_ids_hash=binding.scope_check_ids_hash,
        registered_check_specs_hash=binding.registered_check_specs_hash,
    )


def _load_plan(root: Path) -> dict[str, Any]:
    selected = _logical_path(root, PLAN_PATH, must_exist=True)
    try:
        value = yaml.safe_load(selected.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise EvaluatorV2SourceQualificationError(
            "evaluator-v2 successor plan is unreadable"
        ) from exc
    _require(isinstance(value, dict), "evaluator-v2 successor plan is not a mapping")
    expected_keys = {
        "schema_version",
        "plan_id",
        "status",
        "predecessor_plan",
        "base_suite",
        "successor_suite",
        "runtime",
        "treatment",
        "authority",
        "next_gate",
    }
    _require(set(value) == expected_keys, "evaluator-v2 successor plan fields differ")
    _require(
        value["schema_version"] == "ac-structured-pilot-plan-v7"
        and value["plan_id"]
        == "ac-structured-dev-validation-evaluator-v2-split-budget-20260814-v6"
        and value["status"] == "offline-evaluator-v2-source-qualification"
        and value["predecessor_plan"] == "experiments/ac-structured-pilot-v6.plan.yaml"
        and value["base_suite"] == BASE_SUITE_PATH.as_posix(),
        "evaluator-v2 successor plan identity differs",
    )
    successor = value["successor_suite"]
    _require(isinstance(successor, dict), "successor suite plan is not a mapping")
    expected_schedule = [
        {
            "order": order,
            "task_id": task_id,
            "condition": condition.value,
            "repetition": repetition,
        }
        for order, task_id, condition, repetition in _EXPECTED_SCHEDULE
    ]
    _require(
        successor
        == {
            "suite_id": QUALIFICATION_ID,
            "purpose": "development-validation-ac-readiness",
            "conditions": ["no_memory", "structured"],
            "repetitions": 1,
            "expected_runs": 4,
            "schedule": expected_schedule,
            "replacement_or_retry_allowed": False,
        },
        "successor suite plan differs",
    )
    _require(value["runtime"] == _EXPECTED_RUNTIME, "successor runtime tuple differs")
    _require(value["treatment"] == _EXPECTED_TREATMENT, "successor treatment differs")
    _require(value["authority"] == _EXPECTED_AUTHORITY, "successor authority differs")
    _require(
        value["next_gate"]
        == {
            "action": "run-bounded-no-call-readiness",
            "maximum_attempts": 3,
            "per_attempt_versioned_successor_required": False,
            "requires_separate_paid_execution_approval": True,
            "does_not_authorize_execution": True,
        },
        "successor next gate differs",
    )
    return value


def _load_base_suite(root: Path) -> tuple[Any, str]:
    from patchloop.contracts import (
        AC_FIXED_BUNDLE_CORRECTED_EXPERIMENT_ID,
        AC_FIXED_BUNDLE_SPLIT_BUDGET_EXPERIMENT_ID,
    )
    from patchloop.evals.runner import (
        AC_FIXED_BUNDLE_SPLIT_TOKEN_COST_POLICY,
        GPT54_MINI_AC_SPLIT_TOKEN_BUDGET,
        _is_ac_fixed_bundle_readiness_profile,
        _suite_hash,
        load_suite,
    )

    selected = _logical_path(root, BASE_SUITE_PATH, must_exist=True)
    try:
        suite = load_suite(selected)
        predecessor = load_suite(_logical_path(root, FAST_PREDECESSOR_SUITE_PATH, must_exist=True))
    except (OSError, ValidationError, ValueError) as exc:
        raise EvaluatorV2SourceQualificationError("predecessor A/C suite is unavailable") from exc
    suite_payload = suite.model_dump(mode="json")
    predecessor_payload = predecessor.model_dump(mode="json")
    for field in (
        "experiment_id",
        "budget",
        "campaign_cost_policy",
        "estimated_cost_usd",
        "cost_limit_usd",
    ):
        suite_payload.pop(field, None)
        predecessor_payload.pop(field, None)
    _require(
        suite.experiment_id == AC_FIXED_BUNDLE_SPLIT_BUDGET_EXPERIMENT_ID
        and predecessor.experiment_id == AC_FIXED_BUNDLE_CORRECTED_EXPERIMENT_ID
        and suite_payload == predecessor_payload
        and suite.budget == GPT54_MINI_AC_SPLIT_TOKEN_BUDGET
        and suite.campaign_cost_policy is not None
        and suite.campaign_cost_policy.model_dump(mode="json")
        == AC_FIXED_BUNDLE_SPLIT_TOKEN_COST_POLICY
        and suite.estimated_cost_usd == 15.3
        and suite.cost_limit_usd == 18.0
        and _is_ac_fixed_bundle_readiness_profile(suite)
        and suite.live_cost_approved is False
        and suite.approved_execution_hash is None
        and suite.pricing_verified_at == datetime(2026, 8, 13, 12, 5, 26, tzinfo=UTC),
        "base A/C suite is not the exact split-token successor source",
    )
    return suite, _suite_hash(suite)


def _schedule_rows() -> tuple[QualifiedScheduleRow, ...]:
    rows = []
    for order, task_id, condition, repetition in _EXPECTED_SCHEDULE:
        identity = {
            "suite_id": QUALIFICATION_ID,
            "order": order,
            "task_id": task_id,
            "condition": condition.value,
            "repetition": repetition,
        }
        rows.append(
            QualifiedScheduleRow(
                order=order,
                schedule_row_id=sha256_json(identity),
                task_id=task_id,
                condition=condition.value,
                repetition=repetition,
            )
        )
    return tuple(rows)


def _successor_suite(
    *,
    base_suite_hash: str,
    evaluator_source_hash: str,
    task_bindings: tuple[QualifiedTaskBinding, ...],
) -> SuccessorSuiteBinding:
    schedule = _schedule_rows()
    body = {
        "suite_id": QUALIFICATION_ID,
        "base_suite_hash": base_suite_hash,
        "evaluator_source_hash": evaluator_source_hash,
        "tool_schema_hash": sha256_json(TOOL_SCHEMAS_V2),
        "runtime_tuple_hash": _qualified_runtime_tuple_hash(),
        "treatment_hash": sha256_json(_EXPECTED_TREATMENT),
        "task_binding_hash": sha256_json([item.model_dump(mode="json") for item in task_bindings]),
        "schedule_hash": sha256_json([item.model_dump(mode="json") for item in schedule]),
        "schedule": [item.model_dump(mode="json") for item in schedule],
    }
    return SuccessorSuiteBinding(**body, content_hash=sha256_json(body))


def _build_candidate(
    root: Path,
    *,
    recorded_at: datetime,
) -> EvaluatorV2ACSourceQualification:
    _load_plan(root)
    _base_suite, base_suite_hash = _load_base_suite(root)
    structured = build_fixed_memory_delivery(
        condition=MemoryCondition.STRUCTURED,
        token_budget=2_000,
        repository=root,
    )
    no_memory = build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        token_budget=2_000,
        repository=root,
    )
    _require(
        structured.evidence.entry_count == 3
        and structured.evidence.bundle_bytes == FIXED_BUNDLE_BYTES
        and structured.evidence.bundle_sha256 == FIXED_BUNDLE_SHA256
        and structured.evidence.index_version == D110_INDEX_VERSION
        and structured.evidence.index_content_hash == D110_INDEX_CONTENT_HASH
        and no_memory.text == ""
        and no_memory.evidence.selected_memory_present is False,
        "fixed A/C treatment identity differs",
    )
    source_files = _bindings(root, SOURCE_PATHS)
    validation_files = _bindings(root, VALIDATION_PATHS)
    evaluator_source_hash = sha256_json([item.model_dump(mode="json") for item in source_files])
    packages = tuple(load_task_package(root / path) for path in TASK_PATHS)
    task_bindings = tuple(
        sorted(
            (
                _task_binding(package, evaluator_source_hash=evaluator_source_hash)
                for package in packages
            ),
            key=lambda item: item.task_id,
        )
    )
    successor_suite = _successor_suite(
        base_suite_hash=base_suite_hash,
        evaluator_source_hash=evaluator_source_hash,
        task_bindings=task_bindings,
    )
    body = {
        "schema_version": SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": STATUS,
        "recorded_at": recorded_at,
        "plan": _file_binding(root, PLAN_PATH).model_dump(mode="json"),
        "base_suite": _file_binding(root, BASE_SUITE_PATH).model_dump(mode="json"),
        "base_suite_hash": base_suite_hash,
        "evaluator_source_files": [item.model_dump(mode="json") for item in source_files],
        "evaluator_source_hash": evaluator_source_hash,
        "validation_files": [item.model_dump(mode="json") for item in validation_files],
        "validation_hash": sha256_json([item.model_dump(mode="json") for item in validation_files]),
        "task_bindings": [item.model_dump(mode="json") for item in task_bindings],
        "successor_suite": successor_suite.model_dump(mode="json"),
        "marker_profile": "task-private-plus-run-secret-exact-v1",
        "fixed_bundle_policy_version": FIXED_BUNDLE_POLICY_VERSION,
        "fixed_bundle_sha256": FIXED_BUNDLE_SHA256,
        "d110_index_version": D110_INDEX_VERSION,
        "d110_index_content_hash": D110_INDEX_CONTENT_HASH,
        "authority": QualificationAuthorityBoundary().model_dump(mode="json"),
        "next_gate": "bounded-no-call-readiness",
    }
    json_body = {
        **body,
        "recorded_at": recorded_at.isoformat().replace("+00:00", "Z"),
    }
    return EvaluatorV2ACSourceQualification(
        **body,
        content_hash=sha256_json(json_body),
    )


def _canonical_bytes(value: EvaluatorV2ACSourceQualification) -> bytes:
    return (value.model_dump_json(indent=2) + "\n").encode("utf-8")


def _load_validated(
    root: Path,
) -> tuple[EvaluatorV2ACSourceQualification, bytes]:
    selected = _logical_path(root, OUTPUT_PATH, must_exist=True)
    try:
        raw = selected.read_bytes()
        payload = EvaluatorV2ACSourceQualification.model_validate_json(raw)
    except (OSError, UnicodeDecodeError, ValidationError) as exc:
        raise EvaluatorV2SourceQualificationError(
            "evaluator-v2 source qualification artifact is invalid"
        ) from exc
    _require(raw == _canonical_bytes(payload), "source qualification bytes are not canonical")
    expected = _build_candidate(root, recorded_at=payload.recorded_at)
    _require(payload == expected, "evaluator-v2 source qualification has drifted")
    return payload, raw


def _summary(
    payload: EvaluatorV2ACSourceQualification,
    raw: bytes,
) -> dict[str, Any]:
    return {
        "status": payload.status,
        "qualification_id": payload.qualification_id,
        "source_qualification_hash": payload.content_hash,
        "evaluator_source_hash": payload.evaluator_source_hash,
        "successor_suite_hash": payload.successor_suite.content_hash,
        "base_suite_hash": payload.base_suite_hash,
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "execution_authorized": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
        "agent_runs_made": 0,
    }


def validate_evaluator_v2_ac_source_qualification(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Validate the append-only artifact against exact current local source."""

    root = _repo_root(repository)
    payload, raw = _load_validated(root)
    return _summary(payload, raw)


def _write_new(
    root: Path,
    payload: EvaluatorV2ACSourceQualification,
) -> bytes:
    selected = _logical_path(root, OUTPUT_PATH, must_exist=False)
    _require(not selected.exists(), "evaluator-v2 source qualification already exists")
    content = _canonical_bytes(payload)
    try:
        with selected.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        observed = selected.read_bytes()
    except OSError as exc:
        raise EvaluatorV2SourceQualificationError(
            "evaluator-v2 source qualification cannot be created"
        ) from exc
    _require(observed == content, "source qualification changed after creation")
    return observed


def run_evaluator_v2_ac_source_qualification(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Materialize once, or validate the exact existing offline artifact."""

    root = _repo_root(repository)
    output = _logical_path(root, OUTPUT_PATH, must_exist=False)
    if output.exists():
        return validate_evaluator_v2_ac_source_qualification(repository=root)
    payload = _build_candidate(root, recorded_at=datetime.now(UTC))
    raw = _write_new(root, payload)
    validated, observed = _load_validated(root)
    _require(raw == observed and payload == validated, "source qualification reread differs")
    return _summary(validated, observed)


def load_evaluator_v2_ac_qualification_authority(
    task_dir: str | Path,
    *,
    runtime_secret_markers: Sequence[bytes] = (),
    repository: str | Path | None = None,
):
    """Build a task authority from the validated source gate.

    This factory does not grant run authority.  A caller must still supply the
    resulting object together with the separately gated manifest/execution
    authority.  The qualified OpenAI runtime requires an explicit run-bound
    secret marker; this offline module never reads a credential or environment
    value itself.
    """

    from patchloop.verifier.receipt import EvaluatorV2QualificationAuthority

    root = _repo_root(repository)
    payload, _raw = _load_validated(root)
    selected = Path(task_dir)
    package = load_task_package(selected.parent if selected.is_file() else selected)
    expected = next(
        (item for item in payload.task_bindings if item.task_id == package.public.task_id),
        None,
    )
    _require(expected is not None, "task is outside the qualified successor suite")
    observed = _task_binding(package, evaluator_source_hash=payload.evaluator_source_hash)
    _require(observed == expected, "qualified task package or contract template drifted")
    base_markers = evaluator_v2_task_private_markers(package)
    secrets: list[bytes] = []
    for marker in runtime_secret_markers:
        _require(type(marker) is bytes and bool(marker), "runtime secret marker is invalid")
        _require(len(marker) <= 16_384, "runtime secret marker is unbounded")
        secrets.append(marker)
    _require(len(secrets) == len(set(secrets)), "runtime secret markers are duplicated")
    _require(
        not set(secrets).intersection(base_markers),
        "runtime secret marker duplicates a task-private marker",
    )
    _require(bool(secrets), "OpenAI evaluator-v2 authority requires a run-bound secret marker")
    markers = tuple(sorted((*base_markers, *secrets)))
    contract = build_evaluator_safety_contract_v2(
        package=package,
        tool_schemas=TOOL_SCHEMAS_V2,
        private_markers=markers,
        contract_id=_contract_id(package.public.task_id),
    )
    _require(
        _contract_template_hash(contract) == expected.contract_template_hash,
        "runtime marker expansion changed the qualified contract template",
    )
    runtime = EvaluatorV2RuntimeAuthority(
        safety_contract=contract,
        evaluator_source_hash=payload.evaluator_source_hash,
        tool_schemas=tuple(TOOL_SCHEMAS_V2),
        private_markers=markers,
    )
    return EvaluatorV2QualificationAuthority(
        runtime=runtime,
        suite_hash=payload.successor_suite.content_hash,
        source_qualification_hash=payload.content_hash,
        runtime_tuple_hash=payload.successor_suite.runtime_tuple_hash,
    )


def validate_evaluator_v2_ac_paid_authority(
    manifest: RunManifest,
    authority: Any,
    qualification: dict[str, Any],
    *,
    repository: str | Path | None = None,
):
    """Bind a paid v2 manifest and authority to the exact qualified artifact."""

    from patchloop.contracts import AC_FIXED_BUNDLE_SPLIT_BUDGET_EXPERIMENT_ID
    from patchloop.verifier.receipt import (
        EvaluatorV2QualificationAuthority,
        validate_evaluator_v2_manifest_authority,
    )

    root = _repo_root(repository)
    payload, _raw = _load_validated(root)
    expected_qualification = {
        "source_qualification_hash": payload.content_hash,
        "evaluator_source_hash": payload.evaluator_source_hash,
        "successor_suite_hash": payload.successor_suite.content_hash,
        "base_suite_hash": payload.base_suite_hash,
        "base_suite_matches": True,
    }
    _require(
        type(qualification) is dict and qualification == expected_qualification,
        "paid evaluator-v2 qualification differs from the source artifact",
    )
    _require(
        isinstance(authority, EvaluatorV2QualificationAuthority),
        "paid evaluator-v2 authority has the wrong type",
    )
    checked = validate_evaluator_v2_manifest_authority(manifest, authority)
    binding = manifest.evaluator_contract
    experiment = manifest.experiment
    expected_task = next(
        (item for item in payload.task_bindings if item.task_id == manifest.task_id),
        None,
    )
    package_path = next(
        (path for path in TASK_PATHS if path.name == manifest.task_id),
        None,
    )
    _require(
        binding is not None and experiment is not None and expected_task is not None,
        "paid evaluator-v2 manifest is outside the qualified task set",
    )
    _require(package_path is not None, "paid evaluator-v2 task package is unavailable")
    package = load_task_package(root / package_path)
    base_markers = evaluator_v2_task_private_markers(package)
    runtime_markers = tuple(checked.runtime.private_markers)
    _require(
        runtime_markers == tuple(sorted(runtime_markers))
        and len(runtime_markers) == len(set(runtime_markers))
        and set(base_markers).issubset(runtime_markers)
        and len(runtime_markers) > len(base_markers),
        "paid evaluator-v2 authority lacks its task-private or run-secret marker",
    )
    _require(
        manifest.schema_version == "run-manifest-v2"
        and experiment.experiment_id == AC_FIXED_BUNDLE_SPLIT_BUDGET_EXPERIMENT_ID
        and experiment.suite_hash == payload.successor_suite.content_hash
        and checked.suite_hash == payload.successor_suite.content_hash
        and checked.source_qualification_hash == payload.content_hash
        and checked.runtime_tuple_hash == payload.successor_suite.runtime_tuple_hash
        and checked.runtime.evaluator_source_hash == payload.evaluator_source_hash
        and sha256_json(list(checked.runtime.tool_schemas))
        == payload.successor_suite.tool_schema_hash
        and canonical_json(list(checked.runtime.tool_schemas)) == canonical_json(TOOL_SCHEMAS_V2)
        and _contract_template_hash(checked.runtime.safety_contract)
        == expected_task.contract_template_hash
        and manifest.task_version == expected_task.task_version
        and manifest.public_spec_hash == expected_task.public_spec_hash
        and manifest.private_spec_hash == expected_task.private_spec_hash
        and manifest.base_commit == expected_task.base_commit
        and manifest.evaluator_image_digest == expected_task.evaluator_image_digest
        and binding.task_id == expected_task.task_id
        and binding.task_version == expected_task.task_version
        and binding.public_spec_hash == expected_task.public_spec_hash
        and binding.private_spec_hash == expected_task.private_spec_hash
        and binding.evaluator_source_hash == payload.evaluator_source_hash
        and binding.hidden_check_ids_hash == expected_task.hidden_check_ids_hash
        and binding.regression_check_ids_hash == expected_task.regression_check_ids_hash
        and binding.scope_check_ids_hash == expected_task.scope_check_ids_hash
        and binding.registered_check_specs_hash == expected_task.registered_check_specs_hash,
        "paid evaluator-v2 authority differs from the qualified source or task",
    )
    return checked


__all__ = [
    "BASE_SUITE_PATH",
    "EvaluatorV2ACSourceQualification",
    "EvaluatorV2SourceQualificationError",
    "FAST_PREDECESSOR_SUITE_PATH",
    "OUTPUT_PATH",
    "PLAN_PATH",
    "QUALIFICATION_ID",
    "SCHEMA_VERSION",
    "SOURCE_PATHS",
    "STATUS",
    "TASK_PATHS",
    "VALIDATION_PATHS",
    "evaluator_v2_task_private_markers",
    "load_evaluator_v2_ac_qualification_authority",
    "run_evaluator_v2_ac_source_qualification",
    "validate_evaluator_v2_ac_source_qualification",
    "validate_evaluator_v2_ac_paid_authority",
]
