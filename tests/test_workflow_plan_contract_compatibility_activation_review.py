from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.workflow_plan_contract_compatibility_activation_review import (
    IMMUTABLE_INPUTS,
    REVIEW_PATH,
    SOURCE_FILES,
    build_plan_contract_compatibility_activation_review,
    review_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_v25_activation_review_is_deterministic_and_candidate_noncreating() -> None:
    first = build_plan_contract_compatibility_activation_review(ROOT)
    second = build_plan_contract_compatibility_activation_review(ROOT)

    assert review_bytes(first) == review_bytes(second)
    assert first["status"] == "activation-reviewed-candidate-decision-ready"
    assert first["decision"]["candidate_preparation_ready"] is True
    assert first["decision"]["candidate_created"] is False
    assert first["candidate_created"] is False
    assert first["external_calls"] == 0
    assert [item["path"] for item in first["source_files"]] == list(SOURCE_FILES)
    assert [item["path"] for item in first["immutable_inputs"]] == list(IMMUTABLE_INPUTS)
    assert all(
        first["evidence_boundary"][key] == 0
        for key in (
            "provider_calls",
            "docker_calls",
            "evaluator_calls",
            "visible_check_calls",
            "network_calls",
        )
    )


def test_v25_activation_review_binds_r20_shapes_and_bounded_recovery() -> None:
    value = build_plan_contract_compatibility_activation_review(ROOT)
    historical = value["historical_public_failure_shapes"]
    mock = value["production_shaped_mock_validation"]

    assert [row["run_id"] for row in historical["rows"]] == [
        "run_rapid_v28_d7710f25ffd2_02",
        "run_rapid_v28_d7710f25ffd2_03",
    ]
    assert {row["terminal_error_code"] for row in historical["rows"]} == {"CONTRACT_ERROR"}
    assert historical["raw_trace_replayed"] is False
    assert mock["successful_information_action_depths"] == [8, 9]
    assert mock["bounded_retry_then_completed"] == [True, True]
    assert mock["repeated_invalid_attempt_provider_dispatches"] == 2
    assert mock["third_provider_dispatch"] is False
    assert mock["local_mock_visible_check_dispatches_exercised"] is True
    assert mock["external_visible_check_calls"] == 0
    assert all(value["activation_criteria"].values())


def test_stored_v25_activation_review_is_a_byte_audit() -> None:
    raw = (ROOT / REVIEW_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == review_bytes(value)
    assert sha256_bytes(raw).startswith("sha256:")
