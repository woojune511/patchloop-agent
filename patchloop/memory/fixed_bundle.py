"""Exact, query-independent D-110 structured-memory bundle delivery."""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import Field, model_validator

from patchloop.contracts import MemoryCondition, StrictModel
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes, sha256_text

FIXED_BUNDLE_POLICY_VERSION = "fixed-d110-bundle-v1"
FIXED_BUNDLE_MODE = "fixed-approved-three-entry-bundle"
FIXED_BUNDLE_TOKEN_BUDGET = 2_000
FIXED_BUNDLE_SEPARATOR = "\n\n---\n\n"
FIXED_BUNDLE_BYTES = 3_528
FIXED_BUNDLE_SHA256 = "sha256:572667d431aa75e4fe74bfc030a99f64245b77d9afa1c88e5d531129f708accf"

D105_GATE_PATH = "reports/memory-development/d105-renderer-embedding-index-authorization-gate.json"
D105_GATE_ID = "d105_0f99c7d1cd1c371191073ead8d60636be9ea6040947d9c7f3522aba25bc3df70"
D105_GATE_BODY_SHA256 = "sha256:0f99c7d1cd1c371191073ead8d60636be9ea6040947d9c7f3522aba25bc3df70"
D105_GATE_BYTES = 12_368
D105_GATE_FILE_SHA256 = "sha256:db6303f3de834b3c36493f2863dcc5be3ca697490d18df15c86a18e7ee7b17eb"
D105_RENDER_SET_SHA256 = "sha256:7b72fc94642d996fad5a0b199719c56bfecc8a8fc1bbe42b2060aa18e21d2667"

D110_INDEX_VERSION = "idxgrp_563976c4443a725e287225cef1e718daf134fbb96574921cb9e020049ea52064"
D110_INDEX_PATH = f"reports/memory-development/artifacts/d110/{D110_INDEX_VERSION}/index.json"
D110_INDEX_BYTES = 55_687
D110_INDEX_FILE_SHA256 = "sha256:c0d2ec424e6cc10d64cdebd5ae493e0546fdfa08d09eb5f3269557b46025c6d0"
D110_INDEX_CONTENT_HASH = "sha256:3a99e6c190672d1676bc4d13604de989899de9ddac85d282cc90c4d56f426c56"
D110_MARKER_PATH = f"reports/memory-development/artifacts/d110/{D110_INDEX_VERSION}/FROZEN"
D110_MARKER_BYTES = 72
D110_MARKER_FILE_SHA256 = "sha256:cdfe40b734135a30f66e34ff24469940063a7231a1fe0783420ee2ff816d9561"
D110_GATE_PATH = "reports/memory-development/d110-index-freeze-completion-gate.json"
D110_GATE_ID = "d110_bc1cae7a2ebc5d6531d203ef4d7101762d7366c9e77814c3a4c772d353f0a736"
D110_GATE_BODY_SHA256 = "sha256:bc1cae7a2ebc5d6531d203ef4d7101762d7366c9e77814c3a4c772d353f0a736"
D110_GATE_BYTES = 7_754
D110_GATE_FILE_SHA256 = "sha256:79578db09955dab2a22b015ba5210baec28e7d30b9cac818b1f2c6d6eac782cd"


class FixedBundleEntryBinding(StrictModel):
    order: int = Field(ge=1, le=3)
    memory_id: str = Field(pattern=r"^memgrp_[0-9a-f]{32}$")
    semantic_group_id: str
    render_path: str
    render_file_bytes: int = Field(gt=0)
    render_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="before")
    @classmethod
    def reject_scalar_type_coercion(cls, value: Any) -> Any:
        if isinstance(value, dict):
            for key in ("order", "render_file_bytes"):
                if key in value and type(value[key]) is not int:
                    raise ValueError(f"{key} must be an exact integer")
        return value


