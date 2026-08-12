"""Offline v8 correction for the consumed v7 import-bootstrap error.

Importing this module performs no Docker, dotenv, SDK client/probe, environment,
network, provider, evaluator, or agent observation.  Project dependencies may
load the OpenAI package without constructing a client.  V8 source-qualifies a
staged, value-free child diagnostic and the narrow ``SYSTEMROOT`` pass-through
contract.  It intentionally has no state, approval, attempt, or run entrypoint.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from patchloop.contracts import FrozenStrictModel
from patchloop.errors import ContractError
from patchloop.evals import no_start_executable_preflight as v5
from patchloop.evals import sanitized_sdk_diagnostic_successor as v6
from patchloop.evals import sanitized_sdk_parent_integration as v7
from patchloop.util import sha256_bytes, sha256_json
from scripts import run_sanitized_sdk_import_bootstrap_child as child

CONTRACT_SCHEMA_VERSION = "sanitized-sdk-import-bootstrap-successor-contract-v8"
CONTRACT_VERSION = "ac-evaluator-v2-sanitized-sdk-import-bootstrap-v8"
CONTRACT_PATH = Path("experiments/evaluator-v2-sanitized-sdk-import-bootstrap-v8.contract.json")

PREDECESSOR_TERMINAL_COMMIT = "3cde67ba12390af328979d58b52551f1761f7cb3"
PREDECESSOR_PRESERVATION_COMMIT = "9ec874ce81b76c4c1e885c350ab3089ee8782e80"
PREDECESSOR_TERMINAL_ID = (
    "ncpterminal_a6ad48867773cc2614861cadfbece94c646fa2b7aef453facc7fd37fe4dd537c"
)

RUNTIME_PATH = Path("patchloop/evals/sanitized_sdk_import_bootstrap_successor.py")
CHILD_PATH = Path("scripts/run_sanitized_sdk_import_bootstrap_child.py")
BUILD_SCRIPT_PATH = Path("scripts/build_sanitized_sdk_import_bootstrap_successor.py")
TEST_PATH = Path("tests/test_sanitized_sdk_import_bootstrap_successor.py")

QUALIFICATION_SCHEMA_VERSION = "sanitized-sdk-import-bootstrap-source-qualification-v8"
QUALIFICATION_ID = "ac-evaluator-v2-sanitized-sdk-import-bootstrap-source-20260812-r1"
QUALIFICATION_STATUS = "OFFLINE_SANITIZED_SDK_IMPORT_BOOTSTRAP_SOURCE_QUALIFIED_LIVE_CLOSED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-sanitized-sdk-import-bootstrap-v8-source-qualification.json"
)
NEXT_GATE = "import-bootstrap-parent-integration-successor"

SOURCE_ADDED_PATHS = tuple(
    sorted(
        path.as_posix()
        for path in (CONTRACT_PATH, RUNTIME_PATH, CHILD_PATH, BUILD_SCRIPT_PATH, TEST_PATH)
    )
)
SOURCE_FILES = tuple(
    sorted(
        (
            CONTRACT_PATH,
            RUNTIME_PATH,
            CHILD_PATH,
            BUILD_SCRIPT_PATH,
            TEST_PATH,
            v7.CONTRACT_PATH,
            v7.RUNTIME_PATH,
            v7.QUALIFICATION_PATH,
            v7.TERMINAL_PATH,
            v6.RUNTIME_PATH,
            v6.CHILD_PATH,
            v5.D137_PATH,
        ),
        key=lambda item: item.as_posix(),
    )
)

V7_CHILD_ENVIRONMENT_NAMES = tuple(sorted(v7.CHILD_ENVIRONMENT))
REQUIRED_BOOTSTRAP_PASSTHROUGH_NAMES = ("SYSTEMROOT",)
OFFLINE_REPRODUCTION_STAGE = "versioned_preflight"
OFFLINE_REPRODUCTION_ERROR = "winerror_10106"


class SanitizedSDKImportBootstrapError(ContractError):
    """The v8 import-bootstrap contract failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SanitizedSDKImportBootstrapError(message)


def _root(repository: str | Path | None) -> Path:
    return v5._repo_root(repository)


def _read(root: Path, path: Path) -> bytes:
    return v5._read_bytes(root, path)


