"""Versioned, offline-only contract for a future no-call preflight.

This module defines structural values and a commit-bound source qualification.
It intentionally has no function that observes Docker, the SDK, credentials, or
the network, and it never persists a preflight attempt.  Future runtime code
must supply independently trusted state-change, approval, and durable-ledger
bindings before an attempt identity can be derived.
"""

from __future__ import annotations

import json
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
from patchloop.evals import evaluator_v2_source_qualification as evaluator_q
from patchloop.runtime import repository_root
from patchloop.util import safe_relative_path, sha256_bytes, sha256_json

CONTRACT_SCHEMA_VERSION = "versioned-no-call-preflight-contract-v1"
CONTRACT_VERSION = "ac-evaluator-v2-no-call-preflight-v1"
CONTRACT_PATH = Path("experiments/evaluator-v2-no-call-preflight-v1.contract.json")

QUALIFICATION_SCHEMA_VERSION = "versioned-no-call-preflight-source-qualification-v1"
QUALIFICATION_ID = "ac-evaluator-v2-no-call-preflight-source-20260811-r1"
QUALIFICATION_STATUS = "OFFLINE_CONTRACT_SOURCE_QUALIFIED_LIVE_CLOSED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-no-call-preflight-v1-source-qualification.json"
)

D141_TERMINAL_PATH = Path("reports/live-pilot/artifacts/d141-sdk-no-call-successor-terminal.json")
D142_GATE_PATH = Path(
    "reports/live-pilot/artifacts/d142-d141-sdk-blocked-no-call-successor-offline-source-gate.json"
)
D141_TERMINAL_STATUS = "D141_SDK_NO_CALL_SUCCESSOR_BLOCKED_TRANSITION_COMMIT_REQUIRED"
D141_TERMINAL_ID = "d141sdk_c96ceb8eb274560b89e3688402a0c3576d6f09536c32d611600ac1386d4613ef"
D142_GATE_ID = "d142_9515aeb4c7289fa26987ec605917c395e54b27d076cd226c266acd2a3cb82914"
D142_GATE_STATUS = (
    "D142_D141_SDK_BLOCKED_NO_CALL_SUCCESSOR_OFFLINE_SOURCE_QUALIFIED_FRESH_ACTIVATION_REQUIRED"
)
D142_SOURCE_COMMIT = "1370cf43c08cefb550b158a5d4172a60ac172470"
EVALUATOR_V2_BOUNDARY_COMMIT = "04ee027171d9d4891c4f481d2ccfb277e7a4a9e6"

SOURCE_PATHS = tuple(
    sorted(
        (
            Path("pyproject.toml"),
            Path("uv.lock"),
            Path("patchloop/contracts.py"),
            Path("patchloop/errors.py"),
            Path("patchloop/runtime.py"),
            Path("patchloop/util.py"),
            Path("patchloop/evals/evaluator_v2_source_qualification.py"),
            Path("patchloop/evals/versioned_no_call_preflight.py"),
            evaluator_q.OUTPUT_PATH,
            D141_TERMINAL_PATH,
            D142_GATE_PATH,
            CONTRACT_PATH,
        ),
        key=lambda item: item.as_posix(),
    )
)
VALIDATION_PATHS = (
    Path("scripts/build_versioned_no_call_preflight_contract.py"),
    Path("tests/test_versioned_no_call_preflight_contract.py"),
)
SOURCE_COMMIT_ADDED_PATHS = tuple(
    sorted(
        (
            CONTRACT_PATH.as_posix(),
            "patchloop/evals/versioned_no_call_preflight.py",
            "scripts/build_versioned_no_call_preflight_contract.py",
            "tests/test_versioned_no_call_preflight_contract.py",
        )
    )
)

STATE_CHANGE_SUBJECTS = ("OPENAI_API_KEY",)
OBSERVATION_PHASES = ("docker_metadata", "sdk_no_call")
DOCKER_METADATA_QUERIES = ("engine_version", "qualified_image_identity")
SDK_ENVIRONMENT_NAMES = ("OPENAI_API_KEY", "PYTHONHOME", "PYTHONPATH")
ATTEMPT_APPROVED_SCOPES = (
    "docker-metadata-read-only",
    "environment-membership-only",
    "isolated-sdk-import-and-no-transport-probe",
)


