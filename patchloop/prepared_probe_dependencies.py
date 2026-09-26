"""Prepare public, source-locked wheels once; reuse verified offline import snapshots.

Preparation downloads only exact public PyPI wheel URLs already present in the
prepared repository's uv lock. uv installs those wheels offline into a new target;
no source builds, project installs, evaluator extraction or image acquisition.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from pydantic import Field, ValidationError, field_validator

from patchloop import probe_project_files
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import ProbeDependencyIdentity, PublicTask, StrictModel
from patchloop.deadline import ExecutionDeadline
from patchloop.errors import ContractError
from patchloop.prepared_source import admission_hash, load_source
from patchloop.util import canonical_json, safe_relative_path, sha256_bytes, sha256_json

MANIFEST = "prepared-probe-dependencies.json"
MAX_BYTES = 256 * 1024 * 1024
MAX_FILES = 15_000
MOUNT = "/opt/patchloop-dependencies"


class PublicWheel(StrictModel):
    url: str
    hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    size: int = Field(gt=0, le=MAX_BYTES)

    @field_validator("url")
    @classmethod
    def public_pypi_wheel(cls, value: str) -> str:
        url = urlsplit(value)
        if (url.scheme != "https" or url.netloc != "files.pythonhosted.org"
                or url.query or url.fragment or not url.path.endswith(".whl")
                or not url.path.startswith("/packages/") or "%" in url.path):
            raise ValueError("probe dependencies require exact public PyPI wheel URLs")
        safe_relative_path(url.path.rsplit("/", 1)[-1], field_name="wheel filename")
        return value


class WheelLock(StrictModel):
    schema_version: str = "public-probe-wheel-lock-v1"
    source_lock: str
    source_lock_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_roots: list[str] = Field(default_factory=list, max_length=8)
    wheels: list[PublicWheel] = Field(min_length=1, max_length=128)

    @field_validator("source_lock")
    @classmethod
    def lock_path(cls, value):
        ProbeDependencyIdentity.public_import_roots([value])
        return safe_relative_path(value, field_name="public lock path")

    @field_validator("source_roots")
    @classmethod
    def import_roots(cls, values):
        return ProbeDependencyIdentity.public_import_roots(values)


def _read_bytes(path: Path, limit: int = 4_000_000) -> bytes:
    try:
        if path.is_symlink() or not path.is_file():
            raise ContractError("probe dependency descriptor is missing or invalid")
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ContractError("probe dependency descriptor exceeds its size bound")
        return data
    except OSError as exc:
        raise ContractError("probe dependency descriptor cannot be read") from exc


def _read_json(path: Path) -> dict:
    try:
        return json.loads(_read_bytes(path))
    except ValueError as exc:
        raise ContractError("probe dependency descriptor is not JSON") from exc


def _files(root: Path) -> dict[str, Path]:
    if not root.is_dir() or root.is_symlink():
        raise ContractError("prepared dependency directory is missing or invalid")
    files = {}
    for path in chain((root,), root.rglob("*")):
        attributes = path.lstat()
        if (path.is_symlink() or getattr(attributes, "st_file_attributes", 0) & 0x400
                or not (stat.S_ISDIR(attributes.st_mode) or stat.S_ISREG(attributes.st_mode))):
            raise ContractError("prepared dependencies must be regular public files")
        if path == root:
            continue
        relative = path.relative_to(root).as_posix()
        safe_relative_path(relative, field_name="dependency path")
        if any(part.casefold() in {".git", ".patchloop-hidden"}
               or part.casefold().startswith(".env") for part in Path(relative).parts):
            raise ContractError("prepared dependency path is not public")
        if path.is_file():
            files[relative] = path
        if len(files) > MAX_FILES:
            raise ContractError("prepared dependency file inventory exceeds its bound")
    return files


def _inventory(root: Path, *, target: Path | None = None,
               deadline: ExecutionDeadline | None = None) -> dict[str, str]:
    files, hashes, total = _files(root), {}, 0
    for relative, path in sorted(files.items()):
        if deadline:
            deadline.check(reserve_seconds=5)
        with path.open("rb") as stream:
            content = stream.read(MAX_BYTES - total + 1)
        total += len(content)
        if total > MAX_BYTES:
            raise ContractError("prepared dependencies exceed the byte bound")
        hashes[relative] = sha256_bytes(content)
        if target is not None:
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            destination.chmod(0o444)
    if not hashes or set(_files(root)) != set(files):
        raise ContractError("prepared dependency inventory is empty or changed")
    return hashes


def _content_hash(files: dict[str, str], generated: list[dict]) -> str:
    return sha256_json({"files": files, "generated_project_files": generated}
                       if generated else files)


@dataclass(frozen=True)
class PreparedDependencies:
    path: Path
    identity: ProbeDependencyIdentity
    repository_url: str
    base_commit: str
    generated_project_files: tuple[probe_project_files.GeneratedProjectFile, ...] = ()

    @property
    def environment(self) -> dict:
        return {"kind": "prepared_public_wheels", "python": self.identity.python,
                "snapshot_scope": ("root_files_and_source_trees" if self.identity.source_roots
                                   else "all_tracked_regular_files"),
                "source_roots": ["/workspace", *[f"/workspace/{root}"
                                 for root in self.identity.source_roots]],
                "dependency_path": MOUNT, "network": "none", "installation": "unavailable",
                **({"generated_version_files": True} if self.generated_project_files else {})}

    def verify(self, *, target: Path | None = None,
               deadline: ExecutionDeadline | None = None) -> None:
        descriptor, identity = read_descriptor(self.path)
        if identity != self.identity:
            raise ContractError("prepared dependency identity changed")
        try:
            hashes = _inventory(self.path.parent / "site-packages", target=target,
                                deadline=deadline)
            generated = probe_project_files.records(descriptor)
            if tuple(generated) != self.generated_project_files:
                raise ContractError("prepared generated project file identity changed")
            if generated and _inventory(self.path.parent / probe_project_files.DIRECTORY,
                                        deadline=deadline) != {
                    item.path: item.content_hash for item in generated}:
                raise ContractError("prepared generated project files are missing or changed")
        except OSError as exc:
            raise ContractError("prepared dependencies cannot be read or copied") from exc
        if hashes != descriptor["files"] or _content_hash(
            hashes, [item.model_dump(mode="json") for item in generated],
        ) != identity.content_hash:
            raise ContractError("prepared dependency contents are missing or changed")

    def copy_project_files(self, target: Path, *, tracked_paths: set[str],
                           remaining_bytes: int) -> list[dict]:
        return probe_project_files.copy_to_snapshot(
            list(self.generated_project_files), self.path.parent / probe_project_files.DIRECTORY,
            target, tracked_paths=tracked_paths, remaining_bytes=remaining_bytes,
        )


def read_descriptor(path: Path) -> tuple[dict, ProbeDependencyIdentity]:
    try:
        raw = _read_bytes(path)
        descriptor = json.loads(raw)
        if descriptor["schema_version"] != "prepared-probe-dependencies-v1":
            raise ValueError("unsupported prepared dependencies")
        from patchloop.sandbox.probes import PROBE_IMAGE

        if descriptor["image"] != PROBE_IMAGE:
            raise ValueError("prepared dependencies require the clean probe image")
        identity = ProbeDependencyIdentity(
            manifest_hash=sha256_bytes(raw), content_hash=descriptor["content_hash"],
            python=descriptor["python"], platform=descriptor["platform"],
            source_roots=descriptor["source_roots"],
        )
        if not isinstance(descriptor["files"], dict):
            raise ValueError("missing dependency file inventory")
        probe_project_files.records(descriptor)
        if not all(isinstance(descriptor[key], str) and descriptor[key]
                   for key in ("repository_url", "base_commit")):
            raise ValueError("missing dependency source identity")
        return descriptor, identity
    except (OSError, KeyError, TypeError, ValueError, ValidationError) as exc:
        raise ContractError("prepared dependency descriptor is invalid") from exc


def admit(path: Path | None) -> ProbeDependencyIdentity | None:
    if path is None:
        return None
    try:
        return read_descriptor(path)[1]
    except ContractError:
        return None  # The normal run preflight records the failure before model dispatch.


def load_dependencies(path: Path, public: PublicTask,
                      identity: ProbeDependencyIdentity | None) -> PreparedDependencies:
    descriptor, actual = read_descriptor(path)
    if identity is None or actual != identity:
        raise ContractError("prepared probe dependencies differ from the admitted identity")
    if (descriptor["repository_url"], descriptor["base_commit"]) != (
        public.repository.url, public.repository.base_commit,
    ):
        raise ContractError("prepared probe dependencies do not match the task source")
    return PreparedDependencies(path.resolve(), identity, public.repository.url,
                                public.repository.base_commit,
                                tuple(probe_project_files.records(descriptor)))


def _download(wheel: PublicWheel, destination: Path) -> None:
    with (
        httpx.Client(trust_env=False, follow_redirects=False, timeout=30) as client,
        client.stream("GET", wheel.url) as response,
    ):
        response.raise_for_status()
        size = 0
        with destination.open("xb") as stream:
            for block in response.iter_bytes():
                size += len(block)
                if size > wheel.size:
                    raise ContractError("public wheel exceeds its locked size")
                stream.write(block)
    if size != wheel.size or sha256_bytes(destination.read_bytes()) != wheel.hash:
        raise ContractError("public wheel differs from its locked hash or size")


def _workspace_metadata(repo: Path, packages: list[dict], roots: list[str],
                        commit: str, target: Path) -> list[dict]:
    """Supply importlib.metadata identity without running a project's build hooks."""
    records = []
    for package in packages:
        relative = package.get("source", {}).get("editable")
        if relative not in {".", *roots}:
            continue
        project_file = repo / relative / "pyproject.toml"
        if project_file.is_symlink() or not project_file.resolve().is_relative_to(repo):
            raise ContractError("workspace metadata must come from the public source")
        raw = project_file.read_bytes()
        project = tomllib.loads(raw.decode("utf-8"))["project"]
        name = project["name"]
        if name != package["name"] or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}", name):
            raise ContractError("workspace package name differs from the public lock")
        version = project.get("version")
        basis = "public_pyproject"
        if version is None and "version" in project.get("dynamic", []):
            version, basis = f"0+patchloop.{commit}", "source_snapshot_not_release_version"
        if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.!+_-]{0,199}",
                                                           version):
            raise ContractError("workspace package has no supported public version metadata")
        record = {"name": name, "version": version, "version_basis": basis,
                  "project_path": relative, "pyproject_hash": sha256_bytes(raw)}
        directory = target / f"{re.sub(r'[-_.]+', '_', name)}-{version}.dist-info"
        directory.mkdir(exist_ok=False)
        (directory / "METADATA").write_text(
            f"Metadata-Version: 2.3\nName: {name}\nVersion: {version}\n", encoding="utf-8",
        )
        (directory / "PATCHLOOP-SOURCE.json").write_text(canonical_json(record), encoding="utf-8")
        records.append(record)
    return records


