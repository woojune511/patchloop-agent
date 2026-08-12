"""Offline v10 state-binding successor for the qualified v9 runtime.

This module can bind a future, exact user statement to the qualified v9
contract/source without observing Docker, dotenv, environment, SDK, network,
or provider state.  Source qualification creates no attestation, state,
approval, attempt, or terminal artifact.
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
from patchloop.evals import sanitized_sdk_bootstrap_parent_successor as v9
from patchloop.runtime import repository_root
from patchloop.util import safe_relative_path, sha256_bytes, sha256_json

CONTRACT_SCHEMA_VERSION = "sanitized-sdk-bootstrap-state-binding-successor-contract-v10"
CONTRACT_VERSION = "ac-evaluator-v2-sanitized-sdk-bootstrap-state-binding-v10"
CONTRACT_PATH = Path(
    "experiments/evaluator-v2-sanitized-sdk-bootstrap-state-binding-v10.contract.json"
)
RUNTIME_PATH = Path("patchloop/evals/sanitized_sdk_bootstrap_state_binding_successor.py")
BUILD_SCRIPT_PATH = Path("scripts/build_sanitized_sdk_bootstrap_state_binding_successor.py")
TEST_PATH = Path("tests/test_sanitized_sdk_bootstrap_state_binding_successor.py")

SOURCE_PARENT_COMMIT = "0c0f8065d99996b632c8a2f7e288d473fe7644c5"
V9_SOURCE_COMMIT = "8678ce9e4fbae426971a90a2f47ad28b5a431885"
V9_QUALIFICATION_COMMIT = "b89f59ef46187ca08b02d047d63ad992c8cb3056"

QUALIFICATION_SCHEMA_VERSION = "sanitized-sdk-bootstrap-state-binding-source-qualification-v10"
QUALIFICATION_ID = "ac-evaluator-v2-sanitized-sdk-bootstrap-state-binding-source-20260812-r1"
QUALIFICATION_STATUS = "OFFLINE_V10_STATE_BINDING_SOURCE_QUALIFIED_LIVE_CLOSED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-bootstrap-state-binding-v10-source-qualification.json"
)
USER_ATTESTATION_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-bootstrap-state-binding-v10-user-attestation.json"
)
STATE_EVIDENCE_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-bootstrap-state-binding-v10-state-change-evidence.json"
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
            v9.CONTRACT_PATH,
            v9.RUNTIME_PATH,
            v9.QUALIFICATION_PATH,
        ),
        key=lambda path: path.as_posix(),
    )
)

IDENTITY_ASSURANCE = "current-user-self-attested-not-authenticated-or-signed"
STATE_CLAIM = "docker-running-and-dotenv-only-openai-api-key-user-attested-v10"
DOTENV_EXACT_KEY_NAMES = ("OPENAI_API_KEY",)
ATTESTATION_TEMPLATE = (
    "Contract {contract_id}, source qualification {qualification_hash}: "
    "Docker Desktop is reported running; repository-root .env is reported to contain only "
    "OPENAI_API_KEY; state-binding-only; no-execution-authority."
)
QUALIFICATION_NEXT_GATE = "fresh-exact-user-attestation-and-v10-state-materialization"
STATE_NEXT_GATE = "fresh-exact-v10-approval-successor"


class StateBindingSuccessorError(ContractError):
    """The offline v10 state-binding successor failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise StateBindingSuccessorError(message)


def _root(repository: str | Path | None) -> Path:
    selected = repository_root() if repository is None else Path(repository)
    return selected.resolve(strict=True)


def _logical_path(root: Path, relative: Path, *, must_exist: bool) -> Path:
    safe = safe_relative_path(relative.as_posix(), field_name="v10 state-binding path")
    selected = root.joinpath(*Path(safe).parts)
    resolved = selected.resolve(strict=must_exist)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise StateBindingSuccessorError("v10 state-binding path escaped repository") from exc
    return resolved


