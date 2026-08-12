"""Offline-only v21 envelope diagnostic for the consumed v20 failure.

V20 is immutable and its exact failure cause is not recoverable from the
persisted evidence.  V21 therefore does not retry v20 and does not claim that
the predecessor was truncated.  It adds a source-only, fixed-public-fixture
diagnostic for the two anonymous-pipe hops, complete writes, and staged frame
decoding.  Import, contract materialization, and source qualification perform
no Docker, dotenv, SDK, network, provider, evaluator, agent, or credential
observation.  Qualification may launch exactly two local fixture processes.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from patchloop.contracts import FrozenStrictModel
from patchloop.errors import ContractError
from patchloop.evals import dual_pipe_activation_successor as v20
from patchloop.util import sha256_bytes

v19 = v20.v19
v10 = v20.v10

CONTRACT_SCHEMA_VERSION = "envelope-diagnostic-preflight-successor-contract-v21"
CONTRACT_VERSION = "ac-evaluator-v2-envelope-diagnostic-preflight-successor-v21"
CONTRACT_PATH = Path(
    "experiments/evaluator-v2-envelope-diagnostic-preflight-successor-v21.contract.json"
)
RUNTIME_PATH = Path("patchloop/evals/envelope_diagnostic_preflight_successor.py")
SUPERVISOR_PATH = Path("scripts/run_sanitized_sdk_bootstrap_envelope_diagnostic_v21.py")
BUILD_SCRIPT_PATH = Path("scripts/build_envelope_diagnostic_preflight_successor.py")
TEST_PATH = Path("tests/test_envelope_diagnostic_preflight_successor.py")

SOURCE_PARENT_COMMIT = "ac804d2db098c734d91bc88d285c936953763ad4"
V20_SOURCE_COMMIT = "304da8e9e4fe0d730c184944006e4c76970c12f0"
V20_SOURCE_TREE = "0f43651ed75142c48b29b42664dbf90b22a37291"
V20_QUALIFICATION_COMMIT = "23e8a049b51a66a85f1db5651f9978ac21bd7433"
V20_EVIDENCE_COMMIT = "5cc6b9692e16012a8efe1c39a109e2be375dfa37"
QUALIFICATION_SCHEMA_VERSION = "envelope-diagnostic-source-qualification-v21"
QUALIFICATION_ID = "ac-evaluator-v2-envelope-diagnostic-source-20260813-r1"
QUALIFICATION_STATUS = "OFFLINE_V21_ENVELOPE_DIAGNOSTIC_SOURCE_QUALIFIED_ACTIVATION_CLOSED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-envelope-diagnostic-preflight-v21-source-qualification.json"
)
NEXT_GATE = "new-versioned-state-and-activation-wrapper-required"
FIXTURE_RUNTIME = (
    "patchloop.evals.envelope_diagnostic_preflight_successor.run_offline_fixed_fixture_chain"
)
FRAME_BODY_LIMIT = 262_144
FRAME_OUTPUT_LIMIT = FRAME_BODY_LIMIT + 36
PROCESS_TIMEOUT_SECONDS = 30
CHILD_FLAGS = ("-I", "-E", "-s", "-B")
FIXED_CHILD_ENVIRONMENT = {
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUTF8": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "SYSTEMROOT": r"C:\Windows",
}
DECODE_STAGES = (
    "no_message",
    "not_evaluated",
    "read_error",
    "output_limit",
    "header_invalid",
    "body_length_invalid",
    "frame_length_invalid",
    "digest_invalid",
    "utf8_invalid",
    "json_invalid",
    "object_invalid",
    "schema_invalid",
    "semantic_invalid",
    "valid",
)

SOURCE_ADDED_PATHS = tuple(
    sorted(
        path.as_posix()
        for path in (CONTRACT_PATH, RUNTIME_PATH, SUPERVISOR_PATH, BUILD_SCRIPT_PATH, TEST_PATH)
    )
)
SOURCE_FILES = tuple(
    sorted(
        (
            CONTRACT_PATH,
            RUNTIME_PATH,
            SUPERVISOR_PATH,
            BUILD_SCRIPT_PATH,
            TEST_PATH,
            v20.CONTRACT_PATH,
            v20.RUNTIME_PATH,
            v20.QUALIFICATION_PATH,
            v20.STATE_PATH,
            v20.APPROVAL_PATH,
            v20.RUN_AUTHORIZATION_PATH,
            v20.ATTEMPT_PATH,
            v20.ACTION_STARTED_PATH,
            v20.TERMINAL_PATH,
            v19.CONTRACT_PATH,
            v19.RUNTIME_PATH,
            v19.SUPERVISOR_PATH,
            v19.QUALIFICATION_PATH,
        ),
        key=lambda path: path.as_posix(),
    )
)


class EnvelopeDiagnosticError(ContractError):
    """The source-only v21 envelope diagnostic failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EnvelopeDiagnosticError(message)


