"""Small deterministic helpers shared by domain modules."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from patchloop.errors import ContractError


def utc_now() -> datetime:
    return datetime.now(UTC)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects ambiguous duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_unique_yaml(value: str) -> Any:
    """Parse trusted-shape YAML without accepting last-key-wins ambiguity."""

    return yaml.load(value, Loader=_UniqueKeySafeLoader)


def require_yaml_scalar_type_identity(
    raw: Any,
    normalized: Any,
    *,
    source: str,
    path: str = "$",
) -> None:
    """Reject scalar coercion hidden by a normalized machine contract.

    YAML mappings and sequences may legitimately normalize into Pydantic mapping,
    list, or tuple containers. Their scalar leaves must nevertheless retain the
    exact JSON/YAML type supplied by the source. This keeps quoted numbers,
    quoted booleans, integer-as-float values, and quoted timestamps from sharing
    an identity hash with the intended source representation.
    """

    if isinstance(normalized, Enum):
        normalized = normalized.value

    if isinstance(raw, Mapping):
        if not isinstance(normalized, Mapping):
            raise ContractError(f"{source} scalar type mismatch at {path}")
        for key, raw_value in raw.items():
            matching_key = next((item for item in normalized if item == key), None)
            if matching_key is None:
                raise ContractError(f"{source} mapping key type mismatch at {path}: {key!r}")
            require_yaml_scalar_type_identity(
                raw_value,
                normalized[matching_key],
                source=source,
                path=f"{path}.{key}",
            )
        return

    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
        if not isinstance(normalized, Sequence) or isinstance(normalized, (str, bytes, bytearray)):
            raise ContractError(f"{source} scalar type mismatch at {path}")
        if len(raw) != len(normalized):
            raise ContractError(f"{source} sequence length mismatch at {path}")
        for index, (raw_value, normalized_value) in enumerate(zip(raw, normalized, strict=True)):
            require_yaml_scalar_type_identity(
                raw_value,
                normalized_value,
                source=source,
                path=f"{path}[{index}]",
            )
        return

    if isinstance(normalized, Enum):
        normalized = normalized.value
    if type(raw) is not type(normalized):
        raise ContractError(
            f"{source} scalar type mismatch at {path}: "
            f"expected {type(normalized).__name__}, got {type(raw).__name__}"
        )


def sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def filesystem_path(path: Path) -> Path:
    """Use Windows extended paths for filesystem I/O, independent of host policy."""

    if os.name != "nt":
        return path
    absolute = os.path.abspath(path)
    if absolute.startswith("\\\\?\\"):
        return Path(absolute)
    if absolute.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + absolute[2:])
    return Path("\\\\?\\" + absolute)


def directory_hash(root: Path) -> str:
    root = filesystem_path(root)
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if ".git" in path.relative_to(root).parts:
            continue
        relative = path.relative_to(root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return f"sha256:{digest.hexdigest()}"


def raw_file_set_hash(root: Path, relative_paths: Iterable[str]) -> str:
    """Hash a sorted, explicitly named set of regular files by path and raw bytes."""

    resolved_root = root.resolve()
    normalized = [
        safe_relative_path(value, field_name="content file path")
        for value in relative_paths
    ]
    if len(normalized) != len(set(normalized)):
        raise ContractError("content file set contains duplicate paths")
    digest = hashlib.sha256()
    for relative in sorted(normalized):
        path = ensure_within(resolved_root, relative)
        if not path.is_file() or path.is_symlink():
            raise ContractError(f"content file is not a regular file: {relative}")
        name = relative.encode("utf-8")
        content = path.read_bytes()
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return f"sha256:{digest.hexdigest()}"


def safe_relative_path(value: str, *, field_name: str = "path") -> str:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts:
        raise ContractError(f"{field_name} must be a safe relative path: {value!r}")
    if any(part in {"", "."} for part in path.parts):
        raise ContractError(f"{field_name} contains an invalid segment: {value!r}")
    return path.as_posix()


def ensure_within(root: Path, relative: str) -> Path:
    safe = safe_relative_path(relative)
    root_resolved = root.resolve()
    candidate = (root_resolved / safe).resolve()
    if os.path.commonpath([str(root_resolved), str(candidate)]) != str(root_resolved):
        raise ContractError(f"path escapes root: {relative!r}")
    return candidate
