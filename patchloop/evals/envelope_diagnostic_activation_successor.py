"""Source-only v22 activation contract over the qualified v21 framing channel.

This module binds a projection-only typed diagnostic channel to the exact v21
source and recorded qualification. Contract materialization and source
qualification are deliberately lifecycle-free: they launch no diagnostic or
mock workload process, make no Docker, dotenv, SDK, network, provider,
evaluator, or agent observation, and create no state, approval, attempt, action
marker, or terminal artifact. Local Git subprocesses may read provenance.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from patchloop.contracts import FrozenStrictModel
from patchloop.errors import ContractError
from patchloop.evals import envelope_diagnostic_preflight_successor as v21
from patchloop.util import sha256_bytes

v10 = v21.v10

CONTRACT_SCHEMA_VERSION = "envelope-diagnostic-activation-successor-contract-v22"
CONTRACT_VERSION = "ac-evaluator-v2-envelope-diagnostic-activation-successor-v22"
CONTRACT_PATH = Path(
    "experiments/evaluator-v2-envelope-diagnostic-activation-successor-v22.contract.json"
)
RUNTIME_PATH = Path("patchloop/evals/envelope_diagnostic_activation_successor.py")
SUPERVISOR_PATH = Path("scripts/run_sanitized_sdk_bootstrap_envelope_diagnostic_v22.py")
BUILD_SCRIPT_PATH = Path("scripts/build_envelope_diagnostic_activation_successor.py")
TEST_PATH = Path("tests/test_envelope_diagnostic_activation_successor.py")
UV_LOCK_PATH = Path("uv.lock")
PRODUCTION_MODEL_PATH = Path("patchloop/agent/model.py")

SOURCE_PARENT_COMMIT = "e763a2ed4fbb14659fcba88eb2c7411ab25eec0c"
V21_SOURCE_COMMIT = "05cb2ab717805a5e777a4e7b87f7784d44dfac84"
V21_SOURCE_TREE = "d05216a65fc6e627e1fbee41560a52fb6e8c023d"
V21_QUALIFICATION_COMMIT = "aef271e8ad222167ffd11656d0018d18c1964b57"
V21_CONTRACT_ID = "ncpcontract_d1ec7610e2e29d3a614958a46ac36b190d97fe369cf6b533cfe39afd228ccc8a"
V21_CONTRACT_FILE_SHA256 = "sha256:cf8eed678d2f9d63f1c936509ac2bb0086293335334410171c74891794876b83"
V21_CONTRACT_FILE_BYTES = 4_878
V21_QUALIFICATION_HASH = "sha256:5510796c3ba9e26a36fac67dff46d21fd3bc4d0f646169c0b4862551542132c4"
V21_QUALIFICATION_FILE_SHA256 = (
    "sha256:3e7b9b504eaa551994865ff0c6b3a0dd472206f97cffcc711ac1be7111befb9f"
)
V21_QUALIFICATION_FILE_BYTES = 8_075

QUALIFICATION_SCHEMA_VERSION = "envelope-diagnostic-activation-source-qualification-v22"
QUALIFICATION_ID = "ac-evaluator-v2-envelope-diagnostic-activation-source-20260813-r1"
QUALIFICATION_STATUS = "OFFLINE_V22_TYPED_DIAGNOSTIC_CHANNEL_SOURCE_QUALIFIED_ACTIVATION_CLOSED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-envelope-diagnostic-activation-v22-source-qualification.json"
)
NEXT_GATE = "new-versioned-v23-activation-wrapper-required"
PROJECTION_ONLY_ADAPTER = (
    "scripts.run_sanitized_sdk_bootstrap_envelope_diagnostic_v22.project_worker_envelope"
)
FUTURE_ACTIVATION_SCOPES = (
    "v21-exact-source-and-recorded-qualification-validation-before-observation",
    "already-running-docker-read-only-two-snapshot-eight-command-observation",
    "isolated-dotenv-exact-openai-api-key-membership",
    "isolated-sanitized-sdk-fixed-placeholder-reject-dispatch-diagnostic",
    "parent-supervisor-and-supervisor-worker-v21-framed-result-channel",
)

SOURCE_ADDED_PATHS = tuple(
    sorted(
        path.as_posix()
        for path in (CONTRACT_PATH, RUNTIME_PATH, SUPERVISOR_PATH, BUILD_SCRIPT_PATH, TEST_PATH)
    )
)
SOURCE_FILES = tuple(
    sorted(
        set(v21.SOURCE_FILES)
        | {
            CONTRACT_PATH,
            RUNTIME_PATH,
            SUPERVISOR_PATH,
            BUILD_SCRIPT_PATH,
            TEST_PATH,
            v21.QUALIFICATION_PATH,
            v21.v19.v17.v9.DIAGNOSTIC_CHILD_PATH,
            v21.v19.v17.v9.RUNTIME_PATH,
            v21.v19.v17.v9.CONTRACT_PATH,
            v21.v19.v17.v9.v7.CONTRACT_PATH,
            v21.v19.v17.v9.v7.RUNTIME_PATH,
            v21.v19.v17.v9.v7.QUALIFICATION_PATH,
            v21.v19.v17.v9.v6.CONTRACT_PATH,
            v21.v19.v17.v9.v6.RUNTIME_PATH,
            v21.v19.v17.v9.v6.QUALIFICATION_PATH,
            v21.v19.v17.v9.v6.OLD_CHILD_PATH,
            v21.v19.v17.v9.v6.D137_PATH,
            UV_LOCK_PATH,
            PRODUCTION_MODEL_PATH,
        },
        key=lambda path: path.as_posix(),
    )
)


class EnvelopeDiagnosticActivationError(ContractError):
    """The source-only v22 activation boundary failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EnvelopeDiagnosticActivationError(message)


