from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.evals import rapid_public_development_v26 as rapid
from patchloop.evals import rapid_public_development_v26_qualification as qualification
from patchloop.evals.rapid_public_development_v26_qualification import (
    QUALIFICATION_PATH,
    build_rapid_public_development_v26_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def _stored() -> tuple[bytes, dict[str, object]]:
    target = ROOT / QUALIFICATION_PATH
    if not target.exists():
        pytest.skip("candidate-v32 qualification is materialized after offline gates")
    raw = target.read_bytes()
    return raw, json.loads(raw)


def test_complete_qualification_before_materialization_including_sqlite_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = rapid.build_rapid_public_development_v26_candidate(repository=ROOT)
    rehearsal = rapid._build_rehearsal_for(candidate, repository=ROOT)
    virtual = {
        ROOT / rapid.CANDIDATE_PATH: rapid.candidate_bytes(candidate),
        ROOT / rapid.REHEARSAL_PATH: rapid.rehearsal_bytes(rehearsal),
    }
    original_read = Path.read_bytes
    monkeypatch.setattr(
        Path, "read_bytes", lambda path: virtual[path] if path in virtual else original_read(path)
    )
    monkeypatch.setattr(
        qualification, "load_rapid_public_development_v26_candidate", lambda *_: candidate
    )
    monkeypatch.setattr(
        qualification, "load_rapid_public_development_v26_rehearsal", lambda *a, **k: rehearsal
    )
    first = qualification.build_rapid_public_development_v26_qualification(ROOT)
    second = qualification.build_rapid_public_development_v26_qualification(ROOT)
    assert qualification_bytes(first) == qualification_bytes(second)
    mock = first["production_shaped_image_start_mock"]
    assert mock["real_agent_start_count"] == mock["provider_gate_count"] == 6
    assert mock["mocked_docker_image_inspect_commands"] == 1
    assert mock["isolated_mock_sqlite_connections_closed"] is True
    assert first["evidence_boundary"]["provider_calls"] == 0
    assert first["evidence_boundary"]["docker_calls"] == 0


def test_candidate_v32_qualification_is_canonical_and_zero_call() -> None:
    raw, value = _stored()

    assert raw == qualification_bytes(value)
    assert value == build_rapid_public_development_v26_qualification(ROOT)
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


def test_candidate_v32_qualification_binds_equal_arms_package_and_promotion_floor() -> None:
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


def test_candidate_v32_qualification_retains_frozen_v26_source_proof() -> None:
    _, value = _stored()
    binding = value["reviewed_package_binding"]
    assert all(d["frozen_bytes_recovered"] for d in binding["batch_image_source_deltas"])
    assert binding["agent_semantic_policy_changed"] is False
    mock = value["production_shaped_image_start_mock"]
    assert mock["inspect_adapter_calls"] == 1
    assert mock["real_agent_start_count"] == mock["provider_gate_count"] == 6
    assert mock["per_row_image_inspect_calls"] == mock["actual_docker_calls"] == 0
    assert value["real_docker_identity_observed"] is False
    assert value["real_agent_performance_measured"] is False
    assert binding["historical_artifacts_rewritten"] is False
    assert value["evidence_boundary"]["private_task_schema_parsed_by_trusted_loader"] is True
    assert value["evidence_boundary"]["sealed_task_bytes_hashed_for_identity_only"] is True
    assert (
        value["evidence_boundary"]["hidden_or_reference_content_exposed_to_model_or_selection"]
        is False
    )
