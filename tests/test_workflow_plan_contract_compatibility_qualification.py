from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.workflow_plan_contract_compatibility_qualification import (
    IMMUTABLE_INPUTS,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    build_plan_contract_compatibility_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_v25_qualification_is_deterministic_source_bound_and_zero_call() -> None:
    first = build_plan_contract_compatibility_qualification(ROOT)
    second = build_plan_contract_compatibility_qualification(ROOT)

    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["status"] == "offline-qualified"
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


def test_v25_qualification_records_trigger_schema_feedback_and_retry_limit() -> None:
    scenarios = build_plan_contract_compatibility_qualification(ROOT)["scenarios"]
    schema = scenarios["trigger_bound_plan_schema"]
    feedback = scenarios["bounded_self_directed_feedback"]
    recovery = scenarios["one_retry_recovery"]

    assert schema["initial_disposition_schema"] == {
        "type": "null",
        "enum": [None],
    }
    assert schema["revision_disposition_schema"] == {
        "type": "string",
        "enum": ["retained", "refined", "rejected"],
    }
    assert feedback["v24_predecessor_rejects_self_directed_policy"] is True
    assert feedback["v25_projected_event_count"] == 1
    assert feedback["durable_event_changed"] is False
    assert feedback["durable_result_artifact_changed"] is False
    assert recovery["first_rejection_recovery_used"] is True
    assert recovery["first_rejection_recovery_remaining"] == 0
    assert recovery["first_rejection_provider_retry_available"] is True
    assert recovery["second_rejection_terminal_reason"] == ("work_plan_admission_repeated")
    assert recovery["second_rejection_allowed_tool_names"] == []
    assert recovery["third_provider_dispatch_allowed"] is False


def test_stored_v25_qualification_is_a_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == qualification_bytes(value)
    assert sha256_bytes(raw).startswith("sha256:")
