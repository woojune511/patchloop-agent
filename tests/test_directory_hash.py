from __future__ import annotations

from patchloop.runtime import repository_root
from patchloop.util import directory_hash


def test_snapshot_hash_is_stable_across_host_path_ordering() -> None:
    snapshot = repository_root() / "fixtures/repositories/mini-data-utils"

    assert directory_hash(snapshot) == (
        "sha256:ea86e87d65632d2cadc0a65066bdd1fcdfb66ef3799ff4fed85ea1c2626a3d67"
    )
