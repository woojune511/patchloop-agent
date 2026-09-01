"""One-call local-image inventory successor for the sealed Harbor runner.

The consumed bulk-inspect preflight could not identify individual missing
images.  This successor binds one read-only ``docker image ls`` command and
projects only the twelve preregistered tags.  Source/candidate builders never
open Docker; the external entrypoint remains approval-gated and one-use.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.errors import ContractError
from patchloop.evals.fresh_all_cross_successor import CANDIDATE_IDS
from patchloop.evals.fresh_harbor_partial_preflight import (
    BASE_IMAGE_BY_TASK,
    DOCKER_CLI_BYTES,
    DOCKER_CLI_SHA256,
    DOCKER_CONTEXT,
    DOCKER_ENDPOINT,
    DockerCliBinding,
    _docker_cli_binding,
    _validate_local_context,
)
from patchloop.evals.fresh_harbor_partial_runner import FileBinding, artifact_bytes
from patchloop.util import ensure_within, sha256_bytes, sha256_json

SOURCE_SCHEMA = "lean-fresh-harbor-local-image-inventory-source-qualification-v1"
SOURCE_ID = "lean-fresh-harbor-local-image-inventory-20260818-r1"
SOURCE_PATH = (
    "reports/fresh-panel/artifacts/"
    "lean-fresh-harbor-local-image-inventory-source-qualification-r1.json"
)
CANDIDATE_SCHEMA = "lean-fresh-harbor-local-image-inventory-candidate-v1"
CANDIDATE_ID = "lean-fresh-harbor-local-image-inventory-20260818-v1"
CANDIDATE_PATH = "experiments/lean-harness-fresh-harbor-local-image-inventory-20260818-v1.json"
APPROVAL_SCHEMA = "lean-fresh-harbor-local-image-inventory-approval-v1"
APPROVAL_PATH = (
    "reports/fresh-panel/artifacts/lean-fresh-harbor-local-image-inventory-approval-r1.json"
)
ATTEMPT_SCHEMA = "lean-fresh-harbor-local-image-inventory-attempt-v1"
ATTEMPT_PATH = (
    "reports/fresh-panel/artifacts/lean-fresh-harbor-local-image-inventory-attempt-r1.json"
)
TERMINAL_SCHEMA = "lean-fresh-harbor-local-image-inventory-terminal-v1"
TERMINAL_PATH = (
    "reports/fresh-panel/artifacts/lean-fresh-harbor-local-image-inventory-terminal-r1.json"
)

RUNNER_EXECUTION_HASH = "sha256:92fb35e786a4dfe257d2c242c9a5e3ca62f0f330c497aa10b8235fb049dc2bdb"
RUNNER_PATH = "experiments/lean-harness-fresh-harbor-partial-admission-runner-20260818-v1.json"
RUNNER_BYTES = 92_174
RUNNER_FILE_SHA256 = "sha256:c2e63b4e9c679f0d3b5ff97d02399d9b4fcfac82ff2b18123937946667898082"
RUNNER_CONTENT_HASH = "sha256:f687a887c3c405ad76251b75aa45d89c20b528c8d9cf0724cf7020e05e1255c0"
PREDECESSOR_SOURCE_PATH = "patchloop/evals/fresh_harbor_partial_preflight.py"
PREDECESSOR_SOURCE_BYTES = 42_709
PREDECESSOR_SOURCE_SHA256 = (
    "sha256:bf4555eff79b8db58e83567e93a2ad61a0e434ad842d5e1939bd4ddd344d6a69"
)
PREDECESSOR_TERMINAL_PATH = (
    "reports/fresh-panel/artifacts/lean-fresh-harbor-partial-preflight-terminal-r1.json"
)
PREDECESSOR_TERMINAL_BYTES = 2_940
PREDECESSOR_TERMINAL_FILE_SHA256 = (
    "sha256:fb40fab9a53756ca2dfef4d9f0a88d326f077c7402744cfaebaac351cebfe9a2"
)
PREDECESSOR_TERMINAL_CONTENT_HASH = (
    "sha256:725a230863af4ae43f1c447323cba06e61140920be8b928c4065a3bd4c52b94e"
)

SOURCE_PATHS = (
    "patchloop/evals/fresh_harbor_local_image_inventory.py",
    "scripts/build_lean_fresh_harbor_local_image_inventory_source_qualification.py",
    "scripts/build_lean_fresh_harbor_local_image_inventory_candidate.py",
    "scripts/run_lean_fresh_harbor_local_image_inventory.py",
)
VALIDATION_PATHS = ("tests/test_fresh_harbor_local_image_inventory.py",)
IMAGE_LS_ARGS = (
    "--context",
    DOCKER_CONTEXT,
    "image",
    "ls",
    "--no-trunc",
    "--format",
    "{{json .}}",
)
APPROVAL_TEMPLATE = (
    "execution hash {execution_hash}에 대해 샌드박스 밖 Docker CLI/daemon 읽기 전용 "
    "local-image inventory 1회를 승인합니다. 허용 명령은 고정된 docker image ls "
    "1회뿐이며, 이미지 pull/build/tag/remove/prune, "
    "컨테이너 생성·실행, task/evaluator/provider 호출과 비용 발생은 승인하지 않습니다."
)


class FreshHarborLocalImageInventoryError(ContractError):
    """The local-image inventory source, candidate, or evidence differs."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ZeroAuthority(FrozenModel):
    source_files_read: int = Field(ge=0)
    validation_files_read: int = Field(ge=0)
    predecessor_files_read: int = Field(ge=0)
    docker_cli_calls: Literal[0]
    docker_daemon_calls: Literal[0]
    network_calls: Literal[0]
    image_store_mutations: Literal[0]
    container_mutations: Literal[0]
    task_evaluator_agent_provider_calls: Literal[0]
    added_cost_usd: Literal[0]
    source_qualified: bool
    candidate_materialized: bool
    inventory_preflight_authorized: Literal[False]
    execution_authorized: Literal[False]

    @model_validator(mode="before")
    @classmethod
    def exact_ints(cls, value: Any) -> Any:
        if isinstance(value, dict):
            for name in ("source_files_read", "validation_files_read", "predecessor_files_read"):
                if name in value and type(value[name]) is not int:
                    raise ValueError(f"{name} must be a JSON integer")
        return value


