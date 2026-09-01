"""Bounded read-only Docker preflight for the sealed Harbor admission runner.

The module records the exact user-approved preflight, validates the immutable
runner candidate and twelve package Dockerfiles, and permits only two Docker
daemon reads: ``version`` and one bulk ``image inspect``.  It has no container,
image-pull/build, Harbor, evaluator, agent, provider, or task-execution path.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tarfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.errors import ContractError
from patchloop.evals.fresh_all_cross_successor import CANDIDATE_IDS
from patchloop.evals.fresh_harbor_partial_runner import (
    CANDIDATE_PATH,
    FileBinding,
    RunnerCandidate,
    artifact_bytes,
    load_candidate,
)
from patchloop.util import ensure_within, sha256_bytes, sha256_json

SOURCE_SCHEMA = "lean-fresh-harbor-partial-preflight-source-qualification-v1"
SOURCE_ID = "lean-fresh-harbor-partial-preflight-20260818-r1"
SOURCE_PATH = (
    "reports/fresh-panel/artifacts/lean-fresh-harbor-partial-preflight-source-qualification-r1.json"
)
APPROVAL_SCHEMA = "lean-fresh-harbor-partial-preflight-approval-v1"
APPROVAL_PATH = "reports/fresh-panel/artifacts/lean-fresh-harbor-partial-preflight-approval-r1.json"
ATTEMPT_SCHEMA = "lean-fresh-harbor-partial-preflight-attempt-v1"
ATTEMPT_PATH = "reports/fresh-panel/artifacts/lean-fresh-harbor-partial-preflight-attempt-r1.json"
TERMINAL_SCHEMA = "lean-fresh-harbor-partial-preflight-terminal-v1"
TERMINAL_PATH = "reports/fresh-panel/artifacts/lean-fresh-harbor-partial-preflight-terminal-r1.json"

RUNNER_BYTES = 92_174
RUNNER_FILE_SHA256 = "sha256:c2e63b4e9c679f0d3b5ff97d02399d9b4fcfac82ff2b18123937946667898082"
RUNNER_CONTENT_HASH = "sha256:f687a887c3c405ad76251b75aa45d89c20b528c8d9cf0724cf7020e05e1255c0"
EXECUTION_HASH = "sha256:92fb35e786a4dfe257d2c242c9a5e3ca62f0f330c497aa10b8235fb049dc2bdb"

APPROVAL_MESSAGE = (
    "execution hash sha256:92fb35e786a4dfe257d2c242c9a5e3ca62f0f330c497aa10b8235fb049dc2bdb"
    "에 대해 샌드박스 밖 Docker CLI/daemon 읽기 전용 no-call preflight 1회를 승인합니다. "
    "이미지 pull/build, 컨테이너 생성·실행, task/evaluator/provider 호출과 비용 발생은 "
    "승인하지 않습니다."
)
APPROVAL_MESSAGE_SHA256 = sha256_bytes(APPROVAL_MESSAGE.encode())

DOCKER_CONTEXT = "desktop-linux"
DOCKER_ENDPOINT = "npipe:////./pipe/dockerDesktopLinuxEngine"
DOCKER_CLI_BYTES = 43_095_472
DOCKER_CLI_SHA256 = "sha256:8985cd8ac002c3240b5aa48fe401fcb55dca5d849b537e3c835564e8e8c49a70"
DOCKER_VERSION_ARGS = (
    "--context",
    DOCKER_CONTEXT,
    "version",
    "--format",
    "{{json .}}",
)

SOURCE_PATHS = (
    "patchloop/evals/fresh_harbor_partial_preflight.py",
    "scripts/build_lean_fresh_harbor_partial_preflight_source_qualification.py",
    "scripts/run_lean_fresh_harbor_partial_preflight.py",
)
VALIDATION_PATHS = ("tests/test_fresh_harbor_partial_preflight.py",)

ARCHIVE_DIR_BY_TASK = {
    "harbor-framework__harbor-1764": "fresh-admission-harbor-1764",
    "marimo-team__marimo-9626": "fresh-admission-marimo-9626",
    "microsoft__apm-1553": "fresh-admission-apm-1553",
    "pydantic__pydantic-ai-5842": "fresh-admission-pydantic-ai-5842",
    "hkuds__nanobot-4048": "fresh-admission-nanobot-4048",
    "soju06__codex-lb-744": "fresh-admission-codex-lb-744",
    "nesquena__hermes-webui-3069": "fresh-admission-hermes-webui-3069",
    "agno-agi__agno-8148": "fresh-admission-agno-8148",
    "mozilla-ai__any-llm-1121": "fresh-admission-any-llm-1121",
    "livekit__agents-5944": "fresh-admission-livekit-agents-5944",
    "verl-project__verl-6506": "fresh-admission-verl-6506",
    "raullenchai__rapid-mlx-426": "fresh-admission-rapid-mlx-426",
}
BASE_IMAGE_BY_TASK = {
    "harbor-framework__harbor-1764": "docker.io/swerebenchv2/harbor-framework__harbor-1764:v0.1.0",
    "marimo-team__marimo-9626": "docker.io/swerebenchv2/marimo-team__marimo-9626:v0.1.0",
    "microsoft__apm-1553": "docker.io/swerebenchv2/microsoft__apm-1553:v0.1.0",
    "pydantic__pydantic-ai-5842": "docker.io/swerebenchv2/pydantic__pydantic-ai-5842:v0.1.0",
    "hkuds__nanobot-4048": "docker.io/swerebenchv2/hkuds__nanobot-4048:v0.1.0",
    "soju06__codex-lb-744": "docker.io/swerebenchv2/soju06__codex-lb-744:v0.1.0",
    "nesquena__hermes-webui-3069": "docker.io/swerebenchv2/nesquena__hermes-webui-3069:v0.1.0",
    "agno-agi__agno-8148": "docker.io/swerebenchv2/agno-agi__agno-8148:v0.1.0",
    "mozilla-ai__any-llm-1121": "docker.io/swerebenchv2/mozilla-ai__any-llm-1121:v0.1.0",
    "livekit__agents-5944": "docker.io/swerebenchv2/livekit__agents-5944:v0.1.0",
    "verl-project__verl-6506": "docker.io/swerebenchv2/verl-project__verl-6506:v0.1.0",
    "raullenchai__rapid-mlx-426": "docker.io/swerebenchv2/raullenchai__rapid-mlx-426:v0.1.0",
}


class FreshHarborPartialPreflightError(ContractError):
    """The bounded preflight source, authority, or evidence differs."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class SourceAuthority(FrozenModel):
    source_files_read: Literal[3]
    validation_files_read: Literal[1]
    runner_candidate_files_read: Literal[1]
    docker_cli_calls: Literal[0]
    docker_daemon_calls: Literal[0]
    package_archives_read: Literal[0]
    network_calls: Literal[0]
    image_store_mutations: Literal[0]
    container_mutations: Literal[0]
    task_evaluator_provider_calls: Literal[0]
    added_cost_usd: Literal[0]
    source_qualified: Literal[True]
    preflight_authorized: Literal[False]
    execution_authorized: Literal[False]


