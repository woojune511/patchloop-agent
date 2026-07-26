"""Clean workspace creation and Git patch inspection."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from patchloop.errors import ContractError
from patchloop.util import directory_hash, sha256_bytes

ALLOWED_REMOTE_REPOSITORIES = {
    "https://github.com/agronholm/anyio.git",
    "https://github.com/agronholm/anyio",
    "https://github.com/Delgan/loguru.git",
    "https://github.com/Delgan/loguru",
    "https://github.com/astanin/python-tabulate.git",
    "https://github.com/astanin/python-tabulate",
    "https://github.com/huggingface/huggingface_hub.git",
    "https://github.com/huggingface/huggingface_hub",
    "https://github.com/getmoto/moto.git",
    "https://github.com/getmoto/moto",
    "https://github.com/pdm-project/pdm.git",
    "https://github.com/pdm-project/pdm",
    "https://github.com/pytest-dev/pyfakefs.git",
    "https://github.com/pytest-dev/pyfakefs",
    "https://github.com/tox-dev/tox.git",
    "https://github.com/tox-dev/tox",
}


@dataclass(frozen=True)
class DiffSummary:
    changed_files: list[str]
    added_lines: int
    deleted_lines: int
    patch: str

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
        target = self.workspace_root / run_id / "repo"
        if target.exists():
            raise ContractError(f"workspace already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if repository_url in ALLOWED_REMOTE_REPOSITORIES:
            if not expected_revision or len(expected_revision) != 40:
                raise ContractError("remote repository revision must be a full 40-character commit")
            clone = subprocess.run(
                ["git", "clone", "--quiet", "--no-checkout", repository_url, str(target)],
                capture_output=True,
                text=True,
                check=False,
            )
            if clone.returncode != 0:
                raise ContractError(f"audited remote clone failed: {clone.stderr.strip()}")
            _git(target, "checkout", "--quiet", "--detach", expected_revision)
            actual_revision = _git(target, "rev-parse", "HEAD").stdout.strip()
            if actual_revision != expected_revision:
                raise ContractError(
                    f"remote checkout mismatch: expected {expected_revision}, got {actual_revision}"
                )
            return target
        if not repository_url.startswith("snapshot://"):
            raise ContractError(f"repository URL is not allowlisted: {repository_url}")
        source = self.resolve_repository(repository_url)
        actual_revision = directory_hash(source)
        if expected_revision and expected_revision != actual_revision:
            raise ContractError(
                "snapshot content hash does not match repository.base_commit: "
                f"expected {expected_revision}, got {actual_revision}"
            )
        shutil.copytree(source, target)
        _git(target, "init", "-q")
        _git(target, "config", "user.email", "patchloop@example.invalid")
        _git(target, "config", "user.name", "PatchLoop Evaluator")
        _git(target, "add", ".")
        _git(target, "commit", "-qm", "audited base snapshot")
        return target

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
    def diff_summary(workspace: Path) -> DiffSummary:
        patch = _git(workspace, "diff", "--no-ext-diff", "--binary").stdout
        numstat = _git(workspace, "diff", "--numstat").stdout
        changed_files: list[str] = []
        added = deleted = 0
        for line in numstat.splitlines():
            add_text, delete_text, path = line.split("\t", 2)
            changed_files.append(path.replace("\\", "/"))
            if add_text.isdigit():
                added += int(add_text)
            if delete_text.isdigit():
                deleted += int(delete_text)
        return DiffSummary(changed_files, added, deleted, patch)
