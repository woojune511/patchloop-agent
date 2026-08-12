"""Offline-qualified v7 parent integration for sanitized SDK diagnostics.

Import and source-validation paths perform no Docker, dotenv, SDK, network,
provider, evaluator, or agent observation.  Runtime functions remain inert
until a fresh v7 state artifact and exact approval exist.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from patchloop.contracts import FrozenStrictModel
from patchloop.errors import ContractError
from patchloop.evals import d137_no_call_preflight as d137
from patchloop.evals import no_start_executable_preflight as v5
from patchloop.evals import sanitized_sdk_diagnostic_successor as v6
from patchloop.evals import versioned_no_call_preflight as v1
from patchloop.util import sha256_bytes, sha256_json

CONTRACT_SCHEMA_VERSION = "sanitized-sdk-parent-integration-contract-v7"
CONTRACT_VERSION = "ac-evaluator-v2-sanitized-sdk-parent-integration-v7"
CONTRACT_PATH = Path("experiments/evaluator-v2-sanitized-sdk-parent-integration-v7.contract.json")
RUNTIME_PATH = Path("patchloop/evals/sanitized_sdk_parent_integration.py")
BUILD_SCRIPT_PATH = Path("scripts/build_sanitized_sdk_parent_integration.py")
TEST_PATH = Path("tests/test_sanitized_sdk_parent_integration.py")

SOURCE_PARENT_COMMIT = "f48db03a12b3274c047a01e2cc626395812f1f53"
V6_SOURCE_COMMIT = "1d99a7c0acf20ec961240f33f585553fd881dc02"
V6_QUALIFICATION_COMMIT = "f42fcfdee079bca5f050dc33178ef5316e68c955"
V5_TERMINAL_COMMIT = v6.PREDECESSOR_TERMINAL_COMMIT

QUALIFICATION_SCHEMA_VERSION = "sanitized-sdk-parent-integration-source-qualification-v7"
QUALIFICATION_ID = "ac-evaluator-v2-sanitized-sdk-parent-integration-source-20260812-r1"
QUALIFICATION_STATUS = "OFFLINE_SANITIZED_SDK_PARENT_SOURCE_QUALIFIED_LIVE_CLOSED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-parent-integration-v7-source-qualification.json"
)

STATE_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-sanitized-sdk-parent-integration-v7-state.json"
)
APPROVAL_RECEIPT_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-parent-integration-v7-approval-receipt.json"
)
APPROVAL_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-sanitized-sdk-parent-integration-v7-approval.json"
)
ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-sanitized-sdk-parent-integration-v7-attempt.json"
)
ACTION_STARTED_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-parent-integration-v7-action-started.json"
)
TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-sanitized-sdk-parent-integration-v7-terminal.json"
)

NEXT_GATE = "fresh-v7-state-and-separate-exact-approval"
CHILD_TIMEOUT_SECONDS = 60
CHILD_OUTPUT_LIMIT = 262_144
CHILD_FLAGS = ("-I", "-E", "-s", "-B")
CHILD_ENVIRONMENT = {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
PARENT_ENVIRONMENT_NAMES = ("PYTHONHOME", "PYTHONPATH")
APPROVED_SCOPES = (
    "already-running-docker-read-only-two-snapshot-eight-command-observation",
    "isolated-dotenv-exact-openai-api-key-membership",
    "isolated-sanitized-sdk-fixed-placeholder-reject-dispatch-diagnostic",
)
IDENTITY_ASSURANCE = "current-user-self-attested-not-authenticated-or-signed"

SOURCE_ADDED_PATHS = tuple(
    sorted(path.as_posix() for path in (CONTRACT_PATH, RUNTIME_PATH, BUILD_SCRIPT_PATH, TEST_PATH))
)
SOURCE_FILES = tuple(
    sorted(
        (
            CONTRACT_PATH,
            RUNTIME_PATH,
            BUILD_SCRIPT_PATH,
            TEST_PATH,
            v6.CONTRACT_PATH,
            v6.RUNTIME_PATH,
            v6.CHILD_PATH,
            v6.QUALIFICATION_PATH,
            v5.TERMINAL_PATH,
            v5.D137_PATH,
        ),
        key=lambda item: item.as_posix(),
    )
)


class ChildExecutionCode(StrEnum):
    PARENT_PRESENCE_ERROR = "parent_presence_error"
    PARENT_PYTHON_ENVIRONMENT_NOT_CLEAN = "parent_python_environment_not_clean"
    CHILD_BINDING_ERROR = "child_binding_error"
    CHILD_LAUNCH_ERROR = "child_launch_error"
    CHILD_NONZERO_EXIT = "child_nonzero_exit"
    CHILD_STDERR_NOT_EMPTY = "child_stderr_not_empty"
    CHILD_OUTPUT_LIMIT = "child_output_limit"
    CHILD_OUTPUT_INVALID = "child_output_invalid"
    PARENT_CHILD_OBSERVER_ERROR = "parent_child_observer_error"


class ParentState(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"
    ERROR = "error"


class ParentReason(StrEnum):
    DOCKER_NOT_READY = "docker_not_ready"
    PARENT_PYTHON_ENVIRONMENT_NOT_CLEAN = "parent_python_environment_not_clean"
    CHILD_CHECKER_ERROR = "child_checker_error"
    DOTENV_NOT_READY = "dotenv_not_ready"
    SDK_DIAGNOSTIC_BLOCKED = "sdk_diagnostic_blocked"
    SDK_DIAGNOSTIC_ERROR = "sdk_diagnostic_error"
    DOCKER_CHECKER_ERROR = "docker_checker_error"


class SanitizedSDKParentError(ContractError):
    """The v7 parent integration contract failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SanitizedSDKParentError(message)


def _root(repository: str | Path | None) -> Path:
    return v5._repo_root(repository)


def _read(root: Path, path: Path) -> bytes:
    return v5._read_bytes(root, path)


def _canonical(value: FrozenStrictModel) -> bytes:
    return v5._canonical_bytes(value)


def _hash_body(body: dict[str, Any]) -> str:
    return v5._semantic_hash(body)


def _derived_id(prefix: str, content_hash: str) -> str:
    return v5._derived_id(prefix, content_hash)


def _utc(value: datetime, *, label: str) -> datetime:
    return v5._utc(value, label=label)


