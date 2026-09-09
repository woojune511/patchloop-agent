"""Small repository identities shared by the active runtime."""

from __future__ import annotations

import uuid
from pathlib import Path

from patchloop.deadline import ExecutionDeadline
from patchloop.git_execution import run_git
from patchloop.util import raw_file_set_hash


def repository_root() -> Path:
    return Path(__file__).resolve().parent.parent


def runtime_content_paths(root: Path | None = None) -> list[str]:
    selected_root = (root or repository_root()).resolve()
    paths = [
        path.relative_to(selected_root).as_posix()
        for path in (selected_root / "patchloop").rglob("*.py")
        if path.is_file()
    ]
    paths.extend(
        ["pyproject.toml", "uv.lock", "docker/probe_runner.py", "docker/Dockerfile.sandbox"]
    )
    return sorted(paths)


def runtime_content_hash(root: Path | None = None) -> str:
    selected_root = (root or repository_root()).resolve()
    return raw_file_set_hash(selected_root, runtime_content_paths(selected_root))


def git_commit(*, deadline: ExecutionDeadline | None = None) -> str:
    result = run_git(repository_root(), "rev-parse", "HEAD", check=False, deadline=deadline)
    return result.stdout.strip() if result.returncode == 0 else "uncommitted"


def make_run_id(prefix: str = "dev") -> str:
    return f"run_{prefix}_{uuid.uuid4().hex[:16]}"
