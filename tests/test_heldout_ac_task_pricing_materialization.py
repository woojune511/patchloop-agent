from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.evals import heldout_ac_task_pricing_materialization as materialization
from patchloop.evals.heldout_ac_task_pricing_materialization import (
    OUTPUT_PATH,
    PLAN_HASH,
    PRICING_HASH,
    R5_CONTENT_HASH,
    R5_FILE_BYTES,
    R5_FILE_SHA256,
    R5_PATH,
    R5_SOURCE_HASH,
    R5_TASK_BINDINGS_HASH,
    R10_CONTENT_HASH,
    R10_CONTRACT_SOURCE_HASH,
    R10_FILE_BYTES,
    R10_FILE_SHA256,
    R10_PATH,
    R10_SOURCE_HASH,
    HeldoutACTaskPricingMaterialization,
    _build_candidate,
    run_heldout_ac_task_pricing_materialization,
    validate_heldout_ac_task_pricing_materialization,
)
from patchloop.util import sha256_bytes, sha256_json

ROOT = Path(__file__).resolve().parents[1]


def _candidate() -> HeldoutACTaskPricingMaterialization:
    return _build_candidate(
        ROOT,
        recorded_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
    )


def test_offline_candidate_reuses_exact_r5_projections_and_binds_r10() -> None:
    candidate = _candidate()

    assert candidate.schema_version == "heldout-ac-task-pricing-materialization-v6"
    assert candidate.materialization_id.endswith("20260815-r6")
    assert candidate.binding_source_predecessor.path.endswith(
        "heldout-ac-binding-adapter-source-qualification-r10.json"
    )
    assert candidate.materialization_predecessor.disposition == (
        "invalidated-by-binding-adapter-r10-successor"
    )
    assert candidate.binding_source_predecessor.file_bytes == R10_FILE_BYTES
    assert candidate.binding_source_predecessor.file_sha256 == R10_FILE_SHA256
    assert candidate.binding_source_predecessor.source_qualification_hash == R10_CONTENT_HASH
    assert candidate.binding_source_predecessor.source_hash == R10_SOURCE_HASH
    assert (
        candidate.binding_source_predecessor.contract_source_qualification_hash
        == R10_CONTRACT_SOURCE_HASH
    )
    assert candidate.materialization_predecessor.content_hash == R5_CONTENT_HASH
    assert candidate.materialization_predecessor.source_hash == R5_SOURCE_HASH
    assert candidate.materialization_predecessor.task_bindings_hash == R5_TASK_BINDINGS_HASH
    assert candidate.materialization_predecessor.pricing_binding_hash == PRICING_HASH
    assert len(candidate.task_bindings) == 12
    assert len({item.task.task_id for item in candidate.task_bindings}) == 12
    assert sum(item.task.role == "core-same-repo" for item in candidate.task_bindings) == 6
    assert sum(item.task.role == "core-cross-repo" for item in candidate.task_bindings) == 6
    assert candidate.task_evaluator_plan_content_hash == PLAN_HASH
    assert all(item.task_private_marker_count > 0 for item in candidate.task_bindings)
    assert all(item.runtime_secret_markers_materialized == 0 for item in candidate.task_bindings)
    assert all(
        item.final_evaluator_contract_materialized is False for item in candidate.task_bindings
    )
    assert candidate.pricing.price_nanos_per_token == {
        "uncached_input": 750,
        "cached_input": 75,
        "cache_write_input": 750,
        "output": 4_500,
    }
    assert candidate.pricing.max_cumulative_input_tokens_per_run == 1_000_000
    assert candidate.pricing.max_cumulative_output_tokens_per_run == 100_000
    assert candidate.pricing.per_run_reserve_nanos == 1_200_000_000
    assert candidate.pricing.full_schedule_reserve_nanos == 57_600_000_000
    assert candidate.pricing.hard_cap_nanos == 60_000_000_000
    assert candidate.authority.provider_calls_made == 0
    assert candidate.authority.execution_candidate_authorized is False
    assert candidate.authority.predecessor_official_pricing_public_get_requests == 1
    assert candidate.authority.added_official_pricing_public_get_requests == 0
    assert candidate.pricing.content_hash == PRICING_HASH
    assert candidate.authority.added_distinct_task_packages_materialized == 0
    assert candidate.authority.added_task_package_files_opened == 0
    assert candidate.authority.added_task_evaluator_templates_materialized == 0
    r5 = json.loads((ROOT / R5_PATH).read_bytes())
    assert [item.model_dump(mode="json") for item in candidate.task_bindings] == r5["task_bindings"]
    assert candidate.pricing.model_dump(mode="json") == r5["pricing"]


