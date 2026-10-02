import json

import pytest

from diagnostics.swebench_lite_native import (
    load_predictions,
    restore_transport_bytes,
    validate_rows,
)


@pytest.mark.parametrize("count", [1, 3, 20])
def test_native_roster_binds_each_unique_instance_at_any_batch_size(count):
    image = "example/image@sha256:" + "a" * 64
    rows = [{"instance_id": str(i), "image": image} for i in range(count)]
    assert validate_rows(rows) == {image}


@pytest.mark.parametrize("rows", [[], [{"instance_id": "a", "image": "image:latest"}],
    [{"instance_id": "a", "image": "image@sha256:bad"}],
    [{"instance_id": "a", "image": "image@sha256:" + "a" * 64}] * 2])
def test_native_roster_rejects_empty_duplicate_or_unpinned_rows(rows):
    with pytest.raises(ValueError):
        validate_rows(rows)


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


def test_predictions_preserve_submitted_patch_and_allow_unsubmitted_tasks(tmp_path):
    path = tmp_path / "predictions.jsonl"
    patch = "diff --git a/x b/x\n+exact submitted bytes\n"
    path.write_text(json.dumps({"instance_id": "one", "model_patch": patch}) + "\n")
    assert load_predictions(path, {"one", "two"}) == {"one": patch}


@pytest.mark.parametrize("kind", ["empty", "blank_patch", "unknown", "duplicate"])
def test_predictions_reject_missing_or_misbound_submissions(tmp_path, kind):
    rows = [{"instance_id": "unknown" if kind == "unknown" else "one",
             "model_patch": "" if kind == "blank_patch" else "patch"}]
    if kind == "empty":
        rows = []
    if kind == "duplicate":
        rows *= 2
    path = tmp_path / "predictions.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows))
    with pytest.raises(ValueError):
        load_predictions(path, {"one"})