EXPECTED_ENTRIES = (
    FixedBundleEntryBinding(
        order=1,
        memory_id="memgrp_649483b80292fea26e4009ebdb72df31",
        semantic_group_id="platform-emulation-matrix-gap",
        render_path=(
            "reports/memory-development/rendered/d105/memgrp_649483b80292fea26e4009ebdb72df31.txt"
        ),
        render_file_bytes=1_191,
        render_file_sha256=(
            "sha256:f1cd44ed10d527ff7f5c44dd0be4e6957810530cd055d3329da0d7962d3cec7c"
        ),
    ),
    FixedBundleEntryBinding(
        order=2,
        memory_id="memgrp_b421547d481faabf9be3511217258de5",
        semantic_group_id="request-context-propagation-gap",
        render_path=(
            "reports/memory-development/rendered/d105/memgrp_b421547d481faabf9be3511217258de5.txt"
        ),
        render_file_bytes=1_164,
        render_file_sha256=(
            "sha256:ab0273b575f76efd4ca9facda9540d87f2ea85e69a333cf87e4d7ac781287c2a"
        ),
    ),
    FixedBundleEntryBinding(
        order=3,
        memory_id="memgrp_5a23f463cba43bf3ba395f67cf976047",
        semantic_group_id="exception-origin-state-conflation",
        render_path=(
            "reports/memory-development/rendered/d105/memgrp_5a23f463cba43bf3ba395f67cf976047.txt"
        ),
        render_file_bytes=1_161,
        render_file_sha256=(
            "sha256:00ceca8ed912a48f36ab26fb50b1d7eb428fe261a83b2bd84e231f0c6e786bf7"
        ),
    ),
)


class FixedMemoryDeliveryEvidence(StrictModel):
    schema_version: Literal["fixed-memory-delivery-evidence-v1"] = (
        "fixed-memory-delivery-evidence-v1"
    )
    policy_version: Literal["fixed-d110-bundle-v1"] = FIXED_BUNDLE_POLICY_VERSION
    condition: Literal["no_memory", "structured"]
    mode: Literal["none", "fixed-approved-three-entry-bundle"]
    selected_memory_present: bool
    entry_count: Literal[0, 3]
    ordered_entries: list[FixedBundleEntryBinding]
    bundle_separator: str | None
    bundle_bytes: int = Field(ge=0)
    bundle_sha256: str | None
    token_budget: Literal[2000] = FIXED_BUNDLE_TOKEN_BUDGET
    d105_gate_id: str | None
    d105_gate_file_sha256: str | None
    d105_render_set_sha256: str | None
    index_version: str | None
    index_content_hash: str | None
    index_file_sha256: str | None
    marker_file_sha256: str | None
    d110_gate_id: str | None
    d110_gate_file_sha256: str | None
    query_dependent: Literal[False] = False
    embedding_or_similarity_used: Literal[False] = False
    ranking_or_threshold_used: Literal[False] = False
    truncation_applied: Literal[False] = False
    legacy_retrieval_called: Literal[False] = False

    @model_validator(mode="before")
    @classmethod
    def reject_scalar_type_coercion(cls, value: Any) -> Any:
        if isinstance(value, dict):
            for key in (
                "entry_count",
                "bundle_bytes",
                "token_budget",
            ):
                if key in value and type(value[key]) is not int:
                    raise ValueError(f"{key} must be an exact integer")
            for key in (
                "selected_memory_present",
                "query_dependent",
                "embedding_or_similarity_used",
                "ranking_or_threshold_used",
                "truncation_applied",
                "legacy_retrieval_called",
            ):
                if key in value and type(value[key]) is not bool:
                    raise ValueError(f"{key} must be an exact boolean")
        return value

    @model_validator(mode="after")
    def validate_exact_delivery(self) -> FixedMemoryDeliveryEvidence:
        if self.condition == MemoryCondition.NO_MEMORY.value:
            if not (
                self.mode == "none"
                and self.selected_memory_present is False
                and self.entry_count == 0
                and self.ordered_entries == []
                and self.bundle_separator is None
                and self.bundle_bytes == 0
                and self.bundle_sha256 is None
                and self.d105_gate_id is None
                and self.d105_gate_file_sha256 is None
                and self.d105_render_set_sha256 is None
                and self.index_version is None
                and self.index_content_hash is None
                and self.index_file_sha256 is None
                and self.marker_file_sha256 is None
                and self.d110_gate_id is None
                and self.d110_gate_file_sha256 is None
            ):
                raise ValueError("no-memory delivery evidence is not exact")
            return self
        expected_entries = [entry.model_dump(mode="json") for entry in EXPECTED_ENTRIES]
        if not (
            self.mode == FIXED_BUNDLE_MODE
            and self.selected_memory_present is True
            and self.entry_count == 3
            and [entry.model_dump(mode="json") for entry in self.ordered_entries]
            == expected_entries
            and self.bundle_separator == FIXED_BUNDLE_SEPARATOR
            and self.bundle_bytes == FIXED_BUNDLE_BYTES
            and self.bundle_sha256 == FIXED_BUNDLE_SHA256
            and self.d105_gate_id == D105_GATE_ID
            and self.d105_gate_file_sha256 == D105_GATE_FILE_SHA256
            and self.d105_render_set_sha256 == D105_RENDER_SET_SHA256
            and self.index_version == D110_INDEX_VERSION
            and self.index_content_hash == D110_INDEX_CONTENT_HASH
            and self.index_file_sha256 == D110_INDEX_FILE_SHA256
            and self.marker_file_sha256 == D110_MARKER_FILE_SHA256
            and self.d110_gate_id == D110_GATE_ID
            and self.d110_gate_file_sha256 == D110_GATE_FILE_SHA256
        ):
            raise ValueError("structured fixed-bundle delivery evidence is not exact")
        return self