class V20FailureBinding(FrozenStrictModel):
    source_commit: Literal["304da8e9e4fe0d730c184944006e4c76970c12f0"] = V20_SOURCE_COMMIT
    source_tree: Literal["0f43651ed75142c48b29b42664dbf90b22a37291"] = V20_SOURCE_TREE
    qualification_commit: Literal["23e8a049b51a66a85f1db5651f9978ac21bd7433"] = (
        V20_QUALIFICATION_COMMIT
    )
    evidence_commit: Literal["5cc6b9692e16012a8efe1c39a109e2be375dfa37"] = V20_EVIDENCE_COMMIT
    contract_id: Literal[
        "ncpcontract_2c5d22d26c1ae017e8b78d0e99fe99d33b5916b8282a1c186f25fbd818f68102"
    ]
    contract_file_sha256: Literal[
        "sha256:365faf9b149c71c31a4da84fa751165685324fbaa64349fddf64d025103782f3"
    ]
    contract_file_bytes: Literal[4237] = 4237
    source_qualification_hash: Literal[
        "sha256:6e6a58dcaa1f034ad6146e955bdcd9a289b4031ec261ed22d71fc5264f8fe90b"
    ]
    source_qualification_file_sha256: Literal[
        "sha256:980ab39f6e8a661426005c659c3a18cfc8bfe62ad3fd279981c1f52a32ce9c55"
    ]
    source_qualification_file_bytes: Literal[3757] = 3757
    terminal_id: Literal[
        "ncpterminal_d528eb39f0e367fe8b38b81ae3a3ddbd627d9c9cefe6a84e8874523b7e488897"
    ]
    terminal_file_sha256: Literal[
        "sha256:6ddeabb4fb8f6632887382c9a5f9f1bf4f16dd721873d75af439b4b2e2c2c60b"
    ]
    terminal_file_bytes: Literal[22558] = 22558
    outcome: Literal["error"] = "error"
    reason: Literal["child_checker_error"] = "child_checker_error"
    base_child_code: Literal["child_output_invalid"] = "child_output_invalid"
    supervisor_code: Literal["supervised_output_invalid"] = "supervised_output_invalid"
    envelope_received: Literal[False] = False
    docker_cli_command_count: Literal[8] = 8
    outer_launch_attempt_count: Literal[1] = 1
    outer_process_return_count: Literal[1] = 1
    outer_result_message_nonempty_count: Literal[1] = 1
    outer_result_within_limit: Literal[True] = True
    outer_returncode: Literal[0] = 0
    outer_activity_accounting_complete: Literal[True] = True
    outer_unknown_process_activity_possible: Literal[False] = False
    worker_launch_attempt_count: None = None
    worker_process_return_count: None = None
    worker_result_message_count: None = None
    network_call_count: Literal[0] = 0
    provider_evaluator_agent_call_count: Literal[0] = 0
    docker_mutation_count: Literal[0] = 0
    credential_value_metadata_count: Literal[0] = 0
    raw_supervisor_or_worker_output_persisted: Literal[False] = False
    activity_accounting_complete: Literal[False] = False
    unknown_post_marker_activity_possible: Literal[True] = True
    retry_or_resume_allowed: Literal[False] = False
    causal_detail_available: Literal[False] = False
    partial_write_proven_as_cause: Literal[False] = False


