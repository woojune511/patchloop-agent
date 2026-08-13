"""Offline-first v25 activation wrapper around source-qualified v24.

V24 remains immutable, source-qualified, and projection-only.  This module binds
its exact source qualification, adds a lifecycle-gated two-hop live adapter, and keeps source
qualification free of Docker, dotenv, SDK, network, provider, evaluator, and
agent observation.  Only ``run_once`` reaches the default observer, after the
authorization, attempt, and ``ACTION_STARTED`` artifacts are durable.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, Field, ValidationError, field_validator, model_validator

from patchloop.contracts import FrozenStrictModel
from patchloop.errors import ContractError
from patchloop.evals import order_stable_typed_diagnostic_successor as v24
from patchloop.util import sha256_bytes
from scripts import run_order_stable_typed_diagnostic_activation_v25 as channel
from scripts import run_order_stable_typed_diagnostic_activation_v25 as live_channel

v10 = v24.v10
v23 = v24.v23
v7 = v23.v7

CONTRACT_SCHEMA_VERSION = "typed-diagnostic-activation-successor-contract-v25"
CONTRACT_VERSION = "ac-evaluator-v2-typed-diagnostic-activation-successor-v25"
CONTRACT_PATH = Path(
    "experiments/evaluator-v2-typed-diagnostic-activation-successor-v25.contract.json"
)
RUNTIME_PATH = Path("patchloop/evals/order_stable_typed_diagnostic_activation_successor.py")
LIVE_CHANNEL_PATH = Path("scripts/run_order_stable_typed_diagnostic_activation_v25.py")
BUILD_SCRIPT_PATH = Path("scripts/build_order_stable_typed_diagnostic_activation_successor.py")
TEST_PATH = Path("tests/test_order_stable_typed_diagnostic_activation_successor.py")

SOURCE_PARENT_COMMIT = "88f21e545298d1af0061bb2a125078fba975c8ad"
V24_SOURCE_COMMIT = "870558afecc3c1ebbefd04b9acc78e138fc5d632"
V24_SOURCE_TREE = "6a2fc91416b17f24ae9bf794dc9b75968b5bd380"
V24_QUALIFICATION_COMMIT = "545d14d653d952464fb25287a53bb59b624785b0"
V24_CONTRACT_ID = "ncpcontract_f6fe2bdf24727ab0ba7b32bc86f4678bd253bd4e4652b8eb83acce7660952ed1"
V24_CONTRACT_FILE_SHA256 = "sha256:0f3822a34ed29857e77c246d1150f54ea44113770541cf64f7b938d0f8fad0ca"
V24_CONTRACT_FILE_BYTES = 4_624
V24_QUALIFICATION_HASH = "sha256:79423fd51f0b951e8b4c7565396d6f4e49447604fb33acee894a9c0644a5bcb6"
V24_QUALIFICATION_FILE_SHA256 = (
    "sha256:20e0eb9f12003bc8c8f62e615386d224919d267fbf18b61a7d0b17741715c3f5"
)
V24_QUALIFICATION_FILE_BYTES = 17_599

QUALIFICATION_SCHEMA_VERSION = "typed-diagnostic-activation-source-qualification-v25"
QUALIFICATION_ID = "ac-evaluator-v2-typed-diagnostic-activation-source-20260813-r1"
QUALIFICATION_STATUS = "OFFLINE_V25_TYPED_DIAGNOSTIC_ACTIVATION_SOURCE_QUALIFIED_STATE_REQUIRED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-typed-diagnostic-activation-v25-source-qualification.json"
)
STATE_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-typed-diagnostic-activation-v25-state-change-evidence.json"
)
APPROVAL_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-typed-diagnostic-activation-v25-approval-binding.json"
)
RUN_AUTHORIZATION_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-typed-diagnostic-activation-v25-run-authorization.json"
)
ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-typed-diagnostic-activation-v25-attempt-intent.json"
)
ACTION_STARTED_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-typed-diagnostic-activation-v25-action-started.json"
)
TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-typed-diagnostic-activation-v25-terminal.json"
)

SOURCE_ADDED_PATHS = tuple(
    sorted(
        path.as_posix()
        for path in (CONTRACT_PATH, RUNTIME_PATH, LIVE_CHANNEL_PATH, BUILD_SCRIPT_PATH, TEST_PATH)
    )
)
SOURCE_FILES = tuple(
    sorted(
        set(v24.SOURCE_FILES)
        | {
            CONTRACT_PATH,
            RUNTIME_PATH,
            LIVE_CHANNEL_PATH,
            BUILD_SCRIPT_PATH,
            TEST_PATH,
            v24.QUALIFICATION_PATH,
        },
        key=lambda path: path.as_posix(),
    )
)

APPROVED_RUNTIME = "patchloop.evals.order_stable_typed_diagnostic_activation_successor.run_once"
APPROVED_SCOPES = v23.APPROVED_SCOPES
NEXT_GATE = "fresh-exact-v25-state-statement"

STATE_TEMPLATE = (
    "Contract {contract_id}, source qualification {qualification_hash}, predecessor v24 "
    "qualification {v24_qualification_hash}: Docker Desktop is reported running; "
    "repository-root .env is reported to contain only OPENAI_API_KEY; state-binding-only; "
    "no-execution-authority."
)
APPROVAL_TEMPLATE = (
    "Contract {contract_id}, source qualification {qualification_hash}, state {state_id} "
    "({state_hash}): approve exactly one future v25 typed-channel no-call preflight under "
    "the fixed v24 projection and v23 observation scopes and one parent-to-supervisor plus one "
    "supervisor-to-worker process "
    "limit; current Docker-running and repository-root .env-only-OPENAI_API_KEY report is "
    "reconfirmed; approval-binding-only, no attempt now; no credential value recording, "
    "Docker start/pull/load/image-store mutation/container operation, network/transport, "
    "provider/evaluator/agent, candidate/cost/paid execution, retry/replacement/resume."
)
RUN_TEMPLATE = (
    "Contract {contract_id}, source qualification {qualification_hash}, state {state_id} "
    "({state_hash}), approval {approval_id} ({approval_hash}): authorize exactly one immediate "
    "v25 typed-channel no-call preflight attempt now under one parent-to-supervisor plus one "
    "supervisor-to-worker process limit; append authorization, attempt and ACTION_STARTED before "
    "observation and one terminal after; no credential value recording, Docker start/pull/load/"
    "image-store mutation/container operation, network/transport, provider/evaluator/agent, "
    "candidate/cost/paid execution, retry/replacement/resume."
)


class TypedDiagnosticActivationError(ContractError):
    """The v25 activation successor failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TypedDiagnosticActivationError(message)


