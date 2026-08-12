"""Offline-only v15 correction for the consumed v14 framing failure.

V14 remains immutable and cannot retry.  This source binds its exact terminal
and replaces fd 1/2 restoration with a result descriptor duplicated before the
workload starts.  Source validation never reads Docker, dotenv, SDK, network,
provider, or credential state.  Live activation requires a later versioned
authority wrapper.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from patchloop.contracts import FrozenStrictModel
from patchloop.errors import ContractError
from patchloop.evals import manual_docker_restart_framed_successor as v14
from patchloop.evals import sanitized_sdk_bootstrap_framed_successor as v13
from patchloop.util import sha256_bytes

v10 = v14.v10
v9 = v14.v9

CONTRACT_SCHEMA_VERSION = "dedicated-frame-preflight-successor-contract-v15"
CONTRACT_VERSION = "ac-evaluator-v2-dedicated-frame-preflight-successor-v15"
CONTRACT_PATH = Path(
    "experiments/evaluator-v2-dedicated-frame-preflight-successor-v15.contract.json"
)
RUNTIME_PATH = Path("patchloop/evals/dedicated_frame_preflight_successor.py")
CHILD_PATH = Path("scripts/run_sanitized_sdk_bootstrap_dedicated_frame_child.py")
BUILD_SCRIPT_PATH = Path("scripts/build_dedicated_frame_preflight_successor.py")
TEST_PATH = Path("tests/test_dedicated_frame_preflight_successor.py")

SOURCE_PARENT_COMMIT = "51bb6a6e84faa4266eb64147271febee0b9a38ff"
V14_EVIDENCE_COMMIT = "e63f418e9b2e3c6810fc3de68a203bcbfeb0a217"
QUALIFICATION_SCHEMA_VERSION = "dedicated-frame-preflight-source-qualification-v15"
QUALIFICATION_ID = "ac-evaluator-v2-dedicated-frame-preflight-source-20260813-r1"
QUALIFICATION_STATUS = "OFFLINE_V15_DEDICATED_FRAME_SOURCE_QUALIFIED_ACTIVATION_CLOSED"
QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/"
    "evaluator-v2-dedicated-frame-preflight-v15-source-qualification.json"
)
NEXT_GATE = "new-versioned-state-and-activation-wrapper-required"
APPROVED_RUNTIME = (
    "patchloop.evals.dedicated_frame_preflight_successor.run_parent_preflight_injected"
)
APPROVED_SCOPES = v14.APPROVED_SCOPES
CHILD_FLAGS = v13.CHILD_FLAGS
FIXED_CHILD_ENVIRONMENT = v13.FIXED_CHILD_ENVIRONMENT
CHILD_TIMEOUT_SECONDS = v13.CHILD_TIMEOUT_SECONDS
CHILD_OUTPUT_LIMIT = v13.CHILD_OUTPUT_LIMIT

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
            v14.CONTRACT_PATH,
            v14.RUNTIME_PATH,
            v14.QUALIFICATION_PATH,
            v14.TERMINAL_PATH,
            v13.RUNTIME_PATH,
            v13.CHILD_PATH,
        ),
        key=lambda path: path.as_posix(),
    )
)


class DedicatedFrameSuccessorError(ContractError):
    """The source-only v15 successor failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DedicatedFrameSuccessorError(message)


class V14FailureBinding(FrozenStrictModel):
    evidence_commit: Literal["e63f418e9b2e3c6810fc3de68a203bcbfeb0a217"] = V14_EVIDENCE_COMMIT
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    terminal_id: Literal[
        "ncpterminal_d390b170b452fa9497f22bd46832330e3a9b4097b645c3a9094d8d424e801e5f"
    ]
    terminal_content_hash: Literal[
        "sha256:d390b170b452fa9497f22bd46832330e3a9b4097b645c3a9094d8d424e801e5f"
    ]
    terminal_file_sha256: Literal[
        "sha256:9114e21765913c008fa4345897a4c1a42d7c213283fb31805fed662f887a3930"
    ]
    outcome: Literal["error"] = "error"
    reason: Literal["child_checker_error"] = "child_checker_error"
    base_child_code: Literal["child_output_invalid"] = "child_output_invalid"
    frame_code: Literal["framed_output_invalid"] = "framed_output_invalid"
    envelope_received: Literal[False] = False
    docker_cli_command_count: Literal[8] = 8
    child_launch_attempt_count: Literal[1] = 1
    child_process_return_count: Literal[1] = 1
    network_call_count: Literal[0] = 0
    provider_evaluator_agent_call_count: Literal[0] = 0
    docker_mutation_count: Literal[0] = 0
    credential_value_metadata_count: Literal[0] = 0
    raw_child_output_persisted: Literal[False] = False
    activity_accounting_complete: Literal[False] = False
    unknown_post_marker_activity_possible: Literal[True] = True
    retry_or_resume_allowed: Literal[False] = False
    causal_detail_available: Literal[False] = False


