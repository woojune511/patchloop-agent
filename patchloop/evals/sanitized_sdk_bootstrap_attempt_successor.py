"""Qualified one-shot lifecycle for the already-bound v11 no-call approval.

Contract materialization and source qualification are offline.  The only live
entrypoint requires a fresh exact statement, writes authorization, attempt and
ACTION_STARTED artifacts before observation, calls the sealed v9 parent once,
then writes one terminal artifact.  No retry, replacement or resume exists.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from patchloop.contracts import FrozenStrictModel
from patchloop.errors import ContractError
from patchloop.evals import sanitized_sdk_bootstrap_approval_successor as v11
from patchloop.evals import sanitized_sdk_bootstrap_parent_successor as v9
from patchloop.util import sha256_bytes

CONTRACT_SCHEMA_VERSION = "sanitized-sdk-bootstrap-attempt-successor-contract-v12"
CONTRACT_VERSION = "ac-evaluator-v2-sanitized-sdk-bootstrap-attempt-v12"
CONTRACT_PATH = Path("experiments/evaluator-v2-sanitized-sdk-bootstrap-attempt-v12.contract.json")
RUNTIME_PATH = Path("patchloop/evals/sanitized_sdk_bootstrap_attempt_successor.py")
BUILD_SCRIPT_PATH = Path("scripts/build_sanitized_sdk_bootstrap_attempt_successor.py")
TEST_PATH = Path("tests/test_sanitized_sdk_bootstrap_attempt_successor.py")

SOURCE_PARENT_COMMIT = "74541b2db480857df4e90b4a6732cda605a08950"
V11_SOURCE_COMMIT = "e1524fbdcffcfc2da04aefdf940cf79d32c71d9d"
V11_QUALIFICATION_COMMIT = "ccd5126aae1c413e474adc12783cbc4c6d1b58ee"
V11_APPROVAL_EVIDENCE_COMMIT = "11058e5d0e0d6bedeb5687869f1ca8eed7c7583d"

QUALIFICATION_SCHEMA_VERSION = "sanitized-sdk-bootstrap-attempt-source-qualification-v12"
QUALIFICATION_ID = "ac-evaluator-v2-sanitized-sdk-bootstrap-attempt-source-20260812-r1"
QUALIFICATION_STATUS = "OFFLINE_V12_ATTEMPT_LIFECYCLE_SOURCE_QUALIFIED_EXACT_RUN_STATEMENT_REQUIRED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-bootstrap-attempt-v12-source-qualification.json"
)
RUN_AUTHORIZATION_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-bootstrap-attempt-v12-run-authorization.json"
)
ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-bootstrap-attempt-v12-attempt-intent.json"
)
ACTION_STARTED_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-bootstrap-attempt-v12-action-started.json"
)
TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-sanitized-sdk-bootstrap-attempt-v12-terminal.json"
)

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
            v11.CONTRACT_PATH,
            v11.RUNTIME_PATH,
            v11.QUALIFICATION_PATH,
            v11.APPROVAL_RECEIPT_PATH,
            v11.APPROVAL_BINDING_PATH,
            v9.CONTRACT_PATH,
            v9.RUNTIME_PATH,
            v9.QUALIFICATION_PATH,
        ),
        key=lambda path: path.as_posix(),
    )
)

APPROVED_RUNTIME = v11.APPROVED_RUNTIME
APPROVED_SCOPES = v11.APPROVED_SCOPES
QUALIFICATION_NEXT_GATE = "fresh-exact-v12-run-statement"
RUN_TEMPLATE = (
    "Contract {contract_id}, source qualification {qualification_hash}, approval {approval_id} "
    "({approval_hash}): authorize exactly one immediate v9 no-call preflight attempt now under "
    "the fixed v12 lifecycle; current Docker-running and repository-root "
    ".env-only-OPENAI_API_KEY report is reconfirmed; append authorization, attempt and "
    "ACTION_STARTED before observation and one terminal after; no credential value recording, "
    "Docker start/pull/load/image-store mutation/container operation, network/transport, "
    "provider/evaluator/agent, candidate/cost/paid execution, retry/replacement/resume."
)


class AttemptSuccessorError(ContractError):
    """The v12 attempt lifecycle failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AttemptSuccessorError(message)


def _utc(value: datetime, *, label: str) -> datetime:
    _require(value.tzinfo is not None, f"{label} must be timezone-aware")
    _require(value.utcoffset() == UTC.utcoffset(value), f"{label} must be UTC")
    return value


