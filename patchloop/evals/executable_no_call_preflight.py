"""Executable, approval-gated successor for the receipt-free no-call preflight.

Import, contract materialization, qualification, and state binding are offline.
Only :func:`run_executable_no_call_preflight_once` crosses Docker/SDK/dotenv
observation boundaries, and it refuses to start without the exact append-only
approval artifacts and a durable ACTION_STARTED marker.
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
from patchloop.evals import user_attested_no_call_preflight as v2
from patchloop.runtime import repository_root
from patchloop.util import safe_relative_path, sha256_bytes, sha256_json

CONTRACT_SCHEMA_VERSION = "versioned-no-call-preflight-contract-v3"
CONTRACT_VERSION = "ac-evaluator-v2-no-call-preflight-v3"
CONTRACT_PATH = Path("experiments/evaluator-v2-no-call-preflight-v3.contract.json")
PREDECESSOR_STATE_COMMIT = "00a78b88a5ecee70df88cc288d32fbfc801999d0"

CHILD_PATH = Path("scripts/run_dotenv_sdk_no_call_child.py")
RUNTIME_PATH = Path("patchloop/evals/executable_no_call_preflight.py")
BUILD_SCRIPT_PATH = Path("scripts/build_executable_no_call_preflight.py")
TEST_PATH = Path("tests/test_executable_no_call_preflight.py")

QUALIFICATION_SCHEMA_VERSION = "executable-no-call-preflight-source-qualification-v3"
QUALIFICATION_ID = "ac-evaluator-v2-executable-no-call-preflight-source-20260812-r1"
QUALIFICATION_STATUS = "OFFLINE_EXECUTABLE_PREFLIGHT_SOURCE_QUALIFIED_EXACT_APPROVAL_REQUIRED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-no-call-preflight-v3-source-qualification.json"
)
STATE_EVIDENCE_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-no-call-preflight-v3-state-change-evidence.json"
)
APPROVAL_RECEIPT_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-no-call-preflight-v3-exact-approval-receipt.json"
)
APPROVAL_BINDING_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-no-call-preflight-v3-approval-binding.json"
)
ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-no-call-preflight-v3-attempt-intent.json"
)
ACTION_STARTED_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-no-call-preflight-v3-action-started.json"
)
TERMINAL_PATH = Path("reports/live-pilot/artifacts/evaluator-v2-no-call-preflight-v3-terminal.json")

SOURCE_ADDED_PATHS = tuple(
    sorted(
        (
            CONTRACT_PATH.as_posix(),
            RUNTIME_PATH.as_posix(),
            CHILD_PATH.as_posix(),
            BUILD_SCRIPT_PATH.as_posix(),
            TEST_PATH.as_posix(),
        )
    )
)
SOURCE_FILES = tuple(
    sorted(
        (
            Path("uv.lock"),
            Path("patchloop/agent/model.py"),
            Path("patchloop/evals/d137_no_call_preflight.py"),
            v2.CONTRACT_PATH,
            Path("patchloop/evals/user_attested_no_call_preflight.py"),
            v2.QUALIFICATION_PATH,
            v2.USER_ATTESTATION_PATH,
            v2.STATE_EVIDENCE_PATH,
            CONTRACT_PATH,
            RUNTIME_PATH,
            CHILD_PATH,
            BUILD_SCRIPT_PATH,
            TEST_PATH,
        ),
        key=lambda item: item.as_posix(),
    )
)

APPROVED_SCOPES = (
    "docker-read-only-two-snapshot-eight-command-observation",
    "isolated-dotenv-exact-openai-api-key-membership",
    "isolated-sdk-import-fixed-placeholder-reject-dispatch",
)
IDENTITY_ASSURANCE = v2.IDENTITY_ASSURANCE
STATE_CHANGE_SUBJECTS = v2.STATE_CHANGE_SUBJECTS
CHILD_SCHEMA_VERSION = "isolated-dotenv-sdk-no-call-observation-v1"
CHILD_TIMEOUT_SECONDS = 60
CHILD_OUTPUT_LIMIT = 262_144


class ExecutableNoCallPreflightError(ContractError):
    """Raised when the executable successor fails closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ExecutableNoCallPreflightError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = repository_root() if repository is None else Path(repository)
    return selected.resolve(strict=True)


def _logical_path(root: Path, relative: Path, *, must_exist: bool) -> Path:
    safe = safe_relative_path(relative.as_posix(), field_name="executable preflight path")
    selected = root.joinpath(*Path(safe).parts)
    resolved = selected.resolve(strict=must_exist)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ExecutableNoCallPreflightError(
            "executable preflight path escaped repository"
        ) from exc
    return resolved


