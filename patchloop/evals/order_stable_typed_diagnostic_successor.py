"""Source-only v24 correction for the v23 typed diagnostic rejection.

V23 is immutable and consumed.  V24 validates an already observed legacy
child before mapping-key sorting, then emits only an order-independent typed
summary.  Materialization and qualification perform no diagnostic workload,
process launch, dotenv/SDK/Docker observation, network action, or lifecycle
write.  A separate future activation wrapper is required.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from patchloop.contracts import FrozenStrictModel
from patchloop.errors import ContractError
from patchloop.evals import typed_diagnostic_activation_successor as v23
from patchloop.util import sha256_bytes
from scripts import run_order_stable_typed_diagnostic_projection_v24 as projection

v10 = v23.v10

CONTRACT_SCHEMA_VERSION = "order-stable-typed-diagnostic-successor-contract-v24"
CONTRACT_VERSION = "ac-evaluator-v2-order-stable-typed-diagnostic-successor-v24"
CONTRACT_PATH = Path(
    "experiments/evaluator-v2-order-stable-typed-diagnostic-successor-v24.contract.json"
)
RUNTIME_PATH = Path("patchloop/evals/order_stable_typed_diagnostic_successor.py")
PROJECTION_PATH = Path("scripts/run_order_stable_typed_diagnostic_projection_v24.py")
BUILD_SCRIPT_PATH = Path("scripts/build_order_stable_typed_diagnostic_successor.py")
TEST_PATH = Path("tests/test_order_stable_typed_diagnostic_successor.py")
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-order-stable-typed-diagnostic-v24-source-qualification.json"
)

SOURCE_PARENT_COMMIT = "8b7d92ab72a1815dfdd0a0804f8247106a1f5131"
V23_SOURCE_COMMIT = "733ddc3cc74928f1011c58455fad6b151bfd25ad"
V23_SOURCE_TREE = "8b2de30d46c2ac6eda7a45d6d9c6351624a60f75"
V23_QUALIFICATION_COMMIT = "f1c469d60280b67b40a852863ddf36d94f0d6b8e"
V23_EVIDENCE_COMMIT = "26e9562a77e49c9733da379686e19577fda71e01"
V23_CONTRACT_ID = "ncpcontract_dfdfed2c3e5fabd39f3518cfe9aeae648ad38f182acc2efd2c478bbb449ada0a"
V23_CONTRACT_FILE_SHA256 = "sha256:b362ba003973e1b44d910b426c876f415a02d1c7354689358d0f6dbf010765b7"
V23_CONTRACT_FILE_BYTES = 4_530
V23_QUALIFICATION_HASH = "sha256:f196bac8434dc78d061273ca87bd301237604face9bc93edcf1635afb1678f26"
V23_QUALIFICATION_FILE_SHA256 = (
    "sha256:32a8c74166daf84d20cda8317d434481135a93056e063800bb553efd2f7ae2f4"
)
V23_QUALIFICATION_FILE_BYTES = 14_099
V23_STATE_ID = "ncpstate_c1fae9c0980bf18f55da673fa2416b48150976561a194097b98f39af1c71ee9d"
V23_APPROVAL_ID = "ncpapproval_40be479a1d430f6353e872597109a581f806c136f48dac2d7982576fa4544637"
V23_ATTEMPT_ID = "ncpattempt_c9ee0c8c0fe8f282e164e505f64d8f8d99561035173965ea9c9768d04ba31765"
V23_TERMINAL_ID = "ncpterminal_376d5f2278445847db1b0a122d844606623bf04271baea46ecf3fa3fe8d0d004"
V23_TERMINAL_HASH = "sha256:376d5f2278445847db1b0a122d844606623bf04271baea46ecf3fa3fe8d0d004"

_V23_FILE_BINDINGS = {
    v23.CONTRACT_PATH: (V23_CONTRACT_FILE_SHA256, V23_CONTRACT_FILE_BYTES),
    v23.QUALIFICATION_PATH: (V23_QUALIFICATION_FILE_SHA256, V23_QUALIFICATION_FILE_BYTES),
    v23.STATE_PATH: (
        "sha256:1c03262f461e8f56e7dbf91bed49e3a7b5387c1082ff032734b2bfe18ae0a9ad",
        919,
    ),
    v23.APPROVAL_PATH: (
        "sha256:08b6920e83fcf236b73312f9ef53ef40301594e6d2aca240a3857fe0776e35b8",
        1_486,
    ),
    v23.RUN_AUTHORIZATION_PATH: (
        "sha256:260266575ff0445084b1b2eed15fb2c6d79c6c01aff7f3853298a371ea5de5f4",
        990,
    ),
    v23.ATTEMPT_PATH: (
        "sha256:16ee83121240b564205d2e874238d16289701d71204ae1735598c903ecb4a84a",
        686,
    ),
    v23.ACTION_STARTED_PATH: (
        "sha256:db6297b773c4f67c4a8892603c3ab922f10afabed538fd704ccae770975401cd",
        521,
    ),
    v23.TERMINAL_PATH: (
        "sha256:1be21372e64dd33357d7d176c9b79b88a82d5bf047481bb7e312559bcaa76237",
        18_273,
    ),
}

QUALIFICATION_SCHEMA_VERSION = "order-stable-typed-diagnostic-source-qualification-v24"
QUALIFICATION_ID = "ac-evaluator-v2-order-stable-typed-diagnostic-source-20260813-r1"
QUALIFICATION_STATUS = (
    "OFFLINE_V24_ORDER_STABLE_TYPED_DIAGNOSTIC_SOURCE_QUALIFIED_ACTIVATION_CLOSED"
)
NEXT_GATE = "new-versioned-v25-activation-wrapper-required"

PARENT_MODEL_PATH = Path("patchloop/evals/sanitized_sdk_parent_integration.py")
SDK_DIAGNOSTIC_PATH = Path("patchloop/evals/sanitized_sdk_diagnostic_successor.py")
D137_PATH = Path("patchloop/evals/d137_no_call_preflight.py")
DIAGNOSTIC_CHILD_PATH = Path("scripts/run_sanitized_sdk_diagnostic_child.py")
V21_FRAME_PATH = Path("scripts/run_sanitized_sdk_bootstrap_envelope_diagnostic_v21.py")

SOURCE_ADDED_PATHS = tuple(
    sorted(
        path.as_posix()
        for path in (CONTRACT_PATH, RUNTIME_PATH, PROJECTION_PATH, BUILD_SCRIPT_PATH, TEST_PATH)
    )
)
SOURCE_FILES = tuple(
    sorted(
        set(v23.SOURCE_FILES)
        | set(_V23_FILE_BINDINGS)
        | {
            CONTRACT_PATH,
            RUNTIME_PATH,
            PROJECTION_PATH,
            BUILD_SCRIPT_PATH,
            TEST_PATH,
            PARENT_MODEL_PATH,
            SDK_DIAGNOSTIC_PATH,
            D137_PATH,
            DIAGNOSTIC_CHILD_PATH,
            V21_FRAME_PATH,
        },
        key=lambda path: path.as_posix(),
    )
)


class OrderStableDiagnosticError(ContractError):
    """The v24 source-only correction failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise OrderStableDiagnosticError(message)