class V6SourceBinding(FrozenStrictModel):
    source_commit: Literal["1d99a7c0acf20ec961240f33f585553fd881dc02"] = V6_SOURCE_COMMIT
    qualification_commit: Literal["f42fcfdee079bca5f050dc33178ef5316e68c955"] = (
        V6_QUALIFICATION_COMMIT
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    child_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v5_terminal_id: str = Field(pattern=r"^ncpterminal_[0-9a-f]{64}$")
    v5_retry_or_resume_allowed: Literal[False] = False


class ParentRuntimeProfile(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-parent-runtime-profile-v1"] = (
        "sanitized-sdk-parent-runtime-profile-v1"
    )
    docker_observer_path: Literal["patchloop/evals/d137_no_call_preflight.py"] = (
        v5.D137_PATH.as_posix()
    )
    docker_observer_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    docker_expected_command_count: Literal[8] = 8
    child_path: Literal["scripts/run_sanitized_sdk_diagnostic_child.py"] = v6.CHILD_PATH.as_posix()
    child_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    child_flags: tuple[str, ...] = CHILD_FLAGS
    child_environment: dict[str, str] = CHILD_ENVIRONMENT
    child_timeout_seconds: Literal[60] = CHILD_TIMEOUT_SECONDS
    child_output_limit: Literal[262144] = CHILD_OUTPUT_LIMIT
    parent_environment_names: tuple[str, ...] = PARENT_ENVIRONMENT_NAMES
    dotenv_bytes_confined_to_child: Literal[True] = True
    credential_value_hash_prefix_or_length_limit: Literal[0] = 0
    exception_message_type_repr_or_traceback_limit: Literal[0] = 0
    docker_start_pull_load_or_container_operation_limit: Literal[0] = 0
    transport_dispatch_limit: Literal[0] = 0
    network_call_limit: Literal[0] = 0
    provider_evaluator_agent_call_limit: Literal[0] = 0
    exact_child_execution_codes: tuple[str, ...] = tuple(item.value for item in ChildExecutionCode)
    exact_parent_terminal_reasons: tuple[str, ...] = tuple(item.value for item in ParentReason)
    parent_observer_integration_implemented: Literal[True] = True
    one_use_lifecycle_implemented: Literal[True] = True

    @model_validator(mode="after")
    def validate_literals(self) -> ParentRuntimeProfile:
        if self.child_flags != CHILD_FLAGS:
            raise ValueError("v7 isolated child flags drifted")
        if self.child_environment != CHILD_ENVIRONMENT:
            raise ValueError("v7 isolated child environment drifted")
        if self.parent_environment_names != PARENT_ENVIRONMENT_NAMES:
            raise ValueError("v7 parent environment subjects drifted")
        if self.exact_child_execution_codes != tuple(item.value for item in ChildExecutionCode):
            raise ValueError("v7 child execution codes drifted")
        if self.exact_parent_terminal_reasons != tuple(item.value for item in ParentReason):
            raise ValueError("v7 parent reasons drifted")
        return self


class SourceAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    source_qualification_authorized: Literal[True] = True
    state_change_evidence_creation_authorized: Literal[False] = False
    exact_approval_required: Literal[True] = True
    external_preflight_attempt_authorized: Literal[False] = False
    docker_sdk_or_dotenv_observation_authorized: Literal[False] = False
    network_or_transport_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False
    automatic_retry_replacement_or_resume_authorized: Literal[False] = False


class ParentIntegrationContract(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-parent-integration-contract-v7"] = (
        CONTRACT_SCHEMA_VERSION
    )
    contract_version: Literal["ac-evaluator-v2-sanitized-sdk-parent-integration-v7"] = (
        CONTRACT_VERSION
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    v6: V6SourceBinding
    runtime_profile: ParentRuntimeProfile
    transition_policy: v1.PreflightTransitionPolicy
    fresh_state_required: Literal[True] = True
    v5_state_or_approval_reuse_allowed: Literal[False] = False
    current_manual_start_and_dotenv_reconfirmation_required: Literal[True] = True
    source_authority: SourceAuthority
    next_gate: Literal["fresh-v7-state-and-separate-exact-approval"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> ParentIntegrationContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected = sha256_json(body)
        if self.content_hash != expected:
            raise ValueError("v7 contract hash mismatch")
        if self.contract_id != _derived_id("ncpcontract", expected):
            raise ValueError("v7 contract id mismatch")
        return self


class SourceCommitBinding(FrozenStrictModel):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    parents: tuple[str, ...]
    added_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_exact_source(self) -> SourceCommitBinding:
        if self.parents != (SOURCE_PARENT_COMMIT,):
            raise ValueError("v7 source parent drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v7 source additions drifted")
        return self


class QualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    source_qualified: Literal[True] = True
    state_approval_attempt_or_terminal_created: Literal[False] = False
    docker_sdk_dotenv_network_or_provider_observation_count: Literal[0] = 0
    external_mutation_count: Literal[0] = 0
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class SourceQualification(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-parent-integration-source-qualification-v7"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal[
        "ac-evaluator-v2-sanitized-sdk-parent-integration-source-20260812-r1"
    ] = QUALIFICATION_ID
    status: Literal["OFFLINE_SANITIZED_SDK_PARENT_SOURCE_QUALIFIED_LIVE_CLOSED"] = (
        QUALIFICATION_STATUS
    )
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[v5.CommittedFileBinding, ...]
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    contract_file: v5.CommittedFileBinding
    runtime_file: v5.CommittedFileBinding
    v6_qualification_file: v5.CommittedFileBinding
    authority: QualificationAuthority
    next_gate: Literal["fresh-v7-state-and-separate-exact-approval"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v7 qualification time must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> SourceQualification:
        expected_paths = tuple(path.as_posix() for path in SOURCE_FILES)
        if tuple(item.path for item in self.source_files) != expected_paths:
            raise ValueError("v7 qualification inventory drifted")
        by_path = {item.path: item for item in self.source_files}
        for projection, path in (
            (self.contract_file, CONTRACT_PATH),
            (self.runtime_file, RUNTIME_PATH),
            (self.v6_qualification_file, v6.QUALIFICATION_PATH),
        ):
            if projection != by_path.get(path.as_posix()):
                raise ValueError("v7 qualification projection drifted")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != sha256_json(body):
            raise ValueError("v7 qualification hash mismatch")
        return self


class DotenvCode(StrEnum):
    MISSING = "dotenv_missing"
    STAT_ERROR = "dotenv_stat_error"
    NOT_REGULAR_FILE = "dotenv_not_regular_file"
    SIZE_LIMIT = "dotenv_size_limit"
    READ_ERROR = "dotenv_read_error"
    CHANGED_DURING_READ = "dotenv_changed_during_read"
    NOT_UTF8 = "dotenv_not_utf8"
    LINE_LIMIT = "dotenv_line_limit"
    DUPLICATE_SUBJECT = "dotenv_duplicate_subject"
    PARSE_ERROR = "dotenv_parse_error"
    PATH_ESCAPE = "dotenv_path_escape"
    SUBJECT_EMPTY = "dotenv_subject_empty"
    PARSER_IMPORT_ERROR = "dotenv_parser_import_error"
    DIAGNOSTIC_RUNTIME_IMPORT_ERROR = "diagnostic_runtime_import_error"
    ISOLATED_DIAGNOSTIC_ERROR = "isolated_diagnostic_error"


class DotenvObservation(FrozenStrictModel):
    file_present: bool
    exact_subject_declared: bool
    exact_subject_nonempty: bool
    duplicate_subject: bool
    error_code: DotenvCode | None = None
    raw_value_returned: Literal[False] = False
    value_hash_prefix_or_length_returned: Literal[False] = False


class ChildActivity(FrozenStrictModel):
    dotenv_file_read_count: int = Field(ge=0, le=1)
    dotenv_subject_membership_check_count: int = Field(ge=0, le=1)
    credential_assignment_parse_count: int = Field(ge=0, le=2)
    credential_value_return_count: Literal[0] = 0
    credential_value_hash_prefix_or_length_count: Literal[0] = 0
    exception_message_type_repr_or_traceback_return_count: Literal[0] = 0
    transport_dispatch_count: int = Field(ge=0, le=1)
    network_call_count: Literal[0] = 0
    provider_evaluator_agent_call_count: Literal[0] = 0


class IsolatedDiagnosticChild(FrozenStrictModel):
    schema_version: Literal["isolated-dotenv-sanitized-sdk-diagnostic-v1"]
    state: Literal["ready", "blocked", "error"]
    dotenv: DotenvObservation
    diagnostic: v6.SanitizedSDKDiagnostic | None = None
    error_code: DotenvCode | v6.SDKDiagnosticCode | None = None
    activity: ChildActivity
    raw_credential_value_returned: Literal[False] = False
    credential_hash_prefix_or_length_returned: Literal[False] = False
    exception_message_type_repr_or_traceback_returned: Literal[False] = False

    @model_validator(mode="after")
    def validate_semantics(self) -> IsolatedDiagnosticChild:
        if self.diagnostic is None:
            if self.state == "ready" or self.error_code is None:
                raise ValueError("v7 child without diagnostic differs")
        else:
            if self.state != self.diagnostic.state:
                raise ValueError("v7 child diagnostic state differs")
            expected = None if self.state == "ready" else self.diagnostic.code.value
            if self.error_code != expected:
                raise ValueError("v7 child diagnostic code differs")
            if (
                self.activity.transport_dispatch_count
                != self.diagnostic.activity.transport_dispatch_count
            ):
                raise ValueError("v7 child diagnostic activity differs")
        if self.state == "ready" and (
            not self.dotenv.exact_subject_nonempty or self.dotenv.error_code is not None
        ):
            raise ValueError("v7 ready child lacks dotenv membership")
        return self


class ChildExecution(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-child-execution-v1"] = "sanitized-sdk-child-execution-v1"
    parent_pythonhome_absent: bool
    parent_pythonpath_absent: bool
    launch_attempt_count: int = Field(ge=0, le=1)
    process_returned: bool
    child: IsolatedDiagnosticChild | None = None
    error_code: ChildExecutionCode | None = None
    activity_accounting_complete: bool
    unknown_post_launch_activity_possible: bool
    passed: bool

    @model_validator(mode="after")
    def validate_semantics(self) -> ChildExecution:
        parent_clean = self.parent_pythonhome_absent and self.parent_pythonpath_absent
        if not parent_clean:
            if (
                self.launch_attempt_count != 0
                or self.process_returned
                or self.child is not None
                or self.error_code
                not in {
                    "parent_python_environment_not_clean",
                    "parent_presence_error",
                }
                or not self.activity_accounting_complete
                or self.unknown_post_launch_activity_possible
                or self.passed
            ):
                raise ValueError("v7 dirty parent execution differs")
            return self
        if self.launch_attempt_count == 0:
            if (
                self.process_returned
                or self.child is not None
                or self.error_code
                not in {
                    "child_binding_error",
                    "parent_child_observer_error",
                }
                or self.passed
            ):
                raise ValueError("v7 suppressed child execution differs")
            expected_accounting = self.error_code == "child_binding_error"
            if (
                self.activity_accounting_complete != expected_accounting
                or self.unknown_post_launch_activity_possible == expected_accounting
            ):
                raise ValueError("v7 suppressed child accounting differs")
            return self
        if not self.process_returned:
            if (
                self.child is not None
                or self.error_code != "child_launch_error"
                or self.activity_accounting_complete
                or not self.unknown_post_launch_activity_possible
                or self.passed
            ):
                raise ValueError("v7 unknown child launch differs")
            return self
        if self.child is None:
            if (
                self.error_code is None
                or not self.activity_accounting_complete
                or self.unknown_post_launch_activity_possible
                or self.passed
            ):
                raise ValueError("v7 invalid returned child differs")
            return self
        if (
            self.error_code is not None
            or not self.activity_accounting_complete
            or self.unknown_post_launch_activity_possible
            or self.passed != (self.child.state == "ready")
        ):
            raise ValueError("v7 valid child execution differs")
        return self


class ParentObservation(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-parent-observation-v1"] = (
        "sanitized-sdk-parent-observation-v1"
    )
    state: ParentState
    reason: ParentReason | None = None
    docker_observation: dict[str, Any] | None = None
    child_execution: ChildExecution | None = None
    docker_cli_command_count: int | None = Field(default=None, ge=0, le=8)
    child_launch_attempt_count: int | None = Field(default=None, ge=0, le=1)
    credential_value_hash_prefix_or_length_return_count: Literal[0] = 0
    exception_message_type_repr_or_traceback_return_count: Literal[0] = 0
    network_call_count: Literal[0] = 0
    provider_evaluator_agent_call_count: Literal[0] = 0
    activity_accounting_complete: bool
    unknown_post_marker_activity_possible: bool
    passed: bool

    @model_validator(mode="after")
    def validate_semantics(self) -> ParentObservation:
        if self.docker_observation is None:
            if (
                self.state != ParentState.ERROR
                or self.reason != ParentReason.DOCKER_CHECKER_ERROR
                or self.child_execution is not None
                or self.docker_cli_command_count is not None
                or self.child_launch_attempt_count is not None
                or self.activity_accounting_complete
                or not self.unknown_post_marker_activity_possible
                or self.passed
            ):
                raise ValueError("v7 Docker-error observation differs")
            return self
        try:
            d137.validate_d137_docker_no_call_preflight_observation(self.docker_observation)
        except ContractError as exc:
            raise ValueError("v7 Docker observation is invalid") from exc
        count = self.docker_observation["activity"]["docker_cli_command_count"]
        if self.docker_cli_command_count != count:
            raise ValueError("v7 Docker activity projection differs")
        if not self.docker_observation["passed"]:
            if (
                self.state != ParentState.BLOCKED
                or self.reason != ParentReason.DOCKER_NOT_READY
                or self.child_execution is not None
                or self.child_launch_attempt_count != 0
                or not self.activity_accounting_complete
                or self.unknown_post_marker_activity_possible
                or self.passed
            ):
                raise ValueError("v7 Docker-blocked observation differs")
            return self
        if self.child_execution is None:
            raise ValueError("v7 Docker-ready observation lacks child execution")
        if self.child_launch_attempt_count != self.child_execution.launch_attempt_count:
            raise ValueError("v7 child activity projection differs")
        expected_complete = self.child_execution.activity_accounting_complete
        expected_unknown = self.child_execution.unknown_post_launch_activity_possible
        if (
            self.activity_accounting_complete != expected_complete
            or self.unknown_post_marker_activity_possible != expected_unknown
        ):
            raise ValueError("v7 parent accounting projection differs")
        child = self.child_execution.child
        if (
            child is None
            and self.child_execution.error_code == "parent_python_environment_not_clean"
        ):
            expected = (
                ParentState.BLOCKED,
                ParentReason.PARENT_PYTHON_ENVIRONMENT_NOT_CLEAN,
                False,
            )
        elif child is None:
            expected = (ParentState.ERROR, ParentReason.CHILD_CHECKER_ERROR, False)
        elif child.state == "error":
            expected = (ParentState.ERROR, ParentReason.SDK_DIAGNOSTIC_ERROR, False)
        elif child.state == "blocked" and child.diagnostic is None:
            expected = (ParentState.BLOCKED, ParentReason.DOTENV_NOT_READY, False)
        elif child.state == "blocked":
            expected = (ParentState.BLOCKED, ParentReason.SDK_DIAGNOSTIC_BLOCKED, False)
        else:
            expected = (ParentState.READY, None, True)
        if (self.state, self.reason, self.passed) != expected:
            raise ValueError("v7 parent terminal mapping differs")
        return self


class StateEvidence(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-parent-state-evidence-v7"] = (
        "sanitized-sdk-parent-state-evidence-v7"
    )
    evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v5_terminal_id: str = Field(pattern=r"^ncpterminal_[0-9a-f]{64}$")
    v6_source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    change_kind: Literal["fresh-v7-parent-after-consumed-v5"] = "fresh-v7-parent-after-consumed-v5"
    current_manual_docker_start_reported: Literal[True] = True
    current_dotenv_placement_reported: Literal[True] = True
    state_is_user_attested_not_observed: Literal[True] = True
    credential_value_recorded: Literal[False] = False
    external_observation_count: Literal[0] = 0
    external_mutation_count: Literal[0] = 0
    reusable: Literal[False] = False
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        return _utc(value, label="v7 state recorded_at")

    @model_validator(mode="after")
    def validate_identity(self) -> StateEvidence:
        body = self.model_dump(mode="json", exclude={"evidence_id", "content_hash"})
        expected = sha256_json(body)
        if self.content_hash != expected or self.evidence_id != _derived_id("ncpstate", expected):
            raise ValueError("v7 state identity differs")
        return self


class ApprovalReceipt(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-parent-exact-approval-receipt-v7"] = (
        "sanitized-sdk-parent-exact-approval-receipt-v7"
    )
    receipt_id: str = Field(pattern=r"^ncpapprovalreceipt_[0-9a-f]{64}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    current_manual_start_reconfirmed: Literal[True] = True
    current_dotenv_placement_reconfirmed: Literal[True] = True
    attempt_limit: Literal[1] = 1
    credential_value_in_approval: Literal[False] = False
    docker_start_pull_load_or_container_operation_authorized: Literal[False] = False
    network_or_transport_authorized: Literal[False] = False
    provider_evaluator_agent_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False
    retry_replacement_or_resume_authorized: Literal[False] = False
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        return _utc(value, label="v7 approval receipt recorded_at")

    @model_validator(mode="after")
    def validate_identity(self) -> ApprovalReceipt:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("v7 approval scopes drifted")
        body = self.model_dump(mode="json", exclude={"receipt_id", "content_hash"})
        expected = sha256_json(body)
        if self.content_hash != expected or self.receipt_id != _derived_id(
            "ncpapprovalreceipt", expected
        ):
            raise ValueError("v7 approval receipt identity differs")
        return self


class ApprovalBinding(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-parent-approval-binding-v7"] = (
        "sanitized-sdk-parent-approval-binding-v7"
    )
    approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    receipt_id: str = Field(pattern=r"^ncpapprovalreceipt_[0-9a-f]{64}$")
    receipt_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    attempt_limit: Literal[1] = 1
    retry_replacement_or_resume_authorized: Literal[False] = False
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        return _utc(value, label="v7 approval binding recorded_at")

    @model_validator(mode="after")
    def validate_identity(self) -> ApprovalBinding:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("v7 approval binding scopes drifted")
        body = self.model_dump(mode="json", exclude={"approval_id", "content_hash"})
        expected = sha256_json(body)
        if self.content_hash != expected or self.approval_id != _derived_id(
            "ncpapproval", expected
        ):
            raise ValueError("v7 approval binding identity differs")
        return self


class AttemptIntent(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-parent-attempt-v7"] = "sanitized-sdk-parent-attempt-v7"
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    ledger_snapshot_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    attempt_number: Literal[1] = 1
    one_use: Literal[True] = True
    retry_or_resume_allowed: Literal[False] = False
    created_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        return _utc(value, label="v7 attempt created_at")

    @model_validator(mode="after")
    def validate_identity(self) -> AttemptIntent:
        body = self.model_dump(mode="json", exclude={"attempt_id", "content_hash"})
        expected = sha256_json(body)
        if self.content_hash != expected or self.attempt_id != _derived_id("ncpattempt", expected):
            raise ValueError("v7 attempt identity differs")
        return self


class ActionStarted(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-parent-action-started-v7"] = (
        "sanitized-sdk-parent-action-started-v7"
    )
    marker_id: str = Field(pattern=r"^ncpstarted_[0-9a-f]{64}$")
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    attempt_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sequence: Literal[1] = 1
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        return _utc(value, label="v7 action recorded_at")

    @model_validator(mode="after")
    def validate_identity(self) -> ActionStarted:
        body = self.model_dump(mode="json", exclude={"marker_id", "content_hash"})
        expected = sha256_json(body)
        if self.content_hash != expected or self.marker_id != _derived_id("ncpstarted", expected):
            raise ValueError("v7 action identity differs")
        return self


class TerminalTransition(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-parent-terminal-v7"] = "sanitized-sdk-parent-terminal-v7"
    terminal_id: str = Field(pattern=r"^ncpterminal_[0-9a-f]{64}$")
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    action_started_id: str = Field(pattern=r"^ncpstarted_[0-9a-f]{64}$")
    previous_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sequence: Literal[2] = 2
    observation: ParentObservation
    consumed: Literal[True] = True
    retry_or_resume_allowed: Literal[False] = False
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        return _utc(value, label="v7 terminal recorded_at")

    @model_validator(mode="after")
    def validate_identity(self) -> TerminalTransition:
        body = self.model_dump(mode="json", exclude={"terminal_id", "content_hash"})
        expected = sha256_json(body)
        if self.content_hash != expected or self.terminal_id != _derived_id(
            "ncpterminal", expected
        ):
            raise ValueError("v7 terminal identity differs")
        return self


def _load_v6(root: Path) -> tuple[v6.SanitizedDiagnosticContract, v6.SourceQualification]:
    contract = v6.load_contract(repository=root)
    v6.validate_source_qualification(repository=root)
    raw = _read(root, v6.QUALIFICATION_PATH)
    qualification = v6.SourceQualification.model_validate_json(raw)
    _require(
        qualification.source_commit.commit == V6_SOURCE_COMMIT,
        "v6 source identity drifted",
    )
    parents = tuple(
        _git(root, "rev-list", "--parents", "-n", "1", V6_QUALIFICATION_COMMIT)
        .decode("ascii")
        .strip()
        .split()
    )
    _require(
        parents == (V6_QUALIFICATION_COMMIT, V6_SOURCE_COMMIT),
        "v6 qualification commit ancestry drifted",
    )
    _require(
        _git(
            root,
            "show",
            f"{V6_QUALIFICATION_COMMIT}:{v6.QUALIFICATION_PATH.as_posix()}",
        )
        == raw,
        "v6 qualification artifact is not bound to its qualification commit",
    )
    return contract, qualification


def _v6_binding(root: Path) -> V6SourceBinding:
    contract, qualification = _load_v6(root)
    terminal = v5.TerminalTransition.model_validate_json(_read(root, v5.TERMINAL_PATH))
    _require(terminal.terminal_id == v6.PREDECESSOR_TERMINAL_ID, "v5 terminal drifted")
    return V6SourceBinding(
        contract_id=contract.contract_id,
        contract_content_hash=contract.content_hash,
        source_qualification_hash=qualification.content_hash,
        child_file_sha256=sha256_bytes(_read(root, v6.CHILD_PATH)),
        runtime_file_sha256=sha256_bytes(_read(root, v6.RUNTIME_PATH)),
        v5_terminal_id=terminal.terminal_id,
    )


def _build_contract(root: Path) -> ParentIntegrationContract:
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "v6": _v6_binding(root).model_dump(mode="json"),
        "runtime_profile": ParentRuntimeProfile(
            docker_observer_file_sha256=sha256_bytes(_read(root, v5.D137_PATH)),
            child_file_sha256=sha256_bytes(_read(root, v6.CHILD_PATH)),
        ).model_dump(mode="json"),
        "transition_policy": v1.PreflightTransitionPolicy().model_dump(mode="json"),
        "fresh_state_required": True,
        "v5_state_or_approval_reuse_allowed": False,
        "current_manual_start_and_dotenv_reconfirmation_required": True,
        "source_authority": SourceAuthority().model_dump(mode="json"),
        "next_gate": NEXT_GATE,
    }
    content_hash = _hash_body(body)
    return ParentIntegrationContract(
        **body,
        contract_id=_derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def load_contract(*, repository: str | Path | None = None) -> ParentIntegrationContract:
    root = _root(repository)
    raw = _read(root, CONTRACT_PATH)
    try:
        value = ParentIntegrationContract.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise SanitizedSDKParentError("v7 contract artifact is invalid") from exc
    _require(raw == _canonical(value), "v7 contract bytes are not canonical")
    _require(value == _build_contract(root), "v7 contract has drifted")
    return value


def materialize_contract(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _root(repository)
    target = v5._logical_path(root, CONTRACT_PATH, must_exist=False)
    if target.exists():
        value = load_contract(repository=root)
        raw = _read(root, CONTRACT_PATH)
    else:
        value = _build_contract(root)
        raw = _canonical(value)
        v5._write_once(root, CONTRACT_PATH, raw)
    return {
        "status": "OFFLINE_SANITIZED_SDK_PARENT_CONTRACT_MATERIALIZED_LIVE_CLOSED",
        "contract_id": value.contract_id,
        "contract_content_hash": value.content_hash,
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
    }


def _git(root: Path, *args: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            shell=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SanitizedSDKParentError("local Git source read failed") from exc
    _require(completed.returncode == 0, "local Git source read failed")
    return completed.stdout


def _source_commit(root: Path, selected: str) -> SourceCommitBinding:
    commit = _git(root, "rev-parse", f"{selected}^{{commit}}").decode("ascii").strip()
    tree = _git(root, "rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    row = _git(root, "rev-list", "--parents", "-n", "1", commit).decode("ascii").split()
    _require(row and row[0] == commit and len(row) == 2, "v7 source parent binding failed")
    lines = (
        _git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", row[1], commit)
        .decode("utf-8")
        .splitlines()
    )
    added = tuple(sorted(parts[1] for line in lines if (parts := line.split("\t"))[:1] == ["A"]))
    _require(len(lines) == len(added), "v7 source commit contains non-addition changes")
    return SourceCommitBinding(commit=commit, tree=tree, parents=(row[1],), added_paths=added)


def _build_qualification(
    root: Path, *, source_commit: str, recorded_at: datetime
) -> SourceQualification:
    contract = load_contract(repository=root)
    commit = _source_commit(root, source_commit)
    pairs = tuple(v5._committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(item[0] for item in pairs)
    by_path = {item.path: item for item in files}
    contract_index = SOURCE_FILES.index(CONTRACT_PATH)
    _require(
        pairs[contract_index][1] == _canonical(contract),
        "committed v7 contract differs",
    )
    body = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": QUALIFICATION_STATUS,
        "recorded_at": recorded_at,
        "source_commit": commit.model_dump(mode="json"),
        "source_files": tuple(item.model_dump(mode="json") for item in files),
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "contract_file": by_path[CONTRACT_PATH.as_posix()].model_dump(mode="json"),
        "runtime_file": by_path[RUNTIME_PATH.as_posix()].model_dump(mode="json"),
        "v6_qualification_file": by_path[v6.QUALIFICATION_PATH.as_posix()].model_dump(mode="json"),
        "authority": QualificationAuthority().model_dump(mode="json"),
        "next_gate": NEXT_GATE,
    }
    return SourceQualification(**body, content_hash=_hash_body(body))


def qualify_source(
    *, source_commit: str = "HEAD", repository: str | Path | None = None
) -> dict[str, Any]:
    root = _root(repository)
    target = v5._logical_path(root, QUALIFICATION_PATH, must_exist=False)
    if not target.exists():
        value = _build_qualification(
            root, source_commit=source_commit, recorded_at=datetime.now(UTC)
        )
        v5._write_once(root, QUALIFICATION_PATH, _canonical(value))
    return validate_source_qualification(repository=root)


def validate_source_qualification(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _root(repository)
    raw = _read(root, QUALIFICATION_PATH)
    try:
        value = SourceQualification.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise SanitizedSDKParentError("v7 source qualification is invalid") from exc
    _require(raw == _canonical(value), "v7 qualification bytes are not canonical")
    expected = _build_qualification(
        root,
        source_commit=value.source_commit.commit,
        recorded_at=value.recorded_at,
    )
    _require(value == expected, "v7 source qualification has drifted")
    return {
        "status": value.status,
        "qualification_id": value.qualification_id,
        "source_commit": value.source_commit.commit,
        "source_tree": value.source_commit.tree,
        "contract_id": value.contract_id,
        "contract_content_hash": value.contract_content_hash,
        "source_qualification_hash": value.content_hash,
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
    }


RunCallable = Callable[..., subprocess.CompletedProcess[bytes]]


def _child_execution_error(
    *,
    pythonhome_absent: bool,
    pythonpath_absent: bool,
    launch_attempt_count: int,
    process_returned: bool,
    code: str,
    complete: bool,
    unknown: bool,
) -> ChildExecution:
    return ChildExecution(
        parent_pythonhome_absent=pythonhome_absent,
        parent_pythonpath_absent=pythonpath_absent,
        launch_attempt_count=launch_attempt_count,
        process_returned=process_returned,
        error_code=code,
        activity_accounting_complete=complete,
        unknown_post_launch_activity_possible=unknown,
        passed=False,
    )


def run_isolated_diagnostic_child(
    contract: ParentIntegrationContract,
    *,
    repository: str | Path | None = None,
    environment_present: Callable[[str], bool] | None = None,
    run: RunCallable = subprocess.run,
) -> ChildExecution:
    root = _root(repository)
    present = environment_present or (lambda name: name in os.environ)
    try:
        pythonhome_absent = not present("PYTHONHOME")
        pythonpath_absent = not present("PYTHONPATH")
    except Exception:
        return _child_execution_error(
            pythonhome_absent=False,
            pythonpath_absent=False,
            launch_attempt_count=0,
            process_returned=False,
            code="parent_presence_error",
            complete=True,
            unknown=False,
        )
    if not pythonhome_absent or not pythonpath_absent:
        return _child_execution_error(
            pythonhome_absent=pythonhome_absent,
            pythonpath_absent=pythonpath_absent,
            launch_attempt_count=0,
            process_returned=False,
            code="parent_python_environment_not_clean",
            complete=True,
            unknown=False,
        )
    try:
        validated_contract = ParentIntegrationContract.model_validate(
            contract.model_dump(mode="json")
        )
        _require(
            validated_contract == load_contract(repository=root),
            "v7 runtime contract differs from the checked-in contract",
        )
        child_path = v5._logical_path(root, v6.CHILD_PATH, must_exist=True)
        _require(
            sha256_bytes(_read(root, v6.CHILD_PATH)) == contract.runtime_profile.child_file_sha256,
            "v7 child source differs",
        )
        python = Path(sys.executable).resolve(strict=True)
    except Exception:
        return _child_execution_error(
            pythonhome_absent=True,
            pythonpath_absent=True,
            launch_attempt_count=0,
            process_returned=False,
            code="child_binding_error",
            complete=True,
            unknown=False,
        )
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        completed = run(
            [
                str(python),
                *CHILD_FLAGS,
                str(child_path),
                "--repository",
                str(root),
            ],
            cwd=root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            shell=False,
            timeout=CHILD_TIMEOUT_SECONDS,
            env=dict(CHILD_ENVIRONMENT),
            creationflags=creationflags,
        )
    except Exception:
        return _child_execution_error(
            pythonhome_absent=True,
            pythonpath_absent=True,
            launch_attempt_count=1,
            process_returned=False,
            code="child_launch_error",
            complete=False,
            unknown=True,
        )
    if completed.returncode != 0:
        code = "child_nonzero_exit"
    elif completed.stderr:
        code = "child_stderr_not_empty"
    elif len(completed.stdout) > CHILD_OUTPUT_LIMIT:
        code = "child_output_limit"
    else:
        code = None
    if code is not None:
        return _child_execution_error(
            pythonhome_absent=True,
            pythonpath_absent=True,
            launch_attempt_count=1,
            process_returned=True,
            code=code,
            complete=True,
            unknown=False,
        )
    try:
        child = IsolatedDiagnosticChild.model_validate_json(completed.stdout)
    except (ValidationError, UnicodeDecodeError):
        return _child_execution_error(
            pythonhome_absent=True,
            pythonpath_absent=True,
            launch_attempt_count=1,
            process_returned=True,
            code="child_output_invalid",
            complete=True,
            unknown=False,
        )
    return ChildExecution(
        parent_pythonhome_absent=True,
        parent_pythonpath_absent=True,
        launch_attempt_count=1,
        process_returned=True,
        child=child,
        error_code=None,
        activity_accounting_complete=True,
        unknown_post_launch_activity_possible=False,
        passed=child.state == "ready",
    )


def _docker_error_observation() -> ParentObservation:
    return ParentObservation(
        state=ParentState.ERROR,
        reason=ParentReason.DOCKER_CHECKER_ERROR,
        activity_accounting_complete=False,
        unknown_post_marker_activity_possible=True,
        passed=False,
    )


def run_parent_preflight(
    contract: ParentIntegrationContract,
    *,
    repository: str | Path | None = None,
    docker_observer: Callable[
        ..., dict[str, Any]
    ] = d137.run_d137_docker_no_call_preflight_observation,
    child_observer: Callable[..., ChildExecution] = run_isolated_diagnostic_child,
) -> ParentObservation:
    root = _root(repository)
    try:
        docker = docker_observer(repository=root)
        d137.validate_d137_docker_no_call_preflight_observation(docker)
    except Exception:
        return _docker_error_observation()
    count = docker["activity"]["docker_cli_command_count"]
    if not docker["passed"]:
        return ParentObservation(
            state=ParentState.BLOCKED,
            reason=ParentReason.DOCKER_NOT_READY,
            docker_observation=docker,
            docker_cli_command_count=count,
            child_launch_attempt_count=0,
            activity_accounting_complete=True,
            unknown_post_marker_activity_possible=False,
            passed=False,
        )
    try:
        observed_child = child_observer(contract, repository=root)
        child_execution = ChildExecution.model_validate(observed_child.model_dump(mode="json"))
    except Exception:
        child_execution = _child_execution_error(
            pythonhome_absent=True,
            pythonpath_absent=True,
            launch_attempt_count=0,
            process_returned=False,
            code="parent_child_observer_error",
            complete=False,
            unknown=True,
        )
    child = child_execution.child
    if child is None and child_execution.error_code == "parent_python_environment_not_clean":
        state, reason, passed = (
            ParentState.BLOCKED,
            ParentReason.PARENT_PYTHON_ENVIRONMENT_NOT_CLEAN,
            False,
        )
    elif child is None:
        state, reason, passed = (
            ParentState.ERROR,
            ParentReason.CHILD_CHECKER_ERROR,
            False,
        )
    elif child.state == "error":
        state, reason, passed = (
            ParentState.ERROR,
            ParentReason.SDK_DIAGNOSTIC_ERROR,
            False,
        )
    elif child.state == "blocked" and child.diagnostic is None:
        state, reason, passed = ParentState.BLOCKED, ParentReason.DOTENV_NOT_READY, False
    elif child.state == "blocked":
        state, reason, passed = (
            ParentState.BLOCKED,
            ParentReason.SDK_DIAGNOSTIC_BLOCKED,
            False,
        )
    else:
        state, reason, passed = ParentState.READY, None, True
    return ParentObservation(
        state=state,
        reason=reason,
        docker_observation=docker,
        child_execution=child_execution,
        docker_cli_command_count=count,
        child_launch_attempt_count=child_execution.launch_attempt_count,
        activity_accounting_complete=child_execution.activity_accounting_complete,
        unknown_post_marker_activity_possible=(
            child_execution.unknown_post_launch_activity_possible
        ),
        passed=passed,
    )


def _load_qualification(root: Path) -> SourceQualification:
    validate_source_qualification(repository=root)
    return SourceQualification.model_validate_json(_read(root, QUALIFICATION_PATH))


def build_state_evidence(
    contract: ParentIntegrationContract,
    qualification: SourceQualification,
    *,
    current_manual_start_reported: bool,
    current_dotenv_placement_reported: bool,
    recorded_at: datetime,
) -> StateEvidence:
    _require(current_manual_start_reported, "v7 state lacks current manual-start report")
    _require(current_dotenv_placement_reported, "v7 state lacks current dotenv report")
    body = {
        "schema_version": "sanitized-sdk-parent-state-evidence-v7",
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "source_qualification_hash": qualification.content_hash,
        "v5_terminal_id": contract.v6.v5_terminal_id,
        "v6_source_qualification_hash": contract.v6.source_qualification_hash,
        "change_kind": "fresh-v7-parent-after-consumed-v5",
        "current_manual_docker_start_reported": True,
        "current_dotenv_placement_reported": True,
        "state_is_user_attested_not_observed": True,
        "credential_value_recorded": False,
        "external_observation_count": 0,
        "external_mutation_count": 0,
        "reusable": False,
        "recorded_at": _utc(recorded_at, label="v7 state recorded_at"),
    }
    content_hash = _hash_body(body)
    return StateEvidence(
        **body,
        evidence_id=_derived_id("ncpstate", content_hash),
        content_hash=content_hash,
    )


def materialize_state_evidence(
    *,
    current_manual_start_reported: bool,
    current_dotenv_placement_reported: bool,
    recorded_at: datetime,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    root = _root(repository)
    _require(
        not v5._logical_path(root, STATE_PATH, must_exist=False).exists(),
        "v7 state already exists",
    )
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    value = build_state_evidence(
        contract,
        qualification,
        current_manual_start_reported=current_manual_start_reported,
        current_dotenv_placement_reported=current_dotenv_placement_reported,
        recorded_at=recorded_at,
    )
    v5._write_once(root, STATE_PATH, _canonical(value))
    return validate_state_evidence(repository=root)


def validate_state_evidence(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _root(repository)
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    raw = _read(root, STATE_PATH)
    value = StateEvidence.model_validate_json(raw)
    _require(raw == _canonical(value), "v7 state bytes are not canonical")
    expected = build_state_evidence(
        contract,
        qualification,
        current_manual_start_reported=True,
        current_dotenv_placement_reported=True,
        recorded_at=value.recorded_at,
    )
    _require(value == expected, "v7 state has drifted")
    return {
        "status": "V7_STATE_RECORDED_APPROVAL_ABSENT",
        "contract_id": contract.contract_id,
        "source_qualification_hash": qualification.content_hash,
        "state_evidence_id": value.evidence_id,
        "state_evidence_content_hash": value.content_hash,
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "approval_or_attempt_created": False,
    }


def _build_approval_receipt(
    contract: ParentIntegrationContract,
    qualification: SourceQualification,
    state: StateEvidence,
    *,
    recorded_at: datetime,
) -> ApprovalReceipt:
    body = {
        "schema_version": "sanitized-sdk-parent-exact-approval-receipt-v7",
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "source_qualification_hash": qualification.content_hash,
        "state_evidence_id": state.evidence_id,
        "state_evidence_content_hash": state.content_hash,
        "approved_scopes": APPROVED_SCOPES,
        "identity_assurance": IDENTITY_ASSURANCE,
        "current_manual_start_reconfirmed": True,
        "current_dotenv_placement_reconfirmed": True,
        "attempt_limit": 1,
        "credential_value_in_approval": False,
        "docker_start_pull_load_or_container_operation_authorized": False,
        "network_or_transport_authorized": False,
        "provider_evaluator_agent_authorized": False,
        "candidate_cost_or_paid_execution_authorized": False,
        "retry_replacement_or_resume_authorized": False,
        "recorded_at": _utc(recorded_at, label="v7 approval recorded_at"),
    }
    content_hash = _hash_body(body)
    return ApprovalReceipt(
        **body,
        receipt_id=_derived_id("ncpapprovalreceipt", content_hash),
        content_hash=content_hash,
    )


def _bind_approval(
    contract: ParentIntegrationContract,
    qualification: SourceQualification,
    state: StateEvidence,
    receipt: ApprovalReceipt,
    *,
    recorded_at: datetime,
) -> ApprovalBinding:
    _require(receipt.state_evidence_id == state.evidence_id, "v7 receipt state differs")
    body = {
        "schema_version": "sanitized-sdk-parent-approval-binding-v7",
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "source_qualification_hash": qualification.content_hash,
        "state_evidence_id": state.evidence_id,
        "state_evidence_content_hash": state.content_hash,
        "receipt_id": receipt.receipt_id,
        "receipt_content_hash": receipt.content_hash,
        "approved_scopes": APPROVED_SCOPES,
        "attempt_limit": 1,
        "retry_replacement_or_resume_authorized": False,
        "recorded_at": _utc(recorded_at, label="v7 approval binding recorded_at"),
    }
    content_hash = _hash_body(body)
    return ApprovalBinding(
        **body,
        approval_id=_derived_id("ncpapproval", content_hash),
        content_hash=content_hash,
    )


def record_exact_approval(
    *,
    exact_contract_id: str,
    exact_source_qualification_hash: str,
    exact_state_evidence_id: str,
    reconfirm_current_manual_start: bool,
    reconfirm_current_dotenv_placement: bool,
    recorded_at: datetime,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    root = _root(repository)
    for path in (APPROVAL_RECEIPT_PATH, APPROVAL_PATH):
        _require(not v5._logical_path(root, path, must_exist=False).exists(), "v7 approval exists")
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    validate_state_evidence(repository=root)
    state = StateEvidence.model_validate_json(_read(root, STATE_PATH))
    _require(exact_contract_id == contract.contract_id, "approval contract differs")
    _require(
        exact_source_qualification_hash == qualification.content_hash,
        "approval qualification differs",
    )
    _require(exact_state_evidence_id == state.evidence_id, "approval state differs")
    _require(reconfirm_current_manual_start, "approval lacks manual-start reconfirmation")
    _require(reconfirm_current_dotenv_placement, "approval lacks dotenv reconfirmation")
    receipt = _build_approval_receipt(contract, qualification, state, recorded_at=recorded_at)
    approval = _bind_approval(contract, qualification, state, receipt, recorded_at=recorded_at)
    v5._write_once(root, APPROVAL_RECEIPT_PATH, _canonical(receipt))
    v5._write_once(root, APPROVAL_PATH, _canonical(approval))
    return validate_exact_approval(repository=root)


def validate_exact_approval(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _root(repository)
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    validate_state_evidence(repository=root)
    state = StateEvidence.model_validate_json(_read(root, STATE_PATH))
    receipt_raw = _read(root, APPROVAL_RECEIPT_PATH)
    approval_raw = _read(root, APPROVAL_PATH)
    receipt = ApprovalReceipt.model_validate_json(receipt_raw)
    approval = ApprovalBinding.model_validate_json(approval_raw)
    _require(receipt_raw == _canonical(receipt), "v7 receipt bytes differ")
    _require(approval_raw == _canonical(approval), "v7 approval bytes differ")
    expected_receipt = _build_approval_receipt(
        contract, qualification, state, recorded_at=receipt.recorded_at
    )
    _require(receipt == expected_receipt, "v7 approval receipt has drifted")
    expected = _bind_approval(
        contract, qualification, state, receipt, recorded_at=approval.recorded_at
    )
    _require(approval == expected, "v7 approval has drifted")
    return {
        "status": "V7_EXACT_APPROVAL_RECORDED_ATTEMPT_NOT_STARTED",
        "contract_id": contract.contract_id,
        "source_qualification_hash": qualification.content_hash,
        "state_evidence_id": state.evidence_id,
        "approval_id": approval.approval_id,
        "attempt_limit": 1,
        "external_observations_made": 0,
        "attempt_started": False,
        "paid_execution_authorized": False,
    }


def _ledger_snapshot(root: Path) -> str:
    rows = []
    for path in (ATTEMPT_PATH, ACTION_STARTED_PATH, TERMINAL_PATH):
        exists = v5._logical_path(root, path, must_exist=False).exists()
        rows.append({"path": path.as_posix(), "exists": exists})
    _require(not any(row["exists"] for row in rows), "v7 attempt ledger is consumed")
    return sha256_json(rows)


def _empty_ledger_hash() -> str:
    return sha256_json(
        [
            {"path": path.as_posix(), "exists": False}
            for path in (ATTEMPT_PATH, ACTION_STARTED_PATH, TERMINAL_PATH)
        ]
    )


def _build_attempt(
    contract: ParentIntegrationContract,
    qualification: SourceQualification,
    state: StateEvidence,
    approval: ApprovalBinding,
    *,
    ledger_snapshot_hash: str,
    created_at: datetime,
) -> AttemptIntent:
    body = {
        "schema_version": "sanitized-sdk-parent-attempt-v7",
        "contract_id": contract.contract_id,
        "source_qualification_hash": qualification.content_hash,
        "state_evidence_id": state.evidence_id,
        "approval_id": approval.approval_id,
        "ledger_snapshot_hash": ledger_snapshot_hash,
        "attempt_number": 1,
        "one_use": True,
        "retry_or_resume_allowed": False,
        "created_at": _utc(created_at, label="v7 attempt created_at"),
    }
    content_hash = _hash_body(body)
    return AttemptIntent(
        **body,
        attempt_id=_derived_id("ncpattempt", content_hash),
        content_hash=content_hash,
    )


def _build_action(attempt: AttemptIntent, *, recorded_at: datetime) -> ActionStarted:
    body = {
        "schema_version": "sanitized-sdk-parent-action-started-v7",
        "attempt_id": attempt.attempt_id,
        "attempt_content_hash": attempt.content_hash,
        "sequence": 1,
        "recorded_at": _utc(recorded_at, label="v7 action recorded_at"),
    }
    content_hash = _hash_body(body)
    return ActionStarted(
        **body,
        marker_id=_derived_id("ncpstarted", content_hash),
        content_hash=content_hash,
    )


def _build_terminal(
    attempt: AttemptIntent,
    action: ActionStarted,
    observation: ParentObservation,
    *,
    recorded_at: datetime,
) -> TerminalTransition:
    body = {
        "schema_version": "sanitized-sdk-parent-terminal-v7",
        "attempt_id": attempt.attempt_id,
        "action_started_id": action.marker_id,
        "previous_content_hash": action.content_hash,
        "sequence": 2,
        "observation": observation.model_dump(mode="json"),
        "consumed": True,
        "retry_or_resume_allowed": False,
        "recorded_at": _utc(recorded_at, label="v7 terminal recorded_at"),
    }
    content_hash = _hash_body(body)
    return TerminalTransition(
        **body,
        terminal_id=_derived_id("ncpterminal", content_hash),
        content_hash=content_hash,
    )


def run_once(
    *,
    repository: str | Path | None = None,
    parent_observer: Callable[..., ParentObservation] = run_parent_preflight,
) -> dict[str, Any]:
    root = _root(repository)
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    state = StateEvidence.model_validate_json(_read(root, STATE_PATH))
    validate_exact_approval(repository=root)
    approval = ApprovalBinding.model_validate_json(_read(root, APPROVAL_PATH))
    attempt = _build_attempt(
        contract,
        qualification,
        state,
        approval,
        ledger_snapshot_hash=_ledger_snapshot(root),
        created_at=datetime.now(UTC),
    )
    v5._write_once(root, ATTEMPT_PATH, _canonical(attempt))
    action = _build_action(attempt, recorded_at=datetime.now(UTC))
    v5._write_once(root, ACTION_STARTED_PATH, _canonical(action))
    try:
        observation = parent_observer(contract, repository=root)
    except Exception:
        observation = _docker_error_observation()
    terminal = _build_terminal(attempt, action, observation, recorded_at=datetime.now(UTC))
    raw = _canonical(terminal)
    _require(b"openai_api_key=" not in raw.lower(), "v7 terminal contains credential assignment")
    _require(b"sk-" not in raw.lower(), "v7 terminal contains credential-like material")
    v5._write_once(root, TERMINAL_PATH, raw)
    return validate_attempt_chain(repository=root)


def validate_attempt_chain(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _root(repository)
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    state = StateEvidence.model_validate_json(_read(root, STATE_PATH))
    approval_summary = validate_exact_approval(repository=root)
    approval = ApprovalBinding.model_validate_json(_read(root, APPROVAL_PATH))
    attempt_raw = _read(root, ATTEMPT_PATH)
    action_raw = _read(root, ACTION_STARTED_PATH)
    terminal_raw = _read(root, TERMINAL_PATH)
    attempt = AttemptIntent.model_validate_json(attempt_raw)
    action = ActionStarted.model_validate_json(action_raw)
    terminal = TerminalTransition.model_validate_json(terminal_raw)
    for label, raw, value in (
        ("attempt", attempt_raw, attempt),
        ("action", action_raw, action),
        ("terminal", terminal_raw, terminal),
    ):
        _require(raw == _canonical(value), f"v7 {label} bytes differ")
    _require(attempt.contract_id == contract.contract_id, "v7 attempt contract differs")
    _require(
        attempt.source_qualification_hash == qualification.content_hash,
        "v7 attempt qualification differs",
    )
    _require(attempt.state_evidence_id == state.evidence_id, "v7 attempt state differs")
    _require(attempt.approval_id == approval.approval_id, "v7 attempt approval differs")
    _require(attempt.ledger_snapshot_hash == _empty_ledger_hash(), "v7 ledger differs")
    _require(action.attempt_id == attempt.attempt_id, "v7 action attempt differs")
    _require(
        terminal.attempt_id == attempt.attempt_id
        and terminal.action_started_id == action.marker_id
        and terminal.previous_content_hash == action.content_hash,
        "v7 terminal chain differs",
    )
    _require(
        terminal.recorded_at >= action.recorded_at >= attempt.created_at,
        "v7 chain chronology differs",
    )
    return {
        "status": "V7_SANITIZED_SDK_PARENT_TERMINAL_VALID",
        "contract_id": contract.contract_id,
        "state_evidence_id": state.evidence_id,
        "approval_id": approval_summary["approval_id"],
        "attempt_id": attempt.attempt_id,
        "action_started_id": action.marker_id,
        "terminal_id": terminal.terminal_id,
        "outcome": terminal.observation.state.value,
        "reason": (
            None if terminal.observation.reason is None else terminal.observation.reason.value
        ),
        "activity_accounting_complete": terminal.observation.activity_accounting_complete,
        "unknown_post_marker_activity_possible": (
            terminal.observation.unknown_post_marker_activity_possible
        ),
        "retry_or_resume_allowed": False,
        "network_calls_made": 0,
        "provider_evaluator_agent_calls_made": 0,
        "paid_execution_authorized": False,
    }


__all__ = [
    "ACTION_STARTED_PATH",
    "APPROVAL_PATH",
    "APPROVAL_RECEIPT_PATH",
    "ATTEMPT_PATH",
    "CONTRACT_PATH",
    "ChildExecution",
    "IsolatedDiagnosticChild",
    "ParentIntegrationContract",
    "ParentObservation",
    "QUALIFICATION_PATH",
    "STATE_PATH",
    "SOURCE_ADDED_PATHS",
    "SOURCE_FILES",
    "SanitizedSDKParentError",
    "SourceQualification",
    "TERMINAL_PATH",
    "build_state_evidence",
    "load_contract",
    "materialize_contract",
    "materialize_state_evidence",
    "qualify_source",
    "record_exact_approval",
    "run_isolated_diagnostic_child",
    "run_once",
    "run_parent_preflight",
    "validate_attempt_chain",
    "validate_exact_approval",
    "validate_source_qualification",
    "validate_state_evidence",
]
