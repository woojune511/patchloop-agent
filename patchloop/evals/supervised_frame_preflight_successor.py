"""Offline-only v17 supervisor correction for the consumed v16 frame error.

V16 remains immutable and cannot retry.  V17 binds its exact terminal and
separates the result writer from the diagnostic workload: a stdlib-only
supervisor owns the parent stdout, while one worker starts with stdout/stderr at
the OS null device and returns a typed message over an anonymous pipe.  This
module exposes injected observers only; source validation performs no Docker,
dotenv, SDK, network, provider, or credential observation.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from patchloop.contracts import FrozenStrictModel
from patchloop.errors import ContractError
from patchloop.evals import dedicated_frame_activation_successor as v16
from patchloop.evals import dedicated_frame_preflight_successor as v15
from patchloop.util import sha256_bytes
from scripts import run_sanitized_sdk_bootstrap_supervised_frame_child as child_script

v13 = v15.v13
v10 = v15.v10
v9 = v15.v9

CONTRACT_SCHEMA_VERSION = "supervised-frame-preflight-successor-contract-v17"
CONTRACT_VERSION = "ac-evaluator-v2-supervised-frame-preflight-successor-v17"
CONTRACT_PATH = Path(
    "experiments/evaluator-v2-supervised-frame-preflight-successor-v17.contract.json"
)
RUNTIME_PATH = Path("patchloop/evals/supervised_frame_preflight_successor.py")
CHILD_PATH = Path("scripts/run_sanitized_sdk_bootstrap_supervised_frame_child.py")
BUILD_SCRIPT_PATH = Path("scripts/build_supervised_frame_preflight_successor.py")
TEST_PATH = Path("tests/test_supervised_frame_preflight_successor.py")

SOURCE_PARENT_COMMIT = "3c661b2a7db55e36574734a4e0bf5bec8b530f72"
V16_EVIDENCE_COMMIT = "30c254d03e886e998b47e32d08488f724df3109f"
QUALIFICATION_SCHEMA_VERSION = "supervised-frame-preflight-source-qualification-v17"
QUALIFICATION_ID = "ac-evaluator-v2-supervised-frame-preflight-source-20260813-r1"
QUALIFICATION_STATUS = "OFFLINE_V17_SUPERVISED_FRAME_SOURCE_QUALIFIED_ACTIVATION_CLOSED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-supervised-frame-preflight-v17-source-qualification.json"
)
NEXT_GATE = "new-versioned-state-and-activation-wrapper-required"
APPROVED_RUNTIME = (
    "patchloop.evals.supervised_frame_preflight_successor.run_parent_preflight_injected"
)
APPROVED_SCOPES = (
    *v15.APPROVED_SCOPES,
    "supervisor-worker-anonymous-pipe-result-framing",
)
CHILD_FLAGS = child_script.CHILD_FLAGS
FIXED_CHILD_ENVIRONMENT = child_script.FIXED_WORKER_ENVIRONMENT
OUTER_CHILD_TIMEOUT_SECONDS = v15.CHILD_TIMEOUT_SECONDS
WORKER_TIMEOUT_SECONDS = child_script.WORKER_TIMEOUT_SECONDS
CHILD_OUTPUT_LIMIT = child_script.WORKER_OUTPUT_LIMIT

SOURCE_ADDED_PATHS = tuple(
    sorted(
        path.as_posix()
        for path in (CONTRACT_PATH, RUNTIME_PATH, CHILD_PATH, BUILD_SCRIPT_PATH, TEST_PATH)
    )
)
SOURCE_FILES = tuple(
    sorted(
        (
            CONTRACT_PATH,
            RUNTIME_PATH,
            CHILD_PATH,
            BUILD_SCRIPT_PATH,
            TEST_PATH,
            v16.CONTRACT_PATH,
            v16.RUNTIME_PATH,
            v16.QUALIFICATION_PATH,
            v16.TERMINAL_PATH,
            v15.CONTRACT_PATH,
            v15.RUNTIME_PATH,
            v15.CHILD_PATH,
            v9.DIAGNOSTIC_CHILD_PATH,
            v9.RUNTIME_PATH,
        ),
        key=lambda path: path.as_posix(),
    )
)


class SupervisedFrameSuccessorError(ContractError):
    """The source-only v17 successor failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SupervisedFrameSuccessorError(message)


class SupervisorCode(StrEnum):
    SUPERVISOR_BINDING_ERROR = "supervisor_binding_error"
    WORKER_LAUNCH_ERROR = "worker_launch_error"
    WORKER_NONZERO_EXIT = "worker_nonzero_exit"
    WORKER_RESULT_LIMIT = "worker_result_limit"
    WORKER_RESULT_INVALID = "worker_result_invalid"
    DIAGNOSTIC_WRAPPER_IMPORT_ERROR = "diagnostic_wrapper_import_error"
    DIAGNOSTIC_EXECUTION_ERROR = "diagnostic_execution_error"
    DIAGNOSTIC_RESULT_INVALID = "diagnostic_result_invalid"
    WORKER_INTERNAL_ERROR = "worker_internal_error"
    SUPERVISOR_INTERNAL_ERROR = "supervisor_internal_error"
    SUPERVISED_OUTPUT_INVALID = "supervised_output_invalid"


