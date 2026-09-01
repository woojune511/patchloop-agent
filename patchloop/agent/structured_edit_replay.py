"""Offline compatibility replay for exact structured-edit evidence.

The active gateway still accepts a raw Git patch.  This module mechanically
renders that compatibility input from an already validated structured-edit
projection and then validates observations produced by the current gateway in
a caller-attested disposable workspace.  It does not dispatch a tool, mutate a
workspace, run a check, or grant runtime authority itself.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.structured_edit import AtomicStructuredEditProjection
from patchloop.contracts import RegisteredCheck, ToolResult
from patchloop.util import sha256_bytes, sha256_json, sha256_text

STRUCTURED_EDIT_GATEWAY_PATCH_SCHEMA = "structured-edit-gateway-patch-v1"
STRUCTURED_EDIT_DIFF_CHECK_REPLAY_SCHEMA = "structured-edit-diff-check-replay-v1"
_RENDERER_POLICY = "python-difflib-git-apply-compat-v1"
_EMPTY_WORKTREE_DIFF_HASH = sha256_text("")
_PATCH_INPUT_LIMIT_BYTES = 500_000
_PATCH_SAFE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")


class StructuredEditGatewayPatch(BaseModel):
    """Mechanically rendered legacy gateway input, never model-authored."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["structured-edit-gateway-patch-v1"]
    status: Literal["offline-compatibility-input-runtime-closed"]
    renderer_policy: Literal["python-difflib-git-apply-compat-v1"]
    structured_edit: AtomicStructuredEditProjection
    structured_edit_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    patch: str = Field(min_length=1)
    patch_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    patch_bytes: int = Field(ge=1, le=_PATCH_INPUT_LIMIT_BYTES)
    changed_files: tuple[str, ...] = Field(min_length=1)
    added_lines: int = Field(ge=0)
    deleted_lines: int = Field(ge=0)
    model_authored_raw_diff_required: Literal[False]
    compatibility_patch_only: Literal[True]
    task_workspace_writes_performed: Literal[0]
    runtime_activation_authorized: Literal[False]
    provider_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        if self.structured_edit_content_hash != self.structured_edit.content_hash:
            raise ValueError("gateway patch structured-edit binding differs")
        if (
            self.source_worktree_diff_hash
            != self.structured_edit.arguments.source_worktree_diff_hash
        ):
            raise ValueError("gateway patch source worktree binding differs")
        expected_patch = _render_compatibility_patch(self.structured_edit)
        if self.patch != expected_patch:
            raise ValueError("gateway compatibility patch differs from structured images")
        patch_bytes = self.patch.encode("utf-8")
        if len(patch_bytes) != self.patch_bytes:
            raise ValueError("gateway compatibility patch byte count differs")
        if sha256_bytes(patch_bytes) != self.patch_hash:
            raise ValueError("gateway compatibility patch hash differs")
        expected_paths = tuple(sorted(item.path for item in self.structured_edit.files))
        if self.changed_files != expected_paths:
            raise ValueError("gateway compatibility changed-file set differs")
        expected_added = sum(item.added_lines for item in self.structured_edit.files)
        expected_deleted = sum(item.deleted_lines for item in self.structured_edit.files)
        if (self.added_lines, self.deleted_lines) != (
            expected_added,
            expected_deleted,
        ):
            raise ValueError("gateway compatibility line totals differ")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("gateway compatibility projection hash differs")
        return self


