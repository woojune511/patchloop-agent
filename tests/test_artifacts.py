from __future__ import annotations

import pytest

from patchloop.artifacts import ArtifactStore
from patchloop.errors import RecoveryError


def test_content_addressed_write_reuses_only_verified_bytes(tmp_path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")

    first = store.put_bytes(b"stable evidence")
    second = store.put_bytes(b"stable evidence")

    assert first.path == second.path
    assert first.content_hash == second.content_hash


def test_content_addressed_write_rejects_corrupt_existing_object(
    tmp_path,
) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    artifact = store.put_bytes(b"stable evidence")
    artifact_path = tmp_path / "artifacts" / "objects" / "sha256"
    artifact_path = artifact_path / artifact.content_hash[7:9]
    artifact_path = artifact_path / artifact.content_hash[9:]
    artifact_path.write_bytes(b"corrupt")

    with pytest.raises(RecoveryError, match="failed integrity check"):
        store.put_bytes(b"stable evidence")