class SupervisorActivity(FrozenStrictModel):
    worker_launch_attempt_count: int = Field(ge=0, le=1)
    worker_process_return_count: int = Field(ge=0, le=1)
    worker_result_message_count: int = Field(ge=0, le=1)
    diagnostic_invocation_count: int = Field(ge=0, le=1)
    typed_validation_count: int = Field(ge=0, le=1)
    worker_stdout_suppressed_from_process_start_count: int = Field(ge=0, le=1)
    worker_stderr_suppressed_from_process_start_count: int = Field(ge=0, le=1)
    raw_workload_output_return_count: Literal[0] = 0
    exception_message_type_repr_or_traceback_return_count: Literal[0] = 0
    credential_value_return_hash_prefix_or_length_count: Literal[0] = 0
    activity_accounting_complete: bool
    unknown_workload_activity_possible: bool

    @model_validator(mode="after")
    def validate_semantics(self) -> SupervisorActivity:
        if self.activity_accounting_complete == self.unknown_workload_activity_possible:
            raise ValueError("v17 supervisor accounting flags differ")
        if self.worker_process_return_count > self.worker_launch_attempt_count:
            raise ValueError("v17 worker returns exceed launches")
        if self.worker_result_message_count > self.worker_process_return_count:
            raise ValueError("v17 worker messages exceed returns")
        if (
            self.worker_stdout_suppressed_from_process_start_count
            != self.worker_process_return_count
            or self.worker_stderr_suppressed_from_process_start_count
            != self.worker_process_return_count
        ):
            raise ValueError("v17 worker stream suppression projection differs")
        if self.typed_validation_count > self.diagnostic_invocation_count:
            raise ValueError("v17 typed validation exceeds invocation")
        return self


class SupervisedFrameEnvelope(FrozenStrictModel):
    schema_version: Literal[
        "sanitized-sdk-bootstrap-supervised-frame-envelope-v1"
    ] = child_script.SCHEMA_VERSION
    child: v13.v7.IsolatedDiagnosticChild | None = None
    code: SupervisorCode | None = None
    activity: SupervisorActivity
    raw_output_returned: Literal[False] = False
    exception_message_type_repr_or_traceback_returned: Literal[False] = False
    credential_value_hash_prefix_or_length_returned: Literal[False] = False

    @model_validator(mode="after")
    def validate_semantics(self) -> SupervisedFrameEnvelope:
        if (self.child is None) == (self.code is None):
            raise ValueError("v17 envelope must contain exactly child or code")
        activity = self.activity
        if self.child is not None:
            if (
                activity.worker_launch_attempt_count != 1
                or activity.worker_process_return_count != 1
                or activity.worker_result_message_count != 1
                or activity.diagnostic_invocation_count != 1
                or activity.typed_validation_count != 1
                or not activity.activity_accounting_complete
            ):
                raise ValueError("v17 valid child accounting differs")
            return self
        if self.code == SupervisorCode.SUPERVISED_OUTPUT_INVALID:
            raise ValueError("v17 outer-parse code cannot be self-reported")
        if self.code == SupervisorCode.SUPERVISOR_BINDING_ERROR:
            if (
                activity.worker_launch_attempt_count != 0
                or activity.worker_process_return_count != 0
                or activity.worker_result_message_count != 0
                or not activity.activity_accounting_complete
            ):
                raise ValueError("v17 binding error accounting differs")
        elif self.code == SupervisorCode.DIAGNOSTIC_WRAPPER_IMPORT_ERROR:
            if (
                activity.worker_launch_attempt_count != 1
                or activity.worker_process_return_count != 1
                or activity.worker_result_message_count != 1
                or activity.diagnostic_invocation_count != 0
                or activity.typed_validation_count != 0
                or not activity.activity_accounting_complete
            ):
                raise ValueError("v17 import error accounting differs")
        else:
            if activity.activity_accounting_complete:
                raise ValueError("v17 post-launch error must be incomplete")
            expected = {
                SupervisorCode.DIAGNOSTIC_EXECUTION_ERROR: (1, 0),
                SupervisorCode.DIAGNOSTIC_RESULT_INVALID: (1, 1),
                SupervisorCode.WORKER_INTERNAL_ERROR: (0, 0),
                SupervisorCode.SUPERVISOR_INTERNAL_ERROR: (0, 0),
                SupervisorCode.WORKER_LAUNCH_ERROR: (0, 0),
                SupervisorCode.WORKER_NONZERO_EXIT: (0, 0),
                SupervisorCode.WORKER_RESULT_LIMIT: (0, 0),
                SupervisorCode.WORKER_RESULT_INVALID: (0, 0),
            }[self.code]
            if (
                activity.diagnostic_invocation_count,
                activity.typed_validation_count,
            ) != expected:
                raise ValueError("v17 error stage accounting differs")
        return self