class SourceQualification(FrozenModel):
    schema_version: Literal[SOURCE_SCHEMA]
    qualification_id: Literal[SOURCE_ID]
    status: Literal["LOCAL_IMAGE_INVENTORY_SOURCE_QUALIFIED_NO_DOCKER_AUTHORITY"]
    predecessor_bindings: tuple[FileBinding, ...]
    source_files: tuple[FileBinding, ...]
    validation_files: tuple[FileBinding, ...]
    source_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    checks: dict[str, bool]
    authority: ZeroAuthority
    next_gate: Literal["materialize-execution-closed-local-image-inventory-candidate"]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("predecessor_bindings", "source_files", "validation_files", mode="before")
    @classmethod
    def freeze_bindings(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_source(self) -> Self:
        if self.predecessor_bindings != _expected_predecessors():
            raise ValueError("local-image predecessor bindings differ")
        if tuple(item.path for item in self.source_files) != SOURCE_PATHS:
            raise ValueError("local-image source paths differ")
        if tuple(item.path for item in self.validation_files) != VALIDATION_PATHS:
            raise ValueError("local-image validation paths differ")
        if self.checks != _source_checks():
            raise ValueError("local-image source checks differ")
        if self.authority != _source_authority():
            raise ValueError("local-image source authority differs")
        if self.source_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.source_files]
        ):
            raise ValueError("local-image source inventory differs")
        if self.validation_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.validation_files]
        ):
            raise ValueError("local-image validation inventory differs")
        _check_content_hash(self)
        return self


class TargetImage(FrozenModel):
    task_id: str
    requested_ref: str
    normalized_tag: str
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_target(self) -> Self:
        if self.normalized_tag != _normalize_ref(self.requested_ref):
            raise ValueError("normalized image tag differs")
        _check_content_hash(self)
        return self