class EnvelopeDiagnosticRuntimeProfile(FrozenStrictModel):
    fixture_entrypoint: Literal[
        "patchloop.evals.envelope_diagnostic_preflight_successor.run_offline_fixed_fixture_chain"
    ] = FIXTURE_RUNTIME
    supervisor_path: Literal["scripts/run_sanitized_sdk_bootstrap_envelope_diagnostic_v21.py"] = (
        SUPERVISOR_PATH.as_posix()
    )
    supervisor_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    child_flags: tuple[str, ...] = CHILD_FLAGS
    fixed_child_environment: dict[str, str] = FIXED_CHILD_ENVIRONMENT
    frame_body_limit: Literal[262144] = FRAME_BODY_LIMIT
    frame_output_limit: Literal[262180] = FRAME_OUTPUT_LIMIT
    process_timeout_seconds: Literal[30] = PROCESS_TIMEOUT_SECONDS
    decode_stages: tuple[str, ...] = DECODE_STAGES
    parent_to_supervisor_launch_limit: Literal[1] = 1
    supervisor_to_worker_launch_limit: Literal[1] = 1
    complete_write_required_on_both_hops: Literal[True] = True
    length_and_digest_framing_required: Literal[True] = True
    invalid_raw_payload_metadata_persisted: Literal[False] = False
    offline_fixed_public_fixture_only: Literal[True] = True
    live_diagnostic_default_exposed: Literal[False] = False
    activation_runtime_exposed: Literal[False] = False
    docker_dotenv_sdk_network_or_provider_observation_limit: Literal[0] = 0
    credential_value_metadata_limit: Literal[0] = 0

    @model_validator(mode="after")
    def validate_profile(self) -> EnvelopeDiagnosticRuntimeProfile:
        if self.child_flags != CHILD_FLAGS:
            raise ValueError("v21 child flags drifted")
        if self.fixed_child_environment != FIXED_CHILD_ENVIRONMENT:
            raise ValueError("v21 fixed child environment drifted")
        if self.decode_stages != DECODE_STAGES:
            raise ValueError("v21 decode stages drifted")
        return self


class SourceAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    source_qualification_authorized: Literal[True] = True
    offline_fixed_fixture_process_launch_limit: Literal[2] = 2
    state_approval_attempt_or_terminal_creation_authorized: Literal[False] = False
    docker_dotenv_sdk_network_or_provider_observation_authorized: Literal[False] = False
    credential_value_or_metadata_recording_authorized: Literal[False] = False
    docker_start_pull_load_image_store_or_container_mutation_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class EnvelopeDiagnosticContract(FrozenStrictModel):
    schema_version: Literal["envelope-diagnostic-preflight-successor-contract-v21"] = (
        CONTRACT_SCHEMA_VERSION
    )
    contract_version: Literal["ac-evaluator-v2-envelope-diagnostic-preflight-successor-v21"] = (
        CONTRACT_VERSION
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor: V20FailureBinding
    runtime: EnvelopeDiagnosticRuntimeProfile
    authority: SourceAuthority
    correction_scope: Literal["two-hop-complete-write-and-typed-decode-stage-only"] = (
        "two-hop-complete-write-and-typed-decode-stage-only"
    )
    predecessor_retry_or_repair: Literal[False] = False
    predecessor_root_cause_established: Literal[False] = False
    readiness_or_sdk_result_created: Literal[False] = False
    execution_currently_authorized: Literal[False] = False
    next_gate: Literal["new-versioned-state-and-activation-wrapper-required"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> EnvelopeDiagnosticContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected or self.contract_id != v10._derived_id(
            "ncpcontract", expected
        ):
            raise ValueError("v21 contract identity differs")
        return self


class SourceCommitBinding(FrozenStrictModel):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    parents: tuple[str, ...]
    added_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_source(self) -> SourceCommitBinding:
        if self.parents != (SOURCE_PARENT_COMMIT,):
            raise ValueError("v21 source predecessor drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v21 source additions drifted")
        return self


class FixtureChainEvidence(FrozenStrictModel):
    schema_version: Literal["envelope-diagnostic-fixed-fixture-evidence-v21"] = (
        "envelope-diagnostic-fixed-fixture-evidence-v21"
    )
    fixture_id: Literal["v21-public-fixed-placeholder-no-dispatch"] = (
        "v21-public-fixed-placeholder-no-dispatch"
    )
    parent_supervisor_launch_attempt_count: Literal[1] = 1
    parent_supervisor_process_return_count: Literal[1] = 1
    parent_supervisor_result_message_count: Literal[1] = 1
    parent_supervisor_returncode: Literal[0] = 0
    parent_supervisor_frame_stage: Literal["valid"] = "valid"
    supervisor_worker_launch_attempt_count: Literal[1] = 1
    supervisor_worker_process_return_count: Literal[1] = 1
    supervisor_worker_result_message_count: Literal[1] = 1
    supervisor_worker_returncode: Literal[0] = 0
    supervisor_worker_frame_stage: Literal["valid"] = "valid"
    complete_framed_message_received_on_both_hops: Literal[True] = True
    dotenv_read_count: Literal[0] = 0
    sdk_import_count: Literal[0] = 0
    transport_dispatch_count: Literal[0] = 0
    network_call_count: Literal[0] = 0
    provider_evaluator_agent_call_count: Literal[0] = 0
    credential_value_or_metadata_count: Literal[0] = 0
    invalid_raw_payload_metadata_persisted: Literal[False] = False
    fixture_protocol_accounting_complete: Literal[True] = True
    process_external_activity_absence_proven: Literal[False] = False
    passed: Literal[True] = True


class QualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    source_qualified: Literal[True] = True
    offline_fixed_fixture_process_launch_count: Literal[2] = 2
    state_approval_attempt_or_terminal_created: Literal[False] = False
    docker_dotenv_sdk_network_or_provider_observation_count: Literal[0] = 0
    credential_value_or_metadata_observation_count: Literal[0] = 0
    external_mutation_count: Literal[0] = 0
    execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class SourceQualification(FrozenStrictModel):
    schema_version: Literal["envelope-diagnostic-source-qualification-v21"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal["ac-evaluator-v2-envelope-diagnostic-source-20260813-r1"] = (
        QUALIFICATION_ID
    )
    status: Literal["OFFLINE_V21_ENVELOPE_DIAGNOSTIC_SOURCE_QUALIFIED_ACTIVATION_CLOSED"] = (
        QUALIFICATION_STATUS
    )
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[v10.CommittedFileBinding, ...]
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_terminal_id: Literal[
        "ncpterminal_d528eb39f0e367fe8b38b81ae3a3ddbd627d9c9cefe6a84e8874523b7e488897"
    ]
    fixture_chain: FixtureChainEvidence
    authority: QualificationAuthority
    next_gate: Literal["new-versioned-state-and-activation-wrapper-required"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v21 qualification time must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> SourceQualification:
        expected_paths = tuple(path.as_posix() for path in SOURCE_FILES)
        if tuple(item.path for item in self.source_files) != expected_paths:
            raise ValueError("v21 qualification inventory drifted")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != v10._hash_body(body):
            raise ValueError("v21 qualification hash mismatch")
        return self


def _predecessor_binding(root: Path) -> V20FailureBinding:
    summary = v20.validate_attempt_chain(repository=root)
    _require(summary["terminal_id"].endswith("b7e488897"), "v20 attempt chain differs")
    contract_raw = v10._read(root, v20.CONTRACT_PATH)
    contract = v20.DualPipeActivationContract.model_validate_json(contract_raw)
    _require(contract_raw == v10._canonical(contract), "v20 contract bytes differ")
    _require(
        contract_raw
        == v10._git(root, "show", f"{V20_SOURCE_COMMIT}:{v20.CONTRACT_PATH.as_posix()}"),
        "v20 committed contract differs",
    )
    qualification_raw = v10._read(root, v20.QUALIFICATION_PATH)
    qualification = v20.SourceQualification.model_validate_json(qualification_raw)
    _require(
        qualification_raw == v10._canonical(qualification),
        "v20 qualification bytes differ",
    )
    _require(
        qualification_raw
        == v10._git(
            root,
            "show",
            f"{V20_QUALIFICATION_COMMIT}:{v20.QUALIFICATION_PATH.as_posix()}",
        ),
        "v20 committed qualification differs",
    )
    terminal_raw = v10._read(root, v20.TERMINAL_PATH)
    _require(
        terminal_raw
        == v10._git(root, "show", f"{V20_EVIDENCE_COMMIT}:{v20.TERMINAL_PATH.as_posix()}"),
        "v20 committed terminal differs",
    )
    terminal = v20.TerminalTransition.model_validate_json(terminal_raw)
    _require(terminal_raw == v10._canonical(terminal), "v20 terminal bytes differ")
    _require(terminal.observation is not None, "v20 terminal observation is absent")
    observation = terminal.observation
    supervised = observation.base.supervised_child_execution
    dual = observation.dual_pipe_child_execution
    child = observation.base.base.child_execution
    _require(
        supervised is not None
        and dual is not None
        and dual.parent_supervisor_transport is not None
        and child is not None,
        "v20 transport evidence is absent",
    )
    transport = dual.parent_supervisor_transport
    return V20FailureBinding(
        contract_id=contract.contract_id,
        contract_file_sha256=sha256_bytes(contract_raw),
        contract_file_bytes=len(contract_raw),
        source_qualification_hash=qualification.content_hash,
        source_qualification_file_sha256=sha256_bytes(qualification_raw),
        source_qualification_file_bytes=len(qualification_raw),
        terminal_id=terminal.terminal_id,
        terminal_file_sha256=sha256_bytes(terminal_raw),
        terminal_file_bytes=len(terminal_raw),
        outcome=terminal.outcome,
        reason=terminal.reason,
        base_child_code=child.code,
        supervisor_code=supervised.supervisor_code,
        envelope_received=supervised.envelope_received,
        docker_cli_command_count=observation.base.base.docker_cli_command_count,
        outer_launch_attempt_count=transport.launch_attempt_count,
        outer_process_return_count=transport.process_return_count,
        outer_result_message_nonempty_count=transport.result_message_nonempty_count,
        outer_result_within_limit=transport.result_within_limit,
        outer_returncode=transport.returncode,
        outer_activity_accounting_complete=transport.activity_accounting_complete,
        outer_unknown_process_activity_possible=transport.unknown_process_activity_possible,
        worker_launch_attempt_count=supervised.worker_launch_attempt_count,
        worker_process_return_count=supervised.worker_process_return_count,
        worker_result_message_count=supervised.worker_result_message_count,
        network_call_count=terminal.network_call_count,
        provider_evaluator_agent_call_count=terminal.provider_evaluator_agent_call_count,
        docker_mutation_count=(
            terminal.docker_start_pull_load_image_store_or_container_mutation_count
        ),
        credential_value_metadata_count=(
            terminal.credential_value_return_hash_prefix_or_length_count
        ),
        raw_supervisor_or_worker_output_persisted=(
            supervised.raw_supervisor_or_worker_output_persisted
        ),
        activity_accounting_complete=terminal.activity_accounting_complete,
        unknown_post_marker_activity_possible=terminal.unknown_post_marker_activity_possible,
        retry_or_resume_allowed=terminal.retry_or_resume_allowed,
    )


def _build_contract(root: Path) -> EnvelopeDiagnosticContract:
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "predecessor": _predecessor_binding(root).model_dump(mode="json"),
        "runtime": EnvelopeDiagnosticRuntimeProfile(
            supervisor_file_sha256=sha256_bytes(v10._read(root, SUPERVISOR_PATH))
        ).model_dump(mode="json"),
        "authority": SourceAuthority().model_dump(mode="json"),
        "correction_scope": "two-hop-complete-write-and-typed-decode-stage-only",
        "predecessor_retry_or_repair": False,
        "predecessor_root_cause_established": False,
        "readiness_or_sdk_result_created": False,
        "execution_currently_authorized": False,
        "next_gate": NEXT_GATE,
    }
    content_hash = v10._hash_body(body)
    return EnvelopeDiagnosticContract(
        **body,
        contract_id=v10._derived_id("ncpcontract", content_hash),
        content_hash=content_hash,
    )


def materialize_contract(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    value = _build_contract(root)
    raw = v10._canonical(value)
    v10._write_once(root, CONTRACT_PATH, raw)
    return {
        "status": "OFFLINE_V21_ENVELOPE_DIAGNOSTIC_CONTRACT_MATERIALIZED_LIVE_CLOSED",
        "contract_id": value.contract_id,
        "contract_content_hash": value.content_hash,
        "artifact_path": CONTRACT_PATH.as_posix(),
        "artifact_file_sha256": sha256_bytes(raw),
        "artifact_bytes": len(raw),
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
        "next_gate": "exact-source-commit-and-offline-qualification",
    }


def load_contract(*, repository: str | Path | None = None) -> EnvelopeDiagnosticContract:
    root = v10._root(repository)
    raw = v10._read(root, CONTRACT_PATH)
    value = EnvelopeDiagnosticContract.model_validate_json(raw)
    _require(raw == v10._canonical(value), "v21 contract bytes are not canonical")
    _require(value == _build_contract(root), "v21 contract differs from source")
    return value


@dataclass(frozen=True)
class _FixtureProcessOutcome:
    launch_attempt_count: int
    process_return_count: int
    frame_stage: str
    result_value: dict[str, Any] | None
    result_message_count: int
    result_within_limit: bool
    returncode: int | None
    complete: bool
    unknown: bool


class _BoundedReader:
    def __init__(self, descriptor: int, limit: int) -> None:
        self.descriptor = descriptor
        self.limit = limit
        self.buffer = bytearray()
        self.total = 0
        self.failed = False

    def decode_and_discard(self) -> tuple[str, dict[str, Any] | None, bool]:
        from scripts import run_sanitized_sdk_bootstrap_envelope_diagnostic_v21 as channel

        within_limit = not self.failed and self.total <= self.limit
        if not within_limit:
            self.buffer.clear()
            return "read_error", None, False
        raw = bytes(self.buffer)
        self.buffer.clear()
        decoded = channel.decode_supervisor_frame(raw)
        return str(decoded.stage), decoded.value, True

    def consume(self) -> None:
        try:
            while True:
                chunk = os.read(self.descriptor, 8192)
                if not chunk:
                    break
                self.total += len(chunk)
                remaining = self.limit + 1 - len(self.buffer)
                if remaining > 0:
                    self.buffer.extend(chunk[:remaining])
        except BaseException:
            self.failed = True
        finally:
            with contextlib.suppress(OSError):
                os.close(self.descriptor)


def _run_fixture_supervisor_process(
    repository: str | Path,
    *,
    supervisor_script: str | Path | None = None,
    python: str | Path | None = None,
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
) -> _FixtureProcessOutcome:
    """Launch the fixed-public-fixture supervisor with one result handle."""

    root = Path(repository).resolve(strict=True)
    script = Path(supervisor_script or root / SUPERVISOR_PATH).resolve(strict=True)
    python_path = Path(python or sys.executable).resolve(strict=True)
    read_descriptor, write_descriptor = os.pipe()
    os.set_inheritable(write_descriptor, True)
    reader = _BoundedReader(read_descriptor, FRAME_OUTPUT_LIMIT)
    thread = threading.Thread(target=reader.consume, daemon=True)
    process: subprocess.Popen[bytes] | None = None
    try:
        argv = [
            str(python_path),
            *CHILD_FLAGS,
            str(script),
            "--offline-fixed-fixture",
            "--supervisor",
        ]
        kwargs: dict[str, Any] = {
            "cwd": root,
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "shell": False,
            "env": dict(FIXED_CHILD_ENVIRONMENT),
            "close_fds": True,
        }
        if os.name == "nt":
            import msvcrt

            raw_handle = msvcrt.get_osfhandle(write_descriptor)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.lpAttributeList = {"handle_list": [raw_handle]}
            argv.extend(("--parent-result-handle", str(raw_handle)))
            kwargs["startupinfo"] = startupinfo
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        else:
            argv.extend(("--parent-result-fd", str(write_descriptor)))
            kwargs["pass_fds"] = (write_descriptor,)
        process = popen(argv, **kwargs)
    except BaseException:
        with contextlib.suppress(OSError):
            os.close(write_descriptor)
        with contextlib.suppress(OSError):
            os.close(read_descriptor)
        return _FixtureProcessOutcome(1, 0, "not_evaluated", None, 0, True, None, False, True)

    os.close(write_descriptor)
    thread.start()
    timed_out = False
    try:
        returncode = process.wait(timeout=PROCESS_TIMEOUT_SECONDS)
    except BaseException:
        timed_out = True
        try:
            process.kill()
            returncode = process.wait(timeout=5)
        except BaseException:
            returncode = None
    thread.join(timeout=5)
    if thread.is_alive():
        with contextlib.suppress(OSError):
            os.close(read_descriptor)
        thread.join(timeout=1)
    complete = not timed_out and not reader.failed and not thread.is_alive()
    frame_stage, result_value, within_limit = reader.decode_and_discard()
    return _FixtureProcessOutcome(
        launch_attempt_count=1,
        process_return_count=int(returncode is not None),
        frame_stage=frame_stage,
        result_value=result_value,
        result_message_count=int(result_value is not None),
        result_within_limit=within_limit,
        returncode=returncode,
        complete=complete,
        unknown=not complete,
    )


def _fixture_evidence_from_outcome(outcome: _FixtureProcessOutcome) -> FixtureChainEvidence:
    _require(outcome.complete and not outcome.unknown, "v21 fixture supervisor is incomplete")
    _require(outcome.process_return_count == 1 and outcome.returncode == 0, "v21 fixture failed")
    _require(outcome.result_within_limit, "v21 fixture output differs")
    from scripts import run_sanitized_sdk_bootstrap_envelope_diagnostic_v21 as channel

    _require(outcome.frame_stage == "valid", "v21 outer frame differs")
    _require(isinstance(outcome.result_value, dict), "v21 outer value differs")
    value = outcome.result_value
    _require(value.get("schema_version") == channel.SUPERVISOR_SCHEMA_VERSION, "v21 schema differs")
    fixture = value.get("fixture")
    _require(fixture == channel.fixed_worker_fixture(), "v21 fixture payload differs")
    activity = value.get("activity")
    _require(isinstance(activity, dict), "v21 fixture activity differs")
    _require(value.get("worker_frame_stage") == "valid", "v21 worker frame differs")
    return FixtureChainEvidence(
        parent_supervisor_process_return_count=outcome.process_return_count,
        parent_supervisor_result_message_count=outcome.result_message_count,
        parent_supervisor_returncode=outcome.returncode,
        parent_supervisor_frame_stage=outcome.frame_stage,
        supervisor_worker_launch_attempt_count=activity.get("worker_launch_attempt_count"),
        supervisor_worker_process_return_count=activity.get("worker_process_return_count"),
        supervisor_worker_result_message_count=activity.get("worker_result_message_count"),
        supervisor_worker_returncode=activity.get("worker_returncode"),
        supervisor_worker_frame_stage=value.get("worker_frame_stage"),
        complete_framed_message_received_on_both_hops=True,
        dotenv_read_count=activity.get("dotenv_read_count"),
        sdk_import_count=activity.get("sdk_import_count"),
        transport_dispatch_count=activity.get("transport_dispatch_count"),
        network_call_count=activity.get("network_call_count"),
        provider_evaluator_agent_call_count=activity.get("provider_evaluator_agent_call_count"),
        credential_value_or_metadata_count=activity.get("credential_value_read_count"),
        invalid_raw_payload_metadata_persisted=False,
        fixture_protocol_accounting_complete=activity.get("activity_accounting_complete"),
        process_external_activity_absence_proven=False,
        passed=(value.get("code") is None and fixture is not None),
    )


def run_offline_fixed_fixture_chain(
    *, repository: str | Path | None = None
) -> FixtureChainEvidence:
    """Run only the public no-call fixture; this is not a live preflight."""

    root = v10._root(repository)
    contract = load_contract(repository=root)
    _require(
        sha256_bytes(v10._read(root, SUPERVISOR_PATH)) == contract.runtime.supervisor_file_sha256,
        "v21 fixture supervisor differs from contract",
    )
    return _fixture_evidence_from_outcome(_run_fixture_supervisor_process(root))


def _source_commit(root: Path, selected: str) -> SourceCommitBinding:
    commit = v10._git(root, "rev-parse", f"{selected}^{{commit}}").decode("ascii").strip()
    tree = v10._git(root, "rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    row = v10._git(root, "rev-list", "--parents", "-n", "1", commit).decode().split()
    _require(row and row[0] == commit and len(row) == 2, "v21 source parent failed")
    lines = (
        v10._git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", row[1], commit)
        .decode("utf-8")
        .splitlines()
    )
    added = tuple(sorted(parts[1] for line in lines if (parts := line.split("\t"))[:1] == ["A"]))
    _require(len(lines) == len(added), "v21 source contains non-addition changes")
    return SourceCommitBinding(commit=commit, tree=tree, parents=(row[1],), added_paths=added)


def _build_qualification(
    root: Path, *, source_commit: str, recorded_at: datetime
) -> SourceQualification:
    contract = load_contract(repository=root)
    commit = _source_commit(root, source_commit)
    pairs = tuple(v10._committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(pair[0] for pair in pairs)
    contract_index = SOURCE_FILES.index(CONTRACT_PATH)
    _require(pairs[contract_index][1] == v10._canonical(contract), "committed v21 contract differs")
    for path, pair in zip(SOURCE_FILES, pairs, strict=True):
        _require(v10._read(root, path) == pair[1], f"working v21 dependency differs: {path}")
    fixture_chain = _fixture_evidence_from_outcome(_run_fixture_supervisor_process(root))
    body = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": QUALIFICATION_STATUS,
        "recorded_at": recorded_at,
        "source_commit": commit.model_dump(mode="json"),
        "source_files": [item.model_dump(mode="json") for item in files],
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "predecessor_terminal_id": contract.predecessor.terminal_id,
        "fixture_chain": fixture_chain.model_dump(mode="json"),
        "authority": QualificationAuthority().model_dump(mode="json"),
        "next_gate": NEXT_GATE,
    }
    return SourceQualification(**body, content_hash=v10._hash_body(body))


def qualify_source(*, source_commit: str, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    value = _build_qualification(root, source_commit=source_commit, recorded_at=datetime.now(UTC))
    raw = v10._canonical(value)
    v10._write_once(root, QUALIFICATION_PATH, raw)
    return _qualification_summary(value, raw)


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
        "offline_fixed_fixture_process_launch_count": 2,
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
        "next_gate": value.next_gate,
    }


def validate_source_qualification(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    raw = v10._read(root, QUALIFICATION_PATH)
    value = SourceQualification.model_validate_json(raw)
    _require(raw == v10._canonical(value), "v21 qualification bytes are not canonical")
    contract = load_contract(repository=root)
    commit = _source_commit(root, value.source_commit.commit)
    pairs = tuple(v10._committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(pair[0] for pair in pairs)
    contract_index = SOURCE_FILES.index(CONTRACT_PATH)
    _require(
        pairs[contract_index][1] == v10._canonical(contract),
        "committed v21 contract differs",
    )
    for path, pair in zip(SOURCE_FILES, pairs, strict=True):
        _require(v10._read(root, path) == pair[1], f"working v21 dependency differs: {path}")
    body = {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "status": QUALIFICATION_STATUS,
        "recorded_at": value.recorded_at,
        "source_commit": commit.model_dump(mode="json"),
        "source_files": [item.model_dump(mode="json") for item in files],
        "contract_id": contract.contract_id,
        "contract_content_hash": contract.content_hash,
        "predecessor_terminal_id": contract.predecessor.terminal_id,
        "fixture_chain": value.fixture_chain.model_dump(mode="json"),
        "authority": QualificationAuthority().model_dump(mode="json"),
        "next_gate": NEXT_GATE,
    }
    rebuilt = SourceQualification(**body, content_hash=v10._hash_body(body))
    _require(value == rebuilt, "v21 qualification differs from committed source")
    return _qualification_summary(value, raw)


__all__ = [
    "BUILD_SCRIPT_PATH",
    "CONTRACT_PATH",
    "EnvelopeDiagnosticContract",
    "EnvelopeDiagnosticError",
    "FixtureChainEvidence",
    "QUALIFICATION_PATH",
    "RUNTIME_PATH",
    "SOURCE_ADDED_PATHS",
    "SOURCE_PARENT_COMMIT",
    "SUPERVISOR_PATH",
    "TEST_PATH",
    "_build_contract",
    "load_contract",
    "materialize_contract",
    "qualify_source",
    "run_offline_fixed_fixture_chain",
    "validate_source_qualification",
]