def _utc(value: datetime, *, label: str) -> datetime:
    _require(value.tzinfo is not None, f"{label} must be timezone-aware")
    _require(value.utcoffset() == UTC.utcoffset(value), f"{label} must be UTC")
    return value


def _validate_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("v25 lifecycle time must be UTC")
    return value


UTCDateTime = Annotated[datetime, AfterValidator(_validate_utc)]


class V24SourceBinding(FrozenStrictModel):
    source_commit: Literal["870558afecc3c1ebbefd04b9acc78e138fc5d632"] = V24_SOURCE_COMMIT
    source_tree: Literal["6a2fc91416b17f24ae9bf794dc9b75968b5bd380"] = V24_SOURCE_TREE
    qualification_commit: Literal["545d14d653d952464fb25287a53bb59b624785b0"] = (
        V24_QUALIFICATION_COMMIT
    )
    contract_id: Literal[
        "ncpcontract_f6fe2bdf24727ab0ba7b32bc86f4678bd253bd4e4652b8eb83acce7660952ed1"
    ] = V24_CONTRACT_ID
    contract_content_hash: Literal[
        "sha256:f6fe2bdf24727ab0ba7b32bc86f4678bd253bd4e4652b8eb83acce7660952ed1"
    ] = "sha256:f6fe2bdf24727ab0ba7b32bc86f4678bd253bd4e4652b8eb83acce7660952ed1"
    source_qualification_hash: Literal[
        "sha256:79423fd51f0b951e8b4c7565396d6f4e49447604fb33acee894a9c0644a5bcb6"
    ] = V24_QUALIFICATION_HASH
    qualification_status: Literal[
        "OFFLINE_V24_ORDER_STABLE_TYPED_DIAGNOSTIC_SOURCE_QUALIFIED_ACTIVATION_CLOSED"
    ]
    state_approval_attempt_or_terminal_count: Literal[0] = 0
    live_observation_count: Literal[0] = 0
    execution_authorized: Literal[False] = False


class RuntimeProfile(FrozenStrictModel):
    lifecycle_entrypoint: Literal[
        "patchloop.evals.order_stable_typed_diagnostic_activation_successor.run_once"
    ] = APPROVED_RUNTIME
    internal_observer_entrypoint: Literal[
        "patchloop.evals.order_stable_typed_diagnostic_activation_successor._run_parent_preflight"
    ] = "patchloop.evals.order_stable_typed_diagnostic_activation_successor._run_parent_preflight"
    live_channel_path: Literal["scripts/run_order_stable_typed_diagnostic_activation_v25.py"] = (
        LIVE_CHANNEL_PATH.as_posix()
    )
    live_channel_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v24_runtime_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v24_projection_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v24_contract_id: Literal[
        "ncpcontract_f6fe2bdf24727ab0ba7b32bc86f4678bd253bd4e4652b8eb83acce7660952ed1"
    ] = V24_CONTRACT_ID
    v24_source_qualification_hash: Literal[
        "sha256:79423fd51f0b951e8b4c7565396d6f4e49447604fb33acee894a9c0644a5bcb6"
    ] = V24_QUALIFICATION_HASH
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    docker_expected_command_count: Literal[8] = 8
    parent_to_supervisor_launch_limit: Literal[1] = 1
    supervisor_to_worker_launch_limit: Literal[1] = 1
    child_flags: tuple[str, ...] = live_channel.CHILD_FLAGS
    fixed_process_environment: dict[str, str] = live_channel.FIXED_PROCESS_ENVIRONMENT
    typed_v24_projection_required: Literal[True] = True
    direct_precanonical_child_to_v24_projection_required: Literal[True] = True
    full_legacy_child_cross_process_transmission_allowed: Literal[False] = False
    value_free_summary_only: Literal[True] = True
    complete_write_and_length_digest_frame_required: Literal[True] = True
    default_observer_reachable_only_after_action_started: Literal[True] = True
    standalone_observation_cli_exposed: Literal[False] = False
    internal_inherited_result_roles_exposed: Literal[True] = True
    raw_invalid_payload_metadata_persisted: Literal[False] = False
    credential_value_hash_prefix_or_length_limit: Literal[0] = 0
    network_call_limit: Literal[0] = 0
    provider_evaluator_agent_call_limit: Literal[0] = 0

    @model_validator(mode="after")
    def validate_profile(self) -> RuntimeProfile:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("v25 approved scopes drifted")
        if self.child_flags != channel.CHILD_FLAGS:
            raise ValueError("v25 child flags drifted")
        if self.fixed_process_environment != channel.FIXED_PROCESS_ENVIRONMENT:
            raise ValueError("v25 fixed process environment drifted")
        return self


class LifecyclePolicy(FrozenStrictModel):
    predecessor_source_qualification_required: Literal[True] = True
    fresh_source_bound_state_required: Literal[True] = True
    separate_exact_approval_required: Literal[True] = True
    exact_immediate_run_statement_required: Literal[True] = True
    authorization_attempt_action_before_observation_required: Literal[True] = True
    one_terminal_required_after_action: Literal[True] = True
    attempt_limit: Literal[1] = 1
    state_or_approval_reusable: Literal[False] = False
    retry_replacement_or_resume_allowed: Literal[False] = False
    v24_source_or_qualification_mutation_allowed: Literal[False] = False


class SourceAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    source_qualification_authorized: Literal[True] = True
    state_approval_attempt_action_or_terminal_during_qualification_authorized: Literal[False] = (
        False
    )
    live_process_or_docker_dotenv_sdk_observation_during_qualification_authorized: Literal[
        False
    ] = False
    credential_value_or_metadata_recording_authorized: Literal[False] = False
    docker_start_pull_load_image_store_or_container_mutation_authorized: Literal[False] = False
    network_transport_or_provider_execution_authorized: Literal[False] = False
    evaluator_agent_candidate_cost_or_paid_execution_authorized: Literal[False] = False


