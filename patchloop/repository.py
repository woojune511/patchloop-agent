"""Clean workspace creation and Git patch inspection."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from patchloop.errors import ContractError
from patchloop.util import directory_hash, safe_relative_path, sha256_bytes

ALLOWED_REMOTE_REPOSITORIES = {
    "https://github.com/agronholm/anyio.git",
    "https://github.com/agronholm/anyio",
    "https://github.com/Delgan/loguru.git",
    "https://github.com/Delgan/loguru",
    "https://github.com/dagster-io/dagster.git",
    "https://github.com/dagster-io/dagster",
    "https://github.com/astanin/python-tabulate.git",
    "https://github.com/astanin/python-tabulate",
    "https://github.com/python-babel/babel.git",
    "https://github.com/python-babel/babel",
    "https://github.com/huggingface/huggingface_hub.git",
    "https://github.com/huggingface/huggingface_hub",
    "https://github.com/kubeflow/pipelines.git",
    "https://github.com/kubeflow/pipelines",
    "https://github.com/holoviz/param.git",
    "https://github.com/holoviz/param",
    "https://github.com/olofk/fusesoc.git",
    "https://github.com/olofk/fusesoc",
    "https://github.com/getmoto/moto.git",
    "https://github.com/getmoto/moto",
    "https://github.com/youssofal/MTPLX.git",
    "https://github.com/youssofal/MTPLX",
    "https://github.com/pdm-project/pdm.git",
    "https://github.com/pdm-project/pdm",
    "https://github.com/pytest-dev/pyfakefs.git",
    "https://github.com/pytest-dev/pyfakefs",
    "https://github.com/tox-dev/tox.git",
    "https://github.com/tox-dev/tox",
    "https://github.com/tobymao/sqlglot.git",
    "https://github.com/tobymao/sqlglot",
}


@dataclass(frozen=True)
class DiffSummary:
    changed_files: list[str]
    added_lines: int
    deleted_lines: int
    patch: str
    untracked_files: list[str]

    @property
    def diff_lines(self) -> int:
        return self.added_lines + self.deleted_lines

    @property
    def patch_hash(self) -> str:
        return sha256_bytes(self.patch.encode("utf-8"))


def _git(workspace: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if check and result.returncode != 0:
        raise ContractError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    if result.stdout is None or result.stderr is None:
        raise ContractError(f"git {' '.join(args)} did not produce decodable UTF-8 output")
    return result


class WorkspaceManager:
    def __init__(self, fixture_root: str | Path, workspace_root: str | Path) -> None:
        self.fixture_root = Path(fixture_root).resolve()
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def resolve_repository(self, url: str) -> Path:
        prefix = "snapshot://"
        if not url.startswith(prefix):
            raise ContractError("MVP only accepts audited snapshot:// repositories")
        name = url[len(prefix) :]
        if not name or "/" in name or "\\" in name or name in {".", ".."}:
            raise ContractError(f"invalid snapshot repository name: {name!r}")
        source = (self.fixture_root / name).resolve()
        if source.parent != self.fixture_root or not source.is_dir():
            raise ContractError(f"unknown snapshot repository: {name}")
        return source

    def create(
        self, run_id: str, repository_url: str, expected_revision: str | None = None
    ) -> Path:
        run_root = (self.workspace_root / run_id).resolve()
        if run_root.parent != self.workspace_root:
            raise ContractError(f"invalid workspace run ID: {run_id!r}")
        target = run_root / "repo"
        staging = run_root / "repo.initializing"
        if target.exists() or target.is_symlink():
            raise ContractError(f"workspace already exists: {target}")
        run_root.mkdir(parents=True, exist_ok=True)
        if staging.is_symlink():
            raise ContractError(f"workspace staging path is an unexpected symlink: {staging}")
        if staging.exists():
            shutil.rmtree(staging)
        try:
            if repository_url in ALLOWED_REMOTE_REPOSITORIES:
                if (
                    not expected_revision
                    or re.fullmatch(r"[0-9a-f]{40}", expected_revision) is None
                ):
                    raise ContractError(
                        "remote repository revision must be a full 40-character commit"
                    )
                initialize = subprocess.run(
                    ["git", "init", "--quiet", str(staging)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if initialize.returncode != 0:
                    raise ContractError(
                        "audited remote checkout initialization failed: "
                        f"{initialize.stderr.strip()}"
                    )
                _git(staging, "config", "core.longpaths", "true")
                _git(staging, "remote", "add", "origin", repository_url)
                fetch = _git(
                    staging,
                    "fetch",
                    "--quiet",
                    "--no-tags",
                    "--depth",
                    "1",
                    "origin",
                    expected_revision,
                    check=False,
                )
                if fetch.returncode != 0:
                    raise ContractError(
                        "audited remote revision is unavailable: "
                        f"exact-SHA fetch failed with {fetch.stderr.strip()!r}"
                    )
                _git(staging, "checkout", "--quiet", "--detach", "FETCH_HEAD")
                actual_revision = _git(
                    staging,
                    "rev-parse",
                    "HEAD",
                ).stdout.strip()
                if actual_revision != expected_revision:
                    raise ContractError(
                        "remote checkout mismatch: expected "
                        f"{expected_revision}, got {actual_revision}"
                    )
            else:
                if not repository_url.startswith("snapshot://"):
                    raise ContractError(f"repository URL is not allowlisted: {repository_url}")
                source = self.resolve_repository(repository_url)
                actual_revision = directory_hash(source)
                if expected_revision and expected_revision != actual_revision:
                    raise ContractError(
                        "snapshot content hash does not match "
                        "repository.base_commit: "
                        f"expected {expected_revision}, got {actual_revision}"
                    )
                shutil.copytree(source, staging)
                _git(staging, "init", "-q")
                _git(
                    staging,
                    "config",
                    "user.email",
                    "patchloop@example.invalid",
                )
                _git(
                    staging,
                    "config",
                    "user.name",
                    "PatchLoop Evaluator",
                )
                _git(staging, "add", ".")
                _git(staging, "commit", "-qm", "audited base snapshot")
            os.replace(staging, target)
        except BaseException:
            if staging.exists() and not staging.is_symlink():
                shutil.rmtree(staging)
            raise
        return target

    def validate_pristine(
        self,
        workspace: str | Path,
        repository_url: str,
        expected_revision: str,
    ) -> None:
        """Prove an eventless/pre-checkpoint workspace is the manifest base."""

        resolved = self.validate_managed_workspace(workspace)
        status = _git(
            resolved,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ).stdout
        if status:
            raise ContractError("pre-checkpoint workspace is not a clean base checkout")
        if repository_url.startswith("snapshot://"):
            actual_revision = directory_hash(resolved)
        elif repository_url in ALLOWED_REMOTE_REPOSITORIES:
            actual_revision = _git(
                resolved,
                "rev-parse",
                "HEAD",
            ).stdout.strip()
        else:
            raise ContractError(f"repository URL is not allowlisted: {repository_url}")
        if actual_revision != expected_revision:
            raise ContractError(
                "pre-checkpoint workspace does not match the immutable "
                f"base revision: {actual_revision} != {expected_revision}"
            )

    def validate_managed_workspace(
        self,
        workspace: str | Path,
    ) -> Path:
        """Reject replaced workspace roots before reading or mutating them."""

        target = Path(workspace).absolute()
        try:
            relative = target.relative_to(self.workspace_root)
        except ValueError as exc:
            raise ContractError(
                "workspace root is outside the managed workspace directory"
            ) from exc
        if len(relative.parts) != 2 or relative.parts[-1] != "repo":
            raise ContractError("workspace root does not have the managed run layout")
        cursor = self.workspace_root
        root_is_junction = bool(getattr(cursor, "is_junction", lambda: False)())
        if cursor.is_symlink() or root_is_junction:
            raise ContractError("managed workspace root is a symlink or junction")
        for part in relative.parts:
            cursor = cursor / part
            is_junction = bool(getattr(cursor, "is_junction", lambda: False)())
            if cursor.is_symlink() or is_junction:
                raise ContractError("workspace path contains a symlink or junction")
        resolved = target.resolve()
        if not resolved.is_dir() or not resolved.is_relative_to(self.workspace_root):
            raise ContractError("workspace root is outside the managed workspace directory")
        return resolved

    def read_base_file(
        self,
        workspace: str | Path,
        relative_path: str,
    ) -> bytes:
        """Read one exact file from Git HEAD, never from the mutable worktree."""

        resolved = self.validate_managed_workspace(workspace)
        normalized = safe_relative_path(
            relative_path,
            field_name="base revision file path",
        )
        result = subprocess.run(
            ["git", "show", f"HEAD:{normalized}"],
            cwd=resolved,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", errors="replace").strip()
            raise ContractError(
                f"public review base revision file is unavailable: {normalized!r}: {detail}"
            )
        return result.stdout

    @staticmethod
    def apply_patch(workspace: Path, patch_path: str | Path) -> str:
        content = Path(patch_path).read_bytes()
        digest = sha256_bytes(content)
        if not content.strip():
            return digest
        result = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", str(Path(patch_path).resolve())],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise ContractError(f"patch application failed: {result.stderr.strip()}")
        return digest

    @staticmethod
    def untracked_files(workspace: Path) -> list[str]:
        output = _git(
            workspace,
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
        ).stdout
        return sorted(path.replace("\\", "/") for path in output.split("\0") if path)

    @staticmethod
    def diff_summary(workspace: Path) -> DiffSummary:
        patch = _git(
            workspace,
            "diff",
            "HEAD",
            "--no-ext-diff",
            "--binary",
        ).stdout
        numstat = _git(workspace, "diff", "HEAD", "--numstat").stdout
        changed_files: list[str] = []
        added = deleted = 0
        for line in numstat.splitlines():
            add_text, delete_text, path = line.split("\t", 2)
            changed_files.append(path.replace("\\", "/"))
            if add_text.isdigit():
                added += int(add_text)
            if delete_text.isdigit():
                deleted += int(delete_text)
        return DiffSummary(
            changed_files,
            added,
            deleted,
            patch,
            WorkspaceManager.untracked_files(workspace),
        )
