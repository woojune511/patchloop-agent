"""Offline v4 successor for a user-reported manual Docker Desktop start.

The consumed v3 attempt is never retried or reopened.  This module only binds
the user's bounded manual-start attestation to the exact v3 terminal and a new
source identity.  It has no Docker, SDK, dotenv, network, or provider runtime.
"""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from patchloop.contracts import FrozenStrictModel
from patchloop.errors import ContractError
from patchloop.evals import executable_no_call_preflight as v3
from patchloop.runtime import repository_root
from patchloop.util import safe_relative_path, sha256_bytes, sha256_json

CONTRACT_SCHEMA_VERSION = "manual-docker-start-state-successor-contract-v4"
CONTRACT_VERSION = "ac-evaluator-v2-manual-docker-start-state-v4"
CONTRACT_PATH = Path("experiments/evaluator-v2-manual-docker-start-state-v4.contract.json")
PREDECESSOR_EVIDENCE_COMMIT = "917d6dcc531aa8e6c3db40fd5cf7ca03038c8a50"

RUNTIME_PATH = Path("patchloop/evals/manual_docker_start_state_successor.py")
BUILD_SCRIPT_PATH = Path("scripts/build_manual_docker_start_state_successor.py")
TEST_PATH = Path("tests/test_manual_docker_start_state_successor.py")

QUALIFICATION_SCHEMA_VERSION = "manual-docker-start-state-source-qualification-v4"
QUALIFICATION_ID = "ac-evaluator-v2-manual-docker-start-state-source-20260812-r1"
QUALIFICATION_STATUS = "OFFLINE_MANUAL_DOCKER_START_STATE_SOURCE_QUALIFIED_LIVE_CLOSED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-manual-docker-start-state-v4-source-qualification.json"
)
USER_ATTESTATION_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-manual-docker-start-state-v4-user-attestation.json"
)
STATE_EVIDENCE_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-manual-docker-start-state-v4-state-change-evidence.json"
)

SOURCE_FILES = tuple(sorted((CONTRACT_PATH, RUNTIME_PATH, BUILD_SCRIPT_PATH, TEST_PATH), key=str))
SOURCE_ADDED_PATHS = tuple(item.as_posix() for item in SOURCE_FILES)

MANUAL_START_CLAIM = "docker-desktop-started-manually-by-user"
IDENTITY_ASSURANCE = "current-user-self-attested-not-authenticated-or-signed"
NEXT_GATE = "qualified-no-start-executable-successor-source"


