"""Offline-only v19 parent/supervisor framing correction.

V18 is an immutable consumed error.  V19 changes only the outer result
transport: the supervisor starts with stdout/stderr attached to null devices
and returns the unchanged v17 envelope through a separately inherited,
bounded anonymous pipe.  All observers remain injected; importing, building,
or qualifying this module performs no Docker, dotenv, SDK, network, provider,
evaluator, agent, or credential observation.
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
from patchloop.evals import supervised_frame_activation_successor as v18
from patchloop.evals import supervised_frame_preflight_successor as v17
from patchloop.util import sha256_bytes

v10 = v17.v10
v9 = v17.v9

CONTRACT_SCHEMA_VERSION = "dual-pipe-preflight-successor-contract-v19"
CONTRACT_VERSION = "ac-evaluator-v2-dual-pipe-preflight-successor-v19"
CONTRACT_PATH = Path("experiments/evaluator-v2-dual-pipe-preflight-successor-v19.contract.json")
RUNTIME_PATH = Path("patchloop/evals/dual_pipe_preflight_successor.py")
SUPERVISOR_PATH = Path("scripts/run_sanitized_sdk_bootstrap_dual_pipe_supervisor.py")
BUILD_SCRIPT_PATH = Path("scripts/build_dual_pipe_preflight_successor.py")
TEST_PATH = Path("tests/test_dual_pipe_preflight_successor.py")

SOURCE_PARENT_COMMIT = "e52deab4bbc1a83d473ba4792c85e331018f73af"
V18_EVIDENCE_COMMIT = "490f1edee9cca7c75abbe4301f52011fa40b32cb"
V18_SOURCE_COMMIT = "e4c76af0e101b1f9bc62ab2fde5ebc1c975f6f42"
V18_QUALIFICATION_COMMIT = "50a4b28e45d20adfe2e42da6ced8b4fc2da3551d"
V17_CONTRACT_ID = "ncpcontract_0344d5a846e88299373fd65a9c380b25dd3d069805790bc0c81891ef4159e76c"
V17_CONTRACT_CONTENT_HASH = (
    "sha256:0344d5a846e88299373fd65a9c380b25dd3d069805790bc0c81891ef4159e76c"
)
QUALIFICATION_SCHEMA_VERSION = "dual-pipe-preflight-source-qualification-v19"
QUALIFICATION_ID = "ac-evaluator-v2-dual-pipe-preflight-source-20260813-r1"
QUALIFICATION_STATUS = "OFFLINE_V19_DUAL_PIPE_SOURCE_QUALIFIED_ACTIVATION_CLOSED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-dual-pipe-preflight-v19-source-qualification.json"
)
NEXT_GATE = "new-versioned-state-and-activation-wrapper-required"
APPROVED_RUNTIME = "patchloop.evals.dual_pipe_preflight_successor.run_parent_preflight_injected"
APPROVED_SCOPES = (
    *v17.APPROVED_SCOPES,
    "parent-supervisor-anonymous-pipe-result-framing",
)
CHILD_FLAGS = v17.CHILD_FLAGS
FIXED_CHILD_ENVIRONMENT = v17.FIXED_CHILD_ENVIRONMENT
OUTER_CHILD_TIMEOUT_SECONDS = v17.OUTER_CHILD_TIMEOUT_SECONDS
WORKER_TIMEOUT_SECONDS = v17.WORKER_TIMEOUT_SECONDS
RESULT_OUTPUT_LIMIT = v17.CHILD_OUTPUT_LIMIT

SOURCE_ADDED_PATHS = tuple(
    sorted(
        path.as_posix()
        for path in (
            CONTRACT_PATH,
            RUNTIME_PATH,
            SUPERVISOR_PATH,
            BUILD_SCRIPT_PATH,
            TEST_PATH,
        )
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
            v18.CONTRACT_PATH,
            v18.RUNTIME_PATH,
            v18.QUALIFICATION_PATH,
            v18.TERMINAL_PATH,
            v17.CONTRACT_PATH,
            v17.RUNTIME_PATH,
            v17.CHILD_PATH,
            v17.QUALIFICATION_PATH,
        ),
        key=lambda path: path.as_posix(),
    )
)


class DualPipeSuccessorError(ContractError):
    """The source-only v19 successor failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DualPipeSuccessorError(message)


