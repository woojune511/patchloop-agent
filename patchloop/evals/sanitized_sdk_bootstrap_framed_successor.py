"""V13 framed-output successor for the consumed v12 no-call preflight.

Source construction and qualification are offline.  The runtime replaces the
unframed v9 child stdout boundary with a descriptor-isolated canonical envelope
and preserves the Docker-first, no-network scope.  State, approval and attempt
entrypoints require separate exact statements and are not authorized by source
qualification or generic continuation.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, Field, ValidationError, field_validator, model_validator

from patchloop.contracts import FrozenStrictModel
from patchloop.errors import ContractError
from patchloop.evals import sanitized_sdk_bootstrap_attempt_successor as v12
from patchloop.evals import sanitized_sdk_bootstrap_parent_successor as v9
from patchloop.evals import sanitized_sdk_parent_integration as v7
from patchloop.util import sha256_bytes

v10 = v12.v11.v10

CONTRACT_SCHEMA_VERSION = "sanitized-sdk-bootstrap-framed-successor-contract-v13"
CONTRACT_VERSION = "ac-evaluator-v2-sanitized-sdk-bootstrap-framed-successor-v13"
CONTRACT_PATH = Path(
    "experiments/evaluator-v2-sanitized-sdk-bootstrap-framed-successor-v13.contract.json"
)
RUNTIME_PATH = Path("patchloop/evals/sanitized_sdk_bootstrap_framed_successor.py")
CHILD_PATH = Path("scripts/run_sanitized_sdk_bootstrap_framed_child.py")
BUILD_SCRIPT_PATH = Path("scripts/build_sanitized_sdk_bootstrap_framed_successor.py")
TEST_PATH = Path("tests/test_sanitized_sdk_bootstrap_framed_successor.py")

SOURCE_PARENT_COMMIT = "ff4e00d124a0954903d06f8436c11af2c6bc57b1"
V12_EVIDENCE_COMMIT = "770b661e52646e0e309162121f14ff92f7f2568d"
QUALIFICATION_SCHEMA_VERSION = "sanitized-sdk-bootstrap-framed-source-qualification-v13"
QUALIFICATION_ID = "ac-evaluator-v2-sanitized-sdk-bootstrap-framed-source-20260812-r1"
QUALIFICATION_STATUS = "OFFLINE_V13_FRAMED_SOURCE_QUALIFIED_STATE_STATEMENT_REQUIRED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-bootstrap-framed-v13-source-qualification.json"
)
STATE_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-bootstrap-framed-v13-state-change-evidence.json"
)
APPROVAL_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-bootstrap-framed-v13-approval-binding.json"
)
RUN_AUTHORIZATION_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-bootstrap-framed-v13-run-authorization.json"
)
ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-bootstrap-framed-v13-attempt-intent.json"
)
ACTION_STARTED_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-bootstrap-framed-v13-action-started.json"
)
TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-sanitized-sdk-bootstrap-framed-v13-terminal.json"
)

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
            v12.CONTRACT_PATH,
            v12.RUNTIME_PATH,
            v12.QUALIFICATION_PATH,
            v12.TERMINAL_PATH,
            v9.CONTRACT_PATH,
            v9.RUNTIME_PATH,
            v9.QUALIFICATION_PATH,
            v9.DIAGNOSTIC_CHILD_PATH,
        ),
        key=lambda path: path.as_posix(),
    )
)

CHILD_FLAGS = v9.CHILD_FLAGS
FIXED_CHILD_ENVIRONMENT = v9.FIXED_CHILD_ENVIRONMENT
PASSTHROUGH_ENVIRONMENT_NAMES = v9.PASSTHROUGH_ENVIRONMENT_NAMES
CHILD_TIMEOUT_SECONDS = v9.CHILD_TIMEOUT_SECONDS
CHILD_OUTPUT_LIMIT = v9.CHILD_OUTPUT_LIMIT
APPROVED_RUNTIME = "patchloop.evals.sanitized_sdk_bootstrap_framed_successor.run_parent_preflight"
APPROVED_SCOPES = v12.APPROVED_SCOPES
NEXT_GATE = "fresh-exact-v13-state-statement"

STATE_TEMPLATE = (
    "Contract {contract_id}, source qualification {qualification_hash}: Docker Desktop is reported "
    "running; repository-root .env is reported to contain only OPENAI_API_KEY; state-binding-only; "
    "no-execution-authority."
)
APPROVAL_TEMPLATE = (
    "Contract {contract_id}, source qualification {qualification_hash}, state {state_id} "
    "({state_hash}): approve exactly one future v13 framed no-call preflight under the fixed "
    "scopes; approval-binding-only, no attempt now; no credential value recording, Docker start/"
    "pull/load/image-store mutation/container operation, network/transport, provider/evaluator/"
    "agent, candidate/"
    "cost/paid execution, retry/replacement/resume."
)
RUN_TEMPLATE = (
    "Contract {contract_id}, source qualification {qualification_hash}, state {state_id} "
    "({state_hash}), approval {approval_id} ({approval_hash}): authorize exactly one immediate v13 "
    "framed no-call preflight attempt now; append authorization, attempt and ACTION_STARTED before "
    "observation and one terminal after; no credential value recording, Docker start/pull/load/"
    "image-store mutation/container operation, network/transport, provider/evaluator/agent, "
    "candidate/cost/"
    "paid execution, retry/replacement/resume."
)


class FramedSuccessorError(ContractError):
    """The v13 successor failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FramedSuccessorError(message)


def _utc(value: datetime, *, label: str) -> datetime:
    _require(value.tzinfo is not None, f"{label} must be timezone-aware")
    _require(value.utcoffset() == UTC.utcoffset(value), f"{label} must be UTC")
    return value


def _validate_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("v13 datetime must be UTC")
    return value


UTCDateTime = Annotated[datetime, AfterValidator(_validate_utc_datetime)]


class FrameCode(StrEnum):
    DIAGNOSTIC_WRAPPER_IMPORT_ERROR = "diagnostic_wrapper_import_error"
    DIAGNOSTIC_EXECUTION_ERROR = "diagnostic_execution_error"
    DIAGNOSTIC_RESULT_INVALID = "diagnostic_result_invalid"
    FRAMED_CHILD_INTERNAL_ERROR = "framed_child_internal_error"
    FRAMED_OUTPUT_INVALID = "framed_output_invalid"


