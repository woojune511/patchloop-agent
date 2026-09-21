"""Declarative version modules for probes; never execute project build hooks."""

from __future__ import annotations

import stat
import tomllib
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Literal

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from pydantic import Field, field_validator

from patchloop.contracts import ProbeDependencyIdentity, StrictModel
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes

DIRECTORY = "project-files"
GENERATOR = "hatch-vcs-python-snapshot-v1"


class GeneratedProjectFile(StrictModel):
    path: str
    pyproject_path: str
    pyproject_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    generator: Literal["hatch-vcs-python-snapshot-v1"] = GENERATOR
    version: str = Field(pattern=r"^0\+patchloop\.[0-9a-f]{40}$")

    @field_validator("path", "pyproject_path")
    @classmethod
    def public_path(cls, value: str) -> str:
        # Pure POSIX validation alone accepts Windows drives, ADS names and
        # aliases such as '.. ', which must never become host write targets.
        parts = PurePosixPath(value).parts
        if (not parts or "\\" in value or ":" in value or PureWindowsPath(value).drive
                or PurePosixPath(value).as_posix() != value
                or any(part.endswith((".", " ")) for part in parts)):
            raise ContractError("generated project path must be a canonical public relative path")
        ProbeDependencyIdentity.public_import_roots([value])
        return value


def records(descriptor: dict) -> list[GeneratedProjectFile]:
    raw = descriptor.get("generated_project_files", [])
    if not isinstance(raw, list) or len(raw) > 9:
        raise ValueError("invalid generated project file inventory")
    result = [GeneratedProjectFile.model_validate(item) for item in raw]
    if len({item.path.casefold() for item in result}) != len(result):
        raise ValueError("duplicate generated project file")
    return result


def _version_module(version: str) -> bytes:
    # Same snapshot identity as our minimal dist-info. This is deliberately not
    # a VCS release calculation or a reproduction of arbitrary backend output.
    local = version.split("+", 1)[1]
    return (
        "# Prepared by PatchLoop from a public hatch-vcs declaration.\n"
        "# Source snapshot identity only; release-version behavior is unverified.\n"
        f"__version__ = version = {version!r}\n"
        f"__version_tuple__ = version_tuple = {(0, local)!r}\n"
    ).encode()


def prepare(repo: Path, metadata: list[dict], roots: list[str], output: Path) -> list[dict]:
    generated = []
    for project in metadata:
        project_root = repo / project["project_path"]
        pyproject = project_root / "pyproject.toml"
        raw = pyproject.read_bytes()
        if sha256_bytes(raw) != project["pyproject_hash"]:
            raise ContractError("public project metadata changed during preparation")
        config = tomllib.loads(raw.decode("utf-8"))
        hatch = config.get("tool", {}).get("hatch", {})
        build = hatch.get("build", {})
        hook = build.get("hooks", {}).get("vcs")
        if hook is None:
            continue
        build_system = config.get("build-system", {})
        requirements = {canonicalize_name(Requirement(item).name)
                        for item in build_system.get("requires", [])}
        if (build_system.get("build-backend") != "hatchling.build"
                or "backend-path" in build_system or "hatch-vcs" not in requirements
                or project["version_basis"] != "source_snapshot_not_release_version"
                or hatch.get("version", {}).get("source") != "vcs"
                or not isinstance(hook, dict) or set(hook) != {"version-file"}
                or (project_root / "hatch.toml").exists()
                or any("vcs" in target.get("hooks", {})
                       for target in build.get("targets", {}).values())):
            raise ContractError("generated project files require a default public hatch-vcs hook")
        declared = hook["version-file"]
        GeneratedProjectFile.public_path(declared)
        if not declared.endswith(".py"):
            raise ContractError("generated hatch-vcs version file must be Python")
        relative = (Path(project["project_path"]) / declared).as_posix()
        if roots and "/" in relative and not any(relative.startswith(f"{root}/") for root in roots):
            raise ContractError("generated project file is outside the probe source roots")
        source = repo / relative
        if not source.resolve().is_relative_to(repo):
            raise ContractError("generated project file leaves the prepared source")
        for part in (source, *source.parents):
            if part == repo:
                break
            if part.is_symlink() or (part.exists()
                    and getattr(part.lstat(), "st_file_attributes", 0) & 0x400):
                raise ContractError("generated project file path contains a link or reparse point")
        if source.exists():
            raise ContractError("generated project file would replace prepared source")
        content = _version_module(project["version"])
        record = GeneratedProjectFile(
            path=relative, pyproject_path=pyproject.relative_to(repo).as_posix(),
            pyproject_hash=project["pyproject_hash"], content_hash=sha256_bytes(content),
            version=project["version"],
        )
        generated.append(record.model_dump(mode="json"))
        records({"generated_project_files": generated})
        destination = output / DIRECTORY / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(content)
    return generated


def copy_to_snapshot(items: list[GeneratedProjectFile], source: Path, target: Path, *,
                     tracked_paths: set[str], remaining_bytes: int) -> list[dict]:
    manifest = []
    for item in items:
        if item.path in tracked_paths:
            continue  # A current tracked edit always wins, including omitted links.
        metadata = target / item.pyproject_path
        if not metadata.is_file() or sha256_bytes(metadata.read_bytes()) != item.pyproject_hash:
            raise ContractError("generated project file requires unchanged public build metadata")
        artifact = source / item.path
        attributes = artifact.lstat()
        if (artifact.is_symlink() or getattr(attributes, "st_file_attributes", 0) & 0x400
                or not stat.S_ISREG(attributes.st_mode)):
            raise ContractError("generated project file must be a regular prepared file")
        with artifact.open("rb") as stream:
            content = stream.read(min(remaining_bytes, 64_000) + 1)
        if len(content) > remaining_bytes or sha256_bytes(content) != item.content_hash:
            raise ContractError("generated project file changed or exceeds snapshot bound")
        remaining_bytes -= len(content)
        destination = target / item.path
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(content)
        destination.chmod(0o444)
        manifest.append({"path": item.path, "content_hash": item.content_hash,
                         "origin": item.generator, "pyproject_hash": item.pyproject_hash})
    return manifest
