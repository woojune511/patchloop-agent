"""Offline v9 parent successor for the qualified v8 import-bootstrap child.

Source and qualification paths perform no environment, Docker, dotenv, SDK,
network, provider, evaluator, or agent observation.  The runtime callable is
covered only through injected observers until a fresh state and exact approval
exist; this module deliberately exposes no state, approval, attempt, or ledger
entrypoint.
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
from patchloop.evals import sanitized_sdk_import_bootstrap_successor as v8
from patchloop.evals import sanitized_sdk_parent_integration as v7
from patchloop.util import sha256_bytes, sha256_json

CONTRACT_SCHEMA_VERSION = "sanitized-sdk-bootstrap-parent-successor-contract-v9"
CONTRACT_VERSION = "ac-evaluator-v2-sanitized-sdk-bootstrap-parent-successor-v9"
CONTRACT_PATH = Path(
    "experiments/evaluator-v2-sanitized-sdk-bootstrap-parent-successor-v9.contract.json"
)
RUNTIME_PATH = Path("patchloop/evals/sanitized_sdk_bootstrap_parent_successor.py")
BUILD_SCRIPT_PATH = Path("scripts/build_sanitized_sdk_bootstrap_parent_successor.py")
TEST_PATH = Path("tests/test_sanitized_sdk_bootstrap_parent_successor.py")

SOURCE_PARENT_COMMIT = "7d116ac964634952e82875393d0df1302e8478b3"
V8_SOURCE_COMMIT = "701c988f5ef2074f0cadaa06e04e88c3e3ea6f9e"
V8_QUALIFICATION_COMMIT = "bdfed282d21b08f0ebe4002d77679be549c96a4d"

QUALIFICATION_SCHEMA_VERSION = "sanitized-sdk-bootstrap-parent-source-qualification-v9"
QUALIFICATION_ID = "ac-evaluator-v2-sanitized-sdk-bootstrap-parent-source-20260812-r1"
QUALIFICATION_STATUS = "OFFLINE_SANITIZED_SDK_BOOTSTRAP_PARENT_SOURCE_QUALIFIED_LIVE_CLOSED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-bootstrap-parent-v9-source-qualification.json"
)

NEXT_GATE = "fresh-v9-state-and-separate-exact-approval"
CHILD_FLAGS = ("-I", "-E", "-s", "-B")
FIXED_CHILD_ENVIRONMENT = {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
PASSTHROUGH_ENVIRONMENT_NAMES = ("SYSTEMROOT",)
PARENT_CLEAN_ENVIRONMENT_NAMES = ("PYTHONHOME", "PYTHONPATH")
DIAGNOSTIC_CHILD_PATH = v6.CHILD_PATH
BOOTSTRAP_CHILD_PATH = v8.CHILD_PATH
CHILD_TIMEOUT_SECONDS = 60
CHILD_OUTPUT_LIMIT = 262_144

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
            v5.D137_PATH,
            v6.CHILD_PATH,
            v6.RUNTIME_PATH,
            v8.CONTRACT_PATH,
            v8.RUNTIME_PATH,
            v8.CHILD_PATH,
            v8.QUALIFICATION_PATH,
            v7.RUNTIME_PATH,
        ),
        key=lambda item: item.as_posix(),
    )
)


class SanitizedSDKBootstrapParentError(ContractError):
    """The v9 offline parent successor failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SanitizedSDKBootstrapParentError(message)


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
        raise SanitizedSDKBootstrapParentError("local Git source read failed") from exc
    _require(completed.returncode == 0, "local Git source read failed")
    return completed.stdout


class ParentExecutionCode(StrEnum):
    PARENT_PRESENCE_ERROR = "parent_presence_error"
    PARENT_PYTHON_ENVIRONMENT_NOT_CLEAN = "parent_python_environment_not_clean"
    SYSTEMROOT_PRESENCE_ERROR = "systemroot_presence_error"
    SYSTEMROOT_MISSING = "systemroot_missing"
    SYSTEMROOT_EMPTY = "systemroot_empty"
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
    CONTRACT_BINDING_ERROR = "contract_binding_error"
    DOCKER_NOT_READY = "docker_not_ready"
    PARENT_PYTHON_ENVIRONMENT_NOT_CLEAN = "parent_python_environment_not_clean"
    SYSTEMROOT_NOT_READY = "systemroot_not_ready"
    CHILD_CHECKER_ERROR = "child_checker_error"
    DOTENV_NOT_READY = "dotenv_not_ready"
    SDK_DIAGNOSTIC_BLOCKED = "sdk_diagnostic_blocked"
    SDK_DIAGNOSTIC_ERROR = "sdk_diagnostic_error"
    DOCKER_CHECKER_ERROR = "docker_checker_error"