class SupervisedChildExecution(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-supervised-child-execution-v17"] = (
        "sanitized-sdk-bootstrap-supervised-child-execution-v17"
    )
    base: v9.ParentChildExecution
    supervisor_code: SupervisorCode | None = None
    envelope_received: bool
    worker_launch_attempt_count: int | None = Field(default=None, ge=0, le=1)
    worker_process_return_count: int | None = Field(default=None, ge=0, le=1)
    worker_result_message_count: int | None = Field(default=None, ge=0, le=1)
    raw_supervisor_or_worker_output_persisted: Literal[False] = False
    activity_accounting_complete: bool
    unknown_workload_activity_possible: bool

    @model_validator(mode="after")
    def validate_semantics(self) -> SupervisedChildExecution:
        if self.activity_accounting_complete == self.unknown_workload_activity_possible:
            raise ValueError("v17 execution accounting flags differ")
        counts = (
            self.worker_launch_attempt_count,
            self.worker_process_return_count,
            self.worker_result_message_count,
        )
        if self.base.child is not None:
            if (
                self.supervisor_code is not None
                or not self.envelope_received
                or counts != (1, 1, 1)
                or not self.activity_accounting_complete
            ):
                raise ValueError("v17 valid supervised execution differs")
        elif self.supervisor_code is not None:
            if self.base.code != v9.ParentExecutionCode.CHILD_OUTPUT_INVALID:
                raise ValueError("v17 supervisor failure base differs")
            if self.envelope_received:
                if any(value is None for value in counts):
                    raise ValueError("v17 received envelope lacks worker counts")
            elif (
                self.supervisor_code != SupervisorCode.SUPERVISED_OUTPUT_INVALID
                or any(value is not None for value in counts)
                or self.activity_accounting_complete
            ):
                raise ValueError("v17 invalid outer envelope projection differs")
        elif self.envelope_received or any(value is not None for value in counts):
            raise ValueError("v17 inherited parent error has supervisor evidence")
        return self


class SupervisedParentObservation(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-supervised-parent-observation-v17"] = (
        "sanitized-sdk-bootstrap-supervised-parent-observation-v17"
    )
    base: v9.ParentObservation
    supervised_child_execution: SupervisedChildExecution | None = None
    activity_accounting_complete: bool
    unknown_post_marker_activity_possible: bool
    passed: bool

    @model_validator(mode="after")
    def validate_semantics(self) -> SupervisedParentObservation:
        child = self.base.child_execution
        if child is None:
            if self.supervised_child_execution is not None:
                raise ValueError("v17 unexpected supervised child")
            expected_complete = self.base.activity_accounting_complete
            expected_unknown = self.base.unknown_post_marker_activity_possible
        else:
            if (
                self.supervised_child_execution is None
                or self.supervised_child_execution.base != child
            ):
                raise ValueError("v17 supervised child projection differs")
            expected_complete = (
                self.base.activity_accounting_complete
                and self.supervised_child_execution.activity_accounting_complete
            )
            expected_unknown = (
                self.base.unknown_post_marker_activity_possible
                or self.supervised_child_execution.unknown_workload_activity_possible
            )
        if (
            self.activity_accounting_complete != expected_complete
            or self.unknown_post_marker_activity_possible != expected_unknown
            or self.passed != self.base.passed
        ):
            raise ValueError("v17 parent accounting differs")
        return self


class V16FailureBinding(FrozenStrictModel):
    evidence_commit: Literal[
        "30c254d03e886e998b47e32d08488f724df3109f"
    ] = V16_EVIDENCE_COMMIT
    contract_id: Literal[
        "ncpcontract_e5ab4405de4e30a97c3524d157fbf74ad5757f61809c161bee07ede2dfc7564c"
    ]
    source_qualification_hash: Literal[
        "sha256:f2b3e1483bf67d00ea2b568986971454b7efeef1e0088f51fc1329077bffa091"
    ]
    terminal_id: Literal[
        "ncpterminal_db06f32f6223cdd227eb36b503b34ad6fc0eda817e563b21db9b896f8737c907"
    ]
    terminal_content_hash: Literal[
        "sha256:db06f32f6223cdd227eb36b503b34ad6fc0eda817e563b21db9b896f8737c907"
    ]
    terminal_file_sha256: Literal[
        "sha256:84b6c0d32a67d9d136b6fce98393e46a17f2321a28dc5b8562d6550b09f24ab5"
    ]
    outcome: Literal["error"] = "error"
    reason: Literal["child_checker_error"] = "child_checker_error"
    base_child_code: Literal["child_output_invalid"] = "child_output_invalid"
    frame_code: Literal["framed_output_invalid"] = "framed_output_invalid"
    envelope_received: Literal[False] = False
    docker_cli_command_count: Literal[8] = 8
    child_launch_attempt_count: Literal[1] = 1
    child_process_return_count: Literal[1] = 1
    network_call_count: Literal[0] = 0
    provider_evaluator_agent_call_count: Literal[0] = 0
    docker_mutation_count: Literal[0] = 0
    credential_value_metadata_count: Literal[0] = 0
    raw_child_output_persisted: Literal[False] = False
    activity_accounting_complete: Literal[False] = False
    unknown_post_marker_activity_possible: Literal[True] = True
    retry_or_resume_allowed: Literal[False] = False
    causal_detail_available: Literal[False] = False