class V21SourceBinding(FrozenStrictModel):
    source_commit: Literal["05cb2ab717805a5e777a4e7b87f7784d44dfac84"] = V21_SOURCE_COMMIT
    source_tree: Literal["d05216a65fc6e627e1fbee41560a52fb6e8c023d"] = V21_SOURCE_TREE
    qualification_commit: Literal["aef271e8ad222167ffd11656d0018d18c1964b57"] = (
        V21_QUALIFICATION_COMMIT
    )
    contract_id: Literal[
        "ncpcontract_d1ec7610e2e29d3a614958a46ac36b190d97fe369cf6b533cfe39afd228ccc8a"
    ] = V21_CONTRACT_ID
    contract_content_hash: Literal[
        "sha256:d1ec7610e2e29d3a614958a46ac36b190d97fe369cf6b533cfe39afd228ccc8a"
    ]
    contract_file_sha256: Literal[
        "sha256:cf8eed678d2f9d63f1c936509ac2bb0086293335334410171c74891794876b83"
    ] = V21_CONTRACT_FILE_SHA256
    contract_file_bytes: Literal[4878] = V21_CONTRACT_FILE_BYTES
    source_qualification_hash: Literal[
        "sha256:5510796c3ba9e26a36fac67dff46d21fd3bc4d0f646169c0b4862551542132c4"
    ] = V21_QUALIFICATION_HASH
    source_qualification_file_sha256: Literal[
        "sha256:3e7b9b504eaa551994865ff0c6b3a0dd472206f97cffcc711ac1be7111befb9f"
    ] = V21_QUALIFICATION_FILE_SHA256
    source_qualification_file_bytes: Literal[8075] = V21_QUALIFICATION_FILE_BYTES
    qualification_status: Literal[
        "OFFLINE_V21_ENVELOPE_DIAGNOSTIC_SOURCE_QUALIFIED_ACTIVATION_CLOSED"
    ]
    fixture_passed: Literal[True] = True
    fixture_is_transport_evidence_only: Literal[True] = True
    fixture_process_external_activity_absence_proven: Literal[False] = False
    readiness_or_sdk_result_created: Literal[False] = False
    state_approval_attempt_or_terminal_count: Literal[0] = 0
    execution_authorized: Literal[False] = False