def test_retained_r1_pricing_reuse_makes_no_added_public_get(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import patchloop.evals.d136_fixed_pricing_capture as pricing_capture

    def unexpected_get(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("R6 materialization must not make a pricing GET")

    monkeypatch.setattr(pricing_capture, "capture_official_pricing_evidence", unexpected_get)
    candidate = _candidate()

    assert candidate.authority.official_pricing_public_get_authorized is False
    assert candidate.authority.added_official_pricing_public_get_requests == 0


def test_cost_only_successor_never_reopens_a_task_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_task_open(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("R6 binding-only successor must not reopen held-out task packages")

    def unexpected_private_projection(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("R6 binding-only successor must not read private task files")

    monkeypatch.setattr(materialization, "load_task_package", unexpected_task_open)
    monkeypatch.setattr(materialization, "_task_file_projection", unexpected_private_projection)
    candidate = _candidate()

    assert len(candidate.task_bindings) == 12
    assert candidate.authority.evaluator_side_task_package_access_authorized is False


def test_rehashed_pricing_or_task_projection_drift_fails_closed() -> None:
    candidate = _candidate()
    pricing_drift = candidate.model_dump(mode="json")
    pricing_drift["pricing"]["full_schedule_reserve_nanos"] += 1
    pricing_body = {
        key: value for key, value in pricing_drift["pricing"].items() if key != "content_hash"
    }
    pricing_drift["pricing"]["content_hash"] = sha256_json(pricing_body)
    pricing_drift["content_hash"] = sha256_json(
        {key: value for key, value in pricing_drift.items() if key != "content_hash"}
    )

    with pytest.raises(ValidationError):
        HeldoutACTaskPricingMaterialization.model_validate_json(json.dumps(pricing_drift))

    task_drift = candidate.model_dump(mode="json")
    task_drift["task_bindings"][0]["runtime_secret_markers_materialized"] = 1
    task_drift["task_bindings"][0]["content_hash"] = sha256_json(
        {
            key: value
            for key, value in task_drift["task_bindings"][0].items()
            if key != "content_hash"
        }
    )
    task_drift["task_bindings_hash"] = sha256_json(task_drift["task_bindings"])
    task_drift["content_hash"] = sha256_json(
        {key: value for key, value in task_drift.items() if key != "content_hash"}
    )

    with pytest.raises(ValidationError):
        HeldoutACTaskPricingMaterialization.model_validate_json(json.dumps(task_drift))


def test_r5_and_r10_are_byte_preserved_and_checked_in_r6_is_idempotent() -> None:
    sealed_r5 = ROOT / R5_PATH
    r5_raw = sealed_r5.read_bytes()
    assert len(r5_raw) == R5_FILE_BYTES
    assert sha256_bytes(r5_raw) == R5_FILE_SHA256
    sealed_r10 = ROOT / R10_PATH
    r10_raw = sealed_r10.read_bytes()
    assert len(r10_raw) == R10_FILE_BYTES
    assert sha256_bytes(r10_raw) == R10_FILE_SHA256

    selected = ROOT / OUTPUT_PATH
    before = selected.read_bytes()
    before_mtime = selected.stat().st_mtime_ns
    validated = validate_heldout_ac_task_pricing_materialization(repository=ROOT)
    rerun = run_heldout_ac_task_pricing_materialization(repository=ROOT)

    assert validated == rerun
    assert validated["added_pricing_public_get_requests"] == 0
    assert validated["added_task_package_files_opened"] == 0
    assert selected.read_bytes() == before
    assert selected.stat().st_mtime_ns == before_mtime
    assert sealed_r5.read_bytes() == r5_raw
    assert sealed_r10.read_bytes() == r10_raw
