from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals.rapid_terminal_state_parity_qualification import (
    PREDECESSOR_QUALIFICATION_IDENTITY,
    QUALIFICATION_PATH,
    R17_RESULT_IDENTITY,
    SOURCE_FILES,
    build_rapid_terminal_state_parity_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_terminal_parity_qualification_is_deterministic_and_zero_call() -> None:
    first = build_rapid_terminal_state_parity_qualification(ROOT)
    second = build_rapid_terminal_state_parity_qualification(ROOT)

    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["status"] == "offline-qualified"
    assert first["successor_policy_version"] == "append-only-row-settlement-driver-v2"
    assert first["successor_opt_in_required"] is True
    assert first["candidate_specific_runtime_integrated"] is False
    assert first["rapid_candidate_created"] is False
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


def test_terminal_parity_qualification_binds_production_shape_and_predecessors() -> None:
    value = build_rapid_terminal_state_parity_qualification(ROOT)

    assert [item["path"] for item in value["source_files"]] == list(SOURCE_FILES)
    assert value["predecessor_qualification"] == PREDECESSOR_QUALIFICATION_IDENTITY
    assert value["consumed_r17_result"] == R17_RESULT_IDENTITY
    assert value["terminal_contract"]["completed"] == {
        "event_type": "RunCompleted",
        "status": "completed",
        "result_outcomes": ["resolved", "task_failure"],
        "payload_result_bindings": ["scope_compliant_success", "official"],
        "payload_outcome_kind_required": False,
    }
    assert value["terminal_contract"]["payload_mismatch_halts_before_next_row"] is True
    assert value["consumed_r17_modified"] is False
    assert value["consumed_r17_retry_allowed"] is False


def test_stored_terminal_parity_qualification_is_a_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == qualification_bytes(value)
    assert sha256_bytes(raw).startswith("sha256:")
