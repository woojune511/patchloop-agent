"""Offline v11 exact-approval successor over the sealed v10 state.

Source qualification creates no approval or attempt.  A later exact user
statement can create one append-only approval pair for the exact v9 runtime,
but this module exposes no Docker, dotenv, SDK, network, or attempt executor.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from patchloop.contracts import FrozenStrictModel
from patchloop.errors import ContractError
from patchloop.evals import sanitized_sdk_bootstrap_parent_successor as v9
from patchloop.evals import sanitized_sdk_bootstrap_state_binding_successor as v10
from patchloop.util import sha256_bytes

CONTRACT_SCHEMA_VERSION = "sanitized-sdk-bootstrap-approval-successor-contract-v11"
CONTRACT_VERSION = "ac-evaluator-v2-sanitized-sdk-bootstrap-approval-v11"
CONTRACT_PATH = Path("experiments/evaluator-v2-sanitized-sdk-bootstrap-approval-v11.contract.json")
RUNTIME_PATH = Path("patchloop/evals/sanitized_sdk_bootstrap_approval_successor.py")
BUILD_SCRIPT_PATH = Path("scripts/build_sanitized_sdk_bootstrap_approval_successor.py")
TEST_PATH = Path("tests/test_sanitized_sdk_bootstrap_approval_successor.py")

SOURCE_PARENT_COMMIT = "f05c23e5e1d158bc4cce47840655ead34228f28a"
V10_SOURCE_COMMIT = "3190923f97883e7df4bb53b9b8231c3598239fb1"
V10_QUALIFICATION_COMMIT = "12e0927afdb651a07cc8e25abc0362d373ac48d0"
V10_STATE_EVIDENCE_COMMIT = "5ab4226bfc5017563b673375f9057fde39b1c38c"

QUALIFICATION_SCHEMA_VERSION = "sanitized-sdk-bootstrap-approval-source-qualification-v11"
QUALIFICATION_ID = "ac-evaluator-v2-sanitized-sdk-bootstrap-approval-source-20260812-r1"
QUALIFICATION_STATUS = "OFFLINE_V11_APPROVAL_SOURCE_QUALIFIED_EXACT_APPROVAL_REQUIRED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-bootstrap-approval-v11-source-qualification.json"
)
APPROVAL_RECEIPT_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-bootstrap-approval-v11-exact-approval-receipt.json"
)
APPROVAL_BINDING_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-bootstrap-approval-v11-approval-binding.json"
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
            v10.CONTRACT_PATH,
            v10.RUNTIME_PATH,
            v10.QUALIFICATION_PATH,
            v10.USER_ATTESTATION_PATH,
            v10.STATE_EVIDENCE_PATH,
        ),
        key=lambda path: path.as_posix(),
    )
)

IDENTITY_ASSURANCE = v10.IDENTITY_ASSURANCE
APPROVED_RUNTIME = "patchloop.evals.sanitized_sdk_bootstrap_parent_successor.run_parent_preflight"
APPROVED_SCOPES = (
    "v9-contract-and-source-validation-before-observation",
    "docker-read-only-two-snapshot-eight-command-observation",
    "isolated-dotenv-exact-openai-api-key-membership",
    "sanitized-sdk-fixed-placeholder-reject-dispatch-with-child-only-systemroot",
)
APPROVAL_TEMPLATE = (
    "Contract {contract_id}, source qualification {qualification_hash}, state {state_id} "
    "({state_hash}): approve exactly one future v9 no-call preflight under the fixed v11 "
    "scopes; current Docker-running and repository-root .env-only-OPENAI_API_KEY report is "
    "reconfirmed; approval-binding-only, no attempt now; no credential value recording, "
    "Docker start/pull/load/image-store mutation/container operation, network/transport, "
    "provider/evaluator/agent, candidate/cost/paid execution, retry/replacement/resume."
)
QUALIFICATION_NEXT_GATE = "fresh-exact-v11-user-approval-and-binding"
APPROVAL_NEXT_GATE = "qualified-v11-attempt-lifecycle-successor"


class ApprovalSuccessorError(ContractError):
    """The offline v11 approval successor failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ApprovalSuccessorError(message)