def _read_bytes(root: Path, relative: Path) -> bytes:
    selected = _logical_path(root, relative, must_exist=True)
    _require(not selected.is_symlink(), f"preflight path is link-like: {relative.as_posix()}")
    before = selected.stat()
    raw = selected.read_bytes()
    after = selected.stat()
    _require(
        (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
        f"preflight path changed while reading: {relative.as_posix()}",
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
        raise ExecutableNoCallPreflightError(
            f"append-only artifact already exists: {relative.as_posix()}"
        ) from exc
    except OSError as exc:
        raise ExecutableNoCallPreflightError(
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
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def _semantic_hash(body: dict[str, Any]) -> str:
    return sha256_json(_json_ready(body))


class ExecutableRuntimeProfile(FrozenStrictModel):
    schema_version: Literal["executable-no-call-runtime-profile-v1"] = (
        "executable-no-call-runtime-profile-v1"
    )
    child_path: Literal["scripts/run_dotenv_sdk_no_call_child.py"] = CHILD_PATH.as_posix()
    child_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    d137_observer_path: Literal["patchloop/evals/d137_no_call_preflight.py"] = (
        "patchloop/evals/d137_no_call_preflight.py"
    )
    d137_observer_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    exact_subject_names: tuple[str, ...] = STATE_CHANGE_SUBJECTS
    dotenv_membership_child_only: Literal[True] = True
    dotenv_entire_file_bytes_confined_to_isolated_child: Literal[True] = True
    credential_assignment_parse_limit: Literal[2] = 2
    credential_value_confined_to_isolated_child: Literal[True] = True
    credential_value_return_hash_prefix_or_length_limit: Literal[0] = 0
    sdk_uses_fixed_nonsecret_placeholder: Literal[True] = True
    sdk_transport_kind: Literal["httpx.MockTransport-reject-dispatch"] = (
        "httpx.MockTransport-reject-dispatch"
    )
    child_environment_inherits_parent: Literal[False] = False
    child_timeout_seconds: Literal[60] = CHILD_TIMEOUT_SECONDS
    child_output_limit: Literal[262144] = CHILD_OUTPUT_LIMIT
    docker_observer: Literal["d137-read-only-two-snapshot"] = "d137-read-only-two-snapshot"
    docker_expected_command_count: Literal[8] = 8
    network_call_limit: Literal[0] = 0
    provider_evaluator_agent_call_limit: Literal[0] = 0
    runtime_implemented: Literal[True] = True

    @model_validator(mode="after")
    def validate_profile(self) -> ExecutableRuntimeProfile:
        if self.exact_subject_names != STATE_CHANGE_SUBJECTS:
            raise ValueError("runtime subjects drifted")
        return self


class ExecutableSourceAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    commit_source_qualification_authorized: Literal[True] = True
    predecessor_attestation_rebinding_supported: Literal[True] = True
    state_rebinding_is_presence_proof: Literal[False] = False
    external_preflight_attempt_authorized: Literal[False] = False
    exact_approval_required: Literal[True] = True
    docker_sdk_or_dotenv_observation_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    execution_hash_candidate_cost_or_paid_execution_authorized: Literal[False] = False
    automatic_retry_replacement_or_resume_authorized: Literal[False] = False


class ExecutableNoCallPreflightContract(FrozenStrictModel):
    schema_version: Literal["versioned-no-call-preflight-contract-v3"] = CONTRACT_SCHEMA_VERSION
    contract_version: Literal["ac-evaluator-v2-no-call-preflight-v3"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor_contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor_contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_user_attestation_id: str = Field(pattern=r"^ncpattestation_[0-9a-f]{64}$")
    predecessor_user_attestation_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_state_change_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    predecessor_state_change_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_v2_source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    successor_suite_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_tuple_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_profile: ExecutableRuntimeProfile
    transition_policy: v2.v1.PreflightTransitionPolicy
    source_authority: ExecutableSourceAuthority
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> ExecutableNoCallPreflightContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected_hash = sha256_json(body)
        if self.content_hash != expected_hash:
            raise ValueError("executable contract content hash mismatch")
        if self.contract_id != _derived_id("ncpcontract", expected_hash):
            raise ValueError("executable contract id mismatch")
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
            raise ValueError("executable source predecessor drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("executable source additions drifted")
        return self


class ExecutableQualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    executable_source_qualified: Literal[True] = True
    state_change_evidence_created: Literal[False] = False
    approval_created_or_inferred: Literal[False] = False
    attempt_or_transition_created: Literal[False] = False
    credential_dotenv_environment_observation_count: Literal[0] = 0
    credential_value_observation_or_mutation_count: Literal[0] = 0
    docker_or_sdk_observation_count: Literal[0] = 0
    network_provider_evaluator_agent_call_count: Literal[0] = 0
    execution_hash_candidate_or_cost_created: Literal[False] = False


class ExecutableSourceQualification(FrozenStrictModel):
    schema_version: Literal["executable-no-call-preflight-source-qualification-v3"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal["ac-evaluator-v2-executable-no-call-preflight-source-20260812-r1"] = (
        QUALIFICATION_ID
    )
    status: Literal["OFFLINE_EXECUTABLE_PREFLIGHT_SOURCE_QUALIFIED_EXACT_APPROVAL_REQUIRED"] = (
        QUALIFICATION_STATUS
    )
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[CommittedFileBinding, ...]
    contract_version: Literal["ac-evaluator-v2-no-call-preflight-v3"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    contract_file: CommittedFileBinding
    runtime_file: CommittedFileBinding
    child_file: CommittedFileBinding
    authority: ExecutableQualificationAuthority
    next_gate: Literal["fresh-state-binding-then-exact-user-approval"] = (
        "fresh-state-binding-then-exact-user-approval"
    )
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("qualification recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> ExecutableSourceQualification:
        if tuple(item.path for item in self.source_files) != tuple(
            item.as_posix() for item in SOURCE_FILES
        ):
            raise ValueError("qualification source inventory drifted")
        by_path = {item.path: item for item in self.source_files}
        if self.contract_file != by_path.get(CONTRACT_PATH.as_posix()):
            raise ValueError("qualification contract projection differs")
        if self.runtime_file != by_path.get(RUNTIME_PATH.as_posix()):
            raise ValueError("qualification runtime projection differs")
        if self.child_file != by_path.get(CHILD_PATH.as_posix()):
            raise ValueError("qualification child projection differs")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != sha256_json(body):
            raise ValueError("qualification content hash mismatch")
        return self


class ExecutableStateChangeEvidence(FrozenStrictModel):
    schema_version: Literal["preflight-state-change-evidence-v3"] = (
        "preflight-state-change-evidence-v3"
    )
    evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    contract_version: Literal["ac-evaluator-v2-no-call-preflight-v3"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_id: Literal[
        "ac-evaluator-v2-executable-no-call-preflight-source-20260812-r1"
    ] = QUALIFICATION_ID
    source_qualification_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_kind: Literal["credential-location-user-attestation-rebound-v3"] = (
        "credential-location-user-attestation-rebound-v3"
    )
    predecessor_user_attestation_id: str = Field(pattern=r"^ncpattestation_[0-9a-f]{64}$")
    predecessor_user_attestation_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_state_change_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    predecessor_state_change_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    subject_names_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    location_surface: Literal["repository-root-dotenv"] = v2.DOTENV_SURFACE
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    independent_verification_completed: Literal[False] = False
    attestation_proves_credential_presence: Literal[False] = False
    exact_approval_must_reconfirm_current_state: Literal[True] = True
    dotenv_read_or_stat_performed: Literal[False] = False
    raw_credential_value_observed: Literal[False] = False
    raw_credential_value_persisted: Literal[False] = False
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("state evidence recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> ExecutableStateChangeEvidence:
        if self.subject_names_hash != sha256_json(list(STATE_CHANGE_SUBJECTS)):
            raise ValueError("state evidence subjects drifted")
        body = self.model_dump(mode="json", exclude={"evidence_id", "content_hash"})
        expected_hash = sha256_json(body)
        if self.content_hash != expected_hash:
            raise ValueError("state evidence content hash mismatch")
        if self.evidence_id != _derived_id("ncpstate", expected_hash):
            raise ValueError("state evidence id mismatch")
        return self


class ExecutableApprovalReceipt(FrozenStrictModel):
    schema_version: Literal["preflight-user-exact-approval-receipt-v3"] = (
        "preflight-user-exact-approval-receipt-v3"
    )
    receipt_id: str = Field(pattern=r"^ncpapprovalreceipt_[0-9a-f]{64}$")
    contract_version: Literal["ac-evaluator-v2-no-call-preflight-v3"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_change_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_change_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    current_dotenv_placement_reconfirmed: Literal[True] = True
    attempt_limit: Literal[1] = 1
    credential_value_in_approval: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    network_or_transport_authorized: Literal[False] = False
    execution_hash_candidate_cost_or_paid_execution_authorized: Literal[False] = False
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("approval receipt recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> ExecutableApprovalReceipt:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("approval scopes drifted")
        body = self.model_dump(mode="json", exclude={"receipt_id", "content_hash"})
        expected_hash = sha256_json(body)
        if self.content_hash != expected_hash:
            raise ValueError("approval receipt content hash mismatch")
        if self.receipt_id != _derived_id("ncpapprovalreceipt", expected_hash):
            raise ValueError("approval receipt id mismatch")
        return self


class ExecutableApprovalBinding(FrozenStrictModel):
    schema_version: Literal["preflight-approval-binding-v3"] = "preflight-approval-binding-v3"
    approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    contract_version: Literal["ac-evaluator-v2-no-call-preflight-v3"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_change_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_change_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    user_approval_receipt_id: str = Field(pattern=r"^ncpapprovalreceipt_[0-9a-f]{64}$")
    user_approval_receipt_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    attempt_limit: Literal[1] = 1
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    network_or_transport_authorized: Literal[False] = False
    execution_hash_candidate_cost_or_paid_execution_authorized: Literal[False] = False
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("approval binding recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> ExecutableApprovalBinding:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("approval binding scopes drifted")
        body = self.model_dump(mode="json", exclude={"approval_id", "content_hash"})
        expected_hash = sha256_json(body)
        if self.content_hash != expected_hash:
            raise ValueError("approval binding content hash mismatch")
        if self.approval_id != _derived_id("ncpapproval", expected_hash):
            raise ValueError("approval binding id mismatch")
        return self


class DotenvObservation(FrozenStrictModel):
    file_present: bool
    exact_subject_declared: bool
    exact_subject_nonempty: bool
    duplicate_subject: bool
    error_code: str | None = Field(default=None, pattern=r"^[a-z0-9_-]{1,64}$")
    raw_value_returned: Literal[False] = False
    value_hash_prefix_or_length_returned: Literal[False] = False


class ChildActivity(FrozenStrictModel):
    dotenv_file_read_count: int = Field(ge=0, le=1)
    dotenv_subject_membership_check_count: int = Field(ge=0, le=1)
    credential_assignment_parse_count: int = Field(ge=0, le=2)
    credential_value_return_count: Literal[0] = 0
    credential_value_hash_prefix_or_length_count: Literal[0] = 0
    network_call_count: Literal[0] = 0
    provider_evaluator_agent_call_count: Literal[0] = 0


class IsolatedDotenvSDKObservation(FrozenStrictModel):
    schema_version: Literal["isolated-dotenv-sdk-no-call-observation-v1"] = CHILD_SCHEMA_VERSION
    dotenv: DotenvObservation
    sdk_observation: dict[str, Any] | None = None
    activity: ChildActivity

    @model_validator(mode="after")
    def validate_semantics(self) -> IsolatedDotenvSDKObservation:
        ready_for_sdk = self.dotenv.exact_subject_nonempty and self.dotenv.error_code is None
        if ready_for_sdk != (self.sdk_observation is not None):
            raise ValueError("isolated SDK execution does not match dotenv membership")
        if self.sdk_observation is not None:
            try:
                d137.validate_d137_sdk_no_call_preflight_observation(self.sdk_observation)
            except ContractError as exc:
                raise ValueError("isolated SDK observation is invalid") from exc
            if self.sdk_observation["activity"]["network_call_count"] != 0:
                raise ValueError("isolated SDK observation crossed network boundary")
        return self


class ExecutableSDKObservation(FrozenStrictModel):
    schema_version: Literal["executable-dotenv-sdk-observation-v1"] = (
        "executable-dotenv-sdk-observation-v1"
    )
    parent_pythonhome_absent: bool
    parent_pythonpath_absent: bool
    child_start_count: int = Field(ge=0, le=1)
    child: IsolatedDotenvSDKObservation | None = None
    passed: bool

    @model_validator(mode="after")
    def validate_semantics(self) -> ExecutableSDKObservation:
        parent_clean = self.parent_pythonhome_absent and self.parent_pythonpath_absent
        if not parent_clean:
            if self.child_start_count != 0 or self.child is not None or self.passed:
                raise ValueError("dirty parent Python environment did not suppress child")
            return self
        if self.child_start_count != 1 or self.child is None:
            raise ValueError("clean parent environment lacks isolated child")
        expected = bool(
            self.child.dotenv.exact_subject_nonempty
            and self.child.dotenv.error_code is None
            and self.child.sdk_observation is not None
            and self.child.sdk_observation["passed"] is True
        )
        if self.passed != expected:
            raise ValueError("executable SDK pass state differs")
        return self


class AttemptIntent(FrozenStrictModel):
    schema_version: Literal["preflight-attempt-intent-v3"] = "preflight-attempt-intent-v3"
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    contract_version: Literal["ac-evaluator-v2-no-call-preflight-v3"] = CONTRACT_VERSION
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
    state: Literal["intent_recorded"] = "intent_recorded"
    one_use: Literal[True] = True
    retry_or_resume_allowed: Literal[False] = False
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("attempt created_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> AttemptIntent:
        body = self.model_dump(mode="json", exclude={"attempt_id", "content_hash"})
        expected_hash = sha256_json(body)
        if self.content_hash != expected_hash:
            raise ValueError("attempt content hash mismatch")
        if self.attempt_id != _derived_id("ncpattempt", expected_hash):
            raise ValueError("attempt id mismatch")
        return self


class ActionStarted(FrozenStrictModel):
    schema_version: Literal["preflight-action-started-v3"] = "preflight-action-started-v3"
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
            raise ValueError("action marker recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> ActionStarted:
        body = self.model_dump(mode="json", exclude={"marker_id", "content_hash"})
        expected_hash = sha256_json(body)
        if self.content_hash != expected_hash:
            raise ValueError("action marker content hash mismatch")
        if self.marker_id != _derived_id("ncpstarted", expected_hash):
            raise ValueError("action marker id mismatch")
        return self


class TerminalOutcome(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"
    ERROR = "error"


class TerminalReason(StrEnum):
    DOCKER_NOT_READY = "docker_not_ready"
    PYTHON_ENVIRONMENT_NOT_CLEAN = "python_environment_not_clean"
    DOTENV_CREDENTIAL_MISSING = "dotenv_credential_missing"
    SDK_NO_CALL_FAILED = "sdk_no_call_failed"
    CHECKER_ERROR = "checker_error"


class TerminalTransition(FrozenStrictModel):
    schema_version: Literal["preflight-terminal-v3"] = "preflight-terminal-v3"
    terminal_id: str = Field(pattern=r"^ncpterminal_[0-9a-f]{64}$")
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    action_started_id: str = Field(pattern=r"^ncpstarted_[0-9a-f]{64}$")
    previous_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sequence: Literal[2] = 2
    outcome: TerminalOutcome
    reason: TerminalReason | None = None
    docker_observation: dict[str, Any] | None = None
    sdk_observation: ExecutableSDKObservation | None = None
    activity_accounting_complete: bool
    unknown_post_marker_activity_possible: bool
    docker_cli_command_count: int | None = Field(default=None, ge=0, le=8)
    dotenv_file_read_count: int | None = Field(default=None, ge=0, le=1)
    sdk_child_start_count: int | None = Field(default=None, ge=0, le=1)
    credential_value_return_hash_prefix_or_length_count: Literal[0] = 0
    network_call_count: Literal[0] = 0
    provider_evaluator_agent_call_count: Literal[0] = 0
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("terminal recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_terminal(self) -> TerminalTransition:
        if self.docker_observation is not None:
            try:
                d137.validate_d137_docker_no_call_preflight_observation(self.docker_observation)
            except ContractError as exc:
                raise ValueError("terminal Docker observation is invalid") from exc
        if self.outcome == TerminalOutcome.READY:
            if (
                self.reason is not None
                or self.docker_observation is None
                or self.sdk_observation is None
            ):
                raise ValueError("READY terminal is incomplete")
            if not self.docker_observation["passed"] or not self.sdk_observation.passed:
                raise ValueError("READY terminal lacks passing observations")
            if self.docker_cli_command_count != 8:
                raise ValueError("READY terminal Docker count differs")
            if not self.activity_accounting_complete or self.unknown_post_marker_activity_possible:
                raise ValueError("READY terminal activity accounting is incomplete")
        elif self.reason is None:
            raise ValueError("non-READY terminal lacks reason")
        if self.outcome != TerminalOutcome.ERROR and (
            not self.activity_accounting_complete or self.unknown_post_marker_activity_possible
        ):
            raise ValueError("non-ERROR terminal activity accounting is incomplete")
        if (
            self.outcome == TerminalOutcome.ERROR
            and not self.activity_accounting_complete
            and not self.unknown_post_marker_activity_possible
        ):
            raise ValueError("incomplete ERROR terminal hides unknown activity")
        body = self.model_dump(mode="json", exclude={"terminal_id", "content_hash"})
        expected_hash = sha256_json(body)
        if self.content_hash != expected_hash:
            raise ValueError("terminal content hash mismatch")
        if self.terminal_id != _derived_id("ncpterminal", expected_hash):
            raise ValueError("terminal id mismatch")
        return self


def _load_v2_chain(
    root: Path,
) -> tuple[
    v2.UserAttestedNoCallPreflightContract,
    v2.UserAttestedSourceQualification,
    v2.UserCredentialLocationAttestation,
    v2.UserAttestedStateChangeEvidence,
]:
    v2.validate_user_attested_source_qualification(repository=root)
    v2.validate_user_attested_state_change(repository=root)
    contract = v2.load_user_attested_no_call_preflight_contract(repository=root)
    qualification = v2.UserAttestedSourceQualification.model_validate_json(
        _read_bytes(root, v2.QUALIFICATION_PATH)
    )
    attestation = v2.UserCredentialLocationAttestation.model_validate_json(
        _read_bytes(root, v2.USER_ATTESTATION_PATH)
    )
    state = v2.UserAttestedStateChangeEvidence.model_validate_json(
        _read_bytes(root, v2.STATE_EVIDENCE_PATH)
    )
    _require(state.contract_id == contract.contract_id, "v2 state contract differs")
    _require(state.user_attestation_id == attestation.attestation_id, "v2 attestation differs")
    _require(
        qualification.contract_id == contract.contract_id,
        "v2 qualification contract differs",
    )
    return contract, qualification, attestation, state


def _build_contract(root: Path) -> ExecutableNoCallPreflightContract:
    predecessor, qualification, attestation, state = _load_v2_chain(root)
    child_raw = _read_bytes(root, CHILD_PATH)
    d137_raw = _read_bytes(root, Path("patchloop/evals/d137_no_call_preflight.py"))
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "predecessor_contract_id": predecessor.contract_id,
        "predecessor_contract_content_hash": predecessor.content_hash,
        "predecessor_source_qualification_hash": qualification.content_hash,
        "predecessor_user_attestation_id": attestation.attestation_id,
        "predecessor_user_attestation_content_hash": attestation.content_hash,
        "predecessor_state_change_evidence_id": state.evidence_id,
        "predecessor_state_change_evidence_content_hash": state.content_hash,
        "evaluator_v2_source_qualification_hash": (
            predecessor.evaluator_v2_source_qualification_hash
        ),
        "evaluator_source_hash": predecessor.evaluator_source_hash,
        "successor_suite_hash": predecessor.successor_suite_hash,
        "runtime_tuple_hash": predecessor.runtime_tuple_hash,
        "runtime_profile": ExecutableRuntimeProfile(
            child_file_sha256=sha256_bytes(child_raw),
            d137_observer_file_sha256=sha256_bytes(d137_raw),
        ).model_dump(mode="json"),
        "transition_policy": predecessor.transition_policy.model_dump(mode="json"),
        "source_authority": ExecutableSourceAuthority().model_dump(mode="json"),
    }
    content_hash = _semantic_hash(body)
    return ExecutableNoCallPreflightContract(
        **body,
        contract_id=_derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def load_executable_no_call_preflight_contract(
    *, repository: str | Path | None = None
) -> ExecutableNoCallPreflightContract:
    root = _repo_root(repository)
    raw = _read_bytes(root, CONTRACT_PATH)
    try:
        contract = ExecutableNoCallPreflightContract.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise ExecutableNoCallPreflightError("executable contract is invalid") from exc
    _require(raw == _canonical_bytes(contract), "executable contract bytes are not canonical")
    _require(contract == _build_contract(root), "executable contract has drifted")
    return contract


def materialize_executable_no_call_preflight_contract(
    *, repository: str | Path | None = None
) -> dict[str, Any]:
    root = _repo_root(repository)
    selected = _logical_path(root, CONTRACT_PATH, must_exist=False)
    if selected.exists():
        contract = load_executable_no_call_preflight_contract(repository=root)
        raw = _read_bytes(root, CONTRACT_PATH)
    else:
        contract = _build_contract(root)
        raw = _canonical_bytes(contract)
        _write_once(root, CONTRACT_PATH, raw)
    return {
        "status": "OFFLINE_EXECUTABLE_CONTRACT_MATERIALIZED_EXACT_APPROVAL_REQUIRED",
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "runtime_implemented": True,
        "external_observations_made": 0,
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
        raise ExecutableNoCallPreflightError("local Git source read failed") from exc
    _require(completed.returncode == 0, "local Git source read failed")
    return completed.stdout


def _source_commit(root: Path, selected: str) -> SourceCommitBinding:
    commit = _git(root, "rev-parse", f"{selected}^{{commit}}").decode("ascii").strip()
    tree = _git(root, "rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    row = _git(root, "rev-list", "--parents", "-n", "1", commit).decode("ascii").strip().split()
    _require(row and row[0] == commit, "source parent binding failed")
    diff = _git(
        root,
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "-r",
        row[1],
        commit,
    ).decode("utf-8")
    added = tuple(
        sorted(
            parts[1]
            for line in diff.splitlines()
            if (parts := line.split("\t")) and parts[0] == "A" and len(parts) == 2
        )
    )
    _require(len(diff.splitlines()) == len(added), "source contains non-addition changes")
    return SourceCommitBinding(
        commit=commit,
        tree=tree,
        parents=tuple(row[1:]),
        added_paths=added,
    )


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


def _build_source_qualification(
    root: Path,
    *,
    source_commit: str,
    recorded_at: datetime,
) -> ExecutableSourceQualification:
    contract = load_executable_no_call_preflight_contract(repository=root)
    commit = _source_commit(root, source_commit)
    pairs = tuple(_committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(item[0] for item in pairs)
    indexes = {path: SOURCE_FILES.index(path) for path in (CONTRACT_PATH, RUNTIME_PATH, CHILD_PATH)}
    _require(
        pairs[indexes[CONTRACT_PATH]][1] == _canonical_bytes(contract),
        "committed contract differs",
    )
    _require(
        files[indexes[CHILD_PATH]].file_sha256 == contract.runtime_profile.child_file_sha256,
        "committed child differs from contract",
    )
    d137_index = SOURCE_FILES.index(Path("patchloop/evals/d137_no_call_preflight.py"))
    _require(
        files[d137_index].file_sha256 == contract.runtime_profile.d137_observer_file_sha256,
        "committed D-137 observer differs from contract",
    )
    body = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": QUALIFICATION_STATUS,
        "recorded_at": _utc(recorded_at, label="qualification recorded_at"),
        "source_commit": commit.model_dump(mode="json"),
        "source_files": tuple(item.model_dump(mode="json") for item in files),
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "contract_file": files[indexes[CONTRACT_PATH]].model_dump(mode="json"),
        "runtime_file": files[indexes[RUNTIME_PATH]].model_dump(mode="json"),
        "child_file": files[indexes[CHILD_PATH]].model_dump(mode="json"),
        "authority": ExecutableQualificationAuthority().model_dump(mode="json"),
        "next_gate": "fresh-state-binding-then-exact-user-approval",
    }
    return ExecutableSourceQualification(**body, content_hash=_semantic_hash(body))


def validate_executable_source_qualification(
    *, repository: str | Path | None = None
) -> dict[str, Any]:
    root = _repo_root(repository)
    raw = _read_bytes(root, QUALIFICATION_PATH)
    try:
        value = ExecutableSourceQualification.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise ExecutableNoCallPreflightError("source qualification is invalid") from exc
    _require(raw == _canonical_bytes(value), "source qualification bytes are not canonical")
    expected = _build_source_qualification(
        root,
        source_commit=value.source_commit.commit,
        recorded_at=value.recorded_at,
    )
    _require(value == expected, "source qualification has drifted")
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
        "execution_authorized": False,
    }


def run_executable_source_qualification(
    *,
    source_commit: str = "HEAD",
    repository: str | Path | None = None,
) -> dict[str, Any]:
    root = _repo_root(repository)
    selected = _logical_path(root, QUALIFICATION_PATH, must_exist=False)
    if selected.exists():
        return validate_executable_source_qualification(repository=root)
    value = _build_source_qualification(
        root,
        source_commit=source_commit,
        recorded_at=datetime.now(UTC),
    )
    _write_once(root, QUALIFICATION_PATH, _canonical_bytes(value))
    return validate_executable_source_qualification(repository=root)


def _load_qualification(root: Path) -> ExecutableSourceQualification:
    validate_executable_source_qualification(repository=root)
    return ExecutableSourceQualification.model_validate_json(_read_bytes(root, QUALIFICATION_PATH))


def bind_executable_state_change_evidence(
    contract: ExecutableNoCallPreflightContract,
    qualification: ExecutableSourceQualification,
    predecessor_attestation: v2.UserCredentialLocationAttestation,
    predecessor_state: v2.UserAttestedStateChangeEvidence,
    *,
    recorded_at: datetime,
) -> ExecutableStateChangeEvidence:
    _require(qualification.contract_id == contract.contract_id, "qualification contract differs")
    _require(
        predecessor_attestation.attestation_id == contract.predecessor_user_attestation_id,
        "predecessor attestation differs",
    )
    _require(
        predecessor_state.evidence_id == contract.predecessor_state_change_evidence_id,
        "predecessor state differs",
    )
    _require(recorded_at >= predecessor_state.recorded_at, "state rebind predates predecessor")
    body = {
        "schema_version": "preflight-state-change-evidence-v3",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "source_qualification_id": qualification.qualification_id,
        "source_qualification_content_hash": qualification.content_hash,
        "evidence_kind": "credential-location-user-attestation-rebound-v3",
        "predecessor_user_attestation_id": predecessor_attestation.attestation_id,
        "predecessor_user_attestation_content_hash": predecessor_attestation.content_hash,
        "predecessor_state_change_evidence_id": predecessor_state.evidence_id,
        "predecessor_state_change_evidence_content_hash": predecessor_state.content_hash,
        "subject_names_hash": sha256_json(list(STATE_CHANGE_SUBJECTS)),
        "location_surface": v2.DOTENV_SURFACE,
        "identity_assurance": IDENTITY_ASSURANCE,
        "independent_verification_completed": False,
        "attestation_proves_credential_presence": False,
        "exact_approval_must_reconfirm_current_state": True,
        "dotenv_read_or_stat_performed": False,
        "raw_credential_value_observed": False,
        "raw_credential_value_persisted": False,
        "recorded_at": _utc(recorded_at, label="state rebind recorded_at"),
    }
    content_hash = _semantic_hash(body)
    return ExecutableStateChangeEvidence(
        **body,
        evidence_id=_derived_id("ncpstate", content_hash),
        content_hash=content_hash,
    )


def record_executable_state_change(
    *,
    recorded_at: datetime,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    root = _repo_root(repository)
    _require(
        not _logical_path(root, STATE_EVIDENCE_PATH, must_exist=False).exists(),
        "executable state evidence already exists",
    )
    contract = load_executable_no_call_preflight_contract(repository=root)
    qualification = _load_qualification(root)
    _, _, attestation, predecessor_state = _load_v2_chain(root)
    state = bind_executable_state_change_evidence(
        contract,
        qualification,
        attestation,
        predecessor_state,
        recorded_at=recorded_at,
    )
    _write_once(root, STATE_EVIDENCE_PATH, _canonical_bytes(state))
    return validate_executable_state_change(repository=root)


def validate_executable_state_change(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    contract = load_executable_no_call_preflight_contract(repository=root)
    qualification = _load_qualification(root)
    _, _, attestation, predecessor_state = _load_v2_chain(root)
    raw = _read_bytes(root, STATE_EVIDENCE_PATH)
    try:
        state = ExecutableStateChangeEvidence.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise ExecutableNoCallPreflightError("executable state evidence is invalid") from exc
    _require(raw == _canonical_bytes(state), "executable state bytes are not canonical")
    expected = bind_executable_state_change_evidence(
        contract,
        qualification,
        attestation,
        predecessor_state,
        recorded_at=state.recorded_at,
    )
    _require(state == expected, "executable state evidence has drifted")
    return {
        "status": "EXECUTABLE_STATE_BOUND_EXACT_USER_APPROVAL_REQUIRED",
        "contract_id": contract.contract_id,
        "source_qualification_hash": qualification.content_hash,
        "state_change_evidence_id": state.evidence_id,
        "state_change_evidence_content_hash": state.content_hash,
        "identity_assurance": IDENTITY_ASSURANCE,
        "credential_presence_verified": False,
        "dotenv_read_or_stat_performed": False,
        "exact_approval_required": True,
    }


def build_executable_approval_receipt(
    contract: ExecutableNoCallPreflightContract,
    qualification: ExecutableSourceQualification,
    state: ExecutableStateChangeEvidence,
    *,
    recorded_at: datetime,
) -> ExecutableApprovalReceipt:
    _require(state.contract_id == contract.contract_id, "approval state contract differs")
    _require(
        state.source_qualification_content_hash == qualification.content_hash,
        "approval state qualification differs",
    )
    _require(recorded_at >= state.recorded_at, "approval predates executable state")
    body = {
        "schema_version": "preflight-user-exact-approval-receipt-v3",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "source_qualification_content_hash": qualification.content_hash,
        "state_change_evidence_id": state.evidence_id,
        "state_change_evidence_content_hash": state.content_hash,
        "approved_scopes": APPROVED_SCOPES,
        "identity_assurance": IDENTITY_ASSURANCE,
        "current_dotenv_placement_reconfirmed": True,
        "attempt_limit": 1,
        "credential_value_in_approval": False,
        "provider_evaluator_agent_execution_authorized": False,
        "network_or_transport_authorized": False,
        "execution_hash_candidate_cost_or_paid_execution_authorized": False,
        "recorded_at": _utc(recorded_at, label="approval receipt recorded_at"),
    }
    content_hash = _semantic_hash(body)
    return ExecutableApprovalReceipt(
        **body,
        receipt_id=_derived_id("ncpapprovalreceipt", content_hash),
        content_hash=content_hash,
    )


def bind_executable_approval(
    contract: ExecutableNoCallPreflightContract,
    qualification: ExecutableSourceQualification,
    state: ExecutableStateChangeEvidence,
    receipt: ExecutableApprovalReceipt,
    *,
    recorded_at: datetime,
) -> ExecutableApprovalBinding:
    _require(receipt.contract_id == contract.contract_id, "approval receipt contract differs")
    _require(
        receipt.source_qualification_content_hash == qualification.content_hash,
        "approval receipt qualification differs",
    )
    _require(
        receipt.state_change_evidence_id == state.evidence_id
        and receipt.state_change_evidence_content_hash == state.content_hash,
        "approval receipt does not bind exact state",
    )
    _require(recorded_at >= receipt.recorded_at, "approval binding predates receipt")
    body = {
        "schema_version": "preflight-approval-binding-v3",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "source_qualification_content_hash": qualification.content_hash,
        "state_change_evidence_id": state.evidence_id,
        "state_change_evidence_content_hash": state.content_hash,
        "user_approval_receipt_id": receipt.receipt_id,
        "user_approval_receipt_content_hash": receipt.content_hash,
        "approved_scopes": APPROVED_SCOPES,
        "identity_assurance": IDENTITY_ASSURANCE,
        "attempt_limit": 1,
        "provider_evaluator_agent_execution_authorized": False,
        "network_or_transport_authorized": False,
        "execution_hash_candidate_cost_or_paid_execution_authorized": False,
        "recorded_at": _utc(recorded_at, label="approval binding recorded_at"),
    }
    content_hash = _semantic_hash(body)
    return ExecutableApprovalBinding(
        **body,
        approval_id=_derived_id("ncpapproval", content_hash),
        content_hash=content_hash,
    )


def record_executable_exact_approval(
    *,
    exact_contract_id: str,
    exact_source_qualification_hash: str,
    exact_state_change_evidence_id: str,
    recorded_at: datetime,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    root = _repo_root(repository)
    for path in (APPROVAL_RECEIPT_PATH, APPROVAL_BINDING_PATH):
        _require(
            not _logical_path(root, path, must_exist=False).exists(), "approval already exists"
        )
    contract = load_executable_no_call_preflight_contract(repository=root)
    qualification = _load_qualification(root)
    validate_executable_state_change(repository=root)
    state = ExecutableStateChangeEvidence.model_validate_json(
        _read_bytes(root, STATE_EVIDENCE_PATH)
    )
    _require(exact_contract_id == contract.contract_id, "approval did not cite exact contract")
    _require(
        exact_source_qualification_hash == qualification.content_hash,
        "approval did not cite exact source qualification",
    )
    _require(
        exact_state_change_evidence_id == state.evidence_id,
        "approval did not cite exact state evidence",
    )
    receipt = build_executable_approval_receipt(
        contract,
        qualification,
        state,
        recorded_at=recorded_at,
    )
    approval = bind_executable_approval(
        contract,
        qualification,
        state,
        receipt,
        recorded_at=recorded_at,
    )
    _write_once(root, APPROVAL_RECEIPT_PATH, _canonical_bytes(receipt))
    _write_once(root, APPROVAL_BINDING_PATH, _canonical_bytes(approval))
    return validate_executable_exact_approval(repository=root)


def validate_executable_exact_approval(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    contract = load_executable_no_call_preflight_contract(repository=root)
    qualification = _load_qualification(root)
    validate_executable_state_change(repository=root)
    state = ExecutableStateChangeEvidence.model_validate_json(
        _read_bytes(root, STATE_EVIDENCE_PATH)
    )
    receipt_raw = _read_bytes(root, APPROVAL_RECEIPT_PATH)
    approval_raw = _read_bytes(root, APPROVAL_BINDING_PATH)
    receipt = ExecutableApprovalReceipt.model_validate_json(receipt_raw)
    approval = ExecutableApprovalBinding.model_validate_json(approval_raw)
    _require(receipt_raw == _canonical_bytes(receipt), "approval receipt bytes differ")
    _require(approval_raw == _canonical_bytes(approval), "approval binding bytes differ")
    expected = bind_executable_approval(
        contract,
        qualification,
        state,
        receipt,
        recorded_at=approval.recorded_at,
    )
    _require(approval == expected, "approval binding has drifted")
    return {
        "status": "EXECUTABLE_EXACT_APPROVAL_RECORDED_ATTEMPT_NOT_STARTED",
        "contract_id": contract.contract_id,
        "source_qualification_hash": qualification.content_hash,
        "state_change_evidence_id": state.evidence_id,
        "approval_id": approval.approval_id,
        "approval_content_hash": approval.content_hash,
        "identity_assurance": approval.identity_assurance,
        "attempt_limit": 1,
        "external_observations_made": 0,
        "attempt_started": False,
        "paid_execution_authorized": False,
    }


RunCallable = Callable[..., subprocess.CompletedProcess[bytes]]


def run_isolated_dotenv_sdk_observation(
    contract: ExecutableNoCallPreflightContract,
    *,
    repository: str | Path | None = None,
    environment_present: Callable[[str], bool] | None = None,
    run: RunCallable = subprocess.run,
) -> ExecutableSDKObservation:
    root = _repo_root(repository)
    present = environment_present or (lambda name: name in os.environ)
    pythonhome_absent = not present("PYTHONHOME")
    pythonpath_absent = not present("PYTHONPATH")
    if not pythonhome_absent or not pythonpath_absent:
        return ExecutableSDKObservation(
            parent_pythonhome_absent=pythonhome_absent,
            parent_pythonpath_absent=pythonpath_absent,
            child_start_count=0,
            child=None,
            passed=False,
        )
    child_path = _logical_path(root, CHILD_PATH, must_exist=True)
    _require(
        sha256_bytes(_read_bytes(root, CHILD_PATH)) == contract.runtime_profile.child_file_sha256,
        "isolated child source differs from contract",
    )
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    completed = run(
        [
            str(Path(sys.executable).resolve(strict=True)),
            "-I",
            "-E",
            "-s",
            "-B",
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
        env={"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        creationflags=creationflags,
    )
    _require(completed.returncode == 0, "isolated child failed")
    _require(not completed.stderr, "isolated child wrote stderr")
    _require(len(completed.stdout) <= CHILD_OUTPUT_LIMIT, "isolated child output exceeded limit")
    try:
        child = IsolatedDotenvSDKObservation.model_validate_json(completed.stdout)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise ExecutableNoCallPreflightError("isolated child output is invalid") from exc
    return ExecutableSDKObservation(
        parent_pythonhome_absent=True,
        parent_pythonpath_absent=True,
        child_start_count=1,
        child=child,
        passed=bool(child.sdk_observation and child.sdk_observation["passed"]),
    )


def _ledger_snapshot(root: Path) -> str:
    rows = []
    for path in (ATTEMPT_PATH, ACTION_STARTED_PATH, TERMINAL_PATH):
        selected = _logical_path(root, path, must_exist=False)
        rows.append({"path": path.as_posix(), "exists": selected.exists()})
    _require(not any(row["exists"] for row in rows), "attempt ledger is already consumed")
    return sha256_json(rows)


def _empty_ledger_snapshot_hash() -> str:
    return sha256_json(
        [
            {"path": path.as_posix(), "exists": False}
            for path in (ATTEMPT_PATH, ACTION_STARTED_PATH, TERMINAL_PATH)
        ]
    )


def _build_attempt(
    contract: ExecutableNoCallPreflightContract,
    qualification: ExecutableSourceQualification,
    state: ExecutableStateChangeEvidence,
    approval: ExecutableApprovalBinding,
    *,
    ledger_snapshot_hash: str,
    created_at: datetime,
) -> AttemptIntent:
    _require(approval.contract_id == contract.contract_id, "attempt approval contract differs")
    _require(
        approval.source_qualification_content_hash == qualification.content_hash,
        "attempt approval qualification differs",
    )
    _require(
        approval.state_change_evidence_id == state.evidence_id,
        "attempt approval state differs",
    )
    _require(created_at >= approval.recorded_at, "attempt predates approval")
    body = {
        "schema_version": "preflight-attempt-intent-v3",
        "contract_version": CONTRACT_VERSION,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "source_qualification_content_hash": qualification.content_hash,
        "state_change_evidence_id": state.evidence_id,
        "state_change_evidence_content_hash": state.content_hash,
        "approval_id": approval.approval_id,
        "approval_content_hash": approval.content_hash,
        "ledger_snapshot_hash": ledger_snapshot_hash,
        "created_at": _utc(created_at, label="attempt created_at"),
        "attempt_number": 1,
        "state": "intent_recorded",
        "one_use": True,
        "retry_or_resume_allowed": False,
    }
    content_hash = _semantic_hash(body)
    return AttemptIntent(
        **body,
        attempt_id=_derived_id("ncpattempt", content_hash),
        content_hash=content_hash,
    )


def _build_action_started(attempt: AttemptIntent, *, recorded_at: datetime) -> ActionStarted:
    _require(recorded_at >= attempt.created_at, "action marker predates attempt")
    body = {
        "schema_version": "preflight-action-started-v3",
        "attempt_id": attempt.attempt_id,
        "attempt_content_hash": attempt.content_hash,
        "sequence": 1,
        "recorded_at": _utc(recorded_at, label="action marker recorded_at"),
    }
    content_hash = _semantic_hash(body)
    return ActionStarted(
        **body,
        marker_id=_derived_id("ncpstarted", content_hash),
        content_hash=content_hash,
    )


def _terminal_reason_for_sdk(
    observation: ExecutableSDKObservation,
) -> tuple[TerminalOutcome, TerminalReason]:
    if not observation.parent_pythonhome_absent or not observation.parent_pythonpath_absent:
        return TerminalOutcome.BLOCKED, TerminalReason.PYTHON_ENVIRONMENT_NOT_CLEAN
    _require(observation.child is not None, "clean SDK observation lacks child")
    if observation.child.dotenv.error_code in {"sdk_checker_error", "isolated_checker_error"}:
        return TerminalOutcome.ERROR, TerminalReason.CHECKER_ERROR
    if not observation.child.dotenv.exact_subject_nonempty:
        return TerminalOutcome.BLOCKED, TerminalReason.DOTENV_CREDENTIAL_MISSING
    return TerminalOutcome.BLOCKED, TerminalReason.SDK_NO_CALL_FAILED


def _build_terminal(
    attempt: AttemptIntent,
    action: ActionStarted,
    *,
    outcome: TerminalOutcome,
    reason: TerminalReason | None,
    docker_observation: dict[str, Any] | None,
    sdk_observation: ExecutableSDKObservation | None,
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
        "schema_version": "preflight-terminal-v3",
        "attempt_id": attempt.attempt_id,
        "action_started_id": action.marker_id,
        "previous_content_hash": action.content_hash,
        "sequence": 2,
        "outcome": outcome,
        "reason": reason,
        "docker_observation": docker_observation,
        "sdk_observation": None
        if sdk_observation is None
        else sdk_observation.model_dump(mode="json"),
        "activity_accounting_complete": activity_accounting_complete,
        "unknown_post_marker_activity_possible": not activity_accounting_complete,
        "docker_cli_command_count": docker_count,
        "dotenv_file_read_count": dotenv_count,
        "sdk_child_start_count": child_count,
        "credential_value_return_hash_prefix_or_length_count": 0,
        "network_call_count": 0,
        "provider_evaluator_agent_call_count": 0,
        "recorded_at": _utc(recorded_at, label="terminal recorded_at"),
    }
    content_hash = _semantic_hash(body)
    return TerminalTransition(
        **body,
        terminal_id=_derived_id("ncpterminal", content_hash),
        content_hash=content_hash,
    )


def validate_executable_attempt_chain(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    contract = load_executable_no_call_preflight_contract(repository=root)
    qualification = _load_qualification(root)
    validate_executable_state_change(repository=root)
    approval_summary = validate_executable_exact_approval(repository=root)
    state = ExecutableStateChangeEvidence.model_validate_json(
        _read_bytes(root, STATE_EVIDENCE_PATH)
    )
    approval = ExecutableApprovalBinding.model_validate_json(
        _read_bytes(root, APPROVAL_BINDING_PATH)
    )
    attempt_raw = _read_bytes(root, ATTEMPT_PATH)
    action_raw = _read_bytes(root, ACTION_STARTED_PATH)
    terminal_raw = _read_bytes(root, TERMINAL_PATH)
    try:
        attempt = AttemptIntent.model_validate_json(attempt_raw)
        action = ActionStarted.model_validate_json(action_raw)
        terminal = TerminalTransition.model_validate_json(terminal_raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise ExecutableNoCallPreflightError("attempt chain artifact is invalid") from exc
    for label, raw, value in (
        ("attempt", attempt_raw, attempt),
        ("action marker", action_raw, action),
        ("terminal", terminal_raw, terminal),
    ):
        _require(raw == _canonical_bytes(value), f"{label} bytes are not canonical")
    _require(attempt.contract_id == contract.contract_id, "attempt contract differs")
    _require(
        attempt.source_qualification_content_hash == qualification.content_hash,
        "attempt source qualification differs",
    )
    _require(
        attempt.state_change_evidence_id == state.evidence_id
        and attempt.state_change_evidence_content_hash == state.content_hash,
        "attempt state evidence differs",
    )
    _require(
        attempt.approval_id == approval.approval_id
        and attempt.approval_content_hash == approval.content_hash,
        "attempt approval differs",
    )
    _require(
        attempt.ledger_snapshot_hash == _empty_ledger_snapshot_hash(),
        "attempt ledger snapshot differs",
    )
    _require(
        action.attempt_id == attempt.attempt_id
        and action.attempt_content_hash == attempt.content_hash,
        "action marker attempt differs",
    )
    _require(action.recorded_at >= attempt.created_at, "action marker predates attempt")
    _require(
        terminal.attempt_id == attempt.attempt_id
        and terminal.action_started_id == action.marker_id
        and terminal.previous_content_hash == action.content_hash,
        "terminal chain differs",
    )
    _require(terminal.recorded_at >= action.recorded_at, "terminal predates action marker")
    return {
        "status": "EXECUTABLE_NO_CALL_PREFLIGHT_TERMINAL_VALID",
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
        "network_calls_made": 0,
        "provider_evaluator_agent_calls_made": 0,
        "paid_execution_authorized": False,
    }


def run_executable_no_call_preflight_once(
    *,
    repository: str | Path | None = None,
    docker_observer: Callable[
        ..., dict[str, Any]
    ] = d137.run_d137_docker_no_call_preflight_observation,
    sdk_observer: Callable[..., ExecutableSDKObservation] = run_isolated_dotenv_sdk_observation,
) -> dict[str, Any]:
    root = _repo_root(repository)
    contract = load_executable_no_call_preflight_contract(repository=root)
    qualification = _load_qualification(root)
    state = ExecutableStateChangeEvidence.model_validate_json(
        _read_bytes(root, STATE_EVIDENCE_PATH)
    )
    validate_executable_exact_approval(repository=root)
    approval = ExecutableApprovalBinding.model_validate_json(
        _read_bytes(root, APPROVAL_BINDING_PATH)
    )
    ledger_hash = _ledger_snapshot(root)
    attempt = _build_attempt(
        contract,
        qualification,
        state,
        approval,
        ledger_snapshot_hash=ledger_hash,
        created_at=datetime.now(UTC),
    )
    _write_once(root, ATTEMPT_PATH, _canonical_bytes(attempt))
    action = _build_action_started(attempt, recorded_at=datetime.now(UTC))
    _write_once(root, ACTION_STARTED_PATH, _canonical_bytes(action))

    docker: dict[str, Any] | None = None
    sdk: ExecutableSDKObservation | None = None
    try:
        docker = docker_observer(repository=root)
        d137.validate_d137_docker_no_call_preflight_observation(docker)
        if not docker["passed"]:
            outcome, reason = TerminalOutcome.BLOCKED, TerminalReason.DOCKER_NOT_READY
        else:
            sdk = sdk_observer(contract, repository=root)
            if sdk.passed:
                outcome, reason = TerminalOutcome.READY, None
            else:
                outcome, reason = _terminal_reason_for_sdk(sdk)
    except Exception:
        docker = None
        sdk = None
        outcome, reason = TerminalOutcome.ERROR, TerminalReason.CHECKER_ERROR
    terminal = _build_terminal(
        attempt,
        action,
        outcome=outcome,
        reason=reason,
        docker_observation=docker,
        sdk_observation=sdk,
        activity_accounting_complete=(outcome != TerminalOutcome.ERROR),
        recorded_at=datetime.now(UTC),
    )
    raw = _canonical_bytes(terminal)
    _require(b"sk-" not in raw.lower(), "terminal contains credential-like material")
    _write_once(root, TERMINAL_PATH, raw)
    return validate_executable_attempt_chain(repository=root)