class FrameActivity(FrozenStrictModel):
    diagnostic_invocation_count: int = Field(ge=0, le=1)
    typed_validation_count: int = Field(ge=0, le=1)
    suppressed_stdout_channel_count: Literal[1] = 1
    suppressed_stderr_channel_count: Literal[1] = 1
    raw_workload_output_return_count: Literal[0] = 0
    exception_message_type_repr_or_traceback_return_count: Literal[0] = 0
    credential_value_return_hash_prefix_or_length_count: Literal[0] = 0
    activity_accounting_complete: bool
    unknown_workload_activity_possible: bool

    @model_validator(mode="after")
    def validate_semantics(self) -> FrameActivity:
        if self.typed_validation_count > self.diagnostic_invocation_count:
            raise ValueError("v13 typed validation exceeds invocation")
        if self.activity_accounting_complete == self.unknown_workload_activity_possible:
            raise ValueError("v13 frame accounting flags differ")
        return self


class FramedChildEnvelope(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-framed-child-envelope-v1"] = (
        "sanitized-sdk-bootstrap-framed-child-envelope-v1"
    )
    child: v7.IsolatedDiagnosticChild | None = None
    code: FrameCode | None = None
    activity: FrameActivity
    raw_output_returned: Literal[False] = False
    exception_message_type_repr_or_traceback_returned: Literal[False] = False
    credential_value_hash_prefix_or_length_returned: Literal[False] = False

    @model_validator(mode="after")
    def validate_semantics(self) -> FramedChildEnvelope:
        if (self.child is None) == (self.code is None):
            raise ValueError("v13 frame must contain exactly child or code")
        if self.child is not None:
            if (
                self.activity.diagnostic_invocation_count != 1
                or self.activity.typed_validation_count != 1
                or not self.activity.activity_accounting_complete
                or self.activity.unknown_workload_activity_possible
            ):
                raise ValueError("v13 valid child frame accounting differs")
        elif self.code == FrameCode.DIAGNOSTIC_WRAPPER_IMPORT_ERROR:
            if (
                self.activity.diagnostic_invocation_count != 0
                or self.activity.typed_validation_count != 0
                or not self.activity.activity_accounting_complete
            ):
                raise ValueError("v13 import-error frame accounting differs")
        elif self.activity.activity_accounting_complete:
            raise ValueError("v13 post-import frame error must be incomplete")
        return self


class FramedChildExecution(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-framed-child-execution-v13"] = (
        "sanitized-sdk-bootstrap-framed-child-execution-v13"
    )
    base: v9.ParentChildExecution
    frame_code: FrameCode | None = None
    envelope_received: bool
    raw_child_output_persisted: Literal[False] = False
    activity_accounting_complete: bool
    unknown_workload_activity_possible: bool

    @model_validator(mode="after")
    def validate_semantics(self) -> FramedChildExecution:
        if self.base.child is not None:
            if (
                self.frame_code is not None
                or not self.envelope_received
                or not self.activity_accounting_complete
                or self.unknown_workload_activity_possible
            ):
                raise ValueError("v13 valid framed execution differs")
        elif self.frame_code is not None:
            if self.base.code != v9.ParentExecutionCode.CHILD_OUTPUT_INVALID:
                raise ValueError("v13 frame failure base code differs")
            if self.activity_accounting_complete == self.unknown_workload_activity_possible:
                raise ValueError("v13 frame failure accounting differs")
        elif (
            self.activity_accounting_complete != self.base.activity_accounting_complete
            or self.unknown_workload_activity_possible
            != self.base.unknown_post_launch_activity_possible
        ):
            raise ValueError("v13 inherited child accounting differs")
        return self


class CorrectedParentObservation(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-framed-parent-observation-v13"] = (
        "sanitized-sdk-bootstrap-framed-parent-observation-v13"
    )
    base: v9.ParentObservation
    framed_child_execution: FramedChildExecution | None = None
    activity_accounting_complete: bool
    unknown_post_marker_activity_possible: bool
    passed: bool

    @model_validator(mode="after")
    def validate_semantics(self) -> CorrectedParentObservation:
        child = self.base.child_execution
        if child is None:
            if self.framed_child_execution is not None:
                raise ValueError("v13 unexpected framed child")
            expected_complete = self.base.activity_accounting_complete
            expected_unknown = self.base.unknown_post_marker_activity_possible
        else:
            if self.framed_child_execution is None or self.framed_child_execution.base != child:
                raise ValueError("v13 framed child projection differs")
            expected_complete = (
                self.base.activity_accounting_complete
                and self.framed_child_execution.activity_accounting_complete
            )
            expected_unknown = (
                self.base.unknown_post_marker_activity_possible
                or self.framed_child_execution.unknown_workload_activity_possible
            )
        if (
            self.activity_accounting_complete != expected_complete
            or self.unknown_post_marker_activity_possible != expected_unknown
            or self.passed != self.base.passed
        ):
            raise ValueError("v13 parent accounting differs")
        return self


class V12TerminalBinding(FrozenStrictModel):
    evidence_commit: Literal["770b661e52646e0e309162121f14ff92f7f2568d"] = V12_EVIDENCE_COMMIT
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    terminal_id: str = Field(pattern=r"^ncpterminal_[0-9a-f]{64}$")
    terminal_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    outcome: Literal["error"] = "error"
    reason: Literal["child_checker_error"] = "child_checker_error"
    child_code: Literal["child_output_invalid"] = "child_output_invalid"
    activity_accounting_complete: Literal[True] = True
    unknown_post_marker_activity_possible: Literal[False] = False
    retry_or_resume_allowed: Literal[False] = False


class RuntimeProfile(FrozenStrictModel):
    entrypoint: Literal[
        "patchloop.evals.sanitized_sdk_bootstrap_framed_successor.run_parent_preflight"
    ] = APPROVED_RUNTIME
    v9_source_commit: Literal["8678ce9e4fbae426971a90a2f47ad28b5a431885"] = (
        v12.v11.v10.V9_SOURCE_COMMIT
    )
    v9_contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    v9_source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    framed_child_path: Literal["scripts/run_sanitized_sdk_bootstrap_framed_child.py"] = (
        CHILD_PATH.as_posix()
    )
    framed_child_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    diagnostic_child_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    child_flags: tuple[str, ...] = CHILD_FLAGS
    fixed_child_environment: dict[str, str] = FIXED_CHILD_ENVIRONMENT
    passthrough_environment_names: tuple[str, ...] = PASSTHROUGH_ENVIRONMENT_NAMES
    docker_expected_command_count: Literal[8] = 8
    diagnostic_child_limit: Literal[1] = 1
    stdout_stderr_descriptor_isolation_required: Literal[True] = True
    canonical_single_envelope_required: Literal[True] = True
    raw_child_output_persistence_allowed: Literal[False] = False
    credential_value_return_hash_prefix_or_length_limit: Literal[0] = 0
    network_call_limit: Literal[0] = 0
    provider_evaluator_agent_call_limit: Literal[0] = 0

    @model_validator(mode="after")
    def validate_literals(self) -> RuntimeProfile:
        if self.child_flags != CHILD_FLAGS:
            raise ValueError("v13 child flags drifted")
        if self.fixed_child_environment != FIXED_CHILD_ENVIRONMENT:
            raise ValueError("v13 child environment drifted")
        if self.passthrough_environment_names != PASSTHROUGH_ENVIRONMENT_NAMES:
            raise ValueError("v13 pass-through environment drifted")
        return self


