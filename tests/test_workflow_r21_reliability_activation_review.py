from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from patchloop.agent.workflow_r21_reliability_activation_review import (
    IMMUTABLE_INPUTS,
    REVIEW_PATH,
    SOURCE_FILES,
    activation_criteria,
    build_r21_reliability_activation_review,
    review_bytes,
)
from patchloop.agent.workflow_r21_reliability_qualification import (
    build_r21_reliability_qualification,
)
from patchloop.errors import ContractError
from patchloop.evals.rapid_v26_batch_image_binding import validate_v26_batch_image_binding
from patchloop.evals.rapid_v26_package_binding import (
    V26_REVIEW_FILE_SHA256,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def _frozen_review() -> dict:
    raw = (ROOT / REVIEW_PATH).read_bytes()
    assert sha256_bytes(raw) == V26_REVIEW_FILE_SHA256
    assert validate_v26_batch_image_binding(ROOT)["historical_artifacts_rewritten"] is False
    return json.loads(raw)


def test_frozen_v26_activation_review_is_canonical_zero_call_and_noncreating() -> None:
    first = _frozen_review()
    second = _frozen_review()

    assert review_bytes(first) == review_bytes(second)
    assert first["status"] == "activation-reviewed-candidate-decision-ready"
    assert first["decision"]["suitable_for_future_rapid_candidate"] is True
    assert first["decision"]["adoption_status"] == "eligible-not-adopted"
    assert first["decision"]["candidate_created"] is False
    assert first["candidate_created"] is False
    assert first["external_calls"] == 0
    assert [item["path"] for item in first["review_source_files"]] == list(SOURCE_FILES)
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


def test_v26_activation_review_accepts_only_one_nonattributable_package() -> None:
    value = _frozen_review()

    assert value["package_assessment"]["mechanism_count"] == 4
    assert value["package_assessment"]["acceptable_variable"] == (
        "single-versioned-product-package"
    )
    assert value["package_assessment"]["single_mechanism_attribution_allowed"] is False
    assert all(value["activation_criteria"].values())
    constraints = value["future_candidate_constraints"]
    assert constraints["recommended_control_runtime"] == "lean-harness-v25"
    assert constraints["recommended_treatment_runtime"] == "lean-harness-v26"
    assert constraints["task_successor_allowed"] is False
    assert constraints["runner_continuity_check_allowed"] is False
    assert constraints["candidate_design_authorized_by_review"] is False


def test_v26_activation_review_keeps_hidden_failure_and_public_check_outside() -> None:
    value = _frozen_review()
    historical = value["historical_public_observations"]
    rows = historical["rows"]

    assert [row["run_id"] for row in rows] == [
        "run_rapid_v29_590bbd602a34_01",
        "run_rapid_v29_590bbd602a34_02",
        "run_rapid_v29_590bbd602a34_03",
    ]
    assert historical["mechanism_causality_established"] is False
    assert historical["row_2_hidden_cause_inferred"] is False
    assert historical["reasoning_or_response_text_read"] is False
    separation = value["runner_continuity_separation"]
    assert separation["behavior_observed"] is False
    assert separation["task_successor_created"] is False
    assert separation["include_in_future_v25_v26_comparison"] is False


def test_v26_activation_review_fails_closed_on_semantic_oracle_or_check_activation() -> None:
    qualification = build_r21_reliability_qualification(ROOT)
    semantic_oracle = copy.deepcopy(qualification)
    semantic_oracle["scenarios"]["generic_lifecycle_state_transition"][
        "semantic_truth_verified"
    ] = True
    activated_check = copy.deepcopy(qualification)
    activated_check["separate_public_check_proposal"]["behavior_observed"] = True

    assert (
        activation_criteria(semantic_oracle)[
            "lifecycle_contract_is_public_provenance_not_semantic_oracle"
        ]
        is False
    )
    assert (
        activation_criteria(activated_check)["runner_continuity_remains_unobserved_and_excluded"]
        is False
    )


def test_stored_v26_activation_review_is_a_byte_audit() -> None:
    raw = (ROOT / REVIEW_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == review_bytes(value)
    assert sha256_bytes(raw) == V26_REVIEW_FILE_SHA256


def test_frozen_review_builder_does_not_silently_relabel_admission_integration() -> None:
    with pytest.raises(ContractError, match="qualification source binding differs"):
        build_r21_reliability_activation_review(ROOT)
