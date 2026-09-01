from __future__ import annotations

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