class V18FailureBinding(FrozenStrictModel):
    evidence_commit: Literal["490f1edee9cca7c75abbe4301f52011fa40b32cb"] = V18_EVIDENCE_COMMIT
    contract_id: Literal[
        "ncpcontract_3f641a1b99490ee2db17339d7613a1debf79575e45cccecbc2f2128de1d45a5c"
    ]
    source_qualification_hash: Literal[
        "sha256:6f4825ef41eea63b6cc437ec2d3f06862b21d4a665c81880e82ee42bcf6b345d"
    ]
    terminal_id: Literal[
        "ncpterminal_775512b68eac1b8f418c22a4ab30a450bf5ba8150f155f8bcbe4e5938acca516"
    ]
    terminal_content_hash: Literal[
        "sha256:775512b68eac1b8f418c22a4ab30a450bf5ba8150f155f8bcbe4e5938acca516"
    ]
    terminal_file_sha256: Literal[
        "sha256:45f7d14859fd5cafde9ec551c5a8cb16a2b798f726ceffcab304c8321281e83f"
    ]
    outcome: Literal["error"] = "error"
    reason: Literal["child_checker_error"] = "child_checker_error"
    base_child_code: Literal["child_output_invalid"] = "child_output_invalid"
    supervisor_code: Literal["supervised_output_invalid"] = "supervised_output_invalid"
    envelope_received: Literal[False] = False
    docker_cli_command_count: Literal[8] = 8
    child_launch_attempt_count: Literal[1] = 1
    child_process_return_count: Literal[1] = 1
    network_call_count: Literal[0] = 0
    provider_evaluator_agent_call_count: Literal[0] = 0
    docker_mutation_count: Literal[0] = 0
    credential_value_metadata_count: Literal[0] = 0
    raw_supervisor_or_worker_output_persisted: Literal[False] = False
    activity_accounting_complete: Literal[False] = False
    unknown_post_marker_activity_possible: Literal[True] = True
    retry_or_resume_allowed: Literal[False] = False
    causal_detail_available: Literal[False] = False


class DualPipeRuntimeProfile(FrozenStrictModel):
    entrypoint: Literal[
        "patchloop.evals.dual_pipe_preflight_successor.run_parent_preflight_injected"
    ] = APPROVED_RUNTIME
    parent_supervisor_path: Literal[
        "scripts/run_sanitized_sdk_bootstrap_dual_pipe_supervisor.py"
    ] = SUPERVISOR_PATH.as_posix()
    parent_supervisor_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v17_runtime_path: Literal["patchloop/evals/supervised_frame_preflight_successor.py"] = (
        v17.RUNTIME_PATH.as_posix()
    )
    v17_runtime_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v17_supervisor_worker_path: Literal[
        "scripts/run_sanitized_sdk_bootstrap_supervised_frame_child.py"
    ] = v17.CHILD_PATH.as_posix()
    v17_supervisor_worker_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v17_contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    v17_contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    child_flags: tuple[str, ...] = CHILD_FLAGS
    fixed_child_environment: dict[str, str] = FIXED_CHILD_ENVIRONMENT
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    parent_to_supervisor_launch_limit: Literal[1] = 1
    supervisor_to_worker_launch_limit: Literal[1] = 1
    outer_child_timeout_seconds: Literal[60] = OUTER_CHILD_TIMEOUT_SECONDS
    worker_timeout_seconds: Literal[45] = WORKER_TIMEOUT_SECONDS
    parent_result_output_limit: Literal[262144] = RESULT_OUTPUT_LIMIT
    worker_result_output_limit: Literal[262144] = RESULT_OUTPUT_LIMIT
    parent_supervisor_stdout_null_from_process_start: Literal[True] = True
    parent_supervisor_stderr_null_from_process_start: Literal[True] = True
    parent_result_uses_dedicated_anonymous_pipe: Literal[True] = True
    v17_supervisor_worker_semantics_unchanged: Literal[True] = True
    raw_supervisor_or_worker_output_persistence_allowed: Literal[False] = False
    live_default_observers_exposed: Literal[False] = False
    network_call_limit: Literal[0] = 0
    provider_evaluator_agent_call_limit: Literal[0] = 0
    credential_value_return_hash_prefix_or_length_limit: Literal[0] = 0

    @model_validator(mode="after")
    def validate_literals(self) -> DualPipeRuntimeProfile:
        if self.child_flags != CHILD_FLAGS:
            raise ValueError("v19 child flags drifted")
        if self.fixed_child_environment != FIXED_CHILD_ENVIRONMENT:
            raise ValueError("v19 child environment drifted")
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("v19 approved scopes drifted")
        return self