class ChildActivity(FrozenStrictModel):
    parent_environment_membership_check_count: int = Field(ge=0, le=2)
    parent_environment_membership_check_completed_count: int = Field(ge=0, le=2)
    systemroot_membership_check_count: int = Field(ge=0, le=1)
    systemroot_nonempty_check_count: int = Field(ge=0, le=1)
    systemroot_value_passed_to_child_count: int = Field(ge=0, le=1)
    systemroot_value_return_count: Literal[0] = 0
    exception_message_type_repr_or_traceback_return_count: Literal[0] = 0
    child_launch_attempt_count: int = Field(ge=0, le=1)
    child_process_return_count: int = Field(ge=0, le=1)


class ParentChildExecution(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-parent-child-execution-v1"] = (
        "sanitized-sdk-bootstrap-parent-child-execution-v1"
    )
    contract_binding_valid: bool
    parent_pythonhome_absent: bool
    parent_pythonpath_absent: bool
    systemroot_present: bool
    systemroot_nonempty: bool
    child: v7.IsolatedDiagnosticChild | None = None
    code: ParentExecutionCode | None = None
    activity: ChildActivity
    activity_accounting_complete: bool
    unknown_post_launch_activity_possible: bool
    passed: bool

    @model_validator(mode="after")
    def validate_semantics(self) -> ParentChildExecution:
        activity = self.activity
        if activity.child_process_return_count > activity.child_launch_attempt_count:
            raise ValueError("v9 child process accounting differs")
        if not self.contract_binding_valid:
            if (
                self.code != ParentExecutionCode.CHILD_BINDING_ERROR
                or self.parent_pythonhome_absent
                or self.parent_pythonpath_absent
                or self.systemroot_present
                or self.systemroot_nonempty
                or self.child is not None
                or any(
                    (
                        activity.parent_environment_membership_check_count,
                        activity.parent_environment_membership_check_completed_count,
                        activity.systemroot_membership_check_count,
                        activity.systemroot_nonempty_check_count,
                        activity.systemroot_value_passed_to_child_count,
                        activity.child_launch_attempt_count,
                        activity.child_process_return_count,
                    )
                )
                or not self.activity_accounting_complete
                or self.unknown_post_launch_activity_possible
                or self.passed
            ):
                raise ValueError("v9 contract-binding failure projection differs")
            return self
        if self.code == ParentExecutionCode.CHILD_BINDING_ERROR:
            raise ValueError("v9 valid binding cannot report binding error")
        clean = self.parent_pythonhome_absent and self.parent_pythonpath_absent
        if not clean:
            if (
                self.child is not None
                or self.code
                not in {
                    ParentExecutionCode.PARENT_PRESENCE_ERROR,
                    ParentExecutionCode.PARENT_PYTHON_ENVIRONMENT_NOT_CLEAN,
                }
                or activity.parent_environment_membership_check_count not in {1, 2}
                or activity.systemroot_membership_check_count != 0
                or activity.systemroot_nonempty_check_count != 0
                or activity.child_launch_attempt_count != 0
                or activity.child_process_return_count != 0
                or activity.systemroot_value_passed_to_child_count != 0
                or not self.activity_accounting_complete
                or self.unknown_post_launch_activity_possible
                or self.passed
            ):
                raise ValueError("v9 dirty-parent projection differs")
            if self.code == ParentExecutionCode.PARENT_PRESENCE_ERROR:
                if (
                    activity.parent_environment_membership_check_completed_count
                    >= activity.parent_environment_membership_check_count
                ):
                    raise ValueError("v9 parent checker accounting differs")
            elif (
                activity.parent_environment_membership_check_count != 2
                or activity.parent_environment_membership_check_completed_count != 2
            ):
                raise ValueError("v9 dirty-parent membership accounting differs")
            return self
        if (
            activity.parent_environment_membership_check_count != 2
            or activity.parent_environment_membership_check_completed_count != 2
        ):
            raise ValueError("v9 clean-parent membership accounting differs")
        if not self.systemroot_present or not self.systemroot_nonempty:
            if self.code == ParentExecutionCode.SYSTEMROOT_PRESENCE_ERROR:
                if (
                    self.systemroot_present
                    or self.systemroot_nonempty
                    or self.child is not None
                    or activity.systemroot_membership_check_count != 1
                    or activity.systemroot_nonempty_check_count != 0
                    or activity.child_launch_attempt_count != 0
                    or activity.child_process_return_count != 0
                    or activity.systemroot_value_passed_to_child_count != 0
                    or not self.activity_accounting_complete
                    or self.unknown_post_launch_activity_possible
                    or self.passed
                ):
                    raise ValueError("v9 SYSTEMROOT checker projection differs")
                return self
            expected = (
                ParentExecutionCode.SYSTEMROOT_MISSING
                if not self.systemroot_present
                else ParentExecutionCode.SYSTEMROOT_EMPTY
            )
            if (
                self.code != expected
                or self.child is not None
                or activity.systemroot_membership_check_count != 1
                or activity.systemroot_nonempty_check_count != int(self.systemroot_present)
                or activity.child_launch_attempt_count != 0
                or activity.child_process_return_count != 0
                or activity.systemroot_value_passed_to_child_count != 0
                or not self.activity_accounting_complete
                or self.unknown_post_launch_activity_possible
                or self.passed
            ):
                raise ValueError("v9 SYSTEMROOT precondition projection differs")
            return self
        if activity.systemroot_value_passed_to_child_count != activity.child_launch_attempt_count:
            raise ValueError("v9 SYSTEMROOT pass-through accounting differs")
        if (
            activity.systemroot_membership_check_count != 1
            or activity.systemroot_nonempty_check_count != 1
        ):
            raise ValueError("v9 SYSTEMROOT readiness accounting differs")
        if activity.child_launch_attempt_count == 0:
            valid_binding_error = (
                self.code == ParentExecutionCode.CHILD_BINDING_ERROR
                and self.activity_accounting_complete
                and not self.unknown_post_launch_activity_possible
            )
            valid_observer_error = (
                self.code == ParentExecutionCode.PARENT_CHILD_OBSERVER_ERROR
                and not self.activity_accounting_complete
                and self.unknown_post_launch_activity_possible
            )
            if (
                self.child
                or activity.child_process_return_count != 0
                or not (valid_binding_error or valid_observer_error)
                or self.passed
            ):
                raise ValueError("v9 pre-launch binding projection differs")
            return self
        if activity.child_process_return_count == 0:
            if (
                self.code != ParentExecutionCode.CHILD_LAUNCH_ERROR
                or self.child is not None
                or self.activity_accounting_complete
                or not self.unknown_post_launch_activity_possible
                or self.passed
            ):
                raise ValueError("v9 child-launch error projection differs")
            return self
        if self.child is None:
            if (
                self.code
                not in {
                    ParentExecutionCode.CHILD_NONZERO_EXIT,
                    ParentExecutionCode.CHILD_STDERR_NOT_EMPTY,
                    ParentExecutionCode.CHILD_OUTPUT_LIMIT,
                    ParentExecutionCode.CHILD_OUTPUT_INVALID,
                }
                or activity.child_process_return_count != 1
                or not self.activity_accounting_complete
                or self.unknown_post_launch_activity_possible
                or self.passed
            ):
                raise ValueError("v9 returned child-error projection differs")
            return self
        if (
            self.code is not None
            or activity.child_process_return_count != 1
            or not self.activity_accounting_complete
            or self.unknown_post_launch_activity_possible
            or self.passed != (self.child.state == "ready")
        ):
            raise ValueError("v9 typed child projection differs")
        return self