class Candidate(FrozenModel):
    schema_version: Literal[CANDIDATE_SCHEMA]
    candidate_id: Literal[CANDIDATE_ID]
    status: Literal["EXACT_LOCAL_IMAGE_INVENTORY_CANDIDATE_EXECUTION_CLOSED"]
    source_qualification_binding: FileBinding
    runner_candidate_binding: FileBinding
    predecessor_terminal_binding: FileBinding
    runner_execution_hash: Literal[RUNNER_EXECUTION_HASH]
    docker_cli: DockerCliBinding
    docker_context: Literal[DOCKER_CONTEXT]
    docker_endpoint: Literal[DOCKER_ENDPOINT]
    command_arguments: tuple[str, ...]
    shell: Literal[False]
    stdin: Literal["closed"]
    target_images: tuple[TargetImage, ...]
    target_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_contract: dict[str, bool]
    execution_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approval_message_template: Literal[APPROVAL_TEMPLATE]
    authority: ZeroAuthority
    next_gate: Literal["obtain-exact-user-approval-for-this-inventory-execution-hash"]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("command_arguments", "target_images", mode="before")
    @classmethod
    def freeze_candidate_sequences(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_candidate(self) -> Self:
        if self.runner_candidate_binding != _expected_predecessors()[0]:
            raise ValueError("local-image runner binding differs")
        if self.predecessor_terminal_binding != _expected_predecessors()[1]:
            raise ValueError("local-image terminal binding differs")
        if self.source_qualification_binding.path != SOURCE_PATH or (
            self.source_qualification_binding.role != "local-image-inventory-source-qualification"
        ):
            raise ValueError("local-image source qualification binding differs")
        if (self.docker_cli.file_bytes, self.docker_cli.file_sha256) != (
            DOCKER_CLI_BYTES,
            DOCKER_CLI_SHA256,
        ):
            raise ValueError("local-image Docker CLI binding differs")
        if self.command_arguments != IMAGE_LS_ARGS:
            raise ValueError("local-image inventory command differs")
        if tuple(item.task_id for item in self.target_images) != CANDIDATE_IDS:
            raise ValueError("local-image target order differs")
        if len({item.normalized_tag for item in self.target_images}) != 12:
            raise ValueError("local-image target tags are not unique")
        dumped = [item.model_dump(mode="json") for item in self.target_images]
        if self.target_inventory_hash != sha256_json(dumped):
            raise ValueError("local-image target inventory differs")
        if self.evidence_contract != _evidence_contract():
            raise ValueError("local-image evidence contract differs")
        if self.authority != _candidate_authority():
            raise ValueError("local-image candidate authority differs")
        projection = self.model_dump(
            mode="json",
            exclude={
                "execution_hash",
                "approval_message_template",
                "authority",
                "next_gate",
                "content_hash",
            },
        )
        if self.execution_hash != sha256_json(projection):
            raise ValueError("local-image execution hash differs")
        _check_content_hash(self)
        return self


class ApprovalReceipt(FrozenModel):
    schema_version: Literal["lean-fresh-harbor-local-image-inventory-approval-v1"]
    approval_id: Literal["lean-fresh-harbor-local-image-inventory-approval-20260818-r1"]
    recorded_at: str
    status: Literal["EXACT_LOCAL_IMAGE_INVENTORY_APPROVED_ONCE"]
    candidate_binding: FileBinding
    execution_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    user_message_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_scope: tuple[str, ...]
    explicitly_not_authorized: tuple[str, ...]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("approved_scope", "explicitly_not_authorized", mode="before")
    @classmethod
    def freeze_scope(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_approval(self) -> Self:
        if self.approved_scope != _approved_scope():
            raise ValueError("local-image approved scope differs")
        if self.explicitly_not_authorized != _denied_scope():
            raise ValueError("local-image denied scope differs")
        _check_content_hash(self)
        return self


class AttemptIntent(FrozenModel):
    schema_version: Literal["lean-fresh-harbor-local-image-inventory-attempt-v1"]
    attempt_id: Literal["lean-fresh-harbor-local-image-inventory-attempt-20260818-r1"]
    recorded_at: str
    status: Literal["LOCAL_IMAGE_INVENTORY_ATTEMPT_RECORDED_BEFORE_CALL"]
    approval_binding: FileBinding
    candidate_binding: FileBinding
    execution_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    docker_cli: DockerCliBinding
    command_arguments_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    docker_cli_calls_before_attempt: Literal[0]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_attempt(self) -> Self:
        if self.command_arguments_hash != sha256_json(list(IMAGE_LS_ARGS)):
            raise ValueError("local-image attempt command hash differs")
        _check_content_hash(self)
        return self


class ByteEvidence(FrozenModel):
    byte_count: int = Field(ge=0)
    sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("byte_count", mode="before")
    @classmethod
    def exact_count(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("byte_count must be a JSON integer")
        return value


class TargetObservation(FrozenModel):
    task_id: str
    requested_ref: str
    normalized_tag: str
    present: bool
    image_id: str | None
    digest: str | None
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        if self.present != (self.image_id is not None):
            raise ValueError("local-image present projection differs")
        _check_content_hash(self)
        return self


class Terminal(FrozenModel):
    schema_version: Literal["lean-fresh-harbor-local-image-inventory-terminal-v1"]
    terminal_id: Literal["lean-fresh-harbor-local-image-inventory-terminal-20260818-r1"]
    recorded_at: str
    status: Literal[
        "LOCAL_IMAGE_INVENTORY_COMPLETE_ALL_PRESENT",
        "LOCAL_IMAGE_INVENTORY_COMPLETE_MISSING_IMAGES",
        "LOCAL_IMAGE_INVENTORY_BLOCKED_DOCKER_COMMAND",
        "LOCAL_IMAGE_INVENTORY_BLOCKED_INVALID_OUTPUT",
    ]
    attempt_binding: FileBinding
    execution_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    command_return_code: int
    stdout: ByteEvidence
    stderr: ByteEvidence
    target_observations: tuple[TargetObservation, ...]
    present_count: int = Field(ge=0, le=12)
    missing_count: int = Field(ge=0, le=12)
    unrelated_local_image_records_persisted: Literal[0]
    raw_stdout_or_stderr_persisted: Literal[False]
    docker_cli_calls: Literal[1]
    docker_daemon_read_calls: Literal[1]
    image_pull_build_tag_remove_prune_calls: Literal[0]
    container_mutations: Literal[0]
    network_calls: Literal[0]
    task_evaluator_agent_provider_calls: Literal[0]
    added_cost_usd: Literal[0]
    execution_authorized: Literal[False]
    next_gate: Literal[
        "implement-and-source-qualify-executor-without-running-rows",
        "obtain-exact-pull-authority-only-for-the-identified-missing-refs",
        "repair-local-image-inventory-under-a-new-source-and-approval",
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("target_observations", mode="before")
    @classmethod
    def freeze_observations(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="before")
    @classmethod
    def exact_ints(cls, value: Any) -> Any:
        if isinstance(value, dict):
            for name in ("command_return_code", "present_count", "missing_count"):
                if name in value and type(value[name]) is not int:
                    raise ValueError(f"{name} must be a JSON integer")
        return value

    @model_validator(mode="after")
    def validate_terminal(self) -> Self:
        if self.status.startswith("LOCAL_IMAGE_INVENTORY_COMPLETE"):
            if len(self.target_observations) != 12:
                raise ValueError("complete local-image inventory must have twelve targets")
            actual_present = sum(item.present for item in self.target_observations)
            if (self.present_count, self.missing_count) != (actual_present, 12 - actual_present):
                raise ValueError("local-image terminal counts differ")
        expected_next = {
            "LOCAL_IMAGE_INVENTORY_COMPLETE_ALL_PRESENT": (
                "implement-and-source-qualify-executor-without-running-rows"
            ),
            "LOCAL_IMAGE_INVENTORY_COMPLETE_MISSING_IMAGES": (
                "obtain-exact-pull-authority-only-for-the-identified-missing-refs"
            ),
            "LOCAL_IMAGE_INVENTORY_BLOCKED_DOCKER_COMMAND": (
                "repair-local-image-inventory-under-a-new-source-and-approval"
            ),
            "LOCAL_IMAGE_INVENTORY_BLOCKED_INVALID_OUTPUT": (
                "repair-local-image-inventory-under-a-new-source-and-approval"
            ),
        }[self.status]
        if self.next_gate != expected_next:
            raise ValueError("local-image terminal next gate differs")
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
        raise ValueError("local-image content hash differs")


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _normalize_ref(value: str) -> str:
    return value.removeprefix("docker.io/")


def _file_binding(root: Path, path: str, role: str) -> FileBinding:
    selected = ensure_within(root, path)
    lexical = root / Path(path)
    if lexical.is_symlink() or selected.is_symlink() or not selected.is_file():
        raise FreshHarborLocalImageInventoryError(f"required inventory file is unavailable: {path}")
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


def _expected_predecessors() -> tuple[FileBinding, ...]:
    return (
        FileBinding(
            path=RUNNER_PATH,
            file_bytes=RUNNER_BYTES,
            file_sha256=RUNNER_FILE_SHA256,
            content_hash=RUNNER_CONTENT_HASH,
            role="sealed-partial-runner-candidate",
        ),
        FileBinding(
            path=PREDECESSOR_TERMINAL_PATH,
            file_bytes=PREDECESSOR_TERMINAL_BYTES,
            file_sha256=PREDECESSOR_TERMINAL_FILE_SHA256,
            content_hash=PREDECESSOR_TERMINAL_CONTENT_HASH,
            role="consumed-bulk-inspect-preflight-terminal",
        ),
        FileBinding(
            path=PREDECESSOR_SOURCE_PATH,
            file_bytes=PREDECESSOR_SOURCE_BYTES,
            file_sha256=PREDECESSOR_SOURCE_SHA256,
            content_hash=None,
            role="consumed-preflight-source",
        ),
    )


def _predecessors(root: Path) -> tuple[FileBinding, ...]:
    actual = (
        _file_binding(root, RUNNER_PATH, "sealed-partial-runner-candidate"),
        _file_binding(
            root,
            PREDECESSOR_TERMINAL_PATH,
            "consumed-bulk-inspect-preflight-terminal",
        ),
        _file_binding(root, PREDECESSOR_SOURCE_PATH, "consumed-preflight-source"),
    )
    if actual != _expected_predecessors():
        raise FreshHarborLocalImageInventoryError("local-image predecessor differs")
    return actual


def _source_checks() -> dict[str, bool]:
    return {
        "consumed-preflight-terminal-bound-append-only": True,
        "runner-execution-hash-preserved": True,
        "exact-one-docker-image-ls-command": True,
        "local-desktop-linux-context-only": True,
        "twelve-exact-target-tags-only": True,
        "unrelated-image-records-never-persisted": True,
        "raw-streams-hash-only": True,
        "no-pull-build-tag-remove-prune-or-container-command": True,
        "no-harbor-task-evaluator-agent-provider-command": True,
        "call-claim-written-before-command-no-retry-after-uncertainty": True,
        "approval-attempt-terminal-append-only": True,
    }


def _evidence_contract() -> dict[str, bool]:
    return {
        "one-command-return-code-required": True,
        "stdout-and-stderr-byte-hashes-required": True,
        "exact-twelve-target-presence-projections-required-on-success": True,
        "unrelated-local-image-names-not-persisted": True,
        "raw-output-not-persisted": True,
        "missing-ref-list-is-target-derived-not-error-text-derived": True,
    }


def _source_authority() -> ZeroAuthority:
    return ZeroAuthority(
        source_files_read=4,
        validation_files_read=1,
        predecessor_files_read=3,
        docker_cli_calls=0,
        docker_daemon_calls=0,
        network_calls=0,
        image_store_mutations=0,
        container_mutations=0,
        task_evaluator_agent_provider_calls=0,
        added_cost_usd=0,
        source_qualified=True,
        candidate_materialized=False,
        inventory_preflight_authorized=False,
        execution_authorized=False,
    )


def _candidate_authority() -> ZeroAuthority:
    return ZeroAuthority(
        source_files_read=0,
        validation_files_read=0,
        predecessor_files_read=3,
        docker_cli_calls=0,
        docker_daemon_calls=0,
        network_calls=0,
        image_store_mutations=0,
        container_mutations=0,
        task_evaluator_agent_provider_calls=0,
        added_cost_usd=0,
        source_qualified=True,
        candidate_materialized=True,
        inventory_preflight_authorized=False,
        execution_authorized=False,
    )


def _target_images() -> tuple[TargetImage, ...]:
    result: list[TargetImage] = []
    for task_id in CANDIDATE_IDS:
        ref = BASE_IMAGE_BY_TASK[task_id]
        body = {"task_id": task_id, "requested_ref": ref, "normalized_tag": _normalize_ref(ref)}
        result.append(TargetImage(**body, content_hash=sha256_json(body)))
    return tuple(result)


def build_source_qualification(root: Path) -> SourceQualification:
    root = root.resolve()
    predecessors = _predecessors(root)
    sources = tuple(_file_binding(root, path, "local-image-source") for path in SOURCE_PATHS)
    validation = tuple(
        _file_binding(root, path, "local-image-validation") for path in VALIDATION_PATHS
    )
    body: dict[str, Any] = {
        "schema_version": SOURCE_SCHEMA,
        "qualification_id": SOURCE_ID,
        "status": "LOCAL_IMAGE_INVENTORY_SOURCE_QUALIFIED_NO_DOCKER_AUTHORITY",
        "predecessor_bindings": predecessors,
        "source_files": sources,
        "validation_files": validation,
        "source_inventory_hash": sha256_json([item.model_dump(mode="json") for item in sources]),
        "validation_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in validation]
        ),
        "checks": _source_checks(),
        "authority": _source_authority(),
        "next_gate": "materialize-execution-closed-local-image-inventory-candidate",
    }
    return SourceQualification(**body, content_hash=sha256_json(_jsonable(body)))


def _source_binding(value: SourceQualification) -> FileBinding:
    raw = artifact_bytes(value)
    return FileBinding(
        path=SOURCE_PATH,
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        content_hash=value.content_hash,
        role="local-image-inventory-source-qualification",
    )


def build_candidate(root: Path) -> Candidate:
    root = root.resolve()
    source = build_source_qualification(root)
    predecessors = _predecessors(root)
    _validate_local_context()
    docker_cli = _docker_cli_binding()
    if (docker_cli.file_bytes, docker_cli.file_sha256) != (
        DOCKER_CLI_BYTES,
        DOCKER_CLI_SHA256,
    ):
        raise FreshHarborLocalImageInventoryError("Docker CLI identity differs")
    targets = _target_images()
    body: dict[str, Any] = {
        "schema_version": CANDIDATE_SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "status": "EXACT_LOCAL_IMAGE_INVENTORY_CANDIDATE_EXECUTION_CLOSED",
        "source_qualification_binding": _source_binding(source),
        "runner_candidate_binding": predecessors[0],
        "predecessor_terminal_binding": predecessors[1],
        "runner_execution_hash": RUNNER_EXECUTION_HASH,
        "docker_cli": docker_cli,
        "docker_context": DOCKER_CONTEXT,
        "docker_endpoint": DOCKER_ENDPOINT,
        "command_arguments": IMAGE_LS_ARGS,
        "shell": False,
        "stdin": "closed",
        "target_images": targets,
        "target_inventory_hash": sha256_json([item.model_dump(mode="json") for item in targets]),
        "evidence_contract": _evidence_contract(),
    }
    execution_hash = sha256_json(_jsonable(body))
    body.update(
        execution_hash=execution_hash,
        approval_message_template=APPROVAL_TEMPLATE,
        authority=_candidate_authority(),
        next_gate="obtain-exact-user-approval-for-this-inventory-execution-hash",
    )
    return Candidate(**body, content_hash=sha256_json(_jsonable(body)))


def expected_approval_message(candidate: Candidate) -> str:
    return candidate.approval_message_template.format(execution_hash=candidate.execution_hash)


def _approved_scope() -> tuple[str, ...]:
    return (
        "record-this-self-attested-exact-approval",
        "run-the-exact-local-docker-image-ls-command-once",
        "persist-only-the-twelve-target-presence-projections",
        "record-one-append-only-terminal",
    )


def _denied_scope() -> tuple[str, ...]:
    return (
        "image-pull-build-tag-remove-prune-or-load",
        "container-create-start-run-exec-stop-remove-or-restart",
        "harbor-task-evaluator-agent-provider-or-network-execution",
        "credential-probe-cost-or-admission-result",
    )


def build_approval(
    root: Path, candidate: Candidate, user_message: str, recorded_at: str
) -> ApprovalReceipt:
    root = root.resolve()
    current = load_candidate(root)[0]
    if current != candidate or user_message != expected_approval_message(candidate):
        raise FreshHarborLocalImageInventoryError("exact local-image approval message differs")
    binding = _file_binding(root, CANDIDATE_PATH, "local-image-inventory-candidate")
    body: dict[str, Any] = {
        "schema_version": APPROVAL_SCHEMA,
        "approval_id": "lean-fresh-harbor-local-image-inventory-approval-20260818-r1",
        "recorded_at": recorded_at,
        "status": "EXACT_LOCAL_IMAGE_INVENTORY_APPROVED_ONCE",
        "candidate_binding": binding,
        "execution_hash": candidate.execution_hash,
        "user_message_sha256": sha256_bytes(user_message.encode()),
        "approved_scope": _approved_scope(),
        "explicitly_not_authorized": _denied_scope(),
    }
    return ApprovalReceipt(**body, content_hash=sha256_json(_jsonable(body)))


def build_attempt(
    root: Path,
    candidate: Candidate,
    approval: ApprovalReceipt,
    recorded_at: str,
) -> AttemptIntent:
    root = root.resolve()
    approval_binding = _file_binding(root, APPROVAL_PATH, "local-image-inventory-approval")
    if not (
        approval_binding.content_hash == approval.content_hash
        and approval.execution_hash == candidate.execution_hash
    ):
        raise FreshHarborLocalImageInventoryError("local-image approval binding differs")
    body: dict[str, Any] = {
        "schema_version": ATTEMPT_SCHEMA,
        "attempt_id": "lean-fresh-harbor-local-image-inventory-attempt-20260818-r1",
        "recorded_at": recorded_at,
        "status": "LOCAL_IMAGE_INVENTORY_ATTEMPT_RECORDED_BEFORE_CALL",
        "approval_binding": approval_binding,
        "candidate_binding": _file_binding(root, CANDIDATE_PATH, "local-image-inventory-candidate"),
        "execution_hash": candidate.execution_hash,
        "docker_cli": candidate.docker_cli,
        "command_arguments_hash": sha256_json(list(IMAGE_LS_ARGS)),
        "docker_cli_calls_before_attempt": 0,
    }
    return AttemptIntent(**body, content_hash=sha256_json(_jsonable(body)))


def _byte_evidence(value: bytes) -> ByteEvidence:
    return ByteEvidence(byte_count=len(value), sha256=sha256_bytes(value))


def _parse_inventory(raw: bytes, targets: tuple[TargetImage, ...]) -> tuple[TargetObservation, ...]:
    target_by_tag = {item.normalized_tag: item for item in targets}
    found: dict[str, tuple[str, str | None]] = {}
    for raw_line in raw.splitlines():
        if not raw_line.strip():
            continue
        value = json.loads(raw_line)
        repository = value.get("Repository")
        tag = value.get("Tag")
        if not isinstance(repository, str) or not isinstance(tag, str):
            raise FreshHarborLocalImageInventoryError("Docker image-list row is malformed")
        normalized = _normalize_ref(f"{repository}:{tag}")
        if normalized not in target_by_tag:
            continue
        image_id = value.get("ID")
        digest = value.get("Digest")
        if not isinstance(image_id, str) or not image_id:
            raise FreshHarborLocalImageInventoryError("Docker target image ID is unavailable")
        if normalized in found:
            raise FreshHarborLocalImageInventoryError("Docker target image is duplicated")
        found[normalized] = (image_id, digest if isinstance(digest, str) else None)
    observations: list[TargetObservation] = []
    for target in targets:
        matched = found.get(target.normalized_tag)
        body = {
            "task_id": target.task_id,
            "requested_ref": target.requested_ref,
            "normalized_tag": target.normalized_tag,
            "present": matched is not None,
            "image_id": matched[0] if matched else None,
            "digest": matched[1] if matched else None,
        }
        observations.append(TargetObservation(**body, content_hash=sha256_json(body)))
    return tuple(observations)


def observe(
    candidate: Candidate,
    attempt: AttemptIntent,
    recorded_at: str,
    runner: CommandRunner,
) -> Terminal:
    result = runner(IMAGE_LS_ARGS, 60)
    observations: tuple[TargetObservation, ...] = ()
    if result.returncode != 0:
        status = "LOCAL_IMAGE_INVENTORY_BLOCKED_DOCKER_COMMAND"
    else:
        try:
            observations = _parse_inventory(result.stdout, candidate.target_images)
            status = (
                "LOCAL_IMAGE_INVENTORY_COMPLETE_ALL_PRESENT"
                if all(item.present for item in observations)
                else "LOCAL_IMAGE_INVENTORY_COMPLETE_MISSING_IMAGES"
            )
        except (UnicodeDecodeError, json.JSONDecodeError, FreshHarborLocalImageInventoryError):
            status = "LOCAL_IMAGE_INVENTORY_BLOCKED_INVALID_OUTPUT"
    present = sum(item.present for item in observations)
    missing = len(observations) - present
    next_gate = {
        "LOCAL_IMAGE_INVENTORY_COMPLETE_ALL_PRESENT": (
            "implement-and-source-qualify-executor-without-running-rows"
        ),
        "LOCAL_IMAGE_INVENTORY_COMPLETE_MISSING_IMAGES": (
            "obtain-exact-pull-authority-only-for-the-identified-missing-refs"
        ),
        "LOCAL_IMAGE_INVENTORY_BLOCKED_DOCKER_COMMAND": (
            "repair-local-image-inventory-under-a-new-source-and-approval"
        ),
        "LOCAL_IMAGE_INVENTORY_BLOCKED_INVALID_OUTPUT": (
            "repair-local-image-inventory-under-a-new-source-and-approval"
        ),
    }[status]
    body: dict[str, Any] = {
        "schema_version": TERMINAL_SCHEMA,
        "terminal_id": "lean-fresh-harbor-local-image-inventory-terminal-20260818-r1",
        "recorded_at": recorded_at,
        "status": status,
        "attempt_binding": FileBinding(
            path=ATTEMPT_PATH,
            file_bytes=len(artifact_bytes(attempt)),
            file_sha256=sha256_bytes(artifact_bytes(attempt)),
            content_hash=attempt.content_hash,
            role="local-image-inventory-attempt",
        ),
        "execution_hash": candidate.execution_hash,
        "command_return_code": int(result.returncode),
        "stdout": _byte_evidence(result.stdout),
        "stderr": _byte_evidence(result.stderr),
        "target_observations": observations,
        "present_count": present,
        "missing_count": missing,
        "unrelated_local_image_records_persisted": 0,
        "raw_stdout_or_stderr_persisted": False,
        "docker_cli_calls": 1,
        "docker_daemon_read_calls": 1,
        "image_pull_build_tag_remove_prune_calls": 0,
        "container_mutations": 0,
        "network_calls": 0,
        "task_evaluator_agent_provider_calls": 0,
        "added_cost_usd": 0,
        "execution_authorized": False,
        "next_gate": next_gate,
    }
    return Terminal(**body, content_hash=sha256_json(_jsonable(body)))


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


def _write_once(root: Path, path: str, value: BaseModel, role: str) -> FileBinding:
    selected = ensure_within(root, path)
    raw = artifact_bytes(value)
    if selected.exists():
        if selected.read_bytes() != raw:
            raise FreshHarborLocalImageInventoryError(
                f"append-only inventory artifact differs: {path}"
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
        raise FreshHarborLocalImageInventoryError(f"inventory artifact is unavailable: {path}")
    raw = selected.read_bytes()
    try:
        value = model.model_validate_json(raw)
    except ValueError as exc:
        raise FreshHarborLocalImageInventoryError(f"inventory artifact is invalid: {path}") from exc
    if artifact_bytes(value) != raw:
        raise FreshHarborLocalImageInventoryError(f"inventory artifact is noncanonical: {path}")
    return value, raw


def materialize_source_qualification(root: Path) -> FileBinding:
    root = root.resolve()
    return _write_once(
        root,
        SOURCE_PATH,
        build_source_qualification(root),
        "local-image-inventory-source-qualification",
    )


def materialize_candidate(root: Path) -> FileBinding:
    root = root.resolve()
    source, source_raw = _load(root, SOURCE_PATH, SourceQualification)
    assert isinstance(source, SourceQualification)
    current = build_source_qualification(root)
    if source != current or artifact_bytes(source) != source_raw:
        raise FreshHarborLocalImageInventoryError("inventory source qualification drifted")
    return _write_once(
        root,
        CANDIDATE_PATH,
        build_candidate(root),
        "execution-closed-local-image-inventory-candidate",
    )


def load_candidate(root: Path) -> tuple[Candidate, bytes]:
    value, raw = _load(root.resolve(), CANDIDATE_PATH, Candidate)
    assert isinstance(value, Candidate)
    if value != build_candidate(root.resolve()):
        raise FreshHarborLocalImageInventoryError("local-image candidate drifted")
    return value, raw


def materialize_approval(root: Path, user_message: str) -> FileBinding:
    root = root.resolve()
    candidate, _raw = load_candidate(root)
    approval = build_approval(root, candidate, user_message, _now())
    return _write_once(root, APPROVAL_PATH, approval, "local-image-inventory-approval")


def _validate_runtime_authority(
    root: Path,
    candidate: Candidate,
    approval: ApprovalReceipt,
) -> None:
    candidate_binding = _file_binding(root, CANDIDATE_PATH, "local-image-inventory-candidate")
    if approval.candidate_binding != candidate_binding:
        raise FreshHarborLocalImageInventoryError("local-image approval candidate differs")
    if approval.execution_hash != candidate.execution_hash:
        raise FreshHarborLocalImageInventoryError("local-image approval execution differs")
    expected_message_hash = sha256_bytes(expected_approval_message(candidate).encode())
    if approval.user_message_sha256 != expected_message_hash:
        raise FreshHarborLocalImageInventoryError("local-image approval message differs")


def run_once(root: Path) -> FileBinding:
    root = root.resolve()
    terminal = ensure_within(root, TERMINAL_PATH)
    if terminal.exists():
        raise FreshHarborLocalImageInventoryError("local-image inventory is already consumed")
    attempt_path = ensure_within(root, ATTEMPT_PATH)
    if attempt_path.exists():
        raise FreshHarborLocalImageInventoryError(
            "local-image inventory attempt is already consumed or outcome is uncertain"
        )
    candidate, _candidate_raw = load_candidate(root)
    approval, _approval_raw = _load(root, APPROVAL_PATH, ApprovalReceipt)
    assert isinstance(approval, ApprovalReceipt)
    _validate_runtime_authority(root, candidate, approval)
    _validate_local_context()
    attempt = build_attempt(root, candidate, approval, _now())
    _write_once(root, ATTEMPT_PATH, attempt, "local-image-inventory-attempt")
    value = observe(candidate, attempt, _now(), _default_runner)
    return _write_once(root, TERMINAL_PATH, value, "local-image-inventory-terminal")