class SourceQualification(FrozenModel):
    schema_version: Literal[SOURCE_SCHEMA]
    qualification_id: Literal[SOURCE_ID]
    status: Literal["READ_ONLY_DOCKER_PREFLIGHT_SOURCE_QUALIFIED_NO_AUTHORITY"]
    runner_candidate_binding: FileBinding
    source_files: tuple[FileBinding, ...]
    validation_files: tuple[FileBinding, ...]
    source_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    checks: dict[str, bool]
    authority: SourceAuthority
    next_gate: Literal["record-exact-user-approval-and-preflight-attempt-intent"]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("source_files", "validation_files", mode="before")
    @classmethod
    def freeze_files(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_source(self) -> Self:
        if self.checks != _source_checks():
            raise ValueError("preflight source checks differ")
        if self.source_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.source_files]
        ):
            raise ValueError("preflight source inventory differs")
        if self.validation_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.validation_files]
        ):
            raise ValueError("preflight validation inventory differs")
        _check_content_hash(self)
        return self


class ApprovalAuthority(FrozenModel):
    self_attested_not_authenticated: Literal[True]
    exact_read_only_preflight_authorized: Literal[True]
    docker_version_authorized: Literal[True]
    bulk_image_inspect_authorized: Literal[True]
    image_pull_or_build_authorized: Literal[False]
    container_create_start_run_exec_authorized: Literal[False]
    harbor_task_evaluator_agent_provider_authorized: Literal[False]
    task_materialization_authorized: Literal[False]
    cost_authorized_usd: Literal[0]


class ApprovalReceipt(FrozenModel):
    schema_version: Literal[APPROVAL_SCHEMA]
    approval_id: Literal["lean-fresh-harbor-partial-preflight-approval-20260818-r1"]
    recorded_at: str
    status: Literal["EXACT_READ_ONLY_DOCKER_PREFLIGHT_APPROVED_ONCE"]
    runner_candidate_binding: FileBinding
    execution_hash: Literal[EXECUTION_HASH]
    source_qualification_binding: FileBinding
    user_message_sha256: Literal[APPROVAL_MESSAGE_SHA256]
    approved_scope: tuple[str, ...]
    explicitly_not_authorized: tuple[str, ...]
    authority: ApprovalAuthority
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("approved_scope", "explicitly_not_authorized", mode="before")
    @classmethod
    def freeze_scope(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_receipt(self) -> Self:
        if self.approved_scope != _approved_scope():
            raise ValueError("approved preflight scope differs")
        if self.explicitly_not_authorized != _denied_scope():
            raise ValueError("denied preflight scope differs")
        _check_content_hash(self)
        return self


class DockerCliBinding(FrozenModel):
    resolved_path: str
    file_bytes: Literal[DOCKER_CLI_BYTES]
    file_sha256: Literal[DOCKER_CLI_SHA256]


class ImageRequest(FrozenModel):
    task_id: str
    archive_path: str
    archive_bytes: int = Field(ge=1)
    archive_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    dockerfile_bytes: int = Field(ge=1)
    dockerfile_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    base_image_ref: str
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="before")
    @classmethod
    def exact_integers(cls, value: Any) -> Any:
        if isinstance(value, dict):
            for name in ("archive_bytes", "dockerfile_bytes"):
                if name in value and type(value[name]) is not int:
                    raise ValueError(f"{name} must be a JSON integer")
        return value

    @model_validator(mode="after")
    def validate_request(self) -> Self:
        _check_content_hash(self)
        return self


