"""Offline successor contract for receipt-free, user-attested credential placement.

This module never reads or stats ``.env`` and has no Docker, SDK, network, or
provider entrypoint.  It records a bounded user attestation without upgrading
it to independent proof, then requires a later exact approval bound to the
derived state-evidence identity.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from patchloop.contracts import FrozenStrictModel
from patchloop.errors import ContractError
from patchloop.evals import versioned_no_call_preflight as v1
from patchloop.runtime import repository_root
from patchloop.util import safe_relative_path, sha256_bytes, sha256_json

CONTRACT_SCHEMA_VERSION = "versioned-no-call-preflight-contract-v2"
CONTRACT_VERSION = "ac-evaluator-v2-no-call-preflight-v2"
CONTRACT_PATH = Path("experiments/evaluator-v2-no-call-preflight-v2.contract.json")

PREDECESSOR_EVIDENCE_COMMIT = "e46525d649525502cd808e181ee04ff935f35dce"
PREDECESSOR_QUALIFICATION_PATH = v1.QUALIFICATION_PATH

QUALIFICATION_SCHEMA_VERSION = "user-attested-no-call-preflight-source-qualification-v2"
QUALIFICATION_ID = "ac-evaluator-v2-user-attested-no-call-preflight-source-20260812-r1"
QUALIFICATION_STATUS = "OFFLINE_USER_ATTESTED_CONTRACT_SOURCE_QUALIFIED_LIVE_CLOSED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-no-call-preflight-v2-source-qualification.json"
)
USER_ATTESTATION_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-no-call-preflight-v2-user-attestation.json"
)
STATE_EVIDENCE_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-no-call-preflight-v2-state-change-evidence.json"
)
APPROVAL_RECEIPT_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-no-call-preflight-v2-exact-approval-receipt.json"
)
APPROVAL_BINDING_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-no-call-preflight-v2-approval-binding.json"
)

SOURCE_ADDED_PATHS = tuple(
    sorted(
        (
            CONTRACT_PATH.as_posix(),
            "patchloop/evals/user_attested_no_call_preflight.py",
            "scripts/build_user_attested_no_call_preflight_contract.py",
            "tests/test_user_attested_no_call_preflight_contract.py",
        )
    )
)
SOURCE_FILES = tuple(Path(item) for item in SOURCE_ADDED_PATHS)

STATE_CHANGE_SUBJECTS = ("OPENAI_API_KEY",)
DOTENV_SURFACE = "repository-root-dotenv"
IDENTITY_ASSURANCE = "current-user-self-attested-not-authenticated-or-signed"
ATTESTATION_CLAIM = "openai-api-key-configured-in-repository-root-dotenv"
APPROVED_SCOPES = (
    "docker-metadata-read-only",
    "repository-root-dotenv-exact-openai-api-key-loader",
    "isolated-sdk-import-and-no-transport-probe",
)


class UserAttestedNoCallPreflightError(ContractError):
    """Raised when the successor contract or an append-only binding fails closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise UserAttestedNoCallPreflightError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = repository_root() if repository is None else Path(repository)
    return selected.resolve(strict=True)


