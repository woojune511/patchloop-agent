"""Explicit, immutable source preparation for independent offline workspaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import StrictModel
from patchloop.deadline import ExecutionDeadline
from patchloop.errors import ContractError
from patchloop.git_execution import run_git
from patchloop.util import canonical_json, directory_hash, sha256_bytes

MANIFEST_NAME = "prepared-source.json"
REPO_PATH = "workspaces/source/repo"
MAX_MANIFEST_BYTES = 16_384


class PreparedSource(StrictModel):
    schema_version: Literal["prepared-source-v1"] = "prepared-source-v1"
    repository_url: str
    base_commit: str
    git_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    git_tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    repo_path: Literal["workspaces/source/repo"] = REPO_PATH


def manifest_bytes(path: Path) -> bytes:
    try:
        if path.is_symlink() or not path.is_file():
            raise ContractError("prepared source manifest is missing or not a regular file")
        with path.open("rb") as stream:
            data = stream.read(MAX_MANIFEST_BYTES + 1)
        if len(data) > MAX_MANIFEST_BYTES:
            raise ContractError("prepared source manifest exceeds its size bound")
        return data
    except OSError as exc:
        raise ContractError("prepared source manifest cannot be read") from exc


def admission_hash(path: Path | None) -> str | None:
    """Bind available bytes; a bad/missing descriptor gets a normal preflight terminal."""
    if path is None:
        return None
    try:
        return sha256_bytes(manifest_bytes(path))
    except ContractError:
        return None


def validate_checkout(
    repo: Path, source: PreparedSource, *, deadline: ExecutionDeadline | None = None,
) -> None:
    if not repo.is_dir() or repo.is_symlink() or not (repo / ".git").is_dir():
        raise ContractError("prepared source checkout is missing or invalid")
    git_dir = repo / ".git"
    if (git_dir.is_symlink() or (git_dir / "objects/info/alternates").exists()
            or list((git_dir / "objects/pack").glob("*.promisor"))):
        raise ContractError("prepared source must own its complete Git objects")
    commit = run_git(repo, "rev-parse", "HEAD", deadline=deadline).stdout.strip()
    tree = run_git(repo, "rev-parse", "HEAD^{tree}", deadline=deadline).stdout.strip()
    status = run_git(
        repo, "status", "--porcelain=v1", "--untracked-files=all", deadline=deadline,
    ).stdout
    if commit != source.git_commit or tree != source.git_tree or status:
        raise ContractError("prepared source is not the recorded clean Git checkout")
    if deadline is not None:
        deadline.check()
    if directory_hash(repo) != source.content_hash:
        raise ContractError("prepared source worktree content differs from its manifest")
    if deadline is not None:
        deadline.check()


def load_source(
    path: Path, repository_url: str, base_commit: str, *, expected_hash: str | None,
    deadline: ExecutionDeadline | None = None,
) -> tuple[PreparedSource, Path]:
    from patchloop.repository import ALLOWED_REMOTE_REPOSITORIES

    if deadline is not None:
        deadline.check()
    data = manifest_bytes(path)
    if expected_hash is None or sha256_bytes(data) != expected_hash:
        raise ContractError("prepared source manifest differs from the admitted identity")
    try:
        source = PreparedSource.model_validate(json.loads(data))
    except (ValueError, ValidationError) as exc:
        raise ContractError("prepared source manifest is invalid") from exc
    if (source.repository_url, source.base_commit) != (repository_url, base_commit):
        raise ContractError("prepared source does not match the task repository and base")
    if repository_url in ALLOWED_REMOTE_REPOSITORIES:
        if source.git_commit != base_commit:
            raise ContractError("prepared remote source commit differs from the task base")
    elif repository_url.startswith("snapshot://"):
        name = repository_url[len("snapshot://"):]
        if (not name or "/" in name or "\\" in name or name in {".", ".."}
                or source.content_hash != base_commit):
            raise ContractError("prepared snapshot differs from the audited base")
    else:
        raise ContractError("prepared source repository URL is not allowlisted")
    root = path.resolve().parent
    repo = root / source.repo_path
    if repo.resolve() != repo or not repo.is_relative_to(root):
        raise ContractError("prepared source checkout must stay inside its manifest directory")
    validate_checkout(repo, source, deadline=deadline)
    return source, repo


def prepare_source(
    *, repository_url: str, base_commit: str, output: Path, fixture_root: Path,
    deadline: ExecutionDeadline | None = None,
) -> Path:
    from patchloop.repository import WorkspaceManager
    from patchloop.runtime import repository_root

    output = output.resolve()
    if output.is_relative_to(repository_root().resolve()):
        raise ContractError("prepared source output must be outside the PatchLoop repository")
    try:
        output.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        raise ContractError("prepared source output must be a new external directory") from exc
    # An incomplete preparation remains unpublishable; never reuse or replace its bytes.
    manager = WorkspaceManager(fixture_root, output / "workspaces")
    repo = manager.create("source", repository_url, base_commit, deadline=deadline)
    source = PreparedSource(
        repository_url=repository_url, base_commit=base_commit,
        git_commit=run_git(repo, "rev-parse", "HEAD", deadline=deadline).stdout.strip(),
        git_tree=run_git(repo, "rev-parse", "HEAD^{tree}", deadline=deadline).stdout.strip(),
        content_hash=directory_hash(repo),
    )
    actual_base = (
        source.content_hash if repository_url.startswith("snapshot://") else source.git_commit
    )
    if actual_base != base_commit:
        raise ContractError("prepared source changed during initial checkout")
    validate_checkout(repo, source, deadline=deadline)
    path = output / MANIFEST_NAME
    ArtifactStore(output).write_text_immutable(
        path, canonical_json(source.model_dump(mode="json")) + "\n",
    )
    return path
