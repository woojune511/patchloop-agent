"""Offline-first v16 activation wrapper around source-qualified v15.

V15 remains source-only and immutable.  This module binds that exact source
qualification, implements separate state/approval/immediate-run entrypoints,
and makes the v15 observer reachable only after the append-only run lifecycle
has started.  Source qualification itself performs no Docker, dotenv, SDK,
network, provider, evaluator, or agent observation.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, Field, ValidationError, field_validator, model_validator

from patchloop.contracts import FrozenStrictModel
from patchloop.errors import ContractError
from patchloop.evals import dedicated_frame_preflight_successor as v15
from patchloop.util import sha256_bytes

v13 = v15.v13
v10 = v15.v10
v9 = v15.v9

CONTRACT_SCHEMA_VERSION = "dedicated-frame-activation-successor-contract-v16"
CONTRACT_VERSION = "ac-evaluator-v2-dedicated-frame-activation-successor-v16"
CONTRACT_PATH = Path(
    "experiments/evaluator-v2-dedicated-frame-activation-successor-v16.contract.json"
)
RUNTIME_PATH = Path("patchloop/evals/dedicated_frame_activation_successor.py")
BUILD_SCRIPT_PATH = Path("scripts/build_dedicated_frame_activation_successor.py")
TEST_PATH = Path("tests/test_dedicated_frame_activation_successor.py")

SOURCE_PARENT_COMMIT = "9c6ec8ac7a5a44533f1a1e42c41059b27cfca2b3"
V15_SOURCE_COMMIT = "e962291bfea66980a66c7592e87ce5277b43b30a"
V15_SOURCE_TREE = "082840944a46b2fc8d3b9f2df8afcc5d04b759ee"
V15_QUALIFICATION_COMMIT = "ac32e7848246aa18e04920f2c354abda8707b41e"
V15_QUALIFICATION_HASH = "sha256:0cdf9e0bb8ea981e7360bd7acd456c3b8aebfc6cf719aa2527e828ab7dc2f494"
V15_QUALIFICATION_FILE_SHA256 = (
    "sha256:0112807f9a8bbe4831e7c9103859909c8266247ec0aaf551c2960978421b9708"
)
QUALIFICATION_SCHEMA_VERSION = "dedicated-frame-activation-source-qualification-v16"
QUALIFICATION_ID = "ac-evaluator-v2-dedicated-frame-activation-source-20260813-r1"
QUALIFICATION_STATUS = "OFFLINE_V16_ACTIVATION_SOURCE_QUALIFIED_STATE_STATEMENT_REQUIRED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-dedicated-frame-activation-v16-source-qualification.json"
)
STATE_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-dedicated-frame-activation-v16-state-change-evidence.json"
)
APPROVAL_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-dedicated-frame-activation-v16-approval-binding.json"
)
RUN_AUTHORIZATION_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-dedicated-frame-activation-v16-run-authorization.json"
)
ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-dedicated-frame-activation-v16-attempt-intent.json"
)
ACTION_STARTED_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-dedicated-frame-activation-v16-action-started.json"
)
TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-dedicated-frame-activation-v16-terminal.json"
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
            v15.CONTRACT_PATH,
            v15.RUNTIME_PATH,
            v15.CHILD_PATH,
            v15.QUALIFICATION_PATH,
        ),
        key=lambda path: path.as_posix(),
    )
)

APPROVED_RUNTIME = "patchloop.evals.dedicated_frame_activation_successor.run_once"
APPROVED_SCOPES = v15.APPROVED_SCOPES
NEXT_GATE = "fresh-exact-v16-state-statement"

STATE_TEMPLATE = (
    "Contract {contract_id}, source qualification {qualification_hash}, predecessor v15 "
    "qualification {v15_qualification_hash}: Docker Desktop is reported running; "
    "repository-root .env is reported to contain only OPENAI_API_KEY; state-binding-only; "
    "no-execution-authority."
)
APPROVAL_TEMPLATE = (
    "Contract {contract_id}, source qualification {qualification_hash}, state {state_id} "
    "({state_hash}): approve exactly one future v16 dedicated-frame no-call preflight under the "
    "fixed v15 scopes; current Docker-running and repository-root .env-only-OPENAI_API_KEY "
    "report is reconfirmed; approval-binding-only, no attempt now; no credential value "
    "recording, Docker "
    "start/pull/load/image-store mutation/container operation, network/transport, "
    "provider/evaluator/agent, candidate/cost/paid execution, retry/replacement/resume."
)
RUN_TEMPLATE = (
    "Contract {contract_id}, source qualification {qualification_hash}, state {state_id} "
    "({state_hash}), approval {approval_id} ({approval_hash}): authorize exactly one immediate "
    "v16 dedicated-frame no-call preflight attempt now; append authorization, attempt and "
    "ACTION_STARTED before observation and one terminal after; no credential value recording, "
    "Docker "
    "start/pull/load/image-store mutation/container operation, network/transport, "
    "provider/evaluator/agent, candidate/cost/paid execution, retry/replacement/resume."
)


class DedicatedFrameActivationError(ContractError):
    """The v16 successor failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DedicatedFrameActivationError(message)