class DedicatedFrameRuntimeProfile(FrozenStrictModel):
    entrypoint: Literal[
        "patchloop.evals.dedicated_frame_preflight_successor.run_parent_preflight_injected"
    ] = APPROVED_RUNTIME
    child_path: Literal["scripts/run_sanitized_sdk_bootstrap_dedicated_frame_child.py"] = (
        CHILD_PATH.as_posix()
    )
    child_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v13_runtime_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v13_contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    v13_contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    child_flags: tuple[str, ...] = CHILD_FLAGS
    fixed_child_environment: dict[str, str] = FIXED_CHILD_ENVIRONMENT
    approved_scopes: tuple[str, ...] = APPROVED_SCOPES
    result_descriptor_duplicated_before_workload: Literal[True] = True
    workload_stdout_stderr_redirected_to_null: Literal[True] = True
    envelope_written_directly_to_saved_descriptor: Literal[True] = True
    fd1_fd2_restore_required_before_envelope: Literal[False] = False
    canonical_single_value_free_envelope_required: Literal[True] = True
    raw_child_output_persistence_allowed: Literal[False] = False
    live_default_observers_exposed: Literal[False] = False
    child_launch_limit: Literal[1] = 1
    network_call_limit: Literal[0] = 0
    provider_evaluator_agent_call_limit: Literal[0] = 0
    credential_value_return_hash_prefix_or_length_limit: Literal[0] = 0

    @model_validator(mode="after")
    def validate_literals(self) -> DedicatedFrameRuntimeProfile:
        if self.child_flags != CHILD_FLAGS:
            raise ValueError("v15 child flags drifted")
        if self.fixed_child_environment != FIXED_CHILD_ENVIRONMENT:
            raise ValueError("v15 child environment drifted")
        if self.approved_scopes != APPROVED_SCOPES:
            raise ValueError("v15 approved scopes drifted")
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


