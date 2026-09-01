from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.evals.rapid_public_development_v25_qualification import (
    QUALIFICATION_PATH,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def _stored() -> tuple[bytes, dict[str, object]]:
    target = ROOT / QUALIFICATION_PATH
    if not target.exists():
        pytest.skip("candidate-v30 qualification is materialized after offline gates")
    raw = target.read_bytes()
    return raw, json.loads(raw)


def test_candidate_v30_qualification_is_canonical_and_zero_call() -> None:
    raw, value = _stored()

    assert raw == qualification_bytes(value)
    # Frozen preparation evidence, not a current-source rebuild of stopped R22.
    assert sha256_bytes(raw) == (
        "sha256:fe615a8ad3f7cdf6560c371558aeb99d4b565e7b3b95cb4898c7e80502cf209a"
    )
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


def test_candidate_v30_qualification_binds_equal_arms_package_and_promotion_floor() -> None:
    _, value = _stored()

    design = value["activation_design"]
    assert design["treatment"]["runtime_policy_version"] == "lean-harness-v26"
    assert design["control"]["runtime_policy_version"] == "lean-harness-v25"
    assert design["rows"] == 6
    assert design["control_rows"] == design["treatment_rows"] == 3
    assert design["single_mechanism_attribution_allowed"] is False
    assert design["runner_continuity_check_included"] is False
    assert design["task_successor_created"] is False
    assert value["registered_admission"]["all_manifest_count"] == 6
    assert value["registered_admission"]["requires_row_capability"] is True
    assert value["promotion_criteria"]["valid_initial_plan_rows_min"] == 2
    assert value["promotion_criteria"]["first_mutation_rows_min"] == 2
    assert value["promotion_criteria"]["evaluator_reached_rows_min"] == 2
    assert value["recovery_contract"]["consumed_r21_retry_allowed"] is False


def test_candidate_v30_qualification_retains_frozen_v26_source_proof() -> None:
    _, value = _stored()
    binding = value["reviewed_package_binding"]
    assert binding["admission_only_source_delta"]["reviewed_bytes_recovered"] is True
    assert binding["admission_only_source_delta"]["agent_policy_changed"] is False
    assert binding["historical_artifacts_rewritten"] is False
    assert value["evidence_boundary"]["private_task_schema_parsed_by_trusted_loader"] is True
    assert value["evidence_boundary"]["sealed_task_bytes_hashed_for_identity_only"] is True
    assert (
        value["evidence_boundary"]["hidden_or_reference_content_exposed_to_model_or_selection"]
        is False
    )