def _utc(value: datetime, *, label: str) -> datetime:
    _require(value.tzinfo is not None, f"{label} must be timezone-aware")
    _require(value.utcoffset() == UTC.utcoffset(value), f"{label} must be UTC")
    return value


def _validate_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("v16 lifecycle time must be UTC")
    return value


UTCDateTime = Annotated[datetime, AfterValidator(_validate_utc_datetime)]


class V15SourceBinding(FrozenStrictModel):
    source_commit: Literal["e962291bfea66980a66c7592e87ce5277b43b30a"] = V15_SOURCE_COMMIT
    source_tree: Literal["082840944a46b2fc8d3b9f2df8afcc5d04b759ee"] = V15_SOURCE_TREE
    qualification_commit: Literal["ac32e7848246aa18e04920f2c354abda8707b41e"] = (
        V15_QUALIFICATION_COMMIT
    )
    contract_id: Literal[
        "ncpcontract_ac6959d19db4d7a11ce199a32bde188fbfd515c7bdfcee9241d10ac164800f01"
    ]
    contract_content_hash: Literal[
        "sha256:ac6959d19db4d7a11ce199a32bde188fbfd515c7bdfcee9241d10ac164800f01"
    ]
    source_qualification_hash: Literal[
        "sha256:0cdf9e0bb8ea981e7360bd7acd456c3b8aebfc6cf719aa2527e828ab7dc2f494"
    ] = V15_QUALIFICATION_HASH
    qualification_file_sha256: Literal[
        "sha256:0112807f9a8bbe4831e7c9103859909c8266247ec0aaf551c2960978421b9708"
    ] = V15_QUALIFICATION_FILE_SHA256
    qualification_status: Literal["OFFLINE_V15_DEDICATED_FRAME_SOURCE_QUALIFIED_ACTIVATION_CLOSED"]
    state_approval_attempt_or_terminal_count: Literal[0] = 0
    external_observation_count: Literal[0] = 0
    execution_authorized: Literal[False] = False


class DelegateRuntimeProfile(FrozenStrictModel):
    entrypoint: Literal["patchloop.evals.dedicated_frame_activation_successor.run_once"] = (
        APPROVED_RUNTIME
    )
    observer_entrypoint: Literal[
        "patchloop.evals.dedicated_frame_activation_successor._run_parent_preflight"
    ] = "patchloop.evals.dedicated_frame_activation_successor._run_parent_preflight"
    delegate_entrypoint: Literal[
        "patchloop.evals.dedicated_frame_preflight_successor.run_parent_preflight_injected"
    ] = v15.APPROVED_RUNTIME
    v15_source_commit: Literal["e962291bfea66980a66c7592e87ce5277b43b30a"] = V15_SOURCE_COMMIT
    v15_contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    v15_contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v15_source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v15_runtime_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v15_child_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    delegate_semantics_unchanged: Literal[True] = True
    default_observers_reachable_only_after_action_started: Literal[True] = True
    direct_observer_cli_exposed: Literal[False] = False
    docker_expected_command_count: Literal[8] = 8
    framed_child_limit: Literal[1] = 1
    raw_child_output_persistence_allowed: Literal[False] = False
    credential_value_return_hash_prefix_or_length_limit: Literal[0] = 0
    network_call_limit: Literal[0] = 0
    provider_evaluator_agent_call_limit: Literal[0] = 0

    @model_validator(mode="after")
    def validate_scopes(self) -> DelegateRuntimeProfile:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("v16 approved scopes drifted")
        return self