class ActivationRuntimeProfile(FrozenStrictModel):
    projection_only_adapter: Literal[
        "scripts.run_sanitized_sdk_bootstrap_envelope_diagnostic_v22.project_worker_envelope"
    ] = PROJECTION_ONLY_ADAPTER
    supervisor_path: Literal["scripts/run_sanitized_sdk_bootstrap_envelope_diagnostic_v22.py"] = (
        SUPERVISOR_PATH.as_posix()
    )
    supervisor_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    diagnostic_child_path: Literal["scripts/run_sanitized_sdk_diagnostic_child.py"] = (
        v21.v19.v17.v9.DIAGNOSTIC_CHILD_PATH.as_posix()
    )
    diagnostic_child_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    diagnostic_child_schema_runtime_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    diagnostic_runtime_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    dotenv_parser_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    docker_observer_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    uv_lock_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    production_model_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    offline_worker_schema_version: Literal["offline-fixed-diagnostic-worker-mock-v22"] = (
        "offline-fixed-diagnostic-worker-mock-v22"
    )
    offline_supervisor_schema_version: Literal["offline-fixed-diagnostic-supervisor-mock-v22"] = (
        "offline-fixed-diagnostic-supervisor-mock-v22"
    )
    live_worker_schema_version: Literal["live-no-call-diagnostic-worker-envelope-v22"] = (
        "live-no-call-diagnostic-worker-envelope-v22"
    )
    live_supervisor_schema_version: Literal["live-no-call-diagnostic-supervisor-envelope-v22"] = (
        "live-no-call-diagnostic-supervisor-envelope-v22"
    )
    v21_contract_id: Literal[
        "ncpcontract_d1ec7610e2e29d3a614958a46ac36b190d97fe369cf6b533cfe39afd228ccc8a"
    ] = V21_CONTRACT_ID
    v21_source_qualification_hash: Literal[
        "sha256:5510796c3ba9e26a36fac67dff46d21fd3bc4d0f646169c0b4862551542132c4"
    ] = V21_QUALIFICATION_HASH
    future_activation_scopes: tuple[str, ...] = FUTURE_ACTIVATION_SCOPES
    parent_to_supervisor_launch_limit: Literal[1] = 1
    supervisor_to_worker_launch_limit: Literal[1] = 1
    child_flags: tuple[str, ...] = v21.CHILD_FLAGS
    fixed_process_environment: dict[str, str] = v21.FIXED_CHILD_ENVIRONMENT
    frame_body_limit: Literal[262144] = v21.FRAME_BODY_LIMIT
    frame_output_limit: Literal[262180] = v21.FRAME_OUTPUT_LIMIT
    complete_write_required_on_both_hops: Literal[True] = True
    length_and_digest_framing_required: Literal[True] = True
    typed_live_diagnostic_envelope_required: Literal[True] = True
    fixed_fixture_and_live_schema_separated: Literal[True] = True
    invalid_raw_payload_metadata_persisted: Literal[False] = False
    live_observation_input_projection_only: Literal[True] = True
    live_supervisor_input_projection_only: Literal[True] = True
    live_diagnostic_default_exposed: Literal[False] = False
    activation_runtime_exposed: Literal[False] = False
    offline_fixed_mock_local_test_entrypoint_exposed: Literal[True] = True
    offline_fixed_mock_local_test_process_launch_limit: Literal[2] = 2
    live_process_entrypoint_exposed: Literal[False] = False
    qualification_diagnostic_or_mock_process_launch_limit: Literal[0] = 0
    local_git_provenance_subprocesses_may_run: Literal[True] = True
    qualification_reuses_recorded_v21_evidence_only: Literal[True] = True
    credential_value_metadata_limit: Literal[0] = 0
    network_call_limit: Literal[0] = 0
    provider_evaluator_agent_call_limit: Literal[0] = 0

    @model_validator(mode="after")
    def validate_profile(self) -> ActivationRuntimeProfile:
        if self.future_activation_scopes != FUTURE_ACTIVATION_SCOPES:
            raise ValueError("v22 future activation scopes drifted")
        if self.child_flags != v21.CHILD_FLAGS:
            raise ValueError("v22 child flags drifted")
        if self.fixed_process_environment != v21.FIXED_CHILD_ENVIRONMENT:
            raise ValueError("v22 fixed process environment drifted")
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
    v21_source_qualification_or_fixture_mutation_allowed: Literal[False] = False


class SourceAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    source_qualification_authorized: Literal[True] = True
    state_approval_attempt_action_or_terminal_creation_authorized: Literal[False] = False
    offline_fixed_mock_local_test_process_launch_authorized: Literal[True] = True
    live_process_launch_authorized: Literal[False] = False
    docker_dotenv_sdk_network_or_provider_observation_authorized: Literal[False] = False
    credential_value_or_metadata_recording_authorized: Literal[False] = False
    docker_start_pull_load_image_store_or_container_mutation_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class EnvelopeDiagnosticActivationContract(FrozenStrictModel):
    schema_version: Literal["envelope-diagnostic-activation-successor-contract-v22"] = (
        CONTRACT_SCHEMA_VERSION
    )
    contract_version: Literal["ac-evaluator-v2-envelope-diagnostic-activation-successor-v22"] = (
        CONTRACT_VERSION
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor: V21SourceBinding
    runtime: ActivationRuntimeProfile
    lifecycle: LifecyclePolicy
    authority: SourceAuthority
    correction_scope: Literal["typed-live-diagnostic-channel-over-v21-framing-only"] = (
        "typed-live-diagnostic-channel-over-v21-framing-only"
    )
    predecessor_retry_repair_or_cause_proof: Literal[False] = False
    state_approval_attempt_or_terminal_entrypoints_implemented: Literal[False] = False
    offline_fixed_mock_test_entrypoint_exposed: Literal[True] = True
    live_process_entrypoint_exposed: Literal[False] = False
    readiness_or_sdk_result_created: Literal[False] = False
    execution_currently_authorized: Literal[False] = False
    next_gate: Literal["new-versioned-v23-activation-wrapper-required"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> EnvelopeDiagnosticActivationContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected or self.contract_id != v10._derived_id(
            "ncpcontract", expected
        ):
            raise ValueError("v22 contract identity differs")
        return self


class SourceCommitBinding(FrozenStrictModel):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    parents: tuple[str, ...]
    added_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_source(self) -> SourceCommitBinding:
        if self.parents != (SOURCE_PARENT_COMMIT,):
            raise ValueError("v22 source predecessor drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v22 source additions drifted")
        return self


class QualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    source_qualified: Literal[True] = True
    offline_fixed_mock_or_live_process_launch_count: Literal[0] = 0
    state_approval_attempt_action_or_terminal_created: Literal[False] = False
    docker_dotenv_sdk_network_or_provider_observation_count: Literal[0] = 0
    credential_value_or_metadata_observation_count: Literal[0] = 0
    external_mutation_count: Literal[0] = 0
    execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class SourceQualification(FrozenStrictModel):
    schema_version: Literal["envelope-diagnostic-activation-source-qualification-v22"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal[
        "ac-evaluator-v2-envelope-diagnostic-activation-source-20260813-r1"
    ] = QUALIFICATION_ID
    status: Literal["OFFLINE_V22_TYPED_DIAGNOSTIC_CHANNEL_SOURCE_QUALIFIED_ACTIVATION_CLOSED"] = (
        QUALIFICATION_STATUS
    )
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[v10.CommittedFileBinding, ...]
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_contract_id: Literal[
        "ncpcontract_d1ec7610e2e29d3a614958a46ac36b190d97fe369cf6b533cfe39afd228ccc8a"
    ] = V21_CONTRACT_ID
    predecessor_source_qualification_hash: Literal[
        "sha256:5510796c3ba9e26a36fac67dff46d21fd3bc4d0f646169c0b4862551542132c4"
    ] = V21_QUALIFICATION_HASH
    recorded_v21_fixture_evidence_revalidated_not_replayed: Literal[True] = True
    fixed_mock_or_live_process_evidence_created: Literal[False] = False
    authority: QualificationAuthority
    next_gate: Literal["new-versioned-v23-activation-wrapper-required"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v22 qualification time must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> SourceQualification:
        expected_paths = tuple(path.as_posix() for path in SOURCE_FILES)
        if tuple(item.path for item in self.source_files) != expected_paths:
            raise ValueError("v22 qualification inventory drifted")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != v10._hash_body(body):
            raise ValueError("v22 qualification hash mismatch")
        return self


def _load_v21_source(root: Path) -> tuple[v21.EnvelopeDiagnosticContract, v21.SourceQualification]:
    summary = v21.validate_source_qualification(repository=root)
    contract_raw = v10._read(root, v21.CONTRACT_PATH)
    qualification_raw = v10._read(root, v21.QUALIFICATION_PATH)
    contract = v21.EnvelopeDiagnosticContract.model_validate_json(contract_raw)
    qualification = v21.SourceQualification.model_validate_json(qualification_raw)
    _require(contract_raw == v10._canonical(contract), "v21 contract bytes differ")
    _require(qualification_raw == v10._canonical(qualification), "v21 qualification bytes differ")
    _require(
        contract_raw
        == v10._git(root, "show", f"{V21_SOURCE_COMMIT}:{v21.CONTRACT_PATH.as_posix()}"),
        "v21 committed contract differs",
    )
    _require(
        qualification_raw
        == v10._git(
            root,
            "show",
            f"{V21_QUALIFICATION_COMMIT}:{v21.QUALIFICATION_PATH.as_posix()}",
        ),
        "v21 committed qualification differs",
    )
    _require(
        contract.contract_id == V21_CONTRACT_ID
        and qualification.contract_id == V21_CONTRACT_ID
        and qualification.content_hash == V21_QUALIFICATION_HASH
        and summary["qualification_hash"] == V21_QUALIFICATION_HASH
        and sha256_bytes(contract_raw) == V21_CONTRACT_FILE_SHA256
        and len(contract_raw) == V21_CONTRACT_FILE_BYTES
        and sha256_bytes(qualification_raw) == V21_QUALIFICATION_FILE_SHA256
        and len(qualification_raw) == V21_QUALIFICATION_FILE_BYTES
        and qualification.fixture_chain.passed is True
        and qualification.fixture_chain.process_external_activity_absence_proven is False
        and qualification.authority.execution_authorized is False,
        "v21 exact source qualification binding differs",
    )
    return contract, qualification


def _predecessor_binding(root: Path) -> V21SourceBinding:
    contract, qualification = _load_v21_source(root)
    return V21SourceBinding(
        contract_content_hash=contract.content_hash,
        qualification_status=qualification.status,
    )


def _runtime_profile(root: Path) -> ActivationRuntimeProfile:
    _load_v21_source(root)
    return ActivationRuntimeProfile(
        supervisor_file_sha256=sha256_bytes(v10._read(root, SUPERVISOR_PATH)),
        diagnostic_child_file_sha256=sha256_bytes(
            v10._read(root, v21.v19.v17.v9.DIAGNOSTIC_CHILD_PATH)
        ),
        diagnostic_child_schema_runtime_file_sha256=sha256_bytes(
            v10._read(root, v21.v19.v17.v9.v7.RUNTIME_PATH)
        ),
        diagnostic_runtime_file_sha256=sha256_bytes(
            v10._read(root, v21.v19.v17.v9.v6.RUNTIME_PATH)
        ),
        dotenv_parser_file_sha256=sha256_bytes(v10._read(root, v21.v19.v17.v9.v6.OLD_CHILD_PATH)),
        docker_observer_file_sha256=sha256_bytes(v10._read(root, v21.v19.v17.v9.v6.D137_PATH)),
        uv_lock_file_sha256=sha256_bytes(v10._read(root, UV_LOCK_PATH)),
        production_model_file_sha256=sha256_bytes(v10._read(root, PRODUCTION_MODEL_PATH)),
    )


def _build_contract(root: Path) -> EnvelopeDiagnosticActivationContract:
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "predecessor": _predecessor_binding(root).model_dump(mode="json"),
        "runtime": _runtime_profile(root).model_dump(mode="json"),
        "lifecycle": LifecyclePolicy().model_dump(mode="json"),
        "authority": SourceAuthority().model_dump(mode="json"),
        "correction_scope": "typed-live-diagnostic-channel-over-v21-framing-only",
        "predecessor_retry_repair_or_cause_proof": False,
        "state_approval_attempt_or_terminal_entrypoints_implemented": False,
        "offline_fixed_mock_test_entrypoint_exposed": True,
        "live_process_entrypoint_exposed": False,
        "readiness_or_sdk_result_created": False,
        "execution_currently_authorized": False,
        "next_gate": NEXT_GATE,
    }
    content_hash = v10._hash_body(body)
    return EnvelopeDiagnosticActivationContract(
        **body,
        contract_id=v10._derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def load_contract(*, repository: str | Path | None = None) -> EnvelopeDiagnosticActivationContract:
    root = v10._root(repository)
    raw = v10._read(root, CONTRACT_PATH)
    try:
        value = EnvelopeDiagnosticActivationContract.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise EnvelopeDiagnosticActivationError("v22 contract artifact is invalid") from exc
    _require(raw == v10._canonical(value), "v22 contract bytes are not canonical")
    _require(value == _build_contract(root), "v22 contract differs from source")
    return value


def materialize_contract(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    value = _build_contract(root)
    raw = v10._canonical(value)
    target = v10._logical_path(root, CONTRACT_PATH, must_exist=False)
    if target.exists():
        _require(v10._read(root, CONTRACT_PATH) == raw, "v22 contract already differs")
    else:
        v10._write_once(root, CONTRACT_PATH, raw)
    return {
        "status": "OFFLINE_V22_TYPED_DIAGNOSTIC_CHANNEL_CONTRACT_MATERIALIZED",
        "contract_id": value.contract_id,
        "contract_content_hash": value.content_hash,
        "artifact_path": CONTRACT_PATH.as_posix(),
        "artifact_file_sha256": sha256_bytes(raw),
        "artifact_bytes": len(raw),
        "diagnostic_or_mock_processes_launched": 0,
        "local_git_provenance_subprocesses_may_run": True,
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
        "next_gate": "exact-source-commit-and-offline-qualification",
    }


def _source_commit(root: Path, selected: str) -> SourceCommitBinding:
    commit = v10._git(root, "rev-parse", f"{selected}^{{commit}}").decode("ascii").strip()
    tree = v10._git(root, "rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    row = v10._git(root, "rev-list", "--parents", "-n", "1", commit).decode().split()
    _require(row and row[0] == commit and len(row) == 2, "v22 source parent failed")
    lines = (
        v10._git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", row[1], commit)
        .decode("utf-8")
        .splitlines()
    )
    added = tuple(sorted(parts[1] for line in lines if (parts := line.split("\t"))[:1] == ["A"]))
    _require(len(lines) == len(added), "v22 source contains non-addition changes")
    return SourceCommitBinding(commit=commit, tree=tree, parents=(row[1],), added_paths=added)


def _build_qualification(
    root: Path, *, source_commit: str, recorded_at: datetime
) -> SourceQualification:
    contract = load_contract(repository=root)
    _load_v21_source(root)
    commit = _source_commit(root, source_commit)
    pairs = tuple(v10._committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(pair[0] for pair in pairs)
    contract_index = SOURCE_FILES.index(CONTRACT_PATH)
    _require(pairs[contract_index][1] == v10._canonical(contract), "committed v22 contract differs")
    for path, pair in zip(SOURCE_FILES, pairs, strict=True):
        _require(v10._read(root, path) == pair[1], f"working v22 dependency differs: {path}")
    body = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": QUALIFICATION_STATUS,
        "recorded_at": recorded_at,
        "source_commit": commit.model_dump(mode="json"),
        "source_files": [item.model_dump(mode="json") for item in files],
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "predecessor_contract_id": V21_CONTRACT_ID,
        "predecessor_source_qualification_hash": V21_QUALIFICATION_HASH,
        "recorded_v21_fixture_evidence_revalidated_not_replayed": True,
        "fixed_mock_or_live_process_evidence_created": False,
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
        "offline_fixed_mock_or_live_process_launch_count": 0,
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
    _require(raw == v10._canonical(value), "v22 qualification bytes are not canonical")
    expected = _build_qualification(
        root,
        source_commit=value.source_commit.commit,
        recorded_at=value.recorded_at,
    )
    _require(value == expected, "v22 qualification differs from committed source")
    return _qualification_summary(value, raw)


__all__ = [
    "FUTURE_ACTIVATION_SCOPES",
    "PROJECTION_ONLY_ADAPTER",
    "BUILD_SCRIPT_PATH",
    "CONTRACT_PATH",
    "EnvelopeDiagnosticActivationContract",
    "EnvelopeDiagnosticActivationError",
    "PRODUCTION_MODEL_PATH",
    "QUALIFICATION_PATH",
    "RUNTIME_PATH",
    "SOURCE_ADDED_PATHS",
    "SOURCE_FILES",
    "SOURCE_PARENT_COMMIT",
    "SUPERVISOR_PATH",
    "TEST_PATH",
    "UV_LOCK_PATH",
    "_build_contract",
    "load_contract",
    "materialize_contract",
    "qualify_source",
    "validate_source_qualification",
]