class StructuredGatewayApplyObservation(BaseModel):
    """Minimal successful apply result emitted by the current gateway."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    action_id: str = Field(min_length=1)
    patch_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    changed_files: tuple[str, ...] = Field(min_length=1)
    diff_lines: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        if tuple(sorted(set(self.changed_files))) != self.changed_files:
            raise ValueError("gateway apply changed files must be unique and sorted")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("gateway apply observation hash differs")
        return self


class StructuredGatewayCheckObservation(BaseModel):
    """One registered check result bound to the exact post-edit diff."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    action_id: str = Field(min_length=1)
    check: RegisteredCheck
    check_contract_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    exit_code: int
    passed: bool
    timed_out: bool
    truncated: bool
    stdout: str
    stdout_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    stderr: str
    stderr_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        if self.check_contract_hash != sha256_json(self.check.model_dump(mode="json")):
            raise ValueError("registered check contract hash differs")
        expected_passed = not self.timed_out and self.exit_code in self.check.expected_exit_codes
        if self.passed is not expected_passed:
            raise ValueError("registered check pass state differs")
        if self.stdout_hash != sha256_text(self.stdout):
            raise ValueError("registered check stdout hash differs")
        if self.stderr_hash != sha256_text(self.stderr):
            raise ValueError("registered check stderr hash differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("registered check observation hash differs")
        return self


class StructuredGatewayDiffObservation(BaseModel):
    """Exact current-worktree `get_diff` result after replay and checks."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    action_id: str = Field(min_length=1)
    patch: str = Field(min_length=1)
    patch_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    changed_files: tuple[str, ...] = Field(min_length=1)
    added_lines: int = Field(ge=0)
    deleted_lines: int = Field(ge=0)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        if tuple(sorted(set(self.changed_files))) != self.changed_files:
            raise ValueError("gateway diff changed files must be unique and sorted")
        patch_hash = sha256_text(self.patch)
        if self.patch_hash != patch_hash or self.worktree_diff_hash != patch_hash:
            raise ValueError("gateway diff patch identity differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("gateway diff observation hash differs")
        return self


class StructuredPostimageObservation(BaseModel):
    """Exact file bytes observed in the disposable workspace after replay."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str
    file_text: str
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    file_bytes: int = Field(ge=0)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        raw = self.file_text.encode("utf-8")
        if len(raw) != self.file_bytes:
            raise ValueError("observed postimage byte count differs")
        if sha256_bytes(raw) != self.file_sha256:
            raise ValueError("observed postimage hash differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("observed postimage content hash differs")
        return self


class StructuredEditDiffCheckReplay(BaseModel):
    """Self-validating offline replay of apply, registered checks and diff."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["structured-edit-diff-check-replay-v1"]
    status: Literal["offline-disposable-replay-runtime-closed"]
    gateway_tool_schema_version: Literal["v2"]
    gateway_context_policy_version: Literal["phase-evidence-v5"]
    repository_object_format: Literal["sha1"]
    gateway_patch: StructuredEditGatewayPatch
    legacy_gateway_input_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    baseline_worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    baseline_untracked_files: tuple[str, ...]
    apply: StructuredGatewayApplyObservation
    checks: tuple[StructuredGatewayCheckObservation, ...] = Field(min_length=1)
    diff: StructuredGatewayDiffObservation
    observed_postimages: tuple[StructuredPostimageObservation, ...] = Field(min_length=1)
    final_untracked_files: tuple[str, ...]
    check_count: int = Field(ge=1)
    all_checks_passed: bool
    exact_postimages_observed: Literal[True]
    exact_diff_bound: Literal[True]
    exact_registered_checks_bound: Literal[True]
    scratch_workspace_attested: Literal[True]
    git_core_autocrlf_disabled_attested: Literal[True]
    scratch_workspace_mutations_observed: Literal[1]
    production_workspace_writes_performed: Literal[0]
    model_authored_raw_diff_required: Literal[False]
    structured_action_identity_preserved: Literal[False]
    future_structured_gateway_identity_required: Literal[True]
    append_only_runtime_event_integration_deferred: Literal[True]
    provider_network_docker_calls_attested_zero: Literal[True]
    local_git_and_registered_check_processes_allowed: Literal[True]
    provider_calls_observed: Literal[0]
    network_calls_observed: Literal[0]
    docker_calls_observed: Literal[0]
    runtime_activation_authorized: Literal[False]
    provider_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        structured = self.gateway_patch.structured_edit
        expected_legacy_input = sha256_json(
            {"tool": "apply_patch", "input": {"patch": self.gateway_patch.patch}}
        )
        if self.legacy_gateway_input_hash != expected_legacy_input:
            raise ValueError("legacy gateway input hash differs")
        if self.baseline_worktree_diff_hash != structured.arguments.source_worktree_diff_hash:
            raise ValueError("replay baseline differs from structured source")
        if self.baseline_worktree_diff_hash != _EMPTY_WORKTREE_DIFF_HASH:
            raise ValueError("v1 replay requires a clean disposable baseline")
        if self.baseline_untracked_files or self.final_untracked_files:
            raise ValueError("v1 replay requires no untracked files")
        expected_paths = tuple(sorted(item.path for item in structured.files))
        if self.apply.patch_hash != self.gateway_patch.patch_hash:
            raise ValueError("gateway apply source patch hash differs")
        if self.apply.worktree_diff_hash != self.diff.worktree_diff_hash:
            raise ValueError("gateway apply and diff worktree identities differ")
        if self.apply.changed_files != expected_paths or self.diff.changed_files != expected_paths:
            raise ValueError("gateway replay changed-file set differs")
        if self.apply.diff_lines != self.diff.added_lines + self.diff.deleted_lines:
            raise ValueError("gateway replay diff line totals differ")
        if tuple(item.check.id for item in self.checks) != tuple(
            sorted(item.check.id for item in self.checks)
        ):
            raise ValueError("registered checks must be unique and sorted")
        if len({item.check.id for item in self.checks}) != len(self.checks):
            raise ValueError("registered check IDs must be unique")
        if any(item.worktree_diff_hash != self.diff.worktree_diff_hash for item in self.checks):
            raise ValueError("registered check is not bound to the final diff")
        if self.check_count != len(self.checks):
            raise ValueError("registered check count differs")
        if self.all_checks_passed is not all(item.passed for item in self.checks):
            raise ValueError("registered check aggregate differs")
        expected_postimages = tuple(
            (item.path, item.postimage_text, item.postimage_file_sha256, item.postimage_bytes)
            for item in sorted(structured.files, key=lambda value: value.path)
        )
        actual_postimages = tuple(
            (item.path, item.file_text, item.file_sha256, item.file_bytes)
            for item in self.observed_postimages
        )
        if actual_postimages != expected_postimages:
            raise ValueError("observed workspace postimages differ")
        _validate_diff_blob_bindings(self.diff.patch, structured)
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("structured diff/check replay hash differs")
        return self


def _hashed(model_type: type[BaseModel], body: dict[str, Any]) -> Any:
    return model_type.model_validate({**body, "content_hash": sha256_json(body)})


def _render_unified_file(path: str, before: str, after: str) -> str:
    if _PATCH_SAFE_PATH.fullmatch(path) is None:
        raise ValueError("gateway compatibility renderer requires an unquoted Git-safe path")
    output = [f"diff --git a/{path} b/{path}\n"]
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        n=3,
        lineterm="\n",
    )
    for line in diff:
        if line.startswith((" ", "+", "-")) and not line.endswith("\n"):
            output.extend((line + "\n", "\\ No newline at end of file\n"))
        else:
            output.append(line)
    rendered = "".join(output)
    if "@@" not in rendered:
        raise ValueError("gateway compatibility renderer produced no diff hunk")
    return rendered


def _render_compatibility_patch(
    structured_edit: AtomicStructuredEditProjection,
) -> str:
    rendered = "".join(
        _render_unified_file(item.path, item.preimage_text, item.postimage_text)
        for item in sorted(structured_edit.files, key=lambda value: value.path)
    )
    if len(rendered.encode("utf-8")) > _PATCH_INPUT_LIMIT_BYTES:
        raise ValueError("gateway compatibility patch exceeds the current input limit")
    return rendered


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _validate_diff_blob_bindings(
    patch: str,
    structured_edit: AtomicStructuredEditProjection,
) -> None:
    block_starts = [match.start() for match in re.finditer(r"(?m)^diff --git ", patch)]
    if len(block_starts) != len(structured_edit.files):
        raise ValueError("gateway diff file-block count differs")
    blocks: dict[str, str] = {}
    for index, start in enumerate(block_starts):
        end = block_starts[index + 1] if index + 1 < len(block_starts) else len(patch)
        block = patch[start:end]
        header = block.splitlines()[0]
        match = re.fullmatch(r"diff --git a/([^ ]+) b/([^ ]+)", header)
        if match is None or match.group(1) != match.group(2):
            raise ValueError("gateway diff contains an unsupported path header")
        path = match.group(1)
        if path in blocks:
            raise ValueError("gateway diff contains a duplicate file block")
        blocks[path] = block
    for item in structured_edit.files:
        block = blocks.get(item.path)
        if block is None:
            raise ValueError("gateway diff omits a structured-edit path")
        index_match = re.search(
            r"(?m)^index ([0-9a-f]{7,40})\.\.([0-9a-f]{7,40})(?: [0-7]{6})?$",
            block,
        )
        if index_match is None:
            raise ValueError("gateway diff omits its Git blob identity")
        old_blob = _git_blob_sha1(item.preimage_text.encode("utf-8"))
        new_blob = _git_blob_sha1(item.postimage_text.encode("utf-8"))
        if not old_blob.startswith(index_match.group(1)) or not new_blob.startswith(
            index_match.group(2)
        ):
            raise ValueError("gateway diff Git blob identity differs from file images")


def render_structured_edit_gateway_patch(
    structured_edit: AtomicStructuredEditProjection,
) -> StructuredEditGatewayPatch:
    """Render a legacy gateway patch without reading or writing a workspace."""

    if type(structured_edit) is not AtomicStructuredEditProjection:
        raise TypeError("gateway renderer requires the exact structured-edit projection")
    patch = _render_compatibility_patch(structured_edit)
    body: dict[str, Any] = {
        "schema_version": STRUCTURED_EDIT_GATEWAY_PATCH_SCHEMA,
        "status": "offline-compatibility-input-runtime-closed",
        "renderer_policy": _RENDERER_POLICY,
        "structured_edit": structured_edit.model_dump(mode="python"),
        "structured_edit_content_hash": structured_edit.content_hash,
        "source_worktree_diff_hash": structured_edit.arguments.source_worktree_diff_hash,
        "patch": patch,
        "patch_hash": sha256_text(patch),
        "patch_bytes": len(patch.encode("utf-8")),
        "changed_files": tuple(sorted(item.path for item in structured_edit.files)),
        "added_lines": sum(item.added_lines for item in structured_edit.files),
        "deleted_lines": sum(item.deleted_lines for item in structured_edit.files),
        "model_authored_raw_diff_required": False,
        "compatibility_patch_only": True,
        "task_workspace_writes_performed": 0,
        "runtime_activation_authorized": False,
        "provider_calls_authorized": False,
    }
    return _hashed(StructuredEditGatewayPatch, body)


def _exact_output(result: ToolResult, name: str, expected_type: type[Any]) -> Any:
    value = result.output.get(name)
    if type(value) is not expected_type:
        raise ValueError(f"gateway result {name} has the wrong exact type")
    return value


def _apply_observation(result: ToolResult) -> StructuredGatewayApplyObservation:
    if type(result) is not ToolResult or result.status != "succeeded":
        raise ValueError("gateway apply replay requires an exact successful ToolResult")
    changed_files = _exact_output(result, "changed_files", list)
    if any(type(item) is not str for item in changed_files):
        raise ValueError("gateway apply changed files have the wrong exact type")
    body = {
        "action_id": result.action_id,
        "patch_hash": _exact_output(result, "patch_hash", str),
        "worktree_diff_hash": _exact_output(result, "worktree_diff_hash", str),
        "changed_files": tuple(changed_files),
        "diff_lines": _exact_output(result, "diff_lines", int),
    }
    return _hashed(StructuredGatewayApplyObservation, body)


def _check_observation(
    check: RegisteredCheck,
    result: ToolResult,
) -> StructuredGatewayCheckObservation:
    if type(check) is not RegisteredCheck:
        raise TypeError("replay checks must use exact RegisteredCheck contracts")
    if type(result) is not ToolResult or result.status != "succeeded":
        raise ValueError("registered check replay requires an exact successful ToolResult")
    if _exact_output(result, "check_id", str) != check.id:
        raise ValueError("registered check result ID differs")
    stdout = _exact_output(result, "stdout", str)
    stderr = _exact_output(result, "stderr", str)
    body = {
        "action_id": result.action_id,
        "check": check.model_dump(mode="python"),
        "check_contract_hash": sha256_json(check.model_dump(mode="json")),
        "exit_code": _exact_output(result, "exit_code", int),
        "passed": _exact_output(result, "passed", bool),
        "timed_out": _exact_output(result, "timed_out", bool),
        "truncated": _exact_output(result, "truncated", bool),
        "stdout": stdout,
        "stdout_hash": sha256_text(stdout),
        "stderr": stderr,
        "stderr_hash": sha256_text(stderr),
        "worktree_diff_hash": _exact_output(result, "worktree_diff_hash", str),
    }
    return _hashed(StructuredGatewayCheckObservation, body)


def _diff_observation(result: ToolResult) -> StructuredGatewayDiffObservation:
    if type(result) is not ToolResult or result.status != "succeeded":
        raise ValueError("gateway diff replay requires an exact successful ToolResult")
    changed_files = _exact_output(result, "changed_files", list)
    if any(type(item) is not str for item in changed_files):
        raise ValueError("gateway diff changed files have the wrong exact type")
    body = {
        "action_id": result.action_id,
        "patch": _exact_output(result, "patch", str),
        "patch_hash": _exact_output(result, "patch_hash", str),
        "worktree_diff_hash": _exact_output(result, "worktree_diff_hash", str),
        "changed_files": tuple(changed_files),
        "added_lines": _exact_output(result, "added_lines", int),
        "deleted_lines": _exact_output(result, "deleted_lines", int),
    }
    return _hashed(StructuredGatewayDiffObservation, body)


def _postimage_observations(
    structured_edit: AtomicStructuredEditProjection,
    observed_postimages: dict[str, bytes],
) -> tuple[StructuredPostimageObservation, ...]:
    expected_paths = {item.path for item in structured_edit.files}
    if type(observed_postimages) is not dict or set(observed_postimages) != expected_paths:
        raise ValueError("observed postimages must exactly match structured paths")
    observations: list[StructuredPostimageObservation] = []
    for path in sorted(expected_paths):
        raw = observed_postimages[path]
        if type(path) is not str or type(raw) is not bytes:
            raise ValueError("observed postimages require exact path and byte values")
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError("observed postimage is not UTF-8 text") from exc
        body = {
            "path": path,
            "file_text": text,
            "file_sha256": sha256_bytes(raw),
            "file_bytes": len(raw),
        }
        observations.append(_hashed(StructuredPostimageObservation, body))
    return tuple(observations)


def project_structured_edit_diff_check_replay(
    *,
    gateway_patch: StructuredEditGatewayPatch,
    apply_result: ToolResult,
    registered_checks: tuple[RegisteredCheck, ...],
    check_results: tuple[ToolResult, ...],
    diff_result: ToolResult,
    observed_postimages: dict[str, bytes],
    baseline_worktree_diff_hash: str,
    baseline_untracked_files: tuple[str, ...],
    final_untracked_files: tuple[str, ...],
    scratch_workspace_attested: bool,
    git_core_autocrlf_disabled_attested: bool,
    provider_network_docker_calls_attested_zero: bool,
) -> StructuredEditDiffCheckReplay:
    """Bind one disposable current-gateway replay without dispatching it."""

    if type(gateway_patch) is not StructuredEditGatewayPatch:
        raise TypeError("replay requires the exact gateway patch projection")
    if type(registered_checks) is not tuple or type(check_results) is not tuple:
        raise TypeError("replay check contracts and results must be exact tuples")
    if not registered_checks or len(registered_checks) != len(check_results):
        raise ValueError("replay requires one exact result per registered check")
    if type(baseline_worktree_diff_hash) is not str:
        raise TypeError("replay baseline hash must be an exact string")
    for value, name in (
        (baseline_untracked_files, "baseline untracked files"),
        (final_untracked_files, "final untracked files"),
    ):
        if type(value) is not tuple or any(type(item) is not str for item in value):
            raise TypeError(f"{name} must be an exact string tuple")
    if scratch_workspace_attested is not True:
        raise ValueError("replay requires disposable scratch-workspace attestation")
    if git_core_autocrlf_disabled_attested is not True:
        raise ValueError("replay requires core.autocrlf=false attestation")
    if provider_network_docker_calls_attested_zero is not True:
        raise ValueError("replay requires zero provider/network/Docker attestation")

    apply = _apply_observation(apply_result)
    checks = tuple(
        _check_observation(check, result)
        for check, result in zip(registered_checks, check_results, strict=True)
    )
    diff = _diff_observation(diff_result)
    postimages = _postimage_observations(
        gateway_patch.structured_edit,
        observed_postimages,
    )
    body: dict[str, Any] = {
        "schema_version": STRUCTURED_EDIT_DIFF_CHECK_REPLAY_SCHEMA,
        "status": "offline-disposable-replay-runtime-closed",
        "gateway_tool_schema_version": "v2",
        "gateway_context_policy_version": "phase-evidence-v5",
        "repository_object_format": "sha1",
        "gateway_patch": gateway_patch.model_dump(mode="python"),
        "legacy_gateway_input_hash": sha256_json(
            {"tool": "apply_patch", "input": {"patch": gateway_patch.patch}}
        ),
        "baseline_worktree_diff_hash": baseline_worktree_diff_hash,
        "baseline_untracked_files": baseline_untracked_files,
        "apply": apply.model_dump(mode="python"),
        "checks": tuple(item.model_dump(mode="python") for item in checks),
        "diff": diff.model_dump(mode="python"),
        "observed_postimages": tuple(item.model_dump(mode="python") for item in postimages),
        "final_untracked_files": final_untracked_files,
        "check_count": len(checks),
        "all_checks_passed": all(item.passed for item in checks),
        "exact_postimages_observed": True,
        "exact_diff_bound": True,
        "exact_registered_checks_bound": True,
        "scratch_workspace_attested": True,
        "git_core_autocrlf_disabled_attested": True,
        "scratch_workspace_mutations_observed": 1,
        "production_workspace_writes_performed": 0,
        "model_authored_raw_diff_required": False,
        "structured_action_identity_preserved": False,
        "future_structured_gateway_identity_required": True,
        "append_only_runtime_event_integration_deferred": True,
        "provider_network_docker_calls_attested_zero": True,
        "local_git_and_registered_check_processes_allowed": True,
        "provider_calls_observed": 0,
        "network_calls_observed": 0,
        "docker_calls_observed": 0,
        "runtime_activation_authorized": False,
        "provider_calls_authorized": False,
    }
    return _hashed(StructuredEditDiffCheckReplay, body)