def prepare_dependencies(*, public: PublicTask, prepared_source: Path, output: Path,
                         wheel_lock: Path | None = None, resolve: bool = False,
                         groups: list[str] | None = None, extras: list[str] | None = None,
                         source_roots: list[str] | None = None,
                         selected_dependencies: list[str] | None = None) -> Path:
    from patchloop.dev.state import DevJournal
    from patchloop.runtime import repository_root
    from patchloop.sandbox.probes import PROBE_IMAGE

    if resolve == (wheel_lock is not None):
        raise ContractError("choose exactly one of --wheel-lock or --resolve")
    if not resolve and (groups or extras or source_roots or selected_dependencies):
        raise ContractError("dependency selections and --source-root require --resolve")
    if selected_dependencies and not (groups or extras):
        raise ContractError("--select-dependency requires a public --group or --extra")
    output = output.resolve()
    if output.is_relative_to(repository_root().resolve()):
        raise ContractError("prepared dependencies must be outside the repository")
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise ContractError("prepared dependency output already exists") from exc
    journal = DevJournal(output, "run_dev_preparedependencies")
    journal.append("probe_dependency_preparation_started", {"official": False})
    try:
        source_hash = admission_hash(prepared_source)
        source, repo = load_source(prepared_source, public.repository.url,
                                  public.repository.base_commit,
                                  expected_hash=source_hash)
        roots = list(source_roots or [])
        if resolve:
            ProbeDependencyIdentity.public_import_roots(roots)
            if len(roots) > 8:
                raise ContractError("probe import roots exceed the root bound")
        else:
            lock = WheelLock.model_validate(_read_json(wheel_lock))
            if lock.schema_version != "public-probe-wheel-lock-v1":
                raise ContractError("unsupported public wheel lock")
            lock_path = repo / lock.source_lock
            if not lock_path.resolve().is_relative_to(repo) or lock_path.is_symlink():
                raise ContractError("public dependency lock leaves the prepared source")
            raw_lock = lock_path.read_bytes()
            if sha256_bytes(raw_lock) != lock.source_lock_hash:
                raise ContractError("public dependency lock hash differs from the prepared source")
            packages = tomllib.loads(raw_lock.decode("utf-8")).get("package", [])
            locked = {
                (wheel["url"], wheel["hash"], wheel["size"])
                for package in packages
                if package.get("source") == {"registry": "https://pypi.org/simple"}
                for wheel in package.get("wheels", [])
            }
            if any((wheel.url, wheel.hash, wheel.size) not in locked for wheel in lock.wheels):
                raise ContractError("probe wheel is not pinned in the prepared public PyPI lock")
            lock_record = lock.model_dump(mode="json")
            selected, roots = lock.wheels, lock.source_roots
        for root in roots:
            if not (repo / root).is_dir() or not (repo / root).resolve().is_relative_to(repo):
                raise ContractError("probe import root is absent from the prepared source")
        uv = shutil.which("uv")
        if uv is None:
            raise ContractError("uv must already be installed to prepare public dependencies")
        if resolve:
            from patchloop.probe_dependency_resolution import resolve_dependencies

            lock_record, selected, packages = resolve_dependencies(
                repo=repo, source=source, source_hash=source_hash, output=output, uv=uv,
                groups=groups or [], extras=extras or [], source_roots=roots,
                selected_dependencies=selected_dependencies,
            )
        if sum(wheel.size for wheel in selected) > MAX_BYTES:
            raise ContractError("public wheel downloads exceed the size bound")
        wheels = output / "wheels"
        wheels.mkdir()
        paths = []
        for wheel in selected:
            destination = wheels / wheel.url.rsplit("/", 1)[-1]
            _download(wheel, destination)
            paths.append(str(destination))
        target = output / "site-packages"
        command = [uv, "pip", "install", "--offline", "--no-index", "--no-build", "--no-config",
                   "--no-cache", "--no-python-downloads", "--python", sys.executable,
                   "--python-version", "3.12", "--python-platform", "x86_64-manylinux_2_28",
                   "--link-mode", "copy", "--target", str(target), "--find-links", str(wheels),
                   *paths]
        if paths:
            result = subprocess.run(command, capture_output=True, timeout=120, check=False,
                                    env={key: os.environ[key] for key in
                                         ("PATH", "SystemRoot", "TEMP", "TMP")
                                         if key in os.environ})
        else:
            target.mkdir()
            result = subprocess.CompletedProcess([], 0, b"", b"No third-party wheels selected")
        ArtifactStore(output).write_text_immutable(output / "install.json", canonical_json({
            "argv": command if paths else [], "exit_code": result.returncode,
            "stdout": result.stdout.decode("utf-8", errors="replace")[-12_000:],
            "stderr": result.stderr.decode("utf-8", errors="replace")[-12_000:],
            "installer_hash": sha256_bytes(Path(uv).read_bytes()),
        }))
        if result.returncode:
            raise ContractError("offline public wheel installation failed; no descriptor published")
        # Replace install-local URL records with their already verified public wheel origins.
        origins = {wheel.url.rsplit("/", 1)[-1]: wheel for wheel in selected}
        for path in target.glob("*.dist-info/direct_url.json"):
            metadata = json.loads(path.read_bytes())
            filename = urlsplit(metadata["url"]).path.rsplit("/", 1)[-1]
            wheel = origins[filename]
            path.write_text(canonical_json({"url": wheel.url, "archive_info": {
                "hash": wheel.hash.replace(":", "=", 1)}}), encoding="utf-8")
        workspace_metadata = _workspace_metadata(repo, packages, roots,
                                                 source.git_commit, target)
        generated = probe_project_files.prepare(repo, workspace_metadata, roots, output)
        if generated and _inventory(output / probe_project_files.DIRECTORY) != {
                item["path"]: item["content_hash"] for item in generated}:
            raise ContractError("generated project files changed before publication")
        files = _inventory(target)
        content_hash = _content_hash(files, generated)
        descriptor = {
            "schema_version": "prepared-probe-dependencies-v1", "python": "3.12",
            "platform": "linux/amd64", "image": PROBE_IMAGE,
            "repository_url": public.repository.url, "base_commit": public.repository.base_commit,
            "prepared_source_content_hash": source.content_hash,
            "source_roots": roots, "wheel_lock": lock_record,
            "workspace_metadata": workspace_metadata,
            **({"generated_project_files": generated} if generated else {}),
            "content_hash": content_hash, "files": files,
        }
        manifest = output / MANIFEST
        body = canonical_json(descriptor) + "\n"
        journal.append("probe_dependencies_prepared", {
            "manifest_hash": sha256_bytes(body.encode()), "content_hash": content_hash,
            "wheel_count": len(selected), "file_count": len(files), "official": False,
            **({"generated_project_file_count": len(generated)} if generated else {}),
        })
        ArtifactStore(output).write_text_immutable(manifest, body)
        return manifest
    except Exception as exc:
        journal.append("probe_dependency_preparation_failed", {
            "error_type": type(exc).__name__, "message": str(exc)[:1000], "official": False,
        })
        if isinstance(exc, ContractError):
            raise
        raise ContractError(
            "public dependency preparation failed; incomplete output is unusable",
        ) from exc