def _read(root: Path, relative: Path) -> bytes:
    selected = _logical_path(root, relative, must_exist=True)
    _require(not selected.is_symlink(), f"v10 path is link-like: {relative.as_posix()}")
    before = selected.stat()
    raw = selected.read_bytes()
    after = selected.stat()
    _require(
        (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
        f"v10 path changed while reading: {relative.as_posix()}",
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
        raise StateBindingSuccessorError(
            f"append-only artifact already exists: {relative.as_posix()}"
        ) from exc
    except OSError as exc:
        raise StateBindingSuccessorError(
            f"append-only artifact cannot be written: {relative.as_posix()}"
        ) from exc
    _require(_read(root, relative) == raw, f"artifact reread differs: {relative.as_posix()}")


def _utc(value: datetime, *, label: str) -> datetime:
    _require(value.tzinfo is not None, f"{label} must be timezone-aware")
    _require(value.utcoffset() == UTC.utcoffset(value), f"{label} must be UTC")
    return value


def _canonical(value: FrozenStrictModel) -> bytes:
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


def _derived_id(prefix: str, content_hash: str) -> str:
    return f"{prefix}_{content_hash.removeprefix('sha256:')}"


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
        raise StateBindingSuccessorError("local Git source read failed") from exc
    _require(completed.returncode == 0, "local Git source read failed")
    return completed.stdout


class V9SourceBinding(FrozenStrictModel):
    source_commit: Literal["8678ce9e4fbae426971a90a2f47ad28b5a431885"] = V9_SOURCE_COMMIT
    qualification_commit: Literal["b89f59ef46187ca08b02d047d63ad992c8cb3056"] = (
        V9_QUALIFICATION_COMMIT
    )
    source_tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v9_parent_runtime_integration_implemented: Literal[True] = True
    v9_state_approval_or_attempt_entrypoint_implemented: Literal[False] = False
    v9_state_or_approval_artifact_created: Literal[False] = False


class CurrentStateBindingRule(FrozenStrictModel):
    schema_version: Literal["current-state-binding-rule-v10"] = "current-state-binding-rule-v10"
    claim: Literal["docker-running-and-dotenv-only-openai-api-key-user-attested-v10"] = STATE_CLAIM
    dotenv_exact_key_names: tuple[str, ...] = DOTENV_EXACT_KEY_NAMES
    exact_v10_contract_id_in_statement_required: Literal[True] = True
    exact_v10_source_qualification_hash_in_statement_required: Literal[True] = True
    statement_must_follow_source_qualification: Literal[True] = True
    fixed_statement_template_required: Literal[True] = True
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    independent_verification_completed: Literal[False] = False
    attestation_proves_docker_ready: Literal[False] = False
    attestation_proves_dotenv_membership: Literal[False] = False
    credential_value_allowed: Literal[False] = False
    patchloop_observation_during_binding_allowed: Literal[False] = False
    state_change_evidence_reusable: Literal[False] = False
    separate_exact_approval_required: Literal[True] = True
    generic_continuation_is_exact_attestation_or_approval: Literal[False] = False
    source_or_contract_change_requires_version_bump: Literal[True] = True

    @model_validator(mode="after")
    def validate_exact_keys(self) -> CurrentStateBindingRule:
        if self.dotenv_exact_key_names != DOTENV_EXACT_KEY_NAMES:
            raise ValueError("v10 dotenv key set drifted")
        return self


class StateBindingAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    source_qualification_authorized: Literal[True] = True
    future_exact_attestation_binding_supported: Literal[True] = True
    future_state_evidence_binding_supported: Literal[True] = True
    state_materialization_without_fresh_exact_attestation_authorized: Literal[False] = False
    approval_attempt_or_terminal_creation_authorized: Literal[False] = False
    environment_docker_dotenv_sdk_or_network_observation_authorized: Literal[False] = False
    credential_value_recording_authorized: Literal[False] = False
    docker_image_or_container_mutation_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False
    retry_replacement_or_resume_authorized: Literal[False] = False


class StateBindingSuccessorContract(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-state-binding-successor-contract-v10"] = (
        CONTRACT_SCHEMA_VERSION
    )
    contract_version: Literal["ac-evaluator-v2-sanitized-sdk-bootstrap-state-binding-v10"] = (
        CONTRACT_VERSION
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor: V9SourceBinding
    state_rule: CurrentStateBindingRule
    authority: StateBindingAuthority
    state_materializer_implemented: Literal[True] = True
    approval_or_attempt_entrypoint_implemented: Literal[False] = False
    next_gate: Literal["fresh-exact-user-attestation-and-v10-state-materialization"] = (
        QUALIFICATION_NEXT_GATE
    )
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> StateBindingSuccessorContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected = _hash_body(body)
        if self.content_hash != expected:
            raise ValueError("v10 state-binding contract hash mismatch")
        if self.contract_id != _derived_id("ncpcontract", expected):
            raise ValueError("v10 state-binding contract id mismatch")
        return self


class CurrentStateUserAttestation(FrozenStrictModel):
    schema_version: Literal["current-state-user-attestation-v10"] = (
        "current-state-user-attestation-v10"
    )
    attestation_id: str = Field(pattern=r"^ncpattestation_[0-9a-f]{64}$")
    contract_version: Literal["ac-evaluator-v2-sanitized-sdk-bootstrap-state-binding-v10"] = (
        CONTRACT_VERSION
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    statement_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    claim: Literal["docker-running-and-dotenv-only-openai-api-key-user-attested-v10"] = STATE_CLAIM
    actor: Literal["user"] = "user"
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    docker_desktop_running_reported: Literal[True] = True
    dotenv_exact_key_names_reported: tuple[str, ...] = DOTENV_EXACT_KEY_NAMES
    exact_contract_id_cited: Literal[True] = True
    exact_source_qualification_hash_cited: Literal[True] = True
    state_binding_only: Literal[True] = True
    execution_authority_granted: Literal[False] = False
    independent_verification_completed: Literal[False] = False
    credential_value_observed_or_persisted: Literal[False] = False
    patchloop_external_observation_count: Literal[0] = 0
    patchloop_external_mutation_count: Literal[0] = 0
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v10 attestation recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> CurrentStateUserAttestation:
        if self.dotenv_exact_key_names_reported != DOTENV_EXACT_KEY_NAMES:
            raise ValueError("v10 attestation key set drifted")
        body = self.model_dump(mode="json", exclude={"attestation_id", "content_hash"})
        expected = _hash_body(body)
        if self.content_hash != expected:
            raise ValueError("v10 attestation hash mismatch")
        if self.attestation_id != _derived_id("ncpattestation", expected):
            raise ValueError("v10 attestation id mismatch")
        return self


class CurrentStateEvidence(FrozenStrictModel):
    schema_version: Literal["current-state-change-evidence-v10"] = (
        "current-state-change-evidence-v10"
    )
    evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    contract_version: Literal["ac-evaluator-v2-sanitized-sdk-bootstrap-state-binding-v10"] = (
        CONTRACT_VERSION
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v9_source_commit: Literal["8678ce9e4fbae426971a90a2f47ad28b5a431885"] = V9_SOURCE_COMMIT
    v9_source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    user_attestation_id: str = Field(pattern=r"^ncpattestation_[0-9a-f]{64}$")
    user_attestation_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_kind: Literal["current-state-user-attested-v10"] = "current-state-user-attested-v10"
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    docker_desktop_running_reported: Literal[True] = True
    dotenv_exact_key_names_reported: tuple[str, ...] = DOTENV_EXACT_KEY_NAMES
    independent_verification_completed: Literal[False] = False
    docker_daemon_ready_verified: Literal[False] = False
    dotenv_file_or_membership_verified: Literal[False] = False
    systemroot_presence_or_value_attested: Literal[False] = False
    credential_value_observed_or_persisted: Literal[False] = False
    v9_runtime_source_qualified: Literal[True] = True
    runtime_execution_authorized: Literal[False] = False
    separate_exact_approval_required: Literal[True] = True
    state_change_evidence_reusable: Literal[False] = False
    approval_attempt_or_terminal_created: Literal[False] = False
    patchloop_external_observation_count: Literal[0] = 0
    patchloop_external_mutation_count: Literal[0] = 0
    next_gate: Literal["fresh-exact-v10-approval-successor"] = STATE_NEXT_GATE
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v10 state recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> CurrentStateEvidence:
        if self.dotenv_exact_key_names_reported != DOTENV_EXACT_KEY_NAMES:
            raise ValueError("v10 state key set drifted")
        body = self.model_dump(mode="json", exclude={"evidence_id", "content_hash"})
        expected = _hash_body(body)
        if self.content_hash != expected:
            raise ValueError("v10 state hash mismatch")
        if self.evidence_id != _derived_id("ncpstate", expected):
            raise ValueError("v10 state id mismatch")
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
    def validate_source(self) -> SourceCommitBinding:
        if self.parents != (SOURCE_PARENT_COMMIT,):
            raise ValueError("v10 source predecessor drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v10 source additions drifted")
        return self


class QualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    source_qualified: Literal[True] = True
    user_attestation_created: Literal[False] = False
    state_change_evidence_created: Literal[False] = False
    approval_attempt_or_terminal_created: Literal[False] = False
    environment_docker_dotenv_sdk_network_or_provider_observation_count: Literal[0] = 0
    external_mutation_count: Literal[0] = 0
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class SourceQualification(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-state-binding-source-qualification-v10"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal[
        "ac-evaluator-v2-sanitized-sdk-bootstrap-state-binding-source-20260812-r1"
    ] = QUALIFICATION_ID
    status: Literal["OFFLINE_V10_STATE_BINDING_SOURCE_QUALIFIED_LIVE_CLOSED"] = QUALIFICATION_STATUS
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[CommittedFileBinding, ...]
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    contract_file: CommittedFileBinding
    runtime_file: CommittedFileBinding
    predecessor_contract_file: CommittedFileBinding
    predecessor_runtime_file: CommittedFileBinding
    predecessor_qualification_file: CommittedFileBinding
    predecessor_source_commit: Literal["8678ce9e4fbae426971a90a2f47ad28b5a431885"] = (
        V9_SOURCE_COMMIT
    )
    predecessor_source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authority: QualificationAuthority
    next_gate: Literal["fresh-exact-user-attestation-and-v10-state-materialization"] = (
        QUALIFICATION_NEXT_GATE
    )
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v10 qualification recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> SourceQualification:
        expected_paths = tuple(path.as_posix() for path in SOURCE_FILES)
        if tuple(item.path for item in self.source_files) != expected_paths:
            raise ValueError("v10 qualification inventory drifted")
        by_path = {item.path: item for item in self.source_files}
        for projection, path in (
            (self.contract_file, CONTRACT_PATH),
            (self.runtime_file, RUNTIME_PATH),
            (self.predecessor_contract_file, v9.CONTRACT_PATH),
            (self.predecessor_runtime_file, v9.RUNTIME_PATH),
            (self.predecessor_qualification_file, v9.QUALIFICATION_PATH),
        ):
            if projection != by_path.get(path.as_posix()):
                raise ValueError("v10 qualification projection drifted")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != _hash_body(body):
            raise ValueError("v10 qualification hash mismatch")
        return self


def _load_v9(root: Path) -> tuple[v9.ParentSuccessorContract, v9.SourceQualification]:
    v9.validate_source_qualification(repository=root)
    contract = v9.load_contract(repository=root)
    raw = _read(root, v9.QUALIFICATION_PATH)
    qualification = v9.SourceQualification.model_validate_json(raw)
    _require(raw == _canonical(qualification), "v9 qualification bytes differ")
    _require(
        qualification.source_commit.commit == V9_SOURCE_COMMIT,
        "v9 source commit differs",
    )
    _require(
        _git(root, "show", f"{V9_QUALIFICATION_COMMIT}:{v9.QUALIFICATION_PATH.as_posix()}") == raw,
        "v9 qualification is not bound to its commit",
    )
    return contract, qualification


def _predecessor_binding(root: Path) -> V9SourceBinding:
    contract, qualification = _load_v9(root)
    return V9SourceBinding(
        source_tree=qualification.source_commit.tree,
        contract_id=contract.contract_id,
        contract_content_hash=contract.content_hash,
        source_qualification_hash=qualification.content_hash,
        runtime_file_sha256=qualification.runtime_file.file_sha256,
    )


def _build_contract(root: Path) -> StateBindingSuccessorContract:
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "predecessor": _predecessor_binding(root).model_dump(mode="json"),
        "state_rule": CurrentStateBindingRule().model_dump(mode="json"),
        "authority": StateBindingAuthority().model_dump(mode="json"),
        "state_materializer_implemented": True,
        "approval_or_attempt_entrypoint_implemented": False,
        "next_gate": QUALIFICATION_NEXT_GATE,
    }
    content_hash = _hash_body(body)
    return StateBindingSuccessorContract(
        **body,
        contract_id=_derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def load_contract(*, repository: str | Path | None = None) -> StateBindingSuccessorContract:
    root = _root(repository)
    raw = _read(root, CONTRACT_PATH)
    try:
        value = StateBindingSuccessorContract.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise StateBindingSuccessorError("v10 contract artifact is invalid") from exc
    _require(raw == _canonical(value), "v10 contract bytes are not canonical")
    _require(value == _build_contract(root), "v10 contract has drifted")
    return value


def materialize_contract(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _root(repository)
    selected = _logical_path(root, CONTRACT_PATH, must_exist=False)
    if selected.exists():
        value = load_contract(repository=root)
        raw = _read(root, CONTRACT_PATH)
    else:
        value = _build_contract(root)
        raw = _canonical(value)
        _write_once(root, CONTRACT_PATH, raw)
    return {
        "status": "OFFLINE_V10_STATE_BINDING_CONTRACT_MATERIALIZED_LIVE_CLOSED",
        "contract_id": value.contract_id,
        "contract_content_hash": value.content_hash,
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
    }


def expected_attestation_statement(
    contract: StateBindingSuccessorContract,
    qualification: SourceQualification,
) -> str:
    contract = StateBindingSuccessorContract.model_validate(contract.model_dump(mode="json"))
    qualification = SourceQualification.model_validate(qualification.model_dump(mode="json"))
    _require(qualification.contract_id == contract.contract_id, "qualification contract differs")
    _require(
        qualification.contract_content_hash == contract.content_hash,
        "qualification contract hash differs",
    )
    return ATTESTATION_TEMPLATE.format(
        contract_id=contract.contract_id,
        qualification_hash=qualification.content_hash,
    )


def build_user_attestation(
    contract: StateBindingSuccessorContract,
    qualification: SourceQualification,
    *,
    statement: str,
    recorded_at: datetime,
) -> CurrentStateUserAttestation:
    contract = StateBindingSuccessorContract.model_validate(contract.model_dump(mode="json"))
    qualification = SourceQualification.model_validate(qualification.model_dump(mode="json"))
    expected = expected_attestation_statement(contract, qualification)
    _require(statement == expected, "fresh v10 attestation statement differs")
    recorded_at = _utc(recorded_at, label="v10 attestation recorded_at")
    _require(recorded_at >= qualification.recorded_at, "attestation predates qualification")
    body = {
        "schema_version": "current-state-user-attestation-v10",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "source_qualification_content_hash": qualification.content_hash,
        "statement_sha256": sha256_bytes(statement.encode("utf-8")),
        "claim": STATE_CLAIM,
        "actor": "user",
        "identity_assurance": IDENTITY_ASSURANCE,
        "docker_desktop_running_reported": True,
        "dotenv_exact_key_names_reported": DOTENV_EXACT_KEY_NAMES,
        "exact_contract_id_cited": True,
        "exact_source_qualification_hash_cited": True,
        "state_binding_only": True,
        "execution_authority_granted": False,
        "independent_verification_completed": False,
        "credential_value_observed_or_persisted": False,
        "patchloop_external_observation_count": 0,
        "patchloop_external_mutation_count": 0,
        "recorded_at": recorded_at,
    }
    content_hash = _hash_body(body)
    return CurrentStateUserAttestation(
        **body,
        attestation_id=_derived_id("ncpattestation", content_hash),
        content_hash=content_hash,
    )


def bind_state_evidence(
    contract: StateBindingSuccessorContract,
    qualification: SourceQualification,
    attestation: CurrentStateUserAttestation,
    *,
    recorded_at: datetime,
) -> CurrentStateEvidence:
    contract = StateBindingSuccessorContract.model_validate(contract.model_dump(mode="json"))
    qualification = SourceQualification.model_validate(qualification.model_dump(mode="json"))
    attestation = CurrentStateUserAttestation.model_validate(attestation.model_dump(mode="json"))
    _require(attestation.contract_id == contract.contract_id, "attestation contract differs")
    _require(
        attestation.source_qualification_content_hash == qualification.content_hash,
        "attestation qualification differs",
    )
    recorded_at = _utc(recorded_at, label="v10 state recorded_at")
    _require(recorded_at >= attestation.recorded_at, "state predates attestation")
    body = {
        "schema_version": "current-state-change-evidence-v10",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "source_qualification_content_hash": qualification.content_hash,
        "v9_source_commit": contract.predecessor.source_commit,
        "v9_source_qualification_hash": contract.predecessor.source_qualification_hash,
        "user_attestation_id": attestation.attestation_id,
        "user_attestation_content_hash": attestation.content_hash,
        "evidence_kind": "current-state-user-attested-v10",
        "identity_assurance": IDENTITY_ASSURANCE,
        "docker_desktop_running_reported": True,
        "dotenv_exact_key_names_reported": DOTENV_EXACT_KEY_NAMES,
        "independent_verification_completed": False,
        "docker_daemon_ready_verified": False,
        "dotenv_file_or_membership_verified": False,
        "systemroot_presence_or_value_attested": False,
        "credential_value_observed_or_persisted": False,
        "v9_runtime_source_qualified": True,
        "runtime_execution_authorized": False,
        "separate_exact_approval_required": True,
        "state_change_evidence_reusable": False,
        "approval_attempt_or_terminal_created": False,
        "patchloop_external_observation_count": 0,
        "patchloop_external_mutation_count": 0,
        "next_gate": STATE_NEXT_GATE,
        "recorded_at": recorded_at,
    }
    content_hash = _hash_body(body)
    return CurrentStateEvidence(
        **body,
        evidence_id=_derived_id("ncpstate", content_hash),
        content_hash=content_hash,
    )


def _source_commit(root: Path, selected: str) -> SourceCommitBinding:
    commit = _git(root, "rev-parse", f"{selected}^{{commit}}").decode("ascii").strip()
    tree = _git(root, "rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    row = _git(root, "rev-list", "--parents", "-n", "1", commit).decode("ascii").split()
    _require(row and row[0] == commit and len(row) == 2, "v10 source parent binding failed")
    lines = (
        _git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", row[1], commit)
        .decode("utf-8")
        .splitlines()
    )
    added = tuple(sorted(parts[1] for line in lines if (parts := line.split("\t"))[:1] == ["A"]))
    _require(len(lines) == len(added), "v10 source commit contains non-addition changes")
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
    root: Path,
    *,
    source_commit: str,
    recorded_at: datetime,
) -> SourceQualification:
    contract = load_contract(repository=root)
    _, predecessor = _load_v9(root)
    commit = _source_commit(root, source_commit)
    pairs = tuple(_committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(pair[0] for pair in pairs)
    by_path = {item.path: item for item in files}
    contract_index = SOURCE_FILES.index(CONTRACT_PATH)
    _require(pairs[contract_index][1] == _canonical(contract), "committed v10 contract differs")
    body = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": QUALIFICATION_STATUS,
        "recorded_at": _utc(recorded_at, label="v10 qualification recorded_at"),
        "source_commit": commit.model_dump(mode="json"),
        "source_files": tuple(item.model_dump(mode="json") for item in files),
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "contract_file": by_path[CONTRACT_PATH.as_posix()].model_dump(mode="json"),
        "runtime_file": by_path[RUNTIME_PATH.as_posix()].model_dump(mode="json"),
        "predecessor_contract_file": by_path[v9.CONTRACT_PATH.as_posix()].model_dump(mode="json"),
        "predecessor_runtime_file": by_path[v9.RUNTIME_PATH.as_posix()].model_dump(mode="json"),
        "predecessor_qualification_file": by_path[v9.QUALIFICATION_PATH.as_posix()].model_dump(
            mode="json"
        ),
        "predecessor_source_commit": V9_SOURCE_COMMIT,
        "predecessor_source_qualification_hash": predecessor.content_hash,
        "authority": QualificationAuthority().model_dump(mode="json"),
        "next_gate": QUALIFICATION_NEXT_GATE,
    }
    return SourceQualification(**body, content_hash=_hash_body(body))


def qualify_source(
    *,
    source_commit: str = "HEAD",
    repository: str | Path | None = None,
) -> dict[str, Any]:
    root = _root(repository)
    target = _logical_path(root, QUALIFICATION_PATH, must_exist=False)
    if not target.exists():
        value = _build_qualification(
            root,
            source_commit=source_commit,
            recorded_at=datetime.now(UTC),
        )
        _write_once(root, QUALIFICATION_PATH, _canonical(value))
    return validate_source_qualification(repository=root)


def validate_source_qualification(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _root(repository)
    raw = _read(root, QUALIFICATION_PATH)
    try:
        value = SourceQualification.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise StateBindingSuccessorError("v10 source qualification is invalid") from exc
    _require(raw == _canonical(value), "v10 qualification bytes are not canonical")
    expected = _build_qualification(
        root,
        source_commit=value.source_commit.commit,
        recorded_at=value.recorded_at,
    )
    _require(value == expected, "v10 source qualification has drifted")
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
        "user_attestation_created": False,
        "state_change_evidence_created": False,
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
        "next_gate": QUALIFICATION_NEXT_GATE,
    }


def _load_qualification(root: Path) -> SourceQualification:
    validate_source_qualification(repository=root)
    return SourceQualification.model_validate_json(_read(root, QUALIFICATION_PATH))


def record_current_state(
    *,
    statement: str,
    recorded_at: datetime,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Bind one exact post-qualification user statement; perform no observation."""

    root = _root(repository)
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    _require(
        not _logical_path(root, USER_ATTESTATION_PATH, must_exist=False).exists(),
        "v10 user attestation already exists",
    )
    _require(
        not _logical_path(root, STATE_EVIDENCE_PATH, must_exist=False).exists(),
        "v10 state evidence already exists",
    )
    attestation = build_user_attestation(
        contract,
        qualification,
        statement=statement,
        recorded_at=recorded_at,
    )
    state = bind_state_evidence(
        contract,
        qualification,
        attestation,
        recorded_at=recorded_at,
    )
    attestation_raw = _canonical(attestation)
    state_raw = _canonical(state)
    combined = (attestation_raw + state_raw).lower()
    _require(b"openai_api_key=" not in combined, "credential assignment bytes are forbidden")
    _require(b"sk-" not in combined, "credential-like bytes are forbidden")
    _write_once(root, USER_ATTESTATION_PATH, attestation_raw)
    _write_once(root, STATE_EVIDENCE_PATH, state_raw)
    return validate_current_state(repository=root)


def validate_current_state(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _root(repository)
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    attestation_raw = _read(root, USER_ATTESTATION_PATH)
    state_raw = _read(root, STATE_EVIDENCE_PATH)
    try:
        attestation = CurrentStateUserAttestation.model_validate_json(attestation_raw)
        state = CurrentStateEvidence.model_validate_json(state_raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise StateBindingSuccessorError("v10 state artifact is invalid") from exc
    _require(attestation_raw == _canonical(attestation), "v10 attestation bytes are not canonical")
    _require(state_raw == _canonical(state), "v10 state bytes are not canonical")
    expected = bind_state_evidence(
        contract,
        qualification,
        attestation,
        recorded_at=state.recorded_at,
    )
    _require(state == expected, "v10 state does not bind exact attestation")
    return {
        "status": "V10_CURRENT_STATE_USER_ATTESTED_APPROVAL_SUCCESSOR_REQUIRED",
        "contract_id": contract.contract_id,
        "source_qualification_hash": qualification.content_hash,
        "attestation_id": attestation.attestation_id,
        "state_change_evidence_id": state.evidence_id,
        "state_change_evidence_content_hash": state.content_hash,
        "identity_assurance": IDENTITY_ASSURANCE,
        "docker_daemon_ready_verified": False,
        "dotenv_file_or_membership_verified": False,
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
        "next_gate": STATE_NEXT_GATE,
    }


__all__ = [
    "ATTESTATION_TEMPLATE",
    "BUILD_SCRIPT_PATH",
    "CONTRACT_PATH",
    "CurrentStateEvidence",
    "CurrentStateUserAttestation",
    "QUALIFICATION_PATH",
    "RUNTIME_PATH",
    "SOURCE_ADDED_PATHS",
    "SOURCE_FILES",
    "STATE_EVIDENCE_PATH",
    "StateBindingSuccessorContract",
    "StateBindingSuccessorError",
    "SourceQualification",
    "TEST_PATH",
    "USER_ATTESTATION_PATH",
    "bind_state_evidence",
    "build_user_attestation",
    "expected_attestation_statement",
    "load_contract",
    "materialize_contract",
    "qualify_source",
    "record_current_state",
    "validate_current_state",
    "validate_source_qualification",
]