class AttemptAuthority(FrozenModel):
    user_approval_recorded: Literal[True]
    package_archives_read: Literal[12]
    dockerfiles_read: Literal[12]
    private_tests_or_reference_patches_read: Literal[0]
    docker_cli_calls: Literal[0]
    docker_daemon_calls: Literal[0]
    network_calls: Literal[0]
    image_store_mutations: Literal[0]
    container_mutations: Literal[0]
    task_evaluator_agent_provider_calls: Literal[0]
    added_cost_usd: Literal[0]
    execution_authorized: Literal[False]


class AttemptIntent(FrozenModel):
    schema_version: Literal[ATTEMPT_SCHEMA]
    attempt_id: Literal["lean-fresh-harbor-partial-preflight-attempt-20260818-r1"]
    recorded_at: str
    status: Literal["READ_ONLY_DOCKER_PREFLIGHT_ATTEMPT_RECORDED_BEFORE_CALL"]
    approval_binding: FileBinding
    runner_candidate_binding: FileBinding
    execution_hash: Literal[EXECUTION_HASH]
    docker_cli: DockerCliBinding
    docker_context: Literal[DOCKER_CONTEXT]
    docker_endpoint: Literal[DOCKER_ENDPOINT]
    environment_override_absent: Literal[True]
    image_requests: tuple[ImageRequest, ...]
    image_request_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    version_arguments: tuple[str, ...]
    image_inspect_arguments_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    shell: Literal[False]
    stdin: Literal["closed"]
    maximum_docker_cli_calls: Literal[2]
    authority: AttemptAuthority
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("image_requests", "version_arguments", mode="before")
    @classmethod
    def freeze_sequences(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_intent(self) -> Self:
        if len(self.image_requests) != 12:
            raise ValueError("preflight image-request count differs")
        if tuple(item.task_id for item in self.image_requests) != CANDIDATE_IDS:
            raise ValueError("preflight image-request task order differs")
        if len({item.base_image_ref for item in self.image_requests}) != 12:
            raise ValueError("preflight image refs are not unique")
        dumped = [item.model_dump(mode="json") for item in self.image_requests]
        if self.image_request_inventory_hash != sha256_json(dumped):
            raise ValueError("preflight image inventory differs")
        if self.version_arguments != DOCKER_VERSION_ARGS:
            raise ValueError("Docker version arguments differ")
        if self.image_inspect_arguments_hash != sha256_json(
            list(_image_inspect_args(self.image_requests))
        ):
            raise ValueError("Docker image-inspect arguments differ")
        _check_content_hash(self)
        return self


class ByteEvidence(FrozenModel):
    byte_count: int = Field(ge=0)
    sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="before")
    @classmethod
    def exact_count(cls, value: Any) -> Any:
        if (
            isinstance(value, dict)
            and "byte_count" in value
            and type(value["byte_count"]) is not int
        ):
            raise ValueError("byte_count must be a JSON integer")
        return value


