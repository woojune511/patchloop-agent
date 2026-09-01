from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.workflow_self_directed_exploration_successor_qualification import (
    IMMUTABLE_PREDECESSORS,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    build_workflow_self_directed_exploration_successor_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_self_directed_qualification_is_deterministic_and_zero_call() -> None:
    first = build_workflow_self_directed_exploration_successor_qualification(ROOT)
    second = build_workflow_self_directed_exploration_successor_qualification(ROOT)

    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["status"] == "offline-qualified"
    assert first["candidate_created"] is False
    assert first["external_activation_performed"] is False
    assert first["external_calls"] == 0
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


def test_self_directed_qualification_covers_choice_and_readiness_boundaries() -> None:
    scenarios = build_workflow_self_directed_exploration_successor_qualification(ROOT)["scenarios"]

    assert scenarios["runtime_identity"] == {
        "runtime_policy_version": "lean-harness-v23",
        "tool_schema_version": "v26",
        "context_policy_version": "phase-evidence-v33",
        "request_evidence_schema": "lean-harness-request-evidence-v23",
        "exploration_policy_version": "bounded-self-directed-exploration-v1",
        "opt_in_successor": True,
    }
    choices = scenarios["minimum_floor_and_choice"]
    assert choices["before_source_read"] == ["search_files", "read_file"]
    assert set(choices["after_first_source_read"]) == {
        "search_files",
        "read_file",
        "record_work_plan",
    }
    assert choices["plan_request_present"] is True
    assert choices["investigation_intent_required_after_first_read"] is True
    assert choices["search_counts_as_source_coverage"] is False

    readiness = scenarios["readiness"]
    assert readiness["multi_range"]["admitted"] is True
    assert readiness["co_located_boundary"]["admitted"] is True
    assert readiness["co_located_boundary"]["selected_coverage_count"] == 1
    assert readiness["co_located_missing_preservation_reason"] == (
        "self_directed_colocated_boundary_invalid"
    )
    assert readiness["semantic_understanding_verified_by_admission"] is False


def test_self_directed_qualification_covers_admission_and_stop() -> None:
    scenarios = build_workflow_self_directed_exploration_successor_qualification(ROOT)["scenarios"]
    admission = scenarios["investigation_admission"]
    assert admission["duplicate_target_reason"] == ("self_directed_investigation_target_repeated")
    assert admission["outside_scope_reason"] == ("self_directed_investigation_target_outside_scope")
    assert admission["intent_semantic_truth_judged"] is False

    stop = scenarios["bounded_stop"]
    assert stop["information_actions_used"] == stop["information_action_limit"] == 10
    assert stop["allowed_tools"] == [
        "record_work_plan",
        "declare_exploration_exhausted",
    ]
    assert stop["patch_created"] is False
    assert stop["submission_created"] is False


def test_self_directed_qualification_binds_sources_and_predecessors() -> None:
    value = build_workflow_self_directed_exploration_successor_qualification(ROOT)

    assert [item["path"] for item in value["source_files"]] == list(SOURCE_FILES)
    assert [item["path"] for item in value["immutable_predecessors"]] == list(
        IMMUTABLE_PREDECESSORS
    )
    for item in value["immutable_predecessors"]:
        assert {
            key: item[key] for key in IMMUTABLE_PREDECESSORS[item["path"]]
        } == IMMUTABLE_PREDECESSORS[item["path"]]


def test_stored_self_directed_qualification_is_a_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == qualification_bytes(value)
    assert sha256_bytes(raw).startswith("sha256:")
