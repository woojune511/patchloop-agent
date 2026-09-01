"""Small repository identities shared by the active runtime."""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path


def repository_root() -> Path:
    return Path(__file__).resolve().parent.parent


def git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "uncommitted"


def make_run_id(prefix: str = "dev") -> str:
    return f"run_{prefix}_{uuid.uuid4().hex[:16]}"
