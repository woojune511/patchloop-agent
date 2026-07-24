from __future__ import annotations

import csv
from pathlib import Path

from patchloop.repository import ALLOWED_REMOTE_REPOSITORIES
from patchloop.task_loader import load_task_package

TASK = Path("tasks/dev-train/loguru-invalid-format-feedback")


def test_loguru_candidate_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(TASK)

    assert package.public.task_id == "loguru-invalid-format-feedback"
    assert package.public.repository.url == "https://github.com/Delgan/loguru.git"
    assert package.public.repository.base_commit == "2abeb0fa6d7be4b0455c6e0b580b1e9dab19005e"
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == ["loguru/_handler.py"]
    assert package.public.constraints.max_diff_lines == 60


def test_loguru_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(TASK)
    public_text = (TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_invalid_format_feedback.py" not in public_text
    assert "_make_key_error" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_loguru_candidate_is_traceable_to_swe_rebench_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(encoding="utf-8", newline="") as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["delgan__loguru-1451"]
    assert candidate["benchmark_revision"] == "ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b"
    assert candidate["base_commit"] == "2abeb0fa6d7be4b0455c6e0b580b1e9dab19005e"
    assert candidate["pr_url"] == "https://github.com/Delgan/loguru/pull/1451"
    assert candidate["status"] == "admission-running"