class ManualDockerStartStateError(ContractError):
    """The offline v4 state successor failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ManualDockerStartStateError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = repository_root() if repository is None else Path(repository)
    return selected.resolve(strict=True)


def _logical_path(root: Path, relative: Path, *, must_exist: bool) -> Path:
    safe = safe_relative_path(relative.as_posix(), field_name="manual Docker state path")
    selected = root.joinpath(*Path(safe).parts)
    resolved = selected.resolve(strict=must_exist)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ManualDockerStartStateError("manual Docker state path escaped repository") from exc
    return resolved


def _read_bytes(root: Path, relative: Path) -> bytes:
    selected = _logical_path(root, relative, must_exist=True)
    _require(not selected.is_symlink(), f"state path is link-like: {relative.as_posix()}")
    before = selected.stat()
    raw = selected.read_bytes()
    after = selected.stat()
    _require(
        (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
        f"state path changed while reading: {relative.as_posix()}",
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
        raise ManualDockerStartStateError(
            f"append-only artifact already exists: {relative.as_posix()}"
        ) from exc
    except OSError as exc:
        raise ManualDockerStartStateError(
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
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def _hash_body(body: dict[str, Any]) -> str:
    return sha256_json(_json_ready(body))


class ConsumedV3Binding(FrozenStrictModel):
    evidence_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_change_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_change_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    approval_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    attempt_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    action_started_id: str = Field(pattern=r"^ncpstarted_[0-9a-f]{64}$")
    action_started_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    terminal_id: str = Field(pattern=r"^ncpterminal_[0-9a-f]{64}$")
    terminal_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    terminal_outcome: Literal["blocked"] = "blocked"
    terminal_reason: Literal["docker_not_ready"] = "docker_not_ready"
    activity_accounting_complete: Literal[True] = True
    unknown_post_marker_activity_possible: Literal[False] = False
    docker_cli_command_count: Literal[8] = 8
    dotenv_file_read_count: Literal[0] = 0
    sdk_child_start_count: Literal[0] = 0
    network_call_count: Literal[0] = 0
    provider_evaluator_agent_call_count: Literal[0] = 0
    retry_or_resume_allowed: Literal[False] = False

    @model_validator(mode="after")
    def validate_commit(self) -> ConsumedV3Binding:
        if self.evidence_commit != PREDECESSOR_EVIDENCE_COMMIT:
            raise ValueError("consumed v3 evidence commit drifted")
        return self


class ManualStartStateRule(FrozenStrictModel):
    schema_version: Literal["manual-docker-start-state-rule-v4"] = (
        "manual-docker-start-state-rule-v4"
    )
    exact_claim: Literal["docker-desktop-started-manually-by-user"] = MANUAL_START_CLAIM
    actor: Literal["user"] = "user"
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    manual_start_is_relevant_state_change: Literal[True] = True
    manual_start_reopens_consumed_v3: Literal[False] = False
    attestation_proves_daemon_ready: Literal[False] = False
    attestation_proves_exact_images_present: Literal[False] = False
    attestation_proves_container_inventory_safe: Literal[False] = False
    patchloop_observation_allowed_during_binding: Literal[False] = False
    fresh_executable_source_required: Literal[True] = True
    later_exact_approval_required: Literal[True] = True


class StructuralSuccessorAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    source_qualification_authorized: Literal[True] = True
    manual_user_attestation_binding_authorized: Literal[True] = True
    state_evidence_binding_authorized: Literal[True] = True
    docker_desktop_or_daemon_start_authorized: Literal[False] = False
    docker_cli_observation_authorized: Literal[False] = False
    image_pull_load_or_store_mutation_authorized: Literal[False] = False
    container_operation_authorized: Literal[False] = False
    sdk_or_dotenv_observation_authorized: Literal[False] = False
    network_or_transport_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    execution_hash_candidate_cost_or_paid_execution_authorized: Literal[False] = False
    v3_retry_replacement_or_resume_authorized: Literal[False] = False


class ManualDockerStartStateContract(FrozenStrictModel):
    schema_version: Literal["manual-docker-start-state-successor-contract-v4"] = (
        CONTRACT_SCHEMA_VERSION
    )
    contract_version: Literal["ac-evaluator-v2-manual-docker-start-state-v4"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor: ConsumedV3Binding
    state_rule: ManualStartStateRule
    authority: StructuralSuccessorAuthority
    executable_runtime_implemented: Literal[False] = False
    next_gate: Literal["qualified-no-start-executable-successor-source"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> ManualDockerStartStateContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected = _hash_body(body)
        if self.content_hash != expected:
            raise ValueError("manual Docker state contract hash mismatch")
        if self.contract_id != _derived_id("ncpcontract", expected):
            raise ValueError("manual Docker state contract id mismatch")
        return self


class ManualDockerStartUserAttestation(FrozenStrictModel):
    schema_version: Literal["manual-docker-start-user-attestation-v4"] = (
        "manual-docker-start-user-attestation-v4"
    )
    attestation_id: str = Field(pattern=r"^ncpattestation_[0-9a-f]{64}$")
    contract_version: Literal["ac-evaluator-v2-manual-docker-start-state-v4"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_terminal_id: str = Field(pattern=r"^ncpterminal_[0-9a-f]{64}$")
    claim: Literal["docker-desktop-started-manually-by-user"] = MANUAL_START_CLAIM
    actor: Literal["user"] = "user"
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    manual_start_reported: Literal[True] = True
    daemon_ready_claimed: Literal[False] = False
    exact_images_present_claimed: Literal[False] = False
    container_inventory_safe_claimed: Literal[False] = False
    v3_retry_or_resume_authorized: Literal[False] = False
    offline_state_binding_only: Literal[True] = True
    patchloop_docker_cli_call_count: Literal[0] = 0
    patchloop_dotenv_read_or_stat_count: Literal[0] = 0
    patchloop_sdk_child_start_count: Literal[0] = 0
    patchloop_network_provider_evaluator_agent_call_count: Literal[0] = 0
    patchloop_image_or_container_mutation_count: Literal[0] = 0
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("manual start attestation recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> ManualDockerStartUserAttestation:
        body = self.model_dump(mode="json", exclude={"attestation_id", "content_hash"})
        expected = _hash_body(body)
        if self.content_hash != expected:
            raise ValueError("manual start attestation hash mismatch")
        if self.attestation_id != _derived_id("ncpattestation", expected):
            raise ValueError("manual start attestation id mismatch")
        return self


class ManualDockerStartStateEvidence(FrozenStrictModel):
    schema_version: Literal["manual-docker-start-state-change-evidence-v4"] = (
        "manual-docker-start-state-change-evidence-v4"
    )
    evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    contract_version: Literal["ac-evaluator-v2-manual-docker-start-state-v4"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_terminal_id: str = Field(pattern=r"^ncpterminal_[0-9a-f]{64}$")
    predecessor_terminal_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    user_attestation_id: str = Field(pattern=r"^ncpattestation_[0-9a-f]{64}$")
    user_attestation_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_kind: Literal["manual-docker-desktop-start-user-attested-v4"] = (
        "manual-docker-desktop-start-user-attested-v4"
    )
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    relevant_external_state_change_reported: Literal[True] = True
    independent_verification_completed: Literal[False] = False
    daemon_ready_verified: Literal[False] = False
    exact_images_present_verified: Literal[False] = False
    container_inventory_verified: Literal[False] = False
    v3_consumed_and_not_reopened: Literal[True] = True
    executable_runtime_implemented: Literal[False] = False
    exact_approval_allowed_for_this_structural_source: Literal[False] = False
    patchloop_external_observation_count: Literal[0] = 0
    patchloop_mutation_count: Literal[0] = 0
    next_gate: Literal["qualified-no-start-executable-successor-source"] = NEXT_GATE
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("manual start state recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> ManualDockerStartStateEvidence:
        body = self.model_dump(mode="json", exclude={"evidence_id", "content_hash"})
        expected = _hash_body(body)
        if self.content_hash != expected:
            raise ValueError("manual start state hash mismatch")
        if self.evidence_id != _derived_id("ncpstate", expected):
            raise ValueError("manual start state id mismatch")
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
            raise ValueError("v4 source predecessor drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v4 source additions drifted")
        return self


class QualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    source_qualified: Literal[True] = True
    manual_start_attestation_created: Literal[False] = False
    state_change_evidence_created: Literal[False] = False
    docker_sdk_dotenv_or_network_observation_count: Literal[0] = 0
    external_mutation_count: Literal[0] = 0
    approval_attempt_or_transition_created: Literal[False] = False
    execution_hash_candidate_cost_or_paid_execution_authorized: Literal[False] = False


class ManualDockerStartSourceQualification(FrozenStrictModel):
    schema_version: Literal["manual-docker-start-state-source-qualification-v4"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal["ac-evaluator-v2-manual-docker-start-state-source-20260812-r1"] = (
        QUALIFICATION_ID
    )
    status: Literal["OFFLINE_MANUAL_DOCKER_START_STATE_SOURCE_QUALIFIED_LIVE_CLOSED"] = (
        QUALIFICATION_STATUS
    )
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[CommittedFileBinding, ...]
    contract_version: Literal["ac-evaluator-v2-manual-docker-start-state-v4"] = CONTRACT_VERSION
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    contract_file: CommittedFileBinding
    predecessor_terminal_id: str = Field(pattern=r"^ncpterminal_[0-9a-f]{64}$")
    predecessor_terminal_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authority: QualificationAuthority
    next_gate: Literal["manual-start-attestation-state-binding"] = (
        "manual-start-attestation-state-binding"
    )
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v4 qualification recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> ManualDockerStartSourceQualification:
        if tuple(item.path for item in self.source_files) != SOURCE_ADDED_PATHS:
            raise ValueError("v4 qualification inventory drifted")
        if self.contract_file.path != CONTRACT_PATH.as_posix():
            raise ValueError("v4 qualification contract path drifted")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != _hash_body(body):
            raise ValueError("v4 qualification hash mismatch")
        return self


def _load_predecessor(
    root: Path,
) -> tuple[
    v3.ExecutableNoCallPreflightContract,
    v3.ExecutableSourceQualification,
    v3.ExecutableStateChangeEvidence,
    v3.ExecutableApprovalBinding,
    v3.AttemptIntent,
    v3.ActionStarted,
    v3.TerminalTransition,
]:
    v3.validate_executable_attempt_chain(repository=root)
    contract = v3.load_executable_no_call_preflight_contract(repository=root)
    qualification = v3.ExecutableSourceQualification.model_validate_json(
        _read_bytes(root, v3.QUALIFICATION_PATH)
    )
    state = v3.ExecutableStateChangeEvidence.model_validate_json(
        _read_bytes(root, v3.STATE_EVIDENCE_PATH)
    )
    approval = v3.ExecutableApprovalBinding.model_validate_json(
        _read_bytes(root, v3.APPROVAL_BINDING_PATH)
    )
    attempt = v3.AttemptIntent.model_validate_json(_read_bytes(root, v3.ATTEMPT_PATH))
    action = v3.ActionStarted.model_validate_json(_read_bytes(root, v3.ACTION_STARTED_PATH))
    terminal = v3.TerminalTransition.model_validate_json(_read_bytes(root, v3.TERMINAL_PATH))
    _require(terminal.outcome.value == "blocked", "predecessor outcome is not BLOCKED")
    _require(
        terminal.reason is not None and terminal.reason.value == "docker_not_ready",
        "predecessor reason is not docker_not_ready",
    )
    _require(terminal.docker_cli_command_count == 8, "predecessor Docker count differs")
    _require(terminal.dotenv_file_read_count == 0, "predecessor dotenv count differs")
    _require(terminal.sdk_child_start_count == 0, "predecessor SDK count differs")
    return contract, qualification, state, approval, attempt, action, terminal


def _predecessor_binding(root: Path) -> ConsumedV3Binding:
    contract, qualification, state, approval, attempt, action, terminal = _load_predecessor(root)
    return ConsumedV3Binding(
        evidence_commit=PREDECESSOR_EVIDENCE_COMMIT,
        contract_id=contract.contract_id,
        contract_content_hash=contract.content_hash,
        source_qualification_hash=qualification.content_hash,
        state_change_evidence_id=state.evidence_id,
        state_change_evidence_content_hash=state.content_hash,
        approval_id=approval.approval_id,
        approval_content_hash=approval.content_hash,
        attempt_id=attempt.attempt_id,
        attempt_content_hash=attempt.content_hash,
        action_started_id=action.marker_id,
        action_started_content_hash=action.content_hash,
        terminal_id=terminal.terminal_id,
        terminal_content_hash=terminal.content_hash,
    )


def _build_contract(root: Path) -> ManualDockerStartStateContract:
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "predecessor": _predecessor_binding(root).model_dump(mode="json"),
        "state_rule": ManualStartStateRule().model_dump(mode="json"),
        "authority": StructuralSuccessorAuthority().model_dump(mode="json"),
        "executable_runtime_implemented": False,
        "next_gate": NEXT_GATE,
    }
    content_hash = _hash_body(body)
    return ManualDockerStartStateContract(
        **body,
        contract_id=_derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def load_contract(*, repository: str | Path | None = None) -> ManualDockerStartStateContract:
    root = _repo_root(repository)
    raw = _read_bytes(root, CONTRACT_PATH)
    try:
        value = ManualDockerStartStateContract.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise ManualDockerStartStateError("v4 contract artifact is invalid") from exc
    _require(raw == _canonical_bytes(value), "v4 contract bytes are not canonical")
    _require(value == _build_contract(root), "v4 contract has drifted")
    return value


def materialize_contract(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    selected = _logical_path(root, CONTRACT_PATH, must_exist=False)
    if selected.exists():
        value = load_contract(repository=root)
        raw = _read_bytes(root, CONTRACT_PATH)
    else:
        value = _build_contract(root)
        raw = _canonical_bytes(value)
        _write_once(root, CONTRACT_PATH, raw)
    return {
        "status": "OFFLINE_MANUAL_DOCKER_START_STATE_CONTRACT_MATERIALIZED_LIVE_CLOSED",
        "contract_id": value.contract_id,
        "contract_content_hash": value.content_hash,
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
    }


def build_user_attestation(
    contract: ManualDockerStartStateContract,
    qualification: ManualDockerStartSourceQualification,
    *,
    claim: str,
    recorded_at: datetime,
) -> ManualDockerStartUserAttestation:
    _require(claim == MANUAL_START_CLAIM, "manual start claim differs")
    _require(qualification.contract_id == contract.contract_id, "qualification contract differs")
    body = {
        "schema_version": "manual-docker-start-user-attestation-v4",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "source_qualification_content_hash": qualification.content_hash,
        "predecessor_terminal_id": contract.predecessor.terminal_id,
        "claim": MANUAL_START_CLAIM,
        "actor": "user",
        "identity_assurance": IDENTITY_ASSURANCE,
        "manual_start_reported": True,
        "daemon_ready_claimed": False,
        "exact_images_present_claimed": False,
        "container_inventory_safe_claimed": False,
        "v3_retry_or_resume_authorized": False,
        "offline_state_binding_only": True,
        "patchloop_docker_cli_call_count": 0,
        "patchloop_dotenv_read_or_stat_count": 0,
        "patchloop_sdk_child_start_count": 0,
        "patchloop_network_provider_evaluator_agent_call_count": 0,
        "patchloop_image_or_container_mutation_count": 0,
        "recorded_at": _utc(recorded_at, label="manual start attestation recorded_at"),
    }
    content_hash = _hash_body(body)
    return ManualDockerStartUserAttestation(
        **body,
        attestation_id=_derived_id("ncpattestation", content_hash),
        content_hash=content_hash,
    )


def bind_state_evidence(
    contract: ManualDockerStartStateContract,
    qualification: ManualDockerStartSourceQualification,
    attestation: ManualDockerStartUserAttestation,
    *,
    recorded_at: datetime,
) -> ManualDockerStartStateEvidence:
    _require(attestation.contract_id == contract.contract_id, "attestation contract differs")
    _require(
        attestation.source_qualification_content_hash == qualification.content_hash,
        "attestation qualification differs",
    )
    _require(recorded_at >= attestation.recorded_at, "state predates attestation")
    body = {
        "schema_version": "manual-docker-start-state-change-evidence-v4",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "source_qualification_content_hash": qualification.content_hash,
        "predecessor_terminal_id": contract.predecessor.terminal_id,
        "predecessor_terminal_content_hash": contract.predecessor.terminal_content_hash,
        "user_attestation_id": attestation.attestation_id,
        "user_attestation_content_hash": attestation.content_hash,
        "evidence_kind": "manual-docker-desktop-start-user-attested-v4",
        "identity_assurance": IDENTITY_ASSURANCE,
        "relevant_external_state_change_reported": True,
        "independent_verification_completed": False,
        "daemon_ready_verified": False,
        "exact_images_present_verified": False,
        "container_inventory_verified": False,
        "v3_consumed_and_not_reopened": True,
        "executable_runtime_implemented": False,
        "exact_approval_allowed_for_this_structural_source": False,
        "patchloop_external_observation_count": 0,
        "patchloop_mutation_count": 0,
        "next_gate": NEXT_GATE,
        "recorded_at": _utc(recorded_at, label="manual start state recorded_at"),
    }
    content_hash = _hash_body(body)
    return ManualDockerStartStateEvidence(
        **body,
        evidence_id=_derived_id("ncpstate", content_hash),
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
        raise ManualDockerStartStateError("local Git source read failed") from exc
    _require(completed.returncode == 0, "local Git source read failed")
    return completed.stdout


def _source_commit(root: Path, selected: str) -> SourceCommitBinding:
    commit = _git(root, "rev-parse", f"{selected}^{{commit}}").decode("ascii").strip()
    tree = _git(root, "rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    row = _git(root, "rev-list", "--parents", "-n", "1", commit).decode("ascii").split()
    _require(row and row[0] == commit and len(row) == 2, "v4 source parent binding failed")
    diff = _git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", row[1], commit)
    lines = diff.decode("utf-8").splitlines()
    added = tuple(sorted(parts[1] for line in lines if (parts := line.split("\t"))[:1] == ["A"]))
    _require(len(lines) == len(added), "v4 source commit contains non-addition changes")
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
) -> ManualDockerStartSourceQualification:
    contract = load_contract(repository=root)
    commit = _source_commit(root, source_commit)
    pairs = tuple(_committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(item[0] for item in pairs)
    contract_index = SOURCE_FILES.index(CONTRACT_PATH)
    _require(pairs[contract_index][1] == _canonical_bytes(contract), "committed contract differs")
    body = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": QUALIFICATION_STATUS,
        "recorded_at": _utc(recorded_at, label="v4 qualification recorded_at"),
        "source_commit": commit.model_dump(mode="json"),
        "source_files": tuple(item.model_dump(mode="json") for item in files),
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "contract_file": files[contract_index].model_dump(mode="json"),
        "predecessor_terminal_id": contract.predecessor.terminal_id,
        "predecessor_terminal_content_hash": contract.predecessor.terminal_content_hash,
        "authority": QualificationAuthority().model_dump(mode="json"),
        "next_gate": "manual-start-attestation-state-binding",
    }
    return ManualDockerStartSourceQualification(**body, content_hash=_hash_body(body))


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
        value = ManualDockerStartSourceQualification.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise ManualDockerStartStateError("v4 source qualification is invalid") from exc
    _require(raw == _canonical_bytes(value), "v4 qualification bytes are not canonical")
    expected = _build_qualification(
        root,
        source_commit=value.source_commit.commit,
        recorded_at=value.recorded_at,
    )
    _require(value == expected, "v4 source qualification has drifted")
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


def _load_qualification(root: Path) -> ManualDockerStartSourceQualification:
    validate_source_qualification(repository=root)
    return ManualDockerStartSourceQualification.model_validate_json(
        _read_bytes(root, QUALIFICATION_PATH)
    )


def record_manual_start_state(
    *,
    claim: str,
    recorded_at: datetime,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Record only the user's manual-start report; perform no observation."""

    root = _repo_root(repository)
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    _require(
        not _logical_path(root, USER_ATTESTATION_PATH, must_exist=False).exists(),
        "manual start attestation already exists",
    )
    _require(
        not _logical_path(root, STATE_EVIDENCE_PATH, must_exist=False).exists(),
        "manual start state already exists",
    )
    attestation = build_user_attestation(
        contract,
        qualification,
        claim=claim,
        recorded_at=recorded_at,
    )
    state = bind_state_evidence(
        contract,
        qualification,
        attestation,
        recorded_at=recorded_at,
    )
    attestation_raw = _canonical_bytes(attestation)
    state_raw = _canonical_bytes(state)
    _require(b"sk-" not in attestation_raw.lower() + state_raw.lower(), "credential-like bytes")
    _write_once(root, USER_ATTESTATION_PATH, attestation_raw)
    _write_once(root, STATE_EVIDENCE_PATH, state_raw)
    return validate_manual_start_state(repository=root)


