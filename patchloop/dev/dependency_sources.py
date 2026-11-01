"""Read explicitly registered caller source from an admitted public wheel snapshot."""

from __future__ import annotations

import re
import stat
from pathlib import Path

from packaging.utils import canonicalize_name

from patchloop import probe_callers
from patchloop.contracts import PublicTask
from patchloop.dev.source_glob import matches_source_glob
from patchloop.errors import ContractError
from patchloop.prepared_probe_dependencies import PreparedDependencies, read_descriptor
from patchloop.util import ensure_within, safe_relative_path, sha256_bytes, sha256_json

MAX_SOURCE_BYTES = 2_000_000


def normalize_roots(roots: dict[str, str]) -> dict[str, str]:
    """Normalize explicit package/root pairs, never infer an import root from a pin."""
    if not isinstance(roots, dict) or len(roots) > 8:
        raise ContractError("caller source registration requires at most eight package roots")
    normalized = {}
    for package, root in roots.items():
        if not isinstance(package, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}", package,
        ):
            raise ContractError(
                "caller source package must be a distribution name without a version"
            )
        package = canonicalize_name(package)
        if package in normalized:
            raise ContractError("caller source package must be unique")
        normalized[package] = probe_callers.source_root(root)
    return dict(sorted(normalized.items()))


def parse_cli_roots(values: list[str] | None) -> dict[str, str]:
    """Parse repeated --caller-source distribution=directory options explicitly."""
    pairs = {}
    for value in values or []:
        package, separator, root = value.partition("=")
        if not separator or "=" in root or package in pairs:
            raise ContractError("--caller-source requires unique distribution=directory pairs")
        pairs[package] = root
    return normalize_roots(pairs)


def for_run(
    dependencies: PreparedDependencies | None, roots: dict[str, str],
    public: PublicTask | None = None,
) -> DependencySources | None:
    """Bind task/request read scopes to the prepared caller snapshot before dispatch."""
    roots = normalize_roots(roots)
    if public is not None:
        roots = normalize_roots(probe_callers.task_source_roots(public, roots))
    if not roots:
        return None
    if dependencies is None:
        raise ContractError(
            "caller source registration requires prepared probe dependencies and enabled probes"
        )
    if public is not None:
        descriptor, _ = read_descriptor(dependencies.path)
        probe_callers.verify_task_snapshot(public, descriptor)
    return DependencySources(dependencies, roots)


def _relative(value: str, *, field: str) -> str:
    if not isinstance(value, str) or any(char in value for char in (":", "\x00")):
        raise ContractError(f"{field} must be a safe relative path")
    normalized = safe_relative_path(value, field_name=field)
    if normalized == "." or any(
        part.casefold() in {".git", ".patchloop-hidden"} or part.casefold().startswith(".env")
        for part in normalized.split("/")
    ):
        raise ContractError(f"{field} must be a public relative path")
    return normalized


class DependencySources:
    """Paths are site-packages-relative; registration never follows package imports.

    ``paths`` returns descriptor-indexed candidates without reading their bodies.
    ``read`` verifies the selected bytes against the admitted descriptor before
    returning source. Other installed packages and unindexed files are unavailable.
    """

    def __init__(self, dependencies: PreparedDependencies, roots: dict[str, str]) -> None:
        roots = normalize_roots(roots)
        descriptor, identity = read_descriptor(dependencies.path)
        if identity != dependencies.identity:
            raise ContractError("prepared dependency identity changed")
        callers = probe_callers.from_descriptor(descriptor)
        if callers != dependencies.callers:
            raise ContractError("prepared public caller identity changed")
        if (descriptor["repository_url"], descriptor["base_commit"]) != (
            dependencies.repository_url, dependencies.base_commit,
        ):
            raise ContractError("prepared dependency source identity changed")
        pins = dict(pin.split("==") for pin in callers)
        self._root = dependencies.path.parent / "site-packages"
        self._catalog: dict[str, dict] = {}
        self._files: dict[str, dict[str, str]] = {}
        for package, root in sorted(roots.items()):
            if package not in pins:
                raise ContractError("dependency source registration requires an exact caller pin")
            root = _relative(root, field="dependency source root")
            if any(char in root for char in "*?[]"):
                raise ContractError("dependency source root must be a literal directory")
            scope = f"dependency:{package}"
            files = {}
            for path, file_hash in descriptor["files"].items():
                if path.startswith(root + "/") and path.endswith(".py"):
                    normalized = _relative(path, field="dependency source path")
                    if normalized != path:
                        raise ContractError("dependency source inventory path is not canonical")
                    files[path] = file_hash
            if not files:
                raise ContractError("registered dependency root has no indexed Python source")
            self._catalog[scope] = {
                "scope": scope, "package": package, "version": pins[package], "root": root,
                "manifest_hash": identity.manifest_hash, "content_hash": identity.content_hash,
            }
            self._files[scope] = files
        self.identity = sha256_json({
            "manifest_hash": identity.manifest_hash, "content_hash": identity.content_hash,
            "roots": {entry["package"]: entry["root"] for entry in self._catalog.values()},
        })

    def catalog(self) -> list[dict]:
        return [dict(entry) for entry in self._catalog.values()]

    def _scope(self, scope: str) -> dict[str, str]:
        if scope not in self._files:
            raise ContractError("dependency source scope is not registered")
        return self._files[scope]

    def paths(self, scope: str, path_glob: str = "**/*") -> list[str]:
        files = self._scope(scope)
        pattern = _relative(path_glob, field="dependency search path_glob")
        return sorted(path for path in files if matches_source_glob(path, pattern))

    def _source_path(self, relative: str) -> Path:
        # Check lexical ancestors before ensure_within resolves them: a symlink
        # within the same root is also outside this source-only contract.
        selected = self._root / relative
        for part in (selected, *selected.parents):
            attributes = part.lstat()
            if (stat.S_ISLNK(attributes.st_mode)
                    or getattr(attributes, "st_file_attributes", 0) & 0x400):
                raise ContractError("dependency source symlinks and reparse points are forbidden")
            expected = stat.S_ISREG if part == selected else stat.S_ISDIR
            if not expected(attributes.st_mode):
                raise ContractError("dependency source must be a regular public file")
        return ensure_within(self._root, relative)

    def read(self, scope: str, path: str) -> tuple[str, dict]:
        files = self._scope(scope)
        relative = _relative(path, field="dependency source path")
        if relative not in files:
            raise ContractError("path is not registered dependency Python source")
        try:
            selected = self._source_path(relative)
            with selected.open("rb") as stream:
                raw = stream.read(MAX_SOURCE_BYTES + 1)
            if len(raw) > MAX_SOURCE_BYTES:
                raise ContractError("dependency source read refuses files larger than 2 MB")
            if sha256_bytes(raw) != files[relative]:
                raise ContractError("prepared dependency source hash changed")
            text = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ContractError("prepared dependency source cannot be read as UTF-8") from exc
        return text, {
            **self._catalog[scope], "origin": "prepared_dependency", "path": relative,
            "file_hash": files[relative],
        }
