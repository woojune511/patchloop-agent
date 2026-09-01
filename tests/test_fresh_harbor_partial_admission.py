from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.evals.fresh_harbor_partial_admission import (
    EXPECTED_ROWS,
    PREREGISTRATION_PATH,
    SOURCE_QUALIFICATION_PATH,
    VARIANTS_PER_TASK,
    FreshHarborPartialAdmissionError,
    PartialAdmissionPreregistration,
    _parse_patch,
    _task_plan,
    artifact_bytes,
    build_source_qualification,
    load_preregistration,
    load_source_qualification,
    sha256_standard_library,
)
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _synthetic_patch() -> bytes:
    body = [
        b"diff --git a/example.py b/example.py\n",
        b"index 1111111..2222222 100644\n",
        b"--- a/example.py\n",
        b"+++ b/example.py\n",
        b"@@ -1,9 +1,13 @@\n",
        b" context-1\n",
        b"-old-1\n",
        b"+new-1\n",
        b"+new-2\n",
        b" context-2\n",
        b"-old-2\n",
        b"+new-3\n",
        b"+new-4\n",
        b" context-3\n",
        b"-old-3\n",
        b"+new-5\n",
        b"+new-6\n",
        b" context-4\n",
        b"-old-4\n",
        b"+new-7\n",
        b"+new-8\n",
        b" context-5\n",
    ]
    return b"".join(body)


def test_deterministic_task_plan_has_12_unique_structurally_valid_variants() -> None:
    raw = _synthetic_patch()
    first = _task_plan("synthetic__task-1", "synthetic/task", raw)
    second = _task_plan("synthetic__task-1", "synthetic/task", raw)

    assert first == second
    assert len(first.variants) == VARIANTS_PER_TASK
    assert first.eligible_atomic_unit_count >= VARIANTS_PER_TASK
    assert first.unique_generated_variant_count >= VARIANTS_PER_TASK
    assert len({item.generated_patch.file_sha256 for item in first.variants}) == 12
    assert all(item.patch_body_persisted == 0 for item in first.variants)


def test_single_change_hunk_and_no_newline_adjacent_unit_are_ineligible() -> None:
    raw = b"".join(
        (
            b"diff --git a/a.py b/a.py\n",
            b"--- a/a.py\n",
            b"+++ b/a.py\n",
            b"@@ -1,1 +1,1 @@\n",
            b"-before\n",
            b"+after\n",
            b"\\ No newline at end of file\n",
        )
    )
    _lines, _hunks, units = _parse_patch(
        raw,
        task_id="synthetic__task-2",
        reference_sha256=sha256_bytes(raw),
    )

    assert len(units) == 1
    assert units[0].operation == "retain-deleted-line"


def test_malformed_hunk_counts_fail_closed() -> None:
    raw = b"".join(
        (
            b"diff --git a/a.py b/a.py\n",
            b"--- a/a.py\n",
            b"+++ b/a.py\n",
            b"@@ -1,2 +1,2 @@\n",
            b"-before\n",
            b"+after\n",
        )
    )
    with pytest.raises(FreshHarborPartialAdmissionError, match="body count differs"):
        _parse_patch(
            raw,
            task_id="synthetic__task-3",
            reference_sha256=sha256_bytes(raw),
        )


def test_source_qualification_is_no_call_and_binds_current_source() -> None:
    value = build_source_qualification(REPOSITORY)

    assert value.authority.source_qualified is True
    assert value.authority.evaluator_private_reference_patches_read == 0
    assert value.authority.docker_calls == value.authority.provider_calls == 0
    assert value.authority.execution_authorized is False
    assert len(value.source_files) == 3
    assert len(value.validation_files) == 1


def test_checked_in_source_and_preregistration_are_exact_and_execution_closed() -> None:
    qualification, qualification_raw = load_source_qualification(REPOSITORY)
    preregistration, preregistration_raw = load_preregistration(REPOSITORY)

    assert artifact_bytes(qualification) == qualification_raw
    assert artifact_bytes(preregistration) == preregistration_raw
    assert preregistration.expected_rows == EXPECTED_ROWS
    assert len(preregistration.task_plans) == 12
    assert all(len(item.variants) == 12 for item in preregistration.task_plans)
    assert preregistration.authority.retained_missing_receipts_replayed is False
    assert preregistration.authority.execution_authorized is False
    assert b"diff --git" not in preregistration_raw
    assert b"@@ " not in preregistration_raw


def test_rehashed_design_or_task_plan_overclaim_is_rejected() -> None:
    value, _raw = load_preregistration(REPOSITORY)
    body = value.model_dump(mode="json")
    body["design"]["adaptation"]["automatic-retry"] = True
    body["content_hash"] = sha256_json(
        {key: item for key, item in body.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError, match="design differs"):
        PartialAdmissionPreregistration.model_validate(body)

    body = value.model_dump(mode="json")
    body["task_plans"][0]["eligible_atomic_unit_count"] += 1
    body["content_hash"] = sha256_json(
        {key: item for key, item in body.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError):
        PartialAdmissionPreregistration.model_validate(body)


def test_append_only_outputs_are_not_task_repository_paths() -> None:
    assert SOURCE_QUALIFICATION_PATH.startswith("reports/fresh-panel/artifacts/")
    assert PREREGISTRATION_PATH.startswith("experiments/")
    assert not SOURCE_QUALIFICATION_PATH.startswith("tasks/")
    assert not PREREGISTRATION_PATH.startswith("tasks/")


def test_hash_oracle_matches_standard_library() -> None:
    raw = json.dumps({"design": "deterministic"}, sort_keys=True).encode("utf-8")
    assert sha256_standard_library(raw) == sha256_bytes(raw)