class FixedMemoryRequestEvidence(StrictModel):
    schema_version: Literal["fixed-memory-request-evidence-v1"] = "fixed-memory-request-evidence-v1"
    delivery: FixedMemoryDeliveryEvidence
    delivery_evidence_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    request_body_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    normalized_no_memory_request_body_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    treatment_json_pointer: Literal["/selected_memory"] = "/selected_memory"
    same_state_counterfactual_only: Literal[True] = True

    @model_validator(mode="before")
    @classmethod
    def reject_scalar_type_coercion(cls, value: Any) -> Any:
        if (
            isinstance(value, dict)
            and "same_state_counterfactual_only" in value
            and type(value["same_state_counterfactual_only"]) is not bool
        ):
            raise ValueError("same_state_counterfactual_only must be an exact boolean")
        return value

    @model_validator(mode="after")
    def validate_request_binding(self) -> FixedMemoryRequestEvidence:
        expected_delivery_hash = sha256_text(canonical_json(self.delivery.model_dump(mode="json")))
        if self.delivery_evidence_sha256 != expected_delivery_hash:
            raise ValueError("fixed-memory request delivery hash differs")
        if (
            not self.delivery.selected_memory_present
            and self.request_body_sha256 != self.normalized_no_memory_request_body_sha256
        ):
            raise ValueError("no-memory request differs from its normalized identity")
        if (
            self.delivery.selected_memory_present
            and self.request_body_sha256 == self.normalized_no_memory_request_body_sha256
        ):
            raise ValueError("structured request is identical to its no-memory normalization")
        return self


@dataclass(frozen=True)
class FixedMemoryDelivery:
    text: str
    evidence: FixedMemoryDeliveryEvidence

    @property
    def evidence_sha256(self) -> str:
        return sha256_text(canonical_json(self.evidence.model_dump(mode="json")))


def _repository_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else Path(__file__).resolve().parents[2]
    try:
        root = selected.resolve(strict=True)
    except OSError as exc:
        raise ContractError("fixed bundle repository root is unavailable") from exc
    if not root.is_dir():
        raise ContractError("fixed bundle repository root is not a directory")
    return root