def _logical_path(root: Path, relative: Path, *, must_exist: bool) -> Path:
    safe = safe_relative_path(relative.as_posix(), field_name="user-attested preflight path")
    selected = root.joinpath(*Path(safe).parts)
    resolved = selected.resolve(strict=must_exist)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise UserAttestedNoCallPreflightError("preflight path escaped repository") from exc
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
        raise UserAttestedNoCallPreflightError(
            f"append-only artifact already exists: {relative.as_posix()}"
        ) from exc
    except OSError as exc:
        raise UserAttestedNoCallPreflightError(
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


class StateChangeEvidenceKindV2(StrEnum):
    USER_ATTESTED_CREDENTIAL_LOCATION = "credential_location_user_attested_v2"


class UserAttestedStateChangeRule(FrozenStrictModel):
    schema_version: Literal["preflight-state-change-rule-v2"] = "preflight-state-change-rule-v2"
    allowed_kind: Literal[StateChangeEvidenceKindV2.USER_ATTESTED_CREDENTIAL_LOCATION] = (
        StateChangeEvidenceKindV2.USER_ATTESTED_CREDENTIAL_LOCATION
    )
    exact_subject_names: tuple[str, ...] = STATE_CHANGE_SUBJECTS
    exact_location_surface: Literal["repository-root-dotenv"] = DOTENV_SURFACE
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    external_receipt_required: Literal[False] = False
    independent_trust_anchor_required: Literal[False] = False
    attestation_proves_credential_presence: Literal[False] = False
    exact_preflight_still_required: Literal[True] = True
    exact_approval_after_evidence_id_required: Literal[True] = True
    raw_credential_value_allowed: Literal[False] = False
    unchanged_blocker_is_state_change: Literal[False] = False
    source_or_contract_change_requires_version_bump: Literal[True] = True

    @model_validator(mode="after")
    def validate_exact_rule(self) -> UserAttestedStateChangeRule:
        if self.exact_subject_names != STATE_CHANGE_SUBJECTS:
            raise ValueError("state-change subjects drifted")
        return self


class DotenvExactKeyLoaderContract(FrozenStrictModel):
    schema_version: Literal["dotenv-exact-key-loader-contract-v2"] = (
        "dotenv-exact-key-loader-contract-v2"
    )
    dotenv_surface: Literal["repository-root-dotenv"] = DOTENV_SURFACE
    exact_key_names: tuple[str, ...] = STATE_CHANGE_SUBJECTS
    read_may_begin_only_after_action_started: Literal[True] = True
    dotenv_file_read_limit: Literal[1] = 1
    exact_key_value_load_limit: Literal[1] = 1
    isolated_child_forward_limit: Literal[1] = 1
    parent_or_agent_value_return_limit: Literal[0] = 0
    other_key_forward_limit: Literal[0] = 0
    value_log_persist_hash_prefix_or_length_limit: Literal[0] = 0
    transport_dispatch_limit: Literal[0] = 0
    credential_mutation_limit: Literal[0] = 0
    loader_runtime_implemented: Literal[False] = False

    @model_validator(mode="after")
    def validate_exact_loader(self) -> DotenvExactKeyLoaderContract:
        if self.exact_key_names != STATE_CHANGE_SUBJECTS:
            raise ValueError("dotenv loader subjects drifted")
        return self


class UserAttestedObservationContract(FrozenStrictModel):
    schema_version: Literal["preflight-observation-contract-v2"] = (
        "preflight-observation-contract-v2"
    )
    phases: tuple[str, ...] = ("docker_metadata", "dotenv_sdk_no_call")
    docker_metadata_queries: tuple[str, ...] = v1.DOCKER_METADATA_QUERIES
    parent_environment_membership_names: tuple[str, ...] = ("PYTHONHOME", "PYTHONPATH")
    parent_environment_membership_check_limit: Literal[2] = 2
    dotenv_subject_membership_check_limit: Literal[1] = 1
    docker_container_start_limit: Literal[0] = 0
    sdk_isolated_child_start_limit: Literal[1] = 1
    network_call_limit: Literal[0] = 0
    provider_evaluator_agent_call_limit: Literal[0] = 0
    observation_result_values_allowed: Literal[False] = False

    @model_validator(mode="after")
    def validate_exact_observation(self) -> UserAttestedObservationContract:
        if self.docker_metadata_queries != v1.DOCKER_METADATA_QUERIES:
            raise ValueError("Docker metadata queries drifted")
        return self


class UserAttestedSourceAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    commit_source_qualification_authorized: Literal[True] = True
    user_attestation_binding_supported: Literal[True] = True
    attestation_is_independent_proof: Literal[False] = False
    external_preflight_attempt_authorized: Literal[False] = False
    dotenv_docker_or_sdk_observation_authorized: Literal[False] = False
    execution_hash_or_candidate_authorized: Literal[False] = False
    pricing_or_cost_reservation_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    memory_retrieval_or_injection_authorized: Literal[False] = False
    automatic_retry_replacement_or_resume_authorized: Literal[False] = False
    memory_benefit_claim_authorized: Literal[False] = False


class UserAttestedNoCallPreflightContract(FrozenStrictModel):
    schema_version: Literal["versioned-no-call-preflight-contract-v2"] = CONTRACT_SCHEMA_VERSION
    contract_version: Literal["ac-evaluator-v2-no-call-preflight-v2"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor_contract_version: Literal["ac-evaluator-v2-no-call-preflight-v1"] = (
        v1.CONTRACT_VERSION
    )
    predecessor_contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor_contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_contract_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_source_qualification_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_terminal_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_v2_source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    successor_suite_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_tuple_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_observation_contract_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_transition_policy_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_change_rule: UserAttestedStateChangeRule
    dotenv_loader_contract: DotenvExactKeyLoaderContract
    observation_contract: UserAttestedObservationContract
    transition_policy: v1.PreflightTransitionPolicy
    source_authority: UserAttestedSourceAuthority
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> UserAttestedNoCallPreflightContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected_hash = sha256_json(body)
        if self.content_hash != expected_hash:
            raise ValueError("user-attested preflight contract content hash mismatch")
        if self.contract_id != _derived_id("ncpcontract", expected_hash):
            raise ValueError("user-attested preflight contract id mismatch")
        return self


class UserCredentialLocationAttestation(FrozenStrictModel):
    schema_version: Literal["preflight-user-credential-location-attestation-v2"] = (
        "preflight-user-credential-location-attestation-v2"
    )
    attestation_id: str = Field(pattern=r"^ncpattestation_[0-9a-f]{64}$")
    contract_version: Literal["ac-evaluator-v2-no-call-preflight-v2"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    claim: Literal["openai-api-key-configured-in-repository-root-dotenv"] = ATTESTATION_CLAIM
    subject_names_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    location_surface: Literal["repository-root-dotenv"] = DOTENV_SURFACE
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    external_receipt_present: Literal[False] = False
    independent_verification_completed: Literal[False] = False
    attestation_proves_credential_presence: Literal[False] = False
    dotenv_read_or_stat_performed: Literal[False] = False
    raw_credential_value_observed: Literal[False] = False
    raw_credential_value_persisted: Literal[False] = False
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("user attestation recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> UserCredentialLocationAttestation:
        if self.subject_names_hash != sha256_json(list(STATE_CHANGE_SUBJECTS)):
            raise ValueError("user attestation subjects mismatch")
        body = self.model_dump(mode="json", exclude={"attestation_id", "content_hash"})
        expected_hash = sha256_json(body)
        if self.content_hash != expected_hash:
            raise ValueError("user attestation content hash mismatch")
        if self.attestation_id != _derived_id("ncpattestation", expected_hash):
            raise ValueError("user attestation id mismatch")
        return self


class UserAttestedStateChangeEvidence(FrozenStrictModel):
    schema_version: Literal["preflight-state-change-evidence-v2"] = (
        "preflight-state-change-evidence-v2"
    )
    evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    contract_version: Literal["ac-evaluator-v2-no-call-preflight-v2"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_kind: Literal[StateChangeEvidenceKindV2.USER_ATTESTED_CREDENTIAL_LOCATION] = (
        StateChangeEvidenceKindV2.USER_ATTESTED_CREDENTIAL_LOCATION
    )
    subject_names_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    location_surface: Literal["repository-root-dotenv"] = DOTENV_SURFACE
    user_attestation_id: str = Field(pattern=r"^ncpattestation_[0-9a-f]{64}$")
    user_attestation_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_terminal_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    external_receipt_present: Literal[False] = False
    independent_verification_completed: Literal[False] = False
    attestation_proves_credential_presence: Literal[False] = False
    exact_preflight_still_required: Literal[True] = True
    raw_credential_value_observed: Literal[False] = False
    raw_credential_value_persisted: Literal[False] = False
    source_or_contract_changed: Literal[True] = True
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("state-change evidence recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> UserAttestedStateChangeEvidence:
        if self.subject_names_hash != sha256_json(list(STATE_CHANGE_SUBJECTS)):
            raise ValueError("state-change evidence subjects mismatch")
        body = self.model_dump(mode="json", exclude={"evidence_id", "content_hash"})
        expected_hash = sha256_json(body)
        if self.content_hash != expected_hash:
            raise ValueError("state-change evidence content hash mismatch")
        if self.evidence_id != _derived_id("ncpstate", expected_hash):
            raise ValueError("state-change evidence id mismatch")
        return self


class UserExactApprovalReceipt(FrozenStrictModel):
    schema_version: Literal["preflight-user-exact-approval-receipt-v2"] = (
        "preflight-user-exact-approval-receipt-v2"
    )
    receipt_id: str = Field(pattern=r"^ncpapprovalreceipt_[0-9a-f]{64}$")
    contract_version: Literal["ac-evaluator-v2-no-call-preflight-v2"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_change_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_change_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    attempt_limit: Literal[1] = 1
    credential_value_in_approval: Literal[False] = False
    credential_provisioning_authorized: Literal[False] = False
    execution_hash_or_candidate_authorized: Literal[False] = False
    cost_or_paid_execution_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("approval receipt recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> UserExactApprovalReceipt:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("approval receipt scope drifted")
        body = self.model_dump(mode="json", exclude={"receipt_id", "content_hash"})
        expected_hash = sha256_json(body)
        if self.content_hash != expected_hash:
            raise ValueError("approval receipt content hash mismatch")
        if self.receipt_id != _derived_id("ncpapprovalreceipt", expected_hash):
            raise ValueError("approval receipt id mismatch")
        return self


class UserAttestedApprovalBinding(FrozenStrictModel):
    schema_version: Literal["preflight-approval-binding-v2"] = "preflight-approval-binding-v2"
    approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    contract_version: Literal["ac-evaluator-v2-no-call-preflight-v2"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_change_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_change_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    user_approval_receipt_id: str = Field(pattern=r"^ncpapprovalreceipt_[0-9a-f]{64}$")
    user_approval_receipt_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    attempt_limit: Literal[1] = 1
    credential_value_in_approval: Literal[False] = False
    credential_provisioning_authorized: Literal[False] = False
    execution_hash_or_candidate_authorized: Literal[False] = False
    cost_or_paid_execution_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("approval binding recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> UserAttestedApprovalBinding:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("approval binding scope drifted")
        body = self.model_dump(mode="json", exclude={"approval_id", "content_hash"})
        expected_hash = sha256_json(body)
        if self.content_hash != expected_hash:
            raise ValueError("approval binding content hash mismatch")
        if self.approval_id != _derived_id("ncpapproval", expected_hash):
            raise ValueError("approval binding id mismatch")
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
        if self.parents != (PREDECESSOR_EVIDENCE_COMMIT,):
            raise ValueError("v2 source predecessor drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v2 source additions drifted")
        return self


class UserAttestedQualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    contract_source_qualified: Literal[True] = True
    user_attestation_created: Literal[False] = False
    state_change_evidence_created: Literal[False] = False
    approval_created_or_inferred: Literal[False] = False
    attempt_or_transition_created: Literal[False] = False
    credential_dotenv_or_environment_observation_count: Literal[0] = 0
    credential_value_observation_or_mutation_count: Literal[0] = 0
    docker_or_sdk_observation_count: Literal[0] = 0
    network_provider_evaluator_agent_call_count: Literal[0] = 0
    execution_hash_or_candidate_created: Literal[False] = False
    cost_reserved_or_spent_usd: Literal["0"] = "0"


class UserAttestedSourceQualification(FrozenStrictModel):
    schema_version: Literal["user-attested-no-call-preflight-source-qualification-v2"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal[
        "ac-evaluator-v2-user-attested-no-call-preflight-source-20260812-r1"
    ] = QUALIFICATION_ID
    status: Literal["OFFLINE_USER_ATTESTED_CONTRACT_SOURCE_QUALIFIED_LIVE_CLOSED"] = (
        QUALIFICATION_STATUS
    )
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[CommittedFileBinding, ...]
    contract_version: Literal["ac-evaluator-v2-no-call-preflight-v2"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    contract_file: CommittedFileBinding
    predecessor_contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor_contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authority: UserAttestedQualificationAuthority
    next_gate: Literal["user-attestation-state-evidence-then-exact-approval"] = (
        "user-attestation-state-evidence-then-exact-approval"
    )
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("qualification recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> UserAttestedSourceQualification:
        if tuple(item.path for item in self.source_files) != tuple(
            item.as_posix() for item in SOURCE_FILES
        ):
            raise ValueError("qualification source inventory drifted")
        if self.contract_file.path != CONTRACT_PATH.as_posix():
            raise ValueError("qualification contract path drifted")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != sha256_json(body):
            raise ValueError("qualification content hash mismatch")
        return self


def _build_contract(root: Path) -> UserAttestedNoCallPreflightContract:
    predecessor = v1.load_versioned_no_call_preflight_contract(repository=root)
    predecessor_contract_raw = _read_bytes(root, v1.CONTRACT_PATH)
    predecessor_qualification_raw = _read_bytes(root, PREDECESSOR_QUALIFICATION_PATH)
    predecessor_qualification = v1.VersionedNoCallPreflightSourceQualification.model_validate_json(
        predecessor_qualification_raw
    )
    _require(
        predecessor_qualification.contract_id == predecessor.contract_id
        and predecessor_qualification.contract_content_hash == predecessor.content_hash,
        "predecessor qualification does not bind predecessor contract",
    )
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "predecessor_contract_version": predecessor.contract_version,
        "predecessor_contract_id": predecessor.contract_id,
        "predecessor_contract_content_hash": predecessor.content_hash,
        "predecessor_contract_file_sha256": sha256_bytes(predecessor_contract_raw),
        "predecessor_source_qualification_hash": predecessor_qualification.content_hash,
        "predecessor_source_qualification_file_sha256": sha256_bytes(predecessor_qualification_raw),
        "predecessor_terminal_file_sha256": predecessor.d141_blocked_terminal.file_sha256,
        "evaluator_v2_source_qualification_hash": (
            predecessor.evaluator_v2_source_qualification_hash
        ),
        "evaluator_source_hash": predecessor.evaluator_source_hash,
        "successor_suite_hash": predecessor.successor_suite_hash,
        "runtime_tuple_hash": predecessor.runtime_tuple_hash,
        "predecessor_observation_contract_hash": sha256_json(
            predecessor.observation_contract.model_dump(mode="json")
        ),
        "predecessor_transition_policy_hash": sha256_json(
            predecessor.transition_policy.model_dump(mode="json")
        ),
        "state_change_rule": UserAttestedStateChangeRule().model_dump(mode="json"),
        "dotenv_loader_contract": DotenvExactKeyLoaderContract().model_dump(mode="json"),
        "observation_contract": UserAttestedObservationContract().model_dump(mode="json"),
        "transition_policy": predecessor.transition_policy.model_dump(mode="json"),
        "source_authority": UserAttestedSourceAuthority().model_dump(mode="json"),
    }
    content_hash = _semantic_hash(body)
    return UserAttestedNoCallPreflightContract(
        **body,
        contract_id=_derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def load_user_attested_no_call_preflight_contract(
    *, repository: str | Path | None = None
) -> UserAttestedNoCallPreflightContract:
    root = _repo_root(repository)
    raw = _read_bytes(root, CONTRACT_PATH)
    try:
        contract = UserAttestedNoCallPreflightContract.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise UserAttestedNoCallPreflightError("v2 preflight contract artifact is invalid") from exc
    _require(raw == _canonical_bytes(contract), "v2 preflight contract bytes are not canonical")
    _require(contract == _build_contract(root), "v2 preflight contract has drifted")
    return contract


def validate_user_attested_no_call_preflight_contract(
    *, repository: str | Path | None = None
) -> UserAttestedNoCallPreflightContract:
    return load_user_attested_no_call_preflight_contract(repository=repository)


def materialize_user_attested_no_call_preflight_contract(
    *, repository: str | Path | None = None
) -> dict[str, Any]:
    root = _repo_root(repository)
    selected = _logical_path(root, CONTRACT_PATH, must_exist=False)
    if selected.exists():
        contract = load_user_attested_no_call_preflight_contract(repository=root)
        raw = _read_bytes(root, CONTRACT_PATH)
    else:
        contract = _build_contract(root)
        raw = _canonical_bytes(contract)
        _write_once(root, CONTRACT_PATH, raw)
    return {
        "status": "OFFLINE_USER_ATTESTED_CONTRACT_MATERIALIZED_LIVE_CLOSED",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "dotenv_or_credential_observed": False,
        "execution_authorized": False,
    }


def build_user_credential_location_attestation(
    contract: UserAttestedNoCallPreflightContract,
    *,
    claim: Literal["openai-api-key-configured-in-repository-root-dotenv"],
    recorded_at: datetime,
) -> UserCredentialLocationAttestation:
    contract = UserAttestedNoCallPreflightContract.model_validate(contract.model_dump(mode="json"))
    _require(claim == ATTESTATION_CLAIM, "user attestation claim is not exact")
    body = {
        "schema_version": "preflight-user-credential-location-attestation-v2",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "claim": claim,
        "subject_names_hash": sha256_json(list(STATE_CHANGE_SUBJECTS)),
        "location_surface": DOTENV_SURFACE,
        "identity_assurance": IDENTITY_ASSURANCE,
        "external_receipt_present": False,
        "independent_verification_completed": False,
        "attestation_proves_credential_presence": False,
        "dotenv_read_or_stat_performed": False,
        "raw_credential_value_observed": False,
        "raw_credential_value_persisted": False,
        "recorded_at": _utc(recorded_at, label="user attestation recorded_at"),
    }
    content_hash = _semantic_hash(body)
    return UserCredentialLocationAttestation(
        **body,
        attestation_id=_derived_id("ncpattestation", content_hash),
        content_hash=content_hash,
    )


def bind_user_attested_state_change_evidence(
    contract: UserAttestedNoCallPreflightContract,
    attestation: UserCredentialLocationAttestation,
    *,
    recorded_at: datetime,
) -> UserAttestedStateChangeEvidence:
    contract = UserAttestedNoCallPreflightContract.model_validate(contract.model_dump(mode="json"))
    attestation = UserCredentialLocationAttestation.model_validate(
        attestation.model_dump(mode="json")
    )
    _require(attestation.contract_id == contract.contract_id, "attestation contract differs")
    _require(
        attestation.contract_content_hash == contract.content_hash,
        "attestation contract hash differs",
    )
    _require(recorded_at >= attestation.recorded_at, "state evidence predates attestation")
    body = {
        "schema_version": "preflight-state-change-evidence-v2",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "evidence_kind": StateChangeEvidenceKindV2.USER_ATTESTED_CREDENTIAL_LOCATION,
        "subject_names_hash": sha256_json(list(STATE_CHANGE_SUBJECTS)),
        "location_surface": DOTENV_SURFACE,
        "user_attestation_id": attestation.attestation_id,
        "user_attestation_content_hash": attestation.content_hash,
        "predecessor_terminal_file_sha256": contract.predecessor_terminal_file_sha256,
        "identity_assurance": IDENTITY_ASSURANCE,
        "external_receipt_present": False,
        "independent_verification_completed": False,
        "attestation_proves_credential_presence": False,
        "exact_preflight_still_required": True,
        "raw_credential_value_observed": False,
        "raw_credential_value_persisted": False,
        "source_or_contract_changed": True,
        "recorded_at": _utc(recorded_at, label="state evidence recorded_at"),
    }
    content_hash = _semantic_hash(body)
    return UserAttestedStateChangeEvidence(
        **body,
        evidence_id=_derived_id("ncpstate", content_hash),
        content_hash=content_hash,
    )


def build_user_exact_approval_receipt(
    contract: UserAttestedNoCallPreflightContract,
    evidence: UserAttestedStateChangeEvidence,
    *,
    recorded_at: datetime,
) -> UserExactApprovalReceipt:
    contract = UserAttestedNoCallPreflightContract.model_validate(contract.model_dump(mode="json"))
    evidence = UserAttestedStateChangeEvidence.model_validate(evidence.model_dump(mode="json"))
    _require(evidence.contract_id == contract.contract_id, "approval evidence contract differs")
    _require(
        evidence.contract_content_hash == contract.content_hash,
        "approval evidence contract hash differs",
    )
    _require(recorded_at >= evidence.recorded_at, "approval predates state evidence")
    body = {
        "schema_version": "preflight-user-exact-approval-receipt-v2",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "state_change_evidence_id": evidence.evidence_id,
        "state_change_evidence_content_hash": evidence.content_hash,
        "approved_scopes": APPROVED_SCOPES,
        "identity_assurance": IDENTITY_ASSURANCE,
        "attempt_limit": 1,
        "credential_value_in_approval": False,
        "credential_provisioning_authorized": False,
        "execution_hash_or_candidate_authorized": False,
        "cost_or_paid_execution_authorized": False,
        "provider_evaluator_agent_execution_authorized": False,
        "recorded_at": _utc(recorded_at, label="approval receipt recorded_at"),
    }
    content_hash = _semantic_hash(body)
    return UserExactApprovalReceipt(
        **body,
        receipt_id=_derived_id("ncpapprovalreceipt", content_hash),
        content_hash=content_hash,
    )


def bind_user_attested_approval(
    contract: UserAttestedNoCallPreflightContract,
    evidence: UserAttestedStateChangeEvidence,
    receipt: UserExactApprovalReceipt,
    *,
    recorded_at: datetime,
) -> UserAttestedApprovalBinding:
    contract = UserAttestedNoCallPreflightContract.model_validate(contract.model_dump(mode="json"))
    evidence = UserAttestedStateChangeEvidence.model_validate(evidence.model_dump(mode="json"))
    receipt = UserExactApprovalReceipt.model_validate(receipt.model_dump(mode="json"))
    _require(receipt.contract_id == contract.contract_id, "approval receipt contract differs")
    _require(
        receipt.state_change_evidence_id == evidence.evidence_id
        and receipt.state_change_evidence_content_hash == evidence.content_hash,
        "approval receipt does not bind exact state evidence",
    )
    _require(recorded_at >= receipt.recorded_at, "approval binding predates receipt")
    body = {
        "schema_version": "preflight-approval-binding-v2",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "state_change_evidence_id": evidence.evidence_id,
        "state_change_evidence_content_hash": evidence.content_hash,
        "user_approval_receipt_id": receipt.receipt_id,
        "user_approval_receipt_content_hash": receipt.content_hash,
        "approved_scopes": APPROVED_SCOPES,
        "identity_assurance": IDENTITY_ASSURANCE,
        "attempt_limit": 1,
        "credential_value_in_approval": False,
        "credential_provisioning_authorized": False,
        "execution_hash_or_candidate_authorized": False,
        "cost_or_paid_execution_authorized": False,
        "provider_evaluator_agent_execution_authorized": False,
        "recorded_at": _utc(recorded_at, label="approval binding recorded_at"),
    }
    content_hash = _semantic_hash(body)
    return UserAttestedApprovalBinding(
        **body,
        approval_id=_derived_id("ncpapproval", content_hash),
        content_hash=content_hash,
    )


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
        raise UserAttestedNoCallPreflightError("local Git source read failed") from exc
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
    _require(
        len(diff.splitlines()) == len(added),
        "v2 source commit contains non-addition changes",
    )
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
) -> UserAttestedSourceQualification:
    contract = load_user_attested_no_call_preflight_contract(repository=root)
    commit = _source_commit(root, source_commit)
    pairs = tuple(_committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(item[0] for item in pairs)
    contract_index = SOURCE_FILES.index(CONTRACT_PATH)
    _require(
        pairs[contract_index][1] == _canonical_bytes(contract),
        "committed v2 contract differs from validated contract",
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
        "contract_file": files[contract_index].model_dump(mode="json"),
        "predecessor_contract_id": contract.predecessor_contract_id,
        "predecessor_contract_content_hash": contract.predecessor_contract_content_hash,
        "authority": UserAttestedQualificationAuthority().model_dump(mode="json"),
        "next_gate": "user-attestation-state-evidence-then-exact-approval",
    }
    return UserAttestedSourceQualification(**body, content_hash=_semantic_hash(body))


def validate_user_attested_source_qualification(
    *, repository: str | Path | None = None
) -> dict[str, Any]:
    root = _repo_root(repository)
    raw = _read_bytes(root, QUALIFICATION_PATH)
    try:
        value = UserAttestedSourceQualification.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise UserAttestedNoCallPreflightError("v2 source qualification is invalid") from exc
    _require(raw == _canonical_bytes(value), "v2 source qualification bytes are not canonical")
    expected = _build_source_qualification(
        root,
        source_commit=value.source_commit.commit,
        recorded_at=value.recorded_at,
    )
    _require(value == expected, "v2 source qualification has drifted")
    return {
        "status": value.status,
        "qualification_id": value.qualification_id,
        "source_commit": value.source_commit.commit,
        "source_tree": value.source_commit.tree,
        "contract_version": value.contract_version,
        "contract_id": value.contract_id,
        "contract_content_hash": value.contract_content_hash,
        "source_qualification_hash": value.content_hash,
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "dotenv_or_credential_observations_made": 0,
        "execution_authorized": False,
    }


def run_user_attested_source_qualification(
    *,
    source_commit: str = "HEAD",
    repository: str | Path | None = None,
) -> dict[str, Any]:
    root = _repo_root(repository)
    selected = _logical_path(root, QUALIFICATION_PATH, must_exist=False)
    if selected.exists():
        return validate_user_attested_source_qualification(repository=root)
    value = _build_source_qualification(
        root,
        source_commit=source_commit,
        recorded_at=datetime.now(UTC),
    )
    _write_once(root, QUALIFICATION_PATH, _canonical_bytes(value))
    return validate_user_attested_source_qualification(repository=root)


def record_user_attested_state_change(
    *,
    claim: Literal["openai-api-key-configured-in-repository-root-dotenv"],
    recorded_at: datetime,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Record the user's claim only; do not inspect the claimed file or value."""

    root = _repo_root(repository)
    validate_user_attested_source_qualification(repository=root)
    _require(
        not _logical_path(root, USER_ATTESTATION_PATH, must_exist=False).exists(),
        "user attestation already exists",
    )
    _require(
        not _logical_path(root, STATE_EVIDENCE_PATH, must_exist=False).exists(),
        "state evidence already exists",
    )
    contract = load_user_attested_no_call_preflight_contract(repository=root)
    attestation = build_user_credential_location_attestation(
        contract,
        claim=claim,
        recorded_at=recorded_at,
    )
    evidence = bind_user_attested_state_change_evidence(
        contract,
        attestation,
        recorded_at=recorded_at,
    )
    _write_once(root, USER_ATTESTATION_PATH, _canonical_bytes(attestation))
    try:
        _write_once(root, STATE_EVIDENCE_PATH, _canonical_bytes(evidence))
    except Exception:
        # A partial append-only pair must be preserved and reported, never deleted or overwritten.
        raise
    return validate_user_attested_state_change(repository=root)


def validate_user_attested_state_change(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    contract = load_user_attested_no_call_preflight_contract(repository=root)
    attestation_raw = _read_bytes(root, USER_ATTESTATION_PATH)
    evidence_raw = _read_bytes(root, STATE_EVIDENCE_PATH)
    try:
        attestation = UserCredentialLocationAttestation.model_validate_json(attestation_raw)
        evidence = UserAttestedStateChangeEvidence.model_validate_json(evidence_raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise UserAttestedNoCallPreflightError("user-attested state artifact is invalid") from exc
    _require(
        attestation_raw == _canonical_bytes(attestation),
        "user attestation bytes are not canonical",
    )
    _require(evidence_raw == _canonical_bytes(evidence), "state evidence bytes are not canonical")
    expected = bind_user_attested_state_change_evidence(
        contract,
        attestation,
        recorded_at=evidence.recorded_at,
    )
    _require(evidence == expected, "state evidence does not bind exact user attestation")
    return {
        "status": "USER_ATTESTED_STATE_CHANGE_RECORDED_EXACT_APPROVAL_REQUIRED",
        "contract_id": contract.contract_id,
        "attestation_id": attestation.attestation_id,
        "attestation_content_hash": attestation.content_hash,
        "state_change_evidence_id": evidence.evidence_id,
        "state_change_evidence_content_hash": evidence.content_hash,
        "identity_assurance": IDENTITY_ASSURANCE,
        "external_receipt_present": False,
        "credential_presence_verified": False,
        "dotenv_read_or_stat_performed": False,
        "raw_credential_value_observed": False,
        "exact_approval_required": True,
    }


def record_user_exact_approval(
    *,
    exact_state_change_evidence_id: str,
    recorded_at: datetime,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Record a later exact user approval; this still performs no observation."""

    root = _repo_root(repository)
    _require(
        not _logical_path(root, APPROVAL_RECEIPT_PATH, must_exist=False).exists(),
        "exact approval receipt already exists",
    )
    _require(
        not _logical_path(root, APPROVAL_BINDING_PATH, must_exist=False).exists(),
        "exact approval binding already exists",
    )
    contract = load_user_attested_no_call_preflight_contract(repository=root)
    evidence = UserAttestedStateChangeEvidence.model_validate_json(
        _read_bytes(root, STATE_EVIDENCE_PATH)
    )
    _require(
        exact_state_change_evidence_id == evidence.evidence_id,
        "approval did not cite exact state evidence",
    )
    receipt = build_user_exact_approval_receipt(
        contract,
        evidence,
        recorded_at=recorded_at,
    )
    approval = bind_user_attested_approval(
        contract,
        evidence,
        receipt,
        recorded_at=recorded_at,
    )
    _write_once(root, APPROVAL_RECEIPT_PATH, _canonical_bytes(receipt))
    try:
        _write_once(root, APPROVAL_BINDING_PATH, _canonical_bytes(approval))
    except Exception:
        raise
    return validate_user_exact_approval(repository=root)


def validate_user_exact_approval(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    contract = load_user_attested_no_call_preflight_contract(repository=root)
    evidence = UserAttestedStateChangeEvidence.model_validate_json(
        _read_bytes(root, STATE_EVIDENCE_PATH)
    )
    receipt_raw = _read_bytes(root, APPROVAL_RECEIPT_PATH)
    approval_raw = _read_bytes(root, APPROVAL_BINDING_PATH)
    try:
        receipt = UserExactApprovalReceipt.model_validate_json(receipt_raw)
        approval = UserAttestedApprovalBinding.model_validate_json(approval_raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise UserAttestedNoCallPreflightError("exact approval artifact is invalid") from exc
    _require(receipt_raw == _canonical_bytes(receipt), "approval receipt bytes are not canonical")
    _require(approval_raw == _canonical_bytes(approval), "approval binding bytes are not canonical")
    expected = bind_user_attested_approval(
        contract,
        evidence,
        receipt,
        recorded_at=approval.recorded_at,
    )
    _require(approval == expected, "approval does not bind exact receipt and state evidence")
    return {
        "status": "USER_EXACT_APPROVAL_RECORDED_ATTEMPT_NOT_STARTED",
        "contract_id": contract.contract_id,
        "state_change_evidence_id": evidence.evidence_id,
        "approval_receipt_id": receipt.receipt_id,
        "approval_id": approval.approval_id,
        "approval_content_hash": approval.content_hash,
        "identity_assurance": IDENTITY_ASSURANCE,
        "attempt_limit": 1,
        "dotenv_or_credential_observations_made": 0,
        "attempt_started": False,
        "paid_execution_authorized": False,
    }


def validate_no_secret_material(raw_values: Sequence[bytes]) -> None:
    """Reject common credential material in generated public artifacts."""

    for raw in raw_values:
        lowered = raw.lower()
        _require(b"sk-" not in lowered, "generated artifact contains a credential-like prefix")
        _require(b'"credential_value"' not in lowered, "generated artifact contains a value field")
