from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.workflow_plan_admission_feedback_successor import (
    PROJECTED_FEEDBACK_SCHEMA,
)
from patchloop.agent.workflow_plan_admission_feedback_successor_qualification import (
    IMMUTABLE_PREDECESSORS,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    build_workflow_plan_admission_feedback_successor_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_plan_feedback_qualification_is_deterministic_and_zero_call() -> None:
    first = build_workflow_plan_admission_feedback_successor_qualification(ROOT)
    second = build_workflow_plan_admission_feedback_successor_qualification(ROOT)

    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["status"] == "offline-qualified"
    assert first["runtime_surface_activated"] is True
    assert first["rapid_candidate_created"] is False
    assert first["paid_execution_authorized"] is False
    assert first["quality_improvement_established"] is False
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


def test_plan_feedback_qualification_covers_bounded_retry_and_fail_closed() -> None:
    scenarios = build_workflow_plan_admission_feedback_successor_qualification(ROOT)["scenarios"]

    assert scenarios["runtime_identity"] == {
        "runtime_policy_version": "lean-harness-v22",
        "tool_schema_version": "v25",
        "context_policy_version": "phase-evidence-v32",
        "request_evidence_schema": "lean-harness-request-evidence-v22",
        "projection_policy_version": "bounded-plan-admission-feedback-v1",
        "tool_contract_changed_from_v21": False,
    }
    bounded = scenarios["bounded_projection"]
    assert bounded["projected_feedback_schema"] == PROJECTED_FEEDBACK_SCHEMA
    assert bounded["context_bytes_saved"] > 25_000
    assert bounded["projected_error_details_bytes"] <= 4_096
    assert bounded["source_event_hash_bound_in_projection"] is True
    assert bounded["durable_details_hash_preserved"] is True
    assert bounded["durable_event_changed"] is False
    assert bounded["durable_result_artifact_changed"] is False
    assert bounded["deterministic_projection"] is True
    assert scenarios["empty_context"] == {
        "exact_noop": True,
        "projected_event_count": 0,
        "context_bytes_saved": 0,
    }
    assert "source fields differ" in scenarios["fail_closed"]["unversioned_field"]
    assert "nested binding differs" in scenarios["fail_closed"]["tampered_nested_binding"]


def test_plan_feedback_qualification_records_mock_size_admission() -> None:
    observed = build_workflow_plan_admission_feedback_successor_qualification(ROOT)["scenarios"][
        "observed_public_mock_runner"
    ]

    assert (
        observed["recovered_retry_request_bytes"]
        < observed["admission_thresholds"]["recovered_retry_request_max_bytes"]
    )
    assert (
        observed["current_plan_request_bytes"]
        < observed["admission_thresholds"]["current_plan_request_max_bytes"]
    )
    assert (
        observed["recovered_context_bytes_saved"]
        >= observed["admission_thresholds"]["minimum_context_bytes_saved"]
    )
    assert observed["projected_error_details_bytes"] < observed["durable_error_details_bytes"]
    assert observed["exact_provider_input_tokens_measured"] is False


def test_plan_feedback_qualification_binds_sources_and_predecessors() -> None:
    value = build_workflow_plan_admission_feedback_successor_qualification(ROOT)

    assert [item["path"] for item in value["source_files"]] == list(SOURCE_FILES)
    assert [item["path"] for item in value["immutable_predecessors"]] == list(
        IMMUTABLE_PREDECESSORS
    )
    for item in value["immutable_predecessors"]:
        assert {
            key: item[key] for key in IMMUTABLE_PREDECESSORS[item["path"]]
        } == IMMUTABLE_PREDECESSORS[item["path"]]


def test_stored_plan_feedback_qualification_is_a_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == qualification_bytes(value)
    assert sha256_bytes(raw).startswith("sha256:")
