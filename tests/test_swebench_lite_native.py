import pytest

from diagnostics.swebench_lite_native import restore_transport_bytes


def test_windows_transport_restores_exact_upstream_bytes(tmp_path):
    path = tmp_path / "eval.sh"
    canonical = b"#!/bin/bash\nprintf 'original test'\n"
    path.write_bytes(canonical.replace(b"\n", b"\r\n"))
    restore_transport_bytes(path, canonical)
    assert path.read_bytes() == canonical


def test_transport_rejects_content_edits_without_overwriting(tmp_path):
    path = tmp_path / "eval.sh"
    changed = b"#!/bin/bash\nprintf 'different test'\n"
    path.write_bytes(changed)
    with pytest.raises(ValueError, match="beyond host newlines"):
        restore_transport_bytes(path, b"#!/bin/bash\nprintf 'original test'\n")
    assert path.read_bytes() == changed