class LifecyclePolicy(FrozenStrictModel):
    predecessor_source_qualification_required: Literal[True] = True
    fresh_source_bound_state_required: Literal[True] = True
    separate_exact_approval_required: Literal[True] = True
    exact_immediate_run_statement_required: Literal[True] = True
    authorization_attempt_action_before_observation: Literal[True] = True
    one_terminal_required: Literal[True] = True
    attempt_limit: Literal[1] = 1
    state_or_approval_reusable: Literal[False] = False
    retry_replacement_or_resume_allowed: Literal[False] = False
    v15_source_or_qualification_mutation_allowed: Literal[False] = False


class SourceAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    source_qualification_authorized: Literal[True] = True
    state_approval_attempt_or_terminal_during_qualification_authorized: Literal[False] = False
    environment_docker_dotenv_sdk_or_network_observation_authorized: Literal[False] = False
    credential_value_recording_authorized: Literal[False] = False
    docker_start_pull_load_image_store_or_container_mutation_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class DedicatedFrameActivationContract(FrozenStrictModel):
    schema_version: Literal["dedicated-frame-activation-successor-contract-v16"] = (
        CONTRACT_SCHEMA_VERSION
    )
    contract_version: Literal["ac-evaluator-v2-dedicated-frame-activation-successor-v16"] = (
        CONTRACT_VERSION
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor: V15SourceBinding
    runtime: DelegateRuntimeProfile
    lifecycle: LifecyclePolicy
    authority: SourceAuthority
    state_approval_and_attempt_entrypoints_implemented: Literal[True] = True
    execution_currently_authorized: Literal[False] = False
    next_gate: Literal["fresh-exact-v16-state-statement"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> DedicatedFrameActivationContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected or self.contract_id != v10._derived_id(
            "ncpcontract", expected
        ):
            raise ValueError("v16 contract identity differs")
        return self


class SourceCommitBinding(FrozenStrictModel):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    parents: tuple[str, ...]
    added_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_source(self) -> SourceCommitBinding:
        if self.parents != (SOURCE_PARENT_COMMIT,) or self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v16 source commit boundary differs")
        return self


class QualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    source_qualified: Literal[True] = True
    state_approval_attempt_or_terminal_created: Literal[False] = False
    environment_docker_dotenv_sdk_network_or_provider_observation_count: Literal[0] = 0
    external_mutation_count: Literal[0] = 0
    execution_authorized: Literal[False] = False


class SourceQualification(FrozenStrictModel):
    schema_version: Literal["dedicated-frame-activation-source-qualification-v16"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal["ac-evaluator-v2-dedicated-frame-activation-source-20260813-r1"] = (
        QUALIFICATION_ID
    )
    status: Literal["OFFLINE_V16_ACTIVATION_SOURCE_QUALIFIED_STATE_STATEMENT_REQUIRED"] = (
        QUALIFICATION_STATUS
    )
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[v10.CommittedFileBinding, ...]
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_source_qualification_hash: Literal[
        "sha256:0cdf9e0bb8ea981e7360bd7acd456c3b8aebfc6cf719aa2527e828ab7dc2f494"
    ] = V15_QUALIFICATION_HASH
    authority: QualificationAuthority
    next_gate: Literal["fresh-exact-v16-state-statement"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v16 qualification time must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> SourceQualification:
        if tuple(item.path for item in self.source_files) != tuple(
            path.as_posix() for path in SOURCE_FILES
        ):
            raise ValueError("v16 qualification inventory drifted")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != v10._hash_body(body):
            raise ValueError("v16 qualification hash mismatch")
        return self


class StateEvidence(FrozenStrictModel):
    schema_version: Literal["dedicated-frame-activation-state-v16"] = (
        "dedicated-frame-activation-state-v16"
    )
    state_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_source_qualification_hash: Literal[
        "sha256:0cdf9e0bb8ea981e7360bd7acd456c3b8aebfc6cf719aa2527e828ab7dc2f494"
    ] = V15_QUALIFICATION_HASH
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
            raise ValueError("v16 state identity differs")
        return self


class ApprovalBinding(FrozenStrictModel):
    schema_version: Literal["dedicated-frame-activation-approval-v16"] = (
        "dedicated-frame-activation-approval-v16"
    )
    approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    statement_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    docker_running_reconfirmed: Literal[True] = True
    dotenv_only_openai_api_key_reconfirmed: Literal[True] = True
    approved_runtime: Literal["patchloop.evals.dedicated_frame_activation_successor.run_once"] = (
        APPROVED_RUNTIME
    )
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
            raise ValueError("v16 approval scopes drifted")
        body = self.model_dump(mode="json", exclude={"approval_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected or self.approval_id != v10._derived_id(
            "ncpapproval", expected
        ):
            raise ValueError("v16 approval identity differs")
        return self


class RunAuthorization(FrozenStrictModel):
    schema_version: Literal["dedicated-frame-activation-run-authorization-v16"] = (
        "dedicated-frame-activation-run-authorization-v16"
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
            raise ValueError("v16 run authorization identity differs")
        return self


class AttemptIntent(FrozenStrictModel):
    schema_version: Literal["dedicated-frame-activation-attempt-v16"] = (
        "dedicated-frame-activation-attempt-v16"
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
            raise ValueError("v16 attempt identity differs")
        return self


class ActionStarted(FrozenStrictModel):
    schema_version: Literal["dedicated-frame-activation-action-started-v16"] = (
        "dedicated-frame-activation-action-started-v16"
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
            raise ValueError("v16 action identity differs")
        return self


class TerminalTransition(FrozenStrictModel):
    schema_version: Literal["dedicated-frame-activation-terminal-v16"] = (
        "dedicated-frame-activation-terminal-v16"
    )
    terminal_id: str = Field(pattern=r"^ncpterminal_[0-9a-f]{64}$")
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    action_started_id: str = Field(pattern=r"^ncpstarted_[0-9a-f]{64}$")
    previous_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sequence: Literal[2] = 2
    outcome: v9.ParentState
    reason: v9.ParentReason | Literal["lifecycle_checker_error"] | None = None
    observation: v13.CorrectedParentObservation | None = None
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
                raise ValueError("v16 lifecycle-error terminal differs")
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
            raise ValueError("v16 terminal observation differs")
        body = self.model_dump(mode="json", exclude={"terminal_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected or self.terminal_id != v10._derived_id(
            "ncpterminal", expected
        ):
            raise ValueError("v16 terminal identity differs")
        return self


def _load_v15_source(
    root: Path,
) -> tuple[v15.DedicatedFrameContract, v15.SourceQualification]:
    contract = v15.load_contract(repository=root)
    v15.validate_source_qualification(repository=root)
    raw = v10._read(root, v15.QUALIFICATION_PATH)
    qualification = v15.SourceQualification.model_validate_json(raw)
    committed = v10._git(
        root,
        "show",
        f"{V15_QUALIFICATION_COMMIT}:{v15.QUALIFICATION_PATH.as_posix()}",
    )
    _require(committed == raw, "v15 committed source qualification differs")
    _require(
        qualification.source_commit.commit == V15_SOURCE_COMMIT
        and qualification.source_commit.tree == V15_SOURCE_TREE
        and qualification.contract_id == contract.contract_id
        and qualification.contract_content_hash == contract.content_hash
        and qualification.content_hash == V15_QUALIFICATION_HASH
        and sha256_bytes(raw) == V15_QUALIFICATION_FILE_SHA256
        and qualification.authority.state_approval_attempt_or_terminal_created is False
        and qualification.authority.execution_authorized is False,
        "v15 source-only boundary differs",
    )
    return contract, qualification


def _predecessor_binding(root: Path) -> V15SourceBinding:
    contract, qualification = _load_v15_source(root)
    return V15SourceBinding(
        contract_id=contract.contract_id,
        contract_content_hash=contract.content_hash,
        qualification_status=qualification.status,
    )


def _runtime_profile(root: Path) -> DelegateRuntimeProfile:
    contract, qualification = _load_v15_source(root)
    return DelegateRuntimeProfile(
        v15_contract_id=contract.contract_id,
        v15_contract_content_hash=contract.content_hash,
        v15_source_qualification_hash=qualification.content_hash,
        v15_runtime_file_sha256=sha256_bytes(v10._read(root, v15.RUNTIME_PATH)),
        v15_child_file_sha256=sha256_bytes(v10._read(root, v15.CHILD_PATH)),
    )


def _build_contract(root: Path) -> DedicatedFrameActivationContract:
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
    return DedicatedFrameActivationContract(
        **body,
        contract_id=v10._derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def load_contract(*, repository: str | Path | None = None) -> DedicatedFrameActivationContract:
    root = v10._root(repository)
    raw = v10._read(root, CONTRACT_PATH)
    try:
        value = DedicatedFrameActivationContract.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise DedicatedFrameActivationError("v16 contract artifact is invalid") from exc
    _require(raw == v10._canonical(value), "v16 contract bytes are not canonical")
    _require(value == _build_contract(root), "v16 contract has drifted")
    return value


def materialize_contract(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    value = _build_contract(root)
    target = v10._logical_path(root, CONTRACT_PATH, must_exist=False)
    raw = v10._canonical(value)
    if target.exists():
        _require(v10._read(root, CONTRACT_PATH) == raw, "v16 contract already differs")
    else:
        v10._write_once(root, CONTRACT_PATH, raw)
    return {
        "status": "OFFLINE_V16_ACTIVATION_CONTRACT_MATERIALIZED_LIVE_CLOSED",
        "contract_id": value.contract_id,
        "contract_content_hash": value.content_hash,
        "runtime_artifacts_created": False,
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
        "next_gate": "exact-source-commit-and-offline-qualification",
    }


def _contract_error_observation() -> v13.CorrectedParentObservation:
    base = v9._contract_error_observation()
    return v13.CorrectedParentObservation(
        base=base,
        activity_accounting_complete=base.activity_accounting_complete,
        unknown_post_marker_activity_possible=base.unknown_post_marker_activity_possible,
        passed=False,
    )


def _run_parent_preflight(
    contract: DedicatedFrameActivationContract,
    *,
    repository: str | Path | None = None,
    docker_observer: Callable[
        ..., dict[str, Any]
    ] = v9.d137.run_d137_docker_no_call_preflight_observation,
    child_observer: Callable[..., v13.FramedChildExecution] | None = None,
) -> v13.CorrectedParentObservation:
    root = v10._root(repository)
    try:
        checked = DedicatedFrameActivationContract.model_validate(contract.model_dump(mode="json"))
        _require(checked == load_contract(repository=root), "v16 runtime contract differs")
        _require(
            sha256_bytes(v10._read(root, v15.RUNTIME_PATH))
            == contract.runtime.v15_runtime_file_sha256,
            "v16 delegated runtime differs",
        )
        delegate = v15.load_contract(repository=root)
        _load_v15_source(root)
    except Exception:
        return _contract_error_observation()

    if child_observer is None:

        def child_observer(*_args: Any, **_kwargs: Any) -> v13.FramedChildExecution:
            return v15.run_dedicated_frame_child_injected(
                delegate,
                repository=root,
                environment_present=lambda name: name in os.environ,
                environment_value=os.environ.get,
                python=sys.executable,
                run=subprocess.run,
            )

    return v15.run_parent_preflight_injected(
        delegate,
        repository=root,
        docker_observer=docker_observer,
        child_observer=child_observer,
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
        _require(status == "A", "v16 source commit contains non-addition")
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
    committed_contract = DedicatedFrameActivationContract.model_validate_json(
        committed_contract_raw
    )
    _require(
        committed_contract_raw == v10._canonical(committed_contract),
        "v16 committed contract bytes differ",
    )
    _require(
        committed_contract == load_contract(repository=root),
        "v16 working contract differs from source commit",
    )
    body = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": QUALIFICATION_STATUS,
        "recorded_at": _utc(recorded_at, label="v16 qualification recorded_at"),
        "source_commit": commit.model_dump(mode="json"),
        "source_files": tuple(item.model_dump(mode="json") for item in files),
        "contract_id": committed_contract.contract_id,
        "contract_content_hash": committed_contract.content_hash,
        "predecessor_source_qualification_hash": (
            committed_contract.predecessor.source_qualification_hash
        ),
        "authority": QualificationAuthority().model_dump(mode="json"),
        "next_gate": NEXT_GATE,
    }
    return SourceQualification(**body, content_hash=v10._hash_body(body))


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


def qualify_source(
    *, source_commit: str = "HEAD", repository: str | Path | None = None
) -> dict[str, Any]:
    root = v10._root(repository)
    target = v10._logical_path(root, QUALIFICATION_PATH, must_exist=False)
    value = _build_qualification(root, source_commit=source_commit, recorded_at=datetime.now(UTC))
    raw = v10._canonical(value)
    if target.exists():
        _require(v10._read(root, QUALIFICATION_PATH) == raw, "v16 qualification already differs")
    else:
        v10._write_once(root, QUALIFICATION_PATH, raw)
    return _qualification_summary(value, raw)


def validate_source_qualification(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    raw = v10._read(root, QUALIFICATION_PATH)
    try:
        value = SourceQualification.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise DedicatedFrameActivationError("v16 qualification is invalid") from exc
    _require(raw == v10._canonical(value), "v16 qualification bytes are not canonical")
    expected = _build_qualification(
        root,
        source_commit=value.source_commit.commit,
        recorded_at=value.recorded_at,
    )
    _require(value == expected, "v16 qualification has drifted")
    return _qualification_summary(value, raw)


def _load_qualification(root: Path) -> SourceQualification:
    validate_source_qualification(repository=root)
    return SourceQualification.model_validate_json(v10._read(root, QUALIFICATION_PATH))


def expected_state_statement(
    contract: DedicatedFrameActivationContract, qualification: SourceQualification
) -> str:
    _require(qualification.contract_id == contract.contract_id, "v16 state contract differs")
    return STATE_TEMPLATE.format(
        contract_id=contract.contract_id,
        qualification_hash=qualification.content_hash,
        v15_qualification_hash=contract.predecessor.source_qualification_hash,
    )


def build_state_evidence(
    contract: DedicatedFrameActivationContract,
    qualification: SourceQualification,
    *,
    statement: str,
    recorded_at: datetime,
) -> StateEvidence:
    _require(
        statement == expected_state_statement(contract, qualification),
        "v16 state statement differs",
    )
    recorded_at = _utc(recorded_at, label="v16 state recorded_at")
    _require(recorded_at >= qualification.recorded_at, "v16 state predates qualification")
    body = {
        "schema_version": "dedicated-frame-activation-state-v16",
        "contract_id": contract.contract_id,
        "source_qualification_hash": qualification.content_hash,
        "predecessor_source_qualification_hash": contract.predecessor.source_qualification_hash,
        "statement_sha256": sha256_bytes(statement.encode("utf-8")),
        "docker_running_reported": True,
        "dotenv_only_openai_api_key_reported": True,
        "self_attested_nonproof": True,
        "external_observation_count": 0,
        "execution_authorized": False,
        "reusable": False,
        "recorded_at": recorded_at,
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
        "status": "V16_STATE_RECORDED_SELF_ATTESTED_NO_EXECUTION",
        "state_id": value.state_id,
        "state_content_hash": value.content_hash,
        "external_observations_made": 0,
        "execution_authorized": False,
    }


def _load_state(root: Path) -> StateEvidence:
    raw = v10._read(root, STATE_PATH)
    value = StateEvidence.model_validate_json(raw)
    _require(raw == v10._canonical(value), "v16 state bytes differ")
    return value


def expected_approval_statement(
    contract: DedicatedFrameActivationContract,
    qualification: SourceQualification,
    state: StateEvidence,
) -> str:
    _require(
        state.contract_id == contract.contract_id
        and state.source_qualification_hash == qualification.content_hash,
        "v16 approval state binding differs",
    )
    return APPROVAL_TEMPLATE.format(
        contract_id=contract.contract_id,
        qualification_hash=qualification.content_hash,
        state_id=state.state_id,
        state_hash=state.content_hash,
    )


def build_approval(
    contract: DedicatedFrameActivationContract,
    qualification: SourceQualification,
    state: StateEvidence,
    *,
    statement: str,
    recorded_at: datetime,
) -> ApprovalBinding:
    _require(
        statement == expected_approval_statement(contract, qualification, state),
        "v16 approval statement differs",
    )
    recorded_at = _utc(recorded_at, label="v16 approval recorded_at")
    _require(recorded_at >= state.recorded_at, "v16 approval predates state")
    body = {
        "schema_version": "dedicated-frame-activation-approval-v16",
        "contract_id": contract.contract_id,
        "source_qualification_hash": qualification.content_hash,
        "state_id": state.state_id,
        "state_content_hash": state.content_hash,
        "statement_sha256": sha256_bytes(statement.encode("utf-8")),
        "docker_running_reconfirmed": True,
        "dotenv_only_openai_api_key_reconfirmed": True,
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
        "status": "V16_APPROVAL_RECORDED_ATTEMPT_NOT_STARTED",
        "approval_id": value.approval_id,
        "approval_content_hash": value.content_hash,
        "attempt_started": False,
        "external_observations_made": 0,
    }


def _load_approval(root: Path) -> ApprovalBinding:
    raw = v10._read(root, APPROVAL_PATH)
    value = ApprovalBinding.model_validate_json(raw)
    _require(raw == v10._canonical(value), "v16 approval bytes differ")
    return value


def expected_run_statement(
    contract: DedicatedFrameActivationContract,
    qualification: SourceQualification,
    state: StateEvidence,
    approval: ApprovalBinding,
) -> str:
    _require(
        approval.contract_id == contract.contract_id
        and approval.source_qualification_hash == qualification.content_hash
        and approval.state_id == state.state_id
        and approval.state_content_hash == state.content_hash,
        "v16 run approval binding differs",
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
    contract: DedicatedFrameActivationContract,
    qualification: SourceQualification,
    state: StateEvidence,
    approval: ApprovalBinding,
    *,
    statement: str,
    recorded_at: datetime,
) -> RunAuthorization:
    _require(
        statement == expected_run_statement(contract, qualification, state, approval),
        "v16 run statement differs",
    )
    recorded_at = _utc(recorded_at, label="v16 authorization recorded_at")
    _require(recorded_at >= approval.recorded_at, "v16 authorization predates approval")
    body = {
        "schema_version": "dedicated-frame-activation-run-authorization-v16",
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
    _require(not any(row["exists"] for row in rows), "v16 attempt ledger is consumed")
    return v10._hash_body({"rows": rows})


def _canonical_empty_ledger_hash() -> str:
    return v10._hash_body(
        {"rows": [{"path": path.as_posix(), "exists": False} for path in _ledger_paths()]}
    )


def _build_attempt(
    authorization: RunAuthorization, *, ledger_hash: str, created_at: datetime
) -> AttemptIntent:
    created_at = _utc(created_at, label="v16 attempt created_at")
    _require(created_at >= authorization.recorded_at, "v16 attempt predates authorization")
    body = {
        "schema_version": "dedicated-frame-activation-attempt-v16",
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
    recorded_at = _utc(recorded_at, label="v16 action recorded_at")
    _require(recorded_at >= attempt.created_at, "v16 action predates attempt")
    body = {
        "schema_version": "dedicated-frame-activation-action-started-v16",
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
    observation: v13.CorrectedParentObservation | None,
    recorded_at: datetime,
) -> TerminalTransition:
    recorded_at = _utc(recorded_at, label="v16 terminal recorded_at")
    _require(recorded_at >= action.recorded_at, "v16 terminal predates action")
    if observation is None:
        outcome = v9.ParentState.ERROR
        reason: v9.ParentReason | str | None = "lifecycle_checker_error"
        complete, unknown = False, True
        network_count = provider_count = None
    else:
        observation = v13.CorrectedParentObservation.model_validate(
            observation.model_dump(mode="json")
        )
        outcome = observation.base.state
        reason = observation.base.reason
        complete = observation.activity_accounting_complete
        unknown = observation.unknown_post_marker_activity_possible
        network_count = observation.base.network_call_count
        provider_count = observation.base.provider_evaluator_agent_call_count
    body = {
        "schema_version": "dedicated-frame-activation-terminal-v16",
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
    parent_observer: Callable[..., v13.CorrectedParentObservation] = _run_parent_preflight,
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
        observation = v13.CorrectedParentObservation.model_validate(
            observation.model_dump(mode="json")
        )
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
    _require(b"openai_api_key=" not in lowered and b"sk-" not in lowered, "v16 terminal leaks")
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
        _require(raw == v10._canonical(value), f"v16 {path.name} bytes differ")
        values.append(value)
    authorization, attempt, action, terminal = values
    assert isinstance(authorization, RunAuthorization)
    assert isinstance(attempt, AttemptIntent)
    assert isinstance(action, ActionStarted)
    assert isinstance(terminal, TerminalTransition)
    _require(
        state.contract_id == contract.contract_id
        and state.source_qualification_hash == qualification.content_hash
        and state.predecessor_source_qualification_hash
        == contract.predecessor.source_qualification_hash
        and state.statement_sha256
        == sha256_bytes(expected_state_statement(contract, qualification).encode("utf-8")),
        "v16 state binding differs",
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
        "v16 approval binding differs",
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
        "v16 run authorization differs",
    )
    _require(
        attempt.run_authorization_id == authorization.authorization_id
        and attempt.run_authorization_content_hash == authorization.content_hash
        and attempt.ledger_snapshot_hash == _canonical_empty_ledger_hash(),
        "v16 attempt authorization differs",
    )
    _require(
        action.attempt_id == attempt.attempt_id
        and action.attempt_content_hash == attempt.content_hash
        and terminal.attempt_id == attempt.attempt_id
        and terminal.action_started_id == action.marker_id
        and terminal.previous_content_hash == action.content_hash,
        "v16 terminal chain differs",
    )
    _require(
        qualification.recorded_at
        <= state.recorded_at
        <= approval.recorded_at
        <= authorization.recorded_at
        <= attempt.created_at
        <= action.recorded_at
        <= terminal.recorded_at,
        "v16 lifecycle chronology differs",
    )
    terminal_raw = v10._canonical(terminal).lower()
    _require(
        b"openai_api_key=" not in terminal_raw and b"sk-" not in terminal_raw,
        "v16 persisted terminal leaks",
    )
    return {
        "status": "V16_DEDICATED_FRAME_NO_CALL_PREFLIGHT_TERMINAL_VALID",
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
    "CONTRACT_PATH",
    "DedicatedFrameActivationContract",
    "DedicatedFrameActivationError",
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
    "run_once",
    "validate_attempt_chain",
    "validate_source_qualification",
]
