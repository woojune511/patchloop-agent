"""Pure offline contract for exact, atomic structured text edits.

The current gateway already persists preimages/postimages and recovers atomic
multi-file mutations.  This module replaces only the error-prone model-facing
raw-diff construction step with exact UTF-8 byte-span replacements.  It reads
or writes no files and is not part of any active tool surface.
"""

from __future__ import annotations

import difflib
import fnmatch
from pathlib import PurePosixPath
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.contracts import TaskConstraints
from patchloop.errors import ContractError
from patchloop.util import safe_relative_path, sha256_bytes, sha256_json

STRUCTURED_EDIT_TOOL_NAME = "apply_structured_edit"
STRUCTURED_EDIT_ARGUMENTS_SCHEMA = "structured-edit-arguments-v1"
STRUCTURED_EDIT_PROJECTION_SCHEMA = "structured-edit-projection-v1"
FRESH_STRUCTURED_EDIT_ARGUMENTS_SCHEMA = "structured-edit-arguments-v2"
FRESH_STRUCTURED_EDIT_PROJECTION_SCHEMA = "fresh-structured-edit-projection-v1"

STRUCTURED_EDIT_TOOL_SCHEMA_V1: dict[str, Any] = {
    "type": "function",
    "name": STRUCTURED_EDIT_TOOL_NAME,
    "description": (
        "Prepare exact replacements against existing tracked UTF-8 files. "
        "Every file binds its raw preimage SHA-256 and every replacement binds "
        "a non-overlapping UTF-8 byte span plus its exact current text."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "schema_version": {
                "type": "string",
                "enum": [STRUCTURED_EDIT_ARGUMENTS_SCHEMA],
            },
            "source_worktree_diff_hash": {
                "type": "string",
                "pattern": "^sha256:[0-9a-f]{64}$",
            },
            "files": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "minLength": 1},
                        "preimage_file_sha256": {
                            "type": "string",
                            "pattern": "^sha256:[0-9a-f]{64}$",
                        },
                        "replacements": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "start_byte": {"type": "integer", "minimum": 0},
                                    "end_byte": {"type": "integer", "minimum": 1},
                                    "expected_text": {"type": "string", "minLength": 1},
                                    "replacement_text": {"type": "string"},
                                },
                                "required": [
                                    "start_byte",
                                    "end_byte",
                                    "expected_text",
                                    "replacement_text",
                                ],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": [
                        "path",
                        "preimage_file_sha256",
                        "replacements",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["schema_version", "source_worktree_diff_hash", "files"],
        "additionalProperties": False,
    },
    "strict": True,
}

STRUCTURED_EDIT_TOOL_SCHEMA_V2: dict[str, Any] = {
    "type": "function",
    "name": STRUCTURED_EDIT_TOOL_NAME,
    "description": (
        "Apply exact text replacements to existing tracked UTF-8 files. "
        "Provide a unique current expected_text and its replacement; the gateway "
        "refreshes the exact file bytes, SHA-256, worktree diff, and UTF-8 byte "
        "offsets immediately before the atomic mutation. Do not provide hashes "
        "or byte offsets. If expected_text is missing or ambiguous, narrow it "
        "with more current surrounding text."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "schema_version": {
                "type": "string",
                "enum": [FRESH_STRUCTURED_EDIT_ARGUMENTS_SCHEMA],
            },
            "files": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "minLength": 1},
                        "replacements": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "expected_text": {
                                        "type": "string",
                                        "minLength": 1,
                                    },
                                    "replacement_text": {"type": "string"},
                                },
                                "required": [
                                    "expected_text",
                                    "replacement_text",
                                ],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["path", "replacements"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["schema_version", "files"],
        "additionalProperties": False,
    },
    "strict": True,
}


