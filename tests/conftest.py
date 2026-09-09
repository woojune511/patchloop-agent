from __future__ import annotations

import os
import re
import subprocess
import uuid
from pathlib import Path

import pytest

from patchloop.dev.contracts import DevLimits
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.task_loader import load_task_package


@pytest.fixture(autouse=True)
def require_explicit_real_docker_opt_in(monkeypatch):
    """A changed mock boundary must fail a unit test, not launch a real container."""
    if any(os.environ.get(name) == "1" for name in (
        "PATCHLOOP_TEST_REAL_EXECUTION", "PATCHLOOP_TEST_REAL_PROBES",
    )):
        return
    original = subprocess.Popen

    def guarded(command=None, *args, **kwargs):
        selected = kwargs.get("args", command)
        executable = (
            selected[0] if isinstance(selected, (list, tuple)) else str(selected).split()[0]
        )
        name = re.split(r"[/\\]", str(executable))[-1].lower()
        if name in {"docker", "docker.exe"}:
            pytest.fail("real Docker requires an explicit test opt-in; mock the launch boundary")
        return original(*args, **kwargs) if command is None else original(command, *args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", guarded)


@pytest.fixture
def smoke_package():
    return load_task_package(repository_root() / "tasks" / "smoke" / "csv-quoted-newline")


@pytest.fixture
def gateway_factory(tmp_path: Path, smoke_package):
    def build(*, sandbox=None):
        manager = WorkspaceManager(
            repository_root() / "fixtures" / "repositories",
            tmp_path / "workspaces",
        )
        workspace = manager.create(
            f"workspace_{uuid.uuid4().hex}",
            smoke_package.public.repository.url,
            smoke_package.public.repository.base_commit,
        )
        journal = DevJournal(tmp_path / "state", f"run_dev_{uuid.uuid4().hex[:16]}")
        gateway = DevToolGateway(
            workspace=workspace,
            public_task=smoke_package.public,
            sandbox=sandbox or LocalSandbox(),
            journal=journal,
            limits=DevLimits(),
        )
        return gateway, journal, workspace

    return build