class SupervisedRuntimeProfile(FrozenStrictModel):
    entrypoint: Literal[
        "patchloop.evals.supervised_frame_preflight_successor.run_parent_preflight_injected"
    ] = APPROVED_RUNTIME
    supervisor_worker_path: Literal[
        "scripts/run_sanitized_sdk_bootstrap_supervised_frame_child.py"
    ] = CHILD_PATH.as_posix()
    supervisor_worker_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    diagnostic_child_path: Literal["scripts/run_sanitized_sdk_diagnostic_child.py"] = (
        v9.DIAGNOSTIC_CHILD_PATH.as_posix()
    )
    diagnostic_child_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    typed_parent_runtime_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v15_contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    v15_contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    child_flags: tuple[str, ...] = CHILD_FLAGS
    fixed_child_environment: dict[str, str] = FIXED_CHILD_ENVIRONMENT
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    parent_to_supervisor_launch_limit: Literal[1] = 1
    supervisor_to_worker_launch_limit: Literal[1] = 1
    outer_child_timeout_seconds: Literal[60] = OUTER_CHILD_TIMEOUT_SECONDS
    worker_timeout_seconds: Literal[45] = WORKER_TIMEOUT_SECONDS
    worker_result_output_limit: Literal[262144] = CHILD_OUTPUT_LIMIT
    supervisor_stdlib_only_until_worker_result: Literal[True] = True
    diagnostic_workload_runs_only_in_worker: Literal[True] = True
    worker_stdout_stderr_null_from_process_start: Literal[True] = True
    worker_result_uses_dedicated_anonymous_pipe: Literal[True] = True
    supervisor_alone_owns_parent_stdout: Literal[True] = True
    supervisor_emits_one_canonical_envelope_on_worker_failure: Literal[True] = True
    raw_supervisor_or_worker_output_persistence_allowed: Literal[False] = False
    live_default_observers_exposed: Literal[False] = False
    network_call_limit: Literal[0] = 0
    provider_evaluator_agent_call_limit: Literal[0] = 0
    credential_value_return_hash_prefix_or_length_limit: Literal[0] = 0

    @model_validator(mode="after")
    def validate_literals(self) -> SupervisedRuntimeProfile:
        if self.child_flags != CHILD_FLAGS:
            raise ValueError("v17 child flags drifted")
        if self.fixed_child_environment != FIXED_CHILD_ENVIRONMENT:
            raise ValueError("v17 child environment drifted")
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("v17 approved scopes drifted")
        return self


class SourceAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    source_qualification_authorized: Literal[True] = True
    state_approval_attempt_or_terminal_creation_authorized: Literal[False] = False
    environment_docker_dotenv_sdk_or_network_observation_authorized: Literal[False] = False
    credential_value_recording_authorized: Literal[False] = False
    docker_start_pull_load_image_store_or_container_mutation_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class SupervisedFrameContract(FrozenStrictModel):
    schema_version: Literal["supervised-frame-preflight-successor-contract-v17"] = (
        CONTRACT_SCHEMA_VERSION
    )
    contract_version: Literal[
        "ac-evaluator-v2-supervised-frame-preflight-successor-v17"
    ] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor: V16FailureBinding
    runtime: SupervisedRuntimeProfile
    authority: SourceAuthority
    correction_scope: Literal["supervisor-worker-process-and-result-pipe-only"] = (
        "supervisor-worker-process-and-result-pipe-only"
    )
    predecessor_retry_or_repair: Literal[False] = False
    execution_currently_authorized: Literal[False] = False
    next_gate: Literal["new-versioned-state-and-activation-wrapper-required"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> SupervisedFrameContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected or self.contract_id != v10._derived_id(
            "ncpcontract", expected
        ):
            raise ValueError("v17 contract identity differs")
        return self


class SourceCommitBinding(FrozenStrictModel):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    parents: tuple[str, ...]
    added_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_source(self) -> SourceCommitBinding:
        if self.parents != (SOURCE_PARENT_COMMIT,):
            raise ValueError("v17 source predecessor drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v17 source additions drifted")
        return self


class QualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    source_qualified: Literal[True] = True
    state_approval_attempt_or_terminal_created: Literal[False] = False
    docker_dotenv_sdk_network_or_provider_observation_count: Literal[0] = 0
    external_mutation_count: Literal[0] = 0
    execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class SourceQualification(FrozenStrictModel):
    schema_version: Literal["supervised-frame-preflight-source-qualification-v17"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal[
        "ac-evaluator-v2-supervised-frame-preflight-source-20260813-r1"
    ] = QUALIFICATION_ID
    status: Literal[
        "OFFLINE_V17_SUPERVISED_FRAME_SOURCE_QUALIFIED_ACTIVATION_CLOSED"
    ] = QUALIFICATION_STATUS
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[v10.CommittedFileBinding, ...]
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_terminal_id: Literal[
        "ncpterminal_db06f32f6223cdd227eb36b503b34ad6fc0eda817e563b21db9b896f8737c907"
    ]
    authority: QualificationAuthority
    next_gate: Literal["new-versioned-state-and-activation-wrapper-required"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v17 qualification time must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> SourceQualification:
        expected_paths = tuple(path.as_posix() for path in SOURCE_FILES)
        if tuple(item.path for item in self.source_files) != expected_paths:
            raise ValueError("v17 qualification inventory drifted")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != v10._hash_body(body):
            raise ValueError("v17 qualification hash mismatch")
        return self


def _predecessor_binding(root: Path) -> V16FailureBinding:
    contract = v16.load_contract(repository=root)
    qualification = v16._load_qualification(root)
    terminal_raw = v10._read(root, v16.TERMINAL_PATH)
    terminal = v16.TerminalTransition.model_validate_json(terminal_raw)
    _require(terminal_raw == v10._canonical(terminal), "v16 terminal bytes differ")
    _require(terminal.observation is not None, "v16 terminal lacks observation")
    observation = terminal.observation
    framed = observation.framed_child_execution
    child = observation.base.child_execution
    _require(framed is not None and child is not None, "v16 child evidence is absent")
    return V16FailureBinding(
        contract_id=contract.contract_id,
        source_qualification_hash=qualification.content_hash,
        terminal_id=terminal.terminal_id,
        terminal_content_hash=terminal.content_hash,
        terminal_file_sha256=sha256_bytes(terminal_raw),
        outcome=terminal.outcome,
        reason=terminal.reason,
        base_child_code=child.code,
        frame_code=framed.frame_code,
        envelope_received=framed.envelope_received,
        docker_cli_command_count=observation.base.docker_cli_command_count,
        child_launch_attempt_count=observation.base.child_launch_attempt_count,
        child_process_return_count=child.activity.child_process_return_count,
        network_call_count=terminal.network_call_count,
        provider_evaluator_agent_call_count=terminal.provider_evaluator_agent_call_count,
        docker_mutation_count=(
            terminal.docker_start_pull_load_image_store_or_container_mutation_count
        ),
        credential_value_metadata_count=(
            terminal.credential_value_return_hash_prefix_or_length_count
        ),
        raw_child_output_persisted=framed.raw_child_output_persisted,
        activity_accounting_complete=terminal.activity_accounting_complete,
        unknown_post_marker_activity_possible=terminal.unknown_post_marker_activity_possible,
        retry_or_resume_allowed=terminal.retry_or_resume_allowed,
        causal_detail_available=False,
    )


def _build_contract(root: Path) -> SupervisedFrameContract:
    v15_contract = v15.load_contract(repository=root)
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "predecessor": _predecessor_binding(root).model_dump(mode="json"),
        "runtime": SupervisedRuntimeProfile(
            supervisor_worker_file_sha256=sha256_bytes(v10._read(root, CHILD_PATH)),
            diagnostic_child_file_sha256=sha256_bytes(
                v10._read(root, v9.DIAGNOSTIC_CHILD_PATH)
            ),
            typed_parent_runtime_file_sha256=sha256_bytes(v10._read(root, v9.RUNTIME_PATH)),
            v15_contract_id=v15_contract.contract_id,
            v15_contract_content_hash=v15_contract.content_hash,
        ).model_dump(mode="json"),
        "authority": SourceAuthority().model_dump(mode="json"),
        "correction_scope": "supervisor-worker-process-and-result-pipe-only",
        "predecessor_retry_or_repair": False,
        "execution_currently_authorized": False,
        "next_gate": NEXT_GATE,
    }
    content_hash = v10._hash_body(body)
    return SupervisedFrameContract(
        **body,
        contract_id=v10._derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def materialize_contract(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    value = _build_contract(root)
    raw = v10._canonical(value)
    v10._write_once(root, CONTRACT_PATH, raw)
    return {
        "status": "OFFLINE_V17_SUPERVISED_FRAME_CONTRACT_MATERIALIZED_LIVE_CLOSED",
        "contract_id": value.contract_id,
        "contract_content_hash": value.content_hash,
        "artifact_path": CONTRACT_PATH.as_posix(),
        "artifact_file_sha256": sha256_bytes(raw),
        "artifact_bytes": len(raw),
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
        "next_gate": "exact-source-commit-and-offline-qualification",
    }


def load_contract(*, repository: str | Path | None = None) -> SupervisedFrameContract:
    root = v10._root(repository)
    raw = v10._read(root, CONTRACT_PATH)
    value = SupervisedFrameContract.model_validate_json(raw)
    _require(raw == v10._canonical(value), "v17 contract bytes are not canonical")
    _require(value == _build_contract(root), "v17 contract differs from source")
    return value


RunCallable = Callable[..., subprocess.CompletedProcess[bytes]]


def _execution(
    base: v9.ParentChildExecution,
    *,
    code: SupervisorCode | None = None,
    envelope_received: bool = False,
    activity: SupervisorActivity | None = None,
    complete: bool | None = None,
    unknown: bool | None = None,
) -> SupervisedChildExecution:
    if activity is None:
        worker_counts: tuple[int | None, int | None, int | None] = (None, None, None)
    else:
        worker_counts = (
            activity.worker_launch_attempt_count,
            activity.worker_process_return_count,
            activity.worker_result_message_count,
        )
    return SupervisedChildExecution(
        base=base,
        supervisor_code=code,
        envelope_received=envelope_received,
        worker_launch_attempt_count=worker_counts[0],
        worker_process_return_count=worker_counts[1],
        worker_result_message_count=worker_counts[2],
        activity_accounting_complete=(
            base.activity_accounting_complete if complete is None else complete
        ),
        unknown_workload_activity_possible=(
            base.unknown_post_launch_activity_possible if unknown is None else unknown
        ),
    )


def _failed_child_binding() -> SupervisedChildExecution:
    return _execution(v15._failed_child_binding().base)


def run_supervised_frame_child_injected(
    contract: SupervisedFrameContract,
    *,
    repository: str | Path | None = None,
    environment_present: v9.EnvironmentPresent,
    environment_value: v9.EnvironmentValue,
    python: str | Path,
    run: RunCallable,
) -> SupervisedChildExecution:
    """Run the v17 supervisor only from explicit authority-owned dependencies."""

    root = v10._root(repository)
    try:
        checked = SupervisedFrameContract.model_validate(contract.model_dump(mode="json"))
        _require(checked == load_contract(repository=root), "v17 runtime contract differs")
        wrapper = v10._logical_path(root, CHILD_PATH, must_exist=True)
        _require(
            sha256_bytes(v10._read(root, CHILD_PATH))
            == contract.runtime.supervisor_worker_file_sha256,
            "v17 supervisor source differs",
        )
        python_path = Path(python).resolve(strict=True)
        _require(python_path.is_file(), "v17 python runtime is not a file")
    except Exception:
        return _failed_child_binding()

    checks = completed_checks = 0
    try:
        checks += 1
        pythonhome_absent = not environment_present("PYTHONHOME")
        completed_checks += 1
        checks += 1
        pythonpath_absent = not environment_present("PYTHONPATH")
        completed_checks += 1
    except Exception:
        return _execution(
            v9._execution(
                pythonhome_absent=False,
                pythonpath_absent=False,
                systemroot_present=False,
                systemroot_nonempty=False,
                parent_checks=checks,
                parent_completed=completed_checks,
                systemroot_membership_checks=0,
                systemroot_nonempty_checks=0,
                launch_attempts=0,
                process_returns=0,
                passed_values=0,
                code=v9.ParentExecutionCode.PARENT_PRESENCE_ERROR,
            )
        )
    if not pythonhome_absent or not pythonpath_absent:
        return _execution(
            v9._execution(
                pythonhome_absent=pythonhome_absent,
                pythonpath_absent=pythonpath_absent,
                systemroot_present=False,
                systemroot_nonempty=False,
                parent_checks=2,
                parent_completed=2,
                systemroot_membership_checks=0,
                systemroot_nonempty_checks=0,
                launch_attempts=0,
                process_returns=0,
                passed_values=0,
                code=v9.ParentExecutionCode.PARENT_PYTHON_ENVIRONMENT_NOT_CLEAN,
            )
        )
    try:
        systemroot = environment_value("SYSTEMROOT")
    except Exception:
        systemroot = None
        systemroot_error = True
    else:
        systemroot_error = False
    if systemroot_error or not systemroot:
        return _execution(
            v9._execution(
                pythonhome_absent=True,
                pythonpath_absent=True,
                systemroot_present=systemroot is not None,
                systemroot_nonempty=bool(systemroot),
                parent_checks=2,
                parent_completed=2,
                systemroot_membership_checks=1,
                systemroot_nonempty_checks=int(not systemroot_error and systemroot is not None),
                launch_attempts=0,
                process_returns=0,
                passed_values=0,
                code=(
                    v9.ParentExecutionCode.SYSTEMROOT_PRESENCE_ERROR
                    if systemroot_error
                    else (
                        v9.ParentExecutionCode.SYSTEMROOT_MISSING
                        if systemroot is None
                        else v9.ParentExecutionCode.SYSTEMROOT_EMPTY
                    )
                ),
            )
        )
    try:
        result = run(
            [str(python_path), *CHILD_FLAGS, str(wrapper), "--repository", str(root)],
            cwd=root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            shell=False,
            timeout=OUTER_CHILD_TIMEOUT_SECONDS,
            env={**FIXED_CHILD_ENVIRONMENT, "SYSTEMROOT": systemroot},
            creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
        )
    except Exception:
        return _execution(
            v9._execution(
                pythonhome_absent=True,
                pythonpath_absent=True,
                systemroot_present=True,
                systemroot_nonempty=True,
                parent_checks=2,
                parent_completed=2,
                systemroot_membership_checks=1,
                systemroot_nonempty_checks=1,
                launch_attempts=1,
                process_returns=0,
                passed_values=1,
                code=v9.ParentExecutionCode.CHILD_LAUNCH_ERROR,
                complete=False,
                unknown=True,
            )
        )

    if result.returncode != 0:
        base_code = v9.ParentExecutionCode.CHILD_NONZERO_EXIT
    elif result.stderr:
        base_code = v9.ParentExecutionCode.CHILD_STDERR_NOT_EMPTY
    elif len(result.stdout) > CHILD_OUTPUT_LIMIT:
        base_code = v9.ParentExecutionCode.CHILD_OUTPUT_LIMIT
    else:
        base_code = None
    if base_code is not None:
        return _execution(
            v9._execution(
                pythonhome_absent=True,
                pythonpath_absent=True,
                systemroot_present=True,
                systemroot_nonempty=True,
                parent_checks=2,
                parent_completed=2,
                systemroot_membership_checks=1,
                systemroot_nonempty_checks=1,
                launch_attempts=1,
                process_returns=1,
                passed_values=1,
                code=base_code,
            ),
            complete=False,
            unknown=True,
        )
    try:
        envelope = SupervisedFrameEnvelope.model_validate_json(result.stdout)
    except Exception:
        base = v9._execution(
            pythonhome_absent=True,
            pythonpath_absent=True,
            systemroot_present=True,
            systemroot_nonempty=True,
            parent_checks=2,
            parent_completed=2,
            systemroot_membership_checks=1,
            systemroot_nonempty_checks=1,
            launch_attempts=1,
            process_returns=1,
            passed_values=1,
            code=v9.ParentExecutionCode.CHILD_OUTPUT_INVALID,
        )
        return _execution(
            base,
            code=SupervisorCode.SUPERVISED_OUTPUT_INVALID,
            complete=False,
            unknown=True,
        )
    if envelope.child is None:
        assert envelope.code is not None
        base = v9._execution(
            pythonhome_absent=True,
            pythonpath_absent=True,
            systemroot_present=True,
            systemroot_nonempty=True,
            parent_checks=2,
            parent_completed=2,
            systemroot_membership_checks=1,
            systemroot_nonempty_checks=1,
            launch_attempts=1,
            process_returns=1,
            passed_values=1,
            code=v9.ParentExecutionCode.CHILD_OUTPUT_INVALID,
        )
        return _execution(
            base,
            code=envelope.code,
            envelope_received=True,
            activity=envelope.activity,
            complete=envelope.activity.activity_accounting_complete,
            unknown=envelope.activity.unknown_workload_activity_possible,
        )
    base = v9._execution(
        pythonhome_absent=True,
        pythonpath_absent=True,
        systemroot_present=True,
        systemroot_nonempty=True,
        parent_checks=2,
        parent_completed=2,
        systemroot_membership_checks=1,
        systemroot_nonempty_checks=1,
        launch_attempts=1,
        process_returns=1,
        passed_values=1,
        child=envelope.child,
    )
    return _execution(
        base,
        envelope_received=True,
        activity=envelope.activity,
        complete=True,
        unknown=False,
    )


def run_parent_preflight_injected(
    contract: SupervisedFrameContract,
    *,
    repository: str | Path | None = None,
    docker_observer: Callable[..., dict[str, Any]],
    child_observer: Callable[..., SupervisedChildExecution],
) -> SupervisedParentObservation:
    """Compose v17 only from injected observers; no live defaults are exposed."""

    root = v10._root(repository)
    try:
        checked = SupervisedFrameContract.model_validate(contract.model_dump(mode="json"))
        _require(checked == load_contract(repository=root), "v17 parent contract differs")
        runtime_contract = v13._load_v9_contract(root)[0]
    except Exception:
        base = v9._contract_error_observation()
        return SupervisedParentObservation(
            base=base,
            activity_accounting_complete=base.activity_accounting_complete,
            unknown_post_marker_activity_possible=base.unknown_post_marker_activity_possible,
            passed=False,
        )
    captured: list[SupervisedChildExecution] = []

    def observe_child(*_args: Any, **_kwargs: Any) -> v9.ParentChildExecution:
        value = child_observer(contract, repository=root)
        checked_value = SupervisedChildExecution.model_validate(value.model_dump(mode="json"))
        captured.append(checked_value)
        return checked_value.base

    base = v9.run_parent_preflight(
        runtime_contract,
        repository=root,
        docker_observer=docker_observer,
        child_observer=observe_child,
    )
    supervised = captured[0] if captured else None
    complete = base.activity_accounting_complete and (
        True if supervised is None else supervised.activity_accounting_complete
    )
    unknown = base.unknown_post_marker_activity_possible or (
        False if supervised is None else supervised.unknown_workload_activity_possible
    )
    return SupervisedParentObservation(
        base=base,
        supervised_child_execution=supervised,
        activity_accounting_complete=complete,
        unknown_post_marker_activity_possible=unknown,
        passed=base.passed,
    )


def _source_commit(root: Path, selected: str) -> SourceCommitBinding:
    commit = v10._git(root, "rev-parse", f"{selected}^{{commit}}").decode("ascii").strip()
    tree = v10._git(root, "rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    row = v10._git(root, "rev-list", "--parents", "-n", "1", commit).decode("ascii").split()
    _require(row and row[0] == commit and len(row) == 2, "v17 source parent binding failed")
    lines = (
        v10._git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", row[1], commit)
        .decode("utf-8")
        .splitlines()
    )
    added = tuple(
        sorted(parts[1] for line in lines if (parts := line.split("\t"))[:1] == ["A"])
    )
    _require(len(lines) == len(added), "v17 source commit contains non-addition changes")
    return SourceCommitBinding(commit=commit, tree=tree, parents=(row[1],), added_paths=added)


def _build_qualification(
    root: Path, *, source_commit: str, recorded_at: datetime
) -> SourceQualification:
    contract = load_contract(repository=root)
    commit = _source_commit(root, source_commit)
    pairs = tuple(v10._committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(pair[0] for pair in pairs)
    contract_index = SOURCE_FILES.index(CONTRACT_PATH)
    _require(
        pairs[contract_index][1] == v10._canonical(contract),
        "committed v17 contract differs",
    )
    body = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": QUALIFICATION_STATUS,
        "recorded_at": recorded_at,
        "source_commit": commit.model_dump(mode="json"),
        "source_files": [item.model_dump(mode="json") for item in files],
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "predecessor_terminal_id": contract.predecessor.terminal_id,
        "authority": QualificationAuthority().model_dump(mode="json"),
        "next_gate": NEXT_GATE,
    }
    content_hash = v10._hash_body(body)
    return SourceQualification(**body, content_hash=content_hash)


def qualify_source(*, source_commit: str, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    value = _build_qualification(root, source_commit=source_commit, recorded_at=datetime.now(UTC))
    raw = v10._canonical(value)
    v10._write_once(root, QUALIFICATION_PATH, raw)
    return _qualification_summary(value, raw)


def _qualification_summary(value: SourceQualification, raw: bytes) -> dict[str, Any]:
    return {
        "status": value.status,
        "contract_id": value.contract_id,
        "source_commit": value.source_commit.commit,
        "source_tree": value.source_commit.tree,
        "qualification_hash": value.content_hash,
        "artifact_path": QUALIFICATION_PATH.as_posix(),
        "artifact_file_sha256": sha256_bytes(raw),
        "artifact_bytes": len(raw),
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
        "next_gate": value.next_gate,
    }


def validate_source_qualification(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    raw = v10._read(root, QUALIFICATION_PATH)
    value = SourceQualification.model_validate_json(raw)
    _require(raw == v10._canonical(value), "v17 qualification bytes are not canonical")
    rebuilt = _build_qualification(
        root,
        source_commit=value.source_commit.commit,
        recorded_at=value.recorded_at,
    )
    _require(value == rebuilt, "v17 qualification differs from committed source")
    return _qualification_summary(value, raw)


__all__ = [
    "APPROVED_RUNTIME",
    "BUILD_SCRIPT_PATH",
    "CHILD_PATH",
    "CONTRACT_PATH",
    "QUALIFICATION_PATH",
    "RUNTIME_PATH",
    "SOURCE_ADDED_PATHS",
    "SOURCE_PARENT_COMMIT",
    "SupervisedChildExecution",
    "SupervisedFrameContract",
    "SupervisedFrameEnvelope",
    "SupervisedFrameSuccessorError",
    "SupervisedParentObservation",
    "SupervisorCode",
    "TEST_PATH",
    "_build_contract",
    "load_contract",
    "materialize_contract",
    "qualify_source",
    "run_parent_preflight_injected",
    "run_supervised_frame_child_injected",
    "validate_source_qualification",
]