def _is_linklike(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ContractError(f"fixed bundle path is unavailable: {path}") from exc
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    file_attributes = getattr(metadata, "st_file_attributes", 0)
    return path.is_symlink() or bool(reparse_flag and file_attributes & reparse_flag)


def _logical_path(root: Path, relative: str) -> Path:
    parsed = PurePosixPath(relative)
    if (
        parsed.is_absolute()
        or not parsed.parts
        or any(part in {"", ".", ".."} for part in parsed.parts)
    ):
        raise ContractError(f"fixed bundle path is not canonical: {relative}")
    selected = root.joinpath(*parsed.parts)
    current = root
    for part in parsed.parts:
        current = current / part
        if not current.exists():
            raise ContractError(f"fixed bundle input is missing: {relative}")
        if _is_linklike(current):
            raise ContractError(f"fixed bundle input traverses a link: {relative}")
    try:
        resolved = selected.resolve(strict=True)
    except OSError as exc:
        raise ContractError(f"fixed bundle input cannot be resolved: {relative}") from exc
    if not resolved.is_relative_to(root):
        raise ContractError(f"fixed bundle input escapes the repository: {relative}")
    return selected


def _stable_read(
    root: Path,
    relative: str,
    *,
    expected_bytes: int,
    expected_sha256: str,
) -> bytes:
    selected = _logical_path(root, relative)
    try:
        before_path = selected.stat(follow_symlinks=False)
        if not stat.S_ISREG(before_path.st_mode):
            raise ContractError(f"fixed bundle input is not a regular file: {relative}")
        with selected.open("rb") as stream:
            before_fd = os.fstat(stream.fileno())
            content = stream.read()
            after_fd = os.fstat(stream.fileno())
        after_path = selected.stat(follow_symlinks=False)
    except OSError as exc:
        raise ContractError(f"fixed bundle input cannot be read: {relative}") from exc
    identities = {
        (before_path.st_dev, before_path.st_ino),
        (before_fd.st_dev, before_fd.st_ino),
        (after_fd.st_dev, after_fd.st_ino),
        (after_path.st_dev, after_path.st_ino),
    }
    if len(identities) != 1 or (
        before_path.st_size != after_path.st_size
        or before_path.st_mtime_ns != after_path.st_mtime_ns
        or before_fd.st_size != after_fd.st_size
        or before_fd.st_mtime_ns != after_fd.st_mtime_ns
    ):
        raise ContractError(f"fixed bundle input changed while reading: {relative}")
    if len(content) != expected_bytes or sha256_bytes(content) != expected_sha256:
        raise ContractError(f"fixed bundle input identity differs: {relative}")
    return content


def _parse_json(content: bytes, *, label: str) -> dict[str, object]:
    try:
        parsed = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label} is not canonical UTF-8 JSON") from exc
    if not isinstance(parsed, dict):
        raise ContractError(f"{label} root is not an object")
    return parsed


def _entry_projection(entry: FixedBundleEntryBinding) -> dict[str, object]:
    return {
        "order": entry.order,
        "memory_id": entry.memory_id,
        "semantic_group_id": entry.semantic_group_id,
        "render_file_sha256": entry.render_file_sha256,
    }


def _validate_d105_gate(payload: dict[str, object]) -> None:
    body = payload.get("semantic_body")
    if not isinstance(body, dict):
        raise ContractError("D-105 gate semantic body is unavailable")
    raw_entries = body.get("entries")
    if not isinstance(raw_entries, list):
        raise ContractError("D-105 gate entries are unavailable")
    projection = []
    for item in raw_entries:
        if not isinstance(item, dict):
            raise ContractError("D-105 gate entry is invalid")
        projection.append(
            {
                "order": item.get("order"),
                "memory_id": item.get("proposed_memory_id"),
                "semantic_group_id": item.get("semantic_group_id"),
                "render_file_sha256": item.get("file_sha256"),
            }
        )
    if not (
        payload.get("gate_id") == D105_GATE_ID
        and payload.get("semantic_body_hash") == D105_GATE_BODY_SHA256
        and projection == [_entry_projection(entry) for entry in EXPECTED_ENTRIES]
        and body.get("render_set_hash") == D105_RENDER_SET_SHA256
        and body.get("rendered_memory_count") == 3
        and body.get("render_validation") == "pass"
        and body.get("bundle")
        == {
            "separator": FIXED_BUNDLE_SEPARATOR,
            "file_bytes": FIXED_BUNDLE_BYTES,
            "file_sha256": FIXED_BUNDLE_SHA256,
            "includes_all_three_entries": True,
            "provider_exact_token_count": None,
        }
    ):
        raise ContractError("D-105 gate does not bind the exact fixed bundle")


def _validate_d110_index(payload: dict[str, object]) -> None:
    raw_provenance = payload.get("group_provenance")
    if not isinstance(raw_provenance, list):
        raise ContractError("D-110 index group provenance is unavailable")
    projection = []
    for item in raw_provenance:
        if not isinstance(item, dict):
            raise ContractError("D-110 group provenance entry is invalid")
        projection.append(
            {
                "order": item.get("order"),
                "memory_id": item.get("memory_id"),
                "semantic_group_id": item.get("semantic_group_id"),
                "render_file_sha256": item.get("render_file_sha256"),
            }
        )
    authority = payload.get("authority")
    if not (
        payload.get("schema_version") == "memory-index-v1"
        and payload.get("index_version") == D110_INDEX_VERSION
        and payload.get("frozen") is True
        and payload.get("content_hash") == D110_INDEX_CONTENT_HASH
        and projection == [_entry_projection(entry) for entry in EXPECTED_ENTRIES]
        and isinstance(authority, dict)
        and authority.get("memory_index_frozen") is True
        and authority.get("retrieval_ready") is False
        and authority.get("retrieval_experiment_authorized") is False
        and authority.get("runtime_memory_injection_count") == 0
    ):
        raise ContractError("D-110 index does not bind the exact frozen bundle inputs")