class V23ConsumedBinding(FrozenStrictModel):
    source_commit: Literal["733ddc3cc74928f1011c58455fad6b151bfd25ad"] = V23_SOURCE_COMMIT
    source_tree: Literal["8b2de30d46c2ac6eda7a45d6d9c6351624a60f75"] = V23_SOURCE_TREE
    qualification_commit: Literal["f1c469d60280b67b40a852863ddf36d94f0d6b8e"] = (
        V23_QUALIFICATION_COMMIT
    )
    evidence_commit: Literal["26e9562a77e49c9733da379686e19577fda71e01"] = V23_EVIDENCE_COMMIT
    contract_id: Literal[
        "ncpcontract_dfdfed2c3e5fabd39f3518cfe9aeae648ad38f182acc2efd2c478bbb449ada0a"
    ] = V23_CONTRACT_ID
    source_qualification_hash: Literal[
        "sha256:f196bac8434dc78d061273ca87bd301237604face9bc93edcf1635afb1678f26"
    ] = V23_QUALIFICATION_HASH
    state_id: Literal[
        "ncpstate_c1fae9c0980bf18f55da673fa2416b48150976561a194097b98f39af1c71ee9d"
    ] = V23_STATE_ID
    approval_id: Literal[
        "ncpapproval_40be479a1d430f6353e872597109a581f806c136f48dac2d7982576fa4544637"
    ] = V23_APPROVAL_ID
    attempt_id: Literal[
        "ncpattempt_c9ee0c8c0fe8f282e164e505f64d8f8d99561035173965ea9c9768d04ba31765"
    ] = V23_ATTEMPT_ID
    terminal_id: Literal[
        "ncpterminal_376d5f2278445847db1b0a122d844606623bf04271baea46ecf3fa3fe8d0d004"
    ] = V23_TERMINAL_ID
    terminal_content_hash: Literal[
        "sha256:376d5f2278445847db1b0a122d844606623bf04271baea46ecf3fa3fe8d0d004"
    ] = V23_TERMINAL_HASH
    outcome: Literal["error"] = "error"
    reason: Literal["child_checker_error"] = "child_checker_error"
    docker_passed: Literal[True] = True
    docker_cli_command_count: Literal[8] = 8
    parent_to_supervisor_launch_count: Literal[1] = 1
    supervisor_to_worker_launch_count: Literal[1] = 1
    supervisor_returncode: Literal[0] = 0
    supervisor_frame_stage: Literal["valid"] = "valid"
    worker_frame_stage: Literal["valid"] = "valid"
    worker_code: Literal["diagnostic_result_invalid"] = "diagnostic_result_invalid"
    raw_exception_or_credential_metadata_return_count: Literal[0] = 0
    activity_accounting_complete: Literal[False] = False
    unknown_activity_possible: Literal[True] = True
    network_and_provider_counts_known: Literal[False] = False
    retry_replacement_or_resume_allowed: Literal[False] = False