class StructuredReplacement(BaseModel):
    """One exact UTF-8 byte span in the bound raw preimage."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    start_byte: int = Field(ge=0)
    end_byte: int = Field(ge=1)
    expected_text: str = Field(min_length=1)
    replacement_text: str

    @model_validator(mode="after")
    def validate_replacement(self) -> Self:
        if self.end_byte <= self.start_byte:
            raise ValueError("structured replacement span must be nonempty")
        if self.expected_text == self.replacement_text:
            raise ValueError("structured replacement must change its exact span")
        if "\x00" in self.expected_text or "\x00" in self.replacement_text:
            raise ValueError("structured replacement requires UTF-8 text without NUL")
        return self


class StructuredFileEdit(BaseModel):
    """All replacements for one exact existing file preimage."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    preimage_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    replacements: tuple[StructuredReplacement, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_file_edit(self) -> Self:
        try:
            normalized = safe_relative_path(
                self.path,
                field_name="structured edit path",
            )
        except ContractError as exc:
            raise ValueError(str(exc)) from exc
        if normalized != self.path:
            raise ValueError("structured edit path must already be normalized")
        ordered = tuple((item.start_byte, item.end_byte) for item in self.replacements)
        if ordered != tuple(sorted(ordered)):
            raise ValueError("structured replacement spans must be ordered")
        for previous, current in zip(
            self.replacements,
            self.replacements[1:],
            strict=False,
        ):
            if current.start_byte < previous.end_byte:
                raise ValueError("structured replacement spans must not overlap")
        return self


class StructuredEditArguments(BaseModel):
    """Future model-facing arguments; action identity remains gateway-owned."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["structured-edit-arguments-v1"] = STRUCTURED_EDIT_ARGUMENTS_SCHEMA
    source_worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    files: tuple[StructuredFileEdit, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_arguments(self) -> Self:
        paths = tuple(item.path for item in self.files)
        if len(set(paths)) != len(paths):
            raise ValueError("structured edit paths must be unique")
        return self


class FreshStructuredReplacement(BaseModel):
    """One model-facing replacement resolved against a fresh gateway preimage."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    expected_text: str = Field(min_length=1)
    replacement_text: str

    @model_validator(mode="after")
    def validate_replacement(self) -> Self:
        if self.expected_text == self.replacement_text:
            raise ValueError("fresh structured replacement must change its exact text")
        if "\x00" in self.expected_text or "\x00" in self.replacement_text:
            raise ValueError("fresh structured replacement requires text without NUL")
        return self