def validate_manual_start_state(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    attestation_raw = _read_bytes(root, USER_ATTESTATION_PATH)
    state_raw = _read_bytes(root, STATE_EVIDENCE_PATH)
    try:
        attestation = ManualDockerStartUserAttestation.model_validate_json(attestation_raw)
        state = ManualDockerStartStateEvidence.model_validate_json(state_raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise ManualDockerStartStateError("v4 manual state artifact is invalid") from exc
    _require(attestation_raw == _canonical_bytes(attestation), "attestation bytes not canonical")
    _require(state_raw == _canonical_bytes(state), "state bytes not canonical")
    expected = bind_state_evidence(
        contract,
        qualification,
        attestation,
        recorded_at=state.recorded_at,
    )
    _require(state == expected, "v4 state does not bind exact attestation")
    return {
        "status": "MANUAL_DOCKER_START_STATE_BOUND_EXECUTABLE_SUCCESSOR_REQUIRED",
        "contract_id": contract.contract_id,
        "source_qualification_hash": qualification.content_hash,
        "attestation_id": attestation.attestation_id,
        "state_change_evidence_id": state.evidence_id,
        "state_change_evidence_content_hash": state.content_hash,
        "identity_assurance": IDENTITY_ASSURANCE,
        "daemon_ready_verified": False,
        "exact_images_present_verified": False,
        "container_inventory_verified": False,
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
        "next_gate": NEXT_GATE,
    }