class VersionedNoCallPreflightError(ContractError):
    """Raised when a preflight contract or qualification fails closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VersionedNoCallPreflightError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = repository_root() if repository is None else Path(repository)
    return selected.resolve(strict=True)


def _logical_path(root: Path, relative: Path, *, must_exist: bool) -> Path:
    safe = safe_relative_path(relative.as_posix(), field_name="preflight path")
    selected = root.joinpath(*Path(safe).parts)
    resolved = selected.resolve(strict=must_exist)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise VersionedNoCallPreflightError("preflight path escaped repository") from exc
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


def _utc(value: datetime, *, label: str) -> datetime:
    _require(value.tzinfo is not None, f"{label} must be timezone-aware")
    _require(value.utcoffset() == UTC.utcoffset(value), f"{label} must be UTC")
    return value


def _derived_id(prefix: str, content_hash: str) -> str:
    return f"{prefix}_{content_hash.removeprefix('sha256:')}"


class StateChangeEvidenceKind(StrEnum):
    CREDENTIAL_PROVISIONING_COMPLETED = "credential_provisioning_completed_v1"


class PreflightTerminalOutcome(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"
    ERROR = "error"


class PreflightTerminalReason(StrEnum):
    CREDENTIAL_MEMBERSHIP_MISSING = "credential_membership_missing"
    PYTHON_ENVIRONMENT_NOT_CLEAN = "python_environment_not_clean"
    SDK_IMPORT_UNAVAILABLE = "sdk_import_unavailable"
    SDK_NO_TRANSPORT_PROBE_FAILED = "sdk_no_transport_probe_failed"
    DOCKER_ENGINE_UNAVAILABLE = "docker_engine_unavailable"
    QUALIFIED_IMAGE_IDENTITY_MISSING = "qualified_image_identity_missing"
    CHECKER_ERROR = "checker_error"
    INTEGRITY_ERROR = "integrity_error"
    POST_MARKER_FAILURE = "post_marker_failure"


class HistoricalArtifactBinding(FrozenStrictModel):
    path: str
    schema_version: str = Field(min_length=1, max_length=160)
    identity: str = Field(min_length=1, max_length=96)
    semantic_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    file_bytes: int = Field(ge=1)
    status: str = Field(min_length=1, max_length=160)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return safe_relative_path(value, field_name="historical artifact path")


class PreflightStateChangeRule(FrozenStrictModel):
    schema_version: Literal["preflight-state-change-rule-v1"] = "preflight-state-change-rule-v1"
    allowed_kind: Literal[StateChangeEvidenceKind.CREDENTIAL_PROVISIONING_COMPLETED] = (
        StateChangeEvidenceKind.CREDENTIAL_PROVISIONING_COMPLETED
    )
    exact_subject_names: tuple[str, ...] = STATE_CHANGE_SUBJECTS
    requires_user_controlled_provisioning_receipt: Literal[True] = True
    requires_independent_trust_anchor: Literal[True] = True
    raw_credential_value_allowed: Literal[False] = False
    unchanged_blocker_is_state_change: Literal[False] = False
    source_or_contract_change_requires_version_bump: Literal[True] = True

    @model_validator(mode="after")
    def validate_exact_rule(self) -> PreflightStateChangeRule:
        if self.exact_subject_names != STATE_CHANGE_SUBJECTS:
            raise ValueError("state-change subjects drifted")
        return self


class PreflightObservationContract(FrozenStrictModel):
    schema_version: Literal["preflight-observation-contract-v1"] = (
        "preflight-observation-contract-v1"
    )
    phases: tuple[str, ...] = OBSERVATION_PHASES
    docker_metadata_queries: tuple[str, ...] = DOCKER_METADATA_QUERIES
    sdk_environment_names: tuple[str, ...] = SDK_ENVIRONMENT_NAMES
    environment_membership_check_limit: Literal[3] = 3
    environment_value_read_limit: Literal[0] = 0
    dotenv_read_limit: Literal[0] = 0
    docker_container_start_limit: Literal[0] = 0
    sdk_isolated_child_start_limit: Literal[1] = 1
    transport_dispatch_limit: Literal[0] = 0
    provider_evaluator_agent_call_limit: Literal[0] = 0
    network_call_limit: Literal[0] = 0
    credential_mutation_limit: Literal[0] = 0
    observation_result_values_allowed: Literal[False] = False

    @model_validator(mode="after")
    def validate_exact_observation(self) -> PreflightObservationContract:
        if self.phases != OBSERVATION_PHASES:
            raise ValueError("preflight observation phases drifted")
        if self.docker_metadata_queries != DOCKER_METADATA_QUERIES:
            raise ValueError("Docker metadata queries drifted")
        if self.sdk_environment_names != SDK_ENVIRONMENT_NAMES:
            raise ValueError("SDK environment names drifted")
        return self


class PreflightTransitionPolicy(FrozenStrictModel):
    schema_version: Literal["preflight-transition-policy-v1"] = "preflight-transition-policy-v1"
    exact_sequence: tuple[str, ...] = (
        "intent_recorded",
        "action_started",
        "ready_or_blocked_or_error_terminal",
    )
    state_change_evidence_use_limit: Literal[1] = 1
    approval_use_limit: Literal[1] = 1
    attempt_number: Literal[1] = 1
    marker_before_first_observation: Literal[True] = True
    terminal_typed_observation_required: Literal[True] = True
    intent_creation_reserves_evidence: Literal[True] = True
    post_marker_failure_consumes_attempt: Literal[True] = True
    terminal_is_append_only: Literal[True] = True
    retry_allowed: Literal[False] = False
    resume_allowed: Literal[False] = False
    overwrite_allowed: Literal[False] = False
    repair_or_backfill_allowed: Literal[False] = False
    blocked_authorizes_successor: Literal[False] = False


class PreflightSourceAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    commit_source_qualification_authorized: Literal[True] = True
    state_change_evidence_creation_authorized: Literal[False] = False
    credential_provisioning_authorized: Literal[False] = False
    external_preflight_attempt_authorized: Literal[False] = False
    docker_or_sdk_observation_authorized: Literal[False] = False
    execution_hash_or_candidate_authorized: Literal[False] = False
    pricing_or_cost_reservation_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    memory_retrieval_or_injection_authorized: Literal[False] = False
    automatic_retry_replacement_or_resume_authorized: Literal[False] = False
    memory_benefit_claim_authorized: Literal[False] = False


class VersionedNoCallPreflightContract(FrozenStrictModel):
    schema_version: Literal["versioned-no-call-preflight-contract-v1"] = CONTRACT_SCHEMA_VERSION
    contract_version: Literal["ac-evaluator-v2-no-call-preflight-v1"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    evaluator_v2_source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    successor_suite_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_tuple_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    d141_blocked_terminal: HistoricalArtifactBinding
    d142_deferred_gate: HistoricalArtifactBinding
    d142_source_commit: Literal["1370cf43c08cefb550b158a5d4172a60ac172470"] = D142_SOURCE_COMMIT
    d142_is_audit_only: Literal[True] = True
    state_change_rule: PreflightStateChangeRule
    observation_contract: PreflightObservationContract
    transition_policy: PreflightTransitionPolicy
    source_authority: PreflightSourceAuthority
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> VersionedNoCallPreflightContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected_hash = sha256_json(body)
        if self.content_hash != expected_hash:
            raise ValueError("preflight contract content hash mismatch")
        if self.contract_id != _derived_id("ncpcontract", expected_hash):
            raise ValueError("preflight contract id mismatch")
        if self.d141_blocked_terminal.status != D141_TERMINAL_STATUS:
            raise ValueError("D-141 terminal status mismatch")
        if self.d141_blocked_terminal.identity != D141_TERMINAL_ID:
            raise ValueError("D-141 terminal identity mismatch")
        if self.d142_deferred_gate.identity != D142_GATE_ID:
            raise ValueError("D-142 gate identity mismatch")
        if self.d142_deferred_gate.status != D142_GATE_STATUS:
            raise ValueError("D-142 gate status mismatch")
        return self


class PreflightStateChangeEvidence(FrozenStrictModel):
    schema_version: Literal["preflight-state-change-evidence-v1"] = (
        "preflight-state-change-evidence-v1"
    )
    evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    contract_version: Literal["ac-evaluator-v2-no-call-preflight-v1"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_kind: Literal[StateChangeEvidenceKind.CREDENTIAL_PROVISIONING_COMPLETED] = (
        StateChangeEvidenceKind.CREDENTIAL_PROVISIONING_COMPLETED
    )
    subject_names_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_terminal_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    provisioning_receipt_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    independent_trust_anchor_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    recorded_at: datetime
    raw_credential_value_observed: Literal[False] = False
    raw_credential_value_persisted: Literal[False] = False
    source_or_contract_changed: Literal[False] = False
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("state-change evidence recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> PreflightStateChangeEvidence:
        body = self.model_dump(mode="json", exclude={"evidence_id", "content_hash"})
        expected_hash = sha256_json(body)
        if self.content_hash != expected_hash:
            raise ValueError("state-change evidence content hash mismatch")
        if self.evidence_id != _derived_id("ncpstate", expected_hash):
            raise ValueError("state-change evidence id mismatch")
        if self.subject_names_hash != sha256_json(list(STATE_CHANGE_SUBJECTS)):
            raise ValueError("state-change evidence subjects mismatch")
        return self


class PreflightApprovalBinding(FrozenStrictModel):
    schema_version: Literal["preflight-approval-binding-v1"] = "preflight-approval-binding-v1"
    approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    contract_version: Literal["ac-evaluator-v2-no-call-preflight-v1"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_change_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_change_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_scopes: tuple[str, ...] = ATTEMPT_APPROVED_SCOPES
    authenticated_approval_receipt_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    recorded_at: datetime
    attempt_limit: Literal[1] = 1
    credential_value_in_approval: Literal[False] = False
    credential_provisioning_authorized: Literal[False] = False
    execution_hash_or_candidate_authorized: Literal[False] = False
    cost_or_paid_execution_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("approval recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> PreflightApprovalBinding:
        if self.approved_scopes != ATTEMPT_APPROVED_SCOPES:
            raise ValueError("approval scope drifted")
        body = self.model_dump(mode="json", exclude={"approval_id", "content_hash"})
        expected_hash = sha256_json(body)
        if self.content_hash != expected_hash:
            raise ValueError("approval content hash mismatch")
        if self.approval_id != _derived_id("ncpapproval", expected_hash):
            raise ValueError("approval id mismatch")
        return self


class PreflightConsumptionSnapshot(FrozenStrictModel):
    schema_version: Literal["preflight-consumption-snapshot-v1"] = (
        "preflight-consumption-snapshot-v1"
    )
    ledger_root_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    through_sequence: int = Field(ge=0)
    consumed_state_change_evidence_ids: tuple[str, ...] = ()
    consumed_approval_ids: tuple[str, ...] = ()
    reserved_or_terminal_attempt_ids: tuple[str, ...] = ()
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_snapshot(self) -> PreflightConsumptionSnapshot:
        for label, values, prefix in (
            (
                "state-change evidence",
                self.consumed_state_change_evidence_ids,
                "ncpstate_",
            ),
            ("approval", self.consumed_approval_ids, "ncpapproval_"),
            ("attempt", self.reserved_or_terminal_attempt_ids, "ncpattempt_"),
        ):
            if values != tuple(sorted(values)) or len(values) != len(set(values)):
                raise ValueError(f"{label} consumption set is not canonical")
            if any(
                len(value) != len(prefix) + 64 or not value.startswith(prefix) for value in values
            ):
                raise ValueError(f"{label} consumption identity is invalid")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != sha256_json(body):
            raise ValueError("consumption snapshot content hash mismatch")
        return self


class PreflightAttemptAuthority(FrozenStrictModel):
    docker_metadata_read_authorized: Literal[True] = True
    environment_membership_observation_authorized: Literal[True] = True
    isolated_sdk_no_transport_probe_authorized: Literal[True] = True
    credential_value_read_authorized: Literal[False] = False
    credential_mutation_or_provisioning_authorized: Literal[False] = False
    transport_or_network_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    execution_hash_or_candidate_authorized: Literal[False] = False
    pricing_or_cost_reservation_authorized: Literal[False] = False
    memory_retrieval_or_injection_authorized: Literal[False] = False


class PreflightAttemptIntent(FrozenStrictModel):
    schema_version: Literal["preflight-attempt-intent-v1"] = "preflight-attempt-intent-v1"
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    contract_version: Literal["ac-evaluator-v2-no-call-preflight-v1"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_change_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_change_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    approval_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    consumption_snapshot_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    created_at: datetime
    attempt_number: Literal[1] = 1
    state: Literal["intent_recorded"] = "intent_recorded"
    one_use: Literal[True] = True
    retry_or_resume_allowed: Literal[False] = False
    authority: PreflightAttemptAuthority
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("attempt created_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> PreflightAttemptIntent:
        body = self.model_dump(mode="json", exclude={"attempt_id", "content_hash"})
        expected_hash = sha256_json(body)
        if self.content_hash != expected_hash:
            raise ValueError("attempt content hash mismatch")
        if self.attempt_id != _derived_id("ncpattempt", expected_hash):
            raise ValueError("attempt id mismatch")
        return self


class PreflightActivitySummary(FrozenStrictModel):
    docker_metadata_query_count: int = Field(ge=0, le=2)
    environment_membership_check_count: int = Field(ge=0, le=3)
    environment_value_read_count: Literal[0] = 0
    dotenv_read_count: Literal[0] = 0
    docker_container_start_count: Literal[0] = 0
    sdk_isolated_child_start_count: int = Field(ge=0, le=1)
    credential_value_forward_count: Literal[0] = 0
    credential_mutation_count: Literal[0] = 0
    transport_dispatch_count: Literal[0] = 0
    network_call_count: Literal[0] = 0
    provider_evaluator_agent_call_count: Literal[0] = 0

    @field_validator("*", mode="before")
    @classmethod
    def validate_exact_integer(cls, value: Any) -> Any:
        if type(value) is not int:
            raise ValueError("preflight activity values must be exact integers")
        return value


class PreflightObservationResult(FrozenStrictModel):
    docker_engine_available: bool | None = None
    qualified_image_identity_matched: bool | None = None
    openai_api_key_present: bool | None = None
    pythonhome_absent: bool | None = None
    pythonpath_absent: bool | None = None
    sdk_import_succeeded: bool | None = None
    official_api_base_url_default: bool | None = None
    sdk_transport_retry_zero: bool | None = None

    @field_validator("*", mode="before")
    @classmethod
    def validate_exact_boolean(cls, value: Any) -> Any:
        if value is not None and type(value) is not bool:
            raise ValueError("preflight observations must be exact booleans")
        return value


class PreflightTransition(FrozenStrictModel):
    schema_version: Literal["preflight-transition-v1"] = "preflight-transition-v1"
    transition_id: str = Field(pattern=r"^ncptransition_[0-9a-f]{64}$")
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    sequence: Literal[1, 2]
    previous_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    transition_kind: Literal["action_started", "terminal"]
    recorded_at: datetime
    terminal_outcome: PreflightTerminalOutcome | None = None
    terminal_reason: PreflightTerminalReason | None = None
    activity: PreflightActivitySummary | None = None
    observation: PreflightObservationResult | None = None
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("transition recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_transition(self) -> PreflightTransition:
        if self.transition_kind == "action_started":
            if self.sequence != 1:
                raise ValueError("action-started transition must be sequence 1")
            if any(
                value is not None
                for value in (
                    self.terminal_outcome,
                    self.terminal_reason,
                    self.activity,
                    self.observation,
                )
            ):
                raise ValueError("action-started transition contains terminal data")
        else:
            if (
                self.sequence != 2
                or self.terminal_outcome is None
                or self.activity is None
                or self.observation is None
            ):
                raise ValueError("terminal transition is incomplete")
            if self.terminal_outcome == PreflightTerminalOutcome.READY:
                if self.terminal_reason is not None:
                    raise ValueError("READY terminal cannot have a failure reason")
                if (
                    self.activity.docker_metadata_query_count != 2
                    or self.activity.environment_membership_check_count != 3
                    or self.activity.sdk_isolated_child_start_count != 1
                ):
                    raise ValueError("READY terminal lacks complete bounded observations")
                if any(
                    value is not True
                    for value in (
                        self.observation.docker_engine_available,
                        self.observation.qualified_image_identity_matched,
                        self.observation.openai_api_key_present,
                        self.observation.pythonhome_absent,
                        self.observation.pythonpath_absent,
                        self.observation.sdk_import_succeeded,
                        self.observation.official_api_base_url_default,
                        self.observation.sdk_transport_retry_zero,
                    )
                ):
                    raise ValueError("READY terminal lacks exact positive observations")
            elif self.terminal_reason is None:
                raise ValueError("non-READY terminal requires a reason")
            elif (
                self.terminal_outcome == PreflightTerminalOutcome.BLOCKED
                and self.terminal_reason
                in {
                    PreflightTerminalReason.CHECKER_ERROR,
                    PreflightTerminalReason.INTEGRITY_ERROR,
                    PreflightTerminalReason.POST_MARKER_FAILURE,
                }
            ):
                raise ValueError("BLOCKED terminal has an ERROR-only reason")
            elif (
                self.terminal_outcome == PreflightTerminalOutcome.ERROR
                and self.terminal_reason
                not in {
                    PreflightTerminalReason.CHECKER_ERROR,
                    PreflightTerminalReason.INTEGRITY_ERROR,
                    PreflightTerminalReason.POST_MARKER_FAILURE,
                }
            ):
                raise ValueError("ERROR terminal has a blocker reason")
            elif self.terminal_outcome == PreflightTerminalOutcome.BLOCKED:
                blocker_matches = {
                    PreflightTerminalReason.CREDENTIAL_MEMBERSHIP_MISSING: (
                        self.observation.openai_api_key_present is False
                    ),
                    PreflightTerminalReason.PYTHON_ENVIRONMENT_NOT_CLEAN: (
                        self.observation.pythonhome_absent is False
                        or self.observation.pythonpath_absent is False
                    ),
                    PreflightTerminalReason.SDK_IMPORT_UNAVAILABLE: (
                        self.observation.sdk_import_succeeded is False
                    ),
                    PreflightTerminalReason.SDK_NO_TRANSPORT_PROBE_FAILED: (
                        self.observation.official_api_base_url_default is False
                        or self.observation.sdk_transport_retry_zero is False
                    ),
                    PreflightTerminalReason.DOCKER_ENGINE_UNAVAILABLE: (
                        self.observation.docker_engine_available is False
                    ),
                    PreflightTerminalReason.QUALIFIED_IMAGE_IDENTITY_MISSING: (
                        self.observation.qualified_image_identity_matched is False
                    ),
                }
                if not blocker_matches.get(self.terminal_reason, False):
                    raise ValueError("BLOCKED terminal reason does not match observation")
        body = self.model_dump(mode="json", exclude={"transition_id", "content_hash"})
        expected_hash = sha256_json(body)
        if self.content_hash != expected_hash:
            raise ValueError("transition content hash mismatch")
        if self.transition_id != _derived_id("ncptransition", expected_hash):
            raise ValueError("transition id mismatch")
        return self


class CommittedFileBinding(FrozenStrictModel):
    path: str
    blob_oid: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    file_bytes: int = Field(ge=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return safe_relative_path(value, field_name="committed source path")


class SourceCommitBinding(FrozenStrictModel):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    parents: tuple[str, ...]
    added_paths: tuple[str, ...]

    @field_validator("parents")
    @classmethod
    def validate_parents(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(
            len(value) != 40 or any(char not in "0123456789abcdef" for char in value)
            for value in values
        ):
            raise ValueError("source commit parent is invalid")
        return values

    @field_validator("added_paths")
    @classmethod
    def validate_added_paths(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if values != SOURCE_COMMIT_ADDED_PATHS:
            raise ValueError("source commit additions drifted")
        return values


class PreflightQualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    contract_source_qualified: Literal[True] = True
    state_change_evidence_created: Literal[False] = False
    approval_created_or_inferred: Literal[False] = False
    attempt_or_transition_created: Literal[False] = False
    credential_or_environment_observation_count: Literal[0] = 0
    credential_value_observation_or_mutation_count: Literal[0] = 0
    docker_or_sdk_observation_count: Literal[0] = 0
    network_provider_evaluator_agent_call_count: Literal[0] = 0
    execution_hash_or_candidate_created: Literal[False] = False
    cost_reserved_or_spent_usd: Literal["0"] = "0"


class VersionedNoCallPreflightSourceQualification(FrozenStrictModel):
    schema_version: Literal["versioned-no-call-preflight-source-qualification-v1"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal["ac-evaluator-v2-no-call-preflight-source-20260811-r1"] = (
        QUALIFICATION_ID
    )
    status: Literal["OFFLINE_CONTRACT_SOURCE_QUALIFIED_LIVE_CLOSED"] = QUALIFICATION_STATUS
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[CommittedFileBinding, ...]
    validation_files: tuple[CommittedFileBinding, ...]
    contract_version: Literal["ac-evaluator-v2-no-call-preflight-v1"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    contract_file: CommittedFileBinding
    evaluator_v2_source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    successor_suite_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_tuple_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authority: PreflightQualificationAuthority
    next_gate: Literal["separately-approved-no-call-preflight-attempt"] = (
        "separately-approved-no-call-preflight-attempt"
    )
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("qualification recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_qualification(self) -> VersionedNoCallPreflightSourceQualification:
        expected_source = tuple(path.as_posix() for path in SOURCE_PATHS)
        expected_validation = tuple(path.as_posix() for path in VALIDATION_PATHS)
        if tuple(item.path for item in self.source_files) != expected_source:
            raise ValueError("qualified source inventory drifted")
        if tuple(item.path for item in self.validation_files) != expected_validation:
            raise ValueError("qualified validation inventory drifted")
        if self.contract_file != next(
            (item for item in self.source_files if item.path == CONTRACT_PATH.as_posix()),
            None,
        ):
            raise ValueError("contract file is outside the source inventory")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != sha256_json(body):
            raise ValueError("preflight source qualification content hash mismatch")
        return self


def _historical_binding(
    root: Path,
    path: Path,
    *,
    identity_key: Literal["artifact_id", "gate_id"],
) -> HistoricalArtifactBinding:
    raw = _read_bytes(root, path)
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise VersionedNoCallPreflightError("historical preflight artifact is invalid") from exc
    _require(isinstance(payload, dict), "historical preflight artifact is not an object")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), "historical preflight artifact lacks semantic body")
    return HistoricalArtifactBinding(
        path=path.as_posix(),
        schema_version=payload.get("schema_version"),
        identity=payload.get(identity_key),
        semantic_body_hash=payload.get("semantic_body_hash"),
        file_sha256=sha256_bytes(raw),
        file_bytes=len(raw),
        status=body.get("status"),
    )


def _build_contract(root: Path) -> VersionedNoCallPreflightContract:
    summary = evaluator_q.validate_evaluator_v2_ac_source_qualification(repository=root)
    evaluator_payload = evaluator_q.EvaluatorV2ACSourceQualification.model_validate_json(
        _read_bytes(root, evaluator_q.OUTPUT_PATH)
    )
    d141 = _historical_binding(root, D141_TERMINAL_PATH, identity_key="artifact_id")
    d142 = _historical_binding(root, D142_GATE_PATH, identity_key="gate_id")
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "evaluator_v2_source_qualification_hash": summary["source_qualification_hash"],
        "evaluator_source_hash": summary["evaluator_source_hash"],
        "successor_suite_hash": summary["successor_suite_hash"],
        "runtime_tuple_hash": evaluator_payload.successor_suite.runtime_tuple_hash,
        "d141_blocked_terminal": d141.model_dump(mode="json"),
        "d142_deferred_gate": d142.model_dump(mode="json"),
        "d142_source_commit": D142_SOURCE_COMMIT,
        "d142_is_audit_only": True,
        "state_change_rule": PreflightStateChangeRule().model_dump(mode="json"),
        "observation_contract": PreflightObservationContract().model_dump(mode="json"),
        "transition_policy": PreflightTransitionPolicy().model_dump(mode="json"),
        "source_authority": PreflightSourceAuthority().model_dump(mode="json"),
    }
    content_hash = sha256_json(body)
    return VersionedNoCallPreflightContract(
        **body,
        contract_id=_derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def _contract_bytes(contract: VersionedNoCallPreflightContract) -> bytes:
    return (contract.model_dump_json(indent=2) + "\n").encode("utf-8")


def load_versioned_no_call_preflight_contract(
    *, repository: str | Path | None = None
) -> VersionedNoCallPreflightContract:
    root = _repo_root(repository)
    raw = _read_bytes(root, CONTRACT_PATH)
    try:
        contract = VersionedNoCallPreflightContract.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise VersionedNoCallPreflightError("preflight contract artifact is invalid") from exc
    _require(raw == _contract_bytes(contract), "preflight contract bytes are not canonical")
    _require(contract == _build_contract(root), "preflight contract has drifted")
    return contract


def materialize_versioned_no_call_preflight_contract(
    *, repository: str | Path | None = None
) -> dict[str, Any]:
    """Create the deterministic contract once, or validate its exact bytes."""

    root = _repo_root(repository)
    selected = _logical_path(root, CONTRACT_PATH, must_exist=False)
    if selected.exists():
        contract = load_versioned_no_call_preflight_contract(repository=root)
        raw = _read_bytes(root, CONTRACT_PATH)
    else:
        contract = _build_contract(root)
        raw = _contract_bytes(contract)
        selected.parent.mkdir(parents=True, exist_ok=True)
        try:
            with selected.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            raise VersionedNoCallPreflightError(
                "preflight contract cannot be materialized"
            ) from exc
        _require(_read_bytes(root, CONTRACT_PATH) == raw, "preflight contract reread differs")
    return {
        "status": "OFFLINE_CONTRACT_MATERIALIZED_LIVE_CLOSED",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "execution_authorized": False,
    }


def bind_preflight_state_change_evidence(
    contract: VersionedNoCallPreflightContract,
    *,
    provisioning_receipt_hash: str,
    independent_trust_anchor_hash: str,
    recorded_at: datetime,
) -> PreflightStateChangeEvidence:
    """Bind caller-supplied evidence; this does not attest that a change occurred."""

    contract = VersionedNoCallPreflightContract.model_validate(contract.model_dump(mode="json"))
    _require(
        provisioning_receipt_hash != independent_trust_anchor_hash,
        "provisioning receipt and trust anchor must be independent",
    )
    body = {
        "schema_version": "preflight-state-change-evidence-v1",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "evidence_kind": StateChangeEvidenceKind.CREDENTIAL_PROVISIONING_COMPLETED,
        "subject_names_hash": sha256_json(list(STATE_CHANGE_SUBJECTS)),
        "predecessor_terminal_file_sha256": contract.d141_blocked_terminal.file_sha256,
        "provisioning_receipt_hash": provisioning_receipt_hash,
        "independent_trust_anchor_hash": independent_trust_anchor_hash,
        "recorded_at": _utc(recorded_at, label="state-change evidence recorded_at"),
        "raw_credential_value_observed": False,
        "raw_credential_value_persisted": False,
        "source_or_contract_changed": False,
    }
    json_body = {
        **body,
        "recorded_at": body["recorded_at"].isoformat().replace("+00:00", "Z"),
    }
    content_hash = sha256_json(json_body)
    return PreflightStateChangeEvidence(
        **body,
        evidence_id=_derived_id("ncpstate", content_hash),
        content_hash=content_hash,
    )


def bind_preflight_approval(
    contract: VersionedNoCallPreflightContract,
    evidence: PreflightStateChangeEvidence,
    *,
    authenticated_approval_receipt_hash: str,
    recorded_at: datetime,
) -> PreflightApprovalBinding:
    """Bind an externally authenticated exact approval without inferring it."""

    contract = VersionedNoCallPreflightContract.model_validate(contract.model_dump(mode="json"))
    evidence = PreflightStateChangeEvidence.model_validate(evidence.model_dump(mode="json"))
    _require(evidence.contract_id == contract.contract_id, "state-change evidence contract differs")
    _require(
        evidence.contract_content_hash == contract.content_hash,
        "state-change evidence contract hash differs",
    )
    _require(
        authenticated_approval_receipt_hash
        not in {evidence.provisioning_receipt_hash, evidence.independent_trust_anchor_hash},
        "approval receipt must be independent of state-change evidence",
    )
    _require(recorded_at >= evidence.recorded_at, "approval predates state-change evidence")
    body = {
        "schema_version": "preflight-approval-binding-v1",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "state_change_evidence_id": evidence.evidence_id,
        "state_change_evidence_content_hash": evidence.content_hash,
        "approved_scopes": ATTEMPT_APPROVED_SCOPES,
        "authenticated_approval_receipt_hash": authenticated_approval_receipt_hash,
        "recorded_at": _utc(recorded_at, label="approval recorded_at"),
        "attempt_limit": 1,
        "credential_value_in_approval": False,
        "credential_provisioning_authorized": False,
        "execution_hash_or_candidate_authorized": False,
        "cost_or_paid_execution_authorized": False,
        "provider_evaluator_agent_execution_authorized": False,
    }
    json_body = {
        **body,
        "approved_scopes": list(ATTEMPT_APPROVED_SCOPES),
        "recorded_at": body["recorded_at"].isoformat().replace("+00:00", "Z"),
    }
    content_hash = sha256_json(json_body)
    return PreflightApprovalBinding(
        **body,
        approval_id=_derived_id("ncpapproval", content_hash),
        content_hash=content_hash,
    )


def build_preflight_consumption_snapshot(
    *,
    ledger_root_hash: str,
    through_sequence: int,
    consumed_state_change_evidence_ids: Sequence[str] = (),
    consumed_approval_ids: Sequence[str] = (),
    reserved_or_terminal_attempt_ids: Sequence[str] = (),
) -> PreflightConsumptionSnapshot:
    """Build a canonical projection; the caller must authenticate it at use time."""

    evidence_ids = tuple(consumed_state_change_evidence_ids)
    approval_ids = tuple(consumed_approval_ids)
    attempt_ids = tuple(reserved_or_terminal_attempt_ids)
    _require(len(evidence_ids) == len(set(evidence_ids)), "state-change evidence is duplicated")
    _require(len(approval_ids) == len(set(approval_ids)), "approval is duplicated")
    _require(len(attempt_ids) == len(set(attempt_ids)), "attempt is duplicated")
    body = {
        "schema_version": "preflight-consumption-snapshot-v1",
        "ledger_root_hash": ledger_root_hash,
        "through_sequence": through_sequence,
        "consumed_state_change_evidence_ids": tuple(sorted(evidence_ids)),
        "consumed_approval_ids": tuple(sorted(approval_ids)),
        "reserved_or_terminal_attempt_ids": tuple(sorted(attempt_ids)),
    }
    json_body = {
        **body,
        "consumed_state_change_evidence_ids": list(body["consumed_state_change_evidence_ids"]),
        "consumed_approval_ids": list(body["consumed_approval_ids"]),
        "reserved_or_terminal_attempt_ids": list(body["reserved_or_terminal_attempt_ids"]),
    }
    return PreflightConsumptionSnapshot(**body, content_hash=sha256_json(json_body))


def build_preflight_attempt_intent(
    contract: VersionedNoCallPreflightContract,
    evidence: PreflightStateChangeEvidence,
    approval: PreflightApprovalBinding,
    snapshot: PreflightConsumptionSnapshot,
    *,
    trusted_state_change_evidence_content_hash: str,
    trusted_approval_content_hash: str,
    trusted_consumption_snapshot_hash: str,
    created_at: datetime,
) -> PreflightAttemptIntent:
    """Derive one attempt only after three independent trusted bindings match."""

    contract = VersionedNoCallPreflightContract.model_validate(contract.model_dump(mode="json"))
    evidence = PreflightStateChangeEvidence.model_validate(evidence.model_dump(mode="json"))
    approval = PreflightApprovalBinding.model_validate(approval.model_dump(mode="json"))
    snapshot = PreflightConsumptionSnapshot.model_validate(snapshot.model_dump(mode="json"))
    _require(
        evidence.content_hash == trusted_state_change_evidence_content_hash,
        "state-change evidence is not the trusted artifact",
    )
    _require(
        approval.content_hash == trusted_approval_content_hash,
        "approval is not the trusted artifact",
    )
    _require(
        snapshot.content_hash == trusted_consumption_snapshot_hash,
        "consumption snapshot is not the trusted ledger projection",
    )
    _require(evidence.contract_id == contract.contract_id, "attempt evidence contract differs")
    _require(
        evidence.contract_content_hash == contract.content_hash, "attempt evidence hash differs"
    )
    _require(approval.contract_id == contract.contract_id, "attempt approval contract differs")
    _require(
        approval.contract_content_hash == contract.content_hash, "attempt approval hash differs"
    )
    _require(
        approval.state_change_evidence_id == evidence.evidence_id
        and approval.state_change_evidence_content_hash == evidence.content_hash,
        "approval does not bind the exact state-change evidence",
    )
    _require(
        approval.recorded_at >= evidence.recorded_at, "approval predates state-change evidence"
    )
    _require(created_at >= approval.recorded_at, "attempt predates approval")
    _require(
        evidence.evidence_id not in snapshot.consumed_state_change_evidence_ids,
        "state-change evidence was already consumed",
    )
    _require(
        approval.approval_id not in snapshot.consumed_approval_ids, "approval was already consumed"
    )
    body = {
        "schema_version": "preflight-attempt-intent-v1",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "state_change_evidence_id": evidence.evidence_id,
        "state_change_evidence_content_hash": evidence.content_hash,
        "approval_id": approval.approval_id,
        "approval_content_hash": approval.content_hash,
        "consumption_snapshot_hash": snapshot.content_hash,
        "created_at": _utc(created_at, label="attempt created_at"),
        "attempt_number": 1,
        "state": "intent_recorded",
        "one_use": True,
        "retry_or_resume_allowed": False,
        "authority": PreflightAttemptAuthority().model_dump(mode="json"),
    }
    json_body = {
        **body,
        "created_at": body["created_at"].isoformat().replace("+00:00", "Z"),
    }
    content_hash = sha256_json(json_body)
    attempt = PreflightAttemptIntent(
        **body,
        attempt_id=_derived_id("ncpattempt", content_hash),
        content_hash=content_hash,
    )
    _require(
        attempt.attempt_id not in snapshot.reserved_or_terminal_attempt_ids,
        "attempt identity was already reserved or terminal",
    )
    return attempt


def _transition(
    attempt: PreflightAttemptIntent,
    *,
    sequence: Literal[1, 2],
    previous_content_hash: str,
    transition_kind: Literal["action_started", "terminal"],
    recorded_at: datetime,
    terminal_outcome: PreflightTerminalOutcome | None = None,
    terminal_reason: PreflightTerminalReason | None = None,
    activity: PreflightActivitySummary | None = None,
    observation: PreflightObservationResult | None = None,
) -> PreflightTransition:
    body = {
        "schema_version": "preflight-transition-v1",
        "attempt_id": attempt.attempt_id,
        "sequence": sequence,
        "previous_content_hash": previous_content_hash,
        "transition_kind": transition_kind,
        "recorded_at": _utc(recorded_at, label="transition recorded_at"),
        "terminal_outcome": terminal_outcome,
        "terminal_reason": terminal_reason,
        "activity": None if activity is None else activity.model_dump(mode="json"),
        "observation": None if observation is None else observation.model_dump(mode="json"),
    }
    json_body = {
        **body,
        "recorded_at": body["recorded_at"].isoformat().replace("+00:00", "Z"),
        "terminal_outcome": None if terminal_outcome is None else terminal_outcome.value,
        "terminal_reason": None if terminal_reason is None else terminal_reason.value,
    }
    content_hash = sha256_json(json_body)
    return PreflightTransition(
        **body,
        transition_id=_derived_id("ncptransition", content_hash),
        content_hash=content_hash,
    )


def build_preflight_action_started_transition(
    attempt: PreflightAttemptIntent,
    *,
    recorded_at: datetime,
) -> PreflightTransition:
    """Build the durable marker that must precede the first observation."""

    attempt = PreflightAttemptIntent.model_validate(attempt.model_dump(mode="json"))
    return _transition(
        attempt,
        sequence=1,
        previous_content_hash=attempt.content_hash,
        transition_kind="action_started",
        recorded_at=recorded_at,
    )


def build_preflight_terminal_transition(
    attempt: PreflightAttemptIntent,
    action_started: PreflightTransition,
    *,
    outcome: PreflightTerminalOutcome,
    reason: PreflightTerminalReason | None,
    activity: PreflightActivitySummary,
    observation: PreflightObservationResult,
    recorded_at: datetime,
) -> PreflightTransition:
    """Build one terminal transition after the durable action marker."""

    attempt = PreflightAttemptIntent.model_validate(attempt.model_dump(mode="json"))
    action_started = PreflightTransition.model_validate(action_started.model_dump(mode="json"))
    _require(action_started.attempt_id == attempt.attempt_id, "action marker attempt differs")
    _require(
        action_started.transition_kind == "action_started", "terminal parent is not action-started"
    )
    return _transition(
        attempt,
        sequence=2,
        previous_content_hash=action_started.content_hash,
        transition_kind="terminal",
        recorded_at=recorded_at,
        terminal_outcome=outcome,
        terminal_reason=reason,
        activity=activity,
        observation=observation,
    )


def validate_preflight_transition_chain(
    attempt: PreflightAttemptIntent,
    transitions: Sequence[PreflightTransition],
) -> dict[str, Any]:
    """Validate an append-only chain; intent creation already consumes evidence."""

    attempt = PreflightAttemptIntent.model_validate(attempt.model_dump(mode="json"))
    values = tuple(
        PreflightTransition.model_validate(item.model_dump(mode="json")) for item in transitions
    )
    _require(len(values) <= 2, "preflight transition chain contains an append after terminal")
    if values:
        started = values[0]
        _require(started.attempt_id == attempt.attempt_id, "action marker attempt differs")
        _require(
            started.transition_kind == "action_started", "first transition is not action-started"
        )
        _require(
            started.previous_content_hash == attempt.content_hash, "action marker parent differs"
        )
        _require(started.recorded_at >= attempt.created_at, "action marker predates attempt")
    if len(values) == 2:
        terminal = values[1]
        _require(terminal.attempt_id == attempt.attempt_id, "terminal attempt differs")
        _require(terminal.transition_kind == "terminal", "second transition is not terminal")
        _require(
            terminal.previous_content_hash == values[0].content_hash, "terminal parent differs"
        )
        _require(terminal.recorded_at >= values[0].recorded_at, "terminal predates action marker")
    return {
        "attempt_id": attempt.attempt_id,
        "state_change_evidence_id": attempt.state_change_evidence_id,
        "approval_id": attempt.approval_id,
        "evidence_consumed": True,
        "approval_consumed": True,
        "observation_started": bool(values),
        "terminal": len(values) == 2,
        "terminal_outcome": (None if len(values) != 2 else values[1].terminal_outcome.value),
        "retry_or_resume_allowed": False,
    }


def validate_preflight_attempt_ledger(
    contract: VersionedNoCallPreflightContract,
    attempts: Sequence[PreflightAttemptIntent],
) -> tuple[PreflightAttemptIntent, ...]:
    """Reject evidence, approval, or attempt reuse across a durable ledger."""

    contract = VersionedNoCallPreflightContract.model_validate(contract.model_dump(mode="json"))
    values = tuple(
        PreflightAttemptIntent.model_validate(item.model_dump(mode="json")) for item in attempts
    )
    for item in values:
        _require(item.contract_id == contract.contract_id, "ledger attempt contract differs")
        _require(item.contract_content_hash == contract.content_hash, "ledger attempt hash differs")
    for label, identities in (
        ("attempt", tuple(item.attempt_id for item in values)),
        ("state-change evidence", tuple(item.state_change_evidence_id for item in values)),
        ("approval", tuple(item.approval_id for item in values)),
    ):
        _require(len(identities) == len(set(identities)), f"{label} was reused")
    return values


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
        raise VersionedNoCallPreflightError("local Git source read failed") from exc
    _require(completed.returncode == 0, "local Git source read failed")
    return completed.stdout


def _commit_binding(root: Path, source_commit: str) -> SourceCommitBinding:
    commit = _git(root, "rev-parse", f"{source_commit}^{{commit}}").decode("ascii").strip()
    tree = _git(root, "rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    row = _git(root, "rev-list", "--parents", "-n", "1", commit).decode("ascii").strip().split()
    _require(row and row[0] == commit, "source commit parent binding failed")
    parents = tuple(row[1:])
    _require(
        parents == (EVALUATOR_V2_BOUNDARY_COMMIT,),
        "preflight source is not the exact evaluator-v2 direct child",
    )
    diff = _git(
        root,
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "-r",
        parents[0],
        commit,
    ).decode("utf-8")
    rows = tuple(line.split("\t", 1) for line in diff.splitlines() if line)
    _require(
        all(len(parts) == 2 and parts[0] == "A" for parts in rows),
        "source commit is not add-only",
    )
    added_paths = tuple(sorted(parts[1] for parts in rows))
    return SourceCommitBinding(
        commit=commit,
        tree=tree,
        parents=parents,
        added_paths=added_paths,
    )


def _committed_file(root: Path, commit: str, path: Path) -> tuple[CommittedFileBinding, bytes]:
    logical = safe_relative_path(path.as_posix(), field_name="committed source path")
    raw = _git(root, "show", f"{commit}:{logical}")
    tree_row = _git(root, "ls-tree", commit, "--", logical).decode("utf-8").strip()
    parts = tree_row.split(None, 3)
    _require(len(parts) == 4 and parts[1] == "blob", f"committed source is not a blob: {logical}")
    return (
        CommittedFileBinding(
            path=logical,
            blob_oid=parts[2],
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
) -> VersionedNoCallPreflightSourceQualification:
    contract = load_versioned_no_call_preflight_contract(repository=root)
    commit = _commit_binding(root, source_commit)
    source_pairs = tuple(_committed_file(root, commit.commit, path) for path in SOURCE_PATHS)
    validation_pairs = tuple(
        _committed_file(root, commit.commit, path) for path in VALIDATION_PATHS
    )
    source_files = tuple(item[0] for item in source_pairs)
    validation_files = tuple(item[0] for item in validation_pairs)
    contract_index = SOURCE_PATHS.index(CONTRACT_PATH)
    _require(
        source_pairs[contract_index][1] == _contract_bytes(contract),
        "committed preflight contract differs from validated contract",
    )
    body = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": QUALIFICATION_STATUS,
        "recorded_at": _utc(recorded_at, label="qualification recorded_at"),
        "source_commit": commit.model_dump(mode="json"),
        "source_files": tuple(item.model_dump(mode="json") for item in source_files),
        "validation_files": tuple(item.model_dump(mode="json") for item in validation_files),
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "contract_file": source_files[contract_index].model_dump(mode="json"),
        "evaluator_v2_source_qualification_hash": contract.evaluator_v2_source_qualification_hash,
        "evaluator_source_hash": contract.evaluator_source_hash,
        "successor_suite_hash": contract.successor_suite_hash,
        "runtime_tuple_hash": contract.runtime_tuple_hash,
        "authority": PreflightQualificationAuthority().model_dump(mode="json"),
        "next_gate": "separately-approved-no-call-preflight-attempt",
    }
    json_body = {
        **body,
        "recorded_at": body["recorded_at"].isoformat().replace("+00:00", "Z"),
        "source_files": list(body["source_files"]),
        "validation_files": list(body["validation_files"]),
    }
    return VersionedNoCallPreflightSourceQualification(
        **body,
        content_hash=sha256_json(json_body),
    )


def _qualification_bytes(value: VersionedNoCallPreflightSourceQualification) -> bytes:
    return (value.model_dump_json(indent=2) + "\n").encode("utf-8")


def _qualification_summary(
    value: VersionedNoCallPreflightSourceQualification,
    raw: bytes,
) -> dict[str, Any]:
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
        "execution_authorized": False,
        "credential_or_environment_observations_made": 0,
        "docker_or_sdk_observations_made": 0,
        "provider_evaluator_agent_calls_made": 0,
    }


def validate_versioned_no_call_preflight_source_qualification(
    *, repository: str | Path | None = None
) -> dict[str, Any]:
    root = _repo_root(repository)
    raw = _read_bytes(root, QUALIFICATION_PATH)
    try:
        value = VersionedNoCallPreflightSourceQualification.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise VersionedNoCallPreflightError("preflight source qualification is invalid") from exc
    _require(raw == _qualification_bytes(value), "preflight qualification bytes are not canonical")
    expected = _build_source_qualification(
        root,
        source_commit=value.source_commit.commit,
        recorded_at=value.recorded_at,
    )
    _require(value == expected, "preflight source qualification has drifted")
    return _qualification_summary(value, raw)


def run_versioned_no_call_preflight_source_qualification(
    *,
    source_commit: str = "HEAD",
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Create the commit-bound source artifact once, or replay-validate it."""

    root = _repo_root(repository)
    selected = _logical_path(root, QUALIFICATION_PATH, must_exist=False)
    if selected.exists():
        return validate_versioned_no_call_preflight_source_qualification(repository=root)
    value = _build_source_qualification(
        root,
        source_commit=source_commit,
        recorded_at=datetime.now(UTC),
    )
    raw = _qualification_bytes(value)
    selected.parent.mkdir(parents=True, exist_ok=True)
    try:
        with selected.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise VersionedNoCallPreflightError(
            "preflight source qualification cannot be materialized"
        ) from exc
    _require(_read_bytes(root, QUALIFICATION_PATH) == raw, "qualification reread differs")
    return validate_versioned_no_call_preflight_source_qualification(repository=root)