class CommandObservation(FrozenModel):
    arguments_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    return_code: int
    stdout: ByteEvidence
    stderr: ByteEvidence

    @field_validator("return_code", mode="before")
    @classmethod
    def exact_return_code(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("return_code must be a JSON integer")
        return value


class DockerVersionProjection(FrozenModel):
    client_version: str
    client_api_version: str
    server_version: str
    server_api_version: str
    server_os: str
    server_arch: str


class ImageProjection(FrozenModel):
    requested_ref: str
    image_id: str
    os: str
    architecture: str
    size_bytes: int = Field(ge=0)

    @field_validator("size_bytes", mode="before")
    @classmethod
    def exact_size(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("size_bytes must be a JSON integer")
        return value


class TerminalAuthority(FrozenModel):
    docker_cli_calls: int = Field(ge=1, le=2)
    docker_daemon_read_calls: int = Field(ge=1, le=2)
    image_inspect_requested_refs: int = Field(ge=0, le=12)
    image_pull_or_build_calls: Literal[0]
    image_store_mutations: Literal[0]
    container_create_start_run_exec_calls: Literal[0]
    harbor_calls: Literal[0]
    task_materializations: Literal[0]
    evaluator_calls: Literal[0]
    agent_runs: Literal[0]
    provider_calls: Literal[0]
    network_calls: Literal[0]
    added_cost_usd: Literal[0]
    preflight_consumed: Literal[True]
    execution_authorized: Literal[False]
    admission_authorized: Literal[False]

    @model_validator(mode="before")
    @classmethod
    def exact_counts(cls, value: Any) -> Any:
        if isinstance(value, dict):
            for name in (
                "docker_cli_calls",
                "docker_daemon_read_calls",
                "image_inspect_requested_refs",
            ):
                if name in value and type(value[name]) is not int:
                    raise ValueError(f"{name} must be a JSON integer")
        return value


class TerminalObservation(FrozenModel):
    schema_version: Literal[TERMINAL_SCHEMA]
    terminal_id: Literal["lean-fresh-harbor-partial-preflight-terminal-20260818-r1"]
    recorded_at: str
    status: Literal[
        "READ_ONLY_DOCKER_PREFLIGHT_PASS",
        "READ_ONLY_DOCKER_PREFLIGHT_BLOCKED_DAEMON",
        "READ_ONLY_DOCKER_PREFLIGHT_BLOCKED_IMAGES",
        "READ_ONLY_DOCKER_PREFLIGHT_BLOCKED_INVALID_OUTPUT",
    ]
    attempt_binding: FileBinding
    execution_hash: Literal[EXECUTION_HASH]
    docker_cli: DockerCliBinding
    docker_context: Literal[DOCKER_CONTEXT]
    docker_endpoint: Literal[DOCKER_ENDPOINT]
    version_command: CommandObservation
    version: DockerVersionProjection | None
    image_inspect_command: CommandObservation | None
    images: tuple[ImageProjection, ...]
    missing_refs_identified_from_stderr: tuple[str, ...]
    raw_stdout_or_stderr_persisted: Literal[False]
    authority: TerminalAuthority
    next_gate: Literal[
        "implement-and-source-qualify-executor-without-running-rows",
        "obtain-separate-local-image-readiness-remediation-authority",
        "repair-docker-daemon-outside-this-consumed-preflight",
        "repair-preflight-parser-under-a-new-source-and-approval",
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("images", "missing_refs_identified_from_stderr", mode="before")
    @classmethod
    def freeze_terminal_sequences(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_terminal(self) -> Self:
        expected_next = {
            "READ_ONLY_DOCKER_PREFLIGHT_PASS": (
                "implement-and-source-qualify-executor-without-running-rows"
            ),
            "READ_ONLY_DOCKER_PREFLIGHT_BLOCKED_IMAGES": (
                "obtain-separate-local-image-readiness-remediation-authority"
            ),
            "READ_ONLY_DOCKER_PREFLIGHT_BLOCKED_DAEMON": (
                "repair-docker-daemon-outside-this-consumed-preflight"
            ),
            "READ_ONLY_DOCKER_PREFLIGHT_BLOCKED_INVALID_OUTPUT": (
                "repair-preflight-parser-under-a-new-source-and-approval"
            ),
        }[self.status]
        if self.next_gate != expected_next:
            raise ValueError("preflight terminal next gate differs")
        passed = self.status == "READ_ONLY_DOCKER_PREFLIGHT_PASS"
        if passed and not (
            self.version_command.return_code == 0
            and self.version is not None
            and self.image_inspect_command is not None
            and self.image_inspect_command.return_code == 0
            and len(self.images) == 12
            and not self.missing_refs_identified_from_stderr
            and self.authority.docker_cli_calls == 2
            and self.authority.image_inspect_requested_refs == 12
        ):
            raise ValueError("passing Docker preflight evidence is incomplete")
        _check_content_hash(self)
        return self


CommandRunner = Callable[[tuple[str, ...], int], subprocess.CompletedProcess[bytes]]


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _check_content_hash(value: BaseModel) -> None:
    dumped = value.model_dump(mode="json", exclude={"content_hash"})
    if value.model_dump(mode="json")["content_hash"] != sha256_json(dumped):
        raise ValueError("preflight content hash differs")


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _binding(root: Path, path: str, role: str) -> FileBinding:
    selected = ensure_within(root, path)
    lexical = root / Path(path)
    if lexical.is_symlink() or selected.is_symlink() or not selected.is_file():
        raise FreshHarborPartialPreflightError(f"required preflight file is unavailable: {path}")
    raw = selected.read_bytes()
    content_hash: str | None = None
    if path.endswith(".json"):
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and isinstance(parsed.get("content_hash"), str):
            content_hash = parsed["content_hash"]
    return FileBinding(
        path=path,
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        content_hash=content_hash,
        role=role,
    )


def _runner_binding(root: Path) -> tuple[FileBinding, RunnerCandidate]:
    candidate, raw = load_candidate(root)
    if not (
        len(raw) == RUNNER_BYTES
        and sha256_bytes(raw) == RUNNER_FILE_SHA256
        and candidate.content_hash == RUNNER_CONTENT_HASH
        and candidate.execution_hash == EXECUTION_HASH
    ):
        raise FreshHarborPartialPreflightError("sealed partial runner candidate differs")
    return (
        FileBinding(
            path=CANDIDATE_PATH,
            file_bytes=len(raw),
            file_sha256=sha256_bytes(raw),
            content_hash=candidate.content_hash,
            role="sealed-partial-runner-candidate",
        ),
        candidate,
    )


def _source_checks() -> dict[str, bool]:
    return {
        "exact-runner-candidate-and-execution-hash-bound": True,
        "exact-two-command-read-only-docker-surface": True,
        "explicit-local-desktop-linux-context-required": True,
        "environment-docker-endpoint-overrides-rejected": True,
        "twelve-archive-dockerfiles-only": True,
        "one-bulk-image-inspect-call": True,
        "raw-command-output-hashed-not-persisted": True,
        "no-image-pull-build-or-container-command": True,
        "no-harbor-task-evaluator-agent-provider-entrypoint": True,
        "append-only-approval-attempt-terminal": True,
    }


def build_source_qualification(root: Path) -> SourceQualification:
    root = root.resolve()
    runner, _candidate = _runner_binding(root)
    sources = tuple(_binding(root, path, "preflight-source") for path in SOURCE_PATHS)
    validation = tuple(_binding(root, path, "preflight-validation") for path in VALIDATION_PATHS)
    body: dict[str, Any] = {
        "schema_version": SOURCE_SCHEMA,
        "qualification_id": SOURCE_ID,
        "status": "READ_ONLY_DOCKER_PREFLIGHT_SOURCE_QUALIFIED_NO_AUTHORITY",
        "runner_candidate_binding": runner,
        "source_files": sources,
        "validation_files": validation,
        "source_inventory_hash": sha256_json([item.model_dump(mode="json") for item in sources]),
        "validation_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in validation]
        ),
        "checks": _source_checks(),
        "authority": SourceAuthority(
            source_files_read=3,
            validation_files_read=1,
            runner_candidate_files_read=1,
            docker_cli_calls=0,
            docker_daemon_calls=0,
            package_archives_read=0,
            network_calls=0,
            image_store_mutations=0,
            container_mutations=0,
            task_evaluator_provider_calls=0,
            added_cost_usd=0,
            source_qualified=True,
            preflight_authorized=False,
            execution_authorized=False,
        ),
        "next_gate": "record-exact-user-approval-and-preflight-attempt-intent",
    }
    return SourceQualification(**body, content_hash=sha256_json(_jsonable(body)))


def _approved_scope() -> tuple[str, ...]:
    return (
        "record-this-self-attested-exact-approval-receipt",
        "read-exact-local-runner-candidate-and-twelve-package-dockerfiles",
        "read-exact-local-docker-cli-bytes",
        "read-local-desktop-linux-docker-version-once",
        "inspect-the-twelve-exact-local-base-image-refs-in-one-call",
        "record-one-append-only-terminal-preflight-artifact",
    )


def _denied_scope() -> tuple[str, ...]:
    return (
        "image-pull-load-build-tag-remove-or-prune",
        "container-create-start-run-exec-stop-remove-or-restart",
        "harbor-task-evaluator-agent-or-provider-execution",
        "task-package-materialization",
        "network-or-credential-probe",
        "cost-reservation-or-spend",
        "admission-result-or-official-analysis",
    )


def build_approval_receipt(
    root: Path, source: SourceQualification, recorded_at: str
) -> ApprovalReceipt:
    runner, _candidate = _runner_binding(root.resolve())
    source_binding = _binding(root.resolve(), SOURCE_PATH, "preflight-source-qualification")
    if source_binding.content_hash != source.content_hash:
        raise FreshHarborPartialPreflightError("preflight source qualification differs")
    body: dict[str, Any] = {
        "schema_version": APPROVAL_SCHEMA,
        "approval_id": "lean-fresh-harbor-partial-preflight-approval-20260818-r1",
        "recorded_at": recorded_at,
        "status": "EXACT_READ_ONLY_DOCKER_PREFLIGHT_APPROVED_ONCE",
        "runner_candidate_binding": runner,
        "execution_hash": EXECUTION_HASH,
        "source_qualification_binding": source_binding,
        "user_message_sha256": APPROVAL_MESSAGE_SHA256,
        "approved_scope": _approved_scope(),
        "explicitly_not_authorized": _denied_scope(),
        "authority": ApprovalAuthority(
            self_attested_not_authenticated=True,
            exact_read_only_preflight_authorized=True,
            docker_version_authorized=True,
            bulk_image_inspect_authorized=True,
            image_pull_or_build_authorized=False,
            container_create_start_run_exec_authorized=False,
            harbor_task_evaluator_agent_provider_authorized=False,
            task_materialization_authorized=False,
            cost_authorized_usd=0,
        ),
    }
    return ApprovalReceipt(**body, content_hash=sha256_json(_jsonable(body)))


def _docker_cli_binding() -> DockerCliBinding:
    selected = shutil.which("docker")
    if selected is None:
        raise FreshHarborPartialPreflightError("Docker CLI is unavailable")
    path = Path(selected).resolve()
    raw = path.read_bytes()
    if len(raw) != DOCKER_CLI_BYTES or sha256_bytes(raw) != DOCKER_CLI_SHA256:
        raise FreshHarborPartialPreflightError("Docker CLI identity differs")
    return DockerCliBinding(
        resolved_path=str(path),
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
    )


def _validate_local_context() -> None:
    if os.environ.get("DOCKER_HOST") or os.environ.get("DOCKER_CONTEXT"):
        raise FreshHarborPartialPreflightError("Docker endpoint environment override is present")
    docker_root = Path.home() / ".docker"
    config_path = docker_root / "config.json"
    if not config_path.is_file():
        raise FreshHarborPartialPreflightError("Docker client config is unavailable")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("currentContext") != DOCKER_CONTEXT:
        raise FreshHarborPartialPreflightError("Docker current context differs")
    matches: list[str] = []
    for path in (docker_root / "contexts" / "meta").glob("*/meta.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if value.get("Name") == DOCKER_CONTEXT:
            endpoint = ((value.get("Endpoints") or {}).get("docker") or {}).get("Host")
            if isinstance(endpoint, str):
                matches.append(endpoint)
    if matches != [DOCKER_ENDPOINT]:
        raise FreshHarborPartialPreflightError("Docker local context endpoint differs")


def _archive_sha_by_task(candidate: RunnerCandidate) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in candidate.rows:
        existing = result.setdefault(row.task_id, row.package_archive_sha256)
        if existing != row.package_archive_sha256:
            raise FreshHarborPartialPreflightError("task archive hash differs across rows")
    return result


def _read_dockerfile(raw_archive: Path) -> bytes:
    try:
        with tarfile.open(raw_archive, "r:gz") as archive:
            members = [
                item
                for item in archive.getmembers()
                if item.name.rstrip("/").endswith("environment/Dockerfile")
            ]
            if len(members) != 1 or not members[0].isfile():
                raise FreshHarborPartialPreflightError("package Dockerfile member differs")
            extracted = archive.extractfile(members[0])
            if extracted is None:
                raise FreshHarborPartialPreflightError("package Dockerfile is unavailable")
            return extracted.read()
    except (OSError, tarfile.TarError) as exc:
        raise FreshHarborPartialPreflightError("package archive is unavailable") from exc


def _image_requests(root: Path, candidate: RunnerCandidate) -> tuple[ImageRequest, ...]:
    archive_sha = _archive_sha_by_task(candidate)
    if set(archive_sha) != set(CANDIDATE_IDS):
        raise FreshHarborPartialPreflightError("candidate task archive set differs")
    requests: list[ImageRequest] = []
    for task_id in CANDIDATE_IDS:
        relative = f".tmp/{ARCHIVE_DIR_BY_TASK[task_id]}/dist.tar.gz"
        path = ensure_within(root, relative)
        if not path.is_file() or path.is_symlink():
            raise FreshHarborPartialPreflightError("package archive is unavailable or linked")
        raw = path.read_bytes()
        if sha256_bytes(raw) != archive_sha[task_id]:
            raise FreshHarborPartialPreflightError("package archive bytes differ")
        dockerfile = _read_dockerfile(path)
        lines = [
            line.strip().split()[1]
            for line in dockerfile.decode("utf-8").splitlines()
            if line.strip().upper().startswith("FROM ")
        ]
        if lines != [BASE_IMAGE_BY_TASK[task_id]]:
            raise FreshHarborPartialPreflightError("package base image reference differs")
        body = {
            "task_id": task_id,
            "archive_path": relative,
            "archive_bytes": len(raw),
            "archive_sha256": sha256_bytes(raw),
            "dockerfile_bytes": len(dockerfile),
            "dockerfile_sha256": sha256_bytes(dockerfile),
            "base_image_ref": lines[0],
        }
        requests.append(ImageRequest(**body, content_hash=sha256_json(body)))
    return tuple(requests)


def _image_inspect_args(requests: tuple[ImageRequest, ...]) -> tuple[str, ...]:
    return (
        "--context",
        DOCKER_CONTEXT,
        "image",
        "inspect",
        *(item.base_image_ref for item in requests),
    )


def build_attempt_intent(
    root: Path,
    approval: ApprovalReceipt,
    recorded_at: str,
) -> AttemptIntent:
    root = root.resolve()
    _validate_local_context()
    runner, candidate = _runner_binding(root)
    approval_binding = _binding(root, APPROVAL_PATH, "exact-user-preflight-approval")
    if approval_binding.content_hash != approval.content_hash:
        raise FreshHarborPartialPreflightError("preflight approval differs")
    requests = _image_requests(root, candidate)
    body: dict[str, Any] = {
        "schema_version": ATTEMPT_SCHEMA,
        "attempt_id": "lean-fresh-harbor-partial-preflight-attempt-20260818-r1",
        "recorded_at": recorded_at,
        "status": "READ_ONLY_DOCKER_PREFLIGHT_ATTEMPT_RECORDED_BEFORE_CALL",
        "approval_binding": approval_binding,
        "runner_candidate_binding": runner,
        "execution_hash": EXECUTION_HASH,
        "docker_cli": _docker_cli_binding(),
        "docker_context": DOCKER_CONTEXT,
        "docker_endpoint": DOCKER_ENDPOINT,
        "environment_override_absent": True,
        "image_requests": requests,
        "image_request_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in requests]
        ),
        "version_arguments": DOCKER_VERSION_ARGS,
        "image_inspect_arguments_hash": sha256_json(list(_image_inspect_args(requests))),
        "shell": False,
        "stdin": "closed",
        "maximum_docker_cli_calls": 2,
        "authority": AttemptAuthority(
            user_approval_recorded=True,
            package_archives_read=12,
            dockerfiles_read=12,
            private_tests_or_reference_patches_read=0,
            docker_cli_calls=0,
            docker_daemon_calls=0,
            network_calls=0,
            image_store_mutations=0,
            container_mutations=0,
            task_evaluator_agent_provider_calls=0,
            added_cost_usd=0,
            execution_authorized=False,
        ),
    }
    return AttemptIntent(**body, content_hash=sha256_json(_jsonable(body)))


def _byte_evidence(value: bytes) -> ByteEvidence:
    return ByteEvidence(byte_count=len(value), sha256=sha256_bytes(value))


def _command_observation(
    arguments: tuple[str, ...], result: subprocess.CompletedProcess[bytes]
) -> CommandObservation:
    return CommandObservation(
        arguments_hash=sha256_json(list(arguments)),
        return_code=int(result.returncode),
        stdout=_byte_evidence(result.stdout),
        stderr=_byte_evidence(result.stderr),
    )


def _parse_version(raw: bytes) -> DockerVersionProjection:
    value = json.loads(raw)
    client = value["Client"]
    server = value["Server"]
    return DockerVersionProjection(
        client_version=str(client["Version"]),
        client_api_version=str(client["ApiVersion"]),
        server_version=str(server["Version"]),
        server_api_version=str(server["ApiVersion"]),
        server_os=str(server["Os"]),
        server_arch=str(server["Arch"]),
    )


def _parse_images(raw: bytes, requests: tuple[ImageRequest, ...]) -> tuple[ImageProjection, ...]:
    values = json.loads(raw)
    if not isinstance(values, list) or len(values) != len(requests):
        raise FreshHarborPartialPreflightError("Docker image-inspect count differs")
    images: list[ImageProjection] = []
    for request, value in zip(requests, values, strict=True):
        images.append(
            ImageProjection(
                requested_ref=request.base_image_ref,
                image_id=str(value["Id"]),
                os=str(value["Os"]),
                architecture=str(value["Architecture"]),
                size_bytes=int(value["Size"]),
            )
        )
    return tuple(images)


def _missing_refs(stderr: bytes, requests: tuple[ImageRequest, ...]) -> tuple[str, ...]:
    text = stderr.decode("utf-8", errors="replace")
    return tuple(item.base_image_ref for item in requests if item.base_image_ref in text)


def _default_runner(arguments: tuple[str, ...], timeout: int) -> subprocess.CompletedProcess[bytes]:
    docker = _docker_cli_binding().resolved_path
    environment = os.environ.copy()
    environment.pop("DOCKER_HOST", None)
    environment.pop("DOCKER_CONTEXT", None)
    environment["DOCKER_CLI_HINTS"] = "false"
    return subprocess.run(
        [docker, *arguments],
        check=False,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=timeout,
        shell=False,
        env=environment,
    )


def observe_preflight(
    attempt: AttemptIntent,
    recorded_at: str,
    runner: CommandRunner = _default_runner,
) -> TerminalObservation:
    version_result = runner(DOCKER_VERSION_ARGS, 30)
    version_command = _command_observation(DOCKER_VERSION_ARGS, version_result)
    version: DockerVersionProjection | None = None
    image_result: subprocess.CompletedProcess[bytes] | None = None
    image_command: CommandObservation | None = None
    images: tuple[ImageProjection, ...] = ()
    missing: tuple[str, ...] = ()
    calls = 1
    try:
        if version_result.returncode != 0:
            status = "READ_ONLY_DOCKER_PREFLIGHT_BLOCKED_DAEMON"
        else:
            version = _parse_version(version_result.stdout)
            image_args = _image_inspect_args(attempt.image_requests)
            image_result = runner(image_args, 60)
            calls = 2
            image_command = _command_observation(image_args, image_result)
            if image_result.returncode != 0:
                missing = _missing_refs(image_result.stderr, attempt.image_requests)
                status = "READ_ONLY_DOCKER_PREFLIGHT_BLOCKED_IMAGES"
            else:
                images = _parse_images(image_result.stdout, attempt.image_requests)
                status = "READ_ONLY_DOCKER_PREFLIGHT_PASS"
    except (
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        FreshHarborPartialPreflightError,
    ):
        status = "READ_ONLY_DOCKER_PREFLIGHT_BLOCKED_INVALID_OUTPUT"
    next_gate = {
        "READ_ONLY_DOCKER_PREFLIGHT_PASS": (
            "implement-and-source-qualify-executor-without-running-rows"
        ),
        "READ_ONLY_DOCKER_PREFLIGHT_BLOCKED_IMAGES": (
            "obtain-separate-local-image-readiness-remediation-authority"
        ),
        "READ_ONLY_DOCKER_PREFLIGHT_BLOCKED_DAEMON": (
            "repair-docker-daemon-outside-this-consumed-preflight"
        ),
        "READ_ONLY_DOCKER_PREFLIGHT_BLOCKED_INVALID_OUTPUT": (
            "repair-preflight-parser-under-a-new-source-and-approval"
        ),
    }[status]
    body: dict[str, Any] = {
        "schema_version": TERMINAL_SCHEMA,
        "terminal_id": "lean-fresh-harbor-partial-preflight-terminal-20260818-r1",
        "recorded_at": recorded_at,
        "status": status,
        "attempt_binding": FileBinding(
            path=ATTEMPT_PATH,
            file_bytes=len(artifact_bytes(attempt)),
            file_sha256=sha256_bytes(artifact_bytes(attempt)),
            content_hash=attempt.content_hash,
            role="read-only-docker-preflight-attempt",
        ),
        "execution_hash": EXECUTION_HASH,
        "docker_cli": attempt.docker_cli,
        "docker_context": DOCKER_CONTEXT,
        "docker_endpoint": DOCKER_ENDPOINT,
        "version_command": version_command,
        "version": version,
        "image_inspect_command": image_command,
        "images": images,
        "missing_refs_identified_from_stderr": missing,
        "raw_stdout_or_stderr_persisted": False,
        "authority": TerminalAuthority(
            docker_cli_calls=calls,
            docker_daemon_read_calls=calls,
            image_inspect_requested_refs=12 if image_result is not None else 0,
            image_pull_or_build_calls=0,
            image_store_mutations=0,
            container_create_start_run_exec_calls=0,
            harbor_calls=0,
            task_materializations=0,
            evaluator_calls=0,
            agent_runs=0,
            provider_calls=0,
            network_calls=0,
            added_cost_usd=0,
            preflight_consumed=True,
            execution_authorized=False,
            admission_authorized=False,
        ),
        "next_gate": next_gate,
    }
    return TerminalObservation(**body, content_hash=sha256_json(_jsonable(body)))


def _write_once(root: Path, path: str, value: BaseModel, role: str) -> FileBinding:
    selected = ensure_within(root, path)
    raw = artifact_bytes(value)
    if selected.exists():
        if selected.read_bytes() != raw:
            raise FreshHarborPartialPreflightError(
                f"append-only preflight artifact differs: {path}"
            )
    else:
        selected.parent.mkdir(parents=True, exist_ok=True)
        with selected.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    return FileBinding(
        path=path,
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        content_hash=str(value.model_dump(mode="json")["content_hash"]),
        role=role,
    )


def _load(root: Path, path: str, model: type[FrozenModel]) -> tuple[FrozenModel, bytes]:
    selected = ensure_within(root.resolve(), path)
    if not selected.is_file() or selected.is_symlink():
        raise FreshHarborPartialPreflightError(f"preflight artifact is unavailable: {path}")
    raw = selected.read_bytes()
    try:
        value = model.model_validate_json(raw)
    except ValueError as exc:
        raise FreshHarborPartialPreflightError(f"preflight artifact is invalid: {path}") from exc
    if artifact_bytes(value) != raw:
        raise FreshHarborPartialPreflightError(f"preflight artifact is noncanonical: {path}")
    return value, raw


def materialize_source_qualification(root: Path) -> FileBinding:
    root = root.resolve()
    return _write_once(
        root,
        SOURCE_PATH,
        build_source_qualification(root),
        "read-only-docker-preflight-source-qualification",
    )


def materialize_approval_and_attempt(root: Path) -> tuple[FileBinding, FileBinding]:
    root = root.resolve()
    source_value, _source_raw = _load(root, SOURCE_PATH, SourceQualification)
    assert isinstance(source_value, SourceQualification)
    approval = build_approval_receipt(root, source_value, _now())
    approval_binding = _write_once(root, APPROVAL_PATH, approval, "exact-user-preflight-approval")
    attempt = build_attempt_intent(root, approval, _now())
    attempt_binding = _write_once(root, ATTEMPT_PATH, attempt, "read-only-docker-preflight-attempt")
    return approval_binding, attempt_binding


def run_preflight_once(root: Path) -> FileBinding:
    root = root.resolve()
    terminal = ensure_within(root, TERMINAL_PATH)
    if terminal.exists():
        raise FreshHarborPartialPreflightError("read-only Docker preflight is already consumed")
    source, _source_raw = _load(root, SOURCE_PATH, SourceQualification)
    approval, _approval_raw = _load(root, APPROVAL_PATH, ApprovalReceipt)
    attempt, _attempt_raw = _load(root, ATTEMPT_PATH, AttemptIntent)
    assert isinstance(source, SourceQualification)
    assert isinstance(approval, ApprovalReceipt)
    assert isinstance(attempt, AttemptIntent)
    if attempt.approval_binding.content_hash != approval.content_hash:
        raise FreshHarborPartialPreflightError("preflight attempt approval binding differs")
    current_source = build_source_qualification(root)
    if source != current_source:
        raise FreshHarborPartialPreflightError("preflight source qualification drifted")
    _validate_local_context()
    result = observe_preflight(attempt, _now())
    return _write_once(root, TERMINAL_PATH, result, "read-only-docker-preflight-terminal")


def load_terminal(root: Path) -> tuple[TerminalObservation, bytes]:
    value, raw = _load(root.resolve(), TERMINAL_PATH, TerminalObservation)
    assert isinstance(value, TerminalObservation)
    attempt, attempt_raw = _load(root.resolve(), ATTEMPT_PATH, AttemptIntent)
    assert isinstance(attempt, AttemptIntent)
    if not (
        value.attempt_binding.file_bytes == len(attempt_raw)
        and value.attempt_binding.file_sha256 == sha256_bytes(attempt_raw)
        and value.attempt_binding.content_hash == attempt.content_hash
    ):
        raise FreshHarborPartialPreflightError("preflight terminal attempt binding differs")
    return value, raw