def _validate_d110_gate(payload: dict[str, object]) -> None:
    body = payload.get("semantic_body")
    if not isinstance(body, dict):
        raise ContractError("D-110 gate semantic body is unavailable")
    portable_index = body.get("portable_frozen_index")
    portable_marker = body.get("portable_frozen_marker")
    if not (
        payload.get("gate_id") == D110_GATE_ID
        and payload.get("semantic_body_hash") == D110_GATE_BODY_SHA256
        and isinstance(portable_index, dict)
        and portable_index.get("file_sha256") == D110_INDEX_FILE_SHA256
        and isinstance(portable_marker, dict)
        and portable_marker.get("file_sha256") == D110_MARKER_FILE_SHA256
    ):
        raise ContractError("D-110 gate does not bind the exact portable freeze")


def _none_delivery() -> FixedMemoryDelivery:
    return FixedMemoryDelivery(
        text="",
        evidence=FixedMemoryDeliveryEvidence(
            condition=MemoryCondition.NO_MEMORY.value,
            mode="none",
            selected_memory_present=False,
            entry_count=0,
            ordered_entries=[],
            bundle_separator=None,
            bundle_bytes=0,
            bundle_sha256=None,
            d105_gate_id=None,
            d105_gate_file_sha256=None,
            d105_render_set_sha256=None,
            index_version=None,
            index_content_hash=None,
            index_file_sha256=None,
            marker_file_sha256=None,
            d110_gate_id=None,
            d110_gate_file_sha256=None,
        ),
    )


def build_fixed_memory_delivery(
    *,
    condition: MemoryCondition,
    token_budget: int = FIXED_BUNDLE_TOKEN_BUDGET,
    repository: str | Path | None = None,
) -> FixedMemoryDelivery:
    """Build A-null or exact C-bundle delivery without retrieval or model calls."""

    if token_budget != FIXED_BUNDLE_TOKEN_BUDGET:
        raise ContractError("fixed D-110 bundle requires the exact 2,000-token allowance")
    if condition == MemoryCondition.NO_MEMORY:
        return _none_delivery()
    if condition != MemoryCondition.STRUCTURED:
        raise ContractError("fixed D-110 bundle supports only no_memory and structured")

    root = _repository_root(repository)
    d105_gate = _parse_json(
        _stable_read(
            root,
            D105_GATE_PATH,
            expected_bytes=D105_GATE_BYTES,
            expected_sha256=D105_GATE_FILE_SHA256,
        ),
        label="D-105 gate",
    )
    _validate_d105_gate(d105_gate)

    d110_index = _parse_json(
        _stable_read(
            root,
            D110_INDEX_PATH,
            expected_bytes=D110_INDEX_BYTES,
            expected_sha256=D110_INDEX_FILE_SHA256,
        ),
        label="D-110 index",
    )
    _validate_d110_index(d110_index)

    marker = _stable_read(
        root,
        D110_MARKER_PATH,
        expected_bytes=D110_MARKER_BYTES,
        expected_sha256=D110_MARKER_FILE_SHA256,
    )
    if marker != (D110_INDEX_CONTENT_HASH + "\n").encode("ascii"):
        raise ContractError("D-110 marker content differs from the frozen index")

    d110_gate = _parse_json(
        _stable_read(
            root,
            D110_GATE_PATH,
            expected_bytes=D110_GATE_BYTES,
            expected_sha256=D110_GATE_FILE_SHA256,
        ),
        label="D-110 gate",
    )
    _validate_d110_gate(d110_gate)

    parts = []
    for entry in EXPECTED_ENTRIES:
        content = _stable_read(
            root,
            entry.render_path,
            expected_bytes=entry.render_file_bytes,
            expected_sha256=entry.render_file_sha256,
        )
        try:
            text = content.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ContractError("D-105 render is not exact ASCII model-facing text") from exc
        if not text.endswith("\n") or text.endswith("\n\n"):
            raise ContractError("D-105 render must end in exactly one LF")
        parts.append(text.removesuffix("\n"))
    bundle = FIXED_BUNDLE_SEPARATOR.join(parts) + "\n"
    bundle_bytes = bundle.encode("ascii")
    if len(bundle_bytes) != FIXED_BUNDLE_BYTES or sha256_bytes(bundle_bytes) != FIXED_BUNDLE_SHA256:
        raise ContractError("D-105 render bundle identity differs")

    return FixedMemoryDelivery(
        text=bundle,
        evidence=FixedMemoryDeliveryEvidence(
            condition=MemoryCondition.STRUCTURED.value,
            mode=FIXED_BUNDLE_MODE,
            selected_memory_present=True,
            entry_count=3,
            ordered_entries=[entry.model_copy(deep=True) for entry in EXPECTED_ENTRIES],
            bundle_separator=FIXED_BUNDLE_SEPARATOR,
            bundle_bytes=FIXED_BUNDLE_BYTES,
            bundle_sha256=FIXED_BUNDLE_SHA256,
            d105_gate_id=D105_GATE_ID,
            d105_gate_file_sha256=D105_GATE_FILE_SHA256,
            d105_render_set_sha256=D105_RENDER_SET_SHA256,
            index_version=D110_INDEX_VERSION,
            index_content_hash=D110_INDEX_CONTENT_HASH,
            index_file_sha256=D110_INDEX_FILE_SHA256,
            marker_file_sha256=D110_MARKER_FILE_SHA256,
            d110_gate_id=D110_GATE_ID,
            d110_gate_file_sha256=D110_GATE_FILE_SHA256,
        ),
    )


