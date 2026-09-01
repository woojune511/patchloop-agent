from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.evals.rapid_public_development_v22_qualification import (
    QUALIFICATION_PATH,
    build_rapid_public_development_v22_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def _stored() -> tuple[bytes, dict[str, object]]:
    target = ROOT / QUALIFICATION_PATH
    if not target.exists():
        pytest.skip("candidate-v27 qualification is materialized after offline source gates")
    raw = target.read_bytes()
    return raw, json.loads(raw)


def test_candidate_v27_qualification_is_canonical_and_zero_call() -> None:
    raw, value = _stored()

    assert raw == qualification_bytes(value)
    assert value == build_rapid_public_development_v22_qualification(ROOT)
    assert sha256_bytes(raw).startswith("sha256:")
    assert value["status"] == "offline-qualified"
    assert value["candidate_specific_runtime_integrated"] is True
    assert value["candidate_created"] is True
    assert value["rehearsal_created"] is True
    assert value["paid_execution_authorized"] is False
    assert all(
        value["evidence_boundary"][key] == 0
        for key in (
            "provider_calls",
            "docker_calls",
            "task_calls",
            "evaluator_calls",
            "visible_check_calls",
            "network_calls",
        )
    )


def test_candidate_v27_qualification_binds_v18_v22_and_driver() -> None:
    _, value = _stored()

    comparison = value["runtime_comparison"]
    assert comparison["control"]["runtime_policy_version"] == "lean-harness-v18"
    assert comparison["treatment"]["runtime_policy_version"] == "lean-harness-v22"
    assert comparison["balanced_interleaved_rows_per_variant"] == 3
    assert comparison["task_model_budget_evaluator_driver_equal"] is True
    assert comparison["single_policy_effect_attribution_allowed"] is False
    assert value["driver_qualification"]["successor_policy_version"] == (
        "append-only-row-settlement-driver-v2"
    )
    assert value["registered_admission"]["all_manifest_count"] == 6
    assert value["registered_admission"]["requires_row_capability"] is True
    assert value["recovery_contract"]["consumed_r18_retry_allowed"] is False