class SourceAuthority(FrozenStrictModel):
    contract_materialization_authorized: Literal[True] = True
    source_qualification_authorized: Literal[True] = True
    state_approval_attempt_or_terminal_creation_authorized: Literal[False] = False
    environment_docker_dotenv_sdk_or_network_observation_authorized: Literal[False] = False
    credential_value_recording_authorized: Literal[False] = False
    docker_start_pull_load_image_store_or_container_mutation_authorized: Literal[False] = False
    provider_evaluator_agent_execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class DualPipeContract(FrozenStrictModel):
    schema_version: Literal["dual-pipe-preflight-successor-contract-v19"] = CONTRACT_SCHEMA_VERSION
    contract_version: Literal["ac-evaluator-v2-dual-pipe-preflight-successor-v19"] = (
        CONTRACT_VERSION
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor: V18FailureBinding
    runtime: DualPipeRuntimeProfile
    authority: SourceAuthority
    correction_scope: Literal["parent-supervisor-result-transport-only"] = (
        "parent-supervisor-result-transport-only"
    )
    predecessor_retry_or_repair: Literal[False] = False
    execution_currently_authorized: Literal[False] = False
    next_gate: Literal["new-versioned-state-and-activation-wrapper-required"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> DualPipeContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected or self.contract_id != v10._derived_id(
            "ncpcontract", expected
        ):
            raise ValueError("v19 contract identity differs")
        return self


class SourceCommitBinding(FrozenStrictModel):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    parents: tuple[str, ...]
    added_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_source(self) -> SourceCommitBinding:
        if self.parents != (SOURCE_PARENT_COMMIT,):
            raise ValueError("v19 source predecessor drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v19 source additions drifted")
        return self


class QualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    source_qualified: Literal[True] = True
    state_approval_attempt_or_terminal_created: Literal[False] = False
    docker_dotenv_sdk_network_or_provider_observation_count: Literal[0] = 0
    external_mutation_count: Literal[0] = 0
    execution_authorized: Literal[False] = False
    candidate_cost_or_paid_execution_authorized: Literal[False] = False


class SourceQualification(FrozenStrictModel):
    schema_version: Literal["dual-pipe-preflight-source-qualification-v19"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal["ac-evaluator-v2-dual-pipe-preflight-source-20260813-r1"] = (
        QUALIFICATION_ID
    )
    status: Literal["OFFLINE_V19_DUAL_PIPE_SOURCE_QUALIFIED_ACTIVATION_CLOSED"] = (
        QUALIFICATION_STATUS
    )
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[v10.CommittedFileBinding, ...]
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_terminal_id: Literal[
        "ncpterminal_775512b68eac1b8f418c22a4ab30a450bf5ba8150f155f8bcbe4e5938acca516"
    ]
    authority: QualificationAuthority
    next_gate: Literal["new-versioned-state-and-activation-wrapper-required"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v19 qualification time must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> SourceQualification:
        expected_paths = tuple(path.as_posix() for path in SOURCE_FILES)
        if tuple(item.path for item in self.source_files) != expected_paths:
            raise ValueError("v19 qualification inventory drifted")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != v10._hash_body(body):
            raise ValueError("v19 qualification hash mismatch")
        return self


def _predecessor_binding(root: Path) -> V18FailureBinding:
    contract_raw = v10._read(root, v18.CONTRACT_PATH)
    contract = v18.SupervisedFrameActivationContract.model_validate_json(contract_raw)
    _require(contract_raw == v10._canonical(contract), "v18 contract bytes differ")
    _require(
        contract_raw
        == v10._git(root, "show", f"{V18_SOURCE_COMMIT}:{v18.CONTRACT_PATH.as_posix()}"),
        "v18 committed contract differs",
    )
    qualification_raw = v10._read(root, v18.QUALIFICATION_PATH)
    qualification = v18.SourceQualification.model_validate_json(qualification_raw)
    _require(
        qualification_raw == v10._canonical(qualification),
        "v18 qualification bytes differ",
    )
    _require(
        qualification_raw
        == v10._git(
            root,
            "show",
            f"{V18_QUALIFICATION_COMMIT}:{v18.QUALIFICATION_PATH.as_posix()}",
        ),
        "v18 committed qualification differs",
    )
    raw = v10._read(root, v18.TERMINAL_PATH)
    committed = v10._git(root, "show", f"{V18_EVIDENCE_COMMIT}:{v18.TERMINAL_PATH.as_posix()}")
    _require(raw == committed, "v18 committed terminal differs")
    terminal = v18.TerminalTransition.model_validate_json(raw)
    _require(raw == v10._canonical(terminal), "v18 terminal bytes differ")
    _require(terminal.observation is not None, "v18 terminal lacks observation")
    observation = terminal.observation
    supervised = observation.supervised_child_execution
    child = observation.base.child_execution
    _require(supervised is not None and child is not None, "v18 child evidence is absent")
    return V18FailureBinding(
        contract_id=contract.contract_id,
        source_qualification_hash=qualification.content_hash,
        terminal_id=terminal.terminal_id,
        terminal_content_hash=terminal.content_hash,
        terminal_file_sha256=sha256_bytes(raw),
        outcome=terminal.outcome,
        reason=terminal.reason,
        base_child_code=child.code,
        supervisor_code=supervised.supervisor_code,
        envelope_received=supervised.envelope_received,
        docker_cli_command_count=observation.base.docker_cli_command_count,
        child_launch_attempt_count=observation.base.child_launch_attempt_count,
        child_process_return_count=child.activity.child_process_return_count,
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
        causal_detail_available=False,
    )


def _build_contract(root: Path) -> DualPipeContract:
    v17_raw = v10._read(root, v17.CONTRACT_PATH)
    v17_contract = v17.SupervisedFrameContract.model_validate_json(v17_raw)
    _require(v17_raw == v10._canonical(v17_contract), "v17 contract bytes differ")
    _require(
        v17_contract.contract_id == V17_CONTRACT_ID
        and v17_contract.content_hash == V17_CONTRACT_CONTENT_HASH,
        "v17 contract identity differs",
    )
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "predecessor": _predecessor_binding(root).model_dump(mode="json"),
        "runtime": DualPipeRuntimeProfile(
            parent_supervisor_file_sha256=sha256_bytes(v10._read(root, SUPERVISOR_PATH)),
            v17_runtime_file_sha256=sha256_bytes(v10._read(root, v17.RUNTIME_PATH)),
            v17_supervisor_worker_file_sha256=sha256_bytes(v10._read(root, v17.CHILD_PATH)),
            v17_contract_id=v17_contract.contract_id,
            v17_contract_content_hash=v17_contract.content_hash,
        ).model_dump(mode="json"),
        "authority": SourceAuthority().model_dump(mode="json"),
        "correction_scope": "parent-supervisor-result-transport-only",
        "predecessor_retry_or_repair": False,
        "execution_currently_authorized": False,
        "next_gate": NEXT_GATE,
    }
    content_hash = v10._hash_body(body)
    return DualPipeContract(
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
        "status": "OFFLINE_V19_DUAL_PIPE_CONTRACT_MATERIALIZED_LIVE_CLOSED",
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


def load_contract(*, repository: str | Path | None = None) -> DualPipeContract:
    root = v10._root(repository)
    raw = v10._read(root, CONTRACT_PATH)
    value = DualPipeContract.model_validate_json(raw)
    _require(raw == v10._canonical(value), "v19 contract bytes are not canonical")
    _require(value == _build_contract(root), "v19 contract differs from source")
    return value


@dataclass(frozen=True)
class SupervisorProcessOutcome:
    launch_attempt_count: int
    process_return_count: int
    result_bytes: bytes
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


def _run_supervisor_process(
    repository: str | Path,
    *,
    systemroot: str,
    supervisor_script: str | Path | None = None,
    python: str | Path | None = None,
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
) -> SupervisorProcessOutcome:
    """Launch one null-stdio supervisor and read only its bounded result pipe."""

    root = Path(repository).resolve(strict=True)
    script = Path(supervisor_script or root / SUPERVISOR_PATH).resolve(strict=True)
    python_path = Path(python or sys.executable).resolve(strict=True)
    read_descriptor, write_descriptor = os.pipe()
    os.set_inheritable(write_descriptor, True)
    reader = _BoundedReader(read_descriptor, RESULT_OUTPUT_LIMIT)
    thread = threading.Thread(target=reader.consume, daemon=True)
    process: subprocess.Popen[bytes] | None = None
    try:
        argv = [
            str(python_path),
            *CHILD_FLAGS,
            str(script),
            "--repository",
            str(root),
        ]
        kwargs: dict[str, Any] = {
            "cwd": root,
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "shell": False,
            "env": {**FIXED_CHILD_ENVIRONMENT, "SYSTEMROOT": systemroot},
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
        os.close(write_descriptor)
        os.close(read_descriptor)
        return SupervisorProcessOutcome(1, 0, b"", True, None, False, True)

    os.close(write_descriptor)
    thread.start()
    timed_out = False
    try:
        returncode = process.wait(timeout=OUTER_CHILD_TIMEOUT_SECONDS)
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
    return SupervisorProcessOutcome(
        launch_attempt_count=1,
        process_return_count=int(returncode is not None),
        result_bytes=bytes(reader.buffer),
        result_within_limit=reader.total <= RESULT_OUTPUT_LIMIT,
        returncode=returncode,
        complete=complete,
        unknown=not complete,
    )


class ParentSupervisorTransport(FrozenStrictModel):
    schema_version: Literal["parent-supervisor-dual-pipe-transport-v19"] = (
        "parent-supervisor-dual-pipe-transport-v19"
    )
    launch_attempt_count: Literal[1] = 1
    process_return_count: int = Field(ge=0, le=1)
    result_message_nonempty_count: int = Field(ge=0, le=1)
    result_within_limit: bool
    returncode: int | None = None
    stdout_null_from_process_start_count: Literal[1] = 1
    stderr_null_from_process_start_count: Literal[1] = 1
    raw_process_output_persisted: Literal[False] = False
    activity_accounting_complete: bool
    unknown_process_activity_possible: bool

    @model_validator(mode="after")
    def validate_semantics(self) -> ParentSupervisorTransport:
        if self.activity_accounting_complete == self.unknown_process_activity_possible:
            raise ValueError("v19 transport accounting flags differ")
        if self.process_return_count != int(self.returncode is not None):
            raise ValueError("v19 transport return projection differs")
        if self.result_message_nonempty_count > self.process_return_count:
            raise ValueError("v19 transport message exceeds process return")
        return self


class DualPipeChildExecution(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-dual-pipe-child-execution-v19"] = (
        "sanitized-sdk-bootstrap-dual-pipe-child-execution-v19"
    )
    base: v17.SupervisedChildExecution
    parent_supervisor_transport: ParentSupervisorTransport | None = None
    activity_accounting_complete: bool
    unknown_workload_activity_possible: bool

    @model_validator(mode="after")
    def validate_semantics(self) -> DualPipeChildExecution:
        transport = self.parent_supervisor_transport
        if transport is None:
            expected_complete = self.base.activity_accounting_complete
            expected_unknown = self.base.unknown_workload_activity_possible
            if self.base.base.activity.child_launch_attempt_count:
                raise ValueError("v19 launched supervisor lacks transport evidence")
        else:
            activity = self.base.base.activity
            if (
                activity.child_launch_attempt_count != transport.launch_attempt_count
                or activity.child_process_return_count != transport.process_return_count
            ):
                raise ValueError("v19 transport/base counts differ")
            expected_complete = (
                self.base.activity_accounting_complete and transport.activity_accounting_complete
            )
            expected_unknown = (
                self.base.unknown_workload_activity_possible
                or transport.unknown_process_activity_possible
            )
        if (
            self.activity_accounting_complete != expected_complete
            or self.unknown_workload_activity_possible != expected_unknown
        ):
            raise ValueError("v19 child accounting differs")
        return self


class DualPipeParentObservation(FrozenStrictModel):
    schema_version: Literal["sanitized-sdk-bootstrap-dual-pipe-parent-observation-v19"] = (
        "sanitized-sdk-bootstrap-dual-pipe-parent-observation-v19"
    )
    base: v17.SupervisedParentObservation
    dual_pipe_child_execution: DualPipeChildExecution | None = None
    activity_accounting_complete: bool
    unknown_post_marker_activity_possible: bool
    passed: bool

    @model_validator(mode="after")
    def validate_semantics(self) -> DualPipeParentObservation:
        supervised = self.base.supervised_child_execution
        if supervised is None:
            if self.dual_pipe_child_execution is not None:
                raise ValueError("v19 unexpected dual-pipe child")
            expected_complete = self.base.activity_accounting_complete
            expected_unknown = self.base.unknown_post_marker_activity_possible
        else:
            if (
                self.dual_pipe_child_execution is None
                or self.dual_pipe_child_execution.base != supervised
            ):
                raise ValueError("v19 child projection differs")
            expected_complete = (
                self.base.activity_accounting_complete
                and self.dual_pipe_child_execution.activity_accounting_complete
            )
            expected_unknown = (
                self.base.unknown_post_marker_activity_possible
                or self.dual_pipe_child_execution.unknown_workload_activity_possible
            )
        if (
            self.activity_accounting_complete != expected_complete
            or self.unknown_post_marker_activity_possible != expected_unknown
            or self.passed != self.base.passed
        ):
            raise ValueError("v19 parent accounting differs")
        return self


SupervisorRunner = Callable[..., SupervisorProcessOutcome]


def _wrap_child(
    base: v17.SupervisedChildExecution,
    transport: ParentSupervisorTransport | None,
) -> DualPipeChildExecution:
    complete = base.activity_accounting_complete and (
        True if transport is None else transport.activity_accounting_complete
    )
    unknown = base.unknown_workload_activity_possible or (
        False if transport is None else transport.unknown_process_activity_possible
    )
    return DualPipeChildExecution(
        base=base,
        parent_supervisor_transport=transport,
        activity_accounting_complete=complete,
        unknown_workload_activity_possible=unknown,
    )


def _failed_child_binding() -> DualPipeChildExecution:
    return _wrap_child(v17._failed_child_binding(), None)


def run_dual_pipe_child_injected(
    contract: DualPipeContract,
    *,
    repository: str | Path | None = None,
    environment_present: v9.EnvironmentPresent,
    environment_value: v9.EnvironmentValue,
    python: str | Path,
    supervisor_runner: SupervisorRunner,
) -> DualPipeChildExecution:
    """Run v19 only from explicit authority-owned dependencies."""

    root = v10._root(repository)
    try:
        checked = DualPipeContract.model_validate(contract.model_dump(mode="json"))
        _require(checked == load_contract(repository=root), "v19 runtime contract differs")
        _require(
            sha256_bytes(v10._read(root, SUPERVISOR_PATH))
            == contract.runtime.parent_supervisor_file_sha256,
            "v19 supervisor shim differs",
        )
        _require(
            sha256_bytes(v10._read(root, v17.RUNTIME_PATH))
            == contract.runtime.v17_runtime_file_sha256,
            "v19 v17 runtime differs",
        )
        _require(
            sha256_bytes(v10._read(root, v17.CHILD_PATH))
            == contract.runtime.v17_supervisor_worker_file_sha256,
            "v19 v17 supervisor differs",
        )
        v17_raw = v10._read(root, v17.CONTRACT_PATH)
        v17_contract = v17.SupervisedFrameContract.model_validate_json(v17_raw)
        _require(v17_raw == v10._canonical(v17_contract), "v19 v17 contract differs")
        _require(
            v17_contract.contract_id == contract.runtime.v17_contract_id
            and v17_contract.content_hash == contract.runtime.v17_contract_content_hash,
            "v19 v17 contract identity differs",
        )
    except Exception:
        return _failed_child_binding()

    captured: list[ParentSupervisorTransport] = []

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        environment = kwargs.get("env")
        if not isinstance(environment, dict) or not isinstance(environment.get("SYSTEMROOT"), str):
            raise RuntimeError("v19 SystemRoot binding differs")
        outcome = supervisor_runner(
            root,
            systemroot=environment["SYSTEMROOT"],
            supervisor_script=root / SUPERVISOR_PATH,
            python=python,
        )
        transport = ParentSupervisorTransport(
            launch_attempt_count=outcome.launch_attempt_count,
            process_return_count=outcome.process_return_count,
            result_message_nonempty_count=int(bool(outcome.result_bytes)),
            result_within_limit=outcome.result_within_limit,
            returncode=outcome.returncode,
            activity_accounting_complete=outcome.complete,
            unknown_process_activity_possible=outcome.unknown,
        )
        captured.append(transport)
        if outcome.process_return_count != 1 or outcome.returncode is None:
            raise RuntimeError("v19 supervisor did not return")
        stdout = outcome.result_bytes if outcome.result_within_limit else b""
        return subprocess.CompletedProcess(
            argv,
            outcome.returncode,
            stdout=stdout,
            stderr=b"",
        )

    base = v17.run_supervised_frame_child_injected(
        v17_contract,
        repository=root,
        environment_present=environment_present,
        environment_value=environment_value,
        python=python,
        run=run,
    )
    transport = captured[0] if captured else None
    return _wrap_child(base, transport)


def run_parent_preflight_injected(
    contract: DualPipeContract,
    *,
    repository: str | Path | None = None,
    docker_observer: Callable[..., dict[str, Any]],
    child_observer: Callable[..., DualPipeChildExecution],
) -> DualPipeParentObservation:
    """Compose v19 only from injected observers; no live defaults are exposed."""

    root = v10._root(repository)
    try:
        checked = DualPipeContract.model_validate(contract.model_dump(mode="json"))
        _require(checked == load_contract(repository=root), "v19 parent contract differs")
        v17_raw = v10._read(root, v17.CONTRACT_PATH)
        v17_contract = v17.SupervisedFrameContract.model_validate_json(v17_raw)
        _require(v17_raw == v10._canonical(v17_contract), "v19 parent v17 contract differs")
        _require(
            v17_contract.contract_id == contract.runtime.v17_contract_id
            and v17_contract.content_hash == contract.runtime.v17_contract_content_hash,
            "v19 parent v17 identity differs",
        )
    except Exception:
        inherited = v9._contract_error_observation()
        base = v17.SupervisedParentObservation(
            base=inherited,
            activity_accounting_complete=inherited.activity_accounting_complete,
            unknown_post_marker_activity_possible=(inherited.unknown_post_marker_activity_possible),
            passed=False,
        )
        return DualPipeParentObservation(
            base=base,
            activity_accounting_complete=base.activity_accounting_complete,
            unknown_post_marker_activity_possible=base.unknown_post_marker_activity_possible,
            passed=False,
        )
    captured: list[DualPipeChildExecution] = []

    def observe_child(*_args: Any, **_kwargs: Any) -> v17.SupervisedChildExecution:
        value = child_observer(contract, repository=root)
        checked_value = DualPipeChildExecution.model_validate(value.model_dump(mode="json"))
        captured.append(checked_value)
        return checked_value.base

    base = v17.run_parent_preflight_injected(
        v17_contract,
        repository=root,
        docker_observer=docker_observer,
        child_observer=observe_child,
    )
    dual = captured[0] if captured else None
    complete = base.activity_accounting_complete and (
        True if dual is None else dual.activity_accounting_complete
    )
    unknown = base.unknown_post_marker_activity_possible or (
        False if dual is None else dual.unknown_workload_activity_possible
    )
    return DualPipeParentObservation(
        base=base,
        dual_pipe_child_execution=dual,
        activity_accounting_complete=complete,
        unknown_post_marker_activity_possible=unknown,
        passed=base.passed,
    )


def _source_commit(root: Path, selected: str) -> SourceCommitBinding:
    commit = v10._git(root, "rev-parse", f"{selected}^{{commit}}").decode("ascii").strip()
    tree = v10._git(root, "rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    row = v10._git(root, "rev-list", "--parents", "-n", "1", commit).decode().split()
    _require(row and row[0] == commit and len(row) == 2, "v19 source parent failed")
    lines = (
        v10._git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", row[1], commit)
        .decode("utf-8")
        .splitlines()
    )
    added = tuple(sorted(parts[1] for line in lines if (parts := line.split("\t"))[:1] == ["A"]))
    _require(len(lines) == len(added), "v19 source contains non-addition changes")
    return SourceCommitBinding(commit=commit, tree=tree, parents=(row[1],), added_paths=added)


def _build_qualification(
    root: Path, *, source_commit: str, recorded_at: datetime
) -> SourceQualification:
    contract = load_contract(repository=root)
    commit = _source_commit(root, source_commit)
    pairs = tuple(v10._committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(pair[0] for pair in pairs)
    contract_index = SOURCE_FILES.index(CONTRACT_PATH)
    _require(pairs[contract_index][1] == v10._canonical(contract), "committed v19 contract differs")
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
        "external_observations_made": 0,
        "external_mutations_made": 0,
        "execution_authorized": False,
        "next_gate": value.next_gate,
    }


def validate_source_qualification(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = v10._root(repository)
    raw = v10._read(root, QUALIFICATION_PATH)
    value = SourceQualification.model_validate_json(raw)
    _require(raw == v10._canonical(value), "v19 qualification bytes are not canonical")
    rebuilt = _build_qualification(
        root, source_commit=value.source_commit.commit, recorded_at=value.recorded_at
    )
    _require(value == rebuilt, "v19 qualification differs from committed source")
    return _qualification_summary(value, raw)


__all__ = [
    "APPROVED_RUNTIME",
    "BUILD_SCRIPT_PATH",
    "CONTRACT_PATH",
    "DualPipeChildExecution",
    "DualPipeContract",
    "DualPipeParentObservation",
    "DualPipeSuccessorError",
    "ParentSupervisorTransport",
    "QUALIFICATION_PATH",
    "RUNTIME_PATH",
    "SOURCE_ADDED_PATHS",
    "SOURCE_PARENT_COMMIT",
    "SUPERVISOR_PATH",
    "SupervisorProcessOutcome",
    "TEST_PATH",
    "_build_contract",
    "_run_supervisor_process",
    "load_contract",
    "materialize_contract",
    "qualify_source",
    "run_dual_pipe_child_injected",
    "run_parent_preflight_injected",
    "validate_source_qualification",
]
