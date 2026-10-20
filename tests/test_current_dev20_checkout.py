"""Git-recorded development packages preserve their raw-byte inventory identities."""

import io
import subprocess
import tarfile

import pytest

from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package

PANEL = "tasks/dev-train/current-dev20"


@pytest.fixture(scope="module")
def recorded_panel(tmp_path_factory):
    """Read committed blobs without a clone, provider or evaluator execution."""
    archive = subprocess.run(
        ["git", "archive", "--format=tar", "HEAD", "--", PANEL],
        cwd=repository_root(),
        check=True,
        capture_output=True,
    ).stdout
    destination = tmp_path_factory.mktemp("current-dev20-recorded")
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as contents:
        members = contents.getmembers()
        assert all(member.isdir() or member.isfile() for member in members)
        contents.extractall(destination, members=members, filter="data")
    return destination / PANEL


@pytest.mark.parametrize("row", range(1, 21))
def test_recorded_current_dev20_package_matches_working_identity(recorded_panel, row):
    # The loader validates the opaque reference/hidden inventory hashes; do not
    # print, parse, execute or project those assets into a solver request here.
    current = load_task_package(repository_root() / PANEL / str(row))
    recorded = load_task_package(recorded_panel / str(row))
    assert recorded.public_spec_hash == current.public_spec_hash
    assert recorded.private_spec_hash == current.private_spec_hash
    assert recorded.task_content_hash == current.task_content_hash