class DedicatedFrameContract(FrozenStrictModel):
    schema_version: Literal["dedicated-frame-preflight-successor-contract-v15"] = (
        CONTRACT_SCHEMA_VERSION
    )
    contract_version: Literal["ac-evaluator-v2-dedicated-frame-preflight-successor-v15"] = (
        CONTRACT_VERSION
    )
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    predecessor: V14FailureBinding
    runtime: DedicatedFrameRuntimeProfile
    authority: SourceAuthority
    correction_scope: Literal["child-envelope-result-channel-only"] = (
        "child-envelope-result-channel-only"
    )
    predecessor_retry_or_repair: Literal[False] = False
    execution_currently_authorized: Literal[False] = False
    next_gate: Literal["new-versioned-state-and-activation-wrapper-required"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> DedicatedFrameContract:
        body = self.model_dump(mode="json", exclude={"contract_id", "content_hash"})
        expected = v10._hash_body(body)
        if self.content_hash != expected or self.contract_id != v10._derived_id(
            "ncpcontract", expected
        ):
            raise ValueError("v15 contract identity differs")
        return self


class SourceCommitBinding(FrozenStrictModel):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    parents: tuple[str, ...]
    added_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_source(self) -> SourceCommitBinding:
        if self.parents != (SOURCE_PARENT_COMMIT,):
            raise ValueError("v15 source predecessor drifted")
        if self.added_paths != SOURCE_ADDED_PATHS:
            raise ValueError("v15 source additions drifted")
        return self


class QualificationAuthority(FrozenStrictModel):
    repository_commit_read_authorized: Literal[True] = True
    source_qualified: Literal[True] = True
    state_approval_attempt_or_terminal_created: Literal[False] = False
    environment_docker_dotenv_sdk_network_or_provider_observation_count: Literal[0] = 0
    external_mutation_count: Literal[0] = 0
    execution_authorized: Literal[False] = False


class SourceQualification(FrozenStrictModel):
    schema_version: Literal["dedicated-frame-preflight-source-qualification-v15"] = (
        QUALIFICATION_SCHEMA_VERSION
    )
    qualification_id: Literal["ac-evaluator-v2-dedicated-frame-preflight-source-20260813-r1"] = (
        QUALIFICATION_ID
    )
    status: Literal["OFFLINE_V15_DEDICATED_FRAME_SOURCE_QUALIFIED_ACTIVATION_CLOSED"] = (
        QUALIFICATION_STATUS
    )
    recorded_at: datetime
    source_commit: SourceCommitBinding
    source_files: tuple[v10.CommittedFileBinding, ...]
    contract_id: str = Field(pattern=r"^ncpcontract_[0-9a-f]{64}$")
    contract_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_terminal_id: str = Field(pattern=r"^ncpterminal_[0-9a-f]{64}$")
    authority: QualificationAuthority
    next_gate: Literal["new-versioned-state-and-activation-wrapper-required"] = NEXT_GATE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("v15 qualification time must be UTC")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> SourceQualification:
        expected_paths = tuple(path.as_posix() for path in SOURCE_FILES)
        if tuple(item.path for item in self.source_files) != expected_paths:
            raise ValueError("v15 qualification inventory drifted")
        body = self.model_dump(mode="json", exclude={"content_hash"})
        if self.content_hash != v10._hash_body(body):
            raise ValueError("v15 qualification hash mismatch")
        return self


def _predecessor_binding(root: Path) -> V14FailureBinding:
    contract = v14.load_contract(repository=root)
    qualification = v14._load_qualification(root)
    terminal_raw = v10._read(root, v14.TERMINAL_PATH)
    terminal = v14.TerminalTransition.model_validate_json(terminal_raw)
    _require(terminal_raw == v10._canonical(terminal), "v14 terminal bytes differ")
    _require(terminal.observation is not None, "v14 terminal lacks observation")
    observation = terminal.observation
    framed = observation.framed_child_execution
    child = observation.base.child_execution
    _require(framed is not None and child is not None, "v14 child evidence is absent")
    return V14FailureBinding(
        contract_id=contract.contract_id,
        source_qualification_hash=qualification.content_hash,
        terminal_id=terminal.terminal_id,
        terminal_content_hash=terminal.content_hash,
        terminal_file_sha256=sha256_bytes(terminal_raw),
        outcome=terminal.outcome,
        reason=terminal.reason,
        base_child_code=child.code,
        frame_code=framed.frame_code,
        envelope_received=framed.envelope_received,
        docker_cli_command_count=observation.base.docker_cli_command_count,
        child_launch_attempt_count=observation.base.child_launch_attempt_count,
        child_process_return_count=child.activity.child_process_return_count,
        network_call_count=terminal.network_call_count,
        provider_evaluator_agent_call_count=terminal.provider_evaluator_agent_call_count,
        docker_mutation_count=terminal.docker_start_pull_load_image_store_or_container_mutation_count,
        credential_value_metadata_count=terminal.credential_value_return_hash_prefix_or_length_count,
        raw_child_output_persisted=framed.raw_child_output_persisted,
        activity_accounting_complete=terminal.activity_accounting_complete,
        unknown_post_marker_activity_possible=terminal.unknown_post_marker_activity_possible,
        retry_or_resume_allowed=terminal.retry_or_resume_allowed,
        causal_detail_available=False,
    )


def _build_contract(root: Path) -> DedicatedFrameContract:
    v13_contract = v13.load_contract(repository=root)
    body = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "predecessor": _predecessor_binding(root).model_dump(mode="json"),
        "runtime": DedicatedFrameRuntimeProfile(
            child_file_sha256=sha256_bytes(v10._read(root, CHILD_PATH)),
            v13_runtime_file_sha256=sha256_bytes(v10._read(root, v13.RUNTIME_PATH)),
            v13_contract_id=v13_contract.contract_id,
            v13_contract_content_hash=v13_contract.content_hash,
        ).model_dump(mode="json"),
        "authority": SourceAuthority().model_dump(mode="json"),
        "correction_scope": "child-envelope-result-channel-only",
        "predecessor_retry_or_repair": False,
        "execution_currently_authorized": False,
        "next_gate": NEXT_GATE,
    }
    content_hash = v10._hash_body(body)
    return DedicatedFrameContract(
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
        "status": "OFFLINE_V15_DEDICATED_FRAME_CONTRACT_MATERIALIZED_LIVE_CLOSED",
        "contract_id": value.contract_id,
        "contract_content_hash": value.content_hash,
        "artifact_path": CONTRACT_PATH.as_posix(),
        "artifact_file_sha256": sha256_bytes(raw),
        "artifact_bytes": len(raw),
        "external_observations_made": 0,
        "execution_authorized": False,
        "next_gate": "exact-source-commit-and-offline-qualification",
    }