def _utc(value: datetime, *, label: str) -> datetime:
    _require(value.tzinfo is not None, f"{label} must be timezone-aware")
    _require(value.utcoffset() == UTC.utcoffset(value), f"{label} must be UTC")
    return value


class V10StateBinding(FrozenStrictModel):
    source_commit: Literal["3190923f97883e7df4bb53b9b8231c3598239fb1"] = V10_SOURCE_COMMIT
    qualification_commit: Literal["12e0927afdb651a07cc8e25abc0362d373ac48d0"] = (
        V10_QUALIFICATION_COMMIT
    )
    state_evidence_commit: Literal["5ab4226bfc5017563b673375f9057fde39b1c38c"] = (
        V10_STATE_EVIDENCE_COMMIT
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    user_attestation_id: str = Field(pattern=r"^ncpattestation_[0-9a-f]{64}$")
    user_attestation_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    user_attestation_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_change_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_change_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_change_evidence_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v9_source_commit: Literal["8678ce9e4fbae426971a90a2f47ad28b5a431885"] = v10.V9_SOURCE_COMMIT
    v9_source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    independent_verification_completed: Literal[False] = False
    docker_daemon_ready_verified: Literal[False] = False
    dotenv_file_or_membership_verified: Literal[False] = False
    state_change_evidence_reusable: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    approval_attempt_or_terminal_created: Literal[False] = False
    external_observation_count: Literal[0] = 0
    external_mutation_count: Literal[0] = 0


class ApprovedRuntimeBinding(FrozenStrictModel):
    entrypoint: Literal[
        "patchloop.evals.sanitized_sdk_bootstrap_parent_successor.run_parent_preflight"
    ] = APPROVED_RUNTIME
    v9_source_commit: Literal["8678ce9e4fbae426971a90a2f47ad28b5a431885"] = v10.V9_SOURCE_COMMIT
    v9_contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    v9_contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v9_source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v9_runtime_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    docker_expected_command_count: Literal[8] = 8
    diagnostic_child_limit: Literal[1] = 1
    transport_dispatch_limit: Literal[1] = 1
    network_call_limit: Literal[0] = 0
    provider_evaluator_agent_call_limit: Literal[0] = 0
    credential_value_record_hash_prefix_or_length_limit: Literal[0] = 0
    systemroot_value_record_hash_prefix_or_length_limit: Literal[0] = 0

    @model_validator(mode="after")
    def validate_scopes(self) -> ApprovedRuntimeBinding:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("v11 approved runtime scopes drifted")
        return self


class ExactApprovalRule(FrozenStrictModel):
    schema_version: Literal["exact-approval-rule-v11"] = "exact-approval-rule-v11"
    exact_contract_id_in_statement_required: Literal[True] = True
    exact_source_qualification_hash_in_statement_required: Literal[True] = True
    exact_state_id_and_hash_in_statement_required: Literal[True] = True
    statement_must_follow_source_qualification: Literal[True] = True
    fixed_statement_template_required: Literal[True] = True
    state_reconfirmation_required: Literal[True] = True
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    attempt_limit: Literal[1] = 1
    approval_reusable: Literal[False] = False
    state_reusable: Literal[False] = False
    approval_materialization_is_attempt_start: Literal[False] = False
    attempt_lifecycle_successor_required: Literal[True] = True
    generic_continuation_is_exact_approval: Literal[False] = False
    credential_value_allowed: Literal[False] = False
    retry_replacement_or_resume_allowed: Literal[False] = False

    @model_validator(mode="after")
    def validate_scopes(self) -> ExactApprovalRule:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("v11 approval rule scopes drifted")
        return self


class ApprovalSourceAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    source_qualification_authorized: Literal[True] = True
    future_exact_approval_binding_supported: Literal[True] = True
    approval_creation_during_source_qualification_authorized: Literal[False] = False
    attempt_or_terminal_creation_authorized: Literal[False] = False
    environment_docker_dotenv_sdk_or_network_observation_authorized: Literal[False] = False
    credential_value_recording_authorized: Literal[False] = False
    docker_image_or_container_mutation_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False
    retry_replacement_or_resume_authorized: Literal[False] = False


class ApprovalSuccessorContract(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-approval-successor-contract-v11"] = (
        CONTRACT_SCHEMA_VERSION
    )
    contract_version: Literal["ac-evaluator-v2-sanitized-sdk-bootstrap-approval-v11"] = (
        CONTRACT_VERSION
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor: V10StateBinding
    approved_runtime: ApprovedRuntimeBinding
    approval_rule: ExactApprovalRule
    authority: ApprovalSourceAuthority
    approval_materializer_implemented: Literal[True] = True
    attempt_entrypoint_implemented: Literal[False] = False
    next_gate: Literal["fresh-exact-v11-user-approval-and-binding"] = QUALIFICATION_NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> ApprovalSuccessorContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected:
            raise ValueError("v11 approval contract hash mismatch")
        if self.contract_id != v10._derived_id("ncpcontract", expected):
            raise ValueError("v11 approval contract id mismatch")
        return self


class UserExactApprovalReceipt(FrozenStrictModel):
    schema_version: Literal["user-exact-approval-receipt-v11"] = "user-exact-approval-receipt-v11"
    receipt_id: str = Field(pattern=r"^ncpapprovalreceipt_[0-9a-f]{64}$")
    contract_version: Literal["ac-evaluator-v2-sanitized-sdk-bootstrap-approval-v11"] = (
        CONTRACT_VERSION
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_change_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_change_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    statement_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_runtime: Literal[
        "patchloop.evals.sanitized_sdk_bootstrap_parent_successor.run_parent_preflight"
    ] = APPROVED_RUNTIME
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    current_state_report_reconfirmed: Literal[True] = True
    attempt_limit: Literal[1] = 1
    approval_reusable: Literal[False] = False
    state_reusable: Literal[False] = False
    approval_binding_only: Literal[True] = True
    attempt_started: Literal[False] = False
    attempt_lifecycle_successor_required: Literal[True] = True
    credential_value_in_approval: Literal[False] = False
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
            raise ValueError("v11 approval receipt recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> UserExactApprovalReceipt:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("v11 approval receipt scopes drifted")
        body = self.model_dump(mode="json", exclude={"receipt_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected:
            raise ValueError("v11 approval receipt hash mismatch")
        if self.receipt_id != v10._derived_id("ncpapprovalreceipt", expected):
            raise ValueError("v11 approval receipt id mismatch")
        return self


class ExactApprovalBinding(FrozenStrictModel):
    schema_version: Literal["exact-approval-binding-v11"] = "exact-approval-binding-v11"
    approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    contract_version: Literal["ac-evaluator-v2-sanitized-sdk-bootstrap-approval-v11"] = (
        CONTRACT_VERSION
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_change_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    state_change_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    user_approval_receipt_id: str = Field(pattern=r"^ncpapprovalreceipt_[0-9a-f]{64}$")
    user_approval_receipt_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_runtime: Literal[
        "patchloop.evals.sanitized_sdk_bootstrap_parent_successor.run_parent_preflight"
    ] = APPROVED_RUNTIME
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    identity_assurance: Literal["current-user-self-attested-not-authenticated-or-signed"] = (
        IDENTITY_ASSURANCE
    )
    attempt_limit: Literal[1] = 1
    approval_reusable: Literal[False] = False
    state_reusable: Literal[False] = False
    attempt_started: Literal[False] = False
    attempt_consumed: Literal[False] = False
    attempt_entrypoint_available: Literal[False] = False
    attempt_lifecycle_successor_required: Literal[True] = True
    network_or_transport_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False
    retry_replacement_or_resume_authorized: Literal[False] = False
    next_gate: Literal["qualified-v11-attempt-lifecycle-successor"] = APPROVAL_NEXT_GATE
    recorded_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v11 approval binding recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> ExactApprovalBinding:
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("v11 approval binding scopes drifted")
        body = self.model_dump(mode="json", exclude={"approval_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected:
            raise ValueError("v11 approval binding hash mismatch")
        if self.approval_id != v10._derived_id("ncpapproval", expected):
            raise ValueError("v11 approval binding id mismatch")
        return self


class SourceCommitBinding(FrozenStrictModel):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    parents: tuple[str, ...]
    added_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_source(self) -> SourceCommitBinding:
        if self.parents != (SOURCE_PARENT_COMMIT,):
            raise ValueError("v11 source predecessor drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v11 source additions drifted")
        return self


class QualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    source_qualified: Literal[True] = True
    approval_receipt_or_binding_created: Literal[False] = False
    attempt_or_terminal_created: Literal[False] = False
    environment_docker_dotenv_sdk_network_or_provider_observation_count: Literal[0] = 0
    external_mutation_count: Literal[0] = 0
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class SourceQualification(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-approval-source-qualification-v11"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal[
        "ac-evaluator-v2-sanitized-sdk-bootstrap-approval-source-20260812-r1"
    ] = QUALIFICATION_ID
    status: Literal["OFFLINE_V11_APPROVAL_SOURCE_QUALIFIED_EXACT_APPROVAL_REQUIRED"] = (
        QUALIFICATION_STATUS
    )
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[v10.CommittedFileBinding, ...]
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    contract_file: v10.CommittedFileBinding
    runtime_file: v10.CommittedFileBinding
    predecessor_contract_file: v10.CommittedFileBinding
    predecessor_qualification_file: v10.CommittedFileBinding
    predecessor_attestation_file: v10.CommittedFileBinding
    predecessor_state_file: v10.CommittedFileBinding
    predecessor_state_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    predecessor_state_evidence_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authority: QualificationAuthority
    next_gate: Literal["fresh-exact-v11-user-approval-and-binding"] = QUALIFICATION_NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v11 qualification recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> SourceQualification:
        expected_paths = tuple(path.as_posix() for path in SOURCE_FILES)
        if tuple(item.path for item in self.source_files) != expected_paths:
            raise ValueError("v11 qualification inventory drifted")
        by_path = {item.path: item for item in self.source_files}
        for projection, path in (
            (self.contract_file, CONTRACT_PATH),
            (self.runtime_file, RUNTIME_PATH),
            (self.predecessor_contract_file, v10.CONTRACT_PATH),
            (self.predecessor_qualification_file, v10.QUALIFICATION_PATH),
            (self.predecessor_attestation_file, v10.USER_ATTESTATION_PATH),
            (self.predecessor_state_file, v10.STATE_EVIDENCE_PATH),
        ):
            if projection != by_path.get(path.as_posix()):
                raise ValueError("v11 qualification projection drifted")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != v10._hash_body(body):
            raise ValueError("v11 qualification hash mismatch")
        return self


def _load_v10(
    root: Path,
) -> tuple[
    v10.StateBindingSuccessorContract,
    v10.SourceQualification,
    v10.CurrentStateUserAttestation,
    v10.CurrentStateEvidence,
    bytes,
    bytes,
]:
    v10.validate_current_state(repository=root)
    contract = v10.load_contract(repository=root)
    qualification_raw = v10._read(root, v10.QUALIFICATION_PATH)
    attestation_raw = v10._read(root, v10.USER_ATTESTATION_PATH)
    state_raw = v10._read(root, v10.STATE_EVIDENCE_PATH)
    qualification = v10.SourceQualification.model_validate_json(qualification_raw)
    attestation = v10.CurrentStateUserAttestation.model_validate_json(attestation_raw)
    state = v10.CurrentStateEvidence.model_validate_json(state_raw)
    _require(
        qualification.source_commit.commit == V10_SOURCE_COMMIT,
        "v10 source commit differs",
    )
    _require(
        v10._git(
            root,
            "show",
            f"{V10_QUALIFICATION_COMMIT}:{v10.QUALIFICATION_PATH.as_posix()}",
        )
        == qualification_raw,
        "v10 qualification is not bound to its commit",
    )
    for path, raw in (
        (v10.USER_ATTESTATION_PATH, attestation_raw),
        (v10.STATE_EVIDENCE_PATH, state_raw),
    ):
        _require(
            v10._git(root, "show", f"{V10_STATE_EVIDENCE_COMMIT}:{path.as_posix()}") == raw,
            "v10 state chain is not bound to its evidence commit",
        )
    return contract, qualification, attestation, state, attestation_raw, state_raw


def _predecessor_binding(root: Path) -> V10StateBinding:
    contract, qualification, attestation, state, attestation_raw, state_raw = _load_v10(root)
    return V10StateBinding(
        contract_id=contract.contract_id,
        contract_content_hash=contract.content_hash,
        source_qualification_hash=qualification.content_hash,
        user_attestation_id=attestation.attestation_id,
        user_attestation_content_hash=attestation.content_hash,
        user_attestation_file_sha256=sha256_bytes(attestation_raw),
        state_change_evidence_id=state.evidence_id,
        state_change_evidence_content_hash=state.content_hash,
        state_change_evidence_file_sha256=sha256_bytes(state_raw),
        v9_source_qualification_hash=state.v9_source_qualification_hash,
    )


def _approved_runtime(root: Path, predecessor: V10StateBinding) -> ApprovedRuntimeBinding:
    v9_contract = v9.load_contract(repository=root)
    v9_qualification_raw = v10._read(root, v9.QUALIFICATION_PATH)
    v9_qualification = v9.SourceQualification.model_validate_json(v9_qualification_raw)
    _require(
        v9_qualification.content_hash == predecessor.v9_source_qualification_hash,
        "v9 qualification differs from v10 state",
    )
    return ApprovedRuntimeBinding(
        v9_contract_id=v9_contract.contract_id,
        v9_contract_content_hash=v9_contract.content_hash,
        v9_source_qualification_hash=v9_qualification.content_hash,
        v9_runtime_file_sha256=v9_qualification.runtime_file.file_sha256,
    )


def _build_contract(root: Path) -> ApprovalSuccessorContract:
    predecessor = _predecessor_binding(root)
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "predecessor": predecessor.model_dump(mode="json"),
        "approved_runtime": _approved_runtime(root, predecessor).model_dump(mode="json"),
        "approval_rule": ExactApprovalRule().model_dump(mode="json"),
        "authority": ApprovalSourceAuthority().model_dump(mode="json"),
        "approval_materializer_implemented": True,
        "attempt_entrypoint_implemented": False,
        "next_gate": QUALIFICATION_NEXT_GATE,
    }
    content_hash = v10._hash_body(body)
    return ApprovalSuccessorContract(
        **body,
        contract_id=v10._derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def load_contract(*, repository: str | Path | None = None) -> ApprovalSuccessorContract:
    root = v10._root(repository)
    raw = v10._read(root, CONTRACT_PATH)
    try:
        value = ApprovalSuccessorContract.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise ApprovalSuccessorError("v11 contract artifact is invalid") from exc
    _require(raw == v10._canonical(value), "v11 contract bytes are not canonical")
    _require(value == _build_contract(root), "v11 contract has drifted")
    return value


def materialize_contract(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    selected = v10._logical_path(root, CONTRACT_PATH, must_exist=False)
    if selected.exists():
        value = load_contract(repository=root)
        raw = v10._read(root, CONTRACT_PATH)
    else:
        value = _build_contract(root)
        raw = v10._canonical(value)
        v10._write_once(root, CONTRACT_PATH, raw)
    return {
        "status": "OFFLINE_V11_APPROVAL_CONTRACT_MATERIALIZED_LIVE_CLOSED",
        "contract_id": value.contract_id,
        "contract_content_hash": value.content_hash,
        "state_change_evidence_id": value.predecessor.state_change_evidence_id,
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "approval_created": False,
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
    }


def _source_commit(root: Path, selected: str) -> SourceCommitBinding:
    commit = v10._git(root, "rev-parse", f"{selected}^{{commit}}").decode("ascii").strip()
    tree = v10._git(root, "rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    row = v10._git(root, "rev-list", "--parents", "-n", "1", commit).decode("ascii").split()
    _require(row and row[0] == commit and len(row) == 2, "v11 source parent binding failed")
    lines = (
        v10._git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", row[1], commit)
        .decode("utf-8")
        .splitlines()
    )
    added = tuple(sorted(parts[1] for line in lines if (parts := line.split("\t"))[:1] == ["A"]))
    _require(len(lines) == len(added), "v11 source commit contains non-addition changes")
    return SourceCommitBinding(commit=commit, tree=tree, parents=(row[1],), added_paths=added)


def _build_qualification(
    root: Path,
    *,
    source_commit: str,
    recorded_at: datetime,
) -> SourceQualification:
    contract = load_contract(repository=root)
    commit = _source_commit(root, source_commit)
    pairs = tuple(v10._committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(pair[0] for pair in pairs)
    by_path = {item.path: item for item in files}
    contract_index = SOURCE_FILES.index(CONTRACT_PATH)
    _require(pairs[contract_index][1] == v10._canonical(contract), "committed v11 contract differs")
    body = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": QUALIFICATION_STATUS,
        "recorded_at": _utc(recorded_at, label="v11 qualification recorded_at"),
        "source_commit": commit.model_dump(mode="json"),
        "source_files": tuple(item.model_dump(mode="json") for item in files),
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "contract_file": by_path[CONTRACT_PATH.as_posix()].model_dump(mode="json"),
        "runtime_file": by_path[RUNTIME_PATH.as_posix()].model_dump(mode="json"),
        "predecessor_contract_file": by_path[v10.CONTRACT_PATH.as_posix()].model_dump(mode="json"),
        "predecessor_qualification_file": by_path[v10.QUALIFICATION_PATH.as_posix()].model_dump(
            mode="json"
        ),
        "predecessor_attestation_file": by_path[v10.USER_ATTESTATION_PATH.as_posix()].model_dump(
            mode="json"
        ),
        "predecessor_state_file": by_path[v10.STATE_EVIDENCE_PATH.as_posix()].model_dump(
            mode="json"
        ),
        "predecessor_state_evidence_id": contract.predecessor.state_change_evidence_id,
        "predecessor_state_evidence_content_hash": (
            contract.predecessor.state_change_evidence_content_hash
        ),
        "authority": QualificationAuthority().model_dump(mode="json"),
        "next_gate": QUALIFICATION_NEXT_GATE,
    }
    return SourceQualification(**body, content_hash=v10._hash_body(body))


def qualify_source(
    *,
    source_commit: str = "HEAD",
    repository: str | Path | None = None,
) -> dict[str, Any]:
    root = v10._root(repository)
    target = v10._logical_path(root, QUALIFICATION_PATH, must_exist=False)
    if not target.exists():
        value = _build_qualification(
            root,
            source_commit=source_commit,
            recorded_at=datetime.now(UTC),
        )
        v10._write_once(root, QUALIFICATION_PATH, v10._canonical(value))
    return validate_source_qualification(repository=root)


def validate_source_qualification(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    raw = v10._read(root, QUALIFICATION_PATH)
    try:
        value = SourceQualification.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise ApprovalSuccessorError("v11 source qualification is invalid") from exc
    _require(raw == v10._canonical(value), "v11 qualification bytes are not canonical")
    expected = _build_qualification(
        root,
        source_commit=value.source_commit.commit,
        recorded_at=value.recorded_at,
    )
    _require(value == expected, "v11 source qualification has drifted")
    return {
        "status": value.status,
        "qualification_id": value.qualification_id,
        "source_commit": value.source_commit.commit,
        "source_tree": value.source_commit.tree,
        "contract_id": value.contract_id,
        "contract_content_hash": value.contract_content_hash,
        "source_qualification_hash": value.content_hash,
        "state_change_evidence_id": value.predecessor_state_evidence_id,
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "approval_created": False,
        "attempt_created": False,
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
        "next_gate": QUALIFICATION_NEXT_GATE,
    }


def _load_qualification(root: Path) -> SourceQualification:
    validate_source_qualification(repository=root)
    return SourceQualification.model_validate_json(v10._read(root, QUALIFICATION_PATH))


def expected_approval_statement(
    contract: ApprovalSuccessorContract,
    qualification: SourceQualification,
) -> str:
    contract = ApprovalSuccessorContract.model_validate(contract.model_dump(mode="json"))
    qualification = SourceQualification.model_validate(qualification.model_dump(mode="json"))
    _require(qualification.contract_id == contract.contract_id, "qualification contract differs")
    return APPROVAL_TEMPLATE.format(
        contract_id=contract.contract_id,
        qualification_hash=qualification.content_hash,
        state_id=contract.predecessor.state_change_evidence_id,
        state_hash=contract.predecessor.state_change_evidence_content_hash,
    )


def build_user_approval_receipt(
    contract: ApprovalSuccessorContract,
    qualification: SourceQualification,
    *,
    statement: str,
    recorded_at: datetime,
) -> UserExactApprovalReceipt:
    contract = ApprovalSuccessorContract.model_validate(contract.model_dump(mode="json"))
    qualification = SourceQualification.model_validate(qualification.model_dump(mode="json"))
    expected = expected_approval_statement(contract, qualification)
    _require(statement == expected, "fresh v11 approval statement differs")
    recorded_at = _utc(recorded_at, label="v11 approval receipt recorded_at")
    _require(recorded_at >= qualification.recorded_at, "approval predates qualification")
    body = {
        "schema_version": "user-exact-approval-receipt-v11",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "source_qualification_content_hash": qualification.content_hash,
        "state_change_evidence_id": contract.predecessor.state_change_evidence_id,
        "state_change_evidence_content_hash": (
            contract.predecessor.state_change_evidence_content_hash
        ),
        "statement_sha256": sha256_bytes(statement.encode("utf-8")),
        "approved_runtime": APPROVED_RUNTIME,
        "approved_scopes": APPROVED_SCOPES,
        "identity_assurance": IDENTITY_ASSURANCE,
        "current_state_report_reconfirmed": True,
        "attempt_limit": 1,
        "approval_reusable": False,
        "state_reusable": False,
        "approval_binding_only": True,
        "attempt_started": False,
        "attempt_lifecycle_successor_required": True,
        "credential_value_in_approval": False,
        "network_or_transport_authorized": False,
        "provider_evaluator_agent_execution_authorized": False,
        "candidate_cost_or_paid_execution_authorized": False,
        "retry_replacement_or_resume_authorized": False,
        "recorded_at": recorded_at,
    }
    content_hash = v10._hash_body(body)
    return UserExactApprovalReceipt(
        **body,
        receipt_id=v10._derived_id("ncpapprovalreceipt", content_hash),
        content_hash=content_hash,
    )


def bind_exact_approval(
    contract: ApprovalSuccessorContract,
    qualification: SourceQualification,
    receipt: UserExactApprovalReceipt,
    *,
    recorded_at: datetime,
) -> ExactApprovalBinding:
    contract = ApprovalSuccessorContract.model_validate(contract.model_dump(mode="json"))
    qualification = SourceQualification.model_validate(qualification.model_dump(mode="json"))
    receipt = UserExactApprovalReceipt.model_validate(receipt.model_dump(mode="json"))
    _require(receipt.contract_id == contract.contract_id, "approval receipt contract differs")
    _require(
        receipt.source_qualification_content_hash == qualification.content_hash,
        "approval receipt qualification differs",
    )
    _require(
        receipt.state_change_evidence_id == contract.predecessor.state_change_evidence_id
        and receipt.state_change_evidence_content_hash
        == contract.predecessor.state_change_evidence_content_hash,
        "approval receipt does not bind exact state",
    )
    recorded_at = _utc(recorded_at, label="v11 approval binding recorded_at")
    _require(recorded_at >= receipt.recorded_at, "approval binding predates receipt")
    body = {
        "schema_version": "exact-approval-binding-v11",
        "contract_version": contract.contract_version,
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "source_qualification_content_hash": qualification.content_hash,
        "state_change_evidence_id": contract.predecessor.state_change_evidence_id,
        "state_change_evidence_content_hash": (
            contract.predecessor.state_change_evidence_content_hash
        ),
        "user_approval_receipt_id": receipt.receipt_id,
        "user_approval_receipt_content_hash": receipt.content_hash,
        "approved_runtime": APPROVED_RUNTIME,
        "approved_scopes": APPROVED_SCOPES,
        "identity_assurance": IDENTITY_ASSURANCE,
        "attempt_limit": 1,
        "approval_reusable": False,
        "state_reusable": False,
        "attempt_started": False,
        "attempt_consumed": False,
        "attempt_entrypoint_available": False,
        "attempt_lifecycle_successor_required": True,
        "network_or_transport_authorized": False,
        "provider_evaluator_agent_execution_authorized": False,
        "candidate_cost_or_paid_execution_authorized": False,
        "retry_replacement_or_resume_authorized": False,
        "next_gate": APPROVAL_NEXT_GATE,
        "recorded_at": recorded_at,
    }
    content_hash = v10._hash_body(body)
    return ExactApprovalBinding(
        **body,
        approval_id=v10._derived_id("ncpapproval", content_hash),
        content_hash=content_hash,
    )


def record_exact_approval(
    *,
    statement: str,
    recorded_at: datetime,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Bind one exact post-qualification approval; start no attempt."""

    root = v10._root(repository)
    for path in (APPROVAL_RECEIPT_PATH, APPROVAL_BINDING_PATH):
        _require(
            not v10._logical_path(root, path, must_exist=False).exists(),
            "v11 approval artifact already exists",
        )
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    receipt = build_user_approval_receipt(
        contract,
        qualification,
        statement=statement,
        recorded_at=recorded_at,
    )
    approval = bind_exact_approval(
        contract,
        qualification,
        receipt,
        recorded_at=recorded_at,
    )
    receipt_raw = v10._canonical(receipt)
    approval_raw = v10._canonical(approval)
    combined = (receipt_raw + approval_raw).lower()
    _require(b"openai_api_key=" not in combined, "credential assignment bytes are forbidden")
    _require(b"sk-" not in combined, "credential-like bytes are forbidden")
    v10._write_once(root, APPROVAL_RECEIPT_PATH, receipt_raw)
    v10._write_once(root, APPROVAL_BINDING_PATH, approval_raw)
    return validate_exact_approval(repository=root)


def validate_exact_approval(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    contract = load_contract(repository=root)
    qualification = _load_qualification(root)
    receipt_raw = v10._read(root, APPROVAL_RECEIPT_PATH)
    approval_raw = v10._read(root, APPROVAL_BINDING_PATH)
    try:
        receipt = UserExactApprovalReceipt.model_validate_json(receipt_raw)
        approval = ExactApprovalBinding.model_validate_json(approval_raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise ApprovalSuccessorError("v11 approval artifact is invalid") from exc
    _require(receipt_raw == v10._canonical(receipt), "v11 receipt bytes are not canonical")
    _require(approval_raw == v10._canonical(approval), "v11 approval bytes are not canonical")
    expected = bind_exact_approval(
        contract,
        qualification,
        receipt,
        recorded_at=approval.recorded_at,
    )
    _require(approval == expected, "v11 approval does not bind exact receipt")
    return {
        "status": "V11_EXACT_APPROVAL_BOUND_ATTEMPT_LIFECYCLE_SUCCESSOR_REQUIRED",
        "contract_id": contract.contract_id,
        "source_qualification_hash": qualification.content_hash,
        "state_change_evidence_id": approval.state_change_evidence_id,
        "approval_receipt_id": receipt.receipt_id,
        "approval_id": approval.approval_id,
        "approval_content_hash": approval.content_hash,
        "attempt_limit": 1,
        "attempt_started": False,
        "attempt_entrypoint_available": False,
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "next_gate": APPROVAL_NEXT_GATE,
    }


__all__ = [
    "APPROVAL_BINDING_PATH",
    "APPROVAL_RECEIPT_PATH",
    "APPROVAL_TEMPLATE",
    "APPROVED_RUNTIME",
    "APPROVED_SCOPES",
    "ApprovalSuccessorContract",
    "ApprovalSuccessorError",
    "BUILD_SCRIPT_PATH",
    "CONTRACT_PATH",
    "ExactApprovalBinding",
    "QUALIFICATION_PATH",
    "RUNTIME_PATH",
    "SOURCE_ADDED_PATHS",
    "SOURCE_FILES",
    "SourceQualification",
    "TEST_PATH",
    "UserExactApprovalReceipt",
    "bind_exact_approval",
    "build_user_approval_receipt",
    "expected_approval_statement",
    "load_contract",
    "materialize_contract",
    "qualify_source",
    "record_exact_approval",
    "validate_exact_approval",
    "validate_source_qualification",
]