class RuntimeProfile(FrozenStrictModel):
    projection_entrypoint: Literal[
        "scripts.run_order_stable_typed_diagnostic_projection_v24.project_observed_child"
    ] = "scripts.run_order_stable_typed_diagnostic_projection_v24.project_observed_child"
    projection_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v23_live_channel_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v22_channel_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    parent_model_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sdk_diagnostic_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    d137_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    diagnostic_child_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v21_frame_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_failure_reproduced_with_sdk_observation_fixture: Literal[True] = True
    predecessor_terminal_exact_invalid_field_proven: Literal[False] = False
    legacy_validation_preserves_input_mapping_order: Literal[True] = True
    projection_requires_direct_precanonical_observed_child: Literal[True] = True
    strict_json_runtime_types_required: Literal[True] = True
    canonical_frame_transmits_full_legacy_child: Literal[False] = False
    canonical_frame_transmits_value_free_summary: Literal[True] = True
    summary_contains_sdk_observation: Literal[False] = False
    summary_contains_raw_value_exception_or_traceback: Literal[False] = False
    invalid_input_returns_fixed_code_only: Literal[True] = True
    activation_runtime_or_live_callback_exposed: Literal[False] = False
    state_approval_attempt_action_or_terminal_entrypoint_exposed: Literal[False] = False
    qualification_diagnostic_mock_or_live_process_launch_limit: Literal[0] = 0


class SourceAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    source_qualification_authorized: Literal[True] = True
    offline_projection_tests_authorized: Literal[True] = True
    state_approval_attempt_action_or_terminal_authorized: Literal[False] = False
    docker_dotenv_sdk_live_observation_authorized: Literal[False] = False
    diagnostic_mock_or_live_process_launch_authorized: Literal[False] = False
    local_git_provenance_subprocesses_may_run: Literal[True] = True
    credential_value_or_metadata_recording_authorized: Literal[False] = False
    network_transport_provider_evaluator_or_agent_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class OrderStableDiagnosticContract(FrozenStrictModel):
    schema_version: Literal["order-stable-typed-diagnostic-successor-contract-v24"] = (
        CONTRACT_SCHEMA_VERSION
    )
    contract_version: Literal["ac-evaluator-v2-order-stable-typed-diagnostic-successor-v24"] = (
        CONTRACT_VERSION
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor: V23ConsumedBinding
    runtime: RuntimeProfile
    authority: SourceAuthority
    correction_scope: Literal[
        "order-stable-legacy-validation-and-value-free-summary-projection-only"
    ] = "order-stable-legacy-validation-and-value-free-summary-projection-only"
    lifecycle_or_live_execution_implemented: Literal[False] = False
    readiness_or_sdk_result_created: Literal[False] = False
    execution_currently_authorized: Literal[False] = False
    next_gate: Literal["new-versioned-v25-activation-wrapper-required"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> OrderStableDiagnosticContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected or self.contract_id != v10._derived_id(
            "ncpcontract", expected
        ):
            raise ValueError("v24 contract identity differs")
        return self


class SourceCommitBinding(FrozenStrictModel):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    parents: tuple[str, ...]
    added_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_source(self) -> SourceCommitBinding:
        if self.parents != (SOURCE_PARENT_COMMIT,):
            raise ValueError("v24 source predecessor drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v24 source additions drifted")
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


class SourceQualification(FrozenStrictModel):
    schema_version: Literal["order-stable-typed-diagnostic-source-qualification-v24"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal[
        "ac-evaluator-v2-order-stable-typed-diagnostic-source-20260813-r1"
    ] = QUALIFICATION_ID
    status: Literal[
        "OFFLINE_V24_ORDER_STABLE_TYPED_DIAGNOSTIC_SOURCE_QUALIFIED_ACTIVATION_CLOSED"
    ] = QUALIFICATION_STATUS
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[v10.CommittedFileBinding, ...]
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_contract_id: Literal[
        "ncpcontract_dfdfed2c3e5fabd39f3518cfe9aeae648ad38f182acc2efd2c478bbb449ada0a"
    ] = V23_CONTRACT_ID
    predecessor_terminal_id: Literal[
        "ncpterminal_376d5f2278445847db1b0a122d844606623bf04271baea46ecf3fa3fe8d0d004"
    ] = V23_TERMINAL_ID
    workload_or_runtime_evidence_created: Literal[False] = False
    authority: QualificationAuthority
    next_gate: Literal["new-versioned-v25-activation-wrapper-required"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v24 qualification time must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> SourceQualification:
        expected_paths = tuple(path.as_posix() for path in SOURCE_FILES)
        if tuple(item.path for item in self.source_files) != expected_paths:
            raise ValueError("v24 qualification inventory drifted")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != v10._hash_body(body):
            raise ValueError("v24 qualification identity differs")
        return self


def _read_exact(root: Path, path: Path, expected: tuple[str, int]) -> bytes:
    raw = v10._read(root, path)
    _require((sha256_bytes(raw), len(raw)) == expected, f"v23 dependency differs: {path}")
    return raw


def _predecessor_binding(root: Path) -> V23ConsumedBinding:
    contract_raw = _read_exact(root, v23.CONTRACT_PATH, _V23_FILE_BINDINGS[v23.CONTRACT_PATH])
    qualification_raw = _read_exact(
        root, v23.QUALIFICATION_PATH, _V23_FILE_BINDINGS[v23.QUALIFICATION_PATH]
    )
    for path, expected in _V23_FILE_BINDINGS.items():
        if path not in {v23.CONTRACT_PATH, v23.QUALIFICATION_PATH, v23.TERMINAL_PATH}:
            _read_exact(root, path, expected)
    terminal_raw = _read_exact(root, v23.TERMINAL_PATH, _V23_FILE_BINDINGS[v23.TERMINAL_PATH])
    for path in (
        v23.RUN_AUTHORIZATION_PATH,
        v23.ATTEMPT_PATH,
        v23.ACTION_STARTED_PATH,
        v23.TERMINAL_PATH,
    ):
        _binding, committed_raw = v10._committed_file(root, V23_EVIDENCE_COMMIT, path)
        _require(committed_raw == v10._read(root, path), f"v23 evidence commit differs: {path}")
    contract = v23.TypedDiagnosticActivationContract.model_validate_json(contract_raw)
    qualification = v23.SourceQualification.model_validate_json(qualification_raw)
    terminal = v23.TerminalTransition.model_validate_json(terminal_raw)
    _require(contract_raw == v10._canonical(contract), "v23 contract bytes differ")
    _require(qualification_raw == v10._canonical(qualification), "v23 qualification bytes differ")
    _require(terminal_raw == v10._canonical(terminal), "v23 terminal bytes differ")
    _require(
        contract.contract_id == V23_CONTRACT_ID
        and qualification.contract_id == V23_CONTRACT_ID
        and qualification.content_hash == V23_QUALIFICATION_HASH
        and qualification.source_commit.commit == V23_SOURCE_COMMIT
        and qualification.source_commit.tree == V23_SOURCE_TREE,
        "v23 source identity differs",
    )
    value = terminal.model_dump(mode="json")
    observation = value["observation"]
    channel = observation["channel_observation"]
    envelope = channel["supervisor_envelope"]
    worker = envelope["worker"]
    _require(
        value["terminal_id"] == V23_TERMINAL_ID
        and value["content_hash"] == V23_TERMINAL_HASH
        and value["attempt_id"] == V23_ATTEMPT_ID
        and value["outcome"] == "error"
        and value["reason"] == "child_checker_error"
        and observation["docker_observation"]["passed"] is True
        and observation["docker_cli_command_count"] == 8
        and observation["parent_to_supervisor_launch_attempt_count"] == 1
        and observation["supervisor_to_worker_launch_attempt_count"] == 1
        and channel["supervisor_returncode"] == 0
        and channel["supervisor_frame_stage"] == "valid"
        and envelope["worker_frame_stage"] == "valid"
        and worker["code"] == projection.INVALID_CODE
        and worker["child"] is None
        and value["activity_accounting_complete"] is False
        and value["unknown_post_marker_activity_possible"] is True
        and value["network_call_count"] is None
        and value["provider_evaluator_agent_call_count"] is None
        and value["retry_or_resume_allowed"] is False,
        "v23 consumed terminal differs",
    )
    return V23ConsumedBinding()


def _runtime_profile(root: Path) -> RuntimeProfile:
    _predecessor_binding(root)
    return RuntimeProfile(
        projection_file_sha256=sha256_bytes(v10._read(root, PROJECTION_PATH)),
        v23_live_channel_file_sha256=sha256_bytes(v10._read(root, v23.LIVE_CHANNEL_PATH)),
        v22_channel_file_sha256=sha256_bytes(v10._read(root, v23.v22.SUPERVISOR_PATH)),
        parent_model_file_sha256=sha256_bytes(v10._read(root, PARENT_MODEL_PATH)),
        sdk_diagnostic_file_sha256=sha256_bytes(v10._read(root, SDK_DIAGNOSTIC_PATH)),
        d137_file_sha256=sha256_bytes(v10._read(root, D137_PATH)),
        diagnostic_child_file_sha256=sha256_bytes(v10._read(root, DIAGNOSTIC_CHILD_PATH)),
        v21_frame_file_sha256=sha256_bytes(v10._read(root, V21_FRAME_PATH)),
    )


def _build_contract(root: Path) -> OrderStableDiagnosticContract:
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "predecessor": _predecessor_binding(root).model_dump(mode="json"),
        "runtime": _runtime_profile(root).model_dump(mode="json"),
        "authority": SourceAuthority().model_dump(mode="json"),
        "correction_scope": (
            "order-stable-legacy-validation-and-value-free-summary-projection-only"
        ),
        "lifecycle_or_live_execution_implemented": False,
        "readiness_or_sdk_result_created": False,
        "execution_currently_authorized": False,
        "next_gate": NEXT_GATE,
    }
    content_hash = v10._hash_body(body)
    return OrderStableDiagnosticContract(
        **body,
        contract_id=v10._derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def load_contract(*, repository: str | Path | None = None) -> OrderStableDiagnosticContract:
    root = v10._root(repository)
    raw = v10._read(root, CONTRACT_PATH)
    try:
        value = OrderStableDiagnosticContract.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise OrderStableDiagnosticError("v24 contract artifact is invalid") from exc
    _require(raw == v10._canonical(value), "v24 contract bytes are not canonical")
    _require(value == _build_contract(root), "v24 contract differs from source")
    return value


def materialize_contract(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    value = _build_contract(root)
    raw = v10._canonical(value)
    target = v10._logical_path(root, CONTRACT_PATH, must_exist=False)
    if target.exists():
        _require(v10._read(root, CONTRACT_PATH) == raw, "v24 contract already differs")
    else:
        v10._write_once(root, CONTRACT_PATH, raw)
    return {
        "status": "OFFLINE_V24_ORDER_STABLE_CONTRACT_MATERIALIZED_ACTIVATION_CLOSED",
        "contract_id": value.contract_id,
        "contract_content_hash": value.content_hash,
        "artifact_path": CONTRACT_PATH.as_posix(),
        "artifact_file_sha256": sha256_bytes(raw),
        "artifact_bytes": len(raw),
        "diagnostic_mock_or_live_processes_launched": 0,
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
    _require(row and row[0] == commit and len(row) == 2, "v24 source parent failed")
    lines = (
        v10._git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", row[1], commit)
        .decode("utf-8")
        .splitlines()
    )
    added = tuple(sorted(parts[1] for line in lines if (parts := line.split("\t"))[:1] == ["A"]))
    _require(len(lines) == len(added), "v24 source contains non-addition changes")
    return SourceCommitBinding(commit=commit, tree=tree, parents=(row[1],), added_paths=added)


def _build_qualification(
    root: Path,
    *,
    source_commit: str,
    recorded_at: datetime,
) -> SourceQualification:
    contract = load_contract(repository=root)
    _predecessor_binding(root)
    commit = _source_commit(root, source_commit)
    pairs = tuple(v10._committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(pair[0] for pair in pairs)
    contract_index = SOURCE_FILES.index(CONTRACT_PATH)
    _require(pairs[contract_index][1] == v10._canonical(contract), "committed v24 contract differs")
    for path, pair in zip(SOURCE_FILES, pairs, strict=True):
        _require(v10._read(root, path) == pair[1], f"working v24 dependency differs: {path}")
    body = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": QUALIFICATION_STATUS,
        "recorded_at": recorded_at,
        "source_commit": commit.model_dump(mode="json"),
        "source_files": [item.model_dump(mode="json") for item in files],
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "predecessor_contract_id": V23_CONTRACT_ID,
        "predecessor_terminal_id": V23_TERMINAL_ID,
        "workload_or_runtime_evidence_created": False,
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
        "local_git_provenance_subprocesses_may_run": True,
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
        "next_gate": value.next_gate,
    }


def qualify_source(*, source_commit: str, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    value = _build_qualification(
        root,
        source_commit=source_commit,
        recorded_at=datetime.now(UTC),
    )
    raw = v10._canonical(value)
    v10._write_once(root, QUALIFICATION_PATH, raw)
    return _qualification_summary(value, raw)


def validate_source_qualification(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    raw = v10._read(root, QUALIFICATION_PATH)
    value = SourceQualification.model_validate_json(raw)
    _require(raw == v10._canonical(value), "v24 qualification bytes are not canonical")
    expected = _build_qualification(
        root,
        source_commit=value.source_commit.commit,
        recorded_at=value.recorded_at,
    )
    _require(value == expected, "v24 qualification differs from committed source")
    return _qualification_summary(value, raw)


__all__ = [
    "CONTRACT_PATH",
    "QUALIFICATION_PATH",
    "OrderStableDiagnosticContract",
    "OrderStableDiagnosticError",
    "load_contract",
    "materialize_contract",
    "qualify_source",
    "validate_source_qualification",
]
