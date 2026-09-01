from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals.rapid_row_continuation_qualification import (
    IMMUTABLE_PREDECESSORS,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    build_rapid_row_continuation_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_row_isolation_qualification_is_deterministic_and_zero_call() -> None:
    first = build_rapid_row_continuation_qualification(ROOT)
    second = build_rapid_row_continuation_qualification(ROOT)

    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["status"] == "offline-qualified"
    assert first["typed_capability_gateway_integrated"] is True
    assert first["rapid_batch_driver_integrated"] is False
    assert first["runtime_surface_integrated"] is False
    assert first["rapid_candidate_created"] is False
    assert first["paid_execution_authorized"] is False
    assert all(
        first["evidence_boundary"][key] == 0
        for key in (
            "provider_calls",
            "docker_calls",
            "evaluator_calls",
            "visible_check_calls",
            "workspace_mutations",
        )
    )


def test_row_isolation_qualification_covers_allowlist_and_fail_closed_matrix() -> None:
    scenarios = build_rapid_row_continuation_qualification(ROOT)["scenarios"]

    assert scenarios["eligible_exact_settlement"]["decision"] == "continue"
    assert scenarios["eligible_exact_settlement"]["next_row_capability_issued"] is False
    assert all(
        item["decision"] == "halt" for item in scenarios["each_missing_check_halts"].values()
    )
    assert all(
        item["decision"] == "halt" for item in scenarios["each_missing_identity_halts"].values()
    )
    assert all(item["decision"] == "halt" for item in scenarios["semantic_conflicts_halt"].values())
    assert scenarios["tampered_evidence"] == {
        "rejected": True,
        "public_error": "Rapid row settlement evidence is invalid",
    }


def test_row_isolation_qualification_binds_r16_without_reclassifying_it() -> None:
    value = build_rapid_row_continuation_qualification(ROOT)

    assert [item["path"] for item in value["source_files"]] == list(SOURCE_FILES)
    assert [item["path"] for item in value["immutable_predecessors"]] == list(
        IMMUTABLE_PREDECESSORS
    )
    observation = value["r16_observation"]
    assert observation["bundle_terminal_error_code"] is None
    assert observation["diagnosis_terminal_error_code"] == "RECOVERY_ERROR"
    assert observation["bounded_settlement_receipt_fields_present"] is False
    assert observation["retroactive_continuation_eligible"] is False
    assert observation["retry_allowed"] is False
    assert observation["historical_result_reclassified"] is False


def test_stored_row_isolation_qualification_is_a_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == qualification_bytes(value)
    assert sha256_bytes(raw).startswith("sha256:")