def _canonical(value: FrozenStrictModel) -> bytes:
    return v5._canonical_bytes(value)


def _hash_body(body: dict[str, Any]) -> str:
    return v5._semantic_hash(body)


def _derived_id(prefix: str, content_hash: str) -> str:
    return v5._derived_id(prefix, content_hash)


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
        raise SanitizedSDKImportBootstrapError("local Git source read failed") from exc
    _require(completed.returncode == 0, "local Git source read failed")
    return completed.stdout


class ImportStage(StrEnum):
    SYSTEMROOT_PRESENCE = "systemroot_presence"
    DOTENV_PARSER = "dotenv_parser"
    D137_RUNTIME = "d137_runtime"
    VERSIONED_PREFLIGHT = "versioned_preflight"
    EXECUTABLE_PREFLIGHT = "executable_preflight"
    MANUAL_START_PREFLIGHT = "manual_start_preflight"
    NO_START_PREFLIGHT = "no_start_preflight"
    SANITIZED_DIAGNOSTIC = "sanitized_diagnostic"
    COMPLETE = "complete"


class ImportCode(StrEnum):
    READY = "ready"
    SYSTEMROOT_PRESENCE_ERROR = "systemroot_presence_error"
    SYSTEMROOT_MISSING = "systemroot_missing"
    SYSTEMROOT_EMPTY = "systemroot_empty"
    DOTENV_PARSER_IMPORT_ERROR = "dotenv_parser_import_error"
    D137_RUNTIME_IMPORT_ERROR = "d137_runtime_import_error"
    VERSIONED_PREFLIGHT_IMPORT_ERROR = "versioned_preflight_import_error"
    EXECUTABLE_PREFLIGHT_IMPORT_ERROR = "executable_preflight_import_error"
    MANUAL_START_PREFLIGHT_IMPORT_ERROR = "manual_start_preflight_import_error"
    NO_START_PREFLIGHT_IMPORT_ERROR = "no_start_preflight_import_error"
    SANITIZED_DIAGNOSTIC_IMPORT_ERROR = "sanitized_diagnostic_import_error"
    INTERNAL_SANITIZER_ERROR = "internal_sanitizer_error"


ERROR_CODE_BY_STAGE = {
    ImportStage.DOTENV_PARSER: ImportCode.DOTENV_PARSER_IMPORT_ERROR,
    ImportStage.D137_RUNTIME: ImportCode.D137_RUNTIME_IMPORT_ERROR,
    ImportStage.VERSIONED_PREFLIGHT: ImportCode.VERSIONED_PREFLIGHT_IMPORT_ERROR,
    ImportStage.EXECUTABLE_PREFLIGHT: ImportCode.EXECUTABLE_PREFLIGHT_IMPORT_ERROR,
    ImportStage.MANUAL_START_PREFLIGHT: ImportCode.MANUAL_START_PREFLIGHT_IMPORT_ERROR,
    ImportStage.NO_START_PREFLIGHT: ImportCode.NO_START_PREFLIGHT_IMPORT_ERROR,
    ImportStage.SANITIZED_DIAGNOSTIC: ImportCode.SANITIZED_DIAGNOSTIC_IMPORT_ERROR,
}
STAGE_ORDER = tuple(ImportStage)


class ImportActivity(FrozenStrictModel):
    systemroot_membership_check_count: int = Field(ge=0, le=1)
    systemroot_nonempty_check_count: int = Field(ge=0, le=1)
    import_attempt_count: int = Field(ge=0, le=len(child.IMPORT_STAGES))
    import_completed_count: int = Field(ge=0, le=len(child.IMPORT_STAGES))
    environment_value_return_count: Literal[0] = 0
    exception_message_type_repr_or_traceback_return_count: Literal[0] = 0
    dotenv_file_read_count: Literal[0] = 0
    sdk_package_import_count: int = Field(ge=0, le=1)
    sdk_client_or_probe_count: Literal[0] = 0
    transport_dispatch_count: Literal[0] = 0
    network_call_count: Literal[0] = 0
    provider_evaluator_agent_call_count: Literal[0] = 0