class LifecyclePolicy(FrozenStrictModel):
    fresh_source_bound_state_required: Literal[True] = True
    separate_exact_approval_required: Literal[True] = True
    exact_immediate_run_statement_required: Literal[True] = True
    authorization_attempt_action_before_observation: Literal[True] = True
    one_terminal_required: Literal[True] = True
    attempt_limit: Literal[1] = 1
    state_or_approval_reusable: Literal[False] = False
    retry_replacement_or_resume_allowed: Literal[False] = False
    consumed_v12_reuse_allowed: Literal[False] = False


class SourceAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    source_qualification_authorized: Literal[True] = True
    state_approval_attempt_or_terminal_during_qualification_authorized: Literal[False] = False
    environment_docker_dotenv_sdk_or_network_observation_authorized: Literal[False] = False
    credential_value_recording_authorized: Literal[False] = False
    docker_start_pull_load_image_store_or_container_mutation_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class FramedSuccessorContract(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-framed-successor-contract-v13"] = (
        CONTRACT_SCHEMA_VERSION
    )
    contract_version: Literal["ac-evaluator-v2-sanitized-sdk-bootstrap-framed-successor-v13"] = (
        CONTRACT_VERSION
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor: V12TerminalBinding
    runtime: RuntimeProfile
    lifecycle: LifecyclePolicy
    authority: SourceAuthority
    state_approval_and_attempt_entrypoints_implemented: Literal[True] = True
    execution_currently_authorized: Literal[False] = False
    next_gate: Literal["fresh-exact-v13-state-statement"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> FramedSuccessorContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected:
            raise ValueError("v13 contract hash mismatch")
        if self.contract_id != v10._derived_id("ncpcontract", expected):
            raise ValueError("v13 contract id mismatch")
        return self


class SourceCommitBinding(FrozenStrictModel):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    parents: tuple[str, ...]
    added_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_source(self) -> SourceCommitBinding:
        if self.parents != (SOURCE_PARENT_COMMIT,):
            raise ValueError("v13 source predecessor drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v13 source additions drifted")
        return self


class QualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    source_qualified: Literal[True] = True
    state_approval_attempt_or_terminal_created: Literal[False] = False
    environment_docker_dotenv_sdk_network_or_provider_observation_count: Literal[0] = 0
    external_mutation_count: Literal[0] = 0
    execution_authorized: Literal[False] = False


class SourceQualification(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-framed-source-qualification-v13"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal[
        "ac-evaluator-v2-sanitized-sdk-bootstrap-framed-source-20260812-r1"
    ] = QUALIFICATION_ID
    status: Literal["OFFLINE_V13_FRAMED_SOURCE_QUALIFIED_STATE_STATEMENT_REQUIRED"] = (
        QUALIFICATION_STATUS
    )
    recorded_at: UTCDateTime
    source_commit: SourceCommitBinding
    source_files: tuple[v10.CommittedFileBinding, ...]
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_terminal_id: str = Field(pattern=r"^ncpterminal_[0-9a-f]{64}$")
    authority: QualificationAuthority
    next_gate: Literal["fresh-exact-v13-state-statement"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v13 qualification time must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> SourceQualification:
        if tuple(item.path for item in self.source_files) != tuple(
            path.as_posix() for path in SOURCE_FILES
        ):
            raise ValueError("v13 qualification inventory drifted")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != v10._hash_body(body):
            raise ValueError("v13 qualification hash mismatch")
        return self


class StateEvidence(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-framed-state-v13"] = (
        "sanitized-sdk-bootstrap-framed-state-v13"
    )
    state_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    statement_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    docker_running_reported: Literal[True] = True
    dotenv_only_openai_api_key_reported: Literal[True] = True
    self_attested_nonproof: Literal[True] = True
    external_observation_count: Literal[0] = 0
    execution_authorized: Literal[False] = False
    reusable: Literal[False] = False
    recorded_at: UTCDateTime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> StateEvidence:
        body = self.model_dump(mode="json", exclude={"state_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected or self.state_id != v10._derived_id("ncpstate", expected):
            raise ValueError("v13 state identity differs")
        return self


class ApprovalBinding(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-framed-approval-v13"] = (
        "sanitized-sdk-bootstrap-framed-approval-v13"
    )
    approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    statement_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_runtime: Literal[
        "patchloop.evals.sanitized_sdk_bootstrap_framed_successor.run_parent_preflight"
    ] = APPROVED_RUNTIME
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    future_attempt_limit: Literal[1] = 1
    attempt_started: Literal[False] = False
    reusable: Literal[False] = False
    retry_replacement_or_resume_authorized: Literal[False] = False
    recorded_at: UTCDateTime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> ApprovalBinding:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("v13 approval scopes drifted")
        body = self.model_dump(mode="json", exclude={"approval_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected or self.approval_id != v10._derived_id(
            "ncpapproval", expected
        ):
            raise ValueError("v13 approval identity differs")
        return self


class RunAuthorization(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-framed-run-authorization-v13"] = (
        "sanitized-sdk-bootstrap-framed-run-authorization-v13"
    )
    authorization_id: str = Field(pattern=r"^ncprunauthorization_[0-9a-f]{64}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    approval_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    statement_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    attempt_limit: Literal[1] = 1
    retry_replacement_or_resume_authorized: Literal[False] = False
    recorded_at: UTCDateTime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> RunAuthorization:
        body = self.model_dump(mode="json", exclude={"authorization_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected or self.authorization_id != v10._derived_id(
            "ncprunauthorization", expected
        ):
            raise ValueError("v13 run authorization identity differs")
        return self


class AttemptIntent(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-framed-attempt-v13"] = (
        "sanitized-sdk-bootstrap-framed-attempt-v13"
    )
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    run_authorization_id: str = Field(pattern=r"^ncprunauthorization_[0-9a-f]{64}$")
    run_authorization_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    ledger_snapshot_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    attempt_number: Literal[1] = 1
    retry_or_resume_allowed: Literal[False] = False
    created_at: UTCDateTime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> AttemptIntent:
        body = self.model_dump(mode="json", exclude={"attempt_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected or self.attempt_id != v10._derived_id(
            "ncpattempt", expected
        ):
            raise ValueError("v13 attempt identity differs")
        return self


class ActionStarted(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-framed-action-started-v13"] = (
        "sanitized-sdk-bootstrap-framed-action-started-v13"
    )
    marker_id: str = Field(pattern=r"^ncpstarted_[0-9a-f]{64}$")
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    attempt_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sequence: Literal[1] = 1
    recorded_at: UTCDateTime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> ActionStarted:
        body = self.model_dump(mode="json", exclude={"marker_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected or self.marker_id != v10._derived_id(
            "ncpstarted", expected
        ):
            raise ValueError("v13 action identity differs")
        return self


class TerminalTransition(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-framed-terminal-v13"] = (
        "sanitized-sdk-bootstrap-framed-terminal-v13"
    )
    terminal_id: str = Field(pattern=r"^ncpterminal_[0-9a-f]{64}$")
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    action_started_id: str = Field(pattern=r"^ncpstarted_[0-9a-f]{64}$")
    previous_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sequence: Literal[2] = 2
    outcome: v9.ParentState
    reason: v9.ParentReason | Literal["lifecycle_checker_error"] | None = None
    observation: CorrectedParentObservation | None = None
    activity_accounting_complete: bool
    unknown_post_marker_activity_possible: bool
    retry_or_resume_allowed: Literal[False] = False
    network_call_count: int | None = Field(default=None, ge=0, le=0)
    provider_evaluator_agent_call_count: int | None = Field(default=None, ge=0, le=0)
    docker_start_pull_load_image_store_or_container_mutation_count: Literal[0] = 0
    credential_value_return_hash_prefix_or_length_count: Literal[0] = 0
    recorded_at: UTCDateTime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> TerminalTransition:
        if self.observation is None:
            if (
                self.outcome != v9.ParentState.ERROR
                or self.reason != "lifecycle_checker_error"
                or self.activity_accounting_complete
                or not self.unknown_post_marker_activity_possible
            ):
                raise ValueError("v13 lifecycle-error terminal differs")
        elif (
            self.outcome != self.observation.base.state
            or self.reason != self.observation.base.reason
            or self.activity_accounting_complete != self.observation.activity_accounting_complete
            or self.unknown_post_marker_activity_possible
            != self.observation.unknown_post_marker_activity_possible
            or self.network_call_count != self.observation.base.network_call_count
            or self.provider_evaluator_agent_call_count
            != self.observation.base.provider_evaluator_agent_call_count
        ):
            raise ValueError("v13 terminal observation differs")
        body = self.model_dump(mode="json", exclude={"terminal_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected or self.terminal_id != v10._derived_id(
            "ncpterminal", expected
        ):
            raise ValueError("v13 terminal identity differs")
        return self


def _load_v12_terminal(
    root: Path,
) -> tuple[v12.AttemptSuccessorContract, v12.SourceQualification, v12.TerminalTransition]:
    contract_raw = v10._read(root, v12.CONTRACT_PATH)
    qualification_raw = v10._read(root, v12.QUALIFICATION_PATH)
    terminal_raw = v10._read(root, v12.TERMINAL_PATH)
    contract = v12.AttemptSuccessorContract.model_validate_json(contract_raw)
    qualification = v12.SourceQualification.model_validate_json(qualification_raw)
    terminal = v12.TerminalTransition.model_validate_json(terminal_raw)
    _require(contract_raw == v10._canonical(contract), "v12 contract bytes differ")
    _require(qualification_raw == v10._canonical(qualification), "v12 qualification bytes differ")
    _require(terminal_raw == v10._canonical(terminal), "v12 terminal bytes differ")
    _require(
        v10._git(root, "show", f"{V12_EVIDENCE_COMMIT}:{v12.TERMINAL_PATH.as_posix()}")
        == terminal_raw,
        "v12 terminal evidence commit differs",
    )
    child = terminal.observation.child_execution if terminal.observation is not None else None
    _require(
        terminal.outcome.value == "error"
        and terminal.reason is not None
        and terminal.reason.value == "child_checker_error"
        and child is not None
        and child.code == v9.ParentExecutionCode.CHILD_OUTPUT_INVALID
        and terminal.activity_accounting_complete
        and not terminal.unknown_post_marker_activity_possible,
        "v12 consumed terminal boundary differs",
    )
    return contract, qualification, terminal


def _load_v9_contract(root: Path) -> tuple[v9.ParentSuccessorContract, v9.SourceQualification]:
    contract_raw = v10._read(root, v9.CONTRACT_PATH)
    qualification_raw = v10._read(root, v9.QUALIFICATION_PATH)
    contract = v9.ParentSuccessorContract.model_validate_json(contract_raw)
    qualification = v9.SourceQualification.model_validate_json(qualification_raw)
    _require(contract_raw == v10._canonical(contract), "v9 contract bytes differ")
    _require(qualification_raw == v10._canonical(qualification), "v9 qualification bytes differ")
    return contract, qualification


def _predecessor_binding(root: Path) -> V12TerminalBinding:
    contract, qualification, terminal = _load_v12_terminal(root)
    assert terminal.reason is not None and terminal.observation is not None
    assert terminal.observation.child_execution is not None
    return V12TerminalBinding(
        contract_id=contract.contract_id,
        source_qualification_hash=qualification.content_hash,
        terminal_id=terminal.terminal_id,
        terminal_content_hash=terminal.content_hash,
    )


def _runtime_profile(root: Path) -> RuntimeProfile:
    contract, qualification = _load_v9_contract(root)
    return RuntimeProfile(
        v9_contract_id=contract.contract_id,
        v9_source_qualification_hash=qualification.content_hash,
        framed_child_file_sha256=sha256_bytes(v10._read(root, CHILD_PATH)),
        diagnostic_child_file_sha256=sha256_bytes(v10._read(root, v9.DIAGNOSTIC_CHILD_PATH)),
    )


def _build_contract(root: Path) -> FramedSuccessorContract:
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "predecessor": _predecessor_binding(root).model_dump(mode="json"),
        "runtime": _runtime_profile(root).model_dump(mode="json"),
        "lifecycle": LifecyclePolicy().model_dump(mode="json"),
        "authority": SourceAuthority().model_dump(mode="json"),
        "state_approval_and_attempt_entrypoints_implemented": True,
        "execution_currently_authorized": False,
        "next_gate": NEXT_GATE,
    }
    content_hash = v10._hash_body(body)
    return FramedSuccessorContract(
        **body,
        contract_id=v10._derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def load_contract(*, repository: str | Path | None = None) -> FramedSuccessorContract:
    root = v10._root(repository)
    raw = v10._read(root, CONTRACT_PATH)
    try:
        value = FramedSuccessorContract.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise FramedSuccessorError("v13 contract artifact is invalid") from exc
    _require(raw == v10._canonical(value), "v13 contract bytes are not canonical")
    _require(value == _build_contract(root), "v13 contract has drifted")
    return value


def materialize_contract(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    value = _build_contract(root)
    target = v10._logical_path(root, CONTRACT_PATH, must_exist=False)
    raw = v10._canonical(value)
    if target.exists():
        _require(v10._read(root, CONTRACT_PATH) == raw, "v13 contract already differs")
    else:
        v10._write_once(root, CONTRACT_PATH, raw)
    return {
        "status": "OFFLINE_V13_FRAMED_CONTRACT_MATERIALIZED_LIVE_CLOSED",
        "contract_id": value.contract_id,
        "contract_content_hash": value.content_hash,
        "runtime_artifacts_created": False,
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
        "next_gate": "exact-source-commit-and-offline-qualification",
    }


RunCallable = Callable[..., subprocess.CompletedProcess[bytes]]


def _framed_execution(
    base: v9.ParentChildExecution,
    *,
    frame_code: FrameCode | None = None,
    envelope_received: bool = False,
    complete: bool | None = None,
    unknown: bool | None = None,
) -> FramedChildExecution:
    return FramedChildExecution(
        base=base,
        frame_code=frame_code,
        envelope_received=envelope_received,
        activity_accounting_complete=(
            base.activity_accounting_complete if complete is None else complete
        ),
        unknown_workload_activity_possible=(
            base.unknown_post_launch_activity_possible if unknown is None else unknown
        ),
    )


def run_framed_diagnostic_child(
    contract: FramedSuccessorContract,
    *,
    repository: str | Path | None = None,
    environment_present: v9.EnvironmentPresent | None = None,
    environment_value: v9.EnvironmentValue | None = None,
    run: RunCallable = subprocess.run,
) -> FramedChildExecution:
    root = v10._root(repository)
    try:
        checked = FramedSuccessorContract.model_validate(contract.model_dump(mode="json"))
        _require(checked == load_contract(repository=root), "v13 runtime contract differs")
        wrapper = v10._logical_path(root, CHILD_PATH, must_exist=True)
        _require(
            sha256_bytes(v10._read(root, CHILD_PATH)) == contract.runtime.framed_child_file_sha256,
            "v13 framed child source differs",
        )
        _v9_path, python = v9._runtime_binding(_load_v9_contract(root)[0], root=root)
    except Exception:
        return _framed_execution(
            v9._execution(
                binding_valid=False,
                pythonhome_absent=False,
                pythonpath_absent=False,
                systemroot_present=False,
                systemroot_nonempty=False,
                parent_checks=0,
                parent_completed=0,
                systemroot_membership_checks=0,
                systemroot_nonempty_checks=0,
                launch_attempts=0,
                process_returns=0,
                passed_values=0,
                code=v9.ParentExecutionCode.CHILD_BINDING_ERROR,
            )
        )
    present = environment_present or (lambda name: name in os.environ)
    value = environment_value or os.environ.get
    checks = completed_checks = 0
    try:
        checks += 1
        pythonhome_absent = not present("PYTHONHOME")
        completed_checks += 1
        checks += 1
        pythonpath_absent = not present("PYTHONPATH")
        completed_checks += 1
    except Exception:
        return _framed_execution(
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
        return _framed_execution(
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
        systemroot = value("SYSTEMROOT")
    except Exception:
        return _framed_execution(
            v9._execution(
                pythonhome_absent=True,
                pythonpath_absent=True,
                systemroot_present=False,
                systemroot_nonempty=False,
                parent_checks=2,
                parent_completed=2,
                systemroot_membership_checks=1,
                systemroot_nonempty_checks=0,
                launch_attempts=0,
                process_returns=0,
                passed_values=0,
                code=v9.ParentExecutionCode.SYSTEMROOT_PRESENCE_ERROR,
            )
        )
    if not systemroot:
        return _framed_execution(
            v9._execution(
                pythonhome_absent=True,
                pythonpath_absent=True,
                systemroot_present=systemroot is not None,
                systemroot_nonempty=False,
                parent_checks=2,
                parent_completed=2,
                systemroot_membership_checks=1,
                systemroot_nonempty_checks=int(systemroot is not None),
                launch_attempts=0,
                process_returns=0,
                passed_values=0,
                code=(
                    v9.ParentExecutionCode.SYSTEMROOT_MISSING
                    if systemroot is None
                    else v9.ParentExecutionCode.SYSTEMROOT_EMPTY
                ),
            )
        )
    try:
        result = run(
            [str(python), *CHILD_FLAGS, str(wrapper), "--repository", str(root)],
            cwd=root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            shell=False,
            timeout=CHILD_TIMEOUT_SECONDS,
            env={**FIXED_CHILD_ENVIRONMENT, "SYSTEMROOT": systemroot},
            creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
        )
    except Exception:
        return _framed_execution(
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
            code=base_code,
        )
        return _framed_execution(base, complete=False, unknown=True)
    try:
        envelope = FramedChildEnvelope.model_validate_json(result.stdout)
    except (ValidationError, UnicodeDecodeError):
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
        return _framed_execution(
            base,
            frame_code=FrameCode.FRAMED_OUTPUT_INVALID,
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
        return _framed_execution(
            base,
            frame_code=envelope.code,
            envelope_received=True,
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
    return _framed_execution(base, envelope_received=True, complete=True, unknown=False)


def run_parent_preflight(
    contract: FramedSuccessorContract,
    *,
    repository: str | Path | None = None,
    docker_observer: Callable[
        ..., dict[str, Any]
    ] = v9.d137.run_d137_docker_no_call_preflight_observation,
    child_observer: Callable[..., FramedChildExecution] = run_framed_diagnostic_child,
) -> CorrectedParentObservation:
    root = v10._root(repository)
    try:
        checked = FramedSuccessorContract.model_validate(contract.model_dump(mode="json"))
        _require(checked == load_contract(repository=root), "v13 parent contract differs")
        runtime_contract = _load_v9_contract(root)[0]
    except Exception:
        base = v9._contract_error_observation()
        return CorrectedParentObservation(
            base=base,
            activity_accounting_complete=base.activity_accounting_complete,
            unknown_post_marker_activity_possible=base.unknown_post_marker_activity_possible,
            passed=False,
        )
    captured: list[FramedChildExecution] = []

    def observe_child(*_args: Any, **_kwargs: Any) -> v9.ParentChildExecution:
        value = child_observer(contract, repository=root)
        value = FramedChildExecution.model_validate(value.model_dump(mode="json"))
        captured.append(value)
        return value.base

    base = v9.run_parent_preflight(
        runtime_contract,
        repository=root,
        docker_observer=docker_observer,
        child_observer=observe_child,
    )
    framed = captured[0] if captured else None
    complete = base.activity_accounting_complete and (
        True if framed is None else framed.activity_accounting_complete
    )
    unknown = base.unknown_post_marker_activity_possible or (
        False if framed is None else framed.unknown_workload_activity_possible
    )
    return CorrectedParentObservation(
        base=base,
        framed_child_execution=framed,
        activity_accounting_complete=complete,
        unknown_post_marker_activity_possible=unknown,
        passed=base.passed,
    )


def _source_commit(root: Path, selected: str) -> SourceCommitBinding:
    commit = v10._git(root, "rev-parse", f"{selected}^{{commit}}").decode().strip()
    tree = v10._git(root, "rev-parse", f"{commit}^{{tree}}").decode().strip()
    parents = tuple(v10._git(root, "show", "-s", "--format=%P", commit).decode().strip().split())
    rows = (
        v10._git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", commit)
        .decode()
        .splitlines()
    )
    added: list[str] = []
    for row in rows:
        status, path = row.split("\t", 1)
        _require(status == "A", "v13 source commit contains non-addition")
        added.append(path)
    return SourceCommitBinding(
        commit=commit,
        tree=tree,
        parents=parents,
        added_paths=tuple(sorted(added)),
    )


def _build_qualification(
    root: Path, *, source_commit: str, recorded_at: datetime
) -> SourceQualification:
    commit = _source_commit(root, source_commit)
    pairs = tuple(v10._committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(pair[0] for pair in pairs)
    by_path = {item.path: (item, raw) for item, raw in pairs}
    committed_contract_raw = by_path[CONTRACT_PATH.as_posix()][1]
    committed_contract = FramedSuccessorContract.model_validate_json(committed_contract_raw)
    _require(
        committed_contract_raw == v10._canonical(committed_contract),
        "v13 committed contract bytes differ",
    )
    _require(
        committed_contract == load_contract(repository=root),
        "v13 working contract differs from source commit",
    )
    contract = committed_contract
    body = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": QUALIFICATION_STATUS,
        "recorded_at": _utc(recorded_at, label="v13 qualification recorded_at"),
        "source_commit": commit.model_dump(mode="json"),
        "source_files": tuple(item.model_dump(mode="json") for item in files),
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "predecessor_terminal_id": contract.predecessor.terminal_id,
        "authority": QualificationAuthority().model_dump(mode="json"),
        "next_gate": NEXT_GATE,
    }
    return SourceQualification(**body, content_hash=v10._hash_body(body))


def qualify_source(
    *, source_commit: str = "HEAD", repository: str | Path | None = None
) -> dict[str, Any]:
    root = v10._root(repository)
    target = v10._logical_path(root, QUALIFICATION_PATH, must_exist=False)
    value = _build_qualification(root, source_commit=source_commit, recorded_at=datetime.now(UTC))
    raw = v10._canonical(value)
    if target.exists():
        _require(v10._read(root, QUALIFICATION_PATH) == raw, "v13 qualification already differs")
    else:
        v10._write_once(root, QUALIFICATION_PATH, raw)
    return _qualification_summary(value, raw)


def _qualification_summary(value: SourceQualification, raw: bytes) -> dict[str, Any]:
    return {
        "status": value.status,
        "source_commit": value.source_commit.commit,
        "source_tree": value.source_commit.tree,
        "contract_id": value.contract_id,
        "source_qualification_hash": value.content_hash,
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "runtime_artifacts_created": False,
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate_source_qualification(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    raw = v10._read(root, QUALIFICATION_PATH)
    try:
        value = SourceQualification.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise FramedSuccessorError("v13 qualification is invalid") from exc
    _require(raw == v10._canonical(value), "v13 qualification bytes are not canonical")
    expected = _build_qualification(
        root,
        source_commit=value.source_commit.commit,
        recorded_at=value.recorded_at,
    )
    _require(value == expected, "v13 qualification has drifted")
    return _qualification_summary(value, raw)


def _load_qualification(root: Path) -> SourceQualification:
    validate_source_qualification(repository=root)
    return SourceQualification.model_validate_json(v10._read(root, QUALIFICATION_PATH))


def expected_state_statement(
    contract: FramedSuccessorContract, qualification: SourceQualification
) -> str:
    _require(qualification.contract_id == contract.contract_id, "v13 state contract differs")
    return STATE_TEMPLATE.format(
        contract_id=contract.contract_id,
        qualification_hash=qualification.content_hash,
    )


def build_state_evidence(
    contract: FramedSuccessorContract,
    qualification: SourceQualification,
    *,
    statement: str,
    recorded_at: datetime,
) -> StateEvidence:
    _require(
        statement == expected_state_statement(contract, qualification),
        "v13 state statement differs",
    )
    body = {
        "schema_version": "sanitized-sdk-bootstrap-framed-state-v13",
        "contract_id": contract.contract_id,
        "source_qualification_hash": qualification.content_hash,
        "statement_sha256": sha256_bytes(statement.encode("utf-8")),
        "docker_running_reported": True,
        "dotenv_only_openai_api_key_reported": True,
        "self_attested_nonproof": True,
        "external_observation_count": 0,
        "execution_authorized": False,
        "reusable": False,
        "recorded_at": _utc(recorded_at, label="v13 state recorded_at"),
    }
    content_hash = v10._hash_body(body)
    return StateEvidence(
        **body,
        state_id=v10._derived_id("ncpstate", content_hash),
        content_hash=content_hash,
    )


def record_state(*, statement: str, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    value = build_state_evidence(
        load_contract(repository=root),
        _load_qualification(root),
        statement=statement,
        recorded_at=datetime.now(UTC),
    )
    v10._write_once(root, STATE_PATH, v10._canonical(value))
    return {
        "status": "V13_STATE_RECORDED_SELF_ATTESTED_NO_EXECUTION",
        "state_id": value.state_id,
        "state_content_hash": value.content_hash,
        "external_observations_made": 0,
        "execution_authorized": False,
    }


def _load_state(root: Path) -> StateEvidence:
    raw = v10._read(root, STATE_PATH)
    value = StateEvidence.model_validate_json(raw)
    _require(raw == v10._canonical(value), "v13 state bytes differ")
    return value


def expected_approval_statement(
    contract: FramedSuccessorContract,
    qualification: SourceQualification,
    state: StateEvidence,
) -> str:
    _require(
        state.contract_id == contract.contract_id
        and state.source_qualification_hash == qualification.content_hash,
        "v13 approval state binding differs",
    )
    return APPROVAL_TEMPLATE.format(
        contract_id=contract.contract_id,
        qualification_hash=qualification.content_hash,
        state_id=state.state_id,
        state_hash=state.content_hash,
    )


def build_approval(
    contract: FramedSuccessorContract,
    qualification: SourceQualification,
    state: StateEvidence,
    *,
    statement: str,
    recorded_at: datetime,
) -> ApprovalBinding:
    _require(
        statement == expected_approval_statement(contract, qualification, state),
        "v13 approval statement differs",
    )
    recorded_at = _utc(recorded_at, label="v13 approval recorded_at")
    _require(recorded_at >= state.recorded_at, "v13 approval predates state")
    body = {
        "schema_version": "sanitized-sdk-bootstrap-framed-approval-v13",
        "contract_id": contract.contract_id,
        "source_qualification_hash": qualification.content_hash,
        "state_id": state.state_id,
        "state_content_hash": state.content_hash,
        "statement_sha256": sha256_bytes(statement.encode("utf-8")),
        "approved_runtime": APPROVED_RUNTIME,
        "approved_scopes": APPROVED_SCOPES,
        "future_attempt_limit": 1,
        "attempt_started": False,
        "reusable": False,
        "retry_replacement_or_resume_authorized": False,
        "recorded_at": recorded_at,
    }
    content_hash = v10._hash_body(body)
    return ApprovalBinding(
        **body,
        approval_id=v10._derived_id("ncpapproval", content_hash),
        content_hash=content_hash,
    )


def record_approval(*, statement: str, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    value = build_approval(
        load_contract(repository=root),
        _load_qualification(root),
        _load_state(root),
        statement=statement,
        recorded_at=datetime.now(UTC),
    )
    v10._write_once(root, APPROVAL_PATH, v10._canonical(value))
    return {
        "status": "V13_APPROVAL_RECORDED_ATTEMPT_NOT_STARTED",
        "approval_id": value.approval_id,
        "approval_content_hash": value.content_hash,
        "attempt_started": False,
        "external_observations_made": 0,
    }


def _load_approval(root: Path) -> ApprovalBinding:
    raw = v10._read(root, APPROVAL_PATH)
    value = ApprovalBinding.model_validate_json(raw)
    _require(raw == v10._canonical(value), "v13 approval bytes differ")
    return value


def expected_run_statement(
    contract: FramedSuccessorContract,
    qualification: SourceQualification,
    state: StateEvidence,
    approval: ApprovalBinding,
) -> str:
    _require(
        approval.contract_id == contract.contract_id
        and approval.source_qualification_hash == qualification.content_hash
        and approval.state_id == state.state_id
        and approval.state_content_hash == state.content_hash,
        "v13 run approval binding differs",
    )
    return RUN_TEMPLATE.format(
        contract_id=contract.contract_id,
        qualification_hash=qualification.content_hash,
        state_id=state.state_id,
        state_hash=state.content_hash,
        approval_id=approval.approval_id,
        approval_hash=approval.content_hash,
    )


def _build_run_authorization(
    contract: FramedSuccessorContract,
    qualification: SourceQualification,
    state: StateEvidence,
    approval: ApprovalBinding,
    *,
    statement: str,
    recorded_at: datetime,
) -> RunAuthorization:
    _require(
        statement == expected_run_statement(contract, qualification, state, approval),
        "v13 run statement differs",
    )
    recorded_at = _utc(recorded_at, label="v13 authorization recorded_at")
    _require(recorded_at >= approval.recorded_at, "v13 run authorization predates approval")
    body = {
        "schema_version": "sanitized-sdk-bootstrap-framed-run-authorization-v13",
        "contract_id": contract.contract_id,
        "source_qualification_hash": qualification.content_hash,
        "state_id": state.state_id,
        "approval_id": approval.approval_id,
        "approval_content_hash": approval.content_hash,
        "statement_sha256": sha256_bytes(statement.encode("utf-8")),
        "attempt_limit": 1,
        "retry_replacement_or_resume_authorized": False,
        "recorded_at": recorded_at,
    }
    content_hash = v10._hash_body(body)
    return RunAuthorization(
        **body,
        authorization_id=v10._derived_id("ncprunauthorization", content_hash),
        content_hash=content_hash,
    )


def _ledger_paths() -> tuple[Path, ...]:
    return (RUN_AUTHORIZATION_PATH, ATTEMPT_PATH, ACTION_STARTED_PATH, TERMINAL_PATH)


def _empty_ledger_hash(root: Path) -> str:
    rows = [
        {
            "path": path.as_posix(),
            "exists": v10._logical_path(root, path, must_exist=False).exists(),
        }
        for path in _ledger_paths()
    ]
    _require(not any(row["exists"] for row in rows), "v13 attempt ledger is consumed")
    return v10._hash_body({"rows": rows})


def _canonical_empty_ledger_hash() -> str:
    return v10._hash_body(
        {"rows": [{"path": path.as_posix(), "exists": False} for path in _ledger_paths()]}
    )


def _build_attempt(
    authorization: RunAuthorization, *, ledger_hash: str, created_at: datetime
) -> AttemptIntent:
    created_at = _utc(created_at, label="v13 attempt created_at")
    _require(created_at >= authorization.recorded_at, "v13 attempt predates authorization")
    body = {
        "schema_version": "sanitized-sdk-bootstrap-framed-attempt-v13",
        "run_authorization_id": authorization.authorization_id,
        "run_authorization_content_hash": authorization.content_hash,
        "ledger_snapshot_hash": ledger_hash,
        "attempt_number": 1,
        "retry_or_resume_allowed": False,
        "created_at": created_at,
    }
    content_hash = v10._hash_body(body)
    return AttemptIntent(
        **body,
        attempt_id=v10._derived_id("ncpattempt", content_hash),
        content_hash=content_hash,
    )


def _build_action(attempt: AttemptIntent, *, recorded_at: datetime) -> ActionStarted:
    recorded_at = _utc(recorded_at, label="v13 action recorded_at")
    _require(recorded_at >= attempt.created_at, "v13 action predates attempt")
    body = {
        "schema_version": "sanitized-sdk-bootstrap-framed-action-started-v13",
        "attempt_id": attempt.attempt_id,
        "attempt_content_hash": attempt.content_hash,
        "sequence": 1,
        "recorded_at": recorded_at,
    }
    content_hash = v10._hash_body(body)
    return ActionStarted(
        **body,
        marker_id=v10._derived_id("ncpstarted", content_hash),
        content_hash=content_hash,
    )


def _build_terminal(
    attempt: AttemptIntent,
    action: ActionStarted,
    *,
    observation: CorrectedParentObservation | None,
    recorded_at: datetime,
) -> TerminalTransition:
    recorded_at = _utc(recorded_at, label="v13 terminal recorded_at")
    _require(recorded_at >= action.recorded_at, "v13 terminal predates action")
    if observation is None:
        outcome = v9.ParentState.ERROR
        reason: v9.ParentReason | str | None = "lifecycle_checker_error"
        complete, unknown = False, True
        network_count = provider_count = None
    else:
        observation = CorrectedParentObservation.model_validate(observation.model_dump(mode="json"))
        outcome = observation.base.state
        reason = observation.base.reason
        complete = observation.activity_accounting_complete
        unknown = observation.unknown_post_marker_activity_possible
        network_count = observation.base.network_call_count
        provider_count = observation.base.provider_evaluator_agent_call_count
    body = {
        "schema_version": "sanitized-sdk-bootstrap-framed-terminal-v13",
        "attempt_id": attempt.attempt_id,
        "action_started_id": action.marker_id,
        "previous_content_hash": action.content_hash,
        "sequence": 2,
        "outcome": outcome,
        "reason": reason,
        "observation": None if observation is None else observation.model_dump(mode="json"),
        "activity_accounting_complete": complete,
        "unknown_post_marker_activity_possible": unknown,
        "retry_or_resume_allowed": False,
        "network_call_count": network_count,
        "provider_evaluator_agent_call_count": provider_count,
        "docker_start_pull_load_image_store_or_container_mutation_count": 0,
        "credential_value_return_hash_prefix_or_length_count": 0,
        "recorded_at": recorded_at,
    }
    content_hash = v10._hash_body(body)
    return TerminalTransition(
        **body,
        terminal_id=v10._derived_id("ncpterminal", content_hash),
        content_hash=content_hash,
    )


def run_once(
    *,
    statement: str,
    repository: str | Path | None = None,
    parent_observer: Callable[..., CorrectedParentObservation] = run_parent_preflight,
) -> dict[str, Any]:
    root = v10._root(repository)
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    state = _load_state(root)
    approval = _load_approval(root)
    authorization = _build_run_authorization(
        contract,
        qualification,
        state,
        approval,
        statement=statement,
        recorded_at=datetime.now(UTC),
    )
    ledger_hash = _empty_ledger_hash(root)
    v10._write_once(root, RUN_AUTHORIZATION_PATH, v10._canonical(authorization))
    attempt = _build_attempt(authorization, ledger_hash=ledger_hash, created_at=datetime.now(UTC))
    v10._write_once(root, ATTEMPT_PATH, v10._canonical(attempt))
    action = _build_action(attempt, recorded_at=datetime.now(UTC))
    v10._write_once(root, ACTION_STARTED_PATH, v10._canonical(action))
    try:
        observation = parent_observer(contract, repository=root)
    except Exception:
        observation = None
    terminal = _build_terminal(
        attempt,
        action,
        observation=observation,
        recorded_at=datetime.now(UTC),
    )
    raw = v10._canonical(terminal)
    lowered = raw.lower()
    _require(b"openai_api_key=" not in lowered and b"sk-" not in lowered, "v13 terminal leaks")
    v10._write_once(root, TERMINAL_PATH, raw)
    return validate_attempt_chain(repository=root)


def validate_attempt_chain(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    state = _load_state(root)
    approval = _load_approval(root)
    values: list[FrozenStrictModel] = []
    classes = (RunAuthorization, AttemptIntent, ActionStarted, TerminalTransition)
    for path, cls in zip(_ledger_paths(), classes, strict=True):
        raw = v10._read(root, path)
        value = cls.model_validate_json(raw)
        _require(raw == v10._canonical(value), f"v13 {path.name} bytes differ")
        values.append(value)
    authorization, attempt, action, terminal = values
    assert isinstance(authorization, RunAuthorization)
    assert isinstance(attempt, AttemptIntent)
    assert isinstance(action, ActionStarted)
    assert isinstance(terminal, TerminalTransition)
    _require(
        state.contract_id == contract.contract_id
        and state.source_qualification_hash == qualification.content_hash
        and state.statement_sha256
        == sha256_bytes(expected_state_statement(contract, qualification).encode("utf-8")),
        "v13 state binding differs",
    )
    _require(
        approval.contract_id == contract.contract_id
        and approval.source_qualification_hash == qualification.content_hash
        and approval.state_id == state.state_id
        and approval.state_content_hash == state.content_hash
        and approval.statement_sha256
        == sha256_bytes(
            expected_approval_statement(contract, qualification, state).encode("utf-8")
        ),
        "v13 approval binding differs",
    )
    _require(
        authorization.contract_id == contract.contract_id
        and authorization.source_qualification_hash == qualification.content_hash
        and authorization.state_id == state.state_id
        and authorization.approval_id == approval.approval_id
        and authorization.approval_content_hash == approval.content_hash
        and authorization.statement_sha256
        == sha256_bytes(
            expected_run_statement(contract, qualification, state, approval).encode("utf-8")
        ),
        "v13 run authorization differs",
    )
    _require(
        attempt.run_authorization_id == authorization.authorization_id
        and attempt.run_authorization_content_hash == authorization.content_hash,
        "v13 attempt authorization differs",
    )
    _require(
        attempt.ledger_snapshot_hash == _canonical_empty_ledger_hash(),
        "v13 initial ledger differs",
    )
    _require(
        action.attempt_id == attempt.attempt_id
        and action.attempt_content_hash == attempt.content_hash
        and terminal.attempt_id == attempt.attempt_id
        and terminal.action_started_id == action.marker_id,
        "v13 terminal chain differs",
    )
    _require(
        terminal.previous_content_hash == action.content_hash,
        "v13 terminal predecessor differs",
    )
    _require(
        qualification.recorded_at
        <= state.recorded_at
        <= approval.recorded_at
        <= authorization.recorded_at
        <= attempt.created_at
        <= action.recorded_at
        <= terminal.recorded_at,
        "v13 lifecycle chronology differs",
    )
    terminal_raw = v10._canonical(terminal).lower()
    _require(
        b"openai_api_key=" not in terminal_raw and b"sk-" not in terminal_raw,
        "v13 persisted terminal leaks",
    )
    return {
        "status": "V13_FRAMED_NO_CALL_PREFLIGHT_TERMINAL_VALID",
        "contract_id": contract.contract_id,
        "source_qualification_hash": qualification.content_hash,
        "state_id": state.state_id,
        "approval_id": approval.approval_id,
        "attempt_id": attempt.attempt_id,
        "terminal_id": terminal.terminal_id,
        "outcome": terminal.outcome.value,
        "reason": None if terminal.reason is None else str(terminal.reason),
        "activity_accounting_complete": terminal.activity_accounting_complete,
        "unknown_post_marker_activity_possible": terminal.unknown_post_marker_activity_possible,
        "retry_or_resume_allowed": False,
        "candidate_cost_or_paid_execution_authorized": False,
    }


__all__ = [
    "ACTION_STARTED_PATH",
    "APPROVAL_PATH",
    "ATTEMPT_PATH",
    "CHILD_PATH",
    "CONTRACT_PATH",
    "CorrectedParentObservation",
    "FramedChildEnvelope",
    "FramedChildExecution",
    "FramedSuccessorContract",
    "FramedSuccessorError",
    "QUALIFICATION_PATH",
    "RUN_AUTHORIZATION_PATH",
    "STATE_PATH",
    "TERMINAL_PATH",
    "build_approval",
    "build_state_evidence",
    "expected_approval_statement",
    "expected_run_statement",
    "expected_state_statement",
    "load_contract",
    "materialize_contract",
    "qualify_source",
    "record_approval",
    "record_state",
    "run_framed_diagnostic_child",
    "run_once",
    "run_parent_preflight",
    "validate_attempt_chain",
    "validate_source_qualification",
]