class TypedDiagnosticActivationContract(FrozenStrictModel):
    schema_version: Literal["typed-diagnostic-activation-successor-contract-v25"] = (
        CONTRACT_SCHEMA_VERSION
    )
    contract_version: Literal["ac-evaluator-v2-typed-diagnostic-activation-successor-v25"] = (
        CONTRACT_VERSION
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor: V24SourceBinding
    runtime: RuntimeProfile
    lifecycle: LifecyclePolicy
    authority: SourceAuthority
    state_approval_and_attempt_entrypoints_implemented: Literal[True] = True
    source_qualification_created_runtime_evidence: Literal[False] = False
    execution_currently_authorized: Literal[False] = False
    next_gate: Literal["fresh-exact-v25-state-statement"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> TypedDiagnosticActivationContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected or self.contract_id != v10._derived_id(
            "ncpcontract", expected
        ):
            raise ValueError("v25 contract identity differs")
        return self


class SourceCommitBinding(FrozenStrictModel):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    parents: tuple[str, ...]
    added_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_source(self) -> SourceCommitBinding:
        if self.parents != (SOURCE_PARENT_COMMIT,):
            raise ValueError("v25 source predecessor drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v25 source additions drifted")
        return self


class QualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    source_qualified: Literal[True] = True
    diagnostic_mock_or_live_process_launch_count: Literal[0] = 0
    state_approval_attempt_action_or_terminal_created: Literal[False] = False
    docker_dotenv_sdk_network_or_provider_observation_count: Literal[0] = 0
    credential_value_or_metadata_observation_count: Literal[0] = 0
    external_mutation_count: Literal[0] = 0
    execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class SourceQualification(FrozenStrictModel):
    schema_version: Literal["typed-diagnostic-activation-source-qualification-v25"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal["ac-evaluator-v2-typed-diagnostic-activation-source-20260813-r1"] = (
        QUALIFICATION_ID
    )
    status: Literal["OFFLINE_V25_TYPED_DIAGNOSTIC_ACTIVATION_SOURCE_QUALIFIED_STATE_REQUIRED"] = (
        QUALIFICATION_STATUS
    )
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[v10.CommittedFileBinding, ...]
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_contract_id: Literal[
        "ncpcontract_f6fe2bdf24727ab0ba7b32bc86f4678bd253bd4e4652b8eb83acce7660952ed1"
    ] = V24_CONTRACT_ID
    predecessor_source_qualification_hash: Literal[
        "sha256:79423fd51f0b951e8b4c7565396d6f4e49447604fb33acee894a9c0644a5bcb6"
    ] = V24_QUALIFICATION_HASH
    live_or_mock_process_evidence_created: Literal[False] = False
    authority: QualificationAuthority
    next_gate: Literal["fresh-exact-v25-state-statement"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        return _validate_utc(value)

    @model_validator(mode="after")
    def validate_identity(self) -> SourceQualification:
        expected_paths = tuple(path.as_posix() for path in SOURCE_FILES)
        if tuple(item.path for item in self.source_files) != expected_paths:
            raise ValueError("v25 qualification inventory drifted")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != v10._hash_body(body):
            raise ValueError("v25 qualification identity differs")
        return self


class ChannelCode(StrEnum):
    BINDING_ERROR = "channel_binding_error"
    SUPERVISOR_LAUNCH_ERROR = "supervisor_launch_error"
    SUPERVISOR_NONZERO_EXIT = "supervisor_nonzero_exit"
    SUPERVISOR_FRAME_INVALID = "supervisor_frame_invalid"


class ChannelObservation(FrozenStrictModel):
    schema_version: Literal["typed-diagnostic-live-channel-observation-v25"] = (
        "typed-diagnostic-live-channel-observation-v25"
    )
    code: ChannelCode | None = None
    supervisor_launch_attempt_count: int = Field(ge=0, le=1)
    supervisor_process_return_count: int = Field(ge=0, le=1)
    supervisor_returncode: int | None = None
    supervisor_frame_stage: str
    supervisor_envelope: dict[str, Any] | None = None
    activity_accounting_complete: bool
    unknown_process_activity_possible: bool
    raw_output_return_count: Literal[0] = 0
    exception_message_type_repr_or_traceback_return_count: Literal[0] = 0
    credential_value_hash_prefix_or_length_return_count: Literal[0] = 0

    @model_validator(mode="after")
    def validate_semantics(self) -> ChannelObservation:
        try:
            stage = channel.FrameStage(self.supervisor_frame_stage)
        except ValueError as exc:
            raise ValueError("v25 channel frame stage differs") from exc
        if self.supervisor_process_return_count != int(self.supervisor_returncode is not None):
            raise ValueError("v25 channel return accounting differs")
        if self.supervisor_envelope is not None:
            if (
                self.code is not None
                or self.supervisor_launch_attempt_count != 1
                or self.supervisor_process_return_count != 1
                or self.supervisor_returncode != 0
                or stage != channel.FrameStage.VALID
                or not channel.validate_live_supervisor_envelope(self.supervisor_envelope)
            ):
                raise ValueError("v25 typed supervisor envelope differs")
            activity = self.supervisor_envelope["activity"]
            if (
                self.activity_accounting_complete != activity["activity_accounting_complete"]
                or self.unknown_process_activity_possible
                != activity["unknown_process_activity_possible"]
            ):
                raise ValueError("v25 channel inner accounting differs")
            return self
        if stage == channel.FrameStage.VALID or self.code is None:
            raise ValueError("v25 invalid channel lacks a fixed code")
        if self.code == ChannelCode.BINDING_ERROR:
            expected = (0, 0, None, True, False)
        elif self.code == ChannelCode.SUPERVISOR_LAUNCH_ERROR:
            expected = (1, 0, None, False, True)
        elif self.code == ChannelCode.SUPERVISOR_NONZERO_EXIT:
            if self.supervisor_returncode in {None, 0}:
                raise ValueError("v25 nonzero channel code differs")
            expected = (1, 1, self.supervisor_returncode, False, True)
        else:
            expected = (1, 1, 0, False, True)
        actual = (
            self.supervisor_launch_attempt_count,
            self.supervisor_process_return_count,
            self.supervisor_returncode,
            self.activity_accounting_complete,
            self.unknown_process_activity_possible,
        )
        if actual != expected:
            raise ValueError("v25 invalid channel accounting differs")
        return self


class ParentState(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"
    ERROR = "error"


class ParentReason(StrEnum):
    CONTRACT_BINDING_ERROR = "contract_binding_error"
    DOCKER_CHECKER_ERROR = "docker_checker_error"
    DOCKER_NOT_READY = "docker_not_ready"
    CHILD_CHECKER_ERROR = "child_checker_error"
    DOTENV_NOT_READY = "dotenv_not_ready"
    SDK_DIAGNOSTIC_BLOCKED = "sdk_diagnostic_blocked"
    SDK_DIAGNOSTIC_ERROR = "sdk_diagnostic_error"


def _summary_from_channel(value: ChannelObservation) -> dict[str, Any] | None:
    envelope = value.supervisor_envelope
    if envelope is None or envelope["code"] is not None:
        return None
    projection = envelope["projection"]
    if projection is None or projection["code"] is not None:
        return None
    summary = projection["summary"]
    return summary if type(summary) is dict else None


def _worker_launch_count(value: ChannelObservation) -> int | None:
    envelope = value.supervisor_envelope
    if envelope is None:
        return None
    return envelope["activity"]["worker_launch_attempt_count"]


class PreflightObservation(FrozenStrictModel):
    schema_version: Literal["typed-diagnostic-parent-observation-v25"] = (
        "typed-diagnostic-parent-observation-v25"
    )
    state: ParentState
    reason: ParentReason | None = None
    docker_observation: dict[str, Any] | None = None
    channel_observation: ChannelObservation | None = None
    docker_cli_command_count: int | None = Field(default=None, ge=0, le=8)
    parent_to_supervisor_launch_attempt_count: int | None = Field(default=None, ge=0, le=1)
    supervisor_to_worker_launch_attempt_count: int | None = Field(default=None, ge=0, le=1)
    network_call_count: int | None = Field(default=None, ge=0, le=0)
    provider_evaluator_agent_call_count: int | None = Field(default=None, ge=0, le=0)
    docker_start_pull_load_image_store_or_container_mutation_count: Literal[0] = 0
    credential_value_hash_prefix_or_length_return_count: Literal[0] = 0
    activity_accounting_complete: bool
    unknown_post_marker_activity_possible: bool
    passed: bool

    @model_validator(mode="after")
    def validate_semantics(self) -> PreflightObservation:
        if self.docker_observation is None:
            expected = (
                ParentState.ERROR,
                self.reason,
                None,
                None,
                None,
                False,
                True,
                False,
            )
            actual = (
                self.state,
                self.reason,
                self.docker_cli_command_count,
                self.parent_to_supervisor_launch_attempt_count,
                self.supervisor_to_worker_launch_attempt_count,
                self.activity_accounting_complete,
                self.unknown_post_marker_activity_possible,
                self.passed,
            )
            if (
                self.reason
                not in {
                    ParentReason.CONTRACT_BINDING_ERROR,
                    ParentReason.DOCKER_CHECKER_ERROR,
                }
                or actual != expected
                or self.channel_observation is not None
            ):
                raise ValueError("v25 pre-Docker failure differs")
            return self
        try:
            v7.d137.validate_d137_docker_no_call_preflight_observation(self.docker_observation)
        except ContractError as exc:
            raise ValueError("v25 Docker observation is invalid") from exc
        docker_count = self.docker_observation["activity"]["docker_cli_command_count"]
        if self.docker_cli_command_count != docker_count:
            raise ValueError("v25 Docker count differs")
        if not self.docker_observation["passed"]:
            expected = (
                ParentState.BLOCKED,
                ParentReason.DOCKER_NOT_READY,
                None,
                0,
                0,
                True,
                False,
                False,
            )
            actual = (
                self.state,
                self.reason,
                self.channel_observation,
                self.parent_to_supervisor_launch_attempt_count,
                self.supervisor_to_worker_launch_attempt_count,
                self.activity_accounting_complete,
                self.unknown_post_marker_activity_possible,
                self.passed,
            )
            if (
                actual != expected
                or self.network_call_count != 0
                or self.provider_evaluator_agent_call_count != 0
            ):
                raise ValueError("v25 Docker-blocked projection differs")
            return self
        if self.channel_observation is None:
            raise ValueError("v25 Docker-ready observation lacks channel")
        channel_value = self.channel_observation
        if (
            self.parent_to_supervisor_launch_attempt_count
            != channel_value.supervisor_launch_attempt_count
            or self.supervisor_to_worker_launch_attempt_count != _worker_launch_count(channel_value)
            or self.activity_accounting_complete != channel_value.activity_accounting_complete
            or self.unknown_post_marker_activity_possible
            != channel_value.unknown_process_activity_possible
        ):
            raise ValueError("v25 channel accounting projection differs")
        summary = _summary_from_channel(channel_value)
        if summary is None:
            expected = (ParentState.ERROR, ParentReason.CHILD_CHECKER_ERROR, False)
            counts = (None, None)
        elif summary["state"] == "error":
            expected = (ParentState.ERROR, ParentReason.SDK_DIAGNOSTIC_ERROR, False)
            counts = (
                summary["activity"]["network_call_count"],
                summary["activity"]["provider_evaluator_agent_call_count"],
            )
        elif summary["state"] == "blocked" and summary["diagnostic"] is None:
            expected = (ParentState.BLOCKED, ParentReason.DOTENV_NOT_READY, False)
            counts = (
                summary["activity"]["network_call_count"],
                summary["activity"]["provider_evaluator_agent_call_count"],
            )
        elif summary["state"] == "blocked":
            expected = (ParentState.BLOCKED, ParentReason.SDK_DIAGNOSTIC_BLOCKED, False)
            counts = (
                summary["activity"]["network_call_count"],
                summary["activity"]["provider_evaluator_agent_call_count"],
            )
        else:
            expected = (ParentState.READY, None, True)
            counts = (
                summary["activity"]["network_call_count"],
                summary["activity"]["provider_evaluator_agent_call_count"],
            )
        if (self.state, self.reason, self.passed) != expected:
            raise ValueError("v25 parent terminal mapping differs")
        if (self.network_call_count, self.provider_evaluator_agent_call_count) != counts:
            raise ValueError("v25 child activity projection differs")
        return self


class StateEvidence(FrozenStrictModel):
    schema_version: Literal["typed-diagnostic-activation-state-v25"]
    state_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_source_qualification_hash: Literal[
        "sha256:79423fd51f0b951e8b4c7565396d6f4e49447604fb33acee894a9c0644a5bcb6"
    ] = V24_QUALIFICATION_HASH
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
            raise ValueError("v25 state identity differs")
        return self


class ApprovalBinding(FrozenStrictModel):
    schema_version: Literal["typed-diagnostic-activation-approval-v25"]
    approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    statement_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_runtime: Literal[
        "patchloop.evals.order_stable_typed_diagnostic_activation_successor.run_once"
    ] = APPROVED_RUNTIME
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    parent_to_supervisor_launch_limit: Literal[1] = 1
    supervisor_to_worker_launch_limit: Literal[1] = 1
    future_attempt_limit: Literal[1] = 1
    attempt_started: Literal[False] = False
    reusable: Literal[False] = False
    retry_replacement_or_resume_authorized: Literal[False] = False
    recorded_at: UTCDateTime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> ApprovalBinding:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("v25 approval scopes differ")
        body = self.model_dump(mode="json", exclude={"approval_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected or self.approval_id != v10._derived_id(
            "ncpapproval", expected
        ):
            raise ValueError("v25 approval identity differs")
        return self


class RunAuthorization(FrozenStrictModel):
    schema_version: Literal["typed-diagnostic-activation-run-authorization-v25"]
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
            raise ValueError("v25 run authorization identity differs")
        return self


class AttemptIntent(FrozenStrictModel):
    schema_version: Literal["typed-diagnostic-activation-attempt-v25"]
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
            raise ValueError("v25 attempt identity differs")
        return self


class ActionStarted(FrozenStrictModel):
    schema_version: Literal["typed-diagnostic-activation-action-started-v25"]
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
            raise ValueError("v25 action identity differs")
        return self


class TerminalTransition(FrozenStrictModel):
    schema_version: Literal["typed-diagnostic-activation-terminal-v25"]
    terminal_id: str = Field(pattern=r"^ncpterminal_[0-9a-f]{64}$")
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    action_started_id: str = Field(pattern=r"^ncpstarted_[0-9a-f]{64}$")
    previous_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sequence: Literal[2] = 2
    outcome: ParentState
    reason: ParentReason | Literal["lifecycle_checker_error"] | None = None
    observation: PreflightObservation | None = None
    activity_accounting_complete: bool
    unknown_post_marker_activity_possible: bool
    retry_or_resume_allowed: Literal[False] = False
    network_call_count: int | None = Field(default=None, ge=0, le=0)
    provider_evaluator_agent_call_count: int | None = Field(default=None, ge=0, le=0)
    docker_start_pull_load_image_store_or_container_mutation_count: Literal[0] = 0
    credential_value_hash_prefix_or_length_count: Literal[0] = 0
    recorded_at: UTCDateTime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> TerminalTransition:
        if self.observation is None:
            expected = (
                ParentState.ERROR,
                "lifecycle_checker_error",
                False,
                True,
                None,
                None,
            )
        else:
            expected = (
                self.observation.state,
                self.observation.reason,
                self.observation.activity_accounting_complete,
                self.observation.unknown_post_marker_activity_possible,
                self.observation.network_call_count,
                self.observation.provider_evaluator_agent_call_count,
            )
        actual = (
            self.outcome,
            self.reason,
            self.activity_accounting_complete,
            self.unknown_post_marker_activity_possible,
            self.network_call_count,
            self.provider_evaluator_agent_call_count,
        )
        if actual != expected:
            raise ValueError("v25 terminal projection differs")
        body = self.model_dump(mode="json", exclude={"terminal_id", "content_hash"})
        expected_hash = v10._hash_body(body)
        if self.content_hash != expected_hash or self.terminal_id != v10._derived_id(
            "ncpterminal", expected_hash
        ):
            raise ValueError("v25 terminal identity differs")
        return self


def _load_v24_source(
    root: Path,
) -> tuple[v24.OrderStableDiagnosticContract, v24.SourceQualification]:
    summary = v24.validate_source_qualification(repository=root)
    contract_raw = v10._read(root, v24.CONTRACT_PATH)
    qualification_raw = v10._read(root, v24.QUALIFICATION_PATH)
    contract = v24.OrderStableDiagnosticContract.model_validate_json(contract_raw)
    qualification = v24.SourceQualification.model_validate_json(qualification_raw)
    _require(contract_raw == v10._canonical(contract), "v24 contract bytes differ")
    _require(qualification_raw == v10._canonical(qualification), "v24 qualification bytes differ")
    _require(
        contract_raw
        == v10._git(root, "show", f"{V24_SOURCE_COMMIT}:{v24.CONTRACT_PATH.as_posix()}"),
        "v24 committed contract differs",
    )
    _require(
        qualification_raw
        == v10._git(
            root,
            "show",
            f"{V24_QUALIFICATION_COMMIT}:{v24.QUALIFICATION_PATH.as_posix()}",
        ),
        "v24 committed qualification differs",
    )
    _require(
        contract.contract_id == V24_CONTRACT_ID
        and qualification.contract_id == V24_CONTRACT_ID
        and qualification.content_hash == V24_QUALIFICATION_HASH
        and qualification.source_commit.commit == V24_SOURCE_COMMIT
        and qualification.source_commit.tree == V24_SOURCE_TREE
        and summary["qualification_hash"] == V24_QUALIFICATION_HASH
        and sha256_bytes(contract_raw) == V24_CONTRACT_FILE_SHA256
        and len(contract_raw) == V24_CONTRACT_FILE_BYTES
        and sha256_bytes(qualification_raw) == V24_QUALIFICATION_FILE_SHA256
        and len(qualification_raw) == V24_QUALIFICATION_FILE_BYTES
        and qualification.authority.state_approval_attempt_action_or_terminal_created is False
        and qualification.authority.execution_authorized is False,
        "v24 source-only boundary differs",
    )
    return contract, qualification


def _predecessor_binding(root: Path) -> V24SourceBinding:
    contract, qualification = _load_v24_source(root)
    return V24SourceBinding(
        contract_content_hash=contract.content_hash,
        qualification_status=qualification.status,
    )


def _runtime_profile(root: Path) -> RuntimeProfile:
    _load_v24_source(root)
    return RuntimeProfile(
        live_channel_file_sha256=sha256_bytes(v10._read(root, LIVE_CHANNEL_PATH)),
        v24_runtime_file_sha256=sha256_bytes(v10._read(root, v24.RUNTIME_PATH)),
        v24_projection_file_sha256=sha256_bytes(v10._read(root, v24.PROJECTION_PATH)),
    )


def _build_contract(root: Path) -> TypedDiagnosticActivationContract:
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "predecessor": _predecessor_binding(root).model_dump(mode="json"),
        "runtime": _runtime_profile(root).model_dump(mode="json"),
        "lifecycle": LifecyclePolicy().model_dump(mode="json"),
        "authority": SourceAuthority().model_dump(mode="json"),
        "state_approval_and_attempt_entrypoints_implemented": True,
        "source_qualification_created_runtime_evidence": False,
        "execution_currently_authorized": False,
        "next_gate": NEXT_GATE,
    }
    content_hash = v10._hash_body(body)
    return TypedDiagnosticActivationContract(
        **body,
        contract_id=v10._derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def load_contract(*, repository: str | Path | None = None) -> TypedDiagnosticActivationContract:
    root = v10._root(repository)
    raw = v10._read(root, CONTRACT_PATH)
    try:
        value = TypedDiagnosticActivationContract.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise TypedDiagnosticActivationError("v25 contract artifact is invalid") from exc
    _require(raw == v10._canonical(value), "v25 contract bytes are not canonical")
    _require(value == _build_contract(root), "v25 contract differs from source")
    return value


def materialize_contract(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    value = _build_contract(root)
    raw = v10._canonical(value)
    target = v10._logical_path(root, CONTRACT_PATH, must_exist=False)
    if target.exists():
        _require(v10._read(root, CONTRACT_PATH) == raw, "v25 contract already differs")
    else:
        v10._write_once(root, CONTRACT_PATH, raw)
    return {
        "status": "OFFLINE_V25_ACTIVATION_CONTRACT_MATERIALIZED_EXECUTION_CLOSED",
        "contract_id": value.contract_id,
        "contract_content_hash": value.content_hash,
        "artifact_path": CONTRACT_PATH.as_posix(),
        "artifact_file_sha256": sha256_bytes(raw),
        "artifact_bytes": len(raw),
        "diagnostic_mock_or_live_processes_launched": 0,
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
        "next_gate": "exact-source-commit-and-offline-qualification",
    }


def _source_commit(root: Path, selected: str) -> SourceCommitBinding:
    commit = v10._git(root, "rev-parse", f"{selected}^{{commit}}").decode("ascii").strip()
    tree = v10._git(root, "rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    row = v10._git(root, "rev-list", "--parents", "-n", "1", commit).decode().split()
    _require(row and row[0] == commit and len(row) == 2, "v25 source parent failed")
    lines = (
        v10._git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", row[1], commit)
        .decode("utf-8")
        .splitlines()
    )
    added = tuple(sorted(parts[1] for line in lines if (parts := line.split("\t"))[:1] == ["A"]))
    _require(len(lines) == len(added), "v25 source contains non-addition changes")
    return SourceCommitBinding(commit=commit, tree=tree, parents=(row[1],), added_paths=added)


def _build_qualification(
    root: Path, *, source_commit: str, recorded_at: datetime
) -> SourceQualification:
    contract = load_contract(repository=root)
    _load_v24_source(root)
    commit = _source_commit(root, source_commit)
    pairs = tuple(v10._committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(pair[0] for pair in pairs)
    contract_index = SOURCE_FILES.index(CONTRACT_PATH)
    _require(pairs[contract_index][1] == v10._canonical(contract), "committed v25 contract differs")
    for path, pair in zip(SOURCE_FILES, pairs, strict=True):
        _require(v10._read(root, path) == pair[1], f"working v25 dependency differs: {path}")
    body = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": QUALIFICATION_STATUS,
        "recorded_at": recorded_at,
        "source_commit": commit.model_dump(mode="json"),
        "source_files": [item.model_dump(mode="json") for item in files],
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "predecessor_contract_id": V24_CONTRACT_ID,
        "predecessor_source_qualification_hash": V24_QUALIFICATION_HASH,
        "live_or_mock_process_evidence_created": False,
        "authority": QualificationAuthority().model_dump(mode="json"),
        "next_gate": NEXT_GATE,
    }
    return SourceQualification(**body, content_hash=v10._hash_body(body))


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
        "diagnostic_mock_or_live_process_launch_count": 0,
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
        "next_gate": value.next_gate,
    }


def qualify_source(*, source_commit: str, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    value = _build_qualification(root, source_commit=source_commit, recorded_at=datetime.now(UTC))
    raw = v10._canonical(value)
    v10._write_once(root, QUALIFICATION_PATH, raw)
    return _qualification_summary(value, raw)


def validate_source_qualification(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    raw = v10._read(root, QUALIFICATION_PATH)
    value = SourceQualification.model_validate_json(raw)
    _require(raw == v10._canonical(value), "v25 qualification bytes are not canonical")
    expected = _build_qualification(
        root,
        source_commit=value.source_commit.commit,
        recorded_at=value.recorded_at,
    )
    _require(value == expected, "v25 qualification differs from committed source")
    return _qualification_summary(value, raw)


def _load_qualification(root: Path) -> SourceQualification:
    validate_source_qualification(repository=root)
    return SourceQualification.model_validate_json(v10._read(root, QUALIFICATION_PATH))


def _contract_error_observation(reason: ParentReason) -> PreflightObservation:
    return PreflightObservation(
        state=ParentState.ERROR,
        reason=reason,
        activity_accounting_complete=False,
        unknown_post_marker_activity_possible=True,
        passed=False,
    )


def _channel_from_process(value: dict[str, Any]) -> ChannelObservation:
    frame_stage = value["frame_stage"]
    envelope = value["envelope"]
    if envelope is not None:
        code = None
    elif value["process_return_count"] == 0:
        code = ChannelCode.SUPERVISOR_LAUNCH_ERROR
    elif value["returncode"] not in {None, 0}:
        code = ChannelCode.SUPERVISOR_NONZERO_EXIT
    else:
        code = ChannelCode.SUPERVISOR_FRAME_INVALID
    return ChannelObservation(
        code=code,
        supervisor_launch_attempt_count=value["launch_attempt_count"],
        supervisor_process_return_count=value["process_return_count"],
        supervisor_returncode=value["returncode"],
        supervisor_frame_stage=frame_stage,
        supervisor_envelope=envelope,
        activity_accounting_complete=value["activity_accounting_complete"],
        unknown_process_activity_possible=value["unknown_process_activity_possible"],
    )


def _run_live_channel(
    contract: TypedDiagnosticActivationContract,
    *,
    repository: str | Path | None = None,
    runner: Callable[..., dict[str, Any]] = live_channel.run_live_supervisor_process,
) -> ChannelObservation:
    root = v10._root(repository)
    try:
        checked = TypedDiagnosticActivationContract.model_validate(contract.model_dump(mode="json"))
        _require(checked == load_contract(repository=root), "v25 runtime contract differs")
        _load_v24_source(root)
        _require(
            sha256_bytes(v10._read(root, LIVE_CHANNEL_PATH))
            == contract.runtime.live_channel_file_sha256,
            "v25 live channel source differs",
        )
        _require(
            sha256_bytes(v10._read(root, v24.PROJECTION_PATH))
            == contract.runtime.v24_projection_file_sha256,
            "v25 v24 projection source differs",
        )
    except Exception:
        return ChannelObservation(
            code=ChannelCode.BINDING_ERROR,
            supervisor_launch_attempt_count=0,
            supervisor_process_return_count=0,
            supervisor_returncode=None,
            supervisor_frame_stage=channel.FrameStage.NOT_EVALUATED.value,
            activity_accounting_complete=True,
            unknown_process_activity_possible=False,
        )
    try:
        observed = runner(root)
        return _channel_from_process(observed)
    except Exception:
        return ChannelObservation(
            code=ChannelCode.SUPERVISOR_LAUNCH_ERROR,
            supervisor_launch_attempt_count=1,
            supervisor_process_return_count=0,
            supervisor_returncode=None,
            supervisor_frame_stage=channel.FrameStage.NOT_EVALUATED.value,
            activity_accounting_complete=False,
            unknown_process_activity_possible=True,
        )


def _compose_parent_observation(
    docker: dict[str, Any], channel_observation: ChannelObservation | None
) -> PreflightObservation:
    count = docker["activity"]["docker_cli_command_count"]
    if not docker["passed"]:
        return PreflightObservation(
            state=ParentState.BLOCKED,
            reason=ParentReason.DOCKER_NOT_READY,
            docker_observation=docker,
            docker_cli_command_count=count,
            parent_to_supervisor_launch_attempt_count=0,
            supervisor_to_worker_launch_attempt_count=0,
            network_call_count=0,
            provider_evaluator_agent_call_count=0,
            activity_accounting_complete=True,
            unknown_post_marker_activity_possible=False,
            passed=False,
        )
    assert channel_observation is not None
    summary = _summary_from_channel(channel_observation)
    if summary is None:
        state, reason, passed = ParentState.ERROR, ParentReason.CHILD_CHECKER_ERROR, False
        network = provider = None
    elif summary["state"] == "error":
        state, reason, passed = ParentState.ERROR, ParentReason.SDK_DIAGNOSTIC_ERROR, False
        network = summary["activity"]["network_call_count"]
        provider = summary["activity"]["provider_evaluator_agent_call_count"]
    elif summary["state"] == "blocked" and summary["diagnostic"] is None:
        state, reason, passed = ParentState.BLOCKED, ParentReason.DOTENV_NOT_READY, False
        network = summary["activity"]["network_call_count"]
        provider = summary["activity"]["provider_evaluator_agent_call_count"]
    elif summary["state"] == "blocked":
        state, reason, passed = ParentState.BLOCKED, ParentReason.SDK_DIAGNOSTIC_BLOCKED, False
        network = summary["activity"]["network_call_count"]
        provider = summary["activity"]["provider_evaluator_agent_call_count"]
    else:
        state, reason, passed = ParentState.READY, None, True
        network = summary["activity"]["network_call_count"]
        provider = summary["activity"]["provider_evaluator_agent_call_count"]
    return PreflightObservation(
        state=state,
        reason=reason,
        docker_observation=docker,
        channel_observation=channel_observation,
        docker_cli_command_count=count,
        parent_to_supervisor_launch_attempt_count=(
            channel_observation.supervisor_launch_attempt_count
        ),
        supervisor_to_worker_launch_attempt_count=_worker_launch_count(channel_observation),
        network_call_count=network,
        provider_evaluator_agent_call_count=provider,
        activity_accounting_complete=channel_observation.activity_accounting_complete,
        unknown_post_marker_activity_possible=(
            channel_observation.unknown_process_activity_possible
        ),
        passed=passed,
    )


def _run_parent_preflight(
    contract: TypedDiagnosticActivationContract,
    *,
    repository: str | Path | None = None,
    docker_observer: Callable[..., dict[str, Any]] = (
        v7.d137.run_d137_docker_no_call_preflight_observation
    ),
    channel_observer: Callable[..., ChannelObservation] = _run_live_channel,
) -> PreflightObservation:
    root = v10._root(repository)
    try:
        checked = TypedDiagnosticActivationContract.model_validate(contract.model_dump(mode="json"))
        _require(checked == load_contract(repository=root), "v25 parent contract differs")
        _load_v24_source(root)
    except Exception:
        return _contract_error_observation(ParentReason.CONTRACT_BINDING_ERROR)
    try:
        docker = docker_observer(repository=root)
        v7.d137.validate_d137_docker_no_call_preflight_observation(docker)
    except Exception:
        return _contract_error_observation(ParentReason.DOCKER_CHECKER_ERROR)
    if not docker["passed"]:
        return _compose_parent_observation(docker, None)
    try:
        observed = channel_observer(contract, repository=root)
        typed = ChannelObservation.model_validate(observed.model_dump(mode="json"))
    except Exception:
        typed = ChannelObservation(
            code=ChannelCode.SUPERVISOR_LAUNCH_ERROR,
            supervisor_launch_attempt_count=1,
            supervisor_process_return_count=0,
            supervisor_returncode=None,
            supervisor_frame_stage=channel.FrameStage.NOT_EVALUATED.value,
            activity_accounting_complete=False,
            unknown_process_activity_possible=True,
        )
    return _compose_parent_observation(docker, typed)


def expected_state_statement(
    contract: TypedDiagnosticActivationContract, qualification: SourceQualification
) -> str:
    _require(qualification.contract_id == contract.contract_id, "v25 state contract differs")
    return STATE_TEMPLATE.format(
        contract_id=contract.contract_id,
        qualification_hash=qualification.content_hash,
        v24_qualification_hash=contract.predecessor.source_qualification_hash,
    )


def build_state_evidence(
    contract: TypedDiagnosticActivationContract,
    qualification: SourceQualification,
    *,
    statement: str,
    recorded_at: datetime,
) -> StateEvidence:
    _require(
        statement == expected_state_statement(contract, qualification),
        "v25 state statement differs",
    )
    recorded_at = _utc(recorded_at, label="v25 state recorded_at")
    _require(recorded_at >= qualification.recorded_at, "v25 state predates qualification")
    body = {
        "schema_version": "typed-diagnostic-activation-state-v25",
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
        "status": "V25_STATE_RECORDED_SELF_ATTESTED_NO_EXECUTION",
        "state_id": value.state_id,
        "state_content_hash": value.content_hash,
        "external_observations_made": 0,
        "execution_authorized": False,
    }


def _load_state(root: Path) -> StateEvidence:
    raw = v10._read(root, STATE_PATH)
    value = StateEvidence.model_validate_json(raw)
    _require(raw == v10._canonical(value), "v25 state bytes differ")
    return value


def expected_approval_statement(
    contract: TypedDiagnosticActivationContract,
    qualification: SourceQualification,
    state: StateEvidence,
) -> str:
    _require(
        state.contract_id == contract.contract_id
        and state.source_qualification_hash == qualification.content_hash,
        "v25 approval state binding differs",
    )
    return APPROVAL_TEMPLATE.format(
        contract_id=contract.contract_id,
        qualification_hash=qualification.content_hash,
        state_id=state.state_id,
        state_hash=state.content_hash,
    )


def build_approval(
    contract: TypedDiagnosticActivationContract,
    qualification: SourceQualification,
    state: StateEvidence,
    *,
    statement: str,
    recorded_at: datetime,
) -> ApprovalBinding:
    _require(
        statement == expected_approval_statement(contract, qualification, state),
        "v25 approval statement differs",
    )
    recorded_at = _utc(recorded_at, label="v25 approval recorded_at")
    _require(recorded_at >= state.recorded_at, "v25 approval predates state")
    body = {
        "schema_version": "typed-diagnostic-activation-approval-v25",
        "contract_id": contract.contract_id,
        "source_qualification_hash": qualification.content_hash,
        "state_id": state.state_id,
        "state_content_hash": state.content_hash,
        "statement_sha256": sha256_bytes(statement.encode("utf-8")),
        "approved_runtime": APPROVED_RUNTIME,
        "approved_scopes": APPROVED_SCOPES,
        "parent_to_supervisor_launch_limit": 1,
        "supervisor_to_worker_launch_limit": 1,
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
        "status": "V25_APPROVAL_RECORDED_ATTEMPT_NOT_STARTED",
        "approval_id": value.approval_id,
        "approval_content_hash": value.content_hash,
        "attempt_started": False,
        "external_observations_made": 0,
    }


def _load_approval(root: Path) -> ApprovalBinding:
    raw = v10._read(root, APPROVAL_PATH)
    value = ApprovalBinding.model_validate_json(raw)
    _require(raw == v10._canonical(value), "v25 approval bytes differ")
    return value


def expected_run_statement(
    contract: TypedDiagnosticActivationContract,
    qualification: SourceQualification,
    state: StateEvidence,
    approval: ApprovalBinding,
) -> str:
    _require(
        approval.contract_id == contract.contract_id
        and approval.source_qualification_hash == qualification.content_hash
        and approval.state_id == state.state_id
        and approval.state_content_hash == state.content_hash,
        "v25 run approval binding differs",
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
    contract: TypedDiagnosticActivationContract,
    qualification: SourceQualification,
    state: StateEvidence,
    approval: ApprovalBinding,
    *,
    statement: str,
    recorded_at: datetime,
) -> RunAuthorization:
    _require(
        statement == expected_run_statement(contract, qualification, state, approval),
        "v25 run statement differs",
    )
    recorded_at = _utc(recorded_at, label="v25 authorization recorded_at")
    _require(recorded_at >= approval.recorded_at, "v25 authorization predates approval")
    body = {
        "schema_version": "typed-diagnostic-activation-run-authorization-v25",
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
    _require(not any(row["exists"] for row in rows), "v25 attempt ledger is consumed")
    return v10._hash_body({"rows": rows})


def _canonical_empty_ledger_hash() -> str:
    return v10._hash_body(
        {"rows": [{"path": path.as_posix(), "exists": False} for path in _ledger_paths()]}
    )


def _build_attempt(
    authorization: RunAuthorization, *, ledger_hash: str, created_at: datetime
) -> AttemptIntent:
    created_at = _utc(created_at, label="v25 attempt created_at")
    _require(created_at >= authorization.recorded_at, "v25 attempt predates authorization")
    body = {
        "schema_version": "typed-diagnostic-activation-attempt-v25",
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
    recorded_at = _utc(recorded_at, label="v25 action recorded_at")
    _require(recorded_at >= attempt.created_at, "v25 action predates attempt")
    body = {
        "schema_version": "typed-diagnostic-activation-action-started-v25",
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
    observation: PreflightObservation | None,
    recorded_at: datetime,
) -> TerminalTransition:
    recorded_at = _utc(recorded_at, label="v25 terminal recorded_at")
    _require(recorded_at >= action.recorded_at, "v25 terminal predates action")
    if observation is None:
        outcome = ParentState.ERROR
        reason: ParentReason | str | None = "lifecycle_checker_error"
        complete, unknown = False, True
        network = provider = None
    else:
        observation = PreflightObservation.model_validate(observation.model_dump(mode="json"))
        outcome, reason = observation.state, observation.reason
        complete = observation.activity_accounting_complete
        unknown = observation.unknown_post_marker_activity_possible
        network = observation.network_call_count
        provider = observation.provider_evaluator_agent_call_count
    body = {
        "schema_version": "typed-diagnostic-activation-terminal-v25",
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
        "network_call_count": network,
        "provider_evaluator_agent_call_count": provider,
        "docker_start_pull_load_image_store_or_container_mutation_count": 0,
        "credential_value_hash_prefix_or_length_count": 0,
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
    parent_observer: Callable[..., PreflightObservation] = _run_parent_preflight,
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
        observation = PreflightObservation.model_validate(observation.model_dump(mode="json"))
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
    _require(b"openai_api_key=" not in lowered and b"sk-" not in lowered, "v25 terminal leaks")
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
        _require(raw == v10._canonical(value), f"v25 {path.name} bytes differ")
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
        "v25 state binding differs",
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
        "v25 approval binding differs",
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
        "v25 run authorization differs",
    )
    _require(
        attempt.run_authorization_id == authorization.authorization_id
        and attempt.run_authorization_content_hash == authorization.content_hash
        and attempt.ledger_snapshot_hash == _canonical_empty_ledger_hash(),
        "v25 attempt authorization differs",
    )
    _require(
        action.attempt_id == attempt.attempt_id
        and action.attempt_content_hash == attempt.content_hash
        and terminal.attempt_id == attempt.attempt_id
        and terminal.action_started_id == action.marker_id
        and terminal.previous_content_hash == action.content_hash,
        "v25 terminal chain differs",
    )
    _require(
        qualification.recorded_at
        <= state.recorded_at
        <= approval.recorded_at
        <= authorization.recorded_at
        <= attempt.created_at
        <= action.recorded_at
        <= terminal.recorded_at,
        "v25 lifecycle chronology differs",
    )
    terminal_raw = v10._canonical(terminal).lower()
    _require(
        b"openai_api_key=" not in terminal_raw and b"sk-" not in terminal_raw,
        "v25 persisted terminal leaks",
    )
    return {
        "status": "V25_TYPED_CHANNEL_NO_CALL_PREFLIGHT_TERMINAL_VALID",
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
    "QUALIFICATION_PATH",
    "RUN_AUTHORIZATION_PATH",
    "STATE_PATH",
    "TERMINAL_PATH",
    "ChannelObservation",
    "PreflightObservation",
    "TypedDiagnosticActivationContract",
    "TypedDiagnosticActivationError",
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
