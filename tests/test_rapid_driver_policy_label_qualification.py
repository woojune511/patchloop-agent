from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals.rapid_driver_policy_label_qualification import (
    IMMUTABLE_PREDECESSORS,
    QUALIFICATION_PATH,
    R18_RESULT_IDENTITY,
    SOURCE_FILES,
    build_rapid_driver_policy_label_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_policy_label_qualification_is_deterministic_and_zero_call() -> None:
    first = build_rapid_driver_policy_label_qualification(ROOT)
    second = build_rapid_driver_policy_label_qualification(ROOT)

    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["status"] == "offline-qualified"
    assert first["serializer_contract"]["source_field"] == "contract.policy_version"
    assert first["consumed_r18_modified"] is False
    assert first["consumed_r18_retry_allowed"] is False
    assert first["candidate_created"] is False
    assert first["paid_execution_authorized"] is False
    assert all(
        first["evidence_boundary"][key] == 0
        for key in (
            "provider_calls",
            "docker_calls",
            "agent_calls",
            "evaluator_calls",
            "visible_check_calls",
            "network_calls",
        )
    )


def test_policy_label_qualification_proves_both_policies_and_r18_mismatch() -> None:
    value = build_rapid_driver_policy_label_qualification(ROOT)

    assert [item["path"] for item in value["source_files"]] == list(SOURCE_FILES)
    assert value["policy_matrix"] == [
        {
            **value["policy_matrix"][0],
            "contract_policy_version": "append-only-row-settlement-driver-v1",
            "serialized_policy_version": "append-only-row-settlement-driver-v1",
            "selected_policy_valid": True,
            "cross_policy_label_valid": False,
        },
        {
            **value["policy_matrix"][1],
            "contract_policy_version": "append-only-row-settlement-driver-v2",
            "serialized_policy_version": "append-only-row-settlement-driver-v2",
            "selected_policy_valid": True,
            "cross_policy_label_valid": False,
        },
    ]
    observation = value["r18_observation"]
    assert observation["contract_hash_matches_v1"] is False
    assert observation["contract_hash_matches_v2"] is True
    assert observation["provenance_mismatch_confirmed"] is True
    assert observation["historical_result_rewritten"] is False
    assert observation["promotion_evidence_eligible"] is False


def test_policy_label_qualification_byte_audits_immutable_predecessors() -> None:
    value = build_rapid_driver_policy_label_qualification(ROOT)
    expected = [{"path": path, **identity} for path, identity in IMMUTABLE_PREDECESSORS.items()]

    assert value["immutable_predecessors"] == [*expected, R18_RESULT_IDENTITY]


def test_stored_policy_label_qualification_is_a_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == qualification_bytes(value)
    assert sha256_bytes(raw).startswith("sha256:")