class ParentObservation(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-parent-observation-v1"] = (
        "sanitized-sdk-bootstrap-parent-observation-v1"
    )
    state: ParentState
    reason: ParentReason | None = None
    docker_observation: dict[str, Any] | None = None
    child_execution: ParentChildExecution | None = None
    docker_cli_command_count: int | None = Field(default=None, ge=0, le=8)
    child_launch_attempt_count: int | None = Field(default=None, ge=0, le=1)
    network_call_count: int | None = Field(default=None, ge=0, le=0)
    provider_evaluator_agent_call_count: int | None = Field(default=None, ge=0, le=0)
    activity_accounting_complete: bool
    unknown_post_marker_activity_possible: bool
    passed: bool

    @model_validator(mode="after")
    def validate_semantics(self) -> ParentObservation:
        if self.docker_observation is None:
            contract_error = self.reason == ParentReason.CONTRACT_BINDING_ERROR
            if (
                self.state != ParentState.ERROR
                or self.reason
                not in {
                    ParentReason.CONTRACT_BINDING_ERROR,
                    ParentReason.DOCKER_CHECKER_ERROR,
                }
                or self.child_execution is not None
                or self.docker_cli_command_count is not None
                or self.child_launch_attempt_count is not None
                or self.network_call_count is not None
                or self.provider_evaluator_agent_call_count is not None
                or self.activity_accounting_complete != contract_error
                or self.unknown_post_marker_activity_possible == contract_error
                or self.passed
            ):
                raise ValueError("v9 Docker-error observation differs")
            return self
        try:
            d137.validate_d137_docker_no_call_preflight_observation(self.docker_observation)
        except ContractError as exc:
            raise ValueError("v9 Docker observation is invalid") from exc
        count = self.docker_observation["activity"]["docker_cli_command_count"]
        if self.docker_cli_command_count != count:
            raise ValueError("v9 Docker activity projection differs")
        if not self.docker_observation["passed"]:
            if (
                self.state != ParentState.BLOCKED
                or self.reason != ParentReason.DOCKER_NOT_READY
                or self.child_execution is not None
                or self.child_launch_attempt_count != 0
                or self.network_call_count != 0
                or self.provider_evaluator_agent_call_count != 0
                or not self.activity_accounting_complete
                or self.unknown_post_marker_activity_possible
                or self.passed
            ):
                raise ValueError("v9 Docker-blocked observation differs")
            return self
        if self.child_execution is None:
            raise ValueError("v9 Docker-ready observation lacks child execution")
        if (
            self.child_launch_attempt_count
            != self.child_execution.activity.child_launch_attempt_count
        ):
            raise ValueError("v9 child activity projection differs")
        if (
            self.activity_accounting_complete != self.child_execution.activity_accounting_complete
            or self.unknown_post_marker_activity_possible
            != self.child_execution.unknown_post_launch_activity_possible
        ):
            raise ValueError("v9 parent accounting projection differs")
        child = self.child_execution.child
        if self.child_execution.unknown_post_launch_activity_possible:
            expected_network = None
            expected_provider = None
        elif child is None:
            expected_network = 0
            expected_provider = 0
        else:
            expected_network = child.activity.network_call_count
            expected_provider = child.activity.provider_evaluator_agent_call_count
        if (
            self.network_call_count != expected_network
            or self.provider_evaluator_agent_call_count != expected_provider
        ):
            raise ValueError("v9 child external activity projection differs")
        if child is None and self.child_execution.code in {
            ParentExecutionCode.PARENT_PYTHON_ENVIRONMENT_NOT_CLEAN,
            ParentExecutionCode.SYSTEMROOT_MISSING,
            ParentExecutionCode.SYSTEMROOT_EMPTY,
        }:
            expected = (
                ParentState.BLOCKED,
                ParentReason.SYSTEMROOT_NOT_READY
                if self.child_execution.code
                in {ParentExecutionCode.SYSTEMROOT_MISSING, ParentExecutionCode.SYSTEMROOT_EMPTY}
                else ParentReason.PARENT_PYTHON_ENVIRONMENT_NOT_CLEAN,
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
            raise ValueError("v9 parent terminal mapping differs")
        return self


class V8SourceBinding(FrozenStrictModel):
    source_commit: Literal["701c988f5ef2074f0cadaa06e04e88c3e3ea6f9e"] = V8_SOURCE_COMMIT
    qualification_commit: Literal["bdfed282d21b08f0ebe4002d77679be549c96a4d"] = (
        V8_QUALIFICATION_COMMIT
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    child_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    parent_runtime_integration_implemented: Literal[False] = False
    state_approval_or_attempt_entrypoint_implemented: Literal[False] = False


class ParentRuntimeProfile(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-parent-runtime-profile-v1"] = (
        "sanitized-sdk-bootstrap-parent-runtime-profile-v1"
    )
    docker_observer_path: Literal["patchloop/evals/d137_no_call_preflight.py"] = (
        v5.D137_PATH.as_posix()
    )
    docker_observer_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    docker_expected_command_count: Literal[8] = 8
    bootstrap_child_path: Literal["scripts/run_sanitized_sdk_import_bootstrap_child.py"] = (
        BOOTSTRAP_CHILD_PATH.as_posix()
    )
    bootstrap_child_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    diagnostic_child_path: Literal["scripts/run_sanitized_sdk_diagnostic_child.py"] = (
        DIAGNOSTIC_CHILD_PATH.as_posix()
    )
    diagnostic_child_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    child_flags: tuple[str, ...] = CHILD_FLAGS
    fixed_child_environment: dict[str, str] = FIXED_CHILD_ENVIRONMENT
    passthrough_environment_names: tuple[str, ...] = PASSTHROUGH_ENVIRONMENT_NAMES
    parent_clean_environment_names: tuple[str, ...] = PARENT_CLEAN_ENVIRONMENT_NAMES
    child_timeout_seconds: Literal[60] = CHILD_TIMEOUT_SECONDS
    child_output_limit: Literal[262144] = CHILD_OUTPUT_LIMIT
    child_repository_argument_required: Literal[True] = True
    systemroot_value_child_only: Literal[True] = True
    systemroot_value_return_hash_prefix_or_length_limit: Literal[0] = 0
    exception_message_type_repr_or_traceback_limit: Literal[0] = 0
    exact_parent_codes: tuple[str, ...] = tuple(item.value for item in ParentExecutionCode)
    exact_parent_reasons: tuple[str, ...] = tuple(item.value for item in ParentReason)
    future_diagnostic_child_limit: Literal[1] = 1
    future_transport_dispatch_limit: Literal[1] = 1
    future_network_call_limit: Literal[0] = 0
    future_provider_evaluator_agent_call_limit: Literal[0] = 0
    parent_runtime_integration_implemented: Literal[True] = True
    docker_parent_observer_integration_implemented: Literal[True] = True
    injected_observer_tests_only: Literal[True] = True
    one_use_lifecycle_required: Literal[True] = True
    retry_replacement_or_resume_allowed: Literal[False] = False

    @model_validator(mode="after")
    def validate_literals(self) -> ParentRuntimeProfile:
        if self.child_flags != CHILD_FLAGS:
            raise ValueError("v9 child flags drifted")
        if self.fixed_child_environment != FIXED_CHILD_ENVIRONMENT:
            raise ValueError("v9 fixed child environment drifted")
        if self.passthrough_environment_names != PASSTHROUGH_ENVIRONMENT_NAMES:
            raise ValueError("v9 pass-through environment drifted")
        if self.parent_clean_environment_names != PARENT_CLEAN_ENVIRONMENT_NAMES:
            raise ValueError("v9 parent cleanliness subjects drifted")
        if self.exact_parent_codes != tuple(item.value for item in ParentExecutionCode):
            raise ValueError("v9 parent codes drifted")
        if self.exact_parent_reasons != tuple(item.value for item in ParentReason):
            raise ValueError("v9 parent reasons drifted")
        return self


class TransitionPolicy(FrozenStrictModel):
    fresh_state_required: Literal[True] = True
    state_change_evidence_reusable: Literal[False] = False
    separate_exact_approval_required: Literal[True] = True
    approval_attempt_limit: Literal[1] = 1
    action_started_before_observation_required: Literal[True] = True
    terminal_consumes_attempt: Literal[True] = True
    retry_replacement_or_resume_allowed: Literal[False] = False
    consumed_v7_artifact_reuse_allowed: Literal[False] = False


class SourceAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    source_qualification_authorized: Literal[True] = True
    runtime_execution_authorized: Literal[False] = False
    state_approval_attempt_or_terminal_creation_authorized: Literal[False] = False
    environment_docker_dotenv_sdk_or_network_observation_authorized: Literal[False] = False
    systemroot_value_recording_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class ParentSuccessorContract(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-parent-successor-contract-v9"] = (
        CONTRACT_SCHEMA_VERSION
    )
    contract_version: Literal["ac-evaluator-v2-sanitized-sdk-bootstrap-parent-successor-v9"] = (
        CONTRACT_VERSION
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor: V8SourceBinding
    runtime_profile: ParentRuntimeProfile
    transition_policy: TransitionPolicy
    source_authority: SourceAuthority
    next_gate: Literal["fresh-v9-state-and-separate-exact-approval"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> ParentSuccessorContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected = sha256_json(body)
        if self.content_hash != expected:
            raise ValueError("v9 contract hash mismatch")
        if self.contract_id != _derived_id("ncpcontract", expected):
            raise ValueError("v9 contract id mismatch")
        return self


class SourceCommitBinding(FrozenStrictModel):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    parents: tuple[str, ...]
    added_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_source(self) -> SourceCommitBinding:
        if self.parents != (SOURCE_PARENT_COMMIT,):
            raise ValueError("v9 source predecessor drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v9 source additions drifted")
        return self


class QualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    source_qualified: Literal[True] = True
    state_approval_attempt_or_terminal_created: Literal[False] = False
    environment_docker_sdk_dotenv_network_or_provider_observation_count: Literal[0] = 0
    external_mutation_count: Literal[0] = 0
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class SourceQualification(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-parent-source-qualification-v9"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal[
        "ac-evaluator-v2-sanitized-sdk-bootstrap-parent-source-20260812-r1"
    ] = QUALIFICATION_ID
    status: Literal["OFFLINE_SANITIZED_SDK_BOOTSTRAP_PARENT_SOURCE_QUALIFIED_LIVE_CLOSED"] = (
        QUALIFICATION_STATUS
    )
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[v5.CommittedFileBinding, ...]
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    contract_file: v5.CommittedFileBinding
    runtime_file: v5.CommittedFileBinding
    predecessor_qualification_file: v5.CommittedFileBinding
    authority: QualificationAuthority
    next_gate: Literal["fresh-v9-state-and-separate-exact-approval"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v9 qualification time must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> SourceQualification:
        expected_paths = tuple(path.as_posix() for path in SOURCE_FILES)
        if tuple(item.path for item in self.source_files) != expected_paths:
            raise ValueError("v9 qualification inventory drifted")
        by_path = {item.path: item for item in self.source_files}
        for projection, path in (
            (self.contract_file, CONTRACT_PATH),
            (self.runtime_file, RUNTIME_PATH),
            (self.predecessor_qualification_file, v8.QUALIFICATION_PATH),
        ):
            if projection != by_path.get(path.as_posix()):
                raise ValueError("v9 qualification projection drifted")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != sha256_json(body):
            raise ValueError("v9 qualification hash mismatch")
        return self


def _load_v8(root: Path) -> tuple[v8.ImportBootstrapContract, v8.SourceQualification]:
    v8.validate_source_qualification(repository=root)
    contract = v8.load_contract(repository=root)
    raw = _read(root, v8.QUALIFICATION_PATH)
    qualification = v8.SourceQualification.model_validate_json(raw)
    _require(raw == _canonical(qualification), "v8 qualification bytes differ")
    _require(
        _git(root, "show", f"{V8_QUALIFICATION_COMMIT}:{v8.QUALIFICATION_PATH.as_posix()}") == raw,
        "v8 qualification is not bound to its commit",
    )
    return contract, qualification


def _predecessor_binding(root: Path) -> V8SourceBinding:
    contract, qualification = _load_v8(root)
    _require(qualification.source_commit.commit == V8_SOURCE_COMMIT, "v8 source commit differs")
    return V8SourceBinding(
        contract_id=contract.contract_id,
        contract_content_hash=contract.content_hash,
        source_qualification_hash=qualification.content_hash,
        runtime_file_sha256=qualification.runtime_file.file_sha256,
        child_file_sha256=qualification.child_file.file_sha256,
    )


def _build_contract(root: Path) -> ParentSuccessorContract:
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "predecessor": _predecessor_binding(root).model_dump(mode="json"),
        "runtime_profile": ParentRuntimeProfile(
            docker_observer_file_sha256=sha256_bytes(_read(root, v5.D137_PATH)),
            bootstrap_child_file_sha256=sha256_bytes(_read(root, BOOTSTRAP_CHILD_PATH)),
            diagnostic_child_file_sha256=sha256_bytes(_read(root, DIAGNOSTIC_CHILD_PATH)),
        ).model_dump(mode="json"),
        "transition_policy": TransitionPolicy().model_dump(mode="json"),
        "source_authority": SourceAuthority().model_dump(mode="json"),
        "next_gate": NEXT_GATE,
    }
    content_hash = _hash_body(body)
    return ParentSuccessorContract(
        **body,
        contract_id=_derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def load_contract(*, repository: str | Path | None = None) -> ParentSuccessorContract:
    root = _root(repository)
    raw = _read(root, CONTRACT_PATH)
    try:
        value = ParentSuccessorContract.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise SanitizedSDKBootstrapParentError("v9 contract artifact is invalid") from exc
    _require(raw == _canonical(value), "v9 contract bytes are not canonical")
    _require(value == _build_contract(root), "v9 contract has drifted")
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
        "status": "OFFLINE_SANITIZED_SDK_BOOTSTRAP_PARENT_CONTRACT_MATERIALIZED_LIVE_CLOSED",
        "contract_id": value.contract_id,
        "contract_content_hash": value.content_hash,
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
    }


EnvironmentPresent = Callable[[str], bool]
EnvironmentValue = Callable[[str], str | None]
RunCallable = Callable[..., subprocess.CompletedProcess[bytes]]


def _runtime_binding(contract: ParentSuccessorContract, *, root: Path) -> tuple[Path, Path]:
    checked = ParentSuccessorContract.model_validate(contract.model_dump(mode="json"))
    _require(checked == load_contract(repository=root), "v9 runtime contract differs")
    child_path = v5._logical_path(root, DIAGNOSTIC_CHILD_PATH, must_exist=True)
    _require(
        sha256_bytes(_read(root, DIAGNOSTIC_CHILD_PATH))
        == contract.runtime_profile.diagnostic_child_file_sha256,
        "v9 child source differs",
    )
    python = Path(sys.executable).resolve(strict=True)
    return child_path, python


def _execution(
    *,
    binding_valid: bool = True,
    pythonhome_absent: bool,
    pythonpath_absent: bool,
    systemroot_present: bool,
    systemroot_nonempty: bool,
    parent_checks: int,
    parent_completed: int,
    systemroot_membership_checks: int,
    systemroot_nonempty_checks: int,
    launch_attempts: int,
    process_returns: int,
    passed_values: int,
    child: v8.ImportBootstrapObservation | None = None,
    code: ParentExecutionCode | None = None,
    complete: bool = True,
    unknown: bool = False,
) -> ParentChildExecution:
    return ParentChildExecution(
        contract_binding_valid=binding_valid,
        parent_pythonhome_absent=pythonhome_absent,
        parent_pythonpath_absent=pythonpath_absent,
        systemroot_present=systemroot_present,
        systemroot_nonempty=systemroot_nonempty,
        child=child,
        code=code,
        activity=ChildActivity(
            parent_environment_membership_check_count=parent_checks,
            parent_environment_membership_check_completed_count=parent_completed,
            systemroot_membership_check_count=systemroot_membership_checks,
            systemroot_nonempty_check_count=systemroot_nonempty_checks,
            systemroot_value_passed_to_child_count=passed_values,
            child_launch_attempt_count=launch_attempts,
            child_process_return_count=process_returns,
        ),
        activity_accounting_complete=complete,
        unknown_post_launch_activity_possible=unknown,
        passed=child is not None and child.state == "ready",
    )


def run_isolated_diagnostic_child(
    contract: ParentSuccessorContract,
    *,
    repository: str | Path | None = None,
    environment_present: EnvironmentPresent | None = None,
    environment_value: EnvironmentValue | None = None,
    run: RunCallable = subprocess.run,
) -> ParentChildExecution:
    """Run the sanitized diagnostic child with v8's bootstrap correction."""

    root = _root(repository)
    try:
        child_path, python = _runtime_binding(contract, root=root)
    except Exception:
        return _execution(
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
            code=ParentExecutionCode.CHILD_BINDING_ERROR,
        )
    present = environment_present or (lambda name: name in os.environ)
    value = environment_value or os.environ.get
    parent_checks = 0
    parent_completed = 0
    pythonhome_absent = False
    pythonpath_absent = False
    try:
        parent_checks += 1
        pythonhome_absent = not present("PYTHONHOME")
        parent_completed += 1
        parent_checks += 1
        pythonpath_absent = not present("PYTHONPATH")
        parent_completed += 1
    except Exception:
        return _execution(
            pythonhome_absent=False,
            pythonpath_absent=False,
            systemroot_present=False,
            systemroot_nonempty=False,
            parent_checks=parent_checks,
            parent_completed=parent_completed,
            systemroot_membership_checks=0,
            systemroot_nonempty_checks=0,
            launch_attempts=0,
            process_returns=0,
            passed_values=0,
            code=ParentExecutionCode.PARENT_PRESENCE_ERROR,
        )
    if not pythonhome_absent or not pythonpath_absent:
        return _execution(
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
            code=ParentExecutionCode.PARENT_PYTHON_ENVIRONMENT_NOT_CLEAN,
        )
    try:
        systemroot = value("SYSTEMROOT")
    except Exception:
        return _execution(
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
            code=ParentExecutionCode.SYSTEMROOT_PRESENCE_ERROR,
        )
    if systemroot is None or systemroot == "":
        return _execution(
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
                ParentExecutionCode.SYSTEMROOT_MISSING
                if systemroot is None
                else ParentExecutionCode.SYSTEMROOT_EMPTY
            ),
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
            env={**FIXED_CHILD_ENVIRONMENT, "SYSTEMROOT": systemroot},
            creationflags=creationflags,
        )
    except Exception:
        return _execution(
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
            code=ParentExecutionCode.CHILD_LAUNCH_ERROR,
            complete=False,
            unknown=True,
        )
    if completed.returncode != 0:
        code = ParentExecutionCode.CHILD_NONZERO_EXIT
    elif completed.stderr:
        code = ParentExecutionCode.CHILD_STDERR_NOT_EMPTY
    elif len(completed.stdout) > CHILD_OUTPUT_LIMIT:
        code = ParentExecutionCode.CHILD_OUTPUT_LIMIT
    else:
        code = None
    if code is not None:
        return _execution(
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
            code=code,
        )
    try:
        child = v7.IsolatedDiagnosticChild.model_validate_json(completed.stdout)
    except (ValidationError, UnicodeDecodeError):
        return _execution(
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
            code=ParentExecutionCode.CHILD_OUTPUT_INVALID,
        )
    return _execution(
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
        child=child,
    )


def _docker_error_observation() -> ParentObservation:
    return ParentObservation(
        state=ParentState.ERROR,
        reason=ParentReason.DOCKER_CHECKER_ERROR,
        activity_accounting_complete=False,
        unknown_post_marker_activity_possible=True,
        passed=False,
    )


def _contract_error_observation() -> ParentObservation:
    return ParentObservation(
        state=ParentState.ERROR,
        reason=ParentReason.CONTRACT_BINDING_ERROR,
        activity_accounting_complete=True,
        unknown_post_marker_activity_possible=False,
        passed=False,
    )


def _child_observer_error() -> ParentChildExecution:
    return _execution(
        pythonhome_absent=True,
        pythonpath_absent=True,
        systemroot_present=True,
        systemroot_nonempty=True,
        parent_checks=2,
        parent_completed=2,
        systemroot_membership_checks=1,
        systemroot_nonempty_checks=1,
        launch_attempts=0,
        process_returns=0,
        passed_values=0,
        code=ParentExecutionCode.PARENT_CHILD_OBSERVER_ERROR,
        complete=False,
        unknown=True,
    )


def run_parent_preflight(
    contract: ParentSuccessorContract,
    *,
    repository: str | Path | None = None,
    docker_observer: Callable[
        ..., dict[str, Any]
    ] = d137.run_d137_docker_no_call_preflight_observation,
    child_observer: Callable[..., ParentChildExecution] = run_isolated_diagnostic_child,
) -> ParentObservation:
    """Compose the existing read-only Docker gate with the corrected child."""

    root = _root(repository)
    try:
        _runtime_binding(contract, root=root)
    except Exception:
        return _contract_error_observation()
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
            network_call_count=0,
            provider_evaluator_agent_call_count=0,
            activity_accounting_complete=True,
            unknown_post_marker_activity_possible=False,
            passed=False,
        )
    try:
        observed_child = child_observer(contract, repository=root)
        child_execution = ParentChildExecution.model_validate(
            observed_child.model_dump(mode="json")
        )
    except Exception:
        child_execution = _child_observer_error()
    child = child_execution.child
    if (
        child is None
        and child_execution.code == ParentExecutionCode.PARENT_PYTHON_ENVIRONMENT_NOT_CLEAN
    ):
        state, reason, passed = (
            ParentState.BLOCKED,
            ParentReason.PARENT_PYTHON_ENVIRONMENT_NOT_CLEAN,
            False,
        )
    elif child is None and child_execution.code in {
        ParentExecutionCode.SYSTEMROOT_MISSING,
        ParentExecutionCode.SYSTEMROOT_EMPTY,
    }:
        state, reason, passed = ParentState.BLOCKED, ParentReason.SYSTEMROOT_NOT_READY, False
    elif child is None:
        state, reason, passed = ParentState.ERROR, ParentReason.CHILD_CHECKER_ERROR, False
    elif child.state == "error":
        state, reason, passed = ParentState.ERROR, ParentReason.SDK_DIAGNOSTIC_ERROR, False
    elif child.state == "blocked" and child.diagnostic is None:
        state, reason, passed = ParentState.BLOCKED, ParentReason.DOTENV_NOT_READY, False
    elif child.state == "blocked":
        state, reason, passed = ParentState.BLOCKED, ParentReason.SDK_DIAGNOSTIC_BLOCKED, False
    else:
        state, reason, passed = ParentState.READY, None, True
    if child_execution.unknown_post_launch_activity_possible:
        network_count = None
        provider_count = None
    elif child is None:
        network_count = 0
        provider_count = 0
    else:
        network_count = child.activity.network_call_count
        provider_count = child.activity.provider_evaluator_agent_call_count
    return ParentObservation(
        state=state,
        reason=reason,
        docker_observation=docker,
        child_execution=child_execution,
        docker_cli_command_count=count,
        child_launch_attempt_count=child_execution.activity.child_launch_attempt_count,
        network_call_count=network_count,
        provider_evaluator_agent_call_count=provider_count,
        activity_accounting_complete=child_execution.activity_accounting_complete,
        unknown_post_marker_activity_possible=(
            child_execution.unknown_post_launch_activity_possible
        ),
        passed=passed,
    )


def _source_commit(root: Path, selected: str) -> SourceCommitBinding:
    commit = _git(root, "rev-parse", f"{selected}^{{commit}}").decode("ascii").strip()
    tree = _git(root, "rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    row = _git(root, "rev-list", "--parents", "-n", "1", commit).decode("ascii").split()
    _require(row and row[0] == commit and len(row) == 2, "v9 source parent binding failed")
    lines = (
        _git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", row[1], commit)
        .decode("utf-8")
        .splitlines()
    )
    added = tuple(sorted(parts[1] for line in lines if (parts := line.split("\t"))[:1] == ["A"]))
    _require(len(lines) == len(added), "v9 source commit contains non-addition changes")
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
    _require(pairs[contract_index][1] == _canonical(contract), "committed v9 contract differs")
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
        "predecessor_qualification_file": by_path[v8.QUALIFICATION_PATH.as_posix()].model_dump(
            mode="json"
        ),
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
        raise SanitizedSDKBootstrapParentError("v9 source qualification is invalid") from exc
    _require(raw == _canonical(value), "v9 qualification bytes are not canonical")
    expected = _build_qualification(
        root, source_commit=value.source_commit.commit, recorded_at=value.recorded_at
    )
    _require(value == expected, "v9 source qualification has drifted")
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


__all__ = [
    "BUILD_SCRIPT_PATH",
    "CHILD_FLAGS",
    "CONTRACT_PATH",
    "FIXED_CHILD_ENVIRONMENT",
    "NEXT_GATE",
    "ParentChildExecution",
    "ParentExecutionCode",
    "ParentSuccessorContract",
    "QUALIFICATION_PATH",
    "RUNTIME_PATH",
    "SOURCE_ADDED_PATHS",
    "SOURCE_FILES",
    "SanitizedSDKBootstrapParentError",
    "SourceQualification",
    "TEST_PATH",
    "load_contract",
    "materialize_contract",
    "qualify_source",
    "run_isolated_diagnostic_child",
    "validate_source_qualification",
]