def _fixed_context_strings(value: object) -> list[str]:
    candidates: list[str] = []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return candidates
        if isinstance(parsed, dict) and "selected_memory" in parsed:
            candidates.append(value)
        return candidates
    if isinstance(value, list):
        for item in value:
            candidates.extend(_fixed_context_strings(item))
        return candidates
    if isinstance(value, dict):
        for item in value.values():
            candidates.extend(_fixed_context_strings(item))
    return candidates


def _replace_exact_string(
    value: object,
    *,
    original: str,
    replacement: str,
) -> tuple[object, int]:
    if isinstance(value, str):
        return (replacement, 1) if value == original else (value, 0)
    if isinstance(value, list):
        replaced_items = []
        replacement_count = 0
        for item in value:
            replaced, count = _replace_exact_string(
                item,
                original=original,
                replacement=replacement,
            )
            replaced_items.append(replaced)
            replacement_count += count
        return replaced_items, replacement_count
    if isinstance(value, dict):
        replaced_mapping = {}
        replacement_count = 0
        for key, item in value.items():
            replaced, count = _replace_exact_string(
                item,
                original=original,
                replacement=replacement,
            )
            replaced_mapping[key] = replaced
            replacement_count += count
        return replaced_mapping, replacement_count
    return value, 0


def validate_fixed_memory_request_artifact(
    artifact: dict[str, object],
    *,
    context_event_payload: dict[str, object] | None = None,
) -> FixedMemoryRequestEvidence:
    """Replay one fixed-policy request and its optional ContextBuilt binding."""

    if not isinstance(artifact, dict):
        raise ContractError("fixed-memory request artifact root is invalid")
    if context_event_payload is not None and not isinstance(context_event_payload, dict):
        raise ContractError("ContextBuilt fixed-memory payload is invalid")
    required_keys = {
        "schema_version",
        "provider",
        "endpoint",
        "request_body",
        "request_body_hash",
        "context_build",
        "fixed_memory_delivery",
    }
    optional_keys = {key for key in ("worker_claim", "lean_harness_request") if key in artifact}
    expected_keys = required_keys | optional_keys
    if set(artifact) != expected_keys:
        raise ContractError("fixed-memory request artifact fields differ")
    if artifact.get("schema_version") != "model-request-evidence-v1":
        raise ContractError("fixed-memory request artifact schema differs")
    request_body = artifact.get("request_body")
    context_build = artifact.get("context_build")
    raw_evidence = artifact.get("fixed_memory_delivery")
    if not isinstance(request_body, dict) or not isinstance(context_build, dict):
        raise ContractError("fixed-memory request artifact payload is invalid")
    try:
        evidence = FixedMemoryRequestEvidence.model_validate(raw_evidence)
    except (TypeError, ValueError) as exc:
        raise ContractError("fixed-memory request evidence is invalid") from exc

    request_body_hash = sha256_text(canonical_json(request_body))
    if (
        artifact.get("request_body_hash") != request_body_hash
        or evidence.request_body_sha256 != request_body_hash
    ):
        raise ContractError("fixed-memory request body hash differs")

    rendered_contexts = _fixed_context_strings(request_body)
    if len(rendered_contexts) != 1:
        raise ContractError("fixed-memory request must contain exactly one rendered context")
    rendered_context = rendered_contexts[0]
    try:
        context_payload = json.loads(rendered_context)
    except json.JSONDecodeError as exc:  # pragma: no cover - guarded by discovery
        raise ContractError("fixed-memory rendered context is invalid") from exc
    if not isinstance(context_payload, dict):  # pragma: no cover - guarded by discovery
        raise ContractError("fixed-memory rendered context is not an object")

    selected_memory = context_payload.get("selected_memory")
    if evidence.delivery.selected_memory_present:
        if not isinstance(selected_memory, str):
            raise ContractError("structured request has no selected-memory text")
        try:
            selected_memory_bytes = selected_memory.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ContractError("structured selected-memory text is not exact ASCII") from exc
        if (
            len(selected_memory_bytes) != FIXED_BUNDLE_BYTES
            or sha256_bytes(selected_memory_bytes) != FIXED_BUNDLE_SHA256
            or selected_memory.count(FIXED_BUNDLE_SEPARATOR) != 2
            or not selected_memory.endswith("\n")
        ):
            raise ContractError("structured selected-memory text identity differs")
    elif selected_memory is not None:
        raise ContractError("no-memory request contains selected-memory text")

    normalized_context_payload = dict(context_payload)
    normalized_context_payload["selected_memory"] = None
    normalized_context = json.dumps(
        normalized_context_payload,
        indent=2,
        ensure_ascii=False,
        default=str,
    )
    if evidence.delivery.selected_memory_present:
        normalized_request, replacement_count = _replace_exact_string(
            request_body,
            original=rendered_context,
            replacement=normalized_context,
        )
        if replacement_count != 1 or not isinstance(normalized_request, dict):
            raise ContractError("fixed-memory request normalization is ambiguous")
        normalized_hash = sha256_text(canonical_json(normalized_request))
    else:
        normalized_hash = request_body_hash
    if evidence.normalized_no_memory_request_body_sha256 != normalized_hash:
        raise ContractError("fixed-memory normalized request hash differs")

    if context_event_payload is not None:
        expected_event_bindings = {
            "context_hash": sha256_text(rendered_context),
            "context_characters": len(rendered_context),
            "context_bytes": len(rendered_context.encode("utf-8")),
            "request_body_hash": request_body_hash,
            "memory_delivery_policy_version": FIXED_BUNDLE_POLICY_VERSION,
            "memory_delivery_evidence_sha256": evidence.delivery_evidence_sha256,
            "memory_delivery_entry_count": evidence.delivery.entry_count,
            "memory_delivery_bundle_sha256": evidence.delivery.bundle_sha256,
            "normalized_no_memory_request_body_sha256": normalized_hash,
        }
        if any(
            context_event_payload.get(key) != value
            for key, value in expected_event_bindings.items()
        ):
            raise ContractError("ContextBuilt fixed-memory binding differs")
    return evidence


def fixed_bundle_manifest_binding(condition: MemoryCondition) -> tuple[str | None, str | None]:
    """Return the manifest index binding without touching fixed-bundle inputs."""

    if condition == MemoryCondition.NO_MEMORY:
        return None, None
    if condition == MemoryCondition.STRUCTURED:
        return D110_INDEX_VERSION, D110_INDEX_CONTENT_HASH
    raise ContractError("fixed D-110 policy supports only no_memory and structured")


__all__ = [
    "D110_INDEX_CONTENT_HASH",
    "D110_INDEX_FILE_SHA256",
    "D110_INDEX_VERSION",
    "EXPECTED_ENTRIES",
    "FIXED_BUNDLE_BYTES",
    "FIXED_BUNDLE_POLICY_VERSION",
    "FIXED_BUNDLE_SHA256",
    "FixedMemoryDelivery",
    "FixedMemoryDeliveryEvidence",
    "FixedMemoryRequestEvidence",
    "build_fixed_memory_delivery",
    "fixed_bundle_manifest_binding",
    "validate_fixed_memory_request_artifact",
]
