"""Approval-gated v5 preflight for an already-running Docker daemon.

Source preparation and qualification are offline.  Runtime is one-use and may
only perform the D-137 read-only Docker snapshot followed, when Docker is
ready, by the isolated dotenv-membership and reject-dispatch SDK observation.
It cannot start Docker, pull images, mutate the image store, or operate a
container.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from patchloop.contracts import FrozenStrictModel
from patchloop.errors import ContractError
from patchloop.evals import executable_no_call_preflight as v3
from patchloop.evals import manual_docker_start_state_successor as v4
from patchloop.evals import versioned_no_call_preflight as v1
from patchloop.runtime import repository_root
from patchloop.util import safe_relative_path, sha256_bytes, sha256_json

CONTRACT_SCHEMA_VERSION = "versioned-no-start-executable-preflight-contract-v5"
CONTRACT_VERSION = "ac-evaluator-v2-no-start-executable-preflight-v5"
CONTRACT_PATH = Path("experiments/evaluator-v2-no-start-executable-preflight-v5.contract.json")
PREDECESSOR_STATE_COMMIT = "6e068a714d4b516e75c381839e64fc0dcbd27e07"

RUNTIME_PATH = Path("patchloop/evals/no_start_executable_preflight.py")
BUILD_SCRIPT_PATH = Path("scripts/build_no_start_executable_preflight.py")
TEST_PATH = Path("tests/test_no_start_executable_preflight.py")
CHILD_PATH = v3.CHILD_PATH
D137_PATH = Path("patchloop/evals/d137_no_call_preflight.py")
V3_RUNTIME_PATH = v3.RUNTIME_PATH

QUALIFICATION_SCHEMA_VERSION = "no-start-executable-preflight-source-qualification-v5"
QUALIFICATION_ID = "ac-evaluator-v2-no-start-executable-preflight-source-20260812-r1"
QUALIFICATION_STATUS = "OFFLINE_NO_START_EXECUTABLE_SOURCE_QUALIFIED_EXACT_APPROVAL_REQUIRED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-no-start-executable-preflight-v5-source-qualification.json"
)
APPROVAL_RECEIPT_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-no-start-executable-preflight-v5-exact-approval-receipt.json"
)
APPROVAL_BINDING_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-no-start-executable-preflight-v5-approval-binding.json"
)
ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-no-start-executable-preflight-v5-attempt-intent.json"
)
ACTION_STARTED_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-no-start-executable-preflight-v5-action-started.json"
)
TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-no-start-executable-preflight-v5-terminal.json"
)

SOURCE_ADDED_PATHS = tuple(
    sorted(
        (
            CONTRACT_PATH.as_posix(),
            RUNTIME_PATH.as_posix(),
            BUILD_SCRIPT_PATH.as_posix(),
            TEST_PATH.as_posix(),
        )
    )
)
SOURCE_FILES = tuple(
    sorted(
        (
            CONTRACT_PATH,
            RUNTIME_PATH,
            BUILD_SCRIPT_PATH,
            TEST_PATH,
            CHILD_PATH,
            D137_PATH,
            V3_RUNTIME_PATH,
            v4.CONTRACT_PATH,
            v4.RUNTIME_PATH,
            v4.QUALIFICATION_PATH,
            v4.USER_ATTESTATION_PATH,
            v4.STATE_EVIDENCE_PATH,
        ),
        key=lambda item: item.as_posix(),
    )
)

APPROVED_SCOPES = (
    "already-running-docker-read-only-two-snapshot-eight-command-observation",
    "isolated-dotenv-exact-openai-api-key-membership",
    "isolated-sdk-import-fixed-placeholder-reject-dispatch",
)
IDENTITY_ASSURANCE = v4.IDENTITY_ASSURANCE
NEXT_GATE = "fresh-exact-approval-reconfirm-manual-start-and-dotenv"


class NoStartExecutablePreflightError(ContractError):
    """The v5 no-start executable contract failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise NoStartExecutablePreflightError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = repository_root() if repository is None else Path(repository)
    return selected.resolve(strict=True)


def _logical_path(root: Path, relative: Path, *, must_exist: bool) -> Path:
    safe = safe_relative_path(relative.as_posix(), field_name="v5 preflight path")
    selected = root.joinpath(*Path(safe).parts)
    resolved = selected.resolve(strict=must_exist)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise NoStartExecutablePreflightError("v5 preflight path escaped repository") from exc
    return resolved


