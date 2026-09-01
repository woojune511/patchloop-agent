from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.evals.rapid_public_development_v24_qualification import (
    QUALIFICATION_PATH,
    build_rapid_public_development_v24_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def _stored() -> tuple[bytes, dict[str, object]]:
    target = ROOT / QUALIFICATION_PATH
    if not target.exists():
        pytest.skip("candidate-v29 qualification is materialized after offline gates")
    raw = target.read_bytes()
    return raw, json.loads(raw)


def test_candidate_v29_qualification_is_canonical_and_zero_call() -> None:
    raw, value = _stored()

    assert raw == qualification_bytes(value)
    assert value == build_rapid_public_development_v24_qualification(ROOT)
    assert sha256_bytes(raw).startswith("sha256:")
    assert value["status"] == "offline-qualified-awaiting-exact-paid-approval"
    assert value["candidate_specific_runtime_integrated"] is True
    assert value["candidate_created"] is True
    assert value["rehearsal_created"] is True
    assert value["paid_execution_authorized"] is False
    assert value["rehearsal"]["generation_count"] == 2
    assert value["rehearsal"]["byte_identical"] is True
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


def test_candidate_v29_qualification_binds_single_arm_and_promotion_floor() -> None:
    _, value = _stored()

    design = value["activation_design"]
    assert design["treatment"]["runtime_policy_version"] == "lean-harness-v25"
    assert design["rows"] == 3
    assert design["control_rows"] == 0
    assert design["comparative_effect_claim_allowed"] is False
    assert value["registered_admission"]["all_manifest_count"] == 3
    assert value["registered_admission"]["requires_row_capability"] is True
    assert value["promotion_criteria"]["valid_initial_plan_rows_min"] == 2
    assert value["promotion_criteria"]["first_mutation_rows_min"] == 2
    assert value["promotion_criteria"]["evaluator_reached_rows_min"] == 2
    assert value["recovery_contract"]["consumed_r20_retry_allowed"] is False