def load_contract(*, repository: str | Path | None = None) -> DedicatedFrameContract:
    root = v10._root(repository)
    raw = v10._read(root, CONTRACT_PATH)
    value = DedicatedFrameContract.model_validate_json(raw)
    _require(raw == v10._canonical(value), "v15 contract bytes are not canonical")
    _require(value == _build_contract(root), "v15 contract differs from source")
    return value


RunCallable = Callable[..., subprocess.CompletedProcess[bytes]]


def _failed_child_binding() -> v13.FramedChildExecution:
    return v13._framed_execution(
        v9._execution(
            binding_valid=False,
            pythonhome_absent=False,
            pythonpath_absent=False,
            systemroot_present=False,
            systemroot_nonempty=False,
            parent_checks=0,
            parent_completed=0,
            systemroot_membership_checks=0,
            systemroot_nonempty_checks=0,
            launch_attempts=0,
            process_returns=0,
            passed_values=0,
            code=v9.ParentExecutionCode.CHILD_BINDING_ERROR,
        )
    )


def run_dedicated_frame_child_injected(
    contract: DedicatedFrameContract,
    *,
    repository: str | Path | None = None,
    environment_present: v9.EnvironmentPresent,
    environment_value: v9.EnvironmentValue,
    python: str | Path,
    run: RunCallable,
) -> v13.FramedChildExecution:
    """Run the v15 child only with explicitly supplied, authority-owned inputs."""

    root = v10._root(repository)
    try:
        checked = DedicatedFrameContract.model_validate(contract.model_dump(mode="json"))
        _require(checked == load_contract(repository=root), "v15 runtime contract differs")
        wrapper = v10._logical_path(root, CHILD_PATH, must_exist=True)
        _require(
            sha256_bytes(v10._read(root, CHILD_PATH)) == contract.runtime.child_file_sha256,
            "v15 child source differs",
        )
        python_path = Path(python).resolve(strict=True)
        _require(python_path.is_file(), "v15 python runtime is not a file")
    except Exception:
        return _failed_child_binding()

    checks = completed_checks = 0
    try:
        checks += 1
        pythonhome_absent = not environment_present("PYTHONHOME")
        completed_checks += 1
        checks += 1
        pythonpath_absent = not environment_present("PYTHONPATH")
        completed_checks += 1
    except Exception:
        return v13._framed_execution(
            v9._execution(
                pythonhome_absent=False,
                pythonpath_absent=False,
                systemroot_present=False,
                systemroot_nonempty=False,
                parent_checks=checks,
                parent_completed=completed_checks,
                systemroot_membership_checks=0,
                systemroot_nonempty_checks=0,
                launch_attempts=0,
                process_returns=0,
                passed_values=0,
                code=v9.ParentExecutionCode.PARENT_PRESENCE_ERROR,
            )
        )
    if not pythonhome_absent or not pythonpath_absent:
        return v13._framed_execution(
            v9._execution(
                pythonhome_absent=pythonhome_absent,
                pythonpath_absent=pythonpath_absent,
                systemroot_present=False,
                systemroot_nonempty=False,
                parent_checks=2,
                parent_completed=2,
                systemroot_membership_checks=0,
                systemroot_nonempty_checks=0,
                launch_attempts=0,
                process_returns=0,
                passed_values=0,
                code=v9.ParentExecutionCode.PARENT_PYTHON_ENVIRONMENT_NOT_CLEAN,
            )
        )
    try:
        systemroot = environment_value("SYSTEMROOT")
    except Exception:
        systemroot = None
        systemroot_error = True
    else:
        systemroot_error = False
    if systemroot_error or not systemroot:
        return v13._framed_execution(
            v9._execution(
                pythonhome_absent=True,
                pythonpath_absent=True,
                systemroot_present=systemroot is not None,
                systemroot_nonempty=bool(systemroot),
                parent_checks=2,
                parent_completed=2,
                systemroot_membership_checks=1,
                systemroot_nonempty_checks=int(not systemroot_error and systemroot is not None),
                launch_attempts=0,
                process_returns=0,
                passed_values=0,
                code=(
                    v9.ParentExecutionCode.SYSTEMROOT_PRESENCE_ERROR
                    if systemroot_error
                    else (
                        v9.ParentExecutionCode.SYSTEMROOT_MISSING
                        if systemroot is None
                        else v9.ParentExecutionCode.SYSTEMROOT_EMPTY
                    )
                ),
            )
        )
    try:
        result = run(
            [str(python_path), *CHILD_FLAGS, str(wrapper), "--repository", str(root)],
            cwd=root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            shell=False,
            timeout=CHILD_TIMEOUT_SECONDS,
            env={**FIXED_CHILD_ENVIRONMENT, "SYSTEMROOT": systemroot},
            creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
        )
    except Exception:
        return v13._framed_execution(
            v9._execution(
                pythonhome_absent=True,
                pythonpath_absent=True,
                systemroot_present=True,
                systemroot_nonempty=True,
                parent_checks=2,
                parent_completed=2,
                systemroot_membership_checks=1,
                systemroot_nonempty_checks=1,
                launch_attempts=1,
                process_returns=0,
                passed_values=1,
                code=v9.ParentExecutionCode.CHILD_LAUNCH_ERROR,
                complete=False,
                unknown=True,
            )
        )

    if result.returncode != 0:
        base_code = v9.ParentExecutionCode.CHILD_NONZERO_EXIT
    elif result.stderr:
        base_code = v9.ParentExecutionCode.CHILD_STDERR_NOT_EMPTY
    elif len(result.stdout) > CHILD_OUTPUT_LIMIT:
        base_code = v9.ParentExecutionCode.CHILD_OUTPUT_LIMIT
    else:
        base_code = None
    if base_code is not None:
        return v13._framed_execution(
            v9._execution(
                pythonhome_absent=True,
                pythonpath_absent=True,
                systemroot_present=True,
                systemroot_nonempty=True,
                parent_checks=2,
                parent_completed=2,
                systemroot_membership_checks=1,
                systemroot_nonempty_checks=1,
                launch_attempts=1,
                process_returns=1,
                passed_values=1,
                code=base_code,
            ),
            complete=False,
            unknown=True,
        )
    try:
        envelope = v13.FramedChildEnvelope.model_validate_json(result.stdout)
    except Exception:
        base = v9._execution(
            pythonhome_absent=True,
            pythonpath_absent=True,
            systemroot_present=True,
            systemroot_nonempty=True,
            parent_checks=2,
            parent_completed=2,
            systemroot_membership_checks=1,
            systemroot_nonempty_checks=1,
            launch_attempts=1,
            process_returns=1,
            passed_values=1,
            code=v9.ParentExecutionCode.CHILD_OUTPUT_INVALID,
        )
        return v13._framed_execution(
            base,
            frame_code=v13.FrameCode.FRAMED_OUTPUT_INVALID,
            complete=False,
            unknown=True,
        )
    if envelope.child is None:
        assert envelope.code is not None
        base = v9._execution(
            pythonhome_absent=True,
            pythonpath_absent=True,
            systemroot_present=True,
            systemroot_nonempty=True,
            parent_checks=2,
            parent_completed=2,
            systemroot_membership_checks=1,
            systemroot_nonempty_checks=1,
            launch_attempts=1,
            process_returns=1,
            passed_values=1,
            code=v9.ParentExecutionCode.CHILD_OUTPUT_INVALID,
        )
        return v13._framed_execution(
            base,
            frame_code=envelope.code,
            envelope_received=True,
            complete=envelope.activity.activity_accounting_complete,
            unknown=envelope.activity.unknown_workload_activity_possible,
        )
    base = v9._execution(
        pythonhome_absent=True,
        pythonpath_absent=True,
        systemroot_present=True,
        systemroot_nonempty=True,
        parent_checks=2,
        parent_completed=2,
        systemroot_membership_checks=1,
        systemroot_nonempty_checks=1,
        launch_attempts=1,
        process_returns=1,
        passed_values=1,
        child=envelope.child,
    )
    return v13._framed_execution(base, envelope_received=True, complete=True, unknown=False)


