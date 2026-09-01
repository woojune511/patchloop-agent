from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.workflow_exploration_gate_activation_qualification import (
    IMMUTABLE_PREDECESSORS,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    build_workflow_exploration_gate_activation_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_activation_qualification_is_deterministic_and_zero_call() -> None:
    first = build_workflow_exploration_gate_activation_qualification(ROOT)
    second = build_workflow_exploration_gate_activation_qualification(ROOT)

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
            "workspace_mutations",
        )
    )


def test_activation_scenarios_bind_readiness_surface_and_durable_closure() -> None:
    value = build_workflow_exploration_gate_activation_qualification(ROOT)
    scenarios = value["scenarios"]

    assert scenarios["runtime_identity"] == {
        "runtime_policy_version": "lean-harness-v19",
        "tool_schema_version": "v23",
        "context_policy_version": "phase-evidence-v29",
        "request_evidence_schema": "lean-harness-request-evidence-v19",
        "activation_policy_version": "gateway-owned-public-exploration-closure-v1",
    }
    assert scenarios["bounded_readiness"]["single_range_tools"] == [
        "search_files",
        "read_file",
    ]
    assert scenarios["bounded_readiness"]["single_range_plan_request"] is False
    assert scenarios["bounded_readiness"]["ready_plan_schema_present"] is True
    assert scenarios["dynamic_plan_surface"]["request_parameters_match_surface"] is True
    assert (
        scenarios["dynamic_plan_surface"]["open_blocker_rejection"]
        == "exploration_blocking_unknowns_open"
    )
    assert scenarios["durable_closure"]["binding_round_trip_exact"] is True
    assert scenarios["durable_closure"]["selected_source_coverage_key_count"] >= 2


def test_activation_qualification_binds_exact_sources_and_predecessors() -> None:
    value = build_workflow_exploration_gate_activation_qualification(ROOT)
    assert [item["path"] for item in value["source_files"]] == list(SOURCE_FILES)
    assert [item["path"] for item in value["immutable_predecessors"]] == list(
        IMMUTABLE_PREDECESSORS
    )
    for item in value["immutable_predecessors"]:
        assert {
            key: item[key] for key in IMMUTABLE_PREDECESSORS[item["path"]]
        } == IMMUTABLE_PREDECESSORS[item["path"]]


def test_stored_activation_qualification_remains_an_immutable_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == qualification_bytes(value)
    assert len(raw) == 4_925
    assert sha256_bytes(raw) == (
        "sha256:a25881f54e66a11ef6f3ca9b41d0cf44ce7a37ec1b2fe7fd1efbade0994462c5"
    )