class FreshStructuredFileEdit(BaseModel):
    """Hash-free edit intent for one existing tracked text file."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    replacements: tuple[FreshStructuredReplacement, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_file_edit(self) -> Self:
        try:
            normalized = safe_relative_path(
                self.path,
                field_name="fresh structured edit path",
            )
        except ContractError as exc:
            raise ValueError(str(exc)) from exc
        if normalized != self.path:
            raise ValueError("fresh structured edit path must already be normalized")
        return self


class FreshStructuredEditArguments(BaseModel):
    """Successor input whose volatile bindings are supplied only by the gateway."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["structured-edit-arguments-v2"] = FRESH_STRUCTURED_EDIT_ARGUMENTS_SCHEMA
    files: tuple[FreshStructuredFileEdit, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_arguments(self) -> Self:
        paths = tuple(item.path for item in self.files)
        if len(set(paths)) != len(paths):
            raise ValueError("fresh structured edit paths must be unique")
        return self


class StructuredEditConstraintProjection(BaseModel):
    """Frozen subset of public task scope needed by the offline projection."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    allowed_paths: tuple[str, ...] = Field(min_length=1)
    forbidden_paths: tuple[str, ...]
    max_changed_files: int = Field(ge=1)
    max_diff_lines: int = Field(ge=1)
    dependency_changes_allowed: bool
    public_api_changes_allowed: bool
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_constraints(self) -> Self:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("structured edit constraint hash differs")
        return self


class StructuredFileProjection(BaseModel):
    """Exact reversible preimage/postimage pair built without a workspace write."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str
    preimage_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    preimage_bytes: int = Field(ge=1)
    preimage_text: str
    postimage_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    postimage_bytes: int = Field(ge=0)
    postimage_text: str
    replacements: tuple[StructuredReplacement, ...]
    replacement_count: int = Field(ge=1)
    added_lines: int = Field(ge=0)
    deleted_lines: int = Field(ge=0)
    logical_diff_lines: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        preimage = self.preimage_text.encode("utf-8")
        postimage = self.postimage_text.encode("utf-8")
        if len(preimage) != self.preimage_bytes:
            raise ValueError("structured edit preimage byte count differs")
        if sha256_bytes(preimage) != self.preimage_file_sha256:
            raise ValueError("structured edit preimage hash differs")
        if len(postimage) != self.postimage_bytes:
            raise ValueError("structured edit postimage byte count differs")
        if sha256_bytes(postimage) != self.postimage_file_sha256:
            raise ValueError("structured edit postimage hash differs")
        expected_postimage = _apply_exact_replacements(
            preimage,
            self.replacements,
        )
        if expected_postimage != postimage:
            raise ValueError("structured edit postimage differs from replacements")
        if self.replacement_count != len(self.replacements):
            raise ValueError("structured edit replacement count differs")
        added, deleted = _logical_line_delta(self.preimage_text, self.postimage_text)
        if (self.added_lines, self.deleted_lines) != (added, deleted):
            raise ValueError("structured edit line delta differs")
        if self.logical_diff_lines != added + deleted:
            raise ValueError("structured edit logical diff total differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("structured file projection hash differs")
        return self


class AtomicStructuredEditProjection(BaseModel):
    """Prepared all-or-nothing edit evidence with every runtime authority false."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["structured-edit-projection-v1"]
    status: Literal["offline-projection-runtime-closed"]
    tool_name: Literal["apply_structured_edit"]
    action_id: str = Field(min_length=1, max_length=200)
    arguments: StructuredEditArguments
    arguments_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    input_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    action_identity_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    constraints: StructuredEditConstraintProjection
    files: tuple[StructuredFileProjection, ...]
    preimage_set_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    postimage_set_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    changed_file_count: int = Field(ge=1)
    replacement_count: int = Field(ge=1)
    added_lines: int = Field(ge=0)
    deleted_lines: int = Field(ge=0)
    logical_diff_lines: int = Field(ge=1)
    all_preimages_validated: Literal[True]
    atomic_commit_required: Literal[True]
    rollback_preimages_bound: Literal[True]
    tracked_path_validation_deferred: Literal[True]
    downstream_git_policy_revalidation_required: Literal[True]
    raw_diff_generation_required: Literal[False]
    workspace_writes_performed: Literal[0]
    runtime_activation_authorized: Literal[False]
    state_mutation_authorized: Literal[False]
    provider_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        arguments_body = self.arguments.model_dump(mode="json")
        if self.arguments_hash != sha256_json(arguments_body):
            raise ValueError("structured edit arguments hash differs")
        expected_input_hash = sha256_json({"tool": self.tool_name, "input": arguments_body})
        if self.input_hash != expected_input_hash:
            raise ValueError("structured edit input hash differs")
        if self.action_identity_hash != sha256_json(
            {"action_id": self.action_id, "input_hash": self.input_hash}
        ):
            raise ValueError("structured edit action identity differs")
        if tuple(item.path for item in self.arguments.files) != tuple(
            item.path for item in self.files
        ):
            raise ValueError("structured edit file order differs")
        for requested, projected in zip(
            self.arguments.files,
            self.files,
            strict=True,
        ):
            if (
                requested.path != projected.path
                or requested.preimage_file_sha256 != projected.preimage_file_sha256
                or requested.replacements != projected.replacements
            ):
                raise ValueError("structured edit file request differs")
        if self.preimage_set_hash != _image_set_hash(self.files, preimage=True):
            raise ValueError("structured edit preimage set hash differs")
        if self.postimage_set_hash != _image_set_hash(self.files, preimage=False):
            raise ValueError("structured edit postimage set hash differs")
        if self.changed_file_count != len(self.files):
            raise ValueError("structured edit changed file count differs")
        if self.replacement_count != sum(item.replacement_count for item in self.files):
            raise ValueError("structured edit replacement total differs")
        added = sum(item.added_lines for item in self.files)
        deleted = sum(item.deleted_lines for item in self.files)
        if (self.added_lines, self.deleted_lines) != (added, deleted):
            raise ValueError("structured edit line totals differ")
        if self.logical_diff_lines != added + deleted:
            raise ValueError("structured edit logical diff total differs")
        if self.changed_file_count > self.constraints.max_changed_files:
            raise ValueError("structured edit exceeds changed-file limit")
        if self.logical_diff_lines > self.constraints.max_diff_lines:
            raise ValueError("structured edit exceeds logical diff limit")
        for item in self.files:
            _validate_path_scope(item.path, self.constraints)
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("structured edit projection content hash differs")
        return self


class FreshStructuredEditProjection(BaseModel):
    """Gateway-refreshed bindings plus the existing atomic edit projection."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["fresh-structured-edit-projection-v1"]
    policy_version: Literal["gateway-fresh-preimage-unique-text-v1"]
    action_id: str = Field(min_length=1, max_length=200)
    requested_arguments: FreshStructuredEditArguments
    requested_arguments_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    refreshed_file_hashes: dict[str, str]
    derived_arguments: StructuredEditArguments
    derived_arguments_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    atomic_projection: AtomicStructuredEditProjection
    atomic_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    preimages_read_at_gateway_dispatch: Literal[True]
    model_supplied_preimage_hashes: Literal[False]
    model_supplied_byte_offsets: Literal[False]
    unique_current_text_required: Literal[True]
    crlf_transport_normalized_to_current_file: Literal[True]
    workspace_writes_performed: Literal[0]
    provider_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        requested_body = self.requested_arguments.model_dump(mode="json")
        if self.requested_arguments_hash != sha256_json(requested_body):
            raise ValueError("fresh structured requested-arguments hash differs")
        if self.derived_arguments_hash != sha256_json(
            self.derived_arguments.model_dump(mode="json")
        ):
            raise ValueError("fresh structured derived-arguments hash differs")
        if self.atomic_projection_hash != self.atomic_projection.content_hash:
            raise ValueError("fresh structured atomic projection hash differs")
        if self.atomic_projection.action_id != self.action_id:
            raise ValueError("fresh structured action identity differs")
        if self.atomic_projection.arguments != self.derived_arguments:
            raise ValueError("fresh structured atomic arguments differ")
        if (
            self.atomic_projection.arguments.source_worktree_diff_hash
            != self.source_worktree_diff_hash
        ):
            raise ValueError("fresh structured source worktree hash differs")
        expected_hashes = {
            item.path: item.preimage_file_sha256 for item in self.atomic_projection.files
        }
        if self.refreshed_file_hashes != expected_hashes:
            raise ValueError("fresh structured refreshed file hashes differ")
        requested_paths = tuple(item.path for item in self.requested_arguments.files)
        if requested_paths != tuple(item.path for item in self.derived_arguments.files):
            raise ValueError("fresh structured path order differs")
        for requested, derived, projected in zip(
            self.requested_arguments.files,
            self.derived_arguments.files,
            self.atomic_projection.files,
            strict=True,
        ):
            raw = projected.preimage_text.encode("utf-8")
            expected_replacements = tuple(
                sorted(
                    (
                        _unique_current_span(
                            raw,
                            item.expected_text,
                            item.replacement_text,
                        )
                        for item in requested.replacements
                    ),
                    key=lambda item: (item.start_byte, item.end_byte),
                )
            )
            if derived.replacements != expected_replacements:
                raise ValueError("fresh structured derived replacements differ")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("fresh structured projection content hash differs")
        return self


def _build_hashed(model_type: type[BaseModel], body: dict[str, Any]) -> Any:
    return model_type.model_validate({**body, "content_hash": sha256_json(body)})


def _matches(path: str, pattern: str) -> bool:
    if pattern == "**":
        return True
    return fnmatch.fnmatchcase(path, pattern) or PurePosixPath(path).match(pattern)


def _validate_path_scope(
    path: str,
    constraints: StructuredEditConstraintProjection,
) -> None:
    if not any(_matches(path, pattern) for pattern in constraints.allowed_paths):
        raise ValueError(f"structured edit path is outside allowed paths: {path}")
    if any(_matches(path, pattern) for pattern in constraints.forbidden_paths):
        raise ValueError(f"structured edit path is forbidden: {path}")


def _apply_exact_replacements(
    preimage: bytes,
    replacements: tuple[StructuredReplacement, ...],
) -> bytes:
    cursor = 0
    output = bytearray()
    for item in replacements:
        if item.end_byte > len(preimage):
            raise ValueError("structured replacement span exceeds its preimage")
        expected = item.expected_text.encode("utf-8")
        if preimage[item.start_byte : item.end_byte] != expected:
            raise ValueError("structured replacement text differs from its byte span")
        output.extend(preimage[cursor : item.start_byte])
        output.extend(item.replacement_text.encode("utf-8"))
        cursor = item.end_byte
    output.extend(preimage[cursor:])
    return bytes(output)


def _logical_line_delta(before: str, after: str) -> tuple[int, int]:
    matcher = difflib.SequenceMatcher(
        a=before.splitlines(),
        b=after.splitlines(),
        autojunk=False,
    )
    added = 0
    deleted = 0
    for operation, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if operation in {"replace", "delete"}:
            deleted += old_end - old_start
        if operation in {"replace", "insert"}:
            added += new_end - new_start
    return added, deleted


def _image_set_hash(
    files: tuple[StructuredFileProjection, ...],
    *,
    preimage: bool,
) -> str:
    key = "preimage_file_sha256" if preimage else "postimage_file_sha256"
    byte_key = "preimage_bytes" if preimage else "postimage_bytes"
    return sha256_json(
        [
            {
                "path": item.path,
                "file_sha256": getattr(item, key),
                "file_bytes": getattr(item, byte_key),
            }
            for item in files
        ]
    )


def _constraint_projection(
    constraints: TaskConstraints,
) -> StructuredEditConstraintProjection:
    body: dict[str, Any] = {
        "allowed_paths": tuple(constraints.allowed_paths),
        "forbidden_paths": tuple(constraints.forbidden_paths),
        "max_changed_files": constraints.max_changed_files,
        "max_diff_lines": constraints.max_diff_lines,
        "dependency_changes_allowed": constraints.dependency_changes_allowed,
        "public_api_changes_allowed": constraints.public_api_changes_allowed,
    }
    return _build_hashed(StructuredEditConstraintProjection, body)


def project_atomic_structured_edit(
    *,
    action_id: str,
    arguments: StructuredEditArguments,
    preimages: dict[str, bytes],
    constraints: TaskConstraints,
) -> AtomicStructuredEditProjection:
    """Validate every preimage/span and build all postimages without writing."""

    if type(action_id) is not str or not action_id or len(action_id) > 200:
        raise TypeError("structured edit action_id must be a nonempty exact string")
    if type(arguments) is not StructuredEditArguments:
        raise TypeError("structured edit arguments must use the exact contract")
    if type(preimages) is not dict:
        raise TypeError("structured edit preimages must be an exact mapping")
    if type(constraints) is not TaskConstraints:
        raise TypeError("structured edit constraints must be exact TaskConstraints")
    requested_paths = tuple(item.path for item in arguments.files)
    if set(preimages) != set(requested_paths) or any(
        type(path) is not str or type(raw) is not bytes for path, raw in preimages.items()
    ):
        raise ValueError("structured edit preimages must exactly match requested paths")

    projected_constraints = _constraint_projection(constraints)
    if len(requested_paths) > projected_constraints.max_changed_files:
        raise ValueError("structured edit exceeds changed-file limit")
    files: list[StructuredFileProjection] = []
    for requested in arguments.files:
        _validate_path_scope(requested.path, projected_constraints)
        preimage = preimages[requested.path]
        if not preimage or b"\x00" in preimage:
            raise ValueError("structured edit requires nonempty UTF-8 text preimages")
        try:
            preimage_text = preimage.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError("structured edit preimage is not UTF-8 text") from exc
        if sha256_bytes(preimage) != requested.preimage_file_sha256:
            raise ValueError("structured edit preimage file hash differs")
        postimage = _apply_exact_replacements(preimage, requested.replacements)
        if postimage == preimage:
            raise ValueError("structured edit file has no net effect")
        postimage_text = postimage.decode("utf-8", errors="strict")
        added, deleted = _logical_line_delta(preimage_text, postimage_text)
        file_body: dict[str, Any] = {
            "path": requested.path,
            "preimage_file_sha256": requested.preimage_file_sha256,
            "preimage_bytes": len(preimage),
            "preimage_text": preimage_text,
            "postimage_file_sha256": sha256_bytes(postimage),
            "postimage_bytes": len(postimage),
            "postimage_text": postimage_text,
            "replacements": tuple(
                item.model_dump(mode="python") for item in requested.replacements
            ),
            "replacement_count": len(requested.replacements),
            "added_lines": added,
            "deleted_lines": deleted,
            "logical_diff_lines": added + deleted,
        }
        files.append(_build_hashed(StructuredFileProjection, file_body))
    file_tuple = tuple(files)
    logical_diff_lines = sum(item.logical_diff_lines for item in file_tuple)
    if logical_diff_lines > projected_constraints.max_diff_lines:
        raise ValueError("structured edit exceeds logical diff limit")
    arguments_body = arguments.model_dump(mode="json")
    input_hash = sha256_json({"tool": STRUCTURED_EDIT_TOOL_NAME, "input": arguments_body})
    body: dict[str, Any] = {
        "schema_version": STRUCTURED_EDIT_PROJECTION_SCHEMA,
        "status": "offline-projection-runtime-closed",
        "tool_name": STRUCTURED_EDIT_TOOL_NAME,
        "action_id": action_id,
        "arguments": arguments.model_dump(mode="python"),
        "arguments_hash": sha256_json(arguments_body),
        "input_hash": input_hash,
        "action_identity_hash": sha256_json({"action_id": action_id, "input_hash": input_hash}),
        "constraints": projected_constraints.model_dump(mode="python"),
        "files": tuple(item.model_dump(mode="python") for item in file_tuple),
        "preimage_set_hash": _image_set_hash(file_tuple, preimage=True),
        "postimage_set_hash": _image_set_hash(file_tuple, preimage=False),
        "changed_file_count": len(file_tuple),
        "replacement_count": sum(item.replacement_count for item in file_tuple),
        "added_lines": sum(item.added_lines for item in file_tuple),
        "deleted_lines": sum(item.deleted_lines for item in file_tuple),
        "logical_diff_lines": logical_diff_lines,
        "all_preimages_validated": True,
        "atomic_commit_required": True,
        "rollback_preimages_bound": True,
        "tracked_path_validation_deferred": True,
        "downstream_git_policy_revalidation_required": True,
        "raw_diff_generation_required": False,
        "workspace_writes_performed": 0,
        "runtime_activation_authorized": False,
        "state_mutation_authorized": False,
        "provider_calls_authorized": False,
    }
    return _build_hashed(AtomicStructuredEditProjection, body)


def _unique_current_span(
    preimage: bytes,
    expected_text: str,
    replacement_text: str,
) -> StructuredReplacement:
    """Resolve one unique model-visible text span against exact current bytes."""

    candidates: list[tuple[bytes, str, str]] = [
        (expected_text.encode("utf-8"), expected_text, replacement_text)
    ]
    if "\n" in expected_text and "\r" not in expected_text:
        crlf_expected = expected_text.replace("\n", "\r\n")
        crlf_replacement = replacement_text.replace("\r\n", "\n").replace("\n", "\r\n")
        candidates.append(
            (
                crlf_expected.encode("utf-8"),
                crlf_expected,
                crlf_replacement,
            )
        )

    matches: list[tuple[int, bytes, str, str]] = []
    for needle, resolved_expected, resolved_replacement in candidates:
        cursor = 0
        while True:
            start = preimage.find(needle, cursor)
            if start < 0:
                break
            matches.append((start, needle, resolved_expected, resolved_replacement))
            cursor = start + 1
    unique_positions = {(start, len(needle)) for start, needle, _, _ in matches}
    if not unique_positions:
        raise ValueError("fresh structured expected text is absent from the current preimage")
    if len(unique_positions) != 1:
        raise ValueError("fresh structured expected text is ambiguous in the current preimage")
    start, needle, resolved_expected, resolved_replacement = matches[0]
    return StructuredReplacement(
        start_byte=start,
        end_byte=start + len(needle),
        expected_text=resolved_expected,
        replacement_text=resolved_replacement,
    )


def project_fresh_atomic_structured_edit(
    *,
    action_id: str,
    arguments: FreshStructuredEditArguments,
    source_worktree_diff_hash: str,
    preimages: dict[str, bytes],
    constraints: TaskConstraints,
) -> FreshStructuredEditProjection:
    """Bind hash-free text intent to exact current preimages without writing."""

    if type(arguments) is not FreshStructuredEditArguments:
        raise TypeError("fresh structured edit arguments must use the exact contract")
    if (
        type(source_worktree_diff_hash) is not str
        or not source_worktree_diff_hash.startswith("sha256:")
        or len(source_worktree_diff_hash) != 71
    ):
        raise TypeError("fresh structured edit source diff hash is invalid")
    requested_paths = tuple(item.path for item in arguments.files)
    if type(preimages) is not dict or set(preimages) != set(requested_paths):
        raise ValueError("fresh structured preimages must exactly match requested paths")

    derived_files: list[StructuredFileEdit] = []
    for requested in arguments.files:
        raw = preimages.get(requested.path)
        if type(raw) is not bytes or not raw or b"\x00" in raw:
            raise ValueError("fresh structured edit requires nonempty UTF-8 preimages")
        try:
            raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError("fresh structured edit preimage is not UTF-8 text") from exc
        replacements = tuple(
            sorted(
                (
                    _unique_current_span(
                        raw,
                        item.expected_text,
                        item.replacement_text,
                    )
                    for item in requested.replacements
                ),
                key=lambda item: (item.start_byte, item.end_byte),
            )
        )
        for previous, current in zip(
            replacements,
            replacements[1:],
            strict=False,
        ):
            if current.start_byte < previous.end_byte:
                raise ValueError("fresh structured replacement spans overlap")
        derived_files.append(
            StructuredFileEdit(
                path=requested.path,
                preimage_file_sha256=sha256_bytes(raw),
                replacements=replacements,
            )
        )
    derived = StructuredEditArguments(
        source_worktree_diff_hash=source_worktree_diff_hash,
        files=tuple(derived_files),
    )
    atomic = project_atomic_structured_edit(
        action_id=action_id,
        arguments=derived,
        preimages=preimages,
        constraints=constraints,
    )
    requested_body = arguments.model_dump(mode="json")
    body: dict[str, Any] = {
        "schema_version": FRESH_STRUCTURED_EDIT_PROJECTION_SCHEMA,
        "policy_version": "gateway-fresh-preimage-unique-text-v1",
        "action_id": action_id,
        "requested_arguments": arguments.model_dump(mode="python"),
        "requested_arguments_hash": sha256_json(requested_body),
        "source_worktree_diff_hash": source_worktree_diff_hash,
        "refreshed_file_hashes": {path: sha256_bytes(raw) for path, raw in preimages.items()},
        "derived_arguments": derived.model_dump(mode="python"),
        "derived_arguments_hash": sha256_json(derived.model_dump(mode="json")),
        "atomic_projection": atomic.model_dump(mode="python"),
        "atomic_projection_hash": atomic.content_hash,
        "preimages_read_at_gateway_dispatch": True,
        "model_supplied_preimage_hashes": False,
        "model_supplied_byte_offsets": False,
        "unique_current_text_required": True,
        "crlf_transport_normalized_to_current_file": True,
        "workspace_writes_performed": 0,
        "provider_calls_authorized": False,
    }
    return _build_hashed(FreshStructuredEditProjection, body)