def run_parent_preflight_injected(
    contract: DedicatedFrameContract,
    *,
    repository: str | Path | None = None,
    docker_observer: Callable[..., dict[str, Any]],
    child_observer: Callable[..., v13.FramedChildExecution],
) -> v13.CorrectedParentObservation:
    """Compose v15 only from caller-supplied observers; no live defaults exist."""

    root = v10._root(repository)
    try:
        checked = DedicatedFrameContract.model_validate(contract.model_dump(mode="json"))
        _require(checked == load_contract(repository=root), "v15 parent contract differs")
        delegate = v13.load_contract(repository=root)
    except Exception:
        base = v9._contract_error_observation()
        return v13.CorrectedParentObservation(
            base=base,
            activity_accounting_complete=base.activity_accounting_complete,
            unknown_post_marker_activity_possible=base.unknown_post_marker_activity_possible,
            passed=False,
        )
    return v13.run_parent_preflight(
        delegate,
        repository=root,
        docker_observer=docker_observer,
        child_observer=child_observer,
    )


def _source_commit(root: Path, selected: str) -> SourceCommitBinding:
    commit = v10._git(root, "rev-parse", f"{selected}^{{commit}}").decode("ascii").strip()
    tree = v10._git(root, "rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    row = v10._git(root, "rev-list", "--parents", "-n", "1", commit).decode("ascii").split()
    _require(row and row[0] == commit and len(row) == 2, "v15 source parent binding failed")
    lines = (
        v10._git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", row[1], commit)
        .decode("utf-8")
        .splitlines()
    )
    added = tuple(sorted(parts[1] for line in lines if (parts := line.split("\t"))[:1] == ["A"]))
    _require(len(lines) == len(added), "v15 source commit contains non-addition changes")
    return SourceCommitBinding(commit=commit, tree=tree, parents=(row[1],), added_paths=added)


def _committed_file(root: Path, commit: str, path: Path) -> tuple[v10.CommittedFileBinding, bytes]:
    logical = path.as_posix()
    raw = v10._git(root, "show", f"{commit}:{logical}")
    oid = v10._git(root, "rev-parse", f"{commit}:{logical}").decode("ascii").strip()
    return (
        v10.CommittedFileBinding(
            path=logical,
            blob_oid=oid,
            file_bytes=len(raw),
            file_sha256=sha256_bytes(raw),
        ),
        raw,
    )


def _build_qualification(
    root: Path, *, source_commit: str, recorded_at: datetime
) -> SourceQualification:
    contract = load_contract(repository=root)
    commit = _source_commit(root, source_commit)
    pairs = tuple(_committed_file(root, commit.commit, path) for path in SOURCE_FILES)
    files = tuple(pair[0] for pair in pairs)
    contract_index = SOURCE_FILES.index(CONTRACT_PATH)
    _require(pairs[contract_index][1] == v10._canonical(contract), "committed v15 contract differs")
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
    content_hash = v10._hash_body(body)
    return SourceQualification(**body, content_hash=content_hash)


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
    _require(raw == v10._canonical(value), "v15 qualification bytes are not canonical")
    rebuilt = _build_qualification(
        root,
        source_commit=value.source_commit.commit,
        recorded_at=value.recorded_at,
    )
    _require(value == rebuilt, "v15 qualification differs from committed source")
    return _qualification_summary(value, raw)


__all__ = [
    "APPROVED_RUNTIME",
    "BUILD_SCRIPT_PATH",
    "CHILD_PATH",
    "CONTRACT_PATH",
    "DedicatedFrameContract",
    "DedicatedFrameSuccessorError",
    "QUALIFICATION_PATH",
    "RUNTIME_PATH",
    "SOURCE_ADDED_PATHS",
    "SOURCE_PARENT_COMMIT",
    "SourceQualification",
    "TEST_PATH",
    "_build_contract",
    "load_contract",
    "materialize_contract",
    "qualify_source",
    "run_dedicated_frame_child_injected",
    "run_parent_preflight_injected",
    "validate_source_qualification",
]