class ImportBootstrapObservation(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-import-bootstrap-observation-v1"]
    state: Literal["ready", "blocked", "error"]
    stage: ImportStage
    code: ImportCode
    attempted_stages: tuple[ImportStage, ...]
    completed_stages: tuple[ImportStage, ...]
    systemroot_present: bool
    systemroot_nonempty: bool
    systemroot_value_returned: Literal[False] = False
    exception_message_type_repr_or_traceback_returned: Literal[False] = False
    activity: ImportActivity

    @model_validator(mode="after")
    def validate_semantics(self) -> ImportBootstrapObservation:
        attempted = self.attempted_stages
        completed = self.completed_stages
        if not attempted or self.stage != attempted[-1]:
            raise ValueError("v8 final import stage differs")
        if tuple(stage for stage in STAGE_ORDER if stage in attempted) != attempted:
            raise ValueError("v8 attempted import stages are not canonical")
        if completed != attempted[: len(completed)]:
            raise ValueError("v8 completed import stages are not a prefix")
        expected_import_attempts = sum(
            stage not in {ImportStage.SYSTEMROOT_PRESENCE, ImportStage.COMPLETE}
            for stage in attempted
        )
        expected_import_completed = sum(
            stage not in {ImportStage.SYSTEMROOT_PRESENCE, ImportStage.COMPLETE}
            for stage in completed
        )
        if (
            self.activity.import_attempt_count != expected_import_attempts
            or self.activity.import_completed_count != expected_import_completed
        ):
            raise ValueError("v8 import activity projection differs")
        if self.code == ImportCode.INTERNAL_SANITIZER_ERROR:
            if (
                self.state != "error"
                or attempted != (ImportStage.SYSTEMROOT_PRESENCE,)
                or completed
                or self.activity.systemroot_membership_check_count != 0
            ):
                raise ValueError("v8 internal sanitizer state differs")
            return self
        if self.activity.systemroot_membership_check_count != 1:
            raise ValueError("v8 SYSTEMROOT membership accounting differs")
        expected_nonempty_checks = int(self.systemroot_present)
        if self.activity.systemroot_nonempty_check_count != expected_nonempty_checks:
            raise ValueError("v8 SYSTEMROOT nonempty accounting differs")
        if self.state == "blocked":
            expected_code = (
                ImportCode.SYSTEMROOT_MISSING
                if not self.systemroot_present
                else ImportCode.SYSTEMROOT_EMPTY
            )
            if (
                self.stage != ImportStage.SYSTEMROOT_PRESENCE
                or self.code != expected_code
                or completed != attempted
                or self.systemroot_nonempty
                or self.activity.import_attempt_count != 0
            ):
                raise ValueError("v8 blocked bootstrap state differs")
            return self
        if self.state == "ready":
            if (
                self.stage != ImportStage.COMPLETE
                or self.code != ImportCode.READY
                or attempted != STAGE_ORDER
                or completed != STAGE_ORDER
                or not self.systemroot_present
                or not self.systemroot_nonempty
            ):
                raise ValueError("v8 ready bootstrap state differs")
            return self
        if self.stage == ImportStage.SYSTEMROOT_PRESENCE:
            if (
                self.code != ImportCode.SYSTEMROOT_PRESENCE_ERROR
                or completed
                or self.systemroot_present
                or self.systemroot_nonempty
            ):
                raise ValueError("v8 SYSTEMROOT checker error differs")
            return self
        if (
            self.code != ERROR_CODE_BY_STAGE.get(self.stage)
            or len(completed) != len(attempted) - 1
            or not self.systemroot_present
            or not self.systemroot_nonempty
        ):
            raise ValueError("v8 import error state differs")
        return self


class V7TerminalBinding(FrozenStrictModel):
    terminal_commit: Literal["3cde67ba12390af328979d58b52551f1761f7cb3"] = (
        PREDECESSOR_TERMINAL_COMMIT
    )
    preservation_commit: Literal["9ec874ce81b76c4c1e885c350ab3089ee8782e80"] = (
        PREDECESSOR_PRESERVATION_COMMIT
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    state_evidence_id: str = Field(pattern=r"^ncpstate_[0-9a-f]{64}$")
    approval_id: str = Field(pattern=r"^ncpapproval_[0-9a-f]{64}$")
    attempt_id: str = Field(pattern=r"^ncpattempt_[0-9a-f]{64}$")
    action_started_id: str = Field(pattern=r"^ncpstarted_[0-9a-f]{64}$")
    terminal_id: Literal[
        "ncpterminal_a6ad48867773cc2614861cadfbece94c646fa2b7aef453facc7fd37fe4dd537c"
    ] = PREDECESSOR_TERMINAL_ID
    terminal_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    outcome: Literal["error"] = "error"
    reason: Literal["sdk_diagnostic_error"] = "sdk_diagnostic_error"
    docker_ready: Literal[True] = True
    docker_cli_command_count: Literal[8] = 8
    dotenv_exact_subject_declared: Literal[True] = True
    dotenv_exact_subject_nonempty: Literal[True] = True
    child_error_code: Literal["diagnostic_runtime_import_error"] = "diagnostic_runtime_import_error"
    child_launch_attempt_count: Literal[1] = 1
    transport_dispatch_count: Literal[0] = 0
    network_call_count: Literal[0] = 0
    provider_evaluator_agent_call_count: Literal[0] = 0
    activity_accounting_complete: Literal[True] = True
    unknown_post_marker_activity_possible: Literal[False] = False
    retry_or_resume_allowed: Literal[False] = False


class ImportBootstrapProfile(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-import-bootstrap-profile-v1"] = (
        "sanitized-sdk-import-bootstrap-profile-v1"
    )
    child_path: Literal["scripts/run_sanitized_sdk_import_bootstrap_child.py"] = (
        CHILD_PATH.as_posix()
    )
    child_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v7_child_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v7_runtime_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v6_runtime_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    d137_runtime_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v7_child_environment_names: tuple[str, ...] = V7_CHILD_ENVIRONMENT_NAMES
    required_bootstrap_passthrough_names: tuple[str, ...] = REQUIRED_BOOTSTRAP_PASSTHROUGH_NAMES
    bootstrap_value_return_limit: Literal[0] = 0
    exception_message_type_repr_or_traceback_return_limit: Literal[0] = 0
    exact_import_stages: tuple[str, ...] = tuple(stage.value for stage in STAGE_ORDER)
    exact_import_codes: tuple[str, ...] = tuple(code.value for code in ImportCode)
    exact_import_modules: tuple[str, ...] = tuple(module for _stage, module in child.IMPORT_STAGES)
    offline_reproduction_stage: Literal["versioned_preflight"] = OFFLINE_REPRODUCTION_STAGE
    offline_reproduction_error: Literal["winerror_10106"] = OFFLINE_REPRODUCTION_ERROR
    offline_reproduction_bootstrap_import: Literal["asyncio.windows_events"] = (
        "asyncio.windows_events"
    )
    corrected_environment_mode: Literal["fixed-base-plus-systemroot-passthrough"] = (
        "fixed-base-plus-systemroot-passthrough"
    )
    dotenv_sdk_client_probe_or_network_observation_in_source_limit: Literal[0] = 0
    future_sdk_package_import_limit: Literal[1] = 1
    future_sdk_client_or_probe_limit: Literal[0] = 0
    parent_runtime_integration_implemented: Literal[False] = False
    state_approval_or_attempt_entrypoint_implemented: Literal[False] = False

    @model_validator(mode="after")
    def validate_profile(self) -> ImportBootstrapProfile:
        if self.v7_child_environment_names != V7_CHILD_ENVIRONMENT_NAMES:
            raise ValueError("v8 predecessor child environment drifted")
        if self.required_bootstrap_passthrough_names != REQUIRED_BOOTSTRAP_PASSTHROUGH_NAMES:
            raise ValueError("v8 bootstrap pass-through drifted")
        if self.exact_import_stages != tuple(stage.value for stage in STAGE_ORDER):
            raise ValueError("v8 import stages drifted")
        if self.exact_import_codes != tuple(code.value for code in ImportCode):
            raise ValueError("v8 import codes drifted")
        if self.exact_import_modules != tuple(module for _stage, module in child.IMPORT_STAGES):
            raise ValueError("v8 import module inventory drifted")
        return self


class SourceAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    source_qualification_authorized: Literal[True] = True
    parent_runtime_integration_authorized: Literal[False] = False
    state_binding_or_exact_approval_authorized: Literal[False] = False
    docker_dotenv_sdk_client_probe_or_environment_observation_authorized: Literal[False] = False
    systemroot_value_recording_authorized: Literal[False] = False
    network_or_transport_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False
    retry_replacement_or_resume_authorized: Literal[False] = False


class ImportBootstrapContract(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-import-bootstrap-successor-contract-v8"] = (
        CONTRACT_SCHEMA_VERSION
    )
    contract_version: Literal["ac-evaluator-v2-sanitized-sdk-import-bootstrap-v8"] = (
        CONTRACT_VERSION
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor: V7TerminalBinding
    profile: ImportBootstrapProfile
    source_authority: SourceAuthority
    next_gate: Literal["import-bootstrap-parent-integration-successor"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> ImportBootstrapContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected = sha256_json(body)
        if self.content_hash != expected:
            raise ValueError("v8 contract hash mismatch")
        if self.contract_id != _derived_id("ncpcontract", expected):
            raise ValueError("v8 contract id mismatch")
        return self


class SourceCommitBinding(FrozenStrictModel):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    parents: tuple[str, ...]
    added_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_source(self) -> SourceCommitBinding:
        if self.parents != (PREDECESSOR_PRESERVATION_COMMIT,):
            raise ValueError("v8 source predecessor drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v8 source additions drifted")
        return self


class QualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    source_qualified: Literal[True] = True
    runtime_state_approval_attempt_or_terminal_created: Literal[False] = False
    docker_sdk_client_probe_dotenv_environment_network_or_provider_observation_count: Literal[0] = 0
    external_mutation_count: Literal[0] = 0
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class SourceQualification(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-import-bootstrap-source-qualification-v8"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal[
        "ac-evaluator-v2-sanitized-sdk-import-bootstrap-source-20260812-r1"
    ] = QUALIFICATION_ID
    status: Literal["OFFLINE_SANITIZED_SDK_IMPORT_BOOTSTRAP_SOURCE_QUALIFIED_LIVE_CLOSED"] = (
        QUALIFICATION_STATUS
    )
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[v5.CommittedFileBinding, ...]
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    contract_file: v5.CommittedFileBinding
    runtime_file: v5.CommittedFileBinding
    child_file: v5.CommittedFileBinding
    predecessor_terminal_file: v5.CommittedFileBinding
    authority: QualificationAuthority
    next_gate: Literal["import-bootstrap-parent-integration-successor"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v8 qualification recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> SourceQualification:
        expected_paths = tuple(path.as_posix() for path in SOURCE_FILES)
        if tuple(item.path for item in self.source_files) != expected_paths:
            raise ValueError("v8 qualification inventory drifted")
        by_path = {item.path: item for item in self.source_files}
        for projection, path in (
            (self.contract_file, CONTRACT_PATH),
            (self.runtime_file, RUNTIME_PATH),
            (self.child_file, CHILD_PATH),
            (self.predecessor_terminal_file, v7.TERMINAL_PATH),
        ):
            if projection != by_path.get(path.as_posix()):
                raise ValueError("v8 qualification projection drifted")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != sha256_json(body):
            raise ValueError("v8 qualification hash mismatch")
        return self


def validate_child_observation(payload: bytes) -> ImportBootstrapObservation:
    try:
        return ImportBootstrapObservation.model_validate_json(payload)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise SanitizedSDKImportBootstrapError("v8 child observation is invalid") from exc


def _load_v7_terminal(root: Path) -> tuple[v7.ParentIntegrationContract, v7.TerminalTransition]:
    v7.validate_attempt_chain(repository=root)
    contract = v7.load_contract(repository=root)
    raw = _read(root, v7.TERMINAL_PATH)
    terminal = v7.TerminalTransition.model_validate_json(raw)
    _require(raw == _canonical(terminal), "v7 terminal bytes are not canonical")
    _require(terminal.terminal_id == PREDECESSOR_TERMINAL_ID, "v7 terminal identity drifted")
    _require(
        _git(root, "show", f"{PREDECESSOR_TERMINAL_COMMIT}:{v7.TERMINAL_PATH.as_posix()}") == raw,
        "v7 terminal is not bound to its terminal commit",
    )
    row = (
        _git(root, "rev-list", "--parents", "-n", "1", PREDECESSOR_PRESERVATION_COMMIT)
        .decode("ascii")
        .split()
    )
    _require(
        row == [PREDECESSOR_PRESERVATION_COMMIT, PREDECESSOR_TERMINAL_COMMIT],
        "v7 preservation commit does not directly follow terminal",
    )
    return contract, terminal


def _predecessor_binding(root: Path) -> V7TerminalBinding:
    contract, terminal = _load_v7_terminal(root)
    v7.validate_source_qualification(repository=root)
    qualification = v7.SourceQualification.model_validate_json(_read(root, v7.QUALIFICATION_PATH))
    observation = terminal.observation
    _require(observation.docker_observation is not None, "v7 Docker observation missing")
    _require(observation.child_execution is not None, "v7 child execution missing")
    _require(observation.child_execution.child is not None, "v7 child observation missing")
    child_observation = observation.child_execution.child
    return V7TerminalBinding(
        contract_id=contract.contract_id,
        source_qualification_hash=qualification.content_hash,
        state_evidence_id=v7.StateEvidence.model_validate_json(
            _read(root, v7.STATE_PATH)
        ).evidence_id,
        approval_id=v7.ApprovalBinding.model_validate_json(
            _read(root, v7.APPROVAL_PATH)
        ).approval_id,
        attempt_id=v7.AttemptIntent.model_validate_json(_read(root, v7.ATTEMPT_PATH)).attempt_id,
        action_started_id=v7.ActionStarted.model_validate_json(
            _read(root, v7.ACTION_STARTED_PATH)
        ).marker_id,
        terminal_content_hash=terminal.content_hash,
        docker_ready=observation.docker_observation["passed"],
        docker_cli_command_count=observation.docker_cli_command_count,
        dotenv_exact_subject_declared=child_observation.dotenv.exact_subject_declared,
        dotenv_exact_subject_nonempty=child_observation.dotenv.exact_subject_nonempty,
        child_error_code=child_observation.error_code,
        child_launch_attempt_count=observation.child_launch_attempt_count,
        transport_dispatch_count=child_observation.activity.transport_dispatch_count,
        network_call_count=observation.network_call_count,
        provider_evaluator_agent_call_count=observation.provider_evaluator_agent_call_count,
        activity_accounting_complete=observation.activity_accounting_complete,
        unknown_post_marker_activity_possible=observation.unknown_post_marker_activity_possible,
        retry_or_resume_allowed=False,
    )


def _build_contract(root: Path) -> ImportBootstrapContract:
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "predecessor": _predecessor_binding(root).model_dump(mode="json"),
        "profile": ImportBootstrapProfile(
            child_file_sha256=sha256_bytes(_read(root, CHILD_PATH)),
            v7_child_file_sha256=sha256_bytes(_read(root, v6.CHILD_PATH)),
            v7_runtime_file_sha256=sha256_bytes(_read(root, v7.RUNTIME_PATH)),
            v6_runtime_file_sha256=sha256_bytes(_read(root, v6.RUNTIME_PATH)),
            d137_runtime_file_sha256=sha256_bytes(_read(root, v5.D137_PATH)),
        ).model_dump(mode="json"),
        "source_authority": SourceAuthority().model_dump(mode="json"),
        "next_gate": NEXT_GATE,
    }
    content_hash = _hash_body(body)
    return ImportBootstrapContract(
        **body,
        contract_id=_derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def load_contract(*, repository: str | Path | None = None) -> ImportBootstrapContract:
    root = _root(repository)
    raw = _read(root, CONTRACT_PATH)
    try:
        value = ImportBootstrapContract.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise SanitizedSDKImportBootstrapError("v8 contract artifact is invalid") from exc
    _require(raw == _canonical(value), "v8 contract bytes are not canonical")
    _require(value == _build_contract(root), "v8 contract has drifted")
    return value


def materialize_contract(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _root(repository)
    target = v5._logical_path(root, CONTRACT_PATH, must_exist=False)
    if target.exists():
        value = load_contract(repository=root)
        raw = _read(root, CONTRACT_PATH)
    else:
        value = _build_contract(root)
        raw = _canonical(value)
        v5._write_once(root, CONTRACT_PATH, raw)
    return {
        "status": "OFFLINE_SANITIZED_SDK_IMPORT_BOOTSTRAP_CONTRACT_MATERIALIZED_LIVE_CLOSED",
        "contract_id": value.contract_id,
        "contract_content_hash": value.content_hash,
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
    }


def _source_commit(root: Path, selected: str) -> SourceCommitBinding:
    commit = _git(root, "rev-parse", f"{selected}^{{commit}}").decode("ascii").strip()
    tree = _git(root, "rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    row = _git(root, "rev-list", "--parents", "-n", "1", commit).decode("ascii").split()
    _require(row and row[0] == commit and len(row) == 2, "v8 source parent binding failed")
    lines = (
        _git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", row[1], commit)
        .decode("utf-8")
        .splitlines()
    )
    added = tuple(sorted(parts[1] for line in lines if (parts := line.split("\t"))[:1] == ["A"]))
    _require(len(lines) == len(added), "v8 source commit contains non-addition changes")
    return SourceCommitBinding(commit=commit, tree=tree, parents=(row[1],), added_paths=added)


def _build_qualification(
    root: Path, *, source_commit: str, recorded_at: datetime
) -> SourceQualification:
    contract = load_contract(repository=root)
    commit = _source_commit(root, source_commit)
    pairs = tuple(v5._committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(item[0] for item in pairs)
    by_path = {item.path: item for item in files}
    contract_index = SOURCE_FILES.index(CONTRACT_PATH)
    _require(pairs[contract_index][1] == _canonical(contract), "committed v8 contract differs")
    body = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": QUALIFICATION_STATUS,
        "recorded_at": recorded_at,
        "source_commit": commit.model_dump(mode="json"),
        "source_files": tuple(item.model_dump(mode="json") for item in files),
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "contract_file": by_path[CONTRACT_PATH.as_posix()].model_dump(mode="json"),
        "runtime_file": by_path[RUNTIME_PATH.as_posix()].model_dump(mode="json"),
        "child_file": by_path[CHILD_PATH.as_posix()].model_dump(mode="json"),
        "predecessor_terminal_file": by_path[v7.TERMINAL_PATH.as_posix()].model_dump(mode="json"),
        "authority": QualificationAuthority().model_dump(mode="json"),
        "next_gate": NEXT_GATE,
    }
    return SourceQualification(**body, content_hash=_hash_body(body))


def qualify_source(
    *, source_commit: str = "HEAD", repository: str | Path | None = None
) -> dict[str, Any]:
    root = _root(repository)
    target = v5._logical_path(root, QUALIFICATION_PATH, must_exist=False)
    if not target.exists():
        value = _build_qualification(
            root, source_commit=source_commit, recorded_at=datetime.now(UTC)
        )
        v5._write_once(root, QUALIFICATION_PATH, _canonical(value))
    return validate_source_qualification(repository=root)


def validate_source_qualification(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _root(repository)
    raw = _read(root, QUALIFICATION_PATH)
    try:
        value = SourceQualification.model_validate_json(raw)
    except (ValidationError, UnicodeDecodeError) as exc:
        raise SanitizedSDKImportBootstrapError("v8 source qualification is invalid") from exc
    _require(raw == _canonical(value), "v8 qualification bytes are not canonical")
    expected = _build_qualification(
        root,
        source_commit=value.source_commit.commit,
        recorded_at=value.recorded_at,
    )
    _require(value == expected, "v8 source qualification has drifted")
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


__all__ = [
    "BUILD_SCRIPT_PATH",
    "CHILD_PATH",
    "CONTRACT_PATH",
    "ImportBootstrapContract",
    "ImportBootstrapObservation",
    "ImportCode",
    "ImportStage",
    "NEXT_GATE",
    "PREDECESSOR_TERMINAL_ID",
    "QUALIFICATION_PATH",
    "RUNTIME_PATH",
    "SOURCE_ADDED_PATHS",
    "SOURCE_FILES",
    "SanitizedSDKImportBootstrapError",
    "SourceQualification",
    "TEST_PATH",
    "load_contract",
    "materialize_contract",
    "qualify_source",
    "validate_child_observation",
    "validate_source_qualification",
]