def _read_bytes(root: Path, relative: Path) -> bytes:
    selected = _logical_path(root, relative, must_exist=True)
    _require(not selected.is_symlink(), f"v5 path is link-like: {relative.as_posix()}")
    before = selected.stat()
    raw = selected.read_bytes()
    after = selected.stat()
    _require(
        (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
        f"v5 path changed while reading: {relative.as_posix()}",
    )
    return raw


def _write_once(root: Path, relative: Path, raw: bytes) -> None:
    selected = _logical_path(root, relative, must_exist=False)
    selected.parent.mkdir(parents=True, exist_ok=True)
    try:
        with selected.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise NoStartExecutablePreflightError(
            f"append-only artifact already exists: {relative.as_posix()}"
        ) from exc
    except OSError as exc:
        raise NoStartExecutablePreflightError(
            f"append-only artifact cannot be written: {relative.as_posix()}"
        ) from exc
    _require(_read_bytes(root, relative) == raw, f"artifact reread differs: {relative.as_posix()}")


def _utc(value: datetime, *, label: str) -> datetime:
    _require(value.tzinfo is not None, f"{label} must be timezone-aware")
    _require(value.utcoffset() == UTC.utcoffset(value), f"{label} must be UTC")
    return value


def _derived_id(prefix: str, content_hash: str) -> str:
    return f"{prefix}_{content_hash.removeprefix('sha256:')}"


def _canonical_bytes(value: FrozenStrictModel) -> bytes:
    return (value.model_dump_json(indent=2) + "\n").encode("utf-8")


def _json_ready(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if hasattr(value, "value") and isinstance(value.value, str):
        return value.value
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def _semantic_hash(body: dict[str, Any]) -> str:
    return sha256_json(_json_ready(body))


class V4StateBinding(FrozenStrictModel):
    state_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    user_attestation_id: str = Field(pattern=r"^ncpattestation_[0-9a-f]{64}$")
    user_attestation_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_change_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_change_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    manual_start_reported: Literal[True] = True
    daemon_ready_verified: Literal[False] = False
    exact_images_present_verified: Literal[False] = False
    container_inventory_verified: Literal[False] = False
    v3_consumed_and_not_reopened: Literal[True] = True
    patchloop_external_observation_count: Literal[0] = 0
    patchloop_mutation_count: Literal[0] = 0

    @model_validator(mode="after")
    def validate_state_commit(self) -> V4StateBinding:
        if self.state_commit != PREDECESSOR_STATE_COMMIT:
            raise ValueError("v4 state commit drifted")
        return self


class NoStartRuntimeProfile(FrozenStrictModel):
    schema_version: Literal["no-start-executable-runtime-profile-v1"] = (
        "no-start-executable-runtime-profile-v1"
    )
    child_path: Literal["scripts/run_dotenv_sdk_no_call_child.py"] = CHILD_PATH.as_posix()
    child_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    d137_observer_path: Literal["patchloop/evals/d137_no_call_preflight.py"] = D137_PATH.as_posix()
    d137_observer_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v3_runtime_path: Literal["patchloop/evals/executable_no_call_preflight.py"] = (
        V3_RUNTIME_PATH.as_posix()
    )
    v3_runtime_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    exact_subject_names: tuple[str, ...] = v3.STATE_CHANGE_SUBJECTS
    docker_observer: Literal["d137-read-only-two-snapshot"] = "d137-read-only-two-snapshot"
    docker_expected_command_count: Literal[8] = 8
    docker_desktop_or_daemon_start_limit: Literal[0] = 0
    docker_image_pull_load_or_store_mutation_limit: Literal[0] = 0
    container_create_start_run_exec_limit: Literal[0] = 0
    dotenv_membership_child_only: Literal[True] = True
    dotenv_entire_file_bytes_confined_to_isolated_child: Literal[True] = True
    credential_value_return_hash_prefix_or_length_limit: Literal[0] = 0
    sdk_uses_fixed_nonsecret_placeholder: Literal[True] = True
    sdk_transport_kind: Literal["httpx.MockTransport-reject-dispatch"] = (
        "httpx.MockTransport-reject-dispatch"
    )
    network_call_limit: Literal[0] = 0
    provider_evaluator_agent_call_limit: Literal[0] = 0
    runtime_implemented: Literal[True] = True

    @model_validator(mode="after")
    def validate_subjects(self) -> NoStartRuntimeProfile:
        if self.exact_subject_names != v3.STATE_CHANGE_SUBJECTS:
            raise ValueError("v5 exact subjects drifted")
        return self


class SourceAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    source_qualification_authorized: Literal[True] = True
    exact_approval_required: Literal[True] = True
    external_preflight_attempt_authorized: Literal[False] = False
    docker_sdk_or_dotenv_observation_authorized: Literal[False] = False
    docker_start_pull_load_or_container_operation_authorized: Literal[False] = False
    network_or_transport_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    execution_hash_candidate_cost_or_paid_execution_authorized: Literal[False] = False
    automatic_retry_replacement_or_resume_authorized: Literal[False] = False


class NoStartExecutableContract(FrozenStrictModel):
    schema_version: Literal["versioned-no-start-executable-preflight-contract-v5"] = (
        CONTRACT_SCHEMA_VERSION
    )
    contract_version: Literal["ac-evaluator-v2-no-start-executable-preflight-v5"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor: V4StateBinding
    evaluator_v2_source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    successor_suite_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_tuple_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_profile: NoStartRuntimeProfile
    transition_policy: v1.PreflightTransitionPolicy
    current_manual_start_and_dotenv_reconfirmation_required: Literal[True] = True
    source_authority: SourceAuthority
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> NoStartExecutableContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected = sha256_json(body)
        if self.content_hash != expected:
            raise ValueError("v5 contract hash mismatch")
        if self.contract_id != _derived_id("ncpcontract", expected):
            raise ValueError("v5 contract id mismatch")
        return self


class CommittedFileBinding(FrozenStrictModel):
    path: str
    blob_oid: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    file_bytes: int = Field(ge=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class SourceCommitBinding(FrozenStrictModel):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    parents: tuple[str, ...]
    added_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_exact_source(self) -> SourceCommitBinding:
        if self.parents != (PREDECESSOR_STATE_COMMIT,):
            raise ValueError("v5 source predecessor drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v5 source additions drifted")
        return self


class QualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    source_qualified: Literal[True] = True
    approval_created_or_inferred: Literal[False] = False
    attempt_or_transition_created: Literal[False] = False
    docker_sdk_dotenv_network_or_provider_observation_count: Literal[0] = 0
    docker_start_pull_load_image_or_container_mutation_count: Literal[0] = 0
    execution_hash_candidate_cost_or_paid_execution_authorized: Literal[False] = False


class SourceQualification(FrozenStrictModel):
    schema_version: Literal["no-start-executable-preflight-source-qualification-v5"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal[
        "ac-evaluator-v2-no-start-executable-preflight-source-20260812-r1"
    ] = QUALIFICATION_ID
    status: Literal["OFFLINE_NO_START_EXECUTABLE_SOURCE_QUALIFIED_EXACT_APPROVAL_REQUIRED"] = (
        QUALIFICATION_STATUS
    )
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[CommittedFileBinding, ...]
    contract_version: Literal["ac-evaluator-v2-no-start-executable-preflight-v5"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    contract_file: CommittedFileBinding
    runtime_file: CommittedFileBinding
    child_file: CommittedFileBinding
    d137_observer_file: CommittedFileBinding
    predecessor_state_file: CommittedFileBinding
    authority: QualificationAuthority
    next_gate: Literal["fresh-exact-approval-reconfirm-manual-start-and-dotenv"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v5 qualification recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> SourceQualification:
        if tuple(item.path for item in self.source_files) != tuple(
            item.as_posix() for item in SOURCE_FILES
        ):
            raise ValueError("v5 qualification inventory drifted")
        by_path = {item.path: item for item in self.source_files}
        expected = (
            (self.contract_file, CONTRACT_PATH),
            (self.runtime_file, RUNTIME_PATH),
            (self.child_file, CHILD_PATH),
            (self.d137_observer_file, D137_PATH),
            (self.predecessor_state_file, v4.STATE_EVIDENCE_PATH),
        )
        if any(binding != by_path.get(path.as_posix()) for binding, path in expected):
            raise ValueError("v5 qualification file projection differs")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != sha256_json(body):
            raise ValueError("v5 qualification hash mismatch")
        return self


class ApprovalReceipt(FrozenStrictModel):
    schema_version: Literal["no-start-preflight-exact-approval-receipt-v5"] = (
        "no-start-preflight-exact-approval-receipt-v5"
    )
    receipt_id: str = Field(pattern=r"^ncpapprovalreceipt_[0-9a-f]{64}$")
    contract_version: Literal["ac-evaluator-v2-no-start-executable-preflight-v5"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_change_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_change_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    current_manual_docker_start_state_reconfirmed: Literal[True] = True
    current_dotenv_placement_reconfirmed: Literal[True] = True
    attempt_limit: Literal[1] = 1
    credential_value_in_approval: Literal[False] = False
    docker_desktop_or_daemon_start_authorized: Literal[False] = False
    image_pull_load_or_store_mutation_authorized: Literal[False] = False
    container_operation_authorized: Literal[False] = False
    network_or_transport_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    execution_hash_candidate_cost_or_paid_execution_authorized: Literal[False] = False
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v5 approval recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> ApprovalReceipt:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("v5 approval scopes drifted")
        body = self.model_dump(mode="json", exclude={"receipt_id", "content_hash"})
        expected = sha256_json(body)
        if self.content_hash != expected:
            raise ValueError("v5 approval receipt hash mismatch")
        if self.receipt_id != _derived_id("ncpapprovalreceipt", expected):
            raise ValueError("v5 approval receipt id mismatch")
        return self


class ApprovalBinding(FrozenStrictModel):
    schema_version: Literal["no-start-preflight-approval-binding-v5"] = (
        "no-start-preflight-approval-binding-v5"
    )
    approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_change_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_change_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    receipt_id: str = Field(pattern=r"^ncpapprovalreceipt_[0-9a-f]{64}$")
    receipt_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    attempt_limit: Literal[1] = 1
    docker_desktop_or_daemon_start_authorized: Literal[False] = False
    image_pull_load_or_store_mutation_authorized: Literal[False] = False
    container_operation_authorized: Literal[False] = False
    network_or_transport_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    execution_hash_candidate_cost_or_paid_execution_authorized: Literal[False] = False
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v5 approval binding recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> ApprovalBinding:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("v5 approval binding scopes drifted")
        body = self.model_dump(mode="json", exclude={"approval_id", "content_hash"})
        expected = sha256_json(body)
        if self.content_hash != expected:
            raise ValueError("v5 approval binding hash mismatch")
        if self.approval_id != _derived_id("ncpapproval", expected):
            raise ValueError("v5 approval binding id mismatch")
        return self


class AttemptIntent(FrozenStrictModel):
    schema_version: Literal["no-start-preflight-attempt-intent-v5"] = (
        "no-start-preflight-attempt-intent-v5"
    )
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_change_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_change_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    approval_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    ledger_snapshot_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    created_at: datetime
    attempt_number: Literal[1] = 1
    one_use: Literal[True] = True
    retry_or_resume_allowed: Literal[False] = False
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v5 attempt created_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> AttemptIntent:
        body = self.model_dump(mode="json", exclude={"attempt_id", "content_hash"})
        expected = sha256_json(body)
        if self.content_hash != expected:
            raise ValueError("v5 attempt hash mismatch")
        if self.attempt_id != _derived_id("ncpattempt", expected):
            raise ValueError("v5 attempt id mismatch")
        return self


class ActionStarted(FrozenStrictModel):
    schema_version: Literal["no-start-preflight-action-started-v5"] = (
        "no-start-preflight-action-started-v5"
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
            raise ValueError("v5 action recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> ActionStarted:
        body = self.model_dump(mode="json", exclude={"marker_id", "content_hash"})
        expected = sha256_json(body)
        if self.content_hash != expected:
            raise ValueError("v5 action hash mismatch")
        if self.marker_id != _derived_id("ncpstarted", expected):
            raise ValueError("v5 action id mismatch")
        return self


class TerminalTransition(FrozenStrictModel):
    schema_version: Literal["no-start-preflight-terminal-v5"] = "no-start-preflight-terminal-v5"
    terminal_id: str = Field(pattern=r"^ncpterminal_[0-9a-f]{64}$")
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    action_started_id: str = Field(pattern=r"^ncpstarted_[0-9a-f]{64}$")
    previous_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sequence: Literal[2] = 2
    outcome: v3.TerminalOutcome
    reason: v3.TerminalReason | None = None
    docker_observation: dict[str, Any] | None = None
    sdk_observation: v3.ExecutableSDKObservation | None = None
    activity_accounting_complete: bool
    unknown_post_marker_activity_possible: bool
    docker_cli_command_count: int | None = Field(default=None, ge=0, le=8)
    dotenv_file_read_count: int | None = Field(default=None, ge=0, le=1)
    sdk_child_start_count: int | None = Field(default=None, ge=0, le=1)
    docker_desktop_or_daemon_start_count: Literal[0] = 0
    image_pull_load_or_store_mutation_count: Literal[0] = 0
    container_operation_count: Literal[0] = 0
    credential_value_return_hash_prefix_or_length_count: Literal[0] = 0
    network_call_count: Literal[0] = 0
    provider_evaluator_agent_call_count: Literal[0] = 0
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v5 terminal recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_terminal(self) -> TerminalTransition:
        if self.docker_observation is not None:
            try:
                v3.d137.validate_d137_docker_no_call_preflight_observation(self.docker_observation)
            except ContractError as exc:
                raise ValueError("v5 Docker observation is invalid") from exc
        if self.outcome == v3.TerminalOutcome.READY:
            if (
                self.reason is not None
                or self.docker_observation is None
                or self.sdk_observation is None
                or not self.docker_observation["passed"]
                or not self.sdk_observation.passed
                or self.docker_cli_command_count != 8
                or self.dotenv_file_read_count != 1
                or self.sdk_child_start_count != 1
            ):
                raise ValueError("v5 READY terminal is incomplete")
        elif self.reason is None:
            raise ValueError("v5 non-READY terminal lacks reason")
        if self.reason == v3.TerminalReason.DOCKER_NOT_READY and (
            self.docker_observation is None
            or self.docker_observation["passed"]
            or self.sdk_observation is not None
            or self.docker_cli_command_count != 8
            or self.dotenv_file_read_count != 0
            or self.sdk_child_start_count != 0
        ):
            raise ValueError("v5 Docker-blocked terminal differs")
        if self.reason in {
            v3.TerminalReason.PYTHON_ENVIRONMENT_NOT_CLEAN,
            v3.TerminalReason.DOTENV_CREDENTIAL_MISSING,
            v3.TerminalReason.SDK_NO_CALL_FAILED,
        } and (
            self.outcome != v3.TerminalOutcome.BLOCKED
            or self.docker_observation is None
            or not self.docker_observation["passed"]
            or self.sdk_observation is None
            or self.sdk_observation.passed
            or (self.outcome, self.reason) != _sdk_reason(self.sdk_observation)
            or self.docker_cli_command_count != 8
        ):
            raise ValueError("v5 SDK-blocked terminal differs")
        if (
            self.outcome == v3.TerminalOutcome.ERROR
            and self.reason != v3.TerminalReason.CHECKER_ERROR
        ):
            raise ValueError("v5 ERROR reason differs")
        if self.activity_accounting_complete:
            expected_docker_count = (
                0
                if self.docker_observation is None
                else self.docker_observation["activity"]["docker_cli_command_count"]
            )
            expected_child_count = (
                0 if self.sdk_observation is None else self.sdk_observation.child_start_count
            )
            expected_dotenv_count = 0
            if self.sdk_observation is not None and self.sdk_observation.child is not None:
                expected_dotenv_count = self.sdk_observation.child.activity.dotenv_file_read_count
            if (
                self.docker_cli_command_count != expected_docker_count
                or self.sdk_child_start_count != expected_child_count
                or self.dotenv_file_read_count != expected_dotenv_count
            ):
                raise ValueError("v5 terminal activity projection differs")
        if self.outcome != v3.TerminalOutcome.ERROR and (
            not self.activity_accounting_complete or self.unknown_post_marker_activity_possible
        ):
            raise ValueError("v5 terminal activity accounting is incomplete")
        if (
            self.outcome == v3.TerminalOutcome.ERROR
            and not self.activity_accounting_complete
            and not self.unknown_post_marker_activity_possible
        ):
            raise ValueError("v5 ERROR hides unknown activity")
        body = self.model_dump(mode="json", exclude={"terminal_id", "content_hash"})
        expected = sha256_json(body)
        if self.content_hash != expected:
            raise ValueError("v5 terminal hash mismatch")
        if self.terminal_id != _derived_id("ncpterminal", expected):
            raise ValueError("v5 terminal id mismatch")
        return self


def _load_v4_chain(
    root: Path,
) -> tuple[
    v4.ManualDockerStartStateContract,
    v4.ManualDockerStartSourceQualification,
    v4.ManualDockerStartUserAttestation,
    v4.ManualDockerStartStateEvidence,
]:
    v4.validate_manual_start_state(repository=root)
    contract = v4.load_contract(repository=root)
    qualification = v4.ManualDockerStartSourceQualification.model_validate_json(
        _read_bytes(root, v4.QUALIFICATION_PATH)
    )
    attestation = v4.ManualDockerStartUserAttestation.model_validate_json(
        _read_bytes(root, v4.USER_ATTESTATION_PATH)
    )
    state = v4.ManualDockerStartStateEvidence.model_validate_json(
        _read_bytes(root, v4.STATE_EVIDENCE_PATH)
    )
    _require(state.contract_id == contract.contract_id, "v4 state contract differs")
    _require(state.user_attestation_id == attestation.attestation_id, "v4 attestation differs")
    _require(
        qualification.contract_id == contract.contract_id,
        "v4 qualification contract differs",
    )
    return contract, qualification, attestation, state


def _v4_binding(root: Path) -> V4StateBinding:
    contract, qualification, attestation, state = _load_v4_chain(root)
    return V4StateBinding(
        state_commit=PREDECESSOR_STATE_COMMIT,
        contract_id=contract.contract_id,
        contract_content_hash=contract.content_hash,
        source_qualification_hash=qualification.content_hash,
        user_attestation_id=attestation.attestation_id,
        user_attestation_content_hash=attestation.content_hash,
        state_change_evidence_id=state.evidence_id,
        state_change_evidence_content_hash=state.content_hash,
    )


def _build_contract(root: Path) -> NoStartExecutableContract:
    v3_contract = v3.load_executable_no_call_preflight_contract(repository=root)
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "predecessor": _v4_binding(root).model_dump(mode="json"),
        "evaluator_v2_source_qualification_hash": (
            v3_contract.evaluator_v2_source_qualification_hash
        ),
        "evaluator_source_hash": v3_contract.evaluator_source_hash,
        "successor_suite_hash": v3_contract.successor_suite_hash,
        "runtime_tuple_hash": v3_contract.runtime_tuple_hash,
        "runtime_profile": NoStartRuntimeProfile(
            child_file_sha256=sha256_bytes(_read_bytes(root, CHILD_PATH)),
            d137_observer_file_sha256=sha256_bytes(_read_bytes(root, D137_PATH)),
            v3_runtime_file_sha256=sha256_bytes(_read_bytes(root, V3_RUNTIME_PATH)),
        ).model_dump(mode="json"),
        "transition_policy": v3_contract.transition_policy.model_dump(mode="json"),
        "current_manual_start_and_dotenv_reconfirmation_required": True,
        "source_authority": SourceAuthority().model_dump(mode="json"),
    }
    content_hash = _semantic_hash(body)
    return NoStartExecutableContract(
        **body,
        contract_id=_derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def load_contract(*, repository: str | Path | None = None) -> NoStartExecutableContract:
    root = _repo_root(repository)
    raw = _read_bytes(root, CONTRACT_PATH)
    try:
        contract = NoStartExecutableContract.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise NoStartExecutablePreflightError("v5 contract artifact is invalid") from exc
    _require(raw == _canonical_bytes(contract), "v5 contract bytes are not canonical")
    _require(contract == _build_contract(root), "v5 contract has drifted")
    return contract


def materialize_contract(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    selected = _logical_path(root, CONTRACT_PATH, must_exist=False)
    if selected.exists():
        contract = load_contract(repository=root)
        raw = _read_bytes(root, CONTRACT_PATH)
    else:
        contract = _build_contract(root)
        raw = _canonical_bytes(contract)
        _write_once(root, CONTRACT_PATH, raw)
    return {
        "status": "OFFLINE_NO_START_EXECUTABLE_CONTRACT_MATERIALIZED_LIVE_CLOSED",
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
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
        raise NoStartExecutablePreflightError("local Git source read failed") from exc
    _require(completed.returncode == 0, "local Git source read failed")
    return completed.stdout


def _source_commit(root: Path, selected: str) -> SourceCommitBinding:
    commit = _git(root, "rev-parse", f"{selected}^{{commit}}").decode("ascii").strip()
    tree = _git(root, "rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    row = _git(root, "rev-list", "--parents", "-n", "1", commit).decode("ascii").split()
    _require(row and row[0] == commit and len(row) == 2, "v5 source parent binding failed")
    lines = (
        _git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", row[1], commit)
        .decode("utf-8")
        .splitlines()
    )
    added = tuple(sorted(parts[1] for line in lines if (parts := line.split("\t"))[:1] == ["A"]))
    _require(len(lines) == len(added), "v5 source commit contains non-addition changes")
    return SourceCommitBinding(commit=commit, tree=tree, parents=(row[1],), added_paths=added)


def _committed_file(root: Path, commit: str, path: Path) -> tuple[CommittedFileBinding, bytes]:
    logical = path.as_posix()
    raw = _git(root, "show", f"{commit}:{logical}")
    oid = _git(root, "rev-parse", f"{commit}:{logical}").decode("ascii").strip()
    return (
        CommittedFileBinding(
            path=logical,
            blob_oid=oid,
            file_bytes=len(raw),
            file_sha256=sha256_bytes(raw),
        ),
        raw,
    )


def _build_qualification(
    root: Path, *, source_commit: str, recorded_at: datetime
) -> SourceQualification:
    contract = load_contract(repository=root)
    commit = _source_commit(root, source_commit)
    pairs = tuple(_committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(item[0] for item in pairs)
    by_path = {item.path: item for item in files}
    contract_index = SOURCE_FILES.index(CONTRACT_PATH)
    _require(
        pairs[contract_index][1] == _canonical_bytes(contract), "committed v5 contract differs"
    )
    body = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": QUALIFICATION_STATUS,
        "recorded_at": _utc(recorded_at, label="v5 qualification recorded_at"),
        "source_commit": commit.model_dump(mode="json"),
        "source_files": tuple(item.model_dump(mode="json") for item in files),
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "contract_file": by_path[CONTRACT_PATH.as_posix()].model_dump(mode="json"),
        "runtime_file": by_path[RUNTIME_PATH.as_posix()].model_dump(mode="json"),
        "child_file": by_path[CHILD_PATH.as_posix()].model_dump(mode="json"),
        "d137_observer_file": by_path[D137_PATH.as_posix()].model_dump(mode="json"),
        "predecessor_state_file": by_path[v4.STATE_EVIDENCE_PATH.as_posix()].model_dump(
            mode="json"
        ),
        "authority": QualificationAuthority().model_dump(mode="json"),
        "next_gate": NEXT_GATE,
    }
    return SourceQualification(**body, content_hash=_semantic_hash(body))


def qualify_source(
    *, source_commit: str = "HEAD", repository: str | Path | None = None
) -> dict[str, Any]:
    root = _repo_root(repository)
    selected = _logical_path(root, QUALIFICATION_PATH, must_exist=False)
    if selected.exists():
        return validate_source_qualification(repository=root)
    value = _build_qualification(root, source_commit=source_commit, recorded_at=datetime.now(UTC))
    _write_once(root, QUALIFICATION_PATH, _canonical_bytes(value))
    return validate_source_qualification(repository=root)


def validate_source_qualification(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    raw = _read_bytes(root, QUALIFICATION_PATH)
    try:
        value = SourceQualification.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise NoStartExecutablePreflightError("v5 source qualification is invalid") from exc
    _require(raw == _canonical_bytes(value), "v5 qualification bytes are not canonical")
    expected = _build_qualification(
        root,
        source_commit=value.source_commit.commit,
        recorded_at=value.recorded_at,
    )
    _require(value == expected, "v5 qualification has drifted")
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


def _load_qualification(root: Path) -> SourceQualification:
    validate_source_qualification(repository=root)
    return SourceQualification.model_validate_json(_read_bytes(root, QUALIFICATION_PATH))


def _load_v4_state(root: Path) -> v4.ManualDockerStartStateEvidence:
    v4.validate_manual_start_state(repository=root)
    return v4.ManualDockerStartStateEvidence.model_validate_json(
        _read_bytes(root, v4.STATE_EVIDENCE_PATH)
    )


def build_approval_receipt(
    contract: NoStartExecutableContract,
    qualification: SourceQualification,
    state: v4.ManualDockerStartStateEvidence,
    *,
    recorded_at: datetime,
) -> ApprovalReceipt:
    _require(qualification.contract_id == contract.contract_id, "approval qualification differs")
    _require(
        state.evidence_id == contract.predecessor.state_change_evidence_id, "approval state differs"
    )
    body = {
        "schema_version": "no-start-preflight-exact-approval-receipt-v5",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "source_qualification_content_hash": qualification.content_hash,
        "state_change_evidence_id": state.evidence_id,
        "state_change_evidence_content_hash": state.content_hash,
        "approved_scopes": APPROVED_SCOPES,
        "identity_assurance": IDENTITY_ASSURANCE,
        "current_manual_docker_start_state_reconfirmed": True,
        "current_dotenv_placement_reconfirmed": True,
        "attempt_limit": 1,
        "credential_value_in_approval": False,
        "docker_desktop_or_daemon_start_authorized": False,
        "image_pull_load_or_store_mutation_authorized": False,
        "container_operation_authorized": False,
        "network_or_transport_authorized": False,
        "provider_evaluator_agent_execution_authorized": False,
        "execution_hash_candidate_cost_or_paid_execution_authorized": False,
        "recorded_at": _utc(recorded_at, label="v5 approval recorded_at"),
    }
    content_hash = _semantic_hash(body)
    return ApprovalReceipt(
        **body,
        receipt_id=_derived_id("ncpapprovalreceipt", content_hash),
        content_hash=content_hash,
    )


def bind_approval(
    contract: NoStartExecutableContract,
    qualification: SourceQualification,
    state: v4.ManualDockerStartStateEvidence,
    receipt: ApprovalReceipt,
    *,
    recorded_at: datetime,
) -> ApprovalBinding:
    _require(receipt.contract_id == contract.contract_id, "approval receipt contract differs")
    _require(
        receipt.state_change_evidence_id == state.evidence_id, "approval receipt state differs"
    )
    _require(recorded_at >= receipt.recorded_at, "approval binding predates receipt")
    body = {
        "schema_version": "no-start-preflight-approval-binding-v5",
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "source_qualification_content_hash": qualification.content_hash,
        "state_change_evidence_id": state.evidence_id,
        "state_change_evidence_content_hash": state.content_hash,
        "receipt_id": receipt.receipt_id,
        "receipt_content_hash": receipt.content_hash,
        "approved_scopes": APPROVED_SCOPES,
        "attempt_limit": 1,
        "docker_desktop_or_daemon_start_authorized": False,
        "image_pull_load_or_store_mutation_authorized": False,
        "container_operation_authorized": False,
        "network_or_transport_authorized": False,
        "provider_evaluator_agent_execution_authorized": False,
        "execution_hash_candidate_cost_or_paid_execution_authorized": False,
        "recorded_at": _utc(recorded_at, label="v5 approval binding recorded_at"),
    }
    content_hash = _semantic_hash(body)
    return ApprovalBinding(
        **body,
        approval_id=_derived_id("ncpapproval", content_hash),
        content_hash=content_hash,
    )


def record_exact_approval(
    *,
    exact_contract_id: str,
    exact_source_qualification_hash: str,
    exact_state_change_evidence_id: str,
    reconfirm_current_manual_start: bool,
    reconfirm_current_dotenv_placement: bool,
    recorded_at: datetime,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    root = _repo_root(repository)
    for path in (APPROVAL_RECEIPT_PATH, APPROVAL_BINDING_PATH):
        _require(
            not _logical_path(root, path, must_exist=False).exists(), "v5 approval already exists"
        )
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    state = _load_v4_state(root)
    _require(exact_contract_id == contract.contract_id, "approval did not cite exact contract")
    _require(
        exact_source_qualification_hash == qualification.content_hash,
        "approval did not cite exact source qualification",
    )
    _require(
        exact_state_change_evidence_id == state.evidence_id,
        "approval did not cite exact state",
    )
    _require(
        reconfirm_current_manual_start is True,
        "approval did not reconfirm current manual start",
    )
    _require(
        reconfirm_current_dotenv_placement is True,
        "approval did not reconfirm current dotenv placement",
    )
    receipt = build_approval_receipt(contract, qualification, state, recorded_at=recorded_at)
    approval = bind_approval(
        contract,
        qualification,
        state,
        receipt,
        recorded_at=recorded_at,
    )
    _write_once(root, APPROVAL_RECEIPT_PATH, _canonical_bytes(receipt))
    _write_once(root, APPROVAL_BINDING_PATH, _canonical_bytes(approval))
    return validate_exact_approval(repository=root)


def validate_exact_approval(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    state = _load_v4_state(root)
    receipt_raw = _read_bytes(root, APPROVAL_RECEIPT_PATH)
    approval_raw = _read_bytes(root, APPROVAL_BINDING_PATH)
    try:
        receipt = ApprovalReceipt.model_validate_json(receipt_raw)
        approval = ApprovalBinding.model_validate_json(approval_raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise NoStartExecutablePreflightError("v5 approval artifact is invalid") from exc
    _require(receipt_raw == _canonical_bytes(receipt), "v5 receipt bytes not canonical")
    _require(approval_raw == _canonical_bytes(approval), "v5 approval bytes not canonical")
    expected = bind_approval(
        contract,
        qualification,
        state,
        receipt,
        recorded_at=approval.recorded_at,
    )
    _require(approval == expected, "v5 approval has drifted")
    return {
        "status": "NO_START_EXACT_APPROVAL_RECORDED_ATTEMPT_NOT_STARTED",
        "contract_id": contract.contract_id,
        "source_qualification_hash": qualification.content_hash,
        "state_change_evidence_id": state.evidence_id,
        "approval_id": approval.approval_id,
        "approval_content_hash": approval.content_hash,
        "attempt_limit": 1,
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "attempt_started": False,
        "paid_execution_authorized": False,
    }


def _ledger_snapshot(root: Path) -> str:
    rows = []
    for path in (ATTEMPT_PATH, ACTION_STARTED_PATH, TERMINAL_PATH):
        selected = _logical_path(root, path, must_exist=False)
        rows.append({"path": path.as_posix(), "exists": selected.exists()})
    _require(not any(row["exists"] for row in rows), "v5 attempt ledger is consumed")
    return sha256_json(rows)


def _empty_ledger_hash() -> str:
    return sha256_json(
        [
            {"path": path.as_posix(), "exists": False}
            for path in (ATTEMPT_PATH, ACTION_STARTED_PATH, TERMINAL_PATH)
        ]
    )


def _build_attempt(
    contract: NoStartExecutableContract,
    qualification: SourceQualification,
    state: v4.ManualDockerStartStateEvidence,
    approval: ApprovalBinding,
    *,
    ledger_snapshot_hash: str,
    created_at: datetime,
) -> AttemptIntent:
    _require(approval.contract_id == contract.contract_id, "attempt approval contract differs")
    _require(approval.state_change_evidence_id == state.evidence_id, "attempt state differs")
    _require(created_at >= approval.recorded_at, "attempt predates approval")
    body = {
        "schema_version": "no-start-preflight-attempt-intent-v5",
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "source_qualification_content_hash": qualification.content_hash,
        "state_change_evidence_id": state.evidence_id,
        "state_change_evidence_content_hash": state.content_hash,
        "approval_id": approval.approval_id,
        "approval_content_hash": approval.content_hash,
        "ledger_snapshot_hash": ledger_snapshot_hash,
        "created_at": _utc(created_at, label="v5 attempt created_at"),
        "attempt_number": 1,
        "one_use": True,
        "retry_or_resume_allowed": False,
    }
    content_hash = _semantic_hash(body)
    return AttemptIntent(
        **body,
        attempt_id=_derived_id("ncpattempt", content_hash),
        content_hash=content_hash,
    )


def _build_action(attempt: AttemptIntent, *, recorded_at: datetime) -> ActionStarted:
    _require(recorded_at >= attempt.created_at, "v5 action predates attempt")
    body = {
        "schema_version": "no-start-preflight-action-started-v5",
        "attempt_id": attempt.attempt_id,
        "attempt_content_hash": attempt.content_hash,
        "sequence": 1,
        "recorded_at": _utc(recorded_at, label="v5 action recorded_at"),
    }
    content_hash = _semantic_hash(body)
    return ActionStarted(
        **body,
        marker_id=_derived_id("ncpstarted", content_hash),
        content_hash=content_hash,
    )


def _sdk_reason(
    observation: v3.ExecutableSDKObservation,
) -> tuple[v3.TerminalOutcome, v3.TerminalReason]:
    if not observation.parent_pythonhome_absent or not observation.parent_pythonpath_absent:
        return v3.TerminalOutcome.BLOCKED, v3.TerminalReason.PYTHON_ENVIRONMENT_NOT_CLEAN
    _require(observation.child is not None, "clean SDK observation lacks child")
    if observation.child.dotenv.error_code in {"sdk_checker_error", "isolated_checker_error"}:
        return v3.TerminalOutcome.ERROR, v3.TerminalReason.CHECKER_ERROR
    if not observation.child.dotenv.exact_subject_nonempty:
        return v3.TerminalOutcome.BLOCKED, v3.TerminalReason.DOTENV_CREDENTIAL_MISSING
    return v3.TerminalOutcome.BLOCKED, v3.TerminalReason.SDK_NO_CALL_FAILED


def _build_terminal(
    attempt: AttemptIntent,
    action: ActionStarted,
    *,
    outcome: v3.TerminalOutcome,
    reason: v3.TerminalReason | None,
    docker_observation: dict[str, Any] | None,
    sdk_observation: v3.ExecutableSDKObservation | None,
    activity_accounting_complete: bool,
    recorded_at: datetime,
) -> TerminalTransition:
    docker_count: int | None = None
    dotenv_count: int | None = None
    child_count: int | None = None
    if activity_accounting_complete:
        docker_count = (
            0
            if docker_observation is None
            else docker_observation["activity"]["docker_cli_command_count"]
        )
        dotenv_count = 0
        child_count = 0
        if sdk_observation is not None:
            child_count = sdk_observation.child_start_count
            if sdk_observation.child is not None:
                dotenv_count = sdk_observation.child.activity.dotenv_file_read_count
    body = {
        "schema_version": "no-start-preflight-terminal-v5",
        "attempt_id": attempt.attempt_id,
        "action_started_id": action.marker_id,
        "previous_content_hash": action.content_hash,
        "sequence": 2,
        "outcome": outcome,
        "reason": reason,
        "docker_observation": docker_observation,
        "sdk_observation": (
            None if sdk_observation is None else sdk_observation.model_dump(mode="json")
        ),
        "activity_accounting_complete": activity_accounting_complete,
        "unknown_post_marker_activity_possible": not activity_accounting_complete,
        "docker_cli_command_count": docker_count,
        "dotenv_file_read_count": dotenv_count,
        "sdk_child_start_count": child_count,
        "docker_desktop_or_daemon_start_count": 0,
        "image_pull_load_or_store_mutation_count": 0,
        "container_operation_count": 0,
        "credential_value_return_hash_prefix_or_length_count": 0,
        "network_call_count": 0,
        "provider_evaluator_agent_call_count": 0,
        "recorded_at": _utc(recorded_at, label="v5 terminal recorded_at"),
    }
    content_hash = _semantic_hash(body)
    return TerminalTransition(
        **body,
        terminal_id=_derived_id("ncpterminal", content_hash),
        content_hash=content_hash,
    )


def validate_attempt_chain(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    state = _load_v4_state(root)
    approval_summary = validate_exact_approval(repository=root)
    approval = ApprovalBinding.model_validate_json(_read_bytes(root, APPROVAL_BINDING_PATH))
    attempt_raw = _read_bytes(root, ATTEMPT_PATH)
    action_raw = _read_bytes(root, ACTION_STARTED_PATH)
    terminal_raw = _read_bytes(root, TERMINAL_PATH)
    try:
        attempt = AttemptIntent.model_validate_json(attempt_raw)
        action = ActionStarted.model_validate_json(action_raw)
        terminal = TerminalTransition.model_validate_json(terminal_raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise NoStartExecutablePreflightError("v5 attempt chain is invalid") from exc
    for label, raw, value in (
        ("attempt", attempt_raw, attempt),
        ("action", action_raw, action),
        ("terminal", terminal_raw, terminal),
    ):
        _require(raw == _canonical_bytes(value), f"v5 {label} bytes not canonical")
    _require(attempt.contract_id == contract.contract_id, "v5 attempt contract differs")
    _require(
        attempt.source_qualification_content_hash == qualification.content_hash,
        "v5 attempt qualification differs",
    )
    _require(attempt.state_change_evidence_id == state.evidence_id, "v5 attempt state differs")
    _require(attempt.approval_id == approval.approval_id, "v5 attempt approval differs")
    _require(attempt.ledger_snapshot_hash == _empty_ledger_hash(), "v5 ledger differs")
    _require(action.attempt_id == attempt.attempt_id, "v5 action attempt differs")
    _require(action.recorded_at >= attempt.created_at, "v5 action predates attempt")
    _require(
        terminal.attempt_id == attempt.attempt_id
        and terminal.action_started_id == action.marker_id
        and terminal.previous_content_hash == action.content_hash,
        "v5 terminal chain differs",
    )
    _require(terminal.recorded_at >= action.recorded_at, "v5 terminal predates action")
    return {
        "status": "NO_START_EXECUTABLE_PREFLIGHT_TERMINAL_VALID",
        "contract_id": contract.contract_id,
        "state_change_evidence_id": state.evidence_id,
        "approval_id": approval_summary["approval_id"],
        "attempt_id": attempt.attempt_id,
        "action_started_id": action.marker_id,
        "terminal_id": terminal.terminal_id,
        "outcome": terminal.outcome.value,
        "reason": None if terminal.reason is None else terminal.reason.value,
        "activity_accounting_complete": terminal.activity_accounting_complete,
        "unknown_post_marker_activity_possible": terminal.unknown_post_marker_activity_possible,
        "retry_or_resume_allowed": False,
        "docker_start_pull_or_container_mutations": 0,
        "network_calls_made": 0,
        "provider_evaluator_agent_calls_made": 0,
        "paid_execution_authorized": False,
    }


def run_once(
    *,
    repository: str | Path | None = None,
    docker_observer: Callable[..., dict[str, Any]] = (
        v3.d137.run_d137_docker_no_call_preflight_observation
    ),
    sdk_observer: Callable[..., v3.ExecutableSDKObservation] = (
        v3.run_isolated_dotenv_sdk_observation
    ),
) -> dict[str, Any]:
    root = _repo_root(repository)
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    state = _load_v4_state(root)
    validate_exact_approval(repository=root)
    approval = ApprovalBinding.model_validate_json(_read_bytes(root, APPROVAL_BINDING_PATH))
    attempt = _build_attempt(
        contract,
        qualification,
        state,
        approval,
        ledger_snapshot_hash=_ledger_snapshot(root),
        created_at=datetime.now(UTC),
    )
    _write_once(root, ATTEMPT_PATH, _canonical_bytes(attempt))
    action = _build_action(attempt, recorded_at=datetime.now(UTC))
    _write_once(root, ACTION_STARTED_PATH, _canonical_bytes(action))

    docker: dict[str, Any] | None = None
    sdk: v3.ExecutableSDKObservation | None = None
    try:
        docker = docker_observer(repository=root)
        v3.d137.validate_d137_docker_no_call_preflight_observation(docker)
        if not docker["passed"]:
            outcome, reason = (
                v3.TerminalOutcome.BLOCKED,
                v3.TerminalReason.DOCKER_NOT_READY,
            )
        else:
            sdk = sdk_observer(contract, repository=root)
            if sdk.passed:
                outcome, reason = v3.TerminalOutcome.READY, None
            else:
                outcome, reason = _sdk_reason(sdk)
    except Exception:
        docker = None
        sdk = None
        outcome, reason = v3.TerminalOutcome.ERROR, v3.TerminalReason.CHECKER_ERROR
    terminal = _build_terminal(
        attempt,
        action,
        outcome=outcome,
        reason=reason,
        docker_observation=docker,
        sdk_observation=sdk,
        activity_accounting_complete=(outcome != v3.TerminalOutcome.ERROR),
        recorded_at=datetime.now(UTC),
    )
    raw = _canonical_bytes(terminal)
    _require(b"sk-" not in raw.lower(), "v5 terminal contains credential-like material")
    _write_once(root, TERMINAL_PATH, raw)
    return validate_attempt_chain(repository=root)