class V11ApprovalBinding(FrozenStrictModel):
    source_commit: Literal["e1524fbdcffcfc2da04aefdf940cf79d32c71d9d"] = V11_SOURCE_COMMIT
    qualification_commit: Literal["ccd5126aae1c413e474adc12783cbc4c6d1b58ee"] = (
        V11_QUALIFICATION_COMMIT
    )
    approval_evidence_commit: Literal["11058e5d0e0d6bedeb5687869f1ca8eed7c7583d"] = (
        V11_APPROVAL_EVIDENCE_COMMIT
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_change_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_change_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    receipt_id: str = Field(pattern=r"^ncpapprovalreceipt_[0-9a-f]{64}$")
    receipt_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    receipt_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    approval_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approval_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_runtime: Literal[
        "patchloop.evals.sanitized_sdk_bootstrap_parent_successor.run_parent_preflight"
    ] = APPROVED_RUNTIME
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    attempt_limit: Literal[1] = 1
    approval_reusable: Literal[False] = False
    state_reusable: Literal[False] = False
    attempt_started: Literal[False] = False
    attempt_consumed: Literal[False] = False
    retry_replacement_or_resume_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_scopes(self) -> V11ApprovalBinding:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("v12 predecessor scopes drifted")
        return self


class RuntimeBinding(FrozenStrictModel):
    entrypoint: Literal[
        "patchloop.evals.sanitized_sdk_bootstrap_parent_successor.run_parent_preflight"
    ] = APPROVED_RUNTIME
    source_commit: Literal["8678ce9e4fbae426971a90a2f47ad28b5a431885"] = v11.v10.V9_SOURCE_COMMIT
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    docker_expected_command_count: Literal[8] = 8
    diagnostic_child_limit: Literal[1] = 1
    network_call_limit: Literal[0] = 0
    provider_evaluator_agent_call_limit: Literal[0] = 0
    credential_value_record_limit: Literal[0] = 0

    @model_validator(mode="after")
    def validate_scopes(self) -> RuntimeBinding:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("v12 runtime scopes drifted")
        return self


class AttemptLifecycleRule(FrozenStrictModel):
    schema_version: Literal["attempt-lifecycle-rule-v12"] = "attempt-lifecycle-rule-v12"
    exact_run_statement_required: Literal[True] = True
    run_statement_template: Literal[
        "Contract {contract_id}, source qualification {qualification_hash}, approval {approval_id} "
        "({approval_hash}): authorize exactly one immediate v9 no-call preflight attempt now under "
        "the fixed v12 lifecycle; current Docker-running and repository-root "
        ".env-only-OPENAI_API_KEY report is reconfirmed; append authorization, attempt and "
        "ACTION_STARTED before observation and one terminal after; no credential value recording, "
        "Docker start/pull/load/image-store mutation/container operation, network/transport, "
        "provider/evaluator/agent, candidate/cost/paid execution, retry/replacement/resume."
    ] = RUN_TEMPLATE
    statement_must_follow_source_qualification: Literal[True] = True
    authorization_before_attempt: Literal[True] = True
    attempt_before_action_started: Literal[True] = True
    action_started_before_observation: Literal[True] = True
    terminal_after_observation_required: Literal[True] = True
    attempt_limit: Literal[1] = 1
    retry_replacement_or_resume_allowed: Literal[False] = False
    partial_chain_is_consumed: Literal[True] = True
    credential_value_allowed: Literal[False] = False


class SourceAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    source_qualification_authorized: Literal[True] = True
    exact_run_template_display_authorized: Literal[True] = True
    run_without_fresh_exact_statement_authorized: Literal[False] = False
    execution_during_source_qualification_authorized: Literal[False] = False
    runtime_artifact_creation_during_source_qualification_authorized: Literal[False] = False
    environment_docker_dotenv_sdk_or_network_observation_authorized: Literal[False] = False
    credential_value_recording_authorized: Literal[False] = False
    docker_start_pull_load_image_store_or_container_mutation_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False
    retry_replacement_or_resume_authorized: Literal[False] = False


class AttemptSuccessorContract(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-attempt-successor-contract-v12"] = (
        CONTRACT_SCHEMA_VERSION
    )
    contract_version: Literal["ac-evaluator-v2-sanitized-sdk-bootstrap-attempt-v12"] = (
        CONTRACT_VERSION
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor: V11ApprovalBinding
    runtime: RuntimeBinding
    lifecycle: AttemptLifecycleRule
    authority: SourceAuthority
    future_exact_run_entrypoint_implemented: Literal[True] = True
    execution_currently_authorized: Literal[False] = False
    next_gate: Literal["fresh-exact-v12-run-statement"] = QUALIFICATION_NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> AttemptSuccessorContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected = v11.v10._hash_body(body)
        if self.content_hash != expected:
            raise ValueError("v12 contract hash mismatch")
        if self.contract_id != v11.v10._derived_id("ncpcontract", expected):
            raise ValueError("v12 contract id mismatch")
        return self


class SourceCommitBinding(FrozenStrictModel):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    parents: tuple[str, ...]
    added_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_source(self) -> SourceCommitBinding:
        if self.parents != (SOURCE_PARENT_COMMIT,):
            raise ValueError("v12 source predecessor drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v12 source additions drifted")
        return self


class QualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    source_qualified: Literal[True] = True
    run_authorization_attempt_action_or_terminal_created: Literal[False] = False
    environment_docker_dotenv_sdk_network_or_provider_observation_count: Literal[0] = 0
    external_mutation_count: Literal[0] = 0
    execution_authorized: Literal[False] = False


class SourceQualification(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-attempt-source-qualification-v12"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal[
        "ac-evaluator-v2-sanitized-sdk-bootstrap-attempt-source-20260812-r1"
    ] = QUALIFICATION_ID
    status: Literal[
        "OFFLINE_V12_ATTEMPT_LIFECYCLE_SOURCE_QUALIFIED_EXACT_RUN_STATEMENT_REQUIRED"
    ] = QUALIFICATION_STATUS
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[v11.v10.CommittedFileBinding, ...]
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    predecessor_approval_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authority: QualificationAuthority
    next_gate: Literal["fresh-exact-v12-run-statement"] = QUALIFICATION_NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v12 qualification recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> SourceQualification:
        expected_paths = tuple(path.as_posix() for path in SOURCE_FILES)
        if tuple(item.path for item in self.source_files) != expected_paths:
            raise ValueError("v12 qualification inventory drifted")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != v11.v10._hash_body(body):
            raise ValueError("v12 qualification hash mismatch")
        return self


class RunAuthorization(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-run-authorization-v12"] = (
        "sanitized-sdk-bootstrap-run-authorization-v12"
    )
    authorization_id: str = Field(pattern=r"^ncprunauthorization_[0-9a-f]{64}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    predecessor_approval_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    statement_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_runtime: Literal[
        "patchloop.evals.sanitized_sdk_bootstrap_parent_successor.run_parent_preflight"
    ] = APPROVED_RUNTIME
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    current_state_report_reconfirmed: Literal[True] = True
    run_now_authorized: Literal[True] = True
    attempt_limit: Literal[1] = 1
    one_use: Literal[True] = True
    credential_value_in_statement: Literal[False] = False
    docker_start_pull_load_image_store_or_container_mutation_authorized: Literal[False] = False
    network_or_transport_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False
    retry_replacement_or_resume_authorized: Literal[False] = False
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v12 run authorization recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> RunAuthorization:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("v12 run authorization scopes drifted")
        body = self.model_dump(mode="json", exclude={"authorization_id", "content_hash"})
        expected = v11.v10._hash_body(body)
        if self.content_hash != expected:
            raise ValueError("v12 run authorization hash mismatch")
        if self.authorization_id != v11.v10._derived_id("ncprunauthorization", expected):
            raise ValueError("v12 run authorization id mismatch")
        return self


class AttemptIntent(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-attempt-intent-v12"] = (
        "sanitized-sdk-bootstrap-attempt-intent-v12"
    )
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    source_qualification_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    run_authorization_id: str = Field(pattern=r"^ncprunauthorization_[0-9a-f]{64}$")
    run_authorization_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    ledger_snapshot_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    attempt_number: Literal[1] = 1
    one_use: Literal[True] = True
    retry_or_resume_allowed: Literal[False] = False
    created_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v12 attempt created_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> AttemptIntent:
        body = self.model_dump(mode="json", exclude={"attempt_id", "content_hash"})
        expected = v11.v10._hash_body(body)
        if self.content_hash != expected:
            raise ValueError("v12 attempt hash mismatch")
        if self.attempt_id != v11.v10._derived_id("ncpattempt", expected):
            raise ValueError("v12 attempt id mismatch")
        return self


class ActionStarted(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-action-started-v12"] = (
        "sanitized-sdk-bootstrap-action-started-v12"
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
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v12 action recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> ActionStarted:
        body = self.model_dump(mode="json", exclude={"marker_id", "content_hash"})
        expected = v11.v10._hash_body(body)
        if self.content_hash != expected:
            raise ValueError("v12 action hash mismatch")
        if self.marker_id != v11.v10._derived_id("ncpstarted", expected):
            raise ValueError("v12 action id mismatch")
        return self


class TerminalReason(StrEnum):
    CONTRACT_BINDING_ERROR = "contract_binding_error"
    DOCKER_NOT_READY = "docker_not_ready"
    PARENT_PYTHON_ENVIRONMENT_NOT_CLEAN = "parent_python_environment_not_clean"
    SYSTEMROOT_NOT_READY = "systemroot_not_ready"
    CHILD_CHECKER_ERROR = "child_checker_error"
    DOTENV_NOT_READY = "dotenv_not_ready"
    SDK_DIAGNOSTIC_BLOCKED = "sdk_diagnostic_blocked"
    SDK_DIAGNOSTIC_ERROR = "sdk_diagnostic_error"
    DOCKER_CHECKER_ERROR = "docker_checker_error"
    LIFECYCLE_CHECKER_ERROR = "lifecycle_checker_error"


class TerminalTransition(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-terminal-v12"] = (
        "sanitized-sdk-bootstrap-terminal-v12"
    )
    terminal_id: str = Field(pattern=r"^ncpterminal_[0-9a-f]{64}$")
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    action_started_id: str = Field(pattern=r"^ncpstarted_[0-9a-f]{64}$")
    previous_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sequence: Literal[2] = 2
    outcome: v9.ParentState
    reason: TerminalReason | None = None
    observation: v9.ParentObservation | None = None
    activity_accounting_complete: bool
    unknown_post_marker_activity_possible: bool
    docker_cli_command_count: int | None = Field(default=None, ge=0, le=8)
    sdk_child_start_count: int | None = Field(default=None, ge=0, le=1)
    network_call_count: int | None = Field(default=None, ge=0, le=0)
    provider_evaluator_agent_call_count: int | None = Field(default=None, ge=0, le=0)
    docker_desktop_or_daemon_start_count: Literal[0] = 0
    image_pull_load_or_store_mutation_count: Literal[0] = 0
    container_operation_count: Literal[0] = 0
    credential_value_return_hash_prefix_or_length_count: Literal[0] = 0
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v12 terminal recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_terminal(self) -> TerminalTransition:
        if self.observation is None:
            if (
                self.outcome != v9.ParentState.ERROR
                or self.reason != TerminalReason.LIFECYCLE_CHECKER_ERROR
                or self.activity_accounting_complete
                or not self.unknown_post_marker_activity_possible
                or any(
                    value is not None
                    for value in (
                        self.docker_cli_command_count,
                        self.sdk_child_start_count,
                        self.network_call_count,
                        self.provider_evaluator_agent_call_count,
                    )
                )
            ):
                raise ValueError("v12 lifecycle-error terminal differs")
        else:
            expected_reason = (
                None
                if self.observation.reason is None
                else TerminalReason(self.observation.reason.value)
            )
            if (
                self.outcome != self.observation.state
                or self.reason != expected_reason
                or self.activity_accounting_complete
                != self.observation.activity_accounting_complete
                or self.unknown_post_marker_activity_possible
                != self.observation.unknown_post_marker_activity_possible
                or self.docker_cli_command_count != self.observation.docker_cli_command_count
                or self.sdk_child_start_count != self.observation.child_launch_attempt_count
                or self.network_call_count != self.observation.network_call_count
                or self.provider_evaluator_agent_call_count
                != self.observation.provider_evaluator_agent_call_count
            ):
                raise ValueError("v12 observation terminal projection differs")
        if self.outcome == v9.ParentState.READY and (
            self.observation is None
            or not self.observation.passed
            or self.reason is not None
            or not self.activity_accounting_complete
            or self.unknown_post_marker_activity_possible
        ):
            raise ValueError("v12 READY terminal is incomplete")
        body = self.model_dump(mode="json", exclude={"terminal_id", "content_hash"})
        expected = v11.v10._hash_body(body)
        if self.content_hash != expected:
            raise ValueError("v12 terminal hash mismatch")
        if self.terminal_id != v11.v10._derived_id("ncpterminal", expected):
            raise ValueError("v12 terminal id mismatch")
        return self


def _load_v11_approval(
    root: Path,
) -> tuple[
    v11.ApprovalSuccessorContract,
    v11.SourceQualification,
    v11.UserExactApprovalReceipt,
    v11.ExactApprovalBinding,
    bytes,
    bytes,
]:
    v11.validate_exact_approval(repository=root)
    contract_raw = v11.v10._read(root, v11.CONTRACT_PATH)
    qualification_raw = v11.v10._read(root, v11.QUALIFICATION_PATH)
    receipt_raw = v11.v10._read(root, v11.APPROVAL_RECEIPT_PATH)
    approval_raw = v11.v10._read(root, v11.APPROVAL_BINDING_PATH)
    contract = v11.ApprovalSuccessorContract.model_validate_json(contract_raw)
    qualification = v11.SourceQualification.model_validate_json(qualification_raw)
    receipt = v11.UserExactApprovalReceipt.model_validate_json(receipt_raw)
    approval = v11.ExactApprovalBinding.model_validate_json(approval_raw)
    _require(contract_raw == v11.v10._canonical(contract), "v11 contract bytes differ")
    _require(qualification.source_commit.commit == V11_SOURCE_COMMIT, "v11 source commit differs")
    _require(
        v11.v10._git(
            root,
            "show",
            f"{V11_QUALIFICATION_COMMIT}:{v11.QUALIFICATION_PATH.as_posix()}",
        )
        == qualification_raw,
        "v11 qualification is not bound to its commit",
    )
    for path, raw in (
        (v11.APPROVAL_RECEIPT_PATH, receipt_raw),
        (v11.APPROVAL_BINDING_PATH, approval_raw),
    ):
        _require(
            v11.v10._git(root, "show", f"{V11_APPROVAL_EVIDENCE_COMMIT}:{path.as_posix()}") == raw,
            "v11 approval chain is not bound to its evidence commit",
        )
    _require(approval.attempt_started is False, "v11 approval already started an attempt")
    _require(approval.attempt_consumed is False, "v11 approval is already consumed")
    return contract, qualification, receipt, approval, receipt_raw, approval_raw


def _predecessor_binding(
    root: Path,
) -> tuple[V11ApprovalBinding, v11.ApprovalSuccessorContract]:
    contract, qualification, receipt, approval, receipt_raw, approval_raw = _load_v11_approval(root)
    return (
        V11ApprovalBinding(
            contract_id=contract.contract_id,
            contract_content_hash=contract.content_hash,
            source_qualification_hash=qualification.content_hash,
            state_change_evidence_id=approval.state_change_evidence_id,
            state_change_evidence_content_hash=approval.state_change_evidence_content_hash,
            receipt_id=receipt.receipt_id,
            receipt_content_hash=receipt.content_hash,
            receipt_file_sha256=sha256_bytes(receipt_raw),
            approval_id=approval.approval_id,
            approval_content_hash=approval.content_hash,
            approval_file_sha256=sha256_bytes(approval_raw),
        ),
        contract,
    )


def _runtime_binding(
    contract: v11.ApprovalSuccessorContract,
    predecessor: V11ApprovalBinding,
) -> RuntimeBinding:
    runtime = contract.approved_runtime
    _require(runtime.entrypoint == APPROVED_RUNTIME, "v11 approved runtime differs")
    return RuntimeBinding(
        contract_id=runtime.v9_contract_id,
        contract_content_hash=runtime.v9_contract_content_hash,
        source_qualification_hash=runtime.v9_source_qualification_hash,
        runtime_file_sha256=runtime.v9_runtime_file_sha256,
        approved_scopes=predecessor.approved_scopes,
    )


def _build_contract(root: Path) -> AttemptSuccessorContract:
    predecessor, v11_contract = _predecessor_binding(root)
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "predecessor": predecessor.model_dump(mode="json"),
        "runtime": _runtime_binding(v11_contract, predecessor).model_dump(mode="json"),
        "lifecycle": AttemptLifecycleRule().model_dump(mode="json"),
        "authority": SourceAuthority().model_dump(mode="json"),
        "future_exact_run_entrypoint_implemented": True,
        "execution_currently_authorized": False,
        "next_gate": QUALIFICATION_NEXT_GATE,
    }
    content_hash = v11.v10._hash_body(body)
    return AttemptSuccessorContract(
        **body,
        contract_id=v11.v10._derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def load_contract(*, repository: str | Path | None = None) -> AttemptSuccessorContract:
    root = v11.v10._root(repository)
    raw = v11.v10._read(root, CONTRACT_PATH)
    try:
        value = AttemptSuccessorContract.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise AttemptSuccessorError("v12 contract artifact is invalid") from exc
    _require(raw == v11.v10._canonical(value), "v12 contract bytes are not canonical")
    _require(value == _build_contract(root), "v12 contract has drifted")
    return value


def materialize_contract(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v11.v10._root(repository)
    selected = v11.v10._logical_path(root, CONTRACT_PATH, must_exist=False)
    if selected.exists():
        value = load_contract(repository=root)
        raw = v11.v10._read(root, CONTRACT_PATH)
    else:
        value = _build_contract(root)
        raw = v11.v10._canonical(value)
        v11.v10._write_once(root, CONTRACT_PATH, raw)
    return {
        "status": "OFFLINE_V12_ATTEMPT_LIFECYCLE_CONTRACT_MATERIALIZED_LIVE_CLOSED",
        "contract_id": value.contract_id,
        "contract_content_hash": value.content_hash,
        "predecessor_approval_id": value.predecessor.approval_id,
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "runtime_artifacts_created": False,
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
    }


def _source_commit(root: Path, selected: str) -> SourceCommitBinding:
    commit = v11.v10._git(root, "rev-parse", f"{selected}^{{commit}}").decode("ascii").strip()
    tree = v11.v10._git(root, "rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    row = v11.v10._git(root, "rev-list", "--parents", "-n", "1", commit).decode("ascii").split()
    _require(row and row[0] == commit and len(row) == 2, "v12 source parent binding failed")
    lines = (
        v11.v10._git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", row[1], commit)
        .decode("utf-8")
        .splitlines()
    )
    added = tuple(sorted(parts[1] for line in lines if (parts := line.split("\t"))[:1] == ["A"]))
    _require(len(lines) == len(added), "v12 source commit contains non-addition changes")
    return SourceCommitBinding(commit=commit, tree=tree, parents=(row[1],), added_paths=added)


def _build_qualification(
    root: Path,
    *,
    source_commit: str,
    recorded_at: datetime,
) -> SourceQualification:
    contract = load_contract(repository=root)
    commit = _source_commit(root, source_commit)
    pairs = tuple(v11.v10._committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(pair[0] for pair in pairs)
    contract_index = SOURCE_FILES.index(CONTRACT_PATH)
    _require(
        pairs[contract_index][1] == v11.v10._canonical(contract),
        "committed v12 contract differs",
    )
    body = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": QUALIFICATION_STATUS,
        "recorded_at": _utc(recorded_at, label="v12 qualification recorded_at"),
        "source_commit": commit.model_dump(mode="json"),
        "source_files": tuple(item.model_dump(mode="json") for item in files),
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "predecessor_approval_id": contract.predecessor.approval_id,
        "predecessor_approval_content_hash": contract.predecessor.approval_content_hash,
        "authority": QualificationAuthority().model_dump(mode="json"),
        "next_gate": QUALIFICATION_NEXT_GATE,
    }
    return SourceQualification(**body, content_hash=v11.v10._hash_body(body))


def qualify_source(
    *,
    source_commit: str = "HEAD",
    repository: str | Path | None = None,
) -> dict[str, Any]:
    root = v11.v10._root(repository)
    target = v11.v10._logical_path(root, QUALIFICATION_PATH, must_exist=False)
    if not target.exists():
        value = _build_qualification(
            root,
            source_commit=source_commit,
            recorded_at=datetime.now(UTC),
        )
        raw = v11.v10._canonical(value)
        v11.v10._write_once(root, QUALIFICATION_PATH, raw)
        return _qualification_summary(value, raw)
    return validate_source_qualification(repository=root)


def _qualification_summary(value: SourceQualification, raw: bytes) -> dict[str, Any]:
    return {
        "status": value.status,
        "qualification_id": value.qualification_id,
        "source_commit": value.source_commit.commit,
        "source_tree": value.source_commit.tree,
        "contract_id": value.contract_id,
        "contract_content_hash": value.contract_content_hash,
        "source_qualification_hash": value.content_hash,
        "predecessor_approval_id": value.predecessor_approval_id,
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "runtime_artifacts_created": False,
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
        "next_gate": QUALIFICATION_NEXT_GATE,
    }


def validate_source_qualification(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v11.v10._root(repository)
    raw = v11.v10._read(root, QUALIFICATION_PATH)
    try:
        value = SourceQualification.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise AttemptSuccessorError("v12 source qualification is invalid") from exc
    _require(raw == v11.v10._canonical(value), "v12 qualification bytes are not canonical")
    expected = _build_qualification(
        root,
        source_commit=value.source_commit.commit,
        recorded_at=value.recorded_at,
    )
    _require(value == expected, "v12 source qualification has drifted")
    return _qualification_summary(value, raw)


def _load_qualification(root: Path) -> SourceQualification:
    validate_source_qualification(repository=root)
    return SourceQualification.model_validate_json(v11.v10._read(root, QUALIFICATION_PATH))


def expected_run_statement(
    contract: AttemptSuccessorContract,
    qualification: SourceQualification,
    approval: v11.ExactApprovalBinding,
) -> str:
    contract = AttemptSuccessorContract.model_validate(contract.model_dump(mode="json"))
    qualification = SourceQualification.model_validate(qualification.model_dump(mode="json"))
    approval = v11.ExactApprovalBinding.model_validate(approval.model_dump(mode="json"))
    _require(qualification.contract_id == contract.contract_id, "qualification contract differs")
    _require(
        approval.approval_id == contract.predecessor.approval_id
        and approval.content_hash == contract.predecessor.approval_content_hash,
        "v11 approval differs from v12 contract",
    )
    return RUN_TEMPLATE.format(
        contract_id=contract.contract_id,
        qualification_hash=qualification.content_hash,
        approval_id=approval.approval_id,
        approval_hash=approval.content_hash,
    )


def build_run_authorization(
    contract: AttemptSuccessorContract,
    qualification: SourceQualification,
    approval: v11.ExactApprovalBinding,
    *,
    statement: str,
    recorded_at: datetime,
) -> RunAuthorization:
    expected = expected_run_statement(contract, qualification, approval)
    _require(statement == expected, "fresh v12 run statement differs")
    recorded_at = _utc(recorded_at, label="v12 run authorization recorded_at")
    _require(recorded_at >= qualification.recorded_at, "run statement predates qualification")
    _require(recorded_at >= approval.recorded_at, "run statement predates v11 approval")
    body = {
        "schema_version": "sanitized-sdk-bootstrap-run-authorization-v12",
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "source_qualification_content_hash": qualification.content_hash,
        "predecessor_approval_id": approval.approval_id,
        "predecessor_approval_content_hash": approval.content_hash,
        "statement_sha256": sha256_bytes(statement.encode("utf-8")),
        "approved_runtime": APPROVED_RUNTIME,
        "approved_scopes": APPROVED_SCOPES,
        "current_state_report_reconfirmed": True,
        "run_now_authorized": True,
        "attempt_limit": 1,
        "one_use": True,
        "credential_value_in_statement": False,
        "docker_start_pull_load_image_store_or_container_mutation_authorized": False,
        "network_or_transport_authorized": False,
        "provider_evaluator_agent_execution_authorized": False,
        "candidate_cost_or_paid_execution_authorized": False,
        "retry_replacement_or_resume_authorized": False,
        "recorded_at": recorded_at,
    }
    content_hash = v11.v10._hash_body(body)
    return RunAuthorization(
        **body,
        authorization_id=v11.v10._derived_id("ncprunauthorization", content_hash),
        content_hash=content_hash,
    )


def _ledger_rows(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.as_posix(),
            "exists": v11.v10._logical_path(root, path, must_exist=False).exists(),
        }
        for path in (RUN_AUTHORIZATION_PATH, ATTEMPT_PATH, ACTION_STARTED_PATH, TERMINAL_PATH)
    ]


def _ledger_snapshot(root: Path) -> str:
    rows = _ledger_rows(root)
    _require(not any(row["exists"] for row in rows), "v12 attempt ledger is consumed")
    return v11.v10._hash_body({"rows": rows})


def _empty_ledger_hash() -> str:
    return v11.v10._hash_body(
        {
            "rows": [
                {"path": path.as_posix(), "exists": False}
                for path in (
                    RUN_AUTHORIZATION_PATH,
                    ATTEMPT_PATH,
                    ACTION_STARTED_PATH,
                    TERMINAL_PATH,
                )
            ]
        }
    )


def _build_attempt(
    contract: AttemptSuccessorContract,
    qualification: SourceQualification,
    approval: v11.ExactApprovalBinding,
    authorization: RunAuthorization,
    *,
    ledger_snapshot_hash: str,
    created_at: datetime,
) -> AttemptIntent:
    created_at = _utc(created_at, label="v12 attempt created_at")
    _require(created_at >= authorization.recorded_at, "attempt predates run authorization")
    body = {
        "schema_version": "sanitized-sdk-bootstrap-attempt-intent-v12",
        "contract_id": contract.contract_id,
        "source_qualification_content_hash": qualification.content_hash,
        "predecessor_approval_id": approval.approval_id,
        "run_authorization_id": authorization.authorization_id,
        "run_authorization_content_hash": authorization.content_hash,
        "ledger_snapshot_hash": ledger_snapshot_hash,
        "attempt_number": 1,
        "one_use": True,
        "retry_or_resume_allowed": False,
        "created_at": created_at,
    }
    content_hash = v11.v10._hash_body(body)
    return AttemptIntent(
        **body,
        attempt_id=v11.v10._derived_id("ncpattempt", content_hash),
        content_hash=content_hash,
    )


def _build_action(attempt: AttemptIntent, *, recorded_at: datetime) -> ActionStarted:
    recorded_at = _utc(recorded_at, label="v12 action recorded_at")
    _require(recorded_at >= attempt.created_at, "action predates attempt")
    body = {
        "schema_version": "sanitized-sdk-bootstrap-action-started-v12",
        "attempt_id": attempt.attempt_id,
        "attempt_content_hash": attempt.content_hash,
        "sequence": 1,
        "recorded_at": recorded_at,
    }
    content_hash = v11.v10._hash_body(body)
    return ActionStarted(
        **body,
        marker_id=v11.v10._derived_id("ncpstarted", content_hash),
        content_hash=content_hash,
    )


def _build_terminal(
    attempt: AttemptIntent,
    action: ActionStarted,
    *,
    observation: v9.ParentObservation | None,
    recorded_at: datetime,
) -> TerminalTransition:
    recorded_at = _utc(recorded_at, label="v12 terminal recorded_at")
    _require(recorded_at >= action.recorded_at, "terminal predates action")
    if observation is None:
        outcome = v9.ParentState.ERROR
        reason = TerminalReason.LIFECYCLE_CHECKER_ERROR
        complete = False
        unknown = True
        docker_count = child_count = network_count = provider_count = None
    else:
        observation = v9.ParentObservation.model_validate(observation.model_dump(mode="json"))
        outcome = observation.state
        reason = None if observation.reason is None else TerminalReason(observation.reason.value)
        complete = observation.activity_accounting_complete
        unknown = observation.unknown_post_marker_activity_possible
        docker_count = observation.docker_cli_command_count
        child_count = observation.child_launch_attempt_count
        network_count = observation.network_call_count
        provider_count = observation.provider_evaluator_agent_call_count
    body = {
        "schema_version": "sanitized-sdk-bootstrap-terminal-v12",
        "attempt_id": attempt.attempt_id,
        "action_started_id": action.marker_id,
        "previous_content_hash": action.content_hash,
        "sequence": 2,
        "outcome": outcome,
        "reason": reason,
        "observation": None if observation is None else observation.model_dump(mode="json"),
        "activity_accounting_complete": complete,
        "unknown_post_marker_activity_possible": unknown,
        "docker_cli_command_count": docker_count,
        "sdk_child_start_count": child_count,
        "network_call_count": network_count,
        "provider_evaluator_agent_call_count": provider_count,
        "docker_desktop_or_daemon_start_count": 0,
        "image_pull_load_or_store_mutation_count": 0,
        "container_operation_count": 0,
        "credential_value_return_hash_prefix_or_length_count": 0,
        "recorded_at": recorded_at,
    }
    content_hash = v11.v10._hash_body(body)
    return TerminalTransition(
        **body,
        terminal_id=v11.v10._derived_id("ncpterminal", content_hash),
        content_hash=content_hash,
    )


def _load_v9_contract(root: Path) -> v9.ParentSuccessorContract:
    summary = v9.validate_source_qualification(repository=root)
    contract = v9.load_contract(repository=root)
    _require(summary["source_commit"] == v11.v10.V9_SOURCE_COMMIT, "v9 source differs")
    return contract


def validate_attempt_chain(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v11.v10._root(repository)
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    _, _, _, approval, _, _ = _load_v11_approval(root)
    raw_values = tuple(
        v11.v10._read(root, path)
        for path in (RUN_AUTHORIZATION_PATH, ATTEMPT_PATH, ACTION_STARTED_PATH, TERMINAL_PATH)
    )
    try:
        authorization = RunAuthorization.model_validate_json(raw_values[0])
        attempt = AttemptIntent.model_validate_json(raw_values[1])
        action = ActionStarted.model_validate_json(raw_values[2])
        terminal = TerminalTransition.model_validate_json(raw_values[3])
    except (ValidationError, UnicodeDecodeError) as exc:
        raise AttemptSuccessorError("v12 attempt chain is invalid") from exc
    for label, raw, value in (
        ("authorization", raw_values[0], authorization),
        ("attempt", raw_values[1], attempt),
        ("action", raw_values[2], action),
        ("terminal", raw_values[3], terminal),
    ):
        _require(raw == v11.v10._canonical(value), f"v12 {label} bytes are not canonical")
    _require(authorization.contract_id == contract.contract_id, "authorization contract differs")
    _require(
        authorization.source_qualification_content_hash == qualification.content_hash,
        "authorization qualification differs",
    )
    _require(
        authorization.predecessor_approval_id == approval.approval_id
        and authorization.predecessor_approval_content_hash == approval.content_hash,
        "authorization approval differs",
    )
    _require(
        authorization.statement_sha256
        == sha256_bytes(expected_run_statement(contract, qualification, approval).encode("utf-8")),
        "authorization statement differs",
    )
    _require(attempt.contract_id == contract.contract_id, "attempt contract differs")
    _require(
        attempt.source_qualification_content_hash == qualification.content_hash
        and attempt.predecessor_approval_id == approval.approval_id,
        "attempt authority differs",
    )
    _require(
        attempt.run_authorization_id == authorization.authorization_id
        and attempt.run_authorization_content_hash == authorization.content_hash,
        "attempt authorization differs",
    )
    _require(attempt.ledger_snapshot_hash == _empty_ledger_hash(), "attempt ledger differs")
    _require(
        action.attempt_id == attempt.attempt_id
        and action.attempt_content_hash == attempt.content_hash,
        "action attempt differs",
    )
    _require(
        terminal.attempt_id == attempt.attempt_id
        and terminal.action_started_id == action.marker_id
        and terminal.previous_content_hash == action.content_hash,
        "terminal chain differs",
    )
    _require(
        authorization.recorded_at
        <= attempt.created_at
        <= action.recorded_at
        <= terminal.recorded_at,
        "v12 lifecycle chronology differs",
    )
    return {
        "status": "V12_SANITIZED_SDK_BOOTSTRAP_ATTEMPT_TERMINAL_VALID",
        "contract_id": contract.contract_id,
        "source_qualification_hash": qualification.content_hash,
        "predecessor_approval_id": approval.approval_id,
        "run_authorization_id": authorization.authorization_id,
        "attempt_id": attempt.attempt_id,
        "action_started_id": action.marker_id,
        "terminal_id": terminal.terminal_id,
        "outcome": terminal.outcome.value,
        "reason": None if terminal.reason is None else terminal.reason.value,
        "activity_accounting_complete": terminal.activity_accounting_complete,
        "unknown_post_marker_activity_possible": terminal.unknown_post_marker_activity_possible,
        "retry_or_resume_allowed": False,
        "docker_start_pull_or_container_mutations": 0,
        "network_calls_made": terminal.network_call_count,
        "provider_evaluator_agent_calls_made": terminal.provider_evaluator_agent_call_count,
        "candidate_cost_or_paid_execution_authorized": False,
    }


def run_once(
    *,
    statement: str,
    repository: str | Path | None = None,
    parent_observer: Callable[..., v9.ParentObservation] = v9.run_parent_preflight,
) -> dict[str, Any]:
    """Consume one fresh exact run statement and invoke the sealed v9 observer once."""

    root = v11.v10._root(repository)
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    _, _, _, approval, _, _ = _load_v11_approval(root)
    runtime_contract = _load_v9_contract(root)
    authorization = build_run_authorization(
        contract,
        qualification,
        approval,
        statement=statement,
        recorded_at=datetime.now(UTC),
    )
    ledger_snapshot_hash = _ledger_snapshot(root)
    v11.v10._write_once(root, RUN_AUTHORIZATION_PATH, v11.v10._canonical(authorization))
    attempt = _build_attempt(
        contract,
        qualification,
        approval,
        authorization,
        ledger_snapshot_hash=ledger_snapshot_hash,
        created_at=datetime.now(UTC),
    )
    v11.v10._write_once(root, ATTEMPT_PATH, v11.v10._canonical(attempt))
    action = _build_action(attempt, recorded_at=datetime.now(UTC))
    v11.v10._write_once(root, ACTION_STARTED_PATH, v11.v10._canonical(action))
    try:
        observation = parent_observer(runtime_contract, repository=root)
        observation = v9.ParentObservation.model_validate(observation.model_dump(mode="json"))
    except Exception:
        observation = None
    terminal = _build_terminal(
        attempt,
        action,
        observation=observation,
        recorded_at=datetime.now(UTC),
    )
    terminal_raw = v11.v10._canonical(terminal)
    lowered = terminal_raw.lower()
    _require(b"openai_api_key=" not in lowered, "terminal contains credential assignment")
    _require(b"sk-" not in lowered, "terminal contains credential-like material")
    v11.v10._write_once(root, TERMINAL_PATH, terminal_raw)
    return validate_attempt_chain(repository=root)


__all__ = [
    "ACTION_STARTED_PATH",
    "APPROVED_RUNTIME",
    "APPROVED_SCOPES",
    "ATTEMPT_PATH",
    "AttemptIntent",
    "AttemptSuccessorContract",
    "AttemptSuccessorError",
    "BUILD_SCRIPT_PATH",
    "CONTRACT_PATH",
    "QUALIFICATION_PATH",
    "RUN_AUTHORIZATION_PATH",
    "RUN_TEMPLATE",
    "RUNTIME_PATH",
    "RunAuthorization",
    "SOURCE_ADDED_PATHS",
    "SOURCE_FILES",
    "SourceQualification",
    "TERMINAL_PATH",
    "TEST_PATH",
    "TerminalTransition",
    "build_run_authorization",
    "expected_run_statement",
    "load_contract",
    "materialize_contract",
    "qualify_source",
    "run_once",
    "validate_attempt_chain",
    "validate_source_qualification",
]
